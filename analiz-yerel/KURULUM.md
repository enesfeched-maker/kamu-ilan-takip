# Yerel analiz toplayıcısı (Cloudflare'sız)

`analiz/src` içindeki Worker kodu **değiştirilmeden** bu bilgisayarda Node ile çalışır. Veri `analiz-yerel/veri/analiz.sqlite` dosyasındadır (git dışı). D1 kotası yoktur; bildirim botu kotanın tamamını kullanır.

## Mimari

```
tarayıcı --https--> Tailscale Funnel (*.ts.net) --> 127.0.0.1:8787 (sunucu.js) --> SQLite dosyası
```

- Sunucu yalnız `127.0.0.1`'i dinler; internete tek kapı Funnel'dır. Port açmak, sabit IP gerekmez.
- Ziyaretçi IP'si yalnız günlük tuzlu özet için kullanılır, saklanmaz (eskisi gibi). Ülke/şehir bilgisini Cloudflare veriyordu; yerelde boş kalır.
- Günlük bakım 00:30 UTC (03:30 TR) sonrası çalışır; bilgisayar o saatte kapalıysa açılınca telafi eder.
- Bilgisayar kapalıyken gelen olaylar kaybolur (analiz için kabul edilebilir).

## Kurulum

1. **Node**: sürüm 22.13 veya yenisi (kontrol: `node --version`).
2. **Tailscale**: https://tailscale.com/download/windows adresinden kur, hesapla giriş yap.
3. **Funnel izni** (bir kez, tarayıcıda): https://login.tailscale.com/admin/dns → *MagicDNS* ve *HTTPS Certificates* açık olsun; *Access controls* sayfasında Funnel için `nodeAttrs` içinde `funnel` özniteliği verilsin (Tailscale ilk `funnel` komutunda sihirbaz bağlantısı verir).
4. **Toplayıcıyı kur ve başlat** (PowerShell):
   ```powershell
   cd analiz-yerel
   .\kurulum.ps1
   ```
   Panel anahtarını gizli girişle sorar, `.env` yazar, oturum açılınca başlayan "KPSS Analiz Toplayici" görevini kurar. Çıktıda `Yanıt: kpss-analiz` görmelisin.
5. **Funnel'ı aç**:
   ```powershell
   tailscale funnel --bg 8787
   tailscale funnel status
   ```
   `status` çıktısındaki `https://<bilgisayar>.<tailnet>.ts.net` adresi **yeni API adresin**dir.
6. **Doğrula**: `https://<adres>/` → `kpss-analiz`; `https://<adres>/populer` → JSON.

## Geçiş (siteyi yeni adrese yönlendirme)

Henüz yapılmadı; adres belli olunca ayrı bir PR ile:

| Dosya | Değişecek |
|---|---|
| `docs/a.js` | `URL_` sabiti (`.../o`) |
| `docs/portal.js` | `POPULER_URL` |
| `docs/puanlar/puanlar.js` | `/aranan` adresi |
| `config.json` | `analiz_url` (bot `/aranan` için) |

Sıra: yeni toplayıcıyı birkaç gün **yan yana** çalıştır (site hâlâ eski Worker'a yazar), panelde (`https://<adres>/panel`) çalıştığını gör, sonra yukarıdaki adresleri değiştir. Eski Worker'ı (`kpss-analiz`) en son kapat/sil; geçmiş veri istenirse D1'den dışa aktarılıp SQLite'a yüklenir.

## Günlük işletim

- Durum: `Get-ScheduledTask 'KPSS Analiz Toplayici'`; günlük yok, hata konsola yazılır (gerekirse görevi elle `node --env-file=.env sunucu.js` ile çalıştır).
- Acil durdurma: `.env` içine `TOPLAMA_KAPALI=1` yazıp görevi yeniden başlat.
- Yedek: `veri/analiz.sqlite` dosyasını (WAL kapalıyken ya da `sqlite3 .backup` ile) kopyala.
- Test: `npm test` (analiz-yerel içinde).
