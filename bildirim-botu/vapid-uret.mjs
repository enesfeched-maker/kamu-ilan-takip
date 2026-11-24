// VAPID anahtar çifti üretir (P-256). Yalnız konsola yazar; dosyaya kaydetmez.
//   node vapid-uret.mjs
// VAPID_ACIK  -> wrangler.toml [vars] içine (65 bayt sıkıştırılmamış nokta, base64url)
// VAPID_OZEL  -> `wrangler secret put VAPID_OZEL` (ham özel değer d, 32 bayt, base64url)
import { webcrypto as crypto } from 'node:crypto';

const b64u = (b) => Buffer.from(b).toString('base64url');
const cift = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
const jwk = await crypto.subtle.exportKey('jwk', cift.privateKey);
const acik = Buffer.concat([Buffer.from([4]), Buffer.from(jwk.x, 'base64url'), Buffer.from(jwk.y, 'base64url')]);
console.log('VAPID_ACIK=' + b64u(acik));
console.log('VAPID_OZEL=' + jwk.d);
console.log('\nVAPID_ACIK degerini wrangler.toml [vars] icine ve /nereye/ sayfasindaki applicationServerKey sabitine yaz.');
console.log('VAPID_OZEL gizlidir: wrangler secret put VAPID_OZEL (degeri yapistir). Bu ciktiyi hicbir yere kaydetme.');
