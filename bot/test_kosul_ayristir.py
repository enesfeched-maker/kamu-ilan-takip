import unittest

import kosul_ayristir as k
import site_uret


TSE = ("BU İLANA ''Fakültelerin dört yıllık bilgisayar mühendisliği bölümlerinden mezun olmak,'' ŞARTLARINI TAŞIYAN ADAYLAR "
       "BAŞVURU YAPABİLECEKTİR.<br>a. GENEL ŞARTLAR (NİTELİKLER)<br>a) 657 sayılı Devlet Memurları Kanununun 48’inci maddesinde "
       "belirtilen şartları taşımak,<br>b. ÖZEL ŞARTLAR<br>Genel Nitelikler<br>a. {ozel}<br>Tercihen;<br>a. Docker bilgisi olmak,")
SARAY = ("1.Grup:<br>Unvanı: Koruma ve Güvenlik Görevlisi<br>Kadro Adedi: 5<br>Görev İli : İstanbul<br>Sınav Usulü: KPSS P3<br>"
         "Özel Şartları:<br>1- ÖSYM tarafından 2025 yılında yapılan Kamu Personeli Seçme<br>Sınavlarında KPSS P3 puan türünde en az 60 puan "
         "almış olmak.<br>2- 10/6/2004 tarihli ve 5188 sayılı Özel Güvenlik Hizmetlerine Dair Kanun’un<br>10 uncu maddesinde belirtilen "
         "şartlar ile Sağlık Şartları Yönetmeliği’nde belirtilen sağlık şartlarına sahip olmak.")
HAZINE = ("T.C.<br>I-SINAVA İLİŞKİN BİLGİLER<br>Sınav iki aşamada yapılır.<br>II-SINAVA GİRİŞ ŞARTLARI<br>"
          "Fiili hizmet süresinin en az üç yıl olması gerekmektedir.<br>III-SINAV USULÜ VE KONULARI<br>a-BAKANLIK GÖREV ALANINA GİREN "
          "KONULAR<br>- 4982 sayılı Bilgi Edinme Hakkı Kanunu<br>Genel Yönetim Muhasebe Yönetmeliği<br>- Merkezi Yönetim Muhasebe Yönetmeliği")


class KosulAyristirTest(unittest.TestCase):
    def test_bolumler_basliklar_ve_tercih(self):
        b = dict(k.bolumler(TSE.format(ozel='Linux sistemlerinde en az 5 yıl tecrübe sahibi olmak,')))
        self.assertIn('Bu kadroya yalnız şu şartı taşıyanlar başvurabilir: Fakültelerin dört yıllık bilgisayar mühendisliği '
                      'bölümlerinden mezun olmak.', b[''])
        self.assertEqual(b['Genel Nitelikler'], ['Linux sistemlerinde en az 5 yıl tecrübe sahibi olmak,'])
        self.assertEqual(b['Tercihen'], ['Docker bilgisi olmak,'])
        self.assertIn('GENEL ŞARTLAR (NİTELİKLER)', b)

    def test_ortak_maddeler_bir_kez(self):
        ortak, ozel = k.ayir([TSE.format(ozel='Linux tecrübesi olmak,'), TSE.format(ozel='SQL tecrübesi olmak,')])
        ortak_maddeler = [m for _, ms in ortak for m in ms]
        self.assertIn('657 sayılı Devlet Memurları Kanununun 48’inci maddesinde belirtilen şartları taşımak,', ortak_maddeler)
        self.assertEqual(dict(ozel[0])['Genel Nitelikler'], ['Linux tecrübesi olmak,'])
        self.assertNotIn('Tercihen', dict(ozel[1]))   # iki kadroda da aynı: ortakta

    def test_alanlar_atilir_bolunen_satir_birlesir(self):
        b = k.bolumler(SARAY)
        self.assertEqual([x for x, _ in b], ['Özel Şartları'])
        self.assertEqual(len(b[0][1]), 2)
        self.assertTrue(b[0][1][1].startswith('10/6/2004 tarihli') and 'Sağlık Şartları Yönetmeliği' in b[0][1][1])

    def test_sinav_konulari_atilir(self):
        b = k.bolumler(HAZINE)
        self.assertEqual(b, [['SINAVA GİRİŞ ŞARTLARI', ['Fiili hizmet süresinin en az üç yıl olması gerekmektedir.']]])


class KadroKartiTest(unittest.TestCase):
    def test_kart_ortak_ve_katlama(self):
        kadrolar = [{'unvan': 'Sistem Uzmanı (2 Kişi - Tam Zamanlı, Ücret Tavanının 2 Katına Kadar)', 'adet': 2,
                     'bolumler': [['Genel Şartlar', ['Türk vatandaşı olmak.']], ['Özel Şartlar', [f'Şart {n} olmak.' for n in range(12)]]]}]
        html = site_uret._kk_kadro_kartlari(kadrolar, 'https://kariyerkapisi.gov.tr/IlanDetay?i=x',
                                            [['Genel Şartlar', ['Kamu haklarından mahrum bulunmamak.']]])
        self.assertIn('<strong>Sistem Uzmanı</strong>', html)
        self.assertIn('Tam Zamanlı, Ücret Tavanının 2 Katına Kadar', html)
        self.assertIn('Tüm kadrolar için ortak koşullar', html)
        self.assertIn('Tamamını göster (7 madde daha)', html)
        self.assertLess(html.index('Şart 0'), html.index('Türk vatandaşı'))   # özel şartlar genel şartlardan önce
        html = site_uret._kk_kadro_kartlari([{'unvan': 'Uzman', 'bolumler': [['Genel Nitelikler', ['Linux bilmek.']],
                                                                              ['Tercihen', ['Docker bilmek.']]]}], '')
        self.assertLess(html.index('Linux'), html.index('Docker'))   # 'Genel Nitelikler' asıl şarttır, tercihten önce


if __name__ == '__main__':
    unittest.main()
