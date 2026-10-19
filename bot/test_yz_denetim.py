import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import yz_denetim as yd
from site_uret import TR

SIMDI = datetime(2026, 10, 19, 20, 0, tzinfo=TR)


def ilan(kimlik='kk-1', **ek):
    return dict({'id': kimlik, 'baslik': 'Örnek Bakanlığı - 3 Uzman', 'kurum': 'Örnek Bakanlığı', 'kadro': '3 Uzman',
                 'son_tarih': '2026-10-26', 'ogrenim': ['lisans'], 'puan_turleri': ['P3'], 'ozet': 'Başvurular Kariyer Kapısı.'}, **ek)


def yz(**ek):
    return dict({'kadrolar': [{'unvan': 'Uzman', 'adet': 3}], 'toplam': 3, 'son_basvuru_tarihi': '2026-10-26',
                 'ogrenim': ['lisans'], 'puan_turleri': ['KPSS P3'], 'sartlar': [], 'akademik': False,
                 'iptal_veya_duzeltme': False, 'okunabilirlik': 'iyi'}, **ek)


class Karsilastir(unittest.TestCase):
    def test_uyusan(self):
        self.assertEqual(yd.karsilastir(ilan(), yz()), [])

    def test_kritik_farklar(self):
        farklar = yd.karsilastir(ilan(), yz(son_basvuru_tarihi='2026-11-18', toplam=11, akademik=True))
        self.assertEqual({f[0] for f in farklar if f[3]}, {'son_tarih', 'toplam', 'akademik'})

    def test_eksik_deger_fark_sayilmaz(self):
        self.assertEqual(yd.karsilastir(ilan(kadro='Uzman'), yz(toplam=None, son_basvuru_tarihi=None, ogrenim=[])), [])


class Akis(unittest.TestCase):
    def test_denetle_kaydeder_ve_tekrar_sormaz(self):
        sorulan = []

        def cagir(parca, anahtar):
            sorulan.append(parca[0]['text'])
            return yz(son_basvuru_tarihi='2026-10-30')

        ilanlar = [ilan(), ilan('eski', son_tarih='2026-10-01'), ilan('duyuru', duyuru_turu='iptal')]
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            yol = Path(d) / 'yz.json'
            sayac = yd.denetle(5, 'anahtar', SIMDI, ilanlar, yol, cagir)
            self.assertEqual((sayac['denetlenen'], sayac['kritik']), (1, 1))
            kayit = json.loads(yol.read_text(encoding='utf-8'))['kk-1']
            self.assertEqual(kayit['farklar'][0][:3], ['son_tarih', '2026-10-26', '2026-10-30'])
            self.assertIn('Kariyer Kapısı', sorulan[0])
            yd.denetle(5, 'anahtar', SIMDI, ilanlar, yol, cagir)                      # içerik aynı: yeniden sorulmaz
            self.assertEqual(len(sorulan), 1)
            yd.denetle(5, 'anahtar', SIMDI, [ilan(kadro='4 Uzman')], yol, cagir)     # içerik değişti: yeniden sorulur
            self.assertEqual(len(sorulan), 2)

    def test_kota_dolunca_durur(self):
        def cagir(parca, anahtar):
            raise yd.KotaDoldu('429')
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            sayac = yd.denetle(5, 'a', SIMDI, [ilan(), ilan('kk-2')], Path(d) / 'yz.json', cagir)
        self.assertEqual(sayac['denetlenen'], 0)

    def test_yogunlukta_onceki_modele_gecer(self):
        import urllib.error
        from unittest import mock

        def iste(model, govde, anahtar, zaman_asimi):
            if model == 'yeni-flash':
                raise urllib.error.HTTPError('u', 503, 'yogun', {}, io.BytesIO(b'{"error": "yogun"}'))
            return {'candidates': [{'content': {'parts': [{'text': '{"toplam": 3}'}]}}]}

        with mock.patch.object(yd, '_iste', iste), mock.patch.object(yd, '_MODELLER', ['yeni-flash', 'eski-flash']), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(yd.gemini([], 'a', bekle=0), {'toplam': 3})
            self.assertEqual(yd._MODELLER[0], 'eski-flash')

    def test_anahtarsiz_atlanir(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(yd.denetle(5, '', SIMDI, []))


if __name__ == '__main__':
    unittest.main()
