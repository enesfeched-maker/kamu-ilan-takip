import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import sosyal_istatistik as si
import sosyal_motor as sm
from site_uret import TR

SIMDI = datetime(2026, 10, 19, 12, 0, tzinfo=TR)


def kayit(gun_once, tur='son_gun', muzik='a.mp3', vakit='sabah', **ek):
    return dict({'zaman': (SIMDI - timedelta(days=gun_once)).isoformat(timespec='seconds'), 'tur': tur,
                 'anahtar': f'{tur}:{gun_once}', 'vakit': vakit, 'muzik': muzik}, **ek)


class Agirliklar(unittest.TestCase):
    def test_az_olcumde_agirlik_yok(self):
        gecmis = [kayit(i, ig={'views': 100}) for i in range(5)]
        self.assertEqual(si.agirliklar(gecmis)['tur'], {})

    def test_iyi_giden_tur_ve_muzik_one_cikar(self):
        gecmis = ([kayit(i, tur='rehber', muzik='iyi.mp3', ig={'views': 4000, 'shares': 20}) for i in range(4)]
                  + [kayit(i, tur='yeni', muzik='kotu.mp3', ig={'views': 300}) for i in range(4)])
        a = si.agirliklar(gecmis)
        self.assertGreater(a['tur']['rehber'], 5)
        self.assertLess(a['tur']['yeni'], -5)
        self.assertLessEqual(max(a['tur'].values()), si.EN_BUYUK_ETKI)
        self.assertGreater(a['muzik']['iyi.mp3'], 0)

    def test_skor(self):
        self.assertIsNone(si.skor(None))
        self.assertEqual(si.skor({'reach': 10, 'likes': 1, 'shares': 1}), 10 + 2 + 15)


class KonuVeMuzik(unittest.TestCase):
    def test_konu_sec_agirligi(self):
        adaylar = [{'tur': 'yeni', 'anahtar': 'y', 'puan': 50, 'kelimeler': set()},
                   {'tur': 'rehber', 'anahtar': 'r', 'puan': 45, 'kelimeler': set()}]
        self.assertEqual(sm.konu_sec(adaylar, [], SIMDI)['tur'], 'yeni')
        self.assertEqual(sm.konu_sec(adaylar, [], SIMDI, agirlik={'rehber': 10, 'yeni': -5})['tur'], 'rehber')

    def test_zayif_muzik_secilmez(self):
        with tempfile.TemporaryDirectory() as d:
            for ad in ('a.mp3', 'b.mp3'):
                (Path(d) / ad).write_bytes(b'')
            for tohum in ('1', '2', '3', '4', '5'):
                self.assertEqual(sm.muzik_sec([], tohum, d, agirlik={'a.mp3': -12}).name, 'b.mp3')


class Kimlik(unittest.TestCase):
    def test_eski_paylasim_zamanla_eslesir(self):
        gecmis = [kayit(3), kayit(1, ig_id='M1')]
        yayin = (SIMDI - timedelta(days=3) + timedelta(minutes=4)).astimezone(TR).strftime('%Y-%m-%dT%H:%M:%S%z')
        medyalar = [{'id': 'M1', 'timestamp': yayin}, {'id': 'M2', 'timestamp': yayin}]
        si.kimlik_eslestir(gecmis, medyalar)
        self.assertEqual(gecmis[0]['ig_id'], 'M2')

    def test_sonuc_isle(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            g = kayit(0)
            (d / 'gecmis.json').write_text(json.dumps([kayit(1), g]), encoding='utf-8')
            (d / 'paylasim.json').write_text(json.dumps({'zaman': g['zaman']}), encoding='utf-8')
            (d / 'sonuc.json').write_text(json.dumps({'instagram': {'id': '179'}, 'youtube': {'hata': 'x'},
                                                      'tiktok': {'id': 'v_1'}}), encoding='utf-8')
            self.assertTrue(si.sonuc_isle(d, d / 'gecmis.json'))
            son = json.loads((d / 'gecmis.json').read_text(encoding='utf-8'))[-1]
            self.assertEqual((son['ig_id'], son['tt_id']), ('179', 'v_1'))

    def test_topla_yalniz_2_30_gunlukleri_olcer(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            gecmis = [kayit(40, ig_id='E'), kayit(5, ig_id='O'), kayit(1, ig_id='Y')]
            (d / 'g.json').write_text(json.dumps(gecmis), encoding='utf-8')
            istenen = []

            def sahte(url, **_):
                if '/media?' in url:
                    return {'data': []}
                istenen.append(url.split('/')[4])
                return {'data': [{'name': 'views', 'values': [{'value': 900}]}]}

            with mock.patch.object(si, '_istek', sahte):
                si.topla(SIMDI, ('IG', 'anahtar'), d / 'g.json', d / 'i.json')
            self.assertEqual(istenen, ['O'])
            self.assertEqual(json.loads((d / 'g.json').read_text(encoding='utf-8'))[1]['ig']['views'], 900)
            self.assertEqual(json.loads((d / 'i.json').read_text(encoding='utf-8'))['olculen'], 1)


if __name__ == '__main__':
    unittest.main()
