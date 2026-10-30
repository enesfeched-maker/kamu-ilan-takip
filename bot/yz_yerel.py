"""Yerel yapay zekâ (Ollama): ilanı resmî belgeden okur, sonucu denetim/yz.json'a yazar (30 Ekim 2026).

Kullanıcının bilgisayarında zamanlanmış görevle çalışır (ücretsiz, kota yok). Sonuç Gemini dönemindeki yz.json şemasıyla
(yz_denetim.SURUM) yazılır; site ve Telegram yz_isle.uygula ile bu bilgileri kullanır, elle düzeltmeler yine üstte kalır.
Sınamada (#237'nin elle doğrulanmış 11 ilanı) gemma3:12b metinli belgelerde kadro/kişi/öğrenim/puanı doğru okudu,
taranmış (metinsiz) belgede uydurdu. Bu yüzden:
  - metni çıkmayan belge okutulmaz, 'taranmis' kaydı yazılır (ilan beklemeden botun verisiyle gider);
  - model ilanı durduramaz: akademik / iptal / düzeltme kararları alınmaz (bot kendi kurallarıyla verir);
  - botun bildiği son başvuru tarihi modelden gelenle değiştirilmez.
Bilgisayar kapalıysa ilan en çok 1 saat bekler, sonra botun verisiyle gider (yz_isle.EN_COK_BEKLEME).

Ayar (config.json): yz_yerel_acik, yz_yerel_model. Kullanım: python bot/yz_yerel.py [--en-cok 6] [--sure 25] [--deneme]"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLLAMA = os.environ.get('OLLAMA_ADRESI', 'http://localhost:11434').rstrip('/')
VARSAYILAN_MODEL = 'gemma3:12b'
EN_AZ_METIN = 400          # PDF'ten bundan az metin çıkıyorsa belge taranmış sayılır
EN_COK_METIN = 40000       # bağlam (num_ctx 16384) taşmasın
YZ_YOLU = 'denetim/yz.json'

# Gemini istemi (yz_denetim.ISTEM) ve boş bırakılabilir alanlı şemasıyla gemma3 kişi sayılarını, tarihleri ve özeti boş
# bıraktı, ortak koşullara 657/48 genel şartlarını doldurdu (30 Ekim sınaması). Kısa istem + zorunlu alanlı şema doğru okudu.
ISTEM = """Sen bir kamu personel alım ilanı okuyucususun. Aşağıdaki resmî ilan belgesini oku ve yalnız JSON döndür.
Kurallar:
- kadrolar: her ayrı kadro/pozisyon satırı için bir kayıt. unvan; adet (asil kişi sayısı, yedek sayma);
  ogrenim (ortaogretim/onlisans/lisans/yuksek_lisans); puan_turu (P3, P93, P94 gibi; yoksa null); en_dusuk_puan (yoksa null).
  Aynı unvan kadın/erkek ya da farklı bölüm/öğrenim için ayrı satırlardaysa unvanı ayırt et ("Zabıta Memuru — Kadın").
- kosullar: o kadroya ÖZEL başvuru koşulları (bölüm/mezuniyet, sertifika, ehliyet, deneyim, cinsiyet vb.). Kısa, açık
  Türkçe cümleler ("…mezun olmak" biçimi).
- ortak_kosullar: tüm kadrolar için geçerli önemli bilgiler, en çok 5 madde: yaş sınırı, boy-kilo şartı, başvuru yeri ve
  şekli, sınav tarihi ve usulü. Türk vatandaşlığı, kamu hakları, adli sicil, askerlik, sağlık gibi 657 sayılı Kanun genel
  şartlarını YAZMA.
- son_basvuru_tarihi ve baslangic_tarihi: başvuruların bittiği ve başladığı gün, YYYY-AA-GG. Sınav tarihi DEĞİL.
- toplam: asil kişi toplamı. ogrenim, puan_turleri: tüm ilan için. kpss_gerekli: KPSS puanı isteniyor mu.
- ozet: en çok 2 cümle: kim, kaç kişi, kimleri alıyor, başvuru nereden ve hangi tarihler arasında.
- okunabilirlik: belge okunabildiyse "iyi", kısmen "kismi", okunamadıysa "kotu".
- Belgede olmayan hiçbir bilgiyi ekleme; "belirtilmemiş" gibi dolgu maddeleri yazma. Kelimeleri doğru ayır."""

_OGRENIM = ['ortaogretim', 'onlisans', 'lisans', 'yuksek_lisans']
_DIZI = {'type': 'array', 'items': {'type': 'string'}}
SEMA = {'type': 'object', 'properties': {
    'kadrolar': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'unvan': {'type': 'string'}, 'adet': {'type': 'integer'}, 'ogrenim': {'type': 'string', 'enum': _OGRENIM},
        'puan_turu': {'type': ['string', 'null']}, 'en_dusuk_puan': {'type': ['number', 'null']}, 'kosullar': _DIZI},
        'required': ['unvan', 'adet', 'ogrenim', 'puan_turu', 'en_dusuk_puan', 'kosullar']}},
    'toplam': {'type': 'integer'},
    'son_basvuru_tarihi': {'type': 'string'}, 'baslangic_tarihi': {'type': 'string'},
    'ogrenim': {'type': 'array', 'items': {'type': 'string', 'enum': _OGRENIM}},
    'kpss_gerekli': {'type': 'boolean'}, 'puan_turleri': _DIZI,
    'ortak_kosullar': _DIZI, 'ozet': {'type': 'string'},
    'okunabilirlik': {'type': 'string', 'enum': ['iyi', 'kismi', 'kotu']}}}
SEMA['required'] = list(SEMA['properties'])

_DOLGU = re.compile(r'belirtilme|bilgi (?:yok|verilme)|^\s*(?:kadın\s*/\s*erkek|yok|-)\s*\.?\s*$'
                    r'|657|48 ?(?:inci|\.) madde|devlet memurları kanunu|türk vatandaşı|kamu haklarından|mahk[uû]m'
                    r'|ceza kanunu|askerlik|akıl hastalığı|sağlık durumu', re.I)


# ---------------------------------------------------------------- belge metni
def metin_al(item, sbb_pdf=None, csb_indir=None):
    """(metin, kaynak). kaynak: 'pdf', 'csb', 'metin', 'taranmis' (metin çıkmadı, okutulmaz) ya da 'bekle' (SBB belgesi
    bu bilgisayara henüz inmedi; sonraki çalışmada denenir)."""
    import yz_denetim as yd
    from sbb_detay import document_url
    pdf = sbb_pdf(item) if sbb_pdf else yd._yerel_pdf(item)
    if not pdf and document_url(item):
        return '', 'bekle'
    if pdf:
        from ek_kaynaklar import pdf_text
        try:
            metin = pdf_text(pdf)
        except Exception:
            metin = ''
        return (metin, 'pdf') if len(metin) >= EN_AZ_METIN else ('', 'taranmis')
    if item.get('kaynak_turu') == 'csb':
        import csb_kaynak
        indir = csb_indir or (lambda adres: csb_kaynak.indir(adres, csb_kaynak.BELGE_SINIRI, item.get('link')))
        parcalar = []
        for belge in (item.get('belgeler') or [])[:3]:
            adres = str(belge.get('link') or '')
            if not csb_kaynak.EK_ADRESI.match(adres):
                continue
            try:
                parcalar.append(csb_kaynak.belge_metni(adres, indir(adres)))
            except Exception as hata:
                print(f'Uyarı: ÇŞB belgesi indirilemedi ({type(hata).__name__}): {adres.rsplit("/", 1)[-1][:60]}')
        metin = '\n\n'.join(p for p in parcalar if p)
        if len(metin) >= EN_AZ_METIN:
            return metin, 'csb'
        if item.get('belgeler') and not metin:
            return '', 'taranmis'
    return yd.ham_metin(item), 'metin'


# ---------------------------------------------------------------- Ollama
def ollama(metin, model, baslik='', zaman_asimi=1800):
    govde = {'model': model, 'stream': False, 'format': SEMA,
             'options': {'temperature': 0, 'num_ctx': 16384},
             'messages': [{'role': 'user', 'content': ISTEM + '\n\nİlan kaynak sayfasındaki başlık: '
                           + str(baslik) + '\n\n--- BELGE ---\n' + metin[:EN_COK_METIN]}]}
    istek = urllib.request.Request(OLLAMA + '/api/chat', json.dumps(govde).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
        return json.loads(json.load(y)['message']['content'])


def calisiyor_mu(model):
    try:
        with urllib.request.urlopen(OLLAMA + '/api/tags', timeout=10) as y:
            adlar = {m.get('name') for m in json.load(y).get('models') or []}
    except (OSError, ValueError):
        return False
    return model in adlar or model + ':latest' in adlar


# ---------------------------------------------------------------- güvenli sonuç
def _maddeler(liste):
    return [m for m in (str(x).strip() for x in liste or []) if m and not _DOLGU.search(m)]


def temizle(yz, item):
    """Modelin çıktısını yayına güvenli hâle getirir (bkz. modül açıklaması)."""
    yz = dict(yz)
    yz.update(akademik=False, iptal_veya_duzeltme=False, duyuru_tipi='yeni_ilan')
    if item.get('son_tarih'):
        for alan in ('son_basvuru_tarihi', 'son_basvuru_saati', 'baslangic_tarihi'):
            yz.pop(alan, None)
    yz['ortak_kosullar'] = _maddeler(yz.get('ortak_kosullar'))
    kadrolar = []
    for k in yz.get('kadrolar') or []:
        k = dict(k, unvan=' '.join(str(k.get('unvan') or '').split()), kosullar=_maddeler(k.get('kosullar')))
        ayni = next((x for x in kadrolar if x['unvan'] == k['unvan'] and x['kosullar'] == k['kosullar']), None)
        if ayni and isinstance(ayni.get('adet'), int) and isinstance(k.get('adet'), int):
            ayni['adet'] += k['adet']   # ayırt edilmemiş aynı kadro satırları tek satır
        elif k['unvan']:
            kadrolar.append(k)
    yz['kadrolar'] = kadrolar
    if not kadrolar:
        yz['okunabilirlik'] = 'kotu'
        return yz
    # İlan geneli öğrenim/puan türü kadrolardan türetilir: model ilan genelinde fazladan düzey/puan türü sayabiliyor
    # (İzmir zabıta sınamasında ortaöğretim, yüksek lisans ve P94 eklemişti). Özet botunki kalır (başvuru yerini
    # yanlış yazdığı oldu).
    yz['ogrenim'] = sorted({k['ogrenim'] for k in kadrolar if k.get('ogrenim') in ('lisans', 'onlisans', 'ortaogretim')})
    yz['puan_turleri'] = sorted({str(k['puan_turu']) for k in kadrolar if k.get('puan_turu')})
    yz.pop('ozet', None)
    return yz


def kayit(item, yz, kaynak, model, simdi):
    import yz_denetim as yd
    return {'zaman': simdi.isoformat(timespec='seconds'), 'surum': yd.SURUM, 'model': 'ollama:' + model,
            'kaynak': kaynak, 'imza': yd.imza(item), 'baslik': item.get('baslik'),
            'farklar': yd.karsilastir(item, yz), 'yz': yz}


def taranmis_kaydi(item, model, simdi):
    return kayit(item, {'kadrolar': [], 'ogrenim': [], 'puan_turleri': [], 'ortak_kosullar': [], 'akademik': False,
                        'iptal_veya_duzeltme': False, 'okunabilirlik': 'kotu'}, 'taranmis', model, simdi)


# ---------------------------------------------------------------- akış
def oku(ilanlar, bekleyen, veri, model, simdi, en_cok=6, sure_dk=25, cagir=None, metin=None):
    """Sırayla okur; {kimlik: kayıt} döner (veri yerinde güncellenir)."""
    import yz_isle
    cagir = cagir or ollama
    metin = metin or metin_al
    yeni, bitis = {}, time.monotonic() + sure_dk * 60
    for item in yz_isle.adaylar(ilanlar, bekleyen, veri, simdi)[:en_cok]:
        if time.monotonic() > bitis:
            print('Süre doldu; kalanlar sonraki çalışmada.')
            break
        govde, kaynak = metin(item)
        if kaynak == 'bekle':
            continue
        if kaynak == 'taranmis':
            yeni[item['id']] = taranmis_kaydi(item, model, simdi)
            print(f'Taranmış belge, okutulmadı: {item.get("kurum")} — {str(item.get("baslik"))[:60]}')
            continue
        t = time.monotonic()
        try:
            yz = temizle(cagir(govde, model, item.get('baslik')), item)
        except Exception as hata:
            print(f'Uyarı: {item.get("kurum")} okunamadı: {str(hata)[:200]}')
            continue
        yeni[item['id']] = kayit(item, yz, kaynak, model, simdi)
        print(f'Okundu ({time.monotonic() - t:.0f} sn): {item.get("kurum")} — {str(item.get("baslik"))[:60]} ({kaynak})')
    veri.update(yeni)
    return yeni


def birlestir(uzak, yeni):
    """Kayıt başına en yeni okuma kalır (veri_kaydet.ek_dosyalari_birlestir ile aynı kural)."""
    sonuc = dict(uzak)
    for k, v in yeni.items():
        if str(v.get('zaman') or '') >= str((uzak.get(k) or {}).get('zaman') or ''):
            sonuc[k] = v
    return dict(sorted(sonuc.items()))


def _kilit():
    yol = ROOT / 'local-data' / 'yz-yerel.kilit'
    yol.parent.mkdir(exist_ok=True)
    try:
        if time.time() - yol.stat().st_mtime < 3 * 3600:
            return None
    except OSError:
        pass
    yol.write_text(str(os.getpid()), encoding='utf-8')
    return yol


def main():
    from site_uret import TR
    from yerel_tara import github, decode
    p = argparse.ArgumentParser()
    p.add_argument('--en-cok', type=int, default=6)
    p.add_argument('--sure', type=int, default=25, help='dakika')
    p.add_argument('--deneme', action='store_true', help="GitHub'a yazmaz")
    a = p.parse_args()
    token = os.environ.get('KAMU_GITHUB_TOKEN', '')
    if not token:
        from yerel_guvenlik import load_token
        token = load_token()
    cfg = decode(github('config.json', token=token), token)
    if not cfg.get('yz_yerel_acik'):
        print('Yerel yapay zekâ kapalı (config yz_yerel_acik).')
        return
    model = cfg.get('yz_yerel_model') or VARSAYILAN_MODEL
    if not calisiyor_mu(model):
        print(f'Ollama çalışmıyor ya da {model} kurulu değil; atlandı.')
        return
    kilit = _kilit()
    if not kilit:
        print('Önceki çalışma sürüyor; atlandı.')
        return
    try:
        kayitlar = decode(github('docs/ilanlar.json', token=token), token)
        try:
            veri = decode(github(YZ_YOLU, token=token), token)
        except RuntimeError:
            veri = {}
        yeni = oku(kayitlar.get('ilanlar') or [], set(kayitlar.get('telegram_bekleyen') or []), veri, model,
                   datetime.now(TR), a.en_cok, a.sure)
        if not yeni or a.deneme:
            print(f'Yerel yapay zekâ: {len(yeni)} ilan okundu' + (' (deneme, yazılmadı).' if yeni else '.'))
            return
        from github_yayin import publish_files
        try:
            uzak = decode(github(YZ_YOLU, token=token), token)
        except RuntimeError:
            uzak = {}
        icerik = json.dumps(birlestir(uzak, yeni), ensure_ascii=False, indent=1) + '\n'
        publish_files({YZ_YOLU: icerik.encode()}, token, f'Yerel yapay zekâ {len(yeni)} ilanı okudu [skip ci]')
        print(f'Yerel yapay zekâ: {len(yeni)} ilan okundu ve GitHub’a yazıldı.')
    finally:
        kilit.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if sys.stdout is None:   # pythonw (zamanlanmış görev): çıktı günlüğe
        gunluk = ROOT / 'local-data' / 'yz-yerel.log'
        gunluk.parent.mkdir(exist_ok=True)
        if gunluk.exists() and gunluk.stat().st_size > 1_000_000:
            gunluk.replace(gunluk.with_suffix('.onceki.log'))
        sys.stdout = sys.stderr = gunluk.open('a', encoding='utf-8', buffering=1)
    print('Yerel yapay zekâ:', datetime.now().isoformat(timespec='seconds'), flush=True)
    try:
        main()
    except Exception as hata:
        print(f'Yerel yapay zekâ tamamlanamadı: {type(hata).__name__}: {str(hata)[:200]}')
        raise SystemExit(1)
