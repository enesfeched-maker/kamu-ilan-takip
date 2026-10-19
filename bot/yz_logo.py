"""Arşivde logosu olmayan kurumun logosunu internetten bulur (19 Ekim 2026).

1. Gemini, Google aramasıyla kurumun resmî sitesini ve logo adresini bulur (yalnız resmî alan adları: gov.tr, bel.tr…).
2. Resmî sitenin ana sayfasından logo adayları toplanır (img'de 'logo', og:image, büyük simgeler).
3. Adaylar indirilir; Gemini her birine bakıp "bu, bu kurumun logosu/amblemi mi?" diye doğrular.
4. Güveni yüksek olan PNG'ye çevrilir, docs/assets/kurum-logolari/ arşivine ve kaynaklar.json'a eklenir.
Bulunamazsa ilan logosuz paylaşılmaz (ilan_bot.yayina_hazir); Actions uyarısıyla elle eklenir."""
import base64
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARSIV = ROOT / 'docs' / 'assets' / 'kurum-logolari'
RESMI_UZANTILAR = ('.gov.tr', '.bel.tr', '.edu.tr', '.tsk.tr', '.org.tr', '.pol.tr', '.k12.tr', '.av.tr', '.jgk.gov.tr')
EN_BUYUK_GORSEL = 3 * 1024 * 1024
EN_AZ_GUVEN = 0.8
TARAYICI = {'User-Agent': 'Mozilla/5.0 (KPSS Tercihi logo arşivi; +https://kpsstercihi.com/)'}

ARAMA_ISTEMI = """Türkiye'deki "{kurum}" kurumunun resmî internet sitesini ve sitedeki logo/amblem görselinin doğrudan adresini
Google'da ara. Yalnız resmî alan adlarını (gov.tr, bel.tr, edu.tr, tsk.tr, org.tr) kabul et; haber sitesi, Vikipedi, sosyal
medya olmasın. Yalnız şu JSON'u yaz, başka hiçbir şey yazma:
{{"site": "https://...", "logolar": ["https://.../logo.png"]}}"""

DOGRULA_ISTEMI = """Bu görsel Türkiye'deki "{kurum}" kurumunun logosu ya da amblemi mi? Başka bir kurumun logosu, kişi
fotoğrafı, afiş, haber görseli, bayrak, genel Türkiye Cumhuriyeti arması ya da boş/bozuk görsel ise hayır de.
Belediye logolarında belediyenin adı ya da amblemi görünmeli."""
DOGRULA_SEMA = {'type': 'OBJECT', 'properties': {'logo_mu': {'type': 'BOOLEAN'}, 'guven': {'type': 'NUMBER'},
                                                 'neden': {'type': 'STRING'}}, 'required': ['logo_mu', 'guven']}


def resmi_mi(url):
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or '').lower()
    return u.scheme in ('http', 'https') and any(host.endswith(x) or host == x.lstrip('.') for x in RESMI_UZANTILAR)


def _indir(url, sinir=EN_BUYUK_GORSEL, zaman_asimi=30):
    req = urllib.request.Request(url, headers=TARAYICI)
    with urllib.request.urlopen(req, timeout=zaman_asimi) as r:
        if not resmi_mi(r.geturl()):
            raise ValueError('yönlendirme resmî alan dışına çıktı')
        veri = r.read(sinir + 1)
    if len(veri) > sinir:
        raise ValueError('dosya çok büyük')
    return veri


def _json_bul(metin):
    m = re.search(r'\{.*\}', metin or '', re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}


def gemini_ara(kurum, anahtar, iste=None):
    """Google aramalı Gemini: {'site':…, 'logolar':[…]} (yanıt JSON değilse boş)."""
    import yz_denetim as yd
    govde = {'contents': [{'parts': [{'text': ARAMA_ISTEMI.format(kurum=kurum)}]}], 'tools': [{'google_search': {}}],
             'generationConfig': {'temperature': 0}}
    iste = iste or yd._iste
    if not yd._MODELLER:
        yd._MODELLER.extend([yd.MODEL] if yd.MODEL else yd.modeller_bul(anahtar)[:3])
    for model in yd._MODELLER:
        try:
            yanit = iste(model, govde, anahtar, 120)
            metin = ''.join(p.get('text', '') for p in yanit['candidates'][0]['content']['parts'])
            return _json_bul(metin)
        except Exception as hata:
            print(f'Uyarı: logo araması ({model}) yanıt vermedi: {str(hata)[:150]}')
    return {}


def site_adaylari(site, html=None):
    """Resmî sitenin ana sayfasındaki logo adayları (öncelik: adında/alt yazısında 'logo' geçen img, og:image, simgeler)."""
    from bs4 import BeautifulSoup
    if html is None:
        html = _indir(site, 2 * 1024 * 1024).decode('utf-8', 'replace')
    sayfa = BeautifulSoup(html, 'html.parser')
    adaylar = []
    for img in sayfa.find_all('img'):
        src = img.get('src') or img.get('data-src') or ''
        ipucu = ' '.join([src, img.get('alt') or '', ' '.join(img.get('class') or []), img.get('id') or '']).lower()
        if 'logo' in ipucu or 'amblem' in ipucu:
            adaylar.append(src)
    for meta in sayfa.find_all('meta', attrs={'property': 'og:image'}):
        adaylar.append(meta.get('content') or '')
    for link in sayfa.find_all('link', rel=True):
        if any(r in ('apple-touch-icon', 'icon') for r in link.get('rel')) and re.search(r'(?:1[5-9]\d|[2-9]\d\d)', link.get('sizes') or link.get('href') or ''):
            adaylar.append(link.get('href') or '')
    sonuc = []
    for a in adaylar:
        tam = urllib.parse.urljoin(site, a.strip())
        if tam and resmi_mi(tam) and not tam.lower().endswith('.svg') and tam not in sonuc:
            sonuc.append(tam)
    return sonuc[:6]


def gorsel_hazirla(veri):
    """PNG baytları (en uzun kenar 600 px) ya da None (açılamayan / çok küçük görsel)."""
    from PIL import Image
    try:
        with Image.open(io.BytesIO(veri)) as im:
            im.load()
            if min(im.size) < 48:
                return None
            im = im.convert('RGBA')
            im.thumbnail((600, 600))
            out = io.BytesIO()
            im.save(out, format='PNG', optimize=True)
            return out.getvalue(), im.size
    except Exception:
        return None


def dogrula(kurum, png, anahtar, iste=None):
    import yz_denetim as yd
    govde = {'contents': [{'parts': [{'inline_data': {'mime_type': 'image/png', 'data': base64.b64encode(png).decode()}},
                                     {'text': DOGRULA_ISTEMI.format(kurum=kurum)}]}],
             'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'responseSchema': DOGRULA_SEMA}}
    iste = iste or yd._iste
    for model in yd._MODELLER or [yd.MODEL]:
        try:
            yanit = iste(model, govde, anahtar, 120)
            return json.loads(yanit['candidates'][0]['content']['parts'][0]['text'])
        except Exception as hata:
            print(f'Uyarı: logo doğrulama ({model}) yanıt vermedi: {str(hata)[:150]}')
    return {}


def kaydet(kurum, png, boyut, site, orijinal, arsiv=ARSIV):
    from kurum_gorseli import kurum_anahtari
    anahtar = kurum_anahtari(kurum)
    dosya = re.sub(r'[^a-z0-9]+', '-', anahtar).strip('-')[:80] + '.png'
    arsiv = Path(arsiv)
    (arsiv / dosya).write_bytes(png)
    manifest = arsiv / 'kaynaklar.json'
    kayitlar = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    kayitlar[anahtar] = {'dosya': dosya, 'kaynak': site, 'orijinal': orijinal, 'boyut': list(boyut),
                         'bulan': f'Gemini {date.today().isoformat()}'}
    manifest.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dosya


def logo_bul_ve_kaydet(item, anahtar, iste=None, indir=None, arsiv=ARSIV):
    from kart_tasarimlari import kisa_kurum
    kurum = kisa_kurum(item.get('kurum') or '') or item.get('kurum') or ''
    if not kurum:
        return None
    indir = indir or _indir
    bulunan = gemini_ara(kurum, anahtar, iste)
    site = bulunan.get('site') if resmi_mi(bulunan.get('site') or '') else None
    adaylar = [u for u in bulunan.get('logolar') or [] if resmi_mi(u) and not u.lower().endswith('.svg')]
    if site:
        try:
            adaylar += [u for u in site_adaylari(site, indir(site, 2 * 1024 * 1024).decode('utf-8', 'replace')) if u not in adaylar]
        except Exception as hata:
            print(f'Uyarı: {site} okunamadı: {str(hata)[:120]}')
    for url in adaylar[:6]:
        try:
            hazir = gorsel_hazirla(indir(url))
        except Exception:
            continue
        if not hazir:
            continue
        png, boyut = hazir
        karar = dogrula(kurum, png, anahtar, iste)
        if karar.get('logo_mu') and float(karar.get('guven') or 0) >= EN_AZ_GUVEN:
            dosya = kaydet(item.get('kurum') or kurum, png, boyut, site or url, url, arsiv)
            print(f'Logo bulundu ve arşive eklendi: {kurum} -> {dosya} ({url})')
            return dosya
    print(f'::warning::Logo bulunamadı: {kurum} (site: {site or "yok"}, aday: {len(adaylar)})')
    return None
