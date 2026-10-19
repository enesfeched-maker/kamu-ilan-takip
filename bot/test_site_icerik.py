"""Siteye özgü içerik (19 Ekim 2026): ilan sayfasında geçmiş taban puanları, kurum yerleştirme geçmişi, rehberler, noindex."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import ilan_taban
import kurum_zengin
import rehberler
import site_uret
from site_uret import TR

SIMDI = datetime(2026, 10, 19, 12, 0, tzinfo=TR)


def puan_klasoru():
    t = Path(tempfile.mkdtemp())
    (t / 'puanlar').mkdir()
    satir = lambda d, m, kurum='ANKARA ÜNİVERSİTESİ', il='ANKARA': {'kod': d, 'kurum': kurum, 'il': il, 'unvan': 'ZABITA MEMURU',
                                                                     'kontenjan': 1, 'yerlesen': 1, 'min': m, 'max': m + 3}
    veri = {'donemler': {'2025-2': [satir('1', 70.5), satir('2', 75.25, 'DİDİM BELEDİYE BAŞKANLIĞI', 'AYDIN')],
                         '2026-1': [satir('3', 72.0), satir('4', 80.0)]}}
    (t / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
    ilan_taban._veri.cache_clear()
    kurum_zengin._indeks.cache_clear()
    return t


class Icerik(unittest.TestCase):
    def test_ilan_sayfasi_taban_bolumu(self):
        docs = puan_klasoru()
        item = {'id': 'iskur-1', 'kurum': 'Ankara Üniversitesi Rektörlüğü', 'kadro': '3 Zabıta Memuru', 'ogrenim': ['lisans']}
        h = ilan_taban.bolum_html(item, docs)
        self.assertIn('Bu kadroya geçmişte kaç puanla atanıldı?', h)
        self.assertIn('2026/1', h)
        self.assertIn('70,50', h)
        self.assertIn('Bu kurumun merkezi yerleştirmedeki', h)   # aynı kurumun satırları
        self.assertEqual(ilan_taban.bolum_html(dict(item, kadro='2 Uzman'), docs), '')   # belirsiz unvan eşleşmez

    def test_kurum_yerlestirme_gecmisi(self):
        docs = puan_klasoru()
        self.assertEqual(len(kurum_zengin.yerlestirmeler('ankara universitesi', docs)), 3)
        self.assertIn('KPSS merkezi yerleştirme geçmişi', kurum_zengin.yerlestirme_html('ankara universitesi', docs))
        self.assertEqual(kurum_zengin.yerlestirme_html('yok kurum', docs), '')

    def test_dizinlenmez(self):
        acik = {'kadro': '2 Memur', 'son_tarih': (SIMDI + timedelta(days=5)).date().isoformat()}
        self.assertFalse(site_uret.dizinlenmez(acik, SIMDI))
        self.assertTrue(site_uret.dizinlenmez(dict(acik, duyuru_turu='İptal'), SIMDI))
        self.assertTrue(site_uret.dizinlenmez(dict(acik, son_tarih='2026-08-01'), SIMDI))
        self.assertFalse(site_uret.dizinlenmez(dict(acik, son_tarih='2026-10-01'), SIMDI))
        self.assertTrue(site_uret.dizinlenmez({'son_tarih': acik['son_tarih']}, SIMDI))   # hiç içerik yok

    def test_rehberler(self):
        with tempfile.TemporaryDirectory() as t:
            adresler = rehberler.yaz(t, 'https://kpsstercihi.com/')
            self.assertEqual(len(adresler), len(rehberler.REHBERLER) + 1)
            h = (Path(t) / 'rehber' / 'kpss-puan-turleri' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('"@type": "Article"', h)
        self.assertIn('<h1>KPSS puan türleri', h)
        self.assertEqual(len({r[0] for r in rehberler.REHBERLER}), len(rehberler.REHBERLER))
        for r in rehberler.REHBERLER:
            self.assertLessEqual(len(r[2]), 170, r[0])   # arama sonucu açıklaması kesilmesin


if __name__ == '__main__':
    unittest.main()
