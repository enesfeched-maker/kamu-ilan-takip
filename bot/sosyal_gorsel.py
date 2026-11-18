"""Instagram hikâye (story) ve kaydırmalı gönderi (karusel) yayını — 18 Kasım 2026'da onaylanan üç tür.

Görseller bot/sosyal_ornek.py ile üretilir (onaylı Reels görünümü, Kâğıt/Bordo). Reels akışından (sosyal.yml) ayrıdır:
geçmişi sosyal/gorsel-gecmis.json'da tutulur, böylece Reels'in renk sırası, tekrar engeli ve YouTube kotası etkilenmez.

Program (Türkiye saatiyle, günde bir çalışma ~11:00):
  her gün      son-gun      hikâye (son başvurusu 7 gün içinde biten ilanlar)
  çarşamba     son-gun      karusel
  perşembe     puan-bandi   hikâye + karusel (puan aralığı haftaya göre döner; verisi olmayan aralık atlanır)
  pazar        kadro-raporu hikâye + karusel (son 7 günün yeni ilanları)
Verisi yetmeyen tür o gün paylaşılmaz. Aynı gün aynı tür+biçim iki kez paylaşılmaz.

Instagram Login API: hikâye = media_type STORIES + video_url; karusel = her slayt için image_url (JPEG zorunlu) +
is_carousel_item, sonra media_type CAROUSEL + children + caption. Dosyalar önizleme sürümünden (GitHub Release) çekilir.

Kullanım: python bot/sosyal_gorsel.py uret --cikti gorsel-cikti [--tur son-gun --bicim hikaye]
          python bot/sosyal_gorsel.py yayinla --cikti gorsel-cikti --taban https://github.com/.../releases/download/ETIKET
          python bot/sosyal_gorsel.py kaydet --cikti gorsel-cikti"""
import argparse
import json
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GECMIS_YOLU = ROOT / 'sosyal' / 'gorsel-gecmis.json'
TURLER = ('son-gun', 'kadro-raporu', 'puan-bandi')
PALET = {'kadro-raporu': 'kagit', 'son-gun': 'bordo', 'puan-bandi': 'kagit'}
# Perşembe puan aralığı haftaya göre döner (ISO hafta numarası); verisi olmayan aralık atlanıp sıradaki denenir.
PUAN_ARALIKLARI = (('lisans', 70, 75), ('onlisans', 70, 75), ('lisans', 75, 80), ('ortaogretim', 70, 75),
                   ('lisans', 65, 70), ('onlisans', 75, 80), ('lisans', 80, 85), ('ortaogretim', 75, 80))
ETIKETLER = {'son-gun': ['#songün', '#kpss', '#kamuilanları', '#memuralımı'],
             'kadro-raporu': ['#kpss', '#kamuilanları', '#kadro', '#haftanınözeti', '#memuralımı'],
             'puan-bandi': ['#kpss', '#tabanpuan', '#kpsstercih', '#atama']}
TELEGRAM = {'son-gun': 'Yeni ilanlar ve son gün hatırlatmaları Telegram kanalımızda: @kpsstercihi (bağlantı profilde) 💛',
            'kadro-raporu': 'Her pazar haftanın özeti ve yeni ilanlar Telegram kanalımızda: @kpsstercihi (bağlantı profilde) 💛',
            'puan-bandi': 'Bütün taban puanları ve tercih robotu kpsstercihi.com\'da; yeni ilanlar Telegram\'da: @kpsstercihi 💛'}
SORULAR = {'son-gun': 'Başvurunu yaptın mı, yoksa son güne mi bıraktın? 👇',
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
    return any(g.get('tur') == tur and g.get('bicim') == bicim and str(g.get('zaman', ''))[:10] == gun and g.get('ig_id')
               for g in gecmis)


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
    if tur == 'son-gun':
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


def uret(cikti, simdi=None, turler=None, gecmis_yolu=GECMIS_YOLU, docs=ROOT / 'docs'):
    """Bugünün planındaki işleri üretir; cikti/is.json: [{tür, biçim, dosyalar, açıklama}]. İş yoksa boş liste."""
    import sosyal_motor as sm
    from kurum_gorseli import kurum_logosu
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    gecmis = gecmis_oku(gecmis_yolu)
    isler, acik = [], None
    for tur, bicimler in (turler or plan(simdi)):
        bicimler = [b for b in bicimler if not bugun_yapildi(gecmis, tur, b, simdi)]
        if not bicimler:
            print(f'{tur}: bugün zaten paylaşıldı.')
            continue
        if acik is None and tur != 'puan-bandi':
            acik = sm.acik_ilanlar(sm.ilanlari_yukle(docs), simdi)
        try:
            veri = tur_uret(tur, simdi, cikti / tur, acik or [], docs, kurum_logosu)
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
                dosyalar = []
                for jpg in sorted((cikti / tur).glob('karusel-*.jpg'))[:10]:   # Instagram karuseli en çok 10 öğe
                    ad = f'{tur}-{jpg.name}'
                    (cikti / ad).write_bytes(jpg.read_bytes())
                    dosyalar.append(ad)
                if len(dosyalar) >= 2:
                    isler.append({'tur': tur, 'bicim': 'karusel', 'dosyalar': dosyalar, 'aciklama': aciklama(tur, veri)})
        print(f'{tur}: {", ".join(bicimler)} hazır ({veri["hikaye_kare"]} hikâye karesi, {veri["karusel_slayt"]} slayt)')
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


def yayinla(cikti, taban_url, ortam=None, aralik=5):
    """is.json'daki işleri Instagram'da yayınlar; sonuc.json: [{tür, biçim, id | hata}]. Bir işin hatası diğerini durdurmaz."""
    from sosyal_yayinla import YayinHatasi
    cikti = Path(cikti)
    isler = json.loads((cikti / 'is.json').read_text(encoding='utf-8')).get('isler') or []
    taban_url = taban_url.rstrip('/')
    sonuc = []
    for i in isler:
        adresler = [f'{taban_url}/{urllib.parse.quote(d)}' for d in i['dosyalar']]
        try:
            if i['bicim'] == 'hikaye':
                r = instagram_hikaye(adresler[0], ortam, aralik)
            else:
                r = instagram_karusel(adresler, i['aciklama'], ortam, aralik)
            if r is None:
                sonuc.append(dict(tur=i['tur'], bicim=i['bicim'], hata='Instagram anahtarı yok'))
                print('Instagram anahtarı yok; yayın atlandı.')
                break
            sonuc.append(dict(tur=i['tur'], bicim=i['bicim'], id=r.get('id')))
            print(f'Instagram {i["bicim"]} yayında: {i["tur"]} ({r.get("id")})')
        except (YayinHatasi, OSError) as hata:
            sonuc.append(dict(tur=i['tur'], bicim=i['bicim'], hata=str(hata)[:300]))
            print(f'::warning::Instagram {i["bicim"]} ({i["tur"]}) yayınlanamadı: {str(hata)[:300]}')
    (cikti / 'sonuc.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding='utf-8')
    return sonuc


def kaydet(cikti, gecmis_yolu=GECMIS_YOLU, en_cok=400):
    """Başarılı paylaşımları sosyal/gorsel-gecmis.json'a ekler (yalnız büyür; en yeni en_cok kayıt). Eklenen sayı döner."""
    cikti = Path(cikti)
    try:
        zaman = json.loads((cikti / 'is.json').read_text(encoding='utf-8'))['zaman']
        sonuc = json.loads((cikti / 'sonuc.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, KeyError):
        return 0
    gecmis = gecmis_oku(gecmis_yolu)
    yeni = [{'zaman': zaman, 'tur': s['tur'], 'bicim': s['bicim'], 'ig_id': s['id']} for s in sonuc if s.get('id')]
    if not yeni:
        return 0
    gecmis = (gecmis + yeni)[-en_cok:]
    Path(gecmis_yolu).write_text(json.dumps(gecmis, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return len(yeni)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('islem', choices=('uret', 'yayinla', 'kaydet'))
    p.add_argument('--cikti', default='gorsel-cikti')
    p.add_argument('--tur', choices=TURLER)
    p.add_argument('--bicim', choices=('hikaye', 'karusel'), action='append')
    p.add_argument('--taban')
    a = p.parse_args(argv)
    if a.islem == 'uret':
        turler = [(a.tur, a.bicim or ['hikaye', 'karusel'])] if a.tur else None
        isler = uret(a.cikti, turler=turler)
        print(f'{len(isler)} iş hazır.')
    elif a.islem == 'yayinla':
        if not a.taban:
            sys.exit('--taban gerekli')
        sonuc = yayinla(a.cikti, a.taban)
        if sonuc and all(s.get('hata') for s in sonuc):
            sys.exit('Hiçbir paylaşım yayınlanamadı.')
    else:
        print(f'{kaydet(a.cikti)} paylaşım geçmişe yazıldı.')


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
