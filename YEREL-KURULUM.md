# Yerel kaynak takibi

Bilgisayar açık ve Windows oturumu açılmışken `Kamu Ilan Takip - Yerel Kaynaklar` görevi 30 dakikada bir çalışır. Görev `C:\Users\Feched\Desktop\kamu-ilan\tarayici` klasöründeki ayrı kopyadan `bot/yerel_baslat.py` ile çalışır: her çalışmada önce kodu GitHub `main` ile eşitler (`git fetch` + `reset --hard`), sonra taramayı başlatır. Bu klasörde geliştirme yapılmaz. Açılışta da tetiklenir. Aynı anda iki kopya çalışmaz. Uyku/kapalı durumda tarama yapılmaz; sonraki uygun tetiklemede kontrol edilir.

Program yalnızca bu projedeki `docs/yerel-kaynaklar.json` dosyasını günceller. Telegram anahtarı bilgisayara alınmaz. Gönderim geçmişi yerel program tarafından değiştirilmez. GitHub Actions önce ilanları/siteyi yayımlar, ardından Telegram'da ilgili site ayrıntı bağlantısıyla gönderir.

## Bir defalık bağlantı

GitHub hesabında **fine-grained personal access token** oluşturun: kaynak sahibi `enesfeched-maker`, yalnızca `kamu-ilan-takip` deposu, repository permissions **Contents: Read and write** (Metadata: Read otomatik). Başka izin gerekmiyor. 90 gün gibi süreli bir anahtar kullanın; süresi dolduğunda yenilenmesi gerekir.

`.local-runtime/Scripts/pythonw.exe bot/yerel_kurulum.py` güvenli bağlantı penceresini açar. Anahtarı yalnızca bu pencereye yapıştırın; sohbete veya dosyaya düz metin olarak koymayın. Kurulum ilk veri aktarımını doğrular, Windows kullanıcısına bağlı DPAPI ile şifreler ve görevi etkinleştirir.

`local-data` ve `.local-runtime` Git dışında tutulur. Anahtar `local-data/github.dpapi` içinde şifrelidir. Aynı Windows hesabıyla çalışan yazılımlar tarafından çözülebilir; başka hesaba taşınarak çalışmaz.

## İşleyiş ve kontrol

- SBB listesi yerelden okunur; kurum, kadro ve doğrulanabilen tarihler aktarılır.
- Kariyer Kapısı ayrıntıları da yerelden doğrulanarak GitHub'daki erişim sorunlarında kullanılır.
- Yerel SBB kontrolü 90 dakikadan eskiyse taze sayılmaz; bulut taraması yeniden denenir. Eski bilgiler yeni kontrol yapılmış gibi işaretlenmez.
- Kurum logoları resmî Kariyer Kapısı/e-Devlet kayıtlarıyla eşleştirilir. Doğrulanmış logo bulunmazsa başka kurum logosu uydurulmaz.
- `local-data/tarama.log` çalışma günlüğüdür. `local-data/durum.json` son başarılı aktarımı gösterir. Anahtarlar günlüklere yazılmaz.
- Windows Görev Zamanlayıcı'dan görev durdurulabilir/devre dışı bırakılabilir. GitHub anahtarı hesap ayarlarından iptal edilebilir.

Programın önizlemesi: `.local-runtime/Scripts/python.exe bot/yerel_tara.py --preview`. Bu seçenek GitHub'a veya Telegram'a yazmaz.
