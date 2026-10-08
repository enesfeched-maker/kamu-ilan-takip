import test from 'node:test';
import assert from 'node:assert/strict';
import { topla, hizSifirla, HIZ_SINIR } from '../src/toplama.js';
import { sahteD1, istek, paket } from './sahte-d1.js';

const T0 = Date.parse('2026-10-08T09:00:00Z'); // Türkiye 12:00
const env = () => ({ DB: sahteD1(), IZINLI_KOKENLER: 'https://kpsstercihi.com,https://www.kpsstercihi.com' });
const sayfa = (o = {}) => ({ t: 'sayfa', p: '/', v: 'bugun', f: 1, ...o });
const satirlar = (e) => e.DB.ham.prepare('SELECT * FROM olaylar ORDER BY id').all();

test.beforeEach(() => hizSifirla());

test('olay kaydedilir; tek batch, 204 ve CORS', async () => {
  const e = env();
  const r = await topla(istek(paket([sayfa(), { t: 'tikla', p: '/', a: 'arama', x: 'zabıta', n: 0 }])), e, T0);
  assert.equal(r.status, 204);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.equal(e.DB.sayac.batch, 1);
  const s = satirlar(e);
  assert.equal(s.length, 2);
  assert.equal(s[0].gun, '2026-10-08');
  assert.equal(s[0].saat, 12);
  assert.equal(s[0].hg, 3); // Perşembe
  assert.equal(s[0].ilk, 1);
  assert.equal(s[0].yeni, 1);
  assert.equal(s[0].kaynak, 'Google');
  assert.equal(s[0].sehir, 'Ankara');
  assert.equal(s[0].cihaz, 'masaüstü');
  assert.equal(s[0].gen, '<480');
  // oturum özellikleri yalnız ilk sayfa olayında
  assert.equal(s[1].sehir, null);
  assert.equal(s[1].kaynak, null);
});

test('www kökeni de kabul edilir, yabancı köken 403', async () => {
  const e = env();
  assert.equal((await topla(istek(paket([sayfa()]), { origin: 'https://www.kpsstercihi.com' }), e, T0)).status, 204);
  const r = await topla(istek(paket([sayfa()]), { origin: 'https://evil.example' }), e, T0);
  assert.equal(r.status, 403);
  assert.equal((await topla(istek(paket([sayfa()]), { origin: null }), e, T0)).status, 403);
  assert.equal(satirlar(e).length, 1);
});

test('OPTIONS ve yanlış yöntem', async () => {
  const e = env();
  const o = await topla(istek('', { yontem: 'OPTIONS' }), e, T0);
  assert.equal(o.status, 204);
  assert.equal(o.headers.get('Access-Control-Allow-Methods'), 'POST, OPTIONS');
  assert.equal((await topla(istek('', { yontem: 'GET' }), e, T0)).status, 405);
});

test('botlar, DNT ve GPC ölçülmez', async () => {
  const e = env();
  await topla(istek(paket([sayfa()]), { ua: 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' }), e, T0);
  await topla(istek(paket([sayfa()]), { basliklar: { DNT: '1' } }), e, T0);
  await topla(istek(paket([sayfa()]), { basliklar: { 'Sec-GPC': '1' } }), e, T0);
  assert.equal(satirlar(e).length, 0);
  assert.equal(e.DB.ham.prepare('SELECT COUNT(*) n FROM tuz').get().n, 0, 'ölçülmeyen istek için tuz bile üretilmez');
  await topla(istek(paket([sayfa()]), { basliklar: { DNT: '0' } }), e, T0);
  assert.equal(satirlar(e).length, 1);
});

test('geçersiz paketler: 400 / 413', async () => {
  const e = env();
  assert.equal((await topla(istek('{bozuk'), e, T0)).status, 400);
  assert.equal((await topla(istek(paket([])), e, T0)).status, 400);
  assert.equal((await topla(istek('x'.repeat(9000)), e, T0)).status, 413);
  assert.equal((await topla(istek(paket([{ t: 'x', p: '/' }])), e, T0)).status, 204);
  assert.equal(satirlar(e).length, 0);
});

test('IP ve tam User-Agent hiçbir sütunda saklanmaz', async () => {
  const e = env();
  const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
  await topla(istek(paket([sayfa(), { t: 'aktif', p: '/', n: 15 }]), { ip: '198.51.100.23', ua }), e, T0);
  const dok = JSON.stringify(satirlar(e)) + JSON.stringify(e.DB.ham.prepare('SELECT * FROM tuz').all());
  assert.ok(!dok.includes('198.51.100.23'));
  assert.ok(!dok.includes('537.36'));
  assert.ok(!dok.includes('Mozilla'));
  const zv = satirlar(e)[0].zv;
  assert.match(zv, /^[0-9a-f]{16}$/);
});

test('ziyaretçi özeti: aynı gün aynı kişi aynı; ertesi gün farklı; tuz günlük', async () => {
  const e = env();
  const gonder = (ms, ip = '198.51.100.23') => topla(istek(paket([sayfa()]), { ip }), e, ms);
  await gonder(T0);
  await gonder(T0 + 3600e3);
  await gonder(T0, '198.51.100.99');
  await gonder(T0 + 86400e3);
  const zv = satirlar(e).map((s) => s.zv);
  assert.equal(zv[0], zv[1]);
  assert.notEqual(zv[0], zv[2]);
  assert.notEqual(zv[0], zv[3]);
  assert.equal(e.DB.ham.prepare('SELECT COUNT(*) n FROM tuz').get().n, 2);
});

test('hız sınırı: ziyaretçi başına 10 dakikada en çok 300 olay', async () => {
  const e = env();
  let son = 0;
  for (let i = 0; i < HIZ_SINIR / 20; i++) son = (await topla(istek(paket(Array.from({ length: 20 }, () => ({ t: 'aktif', p: '/', n: 5 })))), e, T0)).status;
  assert.equal(son, 204);
  assert.equal((await topla(istek(paket([{ t: 'aktif', p: '/', n: 5 }])), e, T0 + 1000)).status, 429);
  assert.equal(satirlar(e).length, HIZ_SINIR);
  // başka ziyaretçi etkilenmez, pencere geçince açılır
  assert.equal((await topla(istek(paket([sayfa()]), { ip: '192.0.2.5' }), e, T0)).status, 204);
  assert.equal((await topla(istek(paket([sayfa()])), e, T0 + 601e3)).status, 204);
});

test('geri dönen bayrağı ve utm', async () => {
  const e = env();
  await topla(istek(paket([sayfa()], { r: 1, ref: '', u: { s: 'Telegram', m: 'Kanal', c: 'Ekim Bülten' } })), e, T0);
  const s = satirlar(e)[0];
  assert.equal(s.yeni, 0);
  assert.equal(s.kaynak, 'Telegram');
  assert.deepEqual([s.us, s.um, s.uc], ['telegram', 'kanal', 'ekim bülten']);
});

test('TOPLAMA_KAPALI=1 hiçbir şey yazmaz', async () => {
  const e = { ...env(), TOPLAMA_KAPALI: '1' };
  assert.equal((await topla(istek(paket([sayfa()])), e, T0)).status, 204);
  assert.equal(satirlar(e).length, 0);
});
