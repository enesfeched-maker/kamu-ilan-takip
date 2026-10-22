import unittest

import ilan_bakis as ib
from siniflandir import saf_akademik


class Bakis(unittest.TestCase):
    def test_engellilerde_spor_programi_engelli_kadrosu_degil(self):
        item = {'yz_kadrolar': [{'kosullar': ['Engellilerde beden eğitimi ve spor öğretmenliği mezunu olmak.']}]}
        self.assertNotIn('Engelli kadrosu', ib.sart_kelimeleri(item))
        self.assertIn('Engelli kadrosu', ib.sart_kelimeleri({'ozet': '5 engelli işçi alımı'}))

    def test_sart_kelimeleri(self):
        item = {'yz_ortak': ['35 yaşını doldurmamış olmak.', 'Erkek adaylar için askerlik şartı.'],
                'yz_kadrolar': [{'kosullar': ['B sınıfı sürücü belgesine sahip olmak.', 'En az 3 yıl mesleki deneyim.',
                                              'Boy 1.65 m olmak.']}]}
        self.assertEqual(ib.sart_kelimeleri(item), ['35 yaş altı', 'Yalnız erkek', 'B sınıfı ehliyet', '3 yıl deneyim',
                                                    'Boy-kilo şartı'])

    def test_bolum(self):
        item = {'ozet': 'Başvurular Kariyer Kapısı üzerinden yapılır. 2025 KPSS P3 en az 60 puan almış olmak.'}
        html = ib.bolum_html(item, toplam=12)
        self.assertIn('12 kişi', html)
        self.assertIn('Kariyer Kapısı', html)
        self.assertIn('>60<', html)
        self.assertEqual(ib.bolum_html({'ozet': 'x'}), '')
        self.assertEqual(ib.bolum_html(dict(item, duyuru_turu='İptal'), toplam=12), '')

    def test_saf_akademik(self):
        self.assertTrue(saf_akademik({'baslik': 'X Üniversitesi Öğretim Üyesi Alım İlanı'}))
        self.assertFalse(saf_akademik({'baslik': 'X Üniversitesi Öğretim Üyesi Alım İlanı', 'duyuru_turu': 'İptal'}))
        self.assertFalse(saf_akademik({'baslik': 'X Belediyesi Zabıta Memuru Alım İlanı'}))


if __name__ == '__main__':
    unittest.main()
