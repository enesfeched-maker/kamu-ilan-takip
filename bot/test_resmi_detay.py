import unittest
from datetime import datetime
from unittest.mock import patch
from resmi_detay import detay_coz, detay_oku, satirlar
import ilan_bot


class ResmiDetayTests(unittest.TestCase):
    def test_kadro_sartlari_genellenmez_ve_kontenjan_toplanir(self):
        ana = {'ilanBaslik': 'ÖRNEK İLAN', 'ilanMetni': '[b]Başvurular şahsen yapılacaktır.[/b]',
               'bitTarih': '2026-10-09T13:00:00', 'basTarih': '2026-09-24T09:00:00'}
        alt = [
            {'unvan': 'DESTEK PERSONELİ', 'ilanBaslik': 'Şoför',
             'ilanMetni': '[b]ŞARTLAR[/b]\nKPSS P94 en az 60 puan.\nLise mezunu olmak.',
             'kontenjanList': [{'il': 'NİĞDE / MERKEZ', 'kontenjan': 2}]},
            {'unvan': 'SAĞLIK TEKNİKERİ', 'ilanBaslik': 'Diş Protez Teknikeri',
             'ilanMetni': 'KPSS P93 en az 70 puan.\nDiş Protez ön lisans mezunu olmak.',
             'kontenjanList': [{'il': 'NİĞDE / MERKEZ', 'kontenjan': 3}]}]
        d = detay_coz(ana, alt)
        self.assertEqual(d['son_zaman'], '2026-10-09T13:00:00+03:00')
        self.assertEqual(d['yer'], 'NİĞDE / MERKEZ')
        self.assertIn('Toplam 5 kişi', d['kadro'])
        self.assertIn('P94 en az 60', d['sartlar'][0]['metin'])
        self.assertNotIn('70 puan', d['sartlar'][0]['metin'])
        self.assertIn('P93 en az 70', d['sartlar'][1]['metin'])
        self.assertEqual(d['basvuru_notu'], 'Başvurular şahsen yapılacaktır.')

    def test_yalniz_resmi_adres(self):
        with patch('resmi_detay.api_oku') as api:
            with self.assertRaises(ValueError):
                detay_oku('https://example.com/IlanDetay?i=69465191-48a2-447c-8f55-edb2ecbeb45a')
            api.assert_not_called()

    def test_saat_bazinda_kapanan_ilan_gonderilmez(self):
        with patch.object(ilan_bot, 'simdi', return_value=datetime.fromisoformat('2026-09-24T14:00:00+03:00')):
            self.assertTrue(ilan_bot.suresi_doldu({'son_zaman': '2026-09-24T13:00:00+03:00'}))
            self.assertFalse(ilan_bot.suresi_doldu({'son_zaman': '2026-09-24T17:00:00+03:00'}))

    def test_bicimlendirme_kodu_mesaja_sizmaz(self):
        self.assertEqual(satirlar('[justify][size=14pt][b]ŞARTLAR[/b]\nA &amp; B<br>KPSS[/size][/justify]'),
                         ['ŞARTLAR', 'A & B', 'KPSS'])


if __name__ == '__main__':
    unittest.main()


class GenelSartlarAnaMetinden(unittest.TestCase):
    def test_ana_metindeki_genel_sartlar_ortaga_gecer(self):
        ana = {'ilanBaslik': 'X - SÖZLEŞMELİ BİLİŞİM PERSONELİ', 'basTarih': '2026-10-22T09:00:00', 'bitTarih': '2026-11-06T23:59:00',
               'ilanMetni': 'SÖZLEŞMELİ BİLİŞİM PERSONELİ ALIMI\nA. GENEL ŞARTLAR\n'
                            'a) 657 sayılı Devlet Memurları Kanunu’nun 48 inci maddesinde sayılan genel şartları haiz olması,\n'
                            'b) Güncel programlama dillerinden en az ikisini bildiğini belgelemeleri zorunludur.\n'
                            'B. ÖZEL ŞARTLAR\na. Yazılım Uzmanı (1 Kişi)\n1. En az 5 yıllık mesleki tecrübeye sahip olduğunu belgelemek,\n'}
        alt = [{'ilanBaslik': 'Yazılım Uzmanı', 'unvan': 'YAZILIM UZMANI', 'kontenjanList': [{'il': 'ANKARA', 'kontenjan': 1}],
                'ilanMetni': 'Unvanı: Yazılım Uzmanı\nÖzel Şartları:\n1. En az 5 yıllık mesleki tecrübeye sahip olduğunu belgelemek,\n'}]
        sonuc = detay_coz(ana, alt)
        basliklar = [b for b, _ in sonuc.get('kadro_ortak', [])]
        self.assertTrue(any('GENEL' in b.upper() for b in basliklar), basliklar)
