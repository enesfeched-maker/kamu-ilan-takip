import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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

    def test_kalici_metinsiz(self):
        self.assertTrue(ilan_bot.metinsiz_mi({'telegram_metinsiz': True}, datetime.now(TR) + timedelta(days=400)))
        self.assertTrue(ilan_bot.metinsiz_mi(ilan_bot.json.loads((Path(__file__).resolve().parents[1] / 'config.json').read_text(encoding='utf-8')),
                                             datetime.now(TR) + timedelta(days=30)))


if __name__ == '__main__':
    unittest.main()
