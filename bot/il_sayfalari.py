"""İl sayfaları (docs/il/): her il için başvurusu açık ilanlar ve ÖSYM KPSS merkezi yerleştirme geçmişi.

İlan sayfaları son başvuru geçince arama dizininden çıkar; il sayfası kalıcıdır ve her derlemede yeniden hesaplanır
(AdSense 'düşük değerli içerik', 10 Kasım 2026). Metin şablonu yoktur: her cümle ve tablo docs/puanlar/*.json ile açık
ilan listesinden hesaplanır; verisi az olan il sayfası açık kalır ama dizine ve reklama girmez (IL_MIN_SATIR)."""
import shutil
from datetime import datetime
from pathlib import Path

import analiz_sayfalari as an
import puan_sayfalari as ps
from puan_sayfalari import esc, sayi, tam, donem_yaz, _crumbs, _tablo, _kirinti_json, _donem_anahtar

KLASOR = 'il'
SON_DONEM_SAYISI = 4      # kurum tablosu ve dizin eşiği son bu kadar dönemi kapsar
IL_MIN_SATIR = 20         # son dönemlerde bundan az kadro satırı olan il sayfası dizine girmez
KADRO_N = 15              # düzey başına gösterilen en düşük puanlı kadro
KURUM_N = 10
ACIK_N = 30
KAYNAK = 'Kaynak: ÖSYM KPSS merkezi yerleştirme sayısal bilgileri ve KPSS Tercihi\'nin derlediği ilanlar.'


def _ks():
    import kurum_sayfasi
    return kurum_sayfasi


def il_adi(ham):
    """'AFYONKARAHİSAR' -> 'Afyonkarahisar'; 81 ilden biri değilse None."""
    ks = _ks()
    return ks.IL_ADI.get(ks.kurum_anahtari(str(ham or '')))


def il_slug(il):
    return _ks()._ascii_slug(il)


def il_verisi(veriler):
    """veriler: {düzey: (ad, json)} -> {il: {düzey: {dönem: [satır]}}}; ili tanınmayan satır atlanır."""
    sonuc = {}
    for duzey, (_, veri) in veriler.items():
        for donem, satirlar in (veri.get('donemler') or {}).items():
            for r in satirlar:
                il = il_adi(r.get('il'))
                if il:
                    sonuc.setdefault(il, {}).setdefault(duzey, {}).setdefault(donem, []).append(r)
    return sonuc


def son_donemler(veriler, n=SON_DONEM_SAYISI):
    """Tüm düzeylerde görülen dönemlerin son n tanesi (eski -> yeni)."""
    hepsi = {d for _, veri in veriler.values() for d, rows in (veri.get('donemler') or {}).items() if rows}
    return sorted(hepsi, key=_donem_anahtar)[-n:]


def _secili_satirlar(il_duzeyleri, secili):
    return [r for donemler in il_duzeyleri.values() for d in secili for r in donemler.get(d, [])]


def il_dizinlenir(il_duzeyleri, secili):
    return len(_secili_satirlar(il_duzeyleri, secili)) >= IL_MIN_SATIR


def acik_ilanlar(il, ilanlar, sayfali=None, noindex=None, simdi=None, en_cok=ACIK_N):
    """İli açıkça `il` olan, başvurusu açık ilanlar (en yakın son tarih önce). Ülke geneli ilanlar girmez: il tahmin edilmez.
    Dışlamalar ana sayfadaki statik listeyle aynıdır (statik_icerik.sec)."""
    if not ilanlar:
        return []
    import statik_icerik as si
    if sayfali is None:
        sayfali = {k.get('key') for k in ilanlar}
    adaylar = si.sec(ilanlar, sayfali, noindex or set(), simdi or datetime.now(si.TR), en_cok=len(ilanlar))
    return [k for k in adaylar if il in (k.get('iller') or [])][:en_cok]


def acik_satirlari(liste, kok):
    """Açık ilan satırları (<ul>); liste boşsa boş metin."""
    if not liste:
        return ''
    import statik_icerik as si
    return '<ul>' + ''.join(
        f'<li><a href="{kok}ilan/{esc(k["key"])}/">{esc(k.get("manset") or "Kamu ilanı")}</a>'
        f' <span class="muted">· {esc(k.get("kurum") or "Kurum belirtilmemiş")} · Son başvuru: {esc(si._tarih_yazi(k["son_tarih"]))}</span></li>'
        for k in liste) + '</ul>'


def kurum_ozetleri(satirlar, en_cok=KURUM_N):
    """En çok kontenjanlı kurumlar: [{ham, kurum, kontenjan, satir, med}] (ham: slug için ÖSYM'deki yazım)."""
    ks = _ks()
    gruplar = {}
    for r in satirlar:
        if r.get('kurum'):
            gruplar.setdefault(ks.kurum_kanonik(r['kurum']), []).append(r)
    sonuc = [{'ham': rows[0]['kurum'], 'kurum': ps._kurum(rows[0]['kurum']), 'kontenjan': sum(r.get('kontenjan') or 0 for r in rows),
              'satir': len(rows), 'med': an.medyan(rows)} for rows in gruplar.values()]
    sonuc = [o for o in sonuc if o['kontenjan'] > 0]
    return sorted(sonuc, key=lambda o: (-o['kontenjan'], ps._kucuk(o['kurum'])))[:en_cok]


def bulgular(il, il_duzeyleri, veriler, secili):
    """Hesaplanmış kısa tespitler: düzey başına ilin son puanlı dönemi, önceki dönemle farkı ve aynı dönemin Türkiye geneli medyanı;
    son dönemlerde en çok kontenjan açan kurum."""
    sonuc = []
    for duzey, (ad, veri) in veriler.items():
        donemler = il_duzeyleri.get(duzey)
        if not donemler:
            continue
        oz = [o for o in an.donem_ozetleri(donemler) if o['med'] is not None]
        if not oz:
            continue
        son = oz[-1]
        cumle = an.degisim_cumlesi(oz, ad) or f'{ad}: {donem_yaz(son["donem"])} döneminde en küçük puanların medyanı {sayi(son["med"])}.'
        genel = an.medyan(veri['donemler'].get(son['donem']) or [])
        if genel is not None:
            cumle += f' Aynı dönemde Türkiye geneli medyanı {sayi(genel)}.'
        sonuc.append(cumle)
    kurumlar = kurum_ozetleri(_secili_satirlar(il_duzeyleri, secili), 1)
    if kurumlar and secili:
        sonuc.append(f'{an.donem_araligi(secili)} dönemlerinde {il} için en çok kontenjan açan kurum {kurumlar[0]["kurum"]} ({tam(kurumlar[0]["kontenjan"])} kontenjan).')
    return sonuc


def _toplam(il_duzeyleri):
    satirlar = [r for donemler in il_duzeyleri.values() for rows in donemler.values() for r in rows]
    donemler = sorted({d for dz in il_duzeyleri.values() for d, rows in dz.items() if rows}, key=_donem_anahtar)
    return len(satirlar), sum(r.get('kontenjan') or 0 for r in satirlar), donemler


def _sayfa(base, yol, baslik, aciklama, kirinti, icerik, dizin=True):
    import site_uret as su
    kok = '../' * (2 if yol else 1)
    canonical = base + KLASOR + '/' + yol
    ek = (f'<meta property="og:url" content="{esc(canonical)}">' + _kirinti_json(base, kirinti)
          + ('' if dizin else '<meta name="robots" content="noindex,follow">'))
    html = (su.sayfa_basi(baslik + ' | KPSS Tercihi', aciklama, esc(canonical), kok, ek_head=ek)
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok)}{icerik}{su.alt_html(kok)}</body></html>')
    return canonical, html


def _hero(kirinti_html, baslik, giris):
    return (f'<section class="kp-hero"><div class="wrap">{kirinti_html}<span class="eyebrow">İl il kamu alımları</span>'
            f'<h1>{esc(baslik)}</h1><p>{esc(giris)}</p></div></section>')


def _bolum(baslik, govde, sayi_=None):
    rozet = f' <span class="sayi">{sayi_}</span>' if sayi_ is not None else ''
    return f'<section class="bolum"><div class="bolum-bas"><h2>{esc(baslik)}{rozet}</h2></div>{govde}</section>'


def il_sayfasi(base, il, il_duzeyleri, veriler, secili, acik, guncelleme, kadro_slug=None, kurum_var=None):
    """kadro_slug(düzey, unvan) -> slug|None (taban puanı sayfası varsa); kurum_var(slug) -> bool. (canonical, html)."""
    kok = '../../'
    ks = _ks()
    satir_n, kontenjan, donemler = _toplam(il_duzeyleri)
    giris = (f'ÖSYM\'nin KPSS merkezi yerleştirme sonuçlarında {il} için {donem_yaz(donemler[0])}–{donem_yaz(donemler[-1])} dönemlerinde '
             f'{tam(satir_n)} kadro satırı ve {tam(kontenjan)} kontenjan yer aldı.')
    if acik:
        giris += f' Şu an ili {il} olan başvurusu açık {tam(len(acik))} ilan var.'
    tespitler = bulgular(il, il_duzeyleri, veriler, secili)
    bolumler = ''
    if acik:
        bolumler += _bolum('Başvurusu açık ilanlar', acik_satirlari(acik, kok), len(acik))
    else:
        bolumler += _bolum('Başvurusu açık ilanlar', f'<p>Şu an ili {esc(il)} olarak belirtilmiş açık ilan yok. <a href="{kok}#ilanlar">Tüm açık ilanlar →</a></p>')
    if tespitler:
        bolumler += _bolum('Öne çıkanlar', '<ul>' + ''.join(f'<li>{esc(c)}</li>' for c in tespitler) + '</ul>')
    for duzey, (ad, _) in veriler.items():
        dz = il_duzeyleri.get(duzey)
        if not dz:
            continue
        oz = an.donem_ozetleri(dz)
        bolumler += _bolum(f'{ad}: dönem dönem', _tablo(
            ['Dönem', 'Kadro satırı', 'Kontenjan', 'Yerleşen', 'Medyan en küçük puan', 'En düşük puan'],
            [[esc(donem_yaz(o['donem'])), tam(o['satir']), tam(o['kontenjan']), tam(o['yerlesen']), ps._p(o['med']), ps._p(o['en_dusuk'])] for o in reversed(oz)]))
        son = oz[-1]['donem']
        puanli = sorted((r for r in dz[son] if isinstance(r.get('min'), (int, float))), key=lambda r: (r['min'], str(r.get('kurum')), str(r.get('unvan'))))
        if puanli:
            def unvan_html(r, duzey=duzey):
                u = ' '.join(str(r.get('unvan') or '').split())
                ad_ = esc(ps.baslik_hali(u)) if u else '—'
                s = kadro_slug(duzey, u) if kadro_slug and u else None
                return f'<a href="{kok}{ps.KLASOR}/{duzey}/{esc(s)}/">{ad_}</a>' if s else ad_
            tablo = _tablo(['Kadro (unvan)', 'Kurum', 'Teşkilat', 'Kontenjan', 'En küçük puan'],
                           [[unvan_html(r), esc(ps._kurum(r.get('kurum'))), esc(ps._duzgun(r.get('teskilat'))), tam(r.get('kontenjan') or 0), ps._p(r['min'])]
                            for r in puanli[:KADRO_N]])
            notu = (f'<p class="kp-note">{esc(donem_yaz(son))} döneminde puanı belli {tam(len(puanli))} kadrodan en düşük puanlı {KADRO_N} tanesi gösteriliyor.</p>'
                    if len(puanli) > KADRO_N else '')
            bolumler += _bolum(f'{ad}: {donem_yaz(son)} döneminde en düşük puanlı kadrolar', tablo + notu)
    kurumlar = kurum_ozetleri(_secili_satirlar(il_duzeyleri, secili))
    if kurumlar:
        def kurum_html(o):
            s = ks.kurum_slug(o['ham'])
            return f'<a href="{kok}kurum/{esc(s)}/">{esc(o["kurum"])}</a>' if kurum_var and kurum_var(s) else esc(o['kurum'])
        bolumler += _bolum(f'En çok kontenjan açan kurumlar ({an.donem_araligi(secili)})', _tablo(
            ['Kurum', 'Kontenjan', 'Kadro satırı', 'Medyan en küçük puan'],
            [[kurum_html(o), tam(o['kontenjan']), tam(o['satir']), ps._p(o['med'])] for o in kurumlar]))
    bolumler += (f'<section class="bolum"><p><a href="../">← Tüm iller</a> · <a href="{kok}analiz/il-il-taban-puanlari/">İl il taban puanı karşılaştırması</a>'
                 f' · <a href="{kok}puanlar/">Puanını gir, tercih robotunu dene →</a></p></section>')
    alt = f'<p class="kp-note">{esc(KAYNAK)} Hazırlayan: KPSS Tercihi Editörlüğü. Güncelleme: {esc(guncelleme)}</p>'
    baslik = f'{il} Kamu İlanları ve KPSS Taban Puanları'
    aciklama = f'{il} kamu personel alımları: ' + (f'{tam(len(acik))} açık ilan, ' if acik else '')
    aciklama += f'{donem_yaz(donemler[0])}–{donem_yaz(donemler[-1])} KPSS yerleştirmelerinde {tam(kontenjan)} kontenjan'
    lisans = [o for o in an.donem_ozetleri(il_duzeyleri.get('lisans') or {}) if o['med'] is not None]
    if lisans:
        aciklama += f'; {donem_yaz(lisans[-1]["donem"])} lisans medyan en küçük puanı {sayi(lisans[-1]["med"])}'
    aciklama += '.'
    slug = il_slug(il)
    icerik = (_hero(_crumbs(kok, [('İller', '../'), (il, None)]), baslik, giris)
              + f'<main id="icerik" class="wrap kp-main">{bolumler}{alt}</main>')
    kirinti = [('Ana sayfa', base), ('İller', base + KLASOR + '/'), (il, f'{base}{KLASOR}/{slug}/')]
    return _sayfa(base, slug + '/', baslik, aciklama, kirinti, icerik, dizin=il_dizinlenir(il_duzeyleri, secili))


def hub_sayfasi(base, iller, veriler, secili, acik_sayilari, guncelleme):
    """iller: {il: {düzey: {dönem: [satır]}}}."""
    kok = '../'
    aralik = an.donem_araligi(secili)
    satirlar = []
    for il in sorted(iller, key=lambda i: _ks()._tr_sira(i)):
        secili_satir = _secili_satirlar(iller[il], secili)
        lisans = [r for d in secili for r in (iller[il].get('lisans') or {}).get(d, [])]
        satirlar.append([f'<a href="{esc(il_slug(il))}/">{esc(il)}</a>', tam(acik_sayilari.get(il, 0)), tam(len(secili_satir)),
                         tam(sum(r.get('kontenjan') or 0 for r in secili_satir)), ps._p(an.medyan(lisans))])
    baslik = 'İllere Göre Kamu İlanları ve KPSS Taban Puanları'
    giris = (f'{tam(len(iller))} il için başvurusu açık kamu ilanları ile ÖSYM KPSS merkezi yerleştirme sonuçlarındaki kadro, kontenjan ve en küçük puanlar. '
             f'Tablodaki sayılar {aralik} dönemlerini kapsar.')
    aciklama = f'{tam(len(iller))} ilin kamu personel alımları: açık ilanlar, KPSS ile açılan kontenjanlar ve lisans medyan en küçük puanları ({aralik}).'
    tablo = _tablo(['İl', 'Açık ilan', 'Kadro satırı', 'Kontenjan', 'Lisans medyan en küçük puan'], satirlar)
    icerik = (_hero(_crumbs(kok, [('İller', None)]), baslik, giris)
              + f'<main id="icerik" class="wrap kp-main">{_bolum("İller", tablo, len(iller))}'
              f'<p class="kp-note">Açık ilan sütunu yalnız ili belirtilmiş ilanları sayar; ülke geneli alımlar ana sayfadadır. Medyan, o ildeki lisans kadrolarına yerleşenlerin en küçük puanlarının ortanca değeridir.</p>'
              f'<p class="kp-note">{esc(KAYNAK)} Hazırlayan: KPSS Tercihi Editörlüğü. Güncelleme: {esc(guncelleme)}</p></main>')
    return _sayfa(base, '', baslik, aciklama, [('Ana sayfa', base), ('İller', base + KLASOR + '/')], icerik)


def yaz(docs, base, ilanlar=None, sayfali=None, noindex=None, simdi=None):
    """docs/il/ altını baştan yazar; site haritasına girecek adresleri döndürür. `ilanlar`: liste.json kayıtları (kopyasız)."""
    docs = Path(docs)
    simdi = (simdi or datetime.now(an.TR)).astimezone(an.TR)
    if not base.endswith('/'):
        base += '/'
    shutil.rmtree(docs / KLASOR, ignore_errors=True)
    veriler = an._veriler(docs)
    iller = il_verisi(veriler)
    if not iller:
        return []
    secili = son_donemler(veriler)
    sluglar = an._slug_haritasi(veriler)
    guncelleme = an._tarih_yazi(simdi.date())

    def kadro_slug(duzey, unvan):
        s = (sluglar.get(duzey) or {}).get(unvan)
        return s if s and (docs / ps.KLASOR / duzey / s / 'index.html').is_file() else None

    kurum_var = lambda s: (docs / 'kurum' / s / 'index.html').is_file()
    adresler, acik_sayilari = [], {}
    for il, dz in iller.items():
        acik = acik_ilanlar(il, ilanlar or [], sayfali, noindex, simdi)
        acik_sayilari[il] = len(acik)
        url, html = il_sayfasi(base, il, dz, veriler, secili, acik, guncelleme, kadro_slug, kurum_var)
        hedef = docs / KLASOR / il_slug(il) / 'index.html'
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(html, encoding='utf-8')
        if il_dizinlenir(dz, secili):
            adresler.append(url)
            if _ks().son_ilan_gunu(acik):
                _ks().SON_DEGISIM[url] = _ks().son_ilan_gunu(acik)   # sayfadaki açık ilan listesinin son değiştiği gün
    url, html = hub_sayfasi(base, iller, veriler, secili, acik_sayilari, guncelleme)
    (docs / KLASOR / 'index.html').write_text(html, encoding='utf-8')
    return [url] + sorted(adresler)
