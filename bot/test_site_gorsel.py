import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from PIL import Image

import site_uret
from site_uret import TR, detail_page, gorselleri_uret

KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=%s'
U1 = '11111111-1111-4111-8111-111111111111'
U2 = '22222222-2222-4222-8222-222222222222'
U3 = '33333333-3333-4333-8333-333333333333'


def png(boyut=(300, 200), renk='#336699'):
    cikti = io.BytesIO()
    Image.new('RGB', boyut, renk).save(cikti, format='PNG')
    return cikti.getvalue()


def ilan(uuid, kurum, **ek):
    return {'id': KK % uuid, 'link': KK % uuid, 'baslik': kurum + ' Zabıta Memuru Alımı', 'kurum': kurum,
            'kadro': '2 Zabıta Memuru', 'son_tarih': '2099-12-31', 'ogrenim': ['lisans'], **ek}


SIMDI = datetime(2026, 10, 3, 12, 0, tzinfo=TR)


class GorselTests(unittest.TestCase):
    def kos(self, ilanlar, logo, adres=None, **kw):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        docs = Path(tmp.name)
        with mock.patch.object(site_uret, '_logo_png', side_effect=logo), \
                mock.patch.object(site_uret, '_logo_yerelde', return_value=False), \
                mock.patch.object(site_uret, '_onbellekte', return_value=False), \
                mock.patch.object(site_uret, '_logo_adresi', side_effect=adres or (lambda i: 'https://x/logo.png')):
            sonuc = gorselleri_uret(ilanlar, docs, SIMDI, **kw)
        return docs, sonuc

    def test_kart_ve_logo_uretilir_ayni_kurum_bir_logo(self):
        cagrilar = []

        def logo(item):
            cagrilar.append(item['kurum'])
            return png((200, 200))
        ilanlar = [ilan(U1, 'Ankara Belediyesi'), ilan(U2, 'Ankara Belediyesi'), ilan(U3, 'İzmir Belediyesi')]
        docs, sonuc = self.kos(ilanlar, logo)
        self.assertEqual(set(sonuc), {U1, U2, U3})
        self.assertEqual(len(cagrilar), 2)  # kurum başına tek indirme
        self.assertEqual(sonuc[U1]['logo'], sonuc[U2]['logo'])
        self.assertNotEqual(sonuc[U1]['logo'], sonuc[U3]['logo'])
        kart = docs / sonuc[U1]['kart']
        self.assertTrue(kart.is_file())
        with Image.open(kart) as im:
            self.assertEqual(im.format, 'WEBP')
            self.assertEqual(im.width, 720)
        self.assertLess(kart.stat().st_size, 120_000)
        with Image.open(docs / sonuc[U1]['logo']) as im:
            self.assertEqual(im.size, (128, 128))
        self.assertEqual(len(list((docs / 'ilan' / 'logo').glob('*.webp'))), 2)

    def test_logo_hatasinda_derleme_dusmez_alan_yazilmaz(self):
        def logo(item):
            raise RuntimeError('ağ yok')
        docs, sonuc = self.kos([ilan(U1, 'Ankara Belediyesi')], logo)
        self.assertIn('kart', sonuc[U1])
        self.assertNotIn('logo', sonuc[U1])
        self.assertEqual(list((docs / 'ilan' / 'logo').glob('*')), [])

    def test_kart_hatasinda_ilan_gorselsiz_kalir(self):
        with mock.patch.object(site_uret, '_kart_png', side_effect=ValueError('bozuk')):
            docs, sonuc = self.kos([ilan(U1, 'Ankara Belediyesi')], lambda i: None)
        self.assertNotIn(U1, sonuc)

    def test_gecmis_iptal_akademik_atlanir(self):
        ilanlar = [ilan(U1, 'A Belediyesi', son_tarih='2026-10-01'), ilan(U2, 'B Belediyesi', iptal_edildi=True),
                   ilan(U3, 'C Üniversitesi', baslik='Öğretim Görevlisi alımı', kategori='akademik')]
        docs, sonuc = self.kos(ilanlar, lambda i: None)
        self.assertEqual(sonuc.get(U1), None)
        self.assertEqual(sonuc.get(U2), None)

    def test_adressiz_kurumlar_butceyi_harcamaz(self):
        uuidler = ['%08d-1111-4111-8111-111111111111' % n for n in range(11)]
        ilanlar = [ilan(u, f'Kurum{n} Belediyesi') for n, u in enumerate(uuidler)]
        cagrilar = []

        def logo(item):
            cagrilar.append(item['kurum'])
            return png()
        docs, sonuc = self.kos(ilanlar, logo, adres=lambda i: 'https://x/l.png' if i['kurum'] == 'Kurum10 Belediyesi' else None)
        self.assertEqual(cagrilar, ['Kurum10 Belediyesi'])
        self.assertIn('logo', sonuc[uuidler[10]])

    def test_indirme_siniri(self):
        ilanlar = [ilan(U1, 'A Belediyesi'), ilan(U2, 'B Belediyesi'), ilan(U3, 'C Belediyesi')]
        cagrilar = []

        def logo(item):
            cagrilar.append(1)
            return png()
        docs, sonuc = self.kos(ilanlar, logo, en_cok_indirme=1)
        self.assertEqual(len(cagrilar), 1)
        self.assertEqual(sum('logo' in v for v in sonuc.values()), 1)
        self.assertEqual(len(sonuc), 3)

    def test_detay_sayfasi_og_image_ve_gorsel(self):
        g = {'kart': f'ilan/kart/{U1}.webp', 'logo': 'ilan/logo/abc.webp', 'kart_yukseklik': 900}
        html = detail_page(ilan(U1, 'Ankara Belediyesi'), g)[1]
        self.assertIn(f'<meta property="og:image" content="{site_uret.BASE}ilan/kart/{U1}.webp">', html)
        self.assertIn('og:image:height', html)
        self.assertNotIn('detail-card-img', html)  # kart yalnız paylaşım görseli (og:image); sayfada büyük fotoğraf bandı kullanılır
        self.assertIn('class="detail-logo" src="../../ilan/logo/abc.webp" alt=""', html)
        yok = detail_page(ilan(U1, 'Ankara Belediyesi'))[1]
        self.assertNotIn('og:image', yok)
        self.assertNotIn('detail-visual', yok)

    def test_main_gorseller_json_yazar(self):
        with tempfile.TemporaryDirectory() as t:
            kok = Path(t)
            (kok / 'docs').mkdir()
            (kok / 'docs' / 'ilanlar.json').write_text(json.dumps({'ilanlar': [ilan(U1, 'Ankara Belediyesi')]}), encoding='utf-8')
            with mock.patch.object(site_uret, 'ROOT', kok), mock.patch.object(site_uret, '_logo_png', return_value=png()), \
                    mock.patch.object(site_uret, '_logo_yerelde', return_value=True), \
                    mock.patch('sosyal_paylasim.uret', side_effect=RuntimeError('atla')):
                site_uret.main()
            veri = json.loads((kok / 'docs' / 'ilan' / 'gorseller.json').read_text(encoding='utf-8'))
            self.assertIn(U1, veri)
            self.assertTrue(veri[U1]['logo'].startswith('ilan/logo/'))
            sayfa = (kok / 'docs' / 'ilan' / U1 / 'index.html').read_text(encoding='utf-8')
            self.assertIn('og:image', sayfa)


if __name__ == '__main__':
    unittest.main()
