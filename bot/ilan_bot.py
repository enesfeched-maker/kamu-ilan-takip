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
import siniflandir as siniflandir_modulu
from siniflandir import akademik_ilan, etiketler, il_adlari, kategori, kpss_durumu, kurum_ici, ogrenim_seviyeleri
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
    harfler = [c for c in metin if c.isalpha()]
    # Başlıkta bir harf küçük kalmış olabilir ("57 SüREKLİ İŞÇİ"): harflerin %85'i büyükse tamamı büyük harfli sayılır.
    if not harfler or not (metin.isupper() or sum(c.isupper() for c in harfler) / len(harfler) >= 0.85):
        return metin
    kisaltmalar = {"KPSS", "YDS", "YÖKDİL", "ALES", "İŞKUR", "TÜBİTAK", "TÜİK", "AFAD", "BDDK", "SPK", "SEDDK", "İETT", "TGA",
                   "VHKİ", "TKGM", "GSB", "TTK", "MEB", "MSB", "SGK", "DSİ", "T.C", "T.C.", "J.GN.K.LIĞININ"}
    def kelime(m):
        s = m.group()
        if s in kisaltmalar or any(c.isdigit() for c in s):
            return s
        s = s.translate(str.maketrans("Iİ", "ıi")).lower()
        if s in {"ve", "ile", "veya"}:
            return s
        return s[0].translate(str.maketrans("iı", "İI")).upper() + s[1:]
    return re.sub(r"[\w.]+", kelime, metin)   # '/' sözcük ayracı: "Öğretmen/Mühendis"


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


KADRO_SATIR_EN_COK = 10


def kadro_ozeti(ilan):
    """Çok kadrolu ilan: 'Toplam N kişi' ve her kadro ayrı satırda, en kalabalıktan başlayarak (12 Ekim 2026: Milli Saraylar'da
    100 güvenlik görevlisi '+6 kadro türü' içinde kaybolmuştu). Tek kadro: olduğu gibi."""
    kadro = ilan.get('kadro') or ''
    m = re.match(r'Toplam\s+(\d+)\s+kişi\s+—\s+(.*)$', kadro)
    parcalar = (m.group(2) if m else kadro).split(' • ')
    sayili = []
    for p in parcalar:
        a = re.match(r'(\d+)\s+(.+)$', p.strip())
        sayili.append((int(a.group(1)), a.group(2)) if a else (0, p.strip()))
    if len(sayili) < 2:
        return okunakli_baslik(kadro)
    sayili.sort(key=lambda x: -x[0])
    satirlar = [f"Toplam {m.group(1)} kişi" if m else ""]
    satirlar += [f"• {okunakli_baslik(ad)}" + (f" — {n}" if n else "") for n, ad in sayili[:KADRO_SATIR_EN_COK]]
    if len(sayili) > KADRO_SATIR_EN_COK:
        satirlar.append(f"• +{len(sayili) - KADRO_SATIR_EN_COK} kadro daha")
    return "\n".join(s for s in satirlar if s)


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
            if alan == 'kadro' and '\n' in kadro_ozeti(ilan):   # çok kadro: ilk satır kalın toplam, sonra her kadro
                ilk, *kalan = kadro_ozeti(ilan).split("\n")
                satirlar.append(f"{etiket} <b>{e(ilk)}</b>" if ilk.startswith('Toplam') else f"{etiket} {e(ilk)}")
                satirlar.extend(e(s) for s in kalan)
                continue
            deger = kadro_ozeti(ilan) if alan == 'kadro' else okunakli_baslik(ilan[alan])
            satirlar.append(f"{etiket} {e(kisalt(deger, sinir))}")
    if ilan.get("son_tarih"):
        saat = ""
        if ilan.get("son_zaman"):
            saat = " • " + datetime.fromisoformat(ilan['son_zaman']).strftime('%H:%M')
        satirlar.append(f"📅 <b>Son başvuru:</b> {tarih_yaz(ilan['son_tarih'])}{saat}")
    else:
        satirlar.extend(["", "⏳ <b>Son başvuru:</b> Resmi ilan üzerinden kontrol edin."])
    # 15 Ekim 2026 kullanıcı kararı: 'İlan ayrıntıları sitemizde ↓' ve 'Kaynak: …' satırları gereksiz (düğme ve kart yeterli)
    etiket = " ".join(etiketler(ilan))
    if etiket:
        satirlar.extend(["", e(etiket)])
    return "\n".join(satirlar)


def tek_satir(ilan):
    """20 Ekim 2026: metinsiz kartın altında tek satır (Telegram araması ve bildirim önizlemesi için)."""
    e = html.escape
    parca = [f"<b>{e(kisalt(okunakli_baslik(ilan.get('kurum') or kisa_baslik(ilan)), 80))}</b>"]
    try:
        from kart_tasarimlari import veri as kart_verisi
        toplam = kart_verisi(ilan)['toplam']
    except Exception:
        toplam = None
    if toplam:
        parca.append(f"{toplam} kişi")
    etiket = " ".join(etiketler(ilan)[:4])
    if etiket:
        parca.append(e(etiket))
    return " · ".join(parca)


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
    c = re.sub(r'(?i)\b(?:iptal\s+)?ilanı\s+ilanı\b', 'ilanı', c).strip()   # "İptal İlanı ilanı iptal edilmiştir" çift sözcüğü
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
    if orijinale_yanit and not iptal and duyuru.get('duzeltme_degisen') in ('tarih', 'basvuru'):
        # 15 Ekim 2026: kısa ve net — yalnız ne değişti
        if duyuru.get('duzeltme_yeni_tarih'):
            return f"📝 <b>Başvuru tarihi değişti</b>\n📅 <b>Yeni son başvuru:</b> {tarih_yaz(duyuru['duzeltme_yeni_tarih'])}"
        from duzeltme import duzeltilen_kisim, _bitisik
        kisim = _bitisik(duzeltilen_kisim(duyuru))
        return "📝 <b>Başvuru şekli değişti</b>" + (f"\n{e(kisalt(_bas_harf_buyut(kisim), 220))}" if kisim else '')
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
    return "\n".join(satirlar)


def site_adi(site_url):
    """Kullanıcıya gösterilen kısa site adı: https://kpsstercihi.com/ -> kpsstercihi.com"""
    return re.sub(r'^https?://(www\.)?', '', site_url or '').rstrip('/')


def utm_ekle(url, site_url, ortam='kanal'):
    """Siteye giden Telegram bağlantısına kaynak etiketi ekler; uygulama içi tarayıcı yönlendireni gizlediği için
    analizde aksi hâlde 'Doğrudan' görünür. Başka alan adına giden bağlantıya dokunmaz."""
    if not url or not site_url or not url.startswith(site_url.rstrip('/')) or 'utm_source=' in url:
        return url
    govde, kare, parca = url.partition('#')
    return govde + ('&' if '?' in govde else '?') + 'utm_source=telegram&utm_medium=' + ortam + kare + parca


def ilan_dugmesi(item, bugun=None):
    """19 Ekim 2026: yeni ilan düğmesi son günü söyler, dikkat çeker."""
    bugun = bugun or simdi().date()
    try:
        son = datetime.strptime(str(item.get('son_tarih') or '')[:10], '%Y-%m-%d').date()
    except ValueError:
        return '👉 Hemen incele'
    kalan = (son - bugun).days
    if kalan < 0:
        return '🔎 İlanı incele'
    if kalan == 0:
        return '⏳ Bugün son gün — Hemen incele'
    if kalan == 1:
        return '⏳ Yarın son gün — Hemen incele'
    return f'⏳ Son gün {son.day} {AY_ADLARI[son.month - 1]} — Hemen incele'


def telegram_gonder(token, chat_id, metin, ilan_linki="", site_url="", foto=None, yanit=None, ek_dugmeler=(),
                    dugme_yazisi='🔎 İlanı incele'):
    """Gönderir; başarıda Telegram message_id'sini (yoksa True), başarısızlıkta False döndürür.
    yanit: bir mesaja yanıt olarak göndermek için message_id (mesaj silinmişse yine de gönderilir).
    ek_dugmeler: [(yazı, site adresi)] — ikişer yan yana; site düğmesi en sona (akşam kartında ilan başına)."""
    url = f"https://api.telegram.org/bot{token}/{'sendPhoto' if foto else 'sendMessage'}"
    alanlar = {
        "chat_id": chat_id,
        "caption" if foto else "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    dugmeler = []
    if ilan_linki:
        # style: Telegram'ın yeşil düğmesi (eski uygulamalar gri gösterir)
        dugmeler.append([{"text": dugme_yazisi, "url": utm_ekle(ilan_linki, site_url), "style": "success"}])
    ek = [{"text": yazi, "url": utm_ekle(adres, site_url)} for yazi, adres in ek_dugmeler or ()]
    if ek:   # 19 Ekim 2026: ilan düğmeleri ikişer yan yana, kısa adlarla; site düğmesi tek kalan ilanın yanına
        if site_url:
            ek.append({"text": "🌐 Tüm ilanlar", "url": utm_ekle(site_url, site_url)})
        dugmeler += [ek[n:n + 2] for n in range(0, len(ek), 2)]
    elif site_url:
        dugmeler.append([{"text": "🌐 Tüm kamu ilanları", "url": utm_ekle(site_url, site_url)}])
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


ISKUR_BEKLEME_SAAT = 2


def iskur_bekliyor(i):
    """İŞKUR kaydı ilk görüldükten sonra ISKUR_BEKLEME_SAAT dolmadıysa True (tarih okunamazsa beklemez)."""
    try:
        gorulme = datetime.fromisoformat(i.get('ilk_gorulme') or '')
    except ValueError:
        return False
    if gorulme.tzinfo is None:
        gorulme = gorulme.replace(tzinfo=TR)
    return simdi() - gorulme < timedelta(hours=ISKUR_BEKLEME_SAAT)


def kopyalari_ele(uygun, mevcut, gonderilen, bekleyen):
    """Aynı gerçek ilanın başka kaynaktaki kaydı (kopya) kanalda zaten paylaşıldıysa — ya da aynı çalışmada birincil kayıt
    paylaşılacaksa — ikincisi tekrar paylaşılmaz: yinelenen kayıt, aynı takma adlar gibi 'işlenmiş' sayılır (gönderilmiş işaretlenir,
    sıradan düşer). kopya.kopya_bul hata verirse hiçbir şey elenmez (gönderim aksamaz)."""
    if len(uygun) == 0:
        return uygun
    try:
        import kopya
        kopyalar = kopya.kopya_bul([i for i in mevcut.values() if not akademik_ilan(i)])
    except Exception as hata:
        print(f'Uyarı: kopya ilanlar bulunamadı, tekrar paylaşım denetimi atlandı: {hata}', file=sys.stderr)
        return uygun
    birincil_of = kopyalar.get('kopya_of') or {}
    uyeler = {b: [m['id'] for m in g] for b, g in (kopyalar.get('uyeler') or {}).items()}
    aday_idleri = {i['id'] for i in uygun}
    once = set(gonderilen)   # bu çağrıda eklenen 'işlenmiş' kayıtlar gerçek paylaşım sayılmaz
    secilen_grup, kalan = set(), []
    for i in uygun:
        kimlik = i['id']
        grup_id = birincil_of.get(kimlik, kimlik)
        diger = [m for m in uyeler.get(grup_id, []) if m != kimlik]
        onceden = any(paylasildi(mevcut[m], once) for m in diger if m in mevcut)
        # aynı çalışmada: grubun birincil kaydı da aday ise o gönderilir; birincil aday değilse gruptan ilk aday
        birincil_bekliyor = kimlik != grup_id and grup_id in aday_idleri
        baska_secildi = grup_id in secilen_grup and kimlik != grup_id and not birincil_bekliyor
        if onceden:
            gonderilen.add(kimlik)
            bekleyen.discard(kimlik)
            print(f"Tekrar paylaşım atlandı (aynı ilan başka kaynakta zaten paylaşıldı): {i['baslik']}")
            continue
        if birincil_bekliyor or baska_secildi:
            # Kardeş kayıt bu çalışmada gönderilecek ama henüz gönderilmedi (sessiz dönem, mesaj sınırı, hata olabilir):
            # bu kayıt işlenmiş SAYILMAZ, sırada kalır. Kardeş gerçekten gönderilince sonraki çalışmada 'onceden' ile düşer.
            # (9 Ekim 2026: iki kopya birbirini işaretleyip Türk Patent ve SSB ilanları hiç paylaşılmamıştı.)
            print(f"Tekrar paylaşım ertelendi (aynı ilan başka kaynakta sırada): {i['baslik']}")
            continue
        if diger:
            secilen_grup.add(grup_id)
        kalan.append(i)
    return kalan


def _parmak_izi(i):
    """(kurum anahtarı, son tarih, toplam kişi, unvanlar): kaynak ve kimlik farklı olsa da aynı ilanı tanımak için."""
    import kurum_sayfasi
    from kurum_gorseli import kurum_anahtari
    from siniflandir import kucuk
    kadro = kurum_sayfasi.kadrolar(i)
    adetler = [a for a, _ in kadro]
    toplam = sum(adetler) if adetler and all(isinstance(a, int) for a in adetler) else None
    try:   # kurum adı yazım farkları ('T.C. ... Anonim Şirketi' / '... A.Ş.') aynı çekirdeğe iner
        import kopya
        import kurum_sayfasi as ks
        kurum = kopya._kurum_cekirdek(i, ks.kurum_kanonik(i.get('kurum')))
    except Exception:
        kurum = kurum_anahtari(i.get('kurum') or '')
    return (kurum, str(i.get('son_tarih') or '')[:10], toplam, {kucuk(ad) for _, ad in kadro if ad})


GENEL_BASLIK_KELIMELERI = {'alacak', 'alınacak', 'alım', 'alımı', 'ilanı', 'ilan', 'personel', 'personeli', 'yılı',
                           'duyurusu', 'kişi', 'adet', 'sözleşmeli', 'kadrolu', 'açıktan', 'için', 'ile', 've'}


def _baslik_kokleri(i):
    """Başlığın kurum adı ve genel sözcükler ('personel alım ilanı', yıl, sayı) atılmış kelimeleri."""
    from siniflandir import kucuk
    baslik = kucuk(i.get('baslik') or '')
    kurum = kucuk(i.get('kurum') or '')
    if kurum and baslik.startswith(kurum):
        baslik = baslik[len(kurum):]
    return {w for w in re.findall(r'\w+', baslik) if len(w) > 2 and not w.isdigit() and w not in GENEL_BASLIK_KELIMELERI}


def ayni_ilan_mi(a, b):
    """Aynı kurum ve aynı son tarihli iki kayıt aynı ilan mı? Kişi sayıları biliniyorsa eşit ve unvanları ortak olmalı;
    bilinmiyorsa başlıklar benzer olmalı ya da biri genel başlıklı ('Personel alım ilanı') olmalı."""
    k1, s1, t1, u1 = _parmak_izi(a)
    k2, s2, t2, u2 = _parmak_izi(b)
    if not (k1 and s1) or (k1, s1) != (k2, s2):
        return False
    if t1 and t2:
        return t1 == t2 and (not u1 or not u2 or bool(u1 & u2))
    b1, b2 = _baslik_kokleri(a), _baslik_kokleri(b)
    if not b1 or not b2:
        return True
    return len(b1 & b2) / len(b1 | b2) >= 0.5


def tekrar_karari(a, b):
    """İki kayıt için botun kendi kararı: 'ayni' | 'farkli' | 'belirsiz'. Son gün farklıysa, kişi sayıları farklıysa, bilinen
    unvanlar ortak değilse ya da kurum çekirdekleri benzemiyorsa 'farkli'; 'belirsiz' olanlar Gemini'ye sorulabilir (yz_tekrar)."""
    s1, s2 = str(a.get('son_tarih') or '')[:10], str(b.get('son_tarih') or '')[:10]
    if not s1 or s1 != s2:
        return 'farkli'
    if ayni_ilan_mi(a, b):
        return 'ayni'
    k1, _, t1, u1 = _parmak_izi(a)
    k2, _, t2, u2 = _parmak_izi(b)
    if t1 and t2 and t1 != t2:
        return 'farkli'
    if u1 and u2 and not (u1 & u2):
        return 'farkli'
    if not k1 or not k2 or len(k1 & k2) / max(1, min(len(k1), len(k2))) < 0.5:
        return 'farkli'
    b1, b2 = _baslik_kokleri(a), _baslik_kokleri(b)
    if len(b1) >= 3 and len(b2) >= 3 and len(b1 & b2) / len(b1 | b2) < 0.34:
        return 'farkli'   # iki özgül başlık birbirine benzemiyor (örn. MSB 'Tabip/Diş Tabibi' ile 'Üniversiteye Öğretmen/Mühendis')
    return 'belirsiz'


def _genel_baslikli_belirsiz(i, g, mevcut):
    """'Aynı' kararı yalnız genel başlığa dayanıyorsa (kişi sayısı bilinmiyor ve başlıklardan biri 'Personel alım ilanı' gibi
    özgül sözcük taşımıyorsa) ve aynı kurumun aynı gün kapanan BAŞKA, g'den farklı bir ilanı da i'ye uyuyorsa True: hangisine ait
    olduğu bilinemez, ilan yutulmaz (21 Ekim 2026: sessizce yanlış ilanı yutma riski)."""
    _, _, t1, _ = _parmak_izi(i)
    _, _, t2, _ = _parmak_izi(g)
    b1, b2 = _baslik_kokleri(i), _baslik_kokleri(g)
    if (t1 and t2) or (b1 and b2):
        return False
    for c in mevcut.values():
        if c is i or c is g or c.get('duyuru_turu') or akademik_ilan(c) or c.get('id') in (i.get('id'), g.get('id')):
            continue
        if str(c.get('son_tarih') or '')[:10] != str(i.get('son_tarih') or '')[:10]:
            continue
        if ayni_ilan_mi(i, c) and tekrar_karari(g, c) == 'farkli':
            return True
    return False


def _yakin_zamanli(a, b, saat=72):
    try:
        z1, z2 = (datetime.fromisoformat(x.get('ilk_gorulme') or '') for x in (a, b))
    except ValueError:
        return True   # tarih okunamazsa elenmez
    z1, z2 = (z if z.tzinfo else z.replace(tzinfo=TR) for z in (z1, z2))
    return abs(z1 - z2) <= timedelta(hours=saat)


def onceden_paylasilmis(i, mevcut, gonderilen):
    """Aynı ilan (ayni_ilan_mi) kanalda zaten paylaşıldıysa paylaşılan kaydın kimliği; yoksa None.
    kopya.kopya_bul'un kaçırdığı durumlar için ikinci kilit (aynı ilan 2-3 kez paylaşılmasın).
    Botun 'belirsiz' dediği ve son 72 saatte paylaşılmış kayıtla benzeyen ilan için Gemini'ye ikinci göz olarak sorulur
    (yz_tekrar: yalnız 'aynı, güven >= 0.9' ise tutulur; her türlü hata/belirsizlikte ilan yayınlanır)."""
    for kimlik in gonderilen:
        g = mevcut.get(kimlik)
        if not g or kimlik == i['id'] or g.get('duyuru_turu') or not paylasildi(g, gonderilen):
            continue
        if ayni_ilan_mi(i, g):
            if _genel_baslikli_belirsiz(i, g, mevcut):
                print(f"Tekrar kararı belirsiz (genel başlık, aynı gün birden çok ilan): {i['baslik'][:70]}")
                continue
            return kimlik
    import yz_tekrar
    if not yz_tekrar.etkin():
        return None
    for kimlik in gonderilen:
        g = mevcut.get(kimlik)
        if not g or kimlik == i['id'] or g.get('duyuru_turu') or not paylasildi(g, gonderilen) or not yz_tekrar.etkin():
            continue
        if not _yakin_zamanli(i, g):
            continue
        karar = tekrar_karari(i, g)
        if karar == 'ayni' and _genel_baslikli_belirsiz(i, g, mevcut):
            karar = 'belirsiz'   # genel başlığa dayanan 'aynı' kararı Gemini'ye sorulur
        if karar != 'belirsiz':
            continue
        sonuc = yz_tekrar.sor(i, g, _parmak_izi(i)[2], _parmak_izi(g)[2])
        print(f"Tekrar sorusu (bot: belirsiz): {i['baslik'][:60]} <> {g['baslik'][:60]} -> "
              f"{'cevap yok, ilan gönderilecek' if not sonuc else ('aynı' if sonuc['ayni'] else 'farklı') + f' (güven {sonuc['guven']:.2f}): {sonuc['neden']}'}")
        if yz_tekrar.tutulsun_mu(sonuc):
            return kimlik
    return None


def tekrarlari_ele(uygun, mevcut, gonderilen, bekleyen):
    kalan = []
    for i in uygun:
        try:
            esi = onceden_paylasilmis(i, mevcut, gonderilen)
        except Exception as hata:   # denetim hatası gönderimi durdurmaz; kopya_bul yine çalışmıştır
            print(f'Uyarı: tekrar denetimi yapılamadı ({type(hata).__name__}): {i["baslik"]}', file=sys.stderr)
            esi = None
        if esi:
            gonderilen.add(i['id'])
            bekleyen.discard(i['id'])
            print(f"Tekrar paylaşım atlandı (aynı kurum, son tarih ve kişi sayısıyla zaten paylaşıldı): {i['baslik']}")
            continue
        kalan.append(i)
    return kalan


LOGO_BEKLEME = timedelta(hours=3)


def logo_beklemesi_doldu(i, simdi_=None):
    if i.get('amblem_hemen'):   # config 'telegram_amblem_hemen': logo beklenmeden amblemle gider
        return True
    try:
        ilk = datetime.fromisoformat(i.get('ilk_gorulme') or '')
    except ValueError:
        return False   # ilk görülme bilinmiyorsa logo beklenir
    ilk = ilk if ilk.tzinfo else ilk.replace(tzinfo=TR)
    return (simdi_ or simdi()) - ilk >= LOGO_BEKLEME


def kurum_amblemi(i):
    """Logo bulunamayan kurum için baş harfli amblem (PNG); yapılamazsa None."""
    try:
        from kart_tasarimlari import bas_harf_amblemi
        return bas_harf_amblemi(i.get('kurum') or i.get('baslik') or '')
    except Exception:
        return None


def logolu_olanlar(gonderilecek, logo_bul=None, simdi_=None):
    """Kurum logosu bulunamayan ilan kanala gitmez; sırada bekler (logo eklenince sonraki taramada gönderilir).
    20 Ekim 2026: 3 saatte logo bulunamazsa ilan kaçmasın diye kurumun baş harfli amblemiyle gider.
    Duyurular (iptal/düzeltme yanıtları) görselsiz gittiği için etkilenmez."""
    logo_bul = logo_bul or kurum_logosu
    kalan, logosuz = [], []
    for i in gonderilecek:
        if i.get('duyuru_turu'):
            kalan.append(i)
            continue
        try:
            logo = logo_bul(i)
        except Exception:
            logo = None
        if not logo and logo_beklemesi_doldu(i, simdi_):
            print(f"::warning::Logo 3 saatte bulunamadı, baş harfli amblemle gönderilecek: {i.get('kurum')} — {i['baslik']}")
            logo = True
        (kalan if logo else logosuz).append(i)
    for i in logosuz:
        print(f"::warning::Kanala gönderilmedi (kurum logosu yok, logo eklenince gönderilecek): {i.get('kurum')} — {i['baslik']}")
    return kalan


def yayina_hazir(gonderilecek, logo_bul=None, veri=None):
    """19 Ekim 2026: kanala yalnız Gemini'nin okuduğu ilan, Gemini'nin okuduğu bilgilerle (kadro, tarih, koşul) gider;
    logosu olmayan ilan gitmez. Duyurular etkilenmez. Gemini adımı hiç çalışmadıysa (anahtar yok) kapı kapalı kalır."""
    import yz_isle
    hazir = []
    for i in gonderilecek:
        tamam, neden = yz_isle.yayina_hazir(i, veri)
        if not tamam:
            print(f"::warning::Kanala gönderilmedi ({neden}): {i.get('kurum')} — {i['baslik']}")
            continue
        if neden == 'iptal':   # bot yeni ilan sanmıştı; Gemini iptal duyurusu okudu: orijinal ilana yanıt olarak gider
            print(f"Gemini iptal duyurusu olarak okudu: {i['baslik']}")
            hazir.append(dict(i, duyuru_turu='İptal'))
            continue
        hazir.append(i if i.get('duyuru_turu') else yz_isle.uygula(i, veri))
    return logolu_olanlar(hazir, logo_bul)


def unvanli(i):
    import kurum_sayfasi
    return bool(kurum_sayfasi.kadrolar(i))


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
        if akademik_ilan(i) or kurum_ici(i) or kimlik in set((cfg.get('elle') or {}).get('gizle') or []):
            bekleyen.discard(kimlik)  # akademik, kurum içi (yeterlik/görevde yükselme/yurt dışı eğitim) ve elle gizlenen ilanlar kanala hiç gitmez
            continue
        if suresi_doldu(i):
            bekleyen.discard(kimlik)
            continue
        if i.get('kaynak_turu') == 'iskur' and not i.get('duyuru_turu') and iskur_bekliyor(i):
            # İŞKUR ikincil kaynak: aynı ilan SBB / Kariyer Kapısı'na düşerse kanala o (esas) kayıt gitsin.
            print(f"Kanal için bekletildi (İŞKUR, {ISKUR_BEKLEME_SAAT} saat): {i['baslik']}")
            continue
        if not (i.get('kurum') or '').strip() and not i.get('duyuru_turu'):
            # Kurumu okunamayan kayıt başka kaynaktaki kopyasıyla eşleştirilemez (12 Ekim 2026: TMSF iki kez paylaşıldı):
            # kanala gitmez, sırada bekler; kurum adı sonradan okunursa normal akışla paylaşılır.
            print(f"Kanala gönderilmedi (kurum adı okunamadı): {i['baslik']}")
            continue
        if i.get('kaynak_turu') == 'sbb' and not i.get('duyuru_turu') \
                and not unvanli(dict(i, **(((cfg.get('elle') or {}).get('alanlar') or {}).get(i['id']) or {}))):   # elle girilen unvan geçerli
            # Unvansız SBB kaydı ('… - 2 ALACAK') kanalda anlamsız görünür ve kopyası zor eşleşir (16 Ekim 2026: Akreditasyon
            # bilişim ilanı ikinci kez gitti): sırada bekler; unvan okunursa ya da kopyası paylaşılırsa normal akış sürer.
            print(f"Kanala gönderilmedi (unvan okunamadı): {i['baslik']}")
            continue
        if telegram_icin_uygun(i, dahil, haric):
            uygun.append(i)
    ilanlar = kopyalari_ele([i for i in uygun if not i.get('duyuru_turu')], mevcut, gonderilen, bekleyen)
    uygun = tekrarlari_ele(ilanlar, mevcut, gonderilen, bekleyen) + [i for i in uygun if i.get('duyuru_turu')]
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
    if tur == 'duzeltme':
        return duzeltme_karari(duyuru, ilanlar, mesajlar, yanitlar, bugun)
    if akademik_ilan(duyuru):
        return {'islem': 'sessiz', 'sebep': 'akademik duyuru', 'referans': None}
    # 21 Ekim 2026 (Elmakaya iptali ÇŞB ve SBB'den iki kez gitti): olay imzası her yolda, kelime kümesiyle kontrol edilir
    from iptal_yaniti import ayni_olay_bildirildi
    if ayni_olay_bildirildi(duyuru, yanitlar, bugun, DUZ_METIN_TEKILLESTIRME_GUN, gun_icinde):
        return {'islem': 'sessiz', 'sebep': 'aynı olay (başka kaynaktan) son 30 günde bildirildi', 'referans': None}
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


def yanit_kaydet(yanitlar, karar, duyuru, gun):
    """Gönderilen iptal duyurusunun anahtarlarını kaydeder: karar yolundaki anahtar + yoldan bağımsız olay imzası."""
    yanitlar[karar['yaz']] = gun
    if duyuru_turu_iptal_mi(duyuru):
        yanitlar[duz_anahtar(duyuru)] = gun


def duzeltme_karari(duyuru, ilanlar, mesajlar, yanitlar, bugun):
    """Düzeltme duyuruları kanalda paylaşılmaz (9 Ekim 2026). 15 Ekim 2026 istisnası: başvuru TARİHİ ya da başvuru
    ŞEKLİ değiştiyse ve orijinal ilan kanalda paylaşılmışsa, orijinal mesaja tek satırlık yanıt gider.
    Bağlantı duzeltme.uygula()'nın yazdığı 'duzeltme_of' alanından gelir (ihtiyatlı eşleştirme)."""
    degisen = duyuru.get('duzeltme_degisen')
    if degisen not in ('tarih', 'basvuru'):
        return {'islem': 'sessiz', 'sebep': 'düzeltme duyuruları paylaşılmıyor', 'referans': None}
    o = next((i for i in ilanlar if i.get('id') == duyuru.get('duzeltme_of')), None)
    if o is None or akademik_ilan(o) or not mesaj_kimligi(o, mesajlar):
        return {'islem': 'sessiz', 'sebep': 'orijinal ilan kanalda paylaşılmadı', 'referans': None}
    if suresi_doldu(o):
        return {'islem': 'sessiz', 'sebep': 'orijinal ilanın süresi doldu', 'referans': None}
    anahtarlar = yanit_anahtarlari('duzeltme', o, False, f"{degisen}:{duyuru.get('duzeltme_yeni_tarih') or ''}")
    if any(k in yanitlar for k in anahtarlar):
        return {'islem': 'sessiz', 'sebep': 'aynı düzeltme daha önce bildirildi', 'referans': None}
    return {'islem': 'gonder', 'orijinal': o, 'referans': None, 'tam': True, 'yaz': anahtarlar[0]}


ILAN_ARASI_SN = 150   # 20 Ekim 2026: taramada en çok 3 ilan, aralarında 2,5 dk (kanal dağınık görünmesin)
TOPLU_SINIR = 950  # sendPhoto başlık sınırı 1024 görünür karakter


def calisma_limiti(cfg, bekleyen_sayisi):
    """Tarama başına mesaj sınırı; kuyruk 5'i geçince 2, 10'u geçince 3 mesaj (birikme erirken kanal boğulmaz)."""
    limit = max(1, int(cfg.get('max_mesaj_per_calisma', 15)))
    if bekleyen_sayisi > 10:
        return max(limit, 3)
    if bekleyen_sayisi > 5:
        return max(limit, 2)
    return limit


def metinsiz_mi(cfg, zaman):
    """19 Ekim 2026 kullanıcı denemesi: config 'telegram_metinsiz_bitis' (ISO) gelene kadar ilan gönderileri yalnız kart
    görseli ve düğmelerle gider (altında metin yok). Akşam/sabah kartları ve duyuru yanıtları etkilenmez.
    19 Ekim 2026 kullanıcı kararı: kalıcı oldu ('telegram_metinsiz': true); metin yalnız sabah ve akşam 8 kartlarında."""
    if cfg.get('telegram_metinsiz') is True:
        return True
    bitis = cfg.get('telegram_metinsiz_bitis')
    if not bitis:
        return False
    try:
        return zaman < datetime.fromisoformat(bitis)
    except (TypeError, ValueError):
        return False


def sessiz_donemde(cfg, zaman):
    """config 'telegram_sessiz_bitis' (ISO, saat dilimli) gelene kadar kanala hiçbir şey gönderilmez."""
    bitis = cfg.get('telegram_sessiz_bitis')
    if not bitis:
        return False
    try:
        bitis = datetime.fromisoformat(bitis)
    except ValueError:
        return False
    if bitis.tzinfo is None:
        bitis = bitis.replace(tzinfo=TR)
    return zaman < bitis


def toplu_zamani(zaman, son_gun):
    """Günde bir kez: İstanbul 09:00'dan sonra ve bugün henüz gönderilmediyse."""
    return zaman.hour >= 9 and son_gun != zaman.date().isoformat()


def toplu_secim(ilanlar, gonderilen, cfg):
    """Son başvurusu bugün..3 gün içinde olan, kanalda daha önce paylaşılmış, akademik/iptal/duyuru olmayan ilanlar."""
    bugun = simdi().date()
    dahil, haric = cfg.get('telegram_kelimeler_dahil', []), cfg.get('telegram_kelimeler_haric', [])
    sonuc = []
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i) or kurum_ici(i) or not i.get('son_tarih'):
            continue
        if not ({i['id'], *i.get('kaynak_kimlikleri', [])} & gonderilen) or suresi_doldu(i):
            continue
        if 0 <= (date.fromisoformat(i['son_tarih']) - bugun).days <= 3 and telegram_icin_uygun(i, dahil, haric):
            sonuc.append(i)
    sonuc.sort(key=lambda i: (i['son_tarih'], i.get('kurum', ''), i['id']))
    return kopyasiz(sonuc, ilanlar)


def _kopya_gruplari(ilanlar):
    """kopya.kopya_bul ile kaynaklar arası kopya grupları: {kimlik: birincil kimlik}. Hata olursa boş (seçim aksamaz)."""
    try:
        import kopya
        return kopya.kopya_bul([i for i in ilanlar if not akademik_ilan(i)]).get('kopya_of') or {}
    except Exception as hata:
        print(f'Uyarı: kopya grupları bulunamadı, yalnız kurum/tarih tekilleştirmesi yapılıyor: {hata}', file=sys.stderr)
        return {}


def kopyasiz(secilen, ilanlar):
    """Aynı gerçek ilanın kopyaları (kopya grubu ya da aynı normalize kurum + son tarih) tek kayda iner; sıra korunur.
    Gruptan en çok meslek ayrıntısı olan kayıt seçilir, eşitlikte ilk kayıt. 9 Ekim 2026: sabah kartında 'Rektörlüğü',
    '(TİBU)' gibi kurum adı farkları yüzünden aynı ilan iki kez çıkıyordu."""
    from kart_tasarimlari import veri as kart_verisi
    kof = _kopya_gruplari(ilanlar)

    def ayrintili(i):
        """Meslek ayrıntısı puanı: 'Alacak/Temin' gibi başlık özetinden çıkan genel satırlar sayılmaz."""
        try:
            return sum(1 for k in kart_verisi(i)['kadrolar'] if not re.search(r'alacak|temin|alım', k['ad'], re.I))
        except Exception:
            return 0

    from kopya import _hostlar
    gruplar, sira = {}, []
    for i in secilen:
        k = kurum_kimligi(i)
        grup = ('g', kof.get(i['id'], i['id']))
        kurum_gun = ('k', i.get('son_tarih'), k[:2] if k else i['id'])
        hostlar = _hostlar(i)
        # Aynı kurum + aynı son gün yalnız FARKLI kaynaktan geliyorsa kopya sayılır. 14 Ekim 2026: SBB'deki iki ayrı MSB ilanı
        # (Deniz Kuvvetleri ve TSK subay alımı, ikisi de 2 Kasım) tek ilana indirilmiş, akşam kartında biri görünmemişti.
        hedef = next((g for g in sira if grup in gruplar[g]['anahtar']
                      or (kurum_gun in gruplar[g]['anahtar'] and not (gruplar[g]['host'] & hostlar))), None)
        if hedef is None:
            gruplar[i['id']] = {'anahtar': {grup, kurum_gun}, 'kayit': i, 'host': set(hostlar)}
            sira.append(i['id'])
            continue
        g = gruplar[hedef]
        g['anahtar'] |= {grup, kurum_gun}
        g['host'] |= hostlar
        if ayrintili(i) > ayrintili(g['kayit']):
            g['kayit'] = i
    return [gruplar[g]['kayit'] for g in sira]


GUN_ADLARI = ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')
AY_ADLARI = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')
SABAH_YENI_EN_COK, SABAH_YENI_EN_AZ = 5, 3
SABAH_SON_GUN_EN_COK = 6


def turkce_tarih(zaman):
    """'5 Ekim Pazartesi' (İstanbul tarihi)."""
    return f"{zaman.day} {AY_ADLARI[zaman.month - 1]} {GUN_ADLARI[zaman.weekday()]}"


def gorunen_uzunluk(metin):
    return len(html.unescape(re.sub(r"<[^>]+>", "", metin)))


def aksam_zamani(zaman, son_gun):
    """Günde bir kez: İstanbul 20:00'den sonra ve bugün henüz gönderilmediyse."""
    return zaman.hour >= 20 and son_gun != zaman.date().isoformat()


def aksam_yeniler(ilanlar, cfg, zaman):
    """Akşam kartı: dün 20:00 (dahil) – bugün 20:00 (hariç) arasında ilk görülen, kanal kurallarına uyan açık ilanlar
    (akademik/iptal/duyuru/kurum içi yok; en çok kadro önce; kaynaklar arası kopyalar tek kayıt)."""
    from kart_tasarimlari import veri as kart_verisi
    dahil, haric = cfg.get('telegram_kelimeler_dahil', []), cfg.get('telegram_kelimeler_haric', [])
    bugun_20 = datetime.combine(zaman.astimezone(TR).date(), datetime.min.time(), tzinfo=TR).replace(hour=20)
    elle = cfg.get('elle') or {}
    gizle, alanlar = set(elle.get('gizle') or []), elle.get('alanlar') or {}
    ilanlar = [dict(i, **alanlar.get(i.get('id'), {})) for i in ilanlar if i.get('id') not in gizle]  # sitedeki elle kararlar
    sonuc = []
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i) or kurum_ici(i) or suresi_doldu(i):
            continue
        if not (i.get('kurum') or '').strip():
            continue
        try:
            gorulme = datetime.fromisoformat(i['ilk_gorulme'])
        except (KeyError, TypeError, ValueError):
            continue
        if gorulme.tzinfo is None:
            gorulme = gorulme.replace(tzinfo=TR)
        if bugun_20 - timedelta(days=1) <= gorulme < bugun_20 and telegram_icin_uygun(i, dahil, haric):
            sonuc.append((-(kart_verisi(i)['toplam'] or 0), i.get('kurum', ''), i['id'], i))
    sonuc.sort(key=lambda s: s[:3])
    return kopyasiz([s[-1] for s in sonuc], ilanlar)


def aksam_mesaj(ilanlar):
    """Akşam kartının metni (bildirim önizlemesinde görünen tek şey): günün yoğunluğuna göre sıcak bir başlık + tek cümle.
    16 Ekim 2026: 'gözünden kaçmasın' tonu; yoğun gün (AKSAM_YOGUN_ESIK+ ilan) ayrıca vurgulanır."""
    kadro = sabah_toplam_kadro(ilanlar)
    n = len(ilanlar)
    ek = f" · {kadro} kadro" if kadro else ""
    if n >= AKSAM_YOGUN_ESIK:
        metin = f"🌙 <b>Bugün yoğun bir gündü: {n} yeni kamu ilanı</b>{ek}\nGözünden kaçan olmasın diye hepsini senin için bir araya topladım."
    elif n > 1:
        metin = f"🌙 <b>Bugün {n} yeni kamu ilanı yayımlandı</b>{ek}\nGözünden kaçan olmasın diye hepsini senin için bir araya topladım."
    else:
        metin = f"🌙 <b>Bugün 1 yeni kamu ilanı yayımlandı</b>{ek}\nGözünden kaçmasın diye akşam bir kez daha hatırlatmak istedim."
    return metin + "\n\n👇 Merak ettiğin ilana dokunman yeterli."


AKSAM_YOGUN_ESIK = 5


from ek_kaynaklar import KURUM_KISALTMALARI
KISA_AD = {ad: kisa for kisa, ad in KURUM_KISALTMALARI.items()}   # düğmede yer kazanmak için: Milli Savunma Bakanlığı -> MSB
AKSAM_DUGME_EN_COK = 7   # kartta görünen satır sayısı kadar (kart_tasarimlari.TOPLU_EN_COK_SATIR)


DUGME_KISA = {'Türk Akreditasyon Kurumu': 'TÜRKAK', 'İskenderun Teknik Üniversitesi': 'İSTE', 'Türk Standardları Enstitüsü': 'TSE',
              'Jandarma Genel Komutanlığı': 'Jandarma', 'Jandarma ve Sahil Güvenlik Akademisi': 'JSGA', 'Türk Patent ve Marka Kurumu': 'TÜRKPATENT',
              'Kültür ve Turizm Bakanlığı': 'KTB', 'Türkiye İş Kurumu': 'İŞKUR',
              'Kamu Gözetimi, Muhasebe ve Denetim Standartları Kurumu': 'KGK', 'Orta Anadolu Kalkınma Ajansı': 'ORAN',
              'İstanbul Kalkınma Ajansı': 'İSTKA', 'Ankara Kalkınma Ajansı': 'Ankara KA',
              'Cumhurbaşkanlığı İletişim Başkanlığı': 'İletişim Bşk.', 'Cumhurbaşkanlığı İletişim': 'İletişim Bşk.',
              'Sigortacılık ve Özel Emeklilik Düzenleme ve Denetleme Kurumu': 'SEDDK',
              'Türkiye Uluslararası İslam, Bilim ve Teknoloji Üniversitesi': 'TİBU'}

DUGME_EN_UZUN = 18   # iki düğme yan yana sığsın (telefon ekranında yarım genişlik)


def dugme_kurumu(kurum):
    """Düğme için kısa kurum adı: bilinen kısaltma (MSB, TÜRKAK); yoksa 'Başkanlığı/Genel Müdürlüğü' atılır,
    'Büyükşehir Belediyesi' -> 'BŞB', 'Belediyesi' -> 'Bld.', 'Üniversitesi' -> 'Üni.'"""
    from kart_tasarimlari import kisa_kurum
    tam = kisa_kurum(kurum)
    for ad in (tam, re.sub(r'\s+Başkanlığı$', '', tam)):
        if ad in KISA_AD or ad + ' Başkanlığı' in KISA_AD:
            return KISA_AD.get(ad) or KISA_AD[ad + ' Başkanlığı']
        if ad in DUGME_KISA:
            return DUGME_KISA[ad]
    ad = re.sub(r'\s+(?:Başkanlığı|Genel Müdürlüğü|Genel Sekreterliği)$', '', tam)
    if ad in DUGME_KISA:
        return DUGME_KISA[ad]
    ad = re.sub(r'\s+Büyükşehir Belediyesi$', ' BŞB', ad)
    ad = re.sub(r'\s+Belediyesi$', ' Bld.', ad)
    ad = re.sub(r'\s+Rektörlüğü$', '', ad)
    ad = re.sub(r'\s+Üniversitesi$', ' Üni.', ad)
    ad = re.sub(r'\s+Kalkınma Ajansı$', ' KA', ad)
    if len(ad) <= DUGME_EN_UZUN:
        return ad
    # 19 Ekim 2026: düğmeler ikişer yan yana; uzun adlar sözcük ortasından kesilmez, kibar kısaltılır
    parantez = re.search(r'\(([^()]{2,12})\)\s*$', ad)
    if parantez and parantez.group(1).isupper() and not re.search(r'Belediye', ad):
        return parantez.group(1)                                      # '... Kurumu (TÜBİTAK)'
    ad = re.sub(r'^(\S+)\s+\([^)]*\)\s+(?:Bld\.|Belediye(?:si| Başkanlığı)?)$', r'\1 Bld.', ad)   # 'Subaşı (YALOVA) Bld.'
    from siniflandir import ILLER, kucuk
    ilk, _, kalan = ad.partition(' ')
    if kalan.endswith(' Bld.') and kucuk(ilk) in {kucuk(il) for il in ILLER}:
        ad = kalan                                                    # 'Edirne Uzunköprü Bld.' -> 'Uzunköprü Bld.'
    if len(ad) <= DUGME_EN_UZUN:
        return ad
    sozcukler = [w for w in re.findall(r'[^\s,()]+', ad) if w.casefold() not in ('ve', 'ile') and w[0].isalpha()]
    if ad.endswith(' Üni.') and 3 <= len(sozcukler) <= 6:
        return ''.join(w[0] for w in sozcukler[:-1]).upper() + 'Ü'      # 'Niğde Ömer Halisdemir Üni.' -> 'NÖHÜ'
    if re.search(r'(?:Bakanlığı|Kurumu|Kurulu|Birliği|İdaresi)$', ad) and 2 <= len(sozcukler) <= 6:
        return ''.join(w[0] for w in sozcukler).upper()               # yerleşik kısaltmalar: YSK, TİHEK, GSB, ÇSGB, TBB
    return ad


def dugme_kisalt(yazi, sinir=DUGME_EN_UZUN):
    """Uzun düğme yazısı sözcük sınırında kısaltılır ('Kamu Gözetimi…'); parantez içi kısaltma varsa o kullanılır."""
    m = re.search(r'\(([^()]{2,12})\)\s*$', yazi)
    if m:
        yazi = m.group(1)
    if len(yazi) <= sinir:
        return yazi
    kes = yazi[:sinir].rsplit(' ', 1)[0].rstrip(',·- ')
    return (kes if len(kes) >= 6 else yazi[:sinir - 1]) + '…'


def kisa_kadro(ad, kurum):
    """Aynı kurumun ilanlarını ayırt eden kısa kadro: kurum adındaki sözcükler atılır, 'Yardımcısı' -> 'Yrd.'"""
    kurum_sozcukleri = {w.casefold() for w in (kurum or '').split()}
    sozcukler = [w for w in ad.split() if w.casefold() not in kurum_sozcukleri] or ad.split()
    return re.sub(r'\bYardımcısı\b', 'Yrd.', ' '.join(sozcukler))


def aksam_dugmeleri(ilanlar, logolar, site_url):
    """Kartın satır sırasıyla (logolu ilanlar önce) ilan başına düğme: 'Kurum' -> sitedeki ilan sayfası.
    Görsel tıklanamadığı için kişi ilgilendiği ilana buradan tek dokunuşla gider."""
    from kart_tasarimlari import veri as kart_verisi, kisa_kurum, toplu_satir
    sirali = [x for x, l in zip(ilanlar, logolar) if l] + [x for x, l in zip(ilanlar, logolar) if not l]
    sonuc = []
    secilen = sirali[:AKSAM_DUGME_EN_COK]
    kurumlar = [dugme_kurumu(kart_verisi(i)['kurum']) for i in secilen]
    for i, kurum in zip(secilen, kurumlar):
        try:
            adres = ilan_sayfasi(i, site_url)
        except ValueError:
            continue
        # 16 Ekim 2026: düğmede yalnız kısaltılmış kurum adı; aynı kurumun iki ilanı varsa kısa kadro adı eklenir (MSB Deniz / TSK)
        ilk_kadro = next((k['ad'] for k in kart_verisi(i).get('kadrolar') or [] if k.get('ad')), '') or re.sub(r'^\d+\s+', '', toplu_satir(i)[1])
        yazi = kurum if kurumlar.count(kurum) == 1 else f"{kurum} · {kisa_kadro(ilk_kadro, kart_verisi(i)['kurum'])}"

        sonuc.append((dugme_kisalt(yazi), adres))
    return sonuc


def sabah_yeniler(ilanlar, gonderilen, cfg, zaman):
    """Dünkü 09:00 (dahil) ile bugünkü 09:00 (hariç) arasında ilk görülen, kanalda paylaşılmış; akademik/iptal/duyuru
    olmayan ilanlar (en çok kadro önce). Sabit sınır: özet geç gitse bile günler arası boşluk/çift sayım olmaz.
    Aynı normalize kurum + aynı son tarih (SBB/İŞKUR kopyaları) tek kayıt."""
    from kart_tasarimlari import veri as kart_verisi
    dahil, haric = cfg.get('telegram_kelimeler_dahil', []), cfg.get('telegram_kelimeler_haric', [])
    bugun_09 = datetime.combine(zaman.astimezone(TR).date(), datetime.min.time(), tzinfo=TR).replace(hour=9)
    sonuc = []
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i) or kurum_ici(i):
            continue
        try:
            gorulme = datetime.fromisoformat(i['ilk_gorulme'])
        except (KeyError, TypeError, ValueError):
            continue
        if gorulme.tzinfo is None:
            gorulme = gorulme.replace(tzinfo=TR)
        if not bugun_09 - timedelta(days=1) <= gorulme < bugun_09:
            continue
        if not ({i['id'], *i.get('kaynak_kimlikleri', [])} & gonderilen) or suresi_doldu(i):
            continue
        if telegram_icin_uygun(i, dahil, haric):
            sonuc.append((-(kart_verisi(i)['toplam'] or 0), i.get('kurum', ''), i['id'], i))
    sonuc.sort(key=lambda s: s[:3])
    return kopyasiz([s[-1] for s in sonuc], ilanlar)


def _tekil_anahtar(i):
    k = kurum_kimligi(i)
    return (i.get('son_tarih'), k[:2] if k else i['id'])


def sabah_acik_sayisi(ilanlar, zaman):
    """Sitedeki 'Başvurusu açık' tanımı: akademik/duyuru/iptal değil, son tarihi var, süresi dolmamış, başlamış."""
    sayi = 0
    for i in ilanlar:
        if i.get('duyuru_turu') or i.get('iptal_edildi') or akademik_ilan(i) or kurum_ici(i) or not i.get('son_tarih') or suresi_doldu(i):
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
        url = utm_ekle(ilan_sayfasi(i, site_url), site_url, 'ozet')
    except ValueError:
        url = ''
    govde = f'<a href="{e(url, quote=True)}">{e(ad)}</a>' if url else e(ad)
    return f"• {govde}" + (f" · <b>{etiket}</b>" if etiket else "")


PAZAR_SOZLERI = (
    "Pazar sakin ama yarın ilanlar yeniden başlıyor. Biz hazırız, sen de hazır ol.",
    "Yeni hafta hareketli başlayabilir. İlk duyan sen ol diye biz buradayız.",
    "Bugün ilan yok ama biz hep hazırız. Yarın ilk haber bizden.",
)


# 15 Ekim 2026: hafta içi her sabah farklı, samimi iki satır (aynı söz her gün tekrarlanmasın).
HAFTA_ICI_SOZLERI = (
    "Yeni bir gün, yeni bir fırsat.\nKahveni al, ilanlara birlikte bakalım.",
    "Bugün belki de beklediğin ilanın günü.\nÇayını koy, birlikte göz atalım.",
    "Emeklerin bir gün mutlaka karşılığını bulacak.\nBugünün ilanları seni bekliyor.",
    "Küçük adımlar büyük kapılar açar.\nBugün de bir adım daha atalım.",
    "Güne güzel bir haberle başlamak dileğiyle.\nİlanlara birlikte bakalım mı?",
    "Hayalindeki kadro bir ilan uzağında olabilir.\nBugün neler var, beraber bakalım.",
    "Sabrın ve emeğin en güzel karşılığını bulsun.\nGünün ilanları hazır.",
    "Yorulduğun günler de geçecek, inan.\nBugünün fırsatlarına birlikte bakalım.",
    "Her başvuru, hedefe biraz daha yakınlaşmak demek.\nBugün de buradayız.",
    "Güzel bir gün olsun, güzel haberler gelsin.\nKahveler hazırsa ilanlara geçelim.",
)


def gunun_sozu(zaman):
    """Sabah özetinin ilk satırı: hafta içi her gün sıradaki söz (15 Ekim 2026 = ilk söz), cumartesi dilek,
    pazar haftalık sırayla (11 Ekim 2026 = ilk söz)."""
    gun = zaman.weekday()
    if gun == 6:
        return PAZAR_SOZLERI[((zaman.date() - date(2026, 10, 11)).days // 7) % len(PAZAR_SOZLERI)]
    if gun == 5:
        return "Emeğimizin boşa gitmemesi dileğiyle, iyi hafta sonları."
    return HAFTA_ICI_SOZLERI[(zaman.date() - date(2026, 10, 15)).days % len(HAFTA_ICI_SOZLERI)]


def sabah_mesaj(yeniler, son_gun, acik_sayisi, site_url, zaman, aranan=None):
    """Sabah özeti metni (HTML): başlık + yeni ilanlar (+ pazartesi aranan meslekler). Son başvurusu yaklaşanlar yalnız
    görselde; açık ilan sayısı ve site satırı yazılmaz, site düğmede (10 Ekim 2026 kararı: laf kalabalığı yok).
    Sınır (~950 görünür karakter) aşılırsa yeni listesi kısaltılır."""
    ust = f"☀️ <b>Günaydın — {turkce_tarih(zaman)}</b>\n{gunun_sozu(zaman)}"
    son_gun_anahtar = {x for i in son_gun for x in (('id', i['id']), ('k', _tekil_anahtar(i)))}
    # Son gün listesinde (görselde) olan yeni ilan metinde tekrar yazılmaz (başlıktaki sayı yine hepsini sayar).
    yeni_satirlari = [_ilan_satiri(i, site_url) for i in yeniler
                      if ('id', i['id']) not in son_gun_anahtar and ('k', _tekil_anahtar(i)) not in son_gun_anahtar]
    kadro = sabah_toplam_kadro(yeniler)
    yeni_baslik = f"🆕 <b>Son 24 saatte {len(yeniler)} yeni ilan</b>" + (f" · {kadro} kadro" if kadro else "")

    def olustur(ny):
        parcalar = [ust]
        if yeniler:
            satirlar = yeni_satirlari[:ny] + ([f"+{len(yeni_satirlari) - ny} ilan daha"] if len(yeni_satirlari) > ny else [])
            parcalar.append("\n".join([yeni_baslik, *satirlar]))
        if aranan:
            parcalar.append(aranan_satiri(aranan, site_url))
        return "\n\n".join(parcalar)

    ny = min(len(yeni_satirlari), SABAH_YENI_EN_COK)
    while ny > 0 and gorunen_uzunluk(olustur(ny)) > TOPLU_SINIR:
        ny -= 1
    return olustur(ny)

def _bas_harf(kelime):
    return " ".join(("İ" if k[0] == "i" else "I" if k[0] == "ı" else k[0].upper()) + k[1:] for k in kelime.split())


def aranan_satiri(kelimeler, site_url):
    """Haftalık: merak edilen ama açık ilanı olmayan meslekler + taban puanları bağlantısı (gözetleme izlenimi vermeyen dil)."""
    satir = "💬 <b>Bu hafta merak edilenler:</b> " + " · ".join(html.escape(_bas_harf(k)) for k in kelimeler)
    if site_url:
        url = utm_ekle(site_url.rstrip("/") + "/puanlar/", site_url, "ozet")
        satir += f'\nŞu an maalesef açık ilanları yok; çıktığında ilk burada paylaşacağız. <a href="{html.escape(url, quote=True)}">Taban puanlarına bak →</a>'
    return satir


# Tek başına meslek anlatmayan aramalar ('çocuk': çocuk gelişimi mi, bakıcı mı belirsiz) duyurulmaz.
ARANAN_GENEL = {'cocuk', 'memur', 'personel', 'isci', 'kamu', 'ilan', 'kpss', 'devlet', 'belediye', 'hastane', 'universite', 'okul'}


def haftalik_aranan(cfg, ilanlar, zaman, getir=None):
    """Pazartesi sabahı analizden (/aranan) çok aranıp sonuç çıkmayan kelimeleri alır; şu an açık ilanı olanları eler.
    Analiz erişilemezse ya da GitHub Actions dışında (testler) boş döner; sabah özeti bundan etkilenmez."""
    if zaman.weekday() != 0:
        return []
    if getir is None:
        if not os.environ.get("GITHUB_ACTIONS"):
            return []

        def getir():
            url = cfg.get("analiz_url", "https://api.kpsstercihi.com").rstrip("/") + "/aranan"
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "kpss-tercihi-bot"}), timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
    try:
        kelimeler = [k["kelime"] for k in (getir() or {}).get("kelimeler", []) if k.get("kelime")]
    except Exception as e:  # noqa: BLE001 - analiz hatası özeti durdurmaz
        print(f"Aranan kelimeler alınamadı: {e}")
        return []
    acik = [norm(f"{i.get('baslik', '')} {i.get('kadro', '')}") for i in ilanlar
            if not akademik_ilan(i) and not suresi_doldu(i)]
    adaylar = [k for k in kelimeler if not any(norm(k) in a for a in acik) and norm(k) not in ARANAN_GENEL]
    # 'veteriner' ile 'veteriner hekim' gibi tekrarlarda uzun olan kalır.
    return [k for k in adaylar if not any(k != u and norm(k) in norm(u) for u in adaylar)][:5]


def suresi_doldu(ilan):
    if ilan.get('son_zaman'):
        return datetime.fromisoformat(ilan['son_zaman']) <= simdi()
    return bool(ilan.get('son_tarih') and date.fromisoformat(ilan['son_tarih']) < simdi().date())


def detay_taze(ilan):
    from resmi_detay import SURUM
    if ilan.get('kk_detay_surumu', 1) != SURUM:
        return False   # eski okuyucuyla alınmış ayrıntı (kısaltılmış şartlar): yeniden okunur
    try:
        return simdi() - datetime.fromisoformat(ilan['detay_guncelleme']) < timedelta(hours=12)
    except (KeyError, TypeError, ValueError):
        return False


def detay_bekletir(ilan, cfg):
    """Kanal gönderimi resmi Kariyer Kapısı ayrıntısını bekliyor mu? SBB/İŞKUR/ÇŞB kayıtları bu ayrıntıyı hiç almaz;
    13 Ekim 2026: kk_detay_surumu kontrolü bu kayıtları da süresiz bekletiyordu (Mevlana KA paylaşılmadı)."""
    return bool(cfg.get('resmi_detaylari_oku', False)) and ilan.get('kaynak_turu') not in ('sbb', 'iskur', 'csb') \
        and not detay_taze(ilan)


# ------------------------------------------------------------------- Ana akış
def yukle(yol):
    if yol.exists():
        try:
            return json.loads(yol.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sys.exit("Veri dosyası bozuk. Tekrar mesaj göndermemek için tarama durduruldu.")
    return {"guncelleme": None, "ilanlar": []}


def telegram_icin_uygun(ilan, dahil, haric):
    if akademik_ilan(ilan) or kurum_ici(ilan):
        return False
    metin = (ilan["baslik"] + " " + ilan.get("kurum", "")).lower()
    if dahil and not any(k.lower() in metin for k in dahil):
        return False
    return not any(k.lower() in metin for k in haric)


def ilan_gorseli(i, hatirlatma, logo=None):
    """Telegram kartı: yeni tasarım (afiş/bilet); hata olursa eski kart ile devam eder (gönderim aksamasın)."""
    try:
        from kart_tasarimlari import telegram_karti
        return telegram_karti(i, logo=logo, hatirlatma=hatirlatma)
    except Exception as exc:
        print(f'Yeni ilan kartı oluşturulamadı ({type(exc).__name__}); eski kart kullanılıyor.', file=sys.stderr)
    tarih = tarih_yaz(i['son_tarih']) if i.get('son_tarih') else 'Resmi ilandan kontrol edin'
    if i.get('son_zaman'):
        tarih += ' · ' + datetime.fromisoformat(i['son_zaman']).strftime('%H:%M')
    return gorsel_olustur(
        okunakli_baslik(i.get('kurum') or i['baslik']),
        okunakli_baslik(i.get("kadro", "")) or kisa_baslik(i),
        okunakli_baslik(i.get('yer', '')), tarih,
        kalan_gun_metni(i['son_tarih']).capitalize() if hatirlatma else '',
        kaynak=i.get('kaynak', 'Kariyer Kapısı'), logo=logo)


def siniflandir(ilan):
    """Site filtreleri ve kişisel bot için öğrenim, kategori, il ve KPSS alanlarını günceller."""
    siniflandir_modulu.tazele(ilan)


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
    for k in mevcut.values():  # eski kayıtlarda yazıyla 'None' saklanmış son tarih: boş say (yeniden okunsun)
        if str(k.get('son_tarih')).strip() in ('None', 'null'):
            k['son_tarih'] = ''
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
        # Akıştan düşmüş ama son tarihi hiç okunamamış Kariyer Kapısı kayıtları da yeniden denenir (en çok 5;
        # 22 Eylül 2026'da okunamayan 4 ilan süresi dolduğu hâlde sitede açık kalmıştı).
        gelen_kimlik = {g['id'] for g in gelen}
        sinir = (simdi() - timedelta(days=60)).isoformat()
        eksikler = [k for k in mevcut.values() if k['id'] not in gelen_kimlik and not k.get('son_tarih')
                    and k.get('kaynak_turu') not in ('sbb', 'iskur', 'csb') and not k.get('duyuru_turu')
                    and 'kariyerkapisi.gov.tr/IlanDetay' in (k.get('link') or '') and (k.get('ilk_gorulme') or '') >= sinir][:5]
        for i in [mevcut[g['id']] for g in gelen] + eksikler:
            if i.get('kaynak_turu') in ('sbb','iskur','csb'):
                continue
            local_detail=yerel.get('detaylar',{}).get(i['id'],{})
            if detay_taze(local_detail) and (local_detail.get('detay_guncelleme','')>i.get('detay_guncelleme','')):
                i.pop('kadro_ortak', None)   # yeni okumada ortak koşul kalmadıysa eskisi sayfada kalmasın
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
    # Düzeltmeleri orijinal ilana bağla (sitede uyarı; açıkça verilen yeni son tarih orijinale işlenir).
    try:
        import yz_isle   # 20 Ekim 2026: botun yeni ilan sandığı süre uzatmasını Gemini yakalar
        for i in mevcut.values():
            if yz_isle.sure_uzatma_isaretle(i):
                print(f"Gemini süre uzatması olarak okudu: {i['baslik']}")
    except Exception as exc:
        print(f'Uyarı: süre uzatmaları işaretlenemedi ({type(exc).__name__})', file=sys.stderr)
    try:
        import duzeltme
        print(f'{duzeltme.uygula(list(mevcut.values()), simdi().date())} düzeltme duyurusu orijinal ilana bağlandı.')
    except Exception as exc:
        print(f'Uyarı: düzeltmeler bağlanamadı ({type(exc).__name__}: {str(exc)[:160]})', file=sys.stderr)
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
    import yz_tekrar   # Gemini yalnız "aynı ilan mı?" sorusu için, yalnız gönderim adımında (config: yz_tekrar_acik)
    yz_tekrar.ayarla(cfg.get('yz_tekrar_acik') is True and not a.prepare and not a.dry_run)
    gonderilecek = telegram_sirasi(mevcut, gelen, yeniler, gonderilen, bekleyen,
                                  ilk_calisma, a.duyur_mevcut, cfg)
    if not a.prepare:   # logosuz ilan sıranın başını tıkamasın diye sınırdan önce ayıklanır
        hemen = set(cfg.get('telegram_amblem_hemen') or [])
        gonderilecek = yayina_hazir([dict(i, amblem_hemen=True) if i['id'] in hemen else i for i in gonderilecek])
    # İlan başına hatırlatma kaldırıldı (geçmiş hatirlatilan korunur, yeni kayıt eklenmez);
    # yerine günde bir kez sabah özeti (yeni ilanlar + son başvurusu yaklaşanlar + açık ilan sayısı) gönderilir.
    mesajlar = dict(veri.get('telegram_mesajlari', {}))
    yanitlar = dict(veri.get('telegram_duyuru_yanitlari', {}))
    toplu_gun = veri.get('telegram_toplu_hatirlatma_gunu')
    sabah = None
    if toplu_zamani(simdi(), toplu_gun):
        sabah_yeni = []  # 10 Ekim 2026: yeni ilanlar gun icinde tek tek paylasiliyor; sabah ozetinde listelenmez
        import yz_isle
        sabah_son_gun = [x for x in map(yz_isle.uygula, toplu_secim(gelen, gonderilen, cfg))
                         if not x.get('duyuru_turu') and not x.get('yz_akademik')]   # Gemini: iptal/akademik kartta yer almaz
        sabah_acik = sabah_acik_sayisi(gelen, simdi())
        if sabah_yeni or sabah_son_gun or sabah_acik:  # üçü de boşsa sessizce atlanır, gün işaretlenmez
            sabah = (sabah_yeni, sabah_son_gun, sabah_acik)
    aksam_gun = veri.get('telegram_aksam_gunu')
    aksam = aksam_yeniler(gelen, cfg, simdi()) if aksam_zamani(simdi(), aksam_gun) else []
    if aksam:
        import yz_isle
        aksam = [x for x in map(yz_isle.uygula, aksam) if not x.get('duyuru_turu') and not x.get('yz_akademik')]
    kuyruk = ([('sabah', sabah)] if sabah else []) + ([('aksam', aksam)] if aksam else []) + \
             [('duyuru' if i.get('duyuru_turu') else 'ilan', i) for i in gonderilecek]
    if sessiz_donemde(cfg, simdi()):
        # Sessiz dönemde hiçbir şey gönderilmez; ilanlar sırada (telegram_bekleyen) kalır ve dönem bitince
        # max_mesaj_per_calisma sınırıyla taramalara yayılarak tek tek paylaşılır.
        print(f"Telegram sessiz dönemde ({cfg['telegram_sessiz_bitis']} kadar): "
              f"{len(gonderilecek)} ilan sırada bekliyor.")
        kuyruk = []
    limit = calisma_limiti(cfg, len(gonderilecek))
    site_url = cfg.get('site_url', '')
    hata = False
    adet = 0
    ertelenen = 0
    ilan_gonderildi = False

    def mesaj_kaydet(kimlik, mid):
        if isinstance(mid, int) and not isinstance(mid, bool):
            mesajlar[kimlik] = mid

    for tur, i in ([] if a.prepare else kuyruk[:limit]):
        if tur == 'sabah':
            yeni_l, son_gun_l, acik = i
            metin = sabah_mesaj(yeni_l, son_gun_l, acik, site_url, simdi(), haftalik_aranan(cfg, gelen, simdi()))
            if a.dry_run:
                print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
                continue
            try:
                from kart_tasarimlari import sabah_ozeti_karti, toplu_son_gun_karti
                foto = toplu_son_gun_karti(son_gun_l, simdi(), [kurum_logosu(x) for x in son_gun_l]) if son_gun_l else sabah_ozeti_karti(yeni_l, acik, simdi(), son_gun=son_gun_l)
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
        if tur == 'aksam':
            metin = aksam_mesaj(i)
            if a.dry_run:
                print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
                continue
            logolar = [kurum_logosu(x) for x in i]
            try:
                from kart_tasarimlari import yeni_ilanlar_karti
                foto = yeni_ilanlar_karti(i, simdi(), logolar)
            except Exception as exc:
                print(f'Akşam kartı oluşturulamadı ({type(exc).__name__}); yalnız metin gönderilecek.', file=sys.stderr)
                foto = None
            try:
                ek = aksam_dugmeleri(i, logolar, site_url)
            except Exception as exc:
                print(f'Akşam ilan düğmeleri hazırlanamadı ({type(exc).__name__}).', file=sys.stderr)
                ek = []
            mid = telegram_gonder(token, chat_id, metin, '', site_url, foto=foto, ek_dugmeler=ek) if (token and chat_id) else False
            if not mid:
                hata = True
                break
            aksam_gun = simdi().date().isoformat()  # gün işareti yalnız başarıda yazılır
            adet += 1
            print(f"Telegram'a akşam kartı gönderildi: {len(i)} yayımlanan ilan")
            time.sleep(3.2)
            continue
        elle_alan = ((cfg.get('elle') or {}).get('alanlar') or {}).get(i.get('id'))
        if elle_alan and elle_alan.get('son_tarih') and elle_alan.get('kadro'):
            # 16 Ekim 2026: ayrıntı servisi yanıt vermeyen ilanın bilgileri resmî sayfadan elle girildiyse beklemeden gönderilir
            i = dict(i, **{k: v for k, v in elle_alan.items() if not k.startswith('_')})
        elif detay_bekletir(i, cfg):
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
                # düzeltme sayfası orijinale bağlı: düğme doğrudan güncel bilgili orijinal ilan sayfasını açar
                hedef = ilan_sayfasi(orijinal if (orijinal is not None and not duyuru_turu_iptal_mi(i)) else i, site_url)
            except ValueError:
                hedef = ''
            mid = telegram_gonder(token, chat_id, metin, hedef, site_url, yanit=yanit) if (token and chat_id) else False
            if not mid:
                hata = True
                break
            gonderilen.add(i['id'])
            bekleyen.discard(i['id'])
            mesaj_kaydet(i['id'], mid)
            yanit_kaydet(yanitlar, karar, i, simdi().date().isoformat())
            if orijinal is not None and duyuru_turu_iptal_mi(i) and karar['tam']:
                orijinal['iptal_edildi'] = i['id']  # kısmi (tek kadro) iptallerde ilan açık kalır
            adet += 1
            print(f"Telegram'a {'iptal' if duyuru_turu_iptal_mi(i) else 'düzeltme'} duyurusu gönderildi"
                  f"{' (orijinal ilana yanıt)' if orijinal is not None else ''}: {i['baslik']}")
            time.sleep(3.2)
            continue
        metin = tek_satir(i) if metinsiz_mi(cfg, simdi()) else mesaj_olustur(i, site_url)
        if a.dry_run:
            print('--- (önizleme, gönderilmedi) ---\n' + metin + '\n')
            continue
        try:
            foto = ilan_gorseli(i, False, kurum_logosu(i) or kurum_amblemi(i))
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
        if ilan_gonderildi:
            time.sleep(ILAN_ARASI_SN)
        mid = telegram_gonder(token, chat_id, metin, hedef, site_url, foto=foto,
                              dugme_yazisi=ilan_dugmesi(i)) if (token and chat_id) else False
        ilan_gonderildi = True
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
        "telegram_aksam_gunu": aksam_gun,
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
