import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import ek_kaynaklar as ek
import ilan_bot
from site_uret import detail_page
from veri_kaydet import merge_registry


class SourceTests(unittest.TestCase):
    def test_official_url(self):
        for url in ['https://iskur.gov.tr.evil.test/x','http://www.iskur.gov.tr/x','https://u:p@www.iskur.gov.tr/x']:
            with self.assertRaises(ValueError):
                ek.safe_url(url)
        self.assertIn('%C4%B1',ek.safe_url('/medya/alım.pdf',ek.ISKUR))

    def test_iskur_urgent_row(self):
        doc='<tr class="clickable-row" data-has-file="True" data-file-url="/medya/ilan.pdf"><td>30.09.2026 17:00 (son 3 gün kaldı)</td><td>Örnek Belediyesi Memur Alım İlanı 30.09.2026</td></tr>'
        item=ek.iskur_rows(doc,'Ankara')[0]
        self.assertEqual(item['son_zaman'],'2026-09-30T17:00:00+03:00')
        self.assertEqual(item['kurum'],'Örnek Belediyesi')
        self.assertIsNotNone(detail_page(item))

    def test_pdf_year_must_be_established(self):
        with patch.object(ek,'now',return_value=datetime(2026,9,26,tzinfo=ek.TR)):
            self.assertEqual(ek.pdf_dates('2026 KPSS ve 15 gün','(24 Eylül - 9 Ekim)'),{})
            self.assertEqual(ek.pdf_dates('24.09.2026','(24 Eylül - 9 Ekim)')['son_tarih'],'2026-10-09')
            self.assertEqual(ek.pdf_dates('20.12.2026','(20 Aralık - 4 Ocak)')['son_tarih'],'2027-01-04')

    def test_institution_names(self):
        for name in ['Türkiye İnsan Hakları ve Eşitlik Kurumu','Türkiye Belediyeler Birliği','Cumhurbaşkanlığı İletişim Başkanlığı','Gençlik ve Spor Bakanlığı']:
            self.assertEqual(ek.institution(name+' Personel Alım İlanı'),name)

    def test_root_links_do_not_merge_unrelated_jobs(self):
        a={'id':'a','baslik':'A üniversitesi','kurum':'A','link':ek.SBB,'son_tarih':None}
        b={**a,'id':'b','baslik':'B üniversitesi','kurum':'B'}
        self.assertFalse(ek.same_listing(a,b))
        self.assertEqual(len(ek.merge_sources([a,b],{})),2)

    def test_source_merge_preserves_sent_identity(self):
        a={'id':'old','baslik':'Örnek Belediyesi memur alımı','kurum':'Örnek Belediyesi','son_tarih':'2026-10-09','kadro':'3 memur','kaynak_turu':'sbb','link':ek.SBB}
        b={**a,'id':'new','kaynak_turu':'iskur','link':'https://www.iskur.gov.tr/medya/x.pdf','kadro':''}
        merged=ek.merge_sources([b],{'old':a})
        self.assertEqual(merged[0]['id'],'old')
        reminder=json.dumps(['new','2026-10-09'])
        state=merge_registry({'ilanlar':[b],'telegram_gonderilen':['new'],'telegram_hatirlatilan':[reminder]}, {'ilanlar':merged})
        self.assertEqual([i['id'] for i in state['ilanlar']],['old'])
        self.assertIn('old',state['telegram_gonderilen'])
        self.assertIn(json.dumps(['old','2026-10-09']),state['telegram_hatirlatilan'])

    def test_silent_baseline_then_only_new_messages(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Path(d)/'config.json'; data=Path(d)/'ilanlar.json'
            cfg.write_text(json.dumps({'rss_urls':[],'ek_kaynaklar':['sbb','iskur']}))
            data.write_text(json.dumps({'guncelleme':'2026-09-26','ilanlar':[]}))
            item={'id':'sbb-'+24*'a','baslik':'Örnek kurum alımı','kurum':'Örnek','link':ek.SBB,'son_tarih':None,'kaynak_turu':'sbb','kaynak':'SBB Kamu İlan'}
            with patch.object(ilan_bot,'CONFIG_YOLU',cfg), patch.object(ilan_bot,'read_sbb',return_value=([item],0)) as source, patch.object(ilan_bot,'read_iskur',return_value=([],0)), patch.object(ilan_bot,'telegram_gonder',return_value=True) as send, patch.object(ilan_bot,'gorsel_olustur',return_value=b'PNG'), patch.object(ilan_bot.time,'sleep'), patch.dict('os.environ',{'RSS_URLS':'','TELEGRAM_BOT_TOKEN':'test','TELEGRAM_CHAT_ID':'test'}), patch('sys.argv',['bot','--cikti',str(data)]), contextlib.redirect_stdout(io.StringIO()):
                ilan_bot.main()
                self.assertEqual(send.call_count,0)
                self.assertEqual(json.loads(data.read_text())['kaynak_baslangiclari'],['iskur','sbb'])
                source.return_value=([item,{**item,'id':'sbb-'+24*'b','baslik':'Başka kurum alımı'}],0)
                ilan_bot.main()
                self.assertEqual(send.call_count,1)
                ilan_bot.main()
                self.assertEqual(send.call_count,1)

    def test_notice_has_no_reminder(self):
        self.assertIsNone(ilan_bot.hatirlatma_anahtari({'duyuru_turu':'İptal duyurusu'}))


if __name__=='__main__':
    unittest.main()

