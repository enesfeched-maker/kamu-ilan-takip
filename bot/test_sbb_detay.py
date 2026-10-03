import unittest
from unittest.mock import patch,MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from sbb_detay import summarize,document_url,BASE
from site_uret import detail_page

class SbbDetailTests(unittest.TestCase):
    def test_justified_column_starts_above_job_number(self):
        text=('2547 sayılı kanuna göre başvuran doçentlerin lisans belgelerini sunması gerekir.\n\n'
              '                                                      Doçentliğini    Turizm    Alanında    Almış\n'
              '1001    Turizm Fakültesi       Profesör     1    1     Olmak. Gastronomi alanında çalışmış olmak.\n\n'
              '- Öğretim görevlisi adaylarında lisans ve yüksek lisans derecesini birlikte veren programlardan')
        page=MagicMock();page.extract_text.return_value=text
        with TemporaryDirectory() as folder,patch('sbb_detay.ROOT',Path(folder)),patch('sbb_detay.PdfReader') as reader:
            reader.return_value.pages=[page]
            result=summarize(b'%PDF-test',{'kadro':'1 profesör'})
        self.assertEqual(len(result['sartlar']),1)
        self.assertTrue(result['sartlar'][0]['metin'].startswith('Doçentliğini Turizm'))
        self.assertNotIn('programlardan',str(result['sartlar']))

    def test_application_excludes_post_exam_preferences_and_reads_bullets(self):
        text=('Yazılı sınavda başarılı olan adaylar tarafından yapılacak yer (ilçe) tercihi başvuruları '
              'sınav sonuçları ilan edildikten sonra Online Sınav Sistemi üzerinden yapılacaktır.\n\n'
              'III - SINAV BAŞVURU ŞARTLARI\n'
              ' - En az dört yıllık lisans eğitimi veren hukuk fakültesini bitirmiş olmak,\n'
              ' - KPSSP17 puan türünden 65 ve üzeri puan almış olmak,\n'
              ' - 35 yaşını doldurmamış olmak,\n'
              ' - Adaylar ön başvurularını ÖSYM internet adresinden T.C. kimlik numarası ile elektronik ortamda yapacaklardır.')
        page=MagicMock();page.extract_text.return_value=text
        with TemporaryDirectory() as folder,patch('sbb_detay.ROOT',Path(folder)),patch('sbb_detay.PdfReader') as reader:
            reader.return_value.pages=[page]
            result=summarize(b'%PDF-test',{'kadro':'860 uzman yardımcısı'})
        self.assertIn('ÖSYM',result['ozet'])
        self.assertNotIn('ilçe',result['ozet'])
        self.assertIn('hukuk',str(result['sartlar']))
        self.assertIn('KPSSP17',str(result['sartlar']))

    def test_table_columns_keep_requirements_with_correct_job(self):
        text=('1001    Öğretim Görevlisi       1                      Zootekni lisans mezunu olmak.\n'
              '                                                      Zootekni alanında doktora yapmış olmak.\n\n'
              '1002    Araştırma Görevlisi     1                      Endüstri Mühendisliği mezunu olmak.\n\n'
              'Adaylar başvurularını şahsen veya posta yoluyla yapabilirler.')
        page=MagicMock();page.extract_text.return_value=text
        with TemporaryDirectory() as folder,patch('sbb_detay.ROOT',Path(folder)),patch('sbb_detay.PdfReader') as reader:
            reader.return_value.pages=[page]
            result=summarize(b'%PDF-test',{'kadro':'2 öğretim elemanı','son_tarih':'2026-10-01'})
            self.assertEqual(len(result['sartlar']),2)
            self.assertIn('Zootekni',result['sartlar'][0]['metin'])
            self.assertNotIn('Endüstri',result['sartlar'][0]['metin'])
            self.assertIn('Endüstri',result['sartlar'][1]['metin'])
            self.assertIn('şahsen veya posta',result['ozet'])
            self.assertEqual(next((Path(folder)/'docs/belgeler/sbb').glob('*.pdf')).read_bytes(),b'%PDF-test')

    def test_document_link_is_narrow_and_static_page_opens_document(self):
        link=BASE+'belgeler/sbb/'+'a'*64+'.pdf'
        self.assertIsNone(document_url({'belge_kopyasi':BASE+'../secret'}))
        self.assertIsNone(document_url({'belge_kopyasi':'https://evil.test/a.pdf'}))
        item={'id':'sbb-'+'b'*24,'link':'https://kamuilan.sbb.gov.tr/','kaynak_turu':'sbb','belge_kopyasi':link}
        html=detail_page(item)[1]
        self.assertIn('href="'+link+'"',html)
        self.assertNotIn('kurum adıyla ara',html)

class DuyuruCumlesiTests(unittest.TestCase):
    def test_adana_cumlesi_kesilir(self):
        from sbb_detay import duyuru_cumlesi_bul
        s=duyuru_cumlesi_bul(['Adana … Rektörlüğünden: \nİPTAL İLANI \n20.09.2026 tarihli ve 33376 sayılı Resmi Gazete’de yayımlanan ve aşağıda belirtilen 6 \nSıra Nolu Havacılık … Anabilim Dalı 1 (bir) adet Araştırma Görevlisi kadrosu ilanımız iptal edilmiştir. \nS.NO BİRİM'])
        self.assertTrue(s.endswith('Araştırma Görevlisi kadrosu ilanımız iptal edilmiştir.'))
        self.assertNotIn('S.NO',s)

    def test_ytu_tarzi_fiilden_sonra_kesilir(self):
        from sbb_detay import duyuru_cumlesi_bul
        s=duyuru_cumlesi_bul(['Kadro nitelikleri aşağıdaki şekilde değiştirilmiştir. (*) : 23.03.2016 tarih ve 29662 sayılı'])
        self.assertTrue(s.endswith('değiştirilmiştir.'))
        self.assertNotIn('(*)',s)

    def test_gelecek_zamanli_cumle_eslesmez(self):
        from sbb_detay import duyuru_cumlesi_bul
        self.assertEqual(duyuru_cumlesi_bul(['Atamaları yapılmış olsa dahi iptal edilecektir.']),'')

    def test_bolunmus_fiil_eslesir(self):
        from sbb_detay import duyuru_cumlesi_bul
        self.assertIn('iptal edilmiş tir.',duyuru_cumlesi_bul(['Zabıta alımı ilanı iptal edilmiş  tir. Başka cümle.']))

    def test_gercek_adana_pdf(self):
        from sbb_detay import belge_cumlesi,ROOT
        sha='e94b91e9153ca7114a409d7a187a600cd357a4ee8985bfef4a4f9bb174c0967f'
        if not (ROOT/'docs'/'belgeler'/'sbb'/(sha+'.pdf')).exists():self.skipTest('PDF yok')
        self.assertIn('Araştırma Görevlisi',belge_cumlesi({'belge_sha256':sha}))
        self.assertIsNone(belge_cumlesi({'belge_sha256':'../x'}))


if __name__=='__main__':unittest.main()
