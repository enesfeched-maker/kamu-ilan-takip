import unittest
from nitelik_ayikla import (kilavuz_nitelikleri, nitelik_tanimlari, orta_alan_listesi,
                            orta_nitelik_tanimlari, program_listesi)

SAYFA_1 = '''LİSANS MEZUNLARI İÇİN ARANAN NİTELİKLER
Nitelik Kodu
ÖĞRENİM KOŞULU
Mezuniyet Alanı Kodları
4419
Hukuk Fakültesinden mezun olmak.
3111 3112
3113
14 15
Nit1 Nit2 Nit3'''

SAYFA_2 = '''LİSANS MEZUNLARI İÇİN ARANAN NİTELİKLER
Nitelik Kodu
ÖĞRENİM KOŞULU
Mezuniyet Alanı Kodları
3114 3115
4420
Fizik veya Kimya bölümlerinden mezun olmak. 3342 3343
4421
Herhangi bir lisans programından mezun olmak.
15 16'''


class NitelikTanimlariTesti(unittest.TestCase):
    def setUp(self):
        self.tanim = nitelik_tanimlari([SAYFA_1, SAYFA_2])

    def test_baslik_satirlari_atlanir(self):
        self.assertEqual(set(self.tanim), {'4419', '4420', '4421'})
        for deger in self.tanim.values():
            self.assertNotIn('Nitelik', deger['m'])
            self.assertNotIn('Nit1', deger['m'])
            self.assertNotIn('ARANAN', deger['m'])

    def test_sayfa_sonunda_kalan_kodlar_yeni_nitelik_sayilmaz(self):
        self.assertEqual(self.tanim['4419']['b'], ['3111', '3112', '3113', '3114', '3115'])

    def test_metne_yapisik_kodlar(self):
        self.assertEqual(self.tanim['4420']['b'], ['3342', '3343'])
        self.assertEqual(self.tanim['4420']['m'], 'Fizik veya Kimya bölümlerinden mezun olmak.')

    def test_herhangi_bir_program(self):
        self.assertTrue(self.tanim['4421']['h'])
        self.assertEqual(self.tanim['4421']['b'], [])
        self.assertFalse(self.tanim['4419']['h'])


ORTA_ESKI = '''Ortaöğretim Nitelik Kodları
NİTELİK
KODU
ÖĞRENİM KOŞULLARI
2001
Adalet Alanından mezun olmak.
6001
*
ADALET ALANI VE DALLARI
2002
Elektrik Alanı - Tesisat Dalından mezun olmak.
6008
3
ELEKTRİK ALANI - TESİSAT DALI
6008
3
ELEKTRİK ALANI - TESİSAT DALI
Sayfa 1 / 2
2003
Herhangi bir ortaöğretim kurumundan mezun olmak.'''

# 2025-1 biçimi: dal no ile ad aynı satırda
ORTA_YENI = '''2087
Acil Sağlık Hizmetleri Alanı - Acil Tıp Teknisyenliği Dalından mezun
olmak.
6201
101 ACİL SAĞLIK HİZMETLERİ ALANI - ACİL TIP TEKNİSYENLİĞİ DALI
2089
Anestezi Teknisyenliği Dalından mezun olmak.
6202
101 ANESTEZİ VE REANİMASYON ALANI - ANESTEZİ TEKNİSYENLİĞİ DALI'''

ALAN_LISTESI = '''Alan Kodu Alan Adı
Alan Kod
Alan Adı
Dal Kod
Dal Adı
6001
ADALET
-
ADALET
6001
ADALET
2
İNFAZ VE KORUMA
6008
ELEKTRİK
3
TESİSAT'''


class OrtaogretimTesti(unittest.TestCase):
    def test_nitelik_alan_ve_dal(self):
        t = orta_nitelik_tanimlari([ORTA_ESKI])
        self.assertEqual(set(t), {'2001', '2002', '2003'})
        self.assertEqual(t['2001']['b'], ['6001-*'])
        self.assertEqual(t['2002']['b'], ['6008-3'])  # tekrarlayan satır tek sayılır
        self.assertTrue(t['2003']['h'])

    def test_dal_no_ve_ad_ayni_satirda(self):
        t = orta_nitelik_tanimlari([ORTA_YENI])
        self.assertEqual(t['2087']['b'], ['6201-101'])
        self.assertEqual(t['2089']['b'], ['6202-101'])
        self.assertEqual(t['2087']['ad']['6201-101'], 'ACİL SAĞLIK HİZMETLERİ ALANI - ACİL TIP TEKNİSYENLİĞİ DALI')

    def test_yedek_ad_ayri_satirda(self):
        t = orta_nitelik_tanimlari([ORTA_ESKI])
        self.assertEqual(t['2002']['ad'], {'6008-3': 'ELEKTRİK ALANI - TESİSAT DALI'})
        self.assertEqual(t['2001']['ad'], {'6001-*': 'ADALET ALANI VE DALLARI'})

    def test_alan_listesi(self):
        self.assertEqual(orta_alan_listesi([ALAN_LISTESI]), {
            '6001--': 'ADALET', '6001-2': 'ADALET — İNFAZ VE KORUMA', '6008-3': 'ELEKTRİK — TESİSAT'})


KILAVUZ = '''TABLO-1
202010101
ADIYAMAN İL ÖZEL İDARESİ / ADIYAMAN
TEKNİKER
1
4419 7205 7207
9999
202010102
ANKARA BELEDİYESİ
MEMUR
2
7205
202010103
SAĞLIK FİZİKÇİSİ
1'''


class KilavuzTesti(unittest.TestCase):
    def test_yalniz_ogrenim_kodlari_alinir(self):
        s = kilavuz_nitelikleri([KILAVUZ], {'4419', '7205'})
        self.assertEqual(s['202010101'], ['4419', '7205'])  # 7207 ve 9999 öğrenim kodu değil
        self.assertEqual(s['202010102'], ['7205'])

    def test_kayit_dokuz_haneli_kodla_baslar(self):
        s = kilavuz_nitelikleri([KILAVUZ], {'4419', '7205'})
        self.assertEqual(set(s), {'202010101', '202010102', '202010103'})
        self.assertEqual(s['202010103'], [])  # bölüm şartı özel koşulda


class MetinSayisiTesti(unittest.TestCase):
    def test_metin_satirindaki_dort_haneli_sayi_alinmaz(self):
        sayfa = '202010101\nKURUM\nBu kadro 2023 yılında 4419 sayılı karar ile açıldı\n4419\n'
        self.assertEqual(kilavuz_nitelikleri([sayfa], {'4419', '2023'}), {'202010101': ['4419']})


class HerhangiVeKodTesti(unittest.TestCase):
    def test_kod_listeleyen_nitelik_herhangi_icerebilir(self):
        sayfa = '4430\nHerhangi bir fakülteden veya aşağıdaki programlardan mezun olmak.\n3111 3112'
        t = nitelik_tanimlari([sayfa])
        self.assertTrue(t['4430']['h'])
        self.assertEqual(t['4430']['b'], ['3111', '3112'])  # main: kod listesi 'herhangi bir'i ezmez


class ProgramListesiTesti(unittest.TestCase):
    def test_ayri_satir(self):
        s = 'Kodu\nAdı\n1472\nABAZA DİLİ VE EDEBİYATI\n8342\nACİL YARDIM VE AFET YÖNETİMİ'
        self.assertEqual(program_listesi([s]), {'1472': 'ABAZA DİLİ VE EDEBİYATI', '8342': 'ACİL YARDIM VE AFET YÖNETİMİ'})

    def test_ayni_satir(self):
        s = 'KODU ADI\n1459 ARKA-YÜZ YAZILIM GELİŞTİRME\n1460 YAPAY ZEKA'
        self.assertEqual(program_listesi([s]), {'1459': 'ARKA-YÜZ YAZILIM GELİŞTİRME', '1460': 'YAPAY ZEKA'})

    def test_iki_satira_sarili_ad_ve_sayfa_basligi(self):
        s1 = 'Kodu\nAdı\n3101\nAĞAÇ İŞLERİ ENDÜSTRİ MÜHENDİSLİĞİ /\nAĞAÇ İŞLERİ ENDÜSTRİSİ MÜHENDİSLİĞİ\n4203\nAĞAÇ İŞLERİ ENDÜSTRİSİ'
        s2 = 'Kodu\nAdı\nMezun Olunan Lisans Alanları\n4204\nALMAN DİLİ'
        self.assertEqual(program_listesi([s1, s2]), {
            '3101': 'AĞAÇ İŞLERİ ENDÜSTRİ MÜHENDİSLİĞİ / AĞAÇ İŞLERİ ENDÜSTRİSİ MÜHENDİSLİĞİ',
            '4203': 'AĞAÇ İŞLERİ ENDÜSTRİSİ', '4204': 'ALMAN DİLİ'})

    def test_bozuk_glifli_baslik_ada_eklenmez(self):
        s = '4213\nBİLGİSAYAR PROGRAMCILIĞI\naĞǌƵŶ hůƵŶĂŶ mŶ [ŝƐĂŶƐ !ůĂŶůĂƌŦ\x02\n5316\nHALKLA İLİŞKİLER'
        self.assertEqual(program_listesi([s]), {'4213': 'BİLGİSAYAR PROGRAMCILIĞI', '5316': 'HALKLA İLİŞKİLER'})

    def test_tireli_sarma_bosluksuz_birlesir(self):
        s = '7001\nMÜZİK TEORİ-\nKOMPOZİSYON\n7002\nBİR AD'
        self.assertEqual(program_listesi([s]), {'7001': 'MÜZİK TEORİ-KOMPOZİSYON', '7002': 'BİR AD'})

    def test_ayni_kodun_ilk_adi_alinir(self):
        s = '1306\nAYAKKABI TASARIM VE ÜRETİMİ\n1306\nAYAKKABI TASARIMI VE ÜRETİMİ'
        self.assertEqual(program_listesi([s]), {'1306': 'AYAKKABI TASARIM VE ÜRETİMİ'})


if __name__ == '__main__':
    unittest.main()
