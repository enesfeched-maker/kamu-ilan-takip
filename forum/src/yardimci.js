// Ortak yardımcılar: kategoriler, base64url, HMAC, JSON yanıt.
export const KATEGORILER = [
  { kod: 'ilan', ad: 'İlan soruları' },
  { kod: 'puan', ad: 'Puan ve tercih' },
  { kod: 'kurum', ad: 'Kurum ve şehir' },
  { kod: 'mulakat', ad: 'Mülakat deneyimleri' },
  { kod: 'haklar', ad: 'Haklar ve tayin' },
  { kod: 'hazirlik', ad: 'Sınava hazırlık' },
  { kod: 'etkinlik', ad: 'Etkinlik' },
];
export const KATEGORI_KODLARI = new Set(KATEGORILER.map((k) => k.kod));

const kodlayici = new TextEncoder();

export function b64uKodla(baytlar) {
  let s = '';
  for (const b of baytlar) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function b64uCoz(s) {
  const t = String(s).replace(/-/g, '+').replace(/_/g, '/');
  const ikili = atob(t + '='.repeat((4 - (t.length % 4)) % 4));
  return Uint8Array.from(ikili, (c) => c.charCodeAt(0));
}
export const metinB64u = (metin) => b64uKodla(kodlayici.encode(metin));
export const b64uMetin = (s) => new TextDecoder().decode(b64uCoz(s));

export async function hmacSha256(anahtar, veri) {
  const ham = typeof anahtar === 'string' ? kodlayici.encode(anahtar) : anahtar;
  const k = await crypto.subtle.importKey('raw', ham, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', k, kodlayici.encode(veri)));
}
export async function sha256(metin) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', kodlayici.encode(metin)));
}
export const hex = (baytlar) => [...baytlar].map((b) => b.toString(16).padStart(2, '0')).join('');

// Sabit sürede karşılaştırma (uzunluk farkı da sonuca katılır).
export function sabitEsit(a, b) {
  a = String(a ?? ''); b = String(b ?? '');
  let fark = a.length ^ b.length;
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i++) fark |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return fark === 0;
}

export const simdi = () => Math.floor(Date.now() / 1000);

export function jsonYanit(veri, durum = 200, ek = {}) {
  return new Response(JSON.stringify(veri), {
    status: durum,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...ek },
  });
}
export const hataYanit = (durum, mesaj, ek = {}) => jsonYanit({ hata: mesaj, ...ek }, durum);

export const ILAN_KIMLIK_DESENI = /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})$/i;
export const gecerliIlanKimligi = (k) => typeof k === 'string' && ILAN_KIMLIK_DESENI.test(k);
