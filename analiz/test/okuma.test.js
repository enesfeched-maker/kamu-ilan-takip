// D1 okuma kotası (29 Ekim 2026'da hesap kotası doldu): panel raporu ham tabloyu yalnız özeti çıkmamış günlerde tarar,
// ağır isteklerin okuması bütçe tablosuna hemen yazılır.
import test from 'node:test';
import assert from 'node:assert/strict';
import { sahteD1 } from './sahte-d1.js';
import { aralikOku, gunOzetiYaz, ozetsizDilimler } from '../src/sorgu.js';
import { butceSarmala, butceSifirla, butceBekliyor, butceYaz, butceSaatAyarla } from '../src/butce.js';
import { gunBasSn } from '../src/zaman.js';

test('özetsiz günler art arda dilimlere ayrılır', () => {
  const ozetli = new Set(['2026-10-02', '2026-10-03', '2026-10-05']);
  assert.deepEqual(ozetsizDilimler('2026-10-01', '2026-10-06', ozetli), [['2026-10-01', '2026-10-01'], ['2026-10-04', '2026-10-04'], ['2026-10-06', '2026-10-06']]);
  assert.deepEqual(ozetsizDilimler('2026-10-02', '2026-10-03', ozetli), []);
});

// Bağlanan parametreleri kaydeden ince sarmalayıcı.
function kayitli(db) {
  const deyimler = [];
  const sar = (st, sql) => ({ ...st, bind(...a) { deyimler.push({ sql, a }); st.bind(...a); return sar(st, sql); }, _calistir: () => st._calistir(), all: () => st.all(), first: () => st.first(), run: () => st.run() });
  return { deyimler, ham: db.ham, prepare: (sql) => sar(db.prepare(sql), sql), batch: (l) => db.batch(l) };
}

function olay(db, gun, os, p) {
  const ts = gunBasSn(gun) + 3600;
  db.ham.prepare('INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t, p, ilk) VALUES (?, ?, 1, 0, ?, ?, ?, ?, 1)').run(ts, gun, 'z' + os, os, 'sayfa', p);
}

test('panel raporu özeti çıkmış günlerin ham satırlarını taramaz, sonuç aynı kalır', async () => {
  const db = sahteD1();
  for (const g of ['2026-10-20', '2026-10-21', '2026-10-22']) { olay(db, g, 'a' + g, '/'); olay(db, g, 'b' + g, '/katiplik/'); }
  await gunOzetiYaz(db, '2026-10-20', 1);
  await gunOzetiYaz(db, '2026-10-21', 1);
  const k = kayitli(db);
  const rows = await aralikOku(k, '2026-09-23', '2026-10-22');
  const ham = k.deyimler.filter((d) => d.sql.includes('WITH s AS MATERIALIZED'));
  assert.ok(ham.length > 0);
  for (const d of ham) {
    // Dilimler: ölçüm öncesi boş günler (2026-09-23..10-19) ve bugün (10-22); özetli 20-21 Ekim aralık dışında.
    assert.deepEqual(d.a, [gunBasSn('2026-09-23'), gunBasSn('2026-10-19') + 86400, gunBasSn('2026-10-22'), gunBasSn('2026-10-22') + 86400]);
  }
  const genel = rows.filter((r) => r.boyut === 'genel');
  const toplam = (g) => genel.filter((r) => r.gun === g).reduce((t, r) => t + r.say, 0);
  assert.ok(toplam('2026-10-20') > 0 && toplam('2026-10-22') > 0);
  assert.equal(toplam('2026-10-20'), toplam('2026-10-22'));
});

test('tüm günler özetliyse ham tablo hiç okunmaz', async () => {
  const db = sahteD1();
  olay(db, '2026-10-20', 'a', '/');
  await gunOzetiYaz(db, '2026-10-20', 1);
  const k = kayitli(db);
  await aralikOku(k, '2026-10-20', '2026-10-20');
  assert.equal(k.deyimler.filter((d) => d.sql.includes('FROM olaylar')).length, 0);
});

test('ağır okuma bütçe tablosuna beklemeden yazılır', async () => {
  butceSifirla();
  const simdi = Date.parse('2026-10-29T18:00:00Z');
  butceSaatAyarla(() => simdi);
  try {
    const db = sahteD1();
    db.ham.exec("WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 25000) INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t) SELECT i, '2026-10-29', 0, 0, 'z', 'o', 'aktif' FROM n");
    const env = butceSarmala({ DB: db });
    assert.equal(butceBekliyor(), false);
    await env.DB.prepare('SELECT ts FROM olaylar').all();
    assert.equal(butceBekliyor(), true);
    await butceYaz(env, simdi);
    const r = db.ham.prepare('SELECT okuma FROM butce WHERE gun_utc = ?').get('2026-10-29');
    assert.ok(r.okuma >= 25000, String(r.okuma));
    assert.equal(butceBekliyor(), false);
  } finally { butceSaatAyarla(null); butceSifirla(); }
});
