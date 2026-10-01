import json,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import csb_kaynak as csb
import ek_kaynaklar as ek
import ilan_bot
from ilan_baglanti import ilan_sayfasi
from site_uret import detail_page
from yerel_kaynak import csb_verisi,sbb_verisi

VERI=Path(__file__).parent/'test_veri'
SITE='https://yerelyonetimler.csb.gov.tr/'


def oku(ad):
    return (VERI/ad).read_bytes()


def satir(numara,html_adi):
    return {'numara':numara,'link':SITE+'x-duyuru-'+numara,'baslik':'','yayim':'2026-09-29'},oku(html_adi)


class ListeTesti(unittest.TestCase):
    def test_gercek_liste_ayristirilir(self):
        satirlar=csb.liste_ayristir(oku('csb_liste.html'))
        self.assertEqual(len(satirlar),12)
        self.assertEqual(len({s['numara'] for s in satirlar}),12)
        ilk=satirlar[0]
        self.assertEqual(ilk['numara'],'478009')
        self.assertEqual(ilk['yayim'],'2026-10-01')
        self.assertTrue(ilk['link'].startswith(SITE) and ilk['link'].endswith('-duyuru-478009'))
        self.assertFalse(ilk['baslik'].endswith('.'))

    def test_sayfalanan_kart_listesi_ayristirilir(self):
        satirlar=csb.liste_ayristir(oku('csb_liste_sayfa2.html'))
        self.assertEqual(len(satirlar),12)
        self.assertTrue(all(s['yayim'] and s['baslik'] and s['link'].startswith(SITE) for s in satirlar))
        self.assertIn('477477',{s['numara'] for s in satirlar})
        self.assertEqual(next(s for s in satirlar if s['numara']=='477477')['yayim'],'2026-09-09')

    def test_site_disi_href_tek_karti_atlatir(self):
        html=oku('csb_liste.html').decode('utf-8')
        import re
        slug=re.search(r'href="https://yerelyonetimler\.csb\.gov\.tr/([^"]*-duyuru-\d+)"',html).group(1)
        bozuk=html.replace('href="https://yerelyonetimler.csb.gov.tr/'+slug+'"','href="https://evil.test/'+slug+'"')
        # bir duyurunun (kaydırıcı ve liste kopyası) bağlantısı site dışı; diğer 11 kart okunmalı
        satirlar=csb.liste_ayristir(bozuk)
        self.assertEqual(len(satirlar),11)

    def test_bos_liste_hata_verir(self):
        with self.assertRaises(ValueError):
            csb.liste_ayristir('<html><body>bakım</body></html>')

    def test_dis_alan_adi_reddedilir(self):
        with self.assertRaises(ValueError):
            csb.guvenli_adres('https://evil.test/x-duyuru-1')
        with self.assertRaises(ValueError):
            csb.guvenli_adres('http://yerelyonetimler.csb.gov.tr/x')

    def test_tarih(self):
        self.assertEqual(csb.tarih_coz('01 Ekim 2026 Perşembe'),'2026-10-01')
        self.assertEqual(csb.tarih_coz('29 Eylül 2026'),'2026-09-29')
        self.assertIsNone(csb.tarih_coz('tarih yok'))


class BaslikTesti(unittest.TestCase):
    def test_il_kurum_tur(self):
        p=csb.baslik_coz('İSTANBUL İLİ ŞİLE BELEDİYE BAŞKANLIĞINA İLK DEFA ATANMAK ÜZERE ZABITA MEMURU ALIMI İLANI')
        self.assertEqual((p['il'],p['kurum']),('İstanbul','ŞİLE BELEDİYE BAŞKANLIĞI'))
        self.assertTrue(p['kalan'].startswith('İLK DEFA'))
        self.assertIsNone(csb.duyuru_turu('X'))

    def test_il_merkezi_belediye(self):
        p=csb.baslik_coz('Zonguldak Belediyesi zabıta memur alımı iptal ilanı')
        self.assertEqual((p['il'],p['kurum']),('Zonguldak','ZONGULDAK BELEDİYESİ'))
        self.assertEqual(csb.duyuru_turu('ZONGULDAK BELEDİYESİ ZABITA MEMUR ALIMI İPTAL İLANI'),'İptal duyurusu')

    def test_yazim_hatali_il_bos_kalir(self):
        p=csb.baslik_coz('NİĞDE İLİ ÇUIKURKUYU BELEDİYESİ İLK DEFA  MEMUR (Zabıta) ALIM İPTAL İLANI')
        self.assertEqual((p['il'],p['kurum']),('Niğde','ÇUIKURKUYU BELEDİYESİ'))
        p=csb.baslik_coz('NİGDE İLİ ÇUIKURKUYU BELEDİYESİ MEMUR ALIM İLANI')
        self.assertIsNone(p['il'])
        self.assertEqual(p['kurum'],'ÇUIKURKUYU BELEDİYESİ')

    def test_illi_yazim_hatasi_ve_genel_mudurluk(self):
        p=csb.baslik_coz('ANKARA İLLİ PURSAKLAR BELEDİYE BAŞKANLIĞI İLK DEFA ATANMAK ÜZERE ZABITA MEMURU ALIMI İLANI')
        self.assertEqual((p['il'],p['kurum']),('Ankara','PURSAKLAR BELEDİYE BAŞKANLIĞI'))
        p=csb.baslik_coz('İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜNE İLK DEFA ATANMAK ÜZERE MEMUR ALIM İLANI')
        self.assertEqual((p['il'],p['kurum']),(None,'İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜ'))

    def test_tanimsiz_baslik_tahmin_edilmez(self):
        p=csb.baslik_coz('GENEL DUYURU')
        self.assertEqual((p['il'],p['kurum']),(None,''))

    def test_duzeltme_turu(self):
        self.assertEqual(csb.duyuru_turu('YALOVA İLİ SUBAŞI BELEDİYE BAŞKANLIĞINA MEMUR ALIMI DÜZELTME İLANI'),'Düzeltme / süre değişikliği')


class BelgeTesti(unittest.TestCase):
    def test_docx_metni(self):
        metin=csb.docx_metni(oku('csb_alim.docx'))
        self.assertIn('ZABITA',metin.upper())
        self.assertIn('BAŞVURU YERİ, TARİHİ, ŞEKLİ VE SÜRESİ',metin)

    def test_bozuk_docx_hata_verir(self):
        with self.assertRaises(Exception):
            csb.docx_metni(b'PK bozuk')

    def test_son_basvuru_aralikdan(self):
        self.assertEqual(csb.son_basvuru(csb.docx_metni(oku('csb_alim.docx'))),'2026-11-06')
        self.assertEqual(csb.son_basvuru(csb.docx_metni(oku('csb_duzeltme.docx'))),'2026-10-02')

    def test_son_basvuru_acik_ifade(self):
        self.assertEqual(csb.son_basvuru('Son başvuru tarihi: 15/10/2026 saat 17.00'),'2026-10-15')
        self.assertEqual(csb.son_basvuru('Son başvuru günü 5 Kasım 2026\'dır.'),'2026-11-05')

    def test_aralik_tarihinden_tarihine_kadar(self):
        metin=('Adaylar, sözlü ve uygulamalı sınava katılabilmek için;\n19/10/2026 tarihinden 21/10/2026 tarihi mesai bitimine kadar, '
               'yukarıda sayılan belgeler ile birlikte Aralık/Iğdır adresindeki birime şahsen müracaat ederek başvuru sürecini tamamlayacaklardır.\n')
        self.assertEqual(csb.son_basvuru(metin),'2026-10-21')
        self.assertEqual(csb.son_basvuru(metin.replace('tarihi mesai bitimine','tarihine')),'2026-10-21')
        self.assertIsNone(csb.son_basvuru('Sınav 19/10/2026 tarihinden 21/10/2026 tarihine kadar yapılır. Başvuru yapılır.'))
        self.assertIsNone(csb.son_basvuru('Başvurular 19/10/2026 tarihinden 21/10/2026 tarihine kadar, sınav için yapılır.'))
        self.assertIsNone(csb.son_basvuru(metin+'Başvurular 01/11/2026 tarihinden 05/11/2026 tarihine kadar alınır.'))

    def test_gercek_aralik_igdir_docx(self):
        # canlı belgeden alınan cümle (09 Eylül 2026 duyurusu)
        metin=('BAŞVURU YERİ, TARİHİ, ŞEKLİ VE SÜRESİ:\nAdaylar, sözlü ve uygulamalı sınava katılabilmek için;\n'
               '19/10/2026 tarihinden 21/10/2026 tarihi mesai bitimine kadar, yukarıda sayılan belgeler ile birlikte, boy ve kilo ölçümünü yapmak üzere '
               'Karşıyaka Mahallesi Atatürk Caddesi No:2 Aralık/Iğdır adresindeki Aralık Belediye Başkanlığı Yazı İşleri Müdürlüğü birimine şahsen müracaat '
               'ederek başvuru sürecini tamamlayacaklardır.\nBaşvurular şahsen yapılacaktır.\n')
        self.assertEqual(csb.son_basvuru(metin),'2026-10-21')

    def test_tarih_yoksa_bos(self):
        self.assertIsNone(csb.son_basvuru('Başvurular belediyeye yapılır. Sınav 15/10/2026 tarihinde yapılacaktır.'))
        self.assertIsNone(csb.son_basvuru('Son başvuru tarihi itibarıyla 35 yaşını doldurmamış olmak. Sınav 12/11/2026 - 14/11/2026 tarihleri arasında yapılır.'))
        self.assertIsNone(csb.son_basvuru(''))

    def test_celisen_tarihler_bos(self):
        self.assertIsNone(csb.son_basvuru('Son başvuru: 01/10/2026. Son başvuru: 09/10/2026.'))


class DetayTesti(unittest.TestCase):
    def test_iptal_eksiz(self):
        d=csb.detay_ayristir(oku('csb_detay_iptal.html'))
        self.assertEqual(d['ekler'],[])
        self.assertIn('TEKNİKER',csb.buyuk(d['baslik']))
        self.assertIn('iptal edilmiştir',d['aciklama'])

    def test_alim_eki_alinir_meclis_rehberi_alinmaz(self):
        d=csb.detay_ayristir(oku('csb_detay_alim.html'))
        self.assertEqual(len(d['ekler']),1)
        self.assertTrue(d['ekler'][0].startswith('https://webdosya.csb.gov.tr/v2/yerelyonetimler/2026/09/'))
        self.assertTrue(d['ekler'][0].endswith('.docx'))
        for ad in ('csb_detay_alim.html','csb_detay_duzeltme.html','csb_detay_iptal.html'):
            self.assertIn('belediye-meclisi',oku(ad).decode('utf-8'))  # sabit bağlantı sayfada gerçekten var
            self.assertFalse(any('meclisi' in e for e in csb.detay_ayristir(oku(ad))['ekler']))

    def test_pdf_eki_tanınır(self):
        html='<a href="https://webdosya.csb.gov.tr/v2/yerelyonetimler/2026/10/ilan.pdf">x</a><a href="https://evil.test/v2/yerelyonetimler/2026/10/a.pdf">y</a>'
        self.assertEqual(csb.detay_ayristir(html)['ekler'],['https://webdosya.csb.gov.tr/v2/yerelyonetimler/2026/10/ilan.pdf'])


class KayitTesti(unittest.TestCase):
    def gercek_kayit(self,numara,html_adi,docx=None,baslik=''):
        s=csb.liste_ayristir(oku('csb_liste.html'))
        s=next(x for x in s if x['numara']==numara)
        def sahte(adres,sinir=0):
            return oku(html_adi) if adres==s['link'] else oku(docx)
        with patch.object(csb,'indir',side_effect=sahte):
            return csb.duyuru_oku(s)

    def test_alim_kaydi(self):
        k=self.gercek_kayit('477952','csb_detay_alim.html','csb_alim.docx')
        self.assertEqual(k['id'],'csb-477952')
        self.assertEqual((k['kaynak_turu'],k['kaynak']),('csb','ÇŞB Yerel Yönetimler'))
        self.assertEqual((k['kurum'],k['yer']),('ŞİLE BELEDİYE BAŞKANLIĞI','İstanbul'))
        self.assertEqual(k['son_tarih'],'2026-11-06')
        self.assertNotIn('duyuru_turu',k)
        self.assertEqual(k['link'],SITE+'istanbul-ili-sile-belediye-baskanligina-ilk-defa-atanmak-uzere-zabita-memuru-alimi-ilani-duyuru-477952')
        self.assertEqual(k['kaynaklar'][0]['link'],k['link'])
        self.assertEqual(len(k['belgeler']),1)
        self.assertIn('Son başvuru: 06.11.2026.',k['ozet'])
        self.assertTrue(k['baslik'].startswith('ŞİLE BELEDİYE BAŞKANLIĞI - '))
        json.dumps(k,ensure_ascii=False)

    def test_iptal_kaydi(self):
        k=self.gercek_kayit('478009','csb_detay_iptal.html')
        self.assertEqual(k['duyuru_turu'],'İptal duyurusu')
        self.assertIsNone(k['son_tarih'])
        self.assertEqual(k['yer'],'Rize')
        self.assertEqual(k['belgeler'],[])
        self.assertIn('iptal edilmiştir',k['ozet'])

    def test_duzeltme_kaydi(self):
        k=self.gercek_kayit('477790','csb_detay_duzeltme.html','csb_duzeltme.docx')
        self.assertEqual(k['duyuru_turu'],'Düzeltme / süre değişikliği')
        self.assertEqual((k['son_tarih'],k['yer']),('2026-10-02','Yalova'))

    def test_ayni_duyuru_ayni_kimlik(self):
        a=self.gercek_kayit('478009','csb_detay_iptal.html')
        b=self.gercek_kayit('478009','csb_detay_iptal.html')
        self.assertEqual(a['id'],b['id'])


class TaramaTesti(unittest.TestCase):
    def sahte_ag(self,adres,sinir=0):
        liste=oku('csb_liste.html')
        if adres.startswith(csb.LISTE):
            return liste
        if adres.endswith('.docx'):
            return oku('csb_alim.docx')
        return oku('csb_detay_alim.html')

    def test_tarama_sbb_uyumlu_kayit_uretir(self):
        with patch.object(csb,'indir',side_effect=self.sahte_ag),patch.object(csb.time,'sleep'):
            kayitlar,hata=csb.csb_oku({})
        self.assertEqual(hata,0)
        self.assertEqual(len(kayitlar),12)
        self.assertEqual(len({k['id'] for k in kayitlar}),12)
        for k in kayitlar:
            for alan in ('id','baslik','kurum','link','kaynak','kaynak_turu','kaynaklar','detay_guncelleme','ilan_turu'):
                self.assertIn(alan,k)
            self.assertRegex(k['id'],r'^csb-\d+$')

    def test_onbellekteki_duyuru_yeniden_indirilmez(self):
        with patch.object(csb,'indir',side_effect=self.sahte_ag),patch.object(csb.time,'sleep'):
            ilk,_=csb.csb_oku({})
        cagri=[]
        def sadece_liste(adres,sinir=0):
            cagri.append(adres)
            return self.sahte_ag(adres,sinir)
        with patch.object(csb,'indir',side_effect=sadece_liste),patch.object(csb.time,'sleep'):
            ikinci,_=csb.csb_oku({k['id']:k for k in ilk})
        self.assertEqual(len(ikinci),12)
        self.assertTrue(all(c.startswith(csb.LISTE) for c in cagri))

    def _eski_kayit_listesi(self,saat):
        with patch.object(csb,'indir',side_effect=self.sahte_ag),patch.object(csb.time,'sleep'):
            kayitlar,_=csb.csb_oku({})
        eski=csb.now()-timedelta(hours=saat)
        for k in kayitlar:
            k['detay_guncelleme']=eski.isoformat(timespec='seconds')
            k['ozet']='ESKI'
        return kayitlar

    def test_12_saatten_eski_ayrinti_yeniden_okunur(self):
        eski=self._eski_kayit_listesi(13)
        with patch.object(csb,'indir',side_effect=self.sahte_ag),patch.object(csb.time,'sleep'):
            yeni,hata=csb.csb_oku({k['id']:k for k in eski})
        self.assertEqual(hata,0)
        self.assertEqual(len(yeni),12)
        self.assertTrue(all(k['ozet']!='ESKI' for k in yeni))
        self.assertTrue(all(csb.fresh(k) for k in yeni))

    def test_11_saatlik_ayrinti_yeniden_okunmaz(self):
        eski=self._eski_kayit_listesi(11)
        cagri=[]
        def kaydet(adres,sinir=0):
            cagri.append(adres)
            return self.sahte_ag(adres,sinir)
        with patch.object(csb,'indir',side_effect=kaydet),patch.object(csb.time,'sleep'):
            yeni,_=csb.csb_oku({k['id']:k for k in eski})
        self.assertTrue(all(c.startswith(csb.LISTE) for c in cagri))
        self.assertTrue(all(k['ozet']=='ESKI' for k in yeni))

    def test_okuma_hatasinda_eski_kayit_ve_tarihi_korunur(self):
        eski=self._eski_kayit_listesi(13)
        damga={k['id']:k['detay_guncelleme'] for k in eski}
        def hep_hata(adres,sinir=0):
            if adres.startswith(csb.LISTE):
                return oku('csb_liste.html')
            raise OSError('zaman asimi')
        with patch.object(csb,'indir',side_effect=hep_hata),patch.object(csb.time,'sleep'):
            yeni,hata=csb.csb_oku({k['id']:k for k in eski})
        self.assertEqual(hata,12)
        self.assertEqual(len(yeni),12)
        self.assertTrue(all(k['ozet']=='ESKI' and k['detay_guncelleme']==damga[k['id']] for k in yeni))

    def test_butce_en_eskiden_baslar(self):
        eski=self._eski_kayit_listesi(13)
        for n,k in enumerate(eski):
            k['detay_guncelleme']=(csb.now()-timedelta(hours=13+n)).isoformat(timespec='seconds')
        with patch.object(csb,'AZAMI_DETAY',2),patch.object(csb,'indir',side_effect=self.sahte_ag),patch.object(csb.time,'sleep'):
            yeni,_=csb.csb_oku({k['id']:k for k in eski})
        guncel={k['id'] for k in yeni if k['ozet']!='ESKI'}
        self.assertEqual(guncel,{eski[-1]['id'],eski[-2]['id']})

    def test_ag_hatasinda_cokmez_ve_istisna_bildirir(self):
        with patch.object(csb,'indir',side_effect=OSError('ag yok')):
            with self.assertRaises(RuntimeError):
                csb.csb_oku({})

    def test_ayrinti_hatasi_sayilir_digerleri_devam(self):
        def kismen(adres,sinir=0):
            if adres.endswith('-duyuru-478009'):
                raise OSError('zaman asimi')
            return self.sahte_ag(adres,sinir)
        with patch.object(csb,'indir',side_effect=kismen),patch.object(csb.time,'sleep'):
            kayitlar,hata=csb.csb_oku({})
        self.assertEqual(hata,1)
        self.assertEqual(len(kayitlar),11)

    def test_ek_belge_hatasinda_kayit_tarihsiz_uretilir(self):
        def kotu_ek(adres,sinir=0):
            if adres.endswith('.docx'):
                return b'bozuk'
            return self.sahte_ag(adres,sinir)
        with patch.object(csb,'indir',side_effect=kotu_ek),patch.object(csb.time,'sleep'):
            kayitlar,hata=csb.csb_oku({})
        self.assertEqual(hata,0)
        self.assertTrue(all(k['son_tarih'] is None for k in kayitlar))

    def test_boyut_siniri(self):
        class Yanit:
            def __init__(s,n): s.n=n
            def read(s,n): return b'x'*min(n,s.n)
            def __enter__(s): return s
            def __exit__(s,*a): return False
        class Acici:
            def open(s,istek,timeout=0): return Yanit(csb.SAYFA_SINIRI+50)
        with patch.object(csb.urllib.request,'build_opener',return_value=Acici()):
            with self.assertRaises(ValueError):
                csb.indir(csb.LISTE)


class AkisTesti(unittest.TestCase):
    def kayit(self):
        s=next(x for x in csb.liste_ayristir(oku('csb_liste.html')) if x['numara']=='477952')
        with patch.object(csb,'indir',side_effect=lambda a,n=0:oku('csb_detay_alim.html') if a==s['link'] else oku('csb_alim.docx')):
            return csb.duyuru_oku(s)

    def test_yerel_kaynaklar_akisi(self):
        simdi=datetime.now(timezone.utc)
        k=self.kayit()
        veri={'schema':1,'kaynaklar':{'csb':{'kontrol':simdi.isoformat(),'hata_sayisi':0,'ilanlar':[k]}}}
        self.assertEqual(csb_verisi(veri)[0],[k])
        self.assertIsNone(sbb_verisi(veri))
        veri['kaynaklar']['csb']['kontrol']=(simdi-timedelta(hours=3)).isoformat()
        self.assertIsNone(csb_verisi(veri))
        veri['kaynaklar']['csb']['kontrol']=simdi.isoformat()
        veri['kaynaklar']['csb']['ilanlar']=[{'id':'csb-1','baslik':'x','link':'http://yerelyonetimler.csb.gov.tr/x'}]
        self.assertIsNone(csb_verisi(veri))

    def test_yerel_tara_toplama_csb_ekler_ve_cokmez(self):
        import yerel_tara
        k=self.kayit()
        with patch.object(yerel_tara,'read_sbb',side_effect=OSError('sbb yok')),patch.object(yerel_tara,'csb_oku',return_value=([k],0)):
            sonuc=yerel_tara.collect({'ilanlar':[]},{})
        self.assertEqual(sonuc['kaynaklar']['csb']['ilanlar'],[k])
        self.assertNotIn('sbb',sonuc['kaynaklar'])
        with patch.object(yerel_tara,'read_sbb',side_effect=OSError('sbb yok')),patch.object(yerel_tara,'csb_oku',side_effect=RuntimeError('ag yok')):
            sonuc=yerel_tara.collect({'ilanlar':[]},{'kaynaklar':{'csb':{'ilanlar':[k]}}})
        self.assertEqual(sonuc['kaynaklar']['csb']['ilanlar'],[k])  # eski veri bozulmaz

    def test_site_sayfasi_ve_telegram_baglantisi(self):
        k=self.kayit()
        anahtar,sayfa=detail_page(k)
        self.assertEqual(anahtar,'csb-477952')
        self.assertIn(k['link'],sayfa)
        self.assertIn('webdosya.csb.gov.tr/v2/yerelyonetimler/2026/09/',sayfa)
        self.assertEqual(ilan_sayfasi(k,'https://enesfeched-maker.github.io/kamu-ilan-takip/'),
                         'https://enesfeched-maker.github.io/kamu-ilan-takip/ilan/csb-477952/')
        for kotu in ('csb-','csb-abc','csb-1234567890123'):
            with self.assertRaises(ValueError):
                ilan_sayfasi({'id':kotu,'link':''},'https://enesfeched-maker.github.io/kamu-ilan-takip/')

    def test_telegram_mesaji_duyuru_turu_ve_kaynak(self):
        s=next(x for x in csb.liste_ayristir(oku('csb_liste.html')) if x['numara']=='478009')
        with patch.object(csb,'indir',return_value=oku('csb_detay_iptal.html')):
            k=csb.duyuru_oku(s)
        metin=ilan_bot.mesaj_olustur(k,'https://enesfeched-maker.github.io/kamu-ilan-takip/')
        self.assertIn('📌 <b>İptal duyurusu</b>',metin)
        self.assertIn('Kaynak: ÇŞB Yerel Yönetimler',metin)
        self.assertIn('Resmi ilan üzerinden kontrol edin',metin)
        self.assertIsNone(ilan_bot.hatirlatma_anahtari(k))
        ilan_bot.siniflandir(k)
        self.assertEqual(k['iller'],['Rize'])

    def test_gorsel_olusur(self):
        from ilan_gorsel import gorsel_olustur
        self.assertTrue(gorsel_olustur('RİZE BELEDİYESİ','İptal','Rize','Resmi ilandan kontrol edin',kaynak='ÇŞB Yerel Yönetimler'))


def kayit(kimlik,kurum,tur='csb',**ek):
    k={'id':kimlik,'baslik':kurum+' - ilan','kurum':kurum,'son_tarih':None,'kaynak_turu':tur,'ilk_gorulme':'2026-09-30T10:00:00+03:00'}
    if tur=='csb':
        k['link']=SITE+'x-duyuru-'+kimlik.split('-')[1]
    elif tur=='sbb':
        k['link']='https://kamuilan.sbb.gov.tr/'
    else:
        k['link']='https://www.iskur.gov.tr/medya/'+kimlik+'.pdf'
    k.update(ek)
    return k


class CekirdekTesti(unittest.TestCase):
    def test_ad_varyantlari_ayni_cekirdek(self):
        for kurum,yer in [('ŞİLE BELEDİYE BAŞKANLIĞI','İstanbul'),('İstanbul Şile Belediyesi',None),('Şile Belediyesi',None),('ŞİLE BELEDİYE BAŞKANLIĞI',None)]:
            self.assertEqual(csb.cekirdek(kurum,yer)[0],'sile')
        self.assertEqual(csb.cekirdek('İstanbul Şile Belediyesi')[1],'istanbul')
        self.assertEqual(csb.cekirdek('SUBAŞI (YALOVA) BELEDİYE BAŞKANLIĞI'),('subasi','yalova'))

    def test_buyuksehir_ayrimi_ve_belediye_olmayanlar(self):
        self.assertEqual(csb.cekirdek('İstanbul Büyükşehir Belediyesi')[0],'istanbul buyuksehir')
        self.assertNotEqual(csb.cekirdek('İstanbul Büyükşehir Belediyesi')[0],csb.cekirdek('İstanbul Şile Belediyesi')[0])
        self.assertEqual(csb.cekirdek('Bolu Belediyesi')[0],'bolu')
        self.assertIsNone(csb.cekirdek('İSTANBUL ELEKTRİK TRAMVAY VE TÜNEL İŞLETMELERİ GENEL MÜDÜRLÜĞÜ'))


class EslesmeTesti(unittest.TestCase):
    def test_alim_tek_aday_eslesir(self):
        c=kayit('csb-1','ŞİLE BELEDİYE BAŞKANLIĞI',yer='İstanbul',son_tarih='2026-11-06')
        s=kayit('sbb-'+'a'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,s]),{frozenset((c['id'],s['id']))})

    def test_tarih_farkli_ya_da_bos_eslesmez(self):
        c=kayit('csb-1','Şile Belediyesi',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,kayit('sbb-'+'a'*24,'Şile Belediyesi','sbb',son_tarih='2026-11-13')]),set())
        self.assertEqual(csb.eslesme_ciftleri([{**c,'son_tarih':None},kayit('sbb-'+'a'*24,'Şile Belediyesi','sbb')]),set())

    def test_ayni_kaynakta_iki_aday_ya_da_iki_csb_belirsiz(self):
        c=kayit('csb-1','Şile Belediyesi',son_tarih='2026-11-06')
        s1=kayit('sbb-'+'a'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06')
        s2=kayit('sbb-'+'b'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,s1,s2]),set())
        c2=kayit('csb-2','Şile Belediyesi',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,c2,s1]),set())

    def test_sbb_ve_iskur_birlikte_sbbye_eslesir(self):
        c=kayit('csb-1','Çeltik Belediyesi',yer='Konya',son_tarih='2026-11-06')
        s=kayit('sbb-'+'a'*24,'ÇELTİK BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06')
        i=kayit('iskur-'+'b'*24,'Konya Çeltik Belediyesi','iskur',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,s,i]),{frozenset((c['id'],s['id']))})

    def test_farkli_il_ve_buyuksehir_eslesmez(self):
        c=kayit('csb-1','Merkez Belediyesi',yer='Bolu',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,kayit('iskur-'+'b'*24,'Bingöl Merkez Belediyesi','iskur',son_tarih='2026-11-06')]),set())
        c=kayit('csb-1','İstanbul Büyükşehir Belediyesi',son_tarih='2026-11-06')
        self.assertEqual(csb.eslesme_ciftleri([c,kayit('sbb-'+'a'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06')]),set())

    def test_isci_sigortasi(self):
        c=kayit('csb-1','Şile Belediyesi',son_tarih='2026-11-06')
        s=kayit('sbb-'+'a'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06',kadro='5 İŞÇİ ALACAK')
        self.assertEqual(csb.eslesme_ciftleri([c,s]),set())
        c2={**c,'ozet':'Sürekli işçi alımı yapılacaktır.'}
        self.assertEqual(csb.eslesme_ciftleri([c2,s]),{frozenset((c['id'],s['id']))})
        self.assertEqual(csb.eslesme_ciftleri([c2,{**s,'kadro':'1 MÜHENDİS'}]),set())

    def test_belediye_olmayan_kurum_eslesmez(self):
        ad='İstanbul Elektrik Tramvay ve Tünel İşletmeleri Genel Müdürlüğü'
        self.assertEqual(csb.eslesme_ciftleri([kayit('csb-1',ad,son_tarih='2026-11-06'),kayit('iskur-'+'b'*24,ad,'iskur',son_tarih='2026-11-06')]),set())

    def test_iptal_tek_aday_ve_tarih_toleransi(self):
        c=kayit('csb-1','RİZE BELEDİYESİ',duyuru_turu='İptal duyurusu',yayim_tarihi='2026-10-01')
        s=kayit('sbb-'+'a'*24,'RİZE BELEDİYE BAŞKANLIĞI','sbb',duyuru_turu='İptal duyurusu',ilk_gorulme='2026-09-30T20:00:00+03:00')
        self.assertEqual(csb.eslesme_ciftleri([c,s]),{frozenset((c['id'],s['id']))})
        bes_gun={**s,'ilk_gorulme':'2026-09-26T20:00:00+03:00'}
        self.assertEqual(csb.eslesme_ciftleri([c,bes_gun]),{frozenset((c['id'],s['id']))})
        uzak={**s,'ilk_gorulme':'2026-09-20T20:00:00+03:00'}
        self.assertEqual(csb.eslesme_ciftleri([c,uzak]),set())
        duzeltme={**s,'duyuru_turu':'Düzeltme / süre değişikliği'}
        self.assertEqual(csb.eslesme_ciftleri([c,duzeltme]),set())

    def test_ayni_gun_birden_cok_iptal_birlesmez(self):
        c1=kayit('csb-1','RİZE BELEDİYESİ',duyuru_turu='İptal duyurusu',yayim_tarihi='2026-10-01')
        c2=kayit('csb-2','RİZE BELEDİYESİ',duyuru_turu='İptal duyurusu',yayim_tarihi='2026-10-01')
        s=kayit('sbb-'+'a'*24,'RİZE BELEDİYE BAŞKANLIĞI','sbb',duyuru_turu='İptal duyurusu')
        self.assertEqual(csb.eslesme_ciftleri([c1,c2,s]),set())
        s2=kayit('sbb-'+'b'*24,'RİZE BELEDİYE BAŞKANLIĞI','sbb',duyuru_turu='İptal duyurusu')
        self.assertEqual(csb.eslesme_ciftleri([c1,s,s2]),set())


class BirlesmeTesti(unittest.TestCase):
    def setUp(self):
        self.sbb=kayit('sbb-'+'a'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06',kaynak='SBB Kamu İlan',
                       kaynaklar=[{'ad':'SBB Kamu İlan','link':'https://kamuilan.sbb.gov.tr/'}],kaynak_kimlikleri=['sbb-'+'a'*24])
        self.csb=kayit('csb-477952','ŞİLE BELEDİYE BAŞKANLIĞI',yer='İstanbul',son_tarih='2026-11-06',kaynak='ÇŞB Yerel Yönetimler',
                       kaynaklar=[{'ad':'ÇŞB Yerel Yönetimler','link':SITE+'x-duyuru-477952'}])

    def test_birlesmede_eski_kimlik_korunur_ve_kaynaklar_eklenir(self):
        sonuc=ek.merge_sources([self.csb],{self.sbb['id']:self.sbb})
        self.assertEqual([i['id'] for i in sonuc],[self.sbb['id']])
        self.assertEqual({s['link'] for s in sonuc[0]['kaynaklar']},{'https://kamuilan.sbb.gov.tr/',SITE+'x-duyuru-477952'})
        self.assertIn('csb-477952',sonuc[0]['kaynak_kimlikleri'])
        self.assertIn(self.sbb['id'],sonuc[0]['kaynak_kimlikleri'])

    def test_ayni_tarama_icinde_de_birlesir(self):
        sonuc=ek.merge_sources([self.sbb,self.csb],{})
        self.assertEqual(len(sonuc),1)
        self.assertIn('csb-477952',sonuc[0]['kaynak_kimlikleri'])

    def test_birlesen_kimlik_sonraki_taramada_kalici(self):
        once=ek.merge_sources([self.csb],{self.sbb['id']:self.sbb})[0]
        degisen={**self.csb,'son_tarih':'2026-11-20'}
        sonuc=ek.merge_sources([degisen],{once['id']:once})
        self.assertEqual([i['id'] for i in sonuc],[self.sbb['id']])

    def test_sbbden_gonderilmis_ilan_csbden_gelince_tekrar_gonderilmez(self):
        onceki={self.sbb['id']:self.sbb}
        gonderilen={self.sbb['id']}
        mevcut={**onceki}
        yeni=dict(self.csb,ilk_gorulme='2026-10-01T10:00:00+03:00')
        mevcut[yeni['id']]=yeni
        gelen=ek.merge_sources([mevcut[yeni['id']]],onceki)
        yeniler=[i for i in gelen if i['id']==yeni['id']]
        self.assertEqual(yeniler,[])
        aliases={a:i['id'] for i in gelen for a in i.get('kaynak_kimlikleri',[])}
        for eski in list(mevcut):
            if eski in aliases and aliases[eski]!=eski:
                del mevcut[eski]
        mevcut.update({i['id']:i for i in gelen})
        bekleyen=set()
        sira=ilan_bot.telegram_sirasi(mevcut,gelen,yeniler,gonderilen,bekleyen,False,False,{})
        self.assertEqual(sira,[])
        self.assertEqual(bekleyen,set())
        self.assertEqual(gonderilen,{self.sbb['id']})

    def test_eslesmeyen_csb_kendi_kimligiyle_kalir(self):
        iki=kayit('sbb-'+'b'*24,'ŞİLE BELEDİYE BAŞKANLIĞI','sbb',son_tarih='2026-11-06')
        sonuc=ek.merge_sources([self.csb],{self.sbb['id']:self.sbb,iki['id']:iki})
        self.assertIn('csb-477952',[i['id'] for i in sonuc])


class TekrarOnlemeTesti(unittest.TestCase):
    def test_same_listing_csb_icin_kapali(self):
        a={'id':'csb-1','baslik':'ÖRNEK BELEDİYESİ - MEMUR ALIM İLANI','kurum':'ÖRNEK BELEDİYESİ','son_tarih':'2026-10-09','kaynak_turu':'csb','link':SITE+'x-duyuru-1'}
        b={'id':'iskur-'+24*'a','baslik':'Örnek Belediyesi memur alımı','kurum':'Örnek Belediyesi','son_tarih':'2026-10-09','kaynak_turu':'iskur','link':'https://www.iskur.gov.tr/medya/x.pdf','kadro':''}
        self.assertFalse(ek.same_listing(a,b))

    def test_ayni_csb_kimligi_korunur(self):
        a={'id':'csb-1','baslik':'A','kurum':'K','kaynak_turu':'csb','link':SITE+'x-duyuru-1'}
        birlesik=ek.merge_sources([{**a,'son_tarih':'2026-10-09'}],{'csb-1':a})
        self.assertEqual([i['id'] for i in birlesik],['csb-1'])
        self.assertEqual(birlesik[0]['son_tarih'],'2026-10-09')


if __name__=='__main__':unittest.main()
