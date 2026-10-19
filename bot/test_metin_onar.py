import unittest

from metin_onar import onar


class MetinOnar(unittest.TestCase):
    def test_kelime_kiriklari(self):
        self.assertEqual(onar('Pursaklar Belediye B aşkanlığı bünyesinde'), 'Pursaklar Belediye Başkanlığı bünyesinde')
        self.assertEqual(onar('5393 sayılı Be lediye Kanununun'), '5393 sayılı Belediye Kanununun')
        self.assertEqual(onar('başvuru be lgelerini teslim'), 'başvuru belgelerini teslim')
        self.assertEqual(onar('Cumhuriyet C addesi No:'), 'Cumhuriyet Caddesi No:')
        self.assertEqual(onar('diğer ş artları taşımak'), 'diğer şartları taşımak')
        self.assertEqual(onar('diğer şekil lerde yapılacak'), 'diğer şekillerde yapılacak')
        self.assertEqual(onar('KPSS puanları i le sınav yeri'), 'KPSS puanları ile sınav yeri')
        self.assertEqual(onar('başvuruların değerlendirilmesin i müteakip'), 'başvuruların değerlendirilmesini müteakip')

    def test_kopan_son_harf_ve_ek(self):
        self.assertEqual(onar('kabul edilmiş yur t dışındaki kurumlar'), 'kabul edilmiş yurt dışındaki kurumlar')
        self.assertEqual(onar('No:6 adresi ndeki birime'), 'No:6 adresindeki birime')
        self.assertEqual(onar('mezun olma k ve'), 'mezun olmak ve')
        self.assertEqual(onar('başvuru belgelerini pdf olarak'), 'başvuru belgelerini pdf olarak')
        self.assertEqual(onar('içinde h ttps://ornek.gov.tr adresinden'), 'içinde https://ornek.gov.tr adresinden')
        self.assertEqual(onar('e-posta: a@b.gov.tr Sayfa 5 / 8 T.C.'), 'e-posta: a@b.gov.tr')
        self.assertEqual(onar('İş süreçleri ve Ağ güvenliği'), 'İş süreçleri ve Ağ güvenliği')
        self.assertEqual(onar('ile script yazmak'), 'ile script yazmak')

    def test_adresler(self):
        self.assertEqual(onar('taskestibelediye@gmai l.com mail'), 'taskestibelediye@gmail.com mail')
        self.assertEqual(onar('insankaynaklari@gered e.bel.tr adresine'), 'insankaynaklari@gerede.bel.tr adresine')
        self.assertEqual(onar('muhasebe@atalan.bel.t r adresine'), 'muhasebe@atalan.bel.tr adresine')
        self.assertEqual(onar('(https://ais.osym .gov.tr internet'), '(https://ais.osym.gov.tr internet')
        self.assertEqual(onar('e- Devlet üzerinden'), 'e-Devlet üzerinden')

    def test_dokunulmamasi_gerekenler(self):
        for s in ('2024 KPSS puanı (B grubu)', 'En az B sınıfı sürücü belgesi', 'a) Elektronik ortamda başvurular',
                  'Türk vatandaşı olmak.', 'o tarihte', 'İstanbul ve Edirne', 'KPSS P3 puan türünden en az 70 puan.',
                  'Ankara ili Pursaklar Belediye Başkanlığı', 'proje ve program'):
            self.assertEqual(onar(s), s)

    def test_okunamaz_metin(self):
        self.assertIsNone(onar('a) Elektronikortamdabaşvurular,16/10/2026-21/10/2026tarihleriarasındaistenilenbelgeler eklenmek '
                               'b)Şahsenveyaiadelitaahhütlüpostayoluileyapılacakbaşvurular'))
        self.assertIsNone(onar('S.N. Sınıfı Branşı Erkek Kadın Kontenjan Kuvvet Fakülte/Yüksekokul Bölüm Bilgileri ve Kaynak Okul Kodu'))
        self.assertEqual(onar('TALEP EDİLEN ÖĞRENİM MEZUN OLUNAN BÖLÜM KPSS PUAN DİĞER NİTELİKLER • En az %40 engelli olmak.'),
                         'En az %40 engelli olmak.')


if __name__ == '__main__':
    unittest.main()
