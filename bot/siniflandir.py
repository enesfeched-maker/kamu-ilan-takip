"""İlan sınıflandırma: öğrenim seviyesi, kategori, KPSS durumu ve Telegram etiketleri."""
import re
import unicodedata

ILLER = (
    'Adana Adıyaman Afyonkarahisar Ağrı Aksaray Amasya Ankara Antalya Ardahan Artvin Aydın Balıkesir '
    'Bartın Batman Bayburt Bilecik Bingöl Bitlis Bolu Burdur Bursa Çanakkale Çankırı Çorum Denizli '
    'Diyarbakır Düzce Edirne Elazığ Erzincan Erzurum Eskişehir Gaziantep Giresun Gümüşhane Hakkari '
    'Hatay Iğdır Isparta İstanbul İzmir Kahramanmaraş Karabük Karaman Kars Kastamonu Kayseri Kırıkkale '
    'Kırklareli Kırşehir Kilis Kocaeli Konya Kütahya Malatya Manisa Mardin Mersin Muğla Muş Nevşehir '
    'Niğde Ordu Osmaniye Rize Sakarya Samsun Siirt Sinop Sivas Şanlıurfa Şırnak Tekirdağ Tokat '
    'Trabzon Tunceli Uşak Van Yalova Yozgat Zonguldak'
).split()

HARF = 'a-zçğıöşü'
SOL = '(?<![' + HARF + '])'
SAG = '(?![' + HARF + '])'

AKADEMIK = re.compile(
    r'öğretim (?:üyesi|elemanı)|araştırma görevlisi|profesör|doçent|öğretim görevlisi')
OGRENIM = (
    ('lisans', re.compile(
        SOL + r'(?<!yüksek )(?<!ön )lisans (?:mezun|diploma|derece|program|düzey|eğitim)'
        r'|fakültelerin|fakülte(?:si)? mezun|fakültesinden|dört yıllık|kpss ?p3' + r'(?!\d)')),
    ('onlisans', re.compile(
        r'ön ?lisans|meslek yüksekokul|iki yıllık|' + SOL + r'(?:kpss ?)?p93(?!\d)')),
    ('ortaogretim', re.compile(
        r'ortaöğretim|' + SOL + r'(?:meslek )?lise(?:si|den|ler)?' + SAG + r'|' + SOL + r'(?:kpss ?)?p94(?!\d)')),
)
ETIKET_OGRENIM = {'lisans': '#lisans', 'onlisans': '#önlisans', 'ortaogretim': '#ortaöğretim'}
ETIKET_KATEGORI = {
    'akademik': '#akademik', 'belediye': '#belediye', 'isci': '#işçi',
    'bilisim': '#bilişim', 'saglik': '#sağlık',
}
KPSSSIZ = re.compile(r'kpsssiz|kpss[^.;]{0,40}aranma(?:z|yacak|mamaktadır)|sınavsız')
SAGLIK = re.compile(SOL + r'(?:hemşire|ebe' + SAG + r'|sağlık personeli|hastane)')


P9X = re.compile(SOL + r'(?:kpss ?)?p9[34](?!\d)')
P3 = re.compile(SOL + r'(?:kpss ?)?p3(?!\d)')
LISANS_KESIN = re.compile(r'fakültelerin|dört yıllık|lisans mezun')


def kucuk(metin):
    """Türkçe uyumlu küçük harf: İ/I doğru çevrilir, birleşik nokta temizlenir."""
    metin = unicodedata.normalize('NFC', str(metin or ''))
    metin = metin.translate(str.maketrans({'I': 'ı', 'İ': 'i'}))
    metin = unicodedata.normalize('NFC', metin.lower()).replace('̇', '')
    metin = re.sub(r"['’`´]", '', metin)
    return re.sub(r'\s+', ' ', metin).strip()


def _sartlar(ilan):
    return [s for s in ilan.get('sartlar') or [] if isinstance(s, dict)]


def _kisa_metin(ilan):
    return kucuk(' '.join(str(ilan.get(a) or '') for a in ('baslik', 'kadro', 'ilan_turu')))


def _tum_metin(ilan):
    parcalar = [ilan.get(a) for a in ('baslik', 'kadro', 'ozet')]
    for s in _sartlar(ilan):
        parcalar += [s.get('kadro'), s.get('metin')]
    return kucuk(' '.join(str(p or '') for p in parcalar))


# Başlıkta unvan yazmayan akademik ilanlar şart metninden tanınır.
AKADEMIK_SART = re.compile(r'2547 sayılı|doktora veya tıpta|doçentliğini|doktorasını|öğretim üyeliğine')


def akademik_mi(ilan):
    return bool(AKADEMIK.search(_kisa_metin(ilan)) or AKADEMIK_SART.search(_tum_metin(ilan)))


def ogrenim_seviyeleri(ilan):
    if akademik_mi(ilan):
        return []
    metin = _tum_metin(ilan)
    bulunan = [ad for ad, desen in OGRENIM if _sart_olarak_gecer(desen, metin)]
    # Bozuk PDF tablolarında "ön" ile "lisans" ayrı hücreye düşer; puan türü
    # yalnız P93/P94 ise "lisans program..." eşleşmesi önlisans/lise demektir.
    if 'lisans' in bulunan and P9X.search(metin) and not P3.search(metin) \
            and not LISANS_KESIN.search(metin):
        bulunan.remove('lisans')
    return bulunan


def _sart_olarak_gecer(desen, metin):
    """'... öğrenci kaydı bulunmamak' gibi dışlayıcı ifadeleri saymaz."""
    return any('öğrenci' not in metin[m.end():m.end() + 40] for m in desen.finditer(metin))


def kategori(ilan):
    kisa = _kisa_metin(ilan)
    kurum = kucuk(' '.join(str(ilan.get(a) or '') for a in ('kurum', 'baslik')))
    tur = kucuk(ilan.get('ilan_turu'))
    if akademik_mi(ilan):
        return 'akademik'
    if 'belediye' in kurum or 'il özel idare' in kurum:
        return 'belediye'
    if tur.startswith('işçi'):
        return 'isci'
    if 'bilişim personeli' in kisa:
        return 'bilisim'
    if SAGLIK.search(kisa + ' ' + kurum):
        return 'saglik'
    return None


def kpss_durumu(ilan):
    metin = _tum_metin(ilan)
    if KPSSSIZ.search(metin):
        return 'kpsssiz'
    if 'kpss' in metin:
        return 'kpss'
    return None


def _il_bul(parca):
    kelimeler = kucuk(parca).replace('-', ' ').split()
    if not kelimeler:
        return None
    for il in ILLER:
        if kucuk(il) == kelimeler[0]:
            return il
    return None


def _kesin_il(parca):
    """Parça yalnızca bir il adıysa (isteğe bağlı 'merkez' ekiyle) o ili döndürür; kurum/ilçe adında il üretmez."""
    kelimeler = kucuk(parca).split()
    if len(kelimeler) == 2 and kelimeler[1] == 'merkez':
        kelimeler = kelimeler[:1]
    return _il_bul(parca) if len(kelimeler) == 1 else None


def il_adlari(ilan):
    """Görev yeri il adları (ILLER yazımıyla). Yer '•', ',', ';' veya '-' ile bölümlenir; bölümlerde
    parantez içi atılır ve '/' ile ayrılmış parçalardan kesin il olanların hepsi alınır
    ('DENİZLİ / MANİSA' → ikisi, 'ANKARA / ÇANKAYA' → Ankara). Dolu bir bölümden il çıkarılamazsa
    (ilçe/kurum olabilir) eksik liste yerine tüm sonuç boş döner (ilan herkese gider)."""
    yer = re.sub(r'\([^)]*\)', ' ', str(ilan.get('yer') or ''))
    sonuc = []
    for bolum in re.split(r'[•,;-]', yer):
        if not bolum.strip():
            continue
        bulunan = [il for il in map(_kesin_il, bolum.split('/')) if il]
        if not bulunan:
            return []
        for il in bulunan:
            if il not in sonuc:
                sonuc.append(il)
    return sonuc


def il_etiketi(ilan):
    il = _il_bul(re.split(r'[/•]', str(ilan.get('yer') or ''))[0])
    return '#' + il if il else None


def etiketler(ilan):
    sonuc = {ETIKET_OGRENIM[s] for s in ogrenim_seviyeleri(ilan)}
    kat = kategori(ilan)
    if kat:
        sonuc.add(ETIKET_KATEGORI[kat])
    kpss = kpss_durumu(ilan)
    if kpss:
        sonuc.add('#' + kpss)
    il = il_etiketi(ilan)
    if il:
        sonuc.add(il)
    return sorted(sonuc)
