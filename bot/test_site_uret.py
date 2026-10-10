import unittest
from datetime import datetime
from site_uret import TR, bot_ilanlari, detail_page


class SiteTests(unittest.TestCase):
    def test_safe_static_detail_and_canonical(self):
        result = detail_page({'baslik': '<script>alert(1)</script>', 'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111', 'son_tarih': '2000-01-01'})
        self.assertIn('&lt;script&gt;', result[1])
        self.assertNotIn('<script>alert', result[1])
        self.assertIn('Başvuru sona erdi', result[1])
        self.assertIn('/ilan/11111111-1111-4111-8111-111111111111/', result[1])

    def test_reject_foreign_host_and_path_traversal(self):
        self.assertIsNone(detail_page({'link': 'https://evil.example/?i=11111111-1111-4111-8111-111111111111'}))
        self.assertIsNone(detail_page({'link': 'https://kariyerkapisi.gov.tr/?i=../../secret'}))


    def test_alt_baslik_temizlenir_ve_h1_ile_ayniysa_atilir(self):
        item = {'baslik': 'ADALET BAKANLIĞI - 150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.', 'kurum': 'ADALET BAKANLIĞI', 'kadro': '150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.',
                'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111', 'son_tarih': '2099-01-01'}
        html = detail_page(item, simdi=datetime(2026, 10, 5, tzinfo=TR))[1]
        self.assertNotIn('d-alt', html)
        self.assertNotIn('Alacak', html.split('</section>')[0])
        item['baslik'] = 'ADALET BAKANLIĞI - 2026 Yılı Açıktan İcra Müdür Alım İlanı'
        html = detail_page(item, simdi=datetime(2026, 10, 5, tzinfo=TR))[1]
        self.assertNotIn('d-alt', html)  # alt başlık kaldırıldı (sade sayfa)

    def test_bot_ilanlari(self):
        simdi = datetime(2026, 5, 10, 12, 0, tzinfo=TR)
        kk = 'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111'
        ilanlar = [
            {'id': 'b', 'link': kk, 'baslik': 'Zabıta Memuru', 'kurum': 'İzmir Belediyesi', 'kaynak_kimlikleri': ['z', 'b', 'a'],
             'son_tarih': '2026-05-10', 'ozet': 'KPSS İLE', 'iller': ['İzmir'], 'kpss': 'kpss'},
            {'id': 'gecti', 'link': kk, 'son_tarih': '2026-05-09'},
            {'id': 'gecti2', 'link': kk, 'son_tarih': '2099-01-01', 'son_zaman': '2026-05-10T11:00:00+03:00'},
            {'id': 'tarihsiz', 'link': 'https://ornek.example/x', 'baslik': 'I' * 3000},
        ]
        cikti = bot_ilanlari(ilanlar, simdi)['ilanlar']
        self.assertEqual([i['id'] for i in cikti], ['b', 'tarihsiz'])
        self.assertEqual(cikti[0]['kimlikler'], ['a', 'b', 'z'])
        self.assertTrue(cikti[0]['sayfa'].endswith('/ilan/11111111-1111-4111-8111-111111111111/'))
        self.assertEqual(cikti[0]['iller'], ['İzmir'])
        self.assertIn('zabıta memuru', cikti[0]['metin'])
        self.assertEqual(cikti[1]['sayfa'], 'https://ornek.example/x')
        self.assertEqual(len(cikti[1]['metin']), 1500)


class TemaBetigiTests(unittest.TestCase):
    def test_tema_kurali_isaretleri(self):
        from site_uret import TEMA_BETIGI
        for isaret in ('kit-theme', 'prefers-color-scheme: dark', 'getHours()', 'h>=20||h<7', 'kitKoyu', 'kitTemaUygula', 'setInterval', '"change"', '#0D0E0C', '#F6F6F1'):
            self.assertIn(isaret, TEMA_BETIGI)

    def test_tema_betigi_statik_sayfalarla_ayni(self):
        import os
        from site_uret import TEMA_BETIGI
        kok = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs')
        for yol in ('index.html', '404.html', os.path.join('puanlar', 'index.html')):
            with open(os.path.join(kok, yol), encoding='utf-8') as f:
                self.assertIn(TEMA_BETIGI, f.read(), yol)


class KosulTemizTests(unittest.TestCase):
    def test_karisik_gizlenir_maddeler_alt_alta(self):
        import site_uret
        self.assertEqual(site_uret._kosul_temiz('Ünvan Başvuru Cinsiyet Adet Aranan Nitelikler Kodu Ofis 1 BÜRO PERSONELİ BP01 - 4birinden mezun olmak.'), '')
        t = site_uret._kosul_temiz('6) Tüm unvanlar için en az 60 puan. a) Lisans için KPSSP3. b) Ön lisans için KPSSP93.')
        self.assertEqual(site_uret._kosul_html(t), 'Tüm unvanlar için en az 60 puan.<br>a) Lisans için KPSSP3.<br>b) Ön lisans için KPSSP93.')

if __name__ == '__main__':
    unittest.main()
