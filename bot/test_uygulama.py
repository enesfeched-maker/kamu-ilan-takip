import json
import re
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
UYG = KOK / 'uygulama'


class UygulamaTest(unittest.TestCase):
    def test_uygulama_betigi_yalniz_yerelde_yuklenir(self):
        portal = (KOK / 'docs' / 'portal.js').read_text(encoding='utf-8')
        self.assertRegex(portal, r"isNativePlatform\(\)\)\{[^}]*uygulama\.js")
        betik = (KOK / 'docs' / 'uygulama.js').read_text(encoding='utf-8')
        self.assertIn('if (!C || !C.isNativePlatform || !C.isNativePlatform()) return;', betik)

    def test_canli_sunucu_ve_gelistirme_ayari_yok(self):
        ayar = json.loads((UYG / 'capacitor.config.json').read_text(encoding='utf-8'))
        self.assertEqual(ayar['server']['url'], 'https://kpsstercihi.com')
        self.assertNotIn('cleartext', ayar['server'])

    def test_adsense_uygulama_icinde_engelli(self):
        android = (UYG / 'android/app/src/main/java/com/kpsstercihi/app/MainActivity.java').read_text(encoding='utf-8')
        ios = (UYG / 'ios/App/App/AppDelegate.swift').read_text(encoding='utf-8')
        self.assertIn('pagead2.googlesyndication.com', android)
        self.assertTrue(re.search(r'pagead2\\+\.googlesyndication', ios))

    def test_site_reklam_betigi_korunur(self):
        html = (KOK / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('adsbygoogle.js?client=ca-pub-8335827974832277', html)


if __name__ == '__main__':
    unittest.main()
