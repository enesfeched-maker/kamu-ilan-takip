import unittest
from unittest import mock

import ilan_bot
import site_uret
import yayin_tamlik

KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=3d77e559-3036-4ce5-8131-0d7adae39f48'


def kayit(**ek):
    i = {'id': KK, 'baslik': 'TÜRK AKREDİTASYON KURUMU - KORUMA VE GÜVENLİK GÖREVLİSİ', 'kurum': 'TÜRK AKREDİTASYON KURUMU',
         'son_tarih': '', 'ilk_gorulme': yayin_tamlik.BASLANGIC + 'T00:35:18+03:00'}
    i.update(ek)
    return i


class YayinTamlikTest(unittest.TestCase):
    def test_ayrintisi_inmemis_kk_kaydi_eksik(self):
        self.assertTrue(yayin_tamlik.eksik(kayit()))

    def test_ayrinti_var_ama_tarih_yok_eksik(self):
        self.assertIn('son başvuru', yayin_tamlik.eksik(kayit(kk_detay_surumu=3, sartlar=[{'metin': 'x'}])))

    def test_tam_kayit_yayinlanir(self):
        self.assertEqual('', yayin_tamlik.eksik(kayit(kk_detay_surumu=3, son_tarih='2099-12-07')))

    def test_duyuru_ve_eski_kayit_etkilenmez(self):
        self.assertEqual('', yayin_tamlik.eksik(kayit(duyuru_turu='İptal duyurusu')))
        self.assertEqual('', yayin_tamlik.eksik(kayit(ilk_gorulme='2026-09-22T17:46:21+03:00')))

    def test_sitede_eksik_kayit_yer_almaz(self):
        with mock.patch.object(site_uret, 'elle_kurallar', return_value=(set(), {})):
            kalan = site_uret.elle_uygula([kayit(), kayit(id='sbb-1', son_tarih='2099-12-07')])
        self.assertEqual(['sbb-1'], [i['id'] for i in kalan])

    def test_telegrama_eksik_kayit_gitmez_bekleme_suresi_dolsa_bile(self):
        hazir = ilan_bot.yayina_hazir([kayit(ilk_gorulme='2099-01-01T00:00:00+03:00')], logo_bul=lambda i: True, veri={})
        self.assertEqual([], hazir)

    def test_tarihsiz_sayfa_kapali_sinifi_almaz(self):
        from datetime import datetime
        h = site_uret.hero_html(kayit(kk_detay_surumu=3), None, None, datetime.now(site_uret.TR))
        self.assertIn('dh-son yok tarihsiz', h)


if __name__ == '__main__':
    unittest.main()
