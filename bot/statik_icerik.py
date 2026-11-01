"""JavaScript kapalıyken de içerik: ana sayfa (docs/index.html) ve tercih robotu (docs/puanlar/index.html) derleme sırasında
gerçek ilan satırları ve puan tablosuyla doldurulur (AdSense 'düşük değerli içerik' incelemesi, 1 Kasım 2026).

Tarayıcıda portal.js / puanlar.js aynı alanları yeniden çizer (replaceChildren / textContent), yani bu içerik yalnız JS'siz
okuyucu ve tarayıcılar içindir. İşlem idempotenttir; işaret bulunamazsa dosyaya dokunulmaz."""
import html
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
LEVELS = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim'}
EN_COK_SATIR = 30
PUAN_SATIR = 50

CARDS_BAS = '<div class="zaman" id="cards">'
CARDS_SON = '</div><div class="bos-kutu" id="empty"'


def esc(v):
    return html.escape(str(v if v is not None else ''), quote=True)


def tam(n):
    return f'{int(n):,}'.replace(',', '.')


def _tarih_yazi(iso):
    d = date.fromisoformat(str(iso)[:10])
    return f'{d.day} {AY[d.month - 1]} {d.year}'


def _harf(kurum):
    kelimeler = [w for w in str(kurum or '').split() if re.match(r'[A-Za-zÇĞİIÖŞÜçğıöşü]', w)]
    return ''.join(w[0] for w in kelimeler[:2]).upper() or 'K'


def uygun_ilanlar(gorunen):
    """Ana listede sayılan açık ilanlar: kopya, akademik ve kurum içi olmayanlar."""
    return [k for k in gorunen if not k.get('kopya_of') and not k.get('kurum_ici') and k.get('kategori') != 'akademik']


def sec(gorunen, sayfali, noindex, simdi, en_cok=EN_COK_SATIR):
    """Satır olacak ilanlar: son başvurusu belli ve geçmemiş, sayfası var, dizinlenir; en yakın son tarih önce."""
    bugun = simdi.astimezone(TR).date().isoformat()
    adaylar = [k for k in uygun_ilanlar(gorunen)
               if k.get('key') in sayfali and k.get('key') not in noindex and (k.get('son_tarih') or '') >= bugun]
    adaylar.sort(key=lambda k: (k['son_tarih'], str(k.get('kurum') or ''), str(k.get('key'))))
    return adaylar[:en_cok]


def ozet_cumlesi(gorunen):
    """'N açık ilan · M kadro · K kurum' (hesaplanır; kadro toplamı bilinmiyorsa yazılmaz)."""
    uygun = uygun_ilanlar(gorunen)
    if not uygun:
        return ''
    kadro = sum(int(k.get('toplam') or 0) for k in uygun)
    kurum = len({k.get('kurum_slug') or k.get('kurum') for k in uygun if k.get('kurum_slug') or k.get('kurum')})
    parcalar = [f'{tam(len(uygun))} açık ilan']
    if kadro:
        parcalar.append(f'{tam(kadro)} kadro')
    if kurum:
        parcalar.append(f'{tam(kurum)} kurum')
    return ' · '.join(parcalar)


def satir_html(k):
    """portal.js satirEl() ile aynı sınıflar; kurum adı düz metin, başlık gerçek ilan bağlantısıdır."""
    kurum = k.get('kurum') or 'Kurum belirtilmemiş'
    alt = [k.get('il'), ' / '.join(LEVELS[o] for o in (k.get('ogrenim') or []) if o in LEVELS),
           (f'{tam(k["toplam"])} kadro' if k.get('toplam') and not re.match(r'\d', str(k.get('manset') or '')) else '')]
    alt = ' · '.join(a for a in alt if a)
    hue = sum(ord(c) for c in str(kurum)) % 360
    return (f'<li><article class="satir"><span class="satir-logo"><span class="harf" style="--h:{hue}" aria-hidden="true">{esc(_harf(kurum))}</span></span>'
            f'<div class="satir-govde"><p class="satir-kurum">{esc(kurum)}</p>'
            f'<h3 class="satir-baslik"><a class="satir-link" href="ilan/{esc(k["key"])}/">{esc(k.get("manset") or "Kamu ilanı")}</a> '
            f'<span class="satir-tarih">(Son başvuru: {esc(_tarih_yazi(k["son_tarih"]))})</span></h3>'
            + (f'<p class="satir-alt">{esc(alt)}</p>' if alt else '') + '</div><div class="satir-sag"></div></article></li>')


def anasayfa_html(metin, satirlar, toplam_cumle, uygun_sayi):
    """Ana sayfa HTML'ini doldurur. İşaretlerden biri bulunamazsa None (dosya değişmez)."""
    bas = metin.find(CARDS_BAS)
    if bas < 0:
        return None
    son = metin.find(CARDS_SON, bas)
    if son < 0:
        return None
    if satirlar:
        not_ = ''
        if uygun_sayi > len(satirlar):
            not_ = f'<p class="liste-ozet">Son başvuru tarihi en yakın {tam(len(satirlar))} ilan gösteriliyor.</p>'
        icerik = '<section class="zg"><ul class="gun-liste">' + ''.join(satir_html(k) for k in satirlar) + '</ul></section>' + not_
    else:
        icerik = ''
    yeni = metin[:bas + len(CARDS_BAS)] + icerik + metin[son:]
    sayac = re.compile(r'(<small id="result-count"[^>]*>)[^<]*(</small>)')
    ozet = re.compile(r'(<p class="liste-ozet" id="filter-summary">)[^<]*(</p>)')
    manset = re.compile(r'(<p class="manset-bos">)[^<]*(</p>)')
    if not (sayac.search(yeni) and ozet.search(yeni) and manset.search(yeni)):
        return None
    yeni = sayac.sub(lambda m: m.group(1) + (f'{tam(uygun_sayi)} ilan' if uygun_sayi else '') + m.group(2), yeni, count=1)
    yeni = ozet.sub(lambda m: m.group(1) + esc(toplam_cumle) + m.group(2), yeni, count=1)
    yeni = manset.sub(lambda m: m.group(1) + (f'Başvurusu açık {tam(uygun_sayi)} kamu ilanı aşağıda listeleniyor.' if uygun_sayi else 'İlanlar yükleniyor…') + m.group(2), yeni, count=1)
    return yeni


def _puan(p):
    return '—' if p is None else f'{p:.5f}'.replace('.', ',')


def puan_satiri(donem, r):
    yer = ' · '.join(x for x in (r.get('il'), r.get('teskilat')) if x)
    kurum = f'{esc(r.get("kurum"))}' + (f'<small>{esc(yer)}</small>' if yer else '')
    return (f'<tr><td>{esc(str(donem).replace("-", "/"))}</td><td>{kurum}</td><td>{esc(r.get("unvan"))}</td>'
            f'<td class="sayi">{esc(r.get("kontenjan"))}</td><td class="sayi">{esc(r.get("yerlesen"))}</td>'
            f'<td class="sayi">{_puan(r.get("min"))}</td><td class="sayi">{_puan(r.get("max"))}</td></tr>')


def puan_secimi(veri, en_cok=PUAN_SATIR):
    """(son dönem, o dönemin ilk en_cok satırı en küçük puan yüksekten, dönemdeki satır sayısı); veri yoksa None."""
    donemler = (veri or {}).get('donemler') or {}
    if not donemler:
        return None
    son = max(donemler, key=lambda d: tuple(int(x or 0) for x in str(d).split('-')))
    satirlar = donemler[son]
    if not satirlar:
        return None
    sirali = sorted(satirlar, key=lambda r: -(r['min'] if isinstance(r.get('min'), (int, float)) else -1))
    return son, sirali[:en_cok], len(satirlar)


def puan_html(metin, secim):
    """Tercih robotu sayfasının tablo gövdesini ve /analiz/ bağlantısını doldurur; işaret yoksa None."""
    govde = re.compile(r'(<tbody id="satirlar">).*?(</tbody>)', re.S)
    ozet = re.compile(r'(<span class="sayi" id="tablo-ozet">)[^<]*(</span>)')
    giris = re.compile(r'(<section class="puan-intro"><h1>[^<]*</h1>)(?:<p class="statik-baglanti">.*?</p>)?(</section>)', re.S)
    if not (govde.search(metin) and ozet.search(metin) and giris.search(metin)) or not secim:
        return None
    donem, satirlar, toplam = secim
    yeni = govde.sub(lambda m: m.group(1) + ''.join(puan_satiri(donem, r) for r in satirlar) + m.group(2), metin, count=1)
    yeni = ozet.sub(lambda m: m.group(1) + f'{esc(donem.replace("-", "/"))} dönemi: {tam(toplam)} kadro' + m.group(2), yeni, count=1)
    baglanti = '<p class="statik-baglanti"><a href="../analiz/">Puan verilerinden analizler: değişim, il il karşılaştırma, kadro sıralaması →</a></p>'
    return giris.sub(lambda m: m.group(1) + baglanti + m.group(2), yeni, count=1)


def _oku(yol):
    return yol.read_text(encoding='utf-8')


def _yaz(yol, eski, yeni):
    if yeni is None:
        print(f'Uyarı: {yol.name} için statik içerik işareti bulunamadı; dosya değiştirilmedi.')
        return False
    if yeni != eski:
        yol.write_text(yeni, encoding='utf-8')
    return True


def yaz(docs, gorunen, sayfali, noindex, simdi=None):
    """docs/index.html ve docs/puanlar/index.html dosyalarını doldurur; başarısız olanı atlar, hata yükseltmez."""
    docs = Path(docs)
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    sonuc = []
    ana = docs / 'index.html'
    try:
        eski = _oku(ana)
        uygun = uygun_ilanlar(gorunen)
        sonuc.append(_yaz(ana, eski, anasayfa_html(eski, sec(gorunen, sayfali, noindex, simdi), ozet_cumlesi(gorunen), len(uygun))))
    except Exception as hata:
        print(f'Uyarı: ana sayfa statik içeriği yazılamadı: {hata}')
    puan = docs / 'puanlar' / 'index.html'
    try:
        eski = _oku(puan)
        veri = json.loads(_oku(docs / 'puanlar' / 'lisans.json'))
        sonuc.append(_yaz(puan, eski, puan_html(eski, puan_secimi(veri))))
    except Exception as hata:
        print(f'Uyarı: puanlar sayfası statik içeriği yazılamadı: {hata}')
    return sonuc
