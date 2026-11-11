"""Sosyal medya ajanı: ayar sınırları, haftalık özet, yorum seçimi, karar kaydı."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sosyal_ajan as sa
from site_uret import TR

SIMDI = datetime.now(TR).replace(microsecond=0)


def paylasim(gun_once, tur, izlenme=None, **ek):
    g = {'zaman': (SIMDI - timedelta(days=gun_once)).isoformat(timespec='seconds'), 'tur': tur, 'vakit': 'sabah', **ek}
    if izlenme is not None:
        g['ig'] = {'views': izlenme, 'reach': izlenme // 2, 'likes': 1, 'comments': 0, 'saved': 2, 'shares': 3}
    return g


class AyarTest(unittest.TestCase):
    def test_sinir_disi_ve_taninmayan_atilir(self):
        temiz, atilan = sa.ayar_temizle({'ilan_gunluk': 9, 'son_gun_ufuk': 2, 'ozet_en_az': True, 'cron': '* * * * *',
                                         'sorular': {'ilan': ['Başvurmayı düşünüyor musun? 👇', 'Hemen başvur!', 'kısa?'], 'bilinmeyen': ['x?']}})
        self.assertEqual(temiz, {'son_gun_ufuk': 2, 'sorular': {'ilan': ['Başvurmayı düşünüyor musun? 👇']}})
        self.assertEqual(len(atilan), 5)
        self.assertEqual(sa.ayar_temizle('bozuk'), ({}, []))

    def test_yasak_soz_ve_uzunluk(self):
        uzun = 'Bu kadrolardan hangisi sana uygun, ' + 'a' * 80 + '?'
        temiz, _ = sa.ayar_temizle({'sorular': {'genel': ['KAÇIRMA, başvurdun mu?', 'Müjde, gördün mü?', uzun]}})
        self.assertEqual(temiz, {})

    def test_dosya_yoksa_varsayilan(self):
        with tempfile.TemporaryDirectory() as g:
            yol = Path(g) / 'ayar.json'
            self.assertEqual(sa.ayar('ilan_gunluk', yol), 3)
            self.assertIsNone(sa.sorular('ilan', yol))
            yol.write_text('{"ilan_gunluk": 2, "sorular": {"ilan": ["Sana uygun olan var mı? 👇"]}}', encoding='utf-8')
            self.assertEqual(sa.ayar('ilan_gunluk', yol), 2)
            self.assertEqual(sa.ayar('ozet_en_az', yol), 2)
            self.assertEqual(sa.sorular('ilan', yol), ['Sana uygun olan var mı? 👇'])
            self.assertTrue(sa.dogrula(yol))
            yol.write_text('{"ilan_gunluk": 40}', encoding='utf-8')
            self.assertEqual(sa.ayar('ilan_gunluk', yol), 3)      # geçersiz değer botu bozmaz
            self.assertFalse(sa.dogrula(yol))
            yol.write_text('{bozuk', encoding='utf-8')
            self.assertEqual(sa.ayar('ilan_gunluk', yol), 3)
            self.assertFalse(sa.dogrula(yol))

    def test_depodaki_ayar_gecerli(self):
        self.assertTrue(sa.dogrula())   # sosyal/ayar.json yoksa da geçerlidir


class RaporTest(unittest.TestCase):
    GECMIS = [paylasim(1, 'ilan', 400), paylasim(2, 'ilan', 200), paylasim(3, 'son_gun', 100), paylasim(4, 'ozet'),
              paylasim(9, 'son_gun', 350), paylasim(20, 'ilan', 999)]

    def test_donem_toplamlari(self):
        bu = sa.donem(self.GECMIS, SIMDI - timedelta(days=7), SIMDI)
        self.assertEqual((bu['paylasim'], bu['olculen'], bu['toplam']['views'], bu['toplam']['shares']), (4, 3, 700, 9))
        self.assertEqual(bu['tur'], {'ilan': {'adet': 2, 'medyan': 300}, 'son_gun': {'adet': 1, 'medyan': 100}})
        self.assertEqual(bu['en_iyi']['ig']['views'], 400)

    def test_rapor_metni(self):
        m = sa.rapor_metni(self.GECMIS, SIMDI, 'Tek ilan videoları daha çok izlendi.')
        self.assertIn('4 paylaşım (önceki hafta 1)', m)
        self.assertIn('İzlenme: 700 (+100%)', m)
        self.assertIn('Biçime göre medyan izlenme: Tek ilan 300 (2 video), Son gün 100 (1 video)', m)
        self.assertIn('Ajanın notu: Tek ilan videoları daha çok izlendi.', m)
        self.assertIn('yalnız Instagram', m)

    def test_olcum_yoksa_acikca_yazar(self):
        m = sa.rapor_metni([paylasim(1, 'ilan')], SIMDI)
        self.assertIn('henüz Instagram ölçümü yok', m)
        self.assertNotIn('İzlenme:', m)


class YorumTest(unittest.TestCase):
    def test_yalniz_yeni_ve_gorulmemis(self):
        z = lambda saat: (SIMDI - timedelta(hours=saat)).strftime('%Y-%m-%dT%H:%M:%S%z')
        yorumlar = [{'id': '1', 'text': 'Başvuru nereden?', 'username': 'aday', 'timestamp': z(2)},
                    {'id': '2', 'text': 'eski', 'username': 'x', 'timestamp': z(80)},
                    {'id': '3', 'text': 'görüldü', 'username': 'x', 'timestamp': z(1)},
                    {'id': '4', 'text': '  ', 'username': 'x', 'timestamp': z(1)},
                    {'id': '5', 'text': 'tarihsiz', 'username': 'x', 'timestamp': 'bozuk'}]
        yeni = sa.yeni_yorumlar(yorumlar, {'3'}, SIMDI)
        self.assertEqual([y['id'] for y in yeni], ['1'])
        m = sa.yorum_mesaji(dict(yeni[0], baglanti='https://www.instagram.com/reel/abc/'))
        self.assertEqual(m, "Instagram'da yeni yorum\n@aday: Başvuru nereden?\nVideo: https://www.instagram.com/reel/abc/")


class KararTest(unittest.TestCase):
    def test_kaydet_ayari_ve_gunlugu_yazar(self):
        with tempfile.TemporaryDirectory() as g:
            g = Path(g)
            (g / 'karar.json').write_text(json.dumps({'ayar': {'ilan_gunluk': 2, 'ozet_en_az': 9},
                                                      'not': 'Tek ilan videolarının medyanı 120, diğerlerinin 300; günlük sayıyı 3ten 2ye indirdim.'},
                                                     ensure_ascii=False), encoding='utf-8')
            self.assertTrue(sa.kaydet(SIMDI, g, g / 'ayar.json', g / 'gunluk.md'))
            self.assertEqual(json.loads((g / 'ayar.json').read_text(encoding='utf-8')), {'ilan_gunluk': 2})   # sınır dışı alan atıldı
            gunluk = (g / 'gunluk.md').read_text(encoding='utf-8')
            self.assertIn(f'## {SIMDI:%Y-%m-%d}', gunluk)
            self.assertTrue(sa.son_not(g / 'gunluk.md').startswith('Tek ilan videolarının medyanı 120'))
            self.assertTrue(sa.dogrula(g / 'ayar.json'))

    def test_gerekcesiz_karar_yazilmaz(self):
        with tempfile.TemporaryDirectory() as g:
            g = Path(g)
            (g / 'karar.json').write_text('{"ayar": {"ilan_gunluk": 1}, "not": "kısa"}', encoding='utf-8')
            self.assertFalse(sa.kaydet(SIMDI, g, g / 'ayar.json', g / 'gunluk.md'))
            self.assertFalse((g / 'ayar.json').exists())
            self.assertFalse(sa.kaydet(SIMDI, g / 'yok', g / 'ayar.json', g / 'gunluk.md'))

    def test_hazirla_durum_dosyasi(self):
        with tempfile.TemporaryDirectory() as g:
            d = sa.hazirla(SIMDI, g)
            kayit = json.loads((Path(g) / 'durum.json').read_text(encoding='utf-8'))
        self.assertEqual(kayit['ayar_sinirlari']['ilan_gunluk'], {'varsayilan': 3, 'en_az': 1, 'en_cok': 4})
        self.assertEqual(set(d['bu_hafta']), {'paylasim', 'olculen', 'toplam', 'tur'})
        self.assertTrue(all(set(p) == {'zaman', 'vakit', 'tur', 'muzik', 'palet', 'ig'} for p in kayit['son_30_gun']))   # ilan kimliği, platform kimliği yok


class BaglamaTest(unittest.TestCase):
    def test_bot_ajanin_ayarini_kullanir(self):
        import reels
        import sosyal_motor as sm
        eski = sa.AYAR_YOLU
        with tempfile.TemporaryDirectory() as g:
            sa.AYAR_YOLU = Path(g) / 'ayar.json'
            try:
                self.assertEqual(reels._ayar('ilan_gunluk'), 3)
                sa.AYAR_YOLU.write_text('{"ilan_gunluk": 1, "sorular": {"ilan": ["Bu kadro sana uyuyor mu? 👇"]}}', encoding='utf-8')
                self.assertEqual(reels._ayar('ilan_gunluk'), 1)
                konu = {'tur': 'ilan', 'etiketler': ['#yeniilan'], 'giris': 'Deneme Kurumu 3 kişi alacak.', 'satirlar': [], 'baslik': 'Deneme'}
                self.assertIn('Bu kadro sana uyuyor mu? 👇', sm.metin_olustur(konu, 'ilan', SIMDI)['aciklama'])
            finally:
                sa.AYAR_YOLU = eski


if __name__ == '__main__':
    unittest.main()
