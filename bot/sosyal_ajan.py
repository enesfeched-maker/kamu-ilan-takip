"""Sosyal medya ajanı: ölçüm özeti, haftalık rapor, yorum bildirimi ve sınırlı ayar kararları.

Paylaşımı bot yapar (sosyal_motor / reels); ajan yalnız takip eder ve dar bir ayar kümesini değiştirir:
  rapor    haftalık özeti yöneticiye Telegram özel mesajla gönderir (sosyal-ajan.yml, pazartesi)
  yorum    Instagram'daki yeni yorumları yöneticiye bildirir; yorum metni depoya YAZILMAZ (depo herkese açık)
  hazirla  Claude bulut rutini için sosyal-is/durum.json yazar (son paylaşımlar, ölçümler, geçerli ayar)
  kaydet   rutinin sosyal-is/karar.json çıktısını denetleyip sosyal/ayar.json ve sosyal/ajan-gunlugu.md'ye işler
  dogrula  sosyal/ayar.json geçerli mi (sosyal-ajan-* dalı main'e alınmadan önce)

Ayar sınırları AYAR_SINIR'dadır; sınır dışı ya da tanınmayan değer yok sayılır, bot varsayılanla çalışır."""
import json
import os
import statistics
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AYAR_YOLU = ROOT / 'sosyal' / 'ayar.json'
GUNLUK_YOLU = ROOT / 'sosyal' / 'ajan-gunlugu.md'
IS_KLASORU = ROOT / 'sosyal-is'
# ad: (varsayılan, en az, en çok). ilan_gunluk üst sınırı YouTube yükleme kotasından gelir (günde ~6 video, 2'si sabah/akşam).
AYAR_SINIR = {'ilan_gunluk': (3, 1, 4), 'son_gun_ufuk': (3, 1, 5), 'ozet_en_az': (2, 2, 4)}
SORU_TURLERI = ('genel', 'son_gun', 'ilan', 'ozet')
SORU_EN_COK, SORU_UZUNLUK = 3, 90
YASAK = ('kaçırma', 'hemen', 'şok', 'müjde', 'garanti', 'kesin atan')   # sosyal/voice.md "Söylenmez"
OLCUTLER = ('views', 'reach', 'likes', 'comments', 'saved', 'shares')
TUR_ADI = {'son_gun': 'Son gün', 'ilan': 'Tek ilan', 'ozet': 'Akşam özeti', 'yeni': 'Yeni ilanlar', 'buyuk': 'Büyük alım',
           'kategori': 'Kategori', 'rehber': 'Rehber', 'haber': 'Haber'}


# ---------------------------------------------------------------- ayar
def ayar_temizle(ham):
    """Yalnız tanınan ve sınır içindeki alanlar; geçersiz olan atılır. (temiz ayar, atılanların açıklaması) döner."""
    temiz, atilan = {}, []
    ham = ham if isinstance(ham, dict) else {}
    for ad, deger in ham.items():
        if ad in AYAR_SINIR:
            _, alt, ust = AYAR_SINIR[ad]
            if isinstance(deger, int) and not isinstance(deger, bool) and alt <= deger <= ust:
                temiz[ad] = deger
            else:
                atilan.append(f'{ad}={deger!r} (izin verilen {alt}–{ust})')
        elif ad == 'sorular' and isinstance(deger, dict):
            sorular = {}
            for tur, liste in deger.items():
                if tur not in SORU_TURLERI or not isinstance(liste, list):
                    atilan.append(f'sorular.{tur}')
                    continue
                uygun = [s.strip() for s in liste if isinstance(s, str) and 10 <= len(s.strip()) <= SORU_UZUNLUK
                         and '?' in s and not any(y in s.replace('İ', 'i').replace('I', 'ı').lower() for y in YASAK)]
                if len(uygun) != len(liste):
                    atilan.append(f'sorular.{tur}: {len(liste) - len(uygun)} cümle (uzunluk, soru işareti ya da yasak söz)')
                if uygun:
                    sorular[tur] = uygun[:SORU_EN_COK]
            if sorular:
                temiz['sorular'] = sorular
        else:
            atilan.append(f'{ad} (tanınmayan alan)')
    return temiz, atilan


def ayar_oku(yol=None):
    try:
        return ayar_temizle(json.loads(Path(yol or AYAR_YOLU).read_text(encoding='utf-8')))[0]
    except (OSError, ValueError):
        return {}


def ayar(ad, yol=None):
    """Tek sayısal ayar; dosyada yoksa ya da geçersizse varsayılan."""
    return ayar_oku(yol).get(ad, AYAR_SINIR[ad][0])


def sorular(tur, yol=None):
    """Ajanın o tür için yazdığı kapanış soruları; yoksa None (bot kendi listesini kullanır)."""
    return (ayar_oku(yol).get('sorular') or {}).get(tur)


# ---------------------------------------------------------------- ölçüm özeti
def _zaman(iso):
    try:
        z = datetime.fromisoformat(iso or '')
    except ValueError:
        return None
    from site_uret import TR
    return z if z.tzinfo else z.replace(tzinfo=TR)


def donem(gecmis, bas, son):
    """[bas, son) aralığındaki paylaşımların toplamları ve tür kırılımı."""
    kayitlar = [g for g in gecmis if (_zaman(g.get('zaman')) or son) >= bas and (_zaman(g.get('zaman')) or son) < son]
    olculen = [g for g in kayitlar if g.get('ig')]
    toplam = {o: sum(g['ig'].get(o) or 0 for g in olculen) for o in OLCUTLER}
    turler = {}
    for g in olculen:
        turler.setdefault(g.get('tur') or '?', []).append(g['ig'].get('views') or g['ig'].get('reach') or 0)
    return {'paylasim': len(kayitlar), 'olculen': len(olculen), 'toplam': toplam,
            'tur': {t: {'adet': len(v), 'medyan': round(statistics.median(v))} for t, v in turler.items()},
            'en_iyi': max(olculen, key=lambda g: g['ig'].get('views') or g['ig'].get('reach') or 0, default=None)}


def _fark(yeni, eski):
    if not eski:
        return ''
    oran = round(100 * (yeni - eski) / eski)
    return f' ({"+" if oran >= 0 else ""}{oran}%)'


def rapor_metni(gecmis, simdi, not_=''):
    """Son 7 gün ile önceki 7 günün karşılaştırması; ölçüm yoksa bunu açıkça yazar."""
    bu = donem(gecmis, simdi - timedelta(days=7), simdi)
    onceki = donem(gecmis, simdi - timedelta(days=14), simdi - timedelta(days=7))
    s = ['KPSS Tercihi — haftalık sosyal medya özeti', f'{bu["paylasim"]} paylaşım (önceki hafta {onceki["paylasim"]})']
    if not bu['olculen']:
        s.append('Bu haftanın paylaşımları için henüz Instagram ölçümü yok.')
    else:
        t, o = bu['toplam'], onceki['toplam']
        s.append(f'İzlenme: {t["views"]}{_fark(t["views"], o["views"])} · Erişim: {t["reach"]}{_fark(t["reach"], o["reach"])}')
        s.append(f'Beğeni {t["likes"]} · Yorum {t["comments"]} · Kaydetme {t["saved"]} · Paylaşma {t["shares"]}')
        sirali = sorted(bu['tur'].items(), key=lambda kv: -kv[1]['medyan'])
        s.append('Biçime göre medyan izlenme: ' + ', '.join(f'{TUR_ADI.get(t_, t_)} {v["medyan"]} ({v["adet"]} video)' for t_, v in sirali))
        iyi = bu['en_iyi']
        if iyi:
            s.append(f'En çok izlenen: {TUR_ADI.get(iyi.get("tur"), iyi.get("tur"))}, {(_zaman(iyi["zaman"])).strftime("%d.%m %H:%M")}, '
                     f'{iyi["ig"].get("views") or iyi["ig"].get("reach") or 0} izlenme')
    if not_:
        s += ['', 'Ajanın notu: ' + not_]
    s.append('Ölçümler yalnız Instagram içindir; TikTok ve YouTube sayıları henüz okunmuyor.')
    return '\n'.join(s)


def son_not(yol=None):
    """Günlükteki en son kararın gerekçesi (başlık satırından sonraki paragraf)."""
    try:
        bolumler = Path(yol or GUNLUK_YOLU).read_text(encoding='utf-8').split('\n## ')
    except OSError:
        return ''
    return ' '.join(bolumler[-1].split('\n')[1:]).strip()[:600] if len(bolumler) > 1 else ''


def _telegram(metin):
    import bekci
    token, sohbet = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip(), os.environ.get('TELEGRAM_YONETICI_ID', '').strip()
    if not (token and sohbet):
        print('Uyarı: TELEGRAM_BOT_TOKEN / TELEGRAM_YONETICI_ID tanımlı değil; mesaj gönderilmedi.\n' + metin)
        return False
    return bekci.telegram(token, sohbet, metin[:3900])


# ---------------------------------------------------------------- yorum bildirimi
YORUM_YAS = timedelta(hours=36)     # yalnız bu kadar yeni yorumlar bildirilir (ilk çalışmada eski yorum yağmasın)
YORUM_MEDYA_GUN = 14


def yeni_yorumlar(yorumlar, gorulen, simdi):
    """yorumlar: [{'id','text','username','timestamp', 'medya'}]. Görülmemiş ve YORUM_YAS'tan yeni olanlar."""
    sonuc = []
    for y in yorumlar:
        try:
            z = datetime.strptime(y.get('timestamp', ''), '%Y-%m-%dT%H:%M:%S%z')
        except ValueError:
            continue
        if y.get('id') and y['id'] not in gorulen and simdi - z <= YORUM_YAS and (y.get('text') or '').strip():
            sonuc.append(y)
    return sonuc


def yorum_mesaji(y):
    return (f'Instagram\'da yeni yorum\n@{y.get("username") or "?"}: {(y.get("text") or "").strip()[:500]}\n'
            + (f'Video: {y["baglanti"]}' if y.get('baglanti') else ''))


def yorumlari_bildir(simdi=None, durum_yolu='sosyal-yorum-durum.json'):
    from sosyal_motor import gecmis_oku
    from sosyal_yayinla import IG_SURUM, YayinHatasi, _env, _istek
    from site_uret import TR
    kimlik = _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI')
    if not kimlik:
        print('Instagram anahtarı tanımlı değil; yorumlar atlandı.')
        return 0
    anahtar = urllib.parse.quote(kimlik[1])
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    try:
        durum = json.loads(Path(durum_yolu).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        durum = {}
    gorulen = set(durum.get('gorulen') or [])
    medyalar = [g['ig_id'] for g in gecmis_oku() if g.get('ig_id') and (_zaman(g.get('zaman')) or simdi) >= simdi - timedelta(days=YORUM_MEDYA_GUN)]
    gonderilen = 0
    for medya in medyalar:
        try:
            yanit = _istek(f'https://graph.instagram.com/{IG_SURUM}/{medya}/comments?fields=id,text,username,timestamp&access_token={anahtar}')
        except YayinHatasi as hata:
            if not durum.get('izin_uyarisi'):   # izin yoksa her medya aynı hatayı verir: bir kez haber ver, dur
                _telegram('Instagram yorumları okunamadı. Uygulamaya yorum yönetimi izni (instagram_business_manage_comments) '
                          f'verilmemiş olabilir.\n{str(hata)[:200]}')
                durum['izin_uyarisi'] = simdi.isoformat(timespec='seconds')
            print(f'Uyarı: yorumlar okunamadı: {hata}')
            break
        durum.pop('izin_uyarisi', None)
        yeni = yeni_yorumlar(yanit.get('data') or [], gorulen, simdi)
        baglanti = ''
        if yeni:
            try:
                baglanti = _istek(f'https://graph.instagram.com/{IG_SURUM}/{medya}?fields=permalink&access_token={anahtar}').get('permalink') or ''
            except YayinHatasi:
                pass
        for y in yeni:
            if _telegram(yorum_mesaji(dict(y, baglanti=baglanti))):
                gonderilen += 1
        gorulen.update(y['id'] for y in (yanit.get('data') or []) if y.get('id'))
    durum['gorulen'] = sorted(gorulen)[-2000:]
    Path(durum_yolu).write_text(json.dumps(durum), encoding='utf-8')
    print(f'{len(medyalar)} video tarandı, {gonderilen} yeni yorum bildirildi.')
    return gonderilen


# ---------------------------------------------------------------- Claude rutini: hazırla / kaydet
def hazirla(simdi=None, klasor=None):
    from sosyal_motor import GECMIS_YOLU, gecmis_oku, istatistik_oku
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    gecmis = gecmis_oku()
    son = [{k: g.get(k) for k in ('zaman', 'vakit', 'tur', 'muzik', 'ig')} for g in gecmis
           if (_zaman(g.get('zaman')) or simdi) >= simdi - timedelta(days=30)]
    durum = {'zaman': simdi.isoformat(timespec='seconds'),
             'bu_hafta': {k: v for k, v in donem(gecmis, simdi - timedelta(days=7), simdi).items() if k != 'en_iyi'},
             'onceki_hafta': {k: v for k, v in donem(gecmis, simdi - timedelta(days=14), simdi - timedelta(days=7)).items() if k != 'en_iyi'},
             'agirliklar': istatistik_oku(Path(GECMIS_YOLU).parent / 'istatistik.json'), 'gecerli_ayar': ayar_oku(),
             'ayar_sinirlari': {ad: {'varsayilan': v[0], 'en_az': v[1], 'en_cok': v[2]} for ad, v in AYAR_SINIR.items()},
             'soru_turleri': list(SORU_TURLERI), 'son_30_gun': son}
    klasor = Path(klasor or IS_KLASORU)
    klasor.mkdir(parents=True, exist_ok=True)
    (klasor / 'durum.json').write_text(json.dumps(durum, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(son)} paylaşım, {durum["bu_hafta"]["olculen"]} ölçüm (bu hafta) -> {klasor / "durum.json"}')
    return durum


def kaydet(simdi=None, klasor=None, ayar_yolu=None, gunluk_yolu=None):
    """karar.json: {"ayar": {...}, "not": "gerekçe"}. Geçersiz alanlar atılır; not boşsa hiçbir şey yazılmaz (False)."""
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    try:
        karar = json.loads((Path(klasor or IS_KLASORU) / 'karar.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as hata:
        print(f'Atlandı: karar.json okunamadı: {hata}')
        return False
    not_ = ' '.join(str(karar.get('not') or '').split())[:600]
    if len(not_) < 20:
        print('Atlandı: "not" alanı boş ya da çok kısa (en az 20 karakter gerekçe yaz).')
        return False
    temiz, atilan = ayar_temizle(karar.get('ayar'))
    for a in atilan:
        print('Atlandı:', a)
    ayar_yolu, gunluk_yolu = Path(ayar_yolu or AYAR_YOLU), Path(gunluk_yolu or GUNLUK_YOLU)
    ayar_yolu.write_text(json.dumps(temiz, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    eski = gunluk_yolu.read_text(encoding='utf-8') if gunluk_yolu.exists() else '# Sosyal medya ajanı günlüğü\n'
    girdiler = eski.split('\n## ')
    eski = '\n## '.join(girdiler[:1] + girdiler[1:][-25:])   # son 25 karar saklanır
    gunluk_yolu.write_text(eski.rstrip('\n') + f'\n\n## {simdi:%Y-%m-%d}\n{not_}\n\nAyar: `{json.dumps(temiz, ensure_ascii=False)}`\n', encoding='utf-8')
    print(f'Kaydedildi: {temiz}')
    return True


def dogrula(yol=None):
    """Dosyadaki her alan geçerli mi; sosyal-ajan-* dalı main'e alınmadan önce çalışır."""
    try:
        ham = json.loads(Path(yol or AYAR_YOLU).read_text(encoding='utf-8'))
    except OSError:
        return True
    except ValueError as hata:
        print(f'Geçersiz JSON: {hata}')
        return False
    temiz, atilan = ayar_temizle(ham)
    for a in atilan:
        print('Geçersiz:', a)
    return not atilan and temiz == ham


if __name__ == '__main__':
    komut = sys.argv[1] if len(sys.argv) > 1 else ''
    if komut == 'rapor':
        from sosyal_motor import gecmis_oku
        from site_uret import TR
        _telegram(rapor_metni(gecmis_oku(), datetime.now(TR), son_not()))
    elif komut == 'yorum':
        yorumlari_bildir()
    elif komut == 'hazirla':
        hazirla()
    elif komut == 'kaydet':
        sys.exit(0 if kaydet() else 1)
    elif komut == 'dogrula':
        sys.exit(0 if dogrula() else 1)
    else:
        sys.exit('Kullanım: sosyal_ajan.py rapor|yorum|hazirla|kaydet|dogrula')
