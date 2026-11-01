import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analiz_sayfalari as an
from site_uret import TR

BASE = 'https://kpsstercihi.com/'
SIMDI = datetime(2026, 11, 1, 12, 0, tzinfo=TR)


def satir(unvan, min_, il='ANKARA', kont=1, yer=1, kurum='ABC Kurumu'):
    return {'kod': '1', 'kurum': kurum, 'il': il, 'teskilat': 'Merkez', 'unvan': unvan, 'kontenjan': kont, 'yerlesen': yer,
            'min': min_, 'max': min_, 'nit': []}


class HesapTest(unittest.TestCase):
    def test_medyan_null_atlar(self):
        self.assertEqual(an.medyan([satir('A', 60.0), satir('A', None), satir('A', 70.0), satir('A', 90.0)]), 70.0)
        self.assertEqual(an.medyan([satir('A', 60.0), satir('A', 70.0)]), 65.0)
        self.assertIsNone(an.medyan([satir('A', None)]))

    def test_donem_ozetleri_ve_degisim(self):
        d = {'2025-2': [satir('A', 60.0, kont=4, yer=2), satir('B', 70.0, kont=6, yer=6)],
             '2026-1': [satir('A', 80.0, kont=2, yer=2), satir('B', None, kont=3, yer=0)],
             '2024-1': []}
        oz = an.donem_ozetleri(d)
        self.assertEqual([o['donem'] for o in oz], ['2025-2', '2026-1'])   # boş dönem atlanır
        self.assertEqual((oz[0]['kontenjan'], oz[0]['yerlesen'], oz[0]['med'], oz[0]['en_dusuk']), (10, 8, 65.0, 60.0))
        self.assertAlmostEqual(oz[0]['doluluk'], 80.0)
        self.assertEqual(oz[1]['med'], 80.0)
        c = an.degisim_cumlesi(oz, 'Lisans')
        self.assertIn('2026/1 döneminde en küçük puanların medyanı 80,00', c)
        self.assertIn('15,00 puan yükseldi', c)
        self.assertIsNone(an.degisim_cumlesi(oz[:1], 'Lisans'))
        self.assertIsNone(an.degisim_cumlesi([dict(oz[0]), dict(oz[1], med=None)], 'Lisans'))

    def test_il_esigi(self):
        satirlar = [satir('A', 50.0 + i, il='VAN') for i in range(10)] + [satir('A', 90.0, il='İZMİR') for _ in range(9)] \
            + [satir('A', None, il='MUĞLA') for _ in range(12)]
        oz = an.il_ozetleri(satirlar)
        self.assertEqual([o['il'] for o in oz], ['Van'])   # İzmir 9 satır, Muğla puansız
        self.assertEqual(oz[0]['satir'], 10)
        self.assertEqual(oz[0]['med'], 54.5)
        satirlar += [satir('A', 90.0, il='İZMİR')]
        oz = an.il_ozetleri(satirlar)
        self.assertEqual([o['il'] for o in oz], ['Van', 'İzmir'])

    def test_uc_uclar_cakismaz(self):
        liste = [{'x': i} for i in range(7)]
        dusuk, yuksek = an.uc_uclar(liste, 5)
        self.assertEqual([o['x'] for o in dusuk], [0, 1, 2])
        self.assertEqual([o['x'] for o in yuksek], [6, 5, 4])
        self.assertEqual(an.uc_uclar([{'x': 1}], 5), ([], []))

    def test_kadro_esigi_ve_sira(self):
        s = [satir('MEMUR', 70.0, kont=6), satir('MEMUR', 72.0, kont=5), satir('İŞÇİ', 60.0, kont=9), satir('TEKNİSYEN', 80.0, kont=10),
             satir('KÜÇÜK', 99.0, kont=1), satir('PUANSIZ', None, kont=50)]
        oz = an.kadro_ozetleri(s)
        self.assertEqual([o['unvan'] for o in oz], ['MEMUR', 'TEKNİSYEN'])   # İŞÇİ 9 < 10, PUANSIZ medyan yok
        self.assertEqual(oz[0]['kontenjan'], 11)
        self.assertEqual(oz[0]['med'], 71.0)

    def test_son_dort_donem(self):
        d = {f'202{y}-{n}': [satir('A', 50.0)] for y in (4, 5, 6) for n in (1, 2)}
        secili, satirlar = an.son_satirlar(d)
        self.assertEqual(secili, ['2025-1', '2025-2', '2026-1', '2026-2'])
        self.assertEqual(len(satirlar), 4)
        self.assertEqual(an.donem_araligi(secili), '2025/1–2026/2')

    def test_kurum_en_cok_kontenjan(self):
        s = [satir('A', 60.0, kont=5, kurum='X Belediyesi'), satir('B', 70.0, kont=7, kurum='X Belediyesi'), satir('C', None, kont=20, kurum='Y Kurumu'),
             satir('D', 50.0, kont=0, kurum='Z Kurumu')]
        oz = an.kurum_ozetleri(s, en_cok=2)
        self.assertEqual([o['kurum'] for o in oz], ['Y Kurumu', 'X Belediyesi'])
        self.assertIsNone(oz[0]['med'])
        self.assertEqual(oz[1]['kontenjan'], 12)
        self.assertEqual(oz[1]['med'], 65.0)

    def test_ilan_istatistikleri(self):
        k = lambda y, s, **e: dict({'yayin': y, 'bas': y, 'son': s, 'kurum': 'A', 'il': 'Ankara', 'ogrenim': ['lisans'], 'kadro': 3}, **e)
        kayit = [k(date(2026, 9, 14), date(2026, 9, 28)), k(date(2026, 9, 20), date(2026, 9, 24), il='Van', kadro=None),
                 k(date(2026, 10, 1), None, kurum='B', ogrenim=[], bas=None)]
        ist = an.ilan_istatistikleri(kayit)
        self.assertEqual(ist['toplam'], 3)
        self.assertEqual([(y, m, a['ilan'], a['kadro']) for y, m, a in ist['aylar']], [(2026, 9, 2, 3), (2026, 10, 1, 3)])
        self.assertEqual(ist['sure_medyan'], 9.0)   # 14 ve 4 gün
        self.assertEqual(ist['sure_n'], 2)
        self.assertEqual(ist['iller'][0], ('Ankara', 2))
        self.assertEqual(ist['ogrenim']['belirtilmemis'], 1)
        self.assertEqual((ist['ilk'], ist['son']), (date(2026, 9, 14), date(2026, 10, 1)))
        self.assertEqual(ist['kadro_bilinen'], 2)
        self.assertIsNone(an.ilan_istatistikleri([]))
        self.assertIsNone(an.ilan_sayfasi(None))


class YazTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.docs = Path(self.tmp.name)
        (self.docs / 'puanlar').mkdir()
        illar = ['ADANA', 'VAN', 'MUĞLA']
        satirlar = lambda base: [satir(('MEMUR', 'TEKNİSYEN')[i % 2], base + i, il=illar[i % 3], kont=2) for i in range(24)]
        veri = {'duzey': 'lisans', 'ad': 'Lisans', 'donemler': {'2025-2': satirlar(60.0), '2026-1': satirlar(62.0)}}
        (self.docs / 'puanlar' / 'lisans.json').write_text(json.dumps(veri, ensure_ascii=False), encoding='utf-8')
        # kadro sayfası yalnız dosyası varsa bağlanır
        (self.docs / 'kpss-taban-puanlari' / 'lisans' / 'memur').mkdir(parents=True)
        (self.docs / 'kpss-taban-puanlari' / 'lisans' / 'memur' / 'index.html').write_text('x', encoding='utf-8')

    def test_sayfalar_yazilir(self):
        adresler = an.yaz(self.docs, BASE, [], SIMDI)
        self.assertEqual(adresler[0], BASE + 'analiz/')
        self.assertEqual(len(adresler), 5)   # hub + 4 puan sayfası; ilan listesi boş
        a = self.docs / 'analiz'
        for alt in ('taban-puan-degisimi', 'il-il-taban-puanlari', 'kadro-puan-siralamasi', 'kurum-kontenjanlari'):
            self.assertTrue((a / alt / 'index.html').is_file(), alt)
        self.assertFalse((a / 'kamu-ilan-istatistikleri').exists())
        degisim = (a / 'taban-puan-degisimi' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('2026/1 döneminde en küçük puanların medyanı 73,50', degisim)
        self.assertIn('2,00 puan yükseldi', degisim)
        self.assertIn('Güncelleme: 1 Kasım 2026', degisim)
        self.assertIn('<h1>', degisim)
        self.assertIn('ÖSYM', degisim)
        il = (a / 'il-il-taban-puanlari' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Muğla', il)
        kadro = (a / 'kadro-puan-siralamasi' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('href="../../kpss-taban-puanlari/lisans/memur/"', kadro)
        hub = (a / 'index.html').read_text(encoding='utf-8')
        self.assertIn('href="il-il-taban-puanlari/"', hub)

    def test_veri_yoksa_hicbir_sey_yazilmaz(self):
        (self.docs / 'puanlar' / 'lisans.json').unlink()
        self.assertEqual(an.yaz(self.docs, BASE, [], SIMDI), [])
        self.assertFalse((self.docs / 'analiz').exists())

    def test_baglanti_sayfa_yoksa_yok(self):
        (self.docs / 'kpss-taban-puanlari' / 'lisans' / 'memur' / 'index.html').unlink()
        an.yaz(self.docs, BASE, [], SIMDI)
        kadro = (self.docs / 'analiz' / 'kadro-puan-siralamasi' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('kpss-taban-puanlari/lisans/memur', kadro)


if __name__ == '__main__':
    unittest.main()