"""Denetim düzeltmeleri: yıl-sayı ayrımı, belge başvuru penceresi (İŞKUR/SBB tarihleri)."""
import unittest
from datetime import date, datetime
from unittest import mock

import basvuru_penceresi as bp
import ek_kaynaklar as ek
import kurum_sayfasi as ks
import liste_verisi as lv
from site_uret import TR

SIMDI = datetime(2026, 10, 5, 19, 0, tzinfo=TR)

MSB_KADRO = ('2026 YILI TABİP, DİŞ TABİBİ SINIFI SÖZLEŞMELİ/MUVAZZAF SUBAY VE ÖZEL NİTELİKLİ BEDEN EĞİTİMİ '
             'ÖĞRETMENİ SINIFI MUVAZZAF SUBAY ADAYI TEMİNİ')
GSB_NOT = ('1) Adaylar başvurularını, 21 Eylül 2026 (00.00) – 25 Eylül 2026 (17.00) tarihlerinde e- Devlet aracılığıyla '
           'Kariyer Kapısı (https://kariyerkapisi.gov.tr/isealim) adresi üzerinden elektronik ortamda yapacaktır.')
HANAK_NOT = ('a) Elektronik ortamda başvurular, 01/10/2026 – 05/10/2026 tarihleri arasında istenilen belgeler eklenmek '
             'suretiyle Belediyemizin info@hanak.bel.tr mail adresine yapılacaktır.')


def iskur(**ek_):
    return {'id': 'iskur-' + 'a' * 24, 'baslik': 'X Belediyesi Memur Alım İlanı', 'kurum': 'X Belediyesi', 'kaynak_turu': 'iskur',
            'son_tarih': '2026-10-25', 'son_zaman': '2026-10-25T17:00:00+03:00', 'ilk_gorulme': '2026-09-26T20:25:31+03:00', **ek_}


class YilSayisiTests(unittest.TestCase):
    def test_msb_yili_kadro_sayisi_degil(self):
        i = {'id': 'sbb-' + 'b' * 24, 'baslik': 'MİLLİ SAVUNMA BAKANLIĞI - ' + MSB_KADRO, 'kurum': 'MİLLİ SAVUNMA BAKANLIĞI',
             'kadro': MSB_KADRO, 'kaynak_turu': 'sbb'}
        self.assertTrue(all(adet is None for adet, _ in ks.kadrolar(i)))
        self.assertNotIn('toplam', ks.kart_alanlari(i))

    def test_gercek_sayilar_korunur(self):
        i = {'id': 'sbb-' + 'c' * 24, 'baslik': 'DMKA - 3 UZMAN, 2 DESTEK PERSONEL ALACAK', 'kurum': 'DMKA',
             'kadro': '3 UZMAN, 2 DESTEK PERSONEL ALACAK'}
        self.assertEqual([a for a, _ in ks.kadrolar(i)], [3, 2])
        self.assertEqual(ks.kart_alanlari(i)['toplam'], 5)

    def test_ek_kaynaklar_total_yili_saymaz(self):
        self.assertIsNone(ek.total({'kadro': MSB_KADRO}))
        self.assertEqual(ek.total({'kadro': '1 Teknisyen'}), 1)

    def test_baslik_yedegi_yili_saymaz(self):
        i = {'id': 'x', 'baslik': 'Kurum 2026 yılı 4 Tekniker alımı', 'kurum': 'Kurum', 'kadro': ''}
        self.assertEqual(ks.kadrolar(i)[0][0], 4)


class PencereTests(unittest.TestCase):
    def test_yazili_saatli(self):
        p = bp.pencere(GSB_NOT, date(2026, 9, 26))
        self.assertEqual((p['baslangic'], p['bitis']), (date(2026, 9, 21), date(2026, 9, 25)))
        self.assertEqual((p['baslangic_saat'], p['bitis_saat']), ((0, 0), (17, 0)))

    def test_sayisal_bicimler(self):
        for metin, bas, bit in [
            ('Elektronik ortamda başvurular, 19/10/2026-21/10/2026 tarihleri arasında', date(2026, 10, 19), date(2026, 10, 21)),
            ('Elektronik ortamda başvurular, 02/11/2026 - 06/11/2026 tarihleri arasında', date(2026, 11, 2), date(2026, 11, 6)),
            ('Elektronik ortamda başvurular, 01.10.2026/06.10.2026 tarihleri arasında', date(2026, 10, 1), date(2026, 10, 6)),
            ('Memur kadrosuna başvuran adaylar; a) Elektronik ortamda başvurular, 05/10/2026/-07/10/2026 tarihleri arasında', date(2026, 10, 5), date(2026, 10, 7)),
            ('Adaylar başvurularını 12 Ekim – 19 Ekim 2026 tarihleri arasında saat 23:59:59’a kadar', date(2026, 10, 12), date(2026, 10, 19)),
        ]:
            p = bp.pencere(metin, date(2026, 10, 1))
            self.assertEqual((p['baslangic'], p['bitis']), (bas, bit), metin)

    def test_tarihinden_baslayarak_ve_saat(self):
        p = bp.pencere("Başvurular, 08.10.2026 tarihinden başlayarak 23.10.2026 tarihi saat 23.59'a kadar e- Devlet", date(2026, 10, 1))
        self.assertEqual((p['baslangic'], p['bitis'], p['bitis_saat']), (date(2026, 10, 8), date(2026, 10, 23), (23, 59)))

    def test_baglam_ve_yil_gerekli(self):
        self.assertIsNone(bp.pencere('13/10/1983 tarihli 2918 sayılı Kanun', date(2026, 10, 1)))
        self.assertIsNone(bp.pencere('Sınav 01/10/2026 - 05/10/2026 arasında yapılır', date(2026, 10, 1)))   # başvuru sözcüğü yok
        self.assertIsNone(bp.pencere(HANAK_NOT, date(2030, 1, 1)))   # yıl uzak

    def test_gsb_kapanir_belge_kazanir(self):
        row = iskur(basvuru_notu=GSB_NOT)
        yeni = bp.uygula(row, [row['basvuru_notu']], date(2026, 9, 26))
        self.assertEqual((yeni['son_tarih'], yeni['son_zaman']), ('2026-09-25', '2026-09-25T17:00:00+03:00'))
        self.assertEqual(row['son_tarih'], '2026-10-25', 'girdi değişmez')
        self.assertEqual(ks.durum(yeni, SIMDI)[1], 'closed')
        self.assertEqual(ks.durum(row, SIMDI)[1], 'ok')

    def test_tablo_ile_ayni_bitis_saat_korunur(self):
        row = iskur(son_tarih='2026-10-05', son_zaman='2026-10-05T17:00:00+03:00', basvuru_notu=HANAK_NOT)
        yeni = bp.uygula(row, [HANAK_NOT], date(2026, 9, 26))
        self.assertEqual(yeni['son_zaman'], '2026-10-05T17:00:00+03:00')
        self.assertEqual(yeni['baslangic_zaman'], '2026-10-01T00:00:00+03:00')

    def test_saatsiz_farkli_bitis_son_zaman_kalkar(self):
        row = iskur(basvuru_notu=HANAK_NOT)
        yeni = bp.uygula(row, [HANAK_NOT], date(2026, 9, 26))
        self.assertEqual(yeni['son_tarih'], '2026-10-05')
        self.assertNotIn('son_zaman', yeni)

    def test_iskur_baslangic_yakinda(self):
        not_ = 'Elektronik ortamda başvurular, 19/10/2026-21/10/2026 tarihleri arasında istenilen belgeler eklenmek suretiyle'
        row = iskur(son_tarih='2026-10-21', son_zaman='2026-10-21T17:00:00+03:00', basvuru_notu=not_)
        t = lv.tamamla(row)
        self.assertEqual(ks.durum(t, SIMDI)[1], 'upcoming')
        self.assertEqual(ks.durum(row, SIMDI)[1], 'ok')

    def test_toplayici_iskur_pencere_uygula(self):
        row = iskur(basvuru_notu=GSB_NOT)
        with mock.patch.object(ek, 'now', return_value=datetime(2026, 9, 26, 12, tzinfo=TR)):
            ek.iskur_pencere_uygula(row)
        self.assertEqual(row['son_tarih'], '2026-09-25')
        self.assertEqual(row['baslangic_zaman'][:10], '2026-09-21')
        self.assertEqual(ek.iskur_pencere_uygula({'son_tarih': '2026-10-05', 'basvuru_notu': 'Şahsen başvuru yapılır.'})['son_tarih'], '2026-10-05')

    def test_kopya_tamamla_idempotent(self):
        row = iskur(basvuru_notu=GSB_NOT)
        self.assertEqual(lv.tamamla(lv.tamamla(row)), lv.tamamla(row))


class SbbTarihTests(unittest.TestCase):
    PDF = ('Adaylar, sözlü sınava katılabilmek için; a) Elektronik ortamda başvurular, 01/10/2026 – 05/10/2026 tarihleri arasında '
           'istenilen belgeler eklenmek suretiyle Belediyemizin info@hanak.bel.tr mail adresine yapılacaktır. 13/10/1983 tarihli kanun')

    def test_pdf_araligi_sbb_donemini_gecer(self):
        with mock.patch.object(ek, 'now', return_value=datetime(2026, 10, 5, 12, tzinfo=TR)):
            s = ek.pdf_dates(self.PDF, '( 5 Ekim - 7 Ekim)')
        self.assertEqual(s['son_tarih'], '2026-10-05')
        self.assertEqual(s['baslangic_zaman'], '2026-10-01T00:00:00+03:00')

    def test_pdf_listedeki_bitisi_iceriyorsa_eskisi_gibi(self):
        pdf = 'başvurular 20/10/2026 - 26/10/2026 tarihleri arasında alınır. Geç başvuru 05/11/2026'
        with mock.patch.object(ek, 'now', return_value=datetime(2026, 10, 5, 12, tzinfo=TR)):
            self.assertEqual(ek.pdf_dates(pdf, '( 20 Ekim - 26 Ekim)')['son_tarih'], '2026-10-26')

    def test_pdf_aralik_yoksa_donem(self):
        with mock.patch.object(ek, 'now', return_value=datetime(2026, 10, 5, 12, tzinfo=TR)):
            self.assertEqual(ek.pdf_dates('Başvuru tarihleri ilan metninde belirtilmiştir.', '( 5 Ekim - 7 Ekim)'), {})

    def test_kayitli_sbb_notundan_yedek(self):
        sbb = {'id': 'sbb-' + 'd' * 24, 'baslik': 'HANAK BELEDİYE BAŞKANLIĞI - 3 MEMUR ALACAK', 'kurum': 'HANAK BELEDİYE BAŞKANLIĞI',
               'kaynak_turu': 'sbb', 'son_tarih': '2026-10-07', 'donem': '( 5 Ekim - 7 Ekim)', 'basvuru_notu': HANAK_NOT,
               'baslangic_zaman': '2026-10-05T00:00:00+03:00', 'ilk_gorulme': '2026-09-26T20:29:52+03:00'}
        t = lv.tamamla(sbb)
        self.assertEqual(t['son_tarih'], '2026-10-05')
        self.assertEqual(t['baslangic_zaman'], '2026-10-01T00:00:00+03:00')
        self.assertEqual(sbb['son_tarih'], '2026-10-07')
        self.assertEqual(ks.durum(t, SIMDI)[1], 'closed' if SIMDI.date() > date(2026, 10, 5) else 'today')


if __name__ == '__main__':
    unittest.main()
