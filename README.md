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
6. **Çalıştır.** Actions sekmesi > "İlanları tara" > Run workflow. İlk çalıştırma mevcut ilanları kanala göndermeden sessizce kaydeder. Sonraki çalıştırmalarda sadece yeni ilanlar gider. Mevcut ilanları da kanala göndermek istersen workflow'daki komutu `python bot/ilan_bot.py --duyur-mevcut` yap, bir kez çalıştır, geri al.

Bundan sonra yaklaşık 30 dakikada bir kendi kendine çalışır.

## Ayarlar (config.json)

- `telegram_kelimeler_dahil`: doluysa kanala sadece başlığında bu kelimelerden biri geçen ilanlar gider.
- `telegram_kelimeler_haric`: başlığında bu kelimeler geçen ilanlar kanala gitmez. Site hepsini gösterir.
- `max_mesaj_per_calisma`: bir çalıştırmada en fazla kaç ilan mesajı atılacağı.

## İlk çalıştırmadan sonra kontrol

21 Eylül 2026 tarihinde resmi sayfada tüm filtreler boş bırakılarak üretilen `https://kariyerkapisi.gov.tr/RSS` adresiyle 27 ilan doğrulandı. Kurum başlıktaki ` - ` ayracından alınır; `category` kurum değil, ilan türüdür. Canlı akışta son başvuru tarihi alanı bulunmuyor. `pubDate` veya başlıktaki rastgele bir tarih son başvuru tarihi kabul edilmez. Bu nedenle tarih sıralaması, kırmızı uyarılar ve 7 gün filtresi ancak açıkça son başvuru tarihi belirtilen kayıtlarda çalışır; tarihsiz kayıtlar için başvurunun açık olduğu garanti edilmez. Scraping yapılmaz.

Alanları kontrol etmek için:

```
python bot/ilan_bot.py --dump
```

## Notlar

- Site ve kanal resmi değildir, bunu açıkça belirt. Veriler Kariyer Kapısı'ndan gelir.
- Token'ı asla dosyaya yazma, sadece Secrets'a koy.
- GitHub, 60 gün hareketsiz kalan repolarda zamanlanmış işleri durdurabilir. Arada Actions sekmesine bak.
