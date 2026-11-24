"""docs/nereye/cekirdek.js ("Puanınla nereye başvurabilirsin?") testlerini node ile çalıştırır; node yoksa atlanır."""
import shutil
import subprocess
import unittest
from pathlib import Path

BETIK = Path(__file__).resolve().parent / 'nereye_test.cjs'


@unittest.skipUnless(shutil.which('node'), 'node yok')
class NereyeTesti(unittest.TestCase):
    def test_node_testleri(self):
        s = subprocess.run(['node', str(BETIK)], capture_output=True, text=True, encoding='utf-8', timeout=120)
        self.assertEqual(s.returncode, 0, s.stderr + s.stdout)


KOK = Path(__file__).resolve().parent.parent


class NereyeSayfaTesti(unittest.TestCase):
    def test_menude_nereye_baglantisi(self):
        import site_uret as su
        self.assertIn('<a href="../nereye/" data-a="menu" data-a-x="Nereye Başvururum">Nereye Başvururum</a>', su.ust_html('../'))

    def test_elle_tutulan_sayfalarin_menusu(self):
        for yol in ('index.html', 'puanlar/index.html', 'bolum/index.html', 'katiplik/index.html', 'nereye/index.html'):
            metin = (KOK / 'docs' / yol).read_text(encoding='utf-8')
            self.assertRegex(metin, r'<a href="(?:\.\./)*nereye/"[^>]*>Nereye Başvururum</a>', yol)

    def test_sayfa_betikleri_sirali_ve_var(self):
        metin = (KOK / 'docs' / 'nereye' / 'index.html').read_text(encoding='utf-8')
        es, ce, ne = metin.find('bolum/esles.js'), metin.find('cekirdek.js'), metin.find('nereye.js')
        self.assertTrue(0 < es < ce < ne, 'esles.js → cekirdek.js → nereye.js sırası bozuk')
        for ad in ('cekirdek.js', 'nereye.js', 'nereye.css'):
            self.assertTrue((KOK / 'docs' / 'nereye' / ad).exists(), ad)

    def test_ana_sayfada_giris_kutusu(self):
        metin = (KOK / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('class="ny-davet" href="nereye/"', metin)


if __name__ == '__main__':
    unittest.main()
