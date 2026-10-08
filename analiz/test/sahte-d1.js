// Sahte D1: node:sqlite ile bellek içi gerçek SQLite; schema.sql'i olduğu gibi uygular.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';

export function sahteD1() {
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8'));
  const sayac = { sorgu: 0, batch: 0 };
  const duzelt = (a) => a.map((x) => (x === undefined ? null : x));
  function hazirla(sql) {
    return {
      sql, p: [],
      bind(...a) { this.p = duzelt(a); return this; },
      _calistir() { sayac.sorgu++; const s = db.prepare(sql); return /^\s*(select|with)/i.test(sql) ? { results: s.all(...this.p) } : (s.run(...this.p), { results: [] }); },
      async all() { return this._calistir(); },
      async first() { const r = this._calistir().results; return r[0] ?? null; },
      async run() { return this._calistir(); },
    };
  }
  return {
    ham: db, sayac,
    prepare: hazirla,
    async batch(liste) {
      sayac.batch++;
      db.exec('BEGIN');
      try { const out = liste.map((s) => s._calistir()); db.exec('COMMIT'); return out; } catch (e) { db.exec('ROLLBACK'); throw e; }
    },
  };
}

export function istek(govde, { ip = '203.0.113.7', ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
  origin = 'https://kpsstercihi.com', basliklar = {}, cf = { country: 'TR', region: 'Ankara', city: 'Ankara' }, yontem = 'POST', url = 'https://api.kpsstercihi.com/o' } = {}) {
  const h = { 'User-Agent': ua, 'CF-Connecting-IP': ip, 'Content-Type': 'text/plain;charset=UTF-8', ...(origin ? { Origin: origin } : {}), ...basliklar };
  const r = new Request(url, { method: yontem, headers: h, body: yontem === 'POST' ? (typeof govde === 'string' ? govde : JSON.stringify(govde)) : undefined });
  Object.defineProperty(r, 'cf', { value: cf });
  return r;
}

export const paket = (olaylar, ek = {}) => ({ s: 'abcdEFGH1234', r: 0, w: 390, l: 'tr-TR', ref: 'www.google.com', e: olaylar, ...ek });
