import unittest
from puan_ayikla import metinden_ayikla

YENI = '''Program Kodu
Program Adı
Kadro Ünvanı
Kontenjan
Sayısı
En Küçük
Puan
202010101
ADIYAMAN İL ÖZEL İDARESİ / ADIYAMAN / MERKEZ
TEKNİKER
1
1
0
88,66165 88,66165
202010108
ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞI / ANKARA /
MERKEZ
DESTEK PERSONELİ
5
4
1
71,93905 79,93220
'''
SAYFA_2 = '''KPSS-2023/2 Bazı Kamu Kurum ve Kuruluşlarının Kadro ve Pozisyonlarına Yerleştirme Sonuçlarına İlişkin
En Küçük ve En Büyük Puanlar (Ön Lisans)
202013251
TOPRAK MAHSULLERİ OFİSİ  GENEL MÜDÜRLÜĞÜ / AFYONKARAHİSAR / TAŞRA
SAĞLIK MEMURU
1
0
1
--
--
'''
ESKI = '''Kod
Kurum Adı
252021001 ABDULLAH GÜL ÜNİVERSİTESİ / KAYSERİ / Merkez
MEMUR
1
1
0
89,55988
89,55988
252021820 KİLİS BELEDİYE BAŞKANLIĞI / KİLİS
MEMUR
5
5
0
81,73730
84,83284
(Ön Lisans)
'''


class PuanAyiklaTests(unittest.TestCase):
    def test_yeni_bicim_ve_sayfa_gecisi(self):
        kayitlar, hatalar = metinden_ayikla([YENI, SAYFA_2])
        self.assertEqual(hatalar, [])
        self.assertEqual(kayitlar[0], {
            'kod': '202010101', 'kurum': 'ADIYAMAN İL ÖZEL İDARESİ', 'il': 'ADIYAMAN', 'teskilat': 'Merkez',
            'unvan': 'TEKNİKER', 'kontenjan': 1, 'yerlesen': 1, 'min': 88.66165, 'max': 88.66165})
        self.assertEqual(kayitlar[1]['kurum'], 'ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞI')
        self.assertEqual((kayitlar[1]['unvan'], kayitlar[1]['min']), ('DESTEK PERSONELİ', 71.93905))
        # Kimsenin yerleşmediği kadroda puan uydurulmaz.
        self.assertNotIn('min', kayitlar[2])
        self.assertEqual(kayitlar[2]['yerlesen'], 0)

    def test_eski_bicim_kod_ve_kurum_ayni_satirda(self):
        kayitlar, hatalar = metinden_ayikla([ESKI])
        self.assertEqual(hatalar, [])
        self.assertEqual([k['il'] for k in kayitlar], ['KAYSERİ', 'KİLİS'])
        self.assertEqual(kayitlar[1]['teskilat'], '')
        self.assertEqual(kayitlar[1]['max'], 84.83284)

    def test_tutarsiz_satir_hata_olarak_bildirilir(self):
        bozuk = '202010101\nKURUM / ANKARA / MERKEZ\nMEMUR\n3\n1\n0\n80,1 81,2\n'
        kayitlar, hatalar = metinden_ayikla([bozuk])
        self.assertEqual((kayitlar, hatalar), ([], ['202010101']))


if __name__ == '__main__':
    unittest.main()
