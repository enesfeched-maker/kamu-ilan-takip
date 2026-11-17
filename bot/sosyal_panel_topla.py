"""Sosyal panel (yerel analiz uygulaması) için bulutta ölçüm toplar.

Platform anahtarları yalnız GitHub sırlarında durduğu için Instagram (ve varsa YouTube/Buffer) verisini burada
okuruz; sonuç `panel-veri.json` olarak iş eserine (artifact) yazılır, depoya commit edilmez. Yerel uygulama
(sosyal-panel/) bu eseri GitHub girişiyle indirir. Anahtarlar hiçbir zaman yazdırılmaz.

  Instagram: IG_KULLANICI_ID, IG_ERISIM_ANAHTARI  -> tüm medya + kalıcı bağlantı + insights (izlenme süresi dahil)
  YouTube:   YT_ISTEMCI_KIMLIGI, YT_ISTEMCI_SIRRI, YT_YENILEME_ANAHTARI -> videolar + istatistikler (youtube.readonly gerekir)
  Facebook:  FB_SAYFA_ID, FB_ERISIM_ANAHTARI -> Sayfa Reels listesi + video_insights (lifetime)
  Buffer:    BUFFER_API_ANAHTARI -> gönderilen paylaşımların platform bağlantıları ve metrics (TikTok/YouTube)

Kullanım: python bot/sosyal_panel_topla.py panel-veri.json"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

from sosyal_yayinla import FB_SURUM, IG_SURUM, YayinHatasi, _buffer, _env, _istek

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


# ---------------------------------------------------------------- Facebook (Sayfa Reels + video_insights)
FB_SAYFA_ALANLARI = 'id,description,created_time,permalink_url,picture'
FB_EN_COK = 100
# Reels ölçütleri yalnız `lifetime` döneminde var (Meta: Graph API > Video > video_insights, Reels tablosu).
FB_OLCUTLER = ('fb_reels_total_plays', 'blue_reels_play_count', 'fb_reels_replay_count', 'post_impressions_unique',
               'post_video_avg_time_watched', 'post_video_view_time', 'post_video_likes_by_reaction_type',
               'post_video_social_actions')


def _fb_istek(istek):
    """Meta hata gövdesi okunur kalır (desteklenmeyen ölçüt teşhisi için); anahtar zaten üstbilgidedir."""
    def sar(url, **kw):
        try:
            return istek(url, **kw)
        except YayinHatasi as hata:
            raise YayinHatasi(_hata(hata)) from None
    return sar


def _sayi_mi(d):
    return isinstance(d, (int, float)) and not isinstance(d, bool)


def _fb_deger(deger):
    """Ölçüt değeri sayı ya da {anahtar: sayı} sözlüğü olabilir."""
    if _sayi_mi(deger):
        return deger
    if isinstance(deger, dict):
        return {str(k): v for k, v in deger.items() if _sayi_mi(v)}
    return None


def fb_insights_ayristir(yanit):
    """`/{video}/video_insights` yanıtı -> panel ölçütleri (views, reach, likes, comments, shares, avg_watch_ms, total_watch_ms)."""
    ham = {}
    for m in (yanit or {}).get('data') or []:
        degerler = m.get('values') or []
        d = _fb_deger((degerler[0] if degerler else {}).get('value'))
        if m.get('name') and d is not None:
            ham[m['name']] = d
    sonuc = {}
    izlenme = ham.get('fb_reels_total_plays')
    if not _sayi_mi(izlenme):
        izlenme = ham.get('blue_reels_play_count')
    if _sayi_mi(izlenme):
        sonuc['views'] = izlenme
    for olcut, ad in (('post_impressions_unique', 'reach'), ('post_video_avg_time_watched', 'avg_watch_ms'),
                      ('post_video_view_time', 'total_watch_ms')):
        if _sayi_mi(ham.get(olcut)):
            sonuc[ad] = ham[olcut]
    if isinstance(ham.get('post_video_likes_by_reaction_type'), dict):
        sonuc['likes'] = sum(ham['post_video_likes_by_reaction_type'].values())
    sosyal = ham.get('post_video_social_actions')
    if isinstance(sosyal, dict):
        for anahtar, ad in (('COMMENT', 'comments'), ('SHARE', 'shares')):
            if anahtar in sosyal:
                sonuc[ad] = sosyal[anahtar]
    return sonuc


def fb_video_insights(video_id, taban, basliklar, istek):
    """Önce tüm ölçütler tek istekte; reddedilirse ölçüt ölçüt denenir (desteklenmeyen atlanır). (ölçüt, atlanan) döner."""
    adres = f'{taban}/{video_id}/video_insights?period=lifetime&metric='
    try:
        return fb_insights_ayristir(istek(adres + ','.join(FB_OLCUTLER), basliklar=basliklar)), []
    except YayinHatasi:
        pass
    parcalar, atlanan, son_hata = [], [], None
    for olcut in FB_OLCUTLER:
        try:
            parcalar += istek(adres + olcut, basliklar=basliklar).get('data') or []
        except YayinHatasi as hata:
            atlanan.append(olcut)
            son_hata = hata
    if len(atlanan) == len(FB_OLCUTLER):
        raise son_hata
    return fb_insights_ayristir({'data': parcalar}), atlanan


def facebook(ortam=None, istek=_istek):
    ortam = ortam or _env('FB_SAYFA_ID', 'FB_ERISIM_ANAHTARI')
    if not ortam:
        return {'durum': 'bekliyor', 'aciklama': 'FB_SAYFA_ID / FB_ERISIM_ANAHTARI yok'}
    sayfa, anahtar = ortam
    istek = _fb_istek(istek)
    taban = f'https://graph.facebook.com/{FB_SURUM}'
    basliklar = {'Authorization': f'Bearer {anahtar}'}
    try:
        url = f'{taban}/{sayfa}/video_reels?fields={FB_SAYFA_ALANLARI}&limit=25'
        reeller = []
        while url and len(reeller) < FB_EN_COK:
            yanit = istek(url, basliklar=basliklar)
            reeller.extend(yanit.get('data') or [])
            url = (yanit.get('paging') or {}).get('next')
    except YayinHatasi as hata:
        return {'durum': 'hata', 'aciklama': f'Reels listesi alınamadı: {_hata(hata)}'}
    sonuc, hatalar, atlanan = [], 0, set()
    for r in reeller[:FB_EN_COK]:
        if not r.get('id'):
            continue
        kayit = {k: r.get(k) for k in ('id', 'description', 'created_time', 'permalink_url', 'picture')}
        try:
            kayit['insights'], eksik = fb_video_insights(r['id'], taban, basliklar, istek)
            atlanan.update(eksik)
        except YayinHatasi as hata:
            hatalar += 1
            kayit['insights_hata'] = _hata(hata)
        sonuc.append(kayit)
    aciklama = f'{len(sonuc)} reel'
    if hatalar:
        aciklama += f', {hatalar} reelde ölçüm okunamadı'
    if atlanan:
        aciklama += f'; desteklenmeyen ölçüt: {", ".join(sorted(atlanan))}'
    return {'durum': 'hazir', 'aciklama': aciklama, 'reels': sonuc}


# ---------------------------------------------------------------- Buffer
# `metrics`: Buffer API referansı (developers.buffer.com/reference.html) Post.metrics -> [PostMetric] {name, type, unit, value};
# yalnız gönderilmiş paylaşımda dolu, Buffer günde bir yeniler (metricsUpdatedAt). Şema tutmazsa metriksiz sorguya düşülür.
BUFFER_GONDERI_ALANLAR = 'id text status sentAt dueAt channelId channelService externalLink'
BUFFER_GONDERI_SORGU = ('query { posts(first: 100, input: { organizationId: %%s, filter: { status: [sent] } }) '
                        '{ edges { node { %s } } } }')
BUFFER_GONDERI = BUFFER_GONDERI_SORGU % (BUFFER_GONDERI_ALANLAR + ' metricsUpdatedAt metrics { name type unit value }')
BUFFER_GONDERI_DUZ = BUFFER_GONDERI_SORGU % BUFFER_GONDERI_ALANLAR


def buffer(anahtar=None, sorgu=None):
    anahtar = anahtar or (_env('BUFFER_API_ANAHTARI') or [None])[0]
    if not anahtar:
        return {'durum': 'bekliyor', 'aciklama': 'BUFFER_API_ANAHTARI sırrı yok'}
    sorgu = sorgu or (lambda q: _buffer(q, anahtar))
    metrik_hata = None
    try:
        kurumlar = ((sorgu('query { account { organizations { id } } }').get('account') or {}).get('organizations')) or []
        kanallar, gonderiler = [], []
        for kurum in kurumlar:
            kid = json.dumps(kurum['id'])
            kanallar += sorgu('query { channels(input: { organizationId: %s }) { id service name isDisconnected } }' % kid).get('channels') or []
            try:
                veri = sorgu(BUFFER_GONDERI % kid).get('posts') or {}
            except YayinHatasi as hata:   # metrics alanı şemada yoksa bağlantılar yine de gelsin
                metrik_hata = _hata(hata)
                veri = sorgu(BUFFER_GONDERI_DUZ % kid).get('posts') or {}
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
    aciklama = f'{len(gonderiler)} gönderi' + (f'; metrics okunamadı: {metrik_hata}' if metrik_hata else '')
    return {'durum': 'hazir', 'aciklama': aciklama, 'kanallar': kanallar, 'gonderiler': gonderiler}


def topla():
    # Buffer kotası (30 günde ~1000 istek) yayınla paylaşılıyor: panel için günde bir kez sorulur.
    bf = buffer() if os.environ.get('PANEL_BUFFER') == 'true' else {'durum': 'atlandi', 'aciklama': 'Bu çalışmada sorulmadı'}
    return {'surum': 1, 'zaman': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'instagram': instagram(), 'youtube': youtube(), 'facebook': facebook(), 'buffer': bf}


if __name__ == '__main__':
    veri = topla()
    hedef = sys.argv[1] if len(sys.argv) > 1 else 'panel-veri.json'
    with open(hedef, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False)
    for ad in ('instagram', 'youtube', 'facebook', 'buffer'):
        print(f"{ad}: {veri[ad]['durum']} — {veri[ad].get('aciklama', '')}")
        if veri[ad].get('sema'):
            print(f"{ad} şema: {json.dumps(veri[ad]['sema'])[:1500]}")
