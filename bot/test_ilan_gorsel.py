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
        self.assertLess(image.height,1250)

    def test_meslek_eslemesi(self):
        from meslek_gorseli import meslek_no
        beklenen={'Zabıta Memuru':7,'İtfaiye Eri':8,'Şoför':9,'Sürücü':9,'Mühendis':14,'Mimar':15,'Tekniker':16,
                  'Elektrik Teknisyeni':17,'Elektrik Mühendisi':14,'Öğretim Görevlisi':18,'Araştırma Görevlisi':18,
                  'Öğretmen':19,'Kütüphaneci':20,'Avukat':21,'Büro Personeli':22,'Veri Hazırlama ve Kontrol İşletmeni':22,
                  'Müfettiş Yardımcısı':23,'Sürekli İşçi':24,'Bahçıvan':25,'Orman Muhafaza Memuru':26,
                  'İş Makinesi Operatörü':27,'Mali Hizmetler Uzmanı':28,'Laborant':29,'Kimyager':29,'Yazılım Geliştirme Uzmanı':1,
                  'Siber Güvenlik Uzmanı':1,'Ağ Uzmanı':1,'Hemşire':2,'Sağlık Teknikeri':2,'Uzman Tabip':3,'Veteriner Hekim':4,
                  'Eczacı':5,'Güvenlik Görevlisi':6,'Pilot':10,'Aşçı':11,'Garson':12,'Temizlik Görevlisi':13,
                  'Destek Personeli':13,'3 YAZILIM TAKIM LİDERİ':1,'Uzman':30,'Bilinmeyen Kadro':30}
        for ad,no in beklenen.items():
            self.assertEqual(meslek_no(ad),no,ad)

    def test_fotograf_daire_ve_yedek_cizim(self):
        from unittest import mock
        import meslek_gorseli
        foto=meslek_gorseli.fotograf('Zabıta Memuru')
        self.assertEqual(foto.size[0],foto.size[1])
        self.assertLessEqual(foto.size[0],150)
        self.assertEqual(foto.getpixel((0,0))[3],0)          # köşe şeffaf (daire maskesi)
        self.assertEqual(foto.getpixel((foto.width//2,foto.height//2))[3],255)
        with mock.patch.object(meslek_gorseli,'_foto_yukle',return_value=None):
            self.assertIsNone(meslek_gorseli.fotograf('Zabıta Memuru'))
            yedek=meslek_gorseli.kutu_gorseli('Zabıta Memuru')
            self.assertEqual(yedek.tobytes(),meslek_gorseli.illustration('Zabıta Memuru',206).tobytes())

    def test_alti_uzeri_kadro_ozeti(self):
        yedi=' • '.join(f'{n} {ad}' for n,ad in enumerate(['Zabıta','İtfaiye','Şoför','Mimar','Avukat','Aşçı','Garson'],1))
        alti=' • '.join(f'{n} {ad}' for n,ad in enumerate(['Zabıta','İtfaiye','Şoför','Mimar','Avukat','Aşçı'],1))
        y7=Image.open(io.BytesIO(gorsel_olustur('Kurum',yedi,'Ankara','30 Eylül')))
        y6=Image.open(io.BytesIO(gorsel_olustur('Kurum',alti,'Ankara','30 Eylül')))
        self.assertEqual(y7.size,y6.size)  # 7 kadro: 5 kutu + özet kutusu = 6 kutu
        self.assertEqual(y7.height,y6.height)
        dokuz=' • '.join(f'{n} Büro Personeli' for n in range(1,10))
        self.assertEqual(Image.open(io.BytesIO(gorsel_olustur('Kurum',dokuz,'Ankara','30 Eylül'))).height,y7.height)

    def test_kadro_adlari_tek_tek_normalize(self):
        from unittest import mock
        import ilan_gorsel, meslek_gorseli
        gorulen=[]
        gercek=meslek_gorseli.kutu_gorseli
        with mock.patch.object(meslek_gorseli,'kutu_gorseli',side_effect=lambda r,s=206:(gorulen.append(r),gercek(r,s))[1]):
            gorsel_olustur('Kurum','Toplam 2 kişi — 3 YAZILIM TAKIM LİDERİ • 1 Kıdemli DevOps Uzmanı','Ankara','30 Eylül')
        self.assertEqual(gorulen,['3 Yazılım Takım Lideri','1 Kıdemli DevOps Uzmanı'])

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
