"""python -m panel [--port 8765] [--ornek] [--tarayici-yok] [--topla]

  (seçeneksiz)   sunucuyu başlatır, tarayıcıda açar, açıkken saatte bir veri toplar
  --topla        yalnız bir kez veri toplar ve çıkar (Görev Zamanlayıcı için)
  --ornek        geliştirme: ayrı veritabanında açıkça işaretli ÖRNEK veriyle açar
"""
import argparse
import socket
import sys
import webbrowser

from .db import Depo
from .sunucu import calistir, veri_klasoru
from .topla import hepsini_topla


def main(argv=None):
    p = argparse.ArgumentParser(prog='panel')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--ornek', action='store_true')
    p.add_argument('--tarayici-yok', action='store_true')
    p.add_argument('--topla', action='store_true')
    p.add_argument('--toplama-yok', action='store_true', help='sunucu açıkken otomatik toplama yapma')
    p.add_argument('--veri', help='veri klasörü (varsayılan %%LOCALAPPDATA%%\\KPSSTercihi\\sosyal-panel)')
    a = p.parse_args(argv)
    if a.topla:
        depo = Depo((a.veri and __import__('pathlib').Path(a.veri) or veri_klasoru()) / 'panel.db')
        sonuc = hepsini_topla(depo)
        print('\n'.join(sonuc.get('gunluk') or ['başka bir toplama sürüyor']))
        return 0
    with socket.socket() as s:   # zaten açıksa yalnız tarayıcıyı aç
        if s.connect_ex(('127.0.0.1', a.port)) == 0:
            if not a.tarayici_yok:
                webbrowser.open(f'http://127.0.0.1:{a.port}/')
            return 0
    calistir(port=a.port, ornek=a.ornek, tarayici=not a.tarayici_yok, topla=not a.toplama_yok, veri=a.veri)
    return 0


if __name__ == '__main__':
    sys.exit(main())
