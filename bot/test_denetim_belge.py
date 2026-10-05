"""Denetim H2/M2/M4/M5/M6: SBB ilan belgesinin TAM metninden il, kadro, puan türü, öğrenim ve KPSS durumu.
Metinler gerçek SBB belgelerinden alınmış kısaltılmış alıntılardır (kişi adı yok)."""
import unittest
from unittest import mock

import belge_alanlari as ba
import liste_verisi as lv
import siniflandir as sf

HANAK = """HANAK BELEDİYE BAŞKANLIĞINA
İLK DEFA ATANMAK ÜZERE MEMUR ALIM İLANI

Ardahan ili Hanak Belediye Başkanlığı bünyesinde, 657 sayılı Devlet Memurları Kanununa
tabi olarak istihdam edilmek üzere; Mahalli İdarelere İlk Defa Atanacaklara Dair Sınav ve Atama
Yönetmeliği hükümlerine göre aşağıda unvanı, sınıfı, derecesi, adedi, nitelikleri, KPSS puan türü,
KPSS taban puanı ve diğer şartları taşımak kaydıyla belirtilen boş kadroya  açıktan atama yoluyla
memur alınacaktır.

Sıra
No
Kadro
Unvanı
Hizmet
Sınıfı
Kadro
Derecesi
Kadro
Adedi Niteliği Cinsiyeti
KPSS
Puan
Türü
KPSS
Taban
Puanı
1 Memur GİH 11 1
-Turizm ve otel
işletmeciliği, Turizm
rehberliği, yerel
yönetimler bölümü ön
lisans programlarının
birinden mezun olmak.
Erkek/
Kadın P93
En az
55
puan
2 VHKİ GİH 11 1
-Kamu Yönetimi,
Çalışma Ekonomisi ve
Endüstri İlişkileri,
muhasebe bilgi sistemleri
lisans programlarının
birinden mezun olmak.
-En az (B) sınıfı sürücü
belgesine sahibi olmak.
Erkek/
Kadın P3
En az
55
puan
3 Tahsildar GİH 11 1
-Kamu Yönetimi,
Çalışma Ekonomisi ve
Endüstri İlişkileri,
muhasebe bilgi sistemleri
lisans programlarının
birinden mezun olmak.
Erkek/
Kadın P3
En az
55
puan

BAŞVURU GENEL VE ÖZEL ŞARTLARI

Belediyemizin yukarıda belirtilen boş memur kadrosu için yapılacak başvurularda aranan genel
ve özel şartlar aşağıdadır.
"""

ARALIK = """ARALIK BELEDİYE BAŞKANLIĞINA
İLK DEFA ATANMAK ÜZERE İTFAİYE ERİ ALIMI İLANI

Iğdır ili Aralık Belediye Başkanlığı bünyesinde,  657 sayılı Devlet Memurları Kanunu’na tabi
olarak istihdam edilmek üzere; Belediye İtfaiye Yönetmeliği hükümlerine göre aşağıda unvanı, sınıfı,
derecesi, adedi, nitelikleri, KPSS puan türü, KPSS taban puanı ve diğer şartları taşımak kaydıyla
belirtilen boş kadrolara açıktan atama yoluyla itfaiye eri alımı yapılacaktır.

Sıra
No
Kadro
Unvanı

Sınıfı Kadro
Derecesi

Adedi

Niteliği

Cinsiyeti
KPSS
Puan
Türü
KPSS
Taban
Puanı


1


İtfaiye Eri


GİH


11


1
-Herhangi bir ön lisans
programından mezun
olmak.
-En az (B) sınıfı sürücü
belgesine sahip olmak.


Erkek


P93

En az
65
Puan



2



İtfaiye Eri



GİH



11



2
- Herhangi bir
ortaöğretim
kurumundan (lise veya
dengi okul) mezun
olmak.
-En az (B) sınıfı sürücü
belgesine sahip olmak.



Erkek



P94


En az
60
Puan

BAŞVURU GENEL VE ÖZEL ŞARTLARI

Belediyemizin yukarıda belirtilen boş itfaiye eri kadroları için yapılacak başvurularda aranan
"""

CUKURKUYU = """ÇUKURKUYU BELEDİYE BAŞKANLIĞINA
İLK DEFA ATANMAK ÜZERE ZABITA MEMURU ALIMI İLANI

Niğde ili Çukurkuyu Belediye Başkanlığı bünyesinde, 657 sayılı Devlet Memurları  Kanununa tabi
olarak istihdam edilmek üzere; Belediye Zabıta Yönetmeliği hükümlerine göre aşağıda unvanı, sınıfı,
derecesi, adedi, nitelikleri, KPSS puan türü, KPSS taban puanı ve diğer şartları taşımak kaydıyla
belirtilen boş kadroya açıktan atama yoluyla zabıta memuru alımı yapılacaktır.

Sıra
No
Kadro
Unvanı
Hizmet
Sınıfı
Kadro
Derecesi
Kadro
Adedi Niteliği Cinsiyeti
KPSS
Puan
Türü
KPSS
Taban
Puanı
1 Zabıta
Memuru GİH 10 1
-Yapı yalıtım
teknolojisi, anestezi
teknikerliği veya tıbbi ve
aromatik bitkiler ön
lisans programlarının
birinden mezun olmak.

-En az (B) sınıfı sürücü
belgesine sahip olmak.
Kadın/
Erkek P93
En az
60
puan

BAŞVURU GENEL VE ÖZEL ŞARTLARI
Belediyemizin yukarıda belirtilen boş zabıta memuru kadrosu için yapılacak başvurularda aranan
"""

POSOF = """POSOF BELEDİYE BAŞKANLIĞINA
İLK DEFA ATANMAK ÜZERE SÖZLEŞMELİ PERSONEL ALIM İLANI
Ardahan ili Posof Belediye Başkanlığı bünyesinde 5393 sayılı Belediye Kanunu’nun 49 uncu
maddesi ile Mahalli İdarelere İlk Defa Atanacaklara Dair Sınav ve Atama Yönetmeliği hükümlerine
göre aşağıda unvanı, sınıfı, derecesi, adedi, nitelikleri, KPSS puan türü, KPSS taban puanı ve diğer
şartları taşımak kaydıyla, belirtilen boş pozisyona tam zamanlı sözleşmeli personel alınacaktır.
Sıra
No
Pozisyon
Unvanı
Hizmet
Sınıfı
Pozisyon
Derecesi
Pozisyon
Adedi Niteliği Cinsiyeti
KPSS
Puan
Türü
KPSS
Taban
Puanı
1 Teknisyen TH 11 1
-Herhangi bir mesleki
ve dengi ortaöğretim
kurumlarının (İnşaat
Teknolojisi, Elektrik-
Elektronik Teknolojisi)
alanı dallarının birinden
mezun olmak
-En az (B) sınıfı sürücü
belgesine sahip olmak.
Erkek/Kadın P94
En az
60
puan
BAŞVURU GENEL VE ÖZEL ŞARTLARI
Belediyemizin yukarıda belirtilen boş bulunan tam zamanlı sözleşmeli personel pozisyonu için
yapılacak başvurularda aranan genel ve özel şartlar aşağıdadır.
"""


def iett():
    govde = """İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜNE
İLK DEFA ATANMAK ÜZERE MEMUR ALIM İLANI

    İstanbul Elektrik Tramvay ve Tünel İşletmeleri Genel Müdürlüğü bünyesinde, 657 sayılı Devlet
Memurları Kanununa tabi olarak istihdam edilmek üzere; Mahalli İdarelere İlk Defa Atanacaklara Dair
Sınav ve Atama Yönetmeliği hükümlerine göre aşağıda unvanı, sınıfı, derecesi, adedi, nitelikleri,
KPSS puan türü, KPSS taban puanı ve diğer şartları taşımak kaydıyla belirtilen boş kadrolara açıktan
atama yoluyla memur alınacaktır.

Sıra
No
Kadro
Unvanı
Hizmet
Sınıfı
Kadro
Derecesi
Kadro
Adedi Niteliği Cinsiyeti
KPSS
Puan
Türü
KPSS
Taban
Puanı
"""
    satirlar = [('Bilgisayar\nİşletmeni', 'GİH 9', 2), ('Bilgisayar\nİşletmeni', 'GİH 9', 2), ('Muhasebeci', 'GİH 7', 1),
                ('Psikolog', 'SH 8', 1), ('Mühendis', 'TH 8', 5), ('Mühendis', 'TH 7', 1), ('Mühendis', 'TH 8', 2),
                ('Mühendis', 'TH 7', 9), ('Mühendis', 'TH 8', 6), ('Mühendis', 'TH 8', 1), ('Mühendis', 'TH 7', 2),
                ('Mühendis', 'TH 8', 2), ('Mühendis', 'TH 8', 10)]
    for n, (unvan, sinif, adet) in enumerate(satirlar, 1):
        govde += (f"{n} {unvan} {sinif} {adet}\n-Alanla ilgili lisans\nprogramlarının birinden\nmezun olmak,\n"
                  "Erkek/\nKadın P3 En az\n70 puan\n")
    return govde + "\nBAŞVURU GENEL VE ÖZEL ŞARTLARI\nBelediyemizin\n"


ILETISIM = """Cumhurbaşkanlığı İletişim Başkanlığından:
SINAVLA İLETİŞİM UZMAN YARDIMCISI ALINACAKTIR
I- GENEL BİLGİLER
(1) İletişim Uzman Yardımcısı unvanıyla atama yapılabilecek azami kadro sayısı 15 (onbeş) adettir.
II- SINAVA KATILMA ŞARTLARI
(1) Sınava başvurabilmek için;
a) 657 sayılı Devlet Memurları Kanunu’nun 48. maddesinde sayılan genel şartları taşımak,
c) En az dört yıllık lisans eğitimi veren;
- Siyasal bilgiler, iktisadî ve idarî bilimler, işletme ve iktisat fakültelerinden (5 kişi)
- İletişim fakültelerinden (8 kişi)
veya bunlara denkliği Yükseköğretim Kurulu tarafından kabul edilen yurt içindeki veya yurt
dışındaki öğretim kurumlarından mezun olmak gerekmektedir.
(6)     Sınava başvuru için KPSS şartı aranmamaktadır.
III- BAŞVURU ŞEKLİ, SÜRESİ, BAŞVURU İÇİN GEREKLİ BELGELER
""" + "Açıklama metni. " * 12


def kayit(kadro, **ek):
    return {'id': 'sbb-' + 'a' * 24, 'kaynak_turu': 'sbb', 'kadro': kadro, 'ilan_turu': 'Memur', 'baslik': 'X - ' + kadro, **ek}


class BelgeAlanlariTests(unittest.TestCase):
    def test_hanak(self):
        r = ba.alanlar([HANAK], kayit('3 MEMUR ALACAK'))
        self.assertEqual(r['kadro'], 'Toplam 3 kişi — 1 Memur • 1 VHKİ • 1 Tahsildar')
        self.assertEqual(r['yer'], 'Ardahan')
        self.assertEqual(r['puan_turleri'], ['P3', 'P93'])
        self.assertEqual(r['belge_ogrenim'], ['lisans', 'onlisans'])

    def test_hanak_ogrenim_lisansi_kaybetmez(self):
        # Kısaltılmış özet yalnız P93 görüyor: eski kural 'lisans'ı atıyordu.
        i = {'baslik': 'HANAK - 3 MEMUR ALACAK', 'kadro': '3 MEMUR ALACAK', 'ozet': 'ön lisans programlarının birinden mezun olmak. P93 En az 55 puan'}
        self.assertEqual(sf.ogrenim_seviyeleri(i), ['onlisans'])
        i['belge_ogrenim'] = ['lisans', 'onlisans']
        self.assertEqual(sf.ogrenim_seviyeleri(i), ['lisans', 'onlisans'])

    def test_aralik_itfaiye(self):
        r = ba.alanlar([ARALIK], kayit('3 MEMUR ALACAK'))
        self.assertEqual((r['kadro'], r['yer']), ('3 İtfaiye Eri', 'Iğdır'))
        self.assertEqual(r['puan_turleri'], ['P93', 'P94'])
        self.assertEqual(r['belge_ogrenim'], ['onlisans', 'ortaogretim'])

    def test_iett_toplam_44(self):
        r = ba.alanlar([iett()], kayit('44 MEMUR ALACAK'))
        self.assertEqual(r['kadro'], 'Toplam 44 kişi — 4 Bilgisayar İşletmeni • 1 Muhasebeci • 1 Psikolog • 38 Mühendis')
        self.assertEqual(r['puan_turleri'], ['P3'])
        self.assertEqual(r['belge_ogrenim'], ['lisans'])
        self.assertEqual(r['yer'] if 'yer' in r else '', '', 'açılış cümlesinde "ili" yok: il yazılmaz')

    def test_cukurkuyu_zabita(self):
        r = ba.alanlar([CUKURKUYU], kayit('1 MEMUR ALACAK'))
        self.assertEqual((r['kadro'], r['yer'], r['puan_turleri'], r['belge_ogrenim']), ('1 Zabıta Memuru', 'Niğde', ['P93'], ['onlisans']))

    def test_posof_sozlesmeli_teknisyen(self):
        r = ba.alanlar([POSOF], kayit('1 MEMUR ALACAK'))
        self.assertEqual((r['kadro'], r['ilan_turu'], r['yer'], r['puan_turleri']), ('1 Teknisyen', 'Sözleşmeli Personel', 'Ardahan', ['P94']))

    def test_toplam_uyusmazsa_kadro_degismez(self):
        self.assertNotIn('kadro', ba.alanlar([HANAK], kayit('5 MEMUR ALACAK')))

    def test_genel_olmayan_kadro_degismez(self):
        self.assertNotIn('kadro', ba.alanlar([HANAK], kayit('3 UZMAN, 2 DESTEK PERSONEL ALACAK')))

    def test_kisa_ya_da_tablosuz_belge_guvenli(self):
        self.assertEqual(ba.alanlar(['Görüntü tabanlı belge'], kayit('1 MEMUR ALACAK')), {})
        r = ba.alanlar([ILETISIM], kayit('15 UZMAN YARDIMCISI ALACAK', ilan_turu='Uzman'))
        self.assertNotIn('kadro', r)
        self.assertNotIn('yer', r)

    def test_iletisim_kpsssiz_ve_lisans(self):
        r = ba.alanlar([ILETISIM], kayit('15 UZMAN YARDIMCISI ALACAK', ilan_turu='Uzman'))
        self.assertEqual(r['belge_kpss'], 'kpsssiz')
        self.assertEqual(r['belge_ogrenim'], ['lisans'])
        self.assertNotIn('puan_turleri', r)
        self.assertEqual(sf.kpss_durumu({**kayit('15 UZMAN YARDIMCISI ALACAK'), **r}), 'kpsssiz')

    def test_kpsssiz_ifadesi(self):
        self.assertEqual(sf.kpss_durumu({'ozet': 'Sınava başvuru için KPSS şartı aranmamaktadır.'}), 'kpsssiz')
        self.assertEqual(sf.kpss_durumu({'ozet': 'KPSS şartı aranmayacak olup yazılı sınava tabi tutulacaktır.'}), 'kpsssiz')
        self.assertEqual(sf.kpss_durumu({'ozet': 'KPSS P3 puan türünden en az 70 puan'}), 'kpss')

    def test_belge_ogrenim_belge_listesi_saymaz(self):
        # 'ortaöğretim, ön lisans, lisans … bilgisi' belge sayımı düzey değildir (Jandarma pilot belgesi)
        metin = ('Pilotluk lisansına sahip olmak, (ortaöğretim, ön lisans, lisans, yüksek lisans, doktora, yurt dışı eğitim bilgisi, '
                 'denklik vb.) aday tarafından doldurulur. ' + 'Açıklama metni. ' * 20)
        self.assertNotIn('belge_ogrenim', ba.alanlar([metin], kayit('1 SÖZLEŞMELİ PİLOT ALACAK', ilan_turu='Pilot')))


class BelgeTamamlaTests(unittest.TestCase):
    def setUp(self):
        lv._BELGE_ONBELLEK.clear()

    def eski(self, **ek):
        return {'id': 'sbb-' + 'e' * 24, 'kaynak_turu': 'sbb', 'baslik': 'HANAK BELEDİYE BAŞKANLIĞI - 3 MEMUR ALACAK', 'kurum': 'HANAK BELEDİYE BAŞKANLIĞI',
                'kadro': '3 MEMUR ALACAK', 'ilan_turu': 'Memur', 'ogrenim': ['onlisans'], 'kpss': 'kpss', 'son_tarih': '2999-01-01',
                'belge_sha256': 'f' * 64, 'sbb_detay_surumu': 5, **ek}

    def test_eski_surum_belgeden_tamamlanir(self):
        eski = self.eski()
        with mock.patch('sbb_detay.belge_sayfalari', return_value=[HANAK]):
            yeni = lv.belge_tamamla(eski)
        self.assertEqual(yeni['ogrenim'], ['lisans', 'onlisans'])
        self.assertEqual(yeni['iller'], ['Ardahan'])
        self.assertEqual(yeni['puan_turleri'], ['P3', 'P93'])
        self.assertTrue(yeni['kadro'].startswith('Toplam 3 kişi'))
        self.assertEqual(eski['kadro'], '3 MEMUR ALACAK', 'kayıt değişmez')
        self.assertEqual(lv.puan_turleri(yeni), ['P3', 'P93'])

    def test_yeni_surum_ya_da_pdf_yoksa_dokunmaz(self):
        yeni_surum = self.eski(sbb_detay_surumu=99)
        self.assertIs(lv.belge_tamamla(yeni_surum), yeni_surum)
        with mock.patch('sbb_detay.belge_sayfalari', return_value=None):
            eski = self.eski()
            self.assertIs(lv.belge_tamamla(eski), eski)

    def test_suresi_dolan_ya_da_kopyasiz_okunmaz(self):
        with mock.patch('sbb_detay.belge_sayfalari', side_effect=AssertionError('okunmamalı')):
            gecmis = self.eski(son_tarih='2020-01-01')
            self.assertIs(lv.belge_tamamla(gecmis), gecmis)
            kopyasiz = self.eski()
            kopyasiz.pop('belge_sha256')
            self.assertIs(lv.belge_tamamla(kopyasiz), kopyasiz)


if __name__ == '__main__':
    unittest.main()
