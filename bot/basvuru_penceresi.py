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
    return yeni
