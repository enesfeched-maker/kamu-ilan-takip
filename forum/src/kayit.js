// Üyelik yöntemleri: rumuz + şifre, kurtarma kodu, Google ile devam et, hesaba bağlı profil.
// index.js ile döngüsel içe aktarma güvenlidir: yardımcılar yalnız istek sırasında çağrılır.
import { jsonYanit, hataYanit, simdi } from './yardimci.js';
import { rumuzDogrula, geciciGoogleUret } from './oturum.js';
import { sifreYapilandirildi, sifreKurali, sifreOzetle, sifreDogrula, kurtarmaKoduUret, kurtarmaOzeti, kurtarmaDogrula } from './sifre.js';
import { ipAnahtari, denemeSinirda, denemeYaz, cokDeneme, KAYIT_SINIRI, GIRIS_IP_SINIRI, GIRIS_RUMUZ_SINIRI } from './hiz.js';
import { googleJetonuDogrula } from './google.js';
import { profilTemizle, profilOku, PROFIL_EN_COK } from './profil.js';
import { govdeOku, oturumUyesi, oturumYaniti, uyeOlustur } from './index.js';

const TURNSTILE_ADRESI = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const GENEL_GIRIS_HATASI = 'Rumuz ya da şifre hatalı.';
const GENEL_KOD_HATASI = 'Rumuz ya da kurtarma kodu hatalı.';
const UYE_ALANLARI = 'id, rumuz, kurucu, rol, itibar, dm_acik, sifre_ozet, kurtarma_ozet';

const yapilandirildi = (env) => !!env.OTURUM_SIRRI && sifreYapilandirildi(env);
const metinMi = (v, en_cok = 200) => typeof v === 'string' && v.length > 0 && v.length <= en_cok;
const rumuzAnahtari = (r) => String(r).trim().toLowerCase();
const uyeBul = (env, rumuz) => env.DB.prepare(`SELECT ${UYE_ALANLARI} FROM uyeler WHERE rumuz = ?`).bind(String(rumuz).trim()).first();

// Herkese açık giriş ayarı: arayüz hangi düğmeleri göstereceğini buradan öğrenir.
export function girisAyari(env) {
  return { turnstile_site: env.TURNSTILE_SITE || '', google_istemci: env.GOOGLE_ISTEMCI_KIMLIGI || '', sifre: yapilandirildi(env) };
}
export const girisAyariYaniti = (env) => jsonYanit(girisAyari(env), 200, { 'Cache-Control': 'public, max-age=300' });

async function turnstileDogrula(env, jeton, request) {
  if (!metinMi(jeton, 2048)) return false;
  const f = new URLSearchParams({ secret: env.TURNSTILE_GIZLI, response: jeton });
  const ip = request.headers.get('CF-Connecting-IP');
  if (ip) f.set('remoteip', ip);
  try {
    const r = await fetch(TURNSTILE_ADRESI, { method: 'POST', body: f });
    const j = await r.json();
    return j && j.success === true;
  } catch { return false; }
}

// Başarısız giriş / sıfırlama denemesi: hem IP hem rumuz sayacı. Sınırdaysa 429 yanıtı döner.
async function denemeKontrol(env, ipA, rumuzA, t) {
  if (await denemeSinirda(env, GIRIS_IP_SINIRI, ipA, t) || (rumuzA && await denemeSinirda(env, GIRIS_RUMUZ_SINIRI, rumuzA, t))) return cokDeneme();
  return null;
}
async function denemeKaydet(env, ipA, rumuzA, t) {
  await denemeYaz(env, GIRIS_IP_SINIRI, ipA, t);
  if (rumuzA) await denemeYaz(env, GIRIS_RUMUZ_SINIRI, rumuzA, t);
}
const sifreliYanit = (env, uye, kod) => oturumYaniti(env, uye, { kurtarma_kodu: kod });

// ---------- POST /kayit ----------
export async function kayit(request, env) {
  if (!yapilandirildi(env)) return hataYanit(503, 'Üyelik henüz yapılandırılmadı.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const t = simdi();
  const ipA = await ipAnahtari(request);
  if (await denemeSinirda(env, KAYIT_SINIRI, ipA, t)) return hataYanit(429, 'Bu bağlantıdan çok fazla üyelik açıldı. Bir saat sonra tekrar dene.');
  const r = rumuzDogrula(g.rumuz);
  if (!r.tamam) return hataYanit(400, r.neden);
  const kural = sifreKurali(g.sifre, r.rumuz);
  if (kural) return hataYanit(400, kural);
  if (env.TURNSTILE_GIZLI && !(await turnstileDogrula(env, g.turnstile, request))) return hataYanit(400, 'Robot kontrolü geçilemedi. Sayfayı yenileyip tekrar dene.');
  const kod = kurtarmaKoduUret();
  const s = await uyeOlustur(env, { sifre_ozet: await sifreOzetle(env, g.sifre), kurtarma_ozet: await kurtarmaOzeti(env, kod) }, r.rumuz);
  if (s.hata) return s.hata;
  await denemeYaz(env, KAYIT_SINIRI, ipA, t);
  return sifreliYanit(env, s.uye, kod);
}

// ---------- POST /giris/sifre ----------
export async function girisSifre(request, env) {
  if (!yapilandirildi(env)) return hataYanit(503, 'Giriş henüz yapılandırılmadı.');
  const g = await govdeOku(request);
  if (!g || !metinMi(g.rumuz, 40) || !metinMi(g.sifre, 200)) return hataYanit(400, 'Rumuz ve şifre yazmalısın.');
  const t = simdi();
  const ipA = await ipAnahtari(request);
  const rumuzA = rumuzAnahtari(g.rumuz);
  const ret = await denemeKontrol(env, ipA, rumuzA, t);
  if (ret) return ret;
  const uye = await uyeBul(env, g.rumuz);
  const dogru = await sifreDogrula(env, g.sifre, uye && uye.sifre_ozet);   // üye yoksa da aynı işi yapar
  if (!uye || !dogru) {
    await denemeKaydet(env, ipA, rumuzA, t);
    return hataYanit(401, GENEL_GIRIS_HATASI);
  }
  return oturumYaniti(env, uye);
}

// ---------- POST /sifre-sifirla ----------
export async function sifreSifirla(request, env) {
  if (!yapilandirildi(env)) return hataYanit(503, 'Şifre sıfırlama henüz yapılandırılmadı.');
  const g = await govdeOku(request);
  if (!g || !metinMi(g.rumuz, 40) || !metinMi(g.kod, 64) || !metinMi(g.yeni_sifre, 200)) return hataYanit(400, 'Rumuz, kurtarma kodu ve yeni şifre yazmalısın.');
  const t = simdi();
  const ipA = await ipAnahtari(request);
  const rumuzA = rumuzAnahtari(g.rumuz);
  const ret = await denemeKontrol(env, ipA, rumuzA, t);
  if (ret) return ret;
  const uye = await uyeBul(env, g.rumuz);
  const dogru = await kurtarmaDogrula(env, g.kod, uye && uye.kurtarma_ozet);
  if (!uye || !dogru) {
    await denemeKaydet(env, ipA, rumuzA, t);
    return hataYanit(401, GENEL_KOD_HATASI);
  }
  const kural = sifreKurali(g.yeni_sifre, uye.rumuz);
  if (kural) return hataYanit(400, kural);
  const kod = kurtarmaKoduUret();
  await env.DB.prepare('UPDATE uyeler SET sifre_ozet = ?, kurtarma_ozet = ? WHERE id = ?').bind(await sifreOzetle(env, g.yeni_sifre), await kurtarmaOzeti(env, kod), uye.id).run();
  return sifreliYanit(env, uye, kod);
}

// Oturumdaki üyenin şifre bilgisi (özetlerle birlikte).
async function benSatiri(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return { hata: hataYanit(401, 'Giriş yapmalısın.') };
  const satir = await env.DB.prepare(`SELECT ${UYE_ALANLARI} FROM uyeler WHERE id = ?`).bind(u.id).first();
  return { uye: satir };
}
// Mevcut şifreyi sınar; başarısızlık rumuz sayacına işlenir. Hata yanıtı ya da null.
async function eskiSifreSina(env, request, uye, sifre) {
  const t = simdi();
  const rumuzA = rumuzAnahtari(uye.rumuz);
  if (await denemeSinirda(env, GIRIS_RUMUZ_SINIRI, rumuzA, t)) return cokDeneme();
  if (!metinMi(sifre, 200) || !(await sifreDogrula(env, sifre, uye.sifre_ozet))) {
    await denemeYaz(env, GIRIS_RUMUZ_SINIRI, rumuzA, t);
    return hataYanit(401, 'Mevcut şifre yanlış.');
  }
  return null;
}

// ---------- POST /ben/sifre ----------
export async function benSifre(request, env) {
  if (!yapilandirildi(env)) return hataYanit(503, 'Şifre henüz yapılandırılmadı.');
  const b = await benSatiri(request, env);
  if (b.hata) return b.hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const uye = b.uye;
  if (uye.sifre_ozet) {
    const ret = await eskiSifreSina(env, request, uye, g.eski);
    if (ret) return ret;
  }
  const kural = sifreKurali(g.yeni, uye.rumuz);
  if (kural) return hataYanit(400, kural);
  const kod = uye.kurtarma_ozet ? null : kurtarmaKoduUret();   // ilk kez şifre ekleyen Telegram/Google üyesine kod verilir
  if (kod) await env.DB.prepare('UPDATE uyeler SET sifre_ozet = ?, kurtarma_ozet = ? WHERE id = ?').bind(await sifreOzetle(env, g.yeni), await kurtarmaOzeti(env, kod), uye.id).run();
  else await env.DB.prepare('UPDATE uyeler SET sifre_ozet = ? WHERE id = ?').bind(await sifreOzetle(env, g.yeni), uye.id).run();
  return jsonYanit(kod ? { tamam: true, kurtarma_kodu: kod } : { tamam: true });
}

// ---------- POST /ben/kurtarma-kodu ----------
export async function benKurtarmaKodu(request, env) {
  if (!yapilandirildi(env)) return hataYanit(503, 'Şifre henüz yapılandırılmadı.');
  const b = await benSatiri(request, env);
  if (b.hata) return b.hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!b.uye.sifre_ozet) return hataYanit(400, 'Önce bir şifre belirlemelisin.');
  const ret = await eskiSifreSina(env, request, b.uye, g.sifre);
  if (ret) return ret;
  const kod = kurtarmaKoduUret();
  await env.DB.prepare('UPDATE uyeler SET kurtarma_ozet = ? WHERE id = ?').bind(await kurtarmaOzeti(env, kod), b.uye.id).run();
  return jsonYanit({ tamam: true, kurtarma_kodu: kod });
}

// ---------- POST /giris/google ----------
export async function girisGoogle(request, env) {
  if (!env.GOOGLE_ISTEMCI_KIMLIGI || !env.OTURUM_SIRRI) return hataYanit(404, 'Google ile giriş kapalı.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const d = await googleJetonuDogrula(env, g.kimlik_jetonu, simdi());
  if (!d.tamam) return hataYanit(401, d.neden === 'eski' ? 'Giriş süresi dolmuş, tekrar dene.' : 'Google girişi doğrulanamadı.');
  const uye = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, dm_acik FROM uyeler WHERE google_sub = ?').bind(d.sub).first();
  if (uye) return oturumYaniti(env, uye);
  return jsonYanit({ yeni: true, gecici: await geciciGoogleUret(env, d.sub, simdi()) });
}

// ---------- hesaba bağlı profil ----------
export async function benProfil(env, uyeId) {
  const s = await env.DB.prepare('SELECT profil FROM uyeler WHERE id = ?').bind(uyeId).first();
  return profilOku(s && s.profil);
}
export async function benProfilKaydet(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  const g = await govdeOku(request);
  if (!g || !('profil' in g)) return hataYanit(400, 'Geçersiz istek.');
  if (g.profil === null) {
    await env.DB.prepare('UPDATE uyeler SET profil = NULL WHERE id = ?').bind(u.id).run();
    return jsonYanit({ profil: null });
  }
  if (JSON.stringify(g.profil).length > PROFIL_EN_COK * 4) return hataYanit(400, 'Profil çok büyük.');
  const p = profilTemizle(g.profil);
  if (!p) return hataYanit(400, 'Profil geçersiz.');
  await env.DB.prepare('UPDATE uyeler SET profil = ? WHERE id = ?').bind(JSON.stringify(p), u.id).run();
  return jsonYanit({ profil: p });
}
