import test from 'node:test';
import assert from 'node:assert/strict';
import { paketDogrula, olayDogrula, metinTemizle, sayfaTuru, MAKS_BAYT } from '../src/dogrula.js';
import { paket } from './sahte-d1.js';

const dogrula = (o) => paketDogrula(JSON.stringify(o));

test('geçerli paket kabul edilir, bilinmeyen alanlar atılır', () => {
  const p = dogrula(paket([{ t: 'sayfa', p: '/', v: 'bugun', f: 1, kimlik: 'x', email: 'a@b.c' }], { evil: 1 }));
  assert.equal(p.olaylar.length, 1);
  assert.deepEqual(Object.keys(p.olaylar[0]).sort(), ['a', 'f', 'h', 'k', 'n', 'n2', 'p', 'sy', 't', 'v', 'x']);
  assert.equal(p.rhost, 'google.com');
  assert.equal(p.dil, 'tr-tr');
  assert.equal(p.evil, undefined);
});

test('zarf doğrulaması: oturum kodu, olay sayısı, bayt sınırı, bozuk JSON', () => {
  assert.equal(dogrula({ ...paket([{ t: 'sayfa', p: '/' }]), s: 'a' }).hata, 'oturum');
  assert.equal(dogrula(paket([])).hata, 'olaylar');
  assert.equal(dogrula(paket(Array.from({ length: 21 }, () => ({ t: 'sayfa', p: '/' })))).hata, 'olaylar');
  assert.equal(dogrula(paket(Array.from({ length: 20 }, () => ({ t: 'sayfa', p: '/' })))).olaylar.length, 20);
  assert.equal(paketDogrula('{bozuk').hata, 'json');
  assert.equal(paketDogrula('[]').hata, 'sekil');
  assert.equal(paketDogrula('').hata, 'bos');
  assert.equal(paketDogrula(JSON.stringify(paket([{ t: 'hata', p: '/', x: 'a'.repeat(MAKS_BAYT) }]))).hata, 'buyuk');
});

test('geçersiz olaylar sessizce düşer', () => {
  const p = dogrula(paket([
    { t: 'bilinmeyen', p: '/' }, { t: 'sayfa' }, { t: 'sayfa', p: 'https://evil.example/' }, { t: 'sayfa', p: '/<script>' },
    { t: 'aktif', p: '/', n: 0 }, { t: 'aktif', p: '/', n: 9999 }, { t: 'kaydirma', p: '/', n: 33 }, { t: 'tikla', p: '/' }, { t: 'tikla', p: '/', a: 'Büyük Harf' },
    { t: 'hata', p: '/' }, { t: 'hiz', p: '/' },
    { t: 'sayfa', p: '/' },
  ]));
  assert.equal(p.olaylar.length, 1);
});

test('yol: sorgu ve # atılır, ilan/kurum/taban türleri çıkarılır', () => {
  assert.equal(olayDogrula({ t: 'sayfa', p: '/ilan/abc-123/?utm_source=x#y' }).k, 'abc-123');
  assert.equal(olayDogrula({ t: 'sayfa', p: '/ilan/abc-123/' }).sy, 'ilan');
  assert.deepEqual(sayfaTuru('/kurum/ankara-buyuksehir/'), { sy: 'kurum', k: 'ankara-buyuksehir' });
  assert.deepEqual(sayfaTuru('/kpss-taban-puanlari/lisans/memur/'), { sy: 'taban', k: 'lisans/memur' });
  assert.deepEqual(sayfaTuru('/kpss-taban-puanlari/'), { sy: 'taban', k: null });
  assert.equal(sayfaTuru('/puanlar/').sy, 'robot');
  assert.equal(sayfaTuru('/').sy, 'ana');
  assert.equal(olayDogrula({ t: '404', p: '/yok/sayfa' }).sy, '404');
});

test('metinler kısaltılır; kişisel veri benzeri girdi temizlenir', () => {
  const e = olayDogrula({ t: 'tikla', p: '/', a: 'arama', x: '  BELEDİYE   Zabıta ' + 'x'.repeat(100), n: 3 });
  assert.equal(e.x.length, 60);
  assert.ok(e.x.startsWith('belediye zabıta'));
  assert.equal(olayDogrula({ t: 'tikla', p: '/', a: 'arama', x: 'ali@ornek.com', n: 0 }).x, '[temizlendi]');
  assert.equal(olayDogrula({ t: 'tikla', p: '/', a: 'arama', x: '12345678901', n: 0 }).x, '[temizlendi]');
  assert.equal(olayDogrula({ t: 'tikla', p: '/', a: 'arama', x: '0532 123 45 67', n: 0 }).x, '[temizlendi]');
  assert.equal(metinTemizle('kpss 2026 lisans', 60), 'kpss 2026 lisans');
  assert.equal(olayDogrula({ t: 'hata', p: '/', x: 'Hata at https://kpsstercihi.com/a.js?token=abc:1:2' }).x, 'Hata at https://kpsstercihi.com/a.js?');
});

test('sayılar sınırlanır', () => {
  assert.equal(olayDogrula({ t: 'aktif', p: '/', n: 15.4 }).n, 15);
  assert.equal(olayDogrula({ t: 'kaydirma', p: '/', n: 50 }).n, 50);
  assert.equal(olayDogrula({ t: 'hiz', p: '/', n: 1800, n2: 120 }).n2, 120);
  assert.equal(olayDogrula({ t: 'tikla', p: '/', a: 'manset_tikla', n: -3 }).n, null);
});
