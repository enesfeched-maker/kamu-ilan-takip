import io,json,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from PIL import Image
import ilan_bot
from ilan_baglanti import ilan_sayfasi
from kurum_gorseli import logo_url,kurum_anahtari
from ilan_gorsel import gorsel_olustur
from yerel_kaynak import sbb_verisi,taze
from yerel_tara import publish

class LocalPublishingTests(unittest.TestCase):
    def test_detail_routes_match_static_pages(self):
        base='https://enesfeched-maker.github.io/kamu-ilan-takip/'
        key='39a092b0-f2b1-4f11-a125-1e6e3a6ad020'
        for item,expected in [({'id':'source-id','link':'https://kariyerkapisi.gov.tr/IlanDetay?i='+key},key),({'id':'sbb-'+'a'*24,'link':'https://kamuilan.sbb.gov.tr/'},'sbb-'+'a'*24)]:
            self.assertEqual(ilan_sayfasi(item,base),base+'ilan/'+expected+'/')
        with self.assertRaises(ValueError):ilan_sayfasi({'id':'../../x'},base)

    def test_telegram_primary_button_targets_own_detail(self):
        url='https://enesfeched-maker.github.io/kamu-ilan-takip/ilan/sbb-'+'a'*24+'/'
        with patch.object(ilan_bot.urllib.request,'urlopen',return_value=io.BytesIO(b'{"ok":true}')) as api:
            ilan_bot.telegram_gonder('test','test','test',url,'https://enesfeched-maker.github.io/kamu-ilan-takip/',foto=b'PNG')
        data=api.call_args.args[0].data.decode(errors='replace')
        self.assertIn(url,data);self.assertIn('İlanı incele',data)
        self.assertNotIn('kamuilan.sbb.gov.tr',data)

    def test_old_and_future_local_snapshots_are_rejected(self):
        now=datetime.now(timezone.utc)
        self.assertFalse(taze((now-timedelta(minutes=91)).isoformat()))
        self.assertFalse(taze((now+timedelta(minutes=10)).isoformat()))
        row={'id':'sbb-a','baslik':'Örnek','link':'https://kamuilan.sbb.gov.tr/'}
        data={'kaynaklar':{'sbb':{'kontrol':now.isoformat(),'ilanlar':[row],'hata_sayisi':0}}}
        self.assertEqual(sbb_verisi(data)[0],[row])
        data['kaynaklar']['sbb']['kontrol']=(now-timedelta(hours=2)).isoformat()
        self.assertIsNone(sbb_verisi(data))

    def test_local_upload_does_not_write_delivery_history(self):
        with patch('yerel_tara.github',side_effect=[{'sha':'current'},{}]) as api:
            publish({'schema':1,'kaynaklar':{}},'test')
        self.assertEqual(api.call_args.args[0],'docs/yerel-kaynaklar.json')
        self.assertEqual(api.call_args.args[2]['sha'],'current')

    def test_official_logos_only_and_small_area(self):
        for url in ['https://evil.test/logo.png','https://kariyerkapisi.gov.tr.evil.test/UPS/x.png','https://kariyerkapisi.gov.tr/../secret']:
            with self.assertRaises(ValueError):logo_url(url)
        self.assertEqual(kurum_anahtari('BOĞAZİÇİ ÜNİVERSİTESİ REKTÖRLÜĞÜ'),kurum_anahtari('Boğaziçi Üniversitesi'))
        raw=io.BytesIO();Image.new('RGBA',(600,300),'red').save(raw,format='PNG')
        image=Image.open(io.BytesIO(gorsel_olustur('Örnek Kurum','10 memur','Ankara','30 Eylül 2026',logo=raw.getvalue())))
        self.assertEqual(image.getpixel((1017,171)),(255,0,0))
        self.assertEqual(image.getpixel((870,171)),(16,43,53))

if __name__=='__main__':unittest.main()
