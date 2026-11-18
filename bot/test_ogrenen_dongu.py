"""Öğrenen döngü (18 Kasım 2026): soru cümlesi, video süresi ve haftalık dizi ölçülür; zayıf soru seçilmez, ajan karnesi."""
import unittest
from unittest import mock

import sosyal_ajan as sa
import sosyal_istatistik as si
import sosyal_motor as sm


def _kayit(n, soru, izlenme, sure=14.0, ms=None, tur='son_gun'):
    ig = {'views': izlenme}
    if ms is not None:
        ig['avg_watch_ms'] = ms
    return {'zaman': f'2026-11-{n + 1:02d}T12:30:00+03:00', 'tur': tur, 'soru': soru, 'sure': sure, 'ig': ig}


class SoruSecimi(unittest.TestCase):
    ADAY = ['A? 👇', 'B? 👇', 'C? 👇']

    def test_agirlik_yoksa_eski_tohum_secimi(self):
        self.assertEqual(sm.soru_sec(self.ADAY, None, 'x'), sm._sec(self.ADAY, 'x'))

    def test_olculmemis_cumle_once_denenir(self):
        secilen = {sm.soru_sec(self.ADAY, {'A? 👇': 3, 'B? 👇': 1}, str(n)) for n in range(30)}
        self.assertEqual(secilen, {'C? 👇'})

    def test_zayif_cumle_secilmez_en_iyi_cogunlukla_secilir(self):
        ag = {'A? 👇': 6.0, 'B? 👇': 1.0, 'C? 👇': -9.0}
        secimler = [sm.soru_sec(self.ADAY, ag, str(n)) for n in range(300)]
        self.assertNotIn('C? 👇', secimler)
        self.assertGreater(secimler.count('A? 👇'), secimler.count('B? 👇'))
        self.assertIn('B? 👇', secimler)   # öğrenme sürer: ikinci aday da arada denenir

    def test_hepsi_zayifsa_yine_bir_cumle_doner(self):
        self.assertIn(sm.soru_sec(self.ADAY, {s: -12.0 for s in self.ADAY}, 'x'), self.ADAY)

    def test_metin_olustur_kullanilan_soruyu_doner(self):
        konu = {'tur': 'son_gun', 'baslik': 'B', 'giris': 'g', 'satirlar': [], 'etiketler': []}
        with mock.patch('sosyal_ajan.sorular', return_value=None):
            metin = sm.metin_olustur(konu, 'sabah', sm.datetime(2026, 11, 18, 12, tzinfo=sm.TR),
                                     {'soru': {s: 0.0 for s in sm.SORULAR['son_gun'][:1]}})
        self.assertIn(metin['soru'], sm.SORULAR['son_gun'])
        self.assertIn(metin['soru'], metin['aciklama'])


class Olcum(unittest.TestCase):
    def test_tamamlama_ve_sure_bandi(self):
        self.assertEqual(si.tamamlama({'sure': 10, 'ig': {'avg_watch_ms': 5000}}), 0.5)
        self.assertEqual(si.tamamlama({'sure': 10, 'ig': {'avg_watch_ms': 40000}}), 1.5)   # döngüde üst sınır
        self.assertIsNone(si.tamamlama({'sure': None, 'ig': {'avg_watch_ms': 5000}}))
        self.assertIsNone(si.tamamlama({'sure': 10, 'ig': {}}))
        self.assertEqual([si.sure_bandi(x) for x in (9, 12, 16, 17, None)], ['kisa', 'orta', 'orta', 'uzun', None])

    def test_agirliklar_soru_adet_ve_izlenme_orani(self):
        gecmis = [_kayit(n, 'İyi? 👇', 900, ms=9000) for n in range(4)] + \
                 [_kayit(n + 4, 'Kötü? 👇', 100, ms=2800) for n in range(4)]
        a = si.agirliklar(gecmis)
        self.assertGreater(a['soru']['İyi? 👇'], 0)
        self.assertLess(a['soru']['Kötü? 👇'], 0)
        self.assertEqual(a['adet']['soru'], {'İyi? 👇': 4, 'Kötü? 👇': 4})
        self.assertEqual(a['tamamlama']['soru']['İyi? 👇'], round(9000 / 14000, 3))
        self.assertIn('orta', a['sure_bandi'])
        self.assertIn('tamamlama_genel', a)
        for eski in ('tur', 'muzik', 'vakit', 'palet'):   # eski alanlar yerinde
            self.assertIn(eski, a)

    def test_az_olcumde_agirlik_yok(self):
        a = si.agirliklar([_kayit(0, 'S? 👇', 100)])
        self.assertEqual(a['soru'], {})
        self.assertEqual(a['olculen'], 1)

    def test_izlenme_suresi_okunamazsa_none(self):
        with mock.patch.object(si, '_istek', side_effect=si.YayinHatasi('desteklenmiyor')):
            self.assertIsNone(si.izlenme_suresi_al('1', 'k'))
        with mock.patch.object(si, '_istek', return_value={'data': [{'name': si.SURE_OLCUTU, 'values': [{'value': 4200}]}]}):
            self.assertEqual(si.izlenme_suresi_al('1', 'k'), 4200)


class AjanKarnesi(unittest.TestCase):
    def test_karne_zayifi_once_ve_degistir_isareti(self):
        gecmis = [_kayit(n, 'İyi? 👇', 900) for n in range(4)] + [_kayit(n + 4, 'Kötü? 👇', 100) for n in range(4)] \
                 + [_kayit(9, 'Yeni? 👇', 300)]
        a = si.agirliklar(gecmis)
        karne = sa.soru_karnesi(gecmis, a)
        self.assertEqual(karne[0]['soru'], 'Kötü? 👇')
        self.assertTrue(karne[0]['degistir'])
        self.assertEqual(karne[0]['turler'], ['son_gun'])
        iyi = next(k for k in karne if k['soru'] == 'İyi? 👇')
        self.assertFalse(iyi['degistir'])
        yeni = next(k for k in karne if k['soru'] == 'Yeni? 👇')
        self.assertFalse(yeni['degistir'])   # tek ölçümle değiştirilmez

    def test_karne_istatistiksiz_bos_degil(self):
        karne = sa.soru_karnesi([_kayit(0, 'S? 👇', 1)], {})
        self.assertEqual(karne[0]['olcum'], 0)
        self.assertFalse(karne[0]['degistir'])


if __name__ == '__main__':
    unittest.main()
