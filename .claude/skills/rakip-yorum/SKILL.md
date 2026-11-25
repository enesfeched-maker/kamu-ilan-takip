---
name: rakip-yorum
description: Rakip KPSS videolarının yorumlarından adayların gerçek sorularını, kafa karışıklıklarını ve kullandıkları dili çıkarır; bunları site asistanına, kısa cevaplara ve video soru havuzuna aday olarak dönüştürür. "Yorumları incele", "insanlar ne soruyor", "rakibin yorumlarına bak", "asistana ne eklemeliyiz" denince ya da bir YouTube/TikTok video adresi verilip içgörü istenince kullan.
---

# Rakip yorum madenciliği

Amaç, KPSS Tercihi'nin cevaplaması gereken soruları rakiplerin yorum alanından bulmak. Çıktı bir rapor değil, iş:
asistan için eksik cevaplar, kısa cevap adayları ve video konuları.

## Veri

- **YouTube:** `python bot/sosyal_arastir.py yorumlar <video-adresi> --adet 200`
  En beğenilen yorumları yazar adı olmadan getirir; her yoruma kaba etiket koyar (`soru`, `puan`, `kurum`, `kpsssiz`).
  JSON `sosyal-is/arastirma/` altına düşer (git'e girmez).
- **Hangi videolar:** Kullanıcı adres vermediyse önce `python bot/sosyal_arastir.py rakipler` çalıştır, ortalamasının en
  az 2 katı tutan, yorumu bol 3–5 videoyu seç. Ders anlatımı (genel tekrar, coğrafya vb.) atlanır; atama, puan, alım,
  tercih videoları alınır.
- **TikTok yorumları:** betikte yok. Yerel oturumda vidIQ araçları (`vidiq_tiktok_comment_list`) varsa onunla al; yoksa
  TikTok'u atla ve raporda söyle.
- `yt-dlp` yoksa: `python -m pip install -q yt-dlp`.

## Yöntem

1. Etiket yalnız ön elemedir. Her yorumu kendin oku; dualar, tebrikler, şakalar elenir.
2. Kalan yorumları şu kümelere ayır:
   - **Puan → nereye:** "72 puanla lise mezunu nereye girerim" türü. Puan aralığını ve öğrenim düzeyini not et.
   - **Kadro/şart:** mezun olunan bölüm bir kadroya uyuyor mu, yaş, boy, sağlık şartı, KPSS'siz alım.
   - **Takvim:** alım ne zaman, sonuç ne zaman, tercih kılavuzu ne zaman.
   - **Program/destek:** İŞKUR Gençlik, KYK gibi kamu programları.
   - **Kaygı/yanlış bilgi:** "tasarruf tedbiri var mı", "bu sene alım yok diyorlar".
3. Her küme için sıklığı (kaç yorum) ve toplam beğeniyi yaz; sırayı buna göre koy.
4. Her kümeyi KPSS Tercihi'nin elindekiyle karşılaştır:
   - `docs/asistan/bilgi.json` (asistanın bildiği soru-cevaplar; kaynağı `bot/asistan_bilgi.py`, `bot/yz_gorunurluk.py`,
     `bot/rehberler.py`)
   - sitedeki araçlar: /nereye/ (puanla nereye), bölüm sayfaları, /sonuclar/
   Cevabı zaten varsa "var" de ve hangi sayfa olduğunu yaz. Yoksa "eksik" de.

## Çıktı

`sosyal-is/arastirma/YYYY-AA-GG-rakip-yorum.md` dosyasına yaz, kullanıcıya özetini ver:

```markdown
# Rakip yorum madenciliği — {tarih}
Kaynak: {video sayısı} video, {yorum sayısı} yorum ({adresler})

## En çok sorulan
| Küme | Yorum | Beğeni | Bizde | Örnek (kısaltılmış, adsız) |

## Eksik cevaplar (öncelik sırasıyla)
1. Soru → önerilen kısa cevap (resmî kaynağa dayanmıyorsa "kaynak gerekir" yaz) → nereye eklenir

## Video konuları
- Soru kalıbı → hangi biçim (kimler / meslek / düzey / sohbet / özel)

## Adayların dili
- Yorumlarda sık geçen ifadeler (başlık ve soru cümlesi yazarken kullanılacak)
```

## Kurallar

- Depo herkese açık: yorum metni ve yorum sahibinin adı depoya işlenmez. Rapor `sosyal-is/` altında kalır. Depoya
  yalnız bundan çıkan iş girer (asistan cevabı, soru cümlesi, video tanımı) ve o da ayrı PR ile.
- Örnek yorumu kısalt ve adsız ver; telefon, e-posta, isim varsa çıkar.
- Cevap önerirken sayı uydurma; kural ve puan bilgisi resmî ilandan ya da sitenin verisinden gelir.
- Video ve soru metinlerinde `sosyal/voice.md` geçerli: sıcak ton, emir kipi yok; "kaçırma", "hemen", "şok", "müjde",
  atama vaadi yok.
- Rakibin videosunu, başlığını ya da görselini kopyalama; yalnız adayların neyi sorduğunu öğren.
