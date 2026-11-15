"""15 Kasım 2026 SEO denetimi düzeltmeleri: kırıntı/JobPosting, RSS, ince sayfa sayımı, kadro kısa cevapları."""
import json
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ince_sayfa  # noqa: E402
import puan_sayfalari as ps  # noqa: E402
import site_uret as su  # noqa: E402

TR = timezone(timedelta(hours=3))
SIMDI = datetime(2026, 11, 15, 12, 0, tzinfo=TR)


def satir(kurum, mn, il='ANKARA', kontenjan=2, yerlesen=1):
    return {'kurum': kurum, 'il': il, 'teskilat': 'Merkez', 'unvan': 'MEMUR', 'kontenjan': kontenjan, 'yerlesen': yerlesen, 'min': mn, 'max': mn}


class InceSayfaTest(unittest.TestCase):
    def test_sayfa_basi_giris_sayilir_konum_cubugu_sayilmaz(self):
        html = ('<body><section class="kp-hero"><div class="wrap"><nav class="crumbs">Ana sayfa / Kurumlar</nav>'
                '<h1>Bir iki</h1><p>üç dört beş</p></div></section><main id="icerik">altı yedi</main></body>')
        self.assertEqual(ince_sayfa.ana_kelime_sayisi(html), 7)

    def test_sayfa_basi_yoksa_yalniz_main(self):
        self.assertEqual(ince_sayfa.ana_kelime_sayisi('<body><main>bir iki</main></body>'), 2)


class KadroSorulariTest(unittest.TestCase):
    def test_hepsi_veriden(self):
        donemler = {'2025-2': [satir('A KURUMU', 70.0), satir('B KURUMU', 72.0)],
                    '2026-1': [satir('A KURUMU', 71.5, kontenjan=3, yerlesen=2), satir('A KURUMU', 75.25), satir('C KURUMU', 80.0)]}
        sc = dict(ps.kadro_sorulari('Memur', 'Lisans', donemler))
        cevap = sc['KPSS Memur (lisans) kaç puanla atanılır?']
        self.assertIn('en düşük yerleşme puanı 71,50', cevap)
        self.assertIn('3 kadronun yarısında en küçük puan 75,25', cevap)
        self.assertIn('7 kontenjan vardı; 4 kişi yerleşti, 3 kontenjan boş kaldı', sc['2026/1 döneminde kaç Memur kontenjanı vardı?'])
        self.assertTrue(sc['Memur kadrosu en çok hangi kurumlarda açıldı?'].startswith('2025/2–2026/1 arasındaki 2 dönemde'))
        self.assertIn('2025/2: 4, 2026/1: 7', sc['Memur kontenjanı dönemden döneme nasıl değişti?'])

    def test_tek_kurum_tek_donem(self):
        sc = dict(ps.kadro_sorulari('Memur', 'Lisans', {'2026-1': [satir('A KURUMU', 70.0)]}))
        self.assertNotIn('Memur kadrosu en çok hangi kurumlarda açıldı?', sc)
        self.assertNotIn('Memur kontenjanı dönemden döneme nasıl değişti?', sc)
        self.assertEqual(ps.kurum_bolumu('Memur', {'2026-1': [satir('A KURUMU', 70.0)]}), '')

    def test_soru_semasi_kacisli(self):
        h = ps._soru_bolumu([('<b>soru</b>', 'cevap')])
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', h).group(1)
        self.assertNotIn('<b>', ld)
        self.assertEqual(json.loads(ld)['mainEntity'][0]['name'], '<b>soru</b>')


class IlanSemasiTest(unittest.TestCase):
    def item(self, **ek):
        d = {'id': 'sbb-' + 'a' * 24, 'kurum': 'ÖRNEK BAKANLIĞI', 'baslik': 'ÖRNEK BAKANLIĞI - UZUN RESMİ İLAN BAŞLIĞI', 'kadro': '5 Uzman',
             'link': 'https://kamuilan.sbb.gov.tr/ilan/1', 'son_tarih': '2099-01-01'}
        d.update(ek)
        return d

    def test_kirinti_kurumdan_ilana_ve_isveren_kimligi(self):
        end = datetime(2099, 1, 1, 23, 59, tzinfo=TR)
        ld = su.yapisal_veri(self.item(), su.BASE + 'ilan/x/', end, {'manset': '5 Uzman', 'toplam': 5}, {}, {}, SIMDI, True, ad='Örnek Bakanlığı Uzman Alımı 2099')
        bloklar = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', ld)]
        kirinti = bloklar[0]['itemListElement']
        self.assertNotIn('#ilanlar', json.dumps(kirinti))
        self.assertEqual([k['position'] for k in kirinti], [1, 2, 3])
        self.assertEqual(kirinti[-1]['name'], 'Örnek Bakanlığı Uzman Alımı 2099')
        is_ = bloklar[1]
        self.assertEqual(is_['identifier']['name'], is_['hiringOrganization']['name'])


class RssTest(unittest.TestCase):
    def test_yalniz_acik_ve_dizinlenen_en_yeni_once(self):
        gorunen = [{'key': 'a', 'kurum': 'A & B', 'manset': '2 Memur', 'son_tarih': '2099-01-01', 'ilk_gorulme': '2026-11-10T10:00:00+03:00'},
                   {'key': 'b', 'kurum': 'C', 'manset': 'Uzman', 'son_tarih': '2099-01-01', 'ilk_gorulme': '2026-11-14T10:00:00+03:00'},
                   {'key': 'c', 'kurum': 'D', 'manset': 'Eski', 'son_tarih': '2026-01-01', 'ilk_gorulme': '2026-11-14T10:00:00+03:00'},
                   {'key': 'd', 'kurum': 'E', 'manset': 'Gizli', 'son_tarih': '2099-01-01', 'ilk_gorulme': '2026-11-14T10:00:00+03:00'}]
        x = su.rss_xml(gorunen, {'a', 'b', 'c', 'd'}, {'d'}, SIMDI)
        import xml.etree.ElementTree as ET
        ogeler = ET.fromstring(x).find('channel').findall('item')
        self.assertEqual([o.find('link').text for o in ogeler], [su.BASE + 'ilan/b/', su.BASE + 'ilan/a/'])
        self.assertEqual(ogeler[1].find('title').text, 'A & B: 2 Memur')


class IlkGorselTest(unittest.TestCase):
    def test_main_icindeki_ilk_gorsel_tembel_degil(self):
        h = '<img src="ust.png" loading="lazy"><main><img src="1.png" loading="lazy"><img src="2.png" loading="lazy"></main>'
        self.assertEqual(su.ilk_gorsel_hemen(h), '<img src="ust.png" loading="lazy"><main><img src="1.png"><img src="2.png" loading="lazy"></main>')
        self.assertEqual(su.ilk_gorsel_hemen('<p>görsel yok</p>'), '<p>görsel yok</p>')


if __name__ == '__main__':
    unittest.main()
