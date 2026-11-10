"""Gizlilik ve Hakkımızda sayfalarının taranabilir (statik) sürümleri: /gizlilik/ ve /hakkimizda/.
Ana sayfadaki '#bilgi/...' görünümleri JavaScript ile açılır; Google ve AdSense incelemesi ayrı adreste düz HTML görür.
Metin docs/portal.js 'bilgi/gizlilik' ve 'bilgi/hakkimizda' ile aynı tutulur."""

ILETISIM = 'https://t.me/kpsstercihi'
ILETISIM_EPOSTA = 'iletisim@kpsstercihi.com'   # Cloudflare Email Routing ile yönlenir; boşsa /iletisim/ sayfasında E-posta bölümü çıkmaz
GUNCELLEME = '2026-11-10'   # sayfa metinleri değişince elle artırılır; sayfada "Son güncelleme" olarak görünür
SEMA_TURU = {'hakkimizda': 'AboutPage', 'iletisim': 'ContactPage'}

SAYFALAR = {
    'gizlilik': ('Gizlilik politikası', 'KPSS Tercihi gizlilik politikası: tarayıcıda saklanan bilgiler, çerezsiz ziyaret istatistikleri ve Google AdSense reklamları.',
                 'Bu site üyelik istemez. Özgeçmiş, kimlik bilgisi veya başvuru belgesi toplamak için bir form içermez.', [
        ('Bu cihazda saklanan bilgiler', 'Kaydettiğin ilanların kimlikleri, profilin (öğrenim düzeyi, puan, iller), son ziyaret zamanın ve renk teması '
         'tercihin tarayıcının yerel depolamasında tutulur. Katiplik klavye sınavı, ders, antrenman ve oyunlarındaki sonuçların, hatalı kelimelerin ve tuş istatistiklerin de yalnızca bu tarayıcıda tutulur; yazdığın metin sunucuya gönderilmez. Bunlar başka cihazlara taşınmaz ve sunucumuza gönderilmez. Tarayıcı verilerini silerek '
         'ya da ana sayfadaki Gizlilik bölümündeki düğmeyle temizleyebilirsin.'),
        ('Dış bağlantılar ve barındırma', 'Resmî başvuru sayfası ve Telegram bağlantıları kendi hizmetlerine yönlendirir. Bu hizmetlerin veri '
         'uygulamaları ayrıdır. Site dosyaları bir barındırma hizmeti üzerinden sunulur; bu hizmet teknik erişim kayıtlarını işleyebilir.'),
        ('Ziyaret istatistikleri', 'Hangi sayfaların ve özelliklerin kullanıldığını anlamak için anonim ve çerezsiz ziyaret istatistikleri toplanır; '
         'IP adresin saklanmaz, kişisel veri toplanmaz ve seni sonraki günlerde tanıyacak bir kimlik tutulmaz. Tarayıcında “Do Not Track” ya da '
         'Global Privacy Control (GPC) açıksa hiç ölçüm yapılmaz. Bu ölçüm verisi üçüncü taraflarla paylaşılmaz.'),
        ('Reklamlar ve çerezler', 'Sitede Google AdSense reklamları gösterilir. Google dahil üçüncü taraf sağlayıcılar, bu siteye ve internetteki '
         'başka sitelere yaptığın önceki ziyaretlere dayanarak reklam sunmak için çerez kullanır. Google’ın reklam çerezlerini kullanması, Google ve iş '
         'ortaklarının bu siteye ve/veya internetteki diğer sitelere yaptığın ziyaretlere göre reklam göstermesini sağlar. Kişiselleştirilmiş reklamları '
         'Google Reklam Ayarları’ndan (adssettings.google.com) kapatabilir, üçüncü taraf çerezlerini www.aboutads.info üzerinden yönetebilirsin. '
         'Ayrıntılar: policies.google.com/technologies/ads'),
        ('Sosyal medya hesaplarımız', 'Instagram, YouTube ve TikTok hesaplarımızdaki paylaşımlar, bu platformların resmî paylaşım '
         'arayüzleriyle yalnız kendi hesaplarımıza yapılır. Bu bağlantılar üzerinden takipçilerin ya da ziyaretçilerin kişisel verisi '
         'toplanmaz, saklanmaz, paylaşılmaz.'),
        ('İletişim', f'Gizlilikle ilgili soruların için {ILETISIM_EPOSTA} adresine yazabilirsin. Bize yazarsan e-posta adresin ve iletin yalnızca yanıt vermek için kullanılır.'),
    ]),
    'kullanim-kosullari': ('Kullanım koşulları', 'KPSS Tercihi kullanım koşulları: hizmetin kapsamı, bilgilerin doğruluğu ve sorumluluk.',
                           'KPSS Tercihi’ni ve sosyal medya hesaplarımızı kullanarak aşağıdaki koşulları kabul etmiş olursun.', [
        ('Hizmetin kapsamı', 'KPSS Tercihi, resmî kaynaklarda yayımlanan kamu personel ilanlarını derleyen ücretsiz ve bağımsız bir rehberdir. '
         'Üyelik gerektirmez; başvuru almaz, aracılık yapmaz.'),
        ('Bilgilerin doğruluğu', 'İlanlar resmî kaynaklardan otomatik olarak derlenir ve gecikebilir ya da eksik olabilir. Başvurmadan önce '
         'güncel ve bağlayıcı bilgi için ilgili kurumun resmî ilanını esas al. Taban puanları ÖSYM’nin yayımladığı sayısal bilgilerden derlenir '
         've geçmiş dönemleri gösterir; gelecek yerleştirmeler için garanti değildir.'),
        ('Sorumluluk', 'Sitedeki ya da sosyal medya paylaşımlarımızdaki bilgilere dayanarak yapılan başvuru ve tercihlerden doğan sonuçlardan '
         'KPSS Tercihi sorumlu tutulamaz.'),
        ('İçerik kullanımı', 'Paylaşımlarımızı kaynak göstererek paylaşabilirsin. İlan metinleri ve resmî belgeler ilgili kurumlara aittir.'),
        ('Değişiklikler', 'Bu koşullar gerektiğinde güncellenebilir; güncel metin her zaman bu sayfadadır.'),
        ('İletişim', f'Soruların için {ILETISIM_EPOSTA} adresine yazabilirsin.'),
    ]),
    'hakkimizda': ('Hakkımızda', 'KPSS Tercihi nedir, ilanlar hangi resmî kaynaklardan derlenir, nasıl iletişim kurulur?',
                   'KPSS Tercihi, kamu personel ilanlarını daha kolay incelemek ve takip etmek için hazırlanmış bağımsız bir rehberdir.', [
        ('Veriler nereden geliyor?', 'İlanlar Kariyer Kapısı resmî RSS akışından, İŞKUR kamu memur alım ilanları sayfalarından, SBB Kamu İlan '
         'listesinden ve Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Yerel Yönetimler duyurularından (ÇŞB) derlenir. Kurum, görev yeri, '
         'kontenjan ve koşullar kaynağın sunduğu bilgilerle sınırlıdır.'),
        ('Ne sunuyoruz?', 'Açık ilanlar tek listede, son başvuru tarihine göre; kurum sayfaları, KPSS taban puanları ve tercih robotu. Yeni ilanlar '
         'Telegram kanalımızda (@kpsstercihi) da paylaşılır.'),
        ('Kim hazırlıyor?', 'KPSS Tercihi bağımsız bir yayındır; içerikler “KPSS Tercihi Editörlüğü” adıyla yayımlanır. Herhangi bir kamu kurumuna, kursa ya da yayınevine bağlı değildir. Site ücretsizdir, üyelik istemez; giderleri reklam gelirleriyle karşılanır.'),
        ('Neden kuruldu?', "Kamu ilanları Kariyer Kapısı, İŞKUR, Kamu İlan ve Yerel Yönetimler gibi ayrı kaynaklarda, çoğu zaman uzun PDF belgeleri içinde yayımlanıyor. KPSS Tercihi bu ilanları tek listede toplar; kadroları ve koşulları okunur hâle getirir, ÖSYM'nin geçmiş yerleştirme verileriyle birlikte sunar."),
        ('İlanları nasıl hazırlıyoruz?', 'Kaynaklar gün içinde düzenli olarak taranır. İlan belgeleri otomatik araçlarla ve yapay zekâ desteğiyle okunur; kadro, koşul ve tarih bilgileri belgeyle karşılaştırılır. Aynı ilanın farklı kaynaklardaki kopyaları birleştirilir. Okunamayan ya da belirsiz bilgi tahmin edilmez, resmî belgeye yönlendirilir.'),
        ('Düzeltme ve iptaller', 'Bir ilan için iptal ya da düzeltme duyurusu yayımlandığında bu bilgi ilan sayfasına işlenir. Hatalı bir bilgi fark edersen iletişim sayfasından bildirebilirsin; kontrol edip düzeltiriz.'),
        ('Puan verileri ve analizler', "Taban puanları, tercih robotu ve analiz sayfaları ÖSYM'nin yayımladığı 2022–2026 KPSS yerleştirme sayısal bilgilerinden hesaplanır. Geçmiş sonuçları gösterir, gelecek için garanti değildir."),
        ('Resmî bir hizmet mi?', 'Hayır. Herhangi bir kamu kurumuna bağlı değiliz. Başvuru kabul etmeyiz, aday uygunluğu değerlendirmeyiz. Güncel ve '
         'bağlayıcı bilgi için resmî ilanı esas al.'),
        ('İletişim', 'Hatalı bir ilan, öneri ya da iş birliği için iletişim sayfamızdan bize ulaşabilirsin.', '<a class="yazi-link" href="../iletisim/">İletişim sayfası →</a>'),
    ]),
}


def _iletisim_bolumleri():
    bolumler = [('Telegram', 'Duyurular için kanalımız: @kpsstercihi')]
    if ILETISIM_EPOSTA:
        bolumler.append(('E-posta', 'Soru, düzeltme ve iş birliği için:', f'<a class="yazi-link" href="mailto:{ILETISIM_EPOSTA}">{ILETISIM_EPOSTA}</a>'))
    bolumler.append(('Hatalı ilan bildirirken', 'İlanın bağlantısını ve hatalı gördüğün bilgiyi yazman yeterli. Bildirimi resmî ilan belgesiyle karşılaştırır, '
                     'hata varsa ilan sayfasını düzeltiriz.'))
    bolumler.append(('Neler için yazabilirsin?', 'Yanlış tarih, kontenjan ya da koşul bildirimi; eksik bir kurum veya kaynak önerisi; taban puanı verisi, tercih robotu ve '
                     'klavye sınavıyla ilgili sorunlar; iş birliği ve reklam teklifleri.'))
    bolumler.append(('Yardımcı olamayacağımız konular', 'Kamu kurumlarına bağlı değiliz. Başvuru almıyoruz, başvurunun sonucunu göremiyoruz ve kurumlar adına karar veremiyoruz. '
                     'Başvuru ve atama sürecindeki sorular için ilanı yayımlayan kurumla görüşmelisin.'))
    return bolumler


def _sayfalar():
    """Sabit sayfalar + İletişim (e-posta sabitine göre bölümleri değişir)."""
    return dict(SAYFALAR, iletisim=('İletişim', 'KPSS Tercihi iletişim: hatalı ilan bildirimi, öneri ve iş birliği.',
                                    'Hatalı ilan bildirimi, öneri ya da iş birliği için bize ulaşabilirsin.', _iletisim_bolumleri()))


def _sema(ad, base, canonical, baslik, aciklama):
    """Hakkımızda ve İletişim için yayıncı kimliği (JSON-LD); diğer sayfalarda boş."""
    if ad not in SEMA_TURU:
        return ''
    import json
    import site_uret as su
    ld = {'@context': 'https://schema.org', '@type': SEMA_TURU[ad], 'url': canonical, 'name': baslik, 'description': aciklama,
          'inLanguage': 'tr', 'dateModified': GUNCELLEME, 'mainEntity': su.kurulus_ld(base)}
    return '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def sayfa(ad, base):
    """(adres, html) — SSS sayfasıyla aynı kabuk."""
    import site_uret as su
    baslik, aciklama, giris, bolumler = _sayfalar()[ad]
    canonical = base + ad + '/'
    maddeler = ''.join(f'<section class="bolum"><h2>{su.esc(b[0])}</h2><p>{su.esc(b[1])}</p>{b[2] if len(b) > 2 else ""}</section>' for b in bolumler)
    maddeler += f'<p><a class="yazi-link" href="{ILETISIM}" target="_blank" rel="noopener">Telegram ↗</a></p>'
    maddeler += f'<p class="muted">Son güncelleme: {su.tarih_yazi(GUNCELLEME)}</p>'
    html = (su.sayfa_basi(f'{baslik} — KPSS Tercihi', aciklama, su.esc(canonical), '../',
                          ek_head=f'<meta property="og:url" content="{su.esc(canonical)}">' + _sema(ad, base, canonical, baslik, aciklama))
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html("../")}'
            + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a><span aria-hidden="true">/</span>'
            + f'<span>{su.esc(baslik)}</span></nav><h1>{su.esc(baslik)}</h1><p>{su.esc(giris)}</p></div></section>'
            + f'<main id="icerik" class="wrap kp-main">{maddeler}</main>{su.alt_html("../")}</body></html>')
    return canonical, html


def yaz(docs, base):
    """Sayfaları yazar; site haritası için adresleri döner."""
    adresler = []
    for ad in _sayfalar():
        adres, html = sayfa(ad, base)
        (docs / ad).mkdir(exist_ok=True)
        (docs / ad / 'index.html').write_text(html, encoding='utf-8')
        adresler.append(adres)
    return adresler
