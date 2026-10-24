"""Reviewed, source-linked practical guides; rendered on every site build."""
import json
from pathlib import Path

TARIH = '2026-10-24'


def icerikler():
    return json.loads(Path(__file__).with_name('uygulamali_rehberler.json').read_text(encoding='utf-8'))


def kartlar():
    import site_uret as su
    cards = ''.join(
        f'<a class="guide-card" href="{su.esc(r["slug"])}/"><span>UYGULAMALI REHBER</span>'
        f'<h3>{su.esc(r["title"])}</h3><p>{su.esc(r["description"])}</p><b>Rehberi incele →</b></a>'
        for r in icerikler())
    return ('<section class="guide-feature"><h2>Tercihini adım adım hazırla</h2>'
            '<p>Örnekler, karşılaştırmalar ve kendi durumuna uygulayabileceğin kontrol tabloları.</p>'
            f'<div class="guide-grid">{cards}</div></section><h2>Temel bilgiler ve başvuru rehberleri</h2>')


def yaz(docs, base):
    import site_uret as su
    urls = []
    for r in icerikler():
        url = base + 'rehber/' + r['slug'] + '/'
        schema = {'@context': 'https://schema.org', '@type': 'Article',
                  'headline': r['title'], 'description': r['description'], 'inLanguage': 'tr',
                  'datePublished': TARIH, 'dateModified': TARIH, 'mainEntityOfPage': url,
                  'author': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base},
                  'publisher': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}}
        extra = '<link rel="stylesheet" href="../../rehber.css?v=1"><script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace('</', '<\\/') + '</script>'
        head = su.sayfa_basi(r['title'] + ' | KPSS Tercihi', r['description'], su.esc(url), '../../', 'article', ek_head=extra)
        body = ('<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>'
                + su.ust_html('../../') + r['body'] + su.alt_html('../../') + '</body></html>')
        dest = Path(docs)/'rehber'/r['slug']/'index.html'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(head + body, encoding='utf-8')
        urls.append(url)
    return urls
