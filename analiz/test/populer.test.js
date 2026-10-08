import test from 'node:test';
import assert from 'node:assert/strict';
import { populerIstegi, populerBellekSifirla } from '../src/populer.js';
import { sahteD1 } from './sahte-d1.js';
import { bakim } from '../src/bakim.js';
import { gunBasSn } from '../src/zaman.js';

const T0 = Date.parse('2026-10-08T09:00:00Z');
const SN = Math.floor(T0 / 1000);
let say = 0;
function ekle(db, o) {
  db.ham.prepare('INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t, p, sy, v, k, a, h) VALUES (?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    .run(o.ts ?? SN - 3600, '2026-10-08', 'zv' + say++, o.os, o.t, o.p ?? null, o.sy ?? null, o.v ?? null, o.k ?? null, o.a ?? null, o.h ?? null);
}
const goruntule = (db, os, key, ts) => ekle(db, { os, t: 'sayfa', p: '/ilan/' + key + '/', sy: 'ilan', k: key, ts });
const tikla = (db, os, a, h, ts) => ekle(db, { os, t: 'tikla', a, h, ts });
const iste = (env, ek = {}) => populerIstegi(new Request('https://api.kpsstercihi.com/populer', { headers: ek }), env, T0);

test('puan: benzersiz oturum görüntüleme + satır + 2x resmî + kaydet; manset_tikla sayılmaz', async () => {
  populerBellekSifirla();
  const db = sahteD1(); const env = { DB: db };
  goruntule(db, 's1', 'AAA'); goruntule(db, 's1', 'AAA'); goruntule(db, 's2', 'AAA'); // 2
  ekle(db, { os: 's3', t: 'sayfa', p: '/', sy: 'ana', v: 'ilan', k: 'AAA' }); // ana sayfa içi ayrıntı: 3
  tikla(db, 's1', 'satir_tikla', 'AAA'); tikla(db, 's1', 'satir_tikla', 'AAA'); // +1
  tikla(db, 's1', 'resmi_ilan', 'AAA'); // +2
  tikla(db, 's2', 'kaydet', 'AAA'); // +1  => 3+1+2+1 = 7
  for (let i = 0; i < 20; i++) tikla(db, 'm' + i, 'manset_tikla', 'BBB');
  tikla(db, 's1', 'satir_tikla', 'BBB'); // BBB = 1
  const r = await iste(env, { Origin: 'https://kpsstercihi.com' });
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.deepEqual(j.ilanlar, { AAA: 7, BBB: 1 });
  assert.equal(j.gun, 7);
  assert.equal(j.guncelleme, new Date(T0).toISOString());
  assert.deepEqual(Object.keys(j).sort(), ['guncelleme', 'gun', 'ilanlar'].sort());
  assert.equal(r.headers.get('Cache-Control'), 'public, max-age=600');
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
});

test('son 7 günden eski olaylar, geçersiz anahtarlar ve yabancı köken', async () => {
  populerBellekSifirla();
  const db = sahteD1(); const env = { DB: db };
  tikla(db, 's1', 'resmi_ilan', 'ESKI', SN - 8 * 86400);
  tikla(db, 's1', 'resmi_ilan', '../kotu');
  tikla(db, 's1', 'resmi_ilan', 'YENI');
  const r = await iste(env, { Origin: 'https://evil.example' });
  assert.deepEqual((await r.json()).ilanlar, { YENI: 2 });
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), null);
  assert.equal((await iste(env, { Origin: 'https://www.kpsstercihi.com' })).headers.get('Access-Control-Allow-Origin'), 'https://www.kpsstercihi.com');
});

test('en çok 100 ilan ve sunucu önbelleği 30 dk', async () => {
  populerBellekSifirla();
  const db = sahteD1(); const env = { DB: db };
  for (let i = 0; i < 120; i++) tikla(db, 's' + i, 'kaydet', 'K' + String(i).padStart(3, '0'));
  const j = await (await iste(env)).json();
  assert.equal(Object.keys(j.ilanlar).length, 100);
  const once = db.sayac.sorgu;
  await iste(env);
  assert.equal(db.sayac.sorgu, once, 'ikinci istek veritabanına gitmez');
  const r = await populerIstegi(new Request('https://api.kpsstercihi.com/populer'), env, T0 + 1801_000);
  assert.equal(r.status, 200);
  assert.ok(db.sayac.sorgu > once, '30 dk sonra yenilenir');
});

test('OPTIONS 204, POST 405', async () => {
  populerBellekSifirla();
  const env = { DB: sahteD1() };
  assert.equal((await populerIstegi(new Request('https://x/populer', { method: 'OPTIONS', headers: { Origin: 'https://kpsstercihi.com' } }), env, T0)).status, 204);
  assert.equal((await populerIstegi(new Request('https://x/populer', { method: 'POST', body: '{}' }), env, T0)).status, 405);
});

test('geçmiş günler gün özetinden gelir (ham tabloya gerek yok); bugün artımlı, çift sayım yok', async () => {
  populerBellekSifirla();
  const db = sahteD1(); const env = { DB: db };
  const dun = gunBasSn('2026-10-07') + 3600;
  ekle(db, { os: 'a', t: 'sayfa', p: '/ilan/DUN/', sy: 'ilan', k: 'DUN', ts: dun });
  ekle(db, { os: 'b', t: 'sayfa', p: '/ilan/DUN/', sy: 'ilan', k: 'DUN', ts: dun });
  ekle(db, { os: 'a', t: 'tikla', a: 'resmi_ilan', h: 'DUN', ts: dun });
  ekle(db, { os: 'a', t: 'tikla', a: 'manset_tikla', h: 'DUN', ts: dun });
  await bakim({ DB: db }, T0); // dünü özetler
  db.ham.prepare('DELETE FROM olaylar').run(); // ham veri gitse de dünkü puan özetten gelir
  goruntule(db, 's1', 'BUGUN');
  const j = await (await iste(env)).json();
  assert.deepEqual(j.ilanlar, { DUN: 4, BUGUN: 1 });
  // 31 dk sonra: aynı bugünkü olay yeniden okunsa da iki kez sayılmaz; yeni olay eklenir
  goruntule(db, 's2', 'BUGUN', SN + 60);
  const r = await populerIstegi(new Request('https://api.kpsstercihi.com/populer'), env, T0 + 1801_000);
  assert.deepEqual((await r.json()).ilanlar, { DUN: 4, BUGUN: 2 });
});
