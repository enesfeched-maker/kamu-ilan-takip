import contextlib
import io
import unittest
from datetime import datetime, timedelta

import ilan_bot
import duzeltme
import yz_isle
import kart_tasarimlari as kt
from yz_denetim import SURUM

TR = ilan_bot.TR
SIMDI = datetime(2026, 10, 20, 12, 0, tzinfo=TR)


class LogoYedegi(unittest.TestCase):
    def test_uc_saat_sonra_amblemle_gider(self):
        taze = dict(id='a', baslik='A', kurum='Doğanyol Belediye Başkanlığı', ilk_gorulme=(SIMDI - timedelta(hours=1)).isoformat())
        eski = dict(taze, id='b', ilk_gorulme=(SIMDI - timedelta(hours=4)).isoformat())
        with contextlib.redirect_stdout(io.StringIO()):
            kalan = ilan_bot.logolu_olanlar([taze, eski], logo_bul=lambda i: None, simdi_=SIMDI)
        self.assertEqual([i['id'] for i in kalan], ['b'])
        with contextlib.redirect_stdout(io.StringIO()):
            kalan = ilan_bot.logolu_olanlar([dict(taze, amblem_hemen=True)], logo_bul=lambda i: None, simdi_=SIMDI)
        self.assertEqual([i['id'] for i in kalan], ['a'])

    def test_unvan_beklemesi_1_saat(self):
        taze = {'ilk_gorulme': (SIMDI - timedelta(minutes=40)).isoformat()}
        eski = {'ilk_gorulme': (SIMDI - timedelta(hours=1, minutes=5)).isoformat()}
        self.assertFalse(ilan_bot.sure_doldu(taze, ilan_bot.UNVAN_BEKLEME, SIMDI))
        self.assertTrue(ilan_bot.sure_doldu(eski, ilan_bot.UNVAN_BEKLEME, SIMDI))
        self.assertFalse(ilan_bot.sure_doldu({}, ilan_bot.UNVAN_BEKLEME, SIMDI))   # bilinmiyorsa beklenir

    def test_amblem(self):
        self.assertEqual(kt.bas_harfler('Doğanyol Belediye Başkanlığı'), 'DB')
        self.assertEqual(kt.bas_harfler('Türkiye İş Kurumu Genel Müdürlüğü'), 'TİK')
        self.assertEqual(kt.bas_harfler('İl Sağlık Müdürlüğü'), 'S')
        self.assertTrue(ilan_bot.kurum_amblemi({'kurum': 'Hanak Belediyesi'}).startswith(b'\x89PNG'))


class TekSatir(unittest.TestCase):
    def test_kurum_kisi_etiket(self):
        ilan = {'baslik': 'Ankara Pursaklar Belediyesi Zabıta Memuru Alım İlanı', 'kurum': 'Ankara Pursaklar Belediyesi',
                'kadro': '5 Zabıta Memuru', 'yer': 'Ankara', 'son_tarih': '2099-10-23'}
        satir = ilan_bot.tek_satir(ilan)
        self.assertNotIn('\n', satir)
        self.assertTrue(satir.startswith('<b>'))
        self.assertIn('5 kişi', satir)
        self.assertIn('#Ankara', satir)


class SureUzatma(unittest.TestCase):
    def test_gemini_sure_uzatmasi_orijinale_baglanir(self):
        orijinal = {'id': 'o', 'baslik': 'Örnek Belediyesi Zabıta Memuru Alım İlanı', 'kurum': 'Örnek Belediyesi',
                    'kadro': '3 Zabıta Memuru', 'son_tarih': '2099-10-24', 'ilk_gorulme': '2099-10-10T10:00:00+03:00'}
        uzatma = {'id': 'u', 'baslik': 'Örnek Belediyesi Zabıta Memuru Alım İlanı', 'kurum': 'Örnek Belediyesi',
                  'son_tarih': '2099-11-05', 'ilk_gorulme': '2099-10-20T10:00:00+03:00'}
        veri = {'u': {'surum': SURUM, 'yz': {'duyuru_tipi': 'sure_uzatma', 'iptal_veya_duzeltme': True,
                                              'son_basvuru_tarihi': '2099-11-05'}}}
        self.assertTrue(yz_isle.sure_uzatma_isaretle(uzatma, veri))
        self.assertFalse(yz_isle.sure_uzatma_isaretle(orijinal, {}))
        ilanlar = [orijinal, uzatma]
        duzeltme.uygula(ilanlar, datetime(2099, 10, 20).date(), kopya_of={})
        self.assertEqual(uzatma.get('duzeltme_of'), 'o')
        self.assertEqual(uzatma.get('duzeltme_yeni_tarih'), '2099-11-05')
        self.assertEqual(orijinal['son_tarih'], '2099-11-05')
        karar = ilan_bot.duzeltme_karari(uzatma, ilanlar, {'o': 55}, {}, datetime(2099, 10, 20).date())
        self.assertEqual(karar['islem'], 'gonder')
        self.assertIn('Yeni son başvuru', ilan_bot.duyuru_metni(uzatma, True))


if __name__ == '__main__':
    unittest.main()
