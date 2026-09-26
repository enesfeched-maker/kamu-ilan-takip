# İlan kaynakları

Kariyer Kapısı RSS ve açık ayrıntı servisine ek olarak İŞKUR kamu memur alım listeleri ve SBB Kamu İlan listesi okunur. `config.json` içindeki `ek_kaynaklar` dizisi `sbb` ve `iskur` değerlerini etkinleştirir. Mevcut GitHub Actions tarama ve yayın akışı kullanılır.

Yeni kaynakların ilk başarılı taraması sessiz başlangıçtır: ilanlar siteye eklenir, Telegram'a topluca gönderilmez. Daha sonra yeni ilanlar mevcut görsel ve kısa mesaj biçimiyle gönderilir. `--duyur-mevcut` açıkça seçilirse mevcut ilanlar da gönderim kuyruğuna alınır. Çalışma başına toplam 15 mesaj sınırı geçerlidir.

İŞKUR'da ilan bulunan il sayfalarından kurum, başlık, il, son tarih/saat ve resmî belge bağlantısı alınır. SBB'de başlık ve kontenjan listeden; tarih yılı PDF içindeki açık tarihle doğrulanarak alınır. Tarih doğrulanamazsa boş kalır, tahmin edilmez ve hatırlatma gönderilmez. Belgelerin tam metni ve özgün görselleri yeniden yayımlanmaz. SBB belge bağlantısı dışarıdan doğrudan açılmadığından kullanıcı SBB ana sayfasında kurum adıyla aramaya yönlendirilir.

Gönderilmiş ve son üç gün hatırlatması yapılmış ilanların geçmişi korunur. Kaynaklar arasında kimlik, aynı belge veya kurum/tarih/ilan türü/kontenjan eşleşmesi tekil olduğunda kayıt birleştirilir; belirsiz eşleşmeler ayrı tutulur. İptal/düzeltme duyuruları ayrı işaretlenir ve başvuru hatırlatması almaz.

Bir kaynak veya il sayfası okunamazsa diğer kaynaklar devam eder; eski kayıtlar korunur, kaynak durumunda hata kaydedilir. SBB ayrıntıları 12 saat önbelleğe alınır. İlan formatı değişirse ayrıştırıcı güncellenmelidir. Kaynak erişimi ve GitHub zamanlamaları garanti değildir; resmî ilan güncel başvuru koşullarında esas alınır.
