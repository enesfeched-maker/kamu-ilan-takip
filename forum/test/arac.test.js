// Gizli yönetici araçları (src/arac.js), yalnız piksel avatarlar, sohbet odası hız sınırı ve 0006 göçü.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ortam, cagir, uyeGirisi, kayitEskit } from './yardim.js';
import { uyeOlustur } from '../src/index.js';
import { ipSinirSifirla, ODA_SINIRI } from '../src/hiz.js';
import { pxNormalle, rastgelePx, PX_ADLAR, MUHTAR_AVATAR, ESKI_SVG_PX, ESKI_RENK_TON } from '../src/kart.js';
import { sahteD1 } from './sahte-d1.js';

const satir = (env, sql, ...p) => env.DB.ham.prepare(sql).get(...p);
const sayi = (env, sql, ...p) => satir(env, sql, ...p).n;
const yap = (env, sql, ...p) => env.DB.ham.prepare(sql).run(...p);
const t0 = () => Math.floor(Date.now() / 1000);
function yoneticiYap(env, id) { yap(env, 'INSERT INTO gizli_yoneticiler (uye_id) VALUES (?)', id); }
function baslikAc(env, uyeId, kategori = 'puan', baslik = 'Deneme sorusu başlığı') {
  const t = t0();
  return Number(yap(env, 'INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES (?, ?, ?, ?, ?, ?)', kategori, baslik, 'gövde metni', uyeId, t, t).lastInsertRowid);
}
function yanitEkle(env, baslikId, uyeId, govde = 'cevap metni', faydali = 0, ust = null) {
  const id = Number(yap(env, 'INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, faydali, ust_id) VALUES (?, ?, ?, ?, ?, ?)', baslikId, uyeId, govde, t0() - 3600, faydali, ust).lastInsertRowid);
  yap(env, 'UPDATE basliklar SET yanit_sayisi = yanit_sayisi + 1 WHERE id = ?', baslikId);
  return id;
}

test('gizli yönetici: /ben/arac yalnız yöneticiye 200, diğer herkese 404; araçlar girişsize 401, üyeye 403', async () => {
  const env = ortam();
  const y = await uyeGirisi(env, 'Mahalle_Yonet');
  const u = await uyeGirisi(env, 'Siradan_Uye');
  yoneticiYap(env, y.id);
  assert.equal((await cagir(env, 'GET', '/ben/arac')).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ben/arac', { token: u.token })).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ben/arac', { token: y.token })).durum, 200);
  const b = baslikAc(env, u.id);
  const yid = yanitEkle(env, b, u.id);
  for (const [yontem, yol] of [['DELETE', `/arac/yanit/${yid}`], ['DELETE', `/arac/baslik/${b}`], ['DELETE', '/arac/ozel/1'], ['POST', '/arac/uye/Mahalle_Yonet/kapat']]) {
    assert.equal((await cagir(env, yontem, yol)).durum, 401, yol);
    assert.equal((await cagir(env, yontem, yol, { token: u.token })).durum, 403, yol);
  }
  // eski X-Yonetici anahtarı bu araçlara yetki vermez; satırlar yerinde
  assert.equal((await cagir(env, 'DELETE', `/arac/yanit/${yid}`, { token: u.token, basliklar: { 'X-Yonetici': 'yonetici-anahtar' } })).durum, 403);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM yanitlar WHERE id = ?', yid), 1);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM basliklar WHERE id = ?', b), 1);
});

test('gizli yönetici: rol hiçbir çıktıda sızmaz (/ben, /uye, listeler, başlık, bildirim, özel konuşma)', async () => {
  const env = ortam();
  const y = await uyeGirisi(env, 'Gizli_Muhtar');
  const u = await uyeGirisi(env, 'Komsu_Uye');
  const ben0 = (await cagir(env, 'GET', '/ben', { token: y.token })).json;
  yoneticiYap(env, y.id);
  const ben1 = (await cagir(env, 'GET', '/ben', { token: y.token })).json;
  assert.deepEqual(ben1, ben0);   // yönetici olmak /ben'i hiç değiştirmez
  assert.equal(ben1.uye.rol, 'uye');
  const b = baslikAc(env, y.id, 'puan', 'Yöneticinin açtığı soru');
  yanitEkle(env, b, y.id, '@Komsu_Uye merhaba');
  const ciktilar = [
    (await cagir(env, 'GET', '/uye/Gizli_Muhtar')).json,
    (await cagir(env, 'GET', '/uye/Gizli_Muhtar?tam=1', { token: u.token })).json,
    (await cagir(env, 'GET', '/basliklar')).json,
    (await cagir(env, 'GET', `/baslik/${b}`)).json,
    (await cagir(env, 'GET', '/son')).json,
    (await cagir(env, 'GET', '/ben/bildirimler', { token: u.token })).json,
  ];
  for (const c of ciktilar) {
    const m = JSON.stringify(c);
    assert.ok(!/yonetici|gizli_yonetici|arac/.test(m), m);
  }
  assert.equal(ciktilar[0].rol, 'uye'); assert.equal(ciktilar[3].baslik.rol, 'uye'); assert.equal(ciktilar[3].yanitlar[0].rol, 'uye');
});

test('yönetici sil: cevap kalıcı silinir (yer tutucu yok), sayaçlar ve itibar düşer, ona verilen yanıtlar alıntısız kalır', async () => {
  const env = ortam();
  const y = await uyeGirisi(env, 'Sil_Bakici'); yoneticiYap(env, y.id);
  const a = await uyeGirisi(env, 'Yazar_Uye');
  const c = await uyeGirisi(env, 'Oy_Veren');
  const b = baslikAc(env, c.id);
  const hedef = yanitEkle(env, b, a.id, 'silinecek cevap', 2);
  yap(env, 'UPDATE uyeler SET itibar = 5 WHERE id = ?', a.id);
  yap(env, 'INSERT INTO oylar (yanit_id, uye_id) VALUES (?, ?)', hedef, c.id);
  yap(env, 'INSERT INTO sikayetler (yanit_id, uye_id) VALUES (?, ?)', hedef, c.id);
  const cocuk = yanitEkle(env, b, c.id, 'yanıt veren', 0, hedef);
  assert.equal(satir(env, 'SELECT yanit_sayisi FROM basliklar WHERE id = ?', b).yanit_sayisi, 2);
  const r = await cagir(env, 'DELETE', `/arac/yanit/${hedef}`, { token: y.token });
  assert.equal(r.durum, 200);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM yanitlar WHERE id = ?', hedef), 0);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM oylar WHERE yanit_id = ?', hedef), 0);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM sikayetler WHERE yanit_id = ?', hedef), 0);
  assert.equal(satir(env, 'SELECT yanit_sayisi FROM basliklar WHERE id = ?', b).yanit_sayisi, 1);
  assert.equal(satir(env, 'SELECT itibar FROM uyeler WHERE id = ?', a.id).itibar, 3);
  assert.equal(satir(env, 'SELECT ust_id FROM yanitlar WHERE id = ?', cocuk).ust_id, null);
  const g = (await cagir(env, 'GET', `/baslik/${b}`)).json;
  assert.deepEqual(g.yanitlar.map((x) => x.govde), ['yanıt veren']);
  assert.ok(!JSON.stringify(g).includes('silinecek'));
  assert.equal((await cagir(env, 'DELETE', `/arac/yanit/${hedef}`, { token: y.token })).durum, 404);
});

test('yönetici sil: soru bütün cevapları, oyları, anketi ve takipleriyle kalıcı silinir; sohbet odası silinmez', async () => {
  const env = ortam();
  const y = await uyeGirisi(env, 'Soru_Silen'); yoneticiYap(env, y.id);
  const a = await uyeGirisi(env, 'Soru_Sahibi');
  const c = await uyeGirisi(env, 'Cevap_Veren');
  const b = baslikAc(env, a.id);
  const cv = yanitEkle(env, b, c.id, 'faydalı cevap', 3);
  yap(env, 'UPDATE uyeler SET itibar = 4 WHERE id = ?', c.id);
  yap(env, 'INSERT INTO oylar (yanit_id, uye_id) VALUES (?, ?)', cv, a.id);
  yap(env, 'INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)', a.id, b, t0());
  yap(env, 'INSERT INTO anket_secenekleri (baslik_id, sira, metin, oy) VALUES (?, 1, ?, 1)', b, 'Evet');
  assert.equal((await cagir(env, 'DELETE', `/arac/baslik/${b}`, { token: y.token })).durum, 200);
  for (const [tablo, kosul] of [['basliklar', 'id'], ['yanitlar', 'baslik_id'], ['takipler', 'baslik_id'], ['anket_secenekleri', 'baslik_id']]) {
    assert.equal(sayi(env, `SELECT COUNT(*) AS n FROM ${tablo} WHERE ${kosul} = ?`, b), 0, tablo);
  }
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM oylar WHERE yanit_id = ?', cv), 0);
  assert.equal(satir(env, 'SELECT itibar FROM uyeler WHERE id = ?', c.id).itibar, 1);
  assert.equal((await cagir(env, 'GET', `/baslik/${b}`)).durum, 404);
  const oda = baslikAc(env, 1, 'oda', 'Deneme sohbet odası');
  assert.equal((await cagir(env, 'DELETE', `/arac/baslik/${oda}`, { token: y.token })).durum, 400);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM basliklar WHERE id = ?', oda), 1);
});

test('yönetici sil: özel mesaj (karşı tarafınki dahil) kalıcı silinir', async () => {
  const env = ortam();
  const y = await uyeGirisi(env, 'Dm_Bakici'); yoneticiYap(env, y.id);
  const a = await uyeGirisi(env, 'Dm_Yazan');
  const id = Number(yap(env, 'INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma) VALUES (?, ?, ?, ?)', a.id, y.id, 'rahatsız edici', t0()).lastInsertRowid);
  assert.equal((await cagir(env, 'DELETE', `/arac/ozel/${id}`, { token: a.token })).durum, 403);
  assert.equal((await cagir(env, 'DELETE', `/arac/ozel/${id}`, { token: y.token })).durum, 200);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM ozel_mesajlar WHERE id = ?', id), 0);
  assert.equal((await cagir(env, 'DELETE', `/arac/ozel/${id}`, { token: y.token })).durum, 404);
});

test('hesabı kapat: hesap ve bütün içeriği kalıcı silinir, sayaçlar düzelir, aynı Google / Telegram / e-postayla yeniden üye olunamaz', async () => {
  const env = ortam();
  const y = await uyeGirisi(env, 'Kapatan_Yon'); yoneticiYap(env, y.id);
  const k = await uyeGirisi(env, 'Kotu_Niyetli');
  const d = await uyeGirisi(env, 'Diger_Uye');
  yap(env, "UPDATE uyeler SET google_sub = 'g-123', tg_id = 777, eposta = 'kotu@example.com' WHERE id = ?", k.id);
  // kapatılanın içeriği
  const kb = baslikAc(env, k.id, 'puan', 'Kapatılanın sorusu');
  const dCevap = yanitEkle(env, kb, d.id, 'diğerinin cevabı', 1);
  const db = baslikAc(env, d.id, 'puan', 'Diğerinin sorusu');
  const kCevap = yanitEkle(env, db, k.id, 'kapatılanın cevabı');
  const dYanit = yanitEkle(env, db, d.id, 'alıntılı', 0, kCevap);
  const dOy = yanitEkle(env, db, d.id, 'oylanan cevap', 1);
  yap(env, 'UPDATE uyeler SET itibar = 2 WHERE id = ?', d.id);
  yap(env, 'INSERT INTO oylar (yanit_id, uye_id) VALUES (?, ?)', dOy, k.id);
  yap(env, 'INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma) VALUES (?, ?, ?, ?)', k.id, d.id, 'dm', t0());
  yap(env, 'INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma) VALUES (?, ?, ?, ?)', d.id, k.id, 'dm2', t0());
  yap(env, 'INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)', k.id, db, t0());
  yap(env, 'INSERT INTO engeller (uye_id, engellenen, olusma) VALUES (?, ?, ?)', d.id, k.id, t0());
  yap(env, "INSERT INTO basvurular (ilan_id, kimlik, olusma) VALUES ('csb-12345', ?, ?)", `u${k.id}`, t0());
  yap(env, "INSERT INTO uye_katip (uye_id, veri) VALUES (?, '{}')", k.id);
  assert.equal(satir(env, 'SELECT yanit_sayisi FROM basliklar WHERE id = ?', db).yanit_sayisi, 3);

  assert.equal((await cagir(env, 'POST', '/arac/uye/Kotu_Niyetli/kapat', { token: d.token })).durum, 403);
  assert.equal((await cagir(env, 'POST', '/arac/uye/Kapatan_Yon/kapat', { token: y.token })).durum, 400);   // kendini değil
  assert.equal((await cagir(env, 'POST', '/arac/uye/Asistan/kapat', { token: y.token })).durum, 400);
  const y2 = await uyeGirisi(env, 'Ikinci_Yon'); yoneticiYap(env, y2.id);
  assert.equal((await cagir(env, 'POST', '/arac/uye/Ikinci_Yon/kapat', { token: y.token })).durum, 400);   // başka yönetici kapatılamaz
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM uyeler WHERE id = ?', y2.id), 1);
  const r = await cagir(env, 'POST', '/arac/uye/kotu_niyetli/kapat', { token: y.token });
  assert.equal(r.durum, 200);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM uyeler WHERE id = ?', k.id), 0);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM basliklar WHERE uye_id = ? OR id = ?', k.id, kb), 0);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM yanitlar WHERE uye_id = ? OR baslik_id = ? OR id = ?', k.id, kb, dCevap), 0);
  for (const sql of ['SELECT COUNT(*) AS n FROM ozel_mesajlar WHERE gonderen = ? OR alici = ?', 'SELECT COUNT(*) AS n FROM engeller WHERE uye_id = ? OR engellenen = ?']) assert.equal(sayi(env, sql, k.id, k.id), 0);
  for (const tablo of ['takipler', 'oylar', 'uye_katip']) assert.equal(sayi(env, `SELECT COUNT(*) AS n FROM ${tablo} WHERE uye_id = ?`, k.id), 0, tablo);
  assert.equal(sayi(env, 'SELECT COUNT(*) AS n FROM basvurular WHERE kimlik = ?', `u${k.id}`), 0);
  assert.equal(satir(env, 'SELECT yanit_sayisi FROM basliklar WHERE id = ?', db).yanit_sayisi, 2);
  assert.equal(satir(env, 'SELECT ust_id FROM yanitlar WHERE id = ?', dYanit).ust_id, null);
  assert.equal(satir(env, 'SELECT faydali FROM yanitlar WHERE id = ?', dOy).faydali, 0);
  assert.equal(satir(env, 'SELECT itibar FROM uyeler WHERE id = ?', d.id).itibar, 0);   // 1 (kapatılanın oyu) + 1 (silinen sorudaki cevabı) düştü
  assert.equal((await cagir(env, 'GET', '/uye/Kotu_Niyetli')).durum, 404);
  assert.equal((await cagir(env, 'GET', '/ben', { token: k.token })).durum, 401);
  // kimliğin kendisi değil yalnız özeti saklanır
  const ozetler = env.DB.ham.prepare('SELECT ozet FROM kapali_kimlikler').all().map((x) => x.ozet);
  assert.equal(ozetler.length, 3);
  assert.ok(ozetler.every((o) => /^[0-9a-f]{64}$/.test(o) && !o.includes('g-123')));
  // yeniden üyelik engeli
  for (const kimlik of [{ google_sub: 'g-123' }, { tg_id: 777 }, { eposta: 'kotu@example.com' }, { eposta: 'KOTU@example.com' }]) {
    const s = await uyeOlustur(env, kimlik, 'Yeni_Rumuz_1');
    assert.equal(s.hata && s.hata.status, 403, JSON.stringify(kimlik));
  }
  assert.ok((await uyeOlustur(env, { google_sub: 'g-baska' }, 'Yeni_Rumuz_2')).uye);
  // eski rumuz başkasına verilmez
  assert.equal((await uyeOlustur(env, { google_sub: 'g-ucuncu' }, 'Kotu_Niyetli')).hata.status, 409);
});

test('avatar: yalnız piksel; eski çizim ve biçimler piksele çevrilir; yeni üyeye rastgele piksel; muhtar yalnız yöneticiye', async () => {
  assert.equal(pxNormalle('kedi:lila'), 'px.loaf:pixel.270');
  assert.equal(pxNormalle('robot:bilinmeyen'), 'px.robo:pixel.0');
  assert.equal(pxNormalle('px.wizard:voxel.270'), 'px.wizard:pixel.270');
  assert.equal(pxNormalle('yok-boyle:lila'), null);
  assert.equal(pxNormalle('px.muhtar:dots.0'), null);
  for (const v of Object.values(ESKI_SVG_PX)) assert.ok(PX_ADLAR.has(v), v);
  for (let i = 0; i < 50; i++) assert.match(rastgelePx(), /^px\.[a-z]+:pixel\.(0|45|90|135|180|225|270|315)$/);
  const env = ortam();
  const u = await uyeGirisi(env, 'Normal_Uye');
  const y = await uyeGirisi(env, 'Muhtar_Bey'); yoneticiYap(env, y.id);
  assert.match((await cagir(env, 'GET', '/ben', { token: u.token })).json.uye.av, /^px\.[a-z]+:pixel\.\d+$/);
  assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: MUHTAR_AVATAR } })).durum, 400);
  ipSinirSifirla();
  const r = await cagir(env, 'POST', '/ben/kart', { token: y.token, govde: { avatar: MUHTAR_AVATAR } });
  assert.equal(r.durum, 200); assert.equal(r.json.kart.avatar, MUHTAR_AVATAR);
  assert.equal((await cagir(env, 'GET', '/uye/Muhtar_Bey')).json.av, MUHTAR_AVATAR);
});

test('sohbet odası hız sınırı: akış durmaz (15 sn\'de 10, 2 sn\'de 3); cevaplar 20 sn kuralını korur ve sohbet sayısından etkilenmez', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Hizli_Yazan'); kayitEskit(env, u.id);
  const oda = baslikAc(env, 1, 'oda', 'Hız deneme odası');
  const soru = baslikAc(env, 1, 'puan', 'Hız deneme sorusu');
  const yaz = (b, i) => cagir(env, 'POST', `/baslik/${b}/yanit`, { token: u.token, govde: { govde: `mesaj ${i}` } });
  // aynı anda 3 mesaj geçer, 4. aynı 2 sn içinde bekletilir
  for (let i = 0; i < ODA_SINIRI.kisa_en_cok; i++) assert.equal((await yaz(oda, i)).durum, 201, `oda ${i}`);
  assert.equal((await yaz(oda, 99)).durum, 429);
  // birkaç saniye önceye çekilen mesajlarla 15 sn'de 10'a kadar akış
  yap(env, 'UPDATE yanitlar SET olusma = olusma - 3 WHERE uye_id = ?', u.id);
  for (let i = 3; i < 6; i++) assert.equal((await yaz(oda, i)).durum, 201, `oda ${i}`);
  yap(env, 'UPDATE yanitlar SET olusma = olusma - 3 WHERE uye_id = ?', u.id);
  for (let i = 6; i < 9; i++) assert.equal((await yaz(oda, i)).durum, 201, `oda ${i}`);
  yap(env, 'UPDATE yanitlar SET olusma = olusma - 3 WHERE uye_id = ?', u.id);
  assert.equal((await yaz(oda, 9)).durum, 201);
  assert.equal((await yaz(oda, 10)).durum, 429);   // 15 sn'de 11. mesaj
  // sohbet mesajları cevap sınırını tüketmez: hemen ardından soruya cevap yazılır, ama iki cevap arası 20 sn
  assert.equal((await yaz(soru, 'c1')).durum, 201);
  assert.equal((await yaz(soru, 'c2')).durum, 429);
});

test('göç 0006: eski çizim / biçim avatarları piksele, avatarsızlara kimlikten piksel; tekrar çalıştırılabilir', () => {
  const db = sahteD1();
  const h = db.ham;
  h.exec("INSERT INTO uyeler (id, rumuz, rumuz_kat, avatar) VALUES (10, 'a', 'a', 'kedi:lila'), (11, 'b', 'b', 'px.wizard:voxel.270'), (12, 'c', 'c', NULL), (13, 'd', 'd', 'foto'), (14, 'e', 'e', 'robot:yok'), (15, 'f', 'f', 'px.loaf:pixel.45')");
  h.exec("INSERT INTO uyeler (id, rumuz, rumuz_kat, avatar, silindi) VALUES (16, 'g', 'g', NULL, 1)");
  const goc = readFileSync(new URL('../migrations/0006_yonetim_piksel.sql', import.meta.url), 'utf8');
  h.exec(goc); h.exec(goc);
  const av = (id) => h.prepare('SELECT avatar FROM uyeler WHERE id = ?').get(id).avatar;
  assert.equal(av(10), 'px.loaf:pixel.270');
  assert.equal(av(11), 'px.wizard:pixel.270');
  assert.equal(av(12), pxNormalle(av(12)));   // geçerli piksel değer
  assert.match(av(12), /^px\.[a-z]+:pixel\.\d+$/);
  assert.equal(av(13), 'foto');
  assert.equal(av(14), 'px.robo:pixel.0');
  assert.equal(av(15), 'px.loaf:pixel.45');
  assert.equal(av(16), null);   // silinmiş hesap
  assert.equal(av(1), null);    // sistem hesabı
  assert.equal(h.prepare("SELECT COUNT(*) AS n FROM sqlite_master WHERE name LIKE 'gecici_%'").get().n, 0);
  // migration ile tanımlı her piksel adı izin listesinde
  for (const m of goc.matchAll(/\(\d+,'([a-z]+)'\)/g)) assert.ok(PX_ADLAR.has(m[1]), m[1]);
  // göçteki eski çizim -> piksel ve renk -> ton tabloları src/kart.js ile birebir aynı
  const svg = goc.match(/INSERT OR IGNORE INTO gecici_svg[^;]*;/)[0], ton = goc.match(/INSERT OR IGNORE INTO gecici_ton[^;]*;/)[0];
  assert.deepEqual(Object.fromEntries([...svg.matchAll(/\('([a-z]+)','([a-z]+)'\)/g)].map((m) => [m[1], m[2]])), { ...ESKI_SVG_PX });
  assert.deepEqual(Object.fromEntries([...ton.matchAll(/\('([a-z]+)',(\d+)\)/g)].map((m) => [m[1], Number(m[2])])), { ...ESKI_RENK_TON });
});
