import io,json,unittest,urllib.error
from unittest.mock import patch
import github_yayin


def hata(kod):
    return urllib.error.HTTPError('https://api.github.com/x',kod,'hata',{},io.BytesIO(b''))


class Yanit(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*_):return False


class GithubYayinTest(unittest.TestCase):
    def test_500_tekrar_denenir(self):
        with patch('github_yayin.urllib.request.urlopen',side_effect=[hata(500),Yanit(json.dumps({'sha':'abc'}).encode())]) as ac,\
                patch('github_yayin.time.sleep') as bekle:
            self.assertEqual(github_yayin.api('git/trees','t','POST',{}),{'sha':'abc'})
        self.assertEqual(ac.call_count,2)
        bekle.assert_called_once_with(30)

    def test_surekli_500_istegi_adiyla_bildirilir(self):
        with patch('github_yayin.urllib.request.urlopen',side_effect=[hata(500) for _ in range(4)]) as ac,\
                patch('github_yayin.time.sleep'):
            with self.assertRaises(RuntimeError) as sonuc:
                github_yayin.api('git/trees/abc?recursive=1','t')
        self.assertEqual(ac.call_count,4)
        self.assertEqual(str(sonuc.exception),'GitHub yayın HTTP 500 (GET git/trees/abc)')

    def test_422_tekrar_denenmez(self):
        with patch('github_yayin.urllib.request.urlopen',side_effect=[hata(422)]) as ac,patch('github_yayin.time.sleep') as bekle:
            with self.assertRaises(RuntimeError) as sonuc:
                github_yayin.api('git/refs/heads/main','t','PATCH',{})
        self.assertEqual(ac.call_count,1)
        bekle.assert_not_called()
        self.assertIn('422',str(sonuc.exception))


if __name__=='__main__':
    unittest.main()