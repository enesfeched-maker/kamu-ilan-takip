"""Kariyer Kapısı ilan sayfasının kullandığı herkese açık resmi veri servisi."""
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from resmi_ag import url_ac

TR = timezone(timedelta(hours=3))
API = "https://api.kariyerkapisi.gov.tr/api/"
SURUM = 3   # 2: tüm kadroların tam ayrıntısı (kadro_detay); 3: biçimden bağımsız koşul bölümleri + ortak koşullar (kosul_ayristir)
# eski sürümle okunmuş kayıt taze sayılmaz, yeniden okunur


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
        secilen.append(kisalt(sinav, 400))
    if egitim and egitim != sinav:
        secilen.append(kisalt(egitim, 600))
    if not secilen:
        secilen = [kisalt(p, 300) for p in parcalar if re.search(r"mezun|yaşını|tecrübe|deneyim", p, re.I)][:1]
    return "\n".join(secilen)


OGRENIM_GRUBU = (('ön lisans', 'onlisans'), ('önlisans', 'onlisans'), ('lisans', 'lisans'), ('ortaöğretim', 'ortaogretim'),
                 ('lise', 'ortaogretim'))


def _kucuk(s):
    return (s or '').replace('I', 'ı').replace('İ', 'i').lower()


def kadro_ayrintisi(rol):
    """Bir alt ilanın (kadro grubunun) TAM bilgisi: unvan, il, öğrenim grubu, sınav usulü ve özel şart maddeleri (kısaltılmaz).
    12 Ekim 2026: Milli Saraylar'da 11 kadrodan yalnız 3'ünün kısaltılmış şartı alınmış, öğrenim yalnız 'lisans' görünmüştü."""
    alanlar, maddeler, ozel = {}, [], False
    for s in satirlar(rol.get('ilanMetni')):
        m = re.match(r'(Unvanı|Kadro Adedi|Görev İli|Öğrenim Grubu|Sınav Usulü)\s*:\s*(.*)$', s, re.I)
        if m and not ozel:
            alanlar[_kucuk(m.group(1))] = m.group(2).strip()
            continue
        if re.match(r'(Özel Şartları|Aranan Şartlar|Başvuru Şartları)\s*:?\s*$', s, re.I):
            ozel = True
            continue
        if not ozel:
            continue
        madde = re.match(r'^\d{1,2}\s*[-.)]\s*(.*)$', s)
        if madde:
            maddeler.append(madde.group(1).strip())
        elif maddeler:
            maddeler[-1] += ' ' + s
        else:
            maddeler.append(s)
    grup = _kucuk(alanlar.get('öğrenim grubu'))
    ogrenim = next((d for ad, d in OGRENIM_GRUBU if ad in grup), '') if grup else ''
    iller = [yer_duzelt(k['il']) for k in rol.get('kontenjanList') or [] if k.get('il')]
    adet = sum(k['kontenjan'] for k in rol.get('kontenjanList') or []
               if isinstance(k.get('kontenjan'), int) and not isinstance(k.get('kontenjan'), bool) and k['kontenjan'] > 0)
    return {'unvan': alanlar.get('unvanı') or ' '.join(satirlar(rol.get('ilanBaslik') or rol.get('unvan'))),
            'adet': adet or None, 'iller': list(dict.fromkeys(iller)), 'ogrenim': ogrenim,
            'sinav': alanlar.get('sınav usulü', ''), 'maddeler': [re.sub(r'\s+', ' ', x).strip() for x in maddeler if x.strip()]}


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
    with url_ac(req, timeout=10) as response:
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
    logo=ana.get('logo_Path') or ''
    logo='https://kariyerkapisi.gov.tr/UPS/'+logo if re.fullmatch(r'[a-zA-Z0-9_-]+\.(?:png|jpg|jpeg|webp)',logo,re.I) else None
    sonuc = {"kurum_logo":logo,"son_tarih": bitis[:10] if bitis else None, "son_zaman": bitis,
            "baslangic_zaman": baslangic, "yer": " • ".join(sorted(yerler)),
            "kadro": kadro, "ilan_turu": (ana.get("ilanTuru") or "").rstrip(", "),
            "ozet": ozet, "sartlar": sartlar, "sart_kadro_sayisi": len(alt),
            "basvuru_notu": kisalt(notlar[0], 450) if notlar else "",
            "detay_guncelleme": datetime.now(TR).isoformat(timespec="seconds"), "kk_detay_surumu": SURUM}
    # Her kadronun tam bilgisi; öğrenim düzeyleri ve puan türleri TÜM kadrolardan (ilk birkaçından değil).
    # Koşullar biçimden bağımsız bölümlere ayrılır; tüm kadrolarda aynı olan maddeler bir kez (kadro_ortak) tutulur.
    from kosul_ayristir import ayir
    ayrinti = [kadro_ayrintisi(rol) for rol in alt]
    ortak, ozel = ayir([rol.get('ilanMetni') for rol in alt])
    for a, bl in zip(ayrinti, ozel):
        a['bolumler'] = bl
        a['maddeler'] = [m for _, ms in bl for m in ms]
    ortak_metin = ' '.join(m for _, ms in ortak for m in ms)
    if ortak:
        sonuc['kadro_ortak'] = ortak
    if any(a['maddeler'] or a['ogrenim'] for a in ayrinti) or ortak:
        from siniflandir import ogrenim_seviyeleri
        duzeyler, puanlar = set(), set()
        for a in ayrinti:
            metin = ' '.join(a['maddeler']) + ' ' + a['sinav'] + ' ' + ortak_metin
            duzeyler.update([a['ogrenim']] if a['ogrenim'] else ogrenim_seviyeleri({'ozet': metin}))
            puanlar.update(re.findall(r'(?:KPSS\s?-?|\b)P\s?-?(\d{1,3})\b', metin))   # P3, KPSSP3, KPSSP-4, (P94)
        sonuc['kadro_detay'] = ayrinti
        if duzeyler:
            sonuc['belge_ogrenim'] = [d for d in ('lisans', 'onlisans', 'ortaogretim') if d in duzeyler]
        if puanlar:
            sonuc['puan_turleri'] = sorted({'P' + p for p in puanlar}, key=lambda p: int(p[1:]))
    return sonuc


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
