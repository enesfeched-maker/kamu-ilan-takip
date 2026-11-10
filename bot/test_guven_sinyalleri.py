"""AdSense güven sinyalleri: görünür künye, yayıncı kimliği, gerçek veriyle örnek, yarım kalmayan metinler."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bilgi_sayfalari
import rehberler
import site_uret
import uygulamali_rehberler

KOK = Path(__file__).resolve().parents[1]
BASE = 'https://kpsstercihi.com/'


def _ld(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class BaslikTest(unittest.TestCase):
    def test_kesilen_baslik_baglacla_bitmez(self):
        b = 'Akademik İlanlar 2026: Öğretim Üyesi, Öğretim Görevlisi ve Araştırma Görevlisi Alımları | KPSS Tercihi'
        kisa = site_uret.kisa_baslik(b)
        self.assertLessEqual(len(kisa), site_uret.TITLE_SINIRI)
        self.assertEqual(kisa, 'Akademik İlanlar 2026: Öğretim Üyesi, Öğretim Görevlisi')

    def test_baglac_olmayan_son_sozcuk_kalir(self):
        self.assertEqual(site_uret._sozcukte_kes('Ankara ve İzmir için memur alımı yapılacak', 30), 'Ankara ve İzmir için memur')


class CumleTest(unittest.TestCase):
    def test_yarim_cumle_atilir(self):
        m = 'Adaylar başvurularını e-Devlet üzerinden yapacaktır. Başvurusu görünmeyen hiçbir başvuru…'
        self.assertEqual(site_uret.cumlede_bitir(m), 'Adaylar başvurularını e-Devlet üzerinden yapacaktır.')

    def test_tam_metin_degismez(self):
        m = 'Başvurular e-Devlet üzerinden yapılır.'
        self.assertEqual(site_uret.cumlede_bitir(m), m)

    def test_tam_cumle_yoksa_degismez(self):
        m = 'Başvurular 28 Ekim ile 11 Kasım arasında e-Devlet üzerinden…'
        self.assertEqual(site_uret.cumlede_bitir(m), m)


class KunyeTest(unittest.TestCase):
    def test_tarih_yazi(self):
        self.assertEqual(site_uret.tarih_yazi('2026-11-01'), '1 Kasım 2026')

    def test_rehber_kunyesi_semayla_ayni_tarihte(self):
        _, html = rehberler.sayfa(rehberler.REHBERLER[0], BASE)
        self.assertIn(f'<a href="../../hakkimizda/">{site_uret.EDITOR}</a>', html)
        self.assertIn('Yayın: ' + site_uret.tarih_yazi(rehberler.YAYIN), html)
        self.assertIn('Güncelleme: ' + site_uret.tarih_yazi(rehberler.GUNCELLEME), html)
        makale = _ld(html)[0]
        self.assertEqual((makale['datePublished'], makale['dateModified']), (rehberler.YAYIN, rehberler.GUNCELLEME))

    def test_hakkimizda_kimlik(self):
        _, html = bilgi_sayfalari.sayfa('hakkimizda', BASE)
        self.assertIn('Kim hazırlıyor?', html)
        self.assertIn('Son güncelleme: ' + site_uret.tarih_yazi(bilgi_sayfalari.GUNCELLEME), html)
        ld = _ld(html)[0]
        self.assertEqual(ld['@type'], 'AboutPage')
        self.assertEqual(ld['mainEntity']['@type'], 'Organization')
        self.assertIn('https://t.me/kpsstercihi', ld['mainEntity']['sameAs'])

    def test_iletisim_semasi_ve_digerleri(self):
        _, html = bilgi_sayfalari.sayfa('iletisim', BASE)
        self.assertEqual(_ld(html)[0]['@type'], 'ContactPage')
        for ad in ('gizlilik', 'kullanim-kosullari'):
            _, html = bilgi_sayfalari.sayfa(ad, BASE)
            self.assertEqual(_ld(html), [])
            self.assertIn('Son güncelleme: ', html)


class GercekOrnekTest(unittest.TestCase):
    """Taban puanı rehberindeki üç örnek kayıt ÖSYM verisindeki gerçek satırlardır; veri değişirse test haber verir."""
    SLUG = 'kpss-taban-puani-nasil-yorumlanir'
    KAYITLAR = (
        ('A · Elektrik Üretim A.Ş. Genel Müdürlüğü, Ankara (taşra) — Memur', 'ELEKTRİK ÜRETİM A.Ş. GENEL MÜDÜRLÜĞÜ', 'ANKARA', 'MEMUR', 5, '80,91', '+1,09'),
        ('B · Elektrik Üretim A.Ş. Genel Müdürlüğü, Çanakkale (taşra) — Memur', 'ELEKTRİK ÜRETİM A.Ş. GENEL MÜDÜRLÜĞÜ', 'ÇANAKKALE', 'MEMUR', 1, '83,91', '−1,91'),
        ('C · Sosyal Güvenlik Kurumu Başkanlığı, İstanbul (taşra) — İcra Memuru', 'SOSYAL GÜVENLİK KURUMU BAŞKANLIĞI', 'İSTANBUL', 'İCRA MEMURU', 31, '78,94', '+3,06'),
    )

    def setUp(self):
        self.rehber = next(r for r in uygulamali_rehberler.icerikler() if r['slug'] == self.SLUG)
        self.satirlar = json.loads((KOK / 'docs' / 'puanlar' / 'lisans.json').read_text(encoding='utf-8'))['donemler']['2026-1']

    def _virgul(self, x):
        return f'{x:.2f}'.replace('.', ',')

    def test_uydurma_ornek_kalmadi(self):
        govde = self.rehber['body']
        for eski in ('öğretim amacıyla oluşturulmuştur', 'Temsili kayıt', '80,40', '83,10', '78,90'):
            self.assertNotIn(eski, govde)
        self.assertNotIn('Temsili', self.rehber['description'])

    def test_kayitlar_veride_var(self):
        govde = self.rehber['body']
        bulunan = {}
        for etiket, kurum, il, unvan, kontenjan, puan, fark in self.KAYITLAR:
            eslesen = [r for r in self.satirlar if (r['kurum'], r['il'], r['teskilat'], r['unvan'], r['kontenjan']) == (kurum, il, 'Taşra', unvan, kontenjan)
                       and self._virgul(r['min']) == puan]
            self.assertEqual(len(eslesen), 1, etiket)
            bulunan[etiket[0]] = eslesen[0]
            self.assertEqual(self._virgul(82 - eslesen[0]['min']).replace('-', '−').rjust(1), fark.lstrip('+'))
            for parca in (f'<td>{etiket}</td>', f'>{puan}</td>', f'>{kontenjan}</td>', f'>{fark}</td>'):
                self.assertIn(parca, govde, etiket)
        # Metindeki "aynı nitelik kodları" ve "3,00 puan" iddiaları
        self.assertEqual(bulunan['A']['nit'], bulunan['B']['nit'])
        self.assertEqual(self._virgul(bulunan['B']['min'] - bulunan['A']['min']), '3,00')
        self.assertIn('arasında 3,00 puan var', govde)

    def test_sayfa_kunyesi_ve_tarihi(self):
        import tempfile
        with tempfile.TemporaryDirectory() as gecici:
            uygulamali_rehberler.yaz(gecici, BASE)
            html = (Path(gecici) / 'rehber' / self.SLUG / 'index.html').read_text(encoding='utf-8')
        self.assertIn(f'<div class="guide-meta"><p><a href="/hakkimizda/">{site_uret.EDITOR}</a> · Güncelleme: 10 Kasım 2026.', html)
        makale = _ld(html)[0]
        self.assertEqual((makale['datePublished'], makale['dateModified']), (uygulamali_rehberler.TARIH, '2026-11-10'))


class NitelikOrnegiTest(unittest.TestCase):
    """Nitelik kodu rehberindeki iki örnek KPSS-2026/1 Tablo-3'ün gerçek satırlarıdır (kılavuz PDF'inden doğrulandı, 10 Kasım 2026)."""

    def setUp(self):
        self.govde = next(r for r in uygulamali_rehberler.icerikler() if r['slug'] == 'kpss-nitelik-kodu-nasil-okunur')['body']
        puan = KOK / 'docs' / 'puanlar'
        self.satirlar = {r['kod']: r for r in json.loads((puan / 'lisans.json').read_text(encoding='utf-8'))['donemler']['2026-1']}
        bolum = json.loads((puan / 'lisans-bolum.json').read_text(encoding='utf-8'))
        self.program = lambda kod: [bolum['bolumler'][b] for b in bolum['nitelikler']['2026-1'][kod]]

    def test_temsili_ornek_kalmadi(self):
        self.assertNotIn('Temsili örnek', self.govde)
        self.assertNotIn('gerçek bir alım duyurusu değildir', self.govde)

    def test_kimyager_satiri(self):
        r = self.satirlar['301014630']
        self.assertEqual((r['kurum'], r['il'], r['unvan'], r['kontenjan'], r['nit']),
                         ('ELEKTRİK ÜRETİM A.Ş. GENEL MÜDÜRLÜĞÜ', 'ANKARA', 'KİMYAGER', 2, ['4559', '4569']))
        self.assertEqual((self.program('4559'), self.program('4569')), (['KİMYA'], ['BİYOKİMYA']))
        self.assertIn('ÖSYM kodu 301014630', self.govde)
        self.assertIn('Ankara’daki 2 kişilik Kimyager pozisyonunda aranan nitelikler 4559 ve 4569’dur', self.govde)

    def test_avukat_satiri(self):
        r = self.satirlar['301014595']
        self.assertEqual((r['kurum'], r['il'], r['unvan']), ('DEVLET SU İŞLERİ GENEL MÜDÜRLÜĞÜ', 'ARTVİN', 'AVUKAT'))
        self.assertEqual(r['nit'], ['4419'])   # veri yalnız öğrenim kodunu tutar; 7205, 7257, 7361 kılavuz satırından okundu
        self.assertEqual(self.program('4419'), ['HUKUK'])
        self.assertIn('Artvin’deki Avukat kadrosunda dört kod var: 4419, 7205, 7257 ve 7361', self.govde)


class AracSayfasiTest(unittest.TestCase):
    """İçeriği tarayıcıda oluşan araç sayfalarında reklam betiği yok; /bolum/ ayrıca dizin dışı (AdSense, 10 Kasım 2026)."""

    def test_reklamsiz_araclar(self):
        for yol in ('bolum', 'katiplik/oyunlar', 'katiplik/antrenman', 'katiplik/dersler'):
            t = (KOK / 'docs' / yol / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('adsbygoogle.js', t, yol)
            self.assertIn('google-adsense-account', t, yol)   # doğrulama etiketi kalır
        self.assertIn('<meta name="robots" content="noindex,follow">', (KOK / 'docs' / 'bolum' / 'index.html').read_text(encoding='utf-8'))
        for yol in ('katiplik/oyunlar', 'katiplik/antrenman', 'katiplik/dersler', 'katiplik'):
            self.assertNotIn('noindex', (KOK / 'docs' / yol / 'index.html').read_text(encoding='utf-8'), yol)


if __name__ == '__main__':
    unittest.main()
