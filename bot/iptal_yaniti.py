"""İptal/düzeltme duyurusunun Telegram'da orijinal ilana yanıt olarak gönderilmesi için eşleştirme.

Eşleştirme ihtiyatlıdır: yalnızca TAM OLARAK BİR aday varsa yanıt verilir; aksi halde duyuru kartsız düz metin gider.
Yanlış ilana yanıt vermek, yanıt vermemekten kötüdür."""
import re
from datetime import datetime, timedelta, timezone

from csb_kaynak import cekirdek
from ek_kaynaklar import norm
from siniflandir import akademik_ilan

TR = timezone(timedelta(hours=3))
GUN_PENCERESI = 120

# Duyuru/ilan başlıklarında her yerde geçen, ayırt edici olmayan sözcükler.
GENEL = set('''ilk defa atanmak uzere alim alimi alinacak ilan ilani iptal duzeltme duzeltmesi duyuru duyurusu sure suresi
degisikligi uzatim uzatimi belediye belediyesi baskanligi baskanligina genel mudurlugu mudurlugune ile ve icin olarak kadro
kadrosu kadrolari alacak sinav sinavi yonetmeligi hizmet birimi kurumu bakanligi universitesi rektorlugu iptali iptalidir
duzeltmesi duzeltildi'''.split())
# Ayırt ediciliği zayıf unvan sınıfları: yalnız güçlü sözcük yoksa kullanılır.
# Kökler 6 harfe kırpıldığı için burada da kırpılmış biçimleri yazılır ('personel' -> 'person').
ZAYIF = {'memur', 'memuru', 'sozles', 'person', 'isci', 'iscisi', 'kamu'}


def _parcalar(metin):
    return [t for t in norm(metin).split() if len(t) >= 4]


def kurum_kimligi(ilan):
    """('belediye', çekirdek, il) ya da ('kurum', tam normalize ad, None); kurum yoksa None."""
    k = cekirdek(ilan.get('kurum'), ilan.get('yer'))
    if k:
        return ('belediye', k[0], k[1])
    ad = ' '.join(norm(ilan.get('kurum')).split())
    return ('kurum', ad, None) if ad else None


def kurum_uyumlu(a, b):
    x, y = kurum_kimligi(a), kurum_kimligi(b)
    if not x or not y or x[0] != y[0] or x[1] != y[1]:
        return False
    return not (x[2] and y[2] and x[2] != y[2])


def _kokler(ilan, alanlar, kurum_sozcukleri=frozenset()):
    metin = ' '.join(str(ilan.get(a) or '')[:300] for a in alanlar)
    return {t[:6] for t in _parcalar(metin) if t not in GENEL and t not in kurum_sozcukleri}


def anlamli_ortusme(duyuru, ilan):
    """Duyurunun ayırt edici kadro/unvan sözcüklerinden en az biri ilanda geçmeli ('zabıta', 'tekniker'...).
    Duyuruda ayırt edici sözcük yoksa ('memur alımı iptal') zayıf sınıf sözcüğü ortak olmalı."""
    kurum_s = set(norm(duyuru.get('kurum')).split()) | set(norm(ilan.get('kurum')).split())
    d = _kokler(duyuru, ('baslik', 'kadro'), kurum_s)
    i = _kokler(ilan, ('baslik', 'kadro', 'ozet', 'ilan_turu'), kurum_s)
    guclu = {k for k in d if k not in ZAYIF}
    if guclu:
        return bool(guclu & i)
    return bool(d & i & ZAYIF)


def _gun(ilan):
    try:
        z = datetime.fromisoformat(ilan.get('ilk_gorulme') or '')
    except ValueError:
        return None
    if z.tzinfo is None:
        z = z.replace(tzinfo=TR)
    return z.astimezone(TR).date()


def _tur(duyuru):
    return 'iptal' if 'iptal' in norm(duyuru.get('duyuru_turu')) else 'duzeltme'


def orijinal_ara(duyuru, ilanlar, mesajlar, bugun=None, akademik=False, mesaj_gerekli=True):
    """Duyurunun orijinal ilanı için ADAY listesi: kanalda paylaşılmış (telegram_mesajlari'nda kimliği/takma adı olan),
    duyuru olmayan, kurum çekirdeği aynı, kadro/başlıkta anlamlı örtüşen, son 120 günde görülmüş ilanlar.
    Akademik ilanlar hiçbir zaman aday olmaz. akademik=True: tersine yalnız akademik ilanlara bakar ve mesaj kaydı
    aramaz (duyuru akademik bir ilana aitse kanalda hiç paylaşılmamalıdır).
    mesaj_gerekli=False: akademik olmayan ilanlarda da mesaj kaydı aranmaz (duyurunun başka bir ilana ait olup
    olmadığını anlamak için)."""
    bugun = bugun or datetime.now(TR).date()
    adaylar = []
    for ilan in ilanlar:
        if ilan.get('id') == duyuru.get('id') or ilan.get('duyuru_turu'):
            continue
        if akademik_ilan(ilan) != akademik:
            continue
        # Zaten iptal edilmiş ilan da aday kalır: tek aday ise çağıran taraf duyuruyu sessizce tekrar sayar.
        if not akademik and mesaj_gerekli and not mesaj_kimligi(ilan, mesajlar):
            continue
        gun = _gun(ilan)
        if gun and not (timedelta(0) <= (bugun - gun) <= timedelta(days=GUN_PENCERESI)):
            continue
        if kurum_uyumlu(duyuru, ilan) and anlamli_ortusme(duyuru, ilan):
            adaylar.append(ilan)
    return adaylar


def mesaj_kimligi(ilan, mesajlar):
    """İlanın (ya da takma ad kimliklerinin) kayıtlı Telegram mesajı varsa (kimlik, message_id); yoksa None."""
    for k in [ilan.get('id'), *ilan.get('kaynak_kimlikleri', [])]:
        if k in mesajlar and mesajlar[k]:
            return k, mesajlar[k]
    return None


# ---------------------------------------------------------------- tekilleştirme ve kısmi iptal
def guclu_kokler(duyuru, ek_kurum_sozcukleri=frozenset()):
    """Duyurunun ayırt edici (kurum, genel ve zayıf sınıf olmayan) kök sözcükleri."""
    kurum_s = set(norm(duyuru.get('kurum')).split()) | set(ek_kurum_sozcukleri)
    return {k for k in _kokler(duyuru, ('baslik', 'kadro'), kurum_s) if k not in ZAYIF}


def duyuru_imzasi(duyuru):
    """Aynı olayın kopyaları (SBB/İŞKUR/ÇŞB) için ortak imza: kurum çekirdeği + güçlü kök sözcükler
    (güçlü sözcük yoksa tüm kökler). Büyük/küçük harf ve yazım farklarından etkilenmez."""
    k = kurum_kimligi(duyuru)
    kurum = f'{k[0]}:{k[1]}' if k else ''
    kokler = guclu_kokler(duyuru) or _kokler(duyuru, ('baslik', 'kadro'), set(norm(duyuru.get('kurum')).split()))
    return f"{kurum}|{','.join(sorted(kokler))}"


def kadro_kalemleri(ilan):
    """Orijinal ilanın kadro kalemleri (['TEKNİKER', ...]); kadro bilgisi yoksa []."""
    metin = str(ilan.get('kadro') or '')
    metin = re.sub(r'^\s*Toplam\s+\d+\s+ki[sş]i\s*[—–-]\s*', '', metin, flags=re.I)
    kalemler = []
    for parca in re.split(r'\s*[•;]\s*|\s+[—–]\s+', metin):
        parca = re.sub(r'^\d+\s+', '', parca.strip())
        parca = re.sub(r'\s+(?:alacak|alınacak|alim|alım|adet)$', '', parca, flags=re.I).strip()
        if parca:
            kalemler.append(parca)
    return kalemler


def tam_iptal(duyuru, orijinal):
    """İptal duyurusu orijinal ilanın TAMAMINI mı iptal ediyor? Duyuruda ayırt edici sözcük yoksa (genel iptal),
    orijinal tek kalemliyse ya da duyurunun güçlü sözcükleri orijinalin tüm kalemlerini kapsıyorsa evet.
    Orijinalin kadrosu bilinmiyorsa kapsamı kanıtlanamaz: hayır (kısmi sayılır)."""
    guclu = guclu_kokler(duyuru, set(norm(orijinal.get('kurum')).split()))
    if not guclu:
        return True
    kalemler = kadro_kalemleri(orijinal)
    if len(kalemler) == 1:
        return True
    if not kalemler:
        return False
    return all(guclu & {t[:6] for t in _parcalar(k) if t not in GENEL} for k in kalemler)


def kadro_adi(duyuru):
    """Kısmi iptal metni için duyurudaki kadro adı: parantez içi ya da güçlü sözcükler; yoksa ''."""
    baslik = str(duyuru.get('baslik') or '')
    m = re.search(r'\(\s*([^)]+?)\s*\)', baslik)
    if m:
        return m.group(1).strip()
    guclu = guclu_kokler(duyuru)
    kurum_s = set(norm(duyuru.get('kurum')).split())
    sozcukler = [w for w in re.split(r'\s+', baslik) if norm(w)[:6] in guclu and norm(w) not in kurum_s]
    return ' '.join(sozcukler).strip()


def yanit_anahtarlari(tur, orijinal, tam, imza=''):
    """Orijinal ilan (ve takma adları) için kalıcı yanıt anahtarları. Kısmi iptallerde imza eklenir: aynı ilanın farklı
    kadrolarının iptalleri ayrı ayrı bildirilir, aynı kadronun kopyaları tek kez."""
    ek = '' if tam else ':' + imza
    return [f'o:{tur}:{k}{ek}' for k in [orijinal.get('id'), *orijinal.get('kaynak_kimlikleri', [])] if k]


def duz_anahtar(duyuru):
    return f"m:{_tur(duyuru)}:{duyuru_imzasi(duyuru)}"
