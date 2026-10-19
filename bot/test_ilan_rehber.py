import unittest

import ilan_rehber as ir


class IlanRehber(unittest.TestCase):
    def test_bilisim_ilani(self):
        item = {'baslik': 'KTB - Sözleşmeli Bilişim Personeli', 'kategori': 'bilisim', 'kpss': 'kpss', 'puan_turleri': ['P3'],
                'ogrenim': ['lisans'], 'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=x',
                'ozet': 'Başvurular e-Devlet üzerinden Kariyer Kapısı\'ndan yapılır.',
                'baslangic_zaman': '2026-10-19T00:00:00+03:00', 'son_zaman': '2026-10-26T23:59:00+03:00'}
        html = ir.bolum_html(item)
        self.assertIn('Başvuru dönemi: 19 – 26 Ekim 2026 (8 gün).', html)
        self.assertIn('İstenen KPSS puan türü: P3.', html)
        self.assertIn('Lisans', html)
        self.assertIn('href="../../rehber/sozlesmeli-bilisim-personeli/"', html)
        self.assertIn('href="../../rehber/kariyer-kapisi-basvuru/"', html)
        self.assertNotIn('saat', html)

    def test_kapanis_saati_ve_aylar_arasi(self):
        m = ir.maddeler({'baslangic_zaman': '2026-10-28T00:00:00+03:00', 'son_zaman': '2026-11-03T17:00:00+03:00'})
        self.assertEqual(m[0], 'Başvuru dönemi: 28 Ekim 2026 – 3 Kasım 2026 (7 gün).')
        self.assertIn('17.00', m[1])

    def test_basvuru_kanali_metinden(self):
        kk = 'https://kariyerkapisi.gov.tr/IlanDetay?i=x'
        self.assertEqual(ir.basvuru_kanali({'link': kk, 'ozet': 'Başvurular yalnız İŞKUR web sayfasından yapılır.'}), 'iskur')
        self.assertIsNone(ir.basvuru_kanali({'link': kk, 'ozet': 'Başvurular şahsen yapılır.'}))
        self.assertNotIn('Kariyer Kapısı', ir.bolum_html({'link': kk, 'kategori': 'belediye', 'ozet': 'Şahsen başvuru.'}))

    def test_turler(self):
        self.assertEqual(ir.tur_bilgisi({'kategori': 'belediye', 'kadro': '2 İtfaiye Eri'})[1], 'belediye-memur-alimi')
        self.assertIn('İtfaiye', ir.tur_bilgisi({'kategori': 'belediye', 'kadro': '2 İtfaiye Eri'})[0])
        self.assertEqual(ir.tur_bilgisi({'kadro': '5 Engelli İşçi'})[1], 'ekpss-engelli-memur-alimi')
        self.assertEqual(ir.tur_bilgisi({'ilan_turu': 'İşçi', 'kadro': 'Sürekli İşçi'})[1], 'kamu-isci-alimi')
        self.assertEqual(ir.tur_bilgisi({'kadro': 'Gelir Uzman Yardımcısı'})[1], 'merkezi-yerlestirme-ve-kurum-ilanlari')
        self.assertEqual(ir.tur_bilgisi({'baslik': 'Muvazzaf Subay Adayı Temini'})[1], None)
        self.assertEqual(ir.tur_bilgisi({'baslik': 'Kurum ilanı'}), (None, None))

    def test_bos_ve_duyuru(self):
        self.assertEqual(ir.bolum_html({'baslik': 'Kurum ilanı'}), '')
        self.assertEqual(ir.bolum_html({'duyuru_turu': 'sonuc', 'kategori': 'belediye'}), '')
        for slug in ir.REHBER_ADI:
            import rehberler
            self.assertIn(slug, [r[0] for r in rehberler.REHBERLER])


if __name__ == '__main__':
    unittest.main()
