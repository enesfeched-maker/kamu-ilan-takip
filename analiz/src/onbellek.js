// D1 okuma kotasını korumak için: izolat belleği + Cache API (izolatlar arası paylaşılır) ve okunan satır günlüğü.
const bellek = new Map(); // anahtar -> { ms, govde }
const TAZE_ARALIK_MS = 300_000; // ?taze=1 aynı girdi için en çok 5 dakikada bir işe yarar

export function bellekSifirla() { bellek.clear(); }

const cache = () => (typeof caches !== 'undefined' && caches.default ? caches.default : null);
const cacheIstegi = (anahtar) => new Request('https://onbellek.kpss-analiz.internal/' + encodeURIComponent(anahtar));

async function oku(anahtar) {
  const b = bellek.get(anahtar);
  if (b) return b;
  const c = cache();
  if (!c) return null;
  try {
    const r = await c.match(cacheIstegi(anahtar));
    if (!r) return null;
    const girdi = { ms: Number(r.headers.get('X-Uretildi')) || 0, govde: await r.text() };
    bellek.set(anahtar, girdi);
    return girdi;
  } catch { return null; }
}

export async function yaz(anahtar, govde, ttlSn, ms) {
  bellek.set(anahtar, { ms, govde });
  const c = cache();
  if (!c) return;
  try {
    await c.put(cacheIstegi(anahtar), new Response(govde, { headers: { 'Cache-Control': `public, max-age=${ttlSn}`, 'X-Uretildi': String(ms) } }));
  } catch { /* önbellek yazılamazsa yalnız bellek kalır */ }
}

export const oku_ = oku;

// ttlSn süresince önbellekten verir; taze=true ise (girdi en az 5 dk eskiyse) yeniden üretir.
export async function onbellekli(anahtar, ttlSn, uret, simdiMs = Date.now(), taze = false) {
  const g = await oku(anahtar);
  if (g) {
    const yas = simdiMs - g.ms;
    if (yas >= 0 && yas < ttlSn * 1000 && !(taze && yas >= TAZE_ARALIK_MS)) return { govde: g.govde, ms: g.ms, onbellekte: true };
  }
  const govde = await uret();
  await yaz(anahtar, govde, ttlSn, simdiMs);
  return { govde, ms: simdiMs, onbellekte: false };
}

// D1 sonuçlarındaki meta.rows_read toplamı: `wrangler tail` ile uç nokta başına maliyet görülür.
export function okumaGunlugu(ad, ...sonuclar) {
  let n = 0, var_ = false;
  for (const s of sonuclar.flat()) {
    const r = s && s.meta && s.meta.rows_read;
    if (typeof r === 'number') { n += r; var_ = true; }
  }
  if (var_) console.log(`okuma ${ad} rows_read=${n}`);
  return n;
}
