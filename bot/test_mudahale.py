import json
import tempfile
import unittest
from pathlib import Path

import mudahale

UUID = '1559e356-a0e2-44e2-869b-beb38c5fdb7a'


class Mudahale(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.m = Path(self.t.name) / 'mudahale.json'
        self.c = Path(self.t.name) / 'config.json'
        self.c.write_text(json.dumps({'site_url': 'x', 'elle': {'gizle': [], 'alanlar': {}}}), encoding='utf-8')

    def tearDown(self):
        self.t.cleanup()

    def uygula(self, *a, **k):
        return mudahale.uygula(*a, mudahale_yolu=self.m, config_yolu=self.c, **k)

    def test_anahtar_cozumleme(self):
        self.assertEqual(mudahale.anahtar_coz(f'https://kpsstercihi.com/ilan/{UUID}/'),
                         (UUID, mudahale.KK + UUID))
        self.assertEqual(mudahale.anahtar_coz('https://kpsstercihi.com/ilan/sbb-24c9bb297ddcd48d3ccc1aa2/?utm=x'),
                         ('sbb-24c9bb297ddcd48d3ccc1aa2', 'sbb-24c9bb297ddcd48d3ccc1aa2'))
        with self.assertRaises(ValueError):
            mudahale.anahtar_coz('<script>')

    def test_gizle_ve_geri_al(self):
        self.uygula('gizle', f'https://kpsstercihi.com/ilan/{UUID}/')
        m, c = json.loads(self.m.read_text(encoding='utf-8')), json.loads(self.c.read_text(encoding='utf-8'))
        self.assertEqual(m['gizle'], [UUID])
        self.assertEqual(c['elle']['gizle'], [mudahale.KK + UUID])
        self.assertEqual(c['site_url'], 'x')
        self.uygula('goster', UUID)
        m, c = json.loads(self.m.read_text(encoding='utf-8')), json.loads(self.c.read_text(encoding='utf-8'))
        self.assertEqual((m['gizle'], c['elle']['gizle']), ([], []))

    def test_duzelt(self):
        self.uygula('duzelt', 'iskur-abc123', manset='9 Zabıta Memuru', son_tarih='2026-10-23', toplam='9')
        m, c = json.loads(self.m.read_text(encoding='utf-8')), json.loads(self.c.read_text(encoding='utf-8'))
        self.assertEqual(m['alanlar']['iskur-abc123'], {'son_tarih': '2026-10-23', 'son_zaman': '2026-10-23T23:59:00+03:00',
                                                        'manset': '9 Zabıta Memuru', 'toplam': 9})
        self.assertEqual(c['elle']['alanlar']['iskur-abc123']['kadro'], '9 Zabıta Memuru')
        with self.assertRaises(ValueError):
            self.uygula('duzelt', 'iskur-abc123')

    def test_liste_uygula_kopyalari_da_gizler(self):
        self.uygula('gizle', 'sbb-aaaaaa')
        self.uygula('duzelt', 'iskur-bbbbbb', manset='Yeni')
        liste = [{'key': 'sbb-aaaaaa'}, {'key': 'csb-1', 'kopya_of': 'sbb-aaaaaa'}, {'key': 'iskur-bbbbbb', 'manset': 'Eski'}]
        self.assertEqual(mudahale.liste_uygula(liste, self.m), [{'key': 'iskur-bbbbbb', 'manset': 'Yeni'}])


if __name__ == '__main__':
    unittest.main()
