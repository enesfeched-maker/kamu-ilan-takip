// docs/a.js istemci izleyicisi: sahte tarayıcı ortamında (vm) çalıştırılır.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const KAYNAK = readFileSync(new URL('../../docs/a.js', import.meta.url), 'utf8');

function ortam({ host = 'kpsstercihi.com', protocol = 'https:', pathname = '/', search = '', nav = {}, referrer = '', store = {}, beacon = true, fetchVar = true, a404 = false } = {}) {
  const gonderilen = [], dinleyiciler = {}, fetchler = [], zamanlar = [];
  const oturumDepo = {};
  const belge = {
    hidden: false, readyState: 'interactive', referrer,
    documentElement: { hasAttribute: (n) => a404 && n === 'data-a404', scrollHeight: 3000, scrollTop: 0 },
    addEventListener(t, f) { (dinleyiciler[t] = dinleyiciler[t] || []).push(f); },
  };
  const pencere = {
    navigator: { language: 'tr-TR', ...nav }, innerWidth: 390, innerHeight: 800, scrollY: 0,
    location: { hostname: host, protocol, pathname, search, origin: protocol + '//' + host },
    sessionStorage: { getItem: (k) => oturumDepo[k] ?? null, setItem: (k, v) => { oturumDepo[k] = String(v); } },
    localStorage: { getItem: (k) => (k in store ? store[k] : null) },
    crypto: { getRandomValues: (a) => { a.forEach((_, i) => { a[i] = (i * 37 + 11) % 256; }); } },
    addEventListener(t, f) { (dinleyiciler['w:' + t] = dinleyiciler['w:' + t] || []).push(f); },
  };
  if (beacon) pencere.navigator.sendBeacon = (url, govde) => { gonderilen.push({ url, govde: JSON.parse(govde) }); return true; };
  const ctx = {
    window: pencere, document: belge, URLSearchParams, URL, JSON, Math, Date, Uint8Array, Number, String, isFinite, PerformanceObserver: undefined,
    setTimeout: (f, ms) => { zamanlar.push({ f, ms }); return zamanlar.length; }, clearTimeout: () => {}, setInterval: () => 0,
    fetch: fetchVar ? (url, o) => { fetchler.push({ url, o }); return Promise.resolve({}); } : undefined,
  };
  pencere.window = pencere;
  vm.runInNewContext(KAYNAK, ctx);
  const tetikle = (t, ev) => (dinleyiciler[t] || []).forEach((f) => f(ev));
  return { pencere, gonderilen, fetchler, tetikle, belge, dinleyiciler, oturumDepo, zamanlar };
}

test('yerel adreste, file: üzerinde, DNT/GPC açıkken ve otomasyonda hiçbir şey kurulmaz', () => {
  for (const o of [{ host: 'localhost' }, { host: '127.0.0.1' }, { protocol: 'file:', host: '' }, { host: 'ornek.com' }, { host: 'kpsstercihi.com', protocol: 'http:' },
    { nav: { doNotTrack: '1' } }, { nav: { globalPrivacyControl: true } }, { nav: { webdriver: true } }, { beacon: false, fetchVar: false }]) {
    const e = ortam(o);
    assert.equal(e.pencere.kpssA, undefined, JSON.stringify(o));
    assert.equal(e.gonderilen.length, 0);
  }
});

test('sayfa görüntüleme: ilk olay f=1, oturum kodu sessionStorage, geri dönen bayrağı kit-son-ziyaret’ten', () => {
  const e = ortam({ store: { 'kit-son-ziyaret': '"2026-10-01T10:00:00.000Z"' }, referrer: 'https://www.google.com/search?q=x', search: '?utm_source=telegram&utm_medium=kanal' });
  assert.equal(typeof e.pencere.kpssA, 'function');
  e.pencere.kpssA('sayfa', { v: 'bugun' });
  e.tetikle('visibilitychange', {});
  e.belge.hidden = true;
  e.tetikle('visibilitychange', {});
  assert.equal(e.gonderilen.length, 1);
  const p = e.gonderilen[0];
  assert.equal(p.url, 'https://api.kpsstercihi.com/o');
  assert.equal(p.govde.r, 1);
  assert.equal(p.govde.ref, 'www.google.com');
  assert.deepEqual(p.govde.u, { s: 'telegram', m: 'kanal', c: '' });
  assert.deepEqual(p.govde.e[0], { t: 'sayfa', p: '/', v: 'bugun', f: 1 });
  assert.match(p.govde.s, /^o[a-z0-9]{9}$/);
  assert.ok(JSON.parse(e.oturumDepo['kit-a']).f === 1);
  // yeni ziyaretçi: depo boş
  const y = ortam();
  y.pencere.kpssA('sayfa', {});
  y.belge.hidden = true; y.tetikle('visibilitychange', {});
  assert.equal(y.gonderilen[0].govde.r, 0);
});

test('aynı ekran tekrar sayılmaz; ekran() sayfa olayı üretmez; tıklama olayları görünümü taşır', () => {
  const e = ortam();
  const k = e.pencere.kpssA;
  k('sayfa', { v: 'ilanlar' }); k('sayfa', { v: 'ilanlar' });
  k('sayfa', { v: 'ilan', k: 'abc' }); k('ekran', { v: 'ilanlar' });
  k('tikla', { a: 'arama', x: 'zabıta', n: 0 });
  k('tikla', {});
  e.belge.hidden = true; e.tetikle('visibilitychange', {});
  const ev = e.gonderilen.flatMap((g) => g.govde.e);
  assert.deepEqual(ev.map((x) => x.t + ':' + (x.v || '') + ':' + (x.a || '')), ['sayfa:ilanlar:', 'sayfa:ilan:', 'tikla:ilanlar:arama']);
  assert.equal(ev[1].k, 'abc');
  assert.equal(ev[2].n, 0);
  assert.equal(ev[0].f, 1);
  assert.equal(ev[1].f, undefined);
});

test('data-a öğeleri tıklanınca genel tikla olayı gider; bağlantıysa hemen', () => {
  const e = ortam();
  e.pencere.kpssA('sayfa', {});
  e.gonderilen.length = 0;
  const attr = { 'data-a': 'resmi_ilan', 'data-a-h': 'ilan-1', 'data-a-x': null, 'data-a-n': '3' };
  const el = { tagName: 'A', getAttribute: (n) => attr[n] ?? null };
  e.tetikle('click', { target: { closest: (s) => (s === '[data-a]' ? el : null) } });
  assert.equal(e.gonderilen.length, 1);
  const o = e.gonderilen[0].govde.e.find((x) => x.t === 'tikla');
  assert.deepEqual(o, { t: 'tikla', p: '/', a: 'resmi_ilan', h: 'ilan-1', n: 3 });
  // data-a olmayan öğe: olay yok
  e.gonderilen.length = 0;
  e.tetikle('click', { target: { closest: () => null } });
  assert.equal(e.gonderilen.length, 0);
});

test('404 sayfası yalnız 404 olayı gönderir', () => {
  const e = ortam({ a404: true, pathname: '/eski/sayfa' });
  assert.equal(e.gonderilen.length, 1);
  assert.deepEqual(e.gonderilen[0].govde.e, [{ t: '404', p: '/eski/sayfa' }]);
});

test('sendBeacon yoksa fetch(keepalive) kullanılır; paketler 20 olay ve ~4KB ile sınırlı', () => {
  const e = ortam({ beacon: false });
  for (let i = 0; i < 30; i++) e.pencere.kpssA('tikla', { a: 'daha_fazla', n: i });
  e.belge.hidden = true; e.tetikle('visibilitychange', {});
  assert.ok(e.fetchler.length >= 2);
  for (const f of e.fetchler) {
    const g = JSON.parse(f.o.body);
    assert.ok(g.e.length <= 20 && f.o.body.length <= 4100);
    assert.equal(f.o.keepalive, true);
    assert.equal(f.o.credentials, 'omit');
  }
});

test('hata olayı yalnız site betiklerinden ve en çok 5 kez', () => {
  const e = ortam();
  e.pencere.kpssA('sayfa', {});
  for (let i = 0; i < 8; i++) e.tetikle('w:error', { message: 'TypeError: x', filename: 'https://kpsstercihi.com/portal.js?v=22', lineno: 10 + i });
  e.tetikle('w:error', { message: 'ext', filename: 'chrome-extension://abc/x.js', lineno: 1 });
  e.belge.hidden = true; e.tetikle('visibilitychange', {});
  const h = e.gonderilen.flatMap((g) => g.govde.e).filter((x) => x.t === 'hata');
  assert.equal(h.length, 5);
  assert.equal(h[0].h, '/portal.js:10');
});

test('sayfa bildirmeyen sayfalar için DOMContentLoaded'+"'"+'nda ilk görüntüleme gider; portal bildirdiyse tekrarlanmaz', () => {
  const a = ortam({ pathname: '/ilan/abc-1/' });
  assert.equal(a.gonderilen.length, 0);
  a.tetikle('DOMContentLoaded', {});
  a.belge.hidden = true; a.tetikle('visibilitychange', {});
  assert.deepEqual(a.gonderilen[0].govde.e, [{ t: 'sayfa', p: '/ilan/abc-1/', f: 1 }]);
  const b = ortam();
  b.pencere.kpssA('sayfa', { v: 'bugun' });
  b.tetikle('DOMContentLoaded', {});
  b.belge.hidden = true; b.tetikle('visibilitychange', {});
  assert.equal(b.gonderilen.flatMap((g) => g.govde.e).length, 1);
});
