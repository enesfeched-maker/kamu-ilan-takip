"""Instagram yorumlarına site asistanıyla otomatik yanıt (ağ yok: tüm HTTP sahte)."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sosyal_ajan as sa
import sosyal_yayinla as sy
from site_uret import TR

SIMDI = datetime.now(TR).replace(microsecond=0)
ZAMAN = (SIMDI - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S%z')
GELECEK = (SIMDI + timedelta(days=10)).strftime('%Y-%m-%d')


def yorum(i, metin, kullanici='aday', **ek):
    return dict({'id': str(i), 'text': metin, 'username': kullanici, 'timestamp': ZAMAN}, **ek)


class Sahte:
    """_istek yerine geçer; gelen çağrıları kaydeder."""
    def __init__(self, yorumlar, tur='ilan', izin_yok=False, bizim='kpsstercihi'):
        self.yorumlar, self.tur, self.izin_yok, self.bizim = yorumlar, tur, izin_yok, bizim
        self.cagrilar = []
        self.durumlar = []
        self.yanitlar = []

    def __call__(self, url, veri=None, json_veri=None, basliklar=None, yontem=None, **kw):
        self.cagrilar.append(url)
        if '/asistan/sor' in url:
            assert basliklar['X-Asistan-Anahtar'] == 'gizli'
            return {'kid': 7, 'tur': self.tur, 'metin': 'Açık ilanlar var. Bak: https://x.com/a',
                    'ilanlar': [{'kurum': 'Test Kurumu', 'son_tarih': GELECEK}], 'baglantilar': [{'url': 'u'}]}
        if '/asistan/durum' in url:
            self.durumlar.append(json_veri)
            return {}
        if url.endswith('/replies'):
            if self.izin_yok:
                raise sy.YayinHatasi('HTTP 403: (#200) permission')
            self.yanitlar.append(veri['message'])
            return {'id': 'r'}
        if '/me?' in url:
            return {'username': self.bizim}
        if '/comments?' in url:
            return {'data': self.yorumlar}
        return {'permalink': 'https://www.instagram.com/reel/abc/'}


class YanitMetniTest(unittest.TestCase):
    def test_uzunluk_ve_baglanti_yok(self):
        metin = sa.yanit_metni({'metin': 'Merhaba https://evil.com/x #etiket 😀 ' + 'kelime ' * 200,
                                'ilanlar': [{'kurum': 'A', 'son_tarih': GELECEK}] * 5, 'baglantilar': [{'url': 'u'}]})
        self.assertLessEqual(len(metin), 450)
        self.assertNotIn('http', metin)
        self.assertNotIn('#', metin)
        self.assertNotIn('😀', metin)
        self.assertEqual(metin.count('• '), 3)
        self.assertTrue(metin.endswith("Ayrıntılar kpsstercihi.com'da."))

    def test_tarih_turkce(self):
        self.assertEqual(sa._gun_yaz('2031-11-30'), '30 Kasım')
        self.assertEqual(sa._gun_yaz('2031-03-05T10:00:00'), '5 Mart')
        self.assertEqual(sa._gun_yaz('bozuk'), '')
        m = sa.yanit_metni({'metin': 'Tamam.', 'ilanlar': [{'kurum': 'K', 'son_tarih': '2031-08-02'}]})
        self.assertIn('• K – son gün 2 Ağustos', m)

    def test_ilansiz_ve_baglantisiz_sade(self):
        self.assertEqual(sa.yanit_metni({'metin': 'Rica ederim.', 'ilanlar': [], 'baglantilar': []}), 'Rica ederim.')


class YanitsizTest(unittest.TestCase):
    def test_anahtar_kelimeler(self):
        for t in ['Bu ilan rezalet', 'sponsor olur musunuz', 'DM atın', 'ücret nedir', 'işbirliği yapalım', 'yalan haber']:
            self.assertTrue(sa.yanitsiz_neden(t), t)

    def test_telefon_eposta(self):
        self.assertTrue(sa.yanitsiz_neden('beni ara 0532 123 45 67'))
        self.assertTrue(sa.yanitsiz_neden('a.b@example.com yaz'))

    def test_normal_soru(self):
        self.assertEqual(sa.yanitsiz_neden('Lise mezunuyum, hangi ilanlara başvurabilirim?'), '')
        self.assertEqual(sa.yanitsiz_neden('Admin ile ilgili ilan var mı'), '')


class AkisTest(unittest.TestCase):
    def kos(self, sahte, ortam=None, **ek):
        telegram = []
        ortam_ = {'IG_KULLANICI_ID': '1', 'IG_ERISIM_ANAHTARI': 'tok', 'ASISTAN_ANAHTAR': 'gizli'}
        ortam_.update(ortam or {})
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, ortam_, clear=False), \
                mock.patch.object(sy, '_istek', sahte), mock.patch('sosyal_motor.gecmis_oku', return_value=[{'ig_id': 'M1', 'zaman': SIMDI.isoformat()}]), \
                mock.patch.object(sa, '_telegram', lambda m: telegram.append(m) or True), mock.patch.object(sa, '_uyku', lambda s: None):
            if ortam_.get('ASISTAN_ANAHTAR') == '':
                os.environ.pop('ASISTAN_ANAHTAR', None)
            yol = str(Path(d) / 'durum.json')
            sa.yorumlari_bildir(SIMDI, yol)
            return telegram, Path(yol).read_text(encoding='utf-8')

    def test_yanitlar_ve_durum_bildirir(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        tg, _ = self.kos(s)
        self.assertEqual(len(s.yanitlar), 1)
        self.assertIn('Test Kurumu', s.yanitlar[0])
        self.assertEqual(s.durumlar[0]['durum'], 'yanitlandi')
        self.assertEqual(s.durumlar[0]['kid'], 7)
        self.assertIn('Yanıtlandı:', tg[0])

    def test_bilinmiyor_telegrama_birakilir(self):
        s = Sahte([yorum(1, 'şey hakkında?')], tur='bilinmiyor')
        tg, _ = self.kos(s)
        self.assertEqual(s.yanitlar, [])
        self.assertEqual(s.durumlar[0]['durum'], 'atlandi')
        self.assertIn('Yanıtlanmadı', tg[0])
        self.assertIn('sana bırakıldı', tg[0])

    def test_sikayet_asistana_sorulmaz(self):
        s = Sahte([yorum(1, 'rezalet bir ilan')])
        tg, _ = self.kos(s)
        self.assertFalse([c for c in s.cagrilar if '/asistan/' in c])
        self.assertIn('Yanıtlanmadı (anahtar kelime: rezalet)', tg[0])

    def test_kendi_hesabimiz_ve_konu_yaniti_atlanir(self):
        s = Sahte([yorum(1, 'Teşekkürler', kullanici='KPSSTercihi'), yorum(2, 'Yanıt', parent_id='9')])
        tg, _ = self.kos(s)
        self.assertEqual(tg, [])
        self.assertEqual(s.yanitlar, [])

    def test_gorulen_tekrar_islenmez(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {'IG_KULLANICI_ID': '1', 'IG_ERISIM_ANAHTARI': 't', 'ASISTAN_ANAHTAR': 'gizli'}), \
                mock.patch.object(sy, '_istek', s), mock.patch('sosyal_motor.gecmis_oku', return_value=[{'ig_id': 'M1', 'zaman': SIMDI.isoformat()}]), \
                mock.patch.object(sa, '_telegram', lambda m: True), mock.patch.object(sa, '_uyku', lambda x: None):
            yol = str(Path(d) / 'd.json')
            sa.yorumlari_bildir(SIMDI, yol)
            sa.yorumlari_bildir(SIMDI, yol)
        self.assertEqual(len(s.yanitlar), 1)

    def test_en_cok_10_yanit(self):
        s = Sahte([yorum(i, 'Hangi ilanlar açık?') for i in range(1, 14)])
        tg, _ = self.kos(s)
        self.assertEqual(len(s.yanitlar), 10)
        self.assertEqual(len(tg), 13)
        self.assertIn('en çok 10', tg[-1])

    def test_izin_hatasi_yaniti_durdurur_bir_kez_haber_verir(self):
        s = Sahte([yorum(i, 'Hangi ilanlar açık?') for i in range(1, 4)], izin_yok=True)
        tg, durum = self.kos(s)
        self.assertEqual(s.yanitlar, [])
        self.assertEqual(len(tg), 4)  # 3 yorum + 1 izin uyarısı
        self.assertEqual(sum('izni' in m and 'durduruldu' in m for m in tg), 1)
        self.assertEqual(len([c for c in s.cagrilar if c.endswith('/replies')]), 1)
        self.assertEqual(s.durumlar[0]['durum'], 'hata')
        self.assertIn('yanit_izin_uyarisi', durum)

    def test_anahtar_yoksa_eskisi_gibi_yalniz_telegram(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        tg, _ = self.kos(s, {'ASISTAN_ANAHTAR': ''})
        self.assertEqual(s.yanitlar, [])
        self.assertFalse([c for c in s.cagrilar if '/asistan/' in c or '/me?' in c])
        self.assertEqual(tg[0], "Instagram'da yeni yorum\n@aday: Hangi ilanlar açık?\nVideo: https://www.instagram.com/reel/abc/")

    def test_zaten_yanitlanmis_yoruma_ikinci_yanit_gitmez(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        asil = s.__call__

        def sahte(url, *a, **kw):
            if '/replies?' in url:
                return {'data': [{'username': 'KPSSTercihi'}]}
            return asil(url, *a, **kw)
        tg, _ = self.kos(sahte)
        self.assertEqual(s.yanitlar, [])
        self.assertEqual(s.durumlar[0]['durum'], 'atlandi')
        self.assertIn('zaten yanıtımız var', tg[0])

    def test_yanit_kontrolu_okunamazsa_yanit_gitmez(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        asil = s.__call__

        def sahte(url, *a, **kw):
            if '/replies?' in url:
                raise sy.YayinHatasi('HTTP 500: x')
            return asil(url, *a, **kw)
        self.kos(sahte)
        self.assertEqual(s.yanitlar, [])

    def test_sifir_acik_ilan_yazilmaz(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        asil = s.__call__

        def sahte(url, *a, **kw):
            if '/asistan/sor' in url:
                asil(url, *a, **kw)
                return {'kid': 7, 'tur': 'ilan', 'metin': 'Şu an sitede 0 açık ilan var.', 'ilanlar': [], 'baglantilar': []}
            return asil(url, *a, **kw)
        self.kos(sahte)
        self.assertEqual(s.yanitlar, [])
        self.assertEqual(s.durumlar[0]['durum'], 'atlandi')

    def test_ciplak_alan_adi_silinir(self):
        m = sa.yanit_metni({'metin': 'Kanal: t.me/kpss ve kpsstercihi.com/nereye/ sayfası ✅', 'ilanlar': [], 'baglantilar': []})
        self.assertNotIn('t.me', m)
        self.assertNotIn('/nereye', m)
        self.assertNotIn('✅', m)

    def test_anahtar_anahtari_kapali(self):
        s = Sahte([yorum(1, 'Hangi ilanlar açık?')])
        tg, _ = self.kos(s, {'IG_YORUM_YANIT': '0'})
        self.assertEqual(s.yanitlar, [])
        self.assertEqual(len(tg), 1)
        self.assertNotIn('Yanıtlan', tg[0])


if __name__ == '__main__':
    unittest.main()
