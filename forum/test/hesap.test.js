import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
// docs/hesap.js tarayıcı betiğidir (üst klasörde package.json type=module olduğundan require ile yüklenmez); `document` yokken yalnız saf işlevleri dışa verir.
const modul = { exports: {} };
vm.runInNewContext(readFileSync(new URL('../../docs/hesap.js', import.meta.url), 'utf8'), { module: modul });
const duz = (f) => (...a) => JSON.parse(JSON.stringify(f(...a)));   // vm'den gelen nesneler başka bir bölgeden: deepEqual için ana bölgeye çevrilir
const { birlestir, esitle, gonderilecek } = Object.fromEntries(['birlestir', 'esitle', 'gonderilecek'].map((k) => [k, duz(modul.exports[k])]));
const { anahtar, yerelKimlik, gecerli } = modul.exports;
import { kayitliTemizle } from '../src/kayitli.js';

const U = (i) => `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`;
const KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=';
const SBB = `sbb-${'ab12cd34ef56'.repeat(2)}`, CSB = 'csb-12345';

test('anahtar / yerelKimlik: Kariyer Kapısı adresi <-> UUID, diğer kaynaklarda kimlik anahtarın kendisi', () => {
  assert.equal(anahtar(KK + U(1)), U(1));
  assert.equal(anahtar(U(1)), U(1));
  assert.equal(anahtar(SBB), SBB); assert.equal(anahtar(CSB), CSB);
  assert.equal(anahtar(KK + U(1).toUpperCase()), U(1));   // büyük harf anahtar küçültülür
  for (const kotu of ['x', '', null, 5, 'https://example.com/IlanDetay?i=' + U(1), KK + 'zz', KK + U(1) + '&x=1']) assert.equal(anahtar(kotu), null, String(kotu));
  assert.equal(yerelKimlik(U(1)), KK + U(1)); assert.equal(yerelKimlik(SBB), SBB); assert.equal(yerelKimlik(CSB), CSB);
  // sunucu deseni ile istemci deseni aynı kimlikleri kabul eder
  for (const k of [U(1), SBB, CSB, 'csb-12', 'sbb-zz', 'x']) assert.equal(gecerli(k), kayitliTemizle([k]).length === 1, k);
});

test('birlestir: sunucu sırası önde, yerelde olanlar arkaya (yerel kimlik biçimi korunur), tekrarsız; fark varsa bir kez yüklenir', () => {
  const r = birlestir([U(1), U(2)], [KK + U(2), KK + U(3), SBB]);
  assert.deepEqual(r.gonderilecek, [U(1), U(2), U(3), SBB]);
  assert.deepEqual(r.yerel, [KK + U(1), KK + U(2), KK + U(3), SBB]);
  assert.equal(r.degisti, true);
});

test('birlestir: yerelde yeni bir şey yoksa yükleme gerekmez', () => {
  const r = birlestir([U(1), U(2)], [KK + U(2)]);
  assert.deepEqual(r.yerel, [KK + U(1), KK + U(2)]);
  assert.equal(r.degisti, false);
  assert.equal(birlestir([], []).degisti, false);
  assert.equal(birlestir([U(1)], []).degisti, false);
  assert.equal(birlestir([], [CSB]).degisti, true);
  assert.equal(birlestir([U(1)], [U(1), KK + U(1)]).degisti, false);   // aynı ilanın iki yazımı tek sayılır
});

test('birlestir: anahtarsız yerel kayıt cihazda kalır ama sunucuya gitmez; sunucudaki geçersizler atılır', () => {
  const r = birlestir(['x', U(1)], ['eski-bicim-id', KK + U(1), 5, null, '', 'a'.repeat(81)]);
  assert.deepEqual(r.yerel, [KK + U(1), 'eski-bicim-id']);
  assert.deepEqual(r.gonderilecek, [U(1)]);
  assert.equal(r.degisti, false);
  const k = birlestir(null, undefined);
  assert.deepEqual(k.yerel, []); assert.equal(k.degisti, false);
});

test('birlestir: 300 sınırı, en eskiler (öndekiler) düşer; __proto__ gibi kayıtlar zarar vermez', () => {
  const sunucu = Array.from({ length: 290 }, (_, i) => U(i));
  const yerel = Array.from({ length: 20 }, (_, i) => KK + U(1000 + i));
  const r = birlestir(sunucu, yerel);
  assert.equal(r.gonderilecek.length, 300);
  assert.equal(r.gonderilecek[0], U(10));
  assert.equal(r.gonderilecek[299], U(1019));
  assert.equal(r.yerel.length, 300);
  assert.equal(r.degisti, true);
  assert.deepEqual(birlestir([], ['__proto__', 'constructor', KK + U(1)]).yerel, [KK + U(1), '__proto__', 'constructor']);
});

test('esitle: eşleşmiş hesapta sunucu esastır (silmeler gelir); aynıysa dokunulmaz', () => {
  assert.equal(esitle([U(1)], [KK + U(1)]).ayni, true);
  const e = esitle([U(1), SBB], [KK + U(1), KK + U(9), 'eski-id']);
  assert.equal(e.ayni, false);
  assert.deepEqual(e.yerel, [KK + U(1), SBB, 'eski-id']);   // yerelde fazla olan U(9) düştü, anahtarsız kayıt kaldı
  assert.equal(esitle([], [KK + U(9)]).ayni, false);
  assert.deepEqual(esitle([], [KK + U(9)]).yerel, []);
});

test('gonderilecek: yalnız anahtarlar, tekrarsız, en yeni 300', () => {
  assert.deepEqual(gonderilecek([KK + U(1), 'x', U(1), CSB]), [U(1), CSB]);
  assert.equal(gonderilecek(Array.from({ length: 400 }, (_, i) => U(i))).length, 300);
  assert.deepEqual(gonderilecek('metin'), []);
});