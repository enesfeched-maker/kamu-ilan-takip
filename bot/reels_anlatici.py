"""Anlatıcı biçimi (24 Kasım 2026): çizgi kadın sunucu + üstte defter sayfasında hareketli grafikler + kelime kelime altyazı.

Rakip kalıbı: "60 aldın, atanamazsın diyenler yalan söyledi; liste yaz, DM'den göndereyim". Bizde DM yok: izleyici
kpsstercihi.com'a yönlendirilir. Ses edge-tts tr-TR-EmelNeural (ücretsiz); kelime zamanları hem altyazıyı hem grafiklerin
giriş anını belirler, ağız açıklığı ses zarfından okunur. İlk kare kapaktır (60 rozeti + "atanamazsın" kartı hazır durur).
Örnek ilanların her bilgisi sitedeki ilan kaydının şart metninden elle alınmıştır (24 Kasım 2026'da açık ilanlar).

Kullanım: python bot/reels_anlatici.py [--cikti klasör]"""
import argparse
import asyncio
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SES = 'tr-TR-EmelNeural'
HIZ = '+14%'
ORNEK_HIZI = 48000

# Renkler (elwyn.co "Midnight + Marigold" ailesi: lacivert zemin, krem kâğıt, turuncu/sarı vurgu; yeşil yok)
LACI, LACI2, GECE = '#13233f', '#1d3157', '#0b1529'
KREM, KAGIT_CIZGI, KENAR = '#fdf6e7', '#d9e3f2', '#e8b4a8'
TURUNCU, SARI, KIRMIZI, MAVI = '#f7931e', '#ffd23f', '#e63946', '#2f6fdd'
YAZI, SOLUK = '#1b2236', '#6b7280'
TEN, TEN2, SAC, KAZAK = '#f6c9a4', '#e9b089', '#3b2219', '#e85d4a'
SITE_LACI, SITE_LACI2, SITE_TURUNCU, SITE_K = '#0c1d2a', '#132b3d', '#f89c1c', '#c6f432'

BX0, BY0, BX1, BY1 = 44, 318, 1036, 1040        # defter sayfası
KX, KY = 160, 1078                              # sunucu tuvalinin sol üstü (760x700)
MASA_Y = 1772


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
# soz: seslendirilen metin. goster: altyazıda birleştirilecek söz grupları (seste yazıyla okunan sayı/adres).
SEGMENTLER = [
    dict(ad='kanca', soz="KPSS'den 60 aldın diye, atanamazsın diyenler sana yanlış söylemiş."),
    dict(ad='moral', soz='Çoğu kişi puanını görünce morali bozuluyor, ilanlara bakmıyor bile.'),
    dict(ad='liste', soz='Oysa şu an en az 60 isteyen açık ilanlar var. Biz her gün hepsini tek tek okuyoruz.'),
    dict(ad='ornek', soz='Mesela İçişleri Bakanlığı bin yüz yetmiş sözleşmeli personel alıyor; lise, önlisans, lisans. '
                         'Eyyübiye Belediyesi dokuz zabıta memuru alıyor. Bartın Üniversitesi önlisans mezunu büro personeli arıyor. '
                         'Üçünde de şart: en az 60.'),
    dict(ad='site', soz="Hepsini videoya sığdıramam. DM'ye yazmana da gerek yok. KPSS Tercihi nokta com'a gir, arama kutusuna "
                        'kadronu ya da bölümünü yaz. Sana uyan ilanlar karşına çıksın.'),
    dict(ad='paylas', soz="Atanmak isteyen, KPSS'ye hazırlanan bir arkadaşına bu videoyu gönder. O da bilsin."),
]
GOSTER = [('bin yüz yetmiş', '1.170'), ('dokuz', '9'), ("KPSS Tercihi nokta com'a", "kpsstercihi.com'a")]
ARA_SURE, SON_SURE = 0.25, 2.2

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


# ---------------------------------------------------------------- ses
async def _seslendir(metin, yol):
    import edge_tts
    c = edge_tts.Communicate(metin, SES, rate=HIZ, boundary='WordBoundary')
    kelimeler = []
    with open(yol, 'wb') as f:
        async for p in c.stream():
            if p['type'] == 'audio':
                f.write(p['data'])
            elif p['type'] == 'WordBoundary':
                kelimeler.append([p['offset'] / 1e7, (p['offset'] + p['duration']) / 1e7, p['text']])
    return kelimeler


def ffmpeg_yolu():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def wav_oku(yol, ss=0.0, sure=None):
    """Herhangi bir ses dosyasını 48 kHz mono float diziye çevirir (-ss girişten SONRA: bu makinedeki ffmpeg 7.1 notu)."""
    ek = ['-ss', f'{ss:.2f}'] if ss else []
    ek += ['-t', f'{sure:.2f}'] if sure else []
    p = subprocess.run([ffmpeg_yolu(), '-loglevel', 'error', '-i', str(yol), *ek, '-f', 's16le', '-ac', '1', '-ar', str(ORNEK_HIZI), '-'],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768


def birlestir_kelimeler(kel):
    """GOSTER gruplarını tek altyazı sözcüğüne indirir."""
    kel = [list(k) for k in kel]
    for soz, goster in GOSTER:
        parca = [nrm(x) for x in soz.split()]
        i = 0
        while i <= len(kel) - len(parca):
            if [nrm(k[2]) for k in kel[i:i + len(parca)]] == parca:
                kel[i:i + len(parca)] = [[kel[i][0], kel[i + len(parca) - 1][1], goster]]
            i += 1
    return kel


def ses_hazirla(klasor):
    """Her bölümü ayrı seslendirir; bölümleri ardışık yerleştirir. Dönüş: (ses dizisi, kelimeler, bölüm başlangıçları, toplam)."""
    klasor.mkdir(parents=True, exist_ok=True)
    parcalar, kelimeler, baslar, an = [], [], [], 0.0
    for sg in SEGMENTLER:
        mp3 = klasor / f"ses-{sg['ad']}.mp3"
        kel = asyncio.run(_seslendir(sg['soz'], mp3))
        dizi = wav_oku(mp3)
        # sondaki sessizliği kırp (kelime bitişinden 0,15 sn sonra)
        son = min(len(dizi), int((kel[-1][1] + 0.15) * ORNEK_HIZI))
        dizi = dizi[:son]
        baslar.append(an)
        for b, e, x in birlestir_kelimeler(kel):
            kelimeler.append(dict(bas=an + b, son=an + e, yazi=x, bolum=sg['ad']))
        parcalar.append(dizi)
        an += len(dizi) / ORNEK_HIZI + ARA_SURE
        parcalar.append(np.zeros(int(ARA_SURE * ORNEK_HIZI), dtype=np.float32))
    toplam = an - ARA_SURE + SON_SURE
    ses = np.concatenate(parcalar)
    ses = np.pad(ses, (0, max(0, int(toplam * ORNEK_HIZI) - len(ses))))
    return ses, kelimeler, baslar, toplam


def zarf(ses, toplam):
    """Kare başına 0–1 konuşma şiddeti (ağız için)."""
    n = int(math.ceil(toplam * FPS))
    adim = ORNEK_HIZI // FPS
    z = np.array([np.sqrt(np.mean(ses[i * adim:(i + 1) * adim] ** 2)) if i * adim < len(ses) else 0.0 for i in range(n)])
    ust = np.percentile(z[z > 0.005], 92) if np.any(z > 0.005) else 1.0
    z = np.clip((z / ust - 0.12) / 0.88, 0, 1)
    out, v = np.zeros_like(z), 0.0
    for i, x in enumerate(z):
        v = v + (x - v) * (0.75 if x > v else 0.45)
        out[i] = v
    return out


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


def karistir(ses, efektler, toplam, muzik):
    n = int(toplam * ORNEK_HIZI)
    ses = ses[:n] if len(ses) >= n else np.pad(ses, (0, n - len(ses)))
    rms = np.sqrt(np.mean(ses[np.abs(ses) > 0.01] ** 2))
    karisim = ses * (0.16 / max(rms, 1e-4))
    for an, tur in efektler:
        e = efekt(tur) * 0.5
        i = int(an * ORNEK_HIZI)
        if i < n:
            karisim[i:i + len(e)] += e[:n - i]
    if muzik is not None:
        yol, bas = muzik
        m = wav_oku(yol, ss=bas, sure=toplam + 0.5)[:n]
        m = np.pad(m, (0, n - len(m)))
        mr = np.sqrt(np.mean(m ** 2)) or 1
        m = m * (0.028 / mr)
        m[:int(0.3 * ORNEK_HIZI)] *= np.linspace(0, 1, int(0.3 * ORNEK_HIZI))
        m[-ORNEK_HIZI:] *= np.linspace(1, 0, ORNEK_HIZI)
        karisim += m
    return np.tanh(karisim * 1.6) / np.tanh(1.6) * 0.92


def wav_yaz(dizi, yol):
    with wave.open(str(yol), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ORNEK_HIZI)
        w.writeframes((np.clip(dizi, -1, 1) * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- sabit zemin
def zemin():
    im = Image.new('RGB', (W, H), GECE)
    d = ImageDraw.Draw(im)
    # oda: yukarıdan aşağı koyulaşan lacivert
    ust, alt = np.array((31, 50, 88)), np.array((12, 22, 42))
    for y in range(H):
        p = y / H
        d.line((0, y, W, y), fill=tuple(int(v) for v in ust * (1 - p) + alt * p))
    # ahşap çıta duvar
    for x in range(0, W, 40):
        d.rectangle((x, 1150, x + 30, MASA_Y), fill=(36, 54, 92))
        d.rectangle((x + 30, 1150, x + 39, MASA_Y), fill=(24, 38, 68))
    # sıcak led ışığı
    isik = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
    di = ImageDraw.Draw(isik)
    for i in range(260):
        di.line((0, i, W, i), fill=(247, 147, 30, int(110 * (1 - i / 260) ** 2.2)))
    im.paste(isik, (0, 1150), isik)
    d.rectangle((0, 1144, W, 1152), fill=(255, 190, 110))
    # sağ raf: kitaplar ve saksı (kil)
    d.rectangle((838, 1478, 1080, 1494), fill=(120, 78, 48))
    x = 850
    for w_, h_, c in ((26, 120, '#f2e3c6'), (34, 140, '#e63946'), (22, 104, '#ffd23f'), (30, 132, '#2f6fdd'), (28, 112, '#f7931e')):
        d.rounded_rectangle((x, 1478 - h_, x + w_, 1478), 4, fill=c)
        x += w_ + 6
    d.polygon([(1012, 1478), (1050, 1478), (1044, 1420), (1018, 1420)], fill='#c8643c')
    # sol raf: kupa ve kitaplar
    d.rectangle((0, 1398, 220, 1414), fill=(120, 78, 48))
    for i, (h_, c) in enumerate(((96, '#f2e3c6'), (116, '#2f6fdd'), (88, '#f7931e'))):
        d.rounded_rectangle((24 + i * 34, 1398 - h_, 52 + i * 34, 1398), 4, fill=c)
    d.rounded_rectangle((150, 1340, 196, 1398), 8, fill='#fdf6e7')
    d.arc((184, 1352, 214, 1384), -90, 90, fill='#fdf6e7', width=8)
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


def masa():
    k = Image.new('RGBA', (W, H - MASA_Y + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    d.rectangle((0, 10, W, H), fill='#a86b3c')
    d.rectangle((0, 10, W, 34), fill='#c4844d')
    for y in range(60, H - MASA_Y, 34):
        d.line((0, y, W, y + 6), fill='#9a6035', width=3)
    # isim levhası
    d.polygon([(640, 120), (1000, 120), (980, 44), (660, 44)], fill=SITE_LACI)
    d.rounded_rectangle((676, 58, 716, 98), 9, fill='#000000')
    d.text((696, 78), 'K', font=KALIN(30), fill=SITE_K, anchor='mm')
    d.text((732, 79), 'kpsstercihi.com', font=YARI(32), fill=SITE_TURUNCU, anchor='lm')
    return k


# ---------------------------------------------------------------- sunucu (çizgi kadın)
S = 2   # çizim ölçeği (kenar yumuşatma için)


def _P(*xy):
    return [v * S for v in xy]


def sunucu(t, a, kas, goz_kirp, bakis, kol):
    """t: sn, a: konuşma şiddeti 0–1, kas: kaş kalkışı 0–1, goz_kirp: 0–1, bakis: göz bebeği dikey kayma, kol: 0–1 işaret eli."""
    cw, ch = 760, 700
    aci = 2.2 * math.sin(2 * math.pi * t / 3.9) + 1.6 * a * math.sin(2 * math.pi * t * 1.4)
    dy = 3.5 * math.sin(2 * math.pi * t / 2.7) - 2.5 * a
    nefes = 2.5 * math.sin(2 * math.pi * t / 3.3)
    pivot = (380 * S, 420 * S)

    # arka saç (başla döner)
    sac = Image.new('RGBA', (cw * S, ch * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(sac)
    d.rounded_rectangle(_P(262, 170, 498, 560), 110 * S, fill=SAC)
    d.ellipse(_P(250, 120, 510, 380), fill=SAC)
    sac = sac.rotate(aci, resample=Image.Resampling.BICUBIC, center=pivot, translate=(0, dy * S))

    gov = Image.new('RGBA', (cw * S, ch * S), (0, 0, 0, 0))
    gov.alpha_composite(sac)
    d = ImageDraw.Draw(gov)
    # boyun + gövde
    d.rounded_rectangle(_P(346, 380, 414, 500), 24 * S, fill=TEN2)
    d.rounded_rectangle(_P(150, 468 + nefes, 610, 900), 150 * S, fill=KAZAK)
    d.polygon(_P(318, 468 + nefes, 442, 468 + nefes, 380, 548 + nefes), fill=TEN2)
    d.polygon(_P(300, 468 + nefes, 330, 468 + nefes, 380, 560 + nefes, 380, 590 + nefes), fill='#ffffff')
    d.polygon(_P(460, 468 + nefes, 430, 468 + nefes, 380, 560 + nefes, 380, 590 + nefes), fill='#ffffff')
    d.ellipse(_P(372, 600 + nefes, 388, 616 + nefes), fill='#ffd23f')
    # dinlenen kol (sol): omuzdan masaya
    d.line(_P(214, 540 + nefes, 196, 676, 318, 708), fill='#d24e3d', width=74 * S, joint='curve')
    d.ellipse(_P(300, 678, 366, 728), fill=TEN)
    # sağ kol: dinlenirken masada, konuşurken işaret eder
    omuz = (548, 540 + nefes)
    dirsek = (566 + 10 * kol, 676 - 40 * kol)
    q = yumusak(kol)
    el = (444 * (1 - q) + 640 * q, 708 * (1 - q) + 420 * q)
    d.line(_P(*omuz, *dirsek, *el), fill='#d24e3d', width=74 * S, joint='curve')
    if kol > 0.35:
        d.rounded_rectangle(_P(el[0] - 12, el[1] - 92, el[0] + 8, el[1] - 20), 10 * S, fill=TEN)   # işaret parmağı
        d.ellipse(_P(el[0] - 34, el[1] - 40, el[0] + 30, el[1] + 26), fill=TEN)
    else:
        d.ellipse(_P(el[0] - 32, el[1] - 28, el[0] + 34, el[1] + 22), fill=TEN)

    # baş katmanı
    bas = Image.new('RGBA', (cw * S, ch * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(bas)
    d.ellipse(_P(266, 268, 298, 328), fill=TEN2)                        # kulaklar
    d.ellipse(_P(462, 268, 494, 328), fill=TEN2)
    d.ellipse(_P(274, 326, 290, 342), fill='#ffd23f')                    # küpeler
    d.ellipse(_P(470, 326, 486, 342), fill='#ffd23f')
    d.ellipse(_P(282, 168, 478, 410), fill=TEN)                          # yüz
    # ön saç: kafa üstü (alnı kavisli açık bırakır) + ortadan ayrılmış perde perçem
    maske = Image.new('L', bas.size, 0)
    m = ImageDraw.Draw(maske)
    m.ellipse(_P(264, 124, 496, 344), fill=255)
    m.ellipse(_P(300, 204, 460, 440), fill=0)
    m.polygon(_P(380, 176, 344, 186, 314, 214, 298, 256, 294, 318, 306, 262, 326, 226, 356, 204, 380, 196), fill=255)
    m.polygon(_P(380, 176, 416, 186, 446, 214, 462, 256, 466, 318, 454, 262, 434, 226, 404, 204, 380, 196), fill=255)
    bas.paste(Image.new('RGBA', bas.size, SAC), (0, 0), maske)
    d = ImageDraw.Draw(bas)
    # kaşlar
    k = 7 * kas
    d.line(_P(316, 262 - k, 334, 252 - k, 354, 256 - k), fill='#4a2a1e', width=6 * S, joint='curve')
    d.line(_P(406, 256 - k, 426, 252 - k, 444, 262 - k), fill='#4a2a1e', width=6 * S, joint='curve')
    # gözler
    for gx in (336, 424):
        yuk = 17 * (1 - goz_kirp)
        dis = 1 if gx > 380 else -1
        if yuk > 4:
            d.ellipse(_P(gx - 17, 298 - yuk, gx + 17, 298 + yuk), fill='#ffffff')
            ib = min(yuk, 13)
            d.ellipse(_P(gx - 12, 298 - ib + bakis, gx + 12, 298 + ib + bakis), fill='#3a2318')
            d.ellipse(_P(gx - 6, 298 - min(ib, 7) + bakis, gx + 6, 298 + min(ib, 7) + bakis), fill='#140a06')
            d.ellipse(_P(gx - 1, 290 + bakis, gx + 6, 297 + bakis), fill='#ffffff')
            d.arc(_P(gx - 18, 298 - yuk, gx + 18, 298 + yuk), 195, 345, fill='#2a1a14', width=3 * S)
            d.line(_P(gx + dis * 15, 298 - yuk * 0.7, gx + dis * 23, 298 - yuk * 0.7 - 7), fill='#2a1a14', width=3 * S)
        else:
            d.arc(_P(gx - 17, 286, gx + 17, 304), 20, 160, fill='#2a1a14', width=3 * S)
    # yanak (ayrı katmanda yarı saydam), burun
    yanak = Image.new('RGBA', bas.size, (0, 0, 0, 0))
    dy_ = ImageDraw.Draw(yanak)
    for bx in (316, 444):
        dy_.ellipse(_P(bx - 20, 336, bx + 20, 354), fill=(240, 120, 120, 70))
    bas.alpha_composite(yanak)
    d = ImageDraw.Draw(bas)
    d.line(_P(380, 318, 374, 340, 386, 344), fill=TEN2, width=5 * S, joint='curve')
    # ağız
    if a < 0.07:
        d.arc(_P(352, 350, 408, 384), 20, 160, fill='#b5374a', width=6 * S)
    else:
        aw = 22 + 6 * math.sin(t * 19) * a + 4 * a
        ah = 4 + 20 * a
        d.ellipse(_P(380 - aw, 372 - ah * 0.45, 380 + aw, 372 + ah), fill='#7a2630')
        d.rectangle(_P(380 - aw * 0.7, 372 - ah * 0.45, 380 + aw * 0.7, 372 - ah * 0.45 + max(3, ah * 0.25)), fill='#ffffff')
        if ah > 10:
            d.ellipse(_P(380 - aw * 0.55, 372 + ah * 0.35, 380 + aw * 0.55, 372 + ah * 0.95), fill='#e86a7a')
    bas = bas.rotate(aci, resample=Image.Resampling.BICUBIC, center=pivot, translate=(0, dy * S))
    gov.alpha_composite(bas)
    return gov.resize((cw, ch), Image.Resampling.LANCZOS)


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
            y = 1112 + 10 * (1 - q)
            for x_, w_ in zip(p, ws):
                etkin = x_['bas'] <= t < max(x_['son'], x_['bas'] + 0.15) or (x_ is p[-1] and t >= x_['bas'])
                d.text((x, y), x_['g'], font=f, fill=SARI if etkin else '#ffffff', anchor='lm', stroke_width=8, stroke_fill='#000000')
                x += w_ + bosluk
            return


# ---------------------------------------------------------------- üretim
def uret(cikti, muzikli=True, onizleme=False):
    cikti = Path(cikti)
    gecici = cikti / 'gecici'
    ses, kel, baslar, toplam = ses_hazirla(gecici)
    kurgu = Kurgu(kel, baslar, toplam).kur()
    z = zarf(ses, toplam)
    parcalar = altyazi_parcalari(kel)
    taban, masa_kat = zemin(), masa()

    rng = np.random.default_rng(11)
    kirpma, t_ = [], 1.4
    while t_ < toplam:
        kirpma.append(t_)
        t_ += 2.6 + rng.random() * 2.2

    def jest_degeri(t):
        v = 0.0
        for a, b in kurgu.jest:
            v = max(v, yumusak((t - a) / 0.25) * (1 - yumusak((t - b) / 0.3)))
        return v

    def kare(i):
        t = i / FPS
        im = taban.copy().convert('RGBA')
        for o in kurgu.ogeler:
            if o is getattr(kurgu, 'buyutec', None):
                if t >= o.t0:
                    p = yumusak((t - o.t0) / 1.4)
                    o.cy = 520 + p * 420
            o.ciz(im, t)
        a = float(z[min(i, len(z) - 1)])
        kas = max([1 - yumusak(abs(t - k - 0.25) / 0.5) for k in kurgu.kas_anlari] + [0])
        gk = max([1 - abs(t - k) / 0.07 for k in kirpma] + [0])
        bakis = -4 if any(a_ <= t < b_ for a_, b_ in kurgu.bakis) else 1.5 * math.sin(t * 0.7)
        kisi = sunucu(t, a, kas, kis(gk), bakis, jest_degeri(t))
        im.alpha_composite(kisi, (KX, KY))
        im.alpha_composite(masa_kat, (0, MASA_Y - 10))
        rgb = im.convert('RGB')
        altyazi_ciz(rgb, parcalar, t)
        return rgb

    n = int(math.ceil(toplam * FPS))
    kare(0).save(cikti / 'anlatici-kapak.png')
    for t in (2.6, 6.0, 10.5, 17.0, 24.0, 29.5, 33.0, toplam - 0.3):
        if t < toplam:
            kare(int(t * FPS)).save(cikti / f'anlatici-{t:04.1f}.png')
    if onizleme:
        for o in kurgu.ogeler:      # her öğenin girişinden 0,6 sn sonrası
            t = min(o.t0 + 0.6, toplam - 0.05)
            kare(int(t * FPS)).save(cikti / f'oge-{t:05.2f}.png')
        return None

    sessiz = gecici / 'sessiz.mp4'
    p = subprocess.Popen([ffmpeg_yolu(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', str(sessiz)],
                         stdin=subprocess.PIPE)
    try:
        for i in range(n):
            p.stdin.write(kare(i).tobytes())
    finally:
        p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError('ffmpeg video yazamadı')

    muzik = None
    if muzikli:
        import reels
        yol, bas = reels.muzik_yolu('ilan')
        muzik = (yol, bas) if yol else None
    karisim = karistir(ses, kurgu.efektler(), toplam, muzik)
    wav = gecici / 'ses.wav'
    wav_yaz(karisim, wav)
    son = cikti / 'anlatici-60-puan.mp4'
    subprocess.run([ffmpeg_yolu(), '-y', '-loglevel', 'error', '-i', str(sessiz), '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-t', f'{toplam:.2f}', '-movflags', '+faststart', str(son)], check=True)
    print(f'{son}: {toplam:.1f} sn, {n} kare')
    return son


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--cikti', default='reels-cikti')
    a.add_argument('--muziksiz', action='store_true')
    a.add_argument('--onizleme', action='store_true', help='yalnız denetim kareleri')
    s = a.parse_args()
    uret(s.cikti, not s.muziksiz, s.onizleme)


if __name__ == '__main__':
    main()
