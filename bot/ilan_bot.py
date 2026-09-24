#!/usr/bin/env python3
"""Kariyer Kapısı RSS -> Telegram kanalı + docs/ilanlar.json (site verisi).

Sadece standart kütüphane kullanır. Ortam değişkenleri:
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
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from resmi_detay import detay_oku

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
    with urllib.request.urlopen(istek, timeout=30) as r:
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


def mesaj_olustur(ilan, site_url):
    e = html.escape
    kurum = ilan.get("kurum", "")
    baslik = ilan['baslik']
    if kurum and baslik.startswith(kurum + " - "):
        baslik = baslik[len(kurum) + 3:]
    satirlar = ["📣 <b>KAMU İLAN TAKİP</b>", "", f"<b>{e(kisalt(okunakli_baslik(baslik), 420))}</b>"]
    if kurum:
        satirlar.extend(["", f"🏛 <b>Kurum:</b> {e(kisalt(okunakli_baslik(kurum), 300))}"])
    for alan, etiket, sinir in [("yer", "📍 Görev yeri", 200),
                                 ("ilan_turu", "💼 İlan türü", 150),
                                 ("kadro", "👥 Kadro / kontenjan", 400)]:
        if ilan.get(alan):
            deger = ''.join(okunakli_baslik(s) for s in re.split(r'( • | — )', ilan[alan]))
            satirlar.append(f"<b>{etiket}:</b> {e(kisalt(deger, sinir))}")
    if ilan.get("sartlar"):
        satirlar.extend(["", "📝 <b>Seçilmiş kadrolardan başvuru koşulları</b>"])
        for sart in ilan["sartlar"][:3]:
            satirlar.extend([f"• <b>{e(kisalt(okunakli_baslik(sart['kadro']), 110))}</b>",
                             e(kisalt(sart["metin"], 380))])
        satirlar.append("<i>Seçili alıntılardır; tüm kadrolar ve özel koşullar resmi ilandadır.</i>")
    elif ilan.get("ozet"):
        satirlar.extend(["", "📝 <b>İlan metninden</b>", e(kisalt(ilan["ozet"], 1000)),
                         "<i>Koşulların tamamı ve kadroya özel şartlar resmi ilandadır.</i>"])
    if ilan.get("basvuru_notu"):
        satirlar.extend(["", "📌 <b>Başvuru notu</b>", e(kisalt(ilan['basvuru_notu'], 450))])
    if ilan.get("son_tarih"):
        saat = ""
        if ilan.get("son_zaman"):
            saat = " • " + datetime.fromisoformat(ilan['son_zaman']).strftime('%H:%M') + " (TSİ)"
        satirlar.extend(["", f"📅 <b>Son başvuru:</b> {tarih_yaz(ilan['son_tarih'])}{saat}"])
        kalan = (date.fromisoformat(ilan['son_tarih']) - simdi().date()).days
        simge = "🔴" if kalan <= 3 else "⏳"
        satirlar.append(f"{simge} <b>{kalan_gun_metni(ilan['son_tarih']).capitalize()}</b>")
    else:
        satirlar.extend(["", "⏳ <b>Son başvuru:</b> Resmi ilan üzerinden kontrol edin."])
    satirlar.extend(["", f'🔗 <a href="{e(ilan["link"], quote=True)}"><b>İlan Detayı ve Başvuru</b></a>',
                     "", "<i>Kaynak: Kariyer Kapısı • Resmi bir kanal değildir.</i>"])
    return "\n".join(satirlar)


def telegram_gonder(token, chat_id, metin, ilan_linki="", site_url=""):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    alanlar = {
        "chat_id": chat_id,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    dugmeler = []
    if ilan_linki:
        dugmeler.append([{"text": "🔎 İlanı incele ve başvur", "url": ilan_linki}])
    if site_url:
        dugmeler.append([{"text": "📋 Tüm kamu ilanları", "url": site_url}])
    if dugmeler:
        alanlar["reply_markup"] = json.dumps({"inline_keyboard": dugmeler}, ensure_ascii=False)
    govde = urllib.parse.urlencode(alanlar).encode()
    for deneme in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=govde), timeout=30) as response:
                return bool(json.load(response).get("ok"))
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
        if not i or kimlik not in canli:
            bekleyen.discard(kimlik)
            continue
        if suresi_doldu(i):
            bekleyen.discard(kimlik)
            continue
        if telegram_icin_uygun(i, dahil, haric):
            uygun.append(i)
    return sorted(uygun, key=lambda i: (i.get('son_tarih') or '9999', i.get('kurum', ''), i['baslik']))


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
    metin = (ilan["baslik"] + " " + ilan.get("kurum", "")).lower()
    if dahil and not any(k.lower() in metin for k in dahil):
        return False
    return not any(k.lower() in metin for k in haric)


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
    p.add_argument("--duyur-mevcut", action="store_true",
                   help="Canlı RSS'teki henüz gönderilmemiş mevcut ilanları da sıraya al")
    p.add_argument("--dump", action="store_true", help="Ham ilanların ilk 3'ünü yazdır ve çık")
    a = p.parse_args()

    cfg = json.loads(CONFIG_YOLU.read_text(encoding="utf-8"))
    rss_listesi = [u for u in os.environ.get("RSS_URLS", "").split() if u] or cfg.get("rss_urls", [])
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    # 1) Kaynaktan oku
    gelen, basarili = [], 0
    if a.rss_dosya:
        gelen = rss_coz(Path(a.rss_dosya).read_bytes())
        basarili = 1
    else:
        if not rss_listesi:
            sys.exit("Hata: config.json içine 'rss_urls' ekle (README'ye bak).")
        for url in rss_listesi:
            try:
                gelen += rss_coz(indir(url))
                basarili += 1
            except Exception as h:  # ağ, XML vb.
                print(f"Uyarı: {url[:60]}... okunamadı: {h}", file=sys.stderr)
    if not basarili:
        sys.exit("Hata: hiçbir RSS kaynağı okunamadı.")

    if a.dump:
        print(json.dumps(gelen[:3], ensure_ascii=False, indent=2))
        return

    # 2) Yeni ilanları bul
    cikti = Path(a.cikti)
    veri = yukle(cikti)
    ilk_calisma = not veri.get("guncelleme")
    mevcut = {i["id"]: i for i in veri["ilanlar"]}
    yeniler = []
    for i in gelen:
        if i["id"] in mevcut:
            mevcut[i["id"]].update(baslik=i["baslik"], kurum=i["kurum"],
                                    ilan_turu=i.get("ilan_turu", ""))
            if i.get('son_tarih'):
                mevcut[i['id']]['son_tarih'] = i['son_tarih']
        else:
            i["ilk_gorulme"] = simdi().isoformat(timespec="seconds")
            mevcut[i["id"]] = i
            yeniler.append(i)

    # Resmi sayfanın açık veri servisi: ayrıntıları 12 saat sakla, hata varsa eksik mesaj gönderme.
    detay_hatalari = set()
    if cfg.get('resmi_detaylari_oku', False):
        ardisik_hata = 0
        for gelen_ilan in gelen:
            i = mevcut[gelen_ilan['id']]
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

    # 3) Telegram: sınırı aşan ve başarısız olan gönderimleri sonraki taramaya sakla.
    gonderilen = set(veri.get('telegram_gonderilen', []))
    bekleyen = set(veri.get('telegram_bekleyen', []))
    gonderilecek = telegram_sirasi(mevcut, gelen, yeniler, gonderilen, bekleyen,
                                  ilk_calisma, a.duyur_mevcut, cfg)
    limit = max(1, int(cfg.get('max_mesaj_per_calisma', 15)))
    hata = False
    adet = 0
    for i in gonderilecek[:limit]:
        if cfg.get('resmi_detaylari_oku', False) and not detay_taze(i):
            hata = True
            continue
        metin = mesaj_olustur(i, cfg.get('site_url', ''))
        if a.dry_run:
            print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
            continue
        if not (token and chat_id) or not telegram_gonder(token, chat_id, metin, i['link'], cfg.get('site_url', '')):
            hata = True
            break
        gonderilen.add(i['id'])
        bekleyen.discard(i['id'])
        adet += 1
        print(f"Telegram'a gönderildi: {i['baslik']}")
        time.sleep(3.2)
    if ilk_calisma and not a.duyur_mevcut:
        print(f"İlk çalıştırma: {len(yeniler)} mevcut ilan sessizce kaydedildi (kanala gönderilmedi).")
    if a.dry_run:
        print('Önizleme tamamlandı; veri dosyası değiştirilmedi.')
        return

    # 4) Kaydet
    for i in mevcut.values():
        i.pop("aciklama", None)  # site için gerekli değil, dosyayı küçük tut
    veri = {
        "guncelleme": simdi().isoformat(timespec="seconds"),
        "ilanlar": sorted(temizle(list(mevcut.values())), key=lambda x: x["son_tarih"] or "9999"),
        "telegram_gonderilen": sorted(gonderilen),
        "telegram_bekleyen": sorted(bekleyen - gonderilen),
    }
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Tamam: {len(gelen)} ilan okundu, {len(yeniler)} yeni, {len(veri['ilanlar'])} kayıtlı.")
    print(f"Telegram: {adet} mesaj gönderildi, {len(bekleyen - gonderilen)} ilan bekliyor.")
    if detay_hatalari:
        print(f"Ayrıntıları tekrar denenecek ilan: {len(detay_hatalari)}")
    if hata:
        sys.exit('Telegram gönderimi tamamlanamadı. Gönderilmeyen ilanlar sonraki taramada tekrar denenecek.')


if __name__ == "__main__":
    main()
