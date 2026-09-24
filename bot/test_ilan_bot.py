import unittest
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

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
        self.assertLess(len(ilan_bot.duz_metin(mesaj)), 4096)
        self.assertIn('İlan metninden', mesaj)
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


if __name__ == '__main__':
    unittest.main()
