// E-posta adresi biçimi: normalleştirme, doğrulama, maskeleme. Bağımlılığı yoktur (google.js ve eposta.js kullanır).
const YEREL = /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*$/;
const ETIKET = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

// Küçük harf + NFC + baştaki/sondaki boşluk atılır; yalnız ASCII adresler kabul edilir (IDN ve Unicode yerel kısım yok).
// Geçerliyse normalleşmiş adres, değilse null. Tek yönlü: büyük/küçük harf farkı aynı adres sayılır.
export function epostaNormalle(ham) {
  if (typeof ham !== 'string' || ham.length > 400) return null;
  const s = ham.normalize('NFC').trim().toLowerCase();
  if (s.length < 6 || s.length > 254) return null;
  const i = s.indexOf('@');
  if (i < 1 || i !== s.lastIndexOf('@')) return null;
  const yerel = s.slice(0, i);
  const alan = s.slice(i + 1);
  if (yerel.length > 64 || !YEREL.test(yerel)) return null;
  const etiketler = alan.split('.');
  if (etiketler.length < 2 || !etiketler.every((e) => ETIKET.test(e))) return null;
  if (!/^[a-z]{2,24}$|^xn--[a-z0-9-]{2,59}$/.test(etiketler[etiketler.length - 1])) return null;   // son etiket alfabetik (.com) ya da punycode
  return s;
}

const GMAIL = new Set(['gmail.com', 'googlemail.com']);
export const gmailMi = (eposta) => typeof eposta === 'string' && GMAIL.has(eposta.slice(eposta.lastIndexOf('@') + 1));

// Aynı posta kutusuna giden adres biçimleri tek anahtara iner (yalnız kod ve sayaç anahtarları için; üyede saklanan adres değişmez).
// gmail.com / googlemail.com: noktalar ve +ek atılır, googlemail -> gmail.
export function epostaTekil(eposta) {
  const i = eposta.lastIndexOf('@');
  let yerel = eposta.slice(0, i); let alan = eposta.slice(i + 1);
  if (GMAIL.has(alan)) { yerel = yerel.split('+')[0].replace(/\./g, ''); alan = 'gmail.com'; }
  return `${yerel}@${alan}`;
}
// Hız sınırı sayaçları için: tekil biçim + tüm alan adlarında +ek atılır (a+1@x.com ile a+2@x.com tek sayaç).
export function epostaSayacAdresi(eposta) {
  const t = epostaTekil(eposta); const i = t.lastIndexOf('@');
  return `${t.slice(0, i).split('+')[0]}${t.slice(i)}`;
}

// a***@gmail.com biçimi (adresin tamamı hiçbir yanıtta dönmez).
export function epostaMaskele(eposta) {
  if (typeof eposta !== 'string') return null;
  const i = eposta.indexOf('@');
  if (i < 1) return null;
  return `${eposta[0]}***${eposta.slice(i)}`;
}
