# Telegram yayın düzeni

Yeni ilanlar kuruma ve ilana özel bilgi kartı, kısa açıklama ve iki bağlantı düğmesiyle paylaşılır. Görselde resmi kaynaktan alınan kurum, kadro/kontenjan, yer ve son başvuru tarihi bulunur. Kurum logosu yerine bağımsız bir çizim kullanılır. Bilinmeyen bilgiler tahmin edilmez; koşulların tamamı resmi başvuru bağlantısındadır.

Her ilan için son üç takvim gününde bir kez hatırlatma yapılır. Tarama gecikirse kalan iki gün, yarın veya bugün etiketiyle gönderilir. Başvuru saati geçmiş ilanlar gönderilmez. İlk duyurusu zaten bu dönemde yapılan ilana ayrıca ikinci mesaj gönderilmez. Son tarih değişirse yeni son tarihe göre bir hatırlatma yapılabilir.

Başarıyla gönderilen hatırlatmalar `docs/ilanlar.json` dosyasının `telegram_hatirlatilan` alanında saklanır. Bu alanı ve diğer gönderim geçmişlerini silmeyin. İlan ve hatırlatmalar aynı çalıştırma başına mesaj sınırını paylaşır. Başarısız gönderimler sonraki taramada yeniden denenir. İlk sessiz kurulumda mevcut ilanlara hatırlatma gönderilmez.

Görseller Pillow 11.3.0 ile üretilir. Windows/macOS üzerinde Arial, Linux üzerinde DejaVu Sans gerekir. GitHub Actions bağımlılığı kurar. Yerel kullanım öncesi `python -m pip install Pillow==11.3.0` çalıştırın.

Resmi ayrıntıların güncelliği gönderimden önce kontrol edilir. Resmi servise erişilemediğinde eski bilgiyle mesaj gönderilmez; gönderim ertelenir. Bu nedenle erişim sorunları hatırlatmaların gecikmesine yol açabilir.

Önceki uzun mesajlar değiştirilmez; yeni duyuru ve hatırlatmalar yeni düzeni kullanır.
