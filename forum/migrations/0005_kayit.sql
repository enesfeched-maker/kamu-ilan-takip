-- 0005: rumuz + sifre uyeligi, kurtarma kodu, Google ile giris, uyeye bagli profil, giris deneme sayaci,
-- Turkce harfe duyarsiz benzersiz rumuz (rumuz_kat) ve oturum surumu (sifre degisince eski oturumlar kapanir).
-- Mevcut veritabanina bir kez uygulanir: wrangler d1 execute <ad> --local|--remote --file migrations/0005_kayit.sql
-- ONCE KONTROL: SELECT COUNT(*) FROM (SELECT replace(replace(lower(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(rumuz,'Ç','c'),'ç','c'),'Ğ','g'),'ğ','g'),'İ','i'),'ı','i'),'Ö','o'),'ö','o'),'Ş','s'),'ş','s'),'Ü','u'),'ü','u')),'.',''),'_','') AS k FROM uyeler GROUP BY k HAVING COUNT(*) > 1);  -- 0 olmali, degilse rumuz_kat benzersiz indeksi kurulamaz
ALTER TABLE uyeler ADD COLUMN sifre_ozet TEXT;      -- pbkdf2$v1$<tekrar>$<tuz>$<ozet> - Telegram/Google uyelerinde bos olabilir
ALTER TABLE uyeler ADD COLUMN kurtarma_ozet TEXT;   -- kurtarma kodunun HMAC ozeti (kodun kendisi saklanmaz)
ALTER TABLE uyeler ADD COLUMN google_sub TEXT;      -- Google hesap kimligi, e-posta ve ad saklanmaz
ALTER TABLE uyeler ADD COLUMN profil TEXT;          -- sitedeki kit-profil (JSON, beyaz listeli)
ALTER TABLE uyeler ADD COLUMN kayitli TEXT;         -- sitedeki kit-saved: kayitli ilan kimlikleri (JSON dizi, en cok 300, en cok 8 KB)
ALTER TABLE uyeler ADD COLUMN rumuz_kat TEXT;       -- kucuk harf, Turkce harfler ASCII, "." ve "_" atilmis rumuz (src/oturum.js rumuzKat ile ayni)
ALTER TABLE uyeler ADD COLUMN oturum_surum INTEGER DEFAULT 0;
UPDATE uyeler SET rumuz_kat = replace(replace(lower(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(rumuz,'Ç','c'),'ç','c'),'Ğ','g'),'ğ','g'),'İ','i'),'ı','i'),'Ö','o'),'ö','o'),'Ş','s'),'ş','s'),'Ü','u'),'ü','u')),'.',''),'_','') WHERE rumuz_kat IS NULL AND rumuz IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uyeler_google_sub ON uyeler(google_sub);
CREATE UNIQUE INDEX IF NOT EXISTS uyeler_rumuz_kat ON uyeler(rumuz_kat);
CREATE TABLE IF NOT EXISTS giris_denemeleri (
  tur TEXT,                -- kayit | giris_ip | giris_rumuz_ip | giris_rumuz
  anahtar TEXT,            -- IP ozeti, rumuz ya da rumuz|IP ozeti
  olusma INTEGER
);
CREATE INDEX IF NOT EXISTS giris_denemeleri_anahtar ON giris_denemeleri(tur, anahtar, olusma);
CREATE INDEX IF NOT EXISTS giris_denemeleri_olusma ON giris_denemeleri(olusma);   -- firsat temizligi