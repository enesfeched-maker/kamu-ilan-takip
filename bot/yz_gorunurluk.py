"""Yapay zekâ asistanları (ChatGPT, Gemini, Perplexity…) ve arama motorları için okunur içerik.

- llms.txt: sitenin ne olduğunu ve açık ilanları JavaScript gerektirmeden düz metinle anlatır (ana sayfa JS ile dolar).
- /sss/: kısa soru-cevap sayfası (FAQPage yapılandırılmış verisi); asistanlar bu tür net cevapları alıntılar.
"""
import json
from datetime import date

OGRENIM_AD = {'lisans': 'lisans', 'onlisans': 'önlisans', 'ortaogretim': 'ortaöğretim', 'ilkogretim': 'ilköğretim'}
AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
LLMS_EN_COK = 150

SSS = [
    ('KPSS Tercihi nedir?',
     'KPSS Tercihi (kpsstercihi.com), kamu kurumlarının personel alım ilanlarını resmî kaynaklardan toplayıp tek listede gösteren '
     'ücretsiz bir sitedir. KPSS\'li ve KPSS\'siz, memur, sözleşmeli personel ve işçi alımları kurum, il, öğrenim düzeyi ve son başvuru '
     'tarihiyle birlikte listelenir.'),
    ('Güncel kamu personel alım ilanlarını nereden takip edebilirim?',
     'kpsstercihi.com ana sayfasında açık ilanlar son başvuru tarihine göre listelenir; yeni ilanlar ayrıca Telegram kanalı '
     '@kamuilantakip üzerinden anında paylaşılır.'),
    ('İlanlar ne sıklıkla güncellenir?',
     'Kaynaklar gün boyunca yaklaşık 30 dakikada bir taranır. Yeni ilan, son başvuru tarihi değişikliği veya iptal olduğunda liste kendiliğinden güncellenir.'),
    ('Site ücretli mi, üyelik gerekiyor mu?',
     'Hayır. Site tamamen ücretsizdir ve üyelik gerekmez. Kaydettiğin ilanlar yalnızca kendi tarayıcında saklanır.'),
    ('Başvuruyu KPSS Tercihi üzerinden mi yapıyorum?',
     'Hayır. Her ilan sayfasında kurumun resmî başvuru bağlantısı bulunur; başvuru kurumun belirttiği yerden (çoğunlukla Kariyer Kapısı '
     'veya e-Devlet) yapılır. Başvurmadan önce resmî ilan metnini okumalısın.'),
    ('KPSS puanımla hangi kadrolara yerleşebilirim?',
     'Tercih robotuna (kpsstercihi.com/puanlar/) puanını ve puan türünü girersen geçmiş KPSS yerleştirmelerinde bu puanın yettiği kadroları görürsün.'),
    ('KPSS taban puanlarına nereden bakabilirim?',
     'kpsstercihi.com/kpss-taban-puanlari/ sayfasında lisans, önlisans ve ortaöğretim kadrolarının dönem dönem en düşük ve en yüksek '
     'yerleşme puanları ÖSYM verilerinden derlenmiştir.'),
    ('KPSS şartı olmayan kamu ilanları da var mı?',
     'Evet. Belediye, üniversite ve İŞKUR üzerinden yapılan bazı alımlarda KPSS şartı aranmaz; bu ilanlar da listede yer alır ve ilan '
     'kartında KPSS şartı olmadığı belirtilir.'),
]


def _tarih(gun):
    try:
        d = date.fromisoformat(str(gun)[:10])
    except ValueError:
        return ''
    return f'{d.day} {AYLAR[d.month - 1]} {d.year}'


def llms_metni(kayitlar, base, simdi, sayfasi_olan=None):
    """kayitlar: liste.json 'ilanlar' (kopyalar hariç). sayfasi_olan: yalnız bu anahtarların ilan sayfası var."""
    acik = [k for k in kayitlar if k.get('durum') not in ('expired', 'belirsiz') and not k.get('kopya_of')
            and (sayfasi_olan is None or k.get('key') in sayfasi_olan)]
    acik.sort(key=lambda k: (k.get('son_tarih') or '9999', -(k.get('toplam') or 0)))
    satirlar = [
        '# KPSS Tercihi',
        '',
        '> Türkiye\'deki kamu kurumlarının güncel personel alım ilanlarını (KPSS\'li/KPSS\'siz, memur, sözleşmeli, işçi) resmî '
        'kaynaklardan toplayıp tek listede gösteren ücretsiz site. Ayrıca KPSS taban puanları ve puana göre kadro bulan tercih robotu sunar.',
        '',
        f'Güncelleme: {_tarih(simdi.date().isoformat())}. Kaynaklar yaklaşık 30 dakikada bir taranır. Başvurular sitede değil, '
        'her ilanda verilen resmî bağlantıdan yapılır.',
        '',
        '## Ana sayfalar',
        f'- [Güncel kamu ilanları]({base}): açık ilanlar, son başvuru tarihine göre',
        f'- [KPSS tercih robotu]({base}puanlar/): puanını gir, geçmiş yerleştirmelerde yettiği kadroları gör',
        f'- [KPSS taban puanları]({base}kpss-taban-puanlari/): lisans, önlisans, ortaöğretim kadro kadro en düşük/en yüksek puanlar',
        f'- [Sık sorulan sorular]({base}sss/)',
        '- [Telegram kanalı](https://t.me/kamuilantakip): yeni ilanlar anında',
        '',
        f'## Açık ilanlar ({len(acik)})',
    ]
    for k in acik[:LLMS_EN_COK]:
        parca = [k.get('kurum') or 'Kurum belirtilmemiş']
        if k.get('manset'):
            parca.append(k['manset'])
        iller = k.get('iller') or []
        if iller:
            parca.append(', '.join(iller[:3]) + (' ve diğer iller' if len(iller) > 3 else ''))
        ogr = [OGRENIM_AD[o] for o in (k.get('ogrenim') or []) if o in OGRENIM_AD]
        if ogr:
            parca.append('/'.join(ogr))
        if k.get('kpss') == 'kpss':
            parca.append('KPSS ' + '/'.join(k.get('puan_turleri') or []) if k.get('puan_turleri') else 'KPSS şartlı')
        elif k.get('kpss'):
            parca.append('KPSS şartı yok')
        if k.get('son_tarih'):
            parca.append('son başvuru ' + _tarih(k['son_tarih']))
        satirlar.append(f'- [{" — ".join(parca[:2])}]({base}ilan/{k["key"]}/): {"; ".join(parca[2:])}'.rstrip(': '))
    if len(acik) > LLMS_EN_COK:
        satirlar.append(f'- … ve {len(acik) - LLMS_EN_COK} ilan daha: {base}')
    return '\n'.join(satirlar) + '\n'


def sss_sayfasi(base):
    """(adres, html) — site kabuğuyla aynı görünümde kısa SSS sayfası."""
    import site_uret as su
    canonical = base + 'sss/'
    veri = {'@context': 'https://schema.org', '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question', 'name': s, 'acceptedAnswer': {'@type': 'Answer', 'text': c}} for s, c in SSS]}
    ld = json.dumps(veri, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    ek = f'<meta property="og:url" content="{su.esc(canonical)}"><script type="application/ld+json">{ld}</script>'
    maddeler = ''.join(f'<section class="bolum"><h2>{su.esc(s)}</h2><p>{su.esc(c)}</p></section>' for s, c in SSS)
    govde = (su.sayfa_basi('Sık Sorulan Sorular — KPSS Tercihi', 'KPSS Tercihi nedir, kamu ilanları nereden takip edilir, başvuru nasıl yapılır? Kısa cevaplar.',
                           su.esc(canonical), '../', ek_head=ek)
             + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html("../")}'
             + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a><span aria-hidden="true">/</span>'
             + '<span>Sık sorulan sorular</span></nav><h1>Sık sorulan sorular</h1><p>KPSS Tercihi hakkında kısa cevaplar.</p></div></section>'
             + f'<main id="icerik" class="wrap kp-main">{maddeler}</main>{su.alt_html("../")}</body></html>')
    return canonical, govde
