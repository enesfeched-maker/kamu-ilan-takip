---
name: ustun-video
description: KPSS rakiplerinin (YouTube, TikTok) kendi ortalamasını belirgin aşan videolarını bulur, neden tuttuğunu konu ve kalıp olarak çıkarır, KPSS Tercihi'nin otomatik video biçimlerine uyarlanmış öneriler verir. "Rakipler ne paylaşıyor", "ne tutuyor", "viral KPSS videoları", "rakip analizi", "hangi videoyu yapalım" denince ya da bir rakip hesap verilince kullan.
---

# Üstün video avı

Bir videoyu ham izlenmesiyle değil, kendi hesabının medyanına göre değerlendir. 1 milyon aboneli kanalda 100 bin
sıradandır; 5 bin aboneli kanalda 100 bin bir işarettir. Ölçü `kat` = izlenme / hesabın medyan izlenmesi.

## Veri

- Bütün rakipler: `python bot/sosyal_arastir.py rakipler --adet 30`
  `sosyal/rakipler.json` listesini okur, YouTube'da Shorts ve uzun videoları ayrı medyanla ölçer, KPSS/kamu dışı
  konuları eler (`--hepsi` elemeyi kapatır). Kat ≥ 2 olanları sıralar.
- Tek hesap: `python bot/sosyal_arastir.py videolar <kaynak>` (`@kanal`, kanal kimliği `UC…`, `tt:@hesap`).
- Yeni rakip bulunursa `sosyal/rakipler.json` dosyasına ekle (`ad`, `kaynak`, `not`).
- Instagram rakip verisi betikte yok; yerelde vidIQ (`vidiq_ig_profile_reels`, `vidiq_instagram_tiktok_outlier_search`)
  varsa onunla tamamla.
- Kendi hesabımızın ölçümleri `sosyal/istatistik.json` ve `sosyal/gecmis.json` dosyalarındadır; karşılaştırma için kullan.

## Yöntem

1. Kat ≥ 2 videoları al. Ders anlatımı (genel tekrar, konu anlatımı) bizim işimiz değil; onları ayrı say, öneriye katma.
2. Her üstün videoyu şu alanlarla etiketle:
   - **Konu:** puan → nereye, belirli kurum alımı (Sağlık 38 bin gibi), KPSS'siz/işçi alımı, sonuç açıklandı → ne
     yapmalı, kişisel hikâye, takvim.
   - **Kanca kalıbı:** sayı + puan ("50 puanla 500 atama"), soru ("Hangi puanla atanırım?"), kişisel itiraf
     ("63 puanla atandım"), aciliyet/haber ("Sonuçlar açıklandı!"), liste ("atanabileceğin kurumlar").
   - **Zamanlama:** sonuç açıklanması, büyük alım ilanı gibi bir olaya mı denk geldi? (Tarih yoksa sıra numarasından
     tahmin etme; "bilinmiyor" yaz.)
3. Aynı konu ve kalıp birden fazla hesapta tutuyorsa güçlü sinyaldir; tek hesapta tek videoysa zayıf.
4. Her güçlü sinyali bizim üretim hattına eşle. KPSS Tercihi videoları kodla otomatik üretilir; öneri bu biçimlerden
   birine girmeli:
   - günlük Reels türleri: kimler / meslek / düzey (bkz. `bot/sosyal_motor.py`, `reels` biçimleri)
   - sohbet reels (`sosyal/ozel` ve `sira.json` akışı)
   - tek seferlik özel video: `sosyal/ozel/ozel-<ad>.json` + `sosyal-ozel.yml`
   - haftalık veri dizisi (`bot/haftalik.py`), hikâye ve karusel (`bot/sosyal_gorsel.py`)

## Çıktı

`sosyal-is/arastirma/YYYY-AA-GG-ustun-video.md` dosyasına yaz, kullanıcıya özetini ver:

```markdown
# Üstün videolar — {tarih}
{hesap sayısı} hesap, {video sayısı} video tarandı; kat ≥ 2: {n} (ders anlatımı hariç {m})

| Hesap | Kat | İzlenme | Konu | Kanca kalıbı | Adres |

## Güçlü sinyaller
1. {konu + kalıp} — {kaç hesapta, hangi katlarla}

## Bizim için öneriler (en çok 3)
- Biçim: {kimler/meslek/düzey/sohbet/özel} — Başlık taslağı — Veri kaynağı (hangi ilan/puan verisi) — Neden
```

## Kurallar

- Sayılar yalnız betik çıktısından; tahmin yazma, yuvarlarken "yaklaşık" de.
- Rakibin başlığını, görselini, kurgusunu kopyalama; konuyu ve kalıbı al, içeriği bizim resmî verimizle kur.
- Başlık taslakları `sosyal/voice.md`'ye uyar: "şok", "müjde", "kaçırma", "hemen", atama vaadi yok. Rakiplerde sık
  görülen "Şok olduk", "ATANDIM" gibi kalıplar bize uymaz.
- Akademik ve kurum içi ilanlar önerilmez.
- Öneri koda dönüşecekse ayrı PR ile yapılır; bu beceri yalnız araştırır ve önerir.
