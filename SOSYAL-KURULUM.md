# Sosyal medya otomatik paylaşım — kurulum

Sistem her gün **08:30** ve **20:30**'da bir konu seçer, kareleri ve dikey videoyu üretir, Instagram Reels,
YouTube Shorts ve TikTok'a gönderir (`.github/workflows/sosyal.yml`).

- Konu seçimi: `bot/sosyal_motor.py` (haber > son gün > büyük alım > yeni ilanlar > kategori > puan rehberi; Google Trends eşleşmesi öne çıkarır).
- Tasarım: `bot/sosyal_tasarim.py` (sarı zemin, kırmızı çerçeve, siyah kutu: alanın en çok izlenen biçimi).
- Yayın: `bot/sosyal_yayinla.py` (resmî API'ler; anahtarı tanımlı olmayan platform atlanır).
- Her paylaşım GitHub'da **Releases** bölümünde `sosyal-YYYYAAGG-sabah/aksam` adıyla durur: kareler, video ve açıklama.
  Hesaplar bağlanmadan önce önizleme buradan izlenir.
- Büyük bir açıklama olduğunda `config.json` → `sosyal.haberler` listesine eklenir; o gün ilk sırada paylaşılır.

Anahtarlar yalnız GitHub'a girilir: depo → **Settings → Secrets and variables → Actions → New repository secret**.

## 1. Instagram (tam otomatik)

1. Instagram uygulaması → Ayarlar → Hesap türü ve araçlar → **Profesyonel hesaba geç** (İçerik üreticisi ya da İşletme).
2. https://developers.facebook.com → Uygulamalarım → **Uygulama oluştur** → kullanım durumu
   "Instagram'da mesajları ve içerikleri yönet".
3. Uygulamada **Instagram → API setup with Instagram login** → "Generate access tokens" bölümünde
   **Add account** ile Instagram hesabına giriş yap → **Generate token**.
4. Ekranda görünen iki değeri sır olarak gir:
   - `IG_KULLANICI_ID` — hesabın sayısal kimliği
   - `IG_ERISIM_ANAHTARI` — oluşturulan anahtar (60 gün geçerli, bot haftada bir yeniler)

## 2. Anahtar yenileme izni (önerilir)

Instagram anahtarının 60 günde bir elle yenilenmemesi için:
GitHub → Settings (hesap) → Developer settings → **Fine-grained tokens** → yalnız bu depo, izin
**Secrets: Read and write** → oluşturulan anahtarı `SOSYAL_GH_ANAHTARI` sırrı olarak gir.

## 3. YouTube Shorts

1. https://console.cloud.google.com → yeni proje → **YouTube Data API v3** → Enable.
2. **OAuth consent screen** → External → uygulama adı ve e-posta → kapsam `youtube.upload` →
   **Publish app** (yayında değilse anahtar 7 günde düşer).
3. **Credentials → Create OAuth client ID → Web application**; yönlendirme adresi:
   `https://developers.google.com/oauthplayground`
4. https://developers.google.com/oauthplayground → sağ üstte dişli → "Use your own OAuth credentials" →
   istemci kimliği ve sırrını yaz → kapsam `https://www.googleapis.com/auth/youtube.upload` → Authorize
   (YouTube kanalının hesabıyla) → **Exchange authorization code for tokens**.
5. Sırlar: `YT_ISTEMCI_KIMLIGI`, `YT_ISTEMCI_SIRRI`, `YT_YENILEME_ANAHTARI` (refresh token).
6. Google'ın ücretsiz denetimi bitene kadar videolar **gizli** yüklenir. Denetim başvurusu:
   "YouTube API Services – Audit and Quota Extension Form".

## 4. TikTok

1. https://developers.tiktok.com → TikTok hesabıyla giriş → **Manage apps → Connect an app**.
2. Ürünler: **Login Kit** + **Content Posting API**; kapsamlar `user.info.basic`, `video.upload`
   (inceleme sonrası `video.publish`).
3. Bağlantı adımında yönlendirme ve kodu anahtara çevirme işini birlikte yapacağız.
4. Sırlar: `TT_ISTEMCI_ANAHTARI`, `TT_ISTEMCI_SIRRI`, `TT_YENILEME_ANAHTARI`.
5. İnceleme bitene kadar video her gün TikTok'ta **gelen kutusuna taslak** olarak düşer: popüler bir ses
   seçip paylaşmak tek dokunuş. İnceleme onaylanınca depo değişkeni `TT_MOD=dogrudan` yapılır.

## Elle çalıştırma

Actions → **Sosyal medya paylaşımı** → Run workflow. "Platformlara gönder" kapalıysa yalnız önizleme
sürümü üretilir ve geçmişe yazılmaz.
