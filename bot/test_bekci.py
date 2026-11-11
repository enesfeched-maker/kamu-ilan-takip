import unittest
from datetime import datetime, timedelta, timezone

import bekci

SIMDI = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


def calisma(conclusion, dakika_once, status='completed'):
    z = (SIMDI - timedelta(minutes=dakika_once)).isoformat()
    return {'status': status, 'conclusion': conclusion, 'createdAt': z, 'updatedAt': z}


SAGLIKLI = [calisma('success', 10), calisma('success', 50)]
SITE_TAZE = SIMDI - timedelta(minutes=20)


class Kontrol(unittest.TestCase):
    def test_saglikli(self):
        self.assertEqual(bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, SITE_TAZE, None, 0), {})

    def test_tarama_arka_arkaya_basarisiz(self):
        s = bekci.sorunlar(SIMDI, [calisma('failure', 5), calisma('failure', 35), calisma('success', 65)], SAGLIKLI, SITE_TAZE, None, 0)
        self.assertIn('tarama_hata', s)
        self.assertNotIn('tarama_durdu', s)   # 65 dk önce başarılı tarama var

    def test_tek_basarisizlik_alarm_vermez_iptal_sayilmaz(self):
        self.assertEqual(bekci.sorunlar(SIMDI, [calisma('failure', 5), calisma('cancelled', 20), calisma('success', 40)],
                                        SAGLIKLI, SITE_TAZE, None, 0), {})

    def test_takili_tarama(self):
        takili = dict(calisma(None, 47), status='waiting')
        s = bekci.sorunlar(SIMDI, [takili, calisma('success', 60)], SAGLIKLI, SITE_TAZE, None, 0)
        self.assertIn('tarama_takildi', s)
        sonra_basarili = [calisma('success', 5), takili]   # takılı kayıttan sonra başarılı tarama: eski kayıt, uyarı yok
        self.assertNotIn('tarama_takildi', bekci.sorunlar(SIMDI, sonra_basarili, SAGLIKLI, SITE_TAZE, None, 0))
        kisa = dict(calisma(None, 10), status='waiting')
        self.assertNotIn('tarama_takildi', bekci.sorunlar(SIMDI, [kisa, calisma('success', 40)], SAGLIKLI, SITE_TAZE, None, 0))

    def test_tarama_durmus(self):
        s = bekci.sorunlar(SIMDI, [calisma('success', 150)], SAGLIKLI, SITE_TAZE, None, 0)
        self.assertIn('tarama_durdu', s)

    def test_site_ve_kuyruk_ve_sosyal(self):
        s = bekci.sorunlar(SIMDI, SAGLIKLI, [calisma('failure', 30)], SIMDI - timedelta(hours=4), None, 9)
        self.assertEqual(sorted(s), ['kuyruk', 'site_eski', 'sosyal'])
        self.assertIn('site', bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, None, 'URLError', 0))


class YerelKaynak(unittest.TestCase):
    def durum(self, saat_once):
        return {'kontrol': (SIMDI - timedelta(hours=saat_once)).isoformat(), 'hata_sayisi': 0}

    def test_yerel_tarayici_yarim_gunden_uzun_susarsa_uyarir(self):
        s = bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, SITE_TAZE, None, 0, None, {'sbb': self.durum(13), 'csb': self.durum(2), 'iskur': self.durum(40)})
        self.assertEqual(list(s), ['yerel_kaynak'])
        self.assertIn('SBB', s['yerel_kaynak'])
        self.assertNotIn('ÇŞB', s['yerel_kaynak'])

    def test_gece_kapali_bilgisayar_ve_kullanilmayan_kaynak_uyarmaz(self):
        self.assertEqual(bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, SITE_TAZE, None, 0, None, {'sbb': self.durum(9), 'csb': self.durum(11)}), {})
        self.assertEqual(bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, SITE_TAZE, None, 0, None, {'iskur': self.durum(99)}), {})
        self.assertEqual(bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, SITE_TAZE, None, 0, None, None), {})

    def test_hic_basarili_okuma_yoksa_ve_saat_dilimsiz_tarihte_cokmez(self):
        self.assertEqual(bekci.yerel_gecikenler(SIMDI, {'sbb': {'son_deneme': SIMDI.isoformat(), 'hata_sayisi': 1}}), ['SBB'])
        self.assertEqual(bekci.yerel_gecikenler(SIMDI, {'csb': {'kontrol': '2026-01-01T00:00:00'}}), ['ÇŞB'])


class Ana(unittest.TestCase):
    def calistir(self, site):
        import contextlib, io, os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        giden = []
        with tempfile.TemporaryDirectory() as klasor, \
                patch.object(bekci, 'DURUM', Path(klasor) / 'durum.json'), \
                patch.object(bekci, 'calismalar', return_value=[]), \
                patch.object(bekci, 'site_oku', return_value=site), \
                patch.object(bekci, 'depo_oku', return_value=(0, {})), \
                patch.object(bekci, 'telegram', side_effect=lambda t, s, m: giden.append(m) or True), \
                patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 't', 'TELEGRAM_YONETICI_ID': '1'}), \
                patch('sys.argv', ['bekci.py']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bekci.ana(), 0)
        return giden

    def test_site_okunamadiginda_cokmez_ve_uyari_gonderir(self):
        giden = self.calistir((None, 'URLError'))
        self.assertTrue(any('Site okunamadı' in g for g in giden), giden)

    def test_ozet_metni_site_yokken_de_kurulur(self):
        tr = SIMDI.astimezone(bekci.TR)
        self.assertIn('okunamadı', bekci.ozet_metni(tr, None, None))
        self.assertIn('Telegram sırası: 2', bekci.ozet_metni(tr, SITE_TAZE, 2))


class Mesaj(unittest.TestCase):
    def test_yeni_sorun_hemen_sonra_tekrar_yok_6_saat_sonra_hatirlatma_duzelince_haber(self):
        s = {'kuyruk': 'Telegram sırasında 9 ilan bekliyor.'}
        giden, durum = bekci.mesajlar({}, s, SIMDI, False, 'ozet')
        self.assertEqual(len(giden), 1)
        giden, durum = bekci.mesajlar(durum, s, SIMDI + timedelta(minutes=30), False, 'ozet')
        self.assertEqual(giden, [])
        giden, durum = bekci.mesajlar(durum, s, SIMDI + timedelta(hours=6, minutes=1), False, 'ozet')
        self.assertEqual(len(giden), 1)
        giden, durum = bekci.mesajlar(durum, {}, SIMDI + timedelta(hours=7), False, 'ozet')
        self.assertTrue(giden[0].startswith('✅ Düzeldi'))
        self.assertEqual(durum, {})

    def test_ozet_yalniz_saglikliyken_ve_ozet_zamaninda(self):
        self.assertEqual(bekci.mesajlar({}, {}, SIMDI, True, 'ozet')[0], ['ozet'])
        self.assertEqual(bekci.mesajlar({}, {}, SIMDI, False, 'ozet')[0], [])
        self.assertEqual(bekci.mesajlar({}, {'x': 'sorun'}, SIMDI, True, 'ozet')[0], ['🔴 sorun'])


if __name__ == '__main__':
    unittest.main()
