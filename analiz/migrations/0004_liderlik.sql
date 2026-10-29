-- Katiplik liderlik tablosu: takma ad + sunucuda yeniden puanlanan en iyi net (hafta basina kisi basina tek satir).
-- Uygulama: wrangler d1 execute kpss-analiz --remote --file=migrations/0004_liderlik.sql --config wrangler.toml
-- Tekrar calistirmak zararsizdir (IF NOT EXISTS). Kisisel veri yok: kimlik, tarayicinin rastgele anahtarinin ozetidir.
CREATE TABLE IF NOT EXISTS liderlik (
  hafta  TEXT    NOT NULL,            -- haftanin pazartesisi (Turkiye saati), ör. 2026-10-26
  kimlik TEXT    NOT NULL,            -- SHA-256(tarayici anahtari) ilk 16 hane
  ad     TEXT    NOT NULL,
  net    INTEGER NOT NULL,
  dogru  INTEGER NOT NULL,
  hatali INTEGER NOT NULL,
  dk     INTEGER NOT NULL,            -- dakikadaki vurus
  ts     INTEGER NOT NULL,
  PRIMARY KEY (hafta, kimlik)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS liderlik_net ON liderlik (hafta, net DESC);
