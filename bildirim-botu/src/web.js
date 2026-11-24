// Web Push (tarayıcı bildirimi): /nereye/ sayfasındaki kayıtlı aramalar için. TASARIM.md "Web Push" bölümü.
// Yük (payload) YOKTUR: push yalnız "uyandırma"dır; servis çalışanı /web/bekleyen'den ilan başlıklarını çeker.
import { bugunIstanbul, sureDoldu } from './eslestir.js';

const IZINLI_ORIGINLER = /^(https:\/\/kpsstercihi\.com|http:\/\/(localhost|127\.0\.0\.1)(:\d{1,5})?)$/;
const DUZEYLER = ['ortaogretim', 'onlisans', 'lisans'];
const GOVDE_MAX = 4096;
const ENDPOINT_MAX = 600;
const BOLUM_MAX = 80;
const BEKLEYEN_GOSTER = 5; // /web/bekleyen en çok bu kadar ilan döner
const ABONE_BASINA_MAX = 5; // bir tarama işinde abone başına en çok bekleyen ilan
const IS_SAYFA_MAX = 100;
const CIFT_MAX = 2000;
const JSON_BAYT_MAX = 90000;
const PUSH_PARALEL = 10;
const JWT_OMUR_SN = 11 * 3600; // RFC 8292: en çok 24 saat; biz 11 saat
const BEKLEYEN_OMUR_MS = 7 * 24 * 3600 * 1000;
const GEREKSIZ_KELIMELER = new Set(['ve', 'veya', 'ile', 'bolumu', 'bolum', 'programi', 'program', 'bolumleri', 'programlari', 'mezunu', 'mezunlari']);

// ---------------------------------------------------------------- yardımcılar

export function endpointGecerli(e) {
  if (typeof e !== 'string' || e.length > ENDPOINT_MAX) return false;
  let u;
  try { u = new URL(e); } catch { return false; }
  if (u.protocol !== 'https:' || u.username || u.password || u.port) return false;
  const h = u.hostname;
  return h === 'fcm.googleapis.com' || h === 'updates.push.services.mozilla.com' || h === 'web.push.apple.com' || h.endsWith('.notify.windows.com');
}

// Türkçe küçük harf + aksan/Türkçe harf katlama: "Hukuk Fakültesi" -> "hukuk fakultesi".
export function katla(s) {
  return String(s ?? '').toLocaleLowerCase('tr')
    .replace(/ı/g, 'i').replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u')
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
}

export function bolumKelimeleri(bolum) {
  return katla(bolum).split(/[^a-z0-9]+/).filter((w) => w.length > 1 && !GEREKSIZ_KELIMELER.has(w));
}

const liste = (x) => (Array.isArray(x) ? x : []);

// abone: {duzey, bolum, puan}; ilan: bot-ilanlar.json öğesi. katliMetin: katla(ilanMetni(ilan)) (çağıran önbelleğe alır).
export function webUygunMu(ilan, abone, bugun, simdi, katliMetin, kelimeler) {
  if (ilan.kategori === 'akademik') return false;
  if (sureDoldu(ilan, bugun, simdi)) return false;
  const ogrenim = liste(ilan.ogrenim);
  if (ogrenim.length && abone.duzey && !ogrenim.includes(abone.duzey)) return false;
  const puan = abone.puan;
  if (typeof puan === 'number' && typeof ilan.en_az_puan === 'number' && ilan.kpss !== 'kpsssiz' && puan < ilan.en_az_puan) return false;
  const kw = kelimeler || bolumKelimeleri(abone.bolum);
  if (kw.length) {
    const metin = katliMetin ?? katla(ilan.metin || [ilan.baslik, ilan.kurum].join(' '));
    for (const k of kw) if (!metin.includes(k)) return false;
  }
  return true;
}

const b64uBayt = (s) => {
  const t = String(s).trim().replace(/=+$/, '').replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(t + '='.repeat((4 - (t.length % 4)) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
};
const bayt64u = (b) => {
  let s = '';
  for (const x of b) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};
const metin64u = (s) => bayt64u(new TextEncoder().encode(s));

// ---------------------------------------------------------------- VAPID

export const webAcik = (env) => !!(env && env.VAPID_OZEL && env.VAPID_ACIK);

// VAPID_OZEL: ya ham özel değer d (32 bayt, base64url) ya da PKCS8 (base64url). VAPID_ACIK: 65 bayt sıkıştırılmamış nokta (base64url).
let anahtarOnbellek = { kimlik: null, key: null };
async function anahtarAl(env) {
  const kimlik = `${env.VAPID_OZEL}|${env.VAPID_ACIK}`;
  if (anahtarOnbellek.kimlik === kimlik) return anahtarOnbellek.key;
  const ham = b64uBayt(env.VAPID_OZEL);
  const alg = { name: 'ECDSA', namedCurve: 'P-256' };
  let key;
  if (ham.length === 32) {
    const pub = b64uBayt(env.VAPID_ACIK);
    if (pub.length !== 65 || pub[0] !== 4) throw new Error('VAPID_ACIK geçersiz');
    key = await crypto.subtle.importKey('jwk', { kty: 'EC', crv: 'P-256', d: bayt64u(ham), x: bayt64u(pub.slice(1, 33)), y: bayt64u(pub.slice(33)), ext: true }, alg, false, ['sign']);
  } else {
    key = await crypto.subtle.importKey('pkcs8', ham, alg, false, ['sign']);
  }
  anahtarOnbellek = { kimlik, key };
  return key;
}

const jwtOnbellek = new Map(); // aud|acik -> {jwt, exp}
export function jwtOnbellekTemizle() { jwtOnbellek.clear(); anahtarOnbellek = { kimlik: null, key: null }; }

export async function vapidJwt(env, aud, simdi = new Date()) {
  const sn = Math.floor(simdi.getTime() / 1000);
  const k = `${aud}|${env.VAPID_ACIK}`;
  const var_ = jwtOnbellek.get(k);
  if (var_ && var_.exp - sn > 3600) return var_.jwt; // aynı anda gelen istekler aynı sözü paylaşır
  const exp = sn + JWT_OMUR_SN;
  const sub = env.VAPID_IRTIBAT ? `mailto:${env.VAPID_IRTIBAT}` : 'https://kpsstercihi.com';
  const girdi = `${metin64u(JSON.stringify({ typ: 'JWT', alg: 'ES256' }))}.${metin64u(JSON.stringify({ aud, exp, sub }))}`;
  const jwt = (async () => {
    const imza = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, await anahtarAl(env), new TextEncoder().encode(girdi));
    return `${girdi}.${bayt64u(new Uint8Array(imza))}`;
  })();
  jwtOnbellek.set(k, { jwt, exp });
  try { return await jwt; } catch (e) { jwtOnbellek.delete(k); throw e; }
}

// Yük'süz push; HTTP durum kodunu döner (ağ hatasında 0).
export async function pushGonder(env, endpoint, fetchFn, simdi = new Date()) {
  try {
    const jwt = await vapidJwt(env, new URL(endpoint).origin, simdi);
    const r = await fetchFn(endpoint, {
      method: 'POST',
      headers: { Authorization: `vapid t=${jwt}, k=${env.VAPID_ACIK}`, TTL: '86400', Urgency: 'normal' },
    });
    return r.status;
  } catch {
    return 0;
  }
}

// ---------------------------------------------------------------- HTTP uçları

function corsBasliklari(origin) {
  const h = { 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '86400', Vary: 'Origin' };
  if (origin && IZINLI_ORIGINLER.test(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

const yanit = (govde, durum, origin) => new Response(JSON.stringify(govde), {
  status: durum, headers: { 'Content-Type': 'application/json; charset=utf-8', ...corsBasliklari(origin) },
});
const hata = (durum, mesaj, origin) => yanit({ tamam: false, hata: mesaj }, durum, origin);

async function govdeOku(request) {
  const uzunluk = Number(request.headers.get('Content-Length'));
  if (uzunluk > GOVDE_MAX) return { kod: 413 };
  const metin = await request.text();
  if (new TextEncoder().encode(metin).length > GOVDE_MAX) return { kod: 413 };
  try {
    const v = JSON.parse(metin);
    if (!v || typeof v !== 'object' || Array.isArray(v)) return { kod: 400 };
    return { veri: v };
  } catch { return { kod: 400 }; }
}

const anahtarGecerli = (s, max) => typeof s === 'string' && s.length > 0 && s.length <= max && /^[A-Za-z0-9_\-+/=]+$/.test(s);

// /web/* yolları için; başka yolda null döner.
export async function webIstek(request, env) {
  const url = new URL(request.url);
  if (!url.pathname.startsWith('/web/')) return null;
  const origin = request.headers.get('Origin');
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsBasliklari(origin) });
  if (request.method !== 'POST') return hata(405, 'yöntem desteklenmiyor', origin);
  if (origin && !IZINLI_ORIGINLER.test(origin)) return hata(403, 'köken izinli değil', origin);
  const ad = url.pathname;
  if (ad !== '/web/abone' && ad !== '/web/sil' && ad !== '/web/bekleyen') return hata(404, 'bulunamadı', origin);

  const g = await govdeOku(request);
  if (g.kod) return hata(g.kod, g.kod === 413 ? 'gövde çok büyük' : 'geçersiz JSON', origin);
  const v = g.veri;
  try {
    if (ad === '/web/abone') {
      const ab = v.abonelik;
      if (!ab || typeof ab !== 'object' || !endpointGecerli(ab.endpoint)) return hata(400, 'geçersiz endpoint', origin);
      const keys = ab.keys && typeof ab.keys === 'object' ? ab.keys : {};
      if (keys.p256dh !== undefined && !anahtarGecerli(keys.p256dh, 120)) return hata(400, 'geçersiz p256dh', origin);
      if (keys.auth !== undefined && !anahtarGecerli(keys.auth, 60)) return hata(400, 'geçersiz auth', origin);
      if (!DUZEYLER.includes(v.duzey)) return hata(400, 'geçersiz düzey', origin);
      const bolum = v.bolum === undefined || v.bolum === null ? '' : v.bolum;
      if (typeof bolum !== 'string' || bolum.trim().length > BOLUM_MAX) return hata(400, 'geçersiz bölüm', origin);
      const puan = v.puan === undefined ? null : v.puan;
      if (puan !== null && (typeof puan !== 'number' || !Number.isFinite(puan) || puan < 1 || puan > 100)) return hata(400, 'geçersiz puan', origin);
      await env.DB.prepare(
        `INSERT INTO web_aboneler (endpoint, p256dh, auth, duzey, bolum, puan, olusturma, aktif) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
         ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth, duzey = excluded.duzey,
           bolum = excluded.bolum, puan = excluded.puan, aktif = 1`,
      ).bind(ab.endpoint, keys.p256dh ?? null, keys.auth ?? null, v.duzey, bolum.trim(), puan, new Date().toISOString()).run();
      return yanit({ tamam: true }, 200, origin);
    }
    if (!endpointGecerli(v.endpoint)) return hata(400, 'geçersiz endpoint', origin);
    if (ad === '/web/sil') {
      await env.DB.prepare('DELETE FROM web_bekleyen WHERE endpoint = ?').bind(v.endpoint).run();
      await env.DB.prepare('DELETE FROM web_aboneler WHERE endpoint = ?').bind(v.endpoint).run();
      return yanit({ tamam: true }, 200, origin);
    }
    // /web/bekleyen: en çok 5 ilan döner; bu abonenin tüm bekleyenleri silinir (fazlası 'toplam' ile bildirilir).
    const r = await env.DB.prepare('SELECT baslik, kurum, url FROM web_bekleyen WHERE endpoint = ? ORDER BY zaman, ilan_id LIMIT 50').bind(v.endpoint).all();
    const satirlar = r.results || [];
    if (satirlar.length) await env.DB.prepare('DELETE FROM web_bekleyen WHERE endpoint = ?').bind(v.endpoint).run();
    return yanit({ tamam: true, toplam: satirlar.length, ilanlar: satirlar.slice(0, BEKLEYEN_GOSTER).map((s) => ({ baslik: s.baslik, kurum: s.kurum, url: s.url })) }, 200, origin);
  } catch {
    return hata(500, 'işlenemedi', origin);
  }
}

// ---------------------------------------------------------------- cron: yeni ilan -> abone eşleştirme + push

const kodlayici = new TextEncoder();
function jsonParcala(dizi) {
  const parcalar = [];
  let gecerli = [];
  let bayt = 2;
  for (const o of dizi) {
    const b = kodlayici.encode(JSON.stringify(o)).length + 1;
    if (gecerli.length && bayt + b > JSON_BAYT_MAX) { parcalar.push(gecerli); gecerli = []; bayt = 2; }
    gecerli.push(o); bayt += b;
  }
  if (gecerli.length) parcalar.push(gecerli);
  return parcalar.map((p) => JSON.stringify(p));
}

// ctx: {env, simdi, meta, metaYaz, tum, calis, kalanSql(), kalanIstek(), ilanCek(), fetch(url, opts)}
export async function webIsle(ctx) {
  const { env, simdi, meta } = ctx;
  if (!webAcik(env)) return;
  let idler = [];
  try { idler = JSON.parse(meta.web_ilanlari || '[]'); } catch { idler = []; }
  if (!Array.isArray(idler) || !idler.length) return;
  if (ctx.kalanSql() < 10 || ctx.kalanIstek() < 3) return;

  const bitir = async () => {
    await ctx.calis("DELETE FROM meta WHERE anahtar IN ('web_ilanlari', 'web_imleci')");
    await ctx.calis('DELETE FROM web_bekleyen WHERE zaman < ?', new Date(simdi.getTime() - BEKLEYEN_OMUR_MS).toISOString());
  };

  let ilanlar;
  try { ilanlar = await ctx.ilanCek(); } catch { return; }
  const kume = new Set(idler);
  const bugun = bugunIstanbul(simdi);
  const gorulen = new Set();
  const aktifler = [];
  for (const i of ilanlar) {
    const kimlikler = [i.id, ...liste(i.kimlikler)];
    if (!kimlikler.some((k) => kume.has(k)) || gorulen.has(i.id)) continue;
    gorulen.add(i.id);
    if (i.kategori === 'akademik' || sureDoldu(i, bugun, simdi)) continue;
    aktifler.push({ ilan: i, id: i.id, metin: katla(i.metin || [i.baslik, i.kurum].join(' ')) });
  }
  if (!aktifler.length) { await bitir(); return; }

  const limit = Math.max(1, Math.min(IS_SAYFA_MAX, ctx.kalanIstek(), Math.floor(CIFT_MAX / aktifler.length)));
  const imlec = meta.web_imleci ?? '';
  const aboneler = await ctx.tum('SELECT endpoint, duzey, bolum, puan FROM web_aboneler WHERE aktif = 1 AND endpoint > ? ORDER BY endpoint LIMIT ?', imlec, limit);
  const zaman = simdi.toISOString();
  const satirlar = [];
  const hedefler = [];
  for (const a of aboneler) {
    const kw = bolumKelimeleri(a.bolum);
    const eslesen = aktifler.filter((x) => webUygunMu(x.ilan, a, bugun, simdi, x.metin, kw)).slice(0, ABONE_BASINA_MAX);
    if (!eslesen.length) continue;
    hedefler.push(a.endpoint);
    for (const x of eslesen) {
      const i = x.ilan;
      satirlar.push([a.endpoint, x.id, String(i.baslik || '').slice(0, 160), String(i.kurum || '').slice(0, 100), i.sayfa || i.link || env.SITE_URL || 'https://kpsstercihi.com/', zaman]);
    }
  }
  for (const p of jsonParcala(satirlar)) {
    await ctx.calis(
      `INSERT OR IGNORE INTO web_bekleyen (endpoint, ilan_id, baslik, kurum, url, zaman)
       SELECT json_extract(value, '$[0]'), json_extract(value, '$[1]'), json_extract(value, '$[2]'),
              json_extract(value, '$[3]'), json_extract(value, '$[4]'), json_extract(value, '$[5]') FROM json_each(?)`, p,
    );
  }
  const olu = [];
  for (let n = 0; n < hedefler.length; n += PUSH_PARALEL) {
    const grup = hedefler.slice(n, n + PUSH_PARALEL);
    const kodlar = await Promise.all(grup.map((e) => pushGonder(env, e, ctx.fetch, simdi)));
    kodlar.forEach((k, j) => { if (k === 404 || k === 410) olu.push(grup[j]); });
  }
  if (olu.length) {
    await ctx.calis("DELETE FROM web_bekleyen WHERE endpoint IN (SELECT value FROM json_each(?))", JSON.stringify(olu));
    await ctx.calis("DELETE FROM web_aboneler WHERE endpoint IN (SELECT value FROM json_each(?))", JSON.stringify(olu));
  }
  if (aboneler.length < limit) { await bitir(); return; }
  await ctx.metaYaz([['web_imleci', aboneler[aboneler.length - 1].endpoint]]);
}
