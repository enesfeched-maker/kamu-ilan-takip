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


def mesaj_olustur(ilan, site_url):
    e = html.escape
    satirlar = [f"🆕 <b>{e(ilan['baslik'])}</b>"]
    if ilan.get("kurum"):
        satirlar.append(e(ilan["kurum"]))
    if ilan.get("son_tarih"):
        satirlar.append(f"⏳ Son başvuru: {tarih_yaz(ilan['son_tarih'])} ({kalan_gun_metni(ilan['son_tarih'])})")
    satirlar.append(f'🔗 <a href="{e(ilan["link"], quote=True)}">Kariyer Kapısı\'nda aç</a>')
    if site_url:
        satirlar.append(f'📋 <a href="{e(site_url, quote=True)}">Tüm açık ilanlar</a>')
    return "\n".join(satirlar)


def telegram_gonder(token, chat_id, metin):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    govde = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    for deneme in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=govde), timeout=30):
                return True
        except urllib.error.HTTPError as h:
            if h.code == 429 and deneme == 0:
                try:
                    bekle = json.loads(h.read())["parameters"]["retry_after"]
                except Exception:
                    bekle = 5
                time.sleep(min(int(bekle) + 1, 60))
                continue
            print(f"Telegram hatası {h.code}: {h.read()[:200]!r}", file=sys.stderr)
            return False
    return False


# ------------------------------------------------------------------- Ana akış
def yukle(yol):
    if yol.exists():
        try:
            return json.loads(yol.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("Uyarı: veri dosyası okunamadı, sıfırdan başlanıyor.", file=sys.stderr)
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
                   help="İlk çalıştırmada mevcut tüm ilanları da kanala gönder")
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
            mevcut[i["id"]].update(baslik=i["baslik"], kurum=i["kurum"], son_tarih=i["son_tarih"])
        else:
            i["ilk_gorulme"] = simdi().isoformat(timespec="seconds")
            mevcut[i["id"]] = i
            yeniler.append(i)

    # 3) Telegram
    if yeniler and not (ilk_calisma and not a.duyur_mevcut):
        yeniler.sort(key=lambda x: x["son_tarih"] or "9999")
        dahil = cfg.get("telegram_kelimeler_dahil", [])
        haric = cfg.get("telegram_kelimeler_haric", [])
        gonderilecek = [i for i in yeniler if telegram_icin_uygun(i, dahil, haric)]
        limit = int(cfg.get("max_mesaj_per_calisma", 15))
        for i in gonderilecek[:limit]:
            metin = mesaj_olustur(i, cfg.get("site_url", ""))
            if a.dry_run or not (token and chat_id):
                print("--- (gönderilmedi) ---\n" + metin + "\n")
            else:
                telegram_gonder(token, chat_id, metin)
                time.sleep(1.5)  # kanal hız sınırı
        fazla = len(gonderilecek) - limit
        if fazla > 0 and not a.dry_run and token and chat_id:
            telegram_gonder(token, chat_id, f"➕ {fazla} yeni ilan daha var: {cfg.get('site_url', '')}")
    elif ilk_calisma and yeniler:
        print(f"İlk çalıştırma: {len(yeniler)} mevcut ilan sessizce kaydedildi (kanala gönderilmedi).")

    # 4) Kaydet
    for i in mevcut.values():
        i.pop("aciklama", None)  # site için gerekli değil, dosyayı küçük tut
    veri = {
        "guncelleme": simdi().isoformat(timespec="seconds"),
        "ilanlar": sorted(temizle(list(mevcut.values())), key=lambda x: x["son_tarih"] or "9999"),
    }
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Tamam: {len(gelen)} ilan okundu, {len(yeniler)} yeni, {len(veri['ilanlar'])} kayıtlı.")


if __name__ == "__main__":
    main()
