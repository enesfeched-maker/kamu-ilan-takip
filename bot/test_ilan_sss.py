import json
import re
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import ilan_rehber as ir
import site_uret

TR = ZoneInfo('Europe/Istanbul')
SIMDI = datetime.now(TR)


def ilan(gun_bas=-3, gun_son=10, saat=(23, 59), **ek):
    bas = (SIMDI + timedelta(days=gun_bas)).replace(hour=0, minute=0, second=0, microsecond=0)
    son = (SIMDI + timedelta(days=gun_son)).replace(hour=saat[0], minute=saat[1], second=0, microsecond=0)
    d = {'id': 'sbb-' + 'a' * 24, 'link': 'https://kamuilan.sbb.gov.tr/ilan/x', 'ozet': 'Sözleşmeli personel alınacak.', 'baslik': 'İçişleri Bakanlığı Sözleşmeli Personel Alımı', 'kurum': 'İçişleri Bakanlığı',
         'kpss': 'kpss', 'puan_turleri': ['P3', 'P93'], 'ogrenim': ['lisans', 'onlisans'],
         'baslangic_zaman': bas.isoformat(), 'son_zaman': son.isoformat(), 'son_tarih': son.date().isoformat()}
    d.update(ek)
    return d


class Sorular(unittest.TestCase):
    def test_acik_ilan(self):
        qa = dict(ir.sorular(ilan(), 'X Alımı', 1170, SIMDI))
        self.assertIn('son gün', qa['X Alımı başvurusu ne zaman?'])
        self.assertEqual(qa['X Alımı için kaç kişi alınacak?'], 'İlanda toplam 1.170 kadro var.')
        self.assertEqual(qa['X Alımı için KPSS şartı var mı?'], 'Evet. İstenen puan türü: P3, P93.')
        self.assertIn('Lisans, Önlisans mezunları.', qa['X Alımı için kimler başvurabilir?'])
        self.assertNotIn('X Alımı başvurusu nereden yapılır?', qa)

    def test_kapanan_ilan(self):
        qa = dict(ir.sorular(ilan(-30, -5), 'X', None, SIMDI))
        self.assertIn('sona erdi', qa['X başvurusu ne zaman?'])

    def test_kapanis_saati(self):
        qa = dict(ir.sorular(ilan(saat=(17, 0)), 'X', None, SIMDI))
        self.assertIn('saat 17.00', qa['X başvurusu ne zaman?'])

    def test_kpsssiz_ve_kanal(self):
        qa = dict(ir.sorular(ilan(kpss='kpsssiz', ozet='Başvurular İŞKUR üzerinden yapılır.'), 'X', None, SIMDI))
        self.assertEqual(qa['X için KPSS şartı var mı?'], 'Hayır, bu ilanda KPSS şartı aranmıyor.')
        self.assertIn('İŞKUR', qa['X başvurusu nereden yapılır?'])
        self.assertNotIn('X için kaç kişi alınacak?', qa)

    def test_az_soru_eski_duzen(self):
        item = {'baslik': 'KTB Sözleşmeli Bilişim Personeli', 'kategori': 'bilisim', 'kpss': 'kpss'}
        self.assertLess(len(ir.sorular(item, 'X', None, SIMDI)), 2)
        html = ir.bolum_html(item, ad='X', simdi=SIMDI)
        self.assertIn('Başvuru hakkında ayrıntılar', html)
        self.assertNotIn('ilan-sss', html)

    def test_sss_duzeni(self):
        html = ir.bolum_html(ilan(), ad='X Alımı', toplam=5, simdi=SIMDI)
        self.assertIn('class="ilan-rehber ilan-sss"', html)
        self.assertIn('<h3>X Alımı için kaç kişi alınacak?</h3><p>İlanda toplam 5 kadro var.</p>', html)
        self.assertNotIn('<ul>', html)
        self.assertEqual(ir.bolum_html(ilan(iptal_edildi=True), ad='X'), '')

    def test_faq_jsonld(self):
        s = ir.faq_jsonld([('Soru </script>?', 'Cevap')])
        self.assertNotIn('</script>?', s)
        veri = json.loads(re.search(r'>(.*)</script>$', s, re.S).group(1))
        self.assertEqual(veri['@type'], 'FAQPage')
        self.assertEqual(veri['mainEntity'][0]['acceptedAnswer']['text'], 'Cevap')


class Sayfa(unittest.TestCase):
    def test_faq_yalniz_dizinli_birincil(self):
        item = ilan()
        html = site_uret.detail_page(item, simdi=SIMDI)[1]
        self.assertIn('"@type":"FAQPage"', html)
        self.assertIn('Sık sorulan sorular', html)
        kopya = site_uret.detail_page(item, simdi=SIMDI, kopya={'rol': 'ikincil', 'birincil': 'sbb-' + 'b' * 24})[1]
        self.assertNotIn('FAQPage', kopya)
        self.assertNotIn('FAQPage', site_uret.detail_page(ilan(ozet=None), simdi=SIMDI)[1])   # içeriksiz sayfa noindex


if __name__ == '__main__':
    unittest.main()