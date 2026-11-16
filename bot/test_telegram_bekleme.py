"""16 Kasım 2026: Kariyer Kapısı ayrıntısı inmeden yapay zekâ ilanı 'okunamadı' saydı; süresi geçmiş kayıtlar sırada kaldı."""
import unittest
from datetime import date, timedelta

import ilan_bot
import yz_yerel


class KariyerKapisiAyrintiBeklemesi(unittest.TestCase):
    KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=31b4b404-05cb-4298-9460-1ab3b13b33e8'

    def test_ayrintisiz_kariyer_kapisi_okutulmaz(self):
        item = {'id': self.KK, 'baslik': 'ANADOLU ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIMI', 'kurum': 'ANADOLU ÜNİVERSİTESİ'}
        self.assertTrue(yz_yerel.kk_ayrinti_bekliyor(item))
        self.assertEqual(yz_yerel.metin_al(item, sbb_pdf=lambda i: None), ('', 'bekle'))

    def test_ayrintisi_inen_kariyer_kapisi_okunur(self):
        item = {'id': self.KK, 'baslik': 'ANADOLU ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIMI', 'kurum': 'ANADOLU ÜNİVERSİTESİ',
                'kk_detay_surumu': 3, 'kadro': '1 ÇEVRE MÜHENDİSİ',
                'sartlar': [{'kadro': 'ÇEVRE MÜHENDİSİ', 'metin': 'KPSSP3 puan türünden en az 60 almış olmak.'}]}
        self.assertFalse(yz_yerel.kk_ayrinti_bekliyor(item))
        metin, kaynak = yz_yerel.metin_al(item, sbb_pdf=lambda i: None)
        self.assertEqual(kaynak, 'metin')
        self.assertIn('KPSSP3', metin)

    def test_diger_kaynaklar_etkilenmez(self):
        self.assertFalse(yz_yerel.kk_ayrinti_bekliyor({'id': 'iskur-1297f2230bae0ab64bde59fd'}))
        self.assertFalse(yz_yerel.kk_ayrinti_bekliyor({'id': 'sbb-60d850a0c27b9b6af78a65a1'}))


class SuresiGecenSiradanDuser(unittest.TestCase):
    def test_kaynagi_okunamayan_suresi_gecmis_ilan_siradan_duser(self):
        gecmis = (date.today() - timedelta(days=10)).isoformat()
        i = {'id': 'sbb-eski', 'baslik': 'KIYI EMNİYETİ GENEL MÜDÜRLÜĞÜ - 3 SÜREKLİ İŞÇİ ALACAK', 'kurum': 'KIYI EMNİYETİ',
             'kaynak_turu': 'sbb', 'son_tarih': gecmis}
        bekleyen = {'sbb-eski'}
        sira = ilan_bot.telegram_sirasi({'sbb-eski': i}, [], [], set(), bekleyen, False, False,
                                        {'_basarisiz_kaynaklar': ['sbb']})
        self.assertEqual(sira, [])
        self.assertNotIn('sbb-eski', bekleyen)

    def test_kaynagi_okunamayan_acik_ilan_sirada_kalir(self):
        ileri = (date.today() + timedelta(days=10)).isoformat()
        i = {'id': 'sbb-acik', 'baslik': 'AKDENİZ ÜNİVERSİTESİ - 3 SÜREKLİ İŞÇİ ALACAK', 'kurum': 'AKDENİZ ÜNİVERSİTESİ',
             'kaynak_turu': 'sbb', 'son_tarih': ileri}
        bekleyen = {'sbb-acik'}
        ilan_bot.telegram_sirasi({'sbb-acik': i}, [], [], set(), bekleyen, False, False, {'_basarisiz_kaynaklar': ['sbb']})
        self.assertIn('sbb-acik', bekleyen)


if __name__ == '__main__':
    unittest.main()
