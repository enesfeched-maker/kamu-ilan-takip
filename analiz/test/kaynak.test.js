import test from 'node:test';
import assert from 'node:assert/strict';
import { kaynakSinifla } from '../src/kaynak.js';
import { botMu, cihazTuru, tarayiciAilesi, isletimAilesi, genislikKovasi } from '../src/ua.js';

test('yönlendirenlerin sınıflandırılması', () => {
  const c = [
    ['www.google.com', '', 'Google'], ['google.com.tr', '', 'Google'], ['com.google.android.googlequicksearchbox', '', 'Google'],
    ['www.bing.com', '', 'Bing'], ['yandex.com.tr', '', 'Yandex'], ['t.me', '', 'Telegram'], ['web.telegram.org', '', 'Telegram'],
    ['l.instagram.com', '', 'Instagram'], ['t.co', '', 'X'], ['x.com', '', 'X'], ['twitter.com', '', 'X'],
    ['m.facebook.com', '', 'Facebook'], ['l.facebook.com', '', 'Facebook'], ['wa.me', '', 'WhatsApp'], ['api.whatsapp.com', '', 'WhatsApp'],
    ['', '', 'Doğrudan'], [null, '', 'Doğrudan'], ['kpsstercihi.com', '', 'Doğrudan'], ['blog.ornek.com', '', 'Diğer'],
    ['duckduckgo.com', '', 'Arama (diğer)'],
    ['', 'telegram', 'Telegram'], ['', 'Instagram', 'Instagram'], ['google.com', 'telegram', 'Telegram'], ['', 'bulten', 'Diğer'],
  ];
  for (const [h, u, beklenen] of c) assert.equal(kaynakSinifla(h, u), beklenen, `${h}|${u}`);
});

const CHROME_WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
const SAFARI_IOS = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';
const ANDROID = 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36';
const TABLET = 'Mozilla/5.0 (Linux; Android 13; SM-X700) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';

test('bot süzgeci', () => {
  for (const b of ['Googlebot/2.1 (+http://www.google.com/bot.html)', 'Mozilla/5.0 (compatible; bingbot/2.0)', 'curl/8.0', 'python-requests/2.31', 'HeadlessChrome/120', 'TelegramBot (like TwitterBot)', 'Mozilla/5.0 AppleWebKit Lighthouse', '', 'x'])
    assert.equal(botMu(b), true, b);
  for (const g of [CHROME_WIN, SAFARI_IOS, ANDROID]) assert.equal(botMu(g), false);
});

test('cihaz, tarayıcı, işletim sistemi', () => {
  assert.deepEqual([cihazTuru(CHROME_WIN), tarayiciAilesi(CHROME_WIN), isletimAilesi(CHROME_WIN)], ['masaüstü', 'Chrome', 'Windows']);
  assert.deepEqual([cihazTuru(SAFARI_IOS), tarayiciAilesi(SAFARI_IOS), isletimAilesi(SAFARI_IOS)], ['mobil', 'Safari', 'iOS']);
  assert.deepEqual([cihazTuru(ANDROID), isletimAilesi(ANDROID)], ['mobil', 'Android']);
  assert.equal(cihazTuru(TABLET), 'tablet');
  assert.equal(tarayiciAilesi(CHROME_WIN + ' Edg/130.0'), 'Edge');
  assert.equal(tarayiciAilesi('Mozilla/5.0 Firefox/130.0'), 'Firefox');
  assert.equal(genislikKovasi(390), '<480');
  assert.equal(genislikKovasi(1920), '1440+');
  assert.equal(genislikKovasi(0), '');
});
