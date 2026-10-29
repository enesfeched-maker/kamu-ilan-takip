"""Gizlilik ve Hakkımızda sayfalarının taranabilir (statik) sürümleri: /gizlilik/ ve /hakkimizda/.
Ana sayfadaki '#bilgi/...' görünümleri JavaScript ile açılır; Google ve AdSense incelemesi ayrı adreste düz HTML görür.
Metin docs/portal.js 'bilgi/gizlilik' ve 'bilgi/hakkimizda' ile aynı tutulur."""

ILETISIM = 'https://t.me/kpsstercihi'

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
        ('İletişim', 'Gizlilikle ilgili soruların için Telegram kanalımızı (@kpsstercihi) kullanabilirsin.'),
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
        ('İletişim', 'Soruların için Telegram kanalımız (@kpsstercihi) üzerinden ulaşabilirsin.'),
    ]),
    'hakkimizda': ('Hakkımızda', 'KPSS Tercihi nedir, ilanlar hangi resmî kaynaklardan derlenir, nasıl iletişim kurulur?',
                   'KPSS Tercihi, kamu personel ilanlarını daha kolay incelemek ve takip etmek için hazırlanmış bağımsız bir rehberdir.', [
        ('Veriler nereden geliyor?', 'İlanlar Kariyer Kapısı resmî RSS akışından, İŞKUR kamu memur alım ilanları sayfalarından, SBB Kamu İlan '
         'listesinden ve Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Yerel Yönetimler duyurularından (ÇŞB) derlenir. Kurum, görev yeri, '
         'kontenjan ve koşullar kaynağın sunduğu bilgilerle sınırlıdır.'),
        ('Ne sunuyoruz?', 'Açık ilanlar tek listede, son başvuru tarihine göre; kurum sayfaları, KPSS taban puanları ve tercih robotu. Yeni ilanlar '
         'Telegram kanalımızda (@kpsstercihi) da paylaşılır.'),
        ('Resmî bir hizmet mi?', 'Hayır. Herhangi bir kamu kurumuna bağlı değiliz. Başvuru kabul etmeyiz, aday uygunluğu değerlendirmeyiz. Güncel ve '
         'bağlayıcı bilgi için resmî ilanı esas al.'),
        ('İletişim', 'Hatalı bir ilan, öneri ya da iş birliği için Telegram kanalımız (@kpsstercihi) üzerinden ulaşabilirsin.'),
    ]),
}


def sayfa(ad, base):
    """(adres, html) — SSS sayfasıyla aynı kabuk."""
    import site_uret as su
    baslik, aciklama, giris, bolumler = SAYFALAR[ad]
    canonical = base + ad + '/'
    maddeler = ''.join(f'<section class="bolum"><h2>{su.esc(b)}</h2><p>{su.esc(m)}</p></section>' for b, m in bolumler)
    maddeler += f'<p><a class="yazi-link" href="{ILETISIM}" target="_blank" rel="noopener">Telegram ↗</a></p>'
    html = (su.sayfa_basi(f'{baslik} — KPSS Tercihi', aciklama, su.esc(canonical), '../',
                          ek_head=f'<meta property="og:url" content="{su.esc(canonical)}">')
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html("../")}'
            + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a><span aria-hidden="true">/</span>'
            + f'<span>{su.esc(baslik)}</span></nav><h1>{su.esc(baslik)}</h1><p>{su.esc(giris)}</p></div></section>'
            + f'<main id="icerik" class="wrap kp-main">{maddeler}</main>{su.alt_html("../")}</body></html>')
    return canonical, html


def yaz(docs, base):
    """Sayfaları yazar; site haritası için adresleri döner."""
    adresler = []
    for ad in SAYFALAR:
        adres, html = sayfa(ad, base)
        (docs / ad).mkdir(exist_ok=True)
        (docs / ad / 'index.html').write_text(html, encoding='utf-8')
        adresler.append(adres)
    return adresler
