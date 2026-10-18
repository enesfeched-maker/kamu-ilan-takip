"""Günde iki sosyal medya paylaşımı (sabah/akşam) için konu seçer, kareleri ve videoyu üretir.

Konu adayları (puanı yüksek olan seçilir; aynı konu yakın zamanda paylaşıldıysa atlanır):
  haber     config.json sosyal.haberler: elle girilen büyük açıklamalar (38 bin sağlık personeli gibi)
  son_gun   bugün/yarın son başvurusu olan ilanlar (sabah öne çıkar)
  buyuk     son 3 günde görülen tek bir büyük alım (toplam >= 50 kişi)
  yeni      son 24 saatin yeni ilanları (akşam öne çıkar)
  kategori  şu an açık: lise mezunu / önlisans / KPSS'siz ilanlar
  rehber    ÖSYM taban puanlarından: en düşük puanla atanılan kadrolar, en çok kadro verilen meslekler
Google Trends Türkiye'de günün aramalarından biri adayın konusuyla eşleşirse aday öne çıkar.

Kullanım: python bot/sosyal_motor.py --vakit sabah --cikti sosyal-cikti [--video]"""
import argparse
import hashlib
import json
import re
import statistics
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

import sosyal_tasarim as st
from kart_tasarimlari import veri as kart_verisi
from siniflandir import akademik_ilan, kucuk
from site_uret import TR, _bitis

ROOT = Path(__file__).resolve().parent.parent
GECMIS_YOLU = ROOT / 'sosyal' / 'gecmis.json'
TRENDS_RSS = 'https://trends.google.com/trending/rss?geo=TR'
EN_COK_ILAN = 8
TEKRAR_GUN = {'kategori': 5, 'rehber': 12, 'buyuk': 30, 'haber': 3650}
ETIKET_TABAN = ['#kpss', '#kamuilanları', '#memuralımı', '#personelalımı']
TREND_KELIMELERI = ('kpss', 'memur', 'alım', 'alımı', 'atama', 'personel', 'işçi', 'öğretmen', 'polis', 'sağlık',
                    'ösym', 'kadro', 'ilan', 'bakanlığı', 'jandarma', 'asker', 'msb', 'emniyet', 'belediye', 'işkur')
DUZEY_ADI = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}


# ---------------------------------------------------------------- veri
def ilanlari_yukle(docs=ROOT / 'docs'):
    """Sitedeki gibi: elle kurallar uygulanır, kaynaklar arası kopyalar birleştirilir, yalnız esas kayıt kalır."""
    import kopya
    from site_uret import elle_uygula
    data = json.loads((docs / 'ilanlar.json').read_text(encoding='utf-8'))
    ilanlar = elle_uygula(data.get('ilanlar', []))
    try:
        kopyalar = kopya.kopya_bul(ilanlar)
        ilanlar = [i for i in kopya.birlestir(ilanlar, kopyalar) if i.get('id') not in kopyalar['kopya_of']]
    except Exception as hata:  # kopya birleştirme yalnız güzelleştirir; hata paylaşımı durdurmaz
        print(f'Uyarı: kopya birleştirme yapılamadı: {hata}')
    return ilanlar


def _zaman(iso):
    try:
        z = datetime.fromisoformat(iso or '')
    except ValueError:
        return None
    return z if z.tzinfo else z.replace(tzinfo=TR)


def acik_ilanlar(ilanlar, simdi):
    sonuc = []
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i):
            continue
        bitis = _bitis(i)
        if not bitis or bitis <= simdi or not kart_verisi(i, None, simdi)['kadrolar']:
            continue
        sonuc.append(i)
    return sorted(sonuc, key=lambda i: (_bitis(i), i.get('id') or ''))


def gecmis_oku(yol=GECMIS_YOLU):
    try:
        return json.loads(Path(yol).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def gecmis_yaz(gecmis, kayit, yol=GECMIS_YOLU):
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecmis = (gecmis + [kayit])[-200:]
    yol.write_text(json.dumps(gecmis, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def trendler(zaman_asimi=10):
    """Google Trends Türkiye günlük aramaları (başlıklar); erişilemezse boş liste."""
    try:
        req = urllib.request.Request(TRENDS_RSS, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=zaman_asimi) as r:
            kok = ElementTree.fromstring(r.read())
        return [(e.text or '').strip() for e in kok.iter('title')][1:]
    except Exception as hata:
        print(f'Trendler alınamadı: {hata}')
        return []


def ilgili_trendler(basliklar):
    return [b for b in basliklar if any(t.startswith(w) for t in kucuk(b).split() for w in TREND_KELIMELERI)]


# ---------------------------------------------------------------- metin yardımcıları
def _sec(secenekler, tohum):
    return secenekler[int(hashlib.sha1(tohum.encode()).hexdigest(), 16) % len(secenekler)]


def _kadro_sayisi(ilanlar, simdi):
    return sum(kart_verisi(i, None, simdi)['toplam'] or 0 for i in ilanlar)


def _etiketler(ozel, trend=None):
    """Instagram 5 etiketten fazlasını kısıtlıyor; en çok 5."""
    sonuc = []
    if trend:
        sonuc.append('#' + re.sub(r'[^\wçğıöşüÇĞİÖŞÜ]', '', trend.replace('İ', 'i').replace('I', 'ı').lower()))
    for e in list(ozel) + ETIKET_TABAN:
        if e not in sonuc:
            sonuc.append(e)
    return sonuc[:5]


def _ilan_satiri(i, simdi):
    v = kart_verisi(i, None, simdi)
    ne = f'{v["toplam"]} kişi' if v['toplam'] else (v['kadrolar'][0]['ad'] if v['kadrolar'] else 'alım')
    return f'• {st.kisa_kurum(i.get("kurum") or "")}: {ne} (son gün {st.tarih_yaz(_bitis(i))})'


# ---------------------------------------------------------------- adaylar
def _ilan_konusu(tur, anahtar, puan, ilanlar, simdi, kapak_satir, vurgu, rozet, giris, ozel_etiket, baslik,
                 kelimeler=()):
    ilanlar = ilanlar[:EN_COK_ILAN]
    return {
        'tur': tur, 'anahtar': anahtar, 'puan': puan, 'ilanlar': [i['id'] for i in ilanlar],
        'kelimeler': set(kelimeler) | {w for i in ilanlar for w in kucuk(i.get('kurum') or '').split() if len(w) > 3},
        'baslik': baslik, 'giris': giris, 'satirlar': [_ilan_satiri(i, simdi) for i in ilanlar],
        'etiketler': ozel_etiket,
        'kareler': lambda logo: [st.kapak(kapak_satir, vurgu, rozet,
                                          liste=[st.kisa_kurum(i.get('kurum') or '') for i in ilanlar],
                                          logolar=[logo(i) for i in ilanlar])]
        + [st.ilan_karesi(i, logo(i), n, len(ilanlar), simdi) for n, i in enumerate(ilanlar, 1)] + [st.kapanis()],
    }


def haber_adaylari(cfg, simdi):
    sonuc = []
    for h in (cfg.get('sosyal') or {}).get('haberler') or []:
        try:
            gun = datetime.fromisoformat(h['tarih']).date()
        except (KeyError, ValueError):
            continue
        if not 0 <= (simdi.date() - gun).days <= int(h.get('gun') or 1):   # 'gun': haberin kaç gün güncel sayılacağı
            continue
        sonuc.append({
            'tur': 'haber', 'anahtar': f'haber:{h.get("id") or h["tarih"]}', 'puan': 100, 'ilanlar': [],
            'kelimeler': {w for w in kucuk(' '.join(h.get('manset') or [])).split() if len(w) > 3},
            'baslik': h.get('baslik') or ' '.join(h.get('manset') or []).title(), 'giris': h.get('metin') or '',
            'satirlar': [], 'etiketler': h.get('etiketler') or ['#sondakika'],
            'kareler': lambda logo, h=h: [st.haber_karesi(h.get('etiket') or 'SON DAKİKA', h.get('manset') or [],
                                                          h.get('alinti') or '', h.get('kaynak') or '',
                                                          foto_no=h.get('foto_no')), st.kapanis()],
        })
    return sonuc


def son_gun_adaylari(acik, simdi, vakit):
    sonuc = []
    for fark, ad, puan in ((0, 'BUGÜN', 85), (1, 'YARIN', 75)):
        gun = simdi.date() + timedelta(days=fark)
        bitenler = [i for i in acik if _bitis(i).date() == gun]
        if not bitenler or (fark == 0 and vakit == 'aksam' and all(_bitis(i).hour < 22 for i in bitenler)):
            continue
        n = len(bitenler)
        sonuc.append(_ilan_konusu(
            'son_gun', f'son_gun:{gun}:{vakit}', puan + (10 if vakit == 'sabah' else 0), bitenler, simdi,
            [f'{ad} SON GÜN', f'{n} KAMU İLANI' if n > 1 else '1 KAMU İLANI'], (1,),
            f'Son başvuru {st.tarih_yaz(gun)}',
            _sec([f'⏰ {ad.title()} son gün! Başvurusu kapanmak üzere olan {n} kamu ilanı:',
                  f'⏰ Kaçırmak üzere olabilirsin: {ad.lower()} son başvuru günü olan {n} ilan var.'], f'{gun}{vakit}'),
            ['#songün', '#başvuru'], f'{ad.title()} Son Gün: {n} Kamu İlanı', ['son', 'gün']))
        break
    return sonuc


def yeni_adaylari(acik, simdi, vakit, son_paylasilan):
    yeniler = [i for i in acik if (_zaman(i.get('ilk_gorulme')) or simdi - timedelta(days=9)) >= simdi - timedelta(hours=24)
               and i['id'] not in son_paylasilan]
    if len(yeniler) < 2:
        return []
    n, kadro = len(yeniler), _kadro_sayisi(yeniler, simdi)
    return [_ilan_konusu(
        'yeni', f'yeni:{simdi.date()}:{vakit}', 70 + (10 if vakit == 'aksam' else 0), yeniler, simdi,
        ['SON 24 SAATTE', f'{n} YENİ KAMU İLANI', f'{kadro} KİŞİLİK ALIM' if kadro >= 20 else 'GÖZÜNDEN KAÇMASIN'], (1,),
        f'{st.tarih_yaz(simdi)} · son başvuru tarihleriyle',
        _sec([f'📢 Son 24 saatte {n} yeni kamu ilanı yayımlandı. Gözünden kaçan olmasın diye hepsini bir araya topladım:',
              f'📢 Son 24 saatte yayımlanan {n} kamu ilanı, son başvuru tarihleriyle:'], f'{simdi.date()}{vakit}'),
        ['#yeniilan', '#işilanı'], f'Son 24 Saatte {n} Yeni Kamu İlanı')]


def buyuk_adaylari(acik, simdi):
    sonuc = []
    for i in acik:
        z = _zaman(i.get('ilk_gorulme'))
        toplam = kart_verisi(i, None, simdi)['toplam'] or 0
        if toplam < 50 or not z or z < simdi - timedelta(days=3):
            continue
        kurum = st.kisa_kurum(i.get('kurum') or '')
        sonuc.append(_ilan_konusu(
            'buyuk', f'buyuk:{i["id"]}', 72 + min(toplam // 100, 10), [i], simdi,
            [st.k.tr_buyuk(kurum), f'{toplam} PERSONEL', 'ALACAK'], (1,), f'Son başvuru {st.tarih_yaz(_bitis(i))}',
            f'🚨 {kurum} {toplam} personel alacak. Kadrolar ve son başvuru tarihi görselde:',
            ['#alımvar', '#işilanı'], f'{kurum} {toplam} Personel Alacak'))
    return sorted(sonuc, key=lambda a: -a['puan'])[:1]


KATEGORILER = (
    ('lise', lambda i: 'ortaogretim' in (i.get('ogrenim') or []), ['LİSE MEZUNLARININ', 'BAŞVURABİLECEĞİ'],
     'Lise mezunlarının başvurabileceği', ['#lisemezunu', '#ortaöğretim']),
    ('onlisans', lambda i: 'onlisans' in (i.get('ogrenim') or []), ['ÖNLİSANS MEZUNLARININ', 'BAŞVURABİLECEĞİ'],
     'Önlisans mezunlarının başvurabileceği', ['#önlisans', '#kpssönlisans']),
    ('kpsssiz', lambda i: i.get('kpss') == 'kpsssiz', ['KPSS ŞARTI OLMADAN', 'BAŞVURULABİLECEK'],
     'KPSS şartı olmadan başvurulabilecek', ['#kpsssiz', '#kpsssizalım']),
)


def kategori_adaylari(acik, simdi):
    sonuc = []
    for ad, kosul, satirlar, cumle, etiket in KATEGORILER:
        uyan = [i for i in acik if kosul(i)]
        if len(uyan) < 3:
            continue
        n = min(len(uyan), EN_COK_ILAN)
        sonuc.append(_ilan_konusu(
            'kategori', f'kategori:{ad}', 50 + min(len(uyan), 10), uyan, simdi, satirlar + [f'{n} KAMU İLANI'], (2,),
            f'Şu an başvurusu açık · {st.tarih_yaz(simdi)}',
            f'📌 {cumle} {n} kamu ilanı şu an açık. Hepsini son başvuru tarihleriyle derledim:',
            etiket, f'{cumle.capitalize()} {n} Kamu İlanı'))
    return sonuc


def _puan_verisi(docs, duzey):
    try:
        d = json.loads((docs / 'puanlar' / f'{duzey}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, []
    donemler = sorted(d.get('donemler') or {})
    if not donemler:
        return None, []
    son = donemler[-1]
    return son, [r for r in d['donemler'][son] if (r.get('min') or 0) > 0 and r.get('unvan')]


def rehber_adaylari(docs=ROOT / 'docs'):
    from puan_sayfalari import baslik_hali, sayi, tam, donem_yaz
    sonuc = []
    for duzey, ad in DUZEY_ADI.items():
        donem, kayitlar = _puan_verisi(docs, duzey)
        if len(kayitlar) < 12:
            continue
        dy = donem_yaz(donem)
        dusuk, gorulen = [], set()
        for r in sorted(kayitlar, key=lambda r: r['min']):
            if r['unvan'] not in gorulen and len(dusuk) < 12:
                gorulen.add(r['unvan'])
                dusuk.append(r)
        satir_dusuk = [(baslik_hali(r['unvan']), f'{st.kisa_kurum(r.get("kurum") or "")} · {baslik_hali(r.get("il") or "")}',
                        sayi(r['min'])) for r in dusuk]
        sonuc.append({
            'tur': 'rehber', 'anahtar': f'rehber:dusuk:{duzey}:{donem}', 'puan': 40, 'ilanlar': [],
            'kelimeler': {'kpss', 'atama', 'puan', kucuk(ad)},
            'baslik': f'{ad} En Düşük Puanla Atanılan Kadrolar ({dy})',
            'giris': f'📊 KPSS {ad} {dy} yerleştirmesinde en düşük puanla atanılan kadrolar. '
                     f'Puanım düşük diye umudunu kesme; tercih yaparken işine yarayabilir:',
            'satirlar': [f'• {a}, {b}: {c}' for a, b, c in satir_dusuk[:6]],
            'etiketler': ['#kpsstercih', '#tabanpuan', f'#kpss{duzey}'],
            'kareler': lambda logo, ad=ad, dy=dy, s=satir_dusuk: [
                st.kapak([f'KPSS {st.k.tr_buyuk(ad)}', 'EN DÜŞÜK PUANLA', 'ATANILAN KADROLAR'], (1,),
                         f'{dy} yerleştirme sonuçları', ileri='Kaydırınca puanları göreceksin'),
                st.tablo_karesi(f'En düşük puanla atanılanlar ({ad})', s[:6], 1, 2, 'Kaynak: ÖSYM sayısal bilgiler'),
                st.tablo_karesi(f'En düşük puanla atanılanlar ({ad})', s[6:12], 2, 2, 'Kaynak: ÖSYM sayısal bilgiler'),
                st.kapanis()],
        })
        gruplar = {}
        for r in kayitlar:
            g = gruplar.setdefault(r['unvan'], {'kont': 0, 'min': []})
            g['kont'] += r.get('kontenjan') or 0
            g['min'].append(r['min'])
        cok = sorted(gruplar.items(), key=lambda x: -x[1]['kont'])[:12]
        satir_cok = [(baslik_hali(u), f'en düşük {sayi(min(g["min"]))} · ortanca {sayi(statistics.median(g["min"]))}',
                      tam(g['kont'])) for u, g in cok]
        sonuc.append({
            'tur': 'rehber', 'anahtar': f'rehber:cok:{duzey}:{donem}', 'puan': 40, 'ilanlar': [],
            'kelimeler': {'kpss', 'atama', 'kadro', kucuk(ad)},
            'baslik': f'{ad} En Çok Kadro Verilen Meslekler ({dy})',
            'giris': f'📊 KPSS {ad} {dy} yerleştirmesinde en çok kadro verilen meslekler ve atanılan puanlar:',
            'satirlar': [f'• {a}: {c} kadro ({b})' for a, b, c in satir_cok[:6]],
            'etiketler': ['#kpsstercih', '#kpssatama', f'#kpss{duzey}'],
            'kareler': lambda logo, ad=ad, dy=dy, s=satir_cok: [
                st.kapak([f'KPSS {st.k.tr_buyuk(ad)}', 'EN ÇOK KADRO', 'VERİLEN MESLEKLER'], (1,),
                         f'{dy} yerleştirme sonuçları', ileri='Kaydırınca listeyi göreceksin'),
                st.tablo_karesi(f'En çok kadro verilenler ({ad})', s[:6], 1, 2, 'Sağdaki sayı: toplam kadro'),
                st.tablo_karesi(f'En çok kadro verilenler ({ad})', s[6:12], 2, 2, 'Sağdaki sayı: toplam kadro'),
                st.kapanis()],
        })
    return sonuc


# ---------------------------------------------------------------- seçim
def konu_sec(adaylar, gecmis, simdi, trend_basliklari=()):
    yakin = {}
    for g in gecmis:
        z = _zaman(g.get('zaman'))
        if z:
            yakin[g.get('anahtar')] = max(z, yakin.get(g.get('anahtar'), z))
    son_tur = gecmis[-1].get('tur') if gecmis else None
    trend_kelime = {w for b in trend_basliklari for w in kucuk(b).split() if len(w) > 3}
    uygun = []
    for a in adaylar:
        z = yakin.get(a['anahtar'])
        if z and z > simdi - timedelta(days=TEKRAR_GUN.get(a['tur'], 3650)):
            continue
        puan = a['puan'] - (15 if a['tur'] == son_tur else 0)
        eslesen = [b for b in trend_basliklari if a['kelimeler'] & set(kucuk(b).split())]
        if eslesen or (a['kelimeler'] & trend_kelime):
            puan += 30
            a = dict(a, trend=(eslesen or [None])[0])
        uygun.append((puan, a))
    if not uygun:
        return None
    return max(uygun, key=lambda x: x[0])[1]


SORULAR = {
    'genel': ['Sen hangisine başvurmayı düşünüyorsun? 👇', 'Bu ilanlardan sana uygun olan var mı? 👇'],
    'rehber': ['Senin puanın kaç, hangi kadroyu düşünüyorsun? 👇', 'Listede seni şaşırtan bir kadro oldu mu? 👇'],
    'haber': ['Sen bu alımı bekleyenlerden misin? 👇', 'Hangi branşta kaç kadro açılmasını bekliyorsun? 👇'],
    'son_gun': ['Başvurunu yaptın mı, yoksa son güne mi bıraktın? 👇', 'Sen hangisine başvurdun? 👇'],
}
MUZIK_KLASORU = ROOT / 'sosyal' / 'muzik'


def muzik_sec(gecmis, tohum, klasor=MUZIK_KLASORU):
    """Telifsiz parçalardan biri; son 3 paylaşımda çalınanlar mümkünse tekrarlanmaz. Klasör boşsa None (sessiz video)."""
    parcalar = sorted(p for p in Path(klasor).glob('*') if p.suffix.lower() in ('.mp3', '.m4a', '.wav', '.aac'))
    if not parcalar:
        return None
    son = {g.get('muzik') for g in gecmis[-3:]}
    taze = [p for p in parcalar if p.name not in son] or parcalar
    return _sec(taze, tohum)


def metin_olustur(konu, vakit, simdi):
    etiketler = _etiketler(konu['etiketler'], konu.get('trend'))
    govde = [konu['giris']] + konu['satirlar'][:6]
    if len(konu['satirlar']) > 6:
        govde.append(f'…ve {len(konu["satirlar"]) - 6} ilan daha')
    kapanis = _sec(['Tüm ilanlar ve son başvuru tarihleri kpsstercihi.com\'da 💛',
                    'Bütün kamu ilanlarını tek yerde görmek için: kpsstercihi.com 💛'], f'{simdi.date()}{vakit}k')
    # Yorum ve paylaşım (DM) algoritmanın en güçlü sinyalleri: emir kipi yerine soru ve sıcak bir öneri.
    soru = _sec(SORULAR.get(konu.get('tur'), SORULAR['genel']), f'{simdi.date()}{vakit}s')
    takip = 'Başvuracak bir arkadaşın varsa ona da gönderebilirsin; takipte kalırsan yeni ilanlar ilk senin önüne düşer.'
    aciklama = '\n'.join(govde) + f'\n\n{soru}\n\n{kapanis}\n{takip}\n\n' + ' '.join(etiketler)
    baslik = konu['baslik']
    baslik = (baslik if len(baslik) <= 90 else baslik[:89].rstrip() + '…') + ' #shorts'
    return {'baslik': baslik, 'aciklama': aciklama[:2150], 'etiketler': etiketler}


def uret(vakit, cikti, simdi=None, cfg=None, docs=ROOT / 'docs', gecmis_yolu=GECMIS_YOLU, video=True, trend=True):
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    cfg = cfg if cfg is not None else json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    ilanlar = ilanlari_yukle(docs)
    acik = acik_ilanlar(ilanlar, simdi)
    gecmis = gecmis_oku(gecmis_yolu)
    son_paylasilan = {i for g in gecmis if (_zaman(g.get('zaman')) or simdi) > simdi - timedelta(days=3)
                      for i in g.get('ilanlar') or []}
    adaylar = (haber_adaylari(cfg, simdi) + son_gun_adaylari(acik, simdi, vakit) + buyuk_adaylari(acik, simdi)
               + yeni_adaylari(acik, simdi, vakit, son_paylasilan) + kategori_adaylari(acik, simdi) + rehber_adaylari(docs))
    tb = ilgili_trendler(trendler()) if trend else []
    konu = konu_sec(adaylar, gecmis, simdi, tb)
    if not konu:
        print('Paylaşılacak konu bulunamadı.')
        return None
    from kurum_gorseli import kurum_logosu
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    kareler = konu['kareler'](kurum_logosu)
    for n, im in enumerate(kareler, 1):
        im.save(cikti / f'{n:02d}.png', optimize=True)
    muzik = muzik_sec(gecmis, f'{simdi.date()}{vakit}m')
    if video:
        st.video_yaz(kareler, cikti / 'reel.mp4', muzik=muzik)
    metin = metin_olustur(konu, vakit, simdi)
    ozet = {'tur': konu['tur'], 'anahtar': konu['anahtar'], 'vakit': vakit, 'zaman': simdi.isoformat(timespec='seconds'),
            'kare': len(kareler), 'trend': konu.get('trend'), 'ilgili_trendler': tb[:10],
            'muzik': muzik.name if muzik else None, **metin}
    (cikti / 'paylasim.json').write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding='utf-8')
    gecmis_yaz(gecmis, {'zaman': ozet['zaman'], 'vakit': vakit, 'tur': konu['tur'], 'anahtar': konu['anahtar'],
                        'ilanlar': konu['ilanlar'], 'muzik': ozet['muzik']}, gecmis_yolu)
    print(f'Konu: {konu["anahtar"]} ({len(kareler)} kare)')
    return ozet


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--vakit', choices=('sabah', 'aksam'), required=True)
    p.add_argument('--cikti', default='sosyal-cikti')
    p.add_argument('--videosuz', action='store_true')
    a = p.parse_args()
    uret(a.vakit, a.cikti, video=not a.videosuz)
