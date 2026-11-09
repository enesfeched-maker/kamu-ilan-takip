/* Elle denetim: node bot/bolum_denetim.cjs "Bölüm Adı" [örnek-sayısı]
 * Gerçek veride grup dağılımı, örnekler ve "geri çağırma sondası": eşleşmiyor sayılan ama şart metninde bölümün
 * herhangi bir sözcüğünün kökü geçen ilanlar (olası yanlış elemeler). TUMU=1 ile bütün örnekler. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '../docs/bolum/esles.js'), 'utf8');
const mod = { exports: {} };
vm.runInNewContext(src, { module: mod, self: undefined });
const E = mod.exports;
const d = JSON.parse(fs.readFileSync(path.join(__dirname, '../docs/ilanlar.json'), 'utf8')).ilanlar
  .filter((i) => !i.duyuru_turu && !(process.env.NOAK && i.kategori === 'akademik'));
const ad = process.argv[2] || 'Bilgisayar Mühendisliği';
const bolum = E.bolumCoz(ad);
const n = Number(process.argv[3] || 3);
const g = {};
for (const r of d) { const s = E.siniflandir(r, bolum, ''); (g[s.kademe] = g[s.kademe] || []).push([r, s]); }
console.log(ad, 'toplam', d.length, JSON.stringify(Object.fromEntries(Object.entries(g).map(([k, v]) => [k, v.length]))));
for (const k of ['kesin', 'muhtemel', 'serbest', 'belirsiz', 'eslesmiyor']) {
  console.log('\n== ' + k + ' ==');
  const secim = process.env.TUMU ? (g[k] || []) : (g[k] || []).slice(0, n);
  for (const [r, s] of secim) console.log('-', (r.kurum || '').slice(0, 40), '|', (r.baslik || '').slice(0, 60), '\n    ', s.neden, '|', s.kadro, '|', s.kanit.slice(0, 170));
}
const toks = [...new Set(bolum.flat())].filter((t) => t.length >= 5).map((t) => t.slice(0, Math.max(5, t.length - 3)));
console.log('\n== SONDA: eşleşmiyor ama metinde kök geçiyor ==', toks.join(','));
for (const [r, s] of g.eslesmiyor || []) {
  const metin = E.parcalar(r).filter((p) => p.kaynak === 'sart').map((p) => E.fold(p.metin)).join(' ');
  const hit = toks.filter((t) => metin.includes(t));
  if (hit.length) console.log('!', (r.kurum || '').slice(0, 40), '|', (r.baslik || '').slice(0, 50), '|', hit.join(','));
}
