"""Generate crawlable public detail pages from the existing verified registry."""
import html
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://enesfeched-maker.github.io/kamu-ilan-takip/'
TR = timezone(timedelta(hours=3))


def esc(value):
    return html.escape(str(value or ''), quote=True)


def detail_page(item):
    url = urlparse(item.get('link', ''))
    key = parse_qs(url.query).get('i', [''])[0]
    import uuid
    try:
        key = str(uuid.UUID(key))
    except ValueError:
        return None
    if url.scheme != 'https' or url.hostname != 'kariyerkapisi.gov.tr':
        return None
    canonical = BASE + 'ilan/' + key + '/'
    title = item.get('baslik', 'Kamu ilanı')
    deadline = item.get('son_zaman') or item.get('son_tarih')
    end = datetime.fromisoformat(deadline) if deadline else None
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=TR, hour=23, minute=59, second=59)
    status = 'Başvuru sona erdi' if end and end <= datetime.now(TR) else 'Son tarihi resmî ilandan doğrula'
    date = end.astimezone(TR).strftime('%d.%m.%Y · %H:%M TSİ' if item.get('son_zaman') else '%d.%m.%Y') if end else 'Belirtilmemiş'
    sections = ''
    for heading, value in [('Kadro ve kontenjan', item.get('kadro')), ('İlan özeti', item.get('ozet')), ('Başvuru notu', item.get('basvuru_notu'))]:
        if value:
            sections += f'<h3>{heading}</h3><p>{esc(value)}</p>'
    sections += '<h3>Başvuru koşullarından seçmeler</h3>'
    for s in item.get('sartlar', []):
        sections += f'<section class="condition"><h4>{esc(s.get("kadro"))}</h4><p>{esc(s.get("metin"))}</p></section>'
    sections += '<p class="muted">Seçilmiş alıntılardır. Tüm koşullar, kadrolar ve güncel tarihler için resmî ilanı incele.</p>'
    description = (item.get('kurum', '') + ' — ' + (item.get('kadro') or title))[:190]
    return key, f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Kamu İlan Takip</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="article"><link rel="stylesheet" href="../../portal.css?v=3"><link rel="icon" href="../../kamu-logo.png?v=1" type="image/png"></head><body><div class="topline"><div class="container">Kariyer Kapısı kaynaklı bağımsız ilan rehberi</div></div><header class="header"><div class="container header-inner"><a class="brand" href="../../"><img class="brand-logo" src="../../kamu-logo.png?v=1" alt="" width="48" height="48"><span>Kamu İlan<span class="brand-sub">TAKİP</span></span></a><a class="button secondary" href="../../">Tüm ilanlar →</a></div></header><main class="container" style="padding-block:36px"><p><a class="text-link" href="../../">← İlanları keşfet</a></p><div class="detail-header"><span class="eyebrow">{esc(item.get('ilan_turu','KAMU İLANI'))}</span><h1 style="font-size:clamp(1.7rem,3vw,2.5rem)">{esc(title)}</h1><p>{esc(item.get('kurum'))}</p></div><div class="detail-layout"><article class="detail-content"><p class="notice">Bilgiler kayıtlı kaynak özetini yansıtır. Güncel durum ve başvuru şartlarında resmî ilan esas alınır.</p>{sections}<p class="muted">Ayrıntı kontrolü: {esc(item.get('detay_guncelleme','Tarih belirtilmemiş'))}</p></article><aside class="detail-aside"><dl><dt>Durum</dt><dd>{status}</dd><dt>Görev yeri</dt><dd>{esc(item.get('yer') or 'Resmî ilandan kontrol et')}</dd><dt>Son başvuru</dt><dd>{date}</dd></dl><a class="button primary" href="{esc(item['link'])}" target="_blank" rel="noopener noreferrer">Resmî ilan ve başvuru ↗</a><a class="button secondary" href="../../#ilan/{key}">Kaydet, paylaş ve karşılaştır</a><a class="button secondary" href="https://t.me/kamuilantakip" target="_blank" rel="noopener">Telegram'dan takip et ↗</a></aside></div><section class="trust-strip" style="margin-top:40px"><strong>Başka fırsatlara da göz at.</strong><a class="button primary" href="../../">İlanları keşfet →</a></section></main><footer class="footer"><div class="container footer-bottom">Kamu İlan Takip resmî bir hizmet değildir. Başvurunu ilanda belirtilen resmî kanaldan tamamla.</div></footer></body></html>'''


def main():
    docs = ROOT / 'docs'
    data = json.loads((docs / 'ilanlar.json').read_text(encoding='utf-8'))
    urls = [BASE]
    count = 0
    for item in data.get('ilanlar', []):
        result = detail_page(item)
        if not result:
            continue
        key, content = result
        folder = docs / 'ilan' / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(content, encoding='utf-8')
        urls.append(BASE + 'ilan/' + key + '/')
        count += 1
    (docs / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+esc(u)+'</loc></url>' for u in urls)+'</urlset>\n', encoding='utf-8')
    print(f'{count} public detail pages and sitemap generated.')


if __name__ == '__main__':
    main()
