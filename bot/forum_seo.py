"""Forum SEO (Kasım 2026): Soru-Cevap başlıklarından statik, taranabilir sayfalar (/forum/soru/<id>-<slug>/) ve konu sayfaları (/forum/konu/<kod>/).

Forum bir istemci uygulamasıdır (forum.js + Cloudflare Worker API'si); içerik tarayıcıda yüklendiği için arama motoru görmez.
Bu modül derleme sırasında herkese açık API'den başlıkları çeker ve statik HTML üretir.

Dizinleme anahtarı FORUM_DIZINLE: kapalıyken her üretilen sayfa noindex,follow olur, site haritasına ve llms.txt'ye girmez,
/forum/ kabuğu da noindex kalır. Açıkken yalnız kalite eşiğini geçen sayfalar dizinlenir (aşağıda `uygun`).

API'ye erişilemezse (ağ hatası, zaman aşımı) derleme asla düşmez ve önceki sayfalar silinmez; sayfalar yalnız
API çağrısı BAŞARILI döndüğünde ve başlık artık yoksa kaldırılır.
"""
import html
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

# AdSense yeniden incelemesi sonuçlanana kadar KAPALI; onaydan sonra True yapılır.
# False: üretilen tüm sayfalar noindex,follow; site haritasında ve llms.txt'de yok; /forum/ noindex.
# True : kalite eşiğini geçen sayfalar dizinlenir + site haritasında; /forum/ son soruları sunucu tarafında listeler.
FORUM_DIZINLE = False

API_VARSAYILAN = 'https://forum-api.kpsstercihi.com'
ZAMAN_ASIMI = 10          # saniye, her istek
EN_COK_BASLIK = 500       # derlemede çekilecek en çok başlık
EN_AZ_KELIME = 120        # soru + insan yanıtları toplamı; altı noindex
EN_AZ_KONU_SORUSU = 3     # konu sayfası dizinlenmesi için eşiği geçen en az soru
SLUG_SINIRI = 70
TR = timezone(timedelta(hours=3))
BASE_VARSAYILAN = 'https://kpsstercihi.com/'

# Soru-Cevap dışı kategoriler (sohbet odaları, etkinlik duyuruları) sayfa üretmez.
DISLANAN_KATEGORILER = {'oda', 'etkinlik'}
KATEGORILER = {'ilan': 'İlan soruları', 'puan': 'Puan ve tercih', 'kurum': 'Kurum ve şehir', 'mulakat': 'Mülakat deneyimleri',
               'haklar': 'Haklar ve tayin', 'hazirlik': 'Sınava hazırlık'}
DUZEYLER = {'lisans': 'Lisans', 'onlisans': 'Ön lisans', 'ortaogretim': 'Ortaöğretim', 'ekpss': 'EKPSS', 'agrubu': 'A grubu'}
OTOMATIK_ROLLER = {'asistan', 'sistem', 'bot'}   # insan olmayan yazarlar: şemaya girmez, sayfada "otomatik" etiketli
AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
# kategoriye göre sitenin ilgili bölümü (kök'e göre göreli yol, etiket)
BOLUMLER = {'ilan': ('#ilanlar', 'Açık ilanları gör'), 'puan': ('puanlar/', 'Taban puanları'), 'kurum': ('kurum/', 'Kurumlar'),
            'mulakat': ('rehber/', 'Rehberler'), 'haklar': ('rehber/', 'Rehberler'), 'hazirlik': ('rehber/', 'Rehberler')}

SON_DEGISIM = {}   # adres -> 'YYYY-AA-GG' (site haritası lastmod)
SON_SORULAR = []   # [(klasor, baslik)] /forum/ kabuğundaki sunucu tarafı liste için


class ForumApiHatasi(Exception):
    pass


def getir(url, zaman=ZAMAN_ASIMI):
    # Testler site_uret.main()'i çağırır; açık FORUM_API verilmedikçe test sürecinde canlı API'ye hiç gidilmez.
    if 'unittest' in sys.modules and not os.environ.get('FORUM_API'):
        raise urllib.error.URLError('test sürecinde ağ yok')
    istek = urllib.request.Request(url, headers={'User-Agent': 'kpsstercihi-site-derleme', 'Accept': 'application/json'})
    with urllib.request.urlopen(istek, timeout=zaman) as r:
        return json.loads(r.read().decode('utf-8'))


def esc(v):
    return html.escape(str(v if v is not None else ''), quote=True)


_TR_HARF = str.maketrans({'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'I': 'i',
                          'Ö': 'o', 'Ş': 's', 'Ü': 'u', 'â': 'a', 'î': 'i', 'û': 'u', 'Â': 'a', 'Î': 'i', 'Û': 'u'})


def slug(metin, sinir=SLUG_SINIRI):
    s = str(metin or '').translate(_TR_HARF).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    if len(s) > sinir:
        s = s[:sinir]
        if '-' in s:
            s = s[:s.rindex('-')]   # sözcüğü ortadan kesme
        s = s.strip('-')
    return s or 'soru'


def klasor_adi(t):
    return f'{int(t["id"])}-{slug(t.get("baslik"))}'


def _sozcukte_kes(metin, sinir):
    if len(metin) <= sinir:
        return metin
    kes = metin[:sinir].rsplit(' ', 1)[0].rstrip(' ,;:.-')
    return (kes or metin[:sinir]) + '…'


def _temiz(metin):
    return re.sub(r'\s+', ' ', str(metin or '')).strip()


def _tarih(sn):
    try:
        return datetime.fromtimestamp(int(sn), TR)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _tarih_yazi(d):
    return f'{d.day} {AYLAR[d.month - 1]} {d.year}' if d else ''


def _zaman_etiketi(sn):
    d = _tarih(sn)
    return f'<time datetime="{d.isoformat()}">{_tarih_yazi(d)}</time>' if d else ''


def insan_mi(rol):
    return (rol or '') not in OTOMATIK_ROLLER


def _gizli(x):
    return bool(x.get('gizli') or x.get('silindi') or x.get('silinmis') or x.get('sikayet_gizli'))


def insan_yanitlari(t):
    return [y for y in t.get('yanitlar', []) if insan_mi(y.get('rol')) and not _gizli(y) and _temiz(y.get('govde'))]


def kelime_sayisi(t):
    metin = ' '.join([_temiz(t.get('govde'))] + [_temiz(y.get('govde')) for y in insan_yanitlari(t)])
    return len(metin.split())


def uygun(t):
    """Dizinlenebilir mi? ≥1 insan yanıtı, soru + yanıtlar ≥ EN_AZ_KELIME kelime, gizli/silinmiş değil, soru yazarı otomatik değil."""
    if _gizli(t) or not insan_mi(t.get('rol')):
        return False
    return bool(insan_yanitlari(t)) and kelime_sayisi(t) >= EN_AZ_KELIME


def yanit_sirasi(t):
    """Görünen tüm yanıtlar: en faydalı önce, sonra kronolojik."""
    yan = [y for y in t.get('yanitlar', []) if not _gizli(y)]
    return sorted(yan, key=lambda y: (-(y.get('faydali') or 0), y.get('olusma') or 0, y.get('id') or 0))


# ---------- API ----------

def cek(api=None, ust=EN_COK_BASLIK):
    """[başlık sözlüğü + 'yanitlar'] döndürür; herhangi bir hatada ForumApiHatasi (hiçbir şey yazılmaz)."""
    api = (api or os.environ.get('FORUM_API') or API_VARSAYILAN).rstrip('/')
    try:
        liste = []
        sayfa = 1
        while len(liste) < ust and sayfa <= 100:
            v = getir(f'{api}/basliklar?sayfa={sayfa}&sirala=yeni', ZAMAN_ASIMI)
            liste += v.get('basliklar') or []
            if not v.get('sonraki'):
                break
            sayfa += 1
        liste = [b for b in liste[:ust] if b.get('kategori') in KATEGORILER and b.get('kategori') not in DISLANAN_KATEGORILER]

        def ayrinti(b):
            try:
                d = getir(f'{api}/baslik/{int(b["id"])}?limit=200', ZAMAN_ASIMI)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None   # arada gizlendi/silindi
                raise
            t = dict(d.get('baslik') or b)
            t['yanitlar'] = d.get('yanitlar') or []
            return t
        with ThreadPoolExecutor(max_workers=6) as havuz:
            sonuc = [t for t in havuz.map(ayrinti, liste) if t and t.get('id') and t.get('baslik')]
        return sonuc
    except Exception as hata:
        raise ForumApiHatasi(str(hata)) from hata


# ---------- HTML ----------

def _govde_html(metin):
    bloklar = [b for b in re.split(r'\n\s*\n', str(metin or '').strip()) if b.strip()]
    return ''.join('<p>' + '<br>'.join(esc(s.strip()) for s in b.strip().split('\n') if s.strip()) + '</p>' for b in bloklar)


def _aciklama(t):
    g = _temiz(t.get('govde')) or _temiz(t.get('baslik'))
    return _sozcukte_kes(g, 155)


def _baslik_etiketi(baslik):
    ek = ' | KPSS Forum'
    return _sozcukte_kes(_temiz(baslik), 62 - len(ek)) + ek


def _json_ld(veri):
    s = json.dumps(veri, ensure_ascii=False, separators=(',', ':'))
    return '<script type="application/ld+json">' + s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026') + '</script>'


def _kisi(rumuz):
    return {'@type': 'Person', 'name': str(rumuz or 'Üye')}


def qa_semasi(t, canonical):
    """QAPage JSON-LD sözlüğü ya da None (insan yanıtı yoksa). Otomatik/asistan yanıtlar şemaya girmez."""
    insan = sorted(insan_yanitlari(t), key=lambda y: (-(y.get('faydali') or 0), y.get('olusma') or 0, y.get('id') or 0))
    if not insan:
        return None

    def yanit(y):
        d = _tarih(y.get('olusma'))
        o = {'@type': 'Answer', 'text': _temiz(y.get('govde')), 'upvoteCount': int(y.get('faydali') or 0), 'author': _kisi(y.get('rumuz')),
             'url': f'{canonical}#y{y.get("id")}'}
        if d:
            o['dateCreated'] = d.isoformat()
        return o
    soru = {'@type': 'Question', 'name': _temiz(t.get('baslik')), 'text': _temiz(t.get('govde')) or _temiz(t.get('baslik')),
            'answerCount': len(insan)}
    d = _tarih(t.get('olusma'))
    if d:
        soru['dateCreated'] = d.isoformat()
    soru['author'] = _kisi(t.get('rumuz')) if insan_mi(t.get('rol')) else {'@type': 'Organization', 'name': 'KPSS Tercihi'}
    if (insan[0].get('faydali') or 0) >= 2:
        soru['acceptedAnswer'] = yanit(insan[0])
        diger = insan[1:]
    else:
        diger = insan
    if diger:
        soru['suggestedAnswer'] = [yanit(y) for y in diger]
    return {'@context': 'https://schema.org', '@type': 'QAPage', 'mainEntity': soru}


def _kirinti_semasi(base, t, ek=None):
    kod = t.get('kategori')
    ogeler = [('Ana sayfa', base), ('Forum', base + 'forum/')]
    if kod in KATEGORILER:
        ogeler.append((KATEGORILER[kod], f'{base}forum/konu/{kod}/'))
    if ek:
        ogeler.append(ek)
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList',
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': ad, 'item': url} for i, (ad, url) in enumerate(ogeler)]}


_STIL = ('<style>.fq{max-width:760px;margin:0 auto}.fq h1{font-size:clamp(1.4rem,4.4vw,2rem);line-height:1.25;margin:.2em 0 .5em;overflow-wrap:anywhere}'
         '.fq-chip{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px;padding:0;list-style:none}'
         '.fq-chip a,.fq-chip span{display:inline-block;border:1px solid var(--line-2,#ccc);border-radius:999px;padding:2px 12px;font-size:13px;color:inherit;text-decoration:none}'
         '.fq-meta{color:var(--muted,#666);font-size:14px;margin:0 0 12px}.fq-soru,.fq-yanit{border:1px solid var(--line,#ddd);border-radius:12px;padding:16px;margin:0 0 14px;overflow-wrap:anywhere}'
         '.fq-soru p,.fq-yanit p{margin:0 0 .7em;line-height:1.65}.fq-yanit header{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:14px;margin-bottom:8px}'
         '.fq-oto{border-style:dashed;font-size:12px;padding:0 8px;border:1px dashed var(--line-2,#aaa);border-radius:999px}'
         '.fq-cta{display:inline-block;margin:8px 0 20px;padding:12px 20px;border-radius:10px;background:var(--lime,#c8f169);color:#111310;font-weight:650;text-decoration:none}'
         '.fq-yan{margin:24px 0}.fq-yan ul{padding-left:20px;line-height:1.7}.fq h2{font-size:1.15rem;margin:22px 0 10px}</style>')


def _chipler(t, kok_konu):
    kod = t.get('kategori')
    c = []
    if kod in KATEGORILER:
        c.append(f'<li><a href="{kok_konu}{esc(kod)}/">{esc(KATEGORILER[kod])}</a></li>')
    if t.get('duzey') in DUZEYLER:
        c.append(f'<li><span>{esc(DUZEYLER[t["duzey"]])}</span></li>')
    if t.get('puan_turu'):
        c.append(f'<li><span>{esc(t["puan_turu"])}</span></li>')
    return f'<ul class="fq-chip" aria-label="Etiketler">{"".join(c)}</ul>' if c else ''


def sayfa_html(t, base, ilgili, dizinli):
    """Tek soru sayfası. `dizinli` False ise noindex,follow (reklamsız, site haritasında yok)."""
    import site_uret as su
    kok = '../../../'
    klasor = klasor_adi(t)
    canonical = f'{base}forum/soru/{klasor}/'
    baslik = _temiz(t.get('baslik'))
    robots = '' if dizinli else '<meta name="robots" content="noindex,follow">'
    sema = qa_semasi(t, canonical)
    ek = (robots + f'<meta property="og:url" content="{esc(canonical)}">'
          f'<link rel="stylesheet" href="{kok}forum.css?v={su.FORUM_SURUM}"><link rel="stylesheet" href="{kok}forum-sohbet.css?v={su.FORUM_SURUM}">'
          + (_json_ld(sema) if sema else '') + _json_ld(_kirinti_semasi(base, t, (baslik, canonical))) + _STIL)
    kod = t.get('kategori')
    kat_ad = KATEGORILER.get(kod, 'Forum')
    kirinti = (f'<nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="../../">Forum</a>'
               f'<span aria-hidden="true">/</span><a href="../../konu/{esc(kod)}/">{esc(kat_ad)}</a></nav>')
    yazar = f'<b>{esc(t.get("rumuz") or "Üye")}</b>' if insan_mi(t.get('rol')) else '<b>KPSS Tercihi</b> <span class="fq-oto">otomatik</span>'
    soru = (f'<article class="fq-soru"><p class="fq-meta">{yazar} · {_zaman_etiketi(t.get("olusma"))}</p>'
            f'{_govde_html(t.get("govde")) or ""}</article>')
    yanitlar = yanit_sirasi(t)
    if yanitlar:
        parcalar = []
        for y in yanitlar:
            oto = not insan_mi(y.get('rol'))
            kim = ('<b>KPSS Tercihi asistanı</b> <span class="fq-oto">otomatik yanıt</span>' if oto else f'<b>{esc(y.get("rumuz") or "Üye")}</b>')
            fay = f'<span>{int(y.get("faydali") or 0)} kişi faydalı buldu</span>' if (y.get('faydali') or 0) > 0 else ''
            parcalar.append(f'<article class="fq-yanit" id="y{int(y.get("id") or 0)}"><header>{kim}{_zaman_etiketi(y.get("olusma"))}{fay}</header>'
                            f'{_govde_html(y.get("govde"))}</article>')
        yanit_html = f'<h2>{len(yanitlar)} cevap</h2>' + ''.join(parcalar)
    else:
        yanit_html = '<h2>Henüz cevap yok</h2><p class="fq-meta">Bu soruya ilk cevabı sen yazabilirsin.</p>'
    bolum = BOLUMLER.get(kod)
    baglantilar = [f'<li><a href="{kok}forum/">Forumdaki tüm sorular</a></li>']
    if bolum:
        baglantilar.append(f'<li><a href="{kok}{bolum[0]}">{esc(bolum[1])}</a></li>')
    if kod != 'puan':
        baglantilar.append(f'<li><a href="{kok}puanlar/">Taban puanları</a></li>')
    if ilgili:
        baglantilar.insert(0, '<li>' + '</li><li>'.join(f'<a href="../{esc(klasor_adi(r))}/">{esc(_temiz(r.get("baslik")))}</a>' for r in ilgili) + '</li>')
    ilgili_html = (f'<aside class="fq-yan"><h2>Benzer sorular ve bağlantılar</h2><ul>{"".join(baglantilar)}</ul></aside>')
    cta = f'<a class="fq-cta" href="../../?b={int(t["id"])}" data-a="forum_cta">Forumda cevap yaz</a>'
    govde = (su.sayfa_basi(_baslik_etiketi(baslik), _aciklama(t), esc(canonical), kok, ek_head=ek, og_baslik=baslik)
             + f'<body class="kurum-page forum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok, "forum")}'
             + f'<section class="kp-hero"><div class="wrap">{kirinti}</div></section>'
             + f'<main id="icerik" class="wrap kp-main"><div class="fq"><h1>{esc(baslik)}</h1>{_chipler(t, "../../konu/")}{soru}{cta}{yanit_html}{ilgili_html}</div></main>'
             + f'{su.alt_html(kok)}</body></html>')
    return govde


def konu_html(kod, sorular, base, dizinli):
    import site_uret as su
    kok = '../../../'
    ad = KATEGORILER[kod]
    canonical = f'{base}forum/konu/{kod}/'
    robots = '' if dizinli else '<meta name="robots" content="noindex,follow">'
    ek = (robots + f'<meta property="og:url" content="{esc(canonical)}">'
          f'<link rel="stylesheet" href="{kok}forum.css?v={su.FORUM_SURUM}"><link rel="stylesheet" href="{kok}forum-sohbet.css?v={su.FORUM_SURUM}">'
          + _json_ld(_kirinti_semasi(base, {'kategori': kod}, None)) + _STIL)
    satirlar = ''.join(f'<li><a href="../../soru/{esc(klasor_adi(t))}/">{esc(_temiz(t.get("baslik")))}</a> '
                       f'<span class="fq-meta">{int(t.get("yanit_sayisi") or len(t.get("yanitlar") or []))} cevap</span></li>' for t in sorular[:100])
    aciklama = f'KPSS adaylarının "{ad}" konusunda sorduğu sorular ve topluluk cevapları.'
    kirinti = (f'<nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="../../">Forum</a>'
               f'<span aria-hidden="true">/</span><span>{esc(ad)}</span></nav>')
    return (su.sayfa_basi(f'{ad} soruları | KPSS Forum', aciklama, esc(canonical), kok, ek_head=ek)
            + f'<body class="kurum-page forum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok, "forum")}'
            + f'<section class="kp-hero"><div class="wrap">{kirinti}</div></section>'
            + f'<main id="icerik" class="wrap kp-main"><div class="fq"><h1>{esc(ad)}</h1><p class="fq-meta">{esc(aciklama)}</p>'
            + f'<ul>{satirlar}</ul><a class="fq-cta" href="../../">Forumda soru sor</a></div></main>{su.alt_html(kok)}</body></html>')


# ---------- /forum/ kabuğu ----------

def kabuk_listesi():
    """/forum/ kabuğuna girecek sunucu tarafı liste HTML'i. FORUM_DIZINLE kapalıysa ya da liste boşsa ''."""
    if not FORUM_DIZINLE or not SON_SORULAR:
        return ''
    li = ''.join(f'<li><a href="soru/{esc(k)}/">{esc(b)}</a></li>' for k, b in SON_SORULAR[:20])
    return f'<section id="fq-son" class="fq-son"><h2>Son sorular</h2><ul>{li}</ul></section>'


def kabuk_dizinli():
    """/forum/ kabuğu dizinlenebilir mi: anahtar açık ve gösterecek soru var."""
    return bool(FORUM_DIZINLE and SON_SORULAR)


# ---------- yazım ----------

def _mevcut(docs):
    """Önceki derlemeden kalan dizinli soru sayfalarını okur (API çökerse site haritası ve /forum/ listesi bozulmasın)."""
    sonuc = []
    kok = Path(docs) / 'forum' / 'soru'
    if not kok.is_dir():
        return sonuc
    for d in sorted(kok.iterdir(), key=lambda p: -int(re.match(r'\d+', p.name).group()) if re.match(r'\d+', p.name) else 0):
        f = d / 'index.html'
        if not f.is_file():
            continue
        s = f.read_text(encoding='utf-8', errors='replace')
        if 'noindex' in s:
            continue
        m = re.search(r'<h1>(.*?)</h1>', s, re.S)
        sonuc.append((d.name, html.unescape(m.group(1)) if m else d.name))
    return sonuc


def _yaz_dosya(yol, icerik):
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(icerik, encoding='utf-8')


def _llms_ekle(docs, base, girdiler):
    for ad in ('llms.txt', 'llms-full.txt'):
        f = Path(docs) / ad
        if not f.is_file():
            continue
        s = f.read_text(encoding='utf-8')
        if '## Forum soruları' in s:
            continue
        blok = '\n## Forum soruları\n' + ''.join(f'- [{b}]({base}forum/soru/{k}/)\n' for k, b in girdiler[:50])
        f.write_text(s.rstrip('\n') + '\n' + blok, encoding='utf-8')


def yaz(docs, base=BASE_VARSAYILAN, api=None, dizinle=None, basliklar=None):
    """Sayfaları üretir; site haritasına girecek adreslerin listesini döndürür (dizinleme kapalıyken hep boş).
    Hiçbir koşulda istisna fırlatmaz: API hatasında önceki sayfalar ve liste korunur."""
    global SON_SORULAR
    docs = Path(docs)
    dizinle = FORUM_DIZINLE if dizinle is None else dizinle
    SON_DEGISIM.clear()
    try:
        basliklar = cek(api) if basliklar is None else basliklar
    except ForumApiHatasi as hata:
        print(f'Uyarı: forum API okunamadı, önceki forum sayfaları korunuyor: {hata}')
        eski = _mevcut(docs) if dizinle else []
        SON_SORULAR = eski
        return [f'{base}forum/soru/{k}/' for k, _ in eski] if dizinle else []
    except Exception as hata:   # savunma: derleme asla düşmesin
        print(f'Uyarı: forum sayfaları üretilemedi: {hata}')
        return []

    basliklar = sorted(basliklar, key=lambda t: -(t.get('son_hareket') or t.get('olusma') or 0))
    adresler = []
    girdiler = []
    uygunlar = {}
    yazilan = set()
    for t in basliklar:
        ok = dizinle and uygun(t)
        k = klasor_adi(t)
        ayni = [r for r in basliklar if r is not t and r.get('kategori') == t.get('kategori')]
        ayni.sort(key=lambda r: (not uygun(r), -(r.get('son_hareket') or 0)))
        _yaz_dosya(docs / 'forum' / 'soru' / k / 'index.html', sayfa_html(t, base, ayni[:5], ok))
        yazilan.add(k)
        if ok:
            url = f'{base}forum/soru/{k}/'
            adresler.append(url)
            girdiler.append((k, _temiz(t.get('baslik'))))
            d = _tarih(t.get('son_hareket') or t.get('olusma'))
            if d:
                SON_DEGISIM[url] = d.date().isoformat()
        if uygun(t):
            uygunlar.setdefault(t.get('kategori'), []).append(t)

    # konu sayfaları
    konu_yazilan = set()
    for kod in KATEGORILER:
        hepsi = [t for t in basliklar if t.get('kategori') == kod]
        if not hepsi:
            continue
        ok = dizinle and len(uygunlar.get(kod, [])) >= EN_AZ_KONU_SORUSU
        liste = uygunlar.get(kod, []) if dizinle else hepsi
        _yaz_dosya(docs / 'forum' / 'konu' / kod / 'index.html', konu_html(kod, liste or hepsi, base, ok))
        konu_yazilan.add(kod)
        if ok:
            url = f'{base}forum/konu/{kod}/'
            adresler.append(url)
            SON_DEGISIM[url] = datetime.now(TR).date().isoformat()

    # API başarılı döndü: artık olmayan başlık/konu sayfalarını kaldır
    for kok, tut in ((docs / 'forum' / 'soru', yazilan), (docs / 'forum' / 'konu', konu_yazilan)):
        if kok.is_dir():
            for d in kok.iterdir():
                if d.is_dir() and d.name not in tut:
                    shutil.rmtree(d, ignore_errors=True)

    SON_SORULAR = girdiler if dizinle else []
    if dizinle and girdiler:
        _llms_ekle(docs, base, girdiler)
    print(f'Forum SEO: {len(yazilan)} soru sayfası, {len(adresler)} adres haritada (dizinleme {"açık" if dizinle else "kapalı"})')
    return adresler
