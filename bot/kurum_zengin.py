"""Kurum sayfalarına siteye özgü içerik (19 Ekim 2026, AdSense 'düşük değerli içerik' reddi sonrası):
  - KPSS merkezi yerleştirme geçmişi: ÖSYM sayısal bilgilerinde bu kurumun kadroları ve en küçük puanları (docs/puanlar),
  - takip özeti: sitenin bu kurumdan derlediği ilan sayısı, ilk görülme ve en sık kadrolar.
Ne açık ilanı ne yerleştirme geçmişi olan kurum sayfası arama dizinine girmez (dizinlenir=False)."""
import json
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path

DUZEY_ADI = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
EN_COK_DONEM = 3
EN_COK_SATIR = 15
AYLAR = 'Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık'.split()


@lru_cache(maxsize=4)
def _indeks(docs):
    """{kurum_kanonik: [(düzey, dönem, satır)]}"""
    import kurum_sayfasi as ks
    sonuc = {}
    for duzey in DUZEY_ADI:
        try:
            veri = json.loads((Path(docs) / 'puanlar' / f'{duzey}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for donem, satirlar in (veri.get('donemler') or {}).items():
            for r in satirlar:
                if r.get('kurum') and isinstance(r.get('min'), (int, float)):
                    sonuc.setdefault(ks.kurum_kanonik(r['kurum']), []).append((duzey, donem, r))
    return sonuc


def yerlestirmeler(kan, docs):
    """Kurum grubunun (kurum_gruplari anahtarı; belediyede 'ad|il') yerleştirme satırları."""
    import kurum_sayfasi as ks
    ad, _, il = kan.partition('|')
    satirlar = _indeks(str(docs)).get(ad, [])
    if il:
        satirlar = [s for s in satirlar if ks.kurum_anahtari(s[2].get('il') or '') == il]
    return satirlar


def yerlestirme_html(kan, docs):
    import puan_sayfalari as ps
    satirlar = yerlestirmeler(kan, docs)
    if not satirlar:
        return ''
    donemler = sorted({d for _, d, _ in satirlar}, key=ps._donem_anahtar)
    son = donemler[-EN_COK_DONEM:]
    secili = sorted((s for s in satirlar if s[1] in son), key=lambda s: (ps._donem_anahtar(s[1]), -s[2]['min']), reverse=True)
    mins = [s[2]['min'] for s in satirlar]
    kontenjan = sum(s[2].get('kontenjan') or 0 for s in satirlar)
    ilk, sonuncu = ps.donem_yaz(donemler[0]), ps.donem_yaz(donemler[-1])
    ozet = (f'ÖSYM\'nin KPSS merkezi yerleştirme sonuçlarında bu kurumun {ilk}–{sonuncu} arasında {ps.tam(len(satirlar))} kadrosu '
            f'(toplam {ps.tam(kontenjan)} kontenjan) yer aldı. Yerleşenlerin en küçük puanları '
            f'{ps.sayi(min(mins))} ile {ps.sayi(max(mins))} arasında.')
    tablo = ps._tablo(['Dönem', 'Düzey', 'Kadro', 'İl', 'Kontenjan', 'En düşük puan'],
                      [[ps.esc(ps.donem_yaz(d)), DUZEY_ADI[du], ps.esc(ps._duzgun(r.get('unvan') or '')),
                        ps.esc(ps._duzgun(r.get('il'))), ps.tam(r.get('kontenjan') or 0), ps.sayi(r['min'])]
                       for du, d, r in secili[:EN_COK_SATIR]])
    devam = f'<p class="kp-note">Son {len(son)} dönemden {min(len(secili), EN_COK_SATIR)} kadro gösteriliyor.</p>' if len(secili) > EN_COK_SATIR else ''
    return (f'<section class="bolum"><div class="bolum-bas"><h2>KPSS merkezi yerleştirme geçmişi</h2></div><p>{ps.esc(ozet)}</p>'
            f'{tablo}{devam}<p><a class="yazi-link" href="../../kpss-taban-puanlari/">Tüm kadroların taban puanları →</a></p></section>')


def _tarih(iso):
    try:
        g = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ''
    return f'{g.day} {AYLAR[g.month - 1]} {g.year}'


def takip_ozeti_html(ad, liste):
    """Sitenin bu kurumdan derlediği ilanlara dair kısa, tamamen veriye dayalı paragraf."""
    import kurum_sayfasi as ks
    from site_uret import esc
    ilanlar = [i for i in liste if not i.get('duyuru_turu')]
    if not ilanlar:
        return ''
    ilk = min((i.get('ilk_gorulme') or '9999') for i in ilanlar)
    unvanlar = Counter(ad_ for i in ilanlar for _, ad_ in ks.kadrolar(i))
    kadro = sum(ks.kart_alanlari(i).get('toplam') or 0 for i in ilanlar)
    cumle = f'KPSS Tercihi {esc(ad)} için {len(ilanlar)} personel alım ilanı derledi'
    if _tarih(ilk):
        cumle += f' (ilki {_tarih(ilk)})'
    cumle += '.'
    if kadro:
        cumle += f' Bu ilanlarda bilinen toplam kadro sayısı {kadro}.'
    sik = [u for u, _ in unvanlar.most_common(4)]
    if sik:
        cumle += f' En sık alım yapılan kadrolar: {esc(", ".join(sik))}.'
    duyuru = sum(1 for i in liste if i.get('duyuru_turu'))
    if duyuru:
        cumle += f' Kurumun {duyuru} düzeltme/iptal duyurusu da arşivde.'
    return f'<section class="bolum"><div class="bolum-bas"><h2>Kurum hakkında kısa bilgi</h2></div><p>{cumle}</p></section>'
