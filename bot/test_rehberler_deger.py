"""Rehber yazılarının derinliği (1 Kasım 2026) ve 'Şu an açık ilanlar' bloğu.

Kelime tabanı, tekrar eden paragraf yasağı ve açık ilan eşleştirmesi (donmuş tarihle, sabit yakın tarih olmadan)."""
import re
import sys
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehberler
import uygulamali_rehberler
from statik_icerik import TR

ON_YAZI = ('kpss-ile-memur-olmak', 'kpss-puan-turleri', 'merkezi-yerlestirme-ve-kurum-ilanlari', 'belediye-memur-alimi',
           'sozlesmeli-personel-4b', 'kamu-isci-alimi', 'sozlesmeli-bilisim-personeli', 'ekpss-engelli-memur-alimi',
           'basvuru-belgeleri-ve-hatalar', 'kariyer-kapisi-basvuru')
SIMDI = datetime(2026, 11, 1, 12, 0, tzinfo=TR)   # donmuş "şimdi"; tüm tarihler buna göre hesaplanır


def gun(n):
    return (SIMDI + timedelta(days=n)).date().isoformat()


def ilan(key, manset, kurum, gun_sonra, **ek):
    k = {'key': key, 'manset': manset, 'kurum': kurum, 'son_tarih': gun(gun_sonra)}
    k.update(ek)
    return k


def parcalar(r):
    """Bir yazıdaki tüm metin parçaları: giriş, paragraflar ve madde satırları (başlıklar hariç)."""
    cikti = [r[3]]
    for _, ps in r[4]:
        for p in ps:
            cikti.extend(p[1] if isinstance(p, tuple) else [p])
    return cikti


def kelime(r):
    return sum(len(p.split()) for p in parcalar(r))


YAZILAR = {r[0]: r for r in rehberler.REHBERLER}


class Derinlik(unittest.TestCase):
    def test_on_yazi_ve_guncelleme(self):
        self.assertEqual(rehberler.GUNCELLEME, '2026-11-01')
        for slug in ON_YAZI:
            self.assertIn(slug, YAZILAR)
        self.assertEqual(len(YAZILAR), len(rehberler.REHBERLER))

    def test_kelime_tabani(self):
        for slug in ON_YAZI:
            sayi = kelime(YAZILAR[slug])
            self.assertGreaterEqual(sayi, 600, f'{slug}: {sayi} kelime')   # 600 altı yazı yayına girmez
            self.assertLessEqual(sayi, 1100, f'{slug}: {sayi} kelime')

    def test_ayni_paragraf_yok(self):
        sayac = Counter(p.strip() for r in rehberler.REHBERLER for p in parcalar(r))
        tekrar = [p[:70] for p, n in sayac.items() if n > 1]
        self.assertEqual(tekrar, [])

    def test_yasak_ifadeler(self):
        for r in rehberler.REHBERLER:
            metin = ' '.join(parcalar(r) + [r[1], r[2]]).lower()
            for yasak in ('adsense', 'telegram', 'bu yazıda'):
                self.assertNotIn(yasak, metin, f'{r[0]}: {yasak}')

    def test_aciklama_kisa(self):
        for r in rehberler.REHBERLER:
            self.assertLessEqual(len(r[2]), 170, r[0])

    def test_ilgili_baglantilar(self):
        gecerli = set(YAZILAR) | {r['slug'] for r in uygulamali_rehberler.icerikler()}
        for r in rehberler.REHBERLER:
            self.assertTrue(r[5], r[0])
            for ad, yol in r[5]:
                self.assertTrue(ad)
                self.assertFalse(yol.startswith(('/', '.', 'http')), yol)
                self.assertTrue(yol == '#ilanlar' or yol.endswith('/'), yol)
                if yol.startswith('rehber/'):
                    self.assertIn(yol.split('/')[1], gecerli, yol)

    def test_analiz_baglantilari_kullaniliyor(self):
        tum = {yol for r in rehberler.REHBERLER for _, yol in r[5]}
        for yol in ('analiz/il-il-taban-puanlari/', 'analiz/kadro-puan-siralamasi/', 'analiz/kamu-ilan-istatistikleri/',
                    'kpss-taban-puanlari/', 'puanlar/'):
            self.assertIn(yol, tum)


class AcikIlanlar(unittest.TestCase):
    def test_katla(self):
        self.assertEqual(rehberler.katla('İŞÇİ Alımı'), 'isci alimi')
        self.assertEqual(rehberler.katla('Sözleşmeli ÇAĞRI'), 'sozlesmeli cagri')
        self.assertEqual(rehberler.katla(None), '')

    def test_belediye_kurala_gore_ve_dislamalarla(self):
        liste = [
            ilan('a', '3 Zabıta Memuru', 'Kadıköy Belediyesi', 5),
            ilan('b', '2 Itfaiye Eri', 'Beşiktaş BELEDİYE Başkanlığı', 2),
            ilan('c', '1 Memur', 'Bir Üniversitesi', 1),                          # belediye değil
            ilan('d', '1 Zabıta', 'Çankaya Belediyesi', 3, kopya_of='a'),         # kopya
            ilan('e', '1 Zabıta', 'Mamak Belediyesi', 3, kurum_ici=True),         # kurum içi
            ilan('f', '1 Okutman', 'Pendik Belediyesi', 3, kategori='akademik'),  # akademik
            ilan('g', '1 Zabıta', 'Bornova Belediyesi', -1),                      # süresi geçmiş
            ilan('h', '1 Zabıta', 'Karşıyaka Belediyesi', 3),                     # sayfası yok
            ilan('i', '1 Zabıta', 'Tepebaşı Belediyesi', 3),                      # dizinlenmiyor
            ilan('j', '1 Zabıta', 'Odunpazarı Belediyesi', 0),                    # bugün son gün: girer
            dict(ilan('k', '1 Zabıta', 'Konak Belediyesi', 1), son_tarih=''),      # tarihsiz
        ]
        sayfali = {k['key'] for k in liste} - {'h'}
        sonuc = rehberler.acik_ilanlar('belediye-memur-alimi', liste, sayfali, {'i'}, SIMDI)
        self.assertEqual([k['key'] for k in sonuc], ['j', 'b', 'a'])   # en yakın son tarih önce

    def test_en_cok_bes(self):
        liste = [ilan(f'k{n}', 'Zabıta', f'{n}. Belediyesi', n) for n in range(1, 9)]
        sonuc = rehberler.acik_ilanlar('belediye-memur-alimi', liste, None, None, SIMDI)
        self.assertEqual([k['key'] for k in sonuc], ['k1', 'k2', 'k3', 'k4', 'k5'])

    def test_baslik_kurallari(self):
        liste = [
            ilan('isci', '10 Sürekli İŞÇİ', 'Bir Kurum', 2),
            ilan('isci2', '4 Temizlik İşçisi', 'Bir Kurum', 3),
            ilan('memur', '5 Memur', 'Bir Kurum', 1),
            ilan('bil', '2 Yazılım Uzmanı', 'Bir Kurum', 4),
            ilan('sis', '1 Sistem Uzmanı', 'Bir Kurum', 5),
            ilan('bil2', 'Sözleşmeli BİLİŞİM Personeli', 'Bir Kurum', 6),
            ilan('opr', '1 Sistem Operatörü', 'Bir Kurum', 7),
            ilan('soz', '6 Sözleşmeli Personel', 'Bir Kurum', 8),
            ilan('unvan', '3 Personel', 'Bir Kurum', 9, unvanlar=['sürekli işçi']),
        ]
        anahtar = lambda slug: [k['key'] for k in rehberler.acik_ilanlar(slug, liste, None, None, SIMDI)]
        self.assertEqual(anahtar('kamu-isci-alimi'), ['isci', 'isci2', 'unvan'])
        self.assertEqual(anahtar('sozlesmeli-bilisim-personeli'), ['bil', 'sis', 'bil2'])
        self.assertEqual(anahtar('sozlesmeli-personel-4b'), ['bil2', 'soz'])

    def test_kuralsiz_ve_bos(self):
        liste = [ilan('a', '3 Zabıta Memuru', 'Kadıköy Belediyesi', 5)]
        self.assertEqual(rehberler.acik_ilanlar('kpss-puan-turleri', liste, None, None, SIMDI), [])
        self.assertEqual(rehberler.acik_ilanlar('belediye-memur-alimi', [], None, None, SIMDI), [])
        self.assertEqual(rehberler.acik_ilanlar('belediye-memur-alimi', None, None, None, SIMDI), [])
        self.assertEqual(rehberler.acik_ilanlar('kamu-isci-alimi', liste, None, None, SIMDI), [])   # eşleşme yok

    def test_html_bos_liste_bos_metin(self):
        self.assertEqual(rehberler.acik_html([], str), '')
        h = rehberler.acik_html([ilan('x', '2 Zabıta', 'Bir Belediyesi', 3)], lambda v: str(v))
        self.assertIn('Şu an açık ilanlar', h)
        self.assertIn('../../ilan/x/', h)
        self.assertIn('Son başvuru: 4 Kasım 2026', h)


class Sayfalar(unittest.TestCase):
    def yaz(self, *a, **k):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        adresler = rehberler.yaz(t.name, 'https://kpsstercihi.com/', *a, **k)
        oku = lambda slug: (Path(t.name) / 'rehber' / slug / 'index.html').read_text(encoding='utf-8')
        return adresler, oku

    def test_blok_yalniz_eslesen_yazida(self):
        liste = [ilan('bel1', '3 Zabıta Memuru', 'Kadıköy Belediyesi', 4), ilan('x', '1 Memur', 'Bir Kurum', 2)]
        _, oku = self.yaz(liste, {'bel1', 'x'}, set(), SIMDI)
        belediye = oku('belediye-memur-alimi')
        self.assertIn('Şu an açık ilanlar', belediye)
        self.assertIn('href="../../ilan/bel1/"', belediye)
        self.assertNotIn('href="../../ilan/x/"', belediye)
        for slug in ('kamu-isci-alimi', 'sozlesmeli-bilisim-personeli', 'kpss-ile-memur-olmak'):
            self.assertNotIn('Şu an açık ilanlar', oku(slug))   # eşleşme yok ya da kural yok: bölüm hiç yazılmaz

    def test_eski_cagri_calisir(self):
        adresler, oku = self.yaz()
        self.assertEqual(len(adresler), len(rehberler.REHBERLER) + len(uygulamali_rehberler.icerikler()) + 1)
        self.assertNotIn('Şu an açık ilanlar', oku('belediye-memur-alimi'))
        self.assertIn('"dateModified": "2026-11-01"', oku('belediye-memur-alimi'))
        self.assertIn('"datePublished": "2026-10-19"', oku('belediye-memur-alimi'))

    def test_baslik_ve_ilgili_bolumu(self):
        _, oku = self.yaz()
        h = oku('kpss-puan-turleri')
        self.assertIn('<h1>KPSS puan türleri', h)
        self.assertIn('href="../../analiz/kadro-puan-siralamasi/"', h)
        for slug in ON_YAZI:
            self.assertEqual(len(re.findall(r'<h1>', oku(slug))), 1, slug)


if __name__ == '__main__':
    unittest.main()
