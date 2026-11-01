import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilgi_sayfalari
import site_uret

DOCS = Path(__file__).resolve().parents[1] / 'docs'
BASE = 'https://kpsstercihi.com/'


class AdsenseDegerTest(unittest.TestCase):
    def test_reklam_betigi_yalniz_dizinlenen_sayfada(self):
        acik = site_uret.sayfa_basi('Başlık', 'Açıklama', BASE, '../')
        self.assertIn('adsbygoogle.js', acik)
        gizli = site_uret.sayfa_basi('Başlık', 'Açıklama', BASE, '../', ek_head='<meta name="robots" content="noindex,follow">')
        self.assertNotIn('adsbygoogle.js', gizli)
        self.assertIn('google-adsense-account', gizli)   # doğrulama etiketi kalır

    def test_404_betiksiz(self):
        t = (DOCS / '404.html').read_text(encoding='utf-8')
        self.assertNotIn('adsbygoogle.js', t)
        self.assertIn('google-adsense-account', t)

    def test_robots_belgeler_her_grupta(self):
        t = (DOCS / 'robots.txt').read_text(encoding='utf-8')
        gruplar = [g for g in re.split(r'\n\s*\n', t) if 'User-agent:' in g]
        self.assertGreaterEqual(len(gruplar), 2)
        for g in gruplar:
            self.assertIn('Disallow: /belgeler/', g)

    def test_iletisim_sayfasi(self):
        adres, html = bilgi_sayfalari.sayfa('iletisim', BASE)
        self.assertEqual(adres, BASE + 'iletisim/')
        self.assertIn('<h1>İletişim</h1>', html)
        self.assertIn('Duyurular için kanalımız: @kpsstercihi', html)
        self.assertIn('Hatalı ilan bildirirken', html)
        self.assertNotIn('mailto:', html)   # ILETISIM_EPOSTA boşken e-posta bölümü yok
        eski = bilgi_sayfalari.ILETISIM_EPOSTA
        bilgi_sayfalari.ILETISIM_EPOSTA = 'a@b.com'
        try:
            _, html = bilgi_sayfalari.sayfa('iletisim', BASE)
        finally:
            bilgi_sayfalari.ILETISIM_EPOSTA = eski
        self.assertIn('<a class="yazi-link" href="mailto:a@b.com">a@b.com</a>', html)

    def test_hakkimizda_yeni_bolumler(self):
        _, html = bilgi_sayfalari.sayfa('hakkimizda', BASE)
        for b in ('Neden kuruldu?', 'İlanları nasıl hazırlıyoruz?', 'Düzeltme ve iptaller', 'Puan verileri ve analizler'):
            self.assertIn(b, html)
        self.assertIn('href="../iletisim/"', html)
        js = (DOCS / 'portal.js').read_text(encoding='utf-8')
        self.assertIn('Neden kuruldu?', js)
        self.assertIn('Puan verileri ve analizler', js)

    def test_alt_bilgi_baglantilari(self):
        alt = site_uret.alt_html('../')
        for yol in ('analiz/', 'kurum/', 'iletisim/'):
            self.assertIn(f'href="../{yol}"', alt)
        for dosya, kok in (('index.html', ''), ('puanlar/index.html', '../')):
            t = (DOCS / dosya).read_text(encoding='utf-8')
            for yol in ('analiz/', 'kurum/', 'iletisim/'):
                self.assertIn(f'<a href="{kok}{yol}">', t, dosya)

    def test_dizinlenmez_akademik_ve_yedi_gun(self):
        self.assertEqual(site_uret.ESKI_ILAN_GUN, 7)


if __name__ == '__main__':
    unittest.main()