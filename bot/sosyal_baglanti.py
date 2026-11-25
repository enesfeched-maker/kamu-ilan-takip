"""Sosyal medya paylaşımlarına UTM'li site bağlantısı ve ilk yorum metni üretir (ağ erişimi yok)."""
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

SITE = 'https://kpsstercihi.com/'
TELEGRAM = 'https://t.me/kpsstercihi'
# Açıklama ve yorumdaki bağlantısı tıklanabilen platform. YouTube Shorts'ta (Ağustos 2023'ten beri), Instagram ve
# TikTok'ta tıklanmaz; o platformlarda ölçüm profildeki kısa adresle (BIO) yapılır.
BAGLANTILI = ('facebook',)
# Profil bağlantısı için kısa adres -> platform: kpsstercihi.com/ig/ UTM'li ana sayfaya yönlendirir.
BIO = {'ig': 'instagram', 'tt': 'tiktok', 'yt': 'youtube', 'fb': 'facebook'}


def utm(platform, kampanya, icerik=None, url=SITE, ortam='social'):
    """url'ye utm_source/medium/campaign (+content) ekler; var olan sorgu ve #parça korunur."""
    url, ayrac, parca = url.partition('#')
    alanlar = [('utm_source', platform), ('utm_medium', ortam), ('utm_campaign', kampanya)]
    if icerik:
        alanlar.append(('utm_content', icerik))
    url += ('&' if '?' in url else '?') + urllib.parse.urlencode(alanlar)
    return url + ayrac + parca


def kampanya_adi(metin):
    return (metin or {}).get('tur') or 'paylasim'


def icerik_adi(metin):
    """paylasim.json'daki zaman + vakitten '20261125-aksam' gibi ad; eksikse None."""
    try:
        gun = datetime.fromisoformat(str(metin['zaman'])).strftime('%Y%m%d')
        vakit = str(metin['vakit']).strip()
        return f'{gun}-{vakit}' if vakit else None
    except Exception:
        return None


def _etiket_satiri(paragraf):
    kelimeler = paragraf.split()
    return bool(kelimeler) and all(k.startswith('#') for k in kelimeler)


def aciklama_baglantili(metin, platform):
    """Bağlantısı tıklanabilen platformlarda açıklamaya UTM'li site + Telegram bloğu ekler."""
    aciklama = metin['aciklama']
    if platform not in BAGLANTILI or 'utm_source=' in aciklama:
        return aciklama
    blok = (f'🔗 Tüm ilanlar: {utm(platform, kampanya_adi(metin), icerik_adi(metin))}\n'
            f'📢 Anlık bildirim: {TELEGRAM}')
    parcalar = aciklama.rstrip().split('\n\n')
    if len(parcalar) > 1 and _etiket_satiri(parcalar[-1]):
        return '\n\n'.join(parcalar[:-1] + [blok, parcalar[-1]])
    if len(parcalar) == 1 and _etiket_satiri(aciklama.rstrip().split('\n')[-1]) and '\n' in aciklama.strip():
        satirlar = aciklama.rstrip().split('\n')
        return '\n'.join(satirlar[:-1] + ['', blok, '', satirlar[-1]])
    return aciklama.rstrip() + '\n\n' + blok


def ilk_yorum(metin, platform):
    """Yayından hemen sonra hesabımızdan atılacak ilk yorum; TikTok için None."""
    if platform in BAGLANTILI:
        icerik = icerik_adi(metin)
        baglanti = utm(platform, kampanya_adi(metin), f'{icerik}-yorum' if icerik else 'yorum')
        return (f'📌 Başvuru koşulları ve son tarihler: {baglanti}\n'
                f"📢 Yeni ilanlar ilk Telegram'da: {TELEGRAM}")
    if platform in ('instagram', 'youtube'):
        satirlar = ['📌 Başvuru koşulları ve son tarihler profildeki bağlantıda.',
                    "📢 Yeni ilanlar ilk Telegram'da: @kpsstercihi"]
        if metin.get('soru'):
            satirlar.append(str(metin['soru']))
        return '\n'.join(satirlar)
    return None


def bio_sayfalari_yaz(docs):
    """docs/<kisa>/index.html: profildeki kısa adresi UTM'li ana sayfaya yönlendirir (noindex, site haritasına girmez)."""
    from html import escape
    for kisa, platform in BIO.items():
        hedef = escape(utm(platform, 'profil', ortam='bio'))
        klasor = Path(docs) / kisa
        klasor.mkdir(parents=True, exist_ok=True)
        (klasor / 'index.html').write_text(
            '<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>KPSS Tercihi</title>'
            f'<meta name="robots" content="noindex"><link rel="canonical" href="{SITE}">'
            f'<meta http-equiv="refresh" content="0;url={hedef}"></head>'
            f'<body><p><a href="{hedef}">kpsstercihi.com</a></p></body></html>', encoding='utf-8')
