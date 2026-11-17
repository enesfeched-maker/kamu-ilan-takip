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


class YayinTetikleyicileriTesti(unittest.TestCase):
    def test_site_uretenin_ice_aldigi_her_modul_tetikleyicide_listeli(self):
        """site_uret.py ve site_paketi.py'nin (tembel içe aktarmalar dahil) çağırdığı her bot modülü site-yayinla.yml paths listesinde olmalı."""
        import ast
        bot = Path(__file__).resolve().parent
        moduller = {p.stem for p in bot.glob('*.py') if not p.stem.startswith('test_')}

        def ice_aktarilan(modul):
            agac = ast.parse((bot / f'{modul}.py').read_text(encoding='utf-8'))
            sonuc = set()
            for dugum in ast.walk(agac):
                if isinstance(dugum, ast.Import):
                    sonuc |= {a.name.split('.')[0] for a in dugum.names}
                elif isinstance(dugum, ast.ImportFrom) and dugum.module:
                    sonuc.add(dugum.module.split('.')[0])
            return sonuc & moduller
        gorulen, yigin = set(), ['site_uret', 'site_paketi']
        while yigin:
            m = yigin.pop()
            if m not in gorulen:
                gorulen.add(m)
                yigin += ice_aktarilan(m)
        yml = (KOK / '.github' / 'workflows' / 'site-yayinla.yml').read_text(encoding='utf-8')
        listeli = set(re.findall(r"'bot/(\w+)\.py'", yml))
        self.assertEqual(sorted(gorulen - listeli), [])
        for yeni in ('il_sayfalari', 'meslek_sayfalari', 'puan_sayfalari', 'yz_gorunurluk', 'kurum_sayfasi', 'ince_sayfa', 'analiz_sayfalari'):
            self.assertIn(yeni, listeli)


if __name__ == '__main__':
    unittest.main()
