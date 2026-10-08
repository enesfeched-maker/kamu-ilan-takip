import test from 'node:test';
import assert from 'node:assert/strict';
import { topla, sayacSifirla, sayacOku, sayacAyarla, GUNLUK_YUMUSAK_SINIR } from '../src/toplama.js';
import { raporUret, canli } from '../src/rapor.js';
import { bakim } from '../src/bakim.js';
import { gunBasSn } from '../src/zaman.js';
import { sahteD1, istek, paket } from './sahte-d1.js';

const T0 = Date.parse('2026-10-08T09:00:00Z');
const env = (ek = {}) => ({ DB: sahteD1(), ...ek });
const gonder = (e, olaylar, ek = {}, rastgele = Math.random) => topla(istek(paket(olaylar, ek.paket), ek.istek), e, T0, rastgele);
const say = (e, t) => e.DB.ham.prepare('SELECT COUNT(*) AS n FROM olaylar WHERE t = ?').get(t).n;

test('şemada tek indeks var: idx_olaylar_ts', () => {
  const e = env();
  const idx = e.DB.ham.prepare("SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'olaylar' AND name NOT LIKE 'sqlite_%'").all().map((r) => r.name);
  assert.deepEqual(idx, ['idx_olaylar_ts']);
});

test('sıcak sorgular tam tarama yapmaz (EXPLAIN QUERY PLAN)', () => {
  const e = env();
  const plan = (sql, ...p) => e.DB.ham.prepare('EXPLAIN QUERY PLAN ' + sql).all(...p).map((r) => r.detail).join(' | ');
  assert.match(plan('SELECT COUNT(DISTINCT zv) FROM olaylar WHERE ts >= ?', 1), /USING (COVERING )?INDEX idx_olaylar_ts/);
  assert.match(plan("SELECT gun, COUNT(*) FROM olaylar WHERE t = 'sayfa' AND ts >= ? AND ts < ? AND gun NOT IN (SELECT gun FROM ozet_gun) GROUP BY gun", 1, 2), /idx_olaylar_ts/);
  assert.match(plan('SELECT 1 FROM olaylar WHERE ts >= ? AND ts < ? LIMIT 1', 1, 2), /idx_olaylar_ts/);
  assert.match(plan('DELETE FROM olaylar WHERE ts < ? AND gun IN (SELECT gun FROM ozet_gun)', 1), /idx_olaylar_ts/);
  assert.match(plan('SELECT MIN(ts) FROM olaylar'), /idx_olaylar_ts|SEARCH|MIN/);
  assert.doesNotMatch(plan('SELECT ts FROM olaylar ORDER BY id DESC LIMIT 50'), /TEMP B-TREE/); // birincil anahtar sırası, LIMIT ile erken durur
});

test('kaydırma: ekran başına tek olay (h=m) kümülatif sayılır; eski olay eşik başına', async () => {
  const e = env(); sayacSifirla();
  await gonder(e, [
    { t: 'sayfa', p: '/', f: 1 },
    { t: 'kaydirma', p: '/', n: 75, h: 'm' }, // 25, 50, 75 eşiklerine girer
  ]);
  await gonder(e, [{ t: 'kaydirma', p: '/', n: 50 }], { paket: { s: 'eskiOturum1234' } }); // eski istemci: yalnız 50
  const r = await raporUret(e, 'bugun', T0);
  const k = Object.fromEntries(r.kalite.kaydirma.map((x) => [x.n, x.say]));
  assert.deepEqual(k, { 25: 1, 50: 2, 75: 1, 100: 0 });
});

test('örnekleme: eşik aşılınca aktif/kaydirma %50 ve ağırlıklı (n2=2); diğer olaylar etkilenmez', async () => {
  const e = env(); sayacSifirla();
  const hep = () => 0.1; // her zaman tut
  const hic = () => 0.9; // her zaman at
  // Eşik altında hiçbir şey atılmaz
  await gonder(e, [{ t: 'aktif', p: '/', n: 60 }, { t: 'kaydirma', p: '/', n: 50, h: 'm' }], {}, hic);
  assert.equal(say(e, 'aktif'), 1);
  // Eşik üstü
  e.TOPLAMA_AZALT = '1';
  await gonder(e, [{ t: 'aktif', p: '/', n: 60 }, { t: 'kaydirma', p: '/', n: 50, h: 'm' }, { t: 'tikla', p: '/', a: 'x' }], { paket: { s: 'baskaOturum99' } }, hic);
  assert.equal(say(e, 'aktif'), 1, 'atıldı');
  assert.equal(say(e, 'tikla'), 1, 'tıklama hiç atılmaz');
  await gonder(e, [{ t: 'aktif', p: '/', n: 60 }], { paket: { s: 'baskaOturum99' } }, hep);
  const satir = e.DB.ham.prepare("SELECT n, n2 FROM olaylar WHERE t = 'aktif' ORDER BY id DESC LIMIT 1").get();
  assert.deepEqual({ ...satir }, { n: 60, n2: 2 });
  const r = await raporUret(e, 'bugun', T0);
  assert.equal(r.gunler.length, 1);
});

test('günlük yumuşak sınır: sayaç aşılınca örnekleme başlar, gün değişince sıfırlanır', async () => {
  const e = env(); sayacSifirla();
  await gonder(e, [{ t: 'sayfa', p: '/' }]);
  assert.equal(sayacOku().say, 1);
  assert.ok(GUNLUK_YUMUSAK_SINIR >= 10000);
  // sınır aşılmışken aktif olaylar %50 (burada: hepsi atılır), sayfa olayı etkilenmez
  sayacAyarla('2026-10-08', GUNLUK_YUMUSAK_SINIR + 1);
  await gonder(e, [{ t: 'sayfa', p: '/' }, { t: 'aktif', p: '/', n: 30 }, { t: 'kaydirma', p: '/', n: 25, h: 'm' }], {}, () => 0.9);
  assert.equal(say(e, 'aktif') + say(e, 'kaydirma'), 0);
  assert.equal(say(e, 'sayfa'), 2);
  assert.equal(sayacOku().gun, '2026-10-08');
  await topla(istek(paket([{ t: 'sayfa', p: '/' }])), e, T0 + 86400e3, () => 0.9);
  assert.equal(sayacOku().gun, '2026-10-09');
  assert.equal(sayacOku().say, 1);
});

test('ağırlıklı aktif süre panelde toplanır', async () => {
  const e = env(); sayacSifirla();
  e.DB.ham.prepare("INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t, p, sy, n, n2) VALUES (?, '2026-10-08', 12, 3, 'z', 'o1', 'aktif', '/', 'ana', 30, 2)").run(Math.floor(T0 / 1000));
  e.DB.ham.prepare("INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t, p, sy) VALUES (?, '2026-10-08', 12, 3, 'z', 'o1', 'sayfa', '/', 'ana')").run(Math.floor(T0 / 1000));
  const r = await raporUret(e, 'bugun', T0);
  assert.equal(r.kpi.etkinSaniyeOrt, 60);
});

test('bakım: özeti çıkmamış geçmiş günleri bulur, bugüne dokunmaz, eski ham olayı siler', async () => {
  const e = env();
  const ekle = (gun, ts) => e.DB.ham.prepare("INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t, p, sy) VALUES (?, ?, 1, 0, 'z', 'o', 'sayfa', '/', 'ana')").run(ts, gun);
  ekle('2026-10-05', gunBasSn('2026-10-05') + 100);
  ekle('2026-10-07', gunBasSn('2026-10-07') + 100);
  ekle('2026-10-08', gunBasSn('2026-10-08') + 100);
  const s = await bakim(e, T0);
  assert.deepEqual(s.ozetlenen, ['2026-10-05', '2026-10-07']);
  assert.deepEqual(await bakim(e, T0).then((x) => x.ozetlenen), []);
  const eski = '2026-01-01';
  ekle(eski, gunBasSn(eski) + 5);
  e.DB.ham.prepare("INSERT INTO ozet_gun (gun, ts) VALUES (?, 1)").run(eski);
  await bakim(e, T0);
  assert.equal(e.DB.ham.prepare("SELECT COUNT(*) AS n FROM olaylar WHERE gun = ?").get(eski).n, 0);
});

test('canlı gösterge son 5 dakikayı sayar', async () => {
  const e = env();
  const sn = Math.floor(T0 / 1000);
  const ekle = (zv, ts) => e.DB.ham.prepare("INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t, p) VALUES (?, '2026-10-08', 1, 0, ?, 'o', 'sayfa', '/')").run(ts, zv);
  ekle('a', sn - 10); ekle('b', sn - 200); ekle('c', sn - 400);
  assert.equal((await canli(e, T0)).aktif, 2);
});
