# Kişisel bildirim botu — tasarım

Kullanıcı Telegram'da botla konuşup öğrenim düzeyi, il, kategori ve anahtar kelime seçer; uygun yeni
ilanlar özelden gelir, son başvuru gününden önce hatırlatılır.

## Çalışma yeri
- Cloudflare Workers (ücretsiz) + D1. Webhook ile anında yanıt; Cron Trigger (`* * * * *`, dakikada bir) ile
  kuyruk boşaltma + 30 dakikada bir tarama. Ayrıntı: aşağıdaki "Sürüm 2" bölümü (eski "Bildirim" bölümünün yerine geçer).
- İlan verisi: `https://kpsstercihi.com/bot-ilanlar.json` (Python `site_uret.py` üretir;
  yalnız açık ilanlar ve botun ihtiyaç duyduğu alanlar). `ILAN_URL` bunu gösterir.
- Kişisel veri yalnız D1'de. Repoya, loglara chat_id/tercih yazılmaz.
- Kanal botundan AYRI bir bot (BotFather). Sırlar: `BOT_TOKEN`, `WEBHOOK_SECRET` (wrangler secret).
- Ortam değişkenleri (wrangler.toml [vars]): `ILAN_URL`, `SITE_URL`, `VIP_ACIK` ("0").
- Bağımlılık yok: düz ES modülleri. Testler `node --test` (Node 22) ile, sahte D1 ve sahte fetch kullanır.

## Modüller ve sahipleri
| Dosya | İçerik | Sahip |
|---|---|---|
| `src/telegram.js` | `tg(env, method, params)` → `result`; hata `ok:false` ise fırlatır. 429'da `retry_after` kadar bekleyip 1 kez yeniden dener. | İşçi B |
| `src/db.js` | Kullanıcı okuma/yazma yardımcıları (JSON alanlar parse edilmiş nesne döner) | İşçi B |
| `src/komutlar.js`, `src/klavye.js`, `src/index.js` | Webhook, komutlar, satır içi klavyeler, `fetch` + `scheduled` dışa aktarımları | İşçi B |
| `src/eslestir.js` | `uygunMu(ilan, kullanici)` → bool; `ilanMetni(ilan)` | İşçi C |
| `src/bildirim.js` | `cronCalistir(env)`, `acikIlanOzeti(env, kullanici)` → string, `ilanMesaji(ilan, sponsor)` | İşçi C |
| `src/sponsor.js` | `sponsorSec(env, kullanici, ilan)` → `{metin, link}` ya da `null` | İşçi C |
| `test/sahte.js` | Sahte D1 (`prepare().bind().all()/first()/run()`, basit SQL'i destekleyen bellek içi) + sahte `fetch` | İşçi B yazar, C kullanır |

`kullanici` nesnesi: `{chat_id, onay, duzeyler:[], iller:[], kategoriler:[], kelimeler:[], aktif, hatirlatma, durum, vip_bitis, puan}`. `puan`: boş olabilen KPSS puanı (REAL, 1–100).

## Eşleştirme kuralı (`uygunMu`)
- Kullanıcı `aktif=1` ve `onay=1` değilse: false.
- Süresi geçmiş ilan (`son_tarih` < bugün, Europe/Istanbul): false.
- `ilan.kategori === 'akademik'`: her zaman false (akademik ilanlar hiçbir yerde gösterilmez; `kullanicilar.akademik` kolonu şemada kalır ama kullanılmaz).
- Düzey: `duzeyler` boşsa geçer. İlanın `ogrenim` listesi boş/yoksa GEÇER (belirsiz ilan kaçırılmaz). Doluysa kesişim gerekir.
- İl: `iller` boşsa geçer. İlanın `iller` listesi boş/yoksa GEÇER (çok ilde/merkezi). Doluysa kesişim.
- Kategori: `kategoriler` boşsa geçer; doluysa `ilan.kategori` listede olmalı (kategorisiz ilan geçer).
- KPSS puanı: kullanıcının `puan`ı VE ilanın sayısal `en_az_puan`ı varsa, `ilan.kpss !== 'kpsssiz'` iken `puan < en_az_puan` ise false (eşitse geçer). Eksik veri asla eleme nedeni olmaz. `en_az_puan` = `yz_kadrolar`ın en düşük `en_dusuk_puan`ı; yalnız her kadroda 1–100 arası sayı varsa yazılır, yoksa null.
- Kelime: `kelimeler` boşsa geçer; doluysa en az biri `ilanMetni(ilan)` içinde (Türkçe küçük harf, `toLocaleLowerCase('tr')`) geçmeli.

## Bildirim (`cronCalistir`)
1. `ILAN_URL`'yi çek. `ilanlar` dizisini al.
2. `bilinen_ilanlar` boşsa (ilk çalıştırma): tüm ilan kimliklerini ekle, kimseye gönderme, çık.
3. Yeni ilanlar = bilinenlerde olmayanlar → `bilinen_ilanlar`a ekle.
4. Her aktif+onaylı kullanıcı için uygun yeni ilanları gönder (`gonderilen`de yoksa); kullanıcı başına çalıştırma başına en fazla 10 ileti, fazlası tek "+N ilan daha: SITE_URL" iletisi. Telegram sınırı için iletiler arası ~40 ms.
5. Hatırlatma: `gonderilen.hatirlatildi=0`, kullanıcı `hatirlatma=1`, ilanın `son_tarih`i yarın (İstanbul) → "Yarın son gün" iletisi, `hatirlatildi=1`.
6. Kullanıcı botu engellediyse (403) `aktif=0` yap.

## İleti biçimi (`ilanMesaji`)
HTML parse_mode; tüm ilan metinleri kaçışlanır (`&<>`). Başlık (kalın), kurum, il(ler), son başvuru tarihi (gg.aa.yyyy), "İlanı incele" bağlantısı (`SITE_URL` + `ilan/<uuid>/` varsa, yoksa `ilan.link`). Sponsor varsa en altta `— Sponsorlu: <metin>` (+ bağlantı). Sponsorsuz ileti sponsor satırı içermez.

## Komutlar (`komutlar.js`)
- `/start`: tanıtım + onay metni ("Uygun ilanları sana özelden göndereceğim. İletilerde zaman zaman 'Sponsorlu' etiketli içerik bulunabilir. Tercihlerini istediğin an /sil ile tamamen silebilirsin.") + [Kabul ediyorum] düğmesi. Kabul → kurulum sihirbazı: düzey → il → kategori → (isteğe bağlı) kelime → özet + `acikIlanOzeti`.
- `/ayarlar`: mevcut tercihler + düzenleme düğmeleri.
- `/kelime`: "Anahtar kelimeleri virgülle yaz (ör. hukuk, bilgisayar). Silmek için 'yok' yaz." → `durum='kelime_bekleniyor'`.
- `/puan`: "KPSS puanını yaz (ör. 72,5). Silmek için 'yok' yaz." → `durum='puan_bekleniyor'`; 1–100 arası, virgül/nokta; /ayarlar'da "KPSS puanı" satırı. Veritabanı: `ALTER TABLE kullanicilar ADD COLUMN puan REAL;` (`migrations/001_puan.sql`).
- `/nereye`: "Puanına ve bölümüne göre başvurabileceğin ilanlar:" + URL düğmesi `SITE_URL/nereye/?d=&b=&p=` (d: tek düzey varsa; b: ilk anahtar kelime; p: puan; bilinmeyen yazılmaz).
- `/durdur`, `/devam`: `aktif` 0/1. `/sil`: kullanıcının tüm satırlarını (kullanicilar + gonderilen) siler.
- `/yardim`. `/vip`: `VIP_ACIK!=="1"` ise "Yakında" yanıtı.
- Klavyeler: düzey çoklu seçim (✓ işaretli), il seçimi sayfalı (81 il, 3 sütun, sayfa başına 24, "Tüm Türkiye"), kategori çoklu seçim (akademik anahtarı yok). `callback_data` ≤ 64 bayt.
- Webhook isteği `X-Telegram-Bot-Api-Secret-Token` başlığı `WEBHOOK_SECRET` ile eşleşmiyorsa 401.
- Grup sohbetlerinden gelen iletiler yok sayılır (yalnız `chat.type === 'private'`).

## Sürüm 2 — ücretsiz plan sınırlarına uygun akış (bağlayıcı)
Doğrulanmış Cloudflare ücretsiz plan sınırları (çağrı başına): **50 D1 sorgusu** (batch içindeki her ifade ayrı sayılır),
**50 dış istek** (her Telegram çağrısı ve fetch), **10 ms CPU**, ifade başına **100 bağlı parametre**, ifade ≤ 100 KB.
Her çağrıda bütçe: en fazla 40 D1 ifadesi, en fazla 30 dış istek. Bütçeyi aşacak iş bir sonraki dakikaya kalır.

### `bot-ilanlar.json` (Python, `bot/site_uret.py` üretir, `docs/` altında, .gitignore'da)
`{"guncelleme": ISO, "ilanlar": [ {id, kimlikler:[...tüm kaynak kimlikleri, id dahil], baslik, kurum, son_tarih|null,
son_zaman|null, ogrenim:[], iller:[], kategori|null, kpss|null, duyuru_turu|null, sayfa: tam URL (site ilan sayfası
ya da resmi link), metin: arama için Türkçe küçük harf, en fazla 1500 karakter} ] }`. Yalnız süresi geçmemiş ilanlar
(son_tarih yoksa dahil). Sayfa bağlantısı mantığı site_uret.py'deki ilan sayfası mantığının aynısı.

### Dakikalık çağrı (`scheduled`)
1. **Boşaltma** (yalnız İstanbul saatiyle 08:00–22:59 arası): `SELECT k.*, b.veri FROM kuyruk k LEFT JOIN
   bilinen_ilanlar b ON b.ilan_id=k.ilan_id ORDER BY k.id LIMIT 25` (1 sorgu) + sponsorlar (1 sorgu, yalnız kuyruk
   doluysa). Her satır için ileti gönder (≤25 istek, aralarda 40 ms). Sonra tek ifadeyle sırasıyla:
   gönderilenleri `DELETE FROM kuyruk WHERE id IN (...)`; başarılı 'ilan' satırlarını çok satırlı
   `INSERT OR IGNORE INTO gonderilen` (satır başı 3 parametre → ifade başına ≤33 satır); 'hatirlatma' satırları
   için `UPDATE gonderilen SET hatirlatildi=1 ...`; 403 alanları `UPDATE kullanicilar SET aktif=0 WHERE chat_id IN (...)`
   + `DELETE FROM kuyruk WHERE chat_id IN (...)`. 429/5xx/ağ hatası alan satır kuyrukta kalır (sonraki dakika
   yeniden denenir); 400 gibi kalıcı hatada satır silinir (sonsuz deneme yok). Telegram 429'da o çağrıda
   gönderimi durdur.
2. **Tarama** (meta.son_tarama 30 dakikadan eskiyse ya da meta.tarama_imleci varsa): `ILAN_URL`'yi çek (1 istek).
   - `bilinen_ilanlar` boşsa (ilk çalıştırma): tüm ilanların tüm kimliklerini ekle (çok satırlı INSERT), kimseye
     kuyruk yazma, son_tarama'yı güncelle, bitir.
   - Yeni ilan = `kimlikler`inin HİÇBİRİ bilinenlerde olmayan ilan. Kimliklerinden biri biliniyorsa ilan yeni DEĞİL;
     bilinmeyen kimliklerini aynı `ana_id` ile ekle ve `ana_id` satırının `veri`/`son_tarih`'ini güncelle.
   - Yeni ilanları `bilinen_ilanlar`a yaz (veri = ileti için gereken alanlar JSON). Yeni ilan kimlikleri
     `meta.tarama_ilanlari`na yazılır.
   - Kullanıcılar `chat_id > meta.tarama_imleci` sırasıyla 200'lük sayfalarla okunur; her kullanıcı için
     `uygunMu` → kuyruğa (`INSERT OR IGNORE INTO kuyruk (chat_id, ilan_id, tur)`, çok satırlı). Kullanıcı başına bir
     taramada en fazla 10 'ilan' satırı; fazlası için tek 'fazla' satırı (ilan_id = '+N'). İfade bütçesi dolarsa
     imleci son işlenen chat_id'ye yaz ve çık; sonraki dakika kaldığı yerden devam eder (aynı tarama_ilanlari ile).
     Tüm kullanıcılar bitince imleci ve tarama_ilanlari'nı sil, son_tarama'yı yaz.
   - Zaten gönderilmiş (gonderilen) ya da kuyrukta olan ilan tekrar eklenmez (UNIQUE + gonderilen kontrolü:
     yeni ilan kimlikleri için `SELECT chat_id, ilan_id FROM gonderilen WHERE ilan_id IN (...)` — normalde boş).
3. **Hatırlatma** (günde bir kez, İstanbul saatiyle 09:00 sonrası ilk çağrıda; meta.son_hatirlatma_gunu ile):
   tek ifade: `INSERT OR IGNORE INTO kuyruk (chat_id, ilan_id, tur) SELECT g.chat_id, g.ilan_id, 'hatirlatma' FROM
   gonderilen g JOIN bilinen_ilanlar b ON b.ilan_id=g.ilan_id JOIN kullanicilar u ON u.chat_id=g.chat_id WHERE
   b.son_tarih=?yarin AND g.hatirlatildi=0 AND g.zaman < ?bugunBasi AND u.aktif=1 AND u.onay=1 AND u.hatirlatma=1`.
   Bugün gönderilmiş ilan için ayrıca hatırlatma gitmez.

### İleti kuralları
- `duyuru_turu` doluysa başlığın önünde etiket: "⚠️ İptal duyurusu:" / "📝 Düzeltme / süre değişikliği:" (metin olduğu
  gibi, kaçışlanmış).
- Süre kontrolü: `son_zaman` varsa ve geçmişse gönderme; yoksa `son_tarih` < bugün ise gönderme. Kuyruktan
  gönderim anında da kontrol et (kuyrukta beklerken süresi dolan ilan atlanıp silinir).
- `son_tarih` yoksa iletide "Son başvuru: ilanda belirtilmiş" yerine o satır hiç yazılmaz; özet listede tarih yerine
  "tarih yok" yazılır ve sıralamada sona konur.
- Tüm dinamik metin HTML kaçışlı (özet dahil). Sponsor linki yalnız `https://` ise bağlantı olarak eklenir.

## Web Push (tarayıcı bildirimi) — `src/web.js`, `docs/sw.js`
`/nereye/` sayfasındaki "Yeni ilan çıkınca haber ver" kaydı. Telegram akışından bağımsız; `VAPID_OZEL` (gizli) ve `VAPID_ACIK` ([vars]) yoksa tamamen kapalıdır.
- Tablolar (`migrations/002_web.sql`): `web_aboneler` (endpoint PK; düzey/bölüm/puan; her endpoint tek arama), `web_bekleyen` (endpoint, ilan_id PK; başlık, kurum, url).
- Uçlar (CORS: `https://kpsstercihi.com`, `http://localhost:*`, `http://127.0.0.1:*`; gövde ≤ 4 KB; endpoint yalnız https + bilinen push ana bilgisayarı): `POST /web/abone`, `/web/sil`, `/web/bekleyen` (en çok 5 ilan + `toplam` döner, o abonenin bekleyenlerini siler).
- Cron: Telegram taraması yeni ilan bulunca kimlikleri `meta.web_ilanlari`na da yazar (en çok 50). Ayrı adımda (4) `ILAN_URL` bir kez çekilir; aboneler `endpoint > meta.web_imleci` imleciyle sayfalanır (sayfa ≤ min(100, kalan istek bütçesi, 2000/ilan sayısı)). Eşleşme: akademik ve süresi geçmiş ilan yok; ilan `ogrenim` boşsa ya da abone düzeyini içeriyorsa; bölüm yazılıysa katlanmış (Türkçe → ASCII) kelimelerin HEPSİ ilan metninde (ve, bölümü, programı gibi genel kelimeler atılır); abone puanı < `en_az_puan` ise (kpsssiz değilse) eleme. Abone başına işte en çok 5 bekleyen yazılır (`INSERT OR IGNORE`), sonra yük'süz push gider (abone başına tek). 404/410 → abone ve bekleyenleri silinir. İş bitince `web_ilanlari`/`web_imleci` silinir, 7 günden eski bekleyenler temizlenir. Bütçe: iş için ≥10 ifade ve ≥3 istek kalmışsa çalışır, değilse sonraki dakika.
- VAPID (RFC 8292): JWT ES256, `aud` = endpoint origin, `exp` = +11 saat, `sub` = `mailto:VAPID_IRTIBAT` ya da `https://kpsstercihi.com`; başlıklar `Authorization: vapid t=<jwt>, k=<VAPID_ACIK>`, `TTL: 86400`, `Urgency: normal`. JWT origin başına bellekte önbelleğe alınır. `VAPID_OZEL` = ham özel değer d (32 bayt base64url; PKCS8 base64url da kabul). Anahtar üretimi: `node vapid-uret.mjs` (yalnız konsola yazar).
- `docs/sw.js`: yalnız `push` ve `notificationclick`; push gelince `/web/bekleyen`i çağırır, en çok 3 bildirim (fazlası "N yeni ilan"), hata olursa genel bildirim. Önbellek/fetch yakalama yok.
