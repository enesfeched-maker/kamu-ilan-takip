"""Hareketli dikey video (1080x1920) şablonları: sabah son gün, tek ilan, akşam özeti.

Üç biçim de aynı sahne motorunu kullanır; bot her gün aynı düzeni üretir, yalnız veri değişir:
  sabah  -> son_gun_videosu : son başvurusu 0–3 gün içinde biten ilanlar, en yakın tarih önce
  ilan   -> ilan_videosu    : tek ilan (kurum, kaç kişi, kadrolar, kimler başvurabilir, son başvuru)
  aksam  -> ozet_videosu    : bugün eklenen ilanların özeti

Her sahne öğeleri sırayla girer (kayarak / büyüyerek), sahne sonunda birlikte çıkar. Üstte hikâye çubuğu sahne
ilerleyişini gösterir. Renkler ilan kartlarıyla aynıdır (petrol + lime). Metin yalnız ilan verisinden gelir; tahmin yok.

23 Kasım 2026'dan itibaren yayında üç yeni biçim (palet ve müzik başına ayrı) eskilerin yerine geçer:
  ilan  -> kimler_videosu : "Kurum N kişi alıyor — kimler başvurabilir?" (sarı)
  aksam -> meslek_videosu : aynı mesleğin açık ilanları, en çok kadro çıkaran meslek (indigo)
  sabah -> duzey_videosu  : lise / önlisans / lisans mezunlarının başvurabileceği ilanlar, geri sayım (karmin)
Uygun içerik yoksa eski biçimlere düşülür.

Kullanım: python bot/reels.py sabah|aksam|ilan|kimler|meslek|duzey [--id İLAN_KİMLİĞİ] [--cikti klasör] [--muzik dosya]"""
import argparse
import io
import json
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

import kart_tasarimlari as k
from kart_tasarimlari import F, AYLAR

VW, VH, FPS = 1080, 1920, 30
SOL, SAG = 72, 1008                 # yatay güvenli alan
UST, ALT = 300, 1540                # Reels/TikTok arayüzünün örtmediği dikey alan
GEN = SAG - SOL
ROOT = Path(__file__).resolve().parents[1]
# Renk paletleri. Varsayılan PALET; yeni palet eklemek için buraya bir satır yeterli.
#   zemin: üstten alta geçiş · yazi/soluk: ana ve ikincil metin · vurgu: iri sayı, başlık, dolu rozet · vurgu_ustu: vurgu
#   üstündeki yazı · panel: kutu dolgusu · panel_cizgi: açık zeminde kutu kenarı · acil/yakin: kalan gün rozetleri
PALETLER = {
    'kagit': dict(zemin_ust=(247, 242, 232), zemin_alt=(238, 230, 214), yazi='#16130f', soluk='#6f675c', vurgu='#2337e6', vurgu_ustu='#ffffff',
                  panel='#ffffff', panel_cizgi='#e0d6c2', cizgi=(214, 204, 186), cizgi2=(226, 217, 198), acil='#e03131', acil_ustu='#ffffff',
                  yakin='#f08c00', yakin_ustu='#16130f'),
    'gece': dict(zemin_ust=(34, 20, 58), zemin_alt=(17, 9, 32), yazi='#ffffff', soluk='#cbbfe0', vurgu='#ffb45c', vurgu_ustu='#21143a',
                 panel='#36225a', panel_cizgi=None, cizgi=(78, 56, 116), cizgi2=(60, 41, 94), acil='#ff5d5d', acil_ustu='#ffffff',
                 yakin='#ffe066', yakin_ustu='#21143a'),
    'bordo': dict(zemin_ust=(236, 224, 202), zemin_alt=(224, 209, 182), yazi='#1b1410', soluk='#6d6052', vurgu='#8a1c2b', vurgu_ustu='#fff7ea',
                  panel='#fbf5e9', panel_cizgi='#d6c6aa', cizgi=(201, 186, 160), cizgi2=(214, 200, 176), acil='#1b1410', acil_ustu='#fff7ea',
                  yakin='#d9822b', yakin_ustu='#1b1410'),
    'petrol': dict(zemin_ust=(16, 46, 53), zemin_alt=(9, 28, 33), yazi='#ffffff', soluk='#b6cbcc', vurgu='#c9f395', vurgu_ustu='#102e35',
                   panel='#174c46', panel_cizgi=None, cizgi=(52, 92, 90), cizgi2=(31, 74, 70), acil='#d64545', acil_ustu='#ffffff',
                   yakin='#e0a100', yakin_ustu='#102e35'),
    # Yeni biçimlerin paletleri (rakip kalıbı: yüksek zıtlık). Sıraya girmez; BICIM_PALETI ile vakte bağlanır.
    'sari': dict(zemin_ust=(255, 242, 0), zemin_alt=(250, 232, 0), yazi='#1c4286', soluk='#1c4286', vurgu='#1c4286', vurgu_ustu='#fff200',
                 panel='#ffffff', panel_cizgi='#1c4286', cizgi=(214, 200, 0), cizgi2=(240, 226, 0), acil='#1c4286', acil_ustu='#fff200',
                 yakin='#1c4286', yakin_ustu='#fff200'),
    'indigo': dict(zemin_ust=(9, 26, 66), zemin_alt=(5, 18, 48), yazi='#ffffff', soluk='#c7cde0', vurgu='#f48067', vurgu_ustu='#051230',
                   panel='#132a5e', panel_cizgi=None, cizgi=(44, 62, 108), cizgi2=(22, 40, 82), acil='#f48067', acil_ustu='#051230',
                   yakin='#f48067', yakin_ustu='#051230'),
    'karmin': dict(zemin_ust=(214, 22, 60), zemin_alt=(190, 14, 50), yazi='#ffffff', soluk='#ffd3db', vurgu='#111314', vurgu_ustu='#ffffff',
                   panel='#111314', panel_cizgi=None, cizgi=(236, 110, 136), cizgi2=(200, 16, 52), acil='#111314', acil_ustu='#ffffff',
                   yakin='#111314', yakin_ustu='#ffffff'),
}
PALET = 'kagit'
PALET_SIRASI = ('kagit', 'bordo')   # yayında sırayla kullanılır: videolar hep aynı renkte çıkmasın (kullanıcı, 11 Kasım 2026)
YENI_BICIM_TARIHI = date(2026, 11, 23)   # bu günden itibaren vakit başına yeni biçim ve kendi paleti
BICIM_PALETI = {'ilan': 'sari', 'aksam': 'indigo', 'sabah': 'karmin'}


def bicim_paleti(vakit, simdi):
    """Yeni biçimin paleti; tarih gelmediyse ya da vaktin yeni biçimi yoksa None (eski biçim, sıralı palet)."""
    return BICIM_PALETI.get(vakit) if simdi.date() >= YENI_BICIM_TARIHI else None


class _Renkler:
    def sec(self, ad):
        self.__dict__.update(PALETLER[ad], ad=ad)


R = _Renkler()
R.sec(PALET)


def siradaki_palet(gecmis=()):
    """Son şablon videosunda kullanılanın sıradaki paleti; geçmişte palet kaydı yoksa ilki."""
    son = next((g.get('palet') for g in reversed(list(gecmis)) if g.get('palet') in PALET_SIRASI), None)
    return PALET_SIRASI[(PALET_SIRASI.index(son) + 1) % len(PALET_SIRASI)] if son else PALET_SIRASI[0]


def palet_sec(ad):
    """Sonraki videolar bu paletle çizilir (önizleme ve --palet için)."""
    R.sec(ad)


GUNLER = ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')
GIRIS, CIKIS = 0.38, 0.22           # öğe giriş ve sahne çıkış süresi (sn)
SON_GUN_EN_COK, OZET_SATIR, OZET_SAHNE = 6, 3, 3
SON_GUN_UFUK = 3                    # sabah videosuna giren en uzak son başvuru (gün)
AD_DEGIL = {'alacak', 'alinacak', 'alim', 'alimi', 'personel alimi'}   # başlıktan kadro adı diye kalan fiiller
_OLC = ImageDraw.Draw(Image.new('RGB', (8, 8)))


# ---------------------------------------------------------------- hareket
def _sinirla(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def yumusak(p):
    """Hızlı başlayıp yavaşlayan geçiş (0..1)."""
    return 1 - (1 - _sinirla(p)) ** 3


def esnek(p):
    """Hafif taşarak oturan geçiş (rozet ve logo için)."""
    p = _sinirla(p)
    return 1 + 2.2 * (p - 1) ** 3 + 1.2 * (p - 1) ** 2


class Oge:
    """Sahnedeki tek katman. tur: 'yukari' (alttan kayar), 'sol' (soldan kayar), 'buyu' (büyüyerek oturur), 'sabit'."""

    def __init__(self, katman, x, y, bas=0.0, tur='yukari'):
        self.katman, self.x, self.y, self.bas, self.tur = katman, round(x), round(y), bas, tur

    def ciz(self, im, t, cikis):
        if t < self.bas:
            return
        p = (t - self.bas) / GIRIS
        saydam = yumusak(p) * (1 - cikis)
        if saydam <= 0.01:
            return
        kat, x, y = self.katman, self.x, self.y - round(36 * cikis)
        if self.tur == 'yukari':
            y += round(48 * (1 - yumusak(p)))
        elif self.tur == 'sol':
            x -= round(70 * (1 - yumusak(p)))
        elif self.tur == 'buyu' and p < 1:
            o = 0.55 + 0.45 * esnek(p)
            w, h = max(1, round(kat.width * o)), max(1, round(kat.height * o))
            x, y = x + (kat.width - w) // 2, y + (kat.height - h) // 2
            kat = kat.resize((w, h), Image.Resampling.BILINEAR)
        if saydam >= 0.995:
            im.paste(kat, (x, y), kat)
        else:
            im.paste(kat, (x, y), kat.getchannel('A').point(lambda a: int(a * saydam)))


class Sayac:
    """0'dan hedefe sayan iri sayı; her karede yeniden yazılır."""

    def __init__(self, hedef, x, y, boy, renk=None, bas=0.1, sure=0.9, hiza='lt'):
        renk = renk or R.vurgu
        self.hedef, self.x, self.y, self.boy, self.renk, self.bas, self.sure, self.hiza = hedef, x, y, boy, renk, bas, sure, hiza

    def ciz(self, im, t, cikis):
        if t < self.bas or cikis >= 0.99:
            return
        deger = round(self.hedef * yumusak((t - self.bas) / self.sure))
        kat = yazi(binlik(deger), self.boy, self.renk)
        x = self.x - (kat.width if self.hiza == 'rt' else kat.width // 2 if self.hiza == 'mt' else 0)
        Oge(kat, x, self.y, self.bas, 'yukari').ciz(im, t, cikis)


class Sahne:
    def __init__(self, sure, ogeler, son=False):
        self.sure, self.ogeler, self.son = sure, ogeler, son

    def ciz(self, im, t, oturmus=False):
        """oturmus: öğeler giriş hareketi olmadan, yerine oturmuş çizilir (çıkış hareketi yine oynar)."""
        cikis = 0.0 if self.son else yumusak((t - (self.sure - CIKIS)) / CIKIS)
        for o in self.ogeler:
            o.ciz(im, t + OTURMUS_KAYDIRMA if oturmus else t, cikis)


# ---------------------------------------------------------------- katman üreticileri
def binlik(n):
    return f'{int(n):,}'.replace(',', '.')


def yazi(metin, boy, renk=None, kalin=True, genislik=None, satir=1, aralik=1.14, hiza='l'):
    """Metin katmanı; genislik verilirse en çok `satir` satıra kaydırılır (sığmayan … ile kesilir)."""
    renk = renk or R.yazi
    yz = F(boy, kalin)
    satirlar = k.lines(_OLC, str(metin), yz, genislik, satir) if genislik else [str(metin)]
    w = max(1, max(round(_OLC.textlength(s, font=yz)) for s in satirlar) + 4)
    lh = round(boy * aralik)
    im = Image.new('RGBA', (genislik if genislik and hiza != 'l' else w, lh * len(satirlar) + round(boy * 0.3)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for n, s in enumerate(satirlar):
        if hiza == 'm':
            d.text((im.width / 2, n * lh), s, font=yz, fill=renk, anchor='mt')
        else:
            d.text((0, n * lh), s, font=yz, fill=renk)
    return im


def sigan_yazi(metin, boyutlar, genislik, satir, renk=None):
    """Verilen boyutlardan satır sınırına sığan en büyüğüyle metin katmanı."""
    satirlar, yz = k.sigdir(_OLC, str(metin), True, boyutlar, genislik, satir)
    return yazi(' '.join(satirlar) if len(satirlar) == 1 else metin, yz.size, renk, genislik=genislik, satir=satir)


def hap(metin, dolgu=None, renk=None, boy=40, yuk=None, cizgi=None):
    dolgu, renk = dolgu or R.vurgu, renk or R.vurgu_ustu
    yz = F(boy, True)
    yuk = yuk or round(boy * 1.9)
    w = round(_OLC.textlength(metin, font=yz)) + round(boy * 1.5)
    kat = 3
    buyuk = Image.new('RGBA', (w * kat, yuk * kat), (0, 0, 0, 0))
    ImageDraw.Draw(buyuk).rounded_rectangle((0, 0, w * kat - 1, yuk * kat - 1), radius=yuk * kat // 2, fill=dolgu,
                                            outline=cizgi, width=3 * kat if cizgi else 0)
    im = buyuk.resize((w, yuk), Image.Resampling.LANCZOS)
    ImageDraw.Draw(im).text((w / 2, yuk / 2 + 1), metin, font=yz, fill=renk, anchor='mm')
    return im


def panel(w, h, dolgu=None, yaricap=36, cizgi=None):
    if dolgu is None:
        dolgu, cizgi = R.panel, cizgi or R.panel_cizgi
    kat = 2
    buyuk = Image.new('RGBA', (w * kat, h * kat), (0, 0, 0, 0))
    ImageDraw.Draw(buyuk).rounded_rectangle((0, 0, w * kat - 1, h * kat - 1), radius=yaricap * kat, fill=dolgu,
                                            outline=cizgi, width=3 * kat if cizgi else 0)
    return buyuk.resize((w, h), Image.Resampling.LANCZOS)


def logo_rozeti(ilan, logo, cap):
    """Beyaz dairede kurum logosu; logo yoksa baş harf amblemi."""
    kat = 3
    im = Image.new('RGBA', (cap * kat, cap * kat), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if logo:
        d.ellipse((0, 0, cap * kat - 1, cap * kat - 1), fill='#ffffff', outline=R.panel_cizgi, width=2 * kat if R.panel_cizgi else 0)
        with Image.open(io.BytesIO(logo)) as m:
            m = m.convert('RGBA')
            beyaz = Image.new('RGBA', m.size, 'white')
            beyaz.alpha_composite(m)
            kutu = ImageChops.difference(beyaz.convert('RGB'), Image.new('RGB', m.size, 'white')).getbbox()
            m = m.crop(kutu) if kutu else m
            alan = cap * kat * 0.62   # dairenin içine sığan kare
            o = min(alan / m.width, alan / m.height, 3.0)   # çok küçük logo en çok 3 kat büyütülür
            m = m.resize((max(1, round(m.width * o)), max(1, round(m.height * o))), Image.Resampling.LANCZOS)
        im.alpha_composite(m, ((cap * kat - m.width) // 2, (cap * kat - m.height) // 2))
    else:
        d.ellipse((0, 0, cap * kat - 1, cap * kat - 1), fill=R.vurgu)   # logo yoksa baş harfler, palet renginde
        harf = k.bas_harfler(ilan.get('kurum') or '')
        d.text((cap * kat / 2, cap * kat / 2), harf, font=F(round(cap * kat * (0.42 if len(harf) < 3 else 0.32)), True), fill=R.vurgu_ustu, anchor='mm')
    return im.resize((cap, cap), Image.Resampling.LANCZOS)


def kalan_hapi(v, boy=44):
    """Aciliyet rengi: bugün/yarın kırmızı, 2–6 gün turuncu, sonrası lime."""
    metin = k.tr_buyuk(v['kalan_yazi'] or '')
    if not metin:
        return None
    if v['kalan'] is not None and v['kalan'] <= 1:
        return hap(metin, R.acil, R.acil_ustu, boy)
    if v['kalan'] is not None and v['kalan'] <= 6:
        return hap(metin, R.yakin, R.yakin_ustu, boy)
    return hap(metin, R.vurgu, R.vurgu_ustu, boy)


def kisa_kurum(ilan):
    import sosyal_tasarim
    return sosyal_tasarim.kisa_kurum(ilan.get('kurum') or '')


def kadro_satirlari(v, en_cok):
    """[(adet|None, ad)] en kalabalık kadro önce; fazlası için son öğe (None, '+N kadro daha')."""
    kad = sorted(v['kadrolar'], key=lambda x: -(x['adet'] or 0))
    satirlar = [(x['adet'], x['ad']) for x in (kad if len(kad) <= en_cok else kad[:en_cok - 1])]
    if len(kad) > en_cok:
        satirlar.append((None, f'+{len(kad) - (en_cok - 1)} kadro daha'))
    return satirlar


def ne_alinacak(v):
    """('162', 'KİŞİ ALINACAK') ya da sayı bilinmiyorsa (None, ilk kadro adı)."""
    if v['toplam']:
        return v['toplam'], 'KİŞİ ALINACAK'
    return None, (v['kadrolar'][0]['ad'] if v['kadrolar'] else 'Personel alımı')


def kisa_ne(v):
    """Liste satırı için: '162 kişi · Kütüphaneci' / 'Mühendis, Tekniker'."""
    adlar = [x['ad'] for x in sorted(v['kadrolar'], key=lambda x: -(x['adet'] or 0)) if k._norm(x['ad']) not in AD_DEGIL]
    ad = ', '.join(adlar[:2]) + (f' +{len(adlar) - 2}' if len(adlar) > 2 else '')
    return f'{binlik(v["toplam"])} kişi · {ad}' if v['toplam'] and ad else (f'{binlik(v["toplam"])} kişi' if v['toplam'] else ad)


def kosul_satirlari(v):
    """[(etiket, değer)] yalnız veride olanlar."""
    s = []
    if v['duzeyler']:
        s.append(('Öğrenim', ' · '.join(v['duzeyler'])))
    if v['kpss']:
        s.append(('KPSS', v['kpss'].replace('KPSS şartı var · ', 'Şart var · ').replace('KPSS şartı var', 'Şart var').replace('KPSS şartı yok', 'Şart yok')))
    if v['yer']:
        s.append(('Yer', v['yer']))
    return s


def gun_yazi(gun):
    return f'{gun.day} {AYLAR[gun.month - 1]} {GUNLER[gun.weekday()]}'


# ---------------------------------------------------------------- ortak sahneler
def zemin():
    """Koyu petrol dikey geçiş + sağ üstte ince lime köşe çizgileri (sabit; her karede kopyalanır)."""
    im = Image.linear_gradient('L').resize((VW, VH))
    im = Image.merge('RGB', [im.point(lambda p, a=a, b=b: round(a + (b - a) * p / 255)) for a, b in zip(R.zemin_ust, R.zemin_alt)])
    d = ImageDraw.Draw(im)
    for n in range(3):
        d.line((VW - 260 + n * 70, 0, VW, 260 - n * 70), fill=R.cizgi2, width=3)
    return im


def ust_serit(im, sahne_no, sahne_sayisi, oran):
    """Hikâye çubuğu (her sahneye bir parça) ve marka satırı."""
    d = ImageDraw.Draw(im)
    bosluk, y = 10, 204
    w = (SAG - SOL - bosluk * (sahne_sayisi - 1)) / sahne_sayisi
    for n in range(sahne_sayisi):
        x = SOL + n * (w + bosluk)
        d.rounded_rectangle((x, y, x + w, y + 8), radius=4, fill=R.cizgi)
        dolu = 1.0 if n < sahne_no else oran if n == sahne_no else 0.0
        if dolu > 0:
            d.rounded_rectangle((x, y, x + max(8, w * dolu), y + 8), radius=4, fill=R.vurgu)
    logo = k.logo_kare(56)
    if logo is not None:
        im.paste(logo, (SOL, 232), logo)
    d.text((SOL + 72, 260), 'KPSS Tercihi', font=F(34, True), fill=R.yazi, anchor='lm')


def kapanis_sahnesi(ust_satir, sure=3.0):
    """Son sahne: adres ve Telegram; sahne çıkışı yoktur (video bu karede biter)."""
    o = [Oge(yazi(ust_satir, 52, R.soluk, genislik=SAG - SOL, satir=2, hiza='m'), SOL, 560, 0.0),
         Oge(yazi('TÜM İLANLAR', 104, R.yazi, genislik=SAG - SOL, hiza='m'), SOL, 720, 0.12),
         Oge(yazi('TEK YERDE', 104, R.vurgu, genislik=SAG - SOL, hiza='m'), SOL, 840, 0.22)]
    adres = panel(SAG - SOL, 150, R.vurgu, 44)
    ImageDraw.Draw(adres).text((adres.width / 2, 76), 'kpsstercihi.com', font=F(72, True), fill=R.vurgu_ustu, anchor='mm')
    o.append(Oge(adres, SOL, 1040, 0.45, 'buyu'))
    tg = hap('Telegram: @kpsstercihi', R.panel, R.yazi, 44, cizgi=R.vurgu)
    o.append(Oge(tg, (VW - tg.width) / 2, 1240, 0.7))
    o.append(Oge(yazi('Kaydet, son güne kalmasın', 44, R.soluk, genislik=SAG - SOL, hiza='m'), SOL, 1400, 0.95))
    return Sahne(sure, o, son=True)


def ilan_kutusu(ilan, logo, simdi, y, bas, sira=None):
    """Sabah videosundaki tek ilan sahnesinin öğeleri (kalan gün rozeti, kurum, kaç kişi, koşullar, son başvuru)."""
    v = k.veri(ilan, logo, simdi)
    o = []
    if sira:
        o.append(Oge(hap(sira, R.panel, R.soluk, 34, cizgi=R.cizgi), SOL, y, bas))
    rozet = kalan_hapi(v, 48)
    if rozet:
        o.append(Oge(rozet, SAG - rozet.width, y - 8, bas + 0.05, 'buyu'))
    y += 130
    o.append(Oge(logo_rozeti(ilan, logo, 190), SOL, y, bas + 0.1, 'buyu'))
    ad = sigan_yazi(kisa_kurum(ilan), [62, 54, 48], SAG - SOL - 230, 3)
    o.append(Oge(ad, SOL + 230, y + max(0, (190 - ad.height) // 2), bas + 0.18, 'sol'))
    y += 250
    sayi, alt = ne_alinacak(v)
    kutu = panel(SAG - SOL, 330, yaricap=44)
    o.append(Oge(kutu, SOL, y, bas + 0.28))
    if sayi:
        o.append(Sayac(sayi, SOL + 48, y + 28, 170, R.vurgu, bas + 0.34, 0.7))
        o.append(Oge(yazi(alt, 50, R.yazi), SOL + 52, y + 232, bas + 0.4))
    else:
        o.append(Oge(sigan_yazi(alt, [84, 70, 58], SAG - SOL - 100, 3, R.vurgu), SOL + 48, y + 40, bas + 0.34))
    y += 370
    adlar = ', '.join(a for _, a in kadro_satirlari(v, 4))
    if sayi and adlar:
        o.append(Oge(yazi(adlar, 44, R.yazi, genislik=SAG - SOL, satir=2), SOL, y, bas + 0.5))
        y += 130
    kosul = ' · '.join(p for p in (' · '.join(v['duzeyler']), v['kpss']) if p)
    if kosul:
        o.append(Oge(yazi(kosul, 40, R.soluk, False, genislik=SAG - SOL, satir=2), SOL, y, bas + 0.6))
        y += 120
    if v['tarih']:
        o.append(Oge(yazi('Son başvuru: ' + v['tarih'], 44, R.vurgu, genislik=SAG - SOL, satir=1), SOL, min(y + 10, ALT - 70), bas + 0.7))
    return o


# ---------------------------------------------------------------- 1) sabah: son günü yaklaşan ilanlar
def son_gun_ilanlari(acik, simdi, en_cok=SON_GUN_EN_COK):
    """Son başvurusu bugün ile SON_GUN_UFUK gün sonrası arasında olanlar; en yakın tarih, sonra en kalabalık alım önce."""
    from site_uret import _bitis
    secim = [i for i in acik if 0 <= (_bitis(i).date() - simdi.date()).days <= _ayar('son_gun_ufuk')]
    secim.sort(key=lambda i: (_bitis(i).date(), -(k.veri(i, None, simdi)['toplam'] or 0), i.get('id') or ''))
    return secim[:en_cok], len(secim)


def son_gun_videosu(ilanlar, toplam, simdi, logo=lambda i: None):
    """ilanlar: son_gun_ilanlari çıktısı. Sahne listesi döner; ilan yoksa None."""
    if not ilanlar:
        return None
    from site_uret import _bitis
    kalanlar = [(_bitis(i).date() - simdi.date()).days for i in ilanlar]
    bugun, yarin = kalanlar.count(0), kalanlar.count(1)
    ozet = ' · '.join(p for p in (f'bugün {bugun}' if bugun else '', f'yarın {yarin}' if yarin else '',
                                  f'{toplam - bugun - yarin} ilan birkaç gün içinde' if toplam - bugun - yarin > 0 else '') if p)
    giris = [Oge(hap(gun_yazi(simdi), R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 420, 0.0, 'buyu'),
             Oge(yazi('SON GÜNÜ', 132, R.yazi), SOL, 560, 0.1, 'sol'),
             Oge(yazi('YAKLAŞAN', 132, R.yazi), SOL, 710, 0.2, 'sol'),
             Sayac(toplam, SOL, 880, 300, R.vurgu, 0.3, 0.7),
             Oge(yazi('İLAN', 132, R.vurgu), SOL + round(_OLC.textlength(binlik(toplam), font=F(300, True))) + 36, 1030, 0.5, 'sol'),
             Oge(yazi(ozet[0].upper() + ozet[1:] if ozet else '', 46, R.soluk, genislik=SAG - SOL, satir=2), SOL, 1290, 0.75)]
    sahneler = [Sahne(2.4, giris)]
    for n, i in enumerate(ilanlar, 1):
        sahneler.append(Sahne(2.7, ilan_kutusu(i, logo(i), simdi, 400, 0.0, f'{n} / {len(ilanlar)}')))
    fazla = toplam - len(ilanlar)
    sahneler.append(kapanis_sahnesi(f'+{fazla} ilan daha sitede' if fazla > 0 else 'Başvurmadan önce şartları oku'))
    return sahneler


# ---------------------------------------------------------------- 2) tek ilan
def ilan_videosu(ilan, simdi, logo=None):
    v = k.veri(ilan, logo, simdi)
    sayi, alt = ne_alinacak(v)
    # Sahne 1: kim, kaç kişi
    o = [Oge(hap('YENİ İLAN', R.vurgu, R.vurgu_ustu, 46), SOL, 400, 0.0, 'buyu'),
         Oge(logo_rozeti(ilan, logo, 230), SOL, 540, 0.1, 'buyu')]
    ad = sigan_yazi(kisa_kurum(ilan), [68, 60, 52], SAG - SOL, 3)
    o.append(Oge(ad, SOL, 810, 0.2, 'sol'))
    y = 810 + ad.height + 30
    if sayi:
        o += [Sayac(sayi, SOL, y, 320, R.vurgu, 0.35, 0.8), Oge(yazi(alt, 76, R.yazi), SOL, y + 400, 0.55)]
    else:
        o.append(Oge(sigan_yazi(alt, [120, 100, 84, 70], SAG - SOL, 3, R.vurgu), SOL, y + 20, 0.35))
    sahneler = [Sahne(2.6, o)]
    # Sahne 2: kadrolar
    satirlar = kadro_satirlari(v, 5)
    if satirlar:
        o = [Oge(yazi('HANGİ KADROLAR?', 60, R.vurgu), SOL, 400, 0.0, 'sol')]
        for n, (adet, kad) in enumerate(satirlar):
            kutu = panel(SAG - SOL, 170, yaricap=36)
            d = ImageDraw.Draw(kutu)
            x = 44
            if adet:
                d.text((x, 85), binlik(adet), font=F(76, True), fill=R.vurgu, anchor='lm')
                x += round(d.textlength(binlik(adet), font=F(76, True))) + 32
            s, yz = k.sigdir(d, kad, True, [50, 44, 38], kutu.width - x - 40, 2)
            for m, satir in enumerate(s):
                d.text((x, 85 + (m - (len(s) - 1) / 2) * yz.size * 1.15), satir, font=yz, fill=R.yazi if adet is not None or len(satirlar) == 1 else R.soluk, anchor='lm')
            o.append(Oge(kutu, SOL, 520 + n * 194, 0.15 + n * 0.16))
        sahneler.append(Sahne(1.6 + 0.45 * len(satirlar), o))
    # Sahne 3: kimler başvurabilir
    kosullar = kosul_satirlari(v)
    if kosullar:
        o = [Oge(yazi('KİMLER', 96, R.yazi), SOL, 400, 0.0, 'sol'), Oge(yazi('BAŞVURABİLİR?', 96, R.vurgu), SOL, 510, 0.1, 'sol')]
        for n, (etiket, deger) in enumerate(kosullar):
            kutu = panel(SAG - SOL, 220, yaricap=36)
            d = ImageDraw.Draw(kutu)
            d.text((44, 34), k.tr_buyuk(etiket), font=F(34, True), fill=R.soluk)
            s, yz = k.sigdir(d, deger, True, [60, 52, 44, 38], kutu.width - 88, 2)
            k.blok(d, 44, 92 if len(s) == 1 else 82, s, yz, R.yazi, aralik=round(yz.size * 1.12))
            o.append(Oge(kutu, SOL, 700 + n * 248, 0.3 + n * 0.2))
        sahneler.append(Sahne(2.9, o))
    # Sahne 4: son başvuru + adres (video burada biter)
    o = [Oge(yazi('SON BAŞVURU', 60, R.vurgu), SOL, 400, 0.0, 'sol')]
    y = 520
    bitis, saatli = k._bitis(ilan)
    if bitis:
        o.append(Oge(yazi(f'{bitis.day} {AYLAR[bitis.month - 1]}', 190, R.yazi), SOL, y, 0.12))
        o.append(Oge(yazi(GUNLER[bitis.weekday()] + (f' · {bitis:%H:%M}' if saatli else ''), 56, R.soluk), SOL, y + 240, 0.24))
        rozet = kalan_hapi(v, 56)
        if rozet:
            o.append(Oge(rozet, SOL, y + 360, 0.4, 'buyu'))
        y += 520
    kutu = panel(SAG - SOL, 300, R.vurgu, 44)
    d = ImageDraw.Draw(kutu)
    d.text((48, 44), 'Şartların tamamı ve başvuru bağlantısı', font=F(38, True), fill=R.vurgu_ustu)
    d.text((48, 108), 'kpsstercihi.com', font=F(84, True), fill=R.vurgu_ustu)
    d.text((48, 226), 'Telegram: @kpsstercihi', font=F(38, True), fill=R.vurgu_ustu)
    o.append(Oge(kutu, SOL, min(y, ALT - 320), 0.6, 'buyu'))
    sahneler.append(Sahne(3.2, o, son=True))
    return sahneler


# ---------------------------------------------------------------- 3) akşam: bugünün özeti
def bugunun_ilanlari(acik, simdi):
    """Bugün (TR) siteye eklenen açık ilanlar; en kalabalık alım önce."""
    from sosyal_motor import _zaman
    secim = [i for i in acik if (_zaman(i.get('ilk_gorulme')) or simdi - timedelta(days=9)).astimezone(k.TR).date() == simdi.date()]
    secim.sort(key=lambda i: (-(k.veri(i, None, simdi)['toplam'] or 0), i.get('id') or ''))
    return secim


def ozet_satiri(ilan, logo, simdi):
    v = k.veri(ilan, logo, simdi)
    kutu = panel(SAG - SOL, 300, yaricap=40)
    kutu.alpha_composite(logo_rozeti(ilan, logo, 150), (36, 36))
    d = ImageDraw.Draw(kutu)
    s, yz = k.sigdir(d, kisa_kurum(ilan), True, [46, 40, 36], kutu.width - 240, 2)
    k.blok(d, 216, 40 if len(s) > 1 else 66, s, yz, R.yazi, aralik=round(yz.size * 1.12))
    ne = k.lines(d, kisa_ne(v), F(42, True), kutu.width - 72, 1)[0]
    d.text((36, 212), ne, font=F(42, True), fill=R.vurgu)
    bitis, _ = k._bitis(ilan)
    if bitis:
        d.text((216, 150 if len(s) > 1 else 136), f'Son başvuru {bitis.day} {AYLAR[bitis.month - 1]}', font=F(34), fill=R.soluk)
    return kutu


def parcala(n, satir=OZET_SATIR):
    """n ilanı sahnelere böler; son sahnede tek satır kalmasın diye 7 -> 3+2+2, 4 -> 2+2."""
    boylar = [satir] * (n // satir) + ([n % satir] if n % satir else [])
    if len(boylar) > 1 and boylar[-1] == 1:
        boylar[-2:] = [boylar[-2] - 1, 2]
    return boylar


def ozet_videosu(ilanlar, simdi, logo=lambda i: None):
    if not ilanlar:
        return None
    kadro = sum(k.veri(i, None, simdi)['toplam'] or 0 for i in ilanlar)
    kurum = len({k._norm(i.get('kurum') or '') for i in ilanlar})
    n = len(ilanlar)
    o = [Oge(hap(gun_yazi(simdi), R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 420, 0.0, 'buyu'),
         Oge(yazi('BUGÜN', 132, R.yazi), SOL, 560, 0.1, 'sol'),
         Sayac(n, SOL, 720, 300, R.vurgu, 0.25, 0.7),
         Oge(yazi('YENİ', 110, R.vurgu), SOL + round(_OLC.textlength(binlik(n), font=F(300, True))) + 36, 790, 0.4, 'sol'),
         Oge(yazi('İLAN', 110, R.vurgu), SOL + round(_OLC.textlength(binlik(n), font=F(300, True))) + 36, 910, 0.48, 'sol')]
    x = SOL
    for m, (deger, etiket) in enumerate(((kadro, 'kadro'), (kurum, 'kurum'))):
        if deger:
            kutu = panel(450, 230, yaricap=40)
            d = ImageDraw.Draw(kutu)
            d.text((40, 30), binlik(deger), font=F(104, True), fill=R.yazi)
            d.text((40, 160), etiket, font=F(40, True), fill=R.soluk)
            o.append(Oge(kutu, x, 1170, 0.7 + m * 0.14))
            x += 486
    sahneler = [Sahne(2.8, o)]
    gosterilen = ilanlar[:OZET_SATIR * OZET_SAHNE]
    s = 0
    for boy in parcala(len(gosterilen)):
        parca = gosterilen[s:s + boy]
        o = [Oge(yazi('BUGÜN AÇILANLAR', 56, R.vurgu), SOL, 400, 0.0, 'sol'),
             Oge(hap(f'{s + 1}–{s + len(parca)} / {n}', R.panel, R.soluk, 34, cizgi=R.cizgi), SAG - 230, 400, 0.0)]
        for m, i in enumerate(parca):
            o.append(Oge(ozet_satiri(i, logo(i), simdi), SOL, 520 + m * 330, 0.15 + m * 0.22))
        sahneler.append(Sahne(1.9 + 0.7 * len(parca), o))
        s += boy
    fazla = n - len(gosterilen)
    sahneler.append(kapanis_sahnesi(f'+{fazla} ilan daha sitede' if fazla > 0 else 'Son başvuru tarihleriyle hepsi'))
    return sahneler


# ---------------------------------------------------------------- yeni biçimler (23 Kasım 2026'dan): kimler, meslek, düzey
# Rakip kalıbı: arama sorusu gibi başlık + yıl + yüksek zıtlık. Her biçimin kendi paleti var (BICIM_PALETI).
def _ascii(metin):
    return k._norm(metin).translate(str.maketrans('çğıöşü', 'cgiosu'))


def _gun_ay(d, buyuk=False):
    s = f'{d.day} {AYLAR[d.month - 1]}'
    return k.tr_buyuk(s) if buyuk else s


def _baslangic(ilan):
    try:
        b = datetime.fromisoformat(ilan.get('baslangic_zaman') or '')
    except (ValueError, TypeError):
        return None
    return (b.replace(tzinfo=k.TR) if b.tzinfo is None else b).astimezone(k.TR)


def _tarih_araligi(ilan):
    """'30 Kasım – 4 Aralık' (başlangıç biliniyorsa), yoksa 'Son gün 4 Aralık'; tarih yoksa ''."""
    bitis, _ = k._bitis(ilan)
    bas = _baslangic(ilan)
    if bitis and bas:
        return f'{_gun_ay(bas)} – {_gun_ay(bitis)}'
    return f'Son gün {_gun_ay(bitis)}' if bitis else ''


_RED = ('kabul edilmez', 'kabul edilmeyecek', 'kabul olunmaz', 'alinmaz', 'alinmayacak', 'yapilamaz', 'gecersiz', 'itiraz')


def basvuru_sekli(ilan):
    """Özet ve başvuru notundan başvuru yolu; belgede geçmiyorsa ''. Reddeden cümleler ('şahsen yapılan başvurular kabul
    edilmeyecektir') ve itiraz cümleleri sayılmaz; 'e-posta' posta değildir."""
    metin = f'{ilan.get("ozet") or ""} {ilan.get("basvuru_notu") or ""}'
    # cümle sonu: noktalama + boşluk + büyük harf/rakam ('vb. yoluyla' bölünmez)
    cumleler = [_ascii(c) for c in re.split(r'(?<=[.;!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])', metin)]
    cumleler = [c for c in cumleler if not any(r in c for r in _RED)]
    if any(('e-devlet' in c or 'kariyer kapisi' in c) and 'basvur' in c and 'barkod' not in c for c in cumleler):
        return 'e-Devlet · Kariyer Kapısı'
    m = re.sub(r'\be[\s-]?posta', 'eposta', ' '.join(cumleler))
    yollar = [ad for ad, var in (('şahsen', 'sahsen' in m), ('e-posta', 'eposta' in m), ('posta', re.search(r'\bposta', m))) if var]
    if yollar == ['şahsen']:
        return 'Şahsen, belgelerle'
    if not yollar:
        return ''
    s = yollar[0] if len(yollar) == 1 else ', '.join(yollar[:-1]) + ' veya ' + yollar[-1]
    return s[0].upper() + s[1:] + ' ile'


_RAKAM = {'bir': 1, 'iki': 2, 'uc': 3, 'dort': 4, 'bes': 5, 'alti': 6, 'yedi': 7, 'sekiz': 8, 'dokuz': 9}
_ONLUK = {'yirmi': 20, 'otuz': 30, 'kirk': 40, 'elli': 50}
_YAS = re.compile(r'(?<![\w])(\d{2}|(?:yirmi|otuz|kirk|elli)(?:\s+(?:bir|iki|uc|dort|bes|alti|yedi|sekiz|dokuz))?)\s*(?:\([^)]{0,24}\)\s*)?yasini\s+doldurma\s?mis')


def yas_sarti(ilan):
    """Şartlardaki '(otuz beş) yaşını doldurmamış olmak' -> 35; bulunamazsa None."""
    for s in ilan.get('sartlar') or []:
        m = _YAS.search(_ascii(s.get('metin') or ''))
        if not m:
            continue
        if m.group(1).isdigit():
            yas = int(m.group(1))
        else:
            p = m.group(1).split()
            yas = _ONLUK[p[0]] + (_RAKAM[p[1]] if len(p) > 1 else 0)
        if 18 <= yas <= 65:
            return yas
    return None


def bantlar(satirlar, boy, x, y, bas, bant=None, renk=None, aralik=None):
    """Fosforlu kalem gibi: her satır kendi dolgu bandının üstünde. (öğeler, alt kenar) döner."""
    bant, renk = bant or R.vurgu, renk or R.vurgu_ustu
    o, aralik = [], aralik or round(boy * 1.22)
    for n, s in enumerate(satirlar):
        yz = F(boy, True)
        w = round(_OLC.textlength(s, font=yz)) + 56
        h = round(boy * 1.18)
        kat = panel(w, h, bant, 14)
        ImageDraw.Draw(kat).text((28, h / 2 + boy * 0.04), s, font=yz, fill=renk, anchor='lm')
        o.append(Oge(kat, x, y + n * aralik, bas + n * 0.08, 'sol'))
    return o, y + len(satirlar) * aralik


def _bant_sar(kelimeler, boy):
    """Kelimeleri sırayla sararak her satırı bant genişliğine (GEN) sığdırır; tek kelime bile sığmıyorsa None."""
    yz = F(boy, True)
    sonuc, mevcut = [], ''
    for w in kelimeler:
        aday = (mevcut + ' ' + w).strip()
        if _OLC.textlength(aday, font=yz) + 56 <= GEN:
            mevcut = aday
        else:
            if mevcut:
                sonuc.append(mevcut)
            mevcut = w
    if mevcut:
        sonuc.append(mevcut)
    return sonuc if all(_OLC.textlength(s, font=yz) + 56 <= GEN for s in sonuc) else None


def bilgi_kutusu(etiket, deger, boyutlar=(56, 50, 44), satir=2):
    """Etiket + değer kutusu; yükseklik metne göre."""
    s, yz = k.sigdir(_OLC, deger, True, list(boyutlar), GEN - 88, satir)
    kutu = panel(GEN, round(86 + len(s) * yz.size * 1.14 + 34), yaricap=36)
    d = ImageDraw.Draw(kutu)
    d.text((44, 30), k.tr_buyuk(etiket), font=F(34, True), fill=R.soluk)
    k.blok(d, 44, 86, s, yz, R.yazi, aralik=round(yz.size * 1.14))
    return kutu


def kutu_yigini(ciftler, y, bas, alt_sinir=ALT, ara=24, adim=0.15):
    """(etiket, değer) çiftlerini alt alta dizer; güvenli alana sığmazsa yazıyı küçültür, hâlâ sığmazsa sondan kutu atar.
    (öğeler, alt kenar) döner."""
    ciftler = list(ciftler)
    while True:
        for boyutlar, satir in (((56, 50, 44), 2), ((44, 38), 1), ((34, 30), 1)):
            kutular = [bilgi_kutusu(e, d_, boyutlar, satir) for e, d_ in ciftler]
            if y + sum(x.height + ara for x in kutular) - ara <= alt_sinir:
                break
        if y + sum(x.height + ara for x in kutular) - ara <= alt_sinir or len(ciftler) <= 1:
            break
        ciftler.pop()
    o = []
    for n, kt in enumerate(kutular):
        o.append(Oge(kt, SOL, y, bas + n * adim))
        y += kt.height + ara
    return o, y


def kapanis_kutusu(ust, alt='kpsstercihi.com'):
    kutu = panel(GEN, 220, R.vurgu, 44)
    d = ImageDraw.Draw(kutu)
    d.text((48, 40), k.lines(d, ust, F(38, True), GEN - 96, 1)[0], font=F(38, True), fill=R.vurgu_ustu)
    d.text((48, 100), alt, font=F(80, True), fill=R.vurgu_ustu)
    return kutu


def _hap_sigan(metin, dolgu=None, renk=None, boyutlar=(40, 36, 32, 28), cizgi=None):
    boy = next((b for b in boyutlar if _OLC.textlength(metin, font=F(b, True)) + round(b * 1.5) <= GEN), boyutlar[-1])
    return hap(metin, dolgu, renk, boy, cizgi=cizgi)


def _orta_yazi(metin, boyutlar, renk, y, bas):
    boy = next((b for b in boyutlar if _OLC.textlength(metin, font=F(b, True)) <= GEN - 8), boyutlar[-1])
    return Oge(yazi(metin, boy, renk, genislik=GEN, hiza='m'), SOL, y, bas)


def _kurumlu(acik):
    """Kurum adı olan ilanlar (adı boş ilan satırı/başlığı boş yazı katmanı çizemez)."""
    return [i for i in acik if kisa_kurum(i).strip()]


def _ana_kadro(v):
    """En kalabalık gerçek kadro adı; yalnız 'Alacak' gibi kalıntılar varsa ''."""
    for x in sorted(v['kadrolar'], key=lambda x: -(x['adet'] or 0)):
        if k._norm(x['ad']) not in AD_DEGIL:
            return x['ad']
    return ''


def _baslik_kadro(v):
    """Başlığa giren kadro adı. Toplam sayı tüm kadroları kapsar: kadrolar aynı meslekse sade ad ('Zabıta Memuru — Erkek
    (Spor)' -> 'Zabıta Memuru'), farklı mesleklerse 'Personel' ('8 Yazılım Mimarı' yanlış olur). Kadro yoksa ''."""
    ad = _ana_kadro(v)
    if not ad:
        return ''
    meslekler = {meslek_anahtari(x['ad']) or k._norm(x['ad']) for x in v['kadrolar'] if k._norm(x['ad']) not in AD_DEGIL}
    if len(meslekler) > 1:
        return 'Personel'
    return re.sub(r'\s*(—|–|\(|\s-\s).*$', '', ad).strip() or ad


# ---------------------------------------------------------------- a) kimler başvurabilir (tek ilan)
def _kimler_hapi(ilan, simdi):
    bitis, _ = k._bitis(ilan)
    kalan = (bitis.date() - simdi.date()).days if bitis else None
    bas = _baslangic(ilan)
    if kalan is not None and 0 <= kalan <= 7:
        return 'BUGÜN SON GÜN' if kalan == 0 else f'SON BAŞVURU {_gun_ay(bitis, True)} · {kalan} GÜN KALDI'
    if bas and bas.date() > simdi.date():
        return f'BAŞVURU {_gun_ay(bas, True)} – {_gun_ay(bitis, True)}' if bitis else f'BAŞVURU {_gun_ay(bas, True)} BAŞLIYOR'
    return 'YENİ İLAN'


def _kimler_kutulari(ilan, v):
    c = []
    if v['duzeyler']:
        c.append(('Öğrenim', ' · '.join(v['duzeyler'])))
    if ilan.get('kpss') == 'kpsssiz':
        c.append(('KPSS', 'KPSS şartı yok'))
    elif ilan.get('puan_turleri'):
        c.append(('KPSS', ' · '.join(ilan['puan_turleri'])))
    elif v['kpss']:
        c.append(('KPSS', v['kpss']))
    if c and c[-1][0] == 'KPSS':   # 'P39,P40' gibi bitişik listeler okunur olsun
        c[-1] = ('KPSS', re.sub(r'\s*,\s*', ' · ', c[-1][1]))
    yas = yas_sarti(ilan)
    if yas:
        c.append(('Yaş', f'{yas} yaşını doldurmamış olmak'))
    if len(v['kadrolar']) > 1:
        c.append(('Kadrolar', ' · '.join((f'{x["adet"]} ' if x['adet'] else '') + x['ad'] for x in v['kadrolar'][:3])))
    return c


def kimler_videosu(ilan, simdi, logo=None):
    """Tek ilan: 'X kurumu N kişi alıyor — kimler başvurabilir?'. Anlatacak kadro ve sayı yoksa None."""
    v = k.veri(ilan, logo, simdi)
    ad = _ana_kadro(v)
    if (not v['toplam'] and not ad) or not kisa_kurum(ilan).strip():   # kurum adı yoksa eski biçime düşülür
        return None
    kurum = k.tr_buyuk(kisa_kurum(ilan)).split()
    ad = _baslik_kadro(v)
    adk = k.tr_buyuk(ad).split() if ad else []
    if len(adk) > 2 and adk[:2] == kurum[:2]:   # 'Sosyal Güvenlik Kurumu' + 'Sosyal Güvenlik Denetmen Yardımcısı': tekrar eden başı at
        adk = adk[2:]
    satir = boy = None
    # kadro adı kelime kelime kesilmez ('Denetmen Yardımcısı' -> 'Denetmen' yanlış olur); sığmazsa 'PERSONEL'
    for kadro_k in dict.fromkeys((tuple(adk), ('PERSONEL',) if adk else ())):
        kel = kurum + ([binlik(v['toplam'])] if v['toplam'] else []) + list(kadro_k) + ['ALIYOR']
        for b in (118, 104, 92, 80, 70, 60, 50):
            s = _bant_sar(kel, b)
            if s and len(s) <= 5:
                satir, boy = s, b
                break
        if satir:
            break
    if not satir:
        return None
    o = [Oge(_hap_sigan(_kimler_hapi(ilan, simdi), R.vurgu, R.vurgu_ustu), SOL, 400, 0.0, 'buyu')]
    b, y = bantlar(satir, boy, SOL, 520, 0.1)
    o += b
    kb = 96
    while y + 40 + round(kb * 1.22) + round(kb * 1.14) > ALT and kb > 60:
        kb -= 4
    o += [Oge(yazi('KİMLER', kb, R.yazi), SOL, y + 40, 0.5, 'sol'), Oge(yazi('BAŞVURABİLİR?', kb, R.yazi), SOL, y + 40 + round(kb * 1.14), 0.6, 'sol')]
    sahneler = [Sahne(2.7, o)]
    kutular = _kimler_kutulari(ilan, v)
    if kutular:
        yg, _ = kutu_yigini(kutular, 520, 0.15)
        sahneler.append(Sahne(3.0, [Oge(sigan_yazi('KİMLER BAŞVURABİLİR?', [72, 64, 56], GEN, 1, R.yazi), SOL, 400, 0.0, 'sol')] + yg))
    nasil = []
    if basvuru_sekli(ilan):
        nasil.append(('Başvuru', basvuru_sekli(ilan)))
    if _tarih_araligi(ilan):
        nasil.append(('Tarih', _tarih_araligi(ilan)))
    yg, yy = kutu_yigini(nasil, 520, 0.15, ALT - 250) if nasil else ([], 520)
    sahneler.append(Sahne(3.4, [Oge(sigan_yazi('NASIL BAŞVURULUR?', [72, 64, 56], GEN, 1, R.yazi), SOL, 400, 0.0, 'sol')] + yg +
                          [Oge(kapanis_kutusu('Takip et, her gün yeni kamu alımı'), SOL, yy + 6, 0.65, 'buyu')], son=True))
    return sahneler


# ---------------------------------------------------------------- b) meslek: aynı mesleğin açık ilanları
MESLEK_EN_AZ_ILAN, MESLEK_EN_AZ_KADRO, MESLEK_TEKRAR_GUN = 3, 10, 7
MESLEK_SATIR_EN_COK = 5
MESLEK_DEGIL = {'personel', 'sozlesmeli personel', 'memur', 'sozlesmeli memur', 'surekli isci', 'isci', 'uzman', 'sozlesmeli',
                'surekli personel', 'gecici isci', 'kadrolu isci', 'engelli', 'engelli personel', 'eski hukumlu', 'terorzede',
                'sozlesmeli bilisim personeli'}


def meslek_anahtari(ad):
    """'Zabıta Memuru Alacak' -> 'zabita memuru'; genel adlar ('Personel', 'Sürekli İşçi') için None."""
    s = re.sub(r'\([^)]*\)', ' ', _ascii(ad))
    s = re.sub(r'[^a-z0-9 ]+', ' ', s).split()
    while s and s[-1] in ('alacak', 'alinacak', 'alimi', 'alim', 'erkek', 'kadin', 'bay', 'bayan', 'lisans', 'onlisans', 'ortaogretim', 'lise'):
        s.pop()
    s = ' '.join(s)
    return None if not s or s in MESLEK_DEGIL or s in AD_DEGIL else s


def meslek_gruplari(acik, simdi):
    """{anahtar: {'anahtar', 'ad', 'toplam', 'ilanlar': [(ilan, adet)]}}; adet o ilandaki o mesleğin kadro sayısı."""
    from collections import Counter
    gruplar, adlar = {}, {}
    for i in _kurumlu(acik):
        bu = {}
        for x in k.veri(i, None, simdi)['kadrolar']:
            a = meslek_anahtari(x['ad'])
            if a:
                bu[a] = bu.get(a, 0) + (x['adet'] or 0)
                adlar.setdefault(a, Counter())[x['ad']] += 1
        for a, adet in bu.items():
            g = gruplar.setdefault(a, {'anahtar': a, 'toplam': 0, 'ilanlar': []})
            g['toplam'] += adet
            g['ilanlar'].append((i, adet))
    for a, g in gruplar.items():
        g['ad'] = adlar[a].most_common(1)[0][0]
        g['ilanlar'].sort(key=lambda t: (-t[1], t[0].get('id') or ''))
    return gruplar


def meslek_grubu_sec(acik, simdi, gecmis=()):
    """Açık ilanlarda en çok kadro çıkaran meslek (>= 3 ilan ve >= 10 kadro); son 7 günde işlenen meslek atlanır."""
    from sosyal_motor import _zaman
    yakin = {g.get('anahtar') for g in gecmis
             if (_zaman(g.get('zaman')) or simdi - timedelta(days=99)) > simdi - timedelta(days=MESLEK_TEKRAR_GUN)}
    uygun = [g for g in meslek_gruplari(acik, simdi).values()
             if len(g['ilanlar']) >= MESLEK_EN_AZ_ILAN and g['toplam'] >= MESLEK_EN_AZ_KADRO and f'meslek:{g["anahtar"]}' not in yakin]
    return min(uygun, key=lambda g: (-g['toplam'], -len(g['ilanlar']), g['anahtar'])) if uygun else None


def _bitis_yazi(i):
    b, _ = k._bitis(i)
    return _gun_ay(b) if b else ''


def meslek_satiri(i, adet, simdi):
    kutu = panel(GEN, 184, yaricap=36)
    d = ImageDraw.Draw(kutu)
    v = k.veri(i, None, simdi)
    sayi = binlik(adet) if adet else '·'
    boy = next((b for b in (92, 80, 68, 56) if d.textlength(sayi, font=F(b, True)) <= 150), 56)
    d.text((40, 92), sayi, font=F(boy, True), fill=R.vurgu, anchor='lm')
    x = 220
    d.text((x, 34), k.lines(d, kisa_kurum(i), F(46, True), GEN - x - 30, 1)[0], font=F(46, True), fill=R.yazi)
    alt = ' · '.join(p for p in (' · '.join(v['duzeyler']), f'son gün {_bitis_yazi(i)}' if _bitis_yazi(i) else '') if p)
    if alt:
        d.text((x, 104), k.lines(d, alt, F(36), GEN - x - 30, 1)[0], font=F(36), fill=R.soluk)
    return kutu


def _meslek_sahneleri(g, simdi, logo):
    ad, ilanlar = g['ad'], g['ilanlar']
    toplam = g['toplam']
    v_ler = [k.veri(i, None, simdi) for i, _ in ilanlar]
    kurum_say = len({k._norm(i.get('kurum') or '') for i, _ in ilanlar})
    duzeyler = list(dict.fromkeys(x for v in v_ler for x in v['duzeyler']))
    alt_satir = f'{kurum_say} kurum' + (' · ' + (' ve '.join(k._norm(x) for x in duzeyler) if len(duzeyler) <= 2 else ' · '.join(k._norm(x) for x in duzeyler)) if duzeyler else '')
    # Kapak: bant boyu ve sayaç boyu, hepsi güvenli alana ve satır genişliğine sığacak şekilde
    secim = None
    for boy in (150, 130, 110, 92, 80, 70):
        satir = _bant_sar(k.tr_buyuk(ad).split(), boy)
        if not satir or len(satir) > 3 or _OLC.textlength('ALIMLARI', font=F(boy, True)) + 56 > GEN:
            continue
        satir = satir + ['ALIMLARI']
        by = 510 + len(satir) * round(boy * 1.22)
        for sb in (330, 290, 250, 210, 180, 150):
            w = round(_OLC.textlength(binlik(toplam), font=F(sb, True)))
            if w + 30 + round(_OLC.textlength('KADRO', font=F(86, True))) <= GEN and by + 24 + round(sb * 1.21) + 60 <= ALT:
                secim = (satir, boy, by, sb, w)
                break
        if secim:
            break
    if not secim:
        return None
    satir, boy, by, sb, w = secim
    s1 = [Oge(hap(k.tr_buyuk(f'{AYLAR[simdi.month - 1]} {simdi.year}'), R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 400, 0.0, 'buyu')]
    b, _ = bantlar(satir, boy, SOL, 510, 0.1)
    s1 += b
    s1 += [Sayac(toplam, SOL, by + 24, sb, R.yazi, 0.3, 0.7),
           Oge(yazi('KADRO', 86, R.vurgu), SOL + w + 30, by + 24 + round(sb * 0.58), 0.5, 'sol'),
           Oge(yazi(alt_satir, 48, R.soluk, genislik=GEN, satir=1), SOL, by + 24 + round(sb * 1.21), 0.6)]
    sahneler = [Sahne(2.7, s1)]
    # Liste: kadro sayısına göre, en çok 2 sahne
    gosterilen = ilanlar[:MESLEK_SATIR_EN_COK * 2]
    n = len(gosterilen)
    parcalar = [n] if n <= MESLEK_SATIR_EN_COK else [(n + 1) // 2, n // 2]
    bas = 0
    for p in parcalar:
        o = [Oge(sigan_yazi('HANGİ KURUMLAR?', [64, 56, 48], GEN - 240, 1, R.vurgu), SOL, 400, 0.0, 'sol')]
        if len(parcalar) > 1:
            o.append(Oge(hap(f'{bas + 1}–{bas + p} / {len(ilanlar)}', R.panel, R.soluk, 34, cizgi=R.cizgi), SAG - 230, 400, 0.0))
        for m, (i, adet) in enumerate(gosterilen[bas:bas + p]):
            o.append(Oge(meslek_satiri(i, adet, simdi), SOL, 520 + m * 200, 0.15 + m * 0.2))
        sahneler.append(Sahne(1.8 + 0.4 * p, o))
        bas += p
    # En büyüğü
    i, adet = ilanlar[0]
    v = v_ler[0]
    o = [Oge(yazi('EN BÜYÜĞÜ', 64, R.vurgu), SOL, 400, 0.0, 'sol')]
    isim = sigan_yazi(kisa_kurum(i), [96, 84, 72, 60], GEN, 2, R.yazi)
    o.append(Oge(isim, SOL, 500, 0.1, 'sol'))
    y = 500 + isim.height + 20
    if adet:
        o += [Sayac(adet, SOL, y, 260, R.vurgu, 0.2, 0.6),
              Oge(yazi('kadro', 56, R.soluk), SOL + round(_OLC.textlength(binlik(adet), font=F(260, True))) + 24, y + 150, 0.4, 'sol')]
        y += round(260 * 1.21) + 10
    kutular = []
    basvuru = ' · '.join(p for p in (_tarih_araligi(i), basvuru_sekli(i)) if p)
    if basvuru:
        kutular.append(('Başvuru', basvuru))
    sart = ' · '.join(p for p in (' · '.join(v['duzeyler']), ' '.join((i.get('puan_turleri') or [])[:4]),
                                  f'{yas_sarti(i)} yaşını doldurmamış' if yas_sarti(i) else '') if p)
    if sart:
        kutular.append(('Şart', sart))
    o += kutu_yigini(kutular, y, 0.4)[0] if kutular else []
    sahneler.append(Sahne(2.8, o))
    # Kapanış: yorum çağrısı
    kucuk_ad = k._norm(ad)
    o = [_orta_yazi('Hangi şehirdesin?', [92, 80, 70], R.yazi, 560, 0.0),
         _orta_yazi('YORUMA YAZ', [140, 120, 100], R.vurgu, 680, 0.15),
         _orta_yazi('Yakınındaki alımları paylaşalım', [46, 40, 36], R.soluk, 880, 0.3)]
    if len(ilanlar) > n:
        o.append(_orta_yazi(f'+{len(ilanlar) - n} ilan daha sitede', [40, 36, 32], R.soluk, 1000, 0.4))
    o.append(Oge(kapanis_kutusu(f'Tüm {kucuk_ad} ilanları ve şartlar'), SOL, 1200, 0.5, 'buyu'))
    sahneler.append(Sahne(3.0, o, son=True))
    return sahneler


def meslek_sec(acik, simdi, gecmis=(), logo=lambda i: None):
    """(sahneler, anahtar, ilan kimlikleri) ya da uygun meslek yoksa None."""
    g = meslek_grubu_sec(acik, simdi, gecmis)
    if not g:
        return None
    sahneler = _meslek_sahneleri(g, simdi, logo)
    return (sahneler, g['anahtar'], [i['id'] for i, _ in g['ilanlar'][:MESLEK_SATIR_EN_COK * 2]]) if sahneler else None


def meslek_videosu(acik, simdi, logo=lambda i: None, gecmis=()):
    sonuc = meslek_sec(acik, simdi, gecmis, logo)
    return sonuc[0] if sonuc else None


# ---------------------------------------------------------------- c) düzey: lise / önlisans / lisans mezunlarına ilanlar (geri sayım)
DUZEY_SIRA = ('ortaogretim', 'onlisans', 'lisans')
DUZEY_ETIKET = {'ortaogretim': ('LİSE', 'Lise'), 'onlisans': ('ÖNLİSANS', 'Önlisans'), 'lisans': ('LİSANS', 'Lisans')}
DUZEY_EN_AZ_ILAN, DUZEY_GOSTER = 3, 6


def duzey_sec(acik, simdi):
    """(düzey, ilanlar [en büyükten küçüğe]) ya da None. Düzeyler günden güne döner; ilk uygun (>= 3 açık ilan) seçilir."""
    bas = simdi.toordinal() % 3
    for n in range(3):
        d = DUZEY_SIRA[(bas + n) % 3]
        uyan = [i for i in _kurumlu(acik) if d in (i.get('ogrenim') or [])]
        if len(uyan) >= DUZEY_EN_AZ_ILAN:
            uyan.sort(key=lambda i: (-(k.veri(i, None, simdi)['toplam'] or 0), i.get('id') or ''))
            return d, uyan[:DUZEY_GOSTER]
    return None


def duzey_videosu(acik, simdi, logo=lambda i: None, gecmis=()):
    sec = duzey_sec(acik, simdi)
    if not sec:
        return None
    duzey, ilanlar = sec
    etiket, ad = DUZEY_ETIKET[duzey]
    beyaz = ('#ffffff', '#cc1236') if R.ad == 'karmin' else (R.panel, R.yazi)
    b, y = bantlar([etiket, 'MEZUNLARI'], 140, SOL, 420, 0.0)
    s1 = b + [Oge(sigan_yazi('BUNLARA', [110, 96], GEN, 1, R.yazi), SOL, y + 30, 0.3, 'sol'),
              Oge(sigan_yazi('BAŞVURABİLİR', [110, 96, 84], GEN, 1, R.yazi), SOL, y + 160, 0.4, 'sol'),
              Oge(_hap_sigan(f'{len(ilanlar)} İLAN · {k.tr_buyuk(AYLAR[simdi.month - 1])} {simdi.year}', beyaz[0], beyaz[1], (48, 42, 36)), SOL, y + 340, 0.5, 'buyu')]
    sahneler = [Sahne(2.5, s1)]
    for n, i in enumerate(reversed(ilanlar)):
        sira = len(ilanlar) - n
        v = k.veri(i, None, simdi)
        o = [Oge(yazi(f'#{sira}', 300, R.yazi), SOL, 380, 0.0, 'buyu'),
             Oge(logo_rozeti(i, logo(i), 170), SAG - 170, 440, 0.05, 'buyu'),
             Oge(sigan_yazi(kisa_kurum(i), [76, 66, 58], GEN, 2, R.yazi), SOL, 760, 0.1, 'sol')]
        kutu = panel(GEN, 330, yaricap=40)
        d = ImageDraw.Draw(kutu)
        # 'Zabıta Memuru — Erkek (Spor)' ve 'Zabıta Memuru (Kadın)' tek ad olarak görünsün
        adlar = ', '.join(dict.fromkeys(re.sub(r'\s*(—|\().*$', '', x['ad']).strip() or x['ad'] for x in v['kadrolar']))
        if v['toplam']:
            d.text((44, 30), binlik(v['toplam']), font=F(150, True), fill=R.yazi)
            d.text((44 + round(d.textlength(binlik(v['toplam']), font=F(150, True))) + 28, 120), 'kadro', font=F(56, True), fill=R.soluk)
            if adlar:
                s, yz = k.sigdir(d, adlar, True, [50, 44, 38], GEN - 88, 1)
                d.text((44, 232), s[0], font=yz, fill=R.yazi)
        else:
            s, yz = k.sigdir(d, adlar or 'Personel alımı', True, [84, 70, 58], GEN - 88, 3)
            k.blok(d, 44, 40, s, yz, R.yazi, aralik=round(yz.size * 1.14))
        o.append(Oge(kutu, SOL, 1000, 0.2))
        if _bitis_yazi(i):
            o.append(Oge(_hap_sigan(f'SON GÜN {k.tr_buyuk(_bitis_yazi(i))}', beyaz[0], beyaz[1], (44, 38, 34)), SOL, 1370, 0.3, 'buyu'))
        sahneler.append(Sahne(1.5, o))
    o = [_orta_yazi('Lazım olur', [92, 80], R.yazi, 560, 0.0),
         _orta_yazi('KAYDET', [170, 150, 130], R.yazi, 680, 0.15),
         _orta_yazi(f'{ad} mezunu arkadaşına da gönder', [46, 40, 36], R.soluk, 910, 0.3),
         Oge(kapanis_kutusu('Şartların tamamı ve başvuru'), SOL, 1200, 0.5, 'buyu')]
    sahneler.append(Sahne(2.8, o, son=True))
    return sahneler


# ---------------------------------------------------------------- video
def video_suresi(sahneler):
    return sum(int(FPS * s.sure) for s in sahneler) / FPS


# Platformlar (Instagram, TikTok, YouTube) önizleme/kapak olarak videonun ilk karesini ya da ilk saniyesini alır.
# 11 Kasım 2026: ilk sahne boş zeminden açıldığı için her videonun kapağı boş çıkıyor, elle düzeltmek gerekiyordu.
# İlk sahne artık baştan yerine oturmuş başlar: ilk kare = kapak (kurum, kadro, son gün). Sonraki sahneler hareketli girer.
OTURMUS_KAYDIRMA = 60.0   # giriş hareketlerinin hepsinden uzun bir süre (sn)


def kareler(sahneler):
    taban = zemin()
    for no, sahne in enumerate(sahneler):
        adet = int(FPS * sahne.sure)
        for f in range(adet):
            im = taban.copy()
            sahne.ciz(im, f / FPS, oturmus=no == 0)
            ust_serit(im, no, len(sahneler), (f + 1) / adet)
            yield im


def kare(sahneler, saniye):
    """Verilen andaki tek kare (önizleme ve test için)."""
    t = saniye
    for no, sahne in enumerate(sahneler):
        if t < sahne.sure or no == len(sahneler) - 1:
            im = zemin()
            sahne.ciz(im, min(t, sahne.sure - 1 / FPS), oturmus=no == 0)
            ust_serit(im, no, len(sahneler), _sinirla(t / sahne.sure))
            return im
        t -= sahne.sure


# Biçim başına sabit parça ve başlangıç saniyesi (parçanın girişi atlanır, en dolu bölümünden başlar).
# Kaynak: mixkit.co, Mixkit Stock Music Free License (sosyal medya videosu ve ticari kullanım serbest, atıf gerekmez).
MUZIK = {'sabah': ('mixkit-158-happy-times.mp3', 47.5),      # Alejandro Magaña – Happy Times, ~118 BPM
         'ilan': ('mixkit-702-pop-09.mp3', 49.5),            # Grigoriy Nuzhny – Pop 09, ~96 BPM
         'aksam': ('mixkit-443-serene-view.mp3', 45.2)}      # Arulo – Serene View, ~78 BPM
# Yeni biçimler: kullanıcı kendi parçasını OZEL_MUZIK_KLASORU'ne koyana kadar eski parçalardan biri.
MUZIK.update({'kimler': MUZIK['ilan'], 'meslek': MUZIK['ilan'], 'duzey': MUZIK['sabah']})


MUZIK_ADRESI = 'https://assets.mixkit.co/music/{no}/{no}.mp3'
MUZIK_KLASORU = ROOT / 'sosyal' / 'muzik' / 'reels'   # git dışı önbellek: lisans tek başına dağıtıma izin vermez
OZEL_MUZIK_KLASORU = ROOT / 'sosyal' / 'muzik' / 'ozel'   # kullanıcının kendi parçaları (git'te izlenir): <tür>.mp3, baştan çalar


def muzik_yolu(tur, klasor=None, zaman_asimi=60):
    """Biçimin parçası ve başlangıç saniyesi. Dosya önbellekte yoksa Mixkit'ten indirilir; alınamazsa (None, 0.0) döner
    (çağıran eski parçalardan birine düşer, video sessiz kalmaz)."""
    import urllib.request
    ozel = OZEL_MUZIK_KLASORU / f'{tur}.mp3'
    if ozel.is_file() and ozel.stat().st_size > 50_000:
        return ozel, 0.0
    dosya, bas = MUZIK[tur]
    yol = Path(klasor or MUZIK_KLASORU) / dosya
    if yol.is_file() and yol.stat().st_size > 100_000:
        return yol, bas
    try:
        no = re.match(r'mixkit-(\d+)-', dosya).group(1)
        istek = urllib.request.Request(MUZIK_ADRESI.format(no=no), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
            veri = r.read()
        if len(veri) < 100_000 or not (veri[:3] == b'ID3' or veri[:1] == b'\xff'):
            raise ValueError('mp3 değil')
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(veri)
        return yol, bas
    except Exception as hata:
        print(f'Uyarı: {dosya} indirilemedi: {hata}')
        return None, 0.0


def video_yaz(sahneler, yol, muzik=None, ffmpeg=None, muzik_bas=0.0):
    """MP4 (H.264, yuv420p, 30 fps). muzik yoksa sessiz iz eklenir (platformlar ses izi bekler).
    muzik_bas: parçanın kaçıncı saniyesinden başlanacağı."""
    import sosyal_tasarim
    if ffmpeg is None:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    sure = video_suresi(sahneler)
    girdi, filtre = sosyal_tasarim.ses_girdisi(muzik, sure)
    if muzik and muzik_bas:
        girdi = ['-ss', f'{muzik_bas:.2f}', '-i', str(muzik)]   # döngü yok: seçilen bölüm videodan uzundur
    if muzik:   # üç biçim aynı ses düzeyinde çıksın (-14 LUFS: Reels/Shorts/TikTok hedefi); başta 0,3 sn açılır, sonda 1 sn kısılır
        filtre = ['-af', f'loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=0.3,afade=t=out:st={max(0.0, sure - 1):.2f}:d=1']
    p = subprocess.Popen([ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                          '-r', str(FPS), '-i', '-', *girdi, '-map', '0:v', '-map', '1:a', *filtre, '-t', f'{sure:.2f}',
                          '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                          '-movflags', '+faststart', str(yol)], stdin=subprocess.PIPE)
    try:
        for im in kareler(sahneler):
            p.stdin.write(im.tobytes())
    finally:
        p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError('ffmpeg video yazamadı')
    return sure


# ---------------------------------------------------------------- günlük yayın (sosyal_motor.uret çağırır)
OZET_EN_AZ = 2         # akşam özeti için o gün eklenmiş en az ilan
ILAN_GUNLUK = 3        # günde en çok tek ilan videosu (YouTube yükleme kotası: günde ~6 video; 2'si sabah ve akşam)
ILAN_TAZE_SAAT = 48    # tek ilan videosu için ilanın en çok kaç saat önce eklenmiş olabileceği


def _ayar(ad):
    """Ajanın sosyal/ayar.json'da değiştirebildiği sınırlı ayarlar (sosyal_ajan.AYAR_SINIR); yoksa varsayılan."""
    import sosyal_ajan
    return sosyal_ajan.ayar(ad)


def siradaki_ilan(acik, simdi, gecmis=()):
    """Videosu yapılacak sıradaki yeni ilan: son ILAN_TAZE_SAAT saatte eklenmiş, daha önce tek ilan videosu olmamış, en
    kalabalık alım önce. Günlük sınır dolduysa ya da aday yoksa None."""
    from sosyal_motor import _zaman
    tekler = [g for g in gecmis if g.get('tur') in ('ilan', 'kimler')]   # kimler: 23 Kasım 2026'dan sonraki tek ilan biçimi
    if sum(1 for g in tekler if (_zaman(g.get('zaman')) or simdi - timedelta(days=9)).astimezone(k.TR).date() == simdi.date()) >= _ayar('ilan_gunluk'):
        return None
    yapilan = {i for g in tekler for i in g.get('ilanlar') or []}
    adaylar = [i for i in acik if i.get('id') not in yapilan
               and (_zaman(i.get('ilk_gorulme')) or simdi - timedelta(days=9)) >= simdi - timedelta(hours=ILAN_TAZE_SAAT)]
    adaylar.sort(key=lambda i: (-(k.veri(i, None, simdi)['toplam'] or 0), i.get('id') or ''))
    return adaylar[0] if adaylar else None


def _satir(i, simdi):
    from site_uret import _bitis
    v = k.veri(i, None, simdi)
    b = _bitis(i)
    return f'• {kisa_kurum(i)}: {kisa_ne(v) or "alım"} (son gün {b.day} {AYLAR[b.month - 1]})'


def _eski_konu(vakit, acik, simdi, logo, gecmis):
    """Eski biçimler: sabah son gün, akşam özet, tek ilan."""
    if vakit == 'sabah':
        secim, toplam = son_gun_ilanlari(acik, simdi)
        if not secim:
            return None
        return {'tur': 'son_gun', 'muzik': 'sabah', 'anahtar': f'son_gun:{simdi.date()}:sabah', 'ilanlar': [i['id'] for i in secim],
                'baslik': f'Son Günü Yaklaşan {toplam} Kamu İlanı',
                'giris': f'⏰ Son başvurusu yaklaşan {toplam} kamu ilanı. En yakın tarih en üstte:',
                'satirlar': [_satir(i, simdi) for i in secim], 'etiketler': ['#songün', '#başvuru'],
                'sahneler': son_gun_videosu(secim, toplam, simdi, logo)}
    if vakit == 'aksam':
        secim = bugunun_ilanlari(acik, simdi)
        if len(secim) < _ayar('ozet_en_az'):   # tek ilanlık gün zaten tek ilan videosuyla paylaşılır
            return None
        return {'tur': 'ozet', 'muzik': 'aksam', 'anahtar': f'ozet:{simdi.date()}', 'ilanlar': [i['id'] for i in secim],
                'baslik': f'Bugün {len(secim)} Yeni Kamu İlanı',
                'giris': f'📢 Bugün {len(secim)} yeni kamu ilanı yayımlandı. Son başvuru tarihleriyle:',
                'satirlar': [_satir(i, simdi) for i in secim], 'etiketler': ['#yeniilan', '#işilanı'],
                'sahneler': ozet_videosu(secim, simdi, logo)}
    ilan = siradaki_ilan(acik, simdi, gecmis)
    if ilan is None:
        return None
    v = k.veri(ilan, None, simdi)
    sayi, alt = ne_alinacak(v)
    ne = f'{binlik(sayi)} kişi alacak' if sayi else f'{alt} alacak'
    return {'tur': 'ilan', 'muzik': 'ilan', 'anahtar': f'ilan:{ilan["id"]}', 'ilanlar': [ilan['id']],
            'baslik': f'{kisa_kurum(ilan)} {ne}',
            'giris': f'📢 {kisa_kurum(ilan)} {ne}.' + (f' Son başvuru: {v["tarih"]}.' if v['tarih'] else ''),
            'satirlar': ['• ' + (f'{binlik(a)} ' if a else '') + ad for a, ad in kadro_satirlari(v, 6)],
            'etiketler': ['#yeniilan', '#işilanı'], 'sahneler': ilan_videosu(ilan, simdi, logo(ilan))}


def _etiket(ad):
    return '#' + ''.join(_ascii(ad).split())


def _yeni_konu(vakit, acik, simdi, logo, gecmis):
    """23 Kasım 2026'dan sonraki biçimler; uygun içerik yoksa None (çağıran eski biçime düşer)."""
    yil = simdi.year
    if vakit == 'ilan':
        ilan = siradaki_ilan(acik, simdi, gecmis)
        if ilan is None:
            return None
        sahneler = kimler_videosu(ilan, simdi, logo(ilan))
        if not sahneler:
            return None
        v = k.veri(ilan, None, simdi)
        sayi, alt = ne_alinacak(v)
        ad = _baslik_kadro(v) or 'Personel'
        if len(ad) > 40:   # YouTube başlığı 100 karakterde kesilir; 'Kimler Başvurabilir?' görünsün
            ad = 'Personel'
        ne = f'{binlik(sayi)} kişi alacak' if sayi else f'{alt} alacak'
        return {'tur': 'kimler', 'muzik': 'kimler', 'anahtar': f'ilan:{ilan["id"]}', 'ilanlar': [ilan['id']],
                'baslik': f'{kisa_kurum(ilan)} {binlik(sayi) + " " if sayi else ""}{ad} Alımı {yil}: Kimler Başvurabilir?',
                'giris': f'📢 {kisa_kurum(ilan)} {ne}. Kimler başvurabilir, şartlar ve son başvuru tarihi:',
                'satirlar': [_satir(ilan, simdi)], 'etiketler': ['#kamuilanı', '#kpss', '#kimlerbaşvurabilir'], 'sahneler': sahneler}
    if vakit == 'aksam':
        g = meslek_grubu_sec(acik, simdi, gecmis)
        sahneler = _meslek_sahneleri(g, simdi, logo) if g else None
        if not sahneler:
            return None
        goster = [i for i, _ in g['ilanlar'][:MESLEK_SATIR_EN_COK * 2]]
        return {'tur': 'meslek', 'muzik': 'meslek', 'anahtar': f'meslek:{g["anahtar"]}', 'ilanlar': [i['id'] for i in goster],
                'baslik': f'{yil} {g["ad"]} Alımları: {binlik(g["toplam"])} Kadro',
                'giris': f'📢 Şu an açık {len(g["ilanlar"])} ilanda toplam {binlik(g["toplam"])} {k._norm(g["ad"])} kadrosu var:',
                'satirlar': [_satir(i, simdi) for i in goster], 'etiketler': ['#kamuilanı', '#kpss', _etiket(g['anahtar'])],
                'sahneler': sahneler}
    if vakit == 'sabah':
        sec = duzey_sec(acik, simdi)
        sahneler = duzey_videosu(acik, simdi, logo, gecmis) if sec else None
        if not sahneler:
            return None
        duzey, ilanlar = sec
        etiket = DUZEY_ETIKET[duzey][1]
        return {'tur': 'duzey', 'muzik': 'duzey', 'anahtar': f'duzey:{duzey}:{simdi.date()}', 'ilanlar': [i['id'] for i in ilanlar],
                'baslik': f'{etiket} Mezunlarının Başvurabileceği Kamu İlanları ({AYLAR[simdi.month - 1]} {yil})',
                'giris': f'🎓 {etiket} mezunlarının başvurabileceği, kadro sayısı en yüksek {len(ilanlar)} kamu ilanı:',
                'satirlar': [_satir(i, simdi) for i in ilanlar], 'etiketler': ['#kamuilanı', '#kpss', f'#{duzey}'], 'sahneler': sahneler}
    return None


def gunluk(vakit, acik, simdi, logo=lambda i: None, gecmis=()):
    """Vaktin sabit biçimi için konu: sahneler + açıklama metninin parçaları. İçerik yoksa None.
    vakit: 'sabah' (son günü yaklaşanlar), 'aksam' (bugünün özeti), 'ilan' (sıradaki yeni ilan).
    YENI_BICIM_TARIHI'nden sonra: ilan -> kimler, aksam -> meslek, sabah -> duzey; yeni biçim kurulamazsa eskisine düşer."""
    yeni = bicim_paleti(vakit, simdi)
    if yeni:
        palet_sec(yeni)   # sahne katmanları kurulurken çizilir
        try:
            konu = _yeni_konu(vakit, acik, simdi, logo, gecmis)
        except Exception as hata:   # beklenmedik veri yeni biçimi bozarsa eski şablon yine çıksın
            print(f'::warning::Yeni biçim kurulamadı ({vakit}): {hata}')
            konu = None
        if konu:
            return konu
        palet_sec(siradaki_palet(gecmis))   # eski biçim eski paletiyle çıksın
    konu = _eski_konu(vakit, acik, simdi, logo, gecmis)
    if konu and yeni:
        konu['palet'] = R.ad   # sosyal_motor kayda bu paleti yazar
    return konu


def sahne_kareleri(sahneler):
    """Her sahnenin oturmuş hâli (önizleme sürümü ve kapak için)."""
    an, sonuc = 0.0, []
    for s in sahneler:
        sonuc.append(kare(sahneler, an + s.sure - CIKIS - 0.05))
        an += s.sure
    return sonuc


def uret(tur, cikti, simdi=None, ilan_id=None, muzik=None, docs=None, logo=None):
    """tur: 'sabah' | 'aksam' | 'ilan' | 'kimler' | 'meslek' | 'duzey'. Video ve kapak karesini yazar; içerik yoksa None döner."""
    import sosyal_motor as sm
    simdi = (simdi or datetime.now(k.TR)).astimezone(k.TR)
    ilanlar = sm.ilanlari_yukle(docs or sm.ROOT / 'docs')
    acik = sm.acik_ilanlar(ilanlar, simdi)
    if logo is None:
        from kurum_gorseli import kurum_logosu as logo
    if tur == 'sabah':
        secim, toplam = son_gun_ilanlari(acik, simdi)
        sahneler, kimlikler = son_gun_videosu(secim, toplam, simdi, logo), [i['id'] for i in secim]
    elif tur == 'aksam':
        secim = bugunun_ilanlari(acik, simdi)
        sahneler, kimlikler = ozet_videosu(secim, simdi, logo), [i['id'] for i in secim]
    elif tur == 'meslek':
        sonuc = meslek_sec(acik, simdi, (), logo)
        sahneler, kimlikler = (sonuc[0], sonuc[2]) if sonuc else (None, [])
    elif tur == 'duzey':
        sec = duzey_sec(acik, simdi)
        sahneler, kimlikler = duzey_videosu(acik, simdi, logo), [i['id'] for i in sec[1]] if sec else []
    else:
        if ilan_id:
            ilan = next((i for i in acik if i.get('id') == ilan_id), None)
        elif tur == 'kimler':   # --id verilmezse en kalabalık alım
            ilan = max(acik, key=lambda i: (k.veri(i, None, simdi)['toplam'] or 0), default=None)
        else:
            ilan = acik[-1] if acik else None
        if ilan is None:
            print('İlan bulunamadı ya da başvurusu açık değil.')
            return None
        sahneler = (kimler_videosu if tur == 'kimler' else ilan_videosu)(ilan, simdi, logo(ilan))
        kimlikler = [ilan['id']]
    if not sahneler:
        print('Bu biçim için bugün içerik yok.')
        return None
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    sure = video_yaz(sahneler, cikti / f'{tur}.mp4', muzik)
    kare(sahneler, sahneler[0].sure - CIKIS - 0.05).save(cikti / f'{tur}-kapak.png', optimize=True)
    ozet = {'tur': tur, 'zaman': simdi.isoformat(timespec='seconds'), 'sure': sure, 'sahne': len(sahneler), 'ilanlar': kimlikler,
            'muzik': Path(muzik).name if muzik else None}
    (cikti / f'{tur}.json').write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{tur}: {len(sahneler)} sahne, {sure:.1f} sn, {len(kimlikler)} ilan')
    return ozet


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('tur', choices=('sabah', 'aksam', 'ilan', 'kimler', 'meslek', 'duzey'))
    a.add_argument('--id')
    a.add_argument('--cikti', default='reels-cikti')
    a.add_argument('--muzik')
    a.add_argument('--palet', choices=sorted(PALETLER))
    s = a.parse_args()
    palet_sec(s.palet or {'kimler': 'sari', 'meslek': 'indigo', 'duzey': 'karmin'}.get(s.tur, PALET))
    uret(s.tur, s.cikti, ilan_id=s.id, muzik=s.muzik)
