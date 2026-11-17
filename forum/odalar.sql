-- Sabit sohbet odaları (sistem üyesi, kategori 'oda'). Tekrar çalıştırmak güvenlidir: aynı adlı oda varsa eklenmez.
-- Uygulama: wrangler d1 execute <ad> --local|--remote --file odalar.sql
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket, duzey)
SELECT 'oda', 'Lisans odası', 'Lisans düzeyindeki ilanları, puanları ve tercihleri burada konuşabiliriz. Sorunu yaz, bilenler yanıtlasın.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER), 'lisans'
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'Lisans odası');
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket, duzey)
SELECT 'oda', 'Önlisans odası', 'Önlisans düzeyindeki ilanları, puanları ve tercihleri burada konuşabiliriz. Sorunu yaz, bilenler yanıtlasın.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER), 'onlisans'
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'Önlisans odası');
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket, duzey)
SELECT 'oda', 'Ortaöğretim odası', 'Ortaöğretim düzeyindeki ilanları, puanları ve tercihleri burada konuşabiliriz. Sorunu yaz, bilenler yanıtlasın.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER), 'ortaogretim'
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'Ortaöğretim odası');
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket, duzey)
SELECT 'oda', 'EKPSS odası', 'EKPSS ilanlarını ve tercihlerini burada konuşabiliriz. Sorunu yaz, bilenler yanıtlasın.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER), 'ekpss'
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'EKPSS odası');
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket)
SELECT 'oda', 'Tercih dönemi odası', 'Tercih döneminde yaşadıklarını, sorularını ve tercih listelerini burada paylaşabilirsin.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER)
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'Tercih dönemi odası');
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket)
SELECT 'oda', 'Sınava çalışanlar odası', 'Sınava hazırlananlar çalışma düzenini, kaynakları ve sorularını burada paylaşabilir.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER)
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'Sınava çalışanlar odası');
INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket)
SELECT 'oda', 'Atananlar ve yeni memurlar odası', 'Ataması çıkanlar ve göreve yeni başlayanlar deneyimlerini ve sorularını burada paylaşabilir.', 1, 'sistem', 1, CAST(strftime('%s', 'now') AS INTEGER), CAST(strftime('%s', 'now') AS INTEGER)
WHERE NOT EXISTS (SELECT 1 FROM basliklar WHERE kategori = 'oda' AND baslik = 'Atananlar ve yeni memurlar odası');
