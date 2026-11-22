// docs/portal.js arama işlevlerini (aramaNorm, sorguVaryant, kelimeUyar, bulanikUyar...) satır işaretleriyle çıkarıp vm'de sınar.
const fs = require('fs'), path = require('path'), vm = require('vm');
const kaynak = fs.readFileSync(path.join(__dirname, '..', 'docs', 'portal.js'), 'utf8').split(/\r?\n/);
const bul = (on) => { const i = kaynak.findIndex(l => l.startsWith(on)); if (i < 0) throw new Error('işaret yok: ' + on); return i; };
const parca = [
  kaynak[bul('const normalize')],
  kaynak[bul('const aramaNorm')],
  ...kaynak.slice(bul('const ES_ANLAM'), bul('function aramaUyar(')),
].join('\n');
const ctx = {};
vm.createContext(ctx);
vm.runInContext(parca + '\nthis.api={aramaNorm,sorguVaryant,kelimeUyar,bulanikUyar,kokler,harfFark};', ctx);
const { aramaNorm, sorguVaryant, kelimeUyar, bulanikUyar, kokler, harfFark } = ctx.api;

const sert = (t, q) => sorguVaryant(q).some(ws => ws.every(w => kelimeUyar(t, w)));
const bulanik = (t, q) => sorguVaryant(q).some(ws => ws.every(w => bulanikUyar(t, w)));
const T = ' ' + aramaNorm('İstanbul Gaziosmanpaşa Belediyesi Zabıta Memuru Alım İlanı Devlet Demiryolları Taşımacılık Avukat Büro Personeli Meteoroloji Genel Müdürlüğü Hemşire Muhasebe');
const hata = [];
const bekle = (ad, ok) => { if (!ok) hata.push(ad); };

for (const q of ['zabıta memurluğu', 'meteoroloji müdürlüğü', 'tcdd', 'hemşirelik', 'zabıtası', 'avukatlık', 'demiryolari'])
  bekle('sert: ' + q, sert(T, q));
for (const q of ['avukatbüro personeli', 'muhasebeci', 'zabtia memuru', 'hemsre', 'meteroloji', 'muhasbe']) {
  bekle('bulanik: ' + q, bulanik(T, q));
  bekle('sert değil: ' + q, !sert(T, q));  // bulanık aşama gerçekten gerekli olmalı
}
// olumsuzlar: ne sert ne bulanık eşleşmeli
for (const q of ['eczacı', 'itfaiye', 'ptt']) {
  bekle('olumsuz sert: ' + q, !sert(T, q));
  bekle('olumsuz bulanik: ' + q, !bulanik(T, q));
}
const T2 = ' ' + aramaNorm('Önlisans Mezunu Burs Komisyonu');
for (const q of ['lisans', 'bursa']) {
  bekle('olumsuz sert: ' + q, !sert(T2, q));
  // bulanık aşamada kelime içi / 1 harf farkı eskiden de uyuyordu; yalnız sert aşama koruması sınanır
}
// kök kuralları
const kk = (w, k) => bekle('kök ' + w + '→' + k, kokler(w).includes(k));
kk('memurlugu', 'memur'); kk('mudurlugu', 'mudur'); kk('bekcilik', 'bekci'); kk('ogretmenligi', 'ogretmen');
kk('hemsirelik', 'hemsire'); kk('katiplik', 'katip'); bekle('kök muhasebeci→muhasebe (gevşek)', kokler('muhasebeci', true).includes('muhasebe')); bekle('sıkıda öğrenci→öğren yok', !kokler('ogrenci').includes('ogren'));
bekle('asci kök yok', kokler('asci').length === 0);
bekle('bekci kök yok', kokler('bekci').length === 0);
bekle('bursa kök yok', !kokler('bursa').includes('burs'));
// Damerau: yer değiştirme tek hata
bekle('harfFark yer değiştirme', harfFark('memru', 'memur', 1) && !harfFark('memru', 'memxx', 1));
bekle('harfFark iki hata', harfFark('demiryolari', 'demiryollarx', 2) && !harfFark('abcdefghi', 'abcdefxyz', 2));

if (hata.length) { console.error('BAŞARISIZ:\n' + hata.join('\n')); process.exit(1); }
console.log('tamam');
