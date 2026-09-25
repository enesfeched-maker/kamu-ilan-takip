import unittest
from site_uret import detail_page


class SiteTests(unittest.TestCase):
    def test_safe_static_detail_and_canonical(self):
        result = detail_page({'baslik': '<script>alert(1)</script>', 'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111', 'son_tarih': '2000-01-01'})
        self.assertIn('&lt;script&gt;', result[1])
        self.assertNotIn('<script>alert', result[1])
        self.assertIn('Başvuru sona erdi', result[1])
        self.assertIn('/ilan/11111111-1111-4111-8111-111111111111/', result[1])

    def test_reject_foreign_host_and_path_traversal(self):
        self.assertIsNone(detail_page({'link': 'https://evil.example/?i=11111111-1111-4111-8111-111111111111'}))
        self.assertIsNone(detail_page({'link': 'https://kariyerkapisi.gov.tr/?i=../../secret'}))


if __name__ == '__main__':
    unittest.main()
