"""Veri kaynakları. Hepsi ücretsiz ve resmî/herkese açık uçlar:

  gecmis    GitHub'daki sosyal/gecmis.json (botun yaptığı her Reels paylaşımı + Instagram ölçümleri) ve git geçmişi
  bulut     "Sosyal panel verisi" iş akışının eseri: Instagram Graph insights, YouTube Data API, Buffer bağlantıları
  youtube   kanalın herkese açık RSS akışı (son 15 video, izlenme) + varsa yerel YouTube Data API anahtarı
  telegram  t.me/s/<kanal> herkese açık önizleme (mesaj başına izlenme)

Her kaynak kendi durumunu (hazir / bekliyor / hata) depoya yazar; biri düşerse diğerleri çalışmaya devam eder."""
import html
import io
import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone

from .db import utc
from .siniflandir import KartTasarimi, baslik, gecmis_sablonu, metin_sablonu

DEPO = 'enesfeched-maker/kamu-ilan-takip'
GECMIS_YOLU = 'sosyal/gecmis.json'
TELEGRAM_KANAL = 'kpsstercihi'
YT_KANAL_ID = 'UC12bTJbwtlZFNWqcfjQ8OLw'
IG_PROFIL = 'https://www.instagram.com/kpsstercihii/'
TT_PROFIL = 'https://www.tiktok.com/@kpsstercihi'
SITE_ILANLAR = 'https://kpsstercihi.com/ilanlar.json'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KPSSTercihiSosyalPanel/1.0'


class KaynakHatasi(Exception):
    pass


# ---------------------------------------------------------------- ağ
def getir(url, basliklar=None, zaman_asimi=40, veri=None, yontem=None):
    b = {'User-Agent': UA, 'Accept-Language': 'tr-TR,tr;q=0.9'}
    b.update(basliklar or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=b, data=veri, method=yontem), timeout=zaman_asimi) as r:
            return r.read()
    except urllib.error.HTTPError as h:
        raise KaynakHatasi(f'HTTP {h.code} ({urllib.parse.urlsplit(url).netloc})') from None
    except (urllib.error.URLError, TimeoutError, OSError) as h:
        raise KaynakHatasi(f'Bağlantı kurulamadı ({urllib.parse.urlsplit(url).netloc}): {getattr(h, "reason", h)}') from None


def getir_json(url, **kw):
    return json.loads(getir(url, **kw).decode('utf-8'))


def github_anahtari():
    """GitHub CLI'nin girişli anahtarı (gh auth token). Anahtar yazdırılmaz, diske yazılmaz."""
    try:
        r = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, timeout=20,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.SubprocessError):
        return None
    t = r.stdout.strip()
    return t if r.returncode == 0 and t else None


def _gh(anahtar):
    b = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if anahtar:
        b['Authorization'] = f'Bearer {anahtar}'
    return b


# ---------------------------------------------------------------- gecmis.json (bot paylaşımları)
def gecmis_isle(depo, gecmis, olcum_kaynagi='gecmis'):
    """Geçmiş kayıtlarından Instagram/TikTok/Facebook paylaşımlarını yazar. Döner: kayıt sayısı."""
    adet = 0
    for g in gecmis:
        zaman = g.get('zaman')
        if not zaman:
            continue
        ortak = dict(yayin=zaman, tur=g.get('tur'), vakit=g.get('vakit'), sablon=gecmis_sablonu(g), palet=g.get('palet'),
                     muzik=g.get('muzik'), icerik=utc(zaman), bicim='Reels')
        ad = f"{ortak['sablon']} · {len(g.get('ilanlar') or [])} ilan"
        if g.get('ig_id'):
            gid = depo.gonderi_yaz('instagram', g['ig_id'], baslik=ad, **ortak)
            depo.db.execute("UPDATE gonderi SET url=? WHERE id=? AND url IS NULL", (IG_PROFIL, gid))
            ig = g.get('ig') or {}
            if ig:
                depo.olcum_yaz(gid, ig, zaman=ig.get('olcum'), kaynak=olcum_kaynagi)
            adet += 1
        tt = g.get('tt_id') or ''
        if tt and not tt.startswith('v_inbox'):   # gelen kutusu kimlikleri taslaktı; Buffer kimlikleri yayında
            gid = depo.gonderi_yaz('tiktok', tt, baslik=ad, **ortak)
            depo.db.execute("UPDATE gonderi SET url=? WHERE id=? AND url IS NULL", (TT_PROFIL, gid))
            adet += 1
        if g.get('fb_id'):
            depo.gonderi_yaz('facebook', g['fb_id'], baslik=ad, url=f"https://www.facebook.com/reel/{g['fb_id']}", **ortak)
            adet += 1
    depo.kaydet()
    return adet


def gecmis_topla(depo, anahtar=None, gecmis_derin=True):
    gecmis = getir_json(f'https://raw.githubusercontent.com/{DEPO}/main/{GECMIS_YOLU}')
    adet = gecmis_isle(depo, gecmis)
    # Bir kez: git geçmişindeki eski sürümlerden Instagram ölçümlerinin zaman serisi çıkarılır.
    if gecmis_derin and not depo.ayar('gecmis_geri_yuklendi'):
        sha_listesi, sayfa = [], 1
        while sayfa <= 5:
            parca = getir_json(f'https://api.github.com/repos/{DEPO}/commits?path={GECMIS_YOLU}&per_page=100&page={sayfa}',
                               basliklar=_gh(anahtar))
            sha_listesi += [c['sha'] for c in parca]
            if len(parca) < 100:
                break
            sayfa += 1
        for sha in reversed(sha_listesi):
            try:
                gecmis_isle(depo, getir_json(f'https://raw.githubusercontent.com/{DEPO}/{sha}/{GECMIS_YOLU}'), 'gecmis-git')
            except (KaynakHatasi, ValueError):
                continue
        gecmis_isle(depo, gecmis)
        depo.ayar_yaz('gecmis_geri_yuklendi', len(sha_listesi))
    return adet


# ---------------------------------------------------------------- bulut eseri (Instagram insights, YouTube API, Buffer)
IG_OLCUT = {'views': 'views', 'reach': 'reach', 'likes': 'likes', 'comments': 'comments', 'saved': 'saved',
            'shares': 'shares', 'total_interactions': 'interactions', 'ig_reels_avg_watch_time': 'avg_watch_ms',
            'ig_reels_video_view_total_time': 'total_watch_ms'}


class _YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


def bulut_indir(anahtar):
    """En yeni 'sosyal-panel-veri' eserini indirir. Döner: (veri, eser_zamani)."""
    if not anahtar:
        raise KaynakHatasi('GitHub girişi yok (gh auth login)')
    liste = getir_json(f'https://api.github.com/repos/{DEPO}/actions/artifacts?name=sosyal-panel-veri&per_page=1',
                       basliklar=_gh(anahtar))
    eserler = [e for e in liste.get('artifacts') or [] if not e.get('expired')]
    if not eserler:
        raise KaynakHatasi('Henüz eser yok: "Sosyal panel verisi" iş akışı çalışmamış')
    eser = eserler[0]
    # İndirme adresi depolama alanına yönlendirir; yetki başlığı oraya taşınmamalı.
    acici = urllib.request.build_opener(_YonlendirmeYok)
    try:
        acici.open(urllib.request.Request(eser['archive_download_url'], headers={**_gh(anahtar), 'User-Agent': UA}), timeout=40)
        raise KaynakHatasi('Eser indirme adresi alınamadı')
    except urllib.error.HTTPError as h:
        yer = h.headers.get('Location')
        if h.code not in (301, 302, 303, 307, 308) or not yer:
            raise KaynakHatasi(f'Eser indirilemedi: HTTP {h.code}') from None
    with zipfile.ZipFile(io.BytesIO(getir(yer, zaman_asimi=90))) as z:
        veri = json.loads(z.read('panel-veri.json').decode('utf-8'))
    return veri, eser.get('created_at')


def bulut_isle(depo, veri):
    """Döner: {'instagram': (durum, açıklama, adet), 'youtube_api': ..., 'buffer': ...}"""
    sonuc = {}
    zaman = veri.get('zaman')
    ig = veri.get('instagram') or {}
    adet = 0
    for m in ig.get('medyalar') or []:
        var = depo.db.execute('SELECT sablon FROM gonderi WHERE id=?', (f"instagram:{m['id']}",)).fetchone()
        alan = dict(url=m.get('permalink'), metin=m.get('caption'), baslik=baslik(m.get('caption')) or None,
                    yayin=m.get('timestamp'), kapak=m.get('thumbnail_url'),
                    bicim='Reels' if m.get('media_product_type') == 'REELS' else {'IMAGE': 'Görsel', 'CAROUSEL_ALBUM': 'Kaydırmalı', 'VIDEO': 'Video'}.get(m.get('media_type')))
        if not (var and var['sablon']):
            alan['sablon'] = metin_sablonu(m.get('caption'))
        gid = depo.gonderi_yaz('instagram', m['id'], **alan)
        ins = {IG_OLCUT[k]: v for k, v in (m.get('insights') or {}).items() if k in IG_OLCUT and isinstance(v, (int, float))}
        if 'likes' not in ins and m.get('like_count') is not None:
            ins['likes'] = m['like_count']
        if 'comments' not in ins and m.get('comments_count') is not None:
            ins['comments'] = m['comments_count']
        depo.olcum_yaz(gid, ins, zaman=zaman, kaynak='instagram-api')
        adet += 1
    sonuc['instagram'] = (ig.get('durum', 'hata'), ig.get('aciklama', ''), adet)

    yt = veri.get('youtube') or {}
    adet = 0
    for v in yt.get('videolar') or []:
        gid = youtube_yaz(depo, v['id'], v.get('baslik'), v.get('yayin'), metin=v.get('aciklama'))
        depo.olcum_yaz(gid, {'views': _sayi(v.get('views')), 'likes': _sayi(v.get('likes')),
                             'comments': _sayi(v.get('comments'))}, zaman=zaman, kaynak='youtube-api')
        adet += 1
    sonuc['youtube_api'] = (yt.get('durum', 'hata'), yt.get('aciklama', ''), adet)

    bf = veri.get('buffer') or {}
    adet = 0
    for g in bf.get('gonderiler') or []:
        link = g.get('externalLink')
        if not link:
            continue
        servis = (g.get('channelService') or '').lower()
        if servis == 'tiktok':
            depo.gonderi_yaz('tiktok', g['id'], url=link, metin=g.get('text'), baslik=baslik(g.get('text')) or None,
                             yayin=g.get('sentAt') or g.get('dueAt'))
            adet += 1
    sonuc['buffer'] = (bf.get('durum', 'hata'), bf.get('aciklama', ''), adet)
    depo.kaydet()
    return sonuc


def _sayi(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- YouTube
_YT = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015',
       'media': 'http://search.yahoo.com/mrss/'}


def youtube_rss_ayristir(xml_metni):
    kok = ET.fromstring(xml_metni)
    videolar = []
    for e in kok.findall('a:entry', _YT):
        vid = e.findtext('yt:videoId', namespaces=_YT)
        grup = e.find('media:group', _YT)
        ist = grup.find('media:community/media:statistics', _YT) if grup is not None else None
        link = e.find('a:link', _YT)
        kapak = grup.find('media:thumbnail', _YT) if grup is not None else None
        videolar.append({
            'id': vid, 'baslik': e.findtext('a:title', namespaces=_YT), 'yayin': e.findtext('a:published', namespaces=_YT),
            'url': link.get('href') if link is not None else f'https://www.youtube.com/watch?v={vid}',
            'aciklama': grup.findtext('media:description', namespaces=_YT) if grup is not None else None,
            'kapak': kapak.get('url') if kapak is not None else None,
            'views': _sayi(ist.get('views')) if ist is not None else None,
        })
    return videolar


def youtube_yaz(depo, vid, baslik_, yayin, url=None, metin=None, kapak=None):
    """YouTube videosunu yazar; bot paylaşımıyla (aynı içerik IG'de) zaman eşleşmesi varsa şablonu devralır."""
    alan = dict(baslik=baslik_, yayin=yayin, url=url or f'https://www.youtube.com/shorts/{vid}', metin=metin, kapak=kapak,
                bicim='Shorts')
    var = depo.db.execute('SELECT sablon FROM gonderi WHERE id=?', (f'youtube:{vid}',)).fetchone()
    if not (var and var['sablon']):
        es = _gecmis_eslesmesi(depo, yayin)
        if es:
            alan.update(sablon=es['sablon'], tur=es['tur'], vakit=es['vakit'], palet=es['palet'], muzik=es['muzik'],
                        icerik=es['icerik'])
        else:
            alan['sablon'] = metin_sablonu(metin or baslik_)
    return depo.gonderi_yaz('youtube', vid, **alan)


def _gecmis_eslesmesi(depo, yayin):
    """Videonun yayın anından en çok 90 dk önce üretilmiş bot paylaşımı (aynı video, IG kaydı)."""
    z = utc(yayin)
    if not z:
        return None
    alt = (datetime.fromisoformat(z) - timedelta(minutes=90)).isoformat(timespec='seconds')
    return depo.db.execute(
        "SELECT sablon, tur, vakit, palet, muzik, icerik FROM gonderi WHERE platform='instagram' AND icerik IS NOT NULL "
        "AND icerik BETWEEN ? AND ? ORDER BY icerik DESC LIMIT 1", (alt, z)).fetchone()


def youtube_topla(depo, api_anahtari=None):
    zaman = datetime.now(timezone.utc).isoformat(timespec='seconds')
    videolar = youtube_rss_ayristir(getir(f'https://www.youtube.com/feeds/videos.xml?channel_id={YT_KANAL_ID}'))
    for v in videolar:
        gid = youtube_yaz(depo, v['id'], v['baslik'], v['yayin'], v['url'], v['aciklama'], v['kapak'])
        depo.olcum_yaz(gid, {'views': v['views']}, zaman=zaman, kaynak='youtube-rss')
    adet = len(videolar)
    if api_anahtari:   # isteğe bağlı: tüm videolar + beğeni/yorum (YouTube Data API, ücretsiz kota)
        kimlikler = [r['yerel_id'] for r in depo.db.execute("SELECT yerel_id FROM gonderi WHERE platform='youtube'")]
        for i in range(0, len(kimlikler), 50):
            y = getir_json('https://www.googleapis.com/youtube/v3/videos?part=statistics&id='
                           + ','.join(kimlikler[i:i + 50]) + '&key=' + urllib.parse.quote(api_anahtari))
            for it in y.get('items') or []:
                st = it.get('statistics') or {}
                depo.olcum_yaz(f"youtube:{it['id']}", {'views': _sayi(st.get('viewCount')), 'likes': _sayi(st.get('likeCount')),
                                                       'comments': _sayi(st.get('commentCount'))}, zaman=zaman, kaynak='youtube-api')
    depo.kaydet()
    return adet


# ---------------------------------------------------------------- Telegram
def telegram_sayi(metin):
    """'1.2K' -> 1200, '15' -> 15, '3,4M' -> 3400000."""
    m = re.match(r'\s*([\d.,]+)\s*([KkMm]?)', metin or '')
    if not m:
        return None
    sayi, kat = m.group(1).replace(',', '.'), m.group(2).upper()
    try:
        deger = float(sayi) if kat else float(sayi.replace('.', ''))
    except ValueError:
        return None
    return int(round(deger * {'K': 1000, 'M': 1_000_000}.get(kat, 1)))


def telegram_ayristir(sayfa):
    mesajlar = []
    for blok in sayfa.split('tgme_widget_message_wrap')[1:]:
        post = re.search(r'data-post="([^"/]+)/(\d+)"', blok)
        if not post:
            continue
        no = int(post.group(2))
        metin_m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', blok, re.S)
        metin = ''
        if metin_m:
            metin = re.sub(r'<br\s*/?>', '\n', metin_m.group(1))
            metin = html.unescape(re.sub(r'<[^>]+>', '', metin)).strip()
        gorunum = re.search(r'tgme_widget_message_views">([^<]+)<', blok)
        zaman = re.search(r'<time[^>]+datetime="([^"]+)"', blok)
        kapak = re.search(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", blok)
        tepki = sum(telegram_sayi(t) or 0 for t in re.findall(r'class="tgme_reaction"[^>]*>.*?</i>\s*([\d.,KkMm]+)', blok, re.S))
        if 'video_player' in blok:
            bicim = 'Video'
        elif 'photo_wrap' in blok:
            bicim = 'Görsel'
        elif 'tgme_widget_message_document' in blok:
            bicim = 'Belge'
        elif 'tgme_widget_message_poll' in blok:
            bicim = 'Anket'
        else:
            bicim = 'Metin'
        mesajlar.append({'no': no, 'url': f'https://t.me/{post.group(1)}/{no}', 'metin': metin,
                         'views': telegram_sayi(gorunum.group(1)) if gorunum else None,
                         'reactions': tepki if 'tgme_reaction' in blok else None,
                         'yayin': zaman.group(1) if zaman else None, 'kapak': kapak.group(1) if kapak else None,
                         'bicim': bicim, 'yanit': 'tgme_widget_message_reply' in blok})
    return mesajlar


def telegram_topla(depo, kanal=TELEGRAM_KANAL, kart=None, en_eski_gun=None, en_cok_sayfa=60):
    """Önizlemeyi yeniden eskiye sayfalar. İlk çalışmada tamamı; sonra son `en_eski_gun` gün (izlenmeler oturur)."""
    if en_eski_gun is None:
        en_eski_gun = 45 if depo.ayar('telegram_tam_tarandi') else None
    sinir = datetime.now(timezone.utc) - timedelta(days=en_eski_gun) if en_eski_gun else None
    zaman = datetime.now(timezone.utc).isoformat(timespec='seconds')
    adet, onceki, sayfa_no = 0, None, 0
    while sayfa_no < en_cok_sayfa:
        url = f'https://t.me/s/{kanal}' + (f'?before={onceki}' if onceki else '')
        mesajlar = telegram_ayristir(getir(url).decode('utf-8', 'replace'))
        if not mesajlar:
            break
        for m in mesajlar:
            sablon = metin_sablonu(m['metin'])
            if m['yanit'] and sablon == 'Diğer':
                sablon = 'Yanıt'
            tasarim = kart.tasarim(m['no']) if (kart and sablon == 'İlan kartı') else None
            gid = depo.gonderi_yaz('telegram', m['no'], url=m['url'], metin=m['metin'], baslik=baslik(m['metin']) or f"Mesaj {m['no']}",
                                   yayin=m['yayin'], kapak=m['kapak'], sablon=sablon,
                                   bicim=tasarim or m['bicim'])
            depo.olcum_yaz(gid, {'views': m['views'], 'reactions': m['reactions']}, zaman=zaman, kaynak='telegram-onizleme')
            adet += 1
        en_kucuk = min(m['no'] for m in mesajlar)
        en_eski = min((utc(m['yayin']) for m in mesajlar if m['yayin']), default=None)
        if en_kucuk <= 1 or en_kucuk == onceki or (sinir and en_eski and en_eski < sinir.isoformat()):
            break
        onceki, sayfa_no = en_kucuk, sayfa_no + 1
    if not en_eski_gun:
        depo.ayar_yaz('telegram_tam_tarandi', True)
    depo.kaydet()
    return adet


def site_ilanlari():
    try:
        return getir_json(SITE_ILANLAR, zaman_asimi=60)
    except (KaynakHatasi, ValueError):
        return None


def bulut_tetikle(anahtar):
    """'Sosyal panel verisi' iş akışını hemen çalıştırır (workflow_dispatch)."""
    if not anahtar:
        raise KaynakHatasi('GitHub girişi yok')
    getir(f'https://api.github.com/repos/{DEPO}/actions/workflows/sosyal-panel.yml/dispatches', yontem='POST',
          veri=json.dumps({'ref': 'main'}).encode(), basliklar={**_gh(anahtar), 'Content-Type': 'application/json'})
    return True
