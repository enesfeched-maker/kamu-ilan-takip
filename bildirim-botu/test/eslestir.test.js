import { test } from 'node:test';
import assert from 'node:assert/strict';
import { uygunMu, ilanMetni, bugunIstanbul } from '../src/eslestir.js';

const BUGUN = '2026-10-01';
const k = (ek = {}) => ({ aktif: 1, onay: 1, akademik: 0, duzeyler: [], iller: [], kategoriler: [], kelimeler: [], ...ek });
const i = (ek = {}) => ({ id: 'x', baslik: 'Test', kurum: 'Kurum', son_tarih: '2026-10-10', ...ek });

test('aktif ve onaylı olmayan kullanıcıya uymaz', () => {
  assert.equal(uygunMu(i(), k({ aktif: 0 }), BUGUN), false);
  assert.equal(uygunMu(i(), k({ onay: 0 }), BUGUN), false);
  assert.equal(uygunMu(i(), k(), BUGUN), true);
});

test('süresi geçmiş ilan geçmez, bugün son gün geçer', () => {
  assert.equal(uygunMu(i({ son_tarih: '2026-09-30' }), k(), BUGUN), false);
  assert.equal(uygunMu(i({ son_tarih: '2026-10-01' }), k(), BUGUN), true);
});

test('akademik ilan akademik=0 iken geçmez', () => {
  assert.equal(uygunMu(i({ kategori: 'akademik' }), k(), BUGUN), false);
  assert.equal(uygunMu(i({ kategori: 'akademik' }), k({ akademik: 1 }), BUGUN), true);
});

test('düzey: boş tercih geçer, belirsiz ilan geçer, kesişim gerekir', () => {
  assert.equal(uygunMu(i({ ogrenim: ['lisans'] }), k(), BUGUN), true);
  assert.equal(uygunMu(i(), k({ duzeyler: ['lisans'] }), BUGUN), true);
  assert.equal(uygunMu(i({ ogrenim: [] }), k({ duzeyler: ['lisans'] }), BUGUN), true);
  assert.equal(uygunMu(i({ ogrenim: ['lisans', 'onlisans'] }), k({ duzeyler: ['onlisans'] }), BUGUN), true);
  assert.equal(uygunMu(i({ ogrenim: ['lisans'] }), k({ duzeyler: ['ortaogretim'] }), BUGUN), false);
});

test('il: boş tercih geçer, ilansız ilan geçer, kesişim gerekir', () => {
  assert.equal(uygunMu(i({ iller: ['Ankara'] }), k(), BUGUN), true);
  assert.equal(uygunMu(i(), k({ iller: ['Ankara'] }), BUGUN), true);
  assert.equal(uygunMu(i({ iller: [] }), k({ iller: ['Ankara'] }), BUGUN), true);
  assert.equal(uygunMu(i({ iller: ['Ankara', 'İzmir'] }), k({ iller: ['İzmir'] }), BUGUN), true);
  assert.equal(uygunMu(i({ iller: ['Ankara'] }), k({ iller: ['İzmir'] }), BUGUN), false);
});

test('kategori: boş tercih geçer, kategorisiz ilan geçer, listede olmalı', () => {
  assert.equal(uygunMu(i({ kategori: 'saglik' }), k(), BUGUN), true);
  assert.equal(uygunMu(i(), k({ kategoriler: ['saglik'] }), BUGUN), true);
  assert.equal(uygunMu(i({ kategori: 'saglik' }), k({ kategoriler: ['saglik', 'isci'] }), BUGUN), true);
  assert.equal(uygunMu(i({ kategori: 'bilisim' }), k({ kategoriler: ['saglik'] }), BUGUN), false);
});

test('kelime: Türkçe küçük harf, ilan metninde (şartlar dahil) geçmeli', () => {
  const ilan = i({ baslik: 'IĞDIR BELEDİYESİ', sartlar: [{ kadro: 'Avukat', metin: 'Hukuk fakültesi mezunu' }] });
  assert.equal(uygunMu(ilan, k({ kelimeler: ['ığdır'] }), BUGUN), true);
  assert.equal(uygunMu(ilan, k({ kelimeler: ['belediyesi'] }), BUGUN), true);
  assert.equal(uygunMu(ilan, k({ kelimeler: ['hukuk'] }), BUGUN), true);
  assert.equal(uygunMu(ilan, k({ kelimeler: ['bilgisayar', 'hukuk'] }), BUGUN), true);
  assert.equal(uygunMu(ilan, k({ kelimeler: ['bilgisayar'] }), BUGUN), false);
});

test('ilanMetni Türkçe küçük harfe çevirir', () => {
  assert.ok(ilanMetni({ baslik: 'İSTANBUL IŞIK' }).includes('istanbul ışık'));
});

test('bugunIstanbul gece yarısı sonrası İstanbul gününü verir', () => {
  assert.equal(bugunIstanbul(new Date('2026-09-30T21:30:00Z')), '2026-10-01');
  assert.equal(bugunIstanbul(new Date('2026-09-30T20:59:00Z')), '2026-09-30');
});
