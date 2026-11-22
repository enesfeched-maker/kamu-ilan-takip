"""Yayın öncesi tamlık kapısı: bilgisi eksik ilan ne sitede ne Telegram'da görünür.

23 Kasım 2026 kullanıcı: "ilan gelince önce bütün bilgileri tamamlansın sonra sitede ve telegramda yayınlansın; yarım
yamalak ilan istemiyorum." Türk Akreditasyon Kurumu koruma ve güvenlik ilanı Kariyer Kapısı ayrıntısı (son başvuru,
kadro, koşullar) inmeden siteye düşmüş, tarihsiz sayfa "Bu ilanın başvurusu sona erdi" göstermişti.

Kural: duyuru olmayan bir ilan, son başvuru tarihi okunmadan ve (Kariyer Kapısı kaydıysa) resmî ayrıntısı inmeden
yayınlanmaz; süre sınırı yoktur, bilgi tamamlanınca bir sonraki derlemede/taramada kendiliğinden yayına girer.
Bu tarihten önce görülmüş eski kayıtlar etkilenmez (yayındaki sayfaları kaybolmasın)."""

BASLANGIC = '2026-11-23'


def kk_ayrinti_bekliyor(item):
    """Kariyer Kapısı kaydının resmî ayrıntısı (kadrolar, koşullar) henüz inmedi mi?"""
    kimlik = str(item.get('id') or '')
    return kimlik.startswith('https://kariyerkapisi.gov.tr/') and not item.get('kk_detay_surumu') \
        and not item.get('kadro_detay') and not item.get('sartlar')


def eksik(item):
    """Yayına engel eksik bilgi: '' (tamam) ya da kısa neden."""
    if item.get('duyuru_turu') or str(item.get('ilk_gorulme') or '')[:10] < BASLANGIC:
        return ''
    if kk_ayrinti_bekliyor(item):
        return 'Kariyer Kapısı ayrıntısı henüz okunmadı'
    if not item.get('son_tarih'):
        return 'son başvuru tarihi okunmadı'
    return ''
