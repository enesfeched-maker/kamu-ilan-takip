"""Denetim H9 (kurum içi ilan: sitede ve kanalda yok) ve tekrar paylaşım (kopya ilan ikinci kez gönderilmez)."""
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import ilan_bot
import liste_verisi as lv
import site_uret
from siniflandir import akademik_ilan, kurum_ici
from site_uret import TR
from test_kanal_kurallari import SIMDI as KSIMDI

VERI = json.loads((Path(__file__).parent / 'test_veri' / 'kopya_ilanlar.json').read_text(encoding='utf-8'))
SIMDI = datetime(2026, 10, 5, 12, 0, tzinfo=TR)
ELM_SBB, ELM_ISKUR = 'sbb-97e476fbb140b9951ef70fe8', 'iskur-3f593d9e3c71078c698a111a'


def sec(*ids):
    return {i['id']: json.loads(json.dumps(i)) for i in VERI if i['id'] in ids}


def kk(n, baslik, kurum, **ek):
    u = '%08d-3333-4333-8333-333333333333' % n
    return {'id': 'https://kariyerkapisi.gov.tr/IlanDetay?i=' + u, 'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=' + u,
            'baslik': baslik, 'kurum': kurum, 'son_tarih': '2026-10-14', 'ilk_gorulme': '2026-10-04T10:00:00+03:00', **ek}


HAZINE = kk(1, 'HAZİNE VE MALİYE BAKANLIĞI - MUHASEBE UZMANLIĞI YETERLİK SINAVI DUYURUSU', 'HAZİNE VE MALİYE BAKANLIĞI',
            ilan_turu='Yeterlik Sınavı İlanları', kadro='120 MUHASEBE UZMANI')
CSB_GY = kk(2, 'ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞI - GÖREVDE YÜKSELME SINAVI İLANI (Şube Müdürü (Teknik), Şube Müdürü (İdari) ve Memur Kadroları)',
            'ÇEVRE, ŞEHİRCİLİK VE İKLİM DEĞİŞİKLİĞİ BAKANLIĞI', ilan_turu='Görevde Yükselme ve Unvan Değişikliği İlanları',
            kadro='Toplam 130 kişi — 115 ŞUBE MÜDÜRÜ • 15 MEMUR')
KIK1 = kk(3, 'KAMU İHALE KURUMU - Yurtdışı Staj (2026 Yılı)', 'KAMU İHALE KURUMU', ilan_turu='Yurt Dışı Eğitim İlanları', kadro='2 KAMU İHALE UZMANI',
          ozet='Cumhurbaşkanı Kararı doğrultusunda Kurumumuz personeline yönelik 2026 yılı için; "Hukuk, Kamu Yönetimi" alanlarında')
KIK2 = kk(4, 'KAMU İHALE KURUMU - KAMU İHALE KURUMU PERSONELİ İÇİN YURT DIŞI YÜKSEK LİSANS EĞİTİMİ (2026 YILI)', 'KAMU İHALE KURUMU',
          kadro='1 KAMU İHALE UZMANI')
KIK3 = kk(5, 'KAMU İHALE KURUMU - Uzman alımı', 'KAMU İHALE KURUMU', kadro='1 UZMAN',
          ozet='Kurumumuz personeline yönelik 2026 yılı için yetiştirme programı')
NORMAL = kk(6, 'RİZE BELEDİYESİ - Zabıta Memuru Alımı', 'RİZE BELEDİYESİ', kadro='2 ZABITA MEMURU')


class KurumIciTanimaTests(unittest.TestCase):
    def test_tanima(self):
        for i in (HAZINE, CSB_GY, KIK1, KIK2, KIK3):
            self.assertTrue(kurum_ici(i), i['baslik'])
            self.assertTrue(akademik_ilan(i), 'kurum içi, akademik gibi her yerden elenir')
        self.assertFalse(kurum_ici(NORMAL))
        self.assertFalse(akademik_ilan(NORMAL))

    def test_liste_json_icermez_ve_sayilmaz(self):
        with tempfile.TemporaryDirectory() as kok:
            v = lv.liste_uret([HAZINE, CSB_GY, KIK1, NORMAL], {}, Path(kok), SIMDI, None, {})
        self.assertEqual([k['key'] for k in v['ilanlar']], [NORMAL['id'].split('?i=')[1]])
        self.assertEqual((v['sayilar']['acik'], v['sayilar']['kadro']), (1, 2))

    def test_telegram_siralamasi_ve_ozetler_haric(self):
        bekleyen = {i['id'] for i in (HAZINE, CSB_GY, KIK1, KIK2, NORMAL)}
        mevcut = {i['id']: i for i in (HAZINE, CSB_GY, KIK1, KIK2, NORMAL)}
        with patch.object(ilan_bot, 'simdi', return_value=SIMDI):
            sira = ilan_bot.telegram_sirasi(mevcut, list(mevcut.values()), [], set(), bekleyen, False, False, {})
            self.assertEqual([i['id'] for i in sira], [NORMAL['id']])
            self.assertEqual(bekleyen, {NORMAL['id']}, 'kurum içi sıradan düşer')
            tum = {i['id'] for i in mevcut.values()}
            yakin = dict(NORMAL, son_tarih='2026-10-07')
            self.assertEqual([i['id'] for i in ilan_bot.toplu_secim([HAZINE, CSB_GY, KIK1, yakin], tum, {})], [NORMAL['id']])
            self.assertEqual(ilan_bot.sabah_acik_sayisi(list(mevcut.values()), SIMDI), 1)
            self.assertFalse(ilan_bot.telegram_icin_uygun(HAZINE, [], []))


class PaylasilmisBaglantiTests(unittest.TestCase):
    def test_paylasilmis_kurum_ici_icin_sade_noindex_sayfa(self):
        a = dict(HAZINE, id='sbb-' + 'a' * 24, link='https://kamuilan.sbb.gov.tr/', kaynak_turu='sbb')
        b = dict(CSB_GY, id='sbb-' + 'b' * 24, link='https://kamuilan.sbb.gov.tr/', kaynak_turu='sbb')   # paylaşılmamış
        n = dict(NORMAL, id='sbb-' + 'c' * 24, link='https://kamuilan.sbb.gov.tr/', kaynak_turu='sbb')
        with tempfile.TemporaryDirectory() as kok:
            docs = Path(kok) / 'docs'
            docs.mkdir()
            (docs / 'ilanlar.json').write_text(json.dumps({'ilanlar': [a, b, n], 'telegram_gonderilen': [a['id']]}), encoding='utf-8')
            with patch.object(site_uret, 'ROOT', Path(kok)), contextlib.redirect_stdout(io.StringIO()):
                site_uret.main()
            sayfa = (docs / 'ilan' / a['id'] / 'index.html').read_text(encoding='utf-8')
            self.assertIn('noindex', sayfa)
            self.assertIn('Bu ilan yalnız kurum personeline yöneliktir.', sayfa)
            self.assertFalse((docs / 'ilan' / b['id']).exists())
            self.assertTrue((docs / 'ilan' / n['id'] / 'index.html').exists())
            harita = (docs / 'sitemap.xml').read_text(encoding='utf-8')
            self.assertNotIn(a['id'], harita)
            self.assertNotIn(a['id'], (docs / 'liste.json').read_text(encoding='utf-8'))
            self.assertNotIn(a['id'], (docs / 'bot-ilanlar.json').read_text(encoding='utf-8'))


class TekrarPaylasimTests(unittest.TestCase):
    def calistir(self, mevcut, gonderilen, bekleyen):
        with patch.object(ilan_bot, 'simdi', return_value=SIMDI), contextlib.redirect_stdout(io.StringIO()):
            return ilan_bot.telegram_sirasi(mevcut, list(mevcut.values()), [], gonderilen, bekleyen, False, False, {})

    def test_kopya_zaten_paylasildiysa_atlanir(self):
        # Elmakaya: İŞKUR kaydı kanalda, SBB kaydı (aynı ilan) yeni geldi
        mevcut = sec(ELM_SBB, ELM_ISKUR)
        gonderilen, bekleyen = {ELM_ISKUR}, {ELM_SBB}
        self.assertEqual(self.calistir(mevcut, gonderilen, bekleyen), [])
        self.assertIn(ELM_SBB, gonderilen, 'işlenmiş sayılır, tekrar denenmez')
        self.assertEqual(bekleyen, set())

    def test_ters_yon_de_atlanir(self):
        mevcut = sec(ELM_SBB, ELM_ISKUR)
        gonderilen, bekleyen = {ELM_SBB}, {ELM_ISKUR}
        self.assertEqual(self.calistir(mevcut, gonderilen, bekleyen), [])

    def test_ikisi_de_yeniyse_yalniz_biri_gider(self):
        mevcut = sec(ELM_SBB, ELM_ISKUR)
        gonderilen, bekleyen = set(), {ELM_SBB, ELM_ISKUR}
        sira = self.calistir(mevcut, gonderilen, bekleyen)
        self.assertEqual(len(sira), 1)
        # Kardeş kayıt işlenmiş sayılmaz, sırada kalır; seçilen gerçekten gönderilince sonraki çalışmada düşer.
        self.assertEqual(gonderilen, set())
        self.assertEqual(bekleyen, {ELM_SBB, ELM_ISKUR})
        secilen = sira[0]['id']
        gonderilen.add(secilen); bekleyen.discard(secilen)
        self.assertEqual(self.calistir(mevcut, gonderilen, bekleyen), [])
        self.assertEqual(gonderilen, {ELM_SBB, ELM_ISKUR})
        self.assertEqual(bekleyen, set())

    def test_ikisi_de_yeni_gonderilemezse_ikisi_de_kaybolmaz(self):
        # 9 Ekim 2026 hatası: sessiz dönem/mesaj sınırı yüzünden hiçbiri gönderilmezken kopyalar birbirini
        # 'paylaşıldı' işaretleyip ilan kanala hiç gitmiyordu.
        mevcut = sec(ELM_SBB, ELM_ISKUR)
        gonderilen, bekleyen = set(), {ELM_SBB, ELM_ISKUR}
        for _ in range(3):
            self.assertEqual(len(self.calistir(mevcut, gonderilen, bekleyen)), 1)
        self.assertEqual(gonderilen, set())
        self.assertEqual(bekleyen, {ELM_SBB, ELM_ISKUR})

    def test_farkli_ilan_elenmez(self):
        mevcut = sec(ELM_SBB, ELM_ISKUR)
        diger = dict(NORMAL, id='sbb-' + 'd' * 24, link='https://kamuilan.sbb.gov.tr/', kaynak_turu='sbb')
        mevcut[diger['id']] = diger
        gonderilen, bekleyen = {ELM_ISKUR}, {diger['id']}
        sira = self.calistir(mevcut, gonderilen, bekleyen)
        self.assertEqual([i['id'] for i in sira], [diger['id']])


if __name__ == '__main__':
    unittest.main()
