"""Özel paylaşım sırası: sosyal/ozel/sira.json içinden zamanı gelmiş, henüz paylaşılmamış ilk tanımı seçer.

sira.json: [{"tanim": "sosyal/ozel/x.json", "zaman": "2026-11-22T18:00:00+03:00"}]
Paylaşılmış sayılır: sosyal/gecmis.json'da anahtar 'ozel:<tanım adı>' kaydı var.
Çıktı (GitHub Actions çıktısı biçiminde): 'tanim=<yol>' ya da hiçbir şey."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))
GEC_KALMA = timedelta(hours=4)    # zamanından bu kadar geç kalan öğe o gün atlanır (27 Kas 2026: 20 saat gece paylaşımına yol açıyordu)


def siradaki(sira, gecmis, simdi):
    paylasilan = {g.get('anahtar') for g in gecmis}
    for o in sira:
        zaman = datetime.fromisoformat(o['zaman'])
        if zaman <= simdi < zaman + GEC_KALMA and f'ozel:{Path(o["tanim"]).stem}' not in paylasilan:
            return o['tanim']
    return None


def main():
    yol = ROOT / 'sosyal' / 'ozel' / 'sira.json'
    sira = json.loads(yol.read_text(encoding='utf-8')) if yol.exists() else []
    gecmis = json.loads((ROOT / 'sosyal' / 'gecmis.json').read_text(encoding='utf-8'))
    tanim = siradaki(sira, gecmis, datetime.now(TR))
    if tanim:
        print(f'tanim={tanim}')
    else:
        print('Sırada zamanı gelmiş paylaşım yok.', file=sys.stderr)


if __name__ == '__main__':
    main()
