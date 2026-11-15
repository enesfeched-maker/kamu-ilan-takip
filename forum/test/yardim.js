// Test yardımcıları: ortam kurma, istek atma, sahte fetch.
import { sahteD1 } from './sahte-d1.js';
import worker from '../src/index.js';
import { ilanOnbellekTemizle } from '../src/ilan.js';
import { bildirimSifirla } from '../src/bildirim.js';
import { ipSinirSifirla } from '../src/hiz.js';
import { hmacSha256, sha256, hex } from '../src/yardimci.js';

export const SITE = 'https://kpsstercihi.com/';
export const UUID = '9c82aab5-022e-43c8-b7f1-e6cf329d205b';

export function ortam(ek = {}) {
  ilanOnbellekTemizle(); bildirimSifirla(); ipSinirSifirla();
  return {
    DB: sahteD1(), SITE_URL: SITE, IZINLI_KOKENLER: 'https://kpsstercihi.com,https://www.kpsstercihi.com', YAZMA_KAPALI: '0',
    TELEGRAM_BOT_ADI: 'kamuilanibot', TELEGRAM_BOT_TOKEN: '123456:TEST-TOKEN', OTURUM_SIRRI: 'sir-sir-sir', YONETICI_ANAHTARI: 'yonetici-anahtar',
    ...ek,
  };
}

export async function cagir(env, yontem, yol, { govde, token, origin, basliklar = {}, ctx } = {}) {
  const h = { ...basliklar };
  if (token) h.Authorization = `Bearer ${token}`;
  if (origin) h.Origin = origin;
  if (govde !== undefined) h['Content-Type'] = 'application/json';
  const bekleyen = [];
  const c = ctx || { waitUntil: (p) => bekleyen.push(p) };
  const r = await worker.fetch(new Request(`https://forum-api.kpsstercihi.com${yol}`, { method: yontem, headers: h, body: govde === undefined ? undefined : JSON.stringify(govde) }), env, c);
  await Promise.all(bekleyen);
  let json = null;
  const metin = await r.text();
  try { json = metin ? JSON.parse(metin) : null; } catch { /* json değil */ }
  return { durum: r.status, json, basliklar: r.headers };
}

// yerel ortamda deneme girişiyle üye aç
export async function uyeGirisi(env, rumuz, rol) {
  const e = env.ORTAM === 'yerel' ? env : { ...env, ORTAM: 'yerel' };
  const r = await cagir(e, 'POST', '/giris/deneme', { govde: { rumuz } });
  if (r.durum !== 200) throw new Error(`giris basarisiz: ${r.durum} ${JSON.stringify(r.json)}`);
  if (rol) env.DB.ham.prepare('UPDATE uyeler SET rol = ? WHERE id = ?').run(rol, r.json.uye.id);
  return { token: r.json.oturum, id: r.json.uye.id };
}
// hız sınırlarını aşmadan art arda yazabilmek için üyenin eski kayıtlarını geriye çek
export function zamaniGeriAl(env, uyeId, sn = 3600) {
  env.DB.ham.prepare('UPDATE basliklar SET olusma = olusma - ? WHERE uye_id = ?').run(sn, uyeId);
  env.DB.ham.prepare('UPDATE yanitlar SET olusma = olusma - ? WHERE uye_id = ?').run(sn, uyeId);
}
export function kayitEskit(env, uyeId) {
  env.DB.ham.prepare('UPDATE uyeler SET kayit = kayit - 200000 WHERE id = ?').run(uyeId);
}

export async function telegramImzala(token, alanlar) {
  const satir = Object.keys(alanlar).sort().map((k) => `${k}=${alanlar[k]}`).join('\n');
  return hex(await hmacSha256(await sha256(token), satir));
}

// globalThis.fetch'i geçici değiştir
export function sahteFetch(isleyici) {
  const eski = globalThis.fetch;
  const cagrilar = [];
  globalThis.fetch = async (url, secenek) => { cagrilar.push({ url: String(url), secenek }); return isleyici(String(url), secenek); };
  return { cagrilar, geri: () => { globalThis.fetch = eski; } };
}

export const ORNEK_ILAN = {
  id: `https://kariyerkapisi.gov.tr/IlanDetay?i=${UUID}`,
  kimlikler: [`https://kariyerkapisi.gov.tr/IlanDetay?i=${UUID}`],
  baslik: 'GENÇLİK VE SPOR BAKANLIĞI - 2026 YILI SÖZLEŞMELİ BİLİŞİM PERSONELİ ALIMI',
  kurum: 'GENÇLİK VE SPOR BAKANLIĞI',
  son_tarih: '2026-09-25', son_zaman: '2026-09-25T17:00:00+03:00',
  ogrenim: ['lisans'], iller: [], kategori: 'bilisim', kpss: 'kpss', duyuru_turu: 'ilan',
  sayfa: `https://kpsstercihi.com/ilan/${UUID}/`,
  metin: 'gençlik ve spor bakanlığı sözleşmeli bilişim personeli alımı toplam 9 kişi — 6 yazılım geliştirme uzmanı 2024 yılı kpss b grubu p3 puanının yüzde yetmişi ile yds 35 yaşını doldurmamış olmak',
};
export function ilanSiteFetch(kayitlar = [ORNEK_ILAN]) {
  return sahteFetch(async (url) => {
    if (url.endsWith('bot-ilanlar.json')) return new Response(JSON.stringify({ guncelleme: 'x', ilanlar: kayitlar }), { status: 200 });
    if (url.startsWith('https://api.telegram.org/')) return new Response('{"ok":true}');
    return new Response('yok', { status: 404 });
  });
}
