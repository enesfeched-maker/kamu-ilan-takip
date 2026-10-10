"""Denetim M3/M7/M9/M12/L1/L2 ve iptal duyurusu metni."""
import unittest
from datetime import date, datetime
from unittest.mock import patch

import basvuru_penceresi as bp
import belge_alanlari as ba
import ilan_bot
import kopya
import kurum_sayfasi as ks
import liste_verisi as lv
import site_uret
from site_uret import TR

SIMDI = datetime(2026, 10, 5, 19, 0, tzinfo=TR)
GELIR = ('- Sınava ön başvurular 20-22 Ekim 2026 tarihleri arasında, nihai başvurular ise 30 Ekim - 3 Kasım 2026 tarihleri arasında '
         'alınacaktır. 30 Ekim - 3 Kasım 2026 tarihleri arasında ÖSYM’ye başvurusunu yapamayan adaylar için Geç Başvuru Günü 6 Kasım 2026 tarihi olarak belirlenmiştir.')
TTK4 = ('Türkiye Taşkömürü Kurumu işçi alımı. Yönetmelik hükümlerine göre, Bartın İş Kurumu aracılığı ile toplam 4 işçi alımı yapılacaktır. '
        'Talebimize istinaden Bartın İş Kurumunca 05.10.2026 - 09.10.2026 tarihleri arasında 5 günlük ilana çıkılacaktır. ' + 'Açıklama. ' * 10 +
        '-Bartın ilinde ikamet ediyor olmak, -Ortaöğretim mezunu olmak.')
TTK57 = TTK4.replace('Bartın', 'Zonguldak').replace('toplam 4', 'toplam 57')


class TtkIlTests(unittest.TestCase):
    def test_bartin_ve_zonguldak(self):
        self.assertEqual(ba.alanlar([TTK4], {'kadro': '4 SÜREKLİ İŞÇİ ALACAK', 'ilan_turu': 'İşçi'})['yer'], 'Bartın')
        self.assertEqual(ba.alanlar([TTK57], {'kadro': '57 SÜREKLİ İŞÇİ ALACAK', 'ilan_turu': 'İşçi'})['yer'], 'Zonguldak')

    def test_kayit_ili_belgeden(self):
        i = {'id': 'sbb-' + 'a' * 24, 'kaynak_turu': 'sbb', 'baslik': 'TÜRKİYE TAŞKÖMÜRÜ KURUMU GENEL MÜDÜRLÜĞÜ - 4 SÜREKLİ İŞÇİ ALACAK',
             'kurum': 'TÜRKİYE TAŞKÖMÜRÜ KURUMU GENEL MÜDÜRLÜĞÜ', 'kadro': '4 SÜREKLİ İŞÇİ ALACAK', 'ilan_turu': 'İşçi', 'link': 'https://kamuilan.sbb.gov.tr/',
             'son_tarih': '2099-10-09', 'belge_sha256': 'f' * 64, 'sbb_detay_surumu': 5}
        lv._BELGE_ONBELLEK.clear()
        with patch('sbb_detay.belge_sayfalari', return_value=[TTK4]):
            k = lv.kayit(lv.tamamla(i), None, {}, SIMDI)
        self.assertEqual(k['il'], 'Bartın')


class GrupSaatTests(unittest.TestCase):
    def test_saat_ikizden_gelir(self):
        p = {'key': 'a', 'son_tarih': '2026-10-06', 'ogrenim': [], 'puan_turleri': [], 'iller': []}
        i = {'key': 'b', 'son_tarih': '2026-10-06', 'son_zaman': '2026-10-06T17:00:00+03:00', 'baslangic_zaman': '2026-10-01T00:00:00+03:00',
             'ogrenim': [], 'puan_turleri': [], 'iller': []}
        lv.grup_birlestir(p, [i])
        self.assertEqual((p['son_zaman'], p['baslangic_zaman']), (i['son_zaman'], i['baslangic_zaman']))

    def test_farkli_gunun_saati_alinmaz_ve_mevcut_korunur(self):
        p = {'key': 'a', 'son_tarih': '2026-10-06', 'son_zaman': '2026-10-06T12:00:00+03:00', 'ogrenim': [], 'puan_turleri': [], 'iller': []}
        i = {'key': 'b', 'son_tarih': '2026-10-07', 'son_zaman': '2026-10-07T17:00:00+03:00', 'ogrenim': [], 'puan_turleri': [], 'iller': []}
        lv.grup_birlestir(p, [i])
        self.assertEqual(p['son_zaman'], '2026-10-06T12:00:00+03:00')
        q = {'key': 'c', 'son_tarih': '2026-10-06', 'ogrenim': [], 'puan_turleri': [], 'iller': []}
        lv.grup_birlestir(q, [i])
        self.assertNotIn('son_zaman', q)


class AsamaliBasvuruTests(unittest.TestCase):
    def test_nihai_bitis_kazanir(self):
        p = bp.pencere(GELIR, date(2026, 10, 1))
        self.assertEqual((p['baslangic'], p['bitis']), (date(2026, 10, 20), date(2026, 11, 3)))
        row = {'kaynak_turu': 'sbb', 'son_tarih': '2026-10-22', 'basvuru_notu': GELIR}
        yeni = bp.uygula(row, [GELIR], date(2026, 10, 1))
        self.assertEqual(yeni['son_tarih'], '2026-11-03')
        self.assertEqual(bp.asama_yazisi(yeni['basvuru_asamalari']), 'Ön başvuru 20–22 Ekim · Nihai başvuru 30 Ekim–3 Kasım')

    def test_tek_asama_degismez(self):
        self.assertNotIn('basvuru_asamalari', bp.uygula({'son_tarih': '2026-10-05'}, ['başvurular, 01/10/2026 – 05/10/2026 tarihleri arasında'], date(2026, 10, 1)))

    def test_detay_sayfasi_satiri_ve_kopya(self):
        i = {'id': 'sbb-' + 'a' * 24, 'kaynak_turu': 'sbb', 'baslik': 'GELİR İDARESİ BAŞKANLIĞI - 860 GELİR UZMAN YARDIMCISI ALACAK',
             'kurum': 'GELİR İDARESİ BAŞKANLIĞI', 'kadro': '860 GELİR UZMAN YARDIMCISI ALACAK', 'link': 'https://kamuilan.sbb.gov.tr/',
             'son_tarih': '2026-10-22', 'donem': '( 20 Ekim - 22 Ekim)', 'basvuru_notu': GELIR, 'ilk_gorulme': '2026-10-01T10:00:00+03:00'}
        t = lv.tamamla(i)
        self.assertEqual(t['son_tarih'], '2026-11-03')
        html = site_uret.detail_page(t, simdi=SIMDI)[1]
        self.assertIn('Ön başvuru 20–22 Ekim · Nihai başvuru 30 Ekim–3 Kasım', html)
        iskur = {'id': 'iskur-' + 'b' * 24, 'kaynak_turu': 'iskur', 'baslik': 'Gelir İdaresi Başkanlığı Gelir Uzman Yardımcısı Alım İlanı',
                 'kurum': 'Gelir İdaresi Başkanlığı', 'kadro': '860 GELİR UZMAN YARDIMCISI', 'son_tarih': '2026-10-23', 'yer': 'Ankara',
                 'link': 'https://www.iskur.gov.tr/medya/x/g.pdf', 'kaynaklar': [{'ad': 'İŞKUR', 'link': 'https://www.iskur.gov.tr/medya/x/g.pdf'}],
                 'ilk_gorulme': '2026-10-01T10:00:00+03:00', 'ilan_turu': 'Uzman'}
        self.assertTrue(kopya._asamada(t, iskur))
        self.assertEqual(len(kopya.kopya_bul([t, iskur])['kopya_of']), 1)


class BelirsizTests(unittest.TestCase):
    def kk(self, **ek):
        u = 'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111'
        return {'id': u, 'link': u, 'baslik': 'BURDUR MEHMET AKİF ERSOY ÜNİVERSİTESİ - Sözleşmeli Personel', 'kurum': 'BURDUR MEHMET AKİF ERSOY ÜNİVERSİTESİ',
                'ilk_gorulme': '2026-09-22T10:00:00+03:00', 'kadro': '2 TEKNİSYEN', **ek}

    def test_eski_tarihsiz_detaysiz_belirsiz(self):
        self.assertEqual(ks.durum(self.kk(), SIMDI), ('Tarih doğrulanamadı', 'belirsiz'))

    def test_taze_ya_da_detayli_ya_da_tarihli_degil(self):
        self.assertEqual(ks.durum(self.kk(ilk_gorulme='2026-10-01T10:00:00+03:00'), SIMDI)[1], 'none')
        self.assertEqual(ks.durum(self.kk(detay_guncelleme='2026-10-05T10:00:00+03:00'), SIMDI)[1], 'none')
        self.assertEqual(ks.durum(self.kk(son_tarih='2026-10-30'), SIMDI)[1], 'ok')
        self.assertEqual(ks.durum(self.kk(kaynak_turu='csb', id='csb-123456', link='https://yerelyonetimler.csb.gov.tr/x'), SIMDI)[1], 'none')

    def test_listede_ama_sayilmaz(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as kok:
            v = lv.liste_uret([self.kk()], {}, Path(kok), SIMDI, None, {})
        self.assertEqual(len(v['ilanlar']), 1)
        self.assertEqual(v['ilanlar'][0]['durum'], 'belirsiz')
        self.assertEqual((v['sayilar']['acik'], v['sayilar']['kadro']), (0, 0))
        self.assertIn('tarih doğrulanamadı', ks.satir_html(v['ilanlar'][0], SIMDI))


class BaslikTests(unittest.TestCase):
    def test_karisik_buyuk_harf(self):
        self.assertEqual(ilan_bot.okunakli_baslik('57 SüREKLİ İŞÇİ ALACAK'), '57 Sürekli İşçi Alacak')
        self.assertEqual(ilan_bot.okunakli_baslik('ÖĞRETMEN/MÜHENDİS ALIMI'), 'Öğretmen/Mühendis Alımı')
        self.assertEqual(ilan_bot.okunakli_baslik('BDDK UZMAN YARDIMCISI'), 'BDDK Uzman Yardımcısı')
        self.assertEqual(ilan_bot.okunakli_baslik('Sürekli İşçi alımı'), 'Sürekli İşçi alımı')

    def test_site_kisaltma_korunur(self):
        self.assertEqual(site_uret._duzgun('BDDK UZMAN YARDIMCISI'), 'BDDK Uzman Yardımcısı')
        self.assertEqual(site_uret._duzgun('57 SüREKLİ İŞÇİ ALACAK'), '57 Sürekli İşçi Alacak')
        self.assertEqual(site_uret._duzgun('ZABITA MEMURU'), 'Zabıta Memuru')

    def test_unvan_tekrari(self):
        i = {'id': 'x', 'baslik': 'Y - alım', 'kurum': 'Y', 'kadro': '2 DESTEK PERSONELİ • 3 DESTEK PERSONEL • 1 TEKNİSYEN', 'son_tarih': '2026-10-30'}
        k = lv.kayit(i, None, {}, SIMDI)
        self.assertEqual(k['unvanlar'], ['destek personeli', 'teknisyen'])


class IptalDuyurusuTests(unittest.TestCase):
    ATU = {'id': 'sbb-' + '8' * 24, 'kaynak_turu': 'sbb', 'kaynak': 'SBB Kamu İlan', 'duyuru_turu': 'İptal duyurusu',
           'baslik': 'ADANA ALPARSLAN TÜRKEŞ BİLİM VE TEKNOLOJİ ÜNİVERSİTESİ - İPTAL İLANI', 'kurum': 'ADANA ALPARSLAN TÜRKEŞ BİLİM VE TEKNOLOJİ ÜNİVERSİTESİ',
           'duyuru_cumlesi': 'Adana Alparslan Türkeş Bilim ve Teknoloji Üniversitesi Rektörlüğünden: İPTAL İLANI 20.09.2026 tarihli ve 33376 sayılı Resmi '
                             'Gazete’de yayımlanan ve aşağıda belirtilen 6 Sıra Nolu Havacılık Yönetimi Anabilim Dalı 1 (bir) adet Araştırma Görevlisi kadrosu '
                             'ilanımız iptal edilmiştir.'}

    def test_akademik_iptal_sessiz(self):
        k = ilan_bot.duyuru_karari(self.ATU, [self.ATU], {}, {}, date(2026, 10, 3), set())
        self.assertEqual(k['islem'], 'sessiz')

    def test_cift_ilani_yok(self):
        d = dict(self.ATU, kurum='ÖRNEK BELEDİYESİ', baslik='ÖRNEK BELEDİYESİ - İPTAL İLANI',
                 duyuru_cumlesi='Örnek Belediyesinden: İPTAL İLANI 20.09.2026 tarihli ilanımızda yayımlanan aşağıda belirtilen İptal İlanı ilanı iptal edilmiştir.')
        for yanit in (True, False):
            self.assertNotIn('ilanı ilanı', ilan_bot.duyuru_metni(d, yanit, True).lower())


if __name__ == '__main__':
    unittest.main()
