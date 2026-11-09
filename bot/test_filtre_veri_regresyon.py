"""Arama/filtre denetimi F05–F06 (9 Kasım 2026): öğrenim sınıflandırma, kaynak kopyası, KPSS/YDS puan ayrımı."""
import unittest

import ilan_bakis
import kopya
from siniflandir import ogrenim_seviyeleri


class OgrenimBasliktan(unittest.TestCase):
    def test_en_az_dort_yil_sureli_fakulte_lisanstir(self):
        i = {'baslik': 'MİLLÎ SAVUNMA BAKANLIĞI - TÜRK SİLAHLI KUVVETLERİNE EN AZ DÖRT YIL SÜRELİ FAKÜLTE VEYA YÜKSEKOKUL '
                       'MEZUNLARINDAN 2026 YILI BANDO SINIFI MUVAZZAF ASTSUBAY ADAYI TEMİNİ'}
        self.assertIn('lisans', ogrenim_seviyeleri(i))

    def test_belirsiz_fakulte_veya_yuksekokul_lisans_sayilmaz(self):
        i = {'baslik': 'MİLLÎ SAVUNMA BAKANLIĞI - TÜRK SİLAHLI KUVVETLERİNE FAKÜLTE VEYA YÜKSEKOKUL MEZUNLARINDAN ASTSUBAY ADAYI TEMİNİ'}
        self.assertEqual(ogrenim_seviyeleri(i), [])


class TurkseKerKopyasi(unittest.TestCase):
    def test_iskur_kurum_adindaki_unvan_eki_cekirdegi_bozmaz(self):
        a = {'kurum': 'TÜRKİYE ŞEKER FABRİKALARI A.Ş. GENEL MÜDÜRLÜĞÜ'}
        b = {'kurum': 'Türkiye Şeker Fabrikaları A.Ş. Sözleşmeli Mühendis ve Tekniker'}
        self.assertEqual(kopya._kurum_cekirdek(a, 'x'), kopya._kurum_cekirdek(b, 'y'))

    def test_farkli_sirketler_ayri_kalir(self):
        a = {'kurum': 'Türkiye Şeker Fabrikaları A.Ş.'}
        b = {'kurum': 'Türkiye Çimento Fabrikaları A.Ş.'}
        self.assertNotEqual(kopya._kurum_cekirdek(a, 'x'), kopya._kurum_cekirdek(b, 'y'))


class KpssYdsPuani(unittest.TestCase):
    def _puan(self, metin):
        item = {'yz_ortak': [metin]}
        return dict(ilan_bakis.bilgiler(item)).get('En düşük puan')

    def test_yds_puani_kpss_esigi_sayilmaz(self):
        self.assertEqual(self._puan('YDS\'den en az 50 puan almış olmak. KPSS\'den en az 70 puan almış olmak.'), '70')

    def test_yalniz_yds_varsa_esik_gosterilmez(self):
        self.assertIsNone(self._puan('YDS\'den en az 50 puan almış olmak.'))


if __name__ == '__main__':
    unittest.main()
