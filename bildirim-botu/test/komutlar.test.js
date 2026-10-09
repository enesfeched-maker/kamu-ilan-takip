import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { updateIsle } from '../src/komutlar.js';
import { ILLER, ilKlavye } from '../src/klavye.js';
import { kullaniciGetir } from '../src/db.js';
import worker from '../src/index.js';
import { ENV, sahteTelegram, mesaj, cb } from './sahte-b.js';

let tgs, env;
const bag = { acikIlanOzeti: async () => 'Şu an 3 açık ilan var.' };
const gonder = (u) => updateIsle(env, u, bag);
const metinler = () => tgs.cagrilar.filter((c) => c.method === 'sendMessage' || c.method === 'editMessageText').map((c) => c.params.text);
const butonlar = (c) => c.params.reply_markup.inline_keyboard.flat();

beforeEach(() => {
  tgs = sahteTelegram();
  env = ENV();
});
afterEach(() => tgs.geri());

test('81 il ve callback_data 64 baytı aşmaz', () => {
  assert.equal(ILLER.length, 81);
  for (let s = 0; s < 4; s++) {
    for (const b of ilKlavye(ILLER.slice(0, 5), s).inline_keyboard.flat()) {
      assert.ok(Buffer.byteLength(b.callback_data) <= 64);
    }
  }
});

test('/start onay düğmesi gösterir', async () => {
  await gonder(mesaj(1, '/start'));
  const c = tgs.son('sendMessage');
  assert.doesNotMatch(c.params.text, /sponsor/i);
  assert.equal(butonlar(c)[0].callback_data, 'onay');
  assert.equal(await kullaniciGetir(env, 1), null);
});

const kod = (s) => Buffer.from(s, 'utf8').toString('base64url');

test('siteden gelen kelime: onaysız kullanıcıda onaydan sonra, onaylıda hemen eklenir', async () => {
  await gonder(mesaj(1, '/start k_' + kod('Çocuk Gelişimi')));
  const c = tgs.son('sendMessage');
  assert.match(c.params.text, /“çocuk gelişimi”/);
  const veri = butonlar(c)[0].callback_data;
  assert.equal(veri, 'onay:' + kod('Çocuk Gelişimi'));
  assert.ok(Buffer.byteLength(veri) <= 64);
  assert.equal(await kullaniciGetir(env, 1), null);
  await gonder(cb(1, veri));
  assert.deepEqual((await kullaniciGetir(env, 1)).kelimeler, ['çocuk gelişimi']);
  await gonder(mesaj(1, '/start k_' + kod('diyetisyen')));
  assert.deepEqual((await kullaniciGetir(env, 1)).kelimeler, ['çocuk gelişimi', 'diyetisyen']);
  assert.match(tgs.son('sendMessage').params.text, /takibe eklendi/);
  await gonder(mesaj(1, '/start k_' + kod('diyetisyen')));
  assert.deepEqual((await kullaniciGetir(env, 1)).kelimeler, ['çocuk gelişimi', 'diyetisyen']);
});

test('bozuk derin bağlantı kelime eklemez', async () => {
  await gonder(mesaj(1, '/start k_%%%'));
  assert.equal(butonlar(tgs.son('sendMessage'))[0].callback_data, 'onay');
  await gonder(mesaj(1, '/start k_' + Buffer.from([0xff, 0xfe]).toString('base64url')));
  assert.equal(butonlar(tgs.son('sendMessage'))[0].callback_data, 'onay');
});

test('onay -> düzey klavyesi; düzey seçimi ✓ toggle', async () => {
  await gonder(cb(1, 'onay'));
  const k = await kullaniciGetir(env, 1);
  assert.equal(k.onay, 1);
  assert.equal(k.aktif, 0);
  let c = tgs.son('editMessageText');
  assert.deepEqual(butonlar(c).map((b) => b.callback_data), ['d:w:lisans', 'd:w:onlisans', 'd:w:ortaogretim', 'd:w:ok']);
  await gonder(cb(1, 'd:w:lisans'));
  c = tgs.son('editMessageText');
  assert.match(butonlar(c)[0].text, /^✓ /);
  assert.deepEqual((await kullaniciGetir(env, 1)).duzeyler, ['lisans']);
  await gonder(cb(1, 'd:w:lisans'));
  assert.deepEqual((await kullaniciGetir(env, 1)).duzeyler, []);
  assert.match(butonlar(tgs.son('editMessageText'))[0].text, /^Lisans/);
  assert.ok(tgs.cagrilar.some((x) => x.method === 'answerCallbackQuery'));
});

test('il sayfalama ve seçim', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'd:w:ok'));
  let b = butonlar(tgs.son('editMessageText'));
  assert.equal(b.filter((x) => /^i:w:t\d/.test(x.callback_data)).length, 24);
  assert.ok(b.some((x) => x.text === '✓ Tüm Türkiye'));
  assert.ok(!b.some((x) => x.text.includes('Geri')));
  await gonder(cb(1, 'i:w:p3'));
  b = butonlar(tgs.son('editMessageText'));
  assert.equal(b.filter((x) => /^i:w:t\d/.test(x.callback_data)).length, 9);
  assert.ok(b.some((x) => x.text.includes('Geri')) && !b.some((x) => x.text.includes('İleri')));
  const idx = ILLER.indexOf('Zonguldak');
  await gonder(cb(1, `i:w:t${idx}`));
  assert.deepEqual((await kullaniciGetir(env, 1)).iller, ['Zonguldak']);
  assert.ok(butonlar(tgs.son('editMessageText')).some((x) => x.text === '✓ Zonguldak'));
  await gonder(cb(1, 'i:w:tum'));
  assert.deepEqual((await kullaniciGetir(env, 1)).iller, []);
});

test('kurulum sihirbazı: kategori, kelime, özet', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'i:w:ok'));
  await gonder(cb(1, 'k:w:saglik'));
  await gonder(cb(1, 'k:w:akd')); // eski mesajlardaki akademik düğmesi artık etkisiz
  let k = await kullaniciGetir(env, 1);
  assert.deepEqual(k.kategoriler, ['saglik']);
  assert.ok(!k.akademik);
  assert.ok(!JSON.stringify(tgs.son('editMessageText')).toLowerCase().includes('akademik'));
  await gonder(cb(1, 'k:w:ok'));
  assert.ok(butonlar(tgs.son('editMessageText')).some((x) => x.callback_data === 'kw:atla'));
  await gonder(mesaj(1, ' Hukuk,  BİLGİSAYAR ,hukuk'));
  k = await kullaniciGetir(env, 1);
  assert.deepEqual(k.kelimeler, ['hukuk', 'bilgisayar']);
  assert.equal(k.durum, null);
  const m = metinler();
  assert.match(m.at(-2), /Tercihlerin/);
  assert.equal(m.at(-1), 'Şu an 3 açık ilan var.');
});

test('kurulum: kelime atla', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'k:w:ok'));
  await gonder(cb(1, 'kw:atla'));
  assert.equal((await kullaniciGetir(env, 1)).durum, null);
  assert.equal(metinler().at(-1), 'Şu an 3 açık ilan var.');
});

test('/kelime akışı: kaydet, 10 sınırı, yok temizler', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(mesaj(1, '/kelime'));
  assert.equal((await kullaniciGetir(env, 1)).durum, 'kelime_bekleniyor');
  await gonder(mesaj(1, Array.from({ length: 14 }, (_, i) => 'k' + i).join(',')));
  let k = await kullaniciGetir(env, 1);
  assert.equal(k.kelimeler.length, 10);
  assert.equal(k.durum, null);
  await gonder(mesaj(1, '/kelime'));
  await gonder(mesaj(1, 'YOK'));
  assert.deepEqual((await kullaniciGetir(env, 1)).kelimeler, []);
});

test('onaysız kullanıcı ayar komutunda /start e yönlendirilir', async () => {
  for (const kmd of ['/ayarlar', '/kelime', '/durdur', '/devam']) {
    tgs.temizle();
    await gonder(mesaj(5, kmd));
    assert.match(tgs.son('sendMessage').params.text, /\/start/);
  }
  assert.equal(await kullaniciGetir(env, 5), null);
});

test('/durdur ve /devam', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(mesaj(1, '/durdur'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 0);
  await gonder(mesaj(1, '/devam'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 1);
});

test('/ayarlar ve düzenleme modu', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(mesaj(1, '/ayarlar'));
  assert.match(tgs.son('sendMessage').params.text, /Tercihlerin/);
  await gonder(cb(1, 'ay:duzey'));
  await gonder(cb(1, 'd:e:onlisans'));
  await gonder(cb(1, 'd:e:ok'));
  assert.match(tgs.son('editMessageText').params.text, /Ön lisans/);
  await gonder(cb(1, 'ay:hat'));
  assert.equal((await kullaniciGetir(env, 1)).hatirlatma, 0);
});

test('/sil onay düğmesiyle tüm verileri siler', async () => {
  await gonder(cb(1, 'onay'));
  env.DB.tablolar.gonderilen.push({ chat_id: 1, ilan_id: 'a' }, { chat_id: 2, ilan_id: 'b' });
  env.DB.tablolar.kuyruk.push({ chat_id: 1, ilan_id: 'a', tur: 'ilan' }, { chat_id: 2, ilan_id: 'b', tur: 'ilan' });
  await gonder(mesaj(1, '/sil'));
  assert.ok(butonlar(tgs.son('sendMessage')).some((b) => b.callback_data === 'sil:evet'));
  assert.ok(await kullaniciGetir(env, 1));
  await gonder(cb(1, 'sil:evet'));
  assert.equal(await kullaniciGetir(env, 1), null);
  assert.deepEqual(env.DB.tablolar.gonderilen.map((r) => r.chat_id), [2]);
  assert.deepEqual(env.DB.tablolar.kuyruk.map((r) => r.chat_id), [2]);
});

test('/vip VIP_ACIK kapalıyken yakında der; /yardim', async () => {
  await gonder(mesaj(1, '/vip'));
  assert.match(tgs.son('sendMessage').params.text, /yakında/i);
  await gonder(mesaj(1, '/yardim'));
  assert.match(tgs.son('sendMessage').params.text, /\/ayarlar/);
});

const istek = (govde, secret) =>
  new Request('https://x.test/webhook', {
    method: 'POST',
    headers: secret ? { 'X-Telegram-Bot-Api-Secret-Token': secret } : {},
    body: JSON.stringify(govde),
  });

test('webhook: yanlış/eksik secret 401, GET / ok', async () => {
  assert.equal((await worker.fetch(istek(mesaj(1, '/start'), 'yanlis'), env, {})).status, 401);
  assert.equal((await worker.fetch(istek(mesaj(1, '/start')), env, {})).status, 401);
  assert.equal(tgs.cagrilar.length, 0);
  const r = await worker.fetch(new Request('https://x.test/'), env, {});
  assert.equal(await r.text(), 'ok');
});

test('webhook: grup sohbeti yok sayılır, özel sohbet işlenir', async () => {
  let r = await worker.fetch(istek(mesaj(-100, '/start', 'group'), 'gizli'), env, {});
  assert.equal(r.status, 200);
  assert.equal(tgs.cagrilar.length, 0);
  r = await worker.fetch(istek(cb(-100, 'onay', 11, 'supergroup'), 'gizli'), env, {});
  assert.equal(tgs.cagrilar.length, 0);
  r = await worker.fetch(istek(mesaj(1, '/start'), 'gizli'), env, {});
  assert.equal(r.status, 200);
  assert.equal(tgs.cagrilar.length, 1);
});

test('webhook: Telegram hatası (403 dahil) olsa da 200 döner', async () => {
  tgs.hata('sendMessage', 500, 'Internal Server Error');
  let r = await worker.fetch(istek(mesaj(1, '/start'), 'gizli'), env, {});
  assert.equal(r.status, 200);
  tgs.hata('sendMessage', 403, 'Forbidden: bot was blocked by the user');
  r = await worker.fetch(istek(mesaj(1, '/start'), 'gizli'), env, {});
  assert.equal(r.status, 200);
  r = await worker.fetch(new Request('https://x.test/webhook', { method: 'POST', headers: { 'X-Telegram-Bot-Api-Secret-Token': 'gizli' }, body: 'bozuk{' }), env, {});
  assert.equal(r.status, 200);
});

test('tg: hata alanları, token sızmaz, 429 bir kez yeniden dener', async () => {
  const { tg } = await import('../src/telegram.js');
  tgs.hata('getMe', 400, 'Bad Request');
  await assert.rejects(tg(env, 'getMe', {}), (e) => e.kod === 400 && e.aciklama === 'Bad Request' && !e.message.includes('TEST_TOKEN'));
  tgs.temizle();
  tgs.hata('getMe', 429, 'Too Many Requests', { retry_after: 0 });
  await assert.rejects(tg(env, 'getMe', {}), (e) => e.kod === 429);
  assert.equal(tgs.cagrilar.length, 2);
});

test('eski "Kabul ediyorum" düğmesi durdurulmuş kullanıcıyı yeniden aktif etmez', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(mesaj(1, '/durdur'));
  tgs.temizle();
  await gonder(cb(1, 'onay'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 0);
  assert.match(tgs.son('editMessageText').params.text, /zaten/);
});

test('çakışmada (guncelleme değişti) toggle yeniden okuyup bir kez daha dener', async () => {
  await gonder(cb(1, 'onay'));
  // Araya başka bir güncelleme girer: seçim kaybolmamalı
  env.DB.durum.onceUpdate = (t) => {
    const r = t.kullanicilar.get(1);
    r.kategoriler = JSON.stringify(['isci']);
    r.guncelleme = 'baska-zaman';
  };
  await gonder(cb(1, 'k:w:saglik'));
  assert.deepEqual((await kullaniciGetir(env, 1)).kategoriler.sort(), ['isci', 'saglik']);
});

test('webhook: gizli anahtar uzunluğu farklı olsa da 401', async () => {
  for (const s of ['g', 'gizli!', 'gizlj']) {
    assert.equal((await worker.fetch(istek(mesaj(1, '/start'), s), env, {})).status, 401);
  }
});

test('bütçe: kurulum bitişi (kelime metni + özet) sınırların çok altında', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'k:w:ok'));
  tgs.temizle();
  env.DB.durum.sorgu = 0;
  let fetchSayisi = 0;
  const ozetli = { acikIlanOzeti: async () => { fetchSayisi++; return 'özet'; } };
  await updateIsle(env, mesaj(1, 'hukuk'), ozetli);
  const d1 = env.DB.durum.sorgu;
  const dis = tgs.cagrilar.length + fetchSayisi;
  console.log(`# kurulum bitişi: D1 ifadesi=${d1}, dış istek=${dis} (Telegram ${tgs.cagrilar.length} + ilan fetch ${fetchSayisi})`);
  assert.ok(d1 <= 6 && dis <= 5);
});
test('kurulum bitene kadar aktif=0; özette aktif=1; /ayarlar aktifi değiştirmez', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'd:w:lisans'));
  await gonder(cb(1, 'k:w:ok'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 0);
  await gonder(mesaj(1, 'hukuk'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 1);
  await gonder(mesaj(1, '/durdur'));
  await gonder(cb(1, 'ay:duzey'));
  await gonder(cb(1, 'd:e:onlisans'));
  await gonder(cb(1, 'd:e:ok'));
  await gonder(cb(1, 'ay:hat'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 0);
});

test('kurulum atla düğmesi aktif eder; yarıda bırakan /devam ile aktif olur', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'k:w:ok'));
  await gonder(cb(1, 'kw:atla'));
  assert.equal((await kullaniciGetir(env, 1)).aktif, 1);
  await gonder(cb(2, 'onay'));
  assert.equal((await kullaniciGetir(env, 2)).aktif, 0);
  await gonder(mesaj(2, '/devam'));
  assert.equal((await kullaniciGetir(env, 2)).aktif, 1);
  assert.match(tgs.son('sendMessage').params.text, /\/ayarlar/);
});

test('/sil üç silmeyi tek batch ile yapar', async () => {
  await gonder(cb(1, 'onay'));
  await gonder(cb(1, 'sil:evet'));
  assert.equal(env.DB.durum.batch, 1);
  assert.equal(await kullaniciGetir(env, 1), null);
});