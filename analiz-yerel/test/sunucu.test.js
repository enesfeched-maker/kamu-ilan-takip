import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { yerelD1 } from '../d1.js';
import { ortamKur, sunucuKur, bakimZamanlayici } from '../sunucu.js';

const ORIGIN = 'https://kpsstercihi.com';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
const paket = (olaylar) => ({ s: 'abcdEFGH1234', r: 0, w: 390, l: 'tr-TR', ref: 'www.google.com', e: olaylar });

async function kur(ek = {}) {
  const dizin = mkdtempSync(join(tmpdir(), 'kpss-analiz-'));
  const db = yerelD1(join(dizin, 'a.sqlite'));
  const env = ortamKur(db, { PANEL_ANAHTARI: 'deneme-anahtari', ...ek });
  const sunucu = sunucuKur(env);
  await new Promise((r) => sunucu.listen(0, '127.0.0.1', r));
  const taban = `http://127.0.0.1:${sunucu.address().port}`;
  const kapat = () => { sunucu.close(); db.kapat(); rmSync(dizin, { recursive: true, force: true }); };
  return { db, env, taban, kapat, dizin };
}

test('olay HTTP ile kaydedilir; IP saklanmaz, X-Forwarded-For özet için kullanılır', async () => {
  const k = await kur();
  try {
    const gonder = (ip) => fetch(k.taban + '/o', { method: 'POST', headers: { Origin: ORIGIN, 'User-Agent': UA, 'X-Forwarded-For': ip, 'Content-Type': 'text/plain' },
      body: JSON.stringify(paket([{ t: 'sayfa', p: '/', v: 'bugun', f: 1 }])) });
    assert.equal((await gonder('198.51.100.1')).status, 204);
    assert.equal((await gonder('198.51.100.2')).status, 204);
    const s = k.db.ham.prepare('SELECT * FROM olaylar ORDER BY id').all();
    assert.equal(s.length, 2);
    assert.notEqual(s[0].zv, s[1].zv); // farklı IP -> farklı günlük özet
    assert.equal(s[0].ulke, null);      // Cloudflare ülke bilgisi yok
    assert.ok(!JSON.stringify(s).includes('198.51.100'));
  } finally { k.kapat(); }
});

test('yabancı köken 403, CORS ve OPTIONS çalışır', async () => {
  const k = await kur();
  try {
    const r = await fetch(k.taban + '/o', { method: 'POST', headers: { Origin: 'https://evil.example', 'User-Agent': UA }, body: JSON.stringify(paket([{ t: 'sayfa', p: '/' }])) });
    assert.equal(r.status, 403);
    const o = await fetch(k.taban + '/o', { method: 'OPTIONS', headers: { Origin: ORIGIN } });
    assert.equal(o.status, 204);
    assert.equal(o.headers.get('access-control-allow-origin'), ORIGIN);
  } finally { k.kapat(); }
});

test('/populer, /aranan ve kök yanıt verir; bilinmeyen yol 404', async () => {
  const k = await kur();
  try {
    assert.equal((await fetch(k.taban + '/')).status, 200);
    assert.equal((await fetch(k.taban + '/populer', { headers: { Origin: ORIGIN } })).status, 200);
    assert.equal((await fetch(k.taban + '/aranan', { headers: { Origin: ORIGIN } })).status, 200);
    assert.equal((await fetch(k.taban + '/yok')).status, 404);
  } finally { k.kapat(); }
});

test('panel yanlış anahtarla girişi reddeder, doğru anahtarla çerez verir', async () => {
  const k = await kur();
  try {
    const giris = (anahtar) => fetch(k.taban + '/panel/giris', { method: 'POST', redirect: 'manual',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Forwarded-For': '198.51.100.9' }, body: 'anahtar=' + anahtar });
    const yanlis = await giris('yanlis');
    assert.equal(yanlis.headers.get('set-cookie'), null);
    const dogru = await giris('deneme-anahtari');
    assert.equal(dogru.status, 303);
    assert.match(dogru.headers.get('set-cookie') || '', /Path=\/panel/);
    // çerezsiz veri isteği reddedilir
    assert.notEqual((await fetch(k.taban + '/panel/veri')).status, 200);
  } finally { k.kapat(); }
});

test('bakım gün başına bir kez, 00:30 UTC sonrası çalışır; durum dosyası yazılır', async () => {
  const k = await kur();
  try {
    const dosya = join(k.dizin, 'son-bakim.txt');
    let t = new Date('2026-10-27T00:10:00Z');
    const z = bakimZamanlayici(k.env, dosya, () => t);
    assert.equal(await z.dene(), false);            // 00:10: henüz erken
    t = new Date('2026-10-27T00:31:00Z');
    assert.equal(await z.dene(), true);
    assert.ok(existsSync(dosya));
    assert.equal(await z.dene(), false);            // aynı gün ikinci kez çalışmaz
    t = new Date('2026-10-28T09:00:00Z');
    assert.equal(await z.dene(), true);             // kapalı kalındıysa sonraki gün telafi
  } finally { k.kapat(); }
});
