// GET /populer : site manşetinin kullandığı herkese açık popülerlik sıralaması. Kişisel veri içermez.
// Puan = ilan ayrıntısını gören + satırına tıklayan + kaydeden benzersiz oturum sayısı + 2 x resmî ilana giden oturum sayısı.
// manset_tikla bilerek hariçtir: manşetin kendi tıklamaları sıralamayı kendi kendine büyütmesin.
import { izinliKokenler } from './toplama.js';

export const GUN = 7;
export const EN_COK = 100;
export const ONBELLEK_SN = 600;
const KEY_RE = /^[A-Za-z0-9-]{1,80}$/;

let bellek = { ms: 0, govde: null };
export function populerBellekSifirla() { bellek = { ms: 0, govde: null }; }

function ilanAnahtari(o) {
  if (o.t === 'sayfa') {
    if (o.v === 'ilan' && o.k) return o.k;
    const m = /^\/ilan\/([^/]+)\/?$/.exec(o.p || '');
    return m ? m[1] : null;
  }
  return o.h || null;
}

export async function populerHesapla(env, simdiMs) {
  const bas = Math.floor(simdiMs / 1000) - GUN * 86400;
  const { results } = await env.DB.prepare(
    `SELECT DISTINCT os, t, v, p, k, a, h FROM olaylar
     WHERE ts >= ? AND ((t = 'sayfa' AND (v = 'ilan' OR p LIKE '/ilan/%'))
       OR (t = 'tikla' AND a IN ('satir_tikla', 'resmi_ilan', 'kaydet')))`,
  ).bind(bas).all();
  // anahtar -> tür -> oturum kümesi (aynı oturum aynı türü yalnız bir kez sayar)
  const harita = new Map();
  for (const o of results) {
    const tur = o.t === 'sayfa' ? 'gor' : o.a;
    const key = ilanAnahtari(o);
    if (!key || !KEY_RE.test(key)) continue;
    if (!harita.has(key)) harita.set(key, { gor: new Set(), satir_tikla: new Set(), resmi_ilan: new Set(), kaydet: new Set() });
    harita.get(key)[tur].add(o.os);
  }
  const puanlar = [];
  for (const [key, t] of harita) {
    const puan = t.gor.size + t.satir_tikla.size + 2 * t.resmi_ilan.size + t.kaydet.size;
    if (puan > 0) puanlar.push([key, puan]);
  }
  puanlar.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return { guncelleme: new Date(simdiMs).toISOString(), gun: GUN, ilanlar: Object.fromEntries(puanlar.slice(0, EN_COK)) };
}

export async function populerIstegi(request, env, simdiMs = Date.now()) {
  const origin = request.headers.get('Origin') || '';
  const cors = {};
  if (izinliKokenler(env).includes(origin)) { cors['Access-Control-Allow-Origin'] = origin; cors.Vary = 'Origin'; }
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...cors, 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Max-Age': '86400' } });
  if (request.method !== 'GET') return new Response(null, { status: 405, headers: cors });
  if (!bellek.govde || simdiMs - bellek.ms >= ONBELLEK_SN * 1000) bellek = { ms: simdiMs, govde: JSON.stringify(await populerHesapla(env, simdiMs)) };
  return new Response(bellek.govde, {
    headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `public, max-age=${ONBELLEK_SN}`, 'X-Content-Type-Options': 'nosniff' },
  });
}
