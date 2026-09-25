import io
import unittest
from PIL import Image
from ilan_gorsel import gorsel_olustur, lines, font
from PIL import ImageDraw


class GorselTests(unittest.TestCase):
    def test_turkce_uzun_metin_ve_png(self):
        image = gorsel_olustur('Niğde Ömer Halisdemir Üniversitesi',
            'Toplam 29 kişi — 20 Destek Personeli • 9 Sağlık Teknikeri',
            'Niğde / Merkez', '29 Eylül 2026 · 17:00 TSİ', '3 gün kaldı')
        with Image.open(io.BytesIO(image)) as im:
            self.assertEqual(im.size, (1200, 760))
            self.assertEqual(im.format, 'PNG')
        self.assertLess(len(image), 1_000_000)

    def test_uzun_metin_tasma_yapmaz(self):
        d = ImageDraw.Draw(Image.new('RGB', (1200, 760)))
        face = font(49, True)
        for text in ['ÇĞİÖŞÜ ' * 200, 'A' * 2000]:
            wrapped = lines(d, text, face, 830, 3)
            self.assertLessEqual(len(wrapped), 3)
            self.assertTrue(all(d.textlength(line, font=face) <= 830 for line in wrapped))
