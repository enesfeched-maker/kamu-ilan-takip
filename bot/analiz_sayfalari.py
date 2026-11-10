"""Veri analizi sayfaları (docs/analiz/): siteye özgü, hesaplanmış içerik (AdSense 'düşük değerli içerik' incelemesi, 1 Kasım 2026).

Kaynaklar: docs/puanlar/*.json (ÖSYM KPSS yerleştirme sayısal bilgileri) ve sitenin kendi derlediği ilanlar.
Her sayı veriden hesaplanır; yeterli veri yoksa grup ya da sayfa hiç yazılmaz. Hesaplar saf işlevlerdedir (test_analiz_sayfalari.py).
Kabuk puan_sayfalari.py yardımcılarını kullanır."""
import json
import re
import shutil
import statistics
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import puan_sayfalari as ps
from puan_sayfalari import esc, sayi, tam, donem_yaz, _donem_anahtar, _tablo, _crumbs, _kes, _kirinti_json, _kucuk

TR = timezone(timedelta(hours=3))
KLASOR = 'analiz'
SON_DONEM_SAYISI = 4        # il / kadro / kurum karşılaştırmaları son bu kadar dönemi kapsar
IL_ESIK = 10                # ilin analize girmesi için gereken en az kadro satırı
KADRO_ESIK = 10             # kadro unvanının sıralamaya girmesi için gereken en az toplam kontenjan
SIRALAMA_N = 20
KURUM_N = 30
ILAN_TOP_N = 15
AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
KAYNAK_OSYM = 'Kaynak: ÖSYM KPSS merkezi yerleştirme sayısal bilgileri.'
KAYNAK_ILAN = 'Kaynak: KPSS Tercihi\'nin derlediği ilanlar.'


def _tarih_yazi(d):
    return f'{d.day} {AY[d.month - 1]} {d.year}'


# ------------------------------------------------------------------ saf hesaplar
def sirali_donemler(donemler):
    return sorted(donemler, key=_donem_anahtar)


def son_satirlar(donemler, n=SON_DONEM_SAYISI):
    """(dönem listesi, satırlar) — son n dönemin tüm satırları."""
    secili = sirali_donemler(donemler)[-n:]
    return secili, [r for d in secili for r in donemler[d]]


def donem_araligi(donem_listesi):
    return donem_yaz(donem_listesi[0]) if len(donem_listesi) == 1 else f'{donem_yaz(donem_listesi[0])}–{donem_yaz(donem_listesi[-1])}'


def medyan(satirlar, alan='min'):
    """Boş (null) puanlar atlanır; hiç puan yoksa None."""
    p = ps._puanlar(satirlar, alan)
    return statistics.median(p) if p else None


def _p(x):
    return ps._p(x)


def donem_ozetleri(donemler):
    """Dönem sırasıyla: satır sayısı, kontenjan, yerleşen, doluluk yüzdesi, medyan ve en düşük en küçük puan."""
    sonuc = []
    for d in sirali_donemler(donemler):
        satirlar = donemler[d]
        if not satirlar:
            continue
        kont = sum(r.get('kontenjan') or 0 for r in satirlar)
        yer = sum(r.get('yerlesen') or 0 for r in satirlar)
        mins = ps._puanlar(satirlar, 'min')
        sonuc.append({'donem': d, 'satir': len(satirlar), 'kontenjan': kont, 'yerlesen': yer,
                      'doluluk': (yer / kont * 100) if kont else None,
                      'med': statistics.median(mins) if mins else None, 'en_dusuk': min(mins) if mins else None})
    return sonuc


def degisim_cumlesi(ozetler, ad):
    """Son iki puanlı dönemin medyan karşılaştırması; en az 2 puanlı dönem yoksa None."""
    puanli = [o for o in ozetler if o['med'] is not None]
    if len(puanli) < 2:
        return None
    son, onceki = puanli[-1], puanli[-2]
    fark = round(son['med'] - onceki['med'], 2)
    hareket = 'aynı kaldı' if fark == 0 else f'{sayi(abs(fark))} puan {"yükseldi" if fark > 0 else "düştü"}'
    return (f'{ad}: {donem_yaz(son["donem"])} döneminde en küçük puanların medyanı {sayi(son["med"])}; '
            f'{donem_yaz(onceki["donem"])} dönemine göre {hareket} ({sayi(onceki["med"])}).')


def il_ozetleri(satirlar, esik=IL_ESIK):
    """İl bazında {il, satir, kontenjan, med}; en az `esik` satırı ve en az bir puanı olan iller, medyan artan sırada."""
    gruplar = {}
    for r in satirlar:
        il = ps._duzgun(r.get('il'))
        if il:
            gruplar.setdefault(il, []).append(r)
    sonuc = []
    for il, rows in gruplar.items():
        med = medyan(rows)
        if len(rows) >= esik and med is not None:
            sonuc.append({'il': il, 'satir': len(rows), 'kontenjan': sum(r.get('kontenjan') or 0 for r in rows), 'med': med})
    return sorted(sonuc, key=lambda o: (o['med'], _kucuk(o['il'])))


def uc_uclar(liste, n):
    """Sıralı listeden (düşük, yüksek) n'şer öğe; çakışmasın diye n, listenin yarısını aşmaz."""
    n = min(n, len(liste) // 2)
    return (liste[:n], list(reversed(liste[-n:]))) if n else ([], [])


def adlar_cumlesi(oge_listesi, ad_alani, deger_alani='med'):
    return ', '.join(f'{o[ad_alani]} ({sayi(o[deger_alani])})' for o in oge_listesi)


def kadro_ozetleri(satirlar, esik=KADRO_ESIK):
    """Unvan bazında {unvan, kontenjan, satir, med}: son dönemlerde en az `esik` toplam kontenjanı ve bir puanı olanlar, medyan artan."""
    gruplar = {}
    for r in satirlar:
        u = ' '.join(str(r.get('unvan') or '').split())
        if u:
            gruplar.setdefault(u, []).append(r)
    sonuc = []
    for u, rows in gruplar.items():
        kont = sum(r.get('kontenjan') or 0 for r in rows)
        med = medyan(rows)
        if kont >= esik and med is not None:
            sonuc.append({'unvan': u, 'kontenjan': kont, 'satir': len(rows), 'med': med})
    return sorted(sonuc, key=lambda o: (o['med'], _kucuk(o['unvan'])))


def kurum_ozetleri(satirlar, en_cok=KURUM_N):
    """Kurum bazında en çok kontenjanlı `en_cok` kurum: {kurum, kontenjan, yerlesen, satir, med}."""
    gruplar = {}
    for r in satirlar:
        ad = ps._kurum(r.get('kurum'))
        if ad:
            gruplar.setdefault(ad, []).append(r)
    sonuc = [{'kurum': ad, 'kontenjan': sum(r.get('kontenjan') or 0 for r in rows), 'yerlesen': sum(r.get('yerlesen') or 0 for r in rows),
              'satir': len(rows), 'med': medyan(rows)} for ad, rows in gruplar.items()]
    sonuc = [o for o in sonuc if o['kontenjan'] > 0]
    return sorted(sonuc, key=lambda o: (-o['kontenjan'], _kucuk(o['kurum'])))[:en_cok]


def ilan_istatistikleri(kayitlar, top=ILAN_TOP_N):
    """kayitlar: [{'yayin': date|None, 'son': date|None, 'bas': date|None, 'kurum', 'il', 'ogrenim': [..], 'kadro': int|None}].
    Aylık ilan sayısı + bilinen kadro toplamı, en çok ilanlı il ve kurumlar, öğrenim dağılımı, başvuru süresi medyanı, kapsanan tarih aralığı."""
    if not kayitlar:
        return None
    aylar = {}
    for k in kayitlar:
        if k.get('yayin'):
            a = aylar.setdefault((k['yayin'].year, k['yayin'].month), {'ilan': 0, 'kadro': 0})
            a['ilan'] += 1
            a['kadro'] += k.get('kadro') or 0
    tarihler = [k['yayin'] for k in kayitlar if k.get('yayin')]
    iller = Counter(k['il'] for k in kayitlar if k.get('il'))
    kurumlar = Counter(k['kurum'] for k in kayitlar if k.get('kurum'))
    ogrenim = Counter()
    for k in kayitlar:
        for o in (k.get('ogrenim') or ['belirtilmemis']):
            ogrenim[o] += 1
    sureler = [(k['son'] - k['bas']).days for k in kayitlar if k.get('bas') and k.get('son') and k['son'] >= k['bas']]
    sirala = lambda c: sorted(c.items(), key=lambda kv: (-kv[1], _kucuk(kv[0])))[:top]
    return {'toplam': len(kayitlar), 'aylar': [(y, m, aylar[(y, m)]) for y, m in sorted(aylar)],
            'ilk': min(tarihler) if tarihler else None, 'son': max(tarihler) if tarihler else None,
            'iller': sirala(iller), 'kurumlar': sirala(kurumlar), 'ogrenim': ogrenim,
            'kadro_toplam': sum(k.get('kadro') or 0 for k in kayitlar), 'kadro_bilinen': sum(1 for k in kayitlar if k.get('kadro')),
            'sure_medyan': statistics.median(sureler) if sureler else None, 'sure_n': len(sureler)}


def _tarih(v):
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def ilan_kayitlari(ilanlar, harita=None, simdi=None):
    """Ham ilanlardan istatistik kaydı üretir. Akademik, kurum içi ve duyuru (düzeltme/iptal) kayıtları dışarıda kalır;
    süresi dolmuş ilanlar dahildir. Yayın günü, geçmişteki başlangıç tarihidir; başlangıcı gelecekte ya da bilinmeyen ilan
    sitenin ilk gördüğü güne yazılır. Kopya ayıklama çağıranın işidir."""
    bugun = (simdi or datetime.now(TR)).astimezone(TR).date()
    import kurum_sayfasi as ks
    import liste_verisi
    from siniflandir import akademik_ilan
    sonuc, adlar = [], {}
    for i in ilanlar:
        if i.get('duyuru_turu') or akademik_ilan(i):
            continue
        il = re.sub(r'\s*\+\d+$', '', liste_verisi.il_bul(i, harita) or '')
        il = il if il and liste_verisi._il_gecerli(il) else ''
        kanonik = ks.kurum_kanonik(i.get('kurum'))
        adlar.setdefault(kanonik, Counter())[ks.kurum_adi(i.get('kurum'))] += 1
        bas = _tarih(i.get('baslangic_zaman'))
        sonuc.append({'yayin': bas if bas and bas <= bugun else _tarih(i.get('ilk_gorulme')), 'bas': bas, 'son': _tarih(i.get('son_tarih')), 'kanonik': kanonik,
                      'il': il, 'ogrenim': [o for o in (i.get('ogrenim') or []) if o in dict(ps.DUZEYLER)],
                      'kadro': ks.kart_alanlari(i).get('toplam') or None})
    for k in sonuc:
        c = adlar.get(k['kanonik'])
        k['kurum'] = c.most_common(1)[0][0] if c and k['kanonik'] else ''
    return sonuc


# ------------------------------------------------------------------ sayfa kabuğu
def _sayfa(base, yol, baslik, aciklama, kirinti, icerik):
    """yol: '' (hub) ya da 'alt-klasor/'. (canonical, html)."""
    import site_uret as su
    derinlik = 1 + (1 if yol else 0)
    kok = '../' * derinlik
    canonical = base + KLASOR + '/' + yol
    ek = f'<meta property="og:url" content="{esc(canonical)}">' + _kirinti_json(base, kirinti)
    html = (su.sayfa_basi(baslik + ' | KPSS Tercihi', _kes(aciklama), esc(canonical), kok, ek_head=ek)
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok, "puanlar")}{icerik}{su.alt_html(kok)}</body></html>')
    return canonical, html


def _hero(kok, yol_adi, baslik, giris):
    kirinti = [('Analizler', f'{kok}analiz/' if yol_adi else None)] + ([(yol_adi, None)] if yol_adi else [])
    return (f'<section class="kp-hero"><div class="wrap">{_crumbs(kok, kirinti)}<span class="eyebrow">Veri analizi</span>'
            f'<h1>{esc(baslik)}</h1><p>{esc(giris)}</p></div></section>')


def _govde(bulgular, bolumler, kaynak, guncelleme):
    """bulgular: [str]; bolumler: [(başlık, html)]."""
    liste = ''.join(f'<li>{esc(b)}</li>' for b in bulgular)
    ust = f'<section class="bolum"><div class="bolum-bas"><h2>Öne çıkanlar</h2></div><ul>{liste}</ul></section>' if liste else ''
    govde = ''.join(f'<section class="bolum"><div class="bolum-bas"><h2>{esc(b)}</h2></div>{h}</section>' for b, h in bolumler)
    alt = f'<p class="kp-note">{esc(kaynak)} Hazırlayan: KPSS Tercihi Editörlüğü. Güncelleme: {esc(guncelleme)}</p>'
    return f'<main id="icerik" class="wrap kp-main">{ust}{govde}{alt}</main>'


def _kuruldu(veriler):
    return {s: (ad, v['donemler']) for s, (ad, v) in veriler.items() if v.get('donemler')}


# ------------------------------------------------------------------ sayfa içerikleri: her biri (başlık, açıklama, giriş, bulgular, bölümler, özet) ya da None
def taban_degisimi(veriler):
    bulgular, bolumler = [], []
    for slug, (ad, donemler) in _kuruldu(veriler).items():
        oz = donem_ozetleri(donemler)
        c = degisim_cumlesi(oz, ad)
        if not c or len(oz) < 2:
            continue
        bulgular.append(c)
        satirlar = [[esc(donem_yaz(o['donem'])), tam(o['satir']), tam(o['kontenjan']), tam(o['yerlesen']),
                     ('%' + sayi(o['doluluk'], 1)) if o['doluluk'] is not None else '—', _p(o['med']), _p(o['en_dusuk'])] for o in reversed(oz)]
        bolumler.append((f'{ad}: dönem dönem', _tablo(['Dönem', 'Kadro satırı', 'Kontenjan', 'Yerleşen', 'Doluluk', 'Medyan en küçük puan', 'En düşük puan'], satirlar)))
    if not bolumler:
        return None
    return {'baslik': 'KPSS taban puanları dönemden döneme nasıl değişti?', 'yol': 'taban-puan-degisimi/', 'ad': 'Taban puan değişimi',
            'aciklama': bulgular[0], 'giris': 'Her dönemin kadro satırları ÖSYM tablolarından toplanır; medyan, o dönemdeki kadroların en küçük puanlarının ortanca değeridir.',
            'bulgular': bulgular, 'bolumler': bolumler, 'kaynak': KAYNAK_OSYM, 'ozet': bulgular[0]}


def _il_baglantisi(il):
    """İl adı, kalıcı il sayfasına (/il/<slug>/) bağlantılı; her ilin sayfası vardır (il_sayfalari.yaz)."""
    import kurum_sayfasi as ks
    return f'<a href="../../il/{esc(ks._ascii_slug(il))}/">{esc(il)}</a>'


def il_il(veriler):
    bulgular, bolumler = [], []
    for slug, (ad, donemler) in _kuruldu(veriler).items():
        secili, satirlar = son_satirlar(donemler)
        oz = il_ozetleri(satirlar)
        if not oz:
            continue
        aralik = donem_araligi(secili)
        dusuk, yuksek = uc_uclar(oz, 5)
        if dusuk:
            bulgular.append(f'{ad} ({aralik}): medyan en küçük puanı en düşük iller {adlar_cumlesi(dusuk, "il")}; en yüksek iller {adlar_cumlesi(yuksek, "il")}.')
        tablo = _tablo(['İl', 'Kadro satırı', 'Kontenjan', 'Medyan en küçük puan'], [[_il_baglantisi(o['il']), tam(o['satir']), tam(o['kontenjan']), _p(o['med'])] for o in oz])
        bolumler.append((f'{ad}: iller ({aralik})', tablo + f'<p class="kp-note">En az {IL_ESIK} kadro satırı olan {tam(len(oz))} il listelenir; puanı olmayan satırlar medyana girmez.</p>'))
    if not bolumler:
        return None
    return {'baslik': 'İl il KPSS taban puanları', 'yol': 'il-il-taban-puanlari/', 'ad': 'İl il taban puanları',
            'aciklama': bulgular[0] if bulgular else 'İl bazında medyan KPSS taban puanları.',
            'giris': f'Son {SON_DONEM_SAYISI} dönemin kadro satırları il bazında gruplanır; medyan, o ilin kadrolarına yerleşenlerin en küçük puanlarının ortanca değeridir.',
            'bulgular': bulgular, 'bolumler': bolumler, 'kaynak': KAYNAK_OSYM, 'ozet': bulgular[0] if bulgular else ''}


def kadro_siralamasi(veriler, slug_haritasi=None, sayfa_var=None):
    """slug_haritasi: {düzey: {unvan: slug}}; sayfa_var(düzey_slug, slug) -> bool. İkisi de yoksa bağlantı verilmez."""
    bulgular, bolumler = [], []
    for slug, (ad, donemler) in _kuruldu(veriler).items():
        secili, satirlar = son_satirlar(donemler)
        oz = kadro_ozetleri(satirlar)
        dusuk, yuksek = uc_uclar(oz, SIRALAMA_N)
        if not dusuk:
            continue
        aralik = donem_araligi(secili)

        def ad_html(o, slug=slug):
            s = ((slug_haritasi or {}).get(slug) or {}).get(o['unvan'])
            ad_ = esc(ps.baslik_hali(o['unvan']))
            return f'<a href="../../kpss-taban-puanlari/{slug}/{s}/">{ad_}</a>' if s and sayfa_var and sayfa_var(slug, s) else ad_
        def tablo(liste):
            return _tablo(['Kadro (unvan)', 'Kontenjan', 'Medyan en küçük puan'], [[ad_html(o), tam(o['kontenjan']), _p(o['med'])] for o in liste])
        bulgular.append(f'{ad} ({aralik}): medyan puanı en düşük kadro {ps.baslik_hali(dusuk[0]["unvan"])} ({sayi(dusuk[0]["med"])}), en yüksek kadro {ps.baslik_hali(yuksek[0]["unvan"])} ({sayi(yuksek[0]["med"])}).')
        bolumler.append((f'{ad}: en düşük medyanlı {len(dusuk)} kadro ({aralik})', tablo(dusuk)))
        bolumler.append((f'{ad}: en yüksek medyanlı {len(yuksek)} kadro ({aralik})', tablo(yuksek)))
    if not bolumler:
        return None
    return {'baslik': 'KPSS kadro puan sıralaması', 'yol': 'kadro-puan-siralamasi/', 'ad': 'Kadro puan sıralaması',
            'aciklama': bulgular[0], 'giris': f'Son {SON_DONEM_SAYISI} dönemde toplam en az {KADRO_ESIK} kontenjanı olan kadro unvanları, en küçük puanlarının medyanına göre sıralanır.',
            'bulgular': bulgular, 'bolumler': bolumler, 'kaynak': KAYNAK_OSYM, 'ozet': bulgular[0]}


def kurum_kontenjanlari(veriler):
    bulgular, bolumler = [], []
    for slug, (ad, donemler) in _kuruldu(veriler).items():
        secili, satirlar = son_satirlar(donemler)
        oz = kurum_ozetleri(satirlar)
        if not oz:
            continue
        aralik = donem_araligi(secili)
        bulgular.append(f'{ad} ({aralik}): en çok kontenjanı olan kurum {oz[0]["kurum"]} ({tam(oz[0]["kontenjan"])} kontenjan).')
        bolumler.append((f'{ad}: en çok kontenjanlı {len(oz)} kurum ({aralik})', _tablo(
            ['Kurum', 'Kontenjan', 'Yerleşen', 'Kadro satırı', 'Medyan en küçük puan'],
            [[esc(o['kurum']), tam(o['kontenjan']), tam(o['yerlesen']), tam(o['satir']), _p(o['med'])] for o in oz])))
    if not bolumler:
        return None
    return {'baslik': 'Hangi kurumların kontenjanı çok?', 'yol': 'kurum-kontenjanlari/', 'ad': 'Kurum kontenjanları',
            'aciklama': bulgular[0], 'giris': f'Son {SON_DONEM_SAYISI} dönemde en çok kontenjan açan {KURUM_N} kurum, öğrenim düzeyine göre.',
            'bulgular': bulgular, 'bolumler': bolumler, 'kaynak': KAYNAK_OSYM, 'ozet': bulgular[0]}


def ilan_sayfasi(ist):
    if not ist or not ist['toplam']:
        return None
    ayd = ist['aylar']
    bulgular = []
    aralik = ''
    if ist['ilk'] and ist['son']:
        aralik = f'{_tarih_yazi(ist["ilk"])} – {_tarih_yazi(ist["son"])}'
        bulgular.append(f'{aralik} arasında yayımlanan {tam(ist["toplam"])} ilan incelendi; bunların {tam(ist["kadro_bilinen"])} tanesinde kadro sayısı belli, toplam {tam(ist["kadro_toplam"])} kadro.')
    else:
        bulgular.append(f'{tam(ist["toplam"])} ilan incelendi.')
    if ist['sure_medyan'] is not None:
        bulgular.append(f'Başlangıç ve son tarihi belli {tam(ist["sure_n"])} ilanda başvuru süresinin medyanı {sayi(ist["sure_medyan"], 0)} gündür.')
    if ist['iller']:
        bulgular.append(f'En çok ilanı olan il {ist["iller"][0][0]} ({tam(ist["iller"][0][1])} ilan).')
    if ist['kurumlar']:
        bulgular.append(f'En çok ilan veren kurum {ist["kurumlar"][0][0]} ({tam(ist["kurumlar"][0][1])} ilan).')
    bolumler = []
    if ayd:
        bolumler.append(('Aylara göre ilanlar', _tablo(['Ay', 'İlan sayısı', 'Bilinen kadro'],
                         [[f'{AY[m - 1]} {y}', tam(a['ilan']), tam(a['kadro'])] for y, m, a in ayd])))
    if ist['iller']:
        bolumler.append((f'En çok ilanı olan {len(ist["iller"])} il', _tablo(['İl', 'İlan sayısı'], [[esc(i), tam(n)] for i, n in ist['iller']])))
    if ist['kurumlar']:
        bolumler.append((f'En çok ilan veren {len(ist["kurumlar"])} kurum', _tablo(['Kurum', 'İlan sayısı'], [[esc(k), tam(n)] for k, n in ist['kurumlar']])))
    og = ist['ogrenim']
    if og:
        ad_ = {**ps_duzey_adlari(), 'belirtilmemis': 'Öğrenim düzeyi belirtilmemiş'}
        sirali = sorted(og.items(), key=lambda kv: (-kv[1], kv[0]))
        bolumler.append(('Öğrenim düzeyine göre ilanlar', _tablo(['Öğrenim düzeyi', 'İlan sayısı'], [[esc(ad_.get(k, k)), tam(n)] for k, n in sirali])
                         + '<p class="kp-note">Birden çok düzeye açık ilan her düzeyde ayrı sayılır.</p>'))
    return {'baslik': 'Kamu ilanı istatistikleri', 'yol': 'kamu-ilan-istatistikleri/', 'ad': 'Kamu ilanı istatistikleri',
            'aciklama': bulgular[0], 'giris': f'KPSS Tercihi\'nin derlediği {tam(ist["toplam"])} kamu ilanının aylık, il ve kurum dağılımı. Kapsanan tarih aralığı: {aralik or "belirsiz"}.',
            'bulgular': bulgular, 'bolumler': bolumler, 'kaynak': KAYNAK_ILAN, 'ozet': bulgular[0]}


def ps_duzey_adlari():
    return dict(ps.DUZEYLER)


# ------------------------------------------------------------------ yazım
def _veriler(docs):
    veriler = {}
    for slug, ad in ps.DUZEYLER:
        try:
            v = json.loads((docs / 'puanlar' / f'{slug}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if v.get('donemler'):
            veriler[slug] = (ad, v)
    return veriler


def _slug_haritasi(veriler):
    """puan_sayfalari ile aynı kural: toplam en az MIN_SATIR satırı olan unvanlara benzersiz slug."""
    sonuc = {}
    for slug, (ad, v) in veriler.items():
        grup = ps.unvanlari_grupla(v)
        sonuc[slug] = ps.benzersiz_sluglar([u for u, d in grup.items() if sum(len(r) for r in d.values()) >= ps.MIN_SATIR])
    return sonuc


def yaz(docs, base, ilanlar, simdi=None):
    """docs/analiz/ altını baştan yazar; sitemap adreslerini döndürür. `ilanlar`: kopyaları ayıklanmış ham ilan kayıtları."""
    docs = Path(docs)
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    if not base.endswith('/'):
        base += '/'
    shutil.rmtree(docs / KLASOR, ignore_errors=True)
    veriler = _veriler(docs)
    guncelleme = _tarih_yazi(simdi.date())
    sayfa_var = lambda d, s: (docs / ps.KLASOR / d / s / 'index.html').is_file()
    sayfalar = []
    kuruldu = _kuruldu(veriler)
    for uretici in (lambda: taban_degisimi(veriler), lambda: il_il(veriler),
                    lambda: kadro_siralamasi(veriler, _slug_haritasi(veriler), sayfa_var), lambda: kurum_kontenjanlari(veriler)):
        if kuruldu:
            try:
                s = uretici()
            except Exception as hata:
                print(f'Uyarı: analiz sayfası hesaplanamadı: {hata}')
                s = None
            if s:
                sayfalar.append(s)
    try:
        try:
            import liste_verisi
            harita = liste_verisi.il_haritasi(ilanlar)
        except Exception:
            harita = None
        s = ilan_sayfasi(ilan_istatistikleri(ilan_kayitlari(ilanlar, harita, simdi)))
        if s:
            sayfalar.append(s)
    except Exception as hata:
        print(f'Uyarı: ilan istatistikleri hesaplanamadı: {hata}')
    if not sayfalar:
        return []
    adresler = []
    for s in sayfalar:
        kok = '../../'
        kirinti = [('Ana sayfa', base), ('Analizler', base + KLASOR + '/'), (s['ad'], base + KLASOR + '/' + s['yol'])]
        icerik = _hero(kok, s['ad'], s['baslik'], s['giris']) + _govde(s['bulgular'], s['bolumler'], s['kaynak'], guncelleme)
        canonical, html = _sayfa(base, s['yol'], s['baslik'], s['aciklama'], kirinti, icerik)
        hedef = docs / KLASOR / s['yol'] / 'index.html'
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(html, encoding='utf-8')
        adresler.append(canonical)
    liste = ''.join(f'<li><a href="{esc(s["yol"])}">{esc(s["ad"])}</a> — {esc(s["ozet"])}</li>' for s in sayfalar if s.get('ozet'))
    giris = f'ÖSYM yerleştirme verilerinden ve sitenin derlediği ilanlardan hesaplanan {len(sayfalar)} analiz. Tüm sayılar veriden hesaplanır.'
    icerik = (_hero('../', '', 'Analizler', giris)
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Analizler</h2></div><ul>{liste}</ul>'
              f'<p class="kp-note">Güncelleme: {esc(guncelleme)}</p></section></main>')
    canonical, html = _sayfa(base, '', 'KPSS ve kamu ilanı veri analizleri', 'KPSS taban puanı değişimi, il il puanlar, kadro sıralaması ve kamu ilanı istatistikleri.',
                             [('Ana sayfa', base), ('Analizler', base + KLASOR + '/')], icerik)
    (docs / KLASOR).mkdir(parents=True, exist_ok=True)
    (docs / KLASOR / 'index.html').write_text(html, encoding='utf-8')
    return [canonical] + adresler
