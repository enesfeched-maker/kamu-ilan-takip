import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import sosyal_motor as m
import sosyal_tasarim as st
import sosyal_yayinla as y

TR = m.TR


def ilan(no, gun_sonra, saat_once=2, **ek):
    simdi = datetime.now(TR).replace(hour=10, minute=0, second=0, microsecond=0)
    return dict({
        'id': f'test-{no}', 'kurum': f'DENEME {no} BELEDİYE BAŞKANLIĞI', 'kadro': f'{no + 2} Zabıta Memuru',
        'son_tarih': (simdi + timedelta(days=gun_sonra)).date().isoformat(),
        'ilk_gorulme': (simdi - timedelta(hours=saat_once)).isoformat(), 'ogrenim': ['ortaogretim'], 'kpss': 'kpss',
    }, **ek)


class KonuSecimi(unittest.TestCase):
    def setUp(self):
        self.simdi = datetime.now(TR).replace(hour=10, minute=0, second=0, microsecond=0)

    def test_acik_ilanlar_suresi_gecen_ve_duyuru_elenir(self):
        liste = [ilan(1, 3), ilan(2, -1), ilan(3, 3, duyuru_turu='iptal')]
        self.assertEqual([i['id'] for i in m.acik_ilanlar(liste, self.simdi)], ['test-1'])

    def test_son_gun_sabah_one_cikar(self):
        acik = m.acik_ilanlar([ilan(1, 1), ilan(2, 5)], self.simdi)
        aday = m.son_gun_adaylari(acik, self.simdi, 'sabah')
        self.assertEqual(len(aday), 1)
        self.assertEqual(aday[0]['ilanlar'], ['test-1'])
        self.assertIn('YARIN', aday[0]['baslik'].upper())

    def test_yeni_en_az_iki_ilan_ister_ve_yakinda_paylasilani_saymaz(self):
        acik = m.acik_ilanlar([ilan(1, 5), ilan(2, 6), ilan(3, 7, saat_once=50)], self.simdi)
        self.assertEqual(len(m.yeni_adaylari(acik, self.simdi, 'aksam', set())), 1)
        self.assertEqual(m.yeni_adaylari(acik, self.simdi, 'aksam', {'test-1'}), [])

    def test_kategori_uc_ilan_ister(self):
        acik = m.acik_ilanlar([ilan(1, 5), ilan(2, 6), ilan(3, 7)], self.simdi)
        anahtarlar = [a['anahtar'] for a in m.kategori_adaylari(acik, self.simdi)]
        self.assertIn('kategori:lise', anahtarlar)
        self.assertNotIn('kategori:onlisans', anahtarlar)

    def test_yakinda_paylasilan_konu_tekrarlanmaz_ve_trend_one_cikarir(self):
        a = {'tur': 'kategori', 'anahtar': 'kategori:lise', 'puan': 60, 'kelimeler': {'zabıta'}}
        b = {'tur': 'rehber', 'anahtar': 'rehber:x', 'puan': 40, 'kelimeler': {'sağlık', 'personeli'}}
        gecmis = [{'zaman': (self.simdi - timedelta(days=1)).isoformat(), 'anahtar': 'kategori:lise', 'tur': 'kategori'}]
        self.assertEqual(m.konu_sec([a, b], gecmis, self.simdi)['anahtar'], 'rehber:x')
        self.assertEqual(m.konu_sec([a, b], [], self.simdi)['anahtar'], 'kategori:lise')
        secilen = m.konu_sec([a, b], [], self.simdi, ['Sağlık personeli alımı'])
        self.assertEqual((secilen['anahtar'], secilen['trend']), ('rehber:x', 'Sağlık personeli alımı'))

    def test_haber_yalniz_bugun_ve_dun(self):
        cfg = {'sosyal': {'haberler': [{'id': 'h', 'tarih': self.simdi.date().isoformat(), 'manset': ['A', 'B']},
                                       {'id': 'eski', 'tarih': '2020-01-01', 'manset': ['C']}]}}
        self.assertEqual([a['anahtar'] for a in m.haber_adaylari(cfg, self.simdi)], ['haber:h'])

    def test_ilgili_trendler_kelime_basina_bakar(self):
        self.assertEqual(m.ilgili_trendler(['Milan maçı', 'KPSS sonuçları', 'memur maaşı']), ['KPSS sonuçları', 'memur maaşı'])

    def test_metin_siniri(self):
        konu = {'baslik': 'Ç' * 150, 'giris': 'giriş', 'satirlar': [f'• {n}' for n in range(9)],
                'etiketler': ['#a', '#b', '#c'], 'trend': 'KPSS Sonuçları'}
        metin = m.metin_olustur(konu, 'sabah', self.simdi)
        self.assertLessEqual(len(metin['baslik']), 100)
        self.assertTrue(metin['baslik'].endswith('#shorts'))
        self.assertEqual(len(metin['etiketler']), 5)
        self.assertEqual(metin['etiketler'][0], '#kpsssonuçları')
        self.assertIn('…ve 3 ilan daha', metin['aciklama'])

    def test_muzik_sec_son_calinani_tekrarlamaz(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(m.muzik_sec([], 'x', Path(t)))
            for ad in ('a.mp3', 'b.mp3', 'not.txt'):
                (Path(t) / ad).write_bytes(b'0')
            secilen = {m.muzik_sec([{'muzik': 'a.mp3'}], str(n), Path(t)).name for n in range(20)}
        self.assertEqual(secilen, {'b.mp3'})

    def test_aciklamada_soru_var(self):
        konu = {'tur': 'rehber', 'baslik': 'B', 'giris': 'g', 'satirlar': [], 'etiketler': []}
        self.assertIn('👇', m.metin_olustur(konu, 'sabah', self.simdi)['aciklama'])

    def test_rehber_puan_verisinden_uretir(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'puanlar').mkdir()
            kayit = [{'kurum': 'K', 'il': 'ANKARA', 'unvan': f'UNVAN {n}', 'kontenjan': n, 'min': 60 + n}
                     for n in range(1, 15)]
            (Path(t) / 'puanlar' / 'lisans.json').write_text(json.dumps({'donemler': {'2026-1': kayit}}), encoding='utf-8')
            adaylar = m.rehber_adaylari(Path(t))
        self.assertEqual({a['anahtar'] for a in adaylar}, {'rehber:dusuk:lisans:2026-1', 'rehber:cok:lisans:2026-1'})
        dusuk = next(a for a in adaylar if 'dusuk' in a['anahtar'])
        self.assertIn('Unvan 1', dusuk['satirlar'][0])


class Tasarim(unittest.TestCase):
    def test_kare_boyutlari(self):
        simdi = datetime.now(TR)
        kareler = [st.kapak(['BAŞLIK', '3 İLAN'], (1,), 'rozet', liste=['A', 'B', 'C']),
                   st.ilan_karesi(ilan(1, 3), None, 1, 1, simdi),
                   st.tablo_karesi('Tablo', [('Memur', 'Kurum · İl', '70,12')] * 6, 1, 2, 'dipnot'),
                   st.haber_karesi('SON DAKİKA', ['A', 'B'], 'alıntı', 'kaynak'), st.kapanis()]
        self.assertTrue(all(k.size == (st.W, st.H) for k in kareler))

    def test_video_kare_sayisi(self):
        kare = st.kapanis()
        sayi = sum(1 for _ in st.video_kareleri([kare, kare], ilk=1.0, sonraki=0.5))
        self.assertEqual(sayi, st.FPS + st.FPS // 2)

    def test_ses_girdisi_ve_sure(self):
        self.assertAlmostEqual(st.video_suresi(3, ilk=1.0, sonraki=0.5), 2.0)
        girdi, filtre = st.ses_girdisi(None, 5)
        self.assertIn('anullsrc=r=44100:cl=stereo', girdi)
        self.assertEqual(filtre, [])
        girdi, filtre = st.ses_girdisi('parca.mp3', 10)
        self.assertEqual(girdi[:3], ['-stream_loop', '-1', '-i'])
        self.assertIn('afade=t=out:st=9.00', filtre[1])

    def test_kisa_kurum(self):
        self.assertEqual(st.kisa_kurum('ŞİLE BELEDİYE BAŞKANLIĞI'), 'Şile Belediyesi')
        self.assertEqual(st.kisa_kurum('DÜZCE ÜNİVERSİTESİ REKTÖRLÜĞÜ'), 'Düzce Üniversitesi')


class Yayin(unittest.TestCase):
    def klasor(self, t):
        (Path(t) / 'paylasim.json').write_text(json.dumps({'baslik': 'B #shorts', 'aciklama': 'A', 'etiketler': ['#kpss']}),
                                              encoding='utf-8')
        (Path(t) / 'reel.mp4').write_bytes(b'0' * 10)

    def test_anahtar_yoksa_hepsi_atlanir(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {}, clear=True):
            self.klasor(t)
            sonuc, hata = y.yayinla(t)
        self.assertEqual((sonuc, hata), ({}, False))

    def test_bir_platform_hatasi_digerini_durdurmaz(self):
        ortam = {'IG_KULLANICI_ID': '1', 'IG_ERISIM_ANAHTARI': 'x', 'YT_ISTEMCI_KIMLIGI': 'a', 'YT_ISTEMCI_SIRRI': 'b',
                 'YT_YENILEME_ANAHTARI': 'c'}
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, ortam, clear=True), \
                mock.patch.object(y, 'youtube', return_value={'id': 'v1'}), \
                mock.patch.object(y, 'PLATFORMLAR', (('instagram', mock.Mock(side_effect=y.YayinHatasi('bozuk'))),
                                                     ('youtube', lambda v, mt: {'id': 'v1'}))):
            self.klasor(t)
            sonuc, hata = y.yayinla(t)
        self.assertTrue(hata)
        self.assertEqual(sonuc['youtube'], {'id': 'v1'})
        self.assertIn('bozuk', sonuc['instagram']['hata'])

    def test_kapali_platform_atlanir(self):
        ortam = {'YT_ISTEMCI_KIMLIGI': 'a', 'YT_ISTEMCI_SIRRI': 'b', 'YT_YENILEME_ANAHTARI': 'c', 'SOSYAL_KAPALI': 'youtube'}
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, ortam, clear=True), \
                mock.patch.object(y, '_istek', side_effect=AssertionError('istek atılmamalı')):
            self.klasor(t)
            self.assertEqual(y.yayinla(t), ({}, False))

    def test_instagram_akisi(self):
        cagrilar = []

        def sahte(url, **kw):
            cagrilar.append(url)
            if url.endswith('/media'):
                return {'id': 'k1'}
            if 'status_code' in url:
                return {'status_code': 'FINISHED'}
            if url.endswith('/media_publish'):
                return {'id': 'p1'}
            return {}

        with tempfile.TemporaryDirectory() as t, mock.patch.object(y, '_istek', side_effect=sahte), \
                mock.patch.dict(os.environ, {'VIDEO_URL': ''}):
            self.klasor(t)
            sonuc = y.instagram(Path(t) / 'reel.mp4', {'aciklama': 'A'}, ortam=('42', 'anahtar'))
        self.assertEqual(sonuc, {'id': 'p1'})
        self.assertTrue(any('rupload.facebook.com' in c and c.endswith('/k1') for c in cagrilar))

    def test_instagram_video_adresiyle(self):
        alanlar, cagrilar = {}, []

        def sahte(url, veri=None, **kw):
            cagrilar.append(url)
            if url.endswith('/media'):
                alanlar.update(veri)
                return {'id': 'k1'}
            return {'status_code': 'FINISHED'} if 'status_code' in url else {'id': 'p1'}

        with tempfile.TemporaryDirectory() as t, mock.patch.object(y, '_istek', side_effect=sahte), \
                mock.patch.dict(os.environ, {'VIDEO_URL': 'https://ornek/reel.mp4'}):
            self.klasor(t)
            self.assertEqual(y.instagram(Path(t) / 'reel.mp4', {'aciklama': 'A'}, ortam=('42', 'x')), {'id': 'p1'})
        self.assertEqual(alanlar['video_url'], 'https://ornek/reel.mp4')
        self.assertFalse(any('rupload' in c for c in cagrilar))

    def test_youtube_yanlis_kanala_yuklemez(self):
        def sahte(url, **kw):
            if 'oauth2' in url:
                return {'access_token': 'e'}
            if 'channels' in url:
                return {'items': [{'snippet': {'title': 'Glow Haven'}}]}
            raise AssertionError('yükleme denenmemeliydi: ' + url)

        with tempfile.TemporaryDirectory() as t, mock.patch.object(y, '_istek', side_effect=sahte), \
                mock.patch.dict(os.environ, {'YT_KANAL': 'Kpss Tercihi'}):
            self.klasor(t)
            with self.assertRaisesRegex(y.YayinHatasi, 'Glow Haven'):
                y.youtube(Path(t) / 'reel.mp4', {'baslik': 'B', 'aciklama': 'A'}, ortam=('a', 'b', 'c'))

    def test_tiktok_taslak_gelen_kutusuna(self):
        def sahte(url, **kw):
            if 'oauth/token' in url:
                return {'access_token': 'e', 'refresh_token': 'r'}
            if 'inbox/video/init' in url:
                return {'data': {'upload_url': 'https://yukle', 'publish_id': 'pid'}}
            return {}

        with tempfile.TemporaryDirectory() as t, mock.patch.object(y, '_istek', side_effect=sahte):
            self.klasor(t)
            sonuc = y.tiktok(Path(t) / 'reel.mp4', {'aciklama': 'A'}, ortam=('k', 's', 'r'), mod='taslak')
        self.assertEqual(sonuc, {'id': 'pid', 'gorunurluk': 'taslak'})


if __name__ == '__main__':
    unittest.main()
