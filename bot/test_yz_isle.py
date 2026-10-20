import contextlib
import io
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime
from pathlib import Path

import yz_isle as yi
import yz_logo
from site_uret import TR
from yz_denetim import SURUM

SIMDI = datetime(2026, 10, 19, 20, 0, tzinfo=TR)
ILAN = {'id': 'kk-1', 'baslik': 'Örnek Bakanlığı - 11 ALACAK', 'kurum': 'Örnek Bakanlığı', 'kadro': '11 ALACAK',
        'son_tarih': '2026-10-26', 'ilk_gorulme': '2026-10-19T10:00:00+03:00', 'ozet': 'Kısa.'}
YZ = {'kurum': 'Örnek Bakanlığı', 'okunabilirlik': 'iyi', 'akademik': False, 'iptal_veya_duzeltme': False,
      'son_basvuru_tarihi': '2026-10-28', 'son_basvuru_saati': '17:00', 'baslangic_tarihi': '2026-10-19',
      'kadrolar': [{'unvan': 'Yazılım Geliştirme Uzmanı', 'adet': 6, 'ogrenim': 'lisans', 'puan_turu': 'KPSS P3',
                    'kosullar': ['Bilgisayar mühendisliği mezunu olmak.', "657 sayılı Kanunun 48. maddesindeki şartlar"]},
                   {'unvan': 'Sistem Uzmanı', 'adet': 5, 'kosullar': []}],
      'ogrenim': ['lisans'], 'kpss_gerekli': True, 'puan_turleri': ['KPSS P3'], 'iller': ['ANKARA'],
      'ortak_kosullar': ['En az 3 yıl deneyim.'], 'ozet': 'Örnek Bakanlığı 11 sözleşmeli bilişim personeli alacak; '
                                                         'başvurular 19-28 Ekim arasında Kariyer Kapısı üzerinden yapılır.'}


def veri(yz=YZ, surum=SURUM):
    return {'kk-1': {'surum': surum, 'yz': yz, 'zaman': '2026-10-19T19:00:00+03:00'}}


class Alanlar(unittest.TestCase):
    def test_gemini_kayda_yazilir(self):
        i = yi.uygula(ILAN, veri(), SIMDI)
        self.assertEqual(i['kadro'], 'Toplam 11 kişi — 6 Yazılım Geliştirme Uzmanı • 5 Sistem Uzmanı')
        self.assertEqual((i['son_tarih'], i['son_zaman']), ('2026-10-28', '2026-10-28T17:00:00+03:00'))
        self.assertEqual(i['puan_turleri'], ['P3'])
        self.assertEqual(i['iller'], ['Ankara'])
        self.assertEqual(i['yz_kadrolar'][0]['kosullar'], ['Bilgisayar mühendisliği mezunu olmak.'])   # 657/48 atıldı
        self.assertIn('Kariyer Kapısı', i['ozet'])

    def test_mantiksiz_deger_yazilmaz(self):
        yz = dict(YZ, son_basvuru_tarihi='2025-01-01', kadrolar=[{'unvan': 'Uzman', 'adet': 0, 'kosullar': []}])
        i = yi.uygula(ILAN, veri(yz), SIMDI)
        self.assertEqual(i['son_tarih'], '2026-10-26')
        self.assertEqual(i['kadro'], '11 ALACAK')

    def test_okunamayan_ve_eski_surum_uygulanmaz(self):
        self.assertIs(yi.uygula(ILAN, veri(dict(YZ, okunabilirlik='kotu')), SIMDI), ILAN)
        self.assertIs(yi.uygula(ILAN, veri(surum=SURUM - 1), SIMDI), ILAN)

    def test_takma_ad_ile_bulunur(self):
        ikincil = dict(ILAN, id='sbb-9', kaynak_kimlikleri=['kk-1'])
        self.assertTrue(yi.uygula(ikincil, veri(), SIMDI).get('yz'))


class Kapi(unittest.TestCase):
    def test_yayina_hazir(self):
        self.assertEqual(yi.yayina_hazir(ILAN, {}, SIMDI.replace(hour=10, minute=30))[0], False)   # 30 dk: Gemini beklenir
        self.assertEqual(yi.yayina_hazir(ILAN, {}, SIMDI.replace(hour=11, minute=5))[0], True)     # 1 saat doldu: bot verisiyle
        self.assertEqual(yi.yayina_hazir(ILAN, veri(dict(YZ, okunabilirlik='kotu')), SIMDI.replace(hour=10, minute=30))[0], False)
        self.assertEqual(yi.yayina_hazir(ILAN, veri())[0], True)
        self.assertEqual(yi.yayina_hazir(ILAN, veri(dict(YZ, akademik=True)))[0], False)
        self.assertEqual(yi.yayina_hazir(ILAN, veri(dict(YZ, iptal_veya_duzeltme=True)))[0], False)
        self.assertEqual(yi.yayina_hazir(dict(ILAN, duyuru_turu='iptal'), {})[0], True)

    def test_ilan_bot_kapisi_gemini_alanlariyla_gonderir(self):
        import ilan_bot
        with contextlib.redirect_stdout(io.StringIO()):
            taze = datetime.now(TR).isoformat()
            hazir = ilan_bot.yayina_hazir([ILAN, dict(ILAN, id='kk-2', ilk_gorulme=taze)], logo_bul=lambda i: b'png', veri=veri())
        self.assertEqual([i['id'] for i in hazir], ['kk-1'])
        self.assertEqual(hazir[0]['son_tarih'], '2026-10-28')


class Kapali(unittest.TestCase):
    def test_kapaliyken_gemini_kullanilmaz_ilan_beklemez(self):
        with mock.patch.object(yi, 'kapali', return_value=True):
            self.assertIs(yi.uygula(ILAN), ILAN)
            self.assertEqual(yi.yayina_hazir(ILAN, simdi=SIMDI.replace(hour=10, minute=5)), (True, ''))


class Iptal(unittest.TestCase):
    def test_gemini_iptal_dedigi_kayit_iptal_duyurusu_olarak_gider(self):
        import ilan_bot
        yz = dict(YZ, iptal_veya_duzeltme=True, duyuru_tipi='iptal')
        with contextlib.redirect_stdout(io.StringIO()):
            hazir = ilan_bot.yayina_hazir([ILAN], logo_bul=lambda i: None, veri=veri(yz))
        self.assertEqual(hazir[0]['duyuru_turu'], 'İptal')                       # logo gerekmez, duyuru akışına girer
        self.assertEqual(yi.uygula(ILAN, veri(yz), SIMDI)['duyuru_turu'], 'İptal')  # sitede duyuru olarak görünür

    def test_duzeltme_ve_akademik_gitmez(self):
        self.assertFalse(yi.yayina_hazir(ILAN, veri(dict(YZ, iptal_veya_duzeltme=True, duyuru_tipi='duzeltme')))[0])
        self.assertFalse(yi.yayina_hazir(ILAN, veri(dict(YZ, iptal_veya_duzeltme=True, duyuru_tipi='iptal', akademik=True)))[0])
        self.assertFalse(yi.yayina_hazir(dict(ILAN, duyuru_turu='İptal'), veri(dict(YZ, akademik=True)))[0])
        self.assertTrue(yi.yayina_hazir(dict(ILAN, duyuru_turu='İptal'), veri())[0])


class Isle(unittest.TestCase):
    def test_once_sira_sonra_yeni_okunur_ve_kaydedilir(self):
        ilanlar = [dict(ILAN, id='a', ilk_gorulme='2026-10-19T09:00'), dict(ILAN, id='b', ilk_gorulme='2026-10-19T11:00'),
                   dict(ILAN, id='eski', son_tarih='2026-10-01')]
        okunan = []
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            d = Path(d)
            (d / 'ilanlar.json').write_text(json.dumps({'ilanlar': ilanlar, 'telegram_bekleyen': ['a']}), encoding='utf-8')
            sayac = yi.isle(5, 0, 'anahtar', SIMDI, d / 'ilanlar.json', d / 'yz.json',
                            cagir=lambda parca, anahtar: okunan.append(parca[-1]['text']) or YZ, logo_bul=lambda i, a: None)
            sonuc = json.loads((d / 'yz.json').read_text(encoding='utf-8'))
        self.assertEqual(sayac['okunan'], 2)
        self.assertEqual(sorted(sonuc), ['a', 'b'])
        self.assertEqual(sonuc['a']['surum'], SURUM)


class Logo(unittest.TestCase):
    def test_resmi_alan(self):
        self.assertTrue(yz_logo.resmi_mi('https://www.doganyol.bel.tr/logo.png'))
        self.assertTrue(yz_logo.resmi_mi('https://iskur.gov.tr/a.png'))
        self.assertFalse(yz_logo.resmi_mi('https://tr.wikipedia.org/x.png'))
        self.assertFalse(yz_logo.resmi_mi('https://evil.com/gov.tr.png'))

    def test_belediye_sitesi_tahmini_ve_amblem_kesimi(self):
        self.assertEqual(yz_logo.tahmini_siteler('BOZTEPE BELEDİYE BAŞKANLIĞI')[0], 'https://www.boztepe.bel.tr/')
        self.assertEqual(yz_logo.tahmini_siteler('Muş Elmakaya Belediyesi')[0], 'https://www.elmakaya.bel.tr/')
        self.assertEqual(yz_logo.tahmini_siteler('Türkiye İş Kurumu'), [])
        from PIL import Image, ImageDraw
        im = Image.new('RGBA', (600, 100), (255, 255, 255, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((5, 5, 95, 95), fill=(30, 90, 40, 255))
        d.rectangle((130, 30, 590, 70), fill=(40, 60, 160, 255))
        png = io.BytesIO()
        im.save(png, format='PNG')
        with Image.open(io.BytesIO(yz_logo.amblem_kes(png.getvalue()))) as kesik:
            self.assertLess(abs(kesik.width - kesik.height), 5)
        self.assertIsNone(yz_logo.amblem_kes(b'bozuk'))
        self.assertNotRegex(yz_logo.TARAYICI['User-Agent'], r'[^\x00-\x7f]')   # başlıkta Türkçe harf istek atmayı bozar

    def test_site_adaylari(self):
        html = ('<img src="/img/banner.jpg"><img src="/img/logo.png" alt="x"><img src="https://cdn.com/logo.png">'
                '<meta property="og:image" content="/og.jpg"><link rel="apple-touch-icon" sizes="180x180" href="/a180.png">')
        self.assertEqual(yz_logo.site_adaylari('https://www.ornek.bel.tr/', html),
                         ['https://www.ornek.bel.tr/img/logo.png', 'https://www.ornek.bel.tr/og.jpg',
                          'https://www.ornek.bel.tr/a180.png'])

    def test_bul_dogrula_kaydet(self):
        from PIL import Image
        png = io.BytesIO()
        Image.new('RGBA', (200, 200), (200, 0, 0, 255)).save(png, format='PNG')
        cevaplar = iter([{'candidates': [{'content': {'parts': [{'text': '```json\n{"site": "https://www.doganyol.bel.tr/", '
                                                                        '"logolar": ["https://www.doganyol.bel.tr/logo.png"]}\n```'}]}}]},
                         {'candidates': [{'content': {'parts': [{'text': '{"logo_mu": true, "guven": 0.95}'}]}}]}])
        import yz_denetim as yd
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(yd, '_MODELLER', ['m']):
            dosya = yz_logo.logo_bul_ve_kaydet({'kurum': 'DOĞANYOL BELEDİYE BAŞKANLIĞI'}, 'a',
                                               iste=lambda *a: next(cevaplar),
                                               indir=lambda url, *a: png.getvalue() if url.endswith('.png') else b'<html></html>',
                                               arsiv=d)
            kayit = json.loads((Path(d) / 'kaynaklar.json').read_text(encoding='utf-8'))
        self.assertTrue(dosya.endswith('.png'))
        self.assertEqual(list(kayit.values())[0]['orijinal'], 'https://www.doganyol.bel.tr/logo.png')


if __name__ == '__main__':
    unittest.main()
