import unittest

from ilan_bot import rss_coz, tarih_bul


class RssTests(unittest.TestCase):
    def test_yayin_tarihi_son_tarih_degil(self):
        self.assertIsNone(tarih_bul("PERSONEL ALIMI (09.09.2026)"))

    def test_acik_son_tarih(self):
        self.assertEqual(tarih_bul("Yayın 01.09.2026 Son başvuru: 30.09.2026"), "2026-09-30")
        self.assertEqual(tarih_bul("Son başvuru: 30 Eylül 2026"), "2026-09-30")

    def test_kategori_kurum_degil(self):
        xml = '''<rss><channel><item><title>ÖRNEK ÜNİVERSİTESİ - PERSONEL ALIMI (09.09.2026)</title>
        <link>https://kariyerkapisi.gov.tr/IlanDetay?i=test</link>
        <category>Sözleşmeli Personel İlanları</category>
        <pubDate>Wed, 09 Sep 2026 09:00:00 +0300</pubDate></item></channel></rss>'''
        ilan = rss_coz(xml)[0]
        self.assertEqual(ilan['kurum'], 'ÖRNEK ÜNİVERSİTESİ')
        self.assertIsNone(ilan['son_tarih'])


if __name__ == '__main__':
    unittest.main()
