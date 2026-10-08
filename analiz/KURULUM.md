# Site analizi kurulumu (kpss-analiz)

Çerezsiz, anonim ziyaret istatistiği: site `docs/a.js` ile olayları `https://api.kpsstercihi.com/o` adresine
gönderir; Cloudflare Worker (`kpss-analiz`) D1 veritabanına yazar; sahibi `https://api.kpsstercihi.com/panel`
adresinden anahtarla görür. Bu klasördeki hiçbir şey kendiliğinden dağıtılmaz.

## Tek komutla

```powershell
cd C:\Users\Feched\Desktop\codex-ws\kit-analiz\analiz
powershell -ExecutionPolicy Bypass -File .\kurulum.ps1
```

Betik sırayla şunları yapar (her adım yeniden çalıştırılabilir):

1. `wrangler d1 create kpss-analiz` ve çıkan kimliği `wrangler.toml` içindeki `database_id` alanına yazar.
2. `wrangler d1 execute kpss-analiz --remote --file=schema.sql` ile tabloları kurar.
3. `wrangler secret put PANEL_ANAHTARI`: anahtarı gizli girişle sorar (ekrana/diske yazılmaz).
4. `wrangler deploy`: Worker'ı yayınlar. `api.kpsstercihi.com` özel alan adı ve DNS kaydı dağıtım sırasında
   otomatik oluşturulur (`kpsstercihi.com` Cloudflare hesabında olmalı). Günlük bakım cron'u da bu adımda kurulur.

## Elle (aynı işler)

```powershell
$w = 'C:\Users\Feched\Desktop\codex-ws\node_modules\.bin\wrangler.cmd'
& $w d1 create kpss-analiz --config wrangler.toml          # çıkan database_id'yi wrangler.toml'a yaz
& $w d1 execute kpss-analiz --remote --file=schema.sql --config wrangler.toml
& $w secret put PANEL_ANAHTARI --config wrangler.toml
& $w deploy --config wrangler.toml
```

## Siteyi yayınlamak

`docs/a.js` ve sayfalardaki `data-a` işaretleri `site-analizi` dalı birleştirilip siteyle birlikte yayınlanır.
Worker dağıtılmadan yayınlanırsa tarayıcı istekleri sessizce başarısız olur; sayfa etkilenmez. Önce Worker'ı kur,
sonra siteyi yayınla; ilk ziyaretler panelde birkaç saniye içinde görünür.

## Doğrulama

- `https://api.kpsstercihi.com/` -> `kpss-analiz` yazar.
- Siteyi aç, 10 saniye sonra `https://api.kpsstercihi.com/panel` içinde "Şu an aktif" 1 olur
  (tarayıcında Do Not Track / GPC kapalı ve reklam engelleyici sitedeki `api.` isteğini engellemiyor olmalı).

## Panel ve güvenlik

- Giriş: anahtar -> `HttpOnly; Secure; SameSite=Strict` çerez (30 gün, yalnızca `api.kpsstercihi.com/panel`).
  5 yanlış denemede 15 dakika kilit. Anahtarı değiştirmek için `wrangler secret put PANEL_ANAHTARI` çalıştırıp yeniden dağıt;
  eski çerezler geçersiz olur.
- Acil durdurma: `wrangler.toml` içinde `TOPLAMA_KAPALI = "1"` yapıp `wrangler deploy`.

## Veri

- Saklanan: zaman, sayfa yolu, görünüm, olay türü/adı, kaba cihaz/tarayıcı/işletim sistemi ailesi, ülke/bölge/şehir
  (Cloudflare'ın IP'den türettiği; IP kendisi değil), kaynak sınıfı ve yönlendiren alan adı, utm_*, ekran genişliği kovası,
  arama sözcüğü ve sonuç adedi, rastgele sekme oturum kodu, **günlük tuzlu ziyaretçi özeti**.
- Saklanmayan: IP adresi, tam User-Agent, çerez, kalıcı tarayıcı kimliği, serbest metin (arama hariç; e-posta ve uzun
  rakam dizileri içeren girdiler `[temizlendi]` olur).
- Ham olaylar 90 gün, günlük özetler 400 gün tutulur; tuzlar her gece silinir (gün atlamalı izleme mümkün değildir).

## Yerel deneme

```powershell
$w = 'C:\Users\Feched\Desktop\codex-ws\node_modules\.bin\wrangler.cmd'
& $w d1 execute kpss-analiz --local --file=schema.sql --config wrangler.toml
& $w dev --local --config wrangler.toml --var ORTAM:yerel --test-scheduled   # PANEL_ANAHTARI tanımlı değilken panel girişsiz açılır
# panel: http://127.0.0.1:8787/panel   bakım: http://127.0.0.1:8787/__scheduled
node --test "test/*.test.js"
```

`ORTAM` değişkeni üretimde **tanımlanmaz** (yalnızca `--var` ile, yerelde); üretimde ayrıca `PANEL_ANAHTARI` olduğu için girişsiz erişim zaten kapalıdır.

## Kota tahmini (Cloudflare ücretsiz plan)

Her olay 1 satır + 2 dizin = yaklaşık 3 "satır yazma". Bir oturum ortalama 8–15 olay (sayfa, 60 sn'de bir birleştirilmiş etkin süre,
tıklamalar). Günde 1.000 ziyaretçi ≈ 30–45 bin yazma (limit 100 bin/gün); 2.500+ ziyaretçi/gün civarında limit aşılır.
Panel okumaları özet tablolardan yapılır (bugün hariç); 5 milyon/gün okuma sınırının çok altındadır.