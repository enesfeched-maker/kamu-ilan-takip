import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir, uyeGirisi, zamaniGeriAl, kayitEskit, telegramImzala, ilanSiteFetch, sahteFetch, ORNEK_ILAN, UUID } from './yardim.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const BASLIK = { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' };

async function eskiUye(env, rumuz, rol) {
  const u = await uyeGirisi(env, rumuz, rol);
  kayitEskit(env, u.id);
  return u;
}

// ---------- giriş ----------
test('telegram girişi: yeni üye -> geçici jeton -> rumuz -> oturum; sonra doğrudan giriş', async () => {
  const env = ortam();
  const a = { id: 777, first_name: 'Ali', username: 'ali', auth_date: Math.floor(Date.now() / 1000) - 5 };
  a.hash = await telegramImzala(env.TELEGRAM_BOT_TOKEN, a);
  const r1 = await cagir(env, 'POST', '/giris/telegram', { govde: a });
  assert.equal(r1.durum, 200); assert.equal(r1.json.yeni, true); assert.ok(r1.json.gecici);
  const r2 = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: r1.json.gecici, rumuz: 'Ali_Veli' } });
  assert.equal(r2.durum, 200);
  assert.equal(r2.json.uye.rumuz, 'Ali_Veli'); assert.equal(r2.json.uye.kurucu, true); assert.equal(r2.json.uye.rol, 'uye');
  const kayit = env.DB.ham.prepare('SELECT * FROM uyeler WHERE tg_id = 777').get();
  assert.deepEqual(Object.keys(kayit).sort(), ['bildirim', 'dm_acik', 'engelli', 'id', 'itibar', 'kayit', 'kurucu', 'rol', 'rumuz', 'tg_id']); // ad/kullanıcı adı/foto saklanmaz
  const ben = await cagir(env, 'GET', '/ben', { token: r2.json.oturum });
  assert.equal(ben.durum, 200); assert.equal(ben.json.uye.rumuz, 'Ali_Veli');
  const r3 = await cagir(env, 'POST', '/giris/telegram', { govde: a });
  assert.equal(r3.json.uye.id, r2.json.uye.id); assert.ok(r3.json.oturum);
});

test('telegram girişi: bozuk hash 401, eski tarih 401, token yoksa 503', async () => {
  const env = ortam();
  const a = { id: 5, auth_date: Math.floor(Date.now() / 1000) };
  a.hash = 'f'.repeat(64);
  assert.equal((await cagir(env, 'POST', '/giris/telegram', { govde: a })).durum, 401);
  const eski = { id: 5, auth_date: Math.floor(Date.now() / 1000) - 90000 };
  eski.hash = await telegramImzala(env.TELEGRAM_BOT_TOKEN, eski);
  assert.equal((await cagir(env, 'POST', '/giris/telegram', { govde: eski })).durum, 401);
  assert.equal((await cagir(ortam({ TELEGRAM_BOT_TOKEN: undefined }), 'POST', '/giris/telegram', { govde: a })).durum, 503);
});

test('rumuz: çakışma 409, geçersiz 400, geçersiz geçici jeton 401, kurucu 200. üyeye kadar', async () => {
  const env = ortam();
  const gecici = async (id) => {
    const a = { id, auth_date: Math.floor(Date.now() / 1000) };
    a.hash = await telegramImzala(env.TELEGRAM_BOT_TOKEN, a);
    return (await cagir(env, 'POST', '/giris/telegram', { govde: a })).json.gecici;
  };
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: await gecici(1), rumuz: 'Deneme' } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: await gecici(2), rumuz: 'deneme' } })).durum, 409);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: await gecici(2), rumuz: 'Asistan' } })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: 'x.y', rumuz: 'Kimse' } })).durum, 401);
  // 200 üye dolunca kurucu rozeti verilmez
  const ekle = env.DB.ham.prepare("INSERT INTO uyeler (tg_id, rumuz, kayit, kurucu) VALUES (?, ?, 0, 1)");
  for (let i = 0; i < 199; i++) ekle.run(1000 + i, `dolgu${i}`);
  const son = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: await gecici(3), rumuz: 'Gec_Kalan' } });
  assert.equal(son.json.uye.kurucu, false);
});

test('deneme girişi üretimde 404, yerelde çalışır', async () => {
  const uretim = ortam();
  assert.equal((await cagir(uretim, 'POST', '/giris/deneme', { govde: { rumuz: 'Test1' } })).durum, 404);
  const yerel = ortam({ ORTAM: 'yerel' });
  const r = await cagir(yerel, 'POST', '/giris/deneme', { govde: { rumuz: 'Test1' } });
  assert.equal(r.durum, 200);
  assert.ok(env_tg(yerel, 'Test1') < 0);
  const tekrar = await cagir(yerel, 'POST', '/giris/deneme', { govde: { rumuz: 'test1' } });
  assert.equal(tekrar.json.uye.id, r.json.uye.id);
  assert.equal((await cagir(yerel, 'POST', '/giris/deneme', { govde: { rumuz: 'Asistan' } })).durum, 400);
});
const env_tg = (env, rumuz) => env.DB.ham.prepare('SELECT tg_id FROM uyeler WHERE rumuz = ?').get(rumuz).tg_id;

test('/ben: jeton yok 401; bildirim kapatma; engelli üye yazamaz', async () => {
  const env = ortam();
  assert.equal((await cagir(env, 'GET', '/ben')).durum, 401);
  assert.equal((await cagir(env, 'GET', '/ben', { token: 'sacma.jeton' })).durum, 401);
  const u = await eskiUye(env, 'Bildirimci');
  assert.equal((await cagir(env, 'POST', '/ben/bildirim', { token: u.token, govde: { acik: false } })).json.bildirim, false);
  assert.equal(env.DB.ham.prepare('SELECT bildirim FROM uyeler WHERE id = ?').get(u.id).bildirim, 0);
  assert.equal((await cagir(env, 'POST', '/ben/bildirim', { token: u.token, govde: { acik: 'evet' } })).durum, 400);
  env.DB.ham.prepare('UPDATE uyeler SET engelli = 1 WHERE id = ?').run(u.id);
  assert.equal((await cagir(env, 'POST', '/baslik', { token: u.token, govde: BASLIK })).durum, 403);
  assert.equal((await cagir(env, 'POST', '/giris/telegram', { govde: {} })).durum, 401);
});

// ---------- başlıklar ----------
test('başlık oluştur + listele: sabit önce, sonra son hareket; gizli yok; sayfalama', async () => {
  const env = ortam();
  const u = await eskiUye(env, 'Yazar1');
  const r = await cagir(env, 'POST', '/baslik', { token: u.token, govde: BASLIK });
  assert.equal(r.durum, 201); assert.equal(r.json.baslik.rumuz, 'Yazar1'); assert.equal(r.json.baslik.yanit_sayisi, 0);
  const a = r.json.baslik.id;
  zamaniGeriAl(env, u.id);
  const r2 = await cagir(env, 'POST', '/baslik', { token: u.token, govde: { ...BASLIK, kategori: 'kurum', baslik: 'Ankara kurumları hakkında' } });
  const b = r2.json.baslik.id;
  const sabit = await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { kategori: 'etkinlik', baslik: 'Tercih dönemi canlı başlığı', govde: 'Tercih dönemi boyunca buradayız.', kaynak: 'sistem', sabit: true } });
  assert.equal(sabit.durum, 201);
  env.DB.ham.prepare('UPDATE basliklar SET son_hareket = son_hareket + 100 WHERE id = ?').run(b);
  const liste = await cagir(env, 'GET', '/basliklar');
  assert.deepEqual(liste.json.basliklar.map((x) => x.id), [sabit.json.baslik.id, b, a]);
  assert.equal(liste.json.basliklar[0].sabit, true); assert.equal(liste.json.basliklar[0].rumuz, 'KPSS Tercihi'); assert.equal(liste.json.basliklar[0].rol, 'sistem');
  assert.ok(liste.json.basliklar[1].kisa.length <= 140);
  assert.equal('govde' in liste.json.basliklar[1], false);
  assert.deepEqual((await cagir(env, 'GET', '/basliklar?kategori=puan')).json.basliklar.map((x) => x.id), [a]);
  assert.equal((await cagir(env, 'GET', '/basliklar?kategori=yok')).durum, 400);
  env.DB.ham.prepare('UPDATE basliklar SET gizli = 1 WHERE id = ?').run(a);
  assert.equal((await cagir(env, 'GET', '/basliklar?kategori=puan')).json.basliklar.length, 0);
  assert.equal((await cagir(env, 'GET', `/baslik/${a}`)).durum, 404);
  // sayfalama
  const ekle = env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('hazirlik', 'sayfa deneme', 'x', 1, 1, ?)");
  for (let i = 0; i < 25; i++) ekle.run(i + 1);
  const s1 = await cagir(env, 'GET', '/basliklar?kategori=hazirlik&sayfa=1');
  const s2 = await cagir(env, 'GET', '/basliklar?kategori=hazirlik&sayfa=2');
  assert.equal(s1.json.basliklar.length, 20); assert.equal(s1.json.sonraki, true);
  assert.equal(s2.json.basliklar.length, 5); assert.equal(s2.json.sonraki, false);
});

test('başlık kuralları: giriş şart, ilan/etkinlik kısıtı, uzunluk, denetim', async () => {
  const env = ortam();
  assert.equal((await cagir(env, 'POST', '/baslik', { govde: BASLIK })).durum, 401);
  const u = await eskiUye(env, 'Kural1');
  const dene = (ek) => cagir(env, 'POST', '/baslik', { token: u.token, govde: { ...BASLIK, ...ek } });
  assert.equal((await dene({ kategori: 'ilan' })).durum, 400);
  assert.equal((await dene({ kategori: 'etkinlik' })).durum, 403);
  assert.equal((await dene({ kategori: 'yok' })).durum, 400);
  assert.equal((await dene({ baslik: 'kısa' })).durum, 400);
  assert.equal((await dene({ govde: 'kısa' })).durum, 400);
  assert.equal((await dene({ govde: 'x'.repeat(4001) })).durum, 400);
  const k = await dene({ govde: 'Beni ara 0532 123 45 67 hemen yaz' });
  assert.equal(k.durum, 422); assert.equal(k.json.hata, 'Telefon numarası paylaşma.');
  assert.equal((await dene({ baslik: 'Bu da siktir bir başlık' })).durum, 422);
  const y = await eskiUye(env, 'Kurulbasi', 'yonetici');
  assert.equal((await cagir(env, 'POST', '/baslik', { token: y.token, govde: { ...BASLIK, kategori: 'etkinlik' } })).durum, 201);
});

test('başlık detayı: yanıtlar, gizli yanıt çıkmaz, oy işareti, ust_id', async () => {
  const env = ortam();
  const a = await eskiUye(env, 'Sahip');
  const b = await eskiUye(env, 'Yanitci');
  const t = (await cagir(env, 'POST', '/baslik', { token: a.token, govde: BASLIK })).json.baslik.id;
  const y1 = await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: b.token, govde: { govde: 'İlk yanıt burada' } });
  assert.equal(y1.durum, 201);
  zamaniGeriAl(env, a.id);
  const y2 = await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'Teşekkürler', ust_id: y1.json.yanit.id } });
  assert.equal(y2.json.yanit.ust_id, y1.json.yanit.id);
  assert.equal((await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'olmayan üst', ust_id: 99999 } })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/baslik/99999/yanit', { token: a.token, govde: { govde: 'yok başlık' } })).durum, 404);
  await cagir(env, 'POST', `/yanit/${y1.json.yanit.id}/faydali`, { token: a.token });
  const d = await cagir(env, 'GET', `/baslik/${t}`, { token: a.token });
  assert.equal(d.json.baslik.yanit_sayisi, 2); assert.equal(d.json.yanitlar.length, 2);
  assert.equal(d.json.yanitlar[0].faydali, 1); assert.equal(d.json.yanitlar[0].oyladim, true); assert.equal(d.json.yanitlar[1].benim, true);
  assert.equal(d.json.yanitlar[0].rumuz, 'Yanitci');
  const anon = await cagir(env, 'GET', `/baslik/${t}`);
  assert.equal('oyladim' in anon.json.yanitlar[0], false);
  env.DB.ham.prepare('UPDATE yanitlar SET gizli = 1 WHERE id = ?').run(y2.json.yanit.id);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`)).json.yanitlar.length, 1);
});

// ---------- ilan ----------
test('ilan: tembel başlık + asistan yanıtı + /ilan ve /ozet', async () => {
  const env = ortam();
  const f = ilanSiteFetch();
  try {
    const u = await eskiUye(env, 'Soran');
    assert.equal((await cagir(env, 'GET', `/ilan/${UUID}`)).json.baslik, null);
    const r = await cagir(env, 'POST', `/ilan/${UUID}/yanit`, { token: u.token, govde: { govde: 'Başvurular ne zamana kadar? Yaş sınırı var mı?', ilan_baslik: 'istemci başlığı yok sayılır' } });
    assert.equal(r.durum, 201);
    assert.equal(r.json.yanitlar.length, 2);
    assert.equal(r.json.yanitlar[1].rumuz, 'Asistan'); assert.equal(r.json.yanitlar[1].rol, 'asistan');
    assert.equal(r.json.yanitlar[1].ust_id, r.json.yanitlar[0].id);
    assert.match(r.json.yanitlar[1].govde, /^İlan belgesine göre:.*25 Eylül 2026.*35 yaş.*Kesin bilgi için resmî ilan belgesine bak\.$/);
    const th = env.DB.ham.prepare('SELECT * FROM basliklar WHERE ilan_id = ?').get(UUID);
    assert.equal(th.kategori, 'ilan'); assert.equal(th.uye_id, 1); assert.equal(th.kaynak, 'sistem'); assert.equal(th.govde, '');
    assert.equal(th.baslik, ORNEK_ILAN.baslik); assert.equal(th.yanit_sayisi, 2);
    zamaniGeriAl(env, u.id);
    const r2 = await cagir(env, 'POST', `/ilan/${UUID}/yanit`, { token: u.token, govde: { govde: 'Bu kurumda çalışmak nasıl?' } });
    assert.equal(r2.json.yanitlar.length, 1); // asistan susar
    assert.equal(env.DB.ham.prepare('SELECT COUNT(*) AS n FROM basliklar WHERE ilan_id = ?').get(UUID).n, 1);
    const g = await cagir(env, 'GET', `/ilan/${UUID}`);
    assert.equal(g.json.baslik.yanit_sayisi, 3); assert.equal(g.json.yanitlar.length, 3);
    assert.deepEqual(g.json.basvuru, { sayi: 0, puan: null, ben: null });
    const oz = await cagir(env, 'GET', `/ozet?ilanlar=${UUID},csb-12345,bozuk`);
    assert.deepEqual(oz.json, { [UUID]: { yanit: 3, basvuru: 0 }, 'csb-12345': { yanit: 0, basvuru: 0 } });
    assert.equal((await cagir(env, 'GET', '/ilan/bozuk-id')).durum, 400);
    assert.equal((await cagir(env, 'POST', '/ilan/bozuk-id/yanit', { token: u.token, govde: { govde: 'selam' } })).durum, 400);
  } finally { f.geri(); }
});

test('ilan: kayıt yoksa istemci başlığı kullanılır ve denetlenir', async () => {
  const env = ortam();
  const f = ilanSiteFetch([]);
  try {
    const u = await eskiUye(env, 'Soran2');
    const yol = '/ilan/csb-12345/yanit';
    assert.equal((await cagir(env, 'POST', yol, { token: u.token, govde: { govde: 'merhaba ilan' } })).durum, 400); // başlık yok
    assert.equal((await cagir(env, 'POST', yol, { token: u.token, govde: { govde: 'merhaba ilan', ilan_baslik: 'Bak https://evil.com/ çok güzel ilan' } })).durum, 422);
    const ok = await cagir(env, 'POST', yol, { token: u.token, govde: { govde: 'merhaba ilan', ilan_baslik: '  Temiz   bir ilan başlığı  ' } });
    assert.equal(ok.durum, 201); assert.equal(ok.json.yanitlar.length, 1);
    assert.equal(env.DB.ham.prepare("SELECT baslik FROM basliklar WHERE ilan_id = 'csb-12345'").get().baslik, 'Temiz bir ilan başlığı');
  } finally { f.geri(); }
});

// ---------- faydalı / şikayet ----------
test('faydalı: aç-kapa, kendi yanıtına yok', async () => {
  const env = ortam();
  const a = await eskiUye(env, 'Ya1'), b = await eskiUye(env, 'Ya2');
  const t = (await cagir(env, 'POST', '/baslik', { token: a.token, govde: BASLIK })).json.baslik.id;
  const y = (await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'benim yanıtım' } })).json.yanit.id;
  assert.equal((await cagir(env, 'POST', `/yanit/${y}/faydali`, { token: a.token })).durum, 400);
  assert.deepEqual((await cagir(env, 'POST', `/yanit/${y}/faydali`, { token: b.token })).json, { faydali: 1, oyladim: true });
  assert.deepEqual((await cagir(env, 'POST', `/yanit/${y}/faydali`, { token: b.token })).json, { faydali: 0, oyladim: false });
  assert.deepEqual((await cagir(env, 'POST', `/yanit/${y}/faydali`, { token: b.token })).json, { faydali: 1, oyladim: true });
  assert.equal((await cagir(env, 'POST', `/yanit/${y}/faydali`)).durum, 401);
  assert.equal((await cagir(env, 'POST', '/yanit/9999/faydali', { token: b.token })).durum, 404);
});

test('şikayet: kişi başı bir, 3 şikayette otomatik gizlenir ve sayaç düşer', async () => {
  const env = ortam();
  const a = await eskiUye(env, 'Sk1');
  const t = (await cagir(env, 'POST', '/baslik', { token: a.token, govde: BASLIK })).json.baslik.id;
  const y = (await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'şikayet edilecek yanıt' } })).json.yanit.id;
  const s = [await eskiUye(env, 'Sk2'), await eskiUye(env, 'Sk3'), await eskiUye(env, 'Sk4')];
  assert.equal((await cagir(env, 'POST', `/yanit/${y}/sikayet`, { token: s[0].token })).json.gizlendi, false);
  assert.equal((await cagir(env, 'POST', `/yanit/${y}/sikayet`, { token: s[0].token })).json.zaten, true);
  assert.equal(env.DB.ham.prepare('SELECT sikayet FROM yanitlar WHERE id = ?').get(y).sikayet, 1);
  await cagir(env, 'POST', `/yanit/${y}/sikayet`, { token: s[1].token });
  assert.equal(env.DB.ham.prepare('SELECT gizli FROM yanitlar WHERE id = ?').get(y).gizli, 0);
  const son = await cagir(env, 'POST', `/yanit/${y}/sikayet`, { token: s[2].token });
  assert.equal(son.json.gizlendi, true);
  assert.equal(env.DB.ham.prepare('SELECT gizli FROM yanitlar WHERE id = ?').get(y).gizli, 1);
  assert.equal((await cagir(env, 'GET', `/baslik/${t}`)).json.yanitlar.length, 0);
  assert.equal(env.DB.ham.prepare('SELECT yanit_sayisi FROM basliklar WHERE id = ?').get(t).yanit_sayisi, 0);
  const lis = await cagir(env, 'GET', '/yonetim/sikayetler', { basliklar: YONETICI });
  assert.equal(lis.json.yanitlar[0].id, y); assert.equal(lis.json.yanitlar[0].sikayet, 3); assert.equal(lis.json.yanitlar[0].gizli, true);
});

// ---------- başvuru ----------
const KIM = (n) => `cihaz-${String(n).padStart(12, '0')}`;
test('başvuru: upsert, 5 puan eşiği, tek tek satır sızmaz, sıra', async () => {
  const env = ortam();
  const yol = `/basvuru/${UUID}`;
  const p = (n, puan, tur = 'P3') => cagir(env, 'POST', yol, { govde: { kimlik: KIM(n), puan_turu: tur, puan } });
  assert.equal((await cagir(env, 'POST', yol, { govde: { kimlik: KIM(0) } })).json.basvuru.sayi, 1);
  assert.equal((await cagir(env, 'POST', yol, { govde: { kimlik: KIM(0) } })).json.basvuru.sayi, 1); // upsert
  for (const [n, puan] of [[1, 70], [2, 75.5], [3, 80], [4, 85]]) {
    const r = await p(n, puan);
    assert.equal(r.json.basvuru.puan, null, 'eşik altı sızmamalı');
  }
  const bes = await p(5, 90.456);
  assert.deepEqual(bes.json.basvuru.puan, { adet: 5, puan_turu: 'P3', en_dusuk: 70, ceyrek1: 75.5, medyan: 80, ceyrek3: 85, en_yuksek: 90.46, sira: 1 });
  assert.equal(bes.json.basvuru.sayi, 6);
  assert.deepEqual(bes.json.basvuru.ben, { puan_turu: 'P3', puan: 90.46 });
  const g = await cagir(env, 'GET', `/ilan/${UUID}?kimlik=${KIM(1)}`);
  assert.equal(g.json.basvuru.puan.sira, 5);
  const anon = await cagir(env, 'GET', `/ilan/${UUID}`);
  assert.equal('sira' in anon.json.basvuru.puan, false); assert.equal(anon.json.basvuru.ben, null);
  assert.equal(JSON.stringify(anon.json).includes('cihaz-'), false); // kimlik/satır sızmaz
  // puanı olmayan yeniden gönderim eski puanı silmez
  await cagir(env, 'POST', yol, { govde: { kimlik: KIM(1) } });
  assert.equal(env.DB.ham.prepare('SELECT puan FROM basvurular WHERE kimlik = ?').get(KIM(1)).puan, 70);
  // puan güncelleme
  await p(1, 99);
  assert.equal((await cagir(env, 'GET', `/ilan/${UUID}`)).json.basvuru.puan.en_yuksek, 99);
  // geri alma
  const sil = await cagir(env, 'DELETE', `${yol}?kimlik=${KIM(5)}`);
  assert.equal(sil.json.basvuru.sayi, 5); assert.equal(sil.json.basvuru.puan, null); // 4 puan kaldı
});

test('başvuru: en yaygın puan türü hesaplanır; doğrulamalar', async () => {
  const env = ortam();
  const yol = `/basvuru/${UUID}`;
  for (let i = 0; i < 6; i++) await cagir(env, 'POST', yol, { govde: { kimlik: KIM(i), puan_turu: 'P93', puan: 60 + i } });
  for (let i = 10; i < 13; i++) await cagir(env, 'POST', yol, { govde: { kimlik: KIM(i), puan_turu: 'P3', puan: 70 } });
  const g = (await cagir(env, 'GET', `/ilan/${UUID}`)).json.basvuru;
  assert.equal(g.puan.puan_turu, 'P93'); assert.equal(g.puan.adet, 6); assert.equal(g.sayi, 9);
  const kotu = (govde) => cagir(env, 'POST', yol, { govde });
  assert.equal((await kotu({ kimlik: 'kisa' })).durum, 400);
  assert.equal((await kotu({ kimlik: KIM(50), puan_turu: 'X3', puan: 70 })).durum, 400);
  assert.equal((await kotu({ kimlik: KIM(50), puan_turu: 'P3', puan: 39 })).durum, 400);
  assert.equal((await kotu({ kimlik: KIM(50), puan_turu: 'P3', puan: 101 })).durum, 400);
  assert.equal((await kotu({ kimlik: KIM(50), puan_turu: 'P3' })).durum, 400);
  assert.equal((await kotu({ kimlik: KIM(50), puan: 70 })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/basvuru/bozuk', { govde: { kimlik: KIM(50) } })).durum, 400);
  // oturum açmış üye 'u<id>' kimliğiyle yazar
  const u = await eskiUye(env, 'Basvuran');
  await cagir(env, 'POST', yol, { token: u.token, govde: { puan_turu: 'P3', puan: 71 } });
  assert.ok(env.DB.ham.prepare('SELECT 1 FROM basvurular WHERE kimlik = ?').get(`u${u.id}`));
});

// ---------- yönetim ----------
test('yönetim: anahtar yoksa/yanlışsa 401; başlık, gizle, engelle', async () => {
  const env = ortam();
  for (const [y, yol] of [['POST', '/yonetim/baslik'], ['POST', '/yonetim/gizle'], ['POST', '/yonetim/engelle'], ['GET', '/yonetim/sikayetler']]) {
    assert.equal((await cagir(env, y, yol, { govde: y === 'POST' ? {} : undefined })).durum, 401, yol);
    assert.equal((await cagir(env, y, yol, { govde: y === 'POST' ? {} : undefined, basliklar: { 'X-Yonetici': 'yanlis' } })).durum, 401, yol);
  }
  assert.equal((await cagir(ortam({ YONETICI_ANAHTARI: undefined }), 'GET', '/yonetim/sikayetler', { basliklar: { 'X-Yonetici': 'undefined' } })).durum, 401);
  const tg = await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { kategori: 'puan', baslik: 'Telegram kanalından gelen soru', govde: 'Kanal sorusu burada, yanıtlayın lütfen.', kaynak: 'telegram' } });
  assert.equal(tg.durum, 201); assert.equal(tg.json.baslik.kaynak, 'telegram'); assert.equal(tg.json.baslik.rumuz, 'KPSS Tercihi'); assert.equal(tg.json.baslik.sabit, false);
  assert.equal((await cagir(env, 'POST', '/yonetim/baslik', { basliklar: YONETICI, govde: { kategori: 'puan', baslik: 'Telegram kanalından gelen soru', govde: 'Kanal sorusu burada.', kaynak: 'uye' } })).durum, 400);
  const id = tg.json.baslik.id;
  await cagir(env, 'POST', '/yonetim/gizle', { basliklar: YONETICI, govde: { tur: 'baslik', id, gizli: true } });
  assert.equal((await cagir(env, 'GET', `/baslik/${id}`)).durum, 404);
  await cagir(env, 'POST', '/yonetim/gizle', { basliklar: YONETICI, govde: { tur: 'baslik', id, gizli: false } });
  assert.equal((await cagir(env, 'GET', `/baslik/${id}`)).durum, 200);
  const u = await eskiUye(env, 'Yaramaz');
  assert.equal((await cagir(env, 'POST', '/yonetim/engelle', { basliklar: YONETICI, govde: { uye_id: u.id, engelli: true } })).durum, 200);
  assert.equal((await cagir(env, 'POST', `/baslik/${id}/yanit`, { token: u.token, govde: { govde: 'yazamam' } })).durum, 403);
  await cagir(env, 'POST', '/yonetim/engelle', { basliklar: YONETICI, govde: { uye_id: u.id, engelli: false } });
  assert.equal((await cagir(env, 'POST', `/baslik/${id}/yanit`, { token: u.token, govde: { govde: 'yazabilirim' } })).durum, 201);
  await cagir(env, 'POST', '/yonetim/engelle', { basliklar: YONETICI, govde: { uye_id: 1, engelli: true } });
  assert.equal(env.DB.ham.prepare('SELECT engelli FROM uyeler WHERE id = 1').get().engelli, 0);
});

// ---------- hız sınırları ----------
test('hız: başlık 2 dk, günde 10, yeni üye günde 3; yanıt 20 sn, günde 60', async () => {
  const env = ortam();
  const yeni = await uyeGirisi(env, 'Yeni1');
  const b = (u, i) => cagir(env, 'POST', '/baslik', { token: u.token, govde: { ...BASLIK, baslik: `Başlık sayısı ${i} deneme` } });
  assert.equal((await b(yeni, 1)).durum, 201);
  assert.equal((await b(yeni, 2)).durum, 429);
  zamaniGeriAl(env, yeni.id, 300);
  assert.equal((await b(yeni, 2)).durum, 201);
  zamaniGeriAl(env, yeni.id, 300);
  assert.equal((await b(yeni, 3)).durum, 201);
  zamaniGeriAl(env, yeni.id, 300);
  const r = await b(yeni, 4);
  assert.equal(r.durum, 429); assert.match(r.json.hata, /ilk gün en fazla 3/);

  const eski = await eskiUye(env, 'Eski1');
  for (let i = 0; i < 10; i++) { assert.equal((await b(eski, i)).durum, 201, `başlık ${i}`); zamaniGeriAl(env, eski.id, 300); }
  const on = await b(eski, 11);
  assert.equal(on.durum, 429); assert.match(on.json.hata, /sınırına ulaştın/);

  const t = env.DB.ham.prepare('SELECT id FROM basliklar LIMIT 1').get().id;
  const y = (u) => cagir(env, 'POST', `/baslik/${t}/yanit`, { token: u.token, govde: { govde: 'hızlı yanıt' } });
  const ya = await eskiUye(env, 'Yaz1');
  assert.equal((await y(ya)).durum, 201);
  assert.equal((await y(ya)).durum, 429);
  for (let i = 0; i < 59; i++) { zamaniGeriAl(env, ya.id, 30); assert.equal((await y(ya)).durum, 201, `yanıt ${i}`); }
  zamaniGeriAl(env, ya.id, 30);
  const son = await y(ya);
  assert.equal(son.durum, 429); assert.match(son.json.hata, /Bugün/);
});

// ---------- kill switch ----------
test('YAZMA_KAPALI=1: yazmalar 503, okuma ve yönetim açık', async () => {
  const env = ortam();
  const u = await eskiUye(env, 'Kapali1');
  const kapali = { ...env, YAZMA_KAPALI: '1' };
  assert.equal((await cagir(kapali, 'POST', '/baslik', { token: u.token, govde: BASLIK })).durum, 503);
  assert.equal((await cagir(kapali, 'POST', `/basvuru/${UUID}`, { govde: { kimlik: KIM(1) } })).durum, 503);
  assert.equal((await cagir(kapali, 'POST', '/giris/telegram', { govde: {} })).durum, 503);
  assert.equal((await cagir(kapali, 'DELETE', `/basvuru/${UUID}?kimlik=${KIM(1)}`)).durum, 503);
  assert.equal((await cagir(kapali, 'GET', '/basliklar')).durum, 200);
  assert.equal((await cagir(kapali, 'GET', '/yonetim/sikayetler', { basliklar: YONETICI })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/baslik', { token: u.token, govde: BASLIK })).durum, 201);
});

// ---------- CORS ----------
test('CORS: izinli köken, reddedilen köken, localhost yalnız yerelde, preflight', async () => {
  const env = ortam();
  const ok = await cagir(env, 'GET', '/kategoriler', { origin: 'https://kpsstercihi.com' });
  assert.equal(ok.basliklar.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.equal(ok.json.kategoriler.length, 8); assert.equal(ok.json.kategoriler[0].kod, 'ilan');
  assert.equal((await cagir(env, 'GET', '/kategoriler', { origin: 'https://www.kpsstercihi.com' })).basliklar.get('Access-Control-Allow-Origin'), 'https://www.kpsstercihi.com');
  assert.equal((await cagir(env, 'GET', '/kategoriler', { origin: 'https://evil.com' })).basliklar.get('Access-Control-Allow-Origin'), null);
  assert.equal((await cagir(env, 'GET', '/kategoriler', { origin: 'http://localhost:8000' })).basliklar.get('Access-Control-Allow-Origin'), null);
  assert.equal((await cagir(env, 'POST', '/giris/deneme', { origin: 'https://evil.com', govde: { rumuz: 'Abc' } })).durum, 403);
  const yerel = ortam({ ORTAM: 'yerel' });
  assert.equal((await cagir(yerel, 'GET', '/kategoriler', { origin: 'http://localhost:8000' })).basliklar.get('Access-Control-Allow-Origin'), 'http://localhost:8000');
  assert.equal((await cagir(yerel, 'GET', '/kategoriler', { origin: 'http://127.0.0.1:5500' })).basliklar.get('Access-Control-Allow-Origin'), 'http://127.0.0.1:5500');
  assert.equal((await cagir(yerel, 'GET', '/kategoriler', { origin: 'http://localhost.evil.com' })).basliklar.get('Access-Control-Allow-Origin'), null);
  assert.equal((await cagir(yerel, 'GET', '/kategoriler', { origin: 'https://localhost:8000' })).basliklar.get('Access-Control-Allow-Origin'), null);
  const pre = await cagir(env, 'OPTIONS', '/baslik', { origin: 'https://kpsstercihi.com' });
  assert.equal(pre.durum, 204);
  assert.match(pre.basliklar.get('Access-Control-Allow-Headers'), /Authorization/); assert.match(pre.basliklar.get('Access-Control-Allow-Headers'), /Content-Type/);
  assert.equal((await cagir(env, 'OPTIONS', '/baslik', { origin: 'https://evil.com' })).durum, 403);
});

test('/son: son hareketli 10 başlık; bilinmeyen yol 404', async () => {
  const env = ortam();
  const ekle = env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('puan', ?, 'x', 1, 1, ?)");
  for (let i = 0; i < 12; i++) ekle.run(`Başlık ${i}`, i + 10);
  const r = await cagir(env, 'GET', '/son');
  assert.equal(r.json.basliklar.length, 10); assert.equal(r.json.basliklar[0].baslik, 'Başlık 11');
  assert.equal((await cagir(env, 'GET', '/yok')).durum, 404);
});

test('/durum: gerçek üye ve son 24 saat sayıları; site ve asistan hesapları sayılmaz', async () => {
  const env = ortam();
  const d0 = (await cagir(env, 'GET', '/durum')).json;
  assert.deepEqual(d0, {
    uye: 0, kurucu_kalan: 200, bugun_mesaj: 0, bugun_yazar: 0,
    kategoriler: { ilan: 0, puan: 0, kurum: 0, mulakat: 0, haklar: 0, hazirlik: 0, etkinlik: 0, oda: 0 }, bekleyen: 0, gundem: [], bekleyenler: [],
  });
  const { token } = await uyeGirisi(env, 'ayse_k');
  const b = await cagir(env, 'POST', '/baslik', { token, govde: BASLIK });
  await cagir(env, 'POST', `/baslik/${b.json.baslik.id}/yanit`, { token, govde: { govde: 'Bir ek not yazayım.' } });
  const d = (await cagir(env, 'GET', '/durum')).json;
  assert.equal(d.uye, 1); assert.equal(d.kurucu_kalan, 199);
  assert.equal(d.bugun_mesaj, 1); assert.equal(d.bugun_yazar, 1);
});

// ---------- bildirim ----------
test('bildirim: başlık sahibine Telegram mesajı; kendine, kapalıysa, 10 dk içinde tekrar yok', async () => {
  const env = ortam();
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const sahip = await eskiUye(env, 'Sahibi');
    env.DB.ham.prepare('UPDATE uyeler SET tg_id = 4242 WHERE id = ?').run(sahip.id); // deneme üyesi negatif tg_id taşır
    const yanitci = await eskiUye(env, 'Yanitlayan');
    const t = (await cagir(env, 'POST', '/baslik', { token: sahip.token, govde: BASLIK })).json.baslik.id;
    await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: sahip.token, govde: { govde: 'kendi başlığıma' } });
    assert.equal(f.cagrilar.length, 0);
    await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: yanitci.token, govde: { govde: 'merhaba yanıt' } });
    assert.equal(f.cagrilar.length, 1);
    assert.match(f.cagrilar[0].url, /api\.telegram\.org\/bot123456:TEST-TOKEN\/sendMessage/);
    const g = JSON.parse(f.cagrilar[0].secenek.body);
    assert.equal(g.chat_id, 4242);
    assert.equal(g.text, `Yanitlayan başlığına yanıt yazdı: ${BASLIK.baslik.slice(0, 60)}\nhttps://kpsstercihi.com/forum/?b=${t}`);
    zamaniGeriAl(env, yanitci.id);
    await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: yanitci.token, govde: { govde: 'ikinci yanıt' } });
    assert.equal(f.cagrilar.length, 1, '10 dk içinde ikinci bildirim yok');
    // bildirim kapalı
    const diger = (await cagir(env, 'POST', '/baslik', { token: sahip.token, govde: { ...BASLIK, baslik: 'Başka bir konu başlığı' } }));
    assert.equal(diger.durum, 429);
    zamaniGeriAl(env, sahip.id);
    const t2 = (await cagir(env, 'POST', '/baslik', { token: sahip.token, govde: { ...BASLIK, baslik: 'Başka bir konu başlığı' } })).json.baslik.id;
    await cagir(env, 'POST', '/ben/bildirim', { token: sahip.token, govde: { acik: false } });
    zamaniGeriAl(env, yanitci.id);
    await cagir(env, 'POST', `/baslik/${t2}/yanit`, { token: yanitci.token, govde: { govde: 'kapalıya yanıt' } });
    assert.equal(f.cagrilar.length, 1);
  } finally { f.geri(); }
});

test('bildirim: yanıtlanan yanıtın yazarına gider; yerelde ya da token yoksa gitmez', async () => {
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const env = ortam();
    const a = await eskiUye(env, 'Ata'), b = await eskiUye(env, 'Cevap');
    env.DB.ham.prepare('UPDATE uyeler SET tg_id = 9001 WHERE id = ?').run(b.id);
    const t = (await cagir(env, 'POST', '/baslik', { token: a.token, govde: BASLIK })).json.baslik.id;
    const y = (await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: b.token, govde: { govde: 'ilk yanıt' } })).json.yanit.id;
    const n0 = f.cagrilar.length;
    await cagir(env, 'POST', `/baslik/${t}/yanit`, { token: a.token, govde: { govde: 'sana cevap', ust_id: y } });
    assert.equal(f.cagrilar.length, n0 + 1);
    assert.equal(JSON.parse(f.cagrilar.at(-1).secenek.body).chat_id, 9001);
    // yerel ortam
    const yerel = ortam({ ORTAM: 'yerel' });
    const u1 = await eskiUye(yerel, 'Yerel1'), u2 = await eskiUye(yerel, 'Yerel2');
    yerel.DB.ham.prepare('UPDATE uyeler SET tg_id = 5 WHERE id = ?').run(u1.id);
    const t3 = (await cagir(yerel, 'POST', '/baslik', { token: u1.token, govde: BASLIK })).json.baslik.id;
    const onceki = f.cagrilar.length;
    await cagir(yerel, 'POST', `/baslik/${t3}/yanit`, { token: u2.token, govde: { govde: 'yerel yanıt' } });
    assert.equal(f.cagrilar.length, onceki);
    // token yok
    const env2 = ortam({ TELEGRAM_BOT_TOKEN: undefined });
    const v1 = await eskiUye(env2, 'Tok1'), v2 = await eskiUye(env2, 'Tok2');
    env2.DB.ham.prepare('UPDATE uyeler SET tg_id = 6 WHERE id = ?').run(v1.id);
    const t4 = (await cagir(env2, 'POST', '/baslik', { token: v1.token, govde: BASLIK })).json.baslik.id;
    await cagir(env2, 'POST', `/baslik/${t4}/yanit`, { token: v2.token, govde: { govde: 'tokensiz yanıt' } });
    assert.equal(f.cagrilar.length, onceki);
  } finally { f.geri(); }
});
