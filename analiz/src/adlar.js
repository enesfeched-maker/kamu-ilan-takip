// İlan anahtarı -> okunur ad. Siteden liste.json çekilir (en çok 6 saat önbellekte). Başarısız olursa anahtar gösterilir.
let onbellek = { zaman: 0, harita: null };
const OMUR_MS = 6 * 3600 * 1000;

export function adlariSifirla() { onbellek = { zaman: 0, harita: null }; }

export async function haritaYukle(env, getir = fetch, simdi = Date.now()) {
  if (onbellek.harita && simdi - onbellek.zaman < OMUR_MS) return onbellek.harita;
  const taban = String(env.SITE_URL || 'https://kpsstercihi.com/').replace(/\/?$/, '/');
  try {
    const r = await getir(taban + 'liste.json', { cf: { cacheTtl: 3600, cacheEverything: true } });
    if (!r.ok) throw new Error('http ' + r.status);
    const v = await r.json();
    const h = new Map();
    for (const i of Array.isArray(v.ilanlar) ? v.ilanlar : []) {
      if (!i || typeof i.key !== 'string') continue;
      const kurum = typeof i.kurum === 'string' ? i.kurum.trim() : '';
      const manset = typeof i.manset === 'string' ? i.manset.trim() : '';
      h.set(i.key, [kurum, manset].filter(Boolean).join(' — ').slice(0, 120) || i.key);
    }
    onbellek = { zaman: simdi, harita: h };
    return h;
  } catch {
    return onbellek.harita || new Map();
  }
}

export async function ilanAdlari(env, anahtarlar, getir = fetch) {
  const harita = await haritaYukle(env, getir);
  const out = {};
  for (const k of anahtarlar) if (harita.has(k)) out[k] = harita.get(k);
  return out;
}
