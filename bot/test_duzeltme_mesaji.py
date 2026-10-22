import unittest

import ilan_bot
from ek_kaynaklar import notice


class DuzeltmeMesaji(unittest.TestCase):
    def test_yazim_hatali_duzeltme_basligi_duyuru_sayilir(self):
        self.assertTrue(notice('SARIİDRİS BELEDİYE BAŞKANLIĞI - DÜLETME İLANI'))
        self.assertTrue(notice('RİZE BELEDİYESİ TEKNİKER ALIMI DÜZELTME İLANI'))
        self.assertTrue(notice('X BELEDİYESİ MEMUR ALIMI İPTAL İLANI'))
        self.assertFalse(notice('X BELEDİYESİ 2 ZABITA MEMURU ALIM İLANI'))

    def test_mesaj_ilan_adiyla(self):
        orijinal = {'id': 'k1', 'kurum': 'GALATASARAY ÜNİVERSİTESİ REKTÖRLÜĞÜ', 'kadro': '1 Yazılım Geliştirme Uzmanı',
                    'baslik': 'GALATASARAY ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ BİLİŞİM PERSONELİ ALIM İLANI'}
        metin = ilan_bot.duzeltme_metni({'duzeltme_degisen': 'tarih', 'duzeltme_yeni_tarih': '2026-11-10'}, orijinal)
        ilk, ikinci = metin.split('\n')
        self.assertEqual(ilk, '📝 <b>Galatasaray Üniversitesi Yazılım Geliştirme Uzmanı ilanı hakkında düzeltme yayınlanmıştır.</b>')
        self.assertIn('Yeni son başvuru', ikinci)
        self.assertNotIn('\n', ilan_bot.duzeltme_metni({}, orijinal))   # diğer düzeltmelerde tek satır


if __name__ == '__main__':
    unittest.main()
