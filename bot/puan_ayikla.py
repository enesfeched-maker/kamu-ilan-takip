"""ÖSYM KPSS yerleştirme 'sayısal bilgiler' PDF'lerinden en küçük/en büyük puanları ayıklar.

ÖSYM sitesine GitHub sunucularından erişilemediği için bu betik yerelde, indirilmiş PDF'lerle çalışır:
    python bot/puan_ayikla.py onlisans "C:/.../111önlisans/sayısal bilgiler"
Klasördeki dosyalar dönem adıyla (2025-2.pdf gibi) adlandırılmış olmalıdır.
Çıktı: docs/puanlar/<duzey>.json
"""
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
DUZEYLER = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
KOD = re.compile(r'^\d{9}$')
SAYI = re.compile(r'^\d+$')
PUAN = re.compile(r'^\d{2,3},\d+$')
DONEM = re.compile(r'^(20\d\d)-([12])$')
BASLIK = re.compile(r'^(?:KPSS-\d{4}/\d .*|En Küçük ve En Büyük Puanlar.*|\([^/]*\)|Kod|Program Kodu'
                    r'|Program Adı|Kurum Adı|Kadro Ün?vanı|Kontenjan|Sayısı|Yerleşen Aday'
                    r'|Boş Kalan Kontenjan|En Küçük|En Büyük|Puan)$')


def puan(metin):
    return float(metin.replace(',', '.'))


def satirlar(metin):
    """Sayfa metnini boş olmayan satırlara böler; aynı satırdaki iki puanı ayırır."""
    for satir in metin.splitlines():
        # Eski dönemlerde kod ile kurum adı aynı satırdadır.
        for parca in re.split(r'(?<=^\d{9})\s+|\s+(?=\d{2,3},\d+$)', satir.strip()):
            if parca:
                yield parca


def blok_coz(kod, blok):
    """Bir program kodunun ardından gelen satırları kayda çevirir; tutarsızsa None döner."""
    while blok and blok[-1] == '--':  # Yerleşen olmayan kadrolarda puan yerine '--' yazılır.
        blok.pop()
    puanlar = []
    while blok and PUAN.match(blok[-1]):
        puanlar.insert(0, puan(blok.pop()))
    sayilar = []
    while blok and SAYI.match(blok[-1]) and len(sayilar) < 3:
        sayilar.insert(0, int(blok.pop()))
    if len(sayilar) != 3 or len(puanlar) not in (0, 2) or len(blok) < 2:
        return None
    kontenjan, yerlesen, bos = sayilar
    if kontenjan != yerlesen + bos or (yerlesen and not puanlar):
        return None
    # Kurum satırı 'KURUM / İL / TEŞKİLAT' biçimindedir ve uzun adlarda alt satıra taşabilir.
    bolu = max(i for i, s in enumerate(blok) if '/' in s) + 1 if any('/' in s for s in blok) else 1
    if blok[bolu - 1].endswith('/') and bolu < len(blok) - 1:  # Teşkilat alt satıra taşmış.
        bolu += 1
    kurum_satiri = ' '.join(blok[:bolu])
    unvan = ' '.join(blok[bolu:])
    parcalar = [p.strip() for p in kurum_satiri.split('/')]
    if not unvan or len(parcalar) < 2:
        return None
    if len(parcalar) == 2:  # Bazı belediyelerde teşkilat yazılmaz: 'KURUM / İL'.
        parcalar.append('')
    kayit = {
        'kod': kod, 'kurum': ' / '.join(parcalar[:-2]), 'il': parcalar[-2],
        'teskilat': parcalar[-1].capitalize(), 'unvan': unvan, 'kontenjan': kontenjan, 'yerlesen': yerlesen,
    }
    if puanlar:
        kayit['min'], kayit['max'] = puanlar
    return kayit


def metinden_ayikla(sayfalar):
    """Sayfa metinlerinden (kayıtlar, çözülemeyen kodlar) döndürür."""
    kayitlar, hatalar, kod, blok = [], [], None, []

    def bitir():
        if kod:
            kayit = blok_coz(kod, blok)
            (kayitlar.append(kayit) if kayit else hatalar.append(kod))

    for sayfa in sayfalar:
        for satir in satirlar(sayfa):
            if KOD.match(satir):
                bitir()
                kod, blok = satir, []
            elif kod and not BASLIK.match(satir):
                blok.append(satir)
    bitir()
    return kayitlar, hatalar


def pdf_metni(yol):
    import fitz  # PyMuPDF; yalnız yerel ayıklamada gerekir.
    with fitz.open(yol) as belge:
        return [sayfa.get_text() for sayfa in belge]


def klasoru_ayikla(duzey, klasor):
    donemler, toplam_hata = {}, 0
    for yol in sorted(Path(klasor).glob('*.pdf')):
        if not DONEM.match(yol.stem):
            continue
        kayitlar, hatalar = metinden_ayikla(pdf_metni(yol))
        if not kayitlar:
            raise ValueError(f'{yol.name}: kayıt bulunamadı')
        toplam_hata += len(hatalar)
        print(f'{duzey} {yol.stem}: {len(kayitlar)} kadro, {len(hatalar)} çözülemedi {hatalar[:5]}')
        donemler[yol.stem] = kayitlar
    return {'duzey': duzey, 'ad': DUZEYLER[duzey],
            'kaynak': 'ÖSYM KPSS yerleştirme sonuçları sayısal bilgiler (en küçük ve en büyük puanlar)',
            'donemler': donemler}, toplam_hata


def main(argv):
    if len(argv) != 2 or argv[0] not in DUZEYLER:
        print(__doc__)
        return 2
    veri, hata = klasoru_ayikla(argv[0], argv[1])
    hedef = KOK / 'docs' / 'puanlar' / f'{argv[0]}.json'
    hedef.parent.mkdir(exist_ok=True)
    hedef.write_text(json.dumps(veri, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{hedef} yazıldı; çözülemeyen satır: {hata}')
    return 1 if hata else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
