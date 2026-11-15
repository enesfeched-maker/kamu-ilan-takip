-- 0002: başlık künyesi (düzey, puan), anket, başlık "faydalı" oyu, üye itibarı.
-- Mevcut veritabanına bir kez uygulanır: wrangler d1 execute <ad> --local|--remote --file migrations/0002_ozellikler.sql
ALTER TABLE basliklar ADD COLUMN duzey TEXT;
ALTER TABLE basliklar ADD COLUMN puan_turu TEXT;
ALTER TABLE basliklar ADD COLUMN puan REAL;
ALTER TABLE basliklar ADD COLUMN faydali INTEGER DEFAULT 0;
ALTER TABLE basliklar ADD COLUMN anket INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS basliklar_duzey ON basliklar(duzey, son_hareket);
ALTER TABLE uyeler ADD COLUMN itibar INTEGER DEFAULT 0;
CREATE TABLE IF NOT EXISTS baslik_oylar (
  baslik_id INTEGER,
  uye_id INTEGER,
  PRIMARY KEY (baslik_id, uye_id)
);
CREATE TABLE IF NOT EXISTS anket_secenekleri (
  baslik_id INTEGER,
  sira INTEGER,
  metin TEXT,
  oy INTEGER DEFAULT 0,
  PRIMARY KEY (baslik_id, sira)
);
CREATE TABLE IF NOT EXISTS anket_oylari (
  baslik_id INTEGER,
  uye_id INTEGER,
  sira INTEGER,
  PRIMARY KEY (baslik_id, uye_id)
);
