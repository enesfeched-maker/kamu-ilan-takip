"""Generate crawlable public detail pages from the existing verified registry."""
import html
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://enesfeched-maker.github.io/kamu-ilan-takip/'
TR = timezone(timedelta(hours=3))
KART_GENISLIK = 720
LOGO_BOYUT = 128
EN_COK_LOGO_INDIRME = 150


def esc(value):
    return html.escape(str(value or ''), quote=True)


def detail_page(item, gorsel=None):
    from siniflandir import akademik_ilan
    if akademik_ilan(item):
        return None  # akademik ilanlar sitede gösterilmez
    url = urlparse(item.get('link', ''))
    key = parse_qs(url.query).get('i', [''])[0]
    import uuid
    try:
        key = str(uuid.UUID(key))
    except ValueError:
        import re
        key = item.get('id', '')
        if not re.fullmatch(r'(?:(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})', key):
            return None
    if url.scheme != 'https' or url.hostname not in {'kariyerkapisi.gov.tr','kamuilan.sbb.gov.tr','www.iskur.gov.tr','iskur.gov.tr','yerelyonetimler.csb.gov.tr'} or url.username or url.password:
        return None
    canonical = BASE + 'ilan/' + key + '/'
    title = item.get('baslik', 'Kamu ilanı')
    deadline = item.get('son_zaman') or item.get('son_tarih')
    end = datetime.fromisoformat(deadline) if deadline else None
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=TR, hour=23, minute=59, second=59)
    status = 'Başvuru sona erdi' if end and end <= datetime.now(TR) else 'Son tarihi resmî ilandan doğrula'
    if item.get('duyuru_turu'):
        status = esc(item['duyuru_turu'])
    if item.get('iptal_edildi'):
        status = 'İptal edildi'
    date = end.astimezone(TR).strftime('%d.%m.%Y · %H:%M TSİ' if item.get('son_zaman') else '%d.%m.%Y') if end else 'Belirtilmemiş'
    sections = ''
    if item.get('iptal_edildi'):
        sections += '<p class="notice"><strong>İptal edildi.</strong> Bu ilan için resmî iptal duyurusu yayımlandı. Başvuru yapmadan önce resmî kaynağı kontrol et.</p>'
    for heading, value in [('Kadro ve kontenjan', item.get('kadro')), ('Duyuru metni', item.get('duyuru_cumlesi')), ('İlan özeti', None if item.get('ozet') == item.get('duyuru_cumlesi') else item.get('ozet')),('Başvuru notu', item.get('basvuru_notu'))]:
        if value:
            sections += f'<h3>{heading}</h3><p>{esc(value)}</p>'
    if item.get('sartlar'):
        sections += '<h3>Başvuru koşullarından seçmeler</h3>'
    for s in item.get('sartlar', []):
        sections += f'<section class="condition"><h4>{esc(s.get("kadro"))}</h4><p>{esc(s.get("metin"))}</p></section>'
    if any(item.get(k) for k in ('kadro', 'duyuru_cumlesi', 'ozet', 'basvuru_notu', 'sartlar')):
        sections += '<p class="muted">Seçilmiş alıntılardır. Tüm koşullar, kadrolar ve güncel tarihler için resmî ilanı incele.</p>'
    else:
        sections += '<p class="muted">Bu ilanın kadro, şart ve başvuru ayrıntıları henüz kaynaktan okunamadı. Tüm bilgiler için resmî ilan belgesini aç.</p>'
    for belge in item.get('belgeler', [])[:3]:
        if str(belge.get('link', '')).startswith('https://webdosya.csb.gov.tr/v2/yerelyonetimler/'):
            sections += f'<p><a class="text-link" href="{esc(belge["link"])}" target="_blank" rel="noopener noreferrer">Duyuru eki: {esc(belge.get("ad"))} ↗</a></p>'
    description = (item.get('kurum', '') + ' — ' + (item.get('kadro') or title))[:190]
    gorsel = gorsel or {}
    og_gorsel = kart_html = ''
    kurum_adi = esc(item.get('kurum') or 'Kurum')
    if gorsel.get('kart'):
        kart_url = esc(BASE + gorsel['kart'])
        og_gorsel = f'<meta property="og:image" content="{kart_url}"><meta property="og:image:width" content="{KART_GENISLIK}"><meta property="og:image:height" content="{gorsel.get("kart_yukseklik", 900)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{kart_url}">'
        kart_html = f'<div class="detail-visual"><img class="detail-card-img" src="../../{esc(gorsel["kart"])}" alt="{kurum_adi} ilan görseli" width="{KART_GENISLIK}" height="{gorsel.get("kart_yukseklik", 900)}" decoding="async" fetchpriority="high"></div>'
    if gorsel.get('logo'):
        logo_html = f'<img class="detail-logo" src="../../{esc(gorsel["logo"])}" alt="{kurum_adi} logosu" width="64" height="64">'
    else:
        logo_html = f'<span class="detail-logo institution-badge" style="--h:{_ton(item.get("kurum"))}" aria-hidden="true">{esc(_bas_harfler(item.get("kurum")))}</span>'
    from sbb_detay import document_url
    document=document_url(item)
    target=document or item['link']
    button='İlan belgesini aç (PDF) ↗' if document else 'Resmî ilana git · Başvur ↗'
    if document:
        sections += f'<p class="muted">{esc(item.get("belge_aciklamasi"))}</p>'
    durum_sinifi = ' closed cancelled' if item.get('iptal_edildi') else ' closed' if end and end <= datetime.now(TR) else ''
    durum_html = f'<strong class="status-badge{durum_sinifi}">{status}</strong>'
    if not (item.get('iptal_edildi') or item.get('duyuru_turu')) and end and end > datetime.now(TR) and item.get('son_tarih'):
        durum_html = f'<strong class="status-badge" id="durum" data-son="{esc(item["son_tarih"])}" data-zaman="{esc(item.get("son_zaman") or "")}">{status}</strong>'
    yer = esc(_duzgun(item.get('yer')) or 'Resmî ilandan kontrol et')
    gorunum = '<script>try{var t=JSON.parse(localStorage.getItem("kit-theme"));if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}catch(e){}</script>'
    sayac = ('<script>(function(){var e=document.getElementById("durum");if(!e)return;var z=e.dataset.zaman;if(z&&Date.parse(z)<=Date.now()){e.textContent="Başvuru sona erdi";e.className+=" closed";return}'
             'var t=new Date().toLocaleDateString("sv-SE",{timeZone:"Europe/Istanbul"}),d=Math.round((Date.parse(e.dataset.son+"T00:00:00Z")-Date.parse(t+"T00:00:00Z"))/864e5);if(isNaN(d))return;'
             'if(d<0){e.textContent="Başvuru sona erdi";e.className+=" closed";return}e.textContent=d===0?"Bugün son gün":d===1?"Yarın son gün":d+" gün kaldı";e.className+=d<=1?" urgent today":d<=3?" urgent":d<=7?" soon":""})()</script>')
    return key, f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#102e35"><meta name="color-scheme" content="light dark"><title>{esc(title)} | Kamu İlan Takip</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="article">{og_gorsel}{gorunum}<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700;800&amp;display=swap"><link rel="stylesheet" href="../../portal.css?v=6"><link rel="icon" href="../../assets/logo-192.png?v=1" type="image/png"></head><body class="detail-page"><a class="skip" href="#icerik">İçeriğe geç</a><div class="topline"><div class="container">Kariyer Kapısı · İŞKUR · SBB · ÇŞB Yerel Yönetimler — Bağımsız ilan rehberi <span>Başvurular resmî ilan üzerinden yapılır.</span></div></div><header class="header"><div class="container header-inner"><a class="brand" href="../../" aria-label="Kamu İlan Takip ana sayfa"><img class="brand-logo" src="../../assets/logo-96.webp?v=1" alt="" width="44" height="44"><span>Kamu İlan<span class="brand-sub">TAKİP</span></span></a><nav aria-label="Ana menü"><a href="../../#ilanlar">Tüm ilanlar</a><a href="../../#rehber">Başvuru rehberi</a><a href="../../puanlar/">Taban puanları</a></nav><div class="header-actions"><a class="button primary small" href="https://t.me/kamuilantakip" target="_blank" rel="noopener">Telegram'a katıl ↗</a></div></div></header><section class="detail-hero"><div class="container detail-hero-grid{' has-visual' if kart_html else ''}"><div class="detail-hero-copy"><nav class="crumbs" aria-label="Konum"><a href="../../">Ana sayfa</a><span aria-hidden="true">/</span><a href="../../#ilanlar">İlanlar</a></nav><div class="detail-org">{logo_html}<p>{esc(_duzgun(item.get('kurum')))}</p></div><span class="eyebrow">{esc(item.get('ilan_turu','KAMU İLANI'))}</span><h1>{esc(_gorunen_baslik(item))}</h1><ul class="detail-facts"><li><span>Durum</span>{durum_html}</li><li><span>Son başvuru</span><strong>{date}</strong></li><li><span>Görev yeri</span><strong>{yer}</strong></li></ul><div class="detail-cta"><a class="button lime" href="{esc(target)}" target="_blank" rel="noopener noreferrer">{button}</a><a class="button ghost" href="../../#ilan/{key}">Kaydet ve karşılaştır</a></div></div>{kart_html}</div></section><main id="icerik" class="container detail-main"><div class="detail-layout"><article class="detail-content"><p class="notice">Bilgiler kayıtlı kaynak özetini yansıtır. Güncel durum ve başvuru şartlarında resmî ilan esas alınır.</p>{sections}<p class="muted">Ayrıntı kontrolü: {esc(item.get('detay_guncelleme','Tarih belirtilmemiş'))}</p></article><aside class="detail-aside"><h2>Başvuru</h2><dl><dt>Son başvuru</dt><dd>{date}</dd><dt>Görev yeri</dt><dd>{yer}</dd></dl><a class="button primary" href="{esc(target)}" target="_blank" rel="noopener noreferrer">{button}</a><a class="button secondary" href="../../#ilan/{key}">Kaydet, paylaş ve karşılaştır</a><a class="button secondary" href="https://t.me/kamuilantakip" target="_blank" rel="noopener">Telegram'dan takip et ↗</a><p class="muted">Başvuru bu sitede yapılmaz; işlemini ilanda belirtilen resmî kanaldan tamamla.</p></aside></div><section class="trust-strip"><strong>Başka fırsatlara da göz at.</strong><p>Açık ilanları son tarihe göre sırala, kaydet ve karşılaştır.</p><a class="button primary" href="../../">İlanları keşfet →</a></section></main><footer class="footer"><div class="container footer-bottom"><span>© Kamu İlan Takip</span><span>Kamu İlan Takip resmî bir hizmet değildir. Başvurunu ilanda belirtilen resmî kanaldan tamamla.</span></div></footer>{sayac}</body></html>'''


def _duzgun(metin):
    """portal.js proper(): Türkçe kurallarıyla küçült, kelime başlarını büyüt."""
    import re
    kucuk = str(metin or '').replace('I', 'ı').replace('İ', 'i').lower()
    buyut = lambda h: 'İ' if h == 'i' else 'I' if h == 'ı' else h.upper()
    sonuc = re.sub(r'(^|[\s(/-])([a-zçğıöşü])', lambda m: m.group(1) + buyut(m.group(2)), kucuk)
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
    urls = [BASE]
    count = 0
    from siniflandir import akademik_ilan
    gorseller = {}
    try:
        gorseller = gorselleri_uret(data.get('ilanlar', []), docs, datetime.now(TR))
    except Exception as hata:
        print(f'Uyarı: ilan görselleri üretilemedi: {hata}')
    (docs / 'ilan').mkdir(parents=True, exist_ok=True)
    (docs / 'ilan' / 'gorseller.json').write_text(json.dumps(gorseller, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for item in data.get('ilanlar', []):
        result = detail_page(item)
        if not result:
            if akademik_ilan(item):
                _sayfayi_kaldir(docs, item)
            continue
        result = detail_page(item, gorseller.get(result[0]))
        key, content = result
        folder = docs / 'ilan' / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(content, encoding='utf-8')
        urls.append(BASE + 'ilan/' + key + '/')
        count += 1
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
