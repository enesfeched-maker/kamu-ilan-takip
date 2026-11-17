import test from 'node:test';
import assert from 'node:assert/strict';
import { panelIstegi, forumOzeti } from '../src/panel.js';
import { bellekSifirla } from '../src/onbellek.js';
import { sahteD1 } from './sahte-d1.js';

const T0 = Date.parse('2026-11-15T09:00:00Z');
const OZET = { uyeler: { toplam: 3 }, seri: [], aktif: {}, soru: {}, sohbet: [], sikayet: {} };
const yerel = (ek = {}) => ({ DB: sahteD1(), ORTAM: 'yerel', ...ek });
const yanit = (o, durum = 200) => async () => new Response(JSON.stringify(o), { status: durum });

test('forum: anahtar yoksa istek atılmaz', async () => {
  bellekSifirla();
  let cagri = 0;
  const r = await forumOzeti(yerel(), T0, async () => { cagri++; return new Response('{}'); });
  assert.deepEqual(r, { durum: 'anahtar_yok' });
  assert.equal(cagri, 0);
});

test('forum: anahtar başlıkta gider, sonuç 5 dk önbelleklenir, varsayılan adres kullanılır', async () => {
  bellekSifirla();
  const gor = [];
  const getir = async (u, o) => { gor.push({ u, h: o.headers['X-Yonetici'] }); return new Response(JSON.stringify(OZET)); };
  const env = yerel({ FORUM_YONETICI_ANAHTARI: 'gizli-anahtar' });
  const a = await forumOzeti(env, T0, getir);
  assert.equal(a.durum, 'tamam');
  assert.equal(a.veri.uyeler.toplam, 3);
  await forumOzeti(env, T0 + 60_000, getir);
  assert.equal(gor.length, 1);
  assert.deepEqual(gor[0], { u: 'https://forum-api.kpsstercihi.com/yonetim/ozet', h: 'gizli-anahtar' });
  await forumOzeti(env, T0 + 301_000, getir);
  assert.equal(gor.length, 2);
});

test('forum: FORUM_API değişkeni kullanılır; hata ve bozuk biçim "hata" döner, önbelleğe yazılmaz', async () => {
  bellekSifirla();
  const env = yerel({ FORUM_YONETICI_ANAHTARI: 'k', FORUM_API: 'http://127.0.0.1:8790/' });
  let adres = '';
  assert.equal((await forumOzeti(env, T0, async (u) => { adres = u; return new Response('x', { status: 500 }); })).durum, 'hata');
  assert.equal(adres, 'http://127.0.0.1:8790/yonetim/ozet');
  assert.equal((await forumOzeti(env, T0, async () => { throw new Error('ağ'); })).durum, 'hata');
  assert.equal((await forumOzeti(env, T0, yanit({ yok: 1 }))).durum, 'hata');
  assert.equal((await forumOzeti(env, T0, yanit(OZET))).durum, 'tamam');
});

test('/panel/forum: oturumsuz 401; panel sayfası forum bölümünü içerir, anahtar sayfaya sızmaz', async () => {
  bellekSifirla();
  const env = { DB: sahteD1(), PANEL_ANAHTARI: 'dogru-anahtar-123', FORUM_YONETICI_ANAHTARI: 'forum-gizli' };
  const r = await panelIstegi(new Request('https://api.kpsstercihi.com/panel/forum'), env, new URL('https://api.kpsstercihi.com/panel/forum'), { simdiMs: T0 });
  assert.equal(r.status, 401);
  const e = yerel({ FORUM_YONETICI_ANAHTARI: 'forum-gizli' });
  const s = await (await panelIstegi(new Request('https://api.kpsstercihi.com/panel'), e, new URL('https://api.kpsstercihi.com/panel'), { simdiMs: T0 })).text();
  assert.ok(s.includes('id="sekme-forum"') && s.includes('/panel/forum-analiz'));
  assert.ok(!s.includes('forum-gizli'));
  const j = await panelIstegi(new Request('https://api.kpsstercihi.com/panel/forum'), e, new URL('https://api.kpsstercihi.com/panel/forum'), { simdiMs: T0, forumGetir: yanit(OZET) });
  assert.equal((await j.json()).durum, 'tamam');
});
