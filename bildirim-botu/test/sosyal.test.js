import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cronCalistir } from '../src/bildirim.js';
import { yoneticiTani, guvenliMetin } from '../src/sosyal.js';
import { sahteDB, kullaniciEkle, say, hepsi } from './sahte-c.js';

process.removeAllListeners('warning');

const BUGUN = '2026-10-02';
const T = (hhmm) => new Date(`${BUGUN}T${hhmm}:00+03:00`);
const SITE = 'https://site.test/';
const gorsel = (n) => `https://site.test/paylasim/${BUGUN}/${String(n).padStart(2, '0')}.jpg`;
const gunluk = (ek = {}) => ({
  tarih: BUGUN, bos: false, ilan_sayisi: 3, gorseller: [gorsel(0), gorsel(1), gorsel(2)],
  ig_metin: 'Bugünün ilanları #kpss', x_metin: '📢 Bugün 3 yeni kamu ilanı', ...ek,
});

function kur({ veri = gunluk(), durumlar = ['IN_PROGRESS', 'FINISHED'], env: ekEnv = {}, ig = {} } = {}) {
  const d = sahteDB();
  const c = {
    ...d, istek: [], tgler: [], veri, durumlar: [...durumlar], bekleme: 0, ig,
    env: { DB: d.DB, ILAN_URL: 'https://x/bot-ilanlar.json', SITE_URL: SITE, IG_TOKEN: 'SIR_TOKEN_123', IG_USER_ID: '999', ...ekEnv },
  };
  c.bag = {
    bekle: async () => { c.bekleme++; },
    fetch: async (url, o = {}) => {
      c.istek.push({ url, method: o.method || 'GET', body: o.body || '' });
      const yanit = (g, status = 200) => ({ ok: status < 400, status, text: async () => JSON.stringify(g), json: async () => g });
      if (url.endsWith('bot-ilanlar.json')) return yanit({ ilanlar: [] });
      if (url.endsWith('paylasim/gunluk.json')) return yanit(c.veri);
      if (url.includes('refresh_access_token')) {
        return c.ig.yenilemeHata ? yanit({ error: { message: 'yenileme reddedildi' } }, 400) : yanit({ access_token: 'YENI_TOKEN', expires_in: 5184000 });
      }
      if (c.ig.hata && url.includes(c.ig.hata.icerir)) return yanit({ error: { message: `kötü ${c.ig.hata.token || ''} access_token=SIR_TOKEN_123` } }, 400);
      if (url.endsWith('/media_publish')) return yanit({ id: 'P1' });
      if (url.endsWith('/media')) {
        const b = new URLSearchParams(o.body);
        if (b.get('media_type') === 'CAROUSEL') return yanit({ id: 'KAPSAYICI' });
        if (b.get('is_carousel_item')) return yanit({ id: `cocuk${c.istek.length}` });
        return yanit({ id: 'TEK' });
      }
      if (url.includes('fields=status_code')) return yanit({ status_code: c.durumlar.shift() || 'FINISHED' });
      throw new Error('beklenmeyen url ' + url);
    },
    tg: async (e, m, p, s) => { c.tgler.push({ m, ...p, s }); return {}; },
  };
  c.calis = async (simdi) => {
    const once = { sql: c.sayac.sql, istek: c.istek.length, tg: c.tgler.length };
    const s = await cronCalistir(c.env, simdi, c.bag);
    assert.ok(c.sayac.sql - once.sql <= 40, 'ifade > 40');
    assert.ok(c.istek.length - once.istek + c.tgler.length <= 40, 'istek > 40');
    assert.equal(s.istek, c.istek.length - once.istek + c.tgler.length - once.tg);
    return s;
  };
  c.meta = (k) => (say(c.raw, 'SELECT deger FROM meta WHERE anahtar = ?', k) || {}).deger;
  return c;
}
const yonetici = (c, id = 777) => c.raw.prepare("INSERT OR REPLACE INTO meta VALUES ('yonetici_chat', ?)").run(String(id));

test('zaman penceresi: 10:14 çalışmaz, 10:16 çalışır, aynı gün ikinci kez çalışmaz', async () => {
  const c = kur(); yonetici(c);
  c.ilanlar = [];
  await c.calis(T('10:14'));
  assert.equal(c.meta('sosyal_son_gun'), undefined);
  assert.ok(!c.istek.some((i) => i.url.includes('gunluk.json')));
  const s = await c.calis(T('10:16'));
  assert.equal(s.sosyal, true);
  assert.equal(c.meta('sosyal_son_gun'), BUGUN);
  const n = c.istek.length;
  await c.calis(T('10:17'));
  assert.ok(!c.istek.slice(n).some((i) => i.url.includes('gunluk.json')));
  assert.equal(c.tgler.filter((t) => t.m === 'sendPhoto').length, 1);
});

test('bos gün (tarih bugün): hiçbir şey paylaşılmaz ama sosyal_son_gun yazılır', async () => {
  const c = kur({ veri: gunluk({ bos: true }) }); yonetici(c);
  await c.calis(T('10:30'));
  assert.equal(c.meta('sosyal_son_gun'), BUGUN);
  assert.equal(c.istek.length, 1);
  assert.equal(c.tgler.length, 0);
});

test('eski tarihli gunluk.json: gün kaybolmaz, en sık 10 dakikada bir denenir, yeni dosya gelince paylaşılır', async () => {
  const c = kur({ veri: gunluk({ tarih: '2026-10-01' }) }); yonetici(c);
  const gunlukSayisi = () => c.istek.filter((i) => i.url.includes('gunluk.json')).length;
  await c.calis(T('10:30'));
  assert.equal(c.meta('sosyal_son_gun'), undefined);
  assert.equal(gunlukSayisi(), 1);
  await c.calis(T('10:35'));
  await c.calis(T('10:39'));
  assert.equal(gunlukSayisi(), 1); // 10 dakika dolmadan yeniden çekilmez
  await c.calis(T('10:41'));
  assert.equal(gunlukSayisi(), 2);
  c.veri = gunluk(); // site bugünün dosyasını yayınladı
  await c.calis(T('10:52'));
  assert.equal(c.meta('sosyal_son_gun'), BUGUN);
  assert.equal(c.meta('ig_son_gun'), BUGUN);
  assert.equal(c.tgler.filter((t) => t.m === 'sendPhoto').length, 1);
});

test('boş günde de Instagram anahtarı günde bir kez yenilenir (içerikten bağımsız)', async () => {
  const c = kur({ veri: gunluk({ bos: true }) });
  const eski = new Date(T('10:20').getTime() - 55 * 86400000).toISOString();
  c.raw.prepare("INSERT INTO meta VALUES ('ig_token', 'ESKI_TOKEN'), ('ig_token_tarih', ?)").run(eski);
  await c.calis(T('10:20'));
  assert.equal(c.meta('ig_token'), 'YENI_TOKEN');
  assert.equal(c.meta('ig_token_gunu'), BUGUN);
  assert.equal(c.meta('ig_son_gun'), undefined); // paylaşım yok
  assert.equal(c.istek.filter((i) => i.url.includes('refresh_access_token')).length, 1);
});

test('kilit sahipliği: başkasının kilidi bırakılmaz; sosyal adımda kilit 5 dakikaya uzar', async () => {
  const c = kur();
  const baskasi = `${T('10:20').getTime() + 400000}:baska-sahip`;
  let uzamis = null;
  const asil = c.bag.fetch;
  c.bag.fetch = async (u, o) => {
    if (u.endsWith('gunluk.json')) {
      uzamis = c.meta('kilit'); // kilit bizim, 5 dakikaya uzatılmış olmalı
      c.raw.prepare("UPDATE meta SET deger = ? WHERE anahtar = 'kilit'").run(baskasi); // kilit el değiştirdi
    }
    return asil(u, o);
  };
  await c.calis(T('10:20'));
  const [bitis] = uzamis.split(':');
  assert.equal(Number(bitis), T('10:20').getTime() + 5 * 60 * 1000);
  assert.equal(c.meta('kilit'), baskasi); // finally başkasının kilidini açmadı
  // normal durumda kilit bırakılır
  const c2 = kur();
  await c2.calis(T('10:20'));
  assert.equal(c2.meta('kilit'), '0');
});

test('kilit kaybedilmişse sosyal adım hiç çalışmaz', async () => {
  const c = kur();
  c.raw.exec("INSERT INTO meta VALUES ('kilit', '0')");
  const asil = c.bag.fetch;
  let ilk = true;
  c.bag.fetch = async (u, o) => asil(u, o);
  // kilidi aldıktan hemen sonra el değiştirsin: ilk meta okuması sırasında değil, uzatma öncesi
  const prepare = c.env.DB.prepare.bind(c.env.DB);
  c.env.DB.prepare = (q) => {
    if (ilk && q.includes('SELECT anahtar, deger FROM meta')) {
      ilk = false;
      c.raw.prepare("UPDATE meta SET deger = ? WHERE anahtar = 'kilit'").run(`${T('10:20').getTime() + 400000}:baska`);
    }
    return prepare(q);
  };
  await c.calis(T('10:20'));
  assert.ok(!c.istek.some((i) => i.url.includes('gunluk.json') || i.url.includes('graph.instagram.com')));
});

test('gunluk.json alınamazsa sosyal_son_gun yazılmaz ve normal akış sürer', async () => {
  const c = kur(); 
  c.bag.fetch = async (u) => { if (u.endsWith('gunluk.json')) return { ok: false, status: 404, json: async () => ({}) }; return { ok: true, json: async () => ({ ilanlar: [] }) }; };
  const s = await cronCalistir(c.env, T('10:30'), c.bag);
  assert.equal(c.meta('sosyal_son_gun'), undefined);
  assert.ok(!s.sosyal);
});

test('Instagram carousel: çocuklar, kapsayıcı, FINISHED yoklaması, publish; X taslağı yöneticiye', async () => {
  const c = kur({ durumlar: ['IN_PROGRESS', 'IN_PROGRESS', 'FINISHED'] }); yonetici(c);
  const s = await c.calis(T('10:20'));
  const post = c.istek.filter((i) => i.method === 'POST');
  assert.equal(post.filter((i) => i.body.includes('is_carousel_item=true')).length, 3);
  const kaps = post.find((i) => i.body.includes('media_type=CAROUSEL'));
  assert.ok(kaps && new URLSearchParams(kaps.body).get('children').split(',').length === 3);
  assert.equal(new URLSearchParams(kaps.body).get('caption'), 'Bugünün ilanları #kpss');
  assert.equal(c.istek.filter((i) => i.url.includes('fields=status_code')).length, 3);
  assert.equal(c.bekleme, 2);
  assert.ok(c.istek.at(-1).url.endsWith('/999/media_publish'));
  assert.equal(new URLSearchParams(c.istek.at(-1).body).get('creation_id'), 'KAPSAYICI');
  assert.equal(c.meta('ig_son_gun'), BUGUN);
  assert.equal(c.meta('ig_son_hata'), '');
  const foto = c.tgler.find((t) => t.m === 'sendPhoto');
  assert.deepEqual([foto.chat_id, foto.photo, foto.caption], [777, gorsel(0), '📢 Bugün 3 yeni kamu ilanı']);
  assert.equal(foto.s.yeniden, false);
  assert.equal(c.meta('x_son_gun'), BUGUN);
  assert.ok(s.istek <= 40);
});

test('tek görsel: carousel yok, doğrudan görsel gönderisi', async () => {
  const c = kur({ veri: gunluk({ gorseller: [gorsel(0)] }) });
  await c.calis(T('10:20'));
  const post = c.istek.filter((i) => i.method === 'POST');
  assert.equal(post.length, 2); // media + media_publish
  const b = new URLSearchParams(post[0].body);
  assert.equal(b.get('image_url'), gorsel(0));
  assert.equal(b.get('caption'), 'Bugünün ilanları #kpss');
  assert.equal(b.get('media_type'), null);
  assert.equal(new URLSearchParams(post[1].body).get('creation_id'), 'TEK');
});

test('IG hatası: ikinci deneme yok, ig_son_gun yazılır, hata kısa ve token içermez, yöneticiye bilgi', async () => {
  const c = kur({ ig: { hata: { icerir: '/media' } } }); yonetici(c);
  await c.calis(T('10:20'));
  assert.equal(c.meta('ig_son_gun'), BUGUN);
  const hata = c.meta('ig_son_hata');
  assert.ok(hata && hata.length <= 140 && !hata.includes('SIR_TOKEN_123'));
  const bilgi = c.tgler.find((t) => t.m === 'sendMessage');
  assert.ok(bilgi.text.startsWith('Instagram paylaşımı başarısız:') && !bilgi.text.includes('SIR_TOKEN_123'));
  assert.ok(c.tgler.some((t) => t.m === 'sendPhoto')); // X taslağı yine gider
  // aynı gün ikinci çağrıda Instagram'a hiç istek gitmez
  c.raw.prepare("UPDATE meta SET deger = '' WHERE anahtar = 'sosyal_son_gun'").run();
  const n = c.istek.length;
  await c.calis(T('10:40'));
  assert.ok(!c.istek.slice(n).some((i) => i.url.includes('graph.instagram.com')));
});

test('token yenileme: 51 günlük D1 token yenilenir ve kullanılır; 10 günlük yenilenmez', async () => {
  const c = kur();
  const eski = new Date(T('10:20').getTime() - 51 * 86400000).toISOString();
  c.raw.prepare("INSERT INTO meta VALUES ('ig_token', 'ESKI_TOKEN'), ('ig_token_tarih', ?)").run(eski);
  await c.calis(T('10:20'));
  assert.ok(c.istek.some((i) => i.url.includes('refresh_access_token') && i.url.includes('ESKI_TOKEN')));
  assert.equal(c.meta('ig_token'), 'YENI_TOKEN');
  assert.equal(c.meta('ig_token_tarih'), T('10:20').toISOString());
  assert.ok(c.istek.filter((i) => i.method === 'POST').every((i) => i.body.includes('access_token=YENI_TOKEN')));

  const c2 = kur();
  const yeni = new Date(T('10:20').getTime() - 10 * 86400000).toISOString();
  c2.raw.prepare("INSERT INTO meta VALUES ('ig_token', 'D1_TOKEN'), ('ig_token_tarih', ?)").run(yeni);
  await c2.calis(T('10:20'));
  assert.ok(!c2.istek.some((i) => i.url.includes('refresh_access_token')));
  assert.ok(c2.istek.filter((i) => i.method === 'POST').every((i) => i.body.includes('access_token=D1_TOKEN'))); // sırdan öncelikli
});

test('token yokken IG atlanır ama X taslağı gider; yönetici yokken X atlanır', async () => {
  const c = kur({ env: { IG_TOKEN: undefined } }); yonetici(c);
  await c.calis(T('10:20'));
  assert.ok(!c.istek.some((i) => i.url.includes('graph.instagram.com')));
  assert.equal(c.meta('ig_son_gun'), undefined);
  assert.equal(c.tgler.filter((t) => t.m === 'sendPhoto').length, 1);

  const c2 = kur(); // yönetici yok
  await c2.calis(T('10:20'));
  assert.equal(c2.tgler.length, 0);
  assert.equal(c2.meta('x_son_gun'), undefined);
  assert.equal(c2.meta('ig_son_gun'), BUGUN);
});

test('yönetici tanıma: büyük/küçük harf, yalnız özel sohbet, başkası yazamaz', async () => {
  const c = kur();
  const env = { ...c.env, YONETICI_KULLANICI: '@YoneticiAd' };
  const ileti = (username, tip = 'private', id = 42) => ({ message: { chat: { id, type: tip }, from: { username }, text: 'merhaba' } });
  await yoneticiTani(env, ileti('baskasi'));
  await yoneticiTani(env, ileti('yoneticiAD', 'group', 5));
  assert.equal(c.meta('yonetici_chat'), undefined);
  await yoneticiTani(env, ileti('YONETICIad'));
  assert.equal(c.meta('yonetici_chat'), '42');
  await yoneticiTani({ ...env, YONETICI_KULLANICI: '' }, ileti('x', 'private', 9));
  assert.equal(c.meta('yonetici_chat'), '42');
  // kalıcı: aynı kullanıcı adıyla başka sohbetten gelen ileti değeri değiştirmez
  await yoneticiTani(env, ileti('yoneticiad', 'private', 4242));
  assert.equal(c.meta('yonetici_chat'), '42');
});

test('bu çağrıda kuyruk boşaltma ve tarama yapılmaz', async () => {
  const c = kur(); yonetici(c);
  kullaniciEkle(c.raw, 1);
  c.raw.prepare("INSERT INTO bilinen_ilanlar (ilan_id, ana_id, son_tarih, veri, ilk_gorulme) VALUES ('a','a','2026-10-20',?, 'x')")
    .run(JSON.stringify({ baslik: 'A', sayfa: 'https://s.test/', son_tarih: '2026-10-20' }));
  c.raw.prepare("INSERT INTO kuyruk (chat_id, ilan_id, tur) VALUES (1, 'a', 'ilan')").run();
  await c.calis(T('10:20'));
  assert.equal(c.tgler.filter((t) => t.chat_id === 1).length, 0);
  assert.equal(hepsi(c.raw, 'SELECT * FROM kuyruk').length, 1);
  assert.ok(!c.istek.some((i) => i.url.includes('bot-ilanlar')));
  // sonraki dakikada boşaltma çalışır
  await c.calis(T('10:21'));
  assert.equal(c.tgler.filter((t) => t.chat_id === 1).length, 1);
});

test('en kötü durum: 10 görsel, 6 yoklama, yenileme + X + hata bilgisi ≤40 istek, ≤40 ifade', async () => {
  const c = kur({ veri: gunluk({ gorseller: Array.from({ length: 10 }, (_, n) => gorsel(n)) }), durumlar: ['IN_PROGRESS', 'IN_PROGRESS', 'IN_PROGRESS', 'IN_PROGRESS', 'IN_PROGRESS', 'IN_PROGRESS'] });
  yonetici(c);
  const eski = new Date(T('10:20').getTime() - 60 * 86400000).toISOString();
  c.raw.prepare("INSERT INTO meta VALUES ('ig_token', 'ESKI'), ('ig_token_tarih', ?)").run(eski);
  const once = c.sayac.sql;
  await c.calis(T('10:20')); // yoklama zaman aşımı -> hata
  console.log(`  [bilgi] en kötü durum: ${c.istek.length} fetch + ${c.tgler.length} Telegram, ${c.sayac.sql - once} ifade`);
  assert.match(c.meta('ig_son_hata'), /zamanında hazır olmadı/);
});

test('guvenliMetin token ve access_token alanlarını temizler', () => {
  const s = guvenliMetin('{"access_token":"ABC123xyz","m":"SIR"} access_token=QQQ SIR', 'SIR');
  assert.ok(!s.includes('ABC123xyz') && !s.includes('QQQ') && !s.includes('SIR'));
});

test('env.IG_TOKEN ilk kullanımda D1\'e taşınır (yaş = şimdi, yenileme yok); 51 gün sonra yenilenir; yenileme sürümsüz uç noktadan', async () => {
  const c = kur();
  await c.calis(T('10:20'));
  assert.equal(c.meta('ig_token'), 'SIR_TOKEN_123');
  assert.equal(c.meta('ig_token_tarih'), T('10:20').toISOString());
  assert.ok(!c.istek.some((i) => i.url.includes('refresh_access_token')));
  // 51 gün sonra
  const gun2 = '2026-11-22';
  c.veri = gunluk({ tarih: gun2 });
  const simdi2 = new Date(`${gun2}T10:20:00+03:00`);
  assert.equal(Math.round((simdi2 - T('10:20')) / 86400000), 51);
  await c.calis(simdi2);
  const yen = c.istek.find((i) => i.url.includes('refresh_access_token'));
  assert.ok(yen && yen.url.startsWith('https://graph.instagram.com/refresh_access_token?') && yen.url.includes('access_token=SIR_TOKEN_123'));
  assert.equal(c.meta('ig_token'), 'YENI_TOKEN');
  assert.equal(c.meta('ig_token_tarih'), simdi2.toISOString());
  assert.equal(c.meta('ig_son_gun'), gun2);
});

test('yenileme hatası: eski token ile paylaşım sürer, ig_son_hata notu, yöneticiye bir kez bildirim', async () => {
  const c = kur({ ig: { yenilemeHata: true } }); yonetici(c);
  const eski = new Date(T('10:20').getTime() - 55 * 86400000).toISOString();
  c.raw.prepare("INSERT INTO meta VALUES ('ig_token', 'ESKI_TOKEN'), ('ig_token_tarih', ?)").run(eski);
  await c.calis(T('10:20'));
  assert.ok(c.istek.some((i) => i.url.endsWith('/media_publish')));
  assert.ok(c.istek.filter((i) => i.method === 'POST').every((i) => i.body.includes('access_token=ESKI_TOKEN')));
  assert.equal(c.meta('ig_token'), 'ESKI_TOKEN');
  assert.match(c.meta('ig_son_hata'), /Anahtar yenilenemedi/);
  assert.ok(!c.meta('ig_son_hata').includes('ESKI_TOKEN'));
  assert.equal(c.tgler.filter((t) => t.m === 'sendMessage' && t.text === 'Instagram anahtarı yenilenemedi').length, 1);
  assert.equal(c.meta('ig_yenileme_hata_gunu'), BUGUN);
});
