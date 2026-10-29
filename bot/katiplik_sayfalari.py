"""Katiplik bölümünün aramadan trafik toplayan statik sayfaları (Kasım 2026):
  /katiplik/sinav-metinleri/            2025 zabıt katibi uygulamalı sınavının 30 resmî metni (dizin)
  /katiplik/sinav-metinleri/metin-N/    her metin ayrı sayfa: metin, istatistik, "bu metinle sınava gir"
  /katiplik/degerlendirme-kriterleri/   hata türleri ve net hesaplama rehberi + hesaplayıcı
  /katiplik/klavye-sinavi-rehberi/      sınav nasıl yapılır, hazırlık planı, SSS
Metinler docs/katiplik/metin/zk2025.js'ten okunur (Adalet Bakanlığı PGM'nin sınavdan önce yayımladığı resmî metinler).
Etkileşimli araçlar (simülasyon, ders, antrenman, oyun) docs/katiplik/ altındaki elle yazılmış sayfalardadır."""
import json
import re
from pathlib import Path

KAYNAK_ZIP = 'https://pgm.adalet.gov.tr/Resimler/dokuman/UygulamaliSinavMetinleri.zip'
KAYNAK_DUYURU = 'https://karsiyaka.adalet.gov.tr/sozlesmeli-zabit-katibi-uygulamali-sinav-metinleri-ve-degerlendirme-kriterleri'
KRITER_ZABIT = 'https://pgm.adalet.gov.tr/Resimler/SayfaDokuman/5092025151355Değerlendirme%20Kriterleri.pdf'
KRITER_ICRA = 'https://iidb.adalet.gov.tr/Resimler/SayfaDokuman/20260714115700787İcra%20Kâtipliği%20Uygulama%20Sınavı%20Değerlendirme%20Kriterleri.pdf'
GUNCELLEME = '2026-11-01'
OG_GORSEL = 'assets/katiplik-og.png'
STIL = ('<style>.ks-cta{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 6px}.ks-metin{font:16px/1.75 ui-monospace,Consolas,"Courier New",monospace;'
        'background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:14px 0;color:var(--ink);word-spacing:.04em}'
        '.ks-kutular{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}.ks-kutular div{background:var(--surface);'
        'border:1px solid var(--line);border-radius:12px;padding:12px 14px}.ks-kutular b{display:block;font-size:22px;letter-spacing:-.02em}'
        '.ks-kutular span{color:var(--muted);font-size:13px}.ks-liste{list-style:none;padding:0;margin:0;display:grid;gap:8px}.ks-liste li{display:flex;'
        'justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;padding:12px 16px;border:1px solid var(--line);border-radius:12px;'
        'background:var(--surface)}.ks-liste small{display:block;color:var(--muted);font-size:13px}.ks-gez{display:flex;justify-content:space-between;'
        'gap:10px;flex-wrap:wrap;margin:18px 0}.ks-kelimeler{display:flex;flex-wrap:wrap;gap:6px}.ks-kelimeler code{padding:4px 8px;border-radius:8px;'
        'background:var(--surface-2);font-size:14px}.ks-tablo{width:100%;border-collapse:collapse;font-size:14.5px}.ks-tablo th,.ks-tablo td{text-align:left;'
        'padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}.ks-tablo th{color:var(--muted);font-size:12.5px}'
        '.ks-hesap{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;align-items:end}.ks-hesap label{display:flex;'
        'flex-direction:column;gap:6px;font-size:13px;font-weight:600}.ks-hesap input{height:44px;padding:0 12px;border:1px solid var(--line-2);'
        'border-radius:10px;background:var(--surface);color:var(--ink);font:inherit;font-size:16px}.ks-sonuc{margin-top:14px;padding:14px 16px;'
        'border-radius:12px;background:var(--surface-2);font-size:15px}.ks-sonuc b.iyi{color:#2E8540}.ks-sonuc b.kotu{color:var(--alert)}'
        ':root[data-theme=dark] .ks-sonuc b.iyi{color:var(--lime)}'
        # renk dili docs/katiplik/katiplik.css ile aynı (--k-* paleti)
        ':root{--k-lime:#7CB518;--k-mavi:#2F80ED;--k-mor:#7B5CE6;--k-tur:#F2711C;--k-pembe:#E8487F;--k-sari:#E0A100}'
        ':root[data-theme=dark]{--k-lime:#C8F169;--k-mavi:#6CB2FF;--k-mor:#A68CFF;--k-tur:#FF9A5C;--k-pembe:#FF7AAE;--k-sari:#FFD24D}'
        '.katip-sayfa .kp-hero{background:radial-gradient(700px 420px at 0% 0%,color-mix(in srgb,var(--k-lime) 26%,transparent),transparent 62%),'
        'radial-gradient(600px 420px at 100% 100%,color-mix(in srgb,var(--k-mavi) 20%,transparent),transparent 62%),'
        'radial-gradient(420px 300px at 70% 0%,color-mix(in srgb,var(--k-mor) 18%,transparent),transparent 62%)}'
        '.katip-sayfa .kp-hero .eyebrow{color:var(--k-mavi)}'
        '.ks-kutular div{border-top:4px solid var(--r);background:linear-gradient(170deg,color-mix(in srgb,var(--r) 12%,var(--surface)),var(--surface) 70%)}'
        '.ks-kutular div:nth-child(4n+1){--r:var(--k-lime)}.ks-kutular div:nth-child(4n+2){--r:var(--k-mavi)}'
        '.ks-kutular div:nth-child(4n+3){--r:var(--k-mor)}.ks-kutular div:nth-child(4n){--r:var(--k-tur)}'
        '.ks-liste{counter-reset:ks}.ks-liste li{counter-increment:ks;position:relative;padding-left:66px;border-left:4px solid var(--r)}'
        '.ks-liste li::before{content:counter(ks);position:absolute;left:14px;top:50%;margin-top:-18px;width:36px;height:36px;border-radius:11px;'
        'display:grid;place-items:center;font-weight:800;background:color-mix(in srgb,var(--r) 20%,transparent)}'
        '.ks-liste li:nth-child(5n+1){--r:var(--k-lime)}.ks-liste li:nth-child(5n+2){--r:var(--k-mavi)}.ks-liste li:nth-child(5n+3){--r:var(--k-mor)}'
        '.ks-liste li:nth-child(5n+4){--r:var(--k-tur)}.ks-liste li:nth-child(5n){--r:var(--k-pembe)}'
        '.ks-metin{border-left:5px solid var(--k-lime)}.ks-kelimeler code{background:color-mix(in srgb,var(--k-mor) 14%,var(--surface-2))}'
        '.ks-tablo tbody td:first-child b::before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px;background:var(--k-tur)}'
        '.ks-hesap{padding:18px;border-radius:16px;background:color-mix(in srgb,var(--k-mavi) 9%,var(--surface));border:1px solid color-mix(in srgb,var(--k-mavi) 30%,var(--line))}'
        '.ks-sonuc{border-left:5px solid var(--k-mavi)}</style>')


def metinleri_oku(docs):
    kaynak = (Path(docs) / 'katiplik' / 'metin' / 'zk2025.js').read_text(encoding='utf-8')
    return json.loads(re.search(r'KatipKutuphane\.yukle\("zk2025",(\[.*\])\);', kaynak, re.S).group(1))


def _ld(veri):
    return '<script type="application/ld+json">' + json.dumps(veri, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def _kirinti(base, ogeler):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': ad, 'item': url} for i, (ad, url) in enumerate(ogeler)]}


def _sss_ld(sorular):
    return {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': s, 'acceptedAnswer': {'@type': 'Answer', 'text': c}} for s, c in sorular]}


def _sss_html(esc, sorular):
    return ('<section class="bolum"><h2>Sık sorulanlar</h2>'
            + ''.join(f'<h3>{esc(s)}</h3><p>{esc(c)}</p>' for s, c in sorular) + '</section>')


def _kabuk(su, baslik, aciklama, canonical, kok, kirinti_html, eyebrow, h1, giris, govde, ld, og_tur='article'):
    ek = (f'<meta property="og:url" content="{su.esc(canonical)}"><meta property="og:image" content="{su.BASE}{OG_GORSEL}">'
          f'<meta name="twitter:card" content="summary_large_image">{STIL}{_ld(ld)}')
    return (su.sayfa_basi(baslik, aciklama, su.esc(canonical), kok, og_tur, ek_head=ek)
            + f'<body class="kurum-page katip-sayfa"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok, "katiplik")}'
            + f'<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum">{kirinti_html}</nav>'
            + f'<span class="eyebrow">{su.esc(eyebrow)}</span><h1>{su.esc(h1)}</h1><p>{giris}</p></div></section>'
            + f'<main id="icerik" class="wrap kp-main"><article>{govde}</article></main>{su.alt_html(kok)}</body></html>')


def _araclar(kok):
    return ('<section class="bolum"><h2>Ücretsiz çalışma araçları</h2><ul>'
            f'<li><a href="{kok}katiplik/">Katiplik klavye sınavı simülasyonu</a>: resmî kriterlerle 3 dakikalık deneme, sonuç tutanağı ve klavye analizi</li>'
            f'<li><a href="{kok}katiplik/sinav-metinleri/">2025 zabıt katipliği sınav metinleri</a>: 30 resmî metin</li>'
            f'<li><a href="{kok}katiplik/dersler/">On parmak klavye dersleri</a>: Türkçe Q ve F klavye, 16 ders</li>'
            f'<li><a href="{kok}katiplik/antrenman/">Klavye hız testi ve kelime antrenmanı</a>: zayıf tuşların, sık hukuk kelimeleri</li>'
            f'<li><a href="{kok}katiplik/oyunlar/">Klavye oyunları</a>: Dosya Yetiştir ve Hata Avı</li>'
            f'<li><a href="{kok}katiplik/degerlendirme-kriterleri/">Değerlendirme kriterleri ve net hesaplama</a></li>'
            f'<li><a href="{kok}katiplik/klavye-sinavi-rehberi/">Klavye sınavı nasıl yapılır? Hazırlık rehberi</a></li></ul></section>')


def _ozet(metin, n=10):
    k = metin.split()
    return ' '.join(k[:n]) + ('…' if len(k) > n else '')


def metin_sayfasi(su, base, metinler, i):
    kok = '../../../'
    no = i + 1
    metin = metinler[i][1]
    kelimeler = metin.split()
    canonical = f'{base}katiplik/sinav-metinleri/metin-{no}/'
    tr_orani = round(100 * sum(1 for w in kelimeler if re.search('[çğıöşü]', w)) / len(kelimeler))
    uzunlar = sorted(set(w for w in kelimeler if len(w) >= 11), key=lambda w: (-len(w), w))[:14]
    ort_yazi = f'{sum(len(w) for w in kelimeler) / len(kelimeler):.1f}'.replace('.', ',')
    baslik = f'Zabıt Katipliği 2025 Sınav Metni {no}: “{_ozet(metin, 5)}” | KPSS Tercihi'
    aciklama = (f'2025 zabıt katibi uygulamalı sınavının {no}. resmî metni ({len(kelimeler)} kelime). Metni oku, aynı metinle 3 dakikalık '
                'klavye sınavı simülasyonunu çöz; net kelimeni, hata türlerini ve başarı durumunu gör.')
    onceki = f'<a class="btn btn-ikinci" href="../metin-{no - 1}/">← Metin {no - 1}</a>' if no > 1 else '<span></span>'
    sonraki = f'<a class="btn btn-ikinci" href="../metin-{no + 1}/">Metin {no + 1} →</a>' if no < len(metinler) else '<span></span>'
    govde = (f'<div class="ks-cta"><a class="btn btn-ana btn-buyuk" href="{kok}katiplik/?k=zk2025&amp;m={i}&amp;mod=sinav&amp;basla=1" '
             f'data-a="katiplik" data-a-x="metin-sinav">Bu metinle sınava gir · 3:00</a>'
             f'<a class="btn btn-ikinci btn-buyuk" href="{kok}katiplik/?k=zk2025&amp;m={i}&amp;mod=antrenman" data-a="katiplik" data-a-x="metin-antrenman">Antrenman modunda yaz</a></div>'
             f'<div class="ks-kutular"><div><b>{len(kelimeler)}</b><span>kelime</span></div><div><b>{len(metin)}</b><span>karakter (boşluk dahil)</span></div>'
             f'<div><b>%{tr_orani}</b><span>Türkçe karakterli kelime</span></div><div><b>{ort_yazi}</b><span>ortalama kelime uzunluğu</span></div></div>'
             f'<section class="bolum"><h2>Metin {no}</h2><p class="muted">Resmî metin olduğu gibi: tamamı küçük harf, noktalama ve paragraf yok. '
             f'Sınavda 3 dakikada metnin bu kısmından en az 90 net kelime yazman beklenir (ilandaki barajı kontrol et).</p>'
             f'<div class="ks-metin" lang="tr">{su.esc(metin)}</div></section>'
             + (f'<section class="bolum"><h2>Bu metnin zor kelimeleri</h2><p>Uzun ve ekli kelimeler hem hızı düşürür hem de en çok bölme, eksik vuruş ve '
                f'harf yer değiştirme hatası bu kelimelerde yapılır. Sınavdan önce bunları birkaç kez ritimle yaz.</p>'
                f'<div class="ks-kelimeler">{"".join(f"<code>{su.esc(w)}</code>" for w in uzunlar)}</div></section>' if uzunlar else '')
             + '<section class="bolum"><h2>Bu metinle nasıl çalışmalısın?</h2><ul>'
               '<li>Önce metni bir kez sesli oku; anlamını bilmek yazarken takılmayı azaltır.</li>'
               '<li>Antrenman modunda “metin takibi” açıkken bir kez yaz, ardından resmî koşullarda (3 dakika, takip kapalı) sınava gir.</li>'
               '<li>Sonuç tutanağındaki hata türlerine bak: aynı türü tekrar ediyorsan (ör. eksik vuruş) hızını biraz düşür.</li>'
               '<li>Hatalı yazdığın kelimeler “hata defterine” eklenir; 1 dakikalık tekrarla bunları kalıcı olarak düzelt.</li></ul></section>'
             + f'<nav class="ks-gez" aria-label="Metinler arasında">{onceki}<a class="btn btn-ikinci" href="../">Tüm metinler</a>{sonraki}</nav>'
             + f'<p class="kp-note">Kaynak: Adalet Bakanlığı Personel Genel Müdürlüğü, 2025 Yılı Zabıt Katibi Uygulamalı Sınav Metinleri '
               f'(<a href="{KAYNAK_ZIP}" rel="noopener" target="_blank">resmî arşiv</a>, <a href="{KAYNAK_DUYURU}" rel="noopener" target="_blank">duyuru</a>). '
               'Metinler yönetmelik gereği sınavdan önce adaylara yayımlanmıştır. KPSS Tercihi resmî bir kurum değildir.</p>'
             + _araclar(kok))
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Article', 'headline': f'Zabıt Katipliği 2025 Sınav Metni {no}', 'description': aciklama, 'inLanguage': 'tr-TR',
         'mainEntityOfPage': canonical, 'datePublished': GUNCELLEME, 'dateModified': GUNCELLEME, 'wordCount': len(kelimeler),
         'author': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}, 'publisher': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base},
         'isBasedOn': KAYNAK_ZIP},
        _kirinti(base, [('Ana sayfa', base), ('Katiplik', f'{base}katiplik/'), ('Sınav metinleri', f'{base}katiplik/sinav-metinleri/'), (f'Metin {no}', canonical)])]}
    kir = (f'<a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}katiplik/">Katiplik</a>'
           f'<span aria-hidden="true">/</span><a href="../">Sınav metinleri</a>')
    return canonical, _kabuk(su, baslik, aciklama, canonical, kok, kir, 'Zabıt katipliği 2025 · resmî metin', f'2025 sınav metni {no}',
                             f'Bakanlığın 2025 zabıt katibi uygulamalı sınavı için yayımladığı {no}. metin. Oku, sonra aynı metinle 3 dakikalık simülasyonu çöz.',
                             govde, ld)


def dizin_sayfasi(su, base, metinler):
    kok = '../../'
    canonical = f'{base}katiplik/sinav-metinleri/'
    baslik = 'Zabıt Katipliği Sınav Metinleri 2025: 30 Resmî Uygulamalı Sınav Metni | KPSS Tercihi'
    aciklama = ('Adalet Bakanlığının 2025 zabıt katibi uygulamalı (klavye) sınavı için yayımladığı 30 resmî metin. Her metni oku, '
                'aynı metinle 3 dakikalık sınav simülasyonunu çöz ve net kelimeni gör.')
    satirlar = ''.join(
        f'<li><div><a href="metin-{i + 1}/"><b>Metin {i + 1}</b></a><small>{su.esc(_ozet(m[1], 12))} · {len(m[1].split())} kelime</small></div>'
        f'<a class="btn btn-ikinci" href="{kok}katiplik/?k=zk2025&amp;m={i}&amp;mod=sinav&amp;basla=1" data-a="katiplik" data-a-x="dizin-sinav">Sınava gir</a></li>'
        for i, m in enumerate(metinler))
    sorular = [
        ('Zabıt katipliği sınav metinleri önceden yayımlanıyor mu?',
         'Evet. Adalet Bakanlığı uygulamalı sınavda kullanılacak metinleri sınavdan önce internet sitesinde yayımlar; sınavda bu metinlerden biri seçilir. '
         '2025 sınavı için yayımlanan 30 metnin tamamı bu sayfada.'),
        ('Metinler sınavda nasıl görünür?',
         'Metinler tamamen küçük harfle, noktalama işareti ve paragraf olmadan verilir. Metne olmayan bir noktalama, büyük harf veya rakam eklemek hata sayılır.'),
        ('Bu metinlerle nasıl çalışmalıyım?',
         'Her metni önce okuyup ardından simülasyonda 3 dakika yaz. Sonuç tutanağındaki hata türlerini incele ve hatalı kelimelerini 1 dakikalık tekrarla çalış. '
         'Günde 2–3 deneme, birkaç haftada belirgin artış sağlar.'),
    ]
    govde = (f'<div class="ks-cta"><a class="btn btn-ana btn-buyuk" href="{kok}katiplik/?k=zk2025&amp;mod=sinav&amp;basla=1" data-a="katiplik" data-a-x="dizin-rastgele">'
             'Rastgele metinle sınava gir · 3:00</a><a class="btn btn-ikinci btn-buyuk" href="../degerlendirme-kriterleri/">Değerlendirme kriterleri</a></div>'
             f'<section class="bolum"><h2>30 resmî metin</h2><ul class="ks-liste">{satirlar}</ul></section>'
             + _sss_html(su.esc, sorular)
             + f'<p class="kp-note">Kaynak: Adalet Bakanlığı Personel Genel Müdürlüğü (<a href="{KAYNAK_ZIP}" rel="noopener" target="_blank">resmî arşiv</a>, '
               f'<a href="{KAYNAK_DUYURU}" rel="noopener" target="_blank">duyuru</a>). Daha eski yılların ve icra/CTE katipliğinin çalışma metinleri için '
               f'simülasyondaki mevzuat ve özgün metin kütüphanelerini kullanabilirsin.</p>' + _araclar(kok))
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': 'Zabıt katipliği 2025 sınav metinleri', 'description': aciklama, 'url': canonical, 'inLanguage': 'tr-TR',
         'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(metinler), 'itemListElement': [
             {'@type': 'ListItem', 'position': i + 1, 'url': f'{canonical}metin-{i + 1}/', 'name': f'Metin {i + 1}'} for i in range(len(metinler))]}},
        _kirinti(base, [('Ana sayfa', base), ('Katiplik', f'{base}katiplik/'), ('Sınav metinleri', canonical)]),
        _sss_ld(sorular)]}
    kir = f'<a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}katiplik/">Katiplik</a>'
    return canonical, _kabuk(su, baslik, aciklama, canonical, kok, kir, 'Zabıt katipliği · resmî metinler', 'Zabıt katipliği 2025 sınav metinleri',
                             'Adalet Bakanlığının 2025 zabıt katibi uygulamalı sınavı için sınavdan önce yayımladığı <b>30 resmî klavye metni</b>. '
                             'Her metni oku, aynı metinle 3 dakikalık simülasyonu çöz.', govde, ld, 'website')


HATA_TURLERI = [
    ('Fazla vuruş', 'Bir harf gereğinden fazla yazılır.', 'adalet → adalett, aadalet', '1 hata'),
    ('Eksik vuruş', 'Kelimedeki bir harf yazılmaz.', 'adalet → adale, adaet', '1 hata'),
    ('Harf yer değiştirme', 'Yan yana iki harfin yeri değişir.', 'adalet → adalte', '1 hata'),
    ('Karakter hatası', 'Harf yerine nokta, virgül, rakam gibi başka bir karakter yazılır.', 'adalet → .dalet', '1 hata'),
    ('Kelime bölme', 'Tek kelime araya boşluk girerek parçalara ayrılır.', 'ad al et (doğru yazılmış) · ada al et (yanlış)', 'Harfler doğruysa 1 hata; değilse her parça 1 hata'),
    ('Kelime birleştirme', 'İki ya da daha çok kelime boşluksuz bitişik yazılır.', 'adaletbakanlığı', '1 hata'),
    ('Fazla boşluk', 'Kelimeler arasına iki veya daha çok boşluk bırakılır.', 'adalet␣␣bakanlığı', '1 hata (net kelimeden düşülür)'),
    ('Karışık hata', 'Yukarıdakilerin dışındaki hatalar; metne noktalama, rakam veya ek ibare eklemek de bu türdendir.', 'adalet, · ada2let · adlemt', '1 hata'),
]


def kriter_sayfasi(su, base):
    kok = '../../'
    canonical = f'{base}katiplik/degerlendirme-kriterleri/'
    baslik = 'Klavye Sınavı Değerlendirme Kriterleri ve Net Hesaplama (Zabıt, İcra Katipliği) | KPSS Tercihi'
    aciklama = ('Zabıt ve icra katipliği klavye uygulama sınavında net kelime nasıl hesaplanır? Fazla/eksik vuruş, kelime bölme, birleştirme, '
                'fazla boşluk gibi hata türleri, 22 atlama ve %25 hata oranı kuralı, örnekler ve net hesaplayıcı.')
    tablo = ''.join(f'<tr><td><b>{su.esc(a)}</b></td><td>{su.esc(n)}</td><td><code>{su.esc(o)}</code></td><td>{su.esc(s)}</td></tr>' for a, n, o, s in HATA_TURLERI)
    sorular = [
        ('Klavye sınavında net kelime nasıl hesaplanır?',
         'Net kelime, toplam yazılan kelime sayısından hatalı kelime sayısı çıkarılarak bulunur. Fazla boşluk hataları da hatalı kelime sayılır. '
         'Örneğin 103 kelime yazıp 13 hata yapan aday 90 net yapar.'),
        ('Atlanan kelime hata sayılır mı?',
         'Hayır, atlanan kelime hata sayılmaz. Ancak ayrı ayrı veya peş peşe toplam 22 ve üzeri kelime atlanırsa yazılan kelime sayısına bakılmaksızın sınav başarısız sayılır.'),
        ('Süre biterken yarım kalan kelime hata mı?',
         'Hayır. Süre dolduğunda tamamlanamayan son kelime hata olarak değerlendirilmez.'),
        ('Hata oranı nedir, sınırı kaçtır?',
         'Hata oranı, hatalı kelime sayısının toplam yazılan kelime sayısına oranıdır. Bu oran yüzde 25’i aşarsa metin anlam bütünlüğü taşımıyor kabul edilir ve aday başarısız sayılır.'),
        ('Kelimeyi bölersem kaç hata sayılır?',
         'Bölünen kelimenin harfleri doğruysa tek hata sayılır. Harfleri de yanlışsa her parça ayrı hata olur; “ada al et” yazımı 3 hata sayılır.'),
    ]
    hesap = ('<section class="bolum" id="hesapla"><h2>Net hesaplayıcı</h2><p>Sınav tutanağındaki ya da kendi saydığın değerleri gir; net kelimen ve sonucun anında hesaplanır.</p>'
             '<div class="ks-hesap"><label>Toplam yazılan kelime<input id="h-top" type="number" min="0" value="103" inputmode="numeric"></label>'
             '<label>Hatalı kelime<input id="h-hat" type="number" min="0" value="13" inputmode="numeric"></label>'
             '<label>Atlanan kelime<input id="h-atl" type="number" min="0" value="1" inputmode="numeric"></label>'
             '<label>Baraj (net)<input id="h-bar" type="number" min="1" value="90" inputmode="numeric"></label></div>'
             '<div class="ks-sonuc" id="h-sonuc" aria-live="polite"></div>'
             '<script>(function(){var g=function(i){return Math.max(0,Number(document.getElementById(i).value)||0)};function h(){var t=g("h-top"),x=Math.min(g("h-hat"),t),a=g("h-atl"),b=g("h-bar")||90,'
             'n=t-x,o=t?x/t*100:0,r=[];if(n<b)r.push("net kelime barajın ("+b+") altında");if(a>=22)r.push("toplam atlama 22 veya üzeri");if(o>25)r.push("hata oranı %25\\u2019i aşıyor");'
             'var ok=!r.length&&t>0;document.getElementById("h-sonuc").innerHTML="Net kelime: <b>"+n+"</b> · Hata oranı: <b>%"+o.toFixed(2).replace(".",",")+"</b> · Sonuç: <b class=\\""+(ok?"iyi":"kotu")+"\\">"+(ok?"BAŞARILI":"BAŞARISIZ")+"</b>"+(r.length?"<br><small>Neden: "+r.join(", ")+"</small>":"")}'
             '["h-top","h-hat","h-atl","h-bar"].forEach(function(i){document.getElementById(i).addEventListener("input",h)});h()})()</script></section>')
    govde = ('<div class="ks-kutular"><div><b>3 dakika</b><span>uygulamalı sınav süresi</span></div><div><b>90 net</b><span>ilanlarda aranan en az net kelime</span></div>'
             '<div><b>22 kelime</b><span>toplam atlama sınırı</span></div><div><b>%25</b><span>hata oranı sınırı</span></div></div>'
             '<section class="bolum"><h2>Net kelime nasıl hesaplanır?</h2><p><b>Net kelime = toplam yazılan kelime − hatalı kelime.</b> Doğru yazılan kelimeler sayılır; '
             'her hata türü (aşağıdaki tablo) bir hatalı kelime olarak düşülür. Fazla boşluk da hatalı kelime sayılır.</p>'
             '<p>Örnek: Bir aday 3 dakikada 103 kelime yazmış, bunların 13’ünde hata yapmış ve 1 kelime atlamış olsun. Net kelimesi 103 − 13 = <b>90</b> olur; '
             'atlama 22’nin, hata oranı (%12,6) %25’in altında olduğu için 90 net barajlı bir ilanda <b>başarılı</b> sayılır.</p></section>'
             f'<section class="bolum"><h2>Hata türleri</h2><div style="overflow-x:auto"><table class="ks-tablo"><thead><tr><th>Hata türü</th><th>Ne zaman</th><th>Örnek</th><th>Sayım</th></tr></thead><tbody>{tablo}</tbody></table></div></section>'
             '<section class="bolum"><h2>Hata sayılmayan durumlar</h2><ul><li><b>Atlanan kelime:</b> metinde olup yazılmayan kelime hata sayılmaz, ama toplamı 22’ye ulaşırsa sınav başarısızdır.</li>'
             '<li><b>Eksik son kelime:</b> süre dolarken yarım kalan son kelime hata sayılmaz.</li></ul></section>'
             '<section class="bolum"><h2>Başarısızlık koşulları</h2><ol><li>Net kelimenin ilandaki barajın (çoğunlukla 90) altında kalması,</li>'
             '<li>ayrı ayrı veya peş peşe toplam 22 ve üzeri kelime atlanması,</li><li>hata oranının %25’i aşması (metin anlam bütünlüğü taşımıyor sayılır).</li></ol></section>'
             + hesap + _sss_html(su.esc, sorular)
             + f'<p class="kp-note">Kaynak: Adalet Bakanlığı <a href="{KRITER_ZABIT}" rel="noopener" target="_blank">Zabıt Katibi Uygulamalı Sınav Değerlendirme Kriterleri</a> ve '
               f'<a href="{KRITER_ICRA}" rel="noopener" target="_blank">İcra Kâtipliği Uygulama Sınavı Değerlendirme Kriterleri</a>; bu sayfa kendi cümlelerimizle özetler. '
               'Baraj ve ayrıntılar her ilanda ayrıca belirtilir; başvurduğun ilanın metnini esas al.</p>' + _araclar(kok))
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Article', 'headline': 'Klavye sınavı değerlendirme kriterleri ve net hesaplama', 'description': aciklama, 'inLanguage': 'tr-TR',
         'mainEntityOfPage': canonical, 'datePublished': GUNCELLEME, 'dateModified': GUNCELLEME,
         'author': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}, 'publisher': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}},
        _kirinti(base, [('Ana sayfa', base), ('Katiplik', f'{base}katiplik/'), ('Değerlendirme kriterleri', canonical)]), _sss_ld(sorular)]}
    kir = f'<a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}katiplik/">Katiplik</a>'
    return canonical, _kabuk(su, baslik, aciklama, canonical, kok, kir, 'Katiplik · rehber', 'Klavye sınavı değerlendirme kriterleri ve net hesaplama',
                             'Zabıt ve icra katipliği uygulamalı sınavında hangi yazım hata sayılır, net kelime nasıl bulunur, ne zaman başarısız sayılırsın? '
                             'Örnekler ve hesaplayıcıyla.', govde, ld)


def rehber_sayfasi(su, base):
    kok = '../../'
    canonical = f'{base}katiplik/klavye-sinavi-rehberi/'
    baslik = 'Zabıt Katipliği Klavye Sınavı Nasıl Yapılır? Hazırlık Rehberi ve Çalışma Planı | KPSS Tercihi'
    aciklama = ('Zabıt, icra ve CTE katipliği klavye (uygulama) sınavı nasıl yapılır, metinler nereden çıkar, F mi Q klavye mi, 90 nete nasıl '
                'ulaşılır? 4 haftalık çalışma planı, sınav günü ipuçları ve ücretsiz simülasyon.')
    sorular = [
        ('Zabıt katipliği klavye sınavı kaç dakika?', 'Uygulamalı sınav 3 dakikadır. Bu sürede verilen metni hatasız ve atlamadan yazmaya çalışırsın.'),
        ('Klavye sınavında kaç net gerekir?', 'İlanlarda genellikle 3 dakikada en az 90 net kelime aranır. Baraj ilana göre değişebileceği için başvurduğun ilanın metnini kontrol et.'),
        ('Sınavda çıkacak metin önceden belli mi?', 'Bakanlık uygulamalı sınav metinlerini sınavdan önce yayımlar ve sınavda bu metinlerden biri kurayla seçilir. Yayımlanan metinlerle önceden çalışmak büyük avantaj sağlar.'),
        ('F klavye mi Q klavye mi kullanmalıyım?', 'Hangi klavyeye alışkınsan onunla çalış. Sınavda kullanılabilecek klavye türü ilanda belirtilir; başvuru sırasında tercih istenip istenmediğini ilan metninden kontrol et.'),
        ('Klavye hızımı ne kadar sürede 90 nete çıkarabilirim?', 'Başlangıç seviyene bağlıdır. On parmak bilen biri düzenli günlük çalışmayla birkaç haftada belirgin artış görür; hiç bilmeyen biri önce 1–2 hafta temel dersleri tamamlamalıdır.'),
    ]
    plan = [
        ('1. hafta: temel ve doğruluk', 'Her gün 20–30 dakika on parmak dersleri (temel, üst ve alt sıra). Hızı düşünme; doğruluk %97’nin üzerine çıksın.', 'katiplik/dersler/'),
        ('2. hafta: kelime akıcılığı', 'Günde 2 hız testi, sık kullanılan hukuk kelimeleri ve Türkçe karakter ısınması. Akşamları bir sınav simülasyonu.', 'katiplik/antrenman/'),
        ('3. hafta: resmî metinler', 'Her gün en az 2 resmî metinle 3 dakikalık simülasyon. Tutanaktaki hata türlerini not et, hata defterini tekrarla.', 'katiplik/sinav-metinleri/'),
        ('4. hafta: sınav provası', 'Günün metni + 3 simülasyon. Isınma yap, sınav saatinde çalış, hatasız yazmaya odaklan. Sınavdan önceki gün hafif tut.', 'katiplik/'),
    ]
    plan_html = ''.join(f'<li><b>{su.esc(a)}:</b> {su.esc(b)} <a href="{kok}{c}">Araca git →</a></li>' for a, b, c in plan)
    govde = ('<div class="ks-cta"><a class="btn btn-ana btn-buyuk" href="../" data-a="katiplik" data-a-x="rehber-sinav">Ücretsiz deneme sınavına gir</a>'
             '<a class="btn btn-ikinci btn-buyuk" href="../sinav-metinleri/">2025 resmî metinler</a></div>'
             '<section class="bolum"><h2>Klavye (uygulama) sınavı nasıl yapılır?</h2><p>Zabıt kâtipliği ve icra kâtipliği alımlarında adaylar önce uygulamalı '
             '(klavye) sınavına, başarılı olanlar sözlü sınava alınır. Uygulamalı sınavda bilgisayarda <b>3 dakika</b> boyunca ekranda verilen metni yazarsın. '
             'Metinler tamamen küçük harf ve noktalamasızdır. Süre bitince yazılan metin, Bakanlığın değerlendirme kriterlerine göre kelime kelime incelenir ve '
             '<b>net kelime</b> sayın bulunur.</p><p>Bakanlık, sınavda kullanılacak metinleri sınavdan önce internet sitesinde yayımlar; sınavda bu metinlerden '
             'biri seçilir. 2025 sınavının 30 metnine <a href="../sinav-metinleri/">buradan</a> ulaşabilirsin.</p></section>'
             '<section class="bolum"><h2>Hangi kâtiplikler bu sınavla alınır?</h2><ul><li><b>Zabıt kâtibi:</b> mahkeme kalemlerinde duruşma tutanağı ve yazı işleri.</li>'
             '<li><b>İcra kâtibi:</b> icra dairelerinde takip, haciz ve tebligat işlemleri.</li><li><b>Ceza infaz kurumu (CTE) kâtibi:</b> ceza infaz kurumlarının yazı işleri.</li></ul>'
             '<p>Uygulamalı sınavın puanlama mantığı bu alımlarda benzerdir; ayrıntılar her ilanda belirtilir.</p></section>'
             f'<section class="bolum"><h2>4 haftalık çalışma planı</h2><ol>{plan_html}</ol><p>Sınav tarihini girersen simülasyon sayfasındaki <a href="../#yol-haritasi">90 net yol haritası</a> '
             'sonuçlarına göre günlük programını kendisi çıkarır.</p></section>'
             '<section class="bolum"><h2>Sınav günü ipuçları</h2><ul><li>Sınavdan önce 5 dakika Türkçe karakter ısınması yap; parmaklarını ısıt.</li>'
             '<li>İlk 20 saniyede hızlanmaya çalışma; ritmini bul, sonra tempoyu koru.</li><li>Yanlış yazdığın kelimeye geri dönüp uzun uğraşma; çoğu zaman yeni kelime yazmak daha kârlıdır.</li>'
             '<li>Asla metne nokta, virgül veya büyük harf ekleme; bunlar karışık hata sayılır.</li><li>Satır atlamamak için gözünü metinde, yazdığın son kelimenin hizasında tut.</li></ul></section>'
             '<section class="bolum"><h2>En sık yapılan hatalar</h2><p>Sınav tutanaklarında en sık görülen hatalar <b>eksik vuruş</b> (özellikle uzun ve ekli kelimelerde), '
             '<b>Türkçe karakter karışması</b> (ı/i, ş/s, ğ/g) ve <b>kelime birleştirme</b>dir (boşluğa basmayı unutmak). Hepsinin nasıl sayıldığını '
             '<a href="../degerlendirme-kriterleri/">değerlendirme kriterleri</a> sayfasında örneklerle anlattık.</p></section>'
             + _sss_html(su.esc, sorular)
             + '<p class="kp-note">Bu yazı genel bilgi amaçlıdır. Sınav tarihi, baraj, klavye türü ve başvuru şartları her ilanda ayrıca belirtilir; başvurmadan önce '
               'ilanın resmî metnini ve Adalet Bakanlığı duyurularını esas al.</p>' + _araclar(kok))
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Article', 'headline': 'Zabıt katipliği klavye sınavı nasıl yapılır? Hazırlık rehberi', 'description': aciklama, 'inLanguage': 'tr-TR',
         'mainEntityOfPage': canonical, 'datePublished': GUNCELLEME, 'dateModified': GUNCELLEME,
         'author': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}, 'publisher': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}},
        _kirinti(base, [('Ana sayfa', base), ('Katiplik', f'{base}katiplik/'), ('Klavye sınavı rehberi', canonical)]), _sss_ld(sorular)]}
    kir = f'<a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span><a href="{kok}katiplik/">Katiplik</a>'
    return canonical, _kabuk(su, baslik, aciklama, canonical, kok, kir, 'Katiplik · rehber', 'Zabıt katipliği klavye sınavı nasıl yapılır?',
                             'Sınavın işleyişi, metinlerin nereden çıktığı, 90 nete ulaşmak için 4 haftalık çalışma planı ve sınav günü ipuçları.', govde, ld)


def yaz(docs, base):
    """Katiplik SEO sayfalarını yazar; site haritası için adresleri döner."""
    import site_uret as su
    docs = Path(docs)
    metinler = metinleri_oku(docs)
    adresler = []

    def kaydet(yol, sonuc):
        url, html = sonuc
        (docs / yol).mkdir(parents=True, exist_ok=True)
        (docs / yol / 'index.html').write_text(html, encoding='utf-8')
        adresler.append(url)
    kaydet('katiplik/sinav-metinleri', dizin_sayfasi(su, base, metinler))
    for i in range(len(metinler)):
        kaydet(f'katiplik/sinav-metinleri/metin-{i + 1}', metin_sayfasi(su, base, metinler, i))
    kaydet('katiplik/degerlendirme-kriterleri', kriter_sayfasi(su, base))
    kaydet('katiplik/klavye-sinavi-rehberi', rehber_sayfasi(su, base))
    return adresler
