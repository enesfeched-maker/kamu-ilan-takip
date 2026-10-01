# Kamu İlan Takip — proje hafızası

Türkiye'deki kamu ilanlarını (KPSS ile atanma, sözleşmeli personel, belediye alımları) toplayıp
Telegram kanalına (@kamuilantakip) ve GitHub Pages sitesine yayınlayan bot. Amaç: KPSS adaylarına
fayda + reklam/sponsor geliri. Sohbet dili Türkçe; kod adları Türkçe.

## Çalışma düzeni
- Orkestra şefi: Opus (planlar, karar verir, entegre eder, kendi diff'ini kontrol eder).
- `.claude/agents/isci.md` (Sonnet, düşük efor): dar kapsamlı kodlama/ayrıştırma işleri.
- `.claude/agents/denetci.md` (Opus, orta efor): işçi çıktısını inceler, düzeltme listesi verir.
- Ajanları yalnız büyük/tekrarlı işlerde kullan; küçük işleri doğrudan yap (token tasarrufu).
- Her özellik ayrı dal + PR; kullanıcı main'e kendisi birleştirir.
- Push öncesi: `python -m unittest discover -s bot -p 'test_*.py'` hepsi geçmeli.
- Dosyaların çoğu CRLF satır sonlu; düzenlerken satır sonlarını koru, ilgisiz satır değiştirme.

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

## Yol haritası (sırayla)
1. [PR #2 açık] Öğrenim düzeyi filtresi + Telegram etiketleri.
2. [Taban puanları 3 düzey 2022–2026 hazır; kaynak PDF'ler: C:\Users\Feched\Desktop\kamu-ilan\111lisans|111önlisans|111ortaöğretim. bölüm eşleştirme hazır] KPSS taban puanları (2022–2026 öncelikli; kullanıcının klasörü:
   `C:\Users\Feched\Desktop\codex-ws\KPSS_Lisans_2010_2026`) → aranabilir tablo + tercih robotu.
   Sonra önlisans ve ortaöğretim.
3. Kişisel bildirim botu: kullanıcı düzey/il/bölüm seçer, uygun ilanlar özelden gelir.
4. ÇŞB yerel yönetimler kaynağı (İŞKUR'da olmayan belediye ilanları + iptal duyuruları) yerel tarayıcıya.
5. Sonra: domain, AdSense (kullanıcı açacak), Instagram/X hesapları + otomatik paylaşım,
   Telegram sponsorlu gönderi / VIP kanal.

## Kararlar
- Kanalı şimdilik BÖLME (az abone); etiketler + kişisel bot. Binlerce aboneden sonra düzeye göre kanallar.
- GitHub Actions + Pages ile devam (ücretsiz). macOS runner Kariyer Kapısı erişimi için korunuyor.
- Site ve kanal resmi değildir; veriler resmi kaynaklardan, tahmin yok.
