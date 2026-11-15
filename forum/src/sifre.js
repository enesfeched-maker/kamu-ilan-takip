// Şifre ve kurtarma kodu: PBKDF2-SHA256 + sunucu biberi (pepper), sabit süreli karşılaştırma.
// Workers ücretsiz planında istek başına 10 ms işlemci süresi var; bu yüzden tekrar sayısı düşük (20000) ve
// şifre önce sunucu biberiyle HMAC'lenir. Tekrar sayısı özetin içinde saklanır, sonradan yükseltilebilir.
import { b64uKodla, b64uCoz, hmacSha256, sabitEsit, hex } from './yardimci.js';

export const PBKDF2_TEKRAR = 20000;
export const SIFRE_EN_AZ = 8;
export const SIFRE_EN_COK = 72;

const SIK_SIFRELER = new Set([
  '12345678', '123456789', '1234567890', '11111111', '00000000', '87654321', '12341234', '123123123', '147258369', '987654321',
  'password', 'password1', 'passw0rd', 'qwerty123', 'qwertyui', 'qwertyuiop', 'asdfghjk', 'abcd1234', 'abc12345', 'iloveyou',
  'sifre123', 'sifre1234', 'sifrem123', 'parola123', 'kpss2026', 'kpss2025', 'kpss1234', 'kpsstercihi', 'memur123', 'memur1234',
  'fenerbahce', 'galatasaray', 'besiktas', 'trabzonspor', 'turkiye', 'istanbul', 'ankara06', 'ankara1234',
]);

const biberi = (env) => env.SIFRE_BIBERI || env.OTURUM_SIRRI || '';
export const sifreYapilandirildi = (env) => !!biberi(env);

// Hata metni ya da null.
export function sifreKurali(sifre, rumuz) {
  if (typeof sifre !== 'string') return 'Şifre yazmalısın.';
  if (sifre.length < SIFRE_EN_AZ) return 'Şifre en az 8 karakter olmalı.';
  if (sifre.length > SIFRE_EN_COK) return 'Şifre en çok 72 karakter olabilir.';
  const k = sifre.toLocaleLowerCase('tr');
  if (rumuz && k === String(rumuz).toLocaleLowerCase('tr')) return 'Şifren rumuzunla aynı olmasın.';
  if (SIK_SIFRELER.has(k) || /^(.)\1+$/.test(sifre)) return 'Bu şifre çok bilinen biri. Başka bir şifre seç.';
  return null;
}

async function pbkdf2(env, sifre, tuz, tekrar) {
  const ham = await hmacSha256(biberi(env), `sifre:${sifre}`);
  const anahtar = await crypto.subtle.importKey('raw', ham, 'PBKDF2', false, ['deriveBits']);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: tuz, iterations: tekrar }, anahtar, 256));
}

export async function sifreOzetle(env, sifre, tekrar = PBKDF2_TEKRAR) {
  const tuz = crypto.getRandomValues(new Uint8Array(16));
  return `pbkdf2$${tekrar}$${b64uKodla(tuz)}$${b64uKodla(await pbkdf2(env, sifre, tuz, tekrar))}`;
}

// Özet yoksa ya da bozuksa da aynı işi yapar (zamanlama farkı hesabın var olup olmadığını sızdırmasın).
const SAHTE_OZET = 'pbkdf2$20000$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
export async function sifreDogrula(env, sifre, ozet) {
  const p = typeof ozet === 'string' ? ozet.split('$') : [];
  const gecerli = p.length === 4 && p[0] === 'pbkdf2' && Number.isInteger(Number(p[1])) && Number(p[1]) >= 1000 && Number(p[1]) <= 1_000_000;
  const [, tekrar, tuz, beklenen] = gecerli ? p : SAHTE_OZET.split('$');
  try {
    const bulunan = b64uKodla(await pbkdf2(env, String(sifre ?? ''), b64uCoz(tuz), Number(tekrar)));
    return gecerli && sabitEsit(bulunan, beklenen);
  } catch { return false; }
}

// ---------- kurtarma kodu (Crockford base32, XXXX-XXXX-XXXX = 60 bit) ----------
const ALFABE = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
export function kurtarmaKoduUret() {
  const b = crypto.getRandomValues(new Uint8Array(12));
  let s = '';
  for (let i = 0; i < 12; i++) s += ALFABE[b[i] & 31] + (i % 4 === 3 && i < 11 ? '-' : '');
  return s;
}
export function kurtarmaKoduSadelestir(kod) {
  return String(kod ?? '').toUpperCase().replace(/[\s-]/g, '').replace(/[IL]/g, '1').replace(/O/g, '0');
}
export const kurtarmaKoduBicimiGecerli = (kod) => /^[0-9A-HJKMNP-TV-Z]{12}$/.test(kurtarmaKoduSadelestir(kod));
export async function kurtarmaOzeti(env, kod) {
  return hex(await hmacSha256(biberi(env), `kurtarma:${kurtarmaKoduSadelestir(kod)}`));
}
export async function kurtarmaDogrula(env, kod, ozet) {
  const bulunan = await kurtarmaOzeti(env, kod);
  return typeof ozet === 'string' && ozet.length > 0 && sabitEsit(bulunan, ozet);
}
