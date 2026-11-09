"""Arama/filtre denetimi (9 Kasım 2026) regresyonları: portal.js kaynağı üzerinde kural denetimi."""
import re
import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / 'docs' / 'portal.js').read_text(encoding='utf-8')


class FiltreRegresyon(unittest.TestCase):
    def test_f01_il_listesi_81_ile_kadar_tutulur(self):
        m = re.search(r'o\.iller=strList\(l\.iller,(\d+),', JS)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 81)

    def test_f02_bilinmeyen_ogrenim_il_filtresini_genisletmez(self):
        self.assertNotIn("f.ogr==='bilinmiyor'&&ulusal(o)", JS)

    def test_f03_belediye_ogrenimden_ayridir(self):
        self.assertIn("'kurum'", JS)
        self.assertIn("sp.set('kurum','belediye')", JS)
        self.assertNotIn("['belediye','Belediye ilanları']", JS)
        self.assertNotIn("F.ogr==='belediye'", JS)

    def test_f04_il_sayaclari_arsiv_ve_suzgeclere_uyar(self):
        m = re.search(r'const ilSayilari=\(\)=>\{(.*?)return m;\};', JS, re.S)
        self.assertIsNotNone(m)
        govde = m.group(1)
        self.assertIn('ilanBase(', govde)
        self.assertIn('rowMatches(', govde)
        self.assertNotIn('of liste)', govde)


if __name__ == '__main__':
    unittest.main()
