"""'İnsanlar ne soruyor' testleri: toplayıcı (sahte HTTP), upsert, çözümleme, uç. Ağ yok; tarihler göreli."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from panel import asistan, sorular  # noqa: E402
from panel import kaynaklar as k  # noqa: E402
from panel.db import Depo  # noqa: E402
from panel.sunucu import Uygulama, isleyici  # noqa: E402

SIMDI = datetime.now(timezone.utc).replace(microsecond=0)


def iso(**fark):
    return (SIMDI - timedelta(**fark)).isoformat()


def kayit(kid, soru='Zabıta ilanı var mı?', zaman=None, **alan):
    satir = {'id': kid, 'zaman': zaman or iso(hours=1), 'kanal': 'site', 'soru': soru, 'tur': 'ilan', 'metin': 'cevap',
             'ilan_sayisi': 2, 'baglantilar': ['https://kpsstercihi.com/'], 'sayfa': '/', 'geri': None, 'durum': None, 'meta': None}
    satir.update(alan)
    return satir


class SahteUc:
    """/asistan/kayitlar taklidi: sonra/limit'e göre sıralı sayfa döner, istekleri kaydeder."""

    def __init__(self, satirlar):
        self.satirlar = sorted(satirlar, key=lambda s: s['id'])
        self.istekler = []

    def __call__(self, url, basliklar=None, **kw):
        if 'bilgi.json' in url:
            return {'meslekler': [{'ad': 'Zabıta memuru', 'kelimeler': ['zabita'], 'u': 'x'}]}
        self.istekler.append((url, dict(basliklar or {})))
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        sonra, limit = int(q['sonra']), int(q['limit'])
        sayfa = [dict(s) for s in self.satirlar if s['id'] > sonra][:limit]
        return {'kayitlar': sayfa, 'son': sayfa[-1]['id'] if sayfa else sonra}


class UpsertTesti(unittest.TestCase):
    def setUp(self):
        self.d = Depo(':memory:')

    def test_ekler_gunceller_ayni_kalana_dokunmaz(self):
        self.assertEqual(self.d.asistan_yaz([kayit(1), kayit(2, meta={'kullanici': 'a'}, kanal='instagram')]), (2, 0))
        self.assertEqual(self.d.asistan_yaz([kayit(1), kayit(2, meta={'kullanici': 'a'}, kanal='instagram')]), (0, 0))
        y, dg = self.d.asistan_yaz([kayit(1, geri=1), kayit(2, kanal='instagram', durum='yanitlandi',
                                                              meta={'kullanici': 'a', 'gonderilen': 'Merhaba'})])
        self.assertEqual((y, dg), (0, 2))
        satirlar = {r['id']: r for r in self.d.asistan_kayitlari()}
        self.assertEqual(satirlar[1]['geri'], 1)
        self.assertEqual(satirlar[2]['durum'], 'yanitlandi')
        self.assertEqual(satirlar[2]['gonderilen'], 'Merhaba')
        self.assertEqual(satirlar[2]['meta']['kullanici'], 'a')
        self.assertEqual(satirlar[1]['baglantilar'], ['https://kpsstercihi.com/'])

    def test_metin_json_ve_bozuk_satir(self):
        self.d.asistan_yaz([kayit(5, baglantilar='["https://a"]', meta='{"kullanici": "b"}'), {'soru': 'id yok'}])
        r = self.d.asistan_kayitlari()
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]['baglantilar'], r[0]['meta']), (['https://a'], {'kullanici': 'b'}))


class ToplayiciTesti(unittest.TestCase):
    def setUp(self):
        self.d = Depo(':memory:')

    def test_sayfalar_bosalana_kadar_ve_anahtar_basligi(self):
        uc = SahteUc([kayit(i) for i in range(1, 2501)])
        yeni, degisen, istek = asistan.kayitlari_cek(self.d, 'gizli', getir_json=uc, simdi=SIMDI)
        self.assertEqual((yeni, degisen), (2500, 0))
        self.assertEqual(istek, 4)   # 1000 + 1000 + 500 + boş
        self.assertTrue(all(b['X-Asistan-Anahtar'] == 'gizli' for _, b in uc.istekler))
        self.assertIn('sonra=0&limit=1000', uc.istekler[0][0])
        self.assertTrue(uc.istekler[0][0].startswith('https://bildirim.kpsstercihi.com/asistan/kayitlar?'))

    def test_son_iki_gun_yeniden_cekilir_ve_guncellenir(self):
        eski = [kayit(1, zaman=iso(days=5)), kayit(2, zaman=iso(days=3))]
        yakin = [kayit(3, zaman=iso(hours=30)), kayit(4, zaman=iso(hours=2))]
        self.d.asistan_yaz(eski + yakin)
        yakin[0]['geri'] = -1   # sonradan gelen geri bildirim
        uc = SahteUc(eski + yakin + [kayit(5, zaman=iso(minutes=10))])
        yeni, degisen, _ = asistan.kayitlari_cek(self.d, 'x', getir_json=uc, simdi=SIMDI)
        self.assertIn('sonra=2&', uc.istekler[0][0])   # 48 saat içindeki ilk kayıt (3) öncesinden
        self.assertEqual((yeni, degisen), (1, 1))
        self.assertEqual({r['id']: r['geri'] for r in self.d.asistan_kayitlari()}[3], -1)

    def test_anahtar_dosyasi_yoksa_sessizce_atlar(self):
        with tempfile.TemporaryDirectory() as t:
            yol = Path(t) / 'yok.txt'
            cagri = mock.Mock()
            self.assertIsNone(asistan.topla(self.d, getir_json=cagri, yol=yol))
            cagri.assert_not_called()
            durum = {x['kaynak']: x for x in self.d.durumlar()}['asistan']
            self.assertEqual(durum['durum'], 'bekliyor')
            yol.write_text('\n  anahtar123  \n', encoding='utf-8')
            self.assertEqual(asistan.anahtar_oku(yol), 'anahtar123')

    def test_topla_durum_ve_meslek_onbellegi(self):
        uc = SahteUc([kayit(1), kayit(2)])
        self.assertEqual(asistan.topla(self.d, anahtar='x', getir_json=uc, simdi=SIMDI), (2, 0))
        self.assertEqual(self.d.ayar('asistan_meslekler')['liste'][0]['ad'], 'Zabıta memuru')
        self.assertEqual({x['kaynak']: x for x in self.d.durumlar()}['asistan']['durum'], 'hazir')

    def test_http_hatasi_kaynak_hatasi_olarak_yukselir(self):
        def bozuk(url, **kw):
            raise k.KaynakHatasi('HTTP 401 (bildirim.kpsstercihi.com)')
        with self.assertRaises(k.KaynakHatasi):
            asistan.kayitlari_cek(self.d, 'x', getir_json=bozuk, simdi=SIMDI)


class CozumlemeTesti(unittest.TestCase):
    def test_katlama_kok_ve_grup_anahtari(self):
        self.assertEqual(sorular.katla('IŞIK Çağrı'), 'isik cagri')
        self.assertEqual(sorular.kok('ilanlari'), 'ilan')
        self.assertEqual(sorular.grup_anahtari('Zabıta ilanı var mı?'), sorular.grup_anahtari('zabita ilani varmi'))
        self.assertNotEqual(sorular.grup_anahtari('Zabıta ilanı'), sorular.grup_anahtari('Hemşire ilanı'))

    def test_il_ve_meslek_bulma(self):
        self.assertEqual(sorular.il_bul("istanbul'da izmirden muş"), ['İstanbul', 'İzmir', 'Muş'])
        self.assertEqual(sorular.il_bul('vana gidecek'), [])   # kısa il + ünlü eki sayılmaz
        mes = [{'ad': 'Memur', 'kelimeler': ['memur']}, {'ad': 'Zabıta memuru', 'kelimeler': ['zabita memuru', 'zabita']}]
        self.assertEqual(sorular.meslek_bul('ankara zabita memuru alimi', mes), 'Zabıta memuru')
        self.assertEqual(sorular.meslek_bul('memurluk ilani', mes), 'Memur')

    def test_analiz(self):
        kayitlar = [
            kayit(1, 'Zabıta ilanı var mı?', iso(days=1), geri=1),
            kayit(2, 'zabita ilani varmi', iso(days=2), geri=-1),
            kayit(3, 'Van itfaiye alımı', iso(days=3), ilan_sayisi=0),
            kayit(4, 'Mülakat ne zaman açıklanır?', iso(days=1), tur='bilinmiyor'),
            kayit(5, 'mülakat ne zaman açıklanır', iso(days=2), tur='bilinmiyor', kanal='instagram', durum='atlandi'),
            kayit(6, 'Yaş sınırı kaç', iso(days=4), tur='bilinmiyor', kanal='instagram', durum='yanitlandi'),
            kayit(7, 'Ankara zabıta', iso(days=20)),
            kayit(8, 'Eski soru', iso(days=50)),
        ]
        a = sorular.analiz([dict(x) for x in kayitlar], gun=30, simdi=SIMDI)
        kpi = a['kpi']
        self.assertEqual((kpi['son7'], kpi['son30'], a['donem_adet']), (6, 7, 7))
        self.assertEqual((kpi['cevapsiz'], kpi['cevapsiz_orani']), (3, round(3 / 7, 4)))
        self.assertEqual((kpi['geri_evet'], kpi['geri_hayir'], kpi['faydali_orani']), (1, 1, 0.5))
        self.assertEqual((kpi['ig_toplam'], kpi['ig_yanitlandi'], kpi['ig_birakilan']), (2, 1, 1))
        self.assertEqual(kpi['ilansiz'], 1)
        c = a['cevapsiz_sorular']
        self.assertEqual((c[0]['adet'], c[0]['kanallar']), (2, {'site': 1, 'instagram': 1}))
        self.assertEqual(len(c), 2)
        self.assertEqual([g['metin'] for g in a['ilansiz_sorular']], ['Van itfaiye alımı'])
        self.assertEqual(a['meslekler'][0], {'ad': 'Zabıta memuru', 'adet': 3, 'cevapsiz': 0, 'ilansiz': 0})
        self.assertIn({'ad': 'Van', 'adet': 1, 'cevapsiz': 0, 'ilansiz': 1}, a['iller'])
        kelimeler = {w['kelime']: w for w in a['kelimeler']}
        self.assertEqual(kelimeler['zabıta']['adet'], 3)              # zabıta + zabita tek kelime, asıl yazılışla
        self.assertIn('zabita', kelimeler['zabıta']['bicimler'])
        self.assertEqual(kelimeler['mülakat']['adet'], 2)
        self.assertFalse({'ilan', 'ilanı', 'var', 'mı'} & set(kelimeler))
        self.assertEqual(len(a['gunluk']), 30)
        self.assertEqual(sum(g['site'] + g['instagram'] for g in a['gunluk']), 7)
        self.assertEqual(sorular.analiz([dict(x) for x in kayitlar], gun=None, simdi=SIMDI)['donem_adet'], 8)

    def test_bos_veri(self):
        a = sorular.analiz([], gun=7, simdi=SIMDI)
        self.assertEqual((a['toplam'], a['kpi']['cevapsiz_orani'], a['kpi']['faydali_orani']), (0, None, None))
        self.assertEqual(len(a['gunluk']), 7)


class SorularUcuTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.depo = Depo(':memory:')
        cls.depo.asistan_yaz([kayit(1, '<b>kalın</b> zabıta'), kayit(2, 'Eski', iso(days=40))])
        cls.uyg = Uygulama(cls.depo, topla=False)
        cls.sunucu = ThreadingHTTPServer(('127.0.0.1', 0), isleyici(cls.uyg))
        cls.adres = f'http://127.0.0.1:{cls.sunucu.server_address[1]}'
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()
        cls.sunucu.server_close()
        cls.depo.kapat()

    def test_uc_doneme_gore_kayit_ve_cozumleme_doner(self):
        with urllib.request.urlopen(self.adres + '/api/sorular?gun=30', timeout=10) as r:
            v = json.loads(r.read())
        self.assertEqual([x['id'] for x in v['kayitlar']], [1])
        self.assertEqual(v['kayitlar'][0]['soru'], '<b>kalın</b> zabıta')   # ham metin; arayüz kaçırır
        self.assertEqual(v['kayitlar'][0]['meslek'], 'Zabıta memuru')
        self.assertEqual(v['toplam'], 2)
        self.assertIn('anahtar_var', v)
        with urllib.request.urlopen(self.adres + '/api/sorular?gun=', timeout=10) as r:
            self.assertEqual(len(json.loads(r.read())['kayitlar']), 2)


if __name__ == '__main__':
    unittest.main()
