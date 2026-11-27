"""KPSS taban puanı sayfaları (docs/kpss-taban-puanlari/): hub, düzey ve kadro (unvan) sayfaları.

docs/puanlar/*.json içindeki ÖSYM yerleştirme sayısal bilgilerinden, arama motorlarının tarayabileceği statik sayfalar üretir.
Kabuk (üst/alt bilgi, stiller) site_uret.py yardımcılarını kullanır; kadro sayfası en az MIN_SATIR kayıt gerektirir."""
import html
import json
import re
import shutil
import statistics
from pathlib import Path

from kurum_sayfasi import _ascii_slug

DUZEYLER = (('lisans', 'Lisans'), ('onlisans', 'Önlisans'), ('ortaogretim', 'Ortaöğretim'))
MIN_SATIR = 3
MIN_DIZIN_SATIR = 3   # 15 Kasım 2026: 5'ten indi; kadro sayfası artık kısa cevap + kurum tablosu taşıyor, incelik ince_sayfa'da kelimeyle süzülür
ACIK_N = 15   # kadro ve düzey sayfasında gösterilen en çok açık ilan
ARALIK = 5              # 'bu puanla nereye atanılır' sayfalarının puan aralığı genişliği
MIN_ARALIK_SATIR = 10   # daha az kadrolu aralık sayfası açık kalır, dizine ve reklama girmez (15 Kasım 2026: 20'den indi; incelik ince_sayfa'da ayrıca süzülür)
ARALIK_N = 150          # aralık sayfasındaki kadro kadro dökümde en çok satır
ARALIK_IL_N = 15
MIN_BOLUM_SATIR = 10   # bölüm sayfası için son BOLUM_DONEM dönemde bölümü adıyla/koduyla arayan, puanı olan en az bu kadar kadro gerekir; azı için sayfa hiç açılmaz (ince sayfa üretilmez)
BOLUM_DONEM = 4         # bölüm sayfaları yalnız son bu kadar dönemin verisinden üretilir
BOLUM_N = 150          # bölüm sayfasındaki kadro kadro dökümde en çok satır
KLASOR = 'kpss-taban-puanlari'
NOT = 'Veriler ÖSYM\'nin yayımladığı sayısal bilgilerden derlenmiştir; resmî sonuç için ÖSYM\'yi kontrol edin.'


def esc(v):
    return html.escape(str(v if v is not None else ''), quote=True)


def sayi(x, k=2):
    """Türkçe ondalık: 71,23 (binlik ayraç yok)."""
    return f'{x:.{k}f}'.replace('.', ',')


def tam(n):
    return f'{int(n):,}'.replace(',', '.')


def donem_yaz(d):
    return d.replace('-', '/')


def _kucuk(s):
    return s.replace('İ', 'i').replace('I', 'ı').lower()


def baslik_hali(s):
    """'HEMŞİRE YARDIMCISI' -> 'Hemşire Yardımcısı' (Türkçe i/ı doğru)."""
    out = []
    for w in s.split():
        k = _kucuk(w)
        if out and k in ('ve', 'ile', 'veya'):
            out.append(k)
            continue
        ilk = 'İ' if k[0] == 'i' else k[0].upper()
        out.append(ilk + k[1:])
    return ' '.join(out)


def _donem_anahtar(d):
    y, _, n = d.partition('-')
    return (int(y), int(n or 0))


def _puanlar(satirlar, alan):
    return [r[alan] for r in satirlar if isinstance(r.get(alan), (int, float))]


def _ozet(satirlar):
    mins, maks = _puanlar(satirlar, 'min'), _puanlar(satirlar, 'max')
    return {
        'kadro': len(satirlar),
        'kontenjan': sum(r.get('kontenjan') or 0 for r in satirlar),
        'yerlesen': sum(r.get('yerlesen') or 0 for r in satirlar),
        'min': min(mins) if mins else None,
        'ort': sum(mins) / len(mins) if mins else None,
        'med': statistics.median(mins) if mins else None,
        'max': max(maks) if maks else None,
    }


def _p(x, k=2):
    return sayi(x, k) if x is not None else '—'


def unvanlari_grupla(veri):
    """{unvan: {dönem: [satır, ...]}} — unvan boşlukları sadeleştirilmiş, büyük harfli ad."""
    g = {}
    for d, satirlar in veri['donemler'].items():
        for r in satirlar:
            u = ' '.join(str(r.get('unvan') or '').split())
            if u:
                g.setdefault(u, {}).setdefault(d, []).append(r)
    return g


def benzersiz_sluglar(adlar):
    """Aynı slug çıkan adlara -2, -3 eki; sıra sabit (alfabetik)."""
    gorulen, sonuc = set(), {}
    for ad in sorted(adlar):
        taban = _ascii_slug(ad)[:80].strip('-') or 'kadro'
        s, n = taban, 2
        while s in gorulen:
            s = f'{taban}-{n}'
            n += 1
        gorulen.add(s)
        sonuc[ad] = s
    return sonuc


# ------------------------------------------------------------------ sayfa kabuğu
def _su():
    import site_uret
    return site_uret


def _kurum(k):
    from kurum_sayfasi import kurum_adi
    return kurum_adi(k) if k else ''


def _duzgun(s):
    return _su()._duzgun(s) if s else ''


def _kirinti_json(base, parcalar):
    ogeler = [{'@type': 'ListItem', 'position': i, 'name': ad, 'item': url} for i, (ad, url) in enumerate(parcalar, 1)]
    j = json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': ogeler},
                   ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{j}</script>'


def _veri_seti_json(base, canonical, aciklama):
    """Taban puanları özgün derleme veri: Dataset işareti asistanların ve Google Veri Kümesi Arama'nın kaynağı tanımasını sağlar."""
    j = json.dumps({'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'KPSS Taban Puanları', 'description': aciklama, 'url': canonical,
                    'inLanguage': 'tr-TR', 'isAccessibleForFree': True, 'isBasedOn': 'https://www.osym.gov.tr/',
                    'creator': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}},
                   ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{j}</script>'


def _kes(s, n=160):
    return s if len(s) <= n else s[:n - 1].rstrip(' ,;.') + '…'


def kadro_dizinlenir(donemler):
    """Son iki dönemde en az MIN_DIZIN_SATIR kaydı olmayan kadro sayfası açık kalır, dizine ve reklama girmez (AdSense, 9 Kasım 2026)."""
    son_iki = sorted(donemler, key=_donem_anahtar)[-2:]
    return sum(len(donemler[d]) for d in son_iki) >= MIN_DIZIN_SATIR


def _sayfa(base, yol, derinlik, baslik, aciklama, kirinti, icerik, dizin=True):
    """yol: KLASOR'e göre ('' = hub). derinlik: index.html'in docs'a göre klasör derinliği."""
    su = _su()
    kok = '../' * derinlik
    canonical = base + KLASOR + '/' + yol
    aciklama = _kes(aciklama)
    ek = (f'<meta property="og:url" content="{esc(canonical)}">' + _kirinti_json(base, kirinti) + (_veri_seti_json(base, canonical, aciklama) if not yol else '')
          + ('' if dizin else '<meta name="robots" content="noindex,follow">'))
    govde = (su.sayfa_basi(baslik, aciklama, esc(canonical), kok, ek_head=ek)
             + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok, "puanlar")}{icerik}'
             + f'<p class="wrap kp-note" style="margin:24px auto">{esc(NOT)}</p>{su.alt_html(kok)}</body></html>')
    return canonical, govde


def _crumbs(kok, parcalar):
    """parcalar: [(ad, href|None)] — ilk 'Ana sayfa' otomatik."""
    ogeler = [f'<a href="{kok}">Ana sayfa</a>']
    for ad, href in parcalar:
        ogeler.append(f'<a href="{href}">{esc(ad)}</a>' if href else f'<span>{esc(ad)}</span>')
    return '<nav class="crumbs" aria-label="Konum">' + '<span aria-hidden="true">/</span>'.join(ogeler) + '</nav>'


def _tablo(basliklar, satirlar):
    th = ''.join(f'<th scope="col">{esc(b)}</th>' for b in basliklar)
    # mobilde tablo kartlara dönüşür: her hücre başlığını (data-et) yanında gösterir; ilk sütun kartın başlığıdır
    tr = ''.join('<tr>' + ''.join(f'<td>{h}</td>' if n == 0 else f'<td data-et="{esc(basliklar[n])}">{h}</td>' for n, h in enumerate(s)) + '</tr>' for s in satirlar)
    return f'<div class="tablo-kap"><table class="kp-tablo"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def _hero(kirinti_html, baslik, giris):
    return (f'<section class="kp-hero"><div class="wrap">{kirinti_html}<span class="eyebrow">KPSS yerleştirme taban puanları</span>'
            f'<h1>{esc(baslik)}</h1><p>{esc(giris)}</p></div></section>')


# ------------------------------------------------------------------ sayfalar
def acik_kadro_ilanlari(adaylar, duzey_slug, unvan=None, en_cok=ACIK_N):
    """adaylar: başvurusu açık liste kayıtları (son tarihe göre sıralı). Düzeyi açıkça `duzey_slug` olan, `unvan` verilmişse
    kadro unvanlarından biri onunla birebir aynı olan ilanlar; benzerlik ya da tahmin yok."""
    sade = lambda s: _kucuk(' '.join(str(s or '').split()))
    hedef = sade(unvan) if unvan else None
    return [k for k in adaylar or [] if duzey_slug in (k.get('ogrenim') or [])
            and (hedef is None or hedef in {sade(u) for u in (k.get('unvanlar') or [])})][:en_cok]


def _acik_bolum(baslik, liste, kok):
    if not liste:
        return ''
    import il_sayfalari
    return (f'<section class="bolum"><div class="bolum-bas"><h2>{esc(baslik)} <span class="sayi">{len(liste)}</span></h2></div>'
            f'{il_sayfalari.acik_satirlari(liste, kok)}</section>')


def kadro_cumleleri(donemler):
    """Hesaplanmış kısa tespitler (sabit dolgu yok): son dönem medyanı önceki dönemle, son dönemde en düşük/en yüksek puanlı il.
    Medyan karşılaştırması için puanı olan en az 2 dönem, il cümlesi için son dönemde il+puan bilen en az 3 satır gerekir."""
    puanli = sorted((d for d in donemler if _puanlar(donemler[d], 'min')), key=_donem_anahtar)
    cumleler = []
    if len(puanli) >= 2:
        son, onceki = puanli[-1], puanli[-2]
        a, b = statistics.median(_puanlar(donemler[son], 'min')), statistics.median(_puanlar(donemler[onceki], 'min'))
        fark = round(a - b, 2)
        if fark == 0:
            hareket = 'aynı kaldı'
        else:
            hareket = f'{sayi(abs(fark))} puan {"yükseldi" if fark > 0 else "düştü"}'
        cumleler.append(f'{donem_yaz(son)} döneminde en küçük puanların medyanı {sayi(a)}; {donem_yaz(onceki)} dönemine göre {hareket} ({sayi(b)}).')
    if puanli:
        satirlar = [r for r in donemler[puanli[-1]] if isinstance(r.get('min'), (int, float)) and _duzgun(r.get('il'))]
        if len(satirlar) >= 3:
            dusuk, yuksek = min(satirlar, key=lambda r: r['min']), max(satirlar, key=lambda r: r['min'])
            if _duzgun(dusuk['il']) != _duzgun(yuksek['il']):
                cumleler.append(f'{donem_yaz(puanli[-1])} döneminde en düşük puanla {_duzgun(dusuk["il"])} ({sayi(dusuk["min"])}), '
                                f'en yüksek puanla {_duzgun(yuksek["il"])} ({sayi(yuksek["min"])}) yerleşildi.')
    return cumleler


def kadro_sorulari(ad, duzey_ad, donemler):
    """Kadro sayfasının kısa cevapları (15 Kasım 2026 SEO denetimi: kadro sayfalarının çoğu ince kalıp dizin dışındaydı).
    Tamamı veriden: son dönemin en düşük puanı ve medyanı, kontenjan/yerleşen, en çok kadro açan kurumlar, dönem dönem kontenjan."""
    sirali = sorted(donemler, key=_donem_anahtar)
    son = sirali[-1]
    d, dz = donem_yaz(son), duzey_ad.lower()
    sc = []
    rows = [r for r in donemler[son] if isinstance(r.get('min'), (int, float))]
    if rows:
        en = min(rows, key=lambda r: (r['min'], str(r.get('kurum'))))
        yer = ', '.join(p for p in (_kurum(en.get('kurum')), _duzgun(en.get('il'))) if p)
        cevap = f'{d} döneminde {ad} ({dz}) kadrolarında en düşük yerleşme puanı {sayi(en["min"])} oldu' + (f' ({yer})' if yer else '') + '.'
        if len(rows) >= 2:
            cevap += f' Puanı açıklanan {tam(len(rows))} kadronun yarısında en küçük puan {sayi(statistics.median(r["min"] for r in rows))} ya da altındaydı.'
        sc.append((f'KPSS {ad} ({dz}) kaç puanla atanılır?', cevap + ' Her kadronun nitelik koşulları ayrıca aranır.'))
    oz = _ozet(donemler[son])
    if oz['kontenjan'] and oz['yerlesen']:
        bos = oz['kontenjan'] - oz['yerlesen']
        sc.append((f'{d} döneminde kaç {ad} kontenjanı vardı?',
                   f'{d} KPSS {dz} yerleştirmesinde {tam(oz["kadro"])} {ad} kadrosunda {tam(oz["kontenjan"])} kontenjan vardı; {tam(oz["yerlesen"])} kişi yerleşti'
                   + (f', {tam(bos)} kontenjan boş kaldı.' if bos > 0 else ', kontenjanların hepsi doldu.')))
    kurumlar = {}
    for x in sirali:
        for r in donemler[x]:
            k = _kurum(r.get('kurum'))
            if k:
                kurumlar[k] = kurumlar.get(k, 0) + 1
    if len(kurumlar) >= 2:
        ilk = sorted(kurumlar, key=lambda k: (-kurumlar[k], _kucuk(k)))[:3]
        sc.append((f'{ad} kadrosu en çok hangi kurumlarda açıldı?',
                   f'{donem_yaz(sirali[0])}–{d} arasındaki {len(sirali)} dönemde en çok {ad} kadrosu açan kurumlar: '
                   + ', '.join(f'{k} ({kurumlar[k]} kadro)' for k in ilk) + '.'))
    if len(sirali) >= 2:
        sc.append((f'{ad} kontenjanı dönemden döneme nasıl değişti?',
                   'Dönem dönem toplam kontenjan: ' + ', '.join(f'{donem_yaz(x)}: {tam(_ozet(donemler[x])["kontenjan"])}' for x in sirali) + '.'))
    return sc


def kurum_bolumu(ad, donemler):
    """Kurumlara göre (tüm dönemler): kadro sayısı, toplam kontenjan, en düşük puan; en az iki kurum varsa."""
    g = {}
    for x in donemler:
        for r in donemler[x]:
            k = _kurum(r.get('kurum'))
            if k:
                g.setdefault(k, []).append(r)
    if len(g) < 2:
        return ''
    satir = []
    for k in sorted(g, key=lambda k: (-len(g[k]), _kucuk(k)))[:15]:
        o = _ozet(g[k])
        satir.append([esc(k), tam(o['kadro']), tam(o['kontenjan']), _p(o['min'])])
    return (f'<section class="bolum"><div class="bolum-bas"><h2>{esc(ad)} kadrosu açan kurumlar <span class="sayi">{len(g)}</span></h2></div>'
            + _tablo(['Kurum', 'Kadro sayısı', 'Toplam kontenjan', 'En düşük puan'], satir) + '</section>')


def kadro_sayfasi(base, duzey_slug, duzey_ad, unvan, slug, donemler, ilk_yil, son_yil, acik=None):
    """donemler: {dönem: [satır]}; acik: bu unvanla başvurusu açık ilan kayıtları."""
    sirali = sorted(donemler, key=_donem_anahtar)
    son = sirali[-1]
    oz = _ozet(donemler[son])
    ad = baslik_hali(unvan)
    baslik = f'KPSS {ad} Taban Puanları ({duzey_ad}) — {ilk_yil}–{son_yil}'
    if len(baslik) > _su().TITLE_SINIRI:
        # Uzun unvanda başlık sondan kesilince '(Lisans)' / '(Önlisans)' düşüyor, iki sayfa aynı başlığı alıyordu.
        baslik = f'KPSS {ad} Taban Puanları ({duzey_ad})'
    if len(baslik) > _su().TITLE_SINIRI:
        baslik = f'{ad} Taban Puanları ({duzey_ad})'
    cumle = (f'{donem_yaz(son)} döneminde {tam(oz["kadro"])} kadroya {tam(oz["yerlesen"])} kişi yerleşti')
    if oz['min'] is not None:
        cumle += f'; en düşük puan {_p(oz["min"])}, en yüksek {_p(oz["max"])}'
    cumle += '.'
    toplam_kadro = sum(len(v) for v in donemler.values())
    ozet_p = (f'KPSS {duzey_ad.lower()} {ad} kadrosu için {len(sirali)} dönemde toplam {tam(toplam_kadro)} kadro yer aldı. '
              + cumle + ' Puanlar ÖSYM\'nin yayımladığı yerleştirme sayısal bilgilerindeki en küçük ve en büyük puanlardır; aşağıda dönem dönem özet ve son iki dönemin kadro kadro dökümü var.')
    aciklama = f'{ad} ({duzey_ad}) KPSS taban puanları: {cumle}'
    if len(aciklama) + 30 <= 160:
        aciklama += f' {len(sirali)} dönem karşılaştırması.'
    kok = '../../../'
    kir = [('KPSS Taban Puanları', '../../'), (duzey_ad, '../'), (ad, None)]
    ozet_satir = []
    for d in reversed(sirali):
        o = _ozet(donemler[d])
        ozet_satir.append([esc(donem_yaz(d)), tam(o['kadro']), tam(o['kontenjan']), _p(o['min']), _p(o['ort']), _p(o['max'])])
    ozet_tablo = _tablo(['Dönem', 'Kadro sayısı', 'Kontenjan', 'En düşük puan', 'Ortalama (en küçük puan)', 'En yüksek puan'], ozet_satir)
    detay = ''
    for d in reversed(sirali[-2:]):
        rows = sorted(donemler[d], key=lambda r: (r.get('min') if isinstance(r.get('min'), (int, float)) else 1e9, str(r.get('kurum'))))
        detay += (f'<section class="bolum"><div class="bolum-bas"><h2>{esc(donem_yaz(d))} dönemi kadro kadro puanlar <span class="sayi">{len(rows)}</span></h2></div>'
                  + _tablo(['Kurum', 'İl', 'Teşkilat', 'Kontenjan', 'Yerleşen', 'En küçük puan', 'En büyük puan'],
                           [[esc(_kurum(r.get('kurum'))), esc(_duzgun(r.get('il'))), esc(_duzgun(r.get('teskilat'))), tam(r.get('kontenjan') or 0),
                             tam(r.get('yerlesen') or 0), _p(r.get('min'), 3), _p(r.get('max'), 3)] for r in rows]) + '</section>')
    tespit = ''.join(f'<p>{esc(c)}</p>' for c in kadro_cumleleri(donemler))
    tespit = f'<section class="bolum">{tespit}</section>' if tespit else ''
    icerik = (_hero(_crumbs(kok, kir), f'KPSS {ad} Taban Puanları ({duzey_ad})', ozet_p)
              + f'<main id="icerik" class="wrap kp-main">{_acik_bolum(f"Başvurusu açık {ad} ilanları", acik, kok)}{tespit}<section class="bolum"><div class="bolum-bas"><h2>Dönem dönem özet</h2></div>{ozet_tablo}</section>{detay}'
              f'{kurum_bolumu(ad, donemler)}{_soru_bolumu(kadro_sorulari(ad, duzey_ad, donemler))}'
              f'<section class="bolum"><p><a href="../">← Tüm {esc(duzey_ad.lower())} kadroları</a> · <a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p></section></main>')
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/'),
               (ad, f'{base}{KLASOR}/{duzey_slug}/{slug}/')]
    return _sayfa(base, f'{duzey_slug}/{slug}/', 3, baslik, aciklama, kirinti, icerik, dizin=kadro_dizinlenir(donemler))


def duzey_sayfasi(base, duzey_slug, duzey_ad, grup, sluglar, son_donem, ilk_yil, son_yil, acik=None, araliklar=None, sorular=None, bolum_sayisi=0):
    """grup: {unvan: {dönem: [satır]}}; sluglar: bağlantılı unvanlar; araliklar: {alt: [satır]} — sayfası olan puan aralıkları."""
    aralik_h = (f'<section class="bolum"><div class="bolum-bas"><h2>Puanına göre bak</h2></div><p>{_aralik_baglantilari(araliklar)}</p></section>'
                if araliklar else '')
    bolum_h = (f'<section class="bolum"><div class="bolum-bas"><h2>Bölümüne göre bak</h2></div>'
               f'<p><a href="bolumler/">{tam(bolum_sayisi)} {esc(duzey_ad.lower())} bölümünün mezunları hangi kadrolara atanır? →</a></p></section>' if bolum_sayisi else '')
    kok = '../../'
    satirlar, toplam_kadro = [], 0
    for unvan in sorted(grup, key=lambda u: (_kucuk(u))):
        d = grup[unvan]
        son = max(d, key=_donem_anahtar)
        oz = _ozet(d[son])
        tum_min = [m for rows in d.values() for m in _puanlar(rows, 'min')]
        ad = baslik_hali(unvan)
        ad_h = f'<a href="{esc(sluglar[unvan])}/">{esc(ad)}</a>' if unvan in sluglar else esc(ad)
        toplam_kadro += oz['kontenjan'] if son == son_donem else 0
        satirlar.append([ad_h, esc(donem_yaz(son)), tam(oz['kontenjan']), _p(oz['min']),
                         _p(statistics.median(tum_min) if tum_min else None)])
    tablo = _tablo(['Kadro (unvan)', 'Son dönem', 'Son dönem kontenjan', 'Son dönem en düşük puan', 'Tüm dönemler medyan (en küçük puan)'], satirlar)
    baslik = f'KPSS {duzey_ad} Taban Puanları {donem_yaz(son_donem)} — Kadro Kadro En Düşük Puanlar'
    aciklama = (f'KPSS {duzey_ad.lower()} taban puanları: {tam(len(grup))} kadro unvanı için {ilk_yil}–{son_yil} dönemlerinde yerleşen adayların '
                f'en düşük ve en yüksek puanları. Son dönem: {donem_yaz(son_donem)}.')
    giris = (f'{ilk_yil}–{son_yil} arasındaki KPSS merkezi yerleştirme sonuçlarında {tam(len(grup))} farklı {duzey_ad.lower()} kadro unvanı yer aldı. '
             f'Her unvanın son göründüğü dönemdeki kontenjanı ve en düşük puanı ile tüm dönemlerin medyanı aşağıda; ayrıntı için unvana tıklayın.')
    kir = [('KPSS Taban Puanları', '../'), (duzey_ad, None)]
    icerik = (_hero(_crumbs(kok, kir), f'KPSS {duzey_ad} Taban Puanları ({donem_yaz(son_donem)})', giris)
              + f'<main id="icerik" class="wrap kp-main">{_acik_bolum(f"Başvurusu açık {duzey_ad.lower()} ilanları", acik, kok)}{aralik_h}{bolum_h}<section class="bolum"><div class="bolum-bas"><h2>{esc(duzey_ad)} kadroları <span class="sayi">{len(grup)}</span></h2></div>{tablo}'
              f'<p class="kp-note">Ayrıntı sayfası, en az {MIN_SATIR} kayıt bulunan unvanlar için vardır. Puanlar kadro bazında en küçük puanların özetidir.</p>'
              f'<p><a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p></section>{_soru_bolumu(sorular)}</main>')
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/')]
    return _sayfa(base, f'{duzey_slug}/', 2, baslik, aciklama, kirinti, icerik)


def aralik_slug(alt):
    return f'{alt}-{alt + ARALIK}-puan'


def araliklari_grupla(satirlar):
    """{alt sınır: [satır]} — en küçük puanı [alt, alt+ARALIK) aralığına düşen kadrolar; 100 puan son aralığa girer."""
    g = {}
    for r in satirlar:
        m = r.get('min')
        if isinstance(m, (int, float)):
            g.setdefault(min(int(m // ARALIK) * ARALIK, 100 - ARALIK), []).append(r)
    return g


def _aralik_baglantilari(araliklar, on=''):
    """araliklar: {alt: [satır]}; `on`: aralık klasörlerine göreli önek ('' düzey sayfası, '../' aralık sayfası)."""
    return ' · '.join(f'<a href="{on}{aralik_slug(a)}/">{a}–{a + ARALIK} puan</a> <span class="sayi">{len(araliklar[a])}</span>' for a in sorted(araliklar))


def aralik_sayfasi(base, duzey_slug, duzey_ad, alt, son, araliklar, sluglar, onceki=None):
    """'Bu puanla nereye atanılır' sayfası: son dönemde en küçük puanı [alt, alt+ARALIK) aralığındaki kadrolar.
    araliklar: araliklari_grupla(son dönem); onceki: (dönem, araliklari_grupla(o dönem)) ya da None. Tamamı veriden; tahmin yok."""
    ust = alt + ARALIK
    rows = sorted(araliklar[alt], key=lambda r: (r['min'], str(r.get('unvan')), str(r.get('kurum'))))
    toplam = sum(len(v) for v in araliklar.values())
    yeten = sum(len(v) for a, v in araliklar.items() if a <= alt)
    yerlesen = sum(r.get('yerlesen') or 0 for r in rows)
    d_yaz = donem_yaz(son)
    giris = (f'{d_yaz} KPSS {duzey_ad.lower()} yerleştirmesinde en küçük puanı {alt}–{ust} arasında olan {tam(len(rows))} kadro vardı; '
             f'bu kadrolara {tam(yerlesen)} kişi yerleşti. Puanı açıklanan {tam(toplam)} kadronun {tam(yeten)} tanesinde en küçük puan {ust} puanın altındaydı.')
    if onceki and onceki[1].get(alt):
        giris += f' {donem_yaz(onceki[0])} döneminde aynı aralıkta {tam(len(onceki[1][alt]))} kadro vardı.'
    baslik = f'KPSS {duzey_ad} {alt}–{ust} Puanla Nereye Atanılır? ({d_yaz})'
    aciklama = (f'KPSS {duzey_ad.lower()} {alt}–{ust} puanla nereye atanılır? {d_yaz} döneminde en küçük puanı bu aralıkta olan '
                f'{tam(len(rows))} kadroya {tam(yerlesen)} kişi yerleşti. Unvan, il ve kurum dökümü.')
    kok = '../../../'
    unvanlar = {}
    for r in rows:
        unvanlar.setdefault(' '.join(str(r.get('unvan') or '').split()), []).append(r)
    unvan_satir = []
    for u in sorted(unvanlar, key=lambda u: (-len(unvanlar[u]), _kucuk(u))):
        ad = baslik_hali(u) if u else '—'
        ad_h = f'<a href="../{esc(sluglar[u])}/">{esc(ad)}</a>' if u in sluglar else esc(ad)
        unvan_satir.append([ad_h, tam(len(unvanlar[u])), tam(sum(r.get('kontenjan') or 0 for r in unvanlar[u])), _p(min(r['min'] for r in unvanlar[u]))])
    iller = {}
    for r in rows:
        il = _duzgun(r.get('il'))
        if il:
            iller.setdefault(il, []).append(r)
    il_satir = [[esc(il), tam(len(iller[il])), _p(min(r['min'] for r in iller[il]))]
                for il in sorted(iller, key=lambda i: (-len(iller[i]), _kucuk(i)))[:ARALIK_IL_N]]
    il_bolum = (f'<section class="bolum"><div class="bolum-bas"><h2>İllere göre</h2></div>{_tablo(["İl", "Kadro sayısı", "En düşük puan"], il_satir)}</section>'
                if len(il_satir) >= 3 else '')
    dokum = _tablo(['Kadro (unvan)', 'Kurum', 'İl', 'Kontenjan', 'En küçük puan'],
                   [[esc(baslik_hali(' '.join(str(r.get('unvan') or '').split()))), esc(_kurum(r.get('kurum'))), esc(_duzgun(r.get('il'))),
                     tam(r.get('kontenjan') or 0), _p(r['min'], 3)] for r in rows[:ARALIK_N]])
    kisik = f'<p class="kp-note">En düşük puanlı ilk {ARALIK_N} kadro gösteriliyor.</p>' if len(rows) > ARALIK_N else ''
    diger = {a: v for a, v in araliklar.items() if a != alt}
    diger_h = f'<p>Diğer aralıklar: {_aralik_baglantilari(diger, "../")}</p>' if diger else ''
    kir = [('KPSS Taban Puanları', '../../'), (duzey_ad, '../'), (f'{alt}–{ust} puan', None)]
    icerik = (_hero(_crumbs(kok, kir), f'KPSS {duzey_ad} {alt}–{ust} Puanla Nereye Atanılır?', giris)
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Unvana göre <span class="sayi">{len(unvan_satir)}</span></h2></div>'
              + _tablo(['Kadro (unvan)', 'Kadro sayısı', 'Kontenjan', 'En düşük puan'], unvan_satir) + f'</section>{il_bolum}'
              f'<section class="bolum"><div class="bolum-bas"><h2>{esc(d_yaz)} dönemi kadro kadro puanlar <span class="sayi">{len(rows)}</span></h2></div>{dokum}{kisik}</section>'
              f'<section class="bolum">{diger_h}<p><a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p>'
              f'<p><a href="https://t.me/kpsstercihi" target="_blank" rel="noopener" data-a="telegram" data-a-x="aralik">Tercih kılavuzu çıkınca Telegram kanalında duyuruyoruz →</a></p></section></main>')
    yol = f'{duzey_slug}/{aralik_slug(alt)}/'
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/'),
               (f'{alt}–{ust} puan', f'{base}{KLASOR}/{yol}')]
    return _sayfa(base, yol, 3, baslik, aciklama, kirinti, icerik, dizin=len(rows) >= MIN_ARALIK_SATIR)


SORU_ESIKLERI = (70, 75, 80, 85)


def duzey_sorulari(duzey_ad, son_donem, araliklar):
    """Düzey sayfasının ve llms.txt'nin kısa soru-cevapları (arama motoru ve yapay zekâ asistanı doğrudan alıntılayabilsin).
    araliklar: araliklari_grupla(son dönem). Tamamı veriden hesaplanır; sabit dolgu ve tahmin yok."""
    rows = [r for v in araliklar.values() for r in v]
    if not rows:
        return []
    d, dz, n = donem_yaz(son_donem), duzey_ad.lower(), len(rows)
    en = min(rows, key=lambda r: (r['min'], str(r.get('unvan')), str(r.get('kurum'))))
    yer = ', '.join(p for p in (_kurum(en.get('kurum')), _duzgun(en.get('il'))) if p)
    unvan = baslik_hali(' '.join(str(en.get('unvan') or '').split()))
    sc = [(f'{d} KPSS {dz} en düşük taban puanı kaç?',
           f'{d} merkezi yerleştirmesinde en düşük puanla yerleşilen {dz} kadrosu {unvan}' + (f' ({yer})' if yer else '') + f' oldu: {sayi(en["min"])}.')]
    for esik in SORU_ESIKLERI:
        k = sum(1 for r in rows if r['min'] < esik)
        if 0 < k < n:
            sc.append((f'KPSS {dz} {esik} puanla atanılır mı?',
                       f'{d} döneminde puanı açıklanan {tam(n)} {dz} kadrosunun {tam(k)} tanesinde en küçük puan {esik} puanın altındaydı. '
                       'Her kadronun nitelik koşulları ayrıca aranır.'))
    dolu = max(araliklar, key=lambda a: (len(araliklar[a]), -a))
    if len(araliklar) > 1:
        sc.append((f'KPSS {dz} kadrolarının çoğu hangi puan aralığında?',
                   f'{d} döneminde en çok kadro {dolu}–{dolu + ARALIK} puan aralığındaydı: {tam(n)} kadronun {tam(len(araliklar[dolu]))} tanesi.'))
    return sc


def _soru_bolumu(sorular):
    if not sorular:
        return ''
    veri = {'@context': 'https://schema.org', '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question', 'name': s, 'acceptedAnswer': {'@type': 'Answer', 'text': c}} for s, c in sorular]}
    ld = json.dumps(veri, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e')
    return ('<section class="bolum"><div class="bolum-bas"><h2>Kısa cevaplar</h2></div>'
            + ''.join(f'<h3>{esc(s)}</h3><p>{esc(c)}</p>' for s, c in sorular) + f'<script type="application/ld+json">{ld}</script></section>')


def kisa_bilgiler(docs):
    """llms.txt için: [(düzey slug, düzey adı, son dönem, [(soru, cevap)], [dizindeki aralık alt sınırları])]."""
    sonuc = []
    for slug, ad in DUZEYLER:
        try:
            veri = json.loads((Path(docs) / 'puanlar' / f'{slug}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not veri.get('donemler'):
            continue
        son = max(veri['donemler'], key=_donem_anahtar)
        ar = araliklari_grupla(veri['donemler'][son])
        sonuc.append((slug, ad, son, duzey_sorulari(ad, son, ar), sorted(a for a in ar if len(ar[a]) >= MIN_ARALIK_SATIR)))
    return sonuc


def hub_sayfasi(base, ozetler, ilk_yil, son_yil):
    """ozetler: [(duzey_slug, duzey_ad, kadro_unvan_sayisi, son_donem, [(unvan_adi, slug)])]."""
    kok = '../'
    kartlar = ''.join(
        f'<li><a href="{s}/">KPSS {esc(ad)} taban puanları</a> — {tam(n)} kadro unvanı, son dönem {esc(donem_yaz(d))}</li>' for s, ad, n, d, _ in ozetler)
    one_cikan = ''.join(
        f'<h3>{esc(ad)} kadroları</h3><ul>' + ''.join(f'<li><a href="{s}/{esc(k)}/">KPSS {esc(u)} taban puanları</a></li>' for u, k in liste) + '</ul>'
        for s, ad, _, _, liste in ozetler if liste)
    baslik = f'KPSS Taban Puanları ({ilk_yil}–{son_yil})'
    aciklama = (f'KPSS lisans, önlisans ve ortaöğretim taban puanları ({ilk_yil}–{son_yil}): kadro kadro en düşük ve en yüksek yerleşme puanları, '
                f'dönem dönem karşılaştırma.')
    giris = (f'KPSS merkezi yerleştirmede kadrolara yerleşen adayların en küçük ve en büyük puanlarını {ilk_yil}–{son_yil} dönemleri için '
             f'kadro (unvan) bazında inceleyin. Tercih döneminde hangi puanın hangi kadroya yettiğini geçmiş yıllarla karşılaştırmak için kullanışlıdır.')
    icerik = (_hero(_crumbs(kok, [('KPSS Taban Puanları', None)]), baslik, giris)
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Öğrenim düzeyine göre taban puanları</h2></div><ul>{kartlar}</ul>'
              f'<p><a href="{kok}puanlar/">Puanını gir, hangi kadrolara yettiğini gör: tercih robotu →</a></p>'
              f'<p><a href="{kok}analiz/">Puan verilerinden analizler: değişim, il il karşılaştırma, kadro sıralaması →</a></p>'
              f'<p><a href="{kok}il/">İllere göre açık ilanlar ve taban puanları →</a></p></section>'
              + (f'<section class="bolum"><div class="bolum-bas"><h2>En çok yerleştirme yapılan kadrolar</h2></div>{one_cikan}</section>' if one_cikan else '')
              + '</main>')
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/')]
    return _sayfa(base, '', 1, baslik, aciklama, kirinti, icerik)


# ------------------------------------------------------------------ bölüm (üniversite bölümü) sayfaları
_TR_SIRA = {c: i for i, c in enumerate('abcçdefgğhıijklmnoöprsştuüvyz')}


def _tr_anahtar(s):
    """Türkçe alfabe sırası (ç, ğ, ı, ö, ş, ü doğru yerde)."""
    return [_TR_SIRA.get(c, 100 + ord(c)) for c in _kucuk(s)]


def bolum_gruplari(bolum_veri):
    """{küçük harfli ad: {'ad': büyük harfli ad, 'kodlar': {kod}}} — aynı adı taşıyan kodlar tek bölümde birleşir."""
    g = {}
    for kod, ad in (bolum_veri.get('bolumler') or {}).items():
        sade = ' '.join(str(ad or '').split())
        if not sade:
            continue
        o = g.setdefault(_kucuk(sade), {'ad': sade, 'kodlar': set()})
        o['kodlar'].add(str(kod))
    return g


def _liste_bolumleri(liste, kod_bolum, tum_kodlar):
    """Bir nitelik listesinin özel olarak kabul ettiği bölüm anahtarları. puanlar.js bolumDurumu ile aynı kural:
    tam kod eşleşmesi ya da 'NNNN-*' ön eki (kod, '-*' atılmış ön ekle başlıyorsa); '*' ve '?' özel sayılmaz."""
    bul = set()
    for e in liste:
        if e == '*' or e == '?':
            continue
        if e.endswith('-*'):
            on = e[:-1]
            bul.update(kod_bolum[k] for k in tum_kodlar if k.startswith(on))
        elif e in kod_bolum:
            bul.add(kod_bolum[e])
    return bul


def _liste_kodlari(liste, kod_bolum, tum_kodlar):
    """_liste_bolumleri ile aynı kural; bölüm adı yerine kabul edilen kodları döndürür."""
    bul = set()
    for e in liste:
        if e == '*' or e == '?':
            continue
        if e.endswith('-*'):
            bul.update(k for k in tum_kodlar if k.startswith(e[:-1]))
        elif e in kod_bolum:
            bul.add(e)
    return bul


def bolum_satirlari(veri, bolum_veri):
    """Son BOLUM_DONEM dönemde her bölümü adıyla/koduyla arayan kadrolar.
    Dönüş: ({bölüm anahtarı: [(dönem, satır)]}, tüm bölümlere açık ('*') kadro satırları [(dönem, satır)], kullanılan dönemler)."""
    gruplar = bolum_gruplari(bolum_veri)
    kod_bolum = {k: ad for ad, o in gruplar.items() for k in o['kodlar']}
    tum_kodlar = list(kod_bolum)
    donemler = sorted(veri['donemler'], key=_donem_anahtar)[-BOLUM_DONEM:]
    nit = bolum_veri.get('nitelikler') or {}
    ozel, acik = {}, []
    for d in donemler:
        listeler = nit.get(d) or {}
        onbellek = {}
        for r in veri['donemler'][d]:
            kodlar, hepsi = set(), False
            for n in r.get('nit') or []:
                l = listeler.get(n) or []
                if '*' in l:
                    hepsi = True
                anahtar = tuple(l)
                if anahtar not in onbellek:
                    onbellek[anahtar] = _liste_kodlari(l, kod_bolum, tum_kodlar)
                kodlar |= onbellek[anahtar]
            # bölüm, adını taşıyan BÜTÜN kodlar kabul ediliyorsa sayılır (puanlar.js 'uygun'; yalnız bir kısmı 'kismi'
            # olur ve sayılmaz) — /nereye/ aracının merkezi atama listesiyle aynı sonuç
            bul = {kod_bolum[k] for k in kodlar if gruplar[kod_bolum[k]]['kodlar'] <= kodlar}
            for b in bul:
                ozel.setdefault(b, []).append((d, r))
            if hepsi and not bul:
                acik.append((d, r))
    return ozel, acik, donemler


def bolum_slug_adlari(ozel):
    """Sayfası açılacak bölümler: puanı olan özel kadro sayısı en az MIN_BOLUM_SATIR."""
    return [b for b, l in ozel.items() if sum(1 for _, r in l if isinstance(r.get('min'), (int, float))) >= MIN_BOLUM_SATIR]


def _bolum_cta(kok, duzey_slug, ad):
    from urllib.parse import quote
    href = f'{kok}nereye/?d={duzey_slug}&b={quote(ad, safe="")}'
    return f'<p><a href="{esc(href)}">Puanınla şu an hangi ilanlara başvurabileceğini gör →</a></p>'


def bolum_sayfasi(base, duzey_slug, duzey_ad, bolum_ad, slug, satirlar, acik_sayi, donemler, dizin=True):
    """satirlar: [(dönem, satır)] — bu bölümü özel olarak kabul eden kadrolar; acik_sayi: aynı dönemlerde tüm bölümlere açık kadro sayısı."""
    ad = baslik_hali(bolum_ad)
    dz = duzey_ad.lower()
    puanli = [(d, r) for d, r in satirlar if isinstance(r.get('min'), (int, float))]
    bos = len(satirlar) - len(puanli)
    kont = sum(r.get('kontenjan') or 0 for _, r in satirlar)
    mins = [r['min'] for _, r in puanli]
    unvanlar = {}
    for _, r in satirlar:
        unvanlar.setdefault(' '.join(str(r.get('unvan') or '').split()) or '—', []).append(r)
    en_unvan = sorted(unvanlar, key=lambda u: (-len(unvanlar[u]), _kucuk(u)))
    ilk_d, son_d = donem_yaz(donemler[0]), donem_yaz(donemler[-1])
    baslik_h1 = f'{ad} mezunları KPSS ile hangi kadrolara atanır?'
    # uzun bölüm adında soru yarıda kesilmesin ("…hangi kadrolara"): sığan ilk kalıp seçilir
    sinir = _su().TITLE_SINIRI
    adaylar = [f'{baslik_h1} ({duzey_ad})', baslik_h1,
               f'{ad} mezunları KPSS kadroları ({duzey_ad})', f'{ad} mezunları KPSS kadroları',
               f'{ad} KPSS kadroları']
    baslik = next((b for b in adaylar if len(b) <= sinir), adaylar[-1])
    kisa = (f'{ilk_d}–{son_d} KPSS {dz} yerleştirmelerinde {ad} mezunlarının başvurabildiği {tam(len(satirlar))} kadro vardı; toplam kontenjan {tam(kont)}. '
            f'Yerleşilen kadrolarda en düşük taban puan {_p(min(mins))}, en yüksek {_p(max(mins))} oldu. '
            f'En çok kadro açılan unvan {baslik_hali(en_unvan[0])} ({tam(len(unvanlar[en_unvan[0]]))} kadro).')
    aciklama = (f'{ad} mezunları KPSS ile hangi kadrolara atanır? {ilk_d}–{son_d} dönemlerinde {tam(len(satirlar))} kadro, '
                f'taban puanlar {_p(min(mins), 0)}–{_p(max(mins), 0)}. Unvan, kurum ve il dökümü.')
    kok = '../../../../'
    # unvan özeti
    unvan_satir = []
    for u in en_unvan:
        rs = unvanlar[u]
        m = [r['min'] for r in rs if isinstance(r.get('min'), (int, float))]
        unvan_satir.append([esc(baslik_hali(u) if u != '—' else u), tam(len(rs)), tam(sum(r.get('kontenjan') or 0 for r in rs)),
                            _p(min(m)) if m else '—', _p(max(m)) if m else '—'])
    unvan_tablo = _tablo(['Kadro (unvan)', 'Kadro sayısı', 'Kontenjan', 'En düşük puan', 'En yüksek puan'], unvan_satir)
    # hesaplanmış kısa tespitler
    kurumlar, iller, donem_n = {}, {}, {}
    for d, r in satirlar:
        k = _kurum(r.get('kurum'))
        if k:
            kurumlar[k] = kurumlar.get(k, 0) + 1
        il = _duzgun(r.get('il'))
        if il:
            iller[il] = iller.get(il, 0) + 1
        donem_n[d] = donem_n.get(d, 0) + 1
    tespit = []
    if kurumlar:
        ilk = sorted(kurumlar, key=lambda k: (-kurumlar[k], _kucuk(k)))[:3]
        tespit.append(f'{ad} mezunlarına en çok kadro açan kurumlar: ' + ', '.join(f'{k} ({tam(kurumlar[k])} kadro)' for k in ilk) + '.')
    if iller:
        ilk = sorted(iller, key=lambda i: (-iller[i], _kucuk(i)))[:3]
        tespit.append('En çok kadro bulunan iller: ' + ', '.join(f'{i} ({tam(iller[i])} kadro)' for i in ilk) + '.')
    tespit.append('Dönem dönem kadro sayısı: ' + ', '.join(f'{donem_yaz(d)}: {tam(donem_n[d])}' for d in donemler if d in donem_n) + '.')
    if bos:
        tespit.append(f'Bu kadroların {tam(bos)} tanesine ilgili dönemde yerleşen olmadı; bunların puanı yoktur ve aşağıdaki dökümde yer almaz.')
    if acik_sayi:
        tespit.append(f'Ayrıca bu dönemlerde {tam(acik_sayi)} kadro tüm {dz} bölümlerine açıktı.')
    tespit_h = '<section class="bolum">' + ''.join(f'<p>{esc(c)}</p>' for c in tespit) + '</section>'
    # kadro kadro döküm
    rows = sorted(puanli, key=lambda x: (-_donem_anahtar(x[0])[0], -_donem_anahtar(x[0])[1], -x[1]['min'], str(x[1].get('kurum'))))
    dokum = _tablo(['Dönem', 'Kurum', 'İl', 'Kadro', 'Kontenjan', 'Taban puan'],
                   [[esc(donem_yaz(d)), esc(_kurum(r.get('kurum'))), esc(_duzgun(r.get('il'))),
                     esc(baslik_hali(' '.join(str(r.get('unvan') or '').split())) or '—'), tam(r.get('kontenjan') or 0), _p(r['min'], 3)]
                    for d, r in rows[:BOLUM_N]])
    kisik = f'<p class="kp-note">En yeni dönemden başlayarak ilk {BOLUM_N} kadro gösteriliyor.</p>' if len(rows) > BOLUM_N else ''
    kir = [('KPSS Taban Puanları', '../../../'), (duzey_ad, '../../'), ('Bölümler', '../'), (ad, None)]
    icerik = (_hero(_crumbs(kok, kir), baslik_h1, kisa)
              + f'<main id="icerik" class="wrap kp-main">{tespit_h}'
              f'<section class="bolum"><div class="bolum-bas"><h2>Kadro (unvan) özeti <span class="sayi">{len(unvan_satir)}</span></h2></div>{unvan_tablo}</section>'
              f'<section class="bolum"><div class="bolum-bas"><h2>Kadro kadro taban puanlar <span class="sayi">{len(rows)}</span></h2></div>{dokum}{kisik}</section>'
              f'<section class="bolum">{_bolum_cta(kok, duzey_slug, ad)}'
              f'<p><a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p>'
              f'<p><a href="../">← Tüm {esc(dz)} bölümleri</a></p></section></main>')
    yol = f'{duzey_slug}/bolumler/{slug}/'
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/'),
               ('Bölümler', f'{base}{KLASOR}/{duzey_slug}/bolumler/'), (ad, f'{base}{KLASOR}/{yol}')]
    return _sayfa(base, yol, 4, baslik, aciklama, kirinti, icerik, dizin=dizin)


def bolum_dizin_sayfasi(base, duzey_slug, duzey_ad, liste, donemler):
    """liste: [(bölüm adı, slug, kadro sayısı, en düşük puan)] — Türkçe alfabe sırasında."""
    dz = duzey_ad.lower()
    kok = '../../../'
    ilk_d, son_d = donem_yaz(donemler[0]), donem_yaz(donemler[-1])
    baslik = f'KPSS {duzey_ad} Bölümlerine Göre Atanabilecek Kadrolar'
    giris = (f'{ilk_d}–{son_d} KPSS {dz} yerleştirmelerinde {tam(len(liste))} bölümün mezunları için ayrı kadro ve taban puan dökümü var. '
             f'Bölümünüzü seçin; o bölümü özel olarak arayan kadroları, kurumları ve taban puanlarını görün.')
    aciklama = f'{tam(len(liste))} {dz} bölümü için KPSS ile atanılabilecek kadroların taban puanları ({ilk_d}–{son_d}). Bölümüne göre kadro, kurum ve il dökümü.'
    satir = [[f'<a href="{esc(s)}/">{esc(baslik_hali(a))}</a>', tam(n), _p(m)] for a, s, n, m in liste]
    kir = [('KPSS Taban Puanları', '../../'), (duzey_ad, '../'), ('Bölümler', None)]
    icerik = (_hero(_crumbs(kok, kir), baslik, giris)
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>{esc(duzey_ad)} bölümleri <span class="sayi">{len(liste)}</span></h2></div>'
              + _tablo(['Bölüm', 'Kadro sayısı', 'En düşük taban puan'], satir)
              + f'<p class="kp-note">Bölüm sayfası, son {BOLUM_DONEM} dönemde puanı olan en az {MIN_BOLUM_SATIR} kadro bulunan bölümler için vardır.</p>'
              f'<p><a href="../">← KPSS {esc(dz)} taban puanları</a> · <a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p></section></main>')
    yol = f'{duzey_slug}/bolumler/'
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/'),
               ('Bölümler', f'{base}{KLASOR}/{yol}')]
    return _sayfa(base, yol, 3, baslik, aciklama, kirinti, icerik)


def _bolum_uret(docs, base, slug, ad, veri, adresler):
    """Bir düzey için bölüm sayfalarını ve dizinini yazar; adresleri ekler, sayfa sayısını döndürür."""
    try:
        bv = json.loads((docs / 'puanlar' / f'{slug}-bolum.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    ozel, acik, donemler = bolum_satirlari(veri, bv)
    gruplar = bolum_gruplari(bv)
    secili = bolum_slug_adlari(ozel)
    if not secili:
        return 0
    import ince_sayfa
    sluglar = benzersiz_sluglar([gruplar[b]['ad'] for b in secili])
    liste, yeni = [], []
    for b in sorted(secili, key=_tr_anahtar):
        bolum_ad, s = gruplar[b]['ad'], sluglar[gruplar[b]['ad']]
        satirlar = ozel[b]
        ozel_idler = {id(r) for _, r in satirlar}
        acik_n = sum(1 for _, r in acik if id(r) not in ozel_idler)
        url, h = bolum_sayfasi(base, slug, ad, bolum_ad, s, satirlar, acik_n, donemler)
        # ince sayfa kalkanıyla aynı kelime ölçüsü: eşiğin altındaysa noindex yazılır ve site haritasına girmez
        dizin = ince_sayfa.ana_kelime_sayisi(h) >= ince_sayfa.MIN_KELIME
        if not dizin:
            url, h = bolum_sayfasi(base, slug, ad, bolum_ad, s, satirlar, acik_n, donemler, dizin=False)
        _yaz(docs, f'{slug}/bolumler/{s}', h)
        if dizin:
            yeni.append(url)
        puanli = [r['min'] for _, r in satirlar if isinstance(r.get('min'), (int, float))]
        liste.append((bolum_ad, s, len(satirlar), min(puanli)))
    url, h = bolum_dizin_sayfasi(base, slug, ad, liste, donemler)
    _yaz(docs, f'{slug}/bolumler', h)
    adresler.extend([url] + yeni)
    return len(liste)


def _yaz(docs, goreli, html_metin):
    p = docs / KLASOR / goreli / 'index.html'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_metin, encoding='utf-8')


def _degisim_yaz(url, acik):
    """Sayfadaki açık ilan listesinin son değiştiği gün site haritasına (lastmod) geçsin; açık ilan yoksa tarih yazılmaz."""
    try:
        import kurum_sayfasi as ks
        gun = ks.son_ilan_gunu(acik)
        if gun:
            ks.SON_DEGISIM[url] = gun
    except Exception:
        pass


def puan_sayfalarini_uret(docs, base, ilanlar=None, sayfali=None, noindex=None, simdi=None):
    """docs/kpss-taban-puanlari/ altını baştan yazar; üretilen mutlak adresleri döndürür.
    `ilanlar` (liste.json kayıtları) verilirse kadro ve düzey sayfalarına başvurusu açık ilanlar eklenir."""
    adaylar = []
    if ilanlar:
        from datetime import datetime
        import statik_icerik as si
        adaylar = si.sec(ilanlar, {k.get('key') for k in ilanlar} if sayfali is None else sayfali, noindex or set(),
                         simdi or datetime.now(si.TR), en_cok=len(ilanlar))
    docs = Path(docs)
    if not base.endswith('/'):
        base += '/'
    veriler = {}
    for slug, ad in DUZEYLER:
        try:
            veriler[slug] = (ad, json.loads((docs / 'puanlar' / f'{slug}.json').read_text(encoding='utf-8')))
        except (OSError, ValueError):
            continue
    veriler = {s: v for s, v in veriler.items() if v[1].get('donemler')}
    shutil.rmtree(docs / KLASOR, ignore_errors=True)
    if not veriler:
        return []
    yillar = [_donem_anahtar(d)[0] for _, v in veriler.values() for d in v['donemler']]
    ilk_yil, son_yil = min(yillar), max(yillar)
    adresler, ozetler = [], []
    kok_url = base + KLASOR + '/'
    for slug, (ad, veri) in veriler.items():
        grup = unvanlari_grupla(veri)
        if not grup:
            continue
        son_donem = max(veri['donemler'], key=_donem_anahtar)
        sluglar = benzersiz_sluglar([u for u, d in grup.items() if sum(len(r) for r in d.values()) >= MIN_SATIR])
        for unvan, s in sluglar.items():
            acik_k = acik_kadro_ilanlari(adaylar, slug, unvan)
            url, h = kadro_sayfasi(base, slug, ad, unvan, s, grup[unvan], ilk_yil, son_yil, acik_k)
            _yaz(docs, f'{slug}/{s}', h)
            if kadro_dizinlenir(grup[unvan]):
                adresler.append(url)
                _degisim_yaz(url, acik_k)
        sirali_d = sorted(veri['donemler'], key=_donem_anahtar)
        araliklar = {a: v for a, v in araliklari_grupla(veri['donemler'][son_donem]).items() if aralik_slug(a) not in sluglar.values()}
        onceki = (sirali_d[-2], araliklari_grupla(veri['donemler'][sirali_d[-2]])) if len(sirali_d) >= 2 else None
        for alt in sorted(araliklar):
            url, h = aralik_sayfasi(base, slug, ad, alt, son_donem, araliklar, sluglar, onceki)
            _yaz(docs, f'{slug}/{aralik_slug(alt)}', h)
            if len(araliklar[alt]) >= MIN_ARALIK_SATIR:
                adresler.append(url)
        bolum_adresleri = []
        bolum_n = _bolum_uret(docs, base, slug, ad, veri, bolum_adresleri)
        adresler.extend(bolum_adresleri)
        acik_d = acik_kadro_ilanlari(adaylar, slug)
        url, h = duzey_sayfasi(base, slug, ad, grup, sluglar, son_donem, ilk_yil, son_yil, acik_d, araliklar,
                               duzey_sorulari(ad, son_donem, araliklar), bolum_n)
        _degisim_yaz(url, acik_d)
        _yaz(docs, slug, h)
        adresler.insert(0, url)
        en_cok = sorted(sluglar, key=lambda u: (-sum(len(r) for r in grup[u].values()), _kucuk(u)))[:10]
        ozetler.append((slug, ad, len(grup), son_donem, [(baslik_hali(u), sluglar[u]) for u in en_cok]))
    if not ozetler:
        return []
    url, h = hub_sayfasi(base, ozetler, ilk_yil, son_yil)
    _yaz(docs, '', h)
    return [url] + adresler
