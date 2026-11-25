import json
import tempfile
import unittest
from pathlib import Path

import asistan_bilgi

IZINLI = ('https://kpsstercihi.com/', 'https://t.me/')


class AsistanBilgiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_yapi(self):
        v = asistan_bilgi.uret(self.docs)
        self.assertEqual(v['surum'], 1)
        self.assertTrue(v['uretim'])
        self.assertGreater(len(v['sss']), 10)
        self.assertGreater(len(v['meslekler']), 5)
        self.assertGreater(len(v['sayfalar']), 3)
        for s in v['sss']:
            self.assertEqual(set(s), {'s', 'c', 'u'})
        for m in v['meslekler']:
            self.assertTrue(m['kelimeler'])
        for p in v['sayfalar']:
            self.assertTrue(p['kelimeler'])

    def test_bos_cevap_yok_ve_tekrar_yok(self):
        v = asistan_bilgi.uret(self.docs)
        sorular = [asistan_bilgi.katla(s['s']) for s in v['sss']]
        self.assertEqual(len(sorular), len(set(sorular)))
        for s in v['sss']:
            self.assertTrue(s['s'].strip())
            self.assertTrue(s['c'].strip())

    def test_adresler_kpsstercihi_ya_da_telegram(self):
        v = asistan_bilgi.uret(self.docs)
        adresler = [s['u'] for s in v['sss']] + [m['u'] for m in v['meslekler']] + [p['u'] for p in v['sayfalar']]
        for u in adresler:
            self.assertTrue(u.startswith(IZINLI), u)
        self.assertIn('https://t.me/kpsstercihi', adresler)
        self.assertIn('https://kpsstercihi.com/nereye/', adresler)

    def test_vb_yok(self):
        v = asistan_bilgi.uret(self.docs)
        for s in v['sss']:
            self.assertNotIn('vb.', s['c'])
            self.assertNotIn('vs.', s['c'])

    def test_meslek_kelimeleri_katlanmis(self):
        v = asistan_bilgi.uret(self.docs)
        zabita = [m for m in v['meslekler'] if m['u'].endswith('/zabita-memuru/')][0]
        self.assertIn('zabita', zabita['kelimeler'])
        for m in v['meslekler']:
            for k in m['kelimeler']:
                self.assertEqual(k, asistan_bilgi.katla(k))

    def test_dizin_varsa_yalniz_dolu_meslekler(self):
        (self.docs / 'meslek').mkdir()
        (self.docs / 'meslek' / 'dizin.json').write_text(json.dumps([['zabita-memuru', 'Zabıta Memuru']]), encoding='utf-8')
        v = asistan_bilgi.uret(self.docs)
        self.assertEqual([m['u'] for m in v['meslekler']], ['https://kpsstercihi.com/meslek/zabita-memuru/'])

    def test_dosyaya_yazilir(self):
        asistan_bilgi.yaz(self.docs)
        veri = json.loads((self.docs / 'asistan' / 'bilgi.json').read_text(encoding='utf-8'))
        self.assertEqual(veri['surum'], 1)


if __name__ == '__main__':
    unittest.main()
