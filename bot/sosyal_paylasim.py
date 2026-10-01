"""Günlük sosyal medya paylaşımı: dünün yeni ilanlarından Instagram kartları ve X/Instagram metinleri."""
import json
import re
from collections import Counter
from datetime import datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw

from ilan_gorsel import font, lines
from siniflandir import ETIKET_OGRENIM, kucuk
from site_uret import TR, _bitis

GENISLIK, YUKSEKLIK = 1080, 1350
KOYU, ANA, LIME, BEYAZ, SOLUK = '#102e35', '#174c46', '#c9f395', '#ffffff', '#b6cbcc'
EN_COK_KART = 9
EN_COK_ETIKET = 25  # Instagram 30'u aşarsa yayını reddeder
AYLAR = ('Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık').split()
LOGO = Path(__file__).resolve().parents[1] / 'docs' / 'kamu-logo.png'
ALAN_ADI = re.compile(r'https?:|www\.|\w\.(?:com|net|org|gov|io|tr|me|co)\b|github|kamuilan\.', re.I)


def _gorulme_gunu(ilan):
    try:
        zaman = datetime.fromisoformat(ilan.get('ilk_gorulme') or '')
    except ValueError:
        return None
    if zaman.tzinfo is None:
        zaman = zaman.replace(tzinfo=TR)
    return zaman.astimezone(TR).date()


def sec(ilanlar, simdi):
    """Dün ilk görülen, iptal/düzeltme olmayan, süresi geçmemiş ilanlar; en yakın son tarih önce."""
    bugun = simdi.astimezone(TR).date()
    dun = bugun - timedelta(days=1)
    referans = datetime.combine(bugun, time(10, 30), tzinfo=TR)  # paylaşım anı; üretim anından bağımsız
    uygun = []
    for ilan in ilanlar:
        if ilan.get('duyuru_turu') or _gorulme_gunu(ilan) != dun:
            continue
        bitis = _bitis(ilan)
        if bitis and bitis <= referans:
            continue
        uygun.append(ilan)
    uygun.sort(key=lambda i: (not i.get('son_tarih'), i.get('son_tarih') or '', i.get('ilk_gorulme') or '', i.get('id') or ''))
    return uygun


def _gg_aa(ilan, yil=True):
    bitis = _bitis(ilan)
    return bitis.astimezone(TR).strftime('%d.%m.%Y' if yil else '%d.%m') if bitis else ''



def _baslik_bicimi(metin):
    """Tamamı büyük harfli kurum/başlık metnini okunur Türkçe başlık biçimine çevirir."""
    metin = ' '.join(str(metin or '').split())
    if not metin.isupper():
        return metin
    sonuc = []
    for kelime in kucuk(metin).split(' '):
        parcalar = []
        for parca in kelime.split('-'):
            ilk = parca[:1].replace('i', 'İ').replace('ı', 'I').upper()
            parcalar.append(ilk + parca[1:])
        sonuc.append('-'.join(parcalar))
    return ' '.join(sonuc)


def _kurumu_at(kurum, baslik):
    """Başlık kurum adıyla başlıyorsa (büyük/küçük harf ve noktalama fark etmez) kurumu atar."""
    hedef = kucuk(kurum)
    if hedef:
        for n in range(1, min(len(baslik), len(kurum) + 8) + 1):
            if kucuk(baslik[:n]) == hedef:
                return baslik[n:].lstrip(' -–—:') or baslik
    return baslik


def _kisalt(metin, uzunluk):
    metin = ' '.join(str(metin or '').split())
    return metin if len(metin) <= uzunluk else metin[:uzunluk - 1].rstrip() + '…'


def _il_metni(ilan):
    return ', '.join(ilan.get('iller') or [])


def _kaynak(ilan):
    kaynaklar = ilan.get('kaynaklar') or []
    return (kaynaklar[0].get('ad') if kaynaklar else '') or ''


def _tarih_yazi(gun):
    return f'{gun.day} {AYLAR[gun.month - 1]} {gun.year}'


def _logo_yapistir(im, d, merkez_x, ust, kutu):
    if not LOGO.exists():
        return
    with Image.open(LOGO) as logo:
        logo = logo.convert('RGBA')
        oran = min(1.0, (kutu - 40) / max(logo.size))
        logo = logo.resize((max(1, round(logo.width * oran)), max(1, round(logo.height * oran))), Image.Resampling.LANCZOS)
    d.rounded_rectangle((merkez_x - kutu // 2, ust, merkez_x + kutu // 2, ust + kutu), radius=28, fill=BEYAZ)
    im.paste(logo, (merkez_x - logo.width // 2, ust + (kutu - logo.height) // 2), logo)


def _jpeg(im):
    for kalite in (88, 82, 76, 70):
        cikti = BytesIO()
        im.save(cikti, format='JPEG', quality=kalite, optimize=False, progressive=False, subsampling=0)
        if cikti.tell() <= 1_000_000:
            break
    return cikti.getvalue()


def kapak_gorseli(sayi, simdi):
    im = Image.new('RGB', (GENISLIK, YUKSEKLIK), KOYU)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 18, YUKSEKLIK), fill=LIME)
    d.rectangle((0, YUKSEKLIK - 260, GENISLIK, YUKSEKLIK), fill=ANA)
    _logo_yapistir(im, d, GENISLIK // 2, 120, 260)
    d.text((GENISLIK // 2, 470), 'KAMU İLAN TAKİP', font=font(40, True), fill=LIME, anchor='mm')
    for n, satir in enumerate(('Bugünün yeni', 'kamu ilanları')):
        d.text((GENISLIK // 2, 600 + n * 100), satir, font=font(88, True), fill=BEYAZ, anchor='mm')
    d.text((GENISLIK // 2, 860), _tarih_yazi(simdi.astimezone(TR).date()), font=font(46), fill=SOLUK, anchor='mm')
    d.rounded_rectangle((250, 940, 830, 1060), radius=60, fill=LIME)
    d.text((GENISLIK // 2, 1000), f'{sayi} yeni ilan', font=font(58, True), fill=KOYU, anchor='mm')
    d.text((GENISLIK // 2, 1170), 'Kaydırarak incele', font=font(36, True), fill=BEYAZ, anchor='mm')
    d.text((GENISLIK // 2, 1230), 'Kariyer Kapısı · İŞKUR · SBB · ÇŞB', font=font(28), fill=SOLUK, anchor='mm')
    return _jpeg(im)


def _norm(metin):
    """Tekrar karşılaştırması için: küçük harf, noktalama ve boşluk farkı yok sayılır."""
    return ' '.join(re.sub(r'[^\w]+', ' ', kucuk(str(metin or ''))).split())


DUZEY_ADI = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
KPSS_ADI = {'kpss': 'KPSS puanı ile', 'kpsssiz': 'KPSS şartı yok'}


def _kart_alanlari(ilan, baslik):
    kadro = _baslik_bicimi(ilan.get('kadro'))
    if kadro and _norm(kadro) in _norm(baslik):
        kadro = ''
    duzey = ', '.join(DUZEY_ADI[d] for d in ilan.get('ogrenim') or [] if d in DUZEY_ADI)
    alanlar = [('KADRO', kadro, 3), ('GÖREV YERİ', _il_metni(ilan), 2), ('ÖĞRENİM', duzey, 1),
               ('KPSS', KPSS_ADI.get(ilan.get('kpss'), ''), 1), ('SON BAŞVURU', _gg_aa(ilan), 1),
               ('KAYNAK', _kaynak(ilan), 1)]
    return [(e, str(d), n) for e, d, n in alanlar if d]


def kart_gorseli(ilan, sira, toplam):
    im = Image.new('RGB', (GENISLIK, YUKSEKLIK), KOYU)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 18, YUKSEKLIK), fill=LIME)
    d.text((70, 70), 'KAMU İLAN TAKİP', font=font(30, True), fill=LIME)
    sayac = f'{sira} / {toplam}'
    d.text((GENISLIK - 70 - d.textlength(sayac, font=font(30, True)), 70), sayac, font=font(30, True), fill=SOLUK)
    kurum = _baslik_bicimi(ilan.get('kurum'))
    baslik = _baslik_bicimi(ilan.get('baslik'))
    baslik = _kurumu_at(kurum, baslik)
    alanlar = _kart_alanlari(ilan, baslik)
    ust, alt = 140, YUKSEKLIK - 190
    for olcek in (1.0, 0.9, 0.8, 0.7, 0.6):
        f_kurum, f_baslik, f_alan, f_etiket = (font(round(46 * olcek), True), font(round(64 * olcek), True),
                                               font(round(40 * olcek), True), font(round(24 * olcek), True))
        satir_kurum = lines(d, kurum, f_kurum, 940, 3)
        satir_baslik = lines(d, baslik, f_baslik, 940, 4)
        blok_alanlar = [(e, lines(d, v, f_alan, 940, n)) for e, v, n in alanlar]
        h_kurum, h_baslik, h_alan = round(58 * olcek), round(76 * olcek), round(50 * olcek)
        yukseklik = (len(satir_kurum) * h_kurum + 40 + len(satir_baslik) * h_baslik + 50
                     + sum(round(38 * olcek) + len(s) * h_alan + 24 for _, s in blok_alanlar))
        if yukseklik <= alt - ust:
            break
    y = ust + max(0, (alt - ust - yukseklik) // 2)
    for satir in satir_kurum:
        d.text((70, y), satir, font=f_kurum, fill=LIME)
        y += h_kurum
    y += 10
    d.line((70, y, GENISLIK - 70, y), fill='#35515a', width=3)
    y += 30
    for satir in satir_baslik:
        d.text((70, y), satir, font=f_baslik, fill=BEYAZ)
        y += h_baslik
    y += 50
    for etiket, satirlar in blok_alanlar:
        d.text((70, y), etiket, font=f_etiket, fill=SOLUK)
        y += round(38 * olcek)
        for satir in satirlar:
            d.text((70, y), satir, font=f_alan, fill=BEYAZ)
            y += h_alan
        y += 24
    d.rectangle((0, YUKSEKLIK - 150, GENISLIK, YUKSEKLIK), fill=ANA)
    d.text((GENISLIK // 2, YUKSEKLIK - 100), 'Ayrıntılar ve başvuru bağlantısı:', font=font(30), fill=BEYAZ, anchor='mm')
    d.text((GENISLIK // 2, YUKSEKLIK - 55), 'profildeki bağlantı', font=font(34, True), fill=LIME, anchor='mm')
    return _jpeg(im)


def x_agirlik(metin):
    """X ağırlıklı sayımı: emoji (BMP dışı ya da sembol bloğu) 2, diğer karakterler 1."""
    return sum(2 if ord(c) > 0xFFFF or 0x2600 <= ord(c) <= 0x27BF else 1 for c in metin)


def x_metni(secilen, sayi):
    etiketler = '#kamuilan #kpss'
    giris = f'📢 Bugün {sayi} yeni kamu ilanı'
    son = 'Ayrıntılar profilde.'
    maddeler, gorulen = [], set()
    for ilan in secilen:
        kurum = _baslik_bicimi(ilan.get('kurum'))
        madde = '• ' + _kisalt(kurum, 48)
        if _norm(kurum) in gorulen or ALAN_ADI.search(madde):
            continue
        gorulen.add(_norm(kurum))
        maddeler.append(madde)
        if len(maddeler) == 3:
            break
    while True:
        metin = '\n'.join([giris, *maddeler, son, etiketler])
        if x_agirlik(metin) <= 260 or not maddeler:
            return metin
        maddeler.pop()


def ig_metni(secilen, sayi, tarih):
    giris = f'📢 {_tarih_yazi(tarih)} — dün eklenen {sayi} yeni kamu ilanı:'
    son = 'Tüm ilanlar ve başvuru bağlantıları profildeki bağlantıda.'
    sabit = ['#kamuilanları', '#kpss', '#memuralımı', '#kamupersonel']
    sayac = Counter()
    for ilan in secilen:
        sayac.update('#' + il for il in ilan.get('iller') or [])
        sayac.update(ETIKET_OGRENIM[d] for d in ilan.get('ogrenim') or [] if d in ETIKET_OGRENIM)
    ekler = sorted(sayac, key=lambda e: (-sayac[e], e))
    etiketler = ' '.join(list(dict.fromkeys(sabit + ekler))[:EN_COK_ETIKET])
    maddeler = []
    for ilan in secilen:
        tarih_kisa = _gg_aa(ilan, yil=False)
        ek = f' (son başvuru {tarih_kisa})' if tarih_kisa else ''
        kurum = _baslik_bicimi(ilan.get('kurum'))
        baslik = _baslik_bicimi(ilan.get('baslik'))
        baslik = _kurumu_at(kurum, baslik) if baslik != kurum else ''
        ayrac = ' — ' + _kisalt(baslik, 110) if baslik else ''
        maddeler.append(f'• {_kisalt(kurum, 60)}{ayrac}{ek}')
    while True:
        metin = '\n\n'.join([giris, '\n'.join(maddeler), son, etiketler])
        if len(metin) <= 2200 or not maddeler:
            return metin[:2200]
        maddeler.pop()


def uret(ilanlar, simdi, cikti_kok, site_url):
    """docs/paylasim/<bugün>/ görsellerini ve docs/paylasim/gunluk.json dosyasını yazar; sözlüğü döndürür."""
    simdi = simdi.astimezone(TR) if simdi.tzinfo else simdi.replace(tzinfo=TR)
    bugun = simdi.date().isoformat()
    kok = Path(cikti_kok) / 'paylasim'
    klasor = kok / bugun
    klasor.mkdir(parents=True, exist_ok=True)
    for eski in list(klasor.glob('*.jpg')):
        eski.unlink()
    uygun = sec(ilanlar, simdi)
    secilen = uygun[:EN_COK_KART]
    sayi = len(uygun)
    if not secilen:
        veri = {'tarih': bugun, 'bos': True, 'ilan_sayisi': 0, 'gorseller': [], 'ig_metin': '', 'x_metin': ''}
    else:
        dosyalar = [('00-kapak.jpg', kapak_gorseli(sayi, simdi))]
        for n, ilan in enumerate(secilen, 1):
            dosyalar.append((f'{n:02d}.jpg', kart_gorseli(ilan, n, len(secilen))))
        for ad, icerik in dosyalar:
            (klasor / ad).write_bytes(icerik)
        taban = site_url.rstrip('/') + '/paylasim/' + bugun + '/'
        veri = {'tarih': bugun, 'bos': False, 'ilan_sayisi': sayi, 'gorseller': [taban + ad for ad, _ in dosyalar],
                'ig_metin': ig_metni(secilen, sayi, simdi.date()), 'x_metin': x_metni(secilen, sayi)}
    (kok / 'gunluk.json').write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding='utf-8')
    return veri
