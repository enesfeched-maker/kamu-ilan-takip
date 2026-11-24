import { test } from 'node:test';
import assert from 'node:assert/strict';
import { webIstek, webUygunMu, bolumKelimeleri, katla, endpointGecerli, jwtOnbellekTemizle } from '../src/web.js';
import { cronCalistir } from '../src/bildirim.js';
import worker from '../src/index.js';
import { sahteDB, hepsi, say } from './sahte-c.js';

process.removeAllListeners('warning');

const GUN = new Date('2026-10-01T09:00:00Z');
const dk = (d, m) => new Date(d.getTime() + m * 60000);
const EP = 'https://fcm.googleapis.com/fcm/send/abc123';
const EP2 = 'https://updates.push.services.mozilla.com/wpush/v2/xyz';
const EP3 = 'https://wns2-par02p.notify.windows.com/w/?token=abc';

async function vapidAnahtarlari() {
  const k = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const jwk = await crypto.subtle.exportKey('jwk', k.privateKey);
  const acik = Buffer.concat([Buffer.from([4]), Buffer.from(jwk.x, 'base64url'), Buffer.from(jwk.y, 'base64url')]);
  return { VAPID_ACIK: acik.toString('base64url'), VAPID_OZEL: jwk.d, pkcs8: Buffer.from(await crypto.subtle.exportKey('pkcs8', k.privateKey)).toString('base64url') };
}

const istek = (yol, govde, ek = {}) => new Request('https://w.test' + yol, {
  method: 'POST', headers: { 'Content-Type': 'application/json', ...(ek.baslik || {}) }, body: typeof govde === 'string' ? govde : JSON.stringify(govde),
});
const abone = (ek = {}) => ({ abonelik: { endpoint: EP, keys: { p256dh: 'BPabc-_123', auth: 'au-th_1' } }, duzey: 'lisans', bolum: 'Hukuk', puan: 70, ...ek });

const ilan = (n, ek = {}) => ({
  id: `i${n}`, kimlikler: [`i${n}`], baslik: `İlan ${n}`, kurum: 'Kurum', son_tarih: '2026-10-20', son_zaman: null,
  ogrenim: [], iller: [], kategori: null, kpss: null, duyuru_turu: null, sayfa: `https://site.test/ilan/${n}/`, metin: `ilan ${n} kurum`, ...ek,
});

// ------------------------------------------------------------------ yollar

test('rota: bozuk endpoint, düzey, puan, bölüm uzunluğu ve büyük gövde reddedilir', async () => {
  const { DB, raw } = sahteDB();
  const env = { DB };
  const durum = async (r) => (await webIstek(r, env)).status;
  assert.equal(await durum(istek('/web/abone', abone({ abonelik: { endpoint: 'https://evil.example.com/x' } }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ abonelik: { endpoint: 'http://fcm.googleapis.com/x' } }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ abonelik: { endpoint: 'https://fcm.googleapis.com.evil.com/x' } }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ abonelik: { endpoint: 'https://evilnotify.windows.com/x' } }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ duzey: 'doktora' }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ puan: 0 }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ puan: 101 }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ puan: '70' }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ bolum: 'x'.repeat(81) }))), 400);
  assert.equal(await durum(istek('/web/abone', abone({ bolum: 5 }))), 400);
  assert.equal(await durum(istek('/web/abone', '{bozuk')), 400);
  assert.equal(await durum(istek('/web/abone', abone({ bolum: 'x'.repeat(5000) }))), 413);
  assert.equal(await durum(istek('/web/bilinmeyen', {})), 404);
  assert.equal(await durum(istek('/web/sil', { endpoint: 'ftp://x' })), 400);
  assert.equal(say(raw, 'SELECT COUNT(*) AS n FROM web_aboneler').n, 0);
});

test('rota: CORS izinli/izinsiz köken, OPTIONS ön kontrol, GET reddi', async () => {
  const { DB } = sahteDB();
  const env = { DB };
  const on = await webIstek(new Request('https://w.test/web/abone', { method: 'OPTIONS', headers: { Origin: 'https://kpsstercihi.com' } }), env);
  assert.equal(on.status, 204);
  assert.equal(on.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.match(on.headers.get('Access-Control-Allow-Methods'), /POST/);
  const yerel = await webIstek(istek('/web/abone', abone(), { baslik: { Origin: 'http://localhost:8770' } }), env);
  assert.equal(yerel.status, 200);
  assert.equal(yerel.headers.get('Access-Control-Allow-Origin'), 'http://localhost:8770');
  assert.equal((await webIstek(istek('/web/abone', abone(), { baslik: { Origin: 'http://127.0.0.1:5500' } }), env)).status, 200);
  const kotu = await webIstek(istek('/web/abone', abone(), { baslik: { Origin: 'https://kotu.example' } }), env);
  assert.equal(kotu.status, 403);
  assert.equal(kotu.headers.get('Access-Control-Allow-Origin'), null);
  assert.equal((await webIstek(new Request('https://w.test/web/abone', { method: 'GET' }), env)).status, 405);
  assert.equal(await webIstek(new Request('https://w.test/baska'), env), null);
});

test('rota: abone upsert (kriter yenilenir), bekleyen en çok 5 döner ve siler, sil hepsini kaldırır; index.js yönlendirir', async () => {
  const { DB, raw } = sahteDB();
  const env = { DB };
  assert.equal((await worker.fetch(istek('/web/abone', abone()), env)).status, 200);
  assert.equal((await webIstek(istek('/web/abone', abone({ duzey: 'onlisans', bolum: '', puan: null })), env)).status, 200);
  const satirlar = hepsi(raw, 'SELECT * FROM web_aboneler');
  assert.equal(satirlar.length, 1);
  assert.equal(satirlar[0].duzey, 'onlisans');
  assert.equal(satirlar[0].bolum, '');
  assert.equal(satirlar[0].puan, null);
  assert.equal(satirlar[0].aktif, 1);
  for (let n = 0; n < 7; n++) raw.prepare('INSERT INTO web_bekleyen VALUES (?,?,?,?,?,?)').run(EP, `i${n}`, `B${n}`, 'K', `https://s/${n}`, `2026-10-01T09:0${n}:00Z`);
  raw.prepare('INSERT INTO web_bekleyen VALUES (?,?,?,?,?,?)').run(EP2, 'i1', 'Baska', 'K', 'https://s/x', 'z');
  const r = await webIstek(istek('/web/bekleyen', { endpoint: EP }), env);
  const j = await r.json();
  assert.equal(j.ilanlar.length, 5);
  assert.equal(j.toplam, 7);
  assert.deepEqual(Object.keys(j.ilanlar[0]).sort(), ['baslik', 'kurum', 'url']);
  assert.equal(say(raw, 'SELECT COUNT(*) AS n FROM web_bekleyen WHERE endpoint = ?', EP).n, 0);
  assert.equal(say(raw, 'SELECT COUNT(*) AS n FROM web_bekleyen').n, 1);
  assert.equal((await (await webIstek(istek('/web/bekleyen', { endpoint: EP }), env)).json()).ilanlar.length, 0);
  raw.prepare('INSERT INTO web_bekleyen VALUES (?,?,?,?,?,?)').run(EP, 'i9', 'B', 'K', 'u', 'z');
  assert.equal((await webIstek(istek('/web/sil', { endpoint: EP }), env)).status, 200);
  assert.equal(say(raw, 'SELECT COUNT(*) AS n FROM web_aboneler').n, 0);
  assert.equal(say(raw, 'SELECT COUNT(*) AS n FROM web_bekleyen WHERE endpoint = ?', EP).n, 0);
});

// ------------------------------------------------------------------ eşleştirme

test('endpoint ana bilgisayarları', () => {
  assert.ok(endpointGecerli(EP) && endpointGecerli(EP2) && endpointGecerli(EP3) && endpointGecerli('https://web.push.apple.com/abc'));
  assert.ok(!endpointGecerli('https://notify.windows.com.evil.com/x'));
  assert.ok(!endpointGecerli('https://user:pw@fcm.googleapis.com/x'));
  assert.ok(!endpointGecerli('https://fcm.googleapis.com:8443/x'));
  assert.ok(!endpointGecerli(null));
});

test('bölüm kelimeleri Türkçe katlanır, genel kelimeler atılır', () => {
  assert.deepEqual(bolumKelimeleri('Hukuk Fakültesi'), ['hukuk', 'fakultesi']);
  assert.deepEqual(bolumKelimeleri('Bilgisayar ve Öğretim Teknolojileri Bölümü'), ['bilgisayar', 'ogretim', 'teknolojileri']);
  assert.deepEqual(bolumKelimeleri('  '), []);
  assert.equal(katla('IŞIK İÇİN'), 'isik icin');
});

const uyar = (i, a) => {
  const simdi = GUN;
  return webUygunMu(i, a, '2026-10-01', simdi, katla(i.metin || ''), bolumKelimeleri(a.bolum));
};

test('eşleştirme: düzey', () => {
  assert.ok(uyar(ilan(1, { ogrenim: [] }), { duzey: 'lisans', bolum: '', puan: null }));
  assert.ok(uyar(ilan(1, { ogrenim: ['lisans', 'onlisans'] }), { duzey: 'lisans', bolum: '', puan: null }));
  assert.ok(!uyar(ilan(1, { ogrenim: ['ortaogretim'] }), { duzey: 'lisans', bolum: '', puan: null }));
});

test('eşleştirme: bölüm kelimelerinin HEPSİ gerekir; akademik ve süresi geçen ilan yok', () => {
  const i = ilan(1, { metin: 'belediye hukuk müşaviri alımı, hukuk fakültesi mezunu' });
  assert.ok(uyar(i, { duzey: 'lisans', bolum: 'Hukuk Fakültesi', puan: null }));
  assert.ok(uyar(i, { duzey: 'lisans', bolum: 'Hukuk Bölümü', puan: null }));
  assert.ok(!uyar(i, { duzey: 'lisans', bolum: 'Hukuk Mühendisliği', puan: null }));
  assert.ok(!uyar(ilan(2, { metin: 'bilgisayar mühendisi' }), { duzey: 'lisans', bolum: 'Hukuk', puan: null }));
  assert.ok(uyar(ilan(3, { metin: 'öğretmen' }), { duzey: 'lisans', bolum: 'Öğretmenlik ve', puan: null }) === false);
  assert.ok(!uyar(ilan(4, { kategori: 'akademik' }), { duzey: 'lisans', bolum: '', puan: null }));
  assert.ok(!uyar(ilan(5, { son_tarih: '2026-09-01' }), { duzey: 'lisans', bolum: '', puan: null }));
});

test('eşleştirme: puan eşiği (eşit geçer, kpsssiz ve eksik veri elemez)', () => {
  const a = (puan) => ({ duzey: 'lisans', bolum: '', puan });
  assert.ok(!uyar(ilan(1, { en_az_puan: 70 }), a(65)));
  assert.ok(uyar(ilan(1, { en_az_puan: 70 }), a(70)));
  assert.ok(uyar(ilan(1, { en_az_puan: 70, kpss: 'kpsssiz' }), a(10)));
  assert.ok(uyar(ilan(1, { en_az_puan: null }), a(10)));
  assert.ok(uyar(ilan(1, { en_az_puan: 70 }), a(null)));
});

// ------------------------------------------------------------------ cron

async function kur(ekEnv = {}) {
  const anahtar = await vapidAnahtarlari();
  const d = sahteDB();
  jwtOnbellekTemizle();
  const c = {
    ...d, anahtar, ilanlar: [], istek: 0, pushlar: [], pushDurum: {}, enCok: { sql: 0, istek: 0 },
    env: { DB: d.DB, ILAN_URL: 'https://x/bot-ilanlar.json', SITE_URL: 'https://site.test/', VAPID_ACIK: anahtar.VAPID_ACIK, VAPID_OZEL: anahtar.VAPID_OZEL, ...ekEnv },
  };
  c.bag = {
    bekle: async () => {},
    tg: async () => { c.istek++; return {}; },
    fetch: async (u, o) => {
      c.istek++;
      if (String(u).endsWith('gunluk.json')) return { ok: false, status: 404, json: async () => ({}) };
      if (String(u) === c.env.ILAN_URL) return { ok: true, status: 200, json: async () => ({ ilanlar: c.ilanlar }) };
      c.pushlar.push({ url: String(u), ...o });
      return { ok: true, status: c.pushDurum[String(u)] ?? 201 };
    },
  };
  c.calis = async (simdi) => {
    const once = { sql: c.sayac.sql, istek: c.istek };
    const s = await cronCalistir(c.env, simdi, c.bag);
    const h = { sql: c.sayac.sql - once.sql, istek: c.istek - once.istek };
    assert.ok(h.sql <= 40, `ifade ${h.sql} > 40`);
    assert.ok(h.istek <= 30, `istek ${h.istek} > 30`);
    assert.equal(s.istek, h.istek);
    c.enCok = { sql: Math.max(c.enCok.sql, h.sql), istek: Math.max(c.enCok.istek, h.istek) };
    return s;
  };
  c.aboneEkle = (endpoint, duzey = 'lisans', bolum = '', puan = null) =>
    c.raw.prepare('INSERT INTO web_aboneler (endpoint, p256dh, auth, duzey, bolum, puan, olusturma, aktif) VALUES (?,?,?,?,?,?,?,1)').run(endpoint, 'p', 'a', duzey, bolum, puan, 'x');
  return c;
}

// İlk çalıştırma ile mevcut ilanları "bilinen" yapar; sonra yeni ilanları ekleyip tarama süresini geçirir.
async function yeniIlanTetikle(c, ilk, yeni) {
  c.ilanlar = ilk;
  await c.calis(dk(GUN, -60));
  c.ilanlar = [...ilk, ...yeni];
  return c.calis(dk(GUN, 0));
}

test('cron: yeni ilan eşleşen aboneye kuyruk + yük\'süz VAPID push; eşleşmeyene yok', async () => {
  const c = await kur();
  c.aboneEkle(EP, 'lisans', 'Hukuk', 80);
  c.aboneEkle(EP2, 'lisans', 'Bilgisayar', 80);
  c.aboneEkle(EP3, 'ortaogretim', '', null);
  await yeniIlanTetikle(c, [ilan(0)], [ilan(1, { ogrenim: ['lisans'], metin: 'hukuk müşaviri alımı' })]);
  const bek = hepsi(c.raw, 'SELECT * FROM web_bekleyen ORDER BY endpoint');
  assert.equal(bek.length, 1);
  assert.equal(bek[0].endpoint, EP);
  assert.equal(bek[0].ilan_id, 'i1');
  assert.equal(bek[0].baslik, 'İlan 1');
  assert.equal(bek[0].url, 'https://site.test/ilan/1/'.replace('site.test', 'site.test'));
  assert.equal(c.pushlar.length, 1);
  const p = c.pushlar[0];
  assert.equal(p.url, EP);
  assert.equal(p.method, 'POST');
  assert.equal(p.body, undefined);
  assert.equal(p.headers.TTL, '86400');
  assert.equal(p.headers.Urgency, 'normal');
  const m = /^vapid t=([\w-]+)\.([\w-]+)\.([\w-]+), k=([\w-]+)$/.exec(p.headers.Authorization);
  assert.ok(m, p.headers.Authorization);
  assert.equal(m[4], c.anahtar.VAPID_ACIK);
  const baslik = JSON.parse(Buffer.from(m[1], 'base64url'));
  const yuk = JSON.parse(Buffer.from(m[2], 'base64url'));
  assert.deepEqual(baslik, { typ: 'JWT', alg: 'ES256' });
  assert.equal(yuk.aud, 'https://fcm.googleapis.com');
  assert.equal(yuk.sub, 'https://kpsstercihi.com');
  const sn = Math.floor(GUN.getTime() / 1000);
  assert.ok(yuk.exp > sn && yuk.exp - sn <= 12 * 3600);
  const acik = Buffer.from(c.anahtar.VAPID_ACIK, 'base64url');
  const anahtar = await crypto.subtle.importKey('raw', acik, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  const imza = Buffer.from(m[3], 'base64url');
  assert.equal(imza.length, 64);
  assert.ok(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, anahtar, imza, new TextEncoder().encode(`${m[1]}.${m[2]}`)));
  // iş bitti: meta anahtarları temiz
  assert.equal(say(c.raw, "SELECT COUNT(*) AS n FROM meta WHERE anahtar IN ('web_ilanlari','web_imleci')").n, 0);
});

test('cron: VAPID_IRTIBAT mailto olur; PKCS8 özel anahtar da kabul edilir; JWT aynı bildirim sahibi için önbellekten gelir', async () => {
  const c = await kur();
  c.env.VAPID_OZEL = c.anahtar.pkcs8;
  c.env.VAPID_IRTIBAT = 'iletisim@ornek.test';
  c.aboneEkle(EP, 'lisans', '', null);
  c.aboneEkle('https://fcm.googleapis.com/fcm/send/ikinci', 'lisans', '', null);
  await yeniIlanTetikle(c, [ilan(0)], [ilan(1)]);
  assert.equal(c.pushlar.length, 2);
  const [a, b] = c.pushlar.map((p) => /t=([^,]+),/.exec(p.headers.Authorization)[1]);
  assert.equal(a, b);
  assert.equal(JSON.parse(Buffer.from(a.split('.')[1], 'base64url')).sub, 'mailto:iletisim@ornek.test');
});

test('cron: 410 ve 404 aboneyi ve bekleyenlerini siler; 500 siler ama kuyruk kalır', async () => {
  const c = await kur();
  c.aboneEkle(EP, 'lisans', '', null);
  c.aboneEkle(EP2, 'lisans', '', null);
  c.aboneEkle(EP3, 'lisans', '', null);
  c.pushDurum[EP] = 410;
  c.pushDurum[EP2] = 404;
  c.pushDurum[EP3] = 500;
  await yeniIlanTetikle(c, [ilan(0)], [ilan(1)]);
  assert.deepEqual(hepsi(c.raw, 'SELECT endpoint FROM web_aboneler').map((r) => r.endpoint), [EP3]);
  assert.deepEqual(hepsi(c.raw, 'SELECT endpoint FROM web_bekleyen').map((r) => r.endpoint), [EP3]);
});

test('cron: anahtarlar yoksa web akışı sessizce atlanır, Telegram akışı bozulmaz', async () => {
  const c = await kur({ VAPID_OZEL: undefined });
  c.aboneEkle(EP, 'lisans', '', null);
  await yeniIlanTetikle(c, [ilan(0)], [ilan(1)]);
  assert.equal(c.pushlar.length, 0);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM web_bekleyen').n, 0);
  assert.equal(say(c.raw, "SELECT COUNT(*) AS n FROM meta WHERE anahtar = 'web_ilanlari'").n, 0);
  assert.ok(say(c.raw, "SELECT deger FROM meta WHERE anahtar = 'son_tarama'"));
});

test('cron: abone başına en çok 5 bekleyen; akademik/süresi geçmiş/puan yetmeyen ilan yazılmaz', async () => {
  const c = await kur();
  c.aboneEkle(EP, 'lisans', '', 60);
  const yeni = Array.from({ length: 8 }, (_, n) => ilan(n + 1));
  yeni.push(ilan(20, { kategori: 'akademik' }), ilan(21, { en_az_puan: 90 }), ilan(22, { son_tarih: '2026-09-01' }));
  await yeniIlanTetikle(c, [ilan(0)], yeni);
  const ids = hepsi(c.raw, 'SELECT ilan_id FROM web_bekleyen').map((r) => r.ilan_id);
  assert.equal(ids.length, 5);
  assert.ok(!ids.some((x) => ['i20', 'i21', 'i22'].includes(x)));
  assert.equal(c.pushlar.length, 1); // abone başına tek push
});

test('cron: 500 abone imleçle sayfalanır, her çağrı bütçe içinde, herkes tam bir kez push alır', async () => {
  const c = await kur();
  for (let n = 0; n < 250; n++) c.aboneEkle(`https://fcm.googleapis.com/fcm/send/${String(n).padStart(4, '0')}`, 'lisans', '', null);
  await yeniIlanTetikle(c, [ilan(0)], [ilan(1)]);
  let t = dk(GUN, 1);
  for (let n = 0; n < 40 && say(c.raw, "SELECT 1 AS x FROM meta WHERE anahtar = 'web_ilanlari'"); n++, t = dk(t, 1)) await c.calis(t);
  assert.equal(c.pushlar.length, 250);
  assert.equal(new Set(c.pushlar.map((p) => p.url)).size, 250);
  assert.ok(c.enCok.istek <= 30 && c.enCok.sql <= 40);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM web_bekleyen').n, 250);
});

test('cron: push için kalan istek bütçesi yoksa bekler, sonraki dakikada devam eder', async () => {
  const c = await kur();
  for (let n = 0; n < 5; n++) c.aboneEkle(`https://fcm.googleapis.com/fcm/send/${n}`, 'lisans', '', null);
  c.ilanlar = [ilan(0)];
  await c.calis(dk(GUN, -60));
  c.ilanlar = [ilan(0), ilan(1)];
  // Telegram kuyruğunu şişirip istek bütçesini bitir: 25 kullanıcı + ileti
  for (let k = 1; k <= 25; k++) {
    c.raw.prepare('INSERT INTO kullanicilar (chat_id, onay, olusturma, guncelleme) VALUES (?,1,?,?)').run(k, 'x', 'x');
    c.raw.prepare("INSERT INTO kuyruk (chat_id, ilan_id, tur) VALUES (?, 'i0', 'ilan')").run(k);
  }
  c.raw.prepare("INSERT OR IGNORE INTO bilinen_ilanlar (ilan_id, ana_id, son_tarih, veri, ilk_gorulme) VALUES ('i0','i0','2026-10-20',?, 'x')")
    .run(JSON.stringify({ baslik: 'İlan 0', kurum: 'K', son_tarih: '2026-10-20', sayfa: 'https://site.test/ilan/0/' }));
  await c.calis(dk(GUN, 0));
  assert.ok(c.istek >= 0);
  let t = dk(GUN, 1);
  for (let n = 0; n < 10 && say(c.raw, "SELECT 1 AS x FROM meta WHERE anahtar = 'web_ilanlari'"); n++, t = dk(t, 1)) await c.calis(t);
  assert.equal(c.pushlar.length, 5);
});
