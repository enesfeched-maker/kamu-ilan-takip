"""İnce sayfa kalkanı (15 Kasım 2026, AdSense üçüncü inceleme öncesi).

Kurum, meslek, il ve taban puanı sayfaları şablondan üretilir. İlan bağlantısı taşımayan ve ana içeriği MIN_KELIME'den az olanlar
(ör. açık ilanı olmayan, yalnız birkaç yerleştirme satırı taşıyan kurum sayfası) "düşük değerli içerik"
sayılabilir. Bu sayfalar silinmez (adres 404 vermez) ama noindex alır, reklam betiği çıkar ve site
haritasından düşer. İletişim/gizlilik/kullanım koşulları dizinde kalır, yalnız reklamsız olur.

Onaydan sonra gevşetmek için MIN_KELIME düşürülür ya da SABLON_KLASORLERI boşaltılır.
"""
import re
from pathlib import Path

MIN_KELIME = 250
MIN_ILANLI_KELIME = 120   # ilan bağlantısı olsa da bundan kısa sayfa (yalnız 1–2 eski ilan) ince sayılır
ILANLI_ESIGI = {'kurum': 0}   # kurum sayfasındaki ilan bağlantısı o kurumun açık ilanıdır: kısa da olsa canlı içerik
KLASOR_ESIGI = {'meslek': 180}   # meslek sayfası aramadan trafik alıyor (zabıta): açık ilan tablosu kısa da olsa değerli
SABLON_KLASORLERI = ('kurum', 'meslek', 'il', 'kpss-taban-puanlari')
REKLAMSIZ_SAYFALAR = ('iletisim', 'gizlilik', 'kullanim-kosullari')
NOINDEX = '<meta name="robots" content="noindex,follow">'
_REKLAM = re.compile(r'<script async src="https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js[^"]*" crossorigin="anonymous"></script>')


def ana_kelime_sayisi(html):
    """<main> içindeki görünür kelime sayısı (yoksa <body>)."""
    m = re.search(r'(?s)<main\b.*?</main>', html) or re.search(r'(?s)<body\b.*?</body>', html)
    govde = m.group(0) if m else html
    govde = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', govde)
    metin = re.sub(r'<[^>]+>', ' ', govde)
    return len(metin.split())


def ilan_baglantisi_var(html):
    """Sayfa bir ilan sayfasına bağlanıyorsa (açık/yakın ilan listesi) canlı içerik taşır; kalkan dokunmaz."""
    m = re.search(r'(?s)<main\b.*?</main>', html)
    return bool(re.search(r'href="[^"]*\bilan/[^"/]+/"', m.group(0) if m else html))


def reklami_cikar(html):
    return _REKLAM.sub('', html)


def noindex_yap(html):
    if re.search(r'<meta name="robots"[^>]*noindex', html):
        return html
    return html.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + NOINDEX, 1)


def _adres_yolu(docs, base, url):
    if not url.startswith(base):
        return None
    yol = url[len(base):].strip('/')
    return (docs / yol / 'index.html') if yol else None


def suz(docs, base, urls):
    """Site haritasına girecek adresleri süzer; ince şablon sayfalarını noindex + reklamsız yapar.
    Dönüş: (kalan adresler, çıkarılan adresler)."""
    docs = Path(docs)
    kalan, cikan = [], []
    for url in urls:
        dosya = _adres_yolu(docs, base, url)
        parcalar = url[len(base):].strip('/').split('/') if url.startswith(base) else []
        if dosya is None or not dosya.exists() or len(parcalar) < 2 or parcalar[0] not in SABLON_KLASORLERI:
            kalan.append(url)
            continue
        html = dosya.read_text(encoding='utf-8')
        kelime = ana_kelime_sayisi(html)
        if kelime >= KLASOR_ESIGI.get(parcalar[0], MIN_KELIME) or (kelime >= ILANLI_ESIGI.get(parcalar[0], MIN_ILANLI_KELIME) and ilan_baglantisi_var(html)):
            kalan.append(url)
            continue
        dosya.write_text(noindex_yap(reklami_cikar(html)), encoding='utf-8')
        cikan.append(url)
    for ad in REKLAMSIZ_SAYFALAR:
        dosya = docs / ad / 'index.html'
        if dosya.exists():
            html = dosya.read_text(encoding='utf-8')
            yeni = reklami_cikar(html)
            if yeni != html:
                dosya.write_text(yeni, encoding='utf-8')
    return kalan, cikan
