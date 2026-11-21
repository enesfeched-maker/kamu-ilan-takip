"""İlan sayfalarında "İlgili sayfalar" bağlantı satırı (18 Kasım 2026, SEO ikinci aşama).

İlan sayfası başvuru bitince dizinden çıkar; sıralamayı taşıyan kalıcı sayfalar (meslek, il, kurum, taban puanı kadro sayfası) ise
yaşar. Bu modül ilan sayfasından o sayfalara tek, kısa bağlantı satırı koyar. Yalnız ilan sayfaları yazıldıktan SONRA, site haritasının
son hâli belli olunca çalışır: bağlantı yalnız bu derlemede var olan ve dizinlenen (haritadaki) sayfalara verilir; ince/noindex
sayfalara iç bağlantı yoktur. Eşleşmeler birebirdir (meslek unvan deseni, il adı, kurum adresi, taban puanı unvanı), tahmin yok."""
from pathlib import Path

ISARET = 'ilgili-sayfalar'
EN_COK_MESLEK = 2
EN_COK_IL = 2


def baglantilar(item, kayit, gorsel, docs, base, haritada, yil):
    """[(göreli adres, bağlantı metni)] — sırası: meslek, il, kurum, taban puanı. `haritada`: dizinlenen sayfaların tam adresleri."""
    import ilan_taban
    import kurum_sayfasi as ks
    import meslek_sayfalari as ms
    import puan_sayfalari as ps
    sonuc = []

    def ekle(yol, metin):
        if base + yol in haritada and all(h != '../../' + yol for h, _ in sonuc):
            sonuc.append(('../../' + yol, metin))
    unvanlar = (kayit or {}).get('unvanlar') or []
    eslesen = [(slug, ad) for slug, ad, desen in ms.MESLEKLER if any(ms.eslesir(desen, u) for u in unvanlar)]
    for slug, ad in [m for m in eslesen if base + f'{ms.KLASOR}/{m[0]}/' in haritada][:EN_COK_MESLEK]:
        ekle(f'{ms.KLASOR}/{slug}/', f'{ad} alımı {yil}' + (': yaş sınırı ve KPSS puanı' if slug in ms.GENEL_SORULAR else ''))
    import il_sayfalari as ils
    iller = [(kayit or {}).get('il') or ''] + list((kayit or {}).get('iller') or [])
    gorulen = []
    for ham in iller:
        il = ils.il_adi(ham)
        if il and il not in gorulen and base + f'{ils.KLASOR}/{ils.il_slug(il)}/' in haritada:
            gorulen.append(il)
    for il in gorulen[:EN_COK_IL]:
        ekle(f'{ils.KLASOR}/{ils.il_slug(il)}/', f'{il} kamu ilanları')
    slug = (gorsel or {}).get('kurum_slug')
    if slug and (item.get('kurum') or '').strip():
        ekle(f'kurum/{slug}/', f'{ks.kurum_adi(item["kurum"])} ilanları')
    try:
        for duzey, unvan, _donemler, kadro_slug in ilan_taban.eslesmeler(item, docs):
            if kadro_slug and base + f'{ps.KLASOR}/{duzey}/{kadro_slug}/' in haritada:
                ekle(f'{ps.KLASOR}/{duzey}/{kadro_slug}/', f'{ps._duzgun(unvan)} taban puanları ({ilan_taban.DUZEY_ADI[duzey]})')
                break
    except Exception as hata:
        print(f'Uyarı: ilgili taban puanı sayfası bulunamadı ({item.get("id")}): {hata}')
    return sonuc


def satir_html(baglanti_listesi):
    """Mevcut bağlantı biçimiyle (yazi-link) tek satır; bağlantı yoksa ''."""
    if not baglanti_listesi:
        return ''
    from site_uret import esc
    govde = ' <span aria-hidden="true">·</span> '.join(f'<a class="yazi-link" href="{esc(h)}">{esc(m)}</a>' for h, m in baglanti_listesi)
    return f'<section class="d-bolum {ISARET}" aria-label="İlgili sayfalar"><h2>İlgili sayfalar</h2><p>{govde}</p></section>'


def yerlestir(html, satir):
    """Satırı 'Benzer ilanlar'ın önüne, o yoksa ana içeriğin sonuna ekler; zaten varsa ya da yer bulunamazsa dokunmaz."""
    if not satir or ISARET in html:
        return html
    for isaret in ('<section class="benzer">', '</div></main>'):
        i = html.rfind(isaret)
        if i >= 0:
            return html[:i] + satir + html[i:]
    return html


def uygula(docs, base, haritada, bilgiler, simdi):
    """bilgiler: {ilan anahtarı: (item, kayit, gorsel)}. Yazılan sayfa sayısı döner."""
    docs = Path(docs)
    yazilan = 0
    for anahtar, (item, kayit, gorsel) in bilgiler.items():
        dosya = docs / 'ilan' / anahtar / 'index.html'
        if not dosya.is_file():
            continue
        try:
            html = dosya.read_text(encoding='utf-8')
            yeni = yerlestir(html, satir_html(baglantilar(item, kayit, gorsel, docs, base, haritada, simdi.year)))
            if yeni != html:
                dosya.write_text(yeni, encoding='utf-8')
                yazilan += 1
        except Exception as hata:
            print(f'Uyarı: ilgili sayfalar eklenemedi ({anahtar}): {hata}')
    return yazilan
