"""Ana sayfa için derleme zamanı ince liste verisi: docs/liste.json.

Tarayıcı 700 KB'lık ilanlar.json'u indirmeden "Bugün" akışını çizebilsin diye her açık ilan için
satır kartında gereken alanlar (il, puan türleri, taban puanı referansı, durum…) burada hesaplanır.
Saf fonksiyonlar: ağ ve disk yalnız `taban_tablolari` (docs/puanlar okuma) ve `uret` (yazma) içinde."""
import json
import re
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
ACIK = ('ok', 'soon', 'urgent', 'today', 'none', 'upcoming')
EN_AZ_KAYIT = 5          # taban referansı için aynı unvanda en az bu kadar yerleşme
TAKVIM_GUN = 45
PUAN_RE = re.compile(r'\bKPSS\s*P\s?(\d{1,3})\b|\bP(\d{1,3})\s*puan', re.I)


def _ks():
    import kurum_sayfasi
    return kurum_sayfasi


def baslik_temiz(s):
    """Satır başlığı: 'İlk Defa Atanmak Üzere … Alımı İlanı' -> '… alımı', 'Vhki' -> 'VHKİ'."""
    s = str(s or '')
    s = re.sub(r'^İlk Defa Atanmak Üzere\s+', '', s)
    s = re.sub(r'\s+Alım(?:ı)?\s+İlanı$', ' alımı', s)
    s = re.sub(r'\s+Sınav(?:ı)?\s+(?:İlanı|Duyurusu)$', ' sınavı', s)
    s = re.sub(r'\s+İlanı$', '', s)
    s = s.replace('Vhki', 'VHKİ').replace('.net', '.NET')
    return s[:1].upper() + s[1:]


def il_haritasi(ilanlar):
    """{belediye kanonik adı: il adı} — ili addan/kayıttan bilinen kayıtlardan; aynı belediyenin ili belirsiz
    kayıtları (örn. 'HANAK BELEDİYE BAŞKANLIĞI' <- 'Ardahan Hanak Belediyesi') bununla çözülür."""
    ks = _ks()
    harita = {}
    for item in ilanlar:
        kan = ks.kurum_kanonik(item.get('kurum'))
        if not kan.endswith(' belediye') or kan in harita:
            continue
        il = ks._ilan_ili(item)
        if il:
            harita[kan] = ks.IL_ADI.get(il, il)
    return harita


def il_bul(item, harita=None):
    """Görünen il: tek il -> 'Ankara'; çoklu -> 'Ankara +2'; belediyede addan/kayıttan/haritadan il;
    parantezli il ('Subaşı (Yalova)'); yoksa yer_kisa (bilinmiyorsa '' — tarayıcı bunu ülke geneli sayar)."""
    ks = _ks()
    iller = item.get('iller') or []
    if iller:
        return iller[0] if len(iller) == 1 else f'{iller[0]} +{len(iller) - 1}'
    il = ks._ilan_ili(item)
    if il:
        return ks.IL_ADI.get(il, il)
    for p in re.findall(r'\(([^)]+)\)', item.get('kurum') or ''):
        a = ks.kurum_anahtari(p)
        if a in ks.IL_ADI:
            return ks.IL_ADI[a]
    if harita:
        il = harita.get(ks.kurum_kanonik(item.get('kurum')))
        if il:
            return il
    return ks.yer_kisa(item)


def puan_turleri(item):
    """İlan metninde geçen KPSS puan türleri (['P3', 'P93']); yoksa []."""
    metin = json.dumps([item.get('ozet'), item.get('sartlar'), item.get('kadro')], ensure_ascii=False)
    return sorted({'P' + (a or b) for a, b in PUAN_RE.findall(metin)}, key=lambda s: int(s[1:]))


def taban_tablolari(docs):
    """{düzey: ({unvan: (medyan, n)}, 'dönem1/dönem2')} — son iki dönemde en az EN_AZ_KAYIT yerleşme olan unvanlar."""
    from siniflandir import kucuk
    sonuc = {}
    for duzey in ('lisans', 'onlisans', 'ortaogretim'):
        try:
            d = json.loads((Path(docs) / 'puanlar' / f'{duzey}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        donemler = sorted(d.get('donemler', {}))[-2:]
        toplam = {}
        for dn in donemler:
            for r in d['donemler'][dn]:
                if r.get('min') and r.get('unvan'):
                    toplam.setdefault(kucuk(r['unvan']), []).append(r['min'])
        sonuc[duzey] = ({u: (round(statistics.median(v), 1), len(v)) for u, v in toplam.items() if len(v) >= EN_AZ_KAYIT}, '/'.join(donemler))
    return sonuc


def taban_ref(tablolar, duzey, kadro_adlari):
    """İlk eşleşen unvan için {'duzey','unvan','medyan','n','donem'}; eşleşme yoksa None.
    n: o unvanın son iki dönemdeki taban puanı kayıt sayısı (kadro satırı; yerleşen kişi sayısı değil), en az EN_AZ_KAYIT."""
    from siniflandir import kucuk
    tablo, donem = tablolar.get(duzey, ({}, ''))
    for ad in kadro_adlari:
        k = kucuk(re.sub(r'\s*\(.*?\)', '', ad)).strip()
        if k in tablo and tablo[k][1] >= EN_AZ_KAYIT:
            return {'duzey': duzey, 'unvan': k, 'medyan': tablo[k][0], 'n': tablo[k][1], 'donem': donem}
    return None


def _tr_tarih(iso):
    try:
        return datetime.fromisoformat(iso).astimezone(TR).date()
    except (TypeError, ValueError):
        return None


def kayit(item, gorsel, tablolar, simdi, harita=None):
    """Tek ilanın ince kaydı (None: listede gösterilmeyecek durumda)."""
    ks = _ks()
    metin, cls = ks.durum(item, simdi)
    if cls not in ACIK or item.get('duyuru_turu') or item.get('iptal_edildi'):
        return None
    a = ks.kart_alanlari(item)
    key = ks.anahtar(item)
    g = gorsel or {}
    ogr = [o for o in (item.get('ogrenim') or []) if o in ks.LEVELS]
    adlar = [ad for _, ad in ks.kadrolar(item)]
    from siniflandir import kucuk
    unvanlar = list(dict.fromkeys(kucuk(re.sub(r'\s*\(.*?\)', '', ad)).strip() for ad in adlar))  # puanlar sayfası tam eşleşme için
    ref = {}  # öğrenim düzeyine göre {'lisans': {...}}; tarayıcı profil düzeyine göre okur
    for duzey in ogr:
        r = taban_ref(tablolar, duzey, adlar)
        if r:
            ref[duzey] = {k: v for k, v in r.items() if k != 'duzey'}
    kay = {
        'key': key, 'id': item.get('id') if item.get('id') != key else None,
        'manset': baslik_temiz(a['manset']), 'ek': a.get('ek', 0), 'toplam': a.get('toplam'),
        'meslek': a.get('meslek') or [], 'logo': g.get('logo'),
        'kurum': ks.kurum_adi(item.get('kurum')), 'kurum_slug': g.get('kurum_slug') or ks.kurum_slug(item.get('kurum')),
        'il': il_bul(item, harita), 'iller': item.get('iller') or [],
        'unvanlar': unvanlar, 'ogrenim': ogr, 'ilan_turu': (item.get('ilan_turu') or '')[:60], 'kategori': item.get('kategori'), 'kpss': item.get('kpss'), 'puan_turleri': puan_turleri(item), 'taban_ref': ref or None,
        'son_tarih': item.get('son_tarih'), 'son_zaman': item.get('son_zaman'),
        'baslangic_zaman': item.get('baslangic_zaman'), 'ilk_gorulme': item.get('ilk_gorulme'), 'durum': cls,
    }
    return {k: v for k, v in kay.items() if v not in (None, '', 0) or k in ('ek', 'ogrenim', 'iller', 'meslek', 'puan_turleri', 'unvanlar')}


def takvim(kayitlar, simdi, gun=TAKVIM_GUN):
    """{'2026-10-06': adet} — önümüzdeki `gun` gün içinde son başvurusu olan ilan sayısı."""
    bugun = simdi.astimezone(TR).date()
    son = bugun + timedelta(days=gun)
    sonuc = {}
    for k in kayitlar:
        try:
            d = date.fromisoformat(k.get('son_tarih') or '')
        except ValueError:
            continue
        if bugun <= d <= son:
            sonuc[d.isoformat()] = sonuc.get(d.isoformat(), 0) + 1
    return dict(sorted(sonuc.items()))


KAYNAK_GORUNEN = {'sbb': 'SBB', 'csb': 'ÇŞB Yerel Yönetimler'}   # portal.js ile aynı; diğerleri İŞKUR


def eski_detay(item, simdi):
    """portal.js stale(): ayrıntı kontrolü yok ya da 24 saatten eski."""
    s = item.get('detay_guncelleme')
    if not s:
        return True
    try:
        return (simdi - datetime.fromisoformat(s)).total_seconds() > 86400
    except (TypeError, ValueError):
        return False


def uyari_uret(kaynak_durumlari, acik_ilanlar, simdi):
    """Bugün sayfasındaki tek satırlık uyarı: {'kaynaklar': ['SBB'], 'eski_detay': 12}; ikisi de yoksa {}.
    kaynaklar: son taramada hata_sayisi > 0 olan kaynaklar; eski_detay: gösterilen açık ilanlardan ayrıntısı 24 saatten eski olanların sayısı."""
    kaynaklar = []
    for k, s in (kaynak_durumlari or {}).items():
        if isinstance(s, dict) and (s.get('hata_sayisi') or 0) > 0:
            ad = KAYNAK_GORUNEN.get(k, 'İŞKUR')
            if ad not in kaynaklar:
                kaynaklar.append(ad)
    eski = sum(1 for i in acik_ilanlar if eski_detay(i, simdi))
    sonuc = {}
    if kaynaklar:
        sonuc['kaynaklar'] = kaynaklar
    if eski:
        sonuc['eski_detay'] = eski
    return sonuc


def liste_uret(ilanlar, gorseller, docs, simdi=None, guncelleme=None, kopyalar=None, kaynak_durumlari=None):
    """docs/liste.json içeriği. Kaynaklar arası kopya ilanların ikincil satırlarına `kopya_of` (birincil anahtar),
    birincil satıra `kaynak_sayisi`/`kaynaklar` yazılır; sayılar ve takvim yalnız görünen (birincil) satırlardan hesaplanır."""
    from siniflandir import akademik_ilan
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    tablolar = taban_tablolari(docs)
    harita = il_haritasi(ilanlar)
    if kopyalar is None:
        try:
            import kopya
            kopyalar = kopya.kopya_bul(ilanlar)
        except Exception as hata:
            print(f'Uyarı: kopya ilanlar bulunamadı: {hata}')
            kopyalar = {}
    kayitlar, kayit_id = [], {}
    for item in ilanlar:
        try:
            if akademik_ilan(item):
                continue
            k = kayit(item, (gorseller or {}).get(_ks().anahtar(item)), tablolar, simdi, harita)
        except Exception as hata:
            print(f'Uyarı: liste kaydı üretilemedi ({item.get("id")}): {hata}')
            continue
        if k:
            kayitlar.append(k)
            kayit_id[item.get('id')] = (k, item)
    for ikincil, birincil in (kopyalar.get('kopya_of') or {}).items():
        if ikincil in kayit_id and birincil in kayit_id:   # birincil satırı yoksa ikincil de tek başına görünür
            kayit_id[ikincil][0]['kopya_of'] = kayit_id[birincil][0]['key']
    try:
        import kopya
        for birincil, uyeler in (kopyalar.get('uyeler') or {}).items():
            if birincil in kayit_id:
                adlar = kopya.kaynak_adlari(uyeler)
                if len(adlar) > 1:
                    kayit_id[birincil][0]['kaynak_sayisi'] = len(adlar)
                    kayit_id[birincil][0]['kaynaklar'] = adlar
    except Exception as hata:
        print(f'Uyarı: kaynak adları yazılamadı: {hata}')
    gorunen = [k for k in kayitlar if not k.get('kopya_of')]
    bugun_yeni = sum(1 for k in gorunen if _tr_tarih(k.get('ilk_gorulme')) == simdi.date())
    gorunen_ilanlar = [i for k, i in kayit_id.values() if not k.get('kopya_of')]
    return {
        'guncelleme': guncelleme or simdi.isoformat(timespec='seconds'),
        'sayilar': {'acik': len(gorunen), 'kadro': sum(k.get('toplam') or 0 for k in gorunen), 'bugun_yeni': bugun_yeni},
        'uyari': uyari_uret(kaynak_durumlari, gorunen_ilanlar, simdi),
        'takvim': takvim(gorunen, simdi),
        'ilanlar': kayitlar,
    }


def uret(ilanlar, gorseller, docs, simdi=None, guncelleme=None, kopyalar=None, kaynak_durumlari=None):
    veri = liste_uret(ilanlar, gorseller, docs, simdi, guncelleme, kopyalar, kaynak_durumlari)
    (Path(docs) / 'liste.json').write_text(json.dumps(veri, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return veri
