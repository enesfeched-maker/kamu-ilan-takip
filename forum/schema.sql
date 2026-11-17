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
  dm_acik INTEGER DEFAULT 1,         -- 1: özel mesaj alır
  itibar INTEGER DEFAULT 0,          -- yazılarının aldığı "faydalı" oyu sayısı
  sifre_ozet TEXT,                   -- pbkdf2$<tekrar>$<tuz>$<ozet>; yalnız şifreli üyelerde
  kurtarma_ozet TEXT,                -- kurtarma kodunun HMAC özeti
  google_sub TEXT,                   -- Google hesap kimliği
  eposta TEXT,                       -- yalnız DOĞRULANMIŞ adres (küçük harf, NFC): giriş kodu ve şifre sıfırlama için; Google ile girilince Google'ın doğrulanmış adresi de buraya yazılır
  eposta_dogrulandi INTEGER,         -- doğrulama zamanı (unix sn)
  silindi INTEGER,                   -- hesap silme zamanı; kimlik bilgileri temizlenir, yazılar "Silinmiş üye" adıyla kalır
  profil TEXT,                       -- sitedeki kit-profil (JSON, beyaz listeli)
  kayitli TEXT,                      -- sitedeki kit-saved: kayıtlı ilan kimlikleri (JSON dizi, en çok 300, en çok 8 KB)
  rumuz_kat TEXT,                    -- küçük harf, Türkçe harfler ASCII, "." ve "_" atılmış rumuz (benzersiz)
  oturum_surum INTEGER DEFAULT 0,    -- şifre/kurtarma kodu değişince artar, eski oturumlar kapanır
  avatar TEXT,                       -- piksel karakter "px.<ad>:pixel.<ton>" (üyelikte rastgele atanır) ya da 'foto'
  foto_surum INTEGER,                -- yüklenen fotoğrafın sürümü (unix sn); boş = fotoğraf yok
  foto_gun INTEGER,                  -- fotoğraf yükleme sayacı: UTC gün numarası
  foto_sayi INTEGER,                 -- o gün yapılan yükleme (günde en çok 3)
  foto_yasak INTEGER,                -- yönetici fotoğrafı kaldırınca 1: yeni fotoğraf yüklenemez
  kart TEXT,                         -- profil kartı JSON: hakkimda, hedef, durum, kart_rengi, gizlilik (varsayılanlar yazılmaz)
  basvurular TEXT                    -- sitedeki fr-basvuru: başvurdum dediği ilan kimlikleri (JSON dizi, en çok 300)
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
CREATE UNIQUE INDEX IF NOT EXISTS uyeler_google_sub ON uyeler(google_sub);
CREATE UNIQUE INDEX IF NOT EXISTS uyeler_rumuz_kat ON uyeler(rumuz_kat);
CREATE UNIQUE INDEX IF NOT EXISTS uyeler_eposta ON uyeler(eposta);
CREATE TABLE IF NOT EXISTS eposta_kodlari (
  anahtar TEXT PRIMARY KEY,         -- HMAC(biber, amaç + adres/üye): adresin kendisi saklanmaz
  kod_ozet TEXT,                    -- HMAC(biber, anahtar + kod): kodun kendisi saklanmaz
  bitis INTEGER,                    -- geçerlilik sonu (unix sn, 10 dk)
  deneme INTEGER DEFAULT 0,         -- yanlış doğrulama sayısı (en çok 5)
  son_gonderim INTEGER              -- en erken 60 sn sonra yeniden gönderilir
);
CREATE INDEX IF NOT EXISTS eposta_kodlari_bitis ON eposta_kodlari(bitis);
CREATE TABLE IF NOT EXISTS eposta_gunluk (
  gun TEXT PRIMARY KEY,             -- UTC gün (YYYY-AA-GG); Brevo ücretsiz plan günde 300, biz 280'de durdururuz
  n INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS eposta_sayac (
  tur TEXT,                         -- gonder_ip (IP /24 günlük gönderim) | eposta_adres (adres saatlik gönderim) | dogrula_ip (IP 15 dk deneme) | hata_hedef (hedef başına günlük deneme)
  anahtar TEXT,                     -- biberli özet ya da IP özeti
  dilim INTEGER,                    -- zaman dilimi numarası (gün / saat / 15 dk)
  n INTEGER DEFAULT 0,
  olusma INTEGER,                   -- son yazma (fırsat temizliği)
  PRIMARY KEY (tur, anahtar, dilim)
);
CREATE INDEX IF NOT EXISTS eposta_sayac_olusma ON eposta_sayac(olusma);
CREATE TABLE IF NOT EXISTS ayrilmis_rumuzlar (
  kat TEXT PRIMARY KEY,             -- silinen hesabın rumuz_kat değeri; 180 gün başkası alamaz
  bitis INTEGER
);
CREATE TABLE IF NOT EXISTS giris_denemeleri (
  tur TEXT,                          -- kayit | giris_ip | giris_rumuz_ip | giris_rumuz
  anahtar TEXT,                     -- IP özeti ya da küçük harfli rumuz
  olusma INTEGER
);
CREATE INDEX IF NOT EXISTS giris_denemeleri_anahtar ON giris_denemeleri(tur, anahtar, olusma);
CREATE INDEX IF NOT EXISTS giris_denemeleri_olusma ON giris_denemeleri(olusma);
INSERT OR IGNORE INTO uyeler (id, tg_id, rumuz, rumuz_kat, kayit, kurucu, rol, bildirim) VALUES (1, NULL, 'KPSS Tercihi', 'kpss tercihi', 0, 0, 'sistem', 0);
INSERT OR IGNORE INTO uyeler (id, tg_id, rumuz, rumuz_kat, kayit, kurucu, rol, bildirim) VALUES (2, NULL, 'Asistan', 'asistan', 0, 0, 'asistan', 0);
CREATE TABLE IF NOT EXISTS fotolar (
  uye_id INTEGER PRIMARY KEY,
  veri BLOB,                         -- 160x160 WebP/JPEG/PNG, en çok 24 KB
  tur TEXT,                          -- image/webp | image/jpeg | image/png
  surum INTEGER,
  guncelleme INTEGER
);
CREATE TABLE IF NOT EXISTS foto_bildirimleri (
  uye_id INTEGER,                    -- fotoğrafı bildirilen üye
  bildiren INTEGER,
  surum INTEGER,                     -- bildirilen fotoğrafın sürümü
  olusma INTEGER,
  PRIMARY KEY (uye_id, bildiren)
);
CREATE TABLE IF NOT EXISTS uye_katip (
  uye_id INTEGER PRIMARY KEY,
  veri TEXT,                         -- kit-katip + ders/oyun/antrenman ilerlemesi (JSON, en çok 32 KB)
  ozet TEXT,                         -- karta konan özet (JSON)
  guncelleme INTEGER
);
-- Gizli yöneticiler (0006): uyeler.rol'den ayrı; hiçbir herkese açık çıktıda görünmez. Yalnız SQL ile elle eklenir:
--   INSERT OR IGNORE INTO gizli_yoneticiler (uye_id) SELECT id FROM uyeler WHERE rumuz = '<rumuz>';
CREATE TABLE IF NOT EXISTS gizli_yoneticiler (
  uye_id INTEGER PRIMARY KEY
);
-- Yönetici "Hesabı kapat" dediği hesapların kimlik özetleri (0006): HMAC(biber, 'kapali:google:<sub>' | 'kapali:tg:<id>' | 'kapali:eposta:<adres>').
-- Kimliğin kendisi saklanmaz; aynı Google / Telegram / e-posta ile yeniden üyelik açılmaz.
CREATE TABLE IF NOT EXISTS kapali_kimlikler (
  ozet TEXT PRIMARY KEY,
  olusma INTEGER
);