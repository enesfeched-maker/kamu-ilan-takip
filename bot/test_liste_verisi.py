import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import liste_verisi as lv
from site_uret import TR

KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=%s'
SIMDI = datetime(2026, 10, 4, 18, 30, tzinfo=TR)


def uid(n):
    return '%08d-1111-4111-8111-111111111111' % n


def ilan(n, **ek):
    return {'id': KK % uid(n), 'link': KK % uid(n), 'baslik': 'Test Üniversitesi Alım İlanı', 'kurum': 'Test Üniversitesi',
            'kadro': '2 Memur', 'son_tarih': '2026-10-10', 'ogrenim': ['lisans'], 'iller': ['Ankara'], **ek}


def puan_klasoru(satirlar):
    d = Path(tempfile.mkdtemp())
    (d / 'puanlar').mkdir()
    (d / 'puanlar' / 'lisans.json').write_text(json.dumps({'duzey': 'lisans', 'donemler': {'2024-1': [{'unvan': 'ESKİ', 'min': 1}], '2025-2': satirlar[:3], '2026-1': satirlar[3:]}}), encoding='utf-8')
    return d


class BaslikTests(unittest.TestCase):
    def test_baslik_temiz(self):
        self.assertEqual(lv.baslik_temiz('İlk Defa Atanmak Üzere Vhki Alımı İlanı'), 'VHKİ alımı')
        self.assertEqual(lv.baslik_temiz('Memur Sınav İlanı'), 'Memur sınavı')
        self.assertEqual(lv.baslik_temiz('Büro Personeli İlanı'), 'Büro Personeli')
        self.assertEqual(lv.baslik_temiz('.net Uzmanı'), '.NET Uzmanı')
        self.assertEqual(lv.baslik_temiz('İcra Müdür ve İcra Müdür Yardımcısı Alacak.'), 'İcra Müdür ve İcra Müdür Yardımcısı')
        self.assertEqual(lv.baslik_temiz('1 Sözleşmeli Pilot (Uçak) Temin Edecektir'), '1 Sözleşmeli Pilot (Uçak)')

    def test_sbb_baslik_sonu_ayrinti_basliginda(self):
        from site_uret import detail_page
        item = {'id': 'sbb-46734a52a4045202658b0bf7', 'baslik': 'ADALET BAKANLIĞI - 150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.',
                'kurum': 'ADALET BAKANLIĞI', 'kadro': '150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.', 'kaynak_turu': 'sbb',
                'link': 'https://kamuilan.sbb.gov.tr/', 'son_tarih': None}
        html = detail_page(item, simdi=SIMDI)[1]
        self.assertIn('<h1 id="dh-baslik">İcra Müdür ve İcra Müdür Yardımcısı</h1>', html)


class DonemTests(unittest.TestCase):
    REF = datetime(2026, 10, 5, 17, 22, tzinfo=TR)

    def test_ayni_ay_ve_ay_gecisi(self):
        self.assertEqual(lv.donem_tarihleri('( 5 Ekim - 20 Ekim)', self.REF), (date(2026, 10, 5), date(2026, 10, 20)))
        self.assertEqual(lv.donem_tarihleri('( 24 Eylül - 11 Ekim)', self.REF), (date(2026, 9, 24), date(2026, 10, 11)))
        self.assertEqual(lv.donem_tarihleri('( 20 Ekim - 26 Ekim)', self.REF), (date(2026, 10, 20), date(2026, 10, 26)))

    def test_yil_gecisi(self):
        ref = datetime(2026, 12, 20, 10, 0, tzinfo=TR)
        self.assertEqual(lv.donem_tarihleri('( 22 Aralık - 5 Ocak)', ref), (date(2026, 12, 22), date(2027, 1, 5)))
        self.assertEqual(lv.donem_tarihleri('( 5 Ocak - 12 Ocak)', ref), (date(2027, 1, 5), date(2027, 1, 12)))

    def test_cozulemeyen_donem_none(self):
        for s in ('', None, 'Resmî ilanda', '( 31 Şubat - 5 Mart)', '(5 - 20 Ekim)'):
            with self.subTest(s):
                self.assertIsNone(lv.donem_tarihleri(s, self.REF))

    def test_donem_tamamla(self):
        sbb = {'kaynak_turu': 'sbb', 'donem': '( 20 Ekim - 26 Ekim)', 'ilk_gorulme': '2026-10-05T17:22:54+03:00', 'son_tarih': None}
        t = lv.donem_tamamla(sbb)
        self.assertEqual((t['son_tarih'], t['baslangic_zaman'][:10]), ('2026-10-26', '2026-10-20'))
        self.assertIsNone(sbb['son_tarih'], 'kayıt değişmez, kopya döner')
        self.assertEqual(lv.donem_tamamla({**sbb, 'son_tarih': '2026-10-30'})['son_tarih'], '2026-10-30')
        self.assertIsNone(lv.donem_tamamla({**sbb, 'kaynak_turu': 'iskur'})['son_tarih'])
        self.assertEqual(lv.kayit(sbb | {'id': 'sbb-' + 'a' * 24, 'baslik': 'X - 1 MEMUR ALACAK', 'kurum': 'X', 'kadro': '1 MEMUR ALACAK', 'link': 'https://kamuilan.sbb.gov.tr/'}, None, {}, SIMDI)['durum'], 'upcoming')


class IlTests(unittest.TestCase):
    def test_il_bul(self):
        self.assertEqual(lv.il_bul({'iller': ['Ankara']}), 'Ankara')
        self.assertEqual(lv.il_bul({'iller': ['Ankara', 'İzmir', 'Bursa']}), 'Ankara +2')

    def test_belediyede_addan_il(self):
        self.assertEqual(lv.il_bul({'kurum': 'Kırşehir Mucur Belediyesi'}), 'Kırşehir')

    def test_parantezli_il(self):
        self.assertEqual(lv.il_bul({'kurum': 'SUBAŞI (YALOVA) BELEDİYE BAŞKANLIĞI'}), 'Yalova')
        self.assertEqual(lv.il_bul({'kurum': 'Test Birimi (Konya) Müdürlüğü'}), 'Konya')

    def test_harita_ilsiz_belediyeyi_cozer(self):
        ilanlar = [{'kurum': 'Ardahan Hanak Belediyesi'}, {'kurum': 'HANAK BELEDİYE BAŞKANLIĞI'}, {'kurum': 'Bilinmez Belediyesi'}]
        harita = lv.il_haritasi(ilanlar)
        self.assertEqual(lv.il_bul(ilanlar[1], harita), 'Ardahan')
        self.assertEqual(lv.il_bul(ilanlar[1]), '')
        self.assertEqual(lv.il_bul(ilanlar[2], harita), '')

    def test_yer_kisa_yedek(self):
        self.assertEqual(lv.il_bul({'yer': 'Bakanlık Merkez / Ankara'}), 'Ankara')


class PuanTuruTests(unittest.TestCase):
    def test_puan_turleri(self):
        self.assertEqual(lv.puan_turleri({'ozet': 'KPSS P93 ve KPSS P3 puanı', 'sartlar': [{'metin': 'KPSS P 94'}]}), ['P3', 'P93', 'P94'])

    def test_yok(self):
        self.assertEqual(lv.puan_turleri({'ozet': 'KPSS şartı yok'}), [])


class TabanTests(unittest.TestCase):
    def satirlar(self, n):
        return [{'unvan': 'MEMUR', 'min': 70 + i, 'kurum': 'X'} for i in range(n)]

    def test_en_az_bes_kayit(self):
        t = lv.taban_tablolari(puan_klasoru(self.satirlar(5)))
        r = lv.taban_ref(t, 'lisans', ['Memur'])
        self.assertEqual((r['n'], r['medyan'], r['donem']), (5, 72.0, '2025-2/2026-1'))
        self.assertEqual(r['duzey'], 'lisans')

    def test_dort_kayit_yetmez(self):
        t = lv.taban_tablolari(puan_klasoru(self.satirlar(4)))
        self.assertIsNone(lv.taban_ref(t, 'lisans', ['Memur']))

    def test_eski_donem_sayilmaz_ve_parantez_atilir(self):
        t = lv.taban_tablolari(puan_klasoru(self.satirlar(6)))
        self.assertIsNone(lv.taban_ref(t, 'lisans', ['Eski']))
        self.assertIsNotNone(lv.taban_ref(t, 'lisans', ['Memur (4/B)']))
        self.assertIsNone(lv.taban_ref(t, 'onlisans', ['Memur']))


class TakvimTests(unittest.TestCase):
    def test_sayim_ve_pencere(self):
        k = [{'son_tarih': '2026-10-05'}, {'son_tarih': '2026-10-05'}, {'son_tarih': '2026-10-04'}, {'son_tarih': '2026-10-03'},
             {'son_tarih': '2027-01-01'}, {'son_tarih': ''}, {}]
        self.assertEqual(lv.takvim(k, SIMDI), {'2026-10-04': 1, '2026-10-05': 2})


class ListeTests(unittest.TestCase):
    def test_liste_uret(self):
        docs = puan_klasoru([{'unvan': 'MEMUR', 'min': 70 + i} for i in range(5)])
        ilanlar = [
            ilan(1, ilk_gorulme='2026-10-04T08:00:00+03:00', ozet='KPSS P3', ilan_turu='Sözleşmeli Personel İlanları', kategori='lisans'),
            ilan(2, son_tarih='2026-09-01'),                       # süresi geçmiş
            ilan(3, iptal_edildi=True),
            ilan(4, duyuru_turu='Düzeltme'),
            ilan(5, baslangic_zaman='2026-10-05T01:00:00+03:00'),  # yakında
        ]
        v = lv.liste_uret(ilanlar, {uid(1): {'logo': 'ilan/logo/ab.webp', 'kurum_slug': 'test'}}, docs, SIMDI, '2026-10-04T17:24:28+03:00')
        self.assertEqual([k['key'] for k in v['ilanlar']], [uid(1), uid(5)])
        a = v['ilanlar'][0]
        self.assertEqual((a['il'], a['puan_turleri'], a['logo'], a['durum']), ('Ankara', ['P3'], 'ilan/logo/ab.webp', 'soon'))
        self.assertEqual(a['taban_ref']['lisans']['n'], 5)
        self.assertNotIn('duzey', a['taban_ref']['lisans'])
        self.assertEqual(a['unvanlar'], ['memur'])
        self.assertEqual((a['ilan_turu'], a['kategori']), ('Sözleşmeli Personel İlanları', 'lisans'))
        self.assertNotIn('ilan_turu', v['ilanlar'][1])
        self.assertEqual(v['sayilar'], {'acik': 2, 'kadro': 4, 'bugun_yeni': 1})
        self.assertEqual(v['takvim'], {'2026-10-10': 2})
        self.assertEqual(v['guncelleme'], '2026-10-04T17:24:28+03:00')
        self.assertEqual(v['ilanlar'][1]['durum'], 'upcoming')

    def test_akademik_haric(self):
        docs = puan_klasoru([])
        self.assertEqual(lv.liste_uret([ilan(1, kategori='akademik', baslik='Profesör Alımı')], {}, docs, SIMDI)['ilanlar'], [])

    def test_uret_dosya_yazar(self):
        docs = puan_klasoru([])
        lv.uret([ilan(1)], {}, docs, SIMDI)
        self.assertEqual(json.loads((docs / 'liste.json').read_text(encoding='utf-8'))['sayilar']['acik'], 1)


def kayit_ogr(**ek):
    """Düzey çıkarımını sınamak için: metinde düzey olmayan, açık bir ilanın ince kaydı."""
    return lv.kayit(ilan(1, ogrenim=[], **ek), None, {}, SIMDI)


class OgrenimCikarimTests(unittest.TestCase):
    def test_puan_turu_duzeyi_ima_eder(self):
        k = kayit_ogr(ozet='2024 yılı KPSS B grubu P3 puanının %70')
        self.assertEqual(k['ogrenim'], ['lisans'])
        self.assertTrue(k['ogrenim_cikarim'])
        self.assertEqual(kayit_ogr(ozet='KPSS P93 puanı')['ogrenim'], ['onlisans'])
        self.assertEqual(kayit_ogr(ozet='KPSS P94 puanı')['ogrenim'], ['ortaogretim'])
        self.assertEqual(kayit_ogr(ozet='KPSS P25 puanı (A grubu)')['ogrenim'], ['lisans'])

    def test_metinden_gelen_duzey_silinmez_birlesir(self):
        k = lv.kayit(ilan(1, ogrenim=['onlisans'], ozet='KPSS P3 puanı'), None, {}, SIMDI)
        self.assertEqual(k['ogrenim'], ['lisans', 'onlisans'])
        self.assertTrue(k['ogrenim_cikarim'])
        tam = lv.kayit(ilan(1, ogrenim=['lisans'], ozet='KPSS P3 puanı'), None, {}, SIMDI)
        self.assertEqual(tam['ogrenim'], ['lisans'])
        self.assertNotIn('ogrenim_cikarim', tam)

    def test_kpss_lisans_ifadesi(self):
        self.assertEqual(kayit_ogr(ozet='KPSS Lisans sınavına girmiş olmak')['ogrenim'], ['lisans'])

    def test_lisans_unvanlari(self):
        for baslik in ('TSK 2026 Yılı Hukuk Sınıfı Muvazzaf Subay Adayı Temini', 'Gelir Uzman Yardımcılığı Sınav İlanı',
                       '135 MESLEK PERSONELİ ALACAK', 'Sözleşmeli Bilişim Personeli Alım İlanı', '1 Mühendis'):
            with self.subTest(baslik):
                self.assertEqual(kayit_ogr(baslik=baslik, kadro=baslik)['ogrenim'], ['lisans'])

    def test_belirsiz_unvanlar_bos_kalir(self):
        for baslik in ('Zabıta Memuru alımı', 'İtfaiye Eri alımı', '4/B Sözleşmeli Personel', '1 Sözleşmeli Pilot (Uçak)', 'Bilgisayar İşletmeni'):
            with self.subTest(baslik):
                k = kayit_ogr(baslik=baslik, kadro=baslik)
                self.assertEqual(k['ogrenim'], [])
                self.assertNotIn('ogrenim_cikarim', k)

    def test_unvan_kurali_yalniz_kisa_metinde(self):
        self.assertEqual(kayit_ogr(ozet='Mimarlık ve mühendislik birimlerinde görev yapacak personel')['ogrenim'], [])

    def test_yeterlik_sinavi_kurum_ici(self):
        k = kayit_ogr(baslik='MUHASEBE UZMANLIĞI YETERLİK SINAVI DUYURUSU', ozet='KPSS P3')
        self.assertTrue(k['kurum_ici'])
        self.assertEqual(k['ogrenim'], [])
        self.assertNotIn('kurum_ici', kayit_ogr(baslik='Memur Sınavı Duyurusu'))

    def test_fakulte_sarti_lisans_ve_bolum_kisiti(self):
        sart = {'kadro': 'Belgede belirtilen koşullar', 'metin': 'c) Hukuk fakültesi, adalet meslek yüksekokulu, meslek yüksekokullarının adalet bölümü veya adalet meslek eğitimi ön lisans programı mezunu olmak,'}
        k = lv.kayit(ilan(1, ogrenim=['onlisans'], sartlar=[sart]), None, {}, SIMDI)
        self.assertEqual(k['ogrenim'], ['lisans', 'onlisans'])
        self.assertTrue(k['bolum_kisiti'])
        self.assertNotIn('bolum_kisiti', kayit_ogr(ozet='Lise mezunu olmak'))

    def test_gorevde_yukselme_ve_unvan_degisikligi_kurum_ici(self):
        for baslik in ('Görevde Yükselme Sınavı İlanı (Şube Müdürü)', 'Unvan Değişikliği Sınavı Duyurusu'):
            with self.subTest(baslik):
                self.assertTrue(kayit_ogr(baslik=baslik)['kurum_ici'])

    def test_siniflandirici_kpss_b_p3(self):
        from siniflandir import ogrenim_seviyeleri
        self.assertEqual(ogrenim_seviyeleri({'ozet': 'KPSS B grubu P3 puanı'}), ['lisans'])

    def test_taban_ref_cikarilan_duzey_icin_hesaplanir(self):
        docs = puan_klasoru([{'unvan': 'Memur', 'min': 70 + i} for i in range(9)])
        k = lv.kayit(ilan(1, ogrenim=[], ozet='KPSS P3 puanı', kadro='2 Memur'), None, lv.taban_tablolari(docs), SIMDI)
        self.assertIn('lisans', k['taban_ref'])

    def test_kopya_grubunda_birlesim(self):
        docs = puan_klasoru([])
        birincil = ilan(1, ogrenim=[], iller=[])
        ikincil = ilan(2, ogrenim=['lisans'], iller=['Ankara'], ozet='KPSS P3 puanı')
        v = lv.liste_uret([birincil, ikincil], {}, docs, SIMDI, kopyalar={'kopya_of': {ikincil['id']: birincil['id']}})
        p = next(k for k in v['ilanlar'] if k['key'] == uid(1))
        self.assertEqual((p['ogrenim'], p['puan_turleri'], p['iller']), (['lisans'], ['P3'], ['Ankara']))
        self.assertEqual(p['il'], 'Ankara')


class IlCikarimTests(unittest.TestCase):
    def test_kurum_adindaki_il(self):
        self.assertEqual(lv.il_bul({'kurum': 'Bolu Abant İzzet Baysal Üniversitesi'}), 'Bolu')
        self.assertEqual(lv.il_bul({'kurum': 'İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜ (İETT)'}), 'İstanbul')
        k = lv.kayit(ilan(1, kurum='Bolu Abant İzzet Baysal Üniversitesi', iller=[]), None, {}, SIMDI)
        self.assertEqual((k['il'], k['iller']), ('Bolu', ['Bolu']))

    def test_bilinen_kurum_haritasi(self):
        self.assertEqual(lv.il_bul({'kurum': 'Tarsus Üniversitesi Rektörlüğü'}), 'Mersin')
        self.assertEqual(lv.il_bul({'kurum': 'TÜRKİYE TAŞKÖMÜRÜ KURUMU GENEL MÜDÜRLÜĞÜ'}), 'Zonguldak')

    def test_ozetten_il(self):
        self.assertEqual(lv.il_bul({'kurum': 'Test Kurumu', 'ozet': '(İstanbul) istihdam edilmek üzere'}), 'İstanbul')
        self.assertEqual(lv.il_bul({'kurum': 'Test Kurumu', 'ozet': 'İstanbul’da görev yapmak üzere 3 personel'}), 'İstanbul')
        self.assertEqual(lv.il_bul({'kurum': 'Test Kurumu', 'ozet': '(Ankara) ve (İzmir) için'}), '')

    def test_turkiye_geneli_ulusal_kalir(self):
        self.assertEqual(lv.il_bul({'kurum': 'Test Kurumu', 'yer': 'Türkiye Geneli'}), 'Türkiye Geneli')
        k = lv.kayit(ilan(1, kurum='Test Kurumu', iller=[], yer='Türkiye Geneli'), None, {}, SIMDI)
        self.assertEqual(k['iller'], [])

    def test_ayrinti_sayfasi_iller_ozniteligi(self):
        import site_uret
        item = ilan(1, iller=['Antalya', 'Burdur'], ozet='x')
        html = site_uret.detail_page(item)[1]
        self.assertNotIn('data-kurum-ici', html)
        self.assertIsNone(site_uret.detail_page(ilan(2, baslik='Hazine Uzmanlığı Yeterlik Sınavı Duyurusu', ogrenim=[])),
                          'kurum içi ilan sitede gösterilmez (akademik gibi)')


if __name__ == '__main__':
    unittest.main()
