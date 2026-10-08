// /panel : yalnız sahibin kullandığı yönetim paneli. PANEL_ANAHTARI sırrı ile korunur.
// Giriş başarılıysa HttpOnly + Secure + SameSite=Strict bir oturum çerezi verilir (yalnız api.kpsstercihi.com, yalnız yönetici için).
import { gunlukTuz, ziyaretciOzeti, sha256Hex } from './toplama.js';
import { trParcalari } from './zaman.js';
import { raporUret, canli } from './rapor.js';
import { panelSayfasi, girisSayfasi } from './arayuz.js';
import { onbellekli } from './onbellek.js';
import { butceDurumu, butceOzeti } from './butce.js';

export const COOKIE = 'kpss_panel';
export const OTURUM_SN = 30 * 86400;
export const DENEME_SINIRI = 5;
export const KILIT_SN = 900;
export const GENEL_SINIR = 40;

// Sabit süreli karşılaştırma (uzunluk farkında da tüm baytlar dolaşılır).
export function esit(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a)), y = enc.encode(String(b));
  let fark = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) fark |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return fark === 0;
}

async function hmacHex(anahtar, metin) {
  const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(anahtar), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const imza = await crypto.subtle.sign('HMAC', k, new TextEncoder().encode(metin));
  return [...new Uint8Array(imza)].map((x) => x.toString(16).padStart(2, '0')).join('');
}

export async function oturumCerezi(env, simdiSn) {
  const bit = simdiSn + OTURUM_SN;
  return `${bit}.${await hmacHex(env.PANEL_ANAHTARI, 'panel|' + bit)}`;
}

export async function oturumGecerli(env, request, simdiSn) {
  const cerez = (request.headers.get('Cookie') || '').split(/;\s*/).find((c) => c.startsWith(COOKIE + '='));
  if (!cerez) return false;
  const deger = cerez.slice(COOKIE.length + 1);
  const [bit, imza] = deger.split('.');
  if (!/^\d{9,12}$/.test(bit || '') || !imza) return false;
  const beklenen = await hmacHex(env.PANEL_ANAHTARI, 'panel|' + bit);
  return esit(imza, beklenen) && Number(bit) > simdiSn;
}

const GUVENLIK = {
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow',
};

function html(govde, durum = 200, nonce = '', ek = {}) {
  const csp = nonce
    ? `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; connect-src 'self'; img-src data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`
    : `default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`;
  return new Response(govde, { status: durum, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Content-Security-Policy': csp, ...GUVENLIK, ...ek } });
}

const json = (v, durum = 200) => new Response(JSON.stringify(v), { status: durum, headers: { 'Content-Type': 'application/json; charset=utf-8', ...GUVENLIK } });

function nonceUret() {
  const a = new Uint8Array(16);
  crypto.getRandomValues(a);
  return btoa(String.fromCharCode(...a)).replace(/[^A-Za-z0-9]/g, '');
}

// Kilitleme: hem istemci özeti (tuzlu, IP değil) hem de genel sayaç.
async function kilitDurumu(db, anahtarlar, simdiSn) {
  for (const a of anahtarlar) {
    const r = await db.prepare('SELECT say, ilk, kilit FROM giris_deneme WHERE anahtar = ?').bind(a).first();
    if (r && r.kilit > simdiSn) return r.kilit - simdiSn;
  }
  return 0;
}

async function basarisizKaydet(db, anahtar, sinir, simdiSn) {
  const r = await db.prepare('SELECT say, ilk FROM giris_deneme WHERE anahtar = ?').bind(anahtar).first();
  const say = r && simdiSn - r.ilk < KILIT_SN ? r.say + 1 : 1;
  const ilk = r && simdiSn - r.ilk < KILIT_SN ? r.ilk : simdiSn;
  const kilit = say >= sinir ? simdiSn + KILIT_SN : 0;
  await db.prepare('INSERT OR REPLACE INTO giris_deneme (anahtar, say, ilk, kilit) VALUES (?, ?, ?, ?)').bind(anahtar, say, ilk, kilit).run();
}

async function girisIstegi(request, env, simdiSn) {
  const { gun } = trParcalari(simdiSn);
  const tuz = await gunlukTuz(env.DB, gun);
  const istemci = 'g:' + (await ziyaretciOzeti(tuz, request.headers.get('CF-Connecting-IP') || '', request.headers.get('User-Agent') || ''));
  const anahtarlar = [istemci, 'genel'];
  const bekle = await kilitDurumu(env.DB, anahtarlar, simdiSn);
  if (bekle) return html(girisSayfasi(`Çok fazla deneme. ${Math.ceil(bekle / 60)} dakika sonra yeniden dene.`), 429);
  let anahtar = '';
  try { anahtar = String((await request.formData()).get('anahtar') || ''); } catch { /* boş */ }
  // Boş anahtar da başarısız sayılır; karşılaştırma her durumda aynı yolu izler.
  if (anahtar && esit(anahtar, env.PANEL_ANAHTARI)) {
    await env.DB.prepare('DELETE FROM giris_deneme WHERE anahtar = ?').bind(istemci).run();
    const cerez = await oturumCerezi(env, simdiSn);
    return new Response(null, {
      status: 303,
      headers: { Location: '/panel', 'Set-Cookie': `${COOKIE}=${cerez}; HttpOnly; Secure; SameSite=Strict; Path=/panel; Max-Age=${OTURUM_SN}`, ...GUVENLIK },
    });
  }
  await basarisizKaydet(env.DB, istemci, DENEME_SINIRI, simdiSn);
  await basarisizKaydet(env.DB, 'genel', GENEL_SINIR, simdiSn);
  return html(girisSayfasi('Anahtar hatalı.'), 401);
}

export async function panelIstegi(request, env, url, secenek = {}) {
  const simdiMs = secenek.simdiMs ?? Date.now();
  const simdiSn = Math.floor(simdiMs / 1000);
  const yerel = env.ORTAM === 'yerel' && !env.PANEL_ANAHTARI;
  if (!env.PANEL_ANAHTARI && !yerel) return html(girisSayfasi('Panel kurulmamış: PANEL_ANAHTARI sırrı tanımlı değil.'), 503);
  const yol = url.pathname.replace(/\/+$/, '') || '/';

  if (yol === '/panel/giris' && request.method === 'POST') {
    if (yerel) return new Response(null, { status: 303, headers: { Location: '/panel' } });
    return girisIstegi(request, env, simdiSn);
  }
  if (yol === '/panel/cikis') {
    return new Response(null, { status: 303, headers: { Location: '/panel', 'Set-Cookie': `${COOKIE}=; HttpOnly; Secure; SameSite=Strict; Path=/panel; Max-Age=0`, ...GUVENLIK } });
  }

  const yetkili = yerel || (await oturumGecerli(env, request, simdiSn));
  if (!yetkili) {
    if (yol === '/panel') return html(girisSayfasi(''), 200);
    return json({ hata: 'yetkisiz' }, 401);
  }

  if (yol === '/panel' && request.method === 'GET') {
    const nonce = nonceUret();
    return html(panelSayfasi(nonce), 200, nonce);
  }
  if (yol === '/panel/veri' && request.method === 'GET') {
    const aralik = ['bugun', '7g', '30g', '90g'].includes(url.searchParams.get('aralik')) ? url.searchParams.get('aralik') : '7g';
    // Rapor çok sayıda toplama sorgusu çalıştırır: bugün 10 dk, diğer aralıklar 60 dk önbellekte; ?taze=1 en çok 5 dakikada bir işe yarar.
    const ttl = aralik === 'bugun' ? 600 : 3600;
    const b = await butceDurumu(env, simdiMs);
    const ozet = butceOzeti(b);
    // Okuma bütçesi 2,5M'i aşınca yalnız önbellekteki (bayat olabilir) sonuç verilir; D1'e gidilmez.
    const o = await onbellekli('veri:' + aralik, ttl, async () => {
      const rapor = await raporUret(env, aralik, simdiMs, secenek.adlariGetir);
      rapor.aralik.ad = aralik;
      return JSON.stringify(rapor);
    }, simdiMs, url.searchParams.get('taze') === '1', b.okumaKademesi >= 1);
    if (!o) return json({ kota_korumasi: true, mesaj: 'kota koruması: veri yarın', butce: ozet });
    // Önbellekteki gövdeye güncel bütçe durumu eklenir (rapor nesnesi '}' ile biter).
    const govde = o.govde.endsWith('}') ? o.govde.slice(0, -1) + ',"butce":' + JSON.stringify(ozet) + '}' : o.govde;
    return new Response(govde, { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8', ...GUVENLIK, 'X-Onbellek': o.onbellekte ? 'var' : 'yok' } });
  }
  if (yol === '/panel/butce' && request.method === 'GET') {
    return json(butceOzeti(await butceDurumu(env, simdiMs)));
  }
  if (yol === '/panel/canli' && request.method === 'GET') {
    const b = await butceDurumu(env, simdiMs);
    const o = await onbellekli('canli', 30, async () => JSON.stringify(await canli(env, simdiMs)), simdiMs, false, b.okumaKademesi >= 2);
    if (!o) return json({ aktif: 0, akis: [], sn: Math.floor(simdiMs / 1000), kota_korumasi: true });
    return new Response(o.govde, { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8', ...GUVENLIK, 'X-Onbellek': o.onbellekte ? 'var' : 'yok' } });
  }
  return new Response('bulunamadı', { status: 404 });
}

export { sha256Hex };
