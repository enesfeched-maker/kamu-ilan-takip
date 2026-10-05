"""SBB ilan belgesinin TAM metninden (kısaltılmış özet/şartlar değil) türetilen alanlar.

Saf işlev modülü: ağ yok. `alanlar()` yalnız güvenle bulunanları döndürür; güvenilmez bir tablo/ifade varsa o alan hiç
yazılmaz (mevcut değer korunur, hiçbir şey kötüleşmez). Alanlar:
  yer            belgenin açılış cümlesindeki il ("Ardahan ili Hanak Belediye Başkanlığı bünyesinde")
  kadro          "N MEMUR ALACAK" genel başlığı yerine, tablo satırlarının toplamı N ise gerçek unvanlar
  ilan_turu      belge başlığı "SÖZLEŞMELİ PERSONEL ALIM İLANI" iken başlıktan türeyen 'Memur' yerine 'Sözleşmeli Personel'
  puan_turleri   tablo satırlarından (yoksa metinden) KPSS puan türleri
  belge_ogrenim  tablo satırlarının niteliklerinden (tablo yoksa tüm metinden) öğrenim düzeyleri
  belge_kpss     'kpsssiz': belge "KPSS şartı aranmamaktadır" diyor ve puan türü yok"""
import re

SURUM = 1
GENEL_KADRO = re.compile(r'\s*(\d+)\s+(?:MEMUR|SÖZLEŞMELİ PERSONEL|PERSONEL|İŞÇİ)\s+ALACAK\s*', re.I)
KPSS_PUAN = re.compile(r'\bKPSS\s*\(?[AB]?\)?\s*P\s?(\d{1,3})\b|\bP(\d{1,3})\s*puan', re.I)


def _temiz(plain_pages):
    import iskur_detay
    return iskur_detay._temizle(' '.join(plain_pages))


def _il(plain):
    from siniflandir import ILLER, kucuk
    for m in re.finditer(r'(?<!\S)(\S+)\s+ili\s+(?:\S+\s+){0,3}?Belediye', plain[:600]):
        ad = kucuk(m.group(1).strip('.,;:()'))
        for il in ILLER:
            if kucuk(il) == ad:
                return il
    return ''


def _is_kurumu_ili(plain):
    """TTK gibi işçi alımları: 'Bartın İş Kurumu aracılığı ile … Bartın ilinde ikamet ediyor olmak' (kurum adından çıkarılamayan il)."""
    from siniflandir import ILLER, kucuk
    for desen in (r'(?<!\S)(\S+)\s+İş Kurumu\s+aracılığı', r'(?<!\S)(\S+)\s+ilinde ikamet'):
        m = re.search(desen, plain)
        if m:
            ad = kucuk(m.group(1))
            for il in ILLER:
                if kucuk(il) == ad:
                    return il
    return ''


ESKI_CUMLE = re.compile(r'mezun|öğrenim|yıllık|fakülte|program|kpss', re.I)
ELE_CUMLE = re.compile(r'denklik|belge|transkript|sertifika|fotokopi|vb\.|bilgisi|kayıt', re.I)


def _ogrenim_cumleleri(plain):
    """Tablosuz belgede yalnız şart cümleleri (mezuniyet/öğrenim/KPSS geçen, belge-listesi olmayan) taranır;
    'ortaöğretim, ön lisans, lisans … bilgisi' gibi belge sayımları düzey sayılmaz."""
    cumleler = re.split(r'(?<=[.;:])\s+', plain)
    return ' '.join(c for c in cumleler if ESKI_CUMLE.search(c) and not ELE_CUMLE.search(c) and len(c) < 700)


def _siralama(duzeyler):
    from liste_verisi import SEVIYE_SIRASI
    return [d for d in SEVIYE_SIRASI if d in duzeyler]


def alanlar(plain_pages, row):
    from siniflandir import ogrenim_seviyeleri, KPSSSIZ, kucuk
    import iskur_detay
    plain = _temiz(plain_pages)
    if len(plain) < 200:
        return {}
    sonuc = {}
    il = _il(plain) or _is_kurumu_ili(plain)
    if il and not row.get('yer'):
        sonuc['yer'] = il
    baslik = kucuk(plain[:400])
    if 'sözleşmeli personel alım' in baslik and row.get('ilan_turu') in (None, '', 'Memur', 'Kamu Personeli'):
        sonuc['ilan_turu'] = 'Sözleşmeli Personel'
    try:
        satirlar = iskur_detay._satirlar(plain)
    except Exception:
        satirlar = []
    pt = set()
    if satirlar:
        g = GENEL_KADRO.fullmatch(str(row.get('kadro') or ''))
        if g and sum(s['adet'] for s in satirlar) == int(g.group(1)):
            sonuc['kadro'] = iskur_detay._kadro(satirlar)
        ogr = set()
        for s in satirlar:
            if s['pt']:
                pt.add(s['pt'])
            ogr.update(ogrenim_seviyeleri({'ozet': f"{s.get('nitelik', '')} KPSS {s['pt'] or ''}"}))
        ogr = _siralama(ogr)
    else:
        for a, b in KPSS_PUAN.findall(plain):
            pt.add('P' + (a or b))
        ogr = ogrenim_seviyeleri({'ozet': _ogrenim_cumleleri(plain)})
    if pt:
        sonuc['puan_turleri'] = sorted(pt, key=lambda s: int(s[1:]))
    if ogr:
        sonuc['belge_ogrenim'] = ogr
    if not pt and KPSSSIZ.search(kucuk(plain)):
        sonuc['belge_kpss'] = 'kpsssiz'
    return sonuc
