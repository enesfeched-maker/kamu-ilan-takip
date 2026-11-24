import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import yz_claude as yc
import yz_isle
from site_uret import TR
from yz_denetim import SURUM

SIMDI = datetime(2026, 10, 30, 14, 0, tzinfo=TR)
ILAN = {'id': 'csb-1', 'baslik': 'Örnek Belediyesi zabıta memuru alacak', 'kurum': 'Örnek Belediyesi',
        'kaynak_turu': 'csb', 'son_tarih': '2026-12-11', 'ilk_gorulme': '2026-10-30T12:30:00+03:00', 'kadro': '9 ALACAK'}
CIKTI = {'kadrolar': [{'unvan': 'Zabıta Memuru — Kadın', 'adet': 3, 'ogrenim': 'lisans', 'puan_turu': 'P3',
                       'en_dusuk_puan': 60, 'kosullar': ['Herhangi bir lisans programından mezun olmak.']},
                      {'unvan': 'Zabıta Memuru — Erkek', 'adet': 6, 'ogrenim': 'lisans', 'puan_turu': 'P3',
                       'en_dusuk_puan': 60, 'kosullar': ['Herhangi bir lisans programından mezun olmak.']}],
         'toplam': 9, 'son_basvuru_tarihi': '2026-12-10', 'baslangic_tarihi': '2026-12-07',
         'ortak_kosullar': ['Türk vatandaşı olmak.', 'Sınavın yapıldığı tarihte 30 yaşını doldurmamış olmak.'],
         'ozet': 'Örnek Belediyesi 9 zabıta memuru alacak. Başvurular 7–10 Aralık 2026 arasında şahsen yapılır.',
         'okunabilirlik': 'iyi'}


class Akis(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'ilanlar.json').write_text(json.dumps({'ilanlar': [ILAN], 'telegram_bekleyen': ['csb-1']}),
                                             encoding='utf-8')
        self.yz = self.d / 'yz.json'
        self.yz.write_text(json.dumps({'eski': {'surum': SURUM - 1, 'zaman': '2026-10-20T10:00:00+03:00'}}),
                           encoding='utf-8')
        self.is_ = self.d / 'is'

    def _hazirla(self, metin=('belge metni', 'csb')):
        with contextlib.redirect_stdout(io.StringIO()):
            return yc.hazirla(5, SIMDI, self.is_, self.d / 'ilanlar.json', self.yz, metin=lambda i: metin)

    def _kaydet(self):
        with contextlib.redirect_stdout(io.StringIO()) as cikti:
            yeni = yc.kaydet(SIMDI, self.is_, self.d / 'ilanlar.json', self.yz)
        return yeni, cikti.getvalue()

    def test_hazirla_kaydet_yayina_esas(self):
        g = self._hazirla()
        self.assertEqual(len(g), 1)
        self.assertEqual(Path(g[0]['metin']).read_text(encoding='utf-8'), 'belge metni')
        Path(g[0]['cikti']).write_text(json.dumps(CIKTI, ensure_ascii=False), encoding='utf-8')
        self._kaydet()
        veri = json.loads(self.yz.read_text(encoding='utf-8'))
        self.assertNotIn('eski', veri)   # eski sürüm (Gemini/Ollama) kayıtları atılır
        k = veri['csb-1']
        self.assertEqual((k['model'], k['surum'], k['kaynak']), ('claude', SURUM, 'csb'))
        self.assertEqual(k['yz']['ortak_kosullar'], ['Sınavın yapıldığı tarihte 30 yaşını doldurmamış olmak.'])
        i = yz_isle.uygula(ILAN, veri, SIMDI)
        self.assertEqual(i['kadro'], 'Toplam 9 kişi — 3 Zabıta Memuru — Kadın • 6 Zabıta Memuru — Erkek')
        self.assertEqual(i['son_tarih'], '2026-12-10')   # Claude belgeden okuduğu tarihi düzeltir
        self.assertIn('9 zabıta memuru', i['ozet'])
        self.assertEqual(yz_isle.yayina_hazir(ILAN, veri, SIMDI), (True, ''))
        self.assertEqual(self._hazirla(), [])   # okunmuş ilan yeniden okunmaz

    def test_bozuk_cikti_kaydedilmez(self):
        g = self._hazirla()
        Path(g[0]['cikti']).write_text(json.dumps({'kadrolar': [{'unvan': 'X', 'adet': 'üç'}]}), encoding='utf-8')
        yeni, metin = self._kaydet()
        self.assertEqual(yeni, {})
        self.assertIn('adet sayı değil', metin)

    def test_cikti_yoksa_atlanir(self):
        self._hazirla()
        self.assertEqual(self._kaydet()[0], {})

    def test_taranmis_belge_claudea_pdf_olarak_verilir(self):
        import yz_yerel
        eski = yz_yerel._sbb_pdf
        yz_yerel._sbb_pdf = lambda i: b'%PDF-1.4 taranmis'
        try:
            g = self._hazirla(('', 'taranmis'))
        finally:
            yz_yerel._sbb_pdf = eski
        self.assertTrue(Path(g[0]['pdf']).is_file())
        self.assertNotIn('metin', g[0])
        Path(g[0]['cikti']).write_text(json.dumps(CIKTI, ensure_ascii=False), encoding='utf-8')
        self._kaydet()
        veri = json.loads(self.yz.read_text(encoding='utf-8'))
        self.assertEqual(veri['csb-1']['kaynak'], 'pdf-gorsel')   # yayına girer (taranmis değil)
        self.assertIn('yz_kadrolar', yz_isle.uygula(ILAN, veri, SIMDI))


class Uyarilar(unittest.TestCase):
    """24 Kasım 2026: kadro kadro eşleştirme (nereye aracı) için eksikler UYARI olur; kayıt reddedilmez."""
    def _kadro(self, **ek):
        k = {'unvan': 'Hemşire', 'adet': 2, 'ogrenim': 'lisans', 'puan_turu': 'P3', 'en_dusuk_puan': 60,
             'kosullar': ['Hemşirelik lisans programından mezun olmak.']}
        k.update(ek)
        return {'kadrolar': [k], 'okunabilirlik': 'iyi'}

    def test_ornek_cikti_temiz(self):
        self.assertEqual(yc.uyarilar(CIKTI), [])
        self.assertEqual(yc.uyarilar(self._kadro()), [])
        self.assertEqual(yc.uyarilar(self._kadro(ogrenim='ortaogretim', kosullar=['B sınıfı sürücü belgesi.'])), [])   # lisede bölüm maddesi şart değil

    def test_uyarilar_kaydi_durdurmaz(self):
        kotu = self._kadro(ogrenim=None, puan_turu='yüzde 70', en_dusuk_puan='70', kosullar=['Fizik, Kimya vb. bölümlerinden mezun olmak.'])
        self.assertEqual(yc.dogrula(kotu), [])
        self.assertEqual(len(yc.uyarilar(kotu)), 4)

    def test_kisaltilmis_bolum_listesi(self):
        for m in ('Bilgisayar, Elektrik vb. mühendislik bölümlerinden mezun olmak.',
                  'Hemşirelik, Ebelik… bölümlerinden mezun olmak.', 'Fizik, Kimya vs. programlarından mezun olmak.'):
            self.assertTrue(any('kısaltılmış' in s for s in yc.uyarilar(self._kadro(kosullar=[m]))), m)
        # VB.NET ve deneyim maddesindeki "vb." bölüm listesi değildir
        for m in ('Bilgisayar mühendisliğinden mezun olmak; VB.NET programlama bilmek.', 'Strateji vb. alanlarda 5 yıl çalışmış olmak.'):
            self.assertFalse(any('kısaltılmış' in s for s in yc.uyarilar(self._kadro(kosullar=['Hemşirelik bölümünden mezun olmak.', m]))), m)

    def test_mezuniyet_maddesi_taninir(self):
        for m in ('Hemşirelik lisans diplomasına sahip olmak.', 'Lisans eğitimini tamamlamış olmak.', 'Tıp doktoru olmak.'):
            self.assertEqual(yc.uyarilar(self._kadro(kosullar=[m])), [], m)
        self.assertTrue(any('mezuniyet maddesi yok' in s for s in yc.uyarilar(self._kadro(kosullar=['B sınıfı sürücü belgesi.']))))

    def test_puan_turu_listesi_gecerli(self):
        for t in ('P1,P2,P3', 'P14-P15-P16-P17-P18', 'P12-P40 (bölüme göre)', 'KPSSP3', None):
            self.assertEqual(yc.uyarilar(self._kadro(puan_turu=t)), [], t)
        self.assertEqual(yz_isle._puan_turleri('P14P15P16'), ['P14', 'P15', 'P16'])
        self.assertEqual(yz_isle._puan_turleri('KPSSP3'), ['P3'])

    def test_okunamayan_belgede_uyari_yok(self):
        self.assertEqual(yc.uyarilar({'kadrolar': [{'unvan': 'X'}], 'okunabilirlik': 'kotu'}), [])

    def test_mevcut_claude_okumalari_reddedilmez(self):
        """Yayındaki Claude okumaları yeni kurallarla da kaydedilebilir olmalı (denetim: %32'si reddediliyordu)."""
        veri = json.loads((Path(__file__).resolve().parent.parent / 'denetim' / 'yz.json').read_text(encoding='utf-8'))
        red = [k for k, v in veri.items() if isinstance(v, dict) and v.get('model') == 'claude' and isinstance(v.get('yz'), dict) and yc.dogrula(v['yz'])]
        self.assertEqual(red, [])


class Bekleme(unittest.TestCase):
    def test_claude_okuyana_kadar_4_saat_beklenir(self):
        self.assertEqual(yz_isle.yayina_hazir(ILAN, {}, SIMDI.replace(hour=16))[0], False)   # 3,5 saat
        self.assertEqual(yz_isle.yayina_hazir(ILAN, {}, SIMDI.replace(hour=16, minute=35))[0], True)


if __name__ == '__main__':
    unittest.main()
