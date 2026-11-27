import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import kanca
import reels
import yayin_kapisi as yk
import ilan_bot

TR = timezone(timedelta(hours=3))
SIMDI = datetime(2026, 12, 2, 12, 30, tzinfo=TR)   # sabit gün; test sonucu çalıştığı güne bağlı değil


def ilan(n, puan, kurum='Örnek Belediyesi', bitis_gun=10):
    return {'id': f'i{n}', 'kurum': f'{kurum} {n}', 'baslik': f'{kurum} {n} memur alacak',
            'son_tarih': (SIMDI + timedelta(days=bitis_gun)).date().isoformat(),
            'kadro': '2 Memur', 'ogrenim': ['lisans'],
            'yz_kadrolar': [{'unvan': 'Memur', 'adet': 2, 'en_dusuk_puan': puan, 'puan_turu': 'P3'},
                            {'unvan': 'Mühendis', 'adet': 1, 'en_dusuk_puan': puan + 10, 'puan_turu': 'P3'}]}


def puan_dosyasi(kok, duzey, kayitlar, donem='2026/1'):
    (kok / 'puanlar').mkdir(parents=True, exist_ok=True)
    (kok / 'puanlar' / f'{duzey}.json').write_text(json.dumps({'donemler': {donem: kayitlar}}), encoding='utf-8')


def kayit(n, puan, unvan=None):
    return {'unvan': unvan or f'MEMUR {n}', 'kurum': f'ÖRNEK KURUMU {n}', 'il': 'ANKARA', 'min': puan, 'kontenjan': 1, 'kod': f'{n:04d}'}


class PuanSarti(unittest.TestCase):
    def test_en_dusuk_kadro_ve_gecersiz_puan_elenir(self):
        acik = [ilan(1, 65), ilan(2, 60), {'id': 'x', 'kurum': 'Y', 'yz_kadrolar': [{'unvan': 'A', 'en_dusuk_puan': None}]},
                {'id': 'z', 'kurum': 'Z', 'yz_kadrolar': [{'unvan': 'A', 'en_dusuk_puan': 170}]}]
        s = kanca.puan_sartlari(acik, SIMDI)
        self.assertEqual([(p, i['id'], ad) for p, i, ad in s], [(60, 'i2', 'Memur'), (65, 'i1', 'Memur')])

    def test_puanla_az_ilanda_yok_yeterince_ilanda_var(self):
        reels.palet_sec('kagit')
        self.assertIsNone(kanca.puanla_konusu([ilan(n, 60 + n) for n in range(3)], SIMDI))
        k = kanca.puanla_konusu([ilan(n, 60 + n) for n in range(6)], SIMDI)
        self.assertEqual(k['seri'], 'puanla')
        self.assertIn('60', k['baslik'])
        self.assertIn("85-90 şart değil", k['giris'])
        self.assertEqual(len(k['ilanlar']), 6)
        self.assertGreaterEqual(len(k['sahneler']), 4)   # kapak + 2 liste + kapanış

    def test_puan_siniri_ustu_girmez(self):
        reels.palet_sec('kagit')
        self.assertIsNone(kanca.puanla_konusu([ilan(n, 75) for n in range(6)], SIMDI))


class PuanDizileri(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.docs = Path(self.t.name)
        reels.palet_sec('kagit')

    def tearDown(self):
        self.t.cleanup()

    def test_atanan_en_dusuk_taban(self):
        puan_dosyasi(self.docs, 'onlisans', [kayit(n, 64.45 + n) for n in range(10)])
        k = kanca.atanan_konusu([], SIMDI, self.docs, 'onlisans')
        self.assertTrue(k['baslik'].startswith('Önlisansta 64,45 ile atanan var'))
        self.assertIn('64,45', k['giris'])

    def test_atanan_veri_azsa_yok(self):
        puan_dosyasi(self.docs, 'onlisans', [kayit(n, 64 + n) for n in range(5)])
        self.assertIsNone(kanca.atanan_konusu([], SIMDI, self.docs, 'onlisans'))

    def test_aralik_yalniz_aralikta_kalanlar(self):
        puan_dosyasi(self.docs, 'lisans', [kayit(n, 70 + n * 0.4) for n in range(12)] + [kayit(99, 80)])
        k = kanca.aralik_konusu([], SIMDI, self.docs, ('lisans', 70))
        self.assertIn('70-75', k['baslik'])
        self.assertIn('12 yerleşme', k['giris'])
        self.assertFalse(any('Memur 99' in s for s in k['satirlar']))   # 80 puanlı kayıt aralık dışında

    def test_konu_ayni_gun_ayni_diziyi_tekrarlamaz_ve_yakini_atlar(self):
        puan_dosyasi(self.docs, 'lisans', [kayit(n, 70 + n * 0.4) for n in range(12)])
        for d in ('onlisans', 'ortaogretim'):
            puan_dosyasi(self.docs, d, [kayit(n, 60 + n) for n in range(10)])
        acik = [ilan(n, 60 + n) for n in range(6)]
        ilk = kanca.konu('sabah', acik, SIMDI, [], self.docs)
        gecmis = [{'anahtar': ilk['anahtar'], 'zaman': SIMDI.isoformat(), 'vakit': 'sabah'}]
        ikinci = kanca.konu('aksam', acik, SIMDI.replace(hour=21), gecmis, self.docs)
        self.assertNotEqual(ilk['seri'], ikinci['seri'])
        self.assertIn(ilk['palet'], reels.PALET_SIRASI)

    def test_hic_veri_yoksa_none(self):
        self.assertIsNone(kanca.konu('sabah', [], SIMDI, [], self.docs))


class YayinKapisi(unittest.TestCase):
    def test_pencere_disinda_izin_yok(self):
        self.assertFalse(yk.karar('sabah', SIMDI.replace(hour=4, minute=10), [])[0])   # 27 Kasım'daki gecikmiş öğle videosu
        self.assertTrue(yk.karar('sabah', SIMDI, [])[0])
        self.assertFalse(yk.karar('ozel', SIMDI.replace(hour=2, minute=38), [])[0])
        self.assertTrue(yk.karar('aksam', SIMDI.replace(hour=21), [])[0])

    def test_gunde_bir_kez(self):
        g = [{'vakit': 'sabah', 'zaman': SIMDI.replace(hour=12, minute=31).isoformat()}]
        self.assertFalse(yk.karar('sabah', SIMDI.replace(hour=13), g)[0])
        self.assertTrue(yk.karar('aksam', SIMDI.replace(hour=21), g)[0])

    def test_elle_baslatilan_kapiya_takilmaz(self):
        self.assertTrue(yk.karar('sabah', SIMDI.replace(hour=3), [], elle=True)[0])


class TelegramAralik(unittest.TestCase):
    CFG = {'telegram_aralikli': True}

    def zaman(self, saat, dk=0):
        return SIMDI.replace(hour=saat, minute=dk)

    def test_gece_ilan_yok(self):
        for saat in (23, 0, 3, 7):
            self.assertEqual(ilan_bot.ilan_hakki(self.CFG, self.zaman(saat, 30), None, 3), 0)
        self.assertEqual(ilan_bot.ilan_hakki(self.CFG, self.zaman(8), None, 3), 1)

    def test_aralik_dolmadan_ikinci_ilan_yok(self):
        son = self.zaman(10).isoformat()
        self.assertEqual(ilan_bot.ilan_hakki(self.CFG, self.zaman(10, 30), son, 3), 0)    # normal saat: 60 dk
        self.assertEqual(ilan_bot.ilan_hakki(self.CFG, self.zaman(11), son, 3), 1)
        son = self.zaman(19).isoformat()
        self.assertEqual(ilan_bot.ilan_hakki(self.CFG, self.zaman(19, 30), son, 3), 1)    # yoğun saat: 30 dk

    def test_birikmede_aralik_kisalir(self):
        son = self.zaman(10).isoformat()
        self.assertEqual(ilan_bot.ilan_hakki(self.CFG, self.zaman(10, 30), son, 11), 1)

    def test_ayar_ile_gece_degisir(self):
        self.assertEqual(ilan_bot.ilan_hakki({'telegram_gece': [22, 9]}, self.zaman(8, 30), None, 1), 0)


if __name__ == '__main__':
    unittest.main()
