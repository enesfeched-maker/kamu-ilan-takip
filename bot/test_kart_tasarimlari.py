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


class MarkaSeridiLogoTesti(unittest.TestCase):
    def serit(self, im=True):
        from PIL import ImageDraw
        resim_ = Image.new('RGB', (1080, 200), '#ffffff')
        kt.marka_seridi(ImageDraw.Draw(resim_), 50, im=resim_ if im else None)
        return resim_

    def test_logo_serit_disinda_piksel_basar(self):
        logo, yok = self.serit(True), self.serit(False)
        self.assertNotEqual(logo.crop((kt.KENAR, 64, kt.KENAR + 60, 124)).tobytes(), yok.crop((kt.KENAR, 64, kt.KENAR + 60, 124)).tobytes())
        self.assertEqual(logo.getpixel((kt.KENAR, 64)), (0x17, 0x4c, 0x46))  # yuvarlak köşe: şerit rengi görünür
        self.assertEqual(logo.getpixel((kt.KENAR + 30, 64)), (0xc9, 0xf3, 0x95))  # üst kenarda lime çerçeve

    def test_logo_olmadan_eskisi_gibi(self):
        with mock.patch.object(kt, 'LOGO_YOLU', kt.LOGO_YOLU.with_name('yok.png')):
            kt._logo_yukle.cache_clear()
            kt.logo_kare.cache_clear()
            try:
                self.assertEqual(self.serit(True).tobytes(), self.serit(False).tobytes())
            finally:
                kt._logo_yukle.cache_clear()
                kt.logo_kare.cache_clear()


class TopluKartTesti(unittest.TestCase):
    def liste(self, n, gun=2):
        bitis = (SIMDI.date() + __import__('datetime').timedelta(days=gun)).isoformat()
        return [ilan(id=f'i{k}', kurum=f'Örnek Belediyesi {k}', kadro=f'{k + 1} Zabıta Memuru', son_tarih=bitis) for k in range(n)]

    def test_boyut_ve_satir_siniri(self):
        for n in (1, 4, 7, 12):
            im = Image.open(io.BytesIO(kt.toplu_son_gun_karti(self.liste(n), SIMDI)))
            self.assertEqual(im.size, (1080, 1350))

    def test_satir_bilgisi_kurum_ve_kadro(self):
        kurum, kadro = kt.toplu_satir(self.liste(1)[0])
        self.assertEqual(kurum, 'Örnek Belediyesi 0')
        self.assertEqual(kadro, '1 Zabıta Memuru')
        _, kadro = kt.toplu_satir(ilan(kadro='Toplam 6 kişi — 2 Sekreter • 2 Şoför • 2 Hemşire'))
        self.assertTrue(kadro.endswith('+1'))

    def test_rozet_renkleri_bugun_yarin_kirmizi_diger_turuncu(self):
        def renk(gun):
            im = Image.open(io.BytesIO(kt.toplu_son_gun_karti(self.liste(1, gun), SIMDI))).convert('RGB')
            return im.getpixel((1080 - kt.KENAR - 20, 40 + 210 + 14 + 69))
        kirmizi, turuncu = tuple(int(kt.KIRMIZI[i:i + 2], 16) for i in (1, 3, 5)), tuple(int(kt.TURUNCU[i:i + 2], 16) for i in (1, 3, 5))
        self.assertEqual(renk(0), kirmizi)
        self.assertEqual(renk(1), kirmizi)
        self.assertEqual(renk(2), turuncu)
        self.assertEqual(renk(3), turuncu)

    def test_cok_uzun_kurum_tek_satira_sigar(self):
        uzun = ilan(kurum='Çok Uzun Adlı ' * 12 + 'Belediye Başkanlığı', kadro='1 ' + 'Zabıta ' * 30)
        Image.open(io.BytesIO(kt.toplu_son_gun_karti([uzun], SIMDI))).load()


class SabahKartiTesti(unittest.TestCase):
    def liste(self, n):
        return [ilan(id=f'i{k}', kurum=f'Örnek Belediyesi {k}', kadro=f'Toplam {k + 1} kişi — {k + 1} Zabıta Memuru') for k in range(n)]

    def test_boyut_her_adette(self):
        for n in (0, 1, 2, 4, 9):
            im = Image.open(io.BytesIO(kt.sabah_ozeti_karti(self.liste(n), 44, SIMDI)))
            self.assertEqual(im.size, (1080, 1350))

    def test_cok_uzun_kurum_ve_buyuk_sayi_tasmaz(self):
        uzun = ilan(kurum='Çok Uzun Adlı ' * 12 + 'Belediye Başkanlığı', kadro='1 ' + 'Zabıta ' * 30)
        Image.open(io.BytesIO(kt.sabah_ozeti_karti([uzun] + self.liste(3), 12345, SIMDI))).load()

    def test_marka_seridi_ve_tarih_baslikta(self):
        im = Image.open(io.BytesIO(kt.sabah_ozeti_karti(self.liste(2), 5, SIMDI))).convert('RGB')
        self.assertEqual(im.getpixel((10, 1350 - 10)), (0x17, 0x4c, 0x46))  # alt marka şeridi
        self.assertEqual(im.getpixel((60, 60)), (0x10, 0x2e, 0x35))  # petrol başlık bandı

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
