import os
import unittest
from unittest import mock

import sosyal_panel_topla as t
from sosyal_yayinla import YayinHatasi


class InstagramToplamaTesti(unittest.TestCase):
    def test_sayfalama_ve_dar_olcut_kumesine_dusme(self):
        cagrilar = []

        def istek(url, **kw):
            cagrilar.append(url)
            if '/media?' in url:
                return {'data': [{'id': '1', 'media_type': 'VIDEO', 'media_product_type': 'REELS', 'permalink': 'p1'}],
                        'paging': {'next': 'https://graph.instagram.com/next?access_token=x'}}
            if 'next?' in url:
                return {'data': [{'id': '2', 'media_type': 'IMAGE', 'media_url': 'm2', 'permalink': 'p2'}]}
            if '/1/insights' in url and 'ig_reels_avg_watch_time' in url:
                raise YayinHatasi('HTTP 400: metric not supported access_token=GIZLI')
            if '/1/insights' in url:
                return {'data': [{'name': 'views', 'values': [{'value': 120}]}]}
            if '/2/insights' in url:
                raise YayinHatasi('HTTP 400: no permission access_token=GIZLI')
            raise AssertionError(url)

        sonuc = t.instagram(ortam=('ig', 'GIZLI'), istek=istek)
        self.assertEqual(sonuc['durum'], 'hazir')
        m1, m2 = sonuc['medyalar']
        self.assertEqual(m1['insights'], {'views': 120})
        self.assertEqual(m2['thumbnail_url'], 'm2')
        self.assertNotIn('GIZLI', m2['insights_hata'])
        self.assertIn('1 medyada ölçüm okunamadı', sonuc['aciklama'])

    def test_anahtar_yoksa_bekliyor(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(t.instagram()['durum'], 'bekliyor')
            self.assertEqual(t.youtube()['durum'], 'bekliyor')
            self.assertEqual(t.buffer()['durum'], 'bekliyor')

    def test_medya_listesi_hatasi_anahtari_sizdirmaz(self):
        def istek(url, **kw):
            raise YayinHatasi(f'HTTP 500 {url}')
        sonuc = t.instagram(ortam=('ig', 'GIZLI'), istek=istek)
        self.assertEqual(sonuc['durum'], 'hata')
        self.assertNotIn('GIZLI', sonuc['aciklama'])


class BufferToplamaTesti(unittest.TestCase):
    def test_gonderiler_ve_sema_kaydi(self):
        def sorgu(q):
            if 'organizations' in q:
                return {'account': {'organizations': [{'id': 'org'}]}}
            if 'channels' in q:
                return {'channels': [{'id': 'c1', 'service': 'tiktok'}]}
            return {'posts': {'edges': [{'node': {'id': 'p1', 'externalLink': 'https://tiktok.com/x', 'text': 'a' * 900}}]}}
        sonuc = t.buffer('anahtar', sorgu=sorgu)
        self.assertEqual(sonuc['durum'], 'hazir')
        self.assertEqual(len(sonuc['gonderiler'][0]['text']), 600)

        def bozuk(q):
            if '__type' in q:
                return {'__type': {'fields': [{'name': 'id'}]}}
            raise YayinHatasi('Buffer: Cannot query field "externalLink"')
        sonuc = t.buffer('anahtar', sorgu=bozuk)
        self.assertEqual(sonuc['durum'], 'hata')
        self.assertIn('sema', sonuc)

    def test_buffer_yalniz_izinli_calismada(self):
        with mock.patch.dict(os.environ, {'PANEL_BUFFER': 'false'}, clear=True):
            self.assertEqual(t.topla()['buffer']['durum'], 'atlandi')


if __name__ == '__main__':
    unittest.main()
