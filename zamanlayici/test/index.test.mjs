import test from 'node:test';
import assert from 'node:assert/strict';
import isci, { ISLER, SAATLI, baslat, saatliIsler } from '../src/index.js';

test('cron ifadeleri wrangler.toml ile aynı ve doğru iş akışlarını başlatır', async () => {
  const toml = await import('node:fs').then(fs => fs.readFileSync(new URL('../wrangler.toml', import.meta.url), 'utf8'));
  const cronlar = [...toml.matchAll(/"([^"]+ \* \* \* \*|[^"]+ \*\/2 \* \* \*)"/g)].map(m => m[1]);
  assert.deepEqual(cronlar.sort(), Object.keys(ISLER).sort());
  assert.deepEqual(ISLER['25 */2 * * *'], ['sosyal-yorum.yml']);
  assert.deepEqual(ISLER['*/30 * * * *'], ['ilan.yml']);
  assert.deepEqual(ISLER['7,37 * * * *'], ['bekci.yml']);
});

test('başlatma isteği doğru adrese, anahtar başlıkta, gövdede main dalı', async () => {
  let istek;
  const sahte = async (url, ayar) => { istek = { url, ayar }; return new Response(null, { status: 204 }); };
  assert.equal(await baslat({ GH_TOKEN: 'gizli' }, 'ilan.yml', sahte), true);
  assert.match(istek.url, /repos\/enesfeched-maker\/kamu-ilan-takip\/actions\/workflows\/ilan\.yml\/dispatches$/);
  assert.equal(istek.ayar.headers.Authorization, 'Bearer gizli');
  assert.deepEqual(JSON.parse(istek.ayar.body), { ref: 'main' });
});

test('GitHub hata verirse false döner, anahtar yazılmaz', async () => {
  const kayit = [];
  const eski = console.log;
  console.log = (...a) => kayit.push(a.join(' '));
  try {
    const sahte = async () => new Response('Bad credentials', { status: 401 });
    assert.equal(await baslat({ GH_TOKEN: 'cok-gizli-anahtar' }, 'ilan.yml', sahte), false);
  } finally { console.log = eski; }
  assert.match(kayit.join('\n'), /HTTP 401/);
  assert.doesNotMatch(kayit.join('\n'), /cok-gizli-anahtar/);
});

test('anahtar yoksa hiçbir istek atılmaz', async () => {
  const eskiFetch = globalThis.fetch;
  let cagrildi = false;
  globalThis.fetch = async () => { cagrildi = true; return new Response(null, { status: 204 }); };
  const eskiLog = console.log;
  console.log = () => {};
  try {
    await isci.scheduled({ cron: '*/30 * * * *' }, {}, { waitUntil: p => p });
  } finally { globalThis.fetch = eskiFetch; console.log = eskiLog; }
  assert.equal(cagrildi, false);
});

test('sosyal paylaşımlar TR 12:30, 18:00 ve 21:00 tetiklenir, girdilerde kaynak=zamanlayici', () => {
  const adlar = (iso) => saatliIsler(Date.parse(iso)).map(([a]) => a);
  assert.deepEqual(adlar('2026-11-27T09:30:00Z'), ['sosyal.yml']);
  assert.deepEqual(saatliIsler(Date.parse('2026-11-27T09:30:00Z'))[0][1].vakit, 'sabah');
  assert.deepEqual(adlar('2026-11-27T15:00:00Z'), ['sosyal-ozel.yml', 'sosyal-ilan.yml']);
  assert.deepEqual(saatliIsler(Date.parse('2026-11-27T18:00:00Z'))[0][1].vakit, 'aksam');
  assert.deepEqual(adlar('2026-11-27T01:00:00Z'), []);            // gece hiçbir sosyal iş yok
  assert.deepEqual(adlar('2026-11-29T16:00:00Z'), ['sosyal.yml']); // pazar haftalık
  assert.deepEqual(adlar('2026-11-28T16:00:00Z'), []);
  for (const isler of Object.values(SAATLI)) for (const [, g] of isler) assert.equal(g.kaynak, 'zamanlayici');
  for (const k of Object.keys(SAATLI)) assert.match(k, /^(\d )?\d\d:(00|30)$/);   // yalnız yarım saatlik tetiklerde
});

test('girdili başlatma gövdede inputs taşır', async () => {
  let istek;
  const sahte = async (url, ayar) => { istek = { url, ayar }; return new Response(null, { status: 204 }); };
  await baslat({ GH_TOKEN: 'x' }, 'sosyal.yml', sahte, { vakit: 'sabah', kaynak: 'zamanlayici' });
  assert.deepEqual(JSON.parse(istek.ayar.body), { ref: 'main', inputs: { vakit: 'sabah', kaynak: 'zamanlayici' } });
});
