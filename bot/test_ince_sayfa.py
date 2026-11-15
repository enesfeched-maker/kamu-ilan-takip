"""İnce sayfa kalkanı: kısa şablon sayfası noindex + reklamsız + haritadan çıkar (15 Kasım 2026)."""
import tempfile
import unittest
from pathlib import Path

import ince_sayfa
import site_uret

BASE = 'https://kpsstercihi.com/'


def sayfa(govde):
    return site_uret.sayfa_basi('Başlık', 'Açıklama', BASE, '../') + f'<body><main>{govde}</main></body></html>'


class InceSayfaTesti(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        for yol, govde in {'kurum/ince': 'az kelime ' * 20, 'kurum/dolu': 'kelime ' * 400,
                           'rehber/kisa': 'kısa rehber', 'iletisim': 'iletişim bilgisi',
                           'kurum/ilanli': '<a href="../../ilan/abc-1/">Zabıta Memuru</a> ' + 'satır ' * 150,
                           'meslek/ilanli-ince': '<a href="../../ilan/abc-2/">Ebe</a> kısa'}.items():
            (self.docs / yol).mkdir(parents=True)
            (self.docs / yol / 'index.html').write_text(sayfa(govde), encoding='utf-8')
        self.urls = [BASE, BASE + 'kurum/', BASE + 'kurum/ince/', BASE + 'kurum/dolu/', BASE + 'rehber/kisa/', BASE + 'iletisim/', BASE + 'kurum/ilanli/', BASE + 'meslek/ilanli-ince/']
        self.kalan, self.cikan = ince_sayfa.suz(self.docs, BASE, self.urls)

    def tearDown(self):
        self.tmp.cleanup()

    def oku(self, yol):
        return (self.docs / yol / 'index.html').read_text(encoding='utf-8')

    def test_ince_sablon_sayfasi_haritadan_cikar_noindex_reklamsiz(self):
        self.assertEqual(self.cikan, [BASE + 'kurum/ince/', BASE + 'meslek/ilanli-ince/'])
        self.assertNotIn(BASE + 'kurum/ince/', self.kalan)
        h = self.oku('kurum/ince')
        self.assertIn(ince_sayfa.NOINDEX, h)
        self.assertNotIn('pagead2', h)

    def test_dolu_sayfa_ve_sablon_disi_sayfa_dokunulmaz(self):
        for u in (BASE, BASE + 'kurum/', BASE + 'kurum/dolu/', BASE + 'rehber/kisa/', BASE + 'iletisim/'):
            self.assertIn(u, self.kalan)
        self.assertIn('pagead2', self.oku('kurum/dolu'))
        self.assertIn('pagead2', self.oku('rehber/kisa'))
        self.assertNotIn('noindex', self.oku('kurum/dolu'))

    def test_acik_ilani_olan_kisa_sayfa_dizinde_kalir(self):
        self.assertIn(BASE + 'kurum/ilanli/', self.kalan)
        self.assertNotIn('noindex', self.oku('kurum/ilanli'))

    def test_iletisim_dizinde_ama_reklamsiz(self):
        h = self.oku('iletisim')
        self.assertNotIn('pagead2', h)
        self.assertNotIn('noindex', h)
        self.assertIn('google-adsense-account', h)   # site doğrulama etiketi kalır

    def test_ikinci_gecis_ayni_sonucu_verir(self):
        kalan, cikan = ince_sayfa.suz(self.docs, BASE, self.kalan)
        self.assertEqual(kalan, self.kalan)
        self.assertEqual(self.oku('kurum/ince').count('noindex'), 1)

    def test_reklam_betigi_deseni_site_uret_ile_uyumlu(self):
        self.assertEqual(ince_sayfa.reklami_cikar(site_uret.REKLAM_BETIGI), '')


if __name__ == '__main__':
    unittest.main()
