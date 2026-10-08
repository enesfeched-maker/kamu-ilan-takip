// Günlük D1 kota bekçisi (Cloudflare ücretsiz plan; kota HESAP GENELİNDE ve UTC gün başında sıfırlanır).
// Bu Worker her D1 ifadesinin meta.rows_written / rows_read değerini sayar, izolat başına en çok dakikada bir `butce` tablosuna
// yazar ve tüm izolatların toplamını dakikada bir okur. Toplam bütçeyi aşmaya yaklaştıkça veri toplama ve okuma kademeli kısılır.
export const VARSAYILAN_YAZMA = 60000; // analiz için günlük yazma bütçesi (hesap kotası 100.000; kalan bot + pay için)
export const VARSAYILAN_OKUMA = 3000000; // analiz için günlük okuma bütçesi (hesap kotası 5.000.000)
export const YENILE_MS = 60000;

// Kademe eşikleri bütçenin oranıdır (60.000 yazma için 40.000 / 55.000 / 60.000).
const YAZMA_ORAN = [40 / 60, 55 / 60, 1];
const OKUMA_ORAN = [2.5 / 3, 1];

export const YAZMA_ADLARI = ['normal', 'azaltilmis', 'kisitli', 'durdu'];
export const OKUMA_ADLARI = ['normal', 'onbellek', 'durdu'];

// kademe 1: aktif, kaydirma, hiz atılır. kademe 2: yalnız sayfa + belirli tıklamalar kalır.
export const KADEME1_ATILAN = new Set(['aktif', 'kaydirma', 'hiz']);
export const KADEME2_TIKLA = new Set(['resmi_ilan', 'telegram', 'arama', 'satir_tikla']);

let saat = () => Date.now();
export function butceSaatAyarla(fn) { saat = fn || (() => Date.now()); }

const durum = {
  yerel: { gun: '', yazma: 0, okuma: 0 }, // henüz tabloya yazılmamış, bu izolatın harcaması
  genel: { gun: '', yazma: 0, okuma: 0, ms: 0 }, // tablodaki son okunan hesap toplamı
  bekleyen: null,
};

export function butceSifirla() {
  durum.yerel = { gun: '', yazma: 0, okuma: 0 };
  durum.genel = { gun: '', yazma: 0, okuma: 0, ms: 0 };
  durum.bekleyen = null;
}

export const utcGun = (ms) => new Date(ms).toISOString().slice(0, 10);

function sinirlar(env) {
  const sayi = (v, d) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : d; };
  return { yazma: sayi(env && env.BUTCE_YAZMA, VARSAYILAN_YAZMA), okuma: sayi(env && env.BUTCE_OKUMA, VARSAYILAN_OKUMA) };
}

export function yazmaKademesi(yazma, sinir) {
  let k = 0;
  for (let i = 0; i < YAZMA_ORAN.length; i++) if (yazma >= Math.round(sinir * YAZMA_ORAN[i])) k = i + 1;
  return k;
}
export function okumaKademesi(okuma, sinir) {
  let k = 0;
  for (let i = 0; i < OKUMA_ORAN.length; i++) if (okuma >= Math.round(sinir * OKUMA_ORAN[i])) k = i + 1;
  return k;
}

function say(meta) {
  if (!meta) return;
  const gun = utcGun(saat());
  const y = durum.yerel;
  if (y.gun !== gun) { if (y.yazma || y.okuma) return harcamaGunDegisti(gun, meta); y.gun = gun; }
  if (typeof meta.rows_written === 'number') y.yazma += meta.rows_written;
  if (typeof meta.rows_read === 'number') y.okuma += meta.rows_read;
}
// Gün dönerken eski günün bekleyen sayacı korunur (bir sonraki yenilemede kendi gününe yazılır).
function harcamaGunDegisti(gun, meta) {
  durum.eskiGunler = durum.eskiGunler || [];
  const y = durum.yerel;
  durum.eskiGunler.push({ gun: y.gun, yazma: y.yazma, okuma: y.okuma });
  y.gun = gun; y.yazma = 0; y.okuma = 0;
  say(meta);
}

const SAYILDI = Symbol('butce');

function sarmalaIfade(st) {
  return {
    _st: st,
    bind(...a) { return sarmalaIfade(st.bind(...a)); },
    async run() { const s = await st.run(); say(s && s.meta); return s; },
    async all() { const s = await st.all(); say(s && s.meta); return s; },
    // first() meta döndürmez; all() ile okunup ilk satır verilir (okunan satır sayısı aynıdır).
    async first() { const s = await st.all(); say(s && s.meta); return (s.results && s.results[0]) ?? null; },
    async raw(...a) { return st.raw(...a); },
  };
}

// env.DB'yi sayaçlı sarmalayıcıyla değiştirilmiş bir env kopyası verir (bir kez sarmalar).
export function butceSarmala(env) {
  if (!env || !env.DB || env.DB[SAYILDI]) return env;
  const db = env.DB;
  const sarmal = {
    [SAYILDI]: true,
    _db: db,
    prepare: (sql) => sarmalaIfade(db.prepare(sql)),
    async batch(liste) {
      const out = await db.batch(liste.map((s) => (s && s._st) || s));
      for (const s of out || []) say(s && s.meta);
      return out;
    },
  };
  return { ...env, DB: sarmal };
}

const hamDb = (env) => (env.DB && env.DB._db) || env.DB;

// Bekleyen sayaçları tabloya yazar (UPSERT) ve hesap toplamını okur. Tek istekte iki ifade, tek gidiş-dönüş.
async function yenile(env, gun, ms) {
  const db = hamDb(env);
  const g = durum.genel;
  const gonder = [];
  const y = durum.yerel;
  if (y.gun && y.gun !== gun && (y.yazma || y.okuma)) { gonder.push({ gun: y.gun, yazma: y.yazma, okuma: y.okuma }); y.yazma = 0; y.okuma = 0; }
  y.gun = gun;
  for (const e of durum.eskiGunler || []) gonder.push(e);
  durum.eskiGunler = [];
  if (y.yazma || y.okuma) { gonder.push({ gun, yazma: y.yazma, okuma: y.okuma }); y.yazma = 0; y.okuma = 0; }
  const UPSERT = 'INSERT INTO butce (gun_utc, yazma, okuma) VALUES (?, ?, ?) ON CONFLICT(gun_utc) DO UPDATE SET yazma = yazma + excluded.yazma, okuma = okuma + excluded.okuma';
  const ifadeler = gonder.map((r) => db.prepare(UPSERT).bind(r.gun, r.yazma, r.okuma));
  ifadeler.push(db.prepare('SELECT yazma, okuma FROM butce WHERE gun_utc = ?').bind(gun));
  let out;
  try { out = await db.batch(ifadeler); } catch (e) {
    // Yazılamadı: sayaçlar geri konur, bir dakika sonra yeniden denenir.
    for (const r of gonder) { if (r.gun === gun) { y.yazma += r.yazma; y.okuma += r.okuma; } else (durum.eskiGunler = durum.eskiGunler || []).push(r); }
    console.log('butce yenileme hatası:', e && e.message);
    return;
  }
  const satir = (out[out.length - 1].results || [])[0];
  g.gun = gun; g.yazma = satir ? Number(satir.yazma) || 0 : 0; g.okuma = satir ? Number(satir.okuma) || 0 : 0;
  // Yenilemenin kendi maliyeti sonraki yenilemeye yazılır.
  for (const s of out) { const m = s && s.meta; if (m) { y.yazma += m.rows_written || 0; y.okuma += m.rows_read || 0; } }
}

// En çok dakikada bir yenilenir; eşzamanlı istekler aynı yenilemeyi bekler.
export async function butceHazirla(env, simdiMs = saat()) {
  if (!env || !env.DB || !env.DB._db) return; // sayaçsız (sarmalanmamış) DB: bütçe izlenmez
  const gun = utcGun(simdiMs);
  const g = durum.genel;
  if (g.gun === gun && simdiMs - g.ms < YENILE_MS && simdiMs >= g.ms) return;
  if (durum.bekleyen) return durum.bekleyen;
  g.ms = simdiMs;
  if (g.gun !== gun) { g.gun = gun; g.yazma = 0; g.okuma = 0; }
  durum.bekleyen = yenile(env, gun, simdiMs).finally(() => { durum.bekleyen = null; });
  return durum.bekleyen;
}

// Anlık durum: son okunan hesap toplamı + bu izolatın henüz yazılmamış harcaması.
export function butceOku(env, simdiMs = saat()) {
  const gun = utcGun(simdiMs);
  const s = sinirlar(env);
  const g = durum.genel.gun === gun ? durum.genel : { yazma: 0, okuma: 0 };
  const y = durum.yerel.gun === gun ? durum.yerel : { yazma: 0, okuma: 0 };
  const yazma = g.yazma + y.yazma, okuma = g.okuma + y.okuma;
  const yk = yazmaKademesi(yazma, s.yazma), ok = okumaKademesi(okuma, s.okuma);
  return { gun, yazma, okuma, sinirYazma: s.yazma, sinirOkuma: s.okuma, yazmaKademesi: yk, okumaKademesi: ok, yazmaAd: YAZMA_ADLARI[yk], okumaAd: OKUMA_ADLARI[ok] };
}

export async function butceDurumu(env, simdiMs = saat()) {
  await butceHazirla(env, simdiMs);
  return butceOku(env, simdiMs);
}

// Kademeye göre olay süzgeci.
export function olaylariSuz(olaylar, kademe) {
  if (kademe <= 0) return olaylar;
  if (kademe === 1) return olaylar.filter((e) => !KADEME1_ATILAN.has(e.t));
  if (kademe === 2) return olaylar.filter((e) => e.t === 'sayfa' || (e.t === 'tikla' && KADEME2_TIKLA.has(e.a)));
  return [];
}

// Panelde "veri azaltıldı" notu düşülecek ölçümler.
export function azaltilanOlcumler(kademe) {
  if (kademe <= 0) return [];
  const k1 = ['etkin süre', 'kaydırma derinliği', 'sayfa hızı (LCP/TTFB)'];
  if (kademe === 1) return k1;
  if (kademe === 2) return [...k1, 'hata ve 404 kayıtları', 'diğer tıklamalar (filtre, kategori, kaydet, manşet...)'];
  return [...k1, 'tüm yeni olaylar (toplama durdu)'];
}

export function butceOzeti(b) {
  return {
    gun: b.gun, yazma: b.yazma, okuma: b.okuma, sinirYazma: b.sinirYazma, sinirOkuma: b.sinirOkuma,
    yazmaKademesi: b.yazmaKademesi, yazmaAd: b.yazmaAd, okumaKademesi: b.okumaKademesi, okumaAd: b.okumaAd,
    azaltilan: azaltilanOlcumler(b.yazmaKademesi),
    veriAzaltildi: b.yazmaKademesi > 0,
  };
}
