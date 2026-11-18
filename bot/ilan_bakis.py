"""İlan sayfasında başvuru koşullarının en üstünde "Başvuru koşulları — kısaca" (20 Ekim 2026 kullanıcı kararı).

Okuyan kişi önce yalnız bilmesi gerekenleri anahtar kelimelerle görür (kişi sayısı, en düşük puan, başvuru yeri,
yaş/cinsiyet/ehliyet gibi eleyici şartlar); ilgisini çekerse aşağıdaki kadro kartlarını ve ayrıntıları okur.
Son gün, öğrenim, KPSS ve yer zaten sayfanın üst kutusunda; burada tekrar edilmez. Yalnız kayıtta yazanlar, tahmin yok."""
import re
from html import escape as esc

from siniflandir import kucuk


def _kosul_metni(item):
    parca = list(item.get('yz_ortak') or [])
    for k in item.get('yz_kadrolar') or []:
        parca += k.get('kosullar') or []
    for k in item.get('kadro_detay') or []:
        if isinstance(k, dict):
            parca += [str(x) for x in k.get('maddeler') or []]
    for s in item.get('sartlar') or []:
        if isinstance(s, dict):
            parca.append(s.get('metin') or '')
    parca += [item.get('ozet') or '', item.get('kadro') or '']
    return kucuk(' '.join(str(p) for p in parca))


_DENEYIM_RE = r'(?:en az\s*)?(\d{1,2})\s*(?:\(\w+\)\s*)?yıl(?:lık)?\s*(?:[^.;]{0,30}?)(?:deneyim|tecrübe|mesleki)'


def _etiketler(m):
    """Bir metindeki eleyici şartlar: {anahtar: kısa etiket} (deneyim hariç; o kadro sayısına göre ayrıca işlenir)."""
    s = {}
    yas = re.search(r'(\d{2})\s*(?:\([^)]{0,20}\)\s*)?yaşını\s*(?:doldurmamış|bitirmemiş|geçmemiş|tamamlamamış)', m)
    if yas:
        s['yas'] = f'{yas.group(1)} yaş altı'
    elif re.search(r'yaş sınır', m):
        s['yas'] = 'Yaş sınırı var'
    erkek = re.search(r'erkek (?:aday|olmak|personel)', m)
    kadin = re.search(r'kadın (?:aday|olmak|personel)', m)
    if erkek and not kadin:
        s['cinsiyet'] = 'Yalnız erkek'
    elif kadin and not erkek:
        s['cinsiyet'] = 'Yalnız kadın'
    ehliyet = re.search(r'\b([a-e]\d?)\s*sınıfı?\s*sürücü belgesi', m)
    if ehliyet:
        s['ehliyet'] = f'{ehliyet.group(1).upper()} sınıfı ehliyet'
    elif re.search(r'sürücü belgesi|ehliyet', m):
        s['ehliyet'] = 'Sürücü belgesi'
    if re.search(r'\bboy\b|beden kitle', m):
        s['boy'] = 'Boy-kilo şartı'
    if re.search(r'\byds\b|yökdil|yabancı dil', m):
        s['dil'] = 'Yabancı dil'
    if re.search(r'\bengelli\b', m):
        s['engelli'] = 'Engelli kadrosu'
    if re.search(r'güvenlik (?:kimlik kartı|görevlisi kimlik|eğitimi sertifika)|silahlı güvenlik', m):
        s['sertifika'] = 'Güvenlik kimlik kartı'
    elif re.search(r'sertifika', m):
        s['sertifika'] = 'Sertifika'
    return s


def _deneyim_etiketi(metin):
    """Metindeki deneyim yılı: tek yıl '3 yıl deneyim'; metin birden çok farklı yıl veriyorsa ('3 yıllık, diğerleri için 5 yıllık')
    belirsiz kalmaması için 'Kadroya göre 3–5 yıl deneyim'. Yoksa None."""
    yillar = {int(e.group(1)) for e in re.finditer(_DENEYIM_RE, metin)}
    # 'ücret tavanı iki katını geçemeyecekler için en az 3 yıllık, diğerleri için en az 5 yıllık mesleki tecrübe' (Burdur, TAK)
    for e in re.finditer(r'(\d{1,2})\s*yıllık\s*,?\s*diğer\w*\s+için\s+en\s+az\s+(\d{1,2})\s*yıl', metin):
        yillar.update((int(e.group(1)), int(e.group(2))))
    yillar = sorted(yillar)
    if not yillar:
        return None
    return f'{yillar[0]} yıl deneyim' if len(yillar) == 1 else f'Kadroya göre {yillar[0]}–{yillar[-1]} yıl deneyim'


def _konum_metinleri(item):
    """Çok pozisyonlu ilanda her pozisyonun KENDİ koşul metni (liste); tek/pozisyonsuz ilanda []."""
    kadrolar = [k for k in item.get('kadro_detay') or [] if isinstance(k, dict)]
    if len(kadrolar) > 1:
        return [kucuk(' '.join(str(x) for x in k.get('maddeler') or []) + ' ' + ' '.join(str(x) for b in k.get('bolumler') or [] for x in (b[1] if len(b) > 1 else []))) for k in kadrolar]
    yz = [k for k in item.get('yz_kadrolar') or [] if isinstance(k, dict)]
    if len(yz) > 1:
        return [kucuk(' '.join(str(x) for x in k.get('kosullar') or [])) for k in yz]
    return []


def _ortak_metin(item):
    """Tüm pozisyonlar için geçerli metin: ortak şartlar (yz_ortak, kadro_ortak 'GENEL ŞARTLAR'), özet ve kadro satırı."""
    parca = list(item.get('yz_ortak') or [])
    for b in item.get('kadro_ortak') or []:
        if isinstance(b, (list, tuple)) and len(b) > 1 and isinstance(b[1], (list, tuple)):
            # 657 sayılı Kanun genel şartı 'erkek adaylar için askerlik durumu…' yalnız-erkek ilanı demek değildir.
            parca += [re.sub(r'(?i)erkek\s+aday\w*[^.]{0,60}?asker[^.;]*', '', str(x)) for x in b[1]]
    parca += [item.get('ozet') or '', item.get('kadro') or '']
    return kucuk(' '.join(str(p) for p in parca))


def sart_kelimeleri(item):
    """Eleyici şartlar kısa anahtar kelimeyle: '35 yaş altı', 'Erkek', 'Sürücü belgesi', '3 yıl deneyim'...
    Çok pozisyonlu ilanda tek pozisyonun şartı hepsine yazılmaz: ortak metinde (ya da her pozisyonda) olan düz,
    yalnız bazı pozisyonlarda olan 'Bazı kadrolarda …' diye yazılır."""
    if isinstance(item.get('basvuru_kisa_sartlar'), list):
        return [s for s in item['basvuru_kisa_sartlar'] if isinstance(s, str) and s.strip()]
    konumlar = _konum_metinleri(item)
    if not konumlar:
        m = _kosul_metni(item) + ' ' + _ortak_metin(item)
        s = _etiketler(m)
        deneyim = _deneyim_etiketi(m)
        return [v for k, v in s.items() if k in ('yas', 'cinsiyet', 'ehliyet')] \
            + ([deneyim] if deneyim else []) + [v for k, v in s.items() if k not in ('yas', 'cinsiyet', 'ehliyet')]
    ortak = _ortak_metin(item)
    ortak_s = _etiketler(ortak)
    konum_s = [_etiketler(k) for k in konumlar]
    def bazi(etiket):
        return 'Bazı kadrolarda ' + (etiket[:1].lower() + etiket[1:] if etiket[1:2].islower() else etiket)
    genel = {'yas': 'yaş sınırı var', 'ehliyet': 'sürücü belgesi'}   # pozisyonlara göre değeri değişen şartın değersiz hali
    sonuc = {}
    for k in ('yas', 'cinsiyet', 'ehliyet', 'boy', 'dil', 'engelli', 'sertifika'):
        if k in ortak_s:
            sonuc[k] = ortak_s[k]
            continue
        var = [s[k] for s in konum_s if k in s]
        if not var:
            continue
        hepsi, ayni = len(var) == len(konum_s), len(set(var)) == 1
        if ayni:
            sonuc[k] = var[0] if hepsi else bazi(var[0])
        elif k in genel:
            sonuc[k] = ('Kadroya göre ' if hepsi else 'Bazı kadrolarda ') + genel[k]
        else:
            sonuc[k] = bazi(sorted(set(var))[0])
    # Deneyim: yıl pozisyona göre değişir; ortak metinde yazıyorsa hepsi için, yoksa pozisyon aralığı
    yillar = []
    for k in konumlar:
        e = re.search(_DENEYIM_RE, k)
        yillar.append(e.group(1) if e else None)
    ortak_deneyim = _deneyim_etiketi(ortak)
    if ortak_deneyim and not any(yillar):
        sonuc['deneyim'] = ortak_deneyim
    elif any(yillar):
        bulunan = sorted({int(y) for y in yillar if y})
        if None not in yillar and len(bulunan) == 1:
            sonuc['deneyim'] = f'{bulunan[0]} yıl deneyim'
        elif len(bulunan) > 1:
            sonuc['deneyim'] = f'Kadroya göre {bulunan[0]}–{bulunan[-1]} yıl deneyim'
        else:
            sonuc['deneyim'] = f'Bazı kadrolarda {bulunan[0]} yıl deneyim'
    sira = ('yas', 'cinsiyet', 'ehliyet', 'deneyim', 'boy', 'dil', 'engelli', 'sertifika')
    return [sonuc[k] for k in sira if k in sonuc]


def bilgiler(item, toplam=None, simdi=None):
    """[(etiket, değer)] — üst kutuda (son gün, öğrenim, KPSS, yer) olmayan kısa bilgiler."""
    sonuc = []
    if toplam:
        sonuc.append(('Alınacak', f'{toplam} kişi'))
    metin = _kosul_metni(item)
    # Yabancı dil puanı (YDS/YÖKDİL) KPSS eşiği değildir: öncesindeki kısa bağlamda dil sınavı geçen eşleşmeler atlanır.
    puan = next((m for m in re.finditer(r'(?:en az|asgari|minimum)\s*(\d{2,3})(?:[.,]\d+)?\s*(?:\([^)]{0,20}\)\s*)?puan|(\d{2,3})(?:[.,]\d+)?\s*(?:\([^)]{0,20}\)\s*)?(?:ve üzeri\s*)?puan\s*almış', metin)
                 if not re.search(r'\b(?:yds|ydt|yökdil|toefl|ielts)|yabancı dil', re.split(r'[.;]', metin[max(0, m.start() - 60):m.start()])[-1])), None)
    if puan and not item.get('basvuru_puani_belirtilmemis'):
        sonuc.append(('En düşük puan', puan.group(1) or puan.group(2)))
    from ilan_rehber import basvuru_kanali
    kanal = {'iskur': 'İŞKUR', 'kariyer': 'Kariyer Kapısı'}.get(basvuru_kanali(item))
    if kanal:
        sonuc.append(('Başvuru yeri', kanal))
    return sonuc

def bolum_html(item, toplam=None, simdi=None):
    if item.get('duyuru_turu') or item.get('iptal_edildi'):
        return ''
    kutular = bilgiler(item, toplam, simdi)
    sartlar = sart_kelimeleri(item)
    if len(kutular) + len(sartlar) < 2:
        return ''
    izgara = ''.join(f'<div><dt>{esc(e)}</dt><dd>{esc(d)}</dd></div>' for e, d in kutular)
    cipler = ''.join(f'<li>{esc(s)}</li>' for s in sartlar)
    return ('<section class="bakis" aria-label="Başvuru koşulları kısaca"><h2>Başvuru koşulları — kısaca</h2>'
            + (f'<dl class="bakis-izgara">{izgara}</dl>' if izgara else '')
            + (f'<ul class="bakis-sart" aria-label="Öne çıkan şartlar">{cipler}</ul>' if cipler else '')
            + '<p class="bakis-alt">Kadrolar ve tüm koşullar aşağıda ↓</p></section>')
