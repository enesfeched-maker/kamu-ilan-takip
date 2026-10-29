"""Katiplik SEO sayfaları, statik akademik sayfası ve üst menü (Kasım 2026)."""
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import akademik_sayfasi
import katiplik_sayfalari
import site_uret as su

DOCS = Path(__file__).resolve().parents[1] / 'docs'


def ld_bloklari(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class KatiplikSayfalari(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metinler = katiplik_sayfalari.metinleri_oku(DOCS)

    def test_resmi_metinler_okunur(self):
        self.assertEqual(len(self.metinler), 30)
        for _, metin in self.metinler:
            self.assertRegex(metin, r'^[a-zçğıöşü ]+$')
            self.assertGreater(len(metin.split()), 250)

    def test_tum_sayfalar_yazilir(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'katiplik' / 'metin').mkdir(parents=True)
            (Path(d) / 'katiplik' / 'metin' / 'zk2025.js').write_text((DOCS / 'katiplik' / 'metin' / 'zk2025.js').read_text(encoding='utf-8'), encoding='utf-8')
            adresler = katiplik_sayfalari.yaz(d, su.BASE)
            self.assertEqual(len(adresler), 33)
            self.assertTrue((Path(d) / 'katiplik' / 'sinav-metinleri' / 'metin-30' / 'index.html').exists())
            self.assertIn(su.BASE + 'katiplik/degerlendirme-kriterleri/', adresler)

    def test_metin_sayfasi_metni_ve_sinav_baglantisini_icerir(self):
        url, html = katiplik_sayfalari.metin_sayfasi(su, su.BASE, self.metinler, 14)
        self.assertEqual(url, su.BASE + 'katiplik/sinav-metinleri/metin-15/')
        self.assertIn(self.metinler[14][1], html)
        self.assertIn('katiplik/?k=zk2025&amp;m=14&amp;mod=sinav&amp;basla=1', html)
        self.assertIn('href="../metin-14/"', html)
        self.assertIn('href="../metin-16/"', html)
        self.assertIn('../../../sayfa.css', html)   # ortalama uzunlukta ondalık değiştirme yolları bozmasın
        tipler = [g['@type'] for b in ld_bloklari(html) for g in b['@graph']]
        self.assertEqual(tipler, ['Article', 'BreadcrumbList'])

    def test_kriter_sayfasi_hesaplayici_ve_sss(self):
        _, html = katiplik_sayfalari.kriter_sayfasi(su, su.BASE)
        self.assertIn('id="h-sonuc"', html)
        for tur in ('Fazla vuruş', 'Kelime bölme', 'Fazla boşluk', 'Karışık hata'):
            self.assertIn(tur, html)
        tipler = [g['@type'] for b in ld_bloklari(html) for g in b['@graph']]
        self.assertIn('FAQPage', tipler)

    def test_ust_menu_katiplik_vurgulu_akademik_yok(self):
        ust = su.ust_html('../', 'katiplik')
        self.assertNotIn('Akademik', ust)
        self.assertIn('class="aktif tb-yeni" aria-current="page"', ust)
        self.assertIn('<b class="tb-rozet">Yeni</b>', ust)
        self.assertIn('class="tb-yeni"', su.ust_html('../'))
        self.assertIn('akademik/">Akademik ilanlar</a>', su.alt_html('../'))


class AkademikSayfasi(unittest.TestCase):
    def test_acik_ilanlar_listelenir_gecmisler_atlanir(self):
        simdi = datetime(2026, 11, 2, 10, 0, tzinfo=su.TR)
        kayitlar = [
            {'key': 'AAA', 'kurum': 'Ankara Üniversitesi', 'manset': '12 Araştırma Görevlisi', 'son_tarih': '2026-11-03', 'toplam': 12},
            {'key': 'BBB', 'kurum': 'Ege Üniversitesi', 'manset': '5 Öğretim Üyesi', 'son_tarih': '2026-11-20'},
            {'key': 'CCC', 'kurum': 'Eski Üniversite', 'manset': '1 Öğretim Görevlisi', 'son_tarih': '2026-10-01'},
        ]
        url, html = akademik_sayfasi.sayfa(kayitlar, su.BASE, simdi)
        self.assertEqual(url, su.BASE + 'akademik/')
        self.assertIn('href="../#ilan/AAA"', html)
        self.assertIn('Ege Üniversitesi', html)
        self.assertNotIn('Eski Üniversite', html)
        self.assertIn('<b>2</b> açık ilan', html)
        self.assertIn('Araştırma görevlisi: 1', html)
        self.assertIn('ak-tarih yakin', html)   # 1 gün kala vurgulanır

    def test_bos_liste(self):
        _, html = akademik_sayfasi.sayfa([], su.BASE, datetime(2026, 11, 2, tzinfo=su.TR))
        self.assertIn('Şu an açık akademik ilan yok', html)


if __name__ == '__main__':
    unittest.main()
