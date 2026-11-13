import time
import unittest
from unittest import mock

import facebook_kurulum as f


class FacebookKurulum(unittest.TestCase):
    def debug(self, **degerler):
        return {'data': dict(is_valid=True, app_id='1134321295736637', expires_at=time.time() + 60 * 86400,
                             scopes=['pages_manage_posts', 'pages_read_engagement', 'pages_show_list'], **degerler)}

    def test_kisa_omurlu_anahtar_kaydedilmez(self):
        veri = self.debug()
        veri['data']['expires_at'] = time.time() + 3600
        with mock.patch.object(f, 'graph', return_value=veri), mock.patch.object(f.subprocess, 'run') as gh:
            with self.assertRaisesRegex(ValueError, 'kısa ömürlü'):
                f.kaydet('test-user')
        gh.assert_not_called()

    def test_baska_uygulamanin_anahtari_reddedilir(self):
        veri = self.debug()
        veri['data']['app_id'] = '123'
        with mock.patch.object(f, 'graph', return_value=veri), mock.patch.object(f.subprocess, 'run') as gh:
            with self.assertRaises(ValueError):
                f.kaydet('test-user')
        gh.assert_not_called()

    def test_yayin_izni_olmayan_anahtar_kaydedilmez(self):
        veri = self.debug()
        veri['data']['scopes'] = ['pages_show_list']
        with mock.patch.object(f, 'graph', return_value=veri), mock.patch.object(f.subprocess, 'run') as gh:
            with self.assertRaisesRegex(ValueError, 'izinleri eksik'):
                f.kaydet('test-user')
        gh.assert_not_called()

    def test_sayfa_kimligi_uyusmazsa_kaydedilmez(self):
        cevaplar = [self.debug(), {'id': f.SAYFA, 'name': 'KPSS Tercihi', 'access_token': 'test-page'}, {'id': '999'}]
        with mock.patch.object(f, 'graph', side_effect=cevaplar), mock.patch.object(f.subprocess, 'run') as gh:
            with self.assertRaisesRegex(ValueError, 'kimliği uyuşmuyor'):
                f.kaydet('test-user')
        gh.assert_not_called()

    def test_user_token_yerine_sayfa_tokeni_secret_olarak_yazilir(self):
        cevaplar = [self.debug(), {'id': f.SAYFA, 'name': 'KPSS Tercihi', 'access_token': 'test-page'}, {'id': f.SAYFA}]
        with mock.patch.object(f, 'graph', side_effect=cevaplar), \
                mock.patch.object(f.subprocess, 'run', return_value=mock.Mock(returncode=0)) as gh:
            self.assertEqual(f.kaydet('test-user'), 'test-page')
        self.assertEqual(gh.call_args_list[0].kwargs['input'], 'test-page')
        self.assertNotIn('test-page', ' '.join(gh.call_args_list[0].args[0]))
        self.assertIn(f.SAYFA, gh.call_args_list[1].args[0])


if __name__ == '__main__':
    unittest.main()
