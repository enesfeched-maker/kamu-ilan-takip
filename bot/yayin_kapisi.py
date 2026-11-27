"""Sosyal yayın saat kapısı (27 Kasım 2026).

GitHub'ın zamanlanmış işleri saatlerce gecikiyordu: öğle videosu 04:00–06:30, özel videolar 02:00–06:00 arasında
çıkıyordu (izleyen yok). Asıl tetik artık Cloudflare zamanlayıcısı (zamanlayici/, dakikası dakikasına); GitHub
cron'u yedek kalır. Bu kapı, hangi yoldan gelirse gelsin yayının yalnız kendi saat penceresinde ve günde bir kez
çıkmasını sağlar.

Kullanım: python bot/yayin_kapisi.py <vakit> [--elle]
Çıktı (GitHub Actions çıktısı biçiminde): 'izin=1' ya da 'izin=0' (+ stderr'e neden)."""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))
# vakit: (ilk saat, son saat hariç) — TR saati. Tetik: 12:30, 18:00, 21:00 (zamanlayici/src/index.js).
PENCERE = {
    'sabah': (12, 15),      # öğle videosu (12:30)
    'ilan': (17, 20),       # akşamüstü: yeni ilan videosu ya da sıradaki özel video (18:00)
    'aksam': (20, 23),      # akşam videosu (21:00)
    'haftalik': (18, 22),   # pazar 19:00
    'ozel': (12, 22),       # elle hazırlanan özel videolar (sira.json zamanı + bu pencere)
    'gorsel': (9, 22),      # hikâye ve ilan karuselleri (gece yığını olmasın)
}


def gecmis_oku(yol=ROOT / 'sosyal' / 'gecmis.json'):
    try:
        return json.loads(Path(yol).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return []


def bugun_yapildi(gecmis, vakit, simdi):
    """sabah/aksam/haftalik/ilan: bugün bu vakit için geçmişe kayıt yazıldıysa True."""
    gun = simdi.date().isoformat()
    return any(g.get('vakit') == vakit and str(g.get('zaman', ''))[:10] == gun for g in gecmis)


def karar(vakit, simdi, gecmis, elle=False):
    """(izin, neden). Elle başlatılan çalışma saat kapısına takılmaz (kullanıcı/ben bilerek başlattık)."""
    if elle:
        return True, 'elle başlatıldı'
    bas, son = PENCERE[vakit]
    if not bas <= simdi.hour < son:
        return False, f'{vakit} penceresi dışında ({simdi:%H:%M}; pencere {bas:02d}:00–{son:02d}:00)'
    if vakit in ('sabah', 'aksam', 'haftalik') and bugun_yapildi(gecmis, vakit, simdi):
        return False, f'bugünün {vakit} paylaşımı zaten yapıldı'
    return True, 'pencere içinde'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('vakit', choices=sorted(PENCERE))
    p.add_argument('--elle', action='store_true', help='elle başlatıldı (Cloudflare tetiği değil): saat kapısı uygulanmaz')
    a = p.parse_args()
    izin, neden = karar(a.vakit, datetime.now(TR), gecmis_oku(), a.elle)
    print(f'izin={1 if izin else 0}')
    print(f'Yayın kapısı ({a.vakit}): {neden}', file=sys.stderr)


if __name__ == '__main__':
    main()
