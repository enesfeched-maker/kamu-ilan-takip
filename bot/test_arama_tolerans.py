"""docs/portal.js arama toleransı (ek, kısaltma, bitişik yazım, yazım hatası) testlerini node ile çalıştırır; node yoksa atlanır."""
import shutil
import subprocess
import unittest
from pathlib import Path

BETIK = Path(__file__).resolve().parent / 'arama_tolerans_test.cjs'


@unittest.skipUnless(shutil.which('node'), 'node yok')
class AramaToleransTesti(unittest.TestCase):
    def test_node_testleri(self):
        s = subprocess.run(['node', str(BETIK)], capture_output=True, text=True, encoding='utf-8', timeout=120)
        self.assertEqual(s.returncode, 0, s.stderr + s.stdout)


if __name__ == '__main__':
    unittest.main()
