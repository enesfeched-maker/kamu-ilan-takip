"""Sosyal panel (yerel analiz uygulaması) için bulutta ölçüm toplar.

Platform anahtarları yalnız GitHub sırlarında durduğu için Instagram (ve varsa YouTube/Buffer) verisini burada
okuruz; sonuç `panel-veri.json` olarak iş eserine (artifact) yazılır, depoya commit edilmez. Yerel uygulama
(sosyal-panel/) bu eseri GitHub girişiyle indirir. Anahtarlar hiçbir zaman yazdırılmaz.

  Instagram: IG_KULLANICI_ID, IG_ERISIM_ANAHTARI  -> tüm medya + kalıcı bağlantı + insights (izlenme süresi dahil)
  YouTube:   YT_ISTEMCI_KIMLIGI, YT_ISTEMCI_SIRRI, YT_YENILEME_ANAHTARI -> videolar + istatistikler (youtube.readonly gerekir)
  Buffer:    BUFFER_API_ANAHTARI -> gönderilen paylaşımların platform bağlantıları (TikTok/YouTube)

Kullanım: python bot/sosyal_panel_topla.py panel-veri.json"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

from sosyal_yayinla import IG_SURUM, YayinHatasi, _buffer, _env, _istek

IG_ALANLAR = 'id,caption,media_type,media_product_type,permalink,timestamp,thumbnail_url,media_url,like_count,comments_count'
# İlk deneme en zengin küme; desteklenmeyen ölçüt hatasında daha dar kümeye düşülür.
IG_OLCUT_KUMELERI = {
    'REELS': (('views', 'reach', 'likes', 'comments', 'saved', 'shares', 'total_interactions',
               'ig_reels_avg_watch_time', 'ig_reels_video_view_total_time'),
              ('views', 'reach', 'likes', 'comments', 'saved', 'shares'),
              ('reach', 'likes', 'comments', 'saved', 'shares')),
    'FEED': (('views', 'reach', 'likes', 'comments', 'saved', 'shares', 'total_interactions'),
             ('reach', 'likes', 'comments', 'saved', 'shares')),
}
IG_EN_COK = 300


def _hata(metin):
    """Hata metninden olası anahtar parçalarını ayıklar (access_token=...)."""
    metin = str(metin)[:300]
    return urllib.parse.unquote(metin).split('access_token=')[0]


# ---------------------------------------------------------------- Instagram
def ig_medyalar(ig_id, anahtar, istek=_istek, en_cok=IG_EN_COK):
    url = (f'https://graph.instagram.com/{IG_SURUM}/{ig_id}/media?fields={IG_ALANLAR}&limit=50'
           f'&access_token={urllib.parse.quote(anahtar)}')
    medyalar = []
    while url and len(medyalar) < en_cok:
        yanit = istek(url)
        medyalar.extend(yanit.get('data') or [])
        url = (yanit.get('paging') or {}).get('next')
    return medyalar[:en_cok]


def ig_olcut_tipi(medya):
    return 'REELS' if medya.get('media_product_type') == 'REELS' or medya.get('media_type') == 'VIDEO' else 'FEED'


def ig_insights(medya_id, tip, anahtar, istek=_istek):
    son_hata = None
    for olcutler in IG_OLCUT_KUMELERI[tip]:
        try:
            yanit = istek(f'https://graph.instagram.com/{IG_SURUM}/{medya_id}/insights?metric={",".join(olcutler)}'
                          f'&access_token={urllib.parse.quote(anahtar)}')
        except YayinHatasi as hata:
            son_hata = hata
            continue
        return {m['name']: (m.get('values') or [{}])[0].get('value', 0) for m in yanit.get('data') or [] if m.get('name')}
    raise son_hata


def instagram(ortam=None, istek=_istek):
    ig_id, anahtar = ortam or _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI') or (None, None)
    if not ig_id:
        return {'durum': 'bekliyor', 'aciklama': 'IG_KULLANICI_ID / IG_ERISIM_ANAHTARI sırrı yok'}
    try:
        medyalar = ig_medyalar(ig_id, anahtar, istek)
    except YayinHatasi as hata:
        return {'durum': 'hata', 'aciklama': f'Medya listesi alınamadı: {_hata(hata)}'}
    sonuc, hatalar = [], 0
    for m in medyalar:
        kayit = {k: m.get(k) for k in ('id', 'caption', 'media_type', 'media_product_type', 'permalink', 'timestamp',
                                       'thumbnail_url', 'like_count', 'comments_count')}
        if m.get('media_type') == 'IMAGE':
            kayit['thumbnail_url'] = m.get('media_url')
        try:
            kayit['insights'] = ig_insights(m['id'], ig_olcut_tipi(m), anahtar, istek)
        except YayinHatasi as hata:
            hatalar += 1
            kayit['insights_hata'] = _hata(hata)
        sonuc.append(kayit)
    aciklama = f'{len(sonuc)} medya' + (f', {hatalar} medyada ölçüm okunamadı' if hatalar else '')
    return {'durum': 'hazir', 'aciklama': aciklama, 'medyalar': sonuc}


# ---------------------------------------------------------------- YouTube
def youtube(ortam=None, istek=_istek):
    kimlik = ortam or _env('YT_ISTEMCI_KIMLIGI', 'YT_ISTEMCI_SIRRI', 'YT_YENILEME_ANAHTARI')
    if not kimlik:
        return {'durum': 'bekliyor', 'aciklama': 'YT_* sırları yok'}
    istemci, sir, yenileme = kimlik
    try:
        erisim = istek('https://oauth2.googleapis.com/token', veri={
            'client_id': istemci, 'client_secret': sir, 'refresh_token': yenileme, 'grant_type': 'refresh_token'})['access_token']
        b = {'Authorization': f'Bearer {erisim}'}
        kanal = (istek('https://www.googleapis.com/youtube/v3/channels?part=contentDetails&mine=true', basliklar=b).get('items') or [{}])[0]
        liste = ((kanal.get('contentDetails') or {}).get('relatedPlaylists') or {}).get('uploads')
        if not liste:
            return {'durum': 'hata', 'aciklama': 'Kanal yükleme listesi bulunamadı'}
        kimlikler, sayfa = [], ''
        while len(kimlikler) < 500:
            y = istek('https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50'
                      f'&playlistId={liste}' + (f'&pageToken={sayfa}' if sayfa else ''), basliklar=b)
            kimlikler += [i['contentDetails']['videoId'] for i in y.get('items') or []]
            sayfa = y.get('nextPageToken')
            if not sayfa:
                break
        videolar = []
        for i in range(0, len(kimlikler), 50):
            y = istek('https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id='
                      + ','.join(kimlikler[i:i + 50]), basliklar=b)
            for v in y.get('items') or []:
                sn, st = v.get('snippet') or {}, v.get('statistics') or {}
                videolar.append({'id': v['id'], 'baslik': sn.get('title'), 'aciklama': (sn.get('description') or '')[:600],
                                 'yayin': sn.get('publishedAt'), 'sure': (v.get('contentDetails') or {}).get('duration'),
                                 'views': st.get('viewCount'), 'likes': st.get('likeCount'), 'comments': st.get('commentCount')})
    except (YayinHatasi, KeyError) as hata:
        return {'durum': 'hata', 'aciklama': f'YouTube okunamadı (youtube.readonly izni gerekebilir): {_hata(hata)}'}
    return {'durum': 'hazir', 'aciklama': f'{len(videolar)} video', 'videolar': videolar}


# ---------------------------------------------------------------- Buffer
BUFFER_GONDERI = ('query { posts(first: 100, input: { organizationId: %s, filter: { status: [sent] } }) '
                  '{ edges { node { id text status sentAt dueAt channelId channelService externalLink } } } }')


def buffer(anahtar=None, sorgu=None):
    anahtar = anahtar or (_env('BUFFER_API_ANAHTARI') or [None])[0]
    if not anahtar:
        return {'durum': 'bekliyor', 'aciklama': 'BUFFER_API_ANAHTARI sırrı yok'}
    sorgu = sorgu or (lambda q: _buffer(q, anahtar))
    try:
        kurumlar = ((sorgu('query { account { organizations { id } } }').get('account') or {}).get('organizations')) or []
        kanallar, gonderiler = [], []
        for kurum in kurumlar:
            kid = json.dumps(kurum['id'])
            kanallar += sorgu('query { channels(input: { organizationId: %s }) { id service name isDisconnected } }' % kid).get('channels') or []
            veri = sorgu(BUFFER_GONDERI % kid).get('posts') or {}
            gonderiler += [e['node'] for e in veri.get('edges') or [] if e.get('node')]
    except (YayinHatasi, KeyError, TypeError) as hata:
        sonuc = {'durum': 'hata', 'aciklama': f'Buffer okunamadı: {_hata(hata)}'}
        try:   # şema değişmişse hangi alanların olduğunu kaydet (bir sonraki sürüm için)
            sonuc['sema'] = sorgu('query { __type(name: "Post") { fields { name } } }')
        except Exception:
            pass
        return sonuc
    for g in gonderiler:
        g['text'] = (g.get('text') or '')[:600]
    return {'durum': 'hazir', 'aciklama': f'{len(gonderiler)} gönderi', 'kanallar': kanallar, 'gonderiler': gonderiler}


def topla():
    # Buffer kotası (30 günde ~1000 istek) yayınla paylaşılıyor: panel için günde bir kez sorulur.
    bf = buffer() if os.environ.get('PANEL_BUFFER') == 'true' else {'durum': 'atlandi', 'aciklama': 'Bu çalışmada sorulmadı'}
    return {'surum': 1, 'zaman': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'instagram': instagram(), 'youtube': youtube(), 'buffer': bf}


if __name__ == '__main__':
    veri = topla()
    hedef = sys.argv[1] if len(sys.argv) > 1 else 'panel-veri.json'
    with open(hedef, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False)
    for ad in ('instagram', 'youtube', 'buffer'):
        print(f"{ad}: {veri[ad]['durum']} — {veri[ad].get('aciklama', '')}")
        if veri[ad].get('sema'):
            print(f"{ad} şema: {json.dumps(veri[ad]['sema'])[:1500]}")
