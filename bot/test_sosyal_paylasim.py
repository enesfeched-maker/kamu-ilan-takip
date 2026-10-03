import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from PIL import Image

import kapak_tasarimlari as kt
import site_uret
import sosyal_paylasim as sp
from site_uret import TR

SIMDI = datetime(2026, 10, 2, 10, 30, tzinfo=TR)
SITE = 'https://ornek.example/site/'


def ilan(kimlik, gorulme='2026-10-01T09:00:00+03:00', **ek):
    kayit = {'id': kimlik, 'baslik': f'{kimlik} alım ilanı', 'kurum': 'ÖRNEK BELEDİYESİ', 'link': 'https://kariyerkapisi.gov.tr/x',
             'ilk_gorulme': gorulme, 'son_tarih': '2026-10-20', 'kadro': '3 Zabıta Memuru', 'iller': ['Ankara'],
             'ogrenim': ['lisans'], 'kaynaklar': [{'ad': 'Kariyer Kapısı'}]}
    kayit.update(ek)
    return kayit


class SecimTesti(unittest.TestCase):
    def test_dun_istanbul_siniri(self):
        ilanlar = [ilan('a', '2026-10-01T00:00:00+03:00'), ilan('b', '2026-10-01T23:59:59+03:00'),
                   ilan('c', '2026-10-02T00:00:00+03:00'), ilan('d', '2026-09-30T23:59:59+03:00'),
                   ilan('e', '2026-10-01T22:00:00+00:00'), ilan('f', '2026-09-30T21:30:00+00:00')]
        self.assertEqual({i['id'] for i in sp.sec(ilanlar, SIMDI)}, {'a', 'b', 'f'})

    def test_iptal_ve_suresi_gecen_haric(self):
        ilanlar = [ilan('a'), ilan('b', duyuru_turu='İptal duyurusu'), ilan('c', son_tarih='2026-10-01'),
                   ilan('d', son_zaman='2026-10-02T09:00:00+03:00'), ilan('e', son_tarih=None)]
        self.assertEqual([i['id'] for i in sp.sec(ilanlar, SIMDI)], ['a', 'e'])

    def test_siralama_yakin_tarih_once_tarihsiz_sona(self):
        ilanlar = [ilan('uzak', son_tarih='2026-12-01'), ilan('yok', son_tarih=None), ilan('yakin', son_tarih='2026-10-03'),
                   ilan('yakin2', son_tarih='2026-10-03', ilk_gorulme='2026-10-01T05:00:00+03:00')]
        self.assertEqual([i['id'] for i in sp.sec(ilanlar, SIMDI)], ['yakin2', 'yakin', 'uzak', 'yok'])


class UretimTesti(unittest.TestCase):
    def uret(self, ilanlar):
        klasor = tempfile.TemporaryDirectory()
        self.addCleanup(klasor.cleanup)
        veri = sp.uret(ilanlar, SIMDI, klasor.name, SITE)
        return Path(klasor.name), veri

    def test_bos_durumu(self):
        kok, veri = self.uret([ilan('a', '2026-09-01T00:00:00+03:00')])
        self.assertTrue(veri['bos'])
        self.assertEqual(veri['gorseller'], [])
        kayitli = json.loads((kok / 'paylasim' / 'gunluk.json').read_text(encoding='utf-8'))
        self.assertEqual(kayitli, veri)
        self.assertEqual(kayitli['tarih'], '2026-10-02')

    def test_en_fazla_dokuz_kart_ve_adresler(self):
        kok, veri = self.uret([ilan(f'i{n:02d}', son_tarih=f'2026-10-{10 + n}') for n in range(12)])
        self.assertFalse(veri['bos'])
        self.assertEqual(veri['ilan_sayisi'], 12)
        self.assertEqual(len(veri['gorseller']), 10)
        self.assertEqual(veri['gorseller'][0], SITE + 'paylasim/2026-10-02/00-kapak.jpg')
        self.assertEqual(sorted(p.name for p in (kok / 'paylasim' / '2026-10-02').glob('*.jpg')),
                         ['00-kapak.jpg'] + [f'{n:02d}.jpg' for n in range(1, 10)])

    def test_deterministik(self):
        ilanlar = [ilan('a'), ilan('b', baslik='Çok uzun ' * 40, kurum='Ğ' * 200, kadro='x ' * 300)]
        k1, v1 = self.uret(ilanlar)
        k2, v2 = self.uret(ilanlar)
        self.assertEqual(v1, v2)
        for yol in (k1 / 'paylasim' / '2026-10-02').glob('*.jpg'):
            self.assertEqual(yol.read_bytes(), (k2 / 'paylasim' / '2026-10-02' / yol.name).read_bytes())

    def test_gorsel_boyutu(self):
        kok, _ = self.uret([ilan('a', baslik='Uzun başlık ' * 30)])
        for yol in (kok / 'paylasim' / '2026-10-02').glob('*.jpg'):
            self.assertLessEqual(yol.stat().st_size, 1_000_000)
            with Image.open(io.BytesIO(yol.read_bytes())) as im:
                self.assertEqual((im.format, im.size), ('JPEG', (1080, 1350)))

    def test_metinler(self):
        ilanlar = [ilan(f'i{n}', kurum='GÜZEL KURUM ' * 8, baslik='Başlık ' * 60) for n in range(9)]
        _, veri = self.uret(ilanlar)
        x = veri['x_metin']
        self.assertLessEqual(sp.x_agirlik(x), 260)
        self.assertIn('📢 Bugün 9 yeni kamu ilanı', x)
        for yasak in ('http', 'github', 'kamuilan.', '.com', 'ornek.example', 'gov.tr'):
            self.assertNotIn(yasak, x)
        self.assertLessEqual(len(veri['ig_metin']), 2200)
        self.assertIn('profildeki bağlantı', veri['ig_metin'])
        self.assertIn('#Ankara', veri['ig_metin'])

    def test_x_alan_adi_iceren_madde_atlanir(self):
        metin = sp.x_metni([ilan('a', kurum='Ornek.com Kurumu'), ilan('b', kurum='Temiz Kurum')], 2)
        self.assertNotIn('.com', metin)
        self.assertIn('Temiz Kurum', metin)

    def test_x_emoji_iki_sayilir(self):
        self.assertEqual(sp.x_agirlik('📢a'), 3)


class DenetimDuzeltmeTesti(unittest.TestCase):
    def test_etiket_sayisi_25_ile_sinirli(self):
        iller = ['Adana', 'Ankara', 'Antalya', 'Bolu', 'Bursa', 'Çorum', 'Denizli', 'Edirne', 'Hatay', 'İzmir', 'Konya',
                 'Rize', 'Sivas', 'Van', 'Yozgat', 'Mersin', 'Muğla', 'Ordu', 'Samsun', 'Tokat', 'Uşak', 'Kars', 'Siirt',
                 'Niğde', 'Aydın', 'Bitlis', 'Elazığ', 'Giresun', 'Kayseri', 'Manisa', 'Sinop', 'Trabzon', 'Zonguldak',
                 'Düzce', 'Yalova', 'Bartın', 'Amasya', 'Artvin', 'Burdur', 'Çankırı', 'Isparta', 'Kilis', 'Malatya',
                 'Mardin', 'Muş', 'Rize']
        ilanlar = [ilan(f'i{n}', iller=iller[n * 5:n * 5 + 5], ogrenim=['lisans', 'onlisans']) for n in range(9)]
        metin = sp.ig_metni(ilanlar, 9, SIMDI.date())
        etiketler = metin.rsplit('\n', 1)[1].split()
        self.assertLessEqual(len(etiketler), 25)
        self.assertEqual(etiketler[:4], ['#kamuilanları', '#kpss', '#memuralımı', '#kamupersonel'])
        self.assertEqual(len(etiketler), len(set(etiketler)))
        self.assertIn('#lisans', etiketler)

    def test_sure_referansi_paylasim_gunu_10_30(self):
        ilanlar = [ilan('a', son_zaman='2026-10-02T10:00:00+03:00'), ilan('b', son_zaman='2026-10-02T11:00:00+03:00')]
        for saat in (9, 12):
            simdi = datetime(2026, 10, 2, saat, 45, tzinfo=TR)
            self.assertEqual([i['id'] for i in sp.sec(ilanlar, simdi)], ['b'])

    def test_kurum_tekrari_karisik_harfte_atilir(self):
        self.assertEqual(sp._kurumu_at('İstanbul Üniversitesi', 'İSTANBUL ÜNİVERSİTESİ - 5 Öğretim Üyesi'), '5 Öğretim Üyesi')
        self.assertEqual(sp._kurumu_at('Ankara Valiliği', 'Başka başlık'), 'Başka başlık')

    def test_x_ayni_kurum_bir_kez(self):
        metin = sp.x_metni([ilan('a', kurum='ÖRNEK BELEDİYESİ'), ilan('b', kurum='Örnek Belediyesi'),
                            ilan('c', kurum='Diğer Kurum')], 3)
        self.assertEqual(metin.count('Örnek Belediyesi'), 1)
        self.assertIn('Diğer Kurum', metin)


class KartTesti(unittest.TestCase):
    def test_kartlar_ilan_karti_ile_uretilir(self):
        with tempfile.TemporaryDirectory() as klasor, mock.patch.object(sp, 'ilan_karti', wraps=sp.ilan_karti) as karti:
            veri = sp.uret([ilan('a'), ilan('b', kadro='Toplam 2 kişi — 2 Şoför')], SIMDI, klasor, SITE)
            self.assertEqual(karti.call_count, 2)
            for cagri in karti.call_args_list:  # referans an: paylaşım günü 10:30
                self.assertEqual(cagri.kwargs['simdi'], datetime(2026, 10, 2, 10, 30, tzinfo=TR))
            self.assertEqual(len(veri['gorseller']), 3)

    def test_kart_farkli_uretim_saatinde_ayni(self):
        ilanlar = [ilan('a'), ilan('b', kadro='Toplam 2 kişi — 2 Şoför')]
        sonuclar = []
        for saat in (9, 14):
            with tempfile.TemporaryDirectory() as klasor:
                sp.uret(ilanlar, datetime(2026, 10, 2, saat, 5, tzinfo=TR), klasor, SITE)
                sonuclar.append([(Path(klasor) / 'paylasim' / '2026-10-02' / f'{n:02d}.jpg').read_bytes() for n in (1, 2)])
        self.assertEqual(sonuclar[0], sonuclar[1])


class KapakTesti(unittest.TestCase):
    BUYUK = dict(kadro='Toplam 12 kişi — 12 Zabıta Memuru', son_tarih='2026-10-05')

    def test_uc_gun_uc_farkli_tasarim(self):
        ilanlar = [ilan('a', **self.BUYUK)]
        adlar = [kt.kapak_sec(ilanlar, datetime(2026, 10, g, 10, 30, tzinfo=TR)) for g in (2, 3, 4)]
        self.assertEqual(sorted(adlar), sorted(kt.TASARIMLAR))
        self.assertEqual(kt.kapak_sec(ilanlar, SIMDI), kt.kapak_sec(ilanlar, SIMDI))

    def test_uygunluk_dususleri(self):
        kadrosuz = [ilan('a', kadro='', baslik='Personel alımı', son_tarih='2026-10-05')]
        tarihsiz = [ilan('a', kadro='Toplam 12 kişi — 12 Zabıta Memuru', son_tarih=None)]
        for g in range(1, 10):
            simdi = datetime(2026, 10, g, 10, 30, tzinfo=TR)
            self.assertNotEqual(kt.kapak_sec(kadrosuz, simdi), 'manset')
            self.assertNotEqual(kt.kapak_sec(tarihsiz, simdi), 'kacirma')

    def test_tasarimlar_boyut_ve_az_veri(self):
        bol = [ilan('a', **self.BUYUK), ilan('b', kadro='Toplam 5 kişi — 5 Hemşire • 1 Uzman, 2 Destek Personel', son_tarih='2026-10-03')]
        az = [ilan('c', kadro='', baslik='ÖRNEK BELEDİYESİ personel alımı', son_tarih=None, ogrenim=[], iller=[])]
        for ad, tasarim in kt.TASARIMLAR.items():
            for liste in (bol, az):
                with self.subTest(ad=ad, ilan=len(liste), az=liste is az):
                    im = tasarim(liste, len(liste), SIMDI)
                    self.assertEqual((im.size, im.mode), ((1080, 1350), 'RGB'))

    def test_mozaik_cipleri_temiz(self):
        self.assertEqual(kt._temiz_adlar(['Uzman, 2 Destek Personel', 'Hemşire', 'hemşire', '3 Zabıta', 'x' * 40, 'Mühendis']),
                         ['Uzman', 'Hemşire', 'Mühendis'])

    def test_manset_basligi_adetsiz_kadroda_toplam(self):
        i = ilan('a', kadro='Toplam 12 kişi — Zabıta Memuru')
        v = kt._veri(i, SIMDI)
        baslik = kt.manset_basligi(i, v, 1)
        self.assertIn('12', baslik)
        self.assertIn('Zabıta Memuru', baslik)
        self.assertEqual(kt.manset_basligi(i, None, 3), 'Örnek Belediyesi yeni ilan yayınladı')

    def test_bozuk_tarih_yok_sayilir(self):
        from kart_tasarimlari import _bitis
        self.assertEqual(_bitis({'son_tarih': '31/12/2026'}), (None, False))
        self.assertEqual(_bitis({'son_zaman': 'bozuk'}), (None, False))
        self.assertIsNone(kt._bitis({'son_tarih': 'bozuk'}))

    def test_kapak_saatten_bagimsiz(self):
        ilanlar = [ilan('a', kadro='Toplam 12 kişi — Zabıta Memuru', son_tarih='2026-10-05')]
        sonuc = []
        for an in (datetime(2026, 1, 1, 8, tzinfo=TR), datetime(2030, 6, 6, 20, tzinfo=TR)):
            with mock.patch('kart_tasarimlari.datetime') as sahte:
                sahte.now.return_value = an
                sahte.fromisoformat = datetime.fromisoformat
                sonuc.append({ad: t(ilanlar, 1, SIMDI).tobytes() for ad, t in kt.TASARIMLAR.items()})
        self.assertEqual(sonuc[0], sonuc[1])

    def test_gunluk_json_kapak_tasarimi(self):
        with tempfile.TemporaryDirectory() as klasor:
            veri = sp.uret([ilan('a', **self.BUYUK)], SIMDI, klasor, SITE)
            kayitli = json.loads((Path(klasor) / 'paylasim' / 'gunluk.json').read_text(encoding='utf-8'))
        self.assertIn(veri['kapak_tasarimi'], kt.TASARIMLAR)
        self.assertEqual(kayitli['kapak_tasarimi'], veri['kapak_tasarimi'])
        with tempfile.TemporaryDirectory() as klasor:
            self.assertIsNone(sp.uret([], SIMDI, klasor, SITE)['kapak_tasarimi'])


class SiteUretEntegrasyonu(unittest.TestCase):
    def kur(self):
        klasor = tempfile.TemporaryDirectory()
        self.addCleanup(klasor.cleanup)
        kok = Path(klasor.name)
        (kok / 'docs').mkdir()
        (kok / 'docs' / 'ilanlar.json').write_text(json.dumps({'ilanlar': []}), encoding='utf-8')
        return kok

    def test_main_uret_cagirir(self):
        kok = self.kur()
        with mock.patch.object(site_uret, 'ROOT', kok), mock.patch.object(sp, 'uret') as uret:
            site_uret.main()
        self.assertEqual(uret.call_count, 1)
        self.assertEqual(uret.call_args.args[2], kok / 'docs')
        self.assertEqual(uret.call_args.args[3], site_uret.BASE)

    def test_main_hatayi_yutar(self):
        kok = self.kur()
        with mock.patch.object(site_uret, 'ROOT', kok), mock.patch.object(sp, 'uret', side_effect=RuntimeError('x')):
            site_uret.main()
        self.assertTrue((kok / 'docs' / 'sitemap.xml').exists())
        self.assertTrue((kok / 'docs' / 'bot-ilanlar.json').exists())


if __name__ == '__main__':
    unittest.main()
