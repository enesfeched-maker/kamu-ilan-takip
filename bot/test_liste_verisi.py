import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import liste_verisi as lv
from site_uret import TR

KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=%s'
SIMDI = datetime(2026, 10, 4, 18, 30, tzinfo=TR)


def uid(n):
    return '%08d-1111-4111-8111-111111111111' % n


def ilan(n, **ek):
    return {'id': KK % uid(n), 'link': KK % uid(n), 'baslik': 'Test Üniversitesi Alım İlanı', 'kurum': 'Test Üniversitesi',
            'kadro': '2 Memur', 'son_tarih': '2026-10-10', 'ogrenim': ['lisans'], 'iller': ['Ankara'], **ek}


def puan_klasoru(satirlar):
    d = Path(tempfile.mkdtemp())
    (d / 'puanlar').mkdir()
    (d / 'puanlar' / 'lisans.json').write_text(json.dumps({'duzey': 'lisans', 'donemler': {'2024-1': [{'unvan': 'ESKİ', 'min': 1}], '2025-2': satirlar[:3], '2026-1': satirlar[3:]}}), encoding='utf-8')
    return d


class BaslikTests(unittest.TestCase):
    def test_baslik_temiz(self):
        self.assertEqual(lv.baslik_temiz('İlk Defa Atanmak Üzere Vhki Alımı İlanı'), 'VHKİ alımı')
        self.assertEqual(lv.baslik_temiz('Memur Sınav İlanı'), 'Memur sınavı')
        self.assertEqual(lv.baslik_temiz('Büro Personeli İlanı'), 'Büro Personeli')
        self.assertEqual(lv.baslik_temiz('.net Uzmanı'), '.NET Uzmanı')


class IlTests(unittest.TestCase):
    def test_il_bul(self):
        self.assertEqual(lv.il_bul({'iller': ['Ankara']}), 'Ankara')
        self.assertEqual(lv.il_bul({'iller': ['Ankara', 'İzmir', 'Bursa']}), 'Ankara +2')

    def test_belediyede_addan_il(self):
        self.assertEqual(lv.il_bul({'kurum': 'Kırşehir Mucur Belediyesi'}), 'Kırşehir')

    def test_parantezli_il(self):
        self.assertEqual(lv.il_bul({'kurum': 'SUBAŞI (YALOVA) BELEDİYE BAŞKANLIĞI'}), 'Yalova')
        self.assertEqual(lv.il_bul({'kurum': 'Test Birimi (Konya) Müdürlüğü'}), 'Konya')

    def test_harita_ilsiz_belediyeyi_cozer(self):
        ilanlar = [{'kurum': 'Ardahan Hanak Belediyesi'}, {'kurum': 'HANAK BELEDİYE BAŞKANLIĞI'}, {'kurum': 'Bilinmez Belediyesi'}]
        harita = lv.il_haritasi(ilanlar)
        self.assertEqual(lv.il_bul(ilanlar[1], harita), 'Ardahan')
        self.assertEqual(lv.il_bul(ilanlar[1]), '')
        self.assertEqual(lv.il_bul(ilanlar[2], harita), '')

    def test_yer_kisa_yedek(self):
        self.assertEqual(lv.il_bul({'yer': 'Bakanlık Merkez / Ankara'}), 'Ankara')


class PuanTuruTests(unittest.TestCase):
    def test_puan_turleri(self):
        self.assertEqual(lv.puan_turleri({'ozet': 'KPSS P93 ve KPSS P3 puanı', 'sartlar': [{'metin': 'KPSS P 94'}]}), ['P3', 'P93', 'P94'])

    def test_yok(self):
        self.assertEqual(lv.puan_turleri({'ozet': 'KPSS şartı yok'}), [])


class TabanTests(unittest.TestCase):
    def satirlar(self, n):
        return [{'unvan': 'MEMUR', 'min': 70 + i, 'kurum': 'X'} for i in range(n)]

    def test_en_az_bes_kayit(self):
        t = lv.taban_tablolari(puan_klasoru(self.satirlar(5)))
        r = lv.taban_ref(t, 'lisans', ['Memur'])
        self.assertEqual((r['n'], r['medyan'], r['donem']), (5, 72.0, '2025-2/2026-1'))
        self.assertEqual(r['duzey'], 'lisans')

    def test_dort_kayit_yetmez(self):
        t = lv.taban_tablolari(puan_klasoru(self.satirlar(4)))
        self.assertIsNone(lv.taban_ref(t, 'lisans', ['Memur']))

    def test_eski_donem_sayilmaz_ve_parantez_atilir(self):
        t = lv.taban_tablolari(puan_klasoru(self.satirlar(6)))
        self.assertIsNone(lv.taban_ref(t, 'lisans', ['Eski']))
        self.assertIsNotNone(lv.taban_ref(t, 'lisans', ['Memur (4/B)']))
        self.assertIsNone(lv.taban_ref(t, 'onlisans', ['Memur']))


class TakvimTests(unittest.TestCase):
    def test_sayim_ve_pencere(self):
        k = [{'son_tarih': '2026-10-05'}, {'son_tarih': '2026-10-05'}, {'son_tarih': '2026-10-04'}, {'son_tarih': '2026-10-03'},
             {'son_tarih': '2027-01-01'}, {'son_tarih': ''}, {}]
        self.assertEqual(lv.takvim(k, SIMDI), {'2026-10-04': 1, '2026-10-05': 2})


class ListeTests(unittest.TestCase):
    def test_liste_uret(self):
        docs = puan_klasoru([{'unvan': 'MEMUR', 'min': 70 + i} for i in range(5)])
        ilanlar = [
            ilan(1, ilk_gorulme='2026-10-04T08:00:00+03:00', ozet='KPSS P3', ilan_turu='Sözleşmeli Personel İlanları', kategori='lisans'),
            ilan(2, son_tarih='2026-09-01'),                       # süresi geçmiş
            ilan(3, iptal_edildi=True),
            ilan(4, duyuru_turu='Düzeltme'),
            ilan(5, baslangic_zaman='2026-10-05T01:00:00+03:00'),  # yakında
        ]
        v = lv.liste_uret(ilanlar, {uid(1): {'logo': 'ilan/logo/ab.webp', 'kurum_slug': 'test'}}, docs, SIMDI, '2026-10-04T17:24:28+03:00')
        self.assertEqual([k['key'] for k in v['ilanlar']], [uid(1), uid(5)])
        a = v['ilanlar'][0]
        self.assertEqual((a['il'], a['puan_turleri'], a['logo'], a['durum']), ('Ankara', ['P3'], 'ilan/logo/ab.webp', 'soon'))
        self.assertEqual(a['taban_ref']['lisans']['n'], 5)
        self.assertNotIn('duzey', a['taban_ref']['lisans'])
        self.assertEqual((a['ilan_turu'], a['kategori']), ('Sözleşmeli Personel İlanları', 'lisans'))
        self.assertNotIn('ilan_turu', v['ilanlar'][1])
        self.assertEqual(v['sayilar'], {'acik': 2, 'kadro': 4, 'bugun_yeni': 1})
        self.assertEqual(v['takvim'], {'2026-10-10': 2})
        self.assertEqual(v['guncelleme'], '2026-10-04T17:24:28+03:00')
        self.assertEqual(v['ilanlar'][1]['durum'], 'upcoming')

    def test_akademik_haric(self):
        docs = puan_klasoru([])
        self.assertEqual(lv.liste_uret([ilan(1, kategori='akademik', baslik='Profesör Alımı')], {}, docs, SIMDI)['ilanlar'], [])

    def test_uret_dosya_yazar(self):
        docs = puan_klasoru([])
        lv.uret([ilan(1)], {}, docs, SIMDI)
        self.assertEqual(json.loads((docs / 'liste.json').read_text(encoding='utf-8'))['sayilar']['acik'], 1)


if __name__ == '__main__':
    unittest.main()
