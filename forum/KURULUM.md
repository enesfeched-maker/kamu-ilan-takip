# Forum API kurulumu

1. D1 olustur: `npx wrangler d1 create kpss-forum` ; cikan `database_id` degerini `wrangler.toml` icindeki BURAYA-ID yerine yaz.
2. Tablolari kur: `npx wrangler d1 execute kpss-forum --remote --file=schema.sql --config wrangler.toml`
3. Sirlari ekle (her biri icin degeri sorar):
   - `npx wrangler secret put TELEGRAM_BOT_TOKEN --config wrangler.toml` (@kamuilanibot belirteci)
   - `npx wrangler secret put OTURUM_SIRRI --config wrangler.toml` (uzun rastgele metin)
   - `npx wrangler secret put YONETICI_ANAHTARI --config wrangler.toml`
4. Dagit: `npx wrangler deploy --config wrangler.toml` (forum-api.kpsstercihi.com alan adini kendisi olusturur).
5. Telegram giris araci icin BotFather'da: `/setdomain` -> @kamuilanibot -> `kpsstercihi.com`.
6. Yerel deneme: `npx wrangler dev --local --var ORTAM:yerel --var OTURUM_SIRRI:deneme --var YONETICI_ANAHTARI:deneme`
7. Acil durdurma: `YAZMA_KAPALI = "1"` yapip yeniden dagit (yonetim uclari calismaya devam eder).

Testler: `cd forum; node --test "test/*.test.js"` (bagimlilik yok, Node 22+).
