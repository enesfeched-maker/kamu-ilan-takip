// Google Identity Services kimlik jetonu (RS256 JWT) doğrulaması. Yalnız `sub` kullanılır; e-posta ve ad saklanmaz.
import { b64uCoz, b64uMetin } from './yardimci.js';

const JWKS_ADRESI = 'https://www.googleapis.com/oauth2/v3/certs';
const ONBELLEK_ANAHTARI = 'https://forum-api.kpsstercihi.com/_onbellek/google-jwks';
const SAPMA = 300;           // saat farkı toleransı: 5 dakika
const EN_COK_YASAM = 24 * 3600;
const VARSAYILAN_SN = 3600;
const ISSUERLAR = new Set(['accounts.google.com', 'https://accounts.google.com']);

const ZORLA_ARALIK = 60_000;   // bilinmeyen kid için JWKS en çok dakikada bir zorla yenilenir (sahte kid ile Google'a istek yağdırılamaz)
let sonZorla = 0;
let bellek = null;           // { anahtarlar, bitis (ms) }
export function googleAnahtarOnbellegiTemizle() { bellek = null; sonZorla = 0; }

function maxAge(yanit) {
  const m = /max-age=(\d+)/i.exec(yanit.headers.get('Cache-Control') || '');
  return m ? Math.min(Number(m[1]), EN_COK_YASAM) : VARSAYILAN_SN;
}

async function anahtarlariGetir(zorla = false) {
  const simdiMs = Date.now();
  if (!zorla && bellek && bellek.bitis > simdiMs) return bellek.anahtarlar;
  const c = typeof caches !== 'undefined' ? caches.default : null;
  const istek = new Request(ONBELLEK_ANAHTARI);
  if (!zorla && c) {
    try {
      const k = await c.match(istek);
      if (k) {
        const j = await k.json();
        if (Array.isArray(j.keys) && j.keys.length) { bellek = { anahtarlar: j.keys, bitis: simdiMs + 300_000 }; return j.keys; }
      }
    } catch { /* önbellek yok sayılır */ }
  }
  const r = await fetch(JWKS_ADRESI);
  if (!r.ok) throw new Error('jwks');
  const sn = maxAge(r);
  const j = await r.clone().json();
  if (!Array.isArray(j.keys) || !j.keys.length) throw new Error('jwks');
  bellek = { anahtarlar: j.keys, bitis: simdiMs + sn * 1000 };
  if (c) {
    try { await c.put(istek, new Response(JSON.stringify(j), { headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${sn}` } })); } catch { /* önbellek yazılamadı */ }
  }
  return j.keys;
}

const ayir = (parca) => JSON.parse(b64uMetin(parca));

// Başarılıysa { tamam: true, sub }, değilse { tamam: false, neden }.
export async function googleJetonuDogrula(env, jeton, simdi) {
  if (!env.GOOGLE_ISTEMCI_KIMLIGI) return { tamam: false, neden: 'yapilandirma' };
  if (typeof jeton !== 'string' || jeton.length > 4096) return { tamam: false, neden: 'bicim' };
  const parcalar = jeton.split('.');
  if (parcalar.length !== 3 || parcalar.some((p) => !/^[A-Za-z0-9_-]+$/.test(p))) return { tamam: false, neden: 'bicim' };
  let baslik; let yuk;
  try { baslik = ayir(parcalar[0]); yuk = ayir(parcalar[1]); } catch { return { tamam: false, neden: 'bicim' }; }
  if (!baslik || baslik.alg !== 'RS256' || typeof baslik.kid !== 'string') return { tamam: false, neden: 'alg' };
  if (!yuk || typeof yuk !== 'object') return { tamam: false, neden: 'bicim' };

  let imzaTamam = false;
  try {
    let anahtarlar = await anahtarlariGetir();
    let jwk = anahtarlar.find((k) => k.kid === baslik.kid);
    if (!jwk && Date.now() - sonZorla >= ZORLA_ARALIK) {   // anahtar yenilenmiş olabilir
      sonZorla = Date.now();
      anahtarlar = await anahtarlariGetir(true); jwk = anahtarlar.find((k) => k.kid === baslik.kid);
    }
    if (!jwk || jwk.kty !== 'RSA') return { tamam: false, neden: 'anahtar' };
    const k = await crypto.subtle.importKey('jwk', { kty: jwk.kty, n: jwk.n, e: jwk.e, alg: 'RS256', ext: true }, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
    imzaTamam = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', k, b64uCoz(parcalar[2]), new TextEncoder().encode(`${parcalar[0]}.${parcalar[1]}`));
  } catch { return { tamam: false, neden: 'ag' }; }
  if (!imzaTamam) return { tamam: false, neden: 'imza' };

  if (!ISSUERLAR.has(yuk.iss)) return { tamam: false, neden: 'iss' };
  if (yuk.aud !== env.GOOGLE_ISTEMCI_KIMLIGI) return { tamam: false, neden: 'aud' };
  if (typeof yuk.exp !== 'number' || yuk.exp + SAPMA <= simdi) return { tamam: false, neden: 'eski' };
  if (typeof yuk.iat !== 'number' || yuk.iat - SAPMA > simdi) return { tamam: false, neden: 'gelecek' };
  if (yuk.email_verified !== true && yuk.email_verified !== 'true') return { tamam: false, neden: 'eposta' };
  if (typeof yuk.sub !== 'string' || !/^\d{1,40}$/.test(yuk.sub)) return { tamam: false, neden: 'sub' };
  return { tamam: true, sub: yuk.sub };
}
