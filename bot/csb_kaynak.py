"""ÇŞB Yerel Yönetimler duyurularındaki belediye personel alım ilanları ve iptal/düzeltme duyuruları.

Yalnızca yerel (Türkiye IP'li) tarayıcıdan çalıştırılır; GitHub Actions bu siteye erişemez.
Resmî kaynakta açıkça yazmayan bilgi (ör. son başvuru tarihi) tahmin edilmez, boş bırakılır."""
import io
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date

from bs4 import BeautifulSoup

from ek_kaynaklar import MONTHS, clean, fresh, kind, norm, notice, now, pdf_text
from siniflandir import ILLER, kucuk

SITE = 'https://yerelyonetimler.csb.gov.tr/'
LISTE = SITE + 'duyurular'
SAYFA_SAYISI = 2           # her sayfada ~12 duyuru; 30 dakikalık tarama için yeterli
KAYNAK_ADI = 'ÇŞB Yerel Yönetimler'
# Ayrıştırma mantığı değişince VERSIYON artırılır (önbellekteki eski kayıtlar yeniden okunur).
VERSIYON = 2
HOSTLAR = {'yerelyonetimler.csb.gov.tr', 'webdosya.csb.gov.tr'}
SAYFA_SINIRI = 1_500_000
BELGE_SINIRI = 8_000_000
XML_SINIRI = 6_000_000
AZAMI_BELGE = 3
AZAMI_DETAY = 25           # tek taramada en çok bu kadar yeni duyurunun ayrıntısı okunur
AYLAR = [norm(m).strip() for m in MONTHS]
EK_ADRESI = re.compile(r'^https://webdosya\.csb\.gov\.tr/v2/yerelyonetimler/\d{4}/\d{2}/[^?#\s]+\.(?:docx|pdf)$', re.I)
KURUM = re.compile(r'^(?:(?P<il>\S+)\s+İLL?İ\s+)?(?P<ad>.+?)\s+'
                   r'(?P<tur>BELEDİYE\s+BAŞKANLIĞI(?:NA)?|BELEDİYESİ(?:NE)?|BELEDİYE|GENEL\s+MÜDÜRLÜ[ĞG]Ü(?:NE)?)\b\s*(?P<kalan>.*)$')
ARALIK = re.compile(r'(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})\s*[-–—]\s*'
                    r'(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})\s*tarihleri\s+aras')


def guvenli_adres(deger, taban=''):
    adres = urllib.parse.urljoin(taban, deger)
    p = urllib.parse.urlsplit(adres)
    if p.scheme != 'https' or p.hostname not in HOSTLAR or p.username or p.password:
        raise ValueError('Resmî kaynak dışı bağlantı')
    yol = urllib.parse.quote(urllib.parse.unquote(p.path), safe='/')
    return urllib.parse.urlunsplit((p.scheme, p.netloc, yol, p.query, ''))


class _Yonlendirme(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        guvenli_adres(newurl, req.full_url)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def indir(adres, sinir=SAYFA_SINIRI):
    istek = urllib.request.Request(guvenli_adres(adres), headers={
        'User-Agent': 'kamu-ilan-takip/1.0 (+https://enesfeched-maker.github.io/kamu-ilan-takip/)'})
    with urllib.request.build_opener(_Yonlendirme()).open(istek, timeout=25) as yanit:
        veri = yanit.read(sinir + 1)
    if len(veri) > sinir:
        raise ValueError('Kaynak dosya boyutu sınırı aşıldı')
    return veri


def _belge(veri):
    return BeautifulSoup(veri.decode('utf-8-sig') if isinstance(veri, bytes) else veri, 'html.parser')


def tarih_coz(metin):
    """'29 Eylül 2026 Salı' -> '2026-09-29'; okunamazsa None."""
    m = re.search(r'(\d{1,2})\s+(' + '|'.join(AYLAR) + r')\s+(20\d{2})', norm(metin))
    if not m:
        return None
    try:
        return date(int(m.group(3)), AYLAR.index(m.group(2)) + 1, int(m.group(1))).isoformat()
    except ValueError:
        return None


def liste_ayristir(veri):
    belge = _belge(veri)
    # İki yerleşim var: üstteki son duyuru kaydırıcısı ve sayfalanan kart listesi.
    kutular = belge.select('a.duyurular-wrapper[href], a.duyurular-category-card-wrapper[href]')
    if not kutular:
        raise ValueError('ÇŞB duyuru listesi bulunamadı')
    satirlar = {}
    for a in kutular:
        try:
            adres = guvenli_adres(a['href'], SITE)
        except ValueError:
            continue    # site dışı bağlantılı tek kart atlanır; sayfa düşmez
        numara = re.search(r'-duyuru-(\d+)$', urllib.parse.urlsplit(adres).path)
        baslik = a.select_one('.info p, .duyurular-category-card-body-wrapper p')
        tarih = a.select_one('.date, .duyurular-category-card-body-wrapper span')
        if not numara or not baslik:
            continue
        satirlar.setdefault(numara.group(1), {
            'numara': numara.group(1), 'link': adres,
            'baslik': clean(baslik.get_text(' ')).rstrip('.').strip(),
            'yayim': tarih_coz(tarih.get_text(' ')) if tarih else None})
    if not satirlar:
        raise ValueError('ÇŞB duyuru satırı değişti')
    return list(satirlar.values())


def buyuk(metin):
    return clean(metin).replace('i', 'İ').replace('ı', 'I').upper()


def il_bul(ad):
    for il in ILLER:
        if kucuk(il) == kucuk(ad):
            return il
    return None


def duyuru_turu(baslik):
    if not notice(baslik):
        return None
    return 'İptal duyurusu' if 'iptal' in norm(baslik) else 'Düzeltme / süre değişikliği'


def baslik_coz(baslik):
    """Başlıktan il, belediye adı ve kalan metni çıkarır; bulunamayanı boş bırakır (tahmin yok)."""
    metin = buyuk(baslik)
    m = KURUM.match(metin)
    if not m:
        return {'il': None, 'kurum': '', 'kalan': metin}
    il = il_bul(m.group('il')) if m.group('il') else None
    ad = m.group('ad')
    if not m.group('il') and len(ad.split()) == 1:
        il = il_bul(ad)    # 'ZONGULDAK BELEDİYESİ' gibi il merkezi belediyeleri
    ham = m.group('tur')
    if ham.startswith('GENEL'):
        tur = 'GENEL MÜDÜRLÜĞÜ'
    else:
        tur = 'BELEDİYE BAŞKANLIĞI' if ham.startswith('BELEDİYE B') else 'BELEDİYESİ'
    return {'il': il, 'kurum': ad + ' ' + tur, 'kalan': m.group('kalan').strip()}


def detay_ayristir(veri):
    belge = _belge(veri)
    h1 = belge.select_one('h1.general-content-wrapper') or belge.find('h1')
    aciklama = belge.select_one('.haber-detay-desc-wrapper')
    ekler = []
    for a in belge.select('a[href]'):
        adres = a['href'].strip()
        # Her sayfada bulunan sabit 'belediye-meclisi...pdf' bağlantısı bu kalıba uymaz; ilan eki sayılmaz.
        if EK_ADRESI.match(adres) and adres not in ekler:
            ekler.append(adres)
    return {'baslik': clean(h1.get_text(' ')).rstrip('.') if h1 else '',
            'aciklama': clean(aciklama.get_text(' '))[:600] if aciklama else '',
            'ekler': ekler[:AZAMI_BELGE]}


def docx_metni(veri):
    with zipfile.ZipFile(io.BytesIO(veri)) as z:
        bilgi = z.getinfo('word/document.xml')
        if bilgi.file_size > XML_SINIRI:
            raise ValueError('Belge metni boyut sınırını aşıyor')
        xml = z.read(bilgi)
    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
        raise ValueError('Beklenmeyen belge yapısı')
    w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    satirlar = []
    for p in ET.fromstring(xml).iter(w + 'p'):
        parca = []
        for e in p.iter():
            if e.tag == w + 't':
                parca.append(e.text or '')
            elif e.tag in (w + 'tab', w + 'br'):
                parca.append(' ')
        satir = clean(''.join(parca))
        if satir:
            satirlar.append(satir)
    return '\n'.join(satirlar)


def belge_metni(adres, veri):
    return docx_metni(veri) if adres.lower().endswith('.docx') else pdf_text(veri)


ARALIK_KADAR = re.compile(r'(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})\s*tarihinden\s+'
                          r'(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})\s*tarih(?:ine|i)\b[^.\n]{0,40}?\bkadar')


def _gun(g, a, y):
    try:
        return date(int(y), int(a), int(g))
    except ValueError:
        return None


def son_basvuru(metin):
    """Yalnızca açıkça yazılı tarihi döndürür: 'son başvuru ... <tarih>' ya da
    'başvurular <tarih> - <tarih> tarihleri arasında' (bitiş günü). Belirsizse (birden çok farklı tarih) None."""
    n = norm(metin)
    acik = set()
    for g in re.finditer(r'son basvuru(?: tarihi| gunu)?\D{0,12}?(\d{1,2}) (\d{1,2}) (20\d{2})\b', n):
        acik.add(_gun(*g.groups()))
    for g in re.finditer(r'son basvuru(?: tarihi| gunu)?\D{0,12}?(\d{1,2}) (' + '|'.join(AYLAR) + r') (20\d{2})\b', n):
        acik.add(_gun(g.group(1), AYLAR.index(g.group(2)) + 1, g.group(3)))
    acik.discard(None)
    if acik:
        return next(iter(acik)).isoformat() if len(acik) == 1 else None
    bitisler = set()
    for g in ARALIK.finditer(metin):
        cumle = re.split(r'\n|\.\s', metin[max(0, g.start() - 250):g.start()])[-1]
        yazim = norm(cumle)
        if 'basvuru' not in yazim or 'sinav' in yazim:
            continue
        ilk, son = _gun(*g.group(1, 2, 3)), _gun(*g.group(4, 5, 6))
        if ilk and son and son >= ilk:
            bitisler.add(son)
    for g in ARALIK_KADAR.finditer(metin):
        onceki = re.split(r'\n|\.\s', metin[max(0, g.start() - 250):g.start()])[-1]
        sonraki = re.split(r'\n|\.\s', metin[g.end():g.end() + 400])[0]
        yazim = norm(onceki + ' ' + sonraki)
        if 'basvuru' not in yazim or 'sinav' in yazim:
            continue
        ilk, son = _gun(*g.group(1, 2, 3)), _gun(*g.group(4, 5, 6))
        if ilk and son and son >= ilk:
            bitisler.add(son)
    return next(iter(bitisler)).isoformat() if len(bitisler) == 1 else None


def kayit_olustur(satir, detay, tarih):
    baslik = detay['baslik'] or satir['baslik']
    parca = baslik_coz(baslik)
    kurum = parca['kurum']
    tur = duyuru_turu(baslik)
    ozet = [detay['aciklama']] if detay['aciklama'] else []
    if tarih:
        ozet.append('Son başvuru: ' + '.'.join(reversed(tarih.split('-'))) + '.')
    if detay['ekler'] and not detay['aciklama']:
        ozet.append('İlan metni, resmî duyuruya eklenen belgede yer alıyor.')
    kayit = {'id': 'csb-' + satir['numara'],
             'baslik': kurum + ' - ' + parca['kalan'] if kurum and parca['kalan'] else buyuk(baslik),
             'kurum': kurum, 'kadro': '', 'ilan_turu': kind(baslik), 'son_tarih': tarih,
             'kaynak': KAYNAK_ADI, 'kaynak_turu': 'csb', 'link': satir['link'],
             'kaynaklar': [{'ad': KAYNAK_ADI, 'link': satir['link']}],
             'yayim_tarihi': satir['yayim'],
             'detay_guncelleme': now().isoformat(timespec='seconds'),
             'csb_detay_surumu': VERSIYON, 'ozet': ' '.join(ozet),
             'belgeler': [{'ad': urllib.parse.unquote(e.rsplit('/', 1)[1]), 'link': e} for e in detay['ekler']]}
    if parca['il']:
        kayit['yer'] = parca['il']
    if tur:
        kayit['duyuru_turu'] = tur
    return kayit


def duyuru_oku(satir):
    detay = detay_ayristir(indir(satir['link']))
    tarihler = set()
    for ek in detay['ekler']:
        try:
            tarihler.add(son_basvuru(belge_metni(ek, indir(ek, BELGE_SINIRI))))
        except Exception as exc:
            print(f'ÇŞB ek belge okunamadı ({type(exc).__name__}): {ek.rsplit("/", 1)[-1][:60]}', flush=True)
    tarihler.discard(None)
    # Farklı belgeler çelişirse tarih yazılmaz.
    return kayit_olustur(satir, detay, next(iter(tarihler)) if len(tarihler) == 1 else None)


def csb_oku(onceki):
    """(kayıtlar, hata sayısı) döndürür; read_sbb ile aynı sözleşme. Liste hiç okunamazsa istisna atar."""
    onbellek = {i['id']: i for i in onceki.values()
                if i.get('kaynak_turu') == 'csb' and i.get('csb_detay_surumu') == VERSIYON and i.get('detay_guncelleme')}
    satirlar, hata = {}, 0
    for sayfa in range(1, SAYFA_SAYISI + 1):
        try:
            for s in liste_ayristir(indir(LISTE if sayfa == 1 else LISTE + '/' + str(sayfa))):
                satirlar.setdefault(s['numara'], s)
        except Exception as exc:
            hata += 1
            print(f'ÇŞB liste sayfası {sayfa} okunamadı ({type(exc).__name__}: {str(exc)[:100]})', flush=True)
    if not satirlar:
        raise RuntimeError('ÇŞB duyuru listesi okunamadı')
    # SBB ile aynı sözleşme: 12 saatten eski (ya da hiç olmayan) ayrıntılar yeniden okunur; yeni duyurular
    # önce, sonra en eski ayrıntı. Okunamazsa eski kayıt, detay_guncelleme'si değiştirilmeden korunur.
    okunacak = [n for n, s in satirlar.items() if not (onbellek.get('csb-' + n) and fresh(onbellek['csb-' + n]))]
    okunacak.sort(key=lambda n: (onbellek['csb-' + n]['detay_guncelleme'] if 'csb-' + n in onbellek else ''))
    okunacak = set(okunacak[:AZAMI_DETAY])
    kayitlar = []
    for n, s in satirlar.items():
        eski = onbellek.get('csb-' + n)
        if n not in okunacak:
            if eski:
                kayitlar.append(eski)
            continue
        try:
            kayitlar.append(duyuru_oku(s))
        except Exception as exc:
            hata += 1
            print(f'ÇŞB duyuru ayrıntısı ertelendi ({type(exc).__name__}: {str(exc)[:100]}): {s["baslik"][:60]}', flush=True)
            if eski:
                kayitlar.append(eski)
        time.sleep(.2)
    return kayitlar, hata


# --- Başka kaynaklarla (SBB/İŞKUR) ihtiyatlı eşleştirme -------------------------------------------
PENCERE_GUN = 7
KURUM_SOZLERI = {'belediye', 'belediyesi', 'baskanligi', 'baskanligina', 'ili', 'il', 'illi'}


def cekirdek(kurum, yer=None):
    """Belediye adının normalize çekirdeği ve (biliniyorsa) ili: ('sile', 'istanbul'). Belediye değilse None."""
    parantez = re.search(r'\(([^)]*)\)', kurum or '')
    n = norm(re.sub(r'\([^)]*\)', ' ', kurum or ''))
    if 'belediye' not in n:
        return None
    iller = {norm(x).strip() for x in ILLER}
    kelimeler = [k for k in n.split() if k not in KURUM_SOZLERI]
    if not kelimeler:
        return None
    il = il_bul(yer) if yer else None
    if not il and parantez:
        il = il_bul(parantez.group(1).strip())
    il = norm(il).strip() if il else None
    if 'buyuksehir' not in kelimeler and len(kelimeler) > 1 and kelimeler[0] in iller:
        il = il or kelimeler[0]
        kelimeler = kelimeler[1:]      # 'İstanbul Şile Belediyesi' -> 'şile'
    elif 'buyuksehir' in kelimeler and kelimeler[0] in iller:
        il = il or kelimeler[0]        # büyükşehir ayrımı korunur: 'istanbul buyuksehir'
    return ' '.join(kelimeler), il


def _kimlik(i):
    return cekirdek(i.get('kurum'), i.get('yer'))


def _isci(i):
    metin = norm(' '.join(str(i.get(a) or '') for a in ('baslik', 'kadro', 'ozet')))
    return bool(re.search(r'\bisci', metin))


def _uyumlu(a, b):
    x, y = _kimlik(a), _kimlik(b)
    if _isci(a) != _isci(b):      # sigorta: yalnız birinde 'işçi' geçiyorsa farklı ilan olabilir
        return False
    return bool(x and y and x[0] == y[0] and (not x[1] or not y[1] or x[1] == y[1]))


def _tur(i):
    return i.get('duyuru_turu') or duyuru_turu(i.get('baslik', ''))


def _gun_of(i):
    try:
        return date.fromisoformat((i.get('yayim_tarihi') or i.get('ilk_gorulme') or '')[:10])
    except ValueError:
        return None


def eslesme_ciftleri(kayitlar):
    """ÇŞB kaydı ile SBB/İŞKUR/Kariyer kaydı arasında yalnızca iki tarafta da TEK aday olan çiftleri döndürür:
    frozenset({csb_id, diger_id}) kümesi. Belirsizlikte eşleştirme yapılmaz (yanlış birleşme kayıptan kötü)."""
    havuz = {i['id']: i for i in kayitlar if i.get('id')}
    csb = [i for i in havuz.values() if i.get('kaynak_turu') == 'csb' and _kimlik(i)]
    diger = [i for i in havuz.values() if i.get('kaynak_turu') != 'csb' and _kimlik(i)]
    ciftler = set()
    # Alım ilanları: aynı çekirdek ad + aynı dolu son_tarih, her iki tarafta tek aday.
    anahtar = lambda i: (_kimlik(i)[0], i.get('son_tarih'))
    a_csb = [i for i in csb if not _tur(i) and i.get('son_tarih')]
    a_dig = [i for i in diger if not _tur(i) and i.get('son_tarih')]
    for c in a_csb:
        es = [d for d in a_dig if anahtar(d) == anahtar(c)]
        ters = [x for x in a_csb if anahtar(x) == anahtar(c)]
        # Aynı ilan SBB ve İŞKUR'da ayrı kayıt olabilir: kaynak başına en çok bir aday kabul edilir,
        # eşleşme SBB'ye (yoksa diğerine) yapılır. Aynı kaynakta birden çok aday varsa belirsizdir.
        turler = [d.get('kaynak_turu') for d in es]
        if es and len(set(turler)) == len(turler) and len(ters) == 1 and all(_uyumlu(c, d) for d in es):
            secilen = sorted(es, key=lambda d: {'sbb': 0, 'iskur': 1}.get(d.get('kaynak_turu'), 2))[0]
            ciftler.add(frozenset((c['id'], secilen['id'])))
    # İptal/düzeltme: aynı tür + çekirdek ad + yayım tarihi (±PENCERE_GUN gün), tek aday.
    n_csb = [i for i in csb if _tur(i) and _gun_of(i)]
    n_dig = [i for i in diger if _tur(i) and _gun_of(i)]
    aday = lambda c: [d for d in n_dig if _tur(d) == _tur(c) and _uyumlu(c, d) and abs((_gun_of(d) - _gun_of(c)).days) <= PENCERE_GUN]
    for c in n_csb:
        es = aday(c)
        if len(es) == 1 and len([x for x in n_csb if es[0] in aday(x)]) == 1:
            ciftler.add(frozenset((c['id'], es[0]['id'])))
    return ciftler
