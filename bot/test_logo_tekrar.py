import contextlib
import io
import unittest

import ilan_bot


def ilan(kimlik, kurum='Kıyı Emniyeti Genel Müdürlüğü', son='2026-10-23', kadro='3 Sürekli İşçi, 5 Engelli İşçi'):
    return {'id': kimlik, 'baslik': f'{kurum} alımı', 'kurum': kurum, 'son_tarih': son, 'kadro': kadro}


class Logo(unittest.TestCase):
    def test_logosuz_ilan_siradan_ayiklanir_duyuru_kalir(self):
        a, b, d = ilan('a'), ilan('b', kurum='Logosuz Belediyesi'), dict(ilan('d'), duyuru_turu='iptal')
        with contextlib.redirect_stdout(io.StringIO()) as cikti:
            kalan = ilan_bot.logolu_olanlar([a, b, d], logo_bul=lambda i: None if 'Logosuz' in i['kurum'] else b'png')
        self.assertEqual([i['id'] for i in kalan], ['a', 'd'])
        self.assertIn('Logosuz Belediyesi', cikti.getvalue())

    def test_logo_hatasi_logosuz_sayilir(self):
        def patlar(_):
            raise OSError('ağ')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ilan_bot.logolu_olanlar([ilan('a')], logo_bul=patlar), [])


class Tekrar(unittest.TestCase):
    def test_ayni_ilan_baska_kimlikle_tekrar_paylasilmaz(self):
        eski, yeni = ilan('sbb-1'), ilan('kk-2')
        mevcut = {'sbb-1': eski, 'kk-2': yeni}
        gonderilen, bekleyen = {'sbb-1'}, {'kk-2'}
        with contextlib.redirect_stdout(io.StringIO()):
            kalan = ilan_bot.tekrarlari_ele([yeni], mevcut, gonderilen, bekleyen)
        self.assertEqual(kalan, [])
        self.assertIn('kk-2', gonderilen)
        self.assertNotIn('kk-2', bekleyen)

    def test_farkli_ilanlar_gecer(self):
        eski = ilan('sbb-1')
        mevcut = {'sbb-1': eski}
        for yeni in (ilan('x', son='2026-10-30'),                         # başka son tarih
                     ilan('y', kadro='2 Sürekli İşçi'),                   # başka kişi sayısı
                     ilan('z', kadro='3 Zabıta Memuru, 5 İtfaiye Eri'),   # aynı sayı, ortak unvan yok
                     ilan('w', kurum='Başka Kurum')):
            mevcut[yeni['id']] = yeni
            self.assertIsNone(ilan_bot.onceden_paylasilmis(yeni, mevcut, {'sbb-1'}), yeni['id'])

    def test_kisi_sayisi_yoksa_basliga_bakilir(self):
        msb = 'MİLLİ SAVUNMA BAKANLIĞI'
        tabip = {'id': 't1', 'kurum': msb, 'son_tarih': '2026-10-20',
                 'baslik': f'{msb} - 2026 YILI TABİP, DİŞ TABİBİ SINIFI MUVAZZAF SUBAY ADAYI TEMİNİ'}
        tabip2 = dict(tabip, id='t2', baslik=tabip['baslik'] + ' İLANI')
        msu = dict(tabip, id='m1', baslik=f'{msb} - 2026 YILI MİLLÎ SAVUNMA ÜNİVERSİTESİNE ÖĞRETMEN/MÜHENDİS SINIFI ALIMI')
        genel = dict(tabip, id='g1', baslik=f'{msb} - PERSONEL ALIM İLANI')
        self.assertTrue(ilan_bot.ayni_ilan_mi(tabip, tabip2))
        self.assertFalse(ilan_bot.ayni_ilan_mi(tabip, msu))
        self.assertTrue(ilan_bot.ayni_ilan_mi(genel, msu))

    def test_gonderilmemis_kayit_engel_olmaz(self):
        eski, yeni = ilan('sbb-1'), ilan('kk-2')
        self.assertIsNone(ilan_bot.onceden_paylasilmis(yeni, {'sbb-1': eski, 'kk-2': yeni}, set()))


class Dugmeler(unittest.TestCase):
    def test_kibar_kisaltmalar(self):
        beklenen = {'Kamu Gözetimi, Muhasebe ve Denetim Standartları Kurumu Başkanlığı': 'KGK',
                    'Türkiye İş Kurumu Genel Müdürlüğü': 'İŞKUR', 'Orta Anadolu Kalkınma Ajansı': 'ORAN',
                    'Doğanyol Belediye Başkanlığı': 'Doğanyol Bld.', 'Edirne Uzunköprü Belediyesi': 'Uzunköprü Bld.',
                    'Subaşı (YALOVA) Belediye Başkanlığı': 'Subaşı Bld.', 'Yüksek Seçim Kurulu Başkanlığı': 'YSK',
                    'Gençlik ve Spor Bakanlığı': 'GSB', 'Niğde Ömer Halisdemir Üniversitesi Rektörlüğü': 'NÖHÜ'}
        for kurum, kisa in beklenen.items():
            self.assertEqual(ilan_bot.dugme_kisalt(ilan_bot.dugme_kurumu(kurum)), kisa, kurum)
        self.assertLessEqual(len(ilan_bot.dugme_kisalt('Çok Uzun Bir Kurum Adı Sözcükleri Burada')), ilan_bot.DUGME_EN_UZUN + 1)

    def test_ikiser_yan_yana(self):
        from unittest import mock
        gonderilen = {}

        class Yanit(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def ac(istek, timeout=None):
            import urllib.parse
            gonderilen.update(urllib.parse.parse_qs(istek.data.decode()))
            return Yanit(b'{"ok": true, "result": {"message_id": 5}}')

        with mock.patch.object(ilan_bot.urllib.request, 'urlopen', ac):
            ilan_bot.telegram_gonder('t', 'c', 'metin', site_url='https://kpsstercihi.com/',
                                     ek_dugmeler=[(f'K{n}', f'https://kpsstercihi.com/ilan/{n}/') for n in range(5)])
        satirlar = __import__('json').loads(gonderilen['reply_markup'][0])['inline_keyboard']
        self.assertEqual([len(s) for s in satirlar], [2, 2, 2])
        self.assertEqual(satirlar[-1][1]['text'], '🌐 Tüm ilanlar')


if __name__ == '__main__':
    unittest.main()
