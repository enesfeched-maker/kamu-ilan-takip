"""Kanal kuralları: akademik ilanlar hiçbir yerde yok; iptal/düzeltme orijinal ilana yanıt; message_id kayıtları."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import ilan_bot
import iptal_yaniti
import site_uret
import sosyal_paylasim
from siniflandir import akademik_ilan
from veri_kaydet import merge_registry

TR = timezone(timedelta(hours=3))
SIMDI = datetime(2026, 10, 5, 8, 0, tzinfo=TR)  # 09:00 öncesi: toplu kart karışmaz
BASE = 'https://enesfeched-maker.github.io/kamu-ilan-takip/'
ROOT = Path(__file__).resolve().parents[1]


def gun(n):
    return (SIMDI + timedelta(days=n)).isoformat()


def ilan(kimlik, kurum='RİZE BELEDİYESİ', kadro='1 TEKNİKER ALACAK', **ek):
    r = {'id': kimlik, 'baslik': f'{kurum} - ilan', 'kurum': kurum, 'kadro': kadro,
         'link': f'https://kariyerkapisi.gov.tr/IlanDetay?i={kimlik}', 'son_tarih': gun(20)[:10],
         'ilk_gorulme': gun(-3), 'kaynak_turu': 'csb'}
    r.update(ek)
    return r


def duyuru(kimlik='csb-1', tur='İptal duyurusu', **ek):
    r = ilan(kimlik, kadro='')
    r.update(baslik='RİZE BELEDİYESİ İLK DEFA SÖZLEŞMELİ PERSONEL ( TEKNİKER ) ALIM İPTAL İLANI', duyuru_turu=tur,
             kaynak='ÇŞB Yerel Yönetimler', son_tarih=None, ilk_gorulme=gun(0),
             ozet='Rize Belediyesinin yazısına istinaden tekniker alım ilanı iptal edilmiştir')
    r.update(ek)
    return r


class Dugum(unittest.TestCase):
    """ilan_bot.main'i geçici veri dosyasıyla çalıştırır; gönderimleri yakalar."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        kok = Path(self.temp.name)
        self.cfg = kok / 'config.json'
        self.cfg.write_text(json.dumps({'rss_urls': ['https://example.com/rss'], 'max_mesaj_per_calisma': 15}), encoding='utf-8')
        self.data = kok / 'ilanlar.json'

    def yaz(self, ilanlar, gonderilen=(), mesajlar=None, **ek):
        self.data.write_text(json.dumps({'guncelleme': SIMDI.isoformat(), 'ilanlar': ilanlar,
            'telegram_gonderilen': list(gonderilen), 'telegram_mesajlari': mesajlar or {}, **ek}), encoding='utf-8')

    def durum(self):
        return json.loads(self.data.read_text(encoding='utf-8'))

    def calistir(self, *args, donus=(), basarili=True):
        self.cagrilar = []
        sayac = iter(donus)
        def gonder(*a, **k):
            self.cagrilar.append((a, k))
            return next(sayac, 1000 + len(self.cagrilar)) if basarili else False
        simdi_ilanlar = [dict(i) for i in self.durum()['ilanlar']]
        with patch.object(ilan_bot, 'simdi', return_value=SIMDI), \
             patch.object(ilan_bot, 'CONFIG_YOLU', self.cfg), \
             patch.object(ilan_bot, 'indir', return_value=b''), \
             patch.object(ilan_bot, 'rss_coz', return_value=simdi_ilanlar), \
             patch.object(ilan_bot, 'telegram_gonder', side_effect=gonder), \
             patch.object(ilan_bot, 'kurum_logosu', return_value=None), \
             patch.object(ilan_bot, 'ilan_sayfasi', side_effect=lambda i, s: BASE + 'ilan/' + i['id'] + '/'), \
             patch.object(ilan_bot, 'yerel_oku', return_value={}), \
             patch.object(ilan_bot.time, 'sleep'), \
             patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 't', 'TELEGRAM_CHAT_ID': '@t', 'RSS_URLS': ''}), \
             patch('sys.argv', ['bot', '--cikti', str(self.data), *args]), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ilan_bot.main()
        return len(self.cagrilar)

    def kayit(self, kimlik):
        return next(i for i in self.durum()['ilanlar'] if i['id'] == kimlik)


class AkademikTesti(Dugum):
    AKADEMIK = dict(baslik='ÖRNEK ÜNİVERSİTESİ - Öğretim Görevlisi alımı', kurum='ÖRNEK ÜNİVERSİTESİ', kadro='2 Öğretim Görevlisi')

    def test_tanima_memur_tekniker_etkilenmez(self):
        self.assertTrue(akademik_ilan(ilan('a', **self.AKADEMIK)))
        self.assertTrue(akademik_ilan({'id': 'b', 'baslik': 'x', 'kategori': 'akademik'}))
        self.assertFalse(akademik_ilan(ilan('c', 'ÖRNEK ÜNİVERSİTESİ', '3 Tekniker, 2 Memur', baslik='ÖRNEK ÜNİVERSİTESİ KPSS ile personel alımı')))

    def test_telegram_gonderilmez(self):
        self.assertFalse(ilan_bot.telegram_icin_uygun(ilan('a', **self.AKADEMIK), [], []))
        self.yaz([ilan('a', **self.AKADEMIK, kaynak_turu=None), ilan('b', 'DİĞER BELEDİYESİ', '1 ZABITA', kaynak_turu=None)])
        self.assertEqual(self.calistir('--duyur-mevcut'), 1)
        self.assertIn('Diğer Belediyesi', self.cagrilar[0][0][2])
        self.assertEqual(self.kayit('a')['id'], 'a')  # veri ilanlar.json'da kalır

    def test_sosyal_paylasim_secimi(self):
        dun = (SIMDI - timedelta(days=1)).isoformat()
        secilen = sosyal_paylasim.sec([ilan('a', ilk_gorulme=dun, **self.AKADEMIK, kaynak_turu=None),
                                       ilan('b', ilk_gorulme=dun, kaynak_turu=None),
                                       ilan('c', ilk_gorulme=dun, iptal_edildi='csb-9', kaynak_turu=None)], SIMDI)
        self.assertEqual([i['id'] for i in secilen], ['b'])

    def test_site_sayfasi_bot_verisi_ve_eski_sayfa_silinir(self):
        a = ilan('sbb-' + 'a' * 24, link='https://kamuilan.sbb.gov.tr/', kaynak_turu='sbb', **self.AKADEMIK)
        b = ilan('sbb-' + 'b' * 24, link='https://kamuilan.sbb.gov.tr/', kaynak_turu='sbb', kadro='1 ZABITA', baslik='X - Zabıta')
        self.assertIsNone(site_uret.detail_page(a))
        self.assertIsNotNone(site_uret.detail_page(b))
        self.assertEqual([i['id'] for i in site_uret.bot_ilanlari([a, b], SIMDI)['ilanlar']], [b['id']])
        with tempfile.TemporaryDirectory() as kok:
            docs = Path(kok) / 'docs'
            (docs / 'ilan' / a['id']).mkdir(parents=True)
            (docs / 'ilan' / a['id'] / 'index.html').write_text('eski')
            (docs / 'ilanlar.json').write_text(json.dumps({'ilanlar': [a, b]}), encoding='utf-8')
            with patch.object(site_uret, 'ROOT', Path(kok)), contextlib.redirect_stdout(io.StringIO()):
                site_uret.main()
            self.assertFalse((docs / 'ilan' / a['id']).exists())
            self.assertTrue((docs / 'ilan' / b['id'] / 'index.html').exists())
            self.assertNotIn(a['id'], (docs / 'sitemap.xml').read_text())
            self.assertIn(b['id'], (docs / 'sitemap.xml').read_text())
            self.assertNotIn(a['id'], (docs / 'bot-ilanlar.json').read_text())

    def test_portal_ve_filtre_akademik_gostermez(self):
        js = (ROOT / 'docs' / 'portal.js').read_text(encoding='utf-8')
        self.assertIn("i.kategori!=='akademik'", js)
        self.assertNotIn('Akademik kadrolar', (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8'))

    def test_akademik_ilanin_iptal_duyurusu_sessizce_atlanir(self):
        akademik = ilan('u1', 'ÖRNEK ÜNİVERSİTESİ', '1 TEKNİSYEN ALACAK', ozet='Doçentliğini almış olmak (2547 sayılı Kanun)')
        d = duyuru('csb-5', kurum='ÖRNEK ÜNİVERSİTESİ', baslik='ÖRNEK ÜNİVERSİTESİ TEKNİSYEN ALIM İPTAL İLANI')
        self.yaz([akademik, d], telegram_bekleyen=['csb-5'])
        self.assertEqual(self.calistir(), 0)
        durum = self.durum()
        self.assertIn('csb-5', durum['telegram_gonderilen'])   # tekrar denenmez
        self.assertEqual(durum['telegram_bekleyen'], [])
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [akademik], {'u1': 5}, SIMDI.date()), [])  # aday olamaz

    def test_akademik_bekleyen_kuyruktan_dusurulur(self):
        a = ilan('a', **self.AKADEMIK, kaynak_turu=None)
        bekleyen = {'a'}
        sira = ilan_bot.telegram_sirasi({'a': a}, [a], [], set(), bekleyen, False, False, {})
        self.assertEqual(sira, [])
        self.assertEqual(bekleyen, set())

    def test_akademik_iptal_duyurusu_da_gonderilmez(self):
        d = duyuru(baslik='ÖRNEK ÜNİVERSİTESİ ÖĞRETİM GÖREVLİSİ ALIM İPTAL İLANI')
        self.assertFalse(ilan_bot.telegram_icin_uygun(d, [], []))


class MesajKaydiTesti(Dugum):
    def test_gonderim_basariyla_message_id_kaydeder(self):
        self.yaz([ilan('a', kaynak_turu=None), ilan('b', kaynak_turu=None)])
        self.calistir('--duyur-mevcut', donus=[11, 12])
        self.assertEqual(self.durum()['telegram_mesajlari'], {'a': 11, 'b': 12})

    def test_bool_donus_kayit_yazmaz(self):
        self.yaz([ilan('a', kaynak_turu=None)])
        self.calistir('--duyur-mevcut', donus=[True])
        self.assertEqual(self.durum()['telegram_mesajlari'], {})
        self.assertEqual(self.durum()['telegram_gonderilen'], ['a'])

    def test_telegram_gonder_message_id_dondurur_ve_yanit_alanini_yazar(self):
        class Yanit(io.BytesIO):
            def __enter__(s): return s
            def __exit__(s, *a): return False
        with patch.object(ilan_bot.urllib.request, 'urlopen', return_value=Yanit(b'{"ok":true,"result":{"message_id":321}}')) as api:
            self.assertEqual(ilan_bot.telegram_gonder('t', '@t', 'm', yanit=77), 321)
        veri = api.call_args.args[0].data.decode()
        self.assertIn('reply_parameters', veri)
        self.assertIn('allow_sending_without_reply', __import__('urllib.parse').parse.unquote_plus(veri))
        with patch.object(ilan_bot.urllib.request, 'urlopen', return_value=Yanit(b'{"ok":true}')):
            self.assertIs(ilan_bot.telegram_gonder('t', '@t', 'm'), True)
        with patch.object(ilan_bot.urllib.request, 'urlopen', return_value=Yanit(b'{"ok":false}')):
            self.assertIs(ilan_bot.telegram_gonder('t', '@t', 'm'), False)

    def test_merge_registry_mesaj_kayitlarini_ve_toplu_gunu_korur(self):
        a = {'guncelleme': '2026-10-05T10:00:00+03:00', 'ilanlar': [], 'telegram_mesajlari': {'x': 1, 'y': 2},
             'telegram_toplu_hatirlatma_gunu': '2026-10-05'}
        b = {'guncelleme': '2026-10-05T11:00:00+03:00', 'ilanlar': [], 'telegram_mesajlari': {'z': 3}}
        m = merge_registry(a, b)
        self.assertEqual(m['telegram_mesajlari'], {'x': 1, 'y': 2, 'z': 3})
        self.assertEqual(m['telegram_toplu_hatirlatma_gunu'], '2026-10-05')
        self.assertEqual(merge_registry(b, a)['telegram_mesajlari'], {'x': 1, 'y': 2, 'z': 3})
        self.assertEqual(merge_registry({'ilanlar': []}, {'ilanlar': []})['telegram_mesajlari'], {})

    def test_merge_registry_iptal_isaretini_kaybetmez(self):
        eski = {'guncelleme': '2026-10-05T10:00:00+03:00', 'ilanlar': [{'id': 'a', 'iptal_edildi': 'csb-1'}]}
        yeni = {'guncelleme': '2026-10-05T11:00:00+03:00', 'ilanlar': [{'id': 'a'}]}
        self.assertEqual(merge_registry(eski, yeni)['ilanlar'][0]['iptal_edildi'], 'csb-1')

    def test_takma_ad_kimligiyle_mesaj_bulunur(self):
        ilan_ = {'id': 'sbb-1', 'kaynak_kimlikleri': ['sbb-1', 'iskur-2']}
        self.assertEqual(iptal_yaniti.mesaj_kimligi(ilan_, {'iskur-2': 55}), ('iskur-2', 55))
        self.assertIsNone(iptal_yaniti.mesaj_kimligi(ilan_, {'baska': 5}))


class IptalYanitiTesti(Dugum):
    def senaryo(self, orijinaller, duy=None, mesajlar=None):
        duy = duy or duyuru()
        self.yaz(orijinaller + [duy], gonderilen=[i['id'] for i in orijinaller], telegram_bekleyen=[duy['id']],
                 mesajlar=mesajlar if mesajlar is not None else {i['id']: 500 + n for n, i in enumerate(orijinaller)})

    def test_tek_aday_orijinale_yanit_ve_iptal_edildi(self):
        self.senaryo([ilan('k1')])
        self.assertEqual(self.calistir(donus=[900]), 1)
        a, k = self.cagrilar[0]
        self.assertEqual(k.get('yanit'), 500)
        self.assertIsNone(k.get('foto'))
        self.assertIn('❌ <b>Bu ilan iptal edilmiştir.</b>', a[2])
        self.assertIn('iptal edilmiştir', a[2].split('\n')[1])  # resmî açıklama özeti
        self.assertIn('Kaynak: ÇŞB Yerel Yönetimler', a[2])
        self.assertNotIn('İptal:', a[2])
        durum = self.durum()
        self.assertEqual(self.kayit('k1')['iptal_edildi'], 'csb-1')
        self.assertIn('csb-1', durum['telegram_gonderilen'])
        self.assertEqual(durum['telegram_mesajlari']['csb-1'], 900)
        self.assertEqual(durum['telegram_mesajlari']['k1'], 500)  # geçmiş silinmez

    def test_tekrar_gonderilmez(self):
        self.senaryo([ilan('k1')])
        self.assertEqual(self.calistir(), 1)
        self.assertEqual(self.calistir(), 0)
        self.assertEqual(self.calistir('--duyur-mevcut'), 0)

    def test_aday_yoksa_kartsiz_duz_metin_ve_isaret_yok(self):
        self.senaryo([ilan('k1')], mesajlar={})   # orijinalin message_id'si kayıtlı değil
        self.assertEqual(self.calistir(), 1)
        a, k = self.cagrilar[0]
        self.assertIsNone(k.get('yanit'))
        self.assertIsNone(k.get('foto'))
        self.assertTrue(a[2].startswith('❌ <b>İptal duyurusu:</b> Rize Belediyesi'))  # k1 paylaşıldı ama mesajsız: kural 4
        self.assertIn('Bu ilan iptal edilmiştir.', a[2])
        self.assertTrue(a[3].endswith('/ilan/csb-1/'))  # site bağlantı düğmesi
        self.assertNotIn('iptal_edildi', self.kayit('k1'))
        self.assertIn('csb-1', self.durum()['telegram_gonderilen'])

    def test_birden_cok_aday_duz_metin(self):
        self.senaryo([ilan('k1'), ilan('k2', kadro='2 TEKNİKER ALACAK')])
        self.assertEqual(self.calistir(), 1)
        a, k = self.cagrilar[0]
        self.assertIsNone(k.get('yanit'))
        self.assertTrue(a[2].startswith('❌ <b>İptal duyurusu:</b>'))
        self.assertNotIn('iptal_edildi', self.kayit('k1'))
        self.assertNotIn('iptal_edildi', self.kayit('k2'))

    def test_ortusme_kurum_ve_sure_uyusmazligi_aday_saymaz(self):
        d = duyuru()
        self.assertEqual(len(iptal_yaniti.orijinal_ara(d, [ilan('k1')], {'k1': 1}, SIMDI.date())), 1)
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [ilan('k1', kadro='1 MÜHENDİS ALACAK')], {'k1': 1}, SIMDI.date()), [])
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [ilan('k1', 'TRABZON BELEDİYESİ')], {'k1': 1}, SIMDI.date()), [])
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [ilan('k1', ilk_gorulme=gun(-130))], {'k1': 1}, SIMDI.date()), [])
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [ilan('k1', duyuru_turu='İptal duyurusu')], {'k1': 1}, SIMDI.date()), [])
        # zaten iptal edilmiş ilan aday kalır; karar katmanı sessizce tekrar sayar (aşağıdaki testlere bak)
        self.assertEqual(len(iptal_yaniti.orijinal_ara(d, [ilan('k1', iptal_edildi='csb-0')], {'k1': 1}, SIMDI.date())), 1)
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [ilan('k1')], {}, SIMDI.date()), [])

    def test_belediye_disi_kurum_tam_ad_esitligi(self):
        d = duyuru(kurum='ÖRNEK KURUMU BAŞKANLIĞI', baslik='ÖRNEK KURUMU BAŞKANLIĞI TEKNİKER ALIM İPTAL İLANI')
        self.assertEqual(len(iptal_yaniti.orijinal_ara(d, [ilan('k1', 'Örnek Kurumu Başkanlığı')], {'k1': 1}, SIMDI.date())), 1)
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [ilan('k1', 'Örnek Kurumu Genel Müdürlüğü')], {'k1': 1}, SIMDI.date()), [])

    def test_zayif_unvan_yalniz_ayirt_edici_yoksa_kullanilir(self):
        d = duyuru(baslik='ÇELTİK BELEDİYE BAŞKANLIĞI İLK DEFA ATANMAK ÜZERE MEMUR ALIM İPTAL İLANI', kurum='ÇELTİK BELEDİYE BAŞKANLIĞI',
                   ozet='Çeltik Belediyesinin yazısına istinaden memur alım ilanı iptal edilmiştir.')
        memur = ilan('k1', 'ÇELTİK BELEDİYESİ', '1 MEMUR ALACAK')
        tekniker = ilan('k2', 'ÇELTİK BELEDİYESİ', '1 TEKNİKER ALACAK')
        self.assertEqual([i['id'] for i in iptal_yaniti.orijinal_ara(d, [memur, tekniker], {'k1': 1, 'k2': 2}, SIMDI.date())], ['k1'])

    def test_duzeltme_yanit_yeni_tarih_orijinale_iptal_isareti_yok(self):
        self.senaryo([ilan('k1')], duy=duyuru('csb-2', 'Düzeltme / süre değişikliği', son_tarih='2026-11-06'))
        self.assertEqual(self.calistir(), 1)
        a, k = self.cagrilar[0]
        self.assertEqual(k.get('yanit'), 500)
        self.assertIn('📝 <b>Bu ilanda düzeltme yapıldı.</b>', a[2])
        self.assertIn('Yeni son başvuru:</b> 6 Kasım 2026', a[2])
        self.assertNotIn('iptal_edildi', self.kayit('k1'))

    def test_duzeltme_aday_yoksa_duz_metin(self):
        self.senaryo([ilan('k1')], duy=duyuru('csb-2', 'Düzeltme / süre değişikliği', son_tarih='2026-11-06'), mesajlar={})
        self.calistir()
        a, k = self.cagrilar[0]
        self.assertIsNone(k.get('yanit'))
        self.assertTrue(a[2].startswith('📝 <b>Düzeltme duyurusu:</b> Rize Belediyesi'))
        self.assertIn('6 Kasım 2026', a[2])

    def test_ayni_calistirmada_once_ilan_sonra_iptal_yanit_verir(self):
        orijinal = ilan('k1', kaynak_turu=None, son_tarih=gun(10)[:10])
        self.yaz([orijinal, duyuru()])
        self.assertEqual(self.calistir('--duyur-mevcut', donus=[700, 701]), 2)
        self.assertIsNotNone(self.cagrilar[0][1].get('foto'))      # önce ilan kartı
        self.assertEqual(self.cagrilar[1][1].get('yanit'), 700)     # sonra iptal, orijinal mesaja yanıt
        self.assertEqual(self.kayit('k1')['iptal_edildi'], 'csb-1')

    def test_gonderim_basarisizsa_duyuru_sirada_kalir_isaret_yazilmaz(self):
        self.senaryo([ilan('k1')])
        with self.assertRaises(SystemExit):
            self.calistir(basarili=False)
        self.assertNotIn('iptal_edildi', self.kayit('k1'))
        self.assertNotIn('csb-1', self.durum()['telegram_gonderilen'])
        self.assertEqual(self.calistir(), 1)

    def test_iptal_edilen_ilan_bot_sosyal_ve_toplu_disinda(self):
        k = ilan('k1', kaynak_turu=None, iptal_edildi='csb-1', son_tarih=SIMDI.date().isoformat())
        self.assertEqual(site_uret.bot_ilanlari([k], SIMDI)['ilanlar'], [])
        self.assertEqual(ilan_bot.toplu_secim([k], {'k1'}, {}), [])
        sayfa = site_uret.detail_page(dict(k, link='https://kamuilan.sbb.gov.tr/', id='sbb-' + 'c' * 24))
        self.assertIn('İptal edildi', sayfa[1])
        js = (ROOT / 'docs' / 'portal.js').read_text(encoding='utf-8')
        self.assertIn("i.iptal_edildi)return 'İptal edildi'", js)


class GercekKopyaTesti(Dugum):
    """Gerçek veriden küçültülmüş Mucur ve Rize duyuruları: aynı olayın kopyaları tek ileti üretir."""
    def ornek(self):
        return json.loads((ROOT / 'bot' / 'test_veri' / 'kanal_gercek_ornek.json').read_text(encoding='utf-8'))

    def kur(self):
        o = self.ornek()
        duyurular = [i for i in o['ilanlar'] if i.get('duyuru_turu')]
        self.yaz(o['ilanlar'], gonderilen=o['orijinaller'], telegram_bekleyen=[d['id'] for d in duyurular],
                 mesajlar={k: 100 + n for n, k in enumerate(o['orijinaller'])})
        return duyurular

    def test_mucur_duzeltmesi_iki_kopya_tek_yanit(self):
        o = self.ornek()
        mucur = [i for i in o['ilanlar'] if 'MUCUR' in i['kurum'].upper() and i.get('duyuru_turu')]
        self.assertEqual(len(mucur), 2)
        self.yaz([i for i in o['ilanlar'] if 'MUCUR' in i['kurum'].upper() or 'Mucur' in i['kurum']],
                 gonderilen=['iskur-ced29e58351712e81082b7e6'], telegram_bekleyen=[d['id'] for d in mucur],
                 mesajlar={'iskur-ced29e58351712e81082b7e6': 77})
        self.assertEqual(self.calistir(), 1)
        self.assertEqual(self.cagrilar[0][1].get('yanit'), 77)
        durum = self.durum()
        self.assertTrue(all(d['id'] in durum['telegram_gonderilen'] for d in mucur))   # ikisi de gönderilmiş sayılır
        self.assertTrue(any(k.startswith('o:duzeltme:') for k in durum['telegram_duyuru_yanitlari']))
        self.assertEqual(self.calistir(), 0)

    def test_rize_iptal_kopyalari_kadro_basina_tek_ileti(self):
        duyurular = self.kur()
        self.assertEqual(len(duyurular), 10)  # Rize: gıda x3, tekniker x2, çevre, mimar, peyzaj mimarı; Mucur x2
        sayi = self.calistir()
        metinler = [c[0][2] for c in self.cagrilar]
        rize = [m for m in metinler if 'Rize' in m]
        # 5 farklı kadro (tekniker, gıda, çevre, mimar, peyzaj mimarı); kopyalar sessizce atlanır
        self.assertEqual(len(rize), 5)
        for kadro in ('Gıda Mühendisi', 'Tekniker', 'Çevre Mühendisi', 'Mimar', 'Peyzaj Mimarı'):
            self.assertEqual(sum(kadro.lower() in m.lower() for m in rize), 1 if kadro != 'Mimar' else 2, kadro)  # 'Mimar' peyzaj mimarında da geçer
        self.assertEqual(sayi, 6)             # 5 Rize + 1 Mucur
        self.assertEqual(self.calistir(), 0)  # tekrar gönderilmez
        self.assertTrue(all(d['id'] in self.durum()['telegram_gonderilen'] for d in duyurular))

    def test_duz_metin_tekillestirme_30_gun_sonra_budanir(self):
        duyurular = self.kur()
        durum = self.durum()
        durum['telegram_duyuru_yanitlari'] = {'m:iptal:eski': (SIMDI - timedelta(days=40)).date().isoformat(),
                                              'm:iptal:yeni': (SIMDI - timedelta(days=5)).date().isoformat(),
                                              'o:iptal:kalici': '2025-01-01'}
        self.data.write_text(json.dumps(durum), encoding='utf-8')
        self.calistir()
        yanitlar = self.durum()['telegram_duyuru_yanitlari']
        self.assertNotIn('m:iptal:eski', yanitlar)
        self.assertIn('m:iptal:yeni', yanitlar)
        self.assertIn('o:iptal:kalici', yanitlar)   # orijinale yanıt kayıtları budanmaz

    def test_merge_registry_yanit_kumesini_birlestirir(self):
        a = {'guncelleme': '2026-10-05T10:00:00+03:00', 'ilanlar': [], 'telegram_duyuru_yanitlari': {'o:iptal:a': '2026-10-05'}}
        b = {'guncelleme': '2026-10-05T11:00:00+03:00', 'ilanlar': [], 'telegram_duyuru_yanitlari': {'m:iptal:b': '2026-10-04'}}
        self.assertEqual(merge_registry(a, b)['telegram_duyuru_yanitlari'], {'m:iptal:b': '2026-10-04', 'o:iptal:a': '2026-10-05'})
        self.assertEqual(merge_registry({'ilanlar': []}, {'ilanlar': []})['telegram_duyuru_yanitlari'], {})


class KismiIptalTesti(Dugum):
    def duy(self, baslik, kimlik='csb-7'):
        d = duyuru(kimlik)
        d['baslik'] = baslik
        return d

    def test_tek_kalemli_orijinal_tam_iptal(self):
        o = ilan('k1', kadro='1 TEKNİKER ALACAK')
        self.assertTrue(iptal_yaniti.tam_iptal(self.duy('RİZE BELEDİYESİ ( TEKNİKER ) ALIM İPTAL İLANI'), o))

    def test_cok_kalemli_orijinalde_tek_kadro_kismi_iptal(self):
        o = ilan('k1', kadro='Toplam 3 kişi — 1 TEKNİKER • 1 MİMAR • 1 ZABITA')
        self.assertFalse(iptal_yaniti.tam_iptal(self.duy('RİZE BELEDİYESİ ( TEKNİKER ) ALIM İPTAL İLANI'), o))
        self.assertTrue(iptal_yaniti.tam_iptal(self.duy('RİZE BELEDİYESİ TEKNİKER MİMAR ZABITA ALIM İPTAL İLANI'), o))
        genel = self.duy('RİZE BELEDİYESİ ALIM İPTAL İLANI')
        genel['ozet'] = 'Alım ilanı iptal edilmiştir.'  # kadro adı içermeyen resmî cümle
        self.assertTrue(iptal_yaniti.tam_iptal(genel, o))  # genel iptal

    def test_kadrosu_bilinmeyen_orijinalde_kismi_sayilir(self):
        o = ilan('k1', kadro='')
        self.assertFalse(iptal_yaniti.tam_iptal(self.duy('RİZE BELEDİYESİ ( TEKNİKER ) ALIM İPTAL İLANI'), o))

    def calistir_kismi(self, kadro, *duyurular):
        o = ilan('k1', kadro=kadro)
        self.yaz([o, *duyurular], gonderilen=['k1'], telegram_bekleyen=[d['id'] for d in duyurular], mesajlar={'k1': 500})
        return o

    def test_kismi_iptal_metni_ve_isaret_konmaz(self):
        self.calistir_kismi('Toplam 2 kişi — 1 TEKNİKER • 1 MİMAR', self.duy('RİZE BELEDİYESİ İLK DEFA SÖZLEŞMELİ PERSONEL ( TEKNİKER ) ALIM İPTAL İLANI'))
        self.assertEqual(self.calistir(), 1)
        a, k = self.cagrilar[0]
        self.assertEqual(k.get('yanit'), 500)
        self.assertIn('❌ <b>Bu ilandaki Tekniker alımı iptal edilmiştir.</b>', a[2])
        self.assertNotIn('Bu ilan iptal edilmiştir', a[2])
        self.assertNotIn('iptal_edildi', self.kayit('k1'))   # ilan açık kalır
        # aynı ilanın başka kadrosunun iptali ayrı bildirilir
        durum = self.durum()
        durum['ilanlar'].append(self.duy('RİZE BELEDİYESİ İLK DEFA SÖZLEŞMELİ PERSONEL ( MİMAR ) ALIM İPTAL İLANI', 'csb-8'))
        durum['telegram_bekleyen'] = ['csb-8']
        self.data.write_text(json.dumps(durum), encoding='utf-8')
        self.assertEqual(self.calistir(), 1)
        self.assertIn('Mimar', self.cagrilar[0][0][2])

    def test_tam_iptalde_isaret_konur_ve_ayni_olay_tekrar_gitmez(self):
        self.calistir_kismi('1 TEKNİKER ALACAK', self.duy('RİZE BELEDİYESİ ( TEKNİKER ) ALIM İPTAL İLANI'),
                            self.duy('RİZE BELEDİYE BAŞKANLIĞI TEKNİKER ALIMI İPTALİ', 'sbb-' + 'e' * 24))
        self.assertEqual(self.calistir(), 1)
        self.assertIn('Bu ilan iptal edilmiştir', self.cagrilar[0][0][2])
        self.assertIsNotNone(self.kayit('k1').get('iptal_edildi'))
        self.assertEqual(self.durum()['telegram_bekleyen'], [])

    def test_zaten_iptal_edilmis_tek_aday_sessiz(self):
        o = ilan('k1', kadro='1 TEKNİKER ALACAK', iptal_edildi='csb-0')
        d = self.duy('RİZE BELEDİYESİ ( TEKNİKER ) ALIM İPTAL İLANI')
        self.yaz([o, d], gonderilen=['k1'], telegram_bekleyen=[d['id']], mesajlar={'k1': 500})
        self.assertEqual(self.calistir(), 0)
        self.assertIn(d['id'], self.durum()['telegram_gonderilen'])


class ZayifSozcukTesti(unittest.TestCase):
    def test_genel_kelimeler_guclu_sayilmaz(self):
        d = duyuru(baslik='RİZE BELEDİYESİ İLK DEFA SÖZLEŞMELİ PERSONEL ( TEKNİKER ) ALIM İPTAL İLANI')
        mimar = ilan('k1', kadro='1 MİMAR ALACAK', baslik='RİZE BELEDİYESİ - İLK DEFA SÖZLEŞMELİ PERSONEL ALIM İLANI')
        self.assertEqual(iptal_yaniti.orijinal_ara(d, [mimar], {'k1': 1}, SIMDI.date()), [])
        self.assertEqual(iptal_yaniti.guclu_kokler(d), {'teknik'})
        for sozcuk in ('personel', 'memuru', 'işçisi', 'sözleşmeli'):
            self.assertEqual(iptal_yaniti.guclu_kokler(duyuru(baslik='RİZE BELEDİYESİ ' + sozcuk + ' ALIM İPTAL İLANI')), set(), sozcuk)


class AkademikBastirmaTesti(Dugum):
    def test_kpss_li_duyuru_akademik_yuzunden_yutulmaz(self):
        akademik = ilan('u1', 'ÖRNEK ÜNİVERSİTESİ', '1 TEKNİSYEN ALACAK', ozet='Doçentliğini almış olmak (2547 sayılı Kanun)')
        diger = ilan('u2', 'ÖRNEK ÜNİVERSİTESİ', '1 TEKNİSYEN ALACAK')  # akademik olmayan eşleşme, mesaj kaydı YOK
        d = duyuru('csb-5', kurum='ÖRNEK ÜNİVERSİTESİ', baslik='ÖRNEK ÜNİVERSİTESİ TEKNİSYEN ALIM İPTAL İLANI')
        self.yaz([akademik, diger, d], gonderilen=['u2'], telegram_bekleyen=['csb-5'])
        self.assertEqual(self.calistir(), 1)           # bastırılmaz, düz metin gider
        self.assertIsNone(self.cagrilar[0][1].get('yanit'))


class AkademikTanimaTesti(unittest.TestCase):
    def test_bolunmus_sartlardan_sivas_btu_akademik(self):
        r = {'id': 'x', 'baslik': 'SİVAS BİLİM VE TEKNOLOJİ ÜNİVERSİTESİ - 33 ALACAK', 'kurum': 'SİVAS BİLİM VE TEKNOLOJİ ÜNİVERSİTESİ', 'kadro': '33 ALACAK',
             'sartlar': [{'kadro': 'Belgede belirtilen koşullar', 'metin': 'Profesör  kadroları için ilgili alanda doktora'},
                         {'kadro': 'x', 'metin': 'Doçent\nKadroları için doçentlik'}, {'kadro': 'Öğretim / Görevlisi', 'metin': 'y'}]}
        self.assertTrue(akademik_ilan(r))
        for metin in ('Profesör kadroları', 'Doçent Kadroları', 'Öğretim / Görevlisi', 'yabancı dille öğretim yapılmasında'):
            self.assertTrue(akademik_ilan({'id': 'y', 'baslik': 'X ÜNİVERSİTESİ', 'sartlar': [{'kadro': 'a', 'metin': metin}]}), metin)

    def test_kpssli_universite_memur_tekniker_kutuphaneci_akademik_degil(self):
        for kadro, sart in [('3 TEKNİKER', 'Ön lisans mezunu olmak, KPSS P93 puanı'), ('2 KÜTÜPHANECİ', 'Lisans mezunu, KPSS P3 en az 70 puan'),
                            ('5 MEMUR', 'KPSS P94 puan türünden'), ('1 BİLGİSAYAR İŞLETMENİ', 'Lise mezunu olmak')]:
            self.assertFalse(akademik_ilan({'id': 'z', 'baslik': 'ÖRNEK ÜNİVERSİTESİ - ' + kadro + ' ALACAK', 'kurum': 'ÖRNEK ÜNİVERSİTESİ',
                                            'kadro': kadro, 'sartlar': [{'kadro': kadro, 'metin': sart}]}), kadro)


class IptalIsaretiBirlesmeTesti(unittest.TestCase):
    def test_merge_sources_isaret_kalici_kayda_aktarilir(self):
        import ek_kaynaklar as ek
        link = 'https://www.iskur.gov.tr/medya/x.pdf'
        kalici = {'id': 'iskur-' + 'a' * 24, 'baslik': 'A', 'kurum': 'Rize Belediyesi', 'kaynak_turu': 'iskur', 'link': link, 'son_tarih': '2026-11-01'}
        isaretli = {'id': 'sbb-' + 'b' * 24, 'baslik': 'A', 'kurum': 'Rize Belediyesi', 'kaynak_turu': 'sbb', 'link': link, 'son_tarih': '2026-11-01',
                    'iptal_edildi': 'csb-9'}
        sonuc = ek.merge_sources([isaretli], {kalici['id']: kalici, isaretli['id']: isaretli})
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0]['iptal_edildi'], 'csb-9')

    def test_merge_registry_takma_ada_donusen_kaydin_isareti_korunur(self):
        eski = {'guncelleme': '2026-10-05T10:00:00+03:00', 'ilanlar': [{'id': 'b', 'iptal_edildi': 'csb-9'}, {'id': 'a'}]}
        yeni = {'guncelleme': '2026-10-05T11:00:00+03:00', 'ilanlar': [{'id': 'a', 'kaynak_kimlikleri': ['a', 'b']}]}
        m = merge_registry(eski, yeni)
        self.assertEqual([i['id'] for i in m['ilanlar']], ['a'])
        self.assertEqual(m['ilanlar'][0]['iptal_edildi'], 'csb-9')


ADANA = 'ADANA ALPARSLAN TÜRKEŞ BİLİM VE TEKNOLOJİ ÜNİVERSİTESİ'
ADANA_CUMLE = ('20.09.2026 tarihli ve 33376 sayılı Resmi Gazete’de yayımlanan ve aşağıda belirtilen 6 Sıra Nolu Havacılık ve Uzay '
               'Bilimleri Fakültesi Havacılık Yönetimi Bölümü Havacılık Yönetimi Anabilim Dalı 1 (bir) adet Araştırma Görevlisi '
               'kadrosu ilanımız iptal edilmiştir.')
JUNK = 'İPTAL İLANI. Kadroya göre değişen eğitim ve deneyim koşulları aşağıda ayrı olarak gösterilmiştir.'


def sbb_duyuru(kimlik='sbb-' + '8' * 24, kurum=ADANA, cumle=None, **ek):
    r = {'id': kimlik, 'baslik': f'{kurum} - İPTAL İLANI', 'kurum': kurum, 'kadro': 'İPTAL İLANI',
         'duyuru_turu': 'İptal duyurusu', 'ozet': JUNK, 'kaynak_turu': 'sbb', 'kaynak': 'SBB Kamu İlan',
         'link': 'https://kamuilan.sbb.gov.tr/', 'son_tarih': None, 'ilk_gorulme': gun(0)}
    if cumle is not None:
        r['duyuru_cumlesi'] = cumle
    r.update(ek)
    return r


def adana_orijinal():
    return {'id': 'sbb-' + '7' * 24, 'baslik': f'{ADANA} - 25 ÖĞRETİM ELEMANI ALACAK', 'kurum': ADANA,
            'kadro': '25 ÖĞRETİM ELEMANI ALACAK', 'kategori': 'akademik', 'kaynak_turu': 'sbb',
            'link': 'https://kamuilan.sbb.gov.tr/', 'son_tarih': gun(20)[:10], 'ilk_gorulme': gun(-7)}


class CumleKadrosuTesti(unittest.TestCase):
    def test_gercek_cumleler(self):
        tablo = [
            (ADANA_CUMLE, 'Araştırma Görevlisi'),
            ('Sağlık Bilimleri Fakültesi Ebelik Bölümü Ebelik Ana Bilim Dalı Doçent kadrosu ilanımız iptal edilmiştir.', 'Doçent'),
            ('Fen Edebiyat Fakültesi Sanat Tarihi Bölümü 4.Derece Doktor Öğretim Üyesi kadrosu iptal edilmiştir.', 'Doktor Öğretim Üyesi'),
            ('Gazete de yayımlanan İlk Defa Zabıta Memuru alımı ilanı iptal edilmiştir.', 'Zabıta Memuru'),
            ('Çukurkuyu Belediyesinin yazısına istinaden ilk defa zabıta memuru alımı ilanı iptal edildi.', 'zabıta memuru'),
            ('Rize Belediyesinin yazısına istinaden ilk defa atanmak üzere sözleşmeli personel (Gıda Mühendisi) alım ilanı iptal edilmiştir.', 'Gıda Mühendisi'),
            ('Rize Belediyesinin yazısına istinaden ilk defa sözleşmeli personel (peyzaj mimarı) alım ilanı iptal edilmiştir.', 'peyzaj mimarı'),
            ('Üsküdar Belediyesinin yazısına istinaden ilk defa memur ve zabıta memuru alım ilanı iptal edilmiştir.', 'zabıta memuru'),
            ('Resmî Gazete’de yayımlanan ilk defa atanmak üzere sözleşmeli personel alım ilanı iptal edilmiştir.', ''),
            ('Sözleşmeli Personel Alım ilanımızda yer alan ve aşağıda belirtilen 2 ve 5. sıradaki kadro pozisyonuna ait ilanımız iptal edilmiştir.', ''),
            ('Resmî Gazete ’de yayımlanan aşağıda birimi, anabilim dalı, unvanı, adedi ve nitelikleri belirtilen kadroya ilişkin ilanımız iptal edilmiştir.', ''),
        ]
        for cumle, beklenen in tablo:
            self.assertEqual(iptal_yaniti.cumle_kadrosu(cumle), beklenen, cumle)


class IptalIcerigiTesti(Dugum):
    def karar(self, d, ilanlar, mesajlar=None, gonderilen=()):
        return ilan_bot.duyuru_karari(d, ilanlar + [d], mesajlar or {}, {}, SIMDI.date(), gonderilen=set(gonderilen))

    def test_adana_gercek_senaryo_gonderilmez(self):
        n = sbb_duyuru(cumle=ADANA_CUMLE)
        self.yaz([adana_orijinal(), n], telegram_bekleyen=[n['id']])
        self.assertEqual(self.calistir(), 0)
        self.assertEqual(self.durum()['telegram_bekleyen'], [])  # akademik: kuyruktan düşer (gonderilen'e yazılmaz)
        self.assertTrue(akademik_ilan(n))
        self.assertIsNone(site_uret.detail_page(dict(n, id='sbb-' + '8' * 24)))

    def test_cumlesiz_adana_kurum_kuraliyla_sessiz(self):
        k = self.karar(sbb_duyuru(), [adana_orijinal()], gonderilen=set())
        self.assertEqual(k['islem'], 'sessiz')
        self.assertIn('akademik', k['sebep'])

    def test_kural_1b_akademik_olmayan_ilani_yutmaz(self):
        diger = ilan('d1', ADANA, '2 TEKNİKER', baslik=f'{ADANA} - 2 TEKNİKER')
        k = self.karar(sbb_duyuru(), [adana_orijinal(), diger], gonderilen=['d1'])
        self.assertNotEqual(k.get('sebep'), 'akademik ilana ait (kurum)')

    def test_kural_3_orijinal_kanalda_paylasilmadi(self):
        self.senaryo = None
        k = self.karar(duyuru(), [ilan('k1')], gonderilen=set())
        self.assertEqual((k['islem'], k['sebep']), ('sessiz', 'orijinal kanalda paylaşılmadı'))

    def test_kural_4_referansli_duz_metin(self):
        d = duyuru()
        self.yaz([ilan('k1'), d], gonderilen=['k1'], telegram_bekleyen=[d['id']])
        self.assertEqual(self.calistir(), 1)
        a, k = self.cagrilar[0]
        self.assertIsNone(k.get('yanit'))
        self.assertTrue(a[2].startswith('❌ <b>İptal duyurusu:</b> Rize Belediyesi'))
        self.assertIn('📌 ', a[2])
        self.assertIn('tarihli ilan', a[2])
        self.assertIn('Bu ilan iptal edilmiştir.', a[2])
        self.assertIn('Tekniker alım ilanı iptal edilmiştir', a[2])
        self.assertNotIn('ilanı ilanı', a[2])
        self.assertNotIn('İptal İlanı', a[2])
        self.assertNotIn('iptal_edildi', self.kayit('k1'))

    def test_kural_5_icerik_belirsiz(self):
        d = sbb_duyuru(kurum='ÖRNEK BELEDİYESİ')
        k = self.karar(d, [], gonderilen=set())
        self.assertEqual((k['islem'], k['sebep']), ('sessiz', 'içerik belirsiz'))

    def test_kural_6_somut_icerikli_duz_metin(self):
        d = sbb_duyuru(kurum='ÖRNEK BELEDİYESİ', cumle='Resmi Gazete’de yayımlanan İlk Defa Zabıta Memuru alımı ilanı iptal edilmiştir.')
        self.yaz([d], telegram_bekleyen=[d['id']])
        self.assertEqual(self.calistir(), 1)
        metin = self.cagrilar[0][0][2]
        self.assertIn('<b>Zabıta Memuru alımı iptal edilmiştir.</b>', metin)
        self.assertNotIn('📌', metin)

    def test_genel_baslik_cumle_ile_posted_orijinale_yanit(self):
        o = ilan('k1', kadro='1 ZABITA MEMURU ALACAK')
        d = sbb_duyuru(kurum='RİZE BELEDİYESİ', cumle='Resmi Gazete’de yayımlanan İlk Defa Zabıta Memuru alımı ilanı iptal edilmiştir.')
        self.yaz([o, d], gonderilen=['k1'], telegram_bekleyen=[d['id']], mesajlar={'k1': 500})
        self.assertEqual(self.calistir(), 1)
        a, k = self.cagrilar[0]
        self.assertEqual(k.get('yanit'), 500)
        self.assertIn('Bu ilan iptal edilmiştir.', a[2])
        self.assertNotIn('Kadroya göre', a[2])
        self.assertIsNotNone(self.kayit('k1').get('iptal_edildi'))

    def test_genel_baslik_cumle_kismi_iptal(self):
        o = ilan('k1', kadro='Toplam 2 kişi — 1 ZABITA MEMURU • 1 TEKNİKER')
        d = sbb_duyuru(kurum='RİZE BELEDİYESİ', cumle='Resmi Gazete’de yayımlanan İlk Defa Zabıta Memuru alımı ilanı iptal edilmiştir.')
        self.yaz([o, d], gonderilen=['k1'], telegram_bekleyen=[d['id']], mesajlar={'k1': 500})
        self.assertEqual(self.calistir(), 1)
        self.assertIn('Bu ilandaki Zabıta Memuru alımı iptal edilmiştir.', self.cagrilar[0][0][2])
        self.assertNotIn('iptal_edildi', self.kayit('k1'))

    def test_zayif_baslik_cumledeki_kadro_kismi_iptal(self):
        o = ilan('k1', 'ÖRNEK BELEDİYE BAŞKANLIĞI', 'Toplam 2 kişi — 1 GIDA MÜHENDİSİ • 1 MİMAR')
        d = sbb_duyuru(kurum='ÖRNEK BELEDİYE BAŞKANLIĞI', baslik='ÖRNEK BELEDİYE BAŞKANLIĞI - SÖZLEŞMELİ PERSONEL İPTAL İLANI',
                       cumle='Resmi Gazete’de yayımlanan ilk defa sözleşmeli personel (Gıda Mühendisi) alım ilanı iptal edilmiştir.')
        k = self.karar(d, [o], mesajlar={'k1': 500}, gonderilen=['k1'])
        self.assertEqual(k['islem'], 'gonder')
        self.assertIs(k['tam'], False)
        self.assertIn('Bu ilandaki Gıda Mühendisi alımı iptal edilmiştir.', ilan_bot.duyuru_metni(d, True, k['tam']))
        self.yaz([o, d], gonderilen=['k1'], telegram_bekleyen=[d['id']], mesajlar={'k1': 500})
        self.assertEqual(self.calistir(), 1)
        self.assertNotIn('iptal_edildi', self.kayit('k1'))

    def test_kural_4_referans_zaten_iptal_sessiz(self):
        k = self.karar(duyuru(), [ilan('k1', iptal_edildi='csb-0')], gonderilen=['k1'])
        self.assertEqual((k['islem'], k['sebep']), ('sessiz', 'orijinal zaten iptal edilmiş'))

    def test_site_ozet_duyuru_cumlesiyle_ayniysa_tekrarlanmaz(self):
        n = sbb_duyuru(cumle='Zabıta alımı ilanı iptal edilmiştir.', ozet='Zabıta alımı ilanı iptal edilmiştir.', kurum='ÖRNEK BELEDİYESİ')
        sayfa = site_uret.detail_page(n)[1]
        self.assertEqual(sayfa.count('Zabıta alımı ilanı iptal edilmiştir.'), 1)
        self.assertNotIn('İlan özeti', sayfa)

    def test_akademik_tanima_kapsami(self):
        csb = duyuru('csb-9', ozet='Üniversitesinin araştırma görevlisi alım ilanı iptal edilmiştir.')
        self.assertTrue(akademik_ilan(csb))
        normal = ilan('n1', kadro='1 TEKNİKER', ozet='Öğretim görevlisi gözetiminde çalışacaktır.')
        self.assertFalse(akademik_ilan(normal))

    def test_gecmise_donuk_pdf_cumlesi_eklenir(self):
        n = sbb_duyuru(belge_sha256='a' * 64, kurum='ÖRNEK BELEDİYESİ')
        self.yaz([n], telegram_bekleyen=[])
        with patch('ilan_bot.belge_cumlesi', return_value='X kadrosu iptal edilmiştir.'):
            self.calistir()
        k = self.kayit(n['id'])
        self.assertEqual(k['duyuru_cumlesi'], 'X kadrosu iptal edilmiştir.')
        self.assertEqual(k['ozet'], JUNK)
        self.assertEqual(k['kadro'], 'İPTAL İLANI')


if __name__ == '__main__':
    unittest.main()
