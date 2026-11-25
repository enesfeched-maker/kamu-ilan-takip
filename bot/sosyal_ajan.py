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
import re
import statistics
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AYAR_YOLU = ROOT / 'sosyal' / 'ayar.json'
GUNLUK_YOLU = ROOT / 'sosyal' / 'ajan-gunlugu.md'
IS_KLASORU = ROOT / 'sosyal-is'
# ad: (varsayılan, en az, en çok). ilan_gunluk üst sınırı YouTube yükleme kotasından gelir (günde ~6 video, 2'si sabah/akşam).
AYAR_SINIR = {'ilan_gunluk': (3, 1, 4), 'son_gun_ufuk': (3, 1, 5), 'ozet_en_az': (2, 2, 4)}
SORU_TURLERI = ('genel', 'son_gun', 'ilan', 'ozet', 'kimler', 'meslek', 'duzey')
SORU_EN_COK, SORU_UZUNLUK = 3, 90
YASAK = ('kaçırma', 'hemen', 'şok', 'müjde', 'garanti', 'kesin atan')   # sosyal/voice.md "Söylenmez"
OLCUTLER = ('views', 'reach', 'likes', 'comments', 'saved', 'shares')
TUR_ADI = {'kimler': 'Kimler başvurabilir', 'meslek': 'Meslek alımları', 'duzey': 'Öğrenime göre ilanlar', 'son_gun': 'Son gün', 'ilan': 'Tek ilan', 'ozet': 'Akşam özeti', 'yeni': 'Yeni ilanlar', 'buyuk': 'Büyük alım',
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
            + (f'Video: {y["baglanti"]}' if y.get('baglanti') else '')
            + (f'\n{y["sonuc_notu"]}' if y.get('sonuc_notu') else ''))


# ---------------------------------------------------------------- yorumlara otomatik yanıt (site asistanı)
ASISTAN_ADRES = 'https://bildirim.kpsstercihi.com/asistan'
YANITLANAN_TURLER = {'ilan', 'puan', 'sss', 'selam', 'tesekkur', 'kimlik'}
YANIT_UST_SINIR = 10          # bir çalışmada en çok bu kadar yanıt
YANIT_ARA_SN = 20
YANIT_UZUNLUK = 450
# Yöneticiye bırakılacak yorumlar: şikâyet, hakaret, sponsor/iş teklifi (küçük, bilerek kısa liste)
YANITSIZ_KELIMELER = ('şikayet', 'şikâyet', 'sikayet', 'rezalet', 'dolandırıcı', 'dolandirici', 'yalan', 'sponsor', 'işbirliği',
                      'isbirligi', 'iş birliği', 'reklam', 'iletişim', 'iletisim', 'dm', 'fiyat', 'ücret', 'ucret',
                      'küfür', 'salak', 'aptal', 'gerizekalı')
_EPOSTA = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_TELEFON = re.compile(r'(?<!\d)(?:\+?90[\s-]?)?0?\s?5\d{2}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)')
_AY = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
_uyku = time.sleep


class YorumIzinHatasi(Exception):
    pass


def yanitsiz_neden(metin):
    """Yorum otomatik yanıta uygun değilse nedenini, uygunsa '' döndürür."""
    kucuk = (metin or '').lower().replace('İ', 'i').replace('I', 'ı')
    if _EPOSTA.search(metin or '') or _TELEFON.search(metin or ''):
        return 'telefon/e-posta içeriyor'
    kelimeler = set(re.findall(r'[\wçğıöşü]+', kucuk))
    for k in YANITSIZ_KELIMELER:
        if (k in kelimeler) if len(k) <= 3 else (k in kucuk):
            return f'anahtar kelime: {k.strip()}'
    return ''


def _gun_yaz(tarih):
    try:
        d = datetime.strptime(str(tarih)[:10], '%Y-%m-%d')
    except ValueError:
        return ''
    return f'{d.day} {_AY[d.month]}'


def yanit_metni(sonuc):
    """/asistan/sor cevabından Instagram yanıt metni: ≤450 karakter, yalnız düz alan adı, emoji/etiket yok."""
    metin = sonuc.get('metin') or ''
    metin = re.sub(r'https?://\S+|www\.\S+', '', metin)
    # çıplak alan adı/yol da (t.me/..., kpsstercihi.com/nereye/) bağlantı sayılır; yalnız sondaki düz alan adı kalır
    metin = re.sub(r'\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|org|me|tr|io|ly)\b(?:/\S*)?', '', metin, flags=re.I)
    metin = re.sub(r'#\w+', '', metin)
    metin = ''.join(c for c in metin if ord(c) < 0x10000 and c not in '‍️' and not 0x2600 <= ord(c) <= 0x27BF)
    metin = re.sub(r'[ \t]+', ' ', metin).strip()
    satirlar = []
    for i in (sonuc.get('ilanlar') or [])[:3]:
        kurum = re.sub(r'\s+', ' ', str(i.get('kurum') or '')).strip()[:40]
        gun = _gun_yaz(i.get('son_tarih'))
        if kurum and gun:
            satirlar.append(f'• {kurum} – son gün {gun}')
    son = " Ayrıntılar kpsstercihi.com'da." if (satirlar or sonuc.get('baglantilar')) else ''
    ek = ('\n' + '\n'.join(satirlar) if satirlar else '') + son
    pay = YANIT_UZUNLUK - len(ek)
    if len(metin) > pay:
        metin = metin[:max(pay - 1, 0)].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'
    return (metin + ek).strip()


def _asistan_istek(yol, govde, anahtar):
    from sosyal_yayinla import _istek
    return _istek(f'{ASISTAN_ADRES}/{yol}', json_veri=govde, basliklar={'X-Asistan-Anahtar': anahtar, 'User-Agent': 'kpsstercihi-sosyal-ajan'},
                  zaman_asimi=30)


def _durum_bildir(anahtar, kid, durum, gonderilen=''):
    if not (anahtar and kid):
        return
    try:
        _asistan_istek('durum', {'kid': kid, 'durum': durum, 'gonderilen': (gonderilen or '')[:1000]}, anahtar)
    except Exception as hata:  # kayıt yardımcıdır; akışı bozmaz
        print(f'Uyarı: asistan durumu bildirilemedi: {str(hata)[:120]}')


def _zaten_yanitlandi(yorum_id, ig_anahtar, kullanici_adi):
    """Yorumun altında hesabımızın yanıtı var mı? (durum dosyası kaybolsa da aynı yoruma ikinci kez yazılmasın.)
    Kontrol edilemezse True döner: emin olunamayan yoruma yanıt verilmez."""
    from sosyal_yayinla import IG_SURUM, _istek
    if not kullanici_adi:
        return True
    try:
        r = _istek(f'https://graph.instagram.com/{IG_SURUM}/{yorum_id}/replies?fields=username&access_token={ig_anahtar}')
    except Exception as hata:
        print(f'Uyarı: yorum yanıtları okunamadı: {str(hata)[:120]}')
        return True
    return any((x.get('username') or '').lower() == kullanici_adi for x in (r.get('data') or []))


def _yanit_gonder(yorum_id, mesaj, ig_anahtar):
    from sosyal_yayinla import IG_SURUM, YayinHatasi, _istek
    try:
        # ig_anahtar URL için kodlanmış gelir; form gövdesinde ikinci kez kodlanmasın
        _istek(f'https://graph.instagram.com/{IG_SURUM}/{yorum_id}/replies',
               veri={'message': mesaj, 'access_token': urllib.parse.unquote(ig_anahtar)}, yontem='POST')
    except YayinHatasi as hata:
        m = str(hata)
        if m.startswith(('HTTP 401', 'HTTP 403')) or 'ermission' in m or '(#10)' in m or '(#200)' in m:
            raise YorumIzinHatasi(m[:200]) from None
        raise


def yorumu_isle(y, medya, anahtar, ig_anahtar, kullanici_adi, yanit_acik):
    """Bir yorum için karar ver (+ yanıtla). (not_metni, yanit_gitti_mi) döndürür; izin hatasında YorumIzinHatasi."""
    neden = yanitsiz_neden(y.get('text'))
    if neden:
        return f'Yanıtlanmadı ({neden}) — sana bırakıldı.', False
    try:
        sonuc = _asistan_istek('sor', {'soru': (y.get('text') or '').strip()[:300], 'kanal': 'instagram',
                                       'meta': {'kullanici': y.get('username') or '', 'medya': medya, 'yorum_id': y.get('id')}}, anahtar)
    except Exception as hata:
        print(f'Uyarı: asistan cevap vermedi: {str(hata)[:120]}')
        return 'Yanıtlanmadı (asistana ulaşılamadı) — sana bırakıldı.', False
    kid, tur = sonuc.get('kid'), sonuc.get('tur')
    if tur not in YANITLANAN_TURLER:
        _durum_bildir(anahtar, kid, 'atlandi', f'tür: {tur}')
        return f'Yanıtlanmadı (asistan emin değil: {tur}) — sana bırakıldı.', False
    mesaj = yanit_metni(sonuc)
    if not mesaj:
        _durum_bildir(anahtar, kid, 'atlandi', 'boş cevap')
        return 'Yanıtlanmadı (boş cevap) — sana bırakıldı.', False
    if re.search(r'(?<![\d.,])0 (?:açık|ilan)', mesaj):
        # ilan listesi boş/okunamamış olabilir: herkese açık "0 açık ilan" yazılmaz
        _durum_bildir(anahtar, kid, 'atlandi', 'ilan sayısı 0')
        return 'Yanıtlanmadı (ilan listesi boş görünüyor) — sana bırakıldı.', False
    if not yanit_acik:
        _durum_bildir(anahtar, kid, 'atlandi', 'yanıt sınırı/kapalı')
        return 'Yanıtlanmadı (bu çalışmada yanıt sınırına varıldı) — sana bırakıldı.', False
    if _zaten_yanitlandi(y['id'], ig_anahtar, kullanici_adi):
        _durum_bildir(anahtar, kid, 'atlandi', 'zaten yanıtlanmış ya da denetlenemedi')
        return 'Yanıtlanmadı (yorumun altında zaten yanıtımız var ya da denetlenemedi) — sana bırakıldı.', False
    try:
        _yanit_gonder(y['id'], mesaj, ig_anahtar)
    except YorumIzinHatasi:
        _durum_bildir(anahtar, kid, 'hata', 'yanıt izni yok')
        raise
    except Exception as hata:
        _durum_bildir(anahtar, kid, 'hata', str(hata)[:200])
        return f'Yanıtlanmadı (gönderilemedi: {str(hata)[:80]}) — sana bırakıldı.', False
    _durum_bildir(anahtar, kid, 'yanitlandi', mesaj)
    return f'Yanıtlandı: {mesaj}', True


def yorumlari_bildir(simdi=None, durum_yolu='sosyal-yorum-durum.json'):
    from sosyal_motor import gecmis_oku
    from sosyal_yayinla import IG_SURUM, YayinHatasi, _env, _istek
    from site_uret import TR
    kimlik = _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI')
    if not kimlik:
        print('Instagram anahtarı tanımlı değil; yorumlar atlandı.')
        return 0
    anahtar = urllib.parse.quote(kimlik[1])
    asistan_anahtar = os.environ.get('ASISTAN_ANAHTAR', '').strip()
    yanit_acik = bool(asistan_anahtar) and os.environ.get('IG_YORUM_YANIT', '1').strip() != '0'
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    try:
        durum = json.loads(Path(durum_yolu).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        durum = {}
    gorulen = set(durum.get('gorulen') or [])
    kullanici_adi = ''
    if yanit_acik:
        try:
            kullanici_adi = (_istek(f'https://graph.instagram.com/{IG_SURUM}/me?fields=username&access_token={anahtar}').get('username') or '').lower()
        except YayinHatasi as hata:
            print(f'Uyarı: hesap adı alınamadı, yanıt verilmeyecek: {hata}')
            yanit_acik = False
    medyalar = [g['ig_id'] for g in gecmis_oku() if g.get('ig_id') and (_zaman(g.get('zaman')) or simdi) >= simdi - timedelta(days=YORUM_MEDYA_GUN)]
    gonderilen = yanit_sayisi = 0
    izin_yok = False
    for medya in medyalar:
        try:
            yanit = _istek(f'https://graph.instagram.com/{IG_SURUM}/{medya}/comments?fields=id,text,username,timestamp&access_token={anahtar}')
        except YayinHatasi as hata:
            m = str(hata)
            if '"error_subcode":33' in m or 'does not exist' in m:   # silinmiş/kaldırılmış video: atla, diğerlerine devam
                print(f'Uyarı: {medya} artık yok, atlandı.')
                continue
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
            not_ = ''
            if y.get('parent_id') or (kullanici_adi and (y.get('username') or '').lower() == kullanici_adi):
                continue   # kendi yorumumuz ya da zaten bir konunun yanıtı
            if yanit_acik and not izin_yok:
                if yanit_sayisi >= YANIT_UST_SINIR:
                    not_ = 'Yanıtlanmadı (bu çalışmada en çok 10 yanıt) — sana bırakıldı.'
                else:
                    try:
                        not_, gitti = yorumu_isle(y, medya, asistan_anahtar, anahtar, kullanici_adi, True)
                    except YorumIzinHatasi as hata:
                        izin_yok = True
                        not_ = 'Yanıtlanmadı (yanıt izni yok) — sana bırakıldı.'
                        if not durum.get('yanit_izin_uyarisi'):
                            _telegram('Instagram yorumlarına yanıt verilemedi: yorum yönetimi izni (instagram_business_manage_comments) '
                                      f'eksik olabilir. Bu çalışmada otomatik yanıt durduruldu.\n{str(hata)[:200]}')
                            durum['yanit_izin_uyarisi'] = simdi.isoformat(timespec='seconds')
                    else:
                        if gitti:
                            yanit_sayisi += 1
                            durum.pop('yanit_izin_uyarisi', None)
                            # yanıt gider gitmez kaydedilir: çalışma sonra yarıda kalsa da aynı yoruma ikinci yanıt gitmez
                            gorulen.add(y['id'])
                            durum['gorulen'] = sorted(gorulen)[-2000:]
                            Path(durum_yolu).write_text(json.dumps(durum), encoding='utf-8')
                            _uyku(YANIT_ARA_SN)
            elif yanit_acik and izin_yok:
                not_ = 'Yanıtlanmadı (yanıt izni yok) — sana bırakıldı.'
            if _telegram(yorum_mesaji(dict(y, baglanti=baglanti, sonuc_notu=not_))):
                gonderilen += 1
        gorulen.update(y['id'] for y in (yanit.get('data') or []) if y.get('id'))
    durum['gorulen'] = sorted(gorulen)[-2000:]
    Path(durum_yolu).write_text(json.dumps(durum), encoding='utf-8')
    print(f'{len(medyalar)} video tarandı, {gonderilen} yeni yorum bildirildi, {yanit_sayisi} yanıtlandı.')
    return gonderilen


SORU_EN_AZ_OLCUM = 3   # bir soru cümlesi en az bu kadar ölçülmüş videoda kullanılmadan "zayıf" sayılmaz


def soru_karnesi(gecmis, agirlik):
    """Kullanılmış her soru cümlesi: hangi türde, kaç ölçüm, ağırlık, medyan izlenme oranı ve değiştirilmeye aday mı
    (en az SORU_EN_AZ_OLCUM ölçüm ve eksi ağırlık). En zayıf önce."""
    turler = {}
    for g in gecmis:
        if g.get('soru'):
            turler.setdefault(g['soru'], set()).add(g.get('tur'))
    a, n, t = (agirlik or {}).get('soru') or {}, ((agirlik or {}).get('adet') or {}).get('soru') or {}, \
        ((agirlik or {}).get('tamamlama') or {}).get('soru') or {}
    karne = [{'soru': s, 'turler': sorted(x for x in tr if x), 'olcum': n.get(s, 0), 'agirlik': a.get(s),
              'izlenme_orani': t.get(s), 'degistir': n.get(s, 0) >= SORU_EN_AZ_OLCUM and (a.get(s) or 0) < 0}
             for s, tr in turler.items()]
    return sorted(karne, key=lambda k: (k['agirlik'] is None, k['agirlik'] if k['agirlik'] is not None else 0))


# ---------------------------------------------------------------- Claude rutini: hazırla / kaydet
def hazirla(simdi=None, klasor=None):
    from sosyal_motor import GECMIS_YOLU, gecmis_oku, istatistik_oku
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    gecmis = gecmis_oku()
    son = [{k: g.get(k) for k in ('zaman', 'vakit', 'tur', 'muzik', 'palet', 'soru', 'sure', 'seri', 'ig')} for g in gecmis
           if (_zaman(g.get('zaman')) or simdi) >= simdi - timedelta(days=30)]
    agirlik = istatistik_oku(Path(GECMIS_YOLU).parent / 'istatistik.json')
    durum = {'zaman': simdi.isoformat(timespec='seconds'),
             'bu_hafta': {k: v for k, v in donem(gecmis, simdi - timedelta(days=7), simdi).items() if k != 'en_iyi'},
             'onceki_hafta': {k: v for k, v in donem(gecmis, simdi - timedelta(days=14), simdi - timedelta(days=7)).items() if k != 'en_iyi'},
             'agirliklar': agirlik, 'gecerli_ayar': ayar_oku(),
             'ayar_sinirlari': {ad: {'varsayilan': v[0], 'en_az': v[1], 'en_cok': v[2]} for ad, v in AYAR_SINIR.items()},
             'soru_turleri': list(SORU_TURLERI), 'soru_karnesi': soru_karnesi(gecmis, agirlik), 'son_30_gun': son}
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
