"""Small original vector-style occupational illustrations, rendered locally."""
import re
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw

FOTO_KLASORU = Path(__file__).resolve().parents[1] / 'docs' / 'assets' / 'meslek'
GENEL_PERSONEL = 30
# Sıra önemlidir: özel meslekler genel olanlardan önce gelir. Kökler norm() edilmiş metinde kelime başından aranır;
# sonunda boşluk olan kök tam kelime olmalıdır.
FOTO_ESLEME = [
    (4, ('veteriner',)),
    (5, ('eczaci',)),
    (3, ('hekim', 'doktor', 'tabip')),
    (2, ('hemsire', 'ebe ', 'saglik')),
    (29, ('laborant', 'kimyager', 'biyolog')),
    (1, ('yazilim', 'bilgisayar', 'bilisim', 'sistem', 'ag ', 'siber', 'devops', 'veri tabani', 'veritabani', 'programci')),
    (7, ('zabita',)),
    (8, ('itfaiye',)),
    (6, ('guvenlik', 'koruma', 'bekci')),
    (10, ('pilot',)),
    (11, ('asci',)),
    (12, ('garson',)),
    (27, ('operator', 'is makinesi')),
    (9, ('sofor', 'surucu')),
    (13, ('temizlik', 'destek personeli', 'hizmetli')),
    (18, ('ogretim uyesi', 'ogretim gorevlisi', 'ogretim elemani', 'arastirma gorevlisi', 'akadem', 'profesor', 'docent')),
    (19, ('ogretmen',)),
    (20, ('kutuphane',)),
    (21, ('avukat', 'hukuk')),
    (23, ('mufettis', 'denetci', 'kontrolor')),
    (28, ('muhasebe', 'mali ', 'gelir uzman')),
    (14, ('muhendis',)),
    (15, ('mimar',)),
    (17, ('elektrik',)),
    (16, ('tekniker', 'teknisyen')),
    (25, ('bahcivan',)),
    (26, ('orman',)),
    (24, ('isci',)),
    (22, ('buro', 'memur', 'sekreter', 'veri hazirlama', 'vhki')),
]


def norm(text):
    return text.replace('İ','i').lower().translate(str.maketrans('ışğüöç', 'isguoc'))


YIL_SAYISI = re.compile(r'(?:19|20)\d\d$')


def adet_ayir(parca):
    """'3 UZMAN' -> (3, 'UZMAN'); baştaki sayı yıl (1900-2100) ya da sayı yoksa (None, parca).
    '2026 YILI TABİP ...' bir kadro sayısı değil, yıl bilgisidir."""
    m = re.match(r'^(\d+)\s+(.*)$', parca or '')
    if not m or YIL_SAYISI.fullmatch(m.group(1)) and 1900 <= int(m.group(1)) <= 2100:
        return None, parca
    return int(m.group(1)), m.group(2)


# Başlıktaki "N ... alacak" sayısı: yıl değil
BASLIK_ADET = r'(?<![\d.])(?!(?:19|20)\d\d\b)(\d+)'


def meslekler(kadro):
    text = re.sub(r'^Toplam\s+\d+\s+kişi\s*[—–-]\s*', '', kadro or '', flags=re.I)
    return list(dict.fromkeys(p.strip() for p in text.split('•') if p.strip()))


def kategori(label):
    s = norm(label)
    groups = [
        ('computer', ('bilgisayar', 'yazilim', 'bilisim', 'veritabani', 'programci')),
        ('health', ('hemsire', 'ebe', 'saglik', 'hekim', 'doktor', 'veteriner', 'eczaci', 'laborant')),
        ('security', ('guvenlik', 'zabita', 'polis', 'bekci', 'asker')),
        ('fire', ('itfaiye',)),
        ('driver', ('sofor', 'surucu', 'operator', 'pilot')),
        ('kitchen', ('asci', 'garson', 'mutfak')),
        ('support', ('temizlik', 'destek personeli', 'hizmetli', 'bakim')),
        ('technical', ('muhendis', 'mimar', 'tekniker', 'teknisyen', 'elektrik', 'tesisat', 'usta')),
        ('education', ('ogret', 'arastirma', 'akadem', 'profesor', 'docent', 'egit', 'kutuphane')),
        ('law', ('avukat', 'hukuk',)),
        ('office', ('buro', 'memur', 'uzman', 'sekreter', 'muhasebe', 'denet', 'mufettis')),
        ('worker', ('isci', 'bahcivan', 'orman', 'tarim')),
    ]
    return next((key for key, words in groups if any(w in s for w in words)), 'document')


def illustration(label, size=220):
    # Draw at 2x for clean edges. The icon is representative, never a real employee.
    im = Image.new('RGBA', (320, 250)); d = ImageDraw.Draw(im)
    ink, teal, lime, skin = '#173e48', '#428b88', '#d9f59a', '#e8b99a'
    kind = kategori(label)
    d.ellipse((47, 13, 273, 239), fill='#e7eeeb')
    d.ellipse((67, 220, 259, 239), fill='#cfddd8')
    if kind == 'document':
        d.rounded_rectangle((99, 39, 225, 216), 13, fill='white', outline=ink, width=5)
        d.rounded_rectangle((121, 24, 202, 55), 9, fill=teal)
        for y in (91, 130, 169):
            d.ellipse((119, y, 132, y+13), fill=teal)
            d.line((147, y+6, 202, y+6), fill=ink, width=5)
    else:
        # Uniform silhouette with role-specific clothing and equipment.
        d.rounded_rectangle((109, 117, 218, 229), 28, fill='white' if kind=='health' else teal)
        d.rounded_rectangle((149, 95, 178, 135), 9, fill=skin)
        d.ellipse((130, 40, 196, 114), fill=skin)
        d.pieslice((128, 34, 198, 97), 180, 350, fill=ink)
        d.line((160, 126, 166, 211), fill=ink, width=4)
        if kind in ('technical', 'worker', 'fire'):
            d.pieslice((125, 29, 202, 91), 180, 360, fill='#f2c45e')
            d.rounded_rectangle((119, 54, 209, 65), 5, fill='#f2c45e')
            d.line((163, 32, 163, 57), fill=ink, width=3)
        if kind=='health':
            d.line((142, 132, 142, 169, 177, 169, 177, 133), fill=ink, width=4)
            d.ellipse((168, 166, 185, 183), fill=teal)
            d.rounded_rectangle((216, 153, 259, 208), 8, fill=teal)
            d.rectangle((234, 163, 241, 197), fill='white'); d.rectangle((224, 176, 250, 183), fill='white')
        elif kind=='computer':
            d.rounded_rectangle((72, 149, 222, 215), 8, fill=ink)
            d.rounded_rectangle((81, 158, 213, 204), 4, fill='#9cd3c5')
            d.line((124,174,115,182,124,190), fill=ink,width=4); d.line((168,174,177,182,168,190), fill=ink,width=4)
            d.line((151,171,142,194), fill=ink,width=4)
            d.rounded_rectangle((62, 214, 233, 224), 5, fill=teal)
        elif kind in ('security','fire'):
            if kind=='security':
                d.pieslice((123,25,204,89),180,360,fill=ink); d.rectangle((126,52,202,64),fill=ink)
            d.polygon([(221,132),(258,144),(253,191),(237,208),(217,191),(213,144)],fill=ink)
            d.line((225,167,235,179,250,155),fill=lime,width=5)
        elif kind=='driver':
            d.ellipse((94,141,226,245),fill=ink); d.ellipse((106,153,214,233),fill='#e7eeeb')
            d.ellipse((148,182,174,209),fill=ink)
            for x,y in ((111,163),(207,163),(160,236)):d.line((161,195,x,y),fill=ink,width=9)
        elif kind=='kitchen':
            d.rounded_rectangle((129,28,198,64),12,fill='white',outline=ink,width=3)
            for x in (126,151,174):d.ellipse((x,14,x+33,48),fill='white')
            d.rectangle((143,136,188,220),fill='white')
            d.ellipse((197,181,275,199),fill=ink);d.arc((198,147,274,205),180,360,fill=teal,width=7)
        elif kind=='support':
            d.line((96,92,76,209),fill=ink,width=7); d.polygon([(57,200),(99,207),(105,237),(46,237)],fill='#f2c45e')
            d.rounded_rectangle((218,174,263,230),7,fill=teal);d.arc((223,150,258,194),180,360,fill=ink,width=4)
        elif kind in ('technical','worker'):
            d.rounded_rectangle((72,166,146,227),7,fill=ink);d.rectangle((91,155,126,169),outline=ink,width=5)
            d.line((229,143,207,214),fill=ink,width=12);d.arc((218,116,253,151),0,300,fill=ink,width=9)
            if 'teknisyen' in norm(label):
                d.rounded_rectangle((68,146,151,228),9,fill='#f2c45e')
                d.rounded_rectangle((79,157,140,180),4,fill=ink)
                d.ellipse((95,189,126,220),fill=ink)
            elif 'muhendis' in norm(label) or 'mimar' in norm(label):
                d.rounded_rectangle((64,151,151,230),5,fill='#a1cfc5')
                d.rectangle((76,167,139,212),outline=ink,width=3)
                d.line((76,189,139,189),fill=ink,width=3)
        elif kind=='education':
            d.polygon([(77,157),(132,151),(165,165),(199,151),(254,157),(254,221),(199,215),(165,229),(132,215),(77,221)],fill=ink)
            d.polygon([(86,163),(132,160),(158,172),(158,217),(132,207),(86,212)],fill='white')
            d.polygon([(172,172),(198,160),(245,163),(245,212),(198,207),(172,217)],fill=lime)
        elif kind=='law':
            d.line((239,120,239,218),fill=ink,width=6);d.line((208,146,270,146),fill=ink,width=5)
            for x in (212,264):
                d.line((x,146,x-14,176,x+14,176,x,146),fill=ink,width=3)
                d.pieslice((x-15,164,x+15,188),0,180,fill='#f2c45e')
            d.line((220,222,259,222),fill=ink,width=6)
        else:
            d.rounded_rectangle((74,154,144,221),7,fill=ink)
            d.rectangle((83,163,135,209),fill='white')
            for y in (177,188,199):d.line((92,y,127,y),fill=teal,width=3)
            d.rounded_rectangle((207,182,267,226),6,fill=ink);d.rectangle((224,174,249,184),outline=ink,width=4)
    return im.resize((size, round(size*250/320)), Image.Resampling.LANCZOS)


def meslek_no(label):
    """Kadro adından 30 meslekten birinin numarası (eşleşmezse 30: Genel Personel)."""
    s = ' ' + ' '.join(re.sub(r'[^a-z0-9]+', ' ', norm(label or '')).split()) + ' '
    for no, kokler in FOTO_ESLEME:
        for kok in kokler:
            if (' ' + kok if not kok.endswith(' ') else ' ' + kok) in s:
                return no
    return GENEL_PERSONEL


@lru_cache(maxsize=None)
def _foto_yukle(no):
    for yol in sorted(FOTO_KLASORU.glob(f'{no:02d}-*.jpg')):
        try:
            with Image.open(yol) as im:
                return im.convert('RGB')
        except OSError:
            return None
    return None


def fotograf(label, boy=150):
    """Mesleğin fotoğrafını ince açık kenarlıklı daire olarak döndürür; yoksa/açılamazsa None.
    Fotoğraf kendi çözünürlüğünden fazla büyütülmez."""
    foto = _foto_yukle(meslek_no(label))
    if foto is None:
        return None
    boy = min(boy, *foto.size)
    kat = 4
    buyuk = foto.resize((boy * kat, boy * kat), Image.Resampling.LANCZOS).convert('RGBA')
    maske = Image.new('L', buyuk.size, 0)
    ImageDraw.Draw(maske).ellipse((0, 0, buyuk.width - 1, buyuk.height - 1), fill=255)
    halka = Image.new('RGBA', buyuk.size, (0, 0, 0, 0))
    ImageDraw.Draw(halka).ellipse((0, 0, buyuk.width - 1, buyuk.height - 1), outline='#f3f6f1', width=3 * kat)
    sonuc = Image.new('RGBA', buyuk.size, (0, 0, 0, 0))
    sonuc.paste(buyuk, (0, 0), maske)
    sonuc.alpha_composite(halka)
    return sonuc.resize((boy, boy), Image.Resampling.LANCZOS)


def kutu_gorseli(label, size=206):
    """Kadro kutusu görseli: fotoğraf varsa daire fotoğraf, yoksa eski vektör çizim."""
    return fotograf(label) or illustration(label, size)
