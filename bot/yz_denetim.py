"""Yapay zekâ denetçisi (Gemini): ilanı resmî belgeden bağımsız okur, botun çıkardığı bilgilerle karşılaştırır.

Gözlem modu (19 Ekim 2026): hiçbir ilanı durdurmaz; sonuçlar denetim/yz.json'a yazılır, farklar raporlanır.
Kaynak: SBB ilanlarında saklanan PDF (taranmış belge de olsa Gemini görüntüden okur), ÇŞB'de duyuru eki PDF,
diğerlerinde (Kariyer Kapısı, İŞKUR) botun kaynaktan aldığı ham metin alanları.
Karşılaştırılan: son başvuru tarihi, toplam kişi, öğrenim düzeyi, KPSS puan türü, akademik mi.

Anahtar: GEMINI_ANAHTARI (yazdırılmaz). Kullanım: python bot/yz_denetim.py [--en-cok 8]"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SONUC_YOLU = ROOT / 'denetim' / 'yz.json'
MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
API = 'https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent'
EN_BUYUK_PDF = 15 * 1024 * 1024
SURUM = 1   # istem/şema değişince artırılır: eski sonuçlar yeniden denetlenir

ISTEM = """Sen Türkiye kamu personel ilanlarını okuyan titiz bir denetçisin. Aşağıdaki resmî ilanı (belge ya da metin) oku
ve yalnız belgede AÇIKÇA yazanı doldur; tahmin etme, belgede yoksa null ya da boş liste ver.
- son_basvuru_tarihi: başvuruların bittiği gün (YYYY-AA-GG). Sınav, sonuç, belge teslim tarihi DEĞİL.
- son_basvuru_saati: yazıyorsa SS:DD.
- baslangic_tarihi: başvuruların başladığı gün.
- kadrolar: her unvan ve kişi sayısı (asil sayısı; yedek sayma). toplam: asil kişi toplamı.
- ogrenim: yalnız şu değerler: lisans, onlisans, ortaogretim, ilkogretim.
- kpss_gerekli: ilan KPSS puanı istiyorsa true, açıkça istemiyorsa false, belirsizse null.
- puan_turleri: P3, P93, P94, KPSSP1, P48 gibi; en_dusuk_puan: yazıyorsa sayı.
- basvuru_yeri: kariyer_kapisi, iskur, sahsen, posta, eposta, kurum_sitesi, diger.
- sartlar: en çok 8 madde; her biri tek kısa cümle (en çok 120 karakter), kalıp ifade ve mevzuat atfı yok.
- akademik: öğretim üyesi/görevlisi, araştırma görevlisi ilanıysa true.
- iptal_veya_duzeltme: belge yeni ilan değil de iptal/düzeltme/süre uzatma duyurusuysa true.
- okunabilirlik: belge okunabildiyse "iyi", kısmen okunabildiyse "kismi", okunamadıysa "kotu"."""

SEMA = {
    'type': 'OBJECT',
    'properties': {
        'kurum': {'type': 'STRING', 'nullable': True},
        'kadrolar': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
            'unvan': {'type': 'STRING'}, 'adet': {'type': 'INTEGER', 'nullable': True}}, 'required': ['unvan']}},
        'toplam': {'type': 'INTEGER', 'nullable': True},
        'son_basvuru_tarihi': {'type': 'STRING', 'nullable': True},
        'son_basvuru_saati': {'type': 'STRING', 'nullable': True},
        'baslangic_tarihi': {'type': 'STRING', 'nullable': True},
        'ogrenim': {'type': 'ARRAY', 'items': {'type': 'STRING', 'enum': ['lisans', 'onlisans', 'ortaogretim', 'ilkogretim']}},
        'kpss_gerekli': {'type': 'BOOLEAN', 'nullable': True},
        'puan_turleri': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'en_dusuk_puan': {'type': 'NUMBER', 'nullable': True},
        'iller': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'basvuru_yeri': {'type': 'STRING', 'nullable': True},
        'sartlar': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'akademik': {'type': 'BOOLEAN'},
        'iptal_veya_duzeltme': {'type': 'BOOLEAN'},
        'okunabilirlik': {'type': 'STRING', 'enum': ['iyi', 'kismi', 'kotu']},
    },
    'required': ['kadrolar', 'ogrenim', 'puan_turleri', 'sartlar', 'akademik', 'iptal_veya_duzeltme', 'okunabilirlik'],
}


class KotaDoldu(Exception):
    pass


def gemini(parcalar, anahtar, model=MODEL, zaman_asimi=180):
    govde = {'contents': [{'parts': parcalar}],
             'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'responseSchema': SEMA}}
    req = urllib.request.Request(API.format(model), data=json.dumps(govde).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': anahtar})
    try:
        with urllib.request.urlopen(req, timeout=zaman_asimi) as r:
            yanit = json.load(r)
    except urllib.error.HTTPError as h:
        metin = h.read().decode('utf-8', 'replace')[:300]
        if h.code == 429:
            raise KotaDoldu(metin) from None
        raise RuntimeError(f'Gemini HTTP {h.code}: {metin}') from None
    try:
        return json.loads(yanit['candidates'][0]['content']['parts'][0]['text'])
    except (KeyError, IndexError, ValueError):
        raise RuntimeError(f'Gemini yanıtı çözülemedi: {str(yanit)[:300]}') from None


# ---------------------------------------------------------------- kaynak
def _yerel_pdf(item):
    from sbb_detay import document_url
    url = document_url(item)
    if not url:
        return None
    yol = ROOT / 'docs' / 'belgeler' / 'sbb' / url.rsplit('/', 1)[-1]
    return yol.read_bytes() if yol.is_file() else None


def _csb_pdf(item, indir=None):
    for belge in item.get('belgeler') or []:
        link = str(belge.get('link') or '')
        if link.startswith('https://webdosya.csb.gov.tr/') and link.lower().endswith('.pdf'):
            try:
                if indir:
                    return indir(link)
                with urllib.request.urlopen(urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r:
                    return r.read(EN_BUYUK_PDF + 1)
            except Exception:
                return None
    return None


def ham_metin(item):
    """PDF'i olmayan kaynaklar için: botun kaynaktan aldığı ham alanlar (yorumsuz)."""
    satirlar = [f'Başlık: {item.get("baslik")}', f'Kurum: {item.get("kurum")}', f'İlan türü: {item.get("ilan_turu")}',
                f'Yer: {item.get("yer")}', f'Kadro: {item.get("kadro")}']
    for k in item.get('kadro_detay') or []:
        if isinstance(k, dict):
            satirlar.append(f'- {k.get("unvan")} ({k.get("adet")} kişi; {", ".join(k.get("iller") or [])}; '
                            f'öğrenim: {k.get("ogrenim")}): ' + ' '.join(k.get('maddeler') or []))
    for s in item.get('sartlar') or []:
        if isinstance(s, dict):
            satirlar.append(f'- {s.get("kadro")}: {s.get("metin")}')
    for alan in ('ozet', 'basvuru_notu', 'duyuru_cumlesi', 'kadro_ortak'):
        if item.get(alan):
            satirlar.append(f'{alan}: {item[alan]}')
    for alan in ('son_tarih', 'son_zaman', 'baslangic_zaman'):
        if item.get(alan):
            satirlar.append(f'Kaynak sitedeki {alan}: {item[alan]}')
    return '\n'.join(str(s) for s in satirlar if s)


def parcalar(item, indir=None):
    pdf = _yerel_pdf(item) or (_csb_pdf(item, indir) if item.get('kaynak_turu') == 'csb' else None)
    if pdf and len(pdf) <= EN_BUYUK_PDF and pdf[:4] == b'%PDF':
        return [{'inline_data': {'mime_type': 'application/pdf', 'data': base64.b64encode(pdf).decode()}},
                {'text': ISTEM + '\n\nİlan kaynak sayfasındaki başlık: ' + str(item.get('baslik'))}], 'pdf'
    return [{'text': ISTEM + '\n\n--- İLAN ---\n' + ham_metin(item)}], 'metin'


# ---------------------------------------------------------------- karşılaştırma
def bot_degerleri(item):
    import kurum_sayfasi
    from siniflandir import akademik_ilan
    adetler = [a for a, _ in kurum_sayfasi.kadrolar(item)]
    toplam = sum(adetler) if adetler and all(isinstance(a, int) for a in adetler) else None
    return {'son_tarih': str(item.get('son_tarih') or '')[:10] or None, 'toplam': toplam,
            'ogrenim': sorted(item.get('ogrenim') or []), 'puan_turleri': sorted(item.get('puan_turleri') or []),
            'akademik': bool(akademik_ilan(item))}


def karsilastir(item, yz):
    """[(alan, bot, yz, kritik)] — yalnız iki taraf da değer verdiyse fark sayılır."""
    bot = bot_degerleri(item)
    farklar = []
    if bot['son_tarih'] and yz.get('son_basvuru_tarihi') and bot['son_tarih'] != yz['son_basvuru_tarihi'][:10]:
        farklar.append(('son_tarih', bot['son_tarih'], yz['son_basvuru_tarihi'], True))
    if bot['toplam'] and yz.get('toplam') and bot['toplam'] != yz['toplam']:
        farklar.append(('toplam', bot['toplam'], yz['toplam'], True))
    if bot['akademik'] != bool(yz.get('akademik')):
        farklar.append(('akademik', bot['akademik'], bool(yz.get('akademik')), True))
    yz_ogr = sorted(o for o in yz.get('ogrenim') or [] if o != 'ilkogretim')
    if bot['ogrenim'] and yz_ogr and bot['ogrenim'] != yz_ogr:
        farklar.append(('ogrenim', bot['ogrenim'], yz_ogr, False))
    yz_pt = sorted({p.upper().replace('KPSS', '').replace(' ', '') or p for p in yz.get('puan_turleri') or []})
    if bot['puan_turleri'] and yz_pt and bot['puan_turleri'] != yz_pt:
        farklar.append(('puan_turleri', bot['puan_turleri'], yz_pt, False))
    return [list(f) for f in farklar]


# ---------------------------------------------------------------- akış
def imza(item):
    import hashlib
    return hashlib.sha1((ham_metin(item) + str(item.get('belge_kopyasi') or '')).encode()).hexdigest()[:16]


def adaylar(ilanlar, sonuclar, simdi):
    from siniflandir import akademik_ilan
    secilen = []
    for i in ilanlar:
        if i.get('duyuru_turu') or akademik_ilan(i):
            continue
        if str(i.get('son_tarih') or '9999')[:10] < simdi.date().isoformat():
            continue
        onceki = sonuclar.get(i['id'])
        if onceki and onceki.get('surum') == SURUM and onceki.get('imza') == imza(i):
            continue   # içerik değişmedi (detay_guncelleme her taramada yenilenir; ona bakılmaz)
        secilen.append(i)
    return sorted(secilen, key=lambda i: i.get('ilk_gorulme') or '', reverse=True)


def denetle(en_cok=8, anahtar=None, simdi=None, ilanlar=None, sonuc_yolu=SONUC_YOLU, cagir=gemini, indir=None):
    from site_uret import TR
    anahtar = anahtar or os.environ.get('GEMINI_ANAHTARI', '').strip()
    if not anahtar:
        print('GEMINI_ANAHTARI tanımlı değil; denetim atlandı.')
        return None
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    if ilanlar is None:
        from sosyal_motor import ilanlari_yukle
        ilanlar = ilanlari_yukle(ROOT / 'docs')
    try:
        sonuclar = json.loads(Path(sonuc_yolu).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        sonuclar = {}
    sayac = {'denetlenen': 0, 'farkli': 0, 'kritik': 0, 'hata': 0}
    for item in adaylar(ilanlar, sonuclar, simdi)[:en_cok]:
        try:
            parca, kaynak = parcalar(item, indir)
            yz = cagir(parca, anahtar)
        except KotaDoldu:
            print('Gemini günlük/dakikalık kotası doldu; kalanlar sonraki çalışmada.')
            break
        except Exception as hata:
            sayac['hata'] += 1
            print(f'Uyarı: {item.get("kurum")} denetlenemedi: {str(hata)[:200]}')
            continue
        farklar = karsilastir(item, yz)
        sonuclar[item['id']] = {'zaman': simdi.isoformat(timespec='seconds'), 'surum': SURUM, 'model': MODEL,
                                'kaynak': kaynak, 'imza': imza(item), 'baslik': item.get('baslik'),
                                'farklar': farklar, 'yz': yz}
        sayac['denetlenen'] += 1
        sayac['farkli'] += bool(farklar)
        sayac['kritik'] += any(f[3] for f in farklar)
        durum = 'UYUŞUYOR' if not farklar else ('KRİTİK FARK' if any(f[3] for f in farklar) else 'küçük fark')
        print(f'{durum}: {item.get("kurum")} — {item.get("baslik", "")[:70]} ({kaynak}) {farklar or ""}')
    acik = {i['id'] for i in ilanlar}
    sonuclar = {k: v for k, v in sonuclar.items() if k in acik or v.get('zaman', '') >= (simdi.date().isoformat())[:7]}
    Path(sonuc_yolu).parent.mkdir(parents=True, exist_ok=True)
    Path(sonuc_yolu).write_text(json.dumps(dict(sorted(sonuclar.items())), ensure_ascii=False, indent=1) + '\n',
                                encoding='utf-8')
    print(f'Denetim: {sayac}')
    return sayac


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    p = argparse.ArgumentParser()
    p.add_argument('--en-cok', type=int, default=8)
    a = p.parse_args()
    denetle(a.en_cok)
