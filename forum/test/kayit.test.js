import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir, uyeGirisi, kayitEskit, sahteFetch, telegramImzala } from './yardim.js';
import { b64uKodla, metinB64u } from '../src/yardimci.js';
import { oturumUret, geciciUret, geciciTgKimligi, geciciGoogleUret, geciciGoogleKimligi, oturumUyeKimligi } from '../src/oturum.js';
import { sifreKurali, sifreOzetle, sifreDogrula, kurtarmaKoduUret, kurtarmaKoduSadelestir, kurtarmaKoduBicimiGecerli } from '../src/sifre.js';
import { googleJetonuDogrula, googleAnahtarOnbellegiTemizle } from '../src/google.js';
import { profilTemizle } from '../src/profil.js';

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
  assert.match(s.sifre_ozet, /^pbkdf2\$20000\$[A-Za-z0-9_-]{22}\$[A-Za-z0-9_-]{43}$/);
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

test('şifreyle giriş: rumuz başına 15 dakikada 10 başarısız deneme sonrası doğru şifre bile 429', async () => {
  const env = ortam();
  await kayitOl(env);
  for (let i = 0; i < 10; i++) {
    const r = await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: `Yanlis-${i}-abc` }, basliklar: { 'CF-Connecting-IP': `198.51.100.${i}` } });
    assert.equal(r.durum, 401);
  }
  const r = await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE }, basliklar: { 'CF-Connecting-IP': '198.51.100.99' } });
  assert.equal(r.durum, 429);
  env.DB.ham.prepare('UPDATE giris_denemeleri SET olusma = olusma - 1000').run();
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: SIFRE }, basliklar: { 'CF-Connecting-IP': '198.51.100.99' } })).durum, 200);
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

test('şifre özeti: tekrar sayısı özetin içinde, biberli, yanlış şifre ve bozuk özet reddedilir', async () => {
  const env = ortam();
  const o = await sifreOzetle(env, 'Sifrem-Cok-Iyi-1');
  assert.ok(await sifreDogrula(env, 'Sifrem-Cok-Iyi-1', o));
  assert.equal(await sifreDogrula(env, 'Sifrem-Cok-Iyi-2', o), false);
  assert.equal(await sifreDogrula({ ...env, SIFRE_BIBERI: 'baska-biber' }, 'Sifrem-Cok-Iyi-1', o), false);   // biber değişirse özet geçersiz
  assert.equal(await sifreDogrula(env, 'x', null), false);
  assert.equal(await sifreDogrula(env, 'x', 'pbkdf2$abc$x$y'), false);
  const o2 = await sifreOzetle(env, 'Sifrem-Cok-Iyi-1', 1500);   // eski/farklı tekrar sayısıyla yazılmış özet hâlâ doğrulanır
  assert.ok(o2.startsWith('pbkdf2$1500$'));
  assert.ok(await sifreDogrula(env, 'Sifrem-Cok-Iyi-1', o2));
  const e3 = { OTURUM_SIRRI: 'yalniz-oturum' };   // SIFRE_BIBERI yoksa OTURUM_SIRRI kullanılır
  assert.ok(await sifreDogrula(e3, 'abc', await sifreOzetle(e3, 'abc')));
});

// ---------- şifre ve kod yönetimi ----------
test('/ben/sifre ve /ben/kurtarma-kodu: eski şifre gerekir, yanlışsa reddedilir', async () => {
  const env = ortam();
  const k = await kayitOl(env);
  const token = k.json.oturum;
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { govde: { eski: SIFRE, yeni: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { eski: 'Yanlis-Sifre-1', yeni: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { yeni: 'Yepyeni-Sifre-3' } })).durum, 401);   // eski yoksa değiştirilemez
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { eski: SIFRE, yeni: '12345678' } })).durum, 400);
  const d = await cagir(env, 'POST', '/ben/sifre', { token, govde: { eski: SIFRE, yeni: 'Yepyeni-Sifre-3' } });
  assert.equal(d.durum, 200); assert.equal(d.json.kurtarma_kodu, undefined);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Ayse_01', sifre: 'Yepyeni-Sifre-3' } })).durum, 200);
  // kurtarma kodunu yenile
  assert.equal((await cagir(env, 'POST', '/ben/kurtarma-kodu', { token, govde: { sifre: SIFRE } })).durum, 401);   // eski şifre artık yanlış
  const y = await cagir(env, 'POST', '/ben/kurtarma-kodu', { token, govde: { sifre: 'Yepyeni-Sifre-3' } });
  assert.equal(y.durum, 200); assert.match(y.json.kurtarma_kodu, KOD_DESENI);
  assert.equal((await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Ayse_01', kod: k.json.kurtarma_kodu, yeni_sifre: 'Bir-Baska-Sifre-4' } })).durum, 401);   // ilk kod bitti
  assert.equal((await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Ayse_01', kod: y.json.kurtarma_kodu, yeni_sifre: 'Bir-Baska-Sifre-4' } })).durum, 200);
});

test('Telegram üyesi şifre ekleyebilir: eski gerekmez, kurtarma kodu bir kez verilir, sonra eski gerekir', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Tg_Ekle');   // yerel deneme girişi: tg_id < 0
  const token = u.token;
  assert.equal((await cagir(env, 'POST', '/ben/kurtarma-kodu', { token, govde: { sifre: 'x' } })).durum, 400);   // şifresizken kod yenilenemez
  const r = await cagir(env, 'POST', '/ben/sifre', { token, govde: { yeni: SIFRE } });
  assert.equal(r.durum, 200); assert.match(r.json.kurtarma_kodu, KOD_DESENI);
  assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Tg_Ekle', sifre: SIFRE } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/sifre', { token, govde: { yeni: 'Yepyeni-Sifre-3' } })).durum, 401);
  assert.equal((await cagir(env, 'GET', '/ben', { token })).json.uye.sifre_var, true);
});

// ---------- Turnstile ve genel ayar ----------
test('Turnstile: gizli anahtar varsa /kayit jeton ister ve siteverify ile doğrular; yoksa atlanır', async () => {
  const env = ortam({ TURNSTILE_GIZLI: 'gizli', TURNSTILE_SITE: 'site-anahtari' });
  const ayar = await cagir(env, 'GET', '/giris/ayar');
  assert.equal(ayar.json.turnstile_site, 'site-anahtari'); assert.equal(ayar.json.google_istemci, ''); assert.equal(ayar.json.sifre, true);
  assert.equal((await cagir(env, 'GET', '/durum')).json.giris.turnstile_site, 'site-anahtari');
  assert.equal((await cagir(ortam(), 'GET', '/giris/ayar')).json.turnstile_site, '');
  const f = sahteFetch(async (url, s) => new Response(JSON.stringify({ success: String(s.body).includes('response=iyi') }), { status: 200 }));
  try {
    assert.equal((await kayitOl(env)).durum, 400);
    assert.equal(f.cagrilar.length, 0);   // jeton yoksa dış istek yapılmaz
    assert.equal((await kayitOl(env, 'Ayse_01', SIFRE, { turnstile: 'kotu' })).durum, 400);
    assert.equal((await kayitOl(env, 'Ayse_01', SIFRE, { turnstile: 'iyi' })).durum, 200);
    assert.equal(f.cagrilar[0].url, 'https://challenges.cloudflare.com/turnstile/v0/siteverify');
    assert.ok(String(f.cagrilar[0].secenek.body).includes('secret=gizli'));
    f.geri();
    const f2 = sahteFetch(async () => { throw new Error('ağ'); });
    try { assert.equal((await kayitOl(env, 'Baska_Uye', SIFRE, { turnstile: 'iyi' })).durum, 400); } finally { f2.geri(); }
    assert.equal((await kayitOl(ortam(), 'Ayse_01')).durum, 200);   // yapılandırılmamışsa jeton aranmaz
  } finally { f.geri(); }
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
  const p = metinB64u(JSON.stringify({ iss: 'https://accounts.google.com', aud: GOOGLE_ISTEMCI, sub: '110169484474386276334', email_verified: true, iat: t, exp: t + 3600, email: 'x@example.com', ...yuk }));
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
    assert.deepEqual(iyi, { tamam: true, sub: '110169484474386276334' });
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
    assert.equal(JSON.stringify(s).includes('example.com'), false);
    const g2 = await cagir(env, 'POST', '/giris/google', { govde: { kimlik_jetonu: await googleJetonu(ozel) } });
    assert.equal(g2.durum, 200); assert.equal(g2.json.uye.id, r.json.uye.id); assert.ok(g2.json.oturum);
    const ben = await cagir(env, 'GET', '/ben', { token: g2.json.oturum });
    assert.equal(ben.json.uye.google_var, true); assert.equal(ben.json.uye.telegram, false);
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
  const atla = await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: { v: 1, atlandi: true, t: '2026-11-02' } } });
  assert.deepEqual(atla.json.profil, { v: 1, atlandi: true, t: '2026-11-02' });
  assert.equal((await cagir(env, 'POST', '/ben/profil', { token, govde: { profil: null } })).durum, 200);
  assert.equal((await cagir(env, 'GET', '/ben', { token })).json.profil, null);
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
