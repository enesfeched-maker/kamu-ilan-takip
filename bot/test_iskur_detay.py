import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import ek_kaynaklar as ek
import ilan_bot
import iskur_detay
from site_uret import detail_page

VERI = Path(__file__).parent / 'test_veri'


def sayfalar(ad):
    # PDF'lerden çıkarılmış düz metin; EBYS damgasındaki kişi adı yer tutucuyla değiştirilmiştir.
    return (VERI / f'iskur_{ad}.sayfalar.txt').read_text(encoding='utf-8').split('\f')


def yerlesim(ad):
    return (VERI / f'iskur_{ad}.layout.txt').read_text(encoding='utf-8').split('\f')


def ozet(ad, baslik='Örnek Belediyesi Memur Alım İlanı'):
    return iskur_detay.ozetle_metin(sayfalar(ad), {'baslik': baslik}, 'abc', yerlesim(ad))


def tum_metinler(deger):
    if isinstance(deger, str):
        yield deger
    elif isinstance(deger, list):
        for x in deger:
            yield from tum_metinler(x)
    elif isinstance(deger, dict):
        for x in deger.values():
            yield from tum_metinler(x)


class ParseTests(unittest.TestCase):
    def test_bahce(self):
        o = ozet('bahce_memur')
        self.assertEqual(o['kadro'], '1 Memur')
        self.assertEqual(o['sartlar'][0]['kadro'], 'Memur · 1 kadro')
        self.assertIn('KPSS P3', o['sartlar'][0]['metin'])
        self.assertIn('en az 55', o['sartlar'][0]['metin'])
        self.assertTrue(o['ozet'].startswith('Osmaniye ili Bahçe Belediye Başkanlığı bünyesinde'))
        self.assertTrue(o['ozet'].endswith('memur alınacaktır.'))
        self.assertIn('iletisim@bahce.bel.tr', o['basvuru_notu'])
        self.assertNotIn('D evlet', o['ozet'])
        self.assertEqual(o['iskur_detay_surumu'], iskur_detay.VERSION)
        self.assertEqual(o['iskur_belge_sha256'], 'abc')
        self.assertNotIn('belge_ozeti', o)
        self.assertNotIn('belge_kopyasi', o)

    def test_gole(self):
        o = ozet('gole_memur')
        self.assertEqual(o['kadro'], 'Toplam 3 kişi — 1 Ayniyat Memuru • 1 Anbar Memuru • 1 Memur')
        self.assertEqual(ek.total(o), 3)
        metinler = [s['metin'] for s in o['sartlar'][:3]]
        for metin, pt, taban in zip(metinler, ('P3', 'P3', 'P94'), ('75', '70', '60')):
            self.assertIn(f'KPSS {pt} puan türünden en az {taban} puan', metin)
        item = {'baslik': 'Göle Belediyesi Memur Alım İlanı', 'kurum': 'Göle Belediyesi', 'yer': 'Ardahan', **o}
        ilan_bot.siniflandir(item)
        self.assertIn('lisans', item['ogrenim'])
        self.assertIn('ortaogretim', item['ogrenim'])
        self.assertEqual(item['kpss'], 'kpss')
        self.assertTrue('gole.bel.tr' in o['basvuru_notu'] or 'Göle' in o['basvuru_notu'])

    def test_atalan_pozisyon(self):
        o = ozet('atalan_sozlesmeli', 'Atalan Belediyesi Sözleşmeli Personel Alım İlanı')
        self.assertEqual(o['kadro'], '1 Tekniker')
        self.assertIn('pozisyon', o['sartlar'][0]['kadro'])
        self.assertIn('TH', o['sartlar'][0]['metin'])
        self.assertIn('P93', o['sartlar'][0]['metin'])
        item = {'baslik': 'Atalan Belediyesi Sözleşmeli Personel Alım İlanı', 'kurum': 'Atalan Belediyesi', 'yer': 'Osmaniye', **o}
        ilan_bot.siniflandir(item)
        self.assertEqual(item['ogrenim'], ['onlisans'])

    def test_seddk_damga_ayiklanir(self):
        o = ozet('seddk_genel', 'SEDDK Açıktan Personel Alım İlanı')
        self.assertNotIn('kadro', o)
        self.assertTrue(o['ozet'].startswith('Sigortacılık ve Özel Emeklilik'))
        self.assertTrue(o['ozet'].endswith('personel alınacaktır.'))
        self.assertIn('kariyerkapisi.gov.tr', o['basvuru_notu'])
        for metin in tum_metinler(o):
            self.assertNotIn('EBYS', metin)
            self.assertNotIn('PAZARTESİ', metin)

    def test_damga_adi_gelse_bile_yayimlanmaz(self):
        # Gerçek damga satır sonlarıyla bölünmüş gelir; kişi adı çıktıya sızmamalı.
        sayfa = '14/9/2026 PAZARTESİ AD \nSOYAD \n9310 \nEBYS \n1\nKurumumuz bünyesinde çalışmak üzere sınav sonuçlarına göre yeterli sayıda personel alınacaktır.'
        o = iskur_detay.ozetle_metin([sayfa], {'baslik': 'X'})
        for metin in tum_metinler(o):
            self.assertNotIn('SOYAD', metin)
            self.assertNotIn('EBYS', metin)

    def test_fixture_kisi_adi_icermez(self):
        for p in VERI.glob('iskur_*.sayfalar.txt'):
            self.assertNotIn('ÇEŞİTLİ', p.read_text(encoding='utf-8'))
        for p in VERI.glob('iskur_*.layout.txt'):
            self.assertNotIn('ÇEŞİTLİ', p.read_text(encoding='utf-8'))

    def test_pdf_degil(self):
        with self.assertRaises(ValueError):
            iskur_detay.ozetle(b'not a pdf', {})

    def test_bos_alan_yok(self):
        for ad in ('bahce_memur', 'gole_memur', 'atalan_sozlesmeli', 'seddk_genel'):
            for k, v in ozet(ad).items():
                self.assertTrue(v, k)
        o = iskur_detay.ozetle_metin(['Merhaba dünya.'], {'baslik': 'X'})
        self.assertEqual(set(o), {'iskur_detay_surumu', 'iskur_detay_guncelleme'})


class RowTests(unittest.TestCase):
    def test_sehir_tablosu(self):
        html = (VERI / 'iskur_il_osmaniye.html').read_text(encoding='utf-8')
        rows = ek.iskur_rows(html, 'Osmaniye')
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]['link'].endswith('/ykdb03ym/osmaniye-bah%C3%A7e-belediyesi-memur-al%C4%B1m-ilan%C4%B1-06102026.pdf'))
        self.assertIn('/x0emsn5d/', rows[1]['link'])
        self.assertTrue(rows[1]['link'].endswith('27102026.pdf'))
        self.assertEqual(rows[0]['son_zaman'], '2026-10-06T17:00:00+03:00')


def sehir_html(n):
    satir = '<tr class="clickable-row" data-has-file="True" data-file-url="/medya/id{i}/ilan-{i}.pdf"><td>30.10.2026 17:00</td><td>Örnek{i} Belediyesi Memur Alım İlanı 30.10.2026</td></tr>'
    return ''.join(satir.format(i=i) for i in range(n)).encode()


class ReadIskurTests(unittest.TestCase):
    def calistir(self, html, previous, pdf=None):
        pdf_istekleri = []

        def sahte_get(op, url, referer=None):
            if url == ek.ISKUR:
                return b'', url
            if url.startswith(ek.ISKUR + '?'):
                return html, url
            pdf_istekleri.append(url)
            if isinstance(pdf, Exception):
                raise pdf
            return b'%PDF-sahte', url
        with patch.object(ek, 'get', sahte_get), patch.object(ek, 'iskur_cities', return_value=[('osmaniye', 'Osmaniye')]), \
                patch.object(ek.time, 'sleep'), patch.object(iskur_detay, 'sayfa_metinleri', return_value=(sayfalar('bahce_memur'), yerlesim('bahce_memur'))), \
                contextlib.redirect_stdout(io.StringIO()):
            records, errors = ek.read_iskur(previous)
        return records, errors, pdf_istekleri

    def test_indir_onbellekle_hata_ve_sinir(self):
        html = sehir_html(1)
        records, errors, istekler = self.calistir(html, {})
        self.assertEqual((errors, len(istekler)), (0, 1))
        self.assertEqual(records[0]['kadro'], '1 Memur')
        self.assertEqual(records[0]['iskur_detay_surumu'], iskur_detay.VERSION)
        self.assertNotIn('iskur_detay_denemesi', records[0])
        onceki = {r['id']: r for r in records}
        # (b) önbellekten gelir, tekrar indirilmez
        records2, _, istekler2 = self.calistir(html, onceki)
        self.assertEqual(istekler2, [])
        self.assertEqual(records2[0]['kadro'], '1 Memur')
        # (c) sürüm eskidiyse yeniden dener; hata olursa önceki alanlar korunur
        eski = {k: {**v, 'iskur_detay_surumu': 0} for k, v in onceki.items()}
        records3, errors3, istekler3 = self.calistir(html, eski, pdf=OSError('boom'))
        self.assertEqual((errors3, len(istekler3)), (0, 1))
        self.assertEqual(records3[0]['kadro'], '1 Memur')
        self.assertIn('iskur_detay_denemesi', records3[0])
        # deneme 12 saat içindeyse tekrar indirilmez
        records4, _, istekler4 = self.calistir(html, {r['id']: r for r in records3})
        self.assertEqual(istekler4, [])
        self.assertEqual(records4[0]['kadro'], '1 Memur')
        # (c2) ilk kez hata: satır döner, ayrıntı yok, deneme işaretli
        records5, errors5, _ = self.calistir(html, {}, pdf=OSError('boom'))
        self.assertEqual(errors5, 0)
        self.assertNotIn('kadro', records5[0])
        self.assertIn('iskur_detay_denemesi', records5[0])
        # (d) bütçe
        records6, _, istekler6 = self.calistir(sehir_html(20), {})
        self.assertEqual((len(records6), len(istekler6)), (20, ek.ISKUR_PDF_SINIRI))
        self.assertEqual(sum(1 for r in records6 if r.get('kadro')), ek.ISKUR_PDF_SINIRI)


class DigerKaynakTests(unittest.TestCase):
    def test_baska_kaynak_kaydina_indirme_yapilmaz(self):
        row = ek.iskur_rows((VERI / 'iskur_il_osmaniye.html').read_text(encoding='utf-8'), 'Osmaniye')[0]
        onceki = {'x': {**row, 'kaynak_turu': 'sbb', 'kaynak_kimlikleri': [row['id']], 'id': 'x'}}
        with patch.object(ek, 'get') as g, patch.object(ek.time, 'sleep'):
            ek.iskur_zenginlestir(None, [row], onceki)
        g.assert_not_called()
        self.assertNotIn('kadro', row)


class MergeAndPageTests(unittest.TestCase):
    def test_iskur_kadro_olsa_da_sbb_ile_birlesir(self):
        sbb = {'id': 'old', 'baslik': 'Örnek Belediyesi memur alımı', 'kurum': 'Örnek Belediyesi', 'son_tarih': '2026-10-09',
               'kadro': '1 Memur', 'kaynak_turu': 'sbb', 'link': ek.SBB}
        iskur = {**sbb, 'id': 'new', 'kaynak_turu': 'iskur', 'link': 'https://www.iskur.gov.tr/medya/x.pdf',
                 'kadro': 'Toplam 3 kişi — 1 Memur • 1 VHKİ • 1 Tahsildar'}
        self.assertTrue(ek.same_listing(iskur, sbb))
        merged = ek.merge_sources([iskur], {'old': sbb})
        self.assertEqual([i['id'] for i in merged], ['old'])

    def test_detay_sayfasi(self):
        rows = ek.iskur_rows((VERI / 'iskur_il_osmaniye.html').read_text(encoding='utf-8'), 'Osmaniye')
        bos = detail_page(rows[0])[1]
        self.assertIn('henüz kaynaktan okunamadı', bos)
        self.assertNotIn('Seçilmiş alıntılardır', bos)
        dolu = detail_page({**rows[0], **ozet('bahce_memur')})[1]
        for parca in ('Kadro ve başvuru koşulları', '1 Memur', 'Başvuru koşullarından seçmeler'):
            self.assertIn(parca, dolu)
        self.assertNotIn('henüz kaynaktan okunamadı', dolu)


if __name__ == '__main__':
    unittest.main()
