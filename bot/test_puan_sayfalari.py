import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import puan_sayfalari as ps

BASE = 'https://kpsstercihi.com/'


def satir(unvan, min_, kurum='ABC <b>Kurumu</b>', max_=None, kont=1, yer=1):
    return {'kod': '1', 'kurum': kurum, 'il': 'ANKARA', 'teskilat': 'Merkez', 'unvan': unvan,
            'kontenjan': kont, 'yerlesen': yer, 'min': min_, 'max': max_ if max_ is not None else min_, 'nit': []}


class PuanSayfalariTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        (self.docs / 'puanlar').mkdir()
        veri = {'duzey': 'lisans', 'ad': 'Lisans', 'kaynak': 'x', 'donemler': {
            '2022-1': [satir('HEMŞİRE', 70.5), satir('HEMŞİRE', 72.25), satir('İŞÇİ', 60.0)],
            '2026-1': [satir('HEMŞİRE', 71.2346, max_=88.1), satir('HEMŞİRE', 75.0, kurum='Z Kurumu'), satir('MEMUR', 80.0)],
        }}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
        self.urls = ps.puan_sayfalarini_uret(self.docs, BASE)
        self.k = self.docs / 'kpss-taban-puanlari'

    def tearDown(self):
        self.tmp.cleanup()

    def test_slug_ve_esik(self):
        self.assertTrue((self.k / 'lisans' / 'hemsire' / 'index.html').exists())
        self.assertFalse((self.k / 'lisans' / 'memur').exists())    # 1 satır
        self.assertFalse((self.k / 'lisans' / 'isci').exists())
        s = ps.benzersiz_sluglar(['A B', 'A-B', 'a b'])
        self.assertEqual(len(set(s.values())), 3)
        self.assertEqual(ps._ascii_slug('ÇOCUK GELİŞİMİ'), 'cocuk-gelisimi')

    def test_url_listesi_ve_canonical(self):
        self.assertEqual(sorted(self.urls), sorted([BASE + 'kpss-taban-puanlari/', BASE + 'kpss-taban-puanlari/lisans/']))   # hemşire: son iki dönemde 4 kayıt, haritada yok
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('noindex,follow', h)
        self.assertTrue(ps.kadro_dizinlenir({'2025-1': [{}] * 2, '2025-2': [{}] * 2, '2026-1': [{}] * 3}))
        self.assertFalse(ps.kadro_dizinlenir({'2022-1': [{}] * 9, '2025-2': [{}] * 2, '2026-1': [{}] * 2}))
        self.assertIn('<link rel="canonical" href="' + BASE + 'kpss-taban-puanlari/lisans/hemsire/">', h)
        self.assertIn('<html lang="tr">', h)
        self.assertIn('BreadcrumbList', h)
        self.assertIn('og:url', h)
        self.assertIn('../../../sayfa.css', h)

    def test_uzun_unvanda_baslik_ogrenim_duzeyini_korur(self):
        # 'Veri Hazırlama ve Kontrol İşletmeni' lisans ve önlisans sayfaları aynı <title>'ı alıyordu (düzey sondan kesiliyordu).
        import site_uret as su
        donemler = {'2026-1': [satir('VERİ HAZIRLAMA VE KONTROL İŞLETMENİ', 80.0)]}
        basliklar = set()
        for slug, ad in (('lisans', 'Lisans'), ('onlisans', 'Önlisans')):
            h = ps.kadro_sayfasi(BASE, slug, ad, 'VERİ HAZIRLAMA VE KONTROL İŞLETMENİ', 'veri-hazirlama-ve-kontrol-isletmeni', donemler, 2022, 2026)
            h = h if isinstance(h, str) else next(x for x in h if isinstance(x, str) and '<title>' in x)
            baslik = h.split('<title>')[1].split('</title>')[0]
            self.assertIn(f'({ad})', baslik)
            self.assertLessEqual(len(baslik), su.TITLE_SINIRI)
            basliklar.add(baslik)
        self.assertEqual(len(basliklar), 2)

    def test_sayi_bicimi(self):
        self.assertEqual(ps.sayi(71.2346), '71,23')
        self.assertEqual(ps.sayi(71.2346, 3), '71,235')
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('71,235', h)
        self.assertIn('en düşük puan 71,23, en yüksek 88,10', h)
        self.assertNotIn('71.23', h)

    def test_kurum_il_baslik_hali(self):
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<td data-et="İl">Ankara</td>', h)
        self.assertNotIn('<td>ANKARA</td>', h)
        self.assertEqual(ps._duzgun('İSTANBUL'), 'İstanbul')
        self.assertEqual(ps._duzgun('IĞDIR'), 'Iğdır')
        self.assertIn('Z Kurumu', h)

    def test_kadro_cumleleri(self):
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('2026/1 döneminde en küçük puanların medyanı 73,12', h)   # (71,2346 + 75) / 2
        self.assertIn('2022/1 dönemine göre 1,74 puan yükseldi', h)
        self.assertNotIn('yerleşildi', h)   # tek il: karşılaştırma cümlesi yok
        d = {'2025-2': [satir('X', 70.0)], '2026-1': [dict(satir('X', 60.0), il='VAN'), dict(satir('X', 90.0), il='İZMİR'), satir('X', 75.0)]}
        c = ps.kadro_cumleleri(d)
        self.assertEqual(len(c), 2)
        self.assertIn('75,00', c[0])
        self.assertIn('5,00 puan yükseldi', c[0])
        self.assertIn('en düşük puanla Van (60,00), en yüksek puanla İzmir (90,00)', c[1])
        self.assertEqual(ps.kadro_cumleleri({'2026-1': [satir('X', 60.0)]}), [])   # tek dönem, <3 satır
        self.assertEqual(ps.kadro_cumleleri({'2025-2': [satir('X', None)], '2026-1': [satir('X', 60.0)]}), [])

    def test_baslik_hali(self):
        self.assertEqual(ps.baslik_hali('HEMŞİRE YARDIMCISI'), 'Hemşire Yardımcısı')
        self.assertEqual(ps.baslik_hali('İŞÇİ'), 'İşçi')

    def test_html_kacis(self):
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('&lt;b&gt;', h)
        self.assertNotIn('<b>', h.split('<main')[1])

    def test_aciklama_uzunlugu_ve_not(self):
        import re
        for p in self.k.rglob('index.html'):
            h = p.read_text(encoding='utf-8')
            d = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
            self.assertLessEqual(len(d), 160)
            self.assertIn('resmî sonuç için ÖSYM&#x27;yi kontrol edin', h)

    def test_duzey_tablosu_ince_unvan_baglantisiz(self):
        h = (self.k / 'lisans' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<a href="hemsire/">Hemşire</a>', h)
        self.assertIn('<td>Memur</td>', h)
        self.assertIn('2022–2026', (self.k / 'index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
