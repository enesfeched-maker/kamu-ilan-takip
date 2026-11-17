// E-posta ile giriş: kod gönderme/doğrulama, sınırlar, hesap sızdırmama, Google bağlama, e-postayla şifre sıfırlama, hesap silme.
// Brevo her testte sahte fetch ile taklit edilir; gerçek API'ye hiçbir istek gitmez.
import test from 'node:test';
import assert from 'node:assert/strict';
import { ortam, cagir, uyeGirisi, kayitEskit, sahteFetch } from './yardim.js';
import { b64uKodla, metinB64u } from '../src/yardimci.js';
import { oturumUret, geciciUret, geciciGoogleUret, geciciEpostaUret, geciciEpostaKimligi, geciciGoogleKimligi, geciciGoogleEposta, geciciTgKimligi, oturumUyeKimligi, jetonImzala } from '../src/oturum.js';
import { epostaNormalle, epostaMaskele } from '../src/epostabicim.js';
import { epostaIcerigi, kodUret, GUNLUK_SINIR, GUNLUK_DOLU } from '../src/eposta.js';
import { googleAnahtarOnbellegiTemizle } from '../src/google.js';
import { ipSinirSifirla } from '../src/hiz.js';

const BREVO = 'https://api.brevo.com/v3/smtp/email';
const SIFRE = 'Guvenli-Sifre-9';
const simdi = () => Math.floor(Date.now() / 1000);
const bugun = () => new Date().toISOString().slice(0, 10);
const satir = (env, sql, ...p) => env.DB.ham.prepare(sql).get(...p);
const tum = (env, sql, ...p) => env.DB.ham.prepare(sql).all(...p);
const calistir = (env, sql, ...p) => env.DB.ham.prepare(sql).run(...p);
// ORTAM=yerel: Turnstile şartı yok (üretimde şart; ayrı test). Brevo anahtarı verildiği için gerçek gönderim yolu (taklit fetch) kullanılır.
const ortamE = (ek = {}) => ortam({ BREVO_ANAHTARI: 'brevo-test-anahtari', ORTAM: 'yerel', ...ek });
const IP = (n) => ({ 'CF-Connecting-IP': `203.0.${n}.1` });   // her n ayrı /24 kovası (günlük gönderim sayacı /24 başınadır)

// Brevo + (isteğe bağlı) Google JWKS taklidi.
function ag({ brevoDurum = 201, jwk = null } = {}) {
  const posta = [];
  const f = sahteFetch(async (url, secenek) => {
    if (url === BREVO) {
      posta.push({ ...JSON.parse(secenek.body), _basliklar: secenek.headers, _yontem: secenek.method });
      return new Response(brevoDurum < 300 ? '{"messageId":"<x@y>"}' : '{"code":"x"}', { status: brevoDurum });
    }
    if (jwk && url === 'https://www.googleapis.com/oauth2/v3/certs') return new Response(JSON.stringify({ keys: [jwk] }), { status: 200, headers: { 'Cache-Control': 'public, max-age=22000' } });
    return new Response('yok', { status: 404 });
  });
  return { posta, cagrilar: f.cagrilar, geri: f.geri };
}
const sonKod = (a) => /: (\d{6})\./.exec(a.posta[a.posta.length - 1].textContent)[1];
const kodIste = (env, eposta, ek = {}, basliklar = IP(1)) => cagir(env, 'POST', '/giris/eposta/kod', { govde: { eposta, ...ek }, basliklar });
const dogrula = (env, eposta, kod, basliklar = IP(1)) => cagir(env, 'POST', '/giris/eposta/dogrula', { govde: { eposta, kod }, basliklar });
const gerisar = (env) => {   // 60 sn bekleme dolmuş ve IP günlük gönderim sayacı sıfırlanmış sayılsın
  calistir(env, 'UPDATE eposta_kodlari SET son_gonderim = son_gonderim - 120');
  calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'gonder_ip'");
};
const sayac = (env, tur) => tum(env, 'SELECT * FROM eposta_sayac WHERE tur = ?', tur);

// Üç adım: kod iste → doğrula → (yeni üyeyse) rumuz seç. Dönen: son yanıt.
async function epostaylaGir(env, a, eposta, rumuz, basliklar = IP(1)) {
  ipSinirSifirla(); gerisar(env);
  const k = await kodIste(env, eposta, {}, basliklar);
  assert.equal(k.durum, 200, JSON.stringify(k.json));
  const d = await dogrula(env, eposta, sonKod(a), basliklar);
  assert.equal(d.durum, 200, JSON.stringify(d.json));
  if (!d.json.yeni) return d;
  return cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: d.json.gecici, rumuz } });
}

// ---------- içerik ve gönderim ----------
test('e-posta içeriği: Türkçe, sade, konu kodu içerir, tire/emoji yok, görsel ve izleme pikseli yok', () => {
  const c = epostaIcerigi('giris', '123456');
  assert.equal(c.konu, 'KPSS Tercihi giriş kodun: 123456');
  assert.equal(c.metin, 'Giriş kodun: 123456. 10 dakika geçerli. Bu isteği sen yapmadıysan bu e-postayı yok say.');
  for (const [amac, bas] of [['sifirla', 'Şifre sıfırlama kodun'], ['degistir', 'E-posta doğrulama kodun']]) {
    const x = epostaIcerigi(amac, '000042');
    assert.ok(x.metin.startsWith(`${bas}: 000042.`)); assert.ok(x.konu.endsWith(': 000042'));
  }
  for (const s of [c.konu, c.metin, c.html]) assert.equal(/[—–]/.test(s), false);
  assert.ok(c.html.includes('123456') && c.html.includes('lang="tr"'));
  assert.equal(/<img|<script|<link|url\(|http/i.test(c.html), false);
});

test('kodUret: her zaman 6 hane, başında sıfır korunur, dağılım tek değere takılmaz', () => {
  const g = new Set(); const ilk = new Set();
  for (let i = 0; i < 3000; i++) { const k = kodUret(); assert.match(k, /^\d{6}$/); g.add(k); ilk.add(k[0]); }
  assert.ok(g.size > 2900); assert.equal(ilk.size, 10);
});

test('kod gönderme: Brevo API çağrısı, gönderici, başlık; adres ve kod veritabanına düz yazılmaz', async () => {
  const env = ortamE(); const a = ag();
  try {
    const r = await kodIste(env, '  Ayse.Yilmaz@Example.COM ');
    assert.equal(r.durum, 200); assert.deepEqual(r.json, { tamam: true, bekle: 60 });
    assert.equal(a.posta.length, 1);
    const p = a.posta[0];
    assert.equal(a.cagrilar[0].url, BREVO); assert.equal(p._yontem, 'POST');
    assert.equal(p._basliklar['api-key'], 'brevo-test-anahtari');
    assert.deepEqual(p.sender, { name: 'KPSS Tercihi', email: 'bildirim@kpsstercihi.com' });
    assert.deepEqual(p.to, [{ email: 'ayse.yilmaz@example.com' }]);   // küçük harf, boşluksuz
    const kod = sonKod(a);
    assert.equal(p.subject, `KPSS Tercihi giriş kodun: ${kod}`);
    assert.equal(p.textContent, `Giriş kodun: ${kod}. 10 dakika geçerli. Bu isteği sen yapmadıysan bu e-postayı yok say.`);
    assert.ok(p.htmlContent.includes(kod));
    // kayıt: yalnız özetler
    const dokum = JSON.stringify({ k: tum(env, 'SELECT * FROM eposta_kodlari'), d: tum(env, 'SELECT * FROM giris_denemeleri'), u: tum(env, 'SELECT * FROM uyeler') });
    assert.equal(dokum.includes('ayse.yilmaz'), false); assert.equal(dokum.includes('example.com'), false);
    assert.equal(new RegExp(`"${kod}"`).test(dokum), false);
    const s = satir(env, 'SELECT * FROM eposta_kodlari');
    assert.match(s.anahtar, /^[0-9a-f]{64}$/); assert.match(s.kod_ozet, /^[0-9a-f]{64}$/);
    assert.equal(s.deneme, 0); assert.ok(s.bitis - s.son_gonderim === 600);
    assert.equal(satir(env, 'SELECT n FROM eposta_gunluk WHERE gun = ?', bugun()).n, 1);
    // özel gönderici
    const env2 = ortamE({ EPOSTA_GONDEREN: 'giris@kpsstercihi.com' });
    await kodIste(env2, 'b@example.com', {}, IP(2));
    assert.equal(a.posta[1].sender.email, 'giris@kpsstercihi.com');
  } finally { a.geri(); }
});

test('adres doğrulama: geçersiz adresler 400, Brevo çağrılmaz; normalleştirme ve maske', async () => {
  const env = ortamE(); const a = ag();
  try {
    for (const k of ['', 'abc', 'a@b', 'a@@b.com', 'a b@example.com', 'a..b@example.com', '.a@example.com', 'a@-b.com', 'a@b.c', `${'x'.repeat(250)}@example.com`, 'ayşe@example.com', 'a@ömer.com', 5, null, ['a@b.com']]) {
      ipSinirSifirla();
      const r = await kodIste(env, k);
      assert.equal(r.durum, 400, String(k));
    }
    assert.equal(a.cagrilar.length, 0);
  } finally { a.geri(); }
  assert.equal(epostaNormalle(' A.B+etiket@Example.Com '), 'a.b+etiket@example.com');
  assert.equal(epostaNormalle('x@sub.example.co.uk'), 'x@sub.example.co.uk');
  assert.equal(epostaNormalle('a'.repeat(65) + '@example.com'), null);
  assert.equal(epostaNormalle('x@example.123'), null);
  assert.equal(epostaMaskele('ayse@gmail.com'), 'a***@gmail.com');
  assert.equal(epostaMaskele(null), null);
});

test('yapılandırma: BREVO_ANAHTARI yoksa e-posta kapalı (eposta:false, uçlar 503); yerel kipte açık', async () => {
  const kapali = ortam();
  assert.equal((await cagir(kapali, 'GET', '/giris/ayar')).json.eposta, false);
  assert.equal((await kodIste(kapali, 'a@example.com')).durum, 503);
  assert.equal((await dogrula(kapali, 'a@example.com', '123456')).durum, 503);
  assert.equal((await cagir(kapali, 'POST', '/sifre-sifirla/eposta', { govde: { rumuz: 'Ayse' } })).durum, 503);
  assert.equal((await cagir(ortamE(), 'GET', '/giris/ayar')).json.eposta, true);
  assert.equal((await cagir(ortamE({ SIFRE_BIBERI: undefined }), 'GET', '/giris/ayar')).json.eposta, false);   // biber olmadan özet üretilemez
  assert.equal((await cagir(ortam({ ORTAM: 'yerel' }), 'GET', '/giris/ayar')).json.eposta, true);
});

test('yerel geliştirme kipi: yalnız ORTAM=yerel ve anahtar yokken kod konsola yazılır, ağa istek gitmez', async () => {
  const kayitlar = []; const eskiLog = console.log;
  console.log = (...x) => { kayitlar.push(x.join(' ')); };
  const a = ag();
  try {
    const env = ortam({ ORTAM: 'yerel' });
    const r = await kodIste(env, 'yerel@example.com');
    assert.equal(r.durum, 200); assert.equal(a.cagrilar.length, 0);
    const satirKod = kayitlar.find((s) => s.includes('[eposta-gelistirme]'));
    assert.ok(satirKod); const kod = /: (\d{6})$/.exec(satirKod)[1];
    assert.equal((await dogrula(env, 'yerel@example.com', kod)).json.yeni, true);
    // yerelde ama anahtar varsa gerçek yol (Brevo) kullanılır, konsola kod yazılmaz
    kayitlar.length = 0;
    const env2 = ortam({ ORTAM: 'yerel', BREVO_ANAHTARI: 'x' });
    assert.equal((await kodIste(env2, 'yerel2@example.com', {}, IP(2))).durum, 200);
    assert.equal(a.posta.length, 1); assert.equal(kayitlar.some((s) => s.includes('[eposta-gelistirme]')), false);
  } finally { console.log = eskiLog; a.geri(); }
  // üretimde (ORTAM yok) anahtarsız asla gönderilmez / yazılmaz
  const b = ag();
  try { assert.equal((await kodIste(ortam(), 'x@example.com')).durum, 503); assert.equal(b.cagrilar.length, 0); } finally { b.geri(); }
});

// ---------- doğrulama akışı ----------
test('yeni adres: kod doğrulanınca geçici jeton gelir (oturum değil), rumuz seçilince hesap e-postayla açılır; sonra doğrudan oturum', async () => {
  const env = ortamE(); const a = ag();
  try {
    assert.equal((await kodIste(env, 'Yeni.Uye@Example.com')).durum, 200);
    const d = await dogrula(env, 'yeni.uye@example.com', sonKod(a));
    assert.equal(d.durum, 200); assert.equal(d.json.yeni, true); assert.ok(d.json.gecici); assert.equal(d.json.oturum, undefined);
    assert.equal(await geciciEpostaKimligi(env, d.json.gecici, simdi()), 'yeni.uye@example.com');
    assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM uyeler WHERE rol = ?', 'uye').n, 0);   // rumuz seçilene kadar üye yok
    assert.equal((await cagir(env, 'GET', '/ben', { token: d.json.gecici })).durum, 401);      // geçici jeton oturum değildir
    assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: d.json.gecici, rumuz: 'ab' } })).durum, 400);
    const r = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: d.json.gecici, rumuz: 'Eposta_Uye' } });
    assert.equal(r.durum, 200); assert.equal(r.json.uye.rumuz, 'Eposta_Uye'); assert.ok(r.json.oturum);
    const s = satir(env, 'SELECT * FROM uyeler WHERE rumuz = ?', 'Eposta_Uye');
    assert.equal(s.eposta, 'yeni.uye@example.com'); assert.ok(s.eposta_dogrulandi > 0);
    assert.equal(s.tg_id, null); assert.equal(s.google_sub, null); assert.equal(s.sifre_ozet, null);
    const ben = (await cagir(env, 'GET', '/ben', { token: r.json.oturum })).json;
    assert.equal(ben.uye.eposta, 'y***@example.com'); assert.equal(ben.uye.eposta_dogrulandi, true);
    assert.equal(ben.uye.sifre_var, false); assert.equal(JSON.stringify(ben).includes('yeni.uye@'), false);
    // aynı geçici jetonla ikinci üyelik açılmaz
    const r2 = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: d.json.gecici, rumuz: 'Baska_Rumuz' } });
    assert.equal(r2.json.uye.id, r.json.uye.id);
    // sonraki girişte doğrudan oturum (büyük/küçük harf fark etmez)
    ipSinirSifirla(); gerisar(env);
    await kodIste(env, 'YENI.uye@example.com');
    const d2 = await dogrula(env, 'yeni.uye@EXAMPLE.com', sonKod(a));
    assert.equal(d2.durum, 200); assert.equal(d2.json.uye.id, r.json.uye.id); assert.ok(d2.json.oturum); assert.equal(d2.json.yeni, undefined);
    assert.ok((await cagir(env, 'GET', '/ben', { token: d2.json.oturum })).json.uye);
    // e-posta üyesi forumda yazabilir
    kayitEskit(env, r.json.uye.id);
    const b = await cagir(env, 'POST', '/baslik', { token: r.json.oturum, govde: { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' } });
    assert.equal(b.durum, 201);
  } finally { a.geri(); }
});

test('mevcut üye: oturum sürümü korunur (sürüm artınca eski oturum kapanır, yeni giriş sürümü taşır)', async () => {
  const env = ortamE(); const a = ag();
  try {
    const r = await epostaylaGir(env, a, 'surum@example.com', 'Surum_Uye');
    calistir(env, 'UPDATE uyeler SET oturum_surum = 4 WHERE id = ?', r.json.uye.id);
    assert.equal((await cagir(env, 'GET', '/ben', { token: r.json.oturum })).durum, 401);
    const g = await epostaylaGir(env, a, 'surum@example.com', 'x');
    assert.equal((await cagir(env, 'GET', '/ben', { token: g.json.oturum })).durum, 200);
  } finally { a.geri(); }
});

test('kod tek kullanımlık; yanlış kod 400; süresi dolan kod 400', async () => {
  const env = ortamE(); const a = ag();
  try {
    await kodIste(env, 'tek@example.com');
    const kod = sonKod(a);
    const yanlis = kod === '000000' ? '111111' : '000000';
    const y = await dogrula(env, 'tek@example.com', yanlis);
    assert.equal(y.durum, 400); assert.equal(y.json.hata, 'Kod hatalı ya da süresi dolmuş. Yeni bir kod isteyebilirsin.');
    assert.equal((await dogrula(env, 'tek@example.com', kod)).durum, 200);
    assert.equal((await dogrula(env, 'tek@example.com', kod)).durum, 400);   // tüketildi
    // kod boşluklu / tireli yapıştırılabilir
    ipSinirSifirla(); gerisar(env);
    await kodIste(env, 'tek@example.com');
    const k2 = sonKod(a);
    assert.equal((await dogrula(env, 'tek@example.com', `${k2.slice(0, 3)} ${k2.slice(3)}`)).durum, 200);
    // başka adresin kodu geçmez
    ipSinirSifirla(); gerisar(env);
    await kodIste(env, 'bir@example.com');
    const k3 = sonKod(a);
    assert.equal((await dogrula(env, 'iki@example.com', k3)).durum, 400);
    // süre dolumu
    calistir(env, 'UPDATE eposta_kodlari SET bitis = ?', simdi() - 1);
    assert.equal((await dogrula(env, 'bir@example.com', k3)).durum, 400);
    // biçimi bozuk kod
    for (const k of ['12345', '1234567', 'abcdef', '', null, 123456.5]) { ipSinirSifirla(); assert.equal((await dogrula(env, 'bir@example.com', k)).durum, 400, String(k)); }
  } finally { a.geri(); }
});

test('yanlış kod sınırı: 5. yanlış denemede kod yanar (doğru kod da kabul edilmez); yeni kodla devam edilir', async () => {
  const env = ortamE(); const a = ag();
  try {
    await kodIste(env, 'sinir@example.com');
    const kod = sonKod(a); const yanlis = kod === '654321' ? '123456' : '654321';
    for (let i = 1; i <= 4; i++) assert.equal((await dogrula(env, 'sinir@example.com', yanlis)).durum, 400, `deneme ${i}`);
    const bes = await dogrula(env, 'sinir@example.com', yanlis);
    assert.equal(bes.durum, 429); assert.match(bes.json.hata, /Yeni bir kod iste/);
    assert.equal(satir(env, 'SELECT deneme FROM eposta_kodlari').deneme, 5);
    assert.equal((await dogrula(env, 'sinir@example.com', kod)).durum, 429);   // doğru kod da artık geçmez
    assert.equal(satir(env, "SELECT COUNT(*) AS n FROM uyeler WHERE eposta = 'sinir@example.com'").n, 0);
    ipSinirSifirla(); gerisar(env);
    assert.equal((await kodIste(env, 'sinir@example.com')).durum, 200);        // yeni kod: sayaç sıfırlanır
    assert.equal(satir(env, 'SELECT deneme FROM eposta_kodlari').deneme, 0);
    assert.equal((await dogrula(env, 'sinir@example.com', sonKod(a))).durum, 200);
    // IP başına başarısız deneme sınırı (15 dakikada 10): farklı adreslerde tahmin yağdırmak da kilitlenir
    const env2 = ortamE();
    for (let i = 0; i < 10; i++) { ipSinirSifirla(); assert.equal((await dogrula(env2, `x${i}@example.com`, '123456', IP(9))).durum, 400); }
    ipSinirSifirla();
    assert.equal((await dogrula(env2, 'x11@example.com', '123456', IP(9))).durum, 429);
    assert.equal((await dogrula(env2, 'x11@example.com', '123456', IP(10))).durum, 400);   // başka IP etkilenmez
  } finally { a.geri(); }
});

// ---------- gönderim sınırları ----------
test('yeniden gönderim: 60 sn bekleme (429 + bekle), adres başına saatte 5, IP başına saatte 10', async () => {
  const env = ortamE(); const a = ag();
  try {
    assert.equal((await kodIste(env, 'bekle@example.com')).durum, 200);
    const hemen = await kodIste(env, 'bekle@example.com');
    assert.equal(hemen.durum, 429); assert.ok(hemen.json.bekle >= 1 && hemen.json.bekle <= 60);
    assert.equal(a.posta.length, 1);   // ikinci gönderim yok
    // 5 gönderim/saat/adres
    for (let i = 0; i < 4; i++) { ipSinirSifirla(); gerisar(env); assert.equal((await kodIste(env, 'bekle@example.com')).durum, 200); }
    ipSinirSifirla(); gerisar(env);
    const alti = await kodIste(env, 'bekle@example.com');
    assert.equal(alti.durum, 429); assert.match(alti.json.hata, /Bu adrese çok fazla/);
    assert.equal(a.posta.length, 5);
    calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'eposta_adres'");   // saat geçti
    ipSinirSifirla(); gerisar(env);
    assert.equal((await kodIste(env, 'bekle@example.com')).durum, 200);
    assert.ok(!tum(env, 'SELECT anahtar FROM giris_denemeleri').some((x) => x.anahtar.includes('@')) && !sayac(env, 'eposta_adres').some((x) => x.anahtar.includes('@')));   // adres düz yazılmaz
  } finally { a.geri(); }
});

test('IP günlük gönderim sınırı (M2b): /24 kovası başına günde 5; başka /24 etkilenmez; gün dönünce açılır; ham IP saklanmaz', async () => {
  const env = ortamE(); const a = ag();
  try {
    for (let i = 0; i < 5; i++) { ipSinirSifirla(); assert.equal((await kodIste(env, `ip${i}@example.com`, {}, { 'CF-Connecting-IP': `203.0.113.${10 + i}` })).durum, 200); }   // aynı /24, farklı IP'ler
    ipSinirSifirla();
    const alti = await kodIste(env, 'ip5@example.com', {}, { 'CF-Connecting-IP': '203.0.113.99' });
    assert.equal(alti.durum, 429); assert.match(alti.json.hata, /bugün çok fazla/);
    assert.equal(a.posta.length, 5);
    ipSinirSifirla();
    assert.equal((await kodIste(env, 'ip5@example.com', {}, { 'CF-Connecting-IP': '203.0.114.1' })).durum, 200);   // başka /24
    // IPv6: /64 kovası
    const v6 = (son) => ({ 'CF-Connecting-IP': `2001:db8:1:2:${son}::1` });
    for (let i = 0; i < 5; i++) { ipSinirSifirla(); assert.equal((await kodIste(env, `v6${i}@example.com`, {}, v6(i + 1))).durum, 200); }
    ipSinirSifirla();
    assert.equal((await kodIste(env, 'v66@example.com', {}, v6(77))).durum, 429);
    // şifre sıfırlama ve /ben/eposta da aynı kovayı kullanır
    ipSinirSifirla();
    assert.equal((await sifirlaIste(env, { rumuz: 'Birisi' }, { 'CF-Connecting-IP': '203.0.113.5' })).durum, 429);
    // gün döndü
    calistir(env, "UPDATE eposta_sayac SET dilim = dilim - 1 WHERE tur = 'gonder_ip'");
    ipSinirSifirla();
    assert.equal((await kodIste(env, 'ip9@example.com', {}, { 'CF-Connecting-IP': '203.0.113.99' })).durum, 200);
    const dokum = JSON.stringify(tum(env, 'SELECT * FROM eposta_sayac'));
    assert.equal(/203\.0\.11|2001:db8|@/.test(dokum), false);   // ham IP ve adres saklanmaz
  } finally { a.geri(); }
});

test('kanonik adres (M2c): gmail noktaları/+ekler ve googlemail, tüm alanlarda +ek tek sayaç; saklanan adres değişmez', async () => {
  const env = ortamE(); const a = ag();
  try {
    const biçimler = ['ayse.yilmaz@gmail.com', 'ayseyilmaz@gmail.com', 'a.y.s.e.yilmaz+x@googlemail.com', 'AYSEYILMAZ+deneme@Gmail.com', 'ay.se.yilmaz+y@gmail.com'];
    for (let i = 0; i < 5; i++) { ipSinirSifirla(); gerisar(env); assert.equal((await kodIste(env, biçimler[i], {}, IP(20 + i))).durum, 200, biçimler[i]); }
    ipSinirSifirla(); gerisar(env);
    const alti = await kodIste(env, 'ayse.yilmaz+z@gmail.com', {}, IP(30));
    assert.equal(alti.durum, 429); assert.match(alti.json.hata, /Bu adrese çok fazla/);
    assert.equal(sayac(env, 'eposta_adres').length, 1);   // hepsi tek sayaç
    // gmail dışı alanlarda yalnız +ek atılır (noktalar anlamlıdır)
    const env2 = ortamE();
    for (let i = 0; i < 5; i++) { ipSinirSifirla(); gerisar(env2); assert.equal((await kodIste(env2, `ali+${i}@sirket.com`, {}, IP(40 + i))).durum, 200); }
    ipSinirSifirla(); gerisar(env2);
    assert.equal((await kodIste(env2, 'ali+9@sirket.com', {}, IP(50))).durum, 429);
    assert.equal((await kodIste(env2, 'a.li@sirket.com', {}, IP(51))).durum, 200);
    // kod, farklı gmail biçimlerinde aynı posta kutusu için geçerli; üyede yazıldığı gibi saklanan adres kullanılır
    const env3 = ortamE(); const b = ag();
    try {
      await kodIste(env3, 'ayse.yilmaz@gmail.com');
      const d = await dogrula(env3, 'ayseyilmaz+x@gmail.com', sonKod(b));
      assert.equal(d.json.yeni, true);
      const r = await cagir(env3, 'POST', '/giris/rumuz', { govde: { gecici: d.json.gecici, rumuz: 'Gmail_Uye' } });
      assert.equal(satir(env3, 'SELECT eposta FROM uyeler WHERE id = ?', r.json.uye.id).eposta, 'ayseyilmaz+x@gmail.com');   // yazılan biçim, kanonik değil
    } finally { b.geri(); }
  } finally { a.geri(); }
});

test('kaba ön süzgeç: aynı IP dakikada 10 isteğten sonra D1\'e dokunmadan 429', async () => {
  const env = ortamE(); const a = ag();
  try {
    for (let i = 0; i < 10; i++) await kodIste(env, 'gecersiz', {}, IP(44));
    const once = env.DB.sayac.sorgu;
    const r = await kodIste(env, 'kaba11@example.com', {}, IP(44));
    assert.equal(r.durum, 429); assert.equal(env.DB.sayac.sorgu, once);
  } finally { a.geri(); }
});

test('günlük sınır: 280\'de durur, dostça hata, Brevo çağrılmaz; yeni UTC günü sayaç sıfırdan başlar ve eski günler silinir', async () => {
  const env = ortamE(); const a = ag();
  try {
    assert.equal(GUNLUK_SINIR, 280);
    await epostaylaGir(env, a, 'son@example.com', 'Son_Uye');   // hesabı olan adres (kota yedeği yalnız hesapsız adresleri keser)
    const onceki = a.posta.length;
    calistir(env, 'UPDATE eposta_gunluk SET n = 279 WHERE gun = ?', bugun());
    ipSinirSifirla(); gerisar(env);
    assert.equal((await kodIste(env, 'son@example.com')).durum, 200);
    assert.equal(satir(env, 'SELECT n FROM eposta_gunluk WHERE gun = ?', bugun()).n, 280);
    const r = await kodIste(env, 'sonrasi@example.com', {}, IP(2));
    assert.equal(r.durum, 503); assert.equal(r.json.hata, 'Şu an e-posta gönderemiyoruz, Google ya da rumuzla devam edebilirsin.'); assert.equal(r.json.hata, GUNLUK_DOLU);
    assert.equal(a.posta.length, onceki + 1);
    assert.equal(satir(env, 'SELECT n FROM eposta_gunluk WHERE gun = ?', bugun()).n, 280);   // sayaç aşılmaz
    assert.equal(satir(env, "SELECT COUNT(*) AS n FROM eposta_kodlari WHERE anahtar IS NOT NULL").n, 1);   // sınır dolunca yeni kod satırı da yazılmaz
    // şifre sıfırlama da aynı sayaca bağlı
    const s = await cagir(env, 'POST', '/sifre-sifirla/eposta', { govde: { rumuz: 'Birisi' }, basliklar: IP(3) });
    assert.equal(s.durum, 503); assert.equal(s.json.hata, GUNLUK_DOLU);
    // dünün dolu sayacı bugünü etkilemez; 8+ gün öncesi satırlar temizlenir
    const env2 = ortamE();
    const dun = new Date(Date.now() - 86400e3).toISOString().slice(0, 10); const eski = new Date(Date.now() - 9 * 86400e3).toISOString().slice(0, 10);
    calistir(env2, 'INSERT INTO eposta_gunluk (gun, n) VALUES (?, 280), (?, 5)', dun, eski);
    assert.equal((await kodIste(env2, 'yeni@example.com')).durum, 200);
    assert.equal(satir(env2, 'SELECT n FROM eposta_gunluk WHERE gun = ?', bugun()).n, 1);
    assert.equal(satir(env2, 'SELECT COUNT(*) AS n FROM eposta_gunluk WHERE gun = ?', eski).n, 0);
    assert.equal(satir(env2, 'SELECT COUNT(*) AS n FROM eposta_gunluk WHERE gun = ?', dun).n, 1);
  } finally { a.geri(); }
});

test('Brevo hatası: gönderim arka planda yapılır (yanıt aynı 200), başarısızsa kod satırı ve günlük hak geri alınır', async () => {
  const env = ortamE();
  for (const durum of [401, 400, 500]) {
    const a = ag({ brevoDurum: durum });
    try {
      ipSinirSifirla(); gerisar(env);
      const r = await kodIste(env, 'hata@example.com');
      assert.equal(r.durum, 200, String(durum)); assert.deepEqual(r.json, { tamam: true, bekle: 60 });   // hata yanıta sızmaz (zamanlama da aynı)
      assert.equal(a.posta.length, 1);
      assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM eposta_kodlari').n, 0);
      assert.equal(satir(env, 'SELECT COALESCE(MAX(n), 0) AS n FROM eposta_gunluk').n, 0);
    } finally { a.geri(); }
  }
  const f = sahteFetch(async () => { throw new Error('ağ yok'); });
  try { ipSinirSifirla(); assert.equal((await kodIste(env, 'hata2@example.com', {}, IP(5))).durum, 200); assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM eposta_kodlari').n, 0); } finally { f.geri(); }
  const iyi = ag();
  try { ipSinirSifirla(); gerisar(env); assert.equal((await kodIste(env, 'hata@example.com')).durum, 200); assert.equal(iyi.posta.length, 1); } finally { iyi.geri(); }   // hemen yeniden denenebilir
});

test('arka plan gönderimi (O3): yanıt Brevo çağrısını beklemez; ctx.waitUntil ile tamamlanır', async () => {
  const env = ortamE();
  let cevap; const kapi = new Promise((ok) => { cevap = ok; });
  const f = sahteFetch(async (url) => { if (url === BREVO) await kapi; return new Response('{}', { status: 201 }); });
  try {
    const bekleyen = [];
    const r = await cagir(env, 'POST', '/giris/eposta/kod', { govde: { eposta: 'arka@example.com' }, basliklar: IP(1), ctx: { waitUntil: (p) => bekleyen.push(p) } });
    assert.equal(r.durum, 200);   // Brevo yanıtı hâlâ bekliyor, ama istek döndü
    assert.equal(f.cagrilar.filter((c) => c.url === BREVO).length, 1);
    cevap(); await Promise.all(bekleyen);
    assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM eposta_kodlari').n, 1);
  } finally { cevap(); f.geri(); }
});

test('robot kontrolü: TURNSTILE_GIZLI tanımlıysa jeton şart', async () => {
  const env = ortamE({ TURNSTILE_GIZLI: 'gizli' }); const a = ag();
  const sf = sahteFetch(async (url, s) => {
    if (url === BREVO) { a.posta.push(JSON.parse(s.body)); return new Response('{}', { status: 201 }); }
    return new Response(JSON.stringify({ success: true, hostname: 'kpsstercihi.com' }), { status: 200 });
  });
  try {
    assert.equal((await kodIste(env, 't@example.com')).durum, 400);
    assert.equal(a.posta.length, 0);
    assert.equal((await kodIste(env, 't@example.com', { turnstile: 'iyi' })).durum, 200);
    assert.equal(a.posta.length, 1);
  } finally { sf.geri(); a.geri(); }
});

// ---------- hesap sızdırmama ----------
test('kod isteği: adres kayıtlı da olsa olmasa da yanıt ve e-posta aynı (hesap sızmaz)', async () => {
  const env = ortamE(); const a = ag();
  try {
    await epostaylaGir(env, a, 'kayitli@example.com', 'Kayitli_Uye');
    ipSinirSifirla(); gerisar(env);
    const var_ = await kodIste(env, 'kayitli@example.com', {}, IP(7));
    const yok = await kodIste(env, 'yokkullanici@example.com', {}, IP(8));
    assert.equal(var_.durum, 200); assert.deepEqual(var_.json, yok.json); assert.equal(var_.durum, yok.durum);
    const [x, y] = a.posta.slice(-2);
    assert.equal(x.subject.replace(/\d{6}/, 'K'), y.subject.replace(/\d{6}/, 'K'));
    assert.equal(x.textContent.replace(/\d{6}/, 'K'), y.textContent.replace(/\d{6}/, 'K'));
    // bekleme hatası da aynı biçimde
    const v2 = await kodIste(env, 'kayitli@example.com', {}, IP(7)); const y2 = await kodIste(env, 'yokkullanici@example.com', {}, IP(8));
    assert.equal(v2.durum, y2.durum); assert.equal(v2.json.hata, y2.json.hata);
  } finally { a.geri(); }
});

// ---------- Google bağlama ----------
const GOOGLE_ISTEMCI = '1234567890-abc.apps.googleusercontent.com';
async function anahtarCifti() {
  const c = await crypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
  return { ozel: c.privateKey, jwk: { ...(await crypto.subtle.exportKey('jwk', c.publicKey)), kid: 'anahtar-1', use: 'sig', alg: 'RS256' } };
}
async function googleJetonu(ozel, yuk = {}) {
  const t = simdi();
  const b = metinB64u(JSON.stringify({ alg: 'RS256', kid: 'anahtar-1', typ: 'JWT' }));
  const p = metinB64u(JSON.stringify({ iss: 'https://accounts.google.com', aud: GOOGLE_ISTEMCI, sub: '110169484474386276334', email_verified: true, iat: t, exp: t + 3600, email: 'Ayse@Gmail.com', ...yuk }));
  const imza = new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', ozel, new TextEncoder().encode(`${b}.${p}`)));
  return `${b}.${p}.${b64uKodla(imza)}`;
}
const googleGir = (env, jeton) => cagir(env, 'POST', '/giris/google', { govde: { kimlik_jetonu: jeton } });

test('Google bağlama: aynı doğrulanmış adresli e-posta üyesine Google kimliği eklenir ve oturum o üyeye açılır', async () => {
  googleAnahtarOnbellegiTemizle();
  const env = ortamE({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const { ozel, jwk } = await anahtarCifti(); const a = ag({ jwk });
  try {
    const e = await epostaylaGir(env, a, 'ayse@gmail.com', 'Ayse_Eposta');
    const g = await googleGir(env, await googleJetonu(ozel));   // Google e-postası 'Ayse@Example.com' (büyük harfli) -> normalleşir
    assert.equal(g.durum, 200); assert.equal(g.json.yeni, undefined); assert.equal(g.json.uye.id, e.json.uye.id); assert.ok(g.json.oturum);
    assert.equal(satir(env, 'SELECT google_sub FROM uyeler WHERE id = ?', e.json.uye.id).google_sub, '110169484474386276334');
    assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM uyeler WHERE rol = ?', 'uye').n, 1);   // ikinci hesap açılmadı
    const ben = (await cagir(env, 'GET', '/ben', { token: g.json.oturum })).json.uye;
    assert.equal(ben.google_var, true); assert.equal(ben.eposta, 'a***@gmail.com');
    // sonraki Google girişi sub ile
    assert.equal((await googleGir(env, await googleJetonu(ozel))).json.uye.id, e.json.uye.id);
    // e-posta koduyla da girmeye devam eder
    const k = await epostaylaGir(env, a, 'ayse@gmail.com', 'x');
    assert.equal(k.json.uye.id, e.json.uye.id);
  } finally { a.geri(); googleAnahtarOnbellegiTemizle(); }
});

test('Google: yeni Google üyesinin adresi hesaba yazılır; e-posta koduyla girince aynı hesap; e-postası yoksa bağlama olmaz', async () => {
  googleAnahtarOnbellegiTemizle();
  const env = ortamE({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const { ozel, jwk } = await anahtarCifti(); const a = ag({ jwk });
  try {
    const g1 = await googleGir(env, await googleJetonu(ozel, { email: 'gizli.kisi@gmail.com' }));
    assert.equal(g1.json.yeni, true);
    assert.equal(await geciciGoogleKimligi(env, g1.json.gecici, simdi()), '110169484474386276334');
    assert.equal(await geciciGoogleEposta(env, g1.json.gecici, simdi()), 'gizli.kisi@gmail.com');
    const r = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g1.json.gecici, rumuz: 'Google_Eposta' } });
    assert.equal(r.durum, 200);
    const s = satir(env, 'SELECT * FROM uyeler WHERE rumuz = ?', 'Google_Eposta');
    assert.equal(s.eposta, 'gizli.kisi@gmail.com'); assert.ok(s.eposta_dogrulandi > 0); assert.equal(s.google_sub, '110169484474386276334');
    const k = await epostaylaGir(env, a, 'gizli.kisi@gmail.com', 'x');
    assert.equal(k.json.uye.id, r.json.uye.id);
    // adresi olmayan eski Google üyesi: sonraki Google girişinde adres eklenir
    calistir(env, 'UPDATE uyeler SET eposta = NULL, eposta_dogrulandi = NULL WHERE id = ?', r.json.uye.id);
    assert.equal((await googleGir(env, await googleJetonu(ozel, { email: 'gizli.kisi@gmail.com' }))).durum, 200);
    assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', r.json.uye.id).eposta, 'gizli.kisi@gmail.com');
    // doğrulanmamış Google e-postası kabul edilmez (mevcut davranış): hesap açılmaz, bağlama olmaz
    assert.equal((await googleGir(env, await googleJetonu(ozel, { email_verified: false, sub: '777' }))).durum, 401);
  } finally { a.geri(); googleAnahtarOnbellegiTemizle(); }
});

test('Google: adres başka Google kimliğine bağlı hesaptaysa bağlanmaz, adres yeni hesaba yazılmaz (çakışma yok)', async () => {
  googleAnahtarOnbellegiTemizle();
  const env = ortamE({ GOOGLE_ISTEMCI_KIMLIGI: GOOGLE_ISTEMCI });
  const { ozel, jwk } = await anahtarCifti(); const a = ag({ jwk });
  try {
    const e = await epostaylaGir(env, a, 'cakisma@gmail.com', 'Cakisma_Uye');
    calistir(env, "UPDATE uyeler SET google_sub = '999' WHERE id = ?", e.json.uye.id);
    const g = await googleGir(env, await googleJetonu(ozel, { sub: '555', email: 'cakisma@gmail.com' }));
    assert.equal(g.json.yeni, true);
    assert.equal(await geciciGoogleEposta(env, g.json.gecici, simdi()), null);
    const r = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g.json.gecici, rumuz: 'Baska_Google' } });
    assert.equal(r.durum, 200); assert.notEqual(r.json.uye.id, e.json.uye.id);
    assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', r.json.uye.id).eposta, null);
    // jeton üretildikten sonra adres başka hesapta alınmışsa da yazılmaz
    const g2 = await geciciGoogleUret(env, '556', simdi(), 'cakisma@gmail.com');
    const r2 = await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: g2, rumuz: 'Google_Iki' } });
    assert.equal(r2.durum, 200); assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', r2.json.uye.id).eposta, null);
  } finally { a.geri(); googleAnahtarOnbellegiTemizle(); }
});

// ---------- geçici jeton türleri ----------
test('{e} geçici jetonu ne oturum ne Telegram ne Google jetonuyla karıştırılabilir', async () => {
  const env = ortam(); const t = simdi();
  const e = await geciciEpostaUret(env, 'a@example.com', t);
  const ot = await oturumUret(env, 9, t); const tg = await geciciUret(env, 55, t); const gg = await geciciGoogleUret(env, '12345', t, 'g@example.com');
  assert.equal(await geciciEpostaKimligi(env, e, t), 'a@example.com');
  for (const j of [ot, tg, gg]) assert.equal(await geciciEpostaKimligi(env, j, t), null);
  assert.equal(await geciciGoogleKimligi(env, e, t), null);
  assert.equal(await geciciTgKimligi(env, e, t), null);
  assert.equal(await oturumUyeKimligi(env, e, t), null);
  assert.equal(await geciciGoogleEposta(env, e, t), null);
  assert.equal(await geciciGoogleEposta(env, ot, t), null);
  assert.equal(await geciciGoogleEposta(env, gg, t), 'g@example.com');
  assert.equal(await geciciGoogleKimligi(env, gg, t), '12345');
  assert.equal(await geciciEpostaKimligi(env, e, t + 901), null);   // 15 dakika
  // alanları karışık imzalı jetonlar her türde reddedilir
  for (const yuk of [{ e: 'a@example.com', u: 3 }, { e: 'a@example.com', t: 5 }, { e: 'a@example.com', g: '1' }]) {
    const j = await jetonImzala(env, { ...yuk, s: t + 100 });
    assert.equal(await geciciEpostaKimligi(env, j, t), null, JSON.stringify(yuk));
    assert.equal(await oturumUyeKimligi(env, j, t), null);
    assert.equal(await geciciGoogleKimligi(env, j, t), null);
    assert.equal(await geciciTgKimligi(env, j, t), null);
  }
  assert.equal(await oturumUyeKimligi(env, await jetonImzala(env, { u: 3, e: 'a@example.com', s: t + 100 }), t), null);
  // biçimi bozuk e değerleri
  for (const bozuk of [5, 'adres-degil', 'a b@example.com', 'x'.repeat(260) + '@example.com', null, ['a@b.com']]) assert.equal(await geciciEpostaKimligi(env, await jetonImzala(env, { e: bozuk, s: t + 100 }), t), null);
  // uçta: {e} Bearer olarak oturum değildir; Telegram/Google geçici jetonu e-posta yolunda hesap açmaz; sahte jeton 401
  assert.equal((await cagir(env, 'GET', '/ben', { token: e })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: ot, rumuz: 'Sahte_Jeton' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: await jetonImzala(env, { e: 'a@example.com', u: 1, s: t + 100 }), rumuz: 'Sahte_Iki' } })).durum, 401);
  const imzasiz = e.split('.')[0] + '.' + 'A'.repeat(43);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: imzasiz, rumuz: 'Sahte_Uc' } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: e, rumuz: 'Gecici_Eposta' } })).durum, 200);
  assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE rumuz = ?', 'Gecici_Eposta').eposta, 'a@example.com');
  // e-posta jetonu ile Telegram/Google üyeliği açılamaz
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM uyeler WHERE google_sub IS NOT NULL OR tg_id IS NOT NULL').n, 0);
});

// ---------- e-postayla şifre sıfırlama ----------
async function sifreliUye(env, rumuz, eposta) {
  const k = await cagir(env, 'POST', '/kayit', { govde: { rumuz, sifre: SIFRE } });
  assert.equal(k.durum, 200, JSON.stringify(k.json));
  if (eposta) calistir(env, 'UPDATE uyeler SET eposta = ?, eposta_dogrulandi = 1 WHERE id = ?', eposta, k.json.uye.id);
  return k.json;
}
const sifirlaIste = (env, govde, basliklar = IP(60)) => cagir(env, 'POST', '/sifre-sifirla/eposta', { govde, basliklar });
const sifirla = (env, govde, basliklar = IP(60)) => cagir(env, 'POST', '/sifre-sifirla', { govde, basliklar });

test('şifre sıfırlama (e-posta): kod kayıtlı adrese gider, yeni şifre belirlenir, eski oturumlar kapanır, eski şifre geçmez', async () => {
  const env = ortamE(); const a = ag();
  try {
    const k = await sifreliUye(env, 'Reset_Uye', 'reset@example.com');
    const i = await sifirlaIste(env, { rumuz: 'reset_uye' });
    assert.equal(i.durum, 200); assert.deepEqual(i.json, { tamam: true, bekle: 60 });
    assert.equal(a.posta.length, 1); assert.deepEqual(a.posta[0].to, [{ email: 'reset@example.com' }]);
    assert.match(a.posta[0].subject, /^KPSS Tercihi şifre sıfırlama kodun: \d{6}$/);
    const kod = sonKod(a);
    const yanlisKod = kod === '000001' ? '000002' : '000001';
    const yanlis = await sifirla(env, { rumuz: 'Reset_Uye', eposta_kodu: yanlisKod, yeni_sifre: 'Yeni-Sifre-77' });
    assert.equal(yanlis.durum, 401);
    const zayif = await sifirla(env, { rumuz: 'Reset_Uye', eposta_kodu: kod, yeni_sifre: '12345678' });
    assert.equal(zayif.durum, 400);   // zayıf şifre kodu yakmaz
    const ok = await sifirla(env, { rumuz: 'Reset_Uye', eposta_kodu: kod, yeni_sifre: 'Yeni-Sifre-77' });
    assert.equal(ok.durum, 200); assert.equal(ok.json.uye.id, k.uye.id); assert.ok(ok.json.oturum);
    assert.equal(ok.json.kurtarma_kodu, undefined);   // kurtarma kodu zaten vardı: dokunulmaz
    assert.equal((await cagir(env, 'GET', '/ben', { token: k.oturum })).durum, 401);       // eski oturum kapandı
    assert.equal((await cagir(env, 'GET', '/ben', { token: ok.json.oturum })).durum, 200);
    assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Reset_Uye', sifre: SIFRE } })).durum, 401);
    assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Reset_Uye', sifre: 'Yeni-Sifre-77' } })).durum, 200);
    assert.equal((await cagir(env, 'POST', '/sifre-sifirla', { govde: { rumuz: 'Reset_Uye', kod: k.kurtarma_kodu, yeni_sifre: 'Baska-Sifre-88' } })).durum, 200);   // kurtarma kodu yolu hâlâ çalışır
    assert.equal((await sifirla(env, { rumuz: 'Reset_Uye', eposta_kodu: kod, yeni_sifre: 'Yine-Sifre-99' })).durum, 401);   // kod tek kullanımlık
  } finally { a.geri(); }
});

test('şifre sıfırlama (e-posta): adresle de istenir; şifresiz/kurtarma kodsuz e-posta üyesi ilk şifresiyle kurtarma kodu alır', async () => {
  const env = ortamE(); const a = ag();
  try {
    const e = await epostaylaGir(env, a, 'sifresiz@example.com', 'Sifresiz_Uye');
    ipSinirSifirla(); gerisar(env);
    assert.equal((await sifirlaIste(env, { eposta: ' Sifresiz@Example.com ' })).durum, 200);
    const kod = sonKod(a);
    const ok = await sifirla(env, { eposta: 'sifresiz@example.com', eposta_kodu: kod, yeni_sifre: 'Yeni-Sifre-77' });
    assert.equal(ok.durum, 200); assert.equal(ok.json.uye.id, e.json.uye.id);
    assert.match(ok.json.kurtarma_kodu, /^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/);
    assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Sifresiz_Uye', sifre: 'Yeni-Sifre-77' } })).durum, 200);
  } finally { a.geri(); }
});

test('şifre sıfırlama: hesap var/yok/e-postasız hep aynı yanıt; yalnız e-postası olana gönderilir; yanlış kod yanıtları da aynı', async () => {
  const env = ortamE(); const a = ag();
  try {
    await sifreliUye(env, 'Var_Uye', 'var@example.com');
    await sifreliUye(env, 'Eposta_Yok', null);
    const sonuc = [];
    for (const [n, govde] of [[1, { rumuz: 'Var_Uye' }], [2, { rumuz: 'Olmayan_Biri' }], [3, { rumuz: 'Eposta_Yok' }], [5, { eposta: 'hic@example.com' }]]) {
      ipSinirSifirla(); sonuc.push(await sifirlaIste(env, govde, IP(60 + n)));
    }
    for (const r of sonuc) { assert.equal(r.durum, 200); assert.deepEqual(r.json, { tamam: true, bekle: 60 }); }
    assert.equal(a.posta.length, 1);   // yalnız Var_Uye
    // aynı üye için adresle istek, rumuzla isteğin sayacını paylaşır (tek hedef sayacı): bekleme sürerken 429
    ipSinirSifirla();
    assert.equal((await sifirlaIste(env, { eposta: 'var@example.com' }, IP(64))).durum, 429);
    assert.equal(a.posta.length, 1);
    // hemen ikinci istek: hepsi aynı 429
    const bekle = [];
    for (const [n, govde] of [[1, { rumuz: 'Var_Uye' }], [2, { rumuz: 'Olmayan_Biri' }], [3, { rumuz: 'Eposta_Yok' }]]) { ipSinirSifirla(); bekle.push(await sifirlaIste(env, govde, IP(60 + n))); }
    for (const r of bekle) { assert.equal(r.durum, 429); assert.deepEqual(r.json, bekle[0].json); }
    // yanlış kod: hesap olsa da olmasa da aynı 401 gövdesi
    const y1 = await sifirla(env, { rumuz: 'Var_Uye', eposta_kodu: '000000', yeni_sifre: 'Yeni-Sifre-77' }, IP(80));
    const y2 = await sifirla(env, { rumuz: 'Olmayan_Biri', eposta_kodu: '000000', yeni_sifre: 'Yeni-Sifre-77' }, IP(81));
    const y3 = await sifirla(env, { rumuz: 'Eposta_Yok', eposta_kodu: '000000', yeni_sifre: 'Yeni-Sifre-77' }, IP(82));
    assert.equal(y1.durum, 401); assert.deepEqual(y1.json, y2.json); assert.deepEqual(y1.json, y3.json);
    // 5 yanlış denemeden sonra da hesap varlığı sızmaz: yine aynı yanıt
    for (let i = 0; i < 6; i++) await sifirla(env, { rumuz: 'Var_Uye', eposta_kodu: '000000', yeni_sifre: 'Yeni-Sifre-77' }, IP(90 + i));
    const dogruAma = await sifirla(env, { rumuz: 'Var_Uye', eposta_kodu: sonKod(a), yeni_sifre: 'Yeni-Sifre-77' }, IP(99));
    assert.equal(dogruAma.durum, 401); assert.deepEqual(dogruAma.json, y2.json);
    // geçersiz tanımlayıcı
    assert.equal((await sifirlaIste(env, {}, IP(100))).durum, 400);
    assert.equal((await sifirlaIste(env, { eposta: 'a@@b' }, IP(100))).durum, 400);
    // sayaç tablosunda adres/rumuz düz yazılmaz
    assert.equal(JSON.stringify(tum(env, 'SELECT * FROM giris_denemeleri')).includes('example.com'), false);
    // sıfırlama, üyenin KAYITLI adresinin saatlik gönderim sayacına da yazar (giriş kodu bütçesiyle ortak)
    assert.equal(sayac(env, 'eposta_adres').length, 1);
  } finally { a.geri(); }
});

test('şifre sıfırlama: saatte 5 istek sınırı (tanımlayıcı başına) ve e-posta kapalıyken kurtarma kodu yolu çalışır', async () => {
  const env = ortamE(); const a = ag();
  try {
    await sifreliUye(env, 'Sinirli_Uye', 'sinirli@example.com');
    for (let i = 0; i < 5; i++) { ipSinirSifirla(); calistir(env, 'UPDATE giris_denemeleri SET olusma = olusma - 120 WHERE tur = ?', 'sifirla_istek'); assert.equal((await sifirlaIste(env, { rumuz: 'Sinirli_Uye' }, IP(110 + i))).durum, 200); }
    ipSinirSifirla(); calistir(env, 'UPDATE giris_denemeleri SET olusma = olusma - 120 WHERE tur = ?', 'sifirla_istek');
    const r = await sifirlaIste(env, { rumuz: 'Sinirli_Uye' }, IP(120));
    assert.equal(r.durum, 429); assert.match(r.json.hata, /Çok fazla kod/);
  } finally { a.geri(); }
  // e-posta kapalı: eposta_kodu yolu 503, kurtarma kodu yolu çalışır
  const kapali = ortam();
  const k = await sifreliUye(kapali, 'Kodlu_Uye', null);
  assert.equal((await sifirla(kapali, { rumuz: 'Kodlu_Uye', eposta_kodu: '123456', yeni_sifre: 'Yeni-Sifre-77' })).durum, 503);
  assert.equal((await sifirla(kapali, { rumuz: 'Kodlu_Uye', kod: k.kurtarma_kodu, yeni_sifre: 'Yeni-Sifre-77' })).durum, 200);
});

// ---------- hesapta e-posta ekleme / değiştirme ----------
const benE = (env, token, govde, basliklar = IP(1)) => cagir(env, 'POST', '/ben/eposta', { token, govde, basliklar });

test('/ben/eposta: oturum şart; yeni adrese kod gider, doğrulanınca yazılır; oturum sürümü artar, taze jeton gelir; eski adrese bildirim gider (O4)', async () => {
  const env = ortamE(); const a = ag();
  try {
    const k = await uyeGirisi(env, 'Ekle_Uye');   // e-postası ve şifresi yok
    assert.equal((await benE(env, undefined, { eposta: 'a@example.com' })).durum, 401);
    assert.equal((await benE(env, k.token, { eposta: 'gecersiz' })).durum, 400);
    const i = await benE(env, k.token, { eposta: 'Yeni.Adres@Example.com' });
    assert.equal(i.durum, 200); assert.deepEqual(i.json, { tamam: true, bekle: 60 });
    assert.deepEqual(a.posta[0].to, [{ email: 'yeni.adres@example.com' }]);
    assert.match(a.posta[0].subject, /^KPSS Tercihi e-posta doğrulama kodun: \d{6}$/);
    assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', k.id).eposta, null);   // kod girilene kadar yazılmaz
    const kod = sonKod(a);
    assert.equal((await benE(env, k.token, { eposta: 'yeni.adres@example.com', kod: kod === '000009' ? '000008' : '000009' })).durum, 400);
    assert.equal((await benE(env, k.token, { eposta: 'baska@example.com', kod })).durum, 400);   // başka adresin koduyla olmaz
    const ok = await benE(env, k.token, { eposta: 'yeni.adres@example.com', kod });
    assert.equal(ok.durum, 200);
    assert.deepEqual({ ...ok.json, oturum: undefined }, { tamam: true, eposta: 'y***@example.com', eposta_dogrulandi: true, oturum: undefined });
    assert.ok(ok.json.oturum && ok.json.oturum !== k.token);
    const s = satir(env, 'SELECT eposta, eposta_dogrulandi, oturum_surum FROM uyeler WHERE id = ?', k.id);
    assert.equal(s.eposta, 'yeni.adres@example.com'); assert.ok(s.eposta_dogrulandi > 0); assert.equal(s.oturum_surum, 1);
    assert.equal((await cagir(env, 'GET', '/ben', { token: k.token })).durum, 401);   // eski oturum kapandı
    const ben = await cagir(env, 'GET', '/ben', { token: ok.json.oturum });
    assert.equal(ben.durum, 200); assert.equal(ben.json.uye.eposta, 'y***@example.com'); assert.equal(ben.json.uye.eposta_dogrulandi, true);
    assert.equal(a.posta.length, 1);   // eski adres yoktu: bildirim yok
    // aynı adresi tekrar eklemek anlamsız
    assert.equal((await benE(env, ok.json.oturum, { eposta: 'yeni.adres@example.com' })).durum, 400);
    // değiştirme: ESKİ adrese bildirim gider, yeni jeton yine gelir
    ipSinirSifirla(); gerisar(env);
    await benE(env, ok.json.oturum, { eposta: 'ikinci@example.com' });
    const ok2 = await benE(env, ok.json.oturum, { eposta: 'ikinci@example.com', kod: sonKod(a) });
    assert.equal(ok2.durum, 200); assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', k.id).eposta, 'ikinci@example.com');
    assert.equal(satir(env, 'SELECT oturum_surum FROM uyeler WHERE id = ?', k.id).oturum_surum, 2);
    assert.equal((await cagir(env, 'GET', '/ben', { token: ok.json.oturum })).durum, 401);
    const bildirim = a.posta[a.posta.length - 1];
    assert.deepEqual(bildirim.to, [{ email: 'yeni.adres@example.com' }]);
    assert.equal(bildirim.subject, 'KPSS Tercihi: e-posta adresin değiştirildi');
    assert.equal(bildirim.textContent, "E-posta adresin değiştirildi; sen yapmadıysan iletisim@kpsstercihi.com'a yaz.");
    assert.equal(/[—–]/.test(bildirim.textContent + bildirim.htmlContent), false);
    // eski adresle artık yeni hesap açılır, yenisiyle bu hesaba girilir
    assert.equal((await epostaylaGir(env, a, 'ikinci@example.com', 'x')).json.uye.id, k.id);
  } finally { a.geri(); }
});

test('/ben/eposta (O4): şifresi olan üye her iki adımda mevcut şifreyi vermeli; yanlış şifre ve deneme bütçesi', async () => {
  const env = ortamE(); const a = ag();
  try {
    const k = await sifreliUye(env, 'Sifreli_Ekle', 'eski.adres@example.com');
    assert.equal((await benE(env, k.oturum, { eposta: 'yeni@example.com' })).json.hata, 'Mevcut şifre yanlış.');   // şifre yok
    assert.equal((await benE(env, k.oturum, { eposta: 'yeni@example.com', sifre: 'Yanlis-Sifre-1' })).durum, 401);
    assert.equal(a.posta.length, 0);   // şifresiz/yanlış şifreyle kod gönderilmez
    const i = await benE(env, k.oturum, { eposta: 'yeni@example.com', sifre: SIFRE });
    assert.equal(i.durum, 200); assert.equal(a.posta.length, 1);
    const kod = sonKod(a);
    assert.equal((await benE(env, k.oturum, { eposta: 'yeni@example.com', kod })).durum, 401);   // 2. adımda da şifre şart
    assert.equal((await benE(env, k.oturum, { eposta: 'yeni@example.com', kod, sifre: 'Yanlis-Sifre-1' })).durum, 401);
    assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', k.uye.id).eposta, 'eski.adres@example.com');
    const ok = await benE(env, k.oturum, { eposta: 'yeni@example.com', kod, sifre: SIFRE });   // yanlış şifre kodu yakmadı
    assert.equal(ok.durum, 200); assert.ok(ok.json.oturum);
    assert.equal((await cagir(env, 'GET', '/ben', { token: k.oturum })).durum, 401);
    assert.deepEqual(a.posta[a.posta.length - 1].to, [{ email: 'eski.adres@example.com' }]);   // eski adrese bildirim
    // hedef başına günlük deneme bütçesi: yanlış şifreler de sayılır, 20'den sonra doğru şifre de 429
    for (let i2 = 0; i2 < 25; i2++) { ipSinirSifirla(); calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'dogrula_ip'"); await benE(env, ok.json.oturum, { eposta: 'x@example.com', sifre: 'Yanlis-Sifre-1' }, IP(70 + (i2 % 5))); }
    ipSinirSifirla(); calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'dogrula_ip'");
    assert.equal((await benE(env, ok.json.oturum, { eposta: 'x@example.com', sifre: SIFRE }, IP(79))).durum, 429);
  } finally { a.geri(); }
});

test('/ben/eposta: adres başka hesaptaysa 409 (hesap ele geçirilemez); kod başka hesaba taşınamaz', async () => {
  const env = ortamE(); const a = ag();
  try {
    const diger = await epostaylaGir(env, a, 'dolu@example.com', 'Dolu_Uye');
    const k = await uyeGirisi(env, 'Cakisan_Uye');
    ipSinirSifirla(); gerisar(env);
    assert.equal((await benE(env, k.token, { eposta: 'dolu@example.com' })).durum, 200);   // hesap varlığı bu adımda sızmaz
    const kod = sonKod(a);
    const r = await benE(env, k.token, { eposta: 'dolu@example.com', kod });
    assert.equal(r.durum, 409);
    assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', k.id).eposta, null);
    assert.equal(satir(env, 'SELECT eposta FROM uyeler WHERE id = ?', diger.json.uye.id).eposta, 'dolu@example.com');
    // başka üyenin oturumuyla aynı kod kullanılamaz (kod üyeye bağlı)
    const k2 = await uyeGirisi(env, 'Ucuncu_Uye');
    ipSinirSifirla(); gerisar(env);
    await benE(env, k.token, { eposta: 'serbest@example.com' });
    const kod2 = sonKod(a);
    assert.equal((await benE(env, k2.token, { eposta: 'serbest@example.com', kod: kod2 })).durum, 400);
    assert.equal((await benE(env, k.token, { eposta: 'serbest@example.com', kod: kod2 })).durum, 200);
  } finally { a.geri(); }
});

// ---------- hesap silme ----------
test('hesap silme: onay şart; kimlik bilgileri silinir, yazılar "Silinmiş üye" adıyla kalır, oturumlar kapanır, rumuz ve adres serbest kalır', async () => {
  const env = ortamE(); const a = ag();
  try {
    const k = await cagir(env, 'POST', '/kayit', { govde: { rumuz: 'Silinecek_Uye', sifre: SIFRE } });
    const id = k.json.uye.id;
    calistir(env, "UPDATE uyeler SET eposta = 'sil@example.com', eposta_dogrulandi = 5, google_sub = '4242', tg_id = 4242, profil = '{}', kayitli = '[]' WHERE id = ?", id);
    kayitEskit(env, id);
    const b = await cagir(env, 'POST', '/baslik', { token: k.json.oturum, govde: { kategori: 'puan', baslik: 'P3 puanıyla tercih nasıl olur?', govde: 'Merhaba, bu yıl P3 puanıyla hangi kurumlar mantıklı olur?' } });
    assert.equal(b.durum, 201);
    assert.ok(satir(env, 'SELECT COUNT(*) AS n FROM takipler WHERE uye_id = ?', id).n > 0);   // başlık açan otomatik takip eder
    assert.equal((await cagir(env, 'POST', '/ben/hesap-sil', { govde: { onay: 'SİL' } })).durum, 401);
    for (const onay of [undefined, '', 'hayır', 'SIL ', 'sill', 5]) {
      ipSinirSifirla();
      assert.equal((await cagir(env, 'POST', '/ben/hesap-sil', { token: k.json.oturum, govde: { onay } })).durum, 400, String(onay));
    }
    assert.equal(satir(env, 'SELECT silindi FROM uyeler WHERE id = ?', id).silindi, null);
    ipSinirSifirla();
    const r = await cagir(env, 'POST', '/ben/hesap-sil', { token: k.json.oturum, govde: { onay: ' sil ' } });   // tr-TR: "sil" -> "SİL"
    assert.equal(r.durum, 200); assert.deepEqual(r.json, { tamam: true });
    const s = satir(env, 'SELECT * FROM uyeler WHERE id = ?', id);
    assert.equal(s.rumuz, `Silinmiş üye #${id}`); assert.equal(s.rumuz_kat, `silinmis-${id}`);
    for (const alan of ['eposta', 'eposta_dogrulandi', 'sifre_ozet', 'kurtarma_ozet', 'google_sub', 'tg_id', 'profil', 'kayitli', 'avatar', 'foto_surum', 'kart', 'basvurular']) assert.equal(s[alan], null, alan);
    assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM fotolar WHERE uye_id = ?', id).n, 0);
    assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM uye_katip WHERE uye_id = ?', id).n, 0);
    assert.ok(s.silindi > 0); assert.equal(s.engelli, 1); assert.equal(s.oturum_surum, 1); assert.equal(s.bildirim, 0); assert.equal(s.dm_acik, 0);
    assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM takipler WHERE uye_id = ?', id).n, 0);
    // yazı kaldı, yazar "Silinmiş üye"
    const baslik = await cagir(env, 'GET', `/baslik/${b.json.baslik.id}`);
    assert.equal(baslik.durum, 200); assert.ok(JSON.stringify(baslik.json).includes(`Silinmiş üye #${id}`)); assert.equal(JSON.stringify(baslik.json).includes('Silinecek_Uye'), false);
    // eski oturum ve eski girişler çalışmaz
    assert.equal((await cagir(env, 'GET', '/ben', { token: k.json.oturum })).durum, 401);
    assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: 'Silinecek_Uye', sifre: SIFRE } })).durum, 401);
    assert.equal((await cagir(env, 'POST', '/giris/sifre', { govde: { rumuz: `Silinmiş üye #${id}`, sifre: SIFRE } })).durum, 401);
    // rumuz ve adres serbest: aynı adresle yeni hesap açılır, silinmiş hesaba bağlanmaz
    ipSinirSifirla(); gerisar(env);
    await kodIste(env, 'sil@example.com');
    const d = await dogrula(env, 'sil@example.com', sonKod(a));
    assert.equal(d.json.yeni, true);
    // N3: eski rumuz 180 gün ayrılır (kimlik taklidi olmasın); büyük/küçük harf ve "." "_" farkı da aynı kat
    assert.equal((await cagir(env, 'POST', '/kayit', { govde: { rumuz: 'Silinecek_Uye', sifre: SIFRE } })).durum, 409);
    assert.equal((await cagir(env, 'POST', '/kayit', { govde: { rumuz: 'silinecek.uye', sifre: SIFRE } })).durum, 409);
    assert.equal((await cagir(env, 'POST', '/giris/rumuz', { govde: { gecici: d.json.gecici, rumuz: 'SILINECEK_uye' } })).durum, 409);
    const rez = satir(env, 'SELECT kat, bitis FROM ayrilmis_rumuzlar');
    assert.equal(rez.kat, 'silinecekuye'); assert.ok(Math.abs(rez.bitis - (simdi() + 180 * 86400)) < 5);
    calistir(env, 'UPDATE ayrilmis_rumuzlar SET bitis = ?', simdi() - 1);   // 180 gün doldu
    assert.equal((await cagir(env, 'POST', '/kayit', { govde: { rumuz: 'Silinecek_Uye', sifre: SIFRE } })).durum, 200);
    // kimse "Silinmiş üye" adını alamaz
    assert.equal((await cagir(env, 'POST', '/kayit', { govde: { rumuz: 'Silinmis uye 1', sifre: SIFRE } })).durum, 400);
    // aynı hesap ikinci kez silinemez (oturum kapalı)
    assert.equal((await cagir(env, 'POST', '/ben/hesap-sil', { token: k.json.oturum, govde: { onay: 'SİL' } })).durum, 401);
  } finally { a.geri(); }
});

test('hesap silme: sistem/asistan hesabı silinemez; başka üyelerin verisi etkilenmez', async () => {
  const env = ortamE();
  const u1 = await uyeGirisi(env, 'Kalan_Uye'); const u2 = await uyeGirisi(env, 'Giden_Uye');
  const r = await cagir(env, 'POST', '/ben/hesap-sil', { token: u2.token, govde: { onay: 'SİL' } });
  assert.equal(r.durum, 200);
  assert.equal(satir(env, 'SELECT rumuz FROM uyeler WHERE id = ?', u1.id).rumuz, 'Kalan_Uye');
  assert.equal((await cagir(env, 'GET', '/ben', { token: u1.token })).durum, 200);
  const sis = await oturumUret(env, 2, simdi(), 0);   // Asistan hesabına sahte oturum
  assert.equal((await cagir(env, 'POST', '/ben/hesap-sil', { token: sis, govde: { onay: 'SİL' } })).durum, 403);
});

// ---------- M1: atomik deneme sayacı ----------
test('M1: kod doğrulama tek atomik UPDATE ... RETURNING kullanır; paralel isteklerle 5 denemeden fazlası geçmez, doğru kod yalnız bir kez geçer', async () => {
  const env = ortamE(); const a = ag();
  try {
    await kodIste(env, 'yaris@example.com');
    const kod = sonKod(a); const yanlis = kod === '111111' ? '222222' : '111111';
    // SQL yolu: sayaç artışı ve karşılaştırma verisi aynı ifadede (okuma-sonra-yazma yok)
    const sqller = []; const asil = env.DB.prepare.bind(env.DB);
    env.DB.prepare = (sql) => { sqller.push(sql); return asil(sql); };
    const r = await dogrula(env, 'yaris@example.com', yanlis);
    assert.equal(r.durum, 400);
    assert.ok(sqller.some((s) => /UPDATE eposta_kodlari SET deneme = deneme \+ 1 WHERE anahtar = \? AND bitis > \? AND deneme < \? RETURNING kod_ozet, deneme/.test(s)));
    assert.equal(sqller.some((s) => /SELECT kod_ozet, bitis, deneme FROM eposta_kodlari/.test(s)), false);   // eski okuma-sonra-yazma kalıbı yok
    assert.ok(sqller.some((s) => /INSERT INTO eposta_sayac .* RETURNING n/.test(s)));                       // IP ve hedef sayaçları da atomik
    env.DB.prepare = asil;
    // 8 paralel yanlış deneme (1 yapıldı): satırdaki sayaç 5'i geçmez, hiçbiri başarılı olamaz
    const sonuclar = await Promise.all(Array.from({ length: 8 }, (_, i) => dogrula(env, 'yaris@example.com', yanlis, IP(100 + i))));
    assert.equal(satir(env, 'SELECT deneme FROM eposta_kodlari').deneme, 5);
    assert.equal(sonuclar.filter((x) => x.durum === 400).length, 3);   // 1 + 3 = 4 yanlış, 5. yanlış ve sonrası 429
    assert.equal(sonuclar.filter((x) => x.durum === 429).length, 5);
    assert.equal((await dogrula(env, 'yaris@example.com', kod)).durum, 429);   // 5. denemeden sonra doğru kod da geçmez
    // paralel doğru kodlar: tam bir tanesi tüketir
    ipSinirSifirla(); gerisar(env);
    await kodIste(env, 'yaris@example.com');
    const k2 = sonKod(a);
    const dogrular = await Promise.all(Array.from({ length: 4 }, (_, i) => dogrula(env, 'yaris@example.com', k2, IP(110 + i))));
    assert.equal(dogrular.filter((x) => x.durum === 200).length, 1);
    assert.equal(dogrular.filter((x) => x.durum !== 200).length, 3);
  } finally { a.geri(); }
});

test('M1: IP doğrulama sayacı artır-sonra-kontrol: paralel patlama sınırı aşamaz (15 dakikada 10)', async () => {
  const env = ortamE(); const a = ag();
  try {
    const sonuclar = await Promise.all(Array.from({ length: 14 }, (_, i) => dogrula(env, `p${i}@example.com`, '123456', IP(120))));
    assert.equal(sonuclar.filter((x) => x.durum === 400).length, 10);
    assert.equal(sonuclar.filter((x) => x.durum === 429).length, 4);
    assert.equal(satir(env, "SELECT n FROM eposta_sayac WHERE tur = 'dogrula_ip'").n, 14);
  } finally { a.geri(); }
});

// ---------- O1: kalıcı hedef bütçesi ----------
test('O1: hedef başına günde 20 yanlış kod; yeni kod istemek bütçeyi sıfırlamaz; başka hedef etkilenmez; gün dönünce açılır', async () => {
  const env = ortamE(); const a = ag();
  try {
    let yanlisSayisi = 0;
    for (let tur = 0; tur < 5; tur++) {
      ipSinirSifirla(); gerisar(env); calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'eposta_adres'");
      assert.equal((await kodIste(env, 'butce@example.com', {}, IP(130 + tur))).durum, 200);
      const kod = sonKod(a); const yanlis = kod === '333333' ? '444444' : '333333';
      for (let i = 0; i < 4; i++) {
        calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'dogrula_ip'"); ipSinirSifirla();
        assert.equal((await dogrula(env, 'butce@example.com', yanlis, IP(140 + tur))).durum, 400); yanlisSayisi++;
      }
    }
    assert.equal(yanlisSayisi, 20);
    // 21. deneme: taze kod ve DOĞRU kod bile reddedilir
    ipSinirSifirla(); gerisar(env); calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'eposta_adres'");
    assert.equal((await kodIste(env, 'butce@example.com', {}, IP(150))).durum, 200);
    calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'dogrula_ip'"); ipSinirSifirla();
    const r = await dogrula(env, 'butce@example.com', sonKod(a), IP(150));
    assert.equal(r.durum, 429); assert.match(r.json.hata, /bugünlük deneme hakkı/);
    // başka adres etkilenmez
    ipSinirSifirla(); gerisar(env);
    await kodIste(env, 'baska.butce@example.com', {}, IP(151));
    assert.equal((await dogrula(env, 'baska.butce@example.com', sonKod(a), IP(151))).durum, 200);
    // başarılı doğrulama hedef hakkını geri verir (meşru kullanıcı bütçeyi tüketmez)
    assert.equal(sayac(env, 'hata_hedef').filter((x) => x.n === 0).length, 1);
    // gün döndü
    calistir(env, "UPDATE eposta_sayac SET dilim = dilim - 1 WHERE tur = 'hata_hedef'");
    calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'dogrula_ip'"); ipSinirSifirla();
    assert.equal((await dogrula(env, 'butce@example.com', sonKod(a), IP(152))).durum, 400);   // bütçe açık (kod bu kez 20+ sonra yanmış/yanlış adres)
  } finally { a.geri(); }
});

// ---------- M2a: üretimde Turnstile şart ----------
test('M2a: üretimde e-posta girişi Turnstile (site + gizli anahtar) olmadan kapalı; açıkken kod isteği, sıfırlama ve /ben/eposta geçerli jeton ister', async () => {
  const kapaliler = [{ BREVO_ANAHTARI: 'x' }, { BREVO_ANAHTARI: 'x', TURNSTILE_GIZLI: 'g' }, { BREVO_ANAHTARI: 'x', TURNSTILE_SITE: 's' }, { TURNSTILE_GIZLI: 'g', TURNSTILE_SITE: 's' }];
  for (const ek of kapaliler) {
    const e = ortam(ek);
    assert.equal((await cagir(e, 'GET', '/giris/ayar')).json.eposta, false, JSON.stringify(ek));
    assert.equal((await kodIste(e, 'a@example.com')).durum, 503);
  }
  const env = ortam({ BREVO_ANAHTARI: 'x', TURNSTILE_GIZLI: 'g', TURNSTILE_SITE: 's' });   // ORTAM yok = üretim
  assert.equal((await cagir(env, 'GET', '/giris/ayar')).json.eposta, true);
  const a = ag();
  const tf = sahteFetch(async (url, s) => {
    if (url === BREVO) { a.posta.push(JSON.parse(s.body)); return new Response('{}', { status: 201 }); }
    if (url.startsWith('https://challenges.cloudflare.com/')) return new Response(JSON.stringify({ success: String(s.body).includes('response=iyi'), hostname: 'kpsstercihi.com' }), { status: 200 });
    return new Response('yok', { status: 404 });
  });
  try {
    const k = await uyeGirisi(env, 'Robot_Uye');
    await cagir(env, 'POST', '/kayit', { govde: { rumuz: 'Robot_Sifre', sifre: SIFRE, turnstile: 'iyi' } });
    calistir(env, "UPDATE uyeler SET eposta = 'robot@example.com', eposta_dogrulandi = 1 WHERE rumuz = 'Robot_Sifre'");
    for (const [yol, govde, token] of [
      ['/giris/eposta/kod', { eposta: 'r@example.com' }, undefined],
      ['/sifre-sifirla/eposta', { rumuz: 'Robot_Sifre' }, undefined],
      ['/ben/eposta', { eposta: 'r2@example.com' }, k.token],
    ]) {
      const onceki = a.posta.length;
      ipSinirSifirla(); calistir(env, "DELETE FROM eposta_sayac WHERE tur = 'gonder_ip'"); calistir(env, "DELETE FROM giris_denemeleri WHERE tur = 'sifirla_istek'");
      assert.equal((await cagir(env, 'POST', yol, { govde, token, basliklar: IP(160) })).durum, 400, `${yol}: jetonsuz`);
      assert.equal((await cagir(env, 'POST', yol, { govde: { ...govde, turnstile: 'kotu' }, token, basliklar: IP(160) })).durum, 400, `${yol}: geçersiz jeton`);
      assert.equal(a.posta.length, onceki);   // jetonsuz ya da geçersiz jetonla hiçbir e-posta gitmedi
      const ok = await cagir(env, 'POST', yol, { govde: { ...govde, turnstile: 'iyi' }, token, basliklar: IP(160) });
      assert.equal(ok.durum, 200, `${yol}: geçerli jeton`);
    }
    assert.equal(a.posta.length, 3);
  } finally { tf.geri(); a.geri(); }
});

// ---------- M2d: kota yedeği ----------
test('M2d: kalan kota 60\'ın altındayken hesabı olmayan adrese giriş kodu gönderilmez (yanıt aynı), mevcut üyelere giriş ve sıfırlama kodu gider', async () => {
  const env = ortamE(); const a = ag();
  try {
    const m = await epostaylaGir(env, a, 'mevcut@example.com', 'Mevcut_Uye');
    await sifreliUye(env, 'Sifre_Var', 'sifrevar@example.com');
    calistir(env, 'UPDATE eposta_gunluk SET n = 230 WHERE gun = ?', bugun());   // kalan 50 < 60
    const onceki = a.posta.length;
    ipSinirSifirla(); gerisar(env);
    const var_ = await kodIste(env, 'mevcut@example.com', {}, IP(170));
    const yok = await kodIste(env, 'yeni.kisi@example.com', {}, IP(171));
    assert.equal(var_.durum, 200); assert.deepEqual(var_.json, yok.json);   // sızmaz
    assert.equal(a.posta.length, onceki + 1); assert.deepEqual(a.posta[onceki].to, [{ email: 'mevcut@example.com' }]);
    assert.equal(satir(env, 'SELECT n FROM eposta_gunluk WHERE gun = ?', bugun()).n, 231);   // hesapsız adres kota harcamadı
    // bekleme davranışı da aynı (hesapsız adres için de 60 sn)
    const v2 = await kodIste(env, 'mevcut@example.com', {}, IP(170)); const y2 = await kodIste(env, 'yeni.kisi@example.com', {}, IP(171));
    assert.equal(v2.durum, 429); assert.equal(y2.durum, 429);
    // hesapsız adrese giden "kod" yok: doğrulama hiçbir kodla geçmez
    assert.equal((await dogrula(env, 'yeni.kisi@example.com', '000000', IP(172))).durum, 400);
    // şifre sıfırlama kota yedeğinden etkilenmez
    ipSinirSifirla();
    assert.equal((await sifirlaIste(env, { rumuz: 'Sifre_Var' }, IP(173))).durum, 200);
    assert.equal(a.posta.length, onceki + 2); assert.deepEqual(a.posta[onceki + 1].to, [{ email: 'sifrevar@example.com' }]);
    // yedek bitince (kalan >= 60) yeni adreslere yine gönderilir
    calistir(env, 'UPDATE eposta_gunluk SET n = 100 WHERE gun = ?', bugun());
    ipSinirSifirla(); gerisar(env);
    assert.equal((await kodIste(env, 'yeni.kisi@example.com', {}, IP(174))).durum, 200);
    assert.equal(a.posta.length, onceki + 3);
    assert.ok(m);
  } finally { a.geri(); }
});

// ---------- N2: silinen üyenin özel mesajları karşı tarafta kalır ----------
test('N2: silinen üyenin gönderdiği özel mesajlar karşı tarafın listesinde "Silinmiş üye #id" adıyla kalır', async () => {
  const env = ortamE();
  const a = await uyeGirisi(env, 'Mesaj_Atan'); const b = await uyeGirisi(env, 'Mesaj_Alan');
  kayitEskit(env, a.id); kayitEskit(env, b.id);
  const g = await cagir(env, 'POST', '/ozel/Mesaj_Alan', { token: a.token, govde: { govde: 'Selam, bir sorum var.' } });
  assert.equal(g.durum, 201);
  assert.equal((await cagir(env, 'POST', '/ben/hesap-sil', { token: a.token, govde: { onay: 'SİL' } })).durum, 200);
  const liste = await cagir(env, 'GET', '/ozel', { token: b.token });
  assert.equal(liste.durum, 200);
  assert.equal(liste.json.konusmalar.length, 1);
  assert.equal(liste.json.konusmalar[0].rumuz, `Silinmiş üye #${a.id}`);
  assert.equal(JSON.stringify(liste.json).includes('Mesaj_Atan'), false);
});

test('N4: yönetici engel kaldırma silinmiş üyeye dokunmaz (engelli=1 kalır)', async () => {
  const env = ortamE();
  const u = await uyeGirisi(env, 'Silinen_Yok');
  await cagir(env, 'POST', '/ben/hesap-sil', { token: u.token, govde: { onay: 'SİL' } });
  const r = await cagir(env, 'POST', '/yonetim/engelle', { govde: { uye_id: u.id, engelli: false }, basliklar: { 'X-Yonetici': 'yonetici-anahtar' } });
  assert.equal(r.durum, 200);
  assert.equal(satir(env, 'SELECT engelli FROM uyeler WHERE id = ?', u.id).engelli, 1);
});
