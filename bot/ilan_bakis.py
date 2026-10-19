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


def sart_kelimeleri(item):
    """Eleyici şartlar kısa anahtar kelimeyle: '35 yaş altı', 'Erkek', 'Sürücü belgesi', '3 yıl deneyim'..."""
    m = _kosul_metni(item)
    sonuc = []
    yas = re.search(r'(\d{2})\s*(?:\([^)]{0,20}\)\s*)?yaşını\s*(?:doldurmamış|bitirmemiş|geçmemiş|tamamlamamış)', m)
    if yas:
        sonuc.append(f'{yas.group(1)} yaş altı')
    elif re.search(r'yaş sınır', m):
        sonuc.append('Yaş sınırı var')
    erkek = re.search(r'erkek (?:aday|olmak|personel)', m)
    kadin = re.search(r'kadın (?:aday|olmak|personel)', m)
    if erkek and not kadin:
        sonuc.append('Yalnız erkek')
    elif kadin and not erkek:
        sonuc.append('Yalnız kadın')
    ehliyet = re.search(r'\b([a-e]\d?)\s*sınıfı?\s*sürücü belgesi', m)
    if ehliyet:
        sonuc.append(f'{ehliyet.group(1).upper()} sınıfı ehliyet')
    elif re.search(r'sürücü belgesi|ehliyet', m):
        sonuc.append('Sürücü belgesi')
    deneyim = re.search(r'(?:en az\s*)?(\d{1,2})\s*(?:\(\w+\)\s*)?yıl(?:lık)?\s*(?:[^.;]{0,30}?)(?:deneyim|tecrübe|mesleki)', m)
    if deneyim:
        sonuc.append(f'{deneyim.group(1)} yıl deneyim')
    if re.search(r'\bboy\b|beden kitle', m):
        sonuc.append('Boy-kilo şartı')
    if re.search(r'\byds\b|yökdil|yabancı dil', m):
        sonuc.append('Yabancı dil')
    if re.search(r'engelli', m):
        sonuc.append('Engelli kadrosu')
    if re.search(r'güvenlik (?:kimlik kartı|görevlisi kimlik|eğitimi sertifika)|silahlı güvenlik', m):
        sonuc.append('Güvenlik kimlik kartı')
    elif re.search(r'sertifika', m):
        sonuc.append('Sertifika')
    return sonuc


def bilgiler(item, toplam=None, simdi=None):
    """[(etiket, değer)] — üst kutuda (son gün, öğrenim, KPSS, yer) olmayan kısa bilgiler."""
    sonuc = []
    if toplam:
        sonuc.append(('Alınacak', f'{toplam} kişi'))
    puan = re.search(r'(?:en az|asgari|minimum)\s*(\d{2,3})(?:[.,]\d+)?\s*(?:\([^)]{0,20}\)\s*)?puan|(\d{2,3})(?:[.,]\d+)?\s*(?:\([^)]{0,20}\)\s*)?(?:ve üzeri\s*)?puan\s*almış', _kosul_metni(item))
    if puan:
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
