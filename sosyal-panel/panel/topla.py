"""Tüm kaynakları sırayla çalıştırır; her biri kendi durumunu yazar, biri düşerse diğerleri sürer."""
import threading
import traceback
from datetime import datetime, timedelta, timezone

from . import kaynaklar as k
from .siniflandir import KartTasarimi

PLATFORMLAR = ('instagram', 'youtube', 'tiktok', 'telegram', 'facebook', 'x')
_kilit = threading.Lock()


def _dene(depo, ad, islev, gunluk):
    try:
        sonuc = islev()
        gunluk.append(f'{ad}: tamam')
        return sonuc, None
    except k.KaynakHatasi as h:
        gunluk.append(f'{ad}: {h}')
        return None, str(h)
    except Exception as h:   # beklenmeyen ayrıştırma hataları da uygulamayı durdurmaz
        gunluk.append(f'{ad}: beklenmeyen hata {h!r}')
        traceback.print_exc()
        return None, f'Beklenmeyen hata: {h!r}'[:300]


def hepsini_topla(depo, bulut_tetikle=False, gh_anahtari=None):
    if not _kilit.acquire(blocking=False):
        return {'calisiyor': True}
    try:
        return _topla(depo, bulut_tetikle, gh_anahtari)
    finally:
        _kilit.release()


def _topla(depo, bulut_tetikle, gh_anahtari):
    gunluk = []
    depo.ayar_yaz('toplama', {'basladi': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'bitti': None})
    anahtar = gh_anahtari if gh_anahtari is not None else k.github_anahtari()

    # 1) Bot paylaşım geçmişi (şablon bilgisi + Instagram ölçüm geçmişi)
    adet, hata = _dene(depo, 'gecmis', lambda: k.gecmis_topla(depo, anahtar), gunluk)
    depo.durum_yaz('gecmis', 'hata' if hata else 'hazir', hata or f'{adet} platform kaydı (sosyal/gecmis.json)', adet)

    # 2) Bulut eseri: Instagram insights + YouTube API + Buffer
    bulut, hata = _dene(depo, 'bulut', lambda: k.bulut_indir(anahtar), gunluk)
    ig_durum = None
    if bulut:
        veri, eser_zamani = bulut
        sonuc = k.bulut_isle(depo, veri)
        yas = _yas_saat(eser_zamani)
        depo.durum_yaz('bulut', 'hazir', f'Son eser {yas:.0f} saat önce' if yas is not None else 'Eser okundu', 1)
        ig_durum = sonuc['instagram']
        d, a, n = sonuc['youtube_api']
        depo.durum_yaz('youtube_api', d, a, n)
        d, a, n = sonuc['buffer']
        if d != 'atlandi':
            depo.durum_yaz('buffer', d, a, n)
        if bulut_tetikle and (yas is None or yas > 2):
            _dene(depo, 'bulut-tetikle', lambda: k.bulut_tetikle(anahtar), gunluk)
    else:
        depo.durum_yaz('bulut', 'hata', hata)
        if bulut_tetikle and anahtar:
            _dene(depo, 'bulut-tetikle', lambda: k.bulut_tetikle(anahtar), gunluk)

    # 3) YouTube RSS (anahtarsız) + isteğe bağlı yerel API anahtarı
    yt_anahtari = (depo.ayar('anahtarlar', {}) or {}).get('youtube_api')
    adet, hata = _dene(depo, 'youtube', lambda: k.youtube_topla(depo, yt_anahtari), gunluk)
    yt_api = depo.db.execute("SELECT durum FROM kaynak_durum WHERE kaynak='youtube_api'").fetchone()
    ek = ' + Data API (beğeni, yorum)' if (yt_anahtari or (yt_api and yt_api['durum'] == 'hazir')) else '; beğeni/yorum için YouTube Data API anahtarı bekleniyor'
    depo.durum_yaz('youtube', 'hata' if hata else 'hazir', hata or f'Herkese açık RSS: son {adet} video izlenmesi{ek}', adet)

    # 4) Telegram önizleme (+ kart tasarımı için sitenin ilan verisi)
    kart = KartTasarimi(k.site_ilanlari())
    adet, hata = _dene(depo, 'telegram', lambda: k.telegram_topla(depo, kart=kart), gunluk)
    depo.durum_yaz('telegram', 'hata' if hata else 'hazir', hata or f't.me/s önizlemesi: {adet} mesaj tarandı', adet)

    # 5) Platform özetleri
    if ig_durum and ig_durum[0] == 'hazir':
        depo.durum_yaz('instagram', 'hazir', f'Graph API insights: {ig_durum[2]} medya (izlenme süresi dahil)', ig_durum[2])
    else:
        neden = (ig_durum[1] if ig_durum else depo.db.execute("SELECT aciklama FROM kaynak_durum WHERE kaynak='bulut'").fetchone()['aciklama'])
        depo.durum_yaz('instagram', 'kismi', f'Yalnız bot Reels ölçümleri (gecmis.json). Bulut verisi yok: {neden}')
    tt_link = depo.db.execute("SELECT COUNT(*) n FROM gonderi WHERE platform='tiktok' AND url NOT LIKE '%/@kpsstercihi'").fetchone()['n']
    depo.durum_yaz('tiktok', 'bekliyor', 'Ölçüm için TikTok Display API anahtarı (video.list izni) bekleniyor; paylaşımlar Buffer kayıtlarından listeleniyor'
                   + ('' if tt_link else ', bağlantılar Buffer verisi gelince açılır'))
    depo.durum_yaz('facebook', 'bekliyor', 'Ölçüm okunmuyor (Facebook sayfa insights anahtarı bekleniyor); bağlantılar açılır')
    depo.durum_yaz('x', 'kapali', 'X hesabı bağlı değil (X API ücretli; karar bekleniyor)')
    depo.ayar_yaz('toplama', {'basladi': depo.ayar('toplama')['basladi'],
                              'bitti': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'gunluk': gunluk})
    return {'calisiyor': False, 'gunluk': gunluk}


def _yas_saat(iso):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace('Z', '+00:00'))) / timedelta(hours=1)
    except (AttributeError, ValueError):
        return None
