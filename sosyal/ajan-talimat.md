# Sosyal medya ajanı talimatı (Claude bulut rutini, haftada bir)

Amaç: KPSS Tercihi'nin Instagram, TikTok ve YouTube videolarının ölçümlerine bakıp botun **sınırlı** ayarlarını
gerekirse değiştirmek ve kararı kısa bir notla açıklamak. Videoları sen üretmez ve paylaşmazsın; onu bot yapar.
Emin değilsen ayarı değiştirme: az veriyle karar vermek, hiç karar vermemekten kötüdür.

## Adımlar

1. `python -m pip install -q Pillow beautifulsoup4` (gerekirse), sonra `python bot/sosyal_ajan.py hazirla`.
   `sosyal-is/durum.json` oluşur: son 30 günün paylaşımları ve Instagram ölçümleri, bu hafta / önceki hafta toplamları,
   geçerli ayar ve izin verilen sınırlar.
2. `sosyal/voice.md` (ses profili) ve `sosyal/ajan-gunlugu.md` (önceki kararların) dosyalarını oku.
3. Kararını `sosyal-is/karar.json` dosyasına yaz:
   ```json
   {
     "ayar": {
       "ilan_gunluk": 3,
       "son_gun_ufuk": 3,
       "ozet_en_az": 2,
       "sorular": {"ilan": ["Başvurmayı düşünüyor musun? 👇"], "son_gun": ["Sen hangisine başvurdun? 👇"]}
     },
     "not": "Ne gördün, neyi neden değiştirdin ya da neden değiştirmedin. 2–4 cümle, sayılarla."
   }
   ```
4. `python bot/sosyal_ajan.py kaydet` — kararı denetler; `sosyal/ayar.json` ve `sosyal/ajan-gunlugu.md` dosyalarına işler.
   "Atlandı" satırı varsa karar.json'u düzeltip yeniden çalıştır.
5. Yalnız bu iki dosyayı bu çalışmaya özel YENİ bir dala gönder (komutları ayrı ayrı çalıştır):
   ```
   git checkout -b sosyal-ajan-YYYYAAGG-SSDD
   git add sosyal/ayar.json sosyal/ajan-gunlugu.md
   git commit -m "Sosyal ajan kararı"
   git push origin sosyal-ajan-YYYYAAGG-SSDD
   ```
   `git push -f`, `git reset --hard` ve var olan dala gönderme kullanma. main'e doğrudan gönderme, başka dosya değiştirme.
   `.github/workflows/sosyal-ajan.yml` dalı denetleyip main'e alır ve siler.

## Ayarlar

- **ilan_gunluk** (1–4): günde en çok kaç "tek ilan" videosu. Tek ilan videolarının medyan izlenmesi diğer biçimlerden
  belirgin düşükse azalt, yüksekse artır. 4'ün üstü YouTube yükleme kotasını aşar.
- **son_gun_ufuk** (1–5): sabah videosuna son başvurusuna en çok kaç gün kalan ilanlar girer.
- **ozet_en_az** (2–4): akşam özeti için o gün eklenmiş en az ilan sayısı.
- **sorular**: açıklamanın sonundaki soru cümlesi; türler `genel`, `son_gun`, `ilan`, `ozet`. Tür başına en çok 3 cümle,
  her biri en çok 90 karakter ve soru işaretli. Yalnız değiştirmek istediğin türü yaz; yazmadığın tür botun kendi
  listesini kullanır. `ayar` içinde yazmadığın sayısal alan varsayılana döner, o yüzden korumak istediğin değeri yaz.

## Kurallar

- Karar için en az **6 ölçülmüş video** gerekir (`bu_hafta.olculen` + `onceki_hafta.olculen`). Yoksa `ayar` olarak
  `gecerli_ayar`ı aynen yaz, notta verinin yetmediğini söyle.
- Bir çalışmada en çok **bir sayısal ayarı bir adım** değiştir; neyin işe yaradığı ancak böyle anlaşılır.
- Aynı ayarı iki hafta üst üste ters yöne çevirme; günlükte önceki kararına bak.
- Soru cümlelerinde ses profiline uy: sıcak, emir kipi yok. "Kaçırma", "hemen", "şok", "müjde", atama vaadi yazılmaz.
- Sayı uydurma; notta yalnız durum.json'daki sayıları kullan. Ölçümler yalnız Instagram'dandır.
