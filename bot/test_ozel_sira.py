import unittest
from datetime import datetime, timedelta, timezone

import ozel_sira

TR = timezone(timedelta(hours=3))


class OzelSiraTest(unittest.TestCase):
    def setUp(self):
        self.simdi = datetime.now(TR).replace(microsecond=0)
        self.sira = [{'tanim': 'sosyal/ozel/a.json', 'zaman': (self.simdi - timedelta(hours=2)).isoformat()},
                     {'tanim': 'sosyal/ozel/b.json', 'zaman': (self.simdi - timedelta(hours=1)).isoformat()},
                     {'tanim': 'sosyal/ozel/c.json', 'zaman': (self.simdi + timedelta(days=1)).isoformat()}]

    def test_zamani_gelen_ilk_paylasilmamis(self):
        self.assertEqual(ozel_sira.siradaki(self.sira, [], self.simdi), 'sosyal/ozel/a.json')
        self.assertEqual(ozel_sira.siradaki(self.sira, [{'anahtar': 'ozel:a'}], self.simdi), 'sosyal/ozel/b.json')

    def test_gelecek_ve_bayat_atlanir(self):
        self.assertIsNone(ozel_sira.siradaki(self.sira, [{'anahtar': 'ozel:a'}, {'anahtar': 'ozel:b'}], self.simdi))
        bayat = [{'tanim': 'sosyal/ozel/d.json', 'zaman': (self.simdi - timedelta(days=2)).isoformat()}]
        self.assertIsNone(ozel_sira.siradaki(bayat, [], self.simdi))


if __name__ == '__main__':
    unittest.main()
