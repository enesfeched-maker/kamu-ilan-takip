import unittest
from datetime import datetime, timedelta, timezone

import ilan_bot

TR = timezone(timedelta(hours=3))


class Metinsiz(unittest.TestCase):
    def test_bitis_tarihine_kadar_metinsiz(self):
        simdi = datetime.now(TR)
        cfg = {'telegram_metinsiz_bitis': (simdi + timedelta(days=3)).isoformat()}
        self.assertTrue(ilan_bot.metinsiz_mi(cfg, simdi))
        self.assertFalse(ilan_bot.metinsiz_mi(cfg, simdi + timedelta(days=4)))
        self.assertFalse(ilan_bot.metinsiz_mi({}, simdi))
        self.assertFalse(ilan_bot.metinsiz_mi({'telegram_metinsiz_bitis': 'bozuk'}, simdi))


if __name__ == '__main__':
    unittest.main()
