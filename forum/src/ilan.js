// İlan kaydı: sitedeki bot-ilanlar.json (30 dk bellekte tutulur).
const SURE_MS = 30 * 60 * 1000;
let onbellek = { zaman: 0, url: '', kayitlar: [] };

export function ilanOnbellekTemizle() { onbellek = { zaman: 0, url: '', kayitlar: [] }; }

export async function ilanKayitlari(env) {
  const url = `${env.SITE_URL || 'https://kpsstercihi.com/'}bot-ilanlar.json`;
  if (onbellek.url === url && Date.now() - onbellek.zaman < SURE_MS) return onbellek.kayitlar;
  try {
    const r = await fetch(url, { cf: { cacheTtl: 1800, cacheEverything: true } });
    if (!r.ok) return onbellek.url === url ? onbellek.kayitlar : [];
    const j = await r.json();
    const kayitlar = Array.isArray(j?.ilanlar) ? j.ilanlar : [];
    onbellek = { zaman: Date.now(), url, kayitlar };
    return kayitlar;
  } catch {
    return onbellek.url === url ? onbellek.kayitlar : [];
  }
}

// anahtar: ilan sayfası anahtarı (UUID, sbb-/iskur-/csb- kimliği).
export function ilanBul(kayitlar, anahtar) {
  const a = String(anahtar || '').toLowerCase();
  if (!a) return null;
  return kayitlar.find((r) => {
    if (String(r.id || '').toLowerCase() === a) return true;
    if ((r.kimlikler || []).some((k) => { k = String(k).toLowerCase(); return k === a || k.endsWith(`i=${a}`); })) return true;
    return String(r.sayfa || '').toLowerCase().endsWith(`/ilan/${a}/`);
  }) || null;
}

export async function ilanKaydiGetir(env, anahtar) {
  return ilanBul(await ilanKayitlari(env), anahtar);
}
