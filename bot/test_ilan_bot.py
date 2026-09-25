import unittest
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta

import ilan_bot
from ilan_bot import rss_coz, tarih_bul, mesaj_olustur


class RssTests(unittest.TestCase):
    def test_yayin_tarihi_son_tarih_degil(self):
        self.assertIsNone(tarih_bul("PERSONEL ALIMI (09.09.2026)"))

    def test_acik_son_tarih(self):
        self.assertEqual(tarih_bul("Yayın 01.09.2026 Son başvuru: 30.09.2026"), "2026-09-30")
        self.assertEqual(tarih_bul("Son başvuru: 30 Eylül 2026"), "2026-09-30")

    def test_kategori_kurum_degil(self):
        xml = '''<rss><channel><item><title>ÖRNEK ÜNİVERSİTESİ - PERSONEL ALIMI (09.09.2026)</title>
        <link>https://kariyerkapisi.gov.tr/IlanDetay?i=test</link>
        <category>Sözleşmeli Personel İlanları</category>
        <pubDate>Wed, 09 Sep 2026 09:00:00 +0300</pubDate></item></channel></rss>'''
        ilan = rss_coz(xml)[0]
        self.assertEqual(ilan['kurum'], 'ÖRNEK ÜNİVERSİTESİ')
        self.assertIsNone(ilan['son_tarih'])

    def test_mesaj_kurum_tekrari_ve_html(self):
        mesaj = mesaj_olustur({'baslik': 'A & B - <Uzman> alımı', 'kurum': 'A & B',
                              'link': 'https://example.com/ilan', 'son_tarih': None}, '')
        self.assertEqual(mesaj.count('A &amp; B'), 1)
        self.assertIn('&lt;Uzman&gt; alımı', mesaj)
        self.assertIn('Resmi ilan üzerinden kontrol edin.', mesaj)

    def test_turkce_baslik_ve_uzun_mesaj(self):
        self.assertEqual(ilan_bot.okunakli_baslik('NİĞDE ÜNİVERSİTESİ - KPSS 4/B PERSONEL ALIMI'),
                         'Niğde Üniversitesi - KPSS 4/B Personel Alımı')
        ilan = {'baslik': 'İLAN ' * 1000, 'kurum': 'KURUM ' * 500,
                'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=test',
                'yer': 'İSTANBUL ' * 100, 'kadro': 'Uzman ' * 200,
                'ozet': 'Koşullar & belgeler ' * 1000, 'son_tarih': '2026-09-24'}
        mesaj = mesaj_olustur(ilan, '')
        self.assertLess(len(ilan_bot.duz_metin(mesaj).encode('utf-16-le')) // 2, 1024)
        self.assertNotIn('İlan metninden', mesaj)
        self.assertNotIn('KAMU İLAN TAKİP', mesaj)
        self.assertNotIn('<script', mesaj)


class TelegramDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cfg = root / 'config.json'
        self.cfg.write_text(json.dumps({'rss_urls': ['https://example.com/rss'],
                                       'max_mesaj_per_calisma': 15}), encoding='utf-8')
        self.data = root / 'ilanlar.json'
        self.items = [{'id': str(n), 'baslik': f'KURUM - İlan {n}', 'kurum': 'KURUM',
                       'link': f'https://example.com/{n}', 'son_tarih': None,
                       'ilk_gorulme': ilan_bot.simdi().isoformat()} for n in range(25)]
        self.data.write_text(json.dumps({'guncelleme': ilan_bot.simdi().isoformat(),
                                        'ilanlar': self.items}), encoding='utf-8')

    def run_bot(self, *args, success=True):
        with patch.object(ilan_bot, 'CONFIG_YOLU', self.cfg), \
             patch.object(ilan_bot, 'indir', return_value=b''), \
             patch.object(ilan_bot, 'rss_coz', return_value=[dict(i) for i in self.items]), \
             patch.object(ilan_bot, 'telegram_gonder', return_value=success) as send, \
             patch.object(ilan_bot, 'gorsel_olustur', return_value=b'photo'), \
             patch.object(ilan_bot.time, 'sleep'), \
             patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test', 'TELEGRAM_CHAT_ID': '@test', 'RSS_URLS': ''}), \
             patch('sys.argv', ['bot', '--cikti', str(self.data), *args]), \
             contextlib.redirect_stdout(io.StringIO()):
            ilan_bot.main()
            return send.call_count

    def test_limit_sonraki_taramada_devam_eder_tekrar_gondermez(self):
        self.assertEqual(self.run_bot('--duyur-mevcut'), 15)
        self.assertEqual(len(json.loads(self.data.read_text())['telegram_bekleyen']), 10)
        self.assertEqual(self.run_bot(), 10)
        self.assertEqual(self.run_bot('--duyur-mevcut'), 0)
        self.assertEqual(len(json.loads(self.data.read_text())['telegram_gonderilen']), 25)

    def test_basarisiz_gonderim_saklanir(self):
        with self.assertRaises(SystemExit):
            self.run_bot('--duyur-mevcut', success=False)
        state = json.loads(self.data.read_text())
        self.assertEqual(len(state['telegram_bekleyen']), 25)
        self.assertEqual(state['telegram_gonderilen'], [])
        self.assertEqual(self.run_bot(), 15)

    def test_onizleme_veriyi_degistirmez(self):
        once = self.data.read_bytes()
        self.assertEqual(self.run_bot('--duyur-mevcut', '--dry-run'), 0)
        self.assertEqual(self.data.read_bytes(), once)

    def test_resmi_detay_hatasinda_eksik_mesaj_gondermez(self):
        cfg = json.loads(self.cfg.read_text())
        cfg['resmi_detaylari_oku'] = True
        self.cfg.write_text(json.dumps(cfg))
        with patch.object(ilan_bot, 'detay_oku', side_effect=ValueError('geçici hata')), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.run_bot('--duyur-mevcut')
        state = json.loads(self.data.read_text())
        self.assertEqual(state['telegram_gonderilen'], [])
        self.assertEqual(len(state['telegram_bekleyen']), 25)

    def test_rss_bos_tarih_resmi_tarihi_silmez(self):
        cfg = json.loads(self.cfg.read_text())
        cfg['resmi_detaylari_oku'] = True
        self.cfg.write_text(json.dumps(cfg))
        state = json.loads(self.data.read_text())
        for i in state['ilanlar']:
            i.update(son_tarih='2099-10-09', detay_guncelleme=ilan_bot.simdi().isoformat())
        self.data.write_text(json.dumps(state))
        with patch.object(ilan_bot, 'detay_oku') as fetch:
            self.assertEqual(self.run_bot('--duyur-mevcut'), 15)
            fetch.assert_not_called()
        self.assertEqual(json.loads(self.data.read_text())['ilanlar'][0]['son_tarih'], '2099-10-09')

    def prepare_reminders(self, days=3):
        deadline = (ilan_bot.simdi().date() + timedelta(days=days)).isoformat()
        for i in self.items:
            i['son_tarih'] = deadline
        self.data.write_text(json.dumps({'guncelleme': ilan_bot.simdi().isoformat(),
            'ilanlar': self.items, 'telegram_gonderilen': [i['id'] for i in self.items]}))

    def test_hatirlatma_sinir_ve_tekrar(self):
        self.prepare_reminders()
        self.assertEqual(self.run_bot(), 15)
        self.assertEqual(self.run_bot(), 10)
        self.assertEqual(self.run_bot(), 0)
        state = json.loads(self.data.read_text())
        self.assertEqual(len(state['telegram_hatirlatilan']), 25)

    def test_hatirlatma_basarisizsa_tekrar_denenir(self):
        self.prepare_reminders()
        with self.assertRaises(SystemExit):
            self.run_bot(success=False)
        self.assertEqual(json.loads(self.data.read_text())['telegram_hatirlatilan'], [])
        self.assertEqual(self.run_bot(), 15)

    def test_uzak_ve_suresi_dolan_hatirlatilmaz(self):
        for days in (4, -1):
            self.prepare_reminders(days)
            self.assertEqual(self.run_bot(), 0)

    def test_yeni_ilana_hemen_ikinci_hatirlatma_gitmez(self):
        self.prepare_reminders(2)
        state = json.loads(self.data.read_text())
        state['telegram_gonderilen'] = []
        self.data.write_text(json.dumps(state))
        self.assertEqual(self.run_bot('--duyur-mevcut'), 15)
        self.assertEqual(self.run_bot(), 10)
        self.assertEqual(self.run_bot(), 0)

    def test_son_saat_ve_uzatilan_tarih(self):
        now = ilan_bot.simdi()
        i = {'id': 'one', 'son_tarih': now.date().isoformat(),
             'son_zaman': (now-timedelta(minutes=1)).isoformat()}
        self.assertIsNone(ilan_bot.hatirlatma_anahtari(i))
        i['son_zaman'] = (now+timedelta(minutes=1)).isoformat()
        first = ilan_bot.hatirlatma_anahtari(i)
        self.assertIsNotNone(first)
        i['son_zaman'] = (now+timedelta(hours=1)).isoformat()
        self.assertNotEqual(first, ilan_bot.hatirlatma_anahtari(i))

    def test_fotograf_ve_dugmeler_tek_istekte(self):
        response = io.BytesIO(b'{"ok": true}')
        with patch.object(ilan_bot.urllib.request, 'urlopen', return_value=response) as api:
            self.assertTrue(ilan_bot.telegram_gonder('test', '@test', '<b>İlan</b>',
                             'https://example.com/apply', 'https://example.com', foto=b'PNGDATA'))
        request = api.call_args.args[0]
        self.assertTrue(request.full_url.endswith('/sendPhoto'))
        self.assertIn(b'name="caption"', request.data)
        self.assertIn(b'name="photo"', request.data)
        self.assertIn(b'PNGDATA', request.data)
        self.assertIn(b'inline_keyboard', request.data)


if __name__ == '__main__':
    unittest.main()
