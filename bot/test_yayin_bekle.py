import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import yayin_bekle


class YayinBekleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yerel = Path(self.tmp.name) / 'liste.json'
        self.yerel.write_bytes(b'{"yeni": 1}')

    def tearDown(self):
        self.tmp.cleanup()

    def calistir(self, yanitlar, deneme=5):
        yanitlar = list(yanitlar)
        uykular = []

        def getir():
            y = yanitlar.pop(0) if yanitlar else b'{"eski": 1}'
            if isinstance(y, Exception):
                raise y
            return y
        with contextlib.redirect_stdout(io.StringIO()):
            sonuc = yayin_bekle.bekle(self.yerel, getir, uykular.append, deneme=deneme, aralik=15)
        return sonuc, uykular

    def test_site_guncellenince_hemen_doner(self):
        sonuc, uykular = self.calistir([b'{"eski": 1}', OSError('ag'), b'{"yeni": 1}'])
        self.assertTrue(sonuc)
        self.assertEqual(uykular, [15, 15])

    def test_sure_dolarsa_hata_vermeden_devam_eder(self):
        sonuc, uykular = self.calistir([], deneme=3)
        self.assertFalse(sonuc)
        self.assertEqual(len(uykular), 2)


if __name__ == '__main__':
    unittest.main()
