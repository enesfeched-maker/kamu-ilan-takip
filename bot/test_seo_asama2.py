"""SEO ikinci aşama (18 Kasım 2026): menü/niyet ayrımı, ilgili sayfalar bağlantıları, kırıntılar, iş ilanı şeması, kalıcı kurum sayfaları."""
import json
import re
import unittest
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


if __name__ == '__main__':
    unittest.main()
