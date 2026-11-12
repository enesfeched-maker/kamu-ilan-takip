"""Kalıcı meslek sayfaları (docs/meslek/): bir mesleğin başvurusu açık ilanları, süresi geçen ilanları ve KPSS taban puanları.

Neden: ilan sayfası başvuru bitince dizinden çıkar ve biriktirdiği sıralama kaybolur (Search Console, 12 Kasım 2026: en çok
gösterim alan sayfalar zabıta ilanlarıydı). Meslek sayfasının adresi hiç ölmez; ilanlar değişir, sayfa kalır.
Tamamı veriden üretilir: eşleşme unvan metniyle birebirdir, benzerlik ya da tahmin yok."""
import json
import re
from datetime import datetime
from pathlib import Path

import puan_sayfalari as ps
from puan_sayfalari import esc, tam, sayi, donem_yaz, _donem_anahtar, _tablo, _crumbs, _kirinti_json

KLASOR = 'meslek'
GECMIS_N = 30            # sayfada gösterilen en çok süresi geçmiş ilan
MIN_GECMIS = 3           # açık ilanı ve taban puanı olmayan sayfa, en az bu kadar geçmiş ilanla dizine girer
MIN_PUAN_SATIR = 10      # açık ilanı olmayan sayfa, son dönemde en az bu kadar puan satırıyla dizine girer
# (slug, ad, desen): desen, ilan unvanının ' — ' öncesindeki sade (küçük harfli) hâliyle TAM eşleşir.
MESLEKLER = (
    ('zabita-memuru', 'Zabıta Memuru', r'zabıta memuru'),
    ('itfaiye-eri', 'İtfaiye Eri', r'itfaiye eri|itfaiyeci'),
    ('muhendis', 'Mühendis', r'(?:.+ )?mühendisi?'),
    ('tekniker', 'Tekniker', r'(?:.+ )?teknikeri?'),
    ('memur', 'Memur', r'memur'),
    ('destek-personeli', 'Destek Personeli', r'destek personeli?'),
    ('buro-personeli', 'Büro Personeli', r'büro personeli?'),
    ('koruma-ve-guvenlik-gorevlisi', 'Koruma ve Güvenlik Görevlisi', r'koruma ve güvenlik görevlisi'),
    ('hemsire', 'Hemşire', r'hemşire'),
    ('avukat', 'Avukat', r'avukat'),
    ('mimar', 'Mimar', r'mimar'),
    ('psikolog', 'Psikolog', r'psikolog'),
    # 13 Kasım 2026: sitede aranıp açık ilanı bulunamayan, ama geçmiş ilanı ya da taban puanı olan meslekler.
    ('saglik-teknikeri', 'Sağlık Teknikeri', r'sağlık teknikeri'),
    ('veteriner-hekim', 'Veteriner Hekim', r'veteriner(?: hekim)?'),
    ('diyetisyen', 'Diyetisyen', r'diyetisyen'),
    ('ebe', 'Ebe', r'ebe'),
    ('kimyager', 'Kimyager', r'kimyager'),
    ('bilgisayar-isletmeni', 'Bilgisayar İşletmeni', r'bilgisayar işletmeni'),
    ('veri-hazirlama-ve-kontrol-isletmeni', 'Veri Hazırlama ve Kontrol İşletmeni', r'veri hazırlama ve kontrol işletmeni'),
    ('programci', 'Programcı', r'programcı'),
    ('muhasebeci', 'Muhasebeci', r'muhasebeci'),
    ('sekreter', 'Sekreter', r'(?:tıbbi )?sekreter'),
    ('sofor', 'Şoför', r'şoför'),
    ('hizmetli', 'Hizmetli', r'hizmetli'),
)
DIZIN = 'dizin.json'     # [[slug, ad]]: içeriği olan sayfalar; sitede sonuçsuz aramada öneri için (docs/portal.js meslekBul)


def _sade(unvan):
    return ps._kucuk(' '.join(str(unvan or '').split())).split(' — ')[0].strip()


def eslesir(desen, unvan):
    """Unvanın ' — ' öncesi (ör. 'zabıta memuru — erkek' -> 'zabıta memuru') desenle birebir eşleşiyor mu?"""
    return bool(re.fullmatch(desen, _sade(unvan)))


def _uyan(desen, kayitlar):
    return [k for k in kayitlar or [] if any(eslesir(desen, u) for u in (k.get('unvanlar') or []))]


def _tarih(iso):
    import statik_icerik as si
    return si._tarih_yazi(iso)


def tarih_araligi(bas, son):
    """Kısa başvuru aralığı (telefonda tablo hücresine sığsın): '18–20 Kasım 2026', '30 Kasım – 4 Aralık 2026'; yıl farklıysa iki tam tarih."""
    import statik_icerik as si
    if not son:
        return '—'
    if not bas or bas > son:
        return _tarih(son)
    (y1, a1, g1), (y2, a2, g2) = (tuple(int(p) for p in t.split('-')) for t in (bas, son))
    if y1 != y2:
        return f'{_tarih(bas)} – {_tarih(son)}'
    if a1 != a2:
        return f'{g1} {si.AY[a1 - 1]} – {g2} {si.AY[a2 - 1]} {y2}'
    return f'{g1}–{g2} {si.AY[a2 - 1]} {y2}' if g1 != g2 else _tarih(son)


def gecmis_kayitlari(ham, simdi, kopyalar=None):
    """ilanlar.json kayıtlarından son başvurusu geçmiş ilanların ince kayıtları (duyuru, iptal, akademik ve kopyalar hariç)."""
    import kurum_sayfasi as ks
    import liste_verisi
    from siniflandir import akademik_ilan, kucuk
    bugun = simdi.date().isoformat()
    kopya = (kopyalar or {}).get('kopya_of') or {}
    try:
        harita = liste_verisi.il_haritasi(ham)
    except Exception:
        harita = None
    sonuc, gorulen = [], set()
    for item in ham or []:
        try:
            son = str(item.get('son_tarih') or '')[:10]
            if not son or son >= bugun or item.get('duyuru_turu') or item.get('iptal_edildi') or item.get('id') in kopya or akademik_ilan(item):
                continue
            kurum = ks.kurum_adi(item.get('kurum'))
            if (kurum, son) in gorulen:
                continue
            gorulen.add((kurum, son))
            sonuc.append({'key': ks.anahtar(item), 'kurum': kurum, 'son_tarih': son,
                          'il': re.sub(r'\s*\+\d+$', '', liste_verisi.il_bul(item, harita) or ''),
                          'unvanlar': [kucuk(re.sub(r'\s*\(.*?\)', '', ad)).strip() for _, ad in ks.kadrolar(item)]})
        except Exception:
            continue
    return sorted(sonuc, key=lambda k: k['son_tarih'], reverse=True)


def puan_ozetleri(docs, desen):
    """[(düzey slug, düzey adı, son dönem, satırlar)]: son dönemde unvanı desenle eşleşen ÖSYM yerleştirme satırları (puanı olanlar)."""
    sonuc = []
    for slug, ad in ps.DUZEYLER:
        try:
            veri = json.loads((Path(docs) / 'puanlar' / f'{slug}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not veri.get('donemler'):
            continue
        son = max(veri['donemler'], key=_donem_anahtar)
        rows = [r for r in veri['donemler'][son] if isinstance(r.get('min'), (int, float)) and eslesir(desen, r.get('unvan'))]
        if rows:
            sonuc.append((slug, ad, son, rows))
    return sonuc


def sorular(ad, acik, gecmis, puanlar, simdi):
    """Kısa soru-cevaplar: tamamı veriden; bilgi yoksa soru üretilmez."""
    adk = ps._kucuk(ad)
    bugun = _tarih(simdi.date().isoformat())
    sc = []
    if acik:
        kurumlar = list(dict.fromkeys(k.get('kurum') for k in acik if k.get('kurum')))
        ornek = ', '.join(kurumlar[:3]) + (' ve diğerleri' if len(kurumlar) > 3 else '')
        sc.append((f'Şu an açık {adk} alımı var mı?', f'Evet. {bugun} itibarıyla başvurusu açık {tam(len(acik))} {adk} ilanı var: {ornek}.'))
        ilk = min(acik, key=lambda k: k.get('son_tarih') or '9999')
        if ilk.get('son_tarih'):
            sc.append((f'{ad} alımına son başvuru ne zaman?',
                       f'En yakın son başvuru tarihi {_tarih(ilk["son_tarih"])} ({ilk.get("kurum") or "kurum belirtilmemiş"}). Her ilanın tarihi farklıdır.'))
    else:
        cevap = f'{bugun} itibarıyla başvurusu açık {adk} ilanı yok.'
        if gecmis:
            cevap += f' Son ilanın başvurusu {_tarih(gecmis[0]["son_tarih"])} tarihinde bitti ({gecmis[0]["kurum"]}).'
        sc.append((f'Şu an açık {adk} alımı var mı?', cevap))
    for _, dad, son, rows in puanlar:
        sc.append((f'KPSS {ps._kucuk(dad)} {adk} taban puanı kaç?',
                   f'{donem_yaz(son)} merkezi yerleştirmesinde {tam(len(rows))} {adk} kadrosunda en düşük puan {sayi(min(r["min"] for r in rows))}, '
                   f'en yüksek taban puanı {sayi(max(r["min"] for r in rows))} oldu.'))
    return sc


def dizinlenir(acik, gecmis, puanlar):
    return bool(acik) or len(gecmis) >= MIN_GECMIS or sum(len(r) for *_, r in puanlar) >= MIN_PUAN_SATIR


def _sayfa(base, yol, baslik, aciklama, kirinti, icerik, dizin=True):
    import site_uret as su
    kok = '../' * (2 if yol else 1)
    canonical = base + KLASOR + '/' + yol
    ek = (f'<meta property="og:url" content="{esc(canonical)}">' + _kirinti_json(base, kirinti)
          + ('' if dizin else '<meta name="robots" content="noindex,follow">'))
    html = (su.sayfa_basi(baslik + ' | KPSS Tercihi', ps._kes(aciklama), esc(canonical), kok, ek_head=ek)
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok)}{icerik}{su.alt_html(kok)}</body></html>')
    return canonical, html


def _hero(kirinti_html, baslik, giris):
    return (f'<section class="kp-hero"><div class="wrap">{kirinti_html}<span class="eyebrow">Mesleğe göre kamu alımları</span>'
            f'<h1>{esc(baslik)}</h1><p>{esc(giris)}</p></div></section>')


def _bolum(baslik, govde, sayi_=None):
    rozet = f' <span class="sayi">{sayi_}</span>' if sayi_ is not None else ''
    return f'<section class="bolum"><div class="bolum-bas"><h2>{esc(baslik)}{rozet}</h2></div>{govde}</section>'


def meslek_sayfasi(base, slug, ad, acik, gecmis, puanlar, simdi, sayfali=None, docs=None):
    """(canonical, html, dizin). acik: liste kayıtları; gecmis: gecmis_kayitlari; puanlar: puan_ozetleri."""
    kok = '../../'
    adk = ps._kucuk(ad)
    yil = simdi.year
    acik = sorted(acik, key=lambda k: (k.get('son_tarih') or '9999', k.get('kurum') or ''))
    if acik:
        giris = f'{_tarih(simdi.date().isoformat())} itibarıyla başvurusu açık {tam(len(acik))} {adk} ilanı var.'
        ilk = acik[0]
        if ilk.get('son_tarih'):
            giris += f' En yakın son başvuru: {_tarih(ilk["son_tarih"])} ({ilk.get("kurum") or "kurum belirtilmemiş"}).'
    else:
        giris = f'{_tarih(simdi.date().isoformat())} itibarıyla başvurusu açık {adk} ilanı yok.'
        if gecmis:
            giris += f' Son ilanın başvurusu {_tarih(gecmis[0]["son_tarih"])} tarihinde bitti.'
    giris += ' İlanlar resmî kaynaklardan derlenir; yeni ilan çıktığında bu sayfaya eklenir.'
    govde = ''
    if acik:
        satir = []
        for k in acik:
            bas = str(k.get('baslangic_zaman') or '')[:10]
            tarih = tarih_araligi(bas, str(k.get('son_tarih') or '')[:10])
            satir.append([f'<a href="{kok}ilan/{esc(k["key"])}/">{esc(k.get("manset") or "Kamu ilanı")}</a>', esc(k.get('kurum') or '—'),
                          esc(', '.join((k.get('iller') or [])[:3]) or k.get('il') or '—'), esc(tarih)])
        govde += _bolum(f'Başvurusu açık {adk} ilanları', _tablo(['İlan', 'Kurum', 'İl', 'Başvuru'], satir), len(acik))
    sc = sorular(ad, acik, gecmis, puanlar, simdi)
    govde += ps._soru_bolumu(sc)
    if puanlar:
        satir = []
        for dslug, dad, son, rows in puanlar:
            hedef = Path(docs) / ps.KLASOR / dslug / ps._ascii_slug(ad) / 'index.html' if docs else None
            ad_h = f'<a href="{kok}{ps.KLASOR}/{dslug}/{ps._ascii_slug(ad)}/">{esc(dad)}</a>' if hedef and hedef.exists() else esc(dad)
            satir.append([ad_h, esc(donem_yaz(son)), tam(len(rows)), tam(sum(r.get('kontenjan') or 0 for r in rows)),
                          sayi(min(r['min'] for r in rows)), sayi(max(r['min'] for r in rows))])
        govde += _bolum(f'KPSS {adk} taban puanları',
                        _tablo(['Öğrenim düzeyi', 'Dönem', 'Kadro sayısı', 'Kontenjan', 'En düşük taban puanı', 'En yüksek taban puanı'], satir)
                        + f'<p class="kp-note">{esc(ps.NOT)}</p>')
    if gecmis:
        satir = []
        for k in gecmis[:GECMIS_N]:
            kurum = esc(k['kurum'])
            if sayfali is not None and k['key'] in sayfali:
                kurum = f'<a href="{kok}ilan/{esc(k["key"])}/">{kurum}</a>'
            satir.append([kurum, esc(k.get('il') or '—'), esc(_tarih(k['son_tarih']))])
        govde += _bolum(f'Başvurusu biten {adk} ilanları', _tablo(['Kurum', 'İl', 'Son başvuru'], satir), len(gecmis))
    govde += ('<section class="bolum"><p><a href="../">← Tüm meslekler</a> · '
              f'<a href="{kok}">Tüm açık ilanlar</a></p>'
              '<p><a href="https://t.me/kpsstercihi" target="_blank" rel="noopener" data-a="telegram" data-a-x="meslek">'
              f'Yeni {esc(adk)} ilanlarını Telegram kanalında duyuruyoruz →</a></p></section>')
    baslik = f'{ad} Alımı {yil}: Açık İlanlar ve Başvuru Tarihleri'
    aciklama = f'{ad} alımı {yil}: ' + giris.replace(' İlanlar resmî kaynaklardan derlenir; yeni ilan çıktığında bu sayfaya eklenir.', '')
    if puanlar:
        aciklama += ' KPSS taban puanları ve başvurusu biten ilanlar.'
    kir = [('Meslekler', '../'), (ad, None)]
    icerik = _hero(_crumbs(kok, kir), f'{ad} alımı {yil}', giris) + f'<main id="icerik" class="wrap kp-main">{govde}</main>'
    kirinti = [('Ana sayfa', base), ('Meslekler', base + KLASOR + '/'), (ad, f'{base}{KLASOR}/{slug}/')]
    dizin = dizinlenir(acik, gecmis, puanlar)
    canonical, html = _sayfa(base, slug + '/', baslik, aciklama, kirinti, icerik, dizin)
    return canonical, html, dizin


def hub_sayfasi(base, ozetler, simdi):
    """ozetler: [(slug, ad, açık ilan sayısı, geçmiş ilan sayısı)]."""
    kok = '../'
    toplam = sum(o[2] for o in ozetler)
    satirlar = ''.join(f'<li><a href="{esc(s)}/">{esc(ad)} alımı</a> — ' + (f'{tam(a)} açık ilan' if a else 'şu an açık ilan yok') + '</li>' for s, ad, a, _ in ozetler)
    giris = (f'{tam(len(ozetler))} meslek için başvurusu açık kamu ilanları, başvurusu biten ilanlar ve KPSS taban puanları. '
             f'{_tarih(simdi.date().isoformat())} itibarıyla bu mesleklerde {tam(toplam)} açık ilan var.')
    icerik = (_hero(_crumbs(kok, [('Meslekler', None)]), 'Mesleğe göre kamu personel alımları', giris)
              + f'<main id="icerik" class="wrap kp-main">{_bolum("Meslekler", f"<ul>{satirlar}</ul>", len(ozetler))}</main>')
    return _sayfa(base, '', 'Mesleğe Göre Kamu Personel Alımları', giris, [('Ana sayfa', base), ('Meslekler', base + KLASOR + '/')], icerik)


def yaz(docs, base, ilanlar=None, sayfali=None, noindex=None, simdi=None, ham=None, kopyalar=None):
    """docs/meslek/ altını yazar; site haritasına girecek adresleri döndürür. Listedeki her meslek için sayfa HER ZAMAN üretilir
    (adres 404 vermesin); içeriği zayıf olan `noindex` alır ve haritaya girmez.
    ilanlar: liste.json kayıtları (kopyalar hariç); ham: ilanlar.json kayıtları (başvurusu biten ilanlar için)."""
    import statik_icerik as si
    docs = Path(docs)
    if not base.endswith('/'):
        base += '/'
    simdi = simdi or datetime.now(si.TR)
    adaylar = []
    if ilanlar:
        adaylar = si.sec(ilanlar, {k.get('key') for k in ilanlar} if sayfali is None else sayfali, noindex or set(), simdi, en_cok=len(ilanlar))
    gecmis_tum = gecmis_kayitlari(ham, simdi, kopyalar) if ham else []
    adresler, ozetler, dolu = [], [], []
    for slug, ad, desen in MESLEKLER:
        acik, gecmis, puanlar = _uyan(desen, adaylar), _uyan(desen, gecmis_tum), puan_ozetleri(docs, desen)
        url, html, dizin = meslek_sayfasi(base, slug, ad, acik, gecmis, puanlar, simdi, sayfali, docs)
        hedef = docs / KLASOR / slug / 'index.html'
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(html, encoding='utf-8')
        ozetler.append((slug, ad, len(acik), len(gecmis)))
        if acik or gecmis or puanlar:          # boş sayfa aramada önerilmez
            dolu.append([slug, ad])
        if dizin:
            adresler.append(url)
            ps._degisim_yaz(url, acik)
    url, html = hub_sayfasi(base, ozetler, simdi)
    (docs / KLASOR / 'index.html').write_text(html, encoding='utf-8')
    (docs / KLASOR / DIZIN).write_text(json.dumps(dolu, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return [url] + adresler
