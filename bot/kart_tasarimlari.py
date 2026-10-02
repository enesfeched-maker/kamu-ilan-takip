"""Telegram ve Instagram ilan kartı (1080x1350, 4:5): tek meslekte 'Afiş', çok meslekte 'Bilet'.
Yalnız kayıttaki resmî bilgiler; boş alan gösterilmez, tahmin yok."""
import io
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from ilan_gorsel import lines
from meslek_gorseli import fotograf, meslek_no, meslekler

TR = timezone(timedelta(hours=3))
G, Y = 1080, 1350
KENAR = 64
PETROL, ANA, LIME, ACIK = '#102e35', '#174c46', '#c9f395', '#f5f7f7'
SOLUK = '#b6cbcc'
KIRMIZI, TURUNCU = '#d64545', '#e0a100'
DUZEY_ADI = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
FONT_KLASORU = Path(__file__).resolve().parent / 'fontlar'
AYLAR = 'Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık'.split()


# ---------------------------------------------------------------- yazı tipi (tek yer)
def yazi_tipi_adaylari(kalin):
    """Öncelik: repodaki Noto Sans, sonra Segoe UI, Arial (Windows/macOS), DejaVu Sans."""
    return [
        FONT_KLASORU / ('NotoSans-Bold.ttf' if kalin else 'NotoSans-Regular.ttf'),
        Path('C:/Windows/Fonts/segoeuib.ttf' if kalin else 'C:/Windows/Fonts/segoeui.ttf'),
        Path('C:/Windows/Fonts/arialbd.ttf' if kalin else 'C:/Windows/Fonts/arial.ttf'),
        Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf' if kalin else '/System/Library/Fonts/Supplemental/Arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if kalin else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]


@lru_cache(maxsize=None)
def F(boy, kalin=False):
    for yol in yazi_tipi_adaylari(kalin):
        try:
            if yol.exists():
                return ImageFont.truetype(str(yol), boy)
        except OSError:
            continue
    try:  # hiçbiri yoksa çökme: Pillow'un yerleşik yazı tipi (Türkçe harfler eksik olabilir)
        return ImageFont.load_default(boy)
    except TypeError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- veri
def _baslik(metin):
    try:
        from ilan_bot import okunakli_baslik
    except ImportError:
        return metin
    return okunakli_baslik(metin)


def _kurum_adi(kurum):
    """Okunaklı başlık biçimi; parantez içindeki kısa büyük harfli kısaltma (SEDDK) bozulmaz."""
    sonuc = _baslik(kurum)
    for kisaltma in re.findall(r'\(([A-ZÇĞİÖŞÜ0-9]{2,8})\)', kurum):
        sonuc = re.sub(r'\(' + re.escape(_baslik(kisaltma)) + r'\)', f'({kisaltma})', sonuc)
    return sonuc


def _norm(metin):
    from siniflandir import kucuk
    return kucuk(metin)


def _kurumu_at(kurum, baslik):
    """Başlık kurum adıyla başlıyorsa (büyük/küçük harf ve noktalama fark etmez) kurumu atar."""
    hedef = _norm(kurum)
    if hedef:
        for n in range(1, min(len(baslik), len(kurum) + 8) + 1):
            if _norm(baslik[:n]) == hedef:
                return baslik[n:].lstrip(' -–—:') or baslik
    return baslik


def _baslik_ozeti(ilan):
    """Kurum adı çıkarılmış ilan başlığı (kadro bilgisi olmayan ilanlar için)."""
    return _kurumu_at(ilan.get('kurum') or '', ' '.join(str(ilan.get('baslik') or '').split()))


def _kadrolar(ilan):
    """Kadro satırlarından; kadro yoksa başlıktan ('3 Öğretim Üyesi Alacak'). Duyurularda kadro gösterilmez."""
    if ilan.get('duyuru_turu'):
        return []
    sonuc = []
    for parca in meslekler(ilan.get('kadro')):
        m = re.match(r'^(\d+)\s+(.*)$', parca)
        adet, ad = (int(m.group(1)), m.group(2)) if m else (None, parca)
        sonuc.append({'adet': adet, 'ad': _baslik(ad), 'no': meslek_no(ad)})
    if not sonuc:
        m = re.search(r'(\d+)\s+([^\d]+?)\s+(?:alacak|alınacak|alim|alım)', _baslik_ozeti(ilan), re.I)
        if m:
            sonuc.append({'adet': int(m.group(1)), 'ad': _baslik(m.group(2).strip()), 'no': meslek_no(m.group(2))})
    return sonuc


def _kpss_metni(ilan):
    durum = ilan.get('kpss')
    if durum == 'kpsssiz':
        return 'KPSS şartı yok'
    if durum != 'kpss':
        return ''
    metin = ' '.join([str(ilan.get('baslik') or ''), str(ilan.get('ozet') or '')] +
                     [str(s.get('metin') or '') for s in ilan.get('sartlar') or []])
    puan = re.search(r'KPSS\s*-?\s*(P\s?\d{1,3})\b', metin, re.I)
    return 'KPSS şartı var' + (' · ' + puan.group(1).replace(' ', '').upper() if puan else '')


def _bitis(ilan):
    deger = ilan.get('son_zaman') or ilan.get('son_tarih')
    if not deger:
        return None, False
    bitis = datetime.fromisoformat(deger)
    if bitis.tzinfo is None:
        bitis = bitis.replace(tzinfo=TR, hour=23, minute=59)
    return bitis.astimezone(TR), bool(ilan.get('son_zaman'))


def veri(ilan, logo=None, simdi=None):
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    kadrolar = _kadrolar(ilan)
    m = re.search(r'Toplam\s+(\d+)\s+kişi', ilan.get('kadro') or '', re.I)
    toplam = int(m.group(1)) if m else (sum(k['adet'] or 0 for k in kadrolar) or None)
    bitis, saatli = _bitis(ilan)
    kalan = tarih = None
    if bitis:
        kalan = (bitis.date() - simdi.date()).days
        tarih = f'{bitis.day} {AYLAR[bitis.month - 1]} {bitis.year}' + (f' · {bitis:%H:%M}' if saatli else '')
    if kalan is None:
        kalan_yazi = ''
    elif kalan <= 0:
        kalan_yazi = 'Bugün son gün'
    elif kalan == 1:
        kalan_yazi = 'Yarın son gün'
    else:
        kalan_yazi = f'{kalan} gün kaldı'
    yer = ', '.join(ilan.get('iller') or []) or _baslik(str(ilan.get('yer') or ''))
    kaynaklar = [k.get('ad') for k in ilan.get('kaynaklar') or [] if k.get('ad')] or ([ilan['kaynak']] if ilan.get('kaynak') else [])
    return {
        'kurum': _kurum_adi(ilan.get('kurum') or ilan.get('baslik') or ''), 'kadrolar': kadrolar, 'toplam': toplam,
        'duzeyler': [DUZEY_ADI[d] for d in ilan.get('ogrenim') or [] if d in DUZEY_ADI], 'kpss': _kpss_metni(ilan),
        'yer': yer, 'tarih': tarih, 'kalan': kalan, 'kalan_yazi': kalan_yazi,
        'kaynak': ' · '.join(dict.fromkeys(kaynaklar)), 'logo': logo,
        'duyuru': ilan.get('duyuru_turu') or '', 'baslik_ozeti': _baslik(_baslik_ozeti(ilan)),
    }


# ---------------------------------------------------------------- çizim yardımcıları
def sigdir(d, metin, kalin, boyutlar, genislik, en_cok_satir):
    """Metni sığan en büyük boyutta kaydırır; hiçbiri sığmazsa en küçükte … ile keser. (satırlar, yazı tipi) döner."""
    for boy in boyutlar:
        yz = F(boy, kalin)
        s = lines(d, metin, yz, genislik, 99)
        if len(s) <= en_cok_satir:
            return s, yz
    yz = F(boyutlar[-1], kalin)
    return lines(d, metin, yz, genislik, en_cok_satir), yz


def blok(d, x, y, satirlar, yz, renk, aralik=None, ort=False):
    aralik = aralik or round(yz.size * 1.22)
    for s in satirlar:
        d.text((x, y), s, font=yz, fill=renk, anchor='mt' if ort else 'lt')
        y += aralik
    return y


def cip(d, x, y, metin, dolgu=ANA, yazi='#ffffff', boy=30, yuk=58, cizgi=None):
    yz = F(boy, True)
    w = round(d.textlength(metin, font=yz)) + 44
    d.rounded_rectangle((x, y, x + w, y + yuk), radius=yuk // 2, fill=dolgu, outline=cizgi, width=2 if cizgi else 0)
    d.text((x + w / 2, y + yuk / 2 + 1), metin, font=yz, fill=yazi, anchor='mm')
    return w


def cipler(d, x, y, v, azami_x, dolgu=ANA, yazi='#ffffff', cizgi=LIME, boy=30, yuk=58, bosluk=14):
    """Öğrenim, KPSS ve yer çiplerini yan yana dizer, sığmayanı alt satıra alır; bitiş y'sini döner."""
    metinler = list(v['duzeyler']) + ([v['kpss']] if v['kpss'] else []) + ([v['yer']] if v['yer'] else [])
    cx = x
    for m in metinler:
        yz = F(boy, True)
        w = round(d.textlength(m, font=yz)) + 44
        if w > azami_x - x:  # tek başına sığmayan metni kısalt
            while d.textlength(m + '…', font=yz) + 44 > azami_x - x and len(m) > 4:
                m = m[:-1]
            m = m.rstrip() + '…'
            w = round(d.textlength(m, font=yz)) + 44
        if cx + w > azami_x and cx > x:
            cx, y = x, y + yuk + bosluk
        cip(d, cx, y, m, dolgu, yazi, boy, yuk, cizgi)
        cx += w + bosluk
    return y + yuk


def logo_yerlestir(im, d, v, kutu, arka='#ffffff', yaricap=26, ic=18):
    """Resmî logoyu (varsa) beyaz yuvarlak kutuya sığdırır; büyütmez. kutu=(x0,y0,x1,y1)."""
    x0, y0, x1, y1 = kutu
    if not v['logo']:
        return False
    d.rounded_rectangle(kutu, radius=yaricap, fill=arka)
    with Image.open(io.BytesIO(v['logo'])) as m:
        m = m.convert('RGBA')
        beyaz = Image.new('RGBA', m.size, 'white')
        beyaz.alpha_composite(m)
        kutu_ = ImageChops.difference(beyaz.convert('RGB'), Image.new('RGB', m.size, 'white')).getbbox()
        if kutu_:
            m = m.crop(kutu_)
        olcek = min(1.0, (x1 - x0 - 2 * ic) / m.width, (y1 - y0 - 2 * ic) / m.height)
        m = m.resize((max(1, round(m.width * olcek)), max(1, round(m.height * olcek))), Image.Resampling.LANCZOS)
    im.paste(m, ((x0 + x1 - m.width) // 2, (y0 + y1 - m.height) // 2), m)
    return True


def kadro_ozeti(v, en_cok):
    """Kadro listesini en fazla en_cok kutuya indirir; fazlası '+K kadro daha'. Aynı meslek fotoğrafı yalnız bir kez."""
    k = v['kadrolar']
    kutular = [dict(x) for x in k] if len(k) <= en_cok else [dict(x) for x in k[:en_cok - 1]]
    kalan = len(k) - len(kutular)
    kullanilan = set()
    for x in kutular:
        x['foto'] = x['no'] not in kullanilan
        kullanilan.add(x['no'])
    if kalan > 0:
        kutular.append({'adet': None, 'ad': f'+{kalan} kadro daha', 'no': None, 'foto': False, 'ozet': True})
    return kutular


def marka_seridi(d, y, yuk=88, dolgu=ANA, renk=LIME, sag='#ffffff'):
    d.rectangle((0, y, G, y + yuk), fill=dolgu)
    d.text((KENAR, y + yuk / 2), 'Kamu İlan Takip', font=F(34, True), fill=renk, anchor='lm')
    d.text((G - KENAR, y + yuk / 2), 't.me/kamuilantakip', font=F(34, True), fill=sag, anchor='rm')


def jpeg_png(im):
    cikti = io.BytesIO()
    im.save(cikti, format='PNG')
    return cikti.getvalue()


def tr_buyuk(metin):
    return metin.replace('i', 'İ').replace('ı', 'I').upper()


def paketle(d, ogeler, yz, genislik, en_cok):
    """Öğeleri ' · ' ile satırlara öğe bölünmeden dizer."""
    satirlar, mevcut = [], ''
    for o in ogeler:
        aday = (mevcut + ' · ' + o) if mevcut else o
        if d.textlength(aday, font=yz) <= genislik:
            mevcut = aday
        else:
            satirlar.append(mevcut)
            mevcut = o
    if mevcut:
        satirlar.append(mevcut)
    return satirlar[:en_cok]


def gecis(boyut, yon, renk, a, b):
    """Kenardan içeri doğru tek renkten şeffafa geçiş. yon 'sol', 'ust' ya da 'alt': o kenar opak.
    Kenardan uzaklık oranı a'ya kadar tam opak, b'de tam şeffaf."""
    w, h = boyut
    taban = Image.linear_gradient('L').resize((w, h))  # üstten alta 0..255
    if yon == 'sol':
        u = taban.rotate(90, expand=True).resize((w, h))
    elif yon == 'ust':
        u = taban
    else:
        u = ImageOps.invert(taban)
    maske = u.point(lambda p: round(255 * (1 - min(1.0, max(0.0, (p / 255 - a) / (b - a))))))
    katman = Image.new('RGBA', boyut, renk)
    katman.putalpha(maske)
    return katman


def duyuru_seridi(im, d, v):
    """İptal/düzeltme duyurusu için en üstte tam genişlik şerit; şerit yüksekliğini (yoksa 0) döner."""
    if not v['duyuru']:
        return 0
    iptal = 'iptal' in _norm(v['duyuru'])
    d.rectangle((0, 0, G, 100), fill=KIRMIZI if iptal else TURUNCU)
    d.text((G // 2, 51), 'İPTAL DUYURUSU' if iptal else 'DÜZELTME DUYURUSU', font=F(54, True),
           fill='#ffffff' if iptal else PETROL, anchor='mm')
    return 100


def kalan_rozeti(d, v, sag, y, hatirlatma, koyu_zemin=False):
    """Kalan gün rozeti (sağa yaslı, üst kenarı y). Hatırlatmada büyük ve aciliyet renginde; yüksekliği döner."""
    if not v['kalan_yazi']:
        return 0
    if hatirlatma:
        boy, yuk = 48, 92
        if v['kalan'] is not None and v['kalan'] <= 2:
            dolgu, yazi = KIRMIZI, '#ffffff'
        elif v['kalan'] is not None and v['kalan'] <= 6:
            dolgu, yazi = TURUNCU, PETROL
        else:
            dolgu, yazi = LIME, PETROL
    else:
        boy, yuk = 40, 80
        dolgu, yazi = (LIME, PETROL) if koyu_zemin else (PETROL, LIME)
    yz = F(boy, True)
    w = round(d.textlength(v['kalan_yazi'], font=yz)) + 56
    d.rounded_rectangle((sag - w, y, sag, y + yuk), radius=yuk // 2, fill=dolgu)
    d.text((sag - w / 2, y + yuk / 2 + 1), v['kalan_yazi'], font=yz, fill=yazi, anchor='mm')
    return yuk


# ---------------------------------------------------------------- Afiş (tek meslek / kadrosuz)
def _afis_foto(no, ust_h):
    from meslek_gorseli import _foto_yukle
    foto = _foto_yukle(no)
    if foto is None:
        return None, 0
    boy = 600  # kaynak ~190 px: 3x büyütme; LANCZOS + hafif keskinleştirme
    buyuk = foto.resize((boy, boy), Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=110, threshold=2))
    return buyuk, boy


def afis(ilan, logo=None, simdi=None, hatirlatma=False):
    v = veri(ilan, logo, simdi)
    im = Image.new('RGB', (G, Y), PETROL)
    ust_h = 742
    ana = max(v['kadrolar'], key=lambda k: k['adet'] or 0) if v['kadrolar'] else None
    no = ana['no'] if ana else (meslek_no(v['baslik_ozeti']) if not v['duyuru'] else 30)
    buyuk, boy = _afis_foto(no, ust_h)
    if buyuk is not None:
        fx, fy = G - boy, ust_h - boy + 30
        kare = buyuk.convert('RGBA')  # fotoğrafın kendi kenarları petrole yumuşakça erir
        for yon, a, b in (('sol', 0.0, 0.55), ('ust', 0.0, 0.30), ('alt', 0.05, 0.50)):
            kare.alpha_composite(gecis((boy, boy), yon, PETROL, a, b))
        im.paste(kare, (fx, fy), kare)
    d = ImageDraw.Draw(im)
    d.rectangle((0, ust_h, G, Y), fill='#ffffff')
    d.rectangle((0, 0, 16, ust_h), fill=LIME)
    # başlık
    if v['duyuru'] or not ana:
        baslik = v['baslik_ozeti'] or v['kurum']
    elif len(v['kadrolar']) == 1 and ana['adet']:
        baslik = f'{ana["adet"]} {ana["ad"]} alınacak'
    elif v['toplam']:
        baslik = f'Toplam {v["toplam"]} personel alınacak'
    else:
        baslik = ana['ad']
    satirlar, yz = sigdir(d, tr_buyuk(baslik), True, [88, 80, 72, 66, 64], G - 2 * KENAR, 3)
    lh = round(yz.size * 1.12)
    liste = []
    if len(v['kadrolar']) > 1:  # aynı meslek fotoğrafını paylaşan çok kadro: kısa liste
        ogeler = [f'{k["adet"]} {k["ad"]}' if k['adet'] else k['ad'] for k in v['kadrolar'][:5]]
        if len(v['kadrolar']) > 5:
            ogeler.append(f'+{len(v["kadrolar"]) - 5} kadro daha')
        liste = paketle(d, ogeler, F(32), G - 2 * KENAR, 3)
    y = ust_h - 40 - len(satirlar) * lh - (14 + len(liste) * 42 if liste else 0)
    for s in satirlar:
        d.text((KENAR + 3, y + 3), s, font=yz, fill='#0a1c21')
        d.text((KENAR, y), s, font=yz, fill='#ffffff')
        y += lh
    if liste:
        blok(d, KENAR, y + 14, liste, F(32), LIME, aralik=42)
    duyuru_seridi(im, d, v)
    # beyaz panel
    py = ust_h + 28
    x_metin = KENAR
    if v['logo']:
        logo_yerlestir(im, d, v, (KENAR, py, KENAR + 176, py + 176), ic=8)
        d.rounded_rectangle((KENAR, py, KENAR + 176, py + 176), radius=26, outline='#d5dedd', width=3)
        x_metin = KENAR + 176 + 28
    satirlar, yz = sigdir(d, v['kurum'], True, [44, 40, 36, 32], G - KENAR - x_metin, 4)
    blok(d, x_metin, py + 4, satirlar, yz, PETROL)
    y_cip = max(py + 176, py + 4 + len(satirlar) * round(yz.size * 1.22)) + 22
    y_son = cipler(d, KENAR, y_cip, v, G - KENAR, dolgu='#e6f0ee', yazi=ANA, cizgi=None)
    cy = max(y_son + 24, 1052)
    if v['tarih'] or v['kalan_yazi']:
        d.line((KENAR, cy, G - KENAR, cy), fill='#d5dedd', width=2)
    if v['tarih']:
        d.text((KENAR, cy + 12), 'SON BAŞVURU', font=F(30), fill='#5d6f72')
        d.text((KENAR, cy + 46), v['tarih'], font=F(44, True), fill=PETROL)
    kalan_rozeti(d, v, G - KENAR, cy + 20, hatirlatma)
    if v['kaynak']:
        d.text((KENAR, cy + 106), f'Kaynak: {v["kaynak"]}', font=F(30), fill='#5d6f72')
    marka_seridi(d, Y - 88)
    return jpeg_png(im)


# ---------------------------------------------------------------- Bilet (birden çok meslek)
def bilet(ilan, logo=None, simdi=None, hatirlatma=False):
    v = veri(ilan, logo, simdi)
    im = Image.new('RGB', (G, Y), ACIK)
    d = ImageDraw.Draw(im)
    serit = duyuru_seridi(im, d, v)
    kx0, ky0, kx1, ky1 = 40, (serit + 16 if serit else 40), G - 40, 1230
    d.rounded_rectangle((kx0 + 4, ky0 + 8, kx1 + 4, ky1 + 8), radius=34, fill='#dbe3e2')
    d.rounded_rectangle((kx0, ky0, kx1, ky1), radius=34, fill='#ffffff')
    bant_h = 210 if not serit else 190
    d.rounded_rectangle((kx0, ky0, kx1, ky0 + bant_h), radius=34, fill=PETROL)
    d.rectangle((kx0, ky0 + bant_h - 40, kx1, ky0 + bant_h), fill=PETROL)
    x_metin = KENAR
    sag = G - KENAR
    logo_k = 150 if not serit else 140
    if v['logo']:
        logo_yerlestir(im, d, v, (sag - logo_k, ky0 + (bant_h - logo_k) // 2, sag, ky0 + (bant_h - logo_k) // 2 + logo_k), ic=10)
    metin_w = (sag - logo_k - 28 - x_metin) if v['logo'] else sag - x_metin
    satirlar, yz = sigdir(d, v['kurum'], True, [44, 40, 36, 32], metin_w, 4)
    yuk = len(satirlar) * round(yz.size * 1.2)
    blok(d, x_metin, ky0 + (bant_h - yuk) // 2, satirlar, yz, '#ffffff', aralik=round(yz.size * 1.2))
    y = ky0 + bant_h + 20
    if v['toplam']:
        d.text((KENAR, y), f'{v["toplam"]} kişi alınacak', font=F(72, True), fill=PETROL)
    y += 92
    tablo_ust, tablo_alt = y + 14, 905
    kutular = kadro_ozeti(v, 6)
    rh = min(170, (tablo_alt - tablo_ust) // len(kutular))
    foto_boy = min(150, rh - 20)
    d.line((KENAR, tablo_ust, sag, tablo_ust), fill='#c6d3d1', width=3)
    for i, k in enumerate(kutular):
        ry = tablo_ust + i * rh
        if k.get('ozet'):
            d.text((KENAR, ry + rh / 2), k['ad'], font=F(36, True), fill='#5d6f72', anchor='lm')
        else:
            f = fotograf(k['ad'], foto_boy) if k.get('foto') else None
            if f is not None:
                im.paste(f, (KENAR, ry + (rh - f.height) // 2), f)
            else:
                dot = max(20, foto_boy // 3)
                d.ellipse((KENAR + (foto_boy - dot) // 2, ry + (rh - dot) // 2, KENAR + (foto_boy + dot) // 2, ry + (rh + dot) // 2), fill=ANA)
            tx = KENAR + foto_boy + 24
            satirlar, yz = sigdir(d, k['ad'], True, [38, 34, 30], sag - 150 - tx, 2)
            lh = round(yz.size * 1.2)
            for n, s in enumerate(satirlar):
                d.text((tx, ry + rh / 2 + (n - (len(satirlar) - 1) / 2) * lh + 2), s, font=yz, fill=PETROL, anchor='lm')
            if k['adet']:
                d.text((sag, ry + rh / 2 + 2), str(k['adet']), font=F(64, True), fill=ANA, anchor='rm')
        d.line((KENAR, ry + rh, sag, ry + rh), fill='#c6d3d1', width=2)
    ty = 940
    for x in range(KENAR, sag, 26):
        d.line((x, ty, min(x + 13, sag), ty), fill='#9fb2b0', width=3)
    d.ellipse((kx0 - 30, ty - 30, kx0 + 30, ty + 30), fill=ACIK)
    d.ellipse((kx1 - 30, ty - 30, kx1 + 30, ty + 30), fill=ACIK)
    y_son = cipler(d, KENAR, ty + 34, v, sag, dolgu='#e6f0ee', yazi=ANA, cizgi=None)
    cy = y_son + 26
    if v['tarih']:
        d.text((KENAR, cy), 'SON BAŞVURU', font=F(30), fill='#5d6f72')
        d.text((KENAR, cy + 36), v['tarih'], font=F(44, True), fill=PETROL)
    kalan_rozeti(d, v, sag, cy + (0 if hatirlatma else 8), hatirlatma, koyu_zemin=True)
    if v['kaynak']:
        d.text((KENAR, cy + 94), f'Kaynak: {v["kaynak"]}', font=F(30), fill='#5d6f72')
    marka_seridi(d, Y - 88)
    return jpeg_png(im)


# ---------------------------------------------------------------- giriş
def tasarim_secimi(ilan):
    """Farklı meslek fotoğrafı >= 2 ya da 3+ kadro satırı varsa 'bilet' (tablo en düzenlisi); aksi halde,
    ya da kadro bilgisi yoksa, 'afis'."""
    kadrolar = _kadrolar(ilan)
    return 'bilet' if len({k['no'] for k in kadrolar}) >= 2 or len(kadrolar) >= 3 else 'afis'


def ilan_karti(ilan, logo=None, simdi=None, hatirlatma=False):
    """İlan için 1080x1350 PNG baytı: tek meslekte afiş, çok meslekte bilet."""
    tasarim = bilet if tasarim_secimi(ilan) == 'bilet' else afis
    return tasarim(ilan, logo, simdi, hatirlatma)


# ---------------------------------------------------------------- Toplu son gün kartı (Bilet dili)
TOPLU_EN_COK_SATIR = 7


def toplu_satir(ilan):
    """Toplu kart satırı için (kurum, kadro özeti); yalnız kayıttaki bilgi."""
    v = veri(ilan)
    kadrolar = [f'{k["adet"]} {k["ad"]}' if k['adet'] else k['ad'] for k in v['kadrolar']]
    if kadrolar:
        kadro = ', '.join(kadrolar[:2]) + (f' +{len(kadrolar) - 2}' if len(kadrolar) > 2 else '')
    else:
        kadro = v['baslik_ozeti']
    return v['kurum'], kadro


def tek_satir(d, metin, boyutlar, genislik, kalin=False):
    """Metni tek satıra sığan en büyük boyutta döndürür (yazı tipi, metin); sığmazsa en küçükte … ile keser."""
    metin = ' '.join(str(metin or '').split())
    for boy in boyutlar:
        yz = F(boy, kalin)
        if d.textlength(metin, font=yz) <= genislik:
            return yz, metin
    yz = F(boyutlar[-1], kalin)
    while len(metin) > 4 and d.textlength(metin + '…', font=yz) > genislik:
        metin = metin[:-1]
    return yz, metin.rstrip() + '…'


def toplu_son_gun_karti(ilanlar, simdi=None):
    """Son başvurusu yaklaşan ilanların tek kartı (1080x1350 PNG): en fazla 7 satır + '+N ilan daha'.
    Satır: kurum + kadro özeti, sağda kalan gün rozeti (bugün/yarın kırmızı, 2-3 gün turuncu)."""
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    im = Image.new('RGB', (G, Y), ACIK)
    d = ImageDraw.Draw(im)
    kx0, ky0, kx1, ky1 = 40, 40, G - 40, 1230
    d.rounded_rectangle((kx0 + 4, ky0 + 8, kx1 + 4, ky1 + 8), radius=34, fill='#dbe3e2')
    d.rounded_rectangle((kx0, ky0, kx1, ky1), radius=34, fill='#ffffff')
    bant_h = 210
    d.rounded_rectangle((kx0, ky0, kx1, ky0 + bant_h), radius=34, fill=PETROL)
    d.rectangle((kx0, ky0 + bant_h - 40, kx1, ky0 + bant_h), fill=PETROL)
    sag = G - KENAR
    d.text((KENAR, ky0 + 50), 'KAMU İLAN TAKİP', font=F(28, True), fill=LIME, anchor='lm')
    satirlar, yz = sigdir(d, 'Son başvurusu yaklaşan ilanlar', True, [60, 54, 48], sag - KENAR, 2)
    blok(d, KENAR, ky0 + 86, satirlar, yz, '#ffffff', aralik=round(yz.size * 1.12))
    d.text((sag, ky0 + 50), f'{simdi.day} {AYLAR[simdi.month - 1]} {simdi.year}', font=F(30, True), fill=SOLUK, anchor='rm')

    gorunen = ilanlar[:TOPLU_EN_COK_SATIR]
    fazla = len(ilanlar) - len(gorunen)
    alan_ust = ky0 + bant_h + 14
    alan_alt = ky1 - 24 - (64 if fazla else 0)
    rh = min(138, (alan_alt - alan_ust) // max(1, len(gorunen)))
    d.line((KENAR, alan_ust, sag, alan_ust), fill='#c6d3d1', width=3)
    for n, ilan in enumerate(gorunen):
        ry = alan_ust + n * rh
        kurum, kadro = toplu_satir(ilan)
        bitis, _ = _bitis(ilan)
        kalan = (bitis.date() - simdi.date()).days if bitis else None
        rozet = None if kalan is None else ('Bugün' if kalan <= 0 else 'Yarın' if kalan == 1 else f'{kalan} gün')
        rozet_w = 0
        if rozet:
            yr = F(38, True)
            rozet_w = round(d.textlength(rozet, font=yr)) + 44
            dolgu, yazi = (KIRMIZI, '#ffffff') if kalan <= 1 else (TURUNCU, PETROL)
            d.rounded_rectangle((sag - rozet_w, ry + (rh - 62) // 2, sag, ry + (rh - 62) // 2 + 62), radius=31, fill=dolgu)
            d.text((sag - rozet_w / 2, ry + rh / 2 + 1), rozet, font=yr, fill=yazi, anchor='mm')
        genislik = sag - KENAR - (rozet_w + 24 if rozet else 0)
        yk, ktxt = tek_satir(d, kurum, [40, 36, 32, 30], genislik, True)
        yd, dtxt = tek_satir(d, kadro, [32, 30, 28], genislik)
        d.text((KENAR, ry + rh / 2 - 18), ktxt, font=yk, fill=PETROL, anchor='lm')
        d.text((KENAR, ry + rh / 2 + 24), dtxt, font=yd, fill='#5d6f72', anchor='lm')
        d.line((KENAR, ry + rh, sag, ry + rh), fill='#c6d3d1', width=2)
    if fazla:
        d.text((KENAR, alan_ust + len(gorunen) * rh + 32), f'+{fazla} ilan daha', font=F(36, True), fill='#5d6f72', anchor='lm')
    marka_seridi(d, Y - 88)
    return jpeg_png(im)
