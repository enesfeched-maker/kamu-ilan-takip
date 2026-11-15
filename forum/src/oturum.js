// Oturum jetonları, Telegram Login Widget doğrulaması, rumuz kuralları.
import { b64uKodla, metinB64u, b64uMetin, hmacSha256, sha256, hex, sabitEsit } from './yardimci.js';
import { kabaSozVar } from './denetim.js';

export const OTURUM_SURESI = 30 * 86400;
export const GECICI_SURESI = 15 * 60;
export const TELEGRAM_GECERLILIK = 86400;

export async function jetonImzala(env, yuk) {
  const govde = metinB64u(JSON.stringify(yuk));
  return `${govde}.${b64uKodla(await hmacSha256(env.OTURUM_SIRRI, govde))}`;
}
export async function jetonCoz(env, jeton, simdi) {
  if (!env.OTURUM_SIRRI || typeof jeton !== 'string') return null;
  const [govde, imza, fazla] = jeton.split('.');
  if (!govde || !imza || fazla !== undefined) return null;
  try {
    if (!sabitEsit(imza, b64uKodla(await hmacSha256(env.OTURUM_SIRRI, govde)))) return null;
    const yuk = JSON.parse(b64uMetin(govde));
    if (!yuk || typeof yuk.s !== 'number' || yuk.s <= simdi) return null;
    return yuk;
  } catch { return null; }
}
// v: üyenin oturum_surum değeri; şifre ya da kurtarma kodu değişince artar ve eski oturumlar geçersiz olur.
export const oturumUret = (env, uyeId, simdi, surum = 0) => jetonImzala(env, { u: uyeId, v: surum, s: simdi + OTURUM_SURESI });
export async function oturumCoz(env, jeton, simdi) {
  const y = await jetonCoz(env, jeton, simdi);
  if (!y || !Number.isInteger(y.u) || y.t !== undefined || y.g !== undefined) return null;
  return { id: y.u, surum: Number.isInteger(y.v) ? y.v : 0 };
}
export const geciciUret = (env, tgId, simdi) => jetonImzala(env, { t: tgId, s: simdi + GECICI_SURESI });
export const geciciGoogleUret = (env, sub, simdi) => jetonImzala(env, { g: sub, s: simdi + GECICI_SURESI });
// Üç jeton türü birbirine karıştırılamaz: oturum {u}, Telegram geçici {t}, Google geçici {g}; her biri yalnız kendi alanını taşır.
export async function oturumUyeKimligi(env, jeton, simdi) {
  const y = await jetonCoz(env, jeton, simdi);
  return y && Number.isInteger(y.u) && y.t === undefined && y.g === undefined ? y.u : null;
}
export async function geciciTgKimligi(env, jeton, simdi) {
  const y = await jetonCoz(env, jeton, simdi);
  return y && Number.isInteger(y.t) && y.u === undefined && y.g === undefined ? y.t : null;
}
export async function geciciGoogleKimligi(env, jeton, simdi) {
  const y = await jetonCoz(env, jeton, simdi);
  return y && typeof y.g === 'string' && /^\d{1,40}$/.test(y.g) && y.u === undefined && y.t === undefined ? y.g : null;
}

// Telegram Login Widget: https://core.telegram.org/widgets/login#checking-authorization
export async function telegramDogrula(env, alanlar, simdi) {
  if (!env.TELEGRAM_BOT_TOKEN) return { tamam: false, neden: 'yapilandirma' };
  if (!alanlar || typeof alanlar !== 'object' || typeof alanlar.hash !== 'string') return { tamam: false, neden: 'hash' };
  const satirlar = Object.keys(alanlar)
    .filter((k) => k !== 'hash' && alanlar[k] !== undefined && alanlar[k] !== null)
    .sort()
    .map((k) => `${k}=${alanlar[k]}`);
  const gizli = await sha256(env.TELEGRAM_BOT_TOKEN);
  const beklenen = hex(await hmacSha256(gizli, satirlar.join('\n')));
  if (!sabitEsit(beklenen, alanlar.hash.toLowerCase())) return { tamam: false, neden: 'hash' };
  const tarih = Number(alanlar.auth_date);
  const tgId = Number(alanlar.id);
  if (!Number.isFinite(tarih) || simdi - tarih > TELEGRAM_GECERLILIK || tarih - simdi > 300) return { tamam: false, neden: 'eski' };
  if (!Number.isSafeInteger(tgId) || tgId <= 0) return { tamam: false, neden: 'kimlik' };
  return { tamam: true, tgId };
}

const ayrilmis = ['asistan', 'yonetici', 'admin', 'moderator'];
const kat = (s) => s.toLocaleLowerCase('tr').replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u').replace(/i̇/g, 'i');
// Benzersizlik anahtarı: Türkçe harfleri ASCII'ye indirir, büyük/küçük harf, "." ve "_" farkını yok sayar.
// migrations/0005_kayit.sql içindeki SQL ile birebir aynı sonucu vermelidir (testle doğrulanır).
export const rumuzKat = (s) => kat(String(s).normalize('NFC').trim()).replace(/[._]/g, '');
export function rumuzDogrula(rumuz) {
  if (typeof rumuz !== 'string') return { tamam: false, neden: 'Rumuz geçersiz.' };
  const r = rumuz.normalize('NFC').trim();
  if (r.length < 3 || r.length > 20) return { tamam: false, neden: 'Rumuz 3-20 karakter olmalı.' };
  if (!/^[A-Za-z0-9ÇĞİÖŞÜçğıöşü_.]+$/.test(r) || !/[A-Za-z0-9ÇĞİÖŞÜçğıöşü]/.test(r)) {
    return { tamam: false, neden: 'Rumuzda yalnızca harf, rakam, _ ve . kullanılabilir.' };
  }
  const n = kat(r).replace(/[._]/g, '');
  if (ayrilmis.some((a) => n.includes(a)) || n === 'sistem' || (n.includes('kpss') && n.includes('tercih'))) {
    return { tamam: false, neden: 'Bu rumuz kullanılamaz.' };
  }
  if (kabaSozVar(r)) return { tamam: false, neden: 'Bu rumuz kullanılamaz.' };
  return { tamam: true, rumuz: r, kat: n };
}
