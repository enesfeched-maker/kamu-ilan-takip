"""Düzeltme duyurularının orijinal ilana bağlanması (15 Ekim 2026)."""
import unittest
from datetime import date, datetime, timedelta, timezone

import duzeltme
import liste_verisi
import site_uret

TR = timezone(timedelta(hours=3))
BUGUN = date(2026, 10, 15)
MALAZGIRT = ('Muş İli Malazgirt Belediye Başkanlığından: DÜZELTME İLANI 20/09/2026 tarihli ve 33376 sayılı Resmî Gazete’de '
             'yayımlanan İlk Defa Atanmak Üzere Memur Alım İlanında yer alan; BAŞVURU YERİ, TARİHİ, ŞEKLİ VE SÜRESİ: 4 üncü maddesinin, '
             'a) fıkrası “Elektronik ortamda başvurular, 02/11/2026-04/11/202 6 tarihleri arasında istenilen belgeler eklenmek suretiyle '
             'Belediyemizin malazgirt-belediyesi@hotmail.com mail adresine yapılacaktır.” şeklinde düzeltilmiştir.')


def ilan(kimlik, kadro='2 MEMUR ALACAK', **ek):
    r = {'id': kimlik, 'baslik': 'MALAZGİRT BELEDİYE BAŞKANLIĞI - ' + kadro, 'kurum': 'MALAZGİRT BELEDİYE BAŞKANLIĞI',
         'yer': 'Muş', 'kadro': kadro, 'link': 'https://kamuilan.sbb.gov.tr/', 'son_tarih': '2026-10-20',
         'ilk_gorulme': '2026-09-21T10:00:00+03:00', 'kaynak_turu': 'sbb'}
    r.update(ek)
    return r


def duyuru(kimlik='sbb-d', **ek):
    r = ilan(kimlik, kadro='', baslik='MALAZGİRT BELEDİYE BAŞKANLIĞI - DÜZELTME İLANI', duyuru_turu='Düzeltme / süre değişikliği',
             duyuru_cumlesi=MALAZGIRT, son_tarih='2026-11-04', ilk_gorulme='2026-10-08T10:00:00+03:00',
             link='https://kamuilan.sbb.gov.tr/Ilan/1')
    r.update(ek)
    return r


class Ayristirma(unittest.TestCase):
    def test_bolunmus_tarih_ve_tur(self):
        self.assertEqual(duzeltme.degisiklik(duyuru()), ('tarih', date(2026, 11, 4)))
        self.assertIn('04/11/2026', duzeltme._bitisik(duzeltme.duzeltilen_kisim(duyuru())))

    def test_tirnaksiz_ya_da_tarihsiz(self):
        self.assertEqual(duzeltme.degisiklik(duyuru(duyuru_cumlesi='Düzeltme ilanı yayımlanmıştır.')), ('diger', None))
        adres = duyuru(duyuru_cumlesi='4 üncü madde “Başvurular şahsen yazı işleri müdürlüğüne yapılacaktır.” şeklinde düzeltilmiştir.')
        self.assertEqual(duzeltme.degisiklik(adres), ('basvuru', None))
        kadro = duyuru(duyuru_cumlesi='Tabloda “Zabıta Memuru kadrosu için KPSS P3 puanı 70 olarak” şeklinde düzeltilmiştir.')
        self.assertEqual(duzeltme.degisiklik(kadro), ('diger', None))


class Baglama(unittest.TestCase):
    def test_tek_ilana_baglanir_tarih_guncellenir_ve_tekrar_ayni(self):
        o, d = ilan('sbb-o'), duyuru()
        liste = [o, d]
        self.assertEqual(duzeltme.uygula(liste, BUGUN, {}), 1)
        self.assertEqual(o['son_tarih'], '2026-11-04')
        self.assertEqual(o['ilk_son_tarih'], '2026-10-20')
        self.assertEqual(d['duzeltme_of'], 'sbb-o')
        self.assertEqual(o['duzeltmeler'][0]['tur'], 'tarih')
        self.assertNotIn('202 6', o['duzeltmeler'][0]['cumle'])
        duzeltme.uygula(liste, BUGUN, {})   # her taramada yeniden: sonuç aynı, tarih bir kez kaydırılır
        self.assertEqual((o['son_tarih'], o['ilk_son_tarih'], len(o['duzeltmeler'])), ('2026-11-04', '2026-10-20', 1))

    def test_kaynak_yeni_tarih_yazdiysa_eski_geri_konmaz(self):
        o, d = ilan('sbb-o'), duyuru()
        duzeltme.uygula([o, d], BUGUN, {})
        o['son_tarih'] = '2026-12-01'   # kaynak bu arada başka bir tarih yazdı
        duzeltme.uygula([o, d], BUGUN, {})
        self.assertEqual(o['son_tarih'], '2026-11-04')
        self.assertEqual(o['ilk_son_tarih'], '2026-12-01')

    def test_farkli_iki_ilan_varsa_baglanmaz(self):
        a, b, d = ilan('sbb-a'), ilan('sbb-b', kadro='3 ZABITA MEMURU ALACAK', son_tarih='2026-10-30'), duyuru()
        self.assertEqual(duzeltme.uygula([a, b, d], BUGUN, {}), 0)
        self.assertNotIn('duzeltmeler', a)
        self.assertEqual(a['son_tarih'], '2026-10-20')
        self.assertNotIn('duzeltme_of', d)

    def test_kopyalar_birlikte_baglanir(self):
        a, b, d = ilan('sbb-a'), ilan('iskur-b', kaynak_turu='iskur'), duyuru()
        self.assertEqual(duzeltme.uygula([a, b, d], BUGUN, {'iskur-b': 'sbb-a'}), 1)
        self.assertEqual((a['son_tarih'], b['son_tarih']), ('2026-11-04', '2026-11-04'))

    def test_duzeltmeden_sonra_cikan_ilan_ve_akademik_baglanmaz(self):
        sonra = ilan('sbb-s', ilk_gorulme='2026-10-10T10:00:00+03:00')
        self.assertEqual(duzeltme.uygula([sonra, duyuru()], BUGUN, {}), 0)
        ak = ilan('sbb-ak', kadro='2 ÖĞRETİM GÖREVLİSİ', baslik='MALAZGİRT ÜNİVERSİTESİ - Öğretim Görevlisi alımı')
        self.assertEqual(duzeltme.uygula([ak, duyuru()], BUGUN, {}), 0)

    def test_gecmis_tarih_yeni_son_tarih_sayilmaz(self):
        o, d = ilan('sbb-o'), duyuru(duyuru_cumlesi=MALAZGIRT.replace('02/11/2026-04/11/202 6', '01/09/2026-03/09/2026'))
        duzeltme.uygula([o, d], BUGUN, {})
        self.assertEqual(o['son_tarih'], '2026-10-20')
        self.assertEqual(d['duzeltme_degisen'], 'basvuru')

    def test_iptal_islenmez(self):
        o, d = ilan('sbb-o'), duyuru(duyuru_turu='İptal duyurusu')
        self.assertEqual(duzeltme.uygula([o, d], BUGUN, {}), 0)


class Site(unittest.TestCase):
    def test_orijinal_sayfada_uyari_ve_listede_rozet(self):
        o, d = ilan('sbb-' + 'a' * 24), duyuru('sbb-' + 'b' * 24)
        duzeltme.uygula([o, d], BUGUN, {})
        html = site_uret.detail_page(o, simdi=datetime(2026, 10, 15, 12, tzinfo=TR))[1]
        self.assertIn('Başvuru tarihi değişti', html)
        self.assertIn('04.11.2026', html)
        self.assertIn('Resmî düzeltme ↗', html)
        k = liste_verisi.kayit(o, {}, {}, datetime(2026, 10, 15, 12, tzinfo=TR))
        self.assertTrue(k['duzeltildi'])
        self.assertNotIn('duzeltildi', liste_verisi.kayit(ilan('sbb-' + 'c' * 24), {}, {}, datetime(2026, 10, 15, 12, tzinfo=TR)))

    def test_duzeltme_sayfasi_orijinale_kanonik(self):
        d = duyuru('sbb-' + 'b' * 24)
        html = site_uret.detail_page(d, kopya={'rol': 'duzeltme', 'birincil': 'sbb-' + 'a' * 24})[1]
        self.assertIn('rel="canonical" href="https://kpsstercihi.com/ilan/sbb-' + 'a' * 24 + '/"', html)
        self.assertIn('Düzeltilen ilanın güncel sayfası', html)


if __name__ == '__main__':
    unittest.main()
