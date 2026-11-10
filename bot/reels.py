"""Hareketli dikey video (1080x1920) şablonları: sabah son gün, tek ilan, akşam özeti.

Üç biçim de aynı sahne motorunu kullanır; bot her gün aynı düzeni üretir, yalnız veri değişir:
  sabah  -> son_gun_videosu : son başvurusu 0–3 gün içinde biten ilanlar, en yakın tarih önce
  ilan   -> ilan_videosu    : tek ilan (kurum, kaç kişi, kadrolar, kimler başvurabilir, son başvuru)
  aksam  -> ozet_videosu    : bugün eklenen ilanların özeti

Her sahne öğeleri sırayla girer (kayarak / büyüyerek), sahne sonunda birlikte çıkar. Üstte hikâye çubuğu sahne
ilerleyişini gösterir. Renkler ilan kartlarıyla aynıdır (petrol + lime). Metin yalnız ilan verisinden gelir; tahmin yok.

Kullanım: python bot/reels.py sabah|aksam|ilan [--id İLAN_KİMLİĞİ] [--cikti klasör] [--muzik dosya]"""
import argparse
import io
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

import kart_tasarimlari as k
from kart_tasarimlari import F, AYLAR, PETROL, ANA, LIME, KIRMIZI, TURUNCU

VW, VH, FPS = 1080, 1920, 30
SOL, SAG = 72, 1008                 # yatay güvenli alan
UST, ALT = 300, 1540                # Reels/TikTok arayüzünün örtmediği dikey alan
KOYU, BEYAZ, SOLUK = '#0b2227', '#ffffff', '#b6cbcc'
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

    def __init__(self, hedef, x, y, boy, renk=LIME, bas=0.1, sure=0.9, hiza='lt'):
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

    def ciz(self, im, t):
        cikis = 0.0 if self.son else yumusak((t - (self.sure - CIKIS)) / CIKIS)
        for o in self.ogeler:
            o.ciz(im, t, cikis)


# ---------------------------------------------------------------- katman üreticileri
def binlik(n):
    return f'{int(n):,}'.replace(',', '.')


def yazi(metin, boy, renk=BEYAZ, kalin=True, genislik=None, satir=1, aralik=1.14, hiza='l'):
    """Metin katmanı; genislik verilirse en çok `satir` satıra kaydırılır (sığmayan … ile kesilir)."""
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


def sigan_yazi(metin, boyutlar, genislik, satir, renk=BEYAZ):
    """Verilen boyutlardan satır sınırına sığan en büyüğüyle metin katmanı."""
    satirlar, yz = k.sigdir(_OLC, str(metin), True, boyutlar, genislik, satir)
    return yazi(' '.join(satirlar) if len(satirlar) == 1 else metin, yz.size, renk, genislik=genislik, satir=satir)


def hap(metin, dolgu=LIME, renk=PETROL, boy=40, yuk=None, cizgi=None):
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


def panel(w, h, dolgu=ANA, yaricap=36, cizgi=None):
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
        d.ellipse((0, 0, cap * kat - 1, cap * kat - 1), fill=BEYAZ)
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
        with Image.open(io.BytesIO(k.bas_harf_amblemi(ilan.get('kurum') or '', cap * kat))) as a:
            im.alpha_composite(a.convert('RGBA'))
    return im.resize((cap, cap), Image.Resampling.LANCZOS)


def kalan_hapi(v, boy=44):
    """Aciliyet rengi: bugün/yarın kırmızı, 2–6 gün turuncu, sonrası lime."""
    metin = k.tr_buyuk(v['kalan_yazi'] or '')
    if not metin:
        return None
    if v['kalan'] is not None and v['kalan'] <= 1:
        return hap(metin, KIRMIZI, BEYAZ, boy)
    if v['kalan'] is not None and v['kalan'] <= 6:
        return hap(metin, TURUNCU, PETROL, boy)
    return hap(metin, LIME, PETROL, boy)


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
    im = Image.merge('RGB', [im.point(lambda p, a=a, b=b: round(a + (b - a) * p / 255)) for a, b in zip((16, 46, 53), (9, 28, 33))])
    d = ImageDraw.Draw(im)
    for n in range(3):
        d.line((VW - 260 + n * 70, 0, VW, 260 - n * 70), fill=(31, 74, 70), width=3)
    return im


def ust_serit(im, sahne_no, sahne_sayisi, oran):
    """Hikâye çubuğu (her sahneye bir parça) ve marka satırı."""
    d = ImageDraw.Draw(im)
    bosluk, y = 10, 204
    w = (SAG - SOL - bosluk * (sahne_sayisi - 1)) / sahne_sayisi
    for n in range(sahne_sayisi):
        x = SOL + n * (w + bosluk)
        d.rounded_rectangle((x, y, x + w, y + 8), radius=4, fill=(52, 92, 90))
        dolu = 1.0 if n < sahne_no else oran if n == sahne_no else 0.0
        if dolu > 0:
            d.rounded_rectangle((x, y, x + max(8, w * dolu), y + 8), radius=4, fill=LIME)
    logo = k.logo_kare(56)
    if logo is not None:
        im.paste(logo, (SOL, 232), logo)
    d.text((SOL + 72, 260), 'KPSS Tercihi', font=F(34, True), fill=BEYAZ, anchor='lm')


def kapanis_sahnesi(ust_satir, sure=3.0):
    """Son sahne: adres ve Telegram; sahne çıkışı yoktur (video bu karede biter)."""
    o = [Oge(yazi(ust_satir, 52, SOLUK, genislik=SAG - SOL, satir=2, hiza='m'), SOL, 560, 0.0),
         Oge(yazi('TÜM İLANLAR', 104, BEYAZ, genislik=SAG - SOL, hiza='m'), SOL, 720, 0.12),
         Oge(yazi('TEK YERDE', 104, LIME, genislik=SAG - SOL, hiza='m'), SOL, 840, 0.22)]
    adres = panel(SAG - SOL, 150, LIME, 44)
    ImageDraw.Draw(adres).text((adres.width / 2, 76), 'kpsstercihi.com', font=F(72, True), fill=PETROL, anchor='mm')
    o.append(Oge(adres, SOL, 1040, 0.45, 'buyu'))
    tg = hap('Telegram: @kpsstercihi', ANA, BEYAZ, 44, cizgi=LIME)
    o.append(Oge(tg, (VW - tg.width) / 2, 1240, 0.7))
    o.append(Oge(yazi('Kaydet, son güne kalmasın', 44, SOLUK, genislik=SAG - SOL, hiza='m'), SOL, 1400, 0.95))
    return Sahne(sure, o, son=True)


def ilan_kutusu(ilan, logo, simdi, y, bas, sira=None):
    """Sabah videosundaki tek ilan sahnesinin öğeleri (kalan gün rozeti, kurum, kaç kişi, koşullar, son başvuru)."""
    v = k.veri(ilan, logo, simdi)
    o = []
    if sira:
        o.append(Oge(hap(sira, ANA, SOLUK, 34, cizgi=(52, 92, 90)), SOL, y, bas))
    rozet = kalan_hapi(v, 48)
    if rozet:
        o.append(Oge(rozet, SAG - rozet.width, y - 8, bas + 0.05, 'buyu'))
    y += 130
    o.append(Oge(logo_rozeti(ilan, logo, 190), SOL, y, bas + 0.1, 'buyu'))
    ad = sigan_yazi(kisa_kurum(ilan), [62, 54, 48], SAG - SOL - 230, 3)
    o.append(Oge(ad, SOL + 230, y + max(0, (190 - ad.height) // 2), bas + 0.18, 'sol'))
    y += 250
    sayi, alt = ne_alinacak(v)
    kutu = panel(SAG - SOL, 330, ANA, 44)
    o.append(Oge(kutu, SOL, y, bas + 0.28))
    if sayi:
        o.append(Sayac(sayi, SOL + 48, y + 28, 170, LIME, bas + 0.34, 0.7))
        o.append(Oge(yazi(alt, 50, BEYAZ), SOL + 52, y + 232, bas + 0.4))
    else:
        o.append(Oge(sigan_yazi(alt, [84, 70, 58], SAG - SOL - 100, 3, LIME), SOL + 48, y + 40, bas + 0.34))
    y += 370
    adlar = ', '.join(a for _, a in kadro_satirlari(v, 4))
    if sayi and adlar:
        o.append(Oge(yazi(adlar, 44, BEYAZ, genislik=SAG - SOL, satir=2), SOL, y, bas + 0.5))
        y += 130
    kosul = ' · '.join(p for p in (' · '.join(v['duzeyler']), v['kpss']) if p)
    if kosul:
        o.append(Oge(yazi(kosul, 40, SOLUK, False, genislik=SAG - SOL, satir=2), SOL, y, bas + 0.6))
        y += 120
    if v['tarih']:
        o.append(Oge(yazi('Son başvuru: ' + v['tarih'], 44, LIME, genislik=SAG - SOL, satir=1), SOL, min(y + 10, ALT - 70), bas + 0.7))
    return o


# ---------------------------------------------------------------- 1) sabah: son günü yaklaşan ilanlar
def son_gun_ilanlari(acik, simdi, en_cok=SON_GUN_EN_COK):
    """Son başvurusu bugün ile SON_GUN_UFUK gün sonrası arasında olanlar; en yakın tarih, sonra en kalabalık alım önce."""
    from site_uret import _bitis
    secim = [i for i in acik if 0 <= (_bitis(i).date() - simdi.date()).days <= SON_GUN_UFUK]
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
    giris = [Oge(hap(gun_yazi(simdi), ANA, BEYAZ, 40, cizgi=LIME), SOL, 420, 0.0, 'buyu'),
             Oge(yazi('SON GÜNÜ', 132, BEYAZ), SOL, 560, 0.1, 'sol'),
             Oge(yazi('YAKLAŞAN', 132, BEYAZ), SOL, 710, 0.2, 'sol'),
             Sayac(toplam, SOL, 880, 300, LIME, 0.3, 0.7),
             Oge(yazi('İLAN', 132, LIME), SOL + round(_OLC.textlength(binlik(toplam), font=F(300, True))) + 36, 1030, 0.5, 'sol'),
             Oge(yazi(ozet[0].upper() + ozet[1:] if ozet else '', 46, SOLUK, genislik=SAG - SOL, satir=2), SOL, 1290, 0.75)]
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
    o = [Oge(hap('YENİ İLAN', LIME, PETROL, 46), SOL, 400, 0.0, 'buyu'),
         Oge(logo_rozeti(ilan, logo, 230), SOL, 540, 0.1, 'buyu')]
    ad = sigan_yazi(kisa_kurum(ilan), [68, 60, 52], SAG - SOL, 3)
    o.append(Oge(ad, SOL, 810, 0.2, 'sol'))
    y = 810 + ad.height + 30
    if sayi:
        o += [Sayac(sayi, SOL, y, 320, LIME, 0.35, 0.8), Oge(yazi(alt, 76, BEYAZ), SOL, y + 400, 0.55)]
    else:
        o.append(Oge(sigan_yazi(alt, [120, 100, 84, 70], SAG - SOL, 3, LIME), SOL, y + 20, 0.35))
    sahneler = [Sahne(2.6, o)]
    # Sahne 2: kadrolar
    satirlar = kadro_satirlari(v, 5)
    if satirlar:
        o = [Oge(yazi('HANGİ KADROLAR?', 60, LIME), SOL, 400, 0.0, 'sol')]
        for n, (adet, kad) in enumerate(satirlar):
            kutu = panel(SAG - SOL, 170, ANA, 36)
            d = ImageDraw.Draw(kutu)
            x = 44
            if adet:
                d.text((x, 85), binlik(adet), font=F(76, True), fill=LIME, anchor='lm')
                x += round(d.textlength(binlik(adet), font=F(76, True))) + 32
            s, yz = k.sigdir(d, kad, True, [50, 44, 38], kutu.width - x - 40, 2)
            for m, satir in enumerate(s):
                d.text((x, 85 + (m - (len(s) - 1) / 2) * yz.size * 1.15), satir, font=yz, fill=BEYAZ if adet is not None or len(satirlar) == 1 else SOLUK, anchor='lm')
            o.append(Oge(kutu, SOL, 520 + n * 194, 0.15 + n * 0.16))
        sahneler.append(Sahne(1.6 + 0.45 * len(satirlar), o))
    # Sahne 3: kimler başvurabilir
    kosullar = kosul_satirlari(v)
    if kosullar:
        o = [Oge(yazi('KİMLER', 96, BEYAZ), SOL, 400, 0.0, 'sol'), Oge(yazi('BAŞVURABİLİR?', 96, LIME), SOL, 510, 0.1, 'sol')]
        for n, (etiket, deger) in enumerate(kosullar):
            kutu = panel(SAG - SOL, 220, ANA, 36)
            d = ImageDraw.Draw(kutu)
            d.text((44, 34), k.tr_buyuk(etiket), font=F(34, True), fill=SOLUK)
            s, yz = k.sigdir(d, deger, True, [60, 52, 44, 38], kutu.width - 88, 2)
            k.blok(d, 44, 92 if len(s) == 1 else 82, s, yz, BEYAZ, aralik=round(yz.size * 1.12))
            o.append(Oge(kutu, SOL, 700 + n * 248, 0.3 + n * 0.2))
        sahneler.append(Sahne(2.9, o))
    # Sahne 4: son başvuru + adres (video burada biter)
    o = [Oge(yazi('SON BAŞVURU', 60, LIME), SOL, 400, 0.0, 'sol')]
    y = 520
    bitis, saatli = k._bitis(ilan)
    if bitis:
        o.append(Oge(yazi(f'{bitis.day} {AYLAR[bitis.month - 1]}', 190, BEYAZ), SOL, y, 0.12))
        o.append(Oge(yazi(GUNLER[bitis.weekday()] + (f' · {bitis:%H:%M}' if saatli else ''), 56, SOLUK), SOL, y + 240, 0.24))
        rozet = kalan_hapi(v, 56)
        if rozet:
            o.append(Oge(rozet, SOL, y + 360, 0.4, 'buyu'))
        y += 520
    kutu = panel(SAG - SOL, 300, LIME, 44)
    d = ImageDraw.Draw(kutu)
    d.text((48, 44), 'Şartların tamamı ve başvuru bağlantısı', font=F(38, True), fill=PETROL)
    d.text((48, 108), 'kpsstercihi.com', font=F(84, True), fill=PETROL)
    d.text((48, 226), 'Telegram: @kpsstercihi', font=F(38, True), fill=ANA)
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
    kutu = panel(SAG - SOL, 300, ANA, 40)
    kutu.alpha_composite(logo_rozeti(ilan, logo, 150), (36, 36))
    d = ImageDraw.Draw(kutu)
    s, yz = k.sigdir(d, kisa_kurum(ilan), True, [46, 40, 36], kutu.width - 240, 2)
    k.blok(d, 216, 40 if len(s) > 1 else 66, s, yz, BEYAZ, aralik=round(yz.size * 1.12))
    ne = k.lines(d, kisa_ne(v), F(42, True), kutu.width - 72, 1)[0]
    d.text((36, 212), ne, font=F(42, True), fill=LIME)
    bitis, _ = k._bitis(ilan)
    if bitis:
        d.text((216, 150 if len(s) > 1 else 136), f'Son başvuru {bitis.day} {AYLAR[bitis.month - 1]}', font=F(34), fill=SOLUK)
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
    o = [Oge(hap(gun_yazi(simdi), ANA, BEYAZ, 40, cizgi=LIME), SOL, 420, 0.0, 'buyu'),
         Oge(yazi('BUGÜN', 132, BEYAZ), SOL, 560, 0.1, 'sol'),
         Sayac(n, SOL, 720, 300, LIME, 0.25, 0.7),
         Oge(yazi('YENİ', 110, LIME), SOL + round(_OLC.textlength(binlik(n), font=F(300, True))) + 36, 790, 0.4, 'sol'),
         Oge(yazi('İLAN', 110, LIME), SOL + round(_OLC.textlength(binlik(n), font=F(300, True))) + 36, 910, 0.48, 'sol')]
    x = SOL
    for m, (deger, etiket) in enumerate(((kadro, 'kadro'), (kurum, 'kurum'))):
        if deger:
            kutu = panel(450, 230, ANA, 40)
            d = ImageDraw.Draw(kutu)
            d.text((40, 30), binlik(deger), font=F(104, True), fill=BEYAZ)
            d.text((40, 160), etiket, font=F(40, True), fill=SOLUK)
            o.append(Oge(kutu, x, 1170, 0.7 + m * 0.14))
            x += 486
    sahneler = [Sahne(2.8, o)]
    gosterilen = ilanlar[:OZET_SATIR * OZET_SAHNE]
    s = 0
    for boy in parcala(len(gosterilen)):
        parca = gosterilen[s:s + boy]
        o = [Oge(yazi('BUGÜN AÇILANLAR', 56, LIME), SOL, 400, 0.0, 'sol'),
             Oge(hap(f'{s + 1}–{s + len(parca)} / {n}', ANA, SOLUK, 34, cizgi=(52, 92, 90)), SAG - 230, 400, 0.0)]
        for m, i in enumerate(parca):
            o.append(Oge(ozet_satiri(i, logo(i), simdi), SOL, 520 + m * 330, 0.15 + m * 0.22))
        sahneler.append(Sahne(1.9 + 0.7 * len(parca), o))
        s += boy
    fazla = n - len(gosterilen)
    sahneler.append(kapanis_sahnesi(f'+{fazla} ilan daha sitede' if fazla > 0 else 'Son başvuru tarihleriyle hepsi'))
    return sahneler


# ---------------------------------------------------------------- video
def video_suresi(sahneler):
    return sum(int(FPS * s.sure) for s in sahneler) / FPS


def kareler(sahneler):
    taban = zemin()
    for no, sahne in enumerate(sahneler):
        adet = int(FPS * sahne.sure)
        for f in range(adet):
            im = taban.copy()
            sahne.ciz(im, f / FPS)
            ust_serit(im, no, len(sahneler), (f + 1) / adet)
            yield im


def kare(sahneler, saniye):
    """Verilen andaki tek kare (önizleme ve test için)."""
    t = saniye
    for no, sahne in enumerate(sahneler):
        if t < sahne.sure or no == len(sahneler) - 1:
            im = zemin()
            sahne.ciz(im, min(t, sahne.sure - 1 / FPS))
            ust_serit(im, no, len(sahneler), _sinirla(t / sahne.sure))
            return im
        t -= sahne.sure


# Biçim başına sabit parça ve başlangıç saniyesi (parçanın girişi atlanır, en dolu bölümünden başlar).
# Kaynak: mixkit.co, Mixkit Stock Music Free License (sosyal medya videosu ve ticari kullanım serbest, atıf gerekmez).
MUZIK = {'sabah': ('mixkit-158-happy-times.mp3', 47.5),      # Alejandro Magaña – Happy Times, ~118 BPM
         'ilan': ('mixkit-702-pop-09.mp3', 49.5),            # Grigoriy Nuzhny – Pop 09, ~96 BPM
         'aksam': ('mixkit-443-serene-view.mp3', 45.2)}      # Arulo – Serene View, ~78 BPM


MUZIK_ADRESI = 'https://assets.mixkit.co/music/{no}/{no}.mp3'
MUZIK_KLASORU = Path(__file__).resolve().parents[1] / 'sosyal' / 'muzik' / 'reels'   # git dışı önbellek: lisans tek başına dağıtıma izin vermez


def muzik_yolu(tur, klasor=None, zaman_asimi=60):
    """Biçimin parçası ve başlangıç saniyesi. Dosya önbellekte yoksa Mixkit'ten indirilir; alınamazsa (None, 0.0) döner
    (çağıran eski parçalardan birine düşer, video sessiz kalmaz)."""
    import re
    import urllib.request
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


def siradaki_ilan(acik, simdi, gecmis=()):
    """Videosu yapılacak sıradaki yeni ilan: son ILAN_TAZE_SAAT saatte eklenmiş, daha önce tek ilan videosu olmamış, en
    kalabalık alım önce. Günlük sınır dolduysa ya da aday yoksa None."""
    from sosyal_motor import _zaman
    tekler = [g for g in gecmis if g.get('tur') == 'ilan']
    if sum(1 for g in tekler if (_zaman(g.get('zaman')) or simdi - timedelta(days=9)).astimezone(k.TR).date() == simdi.date()) >= ILAN_GUNLUK:
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


def gunluk(vakit, acik, simdi, logo=lambda i: None, gecmis=()):
    """Vaktin sabit biçimi için konu: sahneler + açıklama metninin parçaları. İçerik yoksa None.
    vakit: 'sabah' (son günü yaklaşanlar), 'aksam' (bugünün özeti), 'ilan' (sıradaki yeni ilan)."""
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
        if len(secim) < OZET_EN_AZ:   # tek ilanlık gün zaten tek ilan videosuyla paylaşılır
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


def sahne_kareleri(sahneler):
    """Her sahnenin oturmuş hâli (önizleme sürümü ve kapak için)."""
    an, sonuc = 0.0, []
    for s in sahneler:
        sonuc.append(kare(sahneler, an + s.sure - CIKIS - 0.05))
        an += s.sure
    return sonuc


def uret(tur, cikti, simdi=None, ilan_id=None, muzik=None, docs=None, logo=None):
    """tur: 'sabah' | 'aksam' | 'ilan'. Video ve kapak karesini yazar; içerik yoksa None döner."""
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
    else:
        ilan = next((i for i in acik if i.get('id') == ilan_id), None) if ilan_id else (acik[-1] if acik else None)
        if ilan is None:
            print('İlan bulunamadı ya da başvurusu açık değil.')
            return None
        sahneler, kimlikler = ilan_videosu(ilan, simdi, logo(ilan)), [ilan['id']]
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
    a.add_argument('tur', choices=('sabah', 'aksam', 'ilan'))
    a.add_argument('--id')
    a.add_argument('--cikti', default='reels-cikti')
    a.add_argument('--muzik')
    s = a.parse_args()
    uret(s.tur, s.cikti, ilan_id=s.id, muzik=s.muzik)
