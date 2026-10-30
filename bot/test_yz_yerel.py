import unittest
from datetime import datetime

import yz_isle
import yz_yerel as yy
from site_uret import TR
from yz_denetim import SEMA, SURUM

SIMDI = datetime(2026, 10, 30, 20, 0, tzinfo=TR)
ILAN = {'id': 'csb-1', 'baslik': 'Örnek Belediyesi zabıta memuru alacak', 'kurum': 'Örnek Belediyesi',
        'kaynak_turu': 'csb', 'son_tarih': '2026-12-11', 'ilk_gorulme': '2026-10-30T19:30:00+03:00',
        'belgeler': [{'link': 'https://webdosya.csb.gov.tr/v2/yerelyonetimler/2026/10/ilan.docx'}]}
CEVAP = {'okunabilirlik': 'iyi', 'akademik': True, 'iptal_veya_duzeltme': True, 'duyuru_tipi': 'iptal',
         'son_basvuru_tarihi': '2026-12-01',
         'kadrolar': [{'unvan': 'Zabıta  Memuru', 'adet': 3, 'ogrenim': 'lisans', 'puan_turu': 'P3',
                       'kosullar': ['En az (B) sınıfı sürücü belgesine sahip olmak.', 'Kadın/Erkek']},
                      {'unvan': 'Zabıta Memuru', 'adet': 6, 'ogrenim': 'lisans', 'puan_turu': 'P3',
                       'kosullar': ['En az (B) sınıfı sürücü belgesine sahip olmak.']}],
         'ogrenim': ['lisans'], 'puan_turleri': ['P3'],
         'ortak_kosullar': ['Sınav tarihinde 30 yaşını doldurmamış olmak.', 'Yaş sınırı: Belirtilmemiş']}


class Sema(unittest.TestCase):
    def test_kisi_sayisi_ve_tarih_zorunlu(self):
        # boş bırakılabilir olunca gemma3 kişi sayısını ve tarihleri boş bırakıyordu (30 Ekim 2026 sınaması)
        kadro = yy.SEMA['properties']['kadrolar']['items']
        self.assertEqual(kadro['properties']['adet']['type'], 'integer')
        self.assertIn('adet', kadro['required'])
        self.assertTrue({'son_basvuru_tarihi', 'ozet', 'ortak_kosullar'} <= set(yy.SEMA['required']))

    def test_genel_sartlar_atilir(self):
        ortak = ['Türk vatandaşı olmak', '657 sayılı Kanun şartları', 'Askerlik durumu uygun olmak',
                 'Erkeklerde en az 1,67 m boy şartı.']
        self.assertEqual(yy._maddeler(ortak), ['Erkeklerde en az 1,67 m boy şartı.'])


class Temizle(unittest.TestCase):
    def test_model_ilani_durduramaz_tarihi_degistiremez(self):
        yz = yy.temizle(CEVAP, ILAN)
        self.assertEqual((yz['akademik'], yz['iptal_veya_duzeltme'], yz['duyuru_tipi']), (False, False, 'yeni_ilan'))
        self.assertNotIn('son_basvuru_tarihi', yz)   # bot tarihi biliyor
        self.assertIn('son_basvuru_tarihi', yy.temizle(CEVAP, dict(ILAN, son_tarih=None)))

    def test_dolgu_atilir_ayni_kadro_birlesir(self):
        yz = yy.temizle(CEVAP, ILAN)
        self.assertEqual(yz['ortak_kosullar'], ['Sınav tarihinde 30 yaşını doldurmamış olmak.'])
        self.assertEqual([(k['unvan'], k['adet']) for k in yz['kadrolar']], [('Zabıta Memuru', 9)])

    def test_ilan_geneli_kadrolardan_turetilir(self):
        yz = yy.temizle(dict(CEVAP, ogrenim=['ortaogretim', 'lisans', 'yuksek_lisans'], puan_turleri=['P3', 'P94'],
                             ozet='Model özeti'), ILAN)
        self.assertEqual((yz['ogrenim'], yz['puan_turleri']), (['lisans'], ['P3']))
        self.assertNotIn('ozet', yz)

    def test_kadrosuz_cevap_kotu_sayilir(self):
        self.assertEqual(yy.temizle(dict(CEVAP, kadrolar=[]), ILAN)['okunabilirlik'], 'kotu')


class Metin(unittest.TestCase):
    def test_csb_belgesi_okunur(self):
        import csb_kaynak
        eski = csb_kaynak.belge_metni
        csb_kaynak.belge_metni = lambda adres, veri: veri
        try:
            self.assertEqual(yy.metin_al(ILAN, csb_indir=lambda a: 'x' * 500), ('x' * 500, 'csb'))
            self.assertEqual(yy.metin_al(ILAN, csb_indir=lambda a: ''), ('', 'taranmis'))
        finally:
            csb_kaynak.belge_metni = eski

    def test_metinsiz_pdf_taranmis(self):
        import ek_kaynaklar
        eski = ek_kaynaklar.pdf_text
        ek_kaynaklar.pdf_text = lambda veri: 'kısa'
        try:
            self.assertEqual(yy.metin_al({'id': 'sbb-1'}, sbb_pdf=lambda i: b'%PDF-1.4'), ('', 'taranmis'))
        finally:
            ek_kaynaklar.pdf_text = eski

    def test_sbb_belgesi_henuz_inmediyse_beklenir(self):
        item = {'id': 'sbb-1', 'belge_kopyasi': 'https://kpsstercihi.com/belgeler/sbb/' + 'a' * 64 + '.pdf'}
        self.assertEqual(yy.metin_al(item, sbb_pdf=lambda i: None), ('', 'bekle'))


class Akis(unittest.TestCase):
    def test_okunan_kayit_yayina_esas_olur(self):
        veri = {}
        yeni = yy.oku([ILAN], {'csb-1'}, veri, 'gemma3:12b', SIMDI, cagir=lambda m, model, b: CEVAP,
                      metin=lambda i: ('metin', 'csb'))
        k = yeni['csb-1']
        self.assertEqual((k['surum'], k['model'], k['kaynak']), (SURUM, 'ollama:gemma3:12b', 'csb'))
        self.assertEqual(yz_isle.yayina_hazir(ILAN, veri, SIMDI), (True, ''))
        self.assertEqual(yz_isle.uygula(ILAN, veri, SIMDI)['kadro'], '9 Zabıta Memuru')
        # imza değişmedikçe yeniden okunmaz
        self.assertEqual(yy.oku([ILAN], set(), veri, 'gemma3:12b', SIMDI, cagir=None, metin=lambda i: 1 / 0), {})

    def test_taranmis_belge_ilani_bekletmez(self):
        veri = {}
        yy.oku([ILAN], set(), veri, 'gemma3:12b', SIMDI, cagir=lambda *a: 1 / 0, metin=lambda i: ('', 'taranmis'))
        self.assertEqual(yz_isle.yayina_hazir(ILAN, veri, SIMDI.replace(minute=40)), (True, ''))
        self.assertNotIn('yz_kadrolar', yz_isle.uygula(ILAN, veri, SIMDI))   # botun verisi kalır

    def test_model_hatasinda_kayit_yazilmaz(self):
        veri = {}
        yy.oku([ILAN], set(), veri, 'gemma3:12b', SIMDI, cagir=lambda *a: 1 / 0, metin=lambda i: ('metin', 'csb'))
        self.assertEqual(veri, {})

    def test_birlestir_en_yeni_okuma_kalir_eski_surum_atilir(self):
        uzak = {'a': {'zaman': '2026-10-30T10:00:00+03:00', 'x': 1, 'surum': SURUM},
                'b': {'zaman': '2026-10-30T12:00:00+03:00', 'surum': SURUM},
                'gemini': {'zaman': '2026-10-20T12:00:00+03:00', 'surum': SURUM - 1}}
        yeni = {'a': {'zaman': '2026-10-30T11:00:00+03:00', 'x': 2, 'surum': SURUM},
                'b': {'zaman': '2026-10-30T09:00:00+03:00', 'surum': SURUM}}
        sonuc = yy.birlestir(uzak, yeni)
        self.assertEqual(sonuc['a']['x'], 2)
        self.assertEqual(sonuc['b']['zaman'], '2026-10-30T12:00:00+03:00')
        self.assertNotIn('gemini', sonuc)

    def test_eski_surumlu_gemini_kaydi_yayina_girmez(self):
        veri = {'csb-1': {'surum': SURUM - 1, 'zaman': '2026-10-20T12:00:00+03:00', 'yz': CEVAP}}
        self.assertIs(yz_isle.uygula(ILAN, veri, SIMDI), ILAN)


if __name__ == '__main__':
    unittest.main()
