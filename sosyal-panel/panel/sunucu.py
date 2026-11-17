"""Yerel web sunucusu (yalnız 127.0.0.1). Standart kütüphane; ek kurulum gerekmez."""
import json
import mimetypes
import os
import sys
import threading
import time
import traceback
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import analiz as an
from .db import Depo
from .topla import PLATFORMLAR, hepsini_topla

STATIK = Path(__file__).resolve().parent / 'statik'
OTOMATIK_ARALIK = 60 * 60   # açıkken saatte bir toplar


def veri_klasoru():
    taban = os.environ.get('LOCALAPPDATA') or str(Path.home() / '.local' / 'share')
    return Path(taban) / 'KPSSTercihi' / 'sosyal-panel'


class Uygulama:
    def __init__(self, depo, ornek=False, topla=True):
        self.depo, self.ornek, self.topla_acik = depo, ornek, topla
        self._kilit = threading.Lock()

    def gonderiler(self):
        with self._kilit:
            return an.zenginlestir(self.depo.gonderiler())

    def durum(self):
        with self._kilit:
            durumlar = {d['kaynak']: d for d in self.depo.durumlar()}
            toplama = self.depo.ayar('toplama')
        return {'ornek': self.ornek, 'platformlar': PLATFORMLAR, 'kaynaklar': durumlar, 'toplama': toplama}

    def yenile(self, bulut=False):
        if self.ornek or not self.topla_acik:
            return {'calisiyor': False, 'atlandi': True}
        threading.Thread(target=hepsini_topla, args=(self.depo,), kwargs={'bulut_tetikle': bulut}, daemon=True).start()
        return {'calisiyor': True}


def isleyici(uyg):
    class Isleyici(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, veri, kod=200):
            govde = json.dumps(veri, ensure_ascii=False, default=str).encode('utf-8')
            self.send_response(kod)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)

        def do_GET(self):
            adres = urllib.parse.urlsplit(self.path)
            q = dict(urllib.parse.parse_qsl(adres.query))
            if adres.path == '/api/durum':
                return self._json(uyg.durum())
            if adres.path == '/api/gonderiler':
                g = uyg.gonderiler()
                return self._json({'gonderiler': g, 'ozet': an.ozet(g)})
            if adres.path == '/api/seri':
                with uyg._kilit:
                    return self._json({'seri': uyg.depo.seri(q.get('id', ''))})
            if adres.path == '/api/analiz':
                return self._json(an.analiz(uyg.gonderiler(), q.get('platform') or None, q.get('gun') or None))
            return self._statik(adres.path)

        def do_POST(self):
            adres = urllib.parse.urlsplit(self.path)
            # Yalnız aynı kaynaktan gelen istekler (başka sitelerin bu uca istek atmasını engeller).
            koken = self.headers.get('Origin')
            if koken and urllib.parse.urlsplit(koken).hostname not in ('127.0.0.1', 'localhost'):
                return self._json({'hata': 'izin yok'}, 403)
            if adres.path == '/api/yenile':
                q = dict(urllib.parse.parse_qsl(adres.query))
                return self._json(uyg.yenile(bulut=q.get('bulut') == '1'))
            return self._json({'hata': 'yok'}, 404)

        def _statik(self, yol):
            yol = 'index.html' if yol in ('', '/') else yol.lstrip('/')
            dosya = (STATIK / yol).resolve()
            if STATIK not in dosya.parents or not dosya.is_file():
                self.send_error(404)
                return
            govde = dosya.read_bytes()
            self.send_response(200)
            tur = mimetypes.guess_type(dosya.name)[0] or 'application/octet-stream'
            self.send_header('Content-Type', tur + ('; charset=utf-8' if tur.startswith('text/') or tur.endswith('javascript') else ''))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)
    return Isleyici


def calistir(port=8765, ornek=False, tarayici=True, topla=True, veri=None):
    klasor = Path(veri) if veri else veri_klasoru()
    klasor.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or sys.stderr is None:   # pythonw (penceresiz): çıktılar günlük dosyasına
        gunluk = open(klasor / 'panel.log', 'a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = gunluk
    gunluk_dosyasi = klasor / 'panel.log'
    hata_kancalari_kur(gunluk_dosyasi)
    try:
        depo = Depo(klasor / ('ornek.db' if ornek else 'panel.db'))
        if ornek and not depo.gonderiler():
            from .ornek import doldur
            doldur(depo)
        uyg = Uygulama(depo, ornek=ornek, topla=topla)
        sunucu = DayanikliSunucu(('127.0.0.1', port), isleyici(uyg))
        sunucu.gunluk_dosyasi = gunluk_dosyasi
        adres = f'http://127.0.0.1:{port}/'
        if topla and not ornek:
            threading.Thread(target=lambda: toplama_dongusu(depo, gunluk_dosyasi), daemon=True).start()
        if tarayici:
            import webbrowser
            threading.Timer(0.6, lambda: webbrowser.open(adres)).start()
        print(f'Sosyal panel: {adres}  (veri: {depo.yol})')
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass
    except BaseException:   # sessizce kapanmasın: neden panel.log'a yazılır, sonra çıkış sürer
        gunluge_yaz(gunluk_dosyasi, 'Sunucu beklenmeyen hatayla kapanıyor', traceback.format_exc())
        raise


def gunluge_yaz(dosya, baslik, ayrinti=''):
    """panel.log'a zaman damgalı satır ekler; kendisi asla hata fırlatmaz."""
    try:
        with open(dosya, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {baslik}\n{ayrinti}")
            if ayrinti and not ayrinti.endswith('\n'):
                f.write('\n')
    except OSError:
        pass


def hata_kancalari_kur(dosya):
    """Yakalanmamış istisnalar (ana iş parçacığı ve diğer iş parçacıkları) panel.log'a düşer."""
    def ana(tur, deger, iz):
        gunluge_yaz(dosya, f'Yakalanmamış hata: {tur.__name__}', ''.join(traceback.format_exception(tur, deger, iz)))

    def parca(a):
        if a.exc_type is SystemExit:
            return
        gunluge_yaz(dosya, f'Yakalanmamış hata (iş parçacığı {getattr(a.thread, "name", "?")}): {a.exc_type.__name__}',
                    ''.join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
    sys.excepthook = ana
    threading.excepthook = parca


def toplama_dongusu(depo, dosya, aralik=None, tur=None):
    """Saatlik toplayıcı: hiçbir hata döngüyü (ve sunucuyu) öldürmez."""
    sayac = 0
    while tur is None or sayac < tur:
        sayac += 1
        try:
            hepsini_topla(depo)
        except BaseException:   # SystemExit/KeyboardInterrupt dahil: bu iş parçacığı sunucuyu düşüremez
            gunluge_yaz(dosya, 'Otomatik toplama hatası (döngü sürüyor)', traceback.format_exc())
        time.sleep(OTOMATIK_ARALIK if aralik is None else aralik)


class DayanikliSunucu(ThreadingHTTPServer):
    gunluk_dosyasi = None

    def handle_error(self, request, client_address):
        if self.gunluk_dosyasi:
            gunluge_yaz(self.gunluk_dosyasi, f'İstek hatası ({client_address[0]})', traceback.format_exc())
        else:
            super().handle_error(request, client_address)
