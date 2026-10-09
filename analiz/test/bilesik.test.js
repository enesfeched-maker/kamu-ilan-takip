// D1 tek deyimde en çok 5 bileşik SELECT terimine izin verir; panel/özet sorguları bu sınırı aşmamalı.
import test from 'node:test';
import assert from 'node:assert/strict';
import { aralikOku, gunOzetiYaz, D1_BILESIK_SINIRI } from '../src/sorgu.js';

function sahteDb() {
  const sqller = [];
  const deyim = (sql) => ({
    sql,
    bind() { return this; },
    async all() { return { results: [], meta: {} }; },
    async first() { return null; },
    async run() { return { meta: {} }; },
  });
  return {
    sqller,
    prepare(sql) { sqller.push(sql); return deyim(sql); },
    async batch(liste) { return liste.map(() => ({ results: [], meta: {} })); },
  };
}

// Parantez içindeki alt sorgular ayrı bileşik deyimdir; en dış düzeydeki UNION ALL sayısı ölçülür.
function disTerim(sql) {
  let derinlik = 0, say = 1;
  const parca = sql.split(/(\(|\)|\bUNION\s+ALL\b)/i);
  for (const p of parca) {
    if (p === '(') derinlik++;
    else if (p === ')') derinlik--;
    else if (/^UNION\s+ALL$/i.test(p) && derinlik === 0) say++;
  }
  return say;
}

test('panel ve gün özeti sorguları D1 bileşik terim sınırını aşmaz', async () => {
  for (const calistir of [(db) => aralikOku(db, '2026-10-01', '2026-10-09'), (db) => gunOzetiYaz(db, '2026-10-08', 1)]) {
    const db = sahteDb();
    await calistir(db);
    const bilesik = db.sqller.filter((s) => s.includes('WITH s AS MATERIALIZED'));
    assert.ok(bilesik.length > 1, 'metrikler birden çok deyime bölünmeli');
    for (const s of bilesik) assert.ok(disTerim(s.replace(/^WITH s AS MATERIALIZED \([^)]*\)/, '')) <= D1_BILESIK_SINIRI, s.slice(0, 120));
  }
});
