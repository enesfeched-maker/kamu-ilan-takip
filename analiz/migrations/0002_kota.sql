-- D1 yazma kotasi: olay basina 3 yerine 2 satir yazilir (tablo + idx_olaylar_ts).
-- Uygulama: wrangler d1 execute kpss-analiz --remote --file=migrations/0002_kota.sql --config wrangler.toml
-- idx_olaylar_ts KALIR (canli, populer, aralik raporu ve temizlik ts araligi ile calisir).
DROP INDEX IF EXISTS idx_olaylar_gun_t;
CREATE INDEX IF NOT EXISTS idx_olaylar_ts ON olaylar (ts);
