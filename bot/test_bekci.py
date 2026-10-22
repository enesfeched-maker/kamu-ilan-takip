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
        kisa = dict(calisma(None, 10), status='waiting')
        self.assertNotIn('tarama_takildi', bekci.sorunlar(SIMDI, [kisa, calisma('success', 40)], SAGLIKLI, SITE_TAZE, None, 0))

    def test_tarama_durmus(self):
        s = bekci.sorunlar(SIMDI, [calisma('success', 150)], SAGLIKLI, SITE_TAZE, None, 0)
        self.assertIn('tarama_durdu', s)

    def test_site_ve_kuyruk_ve_sosyal(self):
        s = bekci.sorunlar(SIMDI, SAGLIKLI, [calisma('failure', 30)], SIMDI - timedelta(hours=4), None, 9)
        self.assertEqual(sorted(s), ['kuyruk', 'site_eski', 'sosyal'])
        self.assertIn('site', bekci.sorunlar(SIMDI, SAGLIKLI, SAGLIKLI, None, 'URLError', 0))


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
