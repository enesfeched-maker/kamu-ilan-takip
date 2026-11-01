import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import statik_icerik as si
from site_uret import TR

SIMDI = datetime(2026, 11, 1, 12, 0, tzinfo=TR)
ANA = ('<main><div class="manset-ic"><p class="manset-bos">İlanlar yükleniyor…</p></div>'
       '<h1><small id="result-count" role="status">yükleniyor…</small></h1><p class="liste-ozet" id="filter-summary"></p>\n\n'
       '<div class="zaman" id="cards"></div><div class="bos-kutu" id="empty" hidden></div></main>')
PUAN = ('<section class="puan-intro"><h1>Taban puanları</h1></section><span class="sayi" id="tablo-ozet"></span>'
        '<table><tbody id="satirlar"></tbody></table>')


def kayit(key, son, **ek):
    return dict({'key': key, 'kurum': 'Ankara <Belediyesi>', 'kurum_slug': 'ankara', 'manset': '2 Zabıta Memuru', 'il': 'Ankara',
                 'ogrenim': ['lisans'], 'toplam': 2, 'son_tarih': son}, **ek)


class AnaSayfaTest(unittest.TestCase):
    def setUp(self):
        self.liste = [kayit('a', '2026-11-20'), kayit('b', '2026-11-05'), kayit('gecmis', '2026-10-01'),
                      kayit('akademik', '2026-11-03', kategori='akademik'), kayit('ici', '2026-11-03', kurum_ici=True),
                      kayit('kopya', '2026-11-03', kopya_of='a'), kayit('noindex', '2026-11-04'), kayit('sayfasiz', '2026-11-04'),
                      kayit('tarihsiz', None)]
        self.sayfali = {'a', 'b', 'gecmis', 'akademik', 'ici', 'kopya', 'noindex', 'tarihsiz'}

    def sec(self):
        return si.sec(self.liste, self.sayfali, {'noindex'}, SIMDI)

    def test_secim_sirasi_ve_filtre(self):
        self.assertEqual([k['key'] for k in self.sec()], ['b', 'a'])   # en yakın son tarih önce; geçmiş, akademik, kurum içi, kopya, noindex, sayfasız, tarihsiz yok
        uzun = [kayit(f'k{i}', '2026-12-01') for i in range(40)]
        self.assertEqual(len(si.sec(uzun, {k['key'] for k in uzun}, set(), SIMDI)), 30)

    def test_ozet_cumlesi(self):
        self.assertEqual(si.ozet_cumlesi(self.liste), '6 açık ilan · 12 kadro · 1 kurum')   # kopya, akademik, kurum içi sayılmaz
        self.assertEqual(si.ozet_cumlesi([]), '')

    def test_doldurur_idempotent_ve_kacirir(self):
        yeni = si.anasayfa_html(ANA, self.sec(), si.ozet_cumlesi(self.liste), 6)
        self.assertIn('<a class="satir-link" href="ilan/b/">2 Zabıta Memuru</a>', yeni)
        self.assertIn('Son başvuru: 5 Kasım 2026', yeni)
        self.assertIn('Ankara &lt;Belediyesi&gt;', yeni)
        self.assertNotIn('<Belediyesi>', yeni)
        self.assertIn('<small id="result-count" role="status">6 ilan</small>', yeni)
        self.assertIn('id="filter-summary">6 açık ilan · 12 kadro · 1 kurum</p>', yeni)
        self.assertIn('Başvurusu açık 6 kamu ilanı', yeni)
        self.assertNotIn('yükleniyor', yeni)
        self.assertIn('<div class="bos-kutu" id="empty" hidden>', yeni)
        self.assertEqual(si.anasayfa_html(yeni, self.sec(), si.ozet_cumlesi(self.liste), 6), yeni)   # ikinci çalıştırma aynı

    def test_isaret_yoksa_none(self):
        self.assertIsNone(si.anasayfa_html('<html></html>', [], '', 0))
        self.assertIsNone(si.anasayfa_html(ANA.replace('id="filter-summary"', 'id="x"'), [], '', 0))

    def test_yaz_dosyalari(self):
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t)
            (docs / 'puanlar').mkdir()
            (docs / 'index.html').write_text(ANA, encoding='utf-8')
            (docs / 'puanlar' / 'index.html').write_text(PUAN, encoding='utf-8')
            satir = lambda u, m: {'kurum': 'X', 'il': 'VAN', 'teskilat': 'Merkez', 'unvan': u, 'kontenjan': 1, 'yerlesen': 1, 'min': m, 'max': m}
            veri = {'donemler': {'2025-2': [satir('ESKİ', 99.0)], '2026-1': [satir(f'U{i}', 50.0 + i) for i in range(60)] + [satir('PUANSIZ', None)]}}
            (docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
            self.assertEqual(si.yaz(docs, self.liste, self.sayfali, {'noindex'}, SIMDI), [True, True])
            ana = (docs / 'index.html').read_text(encoding='utf-8')
            self.assertEqual(ana.count('class="satir"'), 2)
            p = (docs / 'puanlar' / 'index.html').read_text(encoding='utf-8')
            self.assertEqual(p.count('<tr>'), 50)
            self.assertIn('<td>U59</td>', p)
            self.assertLess(p.index('U59'), p.index('U58'))   # en küçük puan yüksekten
            self.assertNotIn('ESKİ', p)   # yalnız son dönem
            self.assertIn('109,00000', p)
            self.assertIn('2026/1 dönemi: 61 kadro', p)
            self.assertIn('href="../analiz/"', p)
            self.assertEqual(p.count('statik-baglanti'), 1)
            self.assertEqual(si.yaz(docs, self.liste, self.sayfali, {'noindex'}, SIMDI), [True, True])
            self.assertEqual((docs / 'puanlar' / 'index.html').read_text(encoding='utf-8'), p)   # idempotent
            self.assertEqual((docs / 'index.html').read_text(encoding='utf-8'), ana)

    def test_dosya_yoksa_hata_yok(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(si.yaz(Path(t), self.liste, self.sayfali, set(), SIMDI), [])

    def test_puan_secimi_bos(self):
        self.assertIsNone(si.puan_secimi({'donemler': {}}))
        self.assertIsNone(si.puan_html(PUAN.replace('id="satirlar"', ''), ('2026-1', [], 0)))


if __name__ == '__main__':
    unittest.main()