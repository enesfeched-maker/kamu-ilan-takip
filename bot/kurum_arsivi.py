"""Kalıcı kurum adresleri (18 Kasım 2026): bir kez sayfası olan kurumun adresi bir daha 404 vermesin.

Kurum sayfası ilanlar.json'daki kayıtlardan üretilir; kayıtlar zamanla silinince açık ilanı ve ÖSYM yerleştirme geçmişi olmayan
kurumun (ör. gazi-universitesi, akdeniz-universitesi, turkiye-is-kurumu) adresi kayboluyor, Search Console'da "bulunamadı" çıkıyordu.
`denetim/kurum-arsivi.json` her sayfası olmuş kurumun adresini ve son ilanlarının ince kaydını saklar; yalnız büyür.
Sayfası başka yoldan üretilmeyen arşiv adresleri için noindex + reklamsız bir sayfa yazılır ("şu an açık ilanı yok" + geçmiş ilanlar);
bu sayfalar site haritasına ve /kurum/ listesine girmez.

Arşiv ilan taramasında (bot/veri_kaydet.py) ilanlar.json ile birlikte commit edilir; site derlemesi yalnız okur ve birleştirir.
Tohum: `python bot/kurum_arsivi.py --tohum` mevcut kayıtlardan ve git geçmişindeki ilanlar.json sürümlerinden arşivi büyütür."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YOL = ROOT / 'denetim' / 'kurum-arsivi.json'
EN_COK_ILAN = 30      # kurum başına saklanan en yeni geçmiş ilan
SURUM = 1
# Elle tohum: sayfası yayında görülmüş ama kaydı artık hiçbir yerde kalmamış kurumlar (Search Console 404 listesi, 18 Kasım 2026).
ELLE_TOHUM = {
    'gazi-universitesi': 'Gazi Üniversitesi',
    'akdeniz-universitesi': 'Akdeniz Üniversitesi',
    'turkiye-is-kurumu': 'Türkiye İş Kurumu',
}


def oku(yol=YOL):
    """{slug: {'ad': str, 'ilanlar': [[anahtar, manşet, son_tarih], …]}}; dosya yoksa ya da bozuksa boş."""
    try:
        return coz(json.loads(Path(yol).read_text(encoding='utf-8')))
    except (OSError, ValueError):
        return {}


def coz(veri):
    """Dosya içeriğinden (dict) arşiv; geçersiz girdiler atlanır."""
    try:
        kurumlar = (veri or {}).get('kurumlar') or {}
        return {s: {'ad': str(k.get('ad') or ''), 'ilanlar': [list(i) for i in k.get('ilanlar') or [] if isinstance(i, list) and len(i) == 3]}
                for s, k in kurumlar.items() if isinstance(k, dict) and re.fullmatch(r'[a-z0-9-]{1,80}', s)}
    except AttributeError:
        return {}


def yaz(arsiv, yol=YOL):
    """Her kurum tek satır (git farkı okunur kalsın); anahtarlar sıralı, çıktı kararlı."""
    satirlar = [f'  {json.dumps(s, ensure_ascii=False)}: {json.dumps(arsiv[s], ensure_ascii=False, separators=(",", ":"))}' for s in sorted(arsiv)]
    metin = '{\n "surum": ' + str(SURUM) + ',\n "kurumlar": {\n' + ',\n'.join(satirlar) + '\n }\n}\n'
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(metin, encoding='utf-8')


def birlestir(*arsivler):
    """Birleşim: hiçbir kurum silinmez; ilanlar anahtara göre tekilleşir, en yeni son tarih önce, kurum başına EN_COK_ILAN."""
    sonuc = {}
    for arsiv in arsivler:
        for slug, k in (arsiv or {}).items():
            hedef = sonuc.setdefault(slug, {'ad': k.get('ad') or '', 'ilanlar': []})
            if k.get('ad') and not hedef['ad']:
                hedef['ad'] = k['ad']
            elif k.get('ad') and arsiv is arsivler[-1]:
                hedef['ad'] = k['ad']   # en yeni kaynak adı günceller
            hedef['ilanlar'] += [list(i) for i in k.get('ilanlar') or []]
    for k in sonuc.values():
        tekil = {}
        for anahtar, manset, son in k['ilanlar']:
            eski = tekil.get(anahtar)
            if eski is None or str(son or '') >= str(eski[2] or ''):
                tekil[anahtar] = [anahtar, manset, son or '']
        k['ilanlar'] = sorted(tekil.values(), key=lambda i: (str(i[2] or ''), i[0]), reverse=True)[:EN_COK_ILAN]
    return sonuc


def gorunen_ad(kan, liste):
    """Sayfada yazan kurum adı (kurum_sayfasi() ile aynı kural: aynı adlı belediyelerde il eklenir)."""
    import kurum_sayfasi as ks
    ad = ks.en_cok_gecen_ad(liste)
    if '|' in kan and kan.split('|')[1] not in ks.kurum_anahtari(ad).split():
        ad += f' ({ks.IL_ADI.get(kan.split("|")[1], kan.split("|")[1])})'
    return ' '.join(ad.split())


def kayitlardan(gruplar, slugler):
    """kurum_gruplari() çıktısından arşiv girdileri: {slug: {'ad', 'ilanlar': [[anahtar, manşet, son_tarih]]}}."""
    import kurum_sayfasi as ks
    sonuc = {}
    for kan, liste in gruplar.items():
        ilanlar = []
        for item in liste:
            try:
                ilanlar.append([ks.anahtar(item), ' '.join(str(ks.kart_alanlari(item)['manset']).split())[:120], str(item.get('son_tarih') or '')[:10]])
            except Exception:
                continue
        sonuc[slugler[kan]] = {'ad': gorunen_ad(kan, liste), 'ilanlar': ilanlar}
    return birlestir(sonuc)


def ilanlardan(ilanlar):
    """Ham ilanlar.json kayıtlarından arşiv girdileri (tarama sonrası ve tohum için)."""
    import kurum_sayfasi as ks
    gruplar, slugler = ks.kurum_gruplari(ilanlar)
    return kayitlardan(gruplar, slugler)


def elle_tohum():
    return {s: {'ad': ad, 'ilanlar': []} for s, ad in ELLE_TOHUM.items()}


def eksik_sayfalar(arsiv, mevcut_sluglar):
    """Sayfası başka yoldan üretilmemiş arşiv kurumları: [(slug, ad, ilanlar)]."""
    return [(s, k['ad'] or s.replace('-', ' ').title(), k['ilanlar']) for s, k in sorted(arsiv.items()) if s not in set(mevcut_sluglar)]


def _tarih(iso):
    try:
        import kurum_sayfasi as ks
        return ks.tarih_yazi(iso) if iso else 'Tarih belirtilmemiş'
    except (ValueError, TypeError):
        return 'Tarih belirtilmemiş'


def arsiv_sayfasi(slug, ad, ilanlar):
    """Açık ilanı ve yerleştirme geçmişi olmayan kurumun kalıcı sayfası: noindex (reklam betiği sayfa_basi'dan kendiliğinden çıkar)."""
    import site_uret as su
    esc = su.esc
    kok = '../../'
    canonical = su.BASE + 'kurum/' + slug + '/'
    baslik = f'{ad} ilanları'
    aciklama = f'{ad}: şu an başvurusu açık ilan yok. Geçmiş ilanları ve kurum listesi.'
    gecmis = ''
    if ilanlar:
        satirlar = ''.join(f'<tr class="kp-row"><td class="kp-baslik">{esc(manset)}</td><td class="kp-tarih"><time>{esc(_tarih(son))}</time></td></tr>'
                           for _, manset, son in ilanlar)
        gecmis = (f'<section class="bolum"><div class="bolum-bas"><h2>Geçmiş ilanlar <span class="sayi">{len(ilanlar)}</span></h2></div>'
                  '<div class="tablo-kap"><table class="kp-tablo"><thead><tr><th scope="col">İlan</th><th scope="col">Son başvuru</th></tr></thead><tbody>'
                  f'{satirlar}</tbody></table></div></section>')
    icerik = (f'<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="{kok}">Ana sayfa</a><span aria-hidden="true">/</span>'
              f'<a href="../">Kurumlar</a><span aria-hidden="true">/</span><span>{esc(ad)}</span></nav>'
              f'<div class="kp-id"><div><span class="eyebrow">Kurum</span><h1>{esc(ad)}</h1></div></div></div></section>'
              '<main id="icerik" class="wrap kp-main"><section class="bolum"><div class="bolum-bas"><h2>Başvurusu açık ilanlar <span class="sayi">0</span></h2></div>'
              '<div class="bos-kutu"><h3>Bu kurumun şu an açık ilanı yok.</h3><p><a href="../">Tüm kurumlar →</a></p></div></section>'
              f'{gecmis}</main>')
    kirinti = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': n, 'name': k_ad, 'item': k_adres}
        for n, (k_ad, k_adres) in enumerate([('Ana sayfa', su.BASE), ('Kurumlar', su.BASE + 'kurum/'), (ad, canonical)], 1)]}
    ek_head = ('<meta name="robots" content="noindex,follow"><script type="application/ld+json">'
               + json.dumps(kirinti, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '</script>')
    return su.sayfa_kabugu(baslik + ' | KPSS Tercihi', aciklama, canonical, icerik, 'kurum-page', baslik, ek_head)


def eksikleri_yaz(docs, arsiv, mevcut_sluglar):
    """Sayfası olmayan arşiv kurumlarını docs/kurum/<slug>/ altına yazar; yazılan sluglar döner."""
    docs = Path(docs)
    yazilan = []
    for slug, ad, ilanlar in eksik_sayfalar(arsiv, mevcut_sluglar):
        klasor = docs / 'kurum' / slug
        try:
            html = arsiv_sayfasi(slug, ad, ilanlar)
            klasor.mkdir(parents=True, exist_ok=True)
            (klasor / 'index.html').write_text(html, encoding='utf-8')
            yazilan.append(slug)
        except Exception as hata:
            print(f'Uyarı: arşiv kurum sayfası yazılamadı ({slug}): {hata}')
    return yazilan


# ------------------------------------------------------------------ tohum (elle, yerelde)
def _git(*args):
    return subprocess.run(['git', '-c', 'safe.directory=*', '-C', str(ROOT), *args], capture_output=True, check=True).stdout


def git_gecmisi_surumleri(yol='docs/ilanlar.json', gunluk=True):
    """Git geçmişindeki ilanlar.json sürümleri (günde en son olan): [(tarih, içerik dict)]."""
    satirlar = _git('log', '--format=%H %cs', '--', yol).decode().split('\n')
    gorulen, sonuc = set(), []
    for s in satirlar:
        if not s.strip():
            continue
        h, gun = s.split()
        if gunluk and gun in gorulen:
            continue
        gorulen.add(gun)
        try:
            sonuc.append((gun, json.loads(_git('show', f'{h}:{yol}').decode('utf-8'))))
        except Exception:
            continue
    return sonuc


def tohumla(yol=YOL):
    """Arşivi mevcut kayıtlar + git geçmişindeki sürümler + elle tohumla büyütür (hiçbir şey silinmez)."""
    arsiv = birlestir(oku(yol))
    for gun, veri in reversed(git_gecmisi_surumleri()):   # eskiden yeniye: en yeni ad kazanır
        arsiv = birlestir(arsiv, ilanlardan(veri.get('ilanlar') or []))
        print(f'{gun}: {len(arsiv)} kurum')
    arsiv = birlestir(elle_tohum(), arsiv)
    yaz(arsiv, yol)
    return arsiv


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if '--tohum' in sys.argv:
        print(f'{len(tohumla())} kurum adresi arşivde.')
    else:
        print(__doc__)
