# İlan okuma talimatı (Claude bulut rutini, 2 saatte bir)

Amaç: KPSS Tercihi sitesinde ve Telegram kanalında yayınlanan kamu personel ilanlarının bilgilerini **resmî belgeden,
doğru** yazmak. Hız değil doğruluk önemli. Belgede açıkça yazmayan hiçbir şeyi yazma, tahmin etme.

## Adımlar

0. Bağımlılıklar: `python -m pip install -q cffi cryptography pypdf beautifulsoup4 Pillow` (pip yerine `python -m pip`:
   bulut ortamında pip başka bir Python'a kuruyor; cffi/cryptography olmadan pypdf açılmıyor).
1. `python bot/yz_claude.py hazirla` — okunacak ilanları `yz-is/gorevler.json` dosyasına yazar. Liste boşsa 4. adıma geç
   (yapılacak iş yok; hiçbir şey gönderme, kısa bir satırla bitir).
2. Her görev için:
   - `metin` varsa o dosyayı oku; `pdf` varsa PDF'i de aç (taranmış belgede yalnız PDF vardır; görüntüden oku).
   - Sonucu görevin `cikti` yoluna aşağıdaki biçimde JSON olarak yaz.
3. `python bot/yz_claude.py kaydet` — çıktıları denetler ve `denetim/yz.json` dosyasına işler. "Atlandı" satırı varsa
   o ilanın JSON'unu düzelt ve komutu yeniden çalıştır.
4. Değişiklik varsa yalnız `denetim/yz.json` dosyasını bu çalışmaya özel YENİ bir dala gönder. Komutları ayrı ayrı
   çalıştır, dal adındaki zamanı bir kez belirleyip hepsinde aynısını kullan (ör. `yz-okuma-20261030-1405`):
   ```
   git checkout -b yz-okuma-YYYYAAGG-SSDD
   git add denetim/yz.json
   git commit -m "Claude ilan okuması"
   git push origin yz-okuma-YYYYAAGG-SSDD
   ```
   Dal yeni olduğu için normal push yeter; `git push -f`, `git reset --hard` ve var olan bir dala gönderme GEREKMEZ, kullanma.
   Push "already exists" ile reddedilirse dal adına saniye ekleyip yeni dal aç. main'e doğrudan gönderme, başka dosya
   değiştirme. `.github/workflows/yz-okuma-al.yml` dalı main'e birleştirip siler.

## Çıktı biçimi (her ilan için bir JSON)

```json
{
  "kadrolar": [
    {"unvan": "Zabıta Memuru — Kadın", "adet": 3, "ogrenim": "lisans", "puan_turu": "P3", "en_dusuk_puan": 60,
     "il": "Şanlıurfa",
     "kosullar": ["Herhangi bir lisans programından mezun olmak.", "En az (B) sınıfı sürücü belgesine sahip olmak."]}
  ],
  "toplam": 9,
  "son_basvuru_tarihi": "2026-12-10",
  "son_basvuru_saati": "17:00",
  "baslangic_tarihi": "2026-12-07",
  "kpss_gerekli": true,
  "iller": ["Şanlıurfa"],
  "ortak_kosullar": ["Sınavın yapıldığı tarihte 30 yaşını doldurmamış olmak.",
                     "Boy: erkeklerde en az 1,67 m, kadınlarda en az 1,60 m; boy-kilo farkı en çok 10 kg."],
  "ozet": "Eyyübiye Belediyesi 9 zabıta memuru alacak. Başvurular 7–10 Aralık 2026'da belediyeye şahsen yapılır.",
  "okunabilirlik": "iyi"
}
```

## Kurallar

- **kadrolar:** belgedeki her kadro/pozisyon satırı bir kayıt. `adet` asil kişi sayısı (yedek sayılmaz). Aynı unvan
  kadın/erkek, öğrenim ya da bölüm farkıyla ayrı satırdaysa unvanı ayırt et ("Zabıta Memuru — Kadın",
  "Mühendis (Makine)"). `ogrenim`: ortaogretim, onlisans, lisans, yuksek_lisans. `puan_turu`: P3, P93, P94 gibi
  (KPSS yoksa null). `en_dusuk_puan`: yazıyorsa sayı, yoksa null. `il`: görev yeri ili (yoksa null).
- **kosullar:** o kadroya ÖZEL şartlar: bölüm/mezuniyet, sertifika, ehliyet, deneyim, cinsiyet, yaş (kadroya özelse).
  Her biri tek kısa cümle, en çok 140 karakter, "…mezun olmak" biçimi. En önemli 5 madde.
- **ortak_kosullar:** tüm kadrolar için geçerli, en çok 5 madde: yaş sınırı, boy-kilo, KPSS yılı/grubu, başvuru yeri ve
  şekli, sınav usulü/tarihi. 657 sayılı Kanun 48. madde genel şartlarını (Türk vatandaşı olmak, kamu hakları, adli sicil,
  askerlik, sağlık), mevzuat numaralarını ve "belirtilmemiş" gibi dolgu maddelerini YAZMA.
- **son_basvuru_tarihi / baslangic_tarihi:** başvuruların bittiği / başladığı gün (YYYY-AA-GG). Sınav, sonuç, belge
  teslim ya da ilan tarihi DEĞİL. Saat yazıyorsa `son_basvuru_saati` (SS:DD).
- **ozet:** en çok 2 cümle, en çok 280 karakter: kim, kaç kişi, kimleri alıyor, başvuru nereden ve hangi tarihler arasında.
- **okunabilirlik:** "iyi", kısmen okunabildiyse "kismi", okunamadıysa "kotu" (o zaman kadrolar boş liste).
- Belge ilanın kendisi değilse (iptal, düzeltme, sonuç duyurusu) ya da akademik kadro ilanıysa (öğretim üyesi,
  araştırma görevlisi) `kadrolar` boş liste ve `okunabilirlik` "kotu" yaz; bot bu ilanları kendi kurallarıyla yönetir.
- `bot_kadro` ve `bot_son_tarih` botun kendi okuması; belge farklı diyorsa belgeye uy.
