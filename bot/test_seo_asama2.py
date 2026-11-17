"""SEO ikinci aşama (18 Kasım 2026): menü/niyet ayrımı, ilgili sayfalar bağlantıları, kırıntılar, iş ilanı şeması, kalıcı kurum sayfaları."""
import json
import re
import unittest
from pathlib import Path

import site_uret as su

KOK = Path(__file__).resolve().parents[1]


class MenuNiyetTesti(unittest.TestCase):
    def test_menude_tercih_robotu_ve_altta_taban_puanlari(self):
        ust = su.ust_html('../')
        self.assertIn('href="../puanlar/" data-a="menu" data-a-x="Tercih Robotu">Tercih Robotu</a>', ust)
        self.assertNotIn('>Taban Puanları<', ust)
        self.assertIn('<a href="../kpss-taban-puanlari/">KPSS taban puanları</a>', su.alt_html('../'))

    def test_statik_sayfalarda_menu_etiketi_ayni(self):
        for yol in ('index.html', 'puanlar/index.html', 'bolum/index.html', 'katiplik/index.html'):
            metin = (KOK / 'docs' / yol).read_text(encoding='utf-8')
            self.assertRegex(metin, r'<a href="(?:\.\./)*puanlar/"[^>]*>Tercih Robotu</a>', yol)
            self.assertNotRegex(metin, r'puanlar/"[^>]*>Taban Puanları</a>', yol)
            self.assertIn('kpss-taban-puanlari/">KPSS taban puanları</a>', metin, yol)

    def test_puanlar_sayfasi_h1_robot(self):
        metin = (KOK / 'docs' / 'puanlar' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<section class="puan-intro"><h1>KPSS tercih robotu</h1></section>', metin)


if __name__ == '__main__':
    unittest.main()
