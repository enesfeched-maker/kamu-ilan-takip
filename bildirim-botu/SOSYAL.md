# Sosyal medya paylaşımı — tasarım (bağlayıcı sözleşme)

## Akış
1. **Python (`bot/sosyal_paylasim.py`, `site_uret.py` her çalıştığında çağrılır):** "dün" (Europe/Istanbul) ilk
   kez görülen, süresi geçmemiş ilanlardan günlük paylaşım üretir → `docs/paylasim/<YYYY-MM-DD>/` (JPEG) ve
   `docs/paylasim/gunluk.json`. Seçim yalnız tarihe bağlı olduğundan gün içindeki her yeniden üretim AYNI sonucu
   verir; böylece site her yayınlandığında dosyalar yeniden oluşur ve URL'ler gün boyu canlı kalır. Klasörler
   .gitignore'da (repoya girmez; Pages artefaktıyla yayınlanır). Yalnız bugünün klasörü üretilir.
2. **Cloudflare Worker (`bildirim-botu/src/sosyal.js`), dakikalık cron içinde, günde bir kez:**
   - İstanbul 10:15 sonrası ilk çağrıda ve `meta.sosyal_son_gun` ≠ bugün ise: `SITE_URL + 'paylasim/gunluk.json'`
     çekilir; `tarih` bugün değilse ya da `bos` ise o gün için hiçbir şey yapılmaz (`sosyal_son_gun` yazılır).
   - Bu çağrıda kuyruk boşaltma/tarama YAPILMAZ (dış istek bütçesi sosyal işe ayrılır; ≤40 istek).
   - **Instagram** (yalnız `IG_TOKEN` D1/sır mevcutsa): kaydırmalı gönderi (carousel) yayınlar. İdempotent:
     `meta.ig_son_gun` = bugün ise atlanır; başarıdan sonra yazılır.
   - **X taslağı** (yalnız `meta.yonetici_chat` varsa): yöneticiye özelden `sendPhoto` (photo = kapak URL'si,
     caption = `x_metin`) gönderilir; `meta.x_son_gun` ile günde bir kez.
3. **Yönetici tanıma:** `YONETICI_KULLANICI` gizli ayarı (wrangler secret; repoya yazılmaz) (Telegram kullanıcı adı, @ olmadan, küçük harf
   karşılaştırma). Bu kullanıcıdan gelen herhangi bir özel iletide `meta.yonetici_chat` = chat_id yazılır (log yok).

## `docs/paylasim/gunluk.json`
```json
{
  "tarih": "2026-10-02",            // paylaşım günü (İstanbul) — içerik bir önceki günün ilanları
  "bos": false,                      // uygun ilan yoksa true ve diğer alanlar boş
  "ilan_sayisi": 7,                  // dün eklenen uygun ilan sayısı (gösterilen ≤ 9)
  "kapak_tasarimi": "manset",        // o günün kapak tasarımı (manset | mozaik | kacirma; bos ise null); Instagram istatistikleriyle karşılaştırmak için kaydedilir
  "gorseller": ["https://.../paylasim/2026-10-02/00-kapak.jpg", "https://.../01.jpg", "..."],  // ≤ 10, ilki kapak
  "ig_metin": "…",                   // ≤ 2200 karakter, sonunda hashtag'ler ve son satırda "kamuilan-2026-10-02" işareti YOK (işaret D1'de)
  "x_metin": "…"                     // ≤ 280 karakter (X ağırlıklı sayımına göre güvenli: ≤ 260 düz karakter), BAĞLANTI İÇERMEZ
}
```
- Görseller: JPEG, 1080×1350 (4:5), sRGB, ≤ 1 MB. Kapak: günün verisinden türetilen kancalı tasarım (manset / mozaik / kacirma; bot/kapak_tasarimlari.py), küçük marka logosu (docs/kamu-logo.png).
   Kartlar: kurum, başlık, kadro özeti, il, son başvuru tarihi, kaynak; alt bilgi "Ayrıntılar ve
  başvuru bağlantısı: profildeki bağlantı". Tüm metin resmi kayıttan; tahmin yok, boş alan gösterilmez.
- Seçim: ilk_gorulme dün (İstanbul) olan, `duyuru_turu` boş (iptal/düzeltme hariç), süresi geçmemiş ilanlar;
  sıra: son_tarih yakın olan önce (tarihsiz sona), sonra ilk_gorulme. En fazla 9 kart.
- `ig_metin`: kısa giriş + madde madde "Kurum — başlık (son başvuru gg.aa)" + "Tüm ilanlar ve başvuru bağlantıları
  profildeki bağlantıda." + hashtag'ler (#kamuilanları #kpss #memuralımı #kamupersonel, ilanlardan #il ve düzey).
- `x_metin`: "📢 Bugün N yeni kamu ilanı" + en fazla 3 kısa satır + "Ayrıntılar profilde." + 2-3 hashtag. URL yok
  (X'te bağlantılı gönderi 13 kat pahalı; ayrıca alan adı yazımı da bağlantı sayılır — site adresi YAZILMAZ).

## Instagram API (Instagram Login ile, graph.instagram.com)
- Sırlar/veriler: ilk kurulumda `IG_TOKEN` ve `IG_USER_ID` wrangler secret olarak girilir (`kurulum-instagram.ps1`,
  gizli giriş). Çalışırken güncel token D1 `meta.ig_token` (+ `meta.ig_token_tarih`) içinde tutulur; varsa sırdan
  önceliklidir. Token 50 günden eskiyse `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=…`
  ile yenilenir ve D1'e yazılır. Token asla loglanmaz/hata metnine konmaz.
- Yayın: her görsel için `POST /{IG_USER_ID}/media` (image_url, is_carousel_item=true) → çocuk id'leri;
  `POST /{IG_USER_ID}/media` (media_type=CAROUSEL, children=…, caption=ig_metin) → kapsayıcı; durum
  `GET /{container}?fields=status_code` FINISHED olana dek (≤ 6 deneme, 5 sn arayla); `POST /{IG_USER_ID}/media_publish`
  (creation_id). Tek görsel varsa carousel yerine tek görsel gönderisi. API sürümü sabit bir değişkende (`IG_API`).
- Hata: herhangi bir adım başarısızsa o gün yeniden denenmez (çift gönderi riskini önlemek için `ig_son_gun`
  yine de yazılır ve `meta.ig_son_hata` kısa mesaj olarak tutulur); yöneticiye tek satır bilgi iletisi gider.

## Yönetici sabitleme ve dayanıklılık notları
- `meta.yonetici_chat` yalnız ilk eşleşmede yazılır ve sonra DEĞİŞMEZ (kullanıcı adı başkasına geçse bile). Yöneticiyi değiştirmek için D1'den elle silin: `DELETE FROM meta WHERE anahtar='yonetici_chat'`.
- Instagram anahtarı yenileme/taşıma içerikten bağımsız günde bir kez (`meta.ig_token_gunu`) çalışır. `gunluk.json` tarihi bugün değilse gün kaybolmaz; en sık 10 dakikada bir yeniden denenir (`meta.sosyal_son_deneme`).
- Kilit değeri `<bitis>:<sahip>` biçimindedir; yalnız sahibi bırakır; sosyal adımda 5 dakikaya uzatılır.
