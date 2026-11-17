import test from 'node:test';
import assert from 'node:assert/strict';
import { telegramDogrula, oturumUret, jetonCoz, oturumUyeKimligi, geciciUret, geciciTgKimligi, rumuzDogrula, OTURUM_SURESI } from '../src/oturum.js';
import { telegramImzala } from './yardim.js';

const env = { TELEGRAM_BOT_TOKEN: '999:FAKE', OTURUM_SIRRI: 'gizli' };
const simdi = 1_800_000_000;

async function alanlar(ek = {}) {
  const a = { id: 424242, first_name: 'Ali', username: 'ali', auth_date: simdi - 60, ...ek };
  a.hash = await telegramImzala(env.TELEGRAM_BOT_TOKEN, a);
  return a;
}

test('telegram: geçerli imza kabul, alan sırası önemsiz', async () => {
  const a = await alanlar();
  const d = await telegramDogrula(env, a, simdi);
  assert.deepEqual(d, { tamam: true, tgId: 424242 });
  const ters = Object.fromEntries(Object.entries(a).reverse());
  assert.equal((await telegramDogrula(env, ters, simdi)).tamam, true);
});

test('telegram: bozuk hash, değişmiş alan, yanlış token, eski tarih reddedilir', async () => {
  const a = await alanlar();
  assert.equal((await telegramDogrula(env, { ...a, hash: 'a'.repeat(64) }, simdi)).tamam, false);
  assert.equal((await telegramDogrula(env, { ...a, id: 1 }, simdi)).tamam, false);
  assert.equal((await telegramDogrula({ ...env, TELEGRAM_BOT_TOKEN: 'baska' }, a, simdi)).tamam, false);
  const eski = await alanlar({ auth_date: simdi - 86401 });
  const d = await telegramDogrula(env, eski, simdi);
  assert.equal(d.tamam, false); assert.equal(d.neden, 'eski');
  assert.equal((await telegramDogrula(env, { id: 1 }, simdi)).tamam, false);
  assert.equal((await telegramDogrula({}, a, simdi)).tamam, false);
});

test('oturum jetonu: imza, süre, kurcalama', async () => {
  const j = await oturumUret(env, 7, simdi);
  assert.equal(await oturumUyeKimligi(env, j, simdi + 10), 7);
  assert.equal(await oturumUyeKimligi(env, j, simdi + OTURUM_SURESI + 1), null);
  assert.equal(await oturumUyeKimligi({ OTURUM_SIRRI: 'baska' }, j, simdi), null);
  const [g, i] = j.split('.');
  const sahte = Buffer.from(JSON.stringify({ u: 1, s: simdi + 999999 })).toString('base64url');
  assert.equal(await jetonCoz(env, `${sahte}.${i}`, simdi), null);
  assert.equal(await jetonCoz(env, g, simdi), null);
  assert.equal(await jetonCoz(env, 'a.b.c', simdi), null);
  assert.equal(await jetonCoz({}, j, simdi), null);
});

test('geçici jeton 15 dakikada geçer ve oturum jetonu olarak kullanılamaz', async () => {
  const g = await geciciUret(env, 55, simdi);
  assert.equal(await geciciTgKimligi(env, g, simdi + 899), 55);
  assert.equal(await geciciTgKimligi(env, g, simdi + 901), null);
  assert.equal(await oturumUyeKimligi(env, g, simdi), null);
  assert.equal(await geciciTgKimligi(env, await oturumUret(env, 3, simdi), simdi), null);
});

test('rumuz kuralları', () => {
  for (const r of ['Ali_Veli', 'şükrü.1', 'Çağlar', 'abc', 'A'.repeat(20)]) assert.equal(rumuzDogrula(r).tamam, true, r);
  for (const r of ['ab', 'A'.repeat(21), 'ali veli', 'ali-veli', 'ali@x', '___', 'Asistan', 'ADMIN', 'Admin_1', 'Yönetici', 'moderator', 'Sistem', 'kpsstercihi', 'KPSS_Tercihi', 'kpss.tercih.1', 'siktir', 'AsİSTAN', '', null, 5]) {
    assert.equal(rumuzDogrula(r).tamam, false, String(r));
  }
  assert.equal(rumuzDogrula('Ekosistem').tamam, true);
});
