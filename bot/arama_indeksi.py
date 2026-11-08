"""Site araması için ilan belgelerinin kelime dizini (docs/arama-belge.json).

9 Kasım 2026 kullanıcı şikâyeti: meslek yalnız PDF'te geçen SBB ilanları aramada çıkmıyordu; ilanlar.json'da belgenin
kısaltılmış özeti var. Tarayıcıya ham metin yerine yalnız benzersiz kelimeler gider (dosya küçük kalır, arama da
kelime kelime yapılır). Akademik ilanlar sitede listelenmediği için dizine girmez."""
import hashlib
import json
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

from kurum_sayfasi import anahtar

ROOT = Path(__file__).resolve().parent.parent
ONBELLEK = ROOT / '.cache' / 'pdf'
EN_BUYUK_BELGE = 8_000_000
EN_COK_KARAKTER = 20_000   # tek ilanın dizini; çok sayfalı belgeler dosyayı şişirmesin
YAYGIN_ORAN = 0.15
YAYGIN_EN_AZ_BELGE = 20
DOLGU = frozenset('''ve veya ile icin olan olarak olmak bir bu su o da de ki ise gibi kadar daha en her ilan ilani tarih tarihi
sayili sayisi madde maddesi uzere gore ait nin nun dan den ise icin hakkinda'''.split())


def katla(metin):
    """portal.js normalize + aramaNorm ile aynı kural; ikisi birlikte değişmeli."""
    metin = (metin or '').replace('I', 'ı').replace('İ', 'i').lower()
    metin = ''.join(c for c in unicodedata.normalize('NFD', metin) if not unicodedata.combining(c)).replace('ı', 'i')
    metin = re.sub(r"['’`]", '', metin)
    return re.sub(r'(\d)\s*[/-]\s*([a-z])\b', r'\1\2', metin)


def kelimeler(metin):
    """Belgedeki sırayla benzersiz arama kelimeleri (sayılar ve dolgu sözcükleri hariç)."""
    gorulen, sonuc, toplam = set(), [], 0
    for k in re.findall(r'[a-z0-9]+', katla(metin)):
        if k in gorulen or len(k) < 3 or k.isdigit() or k in DOLGU:
            continue
        gorulen.add(k)
        toplam += len(k) + 1
        if toplam > EN_COK_KARAKTER:
            break
        sonuc.append(k)
    return ' '.join(sonuc)


def _pdf_metni(yol):
    from pypdf import PdfReader
    return '\n'.join(s.extract_text() or '' for s in PdfReader(str(yol)).pages)


def _docx_metni(yol):
    with zipfile.ZipFile(yol) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    return ' '.join(re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', xml))


def belge_kelimeleri(yol, onbellek=ONBELLEK):
    """Belge değişmediği sürece (içerik özetine göre) önbellekten; okunamayan belge boş döner, ilan yine aranır."""
    try:
        if not yol.is_file() or yol.stat().st_size > EN_BUYUK_BELGE:
            return ''
        ozet = hashlib.sha256(yol.read_bytes()).hexdigest()
        kayit = onbellek / f'arama-{ozet}.txt'
        if kayit.is_file():
            return kayit.read_text(encoding='utf-8')
        sonuc = kelimeler(_docx_metni(yol) if yol.suffix.lower() == '.docx' else _pdf_metni(yol))
        onbellek.mkdir(parents=True, exist_ok=True)
        kayit.write_text(sonuc, encoding='utf-8')
        return sonuc
    except Exception as hata:
        print(f'Uyarı: arama dizini belgeyi okuyamadı ({yol.name}): {hata}')
        return ''


def belge_yollari(ilan, docs):
    """İlanın depodaki belge kopyaları: SBB/İŞKUR PDF'i ve ÇŞB ekleri."""
    yollar = []
    ozet = ilan.get('belge_sha256') or ilan.get('iskur_belge_sha256')
    if ozet:
        yollar.append(docs / 'belgeler' / 'sbb' / f'{ozet}.pdf')
    if ilan.get('belgeler'):
        import csb_kaynak
        for b in ilan['belgeler']:
            if b.get('link'):
                yollar.append(csb_kaynak.belge_yolu(b['link']))
    return yollar


def dizin_uret(ilanlar, docs, onbellek=ONBELLEK):
    """{ilan anahtarı: 'kelime kelime'}; belgesi olmayan ya da okunamayan ilan dizine girmez."""
    dizin = {}
    for ilan in ilanlar:
        if ilan.get('kategori') == 'akademik':
            continue
        metin = ' '.join(filter(None, (belge_kelimeleri(y, onbellek) for y in belge_yollari(ilan, Path(docs)))))
        if metin:
            dizin[anahtar(ilan)] = metin
    return yaygini_ele(dizin)


def yaygini_ele(dizin):
    """Belgelerin çoğunda geçen kalıp sözcükler ('657 sayılı Devlet Memurları', 'sürücü belgesi', 'sosyal güvenlik') her ilanı
    sonuca sokmasın; ayırt edici meslek adları kalır. Az belgede eşik uygulanmaz."""
    if len(dizin) < YAYGIN_EN_AZ_BELGE:
        return dizin
    sayac = Counter(k for metin in dizin.values() for k in set(metin.split()))
    esik = len(dizin) * YAYGIN_ORAN
    return {a: ' '.join(k for k in metin.split() if sayac[k] <= esik) for a, metin in dizin.items()}


def yaz(ilanlar, docs):
    Path(docs, 'arama-belge.json').write_text(json.dumps(dizin_uret(ilanlar, docs), ensure_ascii=False, separators=(',', ':')),
                                              encoding='utf-8')
