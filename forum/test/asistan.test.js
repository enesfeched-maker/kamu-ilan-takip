import test from 'node:test';
import assert from 'node:assert/strict';
import { asistanYaniti, puanTurleri } from '../src/asistan.js';
import { ilanBul, ilanKayitlari, ilanOnbellekTemizle } from '../src/ilan.js';
import { ORNEK_ILAN, UUID, ilanSiteFetch } from './yardim.js';

const BAS = 'İlan belgesine göre:';
const SON = 'Kesin bilgi için resmî ilan belgesine bak.';

test('çerçeve: başlangıç, bitiş, uzunluk', () => {
  const y = asistanYaniti('Son gün ne zaman?', ORNEK_ILAN);
  assert.ok(y.startsWith(BAS) && y.endsWith(SON));
  assert.ok(y.length <= 520);
});

test('son gün', () => {
  assert.match(asistanYaniti('Başvurular ne zamana kadar?', ORNEK_ILAN), /25 Eylül 2026, saat 17:00/);
  assert.match(asistanYaniti('SON GÜN NE', ORNEK_ILAN), /25 Eylül 2026/);
  assert.match(asistanYaniti('bitiş tarihi nedir', { son_tarih: '2026-10-02' }), /2 Ekim 2026\./);
  assert.equal(asistanYaniti('son gün ne zaman', { baslik: 'x' }), null);
});

test('öğrenim', () => {
  assert.match(asistanYaniti('Lise mezunu başvurabilir mi?', ORNEK_ILAN), /Aranan öğrenim düzeyi: lisans\./);
  assert.match(asistanYaniti('hangi bölüm', { ogrenim: ['onlisans', 'ortaogretim'], bolumler: ['Bilgisayar', 'Elektronik'] }), /ön lisans, lise \(ortaöğretim\)\. Bölümler: Bilgisayar, Elektronik\./);
  assert.equal(asistanYaniti('lisans mı', { ogrenim: [] }), null);
});

test('puan', () => {
  const y = asistanYaniti('KPSS kaç puan lazım, taban nedir?', ORNEK_ILAN);
  assert.match(y, /P3/);
  assert.match(y, /Geçmiş taban puanları ilan sayfasında/);
  assert.deepEqual(puanTurleri({ metin: 'kpss p93 ve p94 ile p3' }).sort(), ['P3', 'P93', 'P94']);
  assert.deepEqual(puanTurleri({ metin: 'ürün p999 ve map3' }), []);
  assert.equal(asistanYaniti('puan kaç', { metin: 'puan türü belirtilmedi' }), null);
});

test('kadro sayısı', () => {
  assert.match(asistanYaniti('Kaç kişi alınacak?', ORNEK_ILAN), /kadro sayısı: 9\./);
  assert.match(asistanYaniti('kontenjan', { metin: 'toplam 120 kişi alınacaktır' }), /120/);
  assert.equal(asistanYaniti('kaç kişi', { metin: 'bilgi yok' }), null);
});

test('nereden başvurulur', () => {
  const y = asistanYaniti('Nereden başvuru yapılıyor?', ORNEK_ILAN);
  assert.match(y, new RegExp(`Başvuru bağlantısı ilan sayfasında: https://kpsstercihi.com/ilan/${UUID}/`));
  assert.equal(asistanYaniti('nasıl başvurulur', { metin: 'x' }), null);
});

test('yaş', () => {
  assert.match(asistanYaniti('Yaş sınırı var mı?', ORNEK_ILAN), /35 yaş/);
  assert.equal(asistanYaniti('yaş sınırı', { metin: 'yaş şartı yoktur' }), null);
  assert.equal(asistanYaniti('hayat ve yaşam', ORNEK_ILAN), null);
});

test('alakasız soru ya da veri yok -> null (uydurma yok)', () => {
  assert.equal(asistanYaniti('Bu kurumda çalışmak nasıl?', ORNEK_ILAN), null);
  assert.equal(asistanYaniti('merhaba', ORNEK_ILAN), null);
  assert.equal(asistanYaniti('son gün', null), null);
  assert.equal(asistanYaniti(undefined, ORNEK_ILAN), null);
});

test('birden çok niyet birleşir ve 400 karakteri aşmaz', () => {
  const y = asistanYaniti('Son gün ne, kaç kişi alınacak, yaş sınırı?', ORNEK_ILAN);
  assert.match(y, /25 Eylül/); assert.match(y, /9\./); assert.match(y, /35 yaş/);
  const uzun = { ...ORNEK_ILAN, sayfa: 'https://kpsstercihi.com/ilan/' + 'a'.repeat(300) + '/' };
  const u = asistanYaniti('son gün ne, kaç kişi, nereden başvuru, puan, yaş', uzun);
  assert.ok(u === null || u.length <= 520);
});

test('ilanBul: id, kimlikler, sayfa anahtarı', async () => {
  const kayitlar = [ORNEK_ILAN, { id: 'sbb-' + 'a'.repeat(24), kimlikler: ['sbb-' + 'a'.repeat(24), 'iskur-' + 'b'.repeat(24)], sayfa: 'https://kpsstercihi.com/ilan/sbb-' + 'a'.repeat(24) + '/' }];
  assert.equal(ilanBul(kayitlar, UUID), ORNEK_ILAN);
  assert.equal(ilanBul(kayitlar, ORNEK_ILAN.id), ORNEK_ILAN);
  assert.equal(ilanBul(kayitlar, 'iskur-' + 'b'.repeat(24)), kayitlar[1]);
  assert.equal(ilanBul(kayitlar, 'sbb-' + 'a'.repeat(24)), kayitlar[1]);
  assert.equal(ilanBul(kayitlar, 'csb-12345'), null);
  assert.equal(ilanBul(kayitlar, ''), null);
});

test('ilanKayitlari: bellekte tutulur, hata olursa boş', async () => {
  ilanOnbellekTemizle();
  const f = ilanSiteFetch();
  try {
    const env = { SITE_URL: 'https://kpsstercihi.com/' };
    assert.equal((await ilanKayitlari(env)).length, 1);
    await ilanKayitlari(env);
    assert.equal(f.cagrilar.length, 1);
  } finally { f.geri(); }
  ilanOnbellekTemizle();
  const h = (await import('./yardim.js')).sahteFetch(async () => { throw new Error('ağ'); });
  try { assert.deepEqual(await ilanKayitlari({ SITE_URL: 'https://x.test/' }), []); } finally { h.geri(); ilanOnbellekTemizle(); }
});
