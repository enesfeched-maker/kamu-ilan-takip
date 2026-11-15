-- 0003: sohbet odaları (kategori 'oda') + uygulama içi bildirimler için indeksler.
-- Tablo değişikliği yok. yanitlar(baslik_id, id) zaten var (sayfalama ve /yeni bu indeksi kullanır).
-- yanitlar_ust: "alıntı" bildirimi (ust_id ile üyenin yanıtına bağlanan yanıtlar); yanitlar_olusma: son 14 günün anma taraması.
-- Mevcut veritabanına bir kez uygulanır: wrangler d1 execute <ad> --local|--remote --file migrations/0003_odalar.sql
CREATE INDEX IF NOT EXISTS yanitlar_ust ON yanitlar(ust_id);
CREATE INDEX IF NOT EXISTS yanitlar_olusma ON yanitlar(olusma);
