import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from kurum_gorseli import logo_surumu,kurum_logosu


class LogoQualityTests(unittest.TestCase):
    def test_official_directory_originals_only(self):
        base='https://cdn.e-devlet.gov.tr/themes/ankara/images/logos/'
        self.assertEqual(logo_surumu(base+'64webp/14.1.8.0.webp'),base+'256px/14.1.8.0.png')
        self.assertEqual(logo_surumu(base+'128webp/14.1.8.0.webp'),base+'256px/14.1.8.0.png')
        self.assertEqual(logo_surumu(base+'64px/14.1.8.0.png'),base+'256px/14.1.8.0.png')
        self.assertEqual(logo_surumu('https://kariyerkapisi.gov.tr/UPS/a.png'),'https://kariyerkapisi.gov.tr/UPS/a.png')

    def test_reviewed_emblem_region_uses_library_without_network(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            Image.new('RGBA',(800,300),'red').save(root/'original.png')
            (root/'kaynaklar.json').write_text(json.dumps({'ornek universitesi':{'dosya':'original.png','kesim':[0,0,300,300]}}),encoding='utf-8')
            with patch('kurum_gorseli.LIBRARY',root),patch('urllib.request.build_opener') as network:
                raw=kurum_logosu({'kurum':'Örnek Üniversitesi Rektörlüğü'})
                self.assertEqual(Image.open(io.BytesIO(raw)).size,(300,300))
                network.assert_not_called()

if __name__=='__main__':unittest.main()
