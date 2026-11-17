"""Forum SEO sayfaları: slug, kaçış, şema, kalite eşiği, dizinleme anahtarı, API hatası (ağ yok)."""
import json
import re
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import forum_seo
import forum_sayfasi

BASE = 'https://kpsstercihi.com/'
UZUN = ' '.join(['kelime'] * 130)


def yanit(i, govde='Bence ilanın ikinci maddesine bakmalısın.', rol='uye', faydali=0, rumuz='Ayşe'):
    return {'id': i, 'govde': govde, 'rumuz': rumuz, 'rol': rol, 'faydali': faydali, 'olusma': 1794756125 + i}


def baslik(i=1, ad='Zabıta memuru ilanı için puan kaç?', govde=UZUN, yanitlar=None, kategori='puan', rol='uye', **ek):
    t = {'id': i, 'baslik': ad, 'govde': govde, 'rumuz': 'Mehmet', 'rol': rol, 'kategori': kategori, 'olusma': 1794756125,
         'son_hareket': 1794756300 + i, 'yanit_sayisi': len(yanitlar or []), 'faydali': 0, 'duzey': 'lisans',
         'yanitlar': [yanit(10 + i)] if yanitlar is None else yanitlar}
    t.update(ek)
    return t


def jsonld(html_):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_, re.S)]


class SlugTesti(unittest.TestCase):
    def test_turkce_harfler(self):
        self.assertEqual(forum_seo.slug('Çağrı ĞÜŞİÖ ıİ?'), 'cagri-gusio-ii')

    def test_uzunluk_sozcuk_sinirinda(self):
        s = forum_seo.slug('merhaba dünya ' * 20)
        self.assertLessEqual(len(s), 70)
        self.assertFalse(s.endswith('-'))
        self.assertTrue(s.startswith('merhaba-dunya'))

    def test_bos(self):
        self.assertEqual(forum_seo.slug('???'), 'soru')


class SayfaTesti(unittest.TestCase):
    def test_xss_kacar(self):
        t = baslik(ad='<script>alert(1)</script>', govde='<img src=x onerror=alert(1)> ' + UZUN,
                   yanitlar=[yanit(5, '<b onmouseover=x>"cevap"</b>', rumuz='<i>x</i>')], rumuz='<u>')
        h = forum_seo.sayfa_html(t, BASE, [], True)
        self.assertNotIn('<script>alert(1)', h)
        self.assertNotIn('<img src=x', h)
        self.assertNotIn('<b onmouseover', h)
        self.assertIn('&lt;script&gt;alert(1)', h)
        for blok in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
            self.assertNotIn('<', blok)
            json.loads(blok)

    def test_yapi(self):
        t = baslik(yanitlar=[yanit(1, faydali=0), yanit(2, 'Faydalı cevap', faydali=3)])
        h = forum_seo.sayfa_html(t, BASE, [baslik(2, 'Başka soru')], True)
        self.assertIn(f'<link rel="canonical" href="{BASE}forum/soru/1-zabita-memuru-ilani-icin-puan-kac/">', h)
        self.assertIn('<h1>Zabıta memuru ilanı için puan kaç?</h1>', h)
        self.assertIn('<time datetime="2026-', h)
        self.assertIn('href="../../?b=1"', h)
        self.assertIn('<title>Zabıta memuru ilanı için puan kaç? | KPSS Forum</title>', h)
        self.assertNotIn('noindex', h)
        self.assertLess(h.index('Faydalı cevap'), h.index('Bence ilanın'))   # faydalı önce
        self.assertIn('href="../2-baska-soru/"', h)
        self.assertIn('../../konu/puan/', h)

    def test_noindex_sayfada_reklam_yok(self):
        h = forum_seo.sayfa_html(baslik(), BASE, [], False)
        self.assertIn('<meta name="robots" content="noindex,follow">', h)
        self.assertNotIn('pagead2.googlesyndication', h)


class SemaTesti(unittest.TestCase):
    def test_asistan_semaya_girmez_ama_sayfada_gorunur(self):
        t = baslik(yanitlar=[yanit(1, 'İnsan cevabı', faydali=0), yanit(2, 'Otomatik cevap metni', rol='asistan', rumuz='KPSS Tercihi')])
        s = forum_seo.qa_semasi(t, BASE + 'forum/soru/1-x/')
        metin = json.dumps(s, ensure_ascii=False)
        self.assertIn('İnsan cevabı', metin)
        self.assertNotIn('Otomatik cevap metni', metin)
        self.assertEqual(s['mainEntity']['answerCount'], 1)
        h = forum_seo.sayfa_html(t, BASE, [], True)
        self.assertIn('Otomatik cevap metni', h)
        self.assertIn('otomatik yanıt', h)

    def test_kabul_edilen_yalniz_faydali_ikiden_fazla(self):
        t = baslik(yanitlar=[yanit(1, 'A', faydali=2), yanit(2, 'B', faydali=1)])
        q = forum_seo.qa_semasi(t, 'u')['mainEntity']
        self.assertEqual(q['acceptedAnswer']['text'], 'A')
        self.assertEqual([a['text'] for a in q['suggestedAnswer']], ['B'])
        t = baslik(yanitlar=[yanit(1, 'A', faydali=1), yanit(2, 'B', faydali=0)])
        q = forum_seo.qa_semasi(t, 'u')['mainEntity']
        self.assertNotIn('acceptedAnswer', q)
        self.assertEqual(len(q['suggestedAnswer']), 2)

    def test_gecerli_json_ve_kirinti(self):
        h = forum_seo.sayfa_html(baslik(), BASE, [], True)
        tipler = [d['@type'] for d in jsonld(h)]
        self.assertEqual(tipler, ['QAPage', 'BreadcrumbList'])
        self.assertEqual(jsonld(h)[0]['mainEntity']['author'], {'@type': 'Person', 'name': 'Mehmet'})

    def test_yanitsiz_qapage_yok(self):
        h = forum_seo.sayfa_html(baslik(yanitlar=[]), BASE, [], False)
        self.assertEqual([d['@type'] for d in jsonld(h)], ['BreadcrumbList'])


class KaliteTesti(unittest.TestCase):
    def test_uygun(self):
        self.assertTrue(forum_seo.uygun(baslik()))

    def test_insan_yaniti_sart(self):
        self.assertFalse(forum_seo.uygun(baslik(yanitlar=[])))
        self.assertFalse(forum_seo.uygun(baslik(yanitlar=[yanit(1, rol='asistan')])))

    def test_kelime_esigi(self):
        self.assertFalse(forum_seo.uygun(baslik(govde='kısa soru')))

    def test_gizli_ve_otomatik_yazar(self):
        self.assertFalse(forum_seo.uygun(baslik(gizli=True)))
        self.assertFalse(forum_seo.uygun(baslik(silindi=1)))
        self.assertFalse(forum_seo.uygun(baslik(rol='sistem')))
        self.assertFalse(forum_seo.uygun(baslik(yanitlar=[dict(yanit(1), gizli=True)])))


class YazimTesti(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)
        (self.docs / 'llms.txt').write_text('# KPSS Tercihi\n', encoding='utf-8')
        self.addCleanup(self.tmp.cleanup)

    def sayfa(self, k):
        return (self.docs / 'forum' / 'soru' / k / 'index.html').read_text(encoding='utf-8')

    def uc(self):
        return [baslik(1), baslik(2, 'Ön lisans puanı'), baslik(3, 'Üçüncü soru'), baslik(4, 'Kısa', govde='kısa', yanitlar=[])]

    def test_kapaliyken_hepsi_noindex_haritada_yok(self):
        adresler = forum_seo.yaz(self.docs, BASE, dizinle=False, basliklar=self.uc())
        self.assertEqual(adresler, [])
        dosyalar = list((self.docs / 'forum').rglob('index.html'))
        self.assertEqual(len(dosyalar), 4 + 1)   # 4 soru + 1 konu
        for f in dosyalar:
            self.assertIn('noindex,follow', f.read_text(encoding='utf-8'), f)
        self.assertEqual((self.docs / 'llms.txt').read_text(encoding='utf-8'), '# KPSS Tercihi\n')
        self.assertEqual(forum_seo.SON_DEGISIM, {})

    def test_kabuk_kapaliyken_noindex(self):
        with mock.patch.object(forum_seo, 'FORUM_DIZINLE', False):
            forum_seo.yaz(self.docs, BASE, basliklar=self.uc())
            _, h = forum_sayfasi.forum_sayfasi(BASE)
        self.assertIn('noindex', h)
        self.assertNotIn('fq-son', h)

    def test_acikken_yalniz_uygunlar_indekslenir(self):
        with mock.patch.object(forum_seo, 'FORUM_DIZINLE', True):
            adresler = forum_seo.yaz(self.docs, BASE, basliklar=self.uc())
            self.assertNotIn('noindex', self.sayfa(forum_seo.klasor_adi(baslik(1))))
            self.assertIn('noindex', self.sayfa('4-kisa'))
            self.assertIn(f'{BASE}forum/soru/1-zabita-memuru-ilani-icin-puan-kac/', adresler)
            self.assertNotIn(f'{BASE}forum/soru/4-kisa/', adresler)
            self.assertIn(f'{BASE}forum/konu/puan/', adresler)   # 3 uygun soru
            self.assertIn('## Forum soruları', (self.docs / 'llms.txt').read_text(encoding='utf-8'))
            _, h = forum_sayfasi.forum_sayfasi(BASE)
            self.assertNotIn('noindex', h)
            self.assertIn('soru/1-zabita-memuru-ilani-icin-puan-kac/', h)

    def test_konu_sayfasi_az_soruyla_noindex(self):
        with mock.patch.object(forum_seo, 'FORUM_DIZINLE', True):
            adresler = forum_seo.yaz(self.docs, BASE, basliklar=self.uc()[:2])
        self.assertNotIn(f'{BASE}forum/konu/puan/', adresler)
        self.assertIn('noindex', (self.docs / 'forum' / 'konu' / 'puan' / 'index.html').read_text(encoding='utf-8'))

    def test_oda_ve_etkinlik_uretilmez(self):
        forum_seo.yaz(self.docs, BASE, dizinle=False, basliklar=[baslik(1), baslik(9, 'Oda', kategori='oda')])
        # basliklar dışarıdan verildiğinde süzme cek() içindedir; yine de kategori sözlükte olmayan konu sayfası üretilmez
        self.assertFalse((self.docs / 'forum' / 'konu' / 'oda').exists())

    def test_api_hatasinda_eski_sayfalar_korunur(self):
        forum_seo.yaz(self.docs, BASE, dizinle=False, basliklar=self.uc())
        once = sorted(p.name for p in (self.docs / 'forum' / 'soru').iterdir())
        with mock.patch.object(forum_seo, 'getir', side_effect=urllib.error.URLError('kapalı')):
            self.assertEqual(forum_seo.yaz(self.docs, BASE, dizinle=False), [])
        self.assertEqual(sorted(p.name for p in (self.docs / 'forum' / 'soru').iterdir()), once)

    def test_api_hatasinda_acikken_harita_eski_sayfalardan(self):
        with mock.patch.object(forum_seo, 'FORUM_DIZINLE', True):
            forum_seo.yaz(self.docs, BASE, basliklar=self.uc())
            with mock.patch.object(forum_seo, 'getir', side_effect=TimeoutError('zaman aşımı')):
                adresler = forum_seo.yaz(self.docs, BASE)
        self.assertIn(f'{BASE}forum/soru/1-zabita-memuru-ilani-icin-puan-kac/', adresler)
        self.assertNotIn(f'{BASE}forum/soru/4-kisa/', adresler)

    def test_silinen_baslik_yalniz_basarida_kaldirilir(self):
        forum_seo.yaz(self.docs, BASE, dizinle=False, basliklar=self.uc())
        self.assertTrue((self.docs / 'forum' / 'soru' / '2-on-lisans-puani').exists())
        # başarılı çağrı, 2 numara artık yok
        forum_seo.yaz(self.docs, BASE, dizinle=False, basliklar=[baslik(1), baslik(3, 'Üçüncü soru'), baslik(4, 'Kısa', govde='kısa', yanitlar=[])])
        self.assertFalse((self.docs / 'forum' / 'soru' / '2-on-lisans-puani').exists())
        self.assertTrue((self.docs / 'forum' / 'soru' / '1-zabita-memuru-ilani-icin-puan-kac').exists())

    def test_cek_sayfalar_ve_ayrinti(self):
        def sahte(url, zaman=10):
            if '/basliklar' in url:
                sayfa = int(re.search(r'sayfa=(\d+)', url).group(1))
                return {'basliklar': [{'id': sayfa, 'baslik': f'S{sayfa}', 'kategori': 'puan'}, {'id': 90 + sayfa, 'baslik': 'Oda', 'kategori': 'oda'}],
                        'sonraki': sayfa < 2}
            i = int(re.search(r'/baslik/(\d+)', url).group(1))
            return {'baslik': baslik(i, f'S{i}'), 'yanitlar': [yanit(1)]}
        with mock.patch.object(forum_seo, 'getir', sahte):
            r = forum_seo.cek('http://x')
        self.assertEqual(sorted(t['id'] for t in r), [1, 2])

    def test_cek_ayrinti_hatasi_tum_cekimi_basarisiz_sayar(self):
        def sahte(url, zaman=10):
            if '/basliklar' in url:
                return {'basliklar': [{'id': 1, 'baslik': 'S', 'kategori': 'puan'}], 'sonraki': False}
            raise urllib.error.URLError('kopuk')
        with mock.patch.object(forum_seo, 'getir', sahte), self.assertRaises(forum_seo.ForumApiHatasi):
            forum_seo.cek('http://x')


if __name__ == '__main__':
    unittest.main()
