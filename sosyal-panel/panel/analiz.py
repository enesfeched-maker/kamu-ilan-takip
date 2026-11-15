"""Türetilmiş göstergeler ve kırılımlar.

Puan: paylaşımın ana ölçütü (izlenme; yoksa erişim) / aynı platformdaki olgun paylaşımların medyanı.
1,0 = platformun olağan paylaşımı; 2,0 = iki katı. İlk 48 saatteki paylaşımlar "olgunlaşıyor" sayılır,
taban hesabına girmez ve en iyi/en kötü listelerine alınmaz (sayılar henüz oturmadı)."""
import bisect
import statistics
from datetime import datetime, timedelta, timezone

OLGUNLUK = timedelta(hours=48)
TR = timezone(timedelta(hours=3))
GUNLER = ('Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz')
KIRILIMLAR = {'sablon': 'Şablon', 'bicim': 'Biçim / kart tasarımı', 'vakit': 'Vakit', 'tur': 'Konu türü',
              'palet': 'Renk paleti', 'muzik': 'Müzik', 'platform': 'Platform'}
ETKILESIM = ('likes', 'comments', 'shares', 'saved', 'forwards', 'reactions')


def ana_deger(son):
    if not son:
        return None
    return son.get('views') if son.get('views') is not None else son.get('reach')


def zenginlestir(gonderiler, simdi=None):
    """Her gönderiye: deger, puan, olgun, etkilesim_orani, degisim_24s, yerel saat/gün ekler."""
    simdi = simdi or datetime.now(timezone.utc)
    tabanlar = {}
    for g in gonderiler:
        g['deger'] = ana_deger(g.get('son'))
        yayin = _zaman(g.get('yayin'))
        g['olgun'] = bool(yayin and simdi - yayin >= OLGUNLUK)
        if yayin:
            yerel = yayin.astimezone(TR)
            g['saat'], g['gun'] = yerel.hour, yerel.weekday()
        else:
            g['saat'] = g['gun'] = None
        son = g.get('son') or {}
        toplam = sum(son.get(o) or 0 for o in ETKILESIM)
        g['etkilesim'] = toplam if any(son.get(o) is not None for o in ETKILESIM) else None
        g['etkilesim_orani'] = round(toplam / g['deger'], 4) if g['deger'] and g['etkilesim'] is not None else None
        onceki = g.get('onceki') or {}
        g['degisim_24s'] = (g['deger'] - onceki['views']) if (g['deger'] is not None and onceki.get('views') is not None) else None
    for platform in {g['platform'] for g in gonderiler}:
        degerler = [g['deger'] for g in gonderiler if g['platform'] == platform and g['olgun'] and g['deger'] is not None]
        if len(degerler) < 3:
            degerler = [g['deger'] for g in gonderiler if g['platform'] == platform and g['deger'] is not None]
        tabanlar[platform] = statistics.median(degerler) if degerler else None
    olgunlar = {}
    for g in gonderiler:
        if g['olgun'] and g['deger'] is not None:
            olgunlar.setdefault(g['platform'], []).append((_zaman(g['yayin']), g['deger']))
    for g in gonderiler:
        g['taban'] = donem_tabani(olgunlar.get(g['platform'], []), _zaman(g.get('yayin'))) or tabanlar.get(g['platform'])
        g['puan'] = round(g['deger'] / g['taban'], 2) if (g['taban'] and g['deger'] is not None) else None
    return gonderiler


def donem_tabani(olgunlar, yayin, once=12, sonra=8, en_az=5):
    """Kanal büyüdükçe izlenme tabanı da yükselir; bu yüzden karşılaştırma aynı dönemin olgun paylaşımlarıyla
    yapılır: yayın sırasına göre en yakın 12 önceki ve 8 sonraki paylaşım (zaman penceresi yerine adet: bir günde
    yüzlerce eski ilanın topluca gönderildiği dönemler tabanı bozmasın). Yeterli örnek yoksa None."""
    if not yayin:
        return None
    sirali = sorted((z, d) for z, d in olgunlar if z)
    i = bisect.bisect_left([z for z, _ in sirali], yayin)
    degerler = [d for _, d in sirali[max(0, i - once):i + sonra]]
    return statistics.median(degerler) if len(degerler) >= en_az else None


def _zaman(iso):
    try:
        z = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return z if z.tzinfo else z.replace(tzinfo=timezone.utc)


def _olgun_puanli(gonderiler):
    return [g for g in gonderiler if g['olgun'] and g['puan'] is not None]


def kirilim(gonderiler, alan):
    gruplar = {}
    for g in _olgun_puanli(gonderiler):
        anahtar = g.get(alan) or '—'
        gruplar.setdefault(anahtar, []).append(g)
    satirlar = []
    for ad, liste in gruplar.items():
        oranlar = [g['etkilesim_orani'] for g in liste if g['etkilesim_orani'] is not None]
        satirlar.append({
            'ad': ad, 'adet': len(liste),
            'medyan_puan': round(statistics.median(g['puan'] for g in liste), 2),
            'medyan_deger': statistics.median(g['deger'] for g in liste),
            'toplam_deger': sum(g['deger'] for g in liste),
            'etkilesim_orani': round(statistics.mean(oranlar), 4) if oranlar else None,
            'platformlar': sorted({g['platform'] for g in liste}),
        })
    return sorted(satirlar, key=lambda s: (-s['medyan_puan'], -s['adet']))


def saat_gun(gonderiler):
    """7 gün x 24 saat: paylaşım sayısı ve medyan puan (Türkiye saati)."""
    hucre = {}
    for g in _olgun_puanli(gonderiler):
        if g['saat'] is None:
            continue
        hucre.setdefault((g['gun'], g['saat']), []).append(g['puan'])
    izgara = [[None] * 24 for _ in range(7)]
    for (gun, saat), puanlar in hucre.items():
        izgara[gun][saat] = {'adet': len(puanlar), 'puan': round(statistics.median(puanlar), 2)}
    saatler = []
    for s in range(24):
        p = [x for gun in range(7) for x in hucre.get((gun, s), [])]
        saatler.append({'saat': s, 'adet': len(p), 'puan': round(statistics.median(p), 2) if p else None})
    gunler = []
    for gun in range(7):
        p = [x for s in range(24) for x in hucre.get((gun, s), [])]
        gunler.append({'gun': GUNLER[gun], 'adet': len(p), 'puan': round(statistics.median(p), 2) if p else None})
    return {'izgara': izgara, 'saatler': saatler, 'gunler': gunler, 'gun_adlari': GUNLER}


def ozet(gonderiler, simdi=None):
    simdi = simdi or datetime.now(timezone.utc)
    hafta = simdi - timedelta(days=7)
    sonuc = {}
    for platform in sorted({g['platform'] for g in gonderiler}):
        liste = [g for g in gonderiler if g['platform'] == platform]
        yeni = [g for g in liste if (_zaman(g.get('yayin')) or simdi) >= hafta]
        degerli = [g['deger'] for g in liste if g['deger'] is not None]
        sonuc[platform] = {
            'adet': len(liste), 'olculen': len(degerli), 'son_7_gun_adet': len(yeni),
            'son_7_gun_deger': sum(g['deger'] or 0 for g in yeni),
            'artis_24s': sum(g['degisim_24s'] or 0 for g in liste if g['degisim_24s'] is not None),
            'taban': liste[0]['taban'] if liste else None,
            'toplam_deger': sum(degerli),
        }
    return sonuc


def analiz(gonderiler, platform=None, gun=None, simdi=None):
    simdi = simdi or datetime.now(timezone.utc)
    secili = [g for g in gonderiler if (not platform or g['platform'] == platform)]
    if gun:
        sinir = simdi - timedelta(days=int(gun))
        secili = [g for g in secili if (_zaman(g.get('yayin')) or simdi) >= sinir]
    puanli = sorted(_olgun_puanli(secili), key=lambda g: g['puan'], reverse=True)
    kisa = lambda g: {k: g.get(k) for k in ('id', 'platform', 'baslik', 'yayin', 'puan', 'deger', 'sablon', 'url')}  # noqa: E731
    return {
        'adet': len(secili), 'olgun': len(puanli),
        'kirilimlar': {alan: {'ad': ad, 'satirlar': kirilim(secili, alan)} for alan, ad in KIRILIMLAR.items()},
        'saat_gun': saat_gun(secili),
        'en_iyi': [kisa(g) for g in puanli[:10]],
        'en_kotu': [kisa(g) for g in reversed(puanli[-10:])] if len(puanli) > 10 else [kisa(g) for g in reversed(puanli)],
    }
