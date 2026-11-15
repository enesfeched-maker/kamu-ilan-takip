"""Paylaşımın şablonunu (sabah son gün, yeni ilan, akşam özeti, ilan kartı…) ve kart tasarımını (Afiş/Bilet) bulur."""
import re
import sys
from pathlib import Path

TUR_ADI = {
    'son_gun': 'Son gün', 'yeni': 'Yeni ilanlar', 'ilan': 'Yeni ilan', 'ozet': 'Özet', 'kategori': 'Kategori',
    'haber': 'Haber', 'buyuk': 'Büyük alım', 'rehber': 'Rehber',
}
VAKIT_ADI = {'sabah': 'Sabah', 'aksam': 'Akşam', 'ilan': 'Gün içi'}


def gecmis_sablonu(kayit):
    """sosyal/gecmis.json kaydından şablon adı (Reels videoları)."""
    vakit, tur = kayit.get('vakit'), kayit.get('tur')
    if vakit == 'ilan' or tur == 'ilan':
        return 'Yeni ilan'
    if vakit == 'sabah' and tur == 'son_gun':
        return 'Sabah son gün'
    if vakit == 'aksam' and tur in ('yeni', 'ozet'):
        return 'Akşam özeti'
    if vakit == 'aksam' and tur == 'son_gun':
        return 'Akşam son gün'
    return f'Konu: {TUR_ADI.get(tur, tur or "diğer")}'


_KISI = re.compile(r'·\s*\d[\d.]*\s*kişi\s*·')


def metin_sablonu(metin):
    """Telegram/Instagram açıklamasından şablon (gecmis kaydı olmayan paylaşımlar için)."""
    m = (metin or '').strip()
    k = m.replace('İ', 'i').replace('I', 'ı').lower()   # Türkçe küçültme ('İ'.lower() noktalı i üretir)
    if not m:
        return 'Metinsiz'
    if 'iptal' in k[:80]:
        return 'İptal duyurusu'
    if 'düzeltme' in k[:120]:
        return 'Düzeltme'
    if 'günaydın' in k[:30] or 'son başvuru günü' in k[:200] or 'bugün son gün' in k[:200]:
        return 'Sabah son gün'
    if re.search(r'bugün \d+ yeni kamu ilanı', k):
        return 'Akşam özeti'
    if re.search(r'\d+\s*gün kaldı', k[:40]):
        return 'Son gün hatırlatma'
    if _KISI.search(m[:200]) or 'ilan ayrıntıları' in k or 'son başvuru:' in k or '👥' in m[:200]:
        return 'İlan kartı'
    if 'sonuç' in k[:120]:
        return 'Sonuç duyurusu'
    return 'Diğer'


def baslik(metin, uzunluk=110):
    satir = next((s.strip() for s in (metin or '').splitlines() if s.strip()), '')
    satir = re.sub(r'\s+', ' ', satir)
    return satir if len(satir) <= uzunluk else satir[:uzunluk - 1].rstrip() + '…'


class KartTasarimi:
    """Telegram ilan kartının Afiş mi Bilet mi olduğunu, sitenin ilanlar.json verisi ve botun kendi seçim
    kuralıyla (bot/kart_tasarimlari.tasarim_secimi) bulur. Kural yüklenemezse None döner — tahmin yapılmaz."""

    def __init__(self, ilanlar_json, bot_klasoru=None):
        self.mesaj_ilan = {}
        self.ilanlar = {}
        if ilanlar_json:
            for ilan_id, mesaj_id in (ilanlar_json.get('telegram_mesajlari') or {}).items():
                self.mesaj_ilan[int(mesaj_id)] = ilan_id
            self.ilanlar = {i.get('id'): i for i in ilanlar_json.get('ilanlar') or []}
        self.secim = None
        bot = Path(bot_klasoru or Path(__file__).resolve().parents[2] / 'bot')
        try:
            if str(bot) not in sys.path:
                sys.path.insert(0, str(bot))
            from kart_tasarimlari import tasarim_secimi  # noqa: PLC0415 — Pillow gerektirir
            self.secim = tasarim_secimi
        except Exception:
            self.secim = None

    def tasarim(self, mesaj_id):
        ilan = self.ilanlar.get(self.mesaj_ilan.get(int(mesaj_id)))
        if not ilan or not self.secim:
            return None
        try:
            return {'afis': 'Afiş', 'bilet': 'Bilet'}.get(self.secim(ilan))
        except Exception:
            return None
