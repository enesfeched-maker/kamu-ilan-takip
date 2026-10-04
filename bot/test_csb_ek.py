import io
import ssl
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

import csb_ek
import csb_kaynak as csb
import ek_kaynaklar as ek
from liste_verisi import puan_turleri
from siniflandir import ogrenim_seviyeleri

VERI = Path(__file__).parent / 'test_veri'
SITE = 'https://yerelyonetimler.csb.gov.tr/'
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def hucre(*paragraflar):
    govde = ''.join(f'<w:p><w:r><w:t xml:space="preserve">{escape(p)}</w:t></w:r></w:p>' for p in paragraflar) or '<w:p/>'
    return f'<w:tc>{govde}</w:tc>'


def docx(*tablolar, onsoz='ÖRNEK BELEDİYESİ İLANI'):
    """Yalnız örnek metinli küçük docx: tablolar -> satırlar -> hücreler (hücre = paragraf listesi)."""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body><w:p><w:r><w:t>{escape(onsoz)}</w:t></w:r></w:p>'
    for tablo in tablolar:
        xml += '<w:tbl>' + ''.join('<w:tr>' + ''.join(hucre(*h) for h in satir) + '</w:tr>' for satir in tablo) + '</w:tbl>'
    xml += '</w:body></w:document>'
    kayit = io.BytesIO()
    with zipfile.ZipFile(kayit, 'w') as z:
        z.writestr('word/document.xml', xml)
    return kayit.getvalue()


BASLIK = [['Sıra N o'], ['Kadro U nvanı'], ['Hizmet Sı nıfı'], ['Kadro Derecesi'], ['Kadro Adedi'], ['Niteliği'],
          ['Cinsiyeti'], ['KPSS  Puan  Türü'], ['KPSS', 'Taban Puanı']]


def satir(sira, unvan, sinif, derece, adet, nitelik, cins, pt, taban):
    return [[str(sira)], [unvan] if isinstance(unvan, str) else unvan, [sinif], [derece], [adet], nitelik, [cins], [pt], taban]


class DocxTablosuTesti(unittest.TestCase):
    def test_gercek_ilan_tablosu(self):
        a = csb_ek.belge_alanlari('x.docx', (VERI / 'csb_alim.docx').read_bytes())
        self.assertEqual(a['kadro'], '8 Zabıta Memuru')
        self.assertEqual(len(a['sartlar']), 1)
        s = a['sartlar'][0]
        self.assertEqual(s['kadro'], 'Zabıta Memuru · 8 kadro')
        self.assertIn('KPSS P94 puan türünden en az 65 puan.', s['metin'])
        self.assertIn('Hizmet sınıfı GİH, 11. derece.', s['metin'])
        self.assertIn('Ortaöğretim mezunu', s['metin'])

    def test_siniflandirici_ve_liste_alanlari_turetilir(self):
        a = csb_ek.belge_alanlari('x.docx', (VERI / 'csb_alim.docx').read_bytes())
        kayit = {'baslik': 'ŞİLE BELEDİYE BAŞKANLIĞI - ZABITA MEMURU ALIMI', **a}
        self.assertEqual(ogrenim_seviyeleri(kayit), ['ortaogretim'])
        self.assertEqual(puan_turleri(kayit), ['P94'])

    def test_bozuk_bosluklar_ve_cok_satir(self):
        t = [BASLIK,
             satir(1, ['Zabıta', 'Memuru'], 'GİH', '9', '1 8', ['Herhangi bir lisans programından mezun o lmak.', '- En az (B) sınıfı sürücü belgesine sahip olmak.'],
                   'Kadın/ Erkek', 'P 3', ['En az 7 5 puan']),
             satir(2, 'Tekniker', 'T.H.', '10', '4', ['Harita ve kadastro önlisans', 'programlarının birinden mezun olmak.'], 'Erkek', 'KPSSP93', ['55']),
             satir(3, 'Memur', 'GİH', '11', '2', ['Herhangi bir ortaöğretim kurumundan (lise veya dengi okul) mezun olmak.'], 'Erkek/Kadın', 'P94', ['En az', '60', 'puan'])]
        a = csb_ek.belge_alanlari('x.docx', docx(t))
        self.assertEqual(a['kadro'], 'Toplam 24 kişi — 18 Zabıta Memuru • 4 Tekniker • 2 Memur')
        s = a['sartlar']
        self.assertIn('KPSS P3 puan türünden en az 75 puan.', s[0]['metin'])
        self.assertIn('Öğrenim: Lisans mezunu.', s[0]['metin'])
        self.assertIn('mezun olmak.', s[0]['metin'])            # 'o lmak' onarıldı
        self.assertNotIn('Cinsiyet', s[0]['metin'])               # iki cinsiyet de olabilir: kısıt yok
        self.assertIn('KPSS P93 puan türünden en az 55 puan. Hizmet sınıfı TH, 10. derece. Öğrenim: Önlisans mezunu.', s[1]['metin'])
        self.assertIn('Cinsiyet: Erkek.', s[1]['metin'])
        self.assertIn('KPSS P94 puan türünden en az 60 puan.', s[2]['metin'])
        kayit = {'baslik': 'X BELEDİYESİ', **a}
        self.assertEqual(ogrenim_seviyeleri(kayit), ['lisans', 'onlisans', 'ortaogretim'])
        self.assertEqual(puan_turleri(kayit), ['P3', 'P93', 'P94'])

    def test_pozisyon_basligi_sozlesmeli(self):
        baslik = [['Sıra No'], ['Pozisyon Unvanı'], ['Hizmet Sınıfı'], ['Pozisyon Derecesi'], ['Pozisyon Adedi'], ['Niteliği'],
                  ['Cinsiyeti'], ['KPSS / Puan Türü'], ['KPSS / Taban Puanı']]
        a = csb_ek.belge_alanlari('x.docx', docx([baslik, satir(1, 'Mühendis', 'TH', '8', '1', ['Lisans düzeyinde eğitim veren fakültelerin inşaat mühendisliği bölümünden mezun olmak.'], 'Kadın/ Erkek', 'P3', ['En az 70 puan'])]))
        self.assertEqual(a['sartlar'][0]['kadro'], 'Mühendis · 1 pozisyon')

    def test_ogrenim_puan_turunden_tamamlanir(self):
        t = [BASLIK, satir(1, 'Memur', 'GİH', '9', '1', ['Başvuru şartlarını taşımak.'], 'Erkek/Kadın', 'P93', ['60'])]
        a = csb_ek.belge_alanlari('x.docx', docx(t))
        self.assertIn('Öğrenim: Önlisans mezunu.', a['sartlar'][0]['metin'])

    def test_tablo_yoksa_bos(self):
        self.assertEqual(csb_ek.belge_alanlari('x.docx', docx()), {})
        self.assertEqual(csb_ek.belge_alanlari('x.docx', docx([[['Başka'], ['Tablo']], [['a'], ['b']]])), {})

    def test_gecersiz_satir_tabloyu_reddeder_tahmin_yok(self):
        t = [BASLIK, satir(1, 'Memur', 'GİH', '9', 'bir', ['Lisans mezunu olmak.'], 'Erkek', 'P3', ['60'])]
        self.assertEqual(csb_ek.belge_alanlari('x.docx', docx(t)), {})

    def test_taban_yoksa_yalniz_puan_turu(self):
        t = [BASLIK, satir(1, 'Memur', 'GİH', '9', '1', ['Lisans düzeyinde eğitim veren fakültelerin birinden mezun olmak.'], 'Erkek', 'P3', ['—'])]
        s = csb_ek.belge_alanlari('x.docx', docx(t))['sartlar'][0]['metin']
        self.assertIn('KPSS P3 puan türü.', s)
        self.assertNotIn('en az', s.split('Hizmet')[0])

    def test_bozuk_veya_tehlikeli_docx_hata_verir(self):
        with self.assertRaises(Exception):
            csb_ek.belge_alanlari('x.docx', b'PK bozuk')
        kayit = io.BytesIO()
        with zipfile.ZipFile(kayit, 'w') as z:
            z.writestr('word/document.xml', '<!DOCTYPE x [<!ENTITY a "b">]><w:document ' + W + '/>')
        with self.assertRaises(ValueError):
            csb_ek.belge_alanlari('x.docx', kayit.getvalue())

    def test_duzelt(self):
        self.assertEqual(csb_ek.duzelt('i nşaat m ühendisliği olma k .'), 'inşaat mühendisliği olmak.')
        self.assertEqual(csb_ek.duzelt('E n az ( B ) sınıfı sürücü belgesi'), 'En az (B) sınıfı sürücü belgesi')
        self.assertEqual(csb_ek.duzelt('(B) sınıfı ve (C) sınıfı'), '(B) sınıfı ve (C) sınıfı')

    def test_il_baglantidan(self):
        self.assertEqual(csb_ek.il_slug(SITE + 'istanbul-ili-sile-belediye-baskanligina-x-duyuru-1'), 'İstanbul')
        self.assertEqual(csb_ek.il_slug(SITE + 'sanliurfa-ili-x-belediyesi-duyuru-2'), 'Şanlıurfa')
        self.assertIsNone(csb_ek.il_slug(SITE + 'rize-belediyesi-x-duyuru-3'))
        self.assertIsNone(csb_ek.il_slug(SITE + 'olmayanyer-ili-x-duyuru-4'))

    def test_pdf_iskur_cozumleyicisini_kullanir(self):
        sahte = {'kadro': '2 Memur', 'sartlar': [{'kadro': 'Memur · 2 kadro', 'metin': 'KPSS P3 puan türü.'}], 'ozet': 'x', 'basvuru_notu': 'y'}
        with patch('iskur_detay.ozetle', return_value=sahte) as o:
            a = csb_ek.belge_alanlari('x.PDF', b'%PDF-', 'Başlık')
        self.assertEqual(a, {'kadro': '2 Memur', 'sartlar': sahte['sartlar']})
        self.assertEqual(o.call_args[0][1], {'baslik': 'Başlık'})
        with patch('iskur_detay.ozetle', return_value={'ozet': 'x'}):
            self.assertEqual(csb_ek.belge_alanlari('x.pdf', b'%PDF-'), {})


class TlsTesti(unittest.TestCase):
    def test_sabit_ara_sertifika_yuklenir_ve_dogrulama_acik_kalir(self):
        csb._baglam.cache_clear()
        ctx = csb._baglam()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertTrue(any('SSL2BUY' in str(c.get('subject')) for c in ctx.get_ca_certs()))
        self.assertTrue(ctx.verify_flags & getattr(ssl, 'VERIFY_X509_PARTIAL_CHAIN', 0x80000))

    def test_sertifika_dosyasi_tek_pem(self):
        pem = csb.ARA_SERTIFIKA.read_text(encoding='ascii')
        self.assertEqual(pem.count('BEGIN CERTIFICATE'), 1)
        self.assertEqual(len(ssl.PEM_cert_to_DER_cert(pem)) > 500, True)

    def test_sertifika_yoksa_cokmez(self):
        csb._baglam.cache_clear()
        with patch.object(csb, 'ARA_SERTIFIKA', Path('yok.pem')):
            ctx = csb._baglam()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        csb._baglam.cache_clear()


class DuyuruOkumaTesti(unittest.TestCase):
    def satir(self):
        return {'numara': '477952', 'link': SITE + 'istanbul-ili-sile-belediye-baskanligina-x-duyuru-477952',
                'baslik': 'ŞİLE BELEDİYE BAŞKANLIĞI İLK DEFA ATANMAK ÜZERE ZABITA MEMURU ALIMI İLANI', 'yayim': '2026-09-29'}

    def ag(self, ek_veri=None, hata=False):
        def sahte(adres, sinir=0, referer=None):
            if adres.endswith('.docx'):
                if hata:
                    raise OSError('ag yok')
                return ek_veri if ek_veri is not None else (VERI / 'csb_alim.docx').read_bytes()
            return (VERI / 'csb_detay_alim.html').read_bytes()
        return sahte

    def oku(self, **kw):
        with patch.object(csb, 'indir', side_effect=self.ag(**kw)), patch.object(csb.time, 'sleep'):
            return csb.duyuru_oku(self.satir())

    def test_kayit_kadro_ve_sartlari_tasir(self):
        k = self.oku()
        self.assertEqual(k['kadro'], '8 Zabıta Memuru')
        self.assertTrue(k['sartlar'])
        self.assertNotIn('ek_okunamadi', k)
        self.assertEqual(k['son_tarih'], '2026-11-06')
        self.assertEqual(k['csb_detay_surumu'], csb.VERSIYON)

    def test_gercek_ag_hatasi_ek_okunamadi_kalir(self):
        k = self.oku(hata=True)
        self.assertEqual(k['ek_okunamadi'], 1)
        self.assertEqual(k['kadro'], '')
        self.assertNotIn('sartlar', k)

    def test_tablosuz_belge_hata_sayilmaz(self):
        k = self.oku(ek_veri=docx(onsoz='Yalnız metin'))
        self.assertNotIn('ek_okunamadi', k)
        self.assertEqual(k['kadro'], '')

    def test_tablo_ayiklama_hatasi_okumayi_bozmaz(self):
        with patch.object(csb_ek, 'belge_alanlari', side_effect=ValueError('x')):
            k = self.oku()
        self.assertNotIn('ek_okunamadi', k)
        self.assertEqual(k['son_tarih'], '2026-11-06')
        self.assertEqual(k['kadro'], '')

    def test_baslikta_il_yoksa_baglantidan(self):
        s = {**self.satir(), 'baslik': 'ŞİLE BELEDİYE BAŞKANLIĞINA İLK DEFA ATANMAK ÜZERE ZABITA MEMURU ALIMI İLANI'}
        detay = {'baslik': s['baslik'], 'aciklama': '', 'ekler': []}
        self.assertEqual(csb.kayit_olustur(s, detay, None)['yer'], 'İstanbul')

    def test_eski_surum_kayit_yeniden_okunur(self):
        eski = {'id': 'csb-477952', 'kaynak_turu': 'csb', 'csb_detay_surumu': 3, 'kadro': '',
                'detay_guncelleme': csb.now().isoformat(timespec='seconds'), 'yayim_tarihi': '2026-09-29'}
        cagri = []

        def sahte(adres, sinir=0, referer=None):
            cagri.append(adres)
            if adres.startswith(csb.LISTE):
                return (VERI / 'csb_liste.html').read_bytes()
            return self.ag()(adres, sinir, referer)
        with patch.object(csb, 'indir', side_effect=sahte), patch.object(csb.time, 'sleep'):
            kayitlar, hata = csb.csb_oku({eski['id']: eski})
        self.assertEqual(hata, 0)
        k = next(x for x in kayitlar if x['id'] == 'csb-477952')
        self.assertEqual(k['kadro'], '8 Zabıta Memuru')
        self.assertLessEqual(sum(a.endswith('.docx') for a in cagri), csb.AZAMI_DETAY * csb.AZAMI_BELGE)


class KanalGuvenligiTesti(unittest.TestCase):
    """Zenginleşen ÇŞB kaydı yeni kimlik/eşleşme/Telegram gönderimi üretmemeli."""

    def kayit(self, **ek_alan):
        return {'id': 'csb-477952', 'baslik': 'ŞİLE BELEDİYE BAŞKANLIĞI - ZABITA MEMURU ALIMI', 'kurum': 'ŞİLE BELEDİYE BAŞKANLIĞI',
                'yer': 'İstanbul', 'kadro': '', 'son_tarih': '2026-11-06', 'kaynak_turu': 'csb', 'link': SITE + 'x-duyuru-477952',
                'ozet': 'x', 'yayim_tarihi': '2026-09-29', **ek_alan}

    def test_ayni_kimlik_ve_takma_ad_korunur(self):
        eski = self.kayit()
        yeni = self.kayit(kadro='8 Zabıta Memuru', sartlar=[{'kadro': 'Zabıta Memuru · 8 kadro', 'metin': 'KPSS P94 puan türü.'}])
        birlesik = ek.merge_sources([yeni], {eski['id']: eski})
        self.assertEqual([i['id'] for i in birlesik], ['csb-477952'])
        self.assertEqual(birlesik[0]['kaynak_kimlikleri'], ['csb-477952'])

    def test_isci_sigortasi_belge_kadrosundan_etkilenmez(self):
        a = self.kayit(kadro='3 Sürekli İşçi')
        b = self.kayit()
        self.assertEqual(csb._isci(a), csb._isci(b))
        sbb = {'id': 'sbb-' + 'a' * 24, 'baslik': 'Şile Belediyesi Zabıta Memuru Alımı', 'kurum': 'ŞİLE BELEDİYESİ', 'yer': 'İstanbul',
               'son_tarih': '2026-11-06', 'kaynak_turu': 'sbb', 'link': 'https://kamuilan.sbb.gov.tr/x'}
        self.assertEqual(csb.eslesme_ciftleri([a, sbb]), csb.eslesme_ciftleri([b, sbb]))

    def test_telegram_filtresi_baslik_ve_kurumdan_calisir(self):
        import ilan_bot
        yeni = self.kayit(kadro='8 Zabıta Memuru', sartlar=[{'kadro': 'x', 'metin': 'KPSS P94'}])
        self.assertEqual(ilan_bot.telegram_icin_uygun(yeni, [], []), ilan_bot.telegram_icin_uygun(self.kayit(), [], []))
        gonderilen = {'csb-477952'}
        sira = ilan_bot.telegram_sirasi({yeni['id']: yeni}, [yeni], [], gonderilen, set(), False, False, {})
        self.assertEqual(sira, [])


if __name__ == '__main__':
    unittest.main()
