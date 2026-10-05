"""İlan belgesi metninden başvuru penceresi (başlangıç/bitiş günü ve saati) çıkarır.

Saf işlevler: ağ/dosya yok. Belge metni resmî kaynaktır; liste tablosundaki (İŞKUR) ya da SBB dönem alanındaki tarih
belge ile çelişirse belge kazanır. Metinde açık aralık yoksa None döner (tahmin edilmez).

Desteklenen yazımlar:
  21 Eylül 2026 (00.00) – 25 Eylül 2026 (17.00)      12 Ekim – 19 Ekim 2026      20-22 Ekim 2026
  19/10/2026-21/10/2026     01.10.2026/06.10.2026     05/10/2026/-07/10/2026
  08.10.2026 tarihinden başlayarak 23.10.2026 tarihi saat 23.59'a kadar"""
import re
from datetime import date, datetime, timedelta, timezone

TR = timezone(timedelta(hours=3))
AYLAR = ('ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık')
AY = '(' + '|'.join(AYLAR) + ')'
SAAT_SONRA = re.compile(r'^(?:\s*tarih\w*)?\s*\(?\s*(?:saat\s*:?\s*)?(\d{1,2})[.:](\d{2})(?![\d.])')
SAYISAL = re.compile(
    r'(?<![\d/.])(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})(?!\d)'
    r'(?:\s*/?\s*[-–—]\s*|\s*/\s*|\s+tarihinden(?:\s+başlayarak)?\s+|\s+ile\s+)'
    r'(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})(?!\d)')
YAZILI = re.compile(
    r'(\d{1,2})\s+' + AY + r'(?:\s+(20\d{2}))?' + r'(?:\s*\(\s*(\d{1,2})[.:](\d{2})\s*\))?'
    r'\s*[-–—]\s*(\d{1,2})\s+' + AY + r'\s+(20\d{2})', re.I)
KISA_YAZILI = re.compile(r'(?<!\d)(\d{1,2})\s*[-–—]\s*(\d{1,2})\s+' + AY + r'\s+(20\d{2})', re.I)
BASVURU_BAGLAM = 'başvur'


def _kucuk(s):
    return str(s or '').translate(str.maketrans({'I': 'ı', 'İ': 'i'})).lower()


def _gun(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def _saat_bul(metin, bitis_konumu):
    m = SAAT_SONRA.match(metin[bitis_konumu:bitis_konumu + 40])
    if not m:
        return None
    s, dk = int(m.group(1)), int(m.group(2))
    return (s, dk) if 0 <= s <= 23 and 0 <= dk <= 59 else None


def _adaylar(metin):
    """[(başlangıç konumu, bitiş konumu, başlangıç gün, bitiş gün, başlangıç saati, bitiş saati)] belge sırasında."""
    k = _kucuk(metin)
    sonuc = []
    for m in SAYISAL.finditer(metin):
        b, e = _gun(m.group(3), m.group(2), m.group(1)), _gun(m.group(6), m.group(5), m.group(4))
        if b and e:
            sonuc.append((m.start(), m.end(), b, e, None, _saat_bul(metin, m.end())))
    for m in YAZILI.finditer(k):
        ay1, ay2 = AYLAR.index(m.group(2)) + 1, AYLAR.index(m.group(7)) + 1
        y2 = int(m.group(8))
        y1 = int(m.group(3)) if m.group(3) else y2 - (ay1 > ay2)
        b, e = _gun(y1, ay1, m.group(1)), _gun(y2, ay2, m.group(6))
        bs = (int(m.group(4)), int(m.group(5))) if m.group(4) else None
        if b and e:
            bitis_saat = None
            r = re.match(r'\s*\(\s*(\d{1,2})[.:](\d{2})\s*\)', k[m.end():m.end() + 14])
            if r:
                bitis_saat = (int(r.group(1)), int(r.group(2)))
            sonuc.append((m.start(), m.end(), b, e, bs, bitis_saat))
    for m in KISA_YAZILI.finditer(k):
        ay, y = AYLAR.index(m.group(3)) + 1, m.group(4)
        b, e = _gun(y, ay, m.group(1)), _gun(y, ay, m.group(2))
        if b and e:
            sonuc.append((m.start(), m.end(), b, e, None, _saat_bul(metin, m.end())))
    return sorted(sonuc, key=lambda x: x[0])


def asamali(metin):
    """'ön başvurular 20-22 Ekim 2026 … nihai başvurular ise 30 Ekim - 3 Kasım 2026' -> {'on': (başlangıç, bitiş), 'nihai': (…)} ya da None."""
    metin = re.sub(r'\s+', ' ', str(metin or ''))
    k = _kucuk(metin)
    on, nihai = re.search(r'ön\s*başvuru', k), re.search(r'nihai\s*başvuru', k)
    if not (on and nihai):
        return None
    adaylar = _adaylar(metin)
    sonraki = lambda m: next((a for a in adaylar if 0 <= a[0] - m.end() <= 45), None)
    a, b = sonraki(on), sonraki(nihai)
    if not (a and b) or a[2] > a[3] or b[2] > b[3] or b[3] < a[3]:
        return None
    return {'on': (a[2], a[3]), 'nihai': (b[2], b[3])}


AY_KISA = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')


def _aralik_yazi(b, e):
    if b == e:
        return f'{b.day} {AY_KISA[b.month - 1]}'
    if b.month == e.month:
        return f'{b.day}–{e.day} {AY_KISA[b.month - 1]}'
    return f'{b.day} {AY_KISA[b.month - 1]}–{e.day} {AY_KISA[e.month - 1]}'


def asama_yazisi(asamalar):
    """{'on': ['2026-10-20','2026-10-22'], 'nihai': [...]} -> 'Ön başvuru 20–22 Ekim · Nihai başvuru 30 Ekim–3 Kasım' ('' bozuksa)."""
    try:
        on = [date.fromisoformat(x) for x in asamalar['on']]
        nihai = [date.fromisoformat(x) for x in asamalar['nihai']]
        return f'Ön başvuru {_aralik_yazi(*on)} · Nihai başvuru {_aralik_yazi(*nihai)}'
    except (KeyError, TypeError, ValueError):
        return ''


def pencere(metin, referans=None, en_cok_gun=120):
    """Metindeki ilk başvuru aralığı: {'baslangic': date, 'bitis': date, 'baslangic_saat': (s,dk)|None, 'bitis_saat': (s,dk)|None}.
    Aralığın yakınında 'başvur' geçmeli; bitiş başlangıçtan önce olamaz, aralık en çok `en_cok_gun` gün sürer ve
    bitiş yılı `referans` (varsayılan bugün) yılından ±1 yıl içinde olmalıdır. Bulunamazsa None."""
    metin = re.sub(r'\s+', ' ', str(metin or ''))
    if not metin:
        return None
    k = _kucuk(metin)
    if isinstance(referans, datetime):
        ref = referans.date()
    elif isinstance(referans, date):
        ref = referans
    else:
        ref = datetime.now(TR).date()
    s = asamali(metin)
    if s and abs(s['nihai'][1].year - ref.year) <= 1 and (s['nihai'][1] - s['on'][0]).days <= en_cok_gun:
        return {'baslangic': s['on'][0], 'bitis': s['nihai'][1], 'baslangic_saat': None, 'bitis_saat': None, 'asamalar': s}
    for bas_k, bit_k, b, e, bs, es in _adaylar(metin):
        if e < b or (e - b).days > en_cok_gun or abs(e.year - ref.year) > 1:
            continue
        baglam = k[max(0, bas_k - 220):bit_k + 80]
        if BASVURU_BAGLAM not in baglam:
            continue
        return {'baslangic': b, 'bitis': e, 'baslangic_saat': bs, 'bitis_saat': es}
    return None


def _zaman(gun, saat):
    s, dk = saat if saat else (0, 0)
    return datetime(gun.year, gun.month, gun.day, s, dk, tzinfo=TR)


def uygula(kayit, metinler, referans=None):
    """Kayıt kopyasında belge penceresini uygular (kayıt değişmez). Belge penceresi bulunamazsa aynı nesne döner.
    son_tarih belge bitişinden farklıysa belge kazanır: son_tarih = bitiş günü, son_zaman = belgedeki saat (yoksa kaldırılır).
    Bitiş günü aynıysa mevcut son_zaman korunur (belgede saat varsa o yazılır). baslangic_zaman penceredeki başlangıçtır."""
    for metin in metinler:
        p = pencere(metin, referans)
        if p:
            break
    else:
        return kayit
    yeni = dict(kayit)
    bitis = p['bitis'].isoformat()
    if yeni.get('son_tarih') != bitis:
        yeni['son_tarih'] = bitis
        yeni.pop('son_zaman', None)
        if p['bitis_saat']:
            yeni['son_zaman'] = _zaman(p['bitis'], p['bitis_saat']).isoformat()
    elif p['bitis_saat']:
        yeni['son_zaman'] = _zaman(p['bitis'], p['bitis_saat']).isoformat()
    yeni['baslangic_zaman'] = _zaman(p['baslangic'], p['baslangic_saat']).isoformat()
    if p.get('asamalar'):
        yeni['basvuru_asamalari'] = {a: [d.isoformat() for d in v] for a, v in p['asamalar'].items()}
    return yeni
