import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import {
  butceSarmala, butceHazirla, butceOku, butceSifirla, butceSaatAyarla, butceOzeti, yazmaKademesi, okumaKademesi, olaylariSuz, utcGun,
} from '../src/butce.js';
import { topla, sayacSifirla, hizSifirla } from '../src/toplama.js';
import { populerIstegi, populerBellekSifirla } from '../src/populer.js';
import { panelIstegi, oturumCerezi, COOKIE } from '../src/panel.js';
import { bakim } from '../src/bakim.js';
import { bellekSifirla } from '../src/onbellek.js';
import { sahteD1, istek, paket } from './sahte-d1.js';

const T0 = Date.parse('2026-10-08T09:00:00Z');
let simdi = T0;
const yeni = (ek = {}) => {
  butceSifirla(); sayacSifirla(); hizSifirla(); bellekSifirla(); populerBellekSifirla();
  simdi = T0; butceSaatAyarla(() => simdi);
  return butceSarmala({ DB: sahteD1(), ...ek });
};
const satir = (e, gun = '2026-10-08') => e.DB._db.ham.prepare('SELECT yazma, okuma FROM butce WHERE gun_utc = ?').get(gun);
const toplamKaydet = (e, y, o, gun = '2026-10-08') => e.DB._db.ham.prepare('INSERT OR REPLACE INTO butce VALUES (?, ?, ?)').run(gun, y, o);
const gonder = (e, olaylar, ek = {}) => topla(istek(paket(olaylar), { ip: '203.0.113.' + (ek.ip || 7) }), e, simdi);
const sayOlay = (e, t) => e.DB._db.ham.prepare('SELECT COUNT(*) AS n FROM olaylar WHERE t = ?').get(t).n;
const OLAYLAR = [
  { t: 'sayfa', p: '/', f: 1 }, { t: 'aktif', p: '/', n: 30 }, { t: 'kaydirma', p: '/', n: 50 }, { t: 'hiz', p: '/', n: 1000, n2: 100 },
  { t: 'tikla', p: '/', a: 'resmi_ilan', h: 'X1' }, { t: 'tikla', p: '/', a: 'filtre', h: 'f', x: 'v' }, { t: 'hata', p: '/', x: 'boom' }, { t: '404', p: '/yok' },
];
const hedefler = (e) => e.DB._db.ham.prepare('SELECT t, a FROM olaylar ORDER BY id').all().map((r) => r.t + (r.a ? ':' + r.a : ''));

test('kademe eşikleri: yazma 40k/55k/60k, okuma 2,5M/3M ve ortam değişkeniyle ayarlanır', () => {
  assert.deepEqual([0, 39999, 40000, 54999, 55000, 59999, 60000, 99999].map((y) => yazmaKademesi(y, 60000)), [0, 0, 1, 1, 2, 2, 3, 3]);
  assert.deepEqual([0, 2499999, 2500000, 2999999, 3000000].map((o) => okumaKademesi(o, 3000000)), [0, 0, 1, 1, 2]);
  assert.equal(yazmaKademesi(20000, 30000), 1); // BUTCE_YAZMA=30000 -> eşik 20k
  const e = yeni({ BUTCE_YAZMA: '30000', BUTCE_OKUMA: '1000' });
  toplamKaydet(e, 20000, 1000);
  return butceHazirla(e, simdi).then(() => {
    const b = butceOku(e, simdi);
    assert.equal(b.yazmaKademesi, 1); assert.equal(b.okumaKademesi, 2); assert.equal(b.sinirYazma, 30000);
  });
});

test('olaylariSuz: kademe 1 aktif/kaydirma/hiz atar, kademe 2 yalnız sayfa + 4 tıklama, kademe 3 hiçbiri', () => {
  const t = (k) => olaylariSuz(OLAYLAR, k).map((x) => x.t + (x.a ? ':' + x.a : ''));
  assert.equal(t(0).length, 8);
  assert.deepEqual(t(1), ['sayfa', 'tikla:resmi_ilan', 'tikla:filtre', 'hata', '404']);
  assert.deepEqual(t(2), ['sayfa', 'tikla:resmi_ilan']);
  assert.deepEqual(t(3), []);
});

test('POST /o kademelere göre: normal, 40k, 55k, 60k+ (204, yazım yok)', async () => {
  const e = yeni();
  await gonder(e, OLAYLAR);
  assert.equal(sayOlay(e, 'aktif'), 1);
  assert.equal(sayOlay(e, 'hiz'), 1);

  const k1 = yeni(); toplamKaydet(k1, 40000, 0); await gonder(k1, OLAYLAR);
  assert.deepEqual(hedefler(k1), ['sayfa', 'tikla:resmi_ilan', 'tikla:filtre', 'hata', '404']);

  const k2 = yeni(); toplamKaydet(k2, 55000, 0); await gonder(k2, OLAYLAR);
  assert.deepEqual(hedefler(k2), ['sayfa', 'tikla:resmi_ilan']);

  const k3 = yeni(); toplamKaydet(k3, 60000, 0);
  const r = await gonder(k3, OLAYLAR);
  assert.equal(r.status, 204);
  assert.equal(hedefler(k3).length, 0);
  assert.equal(k3.DB._db.sayac.batch, 1, 'yalnız bütçe okuma batch\'i; olay yazımı yok');
});

test('sayaç: rows_written izolat belleğinde birikir, eşik aşılınca aynı izolatta kademe yükselir', async () => {
  const e = yeni({ BUTCE_YAZMA: '40' }); // eşikler 26 / 37 / 40
  await gonder(e, [{ t: 'sayfa', p: '/', f: 1 }]);
  const b1 = butceOku(e, simdi);
  assert.ok(b1.yazma >= 1 && b1.yazma < 26 && b1.yazmaKademesi === 0, 'bütçe kullanıldı: ' + b1.yazma);
  // Bütçenin kalanını yerel sayaca işleyen bir yazma (tuz INSERT'ü dahil sayılır)
  for (let i = 0; i < 40; i++) await e.DB.prepare('INSERT INTO tuz (gun, tuz) VALUES (?, ?)').bind('g' + i, 'x').run();
  assert.equal(butceOku(e, simdi).yazmaKademesi, 3);
  const r = await gonder(e, [{ t: 'sayfa', p: '/', f: 1 }], { ip: 9 });
  assert.equal(r.status, 204);
  assert.equal(sayOlay(e, 'sayfa'), 1, 'limitte durdu');
});

test('flush kısıtlaması: en çok dakikada bir UPSERT ve bir okuma; bekleyen harcama kaybolmaz', async () => {
  const e = yeni();
  await e.DB.prepare('INSERT INTO tuz (gun, tuz) VALUES (?, ?)').bind('a', 'x').run(); // 1 yazma
  await butceHazirla(e, simdi);
  const bat1 = e.DB._db.sayac.batch;
  assert.equal(satir(e).yazma, 1);
  await e.DB.prepare('INSERT INTO tuz (gun, tuz) VALUES (?, ?)').bind('b', 'x').run();
  simdi += 30_000; await butceHazirla(e, simdi); await butceHazirla(e, simdi);
  assert.equal(e.DB._db.sayac.batch, bat1, '60 sn dolmadan D1\'e gidilmez');
  assert.equal(satir(e).yazma, 1);
  assert.ok(butceOku(e, simdi).yazma >= 2, 'ama bellekteki tahmin güncel');
  simdi += 31_000; await butceHazirla(e, simdi);
  assert.equal(e.DB._db.sayac.batch, bat1 + 1);
  assert.ok(satir(e).yazma >= 2);
});

test('başka izolatın yazımı hesap toplamına dakikada bir yansır', async () => {
  const e = yeni();
  await butceHazirla(e, simdi);
  toplamKaydet(e, 41000, 0); // başka izolat yazdı
  assert.equal(butceOku(e, simdi).yazmaKademesi, 0);
  simdi += 61_000; await butceHazirla(e, simdi);
  assert.equal(butceOku(e, simdi).yazmaKademesi, 1);
});

test('UTC gün dönüşü: sayaçlar sıfırlanır, eski gün kendi satırına yazılır', async () => {
  const e = yeni();
  simdi = Date.parse('2026-10-08T23:59:00Z');
  toplamKaydet(e, 61000, 0);
  await butceHazirla(e, simdi);
  assert.equal(butceOku(e, simdi).yazmaKademesi, 3);
  await e.DB.prepare('INSERT INTO tuz (gun, tuz) VALUES (?, ?)').bind('z', 'x').run();
  simdi = Date.parse('2026-10-09T00:00:30Z');
  assert.equal(utcGun(simdi), '2026-10-09');
  assert.equal(butceOku(e, simdi).yazmaKademesi, 0, 'yeni gün sıfırdan başlar');
  await butceHazirla(e, simdi);
  const r = await gonder(e, [{ t: 'sayfa', p: '/', f: 1 }]);
  assert.equal(r.status, 204);
  assert.equal(sayOlay(e, 'sayfa'), 1, 'ertesi gün toplama yeniden açık');
  assert.equal(satir(e, '2026-10-08').yazma, 61001, 'eski günün harcaması eski satırda kaldı');
});

test('okuma kademesi: önbellekteki /populer bayat da olsa verilir, D1\'e gidilmez', async () => {
  const e = yeni();
  const iste = (ms) => populerIstegi(new Request('https://api.kpsstercihi.com/populer'), e, ms);
  const r1 = await iste(simdi);
  assert.equal(r1.status, 200);
  const g1 = await r1.text();
  toplamKaydet(e, 0, 2_500_000);
  simdi += 61_000; await butceHazirla(e, simdi);
  await butceHazirla(e, simdi + 5 * 3600_000); // bütçe yenilemesi kendi 2 ifadesini harcar; populer sorguları ayrı sayılır
  const once = e.DB._db.sayac.sorgu;
  const r2 = await iste(simdi + 5 * 3600_000); // TTL (30 dk) çoktan geçti
  assert.equal(await r2.text(), g1, 'bayat yanıt');
  assert.equal(e.DB._db.sayac.sorgu, once, 'D1 okunmadı');
});

test('okuma kademesi: önbellek boşsa /populer ve /panel/veri dostça "kota koruması" yanıtı verir', async () => {
  const e = yeni({ PANEL_ANAHTARI: 'k' });
  toplamKaydet(e, 0, 2_600_000);
  await butceHazirla(e, simdi);
  const once = e.DB._db.sayac.sorgu;
  const p = await (await populerIstegi(new Request('https://api.kpsstercihi.com/populer'), e, simdi)).json();
  assert.equal(p.kota_korumasi, true); assert.match(p.mesaj, /veri yarın/); assert.deepEqual(p.ilanlar, {});
  const cerez = `${COOKIE}=${await oturumCerezi(e, Math.floor(simdi / 1000))}`;
  const istekV = new Request('https://api.kpsstercihi.com/panel/veri?aralik=7g', { headers: { Cookie: cerez } });
  const v = await (await panelIstegi(istekV, e, new URL(istekV.url), { simdiMs: simdi })).json();
  assert.equal(v.kota_korumasi, true); assert.match(v.mesaj, /veri yarın/);
  assert.equal(v.butce.okumaKademesi, 1);
  assert.equal(e.DB._db.sayac.sorgu, once, 'rapor sorgusu çalışmadı');
});

test('panel /panel/veri yanıtına bütçe durumu ve "veri azaltıldı" bilgisi eklenir; /panel/butce çalışır', async () => {
  const e = yeni({ PANEL_ANAHTARI: 'k' });
  toplamKaydet(e, 42000, 0);
  const cerez = `${COOKIE}=${await oturumCerezi(e, Math.floor(simdi / 1000))}`;
  const al = async (yol) => { const q = new Request('https://api.kpsstercihi.com' + yol, { headers: { Cookie: cerez } }); return (await panelIstegi(q, e, new URL(q.url), { simdiMs: simdi })).json(); };
  const v = await al('/panel/veri?aralik=bugun');
  assert.equal(v.butce.yazmaKademesi, 1); assert.equal(v.butce.veriAzaltildi, true);
  assert.ok(v.butce.azaltilan.some((s) => /kaydırma/.test(s)));
  assert.ok(v.kpi, 'rapor gövdesi bozulmadı');
  const b = await al('/panel/butce');
  assert.equal(b.yazma >= 42000, true); assert.equal(b.yazmaAd, 'azaltilmis');
  assert.equal(butceOzeti(butceOku(e, simdi)).sinirOkuma, 3000000);
});

test('bakım: okuma 3M ya da yazma limiti aşıldıysa ertelenir, normalde çalışır', async () => {
  const e = yeni();
  toplamKaydet(e, 0, 3_000_000);
  const r = await bakim(e, simdi);
  assert.equal(r.ertelendi, true);
  const e2 = yeni();
  const r2 = await bakim(e2, simdi);
  assert.ok(!r2.ertelendi);
});

test('bütçe tablosu yokken (migrasyon uygulanmamış) toplama çökmez', async () => {
  const e = yeni();
  e.DB._db.ham.exec('DROP TABLE butce');
  const r = await gonder(e, [{ t: 'sayfa', p: '/', f: 1 }]);
  assert.equal(r.status, 204);
  assert.equal(sayOlay(e, 'sayfa'), 1);
});

test('0003_butce.sql iki kez çalıştırılabilir, olaylar tablosuna dokunmaz, schema.sql ile aynı tabloyu kurar', () => {
  const sql = readFileSync(new URL('../migrations/0003_butce.sql', import.meta.url), 'utf8');
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8').replace(/CREATE TABLE IF NOT EXISTS butce[\s\S]*?\);/, ''));
  db.exec("INSERT INTO olaylar (ts, gun, saat, hg, zv, os, t) VALUES (1, '2026-10-08', 0, 0, 'z', 'o', 'sayfa')");
  db.exec(sql); db.exec(sql);
  db.exec("INSERT INTO butce VALUES ('2026-10-08', 5, 7)");
  db.exec(sql);
  assert.deepEqual({ ...db.prepare('SELECT * FROM butce').get() }, { gun_utc: '2026-10-08', yazma: 5, okuma: 7 });
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM olaylar').get().n, 1);
  assert.doesNotMatch(sql, /ALTER TABLE|DROP/i);
});
