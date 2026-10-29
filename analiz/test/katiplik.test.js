// Katiplik bölümü: yeni metrikler gerçek SQLite'ta çalışır, rapor özeti doğru toplanır.
import test from 'node:test';
import assert from 'node:assert/strict';
import { sahteD1 } from './sahte-d1.js';
import { aralikOku, gunOzetiYaz } from '../src/sorgu.js';
import { katiplikOzeti } from '../src/rapor.js';

const GUN = '2026-11-02';
const TS = Date.parse(GUN + 'T09:00:00+03:00') / 1000;
function ekle(db, o) {
  const s = { ts: TS, gun: GUN, saat: 9, hg: 0, zv: o.zv || 'z1', os: o.os || 'o1', ilk: 0, ...o };
  const alan = Object.keys(s);
  db.ham.prepare(`INSERT INTO olaylar (${alan.join(',')}) VALUES (${alan.map(() => '?').join(',')})`).run(...alan.map((a) => s[a] ?? null));
}

function veri(db) {
  ekle(db, { os: 'a', zv: 'z1', t: 'sayfa', p: '/katiplik/sinav-metinleri/metin-3/', ilk: 1, kaynak: 'Google' });
  ekle(db, { os: 'a', zv: 'z1', t: 'sayfa', p: '/katiplik/' });
  ekle(db, { os: 'a', zv: 'z1', t: 'aktif', p: '/katiplik/', n: 240 });
  ekle(db, { os: 'a', zv: 'z1', t: 'tikla', p: '/katiplik/', a: 'katip-basla', x: 'sinav-zk2025' });
  ekle(db, { os: 'a', zv: 'z1', t: 'tikla', p: '/katiplik/', a: 'katip-bitti', x: 'sinav-basarili', n: 96 });
  ekle(db, { os: 'b', zv: 'z2', t: 'sayfa', p: '/katiplik/dersler/', ilk: 1, kaynak: 'Doğrudan' });
  ekle(db, { os: 'b', zv: 'z2', t: 'aktif', p: '/katiplik/dersler/', n: 120 });
  ekle(db, { os: 'b', zv: 'z2', t: 'tikla', p: '/katiplik/', a: 'katip-basla', x: 'gunluk' });
  ekle(db, { os: 'b', zv: 'z2', t: 'tikla', p: '/katiplik/', a: 'katip-bitti', x: 'gunluk-basarisiz', n: 41 });
  ekle(db, { os: 'b', zv: 'z2', t: 'tikla', p: '/katiplik/dersler/', a: 'katip-ders-bitti', x: 'Q-1', n: 3 });
  ekle(db, { os: 'b', zv: 'z2', t: 'tikla', p: '/katiplik/', a: 'katiplik', x: 'paylas' });
  ekle(db, { os: 'c', zv: 'z3', t: 'sayfa', p: '/', ilk: 1 });
  ekle(db, { os: 'c', zv: 'z3', t: 'aktif', p: '/', n: 50 });
}

function kontrol(K) {
  assert.equal(K.kpi.goruntu, 3);
  assert.equal(K.kpi.sureSn, 360);
  assert.equal(K.kpi.girisOturum, 2);
  assert.equal(K.kpi.basla, 2);
  assert.equal(K.kpi.bitti, 2);
  assert.equal(K.kpi.bitenSinav, 2);
  assert.equal(K.kpi.basariOran, 0.5);
  assert.equal(K.kpi.ortNet, 69);
  assert.equal(K.kpi.paylasim, 1);
  assert.deepEqual(K.netDagilim.map((r) => r.say), [0, 1, 0, 1, 0]);
  assert.deepEqual(K.kaynak.map((r) => r.ad).sort(), ['Doğrudan', 'Google']);
  assert.equal(K.girisSayfasi.find((r) => r.ad === '/katiplik/sinav-metinleri/metin-3/').say, 1);
  assert.equal(K.dersler[0].ad, 'Q-1');
  assert.equal(K.dersler[0].ort, 3);
  assert.equal(K.sayfalar.find((r) => r.p === '/katiplik/').ortSn, 240);
}

test('katiplik özeti ham olaylardan doğru hesaplanır', async () => {
  const db = sahteD1();
  veri(db);
  const rows = await aralikOku(db, GUN, GUN);
  kontrol(katiplikOzeti(rows));
});

test('katiplik özeti gün özeti yazıldıktan sonra da aynı', async () => {
  const db = sahteD1();
  veri(db);
  await gunOzetiYaz(db, GUN, TS + 86400);
  const rows = await aralikOku(db, GUN, GUN);
  kontrol(katiplikOzeti(rows));
});
