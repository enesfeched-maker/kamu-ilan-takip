"""Instagram Reels istatistiklerini okur, hangi konu türü ve müziğin daha iyi gittiğini hesaplar.

  sonuc   yayından sonra: platform kimliklerini (Instagram medya, TikTok yayın) son geçmiş kaydına yazar
  topla   günde bir: 2–30 günlük paylaşımların izlenme/beğeni/kaydetme/paylaşım sayılarını çeker,
          sosyal/istatistik.json'a tür ve müzik ağırlıklarını yazar (sosyal_motor konu ve müzik seçerken kullanır)

Anahtar: IG_KULLANICI_ID, IG_ERISIM_ANAHTARI (instagram_business_manage_insights izni gerekir). Anahtar yazdırılmaz.
Kullanım: python bot/sosyal_istatistik.py sonuc sosyal-cikti | python bot/sosyal_istatistik.py topla"""
import json
import math
import statistics
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from sosyal_motor import GECMIS_YOLU, TR, _zaman, gecmis_oku, istatistik_oku  # noqa: F401
from sosyal_yayinla import IG_SURUM, YayinHatasi, _env, _istek

ISTATISTIK_YOLU = GECMIS_YOLU.parent / 'istatistik.json'
OLCUTLER = ('views', 'reach', 'likes', 'comments', 'saved', 'shares')
YEDEK_OLCUTLER = ('reach', 'likes', 'comments', 'saved', 'shares')
EN_GENC, EN_YASLI = timedelta(days=2), timedelta(days=30)  # ilk 2 gün sayılar oturmaz; 30 günden sonra değişmez
EN_AZ_OLCUM = 6     # bu kadar ölçülmüş paylaşım olmadan ağırlık verilmez
EN_BUYUK_ETKI = 20  # konu puanına en çok ±20 (son türün tekrar cezası 15, trend bonusu 30)


def _yaz(yol, veri):
    Path(yol).write_text(json.dumps(veri, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def sonuc_isle(klasor, gecmis_yolu=GECMIS_YOLU):
    """Yayın sonucundaki kimlikleri aynı paylaşımın geçmiş kaydına ekler (eşleşme: paylasim.json zamanı)."""
    klasor = Path(klasor)
    try:
        sonuc = json.loads((klasor / 'sonuc.json').read_text(encoding='utf-8'))
        zaman = json.loads((klasor / 'paylasim.json').read_text(encoding='utf-8'))['zaman']
    except (OSError, ValueError, KeyError):
        return False
    gecmis = gecmis_oku(gecmis_yolu)
    kayit = next((g for g in reversed(gecmis) if g.get('zaman') == zaman), None)
    if kayit is None:
        return False
    for ad, alan in (('instagram', 'ig_id'), ('tiktok', 'tt_id')):
        kimlik = (sonuc.get(ad) or {}).get('id')
        if kimlik:
            kayit[alan] = kimlik
    _yaz(gecmis_yolu, gecmis)
    return True


def _medya_listesi(ig_id, anahtar):
    yanit = _istek(f'https://graph.instagram.com/{IG_SURUM}/{ig_id}/media?fields=id,timestamp,media_type&limit=50'
                   f'&access_token={urllib.parse.quote(anahtar)}')
    return yanit.get('data') or []


def kimlik_eslestir(gecmis, medyalar):
    """Kimliği kaydedilmemiş eski paylaşımlar: üretimden sonraki 45 dk içinde yayınlanan Reels eşleşir."""
    kullanilan = {g.get('ig_id') for g in gecmis}
    for g in gecmis:
        z = _zaman(g.get('zaman'))
        if g.get('ig_id') or not z:
            continue
        for m in medyalar:
            try:
                mz = datetime.strptime(m.get('timestamp', ''), '%Y-%m-%dT%H:%M:%S%z')
            except ValueError:
                continue
            if m.get('id') not in kullanilan and timedelta(0) <= mz - z <= timedelta(minutes=45):
                g['ig_id'] = m['id']
                kullanilan.add(m['id'])
                break
    return gecmis


def olcum_al(medya_id, anahtar):
    son_hata = None
    for olcutler in (OLCUTLER, YEDEK_OLCUTLER):
        try:
            yanit = _istek(f'https://graph.instagram.com/{IG_SURUM}/{medya_id}/insights?metric={",".join(olcutler)}'
                           f'&access_token={urllib.parse.quote(anahtar)}')
        except YayinHatasi as hata:
            son_hata = hata
            continue
        return {m['name']: (m.get('values') or [{}])[0].get('value', 0) for m in yanit.get('data') or [] if m.get('name')}
    raise son_hata


def skor(olcum):
    """Yeni kitleye ulaşma (izlenme/erişim) esas; paylaşma ve kaydetme algoritmanın en güçlü sinyalleri."""
    if not olcum:
        return None
    goruntu = olcum.get('views') or olcum.get('reach') or 0
    return (goruntu + 2 * (olcum.get('likes') or 0) + 5 * (olcum.get('comments') or 0)
            + 10 * (olcum.get('saved') or 0) + 15 * (olcum.get('shares') or 0))


def agirliklar(gecmis):
    """Her tür/müzik için: grubun medyan skoru / genel medyan. Az örnekli gruplar sıfıra çekilir (n/(n+2))."""
    olculen = [(g, skor(g.get('ig'))) for g in gecmis]
    olculen = [(g, s) for g, s in olculen if s is not None]
    sonuc = {'olculen': len(olculen), 'tur': {}, 'muzik': {}, 'vakit': {}}
    if len(olculen) < EN_AZ_OLCUM:
        return sonuc
    genel = statistics.median(s for _, s in olculen) or 1
    for alan in ('tur', 'muzik', 'vakit'):
        gruplar = {}
        for g, s in olculen:
            if g.get(alan):
                gruplar.setdefault(g[alan], []).append(s)
        for ad, skorlar in gruplar.items():
            oran = max(statistics.median(skorlar), 1) / genel
            etki = EN_BUYUK_ETKI * math.log2(oran) * len(skorlar) / (len(skorlar) + 2)
            sonuc[alan][ad] = round(max(-EN_BUYUK_ETKI, min(EN_BUYUK_ETKI, etki)), 1)
    return sonuc


def topla(simdi=None, ortam=None, gecmis_yolu=GECMIS_YOLU, istatistik_yolu=ISTATISTIK_YOLU):
    ig_id, anahtar = ortam or _env('IG_KULLANICI_ID', 'IG_ERISIM_ANAHTARI') or (None, None)
    if not ig_id:
        print('Instagram anahtarı tanımlı değil; istatistik atlandı.')
        return None
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    gecmis = gecmis_oku(gecmis_yolu)
    try:
        kimlik_eslestir(gecmis, _medya_listesi(ig_id, anahtar))
    except YayinHatasi as hata:
        print(f'Uyarı: Instagram paylaşım listesi alınamadı: {hata}')
    olculen, izinsiz, ust_uste = 0, None, 0
    for g in gecmis:
        z = _zaman(g.get('zaman'))
        if not (g.get('ig_id') and z and EN_GENC <= simdi - z <= EN_YASLI):
            continue
        try:
            g['ig'] = dict(olcum_al(g['ig_id'], anahtar), olcum=simdi.isoformat(timespec='seconds'))
            olculen, ust_uste = olculen + 1, 0
        except YayinHatasi as hata:
            izinsiz, ust_uste = str(hata), ust_uste + 1
            if ust_uste >= 3:  # izin yoksa hepsi aynı hatayı verir
                break
    _yaz(gecmis_yolu, gecmis)
    sonuc = dict(agirliklar(gecmis), guncelleme=simdi.isoformat(timespec='seconds'))
    _yaz(istatistik_yolu, sonuc)
    if izinsiz:
        print(f'Uyarı: Instagram istatistikleri okunamadı (instagram_business_manage_insights izni gerekebilir): {izinsiz}')
    print(f'{olculen} paylaşım ölçüldü; toplam {sonuc["olculen"]} ölçüm. Tür: {sonuc["tur"]} Müzik: {sonuc["muzik"]}')
    return sonuc


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sonuc':
        sonuc_isle(sys.argv[2] if len(sys.argv) > 2 else 'sosyal-cikti')
    else:
        topla()
