# Forum API kurulumu

**Hazir betik:** `powershell -ExecutionPolicy Bypass -File .\yayinla.ps1 -Kuru` (once ne yapacagini gosterir), sonra `-Kuru` olmadan. Asagidaki adimlari idempotent sekilde uygular (D1, gocler, sirlar, dagitim, duman testi); sirlari `%USERPROFILE%\.kpss-forum-sirlari.txt` dosyasina yedekler.

1. D1 olustur: `npx wrangler d1 create kpss-forum` ; cikan `database_id` degerini `wrangler.toml` icindeki BURAYA-ID yerine yaz.
2. Tablolari kur: `npx wrangler d1 execute kpss-forum --remote --file=schema.sql --config wrangler.toml`
3. Sirlari ekle (her biri icin degeri sorar):
   - `npx wrangler secret put TELEGRAM_BOT_TOKEN --config wrangler.toml` (@kamuilanibot belirteci)
   - `npx wrangler secret put OTURUM_SIRRI --config wrangler.toml` (uzun rastgele metin)
   - `npx wrangler secret put YONETICI_ANAHTARI --config wrangler.toml`
     Ayni deger analiz Worker'inda `FORUM_YONETICI_ANAHTARI` olarak da tanimlanir (panel "Forum" bolumu `GET /yonetim/ozet` ile okur; salt okunur, onbellek yok).
4. Dagit: `npx wrangler deploy --config wrangler.toml` (forum-api.kpsstercihi.com alan adini kendisi olusturur).
5. Telegram giris araci icin BotFather'da: `/setdomain` -> @kamuilanibot -> `kpsstercihi.com`.
6. Yerel deneme: `npx wrangler dev --local --var ORTAM:yerel --var OTURUM_SIRRI:deneme --var YONETICI_ANAHTARI:deneme`
7. Acil durdurma: `YAZMA_KAPALI = "1"` yapip yeniden dagit (yonetim uclari calismaya devam eder).

Testler: `cd forum; node --test "test/*.test.js"` (bagimlilik yok, Node 22+).

## Üyelik yöntemleri (rumuz + sifre, Google)
- Once D1'e gocu uygula (kod yeni sutunlari okur): `wrangler d1 execute kpss-forum --remote --file=migrations/0005_kayit.sql --config wrangler.toml`
  Oncesinde migration dosyasinin basindaki kontrol sorgusunu calistir: Turkce harf/buyuk-kucuk harf/"."/"_" farkiyla ayni olan rumuz varsa (`rumuz_kat` cakismasi) benzersiz indeks kurulamaz; cakisan hesaplardan birinin rumuzunu elle degistir.
- **ZORUNLU sir (sifre ozelligi icin):** `npx wrangler secret put SIFRE_BIBERI --config wrangler.toml` (uzun rastgele metin, OTURUM_SIRRI'ndan FARKLI). Tanimli degilse rumuz+sifre uyeligi, sifre girisi ve kurtarma kodu kapali kalir
  (`/giris/ayar` `sifre:false`, ilgili uclar 503; Telegram/Google girisi etkilenmez). Sonradan degisirse tum sifre ve kurtarma kodu ozetleri gecersiz olur. Ozetin icindeki surum (`v1`) ileride `SIFRE_BIBERI_2` ile donusturmeye izin verir.
- Istege bagli sir: `TURNSTILE_GIZLI` (Cloudflare Turnstile gizli anahtari; /kayit robot kontrolu ister, yanit hostname'i kpsstercihi.com olmali).
- Yerel deneme: wrangler dev komutuna `--var SIFRE_BIBERI:deneme` ekle (yoksa sifre ozellikleri kapali gorunur).
- **E-posta ile giris (istege bagli, `BREVO_ANAHTARI`):** 6 haneli kod e-postayla gonderilir (Brevo islemsel API, ucretsiz plan gunde 300 e-posta; kod gonderimi 280'de durur, sayac `eposta_gunluk` tablosunda UTC gunune gore). Anahtari **sahibi kendisi** ekler:
  `npx wrangler secret put BREVO_ANAHTARI --config wrangler.toml`. `yayinla.ps1` bu sirri uretmez, sormaz; yalnizca tanimli mi diye raporlar. Tanimli degilse e-posta ile giris gizlenir (`/giris/ayar` `eposta:false`, ilgili uclar 503); Google ve rumuz+sifre etkilenmez.
  **Uretimde Turnstile ZORUNLUDUR:** e-posta girisi yalnizca `BREVO_ANAHTARI` + `TURNSTILE_GIZLI` (secret) + `TURNSTILE_SITE` ([vars]) hepsi tanimliyken acilir (kota tuketme ve e-posta bombalama saldirisina karsi). Kod isteyen uclar (`/giris/eposta/kod`, `/sifre-sifirla/eposta`, `/ben/eposta`) gecerli bir Turnstile jetonu ister; Cloudflare panelinde Turnstile widget'i olustur (alan adi kpsstercihi.com), site anahtarini `wrangler.toml` [vars] icine `TURNSTILE_SITE`, gizli anahtari `npx wrangler secret put TURNSTILE_GIZLI --config wrangler.toml` ile ekle (`ORTAM=yerel` gelistirmede sart degildir).
  Ek korumalar: IP kovasi (IPv4 /24, IPv6 /64) basina gunde 5 kod, adres basina (gmail noktalari/+ekleri ve googlemail tek sayilir; diger alanlarda +ek atilir) saatte 5 kod, hedef basina gunde 20 yanlis deneme; gunluk kota 220'yi gecince hesabi olmayan adreslere giris kodu gonderilmez (yalniz mevcut uyelere ayrilir). Google bagi yalniz @gmail.com/@googlemail.com ya da jetonun `hd` degeri adresin alan adina esitse kurulur.
  Brevo'da once gonderen adresi (varsayilan `bildirim@kpsstercihi.com`) ve alan adi dogrulanmalidir (SPF/DKIM). Baska adres icin `wrangler.toml` [vars] icine `EPOSTA_GONDEREN = "..."`. E-posta ozellikleri `SIFRE_BIBERI` da ister (adres ve kod yalniz biberli ozet olarak tutulur).
  Adres uye satirina yalniz dogrulaninca yazilir (`uyeler.eposta`, kucuk harf); Google ile girerken Google'in dogrulanmis adresi de yazilir ve ayni adresli e-posta hesabina Google kimligi baglanir. Hesap silinince adres, sifre, Google/Telegram kimligi, profil ve kayitli ilanlar silinir; yazilar "Silinmis uye #id" adiyla kalir.
  Yerel deneme: `--var ORTAM:yerel` ve `BREVO_ANAHTARI` yokken kod gonderilmez, wrangler konsoluna `[eposta-gelistirme] giris kodu (adres): 123456` yazilir.
  Veritabani: mevcut veritabaninda 0005 daha once e-postasiz uygulandiysa `yayinla.ps1` eksik sutunlari (`eposta`, `eposta_dogrulandi`, `silindi`) ve yeni tablolari (`eposta_kodlari`, `eposta_gunluk`) kendisi ekler.
- Istege bagli degiskenler ([vars]): `TURNSTILE_SITE` (Turnstile site anahtari), `GOOGLE_ISTEMCI_KIMLIGI` (Google OAuth web istemci kimligi; bos ise Google dugmesi gorunmez).
