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
      _calistir() {
        sayac.sorgu++;
        const s = db.prepare(sql);
        if (/^\s*(select|with)/i.test(sql)) {
          const results = s.all(...this.p);
          return { results, meta: { rows_read: results.length, rows_written: 0, changes: 0 } };
        }
        const r = s.run(...this.p);
        const changes = Number(r.changes) || 0;
        return { results: [], meta: { rows_read: 0, rows_written: changes, changes, last_row_id: Number(r.lastInsertRowid) } };
      },
      async all() { return this._calistir(); },
      async first() { return this._calistir().results[0] ?? null; },
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
