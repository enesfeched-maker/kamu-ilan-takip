import test from 'node:test';
import assert from 'node:assert/strict';
import { panelIstegi } from '../src/panel.js';
import { forumAnalizi, forumOnerileri } from '../src/forum-analiz.js';
import { panelSayfasi } from '../src/arayuz.js';
import { bellekSifirla } from '../src/onbellek.js';
import { sahteD1 } from './sahte-d1.js';

const T0 = Date.parse('2026-11-17T09:00:00Z');
const yerel = (ek = {}) => ({ DB: sahteD1(), ORTAM: 'yerel', ...ek });
const seri = (n) => Array.from({ length: n }, (_, i) => ({ gun: `2026-11-${String(i + 1).padStart(2, '0')}`, uye: 0, soru: 0, cevap: 0, ilan_soru: 0, sohbet: 0, ozel: 0, takip: 0, anket: 0 }));
function veri(ek = {}) {
  return {
    uretildi: 1, gun: 30, uyeler: { toplam: 10, yeni: 4, son: { g1: 1, g7: 2, g30: 4 }, yontem: { google: 3, eposta: 2, telegram: 4, sifre: 1 } },
    aktif: { g1: 1, g7: 3, g30: 6, donem: 6, geri_donen: 1 }, huni: { toplam: 10, yazan: 3, yalniz_etkilesim: 1, iz_yok: 6, yeni: 4, yeni_yazan: 1 },
    seri: seri(30), toplam: {},
    soru: { donem: 5, cevaplanan: 3, ilk_cevap_medyan_dk: 240, bir_saatte: 0, cevapsiz: 4, cevapsiz_liste: [{ id: 9, baslik: 'Eski', kategori: 'Puan ve tercih', gun: 6 }], kategori: [], en_iyi: [], ilan: { n: 4, insan: 1, asistan: 3 } },
    odalar: [{ id: 1, ad: 'Lisans', mesaj: 5, kisi: 2 }, { id: 2, ad: 'Önlisans', mesaj: 0, kisi: 0 }],
    saat: Array.from({ length: 24 }, (_, i) => (i === 21 ? 8 : 1)), isi: [], katkilar: [],
    etkilesim: {}, denetim: { sikayet: 1, ozel_sikayet: 0, foto_bildirim: 1 },
    ...ek,
  };
}
const yanit = (o, durum = 200) => async () => new Response(JSON.stringify(o), { status: durum });

test('forum analizi: anahtar yoksa forum çağrılmaz, "anahtar_yok" döner', async () => {
  bellekSifirla();
  let n = 0;
  assert.deepEqual(await forumAnalizi(yerel(), 30, T0, async () => { n++; return new Response('{}'); }), { durum: 'anahtar_yok' });
  assert.equal(n, 0);
});

test('forum analizi: anahtar başlıkta, gün 7/30/90 (diğerleri 30), dönem başına 5 dk önbellek', async () => {
  bellekSifirla();
  const gor = [];
  const getir = async (u, o) => { gor.push([u, o.headers['X-Yonetici'], !!o.signal]); return new Response(JSON.stringify(veri())); };
  const env = yerel({ FORUM_YONETICI_ANAHTARI: 'gizli', FORUM_API: 'http://127.0.0.1:8790/' });
  const a = await forumAnalizi(env, '7', T0, getir);
  assert.equal(a.durum, 'tamam');
  assert.ok(Array.isArray(a.oneriler) && a.oneriler.length);
  await forumAnalizi(env, '7', T0 + 60_000, getir);
  await forumAnalizi(env, '999', T0, getir);
  await forumAnalizi(env, '90', T0, getir);
  assert.deepEqual(gor.map((g) => g[0]), ['http://127.0.0.1:8790/yonetim/analiz?gun=7', 'http://127.0.0.1:8790/yonetim/analiz?gun=30', 'http://127.0.0.1:8790/yonetim/analiz?gun=90']);
  assert.ok(gor.every((g) => g[1] === 'gizli' && g[2]));
  await forumAnalizi(env, '7', T0 + 301_000, getir);
  assert.equal(gor.length, 4);
});

test('forum analizi: 401 "yetkisiz", ağ hatası/500/bozuk biçim "hata"; hata önbelleğe yazılmaz', async () => {
  bellekSifirla();
  const env = yerel({ FORUM_YONETICI_ANAHTARI: 'k' });
  assert.equal((await forumAnalizi(env, 30, T0, yanit({ hata: 'Yetkisiz.' }, 401))).durum, 'yetkisiz');
  assert.equal((await forumAnalizi(env, 30, T0, async () => { throw new Error('ağ'); })).durum, 'hata');
  assert.equal((await forumAnalizi(env, 30, T0, yanit({}, 500))).durum, 'hata');
  assert.equal((await forumAnalizi(env, 30, T0, yanit({ uyeler: {} }))).durum, 'hata');
  assert.equal((await forumAnalizi(env, 30, T0, yanit(veri()))).durum, 'tamam');
});

test('öneriler: eşiklere göre sade maddeler, önce uyarılar, en çok 6', () => {
  const o = forumOnerileri(veri());
  assert.ok(o.length <= 6);
  assert.equal(o[0].tur, 'uyari');
  assert.equal(o[0].metin, '2 şikâyet bekliyor. Bugün bak.');
  assert.ok(o.some((x) => x.metin.startsWith('4 soru cevapsız, en eskisi 6 gün önce soruldu.')));
  assert.ok(o.some((x) => x.metin.includes('İlk cevap genelde 4 saat')));
  const uyariSonu = o.findIndex((x) => x.tur === 'bilgi');
  assert.ok(uyariSonu === -1 || o.slice(uyariSonu).every((x) => x.tur === 'bilgi'));
  const sakin = forumOnerileri(veri({ soru: { donem: 0, cevaplanan: 0, cevapsiz: 0, cevapsiz_liste: [], ilk_cevap_medyan_dk: null, ilan: { n: 0, insan: 0 } }, aktif: {}, huni: {}, denetim: {}, saat: new Array(24).fill(0), odalar: [] }));
  assert.deepEqual(sakin, [{ tur: 'bilgi', metin: 'Belirgin bir sorun yok.' }]);
  const saat = forumOnerileri(veri({ denetim: {}, soru: { cevapsiz: 0, ilan: {} }, aktif: {}, huni: {} }));
  assert.ok(saat.some((x) => x.metin.startsWith('En yoğun saat 21:00–22:00')));
  assert.ok(saat.some((x) => x.metin === 'Önlisans bu dönemde sessiz.'));
});

test('/panel/forum-analiz: oturumsuz 401; oturumla JSON, anahtar yanıta ve sayfaya sızmaz', async () => {
  bellekSifirla();
  const env = { DB: sahteD1(), PANEL_ANAHTARI: 'dogru-anahtar-123', FORUM_YONETICI_ANAHTARI: 'forum-gizli' };
  const u = new URL('https://api.kpsstercihi.com/panel/forum-analiz?gun=7');
  assert.equal((await panelIstegi(new Request(u), env, u, { simdiMs: T0 })).status, 401);
  const e = yerel({ FORUM_YONETICI_ANAHTARI: 'forum-gizli' });
  const r = await panelIstegi(new Request(u), e, u, { simdiMs: T0, forumGetir: yanit(veri({ gun: 7, seri: seri(7) })) });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('cache-control'), 'no-store');
  const metin = await r.text();
  assert.ok(!metin.includes('forum-gizli'));
  assert.equal(JSON.parse(metin).veri.gun, 7);
  const bos = await panelIstegi(new Request(u), yerel(), u, { simdiMs: T0 });
  assert.deepEqual(await bos.json(), { durum: 'anahtar_yok' });
});

test('arayüz: Forum sekmesi, dönem seçici, durum metinleri ve elwyn renkleri sayfada', () => {
  const s = panelSayfasi('n');
  for (const parca of ['id="sekme-forum"', 'id="forum-aralik"', 'data-g="7"', 'data-g="30"', 'data-g="90"', 'id="forum-icerik"',
    'Forum anahtarı tanımlı değil', 'Foruma ulaşılamadı', 'Ne yapmalı?', 'Cevapsız sorular', 'https://kpsstercihi.com/forum/?b=',
    '#00939b', '#40456a', '#fcb315', '#ae5224', '#78cdd0', '#b5decc', '#fdbf68', '#f48067']) {
    assert.ok(s.includes(parca), parca);
  }
  assert.ok(!s.includes('innerHTML'));
});
