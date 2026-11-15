import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { ortam, cagir, uyeGirisi, zamaniGeriAl, kayitEskit, sahteFetch } from './yardim.js';
import { anmalariBul } from '../src/index.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const BASLIK = { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' };
const dosya = (yol) => readFileSync(new URL(yol, import.meta.url), 'utf8');

async function eskiUye(env, rumuz, rol) {
  const u = await uyeGirisi(env, rumuz, rol);
  kayitEskit(env, u.id);
  return u;
}
// hız sınırına takılmadan başlık aç
async function baslikAc(env, u, ek = {}) {
  zamaniGeriAl(env, u.id);
  return cagir(env, 'POST', '/baslik', { token: u.token, govde: { ...BASLIK, ...ek } });
}
function hamBaslik(env, o) {
  const d = { kategori: 'puan', baslik: 'deneme başlığı', govde: 'x', uye_id: 1, olusma: 1, son_hareket: 1, yanit_sayisi: 0, sabit: 0, gizli: 0, faydali: 0, duzey: null, ...o };
  const r = env.DB.ham.prepare(
    'INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket, yanit_sayisi, sabit, gizli, faydali, duzey) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  ).run(d.kategori, d.baslik, d.govde, d.uye_id, d.olusma, d.son_hareket, d.yanit_sayisi, d.sabit, d.gizli, d.faydali, d.duzey);
  return Number(r.lastInsertRowid);
}
const itibarOku = (env, id) => env.DB.ham.prepare('SELECT itibar FROM uyeler WHERE id = ?').get(id).itibar;

// ---------- göç ----------
test('göç 0002: eski şemanın üstüne temiz uygulanır, veri korunur, sonuç taze şemayla aynı', () => {
  const eski = new DatabaseSync(':memory:');
  eski.exec(dosya('./eski-schema.sql'));
  eski.exec("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('puan', 'eski baslik', 'govde', 1, 5, 5)");
  eski.exec(dosya('../migrations/0002_ozellikler.sql'));
  const taze = new DatabaseSync(':memory:');
  taze.exec(dosya('../schema.sql'));
  const kolonlar = (db, t) => db.prepare(`PRAGMA table_info(${t})`).all().map((r) => r.name).sort();
  for (const t of ['uyeler', 'basliklar', 'baslik_oylar', 'anket_secenekleri', 'anket_oylari', 'yanitlar']) {
    assert.deepEqual(kolonlar(eski, t), kolonlar(taze, t), t);
  }
  const b = eski.prepare('SELECT * FROM basliklar').get();
  assert.equal(b.baslik, 'eski baslik'); assert.equal(b.duzey, null); assert.equal(b.faydali, 0); assert.equal(b.anket, 0);
  assert.equal(eski.prepare('SELECT itibar FROM uyeler WHERE id = 1').get().itibar, 0);
  const indeksler = eski.prepare("SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'basliklar_duzey'").all();
  assert.equal(indeksler.length, 1);
});

// ---------- künye ve anket ----------
test('başlık künyesi: düzey, puan türü + puan ve anket doğrulaması', async () => {
  const env = ortam();
  const u = await eskiUye(env, 'Kunye1');
  const dene = (ek) => baslikAc(env, u, ek);
  const sec = (n) => ({ secenekler: Array.from({ length: n }, (_, i) => `Seçenek numara ${i + 1}`) });
  for (const kotu of [
    { duzey: 'doktora' }, { duzey: 5 }, { puan_turu: 'P3' }, { puan: 80 }, { puan_turu: 'P3', puan: 39.9 }, { puan_turu: 'P3', puan: 100.5 },
    { puan_turu: 'X3', puan: 80 }, { puan_turu: 'P3', puan: 'abc' }, { puan_turu: 'P3', puan: '' },
    { anket: sec(1) }, { anket: sec(7) }, { anket: 'evet' }, { anket: { secenekler: 'a' } }, { anket: { secenekler: ['bir', 3] } },
    { anket: { secenekler: ['bir', 'x'.repeat(81)] } }, { anket: { secenekler: ['bir', '  '] } },
  ]) assert.equal((await dene(kotu)).durum, 400, JSON.stringify(kotu));
  const tel = await dene({ anket: { secenekler: ['Beni ara 0532 123 45 67', 'ikinci'] } });
  assert.equal(tel.durum, 422);
  const siktir = await dene({ anket: { secenekler: ['siktir et', 'ikinci'] } });
  assert.equal(siktir.durum, 422);
  assert.equal(env.DB.ham.prepare('SELECT COUNT(*) AS n FROM basliklar').get().n, 0);

  const duz = await dene({ duzey: 'lisans', puan_turu: 'P3', puan: 78.456 });
  assert.equal(duz.durum, 201);
  assert.equal(duz.json.baslik.duzey, 'lisans'); assert.equal(duz.json.baslik.puan_turu, 'P3'); assert.equal(duz.json.baslik.puan, 78.46);
  assert.equal(duz.json.baslik.faydali, 0); assert.equal(duz.json.baslik.anket, false); assert.equal(duz.json.baslik.itibar, 0);
  const yok = await dene({});
  assert.equal(yok.json.baslik.duzey, null); assert.equal(yok.json.baslik.puan, null); assert.equal(yok.json.baslik.puan_turu, null);
  const nullluk = await dene({ duzey: null, puan_turu: null, puan: null, anket: null });
  assert.equal(nullluk.durum, 201);

  const an = await dene({ anket: { secenekler: ['  Evet  ', 'Hayır', 'Belki'] } });
  assert.equal(an.durum, 201); assert.equal(an.json.baslik.anket, true);
  const id = an.json.baslik.id;
  const liste = await cagir(env, 'GET', '/basliklar');
  assert.equal(liste.json.basliklar.find((x) => x.id === id).anket, true);
  assert.equal(liste.json.basliklar.find((x) => x.id === duz.json.baslik.id).duzey, 'lisans');
  // ayrıntı: anonim
  const d = await cagir(env, 'GET', `/baslik/${id}`);
  assert.deepEqual(d.json.anket, { secenekler: [{ sira: 1, metin: 'Evet', oy: 0 }, { sira: 2, metin: 'Hayır', oy: 0 }, { sira: 3, metin: 'Belki', oy: 0 }], toplam: 0 });
  assert.equal('oyladim' in d.json.baslik, false);
  // ayrıntı: girişli
  const dg = await cagir(env, 'GET', `/baslik/${id}`, { token: u.token });
  assert.equal(dg.json.anket.benim, null); assert.equal(dg.json.baslik.oyladim, false);
  // anketsiz başlıkta anket null
  assert.equal((await cagir(env, 'GET', `/baslik/${yok.json.baslik.id}`)).json.anket, null);
  // yönetim başlığı da künye taşır
  const y = await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { kategori: 'puan', baslik: 'Yönetim anketi başlığı', govde: 'Yönetimden bir anket.', duzey: 'ekpss', puan_turu: 'P93', puan: 61.5, anket: sec(2) } });
  assert.equal(y.durum, 201); assert.equal(y.json.baslik.duzey, 'ekpss'); assert.equal(y.json.baslik.anket, true); assert.equal(y.json.baslik.puan, 61.5);
  assert.equal((await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { kategori: 'puan', baslik: 'Yönetim kötü düzey', govde: 'Yönetimden bir anket.', duzey: 'x' } })).durum, 400);
  assert.equal((await cagir(env, 'GET', `/baslik/${y.json.baslik.id}`)).json.anket.secenekler.length, 2);
});

test('anket oyu: giriş şart, üye başına tek oy (409), seçenek sayacı artar', async () => {
  const env = ortam();
  const a = await eskiUye(env, 'Anketci'), b = await eskiUye(env, 'Oycu1'), c = await eskiUye(env, 'Oycu2');
  const id = (await baslikAc(env, a, { anket: { secenekler: ['Evet', 'Hayır', 'Belki'] } })).json.baslik.id;
  const oyla = (u, sira) => cagir(env, 'POST', `/baslik/${id}/anket`, { token: u && u.token, govde: { sira } });
  assert.equal((await oyla(null, 1)).durum, 401);
  assert.equal((await oyla(b, 9)).durum, 400);
  assert.equal((await oyla(b, '1')).durum, 400);
  const r = await oyla(b, 2);
  assert.equal(r.durum, 200);
  assert.deepEqual(r.json, { secenekler: [{ sira: 1, metin: 'Evet', oy: 0 }, { sira: 2, metin: 'Hayır', oy: 1 }, { sira: 3, metin: 'Belki', oy: 0 }], toplam: 1, benim: 2 });
  const iki = await oyla(b, 1);
  assert.equal(iki.durum, 409); assert.equal(iki.json.hata, 'Bu ankette oyun var.');
  assert.equal((await oyla(b, 2)).durum, 409);
  const r2 = await oyla(c, 2);
  assert.equal(r2.json.toplam, 2); assert.equal(r2.json.secenekler[1].oy, 2);
  assert.equal(env.DB.ham.prepare('SELECT COUNT(*) AS n FROM anket_oylari WHERE baslik_id = ?').get(id).n, 2);
  const d = await cagir(env, 'GET', `/baslik/${id}`, { token: b.token });
  assert.equal(d.json.anket.benim, 2); assert.equal(d.json.anket.toplam, 2);
  assert.equal((await cagir(env, 'GET', `/baslik/${id}`, { token: a.token })).json.anket.benim, null);
  // anketsiz başlık
  const dz = (await baslikAc(env, a, { baslik: 'Anketi olmayan başlık' })).json.baslik.id;
  assert.equal((await cagir(env, 'POST', `/baslik/${dz}/anket`, { token: b.token, govde: { sira: 1 } })).durum, 404);
  assert.equal((await cagir(env, 'POST', '/baslik/9999/anket', { token: b.token, govde: { sira: 1 } })).durum, 404);
});

// ---------- başlık faydalı + itibar ----------
test('başlık faydalı: aç-kapa, kendi başlığına yok, yazarın itibarı ±1, sistem hesabına itibar yazılmaz', async () => {
  const env = ortam();
  const a = await eskiUye(env, 'Yazar_A'), b = await eskiUye(env, 'Begenen');
  const id = (await baslikAc(env, a)).json.baslik.id;
  const f = (u, i = id) => cagir(env, 'POST', `/baslik/${i}/faydali`, { token: u && u.token });
  assert.equal((await f(null)).durum, 401);
  assert.equal((await f(a)).durum, 400);
  assert.equal(itibarOku(env, a.id), 0);
  assert.deepEqual((await f(b)).json, { faydali: 1, oyladim: true });
  assert.equal(itibarOku(env, a.id), 1);
  const d = await cagir(env, 'GET', `/baslik/${id}`, { token: b.token });
  assert.equal(d.json.baslik.faydali, 1); assert.equal(d.json.baslik.oyladim, true); assert.equal(d.json.baslik.itibar, 1);
  assert.equal((await cagir(env, 'GET', `/baslik/${id}`, { token: a.token })).json.baslik.oyladim, false);
  assert.deepEqual((await f(b)).json, { faydali: 0, oyladim: false });
  assert.equal(itibarOku(env, a.id), 0);
  assert.deepEqual((await f(b)).json, { faydali: 1, oyladim: true });
  assert.equal(itibarOku(env, a.id), 1);
  // alt sınır: elle sıfırlanmış itibar eksiye düşmez
  env.DB.ham.prepare('UPDATE uyeler SET itibar = 0 WHERE id = ?').run(a.id);
  await f(b);
  assert.equal(itibarOku(env, a.id), 0);
  assert.equal((await f(b, 9999)).durum, 404);
  // sistem hesabı
  const sis = (await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { kategori: 'etkinlik', baslik: 'Sistem başlığı deneme', govde: 'Sistemden bir başlık.' } })).json.baslik.id;
  assert.deepEqual((await f(b, sis)).json, { faydali: 1, oyladim: true });
  assert.equal(itibarOku(env, 1), 0);
  // gizli başlık
  env.DB.ham.prepare('UPDATE basliklar SET gizli = 1 WHERE id = ?').run(id);
  assert.equal((await f(b)).durum, 404);
});

test('itibar: yanıt faydalısı yazarın itibarını ±1 yapar; /ben, giriş ve yanıt çıktısında görünür', async () => {
  const env = ortam();
  const a = await eskiUye(env, 'Cevapci'), b = await eskiUye(env, 'Oylayan'), c = await eskiUye(env, 'Konucu');
  const t = (await baslikAc(env, c)).json.baslik.id;
  const y = (await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'işe yarar bir cevap' } })).json.yanit;
  assert.equal(y.itibar, 0);
  assert.deepEqual((await cagir(env, 'POST', `/yanit/${y.id}/faydali`, { token: b.token })).json, { faydali: 1, oyladim: true });
  assert.equal(itibarOku(env, a.id), 1);
  assert.equal((await cagir(env, 'GET', '/ben', { token: a.token })).json.uye.itibar, 1);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`)).json.yanitlar[0].itibar, 1);
  // başlıktan da puan gelirse toplanır
  await cagir(env, 'POST', `/baslik/${t}/faydali`, { token: a.token });
  assert.equal(itibarOku(env, c.id), 1);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`)).json.baslik.itibar, 1);
  assert.equal((await cagir(env, 'GET', '/basliklar')).json.basliklar[0].itibar, 1);
  // geri al
  assert.deepEqual((await cagir(env, 'POST', `/yanit/${y.id}/faydali`, { token: b.token })).json, { faydali: 0, oyladim: false });
  assert.equal(itibarOku(env, a.id), 0);
  // giriş yanıtı
  env.DB.ham.prepare('UPDATE uyeler SET itibar = 7 WHERE id = ?').run(a.id);
  const g = await cagir({ ...env, ORTAM: 'yerel' }, 'POST', '/giris/deneme', { govde: { rumuz: 'Cevapci' } });
  assert.equal(g.json.uye.itibar, 7);
  // asistan yanıtı itibar almaz
  env.DB.ham.prepare("INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma) VALUES (?, 2, 'asistan notu', 1)").run(t);
  const ay = env.DB.ham.prepare('SELECT id FROM yanitlar WHERE uye_id = 2').get().id;
  await cagir(env, 'POST', `/yanit/${ay}/faydali`, { token: b.token });
  assert.equal(itibarOku(env, 2), 0);
});

// ---------- listeleme ----------
test('liste: sirala son/yeni/populer/begenilen ve düzey süzgeci, kategori ile birleşir', async () => {
  const env = ortam();
  const T1 = hamBaslik(env, { olusma: 100, son_hareket: 500, yanit_sayisi: 1, faydali: 9, duzey: 'lisans' });
  const T2 = hamBaslik(env, { kategori: 'kurum', olusma: 300, son_hareket: 200, yanit_sayisi: 7, faydali: 2, duzey: 'ekpss' });
  const T3 = hamBaslik(env, { olusma: 200, son_hareket: 400, yanit_sayisi: 7, faydali: 2, duzey: 'lisans' });
  const T4 = hamBaslik(env, { olusma: 50, son_hareket: 100, sabit: 1 });
  const idler = async (q) => (await cagir(env, 'GET', `/basliklar${q}`)).json.basliklar.map((x) => x.id);
  assert.deepEqual(await idler(''), [T4, T1, T3, T2]);
  assert.deepEqual(await idler('?sirala=son'), [T4, T1, T3, T2]);
  assert.deepEqual(await idler('?sirala=yeni'), [T2, T3, T1, T4]);
  assert.deepEqual(await idler('?sirala=populer'), [T3, T2, T1, T4]);
  assert.deepEqual(await idler('?sirala=begenilen'), [T1, T3, T2, T4]);
  assert.equal((await cagir(env, 'GET', '/basliklar?sirala=rastgele')).durum, 400);
  assert.equal((await cagir(env, 'GET', '/basliklar?sirala=constructor')).durum, 400);
  assert.deepEqual(await idler('?duzey=lisans&sirala=yeni'), [T3, T1]);
  assert.deepEqual(await idler('?duzey=ekpss'), [T2]);
  assert.deepEqual(await idler('?duzey=lisans&kategori=puan'), [T1, T3]);
  assert.deepEqual(await idler('?duzey=lisans&kategori=kurum'), []);
  assert.deepEqual(await idler('?duzey=lisans&bekleyen=1'), [T1].filter(() => false));
  assert.deepEqual(await idler('?kategori=puan&bekleyen=1&sirala=yeni'), []);
  env.DB.ham.prepare('UPDATE basliklar SET yanit_sayisi = 0 WHERE id = ?').run(T1);
  assert.deepEqual(await idler('?duzey=lisans&bekleyen=1&sirala=populer'), [T1]);
  assert.equal((await cagir(env, 'GET', '/basliklar?duzey=doktora')).durum, 400);
  const sayfali = await cagir(env, 'GET', '/basliklar?sirala=yeni&sayfa=1');
  assert.equal(sayfali.json.sayfa, 1);
});

// ---------- arama ----------
test('arama: 2-60 karakter, Türkçe büyük/küçük harf, LIKE kaçışı, gizli çıkmaz, en çok 20', async () => {
  const env = ortam();
  const ist = hamBaslik(env, { baslik: 'istanbul ilindeki kurumlar hakkında', son_hareket: 10 });
  const izm = hamBaslik(env, { baslik: 'İZMİR kadrolari nasıl', govde: 'sorular', son_hareket: 20 });
  const ilm = hamBaslik(env, { baslik: 'ılımlı bir başlık', son_hareket: 30 });
  const yuzde = hamBaslik(env, { baslik: 'Oran 100% kesin mi bu', son_hareket: 40 });
  const yuz2 = hamBaslik(env, { baslik: 'Oran 1000 kesin mi bu', son_hareket: 41 });
  const alt = hamBaslik(env, { baslik: 'kod a_b gibi', son_hareket: 42 });
  const alt2 = hamBaslik(env, { baslik: 'kod axb gibi', son_hareket: 43 });
  const govdede = hamBaslik(env, { baslik: 'başka konu', govde: 'metinde Samsun geçiyor', son_hareket: 44 });
  const gizli = hamBaslik(env, { baslik: 'istanbul gizli başlık', gizli: 1, son_hareket: 99 });
  const ara = async (q) => cagir(env, 'GET', `/ara?q=${encodeURIComponent(q)}`);
  const idler = async (q) => (await ara(q)).json.basliklar.map((x) => x.id);
  assert.deepEqual(await idler('İSTANBUL'), [ist]);
  assert.deepEqual(await idler('istanbul'), [ist]);
  assert.deepEqual(await idler('ISTANBUL'), [ist]);
  assert.deepEqual(await idler('izmir'), [izm]);
  assert.deepEqual(await idler('İzmir'), [izm]);
  assert.deepEqual(await idler('ILIMLI'), [ilm]);
  assert.deepEqual(await idler('100%'), [yuzde]);
  assert.deepEqual(await idler('a_b'), [alt]);
  assert.deepEqual(await idler('samsun'), [govdede]);
  assert.deepEqual(await idler('0%'), [yuzde]);
  assert.deepEqual(await idler('%%'), []);
  assert.deepEqual(await idler('kod a'), [alt2, alt]);   // son hareketi yeni olan önce
  assert.ok(![alt2, yuz2].includes((await idler('a_b'))[0]));
  assert.deepEqual(await idler('yokboyle'), []);
  assert.equal(await cagir(env, 'GET', '/ara').then((r) => r.durum), 400);
  assert.equal((await ara('a')).durum, 400);
  assert.equal((await ara('   a ')).durum, 400);
  assert.equal((await ara('x'.repeat(61))).durum, 400);
  assert.equal((await ara('x'.repeat(60))).durum, 200);
  const sonuc = (await ara('İSTANBUL')).json.basliklar[0];
  assert.ok('kisa' in sonuc && !('govde' in sonuc)); assert.equal(sonuc.duzey, null); assert.equal(sonuc.anket, false); assert.equal(sonuc.itibar, 0);
  for (let i = 0; i < 25; i++) hamBaslik(env, { baslik: `toplu arama sonucu ${i}`, son_hareket: 1000 + i });
  const yirmi = (await ara('toplu arama')).json.basliklar;
  assert.equal(yirmi.length, 20); assert.equal(yirmi[0].baslik, 'toplu arama sonucu 24');
  assert.ok(gizli);
});

// ---------- durum ----------
test('/durum: kategori sayıları, bekleyen sayısı, gündem ve bekleyenler listeleri', async () => {
  const env = ortam();
  const simdi = Math.floor(Date.now() / 1000);
  const A = hamBaslik(env, { kategori: 'puan', olusma: simdi - 50, son_hareket: simdi - 50, yanit_sayisi: 0 });
  const B = hamBaslik(env, { kategori: 'kurum', olusma: simdi - 1000, son_hareket: simdi - 500, yanit_sayisi: 5 });
  const C = hamBaslik(env, { kategori: 'kurum', olusma: simdi - 300000, son_hareket: simdi - 200000, yanit_sayisi: 2 });
  const D = hamBaslik(env, { kategori: 'etkinlik', olusma: simdi - 60, son_hareket: simdi - 60, yanit_sayisi: 0, sabit: 1 });
  hamBaslik(env, { kategori: 'puan', son_hareket: simdi - 10, yanit_sayisi: 0, gizli: 1 });
  const E = hamBaslik(env, { kategori: 'hazirlik', olusma: simdi - 900, son_hareket: simdi - 900, yanit_sayisi: 0, duzey: 'agrubu' });
  const d = (await cagir(env, 'GET', '/durum')).json;
  assert.deepEqual(d.kategoriler, { ilan: 0, puan: 1, kurum: 2, mulakat: 0, haklar: 0, hazirlik: 1, etkinlik: 1 });
  assert.equal(d.bekleyen, 2);
  assert.deepEqual(d.gundem.map((x) => x.id), [B, A, D, E]);
  assert.deepEqual(d.bekleyenler.map((x) => x.id), [A, E]);
  assert.equal(d.gundem[0].yanit_sayisi, 5); assert.ok('kisa' in d.gundem[0]); assert.equal(d.bekleyenler[1].duzey, 'agrubu');
  assert.ok(!d.gundem.some((x) => x.id === C));
  assert.equal(d.uye, 0); assert.equal(d.kurucu_kalan, 200);
  // en çok 5
  for (let i = 0; i < 8; i++) hamBaslik(env, { olusma: simdi - i, son_hareket: simdi - i, yanit_sayisi: 0 });
  const d2 = (await cagir(env, 'GET', '/durum')).json;
  assert.equal(d2.gundem.length, 5); assert.equal(d2.bekleyenler.length, 5); assert.equal(d2.bekleyen, 10);
});

// ---------- anmalar ----------
test('anmalariBul: en çok 3 farklı rumuz, büyük/küçük harf ayrımsız, e-posta ve noktalama', () => {
  assert.deepEqual(anmalariBul('selam @Ayse_K ve @ayse_k ile @Çağlar.Y!'), ['Ayse_K', 'Çağlar.Y']);
  assert.deepEqual(anmalariBul('@aaa @bbb @ccc @ddd'), ['aaa', 'bbb', 'ccc']);
  assert.deepEqual(anmalariBul('mail ali@example.com yazın'), []);
  assert.deepEqual(anmalariBul('@ab kısa, @abc.'), ['abc']);
  assert.deepEqual(anmalariBul('anma yok'), []);
});

test('anma bildirimi: bir kez gider; kendine, başlık sahibine ikinci kez ve 3 üyeden fazlasına gitmez', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const tg = (u, n) => env.DB.ham.prepare('UPDATE uyeler SET tg_id = ? WHERE id = ?').run(n, u.id);
    const sahip = await eskiUye(env, 'Sahip_S'), yazan = await eskiUye(env, 'Yazan_Y');
    const m1 = await eskiUye(env, 'Mehmet_A'), m2 = await eskiUye(env, 'Zeynep_B'), m3 = await eskiUye(env, 'Can_C'), m4 = await eskiUye(env, 'Deniz_D');
    [[sahip, 100], [yazan, 101], [m1, 201], [m2, 202], [m3, 203], [m4, 204]].forEach(([u, n]) => tg(u, n));
    const t = (await baslikAc(env, sahip)).json.baslik.id;
    const gonderilenler = () => f.cagrilar.map((c) => JSON.parse(c.secenek.body));
    // bir kez: aynı kişiyi iki kez (farklı harf) anmak tek mesaj
    const r = await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: yazan.token, govde: { govde: 'bakar mısın @mehmet_a ve @MEHMET_A?' } });
    assert.equal(r.durum, 201);
    let g = gonderilenler();
    const anma = g.filter((x) => x.chat_id === 201);
    assert.equal(anma.length, 1);
    assert.equal(anma[0].text, `Yazan_Y seni andı: ${BASLIK.baslik.slice(0, 60)}\nhttps://kpsstercihi.com/forum/?b=${t}#y${r.json.yanit.id}`);
    assert.match(f.cagrilar.find((c) => JSON.parse(c.secenek.body).chat_id === 201).url, /api\.telegram\.org\/bot123456:TEST-TOKEN\/sendMessage/);
    assert.equal(g.filter((x) => x.chat_id === 100).length, 1, 'başlık sahibine olağan yanıt bildirimi');
    // kendini anmak: kimseye gitmez; sahibini anmak: yanıt bildirimi dışında ikinci mesaj yok
    zamaniGeriAl(env, yazan.id);
    const once = f.cagrilar.length;
    await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: yazan.token, govde: { govde: 'ben @yazan_y kendimi anıyorum' } });
    assert.equal(f.cagrilar.length, once);
    // başlık sahibi anılırsa tek bildirim (anma + sahip birleşir)
    const t2 = (await baslikAc(env, sahip, { baslik: 'İkinci başlık için deneme' })).json.baslik.id;
    zamaniGeriAl(env, yazan.id);
    const once2 = f.cagrilar.length;
    await cagir(env, 'POST', `/baslik/${t2}/yanit`, { token: yazan.token, govde: { govde: 'sahibine @sahip_s selam' } });
    assert.equal(f.cagrilar.length - once2, 1);
    assert.match(JSON.parse(f.cagrilar.at(-1).secenek.body).text, /başlığına yanıt yazdı/);
    // en çok 3 üye
    const t3 = (await baslikAc(env, sahip, { baslik: 'Üçüncü başlık için deneme' })).json.baslik.id;
    zamaniGeriAl(env, yazan.id);
    const once3 = f.cagrilar.length;
    await cagir(env, 'POST', `/baslik/${t3}/yanit`, { token: yazan.token, govde: { govde: '@Mehmet_A @Zeynep_B @Can_C @Deniz_D hepiniz gelin' } });
    const yeni = f.cagrilar.slice(once3).map((c) => JSON.parse(c.secenek.body));
    const anilanlar = yeni.filter((x) => /seni andı/.test(x.text)).map((x) => x.chat_id).sort();
    assert.deepEqual(anilanlar, [201, 202, 203]);
    assert.equal(yeni.filter((x) => x.chat_id === 204).length, 0);
    // bildirimi kapalı üye, engelli üye, olmayan rumuz
    await cagir(env, 'POST', '/ben/bildirim', { token: m1.token, govde: { acik: false } });
    env.DB.ham.prepare('UPDATE uyeler SET engelli = 1 WHERE id = ?').run(m2.id);
    const t4 = (await baslikAc(env, sahip, { baslik: 'Dördüncü başlık için deneme' })).json.baslik.id;
    zamaniGeriAl(env, yazan.id);
    const once4 = f.cagrilar.length;
    await cagir(env, 'POST', `/baslik/${t4}/yanit`, { token: yazan.token, govde: { govde: '@Mehmet_A @Zeynep_B @Yokboyle_Z' } });
    assert.deepEqual(f.cagrilar.slice(once4).map((c) => JSON.parse(c.secenek.body)).filter((x) => /seni andı/.test(x.text)), []);
    // anma saklanmaz
    const sutunlar = env.DB.ham.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all().map((x) => x.name);
    assert.ok(!sutunlar.some((n) => /anma/.test(n)));
  } finally { f.geri(); }
});

test('anma bildirimi: ilan yanıtında da çalışır; yerelde ve token yokken gönderilmez', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const yazan = await eskiUye(env, 'Ilanci_Y'), anilan = await eskiUye(env, 'Anilan_Z');
    env.DB.ham.prepare('UPDATE uyeler SET tg_id = 301 WHERE id = ?').run(anilan.id);
    const ilan = 'csb-12345';
    const r = await cagir(env, 'POST', `/ilan/${ilan}/yanit`, { token: yazan.token, govde: { govde: 'şunu da @anilan_z sorsun', ilan_baslik: 'Deneme kurumu 2026 sözleşmeli personel alımı' } });
    assert.equal(r.durum, 201);
    const tgCagri = () => f.cagrilar.filter((c) => c.url.startsWith('https://api.telegram.org/'));
    assert.equal(tgCagri().length, 1);
    const g = JSON.parse(tgCagri()[0].secenek.body);
    assert.equal(g.chat_id, 301);
    assert.equal(g.text, `Ilanci_Y seni andı: Deneme kurumu 2026 sözleşmeli personel alımı\nhttps://kpsstercihi.com/forum/?b=${r.json.baslik_id}#y${r.json.yanitlar[0].id}`);
    // yerel ortam
    const yerel = ortam({ ORTAM: 'yerel' });
    const a = await eskiUye(yerel, 'Yerel_A'), b = await eskiUye(yerel, 'Yerel_B');
    yerel.DB.ham.prepare('UPDATE uyeler SET tg_id = 5 WHERE id = ?').run(b.id);
    const t = (await baslikAc(yerel, a)).json.baslik.id;
    const onceki = tgCagri().length;
    await cagir(yerel, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'anıyorum @yerel_b' } });
    // token yok
    const env2 = ortam({ TELEGRAM_BOT_TOKEN: undefined });
    const c = await eskiUye(env2, 'Tokensiz_A'), d = await eskiUye(env2, 'Tokensiz_B');
    env2.DB.ham.prepare('UPDATE uyeler SET tg_id = 6 WHERE id = ?').run(d.id);
    const t2 = (await baslikAc(env2, c)).json.baslik.id;
    await cagir(env2, 'POST', `/baslik/${t2}/yanit`, { token: c.token, govde: { govde: 'anıyorum @tokensiz_b' } });
    assert.equal(tgCagri().length, onceki);
  } finally { f.geri(); }
});
