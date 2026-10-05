"""Denetim H5/H6/H7/H8/M10: İŞKUR kurum ayrıştırma, yazım hatası, kısmi Kariyer Kapısı kadrosu ve kopya eşleşmeleri."""
import unittest

import ek_kaynaklar as ek
import kopya
import kurum_gorseli
import liste_verisi as lv

ISKUR = 'https://www.iskur.gov.tr/medya/x/'
SBB = 'https://kamuilan.sbb.gov.tr/'
IETT_KADRO = 'Toplam 44 kişi — 4 Bilgisayar İşletmeni • 1 Muhasebeci • 1 Psikolog • 38 Mühendis'


def iskur(n, baslik, **ek_):
    r = {'id': 'iskur-' + ('%024x' % n), 'baslik': baslik, 'kurum': ek.institution(baslik), 'kaynak_turu': 'iskur', 'kaynak': 'İŞKUR',
         'link': ISKUR + str(n) + '.pdf', 'ilan_turu': 'Memur', 'ilk_gorulme': '2026-09-28T10:00:00+03:00'}
    r['kaynaklar'] = [{'ad': 'İŞKUR', 'link': r['link']}]
    r.update(ek_)
    return r


def sbb(n, baslik, kurum, **ek_):
    r = {'id': 'sbb-' + ('%024x' % n), 'baslik': baslik, 'kurum': kurum, 'kaynak_turu': 'sbb', 'kaynak': 'SBB Kamu İlan', 'link': SBB,
         'kaynaklar': [{'ad': 'SBB Kamu İlan', 'link': SBB}], 'ilan_turu': 'Memur', 'ilk_gorulme': '2026-09-28T10:00:00+03:00'}
    r.update(ek_)
    return r


def kk(n, baslik, kurum, **ek_):
    u = 'https://kariyerkapisi.gov.tr/IlanDetay?i=%08d-4444-4444-8444-444444444444' % n
    return {'id': u, 'link': u, 'baslik': baslik, 'kurum': kurum, 'ilk_gorulme': '2026-09-28T09:23:46+03:00', **ek_}


def gruplar(*ilanlar):
    return kopya.kopya_bul(list(ilanlar))['kopya_of']


class KurumAyrismaTests(unittest.TestCase):
    def test_ajans(self):
        self.assertEqual(ek.institution('Türkiye Turizm Tanıtım ve Geliştirme Ajansı Personel Alım İlanı'),
                         'Türkiye Turizm Tanıtım ve Geliştirme Ajansı')

    def test_baslikten_yedek(self):
        self.assertEqual(ek.kurum_basliktan('Örnek Düzenleme Merkezi Personel Alım İlanı'), 'Örnek Düzenleme Merkezi')
        self.assertEqual(ek.kurum_basliktan('Memur Alım İlanı'), '')

    def test_en_ozgul_birim(self):
        self.assertEqual(ek.institution('İstanbul Büyükşehir Belediyesi İETT İşletmeleri Genel Müdürlüğü Memur Alım İlanı'),
                         'İETT İşletmeleri Genel Müdürlüğü')
        self.assertEqual(ek.institution('Ankara Büyükşehir Belediyesi Memur Alım İlanı'), 'Ankara Büyükşehir Belediyesi')
        self.assertEqual(ek.institution('Ardahan Hanak Belediyesi Memur Alım İlanı'), 'Ardahan Hanak Belediyesi')

    def test_yazim_hatasi_pasof(self):
        self.assertEqual(kurum_gorseli.kurum_anahtari('Ardahan Pasof Belediyesi'), kurum_gorseli.kurum_anahtari('Ardahan Posof Belediyesi'))

    def test_toplayici_kurumu_baslikta_yoksa_tamamlar(self):
        eski = iskur(1, 'Türkiye Turizm Tanıtım ve Geliştirme Ajansı Personel Alım İlanı', kurum=None, son_tarih='2026-11-05')
        yeni = lv.iskur_tamamla(eski)
        self.assertEqual(yeni['kurum'], 'Türkiye Turizm Tanıtım ve Geliştirme Ajansı')
        self.assertIsNone(eski['kurum'])

    def test_ozetteki_gorev_ili_iskur_sehrini_ezer(self):
        r = iskur(2, 'Sigortacılık ve Özel Emeklilik Düzenleme ve Denetleme Kurumu Personel Alım İlanı', yer='Ankara',
                  ozet='Kurumumuzun İstanbul`da görev yapmak üzere Sekreter, Şoför ve Hizmetli kadrolarına personel alınacaktır.')
        self.assertEqual(lv.iskur_tamamla(r)['yer'], 'İstanbul')
        self.assertEqual(ek.iskur_il_duzelt(dict(r))['yer'], 'İstanbul')
        self.assertEqual(ek.iskur_il_duzelt(iskur(3, 'X Kurumu Alım İlanı', yer='Ankara', ozet='Ankara merkezde görev yapacaktır'))['yer'], 'Ankara')


class KopyaEslesmeTests(unittest.TestCase):
    def test_iett(self):
        a = iskur(10, 'İstanbul Büyükşehir Belediyesi İETT İşletmeleri Genel Müdürlüğü Memur Alım İlanı', yer='İstanbul',
                  kadro=IETT_KADRO, son_tarih='2026-11-02')
        b = sbb(11, 'İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜ (İETT) - 44 MEMUR ALACAK',
                'İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜ (İETT)', kadro=IETT_KADRO, son_tarih='2026-11-02')
        self.assertEqual(len(gruplar(a, b)), 1)

    def test_pasof_posof(self):
        a = iskur(20, 'Ardahan Pasof Belediyesi Sözleşmeli Personel Alım İlanı', yer='Ardahan', kadro='1 Teknisyen',
                  ilan_turu='Sözleşmeli Personel', son_tarih='2026-11-04')
        b = sbb(21, 'POSOF BELEDİYE BAŞKANLIĞI - 1 MEMUR ALACAK', 'POSOF BELEDİYE BAŞKANLIĞI', kadro='1 Teknisyen',
                ilan_turu='Sözleşmeli Personel', son_tarih='2026-11-04', iller=['Ardahan'])
        self.assertEqual(len(gruplar(a, b)), 1)

    def test_farkli_belediye_birlesmez(self):
        a = iskur(22, 'Ardahan Pasof Belediyesi Sözleşmeli Personel Alım İlanı', yer='Ardahan', kadro='1 Teknisyen', son_tarih='2026-11-04')
        b = sbb(23, 'GÖLE BELEDİYE BAŞKANLIĞI - 1 TEKNİSYEN', 'GÖLE BELEDİYE BAŞKANLIĞI', kadro='1 Teknisyen', son_tarih='2026-11-04', iller=['Ardahan'])
        self.assertEqual(gruplar(a, b), {})

    def test_seddk_istanbul(self):
        a = iskur(30, 'Sigortacılık ve Özel Emeklilik Düzenleme ve Denetleme Kurumu Personel Alım İlanı', yer='Ankara', son_tarih='2026-10-09',
                  ozet='Kurumumuz İstanbul`da görev yapmak üzere 3 Sekreter, 2 Şoför ve 5 Hizmetli alacaktır.')
        b = sbb(31, 'SİGORTACILIK VE ÖZEL EMEKLİLİK DÜZENLEME VE DENETLEME KURUMU - 10 MEMUR ALACAK',
                'SİGORTACILIK VE ÖZEL EMEKLİLİK DÜZENLEME VE DENETLEME KURUMU', kadro='10 MEMUR ALACAK', son_tarih='2026-10-09', yer='İstanbul')
        self.assertEqual(len(gruplar(lv.iskur_tamamla(a), b)), 1)

    def test_ahbvu_kismi_kk_ayrismasi(self):
        k = kk(1, 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ PERSONEL (4/B) ALIM İLANI (28.09.2026)',
               'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ', kadro='Toplam 13 kişi — 4 BÜRO PERSONELİ • 9 DESTEK PERSONELİ',
               son_tarih='2026-10-12', baslangic_zaman='2026-09-28T09:00:00+03:00', yer='ANKARA / MERKEZ', ilan_turu='Sözleşmeli Personel İlanları')
        s = sbb(40, 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ - 18 SÖZLEŞMELİ PERSONEL ALACAK', 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ',
                kadro='18 SÖZLEŞMELİ PERSONEL ALACAK', son_tarih='2026-10-12', baslangic_zaman='2026-09-28T00:00:00+03:00', ilan_turu='Sözleşmeli Personel',
                iller=['Ankara'])
        sonuc = kopya.kopya_bul([k, s])
        self.assertEqual(sonuc['kopya_of'], {k['id']: s['id']}, 'birincil: belgeye dayalı büyük toplamlı (18) kayıt')

    def test_ahbvu_farkli_gun_ya_da_tarih_birlesmez(self):
        k = kk(2, 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ PERSONEL (4/B) ALIM İLANI', 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ',
               kadro='Toplam 13 kişi — 4 BÜRO PERSONELİ • 9 DESTEK PERSONELİ', son_tarih='2026-10-12', baslangic_zaman='2026-09-28T09:00:00+03:00',
               yer='ANKARA / MERKEZ', ilan_turu='Sözleşmeli Personel İlanları')
        s = sbb(41, 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ - 18 SÖZLEŞMELİ PERSONEL ALACAK', 'ANKARA HACI BAYRAM VELİ ÜNİVERSİTESİ',
                kadro='18 SÖZLEŞMELİ PERSONEL ALACAK', son_tarih='2026-10-12', baslangic_zaman='2026-09-20T00:00:00+03:00', ilan_turu='Sözleşmeli Personel', iller=['Ankara'])
        self.assertEqual(gruplar(k, s), {})
        s['baslangic_zaman'] = '2026-09-28T00:00:00+03:00'
        s['son_tarih'] = '2026-10-19'
        self.assertEqual(gruplar(k, s), {})


if __name__ == '__main__':
    unittest.main()
