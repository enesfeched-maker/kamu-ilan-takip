"""İlan sayfasına "Bu kadroya geçmişte kaç puanla atanıldı?" bölümü (19 Ekim 2026).

Kaynak: docs/puanlar/<düzey>.json (ÖSYM KPSS merkezi yerleştirme sayısal bilgileri, en küçük/en büyük puan). İlandaki kadro
unvanı yerleştirme verisindeki unvanla birebir eşleşirse son üç dönemin özeti ve varsa AYNI KURUMUN geçmiş yerleştirmeleri
gösterilir. Resmî ilanda olmayan, siteye özgü bilgi; ama ilanın kendi puan şartı değildir — sayfada açıkça yazılır."""
import json
import re
import statistics
from functools import lru_cache
from pathlib import Path

DUZEY_ADI = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
EN_COK_UNVAN = 3
EN_COK_DONEM = 3
EN_COK_KURUM_SATIRI = 6
BELIRSIZ_UNVANLAR = {'uzman', 'uzman yardımcısı', 'personel', 'sözleşmeli personel', 'işçi'}   # kurumdan kuruma anlamı değişir


def _norm(s):
    from siniflandir import kucuk
    s = re.sub(r'\s*\(.*?\)', '', str(s or ''))
    return ' '.join(kucuk(s).split())


@lru_cache(maxsize=4)
def _veri(docs):
    """{düzey: {'unvanlar': {norm unvan: {dönem: [satır]}}, 'ad': {norm: özgün}, 'slug': {özgün: slug}}}"""
    import puan_sayfalari as ps
    sonuc = {}
    for duzey in DUZEY_ADI:
        try:
            veri = json.loads((Path(docs) / 'puanlar' / f'{duzey}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        grup = ps.unvanlari_grupla(veri)
        sluglar = ps.benzersiz_sluglar([u for u, d in grup.items() if sum(len(r) for r in d.values()) >= ps.MIN_SATIR])
        sonuc[duzey] = {'unvanlar': {_norm(u): d for u, d in grup.items()}, 'ad': {_norm(u): u for u in grup}, 'slug': sluglar}
    return sonuc


def eslesmeler(item, docs):
    """[(düzey, özgün unvan, {dönem: [satır]}, slug|None)] — ilanın kadro adları ve öğrenim düzeyleriyle."""
    import kurum_sayfasi as ks
    veri = _veri(str(docs))
    adlar = list(dict.fromkeys(ad for _, ad in ks.kadrolar(item)))
    duzeyler = [d for d in (item.get('ogrenim') or []) if d in veri] or list(veri)
    sonuc, gorulen = [], set()
    for ad in adlar:
        n = _norm(ad)
        if n in BELIRSIZ_UNVANLAR:
            continue
        for d in duzeyler:
            tablo = veri[d]
            if n in tablo['unvanlar'] and (d, n) not in gorulen:
                gorulen.add((d, n))
                ozgun = tablo['ad'][n]
                sonuc.append((d, ozgun, tablo['unvanlar'][n], tablo['slug'].get(ozgun)))
                break
        if len(sonuc) >= EN_COK_UNVAN:
            break
    return sonuc


def _p(x):
    return f'{x:.2f}'.replace('.', ',') if isinstance(x, (int, float)) else '—'


def bolum_html(item, docs, kok='../../'):
    """Eşleşme yoksa ''. Tablolar puan sayfalarıyla aynı sınıfları (kp-tablo) kullanır."""
    import puan_sayfalari as ps
    from kurum_gorseli import kurum_anahtari
    esc = ps.esc
    eslesen = eslesmeler(item, docs)
    if not eslesen:
        return ''
    kurum = kurum_anahtari(item.get('kurum') or '')
    parcalar = []
    for duzey, unvan, donemler, slug in eslesen:
        sirali = sorted(donemler, key=ps._donem_anahtar)[-EN_COK_DONEM:]
        satirlar = []
        for d in reversed(sirali):
            mins = [r['min'] for r in donemler[d] if isinstance(r.get('min'), (int, float))]
            satirlar.append([esc(ps.donem_yaz(d)), ps.tam(len(donemler[d])),
                             _p(min(mins) if mins else None), _p(statistics.median(mins) if mins else None),
                             _p(max(mins) if mins else None)])
        ad = ps._duzgun(unvan)
        baslik = f'{ad} ({DUZEY_ADI[duzey]})'
        bag = (f' <a class="yazi-link" href="{kok}{ps.KLASOR}/{duzey}/{esc(slug)}/">Tüm dönemler ve kadro kadro döküm →</a>'
               if slug else '')
        kurum_satir = []
        for d in sorted(donemler, key=ps._donem_anahtar, reverse=True):
            for r in donemler[d]:
                if kurum and kurum_anahtari(r.get('kurum') or '') == kurum and isinstance(r.get('min'), (int, float)):
                    kurum_satir.append([esc(ps.donem_yaz(d)), esc(ps._duzgun(r.get('il'))), ps.tam(r.get('kontenjan') or 0), _p(r['min'])])
        kurum_html = ''
        if kurum_satir:
            kurum_html = (f'<p class="muted" style="margin-top:12px">Bu kurumun merkezi yerleştirmedeki {esc(ad)} kadroları:</p>'
                          + ps._tablo(['Dönem', 'İl', 'Kontenjan', 'En düşük puan'], kurum_satir[:EN_COK_KURUM_SATIRI]))
        parcalar.append(f'<h3>{esc(baslik)}</h3>'
                        + ps._tablo(['Dönem', 'Kadro sayısı', 'En düşük puan', 'Ortanca', 'En yüksek taban'], satirlar)
                        + kurum_html + (f'<p>{bag}</p>' if bag else ''))
    return ('<section class="taban-gecmis"><h2>Bu kadroya geçmişte kaç puanla atanıldı?</h2>'
            '<p class="muted">KPSS merkezi yerleştirmelerinde (ÖSYM) aynı unvanlı kadrolara yerleşenlerin en küçük puanları. '
            'Bu ilanın kendi puan şartı değildir; başvuru koşulları için yukarıdaki bilgileri ve resmî ilanı esas al.</p>'
            + ''.join(parcalar) + '</section>')
