import test from 'node:test';
import assert from 'node:assert/strict';
import { panelIstegi, esit, COOKIE, DENEME_SINIRI } from '../src/panel.js';
import { sahteD1 } from './sahte-d1.js';

const T0 = Date.parse('2026-10-08T09:00:00Z');
const env = (ek = {}) => ({ DB: sahteD1(), PANEL_ANAHTARI: 'dogru-anahtar-123', ...ek });
const get = (yol, cerez, url = 'https://api.kpsstercihi.com') => new Request(url + yol, { headers: cerez ? { Cookie: cerez } : {} });
const giris = (anahtar, ip = '198.51.100.1') => new Request('https://api.kpsstercihi.com/panel/giris', {
  method: 'POST', headers: { 'CF-Connecting-IP': ip, 'User-Agent': 'Mozilla/5.0 test', 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'anahtar=' + encodeURIComponent(anahtar),
});
const calistir = (e, istek) => panelIstegi(istek, e, new URL(istek.url), { simdiMs: T0 });

test('esit sabit süreli karşılaştırma doğru çalışır', () => {
  assert.equal(esit('abc', 'abc'), true);
  assert.equal(esit('abc', 'abd'), false);
  assert.equal(esit('abc', 'abcd'), false);
  assert.equal(esit('', ''), true);
});

test('çerezsiz /panel giriş formu gösterir, veri uçları 401', async () => {
  const e = env();
  const r = await calistir(e, get('/panel'));
  assert.equal(r.status, 200);
  const g = await r.text();
  assert.ok(g.includes('name="anahtar"') && g.includes('type="password"'));
  assert.ok(!g.includes('/panel/veri'));
  assert.equal((await calistir(e, get('/panel/veri?aralik=7g'))).status, 401);
  assert.equal((await calistir(e, get('/panel/canli'))).status, 401);
});

test('doğru anahtar: HttpOnly Secure SameSite=Strict çerez ve panel erişimi', async () => {
  const e = env();
  const r = await calistir(e, giris('dogru-anahtar-123'));
  assert.equal(r.status, 303);
  const sc = r.headers.get('Set-Cookie');
  assert.match(sc, /HttpOnly/);
  assert.match(sc, /Secure/);
  assert.match(sc, /SameSite=Strict/);
  assert.match(sc, /Path=\/panel/);
  assert.ok(!sc.includes('dogru-anahtar-123'), 'çerez anahtarı içermez');
  const cerez = sc.split(';')[0];
  const p = await calistir(e, get('/panel', cerez));
  assert.equal(p.status, 200);
  const html = await p.text();
  assert.ok(html.includes('Site analizi') && html.includes('/panel/veri'));
  assert.match(p.headers.get('Content-Security-Policy'), /script-src 'nonce-/);
  const v = await calistir(e, get('/panel/veri?aralik=bugun', cerez));
  assert.equal(v.status, 200);
  assert.equal((await v.json()).aralik.ad, 'bugun');
  assert.equal((await calistir(e, get('/panel/canli', cerez))).status, 200);
});

test('sahte, bozuk ve süresi dolmuş çerezler reddedilir', async () => {
  const e = env();
  const sc = (await calistir(e, giris('dogru-anahtar-123'))).headers.get('Set-Cookie').split(';')[0];
  const [ad, deger] = sc.split('=');
  const [bit, imza] = deger.split('.');
  for (const c of [`${ad}=${bit}.${imza.replace(/.$/, imza.endsWith('0') ? '1' : '0')}`, `${ad}=${Number(bit) + 1000}.${imza}`, `${ad}=${bit}`, `${ad}=x.y`, `${COOKIE}=`]) {
    assert.equal((await calistir(e, get('/panel/veri', c))).status, 401, c);
  }
  // başka anahtarla imzalanmış çerez
  const baska = env({ PANEL_ANAHTARI: 'baska' });
  const sc2 = (await calistir(baska, giris('baska'))).headers.get('Set-Cookie').split(';')[0];
  assert.equal((await calistir(e, get('/panel/veri', sc2))).status, 401);
  // süresi geçmiş
  const gec = await panelIstegi(get('/panel/veri', sc), e, new URL('https://api.kpsstercihi.com/panel/veri'), { simdiMs: T0 + 31 * 86400e3 });
  assert.equal(gec.status, 401);
});

test('yanlış anahtar 401; art arda hatadan sonra kilit (doğru anahtar da reddedilir)', async () => {
  const e = env();
  for (let i = 0; i < DENEME_SINIRI; i++) assert.equal((await calistir(e, giris('yanlis' + i))).status, 401);
  const k = await calistir(e, giris('dogru-anahtar-123'));
  assert.equal(k.status, 429);
  assert.equal(k.headers.get('Set-Cookie'), null);
  // başka istemci etkilenmez
  assert.equal((await calistir(e, giris('dogru-anahtar-123', '192.0.2.77'))).status, 303);
  // kilit süresi dolunca açılır
  const sonra = await panelIstegi(giris('dogru-anahtar-123'), e, new URL('https://api.kpsstercihi.com/panel/giris'), { simdiMs: T0 + 16 * 60e3 });
  assert.equal(sonra.status, 303);
});

test('boş anahtar başarısız sayılır; sır tanımlı değilse panel kapalı', async () => {
  assert.equal((await calistir(env(), giris(''))).status, 401);
  const e = env({ PANEL_ANAHTARI: undefined });
  assert.equal((await calistir(e, get('/panel'))).status, 503);
  assert.equal((await calistir(e, giris('bir-sey'))).status, 503);
});

test('ORTAM=yerel yalnız PANEL_ANAHTARI tanımlı değilken girişi atlar', async () => {
  const e = env({ PANEL_ANAHTARI: undefined, ORTAM: 'yerel' });
  assert.equal((await calistir(e, get('/panel'))).status, 200);
  assert.equal((await (await calistir(e, get('/panel/veri'))).json()).kpi.ziyaretci, 0);
  const sirli = env({ ORTAM: 'yerel' });
  assert.match(await (await calistir(sirli, get('/panel'))).text(), /name="anahtar"/);
  assert.equal((await calistir(env({ PANEL_ANAHTARI: undefined }), get('/panel'))).status, 503);
});