"""Hareketli video şablonları: seçim kuralları, sahne düzeni ve kare çizimi (ffmpeg gerektirmez)."""
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reels
from kart_tasarimlari import TR

SIMDI = datetime.now(TR).replace(hour=9, minute=0, second=0, microsecond=0)
ESKI = datetime(2026, 11, 20, 9, tzinfo=TR)    # yeni biçim tarihinden önce
YENI = datetime(2026, 11, 24, 9, tzinfo=TR)    # yeni biçim tarihinden sonra


def setUpModule():
    """Testler depodaki sosyal/ayar.json'a (ajanın kararlarına) bağlı kalmasın: varsayılan ayarlarla koşar."""
    import sosyal_ajan
    global _ESKI_AYAR, _GERCEK_TARIH
    _ESKI_AYAR = sosyal_ajan.AYAR_YOLU
    sosyal_ajan.AYAR_YOLU = Path(__file__).with_name('yok-ayar.json')
    # Eski biçim testleri saate bağlı kalmasın (zaman_kontrol.py ileri tarihte de koşar): yeni biçim kapalı; açanlar kendi açar.
    _GERCEK_TARIH = reels.YENI_BICIM_TARIHI
    reels.YENI_BICIM_TARIHI = date(2099, 1, 1)


def tearDownModule():
    import sosyal_ajan
    sosyal_ajan.AYAR_YOLU = _ESKI_AYAR
    reels.YENI_BICIM_TARIHI = _GERCEK_TARIH


def ilan(kimlik, gun, kadro='Toplam 12 kişi — 10 Memur • 2 Tekniker', kurum='Deneme Kurumu Başkanlığı', gorulme=0, ref=None, **ek):
    ref = ref or SIMDI
    return {'id': kimlik, 'kurum': kurum, 'kadro': kadro, 'ogrenim': ['lisans'], 'kpss': 'kpss', 'iller': ['Ankara'],
            'son_tarih': (ref + timedelta(days=gun)).date().isoformat(),
            'ilk_gorulme': (ref - timedelta(days=gorulme)).isoformat(timespec='seconds'), **ek}


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

    def test_ilk_kare_kapaktir(self):
        # Platformlar önizleme olarak ilk kareyi alır: ilk sahne boş zeminden değil, yerine oturmuş başlamalı.
        for sahneler in (reels.ilan_videosu(ilan('a', 5), SIMDI),
                         reels.son_gun_videosu([ilan('a', 0), ilan('b', 1)], 2, SIMDI)):
            govde = (0, reels.UST, reels.VW, reels.VH)   # üstteki ilerleme şeridi kareden kareye değişir
            uretec = reels.kareler(sahneler)
            ilk = next(uretec)
            oturmus = reels.kare(sahneler, sahneler[0].sure - reels.CIKIS - 0.05)
            self.assertNotEqual(ilk.crop(govde).tobytes(), reels.zemin().crop(govde).tobytes())
            self.assertEqual(ilk.crop(govde).tobytes(), oturmus.crop(govde).tobytes())
            # ikinci sahne hareketli girmeye devam eder: ilk karesi oturmuş hâlinden farklıdır
            for _ in range(int(reels.FPS * sahneler[0].sure) - 1):
                next(uretec)
            ikinci_ilk = next(uretec)
            ikinci_oturmus = reels.kare(sahneler, sahneler[0].sure + sahneler[1].sure - reels.CIKIS - 0.05)
            self.assertNotEqual(ikinci_ilk.crop(govde).tobytes(), ikinci_oturmus.crop(govde).tobytes())


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
            ozel = reels.OZEL_MUZIK_KLASORU   # depoya kullanıcı parçası (ör. sabah.mp3) eklenirse test bozulmasın
            reels.OZEL_MUZIK_KLASORU = Path(g) / 'ozel-yok'
            self.addCleanup(setattr, reels, 'OZEL_MUZIK_KLASORU', ozel)
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


UZUN_KURUM = 'Çok Uzun Adlı Büyükşehir Belediyesi Başkanlığı Fen İşleri ve Teknik Hizmetler Müdürlüğü'
UZUN_KADRO = 'Toplam 1250 kişi — 1250 Bilgisayar İşletmeni Teknik Destek Uzmanı Yardımcısı'


def zabita(n, ref=YENI, adet=5, **ek):
    return ilan(f'zabita{n}', 20 + n, f'Toplam {adet} kişi — {adet} Zabıta Memuru', f'Belediye {n} Başkanlığı', ref=ref, **ek)


def tasan(sahneler):
    """Sahnelerdeki her katmanın sağ kenarı güvenli alanda (x <= 1008) ve alt kenarı ALT'ı aşmıyor."""
    for sahne in sahneler:
        for o in sahne.ogeler:
            if isinstance(o, reels.Oge):
                yield o.x + o.katman.width, o.y + o.katman.height
            elif isinstance(o, reels.Sayac):
                yield o.x + round(reels._OLC.textlength(reels.binlik(o.hedef), font=reels.F(o.boy, True))), o.y + round(o.boy * 1.1)


class YeniBicimTest(unittest.TestCase):
    """23 Kasım 2026'dan sonraki üç biçim: kimler (tek ilan), meslek (akşam), düzey (sabah, geri sayım)."""

    def setUp(self):
        reels.YENI_BICIM_TARIHI = date(2026, 11, 23)
        eski = reels.R.ad
        self.addCleanup(reels.palet_sec, eski)
        self.addCleanup(setattr, reels, 'YENI_BICIM_TARIHI', date(2099, 1, 1))
        reels.palet_sec('sari')

    def kapak_dolu(self, sahneler):
        govde = (0, reels.UST, reels.VW, reels.VH)
        ilk = next(reels.kareler(sahneler))
        oturmus = reels.kare(sahneler, sahneler[0].sure - reels.CIKIS - 0.05)
        self.assertNotEqual(ilk.crop(govde).tobytes(), reels.zemin().crop(govde).tobytes())
        self.assertEqual(ilk.crop(govde).tobytes(), oturmus.crop(govde).tobytes())
        self.assertTrue(sahneler[-1].son)
        self.assertLessEqual(reels.video_suresi(sahneler), 25)
        for sag, alt in tasan(sahneler):
            self.assertLessEqual(sag, reels.SAG + 4)
            self.assertLessEqual(alt, reels.ALT + 4)

    def test_kapi_tarihi_ve_palet(self):
        self.assertEqual(_GERCEK_TARIH, date(2026, 11, 23))
        self.assertEqual([reels.bicim_paleti(v, YENI) for v in ('ilan', 'aksam', 'sabah')], ['sari', 'indigo', 'karmin'])
        self.assertEqual([reels.bicim_paleti(v, ESKI) for v in ('ilan', 'aksam', 'sabah')], [None, None, None])
        self.assertIsNone(reels.bicim_paleti('haftalik', YENI))
        self.assertEqual(reels.bicim_paleti('ilan', datetime(2026, 11, 23, 0, 5, tzinfo=TR)), 'sari')
        self.assertEqual(reels.PALET_SIRASI, ('kagit', 'bordo'))   # yeni paletler sıraya girmez
        for ad in ('sari', 'indigo', 'karmin'):
            self.assertIn(ad, reels.PALETLER)

    def test_gunluk_tarihten_once_eski_sonra_yeni(self):
        zabitalar = lambda ref: [zabita(n, ref) for n in range(3)]
        for ref, ilan_tur, aksam_tur, sabah_tur in ((ESKI, 'ilan', 'ozet', 'son_gun'), (YENI, 'kimler', 'meslek', 'duzey')):
            acik = [ilan('a', 1, ref=ref)] + zabitalar(ref)
            self.assertEqual(reels.gunluk('ilan', acik, ref)['tur'], ilan_tur)
            self.assertEqual(reels.gunluk('aksam', acik, ref)['tur'], aksam_tur)
            self.assertEqual(reels.gunluk('sabah', acik, ref)['tur'], sabah_tur)
        konu = reels.gunluk('ilan', [ilan('a', 5, ref=YENI)], YENI)
        self.assertEqual((konu['tur'], konu['muzik'], konu['anahtar'], konu['ilanlar']), ('kimler', 'kimler', 'ilan:a', ['a']))
        self.assertEqual(konu['baslik'], 'Deneme Kurumu 12 Personel Alımı 2026: Kimler Başvurabilir?')   # 10 memur + 2 tekniker
        self.assertEqual(len(konu['etiketler']), 3)
        self.assertTrue(konu['satirlar'][0].startswith('• Deneme Kurumu: '))
        konu = reels.gunluk('aksam', [zabita(n) for n in range(3)], YENI)
        self.assertEqual((konu['tur'], konu['muzik'], konu['anahtar'], konu['baslik']),
                         ('meslek', 'meslek', 'meslek:zabita memuru', '2026 Zabıta Memuru Alımları: 15 Kadro'))
        self.assertEqual(len(konu['ilanlar']), 3)
        self.assertEqual(konu['etiketler'][2], '#zabitamemuru')
        konu = reels.gunluk('sabah', [ilan(str(n), 9, ref=YENI) for n in range(3)], YENI)
        self.assertEqual((konu['tur'], konu['muzik'], konu['anahtar']), ('duzey', 'duzey', 'duzey:lisans:2026-11-24'))
        self.assertEqual(konu['baslik'], 'Lisans Mezunlarının Başvurabileceği Kamu İlanları (Kasım 2026)')

    def test_yeni_bicim_yoksa_eskiye_duser_ve_palet_eski_olur(self):
        # 2 zabıta ilanı meslek için az; bugün eklenen 2 ilan akşam özetine yeter
        konu = reels.gunluk('aksam', [zabita(0), zabita(1)], YENI)
        self.assertEqual(konu['tur'], 'ozet')
        self.assertIn(konu['palet'], reels.PALET_SIRASI)
        self.assertIn(reels.R.ad, reels.PALET_SIRASI)
        konu = reels.gunluk('sabah', [ilan('a', 1, ref=YENI)], YENI)
        self.assertEqual(konu['tur'], 'son_gun')
        self.assertIn(konu['palet'], reels.PALET_SIRASI)
        self.assertIsNone(reels.gunluk('ilan', [], YENI))
        # kimler tek ilan günlük sınırı eski 'ilan' kayıtlarını da sayar
        zaman = YENI.isoformat(timespec='seconds')
        dolu = [{'tur': 'kimler', 'zaman': zaman, 'ilanlar': [str(n)]} for n in range(reels.ILAN_GUNLUK)]
        self.assertIsNone(reels.siradaki_ilan([ilan('a', 5, ref=YENI)], YENI, dolu))
        self.assertEqual(reels.siradaki_ilan([ilan('a', 5, ref=YENI)], YENI, [{'tur': 'kimler', 'zaman': zaman, 'ilanlar': ['x']}])['id'], 'a')
        self.assertIsNone(reels.siradaki_ilan([ilan('a', 5, ref=YENI)], YENI, [{'tur': 'kimler', 'zaman': zaman, 'ilanlar': ['a']}]))

    def test_kimler_kapagi_ve_hap(self):
        a = ilan('a', 3, ref=YENI, ogrenim=['lisans'], puan_turleri=['P3', 'P93'],
                 sartlar=[{'metin': 'Sınav tarihinde otuz beş yaşını doldurmamış olmak'}],
                 ozet='Başvurular e-Devlet üzerinden Kariyer Kapısı ile alınır.', baslangic_zaman=(YENI - timedelta(days=5)).isoformat())
        sahneler = reels.kimler_videosu(a, YENI)
        self.assertEqual(len(sahneler), 3)
        self.assertEqual([s.sure for s in sahneler], [2.7, 3.0, 3.4])
        self.kapak_dolu(sahneler)
        bitis = YENI + timedelta(days=3)
        self.assertEqual(reels._kimler_hapi(a, YENI), f'SON BAŞVURU {bitis.day} {reels.k.tr_buyuk(reels.AYLAR[bitis.month - 1])} · 3 GÜN KALDI')
        self.assertEqual(reels._kimler_hapi(ilan('b', 0, ref=YENI), YENI), 'BUGÜN SON GÜN')
        self.assertEqual(reels._kimler_hapi(ilan('b', 40, ref=YENI), YENI), 'YENİ İLAN')
        gelecek = ilan('b', 40, ref=YENI, baslangic_zaman=(YENI + timedelta(days=2)).isoformat())
        self.assertRegex(reels._kimler_hapi(gelecek, YENI), r'^BAŞVURU \d+ [A-ZÇĞİÖŞÜ]+ – \d+ [A-ZÇĞİÖŞÜ]+$')
        sgk = ilan('s', 3, '100 SOSYAL GÜVENLİK DENETMEN YARDIMCISI ALACAK', 'SOSYAL GÜVENLİK KURUMU BAŞKANLIĞI', ref=YENI)
        self.kapak_dolu(reels.kimler_videosu(sgk, YENI))
        self.assertEqual(reels.basvuru_sekli(a), 'e-Devlet · Kariyer Kapısı')
        self.assertEqual(reels.basvuru_sekli({'ozet': 'Başvurular şahsen yapılır'}), 'Şahsen, belgelerle')
        self.assertEqual(reels.basvuru_sekli({'basvuru_notu': 'Evrak posta ile gönderilir'}), 'Posta ile')
        self.assertEqual(reels.basvuru_sekli({'ozet': 'yok'}), '')
        # koşul yoksa ikinci sahne düşer; sayı ve kadro adı yoksa video yok
        self.assertEqual(len(reels.kimler_videosu(ilan('c', 5, 'Toplam 5 kişi — 5 Memur', ref=YENI, ogrenim=[], kpss=None, iller=[]), YENI)), 2)
        self.assertIsNone(reels.kimler_videosu(ilan('d', 5, 'Alacak', ref=YENI), YENI))

    def test_basvuru_sekli_reddedilen_yolu_yazmaz(self):
        sekil = lambda m: reels.basvuru_sekli({'ozet': m})
        self.assertEqual(sekil('Son başvuru 25 Kasım. 3. Şahsen, posta veya diğer yollarla yapılan başvurular kabul edilmeyecektir.'), '')
        self.assertEqual(sekil('Posta ile veya diğer şekillerde yapılan müracaatlar kabul edilmez.'), '')
        self.assertEqual(sekil('Kariyer sayfasından başvurulabilecek olup, şahsen veya posta, faks ve email vb. yoluyla yapılan '
                               'başvurular kabul edilmeyecektir.'), '')
        self.assertEqual(sekil('Şahsen başvuru alınmayacak olup posta ile yapılan başvurular kabul edilmeyecektir.'), '')
        self.assertEqual(sekil('Başvurular e-posta ile yapılır.'), 'E-posta ile')
        self.assertEqual(sekil("Başvurular 30 Kasım'da e-postayla yapılır."), 'E-posta ile')
        self.assertEqual(sekil('Başvurular e-posta, şahsen veya posta ile yapılır.'), 'Şahsen, e-posta veya posta ile')
        self.assertEqual(sekil('Belediyeye şahsen başvurulur. Posta, e-posta veya form yoluyla başvuru kabul edilmez.'), 'Şahsen, belgelerle')
        self.assertEqual(sekil('Başvurular Kariyer Kapısı üzerinden yapılır. İtirazlar dilekçe ile şahsen veya posta yoluyla yapılır.'),
                         'e-Devlet · Kariyer Kapısı')
        self.assertEqual(sekil('Kariyer sayfasından başvurulur, şahsen yapılan başvurular kabul edilmeyecektir. Diploma (e-Devlet kapısından '
                               'alınan barkodlu belge) yüklenir.'), '')

    def test_kimler_basligi_toplami_tek_kadroya_yazmaz(self):
        veri = lambda kadro: reels.k.veri(ilan('a', 5, kadro, ref=YENI), None, YENI)
        self.assertEqual(reels._baslik_kadro(veri('Toplam 8 kişi — 1 Yazılım Mimarı • 7 Siber Güvenlik Uzmanı')), 'Personel')
        self.assertEqual(reels._baslik_kadro(veri('Toplam 90 kişi — 72 Zabıta Memuru — Erkek (Spor) • 18 Zabıta Memuru (Kadın)')), 'Zabıta Memuru')
        self.assertEqual(reels._baslik_kadro(veri('Toplam 9 kişi — 9 Sözleşmeli Programcı (Lisans)')), 'Sözleşmeli Programcı')
        self.assertEqual(reels._baslik_kadro(veri('Alacak')), '')
        konu = reels.gunluk('ilan', [ilan('n', 5, 'Toplam 8 kişi — 1 Yazılım Mimarı • 7 Siber Güvenlik Uzmanı', ref=YENI)], YENI)
        self.assertEqual(konu['baslik'], 'Deneme Kurumu 8 Personel Alımı 2026: Kimler Başvurabilir?')
        uzun_ad = 'Türk Silahlı Kuvvetlerine Fakülte veya Yüksekokul Mezunlarından Muvazzaf Astsubay Adayı Temini'
        konu = reels.gunluk('ilan', [ilan('m', 5, f'Toplam 40 kişi — 40 {uzun_ad}', ref=YENI)], YENI)
        self.assertEqual(konu['baslik'], 'Deneme Kurumu 40 Personel Alımı 2026: Kimler Başvurabilir?')
        # sığmayan kadro adı kelime kelime kesilmez ('PERSONEL' yazılır); kapak yine güvenli alanda
        uzun = ilan('u', 5, 'Toplam 3 kişi — 3 Bilgisayar İşletmeni Teknik Destek Uzmanı Yardımcısı Koordinatörü Sorumlusu', UZUN_KURUM, ref=YENI)
        self.kapak_dolu(reels.kimler_videosu(uzun, YENI))

    def test_yeni_bicim_hatasi_eski_sablona_duser(self):
        eski = reels._yeni_konu
        reels._yeni_konu = lambda *a: 1 / 0
        self.addCleanup(setattr, reels, '_yeni_konu', eski)
        konu = reels.gunluk('sabah', [ilan('a', 1, ref=YENI)], YENI)
        self.assertEqual(konu['tur'], 'son_gun')
        self.assertIn(konu['palet'], reels.PALET_SIRASI)

    def test_kurum_adi_yoksa_yeni_bicim_hata_vermez(self):
        adsiz = [zabita(n) for n in range(3)]
        for i in adsiz:
            i['kurum'], i['id'] = '', 'adsiz' + i['id']
        self.assertIsNone(reels.kimler_videosu(adsiz[0], YENI))
        self.assertIsNone(reels.meslek_videosu(adsiz, YENI))
        self.assertIsNone(reels.duzey_videosu(adsiz, YENI))
        self.assertEqual(sorted(reels.meslek_sec(adsiz + [zabita(n) for n in range(3)], YENI)[2]), ['zabita0', 'zabita1', 'zabita2'])

    def test_yas_ayristirici(self):
        yas = lambda m: reels.yas_sarti({'sartlar': [{'metin': m}]})
        self.assertEqual(yas('b) Sınav tarihi itibarıyla 35 (otuz beş) yaşını doldurma mış olmak.'), 35)
        self.assertEqual(yas('otuz beş yaşını doldurmamış olmak'), 35)
        self.assertEqual(yas('Otuz Beş (35) yaşını doldurmamış olmak'), 35)
        self.assertEqual(yas('30 yaşını doldurmamış olmak'), 30)
        self.assertEqual(yas('kırk yaşını doldurmamış'), 40)
        self.assertEqual(yas('yirmi yedi yaşını doldurmamış'), 27)
        self.assertIsNone(yas('yaş şartı aranmaz'))
        self.assertIsNone(reels.yas_sarti({}))

    def test_meslek_gruplama_ve_yedi_gun_atlama(self):
        acik = [zabita(0), zabita(1, adet=7), zabita(2), ilan('x', 9, 'Toplam 40 kişi — 40 Memur', ref=YENI),
                ilan('k1', 9, 'Toplam 30 kişi — 30 Mühendis', ref=YENI), ilan('k2', 9, 'Toplam 3 kişi — 3 Mühendis', ref=YENI)]
        g = reels.meslek_grubu_sec(acik, YENI)
        self.assertEqual((g['anahtar'], g['toplam'], len(g['ilanlar'])), ('zabita memuru', 17, 3))   # 'Memur' genel ad sayılmaz; mühendis 2 ilan
        self.assertEqual(g['ilanlar'][0][0]['id'], 'zabita1')                                         # kadro sayısı çoktan aza
        sahneler, anahtar, kimlikler = reels.meslek_sec(acik, YENI, [])
        self.assertEqual((anahtar, sorted(kimlikler)), ('zabita memuru', ['zabita0', 'zabita1', 'zabita2']))
        self.assertEqual(len(sahneler), 1 + 1 + 1 + 1)   # kapak, liste, en büyüğü, kapanış
        self.kapak_dolu(sahneler)
        dun = [{'anahtar': 'meslek:zabita memuru', 'zaman': (YENI - timedelta(days=6)).isoformat(timespec='seconds')}]
        self.assertIsNone(reels.meslek_sec(acik, YENI, dun))            # 7 gün dolmadı; başka uygun meslek yok
        eski = [{'anahtar': 'meslek:zabita memuru', 'zaman': (YENI - timedelta(days=8)).isoformat(timespec='seconds')}]
        self.assertEqual(reels.meslek_sec(acik, YENI, eski)[1], 'zabita memuru')
        acik += [ilan(f'm{n}', 9, 'Toplam 6 kişi — 6 Mühendis', ref=YENI) for n in range(2)]   # mühendis: 4 ilan, 45 kadro
        self.assertEqual(reels.meslek_sec(acik, YENI, dun)[1], 'muhendis')
        self.assertEqual(reels.meslek_grubu_sec(acik, YENI)['anahtar'], 'muhendis')                 # çok kadro kazanır
        self.assertIsNone(reels.meslek_videosu([zabita(0), zabita(1)], YENI))                       # en az 3 ilan
        self.assertIsNone(reels.meslek_videosu([zabita(n, adet=2) for n in range(3)], YENI))        # en az 10 kadro
        self.assertEqual(reels.meslek_anahtari('Zabıta Memuru Alacak'), 'zabita memuru')
        self.assertEqual(reels.meslek_anahtari('İtfaiye Eri'), 'itfaiye eri')
        self.assertIsNone(reels.meslek_anahtari('Sürekli İşçi'))

    def test_meslek_cinsiyet_ayrimi_ayni_grup(self):
        izmir = ilan('izmir', 20, 'Toplam 90 kişi — 72 Zabıta Memuru (Erkek) • 18 Zabıta Memuru (Kadın)', 'İzmir Büyükşehir Belediyesi', ref=YENI)
        acik = [izmir, zabita(1, adet=3), zabita(2, adet=3)]
        g = reels.meslek_grubu_sec(acik, YENI)
        self.assertEqual((g['anahtar'], g['toplam'], len(g['ilanlar'])), ('zabita memuru', 96, 3))
        self.assertEqual((g['ilanlar'][0][0]['id'], g['ilanlar'][0][1]), ('izmir', 90))
        self.assertEqual(reels.meslek_anahtari('Zabıta Memuru Kadın'), 'zabita memuru')
        self.assertEqual(reels.meslek_anahtari('Hemşire (Lisans)'), 'hemsire')
        self.kapak_dolu(reels.meslek_sec(acik, YENI)[0])

    def test_meslek_fazla_ilan_iki_sahneye_boler(self):
        acik = [zabita(n, adet=3 + n) for n in range(13)]
        sahneler, _, kimlikler = reels.meslek_sec(acik, YENI, [])
        self.assertEqual((len(sahneler), len(kimlikler)), (1 + 2 + 1 + 1, 10))   # kapak, 2 liste, en büyüğü, kapanış
        self.kapak_dolu(sahneler)

    def test_duzey_donusumu_ve_geri_donus(self):
        def ilanlar(duzey, n, ref):
            return [ilan(f'{duzey}{m}', 9, f'Toplam {m + 1} kişi — {m + 1} Memur', ref=ref, ogrenim=[duzey]) for m in range(n)]
        for gun in range(3):
            ref = YENI + timedelta(days=gun)
            acik = ilanlar('ortaogretim', 3, ref) + ilanlar('onlisans', 4, ref) + ilanlar('lisans', 8, ref)
            beklenen = reels.DUZEY_SIRA[ref.toordinal() % 3]
            duzey, secilen = reels.duzey_sec(acik, ref)
            self.assertEqual(duzey, beklenen)
        # en çok 6 ilan, kadro sayısına göre; video küçükten büyüğe
        duzey, secilen = reels.duzey_sec(ilanlar('lisans', 8, YENI), YENI)
        self.assertEqual((duzey, [i['id'] for i in secilen]), ('lisans', [f'lisans{m}' for m in (7, 6, 5, 4, 3, 2)]))
        reels.palet_sec('karmin')
        sahneler = reels.duzey_videosu(ilanlar('lisans', 8, YENI), YENI)
        self.assertEqual((len(sahneler), [s.sure for s in sahneler[1:-1]]), (1 + 6 + 1, [1.5] * 6))
        self.kapak_dolu(sahneler)
        # düzeyi 3'ten az olan atlanır; hiçbiri yoksa None
        self.assertEqual(reels.duzey_sec(ilanlar('onlisans', 3, YENI) + ilanlar('lisans', 2, YENI), YENI)[0], 'onlisans')
        self.assertIsNone(reels.duzey_videosu(ilanlar('lisans', 2, YENI) + ilanlar('onlisans', 2, YENI), YENI))
        # kadro sayısı bilinmeyen ilanda kadro adı büyük yazılır
        belirsiz = [ilan(f'b{m}', 9, 'Alacak', ref=YENI, ogrenim=['lisans'], baslik='Duyuru') for m in range(3)]
        self.assertEqual(len(reels.duzey_videosu(belirsiz, YENI)), 1 + 3 + 1)

    def test_uzun_adlarda_tasma_yok(self):
        for ad in ('sari', 'indigo', 'karmin'):
            reels.palet_sec(ad)
            uzun = ilan('u', 3, UZUN_KADRO, UZUN_KURUM, ref=YENI, puan_turleri=['P3', 'P93', 'P94', 'P95', 'P96', 'P97'],
                        baslangic_zaman=(YENI + timedelta(days=2)).isoformat(),
                        ozet='e-Devlet', sartlar=[{'metin': 'otuz beş yaşını doldurmamış'}], ogrenim=['ortaogretim', 'onlisans', 'lisans'])
            self.kapak_dolu(reels.kimler_videosu(uzun, YENI))
            meslek = [ilan(f'z{n}', 9, UZUN_KADRO, UZUN_KURUM + f' {n}', ref=YENI) for n in range(4)]
            self.kapak_dolu(reels.meslek_videosu(meslek, YENI))
            self.kapak_dolu(reels.duzey_videosu([ilan(f'd{n}', 9, UZUN_KADRO, UZUN_KURUM, ref=YENI, ogrenim=['lisans']) for n in range(6)], YENI))
        # sığmayan tek kelime bile hata vermez (video ya sığar ya da hiç üretilmez)
        reels.palet_sec('sari')
        sahneler = reels.kimler_videosu(ilan('v', 3, 'Toplam 5 kişi — 5 Bilgisayarprogramcılığıveteknikdestekuzmanlığı', 'Kısa Kurum', ref=YENI), YENI)
        if sahneler:
            self.kapak_dolu(sahneler)

    def test_ozel_muzik_once_gelir(self):
        import tempfile
        eski = reels.OZEL_MUZIK_KLASORU
        with tempfile.TemporaryDirectory() as g:
            reels.OZEL_MUZIK_KLASORU = Path(g) / 'ozel'
            self.addCleanup(setattr, reels, 'OZEL_MUZIK_KLASORU', eski)
            (Path(g) / 'ozel').mkdir()
            (Path(g) / 'onbellek').mkdir()
            dosya, bas = reels.MUZIK['ilan']
            (Path(g) / 'onbellek' / dosya).write_bytes(b'ID3' + b'0' * 200_000)
            self.assertEqual(reels.muzik_yolu('kimler', Path(g) / 'onbellek'), (Path(g) / 'onbellek' / dosya, bas))   # özel yok: eski parça
            (Path(g) / 'ozel' / 'kimler.mp3').write_bytes(b'ID3' + b'0' * 10_000)
            self.assertEqual(reels.muzik_yolu('kimler', Path(g) / 'onbellek')[0], Path(g) / 'onbellek' / dosya)        # 50 KB altı sayılmaz
            (Path(g) / 'ozel' / 'kimler.mp3').write_bytes(b'ID3' + b'0' * 80_000)
            self.assertEqual(reels.muzik_yolu('kimler', Path(g) / 'onbellek'), (Path(g) / 'ozel' / 'kimler.mp3', 0.0))
            self.assertEqual(reels.muzik_yolu('meslek', Path(g) / 'onbellek')[0], Path(g) / 'onbellek' / dosya)        # tür başına ayrı
        self.assertEqual((reels.MUZIK['kimler'], reels.MUZIK['meslek'], reels.MUZIK['duzey']), (reels.MUZIK['ilan'], reels.MUZIK['ilan'], reels.MUZIK['sabah']))
        self.assertTrue((reels.ROOT / 'sosyal' / 'muzik' / 'ozel' / 'README.md').is_file())

    def test_sablon_uret_yeni_bicim_ve_soru(self):
        import json
        import tempfile
        import sosyal_motor as sm
        konu = reels.gunluk('ilan', [ilan('a', 5, ref=YENI)], YENI)
        eski = reels.muzik_yolu
        reels.muzik_yolu = lambda tur, *a, **k: (None, 0.0)
        try:
            with tempfile.TemporaryDirectory() as g:
                sm.sablon_uret(konu, 'ilan', Path(g) / 'cikti', YENI, [], Path(g) / 'gecmis.json', video=False, palet='sari')
                kayit = json.loads((Path(g) / 'cikti' / 'paylasim.json').read_text(encoding='utf-8'))
                gecmis = json.loads((Path(g) / 'gecmis.json').read_text(encoding='utf-8'))
        finally:
            reels.muzik_yolu = eski
        self.assertEqual((kayit['tur'], kayit['palet'], gecmis[-1]['tur'], gecmis[-1]['anahtar']), ('kimler', 'sari', 'kimler', 'ilan:a'))
        self.assertIn(kayit['soru'], sm.SORULAR['kimler'])
        for tur in ('kimler', 'meslek', 'duzey'):
            self.assertEqual(len(sm.SORULAR[tur]), 2)


if __name__ == '__main__':
    unittest.main()
