import unittest

import ilan_bakis as ib
from siniflandir import saf_akademik


class Bakis(unittest.TestCase):
    def test_kadroya_ozel_yas_sarti_tum_ilana_genellenmez(self):
        item = {'basvuru_kisa_sartlar': ['D01/D02: 30 yaş altı'],
                'yz_kadrolar': [{'kosullar': ['Son başvuru tarihinde 30 yaşını doldurmamış olmak.']}]}
        self.assertEqual(ib.sart_kelimeleri(item), ['D01/D02: 30 yaş altı'])

    def test_sozlu_sinav_puani_basvuru_tabani_degil(self):
        item = {'basvuru_puani_belirtilmemis': True, 'ozet': 'Sözlü sınavda en az 70 puan gerekir.'}
        self.assertNotIn(('En düşük puan', '70'), ib.bilgiler(item))

    def test_engellilerde_spor_programi_engelli_kadrosu_degil(self):
        item = {'yz_kadrolar': [{'kosullar': ['Engellilerde beden eğitimi ve spor öğretmenliği mezunu olmak.']}]}
        self.assertNotIn('Engelli kadrosu', ib.sart_kelimeleri(item))
        self.assertIn('Engelli kadrosu', ib.sart_kelimeleri({'ozet': '5 engelli işçi alımı'}))

    def test_sart_kelimeleri(self):
        item = {'yz_ortak': ['35 yaşını doldurmamış olmak.', 'Erkek adaylar için askerlik şartı.'],
                'yz_kadrolar': [{'kosullar': ['B sınıfı sürücü belgesine sahip olmak.', 'En az 3 yıl mesleki deneyim.',
                                              'Boy 1.65 m olmak.']}]}
        self.assertEqual(ib.sart_kelimeleri(item), ['35 yaş altı', 'Yalnız erkek', 'B sınıfı ehliyet', '3 yıl deneyim',
                                                    'Boy-kilo şartı'])

    def test_bolum(self):
        item = {'ozet': 'Başvurular Kariyer Kapısı üzerinden yapılır. 2025 KPSS P3 en az 60 puan almış olmak.'}
        html = ib.bolum_html(item, toplam=12)
        self.assertIn('12 kişi', html)
        self.assertIn('Kariyer Kapısı', html)
        self.assertIn('>60<', html)
        self.assertEqual(ib.bolum_html({'ozet': 'x'}), '')
        self.assertEqual(ib.bolum_html(dict(item, duyuru_turu='İptal'), toplam=12), '')

    def test_saf_akademik(self):
        self.assertTrue(saf_akademik({'baslik': 'X Üniversitesi Öğretim Üyesi Alım İlanı'}))
        self.assertFalse(saf_akademik({'baslik': 'X Üniversitesi Öğretim Üyesi Alım İlanı', 'duyuru_turu': 'İptal'}))
        self.assertFalse(saf_akademik({'baslik': 'X Belediyesi Zabıta Memuru Alım İlanı'}))


if __name__ == '__main__':
    unittest.main()


class CokPozisyonluSartlar(unittest.TestCase):
    """Kariyer Kapısı sözleşmeli bilişim (gerçek ilan metinlerinden kısaltılmış): şart pozisyona özgüyse hepsine yazılmaz."""
    ORTAK = [['GENEL ŞARTLAR', ['657 sayılı Devlet Memurları Kanunu’nun 48 inci maddesinde sayılan genel şartları haiz olması,',
                                'Erkek adaylar için askerlik durumu itibariyle askerlikle ilgisi bulunmamak,']]]

    def kadrolar(self, *maddeler):
        return [{'unvan': f'Kadro {n}', 'maddeler': list(m)} for n, m in enumerate(maddeler, 1)]

    def test_yalniz_bir_pozisyondaki_sertifika_bazi_kadrolarda_yazilir(self):
        item = {'kadro_ortak': self.ORTAK, 'kadro_detay': self.kadrolar(['Siber güvenlik alanında sertifika sahibi olmak.'], ['Linux bilgisine sahip olmak.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['Bazı kadrolarda sertifika'])

    def test_her_pozisyonda_olan_sart_duz_yazilir(self):
        item = {'kadro_detay': self.kadrolar(['CISSP sertifikası sahibi olmak.'], ['ISO 27001 sertifikası sahibi olmak.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['Sertifika'])

    def test_ortak_genel_sartlardaki_yas_tum_kadrolara_yazilir(self):
        ortak = [['GENEL ŞARTLAR', ['Son başvuru tarihi itibarıyla 35 yaşını doldurmamış olmak.']]]
        item = {'kadro_ortak': ortak, 'kadro_detay': self.kadrolar(['Linux bilgisi.'], ['Ağ bilgisi.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['35 yaş altı'])

    def test_erkek_adaylar_icin_askerlik_genel_sarti_yalniz_erkek_degildir(self):
        item = {'kadro_ortak': self.ORTAK, 'kadro_detay': self.kadrolar(['Linux bilgisi.'], ['Ağ bilgisi.'])}
        self.assertEqual(ib.sart_kelimeleri(item), [])

    def test_pozisyonlara_gore_degisen_yas_ve_ehliyet_sinifi(self):
        item = {'kadro_detay': self.kadrolar(['40 yaşını doldurmamış olmak.', 'B sınıfı sürücü belgesine sahip olmak.'],
                                             ['35 yaşını doldurmamış olmak.', 'D sınıfı sürücü belgesine sahip olmak.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['Kadroya göre yaş sınırı var', 'Kadroya göre sürücü belgesi'])

    def test_bazi_pozisyonlarda_sinif_harfi_buyuk_kalir(self):
        item = {'kadro_detay': self.kadrolar(['B sınıfı sürücü belgesine sahip olmak.'], ['Ağ bilgisi.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['Bazı kadrolarda B sınıfı ehliyet'])

    def test_ucret_tavanina_gore_3_ya_da_5_yil_tek_yila_indirgenmez(self):
        # Burdur Mehmet Akif Ersoy Ü. (28 Ekim 2026): '3 yıllık, diğerleri için 5 yıllık' -> eskiden '5 yıl deneyim' yazılıyordu.
        metin = ('Büyük ölçekli bilgi işlem merkezlerinde, ücret tavanı iki katını geçemeyecekler için en az 3 yıllık, '
                 'diğerleri için en az 5 yıllık mesleki tecrübeye sahip bulunması')
        item = {'kadro_ortak': [['GENEL ŞARTLAR', [metin]]], 'kadro_detay': self.kadrolar(['Linux bilgisi.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['Kadroya göre 3–5 yıl deneyim'])

    def test_ortakta_tek_yil_varsa_hepsi_icin_yazilir(self):
        item = {'kadro_ortak': [['GENEL ŞARTLAR', ['En az 5 (beş) yıl mesleki tecrübeye sahip bulunmak.']]],
                'kadro_detay': self.kadrolar(['Linux bilgisi.'], ['Ağ bilgisi.'])}
        self.assertEqual(ib.sart_kelimeleri(item), ['5 yıl deneyim'])


class CokPozisyonluDeneyim(unittest.TestCase):
    def test_tek_kadronun_yili_hepsine_yazilmaz(self):
        item = {'kadro_detay': [
            {'unvan': 'Kıdemli Ağ Uzmanı', 'maddeler': ['En az 10 (on) yıllık mesleki tecrübeye sahip olduğunu belgelemek.']},
            {'unvan': 'Sistem Uzmanı', 'maddeler': ['En az 3 yıl tecrübeye sahip olmak.']}]}
        self.assertIn('Kadroya göre 3–10 yıl deneyim', ib.sart_kelimeleri(item))
        self.assertNotIn('10 yıl deneyim', ib.sart_kelimeleri(item))

    def test_hepsinde_ayni_yil_tek_etiket(self):
        item = {'kadro_detay': [{'unvan': 'A', 'maddeler': ['En az 3 yıl tecrübeye sahip olmak.']},
                                {'unvan': 'B', 'maddeler': ['En az 3 yıl deneyim.']}]}
        self.assertIn('3 yıl deneyim', ib.sart_kelimeleri(item))
