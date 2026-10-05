"""Generate crawlable public detail pages from the existing verified registry."""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://enesfeched-maker.github.io/kamu-ilan-takip/'
TR = timezone(timedelta(hours=3))
KART_GENISLIK = 720
LOGO_BOYUT = 128
EN_COK_LOGO_INDIRME = 150
CSS_SURUM = 13
LOGO_SURUM = 2
ACIK_ZEMIN, KOYU_ZEMIN = '#F6F6F1', '#0D0E0C'
# <head> içinde, theme-color etiketinden sonra: açık tema varsayılan, yalnız kit-theme=="dark" koyu açar.
TEMA_BETIGI = ('<script>try{var d=JSON.parse(localStorage.getItem("kit-theme"))==="dark";document.documentElement.dataset.theme=d?"dark":"light";'
               'var m=document.querySelector("meta[name=theme-color]");if(m)m.content=d?"' + KOYU_ZEMIN + '":"' + ACIK_ZEMIN + '"}'
               'catch(e){document.documentElement.dataset.theme="light"}</script>')
AY_IKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>'
TG_IKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 4-18 7.2 6 2.3M21 4l-3 16-8.5-6.5M21 4 9.5 13.5v5.5l3-3.5"/></svg>'
KISI_IKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>'
ALT_MENU = (('Bugün', '#bugun', '<path d="M4 10.5 12 4l8 6.5V20h-5v-6h-6v6H4z"/>'),
            ('İlanlar', '#ilanlar', '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>'),
            ('Takvim', '#takvim', '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'),
            ('Kayıtlı', '#kayitli', '<path d="M7 3.5h10a1 1 0 0 1 1 1V21l-6-4-6 4V4.5a1 1 0 0 1 1-1z"/>'),
            ('Profil', '?profil=1', '<circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/>'))


def esc(value):
    return html.escape(str(value or ''), quote=True)


def ikonlar(kok):
    """Sekme simgesi + iOS ana ekran simgesi + web uygulaması bildirimi."""
    v = LOGO_SURUM
    return (f'<link rel="icon" href="{kok}assets/logo-32.png?v={v}" type="image/png" sizes="32x32">'
            f'<link rel="icon" href="{kok}assets/logo-192.png?v={v}" type="image/png" sizes="192x192">'
            f'<link rel="apple-touch-icon" href="{kok}assets/logo-180.png?v={v}">'
            f'<link rel="manifest" href="{kok}manifest.webmanifest">')


def ust_html(kok, aktif=''):
    """Ana sayfayla aynı üst bar (docs/index.html .ust); bağlantılar `kok` göreli."""
    menu = [('Bugün', f'{kok}#bugun', ''), ('İlanlar', f'{kok}#ilanlar', ''), ('Takvim', f'{kok}#takvim', ''),
            ('Taban puanları', f'{kok}puanlar/', 'puanlar'), ('Rehber', f'{kok}#rehber', '')]
    bagla = ''.join(f'<a href="{h}"{" class=" + chr(34) + "aktif" + chr(34) + " aria-current=" + chr(34) + "page" + chr(34) if a and a == aktif else ""}>{ad}</a>' for ad, h, a in menu)
    return (f'<header class="ust"><div class="wrap ust-ic"><a class="marka" href="{kok}" aria-label="Kamu İlan Takip ana sayfa">'
            f'<img src="{kok}assets/logo-96.webp?v={LOGO_SURUM}" alt="" width="32" height="32">Kamu İlan Takip</a>'
            f'<nav class="menu" aria-label="Ana menü">{bagla}</nav>'
            f'<div class="ust-sag"><button type="button" class="ikon-btn" id="theme" aria-label="Renk temasını değiştir">{AY_IKON}</button>'
            f'<a class="btn btn-tg" href="https://t.me/kamuilantakip" target="_blank" rel="noopener">{TG_IKON}Telegram</a></div></div></header>')


def alt_html(kok, yil=None):
    """Tek satırlık alt bilgi (ana sayfayla aynı) ve mobil alt menü."""
    yil = yil or datetime.now(TR).year
    menu = ''.join(f'<a href="{kok}{h}"><i><svg viewBox="0 0 24 24" aria-hidden="true">{s}</svg></i>{ad}{'<b id="saved-count-m" hidden>0</b>' if h == '#kayitli' else ''}</a>' for ad, h, s in ALT_MENU)
    return (f'<footer class="alt-bilgi"><div class="wrap"><div><a href="{kok}#bilgi/hakkimizda">Hakkımızda ve veri kaynakları</a><a href="{kok}#bilgi/gizlilik">Gizlilik</a>'
            f'<a href="{kok}#bilgi/reklam">Reklam</a><a href="https://t.me/kamuilantakip" target="_blank" rel="noopener">Telegram</a></div>'
            f'<span>© <span id="yil">{yil}</span> Kamu İlan Takip · Bağımsız ilan rehberi · Başvurular resmî ilan üzerinden yapılır.</span></div></footer>'
            f'<nav class="alt-menu" aria-label="Alt menü">{menu}</nav>')


def sayfa_basi(baslik, aciklama, canonical, kok, og_tur='website', ek_head='', og_baslik=None):
    """<!doctype> … <body> açılışına kadar ortak kısım (kurum ve ilan sayfaları)."""
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="theme-color" content="{ACIK_ZEMIN}"><meta name="color-scheme" content="light dark">{TEMA_BETIGI}'
            f'<title>{esc(baslik)}</title><meta name="description" content="{esc(aciklama)}"><link rel="canonical" href="{canonical}">'
            f'<meta property="og:title" content="{esc(og_baslik or baslik)}"><meta property="og:description" content="{esc(aciklama)}"><meta property="og:type" content="{og_tur}">{ek_head}'
            f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap">'
            f'<link rel="stylesheet" href="{kok}sayfa.css?v={CSS_SURUM}">{ikonlar(kok)}<script src="{kok}sayfa.js?v={CSS_SURUM}" defer></script></head>')


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


def _kadro_tablosu(item):
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
            metin = sartlar[secilen].get('metin') or ''
        satirlar.append((ad, adet, metin))
    kalan = [s for n, s in enumerate(sartlar) if n not in kullanilan]
    html_ = ''
    if satirlar:
        kosullu = any(m for _, _, m in satirlar)
        govde = ''.join(
            f'<tr><td>{esc(ad)}</td><td class="sayi" data-et="Kontenjan">{esc(ks.SAYI_YAZ(adet) if adet else "—")}</td>'
            + (f'<td data-et="Koşullar">{esc(metin) if metin else "Resmî ilandan kontrol et"}</td>' if kosullu else '') + '</tr>'
            for ad, adet, metin in satirlar)
        baslik = '<th scope="col">Kadro</th><th scope="col" class="sayi">Kontenjan</th>' + ('<th scope="col">Başvuru koşulları</th>' if kosullu else '')
        html_ += (f'<h2>{"Kadro ve başvuru koşulları" if kosullu else "Kadro ve kontenjan"}</h2>'
                  f'<div class="tablo-kap"><table class="ktablo"><thead><tr>{baslik}</tr></thead><tbody>{govde}</tbody></table></div>')
    if kalan:
        govde = ''.join(f'<tr><td>{esc(s.get("kadro") or "Genel")}</td><td>{esc(s.get("metin") or "")}</td></tr>' for s in kalan)
        html_ += (f'<h{"3" if satirlar else "2"} class="alt-h">Başvuru koşullarından seçmeler</h{"3" if satirlar else "2"}>'
                  f'<div class="tablo-kap"><table class="ktablo"><thead><tr><th scope="col">Konu</th><th scope="col">Koşul</th></tr></thead><tbody>{govde}</tbody></table></div>')
    return html_

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


def _senin_icin(item, kayit):
    """"Senin için" kutusu: öğrenim/puan türü/il eşleşmesi tarayıcıda kit-profil ile doldurulur (sayfa.js);
    taban referansı derleme zamanında yazılır."""
    kayit = kayit or {}
    ref = kayit.get('taban_ref') or {}
    from kurum_sayfasi import LEVELS
    satirlar = ''
    for duzey, r in ref.items():
        if duzey in LEVELS and isinstance(r.get('medyan'), (int, float)):
            donem = f' · {esc(r["donem"])}' if r.get('donem') else ''
            satirlar += f'<li>{LEVELS[duzey]}: benzer kadroların taban puanı medyanı <b>{_virgul(r["medyan"])}</b> ({int(r.get("n") or 0)} kayıt{donem})</li>'
    ref_html = (f'<ul class="senin-ref">{satirlar}</ul><p class="senin-not">Geçmiş yerleştirmelerden referans; bu ilanın şartı değildir.</p>') if satirlar else ''
    import liste_verisi
    ki = (' data-kurum-ici="1"' if kayit.get('kurum_ici') else '') + (' data-bolum="1"' if kayit.get('bolum_kisiti') else '')
    veri = (f' data-ogr="{esc(",".join(kayit.get("ogrenim") or []))}" data-pt="{esc(",".join(kayit.get("puan_turleri") or []))}"'
            f' data-il="{esc(kayit.get("il") or "")}" data-iller="{esc(",".join(liste_verisi._etkin_iller(kayit)))}"'
            f'{ki} data-ref="{esc(json.dumps(ref, ensure_ascii=False, separators=(",", ":")))}"')
    return (f'<section class="senin" id="senin"{veri}><h2><i>{KISI_IKON}</i>Senin için</h2>'
            '<div data-profil data-ana="../../?profil=1"><p class="senin-link">Öğrenim düzeyini, KPSS puanını ve illerini ana sayfada ekle; bu ilana uyup uymadığını burada göster. '
            '<a href="../../?profil=1">Profilini oluştur →</a></p></div>' + ref_html + '</section>')


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
    alt = liste_verisi.baslik_temiz(_gorunen_baslik(item).strip())
    sayisiz = lambda s: kucuk_ad(re.sub(r'^\d+\s+', '', s))
    alt_html = (f'<p class="d-alt">{esc(alt)}</p>'
                if alt and sayisiz(alt) not in (sayisiz(h1), sayisiz(alanlar['manset'])) else '')
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
        img = f'<img src="{kok}assets/meslek/{esc(foto)}" alt="" width="232" height="232" decoding="async">' if foto else ''
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
    return (f'<section class="dh{"" if afis else " afissiz"}" aria-labelledby="dh-baslik">'
            f'<div class="dh-ana">{kurum}<div class="dh-baslik"><div class="dh-ust"><span class="eyebrow">{esc(item.get("ilan_turu") or "Kamu ilanı")}</span>{pill_html}</div>'
            f'<h1 id="dh-baslik">{esc(h1)}</h1>{alt_html}</div></div>{afis}{bilgi}</section>')


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
    date = end.astimezone(TR).strftime('%d.%m.%Y · %H:%M TSİ' if item.get('son_zaman') else '%d.%m.%Y') if end else 'Belirtilmemiş'
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
    tablo = _kadro_tablosu(item)
    bolum = ''
    if tablo:
        bolum += tablo
    elif item.get('kadro'):
        bolum += f'<h2>Kadro ve kontenjan</h2><p>{esc(item["kadro"])}</p>'
    diger = ''
    for heading, value in [('Duyuru metni', item.get('duyuru_cumlesi')), ('İlan özeti', None if item.get('ozet') == item.get('duyuru_cumlesi') else item.get('ozet')), ('Başvuru notu', item.get('basvuru_notu'))]:
        if value:
            diger += f'<h3>{heading}</h3><p>{esc(value)}</p>'
    if any(item.get(k) for k in ('kadro', 'duyuru_cumlesi', 'ozet', 'basvuru_notu', 'sartlar')):
        diger += '<p class="muted">Seçilmiş alıntılardır. Tüm koşullar, kadrolar ve güncel tarihler için resmî ilanı incele.</p>'
    else:
        diger += '<p class="muted">Bu ilanın kadro, şart ve başvuru ayrıntıları henüz kaynaktan okunamadı. Tüm bilgiler için resmî ilan belgesini aç.</p>'
    for belge in item.get('belgeler', [])[:3]:
        if str(belge.get('link', '')).startswith('https://webdosya.csb.gov.tr/v2/yerelyonetimler/'):
            diger += f'<p><a class="yazi-link" href="{esc(belge["link"])}" target="_blank" rel="noopener noreferrer">Duyuru eki: {esc(belge.get("ad"))} ↗</a></p>'
    description = (item.get('kurum', '') + ' — ' + (item.get('kadro') or title))[:190]
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
    cta = (f'<div class="d-cta"><a class="btn btn-ana btn-buyuk" href="{esc(target)}" target="_blank" rel="noopener noreferrer">{button}</a>'
           f'<button type="button" class="btn btn-ikinci btn-buyuk" id="kaydet-btn" data-kaydet="{kayit_id}"{ikincil_veri} data-ad="{esc(h1)}" aria-pressed="false">{BOOKMARK}<span data-yazi>Kaydet</span></button></div>'
           '<p class="d-cta-not">Başvuru bu sitede yapılmaz; işlemini ilanda belirtilen resmî kanaldan tamamla. Kaydetmek başvuru oluşturmaz.</p>')
    senin = _senin_icin(item, kayit) if acik_ilan else ''
    benzer_html = ''
    if benzer:
        benzer_html = ('<section class="benzer"><div class="bolum-bas"><h2>Benzer ilanlar</h2></div><div class="liste">'
                       + ''.join(ks.satir_html(k, simdi, '../../') for k in benzer[:5]) + '</div></section>')
    kok = '../../'
    govde = (f'<main id="icerik" class="wrap"><article class="d-bas"><nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}#ilanlar">İlanlar</a>{kurum_kirinti}</nav>'
             f'{hero_html(item, gorsel, kayit, simdi)}{kurum_ici_not}{kopya_ust}{cta}{kopya_alt}</article>'
             f'<div class="d-ana">{senin}<section class="d-bolum">{sections}{bolum}{diger}'
             f'<p class="muted d-son">Ayrıntı kontrolü: {esc(item.get("detay_guncelleme", "Tarih belirtilmemiş"))}</p></section>{benzer_html}</div></main>')
    return key, (sayfa_basi(f'{title} | Kamu İlan Takip', description, canonical, kok, 'article', og_gorsel, og_baslik=title)
                 + f'<body class="detail-page"><a class="skip" href="#icerik">İçeriğe geç</a>{ust_html(kok)}{govde}{alt_html(kok)}'
                   '<noscript><div class="not wrap">Bazı özellikler (kaydetme, kalan gün, “Senin için”) için JavaScript gerekir.</div></noscript></body></html>')


def kurum_ici_sayfasi(item):
    """Kanalda zaten paylaşılmış kurum içi ilanın bağlantısı 404 vermesin: kısa, aranamaz (noindex) sayfa. (anahtar, html)."""
    from ilan_baglanti import ilan_anahtari
    key = ilan_anahtari(item)
    kok = '../../'
    baslik = 'Kurum içi ilan'
    govde = (f'<main id="icerik" class="wrap"><article class="d-bas"><h1>{esc(baslik)}</h1>'
             '<p class="not kopya-not"><strong>Bu ilan yalnız kurum personeline yöneliktir.</strong> Açıktan başvuruya açık değildir; sitede listelenmez.</p>'
             f'<p><a class="yazi-link" href="{kok}">Ana sayfaya dön →</a></p></article></main>')
    return key, (sayfa_basi(baslik + ' | Kamu İlan Takip', 'Bu ilan yalnız kurum personeline yöneliktir.', BASE + 'ilan/' + key + '/', kok,
                            ek_head='<meta name="robots" content="noindex,nofollow">')
                 + f'<body class="detail-page"><a class="skip" href="#icerik">İçeriğe geç</a>{ust_html(kok)}{govde}{alt_html(kok)}</body></html>')


def kucuk_ad(metin):
    from siniflandir import kucuk
    return kucuk(' '.join(str(metin or '').split()))


def _duzgun(metin):
    """portal.js proper(): Türkçe kurallarıyla küçült, kelime başlarını büyüt."""
    import re
    kucuk = str(metin or '').replace('I', 'ı').replace('İ', 'i').lower()
    buyut = lambda h: 'İ' if h == 'i' else 'I' if h == 'ı' else h.upper()
    sonuc = re.sub(r'(^|[\s(/-])([a-zçğıöşü])', lambda m: m.group(1) + buyut(m.group(2)), kucuk)
    sonuc = re.sub(r'(?<=\S )(Ve|İle|Veya)(?= )', lambda m: 'ile' if m.group(1) == 'İle' else m.group(1).lower(), sonuc)
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

def main():
    docs = ROOT / 'docs'
    data = json.loads((docs / 'ilanlar.json').read_text(encoding='utf-8'))
    try:
        import liste_verisi
        # Yeniden okunmamış kayıtlar için derleme zamanı düzeltmeleri (belge penceresi, SBB belge alanları); ilanlar.json'a yazılmaz.
        data['ilanlar'] = [liste_verisi.tamamla(i) for i in data.get('ilanlar', [])]
    except Exception as hata:
        print(f'Uyarı: kayıtlar derleme zamanında tamamlanamadı: {hata}')
    urls = [BASE]
    count = 0
    from siniflandir import akademik_ilan
    gorseller = {}
    kopyalar = {}
    try:
        import kopya
        kopyalar = kopya.kopya_bul(data.get('ilanlar', []))
        print(f'{len(kopyalar["kopya_of"])} kopya ilan (kaynaklar arası) birleştirildi.')
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
        urls.append(BASE + 'ilan/' + key + '/')
        count += 1
    urls += kurum_adresleri
    (docs / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+esc(u)+'</loc></url>' for u in urls)+'</urlset>\n', encoding='utf-8')
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
