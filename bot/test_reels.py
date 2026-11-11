"""Hareketli video şablonları: seçim kuralları, sahne düzeni ve kare çizimi (ffmpeg gerektirmez)."""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reels
from kart_tasarimlari import TR

SIMDI = datetime.now(TR).replace(hour=9, minute=0, second=0, microsecond=0)


def setUpModule():
    """Testler depodaki sosyal/ayar.json'a (ajanın kararlarına) bağlı kalmasın: varsayılan ayarlarla koşar."""
    import sosyal_ajan
    global _ESKI_AYAR
    _ESKI_AYAR = sosyal_ajan.AYAR_YOLU
    sosyal_ajan.AYAR_YOLU = Path(__file__).with_name('yok-ayar.json')


def tearDownModule():
    import sosyal_ajan
    sosyal_ajan.AYAR_YOLU = _ESKI_AYAR


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


class GunlukTest(unittest.TestCase):
    """Bota bağlanan akış: vakte göre sabit biçim, ilan başına sıra ve günlük sınır, paylasim.json ve geçmiş kaydı."""

    def test_siradaki_ilan_sirasi_ve_siniri(self):
        acik = [ilan('eski', 9, gorulme=5), ilan('kucuk', 9, 'Toplam 2 kişi — 2 Memur'), ilan('buyuk', 9)]
        self.assertEqual(reels.siradaki_ilan(acik, SIMDI)['id'], 'buyuk')
        zaman = SIMDI.isoformat(timespec='seconds')
        gecmis = [{'tur': 'ilan', 'zaman': zaman, 'ilanlar': ['buyuk']}]
        self.assertEqual(reels.siradaki_ilan(acik, SIMDI, gecmis)['id'], 'kucuk')            # videosu yapılan yeniden yapılmaz
        gecmis.append({'tur': 'ilan', 'zaman': zaman, 'ilanlar': ['kucuk']})
        self.assertIsNone(reels.siradaki_ilan(acik, SIMDI, gecmis))                          # 5 gün önce eklenen taze değil
        dolu = [{'tur': 'ilan', 'zaman': zaman, 'ilanlar': [str(n)]} for n in range(reels.ILAN_GUNLUK)]
        self.assertIsNone(reels.siradaki_ilan(acik, SIMDI, dolu))                            # günlük sınır
        dun = [{'tur': 'ilan', 'zaman': (SIMDI - timedelta(days=1)).isoformat(timespec='seconds'), 'ilanlar': [str(n)]} for n in range(5)]
        self.assertEqual(reels.siradaki_ilan(acik, SIMDI, dun)['id'], 'buyuk')               # dünkü videolar bugünü kısıtlamaz

    def test_gunluk_konular(self):
        acik = [ilan('a', 1), ilan('b', 9, 'Toplam 4 kişi — 4 Şoför')]
        sabah = reels.gunluk('sabah', acik, SIMDI)
        self.assertEqual((sabah['tur'], sabah['muzik'], sabah['ilanlar']), ('son_gun', 'sabah', ['a']))
        self.assertIn('Deneme Kurumu: 12 kişi · Memur, Tekniker (son gün ', sabah['satirlar'][0])
        aksam = reels.gunluk('aksam', acik, SIMDI)
        self.assertEqual((aksam['tur'], aksam['baslik'], aksam['ilanlar']), ('ozet', 'Bugün 2 Yeni Kamu İlanı', ['a', 'b']))
        tek = reels.gunluk('ilan', acik, SIMDI)
        self.assertEqual((tek['tur'], tek['anahtar'], tek['baslik']), ('ilan', 'ilan:a', 'Deneme Kurumu 12 kişi alacak'))
        self.assertEqual(tek['satirlar'], ['• 10 Memur', '• 2 Tekniker'])
        self.assertIsNone(reels.gunluk('sabah', [ilan('uzak', 9)], SIMDI))
        self.assertIsNone(reels.gunluk('aksam', [ilan('dun', 9, gorulme=2)], SIMDI))
        self.assertIsNone(reels.gunluk('aksam', acik[:1], SIMDI))   # tek ilanlık günde özet yok
        self.assertIsNone(reels.gunluk('ilan', [], SIMDI))

    def test_muzik_yolu_onbellek_ve_hata(self):
        import tempfile
        with tempfile.TemporaryDirectory() as g:
            dosya, bas = reels.MUZIK['aksam']
            (Path(g) / dosya).write_bytes(b'ID3' + b'0' * 200_000)
            self.assertEqual(reels.muzik_yolu('aksam', g), (Path(g) / dosya, bas))           # önbellekteki dosya indirilmez
            eski = reels.MUZIK_ADRESI
            reels.MUZIK_ADRESI = 'http://127.0.0.1:9/{no}.mp3'                              # erişilemeyen adres
            try:
                self.assertEqual(reels.muzik_yolu('sabah', g, zaman_asimi=2), (None, 0.0))
            finally:
                reels.MUZIK_ADRESI = eski

    def test_sablon_uret_dosyalari_ve_gecmis(self):
        import json
        import tempfile
        import sosyal_motor as sm
        konu = reels.gunluk('ilan', [ilan('a', 5)], SIMDI)
        eski = reels.muzik_yolu
        reels.muzik_yolu = lambda tur, *a, **k: (None, 0.0)                                  # ağ yok: eski parçaya düşer
        try:
            with tempfile.TemporaryDirectory() as g:
                ozet = sm.sablon_uret(konu, 'ilan', Path(g) / 'cikti', SIMDI, [], Path(g) / 'gecmis.json', video=False)
                kayit = json.loads((Path(g) / 'cikti' / 'paylasim.json').read_text(encoding='utf-8'))
                gecmis = json.loads((Path(g) / 'gecmis.json').read_text(encoding='utf-8'))
                kareler = sorted(p.name for p in (Path(g) / 'cikti').glob('*.png'))
        finally:
            reels.muzik_yolu = eski
        self.assertEqual(kareler, ['01.png', '02.png', '03.png', '04.png'])
        self.assertEqual((kayit['tur'], kayit['sablon'], kayit['kare']), ('ilan', True, 4))
        self.assertTrue(kayit['baslik'].startswith('Deneme Kurumu 12 kişi alacak'))
        self.assertIn('• 10 Memur', kayit['aciklama'])
        self.assertLessEqual(len(kayit['etiketler']), 5)
        self.assertEqual((gecmis[-1]['tur'], gecmis[-1]['ilanlar'], gecmis[-1]['zaman']), ('ilan', ['a'], ozet['zaman']))

    def test_paletler_sirayla_ve_yesilsiz(self):
        self.assertEqual(reels.PALET_SIRASI, ('kagit', 'bordo'))
        self.assertEqual(reels.siradaki_palet([]), 'kagit')
        self.assertEqual(reels.siradaki_palet([{'tur': 'kategori'}, {'palet': 'kagit'}, {'tur': 'haber'}]), 'bordo')   # eski biçimli kayıt sırayı bozmaz
        self.assertEqual(reels.siradaki_palet([{'palet': 'kagit'}, {'palet': 'bordo'}]), 'kagit')
        self.assertEqual(reels.siradaki_palet([{'palet': 'petrol'}]), 'kagit')
        eski = reels.R.ad
        try:
            kareler = {}
            for ad in reels.PALET_SIRASI:
                reels.palet_sec(ad)
                kareler[ad] = reels.kare(reels.ilan_videosu(ilan('a', 5), SIMDI), 1.5)
                r, g, b = kareler[ad].getpixel((540, 1800))   # zemin: açık ve yeşil ağırlıklı değil
                self.assertGreater(min(r, g, b), 150, ad)
                self.assertGreaterEqual(r, g, ad)
            self.assertNotEqual(kareler['kagit'].tobytes(), kareler['bordo'].tobytes())
        finally:
            reels.palet_sec(eski)


if __name__ == '__main__':
    unittest.main()
