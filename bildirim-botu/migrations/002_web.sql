-- Web Push (tarayıcı bildirimi) tabloları. Tekrar çalıştırılabilir (idempotent).
CREATE TABLE IF NOT EXISTS web_aboneler (
  endpoint     TEXT PRIMARY KEY,
  p256dh       TEXT,
  auth         TEXT,
  duzey        TEXT,
  bolum        TEXT,
  puan         REAL,
  olusturma    TEXT,
  aktif        INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS web_bekleyen (
  endpoint     TEXT,
  ilan_id      TEXT,
  baslik       TEXT,
  kurum        TEXT,
  url          TEXT,
  zaman        TEXT,
  PRIMARY KEY (endpoint, ilan_id)
);
