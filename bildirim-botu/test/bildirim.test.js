import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ilanMesaji, hatirlatmaMesaji, acikIlanOzeti, cronCalistir } from '../src/bildirim.js';
import { sponsorSec } from '../src/sponsor.js';
import { sahteDB, kullaniciEkle, say, hepsi } from './sahte-c.js';

process.removeAllListeners('warning');

const SITE = 'https://site.test/';
const GUN = new Date('2026-10-01T09:00:00Z'); // İstanbul 12:00, gündüz
const GECE = new Date('2026-09-30T20:30:00Z'); // İstanbul 23:30 (GUN'den önce), boşaltma yok
const dk = (d, m) => new Date(d.getTime() + m * 60000);

const ilan = (n, ek = {}) => ({
  id: `i${n}`, kimlikler: [`i${n}`], baslik: `İlan ${n}`, kurum: 'Kurum', son_tarih: '2026-10-20', son_zaman: null,
  ogrenim: [], iller: [], kategori: null, kpss: null, duyuru_turu: null, sayfa: `https://site.test/ilan/${n}/`, metin: `ilan ${n} kurum`, ...ek,
});

function kur() {
  const d = sahteDB();
  const c = {
    ...d, ilanlar: [], gonderilen: [], tarama: 0, secenekler: [], istek: 0, hatalar: {}, ozel: null, enCok: { sql: 0, istek: 0, cift: 0 },
    env: { DB: d.DB, ILAN_URL: 'https://x/bot-ilanlar.json', SITE_URL: SITE },
  };
  c.bag = {
    bekle: async () => {},
    fetch: async (u) => {
      c.istek++;
      if (String(u).endsWith('gunluk.json')) return { ok: false, status: 404, json: async () => ({}) }; // sosyal paylaşım dosyası yok
      c.tarama++;
      return { ok: true, status: 200, json: async () => ({ ilanlar: c.ilanlar }) }; },
    tg: async (e, method, p, secenek) => {
      c.istek++;
      c.secenekler.push(secenek);
      const hata = c.hatalar[p.chat_id];
      if (hata) { const x = new Error('h'); x.kod = hata; throw x; }
      if (c.ozel) c.ozel(p);
      c.gonderilen.push(p);
      return {};
    },
  };
  c.calis = async (simdi) => {
    const once = { sql: c.sayac.sql, istek: c.istek };
    const s = await cronCalistir(c.env, simdi, c.bag);
    const harcanan = { sql: c.sayac.sql - once.sql, istek: c.istek - once.istek };
    assert.ok(harcanan.sql <= 40, `ifade sayısı ${harcanan.sql} > 40`);
    assert.ok(harcanan.istek <= 30, `istek sayısı ${harcanan.istek} > 30`);
    assert.equal(s.sql, harcanan.sql);
    assert.equal(s.istek, harcanan.istek);
    assert.ok(s.cift <= 2000, `çift sayısı ${s.cift} > 2000`);
    c.enCok = { sql: Math.max(c.enCok.sql, harcanan.sql), istek: Math.max(c.enCok.istek, harcanan.istek), cift: Math.max(c.enCok.cift, s.cift) };
    return s;
  };
  return c;
}
const kuyruk = (c) => hepsi(c.raw, 'SELECT * FROM kuyruk ORDER BY id');

test('ilk çalıştırma: 192 ilan bile ≤40 ifade, kuyruk yok; hemen sonra tarama yok', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = Array.from({ length: 192 }, (_, n) => ilan(n, { kimlikler: [`i${n}`, `eski${n}`] }));
  const s = await c.calis(GUN);
  assert.equal(kuyruk(c).length, 0);
  assert.equal(c.gonderilen.length, 0);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM bilinen_ilanlar').n, 384);
  assert.ok(say(c.raw, "SELECT deger FROM meta WHERE anahtar = 'son_tarama'"));
  assert.equal(say(c.raw, "SELECT COUNT(*) AS n FROM meta WHERE anahtar IN ('ilk_ofset','tarama_imleci')").n, 0);
  assert.equal(s.yeni, 0);
  const onceki = c.tarama;
  await c.calis(dk(GUN, 5));
  assert.equal(c.tarama, onceki); // 30 dk dolmadan fetch yok
});

test('çok büyük ilk liste (100 KB JSON sınırı aşılır) bütçe içinde kalır, kimseye kuyruk yazmaz', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = Array.from({ length: 900 }, (_, n) => ilan(n, { baslik: 'B'.repeat(600) }));
  let t = GUN; let cagri = 0;
  while (!say(c.raw, "SELECT 1 AS x FROM meta WHERE anahtar = 'son_tarama'")) { await c.calis(t); t = dk(t, 1); if (++cagri > 20) assert.fail('bitmedi'); }
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM bilinen_ilanlar').n, 900);
  assert.equal(kuyruk(c).length, 0);
});

test('300 kullanıcıda imleçli tarama çok çağrıya bölünür; herkes her ilanı tam bir kez alır', async () => {
  const c = kur();
  for (let k = 1; k <= 300; k++) kullaniciEkle(c.raw, k);
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ...Array.from({ length: 10 }, (_, n) => ilan(n + 1))];
  let t = dk(GECE, 31); let cagri = 0;
  for (;;) {
    await c.calis(t); t = dk(t, 1); cagri++;
    if (!say(c.raw, "SELECT 1 AS x FROM meta WHERE anahtar = 'tarama_imleci'")) break;
    assert.ok(cagri < 30);
  }
  assert.ok(cagri > 1, 'tek çağrıda bitti');
  const satirlar = kuyruk(c);
  assert.equal(satirlar.length, 3000);
  assert.equal(new Set(satirlar.map((r) => `${r.chat_id}|${r.ilan_id}`)).size, 3000);
  // Gündüz boşaltma: herkes her ilanı bir kez alır
  let g = GUN; let n = 0;
  while (kuyruk(c).length && n++ < 400) { await c.calis(g); g = dk(g, 1); }
  assert.equal(c.gonderilen.length, 3000);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM gonderilen').n, 3000);
});

test('kullanıcı başına 10 sınırı + tek "fazla" satırı', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ...Array.from({ length: 13 }, (_, n) => ilan(n + 1))];
  await c.calis(dk(GECE, 31));
  const s = kuyruk(c);
  assert.equal(s.filter((r) => r.tur === 'ilan').length, 10);
  const f = s.filter((r) => r.tur === 'fazla');
  assert.equal(f.length, 1);
  assert.equal(f[0].ilan_id, '+3');
  let g = GUN; let n = 0;
  while (kuyruk(c).length && n++ < 20) { await c.calis(g); g = dk(g, 1); }
  assert.equal(c.gonderilen.length, 11); // çağrı başına sohbete en çok 1 ileti
  assert.match(c.gonderilen.at(-1).text, /^\+3 ilan daha: https:\/\/site\.test\//);
});

test('yeni ilan yalnız uygun kullanıcıya gider; uygun olmayan ve onaysız almaz', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2, { iller: '["İzmir"]' }); kullaniciEkle(c.raw, 3, { onay: 0 });
  c.ilanlar = [ilan(0)];
  await c.calis(GUN);
  c.ilanlar = [ilan(0), ilan(1, { iller: ['Ankara'] })];
  await c.calis(dk(GUN, 31)); // tarama
  await c.calis(dk(GUN, 32)); // boşaltma
  assert.deepEqual(c.gonderilen.map((g) => g.chat_id), [1]);
  assert.match(c.gonderilen[0].text, /İlan 1/);
  await c.calis(dk(GUN, 70));
  assert.equal(c.gonderilen.length, 1);
});

test('kimlik değişimi: bilinen kimlik varsa ilan yeni değil, yeni kimlik aynı ana_id ile eklenir', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = [ilan(1)];
  await c.calis(GECE);
  c.ilanlar = [ilan(1, { id: 'yeni1', kimlikler: ['yeni1', 'i1'], son_tarih: '2026-10-25' })];
  const s = await c.calis(dk(GECE, 31));
  assert.equal(s.yeni, 0);
  assert.equal(kuyruk(c).length, 0);
  const r = hepsi(c.raw, 'SELECT ilan_id, ana_id, son_tarih FROM bilinen_ilanlar ORDER BY ilan_id');
  assert.deepEqual(r.map((x) => [x.ilan_id, x.ana_id]), [['i1', 'i1'], ['yeni1', 'i1']]);
  assert.equal(r.find((x) => x.ilan_id === 'i1').son_tarih, '2026-10-25');
  await c.calis(dk(GECE, 70));
  assert.equal(kuyruk(c).length, 0);
});

test('gece boşaltma yok, gündüz var', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ilan(1)];
  await c.calis(dk(GECE, 31));
  assert.equal(kuyruk(c).length, 1);
  await c.calis(dk(GECE, 32));
  assert.equal(c.gonderilen.length, 0);
  assert.equal(kuyruk(c).length, 1);
  const sabah = new Date('2026-10-02T05:00:00Z'); // 08:00 İstanbul
  await c.calis(sabah);
  assert.equal(c.gonderilen.length, 1);
  assert.equal(kuyruk(c).length, 0);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM gonderilen').n, 1);
});

async function birKuyrukSatiri(c, chat = 1) {
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ilan(1)];
  await c.calis(dk(GECE, 31));
  assert.equal(kuyruk(c).filter((r) => r.chat_id === chat).length, 1);
}

test('429: satır kuyrukta kalır ve gönderim durur; 5xx kuyrukta kalır', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2);
  await birKuyrukSatiri(c);
  c.hatalar = { 1: 429 };
  const s = await c.calis(GUN);
  assert.equal(kuyruk(c).length, 2);
  assert.equal(c.gonderilen.length, 0); // 429 sonrası durdu, 2. kullanıcıya gönderilmedi
  assert.equal(s.hata, 1);
  c.hatalar = { 1: 502 };
  await c.calis(dk(GUN, 1));
  assert.equal(kuyruk(c).filter((r) => r.chat_id === 1).length, 1);
  assert.equal(kuyruk(c).filter((r) => r.chat_id === 2).length, 0);
  c.hatalar = {};
  await c.calis(dk(GUN, 2));
  assert.equal(kuyruk(c).length, 0);
});

test('400: satır silinir, gonderilen yazılmaz', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  await birKuyrukSatiri(c);
  c.hatalar = { 1: 400 };
  await c.calis(GUN);
  assert.equal(kuyruk(c).length, 0);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM gonderilen').n, 0);
});

test('403: kullanıcı aktif=0, kuyruğu temizlenir; diğeri etkilenmez', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2);
  await birKuyrukSatiri(c);
  c.hatalar = { 1: 403 };
  await c.calis(GUN);
  assert.equal(say(c.raw, 'SELECT aktif FROM kullanicilar WHERE chat_id = 1').aktif, 0);
  assert.equal(say(c.raw, 'SELECT aktif FROM kullanicilar WHERE chat_id = 2').aktif, 1);
  assert.equal(kuyruk(c).length, 0);
  assert.deepEqual(c.gonderilen.map((g) => g.chat_id), [2]);
});

test('hatırlatma günde bir kez; bugün gönderilen ilana gitmez', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2, { hatirlatma: 0 });
  const ekle = (id, son, zaman) => {
    c.raw.prepare('INSERT INTO bilinen_ilanlar (ilan_id, ana_id, son_tarih, veri, ilk_gorulme) VALUES (?,?,?,?,?)')
      .run(id, id, son, JSON.stringify({ baslik: `B ${id}`, kurum: 'K', son_tarih: son, sayfa: 'https://s.test/x/' }), 'x');
    for (const k of [1, 2]) c.raw.prepare('INSERT INTO gonderilen (chat_id, ilan_id, zaman) VALUES (?,?,?)').run(k, id, zaman);
  };
  ekle('dun', '2026-10-02', '2026-09-30T10:00:00.000Z'); // dün gönderildi, yarın bitiyor
  ekle('bugun', '2026-10-02', '2026-10-01T05:00:00.000Z'); // bugün gönderildi
  ekle('uzak', '2026-10-09', '2026-09-30T10:00:00.000Z');
  c.ilanlar = [];
  await c.calis(GUN); // tarama + hatırlatma kuyruğa
  const k = kuyruk(c);
  assert.deepEqual(k.map((r) => [r.chat_id, r.ilan_id, r.tur]), [[1, 'dun', 'hatirlatma']]);
  await c.calis(dk(GUN, 1));
  assert.equal(c.gonderilen.length, 1);
  assert.match(c.gonderilen[0].text, /Yarın son gün.*B dun/);
  assert.equal(say(c.raw, "SELECT hatirlatildi FROM gonderilen WHERE chat_id=1 AND ilan_id='dun'").hatirlatildi, 1);
  await c.calis(dk(GUN, 120));
  await c.calis(dk(GUN, 240));
  assert.equal(c.gonderilen.length, 1);
  assert.equal(kuyruk(c).length, 0);
});

test('duyuru etiketi ve son_zaman geçmiş ilan gönderilmez', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [
    ilan(0),
    ilan(1, { duyuru_turu: 'İptal duyurusu' }),
    ilan(2, { duyuru_turu: 'Düzeltme / süre değişikliği' }),
    ilan(3, { son_tarih: '2026-10-01', son_zaman: '2026-10-01T10:00:00+03:00' }), // 10:00 İstanbul geçti (12:00)
    ilan(4, { son_tarih: null }),
  ];
  await c.calis(GUN); // tarama
  const sira = hepsi(c.raw, 'SELECT ilan_id FROM kuyruk ORDER BY id').map((r) => r.ilan_id);
  assert.deepEqual(sira, ['i1', 'i2', 'i4']); // i3 kuyruğa girmedi
  for (let m = 1; m <= 3; m++) await c.calis(dk(GUN, m)); // sohbet başına dakikada 1 ileti
  const metinler = c.gonderilen.map((g) => g.text);
  assert.ok(metinler[0].startsWith('⚠️ İptal duyurusu: <b>İlan 1</b>'));
  assert.ok(metinler[1].startsWith('📝 Düzeltme / süre değişikliği: <b>İlan 2</b>'));
  assert.ok(!metinler[2].includes('Son başvuru'));
  // Kuyrukta beklerken süresi dolan ilan gönderim anında atlanır
  c.raw.prepare("INSERT INTO kuyruk (chat_id, ilan_id, tur) VALUES (1, 'i3', 'ilan')").run();
  c.raw.prepare("INSERT OR REPLACE INTO bilinen_ilanlar (ilan_id, ana_id, son_tarih, veri, ilk_gorulme) VALUES ('i3','i3','2026-10-01',?, 'x')")
    .run(JSON.stringify({ baslik: 'x', son_tarih: '2026-10-01', son_zaman: '2026-10-01T10:00:00+03:00', sayfa: 'https://s.test/' }));
  const once = c.gonderilen.length;
  await c.calis(dk(GUN, 5));
  assert.equal(c.gonderilen.length, once);
  assert.equal(kuyruk(c).length, 0);
});

test('sponsorlar boşaltma başına bir kez okunur, sponsor ileti sonuna eklenir', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2);
  c.raw.prepare("INSERT INTO sponsorlar (metin, link, baslangic, bitis) VALUES ('Kurs', 'https://s.test', '2026-09-01', '2026-12-01')").run();
  await birKuyrukSatiri(c);
  let sponsorOkuma = 0;
  const asil = c.env.DB.prepare.bind(c.env.DB);
  c.env.DB.prepare = (q) => { if (q.includes('FROM sponsorlar')) sponsorOkuma++; return asil(q); };
  await c.calis(GUN);
  assert.equal(sponsorOkuma, 1);
  assert.equal(c.gonderilen.length, 2);
  assert.ok(c.gonderilen[0].text.endsWith('— Sponsorlu: <a href="https://s.test">Kurs</a>'));
});

test('HTML kaçışı ve sponsor linki yalnız https', () => {
  const env = { SITE_URL: SITE };
  const m = ilanMesaji(ilan(1, { baslik: 'A <b>&</b> "x"', kurum: 'K & <i>L</i>', iller: ['<Ankara>'] }), { metin: 'S <u>', link: 'https://s.test/?a=1&b="2"' }, env);
  assert.ok(m.text.includes('<b>A &lt;b&gt;&amp;&lt;/b&gt; "x"</b>'));
  assert.ok(m.text.includes('K &amp; &lt;i&gt;L&lt;/i&gt;'));
  assert.ok(m.text.includes('&lt;Ankara&gt;'));
  assert.ok(m.text.includes('S &lt;u&gt;'));
  assert.ok(m.text.includes('href="https://s.test/?a=1&amp;b=&quot;2&quot;"'));
  assert.equal(m.parse_mode, 'HTML');
  assert.equal(m.link_preview_options.is_disabled, true);
  const http = ilanMesaji(ilan(1), { metin: 'S', link: 'http://s.test' }, env);
  assert.ok(http.text.endsWith('— Sponsorlu: S'));
  const js = ilanMesaji(ilan(1), { metin: 'S', link: 'javascript:alert(1)' }, env);
  assert.ok(!js.text.includes('javascript'));
  assert.ok(hatirlatmaMesaji(ilan(1, { baslik: '<x>' }), env).text.includes('&lt;x&gt;'));
});

test('sponsor yokken sponsor satırı yok; tarih gg.aa.yyyy; sayfa bağlantısı kullanılır', () => {
  const env = { SITE_URL: SITE };
  const yok = ilanMesaji(ilan(1, { iller: ['Ankara'] }), null, env);
  assert.ok(!yok.text.includes('Sponsorlu'));
  assert.ok(yok.text.includes('20.10.2026'));
  assert.ok(yok.text.includes('Ankara'));
  assert.ok(yok.text.includes('href="https://site.test/ilan/1/"'));
});

test('sponsor hedefleme: tarih, aktiflik, eşleşme ve en spesifik tercih', async () => {
  const sp = (id, ek) => ({ id, metin: `S${id}`, link: null, duzey: null, il: null, kategori: null, baslangic: '2026-09-01', bitis: '2026-12-01', aktif: 1, ...ek });
  const { DB, raw } = sahteDB();
  const ekle = (s) => raw.prepare('INSERT INTO sponsorlar (id, metin, link, duzey, il, kategori, baslangic, bitis, aktif) VALUES (?,?,?,?,?,?,?,?,?)')
    .run(s.id, s.metin, s.link, s.duzey, s.il, s.kategori, s.baslangic, s.bitis, s.aktif);
  [sp(1, {}), sp(2, { il: 'Ankara' }), sp(3, { il: 'Ankara', kategori: 'bilisim' }), sp(4, { il: 'İzmir' }),
    sp(5, { aktif: 0, il: 'Ankara', kategori: 'bilisim', duzey: 'lisans' }), sp(6, { bitis: '2026-09-15', il: 'Ankara', kategori: 'bilisim', duzey: 'lisans' })].forEach(ekle);
  const env = { DB };
  const u = { duzeyler: [], iller: [], kategoriler: [] };
  assert.equal((await sponsorSec(env, u, ilan(1, { iller: ['Ankara'], kategori: 'bilisim' }), '2026-10-01')).metin, 'S3');
  assert.equal((await sponsorSec(env, u, ilan(1, { iller: ['Ankara'] }), '2026-10-01')).metin, 'S2');
  assert.equal((await sponsorSec(env, u, ilan(1, { iller: ['Van'] }), '2026-10-01')).metin, 'S1');
  assert.equal((await sponsorSec(env, { ...u, iller: ['İzmir'] }, ilan(1), '2026-10-01')).metin, 'S4');
  const bos = sahteDB();
  assert.equal(await sponsorSec({ DB: bos.DB }, u, ilan(1), '2026-10-01'), null);
  const hedefli = sahteDB();
  hedefli.raw.prepare("INSERT INTO sponsorlar (metin, il, baslangic, bitis) VALUES ('H','Ankara','2026-09-01','2026-12-01')").run();
  assert.equal(await sponsorSec({ DB: hedefli.DB }, u, ilan(1, { iller: ['Van'] }), '2026-10-01'), null);
});

test('acikIlanOzeti: sayı, en yakın 5, tarihsiz sona ("tarih yok"), HTML kaçış, uygun yoksa nazik metin', async () => {
  const ilanlar = Array.from({ length: 7 }, (_, n) => ilan(n + 1, { son_tarih: `2026-10-${String(20 - n).padStart(2, '0')}` }));
  ilanlar.push(ilan(98, { kategori: 'akademik' }), ilan(97, { baslik: 'Z <b>&', son_tarih: null }), ilan(99, { son_tarih: '2026-09-01' }));
  const env = { ILAN_URL: 'x', SITE_URL: SITE };
  const bag = { fetch: async () => ({ ok: true, json: async () => ({ ilanlar }) }) };
  const k = { duzeyler: [], iller: [], kategoriler: [], kelimeler: [], akademik: 0 };
  const o = await acikIlanOzeti(env, k, bag, GUN);
  assert.match(o, /8 açık ilan/);
  assert.ok(o.includes('İlan 7 — 14.10.2026'));
  assert.ok(!o.includes('İlan 1 — 20.10.2026')); // ilk 5 dışında
  assert.ok(!o.includes('İlan 99') && !o.includes('İlan 98'));
  const sadece = await acikIlanOzeti(env, k, { fetch: async () => ({ ok: true, json: async () => ({ ilanlar: [ilanlar[0], ilanlar[8]] }) }) }, GUN);
  assert.ok(sadece.indexOf('İlan 1') < sadece.indexOf('Z &lt;b&gt;&amp; — tarih yok'));
  assert.ok(o.includes(SITE));
  const bos = await acikIlanOzeti(env, { ...k, kelimeler: ['yokböylebirşey'] }, bag, GUN);
  assert.match(bos, /uyan açık ilan görünmüyor/);
});



test('gerçekçi yük: 200 kullanıcı × 170 yeni ilan, çağrı başına ≤2000 çift, tarama birden çok çağrıda biter', async () => {
  const c = kur();
  for (let k = 1; k <= 200; k++) kullaniciEkle(c.raw, k, k % 3 === 0 ? { kelimeler: '["Kurum","hukuk"]' } : {});
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ...Array.from({ length: 170 }, (_, n) => ilan(n + 1, { metin: `ilan ${n + 1} kurum hukuk bilişim` }))];
  let t = dk(GECE, 31); let cagri = 0; let toplamCift = 0;
  const bas = performance.now();
  for (;;) {
    const s = await c.calis(t); t = dk(t, 1); cagri++; toplamCift += s.cift;
    if (!say(c.raw, "SELECT 1 AS x FROM meta WHERE anahtar = 'tarama_imleci'")) break;
    assert.ok(cagri < 60);
  }
  const ms = performance.now() - bas;
  console.log(`  [bilgi] ${cagri} çağrı, ${toplamCift} çift, toplam ${ms.toFixed(0)} ms (çağrı başına ~${(ms / cagri).toFixed(1)} ms, DB dahil)`);
  assert.ok(cagri > 1);
  assert.equal(toplamCift, 200 * 170);
  const satirlar = kuyruk(c);
  assert.equal(satirlar.length, 200 * 11); // 10 ilan + 1 fazla
  assert.equal(new Set(satirlar.map((r) => r.chat_id)).size, 200);
});

test('Y-2: tg yeniden denemesiz çağrılır; sohbet başına çağrıda 1 ileti', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ilan(1), ilan(2), ilan(3)];
  await c.calis(dk(GECE, 31));
  assert.equal(kuyruk(c).length, 3);
  await c.calis(GUN);
  assert.equal(c.gonderilen.length, 1);
  assert.equal(kuyruk(c).length, 2);
  assert.ok(c.secenekler.length > 0 && c.secenekler.every((s) => s && s.yeniden === false));
});

test('Y-2: kilit — başka çağrı çalışıyorsa hiçbir şey yapılmaz; bitince kilit bırakılır; süresi dolan kilit aşılır', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1);
  c.ilanlar = [ilan(0)];
  c.raw.prepare("INSERT INTO meta (anahtar, deger) VALUES ('kilit', ?)").run(String(GUN.getTime() + 30000));
  const s = await cronCalistir(c.env, GUN, c.bag);
  assert.equal(s.kilitli, true);
  assert.equal(c.istek, 0);
  assert.equal(say(c.raw, 'SELECT COUNT(*) AS n FROM bilinen_ilanlar').n, 0);
  await c.calis(dk(GUN, 1)); // kilit süresi (55 sn değil, 30 sn) doldu
  assert.equal(say(c.raw, "SELECT deger FROM meta WHERE anahtar = 'kilit'").deger, '0');
  assert.ok(say(c.raw, 'SELECT COUNT(*) AS n FROM bilinen_ilanlar').n > 0);
});

test('Y-2: hata fırlasa da kilit bırakılır', async () => {
  const c = kur();
  c.env.ILAN_URL = 'x';
  c.bag.fetch = async () => { throw new Error('ağ'); };
  const s = await cronCalistir(c.env, GUN, c.bag);
  assert.equal(s.hata, 1);
  assert.equal(say(c.raw, "SELECT deger FROM meta WHERE anahtar = 'kilit'").deger, '0');
});

test('O-4: pasif/onaysız kullanıcıların kuyruk satırları gönderilmeden silinir', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1, { aktif: 0 }); kullaniciEkle(c.raw, 2, { onay: 0 }); kullaniciEkle(c.raw, 3);
  c.raw.prepare("INSERT INTO bilinen_ilanlar (ilan_id, ana_id, son_tarih, veri, ilk_gorulme) VALUES ('a','a','2026-10-20',?, 'x')")
    .run(JSON.stringify({ baslik: 'A', sayfa: 'https://s.test/', son_tarih: '2026-10-20' }));
  for (const k of [1, 2, 3, 99]) c.raw.prepare("INSERT INTO kuyruk (chat_id, ilan_id, tur) VALUES (?, 'a', 'ilan')").run(k);
  c.ilanlar = [];
  await c.calis(GUN);
  assert.deepEqual(c.gonderilen.map((g) => g.chat_id), [3]);
  assert.equal(kuyruk(c).length, 0);
});

test('D-6: günlük en çok 15 ilan iletisi (bugünkü gönderilen + bekleyen sayılır), fazlası tek satır', async () => {
  const c = kur();
  kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2);
  const bugunZaman = '2026-10-01T05:00:00.000Z';
  for (let n = 0; n < 12; n++) c.raw.prepare('INSERT INTO gonderilen (chat_id, ilan_id, zaman) VALUES (1, ?, ?)').run(`eski${n}`, bugunZaman);
  for (let n = 0; n < 12; n++) c.raw.prepare('INSERT INTO gonderilen (chat_id, ilan_id, zaman) VALUES (2, ?, ?)').run(`dun${n}`, '2026-09-29T05:00:00.000Z'); // dün: sayılmaz
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(0), ...Array.from({ length: 10 }, (_, n) => ilan(n + 1))];
  await c.calis(GUN);
  const k1 = kuyruk(c).filter((r) => r.chat_id === 1);
  assert.equal(k1.filter((r) => r.tur === 'ilan').length, 3);
  assert.equal(k1.find((r) => r.tur === 'fazla').ilan_id, '+7');
  assert.equal(kuyruk(c).filter((r) => r.chat_id === 2 && r.tur === 'ilan').length, 10);
});

test('D-9: devam yolunda ilan kimliği değişse de eşleme kimlikler üzerinden yapılır, kuyruğa ana kimlik yazılır', async () => {
  const c = kur();
  for (let k = 1; k <= 3; k++) kullaniciEkle(c.raw, k);
  c.ilanlar = [ilan(0)];
  await c.calis(GECE);
  c.ilanlar = [ilan(1)];
  // Taramayı başlat ama bitirme: imleci elle geri al
  await c.calis(dk(GECE, 31));
  assert.equal(kuyruk(c).length, 3);
  c.raw.exec("DELETE FROM kuyruk; INSERT OR REPLACE INTO meta VALUES ('tarama_imleci','1'), ('tarama_ilanlari','[\"i1\"]');");
  c.ilanlar = [ilan(1, { id: 'yeni1', kimlikler: ['yeni1', 'i1'] })];
  await c.calis(dk(GECE, 32));
  assert.deepEqual(kuyruk(c).map((r) => [r.chat_id, r.ilan_id]), [[2, 'i1'], [3, 'i1']]);
});

test('401/404 token hatası: gönderim durur, satırlar kalır, tokenHatasi döner; 400 yine silinir', async () => {
  for (const kod of [401, 404]) {
    const c = kur();
    kullaniciEkle(c.raw, 1); kullaniciEkle(c.raw, 2);
    await birKuyrukSatiri(c);
    c.hatalar = { 1: kod };
    const hataLog = console.error; let logMetni = '';
    console.error = (...a) => { logMetni += a.join(' '); };
    let s;
    try { s = await c.calis(GUN); } finally { console.error = hataLog; }
    assert.equal(s.tokenHatasi, true);
    assert.equal(logMetni, 'Telegram token reddedildi');
    assert.equal(kuyruk(c).length, 2);
    assert.equal(c.gonderilen.length, 0);
  }
});
