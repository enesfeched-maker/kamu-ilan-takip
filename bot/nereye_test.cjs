/* docs/nereye/cekirdek.js testleri (node bot/nereye_test.cjs). Çıkış kodu ≠ 0 ise test düşmüştür.
 * En önemli kural: emin olunmayan kadro "hemen başvurabilirsin" grubuna GİRMEZ. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const yukle = (yol) => { const mod = { exports: {} }; vm.runInNewContext(fs.readFileSync(path.join(__dirname, yol), 'utf8'), { module: mod, self: undefined }); return mod.exports; };
const E = yukle('../docs/bolum/esles.js');
const C = yukle('../docs/nereye/cekirdek.js')(E);

let n = 0;
const esit = (a, b) => assert.strictEqual(JSON.stringify(a), JSON.stringify(b));   // vm bağlamındaki diziler başka prototipte
const test = (ad, fn) => { try { fn(); n++; } catch (e) { console.error('DÜŞTÜ:', ad, '\n', e.stack || e.message); process.exitCode = 1; } };
const ilan = (o) => Object.assign({ id: 'https://kariyerkapisi.gov.tr/IlanDetay?i=' + (o.k || 'a'), link: 'https://kariyerkapisi.gov.tr/IlanDetay?i=' + (o.k || 'a'), baslik: 'KURUM - ALIM', kurum: 'KURUM', son_tarih: '2099-01-10' }, o);
const kadro = (unvan, kosul, ek) => Object.assign({ unvan, adet: 2, ogrenim: 'lisans', puan_turu: 'P3', en_dusuk_puan: null, kosullar: [kosul] }, ek || {});
const HEM = 'Hemşirelik lisans programından mezun olmak.';

test('puan şartı: "ve üzeri", "en az … puan", yüzde sayılmaz, YDS sayılmaz', () => {
  assert.strictEqual(C.puanSarti({ ozet: '2024 KPSS P3 puan türünden 60 (altmış) ve üzeri puan almış olmak.' }), 60);
  assert.strictEqual(C.puanSarti({ yz_ortak: ['2024 KPSS (B) grubu P3 puan türünden en az 55 puan almış olmak.'] }), 55);
  assert.strictEqual(C.puanSarti({ ozet: 'KPSS P3 puanının yüzde yetmişi (%70) ile alınacaktır.' }), null);
  assert.strictEqual(C.puanSarti({ ozet: 'YDS sınavından en az 70 puan almış olmak.' }), null);
  assert.strictEqual(C.puanSarti({ ozet: 'KPSS P93 65 ve üzeri; KPSS P94 60 ve üzeri puan.' }), 60);
});

test('başvuru şekli: olumsuz cümle atlanır, Kariyer Kapısı bağlantısı ilanın kendisi', () => {
  const r = ilan({ basvuru_notu: 'Kariyer Kapısı üzerinden yapılır. Posta yolu veya şahsen yapılan başvurular kabul edilmeyecektir.' });
  const s = C.basvuruSekli(r);
  assert.match(s.ad, /Kariyer Kapısı/);
  assert.strictEqual(s.link, r.link);
  assert.match(C.basvuruSekli({ link: 'https://x.gov.tr', basvuru_notu: 'Başvurular belediyeye şahsen yapılacaktır.' }).ad, /şahsen/);
  assert.match(C.basvuruSekli({ link: 'https://x.gov.tr', basvuru_notu: '' }).ad, /resmî ilanda/);
});

test('kadro bazlı: bölüm şartta geçen kadro hemen, geçmeyen kadro gösterilmez', () => {
  const r = ilan({ yz_kadrolar: [kadro('Hemşire', HEM), kadro('Mühendis', 'Bilgisayar mühendisliği lisans programından mezun olmak.')] });
  const d = C.degerlendir(r, 'Hemşirelik', 'lisans', 75);
  assert.strictEqual(d.grup, 'hemen');
  esit(d.kadrolar.map((k) => k.ad), ['Hemşire']);
  assert.strictEqual(C.degerlendir(r, 'Tarih', 'lisans', 75).grup, 'degil');
});

test('kadro puanı: altında kalan "yetmiyor", eşit/üstü "hemen", puanı olmayan aday KPSS\'li kadroda "kontrol"', () => {
  const r = ilan({ yz_kadrolar: [kadro('Hemşire', HEM, { en_dusuk_puan: 70 })] });
  assert.strictEqual(C.degerlendir(r, 'Hemşirelik', 'lisans', 69.99).grup, 'yetmiyor');
  assert.strictEqual(C.degerlendir(r, 'Hemşirelik', 'lisans', 70).grup, 'hemen');
  const d = C.degerlendir(r, 'Hemşirelik', 'lisans', null);
  assert.strictEqual(d.grup, 'kontrol');
  assert.match(d.neden, /KPSS puanı gerekiyor \(en az 70\)/);
});

test('denetim 1: kadronun kendi maddesindeki eşik, ilanın en düşük eşiğinden önce gelir', () => {
  const r = ilan({ kadro_detay: [
    { unvan: 'Uzman', adet: 3, maddeler: ['İşletme bölümünden mezun olmak,', 'KPSS P3 puan türünden 80 ve üzeri puan almış olmak.'] },
    { unvan: 'Memur', adet: 1, maddeler: ['Hukuk fakültesinden mezun olmak,', 'KPSS P3 puan türünden 70 ve üzeri puan almış olmak.'] }] });
  assert.strictEqual(C.degerlendir(r, 'İşletme', 'lisans', 75).grup, 'yetmiyor');
  assert.strictEqual(C.degerlendir(r, 'Hukuk', 'lisans', 75).grup, 'hemen');
  // kadroda eşik yok, ilanda farklı eşikler var → kontrol
  const r2 = ilan({ ozet: 'KPSS P3 puan türünden 80 ve üzeri; bazı kadrolar için KPSS P3 70 ve üzeri puan.', yz_kadrolar: [kadro('Uzman', 'İşletme bölümünden mezun olmak.')] });
  assert.strictEqual(C.degerlendir(r2, 'İşletme', 'lisans', 75).grup, 'kontrol');
});

test('denetim 2: çok değerli puan türü okunur; A grubu türü P3 adayına "hemen" değil', () => {
  for (const t of ['P14,P15,P16', 'P14P15P16P17P18', 'KPSSP48']) {
    const r = ilan({ yz_kadrolar: [kadro('Uzman Yardımcısı', 'İktisat bölümünden mezun olmak.', { puan_turu: t })] });
    assert.strictEqual(C.degerlendir(r, 'İktisat', 'lisans', 75).grup, 'kontrol', t);
  }
  const r = ilan({ yz_kadrolar: [kadro('Uzman', 'İktisat bölümünden mezun olmak.', { puan_turu: 'P1,P2,P3' })] });
  assert.strictEqual(C.degerlendir(r, 'İktisat', 'lisans', 75).grup, 'hemen');
  // tür okunmamış ama metinde yalnız A grubu türü yazıyor
  const r3 = ilan({ yz_ortak: ['KPSSP8, KPSSP9 puan türlerinden 70 ve üzeri puan almış olmak.'], yz_kadrolar: [kadro('Uzman Yardımcısı', 'İktisat bölümünden mezun olmak.', { puan_turu: null })] });
  assert.strictEqual(C.degerlendir(r3, 'İktisat', 'lisans', 85).grup, 'kontrol');
});

test('denetim 4: YDS, sözlü sınav ve türe göre eşik', () => {
  esit(C.puanSartlari('KPSS P3 puan türünden 80 ve üzeri puan almış olmak, YDS den en az 50 puan almış olmak.').map((s) => s.v), [80]);
  esit(C.puanSartlari('Sözlü sınavda 100 tam puan üzerinden 60 ve üzeri puan alanlar başarılı sayılır.'), []);
  assert.strictEqual(C.esikBul('KPSS P93 65 ve üzeri; KPSS P94 60 ve üzeri puan almış olmak.', 'P93').esik, 65);
  assert.strictEqual(C.esikBul('KPSS P93 65 ve üzeri; KPSS P94 60 ve üzeri puan almış olmak.', 'P94').esik, 60);
});

test('denetim 5: genel lise adayı belirli alan isteyen kadroda "hemen" değil', () => {
  for (const m of ['Lise ve dengi okulların Makine alanından mezun olmak.', 'Lise veya dengi okulların Bilgisayar alanından mezun olmak.']) {
    const r = ilan({ yz_kadrolar: [kadro('Teknisyen', m, { ogrenim: 'ortaogretim', puan_turu: 'P94' })] });
    assert.notStrictEqual(C.degerlendir(r, '', 'ortaogretim', 80).grup, 'hemen', m);
  }
});

test('denetim 6: düzey yalnız ortak şartta yazıyorsa lisans adayına lise kadrosu gösterilmez', () => {
  const r = ilan({ yz_ortak: ['Ortaöğretim (lise ve dengi) okul mezunu olmak.'], yz_kadrolar: [kadro('Güvenlik', 'Herhangi bir bölümden mezun olmak.', { ogrenim: null, puan_turu: null })] });
  assert.strictEqual(C.degerlendir(r, 'İktisat', 'lisans', 80).grup, 'degil');
});

test('kopya: bir üyesi kurum içi olan grup düşer; birincili listede olmayan kopya kendi adresiyle kalır', () => {
  const ana = ilan({ k: 'ana', baslik: 'KURUM - GÖREVDE YÜKSELME', yz_kadrolar: [kadro('Hemşire', HEM)] });
  const kop = ilan({ k: 'kop', yz_kadrolar: [kadro('Hemşire', HEM)] });
  assert.strictEqual(C.ilanlariDegerlendir([ana, kop], new Map([['kop', 'ana']]), 'Hemşirelik', 'lisans', 80)[0].grup, 'degil');
  const yalniz = C.ilanlariDegerlendir([kop], new Map([['kop', 'yok']]), 'Hemşirelik', 'lisans', 80);
  assert.strictEqual(yalniz[0].anahtar, 'kop');
});

test('cinsiyet şartı kadroda not olarak taşınır', () => {
  const r = ilan({ yz_kadrolar: [kadro('İnfaz ve Koruma Memuru (ERKEK)', HEM)] });
  assert.strictEqual(C.degerlendir(r, 'Hemşirelik', 'lisans', 80).kadrolar[0].not, 'Yalnız erkek adaylar');
});

test('KPSS şartsız ilanda metindeki puan kalıbı aday puanını elemez', () => {
  const r = ilan({ kpss: 'kpsssiz', ozet: 'Daha önce 60 ve üzeri puan alanlar…', yz_kadrolar: [kadro('Hemşire', HEM, { puan_turu: null })] });
  assert.strictEqual(C.degerlendir(r, 'Hemşirelik', 'lisans', 40).grup, 'hemen');
});

test('farklı puan türü (A grubu) hemen değil kontrol', () => {
  const r = ilan({ yz_kadrolar: [kadro('Uzman Yardımcısı', 'Hukuk fakültesi mezunu olmak.', { puan_turu: 'P48' })] });
  const d = C.degerlendir(r, 'Hukuk', 'lisans', 80);
  assert.strictEqual(d.grup, 'kontrol');
  assert.match(d.neden, /P48/);
});

test('okunmuş kadro düzeyi tutmuyorsa gösterilmez (lisans adayına önlisans kadrosu)', () => {
  const r = ilan({ yz_kadrolar: [kadro('Tekniker', 'Herhangi bir önlisans programından mezun olmak.', { ogrenim: 'onlisans', puan_turu: 'P93' })] });
  assert.strictEqual(C.degerlendir(r, 'Hemşirelik', 'lisans', 80).grup, 'degil');
  assert.strictEqual(C.degerlendir(r, 'Tıbbi Dokümantasyon ve Sekreterlik', 'onlisans', 80).grup, 'hemen');
});

test('şartı okunamayan kadro hemen değil', () => {
  const r = ilan({ yz_kadrolar: [kadro('Memur', 'Ekteki tabloda belirtilen bölümlerden mezun olmak.')] });
  const g = C.degerlendir(r, 'Hemşirelik', 'lisans', 80).grup;
  assert.ok(g !== 'hemen', g);
});

test('kurum içi ilan gösterilmez', () => {
  const r = ilan({ baslik: 'KURUM - GÖREVDE YÜKSELME SINAVI', yz_kadrolar: [kadro('Şef', HEM)] });
  assert.strictEqual(C.degerlendir(r, 'Hemşirelik', 'lisans', 80).grup, 'degil');
});

test('çalışan personel şartı (kurumda 5 yılını doldurmuş) olan ilan gösterilmez', () => {
  const r = ilan({ baslik: 'KURUM - YURT DIŞI EĞİTİM', kadro_detay: [{ unvan: 'Aranan Şartlar', adet: 2, maddeler: ['Hukuk fakültesinden mezun olmak,', 'Adaylık ve askerlik dahil Kurumda beş yılını doldurmuş olmak,'] }] });
  assert.strictEqual(C.degerlendir(r, 'Hukuk', 'lisans', 80).grup, 'degil');
  const r2 = ilan({ kadro_detay: [{ unvan: 'Avukat', adet: 1, maddeler: ['Hukuk fakültesinden mezun olmak,', 'Avukatlık ruhsatına sahip olmak.'] }] });
  assert.strictEqual(C.degerlendir(r2, 'Hukuk', 'lisans', 80).grup, 'hemen');
});

test('genel lise: şartta düzey olarak "lise" geçen lise kadrosu kontrol değil hemen', () => {
  const r = ilan({ yz_kadrolar: [kadro('Destek Personeli', '2025-2026 KPSS P3 (lisans), P93 (ön lisans) veya P94 (lise) puanı en az 60 olmak.', { ogrenim: 'ortaogretim', puan_turu: 'P94' })] });
  assert.strictEqual(C.degerlendir(r, '', 'ortaogretim', 70).grup, 'hemen');
});

test('genel lise (bölümsüz): "lise ve dengi" kadrosu hemen, alan listeli kadro değil', () => {
  const r = ilan({ yz_kadrolar: [kadro('Zabıta', 'Lise ve dengi okul mezunu olmak.', { ogrenim: 'ortaogretim', puan_turu: 'P94' }),
    kadro('Teknisyen', 'Meslek liselerinin elektrik, elektronik alanlarından mezun olmak.', { ogrenim: 'ortaogretim', puan_turu: 'P94' })] });
  const d = C.degerlendir(r, '', 'ortaogretim', 70);
  assert.strictEqual(d.grup, 'hemen');
  esit(d.kadrolar.map((k) => k.ad), ['Zabıta']);
});

test('kopyalar tek satır: en iyi sonuç, birincil kaydın bağlantısı', () => {
  const ana = ilan({ k: 'ana', yz_kadrolar: [kadro('Hemşire', HEM)] });
  const kop = ilan({ k: 'kop', link: 'https://www.iskur.gov.tr/x', id: 'https://www.iskur.gov.tr/x' });
  const l = C.ilanlariDegerlendir([kop, ana], new Map([['https://www.iskur.gov.tr/x', 'ana']]), 'Hemşirelik', 'lisans', 80);
  assert.strictEqual(l.length, 1);
  assert.strictEqual(l[0].grup, 'hemen');
  assert.strictEqual(l[0].anahtar, 'ana');
  assert.strictEqual(l[0].rec.id, ana.id);
  assert.strictEqual(l[0].uyeler.length, 2);
});

test('merkezi atama: bölüm kodu, * genel, NNNN-* öneki, en yeni dönem, sınırda ve yakın', () => {
  const b = { bolumler: { '3204': 'HEMŞİRELİK', '3205': 'HEMŞİRELİK', '4000': 'TARİH', '6001-1': 'MUHASEBE', '6001-2': 'FİNANS' },
    nitelikler: { '2025-1': { '4605': ['3204', '3205'], '3001': ['*'], '4700': ['6001-*'] }, '2025-2': { '4605': ['3204', '3205'] } } };
  const p = { donemler: {
    '2025-1': [{ kurum: 'A', il: 'X', teskilat: 'M', unvan: 'HEMŞİRE', kontenjan: 1, min: 70, nit: ['4605'] },
      { kurum: 'B', il: 'X', teskilat: 'M', unvan: 'MEMUR', kontenjan: 3, min: 60, nit: ['3001'] },
      { kurum: 'C', il: 'Y', teskilat: 'M', unvan: 'SAĞLIK', kontenjan: 1, min: 71, nit: ['4700'] }],
    '2025-2': [{ kurum: 'A', il: 'X', teskilat: 'M', unvan: 'HEMŞİRE', kontenjan: 2, min: 74, nit: ['4605'] }] } };
  const m = C.merkezi(p, b, 'Hemşirelik', 72, 4, 2);
  esit(m.uygun.map((k) => k.kurum + k.donem).sort(), ['B2025-1']);   // A: en yeni dönem (74) geçerli; C yalnız 6001-* alanlarına
  esit(m.sinirda.map((k) => k.kurum), ['A']);
  esit(C.merkezi(p, b, 'Muhasebe', 72, 4, 2).uygun.map((k) => k.kurum).sort(), ['B', 'C']);   // 6001-* öneki 6001-1'i kapsar
  assert.strictEqual(C.merkezi(p, b, 'Felsefe', 72, 4, 2).bolumYok, true);
  esit(C.merkezi(p, b, '', 72, 4, 2).uygun.map((k) => k.kurum), ['B']);       // bölümsüz: yalnız * kadro
});

test('takvim dosyası: tarih, bir gün sonrası bitiş, hatırlatma ve kaçış', () => {
  const t = C.icsMetni(ilan({ kurum: 'A; B, C', son_tarih: '2026-12-31', son_zaman: '2026-12-31T17:00:00+03:00' }), 'https://kpsstercihi.com/ilan/a/', new Date('2026-11-24T10:00:00Z'));
  assert.match(t, /DTSTART;VALUE=DATE:20261231\r\n/);
  assert.match(t, /DTEND;VALUE=DATE:20270101\r\n/);
  assert.match(t, /TRIGGER:-PT15H/);
  assert.ok(t.includes('SUMMARY:Son gün: A\\; B\\, C'));
  assert.ok(t.split('\r\n').every((s) => Buffer.byteLength(s, 'utf8') <= 75));
  const uzun = C.icsMetni(ilan({ kurum: 'ÇĞİÖŞÜ'.repeat(30), son_tarih: '2026-12-31' }), 'x');
  assert.ok(uzun.split('\r\n').every((s) => Buffer.byteLength(s, 'utf8') <= 75));
  assert.strictEqual(C.icsMetni({ son_tarih: '' }, 'x'), '');
});

console.log(n + ' test geçti' + (process.exitCode ? ' (düşen var)' : ''));
