"""Instagram / TikTok / YouTube Shorts kareleri (1080x1350) ve dikey video (1080x1920).

Biçim, alandaki en çok izlenen hesaplardan (17 Ekim 2026 araştırması): sarı zemin, kırmızı çerçeve,
siyah kutuda iri büyük harfli başlık, üstte kurum logoları. Kareler PIL Image döner."""
import io
import re
import subprocess

from PIL import Image, ImageDraw

import kart_tasarimlari as k
from kart_tasarimlari import F, AYLAR

W, H = 1080, 1350
VW, VH, FPS = 1080, 1920, 30
SARI, KIRMIZI, SIYAH, BEYAZ = '#ffd60a', '#e10600', '#111111', '#ffffff'
CERCEVE = 22
MARKA_H = 96


def kisa_kurum(kurum):
    s = k._kurum_adi(kurum)
    s = re.sub(r'\s+Rektörlüğü$', '', s, flags=re.I)
    s = re.sub(r'\s+Belediye Başkanlığı$', ' Belediyesi', s, flags=re.I)
    s = re.sub(r'\s+(İdaresi|Kurumu) Başkanlığı$', r' \1', s, flags=re.I)
    s = re.sub(r'\s+Genel Sekreterliği$', '', s, flags=re.I)
    return s


def tarih_yaz(gun):
    return f'{gun.day} {AYLAR[gun.month - 1]}'


def _tuval():
    im = Image.new('RGB', (W, H), SARI)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, H - 1), outline=KIRMIZI, width=CERCEVE)
    return im, d


def _marka(im, d):
    y = H - CERCEVE - MARKA_H
    d.rectangle((CERCEVE, y, W - CERCEVE, H - CERCEVE), fill=SIYAH)
    logo = k.logo_kare(64)
    if logo is not None:
        im.paste(logo, (60, y + 16), logo)
    d.text((140, y + MARKA_H / 2), 'kpsstercihi.com', font=F(38, True), fill=SARI, anchor='lm')
    d.text((W - 60, y + MARKA_H / 2), 'Telegram: @kpsstercihi', font=F(30, True), fill=BEYAZ, anchor='rm')


def _kutu(d, y, satirlar, boy, vurgu=(), ic=44):
    """Siyah kutuda ortalı iri satırlar; sığmayan satır küçültülür. Kutunun alt y'sini döner."""
    genislik = W - 140
    boy = min([boy] + [b for b in range(boy, 40, -4)
                       if all(d.textlength(s, font=F(b, True)) <= genislik - 40 for s in satirlar)][:1])
    lh = round(boy * 1.12)
    h = ic * 2 + lh * len(satirlar) - (lh - boy)
    d.rounded_rectangle((70, y, W - 70, y + h), radius=18, fill=SIYAH)
    for n, s in enumerate(satirlar):
        d.text((W / 2, y + ic + n * lh), s, font=F(boy, True), fill=SARI if n in vurgu else BEYAZ, anchor='mt')
    return y + h


def _hap(d, y, metin, dolgu=KIRMIZI, yazi=BEYAZ, boy=40, yuk=76):
    yz = F(boy, True)
    w = d.textlength(metin, font=yz) + 70
    d.rounded_rectangle(((W - w) / 2, y, (W + w) / 2, y + yuk), radius=yuk // 2, fill=dolgu)
    d.text((W / 2, y + yuk / 2), metin, font=yz, fill=yazi, anchor='mm')
    return y + yuk


def _logo_daire(im, d, logo, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BEYAZ, outline=SIYAH, width=4)
    k.logo_yerlestir(im, d, {'logo': logo}, (cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10),
                     arka=BEYAZ, yaricap=r, ic=int(r * 0.28))


def _logo_sirasi(im, d, logolar, y=150, r=74):
    logolar = [l for l in logolar if l][:5]
    if not logolar:
        return False
    bas = (W - (len(logolar) * 2 * r + (len(logolar) - 1) * 18)) / 2 + r
    for n, logo in enumerate(logolar):
        _logo_daire(im, d, logo, round(bas + n * (2 * r + 18)), y, r)
    return True


def _ileri(d, y, metin):
    yz = F(44, True)
    w = d.textlength(metin, font=yz)
    d.text((W / 2 - 30, y + 30), metin, font=yz, fill=SIYAH, anchor='mm')
    ox = W / 2 - 30 + w / 2 + 24
    d.polygon([(ox, y + 12), (ox + 30, y + 30), (ox, y + 48)], fill=KIRMIZI)


# ---------------------------------------------------------------- kare türleri
def kapak(satirlar, vurgu=(), rozet='', liste=(), logolar=(), ileri='Kaydırınca hepsini göreceksin'):
    im, d = _tuval()
    y = 290 if _logo_sirasi(im, d, logolar) else 150
    y = _kutu(d, y, satirlar, 92, vurgu)
    if rozet:
        y = _hap(d, y + 40, rozet)
    if liste:
        yz = F(38, True)
        tek = len(liste) <= 4
        for n, s in enumerate(liste):
            x = 90 if tek else 90 + (n % 2) * 470
            yy = y + 50 + (n if tek else n // 2) * 62
            d.rectangle((x, yy + 10, x + 22, yy + 32), fill=KIRMIZI)
            d.text((x + 38, yy), k.lines(d, s, yz, (880 if tek else 410), 1)[0], font=yz, fill=SIYAH)
        y += 50 + (len(liste) if tek else (len(liste) + 1) // 2) * 62
    if ileri:
        _ileri(d, min(y + 30, H - CERCEVE - MARKA_H - 90), ileri)
    _marka(im, d)
    return im


def ilan_karesi(ilan, logo, no, toplam, simdi):
    im, d = _tuval()
    v = k.veri(ilan, logo, simdi)
    d.rounded_rectangle((60, 60, 210, 130), radius=35, fill=SIYAH)
    d.text((135, 95), f'{no}/{toplam}', font=F(40, True), fill=SARI, anchor='mm')
    if logo:
        _logo_daire(im, d, logo, W - 150, 150, 96)
    ad, yz = k.sigdir(d, k.tr_buyuk(kisa_kurum(ilan.get('kurum') or '')), True, [64, 58, 52], W - 380, 2)
    k.blok(d, 60, 175, ad, yz, SIYAH, aralik=round(yz.size * 1.1))
    kad = sorted(v['kadrolar'], key=lambda x: -(x['adet'] or 0))
    satirlar = [f'{x["adet"]} {x["ad"]}' if x['adet'] else x['ad'] for x in kad[:4]]
    if len(kad) > 4:
        satirlar.append(f'+{len(kad) - 4} kadro daha')
    y = 400
    d.rounded_rectangle((60, y, W - 60, y + 110), radius=18, fill=KIRMIZI)
    d.text((W / 2, y + 55), f'{v["toplam"]} KİŞİ ALINACAK' if v['toplam'] else 'ALIM YAPILACAK',
           font=F(64, True), fill=BEYAZ, anchor='mm')
    y += 130
    if satirlar:
        yz = F(44, True)
        h = 40 + 64 * len(satirlar)
        d.rounded_rectangle((60, y, W - 60, y + h), radius=18, fill=SIYAH)
        for n, s in enumerate(satirlar):
            d.text((100, y + 26 + n * 64), k.lines(d, s, yz, W - 200, 1)[0], font=yz, fill=SARI if n == 0 else BEYAZ)
        y += h + 30
    cipler = [c for c in (' · '.join(v['duzeyler']), v['kpss'].split(' · ')[0], v['yer']) if c]
    x = 60
    for c in cipler:
        c = k.lines(d, c, F(34, True), W - 120 - x - 44, 1)[0]
        w = k.cip(d, x, y, c, dolgu=BEYAZ, yazi=SIYAH, boy=34, yuk=66, cizgi=SIYAH)
        x += w + 14
        if x > W - 200:
            break
    y = H - CERCEVE - MARKA_H - 40 - 150
    d.rounded_rectangle((60, y, W - 60, y + 150), radius=18, fill=SIYAH)
    d.text((100, y + 30), 'SON BAŞVURU', font=F(34, True), fill=SARI)
    d.text((100, y + 74), v['tarih'] or '', font=F(52, True), fill=BEYAZ)
    if v['kalan_yazi']:
        yz = F(38, True)
        w = d.textlength(v['kalan_yazi'], font=yz) + 50
        d.rounded_rectangle((W - 100 - w, y + 45, W - 100, y + 105), radius=30, fill=KIRMIZI)
        d.text((W - 100 - w / 2, y + 75), v['kalan_yazi'], font=yz, fill=BEYAZ, anchor='mm')
    _marka(im, d)
    return im


def tablo_karesi(baslik, satirlar, no=None, toplam=None, dipnot=''):
    """satirlar: (ana metin, alt metin, sağdaki değer) üçlüleri; en çok 6."""
    im, d = _tuval()
    y = 60
    if no:
        d.rounded_rectangle((60, y, 210, y + 70), radius=35, fill=SIYAH)
        d.text((135, y + 35), f'{no}/{toplam}', font=F(40, True), fill=SARI, anchor='mm')
        y += 100
    s, yz = k.sigdir(d, baslik, True, [60, 54, 48], W - 120, 2)
    y = k.blok(d, 60, y, s, yz, SIYAH, aralik=round(yz.size * 1.12)) + 20
    alt = H - CERCEVE - MARKA_H - (80 if dipnot else 30)
    satir_h = min(150, (alt - y) // max(1, len(satirlar[:6])))
    for n, (ana, ikinci, deger) in enumerate(satirlar[:6]):
        yy = y + n * satir_h
        d.rounded_rectangle((60, yy, W - 60, yy + satir_h - 16), radius=16, fill=SIYAH if n % 2 == 0 else '#2a2a2a')
        dw = d.textlength(deger, font=F(56, True))
        d.text((W - 96, yy + (satir_h - 16) / 2), deger, font=F(56, True), fill=SARI, anchor='rm')
        gen = W - 96 - dw - 40 - 96
        d.text((96, yy + 22), k.lines(d, ana, F(40, True), gen, 1)[0], font=F(40, True), fill=BEYAZ)
        if ikinci:
            d.text((96, yy + 74), k.lines(d, ikinci, F(30), gen, 1)[0], font=F(30), fill='#d6d6d6')
    if dipnot:
        d.text((W / 2, H - CERCEVE - MARKA_H - 46), dipnot, font=F(28), fill=SIYAH, anchor='mm')
    _marka(im, d)
    return im


def haber_karesi(etiket, manset, alinti='', kaynak='', logolar=(), foto_no=None):
    im, d = _tuval()
    y = 290 if _logo_sirasi(im, d, logolar) else 120
    y = _hap(d, y, etiket) + 30
    y = _kutu(d, y, manset, 84, vurgu=(0,))
    if alinti:
        s, yz = k.sigdir(d, f'“{alinti}”', True, [44, 40, 36], W - 180, 6)
        y = k.blok(d, 90, y + 40, s, yz, SIYAH, aralik=round(yz.size * 1.25))
    if kaynak:
        d.text((90, y + 16), kaynak, font=F(32), fill='#3a3a3a')
        y += 70
    if foto_no is not None:  # meslek fotoğrafı (sağlık = 2) kalan boşluğa, yuvarlak köşeli
        foto, _ = k._afis_foto(foto_no, 0)
        alan = H - CERCEVE - MARKA_H - 30 - (y + 20)
        if foto is not None and alan > 200:
            boy = min(alan, W - 140)
            foto = foto.resize((boy, boy), Image.Resampling.LANCZOS).convert('RGB')
            maske = Image.new('L', (boy, boy), 0)
            ImageDraw.Draw(maske).rounded_rectangle((0, 0, boy - 1, boy - 1), radius=28, fill=255)
            im.paste(foto, ((W - boy) // 2, y + 20), maske)
    _marka(im, d)
    return im


def kapanis():
    im, d = _tuval()
    y = _kutu(d, 300, ['TÜM KAMU İLANLARI', 'TEK YERDE'], 88)
    d.text((W / 2, y + 110), 'kpsstercihi.com', font=F(96, True), fill=SIYAH, anchor='mm')
    _hap(d, y + 200, 'Telegram: @kpsstercihi', boy=44, yuk=80)
    d.text((W / 2, y + 380), 'Takip edersen yeni ilanlar', font=F(48, True), fill=SIYAH, anchor='mm')
    d.text((W / 2, y + 440), 'ilk senin önüne düşer', font=F(48, True), fill=SIYAH, anchor='mm')
    _marka(im, d)
    return im


# ---------------------------------------------------------------- video
ILK_SURE, SONRAKI_SURE = 2.6, 2.1   # kısa video = yüksek izlenme tamamlama oranı (algoritmanın ana ölçütü)


def video_suresi(kare_sayisi, ilk=ILK_SURE, sonraki=SONRAKI_SURE):
    return (int(FPS * ilk) + int(FPS * sonraki) * max(0, kare_sayisi - 1)) / FPS


def video_kareleri(kareler, ilk=ILK_SURE, sonraki=SONRAKI_SURE):
    """Her kare girişte hafif yakınlaşarak oturur; dikey tuvalin ortasında, üst/alt sarı."""
    for n, im in enumerate(kareler):
        sure = ilk if n == 0 else sonraki
        for f in range(int(FPS * sure)):
            t = min(1.0, f / 8)
            olcek = 1.06 - 0.06 * (1 - (1 - t) ** 3)
            w, h = round(W * olcek), round(H * olcek)
            z = Image.new('RGB', (VW, VH), SARI)
            z.paste(im.resize((w, h), Image.Resampling.BILINEAR) if olcek != 1 else im,
                    ((VW - w) // 2, (VH - H) // 2 + (H - h) // 2))
            yield z


def ses_girdisi(muzik, sure):
    """ffmpeg ses girdisi ve filtresi: müzik varsa döngülü, başta 0,4 sn açılıp sonda 1 sn kısılarak biter; yoksa sessiz iz."""
    if not muzik:
        return ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo'], []
    return (['-stream_loop', '-1', '-i', str(muzik)],
            ['-af', f'afade=t=in:d=0.4,afade=t=out:st={max(0.0, sure - 1):.2f}:d=1,volume=0.85'])


def video_yaz(kareler, yol, ffmpeg=None, muzik=None):
    """MP4 (H.264, yuv420p). muzik: telifsiz parça yolu (yoksa sessiz). ffmpeg verilmezse imageio-ffmpeg kullanılır."""
    if ffmpeg is None:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    sure = video_suresi(len(kareler))
    girdi, filtre = ses_girdisi(muzik, sure)
    p = subprocess.Popen([ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                          '-r', str(FPS), '-i', '-', *girdi, '-map', '0:v', '-map', '1:a', *filtre, '-t', f'{sure:.2f}',
                          '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '21', '-c:a', 'aac', '-b:a', '128k',
                          '-movflags', '+faststart', str(yol)], stdin=subprocess.PIPE)
    try:
        for z in video_kareleri(kareler):
            p.stdin.write(z.tobytes())
    finally:
        p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError('ffmpeg video yazamadı')


def png(im):
    b = io.BytesIO()
    im.save(b, format='PNG', optimize=True)
    return b.getvalue()
