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


def _kirinti_json(base, parcalar):
    ogeler = [{'@type': 'ListItem', 'position': i, 'name': ad, 'item': url} for i, (ad, url) in enumerate(parcalar, 1)]
    j = json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': ogeler},
                   ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{j}</script>'


def _kes(s, n=160):
    return s if len(s) <= n else s[:n - 1].rstrip(' ,;.') + '…'


def _sayfa(base, yol, derinlik, baslik, aciklama, kirinti, icerik):
    """yol: KLASOR'e göre ('' = hub). derinlik: index.html'in docs'a göre klasör derinliği."""
    su = _su()
    kok = '../' * derinlik
    canonical = base + KLASOR + '/' + yol
    aciklama = _kes(aciklama)
    ek = (f'<meta property="og:url" content="{esc(canonical)}">' + _kirinti_json(base, kirinti))
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
    tr = ''.join('<tr>' + ''.join(f'<td>{h}</td>' for h in s) + '</tr>' for s in satirlar)
    return f'<div class="tablo-kap"><table class="kp-tablo"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def _hero(kirinti_html, baslik, giris):
    return (f'<section class="kp-hero"><div class="wrap">{kirinti_html}<span class="eyebrow">KPSS yerleştirme taban puanları</span>'
            f'<h1>{esc(baslik)}</h1><p>{esc(giris)}</p></div></section>')


# ------------------------------------------------------------------ sayfalar
def kadro_sayfasi(base, duzey_slug, duzey_ad, unvan, slug, donemler, ilk_yil, son_yil):
    """donemler: {dönem: [satır]}."""
    sirali = sorted(donemler, key=_donem_anahtar)
    son = sirali[-1]
    oz = _ozet(donemler[son])
    ad = baslik_hali(unvan)
    baslik = f'KPSS {ad} Taban Puanları ({duzey_ad}) — {ilk_yil}–{son_yil}'
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
                           [[esc(r.get('kurum')), esc(r.get('il')), esc(r.get('teskilat')), tam(r.get('kontenjan') or 0),
                             tam(r.get('yerlesen') or 0), _p(r.get('min'), 3), _p(r.get('max'), 3)] for r in rows]) + '</section>')
    icerik = (_hero(_crumbs(kok, kir), f'KPSS {ad} Taban Puanları ({duzey_ad})', ozet_p)
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Dönem dönem özet</h2></div>{ozet_tablo}</section>{detay}'
              f'<section class="bolum"><p><a href="../">← Tüm {esc(duzey_ad.lower())} kadroları</a> · <a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p></section></main>')
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/'),
               (ad, f'{base}{KLASOR}/{duzey_slug}/{slug}/')]
    return _sayfa(base, f'{duzey_slug}/{slug}/', 3, baslik, aciklama, kirinti, icerik)


def duzey_sayfasi(base, duzey_slug, duzey_ad, grup, sluglar, son_donem, ilk_yil, son_yil):
    """grup: {unvan: {dönem: [satır]}}; sluglar: bağlantılı unvanlar."""
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
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>{esc(duzey_ad)} kadroları <span class="sayi">{len(grup)}</span></h2></div>{tablo}'
              f'<p class="kp-note">Ayrıntı sayfası, en az {MIN_SATIR} kayıt bulunan unvanlar için vardır. Puanlar kadro bazında en küçük puanların özetidir.</p>'
              f'<p><a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p></section></main>')
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/'), (duzey_ad, f'{base}{KLASOR}/{duzey_slug}/')]
    return _sayfa(base, f'{duzey_slug}/', 2, baslik, aciklama, kirinti, icerik)


def hub_sayfasi(base, ozetler, ilk_yil, son_yil):
    """ozetler: [(duzey_slug, duzey_ad, kadro_unvan_sayisi, son_donem)]."""
    kok = '../'
    kartlar = ''.join(
        f'<li><a href="{s}/">KPSS {esc(ad)} taban puanları</a> — {tam(n)} kadro unvanı, son dönem {esc(donem_yaz(d))}</li>' for s, ad, n, d in ozetler)
    baslik = f'KPSS Taban Puanları ({ilk_yil}–{son_yil})'
    aciklama = (f'KPSS lisans, önlisans ve ortaöğretim taban puanları ({ilk_yil}–{son_yil}): kadro kadro en düşük ve en yüksek yerleşme puanları, '
                f'dönem dönem karşılaştırma.')
    giris = (f'KPSS merkezi yerleştirmede kadrolara yerleşen adayların en küçük ve en büyük puanlarını {ilk_yil}–{son_yil} dönemleri için '
             f'kadro (unvan) bazında inceleyin. Tercih döneminde hangi puanın hangi kadroya yettiğini geçmiş yıllarla karşılaştırmak için kullanışlıdır.')
    icerik = (_hero(_crumbs(kok, [('KPSS Taban Puanları', None)]), baslik, giris)
              + f'<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Öğrenim düzeyine göre taban puanları</h2></div><ul>{kartlar}</ul>'
              f'<p><a href="{kok}puanlar/">Puanını gir, hangi kadrolara yettiğini gör: tercih robotu →</a></p></section></main>')
    kirinti = [('Ana sayfa', base), ('KPSS Taban Puanları', base + KLASOR + '/')]
    return _sayfa(base, '', 1, baslik, aciklama, kirinti, icerik)


def _yaz(docs, goreli, html_metin):
    p = docs / KLASOR / goreli / 'index.html'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_metin, encoding='utf-8')


def puan_sayfalarini_uret(docs, base):
    """docs/kpss-taban-puanlari/ altını baştan yazar; üretilen mutlak adresleri döndürür."""
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
            url, h = kadro_sayfasi(base, slug, ad, unvan, s, grup[unvan], ilk_yil, son_yil)
            _yaz(docs, f'{slug}/{s}', h)
            adresler.append(url)
        url, h = duzey_sayfasi(base, slug, ad, grup, sluglar, son_donem, ilk_yil, son_yil)
        _yaz(docs, slug, h)
        adresler.insert(0, url)
        ozetler.append((slug, ad, len(grup), son_donem))
    if not ozetler:
        return []
    url, h = hub_sayfasi(base, ozetler, ilk_yil, son_yil)
    _yaz(docs, '', h)
    return [url] + adresler
