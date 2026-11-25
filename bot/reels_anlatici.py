"""Anlatıcı biçimi (24 Kasım 2026): 3B kadın sunucu (altta) + üstte defter sayfasında hareketli grafikler + kelime kelime altyazı.

Rakip kalıbı: "60 aldın, atanamazsın diyenler yalan söyledi; liste yaz, DM'den göndereyim". Bizde DM yok: izleyici
kpsstercihi.com'a yönlendirilir. Müzik yok (kullanıcı kararı); yalnız ses + kısa efektler.
Girdiler: Gemini TTS seslendirmesi (bot/yz_medya.py, Actions), sunucu görselinden SadTalker ile üretilmiş dudak senkronlu
video (yz-konusma.yml) ve sesin faster-whisper kelime zamanları. Kelime zamanları altyazıyı ve grafik girişlerini sürer.
İlk kare kapaktır (60 rozeti + "atanamazsın" kartı hazır durur).
Örnek ilanların her bilgisi sitedeki ilan kaydının şart metninden elle alınmıştır (24 Kasım 2026'da açık ilanlar).

Kullanım: python bot/reels_anlatici.py --ses anlatim.wav --kelimeler kelime.json --sunucu sunucu.mp4 [--cikti klasör]"""
import argparse
import difflib
import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
ORNEK_HIZI = 48000
SUNUCU_Y = 1001          # sunucu videosunun üst kenarı (defter sayfası biraz üstüne biner)
ALTYAZI_Y = 1098         # sunucunun başı üstünde: ağzı kapatmasın

# Renkler (elwyn.co "Midnight + Marigold" ailesi: lacivert zemin, krem kâğıt, turuncu/sarı vurgu; yeşil yok)
LACI, LACI2, GECE = '#13233f', '#1d3157', '#0b1529'
KREM, KAGIT_CIZGI, KENAR = '#fdf6e7', '#d9e3f2', '#e8b4a8'
TURUNCU, SARI, KIRMIZI, MAVI = '#f7931e', '#ffd23f', '#e63946', '#2f6fdd'
YAZI, SOLUK = '#1b2236', '#6b7280'
SITE_LACI, SITE_LACI2, SITE_TURUNCU, SITE_K = '#0c1d2a', '#132b3d', '#f89c1c', '#c6f432'

BX0, BY0, BX1, BY1 = 44, 318, 1036, 1040        # defter sayfası


# ---------------------------------------------------------------- yazı tipleri
def _font(adlar, boy):
    for ad in adlar:
        for kok in (Path(__file__).resolve().parent / 'fontlar', Path('C:/Windows/Fonts')):
            if (kok / ad).is_file():
                return ImageFont.truetype(str(kok / ad), boy)
    from kart_tasarimlari import F
    return F(boy, True)


def KALIN(boy):
    return _font(['seguibl.ttf', 'ariblk.ttf', 'NotoSans-Bold.ttf'], boy)


def YARI(boy):
    return _font(['segoeuib.ttf', 'NotoSans-SemiBold.ttf', 'NotoSans-Bold.ttf'], boy)


def NORMAL(boy):
    return _font(['segoeui.ttf', 'NotoSans-Regular.ttf'], boy)


def EL(boy):
    return _font(['segoeprb.ttf', 'comicbd.ttf', 'NotoSans-Bold.ttf'], boy)


_OLC = ImageDraw.Draw(Image.new('RGB', (8, 8)))


def genislik(metin, font):
    return _OLC.textlength(metin, font=font)


# ---------------------------------------------------------------- yardımcılar
def kis(p):
    return max(0.0, min(1.0, p))


def yumusak(p):
    p = kis(p)
    return p * p * (3 - 2 * p)


def esnek(p):
    """Hafif taşmalı yaylanma (0→1)."""
    p = kis(p)
    return 1 + 2.2 * (p - 1) ** 3 + 1.2 * (p - 1) ** 2 if p < 1 else 1.0


def kat_yazi(metin, font, renk, cizgi=0, cizgi_renk='#000000'):
    x0, y0, x1, y1 = _OLC.textbbox((0, 0), metin, font=font, stroke_width=cizgi)
    im = Image.new('RGBA', (x1 - x0 + 4, y1 - y0 + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - x0, 2 - y0), metin, font=font, fill=renk, stroke_width=cizgi, stroke_fill=cizgi_renk)
    return im


def kutu(w, h, dolgu, r=28, golge=True, cizgi=None, kalinlik=4):
    pay = 24 if golge else 0
    im = Image.new('RGBA', (w + 2 * pay, h + 2 * pay), (0, 0, 0, 0))
    if golge:
        g = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((pay, pay + 10, pay + w, pay + h + 10), r, fill=(10, 20, 40, 70))
        im = Image.alpha_composite(im, g.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pay, pay, pay + w - 1, pay + h - 1), r, fill=dolgu, outline=cizgi, width=kalinlik if cizgi else 0)
    return im, pay


def ortala(im, kat, cx, cy):
    im.alpha_composite(kat, (round(cx - kat.width / 2), round(cy - kat.height / 2)))


def ortala_rgb(im, kat, cx, cy):
    im.paste(kat, (round(cx - kat.width / 2), round(cy - kat.height / 2)), kat)


def dondur(kat, aci):
    return kat.rotate(aci, resample=Image.Resampling.BICUBIC, expand=True) if aci else kat


def opak(kat, a):
    if a >= 1:
        return kat
    k = kat.copy()
    k.putalpha(k.getchannel('A').point(lambda v: int(v * a)))
    return k


# ---------------------------------------------------------------- öğe (giriş/çıkış animasyonlu katman)
class Oge:
    """kat: sabit katman ya da f(t_yerel) → katman. (cx, cy) merkez. giris: yok|pop|muhur|kay. ses: pop|muhur|hus|None."""

    def __init__(self, kat, cx, cy, t0, t1=None, giris='pop', ses='pop', aci=0.0):
        self.kat, self.cx, self.cy, self.t0, self.t1 = kat, cx, cy, t0, t1
        self.giris, self.ses, self.aci = giris, ses, aci

    def ciz(self, im, t):
        if t < self.t0 or (self.t1 is not None and t >= self.t1 + 0.25):
            return
        kat = self.kat(t - self.t0) if callable(self.kat) else self.kat
        if kat is None:
            return
        kat = dondur(kat, self.aci)
        p = t - self.t0
        olcek, a, dy = 1.0, 1.0, 0.0
        if self.giris == 'pop':
            olcek, a = 0.55 + 0.45 * esnek(p / 0.38), kis(p / 0.12)
        elif self.giris == 'muhur':
            q = yumusak(p / 0.16)
            olcek, a = 1.7 - 0.7 * q, q
        elif self.giris == 'kay':
            q = yumusak(p / 0.3)
            dy, a = 70 * (1 - q), q
        if self.t1 is not None and t > self.t1:
            q = kis((t - self.t1) / 0.25)
            a *= 1 - q
            olcek *= 1 - 0.12 * q
        if a <= 0.01:
            return
        if abs(olcek - 1) > 0.004:
            kat = kat.resize((max(1, round(kat.width * olcek)), max(1, round(kat.height * olcek))), Image.Resampling.BILINEAR)
        ortala(im, opak(kat, a), self.cx, self.cy + dy)


# ---------------------------------------------------------------- senaryo
# Altyazıda görünen metin; seslendirme bot/yz_medya.py METIN'dir (sayılar orada yazıyla). Bölümler grafik sahneleridir.
SEGMENTLER = [
    dict(ad='kanca', yazi="KPSS'den 60 aldın diye, “atanamazsın” diyenler sana yanlış söylemiş."),
    dict(ad='moral', yazi='Çoğu kişi puanını görünce morali bozuluyor, ilanlara bakmıyor bile.'),
    dict(ad='liste', yazi='Oysa şu an en az 60 isteyen açık ilanlar var. Biz her gün hepsini tek tek okuyoruz.'),
    dict(ad='ornek', yazi='Mesela İçişleri Bakanlığı 1.170 sözleşmeli personel alıyor; lise, önlisans, lisans. '
                          'Eyyübiye Belediyesi 9 zabıta memuru alıyor. Bartın Üniversitesi önlisans mezunu büro personeli arıyor. '
                          'Üçünde de şart: en az 60.'),
    dict(ad='site', yazi="Hepsini videoya sığdıramam. DM'ye yazmana da gerek yok. kpsstercihi.com'a gir, arama kutusuna "
                         'kadronu ya da bölümünü yaz. Sana uyan ilanlar karşına çıksın.'),
    dict(ad='paylas', yazi="Atanmak isteyen, KPSS'ye hazırlanan bir arkadaşına bu videoyu gönder. O da bilsin."),
]
SON_SURE = 2.2
# Sesin okunuşu ile altyazı yazımı farklı olan sözcükler (hizalama için)
ESDEGER = {'60': 'altmış', '1170': 'binyüzyetmiş', '9': 'dokuz'}

ORNEKLER = [  # sitedeki ilan kayıtlarından (24 Kasım 2026)
    dict(no='1', kurum='İÇİŞLERİ BAKANLIĞI', ne='1.170 sözleşmeli personel', cip=('Lise · Önlisans · Lisans', 'Başvuru 7–11 Aralık')),
    dict(no='2', kurum='EYYÜBİYE BELEDİYESİ', ne='9 zabıta memuru · Şanlıurfa', cip=('Lisans', 'Başvuru 7–10 Aralık')),
    dict(no='3', kurum='BARTIN ÜNİVERSİTESİ', ne='Büro personeli · Bartın', cip=('Önlisans', 'Son gün 5 Aralık')),
]
LISTE = ['İçişleri Bakanlığı', 'Eyyübiye Belediyesi', 'Bartın Üniversitesi', 'Karabağlar Belediyesi', 'Gündoğmuş Belediyesi']
ZABITA = [('İZMİR BÜYÜKŞEHİR BLD.', '90 zabıta memuru', '30 Kasım – 4 Aralık'),
          ('GAZİOSMANPAŞA BLD.', '36 zabıta memuru', '7 – 11 Aralık'),
          ('EYYÜBİYE BELEDİYESİ', '9 zabıta memuru', '7 – 10 Aralık'),
          ('ULA BELEDİYESİ', '4 zabıta memuru', '21 – 23 Aralık')]


def nrm(s):
    s = s.replace('İ', 'i').replace('I', 'ı').lower()
    return re.sub(r"[^0-9a-zçğıöşüâî]", '', s)


# ---------------------------------------------------------------- ses ve kelime zamanları
def ffmpeg_yolu():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def wav_oku(yol):
    """Ses dosyasını 48 kHz mono float diziye çevirir."""
    p = subprocess.run([ffmpeg_yolu(), '-loglevel', 'error', '-i', str(yol), '-f', 's16le', '-ac', '1', '-ar', str(ORNEK_HIZI), '-'],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768


def _kok(s):
    n = nrm(s)
    return ESDEGER.get(n, n)


def kelimeleri_hizala(duyulan):
    """Altyazı sözcüklerine (SEGMENTLER) whisper'ın duyduğu sözcüklerin zamanını verir. Harf düzeyinde hizalar: whisper bir
    sözcüğü ikiye bölse ya da yanlış duysa da zamanlar doğru yere düşer. duyulan: [[bas, son, söz], ...]"""
    hedef = [(sg['ad'], k) for sg in SEGMENTLER for k in sg['yazi'].split()]
    # her iki tarafı harf dizisine aç; her harf sahibinin sırasını taşır
    h_harf, h_sahip = [], []
    for i, (_, k) in enumerate(hedef):
        for c in _kok(k):
            h_harf.append(c)
            h_sahip.append(i)
    d_harf, d_zaman = [], []
    for b, e, k in duyulan:
        kk = _kok(k)
        for j, c in enumerate(kk):
            d_harf.append(c)
            d_zaman.append(b + (e - b) * j / max(1, len(kk)))
    bas = [None] * len(hedef)
    son = [None] * len(hedef)
    sm = difflib.SequenceMatcher(None, h_harf, d_harf, autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for x in range(n):
            i, t = h_sahip[a + x], d_zaman[b + x]
            bas[i] = t if bas[i] is None else min(bas[i], t)
            son[i] = t if son[i] is None else max(son[i], t)
    # eşleşmeyenleri komşulardan doldur
    bilinen = [i for i in range(len(hedef)) if bas[i] is not None]
    for i in range(len(hedef)):
        if bas[i] is None:
            onceki = max((j for j in bilinen if j < i), default=None)
            sonraki = min((j for j in bilinen if j > i), default=None)
            t0 = son[onceki] if onceki is not None else 0.0
            t1 = bas[sonraki] if sonraki is not None else t0 + 0.4
            bas[i], son[i] = t0 + (t1 - t0) * 0.2, t0 + (t1 - t0) * 0.8
    for i in range(len(hedef)):
        son[i] = max(son[i] + 0.08, bas[i] + 0.12)
    return [dict(bas=bas[i], son=son[i], yazi=k, bolum=ad) for i, (ad, k) in enumerate(hedef)]


def efekt(tur):
    t = np.arange(int(ORNEK_HIZI * {'pop': 0.09, 'muhur': 0.22, 'hus': 0.32}[tur])) / ORNEK_HIZI
    rng = np.random.default_rng(7)
    if tur == 'pop':
        f = 950 * np.exp(-t * 22) + 260
        return 0.35 * np.sin(2 * np.pi * np.cumsum(f) / ORNEK_HIZI) * np.exp(-t * 38)
    if tur == 'muhur':
        gum = np.sin(2 * np.pi * (110 * t - 60 * t * t)) * np.exp(-t * 18)
        gur = np.convolve(rng.standard_normal(len(t)), np.ones(12) / 12, 'same') * np.exp(-t * 45)
        return 0.55 * gum + 0.35 * gur
    g = np.convolve(rng.standard_normal(len(t)), np.ones(30) / 30, 'same')
    return 0.5 * g * np.sin(np.pi * t / t[-1]) ** 2


def karistir(ses, efektler, toplam):
    """Ses + kısa efektler; müzik yok. Konuşma -16 dBFS civarına getirilir, tepeler yumuşak kırpılır."""
    n = int(toplam * ORNEK_HIZI)
    ses = ses[:n] if len(ses) >= n else np.pad(ses, (0, n - len(ses)))
    rms = np.sqrt(np.mean(ses[np.abs(ses) > 0.01] ** 2))
    karisim = ses * (0.16 / max(rms, 1e-4))
    for an, tur in efektler:
        e = efekt(tur) * 0.35
        i = int(an * ORNEK_HIZI)
        if i < n:
            karisim[i:i + len(e)] += e[:n - i]
    return np.tanh(karisim * 1.4) / np.tanh(1.4) * 0.92


def wav_yaz(dizi, yol):
    with wave.open(str(yol), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ORNEK_HIZI)
        w.writeframes((np.clip(dizi, -1, 1) * 32767).astype(np.int16).tobytes())


def sunucu_kareleri(yol, toplam):
    """Sunucu videosunu 30 fps, 1080 genişliğe ölçeklenmiş RGB karelere açar; video bitince son kare tutulur."""
    import imageio_ffmpeg
    oku = imageio_ffmpeg.read_frames(str(yol), output_params=['-vf', f'fps={FPS},scale={W}:-2'], pix_fmt='rgb24')
    meta = next(oku)
    w, h = meta['size']
    son = None
    for _ in range(int(math.ceil(toplam * FPS)) + 1):
        try:
            veri = next(oku)
            son = Image.frombuffer('RGB', (w, h), veri, 'raw', 'RGB', 0, 1).copy()
        except StopIteration:
            pass
        yield son


# ---------------------------------------------------------------- sabit zemin
def zemin():
    im = Image.new('RGB', (W, H), GECE)
    d = ImageDraw.Draw(im)
    # oda: yukarıdan aşağı koyulaşan lacivert
    ust, alt = np.array((31, 50, 88)), np.array((12, 22, 42))
    for y in range(H):
        p = y / H
        d.line((0, y, W, y), fill=tuple(int(v) for v in ust * (1 - p) + alt * p))
    # defter sayfası
    sayfa, pay = kutu(BX1 - BX0, BY1 - BY0, KREM, 40)
    ds = ImageDraw.Draw(sayfa)
    for y in range(pay + 120, pay + BY1 - BY0 - 20, 58):
        ds.line((pay + 20, y, pay + BX1 - BX0 - 20, y), fill=KAGIT_CIZGI, width=3)
    ds.line((pay + 92, pay + 20, pay + 92, pay + BY1 - BY0 - 20), fill=KENAR, width=3)
    im.paste(sayfa, (BX0 - pay, BY0 - pay), sayfa)
    for x in range(BX0 + 70, BX1 - 40, 74):     # spiral halkalar
        d.ellipse((x - 13, BY0 - 13, x + 13, BY0 + 13), fill=GECE)
        d.rounded_rectangle((x - 5, BY0 - 34, x + 5, BY0 + 4), 5, fill='#c9ced8')
    # üst başlık hapları
    _baslik(im)
    return im


def _baslik(im):
    f1 = KALIN(54)
    parcalar = [("KPSS'DEN ", LACI), ('60', '#e8590c'), (' MI ALDIN?', LACI)]
    w1 = sum(genislik(s, f1) for s, _ in parcalar) + 80
    hap, pay = kutu(round(w1), 96, '#ffffff', 48)
    d = ImageDraw.Draw(hap)
    x = pay + 40
    for s, c in parcalar:
        d.text((x, pay + 48), s, font=f1, fill=c, anchor='lm')
        x += genislik(s, f1)
    ortala_rgb(im, hap, W / 2, 112)
    f2 = KALIN(62)
    w_hala = genislik('HÂLÂ', f2) + 36
    w2 = w_hala + genislik(' ATANABİLİRSİN!', f2) + 70
    hap, pay = kutu(round(w2), 108, SARI, 54)
    d = ImageDraw.Draw(hap)
    d.rounded_rectangle((pay + 22, pay + 14, pay + 22 + w_hala, pay + 94), 24, fill=KIRMIZI)
    d.text((pay + 22 + w_hala / 2, pay + 56), 'HÂLÂ', font=f2, fill='#ffffff', anchor='mm')
    d.text((pay + 22 + w_hala, pay + 56), ' ATANABİLİRSİN!', font=f2, fill=LACI, anchor='lm')
    ortala_rgb(im, hap, W / 2, 226)


# ---------------------------------------------------------------- grafikler
def damga(metin, boy, renk=KIRMIZI):
    f = KALIN(boy)
    w = round(genislik(metin, f)) + 70
    h = round(boy * 1.5)
    k = Image.new('RGBA', (w + 20, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.rounded_rectangle((10, 10, w + 10, h + 10), 18, outline=renk, width=9)
    d.text((w / 2 + 10, h / 2 + 12), metin, font=f, fill=renk, anchor='mm')
    # mürekkep dokusu: rastgele boşluklar
    rng = np.random.default_rng(3)
    al = np.array(k.getchannel('A'), dtype=np.float32)
    al *= (rng.random(al.shape) > 0.07) * 0.92
    k.putalpha(Image.fromarray(al.astype(np.uint8)))
    return k


def puan_rozeti(cap=330):
    k = Image.new('RGBA', (cap + 40, cap + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.ellipse((24, 32, cap + 24, cap + 32), fill=(10, 20, 40, 60))
    k = k.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(k)
    d.ellipse((20, 20, cap + 20, cap + 20), fill='#ffffff', outline=KIRMIZI, width=18)
    d.text((cap / 2 + 20, cap / 2 + 10), '60', font=KALIN(round(cap * 0.46)), fill=KIRMIZI, anchor='mm')
    d.text((cap / 2 + 20, cap * 0.78 + 20), 'puan', font=YARI(round(cap * 0.1)), fill=SOLUK, anchor='mm')
    return k


def el_karti(metin, boy=72, w=560, h=170):
    k, pay = kutu(w, h, '#ffffff', 16)
    d = ImageDraw.Draw(k)
    d.rectangle((pay + w / 2 - 70, pay - 14, pay + w / 2 + 70, pay + 20), fill=(255, 226, 120, 200))   # bant
    d.text((pay + w / 2, pay + h / 2 + 4), metin, font=EL(boy), fill=LACI, anchor='mm')
    return k


def hap(metin, dolgu, renk='#ffffff', boy=46, yatay=40, yuk=None):
    f = KALIN(boy)
    w = round(genislik(metin, f)) + 2 * yatay
    h = yuk or round(boy * 1.9)
    k, pay = kutu(w, h, dolgu, h // 2)
    ImageDraw.Draw(k).text((pay + w / 2, pay + h / 2 + 2), metin, font=f, fill=renk, anchor='mm')
    return k


def ok_asagi(d, x, y, boy, renk):
    d.rectangle((x - boy * 0.14, y, x + boy * 0.14, y + boy * 0.6), fill=renk)
    d.polygon([(x - boy * 0.42, y + boy * 0.5), (x + boy * 0.42, y + boy * 0.5), (x, y + boy)], fill=renk)


def sonuc_karti():
    k, pay = kutu(640, 250, '#ffffff', 30)
    d = ImageDraw.Draw(k)
    d.rounded_rectangle((pay, pay, pay + 640, pay + 70), 30, fill=LACI)
    d.rectangle((pay, pay + 40, pay + 640, pay + 70), fill=LACI)
    d.text((pay + 320, pay + 36), 'KPSS SONUCUN', font=KALIN(36), fill='#ffffff', anchor='mm')
    f = KALIN(92)
    w1 = genislik('puanın: ', YARI(64))
    x0 = pay + 320 - (w1 + genislik('60', f)) / 2
    d.text((x0, pay + 168), 'puanın: ', font=YARI(64), fill=YAZI, anchor='lm')
    d.text((x0 + w1, pay + 166), '60', font=f, fill=KIRMIZI, anchor='lm')
    return k


def uzgun_yuz():
    k = Image.new('RGBA', (500, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.ellipse((10, 10, 170, 170), fill=SARI, outline='#e0a800', width=6)
    d.ellipse((52, 62, 72, 88), fill=LACI)
    d.ellipse((108, 62, 128, 88), fill=LACI)
    d.arc((50, 110, 130, 160), 200, 340, fill=LACI, width=8)
    d.text((192, 86), 'moral', font=EL(58), fill=LACI, anchor='lm')
    ok_asagi(d, 410, 40, 70, KIRMIZI)
    ok_asagi(d, 456, 76, 70, KIRMIZI)
    return k


def cizik(p, w=440):
    k = Image.new('RGBA', (w + 20, 60), (0, 0, 0, 0))
    q = yumusak(p / 0.25)
    if q > 0:
        ImageDraw.Draw(k).line((10, 44, 10 + w * q, 14), fill=KIRMIZI, width=9)
    return k


def liste_basligi():
    f = KALIN(50)
    parca = [('En az ', LACI), ('60', '#e8590c'), (' isteyen açık ilanlar', LACI)]
    w = sum(genislik(s, f) for s, _ in parca)
    k = Image.new('RGBA', (round(w) + 10, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    x = 5
    for s, c in parca:
        d.text((x, 40), s, font=f, fill=c, anchor='lm')
        if s == '60':
            d.line((x, 78, x + genislik(s, f), 74), fill=TURUNCU, width=8)
        x += genislik(s, f)
    return k


def liste_satiri(ad):
    k, pay = kutu(820, 84, '#ffffff', 22, golge=False, cizgi='#e2e6ee', kalinlik=3)
    d = ImageDraw.Draw(k)
    d.ellipse((pay + 16, pay + 14, pay + 72, pay + 70), fill=LACI)
    d.text((pay + 44, pay + 43), ad[0], font=KALIN(30), fill='#ffffff', anchor='mm')
    d.text((pay + 92, pay + 43), ad, font=YARI(38), fill=YAZI, anchor='lm')
    d.rounded_rectangle((pay + 610, pay + 20, pay + 712, pay + 64), 22, fill=TURUNCU)
    d.text((pay + 661, pay + 43), '60+', font=KALIN(30), fill='#ffffff', anchor='mm')
    d.ellipse((pay + 734, pay + 18, pay + 782, pay + 66), fill=MAVI)
    d.line((pay + 746, pay + 43, pay + 756, pay + 54, pay + 772, pay + 32), fill='#ffffff', width=7, joint='curve')
    return k


def buyutec():
    k = Image.new('RGBA', (170, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.line((100, 100, 158, 158), fill=LACI, width=22)
    d.ellipse((8, 8, 118, 118), fill=(255, 255, 255, 90), outline=LACI, width=14)
    return k


def ornek_karti(o):
    w, h = 900, 186
    k, pay = kutu(w, h, '#ffffff', 28)
    d = ImageDraw.Draw(k)
    d.ellipse((pay + 22, pay + 26, pay + 96, pay + 100), fill=LACI)
    d.text((pay + 59, pay + 64), o['no'], font=KALIN(44), fill=SARI, anchor='mm')
    d.text((pay + 120, pay + 50), o['kurum'], font=KALIN(42), fill=YAZI, anchor='lm')
    d.text((pay + 120, pay + 104), o['ne'], font=YARI(36), fill='#c2410c', anchor='lm')
    x = pay + 120
    for i, c in enumerate(o['cip']):
        f = YARI(28)
        cw = genislik(c, f) + 34
        d.rounded_rectangle((x, pay + 132, x + cw, pay + 172), 20, fill='#eef2f9' if i == 0 else '#fff1dd')
        d.text((x + cw / 2, pay + 152), c, font=f, fill=LACI, anchor='mm')
        x += cw + 14
    return k


def uzun_kagit(p):
    """Videoya sığmayan uzun ilan listesi: aşağı doğru uzayan kâğıt."""
    uz = 380 + 300 * yumusak(p / 0.8)
    k = Image.new('RGBA', (440, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.rectangle((24, 24, 416, 24 + uz), fill='#ffffff', outline='#d6dbe4', width=4)
    d.text((220, 70), 'İLANLAR', font=KALIN(44), fill=LACI, anchor='mm')
    y = 124
    while y < 24 + uz - 20:
        d.rounded_rectangle((56, y, 76, y + 20), 6, fill=TURUNCU)
        d.rounded_rectangle((92, y + 2, 92 + 230 + (y * 37) % 70, y + 18), 8, fill='#cfd6e2')
        y += 44
    return k


def dm_ikonu(p_carpi):
    k = Image.new('RGBA', (360, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.rounded_rectangle((30, 30, 330, 210), 60, fill=LACI)
    d.polygon([(90, 200), (150, 200), (80, 270)], fill=LACI)
    d.text((180, 120), 'DM', font=KALIN(96), fill='#ffffff', anchor='mm')
    q = yumusak(p_carpi / 0.25)
    if q > 0:
        d.line((40, 40, 40 + 280 * q, 40 + 220 * q), fill=KIRMIZI, width=26)
        if q > 0.5:
            r = yumusak((q - 0.5) * 2)
            d.line((320, 40, 320 - 280 * r, 40 + 220 * r), fill=KIRMIZI, width=26)
    return k


def logo(boy):
    k = Image.new('RGBA', (boy, boy), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.rounded_rectangle((0, 0, boy - 1, boy - 1), boy // 4, fill='#000000')
    d.text((boy / 2, boy / 2 + 2), 'K', font=KALIN(round(boy * 0.66)), fill=SITE_K, anchor='mm')
    return k


TEL_W, TEL_H, TEL_Y, ARA_Y = 660, 750, 680, 235   # telefon tuvali, merkezi ve ekrandaki arama satırı


def telefon(tl, t_ara, t_yaz, t_sonuc):
    """kpsstercihi.com ekranı. tl: telefonun girişinden beri geçen sn; diğerleri telefona göre sn."""
    k = Image.new('RGBA', (TEL_W, TEL_H), (0, 0, 0, 0))
    g = Image.new('RGBA', k.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle((30, 44, TEL_W - 30, TEL_H - 20), 60, fill=(0, 0, 0, 90))
    k = Image.alpha_composite(k, g.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(k)
    d.rounded_rectangle((30, 30, TEL_W - 30, TEL_H - 30), 62, fill='#111418')
    x0, y0, x1, y1 = 46, 46, TEL_W - 46, TEL_H - 46
    ekran = Image.new('RGBA', (x1 - x0, y1 - y0), SITE_LACI)
    e = ImageDraw.Draw(ekran)
    ew = x1 - x0
    # adres çubuğu
    e.rectangle((0, 0, ew, 80), fill='#eef0f3')
    e.rounded_rectangle((26, 18, ew - 26, 64), 23, fill='#ffffff')
    e.text((ew / 2, 41), 'kpsstercihi.com', font=YARI(28), fill=YAZI, anchor='mm')
    # site üst şeridi
    e.rectangle((0, 80, ew, 150), fill='#0a1822')
    ekran.alpha_composite(logo(48), (24, 91))
    e.text((86, 115), 'KPSS Tercihi', font=KALIN(32), fill='#ffffff', anchor='lm')
    e.rounded_rectangle((ew - 122, 95, ew - 22, 135), 20, fill=SITE_TURUNCU)
    e.text((ew - 72, 115), 'Katıl', font=YARI(24), fill='#1b1b1b', anchor='mm')
    e.text((26, 180), 'Kamu personel ilanları', font=KALIN(32), fill='#ffffff', anchor='lm')
    # arama kutusu
    odak = tl >= t_ara
    e.rounded_rectangle((24, ARA_Y - 30, ew - 146, ARA_Y + 30), 14, fill='#ffffff', outline=SITE_TURUNCU if odak else '#2b4256',
                        width=5 if odak else 2)
    n = int(max(0.0, tl - t_yaz) / 0.1)
    yazi = 'zabıta'[:n]
    if yazi:
        e.text((44, ARA_Y), yazi, font=YARI(32), fill=YAZI, anchor='lm')
    else:
        e.text((44, ARA_Y), 'Kurum veya ünvan ara', font=NORMAL(26), fill='#8a94a3', anchor='lm')
    if odak and int(tl * 2.4) % 2 == 0:
        cx = 44 + genislik(yazi, YARI(32)) + 4
        e.line((cx, ARA_Y - 17, cx, ARA_Y + 17), fill=YAZI, width=3)
    e.rounded_rectangle((ew - 132, ARA_Y - 30, ew - 24, ARA_Y + 30), 14, fill=SITE_TURUNCU)
    e.text((ew - 78, ARA_Y), 'ARA', font=KALIN(28), fill='#1b1b1b', anchor='mm')
    # sonuçlar
    for i, (kurum, ne, tarih) in enumerate(ZABITA):
        p = tl - t_sonuc - i * 0.18
        if p < 0:
            continue
        q = yumusak(p / 0.3)
        y = 290 + i * 90 + round(26 * (1 - q))
        satir = Image.new('RGBA', (ew - 48, 80), (0, 0, 0, 0))
        s = ImageDraw.Draw(satir)
        s.rounded_rectangle((0, 0, ew - 49, 79), 16, fill=SITE_LACI2)
        s.text((20, 25), kurum, font=KALIN(26), fill='#ffffff', anchor='lm')
        s.text((20, 57), ne, font=YARI(24), fill=SITE_TURUNCU, anchor='lm')
        s.text((ew - 68, 57), tarih, font=NORMAL(21), fill='#9fb0c3', anchor='rm')
        ekran.alpha_composite(opak(satir, q), (24, y))
    maske = Image.new('L', ekran.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, ew - 1, y1 - y0 - 1), 46, fill=255)
    k.paste(ekran, (x0, y0), maske)
    return k


def parmak():
    k = Image.new('RGBA', (120, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.ellipse((10, 10, 110, 110), fill=(255, 255, 255, 120), outline=(255, 255, 255, 230), width=6)
    d.ellipse((40, 40, 80, 80), fill=(255, 255, 255, 230))
    return k


def gonder_dugmesi():
    k, pay = kutu(420, 120, SARI, 60)
    d = ImageDraw.Draw(k)
    d.text((pay + 250, pay + 62), 'GÖNDER', font=KALIN(50), fill=LACI, anchor='mm')
    d.polygon([(pay + 46, pay + 64), (pay + 122, pay + 30), (pay + 104, pay + 96)], fill=LACI)
    d.line((pay + 76, pay + 66, pay + 120, pay + 34), fill=SARI, width=6)
    return k


def ucak(p):
    """GÖNDER'den sağ üste uçan kâğıt uçak."""
    if p < 0 or p > 0.9:
        return None
    q = yumusak(p / 0.9)
    k = Image.new('RGBA', (700, 520), (0, 0, 0, 0))
    x, y = 100 + 540 * q, 420 - 380 * q
    ImageDraw.Draw(k).polygon([(x - 50, y + 20), (x + 50, y - 30), (x + 20, y + 50)], fill=MAVI)
    return k


def son_kart():
    k, pay = kutu(760, 230, LACI, 40)
    k.alpha_composite(logo(130), (pay + 40, pay + 50))
    d = ImageDraw.Draw(k)
    d.text((pay + 200, pay + 86), 'kpsstercihi.com', font=KALIN(64), fill=SARI, anchor='lm')
    d.text((pay + 202, pay + 160), 'Puanına uygun kamu ilanları', font=YARI(36), fill='#ffffff', anchor='lm')
    return k


# ---------------------------------------------------------------- kurgu
class Kurgu:
    def __init__(self, kelimeler, baslar, toplam):
        self.kel, self.baslar, self.toplam = kelimeler, baslar, toplam
        self.ogeler, self.jest, self.kas_anlari, self.bakis = [], [], [], []

    def an(self, bolum, kok, tam=False, sonra=0.0):
        for k in self.kel:
            if k['bolum'] != bolum or k['bas'] < sonra:
                continue
            n = nrm(k['yazi'])
            if (n == nrm(kok)) if tam else n.startswith(nrm(kok)):
                return k['bas']
        raise KeyError(f'{bolum}: {kok}')

    def bitis(self, bolum):
        i = [s['ad'] for s in SEGMENTLER].index(bolum)
        return (self.baslar[i + 1] if i + 1 < len(self.baslar) else self.toplam + 1) - 0.3

    def ekle(self, *a, **k):
        o = Oge(*a, **k)
        self.ogeler.append(o)
        return o

    def kur(self):
        A = self.an
        cx = (BX0 + BX1) / 2
        # 1 kanca — ilk kare kapak: rozet ve kart hazır
        b = self.bitis('kanca')
        self.ekle(puan_rozeti(330), cx, 556, 0, b, giris='yok', ses=None)
        self.ekle(el_karti('atanamazsın'), cx, 870, 0, b, giris='yok', ses=None, aci=-4)
        t = A('kanca', 'yanlış')
        self.ekle(damga('YANLIŞ!', 72), cx + 250, 760, t, b, giris='muhur', ses='muhur', aci=-14)
        self.kas_anlari.append(t)
        self.jest.append((A('kanca', 'atanamazsın') - 0.1, A('kanca', 'söylemiş') + 0.5))
        # 2 moral
        b = self.bitis('moral')
        self.ekle(sonuc_karti(), cx, 520, self.baslar[1], b)
        self.ekle(uzgun_yuz(), 340, 800, A('moral', 'morali'), b)
        self.ekle(hap('İLANLARA BAK', TURUNCU, boy=40), 790, 940, A('moral', 'ilanlara'), b)
        self.ekle(lambda p: cizik(p, 420), 790, 940, A('moral', 'bakmıyor'), b, giris='yok', ses='hus')
        self.bakis.append((self.baslar[1], self.baslar[1] + 1.0))
        # 3 liste
        b = self.bitis('liste')
        self.ekle(liste_basligi(), cx, 410, self.baslar[2], b)
        t = A('liste', 'açık')
        for i, ad in enumerate(LISTE):
            self.ekle(liste_satiri(ad), cx, 518 + i * 104, t + i * 0.2, b, giris='kay', ses='pop' if i % 2 == 0 else None)
        self.buyutec = self.ekle(buyutec(), cx + 250, 520, A('liste', 'tek'), b, giris='pop', ses='hus')
        self.kas_anlari.append(A('liste', 'en', tam=True))
        self.jest.append((t - 0.2, t + 1.6))
        # 4 örnekler
        b = self.bitis('ornek')
        for o, kok in zip(ORNEKLER, ('içişleri', 'eyyübiye', 'bartın')):
            self.ekle(ornek_karti(o), cx, (466, 680, 894)[int(o['no']) - 1], A('ornek', kok), b, giris='kay')
        t = A('ornek', 'şart')
        self.ekle(damga('ŞART: EN AZ 60', 80), cx + 30, 690, t, b, giris='muhur', ses='muhur', aci=-8)
        self.kas_anlari.append(t)
        self.jest.append((A('ornek', 'içişleri') - 0.1, A('ornek', 'içişleri') + 1.4))
        self.jest.append((t - 0.15, t + 1.0))
        # 5 site
        b = self.bitis('site')
        t_dm = A('site', 'dmye')
        t_site = A('site', 'kpsstercihi')
        self.ekle(uzun_kagit, cx - 150, 784, self.baslar[4], t_dm - 0.3, giris='pop')
        self.ekle(damga('sığmıyor!', 64), cx + 200, 640, A('site', 'sığdıramam'), t_dm - 0.3, giris='muhur', ses='muhur', aci=-14)
        t_gerek = A('site', 'gerek')
        self.ekle(lambda p: dm_ikonu(p - (t_gerek - t_dm)), cx, 620, t_dm, t_site - 0.3, giris='pop')
        self.ekle(el_karti('gerek yok', 64, 400, 130), cx, 900, t_gerek, t_site - 0.3, giris='pop', aci=3)
        t_ara, t_yaz, t_uyan = A('site', 'arama') - t_site, A('site', 'yaz', tam=True) - t_site, A('site', 'uyan') - t_site
        self.ekle(lambda p: telefon(p, t_ara, t_yaz, t_uyan), cx, TEL_Y, t_site, b, giris='kay', ses='hus')
        # dokunuş: arama kutusuna, sonra ARA düğmesine
        sol, ust = cx - TEL_W / 2 + 46, TEL_Y - TEL_H / 2 + 46
        self.ekle(lambda p: parmak() if p < 0.5 else None, sol + 220, ust + ARA_Y, t_site + t_ara, b, giris='pop', ses='pop')
        self.ekle(lambda p: parmak() if p < 0.5 else None, sol + 488, ust + ARA_Y, t_site + t_uyan - 0.35, b, giris='pop', ses='pop')
        self.kas_anlari.append(t_gerek)
        self.jest.append((t_site - 0.1, t_site + 1.6))
        # 6 paylaş
        b = self.toplam + 1
        t_g = A('paylas', 'gönder')
        for (metin, renk, y, x), kok in zip((('atanmak isteyen', MAVI, 440, cx - 140), ("KPSS'ye hazırlanan", TURUNCU, 570, cx + 110),
                                             ('bir arkadaşın', KIRMIZI, 700, cx - 90)), ('atanmak', 'kpssye', 'arkadaşına')):
            self.ekle(hap(metin, renk, boy=44), x, y, A('paylas', kok), t_g + 1.5)
        self.ekle(gonder_dugmesi(), cx, 880, t_g - 0.15, t_g + 1.5)
        self.ekle(ucak, cx + 250, 700, t_g + 0.45, t_g + 1.4, giris='yok', ses='hus')
        self.ekle(son_kart(), cx, 680, t_g + 1.7, None, giris='pop')
        self.kas_anlari.append(t_g)
        self.jest.append((t_g - 0.2, t_g + 1.2))
        return self

    def efektler(self):
        return sorted((o.t0, o.ses) for o in self.ogeler if o.ses)


# ---------------------------------------------------------------- altyazı
def altyazi_parcalari(kelimeler):
    parcalar, cur = [], []
    for k in kelimeler:
        yazi = k['yazi'].strip('.,;:!?')
        if cur and (len(cur) >= 3 or sum(len(x['g']) for x in cur) + len(yazi) > 19 or cur[-1]['kes']):
            parcalar.append(cur)
            cur = []
        if cur and (k['bolum'] != cur[-1]['bolum'] or k['bas'] - cur[-1]['son'] > 0.16):
            parcalar.append(cur)
            cur = []
        cur.append(dict(bas=k['bas'], son=k['son'], g=yazi, kes=k['yazi'][-1:] in '.,;:!?', bolum=k['bolum']))
    if cur:
        parcalar.append(cur)
    for i, p in enumerate(parcalar):
        p_bas = 0.0 if i == 0 else p[0]['bas']
        p_son = parcalar[i + 1][0]['bas'] if i + 1 < len(parcalar) else p[-1]['son'] + 1.0
        if p_son - p[-1]['son'] > 0.55:
            p_son = p[-1]['son'] + 0.35
        parcalar[i] = (p_bas, p_son, p)
    return parcalar


def altyazi_ciz(im, parcalar, t):
    for bas, son, p in parcalar:
        if bas <= t < son:
            boy = 78
            while True:
                f = KALIN(boy)
                bosluk = genislik(' ', f)
                ws = [genislik(x['g'], f) for x in p]
                tw = sum(ws) + bosluk * (len(p) - 1)
                if tw <= 980 or boy <= 54:
                    break
                boy -= 4
            q = yumusak((t - bas) / 0.1)
            x = W / 2 - tw / 2
            d = ImageDraw.Draw(im)
            y = ALTYAZI_Y + 10 * (1 - q)
            for x_, w_ in zip(p, ws):
                etkin = x_['bas'] <= t < max(x_['son'], x_['bas'] + 0.15) or (x_ is p[-1] and t >= x_['bas'])
                d.text((x, y), x_['g'], font=f, fill=SARI if etkin else '#ffffff', anchor='lm', stroke_width=8, stroke_fill='#000000')
                x += w_ + bosluk
            return


# ---------------------------------------------------------------- üretim
def kurgu_hazirla(ses_yolu, kelime_yolu):
    ses = wav_oku(ses_yolu)
    kel = kelimeleri_hizala(json.loads(Path(kelime_yolu).read_text(encoding='utf-8')))
    baslar = []
    for sg in SEGMENTLER:
        ilk = next(k for k in kel if k['bolum'] == sg['ad'])
        baslar.append(0.0 if not baslar else max(0.0, ilk['bas'] - 0.12))
    toplam = len(ses) / ORNEK_HIZI + SON_SURE
    return ses, kel, baslar, toplam


def uret(cikti, ses_yolu, kelime_yolu, sunucu_yolu, onizleme=False):
    cikti = Path(cikti)
    gecici = cikti / 'gecici'
    gecici.mkdir(parents=True, exist_ok=True)
    ses, kel, baslar, toplam = kurgu_hazirla(ses_yolu, kelime_yolu)
    kurgu = Kurgu(kel, baslar, toplam).kur()
    parcalar = altyazi_parcalari(kel)
    taban = zemin()
    # defter sayfası ve başlık sunucunun üstüne biner: o bölgeyi ayrı katman olarak tut
    ust = taban.crop((0, 0, W, BY1 + 2)).convert('RGBA')
    maske = Image.new('L', ust.size, 0)
    dm = ImageDraw.Draw(maske)
    dm.rectangle((0, 0, W, SUNUCU_Y), fill=255)
    dm.rounded_rectangle((BX0, BY0, BX1, BY1), 40, fill=255)
    ust.putalpha(maske)
    sunucu = list(sunucu_kareleri(sunucu_yolu, toplam)) if not onizleme else None

    def sunucu_karesi(i):
        if sunucu is not None:
            return sunucu[min(i, len(sunucu) - 1)]
        return next(sunucu_kareleri(sunucu_yolu, 0.1))

    def kare(i, sk=None):
        t = i / FPS
        im = taban.copy()
        im.paste(sk or sunucu_karesi(i), (0, SUNUCU_Y))
        # sunucunun üstüne hafif koyu geçiş: defter sayfasının gölgesi
        im = im.convert('RGBA')
        im.alpha_composite(GECIS, (0, SUNUCU_Y))
        im.alpha_composite(ALT_KARARMA, (0, H - ALT_KARARMA.height))
        im.alpha_composite(ust, (0, 0))
        for o in kurgu.ogeler:
            if o is getattr(kurgu, 'buyutec', None) and t >= o.t0:
                o.cy = 520 + yumusak((t - o.t0) / 1.4) * 420
            o.ciz(im, t)
        rgb = im.convert('RGB')
        altyazi_ciz(rgb, parcalar, t)
        return rgb

    n = int(math.ceil(toplam * FPS))
    ilk = next(sunucu_kareleri(sunucu_yolu, 0.1))
    kare(0, ilk).save(cikti / 'anlatici-kapak.png')
    if onizleme:
        for o in kurgu.ogeler:      # her öğenin girişinden 0,6 sn sonrası
            t = min(o.t0 + 0.6, toplam - 0.05)
            kare(int(t * FPS), ilk).save(cikti / f'oge-{t:05.2f}.png')
        return None

    sessiz = gecici / 'sessiz.mp4'
    p = subprocess.Popen([ffmpeg_yolu(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', str(sessiz)],
                         stdin=subprocess.PIPE)
    try:
        for i in range(n):
            p.stdin.write(kare(i).tobytes())
    finally:
        p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError('ffmpeg video yazamadı')
    karisim = karistir(ses, kurgu.efektler(), toplam)
    wav = gecici / 'ses.wav'
    wav_yaz(karisim, wav)
    son = cikti / 'anlatici-60-puan.mp4'
    subprocess.run([ffmpeg_yolu(), '-y', '-loglevel', 'error', '-i', str(sessiz), '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{toplam:.2f}', '-movflags', '+faststart', str(son)], check=True)
    print(f'{son}: {toplam:.1f} sn, {n} kare')
    return son


def _gecisler():
    g = Image.new('RGBA', (W, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for y in range(70):
        d.line((0, y, W, y), fill=(11, 21, 41, int(200 * (1 - y / 70) ** 1.6)))
    a = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(a)
    for y in range(420):
        d.line((0, y, W, y), fill=(0, 0, 0, int(150 * (y / 420) ** 1.8)))
    return g, a


GECIS, ALT_KARARMA = _gecisler()


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--ses', required=True, help='seslendirme (wav)')
    a.add_argument('--kelimeler', required=True, help='faster-whisper kelime zamanları (json)')
    a.add_argument('--sunucu', required=True, help='dudak senkronlu sunucu videosu (mp4)')
    a.add_argument('--cikti', default='reels-cikti')
    a.add_argument('--onizleme', action='store_true', help='yalnız denetim kareleri')
    s = a.parse_args()
    uret(s.cikti, s.ses, s.kelimeler, s.sunucu, s.onizleme)


if __name__ == '__main__':
    main()
