# KPSS Tercihi uygulama yayını

Uygulama canlı siteyi (kpsstercihi.com) açar. Üstüne kaydedilen ilan için son başvuru bildirimi, bağlantısız ekran ve AdMob yeri ekler. Site içi AdSense uygulamada engellidir.

## Yayından önce değişmesi zorunlu olanlar

1. AdMob hesabı açılınca Google'ın örnek uygulama kimliklerini gerçekleriyle değiştir:
   - `android/app/src/main/AndroidManifest.xml` → `ca-app-pub-3940256099942544~3347511713`
   - `ios/App/App/Info.plist` → `ca-app-pub-3940256099942544~1458002511`
2. `docs/uygulama.js` içindeki `BANNER` alanlarına gerçek reklam birimlerini yaz. Boşken reklam SDK'sı başlamaz.
3. Gizlilik politikasına uygulamayı, bildirimleri ve AdMob'u ekle. Mağaza formlarındaki reklam ve veri güvenliği beyanları bununla aynı olmalı.
4. `docs/.well-known/assetlinks.json` gerekmez; uygulama TWA değildir.
5. Kök klasöre `app-ads.txt` eklenir (AdMob yayıncı kimliği belli olunca).

## Google Play

- Bireysel yeni hesap: en az 12 test kullanıcısı, kesintisiz 14 gün kapalı test, sonra üretim başvurusu.
- Hükûmet bilgisi beyanı: açıklamada aşağıdaki resmî olmama cümlesi ve kaynak bağlantıları bulunmalı.
- Sürüm dosyası imzalı `.aab` olmalı: `./gradlew bundleRelease`.

## App Store

- Derleme GitHub Actions macOS makinesinde yapılır; imza için Apple Distribution sertifikası ve profil gerekir.
- İnceleme notuna yazılacak yerel özellikler: kayıtlı ilan için yerel bildirim, bağlantısız ekran.
- ATT izni yalnız reklam birimi tanımlıyken istenir.

## Mağaza metni

**Ad:** KPSS Tercihi: Kamu İlanları

**Kısa açıklama:** Kamu personel alımları, son başvuru hatırlatmaları ve KPSS taban puanları.

**Açıklama:**

Güncel kamu personel alımlarını tek yerde gör. Bugün eklenen ilanları ve son günü yaklaşanları izle, sana uygun olanları filtrele. Kaydettiğin ilanların son başvuru tarihinden önce bildirim al. KPSS taban puanlarını ve kadroları incele.

Bu uygulama resmî değildir ve hiçbir devlet kurumunu temsil etmez. Bilgiler, kurumların resmî duyurularından derlenir. Başvurudan önce ilanın kaynağını kontrol et.

Kaynaklar: https://www.kariyerkapisi.gov.tr · https://www.iskur.gov.tr · https://www.osym.gov.tr
