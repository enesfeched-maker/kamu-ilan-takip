// GET /populer : site manşetinin kullandığı herkese açık popülerlik sıralaması. Kişisel veri içermez.
// Puan = ilan ayrıntısını gören + satırına tıklayan + kaydeden benzersiz oturum sayısı + 2 x resmî ilana giden oturum sayısı.
// manset_tikla bilerek hariçtir: manşetin kendi tıklamaları sıralamayı kendi kendine büyütmesin.
//
// D1 okuma maliyeti düşük tutulur:
//  - Tamamlanmış günler: gece bakımının yazdığı gün özetinden ('pop' boyutu, günde en çok 200 satır) okunur; ham tabloya dokunulmaz.
//    (Günler arası oturum eşleşmesi yok; sekme oturumu nadiren gün aşar, bu yüzden günlük puanlar toplanır.)
//  - Bugün: ham olaylar yalnız ts aralığıyla ve ARTIMLI okunur (son okunan ts'den sonrası); durum Cache API'de saklanır.
//  - Sonuç 30 dk Cache API + izolat belleğinde tutulur; tarayıcıya max-age=600 verilir.
import { izinliKokenler } from './toplama.js';
import { butceDurumu } from './butce.js';
import { gunEkle, gunBasSn, bugun } from './zaman.js';
import { onbellekli, okumaGunlugu, yaz as onbellegeYaz, oku_ as onbellektenOku, bellekSifirla } from './onbellek.js';

export const GUN = 7;
export const EN_COK = 100;
export const ONBELLEK_SN = 600; // tarayıcı
export const SUNUCU_ONBELLEK_SN = 1800;
const KEY_RE = /^[A-Za-z0-9-]{1,80}$/;

export function populerBellekSifirla() { bellekSifirla(); }

// Bugünün artımlı durumu: { gun, sonTs, s: { key: { gor: [os], satir_tikla: [], resmi_ilan: [], kaydet: [] } } }
async function bugunDurumu(env, simdiMs) {
  const bu = bugun(simdiMs), simdiSn = Math.floor(simdiMs / 1000);
  const kayit = await onbellektenOku('populer-durum');
  let d = null;
  try { d = kayit ? JSON.parse(kayit.govde) : null; } catch { d = null; }
  if (!d || d.gun !== bu) d = { gun: bu, sonTs: gunBasSn(bu), s: {} };
  const bas = Math.max(gunBasSn(bu), d.sonTs - 5); // 5 sn örtüşme; kümeler yineleneni eler
  const sonuc = await env.DB.prepare(
    `SELECT os, t, k, a, h FROM olaylar
     WHERE ts >= ? AND ((t = 'sayfa' AND k IS NOT NULL AND (sy = 'ilan' OR (sy = 'ana' AND v = 'ilan')))
       OR (t = 'tikla' AND a IN ('satir_tikla', 'resmi_ilan', 'kaydet') AND h IS NOT NULL))`,
  ).bind(bas).all();
  okumaGunlugu('populer/bugun', sonuc);
  for (const o of sonuc.results || []) {
    const key = o.t === 'sayfa' ? o.k : o.h;
    if (!key || !KEY_RE.test(key)) continue;
    const tur = o.t === 'sayfa' ? 'gor' : o.a;
    const m = d.s[key] || (d.s[key] = { gor: [], satir_tikla: [], resmi_ilan: [], kaydet: [] });
    if (!m[tur].includes(o.os)) m[tur].push(o.os);
  }
  d.sonTs = simdiSn;
  await onbellegeYaz('populer-durum', JSON.stringify(d), 86400, simdiMs);
  return d;
}

export async function populerHesapla(env, simdiMs) {
  const bu = bugun(simdiMs);
  const puan = new Map();
  const ekle = (key, p) => puan.set(key, (puan.get(key) || 0) + p);
  const gecmis = await env.DB.prepare(
    `SELECT k1, SUM(say) AS p FROM ozet WHERE boyut = 'pop' AND gun BETWEEN ? AND ? AND gun IN (SELECT gun FROM ozet_gun) GROUP BY k1`,
  ).bind(gunEkle(bu, -(GUN - 1)), gunEkle(bu, -1)).all();
  okumaGunlugu('populer/gecmis', gecmis);
  for (const r of gecmis.results || []) if (KEY_RE.test(r.k1)) ekle(r.k1, Number(r.p) || 0);
  const d = await bugunDurumu(env, simdiMs);
  for (const [key, m] of Object.entries(d.s)) ekle(key, m.gor.length + m.satir_tikla.length + 2 * m.resmi_ilan.length + m.kaydet.length);
  const puanlar = [...puan].filter(([, p]) => p > 0).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return { guncelleme: new Date(simdiMs).toISOString(), gun: GUN, ilanlar: Object.fromEntries(puanlar.slice(0, EN_COK)) };
}

export async function populerIstegi(request, env, simdiMs = Date.now()) {
  const origin = request.headers.get('Origin') || '';
  const cors = {};
  if (izinliKokenler(env).includes(origin)) { cors['Access-Control-Allow-Origin'] = origin; cors.Vary = 'Origin'; }
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...cors, 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Max-Age': '86400' } });
  if (request.method !== 'GET') return new Response(null, { status: 405, headers: cors });
  const b = await butceDurumu(env, simdiMs);
  const o = await onbellekli('populer', SUNUCU_ONBELLEK_SN, async () => JSON.stringify(await populerHesapla(env, simdiMs)), simdiMs, false, b.okumaKademesi >= 1);
  if (!o) {
    // Okuma bütçesi doldu ve elde kayıt yok: D1'e gidilmez.
    return new Response(JSON.stringify({ guncelleme: new Date(simdiMs).toISOString(), gun: GUN, ilanlar: {}, kota_korumasi: true, mesaj: 'kota koruması: veri yarın' }), {
      headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=300', 'X-Content-Type-Options': 'nosniff' },
    });
  }
  return new Response(o.govde, {
    headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `public, max-age=${ONBELLEK_SN}`, 'X-Content-Type-Options': 'nosniff' },
  });
}
