// İçerik denetimi: saf işlevler. denetle(metin) -> { tamam, neden?, temiz }
export const NEDEN = {
  tc: 'Kimlik numarası paylaşma.',
  telefon: 'Telefon numarası paylaşma.',
  eposta: 'E-posta adresi paylaşma.',
  baglanti: 'Bu bağlantıya izin verilmiyor.',
  kaba: 'Lütfen kaba söz kullanma.',
  bagirma: 'Lütfen büyük harfle ya da tekrarla yazma.',
};

export function temizle(metin) {
  return String(metin ?? '')
    .replace(/\r\n?/g, '\n')
    .replace(/[​-‏‪-‮⁠﻿]/g, '')
    .replace(/\t/g, ' ')
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '')
    .replace(/[ ]+\n/g, '\n')
    .replace(/\n{4,}/g, '\n\n\n')
    .trim();
}

// ---- T.C. kimlik no ----
export function tcGecerli(s) {
  if (!/^[1-9]\d{10}$/.test(s)) return false;
  const d = [...s].map(Number);
  const tek = d[0] + d[2] + d[4] + d[6] + d[8];
  const cift = d[1] + d[3] + d[5] + d[7];
  const d10 = (((tek * 7 - cift) % 10) + 10) % 10;
  if (d10 !== d[9]) return false;
  return d.slice(0, 10).reduce((a, b) => a + b, 0) % 10 === d[10];
}
function tcVar(t) {
  for (const m of t.matchAll(/(?<!\d)\d{11}(?!\d)/g)) if (tcGecerli(m[0])) return true;
  return false;
}

// ---- telefon / e-posta ----
const TELEFON = /(?<!\d)(?:\+?90[ \t.\-]*)?0?[ \t.\-]*\(?5\d{2}\)?[ \t.\-]*\d{3}[ \t.\-]*\d{2}[ \t.\-]*\d{2}(?!\d)/;
const EPOSTA = /[a-z0-9._%+\-]+\s?(?:@|\(at\)|\[at\])\s?[a-z0-9\-]+(?:\.[a-z0-9\-]+)+/i;

// ---- bağlantılar ----
const ALAN_UZANTILARI = 'com|net|org|info|me|io|co|xyz|link|ly|gl|app|dev|biz|tv|ru|cc|site|online|top|ws|gg|tr';
const BAGLANTI = new RegExp(
  `(?:https?:\\/\\/[^\\s]+|www\\.[^\\s]+|(?<![\\w@.-])[a-z0-9-]+(?:\\.[a-z0-9-]+)*\\.(?:${ALAN_UZANTILARI})(?![a-z0-9-])(?:[\\/?#][^\\s]*)?)`,
  'gi',
);
export function baglantiIzinli(ham) {
  let s = ham.replace(/[.,;:!?)"'\]]+$/, '').replace(/^https?:\/\//i, '');
  const yetki = s.split(/[\/?#]/)[0];
  const yol = s.slice(yetki.length);
  let host = yetki.slice(yetki.lastIndexOf('@') + 1).replace(/:\d+$/, '').toLowerCase().replace(/^www\./, '').replace(/\.$/, '');
  if (host === 't.me') return /^\/kpsstercihi(?:[\/?#]|$)/i.test(yol);
  if (host === 'kpsstercihi.com' || host.endsWith('.kpsstercihi.com')) return true;
  if (host.endsWith('.gov.tr') || host.endsWith('.edu.tr')) return true;
  return false;
}
function yasakBaglantiVar(t) {
  for (const m of t.matchAll(BAGLANTI)) if (!baglantiIzinli(m[0])) return true;
  return false;
}

// ---- küfür ----
const LEET = { 1: 'i', 0: 'o', 3: 'e', 4: 'a', '@': 'a', $: 's' };
const katla = (s) => s.replace(/(\p{L})\1+/gu, '$1');
const katlaGlue = (s) => s.replace(/(?<=\p{L})[.\-_*]+(?=\p{L})/gu, '');
const kat = (s) => s.replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u');

function sadelestir(metin) {
  let s = metin.replace(/İ/g, 'i').toLowerCase().replace(/[​-‏⁠﻿]/g, '');
  s = s.replace(/[10345@$]/g, (c) => LEET[c] ?? c);
  // "s i k t i r", "s.i.k.t.i.r" gibi tek harf zincirlerini birleştir
  s = s.replace(/(?<!\p{L})\p{L}(?:[ .\-_*]+\p{L}(?!\p{L}))+/gu, (m) => m.replace(/[ .\-_*]+/g, ''));
  return katla(s);
}
// Katlanmış (tekrarsız) yazıma göre; Türkçe karakterler katlanmış listede ASCII karşılığıyla yazılır.
const KOKLER = ['siktir', 'orospu', 'yarak', 'pezevenk', 'kahpe', 'gavat', 'serefsiz', 'yavsak', 'ibne', 'gotveren', 'amına', 'aminako'];
const TAM_KATLANMIS = [
  /^sik(?:e|ey|eyim|erim|erler|is|im|imi|imde)$/,
  /^am[kq](?:ler)?$/,
  /^aq$/,
  /^got(?:un|unu|unun|lek)$/,
  /^pic(?:ler|lik|lerin)$/,
];
const TAM_TURKCE = [/^piç(?:ler|lik|lerin|i)?$/, /^göt(?:ün|ünü|ünün|lek|veren)$/];

function tokenlerdeKufur(tokenler) {
  for (let i = 0; i < tokenler.length; i++) {
    const t = tokenler[i];
    const k = kat(t);
    const sonraki = kat(tokenler[i + 1] ?? '');
    if (KOKLER.some((x) => k.startsWith(x))) return true;
    if (TAM_KATLANMIS.some((r) => r.test(k)) || TAM_TURKCE.some((r) => r.test(t))) return true;
    if (/^am[ıi]n(?:a|da|i)$/.test(k) && /^ko[yc]/.test(sonraki)) return true;
    if (k === 'got' && /^(?:veren|lek)/.test(sonraki)) return true;
  }
  return false;
}
export function kabaSozVar(metin) {
  const s = sadelestir(String(metin ?? ''));
  const ayir = (x) => x.split(/[^\p{L}]+/u).filter(Boolean);
  return tokenlerdeKufur(ayir(s)) || tokenlerdeKufur(ayir(katla(katlaGlue(s))));
}

// ---- bağırma / tekrar ----
function bagirmaVar(t) {
  if (/(\S)\1{7,}/u.test(t)) return true;
  const harfler = t.match(/\p{L}/gu) || [];
  const buyuk = harfler.filter((h) => h !== h.toLocaleLowerCase('tr') && h === h.toLocaleUpperCase('tr'));
  const kucuk = harfler.filter((h) => h !== h.toLocaleUpperCase('tr'));
  const sayi = buyuk.length + kucuk.length;
  return sayi > 20 && buyuk.length / sayi > 0.7;
}

export function denetle(metin) {
  const temiz = temizle(metin);
  const red = (neden) => ({ tamam: false, neden, temiz });
  if (tcVar(temiz)) return red(NEDEN.tc);
  if (TELEFON.test(temiz)) return red(NEDEN.telefon);
  if (EPOSTA.test(temiz)) return red(NEDEN.eposta);
  if (yasakBaglantiVar(temiz)) return red(NEDEN.baglanti);
  if (kabaSozVar(temiz)) return red(NEDEN.kaba);
  if (bagirmaVar(temiz)) return red(NEDEN.bagirma);
  return { tamam: true, temiz };
}
