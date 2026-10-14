"""Kariyer Kapısı kadro metinlerinden başvuru koşulları: başlıklı bölümler ve maddeler.

14 Ekim 2026: eski okuyucu yalnız 'Özel Şartları:' + '1-' biçimini tanıyordu; açık 33 ilandan yalnız 1'inde koşul çıkıyordu.
Kurumlar çok farklı biçim kullanır ('a)', 'a.', '1.1.', '•', '*', '-', 'I. BAŞVURU ŞARTLARI', 'Tercihen;' …). Bu modül biçimden
bağımsız çalışır: satırları başlık / madde / devam satırı olarak sınıflar, koşulla ilgisiz bölümleri (sınav konuları, başvuru
şekli, sonuçların duyurulması, görev tanımı) atar, birden çok kadroda aynen geçen maddeleri 'tüm kadrolar için' ortak listeye alır.

bolumler(metin)            -> [[başlık, [madde, …]], …]   (başlık '' olabilir)
ayir(kadro_metinleri)      -> (ortak bölümler, [her kadronun kendine özgü bölümleri])"""
import html
import re

BICIM_ARTIGI = re.compile(r'=\d+(?:\.\d+)?pt')
MADDE_ON = re.compile(r'^\s*(?:[•\-\*–·▪●○]+|\(?\d{1,2}(?:\.\d{1,2}){1,2}\.?(?=\s)|\(?\d{1,2}\s*[.)\-]|\(?[a-zçğıöşü]\s*[.)]|'
                     r'[a-zçğıöşü]-(?=[A-ZÇĞİÖŞÜ])|[IVX]{1,4}\s*[.\-)]|[A-ZÇĞİÖŞÜ]\s*[)\-])\s*')
BASLIK_NO = re.compile(r'^\d{1,2}(?:\.\d{1,2})*\s+(?=[A-ZÇĞİÖŞÜ])')
ARTIK = re.compile(r'(?i)^(?:\d+\s*\.?\s*)?grup\s*:?$|^ek-?\d+$')
ALAN = re.compile(r'^(Unvanı|Kadro Adedi|Görev İli|Görev Yeri|Sınav Usulü|KPSS Puan Türü|KPSS Taban Puanı|Puan Türü|Taban Puan|'
                  r'Atama Yapılabilecek Boş Kadro Sayısı|Sözlü Sınava Katılabilecek Azami Aday Sayısı|Kontenjan)\s*:\s*(.*)$', re.I)
# Başvuru koşulu olmayan bölümler: başlığı bunlardan birini taşıyan bölümün maddeleri gösterilmez.
DISI = re.compile(r'sınav konu|konuları|konular\b|başvuru şekl|başvuru yer|başvuru tarih|başvuru süre|başvuru usul|nasıl başvur|sonuç|duyurul|atama|'
                  r'görev tanım|sınav usul|sınava ilişkin bilgi|değerlendirme|istenen belge|gerekli belge|yazılı sınav|sözlü sınav|'
                  r'sınav yeri|sınav tarihi|sınav merkezi|ücret|iletişim|diğer hususlar|genel hususlar|ilan metni|açıklama', re.I)
KOSUL = re.compile(r'şart|nitelik|koşul|aranan|tercih|öğrenim|mezun|puan|kpss|yaş|deneyim|tecrübe', re.I)
FIIL_SONU = re.compile(r'(?:mak|mek|ması|mesi|maları|meleri|olmak|bulunmak|sahip|gerekir|gerekmektedir|aranır|alınacaktır|'
                       r'edilecektir|yapacaktır|olmalıdır|dir|dır|tir|tır)\W*$', re.I)


def _temiz(s):
    s = html.unescape(BICIM_ARTIGI.sub('', s or ''))
    return re.sub(r'\s+', ' ', s).strip('  ')


def _buyuk_oran(s):
    harf = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in harf) / len(harf) if harf else 0


def baslik_mi(s):
    """Bölüm başlığı: kısa ve ya ':'/';' ile biten, ya büyük harfli, ya da cümle olmayan kısa ad ('Genel Şartlar')."""
    govde = MADDE_ON.sub('', s).strip()
    if not govde or len(govde) > 110:
        return False
    if re.search(r'[:;]$', govde) and len(govde) <= 90 and not ALAN.match(govde):
        return True
    if FIIL_SONU.search(govde) or re.search(r'[.,]$', govde):
        return False
    if _buyuk_oran(govde) > 0.8 and len(govde) >= 4:
        return True
    if len(govde) <= 90 and len(govde.split()) <= 12 and re.search(r'şart|nitelik|koşul', govde, re.I):
        return True
    return len(govde) <= 60 and len(govde.split()) <= 8 and bool(KOSUL.search(govde) or re.search(r'genel|özel|hususlar|nitelik', govde, re.I))


def _madde(s):
    s = MADDE_ON.sub('', s).strip()
    m = re.match(r"BU İLANA\s*['‘’\"“”]+(.+?)['‘’\"“”]+\s*ŞARTLARINI TAŞIYAN ADAYLAR BAŞVURU YAPABİLECEKTİR", s, re.I)
    if m:
        s = 'Bu kadroya yalnız şu şartı taşıyanlar başvurabilir: ' + m.group(1).strip().rstrip(',') + '.'
    return s


def bolumler(metin):
    """Kadro metnini [[başlık, [madde]]] bölümlerine ayırır; alan satırları ve koşul dışı bölümler atılır."""
    from resmi_detay import satirlar
    sonuc, basl, maddeler, disarda = [], '', [], False

    def kapat():
        if maddeler and not disarda:
            sonuc.append([basl, list(maddeler)])

    for ham in satirlar(metin):
        s = _temiz(ham)
        if not s or re.fullmatch(r'[%\W\d]*', s) or re.fullmatch(r'T\.?\s?C\.?', s):
            continue
        if ALAN.match(MADDE_ON.sub('', s)):
            continue
        on_ekli = bool(MADDE_ON.match(s)) and MADDE_ON.match(s).group(0).strip() != ''
        if maddeler and not on_ekli and re.search(r'[\wçğıöşü’\'"”]$', maddeler[-1]) and (s[:1].islower() or s[:1].isdigit()):
            # yarım kalan madde ('… Dair Kanun’un' + '10 uncu maddesinde …'): başlık sanılmasın, önceki maddeye eklenir
            maddeler[-1] = maddeler[-1].rstrip() + ' ' + s
            continue
        if baslik_mi(s):
            kapat()
            yeni = BASLIK_NO.sub('', MADDE_ON.sub('', s).strip()).rstrip(':;').strip()
            kosul_basligi = bool(re.search(r'şart|nitelik|koşul|aranan|tercih', yeni, re.I))
            # koşul dışı bölümün (sınav konuları) alt başlıkları da dışarıda kalır; yeni bir koşul başlığı gelene kadar
            disarda = (bool(DISI.search(yeni)) or disarda) and not kosul_basligi
            basl, maddeler = yeni, []
            continue
        if maddeler and not on_ekli and (not re.search(r'[.;:!?]$', maddeler[-1]) or s[:1].islower()):
            maddeler[-1] = maddeler[-1].rstrip() + ' ' + s   # satır bölünmesi: önceki maddenin devamı
            continue
        maddeler.append(_madde(s))
    kapat()
    gecerli = lambda m: len(m) > 5 and not ARTIK.match(m)
    return [[b, [m for m in ms if gecerli(m)]] for b, ms in sonuc if any(gecerli(m) for m in ms)]


def _anahtar(m):
    return re.sub(r'\W+', ' ', m.lower()).strip()


def ayir(metinler):
    """(ortak, ozeller): iki ya da daha çok kadroda TÜM kadrolarda aynen geçen maddeler ortak listeye alınır (ilk kadrodaki
    başlığıyla); her kadroya yalnız kendine özgü maddeler kalır, boşalan bölüm atılır."""
    her = [bolumler(m) for m in metinler]
    if len(her) < 2:
        return [], her
    kumeler = [{_anahtar(m) for _, ms in b for m in ms} for b in her]
    ortak_k = set.intersection(*kumeler) if kumeler else set()
    ortak = [[b, [m for m in ms if _anahtar(m) in ortak_k]] for b, ms in her[0]]
    ortak = [[b, ms] for b, ms in ortak if ms]
    ozel = [[[b, [m for m in ms if _anahtar(m) not in ortak_k]] for b, ms in bl] for bl in her]
    ozel = [[[b, ms] for b, ms in bl if ms] for bl in ozel]
    return ortak, ozel
