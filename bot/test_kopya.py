import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import kopya
import kurum_sayfasi as ks
import liste_verisi as lv
import site_uret
from site_uret import TR

VERI = json.loads((Path(__file__).parent / 'test_veri' / 'kopya_ilanlar.json').read_text(encoding='utf-8'))
SIMDI = datetime(2026, 10, 5, 12, 0, tzinfo=TR)
ELM_SBB, ELM_ISKUR, ELM_CSB = 'sbb-97e476fbb140b9951ef70fe8', 'iskur-3f593d9e3c71078c698a111a', 'csb-477595'
MUCUR_SBB, MUCUR_ISKUR, MUCUR_ISKUR_2, MUCUR_CSB = 'sbb-866abc35896ad9d91ee671c5', 'iskur-ced29e58351712e81082b7e6', 'iskur-82e1a52fc83cba2b4d8fa6ff', 'csb-477599'
GOLE_ISKUR, GOLE_CSB = 'iskur-46fd3ccae48ba3acd1a3e086', 'csb-477229'
HANAK = ['iskur-90bc49ba5ab8723a8adb1001', 'sbb-c49d399e06ae4c205b04a173', 'csb-477209']
SUBASI = ['sbb-6f51d37c2089a1c701085572', 'iskur-1c1015bfd1faeaea90028a12']


def sec(*ids):
    return [json.loads(json.dumps(i)) for i in VERI if i['id'] in ids]


def bul(*ids):
    return kopya.kopya_bul(sec(*ids))['kopya_of']


class KopyaTests(unittest.TestCase):
    def test_elmakaya_uc_kaynak_tek_ilan(self):
        sonuc = bul(ELM_SBB, ELM_ISKUR, ELM_CSB)
        self.assertEqual(len(sonuc), 2)
        self.assertEqual(len(set(sonuc.values())), 1, 'üç kayıt tek birincilde toplanır')
        self.assertNotIn(next(iter(set(sonuc.values()))), sonuc)

    def test_sira_sonucu_degistirmez(self):
        a = kopya.kopya_bul(sec(ELM_SBB, ELM_ISKUR, ELM_CSB))['kopya_of']
        b = kopya.kopya_bul(list(reversed(sec(ELM_SBB, ELM_ISKUR, ELM_CSB))))['kopya_of']
        self.assertEqual(a, b)

    def test_csb_duyurusu_tek_gruba_baglanir(self):
        self.assertEqual(bul(GOLE_ISKUR, GOLE_CSB), {GOLE_CSB: GOLE_ISKUR})

    def test_genel_unvan_esit_toplam(self):
        # SBB '2 MEMUR' ile İŞKUR '2 İtfaiye Eri': aynı gün, aynı il, eşit toplam -> kopya
        self.assertEqual(len(bul(MUCUR_SBB, MUCUR_ISKUR)), 1)

    def test_ayni_kurum_farkli_son_tarih_kopya_degil(self):
        self.assertEqual(bul(MUCUR_SBB, MUCUR_ISKUR_2), {})
        iskur = sec(ELM_ISKUR)[0]
        iskur['son_tarih'] = '2026-10-22'
        self.assertEqual(kopya.kopya_bul(sec(ELM_SBB) + [iskur])['kopya_of'], {})

    def test_ayni_adli_belediye_farkli_il_kopya_degil(self):
        iskur = sec(ELM_ISKUR)[0]
        iskur.update(kurum='Konya Elmakaya Belediyesi', iller=['Konya'], yer='Konya')
        sbb = sec(ELM_SBB)[0]
        sbb.update(iller=['Muş'], yer='Muş')
        self.assertEqual(kopya.kopya_bul([sbb, iskur])['kopya_of'], {})

    def test_ili_yazmayan_kayit_belirsiz_adda_il_cozmez(self):
        # SBB kaydında il yok; 'Elmakaya Belediyesi' hem Konya hem Muş'ta var -> ili çözülemez, birleşmez
        sbb, konya, mus = sec(ELM_SBB)[0], sec(ELM_ISKUR)[0], sec(ELM_ISKUR)[0]
        konya.update(kurum='Konya Elmakaya Belediyesi', iller=['Konya'], yer='Konya', id='iskur-000000000000000000000001')
        mus.update(id='iskur-000000000000000000000002')
        self.assertEqual(kopya.kopya_bul([sbb, konya, mus])['kopya_of'], {})
        # il yalnız tek yerde biliniyorsa SBB kaydı o ile bağlanır
        self.assertEqual(len(kopya.kopya_bul([sbb, mus])['kopya_of']), 1)

    def test_farkli_kadro_kopya_degil(self):
        iskur = sec(ELM_ISKUR)[0]
        iskur['kadro'] = '1 Zabıta Memuru'
        self.assertEqual(kopya.kopya_bul(sec(ELM_SBB) + [iskur])['kopya_of'], {})

    def test_tek_tarafta_kadro_bilgisi_dogrulanamaz(self):
        self.assertEqual(bul(*SUBASI), {})

    def test_ayni_kaynak_iki_kayit_kopya_degil(self):
        a, b = sec(ELM_SBB)[0], sec(ELM_SBB)[0]
        b['id'] = 'sbb-000000000000000000000001'
        self.assertEqual(kopya.kopya_bul([a, b])['kopya_of'], {})

    def test_belirsiz_csb_baglanmaz(self):
        # Mucur: iki ayrı grup (10-08 ve 10-28) var; ÇŞB 'memur alım ilanı' hangisine ait belli değil
        self.assertNotIn(MUCUR_CSB, bul(MUCUR_SBB, MUCUR_ISKUR, MUCUR_ISKUR_2, MUCUR_CSB))
        # Hanak: İŞKUR (10-05) ve SBB (10-07) farklı gün -> ikisi de ÇŞB'ye aday, hiçbiri birleşmez
        self.assertEqual(bul(*HANAK), {})

    def test_csb_pencere_disi_baglanmaz(self):
        csb = sec(GOLE_CSB)[0]
        csb['yayim_tarihi'] = '2026-05-01'
        self.assertEqual(kopya.kopya_bul(sec(GOLE_ISKUR) + [csb])['kopya_of'], {})

    def test_csb_sozlesmeli_ile_memur_baglanmaz(self):
        csb = sec(GOLE_CSB)[0]
        csb['baslik'] = 'GÖLE BELEDİYE BAŞKANLIĞI - İLK DEFA ATANMAK ÜZERE SÖZLEŞMELİ PERSONEL ALIM İLANI'
        self.assertEqual(kopya.kopya_bul(sec(GOLE_ISKUR) + [csb])['kopya_of'], {})

    def test_takma_ad_kopya_sayilir(self):
        a, b = sec(ELM_SBB)[0], sec(ELM_ISKUR)[0]
        b['son_tarih'] = '2026-12-01'
        a['kaynak_kimlikleri'] = [a['id'], b['id']]
        self.assertEqual(len(kopya.kopya_bul([a, b])['kopya_of']), 1)

    def test_duyuru_ve_iptal_katilmaz(self):
        csb = sec(GOLE_CSB)[0]
        csb['duyuru_turu'] = 'Düzeltme / süre değişikliği'
        self.assertEqual(kopya.kopya_bul(sec(GOLE_ISKUR) + [csb])['kopya_of'], {})

    def test_kaynak_adlari_ve_baglantilari(self):
        sonuc = kopya.kopya_bul(sec(ELM_SBB, ELM_ISKUR, ELM_CSB))
        uyeler = next(iter(sonuc['uyeler'].values()))
        self.assertEqual(kopya.kaynak_adlari(uyeler), ['SBB', 'ÇŞB', 'İŞKUR'])
        self.assertEqual(len(kopya.kaynak_baglantilari(uyeler)), 3)


def kk_kayit(n, kurum, baslik, son, **ek):
    return {'id': 'https://kariyerkapisi.gov.tr/IlanDetay?i=%08d-2222-4222-8222-222222222222' % n,
            'link': 'https://kariyerkapisi.gov.tr/IlanDetay?i=%08d-2222-4222-8222-222222222222' % n,
            'kurum': kurum, 'baslik': baslik, 'kadro': baslik, 'son_tarih': son, 'ilk_gorulme': '2026-10-05T17:00:00+03:00', **ek}


def sbb_kayit(n, kurum, kadro, son=None, donem=None, **ek):
    return {'id': 'sbb-%024x' % n, 'link': 'https://kamuilan.sbb.gov.tr/', 'kaynak_turu': 'sbb', 'kurum': kurum, 'baslik': kurum + ' - ' + kadro,
            'kadro': kadro, 'son_tarih': son, 'donem': donem, 'ilk_gorulme': '2026-10-05T17:20:00+03:00', **ek}


def iskur_kayit(n, kurum, baslik, son, yer='Ankara', **ek):
    return {'id': 'iskur-%024x' % n, 'link': 'https://www.iskur.gov.tr/x/%d.pdf' % n, 'kaynak_turu': 'iskur', 'kurum': kurum, 'baslik': baslik,
            'kadro': baslik, 'son_tarih': son, 'yer': yer, 'ilk_gorulme': '2026-09-26T20:00:00+03:00', **ek}


class CokKaynakliKopyaTests(unittest.TestCase):
    ICRA_KK = ('ADALET BAKANLIĞI', 'ADALET BAKANLIĞI - 2026 Yılı Açıktan İcra Müdür ve İcra Müdür Yardımcısı Alım İlanı', '2026-11-05')

    def test_sbb_son_tarihi_donemden_gelir_ve_sinav_penceresi_kk_ile_birlesir(self):
        kk = kk_kayit(1, *self.ICRA_KK)
        sbb = sbb_kayit(1, 'ADALET BAKANLIĞI', '150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.', donem='( 20 Ekim - 26 Ekim)')
        self.assertEqual(kopya.kopya_bul([kk, sbb])['kopya_of'], {sbb['id']: kk['id']} if kopya._zengin(kk) < kopya._zengin(sbb) else {kk['id']: sbb['id']})

    def test_sinav_penceresi_toplam_farkliysa_birlesmez(self):
        kk = kk_kayit(1, *self.ICRA_KK, kadro='Toplam 100 kişi — 100 İcra Müdür Yardımcısı')
        sbb = sbb_kayit(1, 'ADALET BAKANLIĞI', '150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.', donem='( 20 Ekim - 26 Ekim)')
        self.assertEqual(kopya.kopya_bul([kk, sbb])['kopya_of'], {})

    def test_farkli_unvan_ayni_kurum_ayni_pencere_birlesmez(self):
        kk = kk_kayit(1, 'ADALET BAKANLIĞI', 'ADALET BAKANLIĞI - Zabıt Katibi Alım İlanı', '2026-11-05')
        sbb = sbb_kayit(1, 'ADALET BAKANLIĞI', '150 İCRA MÜDÜR VE İCRA MÜDÜR YARDIMCISI ALACAK.', donem='( 20 Ekim - 26 Ekim)')
        self.assertEqual(kopya.kopya_bul([kk, sbb])['kopya_of'], {})

    def test_iskur_sbb_tarih_yoksa_ilk_gorulme_yakinsa_birlesir(self):
        iskur = iskur_kayit(1, 'Cumhurbaşkanlığı İletişim Başkanlığı', 'Cumhurbaşkanlığı İletişim Başkanlığı İletişim Uzman Yardımcılığı Sınav İlanı', '2026-10-20')
        sbb = sbb_kayit(1, 'İLETİŞİM BAŞKANLIĞI', '15 UZMAN YARDIMCISI ALACAK', donem='( 5 Ekim - 20 Ekim)')
        self.assertEqual(len(kopya.kopya_bul([iskur, sbb])['kopya_of']), 1)

    def test_kurum_cekirdegi(self):
        def c(k):
            return kopya._kurum_cekirdek({'kurum': k}, ks.kurum_kanonik(k))
        self.assertEqual(c('İstanbul Bankacılık Düzenleme ve Denetleme Kurumu'), c('BANKACILIK DÜZENLEME VE DENETLEME KURUMU BAŞKANLIĞI (BDDK)'))
        self.assertEqual(c('Cumhurbaşkanlığı İletişim Başkanlığı'), c('İLETİŞİM BAŞKANLIĞI'))
        self.assertEqual(c('Doğu Marmara Kalkınma Ajansı (MARKA)'), c('DOĞU MARMARA KALKINMA AJANSI'))
        self.assertEqual(c('Bahçe (OSMANİYE) Belediye Başkanlığı'), c('Osmaniye Bahçe Belediyesi'))
        self.assertNotEqual(c('Göç İdaresi Başkanlığı'), c('Gelir İdaresi Başkanlığı'))
        self.assertNotEqual(c('Ankara Kalkınma Ajansı'), c('İzmir Kalkınma Ajansı'))

    def test_farkli_kurum_ayni_unvan_birlesmez(self):
        a = sbb_kayit(1, 'GÖÇ İDARESİ GENEL MÜDÜRLÜĞÜ', '3 UZMAN YARDIMCISI ALACAK', son='2026-10-20')
        b = iskur_kayit(1, 'Gelir İdaresi Başkanlığı', 'Gelir İdaresi Başkanlığı 3 Uzman Yardımcısı', '2026-10-20')
        self.assertEqual(kopya.kopya_bul([a, b])['kopya_of'], {})


class KalanKopyaTests(unittest.TestCase):
    def test_toplam_virgullu_sbb_kadro(self):
        sbb = sbb_kayit(1, 'DOĞU MARMARA KALKINMA AJANSI', '3 UZMAN, 2 DESTEK PERSONEL ALACAK', son='2026-10-27')
        self.assertEqual(ks.kart_alanlari(sbb)['toplam'], 5)
        self.assertEqual([a for a, _ in ks.kadrolar(sbb)], [3, 2])
        self.assertEqual(ks.kadrolar({'kadro': '3 Uzman Yardımcısı, Ankara'}), [(3, 'Uzman Yardımcısı, Ankara')])

    def marka(self):
        kk = kk_kayit(1, 'DOĞU MARMARA KALKINMA AJANSI (MARKA)', 'DOĞU MARMARA KALKINMA AJANSI (MARKA) - PERSONEL ALIM İLANI (2026)', '2026-10-27',
                      kadro='Toplam 5 kişi — 3 UZMAN • 2 BÜRO PERSONELİ / DESTEK PERSONELİ', iller=['Kocaeli', 'Sakarya'], yer='KOCAELİ, SAKARYA')
        sbb = sbb_kayit(1, 'DOĞU MARMARA KALKINMA AJANSI', '3 UZMAN, 2 DESTEK PERSONEL ALACAK', son='2026-10-27')
        iskur = iskur_kayit(1, 'Doğu Marmara Kalkınma Ajansı', 'Doğu Marmara Kalkınma Ajansı Personel Alım İlanı', '2026-10-27', yer='Kocaeli', iller=['Kocaeli'])
        iskur.pop('kadro')
        return kk, sbb, iskur

    def test_kalkinma_ajansi_uc_kaynak_birlesir(self):
        kk, sbb, iskur = self.marka()
        sonuc = kopya.kopya_bul([kk, sbb, iskur])
        self.assertEqual(len(sonuc['kopya_of']), 2)
        self.assertEqual(len(set(sonuc['kopya_of'].values())), 1)

    def test_kalkinma_ajansi_ayni_gun_iki_ilan_ise_genel_baslikli_birlesmez(self):
        kk, sbb, iskur = self.marka()
        ikinci = sbb_kayit(2, 'DOĞU MARMARA KALKINMA AJANSI', '1 AVUKAT ALACAK', son='2026-10-27')
        sonuc = kopya.kopya_bul([kk, sbb, iskur, ikinci])['kopya_of']
        self.assertNotIn(sonuc.get(iskur['id']), {kk['id'], sbb['id']})   # İŞKUR bu iki kayıtla (tekil kuralı) eşlenmez
        self.assertNotIn(ikinci['id'], sonuc)

    def test_kalkinma_ajansi_farkli_son_tarih_birlesmez(self):
        kk, sbb, iskur = self.marka()
        iskur['son_tarih'] = '2026-11-20'
        self.assertNotIn(iskur['id'], kopya.kopya_bul([kk, sbb, iskur])['kopya_of'])

    def test_genel_baslikli_belediyede_birlesmez(self):
        sbb = sbb_kayit(1, 'ÇUKURKUYU (NİĞDE) BELEDİYE BAŞKANLIĞI', '1 MEMUR ALACAK', son='2026-10-27')
        iskur = iskur_kayit(1, 'Niğde Çukurkuyu Belediyesi', 'Niğde Çukurkuyu Belediyesi Personel Alım İlanı', '2026-10-27', yer='Niğde', iller=['Niğde'])
        iskur.pop('kadro')
        self.assertEqual(kopya.kopya_bul([sbb, iskur])['kopya_of'], {})

    def jandarma(self):
        kk = kk_kayit(1, 'JANDARMA VE SAHİL GÜVENLİK AKADEMİSİ BAŞKANLIĞI',
                      'JANDARMA VE SAHİL GÜVENLİK AKADEMİSİ BAŞKANLIĞI - 2026 YILI J.GN.K.LIĞININ SÖZLEŞMELİ PİLOT (UÇAK) TEMİNİ', '2026-10-11', kadro='')
        sbb = sbb_kayit(1, 'JANDARMA GENEL KOMUTANLIĞI', '1 SÖZLEŞMELİ PİLOT (UÇAK) TEMİN EDECEKTİR', donem='( 24 Eylül - 11 Ekim)')
        return kk, sbb

    def test_jandarma_pilot_birlesir(self):
        kk, sbb = self.jandarma()
        self.assertEqual(len(kopya.kopya_bul([kk, sbb])['kopya_of']), 1)

    def test_jandarma_akademi_baska_ilan_birlesmez(self):
        kk, sbb = self.jandarma()
        bilisim = kk_kayit(2, kk['kurum'], 'JANDARMA VE SAHİL GÜVENLİK AKADEMİSİ BAŞKANLIĞI - 2026 YILI JANDARMA GENEL KOMUTANLIĞININ SÖZLEŞMELİ BİLİŞİM PERSONELİ TEMİNİ', '2026-10-11', kadro='')
        self.assertEqual(kopya.kopya_bul([bilisim, sbb])['kopya_of'], {})
        # J.Gn.K. adı geçmeyen Akademi ilanı (kendi öğrencisi alımı) takma adla eşleşmez
        kk['baslik'] = 'JANDARMA VE SAHİL GÜVENLİK AKADEMİSİ BAŞKANLIĞI - SÖZLEŞMELİ PİLOT (UÇAK) TEMİNİ'
        self.assertEqual(kopya.kopya_bul([kk, sbb])['kopya_of'], {})

    def test_jandarma_farkli_donem_birlesmez(self):
        kk, sbb = self.jandarma()
        sbb['donem'] = '( 24 Ekim - 11 Kasım)'
        self.assertEqual(kopya.kopya_bul([kk, sbb])['kopya_of'], {})

    def cukurkuyu(self, sartlar_unvan='Zabıta Memuru'):
        sbb = sbb_kayit(1, 'ÇUKURKUYU (NİĞDE) BELEDİYE BAŞKANLIĞI', '1 MEMUR ALACAK', son='2026-10-27',
                        sartlar=[{'kadro': 'Sınav puanı koşulu', 'metin': f'Sıra Kadro Unvanı 1 {sartlar_unvan} GİH 10 1 P93 60'}])
        iskur = iskur_kayit(1, 'Niğde Çukurkuyu Belediyesi', 'Niğde Çukurkuyu Belediyesi Zabıta Memuru Alım İlanı', '2026-10-27', yer='Niğde', iller=['Niğde'])
        iskur.pop('kadro')
        return sbb, iskur

    def test_genel_memur_belgede_zabita_gecerse_birlesir(self):
        self.assertEqual(len(kopya.kopya_bul(list(self.cukurkuyu()))['kopya_of']), 1)

    def test_genel_memur_belgede_zabita_yoksa_birlesmez(self):
        self.assertEqual(kopya.kopya_bul(list(self.cukurkuyu('Veri Hazırlama ve Kontrol İşletmeni')))['kopya_of'], {})

    def hanak(self):
        not_ = 'Elektronik ortamda başvurular, 01/10/2026 – 05/10/2026 tarihleri arasında yapılacaktır.'
        sbb = sbb_kayit(1, 'HANAK BELEDİYE BAŞKANLIĞI', '3 MEMUR ALACAK', son='2026-10-07', basvuru_notu='a) ' + not_)
        iskur = iskur_kayit(1, 'Ardahan Hanak Belediyesi', 'Ardahan Hanak Belediyesi Memur Alım İlanı', '2026-10-05', yer='Ardahan', iller=['Ardahan'],
                            kadro='Toplam 3 kişi — 1 Memur • 1 VHKİ • 1 Tahsildar', basvuru_notu=not_)
        return sbb, iskur

    def test_hanak_ayni_basvuru_araligi_birlesir(self):
        self.assertEqual(len(kopya.kopya_bul(list(self.hanak()))['kopya_of']), 1)

    def test_hanak_aralik_farkliysa_ya_da_yoksa_birlesmez(self):
        sbb, iskur = self.hanak()
        sbb['basvuru_notu'] = 'Başvurular 03/10/2026 – 07/10/2026 tarihleri arasındadır.'
        self.assertEqual(kopya.kopya_bul([sbb, iskur])['kopya_of'], {})
        sbb, iskur = self.hanak()
        sbb.pop('basvuru_notu')
        self.assertEqual(kopya.kopya_bul([sbb, iskur])['kopya_of'], {})

    def test_posof_sozlesmeli_csb_ile_memur_sbb_birlesmez(self):
        sbb = sbb_kayit(1, 'POSOF BELEDİYE BAŞKANLIĞI', '1 MEMUR ALACAK', son='2026-11-04')
        csb = {'id': 'csb-477947', 'link': 'https://yerelyonetimler.csb.gov.tr/x-477947', 'kaynak_turu': 'csb', 'kurum': 'POSOF BELEDİYE BAŞKANLIĞI',
               'baslik': 'POSOF BELEDİYE BAŞKANLIĞI - İLK DEFA ATANMAK ÜZERE SÖZLEŞMELİ PERSONEL ALIM İLANI', 'kadro': '', 'yer': 'Ardahan',
               'iller': ['Ardahan'], 'yayim_tarihi': '2026-09-29', 'ilk_gorulme': '2026-10-01T20:47:43+03:00'}
        self.assertEqual(kopya.kopya_bul([sbb, csb])['kopya_of'], {})


class ListeKopyaTests(unittest.TestCase):
    def liste(self, ilanlar, **ek):
        return lv.liste_uret(ilanlar, {}, Path(tempfile.mkdtemp()), SIMDI, **ek)

    def test_ikincil_satir_isaretlenir_sayilar_tek_sayar(self):
        v = self.liste(sec(ELM_SBB, ELM_ISKUR, ELM_CSB, GOLE_ISKUR, GOLE_CSB))
        ikincil = [k for k in v['ilanlar'] if k.get('kopya_of')]
        self.assertEqual(len(ikincil), 3, 'Elmakaya iki, Göle bir ikincil')
        birincil = [k for k in v['ilanlar'] if k.get('kaynak_sayisi')]
        self.assertEqual(len(birincil), 2)
        elm = next(k for k in birincil if 'elmakaya' in k['kurum'].lower())
        self.assertEqual(elm['kaynaklar'], ['SBB', 'ÇŞB', 'İŞKUR'])
        self.assertEqual(elm['kaynak_sayisi'], 3)
        self.assertEqual(v['sayilar']['acik'], len(v['ilanlar']) - 3)
        self.assertTrue(all(k['kopya_of'] in {x['key'] for x in v['ilanlar']} for k in ikincil))
        self.assertEqual(sum(v['takvim'].values()), len([k for k in v['ilanlar'] if not k.get('kopya_of') and k.get('son_tarih')]))

    def test_birincil_satiri_yoksa_ikincil_gorunur_kalir(self):
        iskur = sec(ELM_ISKUR)[0]
        sbb = sec(ELM_SBB)[0]
        sbb['son_zaman'] = '2026-10-05T09:00:00+03:00'   # birincil (SBB) kapandı -> satırı yok
        v = self.liste([sbb, iskur], kopyalar=kopya.kopya_bul([sbb, iskur]))
        self.assertEqual([k for k in v['ilanlar'] if k.get('kopya_of')], [])

    def test_uyari(self):
        a, b = sec(ELM_SBB)[0], sec(GOLE_ISKUR)[0]
        a['detay_guncelleme'] = '2026-10-05T08:00:00+03:00'
        b.pop('detay_guncelleme', None)
        v = self.liste([a, b], kaynak_durumlari={'sbb': {'hata_sayisi': 2}, 'iskur': {'hata_sayisi': 0}, 'csb': {'hata_sayisi': 1}})
        self.assertEqual(v['uyari'], {'kaynaklar': ['SBB', 'ÇŞB Yerel Yönetimler'], 'eski_detay': 1})
        self.assertEqual(self.liste([a], kaynak_durumlari={'sbb': {'hata_sayisi': 0}})['uyari'], {})

    def test_uyari_uret_kaynak_adi(self):
        self.assertEqual(lv.uyari_uret({'iskur': {'hata_sayisi': 1}, 'x': 'bozuk'}, [], SIMDI), {'kaynaklar': ['İŞKUR']})
        self.assertTrue(lv.eski_detay({'detay_guncelleme': '2026-10-04T11:00:00+03:00'}, SIMDI))
        self.assertFalse(lv.eski_detay({'detay_guncelleme': '2026-10-05T01:00:00+03:00'}, SIMDI))
        self.assertTrue(lv.eski_detay({}, SIMDI))
        self.assertFalse(lv.eski_detay({'detay_guncelleme': 'bozuk'}, SIMDI))


class SayfaKopyaTests(unittest.TestCase):
    def setUp(self):
        self.ilanlar = sec(ELM_SBB, ELM_ISKUR, ELM_CSB)
        self.kopyalar = kopya.kopya_bul(self.ilanlar)
        self.harita = {i['id']: i for i in self.ilanlar}
        self.birincil = next(iter(self.kopyalar['uyeler']))

    def sayfa(self, kimlik):
        item = self.harita[kimlik]
        bilgi = kopya.sayfa_bilgisi(self.kopyalar, item, self.harita)
        return site_uret.detail_page(item, kopya=bilgi, simdi=SIMDI)[1], bilgi

    def test_birincil_sayfada_kaynak_satiri(self):
        html, bilgi = self.sayfa(self.birincil)
        self.assertEqual(bilgi['rol'], 'birincil')
        self.assertIn('Bu ilan 3 kaynakta yayımlandı', html)
        self.assertIn('https://kamuilan.sbb.gov.tr/', html)
        self.assertIn('yerelyonetimler.csb.gov.tr', html)
        self.assertIn('iskur.gov.tr', html)
        self.assertNotIn('daha ayrıntılı kaydı', html)
        self.assertEqual(sorted(bilgi['ikincil_idler']), sorted(self.kopyalar['kopya_of']))
        self.assertIn('data-ikincil="', html)

    def test_ikincil_sayfa_birincile_baglanir(self):
        ikincil = next(iter(self.kopyalar['kopya_of']))
        html, bilgi = self.sayfa(ikincil)
        self.assertEqual(bilgi['rol'], 'ikincil')
        self.assertIn('Bu ilanın daha ayrıntılı kaydı →', html)
        self.assertIn(f'href="../{bilgi["birincil"]}/"', html)
        self.assertNotIn('kaynakta yayımlandı', html)

    def test_kopyasiz_sayfada_not_yok(self):
        item = sec(GOLE_ISKUR)[0]
        html = site_uret.detail_page(item, simdi=SIMDI)[1]
        self.assertNotIn('daha ayrıntılı kaydı', html)
        self.assertNotIn('d-kaynaklar', html)

    def test_kurum_sayfasi_kopya_cifti_tek_sayar(self):
        gruplar, slugler = ks.kurum_gruplari(self.ilanlar)
        kan, liste = next(iter(gruplar.items()))
        sayfa = ks.kurum_sayfasi(kan, liste, slugler[kan], {}, SIMDI, kopyalar=self.kopyalar)
        self.assertIn('<strong>1</strong><span>toplam kayıt</span>', sayfa)
        self.assertEqual(sayfa.count('class="ilan"'), 1)
        sayfa2 = ks.kurum_sayfasi(kan, liste, slugler[kan], {}, SIMDI)
        self.assertIn('<strong>3</strong><span>toplam kayıt</span>', sayfa2)
        meta = ks.kart_meta(self.ilanlar, None, self.kopyalar)
        self.assertEqual({m['kurum_sayisi'] for m in meta.values()}, {1})


class YerMetniTests(unittest.TestCase):
    def y(self, yer, **ek):
        return ks.yer_metni({'yer': yer, **ek})

    def test_il_ilce_tekrari(self):
        self.assertEqual(self.y('ANKARA • ANKARA / MERKEZ'), 'Ankara (Merkez)')
        self.assertEqual(self.y('Ankara', iller=['Ankara']), 'Ankara')
        self.assertEqual(self.y('ISPARTA / MERKEZ'), 'Isparta (Merkez)')
        self.assertEqual(self.y('ANKARA / ÇANKAYA', iller=['Ankara']), 'Ankara (Çankaya)')

    def test_birden_cok_ilce(self):
        self.assertEqual(self.y('BOLU / GEREDE • BOLU / MENGEN • BOLU / MERKEZ'), 'Bolu (Gerede, Mengen, Merkez)')

    def test_cok_il(self):
        self.assertEqual(self.y('BURSA -ESKİŞEHİR - BİLECİK'), 'Bursa, Eskişehir, Bilecik')
        self.assertEqual(self.y('KOCAELİ, SAKARYA, YALOVA, BOLU, DÜZCE'), 'Kocaeli, Sakarya +3')

    def test_il_olmayan_ad_korunur(self):
        self.assertEqual(self.y('BAKANLIK MERKEZ TEŞKİLATI'), 'Bakanlık Merkez Teşkilatı')
        self.assertEqual(self.y('BATI AKDENİZ KALKINMA AJANSI / ANTALYA, BURDUR, ISPARTA'), 'Batı Akdeniz Kalkınma Ajansı · Antalya, Burdur, Isparta')

    def test_yer_yoksa_iller_ya_da_yedek(self):
        self.assertEqual(ks.yer_metni({'iller': ['Muş']}), 'Muş')
        self.assertEqual(ks.yer_metni({}, 'Rize'), 'Rize')
        self.assertEqual(ks.yer_metni({}), '')

    def test_ayrinti_sayfasi_yer(self):
        item = sec(ELM_SBB)[0]
        item.update(yer='ANKARA • ANKARA / MERKEZ', iller=['Ankara'])
        html = site_uret.detail_page(item, simdi=SIMDI)[1]
        self.assertIn('<dd>Ankara (Merkez)</dd>', html)
        self.assertNotIn('Ankara • Ankara', html)
        self.assertNotIn('Ankara / Merkez', html)


if __name__ == '__main__':
    unittest.main()
