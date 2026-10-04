import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import site_uret
from site_uret import TR, detail_page, _duzgun
import kurum_sayfasi as ks

KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=%s'
SIMDI = datetime(2026, 10, 3, 12, 0, tzinfo=TR)


def uid(n):
    return '%08d-1111-4111-8111-111111111111' % n


def ilan(n, kurum, **ek):
    return {'id': KK % uid(n), 'link': KK % uid(n), 'baslik': kurum + ' Alım İlanı', 'kurum': kurum,
            'kadro': '2 Zabıta Memuru', 'son_tarih': '2026-12-31', 'ogrenim': ['lisans'], **ek}


class SlugTests(unittest.TestCase):
    def test_turkce_karakterler(self):
        self.assertEqual(ks.kurum_slug('Çanakkale Onsekiz Mart Üniversitesi Rektörlüğü'), 'canakkale-onsekiz-mart-universitesi')
        self.assertEqual(ks.kurum_slug('Iğdır Şırnak İşçi Ğ'), 'igdir-sirnak-isci-g')

    def test_belediye_birlesir(self):
        s = {ks.kurum_slug(k) for k in ('Mucur Belediyesi', 'Kırşehir Mucur Belediyesi', 'MUCUR BELEDİYE BAŞKANLIĞI', 'Mucur (Kırşehir) Belediye Başkanlığı')}
        self.assertEqual(s, {'mucur-belediyesi'})

    def test_buyuksehir_ve_il_belediyesi_korunur(self):
        self.assertEqual(ks.kurum_slug('Ankara Büyükşehir Belediyesi'), 'ankara-buyuksehir-belediyesi')
        self.assertEqual(ks.kurum_slug('Rize Belediyesi'), ks.kurum_slug('Rize Belediye Başkanlığı'))
        self.assertEqual(ks.kurum_slug('Rize Belediyesi'), 'rize-belediyesi')

    def test_uzunluk_siniri(self):
        self.assertLessEqual(len(ks.kurum_slug('A ' * 100 + 'Müdürlüğü')), 80)

    def test_cakisma_il_ekler(self):
        a = ilan(1, 'Gökçeada Belediyesi', iller=['Çanakkale'])
        b = ilan(2, 'Gökçeada Üniversitesi', iller=['Çanakkale'])
        with mock.patch.object(ks, 'kurum_slug', return_value='ayni'):
            _, slugler = ks.kurum_gruplari([a, b])
        self.assertEqual(len(set(slugler.values())), 2)
        self.assertTrue(all(s.startswith('ayni-') for s in slugler.values()))


class IlAyirmaTests(unittest.TestCase):
    def bol(self, *ilanlar):
        return ks.kurum_gruplari(list(ilanlar))

    def test_ayni_adli_farkli_il_ayrilir(self):
        for a, b in ((('Çanakkale Yenice Belediyesi', 'Çanakkale'), ('Karabük Yenice Belediyesi', 'Karabük')),
                     (('Rize Pazar Belediyesi', 'Rize'), ('Pazar (Tokat) Belediye Başkanlığı', 'Tokat')),
                     (('Malatya Kale Belediyesi', 'Malatya'), ('Kale (Denizli) Belediyesi', 'Denizli'))):
            g, s = self.bol(ilan(1, a[0], iller=[a[1]]), ilan(2, b[0], iller=[b[1]]))
            self.assertEqual(len(g), 2, a)
            self.assertEqual(len(set(s.values())), 2)
        g, s = self.bol(ilan(1, 'Gölbaşı Belediyesi', iller=['Ankara']), ilan(2, 'Gölbaşı Belediyesi', iller=['Adıyaman']))
        self.assertEqual(sorted(s.values()), ['golbasi-belediyesi-adiyaman', 'golbasi-belediyesi-ankara'])

    def test_il_slug_ve_gorunen_ad(self):
        a = ilan(1, 'Yenice Belediyesi', iller=['Çanakkale'])
        b = ilan(2, 'Yenice Belediyesi', iller=['Karabük'])
        g, s = self.bol(a, b)
        self.assertIn('yenice-belediyesi-canakkale', s.values())
        kan = next(k for k in g if k.endswith('|canakkale'))
        html = ks.kurum_sayfasi(kan, g[kan], s[kan], {}, SIMDI)
        self.assertIn('Yenice Belediyesi (Çanakkale)', html)

    def test_mucur_hala_birlesir(self):
        g, s = self.bol(ilan(1, 'Kırşehir Mucur Belediyesi'), ilan(2, 'MUCUR BELEDİYE BAŞKANLIĞI', iller=['Kırşehir']),
                        ilan(3, 'Mucur (Kırşehir) Belediye Başkanlığı'), ilan(4, 'Mucur Belediyesi'))
        self.assertEqual(len(g), 1)
        self.assertEqual(list(s.values()), ['mucur-belediyesi'])

    def test_ilsiz_kayit_tek_il_varsa_katilir(self):
        g, _ = self.bol(ilan(1, 'Yenice Belediyesi', iller=['Çanakkale']), ilan(2, 'Yenice Belediyesi'))
        self.assertEqual([len(v) for v in g.values()], [2])

    def test_detay_sayfasiz_kayit_sayilmaz(self):
        kotu = {'id': 'x', 'link': 'https://evil.example/x', 'kurum': 'A Belediyesi', 'baslik': 'x'}
        g, _ = self.bol(ilan(1, 'A Belediyesi'), kotu)
        self.assertEqual([len(v) for v in g.values()], [1])

    def test_sayfasi_yazilamayan_grupta_baglanti_yok(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bozuk = ilan(1, 'A Belediyesi')
        gercek = ks.kart_html

        def kart(item, *a, **k):
            if item is bozuk:
                raise ValueError('bozuk tarih')
            return gercek(item, *a, **k)
        with mock.patch.object(ks, 'kart_html', side_effect=kart):
            sonuc = ks.kurum_sayfalarini_uret([bozuk, ilan(2, 'B Belediyesi')], Path(tmp.name), {}, SIMDI)
        self.assertEqual(len(sonuc[3]), 1)
        meta = ks.kart_meta([bozuk, ilan(2, 'B Belediyesi')], sonuc[3])
        self.assertNotIn('kurum_slug', meta[uid(1)])
        self.assertIn('kurum_slug', meta[uid(2)])
        self.assertFalse((Path(tmp.name) / 'kurum' / 'a-belediyesi').exists())


class BaslikTests(unittest.TestCase):
    def test_tek_kadro(self):
        a = ks.kart_alanlari({'baslik': 'X Üniversitesi 4/B', 'kurum': 'X Üniversitesi', 'kadro': '23 Sağlık Teknikeri'})
        self.assertEqual(a['manset'], '23 Sağlık Teknikeri')
        self.assertEqual(a['toplam'], 23)
        self.assertNotIn('ek', a)

    def test_cok_kadro_ve_ek(self):
        a = ks.kart_alanlari({'baslik': 'Karma', 'kurum': 'K', 'kadro': 'Toplam 77 kişi — 40 Hemşire • 20 Destek Personeli • 10 Sağlık Teknikeri • 4 Şoför • 3 Aşçı'})
        self.assertEqual(a['manset'], 'Hemşire, Destek Personeli, Sağlık Teknikeri')
        self.assertEqual(a['ek'], 2)
        self.assertEqual(a['toplam'], 77)
        self.assertEqual(len(a['meslek']), 3)

    def test_alacak_ayiklanir(self):
        a = ks.kart_alanlari({'baslik': 'b', 'kurum': 'K', 'kadro': '3 Memur ALACAK'})
        self.assertEqual(a['manset'], '3 Memur')
        a = ks.kart_alanlari({'baslik': 'b', 'kurum': 'K', 'kadro': '5 Zabıta Memuru ALINACAK'})
        self.assertEqual(a['manset'], '5 Zabıta Memuru')

    def test_kurum_kekemesi(self):
        self.assertEqual(ks.temiz_baslik({'baslik': 'HANAK BELEDİYE BAŞKANLIĞI - Memur Alım İlanı', 'kurum': 'Hanak Belediye Başkanlığı'}), 'Memur Alım İlanı')
        self.assertEqual(ks.temiz_baslik({'baslik': 'Hanak Belediye Memur Alım İlanı', 'kurum': 'Hanak Belediye Başkanlığı'}), 'Memur Alım İlanı')

    def test_duyuru_kadrosuz(self):
        a = ks.kart_alanlari({'baslik': 'Düzeltme İlanı', 'kurum': 'K', 'duyuru_turu': 'Düzeltme', 'kadro': '5 Memur'})
        self.assertEqual(a['manset'], 'Düzeltme İlanı')
        self.assertNotIn('toplam', a)
        self.assertEqual(a['alt'], 'Kamu personel alımı')

    def test_ve_ile_kucuk(self):
        self.assertEqual(_duzgun('SİGORTACILIK VE ÖZEL EMEKLİLİK'), 'Sigortacılık ve Özel Emeklilik')
        self.assertEqual(ks.kurum_adi('SEDDK (SEDDK) VE X'), 'Seddk (SEDDK) ve X')


class SayfaTests(unittest.TestCase):
    def kos(self, ilanlar, gorseller=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        docs = Path(tmp.name)
        sonuc = ks.kurum_sayfalarini_uret(ilanlar, docs, gorseller or {}, SIMDI)
        return docs, sonuc

    def test_sayfa_uretilir_akademik_haric_ad_kacirilir(self):
        ilanlar = [ilan(1, 'A <b>Belediyesi</b>'), ilan(2, 'A <b>Belediyesi</b>', son_tarih='2026-01-01'),
                   ilan(3, 'X Üniversitesi', baslik='Öğretim Görevlisi alımı', kategori='akademik')]
        docs, (gruplar, slugler, adresler, _) = self.kos(ilanlar)
        self.assertEqual(len(gruplar), 1)
        self.assertEqual(len(adresler), 1)
        klasorler = [p.name for p in (docs / 'kurum').iterdir()]
        self.assertEqual(len(klasorler), 1)
        html = (docs / 'kurum' / klasorler[0] / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('<b>Belediyesi', html)
        self.assertIn('&lt;b&gt;', html)
        self.assertIn('Başvurusu açık ilanlar', html)
        self.assertIn('Duyurular ve geçmiş ilanlar', html)
        self.assertIn(f'../../ilan/{uid(1)}/', html)

    def test_bos_durum(self):
        docs, _ = self.kos([ilan(1, 'A Belediyesi', son_tarih='2026-01-01')])
        html = next((docs / 'kurum').glob('*/index.html')).read_text(encoding='utf-8')
        self.assertIn('Şu an başvurusu açık ilan yok', html)

    def test_eski_klasor_silinir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        docs = Path(tmp.name)
        (docs / 'kurum' / 'eski-kurum').mkdir(parents=True)
        (docs / 'kurum' / 'eski-kurum' / 'index.html').write_text('x', encoding='utf-8')
        ks.kurum_sayfalarini_uret([ilan(1, 'A Belediyesi')], docs, {}, SIMDI)
        self.assertFalse((docs / 'kurum' / 'eski-kurum').exists())
        self.assertTrue((docs / 'kurum' / 'a-belediyesi' / 'index.html').is_file())

    def test_main_sitemap_ve_gorseller_alanlari(self):
        with tempfile.TemporaryDirectory() as t:
            kok = Path(t)
            (kok / 'docs').mkdir()
            veri = [ilan(1, 'Ankara Belediyesi'), ilan(2, 'Ankara Belediyesi'), ilan(3, 'X Üniversitesi', kategori='akademik', baslik='Öğretim Görevlisi')]
            (kok / 'docs' / 'ilanlar.json').write_text(json.dumps({'ilanlar': veri}), encoding='utf-8')
            with mock.patch.object(site_uret, 'ROOT', kok), mock.patch.object(site_uret, 'gorselleri_uret', return_value={}), \
                    mock.patch('sosyal_paylasim.uret', side_effect=RuntimeError('atla')):
                site_uret.main()
            g = json.loads((kok / 'docs' / 'ilan' / 'gorseller.json').read_text(encoding='utf-8'))
            self.assertEqual(g[uid(1)]['kurum_slug'], 'ankara-belediyesi')
            self.assertEqual(g[uid(1)]['kurum_sayisi'], 2)
            self.assertEqual(g[uid(1)]['manset'], '2 Zabıta Memuru')
            self.assertTrue(1 <= len(g[uid(1)]['meslek']) <= 3)
            self.assertNotIn(uid(3), g)
            sm = (kok / 'docs' / 'sitemap.xml').read_text(encoding='utf-8')
            self.assertIn('/kurum/ankara-belediyesi/', sm)
            self.assertNotIn('universitesi', sm)

    def test_detay_sayfasi_kurum_baglantisi(self):
        i = ilan(1, 'Ankara Belediyesi')
        html = detail_page(i, {'kurum_slug': 'ankara-belediyesi', 'kurum_sayisi': 6})[1]
        self.assertIn('href="../../kurum/ankara-belediyesi/"', html)
        self.assertIn('Bu kurumun tüm ilanları (6)', html)
        tek = detail_page(i, {'kurum_slug': 'ankara-belediyesi', 'kurum_sayisi': 1})[1]
        self.assertIn('Kurum sayfası', tek)
        self.assertNotIn('tüm ilanları (', tek)
        yok = detail_page(i)[1]
        self.assertIn('href="../../kurum/ankara-belediyesi/"', yok)


class YeniBicimTests(unittest.TestCase):
    def kayit(self, n, manset='2 Zabıta Memuru', **ek):
        return {'key': uid(n), 'manset': manset, 'kurum': 'A <b>Belediyesi</b>', 'kurum_slug': 'a-belediyesi', 'meslek': ['07-zabita.jpg'],
                'il': 'Ankara', 'ogrenim': ['lisans'], 'puan_turleri': ['P3'], 'son_tarih': '2026-10-20', 'durum': 'ok', 'toplam': 2, **ek}

    def test_satir_kacis_ve_kaydet(self):
        h = ks.satir_html(self.kayit(1, manset='<img src=x onerror=1>', taban_ref={'lisans': {'medyan': 80.5, 'n': 9}}), SIMDI)
        self.assertNotIn('<img src=x', h)
        self.assertNotIn('<b>Belediyesi', h)
        self.assertIn('class="ilan"', h)
        self.assertIn(f'data-kaydet="{uid(1)}"', h)
        self.assertIn('data-ref=', h)
        self.assertIn('href="../../ilan/%s/"' % uid(1), h)

    def test_detay_yeni_iskelet(self):
        i = ilan(1, 'A <b>Belediyesi</b>', sartlar=[{'kadro': 'Zabıta Memuru', 'metin': '<i>x</i> KPSS P3'}])
        html = detail_page(i, {'kurum_slug': 'a-belediyesi', 'kurum_sayisi': 3},
                           self.kayit(1, taban_ref={'lisans': {'medyan': 80.5, 'n': 9, 'donem': '2025-2/2026-1'}}),
                           [self.kayit(n) for n in range(2, 9)], SIMDI)[1]
        self.assertIn('rel="manifest" href="../../manifest.webmanifest"', html)
        self.assertIn('sayfa.css', html)
        self.assertNotIn('portal.css', html)
        self.assertIn('Resmî ilana git · Başvur', html)
        self.assertIn('id="kaydet-btn"', html)
        self.assertIn(f'data-kaydet="{site_uret.esc(i["id"])}"', html)
        self.assertIn('Senin için', html)
        self.assertIn('80,5', html)
        self.assertIn('Geçmiş yerleştirmelerden referans; bu ilanın şartı değildir', html)
        self.assertNotIn('<i>x</i>', html)
        self.assertNotIn('<b>Belediyesi', html)
        self.assertEqual(html.count('<article class="ilan"'), 5)
        self.assertIn('Benzer ilanlar', html)
        self.assertIn('Bu kurumun tüm ilanları (3)', html)
        self.assertIn('"light"', html)

    def test_benzer_ilanlar_sinir_ve_siralama(self):
        k = self.kayit(1)
        digerleri = [self.kayit(n, son_tarih=f'2026-10-{30 - n}') for n in range(2, 9)] + [self.kayit(20, manset='Hemşire', meslek=['02-hemsire.jpg'])]
        s = site_uret.benzer_ilanlar(k, [k] + digerleri)
        self.assertEqual(len(s), 5)
        self.assertNotIn(uid(1), [x['key'] for x in s])
        self.assertNotIn(uid(20), [x['key'] for x in s])
        self.assertEqual(s[0]['key'], uid(8))
        self.assertEqual(site_uret.benzer_ilanlar(None, digerleri), [])

    def test_kurum_sayfasi_yeni_bicim(self):
        g, s = ks.kurum_gruplari([ilan(1, 'A Belediyesi'), ilan(2, 'A Belediyesi', son_tarih='2026-01-01')])
        kan = next(iter(g))
        html = ks.kurum_sayfasi(kan, g[kan], s[kan], {}, SIMDI)
        self.assertIn('class="ilan"', html)
        self.assertIn("Telegram'da takip et", html)
        self.assertIn('class="kp-tablo"', html)
        self.assertIn('rel="manifest"', html)
        self.assertNotIn('class="card"', html)

    def test_manifest_ve_puanlar(self):
        m = json.loads((site_uret.ROOT / 'docs' / 'manifest.webmanifest').read_text(encoding='utf-8'))
        self.assertEqual(m['start_url'], './?g=bugun')
        self.assertEqual(m['display'], 'standalone')
        for ic in m['icons']:
            self.assertTrue((site_uret.ROOT / 'docs' / ic['src']).is_file())
        puan = (site_uret.ROOT / 'docs' / 'puanlar' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('rel="manifest" href="../manifest.webmanifest"', puan)
        self.assertIn('sayfa.css', puan)


if __name__ == '__main__':
    unittest.main()
