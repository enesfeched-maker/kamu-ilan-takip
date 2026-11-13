"""Eski SBB belge adreslerinin ilan sayfasına yönlendirilmesi (bot/eski_belgeler.py, docs/404.html)."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eski_belgeler as eb

A, B, C, D = ('a' * 64), ('b' * 64), ('c' * 64), ('d' * 64)
KOK = Path(__file__).resolve().parent.parent


def kayit(kimlik, sha=None, eski=None, takma=None):
    k = {'id': kimlik, 'kaynak_kimlikleri': takma or []}
    if sha:
        k.update(belge_sha256=sha, belge_kopyasi=f'https://kpsstercihi.com/belgeler/sbb/{sha}.pdf')
    if eski:
        k['eski_belgeler'] = eski
    return k


class EskiBelgelerTest(unittest.TestCase):
    def test_birlesimde_onceki_ozet_saklanir(self):
        yeni = eb.isle(kayit('sbb-1', B), kayit('sbb-1', A, eski=[C]))
        self.assertEqual(yeni['eski_belgeler'], [A, C])
        self.assertEqual(eb.isle(kayit('sbb-1', B), kayit('sbb-1', B)).get('eski_belgeler'), None)   # özet aynı: alan yok
        self.assertNotIn(B, eb.isle(kayit('sbb-1', B), kayit('sbb-1', A, eski=[B]))['eski_belgeler'])
        cok = eb.isle(kayit('x', 'f' * 64), kayit('x', eski=[f'{i:064x}' for i in range(40)]))
        self.assertEqual(len(cok['eski_belgeler']), eb.EN_COK)

    def test_merge_sources_ozeti_tasir(self):
        from ek_kaynaklar import merge_sources
        onceki = {'sbb-1': {**kayit('sbb-1', A), 'kaynak_turu': 'sbb', 'baslik': 'X - 1 MEMUR', 'kurum': 'X', 'link': 'https://kamuilan.sbb.gov.tr/'}}
        yeni = {**kayit('sbb-1', B), 'kaynak_turu': 'sbb', 'baslik': 'X - 1 MEMUR', 'kurum': 'X', 'link': 'https://kamuilan.sbb.gov.tr/'}
        sonuc = merge_sources([yeni], onceki)
        self.assertEqual(sonuc[0]['belge_sha256'], B)
        self.assertEqual(sonuc[0]['eski_belgeler'], [A])

    def test_veri_kaydet_iki_tarafi_birlestirir(self):
        from veri_kaydet import merge_registry
        a = {'guncelleme': '2026-11-13T10:00:00+03:00', 'ilanlar': [kayit('sbb-1', A)]}
        b = {'guncelleme': '2026-11-13T11:00:00+03:00', 'ilanlar': [kayit('sbb-1', B, eski=[C])]}
        i = merge_registry(a, b)['ilanlar'][0]
        self.assertEqual(i['belge_sha256'], B)
        self.assertEqual(set(i['eski_belgeler']), {A, C})

    def test_yonlendirme_haritasi(self):
        with tempfile.TemporaryDirectory() as t:
            tohum = Path(t) / 'tohum.json'
            tohum.write_text(json.dumps({D: 'eski-takma', C: 'sayfasiz', A: 'sbb-1'}), encoding='utf-8')
            ilanlar = [kayit('sbb-1', A, eski=[B], takma=['eski-takma']), kayit('sayfasiz', eski=['e' * 64])]
            h = eb.yonlendirmeler(ilanlar, lambda k: k, {'sbb-1'}, tohum)
        self.assertEqual(h, {B: 'ilan/sbb-1/', D: 'ilan/sbb-1/'})   # A yayında: yönlendirilmez; sayfasız ilan yok

    def test_tohum_gecerli(self):
        veri = json.loads(eb.TOHUM.read_text(encoding='utf-8'))
        self.assertGreater(len(veri), 1000)
        self.assertTrue(all(re.fullmatch(r'[a-f0-9]{64}', s) and isinstance(k, str) for s, k in veri.items()))

    def test_404_sayfasi_haritayi_okur(self):
        h = (KOK / 'docs' / '404.html').read_text(encoding='utf-8')
        self.assertIn("fetch('/" + eb.CIKTI + "')", h)
        self.assertIn('location.replace(', h)
        self.assertIn('docs/' + eb.CIKTI, (KOK / '.gitignore').read_text(encoding='utf-8'))   # her derlemede üretilir


if __name__ == '__main__':
    unittest.main()
