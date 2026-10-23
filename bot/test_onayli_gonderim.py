import unittest
from unittest.mock import patch

import ilan_bot
from onayli_ilanlari_gonder import dogrula


class OnayliGonderim(unittest.TestCase):
    def test_iskur_beklemesi_yalniz_elle_onayli_kimlik_icin_atlanir(self):
        a={'id':'iskur-'+'a'*24,'kurum':'Orman Genel Müdürlüğü','baslik':'12 Müfettiş Yardımcısı',
           'kaynak_turu':'iskur','son_tarih':'2099-01-01','kadro':'12 Müfettiş Yardımcısı'}
        b=dict(a,id='iskur-'+'b'*24)
        cfg={'elle':{'alanlar':{a['id']:{'telegram_hemen':True}}}}
        with patch.object(ilan_bot,'iskur_bekliyor',return_value=True), \
             patch.object(ilan_bot,'kopyalari_ele',side_effect=lambda rows,*args:rows), \
             patch.object(ilan_bot,'tekrarlari_ele',side_effect=lambda rows,*args:rows):
            rows=ilan_bot.telegram_sirasi({a['id']:a,b['id']:b},[a,b],[],set(),{a['id'],b['id']},False,False,cfg)
        self.assertEqual([i['id'] for i in rows],[a['id']])

    def test_eski_canli_sayfada_gonderim_baslamaz(self):
        item={'id':'iskur-'+'a'*24,'link':'https://www.iskur.gov.tr/x.pdf'}
        alan={'yz_kadrolar':[{'adet':12}],'son_tarih':'2026-11-09','ogrenim':['lisans']}
        with self.assertRaisesRegex(RuntimeError,'henüz güncel değil'):
            dogrula(item,alan,{'ilanlar':[{'key':item['id'],'toplam':1,'son_tarih':'2026-11-09'}]})


if __name__=='__main__': unittest.main()
