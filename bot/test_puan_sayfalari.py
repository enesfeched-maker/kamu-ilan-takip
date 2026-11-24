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
        # hemşire: son iki dönemde 4 kayıt ≥ MIN_DIZIN_SATIR (3); içerik inceliğini site haritası yazılırken ince_sayfa ayrıca süzer
        self.assertEqual(sorted(self.urls), sorted([BASE + 'kpss-taban-puanlari/', BASE + 'kpss-taban-puanlari/lisans/', BASE + 'kpss-taban-puanlari/lisans/hemsire/']))
        h = (self.k / 'lisans' / 'hemsire' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('noindex', h)
        self.assertTrue(ps.kadro_dizinlenir({'2025-1': [{}] * 2, '2025-2': [{}] * 2, '2026-1': [{}] * 3}))
        self.assertFalse(ps.kadro_dizinlenir({'2022-1': [{}] * 9, '2025-2': [{}] * 1, '2026-1': [{}] * 1}))
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

    def test_duzey_kisa_cevaplar_veriden(self):
        h = (self.k / 'lisans' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<h2>Kısa cevaplar</h2>', h)
        self.assertIn('"@type":"FAQPage"', h)
        self.assertIn('<h3>2026/1 KPSS lisans en düşük taban puanı kaç?</h3>', h)
        self.assertIn('kadrosu Hemşire (', h)
        self.assertIn('oldu: 71,23.', h)
        self.assertIn('3 lisans kadrosunun 1 tanesinde en küçük puan 75 puanın altındaydı.', h)
        self.assertNotIn('70 puanla atanılır mı', h)     # 70'in altında kadro yok: soru üretilmez
        self.assertNotIn('85 puanla atanılır mı', h)     # hepsi 85'in altında: bilgi taşımayan soru üretilmez
        b = ps.kisa_bilgiler(self.docs)
        self.assertEqual([(x[0], x[2], x[4]) for x in b], [('lisans', '2026-1', [])])
        self.assertEqual(ps.duzey_sorulari('Lisans', '2026-1', {}), [])

    def test_aralik_gruplama(self):
        g = ps.araliklari_grupla([{'min': 74.999}, {'min': 75.0}, {'min': 100.0}, {'min': None}, {}])
        self.assertEqual({a: len(v) for a, v in g.items()}, {70: 1, 75: 1, 95: 1})
        self.assertEqual(ps.aralik_slug(70), '70-75-puan')

    def test_aralik_sayfasi_veriden(self):
        h = (self.k / 'lisans' / '70-75-puan' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('KPSS Lisans 70–75 Puanla Nereye Atanılır? (2026/1)', h)
        self.assertIn('arasında olan 1 kadro vardı', h)
        self.assertIn('Puanı açıklanan 3 kadronun 1 tanesinde en küçük puan 75 puanın altındaydı.', h)
        self.assertIn('2022/1 döneminde aynı aralıkta 2 kadro vardı.', h)
        self.assertIn('<a href="../hemsire/">Hemşire</a>', h)
        self.assertIn('71,235', h)
        self.assertIn('<a href="../75-80-puan/">75–80 puan</a>', h)
        self.assertNotIn('href="../70-75-puan/"', h)
        self.assertIn('<link rel="canonical" href="' + BASE + 'kpss-taban-puanlari/lisans/70-75-puan/">', h)
        self.assertIn('noindex,follow', h)          # 1 kadro: ince sayfa dizine girmez
        self.assertFalse(any('puan/' in u.rsplit('lisans/', 1)[-1] for u in self.urls))
        self.assertTrue((self.k / 'lisans' / '80-85-puan' / 'index.html').exists())
        self.assertFalse((self.k / 'lisans' / '60-65-puan').exists())    # son dönemde o aralıkta kadro yok
        self.assertIn('<a href="70-75-puan/">70–75 puan</a>', (self.k / 'lisans' / 'index.html').read_text(encoding='utf-8'))

    def test_dolu_aralik_dizine_girer(self):
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t)
            (docs / 'puanlar').mkdir()
            veri = {'duzey': 'onlisans', 'ad': 'Önlisans', 'kaynak': 'x', 'donemler': {
                '2026-1': [satir('MEMUR', 80.0 + i / 10) for i in range(ps.MIN_ARALIK_SATIR)] + [satir('MEMUR', 91.0)]}}
            (docs / 'puanlar' / 'onlisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
            urls = ps.puan_sayfalarini_uret(docs, BASE)
            self.assertIn(BASE + 'kpss-taban-puanlari/onlisans/80-85-puan/', urls)
            self.assertNotIn(BASE + 'kpss-taban-puanlari/onlisans/90-95-puan/', urls)
            h = (docs / 'kpss-taban-puanlari' / 'onlisans' / '80-85-puan' / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('noindex', h)
            self.assertNotIn('döneminde aynı aralıkta', h)   # önceki dönem yok


class BolumSayfalariTest(unittest.TestCase):
    """Üniversite bölümüne göre sayfalar (docs/kpss-taban-puanlari/<düzey>/bolumler/)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        (self.docs / 'puanlar').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def kur(self, donemler, nitelikler, bolumler=None):
        """donemler: {dönem: [(nit kodu, min), ...]} — her kadro ayrı, uzun kurum adıyla (ince sayfa kalkanı geçsin)."""
        veri = {'donemler': {d: [dict(satir('HEMŞİRE', m, kurum=f'Büyükşehir Belediyesi Sağlık Hizmetleri Müdürlüğü {i} ve Bağlı Kuruluşları', kont=3, yer=2),
                                   nit=[n]) for i, (n, m) in enumerate(rows)] for d, rows in donemler.items()}}
        bolumler = bolumler or {'3204': 'HEMŞİRELİK', '3205': 'Hemşirelik', '3300': 'EBELİK', '3400': 'DİYETİSYENLİK'}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
        (self.docs / 'puanlar' / 'lisans-bolum.json').write_text(json.dumps({'bolumler': bolumler, 'nitelikler': nitelikler}, ensure_ascii=False), encoding='utf-8')
        self.urls = ps.puan_sayfalarini_uret(self.docs, BASE)
        self.k = self.docs / 'kpss-taban-puanlari' / 'lisans'

    def sayfa(self, slug):
        return (self.k / 'bolumler' / slug / 'index.html').read_text(encoding='utf-8')

    def test_ozel_acik_onek_ve_okunamayan(self):
        # 'ozel': tam kod; 'acik': '*'; 'onek': '3200-*' (3204/3205 ile eşleşmez, ön ek '3204-'), 'okun': '?'
        nit = {'a': ['3204'], 'b': ['*'], 'c': ['3204-*', '3300'], 'd': ['?'], 'e': ['3205']}
        veri = {'donemler': {'2026-1': [satir('X', 70.0, kurum='K')]}}
        bolum = {'bolumler': {'3204': 'HEMŞİRELİK', '3204-1': 'HEMŞİRELİK (İÖ)', '3205': 'Hemşirelik', '3300': 'EBELİK'},
                 'nitelikler': {'2026-1': nit}}
        kadrolar = [dict(satir('X', 70.0), nit=[n]) for n in nit]
        veri = {'donemler': {'2026-1': kadrolar}}
        ozel, acik, donemler = ps.bolum_satirlari(veri, bolum)
        hem = ps._kucuk('HEMŞİRELİK')
        self.assertEqual(sorted(r['nit'][0] for _, r in ozel[hem]), ['a', 'e'])   # a: kod, e: aynı adlı 3205 (c yalnız '3204-1' koduna ön ekle bağlı)
        self.assertEqual([r['nit'][0] for _, r in ozel[ps._kucuk('HEMŞİRELİK (İÖ)')]], ['c'])   # '3204-*' ön eki
        self.assertEqual(sorted(r['nit'][0] for _, r in ozel[ps._kucuk('EBELİK')]), ['c'])
        self.assertEqual([r['nit'][0] for _, r in acik], ['b'])                         # '*' özel sayılmaz, ayrı sayılır
        self.assertNotIn('d', {r['nit'][0] for l in ozel.values() for _, r in l})       # '?' yok sayılır
        self.assertEqual(donemler, ['2026-1'])
        # '3204-*' ön eki '3204-1' koduna uyar ama '32041' gibi koda uymaz (puanlar.js ile aynı: kod ön ekle başlar)
        self.assertEqual(ps._liste_bolumleri(['3204-*'], {'3204-1': 'a', '32041': 'b'}, ['3204-1', '32041']), {'a'})

    def test_esik_9_satirda_sayfa_yok_10da_var(self):
        for n, var in ((9, False), (10, True)):
            with self.subTest(n=n):
                self.kur({'2026-1': [('a', 70.0 + i) for i in range(n)]}, {'2026-1': {'a': ['3204']}})
                self.assertEqual((self.k / 'bolumler' / 'hemsirelik' / 'index.html').exists(), var)
                self.assertEqual((self.k / 'bolumler' / 'index.html').exists(), var)
                self.assertEqual('Bölümüne göre bak' in (self.k / 'index.html').read_text(encoding='utf-8'), var)

    def test_puansiz_satir_esige_sayilmaz(self):
        self.kur({'2026-1': [('a', 70.0 + i) for i in range(9)] + [('a', None)]}, {'2026-1': {'a': ['3204']}})
        self.assertFalse((self.k / 'bolumler' / 'hemsirelik').exists())

    def test_son_dort_donem_penceresi(self):
        # 5 dönemden en eski (2022-1) dışarıda kalır: yalnız o dönemdeki 10 kadro eşiği geçirmemeli
        don = {'2022-1': [('a', 60.0 + i) for i in range(10)], '2023-1': [('z', 70.0)], '2024-1': [('z', 70.0)],
               '2025-1': [('z', 70.0)], '2026-1': [('z', 70.0)]}
        nit = {d: {'a': ['3204'], 'z': ['3300']} for d in don}
        self.kur(don, nit)
        self.assertFalse((self.k / 'bolumler' / 'hemsirelik').exists())
        self.assertEqual(ps.bolum_satirlari({'donemler': {d: [dict(satir('X', 1.0), nit=['a'])] for d in don}}, {'bolumler': {'3204': 'H'}, 'nitelikler': nit})[2],
                         ['2023-1', '2024-1', '2025-1', '2026-1'])

    def test_ayni_adli_kodlar_birlesir_ve_acik_cumlesi(self):
        # 3204 ve 3205 aynı bölüm (büyük/küçük harf farkı); kadrolar ayrı kodlara bağlı → tek sayfada 10 kadro
        nit = {'a': ['3204'], 'b': ['3205'], 'x': ['*']}
        rows = [('a', 70.0 + i) for i in range(5)] + [('b', 80.0 + i) for i in range(5)] + [('x', 50.0)]
        self.kur({'2026-1': rows}, {'2026-1': nit})
        h = self.sayfa('hemsirelik')
        self.assertIn('10 kadro vardı', h)
        self.assertIn('Ayrıca bu dönemlerde 1 kadro tüm lisans bölümlerine açıktı.', h)
        self.assertIn('<h1>Hemşirelik mezunları KPSS ile hangi kadrolara atanır?</h1>', h)
        self.assertEqual(sorted(p.name for p in (self.k / 'bolumler').iterdir() if p.is_dir()), ['hemsirelik'])   # ebelik eşik altında

    def test_cta_baglantisi_kodlanir(self):
        self.kur({'2026-1': [('a', 70.0 + i) for i in range(10)]}, {'2026-1': {'a': ['3204']}}, {'3204': 'AĞIZ VE DİŞ SAĞLIĞI & HİZMETLERİ'})
        h = self.sayfa('agiz-ve-dis-sagligi-hizmetleri')
        self.assertIn('href="../../../../nereye/?d=lisans&amp;b=A%C4%9F%C4%B1z%20ve%20Di%C5%9F%20Sa%C4%9Fl%C4%B1%C4%9F%C4%B1%20%26%20Hizmetleri"', h)
        self.assertIn('Puanını gir, tercih robotunu dene →', h)
        self.assertIn('Puanınla şu an hangi ilanlara başvurabileceğini gör →', h)

    def test_dizin_duzey_sayfasi_ve_site_haritasi(self):
        self.kur({'2026-1': [('a', 70.0 + i) for i in range(10)] + [('b', 50.0 + i) for i in range(10)]},
                 {'2026-1': {'a': ['3204'], 'b': ['3400']}})
        dizin = (self.k / 'bolumler' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<a href="diyetisyenlik/">Diyetisyenlik</a>', dizin)
        self.assertLess(dizin.index('Diyetisyenlik'), dizin.index('Hemşirelik'))   # alfabetik
        self.assertIn('href="../">', dizin)
        self.assertIn('<a href="bolumler/">', (self.k / 'index.html').read_text(encoding='utf-8'))
        self.assertIn(BASE + 'kpss-taban-puanlari/lisans/bolumler/', self.urls)
        self.assertIn(BASE + 'kpss-taban-puanlari/lisans/bolumler/hemsirelik/', self.urls)
        self.assertIn(BASE + 'kpss-taban-puanlari/lisans/bolumler/diyetisyenlik/', self.urls)
        self.assertIn('BreadcrumbList', self.sayfa('hemsirelik'))
        self.assertIn('<a href="../">Bölümler</a>', self.sayfa('hemsirelik'))

    def test_turkce_alfabe_sirasi(self):
        self.assertEqual(sorted(['Zeytin', 'Çay', 'Cam', 'İnci', 'Irmak', 'Şeker', 'Sera', 'Ödev', 'Oda'], key=ps._tr_anahtar),
                         ['Cam', 'Çay', 'Irmak', 'İnci', 'Oda', 'Ödev', 'Sera', 'Şeker', 'Zeytin'])

    def test_kalkan_inceyi_haritaya_almaz_ve_eski_klasor_silinir(self):
        import ince_sayfa
        # kısa kurum adı: sayfa 250 kelimenin altında kalır → noindex, haritada yok
        veri = {'donemler': {'2026-1': [dict(satir('X', 70.0 + i, kurum='K'), nit=['a']) for i in range(10)]}}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri), encoding='utf-8')
        (self.docs / 'puanlar' / 'lisans-bolum.json').write_text(json.dumps({'bolumler': {'3204': 'HEMŞİRELİK'}, 'nitelikler': {'2026-1': {'a': ['3204']}}}), encoding='utf-8')
        urls = ps.puan_sayfalarini_uret(self.docs, BASE)
        h = (self.docs / 'kpss-taban-puanlari' / 'lisans' / 'bolumler' / 'hemsirelik' / 'index.html').read_text(encoding='utf-8')
        self.assertLess(ince_sayfa.ana_kelime_sayisi(h), ince_sayfa.MIN_KELIME)
        self.assertIn('noindex', h)
        self.assertNotIn(BASE + 'kpss-taban-puanlari/lisans/bolumler/hemsirelik/', urls)
        # bölüm kalkınca klasörü de kalkar
        (self.docs / 'puanlar' / 'lisans-bolum.json').write_text(json.dumps({'bolumler': {}, 'nitelikler': {}}), encoding='utf-8')
        ps.puan_sayfalarini_uret(self.docs, BASE)
        self.assertFalse((self.docs / 'kpss-taban-puanlari' / 'lisans' / 'bolumler').exists())


if __name__ == '__main__':
    unittest.main()
