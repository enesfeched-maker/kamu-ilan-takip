"""KPSS tercih kılavuzlarından bölüm eşleştirme verisi üretir (yerelde elle çalıştırılır).

Üç kaynak birleştirilir:
  1. Kılavuz tablosu (TABLO-1/2/3): her kadronun ÖSYM kodu ve nitelik kodları.
  2. Nitelik kodları belgesi: her öğrenim nitelik kodunun kabul ettiği mezuniyet alanı (bölüm) kodları.
  3. Mezun olunan program listesi: bölüm kodu → bölüm adı.

    python bot/nitelik_ayikla.py lisans "C:/.../111lisans/kılavuz" "C:/.../KPSS_2010_2026"

Çıktılar: docs/puanlar/<duzey>.json kayıtlarına 'nit' (kadronun öğrenim nitelik kodları) eklenir,
docs/puanlar/<duzey>-bolum.json (bölüm adları + dönem bazında nitelik → bölüm kodları) yazılır.
Belgede açık olmayan eşleştirme tahmin edilmez: bölüm kodu olmayan nitelik yalnız 'herhangi bir'
ifadesi varsa herkese açık sayılır, yoksa 'belirsiz' olarak işaretlenir.
"""
import json
import re
import sys
from pathlib import Path

from puan_ayikla import DONEM, KOK, pdf_metni

DORT = re.compile(r'^\d{4}$')
KOD = re.compile(r'^\d{9}$')
BELGELER = {
    'lisans': ('Lisans_Mezunlari_Icin_Nitelik_Kodlari.pdf', 'Mezun_Olunan_Lisans_Programi.pdf'),
    'onlisans': ('On_Lisans_Mezunlari_Icin_Nitelik_Kodlari.pdf', 'Mezun_Olunan_On_Lisans_Programi.pdf'),
    'ortaogretim': ('Ortaogretim_Mezunlari_Icin_Nitelik_Kodlari.pdf', 'Mezun_Olunan_Ortaogretim_Alan_Dallar.pdf'),
}


BASLIK = re.compile(r'^(?:.*MEZUNLARI İÇİN ARANAN NİTELİKLER.*|Nitelik|Kodu|Nitelik Kodu|ÖĞRENİM KOŞULU'
                    r'|Mezuniyet Alanı Kodları|Nit\d.*|KODU ADI|KODU|ADI|(?:\d{1,2}\s+)*\d{1,2})$', re.I)
SONDA_KOD = re.compile(r'^(.*?[^\d\s])((?:\s+\d{4})+)$')


def _satirlar(sayfalar):
    """Sayfa başlıklarını atar; metin sonuna yapışmış alan kodlarını ayrı satıra böler."""
    sonuc = []
    for sayfa in sayfalar:
        for satir in sayfa.splitlines():
            satir = satir.strip()
            if not satir or BASLIK.match(satir):
                continue
            sonda = SONDA_KOD.match(satir)
            if sonda and not _sayilar(sonda.group(1)) and re.search(r'olmak\.?$', sonda.group(1)):
                sonuc += [sonda.group(1), sonda.group(2).strip()]
            else:
                sonuc.append(satir)
    return sonuc


def _sayilar(satir):
    parcalar = satir.split()
    return parcalar if parcalar and all(DORT.match(p) for p in parcalar) else None


def nitelik_tanimlari(sayfalar):
    """{nitelik kodu: {'b': [bölüm kodları], 'h': herhangi mi, 'm': metin}} döndürür.

    Tek başına duran 4 haneli satır, ardından metin geliyorsa yeni nitelik kodudur; metinden sonra
    gelen 4 haneli sayı satırları o niteliğin mezuniyet alanı kodlarıdır.
    """
    satirlar, sonuc, kod = _satirlar(sayfalar), {}, None
    for i, satir in enumerate(satirlar):
        sonraki = satirlar[i + 1] if i + 1 < len(satirlar) else ''
        if DORT.match(satir) and sonraki and not _sayilar(sonraki):
            kod = satir
            sonuc[kod] = {'b': [], 'm': ''}
        elif kod and _sayilar(satir):
            sonuc[kod]['b'].extend(_sayilar(satir))
        elif kod and not sonuc[kod]['b']:
            sonuc[kod]['m'] = (sonuc[kod]['m'] + ' ' + satir).strip()
    for deger in sonuc.values():
        deger['h'] = bool(re.search(r'herhangi bir', deger['m'], re.I))
    return sonuc


ORTA_BASLIK = re.compile(r'^(?:Ortaöğretim Nitelik Kodları|NİTELİK|KODU|ÖĞRENİM KOŞULLARI|Alan Kodu.*'
                         r'|Alan Kod|Alan Adı|Dal Kod|Dal Adı|Sayfa \d+.*|\d+ / \d+)$', re.I)
DAL = re.compile(r'^(?:\*|-|\d{1,3})$')
DAL_ADLI = re.compile(r'^(\d{1,3})\s+\D.*')  # 2025-1: dal no ile ad aynı satırda ('101 ACİL ... DALI')


def _orta_satirlar(sayfalar):
    return [s.strip() for sayfa in sayfalar for s in sayfa.splitlines()
            if s.strip() and not ORTA_BASLIK.match(s.strip())]


def orta_nitelik_tanimlari(sayfalar):
    """Ortaöğretim: her satır 'nitelik kodu, koşul, alan kodu, dal no (* = tüm dallar), ad' biçimindedir.

    Bölüm karşılığı 'alan-dal' anahtarıdır: '6001-*' Adalet alanının tüm dalları, '6008-3' tek dal.
    """
    satirlar, sonuc, kod = _orta_satirlar(sayfalar), {}, None
    for i, satir in enumerate(satirlar):
        sonraki = satirlar[i + 1] if i + 1 < len(satirlar) else ''
        adli = DAL_ADLI.match(sonraki)
        if DORT.match(satir) and (DAL.match(sonraki) or adli):
            if kod:
                anahtar = f'{satir}-{adli.group(1) if adli else sonraki}'
                sonuc[kod]['b'].append(anahtar)
                ad = sonraki[len(adli.group(1)):].strip() if adli else (satirlar[i + 2] if i + 2 < len(satirlar) else '')
                if ad and not DORT.match(ad):
                    sonuc[kod]['ad'].setdefault(anahtar, ad)
        elif DORT.match(satir) and sonraki and not sonraki[0].isdigit():
            kod = satir
            sonuc.setdefault(kod, {'b': [], 'm': sonraki, 'ad': {}})
    for deger in sonuc.values():
        deger['b'] = list(dict.fromkeys(deger['b']))
        deger['h'] = bool(re.search(r'herhangi bir', deger['m'], re.I))
    return sonuc


def orta_alan_listesi(sayfalar):
    """{'alan-dal': 'ALAN — DAL'}; dalı olmayan mezuniyet 'alan--' anahtarıyla tutulur."""
    satirlar, sonuc = _orta_satirlar(sayfalar), {}
    for i in range(len(satirlar) - 3):
        alan, alan_adi, dal, dal_adi = satirlar[i:i + 4]
        if DORT.match(alan) and not alan_adi[0].isdigit() and DAL.match(dal) and dal != '*':
            sonuc.setdefault(f'{alan}-{dal}', alan_adi if dal == '-' else f'{alan_adi} — {dal_adi}')
    return sonuc


def kilavuz_nitelikleri(sayfalar, ogrenim_kodlari):
    """{ÖSYM kadro kodu: [öğrenim nitelik kodları]} döndürür; diğer şart kodları alınmaz."""
    sonuc, kod = {}, None
    for satir in _satirlar(sayfalar):
        parcalar = satir.split()
        if not all(p.isdigit() for p in parcalar):
            parcalar = parcalar[:1] if KOD.match(parcalar[0]) else []  # metin satırındaki sayılar kod değildir
        for parca in parcalar:
            if KOD.match(parca):
                kod = parca
                sonuc[kod] = []
            elif kod and parca in ogrenim_kodlari and parca not in sonuc[kod]:
                sonuc[kod].append(parca)
    return sonuc


PROGRAM_BASLIK = re.compile(r'^(?:Kodu?|Adı?|Mezun Olunan .*|.*Diploması Alınan Program)$', re.I)
AD_IZIN = r"[A-ZÇĞİÖŞÜÂÎÛa-zçğıöşüâîû0-9 ,.()\-/'&*:;—+]+"
AD_TEMIZ = re.compile(f'^{AD_IZIN}$')
KOD_AD = re.compile(r'^(\d{4})\s+(\D.*)$')


def program_listesi(sayfalar):
    """{bölüm kodu: bölüm adı}; aynı kodun farklı yazımlarından ilki alınır.

    Kod ayrı satırda ya da adla aynı satırda olabilir; iki satıra sarılmış adlar birleştirilir.
    """
    sonuc, kod, ad = {}, None, []
    for satir in _satirlar(sayfalar) + ['0000']:
        if PROGRAM_BASLIK.match(satir):
            continue
        ayni = KOD_AD.match(satir)
        if DORT.match(satir) or ayni:
            if kod and ad:
                sonuc.setdefault(kod, ad_birlestir(ad))
            kod, ad = satir[:4], [ayni.group(2)] if ayni else []
        elif kod and AD_TEMIZ.match(satir):
            ad.append(satir)  # iki satıra sarılmış ad; bozuk glifli başlık/çöp satırları atılır
    return sonuc


def ad_birlestir(parcalar):
    """Satır sonu '-' ile biten parçayı boşluksuz, diğerlerini boşlukla birleştirir."""
    sonuc = ''
    for p in parcalar:
        sonuc += p if not sonuc or sonuc.endswith('-') else ' ' + p
    return sonuc


def main(argv):
    if len(argv) != 3 or argv[0] not in BELGELER:
        print(__doc__)
        return 2
    duzey, kilavuz_klasoru, arsiv = argv[0], Path(argv[1]), Path(argv[2])
    hedef = KOK / 'docs' / 'puanlar' / f'{duzey}.json'
    puanlar = json.loads(hedef.read_text(encoding='utf-8'))
    nitelik_adi, program_adi = BELGELER[duzey]
    bolumler, nitelikler, eksik, yedek = {}, {}, 0, {}
    for donem, kayitlar in puanlar['donemler'].items():
        klasor = arsiv / donem / 'Kilavuz'
        orta = duzey == 'ortaogretim'
        tanimlar = (orta_nitelik_tanimlari if orta else nitelik_tanimlari)(pdf_metni(klasor / nitelik_adi))
        if (klasor / program_adi).exists():
            liste = (orta_alan_listesi if orta else program_listesi)(pdf_metni(klasor / program_adi))
            bolumler.update(liste)  # dönemler eskiden yeniye gelir; en yeni ad (eksik/kesik yazımlar düzelir) kalır
        kadro = kilavuz_nitelikleri(pdf_metni(kilavuz_klasoru / f'{donem}.pdf'), set(tanimlar))
        bulunan = 0
        for kayit in kayitlar:
            if kayit['kod'] in kadro:
                kayit['nit'] = kadro[kayit['kod']]
                bulunan += 1
        eksik += len(kayitlar) - bulunan
        nitelikler[donem] = {k: v['b'] or (['*'] if v['h'] else ['?']) for k, v in tanimlar.items()}
        for v in tanimlar.values():
            for anahtar, ad in v.get('ad', {}).items():
                yedek.setdefault(anahtar, ad)
        belirsiz = sum(1 for v in nitelikler[donem].values() if v == ['?'])
        print(f'{duzey} {donem}: {len(tanimlar)} nitelik ({belirsiz} belirsiz), '
              f'{bulunan}/{len(kayitlar)} kadro kılavuzda bulundu')
    for anahtar, ad in yedek.items():  # alan listesinde olmayan alanlar için nitelik belgesindeki ad
        if not anahtar.endswith('-*'):
            bolumler.setdefault(anahtar, ad)
        elif not any(b.startswith(anahtar[:-1]) for b in bolumler):
            bolumler[anahtar] = ad
    adsiz = {b for d in nitelikler.values() for v in d.values() for b in v if b not in ('*', '?')
             and not (any(x.startswith(b[:-1]) for x in bolumler) if b.endswith('-*') else b in bolumler)}
    print(f'adsız bölüm kodu: {len(adsiz)} {sorted(adsiz)[:10]}')
    desen_disi = {k: a for k, a in bolumler.items() if not AD_TEMIZ.match(a)}
    print(f'desen dışı bölüm adı: {len(desen_disi)} {list(desen_disi.items())[:5]}')
    hedef.write_text(json.dumps(puanlar, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (KOK / 'docs' / 'puanlar' / f'{duzey}-bolum.json').write_text(json.dumps(
        {'bolumler': dict(sorted(bolumler.items(), key=lambda x: x[1])), 'nitelikler': nitelikler},
        ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(bolumler)} bölüm adı; kılavuzda bulunmayan kadro: {eksik}')
    return 1 if eksik else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
