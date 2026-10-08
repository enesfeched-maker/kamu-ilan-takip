// POST /o : olay toplama. Çerez ve kalıcı tarayıcı kimliği yok; ziyaretçi = SHA-256(günlük tuz + IP + User-Agent).
import { paketDogrula, MAKS_BAYT } from './dogrula.js';
import { botMu, cihazTuru, tarayiciAilesi, isletimAilesi, genislikKovasi } from './ua.js';
import { kaynakSinifla } from './kaynak.js';
import { trParcalari } from './zaman.js';
import { butceDurumu, olaylariSuz } from './butce.js';

export const HIZ_PENCERE_SN = 600;
export const HIZ_SINIR = 300; // ziyaretçi başına 10 dakikada en çok 300 olay

const hizTablosu = new Map(); // yalnız bu Worker örneğinin belleğinde (en iyi çaba); kalıcı bir yere yazılmaz
const tuzOnbellek = new Map();

export function hizSifirla() { hizTablosu.clear(); tuzOnbellek.clear(); }

// Sınır aşılırsa false. Yeni pencerede sayaç sıfırlanır.
export function hizDene(zv, adet, simdiSn) {
  let k = hizTablosu.get(zv);
  if (!k || simdiSn - k.basla >= HIZ_PENCERE_SN) {
    if (hizTablosu.size > 5000) {
      for (const [a, b] of hizTablosu) if (simdiSn - b.basla >= HIZ_PENCERE_SN) hizTablosu.delete(a);
      if (hizTablosu.size > 5000) hizTablosu.clear();
    }
    k = { basla: simdiSn, say: 0 };
    hizTablosu.set(zv, k);
  }
  if (k.say + adet > HIZ_SINIR) return false;
  k.say += adet;
  return true;
}

export async function sha256Hex(metin) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(metin));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
}

function rastgeleHex(bayt = 16) {
  const a = new Uint8Array(bayt);
  crypto.getRandomValues(a);
  return [...a].map((x) => x.toString(16).padStart(2, '0')).join('');
}

// Günün tuzunu getirir (yoksa üretir). Eski günlerin tuzları bakım işinde silinir.
export async function gunlukTuz(db, gun) {
  const o = tuzOnbellek.get(gun);
  if (o) return o;
  await db.prepare('INSERT OR IGNORE INTO tuz (gun, tuz) VALUES (?, ?)').bind(gun, rastgeleHex(16)).run();
  const r = await db.prepare('SELECT tuz FROM tuz WHERE gun = ?').bind(gun).first();
  if (tuzOnbellek.size > 3) tuzOnbellek.clear();
  tuzOnbellek.set(gun, r.tuz);
  return r.tuz;
}

export async function ziyaretciOzeti(tuz, ip, ua) {
  return (await sha256Hex(`${tuz}|${ip}|${ua}`)).slice(0, 16);
}

export function izinliKokenler(env) {
  return String(env.IZINLI_KOKENLER || 'https://kpsstercihi.com,https://www.kpsstercihi.com').split(',').map((s) => s.trim()).filter(Boolean);
}

export function corsBasliklari(request, env) {
  const origin = request.headers.get('Origin') || '';
  const izinli = izinliKokenler(env).includes(origin) || (env.ORTAM === 'yerel' && /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin));
  if (!izinli) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

const yanit = (durum, cors, metin = null) => new Response(metin, { status: durum, headers: { ...cors, 'Cache-Control': 'no-store' } });

const SUTUNLAR = ['ts', 'gun', 'saat', 'hg', 'zv', 'os', 't', 'p', 'sy', 'v', 'k', 'a', 'h', 'x', 'n', 'n2', 'ilk', 'yeni',
  'ulke', 'bolge', 'sehir', 'cihaz', 'tarayici', 'isletim', 'gen', 'dil', 'kaynak', 'rhost', 'us', 'um', 'uc'];
const EKLE = `INSERT INTO olaylar (${SUTUNLAR.join(', ')}) VALUES (${SUTUNLAR.map(() => '?').join(', ')})`;

const kisa = (v, n) => (typeof v === 'string' && v ? v.slice(0, n) : null);

// D1 yazma kotası koruması (izolat belleğinde yaklaşık sayaç; ek D1 yazımı yok): gün içinde kabul edilen olay sayısı
// GUNLUK_YUMUSAK_SINIR'ı aşarsa (ya da TOPLAMA_AZALT=1 ise) 'aktif' ve 'kaydirma' olayları %50 örneklenir; saklanan olay
// n2 = 2 ağırlığı taşır, panel ağırlıklı toplar, böylece toplamlar yaklaşık doğru kalır.
export const GUNLUK_YUMUSAK_SINIR = 30000;
const sayac = { gun: '', say: 0 };
export function sayacSifirla() { sayac.gun = ''; sayac.say = 0; }
export function sayacAyarla(gun, say) { sayac.gun = gun; sayac.say = say; }
export function sayacOku() { return { ...sayac }; }

export async function topla(request, env, simdiMs = Date.now(), rastgele = Math.random) {
  const cors = corsBasliklari(request, env);
  if (request.method === 'OPTIONS') return yanit(204, cors);
  if (request.method !== 'POST') return yanit(405, cors);
  if (!cors['Access-Control-Allow-Origin']) return yanit(403, {});
  if (env.TOPLAMA_KAPALI === '1') return yanit(204, cors);
  // Ölçmeme tercihleri: hiçbir şey saklanmaz.
  if (request.headers.get('Sec-GPC') === '1' || request.headers.get('DNT') === '1') return yanit(204, cors);
  const ua = request.headers.get('User-Agent') || '';
  if (botMu(ua)) return yanit(204, cors);
  // Günlük D1 yazma bütçesi (butce.js): son kademede hiçbir şey yazılmaz.
  const butce = await butceDurumu(env, simdiMs);
  if (butce.yazmaKademesi >= 3) return yanit(204, cors);
  const uzunluk = Number(request.headers.get('Content-Length') || 0);
  if (uzunluk > MAKS_BAYT) return yanit(413, cors);

  const paket = paketDogrula(await request.text());
  if (paket.hata) return yanit(paket.hata === 'buyuk' ? 413 : 400, cors);
  if (!paket.olaylar.length) return yanit(204, cors);

  const simdiSn = Math.floor(simdiMs / 1000);
  const { gun, saat, hg } = trParcalari(simdiSn);
  if (sayac.gun !== gun) { sayac.gun = gun; sayac.say = 0; }
  const azalt = env.TOPLAMA_AZALT === '1' || sayac.say > GUNLUK_YUMUSAK_SINIR;
  const butceSuzulen = olaylariSuz(paket.olaylar, butce.yazmaKademesi);
  const olaylar = azalt
    ? butceSuzulen.filter((e) => (e.t !== 'aktif' && e.t !== 'kaydirma') || (rastgele() < 0.5 && (e.n2 = 2)))
    : butceSuzulen;
  if (!olaylar.length) return yanit(204, cors);
  const tuz = await gunlukTuz(env.DB, gun);
  const ip = request.headers.get('CF-Connecting-IP') || '';
  const zv = await ziyaretciOzeti(tuz, ip, ua);
  if (!hizDene(zv, paket.olaylar.length, simdiSn)) return yanit(429, cors);

  const cf = request.cf || {};
  const oturumOzellikleri = {
    ulke: /^[A-Za-z]{2}$/.test(cf.country || '') ? cf.country.toUpperCase() : null,
    bolge: kisa(cf.region, 40),
    sehir: kisa(cf.city, 40),
    cihaz: cihazTuru(ua),
    tarayici: tarayiciAilesi(ua),
    isletim: isletimAilesi(ua),
    gen: genislikKovasi(paket.genislik) || null,
    dil: paket.dil,
    kaynak: kaynakSinifla(paket.rhost, paket.utm.s),
    rhost: paket.rhost,
    us: paket.utm.s, um: paket.utm.m, uc: paket.utm.c,
  };

  let ilkVar = false;
  sayac.say += olaylar.length;
  const komutlar = olaylar.map((e) => {
    const ilk = e.t === 'sayfa' && e.f && !ilkVar ? 1 : 0;
    if (ilk) ilkVar = true;
    const oz = ilk ? oturumOzellikleri : {};
    const deger = {
      ts: simdiSn, gun, saat, hg, zv, os: paket.oturum, t: e.t, p: e.p, sy: e.sy, v: e.v, k: e.k, a: e.a, h: e.h, x: e.x, n: e.n, n2: e.n2,
      ilk, yeni: ilk ? (paket.geri ? 0 : 1) : null,
      ulke: null, bolge: null, sehir: null, cihaz: null, tarayici: null, isletim: null, gen: null, dil: null, kaynak: null, rhost: null, us: null, um: null, uc: null,
      ...oz,
    };
    return env.DB.prepare(EKLE).bind(...SUTUNLAR.map((s) => deger[s] ?? null));
  });
  // Bir işaretçinin tüm olayları TEK batch'te (tek işlem, tek gidiş-dönüş) yazılır. Çok satırlı tek INSERT yazılan satır sayısını
  // azaltmaz ve D1'in 100 bağlı parametre sınırı yüzünden (31 sütun) en çok 3 satıra sığar; bu yüzden batch kullanılır.
  await env.DB.batch(komutlar);
  return yanit(204, cors);
}
