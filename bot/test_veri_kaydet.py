import unittest
from veri_kaydet import merge_registry


class RegistryMergeTests(unittest.TestCase):
    def test_preserves_delivery_history_and_fresh_details(self):
        a = {'guncelleme': '2026-09-25T13:00', 'ilanlar': [{'id': 'a', 'detay_guncelleme': '2026-09-25T12:00', 'yer': 'Ankara'}], 'telegram_gonderilen': ['a'], 'telegram_bekleyen': ['b']}
        b = {'guncelleme': '2026-09-25T14:00', 'ilanlar': [{'id': 'a', 'detay_guncelleme': '2026-09-24T12:00', 'yer': ''}, {'id': 'b'}], 'telegram_gonderilen': ['b'], 'telegram_bekleyen': ['a', 'c']}
        r = merge_registry(a, b)
        self.assertEqual(r['telegram_gonderilen'], ['a', 'b'])
        self.assertEqual(r['telegram_bekleyen'], ['c'])
        self.assertEqual(r['ilanlar'][0]['yer'], 'Ankara')
        self.assertEqual(len(r['ilanlar']), 2)


if __name__ == '__main__':
    unittest.main()
