"""İlan PDF'lerindeki kadro tablosunu sütunlarıyla okur (pdfplumber) ve tüm kadrolar için ortak koşulları çıkarır.

Düz metne dökülen tablolarda sütunlar birbirine karışıyordu ("Sıra Kadro Kadro KPSS ... En az 1 İtfaiye Eri GİH 11");
burada her satır ayrı kadro olarak okunur: ünvan, adet, nitelikler (madde madde), cinsiyet, KPSS puan türü ve taban puanı.
pdfplumber kurulu değilse ya da belge okunamazsa boş liste döner; sayfa eski görünümle üretilir."""
import re
from functools import lru_cache

SURUM = 1
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


@lru_cache(maxsize=None)
def tablo_oku(yol):
    """PDF'teki kadro tablosu satırları (ilk uygun tablo ve sonraki sayfalarda başlıksız devamı)."""
    try:
        import pdfplumber
    except ImportError:
        return ()
    satirlar, es, genislik = [], None, 0
    try:
        with pdfplumber.open(str(yol)) as pdf:
            for sayfa in pdf.pages[:8]:
                for tb in sayfa.extract_tables({'text_x_tolerance': 1.5}):
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
