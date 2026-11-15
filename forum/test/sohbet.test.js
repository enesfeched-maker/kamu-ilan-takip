import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ortam, cagir, uyeGirisi } from './yardim.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const ODA = { kategori: 'oda', baslik: 'Deneme sohbet odası', govde: 'Bu bir deneme odasıdır, hoş geldiniz.' };
const simdiSn = () => Math.floor(Date.now() / 1000);

function hamBaslik(env, { kategori = 'puan', baslik = 'Deneme başlığı uzun', uye = 1, olusma = simdiSn(), yanit = 0 } = {}) {
  return Number(env.DB.ham.prepare('INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket, yanit_sayisi) VALUES (?, ?, ?, ?, ?, ?, ?)')
    .run(kategori, baslik, 'gövde metni', uye, olusma, olusma, yanit).lastInsertRowid);
}
function hamYanit(env, baslikId, uyeId, govde, { olusma = simdiSn(), ust = null, gizli = 0 } = {}) {
  return Number(env.DB.ham.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, ust_id, gizli) VALUES (?, ?, ?, ?, ?, ?)')
    .run(baslikId, uyeId, govde, olusma, ust, gizli).lastInsertRowid);
}

// ---------- odalar ----------
test('oda: üye 403, yönetici üye ve /yonetim/baslik 201; kategori ve durum sayımında görünür', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Sıradan_Üye');
  const y = await uyeGirisi(env, 'Mudur_Bir', 'yonetici');
  assert.equal((await cagir(env, 'POST', '/baslik', { token: u.token, govde: ODA })).durum, 403);
  assert.equal((await cagir(env, 'POST', '/baslik', { token: y.token, govde: ODA })).durum, 201);
  const s = await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { ...ODA, baslik: 'Sistem odası deneme', sabit: true } });
  assert.equal(s.durum, 201); assert.equal(s.json.baslik.kategori, 'oda');
  const k = await cagir(env, 'GET', '/kategoriler');
  assert.ok(k.json.kategoriler.some((x) => x.kod === 'oda' && x.ad === 'Sohbet odaları'));
  assert.equal((await cagir(env, 'GET', '/durum')).json.kategoriler.oda, 2);
  assert.equal((await cagir(env, 'GET', '/basliklar?kategori=oda')).json.basliklar.length, 2);
});

test('odalar.sql: iki kez uygulanınca yinelenmez, 7 sabit oda, düzeyler ayarlı', () => {
  const env = ortam();
  const sql = readFileSync(new URL('../odalar.sql', import.meta.url), 'utf8');
  env.DB.ham.exec(sql); env.DB.ham.exec(sql);
  const satirlar = env.DB.ham.prepare("SELECT baslik, uye_id, kaynak, sabit, duzey, govde FROM basliklar WHERE kategori = 'oda' ORDER BY id").all();
  assert.equal(satirlar.length, 7);
  assert.deepEqual(satirlar.map((r) => r.baslik), ['Lisans odası', 'Önlisans odası', 'Ortaöğretim odası', 'EKPSS odası', 'Tercih dönemi odası', 'Sınava çalışanlar odası', 'Atananlar ve yeni memurlar odası']);
  assert.deepEqual(satirlar.slice(0, 4).map((r) => r.duzey), ['lisans', 'onlisans', 'ortaogretim', 'ekpss']);
  assert.ok(satirlar.slice(4).every((r) => r.duzey === null));
  assert.ok(satirlar.every((r) => r.uye_id === 1 && r.kaynak === 'sistem' && r.sabit === 1 && r.govde.length > 10));
});

// ---------- sayfalama ----------
test('baslik: son 100 yanıt artan sırada, once ile eskiye sayfalama, daha_eski bayrakları, limit sınırı', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Yazar_Bir');
  const t = hamBaslik(env, { yanit: 250 });
  const idler = [];
  for (let i = 1; i <= 250; i++) idler.push(hamYanit(env, t, u.id, `mesaj ${i}`));
  const a = (await cagir(env, 'GET', `/baslik/${t}`)).json;
  assert.equal(a.yanitlar.length, 100); assert.equal(a.daha_eski, true);
  assert.deepEqual(a.yanitlar.map((r) => r.id), idler.slice(150));
  assert.equal(a.baslik.id, t); assert.equal(a.anket, null);
  const b = (await cagir(env, 'GET', `/baslik/${t}?once=${a.yanitlar[0].id}`)).json;
  assert.deepEqual(b.yanitlar.map((r) => r.id), idler.slice(50, 150)); assert.equal(b.daha_eski, true);
  assert.equal(b.baslik.id, t);
  const c = (await cagir(env, 'GET', `/baslik/${t}?once=${b.yanitlar[0].id}`)).json;
  assert.deepEqual(c.yanitlar.map((r) => r.id), idler.slice(0, 50)); assert.equal(c.daha_eski, false);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}?limit=20`)).json.yanitlar.length, 20);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}?limit=9999`)).json.yanitlar.length, 200);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}?once=abc`)).durum, 400);
  const tam = (await cagir(env, 'GET', `/baslik/${hamBaslik(env)}`)).json;
  assert.deepEqual(tam.yanitlar, []); assert.equal(tam.daha_eski, false);
});

test('baslik: girişliyken oyladim/benim işaretleri sayfadaki yanıtlar için doğru', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Okuyucu_Bir');
  const d = await uyeGirisi(env, 'Yazar_Iki');
  const t = hamBaslik(env, { yanit: 2 });
  const y1 = hamYanit(env, t, d.id, 'birinci');
  const y2 = hamYanit(env, t, u.id, 'ikinci');
  env.DB.ham.prepare('INSERT INTO oylar (yanit_id, uye_id) VALUES (?, ?)').run(y1, u.id);
  const r = (await cagir(env, 'GET', `/baslik/${t}`, { token: u.token })).json.yanitlar;
  assert.deepEqual(r.map((x) => [x.id, x.oyladim, x.benim]), [[y1, true, false], [y2, false, true]]);
});

// ---------- artımlı yoklama ----------
test('/baslik/:id/yeni: yalnız daha yeni yanıtlar, yanit_sayisi, 400/404', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Yazar_Uc');
  const t = hamBaslik(env, { yanit: 3 });
  const [a, b, c] = [hamYanit(env, t, u.id, 'bir'), hamYanit(env, t, u.id, 'iki'), hamYanit(env, t, u.id, 'üç')];
  hamYanit(env, t, u.id, 'gizli olan', { gizli: 1 });
  const r = await cagir(env, 'GET', `/baslik/${t}/yeni?sonra=${a}`);
  assert.equal(r.durum, 200);
  assert.deepEqual(r.json.yanitlar.map((x) => x.id), [b, c]); assert.equal(r.json.yanit_sayisi, 3);
  assert.deepEqual((await cagir(env, 'GET', `/baslik/${t}/yeni?sonra=${c}`)).json.yanitlar, []);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}/yeni?sonra=0`)).json.yanitlar.length, 3);
  for (const kotu of ['', '?sonra=', '?sonra=-1', '?sonra=abc', '?sonra=1.5']) assert.equal((await cagir(env, 'GET', `/baslik/${t}/yeni${kotu}`)).durum, 400, kotu);
  assert.equal((await cagir(env, 'GET', '/baslik/9999/yeni?sonra=0')).durum, 404);
  env.DB.ham.prepare('UPDATE basliklar SET gizli = 1 WHERE id = ?').run(t);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}/yeni?sonra=0`)).durum, 404);
});

test('/baslik/:id/yeni: en çok 100 yanıt, girişliyse oyladim/benim, tek yanıt sorgusu', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Yazar_Dort');
  const t = hamBaslik(env, { yanit: 130 });
  const idler = [];
  for (let i = 0; i < 130; i++) idler.push(hamYanit(env, t, u.id, `m${i}`));
  env.DB.ham.prepare('INSERT INTO oylar (yanit_id, uye_id) VALUES (?, ?)').run(idler[1], u.id);
  const r = await cagir(env, 'GET', `/baslik/${t}/yeni?sonra=0`, { token: u.token });
  assert.equal(r.json.yanitlar.length, 100); assert.equal(r.json.yanitlar[0].id, idler[0]);
  assert.equal(r.json.yanitlar[1].oyladim, true); assert.equal(r.json.yanitlar[0].benim, true);
  // anonim: sorgu sayısı sabit (başlık satırı + yanıtlar)
  const once = env.DB.sayac.sorgu;
  await cagir(env, 'GET', `/baslik/${t}/yeni?sonra=${idler[129]}`);
  assert.equal(env.DB.sayac.sorgu - once, 2);
});

// ---------- silme ----------
test('DELETE /yanit/:id: yazar siler, başkası 403, yönetici siler, sistem/asistan yalnız yönetici, sayaç düşer', async () => {
  const env = ortam();
  const a = await uyeGirisi(env, 'Yazar_Bes');
  const b = await uyeGirisi(env, 'Baska_Uye');
  const y = await uyeGirisi(env, 'Mudur_Iki', 'yonetici');
  const t = hamBaslik(env, { yanit: 4 });
  const benim = hamYanit(env, t, a.id, 'benim mesajım');
  const baskasi = hamYanit(env, t, b.id, 'başkasının mesajı');
  const sistem = hamYanit(env, t, 2, 'asistan cevabı');
  const sayi = () => env.DB.ham.prepare('SELECT yanit_sayisi FROM basliklar WHERE id = ?').get(t).yanit_sayisi;
  assert.equal((await cagir(env, 'DELETE', `/yanit/${benim}`)).durum, 401);
  assert.equal((await cagir(env, 'DELETE', `/yanit/${benim}`, { token: b.token })).durum, 403);
  assert.equal((await cagir(env, 'DELETE', `/yanit/${sistem}`, { token: a.token })).durum, 403);
  const ok = await cagir(env, 'DELETE', `/yanit/${benim}`, { token: a.token });
  assert.equal(ok.durum, 200); assert.deepEqual(ok.json, { tamam: true });
  assert.equal(sayi(), 3);
  assert.equal((await cagir(env, 'DELETE', `/yanit/${benim}`, { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'DELETE', '/yanit/99999', { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'DELETE', `/yanit/${baskasi}`, { token: y.token })).durum, 200);
  assert.equal((await cagir(env, 'DELETE', `/yanit/${sistem}`, { token: y.token })).durum, 200);
  assert.equal(sayi(), 1);
  assert.deepEqual((await cagir(env, 'GET', `/baslik/${t}`)).json.yanitlar, []);
});

// ---------- bildirimler ----------
test('bildirimler: yanit/alinti/anma türleri, öncelik, kendi mesajı hariç, 90 karakter, yeniden eskiye', async () => {
  const env = ortam();
  const ben = await uyeGirisi(env, 'İpek_Y');
  const d = await uyeGirisi(env, 'Diger_Uye');
  const benimBaslik = hamBaslik(env, { uye: ben.id, baslik: 'Benim açtığım başlık', yanit: 0 });
  const baskaBaslik = hamBaslik(env, { uye: d.id, baslik: 'Başkasının başlığı' });
  const t = simdiSn();
  const kendi = hamYanit(env, benimBaslik, ben.id, 'kendi mesajım @İpek_Y', { olusma: t - 50 });          // hariç
  const yanitTur = hamYanit(env, benimBaslik, d.id, 'x'.repeat(200), { olusma: t - 40 });                  // yanit
  const benimOnceki = hamYanit(env, baskaBaslik, ben.id, 'sorum var', { olusma: t - 400 });
  const alintiTur = hamYanit(env, baskaBaslik, d.id, 'cevabım şu', { olusma: t - 30, ust: benimOnceki }); // alinti
  const anmaTur = hamYanit(env, baskaBaslik, d.id, 'bence @ipek_y bilir', { olusma: t - 20 });            // anma (küçük harf, Türkçe)
  const hepsi = hamYanit(env, benimBaslik, d.id, 'hey @İPEK_Y bak', { olusma: t - 10, ust: kendi });       // yanit + anma + alinti -> alinti
  const anmaBuyuk = hamYanit(env, baskaBaslik, d.id, 'selam @İPEK_Y', { olusma: t - 5 });                  // anma (büyük harf)
  hamYanit(env, baskaBaslik, d.id, 'şunu @ipek_yy aradım', { olusma: t - 4 });                              // başka rumuz: sayılmaz
  hamYanit(env, baskaBaslik, d.id, 'gizli @ipek_y', { olusma: t - 3, gizli: 1 });                           // gizli: sayılmaz
  const r = await cagir(env, 'GET', '/ben/bildirimler', { token: ben.token });
  assert.equal(r.durum, 200);
  assert.equal(r.basliklar.get('Cache-Control'), 'no-store');
  assert.ok(Math.abs(r.json.simdi - simdiSn()) <= 2);
  assert.deepEqual(r.json.bildirimler.map((x) => [x.yanit_id, x.tur]), [
    [anmaBuyuk, 'anma'], [hepsi, 'alinti'], [anmaTur, 'anma'], [alintiTur, 'alinti'], [yanitTur, 'yanit'],
  ]);
  const ilk = r.json.bildirimler[4];
  assert.deepEqual(Object.keys(ilk).sort(), ['baslik', 'baslik_id', 'kisa', 'olusma', 'rol', 'rumuz', 'tur', 'yanit_id']);
  assert.equal(ilk.kisa.length, 90); assert.equal(ilk.baslik, 'Benim açtığım başlık'); assert.equal(ilk.rumuz, 'Diger_Uye'); assert.equal(ilk.baslik_id, benimBaslik);
  assert.ok(!r.json.bildirimler.some((x) => x.rumuz === 'İpek_Y'));
  // giriş şart
  assert.equal((await cagir(env, 'GET', '/ben/bildirimler')).durum, 401);
});

test('bildirimler: 14 gün penceresi, sonra filtresi, en çok 30', async () => {
  const env = ortam();
  const ben = await uyeGirisi(env, 'Alici_Uye');
  const d = await uyeGirisi(env, 'Yazar_Alti');
  const b = hamBaslik(env, { uye: ben.id });
  const t = simdiSn();
  hamYanit(env, b, d.id, 'çok eski', { olusma: t - 15 * 86400 });
  const yeni1 = hamYanit(env, b, d.id, 'üç gün önce', { olusma: t - 3 * 86400 });
  const yeni2 = hamYanit(env, b, d.id, 'bir saat önce', { olusma: t - 3600 });
  const hepsi = (await cagir(env, 'GET', '/ben/bildirimler', { token: ben.token })).json.bildirimler;
  assert.deepEqual(hepsi.map((x) => x.yanit_id), [yeni2, yeni1]);
  const sonra = (await cagir(env, 'GET', `/ben/bildirimler?sonra=${t - 7200}`, { token: ben.token })).json.bildirimler;
  assert.deepEqual(sonra.map((x) => x.yanit_id), [yeni2]);
  // 14 günden eski sonra değeri pencereyi genişletmez
  assert.equal((await cagir(env, 'GET', '/ben/bildirimler?sonra=0', { token: ben.token })).json.bildirimler.length, 2);
  assert.equal((await cagir(env, 'GET', '/ben/bildirimler?sonra=abc', { token: ben.token })).durum, 400);
  for (let i = 0; i < 40; i++) hamYanit(env, b, d.id, `ek ${i}`, { olusma: t - 100 + i });
  assert.equal((await cagir(env, 'GET', '/ben/bildirimler', { token: ben.token })).json.bildirimler.length, 30);
});

// ---------- üye kartı ----------
test('/uye/:rumuz: alanlar, büyük/küçük harf ve URL çözme, tg_id yok, engelli 404, son 5 ayrı başlık', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Çağrı_Hoca');
  env.DB.ham.prepare('UPDATE uyeler SET itibar = 7 WHERE id = ?').run(u.id);
  const b = [];
  for (let i = 0; i < 7; i++) b.push(hamBaslik(env, { baslik: `Başlık numara ${i}` }));
  for (const id of b) { hamYanit(env, id, u.id, 'bir'); hamYanit(env, id, u.id, 'iki'); }
  const gizliBaslik = hamBaslik(env, { baslik: 'Gizli başlık deneme' });
  hamYanit(env, gizliBaslik, u.id, 'görünmez');
  env.DB.ham.prepare('UPDATE basliklar SET gizli = 1 WHERE id = ?').run(gizliBaslik);
  hamYanit(env, b[0], u.id, 'gizlenmiş yanıt', { gizli: 1 });
  const r = await cagir(env, 'GET', `/uye/${encodeURIComponent('çağrı_hoca')}`);
  assert.equal(r.durum, 200);
  assert.deepEqual(Object.keys(r.json).sort(), ['itibar', 'kayit', 'kurucu', 'mesaj_sayisi', 'rol', 'rumuz', 'son_basliklar']);
  assert.equal(r.json.rumuz, 'Çağrı_Hoca'); assert.equal(r.json.itibar, 7); assert.equal(r.json.rol, 'uye');
  assert.equal(r.json.mesaj_sayisi, 15); assert.equal(r.json.kurucu, true);
  assert.deepEqual(r.json.son_basliklar.map((x) => x.id), [b[6], b[5], b[4], b[3], b[2]]);
  assert.deepEqual(Object.keys(r.json.son_basliklar[0]).sort(), ['baslik', 'id', 'ilan_id']);
  assert.ok(!JSON.stringify(r.json).includes('tg_id'));
  env.DB.ham.prepare('UPDATE uyeler SET engelli = 1 WHERE id = ?').run(u.id);
  assert.equal((await cagir(env, 'GET', `/uye/${encodeURIComponent('Çağrı_Hoca')}`)).durum, 404);
  assert.equal((await cagir(env, 'GET', '/uye/yok_boyle_biri')).durum, 404);
  assert.equal((await cagir(env, 'GET', '/uye/%E0%A4%A')).durum, 404);
});

test('/uye/:rumuz: anonim yanıt önbelleğe açık (onb), /ben/bildirimler asla', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Onbellek_Uye');
  const c = globalThis.caches;
  const depo = new Map();
  globalThis.caches = { default: { match: async (k) => depo.get(k.url)?.clone(), put: async (k, v) => { depo.set(k.url, v); } } };
  try {
    assert.equal((await cagir(env, 'GET', '/uye/Onbellek_Uye')).durum, 200);
    assert.equal(depo.size, 1);
    await cagir(env, 'GET', '/ben/bildirimler', { token: u.token });
    assert.equal(depo.size, 1);
    await cagir(env, 'GET', '/baslik/1/yeni?sonra=0');   // 404: önbelleğe yazılmaz
    assert.equal(depo.size, 1);
  } finally { globalThis.caches = c; }
});

