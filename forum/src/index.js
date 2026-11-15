// KPSS Tercihi forum API'si (Cloudflare Worker + D1).
import { KATEGORILER, KATEGORI_KODLARI, jsonYanit, hataYanit, simdi, sabitEsit, gecerliIlanKimligi } from './yardimci.js';
import { denetle, temizle } from './denetim.js';
import { oturumUret, geciciUret, oturumUyeKimligi, geciciTgKimligi, telegramDogrula, rumuzDogrula } from './oturum.js';
import { baslikHizi, yanitHizi, ipSiniri } from './hiz.js';
import { asistanYaniti } from './asistan.js';
import { ilanKaydiGetir } from './ilan.js';
import { yanitBildirimi } from './bildirim.js';

const SAYFA_BOYUTU = 20;
const KIMLIK_DESENI = /^[A-Za-z0-9_-]{16,64}$/;
const PUAN_TURU_DESENI = /^P\d{1,3}$/;
const ONBELLEK_SN = 45;

// ---------- giriş noktası ----------
export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin');
    const izinli = kokenIzinli(origin, env);
    if (request.method === 'OPTIONS') {
      return izinli ? new Response(null, { status: 204, headers: corsBasliklari(origin) }) : new Response(null, { status: 403 });
    }
    let yanit;
    try {
      if (origin && !izinli && request.method !== 'GET') yanit = hataYanit(403, 'Köken izinli değil.');
      else yanit = await yonlendir(request, env, ctx);
    } catch (e) {
      console.log('hata:', e && e.message);
      yanit = hataYanit(500, 'Beklenmeyen bir hata oldu.');
    }
    return corsEkle(yanit, origin, izinli);
  },
};

function kokenIzinli(origin, env) {
  if (!origin) return false;
  const liste = String(env.IZINLI_KOKENLER || '').split(',').map((s) => s.trim()).filter(Boolean);
  if (liste.includes(origin)) return true;
  return env.ORTAM === 'yerel' && /^http:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?$/.test(origin);
}
function corsBasliklari(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Yonetici',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}
function corsEkle(yanit, origin, izinli) {
  const h = new Headers(yanit.headers);
  h.append('Vary', 'Origin');
  if (izinli) for (const [k, v] of Object.entries(corsBasliklari(origin))) if (k !== 'Vary') h.set(k, v);
  return new Response(yanit.body, { status: yanit.status, headers: h });
}

const bekle = (ctx, p) => { const s = Promise.resolve(p).catch(() => {}); if (ctx && ctx.waitUntil) ctx.waitUntil(s); };

// ---------- yönlendirme ----------
async function yonlendir(request, env, ctx) {
  const url = new URL(request.url);
  const yol = url.pathname.replace(/\/+$/, '') || '/';
  const yontem = request.method;
  const yazma = yontem !== 'GET' && yontem !== 'HEAD';
  if (yazma && env.YAZMA_KAPALI === '1' && !yol.startsWith('/yonetim')) return hataYanit(503, 'Forum şu an yalnızca okunabiliyor.');
  let m;

  if (yontem === 'GET' || yontem === 'HEAD') {
    if (yol === '/') return new Response('kpss-forum', { headers: { 'Cache-Control': 'no-store' } });
    if (yol === '/kategoriler') return jsonYanit({ kategoriler: KATEGORILER }, 200, { 'Cache-Control': 'public, max-age=300' });
    if (yol === '/ben') return benGetir(request, env);
    if (yol === '/yonetim/sikayetler') return yonetimSikayetler(request, env);
    const anonim = !request.headers.get('Authorization') && !url.searchParams.get('kimlik');
    const onb = (uret) => onbellekli(url, ctx, anonim, uret);
    if (yol === '/basliklar') return onb(() => basliklarListe(env, url));
    if (yol === '/son') return onb(() => sonBasliklar(env));
    if (yol === '/durum') return onb(() => forumDurumu(env));
    if (yol === '/ozet') return onb(() => ozet(env, url));
    if ((m = yol.match(/^\/baslik\/(\d+)$/))) return onb(() => baslikGetir(request, env, Number(m[1])));
    if ((m = yol.match(/^\/ilan\/([^/]+)$/))) return onb(() => ilanGetir(request, env, url, decodeURIComponent(m[1])));
    return hataYanit(404, 'Bulunamadı.');
  }

  if (yontem === 'POST') {
    if (yol === '/giris/telegram') return girisTelegram(request, env);
    if (yol === '/giris/rumuz') return girisRumuz(request, env);
    if (yol === '/giris/deneme') return girisDeneme(request, env);
    if (yol === '/ben/bildirim') return benBildirim(request, env);
    if (yol === '/baslik') return baslikOlustur(request, env);
    if ((m = yol.match(/^\/baslik\/(\d+)\/yanit$/))) return yanitYaz(request, env, ctx, Number(m[1]));
    if ((m = yol.match(/^\/ilan\/([^/]+)\/yanit$/))) return ilanYanitYaz(request, env, decodeURIComponent(m[1]));
    if ((m = yol.match(/^\/yanit\/(\d+)\/faydali$/))) return faydaliDegistir(request, env, Number(m[1]));
    if ((m = yol.match(/^\/yanit\/(\d+)\/sikayet$/))) return sikayetEt(request, env, Number(m[1]));
    if ((m = yol.match(/^\/basvuru\/([^/]+)$/))) return basvuruYaz(request, env, decodeURIComponent(m[1]));
    if (yol === '/yonetim/baslik') return yonetimBaslik(request, env);
    if (yol === '/yonetim/gizle') return yonetimGizle(request, env);
    if (yol === '/yonetim/engelle') return yonetimEngelle(request, env);
    return hataYanit(404, 'Bulunamadı.');
  }

  if (yontem === 'DELETE' && (m = yol.match(/^\/basvuru\/([^/]+)$/))) return basvuruSil(request, env, new URL(request.url), decodeURIComponent(m[1]));
  return hataYanit(405, 'Yöntem desteklenmiyor.');
}

async function onbellekli(url, ctx, anonim, uret) {
  const c = typeof caches !== 'undefined' ? caches.default : null;
  if (!c || !anonim) return uret();
  const anahtar = new Request(`${url.origin}${url.pathname}${url.search}`);
  const var_ = await c.match(anahtar);
  if (var_) return var_;
  const yanit = await uret();
  if (yanit.status === 200) {
    const h = new Headers(yanit.headers);
    h.set('Cache-Control', `public, max-age=0, s-maxage=${ONBELLEK_SN}`);
    const k = new Response(yanit.body, { status: 200, headers: h });
    bekle(ctx, c.put(anahtar, k.clone()));
    return k;
  }
  return yanit;
}

// ---------- ortak ----------
async function govdeOku(request) {
  try {
    const t = await request.text();
    if (t.length > 20000) return null;
    const j = JSON.parse(t || '{}');
    return j && typeof j === 'object' && !Array.isArray(j) ? j : null;
  } catch { return null; }
}
const kullaniciJson = (u) => ({ id: u.id, rumuz: u.rumuz, kurucu: !!u.kurucu, rol: u.rol });

async function oturumUyesi(request, env) {
  const m = (request.headers.get('Authorization') || '').match(/^Bearer (.+)$/);
  if (!m) return null;
  const id = await oturumUyeKimligi(env, m[1], simdi());
  if (!id) return null;
  return env.DB.prepare('SELECT id, rumuz, kurucu, rol, bildirim, engelli, kayit FROM uyeler WHERE id = ?').bind(id).first();
}
async function yazar(request, env) {
  const uye = await oturumUyesi(request, env);
  if (!uye) return { hata: hataYanit(401, 'Giriş yapmalısın.') };
  if (uye.engelli) return { hata: hataYanit(403, 'Hesabın yazmaya kapatıldı.') };
  return { uye };
}
function yoneticiMi(request, env) {
  return !!env.YONETICI_ANAHTARI && sabitEsit(request.headers.get('X-Yonetici') || '', env.YONETICI_ANAHTARI);
}
const ayrik = (n) => Math.max(1, Math.min(Number(n) || 1, 100));

// ---------- giriş ----------
async function oturumYaniti(env, uye) {
  return jsonYanit({ oturum: await oturumUret(env, uye.id, simdi()), uye: kullaniciJson(uye) });
}
async function girisTelegram(request, env) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.OTURUM_SIRRI) return hataYanit(503, 'Giriş henüz yapılandırılmadı.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const d = await telegramDogrula(env, g, simdi());
  if (!d.tamam) return hataYanit(401, d.neden === 'eski' ? 'Giriş süresi dolmuş, tekrar dene.' : 'Telegram girişi doğrulanamadı.');
  const uye = await env.DB.prepare('SELECT id, rumuz, kurucu, rol FROM uyeler WHERE tg_id = ?').bind(d.tgId).first();
  if (uye) return oturumYaniti(env, uye);
  return jsonYanit({ yeni: true, gecici: await geciciUret(env, d.tgId, simdi()) });
}
async function uyeOlustur(env, tgId, rumuz) {
  const r = rumuzDogrula(rumuz);
  if (!r.tamam) return { hata: hataYanit(400, r.neden) };
  const var_ = await env.DB.prepare('SELECT id FROM uyeler WHERE rumuz = ?').bind(r.rumuz).first();
  if (var_) return { hata: hataYanit(409, 'Bu rumuz alınmış.') };
  const sayi = await env.DB.prepare("SELECT COUNT(*) AS n FROM uyeler WHERE rol NOT IN ('sistem', 'asistan')").first();
  const t = simdi();
  try {
    await env.DB.prepare('INSERT INTO uyeler (tg_id, rumuz, kayit, kurucu) VALUES (?, ?, ?, ?)').bind(tgId, r.rumuz, t, (sayi?.n || 0) < KURUCU_SINIRI ? 1 : 0).run();
  } catch { return { hata: hataYanit(409, 'Bu rumuz alınmış.') }; }
  const uye = await env.DB.prepare('SELECT id, rumuz, kurucu, rol FROM uyeler WHERE tg_id = ?').bind(tgId).first();
  return { uye };
}
async function girisRumuz(request, env) {
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const tgId = await geciciTgKimligi(env, g.gecici, simdi());
  if (!tgId) return hataYanit(401, 'Giriş süresi dolmuş, Telegram ile tekrar dene.');
  const mevcut = await env.DB.prepare('SELECT id, rumuz, kurucu, rol FROM uyeler WHERE tg_id = ?').bind(tgId).first();
  if (mevcut) return oturumYaniti(env, mevcut);
  const s = await uyeOlustur(env, tgId, g.rumuz);
  return s.hata || oturumYaniti(env, s.uye);
}
function ozetSayi(metin) {
  let h = 2166136261;
  for (let i = 0; i < metin.length; i++) { h ^= metin.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h;
}
async function girisDeneme(request, env) {
  if (env.ORTAM !== 'yerel') return hataYanit(404, 'Bulunamadı.');
  if (!env.OTURUM_SIRRI) return hataYanit(503, 'OTURUM_SIRRI tanımlı değil.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const r = rumuzDogrula(g.rumuz);
  if (!r.tamam) return hataYanit(400, r.neden);
  const mevcut = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, tg_id FROM uyeler WHERE rumuz = ?').bind(r.rumuz).first();
  if (mevcut) return mevcut.tg_id < 0 ? oturumYaniti(env, mevcut) : hataYanit(409, 'Bu rumuz alınmış.');
  const s = await uyeOlustur(env, -(1 + (ozetSayi(r.rumuz.toLowerCase()) % 2000000000)), r.rumuz);
  return s.hata || oturumYaniti(env, s.uye);
}
async function benGetir(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  return jsonYanit({ uye: { ...kullaniciJson(u), bildirim: u.bildirim === 1, engelli: !!u.engelli } });
}
async function benBildirim(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  const g = await govdeOku(request);
  if (!g || typeof g.acik !== 'boolean') return hataYanit(400, 'acik alanı true/false olmalı.');
  await env.DB.prepare('UPDATE uyeler SET bildirim = ? WHERE id = ?').bind(g.acik ? 1 : 0, u.id).run();
  return jsonYanit({ tamam: true, bildirim: g.acik });
}

// ---------- okuma ----------
const BASLIK_ALANLARI = `b.id, b.kategori, b.baslik, b.kaynak, b.sabit, b.olusma, b.son_hareket, b.yanit_sayisi, b.ilan_id, b.govde,
  u.rumuz, u.kurucu, u.rol`;
const KURUCU_SINIRI = 200;   // ilk 200 üye "Kurucu üye" rozeti alır
function baslikCikti(r, govdeli) {
  const o = {
    id: r.id, kategori: r.kategori, baslik: r.baslik, rumuz: r.rumuz, kurucu: !!r.kurucu, rol: r.rol, kaynak: r.kaynak,
    sabit: !!r.sabit, olusma: r.olusma, son_hareket: r.son_hareket, yanit_sayisi: r.yanit_sayisi, ilan_id: r.ilan_id,
  };
  if (govdeli) o.govde = r.govde; else o.kisa = String(r.govde || '').slice(0, 140);
  return o;
}
async function basliklarListe(env, url) {
  const kategori = url.searchParams.get('kategori') || '';
  if (kategori && !KATEGORI_KODLARI.has(kategori)) return hataYanit(400, 'Kategori geçersiz.');
  const sayfa = Math.min(Math.max(parseInt(url.searchParams.get('sayfa'), 10) || 1, 1), 100);
  const bag = [];
  let kosul = 'b.gizli = 0';
  if (kategori) { kosul += ' AND b.kategori = ?'; bag.push(kategori); }
  if (url.searchParams.get('bekleyen') === '1') kosul += ' AND b.yanit_sayisi = 0 AND b.sabit = 0';   // henüz yanıtlanmamış sorular
  bag.push(SAYFA_BOYUTU + 1, (sayfa - 1) * SAYFA_BOYUTU);
  const { results } = await env.DB.prepare(
    `SELECT b.id, b.kategori, b.baslik, substr(b.govde, 1, 140) AS govde, b.kaynak, b.sabit, b.olusma, b.son_hareket, b.yanit_sayisi, b.ilan_id,
            u.rumuz, u.kurucu, u.rol
     FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE ${kosul}
     ORDER BY b.sabit DESC, b.son_hareket DESC LIMIT ? OFFSET ?`,
  ).bind(...bag).all();
  return jsonYanit({ basliklar: results.slice(0, SAYFA_BOYUTU).map((r) => baslikCikti(r, false)), sayfa, sonraki: results.length > SAYFA_BOYUTU });
}
async function sonBasliklar(env) {
  const { results } = await env.DB.prepare(
    `SELECT b.id, b.kategori, b.baslik, substr(b.govde, 1, 140) AS govde, b.kaynak, b.sabit, b.olusma, b.son_hareket, b.yanit_sayisi, b.ilan_id,
            u.rumuz, u.kurucu, u.rol
     FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE b.gizli = 0 ORDER BY b.son_hareket DESC LIMIT 10`,
  ).all();
  return jsonYanit({ basliklar: results.map((r) => baslikCikti(r, false)) });
}
// Forum sayfasının üst şeridi: üye sayısı, kalan kurucu rozeti, son 24 saatin mesaj ve yazar sayısı (gerçek sayılar; önbellekli).
export async function forumDurumu(env, simdi = Math.floor(Date.now() / 1000)) {
  const u = await env.DB.prepare("SELECT COUNT(*) AS n FROM uyeler WHERE rol NOT IN ('sistem', 'asistan')").first();
  const g = await env.DB.prepare(
    "SELECT COUNT(*) AS mesaj, COUNT(DISTINCT y.uye_id) AS yazar FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id WHERE y.olusma > ? AND y.gizli = 0 AND u.rol NOT IN ('sistem', 'asistan')",
  ).bind(simdi - 86400).first();
  const uye = u?.n || 0;
  return jsonYanit({ uye, kurucu_kalan: Math.max(0, KURUCU_SINIRI - uye), bugun_mesaj: g?.mesaj || 0, bugun_yazar: g?.yazar || 0 });
}
async function baslikSatiri(env, kosul, deger) {
  return env.DB.prepare(`SELECT ${BASLIK_ALANLARI} FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE ${kosul} AND b.gizli = 0`).bind(deger).first();
}
function yanitCikti(r, uye, oylar) {
  const o = { id: r.id, govde: r.govde, rumuz: r.rumuz, rol: r.rol, kurucu: !!r.kurucu, faydali: r.faydali, ust_id: r.ust_id, olusma: r.olusma };
  if (uye) { o.benim = r.uye_id === uye.id; o.oyladim = oylar.has(r.id); }
  return o;
}
const YANIT_SECIM = `SELECT y.id, y.govde, y.olusma, y.faydali, y.ust_id, y.uye_id, u.rumuz, u.rol, u.kurucu FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id`;
async function yanitlariGetir(env, baslikId, uye) {
  const { results } = await env.DB.prepare(`${YANIT_SECIM} WHERE y.baslik_id = ? AND y.gizli = 0 ORDER BY y.id LIMIT 500`).bind(baslikId).all();
  let oylar = new Set();
  if (uye && results.length) {
    const o = await env.DB.prepare('SELECT o.yanit_id FROM oylar o JOIN yanitlar y ON y.id = o.yanit_id WHERE o.uye_id = ? AND y.baslik_id = ?').bind(uye.id, baslikId).all();
    oylar = new Set(o.results.map((x) => x.yanit_id));
  }
  return results.map((r) => yanitCikti(r, uye, oylar));
}
async function yanitTek(env, id, uye) {
  const r = await env.DB.prepare(`${YANIT_SECIM} WHERE y.id = ?`).bind(id).first();
  return r ? yanitCikti(r, uye, new Set()) : null;
}
async function baslikGetir(request, env, id) {
  const b = await baslikSatiri(env, 'b.id = ?', id);
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  const uye = await oturumUyesi(request, env);
  return jsonYanit({ baslik: baslikCikti(b, true), yanitlar: await yanitlariGetir(env, id, uye) });
}

function nicelik(sirali, q) {
  const k = (sirali.length - 1) * q, a = Math.floor(k), b = Math.ceil(k);
  return Math.round((sirali[a] + (sirali[b] - sirali[a]) * (k - a)) * 100) / 100;
}
export async function basvuruOzeti(env, ilanId, kimlik) {
  const say = await env.DB.prepare('SELECT COUNT(*) AS n FROM basvurular WHERE ilan_id = ?').bind(ilanId).first();
  const tur = await env.DB.prepare(
    'SELECT puan_turu, COUNT(*) AS c FROM basvurular WHERE ilan_id = ? AND puan IS NOT NULL GROUP BY puan_turu ORDER BY c DESC, puan_turu LIMIT 1',
  ).bind(ilanId).first();
  let puan = null, ben = null;
  if (kimlik) {
    const b = await env.DB.prepare('SELECT puan_turu, puan FROM basvurular WHERE ilan_id = ? AND kimlik = ?').bind(ilanId, kimlik).first();
    if (b) ben = { puan_turu: b.puan_turu, puan: b.puan };
  }
  if (tur && tur.c >= 5) {
    const { results } = await env.DB.prepare('SELECT puan FROM basvurular WHERE ilan_id = ? AND puan_turu = ? AND puan IS NOT NULL ORDER BY puan').bind(ilanId, tur.puan_turu).all();
    const p = results.map((r) => r.puan);
    puan = { adet: p.length, puan_turu: tur.puan_turu, en_dusuk: p[0], ceyrek1: nicelik(p, 0.25), medyan: nicelik(p, 0.5), ceyrek3: nicelik(p, 0.75), en_yuksek: p[p.length - 1] };
    if (ben && ben.puan_turu === tur.puan_turu && ben.puan != null) puan.sira = p.filter((x) => x > ben.puan).length + 1;
  }
  return { sayi: say?.n || 0, puan, ben };
}
async function ilanGetir(request, env, url, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const uye = await oturumUyesi(request, env);
  const b = await baslikSatiri(env, 'b.ilan_id = ?', ilanId);
  let kimlik = url.searchParams.get('kimlik') || '';
  kimlik = uye ? `u${uye.id}` : KIMLIK_DESENI.test(kimlik) ? kimlik : '';
  return jsonYanit({
    baslik: b ? baslikCikti(b, true) : null,
    yanitlar: b ? await yanitlariGetir(env, b.id, uye) : [],
    basvuru: await basvuruOzeti(env, ilanId, kimlik),
  });
}
async function ozet(env, url) {
  const idler = [...new Set((url.searchParams.get('ilanlar') || '').split(',').map((s) => s.trim()).filter(gecerliIlanKimligi))].slice(0, 100);
  if (!idler.length) return jsonYanit({});
  const yer = idler.map(() => '?').join(',');
  const y = await env.DB.prepare(`SELECT ilan_id, yanit_sayisi FROM basliklar WHERE gizli = 0 AND ilan_id IN (${yer})`).bind(...idler).all();
  const b = await env.DB.prepare(`SELECT ilan_id, COUNT(*) AS n FROM basvurular WHERE ilan_id IN (${yer}) GROUP BY ilan_id`).bind(...idler).all();
  const sonuc = Object.fromEntries(idler.map((i) => [i, { yanit: 0, basvuru: 0 }]));
  for (const r of y.results) sonuc[r.ilan_id].yanit = r.yanit_sayisi;
  for (const r of b.results) sonuc[r.ilan_id].basvuru = r.n;
  return jsonYanit(sonuc);
}

// ---------- yazma: başlık / yanıt ----------
const tekSatir = (s) => temizle(s).replace(/\s+/g, ' ');
function metinDenetle(metin, en, fazla, ad) {
  const t = temizle(metin);
  if (t.length < en || t.length > fazla) return { hata: hataYanit(400, `${ad} ${en}-${fazla} karakter olmalı.`) };
  const d = denetle(t);
  if (!d.tamam) return { hata: hataYanit(422, d.neden) };
  return { temiz: d.temiz };
}
async function baslikOlustur(request, env) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!KATEGORI_KODLARI.has(g.kategori)) return hataYanit(400, 'Kategori geçersiz.');
  if (g.kategori === 'ilan') return hataYanit(400, 'İlan sorularını ilan sayfasından sorabilirsin.');
  if (g.kategori === 'etkinlik' && uye.rol !== 'yonetici' && uye.rol !== 'sistem') return hataYanit(403, 'Etkinlik başlığını yalnızca yöneticiler açabilir.');
  const b = metinDenetle(tekSatir(g.baslik), 8, 120, 'Başlık');
  if (b.hata) return b.hata;
  const o = metinDenetle(g.govde, 10, 4000, 'Metin');
  if (o.hata) return o.hata;
  const sinir = await baslikHizi(env, uye, simdi());
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const t = simdi();
  const r = await env.DB.prepare(
    "INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, olusma, son_hareket) VALUES (?, ?, ?, ?, 'uye', ?, ?)",
  ).bind(g.kategori, b.temiz, o.temiz, uye.id, t, t).run();
  const satir = await baslikSatiri(env, 'b.id = ?', r.meta.last_row_id);
  return jsonYanit({ baslik: baslikCikti(satir, true) }, 201);
}
async function yanitEkle(env, baslikId, uyeId, govde, ustId, t) {
  const r = await env.DB.batch([
    env.DB.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, ust_id) VALUES (?, ?, ?, ?, ?)').bind(baslikId, uyeId, govde, t, ustId ?? null),
    env.DB.prepare('UPDATE basliklar SET yanit_sayisi = yanit_sayisi + 1, son_hareket = ? WHERE id = ?').bind(t, baslikId),
  ]);
  return r[0].meta.last_row_id;
}
async function yanitYaz(request, env, ctx, baslikId) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const o = metinDenetle(g.govde, 2, 2000, 'Yanıt');
  if (o.hata) return o.hata;
  const b = await env.DB.prepare('SELECT id, baslik, uye_id FROM basliklar WHERE id = ? AND gizli = 0').bind(baslikId).first();
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  let ust = null;
  if (g.ust_id !== undefined && g.ust_id !== null) {
    ust = await env.DB.prepare('SELECT id, uye_id FROM yanitlar WHERE id = ? AND baslik_id = ? AND gizli = 0').bind(Number(g.ust_id), baslikId).first();
    if (!ust) return hataYanit(400, 'Yanıtlanan mesaj bulunamadı.');
  }
  const sinir = await yanitHizi(env, uye, simdi());
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const id = await yanitEkle(env, baslikId, uye.id, o.temiz, ust ? ust.id : null, simdi());
  bekle(ctx, yanitBildirimi(env, { baslikId, baslikAdi: b.baslik, yanitlayan: uye, aliciIdleri: [b.uye_id, ust ? ust.uye_id : 0] }));
  return jsonYanit({ yanit: await yanitTek(env, id, uye) }, 201);
}
async function ilanYanitYaz(request, env, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const o = metinDenetle(g.govde, 2, 2000, 'Yanıt');
  if (o.hata) return o.hata;
  let b = await env.DB.prepare('SELECT id, gizli FROM basliklar WHERE ilan_id = ?').bind(ilanId).first();
  if (b && b.gizli) return hataYanit(403, 'Bu başlık kapatıldı.');
  const kayit = await ilanKaydiGetir(env, ilanId);
  let ad = null;
  if (!b) {
    if (kayit && kayit.baslik) ad = tekSatir(kayit.baslik).slice(0, 160);
    else {
      const a = metinDenetle(tekSatir(g.ilan_baslik), 8, 160, 'İlan başlığı');
      if (a.hata) return a.hata;
      ad = a.temiz;
    }
    if (ad.length < 8) return hataYanit(400, 'İlan başlığı en az 8 karakter olmalı.');
  }
  const sinir = await yanitHizi(env, uye, simdi());
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const t = simdi();
  if (!b) {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO basliklar (kategori, baslik, govde, uye_id, ilan_id, kaynak, olusma, son_hareket) VALUES ('ilan', ?, '', 1, ?, 'sistem', ?, ?)",
    ).bind(ad, ilanId, t, t).run();
    b = await env.DB.prepare('SELECT id, gizli FROM basliklar WHERE ilan_id = ?').bind(ilanId).first();
  }
  const soruId = await yanitEkle(env, b.id, uye.id, o.temiz, null, t);
  const yanitlar = [await yanitTek(env, soruId, uye)];
  try {
    const cevap = kayit ? asistanYaniti(o.temiz, kayit) : null;
    if (cevap) {
      const aid = await yanitEkle(env, b.id, 2, cevap, soruId, t);
      yanitlar.push(await yanitTek(env, aid, uye));
    }
  } catch (e) { console.log('asistan hatası:', e && e.message); }
  return jsonYanit({ baslik_id: b.id, yanitlar }, 201);
}

// ---------- faydalı / şikayet ----------
async function faydaliDegistir(request, env, id) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const y = await env.DB.prepare('SELECT id, uye_id FROM yanitlar WHERE id = ? AND gizli = 0').bind(id).first();
  if (!y) return hataYanit(404, 'Yanıt bulunamadı.');
  if (y.uye_id === uye.id) return hataYanit(400, 'Kendi yanıtına oy veremezsin.');
  const ekle = await env.DB.prepare('INSERT OR IGNORE INTO oylar (yanit_id, uye_id) VALUES (?, ?)').bind(id, uye.id).run();
  let oyladim;
  if (ekle.meta.changes > 0) {
    await env.DB.prepare('UPDATE yanitlar SET faydali = faydali + 1 WHERE id = ?').bind(id).run();
    oyladim = true;
  } else {
    await env.DB.batch([
      env.DB.prepare('DELETE FROM oylar WHERE yanit_id = ? AND uye_id = ?').bind(id, uye.id),
      env.DB.prepare('UPDATE yanitlar SET faydali = MAX(faydali - 1, 0) WHERE id = ?').bind(id),
    ]);
    oyladim = false;
  }
  const s = await env.DB.prepare('SELECT faydali FROM yanitlar WHERE id = ?').bind(id).first();
  return jsonYanit({ faydali: s.faydali, oyladim });
}
async function yanitGizle(env, id, gizli) {
  const y = await env.DB.prepare('SELECT baslik_id, gizli FROM yanitlar WHERE id = ?').bind(id).first();
  if (!y || (y.gizli === 1) === gizli) return false;
  await env.DB.batch([
    env.DB.prepare('UPDATE yanitlar SET gizli = ? WHERE id = ?').bind(gizli ? 1 : 0, id),
    env.DB.prepare('UPDATE basliklar SET yanit_sayisi = MAX(yanit_sayisi + ?, 0) WHERE id = ?').bind(gizli ? -1 : 1, y.baslik_id),
  ]);
  return true;
}
async function sikayetEt(request, env, id) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const y = await env.DB.prepare('SELECT id, sikayet, gizli FROM yanitlar WHERE id = ?').bind(id).first();
  if (!y || y.gizli) return hataYanit(404, 'Yanıt bulunamadı.');
  const ekle = await env.DB.prepare('INSERT OR IGNORE INTO sikayetler (yanit_id, uye_id) VALUES (?, ?)').bind(id, uye.id).run();
  if (ekle.meta.changes === 0) return jsonYanit({ tamam: true, zaten: true });
  const yeni = y.sikayet + 1;
  await env.DB.prepare('UPDATE yanitlar SET sikayet = ? WHERE id = ?').bind(yeni, id).run();
  let gizlendi = false;
  if (yeni >= 3) gizlendi = await yanitGizle(env, id, true);
  return jsonYanit({ tamam: true, gizlendi });
}

// ---------- başvuru ----------
async function basvuruKimligi(request, env, kaynak) {
  const uye = await oturumUyesi(request, env);
  if (uye) return uye.engelli ? null : `u${uye.id}`;
  return typeof kaynak === 'string' && KIMLIK_DESENI.test(kaynak) ? kaynak : null;
}
async function basvuruYaz(request, env, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!ipSiniri(request.headers.get('CF-Connecting-IP'), simdi())) return hataYanit(429, 'Çok fazla istek.');
  const kimlik = await basvuruKimligi(request, env, g.kimlik);
  if (!kimlik) return hataYanit(400, 'Kimlik geçersiz.');
  let tur = null, puan = null;
  if (g.puan_turu !== undefined || g.puan !== undefined) {
    const p = Number(g.puan);
    if (typeof g.puan_turu !== 'string' || !PUAN_TURU_DESENI.test(g.puan_turu) || g.puan === null || g.puan === '' || !Number.isFinite(p) || p < 40 || p > 100) {
      return hataYanit(400, 'Puan türü (P3 gibi) ve 40-100 arası puan gerekli.');
    }
    tur = g.puan_turu; puan = Math.round(p * 100) / 100;
  }
  await env.DB.prepare(
    `INSERT INTO basvurular (ilan_id, kimlik, puan_turu, puan, olusma) VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(ilan_id, kimlik) DO UPDATE SET puan_turu = COALESCE(excluded.puan_turu, puan_turu), puan = COALESCE(excluded.puan, puan)`,
  ).bind(ilanId, kimlik, tur, puan, simdi()).run();
  return jsonYanit({ tamam: true, basvuru: await basvuruOzeti(env, ilanId, kimlik) });
}
async function basvuruSil(request, env, url, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const kimlik = await basvuruKimligi(request, env, url.searchParams.get('kimlik'));
  if (!kimlik) return hataYanit(400, 'Kimlik geçersiz.');
  await env.DB.prepare('DELETE FROM basvurular WHERE ilan_id = ? AND kimlik = ?').bind(ilanId, kimlik).run();
  return jsonYanit({ tamam: true, basvuru: await basvuruOzeti(env, ilanId, kimlik) });
}

// ---------- yönetim ----------
async function yonetimBaslik(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!KATEGORI_KODLARI.has(g.kategori) || g.kategori === 'ilan') return hataYanit(400, 'Kategori geçersiz.');
  const kaynak = g.kaynak === 'telegram' ? 'telegram' : g.kaynak === 'sistem' || g.kaynak === undefined ? 'sistem' : null;
  if (!kaynak) return hataYanit(400, 'Kaynak sistem ya da telegram olmalı.');
  const baslik = tekSatir(g.baslik), govde = temizle(g.govde);
  if (baslik.length < 8 || baslik.length > 120 || govde.length < 10 || govde.length > 4000) return hataYanit(400, 'Başlık 8-120, metin 10-4000 karakter olmalı.');
  const t = simdi();
  const r = await env.DB.prepare(
    'INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket) VALUES (?, ?, ?, 1, ?, ?, ?, ?)',
  ).bind(g.kategori, baslik, govde, kaynak, g.sabit ? 1 : 0, t, t).run();
  return jsonYanit({ baslik: baslikCikti(await baslikSatiri(env, 'b.id = ?', r.meta.last_row_id), true) }, 201);
}
async function yonetimGizle(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const g = await govdeOku(request);
  if (!g || !Number.isInteger(g.id) || typeof g.gizli !== 'boolean') return hataYanit(400, 'Geçersiz istek.');
  if (g.tur === 'baslik') {
    await env.DB.prepare('UPDATE basliklar SET gizli = ? WHERE id = ?').bind(g.gizli ? 1 : 0, g.id).run();
  } else if (g.tur === 'yanit') {
    await yanitGizle(env, g.id, g.gizli);
  } else return hataYanit(400, 'tur baslik ya da yanit olmalı.');
  return jsonYanit({ tamam: true });
}
async function yonetimEngelle(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const g = await govdeOku(request);
  if (!g || !Number.isInteger(g.uye_id) || typeof g.engelli !== 'boolean') return hataYanit(400, 'Geçersiz istek.');
  await env.DB.prepare("UPDATE uyeler SET engelli = ? WHERE id = ? AND rol NOT IN ('sistem', 'asistan')").bind(g.engelli ? 1 : 0, g.uye_id).run();
  return jsonYanit({ tamam: true });
}
async function yonetimSikayetler(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const { results } = await env.DB.prepare(
    `SELECT y.id, y.baslik_id, y.govde, y.sikayet, y.gizli, y.olusma, y.uye_id, u.rumuz FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id
     WHERE y.sikayet > 0 ORDER BY y.sikayet DESC, y.id DESC LIMIT 100`,
  ).all();
  return jsonYanit({ yanitlar: results.map((r) => ({ ...r, gizli: !!r.gizli })) });
}
