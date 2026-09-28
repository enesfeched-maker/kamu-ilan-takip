import unittest
from veri_kaydet import merge_registry


class RegistryMergeTests(unittest.TestCase):
    def test_reprocessed_sbb_summary_survives_merge_in_both_orders(self):
        a={'guncelleme':'2026-09-28T12:00','ilanlar':[{'id':'a','kaynak_turu':'sbb','sbb_detay_surumu':4,'detay_guncelleme':'2026-09-28T00:38','ozet':'eski'}],'telegram_gonderilen':['a']}
        b={'guncelleme':'2026-09-28T11:00','ilanlar':[{'id':'a','kaynak_turu':'sbb','sbb_detay_surumu':5,'detay_guncelleme':'2026-09-28T00:32','ozet':'yeni'}]}
        for left,right in [(a,b),(b,a)]:
            result=merge_registry(left,right)
            self.assertEqual(result['ilanlar'][0]['ozet'],'yeni')
            self.assertEqual(result['telegram_gonderilen'],['a'])

    def test_preserves_delivery_history_and_fresh_details(self):
        a = {'guncelleme': '2026-09-25T13:00', 'ilanlar': [{'id': 'a', 'detay_guncelleme': '2026-09-25T12:00', 'yer': 'Ankara'}], 'telegram_gonderilen': ['a'], 'telegram_bekleyen': ['b']}
        b = {'guncelleme': '2026-09-25T14:00', 'ilanlar': [{'id': 'a', 'detay_guncelleme': '2026-09-24T12:00', 'yer': ''}, {'id': 'b'}], 'telegram_gonderilen': ['b'], 'telegram_bekleyen': ['a', 'c']}
        r = merge_registry(a, b)
        self.assertEqual(r['telegram_gonderilen'], ['a', 'b'])
        self.assertEqual(r['telegram_bekleyen'], ['c'])
        self.assertEqual(r['ilanlar'][0]['yer'], 'Ankara')
        self.assertEqual(len(r['ilanlar']), 2)

    def test_reminder_history_union(self):
        r = merge_registry({'telegram_hatirlatilan': ['a', 'b']},
                           {'telegram_hatirlatilan': ['b', 'c']})
        self.assertEqual(r['telegram_hatirlatilan'], ['a', 'b', 'c'])


if __name__ == '__main__':
    unittest.main()
