// /liderlik : katiplik liderlik tablosu. GET herkese açık sıralamayı verir; POST bir sınav sonucunu ekler.
// Tarayıcının söylediği nete güvenilmez: yazılan metin, sitenin kendi puanlama motoruyla (puanla.js) resmî metne karşı
// sunucuda yeniden puanlanır. Kişisel veri yok: takma ad + tarayıcının rastgele anahtarının özeti.
// Yalnız 3 dakikalık resmî koşullar sayılır: sınav simülasyonu ve günün metni, 2025 resmî metinleri (zk2025).
import { corsBasliklari, sha256Hex } from './toplama.js';
import { butceDurumu } from './butce.js';
import { trParcalari, gunEkle } from './zaman.js';
import { onbellekli, yaz as onbellegeYaz, okumaGunlugu } from './onbellek.js';
import { RESMI_METINLER, puanla, zincir } from './katip-metin.js';

export const SURE = 180;
export const EN_COK = 20;
export const ONBELLEK_SN = 120;
export const MAKS_YAZI = 4000;
export const MAKS_DK_VURUS = 1000;   // dakikada 1000 vuruşun üstü insan için gerçekçi değil
export const MAKS_NET = 260;
const HIZ_PENCERE_SN = 600, HIZ_SINIR = 10; // IP başına 10 dakikada en çok 10 gönderim

const hiz = new Map();
export function liderlikHizSifirla() { hiz.clear(); }
function hizDene(anahtar, simdiSn) {
  let k = hiz.get(anahtar);
  if (!k || simdiSn - k.basla >= HIZ_PENCERE_SN) {
    if (hiz.size > 5000) hiz.clear();
    k = { basla: simdiSn, say: 0 };
    hiz.set(anahtar, k);
  }
  if (k.say >= HIZ_SINIR) return false;
  k.say++;
  return true;
}

export function haftaBasi(simdiMs) {
  const { gun, hg } = trParcalari(Math.floor(simdiMs / 1000));
  return gunEkle(gun, -hg);
}

// Küfür ve sitenin adını taklit eden takma adlar reddedilir (Türkçe harfler sadeleştirilip harf dışı karakterler atılarak).
const YASAK = ['orospu', 'amcik', 'amina', 'aminak', 'amk', 'yarrak', 'yarak', 'siktir', 'sikis', 'sikerim', 'sikik', 'pezevenk',
  'kahpe', 'gavat', 'ibne', 'pust', 'yavsak', 'serefsiz', 'oc', 'pic', 'gotveren', 'gotunu', 'kaltak', 'surtuk', 'fuck', 'shit', 'bitch',
  'kpsstercihi', 'yonetici', 'admin', 'moderator'];
const sade = (s) => s.toLocaleLowerCase('tr-TR').replace(/ı/g, 'i').replace(/ş/g, 's').replace(/ğ/g, 'g').replace(/ç/g, 'c')
  .replace(/ö/g, 'o').replace(/ü/g, 'u').replace(/[âà]/g, 'a').replace(/[îì]/g, 'i').replace(/[ûù]/g, 'u').replace(/[^a-z]/g, '');
const KISA_YASAK = new Set(['oc', 'pic', 'amk']); // kısa kökler yalnız kelimenin tamamıysa

export function adDogrula(ham) {
  const ad = String(ham || '').replace(/\s+/g, ' ').trim();
  if (ad.length < 2 || ad.length > 18 || !/^[\p{L}\p{N} ._-]+$/u.test(ad) || !/\p{L}/u.test(ad)) return null;
  const tum = sade(ad);
  const kelimeler = ad.split(/[ ._-]+/).map(sade);
  for (const y of YASAK) {
    if (KISA_YASAK.has(y) ? kelimeler.includes(y) : tum.includes(y)) return null;
  }
  return ad;
}

// Gönderimi doğrular ve yeniden puanlar. Hata varsa { hata } döner.
export function sonucDogrula(g) {
  if (!g || typeof g !== 'object') return { hata: 'bicim' };
  const ad = adDogrula(g.ad);
  if (!ad) return { hata: 'ad' };
  if (typeof g.anahtar !== 'string' || !/^[a-f0-9]{32}$/.test(g.anahtar)) return { hata: 'bicim' };
  if (g.mod !== 'sinav' && g.mod !== 'gunluk') return { hata: 'mod' };
  if (g.kut !== 'zk2025' || !Number.isInteger(g.no) || g.no < 0 || g.no >= RESMI_METINLER.length) return { hata: 'metin' };
  if (typeof g.yazi !== 'string' || !g.yazi.trim() || g.yazi.length > MAKS_YAZI) return { hata: 'bicim' };
  const vurus = Number(g.vurus);
  // Yapıştırma sitede engelli; yine de tuş vuruşu sayısı yazılan karakterden belirgin azsa sonuç kabul edilmez.
  if (!Number.isInteger(vurus) || vurus < g.yazi.trimEnd().length * 0.9) return { hata: 'supheli' };
  const r = puanla(zincir(RESMI_METINLER, g.no, SURE), g.yazi, { sure: SURE, saniye: SURE });
  if (r.toplam < 10 || r.net < 1) return { hata: 'kisa' };
  if (r.dakikaVurus > MAKS_DK_VURUS || r.net > MAKS_NET) return { hata: 'supheli' };
  return { ad, anahtar: g.anahtar, net: r.net, dogru: r.dogru, hatali: r.hatali, dk: r.dakikaVurus };
}

export async function tabloHesapla(env, simdiMs) {
  const hafta = haftaBasi(simdiMs);
  const h = await env.DB.prepare('SELECT kimlik, ad, net, dk FROM liderlik WHERE hafta = ? ORDER BY net DESC, ts ASC LIMIT ?').bind(hafta, EN_COK).all();
  // Tüm zamanlar: kişi başına en iyi hafta (SQLite'ta MAX ile seçilen satırın diğer sütunları o satırdan gelir).
  const t = await env.DB.prepare('SELECT kimlik, ad, MAX(net) AS net, dk FROM liderlik GROUP BY kimlik ORDER BY net DESC LIMIT ?').bind(EN_COK).all();
  okumaGunlugu('liderlik', h, t);
  const satir = (r) => ({ i: r.kimlik, ad: r.ad, net: r.net, dk: r.dk });
  return { guncelleme: new Date(simdiMs).toISOString(), hafta, haftalik: (h.results || []).map(satir), tum: (t.results || []).map(satir) };
}

const json = (veri, durum, basliklar) => new Response(JSON.stringify(veri), {
  status: durum, headers: { ...basliklar, 'Content-Type': 'application/json; charset=utf-8', 'X-Content-Type-Options': 'nosniff' },
});

export async function liderlikIstegi(request, env, simdiMs = Date.now()) {
  const cors = corsBasliklari(request, env);
  if (cors['Access-Control-Allow-Origin']) cors['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS';
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
  const b = await butceDurumu(env, simdiMs);

  if (request.method === 'GET') {
    const o = await onbellekli('liderlik', ONBELLEK_SN, async () => JSON.stringify(await tabloHesapla(env, simdiMs)), simdiMs, false, b.okumaKademesi >= 1);
    if (!o) return json({ hafta: haftaBasi(simdiMs), haftalik: [], tum: [], kota_korumasi: true }, 200, { ...cors, 'Cache-Control': 'public, max-age=300' });
    return new Response(o.govde, { headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=60', 'X-Content-Type-Options': 'nosniff' } });
  }
  if (request.method !== 'POST') return new Response(null, { status: 405, headers: cors });
  const nc = { ...cors, 'Cache-Control': 'no-store' };
  if (!cors['Access-Control-Allow-Origin']) return json({ hata: 'koken' }, 403, nc);
  if (b.yazmaKademesi >= 2 || b.okumaKademesi >= 2) return json({ hata: 'kota' }, 503, nc);
  if (Number(request.headers.get('Content-Length') || 0) > 16000) return json({ hata: 'buyuk' }, 413, nc);
  const simdiSn = Math.floor(simdiMs / 1000);
  const ip = request.headers.get('CF-Connecting-IP') || '';
  if (!hizDene(await sha256Hex('liderlik|' + ip), simdiSn)) return json({ hata: 'hiz' }, 429, nc);

  let govde;
  try { govde = JSON.parse((await request.text()).slice(0, 16000)); } catch { return json({ hata: 'bicim' }, 400, nc); }
  const s = sonucDogrula(govde);
  if (s.hata) return json({ hata: s.hata }, 400, nc);

  const hafta = haftaBasi(simdiMs);
  const kimlik = (await sha256Hex(s.anahtar)).slice(0, 16);
  await env.DB.prepare(
    `INSERT INTO liderlik (hafta, kimlik, ad, net, dogru, hatali, dk, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT (hafta, kimlik) DO UPDATE SET ad = excluded.ad,
       dogru = CASE WHEN excluded.net > liderlik.net THEN excluded.dogru ELSE liderlik.dogru END,
       hatali = CASE WHEN excluded.net > liderlik.net THEN excluded.hatali ELSE liderlik.hatali END,
       dk = CASE WHEN excluded.net > liderlik.net THEN excluded.dk ELSE liderlik.dk END,
       ts = CASE WHEN excluded.net > liderlik.net THEN excluded.ts ELSE liderlik.ts END,
       net = MAX(liderlik.net, excluded.net)`,
  ).bind(hafta, kimlik, s.ad, s.net, s.dogru, s.hatali, s.dk, simdiSn).run();
  // Eklenen kişi tabloyu hemen görsün: önbellek yeniden üretilir ve yanıtla birlikte döner.
  const tablo = await tabloHesapla(env, simdiMs);
  await onbellegeYaz('liderlik', JSON.stringify(tablo), ONBELLEK_SN, simdiMs);
  const sira = await env.DB.prepare('SELECT COUNT(*) AS n FROM liderlik WHERE hafta = ? AND net > ?').bind(hafta, s.net).first();
  return json({ ok: true, net: s.net, sira: (Number(sira && sira.n) || 0) + 1, kimlik, tablo }, 200, nc);
}
