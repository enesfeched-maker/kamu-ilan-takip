# KPSS Tercihi — proje hafızası

Türkiye'deki kamu ilanlarını (KPSS ile atanma, sözleşmeli personel, belediye alımları) toplayıp
Telegram kanalına (@kpsstercihi) ve GitHub Pages sitesine yayınlayan bot. Amaç: KPSS adaylarına
fayda + reklam/sponsor geliri. Sohbet dili Türkçe; kod adları Türkçe.

## Çalışma düzeni
- Orkestra şefi: Opus (planlar, karar verir, entegre eder, kendi diff'ini kontrol eder).
- `.claude/agents/isci.md` (Sonnet, düşük efor): dar kapsamlı kodlama/ayrıştırma işleri.
- `.claude/agents/denetci.md` (Opus, orta efor): işçi çıktısını inceler, düzeltme listesi verir.
- Ajanları yalnız büyük/tekrarlı işlerde kullan; küçük işleri doğrudan yap (token tasarrufu).
- Her özellik ayrı dal + PR; kullanıcı main'e kendisi birleştirir.
- Push öncesi: `python -m unittest discover -s bot -p 'test_*.py'` hepsi geçmeli.
- Dosyaların çoğu CRLF satır sonlu; düzenlerken satır sonlarını koru, ilgisiz satır değiştirme.

## Bağlam ve model düzeni (geliştirme oturumları; yz_claude ilan okuma rutini hariç)
- Oturum `claude --model sonnet --advisor opus` ile açılır: ana oturum Sonnet, danışman Opus.
- Tüm kod tabanı aramaları ve testler Haiku alt ajanlarına bırakılır: `search` (tarama), `grep` (çağrı konumları), `audit` (denetim + test, kendi worktree'inde). Ana bağlam sade kalır.
- Hızlı, kesin küçük seçimler (araç seçme, yol seçme, yeniden deneme) danışmana sorulmadan verilir.

## Mimari
- `bot/ilan_bot.py`: ana akış. Kariyer Kapısı RSS + ayrıntı API, İŞKUR, SBB → `docs/ilanlar.json`.
  `--prepare` (tarama) ve `--send-only` (Telegram) adımları `.github/workflows/ilan.yml` içinde.
- `bot/ek_kaynaklar.py`: İŞKUR ve SBB ayrıştırıcıları. `bot/resmi_detay.py`: Kariyer Kapısı ayrıntıları.
- `bot/siniflandir.py`: öğrenim düzeyi (lisans/onlisans/ortaogretim), kategori, KPSS, il etiketleri.
  Metinde açık değilse tahmin ETME, boş bırak.
- `bot/veri_kaydet.py`: kayıt birleştirme; tarama başına tek commit, yalnız zaman damgası
  değiştiyse commit atlanır (3 saatte bir tazelenir).
- `bot/yerel_tara.py`: kullanıcının Windows bilgisayarında 30 dk'da bir çalışan yerel tarayıcı
  (Türkiye IP'si gerektiren kaynaklar için). `docs/yerel-kaynaklar.json`'a GitHub API ile yazar.
- `docs/`: site (index.html, portal.js, portal.css), `site_uret.py` ilan sayfalarını üretir.
- `bot/puan_ayikla.py`: ÖSYM "sayısal bilgiler" PDF'lerinden (en küçük/en büyük puan) `docs/puanlar/<düzey>.json`
  üretir; YERELDE elle çalıştırılır (ÖSYM yurt dışından kapalı). Site sayfası: `docs/puanlar/` (tablo + tercih robotu).
- `bot/nitelik_ayikla.py`: kılavuz + nitelik kodları + program listesinden bölüm eşleştirmesi; kayıtlara `nit` ekler,
  `docs/puanlar/<düzey>-bolum.json` yazar. Sıra: önce puan_ayikla, sonra nitelik_ayikla (ikinci betik JSON'u günceller).
- Gönderim geçmişleri (`telegram_gonderilen`, `telegram_hatirlatilan`) asla silinmemeli.

## Bilinen kısıtlar
- GitHub Actions (yurt dışı IP) ÇŞB yerelyonetimler.csb.gov.tr, osym.gov.tr, dokuman.osym.gov.tr
  ve SBB'ye erişemiyor → bunlar yerel tarayıcıdan ya da elle yüklenen dosyalardan gelmeli.
- Kariyer Kapısı ayrıntı servisi ara sıra erişilemez; ilan bekletilir, iş başarısız sayılmaz.

## Yol haritası (27 Kasım 2026'da güncellendi)
Hedef (12 Kasım 2026, kullanıcı): 12 ay sonunda aylık 20–40 bin TL net; reklam + sponsor; harcama yalnız kazançtan.
Ölçü: ayda ~300 bin sayfa görüntüleme (13 Kasım: ~90 bin) ve 10 bin Telegram abonesi (12 Kasım: 1,23 bin).

Biten temel: ilan toplama (SBB, KK, ÇŞB, İŞKUR) + kanal + site (kpsstercihi.com), taban puanları ve tercih robotu,
il/kurum/meslek/puan aralığı sayfaları, /nereye/ aracı, site asistanı, AdSense (16 Kasım onay), sosyal otomasyon
(IG/YT/TikTok/FB), Cloudflare zamanlayıcısı + bekçi.

Şimdi (sırayla):
1. **Tercih haftası 2026/2 (kılavuz ~17 Aralık, tercihler ~17–24 Aralık)** — yılın trafik zirvesi.
   - Kılavuz çıkınca: kadro tablolarını oku → /kpss-taban-puanlari/ ve /nereye/ sayfalarına "2026/2'de açılan kadro" işle.
   - Sosyal: kancalı videolar (bot/kanca.py: puanla / atanan / aralik) tercih haftasında her gün 2 kez; kılavuz
     verisiyle "X puanla bu dönem nereye yazılır" dizisi eklenecek.
   - Kanalda sabit tercih gönderisi (metin göndermeden önce kullanıcıya gösterilir).
2. **Sosyal büyüme**: günde 3 video (12:30 kanca, 18:00 yeni ilan/özel, 21:00 kanca), gece paylaşım yok
   (bot/yayin_kapisi.py). Kancalı biçimin izlenmesi 2 haftada ölçülür (≈11 Aralık); tutmazsa dizi/kanca metni değişir.
3. **Telegram**: gece 23–08 ilan yok, ilanlar gün boyu aralıklı (config telegram_aralikli). Abone büyümesi izlenir.
4. **Gelir ölçümü**: ≈8 Aralık otomatik reklam karşılaştırması (17–21 Kasım: RPM ₺26,9, görünürlük %35–40).
5. Sonra: sponsor (5 bin aboneden önce teklif yok), mobil uygulama (#277, mağaza ücreti gelirden), yerel analiz.

Bakım takvimi: tarayıcı GitHub anahtarı ~30 Aralık 2026 yenilenir; zamanlayıcının GH_TOKEN'ı süresi dolmadan yenilenir.

## Kararlar
- Kanalı şimdilik BÖLME (az abone); etiketler + kişisel bot. Binlerce aboneden sonra düzeye göre kanallar.
- GitHub Actions + Pages ile devam (ücretsiz). macOS runner Kariyer Kapısı erişimi için korunuyor.
- Site ve kanal resmi değildir; veriler resmi kaynaklardan, tahmin yok.
