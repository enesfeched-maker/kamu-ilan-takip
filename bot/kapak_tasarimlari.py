"""Instagram günlük carousel kapağı için 3 tasarım (manşet, mozaik, kaçırma) (1080x1350, 4:5). Hepsi aynı imza: f(secilen, sayi, simdi) -> PIL.Image (RGB).
Yalnız kayıttaki veriden kanca türetilir; eksik veri varsa başka metne düşer, '0 kadro' ya da boş alan çizilmez."""
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from kart_tasarimlari import (ACIK, ANA, F, G, KENAR, KIRMIZI, LIME, PETROL, SOLUK, TURUNCU, Y, AYLAR, TR, _kurum_adi,
                              gecis, logo_kare, sigdir, tek_satir, tr_buyuk, veri)
from meslek_gorseli import GENEL_PERSONEL, _foto_yukle, meslek_no, norm

LOGO = Path(__file__).resolve().parents[1] / 'docs' / 'assets' / 'logo-512.png'  # yeni marka logosu (siyah yuvarlak kare, lime K)
SARI = '#f5c400'
SIYAH = '#111417'
# Verideki meslekler 6 kareyi doldurmazsa, bu sırayla (genel personel hariç) fotoğraf eklenir.
YEDEK_FOTO = [3, 2, 14, 19, 1, 7, 8, 10, 15, 11, 21, 5, 17, 9]


# ---------------------------------------------------------------- veri kancaları
def _sayi_yazi(n):
    return f'{n:,}'.replace(',', '.')


def _bitis(ilan):
    deger = ilan.get('son_zaman') or ilan.get('son_tarih')
    if not deger:
        return None
    try:
        bitis = datetime.fromisoformat(deger)
    except ValueError:
        return None
    if bitis.tzinfo is None:
        bitis = bitis.replace(tzinfo=TR, hour=23, minute=59)
    return bitis.astimezone(TR)


def _kurum(ilan):
    return re.sub(r'^T\.?\s?C\.?\s+', '', _kurum_adi(ilan.get('kurum') or ilan.get('baslik') or '')).strip()


def _veri(ilan, simdi):
    """veri() + kadro adlarındaki 'alacak/alınacak' gibi başlık artıkları temizlenir. simdi verilir: saate bağımlılık yok."""
    v = veri(ilan, simdi=simdi)
    for k in v['kadrolar']:
        k['ad'] = re.sub(r'\s+(?:alacak|alınacak|alım|alim)\b.*$', '', k['ad'], flags=re.I).strip() or k['ad']
    return v


def _kancalar(secilen, simdi):
    """Ortak kancalar: toplam kadro, en büyük alım (kurum, adet, kadro adı), fotoğraf numaraları, meslek adları."""
    vs = [(i, _veri(i, simdi)) for i in secilen]
    toplam = sum(v['toplam'] or 0 for _, v in vs)
    en_buyuk = max(vs, key=lambda x: x[1]['toplam'] or 0) if vs else None
    if en_buyuk and not (en_buyuk[1]['toplam'] or 0):
        en_buyuk = vs[0]
    agirlik, adlar = {}, {}
    for ilan, v in vs:
        if v['kadrolar']:
            for k in v['kadrolar']:
                agirlik[k['no']] = agirlik.get(k['no'], 0) + (k['adet'] or 1)
                adlar.setdefault(k['ad'], k['adet'] or 1)
        else:
            no = meslek_no(v['baslik_ozeti'])
            agirlik[no] = agirlik.get(no, 0) + 1
    nolar = [n for n, _ in sorted(agirlik.items(), key=lambda x: -x[1]) if n != GENEL_PERSONEL]
    return {'vs': vs, 'toplam': toplam or None, 'en_buyuk': en_buyuk, 'nolar': nolar,
            'adlar': [a for a, _ in sorted(adlar.items(), key=lambda x: -x[1])]}


def _foto_listesi(nolar, adet):
    liste = list(nolar[:adet])
    for no in YEDEK_FOTO:
        if len(liste) >= adet:
            break
        if no not in liste:
            liste.append(no)
    return liste


def _tarih_etiketi(simdi):
    g = simdi.astimezone(TR).date()
    return f'{g.day} {AYLAR[g.month - 1]} {g.year}'


# ---------------------------------------------------------------- çizim yardımcıları
def _kare_foto(no, boy):
    """Meslek fotoğrafı (192 px) boy x boy kareye büyütülür, hafif keskinleştirilir; yoksa None."""
    foto = _foto_yukle(no)
    if foto is None:
        return None
    return foto.resize((boy, boy), Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=110, threshold=2))


def _kapla(foto, w, h):
    """Fotoğrafı w x h alanı kaplayacak şekilde büyütüp ortadan keser."""
    olcek = max(w / foto.width, h / foto.height)
    buyuk = foto.resize((round(foto.width * olcek), round(foto.height * olcek)), Image.Resampling.LANCZOS)
    x, y = (buyuk.width - w) // 2, (buyuk.height - h) // 2
    return buyuk.crop((x, y, x + w, y + h))


def _marka_seridi(im, d, y=None, dolgu=PETROL, sag_metin='Kaydır', yuk=104):
    """Alt şerit: küçük logo + KAMU İLAN TAKİP solda, sağda kaydır çağrısı. Tüm kapaklarda aynı yer."""
    y = Y - yuk if y is None else y
    d.rectangle((0, y, G, Y), fill=dolgu)
    x = KENAR
    if LOGO.exists():
        kutu = 68
        logo = logo_kare(kutu)
        ky = y + (yuk - kutu) // 2
        im.paste(logo, (x, ky), logo)
        # siyah logo koyu şeritlerde (PETROL/SIYAH) kaybolmasın: ince lime çerçeve
        d.rounded_rectangle((x, ky, x + kutu - 1, ky + kutu - 1), radius=round(kutu * 0.22), outline=LIME, width=2)
        x += kutu + 20
    d.text((x, y + yuk / 2 + 1), 'KAMU İLAN TAKİP', font=F(34, True), fill=LIME, anchor='lm')
    if sag_metin:  # ok işareti yazı tipinde yok: çizgiyle çizilir
        cy, ax = y + yuk / 2 + 1, G - KENAR
        d.line((ax - 50, cy, ax, cy), fill='#ffffff', width=6)
        d.line((ax - 20, cy - 18, ax, cy, ax - 20, cy + 18), fill='#ffffff', width=6, joint='curve')
        d.text((ax - 70, cy), sag_metin, font=F(36, True), fill='#ffffff', anchor='rm')


def _cip_orta(d, cx, y, metin, dolgu, yazi, boy=34, yuk=64, cizgi=None, sol=False):
    """Hap etiket (cx merkez; sol=True ise cx sol kenar); genişliği döndürür."""
    yz = F(boy, True)
    w = round(d.textlength(metin, font=yz)) + 52
    x0 = cx if sol else cx - w / 2
    d.rounded_rectangle((x0, y, x0 + w, y + yuk), radius=yuk // 2, fill=dolgu, outline=cizgi, width=3 if cizgi else 0)
    d.text((x0 + w / 2, y + yuk / 2 + 1), metin, font=yz, fill=yazi, anchor='mm')
    return w


GENEL_ADLAR = {'sozlesmeli personel', 'meslek personeli', 'personel', 'uzman yardimcisi', 'kadrolu personel', 'isci', 'memur'}


def _temiz_adlar(adlar, genel_ele=True, en_uzun=30):
    """Çip metinleri: virgülden sonrası atılır, rakam içeren/çok uzun/genel adlar elenir, tekrarlar bir kez."""
    sonuc, gorulen = [], set()
    for ad in adlar:
        ad = ' '.join(str(ad).split(',')[0].split())
        anahtar = norm(ad)
        if not ad or re.search(r'\d', ad) or len(ad) > en_uzun or anahtar in gorulen or (genel_ele and anahtar in GENEL_ADLAR):
            continue
        gorulen.add(anahtar)
        sonuc.append(ad)
    return sonuc


# ---------------------------------------------------------------- manşet
def manset_basligi(ilan, v, sayi):
    """'<Kurum> <N> <kadro> alıyor'. Kadro adedi yoksa toplam, ad yoksa 'personel'; kurum yoksa genel cümle."""
    kurum = _kurum(ilan) if ilan else ''
    if not kurum:
        return f'Bugün {sayi} yeni kamu ilanı yayınlandı'
    ana = max(v['kadrolar'], key=lambda x: x['adet'] or 0) if v and v['kadrolar'] else None
    adet = (ana['adet'] if ana else None) or (v['toplam'] if v else None)
    if ana:
        return f'{kurum} {adet} {ana["ad"]} alıyor' if adet else f'{kurum} {ana["ad"]} alıyor'
    if adet:
        return f'{kurum} {adet} personel alıyor'
    return f'{kurum} yeni ilan yayınladı'


def manset(secilen, sayi, simdi):
    k = _kancalar(secilen, simdi)
    im = Image.new('RGB', (G, Y), PETROL)
    ust_h = 790
    ilan, v = k['en_buyuk'] if k['en_buyuk'] else (None, None)
    no = None
    if v and v['kadrolar']:
        ana = max(v['kadrolar'], key=lambda x: x['adet'] or 0)
        no = ana['no'] if ana['no'] != GENEL_PERSONEL else None
    no = no or (k['nolar'][0] if k['nolar'] else GENEL_PERSONEL)
    boy = ust_h - 96
    foto = _kare_foto(no, boy)
    if foto is not None:
        kare = foto.convert('RGBA')
        for yon, a, b in (('sol', 0.0, 0.55), ('alt', 0.0, 0.18)):
            kare.alpha_composite(gecis((boy, boy), yon, PETROL, a, b))
        im.paste(kare, (G - boy, 96), kare)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, G, 96), fill=KIRMIZI)
    d.rectangle((0, 0, 330, 96), fill=SARI)
    d.text((KENAR, 50), 'YENİ İLAN', font=F(48, True), fill=SIYAH, anchor='lm')
    d.text((G - KENAR, 50), tr_buyuk(_tarih_etiketi(simdi)), font=F(30, True), fill='#ffffff', anchor='rm')
    d.text((KENAR, 150), 'GÜNÜN ÖNE ÇIKAN İLANI', font=F(28, True), fill=LIME, anchor='lm')
    # beyaz manşet alanı
    d.rectangle((0, ust_h, G, Y), fill='#ffffff')
    d.rectangle((0, ust_h, G, ust_h + 12), fill=KIRMIZI)
    baslik = manset_basligi(ilan, v, sayi)
    satirlar, yz = sigdir(d, baslik, True, [80, 72, 64, 58, 52], G - 2 * KENAR, 3)
    lh = round(yz.size * 1.14)
    y = ust_h + 44
    for s in satirlar:
        d.text((KENAR, y), s, font=yz, fill=SIYAH)
        y += lh
    kalan = sayi - 1
    ry = 1148
    if kalan > 0:
        w = _cip_orta(d, KENAR, ry, f'+ {kalan} ilan daha', PETROL, LIME, boy=38, yuk=76, sol=True)
        if k['toplam']:
            d.text((KENAR + w + 28, ry + 39), f'toplam {_sayi_yazi(k["toplam"])} kadro', font=F(34, True), fill='#5d6f72', anchor='lm')
    elif v and v['kalan_yazi']:
        _cip_orta(d, KENAR, ry, v['kalan_yazi'], PETROL, LIME, boy=38, yuk=76, sol=True)
    _marka_seridi(im, d, y=Y - 80, yuk=80)
    return im


# ---------------------------------------------------------------- mozaik
def mozaik(secilen, sayi, simdi):
    k = _kancalar(secilen, simdi)
    im = Image.new('RGB', (G, Y), PETROL)
    nolar = _foto_listesi(k['nolar'], 6)
    kare = G // 3
    for n, no in enumerate(nolar):
        foto = _kare_foto(no, kare)
        if foto is None:
            continue
        im.paste(foto, ((n % 3) * kare, (n // 3) * kare))
    d = ImageDraw.Draw(im)
    for i in (1, 2):  # ince ayraçlar
        d.line((i * kare, 0, i * kare, 2 * kare), fill=PETROL, width=6)
    d.line((0, kare, G, kare), fill=PETROL, width=6)
    d.rectangle((0, 2 * kare - 3, G, Y), fill=PETROL)
    cy, r = 2 * kare, 212
    d.ellipse((G // 2 - r - 14 + 6, cy - r - 14 + 12, G // 2 + r + 14 + 6, cy + r + 14 + 12), fill='#08181c')
    d.ellipse((G // 2 - r - 14, cy - r - 14, G // 2 + r + 14, cy + r + 14), fill=LIME)
    d.ellipse((G // 2 - r, cy - r, G // 2 + r, cy + r), fill='#ffffff')
    d.text((G // 2, cy - 118), 'BUGÜN', font=F(46, True), fill=ANA, anchor='mm')
    yz, metin = tek_satir(d, str(sayi), [230, 200, 170, 140], 2 * r - 90, True)
    d.text((G // 2, cy - 2), metin, font=yz, fill=PETROL, anchor='mm')
    d.text((G // 2, cy + 120), 'YENİ İLAN', font=F(46, True), fill=ANA, anchor='mm')
    # meslek çipleri
    adlar = _temiz_adlar(k['adlar'])
    meslek = len(adlar) >= 2
    if not meslek:  # temiz meslek adı yetmezse kurum adlarına düşer; o da yetmezse satır çizilmez
        adlar = _temiz_adlar([_kurum(i) for i in secilen], genel_ele=False)
    if len(adlar) < 2:
        adlar = []
    if adlar:
        d.text((G // 2, cy + r + 62), 'BUGÜN İLAN ÇIKAN MESLEKLER' if meslek else 'İLAN VEREN KURUMLAR', font=F(30, True), fill=SOLUK, anchor='mm')
    yz = F(32, True)
    satirlar, mevcut, w_mevcut = [], [], 0
    for ad in adlar:
        w = round(d.textlength(ad, font=yz)) + 44
        if mevcut and w_mevcut + 14 + w > G - 2 * KENAR:
            satirlar.append(mevcut)
            mevcut, w_mevcut = [], 0
        if len(satirlar) == 2:
            break
        mevcut.append((ad, w))
        w_mevcut += w + (14 if len(mevcut) > 1 else 0)
    if mevcut and len(satirlar) < 2:
        satirlar.append(mevcut)
    y = cy + r + 100
    for satir in satirlar:
        toplam_w = sum(w for _, w in satir) + 14 * (len(satir) - 1)
        x = (G - toplam_w) / 2
        for ad, w in satir:
            d.rounded_rectangle((x, y, x + w, y + 58), radius=29, fill=ANA, outline=LIME, width=2)
            d.text((x + w / 2, y + 30), ad, font=yz, fill='#ffffff', anchor='mm')
            x += w + 14
        y += 72
    _marka_seridi(im, d)
    return im


# ---------------------------------------------------------------- kaçırma
def _en_yakin(secilen, simdi):
    """(ilan listesi, 'g Ay', kalan gün, bitiş) en yakın son başvuru günündeki ilanlar; yoksa None."""
    bugun = simdi.astimezone(TR).date()
    adaylar = [(_bitis(i), i) for i in secilen]
    adaylar = [(b, i) for b, i in adaylar if b and b.date() >= bugun]
    if not adaylar:
        return None
    ilk = min(b.date() for b, _ in adaylar)
    gun_ilanlari = [i for b, i in adaylar if b.date() == ilk]
    return gun_ilanlari, f'{ilk.day} {AYLAR[ilk.month - 1]}', (ilk - bugun).days, ilk


def _takvim(d, x, y, w, h, ay, gun):
    d.rounded_rectangle((x + 8, y + 12, x + w + 8, y + h + 12), radius=30, fill='#000000')
    d.rounded_rectangle((x, y, x + w, y + h), radius=30, fill='#ffffff')
    ust = 104
    d.rounded_rectangle((x, y, x + w, y + ust), radius=30, fill=KIRMIZI)
    d.rectangle((x, y + ust - 30, x + w, y + ust), fill=KIRMIZI)
    d.text((x + w / 2, y + ust / 2 + 2), tr_buyuk(ay), font=F(50, True), fill='#ffffff', anchor='mm')
    for cx in (x + 70, x + w - 70):
        d.rounded_rectangle((cx - 9, y - 20, cx + 9, y + 34), radius=9, fill=SIYAH)
    yz, metin = tek_satir(d, str(gun), [220, 190, 160], w - 40, True)
    d.text((x + w / 2, y + ust + (h - ust) / 2 + 4), metin, font=yz, fill=SIYAH, anchor='mm')


def kacirma(secilen, sayi, simdi):
    im = Image.new('RGB', (G, Y), SIYAH)
    d = ImageDraw.Draw(im)
    for bant_y in (0, Y - 104 - 40):  # uyarı şeridi (üst ve marka şeridi üstü)
        for x in range(-60, G + 60, 80):
            d.polygon([(x, bant_y + 40), (x + 40, bant_y + 40), (x + 80, bant_y), (x + 40, bant_y)], fill=SARI)
    yz, metin = tek_satir(d, 'KAÇIRMA!', list(range(250, 120, -10)), G - 2 * KENAR, True)
    d.text((KENAR, 230), metin, font=yz, fill=SARI, anchor='lm')
    en = _en_yakin(secilen, simdi)
    bugun = simdi.astimezone(TR).date()
    cx0, cy0, cw, ch = KENAR, 400, 340, 380
    if en:
        gun_ilanlari, tarih_yazi, kalan, ilk = en
        _takvim(d, cx0, cy0, cw, ch, AYLAR[ilk.month - 1], ilk.day)
        tx = cx0 + cw + 48
        d.text((tx, cy0 + 40), 'SON BAŞVURU', font=F(32, True), fill=SOLUK, anchor='lm')
        d.text((tx, cy0 + 106), tarih_yazi, font=F(76, True), fill='#ffffff', anchor='lm')
        kurumlar = list(dict.fromkeys(_kurum(i) for i in gun_ilanlari))
        ks, yk = sigdir(d, kurumlar[0], True, [44, 40, 36, 32], G - KENAR - tx, 2)  # kelime ortasında bölünmez
        yy = cy0 + 160
        for s in ks:
            d.text((tx, yy), s, font=yk, fill=SARI)
            yy += round(yk.size * 1.18)
        if len(kurumlar) > 1:
            d.text((tx, yy + 2), f'+ {len(kurumlar) - 1} kurum daha', font=F(30), fill=SOLUK)
        etiket = 'Bugün son gün' if kalan <= 0 else 'Yarın son gün' if kalan == 1 else f'{kalan} gün kaldı'
        _cip_orta(d, tx, cy0 + ch - 76, etiket, KIRMIZI, '#ffffff', boy=38, yuk=76, sol=True)
        hafta = [i for i in secilen if _bitis(i) and 0 <= (_bitis(i).date() - bugun).days <= 7]
        if hafta:
            _cip_orta(d, G // 2, 880, f'Bu hafta biten {len(hafta)} ilan', SARI, SIYAH, boy=54, yuk=104)
            d.text((G // 2, 1040), 'Son güne bırakma, başvurunu şimdi planla', font=F(36), fill=SOLUK, anchor='mm')
        else:
            d.text((G // 2, 900), f'Bugün {sayi} yeni kamu ilanı yayınlandı', font=F(44, True), fill='#ffffff', anchor='mm')
            d.text((G // 2, 970), 'Son güne bırakma, başvurunu şimdi planla', font=F(36), fill=SOLUK, anchor='mm')
    else:
        _takvim(d, cx0, cy0, cw, ch, AYLAR[bugun.month - 1], bugun.day)
        tx = cx0 + cw + 48
        d.text((tx, cy0 + 60), 'BUGÜN', font=F(32, True), fill=SOLUK, anchor='lm')
        ks, yk = sigdir(d, f'{sayi} yeni kamu ilanı yayında', True, [60, 54, 48], G - KENAR - tx, 4)
        yy = cy0 + 110
        for s in ks:
            d.text((tx, yy), s, font=yk, fill='#ffffff')
            yy += round(yk.size * 1.2)
        d.text((G // 2, 920), 'Son güne bırakma, başvurunu şimdi planla', font=F(36), fill=SOLUK, anchor='mm')
    _marka_seridi(im, d, dolgu=SIYAH)
    d.rectangle((0, Y - 104, G, Y - 102), fill=SARI)
    return im


TASARIMLAR = {'manset': manset, 'mozaik': mozaik, 'kacirma': kacirma}
SIRA = ['manset', 'mozaik', 'kacirma']


def kapak_sec(secilen, simdi):
    """Günün kapak tasarımının adı; deterministik. Sıra günle döner, ilk uygun olan seçilir (mozaik her zaman uygun)."""
    bugun = simdi.astimezone(TR).date()
    en_buyuk = max((_veri(i, simdi)['toplam'] or 0 for i in secilen), default=0)
    yakin = any(b and 0 <= (b.date() - bugun).days <= 3 for b in (_bitis(i) for i in secilen))
    uygun = {'manset': en_buyuk >= 10, 'mozaik': True, 'kacirma': yakin}
    kayma = bugun.toordinal() % 3
    for ad in SIRA[kayma:] + SIRA[:kayma]:
        if uygun[ad]:
            return ad

