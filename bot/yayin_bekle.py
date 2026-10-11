"""Pages yayını "başarılı" dendikten sonra da yeni sayfaların sunuculara yayılması bir-iki dakika sürebilir.
Telegram'daki ilan bağlantısı "sayfa bulunamadı" vermesin diye canlı liste.json, az önce üretilen yerel kopyayla
aynı olana kadar beklenir (en çok ~5 dk). Süre dolarsa gönderim yine yapılır; bu adım işi asla düşürmez."""
import hashlib
import time
import urllib.request
from pathlib import Path

YEREL = Path(__file__).resolve().parents[1] / 'docs' / 'liste.json'
URL = 'https://kpsstercihi.com/liste.json'


def _getir():
    istek = urllib.request.Request(f'{URL}?t={int(time.time())}',
                                   headers={'User-Agent': 'kpss-tercihi-bot', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(istek, timeout=20) as yanit:
        return yanit.read()


def bekle(yerel=YEREL, getir=_getir, uyu=time.sleep, deneme=20, aralik=15):
    if not yerel.is_file():
        print('Yerel liste.json yok; beklemeden devam ediliyor.')
        return False
    hedef = hashlib.sha256(yerel.read_bytes()).hexdigest()
    for n in range(deneme):
        try:
            if hashlib.sha256(getir()).hexdigest() == hedef:
                print(f'Canlı site güncel ({n * aralik} sn beklendi).')
                return True
        except Exception as hata:  # noqa: BLE001 - ağ hatası gönderimi durdurmaz
            print(f'Canlı site okunamadı ({type(hata).__name__}); tekrar denenecek.')
        if n < deneme - 1:
            uyu(aralik)
    print('Canlı site beklenen sürede güncellenmedi; gönderime yine de devam ediliyor.')
    return False


if __name__ == '__main__':
    bekle()
