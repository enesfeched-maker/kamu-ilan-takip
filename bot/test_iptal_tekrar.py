import unittest
from datetime import date

import ilan_bot

BUGUN = date(2026, 10, 21)


def kayit(kimlik, **ek):
    return dict({'id': kimlik, 'kurum': 'Muş Elmakaya Belediyesi', 'baslik': 'Muş Elmakaya Belediyesi Memur Alım İlanı',
                 'kadro': '1 Memur', 'son_tarih': '2026-10-30', 'ilk_gorulme': '2026-09-26T20:25:00+03:00',
                 'link': 'https://kamuilan.sbb.gov.tr/'}, **ek)


CSB = kayit('csb-1', kurum='', baslik='MUŞ İLİ ELMAKAYA BELEDİYESİNİN MEMUR ALIMI İPTAL İLANI', kadro='', son_tarih=None,
            duyuru_turu='İptal duyurusu', ilk_gorulme='2026-10-21T11:21:00+03:00')
SBB = kayit('sbb-2', kurum='ELMAKAYA BELEDİYE BAŞKANLIĞI', baslik='ELMAKAYA BELEDİYE BAŞKANLIĞI - MUŞ İLİ ELMAKAYA BELEDİYESİNİN MEMUR ALIMI İPTAL İLANI',
            kadro='', duyuru_turu='İptal duyurusu', ilk_gorulme='2026-10-21T16:13:00+03:00')


class IptalIkiKaynak(unittest.TestCase):
    def test_ayni_iptal_iki_kaynaktan_gelse_de_bir_kez_gider(self):
        orijinal = kayit('o1')
        ilanlar = [orijinal, CSB, SBB]
        mesajlar, yanitlar = {'o1': 50}, {}
        k1 = ilan_bot.duyuru_karari(CSB, ilanlar, mesajlar, yanitlar, BUGUN)
        self.assertEqual(k1['islem'], 'gonder')
        ilan_bot.yanit_kaydet(yanitlar, k1, CSB, BUGUN.isoformat())
        k2 = ilan_bot.duyuru_karari(SBB, ilanlar, mesajlar, yanitlar, BUGUN)
        self.assertEqual(k2['islem'], 'sessiz')

    def test_farkli_iptal_engellenmez(self):
        orijinal = kayit('o1')
        muhendis = kayit('sbb-3', kurum='ELMAKAYA BELEDİYE BAŞKANLIĞI', baslik='ELMAKAYA BELEDİYE BAŞKANLIĞI - MUŞ İLİ ELMAKAYA BELEDİYESİNİN MÜHENDİS ALIMI İPTAL İLANI',
                         kadro='', duyuru_turu='İptal duyurusu')
        ilanlar = [orijinal, kayit('o2', kadro='1 Mühendis', baslik='Muş Elmakaya Belediyesi Mühendis Alım İlanı'), CSB, muhendis]
        yanitlar = {}
        k1 = ilan_bot.duyuru_karari(CSB, ilanlar, {'o1': 50, 'o2': 51}, yanitlar, BUGUN)
        ilan_bot.yanit_kaydet(yanitlar, k1, CSB, BUGUN.isoformat())
        k2 = ilan_bot.duyuru_karari(muhendis, ilanlar, {'o1': 50, 'o2': 51}, yanitlar, BUGUN)
        self.assertEqual(k2['islem'], 'gonder')   # başka kadronun iptali ayrıca bildirilir


if __name__ == '__main__':
    unittest.main()
