import unittest
from unittest import mock
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

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

    def run_bot(self, *args, success=True, zaman=None, donus=None):
        self.gonderimler = []
        self.stdout = io.StringIO()
        if zaman is None:  # varsayılan: gerçek an, ama 09:00 öncesine çekilir (sabah özeti duvar saatine bağlı olmasın)
            zaman = datetime.now(timezone(timedelta(hours=3)))
            zaman = zaman.replace(hour=8, minute=0) if zaman.hour >= 9 else zaman
        sahte = patch.object(ilan_bot, 'simdi', return_value=zaman)
        with sahte, patch.object(ilan_bot, 'CONFIG_YOLU', self.cfg), \
             patch.object(ilan_bot, 'indir', return_value=b''), \
             patch.object(ilan_bot, 'rss_coz', return_value=[dict(i) for i in self.items]), \
             patch.object(ilan_bot, 'telegram_gonder', side_effect=self._kaydet(donus or [], success)) as send, \
             patch.object(ilan_bot, 'gorsel_olustur', return_value=b'photo'), \
             patch.object(ilan_bot, 'kurum_logosu', return_value=None), \
             patch.object(ilan_bot, 'ilan_sayfasi', return_value='https://example.com/ilan/test/'), \
             patch.object(ilan_bot, 'yerel_oku', return_value={}), \
             patch.object(ilan_bot.time, 'sleep'), \
             patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test', 'TELEGRAM_CHAT_ID': '@test', 'RSS_URLS': ''}), \
             patch('sys.argv', ['bot', '--cikti', str(self.data), *args]), \
             contextlib.redirect_stdout(self.stdout):
            ilan_bot.main()
            return send.call_count

    def _kaydet(self, donus, varsayilan):
        sayac = iter(donus)
        def gonder(*args, **kwargs):
            self.gonderimler.append((args, kwargs))
            return next(sayac, varsayilan)
        return gonder

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

    def test_channel_refresh_is_once_and_merge_preserves_new_queue(self):
        from veri_kaydet import merge_registry
        self.run_bot('--duyur-mevcut');self.run_bot()
        old=json.loads(self.data.read_text())
        cfg=json.loads(self.cfg.read_text());cfg['telegram_yayin_surumu']=2
        self.cfg.write_text(json.dumps(cfg))
        self.assertEqual(self.run_bot('--prepare'),0)
        fresh=json.loads(self.data.read_text())
        merged=merge_registry(old,fresh)
        self.assertEqual(merged['telegram_gonderilen'],[])
        self.assertEqual(len(merged['telegram_bekleyen']),25)
        self.data.write_text(json.dumps(merged))
        self.assertEqual(self.run_bot('--send-only'),15)
        self.assertEqual(self.run_bot('--send-only'),10)
        self.assertEqual(self.run_bot('--send-only'),0)

    def test_site_yayini_oncesi_sadece_hazirla_sonra_gonder(self):
        self.assertEqual(self.run_bot('--prepare','--duyur-mevcut'),0)
        state=json.loads(self.data.read_text())
        self.assertEqual(len(state['telegram_bekleyen']),25)
        self.assertEqual(len(state['canli_kimlikler']),25)
        with patch.object(ilan_bot,'read_sbb',side_effect=AssertionError('Gönderim aşamasında tarama yapılmamalı')):
            self.assertEqual(self.run_bot('--send-only'),15)
            self.assertEqual(self.run_bot('--send-only'),10)
            self.assertEqual(self.run_bot('--send-only'),0)

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
            # Geçici erişim sorunu işi kırmızıya düşürmez; ilanlar sırada bekler.
            self.assertEqual(self.run_bot('--duyur-mevcut'), 0)
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

    SABAH = datetime(2026, 10, 5, 10, 0, tzinfo=timezone(timedelta(hours=3)))

    def prepare_reminders(self, days=3, gonderilen=True):
        deadline = (self.SABAH.date() + timedelta(days=days)).isoformat()
        for i in self.items:
            i['son_tarih'] = deadline
            i['ilk_gorulme'] = (self.SABAH - timedelta(days=5)).isoformat()
        self.data.write_text(json.dumps({'guncelleme': self.SABAH.isoformat(),
            'ilanlar': self.items, 'telegram_gonderilen': [i['id'] for i in self.items] if gonderilen else []}))

    def test_ilan_basina_hatirlatma_artik_gitmez_gecmis_korunur(self):
        self.prepare_reminders(3)
        state = json.loads(self.data.read_text())
        state['telegram_hatirlatilan'] = ['["eski", "2026-09-01"]']
        self.data.write_text(json.dumps(state))
        self.run_bot(zaman=self.SABAH.replace(hour=8))  # 09:00 öncesi: sabah özeti de yok
        self.assertEqual(self.gonderimler, [])
        self.assertEqual(json.loads(self.data.read_text())['telegram_hatirlatilan'], ['["eski", "2026-09-01"]'])

    def test_sabah_ozeti_gunde_bir_kez(self):
        self.prepare_reminders(3)
        self.assertEqual(self.run_bot(zaman=self.SABAH), 1)
        args, kwargs = self.gonderimler[0]
        self.assertIn('Günaydın — 5 Ekim Pazartesi', args[2])
        self.assertIn('Son başvurusu yaklaşanlar', args[2])
        self.assertTrue(kwargs['foto'].startswith(b'\x89PNG'))
        self.assertEqual(json.loads(self.data.read_text())['telegram_toplu_hatirlatma_gunu'], '2026-10-05')
        self.assertEqual(self.run_bot(zaman=self.SABAH.replace(hour=15)), 0)
        self.assertEqual(self.run_bot(zaman=self.SABAH + timedelta(days=1)), 1)  # ertesi gün yine 2 gün kaldı

    def test_sabah_ozeti_09_oncesi_gitmez_sonra_gider(self):
        self.prepare_reminders(1)
        self.assertEqual(self.run_bot(zaman=self.SABAH.replace(hour=8, minute=59)), 0)
        self.assertEqual(self.run_bot(zaman=self.SABAH.replace(hour=9, minute=0)), 1)

    def test_sabah_ozeti_son_gun_yoksa_da_gider_ama_bolum_ve_kart_degisir(self):
        self.prepare_reminders(4)  # kimse 3 gün içinde kapanmıyor ama 25 açık ilan var
        self.assertEqual(self.run_bot(zaman=self.SABAH), 1)
        args, kwargs = self.gonderimler[0]
        self.assertNotIn('Son başvurusu yaklaşanlar', args[2])
        self.assertNotIn('yeni ilan', args[2])
        self.assertIn('Şu an başvurusu açık <b>25 ilan</b>', args[2])
        self.assertTrue(kwargs['foto'].startswith(b'\x89PNG'))

    def test_sabah_ozeti_her_sey_bossa_atlanir_ve_gun_isaretlenmez(self):
        self.prepare_reminders(-1)  # hepsi süresi dolmuş, yeni yok, açık yok
        self.assertEqual(self.run_bot(zaman=self.SABAH), 0)
        self.assertIsNone(json.loads(self.data.read_text()).get('telegram_toplu_hatirlatma_gunu'))

    def test_sabah_ozeti_prepare_modunda_gitmez(self):
        self.prepare_reminders(2, gonderilen=False)
        self.assertEqual(self.run_bot('--prepare', zaman=self.SABAH), 0)
        self.assertIsNone(json.loads(self.data.read_text()).get('telegram_toplu_hatirlatma_gunu'))

    def test_sabah_ozeti_yeni_ilanlar_bolumu(self):
        self.prepare_reminders(2)
        state = json.loads(self.data.read_text())
        for i in state['ilanlar']:
            i['ilk_gorulme'] = (self.SABAH - timedelta(hours=3)).isoformat()
        self.data.write_text(json.dumps(state))
        self.assertEqual(self.run_bot(zaman=self.SABAH), 1)
        metin = self.gonderimler[0][0][2]
        self.assertIn('🆕 <b>Son 24 saatte 1 yeni ilan</b>', metin)  # 25 kayıt aynı kurum+tarih: tek satır

    def test_sabah_ozeti_basarisizsa_gun_isaretlenmez_ve_yeniden_denenir(self):
        self.prepare_reminders(2)
        with self.assertRaises(SystemExit):
            self.run_bot(success=False, zaman=self.SABAH)
        self.assertIsNone(json.loads(self.data.read_text())['telegram_toplu_hatirlatma_gunu'])
        self.assertEqual(self.run_bot(zaman=self.SABAH.replace(hour=11)), 1)
        self.assertEqual(json.loads(self.data.read_text())['telegram_toplu_hatirlatma_gunu'], '2026-10-05')

    def test_sabah_ozeti_gorsel_hatasinda_yalniz_metin_gider(self):
        self.prepare_reminders(2)
        with patch('kart_tasarimlari.toplu_son_gun_karti', side_effect=RuntimeError('bozuk')), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_bot(zaman=self.SABAH), 1)
        args, kwargs = self.gonderimler[0]
        self.assertIsNone(kwargs['foto'])
        self.assertIn('Günaydın', args[2])
        self.assertEqual(json.loads(self.data.read_text())['telegram_toplu_hatirlatma_gunu'], '2026-10-05')

    def test_sabah_ozeti_dry_run_basligi_yazdirir_ve_veriyi_degistirmez(self):
        self.prepare_reminders(2)
        once = self.data.read_bytes()
        self.assertEqual(self.run_bot('--dry-run', zaman=self.SABAH), 0)
        self.assertIn('Günaydın — 5 Ekim Pazartesi', self.stdout.getvalue())
        self.assertEqual(self.data.read_bytes(), once)

    def test_sabah_ozeti_butce_paylasir(self):
        self.prepare_reminders(2)
        state = json.loads(self.data.read_text())
        state['telegram_gonderilen'] = []
        self.data.write_text(json.dumps(state))
        # 25 kanala gitmemiş ilan: özet (yalnız açık sayısı) 1 yer kaplar, 14 ilan gider; limit 15
        self.assertEqual(self.run_bot('--duyur-mevcut', zaman=self.SABAH), 15)
        self.assertIn('Günaydın', self.gonderimler[0][0][2])

    def kayit(self, n, **ek):
        k = {'id': f'i{n}', 'baslik': f'K{n} Belediyesi - Alım', 'kurum': f'K{n} Belediyesi',
             'kadro': f'Toplam {n + 1} kişi — {n + 1} Zabıta Memuru',
             'son_tarih': (self.SABAH.date() + timedelta(days=10)).isoformat(),
             'ilk_gorulme': (self.SABAH - timedelta(hours=2)).isoformat()}
        k.update(ek)
        return k

    def yeniler(self, kayitlar, gonderilen=None):
        gon = {k['id'] for k in kayitlar} if gonderilen is None else gonderilen
        with patch.object(ilan_bot, 'simdi', return_value=self.SABAH):
            return ilan_bot.sabah_yeniler(kayitlar, gon, {}, self.SABAH)

    def test_sabah_yeniler_sabit_pencere_dunku_09_dahil_bugunku_09_haric(self):
        bugun_09 = self.SABAH.replace(hour=9, minute=0)
        s = timedelta(seconds=1)
        sinir = [self.kayit(0, ilk_gorulme=(bugun_09 - timedelta(days=1)).isoformat()),
                 self.kayit(1, ilk_gorulme=(bugun_09 - timedelta(days=1) - s).isoformat()),
                 self.kayit(2, ilk_gorulme=bugun_09.isoformat()),
                 self.kayit(3, ilk_gorulme=(bugun_09 - s).isoformat()),
                 self.kayit(4, ilk_gorulme='bozuk')]
        simdi_gec = self.SABAH.replace(hour=9, minute=50)  # özet geç gitse de pencere değişmez
        with patch.object(ilan_bot, 'simdi', return_value=simdi_gec):
            sonuc = ilan_bot.sabah_yeniler(sinir, {k['id'] for k in sinir}, {}, simdi_gec)
        self.assertEqual({k['id'] for k in sonuc}, {'i0', 'i3'})

    def test_sabah_mesaji_son_gun_listesindeki_yeni_ilan_yalniz_altta_gorunur(self):
        bitis = (self.SABAH.date() + timedelta(days=1)).isoformat()
        ortak = self.kayit(0, son_tarih=bitis, kurum='Ortak Belediyesi')
        diger = self.kayit(1, kurum='Diger Belediyesi')
        with patch.object(ilan_bot, 'simdi', return_value=self.SABAH), \
             patch.object(ilan_bot, 'ilan_sayfasi', return_value='https://example.com/x/'):
            metin = ilan_bot.sabah_mesaj([ortak, diger], [ortak], 9, '', self.SABAH)
        yeni_bolum, son_bolum = metin.split('⏰')
        self.assertIn('Son 24 saatte 2 yeni ilan', yeni_bolum)  # sayı hepsini sayar
        self.assertNotIn('Ortak Belediyesi', yeni_bolum)
        self.assertIn('Diger Belediyesi', yeni_bolum)
        self.assertIn('Ortak Belediyesi', son_bolum)
        self.assertNotIn('ilan daha', yeni_bolum)
    def test_sabah_yeniler_kanalda_paylasilmayan_girmez(self):
        kayitlar = [self.kayit(0), self.kayit(1)]
        self.assertEqual([k['id'] for k in self.yeniler(kayitlar, {'i1'})], ['i1'])

    def test_sabah_yeniler_akademik_iptal_duyuru_disarida(self):
        kayitlar = [self.kayit(0, iptal_edildi='x-1'), self.kayit(1, duyuru_turu='İptal duyurusu'),
                    self.kayit(2, kategori='akademik'), self.kayit(3, ozet='Doçentliğini almış olmak (2547 sayılı Kanun)'),
                    self.kayit(4)]
        self.assertEqual([k['id'] for k in self.yeniler(kayitlar)], ['i4'])

    def test_sabah_yeniler_tekilleştirir_ve_buyuk_kadro_once(self):
        bitis = (self.SABAH.date() + timedelta(days=5)).isoformat()
        kayitlar = [self.kayit(0, id='sbb-' + 'a' * 24, kurum='ŞİLE BELEDİYE BAŞKANLIĞI', son_tarih=bitis, kadro='Toplam 2 kişi — 2 Memur'),
                    self.kayit(1, id='iskur-' + 'b' * 24, kurum='İstanbul Şile Belediyesi', son_tarih=bitis, kadro='Toplam 2 kişi — 2 Memur'),
                    self.kayit(2, kadro='Toplam 40 kişi — 40 Hemşire'), self.kayit(3)]
        sonuc = self.yeniler(kayitlar)
        self.assertEqual(len(sonuc), 3)
        self.assertEqual(sonuc[0]['id'], 'i2')

    def test_sabah_mesaji_bos_bolumleri_yazmaz_ve_turkce_tarih(self):
        with patch.object(ilan_bot, 'ilan_sayfasi', return_value='https://example.com/x/'):
            yalniz_acik = ilan_bot.sabah_mesaj([], [], 7, 'https://example.com/', self.SABAH)
            self.assertNotIn('🆕', yalniz_acik)
            self.assertNotIn('⏰', yalniz_acik)
            self.assertNotIn('yeni ilan', yalniz_acik)
            self.assertIn('☀️ <b>Günaydın — 5 Ekim Pazartesi</b>', yalniz_acik)
            self.assertIn('📌 Şu an başvurusu açık <b>7 ilan</b>', yalniz_acik)
            self.assertIn('href="https://example.com/?g=bugun"', yalniz_acik)
            yeni = ilan_bot.sabah_mesaj([self.kayit(0)], [], 7, '', self.SABAH)
        self.assertIn('🆕 <b>Son 24 saatte 1 yeni ilan</b> · 1 kadro', yeni)
        self.assertNotIn('⏰', yeni)
        self.assertNotIn('👉', yeni)  # site adresi yoksa bağlantı satırı yok
        for gun, ad in enumerate(('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')):
            self.assertTrue(ilan_bot.turkce_tarih(self.SABAH + timedelta(days=gun)).endswith(ad))
        self.assertEqual(ilan_bot.turkce_tarih(datetime(2026, 8, 30, tzinfo=self.SABAH.tzinfo)), '30 Ağustos Pazar')

    def test_sabah_mesaji_butce_asilinca_once_yeni_sonra_son_gun_kisalir_altlik_kalir(self):
        uzun = 'Çok Uzun Adlı Büyükşehir Belediye Başkanlığı Zabıta Müdürlüğü '
        yeni = [self.kayit(n, kurum=uzun + str(n), baslik=uzun) for n in range(12)]
        bitis = (self.SABAH.date() + timedelta(days=1)).isoformat()
        son = [self.kayit(n + 20, kurum=uzun + str(n + 20), son_tarih=bitis) for n in range(10)]
        with patch.object(ilan_bot, 'simdi', return_value=self.SABAH), \
             patch.object(ilan_bot, 'ilan_sayfasi', return_value='https://example.com/ilan/x/'):
            tam = ilan_bot.sabah_mesaj(yeni[:1], son[:1], 30, 'https://example.com/', self.SABAH)
            metin = ilan_bot.sabah_mesaj(yeni, son, 30, 'https://example.com/', self.SABAH)
        self.assertLessEqual(ilan_bot.gorunen_uzunluk(tam), ilan_bot.TOPLU_SINIR)
        self.assertLessEqual(ilan_bot.gorunen_uzunluk(metin), ilan_bot.TOPLU_SINIR)
        yeni_bolum, son_bolum = metin.split('⏰')
        self.assertGreaterEqual(yeni_bolum.count('• '), 3)  # yeni liste en az 3'e kadar kısalır
        self.assertLess(yeni_bolum.count('• '), 5)
        self.assertIn('ilan daha', yeni_bolum)
        self.assertIn('📌 Şu an başvurusu açık <b>30 ilan</b>', metin)
        self.assertIn('Bugünün tüm ilanları', metin)
        self.assertTrue(metin.startswith('☀️ <b>Günaydın'))

    def test_toplu_secimde_iptal_akademik_duyuru_olmayanlar_yer_almaz(self):
        kayitlar = []
        for n in range(25):
            k = {'id': f'i{n}', 'baslik': f'K{n} Belediyesi - Alım', 'kurum': f'K{n} Belediyesi',
                 'son_tarih': (self.SABAH.date() + timedelta(days=2)).isoformat()}
            if n == 0: k['iptal_edildi'] = 'csb-1'
            if n == 1: k['duyuru_turu'] = 'İptal duyurusu'
            if n == 2: k['kategori'] = 'akademik'
            if n == 3: k['ozet'] = 'Doçentliğini almış olmak (2547 sayılı Kanun)'
            kayitlar.append(k)
        with patch.object(ilan_bot, 'simdi', return_value=self.SABAH), patch.object(ilan_bot, 'ilan_sayfasi', return_value='https://example.com/x/'):
            secim = ilan_bot.toplu_secim(kayitlar, {k['id'] for k in kayitlar}, {})
            self.assertEqual(len(secim), 21)  # 25 - 4 dışlanan
            metin = ilan_bot.sabah_mesaj([], secim, 21, '', self.SABAH)
        self.assertEqual(metin.count('• '), 6)
        self.assertIn('+15 ilan daha', metin)

    def test_toplu_secimde_ayni_kurum_ve_tarih_tek_satir(self):
        bitis = (self.SABAH.date() + timedelta(days=1)).isoformat()
        kayitlar = [{'id': 'sbb-' + 'a' * 24, 'baslik': 'X', 'kurum': 'ŞİLE BELEDİYE BAŞKANLIĞI', 'son_tarih': bitis},
                    {'id': 'iskur-' + 'b' * 24, 'baslik': 'X', 'kurum': 'İstanbul Şile Belediyesi', 'son_tarih': bitis},
                    {'id': 'iskur-' + 'c' * 24, 'baslik': 'Y', 'kurum': 'Başka Belediyesi', 'son_tarih': bitis}]
        with patch.object(ilan_bot, 'simdi', return_value=self.SABAH):
            secim = ilan_bot.toplu_secim(kayitlar, {k['id'] for k in kayitlar}, {})
        self.assertEqual(len(secim), 2)

    def test_acik_sayisi_site_tanimiyla_ayni(self):
        s = self.SABAH
        kayitlar = [self.kayit(0), self.kayit(1, son_tarih=None), self.kayit(2, son_tarih='2026-10-04'),
                    self.kayit(3, duyuru_turu='Düzeltme duyurusu'), self.kayit(4, kategori='akademik'),
                    self.kayit(5, iptal_edildi='x'), self.kayit(6, baslangic_zaman=(s + timedelta(days=1)).isoformat()),
                    self.kayit(7, baslangic_zaman=(s - timedelta(days=1)).isoformat()), self.kayit(8, son_tarih=s.date().isoformat())]
        with patch.object(ilan_bot, 'simdi', return_value=s):
            self.assertEqual(ilan_bot.sabah_acik_sayisi(kayitlar, s), 3)  # 0, 7, 8
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


class EtiketTests(unittest.TestCase):
    def test_mesaj_etiket_satiri_icerir(self):
        ilan = {'baslik': 'Ankara Pursaklar Belediyesi Zabıta Memuru Alım İlanı',
                'kurum': 'Ankara Pursaklar Belediyesi', 'yer': 'Ankara', 'son_tarih': '2099-10-23'}
        metin = ilan_bot.mesaj_olustur(ilan, 'https://ornek.example/')
        self.assertTrue(metin.rstrip().endswith('#Ankara #belediye'))

    def test_siniflandir_bos_alanlari_kaldirir(self):
        ilan = {'baslik': 'Genel duyuru', 'ogrenim': ['lisans'], 'kategori': 'belediye'}
        ilan_bot.siniflandir(ilan)
        self.assertNotIn('ogrenim', ilan)
        self.assertNotIn('kategori', ilan)

    def test_siniflandir_il_ve_kpss_yazar_ve_temizler(self):
        ilan = {'baslik': 'Zabıta Memuru', 'yer': 'Ankara / Çankaya • İzmir', 'ozet': 'KPSS puanı ile'}
        ilan_bot.siniflandir(ilan)
        self.assertEqual(ilan['iller'], ['Ankara', 'İzmir'])
        self.assertEqual(ilan['kpss'], 'kpss')
        ilan.update({'yer': 'Bakanlık merkez teşkilatı', 'ozet': 'Genel duyuru'})
        ilan_bot.siniflandir(ilan)
        self.assertNotIn('iller', ilan)
        self.assertNotIn('kpss', ilan)


class IlanGorseliTesti(unittest.TestCase):
    ILAN = {'id': 'x', 'baslik': 'Örnek Belediyesi - Alım', 'kurum': 'Örnek Belediyesi', 'son_tarih': '2099-10-23',
            'kadro': 'Toplam 3 kişi — 3 Zabıta Memuru', 'yer': 'Ankara'}

    def test_yeni_kart_kullanilir(self):
        import io
        from PIL import Image
        foto = ilan_bot.ilan_gorseli(self.ILAN, False)
        self.assertEqual(Image.open(io.BytesIO(foto)).size, (1080, 1350))

    def test_yeni_kart_hata_verirse_eski_karta_duser(self):
        import io
        from PIL import Image
        import kart_tasarimlari
        with mock.patch.object(kart_tasarimlari, 'ilan_karti', side_effect=RuntimeError('x')):
            foto = ilan_bot.ilan_gorseli(self.ILAN, False)
        self.assertEqual(Image.open(io.BytesIO(foto)).size[0], 1200)  # eski kart genişliği


if __name__ == '__main__':
    unittest.main()
