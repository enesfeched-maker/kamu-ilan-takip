"""Kalıcı il sayfaları (/il/) ile kadro ve düzey sayfalarındaki açık ilan bölümleri."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import il_sayfalari as ils
import puan_sayfalari as ps
import site_uret
from site_uret import TR

KOK = Path(__file__).resolve().parents[1]
BASE = 'https://kpsstercihi.com/'
SIMDI = datetime.now(TR)
YARIN = (SIMDI + timedelta(days=5)).date().isoformat()
DUN = (SIMDI - timedelta(days=2)).date().isoformat()


def satir(unvan, min_, il='ANKARA', kont=1, yer=1, kurum='ABC KURUMU'):
    return {'kod': '1', 'kurum': kurum, 'il': il, 'teskilat': 'Taşra', 'unvan': unvan, 'kontenjan': kont, 'yerlesen': yer,
            'min': min_, 'max': min_, 'nit': []}


def ilan(key, iller, son=YARIN, unvanlar=('memur',), ogrenim=('lisans',), **ek):
    return {'key': key, 'manset': f'İlan {key}', 'kurum': 'Deneme Kurumu', 'il': iller[0] if iller else 'Türkiye Geneli', 'iller': list(iller),
            'unvanlar': list(unvanlar), 'ogrenim': list(ogrenim), 'son_tarih': son, **ek}


def docs_kur(klasor):
    docs = Path(klasor)
    (docs / 'puanlar').mkdir(parents=True)
    lisans = {'2025-2': [satir('MEMUR', 70.0 + i, kont=2) for i in range(12)] + [satir('MEMUR', 90.0, il='VAN')],
              '2026-1': [satir('MEMUR', 80.0 + i) for i in range(12)] + [satir('MEMUR', 60.0, il='VAN'), satir('MEMUR', 61.0, il='BİLİNMEYEN')]}
    (docs / 'puanlar' / 'lisans.json').write_text(json.dumps({'duzey': 'lisans', 'donemler': lisans}, ensure_ascii=False), encoding='utf-8')
    return docs


ILANLAR = [ilan('a1', ['Ankara']), ilan('a2', ['Ankara', 'Van'], unvanlar=('mühendis',)), ilan('gecmis', ['Ankara'], son=DUN),
           ilan('genel', []), ilan('gizli', ['Ankara']), ilan('kopya', ['Ankara'], kopya_of='a1'), ilan('on', ['Ankara'], ogrenim=('onlisans',))]


class HesapTest(unittest.TestCase):
    def test_il_adi(self):
        self.assertEqual(ils.il_adi('AFYONKARAHİSAR'), 'Afyonkarahisar')
        self.assertEqual(ils.il_adi('ISPARTA'), 'Isparta')
        self.assertEqual(ils.il_slug('Şanlıurfa'), 'sanliurfa')
        self.assertIsNone(ils.il_adi('BİLİNMEYEN'))
        self.assertIsNone(ils.il_adi(None))

    def test_acik_ilanlar_yalniz_ili_belli_ve_acik_olanlar(self):
        sayfali = {k['key'] for k in ILANLAR}
        anahtarlar = [k['key'] for k in ils.acik_ilanlar('Ankara', ILANLAR, sayfali, {'gizli'}, SIMDI)]
        self.assertEqual(sorted(anahtarlar), ['a1', 'a2', 'on'])   # süresi geçen, ülke geneli, dizinlenmeyen ve kopya yok
        self.assertEqual([k['key'] for k in ils.acik_ilanlar('Van', ILANLAR, sayfali, set(), SIMDI)], ['a2'])
        self.assertEqual(ils.acik_ilanlar('Ankara', ILANLAR, {'a2'}, set(), SIMDI)[0]['key'], 'a2')   # sayfası olmayan girmez
        self.assertEqual(ils.acik_ilanlar('Ankara', [], None, None, SIMDI), [])

    def test_kadro_ilanlari_birebir_unvan_ve_duzey(self):
        ac = ps.acik_kadro_ilanlari
        self.assertEqual([k['key'] for k in ac(ILANLAR[:2], 'lisans', 'MEMUR')], ['a1'])
        self.assertEqual([k['key'] for k in ac(ILANLAR[:2], 'lisans', 'MÜHENDİS')], ['a2'])   # Türkçe büyük/küçük harf
        self.assertEqual(ac(ILANLAR[:2], 'lisans', 'MEMUR YARDIMCISI'), [])                    # benzerlik yetmez
        self.assertEqual(ac(ILANLAR[:2], 'onlisans', 'MEMUR'), [])                             # düzey açıkça yazmalı
        self.assertEqual(len(ac(ILANLAR[:2], 'lisans')), 2)
        self.assertEqual(ac(None, 'lisans'), [])

    def test_bulgular_il_ve_ulke_medyani(self):
        with tempfile.TemporaryDirectory() as g:
            veriler = ils.an._veriler(docs_kur(g))
        iller = ils.il_verisi(veriler)
        self.assertEqual(sorted(iller), ['Ankara', 'Van'])   # ili tanınmayan satır atlanır
        cumleler = ils.bulgular('Ankara', iller['Ankara'], veriler, ils.son_donemler(veriler))
        self.assertIn('Lisans: 2026/1 döneminde en küçük puanların medyanı 85,50; 2025/2 dönemine göre 10,00 puan yükseldi (75,50).', cumleler[0])
        self.assertIn('Aynı dönemde Türkiye geneli medyanı 84,50.', cumleler[0])   # 14 satır: Ankara 80–91, Van 60, tanınmayan 61
        self.assertEqual(cumleler[1], '2025/2–2026/1 dönemlerinde Ankara için en çok kontenjan açan kurum Abc Kurumu (36 kontenjan).')


class SayfaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gecici = tempfile.TemporaryDirectory()
        cls.docs = docs_kur(cls.gecici.name)
        cls.puan_urls = ps.puan_sayfalarini_uret(cls.docs, BASE, ILANLAR, None, {'gizli'}, SIMDI)
        cls.urls = ils.yaz(cls.docs, BASE, ILANLAR, None, {'gizli'}, SIMDI)
        cls.ankara = (cls.docs / 'il' / 'ankara' / 'index.html').read_text(encoding='utf-8')
        cls.van = (cls.docs / 'il' / 'van' / 'index.html').read_text(encoding='utf-8')
        cls.hub = (cls.docs / 'il' / 'index.html').read_text(encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.gecici.cleanup()

    def test_adresler_yalniz_dizinlenenler(self):
        self.assertEqual(self.urls, [BASE + 'il/', BASE + 'il/ankara/'])   # Van 2 satır: eşiğin altında

    def test_zayif_il_noindex_ve_reklamsiz(self):
        self.assertIn('<meta name="robots" content="noindex,follow">', self.van)
        self.assertNotIn('adsbygoogle', self.van)
        self.assertNotIn('noindex', self.ankara)
        self.assertIn('adsbygoogle', self.ankara)

    def test_il_sayfasi_icerigi(self):
        s = self.ankara
        self.assertIn('<title>Ankara Kamu İlanları ve KPSS Taban Puanları | KPSS Tercihi</title>', s)
        self.assertIn(f'<link rel="canonical" href="{BASE}il/ankara/">', s)
        self.assertIn('Başvurusu açık ilanlar <span class="sayi">3</span>', s)
        self.assertIn('<a href="../../ilan/a1/">İlan a1</a>', s)
        for yok in ('ilan/gecmis/', 'ilan/genel/', 'ilan/gizli/', 'ilan/kopya/'):
            self.assertNotIn(yok, s)
        self.assertIn('24 kadro satırı ve 36 kontenjan', s)
        self.assertIn('Lisans: dönem dönem', s)
        self.assertIn('Lisans: 2026/1 döneminde en düşük puanlı kadrolar', s)
        self.assertIn('<a href="../../kpss-taban-puanlari/lisans/memur/">Memur</a>', s)   # taban puanı sayfası olan unvana bağlantı
        self.assertIn('"@type":"BreadcrumbList"', s)
        self.assertIn('Hazırlayan: KPSS Tercihi Editörlüğü. Güncelleme: ' + site_uret.tarih_yazi(SIMDI.date().isoformat()), s)
        self.assertNotIn('kurum/abc-kurumu/', s)   # sayfası olmayan kuruma bağlantı verilmez

    def test_acik_ilan_yoksa_tek_satir(self):
        with tempfile.TemporaryDirectory() as g:
            docs = docs_kur(g)
            ils.yaz(docs, BASE, [], None, None, SIMDI)
            s = (docs / 'il' / 'ankara' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Şu an ili Ankara olarak belirtilmiş açık ilan yok.', s)
        self.assertNotIn('<span class="sayi">0</span>', s)

    def test_hub(self):
        self.assertIn('<a href="ankara/">Ankara</a>', self.hub)
        self.assertIn('<a href="van/">Van</a>', self.hub)
        self.assertLess(self.hub.index('ankara/'), self.hub.index('van/'))
        satir_ = re.search(r'<tr><td><a href="ankara/">Ankara</a></td>(.*?)</tr>', self.hub).group(1)
        self.assertEqual(re.findall(r'>([^<>]+)</td>', satir_), ['3', '24', '36', '80,50'])

    def test_kadro_ve_duzey_sayfasinda_acik_ilanlar(self):
        kadro = (self.docs / 'kpss-taban-puanlari' / 'lisans' / 'memur' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Başvurusu açık Memur ilanları <span class="sayi">2</span>', kadro)   # a1 ve ülke geneli ilan (il şartı yok)
        self.assertIn('<a href="../../../ilan/a1/">İlan a1</a>', kadro)
        self.assertIn('ilan/genel/', kadro)
        for yok in ('ilan/on/', 'ilan/a2/', 'ilan/gizli/', 'ilan/gecmis/', 'ilan/kopya/'):   # başka düzey, başka unvan, dizin dışı, süresi geçmiş, kopya
            self.assertNotIn(yok, kadro)
        duzey = (self.docs / 'kpss-taban-puanlari' / 'lisans' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Başvurusu açık lisans ilanları <span class="sayi">3</span>', duzey)
        self.assertIn('<a href="../../ilan/a2/">İlan a2</a>', duzey)

    def test_ilan_verilmezse_bolum_yok(self):
        with tempfile.TemporaryDirectory() as g:
            docs = docs_kur(g)
            ps.puan_sayfalarini_uret(docs, BASE)
            kadro = (docs / 'kpss-taban-puanlari' / 'lisans' / 'memur' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('Başvurusu açık', kadro)


class GercekVeriTest(unittest.TestCase):
    """Depodaki ÖSYM verisiyle: 81 ilin hepsi tanınır, dizine giren her il sayfası gerçek tablolar içerir."""

    def test_81_il(self):
        with tempfile.TemporaryDirectory() as g:
            docs = Path(g)
            shutil.copytree(KOK / 'docs' / 'puanlar', docs / 'puanlar', ignore=shutil.ignore_patterns('*.js', '*.css', '*.html', '*-bolum.json'))
            urls = ils.yaz(docs, BASE, [], None, None, SIMDI)
            sayfalar = {p.parent.name: p.read_text(encoding='utf-8') for p in (docs / 'il').glob('*/index.html')}
        self.assertEqual(len(sayfalar), 81)
        self.assertGreaterEqual(len(urls), 70)
        for slug, s in sayfalar.items():
            dizinde = f'{BASE}il/{slug}/' in urls
            self.assertEqual('noindex' not in s, dizinde, slug)
            self.assertEqual('adsbygoogle' in s, dizinde, slug)
            if dizinde:
                self.assertGreaterEqual(s.count('<table class="kp-tablo">'), 2, slug)
                self.assertIn('Öne çıkanlar', s, slug)
            self.assertLessEqual(len(re.search(r'<meta name="description" content="([^"]*)"', s).group(1)), site_uret.ACIKLAMA_SINIRI, slug)


class BaglantiTest(unittest.TestCase):
    def test_alt_bilgide_iller(self):
        self.assertIn('<a href="../il/">İller</a>', site_uret.alt_html('../'))
        for yol, kok in (('index.html', ''), ('bolum/index.html', '../'), ('puanlar/index.html', '../')):
            self.assertIn(f'<a href="{kok}il/">İller</a>', (KOK / 'docs' / yol).read_text(encoding='utf-8'), yol)

    def test_analiz_il_tablosu_baglantili(self):
        self.assertEqual(ils.an._il_baglantisi('Şanlıurfa'), '<a href="../../il/sanliurfa/">Şanlıurfa</a>')


if __name__ == '__main__':
    unittest.main()
