import test from 'node:test';
import assert from 'node:assert/strict';
import { arananIstegi } from '../src/aranan.js';
import { bellekSifirla } from '../src/onbellek.js';
import { sahteD1 } from './sahte-d1.js';

const T0 = Date.parse('2026-10-08T09:00:00Z');
const ozet = (db, gun, k1, k2, oturum) => db.ham.prepare("INSERT INTO ozet (gun, boyut, k1, k2, say, tekil, oturum, toplam) VALUES (?, 'arama', ?, ?, ?, ?, ?, 0)").run(gun, k1, k2, oturum, oturum, oturum);

test('yalnız eşiği geçen, çoğunlukla sonuçsuz ve düzgün kelimeler; bugün ve 7 günden eski sayılmaz', async () => {
  bellekSifirla();
  const db = sahteD1(); const env = { DB: db };
  ozet(db, '2026-10-07', 'diyetisyen', 'sifir', 3); ozet(db, '2026-10-05', 'diyetisyen', 'sifir', 2);
  ozet(db, '2026-10-07', 'fizyoterapist', 'sifir', 3);
  ozet(db, '2026-10-07', 'memur', 'sifir', 4); ozet(db, '2026-10-07', 'memur', 'var', 40); // sonuç çoğunlukla çıkıyor
  ozet(db, '2026-10-07', 'ahmet 0532', 'sifir', 9); // rakam: kişisel olabilir
  ozet(db, '2026-10-07', 'veteriner', 'sifir', 2); // eşik altı
  ozet(db, '2026-10-08', 'bugunku', 'sifir', 9); ozet(db, '2026-09-28', 'eski', 'sifir', 9);
  const r = await arananIstegi(new Request('https://api.kpsstercihi.com/aranan', { headers: { Origin: 'https://kpsstercihi.com' } }), env, T0);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.deepEqual((await r.json()).kelimeler, [{ kelime: 'diyetisyen', oturum: 5 }, { kelime: 'fizyoterapist', oturum: 3 }]);
});
