-- KPSS Tercihi forum sema (D1/SQLite). Zamanlar unix saniyesi.
CREATE TABLE IF NOT EXISTS uyeler (
  id INTEGER PRIMARY KEY,
  tg_id INTEGER UNIQUE,
  rumuz TEXT UNIQUE COLLATE NOCASE,
  kayit INTEGER,
  kurucu INTEGER DEFAULT 0,
  rol TEXT DEFAULT 'uye',            -- uye | yonetici | asistan | sistem
  bildirim INTEGER DEFAULT 1,
  engelli INTEGER DEFAULT 0,
  itibar INTEGER DEFAULT 0           -- yazılarının aldığı "faydalı" oyu sayısı
);
CREATE TABLE IF NOT EXISTS basliklar (
  id INTEGER PRIMARY KEY,
  kategori TEXT,
  baslik TEXT,
  govde TEXT,
  uye_id INTEGER,
  ilan_id TEXT UNIQUE,
  kaynak TEXT DEFAULT 'uye',         -- uye | telegram | sistem
  sabit INTEGER DEFAULT 0,
  olusma INTEGER,
  son_hareket INTEGER,
  yanit_sayisi INTEGER DEFAULT 0,
  gizli INTEGER DEFAULT 0,
  duzey TEXT,                        -- lisans | onlisans | ortaogretim | ekpss | agrubu | NULL
  puan_turu TEXT,
  puan REAL,
  faydali INTEGER DEFAULT 0,
  anket INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS basliklar_duzey ON basliklar(duzey, son_hareket);
CREATE INDEX IF NOT EXISTS basliklar_kategori ON basliklar(kategori, son_hareket);
CREATE INDEX IF NOT EXISTS basliklar_hareket ON basliklar(son_hareket);
CREATE INDEX IF NOT EXISTS basliklar_uye ON basliklar(uye_id, olusma);
CREATE TABLE IF NOT EXISTS yanitlar (
  id INTEGER PRIMARY KEY,
  baslik_id INTEGER,
  uye_id INTEGER,
  govde TEXT,
  olusma INTEGER,
  gizli INTEGER DEFAULT 0,
  sikayet INTEGER DEFAULT 0,
  faydali INTEGER DEFAULT 0,
  ust_id INTEGER
);
CREATE INDEX IF NOT EXISTS yanitlar_baslik ON yanitlar(baslik_id, id);
CREATE INDEX IF NOT EXISTS yanitlar_uye ON yanitlar(uye_id, olusma);
CREATE INDEX IF NOT EXISTS yanitlar_ust ON yanitlar(ust_id);
CREATE INDEX IF NOT EXISTS yanitlar_olusma ON yanitlar(olusma);
CREATE TABLE IF NOT EXISTS oylar (
  yanit_id INTEGER,
  uye_id INTEGER,
  PRIMARY KEY (yanit_id, uye_id)
);
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
CREATE TABLE IF NOT EXISTS sikayetler (
  yanit_id INTEGER,
  uye_id INTEGER,
  PRIMARY KEY (yanit_id, uye_id)
);
CREATE TABLE IF NOT EXISTS basvurular (
  ilan_id TEXT,
  kimlik TEXT,
  puan_turu TEXT,
  puan REAL,
  olusma INTEGER,
  PRIMARY KEY (ilan_id, kimlik)
);
INSERT OR IGNORE INTO uyeler (id, tg_id, rumuz, kayit, kurucu, rol, bildirim) VALUES (1, NULL, 'KPSS Tercihi', 0, 0, 'sistem', 0);
INSERT OR IGNORE INTO uyeler (id, tg_id, rumuz, kayit, kurucu, rol, bildirim) VALUES (2, NULL, 'Asistan', 0, 0, 'asistan', 0);
