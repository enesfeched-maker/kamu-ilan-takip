import unittest
from unittest.mock import patch,MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
from sbb_detay import summarize,document_url,BASE
from site_uret import detail_page

class SbbDetailTests(unittest.TestCase):
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

if __name__=='__main__':unittest.main()
