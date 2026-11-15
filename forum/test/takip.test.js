import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir, uyeGirisi, zamaniGeriAl, kayitEskit, sahteFetch, SITE, UUID } from './yardim.js';
import { bildirimSifirla } from '../src/bildirim.js';

const BASLIK = { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' };

async function uye(env, rumuz, rol) {
  const u = await uyeGirisi(env, rumuz, rol);
  kayitEskit(env, u.id);
  return { ...u, rumuz };
}
const tg = (env, u, n, bildirim = 1) => env.DB.ham.prepare('UPDATE uyeler SET tg_id = ?, bildirim = ? WHERE id = ?').run(n, bildirim, u.id);
const satir = (env, sql, ...p) => env.DB.ham.prepare(sql).get(...p);
const takipte = (env, u, b) => !!satir(env, 'SELECT 1 AS v FROM takipler WHERE uye_id = ? AND baslik_id = ?', u.id, b);
async function baslikAc(env, u, ek = {}) {
  zamaniGeriAl(env, u.id);
  return cagir(env, 'POST', '/baslik', { token: u.token, govde: { ...BASLIK, ...ek } });
}
async function yanitla(env, u, baslikId, govde = 'Bence şöyle olabilir.', ek = {}) {
  zamaniGeriAl(env, u.id);
  return cagir(env, 'POST', `/baslik/${baslikId}/yanit`, { token: u.token, govde: { govde, ...ek } });
}
function oda(env, ad = 'Lisans odası') {
  const t = Math.floor(Date.now() / 1000);
  return Number(env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket) VALUES ('oda', ?, 'oda açıklaması', 1, 'sistem', 1, ?, ?)").run(ad, t, t).lastInsertRowid);
}
const tgCagrilari = (f) => f.cagrilar.filter((c) => c.url.startsWith('https://api.telegram.org/')).map((c) => JSON.parse(c.secenek.body));

test('takip: aç/kapat, doğrulama, 404, GET /baslik/:id ve /ilan/:id içinde takip bayrağı', async () => {
  const env = ortam();
  const a = await uye(env, 'Tk_A'), b = await uye(env, 'Tk_B');
  const t = (await baslikAc(env, a)).json.baslik.id;
  assert.equal((await cagir(env, 'POST', `/baslik/${t}/takip`, { govde: { takip: true } })).durum, 401);
  assert.equal((await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: {} })).durum, 400);
  assert.equal((await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: { takip: 'evet' } })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/baslik/99999/takip', { token: b.token, govde: { takip: true } })).durum, 404);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`, { token: b.token })).json.baslik.takip, false);
  assert.deepEqual((await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: { takip: true } })).json, { takip: true });
  assert.deepEqual((await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: { takip: true } })).json, { takip: true });   // tekrar zararsız
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM takipler WHERE uye_id = ? AND baslik_id = ?', b.id, t).n, 1);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`, { token: b.token })).json.baslik.takip, true);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`)).json.baslik.takip, undefined);   // anonimde yok (önbellek)
  assert.deepEqual((await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: { takip: false } })).json, { takip: false });
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`, { token: b.token })).json.baslik.takip, false);
  // gizli başlık
  env.DB.ham.prepare('UPDATE basliklar SET gizli = 1 WHERE id = ?').run(t);
  assert.equal((await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: { takip: true } })).durum, 404);
  // ilan başlığı
  const ilan = `csb-${12345}`;
  const r = await cagir(env, 'POST', `/ilan/${ilan}/yanit`, { token: b.token, govde: { govde: 'Bu ilan için soru var.', ilan_baslik: 'Deneme kurumu 2026 sözleşmeli personel alımı' } });
  assert.equal(r.durum, 201);
  assert.equal((await cagir(env, 'GET', `/ilan/${ilan}`, { token: b.token })).json.baslik.takip, true);   // soruyu soran otomatik takip
  assert.equal((await cagir(env, 'GET', `/ilan/${ilan}`, { token: a.token })).json.baslik.takip, false);
  assert.equal((await cagir(env, 'GET', `/ilan/${ilan}`)).json.baslik.takip, undefined);
  assert.equal((await cagir(env, 'GET', `/ilan/${ilan.replace('12345', '99999')}`, { token: a.token })).json.baslik, null);
});

test('otomatik takip: başlık açan ve yanıt yazan takip eder; oda, asistan ve yönetim başlığı etmez', async () => {
  const env = ortam();
  const a = await uye(env, 'Oto_A'), b = await uye(env, 'Oto_B'), y = await uye(env, 'Oto_Y', 'yonetici');
  const t = (await baslikAc(env, a)).json.baslik.id;
  assert.equal(takipte(env, a, t), true);          // başlık açan
  assert.equal(takipte(env, b, t), false);
  assert.equal((await yanitla(env, b, t)).durum, 201);
  assert.equal(takipte(env, b, t), true);          // yanıt yazan
  // bir daha yazmak tekrar satır eklemez
  await yanitla(env, b, t, 'bir yanıt daha var burada');
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM takipler WHERE baslik_id = ?', t).n, 2);
  // takibi bırakıp yeniden yazınca yeniden takip (bilinçli: yazmak ilgi göstergesi)
  await cagir(env, 'POST', `/baslik/${t}/takip`, { token: b.token, govde: { takip: false } });
  assert.equal(takipte(env, b, t), false);
  // oda: açan da, yazan da takip etmez
  const o = (await baslikAc(env, y, { kategori: 'oda', baslik: 'Deneme sohbet odası', govde: 'Burada sohbet edebilirsiniz herkes.' }));
  assert.equal(o.durum, 201);
  assert.equal(takipte(env, y, o.json.baslik.id), false);
  const odaId = oda(env);
  assert.equal((await yanitla(env, a, odaId, 'odada merhaba arkadaşlar')).durum, 201);
  assert.equal(takipte(env, a, odaId), false);
  // oda isteğe bağlı takip edilebilir
  assert.deepEqual((await cagir(env, 'POST', `/baslik/${odaId}/takip`, { token: a.token, govde: { takip: true } })).json, { takip: true });
  assert.equal(takipte(env, a, odaId), true);
  // ilan sorusu: soran takip eder, asistan (id 2) etmez
  zamaniGeriAl(env, a.id);
  const r = await cagir(env, 'POST', '/ilan/csb-12345/yanit', { token: a.token, govde: { govde: 'Başvuru şartları neler acaba?', ilan_baslik: 'Deneme kurumu 2026 sözleşmeli personel alımı' } });
  assert.equal(r.durum, 201);
  assert.equal(takipte(env, a, r.json.baslik_id), true);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM takipler WHERE uye_id IN (1, 2)').n, 0);
  // yönetim başlığı (uye 1) kimseyi takipçi yapmaz
  const yb = await cagir(env, 'POST', '/yonetim/baslik', { basliklar: { 'X-Yonetici': 'yonetici-anahtar' }, govde: { kategori: 'puan', baslik: 'Sistem başlığı örnek', govde: 'Sistem başlığının içeriği.' } });
  assert.equal(yb.durum, 201);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM takipler WHERE baslik_id = ?', yb.json.baslik.id).n, 0);
});

test('/ben/takipler: BASLIK şekli, son hareket sırası, gizli hariç, giriş şart', async () => {
  const env = ortam();
  const a = await uye(env, 'Lt_A'), b = await uye(env, 'Lt_B');
  assert.equal((await cagir(env, 'GET', '/ben/takipler')).durum, 401);
  assert.deepEqual((await cagir(env, 'GET', '/ben/takipler', { token: a.token })).json, { basliklar: [] });
  const t1 = (await baslikAc(env, b, { baslik: 'Birinci başlık metni burada' })).json.baslik.id;
  const t2 = (await baslikAc(env, b, { baslik: 'İkinci başlık metni burada' })).json.baslik.id;
  const t3 = (await baslikAc(env, b, { baslik: 'Üçüncü başlık metni burada' })).json.baslik.id;
  for (const t of [t1, t2, t3]) await cagir(env, 'POST', `/baslik/${t}/takip`, { token: a.token, govde: { takip: true } });
  env.DB.ham.prepare('UPDATE basliklar SET son_hareket = ? WHERE id = ?').run(5000, t1);
  env.DB.ham.prepare('UPDATE basliklar SET son_hareket = ? WHERE id = ?').run(9000, t2);
  env.DB.ham.prepare('UPDATE basliklar SET son_hareket = ?, gizli = 1 WHERE id = ?').run(99999, t3);
  const r = await cagir(env, 'GET', '/ben/takipler', { token: a.token });
  assert.equal(r.basliklar.get('Cache-Control'), 'no-store');
  assert.deepEqual(r.json.basliklar.map((x) => x.id), [t2, t1]);
  const liste = (await cagir(env, 'GET', '/basliklar')).json.basliklar.find((x) => x.id === t2);
  assert.deepEqual(r.json.basliklar[0], { ...liste, son_hareket: 9000 });   // aynı BASLIK şekli (kısa özetli)
  assert.equal(r.json.basliklar[0].rumuz, 'Lt_B');
  // en çok 100
  for (let i = 0; i < 110; i++) {
    const id = Number(env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('puan', ?, 'x', 1, 1, ?)").run(`kalabalik ${i}`, 100 + i).lastInsertRowid);
    env.DB.ham.prepare('INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, 1)').run(a.id, id);
  }
  assert.equal((await cagir(env, 'GET', '/ben/takipler', { token: a.token })).json.basliklar.length, 100);
});

test('takip bildirimi: takipçilere Telegram, yazan/başlık sahibi/yanıtlanan/anılan çift almaz, 10 dk sınırı, bildirim kapalı', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const sahip = await uye(env, 'Sahip_S'), yazan = await uye(env, 'Yazan_Y'), t1 = await uye(env, 'Takipci_1'), t2 = await uye(env, 'Takipci_2');
    const kapali = await uye(env, 'Kapali_K'), anilan = await uye(env, 'Anilan_M'), parent = await uye(env, 'Parent_P');
    [[sahip, 100], [yazan, 101], [t1, 201], [t2, 202], [anilan, 203], [parent, 204]].forEach(([u, n]) => tg(env, u, n));
    tg(env, kapali, 205, 0);
    const b = await baslikAc(env, sahip, { baslik: 'Takip edilen deneme başlığı için' });
    const t = b.json.baslik.id;
    for (const u of [t1, t2, kapali, anilan, parent, yazan]) await cagir(env, 'POST', `/baslik/${t}/takip`, { token: u.token, govde: { takip: true } });
    const pId = (await yanitla(env, parent, t, 'ilk yanıtı ben yazdım')).json.yanit.id;
    f.cagrilar.length = 0; bildirimSifirla();
    const r = await yanitla(env, yazan, t, 'iki mesaj @Anilan_M ve cevap', { ust_id: pId });
    assert.equal(r.durum, 201);
    const g = tgCagrilari(f);
    const alicilar = g.map((x) => x.chat_id).sort();
    // sahip (yanıt), parent (yanıt), anılan (anma), t1 + t2 (takip); yazan ve bildirimi kapalı yok; kimse iki kez almaz
    assert.deepEqual(alicilar, [100, 201, 202, 203, 204]);
    const takipMetni = g.find((x) => x.chat_id === 201).text;
    assert.equal(takipMetni, `Takip edilen deneme başlığı için: yeni mesaj\n${SITE}forum/?b=${t}`);
    assert.equal(g.find((x) => x.chat_id === 202).text, takipMetni);
    assert.match(g.find((x) => x.chat_id === 100).text, /başlığına yanıt yazdı/);
    assert.match(g.find((x) => x.chat_id === 203).text, /seni andı/);
    // aynı kişi + başlık için 10 dakika içinde ikinci bildirim yok
    f.cagrilar.length = 0;
    await yanitla(env, yazan, t, 'ikinci mesajım hemen ardından');
    assert.equal(tgCagrilari(f).length, 0);
  } finally { f.geri(); }
});

test('takip bildirimi: oda bağlantısı ?oda=, ilan başlığı, 50 takipçi sınırı, yerel/tokensiz atlanır', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const a = await uye(env, 'Od_A'), b = await uye(env, 'Od_B');
    tg(env, a, 301);
    const odaId = oda(env, 'Sohbet odası: lisans');
    await cagir(env, 'POST', `/baslik/${odaId}/takip`, { token: a.token, govde: { takip: true } });
    await yanitla(env, b, odaId, 'odada selam herkese');
    const g = tgCagrilari(f);
    assert.equal(g.length, 1);
    assert.equal(g[0].text, `Sohbet odası: lisans: yeni mesaj\n${SITE}forum/?oda=${odaId}`);
    assert.equal(takipte(env, b, odaId), false);   // oda otomatik takip değil
    // başlık adı 60 karaktere kısalır
    f.cagrilar.length = 0;
    const uzun = (await baslikAc(env, b, { baslik: 'Uzun başlık metni deneme amaçlı yazıldı ' + 'bu kısım altmış karakteri geçmek içindir' })).json.baslik.id;
    await cagir(env, 'POST', `/baslik/${uzun}/takip`, { token: a.token, govde: { takip: true } });
    await yanitla(env, b, uzun, 'uzun başlığa yanıt');
    assert.equal(tgCagrilari(f)[0].text.split(': yeni mesaj')[0].length, 60);
    // 50 sınırı
    f.cagrilar.length = 0;
    const kalabalik = (await baslikAc(env, b, { baslik: 'Kalabalık takipçili başlık örneği' })).json.baslik.id;
    env.DB.ham.exec(`INSERT INTO uyeler (id, tg_id, rumuz, kayit, rol, bildirim, engelli)
      WITH RECURSIVE s(n) AS (SELECT 0 UNION ALL SELECT n + 1 FROM s WHERE n < 69) SELECT 5000 + n, 9000 + n, 'Kal' || n, 1, 'uye', 1, 0 FROM s`);
    env.DB.ham.exec(`INSERT INTO takipler (uye_id, baslik_id, olusma) WITH RECURSIVE s(n) AS (SELECT 0 UNION ALL SELECT n + 1 FROM s WHERE n < 69) SELECT 5000 + n, ${kalabalik}, 1 FROM s`);
    bildirimSifirla();
    await yanitla(env, a, kalabalik, 'kalabalığa merhaba');
    const g2 = tgCagrilari(f);
    assert.equal(g2.length, 50);
    assert.equal(new Set(g2.map((x) => x.chat_id)).size, 50);
    // yerel ve tokensiz: gönderim yok
    f.cagrilar.length = 0;
    for (const ek of [{ ORTAM: 'yerel' }, { TELEGRAM_BOT_TOKEN: undefined }]) {
      const e = ortam(ek);
      const x = await uye(e, 'Yer_X'), y = await uye(e, 'Yer_Y');
      tg(e, x, 401);
      const bid = (await baslikAc(e, y)).json.baslik.id;
      await cagir(e, 'POST', `/baslik/${bid}/takip`, { token: x.token, govde: { takip: true } });
      await yanitla(e, y, bid, 'selam takipçi');
    }
    assert.equal(tgCagrilari(f).length, 0);
  } finally { f.geri(); }
});

test('takip bildirimi: ilan sorusuna gelen yanıt takipçiye gider (asistan yanıtı değil)', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const a = await uye(env, 'Il_A'), b = await uye(env, 'Il_B');
    tg(env, a, 601);
    const r = await cagir(env, 'POST', '/ilan/csb-12345/yanit', { token: a.token, govde: { govde: 'Başvuru şartları neler acaba?', ilan_baslik: 'Deneme kurumu 2026 sözleşmeli personel alımı' } });
    const bid = r.json.baslik_id;
    assert.equal(tgCagrilari(f).length, 0);   // kendi sorusu: kimse yok
    await yanitla(env, b, bid, 'Şartlara ilan metninden bakabilirsin.');
    const g = tgCagrilari(f);
    assert.equal(g.length, 1);
    assert.equal(g[0].chat_id, 601);
    assert.equal(g[0].text, `Deneme kurumu 2026 sözleşmeli personel alımı: yeni mesaj\n${SITE}forum/?b=${bid}`);
  } finally { f.geri(); }
});

test('bildirimler: takip türü, oda bayrağı, öncelik (alıntı > anma > yanıt > takip), kendi mesajı ve 14 gün dışı yok', async () => {
  const env = ortam();
  const ben = await uye(env, 'Ben_B'), x = await uye(env, 'Diger_X'), z = await uye(env, 'Diger_Z');
  const t = Math.floor(Date.now() / 1000);
  const hamYanit = (baslik, uyeId, govde, olusma, ust = null) => Number(env.DB.ham.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, ust_id) VALUES (?, ?, ?, ?, ?)').run(baslik, uyeId, govde, olusma, ust).lastInsertRowid);
  const hamBaslik = (kategori, ad, uyeId) => Number(env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES (?, ?, 'x', ?, 1, 1)").run(kategori, ad, uyeId).lastInsertRowid);
  const takipEt = (b) => env.DB.ham.prepare('INSERT INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, 1)').run(ben.id, b);
  const dize = hamBaslik('puan', 'Takip edilen konu', x.id), odaB = hamBaslik('oda', 'Takip edilen oda', 1);
  const kendi = hamBaslik('puan', 'Benim konum', ben.id), eski = hamBaslik('puan', 'Eski konu', x.id);
  [dize, odaB, kendi, eski].forEach(takipEt);
  const y1 = hamYanit(dize, x.id, 'konuda ilk mesaj', t - 500);            // takip
  const y2 = hamYanit(odaB, z.id, 'odada mesaj', t - 400);                  // takip, oda
  const y3 = hamYanit(kendi, x.id, 'sana yanıt', t - 300);                  // yanıt (kendi başlığım) ve takip -> yanıt kazanır
  const y4 = hamYanit(dize, z.id, 'bak @Ben_B bu önemli', t - 200);         // anma kazanır
  const benimY = hamYanit(dize, ben.id, 'benim yanıtım', t - 190);
  const y5 = hamYanit(dize, x.id, 'yanıtına alıntı', t - 100, benimY);      // alıntı kazanır
  hamYanit(dize, ben.id, 'bir tane daha benim', t - 90);                    // kendi mesajı yok
  hamYanit(eski, x.id, 'çok eski', t - 15 * 86400);                         // 14 gün dışı
  hamYanit(dize, x.id, 'gizli olan', t - 50);
  env.DB.ham.prepare("UPDATE yanitlar SET gizli = 1 WHERE govde = 'gizli olan'").run();
  const r = await cagir(env, 'GET', '/ben/bildirimler', { token: ben.token });
  assert.equal(r.durum, 200);
  assert.deepEqual(r.json.bildirimler.map((b) => [b.yanit_id, b.tur, b.oda]), [
    [y5, 'alinti', false], [y4, 'anma', false], [y3, 'yanit', false], [y2, 'takip', true], [y1, 'takip', false],
  ]);
  assert.deepEqual(Object.keys(r.json.bildirimler[4]).sort(), ['baslik', 'baslik_id', 'kisa', 'oda', 'olusma', 'rol', 'rumuz', 'tur', 'yanit_id']);
  assert.equal(r.json.bildirimler[3].baslik, 'Takip edilen oda'); assert.equal(r.json.bildirimler[3].rumuz, 'Diger_Z');
  // takip bırakılınca takip bildirimleri kalkar, diğerleri kalır
  await cagir(env, 'POST', `/baslik/${dize}/takip`, { token: ben.token, govde: { takip: false } });
  await cagir(env, 'POST', `/baslik/${odaB}/takip`, { token: ben.token, govde: { takip: false } });
  const r2 = await cagir(env, 'GET', '/ben/bildirimler', { token: ben.token });
  assert.deepEqual(r2.json.bildirimler.map((b) => [b.yanit_id, b.tur]), [[y5, 'alinti'], [y4, 'anma'], [y3, 'yanit']]);
  // sonra filtresi takip öğelerine de uygulanır
  takipEt(dize);
  const r3 = await cagir(env, 'GET', `/ben/bildirimler?sonra=${t - 250}`, { token: ben.token });
  assert.deepEqual(r3.json.bildirimler.map((b) => b.yanit_id), [y5, y4]);
});
