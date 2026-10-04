"""Kurum sayfaları (docs/kurum/<slug>/) ve liste kartı için ortak, derleme zamanı hesaplanan alanlar.

Kurum adı kanonikleştirme, slug, kadro başlığı (manşet), meslek fotoğrafı seçimi ve sunucu tarafı Vitrin kartı burada.
Tarayıcıdaki karşılığı docs/portal.js card() işlevidir; sınıf adları ikisinde de aynıdır."""
import json
import re
import shutil
import uuid
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from kurum_gorseli import kurum_anahtari
from meslek_gorseli import meslekler, meslek_no, FOTO_KLASORU
from siniflandir import akademik_ilan, kucuk, ILLER

TR = timezone(timedelta(hours=3))
AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
LEVELS = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
SON_EK = re.compile(r'\s+(?:alacak|alınacak|alinacak|temin edecektir|alımı|alimi)\s*$', re.I)
IL_ANAHTAR = {kurum_anahtari(il) for il in ILLER}
IL_ADI = {kurum_anahtari(il): il for il in ILLER}
ACIK = ('ok', 'soon', 'urgent', 'today', 'none', 'upcoming')
BOOKMARK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg>'


def _su():
    import site_uret
    return site_uret


def esc(v):
    return _su().esc(v)


# ------------------------------------------------------------------ kurum adı / slug
def kurum_adi(k):
    """Görünen kurum adı: Türkçe düzgün yazım, 've/ile/veya' küçük, parantezli kısaltmalar (SEDDK) büyük."""
    s = _su()._duzgun(k)
    for kis in re.findall(r'\(([A-ZÇĞİÖŞÜ0-9]{2,8})\)', k or ''):
        s = re.sub(r'\(' + re.escape(_su()._duzgun(kis)) + r'\)', f'({kis})', s)
    return s


def _belediye_parcalar(k):
    """Belediye değilse None; değilse (il önekisiz/ilsiz kanonik ad, addan çıkan il anahtarı | None)."""
    s = kurum_anahtari(k or '')
    if not s.endswith(' belediye'):
        return None
    w = s[:-len(' belediye')].split()
    il = None
    if len(w) >= 2 and w[0] in IL_ANAHTAR and w[1:] != ['buyuksehir']:
        il, w = w[0], w[1:]
    elif len(w) >= 2 and w[-1] in IL_ANAHTAR:
        il, w = w[-1], w[:-1]
    return ' '.join(w) + ' belediye', il


def kurum_kanonik(k):
    """kurum_anahtari + belediyelerde il önekini/parantezli ili atar: 'Kırşehir Mucur Belediyesi',
    'MUCUR BELEDİYE BAŞKANLIĞI' ve 'Mucur (Kırşehir) Belediye Başkanlığı' -> 'mucur belediye'.
    Büyükşehir ve il belediyeleri ('rize belediye', 'ankara buyuksehir belediye') korunur.
    Aynı adlı farklı il belediyeleri kurum_gruplari() içinde il ile ayrılır."""
    p = _belediye_parcalar(k)
    return p[0] if p else kurum_anahtari(k or '')


def _ilan_ili(item):
    """Belediye kaydının ili: addaki il, yoksa kayıttaki tek il; bilinmiyorsa None."""
    p = _belediye_parcalar(item.get('kurum'))
    if p and p[1]:
        return p[1]
    iller = item.get('iller') or []
    if len(iller) == 1:
        a = kurum_anahtari(iller[0])
        return a if a in IL_ANAHTAR else None
    return None


def _ascii_slug(s):
    s = s.translate(str.maketrans('çğıöşüâîûÇĞİÖŞÜ', 'cgiosuaiuCGIOSU')).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def kurum_slug(k):
    """kurum_kanonik + ASCII + tire; 'belediye' -> 'belediyesi'; en çok 80 karakter."""
    s = re.sub(r'\bbelediye$', 'belediyesi', kurum_kanonik(k))
    return _ascii_slug(s)[:80].strip('-') or 'kurum'


def _il_slug(item):
    iller = item.get('iller') or []
    return _ascii_slug(iller[0]) if iller else ''


def kart_meta(ilanlar, basarili=None):
    """{ilan anahtarı: kart alanları (+ kurum_slug, kurum_sayisi)} — ayrıntı sayfası olan her kayıt için.
    `basarili` verilirse kurum bağlantısı yalnız sayfası yazılabilen gruplara eklenir."""
    gruplar, slugler = kurum_gruplari(ilanlar)
    sonuc = {}
    for kan, liste in gruplar.items():
        for item in liste:
            alan = kart_alanlari(item)
            if basarili is None or kan in basarili:
                alan.update(kurum_slug=slugler[kan], kurum_sayisi=len(liste))
            sonuc[_su().detail_page(item)[0]] = alan
    return sonuc


def _grup_slug(kan, liste):
    s = kurum_slug(liste[0]['kurum'])
    return (s[:70].strip('-') + '-' + _ascii_slug(IL_ADI.get(kan.split('|')[1], kan.split('|')[1])))[:80].strip('-') if '|' in kan else s


def _sayfali(item):
    try:
        return _su().detail_page(item) is not None
    except Exception:
        return False


def kurum_gruplari(ilanlar):
    """({grup anahtarı: [ilan,…]}, {grup anahtarı: slug}). Yalnız ayrıntı sayfası olan (akademik olmayan) kayıtlar.
    Aynı adlı belediyeler farklı illerdeyse 'ad|il' grupları olur (ili bilinmeyen kayıtlar ayrı, ilsiz grupta kalır);
    tek ilse ili bilinmeyenler de gruba katılır. Slug çakışırsa sonuna il (yoksa sıra no) eklenir."""
    ham = {}
    for item in ilanlar:
        if akademik_ilan(item) or not (item.get('kurum') or '').strip() or not _sayfali(item):
            continue
        ham.setdefault(kurum_kanonik(item['kurum']), []).append(item)
    gruplar = {}
    for kan, liste in ham.items():
        illi, bilinmeyen = {}, []
        if kan.endswith(' belediye'):
            for i in liste:
                il = _ilan_ili(i)
                (illi.setdefault(il, []) if il else bilinmeyen).append(i)
        if len(illi) <= 1:
            gruplar[kan] = liste
            continue
        for il, l in illi.items():
            gruplar[f'{kan}|{il}'] = l
        if bilinmeyen:
            gruplar[kan] = bilinmeyen
    adaylar = {}
    for kan, liste in gruplar.items():
        adaylar.setdefault(_grup_slug(kan, liste), []).append(kan)
    slugler = {}
    for slug, kanlar in adaylar.items():
        if len(kanlar) == 1:
            slugler[kanlar[0]] = slug
            continue
        for n, kan in enumerate(sorted(kanlar), 1):
            il = next((_il_slug(i) for i in gruplar[kan] if _il_slug(i)), '') or str(n)
            slugler[kan] = (slug[:70].strip('-') + '-' + il)[:80].strip('-')
    gorulen = {}
    for kan in sorted(slugler):
        s = slugler[kan]
        if s in gorulen:
            s = f'{s[:74]}-{len(gorulen)}'
            slugler[kan] = s
        gorulen[s] = kan
    return gruplar, slugler


# ------------------------------------------------------------------ başlık / kadro
def temiz_baslik(i):
    """Başlıktan baştaki kurum adı (ve kurum adı kekemesi) atılır."""
    b = ' '.join(str(i.get('baslik') or '').split())
    kurum = str(i.get('kurum') or '')
    kisa = re.sub(r'\s+(rektörlüğü|başkanlığı|genel müdürlüğü)$', '', kucuk(kurum))
    for hedef in (kucuk(kurum), kisa):
        if not hedef:
            continue
        for n in range(1, min(len(b), len(hedef) + 8) + 1):
            if kucuk(b[:n]) == hedef:
                b = b[n:].lstrip(' -–—:') or b
                break
    return _ve_kucuk(_su()._duzgun(b)) or 'Personel alımı'


def _ve_kucuk(s):
    """Cümle ortasındaki Ve/İle/Veya küçük yazılır."""
    return re.sub(r'(?<=\S )(Ve|İle|Veya)(?= )', lambda m: 'ile' if m.group(1) == 'İle' else m.group(1).lower(), s)


def kadrolar(i):
    """[(adet|None, ad)] — duyurularda boş."""
    if i.get('duyuru_turu'):
        return []
    out = []
    for p in meslekler(i.get('kadro')):
        m = re.match(r'^(\d+)\s+(.*)$', p)
        adet, ad = (int(m.group(1)), m.group(2)) if m else (None, p)
        ad = SON_EK.sub('', ad).strip()
        if ad:
            out.append((adet, _ve_kucuk(_su()._duzgun(ad))))
    if not out:
        m = re.search(r'(\d+)\s+([^\d]+?)\s+(?:alacak|alınacak|alımı|alim)', temiz_baslik(i), re.I)
        if m:
            out.append((int(m.group(1)), _ve_kucuk(_su()._duzgun(m.group(2)))))
    return out


def _foto_haritasi():
    return {int(p.name[:2]): p.name for p in FOTO_KLASORU.glob('??-*.jpg')} if FOTO_KLASORU.is_dir() else {}


def kart_alanlari(i):
    """Liste kartı için derleme zamanı alanlar: manset, alt, ek, toplam, meslek (1–3 fotoğraf dosya adı)."""
    k = kadrolar(i)
    m = re.search(r'Toplam\s+(\d+)\s+kişi', i.get('kadro') or '', re.I)
    toplam = int(m.group(1)) if m else (sum(a or 0 for a, _ in k) or None)
    baslik = temiz_baslik(i)
    sirali = sorted(k, key=lambda x: -(x[0] or 0))
    if len(k) == 1:
        manset = (f'{k[0][0]} ' if k[0][0] else '') + k[0][1]
        alt = baslik if kucuk(SON_EK.sub('', baslik)) != kucuk(manset) else (i.get('ilan_turu') or '')
    elif k:
        manset, alt = ', '.join(a for _, a in sirali[:3]), baslik
    else:
        manset, alt = baslik, i.get('ilan_turu') or 'Kamu personel alımı'
    nolar = list(dict.fromkeys(meslek_no(a) for _, a in sirali)) or [meslek_no(baslik)]
    nolar = [n for n in nolar if n != 30][:3] or [30]
    foto = _foto_haritasi()
    alan = {'manset': manset[:160], 'alt': alt[:160], 'meslek': [foto[n] for n in nolar if n in foto]}
    if len(k) > 3:
        alan['ek'] = len(k) - 3
    if toplam and 0 < toplam < 20000:
        alan['toplam'] = toplam
    return alan


# ------------------------------------------------------------------ durum / tarih
def anahtar(i):
    k = parse_qs(urlparse(i.get('link', '')).query).get('i', [''])[0]
    try:
        return str(uuid.UUID(k))
    except ValueError:
        return i.get('id', '')


def tarih_yazi(iso):
    d = date.fromisoformat(iso)
    return f'{d.day} {AY[d.month - 1]} {d.year}'


def durum(i, simdi):
    """(metin, sınıf) — sınıf: ok/soon/urgent/today/none/upcoming/info/closed/cancelled."""
    if i.get('iptal_edildi'):
        return 'İptal edildi', 'cancelled'
    if i.get('duyuru_turu'):
        return i['duyuru_turu'], 'info'
    bit = _su()._bitis(i)
    if bit and bit <= simdi:
        return 'Başvuru sona erdi', 'closed'
    bas = i.get('baslangic_zaman')
    try:
        if bas and datetime.fromisoformat(bas).astimezone(TR) > simdi:
            return 'Başvuru henüz başlamadı', 'upcoming'
    except ValueError:
        pass
    st = i.get('son_tarih')
    if not st:
        return 'Tarih ilanda', 'none'
    d = (date.fromisoformat(st) - simdi.date()).days
    if d <= 0:
        return 'Bugün son gün', 'today'
    if d == 1:
        return 'Yarın son gün', 'today'
    return f'{d} gün kaldı', 'urgent' if d <= 3 else 'soon' if d <= 7 else 'ok'


def yer_kisa(i):
    y = re.split(r'\s*[/•]\s*', i.get('yer') or '')[0].strip(' -')
    if not y:
        return ''
    if kucuk(y).startswith('bakanlık merkez') or kucuk(y).startswith('ankara'):
        return 'Ankara'
    return _su()._duzgun(y)


# ------------------------------------------------------------------ sunucu tarafı kart (kurum sayfası)
def _logo_html(item, gorsel, kok):
    ad = esc(kurum_adi(item.get('kurum')))
    if gorsel.get('logo'):
        return f'<img class="institution-icon institution-logo" src="{kok}{esc(gorsel["logo"])}" alt="{ad} logosu" width="48" height="48" loading="lazy" decoding="async">'
    su = _su()
    return f'<span class="institution-icon institution-badge" style="--h:{su._ton(item.get("kurum"))}" aria-hidden="true">{esc(su._bas_harfler(item.get("kurum")))}</span>'


def kart_html(item, gorsel, simdi, kok='../../'):
    """Vitrin kartı (portal.js card() ile aynı yapı). Kayıt/karşılaştırma düğmeleri yoktur (JS gerektirir)."""
    a = kart_alanlari(item)
    metin, cls = durum(item, simdi)
    key = anahtar(item)
    href = f'{kok}ilan/{esc(key)}/'
    veri = f' data-son="{esc(item["son_tarih"])}" data-zaman="{esc(item.get("son_zaman") or "")}"' if cls in ('ok', 'soon', 'urgent', 'today') and item.get('son_tarih') else ''
    sayi = (f'<strong>{a["toplam"]:,}</strong><span>kadro</span>'.replace(',', '.')) if a.get('toplam') else f'<span class="card-count-none">{"Resmî duyuru" if item.get("duyuru_turu") else "Kadro sayısı ilanda"}</span>'
    dosyalar = a['meslek'] or ['30-genel.jpg']
    fotolar = ''.join(f'<img src="{kok}assets/meslek/{esc(f)}" alt="" width="76" height="76" loading="lazy">' for f in dosyalar)
    ek = f'<span class="card-more">+{a["ek"]}</span>' if a.get('ek') else ''
    chips = ''
    if item.get('kpss') == 'kpss':
        chips += '<span class="pill kpss">KPSS</span>'
    elif item.get('kpss') == 'kpsssiz':
        chips += '<span class="pill kpss">KPSS şartı yok</span>'
    chips += ''.join(f'<span class="pill level">{esc(LEVELS.get(o, o))}</span>' for o in item.get('ogrenim') or [])
    if yer_kisa(item):
        chips += f'<span class="pill place">{esc(yer_kisa(item))}</span>'
    tarih = f'Son başvuru <b>{esc(tarih_yazi(item["son_tarih"]))}</b>' if item.get('son_tarih') else 'Tarih resmî ilanda'
    return (f'<article class="card"><div class="card-band"><span class="card-status {cls}"{veri}>{esc(metin)}</span>'
            f'<div class="card-count">{sayi}</div><div class="card-photos n{len(dosyalar)}">{fotolar}</div></div>'
            f'<div class="card-body"><div class="card-head">{_logo_html(item, gorsel, kok)}</div>'
            f'<p class="institution">{esc(kurum_adi(item.get("kurum")))}</p>'
            f'<h3><a href="{href}">{esc(a["manset"])}</a>{ek}</h3><p class="card-sub">{esc(a["alt"])}</p>'
            f'<div class="card-chips">{chips}</div>'
            f'<div class="card-foot"><div class="card-when"><span class="deadline-date">{tarih}</span></div>'
            f'<a class="detail-link" href="{href}">İncele <span aria-hidden="true">→</span></a></div></div></article>')


def _gecmis_satir(item, simdi, kok):
    a = kart_alanlari(item)
    metin, cls = durum(item, simdi)
    zaman = tarih_yazi(item['son_tarih']) if item.get('son_tarih') else 'Tarih yok'
    return (f'<li class="kp-row"><span class="kp-st {cls}">{esc(metin)}</span>'
            f'<a href="{kok}ilan/{esc(anahtar(item))}/">{esc(a["manset"])}</a><time>{esc(zaman)}</time></li>')


KURUM_SAYAC = ('<script>(function(){var t=new Date().toLocaleDateString("sv-SE",{timeZone:"Europe/Istanbul"});'
               'document.querySelectorAll(".card-status[data-son]").forEach(function(e){var z=e.dataset.zaman;'
               'if(z&&Date.parse(z)<=Date.now()){e.textContent="Başvuru sona erdi";e.className="card-status closed";return}'
               'var d=Math.round((Date.parse(e.dataset.son+"T00:00:00Z")-Date.parse(t+"T00:00:00Z"))/864e5);if(isNaN(d))return;'
               'if(d<0){e.textContent="Başvuru sona erdi";e.className="card-status closed";return}'
               'e.textContent=d===0?"Bugün son gün":d===1?"Yarın son gün":d+" gün kaldı";'
               'e.className="card-status "+(d<=1?"today":d<=3?"urgent":d<=7?"soon":"ok")})})()</script>')


def en_cok_gecen_ad(liste):
    sayac = {}
    for i in liste:
        ad = kurum_adi(i.get('kurum'))
        sayac[ad] = sayac.get(ad, 0) + 1
    # belediyelerde 'X Belediyesi' biçimi 'X Belediye Başkanlığı'ndan önce gelir; sonra sıklık, sonra uzunluk
    return sorted(sayac, key=lambda a: (not a.endswith('Belediyesi'), -sayac[a], -len(a), a))[0]


def kurum_sayfasi(kan, liste, slug, gorseller, simdi):
    """Tek kurumun statik sayfası (HTML metni)."""
    su = _su()
    ad = en_cok_gecen_ad(liste)
    if '|' in kan:
        il = kan.split('|')[1]
        if il not in kurum_anahtari(ad).split():
            ad += f' ({IL_ADI.get(il, il)})'
    kok = '../../'
    ciftler = [(i, gorseller.get(anahtar(i), {})) for i in liste]
    acik = [(i, g) for i, g in ciftler if durum(i, simdi)[1] in ACIK]
    gecmis = [(i, g) for i, g in ciftler if durum(i, simdi)[1] not in ACIK]
    acik.sort(key=lambda p: p[0].get('son_tarih') or '9999')
    gecmis.sort(key=lambda p: p[0].get('son_tarih') or '', reverse=True)
    toplam_kadro = sum(kart_alanlari(i).get('toplam') or 0 for i, _ in acik)
    diger = sorted({kurum_adi(i['kurum']) for i in liste} - {ad})
    logo_g = next((g for _, g in ciftler if g.get('logo')), {})
    logo_i = next((i for i, g in ciftler if g.get('logo')), liste[0])
    logo = _logo_html(logo_i, logo_g, kok).replace('institution-icon', 'kp-logo').replace('width="48" height="48"', 'width="84" height="84"')
    baslik = f'{ad} ilanları'
    aciklama = f'{ad} kurumunun başvurusu açık kamu personel alım ilanları ({len(acik)}) ve geçmiş duyuruları.'[:190]
    canonical = su.BASE + 'kurum/' + slug + '/'
    adlar = f'<p>Kaynaklarda geçen adlar: {esc(", ".join(diger))}</p>' if diger else '<p>Kamu personel alım ilanları ve duyuruları</p>'
    acik_html = ''.join(kart_html(i, g, simdi, kok) for i, g in acik) if acik else ''
    if acik:
        acik_blok = f'<div class="cards">{acik_html}</div>'
    else:
        acik_blok = '<div class="empty"><h3>Şu an başvurusu açık ilan yok.</h3><p>Bu kurumdan yeni bir ilan geldiğinde burada görünür. Telegram kanalından da takip edebilirsin.</p></div>'
    gecmis_blok = ''
    if gecmis:
        gecmis_blok = (f'<section class="kp-section"><h2>Duyurular ve geçmiş ilanlar <small>{len(gecmis)}</small></h2><ul class="kp-past">'
                       + ''.join(_gecmis_satir(i, simdi, kok) for i, _ in gecmis)
                       + '</ul><p class="kp-note">Düzeltme/iptal duyuruları ile sona eren ilanlar arşiv amacıyla gösterilir. Güncel bilgi için resmî kaynağı esas al.</p></section>')
    icerik = f'''<section class="kp-hero"><div class="container"><nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}#ilanlar">İlanlar</a><span aria-hidden="true">/</span><span>{esc(ad)}</span></nav>
<div class="kp-id">{logo}<div><span class="eyebrow">KURUM</span><h1>{esc(ad)}</h1>{adlar}</div></div>
<div class="kp-stats"><div><strong>{len(acik)}</strong><span>başvurusu açık ilan</span></div><div><strong>{f"{toplam_kadro:,}".replace(",", ".") if toplam_kadro else "—"}</strong><span>bilinen kadro</span></div><div><strong>{len(liste)}</strong><span>toplam ilan kaydı</span></div></div>
<div class="kp-actions"><a class="button lime" href="https://t.me/kamuilantakip" target="_blank" rel="noopener">Telegram'da ilanları takip et ↗</a><a class="button ghost" href="{kok}">Tüm ilanlara dön</a></div></div></section>
<main id="icerik" class="container kp-main"><section class="kp-section"><h2>Başvurusu açık ilanlar <small>{len(acik)}</small></h2>{acik_blok}</section>{gecmis_blok}</main>'''
    return su.sayfa_kabugu(baslik + ' | Kamu İlan Takip', aciklama, canonical, icerik, 'kurum-page')


def kurum_sayfalarini_uret(ilanlar, docs, gorseller, simdi=None):
    """docs/kurum/ altını baştan yazar. (gruplar, slugler, sitemap adresleri, başarıyla yazılan grup anahtarları) döndürür;
    bir grubun sayfası üretilemezse atlanır (klasörü silinir) ve başarılı kümeye girmez."""
    su = _su()
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    kok = docs / 'kurum'
    shutil.rmtree(kok, ignore_errors=True)
    gruplar, slugler = kurum_gruplari(ilanlar)
    adresler, basarili = [], set()
    for kan, liste in gruplar.items():
        slug = slugler[kan]
        klasor = kok / slug
        try:
            html = kurum_sayfasi(kan, liste, slug, gorseller, simdi)
            klasor.mkdir(parents=True, exist_ok=True)
            (klasor / 'index.html').write_text(html, encoding='utf-8')
        except Exception as hata:
            print(f'Uyarı: kurum sayfası üretilemedi ({slug}): {hata}')
            shutil.rmtree(klasor, ignore_errors=True)
            continue
        adresler.append(su.BASE + 'kurum/' + slug + '/')
        basarili.add(kan)
    return gruplar, slugler, adresler, basarili
