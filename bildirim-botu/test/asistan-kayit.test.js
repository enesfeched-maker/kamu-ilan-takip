import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { asistanIstek, testSifirla } from '../src/asistan.js';
import { gizle, esit, eskiKayitlariSil, GUNLUK_SINIR } from '../src/asistan-kayit.js';
import worker from '../src/index.js';
import { sahteKayitDB } from './sahte-kayit.js';

const gercekFetch = globalThis.fetch;
const ANAHTAR = 'a'.repeat(32);
let ip = 0;

beforeEach(() => {
  testSifirla();
  globalThis.fetch = async () => { throw new Error('ağ yok'); }; // veri çekilemez; kimlik/selam yine cevaplanır
});
afterEach(() => { globalThis.fetch = gercekFetch; });

const env = (ek = {}) => ({ DB: sahteKayitDB(), ASISTAN_ANAHTAR: ANAHTAR, ASISTAN_YZ: '0', ...ek });
const istek = (yol, govde, { anahtar, yontem = 'POST', origin, ipx } = {}) => new Request(`https://w.test${yol}`, {
  method: yontem,
  headers: {
    'Content-Type': 'application/json', 'CF-Connecting-IP': ipx || `10.1.0.${++ip}`,
    ...(anahtar ? { 'X-Asistan-Anahtar': anahtar } : {}), ...(origin ? { Origin: origin } : {}),
  },
  ...(yontem === 'GET' ? {} : { body: JSON.stringify(govde) }),
});
const sor = async (e, govde, ek) => {
  const r = await asistanIstek(istek('/asistan/sor', govde, ek), e, { waitUntil() {} });
  return { r, j: await r.json() };
};

// ------------------------------------------------------------ gizleme

test('gizle: e-posta, telefon biçimleri ve kimlik no maskelenir', () => {
  assert.equal(gizle('mail ali.veli@ornek.com adresim'), 'mail [e-posta] adresim');
  assert.equal(gizle('0532 123 45 67 ara'), '[telefon] ara');
  assert.equal(gizle('05321234567'), '[telefon]');
  assert.equal(gizle('532-123-45-67'), '[telefon]');
  assert.equal(gizle('+90 532 123 45 67'), '[telefon]');
  assert.equal(gizle('0312 123 45 67'), '[telefon]');
  assert.equal(gizle('tc 12345678901 bu'), 'tc [kimlik no] bu');
  assert.equal(gizle('12345678901'), '[kimlik no]');
});

test('gizle: puan, yaş ve yıl gibi sayılara dokunmaz', () => {
  for (const s of ['kpss 65 puanla nereye girerim', '82,5 puanım var', '2026 yılında kaç kişi alınacak', 'p93 70 75 80 85 90', '30 yaşında zabıta', '65 70 80 90 85']) {
    assert.equal(gizle(s), s);
  }
});

test('esit: sabit süreli karşılaştırma doğru sonuç verir', () => {
  assert.equal(esit('abc', 'abc'), true);
  assert.equal(esit('abc', 'abd'), false);
  assert.equal(esit('abc', 'abcd'), false);
  assert.equal(esit('', 'a'), false);
});

// ------------------------------------------------------------ /sor kaydı

test('/sor: kayıt yazılır, kid ve tur döner; soru maskelenir; IP/UA saklanmaz', async () => {
  const e = env();
  const { r, j } = await sor(e, { soru: 'merhaba ali@ornek.com 05321234567', sayfa: '/meslek/zabita-memuru/' }, { origin: 'https://kpsstercihi.com' });
  assert.equal(r.status, 200);
  assert.equal(j.kid, 1);
  assert.equal(j.tur, 'selam');
  const s = e.DB.d.satirlar[0];
  assert.equal(s.kanal, 'site');
  assert.equal(s.soru, 'merhaba [e-posta] [telefon]');
  assert.equal(s.tur, 'selam');
  assert.equal(s.sayfa, '/meslek/zabita-memuru/');
  assert.equal(s.meta, null);
  assert.ok(/^\d{4}-\d\d-\d\dT.*Z$/.test(s.zaman));
  assert.ok(!JSON.stringify(s).includes('10.1.0.'));
  assert.deepEqual(Object.keys(s).sort(), ['baglantilar', 'durum', 'geri', 'gonderilen', 'id', 'ilan_sayisi', 'kanal', 'meta', 'metin', 'sayfa', 'soru', 'tur', 'zaman']);
});

test('/sor: kanal ve meta yalnız geçerli anahtarla kabul edilir', async () => {
  const e = env();
  const govde = { soru: 'merhaba', kanal: 'instagram', meta: { kullanici: 'ali', medya: 'm1', yorum_id: 'c9', fazla: 'x' } };
  await sor(e, govde); // anahtarsız
  await sor(e, govde, { anahtar: 'yanlis' });
  await sor(e, govde, { anahtar: ANAHTAR });
  const [a, b, c] = e.DB.d.satirlar;
  assert.equal(a.kanal, 'site'); assert.equal(a.meta, null);
  assert.equal(b.kanal, 'site'); assert.equal(b.meta, null);
  assert.equal(c.kanal, 'instagram');
  assert.deepEqual(JSON.parse(c.meta), { kullanici: 'ali', medya: 'm1', yorum_id: 'c9' });
});

test('/sor: anahtar tanımsızsa kanal/meta yok sayılır (bypass kapalı)', async () => {
  const e = env({ ASISTAN_ANAHTAR: undefined });
  await sor(e, { soru: 'merhaba', kanal: 'instagram', meta: { kullanici: 'x' } }, { anahtar: ANAHTAR });
  assert.equal(e.DB.d.satirlar[0].kanal, 'site');
  assert.equal(e.DB.d.satirlar[0].meta, null);
});

test('/sor: geçerli anahtar IP hız sınırını aşar, anahtarsız 13.sü 429', async () => {
  const e = env();
  for (let n = 0; n < 15; n++) assert.equal((await sor(e, { soru: 'merhaba' }, { anahtar: ANAHTAR, ipx: '198.51.100.7' })).r.status, 200);
  for (let n = 0; n < 12; n++) assert.equal((await sor(e, { soru: 'merhaba' }, { ipx: '198.51.100.8' })).r.status, 200);
  assert.equal((await sor(e, { soru: 'merhaba' }, { ipx: '198.51.100.8' })).r.status, 429);
});

test('/sor: D1 hata verse de cevap gelir, kid null', async () => {
  const e = env();
  e.DB.d.hata = true;
  const { r, j } = await sor(e, { soru: 'bot musun' });
  assert.equal(r.status, 200);
  assert.equal(j.kid, null);
  assert.match(j.metin, /otomatik asistan/);
  const bos = await sor({ ASISTAN_YZ: '0' }, { soru: 'bot musun' }); // DB bağlaması hiç yok
  assert.equal(bos.r.status, 200);
  assert.equal(bos.j.kid, null);
});

test('günlük sınır: dolunca cevap normal, kid null; sayaç bellekte (10 dk içinde yeniden sayılmaz)', async () => {
  const e = env();
  e.DB.d.sayiDondur = GUNLUK_SINIR - 1;
  const ilk = await sor(e, { soru: 'merhaba' });
  assert.equal(ilk.j.kid, 1);
  const ikinci = await sor(e, { soru: 'merhaba' });
  assert.equal(ikinci.r.status, 200);
  assert.equal(ikinci.j.kid, null);
  assert.equal(ikinci.j.tur, 'selam');
  assert.equal(e.DB.d.satirlar.length, 1);
  assert.equal(e.DB.d.sorgular.filter((x) => x === 'say').length, 1);
});

// ------------------------------------------------------------ /geri

test('/geri: site kaydına 24 saat içinde yazılır; instagram ve eski kayıt reddedilir; CORS var', async () => {
  const e = env();
  const { j } = await sor(e, { soru: 'merhaba' });
  await sor(e, { soru: 'merhaba', kanal: 'instagram' }, { anahtar: ANAHTAR });
  const geri = async (kid, deger) => {
    const r = await asistanIstek(istek('/asistan/geri', { kid, deger }, { origin: 'https://kpsstercihi.com' }), e, {});
    return { r, j: await r.json() };
  };
  const ok = await geri(j.kid, 1);
  assert.equal(ok.r.status, 200);
  assert.equal(ok.j.ok, true);
  assert.equal(ok.r.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.equal(e.DB.d.satirlar[0].geri, 1);
  assert.equal((await geri(j.kid, -1)).j.ok, true);
  assert.equal(e.DB.d.satirlar[0].geri, -1);
  assert.equal((await geri(2, 1)).j.ok, false); // instagram satırı
  assert.equal(e.DB.d.satirlar[1].geri, null);
  e.DB.d.satirlar[0].zaman = new Date(Date.now() - 25 * 3600 * 1000).toISOString();
  assert.equal((await geri(j.kid, 1)).j.ok, false); // 24 saat geçti
  assert.equal(e.DB.d.satirlar[0].geri, -1);
  assert.equal((await geri(99, 1)).j.ok, false);
  assert.equal((await geri(1, 5)).r.status, 400);
  assert.equal((await geri('x', 1)).r.status, 400);
});

test('/geri: anahtar gerekmez, DB hatasında 200 ok:false', async () => {
  const e = env();
  await sor(e, { soru: 'merhaba' });
  e.DB.d.hata = true;
  const r = await asistanIstek(istek('/asistan/geri', { kid: 1, deger: 1 }), e, {});
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ok, false);
});

// ------------------------------------------------------------ yetkili uçlar

test('/durum ve /kayitlar: anahtar yok 503, yanlış/eksik 401, doğru 200', async () => {
  for (const [yol, yontem, govde] of [['/asistan/durum', 'POST', { kid: 1, durum: 'yanitlandi' }], ['/asistan/kayitlar', 'GET']]) {
    const e = env();
    await sor(e, { soru: 'merhaba' });
    const cagri = (ek, ortam = e) => asistanIstek(istek(yol, govde, { yontem, ...ek }), ortam, {});
    assert.equal((await cagri({}, env({ ASISTAN_ANAHTAR: undefined }))).status, 503);
    assert.equal((await cagri({ anahtar: ANAHTAR }, env({ ASISTAN_ANAHTAR: undefined }))).status, 503);
    assert.equal((await cagri({})).status, 401);
    assert.equal((await cagri({ anahtar: 'yanlis' })).status, 401);
    assert.equal((await cagri({ anahtar: ANAHTAR + 'x' })).status, 401);
    assert.equal((await cagri({ anahtar: ANAHTAR })).status, 200);
  }
});

test('/durum: durum ve gonderilen yazılır; geçersiz değerler 400', async () => {
  const e = env();
  await sor(e, { soru: 'merhaba' }, { anahtar: ANAHTAR });
  const d = (govde) => asistanIstek(istek('/asistan/durum', govde, { anahtar: ANAHTAR }), e, {});
  assert.equal((await d({ kid: 1, durum: 'yanitlandi', gonderilen: 'Merhaba' })).status, 200);
  assert.equal(e.DB.d.satirlar[0].durum, 'yanitlandi');
  assert.equal(e.DB.d.satirlar[0].gonderilen, 'Merhaba');
  assert.equal((await d({ kid: 1, durum: 'atlandi' })).status, 200);
  assert.equal(e.DB.d.satirlar[0].durum, 'atlandi');
  assert.equal((await d({ kid: 1, durum: 'bilinmez' })).status, 400);
  assert.equal((await d({ kid: 0, durum: 'hata' })).status, 400);
  assert.equal((await d({ kid: 1, durum: 'hata', gonderilen: 'x'.repeat(1001) })).status, 400);
});

test('/kayitlar: sonra ve limit ile sayfalanır, id artan, baglantilar/meta çözülür', async () => {
  const e = env();
  for (let n = 0; n < 5; n++) await sor(e, { soru: 'merhaba', kanal: 'instagram', meta: { kullanici: `u${n}` } }, { anahtar: ANAHTAR });
  const al = async (q) => (await asistanIstek(istek(`/asistan/kayitlar${q}`, null, { yontem: 'GET', anahtar: ANAHTAR }), e, {})).json();
  const bir = await al('?limit=2');
  assert.deepEqual(bir.kayitlar.map((k) => k.id), [1, 2]);
  assert.equal(bir.son, 2);
  assert.ok(Array.isArray(bir.kayitlar[0].baglantilar));
  assert.deepEqual(bir.kayitlar[0].meta, { kullanici: 'u0' });
  const iki = await al(`?sonra=${bir.son}&limit=10`);
  assert.deepEqual(iki.kayitlar.map((k) => k.id), [3, 4, 5]);
  assert.equal(iki.son, 5);
  const bos = await al('?sonra=5');
  assert.deepEqual(bos.kayitlar, []);
  assert.equal(bos.son, 5);
  assert.equal((await al('?limit=99999')).kayitlar.length, 5);
});

// ------------------------------------------------------------ saklama

test('saklama: 120 günden eski satırlar günde bir kez silinir', async () => {
  const e = env();
  const gun = 86400000;
  const simdi = Date.parse('2026-12-10T00:30:00Z');
  e.DB.d.satirlar.push(
    { id: 1, zaman: new Date(simdi - 121 * gun).toISOString() },
    { id: 2, zaman: new Date(simdi - 119 * gun).toISOString() },
  );
  assert.equal(await eskiKayitlariSil(e, simdi), true);
  assert.deepEqual(e.DB.d.satirlar.map((r) => r.id), [2]);
  e.DB.d.satirlar.push({ id: 3, zaman: new Date(simdi - 200 * gun).toISOString() });
  assert.equal(await eskiKayitlariSil(e, simdi + 3600000), false); // aynı gün
  assert.equal(e.DB.d.satirlar.length, 2);
  assert.equal(await eskiKayitlariSil(e, simdi + gun), true); // ertesi gün
  assert.deepEqual(e.DB.d.satirlar.map((r) => r.id), [2]);
  e.DB.d.hata = true;
  assert.equal(await eskiKayitlariSil(e, simdi + 2 * gun), false); // hata yutulur
});

test('scheduled: UTC 00:xx saatinde temizlik çalışır, diğer saatlerde çalışmaz', async () => {
  const e = env();
  const bekleyen = [];
  const ctx = { waitUntil: (p) => bekleyen.push(Promise.resolve(p).catch(() => {})) };
  const eski = { id: 1, zaman: '2020-01-01T00:00:00.000Z' };
  e.DB.d.satirlar.push(eski);
  await worker.scheduled({ scheduledTime: Date.parse('2026-12-10T12:00:00Z') }, e, ctx);
  await Promise.all(bekleyen);
  assert.equal(e.DB.d.satirlar.length, 1);
  await worker.scheduled({ scheduledTime: Date.parse('2026-12-10T00:05:00Z') }, e, ctx);
  await Promise.all(bekleyen);
  assert.equal(e.DB.d.satirlar.length, 0);
});
