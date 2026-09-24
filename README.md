# Kamu İlan Takip

Kariyer Kapısı'ndaki yeni kamu ilanlarını Telegram kanalına gönderir ve herkesin bakabileceği bir sitede son başvuru tarihine göre listeler. Sunucu gerekmez: GitHub Actions çalıştırır, GitHub Pages yayınlar. İkisi de ücretsiz.

## Kurulum

1. **Repo aç.** GitHub'da yeni bir public repo oluştur, bu klasördeki her şeyi yükle (`.github` klasörü dahil).
2. **Telegram botu.** Telegram'da @BotFather'a `/newbot` yaz, verdiği **token'ı** kaydet. Sonra herkese açık bir kanal oluştur (ör. `@kamuilan_takip`) ve botu kanala **yönetici** olarak ekle (mesaj gönderme yetkisiyle).
3. **RSS linki.** kariyerkapisi.gov.tr/RSS/RssLinkiAl sayfasında Kurum, İlan Türü ve İl'i boş bırakıp "RSS Linkini oluştur"a bas. Çıkan linki `config.json` içindeki `rss_urls` listesine yapıştır.
4. **Gizli bilgiler.** Repo > Settings > Secrets and variables > Actions > New repository secret:
   - `TELEGRAM_BOT_TOKEN` = BotFather token'ı
   - `TELEGRAM_CHAT_ID` = kanal adı, ör. `@kamuilan_takip`
5. **Site.** Repo > Settings > Pages > Source: **GitHub Actions**. İş akışı `/docs` klasörünü her taramanın ardından yayınlar. Çıkan adresi `config.json` içindeki `site_url` alanına yaz. `docs/index.html` içindeki `TELEGRAM_KANAL` değerine kanal linkini yaz (`https://t.me/kamuilan_takip`).
6. **Çalıştır.** Actions sekmesi > "İlanları tara" > Run workflow. İlk çalıştırma mevcut ilanları kanala göndermeden sessizce kaydeder. Sonraki çalıştırmalarda yeni ilanlar gider. Mevcut ilanları da göndermek için "Mevcut ilanları da Telegram'a gönder" seçeneğini işaretle. Başarıyla gönderilenler tekrar gönderilmez; sınırı aşanlar ve başarısız gönderimler sonraki taramaya saklanır.

Bundan sonra yaklaşık 30 dakikada bir kendi kendine çalışır.

## Ayarlar (config.json)

- `telegram_kelimeler_dahil`: doluysa kanala sadece başlığında bu kelimelerden biri geçen ilanlar gider.
- `telegram_kelimeler_haric`: başlığında bu kelimeler geçen ilanlar kanala gitmez. Site hepsini gösterir.
- `max_mesaj_per_calisma`: bir çalıştırmada en fazla kaç ilan mesajı atılacağı.
- `resmi_detaylari_oku`: resmi ilan sayfasının kullandığı herkese açık Kariyer Kapısı veri servisinden şehir, kadro/kontenjan, şartlardan seçili alıntılar ve başvuru tarihlerini tamamlar. Bu projede kullanıcının izniyle açıktır. Ayrıntılar 12 saat saklanır. Ayrıntıya ulaşılamayan ilan eksik mesajla gönderilmez; tekrar denenir.

## İlk çalıştırmadan sonra kontrol

İlan keşfi resmi `https://kariyerkapisi.gov.tr/RSS` akışından yapılır. RSS'teki `category` ilan türüdür; `pubDate` son başvuru tarihi değildir. Ayrıntılar, resmi ilan sayfasındaki JavaScript'in çağırdığı `https://api.kariyerkapisi.gov.tr/api/ilan/GetIlanPreviewPublic` ve `altilan/GetAltIlanInfoByIlanIdPublic` servislerinden alınır. Yalnızca RSS'te bulunan resmi ilan kimlikleri sorgulanır; giriş gerektiren bilgiler okunmaz.

Son başvuru, servisin `bitTarih` alanından saat bilgisiyle alınır. Şehir ve kontenjanlar kadro kayıtlarından gelir. Şartlar, kadro başlığı altında kaynaktan seçilen kısa alıntılardır; otomatik uygunluk değerlendirmesi değildir. Bazı kurumlar ayrıntıları bu alanlara koymadığı için her ilanda her alan bulunmayabilir. Eksik bilgiler tahmin edilmez. Tam koşullar ve güncel değişiklikler için resmi bağlantı esastır. Telegram mesajları HTML biçimlendirme ve yerel bağlantı düğmeleri kullanır.

Alanları kontrol etmek için:

```
python bot/ilan_bot.py --dump
```

## Notlar

- Site ve kanal resmi değildir, bunu açıkça belirt. Veriler Kariyer Kapısı'ndan gelir.
- Token'ı asla dosyaya yazma, sadece Secrets'a koy.
- GitHub, 60 gün hareketsiz kalan repolarda zamanlanmış işleri durdurabilir. Arada Actions sekmesine bak.
