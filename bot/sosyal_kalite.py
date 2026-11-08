"""Instagram/YouTube metinlerinin son kontrolü (instagram-agent-skill ve youtube-agent-skill kurallarının Türkçeye uyan kısmı).

Skill'lerin Türkçe metinde geçerli kuralları: görünmez karakter yok, ilk satır akışta kesilmez (125 karakter).
Kelime listeleri İngilizce olduğu için burada uygulanmaz."""
import re

AKIS_SINIRI = 125
_GORUNMEZ = re.compile('[­​-‍⁠-⁤﻿\U000e0000-\U000e007f]')
_BOSLUK = re.compile('[   ]')
_CUMLE_SONU = re.compile(r'(?<=[.!?:])\s+')


def temizle(metin):
    return _BOSLUK.sub(' ', _GORUNMEZ.sub('', metin or ''))


def ilk_satiri_bol(metin):
    """Akışta görünen ilk satır 125 karakteri aşıyorsa sınırın içindeki ilk cümle sonundan satır atlatır; cümle yoksa dokunmaz."""
    ilk, ayrac, kalan = metin.partition('\n')
    if len(ilk) <= AKIS_SINIRI:
        return metin
    kesimler = [m.start() for m in _CUMLE_SONU.finditer(ilk) if m.start() <= AKIS_SINIRI]
    if not kesimler:
        return metin
    n = kesimler[-1]
    return ilk[:n] + '\n' + ilk[n:].strip() + ayrac + kalan


def aciklama_duzelt(metin):
    return ilk_satiri_bol(temizle(metin))
