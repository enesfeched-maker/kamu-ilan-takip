"""Haftalık veri dizisi: pazar akşamı tek video (reels.py sahne motoru, onaylı Kâğıt/Bordo görünüm).

Diziler sırayla döner; verisi yetmeyen dizi atlanır (cılız video yayımlanmaz):
  kurum  Bu hafta en çok kadro açan kurumlar      (kadro sayısı bilinen en az KURUM_EN_AZ kurum)
  duzey  Bu hafta lise / önlisans / lisans mezununa açılan kadrolar  (en az DUZEY_EN_AZ_ILAN ilan, en az iki düzey)
  dusuk  En düşük taban puanla atanılan kadrolar (ÖSYM son dönem; düzey her seferinde değişir)

"KPSS şartı olmayan alımlar" dizisi bilerek yok: ilan.kpss='kpsssiz' (siniflandir.kpss_durumu) metnin herhangi bir yerinde
"KPSS aranmaz" geçince bütün ilana yazılıyor; ör. yalnız eczacı kadrosu için KPSS'siz olan bir üniversite ilanı da
'kpsssiz' çıkıyor. Kadro düzeyinde güvenilir alan olmadan "şart yok" diye paylaşmak yanıltır.

"Bu hafta" = son 7 günde siteye eklenen (ilk_gorulme), başvurusu açık ilanlar. Akademik, kurum içi, iptal ve duyuru
kayıtları girmez. Sayılar yalnız ilan verisinden gelir; kadro sayısı bilinmeyen ilan toplama eklenmez.

Örnek içerikler (hikâye/karusel, sosyal_ornek.py) aynı veri hesaplarını kullanır."""
import re
from collections import Counter
from datetime import timedelta
from pathlib import Path

from PIL import ImageDraw

import kart_tasarimlari as k
import reels
from kart_tasarimlari import AYLAR, F
from reels import ALT, SAG, SOL, Oge, Sahne, Sayac, binlik, hap, logo_rozeti, panel, yazi

SERILER = ('kurum', 'duzey', 'dusuk')
HAFTA_GUN = 7
KURUM_EN_AZ = 3
KURUM_SATIR = 5
DUZEY_EN_AZ_ILAN, DUZEY_EN_AZ_DUZEY = 4, 2
DUSUK_SATIR = 8
YOUTUBE_GUNLUK = 6          # YouTube Data API: 10.000 birim/gün, yükleme 1.600 birim -> günde en çok 6 video
DUZEYLER = (('ortaogretim', 'Lise'), ('onlisans', 'Önlisans'), ('lisans', 'Lisans'))
PUAN_DUZEYLERI = (('lisans', 'Lisans'), ('onlisans', 'Önlisans'), ('ortaogretim', 'Ortaöğretim'))
ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- veri
def _zaman(iso):
    from sosyal_motor import _zaman as z
    return z(iso)


def hafta_ilanlari(acik, simdi, gun=HAFTA_GUN):
    """Son `gun` günde siteye eklenen açık ilanlar (kurum içi olanlar hariç); en kalabalık alım önce."""
    from siniflandir import akademik_ilan, kurum_ici
    sinir = simdi - timedelta(days=gun)
    secim = [i for i in acik if not kurum_ici(i) and not akademik_ilan(i) and not i.get('iptal_edildi')
             and (z := _zaman(i.get('ilk_gorulme'))) and sinir <= z <= simdi]
    return sorted(secim, key=lambda i: (-(k.veri(i, None, simdi)['toplam'] or 0), i.get('id') or ''))


def kurum_siralamasi(ilanlar, simdi):
    """[{kurum, kadro, ilan, ornek}] kadro sayısı bilinen ilanlardan, kurum başına toplam; en çok kadro önce."""
    gruplar = {}
    for i in ilanlar:
        toplam = k.veri(i, None, simdi)['toplam']
        if not toplam:
            continue
        ad = reels.kisa_kurum(i)
        anahtar = k._norm(re.sub(r'\s*\([^)]*\)', '', ad))   # 'AFAD' ile '… Başkanlığı (AFAD)' aynı kurum
        g = gruplar.setdefault(anahtar, {'kurum': ad, 'kadro': 0, 'ilan': 0, 'ornek': i})
        g['kadro'] += toplam
        g['ilan'] += 1
    return sorted(gruplar.values(), key=lambda g: (-g['kadro'], g['kurum']))


def duzey_dagilimi(ilanlar, simdi):
    """Her öğrenim düzeyi için o düzeye açık ilan sayısı, kadro toplamı ve en kalabalık ilan. Birden çok düzeye açık
    ilan her birinde sayılır (ortak=True olur); öğrenim bilgisi olmayan ilan hiçbirine girmez."""
    sonuc = []
    for kod, ad in DUZEYLER:
        uyan = [i for i in ilanlar if kod in (i.get('ogrenim') or [])]
        kadrolar = [(k.veri(i, None, simdi)['toplam'] or 0, i) for i in uyan]
        en = max(kadrolar, key=lambda x: (x[0], x[1].get('id') or ''), default=(0, None))
        sonuc.append({'duzey': kod, 'ad': ad, 'ilan': len(uyan), 'kadro': sum(t for t, _ in kadrolar),
                      'en_buyuk': en[1] if en[0] else None, 'en_buyuk_kadro': en[0]})
    ortak = any(sum(1 for kod, _ in DUZEYLER if kod in (i.get('ogrenim') or [])) > 1 for i in ilanlar)
    return sonuc, ortak


def il_dagilimi(ilanlar):
    """[(il, ilan sayısı)] ilanın iller listesinden; en çok ilan önce."""
    sayac = Counter(il for i in ilanlar for il in dict.fromkeys(i.get('iller') or []))
    return sorted(sayac.items(), key=lambda x: (-x[1], x[0]))


def son_gun_gruplari(acik, simdi, gun=7):
    """[(tarih, [ilan…])] son başvurusu bugün ile `gun` gün sonrası arasında olanlar, güne göre; günde en kalabalık önce."""
    from site_uret import _bitis
    from siniflandir import kurum_ici
    gruplar = {}
    for i in acik:
        if kurum_ici(i):
            continue
        b = _bitis(i)
        if b and 0 <= (b.date() - simdi.date()).days <= gun:
            gruplar.setdefault(b.date(), []).append(i)
    return [(g, sorted(v, key=lambda i: (-(k.veri(i, None, simdi)['toplam'] or 0), i.get('id') or '')))
            for g, v in sorted(gruplar.items())]


def puan_kayitlari(docs, duzey):
    """(dönem, kayıtlar) ÖSYM sayısal bilgilerinin son dönemi; taban puanı ve unvanı olan kayıtlar."""
    from sosyal_motor import _puan_verisi
    return _puan_verisi(Path(docs), duzey)


def en_dusukler(kayitlar, n=DUSUK_SATIR):
    """En düşük taban puanlı n yerleşme; her unvandan biri (aynı unvan listeyi doldurmasın)."""
    sonuc, gorulen = [], set()
    for r in sorted(kayitlar, key=lambda r: (r['min'], r.get('kod') or '')):
        if r['unvan'] not in gorulen:
            gorulen.add(r['unvan'])
            sonuc.append(r)
        if len(sonuc) == n:
            break
    return sonuc


def puan_bandi(kayitlar, alt, ust):
    """Taban puanı [alt, ust) aralığındaki yerleşmeler; en düşük puan önce."""
    return sorted((r for r in kayitlar if alt <= r['min'] < ust), key=lambda r: (r['min'], r.get('kod') or ''))


# ---------------------------------------------------------------- metin yardımcıları
def puan_yaz(x):
    return f'{x:.2f}'.replace('.', ',')


def basliga(s):
    from puan_sayfalari import baslik_hali
    return baslik_hali(s or '')


def hafta_araligi(simdi, gun=HAFTA_GUN):
    bas = (simdi - timedelta(days=gun - 1)).date()
    son = simdi.date()
    if bas.month == son.month:
        return f'{bas.day}–{son.day} {AYLAR[son.month - 1]}'
    return f'{bas.day} {AYLAR[bas.month - 1]} – {son.day} {AYLAR[son.month - 1]}'


def hafta_kodu(simdi):
    y, h, _ = simdi.isocalendar()
    return f'{y}-H{h:02d}'


# ---------------------------------------------------------------- sahneler (1080x1920)
def _baslik_sahnesi(ust_hap, satirlar, bas=0.0):
    """Kapak başlığı: tarih hapı + iri başlık satırları; son satır vurgu renginde. (öğeler, sonraki y) döner."""
    R = reels.R
    o = [Oge(hap(ust_hap, R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, 420, bas, 'buyu')]
    y = 560
    for n, s in enumerate(satirlar):
        kat = reels.sigan_yazi(s, [112, 100, 88], SAG - SOL, 1, R.vurgu if n == len(satirlar) - 1 else R.yazi)
        o.append(Oge(kat, SOL, y, bas + 0.1 + 0.08 * n, 'sol'))
        y += kat.height + 4
    return o, y


def sayi_etiket(sayi, etiket, y, bas, boy=240):
    """İri sayaç ve yanında küçük etiket (ör. '1.234' 'kadro')."""
    R = reels.R
    gen = round(reels._OLC.textlength(binlik(sayi), font=F(boy, True)))
    return [Sayac(sayi, SOL, y, boy, R.vurgu, bas, 0.7),
            Oge(yazi(etiket, round(boy * 0.3), R.yazi), SOL + gen + 30, y + round(boy * 0.62), bas + 0.2, 'sol')]


def sira_satiri(no, ad, sayi, alt_yazi, logo_ilan=None, logo=None, w=SAG - SOL, h=170):
    """Sıralama satırı: sıra no, logo, kurum adı, sağda iri kadro sayısı."""
    R = reels.R
    kutu = panel(w, h, yaricap=36)
    d = ImageDraw.Draw(kutu)
    d.text((38, h / 2), str(no), font=F(54, True), fill=R.soluk, anchor='lm')
    x = 100
    if logo_ilan is not None:
        kutu.alpha_composite(logo_rozeti(logo_ilan, logo, 108), (x, (h - 108) // 2))
        x += 132
    sag = binlik(sayi)
    sw = max(round(d.textlength(sag, font=F(72, True))), round(d.textlength('kadro', font=F(30, True))))
    d.text((w - 40, h / 2 - 14), sag, font=F(72, True), fill=R.vurgu, anchor='rm')
    d.text((w - 40, h / 2 + 40), 'kadro', font=F(30, True), fill=R.soluk, anchor='rm')
    gen = w - x - sw - 80
    s, yz = k.sigdir(d, ad, True, [44, 40, 36, 32], gen, 2)
    ara = round(yz.size * 1.12)
    yuk = len(s) * ara + (40 if alt_yazi else 0)
    y = (h - yuk) / 2
    k.blok(d, x, y, s, yz, R.yazi, aralik=ara)
    if alt_yazi:   # ör. '2 ilan': aynı kurumun birden çok ilanı
        d.text((x, y + len(s) * ara + 4), alt_yazi, font=F(30, True), fill=R.soluk)
    return kutu


def _ilan_yazi(g):
    return f'{g["ilan"]} ilan' if g['ilan'] > 1 else ''


def kurum_sahneleri(sira, ilan_sayisi, simdi, logo=lambda i: None, kapanis=True):
    R = reels.R
    toplam = sum(g['kadro'] for g in sira)
    o, y = _baslik_sahnesi(hafta_araligi(simdi), ['BU HAFTA EN ÇOK', 'KADRO AÇAN', 'KURUMLAR'])
    o += sayi_etiket(toplam, 'kadro', y + 20, 0.3, 200)
    o.append(Oge(yazi(f'{ilan_sayisi} yeni ilan · {len(sira)} kurum', 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 250, 0.5))
    ilk = sira[0]   # kapakta birinci sıradaki kurum: kaydıranı listeye çeker
    o.append(Oge(sira_satiri(1, ilk['kurum'], ilk['kadro'], _ilan_yazi(ilk), ilk['ornek'], logo(ilk['ornek']), h=160),
                 SOL, min(y + 340, ALT - 160), 0.6))
    sahneler = [Sahne(2.8, o)]
    ust = sira[:KURUM_SATIR]
    o = [Oge(yazi(f'İLK {len(ust)} KURUM', 56, R.vurgu), SOL, 400, 0.0, 'sol')]
    for n, g in enumerate(ust):
        o.append(Oge(sira_satiri(n + 1, g['kurum'], g['kadro'], _ilan_yazi(g), g['ornek'], logo(g['ornek'])), SOL, 500 + n * 196, 0.15 + n * 0.16))
    sahneler.append(Sahne(1.6 + 0.45 * len(ust), o))
    if kapanis:
        sahneler.append(reels.kapanis_sahnesi('Her pazar haftanın özeti'))
    return sahneler


def duzey_paneli(d_, en_cok, w=SAG - SOL, h=290):
    """Tek öğrenim düzeyi: ad, iri kadro sayısı, oran çubuğu, en kalabalık alım. h < 280 ise sıkı düzen."""
    R = reels.R
    if not d_['ilan']:   # o düzeye bu hafta ilan yok: tek satırlık sade kutu
        kutu = panel(w, 110, yaricap=36)
        d = ImageDraw.Draw(kutu)
        d.text((44, 55), k.tr_buyuk(d_.get('etiket') or d_['ad'] + ' mezunu'), font=F(34, True), fill=R.soluk, anchor='lm')
        d.text((w - 44, 55), 'bu hafta ilan yok', font=F(34, True), fill=R.soluk, anchor='rm')
        return kutu
    nb = 96 if h >= 280 else 72
    if d_.get('en_buyuk') is None:   # alt satır yok: kutu çubuğun altında biter
        h = 74 + nb + (30 if h >= 280 else 22) + 14 + 40
    kutu = panel(w, h, yaricap=40)
    d = ImageDraw.Draw(kutu)
    d.text((44, 30), k.tr_buyuk(d_.get('etiket') or d_['ad'] + ' mezunu'), font=F(34, True), fill=R.soluk)
    d.text((w - 44, 30), f'{d_["ilan"]} ilan', font=F(34, True), fill=R.soluk, anchor='ra')
    sayi = binlik(d_['kadro']) if d_['kadro'] else '–'
    d.text((44, 74), sayi, font=F(nb, True), fill=R.vurgu if d_['kadro'] else R.soluk)
    d.text((44 + d.textlength(sayi, font=F(nb, True)) + 20, 74 + round(nb * 0.55)), 'kadro', font=F(round(nb * 0.42), True), fill=R.yazi)
    cw, by = w - 88, 74 + nb + (30 if nb == 96 else 22)
    d.rounded_rectangle((44, by, 44 + cw, by + 14), radius=7, fill=R.panel_cizgi or R.cizgi)
    if d_['kadro'] and en_cok:
        d.rounded_rectangle((44, by, 44 + max(14, round(cw * d_['kadro'] / en_cok)), by + 14), radius=7, fill=R.vurgu)
    if d_.get('en_buyuk') is not None:
        metin = f'En kalabalık: {reels.kisa_kurum(d_["en_buyuk"])} · {binlik(d_["en_buyuk_kadro"])}'
        d.text((44, by + 24), k.lines(d, metin, F(32, True), cw, 1)[0], font=F(32, True), fill=R.soluk)
    return kutu


def duzey_seridi(dagilim, w=SAG - SOL, yuk=230):
    """Kapakta üç düzeyin kutuları: ad ve kadro sayısı (en kalabalık düzey dolu renkte)."""
    R = reels.R
    from PIL import Image
    bosluk = 18
    kw = (w - bosluk * (len(dagilim) - 1)) // len(dagilim)
    en = max(dagilim, key=lambda x: x['kadro'])
    kat = Image.new('RGBA', (w, yuk), (0, 0, 0, 0))
    for n, x in enumerate(dagilim):
        dolu = x is en and x['kadro']
        kutu = panel(kw, yuk, R.vurgu, 36) if dolu else panel(kw, yuk, yaricap=36)
        d = ImageDraw.Draw(kutu)
        renk, soluk = (R.vurgu_ustu, R.vurgu_ustu) if dolu else (R.vurgu, R.soluk)
        d.text((kw / 2, 50), k.tr_buyuk(x['ad']), font=F(34, True), fill=soluk, anchor='mm')
        d.text((kw / 2, 128), binlik(x['kadro']) if x['kadro'] else '–', font=F(80, True), fill=renk, anchor='mm')
        d.text((kw / 2, 192), 'kadro', font=F(32, True), fill=soluk, anchor='mm')
        kat.alpha_composite(kutu, (n * (kw + bosluk), 0))
    return kat


def duzey_sahneleri(dagilim, ortak, ilan_sayisi, simdi, kapanis=True):
    R = reels.R
    toplam_ilan = ilan_sayisi
    o, y = _baslik_sahnesi(hafta_araligi(simdi), ['BU HAFTA', 'HANGİ MEZUNA', 'KAÇ KADRO?'])
    o.append(Oge(yazi(f'{toplam_ilan} yeni ilan', 64, R.yazi), SOL, y + 60, 0.35, 'sol'))
    o.append(Oge(duzey_seridi(dagilim), SOL, y + 180, 0.5))
    sahneler = [Sahne(2.8, o)]
    en_cok = max((x['kadro'] for x in dagilim), default=0)
    o = [Oge(yazi('ÖĞRENİM DÜZEYİNE GÖRE', 56, R.vurgu), SOL, 400, 0.0, 'sol')]
    y = 500
    for n, x in enumerate(dagilim):
        kat = duzey_paneli(x, en_cok)
        o.append(Oge(kat, SOL, y, 0.15 + n * 0.2))
        y += kat.height + 28
    if ortak:
        o.append(Oge(yazi('Birden çok düzeye açık ilan her birinde sayıldı', 32, R.soluk, False, genislik=SAG - SOL, satir=1),
                     SOL, y, 0.8))
    sahneler.append(Sahne(3.4, o))
    if kapanis:
        sahneler.append(reels.kapanis_sahnesi('Her pazar haftanın özeti'))
    return sahneler


def puan_satiri(r, w=SAG - SOL, h=200, vurgulu=False):
    """Yerleşme satırı: unvan, kurum · il, sağda taban puan."""
    R = reels.R
    kutu = panel(w, h, R.vurgu, 36) if vurgulu else panel(w, h, yaricap=36)
    renk, soluk, puan_renk = (R.vurgu_ustu, R.vurgu_ustu, R.vurgu_ustu) if vurgulu else (R.yazi, R.soluk, R.vurgu)
    d = ImageDraw.Draw(kutu)
    p = puan_yaz(r['min'])
    pw = round(d.textlength(p, font=F(68, True)))
    d.text((w - 40, h / 2 - 12), p, font=F(68, True), fill=puan_renk, anchor='rm')
    d.text((w - 40, h / 2 + 44), 'taban', font=F(28, True), fill=soluk, anchor='rm')
    gen = w - 80 - pw - 40
    s, yz = k.sigdir(d, basliga(r['unvan']), True, [44, 40, 36], gen, 2)
    il = ' · ' + basliga(r.get('il')) if r.get('il') else ''
    alt = k.lines(d, _kisa(r.get('kurum')), F(30), gen - round(d.textlength(il, font=F(30))), 1)[0] + il   # il hep görünür
    yuk = len(s) * round(yz.size * 1.12) + 44
    y = (h - yuk) / 2
    k.blok(d, 40, y, s, yz, renk, aralik=round(yz.size * 1.12))
    d.text((40, y + len(s) * round(yz.size * 1.12) + 6), alt, font=F(30), fill=soluk)
    return kutu


KISALTMALAR = ('GAP', 'TCDD', 'PTT', 'TRT', 'AFAD', 'TÜBİTAK', 'TÜİK', 'DSİ', 'SGK', 'MTA', 'BOTAŞ', 'BDDK', 'SPK', 'EPDK',
               'BTK', 'RTÜK', 'TMO', 'TOKİ', 'KOSGEB', 'İŞKUR', 'ÖSYM', 'MEB', 'MSB', 'TSK', 'TBMM', 'ASKİ', 'İSKİ', 'İETT', 'EGO')


def _kisa(kurum):
    """ÖSYM'nin büyük harfli kurum adı -> kısa, başlık hâli; bilinen kısaltmalar büyük harf kalır (GAP, TCDD…)."""
    import sosyal_tasarim
    s = re.sub(r'^T\.\s?C\.\s*', '', (kurum or '').strip(), flags=re.I)
    s = basliga(sosyal_tasarim.kisa_kurum(s))
    s = re.sub(r'\s+Genel Müdürlüğü$', '', s)
    for kis in KISALTMALAR:
        s = re.sub(rf'(?<!\w){re.escape(basliga(kis))}(?!\w)', kis, s)
    return s


def dusuk_sahneleri(kayitlar, donem, duzey_adi, kapanis=True):
    R = reels.R
    from puan_sayfalari import donem_yaz
    dy = donem_yaz(donem)
    en = kayitlar[0]
    o, y = _baslik_sahnesi(f'KPSS {dy} · {k.tr_buyuk(duzey_adi)}', ['EN DÜŞÜK', 'TABAN PUANLA', 'ATANILANLAR'])
    o.append(Oge(yazi(puan_yaz(en['min']), 220, R.vurgu), SOL, y + 30, 0.3, 'yukari'))
    o.append(Oge(yazi(f'{basliga(en["unvan"])} · {_kisa(en.get("kurum"))}', 44, R.yazi, genislik=SAG - SOL, satir=2), SOL, y + 300, 0.5))
    sahneler = [Sahne(2.8, o)]
    for s in range(0, len(kayitlar), 4):
        parca = kayitlar[s:s + 4]
        o = [Oge(yazi('EN DÜŞÜK PUANLAR', 56, R.vurgu), SOL, 400, 0.0, 'sol'),
             Oge(hap(f'{s + 1}–{s + len(parca)}', R.panel, R.soluk, 34, cizgi=R.cizgi), SAG - 150, 404, 0.0)]
        for m, r in enumerate(parca):
            o.append(Oge(puan_satiri(r), SOL, 500 + m * 226, 0.15 + m * 0.18))
        o.append(Oge(yazi(f'Kaynak: ÖSYM KPSS {dy} sayısal bilgiler', 32, R.soluk, False), SOL, 500 + 4 * 226, 0.9))
        sahneler.append(Sahne(1.6 + 0.6 * len(parca), o))
    if kapanis:
        sahneler.append(reels.kapanis_sahnesi('Tercih yaparken işine yarayabilir'))
    return sahneler


# ---------------------------------------------------------------- diziler -> konu (sosyal_motor.sablon_uret biçimi)
TELEGRAM_SATIRI = 'Her pazar haftanın özeti ve yeni ilanlar Telegram kanalımızda: @kpsstercihi (bağlantı profilde) 💛'


def _konu(seri, anahtar, ilanlar, baslik, giris, satirlar, etiketler, sorular, sahneler):
    return {'tur': 'haftalik', 'seri': seri, 'muzik': 'sabah', 'anahtar': anahtar, 'ilanlar': ilanlar,
            'baslik': baslik, 'giris': giris, 'satirlar': satirlar[:5], 'etiketler': etiketler[:3],
            'sorular': sorular, 'kapanis': TELEGRAM_SATIRI, 'sahneler': sahneler}


def seri_konusu(seri, acik, simdi, docs=None, logo=lambda i: None, gecmis=()):
    """Dizinin bu haftaki konusu; veri yetmezse None."""
    docs = Path(docs or ROOT / 'docs')
    if seri == 'kurum':
        hafta = hafta_ilanlari(acik, simdi)
        sira = kurum_siralamasi(hafta, simdi)
        if len(sira) < KURUM_EN_AZ:
            return None
        toplam = sum(g['kadro'] for g in sira)
        ust = sira[:KURUM_SATIR]
        return _konu('kurum', f'haftalik:kurum:{hafta_kodu(simdi)}', [g['ornek']['id'] for g in ust],
                     f'Bu Hafta {binlik(toplam)} Kadro: En Çok Kadro Açan Kurumlar',
                     f'📊 Bu hafta {len(hafta)} yeni kamu ilanında {binlik(toplam)} kadro açıldı. En çok kadro açan kurumlar:',
                     [f'• {g["kurum"]}: {binlik(g["kadro"])} kadro' for g in ust], ['#kadro', '#haftanınözeti'],
                     ['Bu hafta senin için bir ilan çıktı mı? 👇', 'Listede beklediğin bir kurum var mıydı? 👇'],
                     kurum_sahneleri(sira, len(hafta), simdi, logo))
    if seri == 'duzey':
        hafta = hafta_ilanlari(acik, simdi)
        dagilim, ortak = duzey_dagilimi(hafta, simdi)
        bilinen = [i for i in hafta if any(kod in (i.get('ogrenim') or []) for kod, _ in DUZEYLER)]
        if len(bilinen) < DUZEY_EN_AZ_ILAN or sum(1 for x in dagilim if x['ilan']) < DUZEY_EN_AZ_DUZEY:
            return None
        if not any(x['kadro'] for x in dagilim):
            return None
        en = max(dagilim, key=lambda x: x['kadro'])
        return _konu('duzey', f'haftalik:duzey:{hafta_kodu(simdi)}', [i['id'] for i in bilinen][:8],
                     'Bu Hafta Lise, Önlisans ve Lisans Mezununa Açılan Kadrolar',
                     f'🎓 Bu hafta en çok kadro {en["ad"].lower()} mezununa açıldı: {binlik(en["kadro"])} kadro.',
                     [f'• {x["ad"]}: {binlik(x["kadro"])} kadro, {x["ilan"]} ilan' for x in dagilim if x['ilan']],
                     ['#lisemezunu', '#önlisans', '#lisans'],
                     ['Sen hangi düzeyden başvuruyorsun? 👇', 'Senin mezuniyetine bu hafta kaç ilan düştü? 👇'],
                     duzey_sahneleri(dagilim, ortak, len(bilinen), simdi))
    if seri == 'dusuk':
        kullanilan = {g.get('anahtar') for g in gecmis}
        adaylar = []
        for kod, ad in PUAN_DUZEYLERI:
            donem, kayitlar = puan_kayitlari(docs, kod)
            liste = en_dusukler(kayitlar)
            if donem and len(liste) >= DUSUK_SATIR:
                adaylar.append((f'haftalik:dusuk:{kod}:{donem}', kod, ad, donem, liste))
        if not adaylar:
            return None
        anahtar, kod, ad, donem, liste = next((a for a in adaylar if a[0] not in kullanilan), None) or min(
            adaylar, key=lambda a: max((_zaman(g.get('zaman')) for g in gecmis if g.get('anahtar') == a[0]), default=simdi))
        from puan_sayfalari import donem_yaz
        dy = donem_yaz(donem)
        return _konu('dusuk', anahtar, [], f'KPSS {ad} En Düşük Taban Puanla Atanılan Kadrolar ({dy})',
                     f'📊 KPSS {dy} {ad.lower()} yerleştirmesinde en düşük taban puan {puan_yaz(liste[0]["min"])}. En düşük puanla atanılan kadrolar:',
                     [f'• {basliga(r["unvan"])}, {_kisa(r.get("kurum"))} ({basliga(r.get("il"))}): {puan_yaz(r["min"])}' for r in liste],
                     ['#tabanpuan', '#kpsstercih', f'#kpss{kod}'],
                     ['Senin puanın bu listeye yetiyor mu? 👇', 'Listede seni şaşırtan bir kadro oldu mu? 👇'],
                     dusuk_sahneleri(liste, donem, ad))
    return None


def bugun_paylasilan(gecmis, simdi):
    return sum(1 for g in gecmis if (z := _zaman(g.get('zaman'))) and z.astimezone(k.TR).date() == simdi.date())


def haftalik_konu(acik, simdi, gecmis=(), docs=None, logo=lambda i: None):
    """Bu haftanın dizisi: son haftalık videonun dizisinden sonraki, verisi yeten ilk dizi. None döner:
    son 6 günde haftalık video yapıldıysa, bugün YouTube kotası akşam videosuna yer bırakmıyorsa ya da hiçbir dizinin
    verisi yetmiyorsa."""
    gecmis = list(gecmis)
    if any(g.get('tur') == 'haftalik' and (z := _zaman(g.get('zaman'))) and z > simdi - timedelta(days=6) for g in gecmis):
        print('Bu hafta haftalık video zaten yapıldı.')
        return None
    if bugun_paylasilan(gecmis, simdi) + 2 > YOUTUBE_GUNLUK:   # +1 bu video, +1 akşam videosu
        print('Bugünkü YouTube yükleme kotası dolmak üzere; haftalık video atlandı.')
        return None
    son = next(((g.get('anahtar') or '').split(':')[1] for g in reversed(gecmis)
                if g.get('tur') == 'haftalik' and (g.get('anahtar') or '').count(':') >= 1), None)
    bas = (SERILER.index(son) + 1) % len(SERILER) if son in SERILER else 0
    for n in range(len(SERILER)):
        seri = SERILER[(bas + n) % len(SERILER)]
        konu = seri_konusu(seri, acik, simdi, docs, logo, gecmis)
        if konu:
            return konu
        print(f'Haftalık dizi atlandı (veri yetersiz): {seri}')
    return None
