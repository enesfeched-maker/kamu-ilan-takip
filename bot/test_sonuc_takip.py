import unittest
from datetime import date, datetime

import sonuc_takip as st

SIMDI = datetime(2026, 11, 9, 12, tzinfo=st.TR)
ZABITA = {'id': 'a', 'link': 'https://o/', 'kurum': 'MUCUR BELEDİYE BAŞKANLIĞI', 'baslik': 'MUCUR BELEDİYE BAŞKANLIĞI - ZABITA MEMURU ALIMI',
          'son_tarih': '2026-10-20', 'ozet': 'Sonuçlar www.mucur.bel.tr adresinde.'}
ITFAIYE = dict(ZABITA, id='b', baslik='MUCUR BELEDİYE BAŞKANLIĞI - İTFAİYE ERİ ALIMI', son_tarih='2026-10-01')


class SuzgecTest(unittest.TestCase):
    def test_sonuc_duyurusu_tanir(self):
        for y in ('Personel Alımı Yarışma Sınavı Sonuçları', 'SINAVA ÇAĞRILMAYA HAK KAZANAN ADAYLAR LİSTESİ', 'Memur alımı sınav sonuç duyurusu'):
            self.assertTrue(st.sonuc_mu(y), y)

    def test_ilgisiz_duyuruyu_eler(self):
        for y in ('İhale sonuç ilanı sınav', 'Görevde Yükselme Sınav Sonuçları', 'Sınav sonucunda aday olanlar', 'Burs sonuçları açıklandı aday',
                  'Öğretim üyesi alımı sınav sonuçları', 'Duyurular', 'Seçim sonuçları aday listesi'):
            self.assertFalse(st.sonuc_mu(y), y)

    def test_tarih(self):
        self.assertEqual(st.tarih_bul('Sonuç 08.11.2026'), date(2026, 11, 8))
        self.assertEqual(st.tarih_bul('8 Kasım 2026, 17:49'), date(2026, 11, 8))
        self.assertIsNone(st.tarih_bul('Sonuçlar'))
        self.assertIsNone(st.tarih_bul('45.13.2026'))


class EslesmeTest(unittest.TestCase):
    def test_ayirt_edici_kelimeyle_baglar(self):
        self.assertEqual(st.ilana_bagla('İtfaiye eri sınav sonuçları', [ZABITA, ITFAIYE])['id'], 'b')

    def test_tek_ilan_varsa_ona_baglar(self):
        self.assertEqual(st.ilana_bagla('Sınav sonuçları', [ZABITA])['id'], 'a')

    def test_tek_ilanli_sitede_baska_kadronun_sonucu_baglanmaz(self):
        # Kurum adı ortak olsa da ('Örnek Belediyesi') duyuru başka kadroyu söylüyor: zabıta ilanının sonucu değildir.
        zabita = dict(ZABITA, kurum='Örnek Belediyesi', baslik='Örnek Belediyesi 5 Zabıta Memuru alacak')
        self.assertIsNone(st.ilana_bagla('Örnek Belediyesi itfaiye eri alımı sınav sonuçları', [zabita]))
        self.assertEqual(st.ilana_bagla('Örnek Belediyesi zabıta memuru alımı sınav sonuçları', [zabita])['id'], zabita['id'])
        self.assertEqual(st.ilana_bagla('Örnek Belediyesi memur alımı yazılı sınav sonuçları açıklandı', [zabita])['id'], zabita['id'])

    def test_kadrosu_bilinmeyen_tek_ilana_genel_baglanir(self):
        genel = {'id': 'g', 'kurum': 'Örnek Belediyesi', 'baslik': 'Örnek Belediyesi personel alım ilanı', 'son_tarih': '2026-01-01'}
        self.assertEqual(st.ilana_bagla('İtfaiye eri alımı sınav sonuçları', [genel])['id'], 'g')

    def test_belirsizse_baglamaz(self):
        self.assertIsNone(st.ilana_bagla('Sınav sonuçları', [ZABITA, ITFAIYE]))

    def test_ilk_taramada_tarihsiz_ezberlenir_yayinlanmaz(self):
        kayit, gor = st.yeni_sonuclar([('https://m/1', 'Zabıta sınav sonuçları')], [ZABITA], None)
        self.assertEqual(kayit, [])
        self.assertIn('https://m/1', gor)

    def test_sonraki_taramada_yeni_tarihsiz_alinir(self):
        kayit, _ = st.yeni_sonuclar([('https://m/1', 'Zabıta sınav sonuçları')], [ZABITA], [])
        self.assertEqual(len(kayit), 1)

    def test_son_basvurudan_eski_tarih_elenir(self):
        kayit, _ = st.yeni_sonuclar([('https://m/1', 'Zabıta sınav sonuçları 01.10.2026')], [ZABITA], None)
        self.assertEqual(kayit, [])

    def test_ilk_taramada_tarihli_alinir(self):
        kayit, _ = st.yeni_sonuclar([('https://m/1', 'Zabıta sınav sonuçları 25.10.2026')], [ZABITA], None)
        self.assertEqual(kayit[0][3], date(2026, 10, 25))


class SiteTest(unittest.TestCase):
    def test_metindeki_site(self):
        self.assertEqual(st.site_bul(ZABITA), 'www.mucur.bel.tr')

    def test_resmi_portal_kurum_sitesi_sayilmaz(self):
        self.assertEqual(st.site_bul({'kurum': 'X KURUMU', 'ozet': 'www.turkiye.gov.tr ve osym.gov.tr'}), None)

    def test_belediye_adresi_tahmini(self):
        self.assertEqual(st.site_bul({'kurum': 'ÇUBUK (ANKARA) BELEDİYE BAŞKANLIĞI'}), 'cubuk.bel.tr')

    def test_tahmin_baslikla_dogrulanir(self):
        self.assertTrue(st.site_dogrula('cubuk.bel.tr', '<title>Çubuk Belediyesi</title>', {}))
        self.assertFalse(st.site_dogrula('cubuk.bel.tr', '<title>Satılık alan adı</title>', {}))

    def test_akademik_ve_acik_ilan_izlenmez(self):
        akademik = dict(ZABITA, kategori='akademik')
        acik = dict(ZABITA, son_tarih='2026-12-01')
        self.assertEqual(st.takip_edilenler([akademik, acik], date(2026, 11, 9)), [])


class TaramaTest(unittest.TestCase):
    def test_baslik_temizlenir_ve_adres_ozu(self):
        self.assertEqual(st.baslik_temiz('Sınav Sonuçları Açıklandı 06 Kasım 2026 Ajansımız tarafından'), 'Sınav Sonuçları Açıklandı')
        self.assertEqual(st.adres_ozu('https://www.a.bel.tr/d/'), st.adres_ozu('https://a.bel.tr/d'))

    def test_tarama_ve_tekrar_engeli(self):
        sayfa = '<title>Mucur</title><a href="/s/1">Zabıta sınav sonuçları 25.10.2026</a>'
        veri = {'gorulen': {}, 'sonuclar': []}
        yeni = st.tara([ZABITA], veri, indirici=lambda a: sayfa, simdi=SIMDI, bekle=0)
        self.assertEqual(yeni[0]['adres'], 'https://mucur.bel.tr/s/1')
        self.assertEqual(st.tara([ZABITA], veri, indirici=lambda a: sayfa, simdi=SIMDI, bekle=0), [])

    def test_erisilemeyen_site_ezberi_bozmaz(self):
        def hata(_):
            raise OSError
        veri = {'gorulen': {'mucur.bel.tr': ['x']}, 'sonuclar': []}
        st.tara([ZABITA], veri, indirici=hata, simdi=SIMDI, bekle=0)
        self.assertEqual(veri['gorulen']['mucur.bel.tr'], ['x'])


class KanalTest(unittest.TestCase):
    def _veri(self, n=1):
        return {'gorulen': {}, 'sonuclar': [{'id': f'i{k}', 'adres': f'https://m/{k}', 'ilk_gorulme': f'2026-11-0{k + 1}', 'kanal': False} for k in range(n)]}

    def _ilanlar(self, n=1):
        return [dict(ZABITA, id=f'i{k}') for k in range(n)]

    def test_orijinal_mesaja_yanit_olur_ve_tekrar_gonderilmez(self):
        cagri = []
        veri = self._veri()
        gonder = lambda m, a, y, t, s: cagri.append(y) or True
        st.kanala_paylas(veri, self._ilanlar(), {'i0': 42}, 't', 's', gonder)
        st.kanala_paylas(veri, self._ilanlar(), {'i0': 42}, 't', 's', gonder)
        self.assertEqual(cagri, [42])

    def test_eski_duyuru_kanala_gitmez(self):
        veri = self._veri()
        veri['sonuclar'][0]['tarih'] = '2026-10-01'
        adet = st.kanala_paylas(veri, self._ilanlar(), {}, 't', 's', lambda *a: True, gun=date(2026, 11, 9))
        self.assertEqual(adet, 0)
        self.assertTrue(veri['sonuclar'][0]['kanal'])

    def test_ayni_ilanin_ikinci_listesi_gonderilmez(self):
        veri = self._veri(2)
        veri['sonuclar'][1]['id'] = 'i0'
        self.assertEqual(st.kanala_paylas(veri, self._ilanlar(), {}, 't', 's', lambda *a: True), 1)

    def test_aday_listesi_ayri_soylenir(self):
        self.assertIn('aday listesi', st.kanal_metni(ZABITA, 'Sözlü sınava hak kazanan adaylar'))
        self.assertIn('sonuç duyurusu', st.kanal_metni(ZABITA, 'Sınav sonuçları'))

    def test_calisma_basina_sinir(self):
        adet = st.kanala_paylas(self._veri(5), self._ilanlar(5), {}, 't', 's', lambda *a: True)
        self.assertEqual(adet, st.EN_COK_KANAL)

    def test_basarisiz_gonderim_sonra_denenir(self):
        veri = self._veri()
        st.kanala_paylas(veri, self._ilanlar(), {}, 't', 's', lambda *a: False)
        self.assertFalse(veri['sonuclar'][0]['kanal'])


if __name__ == '__main__':
    unittest.main()
