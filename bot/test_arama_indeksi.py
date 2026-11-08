import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import arama_indeksi as ai


class KelimeTest(unittest.TestCase):
    def test_turkce_katlama_portal_ile_ayni(self):
        self.assertEqual(ai.katla("ZABITA MEMURU Şoför Iğdır 4/B KPSS'siz"), 'zabita memuru sofor igdir 4b kpsssiz')

    def test_benzersiz_ve_dolgusuz(self):
        self.assertEqual(ai.kelimeler('Zabıta ve zabıta memuru 2026 için'), 'zabita memuru')


class YayginTest(unittest.TestCase):
    def test_kalip_sozcuk_atilir_meslek_kalir(self):
        dizin = {str(n): 'kanun zabita' if n == 0 else 'kanun diger' + str(n) for n in range(25)}
        sonuc = ai.yaygini_ele(dizin)
        self.assertEqual(sonuc['0'], 'zabita')

    def test_az_belgede_dokunulmaz(self):
        self.assertEqual(ai.yaygini_ele({'a': 'kanun'}), {'a': 'kanun'})


class DizinTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.docs = Path(self.gecici.name)
        (self.docs / 'belgeler' / 'sbb').mkdir(parents=True)
        self.onbellek = self.docs / 'onbellek'

    def tearDown(self):
        self.gecici.cleanup()

    def _docx(self, ad, metin):
        yol = self.docs / ad
        with zipfile.ZipFile(yol, 'w') as z:
            z.writestr('word/document.xml', f'<w:document><w:t>{metin}</w:t></w:document>')
        return yol

    def test_docx_okunur_ve_onbellege_yazilir(self):
        yol = self._docx('a.docx', 'Zabıta Memuru')
        self.assertEqual(ai.belge_kelimeleri(yol, self.onbellek), 'zabita memuru')
        self.assertEqual(len(list(self.onbellek.glob('arama-*.txt'))), 1)
        self.assertEqual(ai.belge_kelimeleri(yol, self.onbellek), 'zabita memuru')

    def test_bozuk_ve_eksik_belge_bos_doner(self):
        bozuk = self.docs / 'bozuk.pdf'
        bozuk.write_bytes(b'pdf degil')
        self.assertEqual(ai.belge_kelimeleri(bozuk, self.onbellek), '')
        self.assertEqual(ai.belge_kelimeleri(self.docs / 'yok.pdf', self.onbellek), '')

    def test_akademik_dizine_girmez(self):
        (self.docs / 'belgeler' / 'sbb' / 'x.pdf').write_bytes(b'bozuk')
        ilanlar = [{'id': 'a', 'link': 'https://o/', 'kategori': 'akademik', 'belge_sha256': 'x'}]
        self.assertEqual(ai.dizin_uret(ilanlar, self.docs, self.onbellek), {})


if __name__ == '__main__':
    unittest.main()
