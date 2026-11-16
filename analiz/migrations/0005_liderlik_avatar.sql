-- Liderlik tablosuna istege bagli avatar: forum uyesi giris yapmissa sitenin hazir avatari (anahtar:renk, orn. kedi:lila).
-- Uygulama (sira kritik degil: kod sutun yoksa avatarsiz calisir; yine de dagitimdan once uygulanmasi onerilir): wrangler d1 execute kpss-analiz --remote --file=migrations/0005_liderlik_avatar.sql --config wrangler.toml
-- ALTER TABLE ADD COLUMN tekrar calistirilirsa 'duplicate column' hatasi verir; bir kez uygulanir. Mevcut satirlarda avatar bos kalir (arayuz harf gosterir).
ALTER TABLE liderlik ADD COLUMN avatar TEXT;
