import json
import tempfile
import unittest
from pathlib import Path

import belge_temizle as bt

A, B, C = 'a' * 64, 'b' * 64, 'c' * 64
YOL = lambda ozet: f'docs/belgeler/sbb/{ozet}.pdf'


class Basvuru(unittest.TestCase):
    def dosyalar(self, kok, ilanlar, yerel):
        i, y = Path(kok) / 'ilanlar.json', Path(kok) / 'yerel.json'
        i.write_text(json.dumps({'ilanlar': ilanlar}), encoding='utf-8')
        y.write_text(json.dumps({'kaynaklar': {'sbb': {'ilanlar': yerel}}}), encoding='utf-8')
        return i, y

    def test_iki_dosyadaki_kayitlar_birlikte_sayilir(self):
        with tempfile.TemporaryDirectory() as kok:
            i, y = self.dosyalar(kok, [{'belge_sha256': A}, {'belge_kopyasi': f'https://kpsstercihi.com/belgeler/sbb/{B}.pdf'}, {'baslik': 'x'}],
                                 [{'belge_sha256': C}])
            self.assertEqual(bt.basvurulanlar(i, y), {A, B, C})

    def test_okunamayan_veri_temizligi_durdurur(self):
        with tempfile.TemporaryDirectory() as kok:
            i, y = self.dosyalar(kok, [{'belge_sha256': A}], [])
            y.write_text('{bozuk', encoding='utf-8')
            self.assertIsNone(bt.basvurulanlar(i, y))
            self.assertIsNone(bt.basvurulanlar(Path(kok) / 'yok.json', y))
        self.assertEqual(bt.kullanilmayanlar([YOL(A)], None), [])


class Secim(unittest.TestCase):
    def test_yalniz_gosterilmeyen_sbb_pdfleri_secilir(self):
        ozetler = {A} | {f'{n:064x}' for n in range(bt.EN_AZ_BASVURU)}
        yollar = [YOL(A), YOL(B), 'docs/belgeler/csb/abc.docx', 'docs/belgeler/sbb/not.txt', 'docs/index.html']
        self.assertEqual(bt.kullanilmayanlar(yollar, ozetler), [YOL(B)])

    def test_cok_az_belge_gosteriliyorsa_hicbiri_kaldirilmaz(self):
        self.assertEqual(bt.kullanilmayanlar([YOL(A), YOL(B)], {A}), [])
        self.assertEqual(bt.kullanilmayanlar([YOL(A), YOL(B)], set()), [])


if __name__ == '__main__':
    unittest.main()
