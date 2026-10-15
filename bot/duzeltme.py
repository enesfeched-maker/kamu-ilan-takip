"""Düzeltme duyurularını orijinal ilana bağlar (15 Ekim 2026 kararı).

- Orijinal ilana 'duzeltmeler' listesi yazılır: sitede ilan sayfasında uyarı kutusu, listede 'Düzeltildi' rozeti.
- Düzeltme yeni bir son başvuru tarihini AÇIKÇA veriyorsa orijinalin son tarihi güncellenir (eskisi 'ilk_son_tarih').
- Düzeltme kaydına 'duzeltme_of' yazılır: ayrı ilan gibi listelenmez, sayfası orijinale kanonik bağlanır.

Eşleştirme ihtiyatlıdır (iptal_yaniti.orijinal_ara): adaylar aynı gerçek ilanın kopyaları değilse hiçbir şey yazılmaz.
Yanlış ilana düzeltme bağlamak, hiç bağlamamaktan kötüdür. Akademik ilanlar ve düzeltmeler hiç işlenmez.
İşlem her taramada baştan uygulanır (kaynaktan gelen alanlar her seferinde yenilenir); sonuç aynıdır."""
import re
from datetime import date, datetime

from ek_kaynaklar import norm
from iptal_yaniti import TR, orijinal_ara, resmi_cumle
from siniflandir import akademik_ilan

ALANLAR = ('duzeltmeler', 'duzeltme_of', 'duzeltme_degisen', 'duzeltme_yeni_tarih')
_TIRNAK = re.compile(r'[“"«]([^”"»]{15,900})[”"»]\s*(?:şeklinde|olarak)', re.I)
_TARIH = re.compile(r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b')


def _bitisik(metin):
    """PDF'ten gelen '202 6', '04/11/202 6' gibi bölünmüş sayıları birleştirir."""
    return re.sub(r'(?<=\d) (?=\d)', '', re.sub(r'(?<=[./]) (?=\d)|(?<=\d) (?=[./])', '', metin))


def duzeltilen_kisim(duyuru):
    """Resmî metinde tırnak içindeki yeni hâl (“…” şeklinde düzeltilmiştir); yoksa ''."""
    cumle = resmi_cumle(duyuru)
    bulunan = _TIRNAK.findall(cumle or '')
    return ' '.join(bulunan[-1].split()) if bulunan else ''


def _tarihler(metin):
    out = []
    for g, a, y in _TARIH.findall(_bitisik(metin)):
        try:
            out.append(date(int(y), int(a), int(g)))
        except ValueError:
            pass
    return out


def degisiklik(duyuru):
    """(tür, yeni son tarih|None): tür 'tarih' (başvuru tarihi değişti), 'basvuru' (başvuru yeri/şekli), 'diger'."""
    kisim = duzeltilen_kisim(duyuru)
    if not kisim:
        return 'diger', None
    n = norm(kisim)
    basvuru = 'basvuru' in n or 'muracaat' in n
    tarihler = _tarihler(kisim)
    if basvuru and tarihler and 'tarih' in n:
        return 'tarih', max(tarihler)
    if basvuru or re.search(r'e posta|eposta|mail|adres|posta|elektronik|sahsen|kargo', n):
        return 'basvuru', None
    return 'diger', None


def _gun(i):
    try:
        z = datetime.fromisoformat(i.get('ilk_gorulme') or '')
    except ValueError:
        return None
    return (z if z.tzinfo else z.replace(tzinfo=TR)).astimezone(TR).date()


def _ayni_ilan(adaylar, kopya_of):
    """Adaylar tek gerçek ilan mı (hepsi aynı kopya grubunda)?"""
    return len({kopya_of.get(a['id'], a['id']) for a in adaylar}) == 1


def uygula(ilanlar, bugun=None, kopya_of=None):
    """ilanlar listesini yerinde günceller; bağlanan düzeltme sayısını döndürür."""
    bugun = bugun or datetime.now(TR).date()
    for i in ilanlar:   # önceki taramanın işaretleri (kaynak yenilemesiyle silinmemiş olanlar) temizlenir
        # Eski son tarih yalnız alan hâlâ bizim yazdığımız değerdeyse geri konur (kaynak bu arada yenisini yazmış olabilir).
        if i.get('ilk_son_tarih') is not None and i.get('son_tarih') == i.get('duzeltilen_son_tarih'):
            i['son_tarih'] = i['ilk_son_tarih']
            if i.get('ilk_son_zaman'):
                i['son_zaman'] = i['ilk_son_zaman']
        for a in ALANLAR + ('ilk_son_tarih', 'ilk_son_zaman', 'duzeltilen_son_tarih'):
            i.pop(a, None)
    if kopya_of is None:
        try:
            import kopya
            kopya_of = kopya.kopya_bul([i for i in ilanlar if not akademik_ilan(i)]).get('kopya_of') or {}
        except Exception:
            kopya_of = {}
    bagli = 0
    duyurular = sorted((i for i in ilanlar if i.get('duyuru_turu') and 'iptal' not in norm(i.get('duyuru_turu'))
                        and not akademik_ilan(i)), key=lambda i: i.get('ilk_gorulme') or '')
    for d in duyurular:
        dgun = _gun(d)

        def ara(ortusme):
            return [a for a in orijinal_ara(d, ilanlar, {}, bugun, mesaj_gerekli=False, ortusme_gerekli=ortusme)
                    if not (dgun and _gun(a) and _gun(a) > dgun)]   # orijinal düzeltmeden önce yayımlanmış olmalı
        # 'DÜZELTME İLANI' gibi başlıkta kadro adı yoksa örtüşme aranamaz: kurumun TEK ilanı varsa o sayılır.
        adaylar = ara(True) or ara(False)
        if not adaylar or not _ayni_ilan(adaylar, kopya_of):
            continue
        tur, yeni = degisiklik(d)
        if yeni and dgun and yeni < dgun:
            tur, yeni = 'basvuru', None   # geçmiş bir tarih yeni son başvuru olamaz
        d['duzeltme_of'] = adaylar[0]['id']
        d['duzeltme_degisen'] = tur
        if yeni:
            d['duzeltme_yeni_tarih'] = yeni.isoformat()
        kayit = {'id': d['id'], 'link': d.get('link', ''), 'tur': tur, 'cumle': _bitisik(duzeltilen_kisim(d))[:400],
                 'tarih': (d.get('ilk_gorulme') or '')[:10]}
        if yeni:
            kayit['yeni_son_tarih'] = yeni.isoformat()
        for a in adaylar:
            a.setdefault('duzeltmeler', []).append(kayit)
            if yeni and a.get('son_tarih') != yeni.isoformat():
                a.setdefault('ilk_son_tarih', a.get('son_tarih') or '')
                a['son_tarih'] = a['duzeltilen_son_tarih'] = yeni.isoformat()
                if a.get('son_zaman') and a['son_zaman'][:10] != yeni.isoformat():
                    a.setdefault('ilk_son_zaman', a.pop('son_zaman'))
        bagli += 1
    return bagli
