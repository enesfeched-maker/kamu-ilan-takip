#!/usr/bin/env python3
"""Kariyer Kapısı RSS -> Telegram kanalı + docs/ilanlar.json (site verisi).

Görseller için Pillow kullanır. Ortam değişkenleri:
  TELEGRAM_BOT_TOKEN   BotFather'dan aldığın token
  TELEGRAM_CHAT_ID     Kanal kullanıcı adı (@kanaladi) veya sayısal id
"""
import argparse
import html
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from resmi_detay import detay_oku
from resmi_ag import url_ac
from ilan_gorsel import gorsel_olustur
from ek_kaynaklar import read_sbb, read_iskur, merge_sources, norm
from ilan_baglanti import ilan_sayfasi
from iptal_yaniti import (duz_anahtar, guclu_kokler, kadro_adi, kapsam_kokleri, kurum_kimligi, mesaj_kimligi,
                          orijinal_ara, paylasildi, resmi_cumle, tam_iptal, yanit_anahtarlari)
from sbb_detay import FIIL, _katla, belge_cumlesi
from kurum_gorseli import kurum_logosu
from siniflandir import akademik_ilan, etiketler, il_adlari, kategori, kpss_durumu, ogrenim_seviyeleri
from yerel_kaynak import oku as yerel_oku, sbb_verisi, csb_verisi

ROOT = Path(__file__).resolve().parent.parent
CONFIG_YOLU = ROOT / "config.json"
VERI_YOLU = ROOT / "docs" / "ilanlar.json"
TR = timezone(timedelta(hours=3))  # Türkiye saati (UTC+3, yaz saati yok)

AYLAR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def simdi():
    return datetime.now(TR)


# ---------------------------------------------------------------- RSS okuma
def indir(url):
    istek = urllib.request.Request(
        url, headers={"User-Agent": "kamu-ilan-takip/1.0 (topluluk projesi)"}
    )
    with url_ac(istek, timeout=30) as r:
        return r.read()


def duz_metin(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tarih_bul(metin):
    """Metindeki son başvuru tarihini bulur (23 Ocak 2026 veya 23.01.2026)."""
    kucuk = metin.lower()
    i = kucuk.find("son başvuru")
    if i < 0:
        return None  # Başlıktaki yayın/başlangıç tarihini son tarih sanma.
    parca = metin[i:]
    for m in re.finditer(r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", parca):
        ay = AYLAR.get(m.group(2).lower())
        if ay:
            try:
                return date(int(m.group(3)), ay, int(m.group(1))).isoformat()
            except ValueError:
                pass
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", parca)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    return None


def rss_coz(veri):
    """RSS (veya Atom) içeriğini ilan sözlüklerine çevirir."""
    kok = ET.fromstring(veri)
    ilanlar = []
    for el in kok.iter():
        ad = el.tag.split("}")[-1]
        if ad not in ("item", "entry"):
            continue
        alan = {}
        for c in el:
            k = c.tag.split("}")[-1]
            if k == "link" and c.get("href"):
                alan.setdefault("link", c.get("href"))
            elif c.text and c.text.strip():
                alan.setdefault(k, c.text.strip())
        baslik = duz_metin(alan.get("title"))
        aciklama = duz_metin(alan.get("description") or alan.get("summary") or alan.get("content"))
        link = alan.get("link") or alan.get("guid") or ""
        if not baslik or not link:
            continue
        kurum = duz_metin(alan.get("author") or alan.get("creator") or "")
        if not kurum and " - " in baslik:
            kurum = baslik.split(" - ", 1)[0].strip()
        ilanlar.append({
            "id": alan.get("guid") or link,
            "baslik": baslik,
            "kurum": kurum,
            "ilan_turu": duz_metin(alan.get("category")),
            "aciklama": aciklama,
            "link": link,
            "son_tarih": tarih_bul(baslik + " " + aciklama),
        })
    return ilanlar


# ----------------------------------------------------------------- Telegram
def kalan_gun_metni(son_tarih):
    if not son_tarih:
        return ""
    fark = (date.fromisoformat(son_tarih) - simdi().date()).days
    if fark < 0:
        return "süresi doldu"
    if fark == 0:
        return "bugün son gün"
    if fark == 1:
        return "yarın son gün"
    return f"{fark} gün kaldı"


def tarih_yaz(son_tarih):
    d = date.fromisoformat(son_tarih)
    ay = [k for k, v in AYLAR.items() if v == d.month][0].capitalize()
    return f"{d.day} {ay} {d.year}"


def okunakli_baslik(metin):
    """Tamamı büyük harfli metni Türkçe karakterleri koruyarak düzenler."""
    if not metin.isupper():
        return metin
    kisaltmalar = {"KPSS", "YDS", "YÖKDİL", "ALES", "İŞKUR", "TÜBİTAK", "TÜİK", "AFAD",
                   "MEB", "MSB", "SGK", "DSİ", "T.C", "T.C.", "J.GN.K.LIĞININ"}
    def kelime(m):
        s = m.group()
        if s in kisaltmalar or any(c.isdigit() for c in s):
            return s
        s = s.translate(str.maketrans("Iİ", "ıi")).lower()
        if s in {"ve", "ile", "veya"}:
            return s
        return s[0].translate(str.maketrans("iı", "İI")).upper() + s[1:]
    return re.sub(r"[\w./]+", kelime, metin)


def kisalt(metin, sinir):
    metin = re.sub(r"\s+", " ", metin).strip()
    if len(metin) <= sinir:
        return metin
    return metin[:sinir - 1].rsplit(" ", 1)[0] + "…"


def kisa_baslik(ilan):
    baslik = ilan['baslik']
    kurum = ilan.get('kurum', '')
    if kurum and baslik.startswith(kurum + ' - '):
        baslik = baslik[len(kurum) + 3:]
    elif kurum and baslik.startswith(kurum):
        baslik = baslik[len(kurum):].strip(' -–:')
    baslik = re.sub(r'\(\d{4}\)|\(\d{2}[./]\d{2}[./]\d{4}\)', '', baslik).strip()
    # Generic recruitment wording adds nothing when the actual positions are available.
    return kisalt(okunakli_baslik(baslik), 130)


def kadro_ozeti(ilan):
    parcalar = (ilan.get('kadro') or '').split(' • ')
    metin = ' • '.join(parcalar[:3])
    if len(parcalar) > 3:
        metin += f" • +{len(parcalar)-3} kadro türü"
    return ''.join(okunakli_baslik(s) for s in re.split(r'( • | — )', metin))


def mesaj_olustur(ilan, site_url, hatirlatma=False):
    e = html.escape
    kurum = ilan.get("kurum", "")
    satirlar = []
    if ilan.get('duyuru_turu'):
        satirlar.append(f"📌 <b>{e(ilan['duyuru_turu'])}</b>\n")
    if hatirlatma:
        satirlar.append(f"🔴 <b>{kalan_gun_metni(ilan['son_tarih']).capitalize()}</b>\n")
    satirlar.append(f"<b>{e(kisalt(okunakli_baslik(kurum or ilan['baslik']), 180))}</b>")
    baslik = kisa_baslik(ilan)
    genel_baslik = re.fullmatch(r'(?:4/[bB]\s+)?(?:Sözleşmeli\s+)?Personel\s+Alım(?:ı)?(?:\s+İlanı)?', baslik, re.IGNORECASE)
    if not ilan.get('kadro') and kurum and not genel_baslik:
        satirlar.append(e(baslik))
    for alan, etiket, sinir in [("kadro", "👥", 220), ("yer", "📍", 100)]:
        if ilan.get(alan):
            deger = kadro_ozeti(ilan) if alan == 'kadro' else okunakli_baslik(ilan[alan])
            satirlar.append(f"{etiket} {e(kisalt(deger, sinir))}")
    if ilan.get("son_tarih"):
        saat = ""
        if ilan.get("son_zaman"):
            saat = " • " + datetime.fromisoformat(ilan['son_zaman']).strftime('%H:%M') + " (TSİ)"
        satirlar.append(f"📅 <b>Son başvuru:</b> {tarih_yaz(ilan['son_tarih'])}{saat}")
    else:
        satirlar.extend(["", "⏳ <b>Son başvuru:</b> Resmi ilan üzerinden kontrol edin."])
    satirlar.extend(["", "İlan ayrıntıları ve başvuru bilgileri sitemizde ↓"])
    if ilan.get('kaynak_turu') in ('sbb','iskur','csb'):
        satirlar.append(f"<i>Kaynak: {e(ilan['kaynak'])}</i>")
    etiket = " ".join(etiketler(ilan))
    if etiket:
        satirlar.extend(["", e(etiket)])
    return "\n".join(satirlar)


def duyuru_turu_iptal_mi(duyuru):
    return 'iptal' in norm(duyuru.get('duyuru_turu'))


_CUMLE_ONEKI = re.compile(r'(?:yayımlanan|yayınlanan|istinaden)\s+(?:ve\s+)?(?:aşağıda\s+belirtilen\s+)?', re.I)
_CUMLE_KURUM = re.compile(r'\S+(?:ndan|nden):\s*(?:[A-ZÇĞİÖŞÜ ]+İLANI\s*:?\s*)?')


def _bas_harf_buyut(metin):
    return metin[:1].translate(str.maketrans('iı', 'İI')).upper() + metin[1:] if metin else metin


def resmi_cumle_kisa(d, sinir=280):
    """Duyurunun resmi işlem cümlesi, kurum/Resmi Gazete önekinden arındırılmış ve kısaltılmış hâliyle; yoksa ''."""
    c = resmi_cumle(d)
    if not c:
        return ''
    fiil = FIIL.search(_katla(c))
    onceki = c[:fiil.start()] if fiil else c
    ms = list(_CUMLE_ONEKI.finditer(onceki))
    if ms:
        c = c[ms[-1].end():]
    else:
        m = _CUMLE_KURUM.search(c)
        if m:
            c = c[m.end():]
    c = c.strip()
    return kisalt(_bas_harf_buyut(c), sinir) if c else ''


def duyuru_metni(duyuru, orijinale_yanit, tam=True, referans=None):
    """İptal/düzeltme duyurusu mesajı. Orijinal ilana yanıtsa kısa, değilse kurum ve başlıkla kartsız metin.
    tam=False: iptal ilanın yalnız bir kadrosunu kapsıyor ('Bu ilandaki Tekniker alımı iptal edilmiştir').
    referans: kanalda paylaşılmış ama mesaj kaydı olmayan orijinal ilan (yanıt verilemez, 📌 satırıyla gösterilir)."""
    e = html.escape
    iptal = duyuru_turu_iptal_mi(duyuru)
    satirlar = []
    kadro = okunakli_baslik(kadro_adi(duyuru)) if iptal else ''
    cumle = resmi_cumle_kisa(duyuru)
    if orijinale_yanit:
        if iptal and not tam:
            satirlar.append(f"❌ <b>Bu ilandaki {e(kadro or 'bazı kadroların')} alımı iptal edilmiştir.</b>")
        else:
            satirlar.append("❌ <b>Bu ilan iptal edilmiştir.</b>" if iptal else "📝 <b>Bu ilanda düzeltme yapıldı.</b>")
        if cumle:
            satirlar.append(e(cumle))
        if not iptal and duyuru.get('son_tarih'):
            satirlar.append(f"📅 <b>Yeni son başvuru:</b> {tarih_yaz(duyuru['son_tarih'])}")
    else:
        kurum = okunakli_baslik(duyuru.get('kurum') or '') or kisa_baslik(duyuru)
        satirlar.append(f"{'❌ <b>İptal duyurusu:</b>' if iptal else '📝 <b>Düzeltme duyurusu:</b>'} {e(kurum)}")
        if referans:
            gun = str(referans.get('ilk_gorulme') or '')[:10]
            try:
                tarih = f" — {tarih_yaz(gun)} tarihli ilan"
            except ValueError:
                tarih = ' — tarihli ilan'
            satirlar.append(f"📌 {e(kisa_baslik(referans))}{tarih}")
        if iptal and referans:
            baslik = ("Bu ilan iptal edilmiştir." if tam in (True, None)
                      else f"Bu ilandaki {kadro or 'bazı kadroların'} alımı iptal edilmiştir.")
        elif iptal and kadro:
            baslik = f"{_bas_harf_buyut(kadro)} alımı iptal edilmiştir."
        else:
            baslik = ''
        if baslik:
            satirlar.append(f"<b>{e(baslik)}</b>")
        if cumle:
            satirlar.append(e(cumle))
        if not iptal and duyuru.get('son_tarih'):
            satirlar.append(f"📅 <b>Son başvuru:</b> {tarih_yaz(duyuru['son_tarih'])}")
    if duyuru.get('kaynak_turu') in ('sbb', 'iskur', 'csb') and duyuru.get('kaynak'):
        satirlar.append(f"<i>Kaynak: {e(duyuru['kaynak'])}</i>")
    return "\n".join(satirlar)


def telegram_gonder(token, chat_id, metin, ilan_linki="", site_url="", foto=None, yanit=None):
    """Gönderir; başarıda Telegram message_id'sini (yoksa True), başarısızlıkta False döndürür.
    yanit: bir mesaja yanıt olarak göndermek için message_id (mesaj silinmişse yine de gönderilir)."""
    url = f"https://api.telegram.org/bot{token}/{'sendPhoto' if foto else 'sendMessage'}"
    alanlar = {
        "chat_id": chat_id,
        "caption" if foto else "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    dugmeler = []
    if ilan_linki:
        label='🔎 İlanı incele'
        dugmeler.append([{"text": label, "url": ilan_linki}])
    if site_url:
        dugmeler.append([{"text": "📋 Tüm kamu ilanları", "url": site_url}])
    if dugmeler:
        alanlar["reply_markup"] = json.dumps({"inline_keyboard": dugmeler}, ensure_ascii=False)
    if yanit:
        alanlar["reply_parameters"] = json.dumps({"message_id": int(yanit), "allow_sending_without_reply": True})
    headers = {}
    if foto:
        boundary = 'ilan-' + uuid.uuid4().hex
        parcalar = []
        for key, value in alanlar.items():
            parcalar.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parcalar.append(f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="ilan.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + foto + b'\r\n')
        parcalar.append(f'--{boundary}--\r\n'.encode())
        govde = b''.join(parcalar)
        headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
    else:
        govde = urllib.parse.urlencode(alanlar).encode()
    for deneme in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=govde, headers=headers), timeout=30) as response:
                sonuc = json.load(response)
                if not sonuc.get("ok"):
                    return False
                mid = (sonuc.get("result") or {}).get("message_id")
                return mid if isinstance(mid, int) and mid > 0 else True
        except urllib.error.HTTPError as h:
            if h.code == 429 and deneme == 0:
                try:
                    bekle = json.loads(h.read())["parameters"]["retry_after"]
                except Exception:
                    bekle = 5
                time.sleep(min(int(bekle) + 1, 60))
                continue
            print(f"Telegram hatası {h.code}; ilan sırada tutuluyor.", file=sys.stderr)
            return False
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            print("Telegram bağlantısı doğrulanamadı; ilan sırada tutuluyor.", file=sys.stderr)
            return False
    return False


def telegram_sirasi(mevcut, gelen, yeniler, gonderilen, bekleyen, ilk_calisma, duyur_mevcut, cfg):
    """Yeni/mevcut ilanları sıraya ekler; başarıyla gönderilenleri tekrar eklemez."""
    canli = {i['id'] for i in gelen}
    adaylar = canli if duyur_mevcut else {i['id'] for i in yeniler}
    if not (ilk_calisma and not duyur_mevcut):
        bekleyen.update(adaylar - gonderilen)
    dahil = cfg.get('telegram_kelimeler_dahil', [])
    haric = cfg.get('telegram_kelimeler_haric', [])
    uygun = []
    for kimlik in sorted(bekleyen - gonderilen):
        i = mevcut.get(kimlik)
        if i and kimlik not in canli and i.get('kaynak_turu') in cfg.get('_basarisiz_kaynaklar', []):
            continue
        if not i or kimlik not in canli:
            bekleyen.discard(kimlik)
            continue
        if akademik_ilan(i):
            bekleyen.discard(kimlik)  # akademik ilanlar kanala hiç gitmez
            continue
        if suresi_doldu(i):
            bekleyen.discard(kimlik)
            continue
        if telegram_icin_uygun(i, dahil, haric):
            uygun.append(i)
    return sorted(uygun, key=lambda i: (i.get('son_tarih') or '9999', i.get('kurum', ''), i['baslik']))


DUZ_METIN_TEKILLESTIRME_GUN = 30


def gun_icinde(deger, bugun, gun):
    try:
        return 0 <= (bugun - date.fromisoformat(str(deger)[:10])).days <= gun
    except ValueError:
        return False


def duyuru_karari(duyuru, ilanlar, mesajlar, yanitlar, bugun, gonderilen=None):
    """İptal/düzeltme duyurusu için karar:
    {'islem': 'sessiz'|'gonder', 'orijinal', 'referans', 'tam', 'yaz', 'sebep'}.
    Sessiz: akademik duyuru/ilana ait, kanalda hiç paylaşılmamış ilana ait, içeriği belirsiz, orijinal zaten iptal
    edilmiş ya da aynı olay (kopya) daha önce bildirilmiş.
    referans: kanalda paylaşılmış ama mesaj kaydı olmayan tek orijinal (yanıt verilemez; metinde 📌 ile gösterilir)."""
    tur = 'iptal' if duyuru_turu_iptal_mi(duyuru) else 'duzeltme'
    if akademik_ilan(duyuru):
        return {'islem': 'sessiz', 'sebep': 'akademik duyuru', 'referans': None}
    adaylar = orijinal_ara(duyuru, ilanlar, mesajlar, bugun)
    genis = orijinal_ara(duyuru, ilanlar, mesajlar, bugun, mesaj_gerekli=False)
    # Akademik bastırma yalnız: akademik olmayan hiçbir aday (mesaj şartı olmadan da) yok VE akademik aday var.
    if not adaylar and not genis and orijinal_ara(duyuru, ilanlar, mesajlar, bugun, akademik=True):
        return {'islem': 'sessiz', 'sebep': 'akademik ilana ait', 'referans': None}
    kapsam = kapsam_kokleri(duyuru)
    # Kapsamı belirsiz (genel başlıklı) duyuru: aynı kurumun yalnız akademik ilanı varsa ona ait sayılır.
    if not adaylar and not kapsam \
            and not orijinal_ara(duyuru, ilanlar, mesajlar, bugun, mesaj_gerekli=False, ortusme_gerekli=False) \
            and orijinal_ara(duyuru, ilanlar, mesajlar, bugun, akademik=True, ortusme_gerekli=False):
        return {'islem': 'sessiz', 'sebep': 'akademik ilana ait (kurum)', 'referans': None}
    if len(adaylar) == 1:
        o = adaylar[0]
        if tur == 'iptal' and o.get('iptal_edildi'):
            return {'islem': 'sessiz', 'sebep': 'orijinal zaten iptal edilmiş', 'referans': None}
        tam = tam_iptal(duyuru, o) if tur == 'iptal' else True
        imza = ','.join(sorted(kapsam_kokleri(duyuru, set(norm(o.get('kurum')).split()))))
        anahtarlar = yanit_anahtarlari(tur, o, tam, imza)
        if any(k in yanitlar for k in anahtarlar):
            return {'islem': 'sessiz', 'sebep': 'aynı olay daha önce bildirildi', 'referans': None}
        return {'islem': 'gonder', 'orijinal': o, 'referans': None, 'tam': tam, 'yaz': anahtarlar[0]}

    def paylasilmis(i):
        return bool(mesaj_kimligi(i, mesajlar)) or (gonderilen is not None and paylasildi(i, gonderilen))

    if genis and gonderilen is not None and not any(paylasilmis(i) for i in genis):
        return {'islem': 'sessiz', 'sebep': 'orijinal kanalda paylaşılmadı', 'referans': None}
    referans = genis[0] if len(genis) == 1 and paylasilmis(genis[0]) and gonderilen is not None else None
    if referans and tur == 'iptal' and referans.get('iptal_edildi'):
        return {'islem': 'sessiz', 'sebep': 'orijinal zaten iptal edilmiş', 'referans': None}
    if not referans and not kapsam and not resmi_cumle(duyuru) and (tur == 'iptal' or not duyuru.get('son_tarih')):
        return {'islem': 'sessiz', 'sebep': 'içerik belirsiz', 'referans': None}
    anahtar = duz_anahtar(duyuru)
    if anahtar in yanitlar and gun_icinde(yanitlar[anahtar], bugun, DUZ_METIN_TEKILLESTIRME_GUN):
        return {'islem': 'sessiz', 'sebep': 'aynı olay (düz metin) son 30 günde bildirildi', 'referans': None}
    tam = tam_iptal(duyuru, referans) if referans else None
    return {'islem': 'gonder', 'orijinal': None, 'referans': referans, 'tam': tam, 'yaz': anahtar}


TOPLU_SINIR = 950  # sendPhoto başlık sınırı 1024 görünür karakter


def toplu_zamani(zaman, son_gun):
    """Günde bir kez: İstanbul 09:00'dan sonra ve bugün henüz gönderilmediyse."""
    return zaman.hour >= 9 and son_gun != zaman.date().isoformat()


def toplu_secim(ilanlar, gonderilen, cfg):
    """Son başvurusu bugün..3 gün içinde olan, kanalda daha önce paylaşılmış, akademik/iptal/duyuru olmayan ilanlar."""
    bugun = simdi().date()
    dahil, haric = cfg.get('telegram_kelimeler_dahil', []), cfg.get('telegram_kelimeler_haric', [])
    sonuc = []
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i) or not i.get('son_tarih'):
            continue
        if not ({i['id'], *i.get('kaynak_kimlikleri', [])} & gonderilen) or suresi_doldu(i):
            continue
        if 0 <= (date.fromisoformat(i['son_tarih']) - bugun).days <= 3 and telegram_icin_uygun(i, dahil, haric):
            sonuc.append(i)
    sonuc.sort(key=lambda i: (i['son_tarih'], i.get('kurum', ''), i['id']))
    gorulen, tekil = set(), []
    for i in sonuc:  # aynı normalize kurum + aynı son tarih (SBB/İŞKUR kopyaları) tek satır
        k = kurum_kimligi(i)
        anahtar = (i['son_tarih'], k[:2] if k else i['id'])
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            tekil.append(i)
    return tekil


GUN_ADLARI = ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')
AY_ADLARI = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')
SABAH_YENI_EN_COK, SABAH_YENI_EN_AZ = 5, 3
SABAH_SON_GUN_EN_COK = 6


def turkce_tarih(zaman):
    """'5 Ekim Pazartesi' (İstanbul tarihi)."""
    return f"{zaman.day} {AY_ADLARI[zaman.month - 1]} {GUN_ADLARI[zaman.weekday()]}"


def gorunen_uzunluk(metin):
    return len(html.unescape(re.sub(r"<[^>]+>", "", metin)))


def sabah_yeniler(ilanlar, gonderilen, cfg, zaman):
    """Son 24 saatte ilk görülen, kanalda paylaşılmış; akademik/iptal/duyuru olmayan ilanlar (en çok kadro önce).
    Aynı normalize kurum + aynı son tarih (SBB/İŞKUR kopyaları) tek kayıt."""
    from kart_tasarimlari import veri as kart_verisi
    dahil, haric = cfg.get('telegram_kelimeler_dahil', []), cfg.get('telegram_kelimeler_haric', [])
    sonuc = []
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i):
            continue
        try:
            gorulme = datetime.fromisoformat(i['ilk_gorulme'])
        except (KeyError, TypeError, ValueError):
            continue
        if gorulme.tzinfo is None:
            gorulme = gorulme.replace(tzinfo=TR)
        if not timedelta(0) <= zaman - gorulme <= timedelta(hours=24):
            continue
        if not ({i['id'], *i.get('kaynak_kimlikleri', [])} & gonderilen) or suresi_doldu(i):
            continue
        if telegram_icin_uygun(i, dahil, haric):
            sonuc.append((-(kart_verisi(i)['toplam'] or 0), i.get('kurum', ''), i['id'], i))
    sonuc.sort(key=lambda s: s[:3])
    gorulen, tekil = set(), []
    for *_, i in sonuc:
        k = kurum_kimligi(i)
        anahtar = (i.get('son_tarih'), k[:2] if k else i['id'])
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            tekil.append(i)
    return tekil


def sabah_acik_sayisi(ilanlar, zaman):
    """Sitedeki 'Başvurusu açık' tanımı: akademik/duyuru/iptal değil, son tarihi var, süresi dolmamış, başlamış."""
    sayi = 0
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i) or not i.get('son_tarih') or suresi_doldu(i):
            continue
        try:
            if i.get('baslangic_zaman') and datetime.fromisoformat(i['baslangic_zaman']) > zaman:
                continue
        except ValueError:
            pass
        sayi += 1
    return sayi


def sabah_toplam_kadro(yeniler):
    from kart_tasarimlari import veri as kart_verisi
    return sum(kart_verisi(i)['toplam'] or 0 for i in yeniler)


def _ilan_satiri(i, site_url, etiket=None):
    from kart_tasarimlari import toplu_satir
    e = html.escape
    kurum, kadro = toplu_satir(i)
    ad = kisalt(f"{kurum} — {kadro}" if kadro and kadro != kurum else kurum, 70)
    try:
        url = ilan_sayfasi(i, site_url)
    except ValueError:
        url = ''
    govde = f'<a href="{e(url, quote=True)}">{e(ad)}</a>' if url else e(ad)
    return f"• {govde}" + (f" · <b>{etiket}</b>" if etiket else "")


def sabah_mesaj(yeniler, son_gun, acik_sayisi, site_url, zaman):
    """Sabah özeti başlığı (HTML): yeni ilanlar, son başvurusu yaklaşanlar, açık ilan sayısı. Boş bölüm yazılmaz.
    Sınır (~950 görünür karakter) aşılırsa önce yeni listesi 3'e, sonra son gün listesi kısaltılır; başlık/altlık kalır."""
    bugun = zaman.date()
    ust = f"☀️ <b>Günaydın — {turkce_tarih(zaman)}</b>"
    alt = []
    if acik_sayisi:
        alt.append(f"📌 Şu an başvurusu açık <b>{acik_sayisi} ilan</b>")
    if site_url:
        alt.append(f'👉 <a href="{html.escape(site_url.rstrip("/") + "/?g=bugun", quote=True)}">Bugünün tüm ilanları</a>')
    yeni_satirlari = [_ilan_satiri(i, site_url) for i in yeniler]
    son_satirlari = []
    for i in son_gun:
        fark = (date.fromisoformat(i['son_tarih']) - bugun).days
        son_satirlari.append(_ilan_satiri(i, site_url, "Bugün son gün" if fark <= 0 else "Yarın son gün" if fark == 1 else f"{fark} gün kaldı"))
    kadro = sabah_toplam_kadro(yeniler)
    yeni_baslik = f"🆕 <b>Son 24 saatte {len(yeniler)} yeni ilan</b>" + (f" · {kadro} kadro" if kadro else "")

    def olustur(ny, ns):
        parcalar = [ust]
        if ny:
            satirlar = yeni_satirlari[:ny] + ([f"+{len(yeniler) - ny} ilan daha"] if len(yeniler) > ny else [])
            parcalar.append("\n".join([yeni_baslik, *satirlar]))
        if ns:
            satirlar = son_satirlari[:ns] + ([f"+{len(son_gun) - ns} ilan daha"] if len(son_gun) > ns else [])
            parcalar.append("\n".join(["⏰ <b>Son başvurusu yaklaşanlar</b>", *satirlar]))
        if alt:
            parcalar.append("\n".join(alt))
        return "\n\n".join(parcalar)

    ny, ns = min(len(yeniler), SABAH_YENI_EN_COK), min(len(son_gun), SABAH_SON_GUN_EN_COK)
    while gorunen_uzunluk(olustur(ny, ns)) > TOPLU_SINIR:
        if ny > SABAH_YENI_EN_AZ:
            ny -= 1
        elif ns > 1:
            ns -= 1
        elif ny > 1:
            ny -= 1
        elif ns > 0:
            ns -= 1
        elif ny > 0:
            ny -= 1
        else:
            break
    return olustur(ny, ns)

def suresi_doldu(ilan):
    if ilan.get('son_zaman'):
        return datetime.fromisoformat(ilan['son_zaman']) <= simdi()
    return bool(ilan.get('son_tarih') and date.fromisoformat(ilan['son_tarih']) < simdi().date())


def detay_taze(ilan):
    try:
        return simdi() - datetime.fromisoformat(ilan['detay_guncelleme']) < timedelta(hours=12)
    except (KeyError, TypeError, ValueError):
        return False


# ------------------------------------------------------------------- Ana akış
def yukle(yol):
    if yol.exists():
        try:
            return json.loads(yol.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sys.exit("Veri dosyası bozuk. Tekrar mesaj göndermemek için tarama durduruldu.")
    return {"guncelleme": None, "ilanlar": []}


def telegram_icin_uygun(ilan, dahil, haric):
    if akademik_ilan(ilan):
        return False
    metin = (ilan["baslik"] + " " + ilan.get("kurum", "")).lower()
    if dahil and not any(k.lower() in metin for k in dahil):
        return False
    return not any(k.lower() in metin for k in haric)


def ilan_gorseli(i, hatirlatma, logo=None):
    """Telegram kartı: yeni tasarım (afiş/bilet); hata olursa eski kart ile devam eder (gönderim aksamasın)."""
    try:
        from kart_tasarimlari import ilan_karti
        return ilan_karti(i, logo=logo, hatirlatma=hatirlatma)
    except Exception as exc:
        print(f'Yeni ilan kartı oluşturulamadı ({type(exc).__name__}); eski kart kullanılıyor.', file=sys.stderr)
    tarih = tarih_yaz(i['son_tarih']) if i.get('son_tarih') else 'Resmi ilandan kontrol edin'
    if i.get('son_zaman'):
        tarih += ' · ' + datetime.fromisoformat(i['son_zaman']).strftime('%H:%M') + ' TSİ'
    return gorsel_olustur(
        okunakli_baslik(i.get('kurum') or i['baslik']),
        okunakli_baslik(i.get("kadro", "")) or kisa_baslik(i),
        okunakli_baslik(i.get('yer', '')), tarih,
        kalan_gun_metni(i['son_tarih']).capitalize() if hatirlatma else '',
        kaynak=i.get('kaynak', 'Kariyer Kapısı'), logo=logo)


def siniflandir(ilan):
    """Site filtreleri ve kişisel bot için öğrenim, kategori, il ve KPSS alanlarını günceller."""
    for alan, deger in (('ogrenim', ogrenim_seviyeleri(ilan)), ('kategori', kategori(ilan)),
                        ('iller', il_adlari(ilan)), ('kpss', kpss_durumu(ilan))):
        if deger:
            ilan[alan] = deger
        else:
            ilan.pop(alan, None)


def temizle(ilanlar):
    """Süresi 7 günden fazla önce dolanları; tarihsiz olup 45 günden eski olanları çıkarır."""
    bugun = simdi().date()
    kalan = []
    for i in ilanlar:
        if i.get("son_tarih"):
            if date.fromisoformat(i["son_tarih"]) < bugun - timedelta(days=7):
                continue
        else:
            gorulme = datetime.fromisoformat(i["ilk_gorulme"])
            if gorulme < simdi() - timedelta(days=45):
                continue
        kalan.append(i)
    return kalan


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rss-dosya", help="Ağ yerine yerel RSS dosyası oku (test)")
    p.add_argument("--cikti", default=str(VERI_YOLU), help="Veri dosyası yolu")
    p.add_argument("--dry-run", action="store_true", help="Telegram'a gönderme, ekrana yaz")
    phase=p.add_mutually_exclusive_group()
    phase.add_argument('--prepare',action='store_true',help='Veriyi ve kuyruğu hazırla; site yayımlanana kadar gönderme')
    phase.add_argument('--send-only',action='store_true',help='Yayımlanan kayıtların kuyruğunu gönder; yeni veri okuma')
    p.add_argument("--duyur-mevcut", action="store_true",
                   help="Canlı RSS'teki henüz gönderilmemiş mevcut ilanları da sıraya al")
    p.add_argument("--dump", action="store_true", help="Ham ilanların ilk 3'ünü yazdır ve çık")
    a = p.parse_args()

    cfg = json.loads(CONFIG_YOLU.read_text(encoding="utf-8"))
    rss_listesi = [u for u in os.environ.get("RSS_URLS", "").split() if u] or cfg.get("rss_urls", [])
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    cikti = Path(a.cikti)
    veri = yukle(cikti)
    onceki = {i['id']:i for i in veri['ilanlar']}
    kaynak_baslangiclari = set(veri.get('kaynak_baslangiclari', []))
    kaynak_durumlari = veri.get('kaynak_durumlari', {})
    sessiz_kimlikler = set()
    kaynak_hatalari = []
    yerel = yerel_oku()

    # 1) Kaynaktan oku
    gelen, basarili = [], 0
    if a.send_only:
        live=set(veri.get('canli_kimlikler',[]))
        gelen=[dict(i) for i in veri['ilanlar'] if i['id'] in live]
        basarili=1
    elif a.rss_dosya:
        gelen = rss_coz(Path(a.rss_dosya).read_bytes())
        basarili = 1
    else:
        if not rss_listesi and not cfg.get('ek_kaynaklar'):
            sys.exit("Hata: config.json içine 'rss_urls' ekle (README'ye bak).")
        for url in rss_listesi:
            try:
                gelen += rss_coz(indir(url))
                basarili += 1
            except Exception as h:  # ağ, XML vb.
                print(f"Uyarı: {url[:60]}... okunamadı: {h}", file=sys.stderr)
        for kaynak, okuyucu in [('sbb',read_sbb), ('iskur',read_iskur), ('csb',None)]:
            if kaynak not in cfg.get('ek_kaynaklar', []):
                continue
            try:
                local_sbb={'sbb':sbb_verisi,'csb':csb_verisi}[kaynak](yerel) if kaynak in ('sbb','csb') else None
                if kaynak=='csb' and not local_sbb:
                    raise RuntimeError('ÇŞB yerel verisi yok ya da eski')  # GitHub'dan erişilemez; kayıtlar korunur
                eklenen, hatalar = local_sbb[:2] if local_sbb else okuyucu(onceki)
                gelen += eklenen
                basarili += 1
                if kaynak not in kaynak_baslangiclari and not a.duyur_mevcut:
                    sessiz_kimlikler.update(i['id'] for i in eklenen)
                if not hatalar:
                    kaynak_baslangiclari.add(kaynak)
                kaynak_durumlari[kaynak] = {'kontrol':simdi().isoformat(timespec='seconds'),
                    'ilan_sayisi':len(eklenen),'hata_sayisi':hatalar}
                if local_sbb:
                    kaynak_durumlari[kaynak].update(yerel_kontrol=local_sbb[2],calisma_yeri='yerel')
                if hatalar:
                    kaynak_hatalari.append(kaynak)
                print(f'{kaynak}: {len(eklenen)} ilan, {hatalar} erişim hatası.')
            except Exception as exc:
                kaynak_hatalari.append(kaynak)
                kaynak_durumlari[kaynak] = {**kaynak_durumlari.get(kaynak,{}),
                    'son_deneme':simdi().isoformat(timespec='seconds'),'hata_sayisi':1}
                print(f'{kaynak} kaynağı okunamadı ({type(exc).__name__}); diğer kaynaklar devam ediyor.',file=sys.stderr)
        cfg['_basarisiz_kaynaklar'] = kaynak_hatalari
    if not basarili:
        sys.exit("Hata: hiçbir RSS kaynağı okunamadı.")

    if a.dump:
        print(json.dumps(gelen[:3], ensure_ascii=False, indent=2))
        return

    # 2) Yeni ilanları bul
    ilk_calisma = not veri.get("guncelleme")
    mevcut = {i["id"]: i for i in veri["ilanlar"]}
    yeniler = []
    for i in gelen:
        if i["id"] in mevcut:
            mevcut[i["id"]].update(baslik=i["baslik"], kurum=i["kurum"],
                                    ilan_turu=i.get("ilan_turu", ""))
            if i.get('son_tarih'):
                mevcut[i['id']]['son_tarih'] = i['son_tarih']
            if i.get('kaynak_turu'):
                mevcut[i['id']].update(i)
        else:
            i["ilk_gorulme"] = simdi().isoformat(timespec="seconds")
            mevcut[i["id"]] = i
            if i['id'] not in sessiz_kimlikler:
                yeniler.append(i)

    # Resmi sayfanın açık veri servisi: ayrıntıları 12 saat sakla, hata varsa eksik mesaj gönderme.
    detay_hatalari = set()
    if cfg.get('resmi_detaylari_oku', False) and not a.send_only:
        ardisik_hata = 0
        for gelen_ilan in gelen:
            i = mevcut[gelen_ilan['id']]
            if i.get('kaynak_turu') in ('sbb','iskur','csb'):
                continue
            local_detail=yerel.get('detaylar',{}).get(i['id'],{})
            if detay_taze(local_detail) and (local_detail.get('detay_guncelleme','')>i.get('detay_guncelleme','')):
                i.update(local_detail)
            if detay_taze(i):
                continue
            try:
                i.update(detay_oku(i['link']))
                ardisik_hata = 0
            except Exception as h:
                detay_hatalari.add(i['id'])
                ardisik_hata += 1
                print(f"Resmi ayrıntılar alınamadı ({type(h).__name__}: {str(h)[:180]}); daha sonra denenecek: {i['baslik']}", file=sys.stderr)
                if ardisik_hata >= 3:
                    print('Resmi veri servisi üst üste yanıt vermedi; ayrıntı taraması durduruldu.', file=sys.stderr)
                    break
            time.sleep(0.25)

    # Enrich Kariyer Kapısı first so date/quota comparisons use verified fields.
    gelen = merge_sources([mevcut[i['id']] for i in gelen], onceki)
    yeni_ids = {i['id'] for i in yeniler}
    birlesik_ids = {i['id'] for i in gelen}
    aliases = {alias:i['id'] for i in gelen for alias in i.get('kaynak_kimlikleri', [])}
    canli = {i['id']: i for i in gelen}
    for old_id in list(mevcut):
        if old_id in aliases and aliases[old_id] != old_id:
            hedef = canli.get(aliases[old_id])
            if hedef is not None and mevcut[old_id].get('iptal_edildi') and not hedef.get('iptal_edildi'):
                hedef['iptal_edildi'] = mevcut[old_id]['iptal_edildi']  # takma ada dönüşen orijinalin işareti kaybolmaz
            del mevcut[old_id]
    mevcut.update(canli)
    # Eski SBB duyurularına resmi işlem cümlesini depodaki PDF kopyasından bir kez ekle (mevcut alanlar korunur).
    for i in mevcut.values():
        if i.get('duyuru_turu') and i.get('kaynak_turu') == 'sbb' and 'duyuru_cumlesi' not in i:
            try:
                cumle = belge_cumlesi(i)
            except Exception as exc:
                print(f"Duyuru cümlesi okunamadı ({type(exc).__name__}): {i.get('id')}", file=sys.stderr)
                continue
            if cumle is not None:
                i['duyuru_cumlesi'] = cumle
    yeniler = [i for i in gelen if i['id'] in yeni_ids and i['id'] in birlesik_ids]

    # 3) Telegram: sınırı aşan ve başarısız olan gönderimleri sonraki taramaya sakla.
    gonderilen = set(veri.get('telegram_gonderilen', []))
    from veri_kaydet import merge_reminders
    hatirlatilan = set(merge_reminders(veri.get('telegram_hatirlatilan', []),aliases))
    bekleyen = set(veri.get('telegram_bekleyen', []))
    yayin_surumu = int(cfg.get('telegram_yayin_surumu', 1))
    if yayin_surumu > int(veri.get('telegram_yayin_surumu', 1)):
        # Explicit channel refresh: reset only once; subsequent runs resume the queue.
        gonderilen, hatirlatilan = set(), set()
        bekleyen = {i['id'] for i in gelen}
    gonderilen.update(aliases[x] for x in list(gonderilen) if x in aliases)
    bekleyen = {aliases.get(x,x) for x in bekleyen}
    gonderilecek = telegram_sirasi(mevcut, gelen, yeniler, gonderilen, bekleyen,
                                  ilk_calisma, a.duyur_mevcut, cfg)
    # İlan başına hatırlatma kaldırıldı (geçmiş hatirlatilan korunur, yeni kayıt eklenmez);
    # yerine günde bir kez sabah özeti (yeni ilanlar + son başvurusu yaklaşanlar + açık ilan sayısı) gönderilir.
    mesajlar = dict(veri.get('telegram_mesajlari', {}))
    yanitlar = dict(veri.get('telegram_duyuru_yanitlari', {}))
    toplu_gun = veri.get('telegram_toplu_hatirlatma_gunu')
    sabah = None
    if toplu_zamani(simdi(), toplu_gun):
        sabah_yeni = sabah_yeniler(gelen, gonderilen, cfg, simdi())
        sabah_son_gun = toplu_secim(gelen, gonderilen, cfg)
        sabah_acik = sabah_acik_sayisi(gelen, simdi())
        if sabah_yeni or sabah_son_gun or sabah_acik:  # üçü de boşsa sessizce atlanır, gün işaretlenmez
            sabah = (sabah_yeni, sabah_son_gun, sabah_acik)
    kuyruk = ([('sabah', sabah)] if sabah else []) + \
             [('duyuru' if i.get('duyuru_turu') else 'ilan', i) for i in gonderilecek]
    limit = max(1, int(cfg.get('max_mesaj_per_calisma', 15)))
    site_url = cfg.get('site_url', '')
    hata = False
    adet = 0
    ertelenen = 0

    def mesaj_kaydet(kimlik, mid):
        if isinstance(mid, int) and not isinstance(mid, bool):
            mesajlar[kimlik] = mid

    for tur, i in ([] if a.prepare else kuyruk[:limit]):
        if tur == 'sabah':
            yeni_l, son_gun_l, acik = i
            metin = sabah_mesaj(yeni_l, son_gun_l, acik, site_url, simdi())
            if a.dry_run:
                print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
                continue
            try:
                from kart_tasarimlari import sabah_ozeti_karti, toplu_son_gun_karti
                foto = toplu_son_gun_karti(son_gun_l, simdi()) if son_gun_l else sabah_ozeti_karti(yeni_l, acik, simdi())
            except Exception as exc:
                # Görsel yapılamazsa gün atlanmaz: yalnız metin gönderilir.
                print(f'Sabah özeti kartı oluşturulamadı ({type(exc).__name__}); yalnız metin gönderilecek.', file=sys.stderr)
                foto = None
            mid = telegram_gonder(token, chat_id, metin, '', site_url, foto=foto) if (token and chat_id) else False
            if not mid:
                hata = True
                break
            toplu_gun = simdi().date().isoformat()  # gün işareti yalnız başarıda yazılır
            adet += 1
            print(f"Telegram'a sabah özeti gönderildi: {len(yeni_l)} yeni, {len(son_gun_l)} son gün, {acik} açık ilan")
            time.sleep(3.2)
            continue
        if cfg.get('resmi_detaylari_oku', False) and not detay_taze(i):
            # Resmi servise geçici erişim sorunu: ilan sırada kalır, iş başarısız sayılmaz.
            ertelenen += 1
            continue
        if tur == 'duyuru':
            karar = duyuru_karari(i, list(mevcut.values()), mesajlar, yanitlar, simdi().date(), gonderilen=gonderilen)
            if karar['islem'] == 'sessiz':
                # Gönderilmez ama tekrar denenmesin diye gönderilmiş sayılır.
                if not a.dry_run:
                    gonderilen.add(i['id'])
                    bekleyen.discard(i['id'])
                print(f"İptal/düzeltme duyurusu gönderilmedi ({karar['sebep']}): {i['baslik']}")
                continue
            orijinal = karar['orijinal']
            yanit = mesaj_kimligi(orijinal, mesajlar)[1] if orijinal else None
            metin = duyuru_metni(i, orijinal is not None, karar['tam'], karar.get('referans'))
            if a.dry_run:
                print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
                continue
            try:
                hedef = ilan_sayfasi(i, site_url)
            except ValueError:
                hedef = ''
            mid = telegram_gonder(token, chat_id, metin, hedef, site_url, yanit=yanit) if (token and chat_id) else False
            if not mid:
                hata = True
                break
            gonderilen.add(i['id'])
            bekleyen.discard(i['id'])
            mesaj_kaydet(i['id'], mid)
            yanitlar[karar['yaz']] = simdi().date().isoformat()
            if orijinal is not None and duyuru_turu_iptal_mi(i) and karar['tam']:
                orijinal['iptal_edildi'] = i['id']  # kısmi (tek kadro) iptallerde ilan açık kalır
            adet += 1
            print(f"Telegram'a {'iptal' if duyuru_turu_iptal_mi(i) else 'düzeltme'} duyurusu gönderildi"
                  f"{' (orijinal ilana yanıt)' if orijinal is not None else ''}: {i['baslik']}")
            time.sleep(3.2)
            continue
        metin = mesaj_olustur(i, site_url)
        if a.dry_run:
            print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
            continue
        try:
            foto = ilan_gorseli(i, False, kurum_logosu(i))
        except Exception as exc:
            print(f'İlan görseli oluşturulamadı ({type(exc).__name__}); gönderim ertelendi.', file=sys.stderr)
            hata = True
            continue
        try:
            hedef=ilan_sayfasi(i,site_url)
        except ValueError:
            print('Site ayrıntı bağlantısı hazırlanamadı; gönderim ertelendi.',file=sys.stderr)
            hata=True
            continue
        mid = telegram_gonder(token, chat_id, metin, hedef, site_url, foto=foto) if (token and chat_id) else False
        if not mid:
            hata = True
            break
        gonderilen.add(i['id'])
        bekleyen.discard(i['id'])
        mesaj_kaydet(i['id'], mid)
        adet += 1
        print(f"Telegram'a ilan gönderildi: {i['baslik']}")
        time.sleep(3.2)
    if ilk_calisma and not a.duyur_mevcut:
        print(f"İlk çalıştırma: {len(yeniler)} mevcut ilan sessizce kaydedildi (kanala gönderilmedi).")
    if a.dry_run:
        print('Önizleme tamamlandı; veri dosyası değiştirilmedi.')
        return

    # 4) Kaydet
    for i in mevcut.values():
        i.pop("aciklama", None)  # site için gerekli değil, dosyayı küçük tut
        siniflandir(i)
    veri = {
        "guncelleme": simdi().isoformat(timespec="seconds"),
        "ilanlar": sorted(temizle(list(mevcut.values())), key=lambda x: x["son_tarih"] or "9999"),
        "telegram_gonderilen": sorted(gonderilen),
        "telegram_bekleyen": sorted(bekleyen - gonderilen),
        "telegram_hatirlatilan": sorted(hatirlatilan),
        "telegram_mesajlari": dict(sorted(mesajlar.items())),
        # 'm:' (düz metin) kayıtları 30 gün sonra budanır; 'o:' (orijinale yanıt) kayıtları kalıcıdır.
        "telegram_duyuru_yanitlari": dict(sorted((k, v) for k, v in yanitlar.items()
            if not k.startswith('m:') or gun_icinde(v, simdi().date(), DUZ_METIN_TEKILLESTIRME_GUN))),
        "telegram_toplu_hatirlatma_gunu": toplu_gun,
        "telegram_yayin_surumu": yayin_surumu,
        "kaynak_baslangiclari": sorted(kaynak_baslangiclari),
        "kaynak_durumlari": kaynak_durumlari,
        "canli_kimlikler": sorted({i['id'] for i in gelen}),
    }
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Tamam: {len(gelen)} ilan okundu, {len(yeniler)} yeni, {len(veri['ilanlar'])} kayıtlı.")
    print(f"Telegram: {adet} mesaj gönderildi, {len(bekleyen - gonderilen)} ilan bekliyor.")
    if detay_hatalari:
        print(f"Ayrıntıları tekrar denenecek ilan: {len(detay_hatalari)}")
    if ertelenen:
        print(f"::warning::Resmi ayrıntısı güncel olmayan {ertelenen} ilanın gönderimi sonraki taramaya ertelendi.")
    if hata:
        sys.exit('Telegram gönderimi tamamlanamadı. Gönderilmeyen ilanlar sonraki taramada tekrar denenecek.')


if __name__ == "__main__":
    main()
