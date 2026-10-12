"""Yeni yayımlanan sayfaları IndexNow ile Bing'e (ChatGPT aramasının dayandığı dizin), Yandex vb. bildirir.

Ücretsizdir, hesap gerektirmez: anahtar docs/<ANAHTAR>.txt olarak sitede yayımlanır, gizli değildir.
Kullanım: python bot/indexnow.py <eski-sitemap.xml>   → yalnız yeni adresler
          python bot/indexnow.py --hepsi                → tüm site haritası (ilk kurulum)
Bu adım işi asla düşürmez.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ANAHTAR = '29cecb3e9c3e4d3a1b2029610ebb0f23'
HOST = 'kpsstercihi.com'
BASE = f'https://{HOST}/'
HARITA = Path(__file__).resolve().parents[1] / 'docs' / 'sitemap.xml'
UC = 'https://api.indexnow.org/indexnow'


def adresler(metin):
    return re.findall(r'<loc>([^<]+)</loc>', metin or '')


def bildirilecek(yeni_harita, eski_harita=None):
    """eski_harita None ise hepsi; değilse yalnız yeni adresler (+ yeni varsa ana sayfa ve llms.txt)."""
    yeni = adresler(yeni_harita)
    if eski_harita is None:
        return yeni + [BASE + 'llms.txt']
    eski = set(adresler(eski_harita))
    fark = [u for u in yeni if u not in eski]
    if not fark:
        return []
    return list(dict.fromkeys([BASE, BASE + 'llms.txt'] + fark))


def gonder(liste, ac=urllib.request.urlopen):
    govde = json.dumps({'host': HOST, 'key': ANAHTAR, 'keyLocation': f'{BASE}{ANAHTAR}.txt', 'urlList': liste[:10000]}).encode()
    istek = urllib.request.Request(UC, data=govde, headers={'Content-Type': 'application/json; charset=utf-8'})
    with ac(istek, timeout=30) as yanit:
        return yanit.status


def main(argv):
    try:
        yeni = HARITA.read_text(encoding='utf-8')
        if argv and argv[0] == '--hepsi':
            eski = None
        else:
            yol = Path(argv[0]) if argv else None
            if not yol or not yol.is_file() or not adresler(yol.read_text(encoding='utf-8', errors='replace')):
                print('Eski site haritası yok; IndexNow atlandı.')
                return
            eski = yol.read_text(encoding='utf-8', errors='replace')
        liste = bildirilecek(yeni, eski)
        if not liste:
            print('Yeni sayfa yok; IndexNow bildirimi gerekmedi.')
            return
        print(f'IndexNow: {len(liste)} adres bildirildi (HTTP {gonder(liste)}).')
    except Exception as hata:  # noqa: BLE001 - bildirim hatası yayını durdurmaz
        print(f'IndexNow bildirilemedi ({type(hata).__name__}: {hata}); devam ediliyor.')


if __name__ == '__main__':
    main(sys.argv[1:])
