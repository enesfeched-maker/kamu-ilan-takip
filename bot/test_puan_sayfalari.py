import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import puan_sayfalari as ps

BASE = 'https://kpsstercihi.com/'


def satir(unvan, min_, kurum='ABC <b>Kurumu</b>', max_=None, kont=1, yer=1):
    return {'kod': '1', 'kurum': kurum, 'il': 'ANKARA', 'teskilat': 'Merkez', 'unvan': unvan,
            'kontenjan': kont, 'yerlesen': yer, 'min': min_, 'max': max_ if max_ is not None else min_, 'nit': []}


class PuanSayfalariTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        (self.docs / 'puanlar').mkdir()
        veri = {'duzey': 'lisans', 'ad': 'Lisans', 'kaynak': 'x', 'donemler': {
            '2022-1': [satir('HEMŞİRE', 70.5), satir('HEMŞİRE', 72.25), satir('İŞÇİ', 60.0)],
            '2026-1': [satir('HEMŞİRE', 71.2346, max_=88.1), satir('HEMŞİRE', 75.0, kurum='Z Kurumu'), satir('MEMUR', 80.0)],
        }}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
        self.urls = ps.puan_sayfalarini_uret(self.docs, BASE)
        self.k = self.docs / 'kpss-taban-puanlari'

    def tearDown(self):
        self.tmp.cleanup()

    def test_slug_ve_esik(self):
        self.assertTrue((self.k / 'lisans' / 'hemsire' / 'index.html').exists())
        self.assertFalse((self.k / 'lisans' / 'memur').exists())    # 1 satır
        self.assertFalse((self.k / 'lisans' / 'isci').exists())
        s = ps.benzersiz_sluglar(['A B', 'A-B', 'a b'])
        self.assertEqual(len(set(s.values())), 3)
        self.assertEqual(ps._ascii_slug('ÇOCUK GELİŞİMİ'), 'cocuk-gelisimi')

    def test_url_listesi_ve_canonical(self):
        self.assertEqual(sorted(self.urls), sorted([BASE + 'kpss-taban-puanlari/', BASE + 'kpss-taban-puanlari/lisans/',
                                                    BASE + 'kpss-taban-puanlari/lisans/hemsire/']))
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<link rel="canonical" href="' + BASE + 'kpss-taban-puanlari/lisans/hemsire/">', h)
        self.assertIn('<html lang="tr">', h)
        self.assertIn('BreadcrumbList', h)
        self.assertIn('og:url', h)
        self.assertIn('../../../sayfa.css', h)

    def test_sayi_bicimi(self):
        self.assertEqual(ps.sayi(71.2346), '71,23')
        self.assertEqual(ps.sayi(71.2346, 3), '71,235')
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('71,235', h)
        self.assertIn('en düşük puan 71,23, en yüksek 88,10', h)
        self.assertNotIn('71.23', h)

    def test_baslik_hali(self):
        self.assertEqual(ps.baslik_hali('HEMŞİRE YARDIMCISI'), 'Hemşire Yardımcısı')
        self.assertEqual(ps.baslik_hali('İŞÇİ'), 'İşçi')

    def test_html_kacis(self):
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('ABC &lt;b&gt;Kurumu&lt;/b&gt;', h)
        self.assertNotIn('<b>Kurumu</b>', h)

    def test_aciklama_uzunlugu_ve_not(self):
        import re
        for p in self.k.rglob('index.html'):
            h = p.read_text(encoding='utf-8')
            d = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
            self.assertLessEqual(len(d), 160)
            self.assertIn('resmî sonuç için ÖSYM&#x27;yi kontrol edin', h)

    def test_duzey_tablosu_ince_unvan_baglantisiz(self):
        h = (self.k / 'lisans' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<a href="hemsire/">Hemşire</a>', h)
        self.assertIn('<td>Memur</td>', h)
        self.assertIn('2022–2026', (self.k / 'index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
