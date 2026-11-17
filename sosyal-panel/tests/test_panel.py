"""Sosyal panel testleri (ağ yok). Çalıştırma: cd sosyal-panel && python -m unittest discover -s tests"""
import json
import sys
import threading
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from panel import analiz as an  # noqa: E402
from panel import kaynaklar as k  # noqa: E402
from panel.db import Depo  # noqa: E402
from panel.siniflandir import KartTasarimi, gecmis_sablonu, metin_sablonu  # noqa: E402
from panel.sunucu import Uygulama, isleyici  # noqa: E402

SIMDI = datetime.now(timezone.utc).replace(microsecond=0)


def iso(**fark):
    return (SIMDI - timedelta(**fark)).isoformat()


TELEGRAM_HTML = '''
<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="kpsstercihi/41">
<a class="tgme_widget_message_photo_wrap 1" href="https://t.me/kpsstercihi/41" style="width:800px;background-image:url('https://cdn.example/a.jpg')"></a>
<div class="tgme_widget_message_text js-message_text" dir="auto">Akhisar Belediye Başkanlığı  · 1 kişi · <a href="?q=%23lisans">#lisans</a></div>
<div class="tgme_widget_message_footer"><span class="tgme_widget_message_views">1.2K</span>
<a class="tgme_widget_message_date" href="https://t.me/kpsstercihi/41"><time datetime="2026-10-21T08:39:23+00:00" class="time">08:39</time></a></div></div></div>
<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="kpsstercihi/42">
<div class="tgme_widget_message_reply"></div>
<div class="tgme_widget_message_text js-message_text" dir="auto">❌ İptal duyurusu:<br/>Muş İli Elmakaya Belediyesinin alımı iptal edilmiştir.</div>
<span class="tgme_widget_message_views">459</span><time datetime="2026-10-21T08:40:00+00:00"></time></div></div>
'''

YT_RSS = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <id>yt:video:abc123</id><yt:videoId>abc123</yt:videoId>
  <title>Kpss şartı olmadan 3 ilan #shorts</title>
  <link rel="alternate" href="https://www.youtube.com/shorts/abc123"/>
  <published>2026-11-15T16:29:27+00:00</published>
  <media:group><media:title>x</media:title>
   <media:thumbnail url="https://i4.ytimg.com/vi/abc123/hqdefault.jpg" width="480" height="360"/>
   <media:description>açıklama</media:description>
   <media:community><media:statistics views="671"/></media:community>
  </media:group>
 </entry>
</feed>'''


class DepoTesti(unittest.TestCase):
    def setUp(self):
        self.d = Depo(':memory:')

    def test_ayni_olcum_tekrar_yazilmaz_degisen_yazilir(self):
        gid = self.d.gonderi_yaz('telegram', 1, baslik='a', yayin=iso(days=3))
        self.assertTrue(self.d.olcum_yaz(gid, {'views': 10}, zaman=iso(hours=5)))
        self.assertFalse(self.d.olcum_yaz(gid, {'views': 10}, zaman=iso(hours=4)))
        self.assertTrue(self.d.olcum_yaz(gid, {'views': 15}, zaman=iso(hours=1)))
        self.assertEqual([s['views'] for s in self.d.seri(gid)], [10, 15])

    def test_none_alan_eskisini_korur(self):
        self.d.gonderi_yaz('youtube', 'v', baslik='Başlık', sablon='Yeni ilan')
        self.d.gonderi_yaz('youtube', 'v', baslik=None, url='https://y')
        g = self.d.gonderiler()[0]
        self.assertEqual((g['baslik'], g['sablon'], g['url']), ('Başlık', 'Yeni ilan', 'https://y'))

    def test_son_olcum_eksik_olcutleri_eskiden_tamamlar_ve_24s_degisim(self):
        gid = self.d.gonderi_yaz('instagram', 'm', yayin=iso(days=5))
        self.d.olcum_yaz(gid, {'views': 100, 'likes': 3}, zaman=iso(hours=30))
        self.d.olcum_yaz(gid, {'views': 140}, zaman=iso(hours=1))
        g = self.d.gonderiler()[0]
        self.assertEqual((g['son']['views'], g['son']['likes']), (140, 3))
        self.assertEqual(g['onceki']['views'], 100)

    def test_ornek_veri_isaretli_ve_ayri(self):
        from panel.ornek import doldur
        doldur(self.d, adet=5)
        self.assertTrue(all(g['ornek'] == 1 for g in self.d.gonderiler()))
        gercek = Depo(':memory:')
        self.assertEqual(gercek.gonderiler(), [])   # gerçek depo kendiliğinden örnekle dolmaz


class AyristirmaTesti(unittest.TestCase):
    def test_telegram_sayilari(self):
        self.assertEqual(k.telegram_sayi('1.2K'), 1200)
        self.assertEqual(k.telegram_sayi('15'), 15)
        self.assertEqual(k.telegram_sayi('3,4M'), 3_400_000)
        self.assertIsNone(k.telegram_sayi(''))

    def test_telegram_sayfasi(self):
        m = k.telegram_ayristir(TELEGRAM_HTML)
        self.assertEqual([x['no'] for x in m], [41, 42])
        self.assertEqual(m[0]['views'], 1200)
        self.assertEqual(m[0]['url'], 'https://t.me/kpsstercihi/41')
        self.assertEqual(m[0]['bicim'], 'Görsel')
        self.assertEqual(m[0]['kapak'], 'https://cdn.example/a.jpg')
        self.assertIn('Akhisar', m[0]['metin'])
        self.assertTrue(m[1]['yanit'])
        self.assertIn('\n', m[1]['metin'])

    def test_youtube_rss(self):
        v = k.youtube_rss_ayristir(YT_RSS)[0]
        self.assertEqual((v['id'], v['views'], v['url']), ('abc123', 671, 'https://www.youtube.com/shorts/abc123'))
        self.assertEqual(v['yayin'], '2026-11-15T16:29:27+00:00')

    def test_metin_sablonlari(self):
        self.assertEqual(metin_sablonu('❌ İptal duyurusu: …'), 'İptal duyurusu')
        self.assertEqual(metin_sablonu('☀️ Günaydın — 22 Ekim Perşembe'), 'Sabah son gün')
        self.assertEqual(metin_sablonu('🌙 Bugün 2 yeni kamu ilanı yayımlandı · 167 kadro'), 'Akşam özeti')
        self.assertEqual(metin_sablonu('Tarım ve Orman Bakanlığı  · 13 kişi ·  #bilişim'), 'İlan kartı')
        self.assertEqual(metin_sablonu('🔴 3 gün kaldı\n\nKurum'), 'Son gün hatırlatma')
        self.assertEqual(metin_sablonu(''), 'Metinsiz')

    def test_gecmis_sablonlari(self):
        self.assertEqual(gecmis_sablonu({'vakit': 'sabah', 'tur': 'son_gun'}), 'Sabah son gün')
        self.assertEqual(gecmis_sablonu({'vakit': 'ilan', 'tur': 'ilan'}), 'Yeni ilan')
        self.assertEqual(gecmis_sablonu({'vakit': 'aksam', 'tur': 'yeni'}), 'Akşam özeti')
        self.assertEqual(gecmis_sablonu({'vakit': 'aksam', 'tur': 'kategori'}), 'Konu: Kategori')

    def test_kart_tasarimi_kurali_yoksa_tahmin_yok(self):
        kt = KartTasarimi({'telegram_mesajlari': {'a': 5}, 'ilanlar': [{'id': 'a'}]}, bot_klasoru='/yok')
        kt.secim = None
        self.assertIsNone(kt.tasarim(5))
        kt.secim = lambda ilan: 'bilet'
        self.assertEqual(kt.tasarim(5), 'Bilet')
        self.assertIsNone(kt.tasarim(6))   # eşleşmeyen mesaj


class KaynakIslemeTesti(unittest.TestCase):
    def setUp(self):
        self.d = Depo(':memory:')

    def test_gecmis_kayitlari(self):
        gecmis = [{'zaman': '2026-11-10T12:30:00+03:00', 'vakit': 'sabah', 'tur': 'son_gun', 'ilanlar': ['a', 'b'],
                   'palet': 'kagit', 'ig_id': '111', 'tt_id': '6af9ddd216191f4f5d2fc3a6', 'fb_id': '99',
                   'ig': {'views': 150, 'reach': 120, 'likes': 2, 'olcum': '2026-11-13T19:00:00+03:00'}},
                  {'zaman': '2026-10-20T12:30:00+03:00', 'vakit': 'sabah', 'tur': 'son_gun', 'ig_id': '222',
                   'tt_id': 'v_inbox_file~v2.1'}]
        self.assertEqual(k.gecmis_isle(self.d, gecmis), 4)
        g = {x['id']: x for x in self.d.gonderiler()}
        self.assertNotIn('tiktok:v_inbox_file~v2.1', g)   # taslak kimlikleri yayında değildi
        self.assertEqual(g['instagram:111']['sablon'], 'Sabah son gün')
        self.assertEqual(g['instagram:111']['palet'], 'kagit')
        self.assertEqual(g['instagram:111']['son']['views'], 150)
        self.assertEqual(g['instagram:111']['yayin'], '2026-11-10T09:30:00+00:00')
        self.assertEqual(g['facebook:99']['url'], 'https://www.facebook.com/reel/99')
        self.assertEqual(g['instagram:111']['icerik'], g['tiktok:6af9ddd216191f4f5d2fc3a6']['icerik'])

    def test_bulut_eseri_kalici_baglanti_ve_insights(self):
        k.gecmis_isle(self.d, [{'zaman': '2026-11-10T12:30:00+03:00', 'vakit': 'ilan', 'tur': 'ilan', 'ig_id': '111'}])
        veri = {'zaman': '2026-11-15T10:00:00+00:00',
                'instagram': {'durum': 'hazir', 'aciklama': '2 medya', 'medyalar': [
                    {'id': '111', 'permalink': 'https://www.instagram.com/reel/ABC/', 'caption': 'Yeni ilan\nmetin',
                     'timestamp': '2026-11-10T09:31:00+0000', 'media_type': 'VIDEO', 'media_product_type': 'REELS',
                     'insights': {'views': 300, 'reach': 250, 'ig_reels_avg_watch_time': 4200, 'total_interactions': 9}},
                    {'id': '333', 'permalink': 'https://www.instagram.com/p/XYZ/', 'caption': 'Galatasaray Üniversitesi · 1 kişi ·',
                     'timestamp': '2026-11-11T09:00:00+0000', 'media_type': 'IMAGE', 'like_count': 4, 'insights': {'reach': 80}}]},
                'youtube': {'durum': 'hata', 'aciklama': 'izin yok'},
                'buffer': {'durum': 'hazir', 'aciklama': '1', 'gonderiler': [
                    {'id': 'bf1', 'channelService': 'tiktok', 'externalLink': 'https://www.tiktok.com/@kpsstercihi/video/1?utm_source=1',
                     'text': 'Metin', 'sentAt': '2026-11-10T09:32:00Z'}]}}
        s = k.bulut_isle(self.d, veri)
        self.assertEqual(s['instagram'][2], 2)
        self.assertEqual(s['youtube_api'][0], 'hata')
        g = {x['id']: x for x in self.d.gonderiler()}
        self.assertEqual(g['instagram:111']['url'], 'https://www.instagram.com/reel/ABC/')
        self.assertEqual(g['instagram:111']['sablon'], 'Yeni ilan')        # bot şablonu korunur
        self.assertEqual(g['instagram:111']['son']['avg_watch_ms'], 4200)
        self.assertEqual(g['instagram:111']['son']['interactions'], 9)
        self.assertEqual(g['instagram:333']['sablon'], 'İlan kartı')
        self.assertEqual(g['instagram:333']['son']['likes'], 4)
        self.assertEqual(g['tiktok:bf1']['url'], 'https://www.tiktok.com/@kpsstercihi/video/1')

    def test_facebook_ve_tiktok_olcumleri(self):
        k.gecmis_isle(self.d, [{'zaman': '2026-11-10T12:30:00+03:00', 'vakit': 'sabah', 'tur': 'son_gun',
                                'tt_id': 'bf1', 'fb_id': '777'}])
        veri = {'zaman': '2026-11-15T10:00:00+00:00',
                'facebook': {'durum': 'hazir', 'aciklama': '2 reel', 'reels': [
                    {'id': '777', 'description': 'Son gün yaklaşan ilanlar', 'created_time': '2026-11-10T09:31:00+0000',
                     'permalink_url': 'https://www.facebook.com/reel/777', 'picture': 'https://cdn/p.jpg',
                     'insights': {'views': 410, 'reach': 300, 'likes': 12, 'comments': 2, 'shares': 3, 'avg_watch_ms': 5100}},
                    {'id': '888', 'description': 'x', 'insights_hata': 'izin yok'}]},
                'buffer': {'durum': 'hazir', 'aciklama': '1', 'gonderiler': [
                    {'id': 'bf1', 'channelService': 'tiktok', 'externalLink': 'https://www.tiktok.com/@kpsstercihi/video/1',
                     'text': 'Metin', 'sentAt': '2026-11-10T09:32:00Z', 'metricsUpdatedAt': '2026-11-14T00:00:00Z',
                     'metrics': [{'name': 'Views', 'type': 'views', 'unit': 'count', 'value': 1500.0},
                                 {'name': 'Likes', 'type': 'reactions', 'unit': 'count', 'value': 40},
                                 {'name': 'Comments', 'type': 'comments', 'unit': 'count', 'value': 3},
                                 {'name': 'Engagement', 'type': 'engagementRate', 'unit': 'percentage', 'value': 4.2}]}]}}
        s = k.bulut_isle(self.d, veri)
        g = {x['id']: x for x in self.d.gonderiler()}
        self.assertEqual(g['facebook:777']['son']['views'], 410)
        self.assertEqual(g['facebook:777']['son']['shares'], 3)
        self.assertEqual(g['facebook:777']['sablon'], 'Sabah son gün')   # bot şablonu korunur
        self.assertEqual(g['facebook:777']['url'], 'https://www.facebook.com/reel/777')
        self.assertIsNone(g['facebook:888']['son'])
        self.assertEqual(s['facebook'][0], 'hazir')
        self.assertEqual(s['facebook'][2], 1)
        self.assertEqual(g['tiktok:bf1']['son']['views'], 1500)
        self.assertEqual(g['tiktok:bf1']['son']['likes'], 40)
        self.assertEqual(g['tiktok:bf1']['son']['comments'], 3)
        self.assertEqual(s['tiktok'][0], 'hazir')

    def test_tiktok_metrics_yoksa_kismi_facebook_yoksa_bekliyor(self):
        veri = {'buffer': {'durum': 'hazir', 'aciklama': '1', 'gonderiler': [
            {'id': 'bf2', 'channelService': 'tiktok', 'externalLink': 'https://www.tiktok.com/@kpsstercihi/video/2'}]},
            'facebook': {'durum': 'bekliyor', 'aciklama': 'FB_* yok'}}
        s = k.bulut_isle(self.d, veri)
        self.assertEqual(s['tiktok'][0], 'kismi')
        self.assertEqual(s['facebook'][0], 'bekliyor')
        self.assertIsNone(k.bulut_isle(self.d, {'buffer': {'durum': 'atlandi'}})['tiktok'])

    def test_buffer_metrik_eslemesi(self):
        m = k.buffer_metrikleri([{'type': 'impressions', 'unit': 'count', 'value': 900},
                                 {'type': 'views', 'unit': 'count', 'value': 700},
                                 {'type': 'reach', 'unit': 'count', 'value': 5},
                                 {'type': 'averageTimeWatched', 'unit': 'count', 'value': 9}, None])
        self.assertEqual(m, {'views': 700, 'reach': 5})
        self.assertEqual(k.buffer_metrikleri(None), {})

    def test_youtube_bot_paylasimiyla_eslesir(self):
        k.gecmis_isle(self.d, [{'zaman': '2026-11-15T19:27:09+03:00', 'vakit': 'aksam', 'tur': 'kategori',
                                'muzik': 'hip-hop.mp3', 'ig_id': '9'}])
        gid = k.youtube_yaz(self.d, 'abc', 'Başlık', '2026-11-15T16:29:27+00:00')
        g = {x['id']: x for x in self.d.gonderiler()}[gid]
        self.assertEqual((g['sablon'], g['muzik']), ('Konu: Kategori', 'hip-hop.mp3'))
        gid2 = k.youtube_yaz(self.d, 'uzak', 'Son gün yaklaşan', '2026-11-18T16:29:27+00:00')
        self.assertIsNone({x['id']: x for x in self.d.gonderiler()}[gid2]['muzik'])


class AnalizTesti(unittest.TestCase):
    def gonderi(self, i, deger, saat=30, platform='telegram', sablon='İlan kartı'):
        return {'id': f'{platform}:{i}', 'platform': platform, 'yayin': iso(hours=saat), 'sablon': sablon,
                'son': {'views': deger, 'likes': 1}, 'onceki': None}

    def test_puan_donem_tabanina_gore_ve_olgunluk(self):
        liste = [self.gonderi(i, 100, saat=100 + i) for i in range(10)] + [self.gonderi('genc', 300, saat=5)]
        an.zenginlestir(liste, simdi=SIMDI)
        genc = liste[-1]
        self.assertFalse(genc['olgun'])
        self.assertEqual(genc['puan'], 3.0)
        self.assertTrue(liste[0]['olgun'])
        self.assertEqual(liste[0]['puan'], 1.0)

    def test_toplu_gonderim_tabani_bozmaz(self):
        # 200 eski düşük izlenmeli mesaj aynı saatte; sonraki dönem mesajları kendi komşularıyla kıyaslanır.
        eski = [self.gonderi(f'e{i}', 8, saat=2000) for i in range(200)]
        yeni = [self.gonderi(f'y{i}', 450 + i, saat=1000 - i * 10) for i in range(30)]
        an.zenginlestir(eski + yeni, simdi=SIMDI)
        self.assertTrue(all(0.8 < g['puan'] < 1.2 for g in yeni[10:]))

    def test_kirilim_ve_siralama(self):
        liste = ([self.gonderi(f'a{i}', 200, saat=60 + i, sablon='Sabah son gün') for i in range(5)]
                 + [self.gonderi(f'b{i}', 50, saat=80 + i, sablon='Akşam özeti') for i in range(5)])
        an.zenginlestir(liste, simdi=SIMDI)
        sonuc = an.analiz(liste, simdi=SIMDI)
        satirlar = sonuc['kirilimlar']['sablon']['satirlar']
        self.assertEqual(satirlar[0]['ad'], 'Sabah son gün')
        self.assertGreater(satirlar[0]['medyan_puan'], satirlar[1]['medyan_puan'])
        self.assertEqual(sonuc['en_iyi'][0]['deger'], 200)
        self.assertEqual(sonuc['en_kotu'][0]['deger'], 50)
        izgara = sonuc['saat_gun']['izgara']
        self.assertEqual(sum(h['adet'] for satir in izgara for h in satir if h), 10)

    def test_olcumsuz_gonderi_puansiz(self):
        g = {'id': 'tiktok:1', 'platform': 'tiktok', 'yayin': iso(days=3), 'son': None, 'onceki': None}
        an.zenginlestir([g], simdi=SIMDI)
        self.assertIsNone(g['puan'])
        self.assertIsNone(g['deger'])


class DayaniklilikTesti(unittest.TestCase):
    def test_toplama_dongusu_hatada_olmez_ve_gunluge_yazar(self):
        import tempfile
        from unittest import mock
        from panel import sunucu
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / 'panel.log'
            with mock.patch.object(sunucu, 'hepsini_topla', side_effect=[RuntimeError('patladi'), SystemExit(3), None]) as m:
                sunucu.toplama_dongusu(None, log, aralik=0, tur=3)
            self.assertEqual(m.call_count, 3)   # üç tur de çalıştı: hata döngüyü öldürmedi
            metin = log.read_text(encoding='utf-8')
            self.assertIn('Otomatik toplama hatası', metin)
            self.assertIn('RuntimeError: patladi', metin)
            self.assertIn('Traceback', metin)
            self.assertRegex(metin, r'^\[\d{4}-\d\d-\d\dT')

    def test_yakalanmamis_hata_kancasi_gunluge_yazar(self):
        import tempfile
        from panel import sunucu
        eski = sys.excepthook, threading.excepthook
        try:
            with tempfile.TemporaryDirectory() as t:
                log = Path(t) / 'panel.log'
                sunucu.hata_kancalari_kur(log)
                try:
                    raise ValueError('ana')
                except ValueError:
                    sys.excepthook(*sys.exc_info())
                th = threading.Thread(target=lambda: 1 / 0, name='deneme')
                th.start()
                th.join()
                metin = log.read_text(encoding='utf-8')
                self.assertIn('ValueError: ana', metin)
                self.assertIn('ZeroDivisionError', metin)
                self.assertIn('deneme', metin)
        finally:
            sys.excepthook, threading.excepthook = eski


class SunucuTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.depo = Depo(':memory:')
        gid = cls.depo.gonderi_yaz('telegram', 7, baslik='Deneme', yayin=iso(days=4), url='https://t.me/kpsstercihi/7')
        cls.depo.olcum_yaz(gid, {'views': 42})
        cls.depo.durum_yaz('tiktok', 'bekliyor', 'anahtar yok')
        cls.uyg = Uygulama(cls.depo, topla=False)
        cls.sunucu = ThreadingHTTPServer(('127.0.0.1', 0), isleyici(cls.uyg))
        cls.adres = f'http://127.0.0.1:{cls.sunucu.server_address[1]}'
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def al(self, yol, **kw):
        with urllib.request.urlopen(urllib.request.Request(self.adres + yol, **kw), timeout=10) as r:
            return r.status, r.read()

    def test_uclar(self):
        _, govde = self.al('/api/gonderiler')
        veri = json.loads(govde)
        self.assertEqual(veri['gonderiler'][0]['deger'], 42)
        durum = json.loads(self.al('/api/durum')[1])
        self.assertFalse(durum['ornek'])
        self.assertEqual(durum['kaynaklar']['tiktok']['durum'], 'bekliyor')
        self.assertIn('kirilimlar', json.loads(self.al('/api/analiz?gun=30')[1]))
        self.assertEqual(len(json.loads(self.al('/api/seri?id=telegram:7')[1])['seri']), 1)

    def test_statik_ve_dizin_disi_engel(self):
        durum, govde = self.al('/')
        self.assertEqual(durum, 200)
        self.assertIn(b'Sosyal Panel', govde)
        with self.assertRaises(urllib.error.HTTPError):
            self.al('/../db.py')

    def test_baska_kokenden_yenile_reddedilir(self):
        with self.assertRaises(urllib.error.HTTPError) as h:
            self.al('/api/yenile', method='POST', data=b'', headers={'Origin': 'https://kotu.example'})
        self.assertEqual(h.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
