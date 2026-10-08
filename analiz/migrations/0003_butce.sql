-- Gunluk D1 kota bekcisi: izolatlarin yazma/okuma harcamasi UTC gunu basina tek satirda toplanir.
-- Uygulama: wrangler d1 execute kpss-analiz --remote --file=migrations/0003_butce.sql --config wrangler.toml
-- Tekrar calistirmak zararsizdir (IF NOT EXISTS). olaylar tablosuna dokunulmaz.
CREATE TABLE IF NOT EXISTS butce (
  gun_utc TEXT PRIMARY KEY,
  yazma   INTEGER NOT NULL DEFAULT 0,
  okuma   INTEGER NOT NULL DEFAULT 0
);
