"""Yerel Facebook kurulum formu. Anahtar yalnız bellekte ve GitHub Secrets'ta tutulur."""
import html
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SAYFA = '1456851867512312'
REPO = 'enesfeched-maker/kamu-ilan-takip'
ADRES = 'http://127.0.0.1:8790'
NONCE = secrets.token_urlsafe(32)
SONUC = 'Anahtar bekleniyor'


def canli_dene(anahtar):
    from sosyal_yayinla import facebook
    durum_yolu = Path(__file__).resolve().parents[1] / '.cache' / 'facebook-canli-test.json'
    durum_yolu.parent.mkdir(exist_ok=True)
    def al(url):
        req = urllib.request.Request(url, headers={'User-Agent': 'kpsstercihi-kurulum'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    gecmis = al(f'https://raw.githubusercontent.com/{REPO}/main/sosyal/gecmis.json')
    for surum in al(f'https://api.github.com/repos/{REPO}/releases?per_page=10'):
        dosyalar = {a['name']: a['browser_download_url'] for a in surum.get('assets', [])}
        if not {'paylasim.json', 'reel.mp4'}.issubset(dosyalar):
            continue
        metin = al(dosyalar['paylasim.json'])
        if not any(g.get('zaman') == metin.get('zaman') and (g.get('ig_id') or g.get('tt_id')) for g in gecmis):
            continue
        if durum_yolu.exists():
            eski = json.loads(durum_yolu.read_text(encoding='utf-8'))
            if eski.get('etiket') == surum['tag_name']:
                return eski
        kayit = {'etiket': surum['tag_name'], 'durum': 'belirsiz'}
        durum_yolu.write_text(json.dumps(kayit), encoding='utf-8')
        os.environ.update(FB_SAYFA_ID=SAYFA, FB_ERISIM_ANAHTARI=anahtar, VIDEO_URL=dosyalar['reel.mp4'])
        try:
            kayit.update(facebook(None, metin))
        finally:
            os.environ.pop('FB_ERISIM_ANAHTARI', None)
        durum_yolu.write_text(json.dumps(kayit), encoding='utf-8')
        for _ in range(12):
            durum = graph(kayit['id'], anahtar, {'fields': 'status'}).get('status') or {}
            if (durum.get('publishing_phase') or {}).get('status') == 'complete':
                kayit['durum'] = 'published'
                break
            if durum.get('video_status') == 'error':
                kayit['durum'] = 'error'
                break
            time.sleep(5)
        durum_yolu.write_text(json.dumps(kayit), encoding='utf-8')
        return kayit
    raise ValueError('Deneme için yayımlanmış sosyal video bulunamadı.')


def graph(yol, anahtar, parametreler=None):
    adres = 'https://graph.facebook.com/v27.0/' + yol
    if parametreler:
        adres += '?' + urllib.parse.urlencode(parametreler)
    req = urllib.request.Request(adres, headers={'Authorization': 'Bearer ' + anahtar})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def kaydet(kullanici_anahtari):
    # Uzun ömürlü kullanıcı anahtarından yalnız istenen sayfanın anahtarı alınır.
    incele = graph('debug_token', kullanici_anahtari, {'input_token': kullanici_anahtari})['data']
    if not incele.get('is_valid') or str(incele.get('app_id')) != '1134321295736637':
        raise ValueError('KPSS Tercihi uygulamasına ait geçerli anahtar gerekli.')
    if incele.get('expires_at', 0) and incele['expires_at'] < time.time() + 86400:
        raise ValueError('Anahtar kısa ömürlü. Meta Debugger üzerinden Extend Access Token adımını tamamla.')
    gereken = {'pages_manage_posts', 'pages_read_engagement', 'pages_show_list'}
    if not gereken.issubset(incele.get('scopes') or []):
        raise ValueError('Facebook yayınlama izinleri eksik.')
    sayfa = graph(SAYFA, kullanici_anahtari, {'fields': 'id,name,access_token'})
    if str(sayfa.get('id')) != SAYFA or sayfa.get('name') != 'KPSS Tercihi' or not sayfa.get('access_token'):
        raise ValueError('KPSS Tercihi sayfasının anahtarı alınamadı.')
    anahtar = sayfa['access_token']
    if str(graph('me', anahtar, {'fields': 'id'}).get('id')) != SAYFA:
        raise ValueError('Sayfa kimliği uyuşmuyor; işlem durduruldu.')
    sonuc = subprocess.run(['gh', 'secret', 'set', 'FB_ERISIM_ANAHTARI', '--repo', REPO],
                           input=anahtar, text=True, capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if sonuc.returncode:
        raise ValueError('GitHub gizli ayarı kaydedilemedi.')
    sonuc = subprocess.run(['gh', 'variable', 'set', 'FB_SAYFA_ID', '--repo', REPO, '--body', SAYFA],
                           capture_output=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if sonuc.returncode:
        raise ValueError('GitHub sayfa kimliği kaydedilemedi.')
    return anahtar


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # İstek gövdesi ve anahtar günlükte tutulmaz.

    def yanit(self, metin, kod=200):
        veri = metin.encode('utf-8')
        self.send_response(kod)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(veri)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        self.yanit(f'''<!doctype html><html lang="tr"><meta charset="utf-8"><title>Facebook bot bağlantısı</title>
<style>body{{font:18px system-ui;max-width:650px;margin:60px auto;padding:24px}}input{{width:100%;padding:12px;box-sizing:border-box}}button{{margin-top:20px;padding:12px}}</style>
<h1>Facebook bot bağlantısı</h1><p>Hedef sayfa: <b>KPSS Tercihi</b></p><p>{html.escape(SONUC)}</p>
<form method="post"><input type="hidden" name="nonce" value="{NONCE}"><label for="token">Uzun ömürlü kullanıcı erişim anahtarı</label>
<input id="token" name="token" type="password" autocomplete="off" required>
<button type="submit">Sayfa bağlantısını kaydet</button></form>
<p>Anahtar Meta’da doğrulanır ve botun GitHub gizli ayarlarına kaydedilir. Bu form anahtarı diske veya günlüğe yazmaz.</p></html>''')

    def do_POST(self):
        global SONUC
        if self.headers.get('Origin') != ADRES:
            return self.yanit('İstek kabul edilmedi.', 403)
        uzunluk = int(self.headers.get('Content-Length', '0'))
        if not 0 < uzunluk < 16000:
            return self.yanit('Geçersiz istek.', 400)
        veri = urllib.parse.parse_qs(self.rfile.read(uzunluk).decode())
        if not secrets.compare_digest(veri.get('nonce', [''])[0], NONCE):
            return self.yanit('Geçersiz kurulum oturumu.', 403)
        try:
            anahtar = kaydet(veri.get('token', [''])[0].strip())
            SONUC = 'KPSS Tercihi sayfa anahtarı GitHub’a güvenli olarak kaydedildi.'
            if '--dene' in sys.argv:
                sonuc = canli_dene(anahtar)
                SONUC += ' Deneme: ' + sonuc['durum'] + ' ' + sonuc.get('baglanti', '')
        except ValueError as hata:
            SONUC = str(hata)
        except Exception:
            SONUC = 'Meta veya GitHub bağlantısı doğrulanamadı. Anahtarı ve izinleri kontrol et.'
        self.do_GET()


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8790), Handler).serve_forever()
