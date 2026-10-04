"""ÇŞB duyurularına eklenen docx/pdf ilan metinlerinden kadro tablosu (unvan, adet, öğrenim, KPSS puan türü, taban)
çıkarır. Saf işlev modülü: ağ yok; ham belge metni saklanmaz, bulunamayan alan çıktıya girmez.

Çıktı biçimi İŞKUR/SBB kayıtlarıyla aynıdır ('kadro' metni ve 'sartlar' listesi); öğrenim düzeyi, puan türü ve il
süzgeçleri bu metinlerden mevcut sınıflandırıcılarla türetilir."""
import io
import re
import xml.etree.ElementTree as ET
import zipfile

from ek_kaynaklar import clean, norm
from siniflandir import ILLER

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
XML_SINIRI = 6_000_000
SATIR_SINIRI = 40          # bundan çok satırlı tablo kadro tablosu sayılmaz
SART_SINIRI = 6
NITELIK_SINIRI = 420
ETIKET = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
PT_DUZEY = {'P3': 'lisans', 'P93': 'onlisans', 'P94': 'ortaogretim'}


def docx_xml(veri, sinir=XML_SINIRI):
    """word/document.xml kökü; boyut ve DTD/ENTITY denetimli."""
    with zipfile.ZipFile(io.BytesIO(veri)) as z:
        bilgi = z.getinfo('word/document.xml')
        if bilgi.file_size > sinir:
            raise ValueError('Belge metni boyut sınırını aşıyor')
        xml = z.read(bilgi)
    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
        raise ValueError('Beklenmeyen belge yapısı')
    return ET.fromstring(xml)


def _paragraf(p):
    parca = []
    for e in p.iter():
        if e.tag == W + 't':
            parca.append(e.text or '')
        elif e.tag in (W + 'tab', W + 'br'):
            parca.append(' ')
    return clean(''.join(parca))


def docx_tablolari(veri):
    """[tablo][satır][hücre] -> hücrenin boş olmayan paragraf listesi. İç içe tablolar yok sayılır."""
    kok = docx_xml(veri)
    sonuc = []
    for tbl in kok.iter(W + 'tbl'):
        satirlar = []
        for tr in tbl.findall(W + 'tr'):
            hucreler = []
            for tc in tr.findall(W + 'tc'):
                hucreler.append([m for m in (_paragraf(p) for p in tc.findall(W + 'p')) if m])
            satirlar.append(hucreler)
        sonuc.append(satirlar)
    return sonuc


def _harf(metin):
    return re.sub(r'[^a-z]', '', norm(metin))


def duzelt(metin):
    """Word tablolarında harf aralarına giren boşlukları onarır ('i nşaat' -> 'inşaat', 'olma k' -> 'olmak')."""
    m = clean(metin)
    m = re.sub(r'\(\s*([A-Za-z])\s*\)', r'(\1)', m)
    m = re.sub(r'\bE n az\b', 'En az', m)
    # Tek harf + küçük harfli kelime: yalnız küçük harfler ve kelime başı büyük harfler birleştirilir;
    # 'A', 'B', 'C' sınıf adları (ör. 'B sınıfı') ve 've/ya' gibi gerçek tek harfli sözcükler korunur.
    m = re.sub(r'(?<![\w(])([a-zçğıöşü]|[D-Z]|[ÇĞİÖŞÜ]) (?=[a-zçğıöşü]{2,})', r'\1', m)
    m = re.sub(r'(?<=[a-zçğıöşü]{3}) ([a-zçğıöşü])(?=[\s.,;:)]|$)', r'\1', m)
    m = re.sub(r'\s+([.,;:])', r'\1', m)
    return clean(m)


def _tam_sayi(hucre):
    """'1 8' -> 18, '1 0' -> 10; sayı yoksa None."""
    m = re.sub(r'\s+', '', ' '.join(hucre))
    return int(m) if m.isdigit() else None


def _sutunlar(satir):
    """Başlık satırı -> {alan: sütun sırası}; kadro tablosu değilse None."""
    kodlar = [_harf(' '.join(h)) for h in satir]
    harita = {}
    for k, c in enumerate(kodlar):
        if 'unvan' in c:
            harita.setdefault('unvan', k)
        elif re.search(r'ade[dt]', c):
            harita.setdefault('adet', k)
        elif 'derece' in c:
            harita.setdefault('derece', k)
        elif 'sinif' in c:
            harita.setdefault('sinif', k)
        elif re.search(r'nitelik|nitelig', c):
            harita.setdefault('nitelik', k)
        elif 'cinsiyet' in c:
            harita.setdefault('cinsiyet', k)
        elif 'taban' in c:
            harita.setdefault('taban', k)
        elif 'kpss' in c and ('turu' in c or 'puan' in c):
            harita.setdefault('pt', k)
    kod = ' '.join(kodlar)
    harita['pozisyon'] = 'pozisyon' in kod and 'kadro' not in kod
    return harita if {'unvan', 'adet'} <= set(harita) else None


def _puan_turu(hucre):
    m = re.search(r'P(\d{1,3})', re.sub(r'\s+', '', ' '.join(hucre)).upper().replace('KPSS', ''))
    return 'P' + m.group(1) if m else None


def _taban(hucre):
    m = re.sub(r'(?<=\d)\s+(?=\d)', '', ' '.join(hucre))
    for s in re.findall(r'\d{2,3}(?:[.,]\d+)?', m):
        if 30 <= float(s.replace(',', '.')) <= 100:
            return s
    return None


def _cinsiyet(hucre):
    c = _harf(' '.join(hucre))
    erkek, kadin = 'erkek' in c, 'kadin' in c
    return 'Erkek' if erkek and not kadin else 'Kadın' if kadin and not erkek else None


def _nitelik(hucre):
    # Hücredeki paragraflar çoğunlukla satır kırılmasıdır; yalnız '-' ile başlayan paragraf yeni madde sayılır.
    maddeler = []
    for p in hucre:
        if re.match(r'^[-•–]', p) or not maddeler:
            maddeler.append(re.sub(r'^[-•–]\s*', '', p))
        else:
            maddeler[-1] += ' ' + p
    sonuc = []
    for m in maddeler:
        m = duzelt(m)
        if m:
            sonuc.append(m if m[-1] in '.;!?' else m.rstrip(',') + '.')
    metin = ' '.join(sonuc)
    return re.sub(r'(?<!\.)[,;]?\s+(?=En az \([A-D]\) sınıfı)', '. ', metin)    # madde işareti olmayan satır başı


def ogrenim(nitelik, pt):
    """Nitelik metninden öğrenim düzeyleri (boşluk bozukluğuna dayanıklı); bulunamazsa KPSS puan türünden."""
    c = _harf(nitelik)
    bulunan = []
    if re.search(r'(?<!on)(?<!yuksek)lisans', c):
        bulunan.append('lisans')
    if 'onlisans' in c:
        bulunan.append('onlisans')
    if 'ortaogretim' in c or re.search(r'lise(?:vedengi|veyadengi|den|mezun)', c):
        bulunan.append('ortaogretim')
    if not bulunan and pt in PT_DUZEY:
        bulunan.append(PT_DUZEY[pt])
    return bulunan


def tablo_satirlari(tablolar):
    """docx_tablolari çıktısından kadro satırları: [{unvan, sinif, derece, adet, pt, taban, nitelik, cinsiyet, pozisyon}].
    Kadro tablosu bulunamaz ya da güvenilmezse []."""
    sonuc = []
    for tablo in tablolar:
        harita = None
        govde = []
        for satir in tablo:
            h = _sutunlar(satir) if harita is None else None
            if h:
                harita = h
                continue
            if harita:
                govde.append(satir)
        if not harita or not govde or len(govde) > SATIR_SINIRI:
            continue
        gecici = []
        for satir in govde:
            if not any(satir):
                continue
            def al(alan):
                k = harita.get(alan)
                return satir[k] if k is not None and k < len(satir) else []
            unvan = duzelt(' '.join(al('unvan')))
            adet = _tam_sayi(al('adet'))
            if not unvan or not adet or not 1 <= adet <= 500:
                gecici = []
                break
            derece = _tam_sayi(al('derece'))
            pt = _puan_turu(al('pt'))
            nitelik = _nitelik(al('nitelik'))
            gecici.append({'unvan': unvan, 'sinif': re.sub(r'[\s.]', '', ' '.join(al('sinif'))).upper() or None,
                           'derece': derece if derece and 1 <= derece <= 15 else None, 'adet': adet, 'pt': pt,
                           'taban': _taban(al('taban')), 'nitelik': nitelik, 'cinsiyet': _cinsiyet(al('cinsiyet')),
                           'pozisyon': harita['pozisyon']})
        sonuc.extend(gecici)
    return sonuc


def kadro_metni(satirlar):
    toplam = {}
    for s in satirlar:
        toplam[s['unvan']] = toplam.get(s['unvan'], 0) + s['adet']
    kadro = ' • '.join(f'{n} {u}' for u, n in toplam.items())
    if len(toplam) > 1:
        kadro = f'Toplam {sum(toplam.values())} kişi — ' + kadro
    return kadro


def sart_metni(s):
    parcalar = []
    if s['pt']:
        parcalar.append(f"KPSS {s['pt']} puan türünden en az {s['taban']} puan." if s['taban'] else f"KPSS {s['pt']} puan türü.")
    sinif = ''
    if s['sinif']:
        sinif = f"Hizmet sınıfı {s['sinif']}"
        sinif += f", {s['derece']}. derece." if s['derece'] else '.'
        parcalar.append(sinif)
    duzeyler = ogrenim(s['nitelik'], s['pt'])
    if duzeyler:
        parcalar.append('Öğrenim: ' + ' / '.join(ETIKET[d] for d in duzeyler) + ' mezunu.')
    if s['nitelik']:
        parcalar.append(_kisalt(s['nitelik'], NITELIK_SINIRI))
    if s['cinsiyet']:
        parcalar.append(f"Cinsiyet: {s['cinsiyet']}.")
    return ' '.join(parcalar)


def _kisalt(metin, limit):
    if len(metin) <= limit:
        return metin
    return metin[:limit - 1].rsplit(' ', 1)[0] + '…'


def alanlar(satirlar):
    """Kadro satırları -> {'kadro': ..., 'sartlar': [...]} (satır yoksa {})."""
    if not satirlar:
        return {}
    sartlar = []
    for s in satirlar[:SART_SINIRI]:
        birim = 'pozisyon' if s['pozisyon'] else 'kadro'
        sartlar.append({'kadro': f"{s['unvan']} · {s['adet']} {birim}", 'metin': sart_metni(s)})
    return {'kadro': kadro_metni(satirlar), 'sartlar': sartlar}


def pdf_alanlari(veri, baslik=''):
    """PDF ilan metni: İŞKUR çözümleyicisiyle kadro/şart çıkarılır. Tablo bulunamazsa {}."""
    import iskur_detay
    sonuc = iskur_detay.ozetle(veri, {'baslik': baslik})
    return {k: sonuc[k] for k in ('kadro', 'sartlar') if sonuc.get(k)} if sonuc.get('kadro') else {}


def belge_alanlari(adres, veri, baslik=''):
    """Ek belgeden kadro/şart alanları. Çözümleme başarısızsa istisna atar; kadro tablosu yoksa {} döner."""
    if adres.lower().endswith('.docx'):
        return alanlar(tablo_satirlari(docx_tablolari(veri)))
    return pdf_alanlari(veri, baslik)


def il_slug(link):
    """'.../istanbul-ili-sile-...-duyuru-1' -> 'İstanbul'; başlıkta il yazmayan duyurular için."""
    m = re.search(r'/([a-z0-9]+)-ili-', str(link or '').lower())
    if not m:
        return None
    for il in ILLER:
        if re.sub(r'[^a-z]', '', norm(il)) == m.group(1):
            return il
    return None
