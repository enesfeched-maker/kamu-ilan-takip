import io
import unittest
from datetime import datetime
from unittest import mock

from PIL import Image

import kart_tasarimlari as kt
from kart_tasarimlari import TR, ilan_karti, tasarim_secimi

SIMDI = datetime(2026, 10, 8, 10, 0, tzinfo=TR)


def ilan(**ek):
    kayit = {'id': 'x', 'baslik': 'Örnek Belediyesi - Alım', 'kurum': 'Örnek Belediyesi', 'link': 'https://kariyerkapisi.gov.tr/x',
             'son_tarih': '2026-10-09', 'kadro': 'Toplam 5 kişi — 3 Sekreter • 2 Şoför', 'kaynaklar': [{'ad': 'Kariyer Kapısı'}]}
    kayit.update(ek)
    return kayit


def resim(ilan_, **kw):
    return Image.open(io.BytesIO(ilan_karti(ilan_, simdi=SIMDI, **kw))).convert('RGB')


class SecimTesti(unittest.TestCase):
    def test_tek_meslek_afis_cok_meslek_bilet(self):
        self.assertEqual(tasarim_secimi(ilan(kadro='Toplam 23 kişi — 23 SAĞLIK TEKNİKERİ')), 'afis')
        self.assertEqual(tasarim_secimi(ilan(kadro='Toplam 5 kişi — 3 Sekreter • 2 Şoför')), 'bilet')

    def test_ayni_fotografli_cok_kadro_bilet(self):
        kadro = 'Toplam 5 kişi — 2 Yazılım Uzmanı • 2 Sistem Uzmanı • 1 Ağ Uzmanı'
        self.assertEqual(tasarim_secimi(ilan(kadro=kadro)), 'bilet')

    def test_kadrosuz_afis_ve_baslikten_meslek(self):
        i = ilan(kadro=None, baslik='Örnek Belediyesi - 3 Öğretim Üyesi Alacak')
        self.assertEqual(tasarim_secimi(i), 'afis')
        kadrolar = kt._kadrolar(i)
        self.assertEqual([(k['adet'], k['no']) for k in kadrolar], [(3, 18)])
        self.assertEqual(kt.veri(i)['toplam'], 3)
        # eşleşmeyen başlık: kadro yok, genel fotoğraf (30) ve başlık metni kullanılır
        j = ilan(kadro=None, baslik='Örnek Belediyesi - Memur Alım İlanı')
        self.assertEqual(kt._kadrolar(j), [])
        self.assertEqual(resim(j).size, (1080, 1350))

    def test_boyut_ve_biçim(self):
        for i in (ilan(), ilan(kadro='Toplam 2 kişi — 2 Şoför'), ilan(kadro=None, baslik='Örnek - İlan')):
            veri = ilan_karti(i, simdi=SIMDI)
            with Image.open(io.BytesIO(veri)) as im:
                self.assertEqual((im.format, im.size), ('PNG', (1080, 1350)))


class RozetVeSeritTesti(unittest.TestCase):
    @staticmethod
    def adet(im, renk):
        return sum(n for n, c in im.getcolors(maxcolors=1 << 20) if c == renk)

    def test_hatirlatma_rozeti_aciliyet_rengi(self):
        for kadro in ('Toplam 5 kişi — 3 Sekreter • 2 Şoför', 'Toplam 2 kişi — 2 Şoför'):  # bilet ve afiş
            normal = resim(ilan(kadro=kadro))
            acil = resim(ilan(kadro=kadro), hatirlatma=True)  # 9 Ekim, simdi 8 Ekim: yarın son gün
            kirmizi = (0xd6, 0x45, 0x45)
            self.assertEqual(self.adet(normal, kirmizi), 0)
            self.assertGreater(self.adet(acil, kirmizi), 3000)
        self.assertEqual(kt.veri(ilan(), simdi=SIMDI)['kalan_yazi'], 'Yarın son gün')

    def test_hatirlatma_uzak_tarihte_kirmizi_degil(self):
        im = ilan_karti(ilan(son_tarih='2026-10-30'), simdi=SIMDI, hatirlatma=True)
        self.assertEqual(self.adet(Image.open(io.BytesIO(im)).convert('RGB'), (0xd6, 0x45, 0x45)), 0)

    def test_duyuru_seridi(self):
        iptal = resim(ilan(duyuru_turu='İptal duyurusu'))
        duzeltme = resim(ilan(duyuru_turu='Düzeltme / süre değişikliği'))
        normal = resim(ilan())
        self.assertEqual(iptal.getpixel((8, 8)), (0xd6, 0x45, 0x45))
        self.assertEqual(iptal.getpixel((1070, 90)), (0xd6, 0x45, 0x45))
        self.assertEqual(duzeltme.getpixel((8, 8)), (0xe0, 0xa1, 0x00))
        self.assertNotEqual(normal.getpixel((8, 8)), (0xd6, 0x45, 0x45))
        for tek in (False, True):  # her iki tasarımda da şerit
            i = ilan(duyuru_turu='İptal duyurusu', kadro=('Toplam 2 kişi — 2 Şoför' if tek else ilan()['kadro']))
            self.assertEqual(resim(i).getpixel((540, 5)), (0xd6, 0x45, 0x45))


class YaziTipiTesti(unittest.TestCase):
    def tearDown(self):
        kt.F.cache_clear()

    def test_zincir_sirasi(self):
        adaylar = kt.yazi_tipi_adaylari(True)
        self.assertEqual(adaylar[0].name, 'NotoSans-Bold.ttf')
        self.assertEqual(adaylar[0].parent, kt.FONT_KLASORU)
        self.assertEqual(kt.yazi_tipi_adaylari(False)[0].name, 'NotoSans-Regular.ttf')
        adlar = [a.name.lower() for a in adaylar]
        self.assertLess(adlar.index('segoeuib.ttf'), adlar.index('arialbd.ttf'))
        self.assertLess(adlar.index('arialbd.ttf'), adlar.index('dejavusans-bold.ttf'))

    def test_hicbir_font_yoksa_cokmez(self):
        with mock.patch.object(kt, 'yazi_tipi_adaylari', return_value=[kt.Path('/yok/a.ttf'), kt.Path('/yok/b.ttf')]):
            kt.F.cache_clear()
            self.assertIsNotNone(kt.F(30, True))
            im = Image.open(io.BytesIO(ilan_karti(ilan(), simdi=SIMDI)))
            self.assertEqual(im.size, (1080, 1350))

    def test_repodaki_noto_kullanilir(self):
        if not (kt.FONT_KLASORU / 'NotoSans-Bold.ttf').exists():
            self.skipTest('Noto Sans repoda yok')
        self.assertIn('Noto', kt.F(30, True).getname()[0])


if __name__ == '__main__':
    unittest.main()
