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


# (soru, tür, ilan sayısı) — uydurma örnek sorular; gerçek kayıt değildir.
ORNEK_SORULAR = (
    ('Zabıta ilanı var mı?', 'ilan', 3), ('zabita ilani varmi', 'ilan', 3), ('Ankara zabıta alımı', 'ilan', 0),
    ('İzmir\'de büro personeli ilanı', 'ilan', 2), ('Lise mezunu alan belediyeler', 'ilan', 4),
    ('Önlisans 70 puanla nereye girerim?', 'puan', 0), ('KPSS 75 puan yeter mi', 'puan', 0),
    ('Hemşire alımı ne zaman?', 'ilan', 1), ('Van itfaiye eri ilanı', 'ilan', 0), ('Trabzon itfaiye alımı var mı', 'ilan', 0),
    ('Erzurum güvenlik görevlisi', 'ilan', 0), ('Başvuru nasıl yapılır?', 'sss', 0), ('Mülakat ne zaman açıklanır', 'bilinmiyor', 0),
    ('Mülakat sonuçları ne zaman açıklanır?', 'bilinmiyor', 0), ('mülakat sonucu ne zaman', 'bilinmiyor', 0),
    ('Askerlik tecilli olan başvurabilir mi?', 'bilinmiyor', 0), ('Engelli kadrosu var mı', 'bilinmiyor', 0),
    ('Yaş sınırı kaç?', 'bilinmiyor', 0), ('Yaş sınırı var mı', 'bilinmiyor', 0), ('Sözleşmeli personel maaşı ne kadar', 'bilinmiyor', 0),
    ('Merhaba', 'selam', 0), ('Teşekkürler', 'tesekkur', 0), ('Sen bot musun?', 'kimlik', 0),
    ('Bursa şoför alımı', 'ilan', 0), ('Konya veri hazırlama ve kontrol işletmeni', 'ilan', 1),
    ('Mühendis ilanı İstanbul', 'ilan', 2), ('<script>alert(1)</script> zabıta', 'ilan', 3),
    ('Diyarbakır temizlik personeli', 'ilan', 0), ('Ebe alımı var mı', 'ilan', 0), ('Psikolog kadrosu açıldı mı?', 'ilan', 0),
)


def asistan_doldur(depo, adet=260, tohum=11):
    """Örnek asistan kayıtları (site + Instagram); ornek=1 olarak işaretli."""
    r = random.Random(tohum)
    simdi = datetime.now(timezone.utc).replace(microsecond=0)
    satirlar = []
    for i in range(1, adet + 1):
        soru, tur, ilan = r.choice(ORNEK_SORULAR)
        kanal = 'instagram' if r.random() < 0.3 else 'site'
        zaman = simdi - timedelta(minutes=r.randint(5, 60 * 24 * 40) * (1 if r.random() < 0.6 else 0.4))
        metin = {'ilan': f'{ilan} açık ilan buldum.' if ilan else 'Şu an bu aramaya uyan açık ilan yok.',
                 'puan': 'Puanınla başvurabileceğin ilanlar için Nereye aracına bak.',
                 'bilinmiyor': 'Bunu bilmiyorum; sitede ilgili rehberlere bakabilirsin.',
                 'sss': 'Başvurular kurumun kendi sayfasından yapılır.', 'selam': 'Merhaba! Ne aramıştın?',
                 'tesekkur': 'Rica ederim.', 'kimlik': 'Ben sitenin otomatik asistanıyım.'}[tur]
        satir = {'id': i, 'zaman': zaman.isoformat(), 'kanal': kanal, 'soru': soru, 'tur': tur, 'metin': metin,
                 'ilan_sayisi': ilan if tur == 'ilan' else 0,
                 'baglantilar': ['https://kpsstercihi.com/meslek/zabita-memuru/'] if ilan else ['https://kpsstercihi.com/sss/'],
                 'sayfa': r.choice(['/', '/ilanlar/', '/meslek/zabita-memuru/', '/nereye/']) if kanal == 'site' else None,
                 'geri': r.choice([1, 1, 1, -1, None, None]) if kanal == 'site' else None, 'durum': None, 'meta': None}
        if kanal == 'instagram':
            satir['durum'] = r.choice(['yanitlandi', 'yanitlandi', 'yanitlandi', 'atlandi', 'hata', None])
            satir['meta'] = {'kullanici': f'ornek_kullanici_{r.randint(1, 40)}', 'medya': f'ornek-medya-{r.randint(1, 8)}',
                             'yorum_id': f'ornek-yorum-{i}'}
            if satir['durum'] == 'yanitlandi':
                satir['meta']['gonderilen'] = metin + ' Ayrıntılar kpsstercihi.com\'da.'
        satirlar.append(satir)
    depo.asistan_yaz(satirlar, ornek=1)
    depo.durum_yaz('asistan', 'hazir', 'ÖRNEK veri (geliştirme modu)', adet)
