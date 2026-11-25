import unittest

import sosyal_arastir as sa


class KaynakTest(unittest.TestCase):
    def test_kaynak_coz(self):
        self.assertEqual(sa.kaynak_coz('tt:@kpss.gunceloji'), ('tiktok', 'https://www.tiktok.com/@kpss.gunceloji'))
        self.assertEqual(sa.kaynak_coz('@RehberHocam'), ('youtube', 'https://www.youtube.com/@RehberHocam'))
        self.assertEqual(sa.kaynak_coz('UC9gsoe7d_BYa6goZMKvXTWA'),
                         ('youtube', 'https://www.youtube.com/channel/UC9gsoe7d_BYa6goZMKvXTWA'))
        self.assertEqual(sa.kaynak_coz('https://www.youtube.com/@x/'), ('youtube', 'https://www.youtube.com/@x'))
        with self.assertRaises(ValueError):
            sa.kaynak_coz('rastgele')


class KatTest(unittest.TestCase):
    def test_kat_medyana_gore(self):
        vs = [{'izlenme': 100}, {'izlenme': 200}, {'izlenme': 1000}, {'izlenme': None}]
        self.assertEqual(sa.kat_hesapla(vs), 200)
        self.assertEqual([v['kat'] for v in vs], [0.5, 1.0, 5.0, None])
        self.assertEqual([v['izlenme'] for v in sa.ustunler(vs)], [1000])

    def test_bos_liste(self):
        self.assertEqual(sa.kat_hesapla([]), 0)


class YorumTest(unittest.TestCase):
    def test_etiketler(self):
        self.assertEqual(sa.yorum_etiketle('62 puanla sağlık bakanlığına atanır mıyım'), ['soru', 'puan', 'kurum'])
        self.assertEqual(sa.yorum_etiketle('KPSS siz işçi alımı ne zaman'), ['soru', 'kpsssiz'])
        self.assertEqual(sa.yorum_etiketle('Allah nasip etsin'), [])
        self.assertEqual(sa.yorum_etiketle('75 puan ortaöğretim kpss ne gelir'), ['soru', 'puan'])
        self.assertEqual(sa.yorum_etiketle('Bu sene alım olacak diyorlar doğrumu hocam'), ['soru'])

    def test_baglanti_tanitimi_elenir(self):
        ham = [{'text': 'Apple https://a.example/x?y=1 Android https://b.example/z', 'like_count': 8},
               {'text': 'Detay https://site.example/a sayfasında', 'like_count': 1}]
        self.assertEqual([y['metin'] for y in sa.yorum_temizle(ham)], ['Detay [bağlantı] sayfasında'])

    def test_temizle_yazari_atar_kopyayi_eler(self):
        ham = [{'text': 'Kaç puan  lazım?', 'like_count': 3, 'author': 'Ali', 'parent': 'root'},
               {'text': 'kaç puan lazım?', 'like_count': 9, 'author': 'Veli', 'parent': 'root'},
               {'text': 'yanıt', 'like_count': 50, 'parent': 'abc'},
               {'text': 'Harika video', 'like_count': 7}]
        sonuc = sa.yorum_temizle(ham)
        self.assertEqual([y['metin'] for y in sonuc], ['Harika video', 'Kaç puan lazım?'])
        self.assertTrue(all(set(y) == {'metin', 'begeni', 'etiket'} for y in sonuc))


class KonuTest(unittest.TestCase):
    def test_konu_suzgeci(self):
        self.assertTrue(sa.konuyla_ilgili({'baslik': 'Ortaöğretim KPSS ile atanabileceğim kurumlar'}))
        self.assertTrue(sa.konuyla_ilgili({'baslik': 'Sağlık Bakanlığı 38 bin alım'}))
        self.assertFalse(sa.konuyla_ilgili({'baslik': 'Fatih Sultan Mehmet’in torunları #tarih'}))


class VideoOzetTest(unittest.TestCase):
    def test_youtube_adresi_ve_tarih(self):
        v = sa.video_ozet({'id': 'abc', 'title': 'Başlık', 'view_count': 5, 'upload_date': '20261120'}, 'youtube')
        self.assertEqual(v['adres'], 'https://www.youtube.com/watch?v=abc')
        self.assertEqual(v['tarih'], '2026-11-20')


if __name__ == '__main__':
    unittest.main()
