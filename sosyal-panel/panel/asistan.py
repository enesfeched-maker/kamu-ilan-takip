"""Site asistanı ve Instagram yorumlarına verilen cevapların kayıtları (bildirim-botu /asistan/kayitlar).

Anahtar: %LOCALAPPDATA%\\KPSSTercihi\\sosyal-panel\\asistan-anahtar.txt (tek satır, X-Asistan-Anahtar başlığı).
Dosya yoksa toplama sessizce atlanır; arayüz nereye konacağını gösterir. Anahtar yazdırılmaz, günlüğe düşmez.

Satırlar sonradan değişebilir (ziyaretçinin "işe yaradı mı" cevabı, Instagram yanıt durumu); bu yüzden her
çalışmada yeni kayıtların yanında son 48 saatin kayıtları da yeniden çekilip güncellenir."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import kaynaklar as k

TABAN = 'https://bildirim.kpsstercihi.com'
BILGI = 'https://kpsstercihi.com/asistan/bilgi.json'
SAYFA = 1000
EN_COK_SAYFA = 500          # sonsuz döngü kalkanı (500 x 1000 satır)
GERI_PENCERE = timedelta(hours=48)


def anahtar_yolu():
    taban = os.environ.get('LOCALAPPDATA') or str(Path.home() / '.local' / 'share')
    return Path(taban) / 'KPSSTercihi' / 'sosyal-panel' / 'asistan-anahtar.txt'


def anahtar_oku(yol=None):
    """Anahtar dosyasının ilk dolu satırı; dosya yoksa ya da boşsa None."""
    try:
        for satir in Path(yol or anahtar_yolu()).read_text(encoding='utf-8-sig').splitlines():
            if satir.strip():
                return satir.strip()
    except OSError:
        return None
    return None


def kayitlari_cek(depo, anahtar, getir_json=None, simdi=None, taban=TABAN):
    """Yeni kayıtları ve son 48 saati sayfa sayfa çekip depoya yazar. (yeni, degisen, istek) döner."""
    getir_json = getir_json or k.getir_json
    simdi = simdi or datetime.now(timezone.utc)
    sonra = depo.asistan_son_id()
    ilk = depo.asistan_ilk_id_sonra((simdi - GERI_PENCERE).isoformat())
    if ilk is not None:
        sonra = min(sonra, ilk - 1)
    yeni = degisen = istek = 0
    while istek < EN_COK_SAYFA:
        istek += 1
        veri = getir_json(f'{taban}/asistan/kayitlar?sonra={int(sonra)}&limit={SAYFA}',
                          basliklar={'X-Asistan-Anahtar': anahtar, 'Accept': 'application/json'}, zaman_asimi=40)
        satirlar = (veri or {}).get('kayitlar') or []
        if not satirlar:
            break
        y, d = depo.asistan_yaz(satirlar)
        yeni, degisen = yeni + y, degisen + d
        en_buyuk = max(int(s.get('id') or 0) for s in satirlar)
        if en_buyuk <= sonra:      # uç ilerlemiyorsa dur
            break
        sonra = en_buyuk
    return yeni, degisen, istek


def meslekleri_guncelle(depo, getir_json=None, simdi=None):
    """Sitenin meslek listesini (asistanın kullandığı) günde bir kez önbelleğe alır; hata sessizce yutulur."""
    getir_json = getir_json or k.getir_json
    simdi = simdi or datetime.now(timezone.utc)
    eski = depo.ayar('asistan_meslekler') or {}
    try:
        if eski.get('zaman') and simdi - datetime.fromisoformat(eski['zaman']) < timedelta(hours=20):
            return False
    except (TypeError, ValueError):
        pass
    try:
        veri = getir_json(BILGI, zaman_asimi=30)
    except k.KaynakHatasi:
        return False
    liste = [{'ad': m.get('ad'), 'kelimeler': [str(x) for x in (m.get('kelimeler') or []) if x]}
             for m in (veri or {}).get('meslekler') or [] if isinstance(m, dict) and m.get('ad')]
    if liste:
        depo.ayar_yaz('asistan_meslekler', {'zaman': simdi.isoformat(timespec='seconds'), 'liste': liste})
    return bool(liste)


def topla(depo, anahtar=None, getir_json=None, simdi=None, yol=None):
    """Toplama adımı: durumu 'asistan' kaynağı olarak yazar. Anahtar yoksa 'bekliyor' (hata değil)."""
    anahtar = anahtar if anahtar is not None else anahtar_oku(yol)
    if not anahtar:
        depo.durum_yaz('asistan', 'bekliyor', f'Anahtar dosyası yok: {yol or anahtar_yolu()}')
        return None
    yeni, degisen, _ = kayitlari_cek(depo, anahtar, getir_json=getir_json, simdi=simdi)
    meslekleri_guncelle(depo, getir_json=getir_json, simdi=simdi)
    toplam = depo.db.execute('SELECT COUNT(*) n FROM asistan_kayit').fetchone()['n']
    depo.durum_yaz('asistan', 'hazir', f'{toplam} kayıt saklı (bu çalışmada {yeni} yeni, {degisen} güncellendi)', toplam)
    return yeni, degisen
