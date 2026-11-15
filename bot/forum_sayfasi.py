"""Forum sayfası (/forum/, Kasım 2026): statik kabuk; başlıklar ve yanıtlar forum.js ile kpss-forum Worker'ından gelir.

İçerik tarayıcıda yüklendiği için sayfa şimdilik noindex ve reklamsızdır (AdSense 'düşük değer' kalkanı, #309).
"""


def forum_sayfasi(base):
    """(adres, html)."""
    import site_uret as su
    canonical = base + 'forum/'
    ek = (f'<meta name="robots" content="noindex,follow"><meta property="og:url" content="{su.esc(canonical)}">'
          f'<link rel="stylesheet" href="../forum.css?v={su.FORUM_SURUM}">')
    govde = (su.sayfa_basi('Forum — KPSS Tercihi', 'KPSS adaylarının ilanlar, puanlar, tercih, kurumlar ve mülakatlar hakkında soru sorup deneyim paylaştığı forum.',
                           su.esc(canonical), '../', ek_head=ek)
             + f'<body class="kurum-page forum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html("../", "forum")}'
             + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a><span aria-hidden="true">/</span>'
             + '<span>Forum</span></nav><h1>Forum</h1><p>Sor, cevapla, deneyimini paylaş.</p></div></section>'
             + '<main id="icerik" class="wrap kp-main"><div id="forum" class="fr-kok" aria-live="polite">'
             + '<noscript><p class="muted">Forumu görmek için JavaScript gerekir.</p></noscript></div></main>'
             + f'{su.alt_html("../")}<script src="../forum.js?v={su.FORUM_SURUM}" defer></script></body></html>')
    return canonical, govde
