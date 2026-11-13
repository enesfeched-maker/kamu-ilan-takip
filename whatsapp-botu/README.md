# WhatsApp kanal botu

Bu bilgisayarda ayrı bir WhatsApp Web oturumu kullanır (`whatsapp-web.js`; resmî Meta kanal API'si değildir).
Tarayıcıdaki kişisel profil kopyalanmaz. Telefonda bir kez QR okutulur. Bilgisayar ve internet açık olmalı;
Codex'in veya görünür bir tarayıcı penceresinin açık kalması gerekmez.

`kurulum.ps1`, kaynakları `%LOCALAPPDATA%\KpssTercihi\whatsapp-botu` altına kurar ve
`KPSS WhatsApp Kanal Botu` zamanlanmış görevini oluşturur. Oturum açıldığında gizli başlar;
beklenmeyen çıkışta bir dakika sonra yeniden denenir. Çalışan hizmet kod deposunun otomatik
güncellemelerinden bağımsızdır. Oturum ve gönderim geçmişi `veri/` altındadır; yedeklerken
bu klasörü özel tut, repoya yükleme. Kurulumu tekrar çalıştırmak bu verileri silmez.

Panel: http://127.0.0.1:8789/ — yalnız bu bilgisayardan erişilebilir. QR orada görünür,
günlüklere veya GitHub'a yazılmaz. Eşleşen hedef yalnız KPSS Tercihi kanalıdır.

Beş dakikada bir botun GitHub yayınlarını ve `sosyal/gecmis.json` dosyasını okur.
Önizleme sürümlerini paylaşmaz: yayın zamanının geçmişle tam eşleşmesi gerekir.
Başlangıçtan önceki içerikler atlanır. `node src/bot.js --ilk-paylasim`, son 24 saatten
yalnız en son sosyal paylaşımı bir kez göndererek kurulumun doğrulanmasını sağlar.
Kapak görseli ve açıklama kullanılır; sitedeki başvuru bağlantısı metne eklenir.

Gönderimden önce kalıcı `belirsiz` kaydı yazılır. WhatsApp cevabı alınamazsa aynı içerik
otomatik tekrar gönderilmez; kanalda görülüp görülmediği elle kontrol edilmelidir.
`durum.json` kaybolursa eski dosyayı geri yüklemeden geçmişi sıfırlama.

WhatsApp Web değişiklikleri bağlantıyı bozabilir; oturum iptal edilirse panelden tekrar
QR okutulur. Kurulan bağımlılıklar npm kilit dosyasında sabittir. Üst paketlerde bildirilen
güvenlik açıklarının bir bölümü tarayıcı indirme/FTP/arşiv kodlarıyla ilgilidir; bu bot
tarayıcı indirmez, mevcut Brave'i kullanır ve RemoteAuth/arşiv açma kullanmaz.

Test: `npm test`. Durdurma: Görev Zamanlayıcı'dan ilgili görevi durdur/devre dışı bırak. Alt bot süreci en geç 15 saniye içinde kapanır.
