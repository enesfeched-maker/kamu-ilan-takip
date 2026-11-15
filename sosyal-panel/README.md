# Sosyal panel

KPSS Tercihi'nin Instagram, YouTube (Shorts), TikTok, Telegram ve Facebook paylaşımlarını tek akışta gösteren,
ölçümleri yerel SQLite'ta zaman serisi olarak saklayan analiz aracı. Yalnız Python standart kütüphanesi kullanır
(Telegram kartlarının Afiş/Bilet ayrımı için Pillow varsa `bot/kart_tasarimlari.py` kuralı kullanılır).

## Açmak

```
cd sosyal-panel
python -m panel
```

Tarayıcıda `http://127.0.0.1:8765/` açılır. Uygulama açıkken saatte bir veri toplar. Veriler
`%LOCALAPPDATA%\KPSSTercihi\sosyal-panel\panel.db` içindedir. Pencere açmadan başlatmak için `pythonw -m panel`;
bot panelinin (sağ alttaki B simgesi) menüsünde ve başlığında da "Sosyal panel" bağlantısı vardır.

- `python -m panel --topla` — yalnız bir kez toplar ve çıkar (Görev Zamanlayıcı için)
- `python -m panel --ornek` — geliştirme: ayrı veritabanında, arayüzde açıkça işaretli ÖRNEK veri

Kısayollar: `j`/`k` sonraki/önceki, `Enter`/`o` platformda aç, `/` ara, `0`–`6` platform, `a` akış/analiz,
`r` yenile, `t` tema, `?` yardım.

## Veri kaynakları

| Platform | Kaynak | Anahtar |
|---|---|---|
| Instagram | `sosyal/gecmis.json` (bot Reels ölçümleri + git geçmişi) ve bulut eseri (Graph API insights: izlenme, erişim, beğeni, yorum, kaydetme, paylaşım, ortalama/toplam izlenme süresi, kalıcı bağlantı) | GitHub sırrı; yerelde gerekmez |
| YouTube | Kanal RSS akışı (son 15 video, izlenme). Bulut eseri YouTube Data API'yi dener (`youtube.readonly` izni gerekir) | İsteğe bağlı |
| Telegram | `t.me/s/kpsstercihi` herkese açık önizleme (mesaj başına izlenme, tepki) | Yok |
| TikTok | Bot geçmişindeki Buffer gönderileri; bağlantılar bulut eserindeki Buffer verisinden | Ölçüm için TikTok Display API bekleniyor |
| Facebook | Bot geçmişi (bağlantı) | Ölçüm için sayfa insights bekleniyor |
| X | — | Hesap bağlı değil |

Bulut eseri: `.github/workflows/sosyal-panel.yml` günde dört kez (Buffer yalnız bir kez) `bot/sosyal_panel_topla.py`
ile `sosyal-panel-veri` eserini üretir; yerel uygulama bunu `gh auth token` ile indirir ve "Yenile" ile işi tetikler.

## Puan

Paylaşımın izlenmesi (yoksa erişimi) / aynı platformda yayın sırasına göre en yakın 20 olgun paylaşımın medyanı.
1,00× = olağan paylaşım. İlk 48 saatteki paylaşımlar "olgunlaşıyor" sayılır; kırılımlara ve en iyi/en zayıf
listelerine girmez.

## Test

```
cd sosyal-panel
python -m unittest discover -s tests
```
