"""Generate crawlable public detail pages from the existing verified registry."""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
import json as _json
try:
    BASE = _json.loads((ROOT / 'config.json').read_text(encoding='utf-8')).get('site_url') or 'https://kpsstercihi.com/'
except (OSError, ValueError):
    BASE = 'https://kpsstercihi.com/'
if not BASE.endswith('/'):
    BASE += '/'
TR = timezone(timedelta(hours=3))
KART_GENISLIK = 720
LOGO_BOYUT = 128
EN_COK_LOGO_INDIRME = 150
CSS_SURUM = 20
LOGO_SURUM = 2
ACIK_ZEMIN, KOYU_ZEMIN = '#F6F6F1', '#0D0E0C'
ANALIZ_SURUM = 3  # docs/a.js (çerezsiz ziyaret istatistiği) önbellek sürümü
# <head> içinde, theme-color etiketinden sonra: kit-theme (elle seçim) > sistem koyu tercihi > gece 20:00-07:00 koyu > açık.
TEMA_BETIGI = ('<script>try{var r=document.documentElement,O=window.kitOto=function(){try{if(matchMedia("(prefers-color-scheme: dark)").matches)return!0}catch(e){}var h=new Date().getHours();return h>=20||h<7},K=window.kitKoyu=function(){var s,o=O();try{s=JSON.parse(localStorage.getItem("kit-theme"))}catch(e){}if(s&&typeof s==="object"&&s.a===o&&(s.t==="dark"||s.t==="light"))return s.t==="dark";if(s!=null)try{localStorage.removeItem("kit-theme")}catch(e){}return o},U=function(){if(window.kitTemaUygula)return window.kitTemaUygula();var d=K(),m=document.querySelector("meta[name=theme-color]");r.dataset.theme=d?"dark":"light";if(m)m.content=d?"' + KOYU_ZEMIN + '":"' + ACIK_ZEMIN + '"},C=function(){if((K()?"dark":"light")!==r.dataset.theme)U()};U();setInterval(C,3e5);try{matchMedia("(prefers-color-scheme: dark)").addEventListener("change",C)}catch(e){}}catch(e){document.documentElement.dataset.theme="light"}</script>')
TG_IKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 4-18 7.2 6 2.3M21 4l-3 16-8.5-6.5M21 4 9.5 13.5v5.5l3-3.5"/></svg>'
KISI_IKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>'


def esc(value):
    return html.escape(str(value or ''), quote=True)


def ikonlar(kok):
    """Sekme simgesi + iOS ana ekran simgesi + web uygulaması bildirimi."""
    v = LOGO_SURUM
    return (f'<link rel="icon" href="{kok}assets/logo-32.png?v={v}" type="image/png" sizes="32x32">'
            f'<link rel="icon" href="{kok}assets/logo-192.png?v={v}" type="image/png" sizes="192x192">'
            f'<link rel="apple-touch-icon" href="{kok}assets/logo-180.png?v={v}">'
            f'<link rel="manifest" href="{kok}manifest.webmanifest">')


KABUK_SURUM = 3
TG_DOLU = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.5 3.6 2.9 10.8c-1.1.4-1.1 1.2-.2 1.5l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.4l2.4-2.3 4.9 3.6c.9.5 1.5.2 1.8-.8l3.2-15.1c.3-1.3-.5-1.9-1.4-1.6zM9 13.4l9.3-5.9c.4-.3.8-.1.5.2l-7.9 7.1-.3 3.4z"/></svg>'
HAMBURGER_IKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
# Mobil menü düğmesi: iç sayfaların kendi betiğine bağlı kalmasın diye üst barın hemen ardından çalışır.
MENU_BETIGI = ('<script>(function(){var h=document.getElementById("tb"),b=document.getElementById("tb-ac");if(!h||!b)return;'
               'b.onclick=function(){var o=!h.classList.contains("acik");h.classList.toggle("acik",o);b.setAttribute("aria-expanded",String(o));'
               'b.setAttribute("aria-label",o?"Menüyü kapat":"Menüyü aç")}})()</script>')


def ust_html(kok, aktif=''):
    """Ana sayfayla aynı ince koyu üst bar (docs/index.html .tb, docs/kabuk.css); bağlantılar `kok` göreli."""
    # Taban puanı sayfaları (kpss-taban-puanlari/) da 'puanlar' bölümüdür; menüde tek sekme robot ve tablo sayfasına gider.
    menu = [('İlanlar', f'{kok}#ilanlar', 'ilanlar'),
            ('Taban Puanları', f'{kok}puanlar/', 'puanlar'),
            ('Takvim', f'{kok}#takvim', ''), ('Kayıtlı', f'{kok}#kayitli', '')]
    bagla = ''.join(f'<a href="{h}" data-a="menu" data-a-x="{ad}"{" class=" + chr(34) + "aktif" + chr(34) + " aria-current=" + chr(34) + "page" + chr(34) if a and a == aktif else ""}>'
                    f'{ad}{"<b class=" + chr(34) + "tb-sayi" + chr(34) + " id=" + chr(34) + "saved-count-m" + chr(34) + " hidden>0</b>" if ad == "Kayıtlı" else ""}</a>'
                    for ad, h, a in menu)
    return (f'<header class="tb" id="tb"><div class="tb-ic"><a class="tb-marka" href="{kok}" aria-label="KPSS Tercihi ana sayfa">'
            f'<img src="{kok}assets/logo-96.webp?v={LOGO_SURUM}" alt="" width="34" height="34"><span>KPSS Tercihi</span></a>'
            f'<a class="tb-tg" href="https://t.me/kpsstercihi" target="_blank" rel="noopener" data-a="telegram" data-a-x="ust">{TG_DOLU}<span class="tam">Telegram\'a katıl</span><span class="kisa">Katıl</span></a>'
            f'<button type="button" class="tb-ac" id="tb-ac" aria-expanded="false" aria-controls="tb-nav" aria-label="Menüyü aç">{HAMBURGER_IKON}</button>'
            f'<nav class="tb-nav" id="tb-nav" aria-label="Ana menü">{bagla}<span class="tb-ayrac" aria-hidden="true"></span>'
            f'<a class="tb-ikon" href="{kok}?profil=1" aria-label="Profil">{KISI_IKON}<span class="tb-etiket">Profil</span></a>'
            f'<span class="tb-tema"><span class="tb-tema-et">Tema</span><button type="button" class="anahtar" id="theme" aria-pressed="false" aria-label="Koyu temaya geç"><span class="bulut"></span><span class="yildiz y1"></span><span class="yildiz y2"></span><span class="yildiz y3"></span><span class="top"></span></button></span>'
            f'</nav></div></header>{MENU_BETIGI}')


def alt_html(kok, yil=None):
    """Ana sayfayla aynı koyu alt bilgi: marka, bağlantılar ve bağımsızlık notu."""
    yil = yil or datetime.now(TR).year
    return (f'<footer class="ab"><div class="ab-ic"><div class="ab-marka"><img src="{kok}assets/logo-96.webp?v={LOGO_SURUM}" alt="" width="36" height="36">'
            f'<div><strong>KPSS Tercihi</strong><span>Kamu ilanları, sade ve tek yerde</span></div></div>'
            f'<nav class="ab-linkler" aria-label="Alt bilgi"><a href="https://t.me/kpsstercihi" target="_blank" rel="noopener" data-a="telegram" data-a-x="alt">Telegram</a><a href="{kok}sss/">Sık sorulanlar</a><a href="{kok}#bilgi/gizlilik">Gizlilik</a></nav>'
            f'<p class="ab-not">© <span id="yil">{yil}</span> KPSS Tercihi</p></div></footer>')


def sayfa_basi(baslik, aciklama, canonical, kok, og_tur='website', ek_head='', og_baslik=None):
    """<!doctype> … <body> açılışına kadar ortak kısım (kurum ve ilan sayfaları)."""
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="google-adsense-account" content="ca-pub-8335827974832277"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8335827974832277" crossorigin="anonymous"></script>'
            f'<meta name="theme-color" content="{ACIK_ZEMIN}"><meta name="color-scheme" content="light dark">{TEMA_BETIGI}'
            f'<title>{esc(baslik)}</title><meta name="description" content="{esc(aciklama)}"><link rel="canonical" href="{canonical}">'
            f'<meta property="og:title" content="{esc(og_baslik or baslik)}"><meta property="og:description" content="{esc(aciklama)}"><meta property="og:type" content="{og_tur}">{ek_head}'
            f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap">'
            f'<link rel="stylesheet" href="{kok}sayfa.css?v={CSS_SURUM}"><link rel="stylesheet" href="{kok}kabuk.css?v={KABUK_SURUM}">{ikonlar(kok)}<script src="{kok}a.js?v={ANALIZ_SURUM}" defer></script><script src="{kok}sayfa.js?v={CSS_SURUM}" defer></script></head>')


def _kurum_bloklari(item, gorsel, logo_html):
    """(hero kurum bağlantısı, breadcrumb parçası, yan kart) — kurum sayfasına tek bağlantı."""
    from kurum_sayfasi import kurum_adi, kurum_slug
    ad = esc(kurum_adi(item.get('kurum')))
    if not (item.get('kurum') or '').strip():
        return f'<div class="detail-org">{logo_html}<p>Kurum belirtilmemiş</p></div>', '', ''
    slug = (gorsel or {}).get('kurum_slug') or kurum_slug(item['kurum'])
    n = (gorsel or {}).get('kurum_sayisi') or 1
    href = f'../../kurum/{esc(slug)}/'
    etiket = f'Bu kurumun tüm ilanları ({n})' if n > 1 else 'Kurum sayfası'
    hero = (f'<a class="kurum-link" href="{href}" title="{ad} — kurumun tüm ilanları">{logo_html}'
            f'<span><b>{ad}</b><span class="more">{etiket} <i aria-hidden="true">→</i></span></span></a>')
    kirinti = f'<span aria-hidden="true">/</span><a href="{href}">{ad}</a>'
    yan = (f'<a class="aside-kurum" href="{href}">{logo_html}<span><b>{ad}</b>'
           f'<span class="more">{f"Diğer {n - 1} ilanını gör" if n > 1 else "Kurum sayfasını gör"} →</span></span></a>')
    return hero, kirinti, yan


def sayfa_kabugu(baslik, aciklama, canonical, icerik, govde_sinifi='', og_baslik=None):
    """Kurum sayfaları için ortak iskelet (ilan sayfasıyla aynı üst/alt bölüm)."""
    kok = '../../'
    return (sayfa_basi(baslik, aciklama, canonical, kok, og_baslik=og_baslik)
            + f'<body class="{govde_sinifi}"><a class="skip" href="#icerik">İçeriğe geç</a>{ust_html(kok)}{icerik}{alt_html(kok)}'
              f'<noscript><div class="not wrap">Bazı özellikler (kaydetme, kalan gün) için JavaScript gerekir.</div></noscript></body></html>')


def _virgul(n, k=1):
    return f'{n:.{k}f}'.replace('.', ',')


_KOSUL_ETIKET = {'Belgedeki kadro koşullarından alıntı': 'Genel koşul', 'Belgede belirtilen koşullar': 'Genel koşul',
                 'Sınav puanı koşulu · kadroya göre muafiyetler için belgeyi inceleyin': 'KPSS puanı', 'Sınav puanı koşulu': 'KPSS puanı'}
# PDF tablosu düz metne dökülünce sütunlar birbirine karışır (başlık sözcükleri, BP01 gibi kodlar, "4birinden").
_KARISIK_RE = re.compile(r'\b[A-ZÇĞİÖŞÜ]{2,4}\d{2,3}\b|\d[a-zçğıöşü]{3,}')
_TABLO_BASLIK_RE = re.compile(r'\b(?:Ünvan|Unvanı|Kodu|Cinsiyet|Aranan Nitelikler|Sıra No|Adet)\b')


def _kosul_temiz(metin):
    """Koşul metnini sadeleştirir; sütunları karışmış (okunmaz) metinde '' döner."""
    metin = re.sub(r'\s+', ' ', metin or '').strip()
    if not metin or _KARISIK_RE.search(metin) or len(_TABLO_BASLIK_RE.findall(metin)) >= 2:
        return ''
    metin = re.sub(r'^(?:\d{1,2}[).-]|[a-zçğ]\))\s*', '', metin)
    return metin[:1].upper() + metin[1:]


def _kosul_html(metin):
    """a) b) c) maddelerini alt alta yazar."""
    return re.sub(r'\s(?=[a-zçğ]\)\s)', '<br>', esc(metin))


def _kadro_tablosu(item, kosulsuz=False):
    """Kadro / kontenjan tablosu (kadro adıyla eşleşen koşul metni aynı satırda) ve eşleşmeyen koşullar için ikinci tablo.
    HTML bölümü döner (başlıkla birlikte); gösterilecek bir şey yoksa boş metin."""
    import kurum_sayfasi as ks
    from siniflandir import kucuk
    kadrolar = ks.kadrolar(item)
    sartlar = [dict(s) for s in item.get('sartlar') or []]
    if not kadrolar and not sartlar:
        return ''
    def sinirli(kisa, uzun):
        return bool(kisa) and re.search(r'(?<!\w)' + re.escape(kisa) + r'(?!\w)', uzun) is not None
    if kosulsuz:  # koşullar ayrıca (PDF'ten madde madde) gösterilecek: yalnız kadro / kontenjan
        sartlar = []
    satirlar, kullanilan = [], set()
    for adet, ad in kadrolar:
        a, secilen = kucuk(ad), None
        bos = [(n, kucuk(s.get('kadro') or '')) for n, s in enumerate(sartlar) if n not in kullanilan]
        secilen = next((n for n, b in bos if a and a == b), None)
        if secilen is None:
            secilen = next((n for n, b in bos if sinirli(a, b) or sinirli(b, a)), None)
        metin = ''
        if secilen is not None:
            kullanilan.add(secilen)
            metin = _kosul_temiz(sartlar[secilen].get('metin'))
        satirlar.append((ad, adet, metin))
    kalan = [{'kadro': _KOSUL_ETIKET.get(s.get('kadro'), s.get('kadro')), 'metin': m}
             for n, s in enumerate(sartlar) if n not in kullanilan for m in [_kosul_temiz(s.get('metin'))] if m]
    html_ = ''
    if satirlar:
        kosullu = any(m for _, _, m in satirlar)
        govde = ''.join(
            f'<tr><td>{esc(ad)}</td><td class="sayi" data-et="Kontenjan">{esc(ks.SAYI_YAZ(adet) if adet else "—")}</td>'
            + (f'<td data-et="Koşullar">{_kosul_html(metin) if metin else "Resmî ilandan kontrol et"}</td>' if kosullu else '') + '</tr>'
            for ad, adet, metin in satirlar)
        baslik = '<th scope="col">Kadro</th><th scope="col" class="sayi">Kontenjan</th>' + ('<th scope="col">Başvuru koşulları</th>' if kosullu else '')
        html_ += (f'<h2>{"Kadro ve başvuru koşulları" if kosullu else "Kadro ve kontenjan"}</h2>'
                  f'<div class="tablo-kap"><table class="ktablo"><thead><tr>{baslik}</tr></thead><tbody>{govde}</tbody></table></div>')
    if kalan:
        govde = ''.join(f'<tr><td>{esc(s.get("kadro") or "Genel")}</td><td>{_kosul_html(s["metin"])}</td></tr>' for s in kalan)
        html_ += (f'<h{"3" if satirlar else "2"} class="alt-h">Başvuru koşullarından seçmeler</h{"3" if satirlar else "2"}>'
                  f'<div class="tablo-kap"><table class="ktablo"><thead><tr><th scope="col">Konu</th><th scope="col">Koşul</th></tr></thead><tbody>{govde}</tbody></table></div>')
    return html_

BELGE_KLASORU = Path(__file__).resolve().parents[1] / 'docs' / 'belgeler' / 'sbb'


def _pdf_kadrolari(item):
    """İlan belgesinin (SBB PDF kopyası) kadro tablosu satırları; belge yoksa ya da tablo okunamazsa ()."""
    sha = str(item.get('belge_sha256') or '')
    if not re.fullmatch(r'[a-f0-9]{64}', sha) or not (BELGE_KLASORU / f'{sha}.pdf').is_file():
        return ()
    import pdf_tablo
    return pdf_tablo.tablo_oku(str(BELGE_KLASORU / f'{sha}.pdf'))


def _unvan_duzgun(ad):
    return _duzgun(ad) if ad.upper() == ad else ad


def _kadro_kartlari(item, satirlar, belge):
    """PDF tablosundan kadro kartları: ünvan + kişi sayısı, nitelikler madde madde, KPSS türü/taban, cinsiyet;
    altta tüm kadrolar için ortak koşullar ve resmî belge bağlantısı."""
    import pdf_tablo
    kartlar = ''
    for s in satirlar:
        alt = []
        if s['tur'] or s['taban']:
            kpss = ', '.join(s['tur']) + (' · ' if s['tur'] and s['taban'] else '') + (f'en az {s["taban"]} puan' if s['taban'] else '')
            alt.append(f'<span><em>KPSS</em> {esc(kpss)}</span>')
        if s['cinsiyet']:
            alt.append(f'<span><em>Cinsiyet</em> {esc(s["cinsiyet"])}</span>')
        maddeler = ''.join(f'<li>{esc(sade_madde(m))}</li>' for m in s['nitelik'] if sade_madde(m))
        kartlar += (f'<div class="kk"><div class="kk-bas"><strong>{esc(_unvan_duzgun(s["unvan"]))}</strong>'
                    + (f'<span class="kk-adet">{s["adet"]} kişi</span>' if s['adet'] else '') + '</div>'
                    + (f'<ul>{maddeler}</ul>' if maddeler else '')
                    + (f'<div class="kk-alt">{"".join(alt)}</div>' if alt else '') + '</div>')
    metin = ' '.join(str(x.get('metin') or '') for x in item.get('sartlar') or []) + ' ' + str(item.get('ozet') or '')
    ortak = ''.join(f'<li>{esc(x)}</li>' for x in pdf_tablo.ortak_kosullar(metin))
    baglanti = (f'<li>Genel şartların tamamı ve istenen belgeler: <a class="yazi-link" href="{esc(belge)}" target="_blank" '
                f'rel="noopener noreferrer">resmî ilan belgesi (PDF) ↗</a></li>') if belge else ''
    return (f'<h2>Kadrolar ve başvuru koşulları</h2><div class="kk-liste">{kartlar}</div>'
            + (f'<div class="kk-ortak"><h3>Tüm kadrolar için</h3><ul>{ortak}{baglanti}</ul></div>' if ortak or baglanti else ''))


KK_OGRENIM = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}


def sade_madde(m):
    """Şart maddesini okunur kısalığa indirir (12 Ekim 2026 kullanıcı kararı: kişi baktığı anda anlamalı):
    'ÖSYM tarafından 2025 ve 2026 yılında yapılan … KPSS P3 puan türünde en az 60 (altmış) puan almış olmak' -> '2025-2026 KPSS P3
    en az 60 puan almış olmak'; '10/6/2004 tarihli ve 5188 sayılı … Kanun'un 10 uncu maddesinde belirtilen şartlar ile' gibi mevzuat
    öncülleri ve '(Ancak …)' gibi uzun parantez açıklamaları atılır; '60 (altmış)' -> '60'; sondaki virgül nokta olur."""
    m = re.sub(r'\s+', ' ', str(m or '')).strip()
    puan = re.search(r'KPSS\)?\s*(?:\(\w\)\s*grubu\s*)?(P\s?\d{1,3})\b.*?en az\s*(\d{2,3})', m)
    if puan and re.search(r'puan\w*\s+(?:almış|sahip)', m) and len(m) > 50:
        yillar = sorted(set(re.findall(r'\b(20\d\d)\b', m)))
        yil = (yillar[0] if len(yillar) == 1 else f'{yillar[0]}-{yillar[-1]}') + ' ' if yillar else ''
        return f'{yil}KPSS {puan.group(1).replace(" ", "")} en az {puan.group(2)} puan almış olmak.'
    m = re.sub(r'^\d{1,2}[./]\d{1,2}[./]\d{4}\s+tarihli\s+ve\s+\d+\s+sayılı\s+.*?(?:belirtilen|belirtilen|belirtiler)\s+şartlar\s+ile\s+', '', m)
    m = re.sub(r'\s*\([^()]{80,}\)?\s*$', '', m)   # sondaki uzun parantez açıklaması (belge yükleme, istisna notu)
    m = re.sub(r'(?<=\.)\s+Ancak\s.{120,}$', '', m)   # uzun istisna cümlesi ('Ancak … kabul edilir.') ayrıntısı resmî ilanda
    m = re.sub(r'\s*(?:,\s*)?(?:ya da|veya)\s+(?:buna|bunlara)\s+denkliği\s+Yükseköğretim\s+Kurulunca\s+kabul\s+edilmiş\s+yurt\s?dışındaki\s+'
               r'Yükseköğretim\s+Kurumlarından', '', m)   # her ilanda geçen YÖK denklik kalıbı
    m = re.sub(r'\bmezun\s+mezun', 'mezun', m)
    m = re.sub(r'(\d+)\s*\((?:[a-zçğıöşü]+)\)', r'\1', m)
    m = m.replace('“', '').replace('”', '').replace('"', '')
    m = re.sub(r'[,;]\s*$', '.', m.strip())
    if m and m[-1] not in '.!?)':
        m += '.'
    return m[:1].upper() + m[1:] if m else m


def _kk_kadro_kartlari(kadrolar, kaynak):
    """Kariyer Kapısı kadro ayrıntısından kadro kartları (PDF kartlarıyla aynı görünüm): ünvan + kişi sayısı, şart maddelerinin
    TAMAMI, altta öğrenim, görev yeri (il başına kişi), sınav usulü. Aynı ünvan ve aynı şartlı il grupları tek kartta birleşir."""
    gruplar = {}
    for k in kadrolar:
        anahtar = (k['unvan'], tuple(k.get('maddeler') or ()))
        g = gruplar.setdefault(anahtar, {'unvan': k['unvan'], 'adet': 0, 'iller': {}, 'ogrenim': k.get('ogrenim'),
                                         'sinav': k.get('sinav'), 'maddeler': list(k.get('maddeler') or [])})
        g['adet'] += k.get('adet') or 0
        for il in k.get('iller') or []:
            g['iller'][il] = g['iller'].get(il, 0) + (k.get('adet') or 0)
    kartlar = ''
    for g in sorted(gruplar.values(), key=lambda g: -g['adet']):
        alt = []
        if g['ogrenim'] in KK_OGRENIM:
            alt.append(f'<span><em>Öğrenim</em> {KK_OGRENIM[g["ogrenim"]]}</span>')
        if g['iller']:
            yer = ' · '.join(f'{_unvan_duzgun(il)} {n}' if len(g['iller']) > 1 and n else _unvan_duzgun(il) for il, n in g['iller'].items())
            alt.append(f'<span><em>Görev yeri</em> {esc(yer)}</span>')
        if g['sinav']:
            alt.append(f'<span><em>Sınav</em> {esc(g["sinav"])}</span>')
        maddeler = ''.join(f'<li>{esc(sade_madde(m))}</li>' for m in g['maddeler'] if sade_madde(m))
        kartlar += (f'<div class="kk"><div class="kk-bas"><strong>{esc(_unvan_duzgun(g["unvan"]))}</strong>'
                    + (f'<span class="kk-adet">{g["adet"]} kişi</span>' if g['adet'] else '') + '</div>'
                    + (f'<ul>{maddeler}</ul>' if maddeler else '<p class="kk-yok">Şartlar için resmî ilana bak.</p>')
                    + (f'<div class="kk-alt">{"".join(alt)}</div>' if alt else '') + '</div>')
    baglanti = (f'<li>Genel şartların tamamı ve istenen belgeler: <a class="yazi-link" href="{esc(kaynak)}" target="_blank" '
                f'rel="noopener noreferrer">resmî ilan ↗</a></li>') if kaynak else ''
    return (f'<h2>Kadrolar ve başvuru koşulları</h2><div class="kk-liste">{kartlar}</div>'
            + (f'<div class="kk-ortak"><ul>{baglanti}</ul></div>' if baglanti else ''))


def _pdf_sart_bolumleri(item):
    """Tablosuz ilan belgesindeki şart bölümleri (pdf_tablo.sart_bolumleri); belge yoksa ()."""
    sha = str(item.get('belge_sha256') or '')
    if not re.fullmatch(r'[a-f0-9]{64}', sha) or not (BELGE_KLASORU / f'{sha}.pdf').is_file():
        return ()
    import pdf_tablo
    return pdf_tablo.sart_bolumleri(str(BELGE_KLASORU / f'{sha}.pdf'))


def _sart_bolumleri_html(bolumler, belge, gorunen=10):
    """Başvuru şartları: her bölüm başlıklı madde listesi; pozisyon adları kalın ara başlık; uzun liste katlanır."""
    def li(metin, alt):
        return f'<li class="sb-alt">{esc(metin)}</li>' if alt else f'<li>{esc(metin)}</li>'
    govde = ''
    for ad, maddeler in bolumler:
        ilk, kalan = maddeler[:gorunen], maddeler[gorunen:]
        if len(kalan) <= 2:
            ilk, kalan = maddeler, ()
        govde += f'<div class="sb"><h3>{esc(ad)}</h3><ul>{"".join(li(m, a) for m, a in ilk)}</ul>'
        if kalan:
            n = sum(not a for _, a in kalan)
            govde += (f'<details class="sb-devam"><summary>Tamamını göster ({n} madde daha)</summary>'
                      f'<ul>{"".join(li(m, a) for m, a in kalan)}</ul></details>')
        govde += '</div>'
    baglanti = (f'<p class="sb-kaynak">Başvuru belgeleri ve şartların tamamı: <a class="yazi-link" href="{esc(belge)}" '
                f'target="_blank" rel="noopener noreferrer">resmî ilan belgesi (PDF) ↗</a></p>') if belge else ''
    return f'<h2>Başvuru şartları</h2>{govde}{baglanti}'


def _kopya_notlari(kopya):
    """(ikincil kayıt için üst not, birincil kayıt için kaynak satırı) — kopya: kopya.sayfa_bilgisi() çıktısı ya da None."""
    if not kopya:
        return '', ''
    if kopya.get('rol') == 'ikincil':
        return (f'<p class="not kopya-not"><strong>Bu ilan başka bir kaynakta da yayımlandı.</strong> '
                f'<a class="yazi-link" href="../{esc(kopya["birincil"])}/">Bu ilanın daha ayrıntılı kaydı →</a></p>'), ''
    adlar = kopya.get('adlar') or []
    baglar = ', '.join(f'<a href="{esc(h)}" target="_blank" rel="noopener noreferrer">{esc(a)} ↗</a>' for a, h in kopya.get('baglantilar') or [])
    if len(adlar) < 2 or not baglar:
        return '', ''
    return '', f'<p class="d-kaynaklar">Bu ilan {len(adlar)} kaynakta yayımlandı: {baglar}</p>'


def benzer_ilanlar(kayit, kayitlar, en_cok=5):
    """Aynı unvan/meslek fotoğrafı olan diğer açık ilanlar (liste.json kayıtları), en çok `en_cok`; en yakın son tarih önce."""
    if not kayit:
        return []
    from siniflandir import kucuk

    onbellek = {}

    def unvanlar(k):
        if k.get('key') not in onbellek:
            onbellek[k.get('key')] = set(k.get('unvanlar') or ()) or {re.sub(r'^\d+\s+', '', kucuk(p)).strip() for p in re.split(r'\s*,\s*', k.get('manset') or '') if p.strip()}
        return onbellek[k.get('key')]
    mevcut = unvanlar(kayit)
    meslek = {m for m in kayit.get('meslek') or [] if not m.startswith('30-')}
    sonuc = []
    for k in kayitlar or []:
        if k.get('key') == kayit.get('key'):
            continue
        skor = 2 if mevcut & unvanlar(k) else 1 if meslek & set(k.get('meslek') or []) else 0
        if skor:
            sonuc.append((-skor, k.get('son_tarih') or '9999', k.get('key') or '', k))
    return [p[3] for p in sorted(sonuc, key=lambda p: p[:3])[:en_cok]]


def _durum_metni(item, simdi):
    """(rozet metni, durum sınıfı): ks.durum + 'tarih yok' ve 'başvuru ... açılıyor' metinleri."""
    import kurum_sayfasi as ks
    metin, sinif = ks.durum(item, simdi)
    if sinif == 'none':
        metin = 'Son tarihi resmî ilandan doğrula'
    if sinif == 'upcoming' and item.get('baslangic_zaman'):
        try:
            b = datetime.fromisoformat(item['baslangic_zaman']).astimezone(TR)
            metin = f'Başvuru {b.day} {ks.AY[b.month - 1]}’de açılıyor'
        except ValueError:
            pass
    return metin, sinif


def hero_html(item, gorsel, kayit, simdi, kok='../../'):
    """İlan ayrıntısı başlık kartı: <section class="dh"> — kurum, başlık, afiş karosu (meslek fotoğrafı + kadro sayısı)
    ve bilgi şeridi (son başvuru + geri sayım · yer · öğrenim · KPSS)."""
    import kurum_sayfasi as ks
    import liste_verisi
    gorsel = gorsel or {}
    alanlar = ks.kart_alanlari(item)
    toplam = alanlar.get('toplam')
    h1 = liste_verisi.baslik_temiz(alanlar['manset'])
    if toplam:  # sayı karoda büyük yazılıyor: başlıkta tekrar etme ("9 Zabıta Memuru" -> "Zabıta Memuru")
        h1 = re.sub(r'^\d+\s+', '', h1)
    if alanlar.get('ek'):
        h1 += f' +{int(alanlar["ek"])}'
    # kurum
    kurum = ''
    if (item.get('kurum') or '').strip():
        ad = esc(ks.kurum_adi(item.get('kurum')))
        if gorsel.get('logo'):
            logo = f'<img class="detail-logo" src="{kok}{esc(gorsel["logo"])}" alt="" width="36" height="36">'
        else:
            logo = f'<span class="detail-logo institution-badge" style="--h:{_ton(item.get("kurum"))}" aria-hidden="true">{esc(_bas_harfler(item.get("kurum")))}</span>'
        slug = gorsel.get('kurum_slug') or ks.kurum_slug(item['kurum'])
        n = gorsel.get('kurum_sayisi') or 1
        etiket = f'Kurumun tüm ilanları ({n}) →' if n > 1 else 'Kurumun tüm ilanları →'
        kurum = (f'<a class="dh-kurum" href="{kok}kurum/{esc(slug)}/" title="{ad} — kurumun tüm ilanları">{logo}'
                 f'<span><b>{ad}</b><small>{etiket}</small></span></a>')
    # durum rozeti: kalan gün Son başvuru hücresinde; rozet yalnız acil ya da özel durumda (yakında/kapalı/iptal/duyuru)
    metin, sinif = _durum_metni(item, simdi)
    pill = 'kapali' if sinif in ('closed', 'cancelled') else 'yakinda' if sinif == 'upcoming' else ''
    gun = None
    if item.get('son_tarih'):
        try:
            gun = (datetime.fromisoformat(item['son_tarih']).date() - simdi.date()).days
        except ValueError:
            pass
    acil = sinif in ('today', 'urgent') and gun is not None and gun <= 2
    if acil:
        pill = 'acil'
    goster = acil or sinif in ('upcoming', 'closed', 'cancelled', 'info')
    pill_html = f'<span class="pill{" " + pill if pill else ""}">{esc(metin)}</span>' if goster else ''
    # afiş karosu: fotoğraf (isteğe bağlı) + kadro sayısı; ikisi de yoksa karo yok
    foto = next((f for f in ((kayit or {}).get('meslek') or alanlar.get('meslek') or []) if not f.startswith('30-')), None)
    afis = ''
    if foto or toplam:
        img = f'<img src="{kok}assets/meslek/kucuk/{esc(foto)}" alt="" width="232" height="232" decoding="async">' if foto else ''
        cap = f'<figcaption><b>{esc(ks.SAYI_YAZ(toplam))}</b><small>kadro</small></figcaption>' if toplam else ''
        afis = f'<figure class="dh-afis{"" if foto else " fotosuz"}">{img}{cap}</figure>'
    # bilgi şeridi
    son = _bitis(item)
    if son:
        s = son.astimezone(TR)
        tarih = f'{s.day} {ks.AY[s.month - 1]} {s.year}' + (f', {s:%H:%M}' if item.get('son_zaman') else '')
        geri = esc(metin if sinif in ('ok', 'soon', 'urgent', 'today', 'upcoming', 'closed') else '')
        veri = (f' data-son="{esc(item["son_tarih"])}" data-zaman="{esc(item.get("son_zaman") or "")}"'
                if sinif in ('ok', 'soon', 'urgent', 'today') and item.get('son_tarih') else '')
        son_html = (f'<div class="dh-son{" acil" if acil else " yok" if sinif in ("closed", "cancelled") else ""}"><dt>Son başvuru</dt>'
                    f'<dd>{tarih}<span class="dh-geri"{veri}>{geri}</span></dd></div>')
    else:
        son_html = '<div class="dh-son yok"><dt>Son başvuru</dt><dd>Resmî ilanda<span class="dh-geri">Tarihi ilandan doğrula</span></dd></div>'
    ogr = [o for o in ((kayit or {}).get('ogrenim') or item.get('ogrenim') or []) if o in ks.LEVELS]
    pt = (kayit or {}).get('puan_turleri') or liste_verisi.puan_turleri(item)
    kpss = ', '.join(pt[:3]) if pt else 'Gerekli' if item.get('kpss') == 'kpss' else 'Gerekmez' if item.get('kpss') == 'kpsssiz' else ''
    yer = ks.yer_metni(item, (kayit or {}).get('il') or '')

    def hucre(dt, dd):
        return f'<div><dt>{dt}</dt><dd{"" if dd else " class=" + chr(34) + "bos" + chr(34)}>{esc(dd) if dd else "İlanda"}</dd></div>'
    bilgi = (f'<dl class="dh-bilgi">{son_html}{hucre("Yer", yer)}'
             f'{hucre("Öğrenim", " / ".join(ks.LEVELS[o] for o in ogr))}{hucre("KPSS", kpss)}</dl>')
    ust = f'<div class="dh-ust">{pill_html}</div>' if pill_html else ''
    return (f'<section class="dh{"" if afis else " afissiz"}" aria-labelledby="dh-baslik">'
            f'<div class="dh-ana">{kurum}<div class="dh-baslik">{ust}'
            f'<h1 id="dh-baslik">{esc(h1)}</h1></div></div>{afis}{bilgi}</section>')


def _tarih_yazi(d):
    import kurum_sayfasi as ks
    d = d.astimezone(TR)
    return f'{d.day} {ks.AY[d.month - 1]} {d.year}'


def _arama_metinleri(item, alanlar, end, kayit, yedek):
    """(title, description): Google'da aranan biçim — 'Kurum Unvan Alımı 2026', açıklamada son başvuru, yer, öğrenim, KPSS."""
    import kurum_sayfasi as ks
    import liste_verisi
    kurum = ks.kurum_adi(item.get('kurum')) if (item.get('kurum') or '').strip() else ''
    manset = liste_verisi.baslik_temiz(alanlar.get('manset') or '').strip()
    ilan_sozu = bool(re.search(r'al[ıi]m|ilan|s[ıi]nav|duyuru|temin', ks.kurum_anahtari(manset)))
    if not (kurum and manset):
        baslik = yedek
    else:
        yil = '' if re.search(r'\b20\d\d\b', manset) else f' {(end or datetime.now(TR)).astimezone(TR).year}'
        baslik = f'{kurum} {manset}{"" if ilan_sozu else " Alımı"}{yil}'
    parcalar = [f'{kurum + " " if kurum else ""}{manset or yedek}{"" if ilan_sozu or not manset else " alım ilanı"}'.strip()]
    if end:
        parcalar.append('Son başvuru: ' + _tarih_yazi(end))
    yer = ks.yer_metni(item, (kayit or {}).get('il') or '')
    if yer:
        parcalar.append('Yer: ' + yer)
    ogr = [ks.LEVELS[o] for o in ((kayit or {}).get('ogrenim') or item.get('ogrenim') or []) if o in ks.LEVELS]
    if ogr:
        parcalar.append('Öğrenim: ' + ', '.join(ogr))
    pt = (kayit or {}).get('puan_turleri') or liste_verisi.puan_turleri(item)
    if pt:
        parcalar.append('KPSS: ' + ', '.join(pt[:3]))
    aciklama = '. '.join(parcalar) + '. Kadrolar, şartlar ve resmî başvuru bağlantısı.'
    return f'{baslik} | KPSS Tercihi', (aciklama if len(aciklama) <= 300 else aciklama[:297].rsplit(' ', 1)[0] + '…')


def _ld(veri):
    return ('<script type="application/ld+json">' + json.dumps(veri, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e')
            + '</script>')


def yapisal_veri(item, canonical, end, alanlar, kayit, gorsel, simdi, is_ilani):
    """Kırıntı (BreadcrumbList) her ilanda; JobPosting yalnız başvurusu açık, son tarihi belli, esas kayıtta (Google İş İlanları).
    Süresi dolan ilan sayfası her derlemede yeniden yazıldığı için JobPosting kendiliğinden kalkar."""
    import kurum_sayfasi as ks
    kirinti = [{'@type': 'ListItem', 'position': 1, 'name': 'Ana sayfa', 'item': BASE},
               {'@type': 'ListItem', 'position': 2, 'name': 'İlanlar', 'item': BASE + '#ilanlar'}]
    kurum = ks.kurum_adi(item.get('kurum')) if (item.get('kurum') or '').strip() else ''
    if kurum:
        slug = (gorsel or {}).get('kurum_slug') or ks.kurum_slug(item['kurum'])
        kirinti.append({'@type': 'ListItem', 'position': 3, 'name': kurum, 'item': BASE + 'kurum/' + slug + '/'})
    kirinti.append({'@type': 'ListItem', 'position': len(kirinti) + 1, 'name': item.get('baslik') or 'İlan', 'item': canonical})
    sonuc = _ld({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': kirinti})
    if not (is_ilani and kurum and end and end > simdi):
        return sonuc
    metin = [item.get('kadro'), item.get('ozet'), item.get('basvuru_notu')]
    metin += [f'{s.get("kadro")}: {s.get("metin")}' for s in item.get('sartlar') or [] if isinstance(s, dict) and s.get('metin')][:5]
    aciklama = ''.join(f'<p>{esc(m)}</p>' for m in dict.fromkeys(m for m in metin if m))
    if len(aciklama) < 60:
        aciklama += f'<p>{esc(kurum)} tarafından yayımlanan kamu personel alım ilanı. Başvuru şartları ve kadrolar resmî ilandadır.</p>'
    yayim = item.get('baslangic_zaman') or item.get('ilk_gorulme') or simdi.isoformat()
    try:
        yayim = min(datetime.fromisoformat(yayim), simdi).astimezone(TR).date().isoformat()
    except ValueError:
        yayim = simdi.date().isoformat()
    adres = {'@type': 'PostalAddress', 'addressCountry': 'TR'}
    il = (kayit or {}).get('il') or ''
    if il:
        adres['addressRegion'] = il
    import liste_verisi
    unvan = re.sub(r'^\d+\s+', '', liste_verisi.baslik_temiz(alanlar.get('manset') or '')).strip()
    is_ = {'@context': 'https://schema.org', '@type': 'JobPosting', 'title': unvan or item.get('baslik'),
           'description': aciklama, 'datePosted': yayim, 'validThrough': end.isoformat(timespec='seconds'),
           'employmentType': 'FULL_TIME', 'directApply': False, 'url': canonical,
           'hiringOrganization': {'@type': 'Organization', 'name': kurum},
           'jobLocation': {'@type': 'Place', 'address': adres},
           'identifier': {'@type': 'PropertyValue', 'name': 'KPSS Tercihi', 'value': item.get('id') or canonical}}
    if (gorsel or {}).get('logo'):
        is_['hiringOrganization']['logo'] = BASE + gorsel['logo']
    if alanlar.get('toplam'):
        is_['totalJobOpenings'] = alanlar['toplam']
    return sonuc + _ld(is_)


def detail_page(item, gorsel=None, kayit=None, benzer=None, simdi=None, kopya=None):
    from siniflandir import akademik_ilan
    if akademik_ilan(item):
        return None  # akademik ilanlar sitede gösterilmez
    url = urlparse(item.get('link', ''))
    key = parse_qs(url.query).get('i', [''])[0]
    import uuid
    try:
        key = str(uuid.UUID(key))
    except ValueError:
        key = item.get('id', '')
        if not re.fullmatch(r'(?:(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})', key):
            return None
    if url.scheme != 'https' or url.hostname not in {'kariyerkapisi.gov.tr','kamuilan.sbb.gov.tr','www.iskur.gov.tr','iskur.gov.tr','yerelyonetimler.csb.gov.tr'} or url.username or url.password:
        return None
    import kurum_sayfasi as ks
    import liste_verisi
    item = liste_verisi.donem_tamamla(item)
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    canonical = BASE + 'ilan/' + key + '/'
    title = item.get('baslik', 'Kamu ilanı')
    deadline = item.get('son_zaman') or item.get('son_tarih')
    end = datetime.fromisoformat(deadline) if deadline else None
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=TR, hour=23, minute=59, second=59)
    kapali = bool(end and end <= simdi)
    acik_ilan = not (item.get('iptal_edildi') or item.get('duyuru_turu') or kapali)
    date = end.astimezone(TR).strftime('%d.%m.%Y · %H:%M' if item.get('son_zaman') else '%d.%m.%Y') if end else 'Belirtilmemiş'
    if kayit is None:
        try:
            kayit = liste_verisi.kayit(item, gorsel, {}, simdi)
        except Exception:
            kayit = None
    gorsel = gorsel or {}
    alanlar = ks.kart_alanlari(item)
    h1 = liste_verisi.baslik_temiz(alanlar['manset'])
    kopya_ust, kopya_alt = _kopya_notlari(kopya)
    # --- içerik bölümleri
    sections = ''
    if item.get('iptal_edildi'):
        sections += '<p class="not uyari"><strong>İptal edildi.</strong> Bu ilan için resmî iptal duyurusu yayımlandı. Başvuru yapmadan önce resmî kaynağı kontrol et.</p>'
    from sbb_detay import document_url
    pdf_satirlari = _pdf_kadrolari(item)
    kk_kadrolar = [] if pdf_satirlari else [k for k in item.get('kadro_detay') or [] if isinstance(k, dict) and k.get('unvan')]
    sart_bolumleri = () if pdf_satirlari or kk_kadrolar else _pdf_sart_bolumleri(item)
    if pdf_satirlari:
        tablo = _kadro_kartlari(item, pdf_satirlari, document_url(item))
    elif kk_kadrolar:
        tablo = _kk_kadro_kartlari(kk_kadrolar, document_url(item) or item.get('link'))
    elif sart_bolumleri:
        tablo = _kadro_tablosu(item, kosulsuz=True) + _sart_bolumleri_html(sart_bolumleri, document_url(item))
    else:
        tablo = _kadro_tablosu(item)
    if (pdf_satirlari or kk_kadrolar) and item.get('ozet'):  # kartlar özetin üstünde: "koşullar aşağıda gösterilmiştir" cümlesi yanıltır
        item = dict(item, ozet=item['ozet'].replace(' Kadroya göre değişen eğitim ve deneyim koşulları aşağıda ayrı olarak gösterilmiştir.', ''))
    bolum = ''
    if tablo:
        bolum += tablo
    elif item.get('kadro'):
        bolum += f'<h2>Kadro ve kontenjan</h2><p>{esc(item["kadro"])}</p>'
    diger = ''
    from basvuru_penceresi import asama_yazisi
    if item.get('basvuru_asamalari') and asama_yazisi(item['basvuru_asamalari']):
        diger += f'<h3>Başvuru aşamaları</h3><p>{esc(asama_yazisi(item["basvuru_asamalari"]))}</p>'
    for heading, value in [('Duyuru metni', item.get('duyuru_cumlesi')), ('İlan özeti', None if item.get('ozet') == item.get('duyuru_cumlesi') else item.get('ozet')), ('Başvuru notu', item.get('basvuru_notu'))]:
        if value:
            diger += f'<h3>{heading}</h3><p>{esc(value)}</p>'
    if not any(item.get(k) for k in ('kadro', 'duyuru_cumlesi', 'ozet', 'basvuru_notu', 'sartlar')):
        diger += '<p class="muted">Bu ilanın kadro, şart ve başvuru ayrıntıları henüz kaynaktan okunamadı. Tüm bilgiler için resmî ilan belgesini aç.</p>'
    for belge in item.get('belgeler', [])[:3]:
        if str(belge.get('link', '')).startswith('https://webdosya.csb.gov.tr/v2/yerelyonetimler/'):
            diger += f'<p><a class="yazi-link" href="{esc(belge["link"])}" target="_blank" rel="noopener noreferrer">Duyuru eki: {esc(belge.get("ad"))} ↗</a></p>'
    ikincil = (kopya or {}).get('rol') == 'ikincil'
    if ikincil:   # başka kaynaktaki kopya: Google tek sayfayı (esas kaydı) dizinler
        canonical = BASE + 'ilan/' + kopya['birincil'] + '/'
    title, description = _arama_metinleri(item, alanlar, end, kayit, title)
    og_gorsel = ''
    if gorsel.get('kart'):
        kart_url = esc(BASE + gorsel['kart'])
        og_gorsel = f'<meta property="og:image" content="{kart_url}"><meta property="og:image:width" content="{KART_GENISLIK}"><meta property="og:image:height" content="{gorsel.get("kart_yukseklik", 900)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{kart_url}">'
    kurum_kirinti = _kurum_bloklari(item, gorsel, '')[1]
    from sbb_detay import document_url
    document = document_url(item)
    target = document or item['link']
    button = 'İlan belgesini aç (PDF) ↗' if document else 'Resmî ilana git · Başvur ↗' if acik_ilan else 'Resmî duyuruyu aç ↗' if item.get('duyuru_turu') else 'Resmî ilanı aç ↗'
    if document:
        diger += f'<p class="muted">{esc(item.get("belge_aciklamasi"))}</p>'
    kurum_ici_not = '<p class="not kopya-not"><strong>Kurum içi yeterlik sınavı;</strong> açıktan başvuruya açık değil.</p>' if (kayit or {}).get('kurum_ici') else ''
    kayit_id = esc(item.get('id') or key)
    ikincil_veri = f' data-ikincil="{esc(",".join((kopya or {}).get("ikincil_idler") or []))}"' if (kopya or {}).get('ikincil_idler') else ''
    from kurum_sayfasi import BOOKMARK
    cta = (f'<div class="d-cta"><a class="btn btn-ana btn-buyuk" href="{esc(target)}" target="_blank" rel="noopener noreferrer" data-a="resmi_ilan" data-a-h="{esc(key)}">{button}</a>'
           f'<button type="button" class="btn btn-ikinci btn-buyuk" id="kaydet-btn" data-kaydet="{kayit_id}"{ikincil_veri} data-ad="{esc(h1)}" aria-pressed="false">{BOOKMARK}<span data-yazi>Kaydet</span></button></div>')
    benzer_html = ''
    if benzer:
        benzer_html = ('<section class="benzer"><div class="bolum-bas"><h2>Benzer ilanlar</h2></div><div class="liste">'
                       + ''.join(ks.satir_html(k, simdi, '../../') for k in benzer[:5]) + '</div></section>')
    kok = '../../'
    is_ilani = acik_ilan and not ikincil and not (kayit or {}).get('kurum_ici')
    og_gorsel += yapisal_veri(item, canonical, end, alanlar, kayit, gorsel, simdi, is_ilani)
    govde = (f'<main id="icerik" class="wrap"><article class="d-bas"><nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}#ilanlar">İlanlar</a>{kurum_kirinti}</nav>'
             f'{hero_html(item, gorsel, kayit, simdi)}{kurum_ici_not}{kopya_ust}{cta}{kopya_alt}</article>'
             f'<div class="d-ana"><section class="d-bolum">{sections}{bolum}{diger}</section>{benzer_html}</div></main>')
    return key, (sayfa_basi(title, description, canonical, kok, 'article', og_gorsel, og_baslik=title)
                 + f'<body class="detail-page"><a class="skip" href="#icerik">İçeriğe geç</a>{ust_html(kok)}{govde}{alt_html(kok)}</body></html>')


def kurum_ici_sayfasi(item):
    """Kanalda zaten paylaşılmış kurum içi ilanın bağlantısı 404 vermesin: kısa, aranamaz (noindex) sayfa. (anahtar, html)."""
    from ilan_baglanti import ilan_anahtari
    key = ilan_anahtari(item)
    kok = '../../'
    baslik = 'Kurum içi ilan'
    govde = (f'<main id="icerik" class="wrap"><article class="d-bas"><h1>{esc(baslik)}</h1>'
             '<p class="not kopya-not"><strong>Bu ilan yalnız kurum personeline yöneliktir.</strong> Açıktan başvuruya açık değildir; sitede listelenmez.</p>'
             f'<p><a class="yazi-link" href="{kok}">Ana sayfaya dön →</a></p></article></main>')
    return key, (sayfa_basi(baslik + ' | KPSS Tercihi', 'Bu ilan yalnız kurum personeline yöneliktir.', BASE + 'ilan/' + key + '/', kok,
                            ek_head='<meta name="robots" content="noindex,nofollow">')
                 + f'<body class="detail-page"><a class="skip" href="#icerik">İçeriğe geç</a>{ust_html(kok)}{govde}{alt_html(kok)}</body></html>')


def kucuk_ad(metin):
    from siniflandir import kucuk
    return kucuk(' '.join(str(metin or '').split()))


AKRONIMLER = {'BDDK', 'SPK', 'SEDDK', 'İETT', 'TGA', 'VHKİ', 'TKGM', 'GSB', 'TTK', 'MSB', 'MEB', 'SGK', 'DSİ', 'TÜBİTAK', 'TÜİK', 'AFAD', 'DMKA', 'TİBU', 'EGO', 'İSKİ', 'TRT', 'KPSS', 'ALES', 'YDS'}


def _duzgun(metin):
    """portal.js proper(): Türkçe kurallarıyla küçült, kelime başlarını büyüt."""
    import re
    kucuk = str(metin or '').replace('I', 'ı').replace('İ', 'i').lower()
    buyut = lambda h: 'İ' if h == 'i' else 'I' if h == 'ı' else h.upper()
    sonuc = re.sub(r'(^|[\s(/-])([a-zçğıöşü])', lambda m: m.group(1) + buyut(m.group(2)), kucuk)
    sonuc = re.sub(r'(?<=\S )(Ve|İle|Veya)(?= )', lambda m: 'ile' if m.group(1) == 'İle' else m.group(1).lower(), sonuc)
    # Büyük harfle yazılmış bilinen kısaltmalar korunur (BDDK, SPK, İETT…)
    ilk = {w for w in re.findall(r'[\wçğıöşüÇĞİÖŞÜ]+', str(metin or '')) if w in AKRONIMLER}
    if ilk:
        kat = lambda s: s.replace('I', 'ı').replace('İ', 'i').lower()
        harita = {kat(w): w for w in ilk}
        sonuc = re.sub(r'[\wçğıöşüÇĞİÖŞÜ]+', lambda m: harita.get(kat(m.group()), m.group()), sonuc)
    return re.sub(r'\b4/b\b', '4/B', re.sub(r'\bkpss\b', 'KPSS', sonuc, flags=re.I), flags=re.I)


def _gorunen_baslik(item):
    """portal.js title(): baştaki kurum adını at, düzgün yaz."""
    import re
    baslik, kurum = str(item.get('baslik') or 'Kamu ilanı'), str(item.get('kurum') or '')
    if kurum and _duzgun(baslik).startswith(_duzgun(kurum)) and len(baslik) > len(kurum):
        baslik = re.sub(r'^\s*[-–:]\s*', '', baslik[len(kurum):])
    return _duzgun(baslik)


def _ton(kurum):
    """portal.js hue() ile aynı: kurum adından sabit renk tonu."""
    h = 0
    for c in str(kurum or ''):
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h % 360


def _bas_harfler(kurum):
    kelimeler = [k for k in str(kurum or '').split() if k[:1].isalpha()][:2]
    return ''.join(k[0] for k in kelimeler).replace('i', 'İ').upper() or 'K'


def _bitis(item):
    deadline = item.get('son_zaman') or item.get('son_tarih')
    if not deadline:
        return None
    try:
        end = datetime.fromisoformat(deadline)
    except ValueError:
        return None
    if end.tzinfo is None:
        end = end.replace(tzinfo=TR, hour=23, minute=59, second=59)
    return end


def bot_ilani(item):
    """Kişisel bildirim botu için ilanın kısa kaydı."""
    from siniflandir import kucuk
    kimlik = item.get('id')
    kimlikler = sorted({k for k in [*item.get('kaynak_kimlikleri', []), kimlik] if k})
    sayfa = detail_page(item)
    parcalar = [item.get('baslik'), item.get('kurum'), item.get('kadro'), item.get('ozet'), item.get('duyuru_cumlesi')]
    parcalar +=[str(s.get(alan) or '') for s in item.get('sartlar', []) for alan in ('kadro', 'metin')]
    metin = kucuk(' '.join(str(p) for p in parcalar if p))[:1500]
    return {
        'id': kimlik, 'kimlikler': kimlikler, 'baslik': item.get('baslik'), 'kurum': item.get('kurum'),
        'son_tarih': item.get('son_tarih'), 'son_zaman': item.get('son_zaman'),
        'ogrenim': item.get('ogrenim', []), 'iller': item.get('iller', []),
        'kategori': item.get('kategori'), 'kpss': item.get('kpss'), 'duyuru_turu': item.get('duyuru_turu'),
        'sayfa': BASE + 'ilan/' + sayfa[0] + '/' if sayfa else item.get('link'), 'metin': metin,
    }


def bot_ilanlari(ilanlar, simdi=None):
    """Süresi geçmemiş (ya da tarihsiz) ilanların bot kayıtları."""
    simdi = simdi or datetime.now(TR)
    sonuc = []
    from siniflandir import akademik_ilan
    for item in ilanlar:
        if akademik_ilan(item) or item.get('iptal_edildi'):
            continue
        bitis = _bitis(item)
        if bitis and bitis <= simdi:
            continue
        sonuc.append(bot_ilani(item))
    return {'guncelleme': simdi.isoformat(timespec='seconds'), 'ilanlar': sonuc}


GUVENLI_KIMLIK = r'(?:(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})'


def _sayfa_anahtari(kimlik):
    """Kimliğin ilan/<anahtar>/ adresi: Kariyer Kapısı bağlantısında UUID, diğer kaynaklarda kimliğin kendisi; güvensizse None."""
    import uuid
    if re.fullmatch(GUVENLI_KIMLIK, kimlik or ''):
        return kimlik
    try:
        return str(uuid.UUID(parse_qs(urlparse(kimlik or '').query).get('i', [''])[0]))
    except ValueError:
        return None


def yonlendirme_sayfasi(hedef):
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>İlan taşındı — KPSS Tercihi</title>'
            f'<meta name="robots" content="noindex"><link rel="canonical" href="{esc(hedef)}">'
            f'<meta http-equiv="refresh" content="0;url={esc(hedef)}"></head>'
            f'<body><p>Bu ilan yeni adresine taşındı: <a href="{esc(hedef)}">{esc(hedef)}</a></p></body></html>')


def yonlendirmeleri_yaz(docs, ilanlar, sayfali):
    """Kaynaklar birleşince kalıcı kimlik değişebilir (ÇŞB -> İŞKUR); eski kimliğin adresi Telegram'da paylaşılmış olabilir.
    Sayfası olan her ilanın takma adlarına, yeni sayfaya yönlendiren küçük bir sayfa yazılır (asıl sayfaların üzerine yazılmaz)."""
    n = 0
    for item in ilanlar:
        asil = _sayfa_anahtari(item.get('id'))
        if asil not in sayfali:
            continue
        for kimlik in item.get('kaynak_kimlikleri') or []:
            eski = _sayfa_anahtari(kimlik)
            if not eski or eski == asil or eski in sayfali:
                continue
            (docs / 'ilan' / eski).mkdir(parents=True, exist_ok=True)
            (docs / 'ilan' / eski / 'index.html').write_text(yonlendirme_sayfasi(BASE + 'ilan/' + asil + '/'), encoding='utf-8')
            n += 1
    print(f'{n} eski ilan bağlantısı yönlendirildi.')


def _sayfayi_kaldir(docs, item):
    """Önceden üretilmiş akademik ilan sayfasını siler (yalnız ilan/<kimlik>/ altında, güvenli kimliklerde)."""
    import re
    import shutil
    for kimlik in {item.get('id', ''), *item.get('kaynak_kimlikleri', [])}:
        if re.fullmatch(r'(?:(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})', kimlik or ''):
            shutil.rmtree(docs / 'ilan' / kimlik, ignore_errors=True)
    kimlik = parse_qs(urlparse(item.get('link', '')).query).get('i', [''])[0]
    try:
        shutil.rmtree(docs / 'ilan' / str(__import__('uuid').UUID(kimlik)), ignore_errors=True)
    except ValueError:
        pass


def _kart_png(item, simdi, logo=None):
    from kart_tasarimlari import ilan_karti
    return ilan_karti(item, logo=logo, simdi=simdi)


LOGO_ONBELLEK_GUN = 30


def _onbellek_yolu(item):
    import hashlib
    from kurum_gorseli import kurum_anahtari
    return ROOT / '.cache' / 'logolar' / (hashlib.sha1(kurum_anahtari(item.get('kurum', '')).encode('utf-8')).hexdigest() + '.png')


def _onbellekte(item):
    try:
        import time
        yol = _onbellek_yolu(item)
        return yol.is_file() and time.time() - yol.stat().st_mtime < LOGO_ONBELLEK_GUN * 86400
    except Exception:
        return False


def _logo_adresi(item):
    """Ağdan indirilecek logo adresi; yoksa/hatalıysa None."""
    try:
        from kurum_gorseli import logo_adresi
        return logo_adresi(item)
    except Exception:
        return None


def _logo_png(item):
    from kurum_gorseli import kurum_logosu
    if _onbellekte(item):
        try:
            return _onbellek_yolu(item).read_bytes()
        except Exception:
            pass
    png = kurum_logosu(item)
    if png and not _logo_yerelde(item):
        try:
            yol = _onbellek_yolu(item)
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_bytes(png)
        except Exception:
            pass
    return png


def _logo_yerelde(item):
    """Logo yerel kütüphanede varsa ağ gerekmez."""
    try:
        from kurum_gorseli import LIBRARY, kurum_anahtari
        manifest = LIBRARY / 'kaynaklar.json'
        return manifest.exists() and kurum_anahtari(item.get('kurum', '')) in json.loads(manifest.read_text(encoding='utf-8'))
    except Exception:
        return False


def _webp_kare(png, boyut=LOGO_BOYUT):
    import io
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        im = im.convert('RGBA')
        im.thumbnail((boyut - 16, boyut - 16), Image.Resampling.LANCZOS)
        zemin = Image.new('RGBA', (boyut, boyut), (255, 255, 255, 255))
        zemin.alpha_composite(im, ((boyut - im.width) // 2, (boyut - im.height) // 2))
        cikti = io.BytesIO()
        zemin.convert('RGB').save(cikti, format='WEBP', quality=88, method=4)
        return cikti.getvalue()


def _kart_webp(png):
    import io
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        im = im.convert('RGB')
        yuk = round(im.height * KART_GENISLIK / im.width)
        im = im.resize((KART_GENISLIK, yuk), Image.Resampling.LANCZOS)
        for kalite in (82, 74, 66, 58):
            cikti = io.BytesIO()
            im.save(cikti, format='WEBP', quality=kalite, method=4)
            if cikti.tell() <= 120_000:
                break
        return cikti.getvalue(), yuk


def gorselleri_uret(ilanlar, docs, simdi=None, en_cok_indirme=EN_COK_LOGO_INDIRME):
    """Süresi geçmemiş her ilan için kart + kurum logosu WebP dosyalarını docs/ilan/{kart,logo}/ altına yazar.
    {anahtar: {'kart':…, 'logo':…, 'kart_yukseklik':…}} döndürür (olmayan alan yazılmaz). Hiçbir hata derlemeyi düşürmez."""
    import hashlib
    import shutil
    from kurum_gorseli import kurum_anahtari
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    kart_klasoru, logo_klasoru = docs / 'ilan' / 'kart', docs / 'ilan' / 'logo'
    for klasor in (kart_klasoru, logo_klasoru):
        shutil.rmtree(klasor, ignore_errors=True)
        klasor.mkdir(parents=True, exist_ok=True)
    sonuc, logolar, indirme, ardisik_hata = {}, {}, 0, 0
    for item in ilanlar:
        try:
            sayfa = detail_page(item)
            if not sayfa or item.get('iptal_edildi'):
                continue
            bitis = _bitis(item)
            if bitis and bitis <= simdi:
                continue
        except Exception:
            continue
        anahtar, girdi, png = sayfa[0], {}, None
        try:
            kurum = kurum_anahtari(item.get('kurum', ''))
            if kurum:
                if kurum not in logolar:
                    yerel = _logo_yerelde(item) or _onbellekte(item)
                    png = None
                    ag = not yerel and _logo_adresi(item) is not None  # yalnızca gerçek indirme denemesi sayılır
                    if yerel or (ag and indirme < en_cok_indirme and ardisik_hata < 8):
                        if ag:
                            indirme += 1
                        png = _logo_png(item)
                        if ag:
                            ardisik_hata = 0 if png else ardisik_hata + 1
                    ad = None
                    if png:
                        ad = hashlib.sha1(kurum.encode('utf-8')).hexdigest()[:12]
                        (logo_klasoru / f'{ad}.webp').write_bytes(_webp_kare(png))
                    logolar[kurum] = (png, f'ilan/logo/{ad}.webp' if ad else None)
                png, yol = logolar[kurum]
                if yol:
                    girdi['logo'] = yol
        except Exception as hata:
            png = None
            print(f'Uyarı: kurum logosu üretilemedi ({item.get("kurum")}): {hata}')
        try:
            kart, yuk = _kart_webp(_kart_png(item, simdi, png))
            (kart_klasoru / f'{anahtar}.webp').write_bytes(kart)
            girdi['kart'] = f'ilan/kart/{anahtar}.webp'
            girdi['kart_yukseklik'] = yuk
        except Exception as hata:
            print(f'Uyarı: ilan kartı üretilemedi ({item.get("id")}): {hata}')
        if girdi:
            sonuc[anahtar] = girdi
    return sonuc

def elle_kurallar():
    """config.json 'elle': {'gizle': [kimlik], 'alanlar': {kimlik: {alan: değer}}} — kullanıcının elle verdiği kararlar."""
    try:
        elle = json.loads((ROOT / 'config.json').read_text(encoding='utf-8')).get('elle') or {}
    except (OSError, ValueError):
        elle = {}
    return set(elle.get('gizle') or []), dict(elle.get('alanlar') or {})


def elle_uygula(ilanlar):
    """Elle gizlenen kayıtlar sitede hiç yer almaz; elle düzeltilen alanlar (örn. yanlış son tarih) kaydın üzerine yazılır."""
    gizle, alanlar = elle_kurallar()
    return [dict(i, **alanlar.get(i.get('id'), {})) for i in ilanlar if i.get('id') not in gizle]


def main():
    docs = ROOT / 'docs'
    data = json.loads((docs / 'ilanlar.json').read_text(encoding='utf-8'))
    try:
        import liste_verisi
        # Yeniden okunmamış kayıtlar için derleme zamanı düzeltmeleri (belge penceresi, SBB belge alanları); ilanlar.json'a yazılmaz.
        data['ilanlar'] = [liste_verisi.tamamla(i) for i in data.get('ilanlar', [])]
    except Exception as hata:
        print(f'Uyarı: kayıtlar derleme zamanında tamamlanamadı: {hata}')
    data['ilanlar'] = elle_uygula(data.get('ilanlar', []))
    urls = [BASE]
    count = 0
    from siniflandir import akademik_ilan
    gorseller = {}
    kopyalar = {}
    try:
        import kopya
        kopyalar = kopya.kopya_bul(data.get('ilanlar', []))
        print(f'{len(kopyalar["kopya_of"])} kopya ilan (kaynaklar arası) birleştirildi.')
        data['ilanlar'] = kopya.birlestir(data.get('ilanlar', []), kopyalar)   # esas kaydın eksikleri kopyalardan
    except Exception as hata:
        print(f'Uyarı: kopya ilanlar bulunamadı: {hata}')
    kimlik_harita = {i.get('id'): i for i in data.get('ilanlar', [])}
    try:
        gorseller = gorselleri_uret(data.get('ilanlar', []), docs, datetime.now(TR))
    except Exception as hata:
        print(f'Uyarı: ilan görselleri üretilemedi: {hata}')
    (docs / 'ilan').mkdir(parents=True, exist_ok=True)
    kurum_adresleri = []
    try:
        import kurum_sayfasi
        sonuc = kurum_sayfasi.kurum_sayfalarini_uret(data.get('ilanlar', []), docs, gorseller, datetime.now(TR), kopyalar)
        kurum_adresleri = sonuc[2]
        for anahtar, alan in kurum_sayfasi.kart_meta(data.get('ilanlar', []), sonuc[3], kopyalar).items():
            gorseller.setdefault(anahtar, {}).update(alan)
    except Exception as hata:
        print(f'Uyarı: kurum sayfaları üretilemedi: {hata}')
    (docs / 'ilan' / 'gorseller.json').write_text(json.dumps(gorseller, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    liste = None
    try:
        import liste_verisi
        liste = liste_verisi.uret(data.get('ilanlar', []), gorseller, docs, datetime.now(TR), data.get('guncelleme'), kopyalar, data.get('kaynak_durumlari'))
    except Exception as hata:
        print(f'::warning::liste.json üretilemedi: {hata}')
    kayitlar = (liste or {}).get('ilanlar') or []
    paylasilan = set(data.get('telegram_gonderilen') or [])
    kayit_haritasi = {k['key']: k for k in kayitlar}
    gorunen = [k for k in kayitlar if not k.get('kopya_of')]
    sayfa_anahtarlari, degisim = set(), {}
    for item in data.get('ilanlar', []):
        result = detail_page(item)
        if not result:
            if akademik_ilan(item):
                _sayfayi_kaldir(docs, item)
                from siniflandir import kurum_ici
                if kurum_ici(item) and {item.get('id'), *item.get('kaynak_kimlikleri', [])} & paylasilan:
                    try:
                        anahtar, icerik_ = kurum_ici_sayfasi(item)   # Telegram'da paylaşılmış bağlantı 404 vermesin
                        (docs / 'ilan' / anahtar).mkdir(parents=True, exist_ok=True)
                        (docs / 'ilan' / anahtar / 'index.html').write_text(icerik_, encoding='utf-8')
                    except Exception as hata:
                        print(f'Uyarı: kurum içi ilan sayfası yazılamadı ({item.get("id")}): {hata}')
            continue
        kayit = kayit_haritasi.get(result[0])
        try:
            benzer = benzer_ilanlar(kayit, gorunen)
        except Exception as hata:
            benzer = []
            print(f'Uyarı: benzer ilanlar bulunamadı ({result[0]}): {hata}')
        try:
            sayfa_kopya = kopya.sayfa_bilgisi(kopyalar, item, kimlik_harita)
        except Exception as hata:
            sayfa_kopya = None
            print(f'Uyarı: kopya notu yazılamadı ({result[0]}): {hata}')
        result = detail_page(item, gorseller.get(result[0]), kayit, benzer, None, sayfa_kopya)
        key, content = result
        folder = docs / 'ilan' / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(content, encoding='utf-8')
        sayfa_anahtarlari.add(key)
        if (sayfa_kopya or {}).get('rol') != 'ikincil':   # kopya sayfası esas kayda kanonik bağlanır, haritaya girmez
            urls.append(BASE + 'ilan/' + key + '/')
            degisim[urls[-1]] = max(str(item.get(a) or '')[:10] for a in ('ilk_gorulme', 'detay_guncelleme', 'guncelleme'))
        count += 1
    try:
        yonlendirmeleri_yaz(docs, data.get('ilanlar', []), sayfa_anahtarlari)
    except Exception as hata:
        print(f'Uyarı: eski ilan bağlantıları yönlendirilemedi: {hata}')
    urls += kurum_adresleri
    try:
        from puan_sayfalari import puan_sayfalarini_uret
        urls += puan_sayfalarini_uret(docs, BASE)
    except Exception as hata:
        print(f'Uyarı: taban puanı sayfaları üretilemedi: {hata}')
    if BASE + 'puanlar/' not in urls:
        urls.insert(1, BASE + 'puanlar/')   # tercih robotu sayfası haritada yoktu
    try:
        import yz_gorunurluk   # yapay zekâ asistanları için düz metin özet (llms.txt) ve SSS sayfası
        sss_url, sss_html = yz_gorunurluk.sss_sayfasi(BASE)
        (docs / 'sss').mkdir(exist_ok=True)
        (docs / 'sss' / 'index.html').write_text(sss_html, encoding='utf-8')
        urls.insert(2, sss_url)
        sayfali = sayfa_anahtarlari
        (docs / 'llms.txt').write_text(yz_gorunurluk.llms_metni(gorunen, BASE, datetime.now(TR), sayfali), encoding='utf-8')
    except Exception as hata:
        print(f'Uyarı: llms.txt / SSS üretilemedi: {hata}')
    bugun = datetime.now(TR).date().isoformat()   # ana sayfa her gün değişir; Google'a tazelik sinyali
    degisim[BASE] = bugun
    (docs / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                      + ''.join('<url><loc>' + esc(u) + '</loc>'
                                                + (f'<lastmod>{degisim[u]}</lastmod>' if re.fullmatch(r'\d{4}-\d{2}-\d{2}', degisim.get(u, '')) else '')
                                                + '</url>' for u in dict.fromkeys(urls))
                                      + '</urlset>\n', encoding='utf-8')
    bot = bot_ilanlari(data.get('ilanlar', []))
    (docs / 'bot-ilanlar.json').write_text(json.dumps(bot, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    try:
        from sosyal_paylasim import uret
        uret(data.get('ilanlar', []), datetime.now(TR), docs, BASE)
    except Exception as hata:
        print(f'Uyarı: sosyal paylaşım içeriği üretilemedi: {hata}')
    print(f'{count} public detail pages and sitemap generated.')


if __name__ == '__main__':
    main()
