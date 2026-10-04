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


def kart_meta(ilanlar, basarili=None, kopyalar=None):
    """{ilan anahtarı: kart alanları (+ kurum_slug, kurum_sayisi)} — ayrıntı sayfası olan her kayıt için.
    `basarili` verilirse kurum bağlantısı yalnız sayfası yazılabilen gruplara eklenir."""
    gruplar, slugler = kurum_gruplari(ilanlar)
    ikincil = (kopyalar or {}).get('kopya_of') or {}
    sonuc = {}
    for kan, liste in gruplar.items():
        sayi = sum(1 for i in liste if i.get('id') not in ikincil) or len(liste)   # kopya çift tek sayılır
        for item in liste:
            alan = kart_alanlari(item)
            if basarili is None or kan in basarili:
                alan.update(kurum_slug=slugler[kan], kurum_sayisi=sayi)
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


YER_AYIR = re.compile(r'\s*,\s*|\s*/\s*|\s+-\s*|\s*-\s+')
YER_EN_COK_IL = 3


def yer_metni(item, il_yedek=''):
    """Görev yeri gösterimi: il önce, ilçe/birim parantezde ('Ankara (Merkez)'); il/yer/iller alanları tekilleştirilir,
    çoklu iller ', ' ile birleşir, 3'ten fazla ilde 'Ankara, İstanbul +4'. İl bulunamayan ad (örn. 'Bakanlık Merkez Teşkilatı')
    olduğu gibi (düzgün yazımla) kalır. Hiçbir alan yoksa `il_yedek`."""
    su = _su()
    iller, diger = {}, []                      # {il adı: [ilçe/birim, …]}, il olmayan adlar
    ekle = lambda liste, ad: liste.append(ad) if kucuk(ad) not in {kucuk(x) for x in liste} else None
    for parca in re.split(r'\s*•\s*', str(item.get('yer') or '')):
        simdiki = None
        for tok in (t.strip(' -') for t in YER_AYIR.split(parca)):
            if not tok:
                continue
            il = IL_ADI.get(kurum_anahtari(tok))
            if il:
                simdiki = il
                iller.setdefault(il, [])
            elif simdiki:
                ekle(iller[simdiki], su._duzgun(tok))
            else:
                ekle(diger, su._duzgun(tok))
    for ad in item.get('iller') or []:
        il = IL_ADI.get(kurum_anahtari(ad))
        if il:
            iller.setdefault(il, [])
    if not iller and not diger:
        return il_yedek or ''
    liste = list(iller.items())
    if len(liste) > YER_EN_COK_IL:
        yazi = ', '.join(il for il, _ in liste[:2]) + f' +{len(liste) - 2}'
    else:
        yazi = ', '.join(f'{il} ({", ".join(ilce)})' if ilce else il for il, ilce in liste)
    return ' · '.join([*diger, yazi] if yazi else diger)


# ------------------------------------------------------------------ sunucu tarafı satır (kurum / ilan sayfaları)
# portal.js rowEl() çıktısıyla aynı sınıf adları: ilan, ilan-foto, ilan-govde, ilan-kurum, ilan-meta, sinyal, ilan-sag, tarih, kaydet.
SAAT = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>'
KISA_AY = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
SAYI_YAZ = lambda n: f'{n:,}'.replace(',', '.')


def _logo_html(item, gorsel, kok, sinif='institution-icon', boyut=48):
    """Kurum logosu (WebP) ya da baş harfli renkli karo."""
    ad = esc(kurum_adi(item.get('kurum')))
    if gorsel.get('logo'):
        return f'<img class="{sinif} institution-logo" src="{kok}{esc(gorsel["logo"])}" alt="{ad} logosu" width="{boyut}" height="{boyut}" loading="lazy" decoding="async">'
    su = _su()
    return f'<span class="{sinif} institution-badge" style="--h:{su._ton(item.get("kurum"))}" aria-hidden="true">{esc(su._bas_harfler(item.get("kurum")))}</span>'


def _kayit(item, gorsel, simdi, tablolar=None, harita=None):
    import liste_verisi
    return liste_verisi.kayit(item, gorsel, tablolar or {}, simdi, harita)


def _ilan_gorseli(k, kok):
    """(görsel düğümü, karo mu): genel fotoğrafta logo karosu ya da harf karosu."""
    su = _su()
    meslek = k.get('meslek') or []
    if not meslek or meslek[0].startswith('30-'):
        if k.get('logo'):
            return f'<span class="ilan-foto logo-karo"><img src="{kok}{esc(k["logo"])}" alt="" loading="lazy" decoding="async"></span>', True
        return f'<span class="ilan-foto harf-karo" style="--h:{su._ton(k.get("kurum"))}" aria-hidden="true">{esc(su._bas_harfler(k.get("kurum")))}</span>', False
    return f'<img class="ilan-foto" src="{kok}assets/meslek/{esc(meslek[0])}" alt="" width="52" height="52" loading="lazy" decoding="async">', False


def _meta_html(k):
    parcalar = []
    if k.get('toplam') and not re.match(r'\d', k.get('manset') or ''):
        parcalar.append(('', f'<b>{SAYI_YAZ(k["toplam"])} kadro</b>'))
    if k.get('il'):
        parcalar.append(('', esc(k['il'])))
    if k.get('ogrenim'):
        parcalar.append(('', esc(' / '.join(LEVELS[o] for o in k['ogrenim']))))
    if k.get('puan_turleri'):
        parcalar.append(('kpss', 'KPSS ' + esc(', '.join(k['puan_turleri'][:2]))))
    elif k.get('kpss') == 'kpss':
        parcalar.append(('kpss', 'KPSS'))
    return '<p class="ilan-meta">' + ''.join(f'<span{f" class={chr(34)}{c}{chr(34)}" if c else ""}>{v}</span>' for c, v in parcalar[:4]) + '</p>'


def _tarih_html(k, simdi):
    yakinda = k.get('durum') == 'upcoming'
    if not k.get('son_tarih'):
        return '<div class="tarih yok"><strong>—</strong><span>tarih ilanda</span></div>'
    g = (date.fromisoformat(k['son_tarih']) - simdi.date()).days
    veri = f' data-son="{esc(k["son_tarih"])}" data-zaman="{esc(k.get("son_zaman") or "")}" data-yakinda="{int(yakinda)}"'
    d = date.fromisoformat(k['son_tarih'])
    kisa = f'{d.day} ' + KISA_AY[d.month - 1]
    if g <= 2 and not yakinda:
        if g <= 0:
            return f'<div class="tarih acil"{veri}><strong>Bugün</strong><span>son gün</span></div>'
        if g == 1:
            return f'<div class="tarih acil"{veri}><strong>Yarın</strong><span>son gün</span></div>'
        return f'<div class="tarih acil"{veri}><strong>{kisa}</strong><span>2 gün kaldı</span></div>'
    return f'<div class="tarih"{veri}><strong>{kisa}</strong><span>{g} gün</span></div>'


def satir_html(k, simdi, kok='../../', kurum_baglantisi=True):
    """liste.json kaydından tek ilan satırı (portal.js rowEl ile aynı yapı). Tüm metin kaçışlıdır."""
    su = _su()
    gorsel, karo = _ilan_gorseli(k, kok)
    ad = k.get('kurum') or 'Kurum belirtilmemiş'
    if k.get('logo') and not karo:
        kucuk_logo = f'<img class="kl" src="{kok}{esc(k["logo"])}" alt="" width="18" height="18" loading="lazy">'
    elif karo:
        kucuk_logo = ''
    else:
        kucuk_logo = f'<span class="kb" style="--h:{su._ton(k.get("kurum"))}" aria-hidden="true">{esc(su._bas_harfler(k.get("kurum")))}</span>'
    if kurum_baglantisi and k.get('kurum_slug'):
        kurum = f'<a class="ad" href="{kok}kurum/{esc(k["kurum_slug"])}/" title="{esc(ad)} — kurumun tüm ilanları">{esc(ad)}</a>'
    else:
        kurum = f'<span class="ad">{esc(ad)}</span>'
    ek = f' <span class="ek">+{int(k["ek"])}</span>' if k.get('ek') else ''
    sinyal, veri = '', ''
    if k.get('durum') == 'upcoming' and k.get('baslangic_zaman'):
        try:
            b = datetime.fromisoformat(k['baslangic_zaman']).astimezone(TR)
            sinyal = f'<p class="sinyal acilis"><span class="ic">{SAAT}</span>Başvuru {b.day} {AY[b.month - 1]}’de açılıyor</p>'
        except ValueError:
            pass
    elif k.get('taban_ref'):
        veri = f' data-ref="{esc(json.dumps(k["taban_ref"], ensure_ascii=False, separators=(",", ":")))}" data-pt="{esc(",".join(k.get("puan_turleri") or []))}"'
    key = esc(k['key'])
    kayit_id = esc(k.get('id') or k['key'])
    return (f'<article class="ilan"{veri}>{gorsel}<div class="ilan-govde"><div class="ilan-kurum">{kucuk_logo}{kurum}</div>'
            f'<h3><a href="{kok}ilan/{key}/">{esc(k.get("manset") or "Kamu ilanı")}</a>{ek}</h3>{_meta_html(k)}{sinyal}</div>'
            f'<div class="ilan-sag">{_tarih_html(k, simdi)}'
            f'<button type="button" class="kaydet" data-kaydet="{kayit_id}" data-ad="{esc(k.get("manset") or "İlan")}" aria-label="İlanı kaydet: {esc(k.get("manset") or "İlan")}" aria-pressed="false">{BOOKMARK}</button></div></article>')


def kart_html(item, gorsel, simdi, kok='../../', tablolar=None, harita=None, kurum_baglantisi=False):
    """Açık ilanın satırı (yeni .ilan satır biçimi); satır gösterilmeyecek bir ilan için boş metin."""
    k = _kayit(item, gorsel, simdi, tablolar, harita)
    return satir_html(k, simdi, kok, kurum_baglantisi) if k else ''


def _gecmis_satir(item, simdi, kok):
    a = kart_alanlari(item)
    metin, cls = durum(item, simdi)
    zaman = tarih_yazi(item['son_tarih']) if item.get('son_tarih') else 'Tarih yok'
    return (f'<tr class="kp-row"><td class="kp-baslik"><a href="{kok}ilan/{esc(anahtar(item))}/">{esc(a["manset"])}</a></td>'
            f'<td class="kp-durum"><span class="kp-st {cls}">{esc(metin)}</span></td><td class="kp-tarih"><time>{esc(zaman)}</time></td></tr>')


def kurum_turu(ad):
    k = kucuk(ad)
    for parca, etiket in (('belediye', 'Belediye'), ('üniversite', 'Üniversite'), ('hastane', 'Hastane'), ('bakanlığı', 'Bakanlık'),
                          ('genel müdürlüğü', 'Genel müdürlük'), ('başkanlığı', 'Başkanlık'), ('müdürlüğü', 'Müdürlük'), ('kurumu', 'Kurum'), ('kurulu', 'Kurul')):
        if parca in k:
            return etiket
    return ''


def en_cok_gecen_ad(liste):
    sayac = {}
    for i in liste:
        ad = kurum_adi(i.get('kurum'))
        sayac[ad] = sayac.get(ad, 0) + 1
    # belediyelerde 'X Belediyesi' biçimi 'X Belediye Başkanlığı'ndan önce gelir; sonra sıklık, sonra uzunluk
    return sorted(sayac, key=lambda a: (not a.endswith('Belediyesi'), -sayac[a], -len(a), a))[0]


def kurum_sayfasi(kan, liste, slug, gorseller, simdi, tablolar=None, harita=None, kopyalar=None):
    """Tek kurumun statik sayfası (HTML metni). Kaynaklar arası kopyaların ikincil kaydı listelerden ve sayılardan çıkarılır."""
    su = _su()
    import liste_verisi
    tum = liste
    ikincil = (kopyalar or {}).get('kopya_of') or {}
    liste = [i for i in tum if i.get('id') not in ikincil] or tum
    ad = en_cok_gecen_ad(tum)
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
    diger = sorted({kurum_adi(i['kurum']) for i in tum} - {ad})
    logo_g = next((g for _, g in ciftler if g.get('logo')), {})
    logo_i = next((i for i, g in ciftler if g.get('logo')), liste[0])
    logo = _logo_html(logo_i, logo_g, kok, 'kp-logo', 64)
    ilar = {}
    for i in liste:
        il_adi = re.sub(r'\s*\+\d+$', '', liste_verisi.il_bul(i, harita) or '')
        if il_adi:
            ilar[il_adi] = ilar.get(il_adi, 0) + 1
    il_yazi = sorted(ilar, key=lambda a: (-ilar[a], a))[0] if ilar else ''
    ozet = ''.join(f'<span>{esc(p)}</span>' for p in (il_yazi, kurum_turu(ad)) if p)
    ozet = f'<div class="kp-ozet">{ozet}</div>' if ozet else ''
    baslik = f'{ad} ilanları'
    aciklama = f'{ad} kurumunun başvurusu açık kamu personel alım ilanları ({len(acik)}) ve geçmiş duyuruları.'[:190]
    canonical = su.BASE + 'kurum/' + slug + '/'
    adlar = f'<p>Kaynaklarda geçen adlar: {esc(", ".join(diger))}</p>' if diger else ''
    satirlar = ''.join(kart_html(i, g, simdi, kok, tablolar, harita) for i, g in acik)
    if acik:
        acik_blok = f'<div class="liste">{satirlar}</div>'
    else:
        acik_blok = '<div class="bos-kutu"><h3>Şu an başvurusu açık ilan yok.</h3><p>Bu kurumdan yeni bir ilan geldiğinde burada görünür. Telegram kanalından da takip edebilirsin.</p></div>'
    gecmis_blok = ''
    if gecmis:
        gecmis_blok = (f'<section class="bolum"><div class="bolum-bas"><h2>Duyurular ve geçmiş ilanlar <span class="sayi">{len(gecmis)}</span></h2></div>'
                       '<div class="tablo-kap"><table class="kp-tablo"><thead><tr><th scope="col">İlan</th><th scope="col">Durum</th><th scope="col">Son başvuru</th></tr></thead><tbody>'
                       + ''.join(_gecmis_satir(i, simdi, kok) for i, _ in gecmis)
                       + '</tbody></table></div><p class="kp-note">Düzeltme/iptal duyuruları ile sona eren ilanlar arşiv amacıyla gösterilir. Güncel bilgi için resmî kaynağı esas al.</p></section>')
    kadro_yazi = SAYI_YAZ(toplam_kadro) if toplam_kadro else '—'
    icerik = f'''<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}#ilanlar">İlanlar</a><span aria-hidden="true">/</span><span>{esc(ad)}</span></nav>
<div class="kp-id">{logo}<div><span class="eyebrow">Kurum</span><h1>{esc(ad)}</h1>{ozet}{adlar}</div></div>
<div class="kp-stats"><div><strong>{len(acik)}</strong><span>açık ilan</span></div><div><strong>{kadro_yazi}</strong><span>bilinen kadro</span></div><div><strong>{len(liste)}</strong><span>toplam kayıt</span></div></div>
<div class="kp-actions"><a class="btn btn-tg btn-buyuk" href="https://t.me/kamuilantakip" target="_blank" rel="noopener">Telegram'da takip et ↗</a></div></div></section>
<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Başvurusu açık ilanlar <span class="sayi">{len(acik)}</span></h2></div>{acik_blok}</section>{gecmis_blok}</main>'''
    return su.sayfa_kabugu(baslik + ' | Kamu İlan Takip', aciklama, canonical, icerik, 'kurum-page', baslik)


def kurum_sayfalarini_uret(ilanlar, docs, gorseller, simdi=None, kopyalar=None):
    """docs/kurum/ altını baştan yazar. (gruplar, slugler, sitemap adresleri, başarıyla yazılan grup anahtarları) döndürür;
    bir grubun sayfası üretilemezse atlanır (klasörü silinir) ve başarılı kümeye girmez."""
    su = _su()
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    kok = docs / 'kurum'
    shutil.rmtree(kok, ignore_errors=True)
    gruplar, slugler = kurum_gruplari(ilanlar)
    tablolar, harita = {}, None
    try:
        import liste_verisi
        tablolar, harita = liste_verisi.taban_tablolari(docs), liste_verisi.il_haritasi(ilanlar)
    except Exception as hata:
        print(f'Uyarı: kurum sayfaları için taban verisi okunamadı: {hata}')
    adresler, basarili = [], set()
    for kan, liste in gruplar.items():
        slug = slugler[kan]
        klasor = kok / slug
        try:
            html = kurum_sayfasi(kan, liste, slug, gorseller, simdi, tablolar, harita, kopyalar)
            klasor.mkdir(parents=True, exist_ok=True)
            (klasor / 'index.html').write_text(html, encoding='utf-8')
        except Exception as hata:
            print(f'Uyarı: kurum sayfası üretilemedi ({slug}): {hata}')
            shutil.rmtree(klasor, ignore_errors=True)
            continue
        adresler.append(su.BASE + 'kurum/' + slug + '/')
        basarili.add(kan)
    return gruplar, slugler, adresler, basarili
