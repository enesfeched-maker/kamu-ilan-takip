// Gerçek SQLite (node:sqlite) üzerinde D1 benzeri sahte DB: schema.sql'i yükler, ifade sayar,
// ifade başına 100 parametre sınırını uygular.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';

const SEMA = readFileSync(new URL('../schema.sql', import.meta.url), 'utf8');

export function sahteDB() {
  const raw = new DatabaseSync(':memory:');
  raw.exec(SEMA);
  const sayac = { sql: 0 };
  const DB = {
    prepare(q) {
      let args = [];
      const kos = (mod) => {
        sayac.sql++;
        if (args.length > 100) throw new Error(`D1: ifade başına 100 parametre sınırı aşıldı (${args.length})`);
        for (const a of args) if (typeof a === 'string' && Buffer.byteLength(a) > 100 * 1024) throw new Error('D1: ifade 100 KB sınırını aştı');
        const st = raw.prepare(q);
        if (mod === 'all') return st.all(...args).map((r) => ({ ...r }));
        const r = st.run(...args);
        return { success: true, meta: { changes: Number(r.changes) } };
      };
      const o = {
        bind(...x) { args = x; return o; },
        async first() { const r = kos('all'); return r[0] ?? null; },
        async all() { return { results: kos('all') }; },
        async run() { return kos('run'); },
      };
      return o;
    },
  };
  return { DB, raw, sayac };
}

export function kullaniciEkle(raw, chat_id, ek = {}) {
  const k = { onay: 1, duzeyler: '[]', iller: '[]', kategoriler: '[]', akademik: 0, kelimeler: '[]', aktif: 1, hatirlatma: 1, ...ek };
  raw.prepare('INSERT INTO kullanicilar (chat_id, onay, duzeyler, iller, kategoriler, akademik, kelimeler, aktif, hatirlatma, olusturma, guncelleme) VALUES (?,?,?,?,?,?,?,?,?,?,?)')
    .run(chat_id, k.onay, k.duzeyler, k.iller, k.kategoriler, k.akademik, k.kelimeler, k.aktif, k.hatirlatma, 'x', 'x');
}

export const say = (raw, sql, ...a) => raw.prepare(sql).get(...a);
export const hepsi = (raw, sql, ...a) => raw.prepare(sql).all(...a).map((r) => ({ ...r }));
