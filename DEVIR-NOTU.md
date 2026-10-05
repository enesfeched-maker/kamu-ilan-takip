# Devir notu — bulut oturumundan yerel oturuma (1 Ekim 2026)

> Bu metni yeni yerel Claude Code oturumunun ilk mesajı olarak yapıştır.
> Proje kuralları ve mimari ayrıca repodaki `CLAUDE.md` dosyasında; yerel oturum onu otomatik okur.

## Ben kimim, ne istiyorum
KPSS adaylarına kamu ilanlarını, atama haberlerini, bölümlerin taban puanlarını ve tercih
rehberliğini sunup reklam/sponsor geliri elde etmek istiyorum. Önce sistemi oturtacağız, sonra
Telegram + Instagram + X'te organik içerikle büyüyeceğiz. Hedef kitle: lisans, önlisans, lise KPSS.
Telegram kanalı: @kamuilantakip (şu an 6 abone). Site: https://kpsstercihi.com/
Repo: https://github.com/enesfeched-maker/kamu-ilan-takip

Çalışma şekli: Opus orkestra şefi (planlar/karar verir/entegre eder), işçi ajan (Sonnet, düşük efor)
kodlar, denetçi ajan (Opus, orta efor) inceler. Tokenları hızlı bitirmeyecek şekilde çalış.
Her özellik ayrı PR, main'e ben birleştiririm.

## Önceki bulut oturumunda yapılanlar
1. **PR #1 (birleştirildi):**
   - 30 Eylül'deki "Run failed" e-postalarının sebebi bulundu ve düzeltildi. Kariyer Kapısı ayrıntı
     servisine geçici erişim sorunu işi kırmızı yapıyordu; artık ilan bekletiliyor, iş yeşil kalıyor.
   - Veri commit'leri sadeleştirildi: tarama başına en fazla 1 commit, yalnız zaman damgası
     değişince commit yok.
   - Yerel tarayıcının veri aktarımları ayrıca tam tarama başlatmıyor.
   - `.claude/agents/isci.md` ve `denetci.md` eklendi.
2. **PR #2 (açık, birleştirmeyi bekliyor):**
   - `bot/siniflandir.py`: öğrenim düzeyi, kategori, KPSS ve il etiketleri.
   - Telegram mesajlarına `#lisans #belediye #Ankara` gibi etiketler eklendi.
   - Siteye "Öğrenim / alan" filtresi eklendi. 73 test geçiyor.
3. **Erişim testi:** ÇŞB (yerelyonetimler.csb.gov.tr) ve ÖSYM, GitHub sunucularından erişilemiyor
   (yurt dışı IP engeli). Bu kaynaklar yerel bilgisayardan okunmalı.
4. **ÇŞB ile İŞKUR karşılaştırması:** ÇŞB'de İŞKUR'da olmayan belediye ilanları var (Şile, Posof),
   ayrıca iptal duyuruları var. Eklemeye değer, ama en sona bırakıldı.

## Verdiğim kararlar
- Öncelik sırası: (a) bot/site sağlamlaştırma, (b) KPSS taban puanları, (c) tercih rehberi, (d) gelir.
- Taban puanlarında 2022–2026 yılları; tercih robotu istiyorum.
- Domain sistem oturduktan sonra alınacak. AdSense hesabım yok, açılacak.
  Telegram sponsorlu gönderi / VIP kanal fikirlerine açığım.
- Sosyal medya hesapları henüz yok, açılacak; otomatik paylaşım istiyorum.
- Şimdilik GitHub Actions + Pages ile devam.
- Kanal bölme önerisi onaylandı: şimdilik tek kanal + etiketler, sonra kişisel bildirim botu,
  abone çoğalınca düzeye göre kanallar.

## Şimdi yapılacak iş
1. KPSS LİSANS taban puanları. Veri bu bilgisayarda:
   `C:\Users\Feched\Desktop\codex-ws\KPSS_Lisans_2010_2026`
   - Klasörü incele (dosya türleri, yıllar, sütunlar).
   - 2022–2026'yı ayıkla ve repoya düzenli veri olarak koy (ör. `docs/puanlar/lisans.json`).
   - Sitede aranabilir taban puan sayfası ve tercih robotu yap.
   - Sonra önlisans ve lise verileri.
2. Ardından kişisel bildirim botu, en sonda ÇŞB kaynağı.
