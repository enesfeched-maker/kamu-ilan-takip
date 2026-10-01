-- Kişisel bildirim botu (Cloudflare D1). Kişisel veri yalnız burada tutulur; repoya yazılmaz.
-- Ücretsiz plan: çağrı başına 50 sorgu (batch içindeki her ifade sayılır), ifade başına 100 bağlı parametre.

CREATE TABLE IF NOT EXISTS kullanicilar (
  chat_id      INTEGER PRIMARY KEY,
  onay         INTEGER NOT NULL DEFAULT 0,          -- /start'taki bildirim + sponsorlu içerik onayı
  duzeyler     TEXT    NOT NULL DEFAULT '[]',       -- JSON: ["lisans","onlisans","ortaogretim"]; [] = hepsi
  iller        TEXT    NOT NULL DEFAULT '[]',       -- JSON: ["Ankara","İzmir"]; [] = tüm Türkiye
  kategoriler  TEXT    NOT NULL DEFAULT '[]',       -- JSON: ["belediye","saglik","bilisim","isci"]; [] = hepsi
  akademik     INTEGER NOT NULL DEFAULT 0,          -- 1 = akademik kadro ilanları da gelsin
  kelimeler    TEXT    NOT NULL DEFAULT '[]',       -- JSON: ["hukuk","bilgisayar"]; [] = filtre yok
  aktif        INTEGER NOT NULL DEFAULT 1,          -- /durdur = 0, botu engelleyen = 0
  hatirlatma   INTEGER NOT NULL DEFAULT 1,          -- son günden önce hatırlatma
  durum        TEXT,                                -- sohbet durumu, ör. 'kelime_bekleniyor'
  vip_bitis    TEXT,                                -- ISO tarih; şimdilik kullanılmıyor (VIP_ACIK bayrağı)
  olusturma    TEXT    NOT NULL,
  guncelleme   TEXT    NOT NULL
);

-- Kullanıcıya fiilen gönderilmiş ilanlar (gönderim başarılı olunca yazılır).
CREATE TABLE IF NOT EXISTS gonderilen (
  chat_id      INTEGER NOT NULL,
  ilan_id      TEXT    NOT NULL,
  zaman        TEXT    NOT NULL,
  hatirlatildi INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (chat_id, ilan_id)
);

-- Bot'un gördüğü ilanlar. 'veri' = ileti üretmek için gereken alanlar (JSON), böylece kuyruk boşaltılırken
-- ilan dosyası yeniden çekilmez. Aynı ilanın eski/yeni kimlikleri ayrı satır olarak tutulur (kimlik birleşmesi).
CREATE TABLE IF NOT EXISTS bilinen_ilanlar (
  ilan_id      TEXT PRIMARY KEY,
  ana_id       TEXT NOT NULL,                       -- ilanın güncel kimliği
  son_tarih    TEXT,
  veri         TEXT,                                -- yalnız ana_id satırında dolu
  ilk_gorulme  TEXT NOT NULL
);

-- Gönderilecek iletiler. tur: 'ilan' | 'hatirlatma' | 'fazla' (ilan_id = '+N' sayısı).
CREATE TABLE IF NOT EXISTS kuyruk (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id      INTEGER NOT NULL,
  ilan_id      TEXT    NOT NULL,
  tur          TEXT    NOT NULL,
  UNIQUE (chat_id, ilan_id, tur)
);

-- Tek satırlık anahtar/değer: son_tarama (ISO), tarama_imleci (chat_id), tarama_ilanlari (JSON kimlik listesi),
-- son_hatirlatma_gunu (YYYY-MM-DD).
CREATE TABLE IF NOT EXISTS meta (
  anahtar      TEXT PRIMARY KEY,
  deger        TEXT
);

-- Sponsor satırı: boşsa hiçbir iletide reklam görünmez. NULL alan = o boyutta hedefleme yok. link yalnız https.
CREATE TABLE IF NOT EXISTS sponsorlar (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  metin        TEXT    NOT NULL,
  link         TEXT,
  duzey        TEXT,
  il           TEXT,
  kategori     TEXT,
  baslangic    TEXT    NOT NULL,
  bitis        TEXT    NOT NULL,
  aktif        INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS gonderilen_ilan ON gonderilen (ilan_id, hatirlatildi);
CREATE INDEX IF NOT EXISTS bilinen_son_tarih ON bilinen_ilanlar (son_tarih);
