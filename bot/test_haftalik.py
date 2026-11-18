"""Haftalık veri dizisi: veri hesapları, cılız dizinin atlanması, dizi sırası ve kota, ilk kare = kapak, açıklama metni.
Tarihler hep SIMDI'ye göredir (en yakın geçmiş pazar 19:00); sabit yakın tarih yok."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import haftalik as h
import reels
from kart_tasarimlari import TR

_simdi = datetime.now(TR)
SIMDI = (_simdi - timedelta(days=(_simdi.weekday() - 6) % 7)).replace(hour=19, minute=0, second=0, microsecond=0)


def ilan(kimlik, kurum='Deneme Kurumu Başkanlığı', kadro='Toplam 12 kişi — 10 Memur • 2 Tekniker', gorulme=1, ogrenim=('lisans',), **ek):
    return {'id': kimlik, 'kurum': kurum, 'kadro': kadro, 'ogrenim': list(ogrenim), 'kpss': 'kpss', 'iller': ['Ankara'],
            'baslik': f'{kurum} personel alımı', 'son_tarih': (SIMDI + timedelta(days=20)).date().isoformat(),
            'ilk_gorulme': (SIMDI - timedelta(days=gorulme)).isoformat(timespec='seconds'), **ek}


def puan(unvan, mn, kurum='DENEME KURUMU', il='ANKARA', yerlesen=1):
    return {'kod': f'{unvan}{mn}', 'kurum': kurum, 'il': il, 'unvan': unvan, 'kontenjan': yerlesen, 'yerlesen': yerlesen, 'min': mn, 'max': mn}


def docs_yaz(klasor, kayitlar, duzey='lisans', donem='2026-1'):
    (Path(klasor) / 'puanlar').mkdir(parents=True, exist_ok=True)
    (Path(klasor) / 'puanlar' / f'{duzey}.json').write_text(json.dumps({'donemler': {donem: kayitlar}}, ensure_ascii=False), encoding='utf-8')


KURUMLAR = [ilan('a', 'Alfa Kurumu', 'Toplam 30 kişi — 30 Memur'), ilan('b', 'Beta Kurumu', 'Toplam 20 kişi — 20 Memur', ogrenim=('onlisans',)),
            ilan('c', 'Gama Kurumu', 'Toplam 10 kişi — 10 Memur', ogrenim=('ortaogretim', 'lisans')),
            ilan('d', 'Delta Kurumu', 'Toplam 5 kişi — 5 Memur')]


class VeriTest(unittest.TestCase):
    def test_hafta_ilanlari(self):
        acik = [ilan('yeni', gorulme=2), ilan('eski', gorulme=8), ilan('ic', baslik='Görevde yükselme sınavı ilanı'),
                ilan('gelecek', gorulme=-1), ilan('buyuk', kadro='Toplam 90 kişi — 90 Memur')]
        self.assertEqual([i['id'] for i in h.hafta_ilanlari(acik, SIMDI)], ['buyuk', 'yeni'])   # kurum içi ve 7 günden eski yok

    def test_kurum_siralamasi(self):
        acik = [ilan('1', 'Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)', 'Toplam 13 kişi — 13 Uzman'),
                ilan('2', 'Afet ve Acil Durum Yönetimi Başkanlığı', 'Toplam 7 kişi — 7 Uzman'),
                ilan('3', 'Savunma Sanayii Başkanlığı', 'Toplam 26 kişi — 26 Uzman'),
                ilan('4', 'Bilinmeyen Kurum', 'Mühendis')]   # kadro sayısı yok: toplama girmez
        sira = h.kurum_siralamasi(acik, SIMDI)
        self.assertEqual([(g['kadro'], g['ilan']) for g in sira], [(26, 1), (20, 2)])
        self.assertTrue(sira[1]['kurum'].startswith('Afet ve Acil Durum'))

    def test_duzey_dagilimi(self):
        dagilim, ortak = h.duzey_dagilimi(KURUMLAR, SIMDI)
        self.assertEqual([(x['ad'], x['ilan'], x['kadro']) for x in dagilim], [('Lise', 1, 10), ('Önlisans', 1, 20), ('Lisans', 3, 45)])
        self.assertTrue(ortak)                                  # Gama hem lise hem lisans
        self.assertEqual(dagilim[2]['en_buyuk']['id'], 'a')
        self.assertFalse(h.duzey_dagilimi(KURUMLAR[:2], SIMDI)[1])

    def test_puanlar(self):
        kayit = [puan('MEMUR', 70.5), puan('MEMUR', 66.1), puan('ŞOFÖR', 68.2), puan('TEKNİKER', 74.9), puan('UZMAN', 75.0)]
        self.assertEqual([(r['unvan'], r['min']) for r in h.en_dusukler(kayit, 3)], [('MEMUR', 66.1), ('ŞOFÖR', 68.2), ('TEKNİKER', 74.9)])
        self.assertEqual([r['min'] for r in h.puan_bandi(kayit, 70, 75)], [70.5, 74.9])   # üst sınır dahil değil
        self.assertEqual(h.puan_yaz(66.10452), '66,10')
        self.assertEqual(h._kisa('GAP BÖLGE KALKINMA İDARESİ BAŞKANLIĞI'), 'GAP Bölge Kalkınma İdaresi')

    def test_son_gun_gruplari(self):
        acik = [ilan('x', son_tarih=(SIMDI + timedelta(days=1)).date().isoformat()),
                ilan('y', son_tarih=(SIMDI + timedelta(days=1)).date().isoformat(), kadro='Toplam 40 kişi — 40 Memur'),
                ilan('z', son_tarih=(SIMDI + timedelta(days=9)).date().isoformat())]
        gruplar = h.son_gun_gruplari(acik, SIMDI)
        self.assertEqual([(g, [i['id'] for i in v]) for g, v in gruplar], [((SIMDI + timedelta(days=1)).date(), ['y', 'x'])])

    def test_hafta_araligi(self):
        self.assertEqual(h.hafta_araligi(datetime(2099, 3, 3, tzinfo=TR)), '25 Şubat – 3 Mart')
        self.assertEqual(h.hafta_araligi(datetime(2099, 3, 20, tzinfo=TR)), '14–20 Mart')


class DiziTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.docs = Path(self.gecici.name)
        docs_yaz(self.docs, [puan(f'UNVAN {n}', 60 + n) for n in range(10)])

    def tearDown(self):
        self.gecici.cleanup()

    def test_cilız_dizi_atlanir(self):
        self.assertIsNone(h.seri_konusu('kurum', KURUMLAR[:2], SIMDI, self.docs))            # 2 kurum yetmez
        self.assertEqual(h.seri_konusu('kurum', KURUMLAR[:3], SIMDI, self.docs)['anahtar'], f'haftalik:kurum:{h.hafta_kodu(SIMDI)}')
        yalniz_lisans = [ilan(str(n)) for n in range(6)]
        self.assertIsNone(h.seri_konusu('duzey', yalniz_lisans, SIMDI, self.docs))           # tek düzey yetmez
        self.assertIsNone(h.seri_konusu('duzey', KURUMLAR[:3], SIMDI, self.docs))            # 3 ilan yetmez
        self.assertIsNotNone(h.seri_konusu('duzey', KURUMLAR, SIMDI, self.docs))
        az = Path(self.gecici.name) / 'az'
        docs_yaz(az, [puan(f'UNVAN {n}', 60 + n) for n in range(5)])
        self.assertIsNone(h.seri_konusu('dusuk', [], SIMDI, az))                              # 8 farklı unvan yok
        self.assertIsNone(h.seri_konusu('kpsssiz', KURUMLAR, SIMDI, self.docs))              # güvenilir veri yok: dizi yok

    def test_dizi_sirasi_ve_siniri(self):
        def kayit(seri, gun):
            return {'tur': 'haftalik', 'anahtar': f'haftalik:{seri}:x', 'zaman': (SIMDI - timedelta(days=gun)).isoformat(timespec='seconds')}
        self.assertEqual(h.haftalik_konu(KURUMLAR, SIMDI, [], self.docs)['seri'], 'kurum')
        self.assertEqual(h.haftalik_konu(KURUMLAR, SIMDI, [kayit('kurum', 7)], self.docs)['seri'], 'duzey')
        self.assertEqual(h.haftalik_konu(KURUMLAR, SIMDI, [kayit('duzey', 7)], self.docs)['seri'], 'dusuk')
        self.assertEqual(h.haftalik_konu(KURUMLAR, SIMDI, [kayit('dusuk', 7)], self.docs)['seri'], 'kurum')
        self.assertEqual(h.haftalik_konu(KURUMLAR[:3], SIMDI, [kayit('kurum', 7)], self.docs)['seri'], 'dusuk')   # düzey cılız: atlanır
        self.assertIsNone(h.haftalik_konu(KURUMLAR, SIMDI, [kayit('kurum', 2)], self.docs))                       # haftada bir
        bugun = [{'tur': 'ilan', 'zaman': SIMDI.replace(hour=n).isoformat(timespec='seconds')} for n in (10, 12, 15, 18)]
        self.assertIsNotNone(h.haftalik_konu(KURUMLAR, SIMDI, bugun, self.docs))                                  # 4 + bu + akşam = 6
        self.assertIsNone(h.haftalik_konu(KURUMLAR, SIMDI, bugun + bugun[:1], self.docs))                         # akşam kotası kalmaz
        self.assertIsNone(h.haftalik_konu([], SIMDI, [], Path(self.gecici.name) / 'yok'))                         # hiçbir dizi yetmez

    def test_dusuk_duzey_doner(self):
        docs_yaz(self.docs, [puan(f'ÖNLİSANS {n}', 61 + n) for n in range(9)], 'onlisans')
        ilk = h.seri_konusu('dusuk', [], SIMDI, self.docs)
        self.assertEqual(ilk['anahtar'], 'haftalik:dusuk:lisans:2026-1')
        gecmis = [{'tur': 'haftalik', 'anahtar': ilk['anahtar'], 'zaman': (SIMDI - timedelta(days=21)).isoformat()}]
        self.assertEqual(h.seri_konusu('dusuk', [], SIMDI, self.docs, gecmis=gecmis)['anahtar'], 'haftalik:dusuk:onlisans:2026-1')

    def test_ilk_kare_kapaktir(self):
        govde = (0, reels.UST, reels.VW, reels.VH)
        for seri in h.SERILER:
            konu = h.seri_konusu(seri, KURUMLAR, SIMDI, self.docs)
            sahneler = konu['sahneler']
            self.assertTrue(sahneler[-1].son, seri)
            self.assertLessEqual(reels.video_suresi(sahneler), 20, seri)
            ilk = next(reels.kareler(sahneler))
            oturmus = reels.kare(sahneler, sahneler[0].sure - reels.CIKIS - 0.05)
            self.assertNotEqual(ilk.crop(govde).tobytes(), reels.zemin().crop(govde).tobytes(), seri)
            self.assertEqual(ilk.crop(govde).tobytes(), oturmus.crop(govde).tobytes(), seri)

    def test_aciklama_ve_gecmis(self):
        import sosyal_motor as sm
        konu = h.seri_konusu('kurum', KURUMLAR, SIMDI, self.docs)
        metin = sm.metin_olustur(konu, 'haftalik', SIMDI)
        self.assertLessEqual(len(metin['etiketler']), 5)
        ilk_satir = metin['aciklama'].splitlines()[0]
        self.assertIn('65 kadro', ilk_satir)                    # kanca satırında asıl sayı
        self.assertIn('@kpsstercihi', metin['aciklama'])
        self.assertIn('profilde', metin['aciklama'])
        self.assertNotIn('takipte kalırsan', metin['aciklama'])
        self.assertIn('• Alfa Kurumu: 30 kadro', metin['aciklama'])
        eski = reels.muzik_yolu
        reels.muzik_yolu = lambda tur, *a, **k: (None, 0.0)
        try:
            with tempfile.TemporaryDirectory() as g:
                sm.sablon_uret(konu, 'haftalik', Path(g) / 'c', SIMDI, [], Path(g) / 'gecmis.json', video=False, palet='bordo')
                gecmis = json.loads((Path(g) / 'gecmis.json').read_text(encoding='utf-8'))
                kayit = json.loads((Path(g) / 'c' / 'paylasim.json').read_text(encoding='utf-8'))
        finally:
            reels.muzik_yolu = eski
        self.assertEqual((gecmis[-1]['tur'], gecmis[-1]['anahtar'], gecmis[-1]['palet']), ('haftalik', konu['anahtar'], 'bordo'))
        self.assertEqual((kayit['tur'], kayit['vakit']), ('haftalik', 'haftalik'))


if __name__ == '__main__':
    unittest.main()
