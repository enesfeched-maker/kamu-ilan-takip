# Kamu İlan Takip portalı

Site GitHub Pages üzerinde, mevcut adresinde çalışır. Ücretli servis veya yeni sunucu gerekmez.

## Yeni özellikler

- Kurum, başlık, kadro ve mevcut koşul alıntılarında Türkçe arama.
- Kaynaktaki görev yerlerine, ilan türüne ve son tarihe göre filtreleme.
- Bu tarayıcıda kaydetme, üç ilanı karşılaştırma ve takvim dosyası indirme.
- Ayrıntı ekranı, benzer ilanlar ve üç başvuru rehberi.
- Koyu tema, mobil düzen, erişilebilir klavye kontrolleri.
- Her taramada üretilen kalıcı HTML ilan sayfaları ve `sitemap.xml`.
- Tarihi geçmiş ilanları açık ilanlardan çıkarma; kaynak ayrıntısı eskiyse uyarı.

Ana sayfadaki son kontrol zamanı RSS taramasını, ayrıntılardaki kontrol zamanı resmî ayrıntıların okunduğu zamanı gösterir. GitHub çalıştırıcısının ayrıntı servisine erişim sorunu devam ederse yeni ayrıntılar kendiliğinden tamamlanmış sayılmaz.

## Sponsor alanını açmak

`docs/sponsors.json` başlangıçta kapalıdır; boş reklam kutuları görünmez. Gerçek bir kampanya için `enabled` değerini `true` yapıp aşağıdaki yapıyla sidebar ve/veya feed alanını doldurun:

```json
{
  "enabled": true,
  "sidebar": {
    "title": "Gerçek kampanya başlığı",
    "description": "Kısa ve doğru kampanya açıklaması",
    "url": "https://reklamverenin-gercek-adresi.example"
  },
  "feed": null
}
```

Örnek adresi yayımlamayın; gerçek reklamverenin adresiyle değiştirin. Yalnız HTTPS bağlantıları kabul edilir. Başlık ve açıklama düz metin olarak işlenir, çalıştırılabilir HTML kabul edilmez. Alanlar “REKLAM · SPONSORLU” etiketi taşır, dış bağlantılar `rel=sponsored` kullanır. İlan sırası reklama göre değişmez.

AdSense veya başka bir reklam ağı bu sürümde bağlanmadı. Gerçek yayıncı hesabı, ağ onayı ve hizmetin gerektirdiği gizlilik/tercih ayarları ayrıca tamamlanmalıdır. Gelir veya ağ kabulü garanti edilmez. Sahte yayıncı kimliği veya ads.txt kaydı eklenmedi.

## Yayın ve içerik

GitHub Actions `bot/site_uret.py` ile ayrıntı sayfalarını oluşturur ve mevcut Pages yayınına dahil eder. Üretilen `docs/ilan/` sayfalarını elle değiştirmeyin. Kaynak `docs/ilanlar.json` dosyasıdır; eski bir yerel dosyayla gönderim geçmişini ezmeyin.

Arama motoruna siteyi tanıtırken kullanılabilecek site haritası:
https://enesfeched-maker.github.io/kamu-ilan-takip/sitemap.xml

Gizlilik, veri kaynağı, iletişim ve reklam açıklamaları portalda bulunur. İletişim bağlantısı mevcut GitHub Issues sayfasına gider. Ayrı bir iletişim e-postası belirlendiğinde değiştirilebilir. Analiz veya reklam ağı açılırsa gizlilik açıklamasını gerçek uygulamaya göre güncelleyin.

## Yerel doğrulama

`node --check docs/portal.js`

`python bot/site_uret.py`

`python -m http.server 8765 --directory docs`

Sadece bu görevde oluşturulan portal dosyaları, sayfa üreticisi ve iş akışı değişikliği yayımlanmalıdır. Bot anahtarları ve gizli değerler hiçbir site dosyasına eklenmemelidir.
