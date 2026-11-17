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


def _fb_olcutler(*adlar):
    gercek = {
        'fb_reels_total_plays': 410, 'blue_reels_play_count': 380, 'fb_reels_replay_count': 30,
        'post_impressions_unique': 300, 'post_video_avg_time_watched': 5100, 'post_video_view_time': 2090000,
        'post_video_likes_by_reaction_type': {'like': 10, 'love': 2}, 'post_video_social_actions': {'COMMENT': 2, 'SHARE': 3},
    }
    return {'data': [{'name': a, 'period': 'lifetime', 'values': [{'value': gercek[a]}], 'id': f'1/video_insights/{a}/lifetime'}
                     for a in adlar if a in gercek]}


class FacebookToplamaTesti(unittest.TestCase):
    ORTAM = ('123', 'GIZLI')

    def test_ayristirma_gercek_bicimli_yanit(self):
        sonuc = t.fb_insights_ayristir(_fb_olcutler(*t.FB_OLCUTLER))
        self.assertEqual(sonuc, {'views': 410, 'reach': 300, 'avg_watch_ms': 5100, 'total_watch_ms': 2090000,
                                 'likes': 12, 'comments': 2, 'shares': 3})
        # toplam oynatma yoksa yinelemesiz oynatmaya düşer
        self.assertEqual(t.fb_insights_ayristir(_fb_olcutler('blue_reels_play_count'))['views'], 380)
        self.assertEqual(t.fb_insights_ayristir({'data': []}), {})

    def test_liste_sayfalama_ve_insights(self):
        cagrilar = []

        def istek(url, **kw):
            cagrilar.append((url, kw))
            if '/video_reels?' in url:
                return {'data': [{'id': '11', 'description': 'a', 'created_time': '2026-11-10T09:31:00+0000',
                                  'permalink_url': 'https://www.facebook.com/reel/11'}],
                        'paging': {'next': 'https://graph.facebook.com/v27.0/next'}}
            if url.endswith('/next'):
                return {'data': [{'id': '22'}]}
            return _fb_olcutler(*url.split('metric=')[1].split(','))
        sonuc = t.facebook(self.ORTAM, istek)
        self.assertEqual(sonuc['durum'], 'hazir')
        self.assertEqual([r['id'] for r in sonuc['reels']], ['11', '22'])
        self.assertEqual(sonuc['reels'][0]['insights']['views'], 410)
        self.assertEqual(sonuc['reels'][0]['permalink_url'], 'https://www.facebook.com/reel/11')
        self.assertIn('2 reel', sonuc['aciklama'])
        self.assertTrue(all(kw['basliklar']['Authorization'] == 'Bearer GIZLI' for _, kw in cagrilar))
        self.assertFalse(any('GIZLI' in u for u, _ in cagrilar))   # anahtar adreste değil üstbilgide

    def test_desteklenmeyen_olcut_atlanir_kalanlar_okunur(self):
        def istek(url, **kw):
            if '/video_reels?' in url:
                return {'data': [{'id': '11'}]}
            adlar = url.split('metric=')[1].split(',')
            if len(adlar) > 1 or adlar[0] == 'post_impressions_unique':
                raise YayinHatasi('HTTP 400: (#100) metric not supported')
            return _fb_olcutler(*adlar)
        sonuc = t.facebook(self.ORTAM, istek)
        self.assertEqual(sonuc['durum'], 'hazir')
        ins = sonuc['reels'][0]['insights']
        self.assertEqual(ins['views'], 410)
        self.assertNotIn('reach', ins)
        self.assertIn('post_impressions_unique', sonuc['aciklama'])

    def test_hic_olcut_okunamazsa_reel_kalir_calisma_cokmez(self):
        def istek(url, **kw):
            if '/video_reels?' in url:
                return {'data': [{'id': '11'}, {'id': '12'}]}
            raise YayinHatasi('HTTP 403: (#10) permission read_insights')
        sonuc = t.facebook(self.ORTAM, istek)
        self.assertEqual(sonuc['durum'], 'hazir')
        self.assertEqual(len(sonuc['reels']), 2)
        self.assertIn('insights_hata', sonuc['reels'][0])
        self.assertIn('2 reelde ölçüm okunamadı', sonuc['aciklama'])

    def test_liste_hatasi_ve_anahtar_yoksa(self):
        def istek(url, **kw):
            raise YayinHatasi('HTTP 400: access_token=GIZLI bozuk')
        sonuc = t.facebook(self.ORTAM, istek)
        self.assertEqual(sonuc['durum'], 'hata')
        self.assertNotIn('GIZLI', sonuc['aciklama'])
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(t.facebook()['durum'], 'bekliyor')


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

    def test_metrics_istenir_ve_sema_tutmazsa_metriksiz_sorguya_dusulur(self):
        def sorgu(q):
            if 'organizations' in q:
                return {'account': {'organizations': [{'id': 'org'}]}}
            if 'channels' in q:
                return {'channels': []}
            if 'metrics' in q:
                raise YayinHatasi('Buffer: Cannot query field "metrics" on type "Post"')
            return {'posts': {'edges': [{'node': {'id': 'p1', 'externalLink': 'https://tiktok.com/x'}}]}}
        sonuc = t.buffer('anahtar', sorgu=sorgu)
        self.assertEqual(sonuc['durum'], 'hazir')
        self.assertEqual(len(sonuc['gonderiler']), 1)
        self.assertIn('metrics okunamadı', sonuc['aciklama'])
        self.assertIn('metrics { name type unit value }', t.BUFFER_GONDERI % '"o"')
        self.assertNotIn('metrics', t.BUFFER_GONDERI_DUZ)

        def tamam(q):
            if 'organizations' in q:
                return {'account': {'organizations': [{'id': 'org'}]}}
            if 'channels' in q:
                return {'channels': []}
            return {'posts': {'edges': [{'node': {'id': 'p1', 'channelService': 'tiktok', 'metricsUpdatedAt': '2026-11-14T00:00:00Z',
                                                  'metrics': [{'name': 'Views', 'type': 'views', 'unit': 'count', 'value': 5}]}}]}}
        sonuc = t.buffer('anahtar', sorgu=tamam)
        self.assertEqual(sonuc['gonderiler'][0]['metrics'][0]['value'], 5)
        self.assertNotIn('metrics okunamadı', sonuc['aciklama'])

    def test_buffer_yalniz_izinli_calismada(self):
        with mock.patch.dict(os.environ, {'PANEL_BUFFER': 'false'}, clear=True):
            self.assertEqual(t.topla()['buffer']['durum'], 'atlandi')


if __name__ == '__main__':
    unittest.main()
