"""Akademik ilanlar için taranabilir statik sayfa: /akademik/ (Kasım 2026).
Akademik sekmesi üst menüden çıktı; Google'dan "akademik ilanlar", "araştırma görevlisi ilanı" gibi aramalarla gelenler
bu sayfayı bulur. Liste liste.json'daki 'akademik' kayıtlarından üretilir; her satır ana sayfadaki ilan penceresine bağlanır."""
import json
import re
from datetime import date

UNVANLAR = [('ogretim-uyesi', 'Öğretim üyesi', r'öğretim üye|profesör|doçent|doktor öğretim'),
            ('ogretim-gorevlisi', 'Öğretim görevlisi', r'öğretim görevli'),
            ('arastirma-gorevlisi', 'Araştırma görevlisi', r'araştırma görevli')]
STIL = ('<style>.ak-cipler{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px}.ak-cip{padding:7px 12px;border-radius:999px;background:var(--surface-2);'
        'font-size:13.5px;font-weight:600}.ak-liste{list-style:none;margin:0;padding:0;display:grid;gap:8px}.ak-liste li{display:grid;'
        'grid-template-columns:minmax(0,1fr) auto;gap:4px 14px;align-items:center;padding:14px 16px;border:1px solid var(--line);'
        'border-radius:12px;background:var(--surface)}.ak-liste a{font-weight:650;color:var(--ink)}.ak-liste small{color:var(--muted);'
        'font-size:13px}.ak-liste .ak-tarih{text-align:right;font-size:13px;font-weight:600;color:var(--ink-2);white-space:nowrap}'
        '.ak-tarih.yakin{color:var(--alert)}@media(max-width:640px){.ak-liste li{grid-template-columns:1fr}.ak-liste .ak-tarih{text-align:left}}</style>')


def unvan_turu(kayit):
    metin = ' '.join([kayit.get('manset') or ''] + list(kayit.get('unvanlar') or []) + list(kayit.get('meslek') or [])).lower()
    return [k for k, _, desen in UNVANLAR if re.search(desen, metin)]


def _tarih(t):
    try:
        d = date.fromisoformat(t)
    except (TypeError, ValueError):
        return ''
    ay = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'][d.month - 1]
    return f'{d.day} {ay} {d.year}'


def sayfa(kayitlar, base, simdi):
    import site_uret as su
    kok = '../'
    canonical = f'{base}akademik/'
    bugun = simdi.date()
    acik = [k for k in kayitlar if not k.get('son_tarih') or k['son_tarih'] >= bugun.isoformat()]
    say = {k: sum(1 for x in acik if k in unvan_turu(x)) for k, _, _ in UNVANLAR}
    yil = bugun.year
    baslik = f'Akademik İlanlar {yil}: Öğretim Üyesi, Öğretim Görevlisi ve Araştırma Görevlisi Alımları | KPSS Tercihi'
    aciklama = (f'Üniversitelerin güncel akademik personel ilanları: {len(acik)} açık ilan. Öğretim üyesi, öğretim görevlisi ve '
                'araştırma görevlisi alımları son başvuru tarihine göre sıralı, her gün güncellenir.')
    satirlar = []
    for k in acik[:300]:
        kalan = None
        try:
            kalan = (date.fromisoformat(k.get('son_tarih') or '') - bugun).days
        except ValueError:
            pass
        tarih = _tarih(k.get('son_tarih')) or 'Tarih ilanda'
        etiket = f'Son başvuru: {tarih}' + (f' · {kalan} gün kaldı' if kalan is not None and kalan >= 0 else '')
        unvan = ', '.join(ad for kk, ad, _ in UNVANLAR if kk in unvan_turu(k))
        alt = ' · '.join(x for x in (k.get('il') or '', unvan, f"{k['toplam']} kadro" if k.get('toplam') else '') if x)
        satirlar.append(f'<li><div><a href="{kok}#ilan/{su.esc(k["key"])}">{su.esc(k.get("kurum") or k.get("manset"))}</a>'
                        f'<br><small>{su.esc(k.get("manset") or "")}{" · " + su.esc(alt) if alt else ""}</small></div>'
                        f'<span class="ak-tarih{" yakin" if kalan is not None and 0 <= kalan <= 3 else ""}">{su.esc(etiket)}</span></li>')
    liste = f'<ul class="ak-liste">{"".join(satirlar)}</ul>' if satirlar else '<p class="muted">Şu an açık akademik ilan yok. Yeni ilanlar her gün eklenir.</p>'
    cipler = ''.join(f'<span class="ak-cip">{ad}: {say[k]}</span>' for k, ad, _ in UNVANLAR)
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': f'Akademik ilanlar {yil}', 'description': aciklama, 'url': canonical, 'inLanguage': 'tr-TR',
         'dateModified': bugun.isoformat(), 'isPartOf': {'@type': 'WebSite', 'name': 'KPSS Tercihi', 'url': base}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Ana sayfa', 'item': base},
            {'@type': 'ListItem', 'position': 2, 'name': 'Akademik ilanlar', 'item': canonical}]},
        {'@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': 'Akademik ilanlara nereden başvurulur?', 'acceptedAnswer': {'@type': 'Answer', 'text':
             'Başvurular ilanı veren üniversitenin duyurduğu yöntemle (çoğunlukla üniversitenin personel daire başkanlığı sayfası veya e-Devlet) yapılır. Her ilanın resmî metnindeki başvuru adresini ve belgeleri esas al.'}},
            {'@type': 'Question', 'name': 'Araştırma görevlisi ilanında ALES ve YDS şartı var mı?', 'acceptedAnswer': {'@type': 'Answer', 'text':
             'Öğretim görevlisi ve araştırma görevlisi kadrolarında genellikle ALES puanı ve kadroya göre yabancı dil puanı istenir. Puan alt sınırları ve muafiyetler ilan metninde ayrıca belirtilir.'}}]}]}
    html = (su.sayfa_basi(baslik, aciklama, su.esc(canonical), kok,
                          ek_head=f'<meta property="og:url" content="{su.esc(canonical)}">{STIL}<script type="application/ld+json">'
                                  + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>')
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok)}'
            + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a>'
              '<span aria-hidden="true">/</span><span>Akademik ilanlar</span></nav><span class="eyebrow">Üniversite ilanları</span>'
            + f'<h1>Akademik ilanlar {yil}</h1><p>Üniversitelerin öğretim üyesi, öğretim görevlisi ve araştırma görevlisi ilanları. '
              f'Şu an <b>{len(acik)}</b> açık ilan var; liste son başvuru tarihine göre sıralı ve her gün güncellenir.</p></div></section>'
            + f'<main id="icerik" class="wrap kp-main"><div class="ak-cipler">{cipler}</div>{liste}'
              '<section class="bolum"><h2>Akademik ilanlara başvururken</h2><p>Akademik kadrolarda başvuru şartları (ALES, yabancı dil puanı, '
              'lisansüstü alan, ön değerlendirme ve giriş sınavı takvimi) üniversiteden üniversiteye değişir. Başvurmadan önce ilanın resmî '
              'metnini ve istenen belgeleri mutlaka kontrol et.</p><p>Kamu kurumlarının memur, sözleşmeli personel ve işçi alımları için '
              '<a href="../#ilanlar">güncel kamu ilanlarına</a>, adliye kâtipliği hazırlığı için <a href="../katiplik/">katiplik klavye sınavı '
              'simülasyonuna</a> bakabilirsin.</p></section></main>'
            + f'{su.alt_html(kok)}</body></html>')
    return canonical, html


def yaz(docs, base, kayitlar, simdi):
    """docs/akademik/index.html yazar; site haritası için adresi döner."""
    from pathlib import Path
    url, html = sayfa(kayitlar or [], base, simdi)
    hedef = Path(docs) / 'akademik'
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / 'index.html').write_text(html, encoding='utf-8')
    return [url]
