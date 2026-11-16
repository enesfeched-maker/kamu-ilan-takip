// Tarayıcı betikleri (docs/avatar-ortak.js, docs/katip-senkron.js) için saf işlev testleri; DOM olmadan vm içinde çalışır.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { katipTemizle } from '../src/kart.js';

const docs = (a) => readFileSync(new URL(`../../docs/${a}`, import.meta.url), 'utf8');
const duz = (x) => JSON.parse(JSON.stringify(x));   // vm bölgesinden gelen nesneleri ana bölgeye çevirir (deepEqual için)

function avatarKit({ spriteTamam = true } = {}) {
  const pencere = {};
  const kutu = { window: pencere, document: { currentScript: { src: 'https://kpsstercihi.com/avatar-ortak.js?v=3' }, querySelectorAll: () => [] }, location: { hostname: 'kpsstercihi.com' },
    fetch: async () => ({ ok: spriteTamam }), Event: class {}, console };
  pencere.dispatchEvent = () => true;
  vm.runInNewContext(docs('avatar/avatarlar.js'), kutu);
  vm.runInNewContext(docs('avatar/piixpal.js'), kutu);
  kutu.sessionStorage = { getItem: () => null, setItem: () => {} };
  vm.runInNewContext(docs('avatar-ortak.js'), kutu);
  return pencere.kitAvatar;
}

test('avatar: varsayılan rumuzdan türer, kararlı, iki setin birleşik listesinden; büyük/küçük harf fark etmez', () => {
  const a = avatarKit();
  const v = duz(a.varsayilan('Ayse_Kaya'));
  assert.deepEqual(duz(a.varsayilan('ayse_kaya')), v);
  assert.deepEqual(duz(a.varsayilan('Ayse_Kaya')), v);
  const m = a.liste(), p = a.pxListe();
  const ornek = Array.from({ length: 400 }, (_, i) => duz(a.varsayilan(`uye${i}`)));
  assert.ok(ornek.every((x) => (x.set === 'svg' && m.avatarlar.some((y) => y.anahtar === x.k) && m.renkler.some((r) => r.anahtar === x.r && !r.koyu)) || (x.set === 'px' && p.avatarlar.some((y) => y.anahtar === x.k) && x.r === 'pixel' && x.h === 0)));
  const px = ornek.filter((x) => x.set === 'px').length, svg = ornek.length - px;
  assert.ok(px > 80 && svg > 80, `iki set de seçiliyor: ${px}/${svg}`);   // birleşik listeden orantılı dağılım
  assert.equal(new Set(ornek.map((x) => x.k)).size > 40, true);
  assert.equal(a.varsayilanSvg('x').set, 'svg');
});

test('avatar: coz svg ve Piixpal biçimlerini kabul eder; bozuk ya da listede olmayan (kaldırılmış) anahtar null -> varsayılana düşülür', () => {
  const a = avatarKit();
  assert.deepEqual(duz(a.coz('kedi:lila')), { set: 'svg', k: 'kedi', r: 'lila' });
  assert.deepEqual(duz(a.coz('px.loaf:pixel.0')), { set: 'px', k: 'loaf', r: 'pixel', h: 0 });
  assert.deepEqual(duz(a.coz('px.wizard:voxel.270')), { set: 'px', k: 'wizard', r: 'voxel', h: 270 });
  assert.equal(a.dizge(a.coz('px.tofu:dots.45')), 'px.tofu:dots.45'); assert.equal(a.dizge(a.coz('kedi:lila')), 'kedi:lila');
  for (const kotu of [null, undefined, 5, '', 'kedi', 'kedi:', ':lila', 'KEDI:lila', 'yok-boyle-bir-avatar:lila', 'kedi:lila:x', 'foto', '<svg>:lila', 'px.loti:pixel.0', 'px.loaf:neon.0', 'px.loaf', 'px.loaf:pixel']) assert.equal(a.coz(kotu), null, String(kotu));
});

test('Piixpal manifesti: 49 ad (loti yok), her biri bir gruba bağlı, biçim ve ton listeleri sunucuyla aynı', async () => {
  const a = avatarKit(), p = a.pxListe();
  assert.equal(p.avatarlar.length, 49);
  assert.ok(!p.avatarlar.some((x) => x.anahtar === 'loti'));
  for (const x of p.avatarlar) assert.ok(p.gruplar.some((g) => g.anahtar === x.grup), x.anahtar);
  assert.deepEqual(duz(p.gruplar.map((g) => g.ad)), ['Hayvanlar', 'Masa başı', 'Doğa', 'Karakterler', 'Tatlılar', 'Teknoloji']);
  const { PX_ADLAR, PX_BICIMLER, PX_TONLAR } = await import('../src/kart.js');
  assert.deepEqual([...PX_ADLAR].sort(), duz(p.avatarlar.map((x) => x.anahtar).sort()));
  assert.deepEqual([...PX_BICIMLER].sort(), duz(p.bicimler.map((x) => x.anahtar).sort()));
  assert.deepEqual([...PX_TONLAR].sort((x, y) => x - y), duz(p.tonlar.map((x) => x.ton)));
  const anlik = {}; vm.runInNewContext(docs('avatar/piixpal-anlik.js'), { window: anlik });
  for (const x of p.avatarlar) assert.match(anlik.KIT_PIIX_ANLIK[x.anahtar], /^data:image\/png;base64,/, x.anahtar);
});
test('avatar html: yükleme bitmeden harf (sonra svg ile değişir), sonra sprite; fotoğraf img; tüm metin kaçışlı', async () => {
  const a = avatarKit();
  const once = a.html({ rumuz: 'Zeynep', av: 'kedi:pembe' }, 32);
  assert.match(once, /^<span class="fr-av"[^>]*data-avu=/);
  assert.match(once, />Z<\/span>$/);
  await a.yukle();
  assert.equal(a.hazir(), true);
  const svg = a.html({ rumuz: 'Zeynep', av: 'kedi:pembe' }, 32);
  assert.match(svg, /^<svg class="fr-av fr-av-svg"/);
  assert.match(svg, /--av-z:#FBDCE8/);
  assert.match(svg, /<use href="https:\/\/kpsstercihi\.com\/avatar\/avatarlar\.svg#av-kedi"\/>/);
  assert.match(svg, /aria-hidden="true"/);
  // anahtar yoksa ya da bilinmiyorsa varsayılan hayvan çizilir
  for (const x of [{ rumuz: 'Zeynep' }, { rumuz: 'Zeynep', av: 'yok-boyle:lila' }, { rumuz: 'Zeynep', av: 'px.loti:pixel.0' }]) assert.match(a.html(x), /^<(svg|span|img) class="fr-av/);   // varsayılan: svg ya da (Piixpal ise görüntü yüklenene kadar) yer tutucu
  assert.match(a.html({ rumuz: 'Zeynep', av: 'px.loaf:pixel.0' }), /^<span class="fr-av"[^>]*data-avu=/);   // durağan görüntü hazır olana kadar harf
  const foto = a.html({ rumuz: 'Zeynep', av: 'foto', fs: 1790000001, fu: 7 }, 48);
  assert.match(foto, /^<img class="fr-av fr-av-foto" src="http:\/\/127\.0\.0\.1:8790\/foto\/7\?v=1790000001"|^<img class="fr-av fr-av-foto" src="https:\/\/forum-api\.kpsstercihi\.com\/foto\/7\?v=1790000001"/);
  assert.match(foto, /alt="" loading="lazy" decoding="async" width="48" height="48"/);
  // fotoğraf bilgisi eksikse varsayılana düşer, kaçış
  assert.match(a.html({ rumuz: 'Zeynep', av: 'foto' }), /^<(svg|span)/);
  const sinir = avatarKit({ spriteTamam: false });
  return sinir.yukle().then(() => {
    assert.equal(sinir.hazir(), false);
    const harf = sinir.html({ rumuz: '"><img src=x onerror=1>', av: 'kedi:lila' });
    assert.match(harf, /^<span class="fr-av"/);
    assert.ok(!harf.includes('<img'));
  });
});

// ---------- katiplik birleştirme ----------
const K = (() => { const m = { exports: {} }; vm.runInNewContext(docs('katip-senkron.js'), { module: m }); return m.exports; })();
const g = (t, ek = {}) => ({ t, m: 'sinav', s: 180, top: 100, hat: 3, atl: 0, net: 90, dk: 50, b: 1, no: 1, k: 'zk2025', ...ek });
const T0 = 1790000000000;

test('katip birleştir: geçmiş zaman damgasına göre birleşir (tekrarsız, yeniden eskiye, en çok 200)', () => {
  const sunucu = { k: { gecmis: [g(T0 + 3000), g(T0 + 2000), g(T0 + 1000)] } };
  const yerel = { k: { gecmis: [g(T0 + 4000), g(T0 + 2000), g(T0 + 500)] } };
  const r = duz(K.birlestir(sunucu, yerel));
  assert.deepEqual(r.k.gecmis.map((x) => x.t), [T0 + 4000, T0 + 3000, T0 + 2000, T0 + 1000, T0 + 500]);
  const cok = duz(K.birlestir({ k: { gecmis: Array.from({ length: 150 }, (_, i) => g(T0 + i)) } }, { k: { gecmis: Array.from({ length: 150 }, (_, i) => g(T0 + 1000 + i)) } }));
  assert.equal(cok.k.gecmis.length, 200); assert.equal(cok.k.gecmis[0].t, T0 + 1149);
});

test('katip birleştir: hatalar en büyük sayı + ilk 100; rozetler birleşir; günlük günden güne net büyük olan; ders yıldızı ve oyun/antrenman rekorları en büyük', () => {
  const hs = Object.fromEntries(Array.from({ length: 80 }, (_, i) => [`kelime${String.fromCharCode(97 + (i % 26))}`.slice(0, 7) + String.fromCharCode(97 + Math.floor(i / 26)), i + 1]));
  const r = duz(K.birlestir(
    { k: { hatalar: { elma: 5, armut: 2, ...hs }, rozetler: ['ilk', 'd10'], gunluk: { '2026-11-10': { net: 90, top: 100, hat: 2, b: 1 }, '2026-11-11': { net: 80 } } }, d: { Q: { 0: { y: 2, t: 5 }, 1: { y: 3, t: 1 } } }, o: { dosya: 100, hata: 10 }, a: { rekor: { hiz: 40, uzun: 20 }, gecmis: [{ t: T0, m: 'hiz', net: 40 }] } },
    { k: { hatalar: { elma: 3, kitap: 9 }, rozetler: ['ilk', 'seri3'], gunluk: { '2026-11-10': { net: 95, top: 100, hat: 1, b: 1 }, '2026-11-12': { net: 70 } } }, d: { Q: { 0: { y: 3, t: 9 }, 2: { y: 1, t: 1 } }, F: { 0: { y: 1, t: 1 } } }, o: { dosya: 80, hata: 50 }, a: { rekor: { hiz: 55 }, gecmis: [{ t: T0 + 1, m: 'hiz', net: 55 }] } },
  ));
  assert.equal(r.k.hatalar.elma, 5); assert.equal(r.k.hatalar.kitap, 9); assert.ok(Object.keys(r.k.hatalar).length <= 100);
  assert.deepEqual(r.k.rozetler, ['ilk', 'd10', 'seri3']);
  assert.equal(r.k.gunluk['2026-11-10'].net, 95); assert.equal(r.k.gunluk['2026-11-11'].net, 80); assert.equal(r.k.gunluk['2026-11-12'].net, 70);
  assert.equal(r.d.Q[0].y, 3); assert.equal(r.d.Q[1].y, 3); assert.equal(r.d.Q[2].y, 1); assert.equal(r.d.F[0].y, 1);
  assert.deepEqual(r.o, { dosya: 100, hata: 50 });
  assert.deepEqual(r.a.rekor, { hiz: 55, uzun: 20 });
  assert.equal(r.a.gecmis.length, 2);
});

test('katip birleştir: yolda daha yeni değişiklik (yol.g) kazanır, eşitse yerel; günlük 120 gün', () => {
  const yeni = duz(K.birlestir({ k: { yol: { tarih: '2026-12-01', hedef: 100, g: 2000 } } }, { k: { yol: { tarih: '2026-11-20', hedef: 80, g: 1000 } } }));
  assert.deepEqual(yeni.k.yol, { tarih: '2026-12-01', hedef: 100, g: 2000 });
  const yerel = duz(K.birlestir({ k: { yol: { tarih: '2026-12-01', hedef: 100, g: 1000 } } }, { k: { yol: { tarih: '2026-11-20', hedef: 80, g: 1000 } } }));
  assert.equal(yerel.k.yol.hedef, 80);
  const zamansiz = duz(K.birlestir({ k: { yol: { tarih: '', hedef: 90 } } }, { k: { yol: { tarih: '2026-11-20', hedef: 120 } } }));
  assert.equal(zamansiz.k.yol.hedef, 120);   // ikisinde de g yok: yerel
  const gunluk = Object.fromEntries(Array.from({ length: 150 }, (_, i) => [`2026-${String(1 + Math.floor(i / 28)).padStart(2, '0')}-${String(1 + (i % 28)).padStart(2, '0')}`, { net: i }]));
  const r = duz(K.birlestir({ k: { gunluk } }, {}));
  assert.equal(Object.keys(r.k.gunluk).length, 120);
});

test('katip: boş + boş boş kalır; birleştirme yinelenebilir (idempotent) ve sıradan bağımsız veri kaybetmez', () => {
  assert.equal(K.bosMu(K.bos()), true);
  const a = { k: { gecmis: [g(T0), g(T0 + 1)], rozetler: ['ilk'], hatalar: { elma: 2 } }, d: { Q: { 0: { y: 2, t: 1 } } }, o: { dosya: 5, hata: 1 } };
  const b = { k: { gecmis: [g(T0 + 2)], rozetler: ['d10'], hatalar: { elma: 4, kitap: 1 } }, o: { dosya: 7, hata: 0 } };
  const ab = duz(K.birlestir(a, b)), ba = duz(K.birlestir(b, a));
  assert.deepEqual(ab.k.gecmis, ba.k.gecmis); assert.deepEqual(ab.k.hatalar, ba.k.hatalar); assert.deepEqual(ab.o, ba.o); assert.deepEqual(ab.d, ba.d);
  assert.deepEqual(duz(K.birlestir(ab, ab)), ab);
  assert.equal(K.bosMu(ab), false);
});

test('katip topla / uygula: depodaki eşitlenmeyen alanlar (özel metin, takma ad, antrenman ayarı) korunur; boyut sınırı', () => {
  const depo = {
    'kit-katip': { gecmis: [g(T0)], hatalar: { elma: 1 }, rozetler: ['ilk'], gunluk: {}, yol: { tarih: '', hedef: 90 }, ayar: { aday: 'Gizli Ad', klavye: 'F', sure: 180 }, ozel: 'özel metnim', aday: 'x' },
    'kit-katip-ders': { Q: { 0: { y: 3, t: 5 } } }, 'kit-katip-oyun': { dosya: 3, hata: 1 }, 'kit-katip-antrenman': { rekor: { hiz: 44 }, gecmis: [{ t: T0, m: 'hiz', net: 44 }], ayar: { mod: 'hiz', adet: 200 } },
  };
  const oku = (a) => (depo[a] === undefined ? null : JSON.parse(JSON.stringify(depo[a])));
  const yaz = (a, v) => { depo[a] = JSON.parse(JSON.stringify(v)); };
  const p = duz(K.topla(oku));
  assert.equal(p.k.ayar.klavye, 'F'); assert.ok(!('ozel' in p.k)); assert.ok(!JSON.stringify(p).includes('Gizli Ad')); assert.ok(!JSON.stringify(p).includes('özel metnim'));
  assert.equal(p.a.rekor.hiz, 44); assert.ok(!('ayar' in p.a));
  const birlesik = K.birlestir({ k: { gecmis: [g(T0 + 9)] } }, p);
  K.uygula(birlesik, oku, yaz);
  assert.equal(depo['kit-katip'].gecmis.length, 2);
  assert.equal(depo['kit-katip'].ozel, 'özel metnim'); assert.equal(depo['kit-katip'].ayar.aday, 'Gizli Ad'); assert.equal(depo['kit-katip'].ayar.sure, 180); assert.equal(depo['kit-katip'].ayar.klavye, 'F');
  assert.equal(depo['kit-katip-antrenman'].ayar.mod, 'hiz'); assert.equal(depo['kit-katip-antrenman'].rekor.hiz, 44);
  assert.equal(depo['kit-katip-ders'].Q[0].y, 3);
  // boyut: 200 geçmiş + 120 gün + 100 hata 30 KB altına iner
  const dev = K.birlestir({}, { k: {
    gecmis: Array.from({ length: 250 }, (_, i) => g(T0 + i, { s: 180 })),
    hatalar: Object.fromEntries(Array.from({ length: 150 }, (_, i) => [`çalışmadığımız${String.fromCharCode(97 + (i % 26))}${String.fromCharCode(97 + Math.floor(i / 26))}`, 999])),
    gunluk: Object.fromEntries(Array.from({ length: 150 }, (_, i) => [`2026-${String(1 + Math.floor(i / 28)).padStart(2, '0')}-${String(1 + (i % 28)).padStart(2, '0')}`, { net: 100, top: 120, hat: 3, b: 1 }])),
  } });
  K.kirp(dev);
  assert.ok(JSON.stringify(dev).length <= 30000, String(JSON.stringify(dev).length));
});

test('istemci ve sunucu katiplik biçimi uyumlu: birleşik veri sunucu temizleyicisinden kayıpsız geçer', () => {
  const b = duz(K.birlestir({}, { k: { gecmis: [g(T0), g(T0 + 5)], hatalar: { elma: 2 }, rozetler: ['ilk', 'seri30'], gunluk: { '2026-11-10': { net: 90, top: 100, hat: 2, b: 1 } }, yol: { tarih: '2026-12-01', hedef: 100, g: 7 } },
    d: { Q: { 0: { y: 3, t: T0 } } }, o: { dosya: 4, hata: 2 }, a: { rekor: { hiz: 50 }, gecmis: [{ t: T0, m: 'hiz', net: 50, n: 60, h: 10, s: 60 }] } }));
  const s = duz(katipTemizle(b));
  assert.deepEqual(s.k.gecmis, b.k.gecmis);
  assert.deepEqual(s.k.hatalar, b.k.hatalar); assert.deepEqual(s.k.rozetler, b.k.rozetler); assert.deepEqual(s.k.gunluk, b.k.gunluk); assert.deepEqual(s.k.yol, b.k.yol);
  assert.deepEqual(s.d, b.d); assert.deepEqual(s.o, b.o); assert.deepEqual(s.a, b.a);
});


test('katip birlestir: sıfırlama (z) iki yönde de eski kayıtları düşürür; uygula yerel eski geçmişi z öncesinden geri getirmez', () => {
  const Z = T0 + 5000;
  const sunucu = { k: { gecmis: [g(T0 + 6000)], hatalar: {}, rozetler: [] }, z: Z };
  const yerel = { k: { gecmis: [g(T0 + 7000), g(T0 + 1000)], hatalar: { elma: 4 }, rozetler: ['ilk'], gunluk: { '2026-09-01': { net: 90 } } } };
  for (const r of [duz(K.birlestir(sunucu, yerel)), duz(K.birlestir(yerel, sunucu))]) {
    assert.deepEqual(r.k.gecmis.map((x) => x.t), [T0 + 7000, T0 + 6000]);
    assert.deepEqual(r.k.hatalar, {}); assert.deepEqual(r.k.rozetler, []); assert.deepEqual(r.k.gunluk, {}); assert.equal(r.z, Z);
  }
  const depo = { 'kit-katip': { gecmis: [g(T0 + 7000), g(T0 + 1000)], hatalar: { elma: 4 } } };
  const oku = (a) => (depo[a] === undefined ? null : JSON.parse(JSON.stringify(depo[a])));
  const yaz = (a, v) => { depo[a] = JSON.parse(JSON.stringify(v)); };
  K.uygula(K.birlestir(sunucu, K.topla(oku)), oku, yaz, true);
  assert.deepEqual(depo['kit-katip'].gecmis.map((x) => x.t), [T0 + 7000, T0 + 6000]); assert.equal(depo['kit-katip'].z, Z);
  assert.equal(duz(K.topla(oku)).z, Z);   // yerel sıfırlama zamanı sonraki gönderimde de gider
  assert.equal(katipTemizle(duz(K.topla(oku))).z, Z);
});