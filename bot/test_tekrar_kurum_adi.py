import json
import unittest
from pathlib import Path

import ilan_bot
import kopya
import kurum_sayfasi as ks

KK = {'id': 'https://kariyerkapisi.gov.tr/IlanDetay?i=0f54adef-6e76-4b95-b503-03f415523085', 'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=0f54adef-6e76-4b95-b503-03f415523085',
      'baslik': 'TÜRKİYE CUMHURİYETİ DEVLET DEMİRYOLLARI TAŞIMACILIK ANONİM ŞİRKETİ GENEL MÜDÜRLÜĞÜ - 166 SÜREKLİ İŞÇİ İSTİHDAMI',
      'kurum': 'TÜRKİYE CUMHURİYETİ DEVLET DEMİRYOLLARI TAŞIMACILIK ANONİM ŞİRKETİ GENEL MÜDÜRLÜĞÜ', 'kadro': '',
      'son_tarih': '2026-10-26', 'ilk_gorulme': '2026-10-21T08:14:47+03:00'}
SBB = {'id': 'sbb-9eb67dc94a240ed678694f80', 'link': 'https://kamuilan.sbb.gov.tr/', 'kaynak_turu': 'sbb',
       'baslik': 'DEVLET DEMİRYOLLARI TAŞIMACILIK A.Ş GENEL MÜDÜRLÜĞÜ - 166 SüREKLİ İŞÇİ ALACAK',
       'kurum': 'DEVLET DEMİRYOLLARI TAŞIMACILIK A.Ş GENEL MÜDÜRLÜĞÜ', 'kadro': '166 SüREKLİ İŞÇİ ALACAK',
       'son_tarih': '2026-10-26', 'ilk_gorulme': '2026-10-21T01:11:37+03:00'}


class KurumYazimFarki(unittest.TestCase):
    def test_telegram_tekrar_denetimi_ayni_ilan_der(self):
        self.assertTrue(ilan_bot.ayni_ilan_mi(SBB, KK))

    def test_site_kopyasi_birlestirilir(self):
        sonuc = kopya.kopya_bul([SBB, KK])
        self.assertEqual(sonuc['kopya_of'].get(KK['id']), SBB['id'])

    def test_farkli_kurumlar_karismaz(self):
        baska = dict(KK, id='x', kurum='TÜRKİYE CUMHURİYETİ ZİRAAT BANKASI ANONİM ŞİRKETİ GENEL MÜDÜRLÜĞÜ',
                     baslik='TÜRKİYE CUMHURİYETİ ZİRAAT BANKASI ANONİM ŞİRKETİ GENEL MÜDÜRLÜĞÜ - 166 SÜREKLİ İŞÇİ İSTİHDAMI')
        self.assertFalse(ilan_bot.ayni_ilan_mi(SBB, baska))

    def test_anonim_sirket_eki_yazimi(self):
        self.assertTrue(ks.kurum_adi('DEVLET DEMİRYOLLARI TAŞIMACILIK A.Ş GENEL MÜDÜRLÜĞÜ').count('A.Ş.') == 1)


if __name__ == '__main__':
    unittest.main()
