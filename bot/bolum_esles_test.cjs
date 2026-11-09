/* docs/bolum/esles.js testleri (node bot/bolum_esles_test.cjs). Çıkış kodu ≠ 0 ise test düşmüştür.
 * En önemli kural: HİÇBİR İLAN KAYBOLMAZ; okunamayan şart "eşleşmiyor" değil "belirsiz" olur. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '../docs/bolum/esles.js'), 'utf8');
const mod = { exports: {} };
vm.runInNewContext(src, { module: mod, self: undefined });
const E = mod.exports;

const sinif = (rec, ad, duzey) => E.siniflandir(rec, E.bolumCoz(ad), duzey || '').kademe;
const sart = (metin, kadro) => ({ id: 'x', baslik: 'KURUM - ALIM', kurum: 'KURUM', sartlar: [{ kadro: kadro || 'Belgede belirtilen koşullar', metin }] });
let n = 0;
const test = (ad, fn) => { try { fn(); n++; } catch (e) { console.error('DÜŞTÜ:', ad, '\n', e.message); process.exitCode = 1; } };

test('fold Türkçe ve kesme işareti', () => {
  assert.strictEqual(E.fold("İSTANBUL Şişli'den Iğdır"), 'istanbul sisliden igdir');
});

test('bölüm adı parantez ve alternatifleri ayıklar', () => {
  assert.strictEqual(JSON.stringify(E.bolumCoz('Aktüerya / Aktüarya (İngilizce)')), JSON.stringify([['aktuerya'], ['aktuarya']]));
});

test('kesin: bölüm adı şartta geçiyor', () => {
  assert.strictEqual(sinif(sart('Hukuk fakültesi mezunu olmak'), 'Hukuk'), 'kesin');
  assert.strictEqual(sinif(sart('Fakültelerin dört yıllık bilgisayar mühendisliği, yazılım mühendisliği bölümlerinden mezun olmak.'), 'Bilgisayar Mühendisliği'), 'kesin');
});

test('muhtemel: ortak baş sözcüğü ve fakülte grubu', () => {
  assert.strictEqual(sinif(sart('Bilgisayar, yazılım ve elektrik mühendislikleri bölümlerinden mezun olmak.'), 'Bilgisayar Mühendisliği'), 'muhtemel');
  assert.strictEqual(sinif(sart('Hukuk, iktisat ve mühendislik fakültelerinden mezun olmak.'), 'Makine Mühendisliği'), 'muhtemel');
});

test('kısmi: bölümün ayırt edici sözcüğü geçiyor', () => {
  assert.strictEqual(sinif(sart('Muhasebe, finans ve bankacılık bölümlerinden mezun olmak.'), 'Muhasebe ve Vergi Uygulamaları'), 'muhtemel');
});

test('serbest: herhangi bir bölüm', () => {
  assert.strictEqual(sinif(sart('Herhangi bir lisans bölümünden mezun olmak.'), 'Hukuk'), 'serbest');
  assert.strictEqual(sinif(sart('Eski 1 Ön Lisans Herhangi bir ön lisans programından mezun olmak'), 'Hukuk'), 'serbest');
});

test('eşleşmiyor yalnız temiz ve tam bir başka-bölüm listesinde', () => {
  assert.strictEqual(sinif(sart('Üniversitelerin işletme, kamu yönetimi, muhasebe ve finans yönetimi programlarının birinden mezun olmak.'), 'Hukuk'), 'eslesmiyor');
});

test('BELİRSİZ: şart metni hiç yok', () => {
  assert.strictEqual(sinif({ id: 'a', baslik: 'X BELEDİYESİ MEMUR ALIMI', kurum: 'X' }, 'Hukuk'), 'belirsiz');
});

test('BELİRSİZ: kesik metin eşleşmiyor sayılmaz', () => {
  assert.strictEqual(sinif(sart('Fakültelerin dört yıllık makine mühendisliği, endüstri mühendisliği, elektrik mühendisliği bölümlerinden ya da bunlara denkliği yetkili makamlarca kabul edilmiş yurt dışındaki yükseköğretim kurumlarından…'), 'Hukuk'), 'belirsiz');
});

test('BELİRSİZ: bölüm listesi tabloda/ekte', () => {
  assert.strictEqual(sinif(sart('Üniversitelerin Tablo-1’de belirtilen bölümlerinden mezun olmak.'), 'Hukuk'), 'belirsiz');
  assert.strictEqual(sinif(sart('İlan metninde belirtilen bölümden mezun olmak şartıyla alınacaktır.'), 'Hukuk'), 'belirsiz');
});

test('BELİRSİZ: PDF tablo dökümü', () => {
  assert.strictEqual(sinif(sart('Sıra Kadro Hizmet Kadro Kadro KPSS No Unvanı Sınıfı Derecesi Adedi Niteliği Puan Türü Lisans düzeyinde eğitim veren fakültelerin muhasebe bölümlerinden mezun olmak'), 'Hukuk'), 'belirsiz');
});

test('BELİRSİZ: genel cümle (bölüm adı yok) eşleşmiyor sayılmaz', () => {
  assert.strictEqual(sinif(sart('Lisans mezunu olmak ve KPSS puanı almış olmak.'), 'Hukuk'), 'belirsiz');
});

test('BELİRSİZ: bazı kadroların şartı eksik', () => {
  const r = sart('Üniversitelerin işletme, kamu yönetimi, muhasebe ve finans yönetimi programlarının birinden mezun olmak.');
  r.sart_kadro_sayisi = 3;
  assert.strictEqual(sinif(r, 'Hukuk'), 'belirsiz');
});

test('boşluğu silinmiş OCR metni kesin değil ama gizlenmez', () => {
  const k = sinif(sart('Fakültelerinbilgisayarmühendisliğiveyazılımmühendisliğibölümlerindenmezunolmakveyabancıdilbilmek'), 'Bilgisayar Mühendisliği');
  assert.ok(k === 'muhtemel' || k === 'belirsiz', k);
});

test('sınav konusu geçişi kesin sayılmaz', () => {
  assert.notStrictEqual(sinif(sart('Görevde yükselme sınavı konuları: Temel Hukuk'), 'Hukuk'), 'kesin');
});

test('öğrenim düzeyi uyarısı grubu değiştirmez', () => {
  const r = sart('Hukuk fakültesi mezunu olmak');
  r.ogrenim = ['lisans'];
  const s = E.siniflandir(r, E.bolumCoz('Hukuk'), 'ortaogretim');
  assert.strictEqual(s.kademe, 'kesin');
  assert.ok(s.duzeyUyari);
});

test('kopya grubunda en iyi sonuç kazanır, kayıt kaybolmaz', () => {
  const a = { id: 'https://k/IlanDetay?i=A', link: 'https://k/IlanDetay?i=A', baslik: 'X', kurum: 'K' };
  const b = Object.assign(sart('Hukuk fakültesi mezunu olmak'), { id: 'iskur-b', link: 'https://i/b' });
  const key = (r) => (r.link.includes('?i=') ? new URL(r.link).searchParams.get('i') : r.id);
  const out = E.gruplaVeSinifla([a, b], E.bolumCoz('Hukuk'), '', new Map([['iskur-b', 'A']]), key);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].kademe, 'kesin');
  assert.strictEqual(out[0].uyeler.length, 2);
});

/* Denetçi bulguları (9 Kasım 2026) */
test('genel YÖK cümlesi bölüm listesi sayılmaz → eşleşmiyor olmaz', () => {
  assert.notStrictEqual(sinif(sart('En az tezli yüksek lisans derecesine sahip olmak veya lisans ve yüksek lisans derecesini birlikte veren programlardan mezun olmak şartı aranır.'), 'Hukuk'), 'eslesmiyor');
});
test('akademik ilanda genel etiketli kısmi şart → belirsiz', () => {
  const r = sart('Fakültelerin siber güvenlik mühendisliği anabilim dalı bölümlerinden mezun olmak, ilahiyat fakültesi arap dili ve edebiyatı bölümü mezunu olmak.');
  r.kategori = 'akademik';
  assert.strictEqual(sinif(r, 'Bilgisayar Mühendisliği'), 'belirsiz');
});
test('sütunları karışmış tablo metni → belirsiz', () => {
  assert.strictEqual(sinif(sart('Aday tarafından tercih fakülte veya yüksekokullardan edilecek İngilizce, Fransızca veya mezun veya belirtilen alanlarda mezun olmak.'), 'İktisat'), 'belirsiz');
});
test('Ekonomi ≡ İktisat', () => {
  assert.notStrictEqual(sinif(sart('Hukuk, iktisat, siyasal bilgiler, işletme fakültelerinden mezun olmak.'), 'Ekonomi'), 'eslesmiyor');
  assert.strictEqual(sinif(sart('İktisat bölümünden mezun olmak.'), 'Ekonomi'), 'kesin');
});
test('Tarih: "son başvuru tarihi" ve Tıp: "tıpta uzmanlık" kesin sayılmaz', () => {
  assert.notStrictEqual(sinif(sart('Son başvuru tarihi itibarıyla lisans mezunu olmak.'), 'Tarih'), 'kesin');
  assert.notStrictEqual(sinif(sart('Tıpta uzmanlık eğitimini tamamlamış olmak.'), 'Tıp'), 'kesin');
  assert.strictEqual(sinif(sart('Tarih bölümü lisans mezunu olmak.'), 'Tarih'), 'kesin');
});
test('Müh. kısaltması ve anlamsız girdi', () => {
  assert.strictEqual(sinif(sart('Bilgisayar mühendisliği bölümünden mezun olmak.'), 'Bilgisayar Müh.'), 'kesin');
  assert.strictEqual(E.bolumCoz('Ve').length, 0);
  assert.strictEqual(E.bolumCoz('ve ve').length, 0);
});
test('düzeltme yayımlanmış ilan eşleşmiyor sayılmaz', () => {
  const r = sart('Üniversitelerin işletme, kamu yönetimi, muhasebe ve finans yönetimi programlarının birinden mezun olmak.');
  r._duzeltme = true;
  assert.strictEqual(sinif(r, 'Hukuk'), 'belirsiz');
});
test('serbest ama farklı düzey: uyarı verir', () => {
  const s = E.siniflandir(sart('Ortaöğretim kurumlarının herhangi bir alanından mezun olmak.'), E.bolumCoz('Hukuk'), 'lisans');
  assert.strictEqual(s.kademe, 'serbest');
  assert.ok(s.duzeyUyari);
});
test('bitişik OCR metni gizlenmez', () => {
  const k = sinif(sart('Üniversitelerin işletme, kamu yönetimi, GüzelSanatlarFakültelerinin hukukbölümlerindenlisansmezunu olmak şartı aranır.'), 'Hukuk');
  assert.notStrictEqual(k, 'eslesmiyor');
});

/* Gerçek veri: her kayıt tam bir gruba girer; sayı korunur. */
const yol = path.join(__dirname, '../docs/ilanlar.json');
if (fs.existsSync(yol)) {
  const kayit = JSON.parse(fs.readFileSync(yol, 'utf8')).ilanlar.filter((i) => !i.duyuru_turu);
  for (const ad of ['Bilgisayar Mühendisliği', 'Hukuk', 'İşletme', 'Hemşirelik', 'Çocuk Gelişimi', 'Muhasebe ve Vergi Uygulamaları', 'xyzqw']) {
    test('gerçek veri korunumu: ' + ad, () => {
      const key = (r) => r.id;
      const out = E.gruplaVeSinifla(kayit, E.bolumCoz(ad), 'lisans', null, key);
      assert.strictEqual(out.length, kayit.length);
      const toplam = ['kesin', 'muhtemel', 'serbest', 'belirsiz', 'eslesmiyor'].reduce((a, k) => a + out.filter((s) => s.kademe === k).length, 0);
      assert.strictEqual(toplam, kayit.length);
      // şart metni olmayan hiçbir ilan "eşleşmiyor" olamaz
      for (const s of out) if (s.kademe === 'eslesmiyor') assert.ok(E.parcalar(s.rec).some((p) => p.kaynak === 'sart'), s.rec.id);
    });
  }
  test('gerçek veri: ünlü örnekler', () => {
    const find = (re) => kayit.find((i) => re.test(i.baslik || '') && re.test(i.kurum || ''));
    const bul = (kurum, baslik) => kayit.find((i) => kurum.test(i.kurum || '') && baslik.test(i.baslik || ''));
    const hukuk = bul(/ORMAN GENEL/i, /MÜFETTİŞ YARDIMCILIĞI/i);
    if (hukuk) assert.strictEqual(E.siniflandir(hukuk, E.bolumCoz('Hukuk'), '').kademe, 'kesin');
    void find;
  });
}
console.log(n + ' test geçti');
