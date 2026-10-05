"""Kaynaklar arası yinelenen ilanlar ("kopya"): aynı gerçek ilanın İŞKUR / SBB / ÇŞB / Kariyer Kapısı'ndan ayrı kayıtlar olarak gelmesi.

Derleme zamanı, saf fonksiyonlar; veriye dokunmaz. Kural: yanlış birleştirme, kaçan kopyadan kötüdür; bu yüzden
her eşleşme şu koşulların HEPSİNİ ister: farklı kaynak (resmî bağlantı sunucuları ayrık), çözülmüş aynı il,
aynı kurum çekirdeği, aynı son başvuru günü ve uyumlu kadro. Belirsiz durumda eşleştirme yapılmaz.

kopya_bul() -> {'kopya_of': {ikincil id: birincil id}, 'gruplar': {birincil id: [ikincil id, …]}}"""
import re
from datetime import date, timedelta
from urllib.parse import urlparse

import kurum_sayfasi as ks
import liste_verisi
from siniflandir import akademik_ilan, kucuk

GENEL_UNVANLAR = {'memur', 'sözleşmeli personel', 'personel', 'işçi', 'sürekli işçi', 'sözleşmeli', 'daimi işçi'}
CSB_PENCERE_GUN = 60  # ÇŞB duyuru tarihi -> eşleşen ilanın son başvurusu en çok bu kadar sonra olabilir
RUTBE = {'kariyerkapisi.gov.tr': 0, 'kamuilan.sbb.gov.tr': 0, 'yerelyonetimler.csb.gov.tr': 1, 'www.iskur.gov.tr': 2, 'iskur.gov.tr': 2}
AD_SIRASI = ['Kariyer Kapısı', 'SBB', 'ÇŞB', 'İŞKUR']


def _kaynak_listesi(item):
    """[{'ad','link'}] — kaynaklar alanı, yoksa tek kaynak (link + kaynak adı)."""
    kay = [s for s in (item.get('kaynaklar') or []) if isinstance(s, dict) and s.get('link')]
    return kay or [{'ad': item.get('kaynak') or 'Kariyer Kapısı', 'link': item.get('link') or ''}]


def _hostlar(item):
    return {urlparse(s['link']).hostname or '' for s in _kaynak_listesi(item)} - {''}


def _rutbe(item):
    return min([RUTBE.get(h, 3) for h in _hostlar(item)] or [3])


def _ad_kisalt(ad):
    return {'SBB Kamu İlan': 'SBB', 'ÇŞB Yerel Yönetimler': 'ÇŞB'}.get(ad, ad)


def _il_kendi(item):
    """Kaydın kendi bildirdiği tek il (addan/iller/yerden); çoklu, bilinmeyen ya da geçersiz il için ''."""
    il = liste_verisi.il_bul(item, None)
    return il if il and ks.kurum_anahtari(il) in ks.IL_ADI else ''


def _unvanlar(item):
    return {re.sub(r'\s*\(.*?\)', '', kucuk(ad)).strip() for _, ad in ks.kadrolar(item)} - {''}


def _toplam(item):
    return ks.kart_alanlari(item).get('toplam')


def _isci(item):
    metin = ks.kurum_anahtari(' '.join(str(item.get(a) or '') for a in ('baslik', 'kadro', 'ozet')))
    return bool(re.search(r'\bisci', metin))


def _uyumlu_kadro(a, b):
    """Kadro uyumlu mu: unvanlar kesişiyor; ya da bir taraf yalnız genel unvan ('memur') ve toplamlar eşit;
    ya da iki tarafta da unvan yok ama toplam eşit. Yalnız bir tarafta kadro bilgisi varsa doğrulanamaz -> False."""
    ua, ub = _unvanlar(a), _unvanlar(b)
    ta, tb = _toplam(a), _toplam(b)
    if ua and ub:
        if ua & ub:
            return True
        return (ua <= GENEL_UNVANLAR or ub <= GENEL_UNVANLAR) and bool(ta) and ta == tb
    if not ua and not ub:
        return bool(ta) and ta == tb
    return False


def _tur(item):
    """'sozlesmeli' | 'memur' | None — başlık/ilan türü/kadro metninden."""
    m = ks.kurum_anahtari(' '.join(str(item.get(a) or '') for a in ('baslik', 'ilan_turu', 'kadro')))
    return 'sozlesmeli' if 'sozlesmeli' in m else 'memur' if re.search(r'\bmemur', m) else None


def _tur_uyumlu(a, b):
    x, y = _tur(a), _tur(b)
    return not x or not y or x == y


def _gun(iso):
    try:
        return date.fromisoformat((iso or '')[:10])
    except ValueError:
        return None


def _zengin(item):
    """Birincil seçimi için sıralama anahtarı (küçük = daha zengin)."""
    return (0 if ks.kadrolar(item) else 1, 0 if (item.get('ozet') or item.get('sartlar')) else 1,
            _rutbe(item), -(_toplam(item) or 0), item.get('ilk_gorulme') or '9999', item.get('id') or '')


def _uygun(item):
    if akademik_ilan(item) or item.get('duyuru_turu') or item.get('iptal_edildi') or not (item.get('kurum') or '').strip():
        return False
    try:
        import site_uret
        return site_uret.detail_page(item) is not None
    except Exception:
        return False


KURUM_TAKMA = {'iett': 'elektrik tramvay tunel'}   # kısaltma -> adın ayırt edici sözcükleri
KURUM_GENEL = {'ve', 'ile', 'genel', 'mudurlugu', 'kurumu', 'kurulu', 'cumhurbaskanligi', 'baskanlik'}
BASLIK_GENEL = {'ve', 'ile', 'veya', 'alim', 'alimi', 'ilani', 'duyurusu', 'personel', 'sinav', 'sinavi', 'yili', 'yilinda',
                'alacak', 'alinacak', 'ilk', 'defa', 'atanmak', 'uzere', 'aciktan', 'temin', 'edecektir', 'adet', 'kisi',
                'toplam', 'sozlesmeli', 'mevcut'}
ILK_GORULME_FARKI_GUN = 10   # bir tarafta son tarih yoksa kayıtlar en çok bu kadar gün arayla görülmüş olmalı
SINAV_PENCERE_GUN = 60       # Kariyer Kapısı ilan penceresi sonu ile SBB sınav başvuru sonu arası en çok bu kadar
BASLIK_ORTAK_ESIK = 0.6
KK, SBB_HOST, CSB_HOST = 'kariyerkapisi.gov.tr', 'kamuilan.sbb.gov.tr', 'yerelyonetimler.csb.gov.tr'


def _kurum_cekirdek(item, kan):
    """Kurum adının karşılaştırma çekirdeği: parantezli kısaltma, 've/genel müdürlüğü/kurumu', 'Cumhurbaşkanlığı' öneki ve
    (geriye ≥3 sözcük kalıyorsa) baştaki il atılır; belediyelerde kanonik ad olduğu gibi kalır.
    'İstanbul Bankacılık Düzenleme ve Denetleme Kurumu' ile 'BANKACILIK DÜZENLEME VE DENETLEME KURUMU BAŞKANLIĞI (BDDK)' aynıdır."""
    if kan.endswith(' belediye'):
        return frozenset(kan.split())
    ad = ks.kurum_anahtari(re.sub(r'\([^)]*\)', ' ', item.get('kurum') or ''))
    for kisa, acik in KURUM_TAKMA.items():
        ad = re.sub(r'\b' + kisa + r'\b', acik, ad)
    sozcukler = [w for w in ad.split() if w not in KURUM_GENEL]
    if len(sozcukler) >= 4 and sozcukler[0] in ks.IL_ANAHTAR:
        sozcukler = sozcukler[1:]
    return frozenset(sozcukler)


JSGA = 'jandarma ve sahil guvenlik akademisi'
JGK = 'jandarma genel komutanligi'


def _jandarma_takma(a, b):
    """Jandarma ve Sahil Güvenlik Akademisi, J.Gn.K.'lığı adına personel temin eder: başlığında 'J.Gn.K.' ya da 'Jandarma Genel
    Komutanlığı' geçen Akademi ilanı, Jandarma Genel Komutanlığı ilanıyla aynı kurum sayılır. Başka Akademi ilanı sayılmaz."""
    ka, kb = ks.kurum_kanonik(a.get('kurum')), ks.kurum_kanonik(b.get('kurum'))
    if {ka, kb} != {JSGA, JGK}:
        return False
    akademi = a if ka == JSGA else b
    baslik = ks.kurum_anahtari(str(akademi.get('baslik') or '')).replace('.', '')
    return bool(re.search(r'\bj ?gn ?k\b', baslik) or JGK in baslik)


def _genel_belge_kelimeleri(item):
    """Kaydın şart / özet metnindeki sözcük kökleri (SBB'de kadro adı yalnız 'MEMUR' ise unvan burada geçer)."""
    metin = ' '.join([str(item.get('ozet') or '')] + [str(s.get('kadro') or '') + ' ' + str(s.get('metin') or '')
                                                       for s in item.get('sartlar') or [] if isinstance(s, dict)])
    return {w[:5] for w in ks.kurum_anahtari(metin).split()}


def _belgede_unvan_gecer(genel, bilgisiz):
    """Kadrosu yalnız genel unvan ('MEMUR') olan kaydın belge metni, kadro bilgisi olmayan kaydın başlığındaki özgül unvan
    sözcüklerinin (örn. 'zabıta') hepsini içeriyor mu."""
    if not _unvanlar(genel) or not _unvanlar(genel) <= GENEL_UNVANLAR or _unvanlar(bilgisiz):
        return False
    ozgul = {w for w in _baslik_belirtecleri(bilgisiz) if w not in {'memur', 'perso', 'isci'}}
    return bool(ozgul) and ozgul <= _genel_belge_kelimeleri(genel)


def _baslik_belirtecleri(item):
    kurum = set(ks.kurum_anahtari(item.get('kurum') or '').split())
    sozcukler = ks.kurum_anahtari(' '.join(str(item.get(a) or '') for a in ('baslik', 'kadro'))).split()
    return {w[:5] for w in sozcukler if not w.isdigit() and w not in BASLIK_GENEL and w not in kurum}   # 5 harflik kök: yardımcısı/yardımcılığı


def _baslik_ortak(a, b):
    """Unvan sözcüklerinin örtüşme oranı (küçük kümeye göre); bir tarafta sözcük yoksa 0."""
    x, y = _baslik_belirtecleri(a), _baslik_belirtecleri(b)
    return len(x & y) / min(len(x), len(y)) if x and y else 0


def ortak_unvan(a, b):
    """Başlık/kadro sözcükleri ≥ BASLIK_ORTAK_ESIK örtüşüyor ve en az 2 ortak sözcük var."""
    return _baslik_ortak(a, b) >= BASLIK_ORTAK_ESIK and len(_baslik_belirtecleri(a) & _baslik_belirtecleri(b)) >= 2


def _toplam_esit_ya_da_bilinmiyor(a, b):
    ta, tb = _toplam(a), _toplam(b)
    return not (ta and tb) or ta == tb


def _basvuru_araligi(item):
    """Başvuru notundaki ilk 'gg/aa/yyyy – gg/aa/yyyy' aralığı (yoksa None)."""
    m = re.search(r'(\d{2}/\d{2}/\d{4})\s*[–—-]\s*(\d{2}/\d{2}/\d{4})', str(item.get('basvuru_notu') or ''))
    return m.groups() if m else None


def _asamada(a, b):
    """a'nın aşamalı başvuru takvimi (basvuru_asamalari) b'nin son tarihini kapsıyor mu."""
    try:
        s = a['basvuru_asamalari']
        bas, bit = _gun(s['on'][0]), _gun(s['nihai'][1])
        return bool(bas and bit and _gun(b.get('son_tarih')) and bas <= _gun(b['son_tarih']) <= bit)
    except (KeyError, TypeError, IndexError):
        return False


def _takma_ad(a, b):
    return a.get('id') in (b.get('kaynak_kimlikleri') or []) or b.get('id') in (a.get('kaynak_kimlikleri') or [])


def _ayni_ilan(a, b):
    try:
        from ek_kaynaklar import same_listing
        return bool(same_listing(a, b))
    except Exception:
        return False


def kopya_bul(ilanlar):
    """Kaynaklar arası yinelenen ilanları bulur; bkz. modül açıklaması. Girdi değiştirilmez."""
    ilanlar = [liste_verisi.donem_tamamla(i) for i in ilanlar]   # SBB'de son tarih yoksa dönemden türetilir
    aday = [i for i in ilanlar if i.get('id') and _uygun(i)]
    # İli kayıtta yazmayan belediye (SBB 'HANAK BELEDİYE BAŞKANLIĞI'), aynı adın ili yalnızca TEK ilse o ile bağlanır.
    kendi_il = {}
    for i in ilanlar:
        il = _il_kendi(i)
        if il:
            kendi_il.setdefault(ks.kurum_kanonik(i.get('kurum')), set()).add(il)

    def il_coz(i, kan):
        il = _il_kendi(i)
        if il:
            return il
        adaylar = kendi_il.get(kan, set()) if kan.endswith(' belediye') else set()
        return next(iter(adaylar)) if len(adaylar) == 1 else ''

    bilgi = {}
    for i in aday:
        kan = ks.kurum_kanonik(i.get('kurum'))
        bilgi[i['id']] = {'il': il_coz(i, kan), 'kan': kan, 'host': _hostlar(i), 'cekirdek': _kurum_cekirdek(i, kan)}
    siralama = sorted(aday, key=_zengin)

    def temel(a, b):
        x, y = bilgi[a['id']], bilgi[b['id']]
        if x['host'] & y['host'] or not x['kan'] or _isci(a) != _isci(b):
            return False
        if not (x['kan'] == y['kan'] or x['cekirdek'] and x['cekirdek'] == y['cekirdek'] or _jandarma_takma(a, b)):
            return False
        if x['il'] and y['il']:
            return x['il'] == y['il']
        # ili bir tarafta yazmayan (İŞKUR'un şehri, SBB'de il yok) ulusal kurum ilanı eşleşebilir; belediyede il şarttır
        return not x['kan'].endswith(' belediye')

    def tarih_uyumlu(a, b):
        sa, sb = _gun(a.get('son_tarih')), _gun(b.get('son_tarih'))
        if sa and sb:
            fark = abs((sa - sb).days)
            if fark == 0:
                return True
            if _asamada(a, b) or _asamada(b, a):
                return True   # ön + nihai başvuru: öteki kaynağın tarihi aşamalardan birine denk geliyor
            if fark == 1:   # bir günlük kayma (İŞKUR'un 23:59'u): ancak unvan sözcükleri de güçlü biçimde örtüşürse
                return ortak_unvan(a, b)
            if fark <= 3 and _basvuru_araligi(a) and _basvuru_araligi(a) == _basvuru_araligi(b):
                return True   # iki kaynak da belgeden aynı başvuru aralığını (örn. 01/10 – 05/10) veriyor; SBB dönem sonu farklı olabilir
            return sinav_penceresi(a, b, fark)
        if not (sa or sb):
            return False
        eksik = b if sa else a
        ga, gb = _gun(a.get('ilk_gorulme')), _gun(b.get('ilk_gorulme'))
        return bool(ga and gb and abs((ga - gb).days) <= ILK_GORULME_FARKI_GUN and bilgi[eksik['id']]['host'] != {CSB_HOST})

    def sinav_penceresi(a, b, fark):
        """Kariyer Kapısı'nın bitiş tarihi ilan penceresidir, SBB'nin sınav başvuru sonu: aynı kurum, ortak unvan, eşit kadro."""
        hostlar = {frozenset(bilgi[a['id']]['host']), frozenset(bilgi[b['id']]['host'])}
        return (hostlar == {frozenset({KK}), frozenset({SBB_HOST})} and fark <= SINAV_PENCERE_GUN
                and bilgi[a['id']]['cekirdek'] == bilgi[b['id']]['cekirdek']
                and _baslik_ortak(a, b) >= BASLIK_ORTAK_ESIK and _toplam_esit_ya_da_bilinmiyor(a, b))

    def kismi_kadro(a, b):
        """Kariyer Kapısı ayrıştırması kadroların yalnız bir kısmını listeleyebilir (ör. 18 kadrodan 13'ü): aynı son tarih ve aynı
        başlangıç günü, toplamlar farklı, küçük tarafın unvanları büyük tarafın unvanlarının altkümesi ya da büyük taraf genel
        unvanlı ('sözleşmeli personel') ise aynı ilandır. Birincil, belgeye dayalı büyük toplamlı kayıttır (_zengin)."""
        ta, tb = _toplam(a), _toplam(b)
        if not (ta and tb) or ta == tb or not a.get('son_tarih') or a.get('son_tarih') != b.get('son_tarih'):
            return False
        ba, bb = _gun(a.get('baslangic_zaman')), _gun(b.get('baslangic_zaman'))
        if not ba or ba != bb or not _tur_uyumlu(a, b):
            return False
        kucuk_, buyuk_ = (a, b) if ta < tb else (b, a)
        uk, ub = _unvanlar(kucuk_), _unvanlar(buyuk_)
        return bool(uk) and bool(ub) and (uk <= ub or ub <= GENEL_UNVANLAR)

    def kadro_uyumlu(a, b):
        """Unvanlar uyumlu; ya da toplam çelişmiyor ve unvan sözcükleri büyük oranda ortak (en az 2 ortak sözcük);
        bir tarafta unvan bilgisi yoksa eşit bilinen toplam da yeter. Her iki tarafta unvan bilinip uyuşmuyorsa ortak sözcük şart."""
        if _uyumlu_kadro(a, b) or kismi_kadro(a, b):
            return True
        if not _tur_uyumlu(a, b) or not _toplam_esit_ya_da_bilinmiyor(a, b):
            return False
        ortak = ortak_unvan(a, b)
        if _unvanlar(a) and _unvanlar(b):
            return ortak
        return (ortak or bool(_toplam(a) and _toplam(a) == _toplam(b)) or _belgede_unvan_gecer(a, b) or _belgede_unvan_gecer(b, a)
                or _genel_baslikli_tekil(a, b))

    def _genel_baslikli_tekil(a, b):
        """Bir tarafta kadro de unvan de yok ('X Ajansı Personel Alım İlanı'): belediye dışı kurumda, aynı son tarihte, o kurumun her
        kaynaktan yalnız tek ilanı varsa aynı ilan sayılır (içerik doğrulanamaz ama başka aday da yoktur)."""
        x = a if not _unvanlar(a) else b
        y = b if x is a else a
        if _unvanlar(x) or _baslik_belirtecleri(x) or not _unvanlar(y):
            return False
        bx, by = bilgi[x['id']], bilgi[y['id']]
        if bx['kan'].endswith(' belediye') or not (bx['cekirdek'] and bx['cekirdek'] == by['cekirdek']):
            return False
        son = x.get('son_tarih')
        if not son or son != y.get('son_tarih'):
            return False
        say = {}
        for c in aday:
            bc = bilgi[c['id']]
            if bc['cekirdek'] == bx['cekirdek'] and c.get('son_tarih') == son:
                for h in bc['host']:
                    say[h] = say.get(h, 0) + 1
        return all(n == 1 for n in say.values())

    def guclu(a, b):
        if _takma_ad(a, b) or _ayni_ilan(a, b) and not (bilgi[a['id']]['host'] & bilgi[b['id']]['host']):
            return True
        return temel(a, b) and tarih_uyumlu(a, b) and kadro_uyumlu(a, b)

    atanan, gruplar = {}, {}
    for r in siralama:
        if r['id'] in atanan:
            continue
        gruplar[r['id']] = [r]
        atanan[r['id']] = r['id']
        hostlar = set(bilgi[r['id']]['host'])
        for s in siralama:
            if s['id'] in atanan or bilgi[s['id']]['host'] & hostlar or not guclu(r, s):
                continue
            gruplar[r['id']].append(s)
            atanan[s['id']] = r['id']
            hostlar |= bilgi[s['id']]['host']

    # ÇŞB duyuruları son tarih/kadro taşımaz: yalnız TEK bir gruba uyuyorsa (ve o grubun başka ÇŞB adayı yoksa) bağlanır.
    csb = [i for i in aday if bilgi[i['id']]['host'] == {'yerelyonetimler.csb.gov.tr'} and not i.get('son_tarih') and atanan[i['id']] == i['id'] and len(gruplar[i['id']]) == 1]

    def csb_uyar(c, lider):
        if lider['id'] == c['id']:
            return False
        for u in gruplar[lider['id']]:
            if not temel(c, u) or not u.get('son_tarih') or not _tur_uyumlu(c, u):
                continue
            yayim, son = _gun(c.get('yayim_tarihi') or c.get('ilk_gorulme')), _gun(u['son_tarih'])
            if yayim and son and yayim <= son <= yayim + timedelta(days=CSB_PENCERE_GUN):
                return True
        return False

    kimlik = {i['id']: i for i in aday}
    uyan = {c['id']: [l for l in gruplar if csb_uyar(c, kimlik[l])] for c in csb}
    for c in csb:
        liderler = [l for l in uyan[c['id']] if gruplar[l][0]['id'] == l]
        if len(liderler) != 1 or sum(1 for d in csb if liderler[0] in uyan[d['id']]) != 1:
            continue
        gruplar[liderler[0]].append(c)
        atanan[c['id']] = liderler[0]
        del gruplar[c['id']]

    kopya_of = {i: l for i, l in atanan.items() if i != l}
    return {'kopya_of': kopya_of, 'gruplar': {l: [m['id'] for m in g[1:]] for l, g in gruplar.items() if len(g) > 1},
            'uyeler': {l: g for l, g in gruplar.items() if len(g) > 1}}


def sayfa_bilgisi(kopyalar, item, kimlik_harita):
    """Ayrıntı sayfası için: ikincil kayıtta {'rol': 'ikincil', 'birincil': anahtar}; birincilde {'rol': 'birincil', 'adlar', 'baglantilar'}; yoksa None."""
    kimlik = item.get('id')
    birincil = (kopyalar.get('kopya_of') or {}).get(kimlik)
    if birincil:
        hedef = kimlik_harita.get(birincil)
        return {'rol': 'ikincil', 'birincil': ks.anahtar(hedef)} if hedef else None
    uyeler = (kopyalar.get('uyeler') or {}).get(kimlik)
    if uyeler:
        return {'rol': 'birincil', 'adlar': kaynak_adlari(uyeler), 'baglantilar': kaynak_baglantilari(uyeler), 'ikincil_idler': [m['id'] for m in uyeler[1:]]}
    return None


def kaynak_adlari(uyeler):
    """Gruptaki kayıtların (birincil ilk) kaynak görünen adları, tekrarsız, kısa: ['İŞKUR', 'ÇŞB']."""
    sonuc = []
    for m in uyeler:
        for s in _kaynak_listesi(m):
            ad = _ad_kisalt(s.get('ad') or '')
            if ad and ad not in sonuc:
                sonuc.append(ad)
    return sorted(sonuc, key=lambda a: AD_SIRASI.index(a) if a in AD_SIRASI else 9)


def kaynak_baglantilari(uyeler):
    """[(kısa ad, resmî bağlantı)] — yalnız resmî sunucular, tekrarsız."""
    sonuc, gorulen = [], set()
    for m in uyeler:
        for s in _kaynak_listesi(m):
            u = urlparse(s.get('link') or '')
            if u.scheme == 'https' and u.hostname in RUTBE and not u.username and not u.password and s['link'] not in gorulen:
                gorulen.add(s['link'])
                sonuc.append((_ad_kisalt(s.get('ad') or ''), s['link']))
    return sonuc
