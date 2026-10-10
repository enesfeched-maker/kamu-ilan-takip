"""Tarih bombası kontrolü: tüm bot testlerini ileri tarihlerde koşar (varsayılan +7, +30 gün).

Sabit tarihli test verisi zamanla 'geçmiş' olup taramayı durdurabilir (10 Ekim 2026 olayı). Bu kontrol günlük
ayrı bir iş akışında çalışır; yayını durdurmaz, sorunu ilan.yml'yi kırmadan haftalar önce gösterir.
Kullanım: python bot/zaman_kontrol.py [gün ...]   (freezegun gerekir)
"""
import io
import os
import sys
import unittest
from datetime import datetime, timedelta

from freezegun import freeze_time

BOT = os.path.dirname(os.path.abspath(__file__))


def kos(gun):
    with freeze_time(datetime.now() + timedelta(days=gun), tick=True):
        suite = unittest.defaultTestLoader.discover(BOT, pattern='test_*.py', top_level_dir=BOT)
        sonuc = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    bozuk = sorted({str(t[0]) for t in sonuc.failures + sonuc.errors})
    print(f'+{gun} gün: {sonuc.testsRun} test, {len(bozuk)} bozuk')
    for b in bozuk:
        print('   ', b)
    return bozuk


if __name__ == '__main__':
    os.chdir(BOT)
    sys.path.insert(0, BOT)
    gunler = [int(g) for g in sys.argv[1:]] or [7, 30]
    sys.exit(1 if any([kos(g) for g in gunler]) else 0)
