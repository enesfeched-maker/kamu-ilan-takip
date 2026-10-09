// /aranan: son 7 günde çok aranıp sonuç çıkmayan kelimeler (sabah özeti ve taban puanları sayfası için).
// Yalnız gün özetinden (ozet, boyut='arama') okunur; ham tabloya gidilmez. Sonuç 12 saat önbellekte.
// Gizlilik: yalnız en az ESIK farklı oturumda aranmış, harf ve boşluktan oluşan kısa kelimeler döner.
import { izinliKokenler } from './toplama.js';
import { butceDurumu } from './butce.js';
import { gunEkle, bugun } from './zaman.js';
import { onbellekli, okumaGunlugu } from './onbellek.js';

export const ARANAN_GUN = 7;
export const ESIK = 3;
const EN_COK = 10;
const SUNUCU_ONBELLEK_SN = 12 * 3600;
const KELIME_RE = /^[a-zçğıöşü ]{3,30}$/;

export async function arananHesapla(env, simdiMs = Date.now()) {
  const bu = bugun(simdiMs);
  const r = await env.DB.prepare(
    `SELECT k1, SUM(CASE WHEN k2 = 'sifir' THEN oturum ELSE 0 END) AS sifir, SUM(CASE WHEN k2 = 'var' THEN oturum ELSE 0 END) AS var_
     FROM ozet WHERE boyut = 'arama' AND gun >= ? AND gun < ? GROUP BY k1`,
  ).bind(gunEkle(bu, -ARANAN_GUN), bu).all();
  okumaGunlugu('aranan', r);
  const kelimeler = (r.results || [])
    .map((s) => ({ k: String(s.k1 || '').trim(), n: Number(s.sifir) || 0, v: Number(s.var_) || 0 }))
    // Çoğunlukla sonuçsuz kalan aramalar: sonuç çıkan oturumlar sıfırların yarısından azsa.
    .filter((s) => KELIME_RE.test(s.k) && s.n >= ESIK && s.v * 2 < s.n)
    .sort((a, b) => b.n - a.n || a.k.localeCompare(b.k))
    .slice(0, EN_COK)
    .map((s) => ({ kelime: s.k, oturum: s.n }));
  return { guncelleme: new Date(simdiMs).toISOString(), gun: ARANAN_GUN, kelimeler };
}

export async function arananIstegi(request, env, simdiMs = Date.now()) {
  const origin = request.headers.get('Origin') || '';
  const cors = {};
  if (izinliKokenler(env).includes(origin)) { cors['Access-Control-Allow-Origin'] = origin; cors.Vary = 'Origin'; }
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...cors, 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Max-Age': '86400' } });
  if (request.method !== 'GET') return new Response(null, { status: 405, headers: cors });
  const b = await butceDurumu(env, simdiMs);
  const o = await onbellekli('aranan', SUNUCU_ONBELLEK_SN, async () => JSON.stringify(await arananHesapla(env, simdiMs)), simdiMs, false, b.okumaKademesi >= 1);
  const govde = o ? o.govde : JSON.stringify({ guncelleme: new Date(simdiMs).toISOString(), gun: ARANAN_GUN, kelimeler: [], kota_korumasi: true });
  return new Response(govde, {
    headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=3600', 'X-Content-Type-Options': 'nosniff' },
  });
}
