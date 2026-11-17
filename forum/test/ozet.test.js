import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir } from './yardim.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const t = () => Math.floor(Date.now() / 1000);

function doldur(env) {
  const db = env.DB.ham;
  const n = t();
  const uye = db.prepare('INSERT INTO uyeler (tg_id, rumuz, kayit, kurucu, rol, dm_acik, engelli, sifre_ozet, google_sub) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)');
  const a = Number(uye.run(100, 'Ayse', n - 3600, 1, 'uye', 1, 0, null, null).lastInsertRowid);        // telegram, kurucu, 1 saat once
  const b = Number(uye.run(null, 'Berk', n - 3 * 86400, 0, 'uye', 0, 0, 'pbkdf2$x', null).lastInsertRowid); // sifre, dm kapali
  const c = Number(uye.run(null, 'Ceren', n - 20 * 86400, 0, 'uye', 1, 1, null, 'sub-1').lastInsertRowid);  // google, engelli
  const bas = db.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, olusma, son_hareket, yanit_sayisi) VALUES (?, ?, 'g', ?, 'uye', ?, ?, ?)");
  const s1 = Number(bas.run('puan', 'Soru bir <b>', a, n - 7200, n - 3600, 2).lastInsertRowid);
  const s2 = Number(bas.run('kurum', 'Soru iki', b, n - 7200, n - 7200, 0).lastInsertRowid);        // cevapsiz
  bas.run('puan', 'Gizli soru', b, n - 7200, n - 7200, 0);
  db.prepare('UPDATE basliklar SET gizli = 1 WHERE baslik = ?').run('Gizli soru');
  const oda = Number(db.prepare("SELECT id FROM basliklar WHERE kategori = 'oda' LIMIT 1").get()?.id
    || bas.run('oda', 'Lisans odasi', 1, n, n, 0).lastInsertRowid);
  const yan = db.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma) VALUES (?, ?, ?, ?)');
  yan.run(s1, b, 'cevap 1', n - 7200 + 600);     // ilk cevap 10 dk
  yan.run(s1, c, 'cevap 2', n - 3600);
  yan.run(s1, 2, 'asistan cevabi', n - 7000);    // asistan: sayilmaz
  yan.run(oda, a, 'merhaba', n - 600);           // sohbet
  yan.run(oda, b, 'selam', n - 400);
  yan.run(oda, 1, 'sistem mesaji', n - 300);     // sistem: sayilmaz
  const oz = db.prepare('INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma) VALUES (?, ?, ?, ?)');
  oz.run(a, b, 'hey', n - 100); oz.run(2, a, 'asistan', n - 90);
  db.prepare('INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)').run(a, s2, n);
  db.prepare('INSERT INTO sikayetler (yanit_id, uye_id) VALUES (1, ?)').run(a);
  db.prepare('INSERT INTO ozel_sikayetler (sikayet_eden, sikayet_edilen, mesaj_id, olusma) VALUES (?, ?, 1, ?)').run(b, a, n);
  db.prepare('INSERT INTO engeller (uye_id, engellenen, olusma) VALUES (?, ?, ?)').run(a, c, n - 10);
  return { s1, oda };
}

test('/yonetim/ozet: anahtarsiz 401, yanlis anahtar 401', async () => {
  const env = ortam();
  assert.equal((await cagir(env, 'GET', '/yonetim/ozet')).durum, 401);
  assert.equal((await cagir(env, 'GET', '/yonetim/ozet', { basliklar: { 'X-Yonetici': 'yanlis' } })).durum, 401);
});

test('/yonetim/ozet: bos veritabaninda sifirlar ve 30 gunluk seri', async () => {
  const env = ortam();
  const r = await cagir(env, 'GET', '/yonetim/ozet', { basliklar: YONETICI });
  assert.equal(r.durum, 200);
  assert.equal(r.basliklar.get('cache-control'), 'no-store');
  assert.equal(r.json.uyeler.toplam, 0);
  assert.equal(r.json.seri.length, 30);
  assert.equal(r.json.soru.ilk_cevap_dk, null);
  assert.equal(r.json.soru.cevapsiz, 0);
  assert.ok(r.json.sohbet.every((o) => o.mesaj === 0));
});

test('/yonetim/ozet: sayilar, sistem/asistan satirlari insan etkinligine girmez', async () => {
  const env = ortam();
  const { s1 } = doldur(env);
  const r = await cagir(env, 'GET', '/yonetim/ozet', { basliklar: YONETICI });
  assert.equal(r.durum, 200);
  const j = r.json;
  assert.deepEqual(j.uyeler, { toplam: 3, yeni: { g1: 1, g7: 2, g30: 3 }, yontem: { telegram: 1, google: 1, sifre: 1 }, kurucu: 1, engelli: 1, dm_kapali: 1 });
  assert.equal(j.seri.length, 30);
  const toplam = (k) => j.seri.reduce((x, g) => x + g[k], 0);
  assert.equal(toplam('uye'), 3);
  assert.equal(toplam('soru'), 2);      // gizli soru haric
  assert.equal(toplam('cevap'), 2);     // asistan yaniti haric
  assert.equal(toplam('sohbet'), 2);    // sistem mesaji haric
  assert.equal(toplam('ozel'), 1);      // asistan ozel mesaji haric
  assert.deepEqual(j.aktif, { g1: 3, g7: 3, g30: 3 });
  assert.equal(j.soru.toplam, 2);
  assert.equal(j.soru.cevapsiz, 1);
  assert.equal(j.soru.ilk_cevap_n, 1);
  assert.equal(j.soru.ilk_cevap_dk, 10);
  assert.deepEqual(j.soru.kategori.map((k) => [k.kod, k.n]).sort(), [['kurum', 1], ['puan', 1]]);
  assert.equal(j.soru.kategori.find((k) => k.kod === 'puan').ad, 'Puan ve tercih');
  assert.deepEqual(j.soru.populer, [{ id: s1, baslik: 'Soru bir <b>', cevap: 2 }]);
  const oda = j.sohbet.find((o) => o.mesaj > 0);
  assert.equal(oda.mesaj, 2);
  assert.equal(j.takip, 1);
  assert.deepEqual(j.sikayet, { genel: 1, ozel: 1 });
  assert.equal(j.engel_24s, 1);
});

test('/yonetim/ozet: hizli ve az sorgu', async () => {
  const env = ortam();
  doldur(env);
  const once = env.DB.sayac.sorgu;
  await cagir(env, 'GET', '/yonetim/ozet', { basliklar: YONETICI });
  assert.ok(env.DB.sayac.sorgu - once <= 20);
});
