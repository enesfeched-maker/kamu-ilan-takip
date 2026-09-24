"""Kariyer Kapısı ilan sayfasının kullandığı herkese açık resmi veri servisi."""
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

TR = timezone(timedelta(hours=3))
API = "https://api.kariyerkapisi.gov.tr/api/"


def satirlar(metin):
    metin = html.unescape(metin or "")
    metin = re.sub(r"(?i)<(?:br\s*/?|/p|/div|/li)>", "\n", metin)
    metin = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", "", metin)
    metin = re.sub(r"<[^>]+>", " ", metin)
    metin = re.sub(r"\[/?(?:b|i|u|s|size|color|font|justify|left|right|center|url|list|img|table|tr|td)(?:=[^\]]*)?\]", "", metin, flags=re.I)
    return [re.sub(r"\s+", " ", s).strip() for s in metin.splitlines() if s.strip()]


def kisalt(metin, limit):
    if len(metin) <= limit:
        return metin
    return metin[:limit - 1].rsplit(" ", 1)[0] + "…"


def sart_ozeti(metin):
    parcalar = []
    for satir in satirlar(metin):
        parcalar.extend(re.split(r"(?<=[.;])\s+(?=[A-ZÇĞİÖŞÜa-zçğıöşü0-9])", satir))
    parcalar = [re.sub(r"^\s*(?:\d+|[a-zçğıöşü])[).\-]\s*", "", p).strip() for p in parcalar]
    egitim = next((p for p in parcalar if re.search(r"mezun olmak|mezun bulun|mezun olma|mezunu olmak", p, re.I)), "")
    sinav = next((p for p in parcalar if re.search(r"KPSS|P93|P94|P3\b", p, re.I)
                  and re.search(r"en az|asgari|almış|aranma", p, re.I)), "")
    secilen = []
    if sinav:
        secilen.append(kisalt(sinav, 185))
    if egitim and egitim != sinav:
        secilen.append(kisalt(egitim, 185 if sinav else 300))
    if not secilen:
        secilen = [kisalt(p, 300) for p in parcalar if re.search(r"mezun|yaşını|tecrübe|deneyim", p, re.I)][:1]
    return "\n".join(secilen)


def yer_duzelt(metin):
    parcalar = list(dict.fromkeys(re.sub(r"\s+", " ", p).strip().translate(str.maketrans("Iİ", "ıi")).lower()
                                 for p in metin.split("/")))
    return " / ".join(parcalar).translate(str.maketrans("iı", "İI")).upper()


def zaman(deger):
    if not deger:
        return None
    d = datetime.fromisoformat(deger.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=TR)
    return d.astimezone(TR).isoformat(timespec="seconds")


def api_oku(yol, kimlik):
    req = urllib.request.Request(API + yol,
        data=json.dumps({"ilanGuid": kimlik}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "kamu-ilan-takip/2.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status == 204:
            raise ValueError("İlan ayrıntısı artık yayımlanmıyor")
        return json.load(response)


def detay_coz(ana, alt):
    if not isinstance(ana, dict) or not ana.get("ilanBaslik") or not isinstance(alt, list):
        raise ValueError("Resmi veri biçimi tanınmadı")
    bitis = zaman(ana.get("bitTarih"))
    baslangic = zaman(ana.get("basTarih"))
    yerler, kadrolar, sartlar, secilen_unvanlar = set(), Counter(), [], set()
    for rol in alt:
        unvan = " ".join(satirlar(rol.get("unvan") or rol.get("ilanBaslik")))
        for kontenjan in rol.get("kontenjanList") or []:
            if kontenjan.get("il"):
                yerler.add(yer_duzelt(kontenjan["il"]))
            adet = kontenjan.get("kontenjan")
            if isinstance(adet, int) and not isinstance(adet, bool) and adet > 0:
                kadrolar[unvan] += adet
        # Alıntılar kendi kadro başlığı altında kalır; bir kadronun şartı diğerine genellenmez.
        secilen = sart_ozeti(rol.get("ilanMetni"))
        if secilen and unvan not in secilen_unvanlar:
            secilen_unvanlar.add(unvan)
            sartlar.append({"kadro": kisalt(rol.get("ilanBaslik") or unvan, 110),
                            "metin": secilen})
    ana_satirlar = satirlar(ana.get("ilanMetni"))
    # Başvuru usulündeki özel yükümlülükleri görünür tut.
    notlar = [s for s in ana_satirlar if re.search(r"şahsen|posta ile|elden|kargo", s, re.I)]
    genel = [s for s in ana_satirlar if re.search(r"KPSS|mezun|alınacaktır|istihdam edil", s, re.I)
             and len(s) > 60]
    ozet = kisalt(genel[0], 520) if genel else kisalt(" ".join(ana_satirlar), 520)
    toplam = sum(kadrolar.values())
    kadro = " • ".join(f"{n} {unvan}" for unvan, n in kadrolar.items())
    if len(kadrolar) > 1:
        kadro = f"Toplam {toplam} kişi — " + kadro
    return {"son_tarih": bitis[:10] if bitis else None, "son_zaman": bitis,
            "baslangic_zaman": baslangic, "yer": " • ".join(sorted(yerler)),
            "kadro": kadro, "ilan_turu": (ana.get("ilanTuru") or "").rstrip(", "),
            "ozet": ozet, "sartlar": sartlar[:3], "sart_kadro_sayisi": len(alt),
            "basvuru_notu": kisalt(notlar[0], 450) if notlar else "",
            "detay_guncelleme": datetime.now(TR).isoformat(timespec="seconds")}


def detay_oku(link):
    url = urllib.parse.urlparse(link)
    kimlik = urllib.parse.parse_qs(url.query).get("i", [""])[0]
    if (url.scheme != "https" or url.hostname != "kariyerkapisi.gov.tr"
            or url.path.lower() != "/ilandetay"
            or not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", kimlik)):
        raise ValueError("Resmi ilan bağlantısı tanınmadı")
    ana = api_oku("ilan/GetIlanPreviewPublic", kimlik)
    alt = api_oku("altilan/GetAltIlanInfoByIlanIdPublic", kimlik)
    return detay_coz(ana, alt)
