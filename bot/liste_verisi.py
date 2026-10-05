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
SEVIYE_SIRASI = ('lisans', 'onlisans', 'ortaogretim')
# Öğrenim çıkarımı (derleme zamanı): metinde düzey yazmayan ilanlar "tüm düzeylere uygun" sayılmasın.
KPSS_LISANS = re.compile(r'kpss[- ]?\(?lisans\)?|lisans düzeyi kpss|kpss b grubu p3|kpss a grubu')
LISANS_UNVAN = re.compile(
    r'uzman yardımcı|müfettiş yardımcı|denetçi yardımcı|murakıp yardımcı|kontrolör yardımcı|aktüer yardımcı'
    r'|stajyer avukat|(?<!\w)avukat|hukuk sınıfı|muvazzaf subay|meslek personeli'
    r'|bilişim personeli|yazılım geliştirme|(?<!\w)mühendis|(?<!\w)mimar(?!\w)')
# İli kurum adında yazmayan, bilinen kurumlar (kurum_anahtari biçimiyle içerir-eşleşme)
KURUM_IL = (
    ('tarsus universitesi', 'Mersin'), ('turkiye taskomuru kurumu', 'Zonguldak'),
    ('bankacilik duzenleme ve denetleme kurumu', 'İstanbul'), ('bddk', 'İstanbul'),
    ('sigortacilik ve ozel emeklilik duzenleme ve denetleme kurumu', 'İstanbul'), ('seddk', 'İstanbul'),
)
OZET_IL_PARANTEZ = re.compile(r'\(([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\)')
OZET_IL_GOREV = re.compile(r'(\w+?)(?:da|de|ta|te) görev yapmak üzere')


AYLAR = ('ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık')
DONEM_RE = re.compile(r'(\d{1,2})\s+(' + '|'.join(AYLAR) + r')\s*[-–]\s*(\d{1,2})\s+(' + '|'.join(AYLAR) + r')')
KURUM_ICI_BASLIK = re.compile(r'yeterlik sınavı|görevde yükselme|unvan değişikliği')


def donem_tarihleri(donem, referans):
    """SBB 'donem' metni ('( 5 Ekim - 20 Ekim)') -> (başlangıç, bitiş) date çifti; çözülemezse None.
    Yıl referans tarihin (ilk görülme) yılıdır; bitiş ayı başlangıçtan önceyse ya da dönem referanstan çok önce
    bitiyorsa (yıl dönümü) bir yıl ilerletilir."""
    from siniflandir import kucuk
    m = DONEM_RE.search(kucuk(donem))
    ref = referans.date() if isinstance(referans, datetime) else referans
    if not m or not ref:
        return None
    g1, a1, g2, a2 = int(m.group(1)), AYLAR.index(m.group(2)) + 1, int(m.group(3)), AYLAR.index(m.group(4)) + 1
    try:
        for kaydir in (0, 1):
            bas = date(ref.year + kaydir, a1, g1)
            son = date(ref.year + kaydir + (a2 < a1), a2, g2)
            if son >= ref - timedelta(days=60):
                return bas, son
    except ValueError:
        pass
    return None


def pencere_tamamla(item):
    """İŞKUR/SBB kaydında saklı başvuru notundaki (SBB'de özetteki de) belge penceresi son_tarih/son_zaman/baslangic_zaman'dan
    farklıysa belge kazanır; düzeltilmiş KOPYA döner (kayıt değişmez), pencere yoksa aynı nesne. Toplayıcı yeni kayıtlarda
    aynı düzeltmeyi kendisi yazar; bu, henüz yeniden okunmamış kayıtlar için derleme zamanı yedeğidir."""
    if item.get('kaynak_turu') not in ('iskur', 'sbb') or item.get('duyuru_turu') or item.get('iptal_edildi'):
        return item
    from basvuru_penceresi import uygula
    metinler = [item.get('basvuru_notu')] + ([item.get('ozet')] if item.get('kaynak_turu') == 'sbb' else [])
    ref = _tr_tarih(item.get('ilk_gorulme')) or datetime.now(TR).date()
    return uygula(item, [m for m in metinler if m], ref)


def donem_tamamla(item):
    """son_tarih'i olmayan SBB kaydı için dönemden son_tarih/baslangic_zaman türetilmiş KOPYA döndürür (kayıt değişmez);
    türetilemiyorsa aynı nesne. Önce belge penceresi (pencere_tamamla) uygulanır.
    Derleme zamanı yedeği; toplayıcı yeni kayıtlarda aynı alanları kendisi yazar."""
    item = pencere_tamamla(item)
    if item.get('son_tarih') or item.get('kaynak_turu') != 'sbb' or not item.get('donem'):
        return item
    try:
        t = donem_tarihleri(item['donem'], datetime.fromisoformat(item.get('ilk_gorulme') or '').astimezone(TR))
    except ValueError:
        return item
    if not t:
        return item
    yeni = dict(item, son_tarih=t[1].isoformat())
    if not item.get('baslangic_zaman'):
        yeni['baslangic_zaman'] = datetime.combine(t[0], datetime.min.time(), TR).isoformat()
    return yeni


def tamamla(item):
    """Derleme zamanı düzeltmeleri (kayıt değişmez, KOPYA döner): belge penceresi ve SBB dönem yedeği."""
    return donem_tamamla(item)


def puan_duzeyi(p):
    """KPSS puan türü -> öğrenim düzeyi: P94 ortaöğretim, P93 önlisans, P1–P48 lisans (A grubu dahil); diğeri None."""
    if p == 'P94':
        return 'ortaogretim'
    if p == 'P93':
        return 'onlisans'
    try:
        return 'lisans' if 1 <= int(p[1:]) <= 48 else None
    except ValueError:
        return None


def ogrenim_cikar(item, ogr, pt):
    """(düzeyler, çıkarım_yapıldı, kurum_içi). Sırayla: yeterlik sınavı -> kurum içi; puan türü -> düzey; açık 'KPSS lisans'
    ifadesi; yalnız lisans gerektiren unvanlar (başlık/kadro/tür kısa metni). Sonuç metinden gelen düzeylerle birleşir, hiçbiri silinmez."""
    from siniflandir import kucuk, _tum_metin, _kisa_metin, fakulte_sartli
    if KURUM_ICI_BASLIK.search(kucuk(f"{item.get('baslik') or ''} {item.get('ilan_turu') or ''}")):
        return list(ogr), False, True
    ek = {d for d in (puan_duzeyi(p) for p in pt) if d}
    if KPSS_LISANS.search(_tum_metin(item)) or LISANS_UNVAN.search(_kisa_metin(item)) or fakulte_sartli(item):
        ek.add('lisans')
    sonuc = [d for d in SEVIYE_SIRASI if d in ogr or d in ek]
    return sonuc, bool(ek - set(ogr)), False


def _il_gecerli(il):
    ks = _ks()
    return ks.kurum_anahtari(re.sub(r'\s*\+\d+$', '', il or '')) in ks.IL_ADI


def il_cikar(item):
    """İli açıkça yazılmayan ilan için il tahmini ('' = bulunamadı): kurum adındaki tek il sözcüğü, bilinen kurum haritası,
    özetteki '(İstanbul)' ya da 'İstanbul’da görev yapmak üzere'. Birden çok farklı il bulunursa belirsiz sayılır."""
    ks = _ks()
    from siniflandir import kucuk
    kurum = ks.kurum_anahtari(item.get('kurum') or '')
    bulunan = {ks.IL_ADI[t] for t in kurum.split() if t in ks.IL_ADI}
    if len(bulunan) == 1:
        return next(iter(bulunan))
    if bulunan:
        return ''
    for anahtar, il in KURUM_IL:
        if re.search(r'\b' + anahtar + r'\b', kurum):
            return il
    ozet = str(item.get('ozet') or '')
    bulunan = {ks.IL_ADI[a] for a in (ks.kurum_anahtari(p) for p in OZET_IL_PARANTEZ.findall(ozet)) if a in ks.IL_ADI}
    bulunan |= {ks.IL_ADI[a] for a in (ks.kurum_anahtari(p) for p in OZET_IL_GOREV.findall(kucuk(ozet))) if a in ks.IL_ADI}
    return next(iter(bulunan)) if len(bulunan) == 1 else ''


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
    s = re.sub(r'\s+(?:alacak|alınacak|temin edecektir)\s*[.,;:]*\s*$', '', s, flags=re.I)
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
    il = ks.yer_kisa(item)
    if _il_gecerli(il) or ks.kurum_anahtari(il).startswith('turkiye geneli'):
        return il
    return il_cikar(item) or il


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
    item = donem_tamamla(item)
    metin, cls = ks.durum(item, simdi)
    if cls not in ACIK or item.get('duyuru_turu') or item.get('iptal_edildi'):
        return None
    a = ks.kart_alanlari(item)
    key = ks.anahtar(item)
    g = gorsel or {}
    ogr = [o for o in (item.get('ogrenim') or []) if o in ks.LEVELS]
    pt = puan_turleri(item)
    ogr, cikarim, kurum_ici = ogrenim_cikar(item, ogr, pt)
    adlar = [ad for _, ad in ks.kadrolar(item)]
    from siniflandir import kucuk, bolum_kisitli
    unvanlar = list(dict.fromkeys(kucuk(re.sub(r'\s*\(.*?\)', '', ad)).strip() for ad in adlar))  # puanlar sayfası tam eşleşme için
    ref = {}  # öğrenim düzeyine göre {'lisans': {...}}; tarayıcı profil düzeyine göre okur
    for duzey in ogr:
        r = taban_ref(tablolar, duzey, adlar)
        if r:
            ref[duzey] = {k: v for k, v in r.items() if k != 'duzey'}
    il = il_bul(item, harita)
    iller = item.get('iller') or []
    if not iller and _il_gecerli(il) and il == il_cikar(item):
        iller = [il]   # kurum adı/özetten çıkarılan il, tarayıcıda ve ayrıntı sayfasında iller gibi kullanılır
    kay = {
        'key': key, 'id': item.get('id') if item.get('id') != key else None,
        'manset': baslik_temiz(a['manset']), 'ek': a.get('ek', 0), 'toplam': a.get('toplam'),
        'meslek': a.get('meslek') or [], 'logo': g.get('logo'),
        'kurum': ks.kurum_adi(item.get('kurum')), 'kurum_slug': g.get('kurum_slug') or ks.kurum_slug(item.get('kurum')),
        'il': il, 'iller': iller,
        'unvanlar': unvanlar, 'ogrenim': ogr, 'ilan_turu': (item.get('ilan_turu') or '')[:60], 'kategori': item.get('kategori'), 'kpss': item.get('kpss'), 'puan_turleri': pt, 'taban_ref': ref or None,
        'ogrenim_cikarim': cikarim, 'kurum_ici': kurum_ici, 'bolum_kisiti': bolum_kisitli(item),
        'son_tarih': item.get('son_tarih'), 'son_zaman': item.get('son_zaman'),
        'baslangic_zaman': item.get('baslangic_zaman'), 'ilk_gorulme': item.get('ilk_gorulme'), 'durum': cls,
    }
    return {k: v for k, v in kay.items() if v not in (None, '', 0) or k in ('ek', 'ogrenim', 'iller', 'meslek', 'puan_turleri', 'unvanlar')}


def _etkin_iller(k):
    return k.get('iller') or ([re.sub(r'\s*\+\d+$', '', k['il'])] if k.get('il') and _il_gecerli(k['il']) else [])


def grup_birlestir(birincil, ikincil):
    """Kopya grubunda birincil satırın öğrenim, puan türü, il ve taban referansı bilgisi ikincillerle birleştirilir
    (birincil metinde düzey yazmıyor ama aynı ilanın başka kaynaktaki kaydı yazıyor olabilir); hiçbir değer silinmez."""
    uyeler = [birincil, *ikincil]
    ogr = [d for d in SEVIYE_SIRASI if any(d in (u.get('ogrenim') or []) for u in uyeler)]
    if ogr != (birincil.get('ogrenim') or []):
        if not (birincil.get('ogrenim') or []):
            birincil['ogrenim_cikarim'] = True
        birincil['ogrenim'] = ogr
    pt = sorted({p for u in uyeler for p in (u.get('puan_turleri') or [])}, key=lambda s: int(s[1:]))
    birincil['puan_turleri'] = pt
    ilk_iller = _etkin_iller(birincil)
    iller = list(dict.fromkeys(il for u in uyeler for il in _etkin_iller(u)))
    if iller != ilk_iller and (not ilk_iller or all(il in iller for il in ilk_iller)):
        birincil['iller'] = iller
        if not _il_gecerli(birincil.get('il')):
            birincil['il'] = iller[0] if len(iller) == 1 else f'{iller[0]} +{len(iller) - 1}'
    ref = dict(birincil.get('taban_ref') or {})
    for u in ikincil:
        for d, r in (u.get('taban_ref') or {}).items():
            ref.setdefault(d, r)
    ref = {d: r for d, r in ref.items() if d in ogr}
    if ref:
        birincil['taban_ref'] = ref
    elif 'taban_ref' in birincil:
        del birincil['taban_ref']


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
    gruplar = {}
    for ikincil, birincil in (kopyalar.get('kopya_of') or {}).items():
        if ikincil in kayit_id and birincil in kayit_id:
            gruplar.setdefault(birincil, []).append(kayit_id[ikincil][0])
    for birincil, ikinciller in gruplar.items():
        grup_birlestir(kayit_id[birincil][0], ikinciller)
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
