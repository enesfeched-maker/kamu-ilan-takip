-- KPSS Tercihi site analizi. Uygulama: wrangler d1 execute kpss-analiz --remote --file=schema.sql --config wrangler.toml
-- IP adresi ve tam User-Agent HICBIR yerde saklanmaz. Ziyaretci kimligi (zv) gunluk rastgele tuzle uretilen
-- kisa bir ozettir; tuz gece degisir ve eskisi silinir, bu yuzden gunler arasi izleme yapilamaz.

-- Ham olaylar (90 gun sonra silinir). Oturum ozellikleri (ulke, cihaz, kaynak...) yalniz oturumun ilk sayfa olayinda (ilk = 1) bulunur.
CREATE TABLE IF NOT EXISTS olaylar (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  ts       INTEGER NOT NULL,           -- unix saniye (UTC)
  gun      TEXT    NOT NULL,           -- YYYY-MM-DD (Turkiye saati)
  saat     INTEGER NOT NULL,           -- 0-23 (Turkiye saati)
  hg       INTEGER NOT NULL,           -- hafta gunu, 0 = Pazartesi
  zv       TEXT    NOT NULL,           -- gunluk anonim ziyaretci ozeti
  os       TEXT    NOT NULL,           -- sekme oturum kodu (rastgele)
  t        TEXT    NOT NULL,           -- sayfa | aktif | tikla | kaydirma | hata | hiz | 404
  p        TEXT,                       -- yol (sorgu ve # yok)
  sy       TEXT,                       -- sayfa turu: ana | ilan | kurum | taban | robot | diger | 404
  v        TEXT,                       -- ana sayfa gorunumu / pencere (bugun, ilanlar, takvim, ilan, makale ...)
  k        TEXT,                       -- ekranin anahtari (ilan anahtari, kurum adresi, makale)
  a        TEXT,                       -- tikla: eylem adi
  h        TEXT,                       -- tikla: hedef (ilan anahtari, filtre adi ...)
  x        TEXT,                       -- metin/deger (arama sorgusu, filtre degeri, hata iletisi)
  n        INTEGER,                    -- sayi (sonuc adedi, saniye, kaydirma yuzdesi, LCP ms)
  n2       INTEGER,                    -- ikinci sayi (TTFB ms)
  ilk      INTEGER NOT NULL DEFAULT 0, -- 1 = oturumun ilk sayfa goruntulemesi
  yeni     INTEGER,                    -- 1 yeni, 0 geri donen (yalniz ilk = 1)
  ulke     TEXT, bolge TEXT, sehir TEXT,
  cihaz    TEXT, tarayici TEXT, isletim TEXT, gen TEXT, dil TEXT,
  kaynak   TEXT, rhost TEXT, us TEXT, um TEXT, uc TEXT
);
-- TEK indeks: her olay 2 satir yazar (tablo + indeks). Tum sicak sorgular (canli, populer, gun/aralik raporu, bakim, temizlik) ts araligi kullanir.
CREATE INDEX IF NOT EXISTS idx_olaylar_ts ON olaylar (ts);

-- Gunluk tuz: gun basina bir satir, gece yarisindan sonra bakim isi eskileri siler.
CREATE TABLE IF NOT EXISTS tuz (
  gun TEXT PRIMARY KEY,
  tuz TEXT NOT NULL
);

-- Panel giris denemeleri (kilitleme). Anahtar tuzlu ozettir, IP degildir.
CREATE TABLE IF NOT EXISTS giris_deneme (
  anahtar TEXT PRIMARY KEY,
  say     INTEGER NOT NULL,
  ilk     INTEGER NOT NULL,
  kilit   INTEGER NOT NULL DEFAULT 0
);

-- Gunluk ozetler (ham olaylar silindikten sonra da kalir). Tamamlanan her gun icin bakim isi doldurur.
CREATE TABLE IF NOT EXISTS ozet (
  gun    TEXT    NOT NULL,
  boyut  TEXT    NOT NULL,
  k1     TEXT    NOT NULL DEFAULT '',
  k2     TEXT    NOT NULL DEFAULT '',
  say    INTEGER NOT NULL DEFAULT 0,
  tekil  INTEGER NOT NULL DEFAULT 0,
  oturum INTEGER NOT NULL DEFAULT 0,
  toplam INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (gun, boyut, k1, k2)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS ozet_gun (
  gun TEXT PRIMARY KEY,
  ts  INTEGER NOT NULL
);
