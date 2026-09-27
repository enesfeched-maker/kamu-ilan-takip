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
            self.assertEqual(im.size, (1200, 820))
            self.assertEqual(im.format, 'PNG')
        self.assertLess(len(image), 1_000_000)

    def test_all_professions_have_separate_illustrations(self):
        from meslek_gorseli import meslekler, kategori, illustration
        roles=meslekler('Toplam 6 kişi — 1 Hemşire • 2 Mühendis • 3 Güvenlik Görevlisi')
        self.assertEqual(len(roles),3)
        self.assertEqual([kategori(r) for r in roles],['health','technical','security'])
        self.assertEqual(kategori('3 TEKNİKER'),'technical')
        self.assertEqual(kategori('1 KÜTÜPHANECİ'),'education')
        self.assertEqual(len({illustration(r).tobytes() for r in roles}),3)
        many=' • '.join(str(n)+' Büro Personeli' for n in range(1,11))
        image=Image.open(io.BytesIO(gorsel_olustur('Kurum',many,'Ankara','30 Eylül')))
        self.assertGreater(image.height,1500)

    def test_uzun_metin_tasma_yapmaz(self):
        d = ImageDraw.Draw(Image.new('RGB', (1200, 760)))
        face = font(49, True)
        for text in ['ÇĞİÖŞÜ ' * 200, 'A' * 2000]:
            wrapped = lines(d, text, face, 830, 3)
            self.assertLessEqual(len(wrapped), 3)
            self.assertTrue(all(d.textlength(line, font=face) <= 830 for line in wrapped))

    def test_channel_branding_and_location_are_visible(self):
        from PIL import ImageChops
        image = Image.open(io.BytesIO(gorsel_olustur(
            'Örnek Kurum', '1 Mühendis', 'Ankara / Çankaya', '30 Eylül 2026')))
        background=Image.new('RGB',image.size,(16,43,53))
        self.assertIsNotNone(ImageChops.difference(image.crop((45,210,800,280)),background.crop((45,210,800,280))).getbbox())
        # Footer contains two separate, high-contrast brand areas.
        self.assertIsNotNone(ImageChops.difference(image.crop((45,image.height-70,1155,image.height-25)),background.crop((45,image.height-70,1155,image.height-25))).getbbox())
