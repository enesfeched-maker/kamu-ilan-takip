import unittest
from unittest import mock

import pdf_tablo


class BaslikTests(unittest.TestCase):
    def test_belediye_standart_tablosu(self):
        es = pdf_tablo._basliklar(['Sıra No', 'Kadro Unvanı', 'Sınıfı', 'Kadro Derecesi', 'Adedi', 'Niteliği', 'Cinsiyeti',
                                   'KPSS Puan Türü', 'KPSS Taban Puanı'])
        self.assertEqual(es, {1: 'unvan', 4: 'adet', 5: 'nitelik', 6: 'cinsiyet', 7: 'tur', 8: 'taban'})

    def test_birlesik_baslik_ve_atlanan_sutunlar(self):
        es = pdf_tablo._basliklar(['Ünvan', 'Kadro Sayısı', 'Şartlar', '', 'KPSS Puan Türü (*)', 'KPSS Taban Puanı',
                                   'Uygulama Sınavına Çağrılabilecek Aday Sayısı (**)'])
        self.assertEqual(es, {0: 'unvan', 1: 'adet', 2: 'nitelik', 3: 'nitelik', 4: 'tur', 5: 'taban'})


class SatirTests(unittest.TestCase):
    ES = {1: 'unvan', 4: 'adet', 5: 'nitelik', 6: 'cinsiyet', 7: 'tur', 8: 'taban'}

    def test_satir_alanlari(self):
        s = pdf_tablo._satir(self.ES, ['1', 'İtfaiye Eri', 'GİH', '11', '2', '- Herhangi bir ortaöğretim kurumundan mezun olmak. '
                                       '-En az (B) sınıfı sürücü belgesine sahip olmak.', 'Erkek', 'P94', 'En az 60 Puan'])
        self.assertEqual(s, {'unvan': 'İtfaiye Eri', 'adet': 2, 'cinsiyet': 'Erkek', 'tur': ['P94'], 'taban': 60,
                             'nitelik': ['Herhangi bir ortaöğretim kurumundan mezun olmak.', 'En az (B) sınıfı sürücü belgesine sahip olmak.']})

    def test_unvansiz_satir_atlanir(self):
        self.assertIsNone(pdf_tablo._satir(self.ES, ['', '', '', '', '', 'devam metni', '', '', '']))

    def test_bozuk_turkce_harfler(self):
        self.assertEqual(pdf_tablo._hucre('Daimi ĠĢçi'), 'Daimi İşçi')
        self.assertEqual(pdf_tablo._hucre('ĠġÇĠ'.replace('ġ', 'Ģ')), 'İŞÇİ')


class MaddeTests(unittest.TestCase):
    def test_maddeler(self):
        self.assertEqual(pdf_tablo.maddeler('*A olmak. *B olmak,'), ['A olmak.', 'B olmak.'])
        self.assertEqual(pdf_tablo.maddeler('D sınıfı belge. (Eski tip E sınıfı) - Tecrübe.'),
                         ['D sınıfı belge. (Eski tip E sınıfı)', 'Tecrübe.'])
        self.assertEqual(pdf_tablo.maddeler('Ön Lisans mezunu | Büro Yönetimi programı'), ['Ön Lisans mezunu', 'Büro Yönetimi programı'])

    def test_ortak_kosullar(self):
        metin = ('2024 yılı Kamu Personel Seçme Sınavından (KPSS (B) grubu) alım yapılacak kadroların ... '
                 'Sınavın yapıldığı tarihte 30 yaşını doldurmamış olmak')
        self.assertEqual(pdf_tablo.ortak_kosullar(metin), ['2024 KPSS puanı (B grubu)', '30 yaşını doldurmamış olmak'])
        self.assertEqual(pdf_tablo.ortak_kosullar('koşul yok'), [])


class SartBolumuTests(unittest.TestCase):
    def bolumler(self, satirlar):
        pdf_tablo.sart_bolumleri.cache_clear()
        with mock.patch.object(pdf_tablo, '_metin_oku', return_value=satirlar):
            sonuc = pdf_tablo.sart_bolumleri('x.pdf')
        pdf_tablo.sart_bolumleri.cache_clear()
        return sonuc

    def test_genel_ozel_sartlar_ve_pozisyon_basligi(self):
        sonuc = self.bolumler([
            'I. BAŞVURU ŞARTLARI', 'A- GENEL ŞARTLAR',
            'a) Devlet Memurları Kanununun 48 inci maddesinde yazılı genel', 'şartları haiz olmak,',
            'b) Güvenlik soruşturması olumlu olmak,',
            'B- ÖZEL ŞARTLAR', 'Mobil Yazılım Uzmanı (2 kişi)',
            'a) En az 3 yıllık tecrübe sahibi olmak.', 'b) Flutter bilmek.',
            'II. SINAV YERİ', '- Ankara.'])
        self.assertEqual([ad for ad, _ in sonuc], ['Genel şartlar', 'Özel şartlar'])
        self.assertEqual(sonuc[0][1], (('Devlet Memurları Kanununun 48 inci maddesinde yazılı genel şartları haiz olmak.', False),
                                       ('Güvenlik soruşturması olumlu olmak.', False)))
        self.assertEqual(sonuc[1][1][0], ('Mobil Yazılım Uzmanı (2 kişi)', True))

    def test_yarim_kalan_bolum_verilmez(self):
        sonuc = self.bolumler(['SINAVA KATILMA KOŞULLARI', '1- Genel şartları taşımak,', '2- 40 adet kadro için;', 'ATAMA YERLERİ'])
        self.assertEqual(sonuc, ())


class OkumaTests(unittest.TestCase):
    def test_pdfplumber_yoksa_bos(self):
        pdf_tablo.tablo_oku.cache_clear()
        with mock.patch.dict('sys.modules', {'pdfplumber': None}):
            self.assertEqual(pdf_tablo.tablo_oku('yok.pdf'), ())
        pdf_tablo.tablo_oku.cache_clear()


class SayfaTests(unittest.TestCase):
    def test_kadro_kartlari_html(self):
        import site_uret
        satirlar = ({'unvan': 'BÜRO PERSONELİ', 'adet': 4, 'nitelik': ['Lisans mezunu olmak.'], 'cinsiyet': '',
                     'tur': ['P3'], 'taban': 70},)
        item = {'sartlar': [{'metin': 'Sınav tarihinde 35 yaşını doldurmamış olmak'}]}
        h = site_uret._kadro_kartlari(item, satirlar, 'https://kpsstercihi.com/belgeler/sbb/x.pdf')
        self.assertIn('Büro Personeli', h)
        self.assertIn('4 kişi', h)
        self.assertIn('P3 · en az 70 puan', h)
        self.assertIn('35 yaşını doldurmamış olmak', h)
        self.assertIn('resmî ilan belgesi (PDF)', h)


if __name__ == '__main__':
    unittest.main()
