import unittest

from siniflandir import etiketler, il_adlari, kategori, kpss_durumu, ogrenim_seviyeleri


def ilan(**alanlar):
    return alanlar


ICRA_SART = ('c) Hukuk fakültesi, adalet meslek yüksekokulu, meslek yüksekokullarının adalet bölümü veya adalet meslek eğitimi '
             'ön lisans programı mezunu olmak, öğrenim yabancı ülkede yapılmış ise denklik belgesi almış olmak,')


class FakulteSartiTesti(unittest.TestCase):
    def test_fakulte_virgul_lisans_sayilir(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(sartlar=[{'metin': ICRA_SART}])), ['lisans', 'onlisans'])
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Hukuk fakültesi veya iktisat fakültesi mezunu olmak')), ['lisans'])
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Eczacılık fakültesi ya da tıp fakültesi mezunu')), ['lisans'])

    def test_fakulte_adi_kurum_ve_gorev_yerinde_lisans_degil(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(kurum='Tıp Fakültesi Hastanesi', baslik='Tıp Fakültesi, Hastanesi Personel')), [])
        self.assertEqual(ogrenim_seviyeleri(ilan(sartlar=[{'metin': 'Önlisans. Diş Hekimliği Fakültesinde görevlendirilecektir.'}])), ['onlisans'])

    def test_bolum_kisiti(self):
        from siniflandir import bolum_kisitli
        self.assertTrue(bolum_kisitli(ilan(sartlar=[{'metin': ICRA_SART}])))
        self.assertTrue(bolum_kisitli(ilan(ozet='makine mühendisliği bölümünden mezun olmak')))
        self.assertFalse(bolum_kisitli(ilan(ozet='Lisans mezunu olmak; Tıp Fakültesi Hastanesi', kurum='Tıp Fakültesi Hastanesi')))


class OgrenimTesti(unittest.TestCase):
    def test_onlisans_lisans_karismaz(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Önlisans mezunu olmak.')), ['onlisans'])
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Ön lisans mezunu olmak.')), ['onlisans'])

    def test_lisans_ve_kpss_puani(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Lisans mezunu, KPSSP3 puanı')), ['lisans'])
        self.assertEqual(ogrenim_seviyeleri(ilan(
            sartlar=[{'kadro': 'Uzman', 'metin': 'Fakültelerin dört yıllık bölümlerinden'}])), ['lisans'])

    def test_lisansustu_lisans_degil(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Lisansüstü eğitim yapmış olmak.')), [])
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='Yüksek lisans mezunu olmak.')), [])

    def test_buyuk_harf(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='LİSANS MEZUNU OLMAK')), ['lisans'])
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='ORTAÖĞRETİM MEZUNU, LİSE')), ['ortaogretim'])
        self.assertEqual(ogrenim_seviyeleri(ilan(ozet='ÖN LİSANS MEZUNU')), ['onlisans'])

    def test_birden_cok_seviye_sirali(self):
        sartlar = [{'kadro': 'A', 'metin': 'KPSSP94 puanı'}, {'kadro': 'B', 'metin': 'KPSSP3 puanı'}]
        self.assertEqual(ogrenim_seviyeleri(ilan(sartlar=sartlar)), ['lisans', 'ortaogretim'])

    def test_akademik_bos(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(
            ilan_turu='Öğretim Üyesi', ozet='Lisans mezunu doktor öğretim üyesi')), [])

    def test_emin_degilse_bos(self):
        self.assertEqual(ogrenim_seviyeleri(ilan(baslik='Personel alımı')), [])


class KategoriTesti(unittest.TestCase):
    def test_oncelik(self):
        self.assertEqual(kategori(ilan(kurum='X Belediyesi', ilan_turu='Öğretim Elemanı')), 'akademik')
        self.assertEqual(kategori(ilan(kurum='X Belediyesi', ilan_turu='İşçi')), 'belediye')
        self.assertEqual(kategori(ilan(ilan_turu='İşçi İlanları')), 'isci')
        self.assertEqual(kategori(ilan(baslik='SÖZLEŞMELİ BİLİŞİM PERSONELİ ALIMI')), 'bilisim')
        self.assertEqual(kategori(ilan(kurum='Devlet Hastanesi')), 'saglik')
        self.assertIsNone(kategori(ilan(baslik='Uzman alımı')))

    def test_ebe_kelime_siniri(self):
        self.assertIsNone(kategori(ilan(baslik='Ebeveyn destek uzmanı')))


class KpssTesti(unittest.TestCase):
    def test_durumlar(self):
        self.assertEqual(kpss_durumu(ilan(ozet='KPSS P3 puanı')), 'kpss')
        self.assertEqual(kpss_durumu(ilan(ozet="KPSS şartı aranmaz.")), 'kpsssiz')
        self.assertEqual(kpss_durumu(ilan(ozet="KPSS'siz alım")), 'kpsssiz')
        self.assertIsNone(kpss_durumu(ilan(ozet='Sözlü sınav')))


class EtiketTesti(unittest.TestCase):
    def test_iskur_sadece_baslik(self):
        self.assertEqual(etiketler(ilan(
            baslik='KIRŞEHİR BELEDİYESİ 5 İŞÇİ', kurum='Kırşehir Belediyesi', yer='Kırşehir')),
            ['#Kırşehir', '#belediye'])

    def test_il_formati(self):
        self.assertIn('#İstanbul', etiketler(ilan(yer='İSTANBUL / KADIKÖY')))
        self.assertIn('#Iğdır', etiketler(ilan(yer='IĞDIR')))
        self.assertIn('#Ankara', etiketler(ilan(yer='ANKARA • ANKARA / MERKEZ')))

    def test_bilinmeyen_il(self):
        self.assertEqual(etiketler(ilan(yer='BAKANLIK MERKEZ TEŞKİLATI')), [])
        self.assertEqual(etiketler(ilan(yer=None)), [])

    def test_sirali_tekrarsiz(self):
        sonuc = etiketler(ilan(ozet='Lisans mezunu KPSSP3', ilan_turu='Memur', yer='Rize / Merkez'))
        self.assertEqual(sonuc, ['#Rize', '#kpss', '#lisans'])

    def test_akademik(self):
        self.assertEqual(etiketler(ilan(ilan_turu='Araştırma Görevlisi', yer='Van')), ['#Van', '#akademik'])


class AkademikVeFakulteTests(unittest.TestCase):
    def test_basliksiz_akademik_ilan_sartlardan_tanınır(self):
        ilan = {'baslik': 'NEVŞEHİR HACI BEKTAŞ VELİ ÜNİVERSİTESİ - 1 ALACAK', 'kadro': '1 ALACAK',
                'sartlar': [{'kadro': 'Koşullar', 'metin': '1- Doktora veya tıpta uzmanlık eğitimini tamamlamış olanlarda, meslek yüksekokullarının'}]}
        self.assertEqual(kategori(ilan), 'akademik')
        self.assertEqual(ogrenim_seviyeleri(ilan), [])

    def test_kurum_adindaki_fakulte_lisans_sayilmaz(self):
        ilan = {'baslik': 'Tıp Fakültesi Hastanesi Sürekli İşçi Alımı', 'kurum': 'X Üniversitesi'}
        self.assertNotIn('lisans', ogrenim_seviyeleri(ilan))


class DenetimDuzeltmeTests(unittest.TestCase):
    def test_olumlu_kpss_sarti_kpsssiz_sayilmaz(self):
        self.assertEqual(kpss_durumu({'ozet': '2024 KPSS P3 puanı en az 70 olma şartı aranmaktadır.'}), 'kpss')
        self.assertEqual(kpss_durumu({'ozet': 'KPSS şartı aranmaz.'}), 'kpsssiz')

    def test_ogrenci_kaydi_sarti_ogrenim_duzeyi_sayilmaz(self):
        ilan = {'ozet': 'Örgün ön lisans eğitimi öğrencisi kaydı bulunmamak. Lise mezunu olmak.'}
        self.assertEqual(ogrenim_seviyeleri(ilan), ['ortaogretim'])

    def test_bozuk_tabloda_p93_lisans_sayilmaz(self):
        ilan = {'ozet': 'ön kadın en az 1 memuru gih 10 1 lisans programlarının erkek p93 60'}
        self.assertEqual(ogrenim_seviyeleri(ilan), ['onlisans'])


class IlAdlariTesti(unittest.TestCase):
    def il(self, yer):
        return il_adlari(ilan(yer=yer))

    def test_tek_il_ve_ilce(self):
        self.assertEqual(self.il('İSTANBUL / ATAŞEHİR'), ['İstanbul'])
        self.assertEqual(self.il('Afyonkarahisar'), ['Afyonkarahisar'])
        self.assertEqual(self.il('ANKARA • ANKARA / MERKEZ'), ['Ankara'])

    def test_kurum_sonrasi_iller_taranir(self):
        self.assertEqual(self.il('BATI AKDENİZ KALKINMA AJANSI / ANTALYA, BURDUR, ISPARTA'),
                         ['Antalya', 'Burdur', 'Isparta'])

    def test_tire_ile_birden_cok_il(self):
        self.assertEqual(self.il('Kars-Ardahan'), ['Kars', 'Ardahan'])
        self.assertEqual(self.il('İSTANBUL-ANKARA'), ['İstanbul', 'Ankara'])
        self.assertEqual(self.il('BURSA -ESKİŞEHİR - BİLECİK'), ['Bursa', 'Eskişehir', 'Bilecik'])

    def test_ilce_basta_il_sonda(self):
        self.assertEqual(self.il('Çankaya / Ankara'), ['Ankara'])
        self.assertEqual(self.il('MERKEZ / ANKARA'), ['Ankara'])

    def test_parantez_ve_kismi_tanim(self):
        self.assertEqual(self.il('İstanbul (Avrupa Yakası) • Ankara'), ['İstanbul', 'Ankara'])
        self.assertEqual(self.il('DENİZLİ / MANİSA'), ['Denizli', 'Manisa'])
        self.assertEqual(self.il('ANKARA / ÇANKAYA'), ['Ankara'])
        self.assertEqual(self.il('Ankara • Çankaya'), [])
        self.assertEqual(self.il('İzmir, Merkez Teşkilatı'), [])

    def test_emin_degilse_bos(self):
        self.assertEqual(self.il('BAKANLIK MERKEZ TEŞKİLATI'), [])
        self.assertEqual(self.il('Ankara Kalkınma Ajansı'), [])
        self.assertEqual(self.il('Çankaya'), [])
        self.assertEqual(self.il(None), [])


if __name__ == '__main__':
    unittest.main()
