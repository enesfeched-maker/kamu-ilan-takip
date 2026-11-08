import unittest

import sosyal_kalite as sk


class KaliteTest(unittest.TestCase):
    def test_gorunmez_karakter_silinir(self):
        self.assertEqual(sk.temizle('a​b c﻿'), 'ab c')

    def test_turkce_harfe_dokunmaz(self):
        self.assertEqual(sk.temizle('Şoför İğdır ç'), 'Şoför İğdır ç')

    def test_kisa_ilk_satir_degismez(self):
        self.assertEqual(sk.ilk_satiri_bol('Kısa satır.\nDevam'), 'Kısa satır.\nDevam')

    def test_uzun_ilk_satir_cumlede_bolunur(self):
        metin = 'A' * 80 + '. ' + 'B' * 80 + '\nSon'
        self.assertEqual(sk.ilk_satiri_bol(metin), 'A' * 80 + '.\n' + 'B' * 80 + '\nSon')

    def test_cumlesiz_uzun_satira_dokunmaz(self):
        metin = 'A' * 200
        self.assertEqual(sk.ilk_satiri_bol(metin), metin)


if __name__ == '__main__':
    unittest.main()
