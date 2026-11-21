"""Sohbet biçimi: gerçek bir ilan, iki kişinin mesajlaşması üzerinden anlatılır (21 Kasım 2026, kullanıcı onayladı).

Rakiplerin canlandırma + seslendirme kalıbından farklı olarak burada ses yok; izleyici sohbeti okur. Mesajlar sırayla
"yazıyor…" göstergesinden sonra düşer, sohbet aşağı kayar. İlk kare kapaktır (kanca + ilk iki mesaj hazır durur).
Karakterler kurgudur; mesajlardaki her bilgi ilanın kendi şart metninden elle alınmıştır (SENARYOLAR).

Kullanım: python bot/reels_sohbet.py <senaryo|hepsi> [--cikti klasör]"""
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

import kart_tasarimlari as k
import reels as r
from kart_tasarimlari import F
from reels import Sahne, SOL, GEN, yazi, panel, yumusak

# Sohbet ekranı (telefon) yerleşimi
TEL_UST, TEL_ALT = 560, 1560
BASLIK_H = 112
ALAN_UST = TEL_UST + BASLIK_H + 18
ALAN_ALT = TEL_ALT - 24
ALAN_H = ALAN_ALT - ALAN_UST
IC = 28                                   # telefon içi yatay boşluk
BALON_EN = round((GEN - 2 * IC) * 0.78)
YAZI_BOY = 40
ARA = 16
YAZIYOR = 0.8                             # karşı tarafın "yazıyor" süresi (sn)
KAYMA = 0.35

EKRAN = '#f4ede2'                         # sohbet zemini (krem)
GELEN, GELEN_YAZI = '#ffffff', '#1d1530'
SAAT = '#8b8196'

# Video başına renk: zemin (üst, alt) + giden balon / kanca bandı rengi. Yeşil yok (kullanıcı kararı).
RENKLER = {
    'gece': ((34, 20, 58), (17, 9, 32), '#ffb45c', '#21143a', '#6c4bd1'),
    'lacivert': ((9, 26, 66), (5, 18, 48), '#f48067', '#051230', '#1c4286'),
    'kobalt': ((30, 48, 190), (18, 30, 128), '#ffd23f', '#14183a', '#2337e6'),
    'zift': ((24, 26, 28), (10, 11, 12), '#fff200', '#111314', '#3a3d42'),
    'erik': ((74, 18, 66), (40, 8, 38), '#ffc8dd', '#2a0a26', '#8a2a7c'),
    'kiremit': ((128, 40, 22), (84, 22, 10), '#ffe2b8', '#3a1406', '#b5462a'),
}


def renk_sec(ad):
    zu, za, vurgu, vurgu_ustu, avatar = RENKLER[ad]
    r.PALETLER['sohbet-' + ad] = dict(r.PALETLER['gece'], zemin_ust=zu, zemin_alt=za, vurgu=vurgu, vurgu_ustu=vurgu_ustu, soluk='#ece6df',
                                       panel=avatar, cizgi=tuple(min(255, c + 40) for c in zu), cizgi2=tuple(min(255, c + 22) for c in zu))
    r.palet_sec('sohbet-' + ad)
    return vurgu, vurgu_ustu, avatar


def _balon_zemin(w, h, dolgu, giden):
    kat = 3
    im = Image.new('RGBA', (w * kat, h * kat), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * kat - 1, h * kat - 1), radius=34 * kat, fill=dolgu)
    if giden:   # kuyruk tarafındaki alt köşe sivri
        d.rectangle((w * kat - 40 * kat, h * kat - 40 * kat, w * kat - 1, h * kat - 1), fill=dolgu)
    else:
        d.rectangle((0, h * kat - 40 * kat, 40 * kat, h * kat - 1), fill=dolgu)
    return im.resize((w, h), Image.Resampling.LANCZOS)


def balon(metin, giden, saat, renk):
    dolgu, yazi_renk = (renk[0], renk[1]) if giden else (GELEN, GELEN_YAZI)
    saat_renk = _soluk(dolgu, yazi_renk) if giden else SAAT
    yz = F(YAZI_BOY, False)
    satirlar = k.lines(r._OLC, metin, yz, BALON_EN - 64, 8)
    lh = round(YAZI_BOY * 1.24)
    saat_yz = F(26, False)
    w = max(round(r._OLC.textlength(s, font=yz)) for s in satirlar) + 64
    son_w = round(r._OLC.textlength(satirlar[-1], font=yz)) + 64
    saat_w = round(r._OLC.textlength(saat, font=saat_yz)) + 20
    h = 30 + lh * len(satirlar) + 26
    if son_w + saat_w > BALON_EN:      # saat son satıra sığmıyorsa alta in
        h += 30
    else:
        w = max(w, son_w + saat_w)
    w = min(w, BALON_EN)
    im = _balon_zemin(w, h, dolgu, giden)
    d = ImageDraw.Draw(im)
    for n, s in enumerate(satirlar):
        d.text((32, 28 + n * lh), s, font=yz, fill=yazi_renk)
    d.text((w - 28, h - 18), saat, font=saat_yz, fill=saat_renk, anchor='rs')
    return im


def _soluk(dolgu, yazi_renk):
    """Balon dolgusuyla yazı rengi arası (saat ve adres için)."""
    a, b = Image.new('RGB', (1, 1), dolgu).getpixel((0, 0)), Image.new('RGB', (1, 1), yazi_renk).getpixel((0, 0))
    return tuple(round(x * 0.45 + y * 0.55) for x, y in zip(a, b))


def ilan_balonu(kart, ilan, logo, saat, giden, renk):
    """Paylaşılan ilan bağlantısının önizlemesi (balonun içinde beyaz kart)."""
    dolgu, yazi_renk = (renk[0], renk[1]) if giden else ('#ffffff', GELEN_YAZI)
    w = BALON_EN
    kart_w, kart_h = w - 32, 390
    kt = panel(kart_w, kart_h, '#ffffff' if giden else '#f3eee6', 26)
    d = ImageDraw.Draw(kt)
    kt.alpha_composite(r.logo_rozeti(ilan, logo, 104), (28, 28))
    for boy in (38, 34, 30, 27):
        if r._OLC.textlength(kart['kurum'], font=F(boy, True)) <= kart_w - 180:
            break
    d.text((152, 44), kart['kurum'], font=F(boy, True), fill=GELEN_YAZI)
    d.text((152, 92), kart['alt'], font=F(30, False), fill=SAAT)
    d.text((28, 160), kart['sayi'], font=F(96, True), fill=renk[2])
    d.text((30, 272), kart['satir1'], font=F(34, True), fill=GELEN_YAZI)
    d.text((30, 322), kart['satir2'], font=F(34, False), fill=GELEN_YAZI)
    h = kart_h + 16 + 74
    im = _balon_zemin(w, h, dolgu, giden)
    im.alpha_composite(kt, (16, 16))
    d = ImageDraw.Draw(im)
    soluk = _soluk(dolgu, yazi_renk) if giden else SAAT
    d.text((32, kart_h + 30), 'kpsstercihi.com', font=F(30, True), fill=soluk)
    d.text((w - 28, h - 18), saat, font=F(26, False), fill=soluk, anchor='rs')
    return im


def yaziyor_balonu(t0, t):
    w, h = 150, 84
    im = _balon_zemin(w, h, GELEN, False)
    d = ImageDraw.Draw(im)
    for n in range(3):
        faz = ((t - t0) * 2.4 - n * 0.22) % 1.0
        zip_ = 8 * max(0.0, 1 - abs(faz - 0.3) / 0.3)
        x = 44 + n * 31
        d.ellipse((x - 10, 42 - zip_ - 10, x + 10, 42 - zip_ + 10), fill='#b9b0c4')
    return im


class Sohbet:
    """Tüm videoya yayılan sohbet. mesajlar: [(bas_sn, giden, katman)] (bas mutlak video saniyesi; <0: baştan hazır)."""

    def __init__(self, mesajlar):
        self.m = []
        y = 0
        for bas, giden, kat in mesajlar:
            x = (GEN - 2 * IC) - kat.width if giden else 0
            self.m.append(dict(bas=bas, giden=giden, kat=kat, x=x, y=y))
            y += kat.height + ARA

    def _kayma(self, t):
        en = 0.0
        for m in self.m:
            alt = m['y'] + m['kat'].height
            if not m['giden'] and m['bas'] > 0:     # yazıyor göstergesi de yer kaplar
                yb = m['bas'] - YAZIYOR
                if t >= yb:
                    en = max(en, (m['y'] + 84 - ALAN_H) * yumusak((t - yb) / KAYMA))
            if t >= m['bas']:
                en = max(en, (alt - ALAN_H) * (yumusak((t - m['bas']) / KAYMA) if m['bas'] > 0 else 1))
        return max(0.0, en)

    def ciz(self, im, t):
        alan = Image.new('RGBA', (GEN - 2 * IC, ALAN_H), (0, 0, 0, 0))
        dy = self._kayma(t)
        for m in self.m:
            if not m['giden'] and m['bas'] > 0 and m['bas'] - YAZIYOR <= t < m['bas']:
                y = round(m['y'] - dy)
                if 0 <= y < ALAN_H:
                    alan.alpha_composite(yaziyor_balonu(m['bas'] - YAZIYOR, t), (0, y))
                continue
            if t < m['bas']:
                continue
            p = 1.0 if m['bas'] < 0 else yumusak((t - m['bas']) / 0.3)
            kat = m['kat']
            if p < 1:
                o = 0.86 + 0.14 * p
                kat = kat.resize((max(1, round(kat.width * o)), max(1, round(kat.height * o))), Image.Resampling.BILINEAR)
                kat.putalpha(kat.getchannel('A').point(lambda a: int(a * p)))
            x = max(0, m['x'] + (m['kat'].width - kat.width if m['giden'] else 0))
            y = round(m['y'] - dy + (m['kat'].height - kat.height) + 30 * (1 - p))
            if y + kat.height <= 0 or y >= ALAN_H:
                continue
            if y < 0:
                kat, y = kat.crop((0, -y, kat.width, kat.height)), 0
            if y + kat.height > ALAN_H:
                kat = kat.crop((0, 0, kat.width, ALAN_H - y))
            alan.alpha_composite(kat, (x, y))
        im.paste(alan, (SOL + IC, ALAN_UST), alan)


def telefon(ad, avatar):
    """Sohbet ekranının sabit çerçevesi: krem zemin + üst kişi şeridi."""
    w, h = GEN, TEL_ALT - TEL_UST
    im = panel(w, h, EKRAN, 44)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, BASLIK_H), radius=44, fill='#ffffff')
    d.rectangle((0, BASLIK_H - 44, w - 1, BASLIK_H), fill='#ffffff')
    d.line((0, BASLIK_H, w, BASLIK_H), fill='#e6dccd', width=2)
    d.ellipse((30, 22, 98, 90), fill=avatar)
    d.text((64, 57), ad[0], font=F(38, True), fill='#ffffff', anchor='mm')
    d.text((118, 28), ad, font=F(38, True), fill=GELEN_YAZI)
    d.text((118, 72), 'çevrimiçi', font=F(26, False), fill='#3aa76d')
    return im


class Sabit:
    def __init__(self, kat, x, y):
        self.kat, self.x, self.y = kat, x, y

    def ciz(self, im, t, cikis):
        im.paste(self.kat, (self.x, self.y), self.kat)


class SohbetOgesi:
    """Sohbeti sahneye bağlar: sahne yerel zamanını mutlak video zamanına çevirir."""

    def __init__(self, sohbet, bas):
        self.s, self.bas = sohbet, bas

    def ciz(self, im, t, cikis):
        if t >= r.OTURMUS_KAYDIRMA:          # ilk sahne "oturmuş" çizilir; sohbet zamanı yine baştan akar
            t -= r.OTURMUS_KAYDIRMA
        self.s.ciz(im, self.bas + t)


def kanca(satir1, satir2, renk):
    """Üstteki kanca başlığı: düz satır + vurgu bandında ikinci satır."""
    boy = next((b for b in (66, 60, 54, 48) if r._OLC.textlength(satir1, font=F(b, True)) <= GEN), 48)
    o = [Sabit(yazi(satir1, boy, '#ffffff'), SOL, 330 + (66 - boy) // 2)]
    bb = next((b for b in (66, 60, 54, 48) if r._OLC.textlength(satir2, font=F(b, True)) + 56 <= GEN), 48)
    b, _ = r.bantlar([satir2], bb, SOL, 420, -10, bant=renk[0], renk=renk[1])
    return o + [Sabit(x.katman, x.x, x.y) for x in b]


def okuma_suresi(metin):
    return 0.8 + 0.027 * len(metin)


def sahneler_kur(sn, ilan, logo):
    """sn: SENARYOLAR öğesi. mesaj: ('o'|'ben', metin) ya da ('o'|'ben', 'KART'). İlk iki mesaj kapakta hazır durur."""
    renk = renk_sec(sn['renk'])
    saat_h, saat_d = map(int, sn.get('saat', '21:02').split(':'))
    m, t = [], 2.4
    for n, (kim, metin) in enumerate(sn['mesajlar']):
        giden = kim == 'ben'
        saat = f'{saat_h:02d}:{saat_d + n // 3:02d}'
        if n < 2:
            bas = -1
        else:
            if not giden:
                t += YAZIYOR
            bas = t
        kat = ilan_balonu(sn['kart'], ilan, logo, saat, giden, renk) if metin == 'KART' else balon(metin, giden, saat, renk)
        m.append((bas, giden, kat))
        if n >= 2:
            t += 2.8 if metin == 'KART' else okuma_suresi(metin)
    bitis = t + 1.2
    sohbet = Sohbet(m)
    zemin_ogeleri = kanca(sn['kanca'][0], sn['kanca'][1], renk) + [Sabit(telefon(sn['kisi'], renk[2]), SOL, TEL_UST)]
    sureler = [2.2] + [(bitis - 2.2) / 4] * 4
    sahneler, an = [], 0.0
    for s in sureler:
        sahneler.append(Sahne(s, zemin_ogeleri + [SohbetOgesi(sohbet, an)], son=True))
        an += s
    sahneler.append(r.kapanis_sahnesi(sn['kapanis'], 3.0))   # sohbetin üstünü örtmez, ayrı sahne
    return sahneler


# ---------------------------------------------------------------- senaryolar
# Her bilgi ilanın şart metninden; bölüm sayılıyorsa ilanda kabul edilen bölümlerin tamamı yazılır (kural: tüm bölümler).
SENARYOLAR = {
    'adli-tip': dict(
        ilan='dc97ce1e-dce0-408a-a785-682c4656435e', renk='gece', kisi='Emre',
        kanca=('“Lise mezununa ilan yok”', 'DEDİ. GÖSTERDİM.'),
        kart=dict(kurum='ADLİ TIP KURUMU', alt='Sözleşmeli personel alımı', sayi='181 KİŞİ', satir1='Lise · Önlisans · Lisans',
                  satir2='Başvuru: 30 Kasım – 6 Aralık'),
        kapanis='Lise, önlisans, lisans: her gün yeni kamu ilanı',
        mesajlar=[('o', 'Lise mezunuyum, KPSS\'ye de girdim'), ('o', 'Ama bize hiç ilan çıkmıyor ki'),
                  ('ben', 'Adli Tıp Kurumu 181 kişi alıyor, gördün mü?'), ('ben', 'KART'),
                  ('o', '181\'in hepsi mühendistir kesin'),
                  ('ben', 'Değil. Lise mezunlarına 37 kadro var'),
                  ('ben', '26 hizmetli, 10 şoför, 1 infaz ve koruma memuru (erkek)'),
                  ('o', 'Ek şart var mı peki?'),
                  ('ben', 'Hizmetlide 6 ay temizlik işinde sigortalı çalışmış olmak gerekiyor'),
                  ('ben', 'Şoförde E sınıfı ya da dengi ehliyet, infaz korumada 30 yaş sınırı var'),
                  ('o', 'Tamam, nasıl başvuruluyor?'),
                  ('ben', 'e-Devlet\'ten, Kariyer Kapısı üzerinden'),
                  ('ben', '30 Kasım\'da açılıyor, 6 Aralık\'ta kapanıyor'),
                  ('o', 'Takvime yazdım. İyi ki sordum')]),
    'sayistay': dict(
        ilan='ff6084a1-bbdd-45d7-b62e-a649a026a2b2', renk='lacivert', kisi='Selin', saat='22:14',
        kanca=('“Devlette yazılımcıya yer yok”', 'DEDİ. SAYIŞTAY\'I GÖSTERDİM.'),
        kart=dict(kurum='SAYIŞTAY BAŞKANLIĞI', alt='Sözleşmeli bilişim personeli', sayi='16 KİŞİ', satir1='Lisans · Önlisans',
                  satir2='Son başvuru: 25 Kasım'),
        kapanis='Bilişimden sağlığa her gün yeni kamu ilanı',
        mesajlar=[('o', 'Bilgisayar programcılığı bitirdim'),
                  ('o', 'Özelde staj bile bulamadım, devlette zaten yazılımcıya yer yok'),
                  ('ben', 'Sayıştay şu an programcı alıyor, bak'), ('ben', 'KART'),
                  ('o', 'Önlisans var mı içinde?'),
                  ('ben', '4 kadro önlisans programcı. Bilgisayar programcılığı ile ilgili bölümler başvurabiliyor'),
                  ('ben', 'Lisans mezunlarına da 9 programcı ve 3 çözümleyici kadrosu var'),
                  ('o', 'Nerede çalışılıyor?'),
                  ('ben', 'Ankara, Çankaya'),
                  ('o', 'Başvuru nereden?'),
                  ('ben', 'e-Devlet\'ten Kariyer Kapısı\'na giriyorsun. KPSS puanın da isteniyor'),
                  ('ben', 'Son gün 25 Kasım, bekleme'),
                  ('o', 'Şimdi açıyorum e-Devlet\'i')]),
    'izmir-zabita': dict(
        ilan='sbb-a00f639e934dfda13b150416', renk='kobalt', kisi='Annem', saat='19:40',
        kanca=('Annem zabıta ilanı attı', 'MEĞER HAKLIYMIŞ.'),
        kart=dict(kurum='İZMİR BÜYÜKŞEHİR BLD.', alt='Zabıta memuru alımı', sayi='90 KİŞİ', satir1='Lisans · Önlisans',
                  satir2='Başvuru: 30 Kasım – 4 Aralık'),
        kapanis='Senin bölümüne uygun ilanlar her gün',
        mesajlar=[('o', 'Oğlum İzmir Büyükşehir zabıta alıyormuş'), ('o', 'KART'),
                  ('ben', 'Anne ben beden eğitimi mezunuyum, zabıtayla ne ilgisi var'),
                  ('o', 'Spor bölümlerine 30 kadro ayırmışlar. 24 erkek, 6 kadın'),
                  ('ben', 'Ciddi misin? Hangi bölümler?'),
                  ('o', 'Antrenörlük eğitimi, beden eğitimi ve spor öğretmenliği, spor yöneticiliği, egzersiz ve spor bilimleri, '
                        'rekreasyon, engellilerde beden eğitimi ve spor öğretmenliği, engellilerde egzersiz ve spor bilimleri'),
                  ('ben', 'Puan kaç lazım?'),
                  ('o', '2026 KPSS P3\'ten en az 65. En az B sınıfı ehliyet de istiyorlar'),
                  ('ben', 'Başvuru nasıl?'),
                  ('o', '30 Kasım – 4 Aralık arası Zabıta Dairesine şahsen. Formu izmir.bel.tr\'den dolduruyorsun'),
                  ('ben', 'Tamam anne, haklıymışsın')]),
    'ssb': dict(
        ilan='41353f9d-7dda-4b65-b2ba-de6bf8e72f54', renk='zift', kisi='Kaan', saat='23:05',
        kanca=('KPSS\'siz devlet işi mi?', 'ŞARTI 5 YIL DENEYİM.'),
        kart=dict(kurum='SAVUNMA SANAYİİ BŞK.', alt='Proje bazlı sözleşmeli uzman', sayi='26 KİŞİ', satir1='KPSS şartı yok',
                  satir2='Son başvuru: 21 Aralık'),
        kapanis='KPSS\'li, KPSS\'siz: her gün yeni kamu ilanı',
        mesajlar=[('o', '6 yıldır özelde savunma projelerinde mühendisim'),
                  ('o', 'KPSS\'ye hiç girmedim, devlet kapısı bana kapalı değil mi?'),
                  ('ben', 'Değil. Savunma Sanayii Başkanlığı KPSS\'siz uzman alıyor'), ('ben', 'KART'),
                  ('o', 'Şartı ne?'),
                  ('ben', 'İlan tablosundaki mühendislik bölümlerinden mezun olmak ve ilandaki alanlardan birinde en az 5 yıl tecrübe'),
                  ('ben', 'Radar, aviyonik, elektronik harp, yapay zekâ, uzay gibi 20 alan sayılmış'),
                  ('o', 'İngilizce istiyor mu?'),
                  ('ben', 'Son 2 yılda YDS İngilizceden en az 70 ya da denk belge. Derslerin tamamı İngilizceyse aranmıyor'),
                  ('o', 'Benim bölüm yüzde yüz İngilizceydi'),
                  ('ben', 'O zaman 21 Aralık\'a kadar Kariyer Kapısı\'ndan başvur. Görev yeri Ankara'),
                  ('o', 'Bu akşam başvuruyorum')]),
    'kaymakam': dict(
        ilan='sbb-6fb367ee271dfcd5f58d9c5b', renk='erik', kisi='Dedem', saat='18:20',
        kanca=('Dedem: “Kaymakam ol”', '60 KİŞİ ALINACAKMIŞ.'),
        kart=dict(kurum='İÇİŞLERİ BAKANLIĞI', alt='Kaymakam adayı alımı', sayi='60 KİŞİ', satir1='Lisans',
                  satir2='Ön başvuru: 1 – 7 Aralık'),
        kapanis='Hangi bölüm nereye başvurur, her gün',
        mesajlar=[('o', 'Gazetede gördüm, 60 kaymakam adayı alınacakmış'),
                  ('o', 'Sen iktisat okumadın mı? Olsana kaymakam'),
                  ('ben', 'Dede o kadar kolay mı, dur bakayım'), ('ben', 'KART'),
                  ('ben', 'Haklısın, iktisat da sayılıyor'),
                  ('o', 'Başka hangi bölümler?'),
                  ('ben', 'Uluslararası ilişkiler, siyaset bilimi, kamu yönetimi, iktisat, işletme, maliye, finans, ekonometri, '
                          'çalışma ekonomisi ve endüstri ilişkileri, hukuk. Müfredatı bunlara yüzde 80 benzeyenler de'),
                  ('ben', 'Mühendislik, tarih, sosyoloji, halkla ilişkiler ve tanıtım, psikoloji mezunları da uluslararası ilişkiler, '
                          'siyaset bilimi, kamu yönetimi, hukuk, maliye ya da iktisatta tezli yüksek lisans yaptıysa olur'),
                  ('o', 'Yaş sınırı var mı?'),
                  ('ben', '1 Ocak 1992 ve sonrasında doğmuş olmak gerekiyor'),
                  ('o', 'Sen 96\'lısın, tamam o zaman'),
                  ('ben', 'Ön başvuru 1–7 Aralık\'ta ÖSYM üzerinden. Takvime yazdım dede'),
                  ('o', 'Aferin benim kaymakamıma')]),
    'gaziosmanpasa': dict(
        ilan='iskur-090fb7d39012e2f5024f6e1a', renk='kiremit', kisi='Zeynep', saat='20:31',
        kanca=('“65 aldım, bitti” dedi', 'İSTANBUL\'DA 36 KADRO VAR.'),
        kart=dict(kurum='GAZİOSMANPAŞA BLD.', alt='Zabıta memuru alımı', sayi='36 KİŞİ', satir1='Lisans · Önlisans',
                  satir2='Başvuru: 7 – 11 Aralık'),
        kapanis='Puanına uygun ilanlar her gün',
        mesajlar=[('o', 'KPSS\'den 65 aldım'), ('o', 'Bu puanla bir yere girilmez, bitti'),
                  ('ben', 'Gaziosmanpaşa Belediyesi zabıta alıyor, en az 65 puan istiyor'), ('ben', 'KART'),
                  ('o', 'Önlisans da var mı?'),
                  ('ben', 'Lisansa P3 ile 23 kadro, önlisansa P93 ile 13 kadro. İkisinde de en az 65'),
                  ('o', 'Başka şart?'),
                  ('ben', 'Sınav tarihinde 30 yaşını doldurmamış olmak ve en az B sınıfı ehliyet. Bölümler ilandaki tabloda'),
                  ('o', 'Başvuru internetten mi?'),
                  ('ben', 'Hayır, şahsen. 7–11 Aralık arası Gaziosmanpaşa Kültür Merkezi\'ndeki Yazı İşleri Müdürlüğüne'),
                  ('o', 'Ehliyetim var, yaşım da tutuyor. Gidiyorum')]),
}


def uret(ad, cikti, acik):
    from kurum_gorseli import kurum_logosu
    sn = SENARYOLAR[ad]
    ilan = next(i for i in acik if sn['ilan'] in i['id'])
    sahneler = sahneler_kur(sn, ilan, kurum_logosu(ilan))
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    r.kare(sahneler, 0.0).save(cikti / f'{ad}-kapak.png')
    an = 0.0
    for n, s in enumerate(sahneler[1:], 1):    # her sahnenin sonu (denetim için)
        an += sahneler[n - 1].sure
        r.kare(sahneler, an + s.sure - 0.05).save(cikti / f'{ad}-kare-{n}.png')
    muzik, bas = r.muzik_yolu('ilan')
    sessiz = cikti / f'{ad}-sessiz.mp4'
    sure = r.video_yaz(sahneler, sessiz, None)
    import imageio_ffmpeg
    # Bu makinedeki ffmpeg 7.1 (Windows) loudnorm'da çöküyor; ses ayrı işlenip birleştirilir.
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(sessiz), '-ss', f'{bas:.2f}', '-i', str(muzik),
                    '-filter_complex', f'[1:a]afade=t=in:d=0.3,afade=t=out:st={sure - 1:.2f}:d=1,volume=0.85[a]',
                    '-map', '0:v', '-map', '[a]', '-t', f'{sure:.2f}', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                    '-movflags', '+faststart', str(cikti / f'{ad}.mp4')], check=True)
    sessiz.unlink()
    print(f'{ad}: {sure:.1f} sn')
    return sure


def main():
    a = argparse.ArgumentParser()
    a.add_argument('senaryo', choices=[*SENARYOLAR, 'hepsi'])
    a.add_argument('--cikti', default='reels-cikti')
    s = a.parse_args()
    import sosyal_motor as sm
    acik = sm.acik_ilanlar(sm.ilanlari_yukle(sm.ROOT / 'docs'), datetime.now(k.TR))
    for ad in (SENARYOLAR if s.senaryo == 'hepsi' else [s.senaryo]):
        uret(ad, s.cikti, acik)


if __name__ == '__main__':
    main()
