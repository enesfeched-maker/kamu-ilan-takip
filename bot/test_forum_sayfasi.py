"""Forum (Kasım 2026): ilan sayfasındaki tartışma alanı, /forum/ kabuğu ve menü bağlantısı."""
import unittest
from datetime import datetime

import forum_sayfasi
import site_uret as su

UUID = '11111111-1111-4111-8111-111111111111'


def ilan(**ek):
    item = {'baslik': 'ADALET BAKANLIĞI - 2026 Yılı Açıktan İcra Müdür Alım İlanı', 'kurum': 'ADALET BAKANLIĞI',
            'link': f'https://kariyerkapisi.gov.tr/IlanDetay?i={UUID}', 'son_tarih': '2099-01-01'}
    item.update(ek)
    return item


class IlanTartismasi(unittest.TestCase):
    def test_acik_ilanda_tartisma_alani_ve_betik(self):
        html = su.detail_page(ilan(), simdi=datetime(2026, 11, 15, tzinfo=su.TR))[1]
        self.assertIn(f'id="tartisma" data-ilan="{UUID}"', html)
        self.assertIn('data-acik="1"', html)
        self.assertIn('forum.js?v=', html)
        self.assertIn('forum.css?v=', html)
        # tartışma içerikten sonra, benzer ilanlardan önce gelir
        self.assertLess(html.index('class="d-bolum"'), html.index('id="tartisma"'))

    def test_suresi_gecmis_ilanda_basvuru_kapali(self):
        html = su.detail_page(ilan(son_tarih='2000-01-01'), simdi=datetime(2026, 11, 15, tzinfo=su.TR))[1]
        self.assertIn('data-acik="0"', html)

    def test_kopya_sayfa_esas_ilanin_tartismasini_kullanir(self):
        kopya = {'rol': 'ikincil', 'birincil': 'sbb-' + 'a' * 24}
        html = su.detail_page(ilan(), simdi=datetime(2026, 11, 15, tzinfo=su.TR), kopya=kopya)[1]
        self.assertIn('data-ilan="sbb-' + 'a' * 24 + '"', html)

    def test_ilan_adi_kacislanir(self):
        html = su.detail_page(ilan(baslik='<b>"X"</b> ilanı'), simdi=datetime(2026, 11, 15, tzinfo=su.TR))[1]
        bolum = html[html.index('id="tartisma"'):]
        self.assertNotIn('data-ad="<b>', bolum)


class ForumKabugu(unittest.TestCase):
    def test_noindex_reklamsiz_ve_betikli(self):
        adres, html = forum_sayfasi.forum_sayfasi('https://kpsstercihi.com/')
        self.assertEqual(adres, 'https://kpsstercihi.com/forum/')
        self.assertIn('noindex', html)
        self.assertNotIn('adsbygoogle', html)
        self.assertIn('id="forum"', html)
        self.assertIn('../forum.js?v=', html)
        self.assertIn('aria-current="page"', html)

    def test_menude_forum(self):
        self.assertIn('href="../forum/"', su.ust_html('../'))

    def test_ust_cubukta_hesap_girisi(self):
        # her sayfada hesap.js (ertelenmiş); forum.js'in sürümü tembel yükleme için data-f ile verilir
        for kok in ('', '../', '../../'):
            h = su.ust_html(kok)
            self.assertIn(f'<script src="{kok}hesap.js?v={su.HESAP_SURUM}" data-f="{su.FORUM_SURUM}" defer></script>', h)
            self.assertIn('class="tb-ikon"', h)   # Profil girişsiz kullanıcı için durur; hesap.js girişliyken gizler


if __name__ == '__main__':
    unittest.main()
