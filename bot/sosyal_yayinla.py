"""Üretilen paylaşımı (sosyal_motor çıktısı: reel.mp4 + paylasim.json) resmî API'lerle yayınlar.

Her platform yalnız anahtarları GitHub sırlarında tanımlıysa çalışır; biri hata verirse diğerleri yine denenir.
  Instagram (Instagram Login API, profesyonel hesap): IG_KULLANICI_ID, IG_ERISIM_ANAHTARI
  YouTube Shorts (Data API v3, OAuth):               YT_ISTEMCI_KIMLIGI, YT_ISTEMCI_SIRRI, YT_YENILEME_ANAHTARI
  TikTok (Content Posting API):                      TT_ISTEMCI_ANAHTARI, TT_ISTEMCI_SIRRI, TT_YENILEME_ANAHTARI
                                                     TT_MOD=taslak (varsayılan; uygulamadaki gelen kutusuna düşer)
                                                     ya da dogrudan (TikTok incelemesi onaylandıktan sonra)
Yenilenen anahtarlar (Instagram haftada bir, TikTok her seferinde dönebilir) SOSYAL_GH_ANAHTARI tanımlıysa
GitHub sırrına geri yazılır; tanımlı değilse yalnız uyarı verilir. Anahtarlar hiçbir zaman yazdırılmaz.

Kullanım: python bot/sosyal_yayinla.py sosyal-cikti [--instagram-yenile]"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

IG_SURUM = 'v23.0'
ZAMAN_ASIMI = 120


class YayinHatasi(Exception):
    pass


def _istek(url, veri=None, json_veri=None, basliklar=None, yontem=None, zaman_asimi=ZAMAN_ASIMI, ham=False):
    basliklar = dict(basliklar or {})
    govde = None
    if json_veri is not None:
        govde = json.dumps(json_veri).encode()
        basliklar.setdefault('Content-Type', 'application/json; charset=UTF-8')
    elif isinstance(veri, (bytes, bytearray)):
        govde = bytes(veri)
    elif veri is not None:
        govde = urllib.parse.urlencode(veri).encode()
        basliklar.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    req = urllib.request.Request(url, data=govde, headers=basliklar, method=yontem)
    try:
        with urllib.request.urlopen(req, timeout=zaman_asimi) as r:
            icerik = r.read()
            return (r, icerik) if ham else (json.loads(icerik or b'{}') if icerik else {})
    except urllib.error.HTTPError as h:
        metin = h.read().decode('utf-8', 'replace')[:500]
        raise YayinHatasi(f'HTTP {h.code}: {metin}') from None


def _env(*adlar):
    degerler = [os.environ.get(a, '').strip() for a in adlar]
    return degerler if all(degerler) else None


def sir_guncelle(ad, deger):
    """Yenilenen anahtarı GitHub sırrına yazar (SOSYAL_GH_ANAHTARI: yalnız 'secrets' yazma izinli ince anahtar)."""
    pat, repo = os.environ.get('SOSYAL_GH_ANAHTARI'), os.environ.get('GITHUB_REPOSITORY')
    if not (pat and repo):
        print(f'Uyarı: {ad} yenilendi ama SOSYAL_GH_ANAHTARI yok; sır güncellenemedi.')
        return False
    sonuc = subprocess.run(['gh', 'secret', 'set', ad, '--repo', repo], input=deger, text=True,
                           capture_output=True, env=dict(os.environ, GH_TOKEN=pat))
    if sonuc.returncode != 0:
        print(f'Uyarı: {ad} sırrı güncellenemedi.')
        return False
    return True


# ---------------------------------------------------------------- Instagram
def instagram(video, metin, ortam=None):
    ig_id, anahtar = ortam or _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI') or (None, None)
    if not ig_id:
        return None
    taban = f'https://graph.instagram.com/{IG_SURUM}'
    kap = _istek(f'{taban}/{ig_id}/media', veri={'media_type': 'REELS', 'upload_type': 'resumable',
                                                 'caption': metin['aciklama'], 'share_to_feed': 'true',
                                                 'access_token': anahtar})
    kap_id = kap.get('id')
    if not kap_id:
        raise YayinHatasi(f'Instagram kapsayıcı oluşturulamadı: {kap}')
    veri = Path(video).read_bytes()
    _istek(f'https://rupload.facebook.com/ig-api-upload/{IG_SURUM}/{kap_id}', veri=veri,
           basliklar={'Authorization': f'OAuth {anahtar}', 'offset': '0', 'file_size': str(len(veri))}, zaman_asimi=600)
    for _ in range(60):  # en çok ~5 dk işleme beklenir
        durum = _istek(f'{taban}/{kap_id}?fields=status_code,status&access_token={urllib.parse.quote(anahtar)}')
        kod = durum.get('status_code')
        if kod == 'FINISHED':
            break
        if kod in ('ERROR', 'EXPIRED'):
            raise YayinHatasi(f'Instagram videoyu işleyemedi: {durum.get("status")}')
        time.sleep(5)
    else:
        raise YayinHatasi('Instagram video işleme zaman aşımı')
    yayin = _istek(f'{taban}/{ig_id}/media_publish', veri={'creation_id': kap_id, 'access_token': anahtar})
    return {'id': yayin.get('id')}


def instagram_yenile():
    """Uzun ömürlü anahtar 60 gün geçerli; haftada bir yenilenir (en az 24 saatlik olmalı)."""
    ortam = _env('IG_ERISIM_ANAHTARI')
    if not ortam:
        return None
    yanit = _istek('https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token='
                   + urllib.parse.quote(ortam[0]))
    yeni = yanit.get('access_token')
    if yeni and yeni != ortam[0]:
        sir_guncelle('IG_ERISIM_ANAHTARI', yeni)
    print(f'Instagram anahtarı yenilendi; {int(yanit.get("expires_in") or 0) // 86400} gün geçerli.')
    return True


# ---------------------------------------------------------------- YouTube
def youtube(video, metin, ortam=None):
    kimlik = ortam or _env('YT_ISTEMCI_KIMLIGI', 'YT_ISTEMCI_SIRRI', 'YT_YENILEME_ANAHTARI')
    if not kimlik:
        return None
    istemci, sir, yenileme = kimlik
    erisim = _istek('https://oauth2.googleapis.com/token', veri={
        'client_id': istemci, 'client_secret': sir, 'refresh_token': yenileme, 'grant_type': 'refresh_token'})['access_token']
    beklenen = os.environ.get('YT_KANAL', '').strip()
    if beklenen:  # yanlış kanala yüklemeyi önler (anahtar youtube.readonly kapsamını da içermeli)
        kanallar = _istek('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                          basliklar={'Authorization': f'Bearer {erisim}'}).get('items') or []
        adlar = [(c.get('snippet') or {}).get('title', '') for c in kanallar]
        if beklenen.casefold() not in [a.casefold() for a in adlar]:
            raise YayinHatasi(f'Anahtar "{beklenen}" kanalına ait değil ({", ".join(adlar) or "kanal yok"}); yüklenmedi.')
    veri = Path(video).read_bytes()
    govde = {
        'snippet': {'title': metin['baslik'][:100], 'description': metin['aciklama'][:4900],
                    'tags': [e.lstrip('#') for e in metin.get('etiketler', [])] + ['kpss', 'kamu ilanları', 'memur alımı'],
                    'categoryId': '27', 'defaultLanguage': 'tr', 'defaultAudioLanguage': 'tr'},
        'status': {'privacyStatus': os.environ.get('YT_GORUNURLUK', 'public'), 'selfDeclaredMadeForKids': False},
    }
    yanit, _ = _istek('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
                      json_veri=govde, ham=True, basliklar={
                          'Authorization': f'Bearer {erisim}', 'X-Upload-Content-Type': 'video/mp4',
                          'X-Upload-Content-Length': str(len(veri))})
    yer = yanit.headers.get('Location')
    if not yer:
        raise YayinHatasi('YouTube yükleme adresi alınamadı')
    sonuc = _istek(yer, veri=veri, yontem='PUT', zaman_asimi=600,
                   basliklar={'Authorization': f'Bearer {erisim}', 'Content-Type': 'video/mp4'})
    return {'id': sonuc.get('id'), 'kanal': (sonuc.get('snippet') or {}).get('channelTitle'),
            'gorunurluk': (sonuc.get('status') or {}).get('privacyStatus')}


# ---------------------------------------------------------------- TikTok
def _tiktok_erisim(istemci, sir, yenileme):
    yanit = _istek('https://open.tiktokapis.com/v2/oauth/token/', veri={
        'client_key': istemci, 'client_secret': sir, 'grant_type': 'refresh_token', 'refresh_token': yenileme})
    if 'access_token' not in yanit:
        raise YayinHatasi(f'TikTok anahtarı yenilenemedi: {yanit.get("error_description") or yanit.get("error")}')
    yeni = yanit.get('refresh_token')
    if yeni and yeni != yenileme:
        sir_guncelle('TT_YENILEME_ANAHTARI', yeni)
    return yanit['access_token']


def tiktok(video, metin, ortam=None, mod=None):
    kimlik = ortam or _env('TT_ISTEMCI_ANAHTARI', 'TT_ISTEMCI_SIRRI', 'TT_YENILEME_ANAHTARI')
    if not kimlik:
        return None
    mod = mod or os.environ.get('TT_MOD', 'taslak')
    erisim = _tiktok_erisim(*kimlik)
    b = {'Authorization': f'Bearer {erisim}'}
    boyut = Path(video).stat().st_size
    kaynak = {'source': 'FILE_UPLOAD', 'video_size': boyut, 'chunk_size': boyut, 'total_chunk_count': 1}
    if mod == 'dogrudan':
        bilgi = _istek('https://open.tiktokapis.com/v2/post/publish/creator_info/query/', json_veri={}, basliklar=b)
        secenek = (bilgi.get('data') or {}).get('privacy_level_options') or ['SELF_ONLY']
        gizlilik = 'PUBLIC_TO_EVERYONE' if 'PUBLIC_TO_EVERYONE' in secenek else secenek[0]
        govde = {'post_info': {'title': metin['aciklama'][:2200], 'privacy_level': gizlilik, 'disable_comment': False,
                               'disable_duet': False, 'disable_stitch': False},
                 'source_info': kaynak}
        yol = 'https://open.tiktokapis.com/v2/post/publish/video/init/'
    else:
        govde, yol, gizlilik = {'source_info': kaynak}, 'https://open.tiktokapis.com/v2/post/publish/inbox/video/init/', 'taslak'
    yanit = _istek(yol, json_veri=govde, basliklar=b)
    veri = yanit.get('data') or {}
    if not veri.get('upload_url'):
        raise YayinHatasi(f'TikTok yükleme başlatılamadı: {(yanit.get("error") or {}).get("message")}')
    _istek(veri['upload_url'], veri=Path(video).read_bytes(), yontem='PUT', zaman_asimi=600, basliklar={
        'Content-Type': 'video/mp4', 'Content-Range': f'bytes 0-{boyut - 1}/{boyut}', 'Content-Length': str(boyut)})
    return {'id': veri.get('publish_id'), 'gorunurluk': gizlilik}


PLATFORMLAR = (('instagram', instagram), ('youtube', youtube), ('tiktok', tiktok))


def yayinla(klasor):
    klasor = Path(klasor)
    metin = json.loads((klasor / 'paylasim.json').read_text(encoding='utf-8'))
    video = klasor / 'reel.mp4'
    sonuclar, hatali = {}, False
    for ad, islev in PLATFORMLAR:
        try:
            sonuc = islev(video, metin)
        except Exception as hata:  # bir platformun hatası diğerlerini durdurmaz
            sonuc, hatali = {'hata': str(hata)[:300]}, True
        if sonuc is None:
            print(f'{ad}: anahtar tanımlı değil, atlandı.')
            continue
        sonuclar[ad] = sonuc
        print(f'{ad}: {sonuc}')
    (klasor / 'sonuc.json').write_text(json.dumps(sonuclar, ensure_ascii=False, indent=1), encoding='utf-8')
    return sonuclar, hatali


if __name__ == '__main__':
    if '--instagram-yenile' in sys.argv:
        try:
            instagram_yenile()
        except Exception as hata:
            print(f'Uyarı: Instagram anahtarı yenilenemedi: {hata}')
    _, hata_var = yayinla(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'sosyal-cikti')
    sys.exit(1 if hata_var else 0)
