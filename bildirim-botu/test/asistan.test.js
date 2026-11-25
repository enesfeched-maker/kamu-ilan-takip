import { test } from 'node:test';
import assert from 'node:assert/strict';
import { asistanIstek, cevapla, katla, govdeKok, yzDogrula, testSifirla, IL_SAYISI, bulunmaEki, basHarfBuyuk } from '../src/asistan.js';
import worker from '../src/index.js';

const SIMDI = new Date('2026-11-25T09:00:00Z');
const SITE = 'https://kpsstercihi.com/';

const ilan = (id, ek) => ({
  id, baslik: 'Ilan', kurum: 'Kurum', son_tarih: '2026-12-10', son_zaman: null, ogrenim: [], iller: [], kategori: null, kpss: 'kpss',
  sayfa: `${SITE}ilan/${id}/`, metin: '', ...ek,
});
const ILANLAR = [
  ilan('a1', { baslik: 'Ankara Büyükşehir Belediyesi — Zabıta Memuru', kurum: 'Ankara Büyükşehir Belediyesi', iller: ['Ankara'], ogrenim: ['ortaogretim', 'onlisans'], son_tarih: '2026-12-01', kategori: 'belediye', metin: 'ankara büyükşehir belediyesi zabıta memuru' }),
  ilan('a2', { baslik: 'İzmir Büyükşehir Belediyesi — Hemşire', kurum: 'İzmir Büyükşehir Belediyesi', iller: ['İzmir'], ogrenim: ['lisans', 'onlisans'], son_tarih: '2026-12-05', kategori: 'belediye', metin: 'izmir büyükşehir belediyesi hemşire' }),
  ilan('a3', { baslik: 'Ankara Üniversitesi — Kamu İşçi Alımı', kurum: 'Ankara Üniversitesi Genel Daire', iller: ['Ankara'], kpss: 'kpsssiz', kategori: 'isci', metin: 'ankara üniversitesi kamu işçi alımı' }),
  ilan('a4', { baslik: 'Ankara Zabıta Memuru (süresi geçti)', kurum: 'Ankara Çankaya Belediyesi', iller: ['Ankara'], ogrenim: ['ortaogretim'], son_tarih: '2026-11-20', son_zaman: '2026-11-20T17:00:00+03:00', metin: 'ankara çankaya belediyesi zabıta memuru' }),
  ilan('a5', { baslik: 'Ankara Üniversitesi Öğretim Görevlisi', kurum: 'Ankara Üniversitesi', iller: ['Ankara'], kategori: 'akademik', ogrenim: ['lisans'], son_tarih: '2026-12-20', metin: 'ankara üniversitesi öğretim görevlisi' }),
  ilan('a6', { baslik: 'İstanbul Büyükşehir Belediyesi — İtfaiye Eri', kurum: 'İstanbul Büyükşehir Belediyesi', iller: ['İstanbul'], ogrenim: ['ortaogretim'], son_tarih: '2026-12-15', kategori: 'belediye', metin: 'istanbul büyükşehir belediyesi itfaiye eri' }),
  ilan('a7', { baslik: 'Konya Büyükşehir Belediyesi — Zabıta Memuru', kurum: 'Konya Büyükşehir Belediyesi', iller: ['Konya'], ogrenim: ['ortaogretim', 'onlisans'], son_tarih: '2026-12-03', kategori: 'belediye', metin: 'konya büyükşehir belediyesi zabıta memuru' }),
  // Bugün biten ama saati geçmiş: son_zaman 07:00Z, şimdi 09:00Z.
  ilan('a8', { baslik: 'Ankara Belediyesi — Mühendis (saati geçti)', kurum: 'Ankara Belediyesi', iller: ['Ankara'], ogrenim: ['lisans'], son_tarih: '2026-11-25', son_zaman: '2026-11-25T10:00:00+03:00', metin: 'ankara belediyesi mühendis' }),
  ilan('a9', { baslik: 'Ankara Büyükşehir Belediyesi — Mühendis', kurum: 'Ankara Büyükşehir Belediyesi', iller: ['Ankara'], ogrenim: ['lisans'], son_tarih: '2026-12-08', kategori: 'belediye', metin: 'ankara büyükşehir belediyesi mühendis' }),
];

const BILGI = {
  surum: 1,
  sss: [
    { s: 'KPSS Tercihi nedir?', c: 'KPSS Tercihi, kamu kurumlarının personel alım ilanlarını resmî kaynaklardan toplayıp tek listede gösteren ücretsiz bir sitedir.', u: `${SITE}sss/` },
    { s: 'Site ücretli mi, üyelik gerekiyor mu?', c: 'Hayır. Site tamamen ücretsizdir ve üyelik gerekmez.', u: `${SITE}sss/` },
    { s: 'İlanlar ne sıklıkla güncellenir?', c: 'Kaynaklar gün boyunca yaklaşık 30 dakikada bir taranır. Yeni ilan olduğunda liste kendiliğinden güncellenir.', u: `${SITE}sss/` },
    { s: 'Başvuruyu KPSS Tercihi üzerinden mi yapıyorum?', c: 'Hayır. Her ilan sayfasında kurumun resmî başvuru bağlantısı bulunur; başvuru kurumun belirttiği yerden yapılır.', u: `${SITE}sss/` },
    { s: 'KPSS taban puanlarına nereden bakabilirim?', c: 'Taban puanları sayfasında lisans, önlisans ve ortaöğretim kadrolarının dönem dönem en düşük ve en yüksek puanları yer alır.', u: `${SITE}kpss-taban-puanlari/` },
    { s: 'Kariyer Kapısı’na nasıl giriş yapılır?', c: 'kariyerkapisi.gov.tr adresine git, giriş bölümünden e-Devlet ile doğrulama yap. Ayrı bir üyelik açman gerekmez.', u: `${SITE}rehber/kariyer-kapisi-basvuru/` },
    { s: 'Zabıtada yaş sınırı kaç?', c: 'Zabıta memuru ilanlarında “sınavın yapıldığı tarihte 30 yaşını doldurmamış olmak” şartı aranır.', u: `${SITE}meslek/zabita-memuru/` },
    { s: 'Zabıta olmak için boy ve kilo şartı var mı?', c: 'Boy erkeklerde 1,67 metre, kadınlarda 1,60 metreden kısa olmamalı. İlanda farklı bir şart yazıyorsa ilan geçerlidir.', u: `${SITE}meslek/zabita-memuru/` },
    { s: 'Telegram kanalına nasıl katılırım?', c: 'Yeni ilanlar Telegram kanalımızda anında paylaşılır; kanalın adı kpsstercihi.', u: 'https://t.me/kpsstercihi' },
    { s: 'ÖSYM üzerinden iş başvurusu nasıl yapılır?', c: 'ÖSYM yalnızca merkezi yerleştirmeyi yürütür. Kurumların kendi ilanlarına ÖSYM’den başvurulmaz.', u: `${SITE}rehber/kariyer-kapisi-basvuru/` },
  ],
  meslekler: [
    { ad: 'Zabıta Memuru', u: `${SITE}meslek/zabita-memuru/`, kelimeler: ['zabita', 'zabita memuru'] },
    { ad: 'İtfaiye Eri', u: `${SITE}meslek/itfaiye-eri/`, kelimeler: ['itfaiye', 'itfaiyeci', 'itfaiye eri'] },
    { ad: 'Hemşire', u: `${SITE}meslek/hemsire/`, kelimeler: ['hemsire'] },
    { ad: 'Mühendis', u: `${SITE}meslek/muhendis/`, kelimeler: ['muhendis'] },
    { ad: 'Memur', u: `${SITE}meslek/memur/`, kelimeler: ['memur'] },
    { ad: 'Veri Hazırlama ve Kontrol İşletmeni', u: `${SITE}meslek/veri-hazirlama-ve-kontrol-isletmeni/`, kelimeler: ['vhki', 'veri hazirlama'] },
  ],
  sayfalar: [{ ad: 'Bana uygun ilanlar', u: `${SITE}nereye/`, kelimeler: ['puanimla'] }],
};
const VERI = { site: SITE, ilanlar: ILANLAR, bilgi: BILGI };
const VERI_BOS = { site: SITE, ilanlar: [], bilgi: null };

const q = (soru, veri = VERI, sayfa = '') => cevapla(soru, veri, SIMDI, sayfa);
const idler = (c) => c.ilanlar.map((i) => i.url.split('/').filter(Boolean).pop());
const linkler = (c) => c.baglantilar.map((b) => b.url);

// -------------------------------------------------------------- altın set

// [soru, tur, { link, ilan (hepsi gelmeli), tam (yalnız bunlar), yok (hiçbiri gelmemeli), metin }]
const ALTIN = [
  // kimlik
  ['insan mısın?', 'kimlik'],
  ['bot musun', 'kimlik'],
  ['sen bir yapay zeka mısın', 'kimlik'],
  ['kimsin sen', 'kimlik'],
  ['gerçek kişi misin', 'kimlik'],
  ['ROBOT MUSUN', 'kimlik'],
  ['insan misin yoksa bot mu', 'kimlik'],
  // selam / teşekkür
  ['merhaba', 'selam'],
  ['selam', 'selam'],
  ['slm', 'selam'],
  ['günaydın', 'selam'],
  ['iyi akşamlar', 'selam'],
  ['naber', 'selam'],
  ['teşekkürler', 'tesekkur'],
  ['eyvallah', 'tesekkur'],
  ['sağ ol', 'tesekkur'],
  ['çok teşekkür ederim', 'tesekkur'],
  ['sagol', 'tesekkur'],
  // puan
  ['kpss 65 le nereye girerim', 'puan', { link: 'nereye/' }],
  ['önlisans p93 70 puan yeter mi', 'puan', { link: 'kpss-taban-puanlari/onlisans/' }],
  ['65 puanla ne olur', 'puan', { link: 'nereye/' }],
  ['puanım 80 hangi kadrolara girerim', 'puan', { link: 'nereye/' }],
  ['lisans p3 75 puanım var', 'puan', { link: 'kpss-taban-puanlari/lisans/' }],
  ['kaç puanla zabıta olunur', 'puan', { link: 'meslek/zabita-memuru/' }],
  ['70 kpss puani ile nereye basvurabilirim', 'puan', { link: 'nereye/' }],
  ['ortaöğretim 68 puan yeter mi', 'puan', { link: 'kpss-taban-puanlari/ortaogretim/' }],
  ['kpss 55 puanla memur olunur mu', 'puan', { link: 'meslek/memur/' }],
  ['puanımla ankarada ne var', 'puan', { link: 'nereye/' }],
  ['yeter mi 72 puan', 'puan'],
  ['KPSS 82,5 ile girilir mi', 'puan'],
  ['ön lisans 70 puan yeter mi', 'puan', { link: 'kpss-taban-puanlari/onlisans/' }],
  ['p94 ile 60 puanım var', 'puan', { link: 'kpss-taban-puanlari/ortaogretim/' }],
  // ilan
  ['ankarada zabıta alımı varmı', 'ilan', { tam: ['a1'], yok: ['a4'], link: 'meslek/zabita-memuru/' }],
  ['ankara zabita ilani', 'ilan', { tam: ['a1'], yok: ['a4'] }],
  ['Ankara Zabıta ilanı var mı?', 'ilan', { tam: ['a1'] }],
  ['izmir hemşire ilanı', 'ilan', { tam: ['a2'], link: 'meslek/hemsire/' }],
  ['izmirde hemsire alimi', 'ilan', { tam: ['a2'] }],
  ['kpsssiz işçi alımı', 'ilan', { tam: ['a3'] }],
  ['kpss şartsız ilanlar', 'ilan', { tam: ['a3'] }],
  ['konya zabıta var mı', 'ilan', { tam: ['a7'] }],
  ['istanbul itfaiye', 'ilan', { tam: ['a6'], link: 'meslek/itfaiye-eri/' }],
  ['itfaiye alımı', 'ilan', { tam: ['a6'] }],
  ['mühendis ilanı', 'ilan', { tam: ['a9'], yok: ['a8'] }],
  ['ankara mühendis alımı', 'ilan', { tam: ['a9'], yok: ['a8'] }],
  ['lisans ilanları', 'ilan', { ilan: ['a2', 'a9'], yok: ['a1', 'a4', 'a5'] }],
  ['ortaöğretim ilanı', 'ilan', { tam: ['a1', 'a7', 'a6'] }],
  ['önlisans zabıta ilanı', 'ilan', { tam: ['a1', 'a7'] }],
  ['ankara ilanları', 'ilan', { ilan: ['a1', 'a3', 'a9'], yok: ['a4', 'a5', 'a8'] }],
  ['ankara akademik ilan', 'ilan', { yok: ['a5'] }],
  ['izmir büyükşehir belediyesi ilanı', 'ilan', { tam: ['a2'] }],
  ['bursa zabıta alımı var mı', 'ilan', { tam: [], metin: /göremiyorum/, link: 't.me/kpsstercihi' }],
  ['van hemşire ilanı', 'ilan', { tam: [], metin: /göremiyorum/ }],
  ['ilan var mı', 'ilan', { tam: [], link: 'nereye/' }],
  ['açık ilanlar', 'ilan', { tam: [] }],
  ['hatay itfaiye ilani var mi', 'ilan', { tam: [] }],
  // sss
  ['kariyer kapısına nasıl girilir', 'sss', { link: 'rehber/kariyer-kapisi-basvuru/', metin: /e-Devlet/ }],
  ['site ücretli mi', 'sss', { metin: /ücretsiz/ }],
  ['üyelik gerekiyor mu', 'sss'],
  ['ilanlar ne sıklıkla güncelleniyor', 'sss', { metin: /30 dakika/ }],
  ['taban puanlarına nereden bakabilirim', 'sss', { link: 'kpss-taban-puanlari/' }],
  ['zabıtada yaş sınırı kaç', 'sss', { link: 'meslek/zabita-memuru/', metin: /30 yaşını/ }],
  ['zabıta boy kilo şartı', 'sss', { metin: /1,67/ }],
  ['telegram kanalına nasıl katılırım', 'sss', { link: 't.me/kpsstercihi' }],
  ['osym uzerinden basvuru nasil yapilir', 'sss'],
  ['kpss tercihi nedir', 'sss'],
  ['başvuruyu buradan mı yapıyorum', 'sss'],
  // bilinmiyor
  ['asdfgh', 'bilinmiyor', { link: 'sss/' }],
  ['hava durumu nasıl', 'bilinmiyor'],
  ['bugün ne yesem', 'bilinmiyor'],
  ['pizza siparişi vermek istiyorum', 'bilinmiyor'],
  ['xyz', 'bilinmiyor', { link: 't.me/kpsstercihi' }],
  ['futbol maçı kaçta', 'bilinmiyor'],
  ['qwerty zxcv', 'bilinmiyor'],
];

test('altın set en az 60 soru içerir', () => assert.ok(ALTIN.length >= 60, String(ALTIN.length)));

for (const [soru, tur, bek = {}] of ALTIN) {
  test(`altın: "${soru}" -> ${tur}`, () => {
    const c = q(soru);
    assert.equal(c.tur, tur, JSON.stringify(c));
    // Her cevapta ortak güvenceler.
    assert.ok(c.metin && c.metin.length > 10);
    assert.ok(c.baglantilar.length <= 3 && c.ilanlar.length <= 5 && c.oneriler.length <= 3);
    for (const b of c.baglantilar) assert.match(b.url, /^https:\/\/(kpsstercihi\.com\/|t\.me\/)/);
    for (const i of c.ilanlar) assert.match(i.url, /^https:\/\/kpsstercihi\.com\//);
    assert.ok(!/\bvb\.|\bvs\./.test(c.metin));
    const ids = idler(c);
    for (const yasak of ['a4', 'a5', 'a8']) assert.ok(!ids.includes(yasak), `süresi geçmiş/akademik ilan çıktı: ${yasak}`);
    if (bek.link) assert.ok(linkler(c).some((u) => u.includes(bek.link)), `bağlantı yok: ${bek.link} / ${linkler(c)}`);
    if (bek.ilan) for (const id of bek.ilan) assert.ok(ids.includes(id), `ilan yok: ${id} / ${ids}`);
    if (bek.tam) assert.deepEqual([...ids].sort(), [...bek.tam].sort());
    if (bek.yok) for (const id of bek.yok) assert.ok(!ids.includes(id), `olmaması gereken ilan: ${id}`);
    if (bek.metin) assert.match(c.metin, bek.metin);
    if (tur === 'puan') {
      assert.equal(c.ilanlar.length, 0);
      assert.ok(linkler(c).some((u) => u.endsWith('/nereye/')));
      assert.doesNotMatch(c.metin, /yeterli|yeterlidir|girersin|kazanırsın/);
    }
  });
}

test('ilanlar son tarihe göre artan sıralanır ve en çok 5 tane gelir', () => {
  const cok = Array.from({ length: 8 }, (_, n) => ilan(`z${n}`, { baslik: `Ankara Memur ${n}`, metin: `ankara memur ${n}`, iller: ['Ankara'], son_tarih: `2026-12-${String(20 - n).padStart(2, '0')}` }));
  const c = q('ankara memur ilanı', { ...VERI, ilanlar: cok });
  assert.equal(c.ilanlar.length, 5);
  const t = c.ilanlar.map((i) => i.son_tarih);
  assert.deepEqual(t, [...t].sort());
  assert.match(c.metin, /8 ilan/);
});

test('süresi saatiyle geçmiş ilan hiçbir sorguda çıkmaz', () => {
  for (const s of ['ankara mühendis', 'ankara zabıta', 'ankara ilanları', 'lisans ilanları', 'mühendis alımı var mı']) {
    const ids = idler(q(s));
    assert.ok(!ids.includes('a8') && !ids.includes('a4') && !ids.includes('a5'), `${s}: ${ids}`);
  }
});

test('il listesi 81 ilden oluşur ve ek almış hâlleri tanır', () => {
  assert.equal(IL_SAYISI, 81);
  assert.deepEqual(idler(q('konyada zabıta')), ['a7']);
  assert.deepEqual(idler(q('Konya’daki zabıta ilanları')), ['a7']);
});

test('meslek sayfası bağlamı: sayfa /meslek/zabita-memuru/ iken "ilan var mı" zabıta için bakar', () => {
  const c = q('ilan var mı', VERI, '/meslek/zabita-memuru/');
  assert.equal(c.tur, 'ilan');
  assert.deepEqual([...idler(c)].sort(), ['a1', 'a7']);
});

test('uzun sorulardaki rastgele sayı puan sayılmaz (yaş, tarih)', () => {
  assert.notEqual(q('2026 yılında kaç kişi alınacak').tur, 'puan');
  assert.notEqual(q('zabıta için 30 yaşında olabilir miyim').tur, 'puan');
});

test('veri hiç yokken kimlik, selam, puan ve bilinmiyor yine cevaplanır', () => {
  assert.equal(q('bot musun', VERI_BOS).tur, 'kimlik');
  assert.equal(q('merhaba', VERI_BOS).tur, 'selam');
  assert.equal(q('kpss 70 ile nereye girerim', VERI_BOS).tur, 'puan');
  assert.equal(q('asdfgh', VERI_BOS).tur, 'bilinmiyor');
  const c = q('ankara zabıta ilanı var mı', VERI_BOS);
  assert.equal(c.ilanlar.length, 0);
});

test('kimlik cevabı dürüsttür: otomatik asistan der, insan olduğunu söylemez', () => {
  for (const s of ['insan mısın', 'bot musun', 'yapay zeka mısın', 'kimsin', 'gerçek kişi misin']) {
    const c = q(s);
    assert.match(c.metin, /otomatik asistan/);
    assert.doesNotMatch(katla(c.metin), /insanim|gercek kisiyim/);
  }
});

test('stil: şablon cevaplarda vb. yok, emoji yok, bağlantı alanı mutlak', () => {
  for (const [s] of ALTIN) {
    const c = q(s);
    assert.ok(!/vb\.|vs\./.test(c.metin), s);
    assert.ok(!/[\u{1F300}-\u{1FAFF}]/u.test(c.metin), s);
  }
});

test('Türkçe katlama ve kök bulma', () => {
  assert.equal(katla('İSTANBUL Iğdır Şanlıurfa ÇANKIRI'), 'istanbul igdir sanliurfa cankiri');
  assert.equal(govdeKok('ilanlari'), 'ilan');
  assert.equal(govdeKok('ankarada'), 'ankara');
  assert.equal(govdeKok('ay'), 'ay');
});

// -------------------------------------------------------------- yapay zekâ doğrulaması

test('yzDogrula: uydurma sayı, bağlantı, yasak ifade, uzunluk ve yabancı yazıyı reddeder', () => {
  const g = 'Şu an Ankara için 2 ilan buldum. Son tarih 2026-12-01.';
  assert.ok(yzDogrula('Ankara için şu an 2 ilan var, son tarih 2026-12-01.', g));
  assert.equal(yzDogrula('Ankara için şu an 5 ilan var.', g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var, bak: https://example.com', g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var, kpsstercihi.com sayfasına bak.', g), null);
  assert.equal(yzDogrula('Ben bir yapay zekâ olarak 2 ilan buldum.', g), null);
  assert.equal(yzDogrula('Ben bir dil modeli olarak 2 ilan buldum.', g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var vb. şeyler de var.', g), null);
  assert.equal(yzDogrula('kısa', g), null);
  assert.equal(yzDogrula('a'.repeat(501), g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var 你好，欢迎来到这里', g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var 🙂 bakabilirsin', g), null);
  assert.equal(yzDogrula(null, g), null);
  // sayıyı yazıyla, ay adını ya da "yarın"ı uydurmak; insan olduğunu söylemek
  assert.equal(yzDogrula('Ankara için şu an beş ilan var, haberin olsun.', g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var, son gün 1 Ocak.', g), null);
  assert.equal(yzDogrula('Ankara için 2 ilan var, yarın son günü.', g), null);
  assert.equal(yzDogrula('Ben gerçek bir insan olarak 2 ilan buldum.', g), null);
});

test('HTTP: sınırı aşan gövde JSON çözülmeden 400', async () => {
  testSifirla(); sahteFetch();
  const r = await asistanIstek(istek(JSON.stringify({ soru: 'x', dolgu: 'a'.repeat(5000) })), ENV, {});
  assert.equal(r.status, 400);
  globalThis.fetch = gercekFetch;
});

// -------------------------------------------------------------- HTTP katmanı

let ip = 0;
const yeniIp = () => `10.0.0.${++ip}`;
const istek = (govde, ek = {}) => new Request('https://w.test/asistan/sor', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'CF-Connecting-IP': ek.ip || yeniIp(), ...(ek.origin ? { Origin: ek.origin } : {}) },
  body: typeof govde === 'string' ? govde : JSON.stringify(govde),
});
const ENV = { ILAN_URL: 'https://x.test/bot-ilanlar.json', SITE_URL: SITE };

// HTTP katmanı gerçek saati (new Date()) kullanır: tarih bombası olmasın diye ilan tarihleri SIMDI'den bugüne kaydırılır.
function buguneKaydir(ilanlar) {
  const fark = Math.round((Date.now() - SIMDI.getTime()) / 86400000) * 86400000;
  const kay = (s, n) => new Date(Date.parse(s) + fark).toISOString().slice(0, n);
  return ilanlar.map((i) => ({ ...i,
    son_tarih: i.son_tarih ? kay(`${i.son_tarih}T12:00:00Z`, 10) : i.son_tarih,
    son_zaman: i.son_zaman ? new Date(Date.parse(i.son_zaman) + fark).toISOString() : i.son_zaman }));
}

function sahteFetch(sayac = { n: 0 }) {
  globalThis.fetch = async (u) => {
    sayac.n++;
    const url = String(u);
    if (url.includes('bot-ilanlar')) return new Response(JSON.stringify({ guncelleme: 'x', ilanlar: buguneKaydir(ILANLAR) }), { status: 200 });
    if (url.includes('asistan/bilgi.json')) return new Response(JSON.stringify(BILGI), { status: 200 });
    return new Response('yok', { status: 404 });
  };
  return sayac;
}
const gercekFetch = globalThis.fetch;

async function sor(soru, env = ENV, ek = {}) {
  const r = await asistanIstek(istek({ soru }, ek), env, { waitUntil() {} });
  return { r, j: await r.json() };
}

test('HTTP: 200 cevap sözleşmeye uyar, "tur" dışarı sızmaz', async () => {
  testSifirla(); sahteFetch();
  const { r, j } = await sor('ankarada zabıta alımı varmı', ENV, { origin: 'https://kpsstercihi.com' });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.equal(r.headers.get('Vary'), 'Origin');
  assert.deepEqual(Object.keys(j).sort(), ['baglantilar', 'ilanlar', 'metin', 'oneriler']);
  assert.deepEqual(j.ilanlar.map((i) => i.url), [`${SITE}ilan/a1/`]);
  assert.deepEqual(Object.keys(j.ilanlar[0]).sort(), ['baslik', 'iller', 'kurum', 'son_tarih', 'url']);
  globalThis.fetch = gercekFetch;
});

test('HTTP: veri 10 dakika bellekte tutulur (ikinci istek yeniden çekmez)', async () => {
  testSifirla();
  const sayac = sahteFetch();
  await sor('merhaba');
  const ilk = sayac.n;
  assert.equal(ilk, 2);
  await sor('ankara zabıta ilanı');
  assert.equal(sayac.n, ilk);
  globalThis.fetch = gercekFetch;
});

test('HTTP: veri çekilemezse de kimlik cevaplanır', async () => {
  testSifirla();
  globalThis.fetch = async () => { throw new Error('ağ yok'); };
  const { r, j } = await sor('bot musun');
  assert.equal(r.status, 200);
  assert.match(j.metin, /otomatik asistan/);
  const b = await sor('ankara zabıta ilanı var mı');
  assert.equal(b.r.status, 200);
  assert.deepEqual(b.j.ilanlar, []);
  globalThis.fetch = gercekFetch;
});

test('HTTP: CORS ön uçuş, izinli ve izinsiz köken', async () => {
  testSifirla();
  const pre = (origin) => asistanIstek(new Request('https://w.test/asistan/sor', { method: 'OPTIONS', headers: { Origin: origin } }), ENV, {});
  for (const o of ['https://kpsstercihi.com', 'https://www.kpsstercihi.com', 'http://localhost:8788', 'http://127.0.0.1:5500']) {
    const r = await pre(o);
    assert.equal(r.status, 204);
    assert.equal(r.headers.get('Access-Control-Allow-Origin'), o);
    assert.match(r.headers.get('Access-Control-Allow-Methods'), /POST/);
    assert.equal(r.headers.get('Vary'), 'Origin');
  }
  const kotu = await pre('https://kotu.example.com');
  assert.equal(kotu.headers.get('Access-Control-Allow-Origin'), null);
  sahteFetch();
  const r = await asistanIstek(istek({ soru: 'merhaba' }, { origin: 'https://kotu.example.com' }), ENV, {});
  assert.equal(r.status, 403);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), null);
  globalThis.fetch = gercekFetch;
});

test('HTTP: yalnız POST/OPTIONS; boş, bozuk ve aşırı uzun soru 400', async () => {
  testSifirla(); sahteFetch();
  const get = await asistanIstek(new Request('https://w.test/asistan/sor'), ENV, {});
  assert.equal(get.status, 405);
  assert.equal((await sor('')).r.status, 400);
  assert.equal((await sor('   \n\t ')).r.status, 400);
  assert.equal((await asistanIstek(istek('{bozuk'), ENV, {})).status, 400);
  assert.equal((await asistanIstek(istek({ soru: 5 }), ENV, {})).status, 400);
  assert.equal((await asistanIstek(istek({}), ENV, {})).status, 400);
  assert.equal((await sor('a '.repeat(2000))).r.status, 400);
  const yol = await asistanIstek(new Request('https://w.test/asistan/baska', { method: 'POST', body: '{}' }), ENV, {});
  assert.equal(yol.status, 404);
  globalThis.fetch = gercekFetch;
});

test('HTTP: 300 karakteri aşan (ama makul) soru kısaltılır, kontrol karakterleri temizlenir', async () => {
  testSifirla(); sahteFetch();
  const { r } = await sor(`ankara\u0000 zabıta\u0007 ilanı ${'x'.repeat(350)}`);
  assert.equal(r.status, 200);
});

test('HTTP: IP başına 5 dakikada 12 istek, 13.sü 429', async () => {
  testSifirla(); sahteFetch();
  const ipx = '203.0.113.9';
  for (let n = 0; n < 12; n++) assert.equal((await sor('merhaba', ENV, { ip: ipx })).r.status, 200);
  const son = await sor('merhaba', ENV, { ip: ipx, origin: 'https://kpsstercihi.com' });
  assert.equal(son.r.status, 429);
  assert.equal(son.j.metin, 'Biraz hızlı gittik, bir dakika sonra tekrar sorabilirsin.');
  assert.equal(son.r.headers.get('Access-Control-Allow-Origin'), 'https://kpsstercihi.com');
  assert.equal((await sor('merhaba', ENV, { ip: '203.0.113.10' })).r.status, 200);
  globalThis.fetch = gercekFetch;
});

test('index.js: /asistan/ yolu asistana yönlenir', async () => {
  testSifirla(); sahteFetch();
  const r = await worker.fetch(istek({ soru: 'bot musun' }), ENV, { waitUntil() {} });
  assert.equal(r.status, 200);
  assert.match((await r.json()).metin, /otomatik asistan/);
  globalThis.fetch = gercekFetch;
});

// -------------------------------------------------------------- Workers AI

function yzEnv(calistir, ek = {}) {
  const cagrilar = [];
  return { env: { ...ENV, ...ek, AI: { run: async (model, girdi) => { cagrilar.push({ model, girdi }); return calistir(model, girdi); } } }, cagrilar };
}

test('YZ: iyi yeniden yazım kullanılır; bağlantılar ve ilanlar koddan gelir', async () => {
  testSifirla(); sahteFetch();
  const { env, cagrilar } = yzEnv(() => ({ response: 'Ankara için şu an 1 zabıta ilanı açık, şartlara resmî ilan metninden mutlaka bakmalısın.' }));
  const { j } = await sor('ankarada zabıta alımı varmı', env);
  assert.match(j.metin, /mutlaka bakmalısın/);
  assert.equal(cagrilar.length, 1);
  assert.equal(cagrilar[0].model, '@cf/meta/llama-3.3-70b-instruct-fp8-fast');
  assert.match(cagrilar[0].girdi.messages[0].content, /yalnızca verilen gerçekleri/i);
  assert.deepEqual(j.ilanlar.map((i) => i.url), [`${SITE}ilan/a1/`]);
  assert.ok(j.baglantilar.every((b) => b.url.startsWith(SITE)));
  globalThis.fetch = gercekFetch;
});

test('YZ: model adı ASISTAN_MODEL ile değişir', async () => {
  testSifirla(); sahteFetch();
  const { env, cagrilar } = yzEnv(() => ({ response: 'x' }), { ASISTAN_MODEL: '@cf/test/model' });
  await sor('ankara zabıta ilanı', env);
  assert.equal(cagrilar[0].model, '@cf/test/model');
  globalThis.fetch = gercekFetch;
});

for (const [ad, donus] of [
  ['uydurma sayı', { response: 'Ankara için şu an 7 zabıta ilanı açık, bakabilirsin.' }],
  ['bağlantı', { response: 'Ankara için bir zabıta ilanı açık, bak: https://evil.example.com/x' }],
  ['alan adı', { response: 'Ankara için bir zabıta ilanı açık, kpsstercihi.com sayfasına bakabilirsin.' }],
  ['"yapay zek"', { response: 'Bir yapay zekâ olarak Ankara için 1 zabıta ilanı buldum.' }],
  ['"dil modeli"', { response: 'Bir dil modeli olarak Ankara için 1 zabıta ilanı buldum.' }],
  ['vb.', { response: 'Ankara için 1 zabıta ilanı var vb. başka ilanlar da var.' }],
  ['çok kısa', { response: 'Var.' }],
  ['çok uzun', { response: `Ankara için 1 zabıta ilanı var. ${'Detaylı bilgi. '.repeat(60)}` }],
  ['yabancı yazı', { response: 'Ankara için 1 zabıta ilanı var 请看这里的详细信息谢谢' }],
  ['emoji', { response: 'Ankara için 1 zabıta ilanı var 🙂 bakabilirsin.' }],
  ['dize olmayan', { response: 42 }],
  ['boş', {}],
]) {
  test(`YZ: ${ad} -> şablon cevap kullanılır`, async () => {
    testSifirla(); sahteFetch();
    const sablon = (await sor('ankarada zabıta alımı varmı', { ...ENV, ASISTAN_YZ: '0' })).j.metin;
    const { env } = yzEnv(() => donus);
    const { j } = await sor('ankarada zabıta alımı varmı', env);
    assert.equal(j.metin, sablon);
    globalThis.fetch = gercekFetch;
  });
}

test('YZ: hata (kota dahil) ve zaman aşımı -> şablon cevap', async () => {
  testSifirla(); sahteFetch();
  const sablon = (await sor('site ücretli mi', ENV)).j.metin;
  const { env } = yzEnv(() => { throw new Error('4006: daily free allocation exceeded'); });
  assert.equal((await sor('site ücretli mi', env)).j.metin, sablon);
  const reddet = yzEnv(() => Promise.reject(new Error('kota')));
  assert.equal((await sor('site ücretli mi', reddet.env)).j.metin, sablon);
  globalThis.fetch = gercekFetch;
});

test('YZ: yalnız ilan/puan için çağrılır (sss metni olduğu gibi); ASISTAN_YZ=0 ile kapanır', async () => {
  testSifirla(); sahteFetch();
  const { env, cagrilar } = yzEnv(() => ({ response: 'Merhaba, hoş geldin, buradayım seni dinliyorum.' }));
  for (const s of ['merhaba', 'bot musun', 'teşekkürler', 'asdfgh', 'site ücretli mi']) await sor(s, env);
  assert.equal(cagrilar.length, 0);
  for (const s of ['ankara zabıta ilanı', 'kpss 65 ile nereye girerim']) await sor(s, env);
  assert.equal(cagrilar.length, 2);
  const kapali = yzEnv(() => ({ response: 'olmaz' }), { ASISTAN_YZ: '0' });
  await sor('ankara zabıta ilanı', kapali.env);
  assert.equal(kapali.cagrilar.length, 0);
  globalThis.fetch = gercekFetch;
});

test('YZ: kimlik cevabı hiçbir zaman modelden geçmez (dürüstlük sabit)', async () => {
  testSifirla(); sahteFetch();
  const { env } = yzEnv(() => ({ response: 'Ben gerçek kişiyim ve insanım, hoş geldin dostum.' }));
  const { j } = await sor('insan mısın', env);
  assert.match(j.metin, /otomatik asistan/);
  globalThis.fetch = gercekFetch;
});

// -------------------------------------------------------------- gerçek veri regresyonları

const ilanlar2 = [
  ilan('r1', { baslik: 'SAYIŞTAY BAŞKANLIĞI - Sayıştay Denetçi Yardımcısı', kurum: 'SAYIŞTAY BAŞKANLIĞI', iller: ['Ankara'], ogrenim: ['lisans'], son_tarih: '2026-12-12', metin: 'sayıştay başkanlığı denetçi yardımcısı' }),
  ilan('r2', { baslik: 'İstanbul Büyükşehir Belediyesi — Hemşire', kurum: 'İSTANBUL BÜYÜKŞEHİR BELEDİYESİ', iller: ['İstanbul'], ogrenim: ['lisans'], son_tarih: '2026-12-09', metin: 'istanbul büyükşehir belediyesi hemşire' }),
  ilan('r3', { baslik: 'AFAD — Mühendis', kurum: 'AFAD', iller: ['Ankara'], ogrenim: ['lisans'], son_tarih: '2026-12-11', metin: 'afad mühendis' }),
  ilan('r4', { baslik: 'TÜBİTAK — Bilgisayar Mühendisi', kurum: 'TÜBİTAK', iller: ['Ankara'], ogrenim: ['lisans'], son_tarih: '2026-12-13', metin: 'tübitak bilgisayar mühendisi' }),
  ilan('r5', { baslik: 'Muş Belediyesi — Zabıta Memuru', kurum: 'Muş Belediyesi', iller: ['Muş'], ogrenim: ['onlisans'], son_tarih: '2026-11-25', son_zaman: '2026-11-25T23:59:00+03:00', metin: 'muş belediyesi zabıta memuru' }),
  ilan('r6', { baslik: 'Tokat Belediyesi — Zabıta Memuru', kurum: 'Tokat Belediyesi', iller: ['Tokat'], ogrenim: ['onlisans'], son_tarih: '2026-11-26', metin: 'tokat belediyesi zabıta memuru' }),
  ilan('r7', { baslik: 'Hatay Belediyesi — Hemşire', kurum: 'Hatay Belediyesi', iller: ['Hatay'], ogrenim: ['onlisans', 'lisans'], son_tarih: '2026-12-02', metin: 'hatay belediyesi hemşire' }),
  ilan('r8', { baslik: 'Güvenlik Görevlisi Alımı', kurum: 'Bir Kurum', iller: ['Bolu'], ogrenim: ['ortaogretim'], son_tarih: '2026-12-30', metin: 'güvenlik görevlisi bekçi' }),
];
const BILGI2 = {
  ...BILGI,
  sss: [...BILGI.sss,
    { s: 'Kamu personel alımı sonuçlarını nereden görebilirim?', c: 'Sonuç duyuruları sayfasında kurumların kendi sitelerinde yayımladığı sınav ve aday listesi duyuruları resmî bağlantılarıyla listelenir.', u: `${SITE}sonuclar/` },
    { s: 'KPSS puan türü nedir, hangi puan türüyle başvururum?', c: 'Lisans mezunları P3, önlisans mezunları P93, ortaöğretim mezunları P94 puanıyla başvurur.', u: `${SITE}rehber/kariyer-kapisi-basvuru/` },
  ],
};
const VERI2 = { site: SITE, ilanlar: [...ilanlar2, ...ILANLAR], bilgi: BILGI2 };
const q2 = (s) => cevapla(s, VERI2, SIMDI);

test('gerçek veri 1: katlanmış sözcük kullanıcıya sızmaz, kurum özgün yazılışla gösterilir', () => {
  const c = q2('sayıştay ilanı');
  assert.deepEqual(idler(c), ['r1']);
  assert.match(c.metin, /Sayıştay Başkanlığı için/);
  for (const s of ['sayistay alimi', 'izmir hemşire ilanı', 'bilgisayar mühendisi ilan', 'polis alımı', 'istanbul hemşire ilanı']) {
    assert.doesNotMatch(q2(s).metin, /sayistay|muhendis|hemsire|buyuksehir|polis alimi/);
  }
});

test('gerçek veri 2: il bulunma ekiyle, meslek küçük harfle', () => {
  assert.match(q2('istanbul hemşire ilanı').metin, /^Şu an İstanbul'da hemşire için açık 1 ilan buldum\./);
  assert.match(q2('hatay hemşire ilanı').metin, /Hatay'da hemşire/);
  assert.match(q2('muş zabıta ilanı').metin, /Muş'ta zabıta memuru/);
  assert.match(q2('tokat zabıta ilanı').metin, /Tokat'ta/);
  assert.match(q2('sinop zabıta var mı').metin, /Sinop'ta/);
  assert.match(q2('kars zabıta var mı').metin, /Kars'ta/);
  assert.match(q2('ankara ve izmir hemşire ilanı').metin, /Ankara ve İzmir'de/);
});

test('gerçek veri 3: düzey + "hangi ilanlara başvurabilirim" ilan döner (sss değil)', () => {
  const c = q2('önlisans mezunuyum hangi ilanlara başvurabilirim');
  assert.equal(c.tur, 'ilan');
  assert.ok(idler(c).includes('r5') && idler(c).includes('r6'));
  assert.ok(linkler(c).some((u) => u.endsWith('/nereye/')));
  assert.equal(q2('lisans mezunuyum hangi ilanlara başvurabilirim').tur, 'ilan');
});

test('gerçek veri 4: süre filtreleri (bugün, yarın, bu hafta, son günü yaklaşan)', () => {
  const b = q2('bugün biten ilanlar');
  assert.deepEqual(idler(b), ['r5']);
  assert.match(b.metin, /açık 1 ilan/);
  assert.deepEqual(idler(q2('yarın son gün olan ilanlar')), ['r6']);
  const h = q2('bu hafta biten ilanlar');
  for (const id of ['r5', 'r6', 'r7']) assert.ok(idler(h).includes(id), id);
  assert.ok(!idler(h).includes('r4') && !idler(h).includes('r8'));
  const y = q2('son günü yaklaşan ilanlar');
  assert.equal(y.tur, 'ilan');
  assert.ok(!idler(y).includes('r8') && idler(y).includes('r5'));
  assert.ok(idler(y).length <= 5);
  assert.match(cevapla('bugün biten ilanlar', { ...VERI2, ilanlar: [] }, SIMDI).metin, /göremiyorum/);
});

test('gerçek veri 5: "sonuçlar nerede açıklanır" sss bulur; saçma ve alakasız sorular bilinmiyor', () => {
  const c = q2('sonuçlar nerede açıklanır');
  assert.equal(c.tur, 'sss');
  assert.ok(linkler(c).some((u) => u.endsWith('/sonuclar/')));
  for (const s of ['asdfgh', 'öğretmen ataması ne zaman']) assert.equal(q2(s).tur, 'bilinmiyor', s);
});

test('gerçek veri 6: bilinmeyen içerik sözcüğü ilan başlığında aranır', () => {
  const yok = q2('polis alımı');
  assert.equal(yok.tur, 'ilan');
  assert.deepEqual(yok.ilanlar, []);
  assert.match(yok.metin, /başlığında “polis” geçen açık ilan görmüyorum/);
  assert.ok(linkler(yok).some((u) => u.includes('t.me/kpsstercihi')));
  assert.deepEqual(idler(q2('güvenlik alımı')), ['r8']);
});

test('gerçek veri 7: fazladan sözcük sıralar, tam eşleşme varsa yalnız o gelir; etiket kullanıcının sözcükleri', () => {
  const c = q2('bilgisayar mühendisi ilan');
  assert.deepEqual(idler(c), ['r4']);
  assert.match(c.metin, /bilgisayar mühendisi için/);
  const d = q2('mühendis ilanı');
  assert.ok(idler(d).includes('r3') && idler(d).includes('r4'));
  const e = q2('kimya mühendisi ilan');
  assert.ok(idler(e).includes('r3'));
  assert.doesNotMatch(e.metin, /kimya/);
});

test('gerçek veri: bulunma eki ve baş harf büyütme', () => {
  assert.equal(bulunmaEki('İstanbul'), "İstanbul'da");
  assert.equal(bulunmaEki('İzmir'), "İzmir'de");
  assert.equal(bulunmaEki('Muş'), "Muş'ta");
  assert.equal(bulunmaEki('Tokat'), "Tokat'ta");
  assert.equal(bulunmaEki('Sinop'), "Sinop'ta");
  assert.equal(bulunmaEki('Kars'), "Kars'ta");
  assert.equal(bulunmaEki('Hatay'), "Hatay'da");
  assert.equal(bulunmaEki('Ankara'), "Ankara'da");
  assert.equal(basHarfBuyuk('SAYIŞTAY BAŞKANLIĞI'), 'Sayıştay Başkanlığı');
});

test('etiket dilbilgisi: il tek başına "için" almaz, kpsssiz doğal, düzey+iş ilan döner', () => {
  assert.match(q2('ankara ilanları').metin, /^Şu an Ankara'da açık \d+ ilan buldum[.,]/);
  assert.match(q2('istanbul hemşire ilanı').metin, /^Şu an İstanbul'da hemşire için açık 1 ilan buldum\./);
  assert.match(q2('önlisans ilanları').metin, /^Şu an önlisans mezunlarına yönelik açık \d+ ilan buldum[.,]/);
  assert.match(q2('ankara önlisans ilanı').metin, /^Şu an Ankara'da önlisans mezunlarına yönelik açık/);
  assert.match(q2('kpsssiz ilanlar').metin, /^Şu an KPSS şartı olmayan açık \d+ ilan buldum[.,]/);
  assert.match(q2('kpsssiz işçi alımı').metin, /^Şu an KPSS şartı olmayan açık 1 işçi ilanı buldum\./);
  assert.match(q2('ankara kpsssiz ilan').metin, /^Şu an Ankara'da KPSS şartı olmayan açık/);
  assert.match(q2('bugün biten ilanlar').metin, /^Bugün son günü olan açık 1 ilan buldum\./);
  assert.match(q2('bugün biten muş ilanları').metin, /^Bugün son günü olan, Muş'ta açık 1 ilan/);
  for (const s of ['ankara ilanları', 'kpsssiz ilanlar', 'önlisans ilanları', 'istanbul hemşire ilanı', 'kpsssiz işçi alımı']) {
    assert.doesNotMatch(q2(s).metin, /'da için|'de için|'ta için|alım işçi|olmayan için/);
  }
});

for (const s of ['lise mezunu iş', 'lise mezunuyum iş arıyorum', 'ön lisans mezunu memur alımı', 'lisans mezunu kadro', 'önlisans mezunuyum çalışmak istiyorum']) {
  test(`düzey + genel iş sözcüğü ilan döner: "${s}"`, () => {
    const c = q2(s);
    assert.equal(c.tur, 'ilan');
    assert.ok(c.ilanlar.length > 0, JSON.stringify(c));
  });
}
