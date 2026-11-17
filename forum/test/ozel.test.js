import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { ortam, cagir, uyeGirisi, kayitEskit, sahteFetch } from './yardim.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const dosya = (yol) => readFileSync(new URL(yol, import.meta.url), 'utf8');

async function uye(env, rumuz, rol, yeni = false) {
  const u = await uyeGirisi(env, rumuz, rol);
  if (!yeni) kayitEskit(env, u.id);
  return { ...u, rumuz };
}
const dm = (env, kimden, kime, govde) => cagir(env, 'POST', `/ozel/${encodeURIComponent(kime.rumuz)}`, { token: kimden.token, govde: { govde } });
const sorgu = (env, sql, ...p) => env.DB.ham.prepare(sql).all(...p);
const satir = (env, sql, ...p) => env.DB.ham.prepare(sql).get(...p);
const ham = (env, g, a, govde, olusma, ek = {}) => Number(env.DB.ham.prepare('INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma, okundu, gizli) VALUES (?, ?, ?, ?, ?, ?)')
  .run(g, a, govde, olusma, ek.okundu ?? 0, ek.gizli ?? 0).lastInsertRowid);
const simdi = () => Math.floor(Date.now() / 1000);

// ---------- göç ----------
test('göç 0004: 0002+0003 sonrası temiz uygulanır, dm_acik varsayılan 1, indeksler var, taze şemayla aynı', () => {
  const eski = new DatabaseSync(':memory:');
  eski.exec(dosya('./eski-schema.sql'));
  eski.exec('INSERT INTO uyeler (id, tg_id, rumuz, kayit) VALUES (10, 5, \'Eski_U\', 1)');
  eski.exec(dosya('../migrations/0002_ozellikler.sql'));
  eski.exec(dosya('../migrations/0003_odalar.sql'));
  eski.exec(dosya('../migrations/0004_ozel_takip.sql'));
  eski.exec(dosya('../migrations/0005_kayit.sql'));
  assert.equal(eski.prepare('SELECT dm_acik FROM uyeler WHERE id = 10').get().dm_acik, 1);
  const taze = new DatabaseSync(':memory:');
  taze.exec(dosya('../schema.sql'));
  const kolonlar = (db, t) => db.prepare(`PRAGMA table_info(${t})`).all().map((r) => `${r.name}:${r.type}:${r.dflt_value}`).sort();
  for (const t of ['uyeler', 'ozel_mesajlar', 'engeller', 'ozel_sikayetler', 'takipler']) assert.deepEqual(kolonlar(eski, t), kolonlar(taze, t), t);
  const indeks = (db) => db.prepare("SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'").all().map((r) => r.name).sort();
  assert.deepEqual(indeks(eski), indeks(taze));
  assert.ok(indeks(eski).includes('takipler_baslik') && indeks(eski).includes('ozel_alici_okundu'));
  eski.exec(dosya('../migrations/0004_ozel_takip.sql').replace('ALTER TABLE uyeler ADD COLUMN dm_acik INTEGER DEFAULT 1;', ''));   // IF NOT EXISTS: tekrar zararsız
});

// ---------- ayarlar ----------
test('/ben/ayar: dm_acik ve bildirim, doğrulama, /ben ve /uye çıktıları', async () => {
  const env = ortam();
  const a = await uye(env, 'Ayar_A');
  assert.equal((await cagir(env, 'POST', '/ben/ayar', { govde: { dm_acik: false } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ben/ayar', { token: a.token, govde: {} })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/ben/ayar', { token: a.token, govde: { dm_acik: 'hayır' } })).durum, 400);
  const ben0 = await cagir(env, 'GET', '/ben', { token: a.token });
  assert.equal(ben0.json.uye.dm_acik, true); assert.equal(ben0.json.uye.ozel_okunmamis, 0);
  const r = await cagir(env, 'POST', '/ben/ayar', { token: a.token, govde: { dm_acik: false, bildirim: false } });
  assert.equal(r.durum, 200);
  assert.equal(r.json.uye.dm_acik, false); assert.equal(r.json.uye.bildirim, false); assert.equal(r.json.uye.rumuz, 'Ayar_A');
  assert.equal((await cagir(env, 'GET', '/ben', { token: a.token })).json.uye.dm_acik, false);
  assert.equal((await cagir(env, 'GET', '/uye/Ayar_A')).json.dm_acik, false);
  await cagir(env, 'POST', '/ben/ayar', { token: a.token, govde: { dm_acik: true } });
  assert.equal((await cagir(env, 'GET', '/uye/Ayar_A')).json.dm_acik, true);
  assert.equal(satir(env, 'SELECT bildirim FROM uyeler WHERE id = ?', a.id).bildirim, 0);   // verilmeyen alan değişmedi
});

// ---------- gönderme kuralları ----------
test('özel mesaj: temel akış, kendine / sistem / asistan / yasaklı / yok, dm_acik kapalı', async () => {
  const env = ortam();
  const a = await uye(env, 'Ece_A'), b = await uye(env, 'Burak_B'), c = await uye(env, 'Cem_C'), y = await uye(env, 'Yasak_Y');
  assert.equal((await cagir(env, 'POST', '/ozel/Burak_B', { govde: { govde: 'selam' } })).durum, 401);
  const r = await dm(env, a, b, '  Merhaba, nasılsın?  ');
  assert.equal(r.durum, 201);
  assert.deepEqual(Object.keys(r.json.mesaj).sort(), ['benden', 'govde', 'id', 'olusma']);
  assert.equal(r.json.mesaj.govde, 'Merhaba, nasılsın?'); assert.equal(r.json.mesaj.benden, true);
  assert.equal((await dm(env, a, a, 'kendime')).durum, 400);
  assert.equal((await cagir(env, 'POST', '/ozel/YokBoyleBiri', { token: a.token, govde: { govde: 'x' } })).durum, 404);
  const sis = await dm(env, a, { rumuz: 'KPSS Tercihi' }, 'selam'); assert.equal(sis.durum, 403);
  assert.equal((await dm(env, a, { rumuz: 'Asistan' }, 'selam')).durum, 403);
  await cagir(env, 'POST', '/yonetim/engelle', { basliklar: YONETICI, govde: { uye_id: y.id, engelli: true } });
  assert.equal((await dm(env, a, y, 'selam')).durum, 404);
  assert.equal((await cagir(env, 'POST', '/ozel/Ece_A', { token: y.token, govde: { govde: 'x' } })).durum, 403);   // yasaklı yazamaz
  // dm_acik = 0
  await cagir(env, 'POST', '/ben/ayar', { token: c.token, govde: { dm_acik: false } });
  const kapali = await dm(env, a, c, 'selam');
  assert.equal(kapali.durum, 403); assert.equal(kapali.json.hata, 'Bu üye özel mesaj almıyor.');
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM ozel_mesajlar').n, 1);
  // başkasına kapalı olması kendi gönderimini engellemez
  assert.equal((await dm(env, c, a, 'merhaba')).durum, 201);
});

test('özel mesaj: gövde 1-2000 karakter ve denetim (422)', async () => {
  const env = ortam();
  const a = await uye(env, 'Den_A'), b = await uye(env, 'Den_B');
  assert.equal((await dm(env, a, b, '   ')).durum, 400);
  assert.equal((await dm(env, a, b, 'x'.repeat(2001))).durum, 400);
  assert.equal((await dm(env, a, b, 'Beni ara 0532 123 45 67')).durum, 422);
  assert.equal((await dm(env, a, b, 'mail: ali@ornek.com')).durum, 422);
  assert.equal((await dm(env, a, b, 'siktir git')).durum, 422);
  assert.equal((await dm(env, a, b, 'bak https://kotu-site.xyz/abc')).durum, 422);
  assert.equal((await dm(env, a, b, 'a'.repeat(2000))).durum, 422);   // tekrar/bağırma denetimi
  assert.equal((await dm(env, a, b, 'Gayet normal bir mesaj. '.repeat(10))).durum, 201);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM ozel_mesajlar').n, 1);
});

test('özel mesaj: engelleme iki yönde de gönderimi durdurur, kaldırınca açılır', async () => {
  const env = ortam();
  const a = await uye(env, 'Eng_A'), b = await uye(env, 'Eng_B');
  assert.equal((await dm(env, a, b, 'selam')).durum, 201);
  assert.equal((await cagir(env, 'POST', '/ozel/Eng_A/engelle', { token: b.token, govde: { engel: 'evet' } })).durum, 400);
  const e = await cagir(env, 'POST', '/ozel/Eng_A/engelle', { token: b.token, govde: { engel: true } });
  assert.deepEqual(e.json, { engelledim: true });
  const bana = await dm(env, a, b, 'tekrar');
  assert.equal(bana.durum, 403); assert.equal(bana.json.hata, 'Bu üyeye mesaj gönderemezsin.');
  const ben = await dm(env, b, a, 'sen de');
  assert.equal(ben.durum, 403); assert.equal(ben.json.hata, 'Bu üyeye mesaj gönderemezsin.');
  const liste = await cagir(env, 'GET', '/ben/engellenenler', { token: b.token });
  assert.deepEqual(liste.json, { uyeler: [{ rumuz: 'Eng_A' }] });
  assert.deepEqual((await cagir(env, 'GET', '/ben/engellenenler', { token: a.token })).json, { uyeler: [] });
  assert.equal((await cagir(env, 'GET', '/ben/engellenenler')).durum, 401);
  // konuşma bayrakları
  const k = await cagir(env, 'GET', '/ozel/Eng_B', { token: a.token });
  assert.equal(k.json.engellendim, true); assert.equal(k.json.engelledim, false);
  const k2 = await cagir(env, 'GET', '/ozel/Eng_A', { token: b.token });
  assert.equal(k2.json.engelledim, true); assert.equal(k2.json.engellendim, false);
  assert.deepEqual((await cagir(env, 'POST', '/ozel/Eng_A/engelle', { token: b.token, govde: { engel: false } })).json, { engelledim: false });
  assert.equal((await dm(env, a, b, 'barıştık')).durum, 201);
  assert.equal((await cagir(env, 'POST', '/ozel/Eng_B/engelle', { token: b.token, govde: { engel: true } })).durum, 400);   // kendini engelleyemez
  assert.equal((await cagir(env, 'POST', '/ozel/Yok_U/engelle', { token: b.token, govde: { engel: true } })).durum, 404);
});

test('özel mesaj: yeni hesap kapısı (1 günden genç ve 3 mesajdan az)', async () => {
  const env = ortam();
  const yeni = await uye(env, 'Yeni_Y', undefined, true), eski = await uye(env, 'Eski_E');
  const k = await dm(env, yeni, eski, 'selam');
  assert.equal(k.durum, 403);
  assert.equal(k.json.hata, 'Özel mesaj için hesabının en az 1 günlük olması ya da forumda 3 mesajının olması gerekir.');
  // 3 forum mesajı kapıyı açar (yanıtlar; gizli olanlar sayılmaz)
  const t = Number(env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('puan', 'deneme başlığı', 'x', 1, 1, 1)").run().lastInsertRowid);
  const yanit = (gizli) => env.DB.ham.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, gizli) VALUES (?, ?, ?, ?, ?)').run(t, yeni.id, 'yanıt', simdi(), gizli);
  yanit(0); yanit(0); yanit(1);
  assert.equal((await dm(env, yeni, eski, 'selam')).durum, 403);
  yanit(0);
  assert.equal((await dm(env, yeni, eski, 'selam')).durum, 201);
  // 1 günü dolduran hesap mesaj sayısına bakılmaz
  const g = await uye(env, 'Gunluk_G', undefined, true);
  env.DB.ham.prepare('UPDATE uyeler SET kayit = ? WHERE id = ?').run(simdi() - 90000, g.id);
  assert.equal((await dm(env, g, eski, 'selam')).durum, 201);
});

test('özel mesaj: karşı taraf yanıt verene kadar en çok 3 mesaj, yanıt kilidi açar', async () => {
  const env = ortam();
  const a = await uye(env, 'Sir_A'), b = await uye(env, 'Sir_B'), c = await uye(env, 'Sir_C');
  for (let i = 1; i <= 3; i++) assert.equal((await dm(env, a, b, `mesaj ${i}`)).durum, 201);
  const d = await dm(env, a, b, 'dördüncü');
  assert.equal(d.durum, 403); assert.equal(d.json.hata, 'Karşı taraf yanıt verene kadar en fazla 3 mesaj gönderebilirsin.');
  // başka kişiye serbest
  assert.equal((await dm(env, a, c, 'selam')).durum, 201);
  // gönderen mesajları gizlese de sayılır
  const id = satir(env, 'SELECT MIN(id) AS id FROM ozel_mesajlar WHERE alici = ?', b.id).id;
  await cagir(env, 'DELETE', `/ozel/mesaj/${id}`, { token: a.token });
  assert.equal((await dm(env, a, b, 'gizledim, yine de')).durum, 403);
  // yanıt gelince açılır
  assert.equal((await dm(env, b, a, 'tamam, buradayım')).durum, 201);
  assert.equal((await dm(env, a, b, 'teşekkürler')).durum, 201);
  assert.equal((await dm(env, a, b, 'ikinci')).durum, 201);
  assert.equal((await dm(env, a, b, 'üçüncü')).durum, 201);
  assert.equal((await dm(env, a, b, 'dördüncü')).durum, 403);
  // kural simetrik: a'nın son mesajından sonra b de en çok 3 mesaj atabilir
  for (let i = 0; i < 3; i++) assert.equal((await dm(env, b, a, `b mesajı ${i}`)).durum, 201);
  assert.equal((await dm(env, b, a, 'dördüncü')).durum, 403);
});

test('özel mesaj: saatte 20, günde 100 hız sınırı (429)', async () => {
  const env = ortam();
  const a = await uye(env, 'Hiz_A'), b = await uye(env, 'Hiz_B');
  const t = simdi();
  for (let i = 0; i < 19; i++) ham(env, a.id, 500 + i, 'x', t - 60);   // başka alıcılar; son saatte 19 mesaj
  b && assert.equal((await dm(env, a, b, 'yirminci')).durum, 201);
  const s = await dm(env, a, await uye(env, 'Hiz_C'), 'yirmibirinci');
  assert.equal(s.durum, 429); assert.match(s.json.hata, /Saatte en fazla 20/);
  // 1 saatten eski ama bir günden yeni mesajlar günlük sınıra sayılır
  const env2 = ortam();
  const d = await uye(env2, 'Gun_D'), e = await uye(env2, 'Gun_E');
  for (let i = 0; i < 100; i++) ham(env2, d.id, 700 + i, 'x', t - 7200);
  const g = await dm(env2, d, e, 'yüz bir');
  assert.equal(g.durum, 429); assert.match(g.json.hata, /Bugün için özel mesaj sınırı/);
  // bir günden eskiler sayılmaz
  const env3 = ortam();
  const f = await uye(env3, 'Eski_F'), h = await uye(env3, 'Eski_H');
  for (let i = 0; i < 150; i++) ham(env3, f.id, 900 + i, 'x', t - 90000);
  assert.equal((await dm(env3, f, h, 'serbest')).durum, 201);
});

// ---------- okuma, işaretleme, sayfalama ----------
test('konuşma: okundu işareti, toplam_okunmamis, /ben.ozel_okunmamis, /yeni yoklama', async () => {
  const env = ortam();
  const a = await uye(env, 'Oku_A'), b = await uye(env, 'Oku_B');
  await dm(env, a, b, 'bir'); await dm(env, a, b, 'iki');
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 2);
  assert.equal((await cagir(env, 'GET', '/ben', { token: a.token })).json.uye.ozel_okunmamis, 0);
  const liste = await cagir(env, 'GET', '/ozel', { token: b.token });
  assert.equal(liste.json.toplam_okunmamis, 2);
  assert.equal(liste.json.konusmalar.length, 1);
  const k = liste.json.konusmalar[0];
  assert.deepEqual(Object.keys(k).sort(), ['av', 'itibar', 'kurucu', 'okunmamis', 'rol', 'rumuz', 'son']);
  assert.equal(k.rumuz, 'Oku_A'); assert.equal(k.okunmamis, 2); assert.equal(k.son.govde, 'iki'); assert.equal(k.son.benden, false);
  // listeyi görmek okundu yapmaz
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 2);
  // gönderenin görünümü: okunmamış yok, son mesaj benden
  const ga = (await cagir(env, 'GET', '/ozel', { token: a.token })).json;
  assert.equal(ga.konusmalar[0].okunmamis, 0); assert.equal(ga.konusmalar[0].son.benden, true); assert.equal(ga.toplam_okunmamis, 0);
  const c = await cagir(env, 'GET', '/ozel/Oku_A', { token: b.token });
  assert.equal(c.durum, 200);
  const { av: oAv, ...oUye } = c.json.uye;
  assert.match(oAv, /^px\.[a-z]+:pixel\.\d+$/);   // her üyenin bir piksel karakteri var
  assert.deepEqual(oUye, { rumuz: 'Oku_A', rol: 'uye', kurucu: true, itibar: 0, dm_acik: true });
  assert.deepEqual(c.json.mesajlar.map((m) => [m.govde, m.benden]), [['bir', false], ['iki', false]]);
  assert.deepEqual(Object.keys(c.json.mesajlar[0]).sort(), ['benden', 'govde', 'id', 'olusma']);
  assert.equal(c.json.daha_eski, false); assert.equal(c.json.engelledim, false); assert.equal(c.json.engellendim, false);
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 0);
  assert.equal((await cagir(env, 'GET', '/ozel', { token: b.token })).json.toplam_okunmamis, 0);
  // yoklama: yeni gelen okundu olur, boşsa sorgu yok
  const son = c.json.mesajlar.at(-1).id;
  assert.deepEqual((await cagir(env, 'GET', `/ozel/Oku_A/yeni?sonra=${son}`, { token: b.token })).json, { mesajlar: [] });
  await dm(env, a, b, 'üç');
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 1);
  const y = await cagir(env, 'GET', `/ozel/Oku_A/yeni?sonra=${son}`, { token: b.token });
  assert.deepEqual(y.json.mesajlar.map((m) => m.govde), ['üç']);
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 0);
  assert.equal((await cagir(env, 'GET', '/ozel/Oku_A/yeni', { token: b.token })).durum, 400);
  assert.equal((await cagir(env, 'GET', '/ozel/Oku_A/yeni?sonra=x', { token: b.token })).durum, 400);
  assert.equal((await cagir(env, 'GET', '/ozel/Yok_Y/yeni?sonra=0', { token: b.token })).durum, 404);
  // kimlik doğrulama ve önbellek
  for (const yol of ['/ozel', '/ozel/Oku_A', '/ozel/Oku_A/yeni?sonra=0']) {
    assert.equal((await cagir(env, 'GET', yol)).durum, 401, yol);
    const r = await cagir(env, 'GET', yol, { token: b.token });
    assert.equal(r.basliklar.get('Cache-Control'), 'no-store', yol);
  }
});

test('konuşma: oku işareti tek UPDATE ve yalnız okunmamış varken; yoklama yazma yapmaz', async () => {
  const env = ortam();
  const a = await uye(env, 'Yaz_A'), b = await uye(env, 'Yaz_B');
  await dm(env, a, b, 'selam');
  const yazma = () => env.DB.sayac.sorgu;
  await cagir(env, 'GET', '/ozel/Yaz_A', { token: b.token });   // oku
  const once = satir(env, 'SELECT COUNT(*) AS n FROM ozel_mesajlar WHERE okundu = 1').n;
  assert.equal(once, 1);
  const s1 = yazma();
  await cagir(env, 'GET', '/ozel/Yaz_A', { token: b.token });   // hepsi okunmuş: UPDATE yok
  const harcanan = yazma() - s1;
  await dm(env, a, b, 'ikinci');
  const s2 = yazma();
  await cagir(env, 'GET', '/ozel/Yaz_A', { token: b.token });
  assert.equal(yazma() - s2, harcanan + 1);   // okunmamış varken tam bir ek UPDATE
});

test('konuşma: 50 sınırı, once ile eskiye sayfalama, gizli ve karşı tarafın mesajı', async () => {
  const env = ortam();
  const a = await uye(env, 'Say_A'), b = await uye(env, 'Say_B');
  const t = simdi();
  const idler = [];
  for (let i = 1; i <= 60; i++) idler.push(ham(env, i % 2 ? a.id : b.id, i % 2 ? b.id : a.id, `m${i}`, t - 1000 + i));
  const gizli = ham(env, a.id, b.id, 'gizli olan', t, { gizli: 1 });
  assert.ok(gizli > idler.at(-1));
  const s1 = await cagir(env, 'GET', '/ozel/Say_B', { token: a.token });
  assert.equal(s1.json.mesajlar.length, 50); assert.equal(s1.json.daha_eski, true);
  assert.equal(s1.json.mesajlar[0].govde, 'm11'); assert.equal(s1.json.mesajlar.at(-1).govde, 'm60');
  assert.ok(!s1.json.mesajlar.some((m) => m.govde === 'gizli olan'));
  assert.equal(s1.json.mesajlar[0].benden, true); assert.equal(s1.json.mesajlar[1].benden, false);
  const s2 = await cagir(env, 'GET', `/ozel/Say_B?once=${s1.json.mesajlar[0].id}`, { token: a.token });
  assert.equal(s2.json.mesajlar.length, 10); assert.equal(s2.json.daha_eski, false);
  assert.equal(s2.json.mesajlar[0].govde, 'm1'); assert.equal(s2.json.mesajlar.at(-1).govde, 'm10');
  assert.equal((await cagir(env, 'GET', '/ozel/Say_B?once=abc', { token: a.token })).durum, 400);
  // son mesaj gizliyse listede bir önceki görünür
  const l = await cagir(env, 'GET', '/ozel', { token: a.token });
  assert.equal(l.json.konusmalar[0].son.govde, 'm60');
  // 80 karakterlik özet
  ham(env, b.id, a.id, 'u'.repeat(300), t + 5);
  assert.equal((await cagir(env, 'GET', '/ozel', { token: a.token })).json.konusmalar[0].son.govde.length, 80);
});

test('konuşma: yok / yasaklı üye 404', async () => {
  const env = ortam();
  const a = await uye(env, 'Yk_A'), y = await uye(env, 'Yk_Y');
  ham(env, y.id, a.id, 'eskiden', simdi() - 50);
  assert.equal((await cagir(env, 'GET', '/ozel/Yk_Y', { token: a.token })).durum, 200);
  assert.equal((await cagir(env, 'GET', '/ozel', { token: a.token })).json.konusmalar.length, 1);
  await cagir(env, 'POST', '/yonetim/engelle', { basliklar: YONETICI, govde: { uye_id: y.id, engelli: true } });
  assert.equal((await cagir(env, 'GET', '/ozel/Yk_Y', { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ozel/Hic_Yok', { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ozel', { token: a.token })).json.konusmalar.length, 0);   // yasaklı eş listede yok
  // Türkçe rumuz (URL kodlu) bulunur
  const ip = await uye(env, 'İpek_Y');
  await dm(env, ip, a, 'merhaba');
  assert.equal((await cagir(env, 'GET', `/ozel/${encodeURIComponent('İpek_Y')}`, { token: a.token })).durum, 200);
});

test('konuşma listesi: engellenen eş çıkar, okunmamış sayılmaz; en yeni üstte, en çok 50', async () => {
  const env = ortam();
  const a = await uye(env, 'Lst_A'), b = await uye(env, 'Lst_B'), c = await uye(env, 'Lst_C');
  const t = simdi();
  ham(env, b.id, a.id, 'b den', t - 300); ham(env, c.id, a.id, 'c den', t - 200);
  ham(env, a.id, b.id, 'a dan b ye', t - 100);
  let l = (await cagir(env, 'GET', '/ozel', { token: a.token })).json;
  assert.deepEqual(l.konusmalar.map((k) => [k.rumuz, k.okunmamis]), [['Lst_B', 1], ['Lst_C', 1]]);
  assert.equal(l.toplam_okunmamis, 2);
  ham(env, c.id, a.id, 'c yine', t - 50);
  l = (await cagir(env, 'GET', '/ozel', { token: a.token })).json;
  assert.deepEqual(l.konusmalar.map((k) => [k.rumuz, k.okunmamis]), [['Lst_C', 2], ['Lst_B', 1]]);
  await cagir(env, 'POST', '/ozel/Lst_C/engelle', { token: a.token, govde: { engel: true } });
  l = (await cagir(env, 'GET', '/ozel', { token: a.token })).json;
  assert.deepEqual(l.konusmalar.map((k) => k.rumuz), ['Lst_B']);
  assert.equal(l.toplam_okunmamis, 1);
  assert.equal((await cagir(env, 'GET', '/ben', { token: a.token })).json.uye.ozel_okunmamis, 1);
  // 50 sınırı
  for (let i = 0; i < 60; i++) ham(env, 2000 + i, a.id, 'x', t - 10 + (i % 5));
  env.DB.ham.exec("INSERT OR IGNORE INTO uyeler (id, rumuz, kayit, rol) SELECT 2000 + value, 'Dolgu' || value, 1, 'uye' FROM (WITH RECURSIVE s(value) AS (SELECT 0 UNION ALL SELECT value + 1 FROM s WHERE value < 59) SELECT value FROM s)");
  l = (await cagir(env, 'GET', '/ozel', { token: a.token })).json;
  assert.equal(l.konusmalar.length, 50);
});

// ---------- silme, şikayet ----------
test('DELETE /ozel/mesaj/:id: yalnız gönderen gizler, gizli her yerde dışlanır', async () => {
  const env = ortam();
  const a = await uye(env, 'Sil_A'), b = await uye(env, 'Sil_B');
  const m = (await dm(env, a, b, 'silinecek')).json.mesaj;
  assert.equal((await cagir(env, 'DELETE', `/ozel/mesaj/${m.id}`)).durum, 401);
  assert.equal((await cagir(env, 'DELETE', `/ozel/mesaj/${m.id}`, { token: b.token })).durum, 403);
  assert.equal((await cagir(env, 'DELETE', '/ozel/mesaj/99999', { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 1);
  assert.deepEqual((await cagir(env, 'DELETE', `/ozel/mesaj/${m.id}`, { token: a.token })).json, { tamam: true });
  assert.equal(satir(env, 'SELECT gizli FROM ozel_mesajlar WHERE id = ?', m.id).gizli, 1);
  assert.equal((await cagir(env, 'DELETE', `/ozel/mesaj/${m.id}`, { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ben', { token: b.token })).json.uye.ozel_okunmamis, 0);
  assert.equal((await cagir(env, 'GET', '/ozel', { token: b.token })).json.konusmalar.length, 0);
  assert.equal((await cagir(env, 'GET', '/ozel/Sil_A', { token: b.token })).json.mesajlar.length, 0);
  assert.equal((await cagir(env, 'GET', `/ozel/Sil_A/yeni?sonra=0`, { token: b.token })).json.mesajlar.length, 0);
  assert.equal((await cagir(env, 'GET', '/ozel/Sil_B', { token: a.token })).json.mesajlar.length, 0);
});

test('şikayet: kayıt, otomatik engel, günde bir, yönetici listesi mesaj metniyle', async () => {
  const env = ortam();
  const a = await uye(env, 'Sk_A'), b = await uye(env, 'Sk_B');
  const m1 = (await dm(env, b, a, 'rahatsız edici mesaj')).json.mesaj;
  await dm(env, b, a, 'bir tane daha');
  assert.equal((await cagir(env, 'POST', '/ozel/Sk_B/sikayet', { govde: {} })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ozel/Sk_A/sikayet', { token: a.token, govde: {} })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/ozel/Yok_X/sikayet', { token: a.token, govde: {} })).durum, 404);
  assert.equal((await cagir(env, 'POST', '/ozel/Sk_B/sikayet', { token: a.token, govde: { mesaj_id: 'x' } })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/ozel/Sk_B/sikayet', { token: a.token, govde: { mesaj_id: 9999 } })).durum, 400);
  const r = await cagir(env, 'POST', '/ozel/Sk_B/sikayet', { token: a.token, govde: { mesaj_id: m1.id } });
  assert.equal(r.durum, 200); assert.equal(r.json.tamam, true); assert.equal(r.json.engelledim, true);
  // otomatik engel
  assert.equal((await dm(env, b, a, 'tekrar')).durum, 403);
  assert.equal((await dm(env, a, b, 'sen de')).durum, 403);
  assert.deepEqual((await cagir(env, 'GET', '/ben/engellenenler', { token: a.token })).json.uyeler, [{ rumuz: 'Sk_B' }]);
  assert.equal((await cagir(env, 'GET', '/ben', { token: a.token })).json.uye.ozel_okunmamis, 0);   // engelli kişiden gelen sayılmaz
  // günde bir kayıt
  const ikinci = await cagir(env, 'POST', '/ozel/Sk_B/sikayet', { token: a.token, govde: {} });
  assert.equal(ikinci.json.zaten, true);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM ozel_sikayetler').n, 1);
  // bir gün sonra yeniden (mesaj_id verilmezse son mesaj)
  env.DB.ham.prepare('UPDATE ozel_sikayetler SET olusma = olusma - 90000').run();
  await cagir(env, 'POST', '/ozel/Sk_B/sikayet', { token: a.token, govde: {} });
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM ozel_sikayetler').n, 2);
  const son = satir(env, 'SELECT mesaj_id FROM ozel_sikayetler ORDER BY id DESC LIMIT 1');
  assert.equal(son.mesaj_id, satir(env, "SELECT MAX(id) AS id FROM ozel_mesajlar WHERE gonderen = ?", b.id).id);
  // yönetici
  assert.equal((await cagir(env, 'GET', '/yonetim/ozel-sikayetler')).durum, 401);
  assert.equal((await cagir(env, 'GET', '/yonetim/ozel-sikayetler', { token: a.token })).durum, 401);
  const y = await cagir(env, 'GET', '/yonetim/ozel-sikayetler', { basliklar: YONETICI });
  assert.equal(y.durum, 200); assert.equal(y.json.sikayetler.length, 2);
  const ilk = y.json.sikayetler[1];
  assert.equal(ilk.govde, 'rahatsız edici mesaj'); assert.equal(ilk.mesaj_id, m1.id);
  assert.equal(ilk.sikayet_eden.rumuz, 'Sk_A'); assert.equal(ilk.sikayet_edilen.rumuz, 'Sk_B'); assert.equal(ilk.sikayet_edilen.engelli, false);
  // gönderen mesajı gizlese bile yönetici görür
  await cagir(env, 'DELETE', `/ozel/mesaj/${m1.id}`, { token: b.token });
  const y2 = await cagir(env, 'GET', '/yonetim/ozel-sikayetler', { basliklar: YONETICI });
  const g = y2.json.sikayetler.find((x) => x.mesaj_id === m1.id);
  assert.equal(g.govde, 'rahatsız edici mesaj'); assert.equal(g.gizli, true);
});

// ---------- Telegram bildirimi ----------
test('özel mesaj Telegram bildirimi: metin içermez, bildirim kapalı/yerel/tokensiz atlanır, 10 dk aynı çift tek', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const a = await uye(env, 'İpek_G'), b = await uye(env, 'Tg_B'), c = await uye(env, 'Tg_C'), d = await uye(env, 'Tg_D');
    env.DB.ham.prepare('UPDATE uyeler SET tg_id = ? WHERE id = ?').run(401, b.id);
    env.DB.ham.prepare('UPDATE uyeler SET tg_id = ?, bildirim = 0 WHERE id = ?').run(402, c.id);
    const tg = () => f.cagrilar.filter((x) => x.url.startsWith('https://api.telegram.org/'));
    const SIR = 'çok gizli özel cümle 12345';
    assert.equal((await dm(env, a, b, SIR)).durum, 201);
    assert.equal(tg().length, 1);
    const g = JSON.parse(tg()[0].secenek.body);
    assert.equal(g.chat_id, 401);
    assert.equal(g.text, `İpek_G sana özel mesaj gönderdi\nhttps://kpsstercihi.com/forum/?mesaj=${encodeURIComponent('İpek_G')}`);
    assert.ok(!g.text.includes('gizli') && !g.text.includes('12345'));
    assert.ok(!JSON.stringify(tg()[0].secenek).includes('çok gizli'));
    // aynı çift 10 dakika içinde tek bildirim
    await dm(env, a, b, 'ikinci mesaj');
    assert.equal(tg().length, 1);
    // farklı gönderen için ayrı
    assert.equal((await dm(env, d, b, 'selam')).durum, 201);
    assert.equal(tg().length, 2);
    // bildirim kapalı, tg_id yok
    await dm(env, a, c, 'selam'); await dm(env, a, d, 'selam');
    assert.equal(tg().length, 2);
    // yerel ve tokensiz
    const yerel = ortam({ ORTAM: 'yerel' });
    const y1 = await uye(yerel, 'Yer_A'), y2 = await uye(yerel, 'Yer_B');
    yerel.DB.ham.prepare('UPDATE uyeler SET tg_id = 7 WHERE id = ?').run(y2.id);
    await dm(yerel, y1, y2, 'selam');
    const e2 = ortam({ TELEGRAM_BOT_TOKEN: undefined });
    const t1 = await uye(e2, 'Tok_A'), t2 = await uye(e2, 'Tok_B');
    e2.DB.ham.prepare('UPDATE uyeler SET tg_id = 8 WHERE id = ?').run(t2.id);
    await dm(e2, t1, t2, 'selam');
    assert.equal(tg().length, 2);
  } finally { f.geri(); }
});
