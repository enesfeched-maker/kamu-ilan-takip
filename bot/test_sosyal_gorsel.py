"""Instagram hikâye ve karusel yayını (bot/sosyal_gorsel.py): program, açıklama, tekrar engeli, API çağrı sırası."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import sosyal_gorsel as sg
from site_uret import TR

PAZARTESI = datetime(2026, 11, 16, 11, tzinfo=TR)


def gun(n):
    return PAZARTESI.replace(day=16 + n)


class Program(unittest.TestCase):
    def test_haftalik_program(self):
        self.assertEqual(sg.plan(gun(0)), [('son-gun', ['hikaye'])])
        self.assertEqual(sg.plan(gun(2)), [('son-gun', ['hikaye', 'karusel'])])          # çarşamba
        self.assertEqual(sg.plan(gun(3)), [('puan-bandi', ['hikaye', 'karusel']), ('son-gun', ['hikaye'])])
        self.assertEqual(sg.plan(gun(6)), [('kadro-raporu', ['hikaye', 'karusel']), ('son-gun', ['hikaye'])])

    def test_puan_araligi_haftaya_gore_doner_ve_hepsini_dener(self):
        a, b = sg.puan_araliklari(gun(3)), sg.puan_araliklari(gun(10) if False else datetime(2026, 11, 26, tzinfo=TR))
        self.assertEqual(sorted(a), sorted(sg.PUAN_ARALIKLARI))
        self.assertNotEqual(a[0], b[0])

    def test_ayni_gun_ayni_is_tekrarlanmaz(self):
        g = [{'zaman': '2026-11-18T11:05:00+03:00', 'tur': 'son-gun', 'bicim': 'hikaye', 'ig_id': '1'},
             {'zaman': '2026-11-18T11:05:00+03:00', 'tur': 'son-gun', 'bicim': 'karusel'}]   # kimliksiz = yayınlanmamış
        self.assertTrue(sg.bugun_yapildi(g, 'son-gun', 'hikaye', gun(2)))
        self.assertFalse(sg.bugun_yapildi(g, 'son-gun', 'karusel', gun(2)))
        self.assertFalse(sg.bugun_yapildi(g, 'son-gun', 'hikaye', gun(3)))


class Aciklama(unittest.TestCase):
    def kontrol(self, metin, sayi):
        self.assertIn(sayi, metin.splitlines()[0])   # kanca satırında asıl sayı
        self.assertIn('@kpsstercihi', metin)
        self.assertLessEqual(sum(1 for k in metin.split() if k.startswith('#')), 5)
        self.assertLessEqual(len(metin), 2200)
        for yasak in ('Kaçırma', 'hemen', 'şok', 'müjde'):
            self.assertNotIn(yasak, metin)

    def test_son_gun(self):
        veri = {'ilan': 15, 'kadro': 1255, 'gunler': [['2026-11-19', [['Dokuz Eylül Üniversitesi', 68], ['Keşan Belediyesi', 2]]],
                                                      ['2026-11-23', [['Milli Savunma Bakanlığı', None]] * 5]]}
        m = sg.aciklama('son-gun', veri)
        self.kontrol(m, '1.255 kadro')
        self.assertIn('• 19 Kasım: Dokuz Eylül Üniversitesi (68), Keşan Belediyesi (2)', m)
        self.assertIn('Milli Savunma Bakanlığı ve 2 ilan daha', m)   # kişi sayısı yoksa parantez yok

    def test_kadro_raporu(self):
        veri = {'aralik': '12–18 Kasım', 'ilan': 11, 'kadro': 81, 'ilk5': [['Savunma Sanayii Başkanlığı', 26], ['AFAD', 20]]}
        m = sg.aciklama('kadro-raporu', veri)
        self.kontrol(m, '81 kadro')
        self.assertIn('• Savunma Sanayii Başkanlığı: 26 kadro', m)

    def test_puan_bandi(self):
        veri = {'donem': '2026-1', 'duzey_adi': 'Lisans', 'bant': [70, 75], 'kadro_kodu': 64, 'kisi': 110,
                'en_dusuk': [['BÜRO PERSONELİ', 'SOSYAL GÜVENLİK KURUMU BAŞKANLIĞI', 'MERSİN', 70.30772]]}
        m = sg.aciklama('puan-bandi', veri)
        self.kontrol(m, '110 kişi')
        self.assertIn('70–75', m.splitlines()[0])
        self.assertIn('70,31', m)


class Yayin(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        isler = [{'tur': 'son-gun', 'bicim': 'hikaye', 'dosyalar': ['son-gun-hikaye.mp4']},
                 {'tur': 'son-gun', 'bicim': 'karusel', 'dosyalar': ['son-gun-karusel-01.jpg', 'son-gun-karusel-02.jpg'],
                  'aciklama': 'Açıklama'}]
        (self.d / 'is.json').write_text(json.dumps({'zaman': '2026-11-18T11:02:00+03:00', 'isler': isler}), encoding='utf-8')

    def tearDown(self):
        self.t.cleanup()

    def test_cagri_sirasi_ve_gecmis(self):
        cagrilar = []

        def sahte(url, veri=None, **_):
            cagrilar.append((url.split('/v')[1].split('/', 1)[1].split('?')[0], dict(veri or {})))
            if url.endswith('/media'):
                return {'id': f'k{len(cagrilar)}'}
            if url.endswith('/media_publish'):
                return {'id': 'yayin-' + veri['creation_id']}
            return {'status_code': 'FINISHED'}
        with mock.patch('sosyal_yayinla._istek', sahte):
            sonuc = sg.yayinla(self.d, 'https://ornek/indir/ETIKET/', ortam=('IG', 'anahtar'), aralik=0)
        self.assertEqual([s.get('id') is not None for s in sonuc], [True, True])
        medya = [v for u, v in cagrilar if u.endswith('/media')]
        self.assertEqual(medya[0]['media_type'], 'STORIES')
        self.assertEqual(medya[0]['video_url'], 'https://ornek/indir/ETIKET/son-gun-hikaye.mp4')
        self.assertEqual([m.get('is_carousel_item') for m in medya[1:3]], ['true', 'true'])
        self.assertTrue(medya[1]['image_url'].endswith('.jpg'))
        self.assertEqual(medya[3]['media_type'], 'CAROUSEL')
        self.assertEqual(medya[3]['children'].count(','), 1)
        self.assertEqual(medya[3]['caption'], 'Açıklama')
        g = self.d / 'g.json'
        self.assertEqual(sg.kaydet(self.d, g), 2)
        self.assertEqual([x['bicim'] for x in json.loads(g.read_text(encoding='utf-8'))], ['hikaye', 'karusel'])

    def test_hata_digerini_durdurmaz_ve_gecmise_yazilmaz(self):
        from sosyal_yayinla import YayinHatasi

        def sahte(url, veri=None, **_):
            if veri and veri.get('media_type') == 'STORIES':
                raise YayinHatasi('HTTP 400: video')
            if url.endswith('/media'):
                return {'id': 'k'}
            if url.endswith('/media_publish'):
                return {'id': 'y'}
            return {'status_code': 'FINISHED'}
        with mock.patch('sosyal_yayinla._istek', sahte):
            sonuc = sg.yayinla(self.d, 'https://ornek', ortam=('IG', 'a'), aralik=0)
        self.assertIn('hata', sonuc[0])
        self.assertEqual(sonuc[1]['id'], 'y')
        g = self.d / 'g.json'
        self.assertEqual(sg.kaydet(self.d, g), 1)

    def test_karusel_en_az_iki_gorsel(self):
        from sosyal_yayinla import YayinHatasi
        with self.assertRaises(YayinHatasi):
            sg.instagram_karusel(['tek.jpg'], 'x', ortam=('IG', 'a'), aralik=0)

    def test_anahtar_yoksa_none(self):
        with mock.patch.dict('os.environ', {'IG_KULLANICI_ID': '', 'IG_ERISIM_ANAHTARI': ''}):
            self.assertIsNone(sg.instagram_hikaye('u'))


class Uretim(unittest.TestCase):
    def test_veri_yoksa_is_yok_ve_tekrar_atlanir(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            g = t / 'g.json'
            g.write_text(json.dumps([{'zaman': '2026-11-16T11:00:00+03:00', 'tur': 'son-gun', 'bicim': 'hikaye', 'ig_id': '1'}]),
                         encoding='utf-8')
            with mock.patch('sosyal_motor.ilanlari_yukle', return_value=[]), \
                    mock.patch('sosyal_motor.acik_ilanlar', return_value=[]):
                isler = sg.uret(t / 'c', gun(0), gecmis_yolu=g)                        # pazartesi: yalnız son-gun hikâye, zaten yapılmış
                self.assertEqual(isler, [])
                isler = sg.uret(t / 'c', gun(2), gecmis_yolu=g)                        # açık ilan yok: veri yetersiz
                self.assertEqual(isler, [])
            self.assertEqual(json.loads((t / 'c' / 'is.json').read_text(encoding='utf-8'))['isler'], [])


if __name__ == '__main__':
    unittest.main()
