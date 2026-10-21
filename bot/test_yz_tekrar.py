import contextlib
import io
import json
import unittest
from datetime import datetime, timedelta

import ilan_bot
import yz_tekrar

TR = ilan_bot.TR
SIMDI = datetime(2026, 10, 21, 12, 0, tzinfo=TR)


def ilan(kimlik, kurum, kadro='', baslik=None, son='2026-10-26', **ek):
    return dict({'id': kimlik, 'kurum': kurum, 'kadro': kadro, 'baslik': baslik or f'{kurum} - {kadro}', 'son_tarih': son,
                 'ilk_gorulme': (SIMDI - timedelta(hours=5)).isoformat(), 'link': 'https://kamuilan.sbb.gov.tr/'}, **ek)


TCDD_SBB = ilan('sbb-1', 'DEVLET DEMİRYOLLARI TAŞIMACILIK A.Ş GENEL MÜDÜRLÜĞÜ', '166 SüREKLİ İŞÇİ ALACAK')
TCDD_KK = ilan('kk-1', 'TÜRKİYE CUMHURİYETİ DEVLET DEMİRYOLLARI TAŞIMACILIK ANONİM ŞİRKETİ GENEL MÜDÜRLÜĞÜ',
               baslik='TÜRKİYE CUMHURİYETİ DEVLET DEMİRYOLLARI TAŞIMACILIK ANONİM ŞİRKETİ GENEL MÜDÜRLÜĞÜ - 166 SÜREKLİ İŞÇİ İSTİHDAMI')
POSOF_TEKNISYEN = ilan('p1', 'POSOF BELEDİYE BAŞKANLIĞI', '1 Teknisyen')
POSOF_COZUMLEYICI = ilan('p2', 'POSOF BELEDİYE BAŞKANLIĞI', '1 Çözümleyici')


def cevap(ayni, guven, neden='x'):
    return lambda model, govde, anahtar, zaman: {'candidates': [{'content': {'parts': [{'text': json.dumps(
        {'ayni': ayni, 'guven': guven, 'neden': neden})}]}}]}


class BotKarari(unittest.TestCase):
    def test_farkli_unvan_ya_da_gun_ya_da_kisi_farkli_ilan(self):
        self.assertEqual(ilan_bot.tekrar_karari(POSOF_TEKNISYEN, POSOF_COZUMLEYICI), 'farkli')   # kadro unvanı farklı
        self.assertEqual(ilan_bot.tekrar_karari(TCDD_SBB, dict(TCDD_KK, son_tarih='2026-10-27')), 'farkli')
        self.assertEqual(ilan_bot.tekrar_karari(ilan('a', 'X BELEDİYE BAŞKANLIĞI', '2 Memur'), ilan('b', 'X BELEDİYE BAŞKANLIĞI', '3 Memur')), 'farkli')

    def test_yazim_farkli_ayni_ilan(self):
        self.assertEqual(ilan_bot.tekrar_karari(TCDD_SBB, TCDD_KK), 'ayni')

    def test_belirsiz(self):
        a = ilan('a', 'ÖRNEK KURUMU GENEL MÜDÜRLÜĞÜ', baslik='ÖRNEK KURUMU GENEL MÜDÜRLÜĞÜ - SÖZLEŞMELİ BİLİŞİM PERSONELİ SINAV İLANI')
        b = ilan('b', 'ÖRNEK KURUMU', '1 Kıdemli Yazılım Mimarı')
        self.assertIn(ilan_bot.tekrar_karari(a, b), ('belirsiz', 'ayni'))


class SessizYutmaKorumasi(unittest.TestCase):
    """Bot yanlış 'aynı' derse gerçek ilan sessizce yutulur: bunun yolları kapalı olmalı."""

    def test_ozgul_ve_benzemeyen_basliklar_farkli(self):
        tabip = ilan('t', 'MİLLİ SAVUNMA BAKANLIĞI', baslik='MİLLİ SAVUNMA BAKANLIĞI - 2026 YILI TABİP, DİŞ TABİBİ SINIFI SÖZLEŞMELİ/MUVAZZAF SUBAY ADAYI TEMİNİ')
        uni = ilan('u', 'MİLLİ SAVUNMA BAKANLIĞI', baslik='MİLLİ SAVUNMA BAKANLIĞI - 2026 YILI MİLLÎ SAVUNMA ÜNİVERSİTESİNE ÖĞRETMEN/MÜHENDİS SINIFI MUVAZZAF SUBAY ADAYI')
        self.assertEqual(ilan_bot.tekrar_karari(tabip, uni), 'farkli')

    def test_genel_baslik_birden_cok_ilana_uyuyorsa_yutulmaz(self):
        genel = ilan('kk', 'ÖRNEK KURUMU', baslik='ÖRNEK KURUMU - PERSONEL ALIM İLANI')
        a = ilan('a', 'ÖRNEK KURUMU', '3 Mühendis')
        b = ilan('b', 'ÖRNEK KURUMU', '2 Şoför')
        mevcut = {'kk': genel, 'a': a, 'b': b}
        self.assertEqual(ilan_bot.onceden_paylasilmis(genel, mevcut, {'a'}), None)   # a mı b mi belli değil -> yayınla

    def test_genel_baslik_tek_ilana_uyuyorsa_tekrardir(self):
        genel = ilan('kk', 'ÖRNEK KURUMU', baslik='ÖRNEK KURUMU - PERSONEL ALIM İLANI')
        a = ilan('a', 'ÖRNEK KURUMU', '3 Mühendis')
        self.assertEqual(ilan_bot.onceden_paylasilmis(genel, {'kk': genel, 'a': a}, {'a'}), 'a')


class GroqAnaSaglayici(unittest.TestCase):
    def tearDown(self):
        yz_tekrar.ayarla(False)

    def test_groq_cevabi_kullanilir_gemini_sorulmaz(self):
        yz_tekrar.ayarla(True, 'groq-anahtar', 'gemini-anahtar')
        modeller = []

        def groq(model, istem, anahtar, zaman):
            modeller.append(model)
            return json.dumps({'ayni': True, 'guven': 0.96, 'neden': 'aynı kurum ve kadro'})

        def gemini_olmamali(*a):
            raise AssertionError('Groq cevap verdiğinde Gemini çağrılmamalı')
        sonuc = yz_tekrar.sor(TCDD_SBB, TCDD_KK, 166, None, iste=gemini_olmamali, groq_iste=groq)
        self.assertTrue(yz_tekrar.tutulsun_mu(sonuc))
        self.assertEqual(modeller, ['llama-3.3-70b-versatile'])

    def test_groq_hata_verirse_once_kucuk_model_sonra_gemini(self):
        import yz_denetim as yd
        yd._MODELLER[:] = ['m']
        yz_tekrar.ayarla(True, 'groq-anahtar', 'gemini-anahtar')
        denenen = []

        def groq(model, istem, anahtar, zaman):
            denenen.append(model)
            raise OSError('429')
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                sonuc = yz_tekrar.sor(TCDD_SBB, TCDD_KK, groq_iste=groq, iste=cevap(False, 0.8, 'farklı'))
        finally:
            yd._MODELLER[:] = []
        self.assertEqual(denenen, ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant'])
        self.assertFalse(sonuc['ayni'])   # Gemini yedeği cevap verdi

    def test_hicbiri_cevap_vermezse_none_ve_ilan_yayinlanir(self):
        import yz_denetim as yd
        yd._MODELLER[:] = ['m']
        yz_tekrar.ayarla(True, 'groq-anahtar', 'gemini-anahtar')

        def patlar(*a):
            raise OSError('503')
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(yz_tekrar.sor(TCDD_SBB, TCDD_KK, groq_iste=patlar, iste=patlar))
        finally:
            yd._MODELLER[:] = []
        self.assertFalse(yz_tekrar.tutulsun_mu(None))

    def test_yalniz_groq_anahtari_yeter_ve_anahtarsiz_kapali(self):
        yz_tekrar.ayarla(True, 'groq-anahtar', '')
        self.assertTrue(yz_tekrar.etkin())
        yz_tekrar.ayarla(True, '', '')
        self.assertFalse(yz_tekrar.etkin())

    def test_bozuk_json_yok_sayilir(self):
        yz_tekrar.ayarla(True, 'groq-anahtar', '')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(yz_tekrar.sor(TCDD_SBB, TCDD_KK, groq_iste=lambda *a: 'json değil'))


class GeminiIkinciGoz(unittest.TestCase):
    def setUp(self):
        import yz_denetim as yd
        self.yd = yd
        yd._MODELLER[:] = ['m']
        yz_tekrar.ayarla(True, '', 'anahtar')

    def tearDown(self):
        self.yd._MODELLER[:] = []
        yz_tekrar.ayarla(False)

    def test_tutulma_kurali(self):
        self.assertTrue(yz_tekrar.tutulsun_mu({'ayni': True, 'guven': 0.95}))
        self.assertFalse(yz_tekrar.tutulsun_mu({'ayni': True, 'guven': 0.7}))     # emin değil -> yayınla
        self.assertFalse(yz_tekrar.tutulsun_mu({'ayni': False, 'guven': 0.99}))
        self.assertFalse(yz_tekrar.tutulsun_mu(None))                              # hata/kota -> yayınla

    def test_sor_cevap_ve_hata(self):
        self.assertEqual(yz_tekrar.sor(TCDD_SBB, TCDD_KK, 166, None, iste=cevap(True, 0.97))['ayni'], True)

        def patlar(*a):
            raise OSError('503')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(yz_tekrar.sor(TCDD_SBB, TCDD_KK, iste=patlar))

    def test_cagri_siniri(self):
        for _ in range(yz_tekrar.CAGRI_SINIRI):
            yz_tekrar.sor(TCDD_SBB, TCDD_KK, iste=cevap(False, 0.5))
        self.assertFalse(yz_tekrar.etkin())

    def test_kapali_iken_sorulmaz(self):
        yz_tekrar.ayarla(False)
        self.assertFalse(yz_tekrar.etkin())

    def test_onceden_paylasilmis_gemini_ile(self):
        a = ilan('a', 'ÖRNEK KURUMU GENEL MÜDÜRLÜĞÜ', baslik='ÖRNEK KURUMU GENEL MÜDÜRLÜĞÜ - SÖZLEŞMELİ BİLİŞİM PERSONELİ SINAV İLANI')
        b = ilan('b', 'ÖRNEK KURUMU', '1 Kıdemli Yazılım Mimarı', gonderildi=True)
        if ilan_bot.tekrar_karari(a, b) != 'belirsiz':
            self.skipTest('bot bu çifti kendisi karara bağlıyor')
        mevcut, gonderilen = {'a': a, 'b': b}, {'b'}
        with contextlib.redirect_stdout(io.StringIO()):
            yz_tekrar.sor_orijinal = yz_tekrar.sor
            try:
                yz_tekrar.sor = lambda *x, **k: {'ayni': True, 'guven': 0.95, 'neden': 'aynı'}
                self.assertEqual(ilan_bot.onceden_paylasilmis(a, mevcut, gonderilen), 'b')
                yz_tekrar.ayarla(True, '', 'anahtar')
                yz_tekrar.sor = lambda *x, **k: {'ayni': True, 'guven': 0.6, 'neden': 'belki'}
                self.assertIsNone(ilan_bot.onceden_paylasilmis(a, mevcut, gonderilen))   # emin değil -> yayınla
                yz_tekrar.sor = lambda *x, **k: None
                self.assertIsNone(ilan_bot.onceden_paylasilmis(a, mevcut, gonderilen))   # hata -> yayınla
            finally:
                yz_tekrar.sor = yz_tekrar.sor_orijinal


if __name__ == '__main__':
    unittest.main()
