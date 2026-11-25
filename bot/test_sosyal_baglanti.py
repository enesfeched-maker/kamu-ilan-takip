import os
import tempfile
import unittest
from unittest import mock

import sosyal_baglanti as b
import sosyal_yayinla as y

METIN = {'aciklama': 'Başlık satırı\n\nİçerik\n\n#kpss #memur', 'baslik': 'B', 'tur': 'sabah', 'vakit': 'aksam',
         'zaman': '2026-11-25T18:00:00', 'soru': 'Hangi kadro?'}


class UtmTesti(unittest.TestCase):
    def test_temel(self):
        self.assertEqual(b.utm('youtube', 'sabah'),
                         'https://kpsstercihi.com/?utm_source=youtube&utm_medium=social&utm_campaign=sabah')

    def test_sorgu_ve_parca(self):
        u = b.utm('facebook', 'a b', 'x', url='https://s.com/p?k=1#bolum')
        self.assertEqual(u, 'https://s.com/p?k=1&utm_source=facebook&utm_medium=social&utm_campaign=a+b&utm_content=x#bolum')

    def test_adlar(self):
        self.assertEqual(b.icerik_adi(METIN), '20261125-aksam')
        self.assertIsNone(b.icerik_adi({}))
        self.assertIsNone(b.icerik_adi({'zaman': 'bozuk', 'vakit': 'x'}))
        self.assertEqual(b.kampanya_adi({}), 'paylasim')
        self.assertEqual(b.kampanya_adi(METIN), 'sabah')


class BioTesti(unittest.TestCase):
    def test_bio_sayfalari(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            b.bio_sayfalari_yaz(d)
            html = (Path(d) / 'ig' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('noindex', html)
            self.assertIn('url=https://kpsstercihi.com/?utm_source=instagram&amp;utm_medium=bio&amp;utm_campaign=profil', html)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ['fb', 'ig', 'tt', 'yt'])


class AciklamaTesti(unittest.TestCase):
    def test_etiketten_once(self):
        a = b.aciklama_baglantili(METIN, 'facebook')
        self.assertIn('🔗 Tüm ilanlar: https://kpsstercihi.com/?utm_source=facebook', a)
        self.assertIn('utm_content=20261125-aksam', a)
        self.assertIn('📢 Anlık bildirim: https://t.me/kpsstercihi', a)
        self.assertTrue(a.endswith('\n\n#kpss #memur'))
        self.assertLess(a.index('🔗'), a.index('#kpss'))

    def test_etiketsiz_sona(self):
        a = b.aciklama_baglantili({'aciklama': 'Merhaba', 'tur': 'x'}, 'facebook')
        self.assertTrue(a.startswith('Merhaba\n\n🔗'))
        self.assertTrue(a.endswith('https://t.me/kpsstercihi'))

    def test_ig_tiktok_degismez(self):
        for p in ('instagram', 'tiktok'):
            self.assertEqual(b.aciklama_baglantili(METIN, p), METIN['aciklama'])

    def test_tekrarsiz(self):
        bir = b.aciklama_baglantili(METIN, 'facebook')
        self.assertEqual(b.aciklama_baglantili(dict(METIN, aciklama=bir), 'facebook'), bir)


class IlkYorumTesti(unittest.TestCase):
    def test_platformlar(self):
        fb = b.ilk_yorum(METIN, 'facebook')
        self.assertIn('utm_content=20261125-aksam-yorum', fb)
        self.assertIn("Yeni ilanlar ilk Telegram'da: https://t.me/kpsstercihi", fb)
        self.assertNotIn('http', b.ilk_yorum(METIN, 'youtube'))   # Shorts'ta bağlantı tıklanmaz
        self.assertIn('utm_source=facebook', b.ilk_yorum(METIN, 'facebook'))
        ig = b.ilk_yorum(METIN, 'instagram')
        self.assertIn('profildeki bağlantıda', ig)
        self.assertIn('@kpsstercihi', ig)
        self.assertTrue(ig.endswith('Hangi kadro?'))
        self.assertNotIn('http', ig)
        self.assertNotIn('Hangi', b.ilk_yorum({'aciklama': 'x'}, 'instagram'))
        self.assertIsNone(b.ilk_yorum(METIN, 'tiktok'))


def _cagri_sahte(cagrilar, yorum_hatasi):
    def sahte(url, **kw):
        cagrilar.append((url, kw))
        if '/comments' in url or 'commentThreads' in url:
            if yorum_hatasi:
                raise y.YayinHatasi('HTTP 403: yetersiz kapsam')
            return {'id': 'y1'}
        if 'media_publish' in url:
            return {'id': 'M1'}
        if url.endswith('/media'):
            return {'id': 'K1'}
        if 'status_code' in url:
            return {'status_code': 'FINISHED'}
        if 'oauth2.googleapis.com/token' in url:
            return {'access_token': 'ERISIM'}
        if 'uploadType=resumable' in url:
            return (mock.Mock(headers={'Location': 'https://yukle'}), b'')
        if url == 'https://yukle':
            return {'id': 'V1', 'snippet': {'channelTitle': 'K'}, 'status': {'privacyStatus': 'public'}}
        if url.endswith('?fields=id'):
            return {'id': '123'}
        if url.endswith('/video_reels') and kw.get('veri', {}).get('upload_phase') == 'start':
            return {'video_id': 'F1', 'upload_url': 'https://rupload.facebook.com/x'}
        if url.startswith('https://rupload'):
            return {'success': True}
        if url.endswith('/video_reels'):
            return {'success': True}
        if 'fields=status' in url:
            return {'status': {'publishing_phase': {'status': 'complete'}}}
        return {}
    return sahte


class YayinYorumTesti(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.mkdtemp()
        self.video = os.path.join(self.klasor, 'reel.mp4')
        open(self.video, 'wb').write(b'x')
        ortam = {'VIDEO_URL': 'https://v/reel.mp4', 'FB_SAYFA_ID': '123', 'FB_ERISIM_ANAHTARI': 'FBGIZLI'}
        p = mock.patch.dict(os.environ, ortam)
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop('SOSYAL_ILK_YORUM', None)
        os.environ.pop('YT_KANAL', None)
        mock.patch('sosyal_yayinla.time.sleep').start()
        self.addCleanup(mock.patch.stopall)

    def _calistir(self, ad, hata):
        cagrilar = []
        sahte = _cagri_sahte(cagrilar, hata)
        with mock.patch.object(y, '_istek', sahte):
            if ad == 'instagram':
                s = y.instagram(self.video, METIN, ('IG', 'TOKEN'))
            elif ad == 'youtube':
                s = y.youtube(self.video, METIN, ('c', 's', 'r'))
            else:
                s = y.facebook(self.video, METIN)
        return s, cagrilar

    def test_yorum_hatasi_yayini_bozmaz(self):
        for ad in ('instagram', 'youtube', 'facebook'):
            s, _ = self._calistir(ad, True)
            self.assertTrue(s['id'], ad)
            self.assertTrue(s['yorum'].startswith('hata: '), ad)
            self.assertLessEqual(len(s['yorum']), 156)

    def test_yorum_tamam(self):
        for ad in ('instagram', 'youtube', 'facebook'):
            s, c = self._calistir(ad, False)
            self.assertEqual(s['yorum'], 'tamam', ad)
            yorumlar = [u for u, _ in c if '/comments' in u or 'commentThreads' in u]
            self.assertEqual(len(yorumlar), 1, ad)

    def test_youtube_aciklamasi_baglantili(self):
        _, c = self._calistir('youtube', False)
        govde = [kw['json_veri'] for u, kw in c if 'uploadType=resumable' in u][0]
        self.assertEqual(govde['snippet']['description'], METIN['aciklama'])   # Shorts'ta bağlantı tıklanmaz

    def test_kapali_yorum_atlanir(self):
        with mock.patch.dict(os.environ, {'SOSYAL_ILK_YORUM': 'kapali'}):
            for ad in ('instagram', 'youtube', 'facebook'):
                s, c = self._calistir(ad, False)
                self.assertNotIn('yorum', s, ad)
                self.assertFalse([u for u, _ in c if '/comments' in u or 'commentThreads' in u], ad)


if __name__ == '__main__':
    unittest.main()