"""Eski SBB belge adreslerini (belgeler/sbb/<sha256>.pdf) ilanın sayfasına yönlendirme.

13 Kasım 2026: analiz panelinde en sık 404 veren adresler eski belge kopyalarıydı. Sitede yalnız kayıtların bugün gösterdiği
belge yayımlanır (site_paketi); belgenin özeti değişince (11 Kasım'a kadar SBB her indirmede farklı özet veriyordu, bkz.
sbb_detay.pdf_govdesi; belge düzeltilince de değişir) eski adres 404 verir, oysa sayfada, Telegram'da ya da tarayıcı
geçmişinde duruyor olabilir.

- Kayıt artık önceki özetlerini `eski_belgeler` alanında taşır (ek_kaynaklar.merge_sources, veri_kaydet.merge_registry).
- 13 Kasım'dan önceki özetler bir kez Git geçmişinden çıkarıldı: denetim/eski-belgeler.json {sha256: ilan kimliği}.
- Site derlemesi docs/eski-belgeler.json {sha256: "ilan/<anahtar>/"} yazar; docs/404.html eski belge adresini oradan
  ilan sayfasına yönlendirir. Eşleşmeyen belge için 404 sayfası açıklama gösterir."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOHUM = ROOT / 'denetim' / 'eski-belgeler.json'
CIKTI = 'eski-belgeler.json'      # docs/ altında; docs/404.html bu adı okur
EN_COK = 20                       # kayıt başına saklanan eski özet
SHA = re.compile(r'[a-f0-9]{64}')
PDF = re.compile(r'belgeler/sbb/([a-f0-9]{64})\.pdf')


def guncel_ozetler(item):
    """Kaydın bugün gösterdiği belge özetleri (belge_sha256 ve belge_kopyasi)."""
    s = set(PDF.findall(str(item.get('belge_kopyasi') or '')))
    if SHA.fullmatch(str(item.get('belge_sha256') or '')):
        s.add(item['belge_sha256'])
    return s


def birlestir(guncel, *kayitlar):
    """Kayıtların gösterdiği ya da önceden gösterdiği özetler (verilen sırayla, tekrarsız), `guncel` kaydın bugünkü
    özetleri hariç; en çok EN_COK. merge_sources/merge_registry birleşen kayıtların hepsini verir."""
    haric = guncel_ozetler(guncel or {})
    sira = []
    for k in kayitlar:
        k = k or {}
        for s in [*sorted(guncel_ozetler(k)), *(k.get('eski_belgeler') or [])]:
            if isinstance(s, str) and SHA.fullmatch(s) and s not in haric and s not in sira:
                sira.append(s)
    return sira[:EN_COK]


def isle(merged, *kayitlar):
    """merged kaydına eski_belgeler alanını yazar (boşsa alanı siler)."""
    eski = birlestir(merged, merged, *kayitlar)
    if eski:
        merged['eski_belgeler'] = eski
    else:
        merged.pop('eski_belgeler', None)
    return merged


def _tohum(yol):
    try:
        v = json.loads(Path(yol).read_text(encoding='utf-8'))
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def yonlendirmeler(ilanlar, sayfa_anahtari, sayfali, tohum_yolu=TOHUM):
    """{sha256: 'ilan/<anahtar>/'}: sayfası olan ilanların eski belgeleri. Bugün yayımlanan belge hiç yönlendirilmez."""
    asil, yayinda = {}, set()
    for item in ilanlar or []:
        yayinda |= guncel_ozetler(item)
        anahtar = sayfa_anahtari(item.get('id'))
        if anahtar in sayfali:
            for kimlik in [item.get('id'), *(item.get('kaynak_kimlikleri') or [])]:
                asil.setdefault(kimlik, anahtar)
    sonuc = {}
    for item in ilanlar or []:
        anahtar = asil.get(item.get('id'))
        for s in item.get('eski_belgeler') or []:
            if anahtar and SHA.fullmatch(str(s)):
                sonuc.setdefault(s, anahtar)
    for s, kimlik in _tohum(tohum_yolu).items():
        if SHA.fullmatch(str(s)) and asil.get(kimlik):
            sonuc.setdefault(s, asil[kimlik])
    return {s: f'ilan/{a}/' for s, a in sorted(sonuc.items()) if s not in yayinda}


def yaz(docs, ilanlar, sayfa_anahtari, sayfali, tohum_yolu=TOHUM):
    harita = yonlendirmeler(ilanlar, sayfa_anahtari, sayfali, tohum_yolu)
    (Path(docs) / CIKTI).write_text(json.dumps(harita, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(harita)} eski belge adresi ilan sayfasına yönlendirildi.')
    return harita
