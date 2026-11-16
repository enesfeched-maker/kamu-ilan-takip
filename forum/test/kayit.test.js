import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir, uyeGirisi, kayitEskit, sahteFetch, telegramImzala } from './yardim.js';
import { b64uKodla, metinB64u } from '../src/yardimci.js';
import { oturumUret, geciciUret, geciciTgKimligi, geciciGoogleUret, geciciGoogleKimligi, oturumUyeKimligi } from '../src/oturum.js';
import { sifreYapilandirildi, sifreKurali, sifreOzetle, sifreDogrula, kurtarmaKoduUret, kurtarmaKoduSadelestir, kurtarmaKoduBicimiGecerli } from '../src/sifre.js';
import { googleJetonuDogrula, googleAnahtarOnbellegiTemizle } from '../src/google.js';
import { profilTemizle } from '../src/profil.js';
import { kayitliTemizle, kayitliOku } from '../src/kayitli.js';
import { ipSinirSifirla, ipOnEki, ipAnahtari, denemeYaz, denemeTemizle, KAYIT_SINIRI } from '../src/hiz.js';
import { rumuzKat } from '../src/oturum.js';

const SIFRE = 'Guvenli-Sifre-9';
const KOD_DESENI = /^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/;
const kayitOl = (env, rumuz = 'Ayse_01', sifre = SIFRE, ek = {}, basliklar = {}) => cagir(env, 'POST', '/kayit', { govde: { rumuz, sifre, ...ek }, basliklar });
const satir = (env, sql, ...p) => env.DB.ham.prepare(sql).get(...p);
const simdi = () => Math.floor(Date.now() / 1000);

// ---------- kayıt ----------
test('kayıt: rumuz + şifre ile üyelik, oturum ve kurtarma kodu döner; tg_id boş, şifre özetlenmiş', async () => {
  const env = ortam();
  const r = await kayitOl(env);
  assert.equal(r.durum, 200);
  assert.equal(r.json.uye.rumuz, 'Ayse_01');
  assert.match(r.json.kurtarma_kodu, KOD_DESENI);
  assert.ok(await oturumUyeKimligi(env, r.json.oturum, simdi()) > 0);
  const s = satir(env, 'SELECT tg_id, sifre_ozet, kurtarma_ozet, google_sub, kurucu FROM uyeler WHERE rumuz = ?', 'Ayse_01');
  assert.equal(s.tg_id, null);
  assert.equal(s.kurucu, 1);
  assert.match(s.sifre_ozet, /^pbkdf2\$v1\$10000\$[A-Za-z0-9_-]{22}\$[A-Za-z0-9_-]{43}$/);
  assert.equal(satir(env, 'SELECT rumuz_kat, oturum_surum FROM uyeler WHERE rumuz = ?', 'Ayse_01').rumuz_kat, 'ayse01');
  assert.ok(!JSON.stringify(s).includes(SIFRE) && !s.kurtarma_ozet.includes(r.json.kurtarma_kodu.replace(/-/g, '')));
  const ben = (await cagir(env, 'GET', '/ben', { token: r.json.oturum })).json;
  assert.equal(ben.uye.telegram, false); assert.equal(ben.uye.sifre_var, true); assert.equal(ben.uye.google_var, false); assert.equal(ben.profil, null);
  assert.equal(JSON.stringify(ben).includes('pbkdf2'), false);
  // yeni üye forumda yazabilir
  const b = await cagir(env, 'POST', '/baslik', { token: r.json.oturum, govde: { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' } });
  assert.equal(b.durum, 201);
});

test('kayıt: aynı rumuz (büyük/küçük harf fark etmez) 409; geçersiz rumuz 400; yapılandırma yoksa 503', async () => {
  const env = ortam();
  assert.equal((await kayitOl(env)).durum, 200);
  assert.equal((await kayitOl(env, 'AYSE_01', 'Baska-Sifre-77')).durum, 409);
  assert.equal((await kayitOl(env, 'ab')).durum, 400);
  assert.equal((await kayitOl(env, 'Asistan_1')).durum, 400);
  assert.equal((await cagir(env, 'POST', '/kayit', { govde: 'x' })).durum, 400);
  const e2 = ortam({ OTURUM_SIRRI: undefined });
  assert.equal((await kayitOl(e2)).durum, 503);
});

test('kayıt: zayıf şifreler reddedilir', async () => {
  const env = ortam();
  for (const s of ['kisa', '12345678', 'PASSWORD', 'qwerty123', '11111111', 'aaaaaaaaaa', 'ayse_01x'.slice(0, 7), 'x'.repeat(73), '', null, 12345678]) {
    ipSinirSifirla();   // bellek içi ön süzgeç dakikada 10 kayıt izin verir; döngü bunu aşmasın
    const r = await kayitOl(env, 'Zayif_U', s);
    assert.equal(r.durum, 400, String(s));
    assert.ok(r.json.hata.length > 5);
  }
  assert.equal((await kayitOl(env, 'Ayse_01', 'ayse_01')).durum, 400);   // rumuzla aynı
  assert.equal((await kayitOl(env, 'Ayşe_01', 'AYŞE_01')).durum, 400);
  assert.equal(satir(env, "SELECT COUNT(*) AS n FROM uyeler WHERE rol = 'uye'").n, 0);
  assert.equal(sifreKurali('ab'.repeat(36), 'a'), null);
  assert.equal(sifreKurali('sekiz-kr', 'a'), null);
});

test('kayıt: IP başına saatte en çok 5 üyelik; başka IP etkilenmez, süre dolunca açılır', async () => {
  const env = ortam();
  const ip = { 'CF-Connecting-IP': '203.0.113.7' };
  for (let i = 0; i < 5; i++) assert.equal((await kayitOl(env, `Uye_${i}x`, SIFRE, {}, ip)).durum, 200);
  const r = await kayitOl(env, 'Uye_6x', SIFRE, {}, ip);
  assert.equal(r.durum, 429);
  assert.equal((await kayitOl(env, 'Uye_6x', SIFRE, {}, { 'CF-Connecting-IP': '203.0.113.8' })).durum, 200);
  env.DB.ham.prepare('UPDATE giris_denemeleri SET olusma = olusma - 3700').run();
  assert.equal((await kayitOl(env, 'Uye_7x', SIFRE, {}, ip)).durum, 200);
  assert.ok(!satir(env, 'SELECT anahtar FROM giris_denemeleri LIMIT 1').anahtar.includes('203.0.113'));   // ham IP saklanmaz
});

// ---------- giriş ----------
test('şifreyle giriş: doğru şifre oturum verir; yanlış şifre ve olmayan rumuz aynı genel hatayı alır', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const g = await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'ayse_01', sifre: SIFRE } });
  assert.equal(g.durum, 200);
  assert.equal(g.json.uye.id, k.json.uye.id);
  assert.equal(g.json.kurtarma_kodu, undefined);
  const yanlis = await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: 'Yanlis-Sifre-1' } });
  const yok = await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Olmayan_U', sifre: 'Yanlis-Sifre-1' } });
  assert.equal(yanlis.durum, 401); assert.equal(yok.durum, 401);
  assert.deepEqual(yanlis.json, yok.json);
  assert.equal(yanlis.json.hata, 'Rumuz ya da şifre hatalı.');
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01' } })).durum, 400);
  // Telegram'dan gelen şifresiz üye şifreyle giremez
  env.DB.ham.prepare("INSERT INTO uyeler (tg_id, rumuz, kayit) VALUES (77, 'Tg_Uye', 1)").run();
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Tg_Uye', sifre: SIFRE } })).json.hata, 'Rumuz ya da şifre hatalı.');
});

test('şifreyle giriş: rumuz+IP başına 10 başarısız deneme kilitler; başka IP kilitlenmez (kilitleme DoS\'u yok), yalnız rumuz için eşik 50', async () => {
  const env = ortam();
  await kayitOl(env);
  const ip = { 'CF-Connecting-IP': '198.51.100.7' };
  // büyük/küçük harf ve "." "_" farkı aynı sayaca düşer
  const adlar = ['Ayse_01', 'ayse_01', 'AYSE.01', 'ayse01', 'Ayse_01', 'ayse_01', 'AYSE.01', 'ayse01', 'Ayse_01', 'ayse_01'];
  for (let i = 0; i < 10; i++) assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: adlar[i], sifre: `Yanlis-${i}-abc` }, basliklar: ip })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE }, basliklar: ip })).durum, 429);
  // gerçek sahibi başka bir ağdan hâlâ girebilir
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE }, basliklar: { 'CF-Connecting-IP': '198.51.100.99' } })).durum, 200);
  env.DB.ham.prepare('UPDATE giris_denemeleri SET olusma = olusma - 1000').run();
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE }, basliklar: ip })).durum, 200);
  // yalnız rumuz sayacı: 50 farklı IP'den başarısız deneme sonrası doğru şifre de 429
  const env2 = ortam();
  await kayitOl(env2);
  env2.DB.ham.prepare("INSERT INTO giris_denemeleri (tur, anahtar, olusma) SELECT 'giris_rumuz', 'ayse01', ? FROM (WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 50) SELECT i FROM n)").run(simdi());
  assert.equal((await cagir(env2, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE }, basliklar: { 'CF-Connecting-IP': '203.0.113.5' } })).durum, 429);
});

test('şifreyle giriş: IP başına 15 dakikada 10 başarısız deneme (farklı rumuzlarla da) sonrası 429', async () => {
  const env = ortam();
  const ip = { 'CF-Connecting-IP': '192.0.2.50' };
  for (let i = 0; i < 10; i++) assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: `Rastgele_${i}`, sifre: 'Yanlis-Sifre-1' }, basliklar: ip })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Baska_Biri', sifre: 'Yanlis-Sifre-1' }, basliklar: ip })).durum, 429);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Baska_Biri', sifre: 'Yanlis-Sifre-1' }, basliklar: { 'CF-Connecting-IP': '192.0.2.51' } })).durum, 401);
});

// ---------- kurtarma kodu ----------
test('şifre sıfırlama: kurtarma koduyla yeni şifre; eski kod ve eski şifre artık işe yaramaz, yeni kod gelir', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const eskiKod = k.json.kurtarma_kodu;
  const sifirla = (kod, yeni = 'Yepyeni-Sifre-3', rumuz = 'Ayse_01') => cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz, kod, yeni_sifre: yeni } });
  const yanlis = await sifirla('AAAA-AAAA-AAAA');
  assert.equal(yanlis.durum, 401); assert.equal(yanlis.json.hata, 'Rumuz ya da kurtarma kodu hatalı.');
  assert.deepEqual((await sifirla(eskiKod, 'Yepyeni-Sifre-3', 'Olmayan_U')).json, yanlis.json);
  assert.equal((await sifirla(eskiKod, '12345678')).durum, 400);   // zayıf yeni şifre kodu harcamaz
  const r = await sifirla(eskiKod.toLowerCase().replace(/-/g, ' '));   // küçük harf ve boşluk serbest
  assert.equal(r.durum, 200);
  assert.match(r.json.kurtarma_kodu, KOD_DESENI);
  assert.notEqual(r.json.kurtarma_kodu, eskiKod);
  assert.ok(r.json.oturum);
  assert.equal((await sifirla(eskiKod)).durum, 401);   // eski kod bitti
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: 'Yepyeni-Sifre-3' } })).durum, 200);
  assert.equal((await sifirla(r.json.kurtarma_kodu, 'Bir-Baska-Sifre-4')).durum, 200);   // yeni kod geçerli
});

test('şifre sıfırlama: yanlış kod denemeleri sınırlanır', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  for (let i = 0; i < 10; i++) assert.equal((await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Ayse_01', kod: `AAAA-AAAA-AAA${i}`, yeni_sifre: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Ayse_01', kod: k.json.kurtarma_kodu, yeni_sifre: 'Yepyeni-Sifre-3' } })).durum, 429);
});

test('kurtarma kodu üretimi ve biçimi', () => {
  const k = kurtarmaKoduUret();
  assert.match(k, KOD_DESENI);
  assert.equal(new Set(Array.from({ length: 50 }, kurtarmaKoduUret)).size, 50);
  assert.equal(kurtarmaKoduSadelestir('ab1l-o0cd-efgh'), 'AB110 0CDEFGH'.replace(' ', ''));
  assert.equal(kurtarmaKoduBicimiGecerli(k.toLowerCase()), true);
  assert.equal(kurtarmaKoduBicimiGecerli('UUUU-UUUU-UUUU'), false);
});

test('şifre özeti: sürüm + tekrar sayısı özetin içinde, biberli, NFC, yanlış şifre ve bozuk özet reddedilir', async () => {
  const env = ortam();
  const o = await sifreOzetle(env, 'Sifrem-Cok-Iyi-1');
  assert.match(o, /^pbkdf2\$v1\$10000\$/);
  assert.ok(await sifreDogrula(env, 'Sifrem-Cok-Iyi-1', o));
  assert.equal(await sifreDogrula(env, 'Sifrem-Cok-Iyi-2', o), false);
  assert.equal(await sifreDogrula({ ...env, SIFRE_BIBERI: 'baska-biber' }, 'Sifrem-Cok-Iyi-1', o), false);   // biber değişirse özet geçersiz
  assert.equal(await sifreDogrula(env, 'x', null), false);
  assert.equal(await sifreDogrula(env, 'x', 'pbkdf2$abc$x$y'), false);
  assert.equal(await sifreDogrula(env, 'Sifrem-Cok-Iyi-1', o.replace('$v1$', '$v9$')), false);   // bilinmeyen biber sürümü
  const o2 = await sifreOzetle(env, 'Sifrem-Cok-Iyi-1', 1500);   // farklı tekrar sayısıyla yazılmış özet hâlâ doğrulanır
  assert.ok(o2.startsWith('pbkdf2$v1$1500$'));
  assert.ok(await sifreDogrula(env, 'Sifrem-Cok-Iyi-1', o2));
  // Unicode: "ş" bileşik ya da ayrık yazılsa da aynı şifre
  const bilesik = 'Şifrem-Güçlü-1'.normalize('NFC'), ayrik = bilesik.normalize('NFD');
  assert.notEqual(bilesik, ayrik);
  assert.ok(await sifreDogrula(env, ayrik, await sifreOzetle(env, bilesik)));
  assert.equal(sifreKurali(ayrik, 'x'), null);
  assert.equal(sifreKurali('e\u0301x'.repeat(30), 'x'), null);   // NFC sonrası 40 karakter (72 sınırı NFC üzerinden)
});

test('SIFRE_BIBERI yoksa şifre özellikleri kapalı (OTURUM_SIRRI\'na geri dönülmez): ayar sifre:false, uçlar 503, Telegram etkilenmez', async () => {
  const env = ortam({ SIFRE_BIBERI: undefined });
  assert.equal(sifreYapilandirildi({ OTURUM_SIRRI: 'x' }), false);
  assert.equal((await cagir(env, 'GET', '/giris/ayar')).json.sifre, false);
  assert.equal((await cagir(env, 'GET', '/durum')).json.giris.sifre, false);
  for (const [yol, govde] of [['/kayit', { rumuz: 'Ayse_01', sifre: SIFRE }], ['/giris/sifre', { rumuz: 'Ayse_01', sifre: SIFRE }], ['/sifre-sifirla', { rumuz: 'Ayse_01', kod: 'AAAA-AAAA-AAAA', yeni_sifre: SIFRE }]]) {
    const r = await cagir(env, 'POST', yol, { govde });
    assert.equal(r.durum, 503, yol); assert.match(r.json.hata, /kapalı/);
  }
  const u = await uyeGirisi(env, 'Tg_Kapali');
  for (const yol of ['/ben/sifre', '/ben/kurtarma-kodu']) assert.equal((await cagir(env, 'POST', yol, { token: u.token, govde: { yeni: SIFRE, sifre: SIFRE } })).durum, 503, yol);
  assert.equal((await cagir(env, 'GET', '/ben', { token: u.token })).durum, 200);
});

// ---------- şifre ve kod yönetimi ----------
test('/ben/sifre ve /ben/kurtarma-kodu: eski şifre gerekir; değişince eski oturumlar kapanır, istek taze jeton alır', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const token = k.json.oturum;
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { govde: { eski: SIFRE, yeni: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { eski: 'Yanlis-Sifre-1', yeni: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { yeni: 'Yepyeni-Sifre-3' } })).durum, 401);   // eski yoksa değiştirilemez
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { eski: SIFRE, yeni: '12345678' } })).durum, 400);
  const d = await cagir(env, 'POST', '/ben/sifre', { token, govde: { eski: SIFRE, yeni: 'Yepyeni-Sifre-3' } });
  assert.equal(d.durum, 200); assert.equal(d.json.kurtarma_kodu, undefined);
  assert.ok(d.json.oturum && d.json.oturum !== token);
  assert.equal((await cagir(env, 'GET', '/ben', { token })).durum, 401);   // eski oturum kapandı
  const yeniToken = d.json.oturum;
  assert.equal((await cagir(env, 'GET', '/ben', { token: yeniToken })).durum, 200);
  assert.equal(satir(env, 'SELECT oturum_surum FROM uyeler WHERE rumuz = ?', 'Ayse_01').oturum_surum, 1);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: 'Yepyeni-Sifre-3' } })).durum, 200);
  // kurtarma kodunu yenile
  assert.equal((await cagir(env, 'POST', '/ben/kurtarma-kodu', { token: yeniToken, govde: { sifre: SIFRE } })).durum, 401);   // eski şifre artık yanlış
  const y = await cagir(env, 'POST', '/ben/kurtarma-kodu', { token: yeniToken, govde: { sifre: 'Yepyeni-Sifre-3' } });
  assert.equal(y.durum, 200); assert.match(y.json.kurtarma_kodu, KOD_DESENI);
  assert.equal((await cagir(env, 'GET', '/ben', { token: yeniToken })).durum, 401);   // kod yenilenince de oturumlar kapanır
  assert.equal((await cagir(env, 'GET', '/ben', { token: y.json.oturum })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Ayse_01', kod: k.json.kurtarma_kodu, yeni_sifre: 'Bir-Baska-Sifre-4' } })).durum, 401);   // ilk kod bitti
  const s = await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Ayse_01', kod: y.json.kurtarma_kodu, yeni_sifre: 'Bir-Baska-Sifre-4' } });
  assert.equal(s.durum, 200);
  assert.equal((await cagir(env, 'GET', '/ben', { token: y.json.oturum })).durum, 401);   // sıfırlama da oturumları kapatır
  assert.equal((await cagir(env, 'GET', '/ben', { token: s.json.oturum })).durum, 200);
  assert.equal((await cagir(env, 'GET', '/ben', { token: s.json.oturum })).json.uye.rumuz, 'Ayse_01');
});

test('Telegram üyesi şifre ekleyebilir: eski gerekmez, kurtarma kodu bir kez verilir, sonra eski gerekir', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Tg_Ekle');   // yerel deneme girişi: tg_id < 0
  const token = u.token;
  assert.equal((await cagir(env, 'POST', '/ben/kurtarma-kodu', { token, govde: { sifre: 'x' } })).durum, 400);   // şifresizken kod yenilenemez
  const r = await cagir(env, 'POST', '/ben/sifre', { token, govde: { yeni: SIFRE } });
  assert.equal(r.durum, 200); assert.match(r.json.kurtarma_kodu, KOD_DESENI);
  const yt = r.json.oturum;
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Tg_Ekle', sifre: SIFRE } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token: yt, govde: { yeni: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'GET', '/ben', { token: yt })).json.uye.sifre_var, true);
});

// ---------- Turnstile ve genel ayar ----------
test('Turnstile: gizli anahtar varsa /kayit jeton ister, siteverify ile doğrular ve hostname\'i kontrol eder; yoksa atlanır', async () => {
  const env = ortam({ TURNSTILE_GIZLI: 'gizli', TURNSTILE_SITE: 'site-anahtari' });
  const ayar = await cagir(env, 'GET', '/giris/ayar');
  assert.equal(ayar.json.turnstile_site, 'site-anahtari'); assert.equal(ayar.json.google_istemci, ''); assert.equal(ayar.json.sifre, true);
  assert.equal((await cagir(env, 'GET', '/durum')).json.giris.turnstile_site, 'site-anahtari');
  assert.equal((await cagir(ortam(), 'GET', '/giris/ayar')).json.turnstile_site, '');
  const yanit = (govde) => async (url, s) => new Response(JSON.stringify(govde(String(s.body))), { status: 200 });
  const f = sahteFetch(yanit((b) => ({ success: b.includes('response=iyi'), hostname: 'kpsstercihi.com' })));
  try {
    assert.equal((await kayitOl(env)).durum, 400);
    assert.equal(f.cagrilar.length, 0);   // jeton yoksa dış istek yapılmaz
    assert.equal((await kayitOl(env, 'Ayse_01', SIFRE, { turnstile: 'kotu' })).durum, 400);
    assert.equal((await kayitOl(env, 'Ayse_01', SIFRE, { turnstile: 'iyi' })).durum, 200);
    assert.equal(f.cagrilar[0].url, 'https://challenges.cloudflare.com/turnstile/v0/siteverify');
    assert.ok(String(f.cagrilar[0].secenek.body).includes('secret=gizli'));
  } finally { f.geri(); }
  for (const [host, beklenen] of [['www.kpsstercihi.com', 200], ['baska-site.example.net', 400], [undefined, 400]]) {
    const g = sahteFetch(yanit(() => ({ success: true, hostname: host })));
    try { assert.equal((await kayitOl(env, `Host_${beklenen}_${String(host).length}`, SIFRE, { turnstile: 'iyi' })).durum, beklenen, String(host)); } finally { g.geri(); }
  }
  const yerel = ortam({ TURNSTILE_GIZLI: 'gizli', ORTAM: 'yerel' });
  const h = sahteFetch(yanit(() => ({ success: true, hostname: 'localhost' })));
  try { assert.equal((await kayitOl(yerel, 'Yerel_U', SIFRE, { turnstile: 'iyi' })).durum, 200); } finally { h.geri(); }
  const h2 = sahteFetch(yanit(() => ({ success: true, hostname: 'localhost' })));
  try { assert.equal((await kayitOl(env, 'Yerel_V', SIFRE, { turnstile: 'iyi' })).durum, 400); } finally { h2.geri(); }   // üretimde localhost kabul edilmez
  const f2 = sahteFetch(async () => { throw new Error('ağ'); });
  try { assert.equal((await kayitOl(env, 'Baska_Uye', SIFRE, { turnstile: 'iyi' })).durum, 400); } finally { f2.geri(); }
  assert.equal((await kayitOl(ortam(), 'Ayse_01')).durum, 200);   // yapılandırılmamışsa jeton aranmaz
});
// ---------- Google ----------
const GOOGLE_ISTEMCI = '1234567890-abc.apps.googleusercontent.com';
async function anahtarCifti() {
  const c = await crypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
  return { ozel: c.privateKey, jwk: { ...(await crypto.subtle.exportKey('jwk', c.publicKey)), kid: 'anahtar-1', use: 'sig', alg: 'RS256' } };
}
async function googleJetonu(ozel, yuk = {}, baslik = {}) {
  const t = simdi();
  const b = metinB64u(JSON.stringify({ alg: 'RS256', kid: 'anahtar-1', typ: 'JWT', ...baslik }));
  const p = metinB64u(JSON.stringify({ iss: 'https://accounts.google.com', aud: GOOGLE_ISTEMCI, sub: '110169484474386276334', email_verified: true, iat: t, exp: t + 3600, email: 'x@gmail.com', ...yuk }));
  const imza = new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', ozel, new TextEncoder().encode(`${b}.${p}`)));
  return `${b}.${p}.${b64uKodla(imza)}`;
}
const jwksFetch = (jwk, sayac = { n: 0 }) => sahteFetch(async (url) => {
  if (url !== 'https://www.googleapis.com/oauth2/v3/certs') return new Response('yok', { status: 404 });
  sayac.n++;
  return new Response(JSON.stringify({ keys: [jwk] }), { status: 200, headers: { 'Cache-Control': 'public, max-age=22000, must-revalidate' } });
});

test('Google jeton doğrulama: geçerli jeton kabul; yanlış aud/iss, süresi dolmuş, doğrulanmamış e-posta, başka anahtar, alg değişimi reddedilir', async () => {
  googleAnahtarOnbellegiTemizle();
  const env = ortam({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const { ozel, jwk } = await anahtarCifti();
  const sayac = { n: 0 };
  const f = jwksFetch(jwk, sayac);
  try {
    const dogrula = (j, e = env) => googleJetonuDogrula(e, j, simdi());
    const iyi = await dogrula(await googleJetonu(ozel));
    assert.deepEqual(iyi, { tamam: true, sub: '110169484474386276334', eposta: 'x@gmail.com' });
    assert.equal((await dogrula(await googleJetonu(ozel, { iss: 'accounts.google.com' }))).tamam, true);
    assert.equal(sayac.n, 1);   // anahtarlar önbellekten gelir
    assert.equal((await dogrula(await googleJetonu(ozel, { aud: 'baska.apps.googleusercontent.com' }))).neden, 'aud');
    assert.equal((await dogrula(await googleJetonu(ozel, { iss: 'https://evil.example.com' }))).neden, 'iss');
    assert.equal((await dogrula(await googleJetonu(ozel, { iat: simdi() - 7200, exp: simdi() - 3600 }))).neden, 'eski');
    assert.equal((await dogrula(await googleJetonu(ozel, { iat: simdi() - 7200, exp: simdi() - 100 }))).tamam, true);   // 5 dk sapma toleransı
    assert.equal((await dogrula(await googleJetonu(ozel, { iat: simdi() + 3600, exp: simdi() + 7200 }))).neden, 'gelecek');
    assert.equal((await dogrula(await googleJetonu(ozel, { email_verified: false }))).neden, 'eposta');
    assert.equal((await dogrula(await googleJetonu(ozel, { sub: undefined }))).neden, 'sub');
    assert.equal((await dogrula(await googleJetonu(ozel, {}, { alg: 'HS256' }))).neden, 'alg');
    assert.equal((await dogrula(await googleJetonu(ozel, {}, { alg: 'none' }))).tamam, false);
    const baska = await anahtarCifti();
    assert.equal((await dogrula(await googleJetonu(baska.ozel))).neden, 'imza');   // kid aynı, imza başka anahtardan
    const iyiJeton = await googleJetonu(ozel);
    const [b, p, s] = iyiJeton.split('.');
    const kurcali = metinB64u(JSON.stringify({ ...JSON.parse(Buffer.from(p, 'base64url').toString()), sub: '999' }));
    assert.equal((await dogrula(`${b}.${kurcali}.${s}`)).neden, 'imza');
    assert.equal((await dogrula('a.b')).neden, 'bicim');
    assert.equal((await dogrula(null)).tamam, false);
    assert.equal((await dogrula(iyiJeton, ortam())).neden, 'yapilandirma');
    assert.equal((await dogrula(await googleJetonu(ozel, {}, { kid: 'yeni-anahtar' }))).tamam, false);   // bilinmeyen kid: anahtarlar bir kez yenilenir
    assert.ok(sayac.n <= 2);
  } finally { f.geri(); googleAnahtarOnbellegiTemizle(); }
});

test('Google JWKS: bilinmeyen kid için zorla yenileme dakikada en çok bir kez', async () => {
  googleAnahtarOnbellegiTemizle();
  const env = ortam({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const { ozel, jwk } = await anahtarCifti();
  const sayac = { n: 0 };
  const f = jwksFetch(jwk, sayac);
  try {
    assert.equal((await googleJetonuDogrula(env, await googleJetonu(ozel), simdi())).tamam, true);   // ilk çekim
    for (let i = 0; i < 5; i++) assert.equal((await googleJetonuDogrula(env, await googleJetonu(ozel, {}, { kid: `sahte-${i}` }), simdi())).tamam, false);
    assert.equal(sayac.n, 2);   // ilk çekim + tek zorla yenileme; 4 sahte kid daha Google'a gitmedi
  } finally { f.geri(); googleAnahtarOnbellegiTemizle(); }
});
test('POST /giris/google: yeni üye rumuz seçer, sonraki girişte doğrudan oturum; kapalıysa 404; e-posta saklanmaz', async () => {
  googleAnahtarOnbellegiTemizle();
  const env = ortam({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const { ozel, jwk } = await anahtarCifti();
  const f = jwksFetch(jwk);
  try {
    assert.equal((await cagir(ortam(), 'POST', '/giris/google', { govde: { kimlik_jetonu: await googleJetonu(ozel) } })).durum, 404);
    assert.equal((await cagir(env, 'POST', '/giris/google', { govde: { kimlik_jetonu: 'bozuk' } })).durum, 401);
    assert.equal((await cagir(env, 'POST', '/giris/google', { govde: { kimlik_jetonu: await googleJetonu(ozel, { aud: 'x' }) } })).durum, 401);
    assert.equal((await cagir(env, 'GET', '/giris/ayar')).json.google_istemci, GOOGLE_ISTEMCI);
    const g1 = await cagir(env, 'POST', '/giris/google', { govde: { kimlik_jetonu: await googleJetonu(ozel) } });
    assert.equal(g1.durum, 200); assert.equal(g1.json.yeni, true); assert.ok(g1.json.gecici); assert.equal(g1.json.oturum, undefined);
    // geçici jeton oturum olarak kullanılamaz
    assert.equal((await cagir(env, 'GET', '/ben', { token: g1.json.gecici })).durum, 401);
    assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g1.json.gecici, rumuz: 'ab' } })).durum, 400);
    const r = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g1.json.gecici, rumuz: 'Google_Uye' } });
    assert.equal(r.durum, 200); assert.equal(r.json.uye.rumuz, 'Google_Uye');
    const s = satir(env, 'SELECT * FROM uyeler WHERE rumuz = ?', 'Google_Uye');
    assert.equal(s.google_sub, '110169484474386276334'); assert.equal(s.tg_id, null);
    assert.equal(s.eposta, 'x@gmail.com'); assert.ok(s.eposta_dogrulandi > 0);   // Google'ın doğrulanmış adresi hesaba yazılır (sonradan e-posta koduyla girmek için)
    const g2 =await cagir(env, 'POST', '/giris/google', { govde: { kimlik_jetonu: await googleJetonu(ozel) } });
    assert.equal(g2.durum, 200); assert.equal(g2.json.uye.id, r.json.uye.id); assert.ok(g2.json.oturum);
    const ben = await cagir(env, 'GET', '/ben', { token: g2.json.oturum });
    assert.equal(ben.json.uye.google_var, true); assert.equal(ben.json.uye.telegram, false);
    assert.equal(ben.json.uye.eposta, 'x***@gmail.com'); assert.equal(JSON.stringify(ben.json).includes('x@gmail.com'), false);   // tam adres hiçbir yanıtta dönmez
    // aynı geçici jetonla ikinci üyelik açılmaz; var olan üyenin oturumu döner
    const r2 = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g1.json.gecici, rumuz: 'Baska_Rumuz' } });
    assert.equal(r2.json.uye.id, r.json.uye.id);
  } finally { f.geri(); googleAnahtarOnbellegiTemizle(); }
});

test('geçici jetonlar birbirine ve oturum jetonuna karıştırılamaz', async () => {
  const env = ortam();
  const t = simdi();
  const tg = await geciciUret(env, 55, t);
  const gg = await geciciGoogleUret(env, '12345', t);
  const ot = await oturumUret(env, 9, t);
  assert.equal(await geciciTgKimligi(env, tg, t), 55);
  assert.equal(await geciciGoogleKimligi(env, gg, t), '12345');
  assert.equal(await geciciTgKimligi(env, gg, t), null);
  assert.equal(await geciciGoogleKimligi(env, tg, t), null);
  assert.equal(await geciciGoogleKimligi(env, ot, t), null);
  assert.equal(await geciciTgKimligi(env, ot, t), null);
  for (const j of [tg, gg]) assert.equal(await oturumUyeKimligi(env, j, t), null);
  assert.equal(await oturumUyeKimligi(env, ot, t), 9);
  assert.equal(await geciciGoogleKimligi(env, gg, t + 901), null);
  // alanları karışık imzalı jetonlar da reddedilir
  const { jetonImzala } = await import('../src/oturum.js');
  const karisik = await jetonImzala(env, { u: 3, g: '1', s: t + 100 });
  assert.equal(await oturumUyeKimligi(env, karisik, t), null);
  assert.equal(await geciciGoogleKimligi(env, await jetonImzala(env, { g: '1', t: 5, s: t + 100 }), t), null);
  assert.equal(await geciciTgKimligi(env, await jetonImzala(env, { t: 5, g: '1', s: t + 100 }), t), null);
  assert.equal(await geciciGoogleKimligi(env, await jetonImzala(env, { g: 'abc', s: t + 100 }), t), null);
  // uçta: Telegram geçici jetonu Telegram yolunda, Google jetonu Google yolunda çalışır; sahte jeton 401
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: ot, rumuz: 'Sahte_Jeton' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: tg, rumuz: 'Tg_Yeni_U' } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: gg, rumuz: 'Gg_Yeni_U' } })).durum, 200);
  assert.equal(satir(env, 'SELECT tg_id FROM uyeler WHERE rumuz = ?', 'Tg_Yeni_U').tg_id, 55);
});

test('Telegram girişi hâlâ çalışır (yeni üye + mevcut üye)', async () => {
  const env = ortam();
  const alan = { id: 4242, first_name: 'Ali', auth_date: simdi() };
  alan.hash = await telegramImzala(env.TELEGRAM_BOT_TOKEN, alan);
  const g = await cagir(env, 'POST', '/giris/telegram', { govde: alan });
  assert.equal(g.json.yeni, true);
  const r = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g.json.gecici, rumuz: 'Tg_Giris' } });
  assert.equal(r.durum, 200);
  const g2 = await cagir(env, 'POST', '/giris/telegram', { govde: alan });
  assert.equal(g2.json.uye.rumuz, 'Tg_Giris');
  assert.equal((await cagir(env, 'GET', '/ben', { token: r.json.oturum })).json.uye.telegram, true);
});

// ---------- tg_id olmayan üyeler ----------
test('tg_id olmayan üyeler bildirim yollarında hata vermez ve Telegram\'a istek gitmez', async () => {
  const env = ortam();
  const a = await kayitOl(env, 'Sifreli_A');
  const b = await uyeGirisi(env, 'Deneme_B');
  kayitEskit(env, a.json.uye.id); kayitEskit(env, b.id);
  const f = sahteFetch(async () => new Response('{"ok":true}'));
  try {
    const bas = await cagir(env, 'POST', '/baslik', { token: a.json.oturum, govde: { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' } });
    assert.equal(bas.durum, 201);
    const id = bas.json.baslik.id;
    assert.ok(id);
    assert.equal((await cagir(env, 'POST', '/ben/bildirim', { token: a.json.oturum, govde: { acik: true } })).durum, 200);
    assert.equal((await cagir(env, 'POST', `/baslik/${id}/takip`, { token: a.json.oturum, govde: { takip: true } })).durum, 200);
    const y = await cagir(env, 'POST', `/baslik/${id}/yanit`, { token: b.token, govde: { govde: 'Merhaba @Sifreli_A, bence önce kadro sayısına bak.' } });
    assert.equal(y.durum, 201);
    const dm = await cagir(env, 'POST', '/ozel/Sifreli_A', { token: b.token, govde: { govde: 'Selam, bir sorum var.' } });
    assert.equal(dm.durum, 201);
    assert.equal(f.cagrilar.filter((c) => c.url.startsWith('https://api.telegram.org/')).length, 0);
  } finally { f.geri(); }
});

// ---------- profil ----------
const PROFIL = { v: 1, ogrenim: 'lisans', puan_turu: 'P3', iller: ['Ankara', 'İstanbul'], tum_turkiye: false, bolum: 'Bilgisayar Mühendisliği', t: '2026-11-01', puan: 78.5 };

test('profil: /ben/profil kaydeder, /ben döner; beyaz liste dışı alanlar atılır, geçersiz profil 400', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const token = k.json.oturum;
  assert.equal((await cagir(env, 'POST', '/ben/profil', { govde: { profil: PROFIL } })).durum, 401);
  const r = await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { ...PROFIL, ek: 'x', __proto__: { a: 1 }, email: 'a@b.c' } } });
  assert.equal(r.durum, 200);
  assert.deepEqual(r.json.profil, PROFIL);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token })).json.profil, PROFIL);
  assert.equal(JSON.stringify(satir(env, 'SELECT profil FROM uyeler WHERE id = ?', k.json.uye.id)).includes('a@b.c'), false);
  for (const kotu of [{ ...PROFIL, ogrenim: 'doktora' }, { ...PROFIL, v: 2 }, 'metin', [1], 5, undefined]) {
    assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: kotu } })).durum, 400, JSON.stringify(kotu));
  }
  assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { ...PROFIL, iller: Array.from({ length: 5000 }, () => 'Ankara') } } })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: {} })).durum, 400);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token })).json.profil, PROFIL);   // bozuk istekler eskisini bozmadı
  ipSinirSifirla();   // üye başına dakikada 10 kayıt sınırı bellek içidir
  const atla = await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { v: 1, atlandi: true, t: '2026-11-02' } } });
  assert.deepEqual(atla.json.profil, { v: 1, atlandi: true, t: '2026-11-02' });
  assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: null } })).durum, 200);
  assert.equal((await cagir(env, 'GET', '/ben', { token })).json.profil, null);
});

test('profil: değişmediyse UPDATE yapılmaz, iller tekrarsız, üye başına dakikada 10 kayıt', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const token = k.json.oturum;
  const degisiklik = () => env.DB.ham.prepare('SELECT total_changes() AS n').get().n;
  const r1 = await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { ...PROFIL, iller: ['Ankara', 'Ankara', 'İzmir', 'Ankara'] } } });
  assert.deepEqual(r1.json.profil.iller, ['Ankara', 'İzmir']);
  const once = degisiklik();
  const r2 = await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { ...PROFIL, iller: ['Ankara', 'İzmir'] } } });
  assert.equal(r2.durum, 200);
  assert.equal(degisiklik(), once);   // aynı profil: satır değişmedi
  await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { ...PROFIL, bolum: 'Başka' } } });
  assert.equal(degisiklik(), once + 1);
  for (let i = 0; i < 7; i++) assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: PROFIL } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: PROFIL } })).durum, 429);   // 11. istek
  assert.equal((await cagir(env, 'GET', '/ben', { token })).durum, 200);
});

// ---------- kayıtlı ilanlar ----------
const U1 = '9c82aab5-022e-43c8-b7f1-e6cf329d205b', U2 = '11111111-2222-4333-8444-555555555555', SBB = `sbb-${'a1b2c3d4e5f6'.repeat(2)}`, CSB = 'csb-12345';

test('kayıtlı: /ben/kayitli kaydeder, /ben döner; tekrar ve geçersiz kimlikler atılır, bozuk istek 400', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const token = k.json.oturum;
  assert.equal((await cagir(env, 'POST', '/ben/kayitli', { govde: { kayitli: [U1] } })).durum, 401);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token })).json.kayitli, []);
  const r = await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [U1, SBB, U1, 'x'.repeat(40), '<script>', 5, CSB] } });
  assert.equal(r.durum, 200);
  assert.deepEqual(r.json.kayitli, [U1, SBB, CSB]);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token })).json.kayitli, [U1, SBB, CSB]);
  for (const kotu of ['metin', 5, null, { a: 1 }, undefined]) {
    assert.equal((await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: kotu } })).durum, 400, JSON.stringify(kotu));
  }
  assert.equal((await cagir(env, 'POST', '/ben/kayitli', { token, govde: {} })).durum, 400);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token })).json.kayitli, [U1, SBB, CSB]);   // bozuk istekler eskisini bozmadı
  const bos = await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [] } });
  assert.deepEqual(bos.json.kayitli, []);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token })).json.kayitli, []);
});

test('kayıtlı: 300 kimlik sınırı, değişmediyse UPDATE yapılmaz, üye başına dakikada 10 kayıt', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const token = k.json.oturum;
  const degisiklik = () => env.DB.ham.prepare('SELECT total_changes() AS n').get().n;
  const uuid = (i) => `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`;
  const tam = Array.from({ length: 300 }, (_, i) => uuid(i));
  assert.equal((await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: tam } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [...tam, uuid(300)] } })).durum, 400);   // 301
  assert.equal((await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: Array.from({ length: 5000 }, (_, i) => uuid(i)) } })).durum, 400);
  assert.equal((await cagir(env, 'GET', '/ben', { token })).json.kayitli.length, 300);
  const once = degisiklik();
  assert.equal((await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: tam } })).durum, 200);
  assert.equal(degisiklik(), once);   // aynı liste: satır değişmedi
  await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [U1] } });
  assert.equal(degisiklik(), once + 1);
  await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [] } });
  const bosSonrasi = degisiklik();
  await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [] } });
  assert.equal(degisiklik(), bosSonrasi);   // zaten boşken boş liste yazmaz
  ipSinirSifirla();
  let ok = 0, ret = 0;
  for (let i = 0; i < 12; i++) { const d = (await cagir(env, 'POST', '/ben/kayitli', { token, govde: { kayitli: [i % 2 ? U1 : U2] } })).durum; if (d === 200) ok++; else if (d === 429) ret++; }
  assert.equal(ok, 10); assert.equal(ret, 2);
});

test('kayıtlı: bir üyenin listesi ötekine görünmez', async () => {
  const env = ortam();
  const a = await uyeGirisi(env, 'Kayitli_A'), b = await uyeGirisi(env, 'Kayitli_B');
  await cagir(env, 'POST', '/ben/kayitli', { token: a.token, govde: { kayitli: [U1] } });
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token: b.token })).json.kayitli, []);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token: a.token })).json.kayitli, [U1]);
});

test('kayitliTemizle: kimlik deseni, tekrar, 300 ve 8 KB sınırı', () => {
  assert.deepEqual(kayitliTemizle([U1, U1, CSB, 'csb-12', 'sbb-zz']), [U1, CSB]);
  assert.equal(kayitliTemizle('x'), null);
  assert.equal(kayitliTemizle(Array.from({ length: 301 }, (_, i) => `csb-${100000 + i}`)), null);
  assert.equal(kayitliTemizle(Array.from({ length: 300 }, (_, i) => `csb-${100000 + i}`)).length, 300);
  assert.deepEqual(kayitliOku('bozuk{'), []);
  assert.deepEqual(kayitliOku(null), []);
  assert.deepEqual(kayitliOku(JSON.stringify([U1])), [U1]);
});

// ---------- Türkçe harfe duyarsız benzersiz rumuz ----------
const KAT_ORNEKLERI = ['Çağlar', 'ÇAĞLAR', 'caglar', 'Şükrü.1', 'sukru_1', 'İREM', 'Irmak', 'ırmak', 'IRMAK', 'iremi', 'ışık_x', 'IŞIK.X', 'ÖMER', 'ömer', 'Ümit', 'umit', 'Gül_Şen', 'GUL.SEN', 'ali.veli', 'Ali_Veli', 'ALİ', 'ali', 'Ağrı35', 'agri35', 'ÜÇ_ÖĞ', 'uc.og', 'Ab.c_d1'];
test('rumuz_kat: JS rumuzKat ile migration SQL aynı sonucu verir', async () => {
  const { DatabaseSync } = await import('node:sqlite');
  const { readFileSync } = await import('node:fs');
  const dosya = (y) => readFileSync(new URL(y, import.meta.url), 'utf8');
  const db = new DatabaseSync(':memory:');
  db.exec(dosya('./eski-schema.sql'));
  for (const m of ['0002_ozellikler', '0003_odalar', '0004_ozel_takip']) db.exec(dosya(`../migrations/${m}.sql`));
  const tekil = new Map(); const cakisanlar = new Set();
  for (const r of KAT_ORNEKLERI) { const k = rumuzKat(r); if (tekil.has(k)) cakisanlar.add(r); else tekil.set(k, r); }
  assert.ok(cakisanlar.size > 5);
  const ekle2 = db.prepare('INSERT INTO uyeler (tg_id, rumuz, kayit) VALUES (?, ?, 1)');
  [...tekil.values()].forEach((r, i) => ekle2.run(2000 + i, r));
  db.exec(dosya('../migrations/0005_kayit.sql'));
  for (const s of db.prepare('SELECT rumuz, rumuz_kat FROM uyeler').all()) assert.equal(s.rumuz_kat, rumuzKat(s.rumuz), s.rumuz);
  // taze şemadaki indeks gerçekten çakışmayı engeller
  const taze = new DatabaseSync(':memory:'); taze.exec(dosya('../schema.sql'));
  taze.prepare("INSERT INTO uyeler (rumuz, rumuz_kat) VALUES ('Ayşe_1', ?)").run(rumuzKat('Ayşe_1'));
  assert.throws(() => taze.prepare("INSERT INTO uyeler (rumuz, rumuz_kat) VALUES ('AYSE.1', ?)").run(rumuzKat('AYSE.1')), /UNIQUE/);
  assert.equal(rumuzKat('İREM'), rumuzKat('irem')); assert.equal(rumuzKat('Irmak'), rumuzKat('ırmak'));
});

test('kayıt: Türkçe harf, büyük/küçük harf, "." ve "_" farkıyla aynı rumuz alınamaz (tüm giriş yollarında)', async () => {
  const env = ortam();
  assert.equal((await kayitOl(env, 'Çağlar_Ş')).durum, 200);
  for (const r of ['CAGLAR_S', 'çağlar.ş', 'ÇAĞLARŞ', 'caglar_s']) { ipSinirSifirla(); assert.equal((await kayitOl(env, r)).durum, 409, r); }
  assert.equal(satir(env, 'SELECT rumuz_kat FROM uyeler WHERE rumuz = ?', 'Çağlar_Ş').rumuz_kat, 'caglars');
  // deneme girişi (yerel) ve Telegram geçici jetonu da aynı denetimden geçer
  assert.equal((await cagir({ ...env, ORTAM: 'yerel' }, 'POST', '/giris/deneme', { govde: { rumuz: 'CAGLAR.S' } })).durum, 409);
  const tg = await geciciUret(env, 99, simdi());
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: tg, rumuz: 'caglar_ş' } })).durum, 409);
  const gg = await geciciGoogleUret(env, '555', simdi());
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: gg, rumuz: 'ÇAĞLAR.Ş' } })).durum, 409);
  // giriş ve sıfırlama farklı yazımla da çalışır; kod sıfırlama aynı hesaba gider
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'caglar.s', sifre: SIFRE } })).durum, 200);
  // NFC: ayrık (NFD) yazılmış rumuz aynı hesaba çözülür
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Çağlar_Ş'.normalize('NFD'), sifre: SIFRE } })).durum, 200);
  env.DB.ham.prepare('DELETE FROM giris_denemeleri').run();
  const nfd = await kayitOl(env, 'Şule_Ç'.normalize('NFD'));
  assert.equal(nfd.durum, 200); assert.equal(nfd.json.uye.rumuz, 'Şule_Ç'.normalize('NFC'));
});

test('uyeOlustur: yalnız UNIQUE hatası 409 olur, başka D1 hatası 500 + günlük', async () => {
  const env = ortam();
  const gercek = env.DB.prepare.bind(env.DB);
  const gunluk = []; const eskiLog = console.error; console.error = (...a) => gunluk.push(a.join(' '));
  try {
    env.DB.prepare = (sql) => {
      if (/^INSERT INTO uyeler/.test(sql)) return { bind() { return this; }, async run() { throw new Error('D1_ERROR: database is locked'); } };
      return gercek(sql);
    };
    const r = await kayitOl(env, 'Hata_U');
    assert.equal(r.durum, 500);
    assert.ok(gunluk.some((s) => /database is locked/.test(s)));
    env.DB.prepare = (sql) => {
      if (/^INSERT INTO uyeler/.test(sql)) return { bind() { return this; }, async run() { throw new Error('D1_ERROR: UNIQUE constraint failed: uyeler.rumuz_kat'); } };
      return gercek(sql);
    };
    ipSinirSifirla();
    assert.equal((await kayitOl(env, 'Hata_V')).durum, 409);
  } finally { console.error = eskiLog; }
});

// ---------- IP anahtarı, ön süzgeç, temizlik ----------
test('IP anahtarı: IPv6 /64 ile, X-Forwarded-For yok sayılır, başlık yoksa tek "yok" kovası', async () => {
  assert.equal(ipOnEki('2001:db8:1:2:aaaa:bbbb:cccc:dddd'), ipOnEki('2001:0db8:0001:0002::1'));
  assert.notEqual(ipOnEki('2001:db8:1:2::1'), ipOnEki('2001:db8:1:3::1'));
  assert.equal(ipOnEki('2001:db8::5'), 'v6:2001:db8:0:0');
  assert.equal(ipOnEki('::ffff:192.0.2.9'), ipOnEki('192.0.2.9'));
  assert.equal(ipOnEki(null), 'yok'); assert.equal(ipOnEki(''), 'yok');
  const ist = (h) => ipAnahtari(new Request('https://x/', { headers: h }));
  assert.equal(await ist({ 'CF-Connecting-IP': '2001:db8:1:2:1:2:3:4' }), await ist({ 'CF-Connecting-IP': '2001:db8:1:2:ffff::9' }));
  assert.equal(await ist({ 'X-Forwarded-For': '1.2.3.4' }), await ist({ 'X-Forwarded-For': '5.6.7.8' }));   // sahte başlıkla kova değişmez
  assert.equal(await ist({}), await ist({ 'X-Forwarded-For': '9.9.9.9' }));
  assert.notEqual(await ist({ 'CF-Connecting-IP': '192.0.2.1' }), await ist({}));
  // /64 içinden değişen adreslerle sınır aşılamaz
  const env = ortam();
  for (let i = 0; i < 5; i++) assert.equal((await kayitOl(env, `V6_${i}x`, SIFRE, {}, { 'CF-Connecting-IP': `2001:db8:5:5::${i + 1}` })).durum, 200);
  assert.equal((await kayitOl(env, 'V6_son', SIFRE, {}, { 'CF-Connecting-IP': '2001:db8:5:5:aaaa::1' })).durum, 429);
});

test('bellek içi ön süzgeç D1 yazmasından önce çalışır (kayıt, giriş, sıfırlama, Google, şifre, profil uçları)', async () => {
  const env = ortam({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const u = await uyeGirisi(env, 'Sinir_U');
  const yaz = () => env.DB.ham.prepare('SELECT COUNT(*) AS n FROM giris_denemeleri').get().n;
  const durumlar = {};
  const uclar = [['/kayit', { rumuz: 'ab', sifre: 'x' }, 10], ['/giris/sifre', { rumuz: 'Yok_Biri', sifre: 'yanlis-sifre-1' }, 20],
    ['/sifre-sifirla', { rumuz: 'Yok_Biri', kod: 'AAAA-AAAA-AAAA', yeni_sifre: SIFRE }, 10], ['/giris/google', { kimlik_jetonu: 'x' }, 20],
    ['/ben/sifre', { eski: 'x', yeni: SIFRE }, 10], ['/ben/kurtarma-kodu', { sifre: 'x' }, 10], ['/ben/profil', { profil: null }, 30], ['/ben/kayitli', { kayitli: [] }, 30]];
  for (const [yol, govde, limit] of uclar) {
    ipSinirSifirla();
    let son;
    for (let i = 0; i < limit + 1; i++) son = await cagir(env, 'POST', yol, { govde, token: u.token });
    durumlar[yol] = son.durum;
    const once = yaz();
    const bir = await cagir(env, 'POST', yol, { govde, token: u.token });
    assert.equal(bir.durum, 429, yol);
    assert.equal(yaz(), once, `${yol}: sınır aşıldıktan sonra D1'e yazılmamalı`);
  }
  assert.ok(Object.values(durumlar).every((d) => d === 429));
});

test('giris_denemeleri: fırsat temizliği eski satırları siler, taze satırları korur', async () => {
  const env = ortam();
  const t = simdi();
  env.DB.ham.prepare("INSERT INTO giris_denemeleri (tur, anahtar, olusma) VALUES ('kayit', 'a', ?), ('kayit', 'b', ?), ('giris_ip', 'c', ?)").run(t - 7200, t - 5000, t - 10);
  await denemeTemizle(env, t);
  assert.deepEqual(env.DB.ham.prepare('SELECT anahtar FROM giris_denemeleri').all().map((r) => r.anahtar), ['c']);
  env.DB.ham.prepare("INSERT INTO giris_denemeleri (tur, anahtar, olusma) VALUES ('kayit', 'eski', ?)").run(t - 9000);
  await denemeYaz(env, KAYIT_SINIRI, 'yeni', t, 0);   // rastgele < 0.01: temizlik tetiklenir
  assert.deepEqual(env.DB.ham.prepare('SELECT anahtar FROM giris_denemeleri ORDER BY anahtar').all().map((r) => r.anahtar), ['c', 'yeni']);
});

test('kayıt: rumuz uygunluğu ve sayaç özetlemeden önce; başarısız (alınmış rumuz) denemeler de IP sınırına işler', async () => {
  const env = ortam();
  const ip = { 'CF-Connecting-IP': '203.0.113.77' };
  assert.equal((await kayitOl(env, 'Ayse_01', SIFRE, {}, ip)).durum, 200);
  for (let i = 0; i < 4; i++) assert.equal((await kayitOl(env, 'ayse.01', SIFRE, {}, ip)).durum, 409);
  assert.equal(satir(env, "SELECT COUNT(*) AS n FROM giris_denemeleri WHERE tur = 'kayit'").n, 5);
  assert.equal((await kayitOl(env, 'Bambaska_U', SIFRE, {}, ip)).durum, 429);
  // geçersiz rumuz / zayıf şifre D1'e yazmaz (yalnız özetleme öncesi sayaç)
  const env2 = ortam();
  await kayitOl(env2, 'ab'); await kayitOl(env2, 'Gecerli_U', '12345678');
  assert.equal(satir(env2, 'SELECT COUNT(*) AS n FROM giris_denemeleri').n, 0);
  // özetleme yapılmadan 409 döner: hash çağrısı gerekmediği için sahte biber bile yanıtı değiştirmez
  const env3 = ortam();
  await kayitOl(env3, 'Ayse_01');
  const sure = Date.now(); const r = await kayitOl(env3, 'AYSE_01'); 
  assert.equal(r.durum, 409); assert.ok(Date.now() - sure < 2000);
});
test('profilTemizle: 2 KB sınırı, sayı ve il adı kuralları', () => {
  assert.equal(profilTemizle({ ...PROFIL, puan: 500 }).puan, undefined);
  assert.deepEqual(profilTemizle({ ...PROFIL, iller: ['Ankara', '<script>', 5, 'A'.repeat(50)] }).iller, ['Ankara']);
  assert.equal(profilTemizle({ ...PROFIL, bolum: 'x'.repeat(500) }).bolum.length, 60);
  assert.equal(profilTemizle(null), null);
  assert.ok(JSON.stringify(profilTemizle({ ...PROFIL, iller: Array.from({ length: 200 }, () => 'Kahramanmaraş') })).length <= 2048);
});

test('göç 0005: eski şemaya uygulanır, tekrar uygulamak zararsızdır; google_sub benzersizdir', async () => {
  const { DatabaseSync } = await import('node:sqlite');
  const { readFileSync } = await import('node:fs');
  const dosya = (y) => readFileSync(new URL(y, import.meta.url), 'utf8');
  const db = new DatabaseSync(':memory:');
  db.exec(dosya('./eski-schema.sql'));
  for (const m of ['0002_ozellikler', '0003_odalar', '0004_ozel_takip']) db.exec(dosya(`../migrations/${m}.sql`));
  db.exec("INSERT INTO uyeler (id, tg_id, rumuz, kayit) VALUES (10, 5, 'Eski_U', 1)");
  db.exec(dosya('../migrations/0005_kayit.sql'));
  assert.equal(db.prepare('SELECT sifre_ozet, google_sub, profil FROM uyeler WHERE id = 10').get().sifre_ozet, null);
  db.exec("INSERT INTO uyeler (tg_id, rumuz, google_sub) VALUES (NULL, 'A_Uye', 'g1'), (NULL, 'B_Uye', 'g2'), (NULL, 'C_Uye', NULL), (NULL, 'D_Uye', NULL)");
  assert.throws(() => db.exec("INSERT INTO uyeler (tg_id, rumuz, google_sub) VALUES (NULL, 'E_Uye', 'g1')"));
  db.exec(dosya('../migrations/0005_kayit.sql').replace(/ALTER TABLE[^;]*;/g, ''));
});
