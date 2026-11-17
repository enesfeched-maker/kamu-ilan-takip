"""Forum sayfası (/forum/, Kasım 2026): statik kabuk; başlıklar ve yanıtlar forum.js ile kpss-forum Worker'ından gelir.

İçerik tarayıcıda yüklendiği için sayfa şimdilik noindex ve reklamsızdır (AdSense 'düşük değer' kalkanı, #309).
"""


def forum_sayfasi(base):
    """(adres, html)."""
    import site_uret as su
    import forum_seo   # FORUM_DIZINLE kapalıyken kabuk noindex kalır; açıkken son sorular sunucu tarafında listelenir
    canonical = base + 'forum/'
    dizinli = forum_seo.kabuk_dizinli()
    liste = forum_seo.kabuk_listesi()
    if liste:   # JS açıkken uygulama kendi listesini gösterir; sunucu listesi yalnız tarayıcısız okuyucu/tarayıcı botu içindir
        liste += '<script>document.getElementById("fq-son").hidden=true</script>'
    ek = (('' if dizinli else '<meta name="robots" content="noindex,follow">') + f'<meta property="og:url" content="{su.esc(canonical)}">'
          f'<link rel="stylesheet" href="../forum.css?v={su.FORUM_SURUM}">'
          f'<link rel="stylesheet" href="../forum-sohbet.css?v={su.FORUM_SURUM}">')
    baslik = 'KPSS Forum: ilan, puan ve tercih soruları | KPSS Tercihi' if dizinli else 'Forum — KPSS Tercihi'
    govde = (su.sayfa_basi(baslik, 'KPSS adaylarının ilanlar, puanlar, tercih, kurumlar ve mülakatlar hakkında soru sorup deneyim paylaştığı forum.',
                           su.esc(canonical), '../', ek_head=ek)
             + f'<body class="kurum-page forum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html("../", "forum")}'
             + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a><span aria-hidden="true">/</span>'
             + '<span>Forum</span></nav><h1>Forum</h1></div></section>'
             + '<main id="icerik" class="wrap kp-main"><div id="forum" class="fr-kok" aria-live="polite">'
             + '<noscript><p class="muted">Forumu görmek için JavaScript gerekir.</p></noscript></div>' + liste + '</main>'
             + f'{su.alt_html("../")}<script src="../forum.js?v={su.FORUM_SURUM}" defer></script></body></html>')
    return canonical, govde
