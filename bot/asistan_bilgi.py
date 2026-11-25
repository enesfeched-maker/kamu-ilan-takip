"""Site asistanının bilgi dosyası: docs/asistan/bilgi.json (https://kpsstercihi.com/asistan/bilgi.json).
Soru-cevaplar, meslek sayfaları ve önemli sayfalar siteyle aynı kaynaklardan okunur; asistan (bildirim-botu/src/asistan.js)
yalnız bu dosyadaki ve açık ilan listesindeki bilgilerle cevap verir.

Kullanım: python bot/asistan_bilgi.py [docs=docs]"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import meslek_sayfalari as ms  # noqa: E402
import rehberler  # noqa: E402
import yz_gorunurluk  # noqa: E402

BASE = 'https://kpsstercihi.com/'
TELEGRAM = 'https://t.me/kpsstercihi'
SURUM = 1

_TR = str.maketrans({'İ': 'i', 'I': 'ı', 'ı': 'i', 'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g', 'ö': 'o', 'Ö': 'o',
                     'ş': 's', 'Ş': 's', 'ü': 'u', 'Ü': 'u'})


def katla(s):
    """Türkçe küçük harf + Türkçe harf katlama ('Zabıta' -> 'zabita')."""
    return re.sub(r'\s+', ' ', str(s or '').translate(_TR).lower()).strip()


# Meslek adının kendisinden çıkan kelimeler yetmediğinde eklenen gündelik söyleyişler (katlanmış).
EK_KELIMELER = {
    'zabita-memuru': ['zabita'],
    'itfaiye-eri': ['itfaiye', 'itfaiyeci'],
    'muhendis': ['muhendis'],
    'tekniker': ['tekniker', 'teknik'],
    'destek-personeli': ['destek personeli', 'destek'],
    'buro-personeli': ['buro personeli', 'buro'],
    'koruma-ve-guvenlik-gorevlisi': ['koruma', 'guvenlik gorevlisi', 'bekci'],
    'hemsire': ['hemsire'],
    'saglik-teknikeri': ['saglik teknikeri'],
    'veteriner-hekim': ['veteriner'],
    'veri-hazirlama-ve-kontrol-isletmeni': ['vhki', 'veri hazirlama', 'veri girisi'],
    'bilgisayar-isletmeni': ['bilgisayar isletmeni'],
    'sofor': ['sofor', 'surucu'],
    'sekreter': ['sekreter'],
    'hizmetli': ['hizmetli'],
}


def _sss():
    cikti, gorulen = [], set()

    def ekle(s, c, u):
        s, c = ' '.join(str(s).split()), ' '.join(str(c).split())
        k = katla(s)
        if not s or not c or k in gorulen:
            return
        gorulen.add(k)
        cikti.append({'s': s, 'c': c, 'u': u})

    for s, c in yz_gorunurluk.SSS:
        ekle(s, c, BASE + 'sss/')
    for slug, ciftler in rehberler.KISA_CEVAPLAR.items():
        for s, c in ciftler:
            ekle(s, c, f'{BASE}rehber/{slug}/')
    for slug, ciftler in ms.GENEL_SORULAR.items():
        for s, c in ciftler:
            ekle(s, c, f'{BASE}meslek/{slug}/')
    return cikti


def _dolu_meslekler(docs):
    """docs/meslek/dizin.json varsa içeriği olan slug'lar; yoksa None (hepsi alınır)."""
    yol = Path(docs) / ms.KLASOR / ms.DIZIN if hasattr(ms, 'KLASOR') else Path(docs) / 'meslek' / ms.DIZIN
    try:
        return {str(x[0]) for x in json.loads(yol.read_text(encoding='utf-8-sig'))}
    except (OSError, ValueError, IndexError, TypeError):
        return None


def _meslekler(docs):
    dolu = _dolu_meslekler(docs)
    cikti = []
    for slug, ad, _desen in ms.MESLEKLER:
        if dolu is not None and slug not in dolu:
            continue
        kelimeler = []
        for k in EK_KELIMELER.get(slug, []) + [katla(ad)]:
            if k and k not in kelimeler:
                kelimeler.append(k)
        cikti.append({'ad': ad, 'u': f'{BASE}meslek/{slug}/', 'kelimeler': kelimeler})
    return cikti


SAYFALAR = (
    ('Bana uygun ilanlar', 'nereye/', ['puanimla', 'puanla', 'basvurabilir', 'uygun ilan', 'nereye', 'bolumum', 'girerim']),
    ('KPSS taban puanları', 'kpss-taban-puanlari/', ['taban puan', 'taban puani', 'gecen yil', 'yerlesme', 'en dusuk puan']),
    ('Lisans taban puanları', 'kpss-taban-puanlari/lisans/', ['lisans', 'p3']),
    ('Önlisans taban puanları', 'kpss-taban-puanlari/onlisans/', ['onlisans', 'on lisans', 'p93']),
    ('Ortaöğretim taban puanları', 'kpss-taban-puanlari/ortaogretim/', ['ortaogretim', 'lise', 'p94']),
    ('Tercih robotu', 'puanlar/', ['tercih', 'tercih robotu', 'puan turu', 'yerlestirme']),
    ('Sonuç duyuruları', 'sonuclar/', ['sonuc', 'sonuclar', 'sinav sonucu', 'aday listesi', 'mulakat']),
    ('Katiplik klavye sınavı', 'katiplik/', ['katip', 'katiplik', 'zabit katibi', 'klavye', 'adliye']),
    ('Sık sorulan sorular', 'sss/', ['sss', 'sik sorulan', 'soru']),
    ('Ana sayfa', '', ['ana sayfa', 'ilanlar', 'acik ilan']),
)


def _sayfalar(docs):
    """Yalnız üretici kodunda ya da docs/ altında karşılığı doğrulanan sayfalar alınır; ana sayfa her zaman vardır."""
    docs = Path(docs)
    cikti = []
    for ad, yol, kelimeler in SAYFALAR:
        if yol and not any((d / yol / 'index.html').exists() for d in (docs, ROOT / 'docs')) and not _uretilir(yol):
            continue
        cikti.append({'ad': ad, 'u': BASE + yol, 'kelimeler': kelimeler})
    cikti.append({'ad': 'Telegram kanalı', 'u': TELEGRAM, 'kelimeler': ['telegram', 'kanal', 'bildirim', 'yeni ilan']})
    return cikti


def _uretilir(yol):
    """docs/ altında henüz üretilmemiş sayfaların (site_uret çalışmadan önce) üretici koddan doğrulanması."""
    if yol == 'sonuclar/':
        return (Path(__file__).resolve().parent / 'sonuc_takip.py').exists()
    if yol == 'sss/':
        return callable(getattr(yz_gorunurluk, 'sss_sayfasi', None))
    if yol.startswith('kpss-taban-puanlari/'):
        import puan_sayfalari
        k = yol.split('/')[1]
        return not k or k in {d for d, _ in puan_sayfalari.DUZEYLER}
    return False


def uret(docs_dir='docs'):
    return {
        'surum': SURUM,
        'uretim': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'sss': _sss(),
        'meslekler': _meslekler(docs_dir),
        'sayfalar': _sayfalar(docs_dir),
    }


def yaz(docs_dir='docs'):
    veri = uret(docs_dir)
    hedef = Path(docs_dir) / 'asistan' / 'bilgi.json'
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(veri, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return veri


if __name__ == '__main__':
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'docs'
    v = yaz(d)
    print(f'Asistan bilgisi: {len(v["sss"])} soru, {len(v["meslekler"])} meslek, {len(v["sayfalar"])} sayfa.')
