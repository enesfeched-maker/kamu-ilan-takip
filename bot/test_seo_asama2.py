"""SEO ikinci aşama (18 Kasım 2026): menü/niyet ayrımı, ilgili sayfalar bağlantıları, kırıntılar, iş ilanı şeması, kalıcı kurum sayfaları."""
import json
import re
import unittest
from unittest import mock
from datetime import date, datetime
from pathlib import Path

import site_uret as su

KOK = Path(__file__).resolve().parents[1]


class MenuNiyetTesti(unittest.TestCase):
    def test_menude_tercih_robotu_ve_altta_taban_puanlari(self):
        ust = su.ust_html('../')
        self.assertIn('href="../puanlar/" data-a="menu" data-a-x="Tercih Robotu">Tercih Robotu</a>', ust)
        self.assertNotIn('>Taban Puanları<', ust)
        self.assertIn('<a href="../kpss-taban-puanlari/">KPSS taban puanları</a>', su.alt_html('../'))

    def test_statik_sayfalarda_menu_etiketi_ayni(self):
        for yol in ('index.html', 'puanlar/index.html', 'bolum/index.html', 'katiplik/index.html'):
            metin = (KOK / 'docs' / yol).read_text(encoding='utf-8')
            self.assertRegex(metin, r'<a href="(?:\.\./)*puanlar/"[^>]*>Tercih Robotu</a>', yol)
            self.assertNotRegex(metin, r'puanlar/"[^>]*>Taban Puanları</a>', yol)
            self.assertIn('kpss-taban-puanlari/">KPSS taban puanları</a>', metin, yol)

    def test_puanlar_sayfasi_h1_robot(self):
        metin = (KOK / 'docs' / 'puanlar' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<section class="puan-intro"><h1>KPSS tercih robotu</h1></section>', metin)


class YayinTetikleyicileriTesti(unittest.TestCase):
    def test_site_uretenin_ice_aldigi_her_modul_tetikleyicide_listeli(self):
        """site_uret.py ve site_paketi.py'nin (tembel içe aktarmalar dahil) çağırdığı her bot modülü site-yayinla.yml paths listesinde olmalı."""
        import ast
        bot = Path(__file__).resolve().parent
        moduller = {p.stem for p in bot.glob('*.py') if not p.stem.startswith('test_')}

        def ice_aktarilan(modul):
            agac = ast.parse((bot / f'{modul}.py').read_text(encoding='utf-8'))
            sonuc = set()
            for dugum in ast.walk(agac):
                if isinstance(dugum, ast.Import):
                    sonuc |= {a.name.split('.')[0] for a in dugum.names}
                elif isinstance(dugum, ast.ImportFrom) and dugum.module:
                    sonuc.add(dugum.module.split('.')[0])
            return sonuc & moduller
        gorulen, yigin = set(), ['site_uret', 'site_paketi']
        while yigin:
            m = yigin.pop()
            if m not in gorulen:
                gorulen.add(m)
                yigin += ice_aktarilan(m)
        yml = (KOK / '.github' / 'workflows' / 'site-yayinla.yml').read_text(encoding='utf-8')
        listeli = set(re.findall(r"'bot/(\w+)\.py'", yml))
        self.assertEqual(sorted(gorulen - listeli), [])
        for yeni in ('il_sayfalari', 'meslek_sayfalari', 'puan_sayfalari', 'yz_gorunurluk', 'kurum_sayfasi', 'ince_sayfa', 'analiz_sayfalari'):
            self.assertIn(yeni, listeli)


def _is_ilanlari(html):
    return [v for v in (json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html)) if v.get('@type') == 'JobPosting']


class IsIlaniSemasiTesti(unittest.TestCase):
    """Google İş İlanları: gerekli/önerilen alanlar. Veri, depodaki gerçek kayıt defteridir; "şimdi" kayıt defterinin kendi
    güncelleme zamanıdır (sabit yakın tarih yok, veri yenilendikçe test kendiliğinden kayar)."""

    @classmethod
    def setUpClass(cls):
        veri = json.loads((KOK / 'docs' / 'ilanlar.json').read_text(encoding='utf-8'))
        cls.simdi = datetime.fromisoformat(veri['guncelleme']).astimezone(su.TR)
        bugun = cls.simdi.date().isoformat()
        cls.acik = [i for i in veri['ilanlar'] if str(i.get('son_tarih') or '9999') >= bugun and not i.get('iptal_edildi') and not i.get('duyuru_turu')]
        cls.kapali = [i for i in veri['ilanlar'] if i.get('son_tarih') and str(i['son_tarih']) < bugun][:25]

    def test_gercek_veride_her_is_ilani_eksiksiz(self):
        sayac = 0
        for item in self.acik:
            sonuc = su.detail_page(item, simdi=self.simdi)
            if not sonuc:
                continue
            html = sonuc[1]
            for j in _is_ilanlari(html):
                sayac += 1
                kimlik = item.get('id')
                self.assertNotIn('noindex', html, f'{kimlik}: noindex sayfada JobPosting olmamalı')
                self.assertEqual(j['@context'], 'https://schema.org')
                self.assertTrue(str(j.get('title') or '').strip(), kimlik)
                self.assertGreaterEqual(len(re.sub(r'<[^>]+>', '', j['description']).strip()), 40, kimlik)
                self.assertRegex(j['datePosted'], r'^\d{4}-\d{2}-\d{2}$', kimlik)
                yayim = date.fromisoformat(j['datePosted'])
                bitis = datetime.fromisoformat(j['validThrough'])
                self.assertIsNotNone(bitis.tzinfo, f'{kimlik}: validThrough saat dilimi taşımalı')
                self.assertGreater(bitis, self.simdi, f'{kimlik}: süresi dolmuş ilan JobPosting yazmamalı')
                self.assertLessEqual(yayim, bitis.date(), kimlik)
                self.assertLessEqual(yayim, self.simdi.date(), kimlik)
                kurum = j['hiringOrganization']
                self.assertEqual(kurum['@type'], 'Organization')
                self.assertTrue(kurum['name'].strip(), kimlik)
                yerler = j['jobLocation'] if isinstance(j['jobLocation'], list) else [j['jobLocation']]
                self.assertTrue(yerler, kimlik)
                for yer in yerler:
                    adres = yer['address']
                    self.assertEqual(adres['@type'], 'PostalAddress')
                    self.assertEqual(adres['addressCountry'], 'TR', kimlik)
                    self.assertEqual('addressRegion' in adres, 'addressLocality' in adres, kimlik)
                self.assertIn(j['employmentType'], {'FULL_TIME', 'PART_TIME', 'CONTRACTOR', 'TEMPORARY', 'INTERN', 'VOLUNTEER', 'PER_DIEM', 'OTHER'})
                self.assertIs(j['directApply'], False)
                self.assertTrue(j['identifier']['name'] and j['identifier']['value'], kimlik)
                self.assertTrue(j['url'].startswith(su.BASE + 'ilan/'), kimlik)
        self.assertGreater(sayac, 0, 'gerçek veride hiç JobPosting üretilmedi')

    def test_suresi_dolan_ilanda_is_ilani_yok(self):
        self.assertTrue(self.kapali)
        for item in self.kapali:
            sonuc = su.detail_page(item, simdi=self.simdi)
            if sonuc:
                self.assertEqual(_is_ilanlari(sonuc[1]), [], item.get('id'))

    def _ilan(self, **ek):
        item = {'baslik': 'ÖRNEK BAKANLIĞI - 5 MEMUR ALACAK', 'kurum': 'ÖRNEK BAKANLIĞI', 'kadro': '5 MEMUR', 'ozet': 'Örnek bakanlığına memur alınacaktır. Başvurular internetten alınır.',
                'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111', 'son_tarih': '2099-01-01', 'ilk_gorulme': '2098-12-01T10:00:00+03:00'}
        item.update(ek)
        return item

    def test_ulke_geneli_ilanda_yalniz_ulke(self):
        simdi = datetime(2098, 12, 5, tzinfo=su.TR)
        html = su.detail_page(self._ilan(), kayit={'il': 'Türkiye geneli', 'iller': []}, simdi=simdi)[1]
        yer = _is_ilanlari(html)[0]['jobLocation']
        self.assertEqual(yer, {'@type': 'Place', 'address': {'@type': 'PostalAddress', 'addressCountry': 'TR'}})
        cok_il = ['Adana', 'Ankara', 'Antalya', 'Bursa', 'Çorum', 'Denizli', 'Edirne', 'Hatay', 'İzmir', 'Konya', 'Muğla', 'Van']
        html = su.detail_page(self._ilan(), kayit={'il': 'Adana +11', 'iller': cok_il}, simdi=simdi)[1]
        self.assertEqual(_is_ilanlari(html)[0]['jobLocation']['address'], {'@type': 'PostalAddress', 'addressCountry': 'TR'})

    def test_tek_ilde_bolge_ve_sehir_yazilir(self):
        simdi = datetime(2098, 12, 5, tzinfo=su.TR)
        html = su.detail_page(self._ilan(), kayit={'il': 'Van', 'iller': ['Van']}, simdi=simdi)[1]
        self.assertEqual(_is_ilanlari(html)[0]['jobLocation']['address'],
                         {'@type': 'PostalAddress', 'addressCountry': 'TR', 'addressRegion': 'Van', 'addressLocality': 'Van'})

    def test_noindex_ve_kapali_sayfada_is_ilani_yok(self):
        simdi = datetime(2098, 12, 5, tzinfo=su.TR)
        icerik_yok = self._ilan(kadro=None, ozet=None)
        html = su.detail_page(icerik_yok, kayit={'il': 'Van', 'iller': ['Van']}, simdi=simdi)[1]
        self.assertIn('noindex', html)
        self.assertEqual(_is_ilanlari(html), [])
        html = su.detail_page(self._ilan(son_tarih='2098-11-01'), kayit={'il': 'Van', 'iller': ['Van']}, simdi=simdi)[1]
        self.assertEqual(_is_ilanlari(html), [])


class KurumArsiviTesti(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kok = Path(self.tmp.name)

    def test_birlestir_hicbir_kurumu_silmez_ve_ilanlari_tekillestirir(self):
        import kurum_arsivi as ka
        eski = {'a': {'ad': 'A', 'ilanlar': [['k1', 'Memur', '2026-01-01']]}, 'b': {'ad': 'B', 'ilanlar': []}}
        yeni = {'a': {'ad': 'A Kurumu', 'ilanlar': [['k1', 'Memur', '2026-02-01'], ['k2', 'Hemşire', '2026-03-01']]}}
        b = ka.birlestir(eski, yeni)
        self.assertEqual(set(b), {'a', 'b'})
        self.assertEqual(b['a']['ad'], 'A Kurumu')
        self.assertEqual(b['a']['ilanlar'], [['k2', 'Hemşire', '2026-03-01'], ['k1', 'Memur', '2026-02-01']])
        cok = {'x': {'ad': 'X', 'ilanlar': [[f'k{i:03d}', 'M', f'2026-01-{i % 28 + 1:02d}'] for i in range(100)]}}
        self.assertEqual(len(ka.birlestir(cok)['x']['ilanlar']), ka.EN_COK_ILAN)

    def test_yaz_oku_gidis_donus_ve_bozuk_dosya(self):
        import kurum_arsivi as ka
        yol = self.kok / 'denetim' / 'kurum-arsivi.json'
        arsiv = {'b-kurumu': {'ad': 'B Kurumu', 'ilanlar': [['k', 'Zabıta Memuru', '2026-01-02']]}, 'a-kurumu': {'ad': 'A Kurumu', 'ilanlar': []}}
        ka.yaz(arsiv, yol)
        self.assertEqual(ka.oku(yol), arsiv)
        self.assertLess(yol.read_text(encoding='utf-8').index('a-kurumu'), yol.read_text(encoding='utf-8').index('b-kurumu'))
        yol.write_text('{bozuk', encoding='utf-8')
        self.assertEqual(ka.oku(yol), {})
        self.assertEqual(ka.coz({'kurumlar': {'../kotu': {'ad': 'X'}, 'iyi': {'ad': 'Y'}}}), {'iyi': {'ad': 'Y', 'ilanlar': []}})

    def test_arsiv_sayfasi_noindex_reklamsiz_ve_kirintili(self):
        import kurum_arsivi as ka
        html = ka.arsiv_sayfasi('gazi-universitesi', 'Gazi Üniversitesi', [['k1', '3 Sürekli İşçi', '2026-11-20']])
        self.assertIn('<meta name="robots" content="noindex,follow">', html)
        self.assertNotIn('adsbygoogle', html)
        self.assertIn('Bu kurumun şu an açık ilanı yok.', html)
        self.assertIn('3 Sürekli İşçi', html)
        self.assertIn('20 Kasım 2026', html)
        self.assertIn('<a href="../">Tüm kurumlar →</a>', html)
        self.assertIn('"@type":"BreadcrumbList"', html)
        self.assertIn(su.BASE + 'kurum/gazi-universitesi/', html)

    def test_site_uretimi_arsivdeki_eksik_adresi_yazar_haritaya_koymaz(self):
        import kurum_arsivi as ka
        import kurum_sayfasi as ks
        docs = self.kok / 'docs'
        (docs / 'puanlar').mkdir(parents=True)
        yol = self.kok / 'denetim' / 'kurum-arsivi.json'
        ka.yaz({'gazi-universitesi': {'ad': 'Gazi Üniversitesi', 'ilanlar': [['k1', '3 Sürekli İşçi', '2026-11-20']]}}, yol)
        ilan = {'id': 'iskur-' + 'a' * 24, 'kurum': 'ÖRNEK BELEDİYE BAŞKANLIĞI', 'baslik': 'Örnek Belediyesi zabıta memuru alacak', 'kadro': '2 Zabıta Memuru',
                'link': 'https://www.iskur.gov.tr/is-ilani/1', 'son_tarih': '2099-01-01', 'ilk_gorulme': '2098-12-01T10:00:00+03:00'}
        with mock.patch.object(ks, 'kurum_dizinlenir', return_value=True):
            gruplar, slugler, adresler, basarili = ks.kurum_sayfalarini_uret([ilan], docs, {}, datetime(2098, 12, 5, tzinfo=su.TR), None, yol)
        arsiv_sayfa = docs / 'kurum' / 'gazi-universitesi' / 'index.html'
        self.assertTrue(arsiv_sayfa.is_file())
        self.assertIn('noindex', arsiv_sayfa.read_text(encoding='utf-8'))
        self.assertNotIn(su.BASE + 'kurum/gazi-universitesi/', adresler)
        self.assertNotIn('gazi-universitesi', (docs / 'kurum' / 'index.html').read_text(encoding='utf-8'))
        sluglar = ka.oku(yol)
        self.assertIn('gazi-universitesi', sluglar)
        self.assertTrue(set(slugler.values()) <= set(sluglar))   # güncel kurumlar da arşive girdi
        # kayıt silinse de (ilan listesi boş) adres yaşar
        ks.kurum_sayfalarini_uret([], docs, {}, datetime(2098, 12, 5, tzinfo=su.TR), None, yol)
        for slug in sluglar:
            self.assertTrue((docs / 'kurum' / slug / 'index.html').is_file(), slug)

    def test_depodaki_arsiv_gecerli_ve_elle_tohum_icinde(self):
        import kurum_arsivi as ka
        arsiv = ka.oku()
        self.assertGreater(len(arsiv), 100)
        for slug in ka.ELLE_TOHUM:
            self.assertIn(slug, arsiv)
        for slug, k in arsiv.items():
            self.assertTrue(k['ad'], slug)


class IlgiliSayfalarTesti(unittest.TestCase):
    ILAN = {'id': 'iskur-' + 'b' * 24, 'kurum': 'ANKARA BÜYÜKŞEHİR BELEDİYE BAŞKANLIĞI', 'baslik': 'Ankara Büyükşehir Belediyesi zabıta memuru alacak', 'kadro': '5 Zabıta Memuru',
            'ozet': 'Zabıta memuru alınacaktır.', 'link': 'https://www.iskur.gov.tr/is-ilani/9', 'son_tarih': '2099-01-01', 'ilk_gorulme': '2098-12-01T10:00:00+03:00'}
    KAYIT = {'unvanlar': ['zabıta memuru'], 'il': 'Ankara', 'iller': ['Ankara']}

    def harita(self, *yollar):
        return {su.BASE + y for y in yollar}

    def test_yalniz_haritada_olan_sayfalara_baglanir(self):
        import ilgili_sayfalar as isf
        gorsel = {'kurum_slug': 'ankara-buyuksehir-belediyesi'}
        tam = self.harita('meslek/zabita-memuru/', 'il/ankara/', 'kurum/ankara-buyuksehir-belediyesi/')
        bag = isf.baglantilar(self.ILAN, self.KAYIT, gorsel, KOK / 'docs', su.BASE, tam, 2098)
        self.assertEqual(bag, [('../../meslek/zabita-memuru/', 'Zabıta Memuru alımı 2098: yaş sınırı ve KPSS puanı'), ('../../il/ankara/', 'Ankara kamu ilanları'),
                               ('../../kurum/ankara-buyuksehir-belediyesi/', 'Ankara Büyükşehir Belediye Başkanlığı ilanları')])
        # kalkanla haritadan çıkan (noindex) sayfaya bağlanılmaz
        self.assertEqual(isf.baglantilar(self.ILAN, self.KAYIT, gorsel, KOK / 'docs', su.BASE, self.harita('il/ankara/'), 2098), [('../../il/ankara/', 'Ankara kamu ilanları')])
        self.assertEqual(isf.baglantilar(self.ILAN, self.KAYIT, gorsel, KOK / 'docs', su.BASE, set(), 2098), [])
        self.assertEqual(isf.satir_html([]), '')

    def test_eslesmeyen_unvana_meslek_baglantisi_yok(self):
        import ilgili_sayfalar as isf
        kayit = dict(self.KAYIT, unvanlar=['uzman yardımcısı'])
        bag = isf.baglantilar(self.ILAN, kayit, {}, KOK / 'docs', su.BASE, self.harita('meslek/zabita-memuru/'), 2098)
        self.assertEqual(bag, [])

    def test_taban_puani_kadro_sayfasi_birebir_eslesmede(self):
        import json as _json
        import tempfile
        import ilgili_sayfalar as isf
        import puan_sayfalari as ps
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t)
            (docs / 'puanlar').mkdir()
            satir = [{'kurum': 'X BELEDİYESİ', 'il': 'ANKARA', 'unvan': 'ZABITA MEMURU', 'kontenjan': 1, 'yerlesen': 1, 'min': 70.0 + i, 'max': 71.0 + i} for i in range(ps.MIN_SATIR + 1)]
            (docs / 'puanlar' / 'lisans.json').write_text(_json.dumps({'donemler': {'2026-1': satir}}, ensure_ascii=False), encoding='utf-8')
            item = dict(self.ILAN, ogrenim=['lisans'])
            import ilan_taban
            ilan_taban._veri.cache_clear()
            es = ilan_taban.eslesmeler(item, docs)
            self.assertTrue(es and es[0][3], es)
            yol = f'{ps.KLASOR}/lisans/{es[0][3]}/'
            bag = isf.baglantilar(item, self.KAYIT, {}, docs, su.BASE, self.harita(yol), 2098)
            self.assertEqual(bag, [(f'../../{yol}', 'Zabıta Memuru taban puanları (Lisans)')])
            ilan_taban._veri.cache_clear()

    def test_satir_benzer_ilanlardan_once_ve_tek_sefer(self):
        import ilgili_sayfalar as isf
        satir = isf.satir_html([('../../il/ankara/', 'Ankara kamu ilanları')])
        self.assertIn('<h2>İlgili sayfalar</h2><p><a class="yazi-link" href="../../il/ankara/">Ankara kamu ilanları</a></p>', satir)
        sayfa = '<main><div class="d-ana"><section class="d-bolum">x</section><section class="benzer">b</section></div></main>'
        yeni = isf.yerlestir(sayfa, satir)
        self.assertLess(yeni.index('ilgili-sayfalar'), yeni.index('<section class="benzer">'))
        self.assertEqual(isf.yerlestir(yeni, satir), yeni)
        benzersiz = '<main><div class="d-ana">x</div></main>'
        self.assertIn('ilgili-sayfalar', isf.yerlestir(benzersiz, satir))
        self.assertEqual(isf.yerlestir('<p>yer yok</p>', satir), '<p>yer yok</p>')

    def test_uygula_gercek_ilan_sayfasina_yazar(self):
        import tempfile
        import ilgili_sayfalar as isf
        simdi = datetime(2098, 12, 5, tzinfo=su.TR)
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t)
            anahtar, html = su.detail_page(self.ILAN, {'kurum_slug': 'ankara-buyuksehir-belediyesi', 'kurum_sayisi': 1}, self.KAYIT, None, simdi)
            (docs / 'ilan' / anahtar).mkdir(parents=True)
            (docs / 'ilan' / anahtar / 'index.html').write_text(html, encoding='utf-8')
            haritada = self.harita('meslek/zabita-memuru/', 'il/ankara/')
            self.assertEqual(isf.uygula(docs, su.BASE, haritada, {anahtar: (self.ILAN, self.KAYIT, {})}, simdi), 1)
            yeni = (docs / 'ilan' / anahtar / 'index.html').read_text(encoding='utf-8')
            self.assertIn('href="../../meslek/zabita-memuru/">Zabıta Memuru alımı 2098: yaş sınırı ve KPSS puanı</a>', yeni)
            self.assertIn('href="../../il/ankara/">Ankara kamu ilanları</a>', yeni)
            self.assertEqual(yeni.count('ilgili-sayfalar'), 1)
            self.assertTrue(yeni.rstrip().endswith('</html>'))
            self.assertEqual(isf.uygula(docs, su.BASE, haritada, {anahtar: (self.ILAN, self.KAYIT, {})}, simdi), 0)   # ikinci çalışma değişiklik yapmaz


class KirintiTesti(unittest.TestCase):
    def test_kurum_listesi_kirintisi(self):
        import kurum_sayfasi as ks
        _, html = ks.kurum_hub_sayfasi([('A Kurumu', 'a', 1, 2)])
        veri = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html)]
        kirinti = next(v for v in veri if v['@type'] == 'BreadcrumbList')
        self.assertEqual([o['name'] for o in kirinti['itemListElement']], ['Ana sayfa', 'Kurumlar'])
        self.assertEqual(kirinti['itemListElement'][1]['item'], su.BASE + 'kurum/')


if __name__ == '__main__':
    unittest.main()
