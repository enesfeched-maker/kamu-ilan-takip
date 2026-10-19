"""Gemini ilanı baştan okur, kayıt sitede ve Telegram'da Gemini'nin okuduğu bilgilerle yayınlanır (19 Ekim 2026).

Akış (ilan.yml, bot taramasından hemen sonra):
  1. Telegram sırasındaki ve yeni/değişen açık ilanlar Gemini'ye okutulur (yz_denetim.parcalar/gemini) -> denetim/yz.json
  2. Logosu olmayan kurumların logosu internetten bulunur (yz_logo)
  3. site_uret.elle_uygula ve ilan_bot gönderimi uygula() ile Gemini alanlarını kaydın üzerine yazar
     (elle girilen düzeltmeler her zaman Gemini'nin üstündedir).
Telegram'a yalnız Gemini'nin okuduğu ilan gider (yayina_hazir); okunamayan (okunabilirlik 'kotu') ya da Gemini'nin
iptal/düzeltme ya da akademik dediği ilan kanala gitmez, Actions uyarısı verir.

Kullanım: python bot/yz_isle.py [--en-cok 8] [--logo 3]"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SONUC_YOLU = ROOT / 'denetim' / 'yz.json'
KADRO_SINIRI = 100000


# ---------------------------------------------------------------- sonuçlar
_ONBELLEK = {}


def sonuclar(yol=SONUC_YOLU):
    """denetim/yz.json (dosya değişmedikçe yeniden okunmaz)."""
    yol = Path(yol)
    try:
        damga = yol.stat().st_mtime_ns
    except OSError:
        return {}
    if _ONBELLEK.get(yol) and _ONBELLEK[yol][0] == damga:
        return _ONBELLEK[yol][1]
    try:
        veri = json.loads(yol.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        veri = {}
    _ONBELLEK[yol] = (damga, veri)
    return veri


def kayit_bul(item, veri=None):
    """Kaydın (ya da kaynaklar arası takma adlarından birinin) güncel sürümlü Gemini sonucu."""
    from yz_denetim import SURUM
    veri = sonuclar() if veri is None else veri
    for kimlik in [item.get('id'), *(item.get('kaynak_kimlikleri') or [])]:
        k = veri.get(kimlik)
        if k and k.get('surum', 0) >= SURUM and isinstance(k.get('yz'), dict):
            return k
    return None


# ---------------------------------------------------------------- Gemini -> kayıt alanları
def _tarih(deger):
    try:
        return date.fromisoformat(str(deger or '')[:10])
    except ValueError:
        return None


def _puan_turu(p):
    """'KPSS P3', 'KPSSP3', 'P3' -> 'P3' (ÖSYM'de KPSSP3 ile P3 aynı puan türü)."""
    p = re.sub(r'[\s-]+', '', str(p or '').upper())
    return p[4:] if re.fullmatch(r'KPSSP\d+', p) else p


def _il(ad):
    from siniflandir import ILLER, kucuk
    a = kucuk(re.split(r'[/(,-]', str(ad or ''))[0].strip())
    return next((il for il in ILLER if kucuk(il) == a), None)


def _kisa(m, sinir=140):
    m = ' '.join(str(m or '').split()).strip(' -•;')
    if not m or re.search(r'657 sayılı|48 ?(?:inci|\.) madde', m):
        return ''
    return m if len(m) <= sinir else m[:sinir - 1].rsplit(' ', 1)[0] + '…'


def alanlar(yz, item, simdi=None):
    """Gemini çıktısından kayda yazılacak alanlar. Mantıksız değer (geçmiş/uzak tarih, aşırı kişi sayısı) yazılmaz."""
    from site_uret import TR
    if not yz or yz.get('okunabilirlik') == 'kotu':
        return {}
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    sonuc = {'yz': True}
    ilk = _tarih(item.get('ilk_gorulme')) or simdi.date()
    son = _tarih(yz.get('son_basvuru_tarihi'))
    if son and ilk - timedelta(days=3) <= son <= ilk + timedelta(days=370):
        saat = yz.get('son_basvuru_saati') if re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', str(yz.get('son_basvuru_saati') or '')) else '23:59'
        sonuc['son_tarih'] = son.isoformat()
        sonuc['son_zaman'] = f'{son.isoformat()}T{saat}:00+03:00'
    bas = _tarih(yz.get('baslangic_tarihi'))
    if bas and son and bas <= son:
        sonuc['baslangic_zaman'] = f'{bas.isoformat()}T00:00:00+03:00'
    kadrolar = []
    for k in yz.get('kadrolar') or []:
        unvan = _kisa(k.get('unvan'), 90)
        if not unvan:
            continue
        adet = k.get('adet') if isinstance(k.get('adet'), int) and 0 < k['adet'] < KADRO_SINIRI else None
        kadrolar.append({'unvan': unvan, 'adet': adet, 'ogrenim': k.get('ogrenim'),
                         'puan_turu': _puan_turu(k.get('puan_turu')) or None, 'en_dusuk_puan': k.get('en_dusuk_puan'),
                         'il': _il(k.get('il')), 'kosullar': [m for m in map(_kisa, k.get('kosullar') or []) if m][:5]})
    if kadrolar:
        sonuc['yz_kadrolar'] = kadrolar
        adetler = [k['adet'] for k in kadrolar]
        if all(adetler):
            toplam = sum(adetler)
            sonuc['kadro'] = (f'{adetler[0]} {kadrolar[0]["unvan"]}' if len(kadrolar) == 1 else
                              f'Toplam {toplam} kişi — ' + ' • '.join(f'{k["adet"]} {k["unvan"]}' for k in kadrolar))
    ortak = [m for m in map(_kisa, yz.get('ortak_kosullar') or []) if m][:5]
    if ortak:
        sonuc['yz_ortak'] = ortak
    ogrenim = [o for o in yz.get('ogrenim') or [] if o in ('lisans', 'onlisans', 'ortaogretim')]
    if ogrenim:
        sonuc['ogrenim'] = sonuc['belge_ogrenim'] = sorted(set(ogrenim))
    if yz.get('kpss_gerekli') is True:
        sonuc['kpss'] = 'kpss'
    elif yz.get('kpss_gerekli') is False:
        sonuc['kpss'] = 'kpsssiz'
    puanlar = sorted({_puan_turu(p) for p in yz.get('puan_turleri') or [] if _puan_turu(p)})
    if puanlar:
        sonuc['puan_turleri'] = puanlar
    iller = sorted({i for i in map(_il, yz.get('iller') or []) if i})
    if iller:
        sonuc['iller'] = iller
    if yz.get('ozet') and 40 <= len(yz['ozet']) <= 400:
        sonuc['ozet'] = ' '.join(yz['ozet'].split())
    if yz.get('akademik'):
        sonuc['yz_akademik'] = True
    if yz.get('iptal_veya_duzeltme'):
        sonuc['yz_duyuru'] = True
        tip = DUYURU_TURU.get(yz.get('duyuru_tipi'))
        if tip and not item.get('duyuru_turu'):
            sonuc['duyuru_turu'] = tip   # sitede açık ilan gibi değil, duyuru olarak görünür
    return sonuc


DUYURU_TURU = {'iptal': 'İptal', 'duzeltme': 'Düzeltme / süre değişikliği', 'sure_uzatma': 'Düzeltme / süre değişikliği'}


def iptal_mi(item, veri=None):
    """Bot yeni ilan sanmış ama Gemini belgeyi iptal duyurusu olarak okumuşsa True."""
    k = kayit_bul(item, veri)
    return bool(k and not item.get('duyuru_turu') and k['yz'].get('duyuru_tipi') == 'iptal'
                and not k['yz'].get('akademik'))


def sure_uzatma_isaretle(item, veri=None):
    """Bot yeni ilan sanmış, Gemini süre uzatması okumuşsa kaydı düzeltme duyurusu yapar (yerinde); True döner.
    duzeltme.uygula orijinali bulur ve son gününü günceller; kanala orijinal mesaja 'Yeni son başvuru' yanıtı gider."""
    k = kayit_bul(item, veri)
    if not k or item.get('duyuru_turu'):
        return False
    yz = k['yz']
    if yz.get('duyuru_tipi') != 'sure_uzatma' or yz.get('akademik'):
        return False
    son, ilk = _tarih(yz.get('son_basvuru_tarihi')), _tarih(item.get('ilk_gorulme'))
    if not son or (ilk and not ilk <= son <= ilk + timedelta(days=370)):
        return False
    item['duyuru_turu'] = DUYURU_TURU['sure_uzatma']
    item['yz_yeni_son_tarih'] = son.isoformat()
    return True


def uygula(item, veri=None, simdi=None):
    """Kaydın Gemini alanlarıyla birleşmiş kopyası (Gemini sonucu yoksa kaydın kendisi)."""
    k = kayit_bul(item, veri)
    if not k:
        return item
    ek = alanlar(k['yz'], item, simdi)
    return dict(item, **ek) if ek else item


EN_COK_BEKLEME = timedelta(hours=1)   # kullanıcı kararı: yeni ilan Telegram'a en geç 1 saatte gitsin


def _bekleme_doldu(item, simdi=None):
    from site_uret import TR
    try:
        ilk = datetime.fromisoformat(item.get('ilk_gorulme') or '')
    except ValueError:
        return True
    ilk = ilk if ilk.tzinfo else ilk.replace(tzinfo=TR)
    return (simdi or datetime.now(TR)) - ilk >= EN_COK_BEKLEME


def yayina_hazir(item, veri=None, simdi=None):
    """(hazır mı, neden). Telegram'a Gemini'nin okuduğu ilan gider; Gemini (yoğunluk/kota) 1 saatte okuyamazsa ilan
    botun kendi bilgileriyle gider (gecikmesin), Gemini sonradan okuyunca site güncellenir."""
    if item.get('duyuru_turu'):
        k = kayit_bul(item, veri)   # iptal duyuruları gider (orijinal ilana yanıt); akademik ilana ait olan gitmez
        return (False, 'Gemini akademik ilan dedi') if k and k['yz'].get('akademik') else (True, '')
    k = kayit_bul(item, veri)
    if not k:
        return (True, '') if _bekleme_doldu(item, simdi) else (False, 'Gemini henüz okumadı; en çok 1 saat beklenir')
    yz = k['yz']
    if yz.get('okunabilirlik') == 'kotu':
        return (True, '') if _bekleme_doldu(item, simdi) else (False, 'Gemini belgeyi okuyamadı; en çok 1 saat beklenir')
    if yz.get('akademik'):
        return False, 'Gemini akademik ilan dedi'
    if iptal_mi(item, veri):
        return True, 'iptal'
    if yz.get('iptal_veya_duzeltme'):
        return False, 'Gemini düzeltme/süre uzatma duyurusu dedi (kanalda paylaşılmaz)'
    return True, ''


# ---------------------------------------------------------------- işleme
def adaylar(ilanlar, bekleyen, veri, simdi):
    """Önce Telegram sırasındakiler, sonra en yeni açık ilanlar; sonucu güncel olan ya da içeriği değişmeyen atlanır."""
    from siniflandir import akademik_ilan
    from yz_denetim import SURUM, imza
    secilen = []
    for i in ilanlar:
        if i.get('duyuru_turu') or akademik_ilan(i) or str(i.get('son_tarih') or '9999')[:10] < simdi.date().isoformat():
            continue
        k = veri.get(i['id'])
        if k and k.get('surum', 0) >= SURUM and k.get('imza') == imza(i):
            continue
        secilen.append(i)
    return sorted(secilen, key=lambda i: (i['id'] in bekleyen, i.get('ilk_gorulme') or ''), reverse=True)


def isle(en_cok=8, logo_en_cok=3, anahtar=None, simdi=None, yol=ROOT / 'docs' / 'ilanlar.json', sonuc_yolu=SONUC_YOLU,
         cagir=None, logo_bul=None):
    import yz_denetim as yd
    from site_uret import TR
    anahtar = anahtar or os.environ.get('GEMINI_ANAHTARI', '').strip()
    if not anahtar:
        print('GEMINI_ANAHTARI tanımlı değil; yapay zekâ adımı atlandı.')
        return None
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    veri_json = json.loads(Path(yol).read_text(encoding='utf-8'))
    ilanlar = veri_json.get('ilanlar') or []
    bekleyen = set(veri_json.get('telegram_bekleyen') or [])
    try:
        veri = json.loads(Path(sonuc_yolu).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        veri = {}
    cagir = cagir or yd.gemini
    sayac = {'okunan': 0, 'hata': 0, 'logo': 0}
    for item in adaylar(ilanlar, bekleyen, veri, simdi)[:en_cok]:
        try:
            parca, kaynak = yd.parcalar(item)
            yz = cagir(parca, anahtar)
        except yd.KotaDoldu:
            print('Gemini kotası doldu; kalanlar sonraki taramada.')
            break
        except Exception as hata:
            sayac['hata'] += 1
            print(f'Uyarı: {item.get("kurum")} okunamadı: {str(hata)[:300]}')
            if sayac['hata'] >= 2 and not sayac['okunan']:
                print('Gemini şu an yanıt vermiyor; kalanlar sonraki taramada.')
                break
            continue
        veri[item['id']] = {'zaman': simdi.isoformat(timespec='seconds'), 'surum': yd.SURUM, 'model': yd.MODEL,
                            'kaynak': kaynak, 'imza': yd.imza(item), 'baslik': item.get('baslik'),
                            'farklar': yd.karsilastir(item, yz), 'yz': yz}
        sayac['okunan'] += 1
        farklar = veri[item['id']]['farklar']
        print(f'Gemini okudu: {item.get("kurum")} — {str(item.get("baslik"))[:60]} ({kaynak})'
              + (f' · botla fark: {farklar}' if farklar else ''))
    Path(sonuc_yolu).parent.mkdir(parents=True, exist_ok=True)
    Path(sonuc_yolu).write_text(json.dumps(dict(sorted(veri.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    # logo: Telegram sırasında olup logosu bulunmayan kurumlar
    try:
        from kurum_gorseli import kurum_logosu
        import yz_logo
        logo_bul = logo_bul or yz_logo.logo_bul_ve_kaydet
        denenen = set()
        for item in [i for i in ilanlar if i['id'] in bekleyen and not i.get('duyuru_turu')]:
            if sayac['logo'] >= logo_en_cok or item.get('kurum') in denenen:
                continue
            denenen.add(item.get('kurum'))
            if kurum_logosu(item):
                continue
            if logo_bul(item, anahtar):
                sayac['logo'] += 1
    except Exception as hata:
        print(f'Uyarı: logo arama yapılamadı: {str(hata)[:200]}')
    print(f'Yapay zekâ: {sayac}')
    return sayac


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    p = argparse.ArgumentParser()
    p.add_argument('--en-cok', type=int, default=8)
    p.add_argument('--logo', type=int, default=3)
    a = p.parse_args()
    isle(a.en_cok, a.logo)
