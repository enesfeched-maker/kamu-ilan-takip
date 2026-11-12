"""İlanı kalmayan ama KPSS yerleştirme geçmişi olan kurumların kalıcı sayfası (adres 404 vermesin)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kurum_sayfasi as ks


def satirlar(kurum, n, il='ANKARA'):
    return [{'kurum': kurum, 'il': il, 'unvan': 'MEMUR', 'kontenjan': 1, 'yerlesen': 1, 'min': 70.0 + i, 'max': 71.0 + i} for i in range(n)]


class KaliciKurumTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        (self.docs / 'puanlar').mkdir()
        n = ks.KURUM_MIN_YERLESTIRME
        veri = {'donemler': {'2026-1': satirlar('ÖRNEK İŞLETMESİ GENEL MÜDÜRLÜĞÜ', n) + satirlar('AZ KAYITLI KURUMU', n - 1)
                             + satirlar('İLANLI BAKANLIĞI', n) + satirlar('ÖRNEK BELEDİYE BAŞKANLIĞI', n)}}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_yalniz_gecmisi_yeterli_ilansiz_kurum(self):
        dolu = {ks.kurum_kanonik('İLANLI BAKANLIĞI')}
        l = ks.kalici_kurumlar(self.docs, dolu, set())
        self.assertEqual([(ad, slug) for _, ad, slug in l], [('Örnek İşletmesi Genel Müdürlüğü', 'ornek-isletmesi-genel-mudurlugu')])
        self.assertEqual(ks.kalici_kurumlar(self.docs, dolu, {'ornek-isletmesi-genel-mudurlugu'}), [])   # slug doluysa üstüne yazılmaz

    def test_sayfa_veriden_ve_dizinde(self):
        kan, ad, slug = ks.kalici_kurumlar(self.docs, set(), set())[0] if False else next(
            x for x in ks.kalici_kurumlar(self.docs, set(), set()) if x[2] == 'ornek-isletmesi-genel-mudurlugu')
        h = ks.kurum_gecmis_sayfasi(kan, ad, slug, self.docs)
        self.assertNotIn('noindex', h)
        self.assertIn('<h1>Örnek İşletmesi Genel Müdürlüğü</h1>', h)
        self.assertIn('kurum/ornek-isletmesi-genel-mudurlugu/', h)
        self.assertIn('Şu an başvurusu açık ilan yok.', h)
        self.assertIn('KPSS merkezi yerleştirme geçmişi', h)
        self.assertIn('70,00', h)
        self.assertIn('BreadcrumbList', h)

    def test_hub_etiketi(self):
        _, h = ks.kurum_hub_sayfasi([('A Kurumu', 'a', 2, 5), ('B Kurumu', 'b', 0, 3), ('C Kurumu', 'c', 0, 0)])
        self.assertIn('A Kurumu</a> — 2 açık ilan', h)
        self.assertIn('B Kurumu</a> — 3 kayıt', h)
        self.assertIn('C Kurumu</a> — yerleştirme geçmişi', h)


if __name__ == '__main__':
    unittest.main()
