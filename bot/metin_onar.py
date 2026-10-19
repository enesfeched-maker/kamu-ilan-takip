"""PDF'ten çıkan ilan metinlerindeki yazım kırıklarını onarır (19 Ekim 2026 koşul denetimi).

Görülen kırıklar: kelime ortasına giren boşluk ('Be lediye', 'B aşkanlığı', 'be lgelerini', 'şekil lerde',
'değerlendirilmesin i', 'i le'), bölünen e-posta ve alan adları ('@gmai l.com', 'atalan.bel.t r', 'ais.osym .gov.tr'),
'e- Devlet'. Onarılamayacak kadar bozuk metinde (boşlukları tamamen kaybolmuş, sütun başlıkları karışmış) None döner:
çağıran o metni göstermez, resmî belgeye yönlendirir. İhtiyatlı kurallar: yanlış birleştirme, kırığı bırakmaktan kötüdür."""
import re

KUCUK = 'a-zçğıöşüâîû'
BUYUK = 'A-ZÇĞİÖŞÜÂÎÛ'
# Tek büyük harften sonra gelince ayrı kalması gereken sözcükler ('B grubu', 'C sınıfı', 'A bendi')
HARF_SONRASI = ('grub', 'sınıf', 'tip', 'blok', 'bend', 'fıkra', 'kadro', 'kategori', 'ehliyet', 'seviye', 'düzey', 'şık')
# Türkçe sözcük başında bulunabilen ünsüz ikilileri (alıntı sözcükler); bunun dışındaki ikiliyle başlayan parça önceki parçaya aittir
BAS_IKILI = {'bl', 'br', 'dr', 'fl', 'fr', 'gl', 'gr', 'kl', 'kr', 'pl', 'pr', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sv', 'tr', 'ps', 'ts', 'şt',
             'sc', 'sw', 'sh', 'th', 'ch', 'wh', 'wr', 'kn', 'ph', 'sq', 'ng', 'xm', 'js', 'cr', 'gn', 'pn'}   # yabancı terimler: script, switch, nginx
UNLU = set('aeıioöuüâîû')
IKI_HARFLI = {'ve', 'de', 'da', 'ki', 'mi', 'mı', 'bu', 'şu', 'en', 'ne', 'ya', 'iç', 'üç', 'el', 'il', 'at', 'ev', 'an', 'aş', 'iş', 'uç',
              'ad', 'su', 'on', 'ay', 'öz', 'ek', 'üs', 'oy', 'ön', 'ok', 'az', 'ağ', 'ab', 'af', 'al', 'ar', 'as', 'av', 'er', 'et',
              'ey', 'ha', 'in', 'it', 'iz', 'ol', 'ot', 'öç', 'ün', 'un', 'us', 'ye', 'ti', 'ip', 'ak', 'ok'}
# Sonraki parça bunlardan biriyse birleştirme yapılmaz (bağlaç, kısaltma, birim, adres)
AYRI_KALIR = {'ve', 'ile', 'veya', 'ya', 'ise', 'de', 'da', 'ki', 'yahut', 'ya da'}
KISALTMA_RE = re.compile(r'(?:vb|vs|cm|km|kg|mm|ml|sn|dk|tl|ytl|no|nolu|maddesi|md|pdf|jpe?g|png|sql|xml|html?|css|php|json|cv|ttps?)\b', re.I)
BASLIK_SOZCUKLERI = ('TALEP EDİLEN', 'MEZUN OLUNAN', 'KPSS PUAN', 'DİĞER NİTELİKLER', 'İŞÇİ SAYISI', 'S.N.', 'Kaynak Okul Kodu',
                     'Erkek Kadın', 'Sınıfı Branşı', 'ALES Puan Alanı', 'Aranan Şartlar', 'Fakülte/Yüksekokul')


def _kucuk(s):
    return s.replace('İ', 'i').replace('I', 'ı').lower()


def _adres_onar(s):
    s = re.sub(r'\be-\s+Devlet', 'e-Devlet', s)
    s = re.sub(r'\bh\s+(ttps?://)', r'h\1', s)                                      # h ttps://
    s = re.sub(r'(\S+@[\w.-]*)\s+([\w-]*\.(?:com|net|org|tr)\b)', r'\1\2', s)       # @gmai l.com
    s = re.sub(r'(@[\w.-]+)\s+([\w-]{1,4}\.(?:bel|gov|edu|k12)\.tr\b)', r'\1\2', s)   # @gered e.bel.tr
    s = re.sub(r'(\.(?:bel|gov|edu|com|org|k12)\.t)\s+(r)\b', r'\1\2', s)            # .bel.t r
    s = re.sub(r'((?:https?://|www\.)\S+)\s+(\.(?:gov|com|org|edu|bel|net)\b\S*)', r'\1\2', s)   # ais.osym .gov.tr
    return s


def _parca_onar(s):
    t = s.split(' ')
    i, cikti = 0, []
    while i < len(t):
        x = t[i]
        y = t[i + 1] if i + 1 < len(t) else None
        yalin = re.sub(r'[.,;:)]+$', '', y or '').lower()
        if y is not None and x and y and yalin not in AYRI_KALIR and not KISALTMA_RE.match(y) and not y.startswith(('http', 'www')):
            yk = y.lstrip('(')
            # 1) tek harf + sesliyle süren parça: 'B aşkanlığı', 'C addesi', 'ş artları', 'i le', 'b aşvurular'
            #    (ünsüz başlayan parçaya bağlanan tek harf çoğu zaman önceki sözcüğün kopan son harfidir: 'olma k ve')
            if (re.fullmatch(f'[{BUYUK}{KUCUK}]', x) and x not in ('o', 'O', 'a', 'A', 'e', 'E')
                    and re.match(f'[{KUCUK}]', y) and (y[0] in UNLU or x in 'iıIİ')
                    and not (x.isupper() and y.lower().startswith(HARF_SONRASI))):
                t[i + 1] = x + y
                i += 1
                continue
            # 1b) büyük harfle başlayan anlamsız iki harf + küçük harfle süren parça: 'Be lediye', 'Ko şullar'
            if re.fullmatch(f'[{BUYUK}][{KUCUK}]', x) and _kucuk(x) not in IKI_HARFLI and re.match(f'[{KUCUK}]{{3,}}', y):
                t[i + 1] = x + y
                i += 1
                continue
            # 2) Türkçe sözcük başlatamayan ünsüz ikilisiyle başlayan parça: 'be lgelerini', 'a sgari', 'adresi ndeki'
            if (re.fullmatch(f'[{BUYUK}{KUCUK}]+', x) and _kucuk(x) not in IKI_HARFLI and re.fullmatch(f'[{KUCUK}]{{3,}}[.,;:]?', y)
                    and y[0] not in UNLU and y[1] not in UNLU and y[:2] not in BAS_IKILI):
                t[i + 1] = x + y
                i += 1
                continue
            # 3) çoğul eki ayrı düşmüş: 'şekil lerde', 'diğer leri'
            if re.fullmatch(f'[{BUYUK}{KUCUK}]{{3,}}', x) and re.fullmatch(f'(?:ler|lar)[{KUCUK}]*[.,;:]?', y):
                t[i + 1] = x + y
                i += 1
                continue
            # 4) son harfi ayrı düşmüş: 'değerlendirilmesin i', 'belirlendiğ i'
            z = t[i + 2] if i + 2 < len(t) else ''
            if (re.fullmatch(f'[{BUYUK}{KUCUK}]{{3,}}', x) and re.fullmatch(f'[iıuü][.,;:]?', yk) and yk == y
                    and not re.fullmatch(f'[{KUCUK}]{{1,2}}[.,;:]?', z)):   # 'i le' ise 1. kural 'ile' yapar
                t[i + 1] = x + y
                i += 1
                continue
            # 4b) son ünsüzü ayrı düşmüş: 'yur t dışındaki', 'olma k ve' (sonraki parça ünsüzle başlıyorsa; sesliyle
            #     başlıyorsa harf o parçanın başıdır ve 1. kural ileriye bağlar: 'Tüm b aşvurular')
            zk = _kucuk(z)
            if y == 'h' and zk.startswith('ttp'):   # 'h ttps://' bağlantısı: 1. kural sonraki parçaya bağlar
                zk = 'a'
            if (re.fullmatch(f'[{BUYUK}{KUCUK}]{{2,}}', x) and re.fullmatch(f'[{KUCUK}]', y) and y not in UNLU
                    and (not z or not re.match(f'[{KUCUK}{BUYUK}]', z) or zk[0] not in UNLU or re.sub(r'[.,;:)]+$', '', zk) in AYRI_KALIR)):
                t[i + 1] = x + y
                i += 1
                continue
        cikti.append(x)
        i += 1
    return ' '.join(cikti)


def _yapisik_mi(s):
    """Boşlukları kaybolmuş metin: harflerden oluşan, 22+ karakterli en az üç parça (adresler hariç; Türkçede bile nadir)."""
    uzun = [w for w in re.findall(f'[{BUYUK}{KUCUK}]+', re.sub(r'\S+@\S+|https?://\S+|www\.\S+', ' ', s)) if len(w) >= 22]
    return len(uzun) >= 3


def onar(metin):
    """Onarılmış metin; okunamayacak kadar bozuksa None."""
    if not metin:
        return metin
    s = re.sub(r'\s+', ' ', str(metin)).strip()
    if _yapisik_mi(s):
        return None
    if sum(1 for b in BASLIK_SOZCUKLERI if b in s) >= 3:
        if '•' not in s:
            return None
        s = s[s.index('•'):].lstrip('• ').strip()   # tablo başlığı döküntüsü atılır, ilk maddeden başlanır
    s = re.sub(r'\s*\bSayfa\s+\d+\s*/\s*\d+\b(?:\s+T\.C\.)?', '', s).strip()   # PDF sayfa altlığı ('Sayfa 5 / 8 T.C.')
    s = _adres_onar(s)
    if re.search(r'(?:(?:^|\s)\S(?=\s)){4}', s):   # 'Ö ğ r e t i m' gibi harf harf dökülmüş metin: tahminle birleştirilmez
        return s
    for _ in range(2):   # 'B aşkanlığı' gibi zincirleri de toplar
        s = _parca_onar(s)
    return s
