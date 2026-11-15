-- 0005: rumuz + sifre uyeligi, kurtarma kodu, Google ile giris, uyeye bagli profil, giris deneme sayaci.
-- Mevcut veritabanina bir kez uygulanir: wrangler d1 execute <ad> --local|--remote --file migrations/0005_kayit.sql
ALTER TABLE uyeler ADD COLUMN sifre_ozet TEXT;      -- pbkdf2$<tekrar>$<tuz>$<ozet> - Telegram/Google uyelerinde bos olabilir
ALTER TABLE uyeler ADD COLUMN kurtarma_ozet TEXT;   -- kurtarma kodunun HMAC ozeti (kodun kendisi saklanmaz)
ALTER TABLE uyeler ADD COLUMN google_sub TEXT;      -- Google hesap kimligi; e-posta ve ad saklanmaz
ALTER TABLE uyeler ADD COLUMN profil TEXT;          -- sitedeki kit-profil (JSON, beyaz listeli, <= 2 KB)
CREATE UNIQUE INDEX IF NOT EXISTS uyeler_google_sub ON uyeler(google_sub);
CREATE TABLE IF NOT EXISTS giris_denemeleri (
  tur TEXT,                -- kayit | giris_ip | giris_rumuz
  anahtar TEXT,            -- IP ozeti ya da kucuk harfli rumuz
  olusma INTEGER
);
CREATE INDEX IF NOT EXISTS giris_denemeleri_anahtar ON giris_denemeleri(tur, anahtar, olusma);