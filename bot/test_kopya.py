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
        self.assertIn('<strong>Ankara (Merkez)</strong>', html)
        self.assertNotIn('Ankara • Ankara', html)
        self.assertNotIn('Ankara / Merkez', html)


if __name__ == '__main__':
    unittest.main()
