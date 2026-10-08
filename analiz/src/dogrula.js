// Gelen olay paketinin sıkı doğrulaması: bilinmeyen alanlar atılır, metinler kısaltılır, kişisel veri sızdırabilecek
// değerler (e-posta, uzun rakam dizisi) temizlenir. Geçersiz olay sessizce düşer; geçersiz zarf paketi reddeder.
import { temizHost } from './kaynak.js';

export const MAKS_BAYT = 8192;
export const MAKS_OLAY = 20;
export const OLAY_TURLERI = new Set(['sayfa', 'aktif', 'tikla', 'kaydirma', 'hata', 'hiz', '404']);

const OTURUM = /^[A-Za-z0-9_-]{8,32}$/;
const ETIKET = /^[a-z0-9_-]{1,32}$/;
const ANAHTAR = /^[A-Za-z0-9_\-/.]{1,80}$/;
const YOL = /^\/[A-Za-z0-9/._~%+-]*$/;
const GIZLI = '[temizlendi]';

const kes = (s, n) => String(s).slice(0, n);

export function metinTemizle(v, n, kucuk = false) {
  if (typeof v !== 'string') return null;
  let s = v.replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim();
  if (kucuk) s = s.toLocaleLowerCase('tr-TR');
  if (!s) return null;
  // E-posta, uzun rakam dizisi (TC kimlik, telefon, IBAN parçası) ve yalnız rakam/ayraçtan oluşan 10+ haneli girdiler saklanmaz.
  const rakam = s.replace(/\D/g, '').length;
  if (/@/.test(s) || /\d{7,}/.test(s) || (/^[\d\s.+()-]+$/.test(s) && rakam >= 10)) return GIZLI;
  return kes(s, n);
}

function hataIletisi(v, n) {
  if (typeof v !== 'string') return null;
  // URL sorgu dizilerini (anahtar/kimlik taşıyabilir) at.
  const s = v.replace(/\?[^\s)'"]*/g, '?').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim();
  return s ? kes(s, n) : null;
}

function tamsayi(v, alt, ust) {
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  const r = Math.round(n);
  return r < alt || r > ust ? null : r;
}

export function yolTemizle(v) {
  if (typeof v !== 'string') return null;
  const p = v.split('?')[0].split('#')[0];
  return p.length <= 120 && YOL.test(p) ? p : null;
}

// Yoldan sayfa türü ve (varsa) anahtar.
export function sayfaTuru(p) {
  if (!p) return { sy: 'diger', k: null };
  if (p === '/' || p === '/index.html') return { sy: 'ana', k: null };
  let m = p.match(/^\/ilan\/([A-Za-z0-9-]{1,80})\/?$/);
  if (m) return { sy: 'ilan', k: m[1] };
  m = p.match(/^\/kurum\/([a-z0-9-]{1,80})\/?$/);
  if (m) return { sy: 'kurum', k: m[1] };
  m = p.match(/^\/kpss-taban-puanlari(?:\/(.*?))?\/?$/);
  if (m) return { sy: 'taban', k: (m[1] || '').slice(0, 80) || null };
  if (/^\/puanlar(\/|\/index\.html)?$/.test(p)) return { sy: 'robot', k: null };
  return { sy: 'diger', k: null };
}

export function olayDogrula(o) {
  if (!o || typeof o !== 'object' || Array.isArray(o)) return null;
  if (typeof o.t !== 'string' || !OLAY_TURLERI.has(o.t)) return null;
  const t = o.t;
  const p = yolTemizle(o.p);
  if (!p) return null;
  const e = { t, p, sy: null, v: null, k: null, a: null, h: null, x: null, n: null, n2: null, f: o.f === 1 || o.f === true };
  if (t === '404') {
    e.sy = '404';
    e.x = kes(p, 100);
    return e;
  }
  const tur = sayfaTuru(p);
  e.sy = tur.sy;
  e.k = tur.k;
  if (typeof o.v === 'string' && ETIKET.test(o.v)) e.v = o.v;
  if (typeof o.k === 'string' && ANAHTAR.test(o.k) && !e.k) e.k = o.k;
  if (t === 'aktif') {
    e.n = tamsayi(o.n, 1, 120);
    return e.n === null ? null : e;
  }
  if (t === 'kaydirma') {
    e.n = tamsayi(o.n, 0, 100);
    return [25, 50, 75, 100].includes(e.n) ? e : null;
  }
  if (t === 'hiz') {
    e.n = tamsayi(o.n, 0, 60000);
    e.n2 = tamsayi(o.n2, 0, 60000);
    return e.n || e.n2 ? e : null;
  }
  if (t === 'hata') {
    e.x = hataIletisi(o.x, 160);
    if (!e.x) return null;
    if (typeof o.h === 'string') e.h = kes(o.h.replace(/\?.*$/, ''), 80);
    return e;
  }
  if (t === 'tikla') {
    if (typeof o.a !== 'string' || !ETIKET.test(o.a)) return null;
    e.a = o.a;
    if (typeof o.h === 'string' && ANAHTAR.test(o.h)) e.h = o.h;
    e.x = metinTemizle(o.x, o.a === 'arama' ? 60 : 80, true);
    e.n = tamsayi(o.n, 0, 1000000);
    return e;
  }
  return e; // sayfa
}

// Paket zarfı: oturum kodu, geri dönen bayrağı, ekran genişliği, dil, yönlendiren, utm ve olay listesi.
export function paketDogrula(metin) {
  if (typeof metin !== 'string' || !metin) return { hata: 'bos' };
  if (new TextEncoder().encode(metin).length > MAKS_BAYT) return { hata: 'buyuk' };
  let j;
  try { j = JSON.parse(metin); } catch { return { hata: 'json' }; }
  if (!j || typeof j !== 'object' || Array.isArray(j)) return { hata: 'sekil' };
  if (typeof j.s !== 'string' || !OTURUM.test(j.s)) return { hata: 'oturum' };
  if (!Array.isArray(j.e) || !j.e.length || j.e.length > MAKS_OLAY) return { hata: 'olaylar' };
  const olaylar = j.e.map(olayDogrula).filter(Boolean);
  const u = j.u && typeof j.u === 'object' ? j.u : {};
  const utm = (v) => (typeof v === 'string' ? v.toLowerCase().replace(/[^a-z0-9 _.\-çğıöşü]/g, '').trim().slice(0, 40) || null : null);
  const lang = typeof j.l === 'string' && /^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?$/.test(j.l) ? j.l.toLowerCase().slice(0, 8) : null;
  return {
    oturum: j.s,
    geri: j.r === 1 || j.r === true,
    genislik: tamsayi(j.w, 1, 20000),
    dil: lang,
    rhost: temizHost(j.ref) || null,
    utm: { s: utm(u.s), m: utm(u.m), c: utm(u.c) },
    olaylar,
  };
}
