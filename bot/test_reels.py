"""Hareketli video şablonları: seçim kuralları, sahne düzeni ve kare çizimi (ffmpeg gerektirmez)."""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reels
from kart_tasarimlari import TR

SIMDI = datetime.now(TR).replace(hour=9, minute=0, second=0, microsecond=0)


def ilan(kimlik, gun, kadro='Toplam 12 kişi — 10 Memur • 2 Tekniker', kurum='Deneme Kurumu Başkanlığı', gorulme=0, **ek):
    return {'id': kimlik, 'kurum': kurum, 'kadro': kadro, 'ogrenim': ['lisans'], 'kpss': 'kpss', 'iller': ['Ankara'],
            'son_tarih': (SIMDI + timedelta(days=gun)).date().isoformat(),
            'ilk_gorulme': (SIMDI - timedelta(days=gorulme)).isoformat(timespec='seconds'), **ek}


class SecimTest(unittest.TestCase):
    def test_son_gun_ufku_ve_sirasi(self):
        acik = [ilan('uzak', 9), ilan('uc', 3), ilan('bugun', 0), ilan('yarin-kucuk', 1, 'Toplam 1 kişi — 1 Memur'), ilan('yarin-buyuk', 1)]
        secim, toplam = reels.son_gun_ilanlari(acik, SIMDI)
        self.assertEqual([i['id'] for i in secim], ['bugun', 'yarin-buyuk', 'yarin-kucuk', 'uc'])   # en yakın tarih, sonra kalabalık alım
        self.assertEqual(toplam, 4)
        secim, toplam = reels.son_gun_ilanlari([ilan(str(n), 1) for n in range(9)], SIMDI)
        self.assertEqual((len(secim), toplam), (reels.SON_GUN_EN_COK, 9))

    def test_bugunun_ilanlari(self):
        acik = [ilan('dun', 5, gorulme=1), ilan('kucuk', 5, 'Toplam 2 kişi — 2 Memur'), ilan('buyuk', 5)]
        self.assertEqual([i['id'] for i in reels.bugunun_ilanlari(acik, SIMDI)], ['buyuk', 'kucuk'])

    def test_parcala_tek_satir_birakmaz(self):
        self.assertEqual([reels.parcala(n) for n in (1, 3, 4, 6, 7, 9)], [[1], [3], [2, 2], [3, 3], [3, 2, 2], [3, 3, 3]])


class MetinTest(unittest.TestCase):
    def test_kisa_ne_fiil_kalintisini_atar(self):
        v = {'toplam': 1, 'kadrolar': [{'adet': 1, 'ad': 'Alacak'}]}
        self.assertEqual(reels.kisa_ne(v), '1 kişi')
        v = {'toplam': 30, 'kadrolar': [{'adet': 20, 'ad': 'Memur'}, {'adet': 6, 'ad': 'Tekniker'}, {'adet': 4, 'ad': 'Şoför'}]}
        self.assertEqual(reels.kisa_ne(v), '30 kişi · Memur, Tekniker +1')

    def test_kosullar_yalniz_veride_olanlar(self):
        v = reels.k.veri(ilan('a', 5, ogrenim=[], kpss=None, iller=[]), None, SIMDI)
        self.assertEqual(reels.kosul_satirlari(v), [])
        v = reels.k.veri(ilan('a', 5), None, SIMDI)
        self.assertEqual([e for e, _ in reels.kosul_satirlari(v)], ['Öğrenim', 'KPSS', 'Yer'])

    def test_kadro_satirlari(self):
        v = {'kadrolar': [{'adet': n, 'ad': f'K{n}'} for n in range(1, 8)]}
        s = reels.kadro_satirlari(v, 5)
        self.assertEqual(s[0], (7, 'K7'))
        self.assertEqual(s[-1], (None, '+3 kadro daha'))


class SahneTest(unittest.TestCase):
    def test_uc_bicimin_sahne_duzeni(self):
        ilanlar = [ilan(str(n), n % 3) for n in range(7)]
        sabah = reels.son_gun_videosu(ilanlar[:4], 9, SIMDI)
        self.assertEqual(len(sabah), 1 + 4 + 1)             # giriş + ilan başına sahne + kapanış
        tek = reels.ilan_videosu(ilanlar[0], SIMDI)
        self.assertEqual(len(tek), 4)                       # kim/kaç kişi, kadrolar, koşullar, son başvuru
        aksam = reels.ozet_videosu(ilanlar, SIMDI)
        self.assertEqual(len(aksam), 1 + 3 + 1)             # 7 ilan -> 3+2+2
        for sahneler in (sabah, tek, aksam):
            self.assertTrue(sahneler[-1].son)               # video kapanış karesinde biter
            self.assertLessEqual(reels.video_suresi(sahneler), 25)
        self.assertIsNone(reels.son_gun_videosu([], 0, SIMDI))
        self.assertIsNone(reels.ozet_videosu([], SIMDI))

    def test_kosulsuz_ilanda_sahne_atlanir(self):
        tek = reels.ilan_videosu(ilan('a', 5, ogrenim=[], kpss=None, iller=[]), SIMDI)
        self.assertEqual(len(tek), 3)

    def test_kare_boyutu_ve_icerik(self):
        sahneler = reels.ilan_videosu(ilan('a', 5), SIMDI)
        bos, dolu = reels.zemin(), reels.kare(sahneler, 1.5)
        self.assertEqual(dolu.size, (reels.VW, reels.VH))
        self.assertNotEqual(bos.tobytes(), dolu.tobytes())
        self.assertEqual(sum(1 for _ in reels.kareler([reels.Sahne(0.2, [], son=True)])), 6)


if __name__ == '__main__':
    unittest.main()
