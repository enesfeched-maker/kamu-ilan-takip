"""Geliştirme için ÖRNEK veri. Yalnız `--ornek` ile, ayrı bir veritabanına yazılır; arayüz bunu açıkça işaretler.
Gerçek veritabanına hiçbir zaman karışmaz (her satırda ornek=1)."""
import random
from datetime import datetime, timedelta, timezone

SABLONLAR = ('Sabah son gün', 'Yeni ilan', 'Akşam özeti', 'İlan kartı')


def doldur(depo, adet=120, tohum=7):
    r = random.Random(tohum)
    simdi = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for i in range(adet):
        platform = r.choice(('instagram', 'youtube', 'telegram', 'tiktok'))
        yayin = simdi - timedelta(hours=r.randint(1, 24 * 40))
        sablon = r.choice(SABLONLAR)
        gid = depo.gonderi_yaz(platform, f'ornek-{i}', baslik=f'Örnek paylaşım {i + 1} — {sablon}', yayin=yayin.isoformat(),
                               sablon=sablon, bicim=r.choice(('Afiş', 'Bilet')) if sablon == 'İlan kartı' else 'Reels',
                               url='https://kpsstercihi.com/', ornek=1)
        taban = {'instagram': 180, 'youtube': 400, 'telegram': 480, 'tiktok': 200}[platform] * r.uniform(0.4, 2.2)
        for gun in range(0, min(10, (simdi - yayin).days + 1)):
            oran = 1 - 0.6 ** (gun + 1)
            depo.olcum_yaz(gid, {'views': int(taban * oran), 'likes': int(taban * oran * 0.03),
                                 'shares': int(taban * oran * 0.01)},
                           zaman=(yayin + timedelta(days=gun, hours=1)).isoformat(), kaynak='ornek')
    for k in ('instagram', 'youtube', 'telegram', 'tiktok'):
        depo.durum_yaz(k, 'hazir', 'ÖRNEK veri (geliştirme modu)')
    depo.durum_yaz('x', 'kapali', 'ÖRNEK veri (geliştirme modu)')
    depo.kaydet()
