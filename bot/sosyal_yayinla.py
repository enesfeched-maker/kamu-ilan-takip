"""Üretilen paylaşımı (sosyal_motor çıktısı: reel.mp4 + paylasim.json) resmî API'lerle yayınlar.

Her platform yalnız anahtarları GitHub sırlarında tanımlıysa çalışır; biri hata verirse diğerleri yine denenir.
  Facebook Reels (Meta Graph API):                  FB_SAYFA_ID, FB_ERISIM_ANAHTARI
  Instagram (Instagram Login API, profesyonel hesap): IG_KULLANICI_ID, IG_ERISIM_ANAHTARI
  YouTube Shorts (Data API v3, OAuth):               YT_ISTEMCI_KIMLIGI, YT_ISTEMCI_SIRRI, YT_YENILEME_ANAHTARI
  TikTok (Content Posting API):                      TT_ISTEMCI_ANAHTARI, TT_ISTEMCI_SIRRI, TT_YENILEME_ANAHTARI
                                                     TT_MOD=taslak (varsayılan; uygulamadaki gelen kutusuna düşer)
                                                     ya da dogrudan (TikTok incelemesi onaylandıktan sonra)
  TikTok, Buffer üzerinden (önerilen):               BUFFER_API_ANAHTARI tanımlıysa video taslak yerine Buffer ile
                                                     açıklaması ve kapağıyla hemen yayınlanır; Buffer hata verirse
                                                     taslak yöntemine dönülür.
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
    # Instagram Login API videoyu herkese açık adresten çeker (VIDEO_URL: önizleme sürümündeki reel.mp4);
    # adres yoksa doğrudan yükleme (resumable) denenir.
    video_url = os.environ.get('VIDEO_URL', '').strip()
    alanlar = {'media_type': 'REELS', 'caption': metin['aciklama'], 'share_to_feed': 'true', 'access_token': anahtar}
    alanlar.update({'video_url': video_url} if video_url else {'upload_type': 'resumable'})
    kap = _istek(f'{taban}/{ig_id}/media', veri=alanlar)
    kap_id = kap.get('id')
    if not kap_id:
        raise YayinHatasi(f'Instagram kapsayıcı oluşturulamadı: {kap}')
    if not video_url:
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
        try:
            kanallar = _istek('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                              basliklar={'Authorization': f'Bearer {erisim}'}).get('items') or []
        except YayinHatasi:
            izinler = _istek('https://oauth2.googleapis.com/tokeninfo?access_token=' + urllib.parse.quote(erisim)).get('scope')
            raise YayinHatasi(f'Kanal doğrulanamadı; anahtarın izinleri: {izinler}. youtube.readonly ya da youtube gerekir.') from None
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


def youtube_kontrol():
    """Video yüklemeden YouTube anahtarını sınar: yenileme anahtarı geçerli mi, hangi izinler var, hangi kanal."""
    kimlik = _env('YT_ISTEMCI_KIMLIGI', 'YT_ISTEMCI_SIRRI', 'YT_YENILEME_ANAHTARI')
    if not kimlik:
        print('YouTube anahtarları tanımlı değil.')
        return False
    istemci, sir, yenileme = kimlik
    try:
        erisim = _istek('https://oauth2.googleapis.com/token', veri={
            'client_id': istemci, 'client_secret': sir, 'refresh_token': yenileme, 'grant_type': 'refresh_token'})['access_token']
    except YayinHatasi as hata:
        print(f'YouTube yenileme anahtarı KABUL EDİLMEDİ: {hata}')
        return False
    izinler = _istek('https://oauth2.googleapis.com/tokeninfo?access_token=' + urllib.parse.quote(erisim)).get('scope')
    print(f'Yenileme anahtarı geçerli. İzinler: {izinler}')
    beklenen = os.environ.get('YT_KANAL', '').strip()
    if beklenen:
        try:
            kanallar = _istek('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                              basliklar={'Authorization': f'Bearer {erisim}'}).get('items') or []
            adlar = [(c.get('snippet') or {}).get('title', '') for c in kanallar]
            print(f'Kanal: {", ".join(adlar) or "yok"} (beklenen: {beklenen}) -> '
                  f'{"EŞLEŞTİ" if beklenen.casefold() in [a.casefold() for a in adlar] else "EŞLEŞMEDİ"}')
        except YayinHatasi as hata:
            print(f'Kanal doğrulanamadı (youtube.readonly izni yok; YT_KANAL değişkeni bu yüzden yüklemeyi durdurur): {hata}')
            return False
    return True


# ---------------------------------------------------------------- Buffer (TikTok'a doğrudan yayın)
BUFFER_ADRESI = 'https://api.buffer.com'
BUFFER_KAPAK_MS = 2500   # kapak: videonun bu anındaki kare (ilk sahnenin başlığı yerine oturduktan sonra)


def _buffer(sorgu, anahtar):
    yanit = _istek(BUFFER_ADRESI, json_veri={'query': sorgu}, basliklar={'Authorization': f'Bearer {anahtar}'})
    if yanit.get('errors'):
        raise YayinHatasi(f"Buffer: {str(yanit['errors'][0].get('message'))[:200]}")
    return yanit.get('data') or {}


def buffer_kanal(anahtar, servis='tiktok'):
    """İstenen servisin kanalı; varsa servise özgü BUFFER_*_KANAL ayarı kullanılır."""
    hazir = os.environ.get(f'BUFFER_{servis.upper()}_KANAL', '').strip()
    if hazir:
        return hazir
    kurumlar = ((_buffer('query { account { organizations { id } } }', anahtar).get('account') or {}).get('organizations')) or []
    for kurum in kurumlar:
        sorgu = 'query { channels(input: { organizationId: %s }) { id service isDisconnected } }' % json.dumps(kurum['id'])
        for kanal in _buffer(sorgu, anahtar).get('channels') or []:
            if kanal.get('service') == servis and not kanal.get('isDisconnected'):
                return kanal['id']
    raise YayinHatasi(f'Buffer hesabında bağlı {servis} kanalı yok')


def buffer_tiktok(metin, anahtar, video_url, bekle=40):
    """Videoyu Buffer üzerinden TikTok'ta hemen yayınlar: açıklama ve kapak karesi dahil.

    TikTok kendi incelemesinden geçmemiş uygulamalara herkese açık paylaşım izni vermiyor; Buffer onaylı bir
    aracı olduğu için ücretsiz planıyla (API dahil) bu sınır aşılır. Buffer videoyu herkese açık adresten çeker."""
    kanal = buffer_kanal(anahtar)
    sorgu = ('mutation { createPost(input: { text: %s channelId: %s schedulingType: automatic mode: shareNow '
             'assets: [{ video: { url: %s metadata: { thumbnailOffset: %d } } }] }) '
             '{ ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }'
             % (json.dumps(metin['aciklama'][:2200], ensure_ascii=False), json.dumps(kanal), json.dumps(video_url), BUFFER_KAPAK_MS))
    yanit = _buffer(sorgu, anahtar).get('createPost') or {}
    gonderi = yanit.get('post') or {}
    if not gonderi.get('id'):
        raise YayinHatasi(f"Buffer gönderiyi kabul etmedi: {str(yanit.get('message'))[:200]}")
    durum = gonderi.get('status')
    if bekle:   # istek kotası dar (30 günde 1000): yalnız bir kez sorulur
        time.sleep(bekle)
        son = (_buffer('query { post(input: { id: %s }) { status error { message } } }' % json.dumps(gonderi['id']), anahtar).get('post')) or {}
        durum = son.get('status') or durum
        if (son.get('error') or {}).get('message'):
            raise YayinHatasi(f"Buffer TikTok'ta yayınlayamadı: {son['error']['message'][:200]}")
    return {'id': gonderi['id'], 'gorunurluk': 'buffer', 'durum': durum}


# ---------------------------------------------------------------- Facebook (doğrudan Meta Graph API)
FB_SURUM = 'v27.0'


def _facebook_istek(url, **kw):
    try:
        return _istek(url, **kw)
    except YayinHatasi:
        # Meta hata gövdesinde anahtar veya başka hassas değerler bulunabilir.
        raise YayinHatasi('Facebook API isteği reddedildi; sayfa anahtarını ve yayın izinlerini kontrol edin.') from None


def facebook(video, metin):
    ortam = _env('FB_SAYFA_ID', 'FB_ERISIM_ANAHTARI')
    if not ortam:
        return None
    sayfa, anahtar = ortam
    if not sayfa.isdigit():
        raise YayinHatasi('FB_SAYFA_ID sayısal olmalı')
    taban = f'https://graph.facebook.com/{FB_SURUM}'
    basliklar = {'Authorization': f'Bearer {anahtar}'}
    # Sayfa anahtarının kimliği her yayından önce doğrulanır.
    kimlik = _facebook_istek(f'{taban}/me?fields=id', basliklar=basliklar)
    if str(kimlik.get('id')) != sayfa:
        raise YayinHatasi('Facebook anahtarı seçilen sayfaya ait değil; yayın durduruldu')
    baslat = _facebook_istek(f'{taban}/{sayfa}/video_reels', veri={'upload_phase': 'start'}, basliklar=basliklar)
    video_id, yukle = baslat.get('video_id'), baslat.get('upload_url')
    if not video_id or not yukle:
        raise YayinHatasi('Facebook video oturumu oluşturulamadı')
    adres = urllib.parse.urlsplit(yukle)
    if adres.scheme != 'https' or adres.netloc != 'rupload.facebook.com':
        raise YayinHatasi('Facebook beklenmeyen yükleme adresi döndürdü')
    yukleme_basliklari = {'Authorization': f'OAuth {anahtar}'}
    video_url = os.environ.get('VIDEO_URL', '').strip()
    if video_url:
        yukleme_basliklari['file_url'] = video_url
        yuklendi = _facebook_istek(yukle, yontem='POST', basliklar=yukleme_basliklari, zaman_asimi=600)
    else:
        veri = Path(video).read_bytes()
        yukleme_basliklari.update({'offset': '0', 'file_size': str(len(veri)), 'Content-Type': 'application/octet-stream'})
        yuklendi = _facebook_istek(yukle, veri=veri, basliklar=yukleme_basliklari, zaman_asimi=600)
    if not yuklendi.get('success'):
        raise YayinHatasi('Facebook video yüklemesini onaylamadı')
    yayin = _facebook_istek(f'{taban}/{sayfa}/video_reels', veri={
        'upload_phase': 'finish', 'video_id': video_id, 'video_state': 'PUBLISHED',
        'description': metin['aciklama'], 'title': metin.get('baslik', '')[:255]}, basliklar=basliklar)
    if not yayin.get('success'):
        raise YayinHatasi('Facebook yayın isteğini onaylamadı')
    # Kabulü yayın tamamlandı diye göstermeyiz; bekleyen video otomatik tekrar yüklenmez.
    durum = _facebook_istek(f'{taban}/{video_id}?fields=status', basliklar=basliklar).get('status') or {}
    if durum.get('video_status') == 'error':
        raise YayinHatasi(f'Facebook videoyu işleyemedi (video: {video_id})')
    tamam = (durum.get('publishing_phase') or {}).get('status') == 'complete'
    return {'id': str(video_id), 'durum': 'published' if tamam else 'processing',
            'baglanti': f'https://www.facebook.com/reel/{video_id}'}


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
    buffer_anahtari, video_url = os.environ.get('BUFFER_API_ANAHTARI', '').strip(), os.environ.get('VIDEO_URL', '').strip()
    if buffer_anahtari and video_url and ortam is None:
        try:
            return buffer_tiktok(metin, buffer_anahtari, video_url)
        except Exception as hata:   # Buffer aksarsa video yine de taslak olarak telefona düşsün
            print(f'::warning::Buffer ile TikTok yayını olmadı, taslak yöntemine dönülüyor: {str(hata)[:200]}')
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


def tiktok_durum(publish_id, ortam=None, bekle=90):
    """TikTok'un yüklemeyi nasıl işlediği (PROCESSING_UPLOAD / SEND_TO_USER_INBOX / FAILED + neden); en çok `bekle` sn bekler."""
    import time
    kimlik = ortam or _env('TT_ISTEMCI_ANAHTARI', 'TT_ISTEMCI_SIRRI', 'TT_YENILEME_ANAHTARI')
    erisim = _tiktok_erisim(*kimlik)
    son = {}
    for _ in range(max(1, bekle // 6)):
        son = (_istek('https://open.tiktokapis.com/v2/post/publish/status/fetch/', json_veri={'publish_id': publish_id},
                      basliklar={'Authorization': f'Bearer {erisim}'}).get('data') or {})
        if son.get('status') in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE', 'FAILED'):
            break
        time.sleep(6)
    return son


PLATFORMLAR = (('instagram', instagram), ('youtube', youtube), ('tiktok', tiktok), ('facebook', facebook))


def yayinla(klasor):
    klasor = Path(klasor)
    metin = json.loads((klasor / 'paylasim.json').read_text(encoding='utf-8'))
    video = klasor / 'reel.mp4'
    sonuclar, hatali = {}, False
    kapali = {p.strip().lower() for p in os.environ.get('SOSYAL_KAPALI', '').split(',') if p.strip()}
    for ad, islev in PLATFORMLAR:
        if ad in kapali:  # depo değişkeni SOSYAL_KAPALI=youtube,tiktok: anahtar olsa da atlanır
            print(f'{ad}: kapalı, atlandı.')
            continue
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
    if '--tiktok-dene' in sys.argv:   # yalnız TikTok'a yükler ve TikTok'un cevabını yazar (tiktok-dene.yml)
        k = Path(sys.argv[sys.argv.index('--tiktok-dene') + 1])
        yanit = tiktok(k / 'reel.mp4', json.loads((k / 'paylasim.json').read_text(encoding='utf-8')))
        print('TikTok yükleme isteği:', yanit)
        if yanit.get('gorunurluk') == 'buffer':
            sys.exit(0)
        durum = tiktok_durum(yanit['id'])
        print('TikTok durumu:', json.dumps(durum, ensure_ascii=False))
        sys.exit(0 if durum.get('status') in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE') else 1)
    if '--youtube-kontrol' in sys.argv:
        sys.exit(0 if youtube_kontrol() else 1)
    if '--instagram-yenile' in sys.argv:
        try:
            instagram_yenile()
        except Exception as hata:
            print(f'Uyarı: Instagram anahtarı yenilenemedi: {hata}')
    sonuclar, hata_var = yayinla(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'sosyal-cikti')
    # 20 Ekim 2026: bir platform (ör. süresi dolmuş YouTube anahtarı) hata verse de diğerlerinde paylaşıldıysa iş kırmızı
    # olmaz, uyarı verir; hiçbirinde paylaşılamadıysa iş başarısız sayılır.
    for ad, sonuc in sonuclar.items():
        if 'hata' in sonuc:
            print(f"::warning::{ad} paylaşımı başarısız: {sonuc['hata'][:200]}")
    sys.exit(1 if hata_var and all('hata' in s for s in sonuclar.values()) else 0)
