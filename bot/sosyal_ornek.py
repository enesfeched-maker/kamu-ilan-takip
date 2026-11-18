"""Onay örnekleri (yayına bağlı DEĞİL): Instagram hikâye seti (1080x1920, PNG kareler + ≤15 sn MP4) ve karusel
(1080x1350, PNG slaytlar). Üç içerik türü, reels.py'nin onaylı görünümüyle (Kâğıt/Bordo, logo rozeti, hap, panel):

  kadro-raporu   Haftanın kadro raporu: son 7 günün yeni ilanları, toplam kadro, ilk 5 kurum, öğrenim düzeyi, iller
  son-gun        Son günü yaklaşanlar: son başvurusu 7 gün içinde biten ilanlar, güne göre
  puan-bandi     Bu puanla nereye?: ÖSYM son dönem taban puanlarında bir puan aralığındaki yerleşmeler

Sayıların hepsi docs/ilanlar.json ve docs/puanlar/*.json'dan; tahmin yok.

Kullanım: python bot/sosyal_ornek.py --cikti KLASÖR [--tur kadro-raporu|son-gun|puan-bandi] [--duzey lisans --alt 70 --ust 75]"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

import haftalik as h
import kart_tasarimlari as k
import reels
from kart_tasarimlari import AYLAR, F
from reels import ALT, SAG, SOL, Oge, Sahne, Sayac, binlik, hap, logo_rozeti, panel, yazi

KW, KH = 1080, 1350          # karusel slaytı (4:5)
HIKAYE_EN_UZUN = 15.0         # Instagram hikâyesinde tek video en çok 15 sn
ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- karusel altyapısı
def karusel_zemin():
    """reels.zemin ile aynı geçiş ve sağ üst köşe çizgileri, 1080x1350."""
    R = reels.R
    im = Image.linear_gradient('L').resize((KW, KH))
    im = Image.merge('RGB', [im.point(lambda p, a=a, b=b: round(a + (b - a) * p / 255)) for a, b in zip(R.zemin_ust, R.zemin_alt)])
    d = ImageDraw.Draw(im)
    for n in range(3):
        d.line((KW - 260 + n * 70, 0, KW, 260 - n * 70), fill=R.cizgi2, width=3)
    return im.convert('RGBA')


def slayt(ogeler, no, toplam):
    """ogeler: [(katman, x, y)]. Üstte marka satırı ve sayfa göstergesi."""
    R = reels.R
    im = karusel_zemin()
    d = ImageDraw.Draw(im)
    logo = k.logo_kare(56)
    if logo is not None:
        im.paste(logo, (SOL, 64), logo)
    d.text((SOL + 72, 92), 'KPSS Tercihi', font=F(34, True), fill=R.yazi, anchor='lm')
    d.text((SAG, 92), f'{no}/{toplam}', font=F(32, True), fill=R.soluk, anchor='rm')
    for kat, x, y in ogeler:
        im.alpha_composite(kat, (round(x), round(y)))
    return im.convert('RGB')


def baslik_katmanlari(satirlar, y, boyutlar=(112, 100, 88), son_vurgu=True):
    """İri başlık satırları; (katmanlar, sonraki y)."""
    R = reels.R
    o = []
    for n, s in enumerate(satirlar):
        renk = R.vurgu if son_vurgu and n == len(satirlar) - 1 else R.yazi
        kat = reels.sigan_yazi(s, list(boyutlar), SAG - SOL, 1, renk)
        o.append((kat, SOL, y))
        y += kat.height + 2
    return o, y


def iri_sayi(sayi, etiket, y, boy=230, metin=None):
    R = reels.R
    m = metin or binlik(sayi)
    sayi_kat = yazi(m, boy, R.vurgu)
    gen = round(reels._OLC.textlength(m, font=F(boy, True)))
    return [(sayi_kat, SOL, y), (yazi(etiket, round(boy * 0.3), R.yazi), SOL + gen + 28, y + round(boy * 0.62))]


def ileri_hapi(metin, y):
    """Kapakta sağ alt: kaydırmaya çağıran sıcak bir söz + ok."""
    R = reels.R
    boy, yuk = 38, 72
    w = round(reels._OLC.textlength(metin, font=F(boy, True))) + 130
    kat = panel(w, yuk, R.vurgu, yuk // 2)
    d = ImageDraw.Draw(kat)
    d.text((34, yuk / 2 + 1), metin, font=F(boy, True), fill=R.vurgu_ustu, anchor='lm')
    x, cy = kat.width - 34, kat.height / 2
    d.line((x - 26, cy, x, cy), fill=R.vurgu_ustu, width=5)
    d.line((x - 12, cy - 12, x, cy, x - 12, cy + 12), fill=R.vurgu_ustu, width=5, joint='curve')
    return [(kat, SAG - kat.width, y)]


def cta_slayti(no, toplam):
    """Tek çağrı: Telegram kanalı (bağlantı profilde)."""
    R = reels.R
    o = []
    logo = k.logo_kare(150)
    if logo is not None:
        o.append((logo.convert('RGBA'), (KW - 150) / 2, 230))
    o.append((yazi('HER YENİ İLAN', 96, R.yazi, genislik=SAG - SOL, hiza='m'), SOL, 440))
    o.append((yazi('TELEGRAM', 96, R.vurgu, genislik=SAG - SOL, hiza='m'), SOL, 550))
    o.append((yazi('KANALINDA', 96, R.vurgu, genislik=SAG - SOL, hiza='m'), SOL, 660))
    kutu = panel(SAG - SOL, 150, R.vurgu, 44)
    ImageDraw.Draw(kutu).text((kutu.width / 2, 76), '@kpsstercihi', font=F(76, True), fill=R.vurgu_ustu, anchor='mm')
    o.append((kutu, SOL, 850))
    o.append((yazi('Bağlantı profilde', 46, R.soluk, genislik=SAG - SOL, hiza='m'), SOL, 1040))
    return slayt(o, no, toplam)


def hikaye_kapanisi(sure=2.4):
    """Hikâyenin son karesi: tek çağrı (Telegram), çıkış hareketi yok."""
    R = reels.R
    o = [Oge(yazi('HER YENİ İLAN', 104, R.yazi, genislik=SAG - SOL, hiza='m'), SOL, 600, 0.0),
         Oge(yazi('TELEGRAM', 104, R.vurgu, genislik=SAG - SOL, hiza='m'), SOL, 720, 0.1),
         Oge(yazi('KANALINDA', 104, R.vurgu, genislik=SAG - SOL, hiza='m'), SOL, 840, 0.18)]
    kutu = panel(SAG - SOL, 160, R.vurgu, 44)
    ImageDraw.Draw(kutu).text((kutu.width / 2, 81), '@kpsstercihi', font=F(80, True), fill=R.vurgu_ustu, anchor='mm')
    o.append(Oge(kutu, SOL, 1060, 0.35, 'buyu'))
    o.append(Oge(yazi('Bağlantı profilde', 48, R.soluk, genislik=SAG - SOL, hiza='m'), SOL, 1270, 0.6))
    return Sahne(sure, o, son=True)


# ---------------------------------------------------------------- ortak satırlar
def il_satirlari(iller, en_cok, w=SAG - SOL, adim=96):
    """İl adı, oran çubuğu ve ilan sayısı; tek katman."""
    R = reels.R
    kat = Image.new('RGBA', (w, adim * len(iller)), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    for n, (il, sayi) in enumerate(iller):
        y = n * adim
        d.text((0, y + 40), il, font=F(44, True), fill=R.yazi, anchor='lm')
        x0, x1 = 300, w - 150
        d.rounded_rectangle((x0, y + 30, x1, y + 50), radius=10, fill=R.panel_cizgi or R.cizgi)
        d.rounded_rectangle((x0, y + 30, x0 + max(20, round((x1 - x0) * sayi / en_cok)), y + 50), radius=10, fill=R.vurgu)
        d.text((w, y + 40), f'{sayi} ilan', font=F(40, True), fill=R.vurgu, anchor='rm')
    return kat


def gun_basligi(gun, simdi):
    kalan = (gun - simdi.date()).days
    return f'{gun.day} {AYLAR[gun.month - 1]} {reels.GUNLER[gun.weekday()]}', \
        'BUGÜN SON GÜN' if kalan <= 0 else 'YARIN SON GÜN' if kalan == 1 else f'{kalan} GÜN KALDI', kalan


def kalan_rengi(kalan):
    R = reels.R
    return (R.acil, R.acil_ustu) if kalan <= 1 else (R.yakin, R.yakin_ustu) if kalan <= 3 else (R.vurgu, R.vurgu_ustu)


def ilan_satiri(ilan, simdi, logo, w=SAG - SOL, h=130):
    """Liste satırı: logo, kurum adı, altında kadro adları; sağda kaç kişi (bilinmiyorsa boş)."""
    R = reels.R
    v = k.veri(ilan, logo, simdi)
    kutu = panel(w, h, yaricap=32)
    d = ImageDraw.Draw(kutu)
    cap = h - 36
    kutu.alpha_composite(logo_rozeti(ilan, logo, cap), (22, 18))
    x = 22 + cap + 24
    sag = f'{binlik(v["toplam"])} kişi' if v['toplam'] else ''
    sw = round(d.textlength(sag, font=F(44, True))) if sag else 0
    if sag:
        d.text((w - 32, h / 2), sag, font=F(44, True), fill=R.vurgu, anchor='rm')
    gen = w - x - sw - 60
    adlar = [x_['ad'] for x_ in sorted(v['kadrolar'], key=lambda x_: -(x_['adet'] or 0)) if k._norm(x_['ad']) not in reels.AD_DEGIL]
    alt = ', '.join(adlar[:2]) + (f' +{len(adlar) - 2}' if len(adlar) > 2 else '')
    s_, yz = k.sigdir(d, reels.kisa_kurum(ilan), True, [38, 34, 30], gen, 1)
    if alt:
        d.text((x, h / 2 - 4), s_[0], font=yz, fill=R.yazi, anchor='ls')
        d.text((x, h / 2 + 8), k.lines(d, alt, F(28), gen, 1)[0], font=F(28), fill=R.soluk, anchor='lt')
    else:
        d.text((x, h / 2), s_[0], font=yz, fill=R.yazi, anchor='lm')
    return kutu


# ---------------------------------------------------------------- 1) Haftanın kadro raporu
def kadro_raporu(acik, simdi, logo):
    R = reels.R
    hafta = h.hafta_ilanlari(acik, simdi)
    sira = h.kurum_siralamasi(hafta, simdi)
    dagilim, ortak = h.duzey_dagilimi(hafta, simdi)
    belirsiz = [i for i in hafta if not any(kod in (i.get('ogrenim') or []) for kod, _ in h.DUZEYLER)]
    if belirsiz:
        dagilim = dagilim + [{'ad': 'Belirtilmemiş', 'etiket': 'Öğrenim belgede belirtilmemiş', 'ilan': len(belirsiz),
                              'kadro': sum(k.veri(i, None, simdi)['toplam'] or 0 for i in belirsiz), 'en_buyuk': None}]
    iller = h.il_dagilimi(hafta)
    toplam = sum(g['kadro'] for g in sira)
    aralik = h.hafta_araligi(simdi)
    alt_satir = f'{len(hafta)} yeni ilan · {len(sira)} kurum · {len(iller)} il'
    en_cok = max((x['kadro'] for x in dagilim), default=0)

    # hikâye
    o, y = h._baslik_sahnesi(aralik, ['HAFTANIN', 'KADRO RAPORU'])
    o += h.sayi_etiket(toplam, 'kadro', y + 30, 0.3, 240)
    o.append(Oge(yazi(alt_satir, 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 330, 0.5))
    ilk = sira[0]
    o.append(Oge(h.sira_satiri(1, ilk['kurum'], ilk['kadro'], h._ilan_yazi(ilk), ilk['ornek'], logo(ilk['ornek']), h=160), SOL, y + 430, 0.6))
    sahneler = [Sahne(2.6, o), h.kurum_sahneleri(sira, len(hafta), simdi, logo, kapanis=False)[1]]
    o = [Oge(yazi('ÖĞRENİM DÜZEYİNE GÖRE', 56, R.vurgu), SOL, 400, 0.0, 'sol')]
    y = 500
    for n, x in enumerate(dagilim):
        kat = h.duzey_paneli(x, en_cok, h=260)
        o.append(Oge(kat, SOL, y, 0.12 + n * 0.14))
        y += kat.height + 24
    sahneler.append(Sahne(2.9, o))
    o = [Oge(yazi('İLLERE GÖRE', 56, R.vurgu), SOL, 400, 0.0, 'sol'),
         Oge(il_satirlari(iller[:10], iller[0][1]), SOL, 510, 0.15)]
    if len(iller) > 10:
        o.append(Oge(yazi(f'+{len(iller) - 10} il daha', 40, R.soluk), SOL, 510 + 10 * 96 + 10, 0.4))
    sahneler.append(Sahne(2.6, o))
    sahneler.append(hikaye_kapanisi())

    # karusel
    n_slayt = 6
    sl = []
    o, y = baslik_katmanlari(['HAFTANIN', 'KADRO RAPORU'], 290, (128, 112, 100))
    o = [(hap(aralik, R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 180)] + o
    o += iri_sayi(toplam, 'kadro', y + 40)
    o.append((yazi(alt_satir, 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 300))
    o.append((h.sira_satiri(1, ilk['kurum'], ilk['kadro'], h._ilan_yazi(ilk), ilk['ornek'], logo(ilk['ornek']), h=150), SOL, y + 380))
    o += ileri_hapi('İlk 5 kurum', 1215)
    sl.append(slayt(o, 1, n_slayt))
    o = [(yazi('EN ÇOK KADRO AÇAN 5 KURUM', 52, R.vurgu, genislik=SAG - SOL, satir=1), SOL, 190)]
    for n, g in enumerate(sira[:5]):
        o.append((h.sira_satiri(n + 1, g['kurum'], g['kadro'], h._ilan_yazi(g), g['ornek'], logo(g['ornek']), h=158), SOL, 290 + n * 176))
    sl.append(slayt(o, 2, n_slayt))
    o = [(yazi('ÖĞRENİM DÜZEYİNE GÖRE', 52, R.vurgu), SOL, 190)]
    y = 290
    for n, x in enumerate(dagilim):
        kat = h.duzey_paneli(x, en_cok, h=260)
        o.append((kat, SOL, y))
        y += kat.height + 24
    sl.append(slayt(o, 3, n_slayt))
    o = [(yazi('İLLERE GÖRE', 52, R.vurgu), SOL, 190), (il_satirlari(iller[:9], iller[0][1], adim=100), SOL, 300)]
    if len(iller) > 9:
        o.append((yazi(f'+{len(iller) - 9} il daha', 40, R.soluk), SOL, 300 + 9 * 100 + 10))
    sl.append(slayt(o, 4, n_slayt))
    sl.append(en_buyuk_slayti(sira[0]['ornek'], simdi, logo, 5, n_slayt))
    sl.append(cta_slayti(6, n_slayt))
    veri = {'tur': 'kadro-raporu', 'aralik': aralik, 'ilan': len(hafta), 'kadro': toplam, 'kurum': len(sira),
            'ilk5': [(g['kurum'], g['kadro']) for g in sira[:5]], 'duzey': [(x['ad'], x['ilan'], x['kadro']) for x in dagilim],
            'iller': iller, 'ortak_duzey': ortak}
    return sahneler, sl, veri


def en_buyuk_slayti(ilan, simdi, logo, no, toplam):
    R = reels.R
    lg = logo(ilan)
    v = k.veri(ilan, lg, simdi)
    o = [(yazi('HAFTANIN EN BÜYÜK ALIMI', 52, R.vurgu), SOL, 190), (logo_rozeti(ilan, lg, 170), SOL, 290)]
    ad = reels.sigan_yazi(reels.kisa_kurum(ilan), [58, 50, 44], SAG - SOL - 210, 3)
    o.append((ad, SOL + 210, 290 + max(0, (170 - ad.height) // 2)))
    o += iri_sayi(v['toplam'] or 0, 'kişi', 500, 200)
    y = 760
    for adet, kad in reels.kadro_satirlari(v, 4):
        metin = (f'{binlik(adet)}  ' if adet else '') + kad
        o.append((yazi(metin, 42, R.yazi if adet is not None else R.soluk, genislik=SAG - SOL, satir=1), SOL, y))
        y += 64
    kosul = ' · '.join(p for p in (' · '.join(v['duzeyler']), v['yer']) if p)
    if kosul:
        o.append((yazi(kosul, 38, R.soluk, False, genislik=SAG - SOL, satir=1), SOL, y + 16))
    if v['tarih']:
        o.append((yazi('Son başvuru: ' + v['tarih'], 44, R.vurgu, genislik=SAG - SOL, satir=1), SOL, 1170))
        rozet = reels.kalan_hapi(v, 38)
        if rozet:
            o.append((rozet, SAG - rozet.width, 1100))
    return slayt(o, no, toplam)


# ---------------------------------------------------------------- 2) Son günü yaklaşanlar
SON_GUN_SATIR = 4


def _gun_listesi_katmani(gun, ilanlar, simdi, logo, w=SAG - SOL, satir=SON_GUN_SATIR, adim=118):
    """Gün başlığı (tarih + kalan hapı) ve altında ilan satırları; tek katman."""
    R = reels.R
    yazi_gun, kalan_metin, kalan = gun_basligi(gun, simdi)
    goster = ilanlar if len(ilanlar) <= satir else ilanlar[:satir - 1]
    fazla = len(ilanlar) - len(goster)
    yuk = 92 + len(goster) * adim + (56 if fazla else 0)
    kat = Image.new('RGBA', (w, yuk), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    d.text((0, 34), yazi_gun, font=F(48, True), fill=R.yazi, anchor='lm')
    dolgu, renk = kalan_rengi(kalan)
    rozet = hap(kalan_metin, dolgu, renk, 30)
    kat.alpha_composite(rozet, (w - rozet.width, 34 - rozet.height // 2))
    for n, i in enumerate(goster):
        kat.alpha_composite(ilan_satiri(i, simdi, logo(i), w, adim - 14), (0, 92 + n * adim))
    if fazla:
        d.text((0, 92 + len(goster) * adim + 6), f'+{fazla} ilan daha', font=F(38, True), fill=R.soluk)
    return kat


def son_gun(acik, simdi, logo, gun=7):
    R = reels.R
    gruplar = h.son_gun_gruplari(acik, simdi, gun)
    if not gruplar:
        return None
    ilan_say = sum(len(v) for _, v in gruplar)
    kadro = sum(k.veri(i, None, simdi)['toplam'] or 0 for _, v in gruplar for i in v)
    bugun = f'{simdi.day} {AYLAR[simdi.month - 1]} {reels.GUNLER[simdi.weekday()]}'
    alt_satir = f'{gun} gün içinde · {binlik(kadro)} kadro'

    # hikâye: kapak + gün listeleri (sahneye sığdığı kadar) + kapanış
    o, y = h._baslik_sahnesi(bugun, ['SON GÜNÜ', 'YAKLAŞAN'])
    o += h.sayi_etiket(ilan_say, 'ilan', y + 30, 0.3, 240)
    o.append(Oge(yazi(alt_satir, 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 330, 0.5))
    o.append(Oge(gun_seridi(gruplar, simdi), SOL, y + 430, 0.6))
    sahneler = [Sahne(2.4, o)]
    katlar = [_gun_listesi_katmani(g, v, simdi, logo, satir=3, adim=112) for g, v in gruplar]
    parca, y0 = [], 400
    for kat in katlar + [None]:
        if kat is None or (parca and y0 + sum(p.height + 40 for p in parca) + kat.height > ALT):
            o = [Oge(p, SOL, y0 + sum(q.height + 40 for q in parca[:n]), 0.1 + n * 0.25) for n, p in enumerate(parca)]
            sahneler.append(Sahne(0, o))
            parca = []
        if kat is not None:
            parca.append(kat)
    sahneler.append(hikaye_kapanisi(2.2))
    kalan_sure = HIKAYE_EN_UZUN - 0.2 - sum(s.sure for s in sahneler)
    for s in sahneler[1:-1]:
        s.sure = round(min(3.4, kalan_sure / (len(sahneler) - 2)), 2)

    # karusel: kapak + her gün bir slayt + çağrı (en çok 8)
    sayfalar = gun_sayfalari(gruplar, simdi, logo)
    n_slayt = len(sayfalar) + 2
    sl = []
    o, y = baslik_katmanlari(['SON GÜNÜ', 'YAKLAŞAN'], 290, (128, 112))
    o = [(hap(bugun, R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 180)] + o
    o += iri_sayi(ilan_say, 'ilan', y + 20, 200)
    o.append((yazi(alt_satir, 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 270))
    o.append((gun_seridi(gruplar, simdi), SOL, y + 360))
    o += ileri_hapi('Gün gün liste', 1215)
    sl.append(slayt(o, 1, n_slayt))
    for n, sayfa in enumerate(sayfalar, 2):
        if len(sayfa) == 1:   # tek gün: iri tarih düzeni
            g, v = sayfa[0]
            yazi_gun, kalan_metin, kalan = gun_basligi(g, simdi)
            dolgu, renk = kalan_rengi(kalan)
            o = [(hap(kalan_metin, dolgu, renk, 40), SOL, 180),
                 (yazi(f'{g.day} {AYLAR[g.month - 1]}', 150, R.yazi), SOL, 270),
                 (yazi(reels.GUNLER[g.weekday()] + f' · {len(v)} ilan', 50, R.soluk), SOL, 460)]
            goster = v if len(v) <= 5 else v[:4]
            for m, i in enumerate(goster):
                o.append((ilan_satiri(i, simdi, logo(i)), SOL, 560 + m * 146))
            if len(v) > len(goster):
                o.append((yazi(f'+{len(v) - len(goster)} ilan daha · kpsstercihi.com', 40, R.soluk), SOL, 560 + len(goster) * 146 + 10))
        else:                 # birden çok gün: gün blokları alt alta
            o, y = [], 190
            for g, v in sayfa:
                kat = _gun_listesi_katmani(g, v, simdi, logo, satir=6, adim=GUN_ADIM)
                o.append((kat, SOL, y))
                y += kat.height + 40
        sl.append(slayt(o, n, n_slayt))
    sl.append(cta_slayti(n_slayt, n_slayt))
    veri = {'tur': 'son-gun', 'bugun': str(simdi.date()), 'ilan': ilan_say, 'kadro': kadro,
            'gunler': [(str(g), [(reels.kisa_kurum(i), k.veri(i, None, simdi)['toplam']) for i in v]) for g, v in gruplar]}
    return sahneler, sl, veri


GUN_ADIM, SAYFA_YUK = 124, 1100


def gun_sayfalari(gruplar, simdi, logo):
    """Günleri karusel sayfalarına böler: sondan başa doldurur (tek ilanlık son gün yalnız kalmasın); en çok 6 sayfa."""
    def yuk(v):
        return 92 + min(len(v), 6) * GUN_ADIM
    sayfalar, sayfa, dolu = [], [], 0
    for g, v in reversed(gruplar):
        ek = yuk(v) + (40 if sayfa else 0)
        if sayfa and dolu + ek > SAYFA_YUK:
            sayfalar.insert(0, sayfa)
            sayfa, dolu, ek = [], 0, yuk(v)
        sayfa.insert(0, (g, v))
        dolu += ek
    if sayfa:
        sayfalar.insert(0, sayfa)
    return sayfalar[:6]


def gun_seridi(gruplar, simdi, w=SAG - SOL):
    """Kapakta günlerin küçük kutuları: '19 Kas' + ilan sayısı."""
    R = reels.R
    g = gruplar[:6]
    bosluk = 14
    kw = (w - bosluk * (len(g) - 1)) // len(g)
    kat = Image.new('RGBA', (w, 150), (0, 0, 0, 0))
    for n, (gun, v) in enumerate(g):
        kalan = (gun - simdi.date()).days
        dolgu, renk = kalan_rengi(kalan) if kalan <= 1 else (R.panel, R.yazi)
        kutu = panel(kw, 150, dolgu, 28, None if kalan <= 1 else R.panel_cizgi)
        d = ImageDraw.Draw(kutu)
        d.text((kw / 2, 40), f'{gun.day} {AYLAR[gun.month - 1][:3]}', font=F(32, True), fill=renk if kalan <= 1 else R.soluk, anchor='mm')
        d.text((kw / 2, 100), str(len(v)), font=F(60, True), fill=renk if kalan <= 1 else R.vurgu, anchor='mm')
        kat.alpha_composite(kutu, (n * (kw + bosluk), 0))
    return kat


# ---------------------------------------------------------------- 3) Bu puanla nereye?
def puan_bandi(docs, duzey, duzey_adi, alt, ust):
    R = reels.R
    from puan_sayfalari import donem_yaz
    donem, kayitlar = h.puan_kayitlari(docs, duzey)
    bant = h.puan_bandi(kayitlar, alt, ust)
    if len(bant) < 8:
        return None
    dy = donem_yaz(donem)
    kisi = sum(r.get('yerlesen') or 0 for r in bant)
    ust_hap = f'KPSS {dy} · {k.tr_buyuk(duzey_adi)}'
    bant_yazi = f'{alt}–{ust}'
    unvanlar = {}
    for r in bant:
        u = unvanlar.setdefault(h.basliga(r['unvan']), {'kisi': 0, 'kadro': 0, 'min': []})
        u['kisi'] += r.get('yerlesen') or 0
        u['kadro'] += 1
        u['min'].append(r['min'])
    cok = sorted(unvanlar.items(), key=lambda x: (-x[1]['kisi'], x[0]))[:6]
    alt_satir = f'{len(bant)} kadroda · taban puanı {alt} ile {ust} arası'

    def unvan_katmani(w=SAG - SOL, adim=150):
        kat = Image.new('RGBA', (w, adim * len(cok)), (0, 0, 0, 0))
        for n, (ad, u) in enumerate(cok):
            kutu = panel(w, adim - 18, yaricap=32)
            d = ImageDraw.Draw(kutu)
            sag = f'{u["kisi"]} kişi'
            sw = round(d.textlength(sag, font=F(52, True)))
            d.text((w - 36, (adim - 18) / 2), sag, font=F(52, True), fill=R.vurgu, anchor='rm')
            s = k.lines(d, ad, F(42, True), w - sw - 110, 1)[0]
            d.text((36, 26), s, font=F(42, True), fill=R.yazi)
            aral = f'{h.puan_yaz(min(u["min"]))} – {h.puan_yaz(max(u["min"]))}' if len(u['min']) > 1 else h.puan_yaz(u['min'][0])
            d.text((36, 80), f'{u["kadro"]} kadro · taban {aral}', font=F(32), fill=R.soluk)
            kat.alpha_composite(kutu, (0, n * adim))
        return kat

    # hikâye
    o, y = h._baslik_sahnesi(ust_hap, [f'{bant_yazi} PUANLA', 'NEREYE', 'ATANILDI?'])
    o += h.sayi_etiket(kisi, 'kişi yerleşti', y + 30, 0.3, 220)
    o.append(Oge(yazi(alt_satir, 46, R.soluk, genislik=SAG - SOL, satir=2), SOL, y + 300, 0.5))
    sahneler = [Sahne(2.6, o)]
    o = [Oge(yazi('EN DÜŞÜK PUANLA GİRİLENLER', 52, R.vurgu, genislik=SAG - SOL, satir=1), SOL, 400, 0.0, 'sol')]
    for m, r in enumerate(bant[:4]):
        o.append(Oge(h.puan_satiri(r, vurgulu=m < 3), SOL, 500 + m * 226, 0.15 + m * 0.18))
    o.append(Oge(yazi(f'Kaynak: ÖSYM KPSS {dy} sayısal bilgiler', 32, R.soluk, False), SOL, 500 + 4 * 226, 0.9))
    sahneler.append(Sahne(3.6, o))
    o = [Oge(yazi('EN ÇOK YERLEŞİLEN UNVANLAR', 52, R.vurgu, genislik=SAG - SOL, satir=1), SOL, 400, 0.0, 'sol'),
         Oge(unvan_katmani(adim=160), SOL, 500, 0.15)]
    sahneler.append(Sahne(3.4, o))
    sahneler.append(hikaye_kapanisi())

    # karusel
    n_slayt = 6
    sl = []
    o, y = baslik_katmanlari([f'{bant_yazi} PUANLA', 'NEREYE', 'ATANILDI?'], 290, (128, 112, 100))
    o = [(hap(ust_hap, R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 180)] + o
    o += iri_sayi(kisi, 'kişi yerleşti', y + 30, 200)
    o.append((yazi(alt_satir, 44, R.soluk, genislik=SAG - SOL, satir=2), SOL, y + 270))
    o += ileri_hapi('En düşük puanlar', 1215)
    sl.append(slayt(o, 1, n_slayt))
    o = [(yazi('EN DÜŞÜK PUANLA GİRİLEN 3 KADRO', 50, R.vurgu, genislik=SAG - SOL, satir=1), SOL, 190)]
    for m, r in enumerate(bant[:3]):
        o.append((h.puan_satiri(r, h=230, vurgulu=True), SOL, 290 + m * 254))
    o.append((yazi('Taban puan: o kadroya yerleşen adayların en düşük puanı', 36, R.yazi, False, genislik=SAG - SOL, satir=2), SOL, 290 + 3 * 254 + 10))
    o.append((yazi(f'Kaynak: ÖSYM KPSS {dy} sayısal bilgiler', 32, R.soluk, False), SOL, 290 + 3 * 254 + 130))
    sl.append(slayt(o, 2, n_slayt))
    for n, (s, e) in enumerate(((3, 8), (8, 13)), 3):
        o = [(yazi(f'SIRADAKİLER · {s + 1}–{e}', 50, R.vurgu), SOL, 190)]
        for m, r in enumerate(bant[s:e]):
            o.append((h.puan_satiri(r, h=170), SOL, 290 + m * 190))
        sl.append(slayt(o, n, n_slayt))
    o = [(yazi('EN ÇOK YERLEŞİLEN UNVANLAR', 50, R.vurgu, genislik=SAG - SOL, satir=1), SOL, 190), (unvan_katmani(), SOL, 290)]
    sl.append(slayt(o, 5, n_slayt))
    sl.append(cta_slayti(6, n_slayt))
    veri = {'tur': 'puan-bandi', 'donem': donem, 'duzey': duzey, 'bant': [alt, ust], 'kadro_kodu': len(bant), 'kisi': kisi,
            'en_dusuk': [(r['unvan'], r.get('kurum'), r.get('il'), r['min']) for r in bant[:13]], 'unvanlar': [(a, u['kisi']) for a, u in cok]}
    return sahneler, sl, veri


# ---------------------------------------------------------------- 4) Tek ilan (her yeni ilan bir karusel)
def _kadro_kutusu(adet, ad, w, h, soluk=False):
    R = reels.R
    kutu = panel(w, h, yaricap=32)
    d = ImageDraw.Draw(kutu)
    x = 40
    if adet:
        d.text((x, h / 2), binlik(adet), font=F(64, True), fill=R.vurgu, anchor='lm')
        x += round(d.textlength(binlik(adet), font=F(64, True))) + 30
    s, yz = k.sigdir(d, ad, True, [44, 38, 34], w - x - 36, 2)
    for m, satir in enumerate(s):
        d.text((x, h / 2 + (m - (len(s) - 1) / 2) * yz.size * 1.15), satir, font=yz, fill=R.soluk if soluk else R.yazi, anchor='lm')
    return kutu


def ilan_karuseli(ilan, simdi, logo):
    """Yeni ilan karuseli (1080x1350): kapak, kadrolar, kimler başvurabilir, son başvuru, Telegram. (slaytlar, veri)."""
    R = reels.R
    lg = logo(ilan)
    v = k.veri(ilan, lg, simdi)
    if not v['kadrolar']:
        return None
    satirlar = reels.kadro_satirlari(v, 7)
    kosullar = reels.kosul_satirlari(v)
    bitis, saatli = k._bitis(ilan)
    toplam = 3 + (len(satirlar) > 1) + bool(kosullar)
    sl, no = [], 1

    # 1) kapak
    o = [(hap('YENİ İLAN', R.vurgu, R.vurgu_ustu, 40), SOL, 180), (logo_rozeti(ilan, lg, 190), SOL, 280)]
    ad = reels.sigan_yazi(reels.kisa_kurum(ilan), [64, 56, 48, 42], SAG - SOL - 230, 3)
    o.append((ad, SOL + 230, 280 + max(0, (190 - ad.height) // 2)))
    sayi, alt = reels.ne_alinacak(v)
    if sayi:
        o += iri_sayi(sayi, 'kişi alınacak', 540, 230)
        ne = reels.kisa_ne(v).split(' · ', 1)[-1] if ' · ' in reels.kisa_ne(v) else ''
        if ne:
            o.append((yazi(ne, 50, R.yazi, genislik=SAG - SOL, satir=2), SOL, 830))
    else:
        o.append((reels.sigan_yazi(alt, [110, 92, 76, 64], SAG - SOL, 3, R.vurgu), SOL, 560))
    if bitis:
        o.append((yazi(f'Son başvuru: {bitis.day} {AYLAR[bitis.month - 1]} {reels.GUNLER[bitis.weekday()]}', 46, R.soluk,
                       genislik=SAG - SOL, satir=1), SOL, 1030))
        rozet = reels.kalan_hapi(v, 38)
        if rozet:
            o.append((rozet, SOL, 1110))
    o += ileri_hapi('Kadrolar ve şartlar' if len(satirlar) > 1 else 'Şartlar ve tarih', 1215)
    sl.append(slayt(o, no, toplam))

    # 2) kadrolar (birden çoksa; tek kadro kapakta zaten yazıyor)
    if len(satirlar) > 1:
        no += 1
        o = [(yazi('HANGİ KADROLAR?', 56, R.vurgu), SOL, 190)]
        adim = 132 if len(satirlar) > 5 else 160
        for n, (adet, kad) in enumerate(satirlar):
            o.append((_kadro_kutusu(adet, kad, SAG - SOL, adim - 18, soluk=adet is None), SOL, 300 + n * adim))
        sl.append(slayt(o, no, toplam))

    # 3) kimler başvurabilir
    if kosullar:
        no += 1
        o = [(yazi('KİMLER', 96, R.yazi), SOL, 190), (yazi('BAŞVURABİLİR?', 96, R.vurgu), SOL, 300)]
        for n, (etiket, deger) in enumerate(kosullar):
            kutu = panel(SAG - SOL, 230, yaricap=36)
            d = ImageDraw.Draw(kutu)
            d.text((44, 32), k.tr_buyuk(etiket), font=F(34, True), fill=R.soluk)
            s, yz = k.sigdir(d, deger, True, [56, 48, 42, 36], kutu.width - 88, 2)
            k.blok(d, 44, 92 if len(s) == 1 else 84, s, yz, R.yazi, aralik=round(yz.size * 1.12))
            o.append((kutu, SOL, 470 + n * 256))
        sl.append(slayt(o, no, toplam))

    # 4) son başvuru + site
    no += 1
    o = [(yazi('SON BAŞVURU', 60, R.vurgu), SOL, 190)]
    if bitis:
        o.append((yazi(f'{bitis.day} {AYLAR[bitis.month - 1]}', 180, R.yazi), SOL, 290))
        o.append((yazi(reels.GUNLER[bitis.weekday()] + (f' · {bitis:%H:%M}' if saatli else ''), 56, R.soluk), SOL, 520))
        rozet = reels.kalan_hapi(v, 50)
        if rozet:
            o.append((rozet, SOL, 620))
    kutu = panel(SAG - SOL, 300, R.vurgu, 44)
    d = ImageDraw.Draw(kutu)
    d.text((48, 44), 'Şartların tamamı ve başvuru bağlantısı', font=F(38, True), fill=R.vurgu_ustu)
    d.text((48, 108), 'kpsstercihi.com', font=F(84, True), fill=R.vurgu_ustu)
    d.text((48, 226), 'Bağlantı profilde', font=F(38, True), fill=R.vurgu_ustu)
    o.append((kutu, SOL, 860))
    sl.append(slayt(o, no, toplam))

    # 5) Telegram
    sl.append(cta_slayti(toplam, toplam))
    veri = {'tur': 'ilan', 'id': ilan.get('id'), 'kurum': reels.kisa_kurum(ilan), 'toplam': v['toplam'],
            'kadrolar': [(a, n) for n, a in satirlar], 'bitis': str(bitis.date()) if bitis else None,
            'kosullar': kosullar, 'karusel_slayt': len(sl)}
    return sl, veri


# ---------------------------------------------------------------- yazma
def yaz(sahneler, slaytlar, veri, klasor, muzik=True):
    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    for eski in list(klasor.glob('hikaye-*.png')) + list(klasor.glob('karusel-*.png')):
        eski.unlink()
    for n, im in enumerate(reels.sahne_kareleri(sahneler), 1):
        im.save(klasor / f'hikaye-{n:02d}.png', optimize=True)
    for n, im in enumerate(slaytlar, 1):
        im.save(klasor / f'karusel-{n:02d}.png', optimize=True)
    parca, bas = reels.muzik_yolu('sabah') if muzik else (None, 0.0)
    sure = reels.video_yaz(sahneler, klasor / 'hikaye.mp4', parca, muzik_bas=bas)
    veri = dict(veri, hikaye_sure=round(sure, 2), hikaye_kare=len(sahneler), karusel_slayt=len(slaytlar), palet=reels.R.ad)
    (klasor / 'veri.json').write_text(json.dumps(veri, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    return veri


def main():
    import sosyal_motor as sm
    from kurum_gorseli import kurum_logosu
    a = argparse.ArgumentParser()
    a.add_argument('--cikti', required=True)
    a.add_argument('--tur', choices=('kadro-raporu', 'son-gun', 'puan-bandi'), action='append')
    a.add_argument('--duzey', default='lisans')
    a.add_argument('--alt', type=int, default=70)
    a.add_argument('--ust', type=int, default=75)
    s = a.parse_args()
    turler = s.tur or ['kadro-raporu', 'son-gun', 'puan-bandi']
    simdi = datetime.now(k.TR)
    acik = sm.acik_ilanlar(sm.ilanlari_yukle(ROOT / 'docs'), simdi) if set(turler) - {'puan-bandi'} else []
    paletler = {'kadro-raporu': 'kagit', 'son-gun': 'bordo', 'puan-bandi': 'kagit'}
    adlar = dict(h.PUAN_DUZEYLERI)
    for tur in turler:
        reels.palet_sec(paletler[tur])
        if tur == 'kadro-raporu':
            sonuc = kadro_raporu(acik, simdi, kurum_logosu)
        elif tur == 'son-gun':
            sonuc = son_gun(acik, simdi, kurum_logosu)
        else:
            sonuc = puan_bandi(ROOT / 'docs', s.duzey, adlar[s.duzey], s.alt, s.ust)
        if not sonuc:
            print(f'{tur}: veri yetersiz')
            continue
        veri = yaz(*sonuc, Path(s.cikti) / tur)
        print(f'{tur}: {veri["hikaye_kare"]} hikâye karesi ({veri["hikaye_sure"]} sn), {veri["karusel_slayt"]} karusel slaytı')


if __name__ == '__main__':
    main()
