-- 0004: özel mesajlar, engelleme, şikayet, başlık/oda takibi, üye ayarı (dm_acik).
-- Mevcut veritabanına bir kez uygulanır: wrangler d1 execute <ad> --local|--remote --file migrations/0004_ozel_takip.sql
ALTER TABLE uyeler ADD COLUMN dm_acik INTEGER DEFAULT 1;   -- 1: özel mesaj alır
CREATE TABLE IF NOT EXISTS ozel_mesajlar (
  id INTEGER PRIMARY KEY,
  gonderen INTEGER,
  alici INTEGER,
  govde TEXT,
  olusma INTEGER,
  okundu INTEGER DEFAULT 0,
  gizli INTEGER DEFAULT 0            -- gönderen kendi mesajını gizleyebilir
);
CREATE INDEX IF NOT EXISTS ozel_alici_okundu ON ozel_mesajlar(alici, okundu);
CREATE INDEX IF NOT EXISTS ozel_gonderen_alici ON ozel_mesajlar(gonderen, alici, id);
CREATE INDEX IF NOT EXISTS ozel_alici_gonderen ON ozel_mesajlar(alici, gonderen, id);
CREATE INDEX IF NOT EXISTS ozel_gonderen_olusma ON ozel_mesajlar(gonderen, olusma);   -- saatlik/günlük hız sınırı
CREATE TABLE IF NOT EXISTS engeller (
  uye_id INTEGER,
  engellenen INTEGER,
  olusma INTEGER,
  PRIMARY KEY (uye_id, engellenen)
);
CREATE TABLE IF NOT EXISTS ozel_sikayetler (
  id INTEGER PRIMARY KEY,
  sikayet_eden INTEGER,
  sikayet_edilen INTEGER,
  mesaj_id INTEGER,
  olusma INTEGER
);
CREATE INDEX IF NOT EXISTS ozel_sikayet_cift ON ozel_sikayetler(sikayet_eden, sikayet_edilen, olusma);
CREATE TABLE IF NOT EXISTS takipler (
  uye_id INTEGER,
  baslik_id INTEGER,
  olusma INTEGER,
  PRIMARY KEY (uye_id, baslik_id)
);
CREATE INDEX IF NOT EXISTS takipler_baslik ON takipler(baslik_id);
