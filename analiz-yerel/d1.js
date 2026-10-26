// Cloudflare D1 arayüzünü dosya tabanlı SQLite (node:sqlite) ile taklit eder; analiz/src koduna dokunmadan çalışır.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export function yerelD1(dosya, sema = new URL('../analiz/schema.sql', import.meta.url)) {
  if (dosya !== ':memory:') mkdirSync(dirname(dosya), { recursive: true });
  const db = new DatabaseSync(dosya);
  db.exec('PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA busy_timeout = 5000;');
  db.exec(readFileSync(sema, 'utf8')); // tüm ifadeler IF NOT EXISTS: yeniden çalıştırmak zararsız
  const duzelt = (a) => a.map((x) => (x === undefined ? null : x));

  function hazirla(sql) {
    return {
      p: [],
      bind(...a) { this.p = duzelt(a); return this; },
      _calistir() {
        const s = db.prepare(sql);
        if (/^\s*(select|with)/i.test(sql)) {
          const results = s.all(...this.p);
          return { results, meta: { rows_read: results.length, rows_written: 0 } };
        }
        const r = s.run(...this.p);
        return { results: [], meta: { rows_read: 0, rows_written: Number(r.changes) || 0 } };
      },
      async all() { return this._calistir(); },
      async first() { return this._calistir().results[0] ?? null; },
      async run() { return this._calistir(); },
      async raw() { return this._calistir().results.map((r) => Object.values(r)); },
    };
  }

  return {
    ham: db,
    prepare: hazirla,
    async batch(liste) {
      db.exec('BEGIN');
      try { const out = liste.map((s) => s._calistir()); db.exec('COMMIT'); return out; } catch (e) { db.exec('ROLLBACK'); throw e; }
    },
    kapat() { db.close(); },
  };
}
