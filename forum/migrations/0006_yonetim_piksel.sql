-- 0006: gizli yoneticiler, kapatilan hesaplarin kimlik ozetleri ve yalniz piksel avatarlar.
-- Idempotent: tekrar calistirilabilir (IF NOT EXISTS, yalniz eksik/eski avatarlari gunceller).
-- Uygulama: wrangler d1 execute kpss-forum --remote --file migrations/0006_yonetim_piksel.sql --config wrangler.toml
CREATE TABLE IF NOT EXISTS gizli_yoneticiler (
  uye_id INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS kapali_kimlikler (
  ozet TEXT PRIMARY KEY,   -- HMAC(SIFRE_BIBERI, 'kapali:google:<sub>' | 'kapali:tg:<id>' | 'kapali:eposta:<adres>')
  olusma INTEGER
);
-- Gecici esleme tablolari (src/kart.js ESKI_SVG_PX / ESKI_RENK_TON ve docs/avatar-ortak.js ile ayni).
CREATE TABLE IF NOT EXISTS gecici_px (i INTEGER PRIMARY KEY, ad TEXT);
INSERT OR IGNORE INTO gecici_px (i, ad) VALUES (0,'loaf'),(1,'hops'),(2,'mumu'),(3,'fluff'),(4,'llama'),(5,'elephant'),(6,'whale'),(7,'dragon'),(8,'inky'),(9,'unicorn'),(10,'coffee'),(11,'keycap'),(12,'inbox'),(13,'floppy'),(14,'battery'),(15,'candle'),(16,'prompty'),(17,'heart'),(18,'cactus'),(19,'cloud'),(20,'star'),(21,'planet'),(22,'flick'),(23,'astronaut'),(24,'wizard'),(25,'robo'),(26,'ufo'),(27,'alien'),(28,'gloop'),(29,'bolt'),(30,'boba'),(31,'cookie'),(32,'mochi'),(33,'avocado'),(34,'donut'),(35,'sushi'),(36,'onigiri'),(37,'toast'),(38,'pudding'),(39,'cherries'),(40,'egg'),(41,'spud'),(42,'tofu'),(43,'gpu'),(44,'server'),(45,'modem'),(46,'token'),(47,'crt'),(48,'brain');
CREATE TABLE IF NOT EXISTS gecici_svg (k TEXT PRIMARY KEY, ad TEXT);
INSERT OR IGNORE INTO gecici_svg (k, ad) VALUES ('kedi','loaf'),('tavsan','hops'),('panda','mumu'),('tilki','loaf'),('baykus','star'),('ayicik','mumu'),('penguen','whale'),('koala','mumu'),('sincap','hops'),('kuzu','fluff'),('ordek','egg'),('hamster','mochi'),('kirpi','cactus'),('geyik','llama'),('kelebek','heart'),('astronot','astronaut'),('kaptan','wizard'),('kitapkurdu','brain'),('dagci','planet'),('bisikletci','bolt'),('asci','cookie'),('ressam','star'),('gitarist','flick'),('satranc','keycap'),('kahve','coffee'),('saksi','cactus'),('robot','robo'),('dinozor','dragon'),('ayikaptan','mumu'),('kurt','dragon'),('aslan','loaf'),('kartal','cloud'),('kalem','prompty'),('dosya','inbox'),('muhur','token'),('cay','boba'),('tus','keycap'),('kitap','floppy');
CREATE TABLE IF NOT EXISTS gecici_ton (r TEXT PRIMARY KEY, ton INTEGER);
INSERT OR IGNORE INTO gecici_ton (r, ton) VALUES ('lila',270),('pembe',315),('seftali',45),('limon',45),('nane',135),('gok',225),('lavanta',270),('kum',0),('mercan',315),('adacayi',90);
-- 1) eski cizim avatarlari ("kedi:lila") en yakin piksel karaktere
UPDATE uyeler SET avatar = 'px.' || COALESCE((SELECT ad FROM gecici_svg WHERE k = substr(uyeler.avatar, 1, instr(uyeler.avatar, ':') - 1)), 'loaf')
  || ':pixel.' || COALESCE((SELECT ton FROM gecici_ton WHERE r = substr(uyeler.avatar, instr(uyeler.avatar, ':') + 1)), 0)
  WHERE avatar IS NOT NULL AND avatar <> 'foto' AND avatar NOT LIKE 'px.%' AND instr(avatar, ':') > 0;
-- 2) piksel disi bicimler (dots / halftone / voxel) duz piksele, ton korunur
UPDATE uyeler SET avatar = substr(avatar, 1, instr(avatar, ':')) || 'pixel.' || substr(substr(avatar, instr(avatar, ':') + 1), instr(substr(avatar, instr(avatar, ':') + 1), '.') + 1)
  WHERE avatar LIKE 'px.%' AND avatar NOT LIKE 'px.%:pixel.%';
-- 3) avatari olmayan uyelere kimlikten turetilen piksel karakter ve ton (silinmis hesaplar ve sistem hesaplari haric)
UPDATE uyeler SET avatar = 'px.' || (SELECT ad FROM gecici_px WHERE i = uyeler.id % 49) || ':pixel.' || (((uyeler.id / 49) % 8) * 45)
  WHERE (avatar IS NULL OR avatar = '') AND rol NOT IN ('sistem', 'asistan') AND silindi IS NULL;
DROP TABLE IF EXISTS gecici_px;
DROP TABLE IF EXISTS gecici_svg;
DROP TABLE IF EXISTS gecici_ton;