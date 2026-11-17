import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir } from './yardim.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const t = () => Math.floor(Date.now() / 1000);

function doldur(env) {
  const db = env.DB.ham;
  const n = t();
  const uye = db.prepare(`INSERT INTO uyeler (tg_id, rumuz, kayit, kurucu, rol, engelli, sifre_ozet, google_sub, eposta, itibar, silindi)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
  const a = Number(uye.run(777001, 'Ayse', n - 3600, 1, 'uye', 0, null, null, null, 5, null).lastInsertRowid);                 // telegram, kurucu
  const b = Number(uye.run(null, 'Berk', n - 3 * 86400, 0, 'yonetici', 0, 'pbkdf2$gizli', null, null, 1, null).lastInsertRowid); // şifre, yönetici
  const c = Number(uye.run(null, 'Ceren', n - 20 * 86400, 0, 'uye', 0, null, 'google-sub-xyz', 'ceren@ornek.com', 0, null).lastInsertRowid); // google
  const d = Number(uye.run(null, 'Deniz', n - 2 * 86400, 0, 'uye', 0, null, null, 'deniz@ornek.com', 0, null).lastInsertRowid); // e-posta, yalnız oy verir
  const e = Number(uye.run(null, 'Ece', n - 40 * 86400, 0, 'uye', 0, null, null, 'ece@ornek.com', 0, null).lastInsertRowid);   // hiç iz yok (yalnız okur)
  uye.run(null, 'Silik', n - 5 * 86400, 0, 'uye', 0, null, null, null, 0, n - 100);                                            // silinmiş
  db.prepare('INSERT INTO gizli_yoneticiler (uye_id) VALUES (?)').run(c);
  const bas = db.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, olusma, son_hareket, yanit_sayisi, faydali, anket) VALUES (?, ?, 'g', ?, 'uye', ?, ?, ?, ?, ?)");
  const s1 = Number(bas.run('puan', 'Soru bir', a, n - 2 * 86400, n - 3600, 2, 1, 0).lastInsertRowid);
  const s2 = Number(bas.run('kurum', 'Soru iki', b, n - 5 * 86400, n - 5 * 86400, 0, 0, 0).lastInsertRowid);   // cevapsız, 5 gün
  const s3 = Number(bas.run('puan', 'Anket soru', a, n - 50 * 86400, n - 50 * 86400, 0, 0, 1).lastInsertRowid); // 30 gün dışı, cevapsız
  bas.run('puan', 'Gizli soru', b, n - 7200, n - 7200, 0, 0, 0);
  db.prepare('UPDATE basliklar SET gizli = 1 WHERE baslik = ?').run('Gizli soru');
  const oda = Number(bas.run('oda', 'Lisans odasi', 1, n - 90 * 86400, n, 0, 0, 0).lastInsertRowid);
  const ilan = Number(db.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, ilan_id, kaynak, olusma, son_hareket) VALUES ('ilan', 'Ilan', '', 1, 'x1', 'sistem', ?, ?)").run(n - 86400, n).lastInsertRowid);
  const yan = db.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, ust_id) VALUES (?, ?, ?, ?, ?)');
  yan.run(s1, b, 'cevap 1', n - 2 * 86400 + 1200, null);   // ilk cevap 20 dk
  yan.run(s1, c, 'cevap 2', n - 3600, null);
  yan.run(oda, a, 'merhaba', n - 600, null);
  yan.run(oda, b, 'selam', n - 400, null);
  yan.run(oda, a, 'nasilsiniz', n - 4 * 86400, null);
  yan.run(oda, 1, 'sistem mesaji', n - 300, null);         // sayılmaz
  const iq = Number(yan.run(ilan, c, 'ilan sorusu', n - 3600, null).lastInsertRowid);   // Ceren'in iki yazısı aynı an: tek gün
  yan.run(ilan, 2, 'asistan cevabi', n - 3595, iq);   // asistan cevabı (sayılmaz ama ilan sorusu asistan aldı)
  const oz = db.prepare('INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma) VALUES (?, ?, ?, ?)');
  oz.run(a, b, 'GIZLI-DM-METNI', n - 100); oz.run(2, a, 'asistan', n - 90);
  db.prepare('INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)').run(a, s1, n - 50);
  db.prepare('INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)').run(d, s1, n - 40);
  db.prepare('INSERT INTO oylar (yanit_id, uye_id) VALUES (1, ?)').run(d);
  db.prepare('INSERT INTO baslik_oylar (baslik_id, uye_id) VALUES (?, ?)').run(s1, d);
  db.prepare('INSERT INTO anket_secenekleri (baslik_id, sira, metin, oy) VALUES (?, 0, ?, 1)').run(s3, 'evet');
  db.prepare('INSERT INTO anket_oylari (baslik_id, uye_id, sira) VALUES (?, ?, 0)').run(s3, d);
  db.prepare('INSERT INTO sikayetler (yanit_id, uye_id) VALUES (1, ?)').run(a);
  db.prepare('INSERT INTO ozel_sikayetler (sikayet_eden, sikayet_edilen, mesaj_id, olusma) VALUES (?, ?, 1, ?)').run(b, a, n);
  db.prepare('UPDATE uyeler SET foto_surum = 9 WHERE id = ?').run(c);
  db.prepare('INSERT INTO foto_bildirimleri (uye_id, bildiren, surum, olusma) VALUES (?, ?, 9, ?)').run(c, a, n);
  db.prepare('INSERT INTO kapali_kimlikler (ozet, olusma) VALUES (?, ?)').run('ozet-hash-abc', n);
  return { a, b, c, d, e, s1, s2, s3, oda };
}

test('/yonetim/analiz: anahtarsız ve yanlış anahtarla 401, YONETICI_ANAHTARI yoksa 401', async () => {
  const env = ortam();
  assert.equal((await cagir(env, 'GET', '/yonetim/analiz')).durum, 401);
  assert.equal((await cagir(env, 'GET', '/yonetim/analiz', { basliklar: { 'X-Yonetici': 'yanlis' } })).durum, 401);
  assert.equal((await cagir(ortam({ YONETICI_ANAHTARI: '' }), 'GET', '/yonetim/analiz', { basliklar: { 'X-Yonetici': '' } })).durum, 401);
});

test('/yonetim/analiz: boş veritabanı, dönem seçimi 7/30/90, geçersiz gün 30 olur', async () => {
  const env = ortam();
  for (const [q, beklenen] of [['7', 7], ['30', 30], ['90', 90], ['365', 30], ['abc', 30]]) {
    const r = await cagir(env, 'GET', '/yonetim/analiz?gun=' + q, { basliklar: YONETICI });
    assert.equal(r.durum, 200);
    assert.equal(r.basliklar.get('cache-control'), 'no-store');
    assert.equal(r.json.gun, beklenen);
    assert.equal(r.json.seri.length, beklenen);
  }
  const r = await cagir(env, 'GET', '/yonetim/analiz', { basliklar: YONETICI });
  assert.equal(r.json.uyeler.toplam, 0);
  assert.equal(r.json.soru.ilk_cevap_medyan_dk, null);
  assert.equal(r.json.saat.length, 24);
  assert.deepEqual(r.json.katkilar, []);
});

test('/yonetim/analiz: toplamlar doğru, sistem/asistan sayılmaz', async () => {
  const env = ortam();
  const { s1, s2, s3 } = doldur(env);
  const r = await cagir(env, 'GET', '/yonetim/analiz?gun=30', { basliklar: YONETICI });
  assert.equal(r.durum, 200);
  const j = r.json;
  assert.equal(j.uyeler.toplam, 5);
  assert.equal(j.uyeler.silinen, 1);
  assert.equal(j.uyeler.yeni, 5);                     // 30 gün içinde: Ayse, Berk, Ceren, Deniz, Silik
  assert.deepEqual(j.uyeler.yontem, { google: 1, eposta: 2, telegram: 1, sifre: 1 });
  assert.equal(j.uyeler.kurucu, 1);
  assert.equal(j.uyeler.fotolu, 1);
  assert.equal(j.toplam.uye, 5);
  assert.equal(j.toplam.soru, 2);                     // gizli ve 30 gün dışı hariç
  assert.equal(j.toplam.cevap, 2);                    // asistan hariç
  assert.equal(j.toplam.ilan_soru, 1);
  assert.equal(j.toplam.sohbet, 3);                   // sistem hariç
  assert.equal(j.toplam.ozel, 1);                     // asistan hariç
  assert.equal(j.toplam.takip, 2);
  assert.deepEqual(j.aktif, { g1: 3, g7: 3, g30: 3, donem: 3, geri_donen: 2 }); // Ayse ve Berk farklı günlerde yazdı; Ceren tek gün
  assert.deepEqual(j.huni, { toplam: 5, yazan: 3, yalniz_etkilesim: 1, iz_yok: 1, yeni: 4, yeni_yazan: 3 });
  assert.equal(j.soru.donem, 2);
  assert.equal(j.soru.cevaplanan, 1);
  assert.equal(j.soru.ilk_cevap_medyan_dk, 20);
  assert.equal(j.soru.bir_saatte, 1);
  assert.equal(j.soru.cevapsiz, 2);
  assert.deepEqual(j.soru.cevapsiz_liste.map((x) => [x.id, x.gun]), [[s3, 50], [s2, 5]]);
  assert.equal(j.soru.cevapsiz_liste[1].kategori, 'Kurum ve şehir');
  assert.deepEqual(j.soru.en_iyi, [{ id: s1, baslik: 'Soru bir', kategori: 'Puan ve tercih', cevap: 2, faydali: 1, takip: 2 }]);
  assert.deepEqual(j.soru.ilan, { n: 1, insan: 0, asistan: 1 });
  assert.deepEqual(j.soru.kategori.map((k) => [k.kod, k.n, k.cevaplanan]).sort(), [['kurum', 1, 0], ['puan', 1, 1]]);
  const oda = j.odalar.find((o) => o.ad === 'Lisans odasi');
  assert.equal(oda.mesaj, 3);
  assert.equal(oda.kisi, 2);
  assert.equal(j.saat.reduce((x, y) => x + y, 0), 3 + 2 + 3 + 1 + 1); // 3 soru (gizlenen de yazıldı) + 2 cevap + 3 sohbet + ilan sorusu + özel mesaj
  assert.equal(j.isi.reduce((x, r) => x + r[2], 0), 10);
  assert.ok(j.isi.every((r) => r[0] >= 0 && r[0] <= 6 && r[1] >= 0 && r[1] <= 23));
  assert.deepEqual(j.katkilar.map((k) => k.rumuz), ['Berk', 'Ceren', 'Ayse']);
  assert.deepEqual(j.katkilar[2], { rumuz: 'Ayse', soru: 1, cevap: 0, sohbet: 2, itibar: 5, kurucu: true });
  assert.deepEqual(j.etkilesim, { yanit_oy: 1, baslik_oy: 1, anket: 1, anket_oy: 1, takip: 2 });
  assert.deepEqual(j.denetim, { sikayet: 1, ozel_sikayet: 1, foto_bildirim: 1, kapali_kimlik: 1, engelli: 0, engel: 0, gizlenen: 1 });
});

test('/yonetim/analiz: gizli alan sızmaz (e-posta, kimlik, DM metni, yönetici bilgisi)', async () => {
  const env = ortam();
  doldur(env);
  for (const gun of [7, 30, 90]) {
    const r = await cagir(env, 'GET', '/yonetim/analiz?gun=' + gun, { basliklar: YONETICI });
    const metin = JSON.stringify(r.json);
    for (const yasak of ['@ornek.com', 'google-sub-xyz', '777001', 'pbkdf2', 'GIZLI-DM-METNI', 'ozet-hash-abc', 'yonetici', 'rol', 'gizli_yonetici', 'Gizli soru', 'tg_id', 'uye_id', 'Silik']) {
      assert.ok(!metin.includes(yasak), `${yasak} sızdı (gun=${gun})`);
    }
    for (const k of r.json.katkilar) assert.deepEqual(Object.keys(k).sort(), ['cevap', 'itibar', 'kurucu', 'rumuz', 'sohbet', 'soru']);
  }
});

test('/yonetim/analiz: az sorgu, yazma yok', async () => {
  const env = ortam();
  doldur(env);
  const once = env.DB.sayac.sorgu;
  const sayimOnce = env.DB.ham.prepare('SELECT (SELECT COUNT(*) FROM yanitlar) + (SELECT COUNT(*) FROM basliklar) + (SELECT COUNT(*) FROM uyeler) AS n').get().n;
  await cagir(env, 'GET', '/yonetim/analiz?gun=90', { basliklar: YONETICI });
  assert.ok(env.DB.sayac.sorgu - once <= 20);
  assert.equal(env.DB.sayac.batch, 0);
  const sayimSonra = env.DB.ham.prepare('SELECT (SELECT COUNT(*) FROM yanitlar) + (SELECT COUNT(*) FROM basliklar) + (SELECT COUNT(*) FROM uyeler) AS n').get().n;
  assert.equal(sayimSonra, sayimOnce);
});
