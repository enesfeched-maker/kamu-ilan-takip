"""Kalıcı meslek sayfaları (/meslek/): eşleşme, içerik, dizin kuralı ve adresin hiç 404 vermemesi."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meslek_sayfalari as ms
import statik_icerik as si

BASE = 'https://kpsstercihi.com/'
SIMDI = datetime.now(si.TR)          # sabit tarih yok: testler takvimden bağımsız


def gun(n):
    return (SIMDI + timedelta(days=n)).date().isoformat()


def ilan(key, unvanlar, kurum='Örnek <b>Belediyesi</b>', son=10, il='Konya'):
    return {'key': key, 'manset': '3 ' + unvanlar[0].title(), 'kurum': kurum, 'iller': [il], 'il': il, 'unvanlar': unvanlar,
            'ogrenim': ['onlisans'], 'son_tarih': gun(son), 'baslangic_zaman': gun(son - 5) + 'T00:00:00+03:00', 'durum': 'ok'}


class MeslekSayfalariTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        (self.docs / 'puanlar').mkdir()
        satir = lambda u, m: {'kurum': 'X BAKANLIĞI', 'il': 'ANKARA', 'unvan': u, 'kontenjan': 2, 'yerlesen': 2, 'min': m, 'max': m + 1}
        veri = {'donemler': {'2025-2': [satir('HEMŞİRE', 60.0)], '2026-1': [satir('HEMŞİRE', 71.5), satir('HEMŞİRE', 80.25), satir('MEMUR', 75.0)]}}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
        self.ilanlar = [ilan('a1', ['zabıta memuru — erkek', 'zabıta memuru — kadın'], son=3), ilan('a2', ['zabıta memuru', 'tekniker'], kurum='B Belediyesi', son=9),
                        ilan('a3', ['inşaat mühendisi'])]
        self.urls = ms.yaz(self.docs, BASE, self.ilanlar, simdi=SIMDI)
        self.k = self.docs / 'meslek'

    def tearDown(self):
        self.tmp.cleanup()

    def oku(self, slug=''):
        return (self.k / slug / 'index.html').read_text(encoding='utf-8')

    def test_eslesme_birebir(self):
        e = lambda slug, u: ms.eslesir(next(d for s, _, d in ms.MESLEKLER if s == slug), u)
        self.assertTrue(e('zabita-memuru', 'Zabıta Memuru — Erkek'))
        self.assertFalse(e('zabita-memuru', 'zabıta amiri'))
        self.assertTrue(e('muhendis', 'inşaat mühendisi'))
        self.assertTrue(e('muhendis', 'MÜHENDİS'))
        self.assertFalse(e('muhendis', 'uzman personel — mühendislik'))
        self.assertFalse(e('memur', 'zabıta memuru'))        # 'memur' yalnız düz memur unvanıdır
        self.assertFalse(e('memur', 'hareket memuru'))
        self.assertTrue(e('itfaiye-eri', 'itfaiyeci'))
        self.assertEqual(len({s for s, _, _ in ms.MESLEKLER}), len(ms.MESLEKLER))

    def test_her_meslek_sayfasi_var(self):
        for slug, _, _ in ms.MESLEKLER:                       # ilanı olmasa da adres 404 vermez
            self.assertTrue((self.k / slug / 'index.html').exists(), slug)
        self.assertIn('noindex,follow', self.oku('avukat'))   # ilan da puan da yok: dizine girmez
        self.assertNotIn(BASE + 'meslek/avukat/', self.urls)
        self.assertIn('başvurusu açık avukat ilanı yok', self.oku('avukat'))

    def test_acik_ilanli_sayfa(self):
        h = self.oku('zabita-memuru')
        self.assertIn(BASE + 'meslek/zabita-memuru/', self.urls)
        self.assertNotIn('noindex', h)
        self.assertIn(f'<h1>Zabıta Memuru alımı {SIMDI.year}</h1>', h)
        self.assertIn('başvurusu açık 2 zabıta memuru ilanı var', h)
        self.assertIn('<a href="../../ilan/a1/">', h)
        self.assertIn('<a href="../../ilan/a2/">', h)
        self.assertNotIn('ilan/a3/', h)
        self.assertIn('&lt;b&gt;Belediyesi', h)
        import re
        gorunen = re.sub(r'<script type="application/ld\+json">.*?</script>', '', h, flags=re.S)   # JSON-LD metin taşır, HTML olarak işlenmez
        self.assertNotIn('<b>Belediyesi', gorunen)
        self.assertNotIn('</b>', re.search(r'"@type":"FAQPage".*?</script>', h, re.S).group(0)[:-9])   # betik içinde '</' kaçışlı
        self.assertLess(h.index('ilan/a1/'), h.index('ilan/a2/'))      # en yakın son başvuru önce
        self.assertIn('"@type":"FAQPage"', h)
        self.assertIn('Şu an açık zabıta memuru alımı var mı?', h)
        self.assertIn('<link rel="canonical" href="' + BASE + 'meslek/zabita-memuru/">', h)
        self.assertIn('ilan/a3/', self.oku('muhendis'))
        self.assertIn('ilan/a2/', self.oku('tekniker'))

    def test_taban_puani_veriden(self):
        h = self.oku('hemsire')
        self.assertIn(BASE + 'meslek/hemsire/', self.urls) if ms.MIN_PUAN_SATIR <= 2 else self.assertIn('noindex,follow', h)
        self.assertIn('KPSS hemşire taban puanları', h)
        self.assertIn('2026/1', h)
        self.assertIn('71,50', h)
        self.assertIn('80,25', h)
        self.assertNotIn('60,00', h)                           # yalnız son dönem
        self.assertIn('KPSS lisans hemşire taban puanı kaç?', h)
        self.assertNotIn('taban puanları', self.oku('zabita-memuru').split('<main')[1].split('Telegram')[0])

    def test_gecmis_ve_dizin_kurali(self):
        gecmis = [{'key': f'g{i}', 'kurum': f'K{i}', 'il': 'Van', 'unvanlar': ['avukat'], 'son_tarih': gun(-i - 1)} for i in range(ms.MIN_GECMIS)]
        _, h, dizin = ms.meslek_sayfasi(BASE, 'avukat', 'Avukat', [], gecmis, [], SIMDI, sayfali={'g0'})
        self.assertTrue(dizin)
        self.assertIn('Başvurusu biten avukat ilanları', h)
        self.assertIn('<a href="../../ilan/g0/">K0</a>', h)
        self.assertNotIn('ilan/g1/', h)                        # sayfası olmayan ilana bağlantı verilmez
        self.assertFalse(ms.dizinlenir([], gecmis[:ms.MIN_GECMIS - 1], []))
        self.assertTrue(ms.dizinlenir([{}], [], []))

    def test_hub_ve_alt_bilgi(self):
        h = self.oku()
        self.assertEqual(self.urls[0], BASE + 'meslek/')
        self.assertIn('<a href="zabita-memuru/">Zabıta Memuru alımı</a> — 2 açık ilan', h)
        self.assertIn('<a href="avukat/">Avukat alımı</a> — şu an açık ilan yok', h)
        import site_uret
        self.assertIn('<a href="../meslek/">Meslekler</a>', site_uret.alt_html('../'))
        kok = Path(__file__).resolve().parent.parent
        self.assertIn('<a href="meslek/">Meslekler</a>', (kok / 'docs' / 'index.html').read_text(encoding='utf-8'))

    def test_arama_dizini(self):
        dizin = json.loads((self.k / ms.DIZIN).read_text(encoding='utf-8'))
        sluglar = [s for s, _ in dizin]
        self.assertIn(['zabita-memuru', 'Zabıta Memuru'], dizin)      # açık ilanı var
        self.assertIn('hemsire', sluglar)                              # yalnız taban puanı var
        self.assertNotIn('avukat', sluglar)                            # boş sayfa aramada önerilmez
        e = lambda slug, u: ms.eslesir(next(d for s, _, d in ms.MESLEKLER if s == slug), u)
        self.assertTrue(e('sekreter', 'Tıbbi Sekreter'))
        self.assertTrue(e('veteriner-hekim', 'VETERİNER'))
        self.assertFalse(e('veteriner-hekim', 'veteriner sağlık teknisyeni'))
        self.assertFalse(e('ebe', 'muhasebeci'))
        kok = Path(__file__).resolve().parent.parent
        js = (kok / 'docs' / 'portal.js').read_text(encoding='utf-8')
        self.assertIn("getJSON('meslek/" + ms.DIZIN + "')", js)        # site bu dosyayı okur; adı birlikte değişmeli
        self.assertIn("a.href='meslek/'+m[0]+'/'", js)

    def test_tarih_araligi_kisa(self):
        self.assertEqual(ms.tarih_araligi('2026-11-18', '2026-11-20'), '18–20 Kasım 2026')
        self.assertEqual(ms.tarih_araligi('2026-11-30', '2026-12-04'), '30 Kasım – 4 Aralık 2026')
        self.assertEqual(ms.tarih_araligi('2026-12-21', '2027-01-05'), '21 Aralık 2026 – 5 Ocak 2027')
        self.assertEqual(ms.tarih_araligi('', '2026-11-20'), '20 Kasım 2026')
        self.assertEqual(ms.tarih_araligi('2026-11-20', '2026-11-20'), '20 Kasım 2026')
        self.assertEqual(ms.tarih_araligi('2026-11-18', ''), '—')

    def test_gecmis_kayitlari_suzer(self):
        ham = [{'id': 'x1', 'kurum': 'A Belediyesi', 'son_tarih': gun(-2), 'baslik': 'Zabıta memuru alımı'},
               {'id': 'x2', 'kurum': 'A Belediyesi', 'son_tarih': gun(5)},
               {'id': 'x3', 'kurum': 'C Belediyesi', 'son_tarih': gun(-3), 'iptal_edildi': True}]
        g = ms.gecmis_kayitlari(ham, SIMDI)
        self.assertEqual([k['kurum'] for k in g], ['A Belediyesi'])
        self.assertEqual(ms.gecmis_kayitlari(ham, SIMDI, {'kopya_of': {'x1': 'y'}}), [])


if __name__ == '__main__':
    unittest.main()
