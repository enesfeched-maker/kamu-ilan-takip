// Profil kartı: avatar, fotoğraf, hakkımda, hedef, durum, kart rengi, gizlilik; rozetler; hesaba bağlı katiplik verisi; başvurdum işaretleri.
// index.js ile döngüsel içe aktarma güvenlidir: yardımcılar yalnız istek sırasında çağrılır (kayit.js ile aynı düzen).
// D1 yazma kotası hesap genelindedir: her kayıt tek UPDATE'tir, değişmediyse satır yazılmaz; fotoğraflar uçta (caches.default) 1 yıl önbelleklenir.
import { jsonYanit, hataYanit, simdi, avCikti } from './yardimci.js';
import { temizle } from './denetim.js';
import { ipSiniri, cokDeneme } from './hiz.js';
import { profilOku } from './profil.js';
import { kayitliOku, kayitliTemizle } from './kayitli.js';
import { kabaSinir } from './kayit.js';
import { oturumUyesi, yazar, yoneticiMi, uyeRumuzla, metinDenetle, govdeOku, negatifsizTamsayi } from './index.js';

export const DURUMLAR = ['tercih-yapacagim', 'basvuru-yapiyorum', 'basvurdum', 'yerlestim', 'atandim', 'calisiyorum'];
export const KART_RENKLERI = ['yesil', 'mavi', 'mor', 'pembe', 'turuncu', 'sari', 'turkuaz', 'gri'];
// Puan, il ve katiplik sonuçları varsayılan olarak GİZLİ (üye düzenleyicide "görünür olsun" demedikçe). Varsayılanlar saklanmadığı için kartını hiç
// kaydetmemiş (ya da bu alanları değiştirmemiş) üyeler de gizli görünür.
export const GIZLILIK_VARSAYILAN = { profil: 'herkes', puan_goster: false, il_goster: false, katiplik_goster: false };
const PROFIL_GORUNURLUK = new Set(['herkes', 'uyeler', 'gizli']);
const AV_ANAHTAR = /^[a-z0-9-]{1,24}$/;
const AV_RENK = /^[a-z-]{1,16}$/;
// Piixpal avatarları (docs/avatar/piixpal.js ile aynı izin listeleri): "px.<anahtar>:<biçim>.<ton>"
export const PX_ADLAR = new Set(['loaf', 'hops', 'mumu', 'fluff', 'llama', 'elephant', 'whale', 'dragon', 'inky', 'unicorn', 'coffee', 'keycap', 'inbox', 'floppy', 'battery', 'candle', 'prompty', 'heart',
  'cactus', 'cloud', 'star', 'planet', 'flick', 'astronaut', 'wizard', 'robo', 'ufo', 'alien', 'gloop', 'bolt', 'boba', 'cookie', 'mochi', 'avocado', 'donut', 'sushi', 'onigiri', 'toast', 'pudding',
  'cherries', 'egg', 'spud', 'tofu', 'gpu', 'server', 'modem', 'token', 'crt', 'brain']);
export const PX_BICIMLER = new Set(['pixel', 'dots', 'halftone', 'voxel']);
export const PX_TONLAR = new Set([0, 45, 90, 135, 180, 225, 270, 315]);
const PX_DEGER = /^px\.([a-z]{2,10}):([a-z]{3,10})\.(\d{1,3})$/;
export const HAKKIMDA_EN_COK = 160;
export const HEDEF_EN_COK = 60;
export const FOTO_EN_COK = 24 * 1024;
export const FOTO_GUNLUK = 3;
export const FOTO_YAS_SN = 86400;
export const KATIP_EN_COK = 32 * 1024;
export const BASVURULAR_EN_COK = 300;
const GUN = 86400;
const DERS_TOPLAM = 16;   // docs/katiplik/dersler: klavye ders sayısı
const tekSatir = (s) => temizle(s).replace(/\s+/g, ' ');

// ---------- kart alanları ----------
export function gizlilikTamamla(g) {
  const o = g && typeof g === 'object' && !Array.isArray(g) ? g : {};
  return {
    profil: PROFIL_GORUNURLUK.has(o.profil) ? o.profil : GIZLILIK_VARSAYILAN.profil,
    puan_goster: typeof o.puan_goster === 'boolean' ? o.puan_goster : GIZLILIK_VARSAYILAN.puan_goster,
    il_goster: typeof o.il_goster === 'boolean' ? o.il_goster : GIZLILIK_VARSAYILAN.il_goster,
    katiplik_goster: typeof o.katiplik_goster === 'boolean' ? o.katiplik_goster : GIZLILIK_VARSAYILAN.katiplik_goster,
  };
}
// Kayıtlı kart JSON'u (varsayılanlar yazılmamıştır) tam nesneye çevirir; bozuksa boş kart.
export function kartOku(metin) {
  let o = null;
  try { o = metin ? JSON.parse(metin) : null; } catch { o = null; }
  if (!o || typeof o !== 'object' || Array.isArray(o)) o = {};
  return {
    hakkimda: typeof o.hakkimda === 'string' ? o.hakkimda.slice(0, HAKKIMDA_EN_COK) : '',
    hedef: typeof o.hedef === 'string' ? o.hedef.slice(0, HEDEF_EN_COK) : '',
    durum: DURUMLAR.includes(o.durum) ? o.durum : null,
    kart_rengi: KART_RENKLERI.includes(o.kart_rengi) ? o.kart_rengi : null,
    gizlilik: gizlilikTamamla(o.gizlilik),
  };
}
// Depolanacak sıkıştırılmış JSON (boş ve varsayılan alanlar yazılmaz); hiç alan kalmazsa null.
export function kartSakla(k) {
  const o = {};
  if (k.hakkimda) o.hakkimda = k.hakkimda;
  if (k.hedef) o.hedef = k.hedef;
  if (k.durum) o.durum = k.durum;
  if (k.kart_rengi) o.kart_rengi = k.kart_rengi;
  const g = {};
  for (const ad of Object.keys(GIZLILIK_VARSAYILAN)) if (k.gizlilik[ad] !== GIZLILIK_VARSAYILAN[ad]) g[ad] = k.gizlilik[ad];
  if (Object.keys(g).length) o.gizlilik = g;
  return Object.keys(o).length ? JSON.stringify(o) : null;
}
// Avatar değeri: null | 'foto' | "anahtar:renk" | { k, r }. Geçerliyse { avatar } (null olabilir), değilse { hata }.
export function avatarTemizle(v, fotoVar) {
  if (v === undefined || v === null || v === '') return { avatar: null };
  if (v === 'foto') return fotoVar ? { avatar: 'foto' } : { hata: 'Önce bir fotoğraf yüklemelisin.' };
  let k, r;
  if (typeof v === 'string' && v.startsWith('px.')) {   // Piixpal: izin listesi dışı her şey reddedilir
    const m = PX_DEGER.exec(v);
    return m && PX_ADLAR.has(m[1]) && PX_BICIMLER.has(m[2]) && PX_TONLAR.has(Number(m[3])) && String(Number(m[3])) === m[3] ? { avatar: v } : { hata: 'Avatar geçersiz.' };
  }
  if (v && typeof v === 'object' && !Array.isArray(v) && v.set === 'px') {
    const s = `px.${v.k}:${v.r || 'pixel'}.${v.renk ?? 0}`;
    return avatarTemizle(s, fotoVar);
  }
  if (typeof v === 'string') [k, r] = v.split(':');
  else if (v && typeof v === 'object' && !Array.isArray(v)) { k = v.k; r = v.renk ?? v.r; }
  if (typeof k !== 'string' || !AV_ANAHTAR.test(k) || typeof r !== 'string' || !AV_RENK.test(r)) return { hata: 'Avatar geçersiz.' };
  return { avatar: `${k}:${r}` };
}
// Kullanıcının gönderdiği kartı doğrular (tam değiştirme). { hata } ya da { avatar, kart }.
export function kartTemizle(g, fotoVar) {
  const a = avatarTemizle(g.avatar, fotoVar);
  if (a.hata) return { hata: hataYanit(400, a.hata) };
  let durum = null;
  if (g.durum !== undefined && g.durum !== null && g.durum !== '') {
    if (typeof g.durum !== 'string' || !DURUMLAR.includes(g.durum)) return { hata: hataYanit(400, 'Durum geçersiz.') };
    durum = g.durum;
  }
  let renk = null;
  if (g.kart_rengi !== undefined && g.kart_rengi !== null && g.kart_rengi !== '') {
    if (typeof g.kart_rengi !== 'string' || !KART_RENKLERI.includes(g.kart_rengi)) return { hata: hataYanit(400, 'Kart rengi geçersiz.') };
    renk = g.kart_rengi;
  }
  const gz = g.gizlilik;
  if (gz !== undefined && gz !== null) {
    if (typeof gz !== 'object' || Array.isArray(gz)) return { hata: hataYanit(400, 'Gizlilik ayarı geçersiz.') };
    if (gz.profil !== undefined && !PROFIL_GORUNURLUK.has(gz.profil)) return { hata: hataYanit(400, 'Profil görünürlüğü geçersiz.') };
    for (const ad of ['puan_goster', 'il_goster', 'katiplik_goster']) if (gz[ad] !== undefined && typeof gz[ad] !== 'boolean') return { hata: hataYanit(400, `${ad} true/false olmalı.`) };
  }
  const metinler = {};
  for (const [ad, en] of [['hakkimda', HAKKIMDA_EN_COK], ['hedef', HEDEF_EN_COK]]) {
    const ham = g[ad];
    if (ham === undefined || ham === null || ham === '') { metinler[ad] = ''; continue; }
    if (typeof ham !== 'string') return { hata: hataYanit(400, `${ad} metin olmalı.`) };
    const t = tekSatir(ham);
    if (!t) { metinler[ad] = ''; continue; }
    const d = metinDenetle(t, 1, en, ad === 'hakkimda' ? 'Hakkımda' : 'Hedef');
    if (d.hata) return d;
    metinler[ad] = d.temiz;
  }
  return { avatar: a.avatar, kart: { hakkimda: metinler.hakkimda, hedef: metinler.hedef, durum, kart_rengi: renk, gizlilik: gizlilikTamamla(gz) } };
}
// /ben ve kendi kartı için tam çıktı.
export function kartCikti(s) {
  return { avatar: s.avatar || null, foto_surum: s.foto_surum || null, ...kartOku(s.kart) };
}

// ---------- POST /ben/kart ----------
export async function benKartKaydet(request, env) {
  const { ret: kaba } = await kabaSinir(request, 'kart', 30);
  if (kaba) return kaba;
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  if (!ipSiniri(`kart-uye:${uye.id}`, simdi(), 10, 60)) return cokDeneme();   // üye başına dakikada 10 kayıt
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const s = kartTemizle(g, !!uye.foto_surum);
  if (s.hata) return s.hata;
  const m = kartSakla(s.kart);
  await env.DB.prepare('UPDATE uyeler SET avatar = ?, kart = ? WHERE id = ? AND (avatar IS NOT ? OR kart IS NOT ?)').bind(s.avatar, m, uye.id, s.avatar, m).run();   // değişmediyse yazma yok
  return jsonYanit({ kart: kartCikti({ avatar: s.avatar, foto_surum: uye.foto_surum, kart: m }) });
}

// ---------- /ben: tek okumada profil, kayıtlı ilanlar, kart ve başvurular ----------
export async function benTumu(env, uyeId) {
  const s = await env.DB.prepare('SELECT profil, kayitli, avatar, foto_surum, kart, basvurular FROM uyeler WHERE id = ?').bind(uyeId).first();
  return { profil: profilOku(s && s.profil), kayitli: kayitliOku(s && s.kayitli), kart: kartCikti(s || {}), basvurular: kayitliOku(s && s.basvurular) };
}

// ---------- POST /ben/basvurular ----------
export async function benBasvurularKaydet(request, env) {
  const { ret: kaba } = await kabaSinir(request, 'basvurular', 30);
  if (kaba) return kaba;
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  if (!ipSiniri(`basvurular-uye:${u.id}`, simdi(), 10, 60)) return cokDeneme();
  const g = await govdeOku(request);
  if (!g || !Array.isArray(g.basvurular)) return hataYanit(400, 'Geçersiz istek.');
  const k = kayitliTemizle(g.basvurular);
  if (!k) return hataYanit(400, 'Başvuru listesi geçersiz ya da çok büyük.');
  if (!k.length) {
    await env.DB.prepare('UPDATE uyeler SET basvurular = NULL WHERE id = ? AND basvurular IS NOT NULL').bind(u.id).run();
    return jsonYanit({ basvurular: [] });
  }
  const m = JSON.stringify(k);
  await env.DB.prepare('UPDATE uyeler SET basvurular = ? WHERE id = ? AND basvurular IS NOT ?').bind(m, u.id, m).run();
  return jsonYanit({ basvurular: k });
}

// ---------- fotoğraf ----------
// Sihirli baytlar: WebP (RIFF....WEBP), JPEG (FF D8 FF), PNG. Başka her şey reddedilir.
export function fotoTuru(b) {
  if (!b || b.length < 12) return null;
  const ascii = (i, n) => String.fromCharCode(...b.slice(i, i + n));
  if (ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WEBP') return 'image/webp';
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (b[0] === 0x89 && ascii(1, 3) === 'PNG' && b[4] === 0x0d && b[5] === 0x0a && b[6] === 0x1a && b[7] === 0x0a) return 'image/png';
  return null;
}
// Gövdeyi en çok `en_cok` bayta kadar okur; aşarsa null (Content-Length yalan söylese de bellek şişmez).
async function sinirliOku(request, en_cok) {
  if (!request.body) return new Uint8Array(0);
  const okuyucu = request.body.getReader();
  const parcalar = [];
  let n = 0;
  for (;;) {
    const { done, value } = await okuyucu.read();
    if (done) break;
    n += value.length;
    if (n > en_cok) { try { await okuyucu.cancel(); } catch { /* yoksay */ } return null; }
    parcalar.push(value);
  }
  const b = new Uint8Array(n);
  let i = 0;
  for (const p of parcalar) { b.set(p, i); i += p.length; }
  return b;
}
export function baytlar(v) {   // D1 BLOB'u Uint8Array, ArrayBuffer ya da sayı dizisi olarak döndürebilir
  if (!v) return null;
  if (v instanceof Uint8Array) return v;
  if (v instanceof ArrayBuffer) return new Uint8Array(v);
  if (Array.isArray(v)) return Uint8Array.from(v);
  return null;
}
const fotoAdresi = (id, v) => `/foto/${id}?v=${v}`;

// POST /ben/foto: gövde ham görüntü baytlarıdır (istemci canvas'ta 160x160 WebP/JPEG üretir).
export async function benFotoYukle(request, env) {
  const { ret: kaba } = await kabaSinir(request, 'foto', 20);
  if (kaba) return kaba;
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const t = simdi();
  if (uye.foto_yasak) return hataYanit(403, 'Fotoğraf yükleme hesabın için kapatıldı. Hazır avatarlardan seçebilirsin.');
  if (!uye.kayit || t - uye.kayit < FOTO_YAS_SN) return hataYanit(403, 'Fotoğraf yüklemek için hesabın en az 24 saatlik olmalı. O zamana kadar hazır avatarlardan seçebilirsin.');
  if (!ipSiniri(`foto-uye:${uye.id}`, t, 6, 60)) return cokDeneme();
  if (Number(request.headers.get('Content-Length') || 0) > FOTO_EN_COK) return hataYanit(413, 'Fotoğraf en çok 24 KB olabilir.');
  const gun = Math.floor(t / GUN);
  const sayi = uye.foto_gun === gun ? uye.foto_sayi || 0 : 0;
  if (sayi >= FOTO_GUNLUK) return hataYanit(429, `Bir günde en çok ${FOTO_GUNLUK} fotoğraf yükleyebilirsin. Yarın tekrar dene.`);
  const b = await sinirliOku(request, FOTO_EN_COK);
  if (b === null) return hataYanit(413, 'Fotoğraf en çok 24 KB olabilir.');
  if (!b.length) return hataYanit(400, 'Fotoğraf boş.');
  const tur = fotoTuru(b);
  if (!tur) return hataYanit(415, 'Yalnız WebP, JPEG ya da PNG fotoğraf yüklenebilir.');
  const surum = Math.max(t, (uye.foto_surum || 0) + 1);
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO fotolar (uye_id, veri, tur, surum, guncelleme) VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(uye_id) DO UPDATE SET veri = excluded.veri, tur = excluded.tur, surum = excluded.surum, guncelleme = excluded.guncelleme`,
    ).bind(uye.id, b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), tur, surum, t),
    env.DB.prepare("UPDATE uyeler SET foto_surum = ?, avatar = 'foto', foto_gun = ?, foto_sayi = ? WHERE id = ?").bind(surum, gun, sayi + 1, uye.id),
  ]);
  return jsonYanit({ foto_surum: surum, avatar: 'foto', kalan: FOTO_GUNLUK - sayi - 1 }, 201);
}
// DELETE /ben/foto: fotoğrafı kaldırır, avatar 'foto' ise varsayılana döner. Fotoğraf yoksa yazma yok.
export async function benFotoSil(request, env) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  if (!uye.foto_surum) return jsonYanit({ tamam: true });
  await env.DB.batch([
    env.DB.prepare('DELETE FROM fotolar WHERE uye_id = ?').bind(uye.id),
    env.DB.prepare("UPDATE uyeler SET foto_surum = NULL, avatar = CASE WHEN avatar = 'foto' THEN NULL ELSE avatar END WHERE id = ?").bind(uye.id),
  ]);
  await ucOnbellektenSil(new URL(request.url), uye.id, uye.foto_surum);
  return jsonYanit({ tamam: true, avatar: uye.avatar === 'foto' ? null : uye.avatar || null });
}
const ucOnbellek = () => (typeof caches !== 'undefined' ? caches.default : null);
// GET /foto/:uye_id?v=<surum>. Sürüm eşleşirse 1 yıl değişmez önbellek (tarayıcı + uç); eşleşmezse güncel görüntü kısa süre.
export async function fotoGetir(request, env, ctx, url, id) {
  const uyeId = negatifsizTamsayi(id);
  if (!uyeId) return hataYanit(404, 'Bulunamadı.');
  const v = negatifsizTamsayi(url.searchParams.get('v') || '');
  const c = ucOnbellek();
  const anahtar = v ? new Request(`${url.origin}/foto/${uyeId}?v=${v}`) : null;
  if (c && anahtar) { const var_ = await c.match(anahtar); if (var_) return var_; }
  const r = await env.DB.prepare('SELECT veri, tur, surum FROM fotolar WHERE uye_id = ?').bind(uyeId).first();
  const b = r && baytlar(r.veri);
  if (!b || !b.length) return hataYanit(404, 'Fotoğraf yok.');
  const eslesti = v !== null && Number(r.surum) === v;
  const yanit = new Response(b, {
    status: 200,
    headers: {
      'Content-Type': r.tur, 'X-Content-Type-Options': 'nosniff', 'Cross-Origin-Resource-Policy': 'cross-origin',
      'Content-Security-Policy': "default-src 'none'; sandbox",   // görüntü doğrudan açılsa da içindeki hiçbir şey çalışmaz
      'Cache-Control': eslesti ? 'public, max-age=31536000, immutable' : 'public, max-age=300',
    },
  });
  if (c && anahtar && eslesti) {
    // uç önbellekte en çok 1 gün: yönetici kaldırdığında silme yalnız bu ucu temizler, diğer uçlardaki kopya en geç 1 günde düşer
    const kopya = new Response(b, { status: 200, headers: { ...Object.fromEntries(yanit.headers), 'Cache-Control': 'public, max-age=86400' } });
    const p = Promise.resolve(c.put(anahtar, kopya)).catch(() => {});
    if (ctx && ctx.waitUntil) ctx.waitUntil(p);
  }
  return yanit;
}
async function ucOnbellektenSil(url, uyeId, surum) {
  const c = ucOnbellek();
  if (!c || !surum) return;
  try { await c.delete(new Request(`${url.origin}/foto/${uyeId}?v=${surum}`)); } catch { /* en iyi çaba (yalnız bu uç) */ }
}

// POST /uye/:rumuz/foto-bildir
export async function fotoBildir(request, env, ham) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  if (!ipSiniri(`foto-bildir:${uye.id}`, simdi(), 10, 60)) return cokDeneme();
  const o = await uyeRumuzla(env, ham);
  if (!o || o.engelli) return hataYanit(404, 'Üye bulunamadı.');
  if (o.id === uye.id) return hataYanit(400, 'Kendi fotoğrafını bildiremezsin.');
  if (!o.foto_surum) return hataYanit(404, 'Bu üyenin fotoğrafı yok.');
  const r = await env.DB.prepare(
    `INSERT INTO foto_bildirimleri (uye_id, bildiren, surum, olusma) VALUES (?, ?, ?, ?)
     ON CONFLICT(uye_id, bildiren) DO UPDATE SET surum = excluded.surum, olusma = excluded.olusma WHERE foto_bildirimleri.surum IS NOT excluded.surum`,
  ).bind(o.id, uye.id, o.foto_surum, simdi()).run();
  return jsonYanit({ tamam: true, zaten: r.meta.changes === 0 });
}
// GET /yonetim/foto-bildirimleri: yalnız güncel fotoğrafa gelen bildirimler, en çok bildirilen önce.
export async function yonetimFotoBildirimleri(request, env) {
  if (!yoneticiMi(request, env)) return hataHata401();
  const { results } = await env.DB.prepare(
    `SELECT u.id, u.rumuz, u.foto_surum, u.foto_yasak, COUNT(*) AS bildirim, MAX(b.olusma) AS son
     FROM foto_bildirimleri b JOIN uyeler u ON u.id = b.uye_id AND u.foto_surum = b.surum
     GROUP BY b.uye_id ORDER BY bildirim DESC, son DESC LIMIT 100`,
  ).all();
  return jsonYanit({ fotolar: results.map((r) => ({ uye_id: r.id, rumuz: r.rumuz, bildirim: r.bildirim, son: r.son, yasak: !!r.foto_yasak, foto: fotoAdresi(r.id, r.foto_surum) })) });
}
const hataHata401 = () => hataYanit(401, 'Yetkisiz.');
// POST /yonetim/foto-kaldir { uye_id | rumuz, yasak? }: fotoğrafı siler, avatarı varsayılana döndürür; yasak (varsayılan true) yeni yüklemeyi kapatır.
export async function yonetimFotoKaldir(request, env, url) {
  if (!yoneticiMi(request, env)) return hataHata401();
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  let u = null;
  if (Number.isInteger(g.uye_id)) u = await env.DB.prepare("SELECT id, foto_surum FROM uyeler WHERE id = ? AND rol NOT IN ('sistem', 'asistan')").bind(g.uye_id).first();
  else if (typeof g.rumuz === 'string') u = await uyeRumuzla(env, encodeURIComponent(g.rumuz));
  if (!u) return hataYanit(404, 'Üye bulunamadı.');
  const yasak = g.yasak === false ? 0 : 1;
  await env.DB.batch([
    env.DB.prepare('DELETE FROM fotolar WHERE uye_id = ?').bind(u.id),
    env.DB.prepare("UPDATE uyeler SET foto_surum = NULL, avatar = CASE WHEN avatar = 'foto' THEN NULL ELSE avatar END, foto_yasak = ? WHERE id = ?").bind(yasak, u.id),
    env.DB.prepare('DELETE FROM foto_bildirimleri WHERE uye_id = ?').bind(u.id),
  ]);
  await ucOnbellektenSil(url, u.id, u.foto_surum);
  return jsonYanit({ tamam: true, yasak: !!yasak });
}

// ---------- hesaba bağlı katiplik verisi ----------
const TAM = (v, en, cok) => (Number.isInteger(v) && v >= en && v <= cok ? v : null);
const TARIH = /^\d{4}-\d{2}-\d{2}$/;
const KISA = /^[a-z0-9]{1,12}$/;
const KELIME = /^[a-zçğıöşüâîû]{1,30}$/;
const obje = (v) => (v && typeof v === 'object' && !Array.isArray(v) ? v : null);

function gecmisTemizle(liste, en_cok) {
  const goru = new Set(), cikti = [];
  for (const x of Array.isArray(liste) ? liste.slice(0, en_cok * 2) : []) {
    const o = obje(x);
    if (!o) continue;
    const t = TAM(o.t, 1e12, 4e12);
    if (t === null || typeof o.m !== 'string' || !/^[a-z0-9]{1,12}$/.test(o.m)) continue;
    const anahtar = `${t}:${o.m}`;
    if (goru.has(anahtar)) continue;
    goru.add(anahtar);
    const e = { t, m: o.m };
    for (const [ad, en, cok] of [['s', 0, 7200], ['top', 0, 9999], ['hat', 0, 9999], ['atl', 0, 9999], ['net', -9999, 9999], ['dk', -999, 9999], ['n', 0, 9999], ['h', 0, 9999], ['no', -1, 9999]]) {
      const v = TAM(o[ad], en, cok);
      if (v !== null) e[ad] = v;
    }
    if (o.b === 0 || o.b === 1) e.b = o.b;
    if (typeof o.k === 'string' && KISA.test(o.k)) e.k = o.k;
    cikti.push(e);
  }
  return cikti.sort((a, b) => b.t - a.t).slice(0, en_cok);
}
export function katipTemizle(girdi) {
  const k = obje(girdi);
  if (!k) return null;
  const kk = obje(k.k) || {}, d = obje(k.d) || {}, o = obje(k.o) || {}, a = obje(k.a) || {};
  const hatalar = {};
  const hl = Object.entries(obje(kk.hatalar) || {}).filter(([w, n]) => KELIME.test(w) && TAM(n, 1, 9999) !== null).sort((x, y) => y[1] - x[1]).slice(0, 100);
  for (const [w, n] of hl) hatalar[w] = n;
  const gunluk = {};
  const gk = Object.keys(obje(kk.gunluk) || {}).filter((g) => TARIH.test(g)).sort().slice(-120);
  for (const g of gk) {
    const e = obje(kk.gunluk[g]);
    if (!e) continue;
    const c = {};
    for (const [ad, en, cok] of [['net', -9999, 9999], ['top', 0, 9999], ['hat', 0, 9999]]) { const v = TAM(e[ad], en, cok); if (v !== null) c[ad] = v; }
    if (e.b === 0 || e.b === 1) c.b = e.b;
    gunluk[g] = c;
  }
  const yol = obje(kk.yol) || {};
  const ders = {};
  for (const duzen of ['Q', 'F']) {
    const dd = obje(d[duzen]);
    if (!dd) continue;
    const c = {};
    for (const [i, e] of Object.entries(dd).slice(0, 60)) {
      const n = Number(i), y = obje(e);
      if (!Number.isInteger(n) || n < 0 || n > 59 || !y || TAM(y.y, 1, 3) === null) continue;
      c[n] = { y: y.y, t: TAM(y.t, 1e12, 4e12) || 0 };
    }
    if (Object.keys(c).length) ders[duzen] = c;
  }
  const rekor = {};
  for (const [ad, v] of Object.entries(obje(a.rekor) || {}).slice(0, 12)) if (/^[a-z]{1,8}\d{0,4}$/.test(ad) && TAM(v, 0, 2000) !== null) rekor[ad] = v;
  const temiz = {
    v: 1,
    k: {
      gecmis: gecmisTemizle(kk.gecmis, 200), hatalar,
      rozetler: [...new Set((Array.isArray(kk.rozetler) ? kk.rozetler : []).filter((x) => typeof x === 'string' && /^[a-z0-9]{1,16}$/.test(x)))].slice(0, 40),
      gunluk,
      yol: { tarih: typeof yol.tarih === 'string' && (yol.tarih === '' || TARIH.test(yol.tarih)) ? yol.tarih : '', hedef: TAM(yol.hedef, 30, 250) || 90, g: TAM(yol.g, 0, 4e12) || 0 },
      ayar: { klavye: obje(kk.ayar) && kk.ayar.klavye === 'F' ? 'F' : 'Q' },
    },
    d: ders,
    o: { dosya: TAM(o.dosya, 0, 1e6) || 0, hata: TAM(o.hata, 0, 1e6) || 0 },
    a: { rekor, gecmis: gecmisTemizle(a.gecmis, 30) },
    z: TAM(k.z, 0, 4e12) || 0,   // "geçmişi sil" zamanı (ms); 0 = hiç sıfırlanmadı
  };
  if (temiz.z) temiz.k.gecmis = temiz.k.gecmis.filter((x) => x.t > temiz.z);
  // en eski geçmiş kayıtları düşerek 32 KB'a sığdır (istemci de aynısını yapar)
  while (JSON.stringify(temiz).length > KATIP_EN_COK && temiz.k.gecmis.length > 20) temiz.k.gecmis.pop();
  return JSON.stringify(temiz).length <= KATIP_EN_COK ? temiz : null;
}
// Hesaptaki veri ile gelen veriyi birleştirir (iki cihaz birbirinin sonucunu ezmesin). Girdiler katipTemizle çıktısıdır; sonuç yeniden temizlenir.
// Kurallar docs/katip-senkron.js birlestir ile aynı: geçmiş zaman damgasıyla birleşir; en iyi değerlerin büyüğü; rozetler birleşir; günlük sonuçta
// net büyük olan; yolda yeni değişiklik (yol.g); ayarda gelen. Sıfırlama (z, "geçmişi sil" zamanı): büyük z kazanır, z'den eski geçmiş düşer;
// sıfırlamayı görmemiş tarafın hata ve rozetleri alınmaz, günlük sonuçlarından yalnız sıfırlama gününden sonrakiler kalır.
const trGunAnahtari = (ms) => new Date(ms + 3 * 3600 * 1000).toISOString().slice(0, 10);
export function katipBirlestir(eski, yeni) {
  if (!eski) return yeni;
  const z = Math.max(eski.z || 0, yeni.z || 0);
  const kes = (t) => {
    if ((t.z || 0) >= z) return t.k;
    const gun = trGunAnahtari(z), gunluk = {};
    for (const [g, e] of Object.entries(t.k.gunluk)) if (g > gun) gunluk[g] = e;
    return { ...t.k, hatalar: {}, rozetler: [], gunluk };
  };
  const ek = kes(eski), yk = kes(yeni);
  const hatalar = { ...ek.hatalar };
  for (const [w, n] of Object.entries(yk.hatalar)) hatalar[w] = Math.max(hatalar[w] || 0, n);
  const gunluk = { ...ek.gunluk };
  for (const [g, e] of Object.entries(yk.gunluk)) if (!gunluk[g] || (e.net || 0) >= (gunluk[g].net || 0)) gunluk[g] = e;
  const ders = {};
  for (const d of ['Q', 'F']) {
    const c = { ...(eski.d[d] || {}) };
    for (const [i, y] of Object.entries(yeni.d[d] || {})) { const p = c[i]; if (!p || y.y > p.y || (y.y === p.y && y.t >= p.t)) c[i] = y; }
    if (Object.keys(c).length) ders[d] = c;
  }
  const rekor = { ...eski.a.rekor };
  for (const [ad, v] of Object.entries(yeni.a.rekor)) rekor[ad] = Math.max(rekor[ad] || 0, v);
  return katipTemizle({   // tekrarları atar, sıralar, sınırlara (200 geçmiş, 100 hata, 120 gün, 32 KB) indirir
    v: 1,
    k: {
      gecmis: [...yk.gecmis, ...ek.gecmis], hatalar, rozetler: [...new Set([...yk.rozetler, ...ek.rozetler])], gunluk,
      yol: (yk.yol.g || 0) >= (ek.yol.g || 0) ? yk.yol : ek.yol, ayar: yk.ayar,
    },
    d: ders,
    o: { dosya: Math.max(eski.o.dosya, yeni.o.dosya), hata: Math.max(eski.o.hata, yeni.o.hata) },
    a: { rekor, gecmis: [...yeni.a.gecmis, ...eski.a.gecmis] },
    z,
  });
}
const trGun = (ms) => Math.floor((ms + 3 * 3600 * 1000) / 86400000);   // Türkiye günü numarası
export function katipOzeti(t, simdiSn) {
  const sinav = t.k.gecmis.filter((x) => x.m === 'sinav' || x.m === 'gunluk');
  const en = (ad) => sinav.reduce((m, x) => (typeof x[ad] === 'number' && x[ad] > m ? x[ad] : m), 0);
  const gunler = new Set(t.k.gecmis.map((x) => trGun(x.t)));
  let g = trGun(simdiSn * 1000);
  if (!gunler.has(g)) g -= 1;
  const son = g;
  let seri = 0;
  while (gunler.has(g)) { seri++; g--; }
  const ders = Math.max(0, ...['Q', 'F'].map((d) => Object.keys(t.d[d] || {}).length));
  return { net: en('net'), dk: en('dk'), ders: Math.min(ders, DERS_TOPLAM), seri, sg: seri ? son : 0, s30: t.k.rozetler.includes('seri30') ? 1 : 0 };
}
export function ozetOku(metin, simdiSn) {
  let o = null;
  try { o = metin ? JSON.parse(metin) : null; } catch { o = null; }
  if (!o || typeof o !== 'object') return null;
  const bugun = trGun(simdiSn * 1000);
  return { net: o.net || 0, dk: o.dk || 0, ders: o.ders || 0, seri: o.sg >= bugun - 1 ? o.seri || 0 : 0, s30: o.s30 ? 1 : 0 };
}
async function buyukGovde(request, en_cok) {
  if (Number(request.headers.get('Content-Length') || 0) > en_cok * 2) return null;
  const b = await sinirliOku(request, en_cok * 2);
  if (!b) return null;
  try { const j = JSON.parse(new TextDecoder().decode(b)); return obje(j); } catch { return null; }
}
export async function benKatipGetir(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  const r = await env.DB.prepare('SELECT veri FROM uye_katip WHERE uye_id = ?').bind(u.id).first();
  let katip = null;
  try { katip = r && r.veri ? JSON.parse(r.veri) : null; } catch { katip = null; }
  return jsonYanit({ katip });
}
export async function benKatipKaydet(request, env) {
  const { ret: kaba } = await kabaSinir(request, 'katip', 30);
  if (kaba) return kaba;
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  if (u.engelli) return hataYanit(403, 'Hesabın yazmaya kapatıldı.');
  if (!ipSiniri(`katip-uye:${u.id}`, simdi(), 10, 60)) return cokDeneme();   // üye başına dakikada 10 kayıt
  const g = await buyukGovde(request, KATIP_EN_COK);
  if (!g) return hataYanit(413, 'Katiplik verisi çok büyük ya da geçersiz.');
  const gelen = katipTemizle(g.katip);
  if (!gelen) return hataYanit(400, 'Katiplik verisi geçersiz ya da çok büyük.');
  // tam değiştirme değil birleştirme: başka cihazın gönderdiği sonuçlar silinmez (silme yalnız z ile, bkz. katipBirlestir)
  const r = await env.DB.prepare('SELECT veri FROM uye_katip WHERE uye_id = ?').bind(u.id).first();
  let eski = null;
  try { eski = r && r.veri ? katipTemizle(JSON.parse(r.veri)) : null; } catch { eski = null; }
  const t = katipBirlestir(eski, gelen) || gelen;
  const veri = JSON.stringify(t), ozet = JSON.stringify(katipOzeti(t, simdi()));
  await env.DB.prepare(
    `INSERT INTO uye_katip (uye_id, veri, ozet, guncelleme) VALUES (?, ?, ?, ?)
     ON CONFLICT(uye_id) DO UPDATE SET veri = excluded.veri, ozet = excluded.ozet, guncelleme = excluded.guncelleme WHERE uye_katip.veri IS NOT excluded.veri`,
  ).bind(u.id, veri, ozet, simdi()).run();   // değişmediyse yazma yok
  return jsonYanit({ katip: t });
}

// ---------- rozetler (okuma anında hesaplanır; dış sorgu yok, girdiler zaten okunmuş) ----------
// Önem sırası: en değerli önde. Kartta ilk 6, profil sayfasında hepsi. yerlestim / atandim kullanıcı beyanıdır.
export function rozetleriHesapla({ kurucu, soru = 0, cevap = 0, sohbet = 0, itibar = 0, katip = null, durum = null }) {
  const r = [];
  if (kurucu) r.push('kurucu');
  if (itibar >= 100) r.push('faydali-100'); else if (itibar >= 25) r.push('faydali-25'); else if (itibar >= 5) r.push('faydali-5');
  if (katip) {
    if (katip.dk >= 80) r.push('katip-hiz-80'); else if (katip.dk >= 60) r.push('katip-hiz-60'); else if (katip.dk >= 40) r.push('katip-hiz-40');
    if (katip.s30) r.push('katip-seri-30');
    if (katip.ders >= DERS_TOPLAM) r.push('ders-yildizi');
  }
  if (sohbet >= 100) r.push('sohbet-nesesi');
  if (cevap >= 1) r.push('ilk-cevap');
  if (soru >= 1) r.push('ilk-soru');
  if (durum === 'atandim') r.push('atandi'); else if (durum === 'yerlestim') r.push('yerlesti');
  return r;
}
export const BEYAN_ROZETLERI = ['yerlesti', 'atandi'];

// ---------- herkese açık üye kartı ----------
// Gizlilik: 'gizli' yalnız rumuz + avatar (+ mesaj izni); 'uyeler' girişsizlere aynı kısıtlı görünüm; kendi kartı her zaman tam.
// Yanıt anonim istekler için önbelleklenir (index.js onbellekli), bu yüzden girişsiz görünüm tek başına güvenli olmalıdır.
export async function uyeKartiYaniti(request, env, url, ham) {
  const u = await uyeRumuzla(env, ham);
  if (!u || u.engelli) return hataYanit(404, 'Üye bulunamadı.');
  const av = avCikti(u, u.id);
  const sistem = u.rol === 'sistem' || u.rol === 'asistan';
  const kart = kartOku(u.kart);
  let bakan = null;
  if (request.headers.get('Authorization')) bakan = await oturumUyesi(request, env);
  const kendisi = !!bakan && bakan.id === u.id;
  const gorunur = sistem || kendisi || kart.gizlilik.profil === 'herkes' || (kart.gizlilik.profil === 'uyeler' && !!bakan);
  if (!gorunur) {
    return jsonYanit({ rumuz: u.rumuz, rol: u.rol, dm_acik: u.dm_acik !== 0, kisitli: kart.gizlilik.profil === 'uyeler' ? 'uyeler' : 'gizli', ...av });
  }
  const say = await env.DB.prepare(
    `SELECT
       (SELECT COUNT(*) FROM yanitlar WHERE uye_id = ? AND gizli = 0) AS mesaj,
       (SELECT COUNT(*) FROM basliklar WHERE uye_id = ? AND gizli = 0 AND kategori <> 'oda') AS soru,
       (SELECT COUNT(*) FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id WHERE y.uye_id = ? AND y.gizli = 0 AND b.kategori = 'oda') AS sohbet`,
  ).bind(u.id, u.id, u.id).first();
  const son = await env.DB.prepare(
    `SELECT b.id, b.baslik, b.ilan_id FROM (SELECT baslik_id, MAX(id) AS son FROM yanitlar WHERE uye_id = ? AND gizli = 0 GROUP BY baslik_id ORDER BY son DESC LIMIT 20) t
     JOIN basliklar b ON b.id = t.baslik_id WHERE b.gizli = 0 ORDER BY t.son DESC LIMIT 5`,
  ).bind(u.id).all();
  const mesaj = say?.mesaj || 0, soru = say?.soru || 0, sohbet = say?.sohbet || 0;
  const o = {
    rumuz: u.rumuz, rol: u.rol, kurucu: !!u.kurucu, itibar: u.itibar || 0, dm_acik: u.dm_acik !== 0, kayit: u.kayit, mesaj_sayisi: mesaj,
    soru_sayisi: soru, cevap_sayisi: Math.max(0, mesaj - sohbet), sohbet_sayisi: sohbet,
    son_basliklar: son.results.map((r) => ({ id: r.id, baslik: r.baslik, ilan_id: r.ilan_id })), ...av,
  };
  if (sistem) return jsonYanit(o);
  if (kart.kart_rengi) o.kart_rengi = kart.kart_rengi;
  if (kart.durum) o.durum = kart.durum;
  if (kart.hedef) o.hedef = kart.hedef;
  if (kart.hakkimda) o.hakkimda = kart.hakkimda;
  if (kendisi) o.gizlilik = kart.gizlilik;
  const p = profilOku(u.profil);
  if (p && !p.atlandi) {
    o.duzey = p.ogrenim;
    if ((kart.gizlilik.puan_goster || kendisi) && typeof p.puan === 'number') { o.puan = p.puan; if (p.puan_turu) o.puan_turu = p.puan_turu; if (!kart.gizlilik.puan_goster) o.puan_gizli = true; }
    if ((kart.gizlilik.il_goster || kendisi) && (p.iller.length || p.tum_turkiye)) { o.iller = p.iller.slice(0, 8); o.il_sayisi = p.iller.length; if (p.tum_turkiye) o.tum_turkiye = true; if (!kart.gizlilik.il_goster) o.il_gizli = true; }
  }
  let katip = null;
  if (kart.gizlilik.katiplik_goster || kendisi) {
    const k = await env.DB.prepare('SELECT ozet FROM uye_katip WHERE uye_id = ?').bind(u.id).first();
    katip = k ? ozetOku(k.ozet, simdi()) : null;
    if (katip && (katip.net || katip.dk || katip.ders || katip.seri)) { o.katip = { net: katip.net, dk: katip.dk, ders: katip.ders, seri: katip.seri }; if (!kart.gizlilik.katiplik_goster) o.katip_gizli = true; }
  }
  o.rozetler = rozetleriHesapla({ kurucu: !!u.kurucu, soru, cevap: o.cevap_sayisi, sohbet, itibar: o.itibar, katip, durum: kart.durum });
  if (url.searchParams.get('tam') === '1') {
    const s = await env.DB.prepare(
      "SELECT id, baslik, olusma, yanit_sayisi, kategori FROM basliklar WHERE uye_id = ? AND gizli = 0 AND kategori <> 'oda' ORDER BY id DESC LIMIT 5",
    ).bind(u.id).all();
    const c = await env.DB.prepare(
      `SELECT y.id, y.baslik_id, y.faydali, substr(y.govde, 1, 140) AS govde, b.baslik FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id
       WHERE y.uye_id = ? AND y.gizli = 0 AND y.faydali > 0 AND b.gizli = 0 AND b.kategori <> 'oda' ORDER BY y.faydali DESC, y.id DESC LIMIT 5`,
    ).bind(u.id).all();
    o.sorular = s.results.map((r) => ({ id: r.id, baslik: r.baslik, olusma: r.olusma, yanit_sayisi: r.yanit_sayisi }));
    o.cevaplar = c.results.map((r) => ({ id: r.id, baslik_id: r.baslik_id, baslik: r.baslik, faydali: r.faydali, kisa: r.govde }));
  }
  return jsonYanit(o);
}
