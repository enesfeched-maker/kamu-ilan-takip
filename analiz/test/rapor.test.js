import test from 'node:test';
import assert from 'node:assert/strict';
import { topla, hizSifirla } from '../src/toplama.js';
import { raporUret, canli } from '../src/rapor.js';
import { bakim } from '../src/bakim.js';
import { haritaYukle, adlariSifirla, ilanAdlari } from '../src/adlar.js';
import { sahteD1, istek, paket } from './sahte-d1.js';

const GUN = Date.parse('2026-10-07T09:00:00Z');   // dün 12:00 (TR)
const BUGUN = Date.parse('2026-10-08T09:00:00Z');
const UA_MOBIL = 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36';
const ANAHTAR = 'AAAA1111-2222-4333-8444-555566667777';

async function gonder(env, ms, ip, olaylar, ek = {}, ist = {}) {
  const r = await topla(istek(paket(olaylar, ek), { ip, ...ist }), env, ms);
  assert.equal(r.status, 204);
}

async function tohumla(env) {
  hizSifirla();
  // Ziyaretçi A (dün): Google'dan ilan sayfasına, resmî ilana gider
  await gonder(env, GUN, '10.0.0.1', [
    { t: 'sayfa', p: `/ilan/${ANAHTAR}/`, f: 1 }, { t: 'aktif', p: `/ilan/${ANAHTAR}/`, n: 45 },
    { t: 'tikla', p: `/ilan/${ANAHTAR}/`, a: 'resmi_ilan', h: ANAHTAR }, { t: 'kaydirma', p: `/ilan/${ANAHTAR}/`, n: 50 },
    { t: 'hiz', p: `/ilan/${ANAHTAR}/`, n: 1800, n2: 200 },
  ], { s: 'oturumAAAA01', ref: 'www.google.com' });
  // Ziyaretçi B (dün): mobil, doğrudan, hemen çıkar
  await gonder(env, GUN + 60e3, '10.0.0.2', [{ t: 'sayfa', p: '/', v: 'bugun', f: 1 }], { s: 'oturumBBBB02', ref: '' }, { ua: UA_MOBIL, cf: { country: 'TR', region: 'İstanbul', city: 'İstanbul' } });
  // Ziyaretçi A (bugün): geri dönen, Telegram, arama, sonuçsuz arama, ana sayfa → ilan penceresi → resmî
  await gonder(env, BUGUN, '10.0.0.1', [
    { t: 'sayfa', p: '/', v: 'bugun', f: 1 }, { t: 'sayfa', p: '/', v: 'ilanlar' },
    { t: 'tikla', p: '/', v: 'ilanlar', a: 'arama', x: 'zabıta', n: 12 }, { t: 'tikla', p: '/', v: 'ilanlar', a: 'arama', x: 'astronot', n: 0 },
    { t: 'tikla', p: '/', v: 'ilanlar', a: 'kategori', h: 'memur' }, { t: 'tikla', p: '/', v: 'ilanlar', a: 'filtre', h: 'il', x: 'ankara' },
    { t: 'tikla', p: '/', v: 'bugun', a: 'manset_tikla', h: ANAHTAR, n: 2 }, { t: 'tikla', p: '/', v: 'bugun', a: 'telegram', x: 'ust' },
    { t: 'sayfa', p: '/', v: 'ilan', k: ANAHTAR }, { t: 'aktif', p: '/', v: 'ilan', k: ANAHTAR, n: 30 },
    { t: 'tikla', p: '/', v: 'ilan', k: ANAHTAR, a: 'resmi_ilan', h: ANAHTAR },
  ], { s: 'oturumAAAA03', r: 1, ref: 't.me' });
  await gonder(env, BUGUN + 10e3, '10.0.0.3', [
    { t: 'sayfa', p: '/kurum/ankara-bb/', f: 1 }, { t: 'hata', p: '/kurum/ankara-bb/', x: 'TypeError: x is undefined', h: '/portal.js:10' },
    { t: '404', p: '/eski-sayfa', f: 1 }, { t: 'aktif', p: '/kurum/ankara-bb/', n: 15 },
  ], { s: 'oturumCCCC04', ref: 'l.instagram.com' });
}

test('rapor: KPI, kaynaklar, içerik, etkileşim, huni, kalite', async () => {
  const e = { DB: sahteD1() };
  await tohumla(e);
  const adlar = async (anahtarlar) => Object.fromEntries([...anahtarlar].map((k) => [k, 'Örnek Belediye — Zabıta Memuru']));
  const r = await raporUret(e, '7g', BUGUN + 3600e3, adlar);
  assert.equal(r.gunler.length, 7);
  assert.equal(r.aralik.bas, '2026-10-02');
  // dün: A, B; bugün: A, C -> günlük tekil toplam 4
  assert.equal(r.kpi.ziyaretci, 4);
  assert.equal(r.kpi.oturum, 4);
  assert.equal(r.kpi.sayfa, 6);
  assert.equal(r.kpi.etkinSaniyeOrt, Math.round(90 / 4));
  // hemen çıkma: B tek sayfa etkileşimsiz; diğerleri tıklama içeriyor, C ise hata/aktif 15 sn + 2 sayfa
  assert.ok(r.kpi.hemenCikma > 0 && r.kpi.hemenCikma < 1);
  assert.equal(r.kpi.yeni, 3);
  assert.equal(r.kpi.geri, 1);
  const kaynak = Object.fromEntries(r.kaynak.map((k) => [k.ad, k.oturum]));
  assert.deepEqual(kaynak, { Google: 1, Doğrudan: 1, Telegram: 1, Instagram: 1 });
  assert.equal(r.cihaz.find((c) => c.ad === 'mobil').oturum, 1);
  assert.ok(r.sehir.some((s) => s.ad === 'İstanbul'));
  assert.equal(r.isi.reduce((t, x) => t + x[2], 0), 6);
  assert.ok(r.ilanlar.some((i) => i.k === ANAHTAR && i.say === 3 - 1 + 0 && i.ad.includes('Zabıta')) || r.ilanlar[0].say >= 2);
  const ilan = r.ilanlar.find((i) => i.k === ANAHTAR);
  assert.equal(ilan.say, 2); // sayfa + pencere
  assert.equal(ilan.sureSn, 75);
  assert.equal(r.enUzun[0].k, ANAHTAR);
  assert.equal(r.kurumlar[0].k, 'ankara-bb');
  assert.deepEqual(r.aramalar.map((a) => a.q).sort(), ['astronot', 'zabıta']);
  assert.deepEqual(r.sifirAramalar, [{ q: 'astronot', var: 0, sifir: 1 }]);
  assert.equal(r.kategori[0].k, 'memur');
  assert.deepEqual(r.filtre[0], { filtre: 'il', deger: 'ankara', say: 1 });
  assert.deepEqual(r.manset.konum, [{ n: 2, say: 1 }]);
  assert.equal(r.donusum.resmi, 2);
  assert.equal(r.donusum.telegram, 1);
  assert.equal(r.resmiIlanlar[0].say, 2);
  assert.equal(r.huni.oturum, 4);
  assert.equal(r.huni.ilan, 2);
  assert.equal(r.huni.resmi, 2);
  assert.equal(r.huni.anaIlan, 1);
  assert.equal(r.huni.ilanResmi, 2);
  assert.equal(r.kalite.kaydirma.find((x) => x.n === 50).say, 1);
  assert.equal(r.kalite.hatalar[0].mesaj, 'TypeError: x is undefined');
  assert.equal(r.kalite.yok404[0].p, '/eski-sayfa');
  assert.equal(r.kalite.lcpMs, 1800);
  assert.equal(r.kalite.ttfbMs, 200);
  assert.deepEqual(r.gorunumler.map((g) => g.v).sort(), ['bugun', 'ilan', 'ilanlar']);
});

test('günlük özet (cron) ile ham veri aynı raporu verir; ham olaylar silinse de özet kalır', async () => {
  const e = { DB: sahteD1() };
  await tohumla(e);
  const once = await raporUret(e, '7g', BUGUN + 3600e3);
  const ozet = await bakim(e, BUGUN + 3600e3);
  assert.deepEqual(ozet.ozetlenen, ['2026-10-07']);
  assert.equal(e.DB.ham.prepare('SELECT COUNT(*) n FROM ozet_gun').get().n, 1);
  const sonra = await raporUret(e, '7g', BUGUN + 3600e3);
  // özet yalnız ilk 200 satırı tutar; bu küçük veride tümü aynı olmalı
  assert.deepEqual(sonra, once);
  // ikinci çalıştırma yeni gün özetlemez
  assert.deepEqual((await bakim(e, BUGUN + 7200e3)).ozetlenen, []);
});

test('bakım: 90 günden eski ham olaylar ve eski tuzlar silinir, bugünküne dokunulmaz', async () => {
  const e = { DB: sahteD1() };
  await tohumla(e);
  await bakim(e, BUGUN + 3600e3);
  assert.equal(e.DB.ham.prepare('SELECT COUNT(*) n FROM tuz').get().n, 1, 'dünün tuzu silindi');
  const once = e.DB.ham.prepare('SELECT COUNT(*) n FROM olaylar').get().n;
  const ileri = BUGUN + 91 * 86400e3;
  await bakim(e, ileri);
  const kalan = e.DB.ham.prepare('SELECT COUNT(*) n FROM olaylar').get().n;
  assert.ok(kalan < once);
  assert.equal(e.DB.ham.prepare("SELECT COUNT(*) n FROM olaylar WHERE gun = '2026-10-07'").get().n, 0);
  assert.ok(e.DB.ham.prepare('SELECT COUNT(*) n FROM ozet').get().n > 0, 'özetler kalır');
});

test('canlı: son 5 dakikadaki tekil ziyaretçi ve anonim akış', async () => {
  const e = { DB: sahteD1() };
  await tohumla(e);
  const c = await canli(e, BUGUN + 60e3);
  assert.equal(c.aktif, 2);
  assert.ok(c.akis.length > 0 && c.akis.length <= 50);
  assert.ok(!('zv' in c.akis[0]) && !('os' in c.akis[0]));
  assert.equal((await canli(e, BUGUN + 3600e3)).aktif, 0);
});

test('ilan adları: liste.json çekilir, önbelleğe alınır, hata durumunda anahtar kalır', async () => {
  adlariSifirla();
  let cagri = 0;
  const getir = async () => { cagri++; return { ok: true, json: async () => ({ ilanlar: [{ key: 'k1', kurum: 'Kurum', manset: 'Büro Personeli' }, { key: 5 }] }) }; };
  const e = { SITE_URL: 'https://kpsstercihi.com/' };
  assert.deepEqual(await ilanAdlari(e, ['k1', 'yok'], getir), { k1: 'Kurum — Büro Personeli' });
  await ilanAdlari(e, ['k1'], getir);
  assert.equal(cagri, 1);
  adlariSifirla();
  const bozuk = async () => ({ ok: false, status: 500 });
  assert.deepEqual(await ilanAdlari(e, ['k1'], bozuk), {});
  assert.equal((await haritaYukle(e, bozuk)).size, 0);
});
