import json
import re
import unittest
from datetime import datetime

import indexnow
import yz_gorunurluk as yz

BASE = 'https://kpsstercihi.com/'


class LlmsTest(unittest.TestCase):
    def test_acik_ilanlar_tarih_sirasiyla_listelenir_bitmis_ve_kopya_atlanir(self):
        kayitlar = [
            {'key': 'b', 'kurum': 'B Bakanlığı', 'manset': '5 Memur', 'son_tarih': '2026-11-02', 'durum': 'ok', 'iller': ['Ankara'],
             'ogrenim': ['lisans'], 'kpss': 'kpss', 'puan_turleri': ['P3']},
            {'key': 'a', 'kurum': 'A Belediyesi', 'manset': '3 İşçi', 'son_tarih': '2026-10-20', 'durum': 'soon', 'kpss': 'kpsssiz'},
            {'key': 'x', 'kurum': 'Bitmiş', 'son_tarih': '2026-10-01', 'durum': 'expired'},
            {'key': 'k', 'kurum': 'Kopya', 'son_tarih': '2026-10-21', 'durum': 'ok', 'kopya_of': 'a'},
            {'key': 's', 'kurum': 'Sayfasız', 'son_tarih': '2026-10-22', 'durum': 'ok'},
        ]
        metin = yz.llms_metni(kayitlar, BASE, datetime(2026, 10, 12, 9), {'a', 'b', 'x', 'k'})
        self.assertTrue(metin.startswith('# KPSS Tercihi\n'))
        self.assertIn('## Açık ilanlar (2)', metin)
        self.assertLess(metin.index('ilan/a/'), metin.index('ilan/b/'))
        self.assertIn('- [B Bakanlığı — 5 Memur](https://kpsstercihi.com/ilan/b/): Ankara; lisans; KPSS P3; son başvuru 2 Kasım 2026', metin)
        self.assertIn('KPSS şartı yok', metin)
        self.assertNotIn('Bitmiş', metin)
        self.assertNotIn('Kopya', metin)
        self.assertNotIn('Sayfasız', metin)

    def test_sss_sayfasi_gecerli_faq_verisi_tasir(self):
        url, html = yz.sss_sayfasi(BASE)
        self.assertEqual(url, BASE + 'sss/')
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html).group(1))
        self.assertEqual(ld['@type'], 'FAQPage')
        self.assertEqual(len(ld['mainEntity']), len(yz.SSS))
        self.assertIn('<h1>Sık sorulan sorular</h1>', html)


class IndexNowTest(unittest.TestCase):
    def harita(self, *yollar):
        return '<urlset>' + ''.join(f'<url><loc>{BASE}{y}</loc></url>' for y in yollar) + '</urlset>'

    def test_yalniz_yeni_adresler_bildirilir(self):
        liste = indexnow.bildirilecek(self.harita('', 'ilan/a/', 'ilan/b/'), self.harita('', 'ilan/a/'))
        self.assertEqual(liste, [BASE, BASE + 'llms.txt', BASE + 'ilan/b/'])
        self.assertEqual(indexnow.bildirilecek(self.harita('', 'ilan/a/'), self.harita('', 'ilan/a/')), [])

    def test_gonderim_anahtar_ve_host_tasir(self):
        gelen = {}

        class Yanit:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def ac(istek, timeout):
            gelen.update(json.loads(istek.data))
            return Yanit()

        self.assertEqual(indexnow.gonder([BASE], ac), 200)
        self.assertEqual(gelen['host'], 'kpsstercihi.com')
        self.assertEqual(gelen['keyLocation'], f'{BASE}{indexnow.ANAHTAR}.txt')
        self.assertEqual(gelen['urlList'], [BASE])


if __name__ == '__main__':
    unittest.main()
