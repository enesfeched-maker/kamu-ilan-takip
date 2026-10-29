// Liderlik tablosu: sunucu neti kendisi hesaplar, hileli/uygunsuz gönderimleri reddeder, hafta başına en iyi neti tutar.
import test from 'node:test';
import assert from 'node:assert/strict';
import { sahteD1, istek } from './sahte-d1.js';
import { liderlikIstegi, liderlikHizSifirla, adDogrula, haftaBasi } from '../src/liderlik.js';
import { RESMI_METINLER, puanla, zincir } from '../src/katip-metin.js';
import { bellekSifirla } from '../src/onbellek.js';

const SIMDI = Date.parse('2026-10-29T15:00:00+03:00'); // Perşembe
const env = (db) => ({ DB: db, IZINLI_KOKENLER: 'https://kpsstercihi.com' });
const URL_ = 'https://api.kpsstercihi.com/liderlik';
const ANAHTAR = 'a'.repeat(32);

// İlk n kelimeyi doğru, sonra her 10 kelimede bir hatalı yazar.
function yazi(no, n, hataAraligi = 0) {
  return zincir(RESMI_METINLER, no, 180).split(' ').slice(0, n).map((w, i) => (hataAraligi && i % hataAraligi === 5 ? w + 'x' : w)).join(' ');
}
const gonder = (db, govde, ek = {}, ms = SIMDI) => liderlikIstegi(istek(govde, { url: URL_, ...ek }), env(db), ms);
const govde = (ek = {}) => {
  const y = ek.yazi || yazi(0, 120);
  return { ad: 'Ayşe K.', anahtar: ANAHTAR, mod: 'sinav', kut: 'zk2025', no: 0, yazi: y, vurus: y.length + 12, ...ek };
};

test.beforeEach(() => { liderlikHizSifirla(); bellekSifirla(); });

test('metinler ve puanlama sitenin dosyalarından yüklenir', () => {
  assert.equal(RESMI_METINLER.length, 30);
  assert.equal(typeof puanla, 'function');
});

test('geçerli sonuç eklenir; net sunucuda hesaplanır, tabloda görünür', async () => {
  const db = sahteD1();
  const g = govde({ yazi: yazi(3, 110, 10), no: 3, net: 999 });
  g.vurus = g.yazi.length;
  const r = await gonder(db, g);
  assert.equal(r.status, 200);
  const j = await r.json();
  const beklenen = puanla(zincir(RESMI_METINLER, 3, 180), g.yazi, { sure: 180, saniye: 180 }).net;
  assert.equal(j.net, beklenen);
  assert.ok(j.net < 110 && j.net > 90);
  assert.equal(j.sira, 1);
  assert.equal(j.tablo.haftalik[0].ad, 'Ayşe K.');
  assert.equal(j.tablo.haftalik[0].net, beklenen);
  assert.equal(j.tablo.hafta, '2026-10-26');
  const t = await (await liderlikIstegi(istek(null, { url: URL_, yontem: 'GET' }), env(db), SIMDI)).json();
  assert.equal(t.haftalik.length, 1);
  assert.equal(t.tum[0].net, beklenen);
});

test('aynı kişi: hafta içinde en iyi net kalır, takma ad güncellenir', async () => {
  const db = sahteD1();
  await gonder(db, govde({ yazi: yazi(0, 130) }));
  const r = await gonder(db, govde({ ad: 'Ayşe Kaya', yazi: yazi(0, 80) }));
  const j = await r.json();
  assert.equal(j.tablo.haftalik.length, 1);
  assert.equal(j.tablo.haftalik[0].net, 130);
  assert.equal(j.tablo.haftalik[0].ad, 'Ayşe Kaya');
});

test('yeni hafta boş başlar, tüm zamanlar kişi başına en iyi neti tutar', async () => {
  const db = sahteD1();
  await gonder(db, govde({ yazi: yazi(0, 130) }));
  const sonraki = SIMDI + 5 * 86400000; // sonraki salı
  bellekSifirla();
  const j = await (await gonder(db, govde({ yazi: yazi(0, 100) }), {}, sonraki)).json();
  assert.equal(j.tablo.hafta, '2026-11-02');
  assert.equal(j.tablo.haftalik[0].net, 100);
  assert.equal(j.tablo.tum.length, 1);
  assert.equal(j.tablo.tum[0].net, 130);
});

test('sıralama net büyükten küçüğe', async () => {
  const db = sahteD1();
  await gonder(db, govde({ ad: 'Birinci', anahtar: 'b'.repeat(32), yazi: yazi(0, 140) }));
  const j = await (await gonder(db, govde({ ad: 'İkinci', anahtar: 'c'.repeat(32), yazi: yazi(0, 100) }))).json();
  assert.deepEqual(j.tablo.haftalik.map((x) => x.ad), ['Birinci', 'İkinci']);
  assert.equal(j.sira, 2);
});

test('hileli gönderimler reddedilir', async () => {
  const db = sahteD1();
  const durum = async (g) => { const r = await gonder(db, g); return [r.status, (await r.json()).hata]; };
  const y = yazi(0, 120);
  assert.deepEqual(await durum(govde({ yazi: y, vurus: 20 })), [400, 'supheli']);               // yapıştırma: vuruş yok
  const hepsi = yazi(0, 420);
  assert.deepEqual(await durum(govde({ yazi: hepsi, vurus: hepsi.length })), [400, 'supheli']);  // insanüstü hız
  assert.deepEqual(await durum(govde({ no: 30 })), [400, 'metin']);
  assert.deepEqual(await durum(govde({ kut: 'ozgun' })), [400, 'metin']);
  assert.deepEqual(await durum(govde({ mod: 'antrenman' })), [400, 'mod']);
  assert.deepEqual(await durum(govde({ yazi: 'suç toplumda' })), [400, 'kisa']);
  assert.deepEqual(await durum(govde({ anahtar: 'xyz' })), [400, 'bicim']);
  assert.deepEqual(await durum(govde({ ad: 'orospu çocuğu' })), [400, 'ad']);
  const kayit = await (await liderlikIstegi(istek(null, { url: URL_, yontem: 'GET' }), env(db), SIMDI)).json();
  assert.equal(kayit.haftalik.length, 0);
});

test('başka siteden gönderim ve aşırı sık gönderim engellenir', async () => {
  const db = sahteD1();
  assert.equal((await gonder(db, govde(), { origin: 'https://kotu.example' })).status, 403);
  for (let i = 0; i < 10; i++) assert.equal((await gonder(db, govde())).status, 200);
  assert.equal((await gonder(db, govde())).status, 429);
});

test('takma ad kuralları', () => {
  assert.equal(adDogrula('  Ayşe   K. '), 'Ayşe K.');
  assert.equal(adDogrula('Işık_93'), 'Işık_93');
  assert.equal(adDogrula('Koçak'), 'Koçak');
  assert.equal(adDogrula('Hakan Sıkı'), 'Hakan Sıkı');
  for (const kotu of ['a', '12345', 'x'.repeat(19), '<script>', 'Oç', 'aq amk', 'KPSS Tercihi', 'Admin', 'S.i.k.t.i.r', 'Yavşak']) {
    assert.equal(adDogrula(kotu), null, kotu);
  }
});

test('hafta Türkiye saatine göre pazartesi başlar', () => {
  assert.equal(haftaBasi(Date.parse('2026-11-01T23:30:00+03:00')), '2026-10-26'); // pazar gecesi
  assert.equal(haftaBasi(Date.parse('2026-11-02T00:10:00+03:00')), '2026-11-02'); // pazartesi
});
