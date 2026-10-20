import json
import tempfile
import unittest
from pathlib import Path

import site_paketi

A, B = 'a' * 64, 'b' * 64


class Paket(unittest.TestCase):
    def kur(self, kok, ilanlar):
        docs = Path(kok) / 'docs'
        (docs / 'belgeler' / 'sbb').mkdir(parents=True)
        for ad in (A, B):
            (docs / 'belgeler' / 'sbb' / f'{ad}.pdf').write_bytes(b'pdf')
        (docs / 'index.html').write_text('x')
        if ilanlar is not None:
            (docs / 'ilanlar.json').write_text(json.dumps({'ilanlar': ilanlar}), encoding='utf-8')
        return docs

    def test_yalniz_bagli_belgeler_pakete_girer(self):
        with tempfile.TemporaryDirectory() as kok:
            docs = self.kur(kok, [{'id': '1', 'belge_sha256': A}])
            site_paketi.paketle(docs, Path(kok) / '_site')
            site = Path(kok) / '_site'
            self.assertTrue((site / 'belgeler' / 'sbb' / f'{A}.pdf').exists())
            self.assertFalse((site / 'belgeler' / 'sbb' / f'{B}.pdf').exists())
            self.assertTrue((site / 'index.html').exists())
            self.assertTrue((docs / 'belgeler' / 'sbb' / f'{B}.pdf').exists())   # depodaki dosyaya dokunulmaz

    def test_kopya_adresiyle_baglanan_belge(self):
        with tempfile.TemporaryDirectory() as kok:
            docs = self.kur(kok, [{'id': '1', 'belge_kopyasi': f'https://kpsstercihi.com/belgeler/sbb/{B}.pdf'}])
            site_paketi.paketle(docs, Path(kok) / '_site')
            self.assertTrue((Path(kok) / '_site' / 'belgeler' / 'sbb' / f'{B}.pdf').exists())

    def test_veri_okunamazsa_hicbir_sey_ayiklanmaz(self):
        with tempfile.TemporaryDirectory() as kok:
            docs = self.kur(kok, None)
            site_paketi.paketle(docs, Path(kok) / '_site')
            self.assertTrue((Path(kok) / '_site' / 'belgeler' / 'sbb' / f'{A}.pdf').exists())
            self.assertTrue((Path(kok) / '_site' / 'belgeler' / 'sbb' / f'{B}.pdf').exists())


if __name__ == '__main__':
    unittest.main()
