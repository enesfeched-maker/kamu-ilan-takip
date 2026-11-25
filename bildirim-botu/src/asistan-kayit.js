// Asistan kaydı: sorulan sorular, verilen cevaplar ve "işine yaradı mı" geri bildirimi (D1, tablo asistan_kayit).
// Kimlik bilgisi (IP, user agent) hiçbir zaman saklanmaz; soru metnindeki e-posta/telefon/kimlik no kayıttan önce gizlenir.
// Kayıt asla cevabı bozmaz: her hata yutulur, kid null döner. D1 bütçesi bota da ait olduğu için günlük üst sınır vardır.

export const GUNLUK_SINIR = 3000;
export const SAKLAMA_GUN = 120;
const SAYAC_KONTROL_MS = 10 * 60 * 1000;
const GERI_PENCERE_MS = 24 * 60 * 60 * 1000;
export const DURUMLAR = ['yanitlandi', 'atlandi', 'hata'];

export const SQL = {
  tablo: 'CREATE TABLE IF NOT EXISTS asistan_kayit (id INTEGER PRIMARY KEY AUTOINCREMENT, zaman TEXT NOT NULL, kanal TEXT NOT NULL, soru TEXT NOT NULL, '
    + 'tur TEXT, metin TEXT, ilan_sayisi INTEGER DEFAULT 0, baglantilar TEXT, sayfa TEXT, geri INTEGER, durum TEXT, gonderilen TEXT, meta TEXT)',
  indeks: 'CREATE INDEX IF NOT EXISTS asistan_kayit_zaman ON asistan_kayit (zaman)',
  say: 'SELECT COUNT(*) AS n FROM asistan_kayit WHERE zaman >= ?',
  ekle: 'INSERT INTO asistan_kayit (zaman, kanal, soru, tur, metin, ilan_sayisi, baglantilar, sayfa, meta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
  geri: "UPDATE asistan_kayit SET geri = ? WHERE id = ? AND kanal = 'site' AND zaman >= ?",
  durum: 'UPDATE asistan_kayit SET durum = ?, gonderilen = ? WHERE id = ?',
  liste: 'SELECT id, zaman, kanal, soru, tur, metin, ilan_sayisi, baglantilar, sayfa, geri, durum, gonderilen, meta FROM asistan_kayit WHERE id > ? ORDER BY id ASC LIMIT ?',
  sil: 'DELETE FROM asistan_kayit WHERE zaman < ?',
};

// ---------------------------------------------------------------- yetki

// Sabit süreli karşılaştırma (uzunluk farkında da tüm baytlar dolaşılır).
export function esit(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a)), y = enc.encode(String(b));
  let fark = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) fark |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return fark === 0;
}

// 'yok' (gizli ayar tanımsız: yetkili uçlar 503), 'gecerli' ya da 'gecersiz'.
export function yetkiDurumu(request, env) {
  if (!env || !env.ASISTAN_ANAHTAR) return 'yok';
  const k = request.headers.get('X-Asistan-Anahtar');
  return k && esit(k, env.ASISTAN_ANAHTAR) ? 'gecerli' : 'gecersiz';
}

// ---------------------------------------------------------------- gizleme

const EPOSTA = /[^\s@<>()"',;:]+@[^\s@<>()"',;]+\.[A-Za-z]{2,}/g;
const SAYI_DIZISI = /(?<!\d)\+?\(?\d[\d\s().-]{7,20}\d(?!\d)/g;

export function gizle(metin) {
  let s = String(metin ?? '').replace(EPOSTA, '[e-posta]');
  s = s.replace(SAYI_DIZISI, (m) => {
    const r = m.replace(/\D/g, '');
    if (r.length === 11 && r[0] !== '0') return '[kimlik no]';
    if ((r.length === 10 && '2345'.includes(r[0])) || (r.length === 11 && r[0] === '0') || (r.length === 12 && r.startsWith('90'))) return '[telefon]';
    return m;
  });
  return s;
}

// ---------------------------------------------------------------- tablo, sınır

const durum = { tabloHazir: false, sayacGun: '', sayacN: 0, sayacKontrol: 0, temizlikGun: '' };

export function kayitSifirla() {
  durum.tabloHazir = false;
  durum.sayacGun = '';
  durum.sayacN = 0;
  durum.sayacKontrol = 0;
  durum.temizlikGun = '';
}

async function tabloHazirla(env) {
  if (durum.tabloHazir) return;
  await env.DB.prepare(SQL.tablo).run();
  await env.DB.prepare(SQL.indeks).run();
  durum.tabloHazir = true;
}

const gunBasi = (simdi) => `${new Date(simdi).toISOString().slice(0, 10)}T00:00:00.000Z`;

// Günlük sayaç bellekte tutulur; D1'e en çok 10 dakikada bir (isolate başına) COUNT sorulur.
async function sinirAsildi(env, simdi) {
  const gun = new Date(simdi).toISOString().slice(0, 10);
  if (durum.sayacGun !== gun) { durum.sayacGun = gun; durum.sayacN = 0; durum.sayacKontrol = 0; }
  if (simdi - durum.sayacKontrol >= SAYAC_KONTROL_MS) {
    durum.sayacKontrol = simdi;
    const r = await env.DB.prepare(SQL.say).bind(gunBasi(simdi)).first();
    durum.sayacN = Math.max(durum.sayacN, Number(r?.n) || 0);
  }
  return durum.sayacN >= GUNLUK_SINIR;
}

const kisalt = (s, n) => String(s ?? '').slice(0, n);

function metaTemizle(meta) {
  if (!meta || typeof meta !== 'object' || Array.isArray(meta)) return null;
  const o = {};
  for (const k of ['kullanici', 'medya', 'yorum_id']) if (meta[k] !== undefined && meta[k] !== null) o[k] = kisalt(meta[k], 100);
  return Object.keys(o).length ? JSON.stringify(o) : null;
}

// Kayıt yazar, satır kimliğini döner; sınır aşıldıysa ya da herhangi bir hata olursa null (cevabı asla bozmaz).
export async function kayitEkle(env, { kanal, soru, cevap, sayfa, meta }, simdi = Date.now()) {
  try {
    if (!env || !env.DB) return null;
    await tabloHazirla(env);
    if (await sinirAsildi(env, simdi)) return null;
    const baglantilar = (cevap.baglantilar || []).map((b) => b.url).filter(Boolean);
    const r = await env.DB.prepare(SQL.ekle).bind(
      new Date(simdi).toISOString(), kanal === 'instagram' ? 'instagram' : 'site', gizle(soru), cevap.tur || null, kisalt(cevap.metin, 1500),
      (cevap.ilanlar || []).length, JSON.stringify(baglantilar), kisalt(sayfa, 200) || null, metaTemizle(meta),
    ).run();
    durum.sayacN++;
    const id = r?.meta?.last_row_id;
    return Number.isInteger(id) && id > 0 ? id : null;
  } catch {
    durum.tabloHazir = false; // tablo silindiyse/erişilemediyse sonraki istek yeniden dener
    return null;
  }
}

export async function geriYaz(env, kid, deger, simdi = Date.now()) {
  await tabloHazirla(env);
  const r = await env.DB.prepare(SQL.geri).bind(deger, kid, new Date(simdi - GERI_PENCERE_MS).toISOString()).run();
  return (r?.meta?.changes ?? 0) > 0;
}

export async function durumYaz(env, kid, d, gonderilen) {
  await tabloHazirla(env);
  const r = await env.DB.prepare(SQL.durum).bind(d, gonderilen ? kisalt(gonderilen, 1000) : null, kid).run();
  return (r?.meta?.changes ?? 0) > 0;
}

const jsonAyir = (s, yedek) => { try { return s ? JSON.parse(s) : yedek; } catch { return yedek; } };

export async function kayitlariListele(env, sonra, limit) {
  await tabloHazirla(env);
  const r = await env.DB.prepare(SQL.liste).bind(sonra, limit).all();
  const kayitlar = (r.results || []).map((k) => ({ ...k, baglantilar: jsonAyir(k.baglantilar, []), meta: jsonAyir(k.meta, null) }));
  return { kayitlar, son: kayitlar.length ? kayitlar[kayitlar.length - 1].id : sonra };
}

// Günde bir kez (bellekte gün bekçisi): 120 günden eski satırları siler. Hata yutulur.
export async function eskiKayitlariSil(env, simdi = Date.now()) {
  try {
    if (!env || !env.DB) return false;
    const gun = new Date(simdi).toISOString().slice(0, 10);
    if (durum.temizlikGun === gun) return false;
    durum.temizlikGun = gun;
    await tabloHazirla(env);
    await env.DB.prepare(SQL.sil).bind(new Date(simdi - SAKLAMA_GUN * 86400000).toISOString()).run();
    return true;
  } catch {
    return false;
  }
}
