"""İlan PDF'lerindeki kadro tablosunu sütunlarıyla okur (pdfplumber) ve tüm kadrolar için ortak koşulları çıkarır.

Düz metne dökülen tablolarda sütunlar birbirine karışıyordu ("Sıra Kadro Kadro KPSS ... En az 1 İtfaiye Eri GİH 11");
burada her satır ayrı kadro olarak okunur: ünvan, adet, nitelikler (madde madde), cinsiyet, KPSS puan türü ve taban puanı.
pdfplumber kurulu değilse ya da belge okunamazsa boş liste döner; sayfa eski görünümle üretilir."""
import hashlib
import json
import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path

SURUM = 1
HAM_SURUM = 1  # ham önbellek biçimi değişirse artırılır
# pdfplumber'ın ham çıktısı diskte saklanır (ilan PDF'leri değişmez); ayrıştırma mantığı her seferinde taze çalışır.
ONBELLEK = Path(os.environ.get('PDF_ONBELLEK') or Path(__file__).resolve().parent.parent / '.cache' / 'pdf')
# Başlık hücresi -> alan. Sıra önemli: 'puan türü' 'taban'dan önce denenir.
SUTUN = [
    ('unvan', re.compile(r'unvan|ünvan', re.I)),
    ('adet', re.compile(r'adet|aded|kadro sayısı|kontenjan|sayısı', re.I)),
    ('tur', re.compile(r'puan\s*türü', re.I)),
    ('taban', re.compile(r'taban', re.I)),
    ('cinsiyet', re.compile(r'cinsiyet', re.I)),
    ('nitelik', re.compile(r'niteli|şartlar|aranan|öğrenim|mezuniyet', re.I)),
]
ATLA = re.compile(r'çağrıl|sıra\s*no|^s\.?\s*n\.?$|derece|sınıfı|kodu|ilan\s*no', re.I)


# Eski yazı tipli Türkçe PDF'lerde harfler başka karakterlere dökülür ("Daimi ĠĢçi" -> "Daimi İşçi").
_BOZUK_HARF = str.maketrans({'Ġ': 'İ', 'ģ': 'ş', 'Ð': 'Ğ', 'ð': 'ğ', 'Ý': 'İ', 'ý': 'ı', 'Þ': 'Ş', 'þ': 'ş', '­': ''})


def _hucre(c):
    metin = re.sub(r'Ģ(?=[a-zçğıöşü])', 'ş', (c or '').translate(_BOZUK_HARF)).replace('Ģ', 'Ş')  # bu yazı tipinde küçük ş de Ģ
    return re.sub(r'\s+', ' ', metin).strip()


def _basliklar(satir):
    """Başlık satırından {sütun no: alan}; boş başlıklı sütun soldaki alana eklenir (birleştirilmiş başlık)."""
    es, onceki = {}, None
    for n, b in enumerate(satir):
        alan = None
        if b and not ATLA.search(b):
            alan = next((a for a, d in SUTUN if d.search(b) and a not in es.values()), None)
        elif not b and onceki:
            alan = onceki
        if alan:
            es[n] = alan
        onceki = alan if b or alan else None
    return es


def maddeler(metin):
    """'-A olmak. -B olmak.' / '*A *B' / 'A. B.' -> ['A olmak.', 'B olmak.']"""
    metin = _hucre(metin)
    if not metin:
        return []
    parcalar = re.split(r'\s\|\s|(?:^|\s)[-*•●▪]\s*|(?<=[.;])\s+(?=[A-ZÇĞİÖŞÜ(])', metin)
    out = []
    for p in parcalar:
        p = re.sub(r',$', '.', p.strip(' -*•;|'))
        if p.startswith('(') and out:  # "(Eski tip sürücü belgesi olarak E sınıfı)" önceki maddenin açıklaması
            out[-1] += ' ' + p
            continue
        if len(p) > 2:
            out.append(p[0].upper() + p[1:])
    return out


def _satir(es, r):
    alanlar = {}
    for n, alan in es.items():
        if n < len(r) and r[n]:
            # Aynı alana düşen ikinci sütun (birleştirilmiş başlık): nitelikte ayrı madde olur.
            alanlar[alan] = (alanlar[alan] + (' | ' if alan == 'nitelik' else ' ') + r[n]) if alanlar.get(alan) else r[n]
    unvan = alanlar.get('unvan', '')
    if not unvan:
        return None
    adet = re.search(r'\d+', alanlar.get('adet', ''))
    taban = re.search(r'\b(\d{2,3})(?:[.,]\d+)?\b', alanlar.get('taban', ''))
    tur_metin = alanlar.get('tur', '') + ' ' + alanlar.get('taban', '')
    turler = list(dict.fromkeys(re.findall(r'P\s?(\d{1,3})', tur_metin.replace('KPSSP', 'KPSS P'))))
    cins = alanlar.get('cinsiyet', '').replace(' /', '/').replace('/ ', '/').strip(' -')
    return {
        'unvan': unvan,
        'adet': int(adet.group()) if adet else None,
        'nitelik': maddeler(alanlar.get('nitelik', '')),
        'cinsiyet': cins if cins and cins != '-' else '',
        'tur': ['P' + t for t in turler],
        'taban': int(taban.group(1)) if taban and 30 <= int(taban.group(1)) <= 100 else None,
    }


def _ham(yol, tur, hesapla):
    """pdfplumber'ın ham çıktısını PDF içeriği + sürümle diskte saklar; bozuk/yazılamayan önbellek yok sayılır."""
    import pdfplumber
    ozet = hashlib.sha256(Path(yol).read_bytes()).hexdigest()
    dosya = ONBELLEK / f'{tur}-{HAM_SURUM}-{pdfplumber.__version__}-{ozet}.json'
    try:
        return json.loads(dosya.read_text(encoding='utf-8'))
    except Exception:
        pass
    deger = hesapla()
    try:
        ONBELLEK.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=ONBELLEK, suffix='.tmp', delete=False) as f:
            json.dump(deger, f, ensure_ascii=False)
        os.replace(f.name, dosya)
    except Exception:
        pass
    return deger


@lru_cache(maxsize=None)
def tablo_oku(yol):
    """PDF'teki kadro tablosu satırları (ilk uygun tablo ve sonraki sayfalarda başlıksız devamı)."""
    try:
        import pdfplumber
    except ImportError:
        return ()
    satirlar, es, genislik = [], None, 0

    def hesapla():
        with pdfplumber.open(str(yol)) as pdf:
            return [sayfa.extract_tables({'text_x_tolerance': 1.5}) for sayfa in pdf.pages[:8]]
    try:
        for sayfa in _ham(yol, 'tablo', hesapla):
            for tb in sayfa:
                tb = [[_hucre(c) for c in r] for r in tb if any(r)]
                if not tb:
                    continue
                yeni = _basliklar(tb[0])
                if 'unvan' in yeni.values() and ({'adet', 'nitelik'} & set(yeni.values())):
                    if es is not None:  # ikinci bir kadro tablosu: ilkine eklenmez (farklı biçim olabilir)
                        continue
                    es, genislik, govde = yeni, len(tb[0]), tb[1:]
                elif es is not None and len(tb[0]) == genislik:
                    govde = tb  # önceki sayfadaki tablonun devamı (başlıksız)
                else:
                    continue
                for r in govde:
                    s = _satir(es, r)
                    if s:
                        satirlar.append(s)
    except Exception:
        return ()
    return tuple(satirlar)


_NUMARA = r'(?:[IVX]{1,4}\s*[.\-–)]|[A-ZÇĞİÖŞÜ]\s*[.\-–)]|\d{1,2}(?:\.\d{1,2})*\s*[.\-–)]?|\d\.[a-z](?:\.\(\d\))?)'
_BASLIK_RE = re.compile(r'^\s*(?:' + _NUMARA + r'\s*)?(?P<ad>[^\n]{3,80}?)\s*:?\s*$')
_SART_RE = re.compile(r'ŞART|KOŞUL|NİTELİK|şart(?:lar|ları)\b|koşul(?:lar|ları)\b|nitelikler\b', re.I)
_MADDE_RE = re.compile(r'^\s*(?:[-–•❖▪●►]\s*|[a-zçğıöşü]\s*[).]\s+|\(\s*\d{1,2}\s*\)\s*|\d{1,2}\s*[).-]\s+(?=\D))')


def _baslik_mi(satir):
    """Kısa, büyük harf ağırlıklı ya da numaralı ve nokta/virgülle bitmeyen satır; içindekiler satırı (sonda sayfa no) değil."""
    s = satir.strip()
    if not s or len(s) > 90 or re.search(r'[.,;]$', s) or re.search(r'\s\d{1,3}$', s) or _MADDE_RE.match(s) and not s.isupper():
        return False
    harf = [c for c in s if c.isalpha()]
    buyuk = sum(c.isupper() for c in harf) / max(1, len(harf))
    numarali = re.match(r'^\s*' + _NUMARA + r'\s', s) is not None
    return buyuk >= 0.7 or (numarali and buyuk >= 0.3 and len(s) <= 70)


def _baslik_adi(satir):
    ad = re.sub(r'^\s*' + _NUMARA + r'\s*', '', satir.strip()).strip(' :')
    if ad.isupper():
        ad = ad.replace('I', 'ı').replace('İ', 'i').lower()
    return ad[:1].upper() + ad[1:]


def _metin_oku(yol):
    import pdfplumber

    def hesapla():
        with pdfplumber.open(str(yol)) as pdf:
            return [(sayfa.extract_text(x_tolerance=1.5) or '') for sayfa in pdf.pages[:20]]
    satirlar = []
    for metin in _ham(yol, 'metin', hesapla):
        for s in metin.splitlines():
            s = _hucre(s)
            if s and not re.fullmatch(r'\d{1,3}\s*/\s*\d{1,3}|\d{1,3}|Sayfa \d+.*', s):
                satirlar.append(s)
    return satirlar


_FIIL_SONU = re.compile(r'(?:mak|mek|maması|memesi|olmak|bulunmak|edilir|edilecektir|dır|dir|tır|tir|lıdır|lidir)[.,;:)]?$', re.I)


def _alt_baslik_mi(madde):
    """Pozisyon adı / ara başlık: '2.1. Uzman Personel İçin Aranan Nitelikler', 'Mobil Yazılım Geliştirme Uzmanı (2 kişi …)'."""
    m = madde.strip()
    if re.match(r'^\d+\.\d+\.?\s', m):
        return True
    return (len(m) <= 130 and not re.search(r'[.;:,]$', m) and not _FIIL_SONU.search(m) and m[:1].isupper()
            and m.count('(') == m.count(')'))


@lru_cache(maxsize=None)
def sart_bolumleri(yol):
    """Tablosuz (düz metin) ilanlarda 'Genel şartlar', 'Özel şartlar', 'Sınava katılma koşulları' gibi bölümler:
    ((başlık, ((madde, alt_baslik_mi), ...)), ...). Bölüm, şart içermeyen ilk başlıkta biter; maddesiz başlık atlanır.
    Yanlış bilgi göstermemek için son maddesi yarım kalan (noktalama ile bitmeyen) bölüm hiç verilmez."""
    try:
        satirlar = _metin_oku(yol)
    except Exception:
        return ()
    bolumler, mevcut = [], None
    for s in satirlar:
        if _baslik_mi(s):
            if _SART_RE.search(s) and not re.search(r'telefon|tablo|form|belge', s, re.I):
                mevcut = [_baslik_adi(s), []]
                bolumler.append(mevcut)
                continue
            if mevcut is not None and not _MADDE_RE.match(s):
                mevcut = None
                continue
        if mevcut is None:
            continue
        m = _MADDE_RE.match(s)
        if m:
            mevcut[1].append(s[m.end():].strip())
        elif mevcut[1]:
            onceki = mevcut[1][-1]
            if re.search(r'[.;:]$', onceki) and _alt_baslik_mi(s) and len(s) <= 90:
                mevcut[1].append(s)  # noktayla bitmiş maddeden sonra gelen pozisyon adı yeni satırdır
            else:
                mevcut[1][-1] = (onceki[:-1] + s) if re.search(r'[a-zçğıöşü]-$', onceki) else onceki + ' ' + s
        else:
            mevcut[1].append(s)  # giriş cümlesi (madde işaretsiz)
    sonuc = []
    for ad, ham in bolumler:
        temiz = []
        for x in ham:
            x = re.sub(r'\s+Tablo\s*[-–]?\s*\d.*$', '', x.strip())  # sayfa altındaki tablo başlığı maddeye yapışmışsa
            x = re.sub(r',$', '.', x)
            if len(x) > 3:
                temiz.append((x[:1].upper() + x[1:], _alt_baslik_mi(x)))
        while temiz and temiz[-1][1]:
            temiz.pop()
        if not temiz or not re.search(r'[.!)]$', temiz[-1][0]):
            continue  # yarım kalmış bölüm (son madde ';' / ':' ile bitiyorsa devamı okunamamıştır)
        maddeler_ = [x for x, b in temiz if not b]
        if len(maddeler_) >= 2:
            sonuc.append((ad, tuple(temiz)))
    return tuple(sonuc)


def ortak_kosullar(metin):
    """Tüm kadrolar için geçerli kısa koşullar: istenen KPSS yılı (ve grubu), yaş sınırı."""
    metin = _hucre(metin)
    out = []
    m = re.search(r'(20\d\d)\s*yılı\s*Kamu\s*Personel\s*Seçme\s*Sınavı\S*\s*(\(KPSS[^)]*\))?', metin, re.I)
    if not m:
        m = re.search(r'(20\d\d)\s*(?:yılı\s*)?KPSS\b\s*(\([^)]*\))?', metin)
    if m:
        grup = ' (B grubu)' if m.group(2) and re.search(r'\bB\b', m.group(2)) else ''
        out.append(f'{m.group(1)} KPSS puanı{grup}')
    m = re.search(r'(\d{2})\s*yaşını\s*doldurmamış', metin, re.I)
    if m:
        out.append(f'{m.group(1)} yaşını doldurmamış olmak')
    return out
