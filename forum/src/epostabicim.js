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

// a***@gmail.com biçimi (adresin tamamı hiçbir yanıtta dönmez).
export function epostaMaskele(eposta) {
  if (typeof eposta !== 'string') return null;
  const i = eposta.indexOf('@');
  if (i < 1) return null;
  return `${eposta[0]}***${eposta.slice(i)}`;
}
