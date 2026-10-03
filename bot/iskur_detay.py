"""İŞKUR kamu ilan PDF'lerinden kadro/KPSS/özet/başvuru bilgisi çıkarır.

Saf işlev modülü: ağ ve dosya yazma yok. Hiçbir ham PDF metni saklanmaz; bulunamayan alan çıktıya girmez.
"""
import hashlib
import io
import re
from datetime import datetime
from pypdf import PdfReader

VERSION = 1
SAYFA_SINIRI = 40
ETIKET_KOSUL = 'Belgede belirtilen koşullar'

# e-imza (EBYS) damgası bir yetkilinin adını içerir: asla yayımlanmaz.
DAMGA = re.compile(r'\d{1,2}/\d{1,2}/20\d{2}\s+(?:PAZARTESİ|SALI|ÇARŞAMBA|PERŞEMBE|CUMA|CUMARTESİ|PAZAR)\b.{0,80}?EBYS\s*\d*', re.S)
SINIF = r'(?:G\.?\s?İ\.?\s?H\.?|T\.?\s?H\.?|S\.?\s?H\.?|A\.?\s?H\.?|Y\.?\s?H\.?|D\.?\s?H\.?|E\.?\s?Ö\.?\s?H\.?)'
ROW = re.compile(r'(?<![\d/.,])(\d{1,2})\s+([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü() ]{1,60}?)\s+(' + SINIF + r')\s+(\d{1,2})\s+(\d{1,3})(?![\d.,/])')
PT = re.compile(r'\b(?:KPSS\s?)?P\s?(\d{1,3})\b(?:\s+(?:En\s+az\s+)?(\d{2,3}(?:[.,]\d+)?)(?:\s*[Pp]uan)?)?')
BASLIK_SONU = re.compile(r'BAŞVURU\s+GENEL|GENEL\s+ŞARTLAR')
PARCA = re.compile(r'(?<=[.!?;:])(?<!Mah\.)(?<!Cad\.)(?<!Sok\.)(?<!Bul\.)(?<!No\.)\s+(?=[A-ZÇĞİÖŞÜ(])|\s+(?=[a-zçğış]\)\s)|\s+(?=\d{1,2}\s?[-.)]\s+[A-ZÇĞİÖŞÜ])')
BASLIK_ATLA = re.compile(r'\b\w+(?:ndan|nden|dan|den):\s*(?:[A-ZÇĞİÖŞÜ0-9/().\-]+\s+){1,12}?(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü])')
GIRIS = re.compile(r'^(.{60,1400}?(?:alınacaktır|yapılacaktır|gerçekleştirecektir)\.)')
BASVURU_DISLA = ('sinavsonuc', 'itiraz', 'fotokopi', 'eksikbilgi', 'tebligat', 'hataliadres', 'gecik')
BASVURU_ONCELIK0 = ('tarihleriarasinda', 'tarihinden')
BASVURU_ONCELIK1 = ('sahsen', 'adresine', 'edevlet', 'kariyerkapisi')


def _ek():
    import ek_kaynaklar
    return ek_kaynaklar


def _kisalt(metin, limit):
    from resmi_detay import kisalt
    return kisalt(metin, limit)


def _temizle(metin):
    """Çıktıya giren her metin: damga ayıkla, boşlukları topla."""
    return _ek().clean(DAMGA.sub(' ', metin))


def sayfa_metinleri(raw):
    if not raw.startswith(b'%PDF-'):
        raise ValueError('İŞKUR belgesi PDF değil')
    reader = PdfReader(io.BytesIO(raw))
    if len(reader.pages) > SAYFA_SINIRI:
        raise ValueError('İŞKUR belgesi çok uzun')
    return [p.extract_text() or '' for p in reader.pages]


def _satirlar(plain):
    """Kadro tablosu: [{sira, unvan, sinif, derece, adet, pt, taban}] ; güvenilmezse []."""
    m = BASLIK_SONU.search(plain)
    govde = plain[:m.start()] if m else plain
    eslesmeler = list(ROW.finditer(govde))
    if not eslesmeler or len(eslesmeler) > 40:
        return []
    sonuc = []
    for k, e in enumerate(eslesmeler):
        sira, unvan, sinif, derece, adet = int(e.group(1)), _ek().clean(e.group(2)), e.group(3), int(e.group(4)), int(e.group(5))
        if sira != k + 1 or not 1 <= adet <= 500 or not 1 <= derece <= 15:
            return []
        son = eslesmeler[k + 1].start() if k + 1 < len(eslesmeler) else min(len(govde), e.end() + 600)
        pt = PT.search(govde[e.end():son])
        sonuc.append({'unvan': unvan, 'sinif': re.sub(r'[\s.]', '', sinif), 'derece': derece, 'adet': adet,
                      'pt': 'P' + pt.group(1) if pt else None, 'taban': pt.group(2) if pt else None})
    return sonuc


def _kadro(satirlar):
    toplam = {}
    for s in satirlar:
        toplam[s['unvan']] = toplam.get(s['unvan'], 0) + s['adet']
    kadro = ' • '.join(f'{n} {u}' for u, n in toplam.items())
    if len(toplam) > 1:
        kadro = f'Toplam {sum(toplam.values())} kişi — ' + kadro
    return kadro


def _parcalar(plain):
    out = []
    for p in PARCA.split(plain):
        p = re.sub(r'^[a-zçğış]\)\s+', '', _ek().clean(p))
        if p:
            out.append(p)
    return out


def _sartlar(plain, satirlar, pozisyon):
    norm = _ek().norm
    sartlar = []
    birim = 'pozisyon' if pozisyon else 'kadro'
    for s in satirlar[:6]:
        metin = ''
        if s['pt']:
            metin = f"KPSS {s['pt']} puan türünden en az {s['taban']} puan. " if s['taban'] else f"KPSS {s['pt']} puan türü. "
        metin += f"Hizmet sınıfı {s['sinif']}, {s['derece']}. derece. Öğrenim ve diğer nitelikler ilan belgesindeki tabloda yer alıyor."
        sartlar.append({'kadro': f"{s['unvan']} · {s['adet']} {birim}", 'metin': metin})
    ekler, gorulen = [], set()
    b = BASLIK_SONU.search(plain)
    for p in _parcalar(plain[b.start():] if satirlar and b else plain):
        n = norm(p)
        if satirlar:
            uygun = 'yasini doldurmamis' in n or ('surucu belgesi' in n and 'olmak' in n)
            uygun = uygun and 'fotokopi' not in n and 'istenen belgeler' not in n
        else:
            uygun = (('kpss' in n and ('en az' in n or 'puan turu' in n)) or ('mezun' in n and 'olmak' in n)) \
                and not re.search(r'fotokopi|transkript|istenen belgeler|itiraz|sinav sonuc', n)
        # Tablo hücresi artıkları (başlık/KPSS sütunları) koşul sayılmaz; 300 karakteri aşanlar kesilmeden atılır.
        if not uygun or not 20 <= len(p) <= 300 or re.search(r'Sıra No|Ünvan Kadro|\bKPSS P\d', p):
            continue
        if p in gorulen:
            continue
        gorulen.add(p)
        ekler.append({'kadro': ETIKET_KOSUL, 'metin': p})
    return (sartlar + ekler[:2])[:6] if satirlar else ekler[:3]


def _ozet(plain, plain_pages, baslik):
    ek = _ek()
    if ek.notice(baslik):
        from sbb_detay import duyuru_cumlesi_bul
        cumle = duyuru_cumlesi_bul(plain_pages)
        if cumle:
            return cumle
    h = BASLIK_ATLA.search(plain[:600])
    govde = plain[h.end():] if h else plain
    m = GIRIS.search(govde)
    return _kisalt(m.group(1), 520) if m else ''


def _basvuru(plain):
    norm = _ek().norm
    adaylar = []
    for p in _parcalar(plain):
        if not 30 <= len(p) <= 450:
            continue
        n = norm(p)
        c = n.replace(' ', '')
        if 'basvur' not in c or any(w in c for w in BASVURU_DISLA):
            continue
        if any(w in c for w in BASVURU_ONCELIK0):
            adaylar.append((0, p))
        elif any(w in c for w in BASVURU_ONCELIK1) or ' posta ile ' in f' {n} ' or ' elden ' in f' {n} ':
            adaylar.append((1, p))
    adaylar.sort(key=lambda x: x[0])  # kararlı sıralama
    secilen = []
    for _, p in adaylar:
        if any(p in q or q in p for q in secilen):
            continue
        secilen.append(p)
        if len(secilen) == 2:
            break
    return ' '.join(secilen)


def ozetle_metin(plain_pages, row, sha=''):
    plain = _temizle(' '.join(plain_pages))
    satirlar = _satirlar(plain)
    sonuc = {}
    if satirlar:
        sonuc['kadro'] = _kadro(satirlar)
    pozisyon = bool(re.search(r'Pozisyon\s+Ünvanı', plain)) and not re.search(r'Kadro\s+Ünvanı', plain)
    sartlar = _sartlar(plain, satirlar, pozisyon)
    if sartlar:
        sonuc['sartlar'] = sartlar
    ozet = _ozet(plain, plain_pages, row.get('baslik', ''))
    if ozet:
        sonuc['ozet'] = ozet
    basvuru = _basvuru(plain)
    if basvuru:
        sonuc['basvuru_notu'] = basvuru
    sonuc = _damgasiz(sonuc)
    sonuc['iskur_detay_surumu'] = VERSION
    if sha:
        sonuc['iskur_belge_sha256'] = sha
    sonuc['iskur_detay_guncelleme'] = _ek().now().isoformat(timespec='seconds')
    return sonuc


def _damgasiz(deger):
    if isinstance(deger, str):
        return _temizle(deger)
    if isinstance(deger, list):
        return [_damgasiz(x) for x in deger]
    if isinstance(deger, dict):
        return {k: _damgasiz(v) for k, v in deger.items()}
    return deger


def ozetle(raw, row):
    """PDF baytları -> yalnızca dolu alanlar. Hatalarda istisna yükseltir; çağıran yakalar."""
    return ozetle_metin(sayfa_metinleri(raw), row, hashlib.sha256(raw).hexdigest())
