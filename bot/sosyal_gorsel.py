"""Instagram hikâye (story) ve kaydırmalı gönderi (karusel) yayını — 18 Kasım 2026'da onaylanan üç tür.

Görseller bot/sosyal_ornek.py ile üretilir (onaylı Reels görünümü, Kâğıt/Bordo). Reels akışından (sosyal.yml) ayrıdır:
geçmişi sosyal/gorsel-gecmis.json'da tutulur, böylece Reels'in renk sırası, tekrar engeli ve YouTube kotası etkilenmez.

Program (Türkiye saatiyle, günde bir çalışma ~11:00):
  her gün      son-gun      hikâye (son başvurusu 7 gün içinde biten ilanlar)
  çarşamba     son-gun      karusel
  perşembe     puan-bandi   hikâye + karusel (puan aralığı haftaya göre döner; verisi olmayan aralık atlanır)
  pazar        kadro-raporu hikâye + karusel (son 7 günün yeni ilanları)
  saatte bir   ilan         karusel: son 48 saatte eklenen her açık ilan için bir gönderi (çalışma başına en çok
                            ILAN_CALISMA; akademik, kurum içi ve iptal ilanlar paylaşılmaz; aynı ilan bir kez)
Verisi yetmeyen tür o gün paylaşılmaz. Aynı gün aynı tür+biçim iki kez paylaşılmaz.

Platformlar (SOSYAL_KAPALI=facebook,tiktok ile kapatılabilir; biri hata verirse diğerleri yine denenir):
  Instagram  hikâye + karusel (Instagram Login API)
  Facebook   hikâye (sayfa video_stories) + karusel (çok fotoğraflı sayfa gönderisi: photos published=false + feed)
  TikTok     yalnız karusel, Buffer üzerinden fotoğraf gönderisi (TikTok'un hikâye API'si yok). Buffer ücretsiz planında
             kanal başına 30 günde 1000 istek var; Reels ve panel de aynı kotayı kullandığı için TikTok'a günde en çok
             TT_GUNLUK karusel gider (önce günlük türler, sonra en kalabalık alımlı ilanlar).

Instagram Login API: hikâye = media_type STORIES + video_url; karusel = her slayt için image_url (JPEG zorunlu) +
is_carousel_item, sonra media_type CAROUSEL + children + caption. Dosyalar önizleme sürümünden (GitHub Release) çekilir.

Kullanım: python bot/sosyal_gorsel.py uret --cikti gorsel-cikti [--tur son-gun --bicim hikaye]
          python bot/sosyal_gorsel.py yayinla --cikti gorsel-cikti --taban https://github.com/.../releases/download/ETIKET
          python bot/sosyal_gorsel.py kaydet --cikti gorsel-cikti"""
import argparse
import hashlib
import json
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GECMIS_YOLU = ROOT / 'sosyal' / 'gorsel-gecmis.json'
TURLER = ('son-gun', 'kadro-raporu', 'puan-bandi')
PALET = {'kadro-raporu': 'kagit', 'son-gun': 'bordo', 'puan-bandi': 'kagit', 'ilan': 'kagit'}
ILAN_TAZE_SAAT = 48      # ilan karuseli: ilanın siteye en çok kaç saat önce eklenmiş olabileceği
ILAN_CALISMA = 1         # bir çalışmada en çok kaç ilan karuseli (saatlik çalışmalarla gün boyuna yayılır)
ILAN_GUNLUK = 3          # günde en çok kaç ilan karuseli (27 Kas 2026: gece 03:40'ta art arda 3 karusel çıkıyordu)
TT_GUNLUK = 5            # TikTok'a günde en çok kaç karusel (Buffer kotası). 27 Kas 2026'dan beri iş akışı
                         # TikTok karuselini kapatır (SOSYAL_KAPALI'ye tiktok eklenir): ~100 izlenmede kalıyordu.
PLATFORMLAR = ('instagram', 'facebook', 'tiktok')
SITE = 'https://kpsstercihi.com'
# Perşembe puan aralığı haftaya göre döner (ISO hafta numarası); verisi olmayan aralık atlanıp sıradaki denenir.
PUAN_ARALIKLARI = (('lisans', 70, 75), ('onlisans', 70, 75), ('lisans', 75, 80), ('ortaogretim', 70, 75),
                   ('lisans', 65, 70), ('onlisans', 75, 80), ('lisans', 80, 85), ('ortaogretim', 75, 80))
ETIKETLER = {'ilan': ['#kpss', '#kamuilanları', '#yeniilan', '#memuralımı', '#işilanı'],
             'son-gun': ['#songün', '#kpss', '#kamuilanları', '#memuralımı'],
             'kadro-raporu': ['#kpss', '#kamuilanları', '#kadro', '#haftanınözeti', '#memuralımı'],
             'puan-bandi': ['#kpss', '#tabanpuan', '#kpsstercih', '#atama']}
TELEGRAM = {'ilan': 'Her yeni ilan ilk önce Telegram kanalımızda: @kpsstercihi (bağlantı profilde) 💛',
            'son-gun': 'Yeni ilanlar ve son gün hatırlatmaları Telegram kanalımızda: @kpsstercihi (bağlantı profilde) 💛',
            'kadro-raporu': 'Her pazar haftanın özeti ve yeni ilanlar Telegram kanalımızda: @kpsstercihi (bağlantı profilde) 💛',
            'puan-bandi': 'Bütün taban puanları ve tercih robotu kpsstercihi.com\'da; yeni ilanlar Telegram\'da: @kpsstercihi 💛'}
SORULAR = {'ilan': 'Bu ilan sana uygun mu? Başvuracak birini etiketle 👇',
           'son-gun': 'Başvurunu yaptın mı, yoksa son güne mi bıraktın? 👇',
           'kadro-raporu': 'Bu hafta senin için bir ilan çıktı mı? 👇',
           'puan-bandi': 'Senin puanın bu aralıkta mı? 👇'}
JPEG_KALITE = 92


# ---------------------------------------------------------------- plan
def plan(simdi):
    """[(tür, [biçimler])] — haftanın gününe göre (pazartesi=0)."""
    gun = simdi.weekday()
    sonuc = []
    if gun == 6:
        sonuc.append(('kadro-raporu', ['hikaye', 'karusel']))
    if gun == 3:
        sonuc.append(('puan-bandi', ['hikaye', 'karusel']))
    sonuc.append(('son-gun', ['hikaye', 'karusel'] if gun == 2 else ['hikaye']))
    return sonuc


def gecmis_oku(yol=GECMIS_YOLU):
    try:
        veri = json.loads(Path(yol).read_text(encoding='utf-8'))
        return veri if isinstance(veri, list) else []
    except (OSError, ValueError):
        return []


def bugun_yapildi(gecmis, tur, bicim, simdi):
    gun = simdi.date().isoformat()
    return any(g.get('tur') == tur and g.get('bicim') == bicim and str(g.get('zaman', ''))[:10] == gun and _yayinda(g)
               for g in gecmis)


def _yayinda(g):
    return any(g.get(f'{p}_id') for p in ('ig', 'fb', 'tt'))


def ilan_adaylari(acik, simdi, gecmis, en_cok=ILAN_CALISMA):
    """Karuseli yapılacak ilanlar: son ILAN_TAZE_SAAT saatte eklenmiş, daha önce karuseli paylaşılmamış; önce eskiler."""
    from sosyal_motor import _zaman
    yapilan = {g.get('ilan_id') for g in gecmis if g.get('tur') == 'ilan' and _yayinda(g)}
    bugun = sum(1 for g in gecmis if g.get('tur') == 'ilan' and _yayinda(g) and str(g.get('zaman', ''))[:10] == simdi.date().isoformat())
    en_cok = min(en_cok, max(0, ILAN_GUNLUK - bugun))
    if not en_cok:
        return []
    sinir = simdi - timedelta(hours=ILAN_TAZE_SAAT)
    adaylar = [i for i in acik if i.get('id') and i['id'] not in yapilan and (_zaman(i.get('ilk_gorulme')) or sinir) > sinir]
    adaylar.sort(key=lambda i: (_zaman(i.get('ilk_gorulme')), i['id']))
    return adaylar[:en_cok]


def puan_araliklari(simdi):
    """Bu haftanın sırasından başlayan aralık listesi (verisi olmayan atlanabilsin diye hepsi döner)."""
    bas = simdi.isocalendar()[1] % len(PUAN_ARALIKLARI)
    return [PUAN_ARALIKLARI[(bas + n) % len(PUAN_ARALIKLARI)] for n in range(len(PUAN_ARALIKLARI))]


# ---------------------------------------------------------------- açıklama
def _tarih(iso):
    from kart_tasarimlari import AYLAR
    g = datetime.fromisoformat(str(iso)[:10])
    return f'{g.day} {AYLAR[g.month - 1]}'


def _sayi(n):
    return f'{n:,}'.replace(',', '.')


def _puan(x):
    return f'{x:.2f}'.replace('.', ',')


def _basliga(s):
    import re
    from haftalik import basliga
    return re.sub(r'\bA\.ş\.?(?=\s|$)', 'A.Ş.', basliga(s or ''))


def _kurum(s):
    from haftalik import _kisa
    return _basliga(_kisa(s) or s)


def aciklama(tur, veri):
    """Karusel açıklaması: ilk satır sayılı kanca, kısa liste, tek soru, Telegram satırı, en çok 5 etiket."""
    if tur == 'ilan':
        satirlar = [f'• {_sayi(n)} {ad}' if n else f'• {ad}' for ad, n in veri['kadrolar'][:6]]
        kanca = (f'📢 {_kurum(veri["kurum"])} {_sayi(veri["toplam"])} personel alacak:' if veri['toplam']
                 else f'📢 {_kurum(veri["kurum"])} personel alımı ilanı yayımladı:')
        if veri.get('bitis'):
            satirlar.append(f'\n🗓 Son başvuru: {_tarih(veri["bitis"])}')
        if veri.get('adres'):
            satirlar.append(f'Şartların tamamı ve başvuru bağlantısı: {veri["adres"]}')
    elif tur == 'son-gun':
        satirlar = []
        for gun, ilanlar in veri['gunler'][:4]:
            adlar = ', '.join(f'{ad} ({_sayi(n)})' if n else ad for ad, n in ilanlar[:3])
            fazla = f' ve {len(ilanlar) - 3} ilan daha' if len(ilanlar) > 3 else ''
            satirlar.append(f'• {_tarih(gun)}: {adlar}{fazla}')
        kanca = f'⏰ Son başvurusu 7 gün içinde biten {veri["ilan"]} kamu ilanı, {_sayi(veri["kadro"])} kadro:'
    elif tur == 'kadro-raporu':
        satirlar = [f'• {ad}: {_sayi(n)} kadro' for ad, n in veri['ilk5']]
        kanca = (f'📊 Haftanın kadro raporu ({veri["aralik"]}): {veri["ilan"]} yeni kamu ilanında {_sayi(veri["kadro"])} kadro. '
                 'En çok kadro açan kurumlar:')
    else:
        from puan_sayfalari import donem_yaz
        alt, ust = veri['bant']
        satirlar = [f'• {_basliga(u)}, {_kurum(k)} ({_basliga(il)}): {_puan(p)}' for u, k, il, p in veri['en_dusuk'][:5]]
        kanca = (f'📊 KPSS {donem_yaz(veri["donem"])} {veri["duzey_adi"].lower()} {alt}–{ust} puanla nereye atanıldı? '
                 f'{_sayi(veri["kadro_kodu"])} kadroya {_sayi(veri["kisi"])} kişi yerleşti. En düşük puanla:')
    metin = '\n'.join([kanca] + satirlar) + f'\n\n{SORULAR[tur]}\n\n{TELEGRAM[tur]}\n\n' + ' '.join(ETIKETLER[tur][:5])
    import sosyal_kalite
    return sosyal_kalite.aciklama_duzelt(metin)[:2150]


# ---------------------------------------------------------------- üretim
def _jpeg(png, hedef):
    from PIL import Image
    with Image.open(png) as im:
        im.convert('RGB').save(hedef, 'JPEG', quality=JPEG_KALITE, optimize=True)


def tur_uret(tur, simdi, klasor, acik, docs, logo):
    """Türün hikâye + karusel dosyaları; veri yetmezse None. Döner: veri (sosyal_ornek.yaz çıktısı)."""
    import haftalik as h
    import reels
    import sosyal_ornek as so
    reels.palet_sec(PALET[tur])
    if tur == 'kadro-raporu':
        sonuc = so.kadro_raporu(acik, simdi, logo)
    elif tur == 'son-gun':
        sonuc = so.son_gun(acik, simdi, logo)
    else:
        adlar, sonuc = dict(h.PUAN_DUZEYLERI), None
        for duzey, alt, ust in puan_araliklari(simdi):
            sonuc = so.puan_bandi(docs, duzey, adlar[duzey], alt, ust)
            if sonuc:
                sonuc[2]['duzey_adi'] = adlar[duzey]
                break
    if not sonuc:
        return None
    veri = so.yaz(*sonuc, klasor)
    for png in sorted(Path(klasor).glob('karusel-*.png')):
        _jpeg(png, png.with_suffix('.jpg'))
    return veri


def _karusel_dosyalari(kaynak, cikti, onek):
    dosyalar = []
    for jpg in sorted(Path(kaynak).glob('karusel-*.jpg'))[:10]:   # Instagram karuseli en çok 10 öğe
        ad = f'{onek}-{jpg.name}'
        (cikti / ad).write_bytes(jpg.read_bytes())
        dosyalar.append(ad)
    return dosyalar


def ilan_uret(ilan, simdi, klasor, logo):
    """Tek ilanın karusel slaytları (JPEG) ve açıklama verisi; kadro yoksa None."""
    import reels
    import sosyal_ornek as so
    from ilan_baglanti import ilan_sayfasi
    reels.palet_sec(PALET['ilan'])
    sonuc = so.ilan_karuseli(ilan, simdi, logo)
    if not sonuc:
        return None
    slaytlar, veri = sonuc
    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    for n, im in enumerate(slaytlar, 1):
        im.convert('RGB').save(klasor / f'karusel-{n:02d}.jpg', 'JPEG', quality=JPEG_KALITE, optimize=True)
    try:
        veri['adres'] = ilan_sayfasi(ilan, SITE)
    except ValueError:
        veri['adres'] = SITE
    return veri


def uret(cikti, simdi=None, turler=None, gecmis_yolu=GECMIS_YOLU, docs=ROOT / 'docs', ilan_sayisi=ILAN_CALISMA):
    """Bugünün planındaki işleri (turler=[] ise hiçbiri) ve yeni ilan karuselerini (en çok ilan_sayisi) üretir.
    cikti/is.json: [{tür, biçim, dosyalar, açıklama, ilan_id?, kadro?}]. İş yoksa boş liste."""
    import sosyal_motor as sm
    from kurum_gorseli import kurum_logosu
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    gecmis = gecmis_oku(gecmis_yolu)
    isler, acik = [], None

    def acik_al():
        nonlocal acik
        if acik is None:
            acik = sm.acik_ilanlar(sm.ilanlari_yukle(docs), simdi)
        return acik

    for tur, bicimler in (plan(simdi) if turler is None else turler):
        bicimler = [b for b in bicimler if not bugun_yapildi(gecmis, tur, b, simdi)]
        if not bicimler:
            print(f'{tur}: bugün zaten paylaşıldı.')
            continue
        try:
            veri = tur_uret(tur, simdi, cikti / tur, [] if tur == 'puan-bandi' else acik_al(), docs, kurum_logosu)
        except Exception as hata:   # bir türün hatası diğerlerini durdurmaz
            print(f'::warning::{tur} üretilemedi: {hata}')
            continue
        if not veri:
            print(f'{tur}: veri yetersiz, bugün paylaşılmaz.')
            continue
        for bicim in bicimler:
            if bicim == 'hikaye':
                dosyalar = [f'{tur}-hikaye.mp4']
                (cikti / dosyalar[0]).write_bytes((cikti / tur / 'hikaye.mp4').read_bytes())
                isler.append({'tur': tur, 'bicim': 'hikaye', 'dosyalar': dosyalar})
            else:
                dosyalar = _karusel_dosyalari(cikti / tur, cikti, tur)
                if len(dosyalar) >= 2:
                    isler.append({'tur': tur, 'bicim': 'karusel', 'dosyalar': dosyalar, 'aciklama': aciklama(tur, veri)})
        print(f'{tur}: {", ".join(bicimler)} hazır ({veri["hikaye_kare"]} hikâye karesi, {veri["karusel_slayt"]} slayt)')

    if ilan_sayisi:
        for ilan in ilan_adaylari(acik_al(), simdi, gecmis, ilan_sayisi):
            # kimlik çoğu zaman uzun bir adres; ilk 40 karakteri bütün Kariyer Kapısı ilanlarında aynı olduğundan klasör
            # ve sürüm dosya adları çakışıyordu (GitHub yüklemesi 404). Kimliğin özeti adı tekil tutar.
            onek = 'ilan-' + hashlib.sha1(ilan['id'].encode('utf-8')).hexdigest()[:12]
            try:
                veri = ilan_uret(ilan, simdi, cikti / onek, kurum_logosu)
            except Exception as hata:
                print(f'::warning::{ilan["id"]} karuseli üretilemedi: {hata}')
                continue
            if not veri:
                continue
            dosyalar = _karusel_dosyalari(cikti / onek, cikti, onek)
            if len(dosyalar) >= 2:
                isler.append({'tur': 'ilan', 'bicim': 'karusel', 'dosyalar': dosyalar, 'aciklama': aciklama('ilan', veri),
                              'ilan_id': ilan['id'], 'kadro': veri['toplam'] or 0})
                print(f'ilan: {ilan["id"]} karuseli hazır ({len(dosyalar)} slayt)')
    (cikti / 'is.json').write_text(json.dumps({'zaman': simdi.isoformat(timespec='seconds'), 'isler': isler},
                                              ensure_ascii=False, indent=1), encoding='utf-8')
    return isler


# ---------------------------------------------------------------- Instagram
def _bekle(taban, kap_id, anahtar, deneme=60, aralik=5):
    from sosyal_yayinla import YayinHatasi, _istek
    for _ in range(deneme):
        durum = _istek(f'{taban}/{kap_id}?fields=status_code,status&access_token={urllib.parse.quote(anahtar)}')
        kod = durum.get('status_code')
        if kod == 'FINISHED':
            return True
        if kod in ('ERROR', 'EXPIRED'):
            raise YayinHatasi(f'Instagram dosyayı işleyemedi: {durum.get("status")}')
        time.sleep(aralik)
    raise YayinHatasi('Instagram işleme zaman aşımı')


def instagram_hikaye(video_url, ortam=None, aralik=5):
    from sosyal_yayinla import IG_SURUM, YayinHatasi, _env, _istek
    ig_id, anahtar = ortam or _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI') or (None, None)
    if not ig_id:
        return None
    taban = f'https://graph.instagram.com/{IG_SURUM}'
    kap = _istek(f'{taban}/{ig_id}/media', veri={'media_type': 'STORIES', 'video_url': video_url, 'access_token': anahtar})
    if not kap.get('id'):
        raise YayinHatasi(f'Instagram hikâye kapsayıcısı oluşturulamadı: {kap}')
    _bekle(taban, kap['id'], anahtar, aralik=aralik)
    yayin = _istek(f'{taban}/{ig_id}/media_publish', veri={'creation_id': kap['id'], 'access_token': anahtar})
    return {'id': yayin.get('id')}


def instagram_karusel(resim_urller, metin, ortam=None, aralik=5):
    from sosyal_yayinla import IG_SURUM, YayinHatasi, _env, _istek
    ig_id, anahtar = ortam or _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI') or (None, None)
    if not ig_id:
        return None
    if not 2 <= len(resim_urller) <= 10:
        raise YayinHatasi(f'Karusel 2–10 görsel ister, {len(resim_urller)} verildi')
    taban = f'https://graph.instagram.com/{IG_SURUM}'
    cocuklar = []
    for url in resim_urller:
        kap = _istek(f'{taban}/{ig_id}/media', veri={'image_url': url, 'is_carousel_item': 'true', 'access_token': anahtar})
        if not kap.get('id'):
            raise YayinHatasi(f'Instagram karusel öğesi oluşturulamadı: {kap}')
        cocuklar.append(kap['id'])
    for c in cocuklar:
        _bekle(taban, c, anahtar, aralik=aralik)
    kap = _istek(f'{taban}/{ig_id}/media', veri={'media_type': 'CAROUSEL', 'children': ','.join(cocuklar),
                                                 'caption': metin, 'access_token': anahtar})
    if not kap.get('id'):
        raise YayinHatasi(f'Instagram karusel kapsayıcısı oluşturulamadı: {kap}')
    _bekle(taban, kap['id'], anahtar, aralik=aralik)
    yayin = _istek(f'{taban}/{ig_id}/media_publish', veri={'creation_id': kap['id'], 'access_token': anahtar})
    return {'id': yayin.get('id')}


# ---------------------------------------------------------------- Facebook sayfası
def _facebook_ortam():
    """(taban, sayfa, başlıklar) ya da anahtar yoksa None. Anahtarın seçili sayfaya ait olduğu her çalışmada doğrulanır."""
    from sosyal_yayinla import FB_SURUM, YayinHatasi, _env, _facebook_istek
    ortam = _env('FB_SAYFA_ID', 'FB_ERISIM_ANAHTARI')
    if not ortam:
        return None
    sayfa, anahtar = ortam
    if not sayfa.isdigit():
        raise YayinHatasi('FB_SAYFA_ID sayısal olmalı')
    taban, basliklar = f'https://graph.facebook.com/{FB_SURUM}', {'Authorization': f'Bearer {anahtar}'}
    if str(_facebook_istek(f'{taban}/me?fields=id', basliklar=basliklar).get('id')) != sayfa:
        raise YayinHatasi('Facebook anahtarı seçilen sayfaya ait değil; yayın durduruldu')
    return taban, sayfa, basliklar


def facebook_hikaye(video_url, fb):
    """Sayfa hikâyesi: video_stories start → rupload (file_url) → finish."""
    from sosyal_yayinla import YayinHatasi, _facebook_istek
    taban, sayfa, b = fb
    bas = _facebook_istek(f'{taban}/{sayfa}/video_stories', veri={'upload_phase': 'start'}, basliklar=b)
    video_id, yukle = bas.get('video_id'), bas.get('upload_url')
    if not video_id or not yukle or urllib.parse.urlsplit(yukle).netloc != 'rupload.facebook.com':
        raise YayinHatasi('Facebook hikâye yükleme oturumu açılamadı')
    tamam = _facebook_istek(yukle, yontem='POST', zaman_asimi=600,
                            basliklar={'Authorization': b['Authorization'].replace('Bearer', 'OAuth'), 'file_url': video_url})
    if not tamam.get('success'):
        raise YayinHatasi('Facebook hikâye videosunu kabul etmedi')
    son = _facebook_istek(f'{taban}/{sayfa}/video_stories', veri={'upload_phase': 'finish', 'video_id': video_id}, basliklar=b)
    if not son.get('success'):
        raise YayinHatasi('Facebook hikâyeyi yayınlamadı')
    return {'id': str(son.get('post_id') or video_id)}


def _fb_aciklama(i):
    """Facebook açıklamasına UTM'li bağlantı bloğu ekler (IG/TikTok'ta bağlantı tıklanmaz)."""
    import sosyal_baglanti
    return sosyal_baglanti.aciklama_baglantili(
        {'aciklama': i['aciklama'], 'tur': i['tur'], 'zaman': datetime.now().isoformat()}, 'facebook')


def facebook_karusel(resim_urller, metin, fb):
    """Çok fotoğraflı sayfa gönderisi: her görsel yayınlanmadan yüklenir, sonra tek gönderide birleştirilir."""
    from sosyal_yayinla import YayinHatasi, _facebook_istek
    taban, sayfa, b = fb
    veri = {'message': metin, 'published': 'true'}
    for n, url in enumerate(resim_urller):
        foto = _facebook_istek(f'{taban}/{sayfa}/photos', veri={'url': url, 'published': 'false'}, basliklar=b, zaman_asimi=300)
        if not foto.get('id'):
            raise YayinHatasi('Facebook görseli yüklenemedi')
        veri[f'attached_media[{n}]'] = json.dumps({'media_fbid': foto['id']})
    yayin = _facebook_istek(f'{taban}/{sayfa}/feed', veri=veri, basliklar=b)
    if not yayin.get('id'):
        raise YayinHatasi('Facebook gönderiyi yayınlamadı')
    return {'id': yayin['id']}


# ---------------------------------------------------------------- TikTok (Buffer fotoğraf gönderisi)
def tiktok_karusel(resim_urller, metin, baslik=''):
    """Buffer ile TikTok fotoğraf (kaydırmalı) gönderisi; anahtar yoksa None. Kota için durum ayrıca sorulmaz."""
    import os
    from sosyal_yayinla import YayinHatasi, _buffer, buffer_kanal
    anahtar = os.environ.get('BUFFER_API_ANAHTARI', '').strip()
    if not anahtar:
        return None
    kanal = buffer_kanal(anahtar)
    gorseller = ' '.join('{ image: { url: %s } }' % json.dumps(u) for u in resim_urller[:35])
    meta = ' metadata: { tiktok: { title: %s } }' % json.dumps(baslik[:90], ensure_ascii=False) if baslik else ''
    sorgu = ('mutation { createPost(input: { text: %s channelId: %s schedulingType: automatic mode: shareNow '
             'assets: [%s]%s }) { ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }'
             % (json.dumps(metin[:2200], ensure_ascii=False), json.dumps(kanal), gorseller, meta))
    yanit = _buffer(sorgu, anahtar).get('createPost') or {}
    gonderi = yanit.get('post') or {}
    if not gonderi.get('id'):
        raise YayinHatasi(f"Buffer TikTok gönderisini kabul etmedi: {str(yanit.get('message'))[:200]}")
    return {'id': gonderi['id']}


# ---------------------------------------------------------------- yayın
def _kapali():
    import os
    return {p.strip().lower() for p in os.environ.get('SOSYAL_KAPALI', '').split(',') if p.strip()}


def _tiktok_bugun(gecmis_yolu, simdi):
    gun = simdi.date().isoformat()
    return sum(1 for g in gecmis_oku(gecmis_yolu) if g.get('tt_id') and str(g.get('zaman', ''))[:10] == gun)


def _baslik(i):
    return {'son-gun': 'Son günü yaklaşan kamu ilanları', 'kadro-raporu': 'Haftanın kadro raporu',
            'puan-bandi': 'Bu puanla nereye atanıldı?'}.get(i['tur']) or (i.get('aciklama') or '').split('\n')[0][2:]


def yayinla(cikti, taban_url, ortam=None, aralik=5, gecmis_yolu=GECMIS_YOLU, simdi=None):
    """is.json'daki işleri Instagram, Facebook ve TikTok'ta yayınlar.
    sonuc.json: [{tür, biçim, ilan_id?, instagram|facebook|tiktok: {id}|{hata}}]. Bir hata diğerlerini durdurmaz."""
    from sosyal_yayinla import YayinHatasi
    from site_uret import TR
    simdi = simdi or datetime.now(TR)
    cikti = Path(cikti)
    isler = json.loads((cikti / 'is.json').read_text(encoding='utf-8')).get('isler') or []
    taban_url = taban_url.rstrip('/')
    kapali = _kapali()
    fb = None
    if 'facebook' not in kapali:
        try:
            fb = _facebook_ortam()
        except Exception as hata:
            fb = hata
    # TikTok günlük sınırı: önce günlük türler, sonra en kalabalık alımlı ilanlar
    tt_hak = max(0, TT_GUNLUK - _tiktok_bugun(gecmis_yolu, simdi)) if 'tiktok' not in kapali else 0
    tt_sira = sorted((n for n, i in enumerate(isler) if i['bicim'] == 'karusel'),
                     key=lambda n: (isler[n]['tur'] == 'ilan', -(isler[n].get('kadro') or 0), n))
    tt_izin = set(tt_sira[:tt_hak])
    sonuc = []
    for n, i in enumerate(isler):
        adresler = [f'{taban_url}/{urllib.parse.quote(d)}' for d in i['dosyalar']]
        kayit = {'tur': i['tur'], 'bicim': i['bicim']}
        if i.get('ilan_id'):
            kayit['ilan_id'] = i['ilan_id']
        hikaye = i['bicim'] == 'hikaye'

        def calistir(ad):
            if ad == 'instagram':
                return instagram_hikaye(adresler[0], ortam, aralik) if hikaye else instagram_karusel(adresler, i['aciklama'], ortam, aralik)
            if ad == 'facebook':
                if isinstance(fb, Exception):
                    raise fb
                return facebook_hikaye(adresler[0], fb) if hikaye else facebook_karusel(adresler, _fb_aciklama(i), fb)
            return tiktok_karusel(adresler, i['aciklama'], _baslik(i))
        platformlar = [p for p, acik in (('instagram', 'instagram' not in kapali), ('facebook', fb is not None),
                                         ('tiktok', n in tt_izin)) if acik]
        for ad in platformlar:
            try:
                r = calistir(ad)
            except (YayinHatasi, OSError, ValueError) as hata:
                kayit[ad] = {'hata': str(hata)[:300]}
                print(f'::warning::{ad} {i["bicim"]} ({i["tur"]}) yayınlanamadı: {str(hata)[:300]}')
                continue
            if r is None:
                continue   # anahtar tanımlı değil
            kayit[ad] = {'id': r.get('id')}
            print(f'{ad} {i["bicim"]} yayında: {i["tur"]} {i.get("ilan_id") or ""} ({r.get("id")})')
        sonuc.append(kayit)
    (cikti / 'sonuc.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding='utf-8')
    return sonuc


def _idler(s):
    return {kisa + '_id': (s.get(ad) or {}).get('id') for ad, kisa in (('instagram', 'ig'), ('facebook', 'fb'), ('tiktok', 'tt'))
            if (s.get(ad) or {}).get('id')}


def kaydet(cikti, gecmis_yolu=GECMIS_YOLU, en_cok=1500):
    """En az bir platformda yayınlanan işleri sosyal/gorsel-gecmis.json'a ekler (en yeni en_cok kayıt). Eklenen sayı döner."""
    cikti = Path(cikti)
    try:
        zaman = json.loads((cikti / 'is.json').read_text(encoding='utf-8'))['zaman']
        sonuc = json.loads((cikti / 'sonuc.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, KeyError):
        return 0
    yeni = []
    for s in sonuc:
        idler = _idler(s)
        if idler:
            yeni.append(dict({'zaman': zaman, 'tur': s['tur'], 'bicim': s['bicim']},
                             **({'ilan_id': s['ilan_id']} if s.get('ilan_id') else {}), **idler))
    if not yeni:
        return 0
    gecmis = (gecmis_oku(gecmis_yolu) + yeni)[-en_cok:]
    Path(gecmis_yolu).write_text(json.dumps(gecmis, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return len(yeni)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('islem', choices=('uret', 'yayinla', 'kaydet'))
    p.add_argument('--cikti', default='gorsel-cikti')
    p.add_argument('--tur', choices=TURLER)
    p.add_argument('--bicim', choices=('hikaye', 'karusel'), action='append')
    p.add_argument('--yalniz-ilan', action='store_true', help='günlük programı atla, yalnız yeni ilan karuselleri')
    p.add_argument('--ilan', type=int, default=ILAN_CALISMA, help='en çok kaç ilan karuseli (0: hiç)')
    p.add_argument('--taban')
    a = p.parse_args(argv)
    if a.islem == 'uret':
        turler = [] if a.yalniz_ilan else [(a.tur, a.bicim or ['hikaye', 'karusel'])] if a.tur else None
        isler = uret(a.cikti, turler=turler, ilan_sayisi=0 if a.tur else a.ilan)
        print(f'{len(isler)} iş hazır.')
    elif a.islem == 'yayinla':
        if not a.taban:
            sys.exit('--taban gerekli')
        sonuc = yayinla(a.cikti, a.taban)
        if sonuc and not any(_idler(s) for s in sonuc):
            sys.exit('Hiçbir paylaşım yayınlanamadı.')
    else:
        print(f'{kaydet(a.cikti)} paylaşım geçmişe yazıldı.')


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
