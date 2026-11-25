---
name: konu-nabzi
description: KPSS ve kamu alımları alanında bu hafta neyin konuşulduğunu YouTube'daki en yeni videolar, rakiplerin son paylaşımları ve bizim açık ilanlarımızla birlikte okuyup haftanın 3–5 konusunu önerir. "Bu hafta ne paylaşalım", "gündem ne", "trend konular", "konu bul", "içerik planı" denince kullan.
---

# Konu nabzı

Soru şu: bu hafta adayların aklındaki konu ne, ve bizde o konuya ait resmî veri var mı? İkisinin kesiştiği yer
haftanın konusudur. Yalnız gündemde olup verimiz olmayan konu öneri olmaz.

## Veri

1. **YouTube'da yeni yüklenenler** (her sorgu için en yeni 20):
   ```
   python bot/sosyal_arastir.py ara "kpss alım" --yeni
   python bot/sosyal_arastir.py ara "personel alımı" --yeni
   python bot/sosyal_arastir.py ara "kpss tercih" --yeni
   python bot/sosyal_arastir.py ara "işçi alımı kpss şartsız" --yeni
   ```
   Gündemdeki bir kurum ya da olay görürsen ("Sağlık Bakanlığı 38 bin") o adla bir arama daha yap.
2. **Rakiplerin son videoları:** `python bot/sosyal_arastir.py rakipler --adet 15` (yalnız son 15; yeni olana bak).
3. **Bizim verimiz:** sitenin açık ilanları ve son başvuru tarihleri (`docs/` altındaki ilan verisi; canlıda
   https://kpsstercihi.com), `sosyal/gecmis.json` (son paylaştıklarımız, tekrar etmemek için).
4. Google Trends eşleşmesi `bot/sosyal_motor.py` içinde zaten var; aynı işi burada tekrarlama.

## Yöntem

1. Aynı konunun birden fazla kanalda son günlerde işlenmesi ve yüksek izlenmesi gündem işaretidir. Tek videoluk
   konu zayıf sinyaldir.
2. Her gündem konusunu bizim verimizle eşle: açık ilan var mı, son başvuru ne zaman, kaç kadro, hangi öğrenim düzeyi.
3. Son 7 günde paylaştığımız konuyu tekrar önerme; farklı açı varsa (ör. "kimler başvurabilir" yerine "puan şartı")
   açıkça yaz.
4. Konuları şu sırayla koy: son başvurusu yakın büyük alım > gündemde olup verimiz olan konu > kalıcı soru
   (puan → nereye).

## Çıktı

`sosyal-is/arastirma/YYYY-AA-GG-konu-nabzi.md` dosyasına yaz, kullanıcıya kısa liste ver:

```markdown
# Konu nabzı — {tarih}

| # | Konu | Gündem kanıtı (kanal, izlenme, adres) | Bizdeki veri | Biçim | Neden şimdi |

## Bu hafta paylaşmayalım
- {konu} — neden (verimiz yok / geçen hafta paylaştık / akademik / kurum içi)
```

## Kurallar

- Kanıtsız konu yazma; her satırda en az bir video adresi ya da bizim ilan sayfamız olsun.
- Sayıları yalnız betik çıktısından ve resmî ilandan al.
- `sosyal/voice.md` geçerli. Akademik ve kurum içi ilanlar önerilmez.
- Bu beceri öneri üretir; paylaşım otomatik hat tarafından yapılır. Yeni biçim ya da özel video gerekiyorsa ayrı PR.
