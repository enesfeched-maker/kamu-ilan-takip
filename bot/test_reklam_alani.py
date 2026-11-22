import unittest
from datetime import datetime
from unittest.mock import patch

import site_uret
import statik_icerik
from site_uret import TR, reklam_alani

SIMDI = datetime(2026, 10, 5, 19, 0, tzinfo=TR)
ILAN = {'id': 'sbb-' + 'a' * 24, 'kaynak_turu': 'sbb', 'baslik': 'GELİR İDARESİ BAŞKANLIĞI - 860 GELİR UZMAN YARDIMCISI ALACAK',
        'kurum': 'GELİR İDARESİ BAŞKANLIĞI', 'kadro': '860 GELİR UZMAN YARDIMCISI ALACAK', 'link': 'https://kamuilan.sbb.gov.tr/',
        'son_tarih': '2026-10-22', 'donem': '( 20 Ekim - 22 Ekim)', 'ilk_gorulme': '2026-10-01T10:00:00+03:00'}
BENZER = {'id': 'sbb-' + 'b' * 24, 'key': 'b' * 8, 'baslik': 'Başka ilan', 'kurum': 'Kurum', 'kadro': '3 UZMAN', 'son_tarih': '2026-10-25'}


def sayfa(item=ILAN, benzer=None):
    import liste_verisi as lv
    return site_uret.detail_page(lv.tamamla(dict(item)), benzer=benzer, simdi=SIMDI)[1]


class ReklamAlaniTests(unittest.TestCase):
    def test_bos_slot_bos_doner(self):
        self.assertEqual(reklam_alani('', 'x'), '')
        with patch.object(site_uret, 'REKLAM_SLOT_SAYFA', ''):
            self.assertNotIn('class="rk"', sayfa())

    def test_dolu_slot_ins_ve_push(self):
        h = reklam_alani('123', 'kadro-alti')
        self.assertIn('class="adsbygoogle"', h)
        self.assertIn('data-ad-slot="123"', h)
        self.assertIn('data-ad-client="ca-pub-8335827974832277"', h)
        self.assertIn('.push({})', h)
        self.assertEqual(h.count('push('), 1)

    def test_ilan_sayfasi_konumlari(self):
        with patch.object(site_uret, 'REKLAM_SLOT_SAYFA', '123'):
            h = sayfa(benzer=[BENZER])
        self.assertEqual(h.count('class="rk"'), 2)
        cta, r1, tart, r2, benzer = (h.find(x) for x in ('class="d-cta"', 'data-rk="kadro-alti"', 'id="tartisma"', 'data-rk="benzer-ustu"', 'class="benzer"'))
        self.assertTrue(0 < cta < r1 < tart < r2 < benzer)
        self.assertGreater(r1, h.find('Kadro'))
        self.assertLess(h.find('class="dh'), cta)

    def test_noindex_sayfada_alan_yok(self):
        kapali = dict(ILAN, iptal_edildi=True)
        with patch.object(site_uret, 'REKLAM_SLOT_SAYFA', '123'):
            h = sayfa(kapali, [BENZER])
        self.assertIn('noindex', h)
        self.assertNotIn('class="rk"', h)
        self.assertNotIn('adsbygoogle', h)

    def test_ana_sayfa_akis_slotu(self):
        metin = '<div class="zaman" id="cards"></div><div class="bos-kutu" id="empty"'
        for slot, beklenen in (('55', ' data-rk-akis="55"'), ('', '')):
            with patch.object(site_uret, 'REKLAM_SLOT_AKIS', slot):
                yeni = statik_icerik.anasayfa_html('<small id="result-count">x</small><p class="liste-ozet" id="filter-summary">a</p><p class="manset-bos">b</p>' + metin, [], '', 0)
            self.assertIn(f'id="cards"{beklenen}>', yeni)


if __name__ == '__main__':
    unittest.main()
