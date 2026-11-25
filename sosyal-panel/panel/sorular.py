"""İnsanlar ne soruyor: asistan kayıtlarından ihtiyaç çıkarımı.

Soru metinleri Türkçe katlanır (ı→i, ş→s ...), dolgu sözcükleri atılır ve basit ek kırpmayla köke indirilir.
Aynı köklere inen sorular tek soru sayılır ("zabıta ilanı var mı?" ~ "Zabita ilani varmi"); listede en sık
yazılan asıl biçim gösterilir. Gün sınırları Türkiye saatine göredir."""
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone

TR = timezone(timedelta(hours=3))
_KATLA = str.maketrans({'İ': 'i', 'I': 'ı', 'ı': 'i', 'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g', 'ö': 'o', 'Ö': 'o',
                        'ş': 's', 'Ş': 's', 'ü': 'u', 'Ü': 'u', 'â': 'a', 'Â': 'a', 'î': 'i', 'Î': 'i', 'û': 'u', 'Û': 'u'})


def tr_kucuk(s):
    return str(s or '').replace('I', 'ı').replace('İ', 'i').lower()


def katla(s):
    t = unicodedata.normalize('NFD', tr_kucuk(s).translate(_KATLA))
    return ''.join(c for c in t if not unicodedata.combining(c))


def _sade(s):
    return re.sub(r'[^a-z0-9]+', ' ', katla(s)).strip()


EKLER = sorted(['larin', 'lerin', 'lari', 'leri', 'lar', 'ler', 'dan', 'den', 'tan', 'ten', 'nda', 'nde', 'ina', 'ine', 'una',
                'une', 'yla', 'yle', 'da', 'de', 'ta', 'te', 'na', 'ne', 'ya', 'ye', 'la', 'le', 'si', 'su', 'mi', 'mu', 'im',
                'um', 'in', 'un', 'i', 'u'], key=len, reverse=True)


def kok(t):
    """Basit ek kırpma (asistanın govdeKok'u ile aynı kural): 'ilanları' -> 'ilan'."""
    for _ in range(2):
        ek = next((e for e in EKLER if t.endswith(e) and len(t) - len(e) >= 4), None)
        if not ek:
            break
        t = t[:-len(ek)]
    return t


# Katlanmış dolgu sözcükleri (soru kalıpları, zamirler, bağlaçlar). Alan sözcükleri (ilan, kpss) en çok kelimeler
# listesinde her şeyi bastırdığı için orada ayrıca atlanır.
DURAK = frozenset('''
ve veya ile mi mu mı mü misin musun misiniz musunuz miyim muyum midir mudur ne nasil icin bir bu su o da de ki ben sen
biz siz onlar var yok varmi yokmu olur olurmu olmaz olarak nedir neler kadar gibi hangi hangisi kim neden niye nerede
nereden nereye kac kacta acaba lutfen ama fakat en cok daha ya hem her tum butun olan olmak olabilir yapilir yapabilirim
edebilirim ise ancak bana beni benim bize bizim sana seni senin la le na ne merhaba merhabalar selam slm mrb hocam hocama
iyi gunler aksamlar tesekkur tesekkurler sagol sagolun abi abla arkadaslar arkadas yardim yardimci eder edermisiniz
istiyorum istiyoruz isterim lazim gerek gerekiyor simdi sonra once zaten hala hep yani evet hayir tamam ok peki sey
zaman zamanda zamani
bilgi bilgisi ogrenmek ogrenebilir ogrenebilirmiyim alabilir alabilirmiyim verir verirmisiniz soyler soylermisiniz
'''.split())
ALAN_SOZLERI = frozenset('ilan ilani ilanlar ilanlari alim alimi kpss basvuru basvur basvurabilir kamu devlet personel'.split())

IL_ADLARI = ('Adana', 'Adıyaman', 'Afyonkarahisar', 'Ağrı', 'Aksaray', 'Amasya', 'Ankara', 'Antalya', 'Ardahan', 'Artvin',
             'Aydın', 'Balıkesir', 'Bartın', 'Batman', 'Bayburt', 'Bilecik', 'Bingöl', 'Bitlis', 'Bolu', 'Burdur', 'Bursa',
             'Çanakkale', 'Çankırı', 'Çorum', 'Denizli', 'Diyarbakır', 'Düzce', 'Edirne', 'Elazığ', 'Erzincan', 'Erzurum',
             'Eskişehir', 'Gaziantep', 'Giresun', 'Gümüşhane', 'Hakkâri', 'Hatay', 'Iğdır', 'Isparta', 'İstanbul', 'İzmir',
             'Kahramanmaraş', 'Karabük', 'Karaman', 'Kars', 'Kastamonu', 'Kayseri', 'Kırıkkale', 'Kırklareli', 'Kırşehir',
             'Kilis', 'Kocaeli', 'Konya', 'Kütahya', 'Malatya', 'Manisa', 'Mardin', 'Mersin', 'Muğla', 'Muş', 'Nevşehir',
             'Niğde', 'Ordu', 'Osmaniye', 'Rize', 'Sakarya', 'Samsun', 'Siirt', 'Sinop', 'Sivas', 'Şanlıurfa', 'Şırnak',
             'Tekirdağ', 'Tokat', 'Trabzon', 'Tunceli', 'Uşak', 'Van', 'Yalova', 'Yozgat', 'Zonguldak')
IL_TAKMA = {'afyon': 'Afyonkarahisar', 'maras': 'Kahramanmaraş', 'urfa': 'Şanlıurfa', 'antep': 'Gaziantep', 'icel': 'Mersin'}
IL_EKLERI = frozenset(['', 'da', 'de', 'ta', 'te', 'dan', 'den', 'tan', 'ten', 'li', 'lu', 'daki', 'deki', 'taki', 'teki',
                       'a', 'e', 'ya', 'ye', 'in', 'nin', 'i', 'si', 'lik', 'yi'])
_IL_LISTESI = [(katla(ad), ad) for ad in IL_ADLARI] + list(IL_TAKMA.items())
_KISA_EKLER = frozenset(['a', 'e', 'ya', 'ye', 'i', 'in'])

# Sitenin meslek listesi gelmezse kullanılan küçük liste (katlanmış eşleşme kelimeleri).
VARSAYILAN_MESLEKLER = [
    {'ad': 'Zabıta memuru', 'kelimeler': ['zabita']},
    {'ad': 'İtfaiye eri', 'kelimeler': ['itfaiye', 'itfaiyeci']},
    {'ad': 'Mühendis', 'kelimeler': ['muhendis']},
    {'ad': 'Tekniker', 'kelimeler': ['tekniker']},
    {'ad': 'Teknisyen', 'kelimeler': ['teknisyen']},
    {'ad': 'Destek personeli', 'kelimeler': ['destek personeli', 'temizlik']},
    {'ad': 'Büro personeli', 'kelimeler': ['buro personeli', 'buro']},
    {'ad': 'Koruma ve güvenlik görevlisi', 'kelimeler': ['koruma', 'guvenlik gorevlisi', 'guvenlik', 'bekci']},
    {'ad': 'Hemşire', 'kelimeler': ['hemsire']},
    {'ad': 'Sağlık teknikeri', 'kelimeler': ['saglik teknikeri']},
    {'ad': 'Veteriner hekim', 'kelimeler': ['veteriner']},
    {'ad': 'Veri hazırlama ve kontrol işletmeni', 'kelimeler': ['vhki', 'veri hazirlama', 'veri girisi']},
    {'ad': 'Bilgisayar işletmeni', 'kelimeler': ['bilgisayar isletmeni']},
    {'ad': 'Şoför', 'kelimeler': ['sofor', 'surucu']},
    {'ad': 'Sekreter', 'kelimeler': ['sekreter']},
    {'ad': 'Hizmetli', 'kelimeler': ['hizmetli']},
    {'ad': 'Memur', 'kelimeler': ['memur']},
    {'ad': 'Öğretmen', 'kelimeler': ['ogretmen']},
    {'ad': 'Avukat', 'kelimeler': ['avukat']},
    {'ad': 'Mimar', 'kelimeler': ['mimar']},
    {'ad': 'Ebe', 'kelimeler': ['ebe']},
    {'ad': 'Psikolog', 'kelimeler': ['psikolog']},
    {'ad': 'Sosyal çalışmacı', 'kelimeler': ['sosyal calismaci']},
    {'ad': 'Polis', 'kelimeler': ['polis']},
]


def _kelime_var(metin, ifade):
    """'metin' içinde ifade kelime başında geçiyor mu (arkasında en çok 4 harflik ek olabilir)."""
    sinir = 2 if len(ifade) <= 3 else 4
    return re.search(rf'(?:^| ){re.escape(ifade)}[a-z]{{0,{sinir}}}(?: |$)', metin) is not None


def il_bul(metin):
    bulunan = []
    for t in _sade(metin).split():
        for k, ad in _IL_LISTESI:
            if not t.startswith(k):
                continue
            ek = t[len(k):]
            if ek not in IL_EKLERI or (ek in _KISA_EKLER and len(k) < 5):
                continue
            if ad not in bulunan:
                bulunan.append(ad)
    return bulunan


def meslek_bul(metin, meslekler):
    """En uzun eşleşen meslek kelimesi kazanır ('zabıta memuru' > 'memur')."""
    secilen, uzunluk, sade_metin = None, 0, _sade(metin)
    for m in meslekler or ():
        for k in m.get('kelimeler') or ():
            k = _sade(k)
            if k and len(k) > uzunluk and _kelime_var(sade_metin, k):
                secilen, uzunluk = m['ad'], len(k)
    return secilen


def icerik_kokleri(soru):
    return [kok(t) for t in _sade(soru).split() if t not in DURAK and not t.isdigit() and len(t) > 1]


def grup_anahtari(soru):
    """Yakın kopyaları birleştiren anahtar: dolgu sözcüksüz, köke inmiş, sıralı ve tekilleştirilmiş içerik."""
    kokler = sorted(set(icerik_kokleri(soru)))
    return ' '.join(kokler) or _sade(soru)


def _zaman(iso):
    try:
        z = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return z if z.tzinfo else z.replace(tzinfo=timezone.utc)


def _oran(pay, payda):
    return round(pay / payda, 4) if payda else None


def _gruplar(kayitlar, en_cok=30):
    gruplar = {}
    for k in kayitlar:
        soru = (k.get('soru') or '').strip()
        if not soru:
            continue
        g = gruplar.setdefault(grup_anahtari(soru), {'adet': 0, 'bicimler': Counter(), 'son': None, 'kanallar': Counter(),
                                                     'idler': []})
        g['adet'] += 1
        g['bicimler'][' '.join(soru.split())] += 1
        g['kanallar'][k.get('kanal') or 'site'] += 1
        g['idler'].append(k.get('id'))
        if k.get('zaman') and (g['son'] is None or k['zaman'] > g['son']):
            g['son'] = k['zaman']
    cikti = []
    for anahtar, g in gruplar.items():
        bicimler = [b for b, _ in g['bicimler'].most_common()]
        cikti.append({'anahtar': anahtar, 'metin': bicimler[0], 'adet': g['adet'], 'son': g['son'],
                      'kanallar': dict(g['kanallar']), 'ornekler': bicimler[1:4], 'idler': g['idler'][:50]})
    cikti.sort(key=lambda g: g['son'] or '', reverse=True)   # eşit sayıda en yenisi önce
    cikti.sort(key=lambda g: -g['adet'])
    return cikti[:en_cok]


def _sayim(kayitlar, alan_fn, en_cok=12):
    sayac, cevapsiz, ilansiz = Counter(), Counter(), Counter()
    for k in kayitlar:
        for ad in alan_fn(k):
            sayac[ad] += 1
            if k.get('tur') == 'bilinmiyor':
                cevapsiz[ad] += 1
            if k.get('tur') == 'ilan' and k.get('ilan_sayisi') == 0:
                ilansiz[ad] += 1
    return [{'ad': ad, 'adet': n, 'cevapsiz': cevapsiz[ad], 'ilansiz': ilansiz[ad]} for ad, n in sayac.most_common(en_cok)]


def kelime_sayimi(kayitlar, en_cok=30):
    """En sık içerik kelimeleri; köke göre sayılır, en sık yazılan asıl biçim gösterilir."""
    sayac, bicimler = Counter(), {}
    for k in kayitlar:
        gorulen = set()
        for ham in re.findall(r'[^\W\d_]+', k.get('soru') or ''):
            kucuk = tr_kucuk(ham)
            t = katla(kucuk)
            if len(t) < 3 or t in DURAK or t in ALAN_SOZLERI:
                continue
            kk = kok(t)
            if kk in DURAK or kk in ALAN_SOZLERI or kk in gorulen:
                continue
            gorulen.add(kk)   # bir soruda aynı kelime bir kez sayılır
            sayac[kk] += 1
            bicimler.setdefault(kk, Counter())[kucuk] += 1
    return [{'kelime': bicimler[kk].most_common(1)[0][0], 'kok': kk, 'adet': n,
             'bicimler': [b for b, _ in bicimler[kk].most_common(4)]} for kk, n in sayac.most_common(en_cok)]


def zenginlestir(kayitlar, meslekler=None):
    """Her kayda il ve meslek ekler (arayüzde süzgeç ve ayrıntı için)."""
    meslekler = meslekler or VARSAYILAN_MESLEKLER
    for k in kayitlar:
        s = _sade(k.get('soru'))
        k['iller'] = il_bul(s)
        k['meslek'] = meslek_bul(s, meslekler)
    return kayitlar


def analiz(kayitlar, meslekler=None, gun=30, simdi=None):
    """kayitlar: Depo.asistan_kayitlari() çıktısı (zenginleştirilmemişse burada zenginleştirilir)."""
    simdi = simdi or datetime.now(timezone.utc)
    if kayitlar and 'iller' not in kayitlar[0]:
        zenginlestir(kayitlar, meslekler)
    zamanli = [(k, _zaman(k.get('zaman'))) for k in kayitlar]

    def aralik(bas, bit):
        return [k for k, z in zamanli if z and bas <= z < bit]

    son7, son30 = aralik(simdi - timedelta(days=7), simdi + timedelta(minutes=5)), aralik(simdi - timedelta(days=30), simdi + timedelta(minutes=5))
    once7, once30 = aralik(simdi - timedelta(days=14), simdi - timedelta(days=7)), aralik(simdi - timedelta(days=60), simdi - timedelta(days=30))
    if gun:
        donem = aralik(simdi - timedelta(days=int(gun)), simdi + timedelta(minutes=5))
    else:
        donem = [k for k, _ in zamanli]

    cevapsiz = [k for k in donem if k.get('tur') == 'bilinmiyor']
    site = [k for k in donem if (k.get('kanal') or 'site') == 'site']
    evet = sum(1 for k in site if k.get('geri') == 1)
    hayir = sum(1 for k in site if k.get('geri') == -1)
    ig = [k for k in donem if k.get('kanal') == 'instagram']
    ig_durum = Counter(k.get('durum') or 'bekliyor' for k in ig)
    ilansiz = [k for k in donem if k.get('tur') == 'ilan' and k.get('ilan_sayisi') == 0]

    return {
        'toplam': len(kayitlar), 'donem_adet': len(donem),
        'kpi': {
            'son7': len(son7), 'once7': len(once7), 'son30': len(son30), 'once30': len(once30),
            'cevapsiz': len(cevapsiz), 'cevapsiz_orani': _oran(len(cevapsiz), len(donem)),
            'geri_evet': evet, 'geri_hayir': hayir, 'faydali_orani': _oran(evet, evet + hayir),
            'geri_orani': _oran(evet + hayir, len(site)), 'site': len(site),
            'ig_toplam': len(ig), 'ig_yanitlandi': ig_durum.get('yanitlandi', 0), 'ig_birakilan': ig_durum.get('atlandi', 0),
            'ig_hata': ig_durum.get('hata', 0), 'ig_bekleyen': ig_durum.get('bekliyor', 0),
            'ilansiz': len(ilansiz),
        },
        'gunluk': gunluk(donem, gun, simdi),
        'kanallar': dict(Counter(k.get('kanal') or 'site' for k in donem)),
        'turler': [{'tur': t, 'adet': n} for t, n in Counter(k.get('tur') or '—' for k in donem).most_common()],
        'meslekler': _sayim(donem, lambda k: [k['meslek']] if k.get('meslek') else []),
        'iller': _sayim(donem, lambda k: k.get('iller') or []),
        'kelimeler': kelime_sayimi(donem),
        'cevapsiz_sorular': _gruplar(cevapsiz),
        'ilansiz_sorular': _gruplar(ilansiz),
    }


def gunluk(kayitlar, gun, simdi):
    """Türkiye saatine göre günlük kanal sayıları; dönemdeki her gün (boş günler dahil, en çok 120 gün)."""
    sayac = {}
    for k in kayitlar:
        z = _zaman(k.get('zaman'))
        if not z:
            continue
        g = z.astimezone(TR).date().isoformat()
        s = sayac.setdefault(g, {'site': 0, 'instagram': 0, 'cevapsiz': 0})
        s['instagram' if k.get('kanal') == 'instagram' else 'site'] += 1
        if k.get('tur') == 'bilinmiyor':
            s['cevapsiz'] += 1
    bugun = simdi.astimezone(TR).date()
    if gun:
        uzunluk = int(gun)
    else:
        ilk = min(sayac) if sayac else bugun.isoformat()
        uzunluk = (bugun - datetime.fromisoformat(ilk).date()).days + 1
    uzunluk = max(1, min(uzunluk, 120))
    cikti = []
    for i in range(uzunluk - 1, -1, -1):
        g = (bugun - timedelta(days=i)).isoformat()
        cikti.append({'gun': g, **sayac.get(g, {'site': 0, 'instagram': 0, 'cevapsiz': 0})})
    return cikti
