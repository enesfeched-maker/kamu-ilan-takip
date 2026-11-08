"""Başvurusu biten ilanların sonuç duyurularını kurumların kendi sitelerinden bulur (docs/sonuclar.json + /sonuclar/ + kanal).

SBB, ÇŞB, İŞKUR ve Kariyer Kapısı sonuç yayımlamıyor (9 Kasım 2026 kontrolü); sonuçlar kurum sitesinde çıkıyor. Yanlış duyuru
vermemek için dar eşleşme: bağlantı yazısı sonuç ifadesi taşımalı, tarihi ilanın son başvurusundan eski olmamalı ve ilana
bağlanabilmeli. Tarihsiz bağlantı yalnız siteyi önceki taramadan bildiğimizde yeni çıkmışsa alınır.

Kullanım: python bot/sonuc_takip.py [--kuru]   (--kuru: yazmaz, kanala göndermez)"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
ROOT = Path(__file__).resolve().parent.parent
VERI = ROOT / 'docs' / 'sonuclar.json'
TAKIP_GUN = 120
EN_COK_KANAL = 3
KANAL_EN_ESKI_GUN = 3
EN_AZ_DIZIN_KAYDI = 10   # bundan az kayıtta sayfa ince içerik sayılır, dizine girmez (AdSense kuralı)
EN_COK_BELLEK = 300
AJAN = 'kamu-ilan-takip/1.0 (+https://kpsstercihi.com/)'
AYLAR = ['ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik']
AYLAR_AD = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

SONUC = re.compile(r'\bsonuc(?:u|lari|larina|larinin)?\b|hak kazanan|basarili olan|kazanan aday|asil ve yedek|asil yedek|yerlesen aday')
BAGLAM = re.compile(r'\b(?:memur|personel|isci|sozlesmeli|sinav\w*|aday\w*|alim\w*)\b')
HARIC = re.compile(r'gorevde yukselme|unvan degisikligi|ihale|ogrenci|burs|staj|proje|hibe|secim|anket|faaliyet|denetim|ogretim|akademik'
                   r'|dekan|arastirma|yarismasi|sonucunda|sonuclanan|sonuc raporu|muhtar|kiralama|satis')
GENEL = frozenset('''alim alimi ilan ilani personel sozlesmeli memur isci kadro sinav aday kamu belediye belediyesi baskanligi universitesi
genel mudurlugu bakanligi kurumu ilk defa atanmak uzere yili icin olan'''.split())
SITE = re.compile(r'(?:https?://)?((?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:gov|bel|edu|org)\.tr)\b', re.I)
SITE_DEGIL = re.compile(r'kariyerkapisi|turkiye\.gov|osym|iskur|yok\.gov|nvi\.gov|resmigazete|sbb\.gov|csb\.gov|e-?devlet|ptt\.gov|ziraat')


def katla(metin):
    metin = html.unescape(metin or '').replace('I', 'ı').replace('İ', 'i').lower()
    for a, b in zip('çğıöşüâîû', 'cgiosuaiu'):
        metin = metin.replace(a, b)
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9/.-]+', ' ', metin)).strip()


def _gecerli_tarih(gun, ay, yil):
    try:
        return date(yil, ay, gun)
    except ValueError:
        return None


def tarih_bul(metin):
    """Bağlantı yazısı ya da adresindeki açık tarih; yoksa None. Tahmin yok."""
    k = katla(metin)
    m = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b', k)
    if m:
        return _gecerli_tarih(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r'\b(\d{1,2}) (' + '|'.join(AYLAR) + r') (20\d{2})\b', k)
    if m:
        return _gecerli_tarih(int(m[1]), AYLAR.index(m[2]) + 1, int(m[3]))
    return None


def sonuc_mu(yazi):
    k = katla(yazi)
    return bool(SONUC.search(k) and BAGLAM.search(k) and not HARIC.search(k))


def baglantilar(sayfa, adres):
    """Sayfadaki (mutlak adres, düz yazı) çiftleri; yalnız http(s)."""
    sonuc, gorulen = [], set()
    for href, ic in re.findall(r'<a\b[^>]*?href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', sayfa, re.S | re.I):
        yazi = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', ic))).strip()
        tam = urllib.parse.urljoin(adres, html.unescape(href).strip())
        if yazi and tam not in gorulen and urllib.parse.urlsplit(tam).scheme in ('http', 'https'):
            gorulen.add(tam)
            sonuc.append((tam, yazi))
    return sonuc


def ayirt_edici(ilan):
    return {k for k in re.findall(r'[a-z]{4,}', katla(' '.join(str(ilan.get(a) or '') for a in ('baslik', 'kadro')))) if k not in GENEL}


def ilana_bagla(yazi, ilanlar):
    """Bağlantıyı ilana bağlar: ayırt edici kelime ortaksa onunla, sitede tek ilan varsa ona; belirsizse None."""
    kelimeler = set(re.findall(r'[a-z]{4,}', katla(yazi)))
    ortak = [(len(ayirt_edici(i) & kelimeler), i.get('son_tarih') or '', n) for n, i in enumerate(ilanlar)]
    ortak = [o for o in ortak if o[0]]
    if ortak:
        return ilanlar[max(ortak)[2]]
    return ilanlar[0] if len(ilanlar) == 1 else None


def yeni_sonuclar(bag, ilanlar, gorulen):
    """(kayıtlar, güncel görülen küme). gorulen None ise site ilk kez taranıyor: tarihsiz bağlantılar yalnız ezberlenir."""
    kayitlar, bilinen = [], set(gorulen or ())
    for adres, yazi in bag:
        if adres in bilinen or not sonuc_mu(yazi):
            continue
        bilinen.add(adres)
        tarih = tarih_bul(yazi) or tarih_bul(urllib.parse.unquote(adres))
        if tarih is None and gorulen is None:
            continue
        ilan = ilana_bagla(yazi, ilanlar)
        if ilan is None or (tarih and tarih.isoformat() < str(ilan.get('son_tarih') or '')):
            continue
        kayitlar.append((ilan, adres, yazi, tarih))
    return kayitlar, bilinen


def bugun():
    return datetime.now(TR).date()


def takip_edilenler(ilanlar, gun=None):
    gun = gun or bugun()
    alt = (gun - timedelta(days=TAKIP_GUN)).isoformat()
    return [i for i in ilanlar if i.get('kategori') != 'akademik' and not i.get('duyuru_turu') and not i.get('iptal_edildi')
            and not i.get('kurum_ici') and i.get('son_tarih') and alt <= i['son_tarih'] < gun.isoformat()]


def ilan_metni(ilan):
    parca = [str(ilan.get(a) or '') for a in ('basvuru_notu', 'ozet', 'duyuru_cumlesi')]
    parca += [str(s.get('metin') or '') for s in ilan.get('sartlar') or []]
    return ' '.join(parca)


def site_bul(ilan, metin=None):
    """Metinde geçen ilk kurum sitesi; yoksa belediye için ad.bel.tr adayı (site_dogrula ile sınanır)."""
    for s in SITE.findall(metin if metin is not None else ilan_metni(ilan)):
        if not SITE_DEGIL.search(s.lower()):
            return s.lower().strip('.')
    m = re.match(r'([^\W\d_]+)(?:\s*\([^)]*\))?\s+BELEDİYE', (ilan.get('kurum') or '').strip(), re.I)
    return katla(m[1]) + '.bel.tr' if m else None


def indir(adres, zaman=12):
    with urllib.request.urlopen(urllib.request.Request(adres, headers={'User-Agent': AJAN}), timeout=zaman) as y:
        ham = y.read(1_200_000)
        kod = y.headers.get_content_charset() or 'utf-8'
    try:
        return ham.decode(kod)
    except (LookupError, UnicodeDecodeError):
        return ham.decode('windows-1254', 'ignore')


def site_dogrula(site, sayfa, ilan):
    """Tahminî .bel.tr adresi gerçekten bu belediyenin mi: ilk kelime sayfa başlığında geçmeli."""
    if not site.endswith('.bel.tr'):
        return True
    m = re.search(r'<title[^>]*>(.*?)</title>', sayfa, re.S | re.I)
    return bool(m) and site.split('.')[0].replace('www', '') in katla(m[1]).replace(' ', '')


def veri_oku(yol=VERI):
    try:
        return json.loads(Path(yol).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'gorulen': {}, 'sonuclar': []}


def adres_ozu(adres):
    """Aynı duyurunun www'li/www'siz adresi tek kayıt olsun."""
    p = urllib.parse.urlsplit(adres)
    return re.sub(r'^www\.', '', p.netloc.lower()) + p.path.rstrip('/') + ('?' + p.query if p.query else '')


def baslik_temiz(yazi):
    """Duyuru listelerinde başlığa yapışan tarih ve önizleme metni atılır."""
    m = re.search(r'\s+\d{1,2}(?:[./-]\d{1,2}[./-]20\d{2}| [^\W\d_]+ 20\d{2})\b', yazi)
    return (yazi[:m.start()] if m and m.start() > 15 else yazi).strip()[:200]


def kayit_yap(ilan, adres, yazi, tarih, simdi):
    from kurum_sayfasi import anahtar
    return {'id': ilan['id'], 'key': anahtar(ilan), 'kurum': ilan.get('kurum') or '', 'baslik': baslik_temiz(yazi), 'adres': adres,
            'tarih': tarih.isoformat() if tarih else None, 'ilk_gorulme': simdi.isoformat(timespec='seconds'), 'kanal': False}


def tara(ilanlar, veri, indirici=indir, simdi=None, bekle=1.0):
    """Siteleri gezer, veri'yi günceller; yeni kayıtları döner. Erişilemeyen site bu turda atlanır, ezber bozulmaz."""
    simdi = simdi or datetime.now(TR)
    siteler = {}
    for i in takip_edilenler(ilanlar, simdi.date()):
        s = site_bul(i)
        if s:
            grup = siteler.setdefault(re.sub(r'^www\.', '', s), [])
            if not any(g.get('son_tarih') == i['son_tarih'] for g in grup):   # aynı ilanın başka kaynaktaki kopyası
                grup.append(i)
    yeni, bilinen = [], {adres_ozu(k['adres']) for k in veri['sonuclar']}
    for site, grup in siteler.items():
        gorulen = veri['gorulen'].get(site)
        bag = []
        for yol in ('', 'duyurular'):
            adres = f'https://{site}/{yol}'
            try:
                sayfa = indirici(adres)
            except Exception:
                continue
            if not yol and not site_dogrula(site, sayfa, grup[0]):
                bag = []
                break
            bag += baglantilar(sayfa, adres)
            time.sleep(bekle)
        if not bag:
            continue
        kayitlar, ezber = yeni_sonuclar(bag, grup, gorulen)
        veri['gorulen'][site] = sorted(ezber)[-EN_COK_BELLEK:]
        for ilan, adres, yazi, tarih in kayitlar:
            if adres_ozu(adres) not in bilinen:
                bilinen.add(adres_ozu(adres))
                yeni.append(kayit_yap(ilan, adres, yazi, tarih, simdi))
    veri['sonuclar'] = sorted(veri['sonuclar'] + yeni, key=lambda k: k['ilk_gorulme'], reverse=True)[:EN_COK_BELLEK]
    return yeni


def kanal_metni(ilan, baslik=''):
    from ilan_bot import ilan_adi
    tur = 'aday listesi' if 'hak kazanan' in katla(baslik) else 'sonuç duyurusu'
    return f'🏁 <b>{html.escape(ilan_adi(ilan))} ilanı için {tur} yayımlandı.</b>'


def kanala_gonder(metin, adres, yanit, token, sohbet):
    alanlar = {'chat_id': sohbet, 'text': metin, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true',
               'reply_markup': json.dumps({'inline_keyboard': [[{'text': 'Sonuç duyurusunu aç', 'url': adres, 'style': 'success'}]]}, ensure_ascii=False)}
    if yanit:
        alanlar['reply_parameters'] = json.dumps({'message_id': int(yanit), 'allow_sending_without_reply': True})
    istek = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=urllib.parse.urlencode(alanlar).encode())
    with urllib.request.urlopen(istek, timeout=30) as y:
        return bool(json.load(y).get('ok'))


def kanala_paylas(veri, ilanlar, mesajlar, token, sohbet, gonderici=kanala_gonder, gun=None):
    """Paylaşılmamış kayıtları en eskiden başlayarak gönderir; ilanı kanalda olan kayıt orijinal mesaja yanıt olur."""
    harita, adet, gonderilen = {i['id']: i for i in ilanlar}, 0, set()
    alt = (gun or bugun()) - timedelta(days=KANAL_EN_ESKI_GUN)
    for k in sorted(veri['sonuclar'], key=lambda k: (k.get('tarih') or k['ilk_gorulme'][:10], k['ilk_gorulme']), reverse=True):
        ilan = harita.get(k['id'])
        if k.get('kanal') or not ilan:
            continue
        if (k.get('tarih') and k['tarih'] < alt.isoformat()) or k['id'] in gonderilen:   # eski duyuru ve aynı ilanın ikinci listesi kanala gitmez
            k['kanal'] = True
            continue
        if adet >= EN_COK_KANAL:
            break
        try:
            tamam = gonderici(kanal_metni(ilan, k.get('baslik', '')), k['adres'], mesajlar.get(k['id']), token, sohbet)
        except Exception as hata:
            print(f'Uyarı: sonuç kanala gönderilemedi: {type(hata).__name__}')
            tamam = False
        if tamam:
            k['kanal'] = True
            adet += 1
            gonderilen.add(k['id'])
    return adet


def _tarih_yaz(gun):
    d = date.fromisoformat(gun[:10])
    return f'{d.day} {AYLAR_AD[d.month - 1]} {d.year}'


def sayfa(veri, base):
    """(adres, html, dizine girsin mi) — kurum sitelerinde yayımlanan sonuç duyuruları."""
    import site_uret as su
    canonical = base + 'sonuclar/'
    kayitlar = veri.get('sonuclar') or []
    dizin = len(kayitlar) >= EN_AZ_DIZIN_KAYDI
    satirlar = ''.join(
        f'<li><a href="{su.esc(k["adres"])}" target="_blank" rel="noopener nofollow">{su.esc(k["baslik"])}</a>'
        f'<br><small>{su.esc(k["kurum"])} · {_tarih_yaz(k["tarih"] or k["ilk_gorulme"])}</small></li>' for k in kayitlar)
    icerik = f'<ul>{satirlar}</ul>' if kayitlar else '<p>Henüz sonuç duyurusu bulunmadı.</p>'
    ek = f'<meta property="og:url" content="{su.esc(canonical)}">' + ('' if dizin else '<meta name="robots" content="noindex,follow">')
    govde = (su.sayfa_basi('Kamu Personel Alımı Sonuç Duyuruları — KPSS Tercihi', 'Kamu kurumlarının personel alımı sınav ve yerleştirme sonuç duyuruları, resmî kurum bağlantılarıyla.',
                           su.esc(canonical), '../', ek_head=ek)
             + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html("../")}'
             + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a><span aria-hidden="true">/</span>'
             + '<span>Sonuç duyuruları</span></nav><h1>Sonuç duyuruları</h1><p>Bağlantılar kurumun kendi sitesine gider.</p></div></section>'
             + f'<main id="icerik" class="wrap kp-main">{icerik}</main>{su.alt_html("../")}</body></html>')
    return canonical, govde, dizin


def yaz(docs, base):
    """Sayfayı yazar; dizine girecekse site haritası için adresini döner."""
    adres, govde, dizin = sayfa(veri_oku(Path(docs) / 'sonuclar.json'), base)
    (Path(docs) / 'sonuclar').mkdir(exist_ok=True)
    (Path(docs) / 'sonuclar' / 'index.html').write_text(govde, encoding='utf-8')
    return [adres] if dizin else []


def calistir(kuru=False):
    kaynak = json.loads((ROOT / 'docs' / 'ilanlar.json').read_text(encoding='utf-8'))
    veri = veri_oku()
    yeni = tara(kaynak['ilanlar'], veri)
    print(f'{len(yeni)} yeni sonuç duyurusu; {len(veri["gorulen"])} site izleniyor.')
    for k in yeni:
        print(f'- {k["kurum"]}: {k["baslik"]} → {k["adres"]}')
    if kuru:
        return
    token, sohbet = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if token and sohbet:
        print(f'{kanala_paylas(veri, kaynak["ilanlar"], kaynak.get("telegram_mesajlari", {}), token, sohbet)} duyuru kanala gönderildi.')
    VERI.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    calistir('--kuru' in sys.argv)
