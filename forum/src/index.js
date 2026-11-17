// KPSS Tercihi forum API'si (Cloudflare Worker + D1).
import { KATEGORILER, KATEGORI_KODLARI, jsonYanit, hataYanit, simdi, sabitEsit, gecerliIlanKimligi, avCikti } from './yardimci.js';
import { denetle, temizle } from './denetim.js';
import { oturumUret, oturumCoz, geciciUret, geciciTgKimligi, geciciGoogleKimligi, geciciGoogleEposta, geciciEpostaKimligi, telegramDogrula, rumuzDogrula } from './oturum.js';
import { kayit, girisSifre, girisGoogle, sifreSifirla, benSifre, benKurtarmaKodu, benProfil, benProfilKayitli, benProfilKaydet, benKayitliKaydet, benHesapSil, girisAyari, girisAyariYaniti } from './kayit.js';
import { epostaKod, epostaDogrula, sifirlaEposta, benEposta } from './eposta.js';
import { epostaMaskele } from './epostabicim.js';
import { baslikHizi, yanitHizi, ipSiniri } from './hiz.js';
import { asistanYaniti } from './asistan.js';
import { ilanKaydiGetir } from './ilan.js';
import { yanitBildirimi, anmaBildirimi, takipBildirimi } from './bildirim.js';
import { ozelKonusmalar, ozelKonusma, ozelYeni, ozelGonder, ozelMesajSil, ozelEngelle, engellenenler, ozelSikayet, yonetimOzelSikayetler, ozelOkunmamis } from './ozel.js';
import { takipDegistir, takipMi, benTakipler } from './takip.js';
import { yonetimOzet } from './yonetim-ozet.js';
import { aracYanitSil, aracBaslikSil, aracOzelSil, aracHesapKapat, benArac, kimlikKapaliMi } from './arac.js';
import { rastgelePx } from './kart.js';
import { benTumu, benKartKaydet, benBasvurularKaydet, benKatipGetir, benKatipKaydet, benFotoYukle, benFotoSil, fotoGetir, fotoBildir, yonetimFotoBildirimleri, yonetimFotoKaldir, uyeKartiYaniti } from './kart.js';

const SAYFA_BOYUTU = 20;
const DUZEYLER = new Set(['lisans', 'onlisans', 'ortaogretim', 'ekpss', 'agrubu']);
const SIRALAMALAR = {
  son: 'b.sabit DESC, b.son_hareket DESC',
  yeni: 'b.olusma DESC, b.id DESC',
  populer: 'b.yanit_sayisi DESC, b.son_hareket DESC',
  begenilen: 'b.faydali DESC, b.son_hareket DESC',
};
const KIMLIK_DESENI = /^[A-Za-z0-9_-]{16,64}$/;
const PUAN_TURU_DESENI = /^P\d{1,3}$/;
const ONBELLEK_SN = 45;
const YENI_ONBELLEK_SN = 10;
const BILDIRIM_GUN = 14;

// ---------- giriş noktası ----------
export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin');
    const izinli = kokenIzinli(origin, env);
    if (request.method === 'OPTIONS') {
      return izinli ? new Response(null, { status: 204, headers: corsBasliklari(origin) }) : new Response(null, { status: 403 });
    }
    let yanit;
    try {
      if (origin && !izinli && request.method !== 'GET') yanit = hataYanit(403, 'Köken izinli değil.');
      else yanit = await yonlendir(request, env, ctx);
    } catch (e) {
      console.log('hata:', e && e.message);
      yanit = hataYanit(500, 'Beklenmeyen bir hata oldu.');
    }
    return corsEkle(yanit, origin, izinli);
  },
};

function kokenIzinli(origin, env) {
  if (!origin) return false;
  const liste = String(env.IZINLI_KOKENLER || '').split(',').map((s) => s.trim()).filter(Boolean);
  if (liste.includes(origin)) return true;
  return env.ORTAM === 'yerel' && /^http:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?$/.test(origin);
}
function corsBasliklari(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Yonetici',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}
function corsEkle(yanit, origin, izinli) {
  const h = new Headers(yanit.headers);
  h.append('Vary', 'Origin');
  if (izinli) for (const [k, v] of Object.entries(corsBasliklari(origin))) if (k !== 'Vary') h.set(k, v);
  return new Response(yanit.body, { status: yanit.status, headers: h });
}

const bekle = (ctx, p) => { const s = Promise.resolve(p).catch(() => {}); if (ctx && ctx.waitUntil) ctx.waitUntil(s); };

// ---------- yönlendirme ----------
async function yonlendir(request, env, ctx) {
  const url = new URL(request.url);
  const yol = url.pathname.replace(/\/+$/, '') || '/';
  const yontem = request.method;
  const yazma = yontem !== 'GET' && yontem !== 'HEAD';
  if (yazma && env.YAZMA_KAPALI === '1' && !yol.startsWith('/yonetim')) return hataYanit(503, 'Forum şu an yalnızca okunabiliyor.');
  let m;

  if (yontem === 'GET' || yontem === 'HEAD') {
    if (yol === '/') return new Response('kpss-forum', { headers: { 'Cache-Control': 'no-store' } });
    if (yol === '/kategoriler') return jsonYanit({ kategoriler: KATEGORILER }, 200, { 'Cache-Control': 'public, max-age=300' });
    if (yol === '/giris/ayar') return girisAyariYaniti(env);
    if (yol === '/ben') return benGetir(request, env);
    if (yol === '/ben/bildirimler') return benBildirimler(request, env, url);
    if (yol === '/ben/takipler') return benTakipler(request, env);
    if (yol === '/ben/katip') return benKatipGetir(request, env);
    if (yol === '/ben/arac') return benArac(request, env);
    if ((m = yol.match(/^\/foto\/(\d+)$/))) return fotoGetir(request, env, ctx, url, m[1]);
    if (yol === '/yonetim/foto-bildirimleri') return yonetimFotoBildirimleri(request, env);
    if (yol === '/ben/engellenenler') return engellenenler(request, env);
    if (yol === '/ozel') return ozelKonusmalar(request, env);
    if ((m = yol.match(/^\/ozel\/([^/]+)\/yeni$/))) return ozelYeni(request, env, url, m[1]);
    if ((m = yol.match(/^\/ozel\/([^/]+)$/))) return ozelKonusma(request, env, url, m[1]);
    if (yol === '/yonetim/sikayetler') return yonetimSikayetler(request, env);
    if (yol === '/yonetim/ozel-sikayetler') return yonetimOzelSikayetler(request, env);
    if (yol === '/yonetim/ozet') return yonetimOzet(request, env);
    const anonim = !request.headers.get('Authorization') && !url.searchParams.get('kimlik');
    const onb = (uret) => onbellekli(url, ctx, anonim, uret);
    if (yol === '/basliklar') return onb(() => basliklarListe(env, url));
    if (yol === '/son') return onb(() => sonBasliklar(env));
    if (yol === '/durum') return onb(() => forumDurumu(env));
    if (yol === '/ara') return onb(() => baslikAra(env, url));
    if (yol === '/ozet') return onb(() => ozet(env, url));
    if ((m = yol.match(/^\/baslik\/(\d+)$/))) return onb(() => baslikGetir(request, env, url, Number(m[1])));
    if ((m = yol.match(/^\/baslik\/(\d+)\/yeni$/))) return onbellekli(url, ctx, anonim, () => yeniYanitlar(request, env, url, Number(m[1])), YENI_ONBELLEK_SN);
    if ((m = yol.match(/^\/uye\/([^/]+)$/))) return onb(() => uyeKartiYaniti(request, env, url, m[1]));
    if ((m = yol.match(/^\/ilan\/([^/]+)$/))) return onb(() => ilanGetir(request, env, url, decodeURIComponent(m[1])));
    return hataYanit(404, 'Bulunamadı.');
  }

  if (yontem === 'POST') {
    if (yol === '/giris/telegram') return girisTelegram(request, env);
    if (yol === '/giris/rumuz') return girisRumuz(request, env);
    if (yol === '/giris/deneme') return girisDeneme(request, env);
    if (yol === '/kayit') return kayit(request, env);
    if (yol === '/giris/sifre') return girisSifre(request, env);
    if (yol === '/giris/google') return girisGoogle(request, env);
    if (yol === '/giris/eposta/kod') return epostaKod(request, env, ctx);
    if (yol === '/giris/eposta/dogrula') return epostaDogrula(request, env);
    if (yol === '/sifre-sifirla') return sifreSifirla(request, env);
    if (yol === '/sifre-sifirla/eposta') return sifirlaEposta(request, env, ctx);
    if (yol === '/ben/eposta') return benEposta(request, env, ctx);
    if (yol === '/ben/hesap-sil') return benHesapSil(request, env);
    if (yol === '/ben/sifre') return benSifre(request, env);
    if (yol === '/ben/kurtarma-kodu') return benKurtarmaKodu(request, env);
    if (yol === '/ben/profil') return benProfilKaydet(request, env);
    if (yol === '/ben/kayitli') return benKayitliKaydet(request, env);
    if (yol === '/ben/kart') return benKartKaydet(request, env);
    if (yol === '/ben/basvurular') return benBasvurularKaydet(request, env);
    if (yol === '/ben/katip') return benKatipKaydet(request, env);
    if (yol === '/ben/foto') return benFotoYukle(request, env);
    if ((m = yol.match(/^\/uye\/([^/]+)\/foto-bildir$/))) return fotoBildir(request, env, m[1]);
    if ((m = yol.match(/^\/arac\/uye\/([^/]+)\/kapat$/))) return aracHesapKapat(request, env, m[1]);
    if (yol === '/yonetim/foto-kaldir') return yonetimFotoKaldir(request, env, url);
    if (yol === '/ben/bildirim') return benBildirim(request, env);
    if (yol === '/ben/ayar') return benAyar(request, env);
    if ((m = yol.match(/^\/baslik\/(\d+)\/takip$/))) return takipDegistir(request, env, Number(m[1]));
    if ((m = yol.match(/^\/ozel\/([^/]+)\/engelle$/))) return ozelEngelle(request, env, m[1]);
    if ((m = yol.match(/^\/ozel\/([^/]+)\/sikayet$/))) return ozelSikayet(request, env, m[1]);
    if ((m = yol.match(/^\/ozel\/([^/]+)$/))) return ozelGonder(request, env, ctx, m[1]);
    if (yol === '/baslik') return baslikOlustur(request, env);
    if ((m = yol.match(/^\/baslik\/(\d+)\/yanit$/))) return yanitYaz(request, env, ctx, Number(m[1]));
    if ((m = yol.match(/^\/baslik\/(\d+)\/anket$/))) return anketOyla(request, env, Number(m[1]));
    if ((m = yol.match(/^\/baslik\/(\d+)\/faydali$/))) return baslikFaydaliDegistir(request, env, Number(m[1]));
    if ((m = yol.match(/^\/ilan\/([^/]+)\/yanit$/))) return ilanYanitYaz(request, env, ctx, decodeURIComponent(m[1]));
    if ((m = yol.match(/^\/yanit\/(\d+)\/faydali$/))) return faydaliDegistir(request, env, Number(m[1]));
    if ((m = yol.match(/^\/yanit\/(\d+)\/sikayet$/))) return sikayetEt(request, env, Number(m[1]));
    if ((m = yol.match(/^\/basvuru\/([^/]+)$/))) return basvuruYaz(request, env, decodeURIComponent(m[1]));
    if (yol === '/yonetim/baslik') return yonetimBaslik(request, env);
    if (yol === '/yonetim/gizle') return yonetimGizle(request, env);
    if (yol === '/yonetim/engelle') return yonetimEngelle(request, env);
    return hataYanit(404, 'Bulunamadı.');
  }

  if (yontem === 'DELETE' && yol === '/ben/foto') return benFotoSil(request, env);
  if (yontem === 'DELETE' && (m = yol.match(/^\/arac\/yanit\/(\d+)$/))) return aracYanitSil(request, env, Number(m[1]));
  if (yontem === 'DELETE' && (m = yol.match(/^\/arac\/baslik\/(\d+)$/))) return aracBaslikSil(request, env, Number(m[1]));
  if (yontem === 'DELETE' && (m = yol.match(/^\/arac\/ozel\/(\d+)$/))) return aracOzelSil(request, env, Number(m[1]));
  if (yontem === 'DELETE' && (m = yol.match(/^\/ozel\/mesaj\/(\d+)$/))) return ozelMesajSil(request, env, Number(m[1]));
  if (yontem === 'DELETE' && (m = yol.match(/^\/yanit\/(\d+)$/))) return yanitSil(request, env, Number(m[1]));
  if (yontem === 'DELETE' && (m = yol.match(/^\/basvuru\/([^/]+)$/))) return basvuruSil(request, env, new URL(request.url), decodeURIComponent(m[1]));
  return hataYanit(405, 'Yöntem desteklenmiyor.');
}

async function onbellekli(url, ctx, anonim, uret, sn = ONBELLEK_SN) {
  const c = typeof caches !== 'undefined' ? caches.default : null;
  if (!c || !anonim) return uret();
  const anahtar = new Request(`${url.origin}${url.pathname}${url.search}`);
  const var_ = await c.match(anahtar);
  if (var_) return var_;
  const yanit = await uret();
  if (yanit.status === 200) {
    const h = new Headers(yanit.headers);
    h.set('Cache-Control', `public, max-age=0, s-maxage=${sn}`);
    const k = new Response(yanit.body, { status: 200, headers: h });
    bekle(ctx, c.put(anahtar, k.clone()));
    return k;
  }
  return yanit;
}

// ---------- ortak ----------
export async function govdeOku(request) {
  try {
    const t = await request.text();
    if (t.length > 20000) return null;
    const j = JSON.parse(t || '{}');
    return j && typeof j === 'object' && !Array.isArray(j) ? j : null;
  } catch { return null; }
}
const kullaniciJson = (u) => ({ id: u.id, rumuz: u.rumuz, kurucu: !!u.kurucu, rol: u.rol, itibar: u.itibar || 0, dm_acik: u.dm_acik !== 0, ...avCikti(u, u.id) });

export async function oturumUyesi(request, env) {
  const m = (request.headers.get('Authorization') || '').match(/^Bearer (.+)$/);
  if (!m) return null;
  const j = await oturumCoz(env, m[1], simdi());
  if (!j) return null;
  const uye = await env.DB.prepare(
    'SELECT id, rumuz, kurucu, rol, itibar, bildirim, engelli, kayit, dm_acik, tg_id, oturum_surum, eposta, eposta_dogrulandi, avatar, foto_surum, foto_gun, foto_sayi, foto_yasak, sifre_ozet IS NOT NULL AS sifre_var, google_sub IS NOT NULL AS google_var FROM uyeler WHERE id = ?',
  ).bind(j.id).first();
  // şifre / kurtarma kodu değişince oturum sürümü artar: eski jetonlar geçersiz olur
  return uye && (uye.oturum_surum || 0) === j.surum ? uye : null;
}
export async function yazar(request, env) {
  const uye = await oturumUyesi(request, env);
  if (!uye) return { hata: hataYanit(401, 'Giriş yapmalısın.') };
  if (uye.engelli) return { hata: hataYanit(403, 'Hesabın yazmaya kapatıldı.') };
  return { uye };
}
export function yoneticiMi(request, env) {
  return !!env.YONETICI_ANAHTARI && sabitEsit(request.headers.get('X-Yonetici') || '', env.YONETICI_ANAHTARI);
}
const ayrik = (n) => Math.max(1, Math.min(Number(n) || 1, 100));

// ---------- giriş ----------
export async function oturumYaniti(env, uye, ek = {}) {
  const surum = uye.oturum_surum !== undefined ? uye.oturum_surum : (await env.DB.prepare('SELECT oturum_surum FROM uyeler WHERE id = ?').bind(uye.id).first())?.oturum_surum;
  return jsonYanit({ oturum: await oturumUret(env, uye.id, simdi(), surum || 0), uye: kullaniciJson(uye), ...ek });
}
async function girisTelegram(request, env) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.OTURUM_SIRRI) return hataYanit(503, 'Giriş henüz yapılandırılmadı.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const d = await telegramDogrula(env, g, simdi());
  if (!d.tamam) return hataYanit(401, d.neden === 'eski' ? 'Giriş süresi dolmuş, tekrar dene.' : 'Telegram girişi doğrulanamadı.');
  const uye = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, dm_acik FROM uyeler WHERE tg_id = ?').bind(d.tgId).first();
  if (uye) return oturumYaniti(env, uye);
  return jsonYanit({ yeni: true, gecici: await geciciUret(env, d.tgId, simdi()) });
}
// kimlik: { tg_id } | { google_sub, eposta? } | { eposta } | { sifre_ozet, kurtarma_ozet }. eposta yalnız doğrulanmış adrestir. Şifreli ve Google üyelerinde tg_id NULL kalır
// (UNIQUE sütunda birden çok NULL serbesttir); Telegram bildirimleri tg_id > 0 koşuluyla bu üyeleri atlar.
export async function uyeOlustur(env, kimlik, rumuz) {
  const r = rumuzDogrula(rumuz);
  if (!r.tamam) return { hata: hataYanit(400, r.neden) };
  const var_ = await env.DB.prepare('SELECT id FROM uyeler WHERE rumuz_kat = ? OR rumuz = ?').bind(r.kat, r.rumuz).first();
  if (var_) return { hata: hataYanit(409, 'Bu rumuz alınmış.') };
  const ayrilmis = await env.DB.prepare('SELECT 1 AS x FROM ayrilmis_rumuzlar WHERE kat = ? AND bitis > ?').bind(r.kat, simdi()).first();   // silinen hesabın rumuzu 180 gün ayrılır
  if (ayrilmis) return { hata: hataYanit(409, 'Bu rumuz alınmış.') };
  // yönetici tarafından kapatılmış hesabın Google / Telegram / e-posta kimliğiyle yeniden üyelik açılmaz (yalnız özetler saklanır)
  if (await kimlikKapaliMi(env, kimlik)) return { hata: hataYanit(403, 'Bu hesapla üyelik açılamıyor.') };
  const sayi =await env.DB.prepare("SELECT COUNT(*) AS n FROM uyeler WHERE rol NOT IN ('sistem', 'asistan')").first();
  const t = simdi();
  try {
    // her yeni üye rastgele bir piksel karakterle başlar (istediği zaman değiştirir)
    await env.DB.prepare('INSERT INTO uyeler (tg_id, rumuz, rumuz_kat, kayit, kurucu, google_sub, sifre_ozet, kurtarma_ozet, eposta, eposta_dogrulandi, avatar) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
      .bind(kimlik.tg_id ?? null, r.rumuz, r.kat, t, (sayi?.n || 0) < KURUCU_SINIRI ? 1 : 0, kimlik.google_sub ?? null, kimlik.sifre_ozet ?? null, kimlik.kurtarma_ozet ?? null,
        kimlik.eposta ?? null, kimlik.eposta ? t : null, rastgelePx()).run();
  } catch (e) {
    // yalnız benzersizlik ihlali "rumuz alınmış" demektir (aynı anda iki istek); başka hata gerçek bir arızadır
    if (/UNIQUE constraint failed: uyeler\.eposta/i.test(String(e && e.message))) return { hata: hataYanit(409, 'Bu e-posta adresiyle bir hesap zaten var. Girişi baştan dene.') };
    if (/UNIQUE constraint failed/i.test(String(e && e.message))) return { hata: hataYanit(409, 'Bu rumuz alınmış.') };
    console.error('uyeOlustur:', e && e.message);
    return { hata: hataYanit(500, 'Üyelik şu an oluşturulamadı. Biraz sonra tekrar dene.') };
  }
  const uye = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, dm_acik, oturum_surum, avatar FROM uyeler WHERE rumuz_kat = ?').bind(r.kat).first();
  return { uye };
}
async function girisRumuz(request, env) {
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const tgId = await geciciTgKimligi(env, g.gecici, simdi());
  if (tgId) {
    const mevcut = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, dm_acik FROM uyeler WHERE tg_id = ?').bind(tgId).first();
    if (mevcut) return oturumYaniti(env, mevcut);
    const s = await uyeOlustur(env, { tg_id: tgId }, g.rumuz);
    return s.hata || oturumYaniti(env, s.uye);
  }
  const eposta = await geciciEpostaKimligi(env, g.gecici, simdi());
  if (eposta) {   // e-posta koduyla doğrulanmış yeni üye: rumuz seçince hesap bu adresle açılır
    const var_ = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, dm_acik FROM uyeler WHERE eposta = ?').bind(eposta).first();
    if (var_) return oturumYaniti(env, var_);   // aynı geçici jetonla ikinci üyelik açılmaz
    const s = await uyeOlustur(env, { eposta }, g.rumuz);
    return s.hata || oturumYaniti(env, s.uye);
  }
  const sub = await geciciGoogleKimligi(env, g.gecici, simdi());
  if (!sub) return hataYanit(401, 'Giriş süresi dolmuş, tekrar dene.');
  const mevcut = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, dm_acik FROM uyeler WHERE google_sub = ?').bind(sub).first();
  if (mevcut) return oturumYaniti(env, mevcut);
  let gEposta = await geciciGoogleEposta(env, g.gecici, simdi());
  if (gEposta && await env.DB.prepare('SELECT 1 AS x FROM uyeler WHERE eposta = ?').bind(gEposta).first()) gEposta = null;   // başka hesapta kayıtlıysa yazılmaz
  const s = await uyeOlustur(env, { google_sub: sub, eposta: gEposta || undefined }, g.rumuz);
  return s.hata || oturumYaniti(env, s.uye);
}
function ozetSayi(metin) {
  let h = 2166136261;
  for (let i = 0; i < metin.length; i++) { h ^= metin.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h;
}
async function girisDeneme(request, env) {
  if (env.ORTAM !== 'yerel') return hataYanit(404, 'Bulunamadı.');
  if (!env.OTURUM_SIRRI) return hataYanit(503, 'OTURUM_SIRRI tanımlı değil.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const r = rumuzDogrula(g.rumuz);
  if (!r.tamam) return hataYanit(400, r.neden);
  const mevcut = await env.DB.prepare('SELECT id, rumuz, kurucu, rol, itibar, tg_id, dm_acik FROM uyeler WHERE rumuz_kat = ? OR rumuz = ?').bind(r.kat, r.rumuz).first();
  if (mevcut) return mevcut.tg_id < 0 ? oturumYaniti(env, mevcut) : hataYanit(409, 'Bu rumuz alınmış.');
  const s = await uyeOlustur(env, { tg_id: -(1 + (ozetSayi(r.rumuz.toLowerCase()) % 2000000000)) }, r.rumuz);
  return s.hata || oturumYaniti(env, s.uye);
}
async function benGetir(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  const { profil, kayitli, kart, basvurular } = await benTumu(env, u.id);
  const uye = await benNesnesi(env, u);
  uye.kg = !!(kart && kart.gizlilik && kart.gizlilik.katiplik_goster);   // katiplik sonuçlarım görünür mü: site liderlik tablosuna avatar yalnız açıksa gider
  return jsonYanit({ uye, profil, kayitli, kart, basvurular });
}
async function benNesnesi(env, u) {
  return {
    ...kullaniciJson(u), bildirim: u.bildirim === 1, engelli: !!u.engelli, ozel_okunmamis: await ozelOkunmamis(env, u.id),
    telegram: u.tg_id > 0, sifre_var: !!u.sifre_var, google_var: !!u.google_var,   // hangi giriş yöntemleri bağlı
    eposta: epostaMaskele(u.eposta), eposta_dogrulandi: !!u.eposta && !!u.eposta_dogrulandi,   // adres yalnız maskeli döner (a***@gmail.com)
  };
}
// Ayarlar: dm_acik (özel mesaj alır) ve bildirim (Telegram); en az biri verilmeli. Güncel /ben nesnesini döner.
async function benAyar(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const alanlar = [];
  const deger = [];
  for (const ad of ['dm_acik', 'bildirim']) {
    if (g[ad] === undefined) continue;
    if (typeof g[ad] !== 'boolean') return hataYanit(400, `${ad} alanı true/false olmalı.`);
    alanlar.push(`${ad} = ?`); deger.push(g[ad] ? 1 : 0);
    u[ad] = g[ad] ? 1 : 0;
  }
  if (!alanlar.length) return hataYanit(400, 'dm_acik ya da bildirim verilmeli.');
  await env.DB.prepare(`UPDATE uyeler SET ${alanlar.join(', ')} WHERE id = ?`).bind(...deger, u.id).run();
  return jsonYanit({ uye: await benNesnesi(env, u) });
}
async function benBildirim(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  const g = await govdeOku(request);
  if (!g || typeof g.acik !== 'boolean') return hataYanit(400, 'acik alanı true/false olmalı.');
  await env.DB.prepare('UPDATE uyeler SET bildirim = ? WHERE id = ?').bind(g.acik ? 1 : 0, u.id).run();
  return jsonYanit({ tamam: true, bildirim: g.acik });
}

// ---------- okuma ----------
const BASLIK_ALANLARI = `b.id, b.kategori, b.baslik, b.kaynak, b.sabit, b.olusma, b.son_hareket, b.yanit_sayisi, b.ilan_id, b.govde,
  b.duzey, b.puan_turu, b.puan, b.faydali, b.anket, u.rumuz, u.kurucu, u.rol, u.itibar, u.avatar, u.foto_surum, CASE WHEN u.foto_surum IS NOT NULL THEN u.id END AS fu`;
// liste/özet sorguları: gövdenin yalnız ilk 140 karakteri
export const LISTE_ALANLARI = `b.id, b.kategori, b.baslik, substr(b.govde, 1, 140) AS govde, b.kaynak, b.sabit, b.olusma, b.son_hareket, b.yanit_sayisi, b.ilan_id,
  b.duzey, b.puan_turu, b.puan, b.faydali, b.anket, u.rumuz, u.kurucu, u.rol, u.itibar, u.avatar, u.foto_surum, CASE WHEN u.foto_surum IS NOT NULL THEN u.id END AS fu`;
const KURUCU_SINIRI = 200;   // ilk 200 üye "Kurucu üye" rozeti alır
export function baslikCikti(r, govdeli) {
  const o = {
    id: r.id, kategori: r.kategori, baslik: r.baslik, rumuz: r.rumuz, kurucu: !!r.kurucu, rol: r.rol, itibar: r.itibar || 0, kaynak: r.kaynak,
    sabit: !!r.sabit, olusma: r.olusma, son_hareket: r.son_hareket, yanit_sayisi: r.yanit_sayisi, ilan_id: r.ilan_id,
    duzey: r.duzey ?? null, puan_turu: r.puan_turu ?? null, puan: r.puan ?? null, faydali: r.faydali || 0, anket: !!r.anket, ...avCikti(r),
  };
  if (govdeli) o.govde = r.govde; else o.kisa = String(r.govde || '').slice(0, 140);
  return o;
}
async function basliklarListe(env, url) {
  const kategori = url.searchParams.get('kategori') || '';
  if (kategori && !KATEGORI_KODLARI.has(kategori)) return hataYanit(400, 'Kategori geçersiz.');
  const sayfa = Math.min(Math.max(parseInt(url.searchParams.get('sayfa'), 10) || 1, 1), 100);
  const bag = [];
  let kosul = 'b.gizli = 0';
  if (kategori) { kosul += ' AND b.kategori = ?'; bag.push(kategori); }
  const duzey = url.searchParams.get('duzey') || '';
  if (duzey) {
    if (!DUZEYLER.has(duzey)) return hataYanit(400, 'Düzey geçersiz.');
    kosul += ' AND b.duzey = ?'; bag.push(duzey);
  }
  const sirala = url.searchParams.get('sirala') || 'son';
  if (!Object.hasOwn(SIRALAMALAR, sirala)) return hataYanit(400, 'Sıralama geçersiz.');
  if (url.searchParams.get('bekleyen') === '1') kosul += ' AND b.yanit_sayisi = 0 AND b.sabit = 0';   // henüz yanıtlanmamış sorular
  bag.push(SAYFA_BOYUTU + 1, (sayfa - 1) * SAYFA_BOYUTU);
  const { results } = await env.DB.prepare(
    `SELECT ${LISTE_ALANLARI}
     FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE ${kosul}
     ORDER BY ${SIRALAMALAR[sirala]} LIMIT ? OFFSET ?`,
  ).bind(...bag).all();
  return jsonYanit({ basliklar: results.slice(0, SAYFA_BOYUTU).map((r) => baslikCikti(r, false)), sayfa, sonraki: results.length > SAYFA_BOYUTU });
}
async function sonBasliklar(env) {
  const { results } = await env.DB.prepare(
    `SELECT ${LISTE_ALANLARI}
     FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE b.gizli = 0 ORDER BY b.son_hareket DESC LIMIT 10`,
  ).all();
  return jsonYanit({ basliklar: results.map((r) => baslikCikti(r, false)) });
}
// Türkçe büyük/küçük harf: İ→i, I→ı (ve tersi); SQLite LIKE yalnız ASCII harfte büyük/küçük ayırmaz.
const trKucuk = (s) => s.replace(/İ/g, 'i').replace(/I/g, 'ı').toLowerCase();
const trBuyuk = (s) => s.replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase();
async function baslikAra(env, url) {
  const q = (url.searchParams.get('q') || '').trim();
  if (q.length < 2 || q.length > 60) return hataYanit(400, 'Arama 2-60 karakter olmalı.');
  const kacis = (s) => s.replace(/[\\%_]/g, '\\$&');
  const bicimler = [...new Set([q, trKucuk(q), trBuyuk(q)])].map((s) => `%${kacis(s)}%`);
  const kosul = bicimler.map(() => "(b.baslik LIKE ? ESCAPE '\\' OR b.govde LIKE ? ESCAPE '\\')").join(' OR ');
  const bag = bicimler.flatMap((p) => [p, p]);
  const { results } = await env.DB.prepare(
    `SELECT ${LISTE_ALANLARI}
     FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE b.gizli = 0 AND (${kosul}) ORDER BY b.son_hareket DESC LIMIT 20`,
  ).bind(...bag).all();
  return jsonYanit({ basliklar: results.map((r) => baslikCikti(r, false)) });
}
// Forum sayfasının üst şeridi: üye sayısı, kalan kurucu rozeti, son 24 saatin mesaj ve yazar sayısı (gerçek sayılar; önbellekli).
export async function forumDurumu(env, simdi = Math.floor(Date.now() / 1000)) {
  const u = await env.DB.prepare("SELECT COUNT(*) AS n FROM uyeler WHERE rol NOT IN ('sistem', 'asistan')").first();
  const g = await env.DB.prepare(
    "SELECT COUNT(*) AS mesaj, COUNT(DISTINCT y.uye_id) AS yazar FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id WHERE y.olusma > ? AND y.gizli = 0 AND u.rol NOT IN ('sistem', 'asistan')",
  ).bind(simdi - 86400).first();
  // kategori başına başlık sayısı + bekleyen (yanıtsız, sabit olmayan) sayısı tek GROUP BY ile
  const kt = await env.DB.prepare(
    'SELECT kategori, COUNT(*) AS n, SUM(CASE WHEN yanit_sayisi = 0 AND sabit = 0 THEN 1 ELSE 0 END) AS bekleyen FROM basliklar WHERE gizli = 0 GROUP BY kategori',
  ).all();
  const kategoriler = Object.fromEntries(KATEGORILER.map((k) => [k.kod, 0]));
  let bekleyen = 0;
  for (const r of kt.results) { kategoriler[r.kategori] = r.n; bekleyen += r.bekleyen || 0; }
  const gundem = await env.DB.prepare(
    `SELECT ${LISTE_ALANLARI} FROM basliklar b JOIN uyeler u ON u.id = b.uye_id
     WHERE b.gizli = 0 AND b.son_hareket > ? ORDER BY b.yanit_sayisi DESC, b.son_hareket DESC LIMIT 5`,
  ).bind(simdi - 86400).all();
  // yanıtsız başlıkta son_hareket = olusma olduğundan son_hareket indeksi yeterli
  const bekleyenler = await env.DB.prepare(
    `SELECT ${LISTE_ALANLARI} FROM basliklar b JOIN uyeler u ON u.id = b.uye_id
     WHERE b.gizli = 0 AND b.sabit = 0 AND b.yanit_sayisi = 0 ORDER BY b.son_hareket DESC LIMIT 5`,
  ).all();
  const uye = u?.n || 0;
  return jsonYanit({
    uye, kurucu_kalan: Math.max(0, KURUCU_SINIRI - uye), bugun_mesaj: g?.mesaj || 0, bugun_yazar: g?.yazar || 0,
    kategoriler, bekleyen, giris: girisAyari(env),
    gundem: gundem.results.map((r) => baslikCikti(r, false)),
    bekleyenler: bekleyenler.results.map((r) => baslikCikti(r, false)),
  });
}
async function baslikSatiri(env, kosul, deger) {
  return env.DB.prepare(`SELECT ${BASLIK_ALANLARI} FROM basliklar b JOIN uyeler u ON u.id = b.uye_id WHERE ${kosul} AND b.gizli = 0`).bind(deger).first();
}
function yanitCikti(r, uye, oylar) {
  const o = { id: r.id, govde: r.govde, rumuz: r.rumuz, rol: r.rol, kurucu: !!r.kurucu, itibar: r.itibar || 0, faydali: r.faydali, ust_id: r.ust_id, olusma: r.olusma, ...avCikti(r) };
  if (uye) { o.benim = r.uye_id === uye.id; o.oyladim = oylar.has(r.id); }
  return o;
}
const YANIT_SECIM = `SELECT y.id, y.govde, y.olusma, y.faydali, y.ust_id, y.uye_id, u.rumuz, u.rol, u.kurucu, u.itibar, u.avatar, u.foto_surum, CASE WHEN u.foto_surum IS NOT NULL THEN u.id END AS fu FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id`;
async function oylananlar(env, uye, satirlar) {
  if (!uye || !satirlar.length) return new Set();
  const ilk = satirlar[0].id, son = satirlar[satirlar.length - 1].id;
  const o = await env.DB.prepare('SELECT yanit_id FROM oylar WHERE uye_id = ? AND yanit_id BETWEEN ? AND ?').bind(uye.id, ilk, son).all();
  return new Set(o.results.map((x) => x.yanit_id));
}
// Son `limit` yanıt (once verilirse id < once olanlardan son `limit`), artan id sırasıyla; { yanitlar, daha_eski }.
async function yanitlariGetir(env, baslikId, uye, limit = 200, once = null) {
  const bag = [baslikId];
  let kosul = 'y.baslik_id = ? AND y.gizli = 0';
  if (once !== null) { kosul += ' AND y.id < ?'; bag.push(once); }
  bag.push(limit + 1);
  const { results } = await env.DB.prepare(`${YANIT_SECIM} WHERE ${kosul} ORDER BY y.id DESC LIMIT ?`).bind(...bag).all();
  const daha_eski = results.length > limit;
  const satirlar = results.slice(0, limit).reverse();
  const oylar = await oylananlar(env, uye, satirlar);
  return { yanitlar: satirlar.map((r) => yanitCikti(r, uye, oylar)), daha_eski };
}
async function yanitTek(env, id, uye) {
  const r = await env.DB.prepare(`${YANIT_SECIM} WHERE y.id = ?`).bind(id).first();
  return r ? yanitCikti(r, uye, new Set()) : null;
}
export const negatifsizTamsayi = (s) => (typeof s === 'string' && /^\d{1,15}$/.test(s) ? Number(s) : null);
async function baslikGetir(request, env, url, id) {
  const lim = negatifsizTamsayi(url.searchParams.get('limit'));
  const limit = lim ? Math.min(lim, 200) : 100;
  const onceHam = url.searchParams.get('once');
  const once = onceHam === null ? null : negatifsizTamsayi(onceHam);
  if (onceHam !== null && once === null) return hataYanit(400, 'once geçersiz.');
  const b = await baslikSatiri(env, 'b.id = ?', id);
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  const uye = await oturumUyesi(request, env);
  const baslik = baslikCikti(b, true);
  if (uye) {
    baslik.oyladim = !!(await env.DB.prepare('SELECT 1 AS v FROM baslik_oylar WHERE baslik_id = ? AND uye_id = ?').bind(id, uye.id).first());
    baslik.takip = await takipMi(env, uye.id, id);
  }
  const { yanitlar, daha_eski } = await yanitlariGetir(env, id, uye, limit, once);
  return jsonYanit({ baslik, anket: b.anket ? await anketGetir(env, id, uye) : null, yanitlar, daha_eski });
}
// Artımlı yoklama: sonra'dan büyük yanıtlar (en çok 100) + güncel yanıt sayısı. Tek indeksli sorgu + başlık satırı.
async function yeniYanitlar(request, env, url, id) {
  const sonra = negatifsizTamsayi(url.searchParams.get('sonra'));
  if (sonra === null) return hataYanit(400, 'sonra geçersiz.');
  const b = await env.DB.prepare('SELECT yanit_sayisi FROM basliklar WHERE id = ? AND gizli = 0').bind(id).first();
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  const uye = await oturumUyesi(request, env);
  const { results } = await env.DB.prepare(`${YANIT_SECIM} WHERE y.baslik_id = ? AND y.id > ? AND y.gizli = 0 ORDER BY y.id LIMIT 100`).bind(id, sonra).all();
  const oylar = await oylananlar(env, uye, results);
  return jsonYanit({ yanitlar: results.map((r) => yanitCikti(r, uye, oylar)), yanit_sayisi: b.yanit_sayisi });
}
async function anketGetir(env, baslikId, uye) {
  const { results } = await env.DB.prepare('SELECT sira, metin, oy FROM anket_secenekleri WHERE baslik_id = ? ORDER BY sira').bind(baslikId).all();
  const a = { secenekler: results.map((r) => ({ sira: r.sira, metin: r.metin, oy: r.oy })), toplam: results.reduce((t, r) => t + r.oy, 0) };
  if (uye) {
    const o = await env.DB.prepare('SELECT sira FROM anket_oylari WHERE baslik_id = ? AND uye_id = ?').bind(baslikId, uye.id).first();
    a.benim = o ? o.sira : null;
  }
  return a;
}

function nicelik(sirali, q) {
  const k = (sirali.length - 1) * q, a = Math.floor(k), b = Math.ceil(k);
  return Math.round((sirali[a] + (sirali[b] - sirali[a]) * (k - a)) * 100) / 100;
}
export async function basvuruOzeti(env, ilanId, kimlik) {
  const say = await env.DB.prepare('SELECT COUNT(*) AS n FROM basvurular WHERE ilan_id = ?').bind(ilanId).first();
  const tur = await env.DB.prepare(
    'SELECT puan_turu, COUNT(*) AS c FROM basvurular WHERE ilan_id = ? AND puan IS NOT NULL GROUP BY puan_turu ORDER BY c DESC, puan_turu LIMIT 1',
  ).bind(ilanId).first();
  let puan = null, ben = null;
  if (kimlik) {
    const b = await env.DB.prepare('SELECT puan_turu, puan FROM basvurular WHERE ilan_id = ? AND kimlik = ?').bind(ilanId, kimlik).first();
    if (b) ben = { puan_turu: b.puan_turu, puan: b.puan };
  }
  if (tur && tur.c >= 5) {
    const { results } = await env.DB.prepare('SELECT puan FROM basvurular WHERE ilan_id = ? AND puan_turu = ? AND puan IS NOT NULL ORDER BY puan').bind(ilanId, tur.puan_turu).all();
    const p = results.map((r) => r.puan);
    puan = { adet: p.length, puan_turu: tur.puan_turu, en_dusuk: p[0], ceyrek1: nicelik(p, 0.25), medyan: nicelik(p, 0.5), ceyrek3: nicelik(p, 0.75), en_yuksek: p[p.length - 1] };
    if (ben && ben.puan_turu === tur.puan_turu && ben.puan != null) puan.sira = p.filter((x) => x > ben.puan).length + 1;
  }
  return { sayi: say?.n || 0, puan, ben };
}
async function ilanGetir(request, env, url, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const uye = await oturumUyesi(request, env);
  const b = await baslikSatiri(env, 'b.ilan_id = ?', ilanId);
  let kimlik = url.searchParams.get('kimlik') || '';
  kimlik = uye ? `u${uye.id}` : KIMLIK_DESENI.test(kimlik) ? kimlik : '';
  const baslik = b ? baslikCikti(b, true) : null;
  if (baslik && uye) baslik.takip = await takipMi(env, uye.id, b.id);
  return jsonYanit({
    baslik,
    yanitlar: b ? (await yanitlariGetir(env, b.id, uye, 200)).yanitlar : [],
    basvuru: await basvuruOzeti(env, ilanId, kimlik),
  });
}
async function ozet(env, url) {
  const idler = [...new Set((url.searchParams.get('ilanlar') || '').split(',').map((s) => s.trim()).filter(gecerliIlanKimligi))].slice(0, 100);
  if (!idler.length) return jsonYanit({});
  const yer = idler.map(() => '?').join(',');
  const y = await env.DB.prepare(`SELECT ilan_id, yanit_sayisi FROM basliklar WHERE gizli = 0 AND ilan_id IN (${yer})`).bind(...idler).all();
  const b = await env.DB.prepare(`SELECT ilan_id, COUNT(*) AS n FROM basvurular WHERE ilan_id IN (${yer}) GROUP BY ilan_id`).bind(...idler).all();
  const sonuc = Object.fromEntries(idler.map((i) => [i, { yanit: 0, basvuru: 0 }]));
  for (const r of y.results) sonuc[r.ilan_id].yanit = r.yanit_sayisi;
  for (const r of b.results) sonuc[r.ilan_id].basvuru = r.n;
  return jsonYanit(sonuc);
}

// ---------- yazma: başlık / yanıt ----------
const tekSatir = (s) => temizle(s).replace(/\s+/g, ' ');
export function metinDenetle(metin, en, fazla, ad) {
  const t = temizle(metin);
  if (t.length < en || t.length > fazla) return { hata: hataYanit(400, `${ad} ${en}-${fazla} karakter olmalı.`) };
  const d = denetle(t);
  if (!d.tamam) return { hata: hataYanit(422, d.neden) };
  return { temiz: d.temiz };
}
// Başlık künyesi: düzey, puan türü + puan, anket seçenekleri. { hata } ya da { duzey, puan_turu, puan, secenekler }.
function baslikEkAlanlari(g) {
  const yok = (v) => v === undefined || v === null;
  let duzey = null;
  if (!yok(g.duzey)) {
    if (typeof g.duzey !== 'string' || !DUZEYLER.has(g.duzey)) return { hata: hataYanit(400, 'Düzey geçersiz.') };
    duzey = g.duzey;
  }
  let tur = null, puan = null;
  if (!yok(g.puan_turu) || !yok(g.puan)) {
    const p = Number(g.puan);
    if (typeof g.puan_turu !== 'string' || !PUAN_TURU_DESENI.test(g.puan_turu) || yok(g.puan) || g.puan === '' || typeof g.puan === 'boolean' || !Number.isFinite(p) || p < 40 || p > 100) {
      return { hata: hataYanit(400, 'Puan türü (P3 gibi) ve 40-100 arası puan birlikte gerekli.') };
    }
    tur = g.puan_turu; puan = Math.round(p * 100) / 100;
  }
  let secenekler = null;
  if (!yok(g.anket)) {
    const s = g.anket && typeof g.anket === 'object' && !Array.isArray(g.anket) ? g.anket.secenekler : null;
    if (!Array.isArray(s) || s.length < 2 || s.length > 6) return { hata: hataYanit(400, 'Anketin 2-6 seçeneği olmalı.') };
    secenekler = [];
    for (const x of s) {
      if (typeof x !== 'string') return { hata: hataYanit(400, 'Anket seçeneği metin olmalı.') };
      const d = metinDenetle(tekSatir(x), 1, 80, 'Anket seçeneği');
      if (d.hata) return d;
      secenekler.push(d.temiz);
    }
  }
  return { duzey, puan_turu: tur, puan, secenekler };
}
const anketSecenekleriEkle = (env, baslikId, secenekler) => env.DB.batch(
  secenekler.map((m, i) => env.DB.prepare('INSERT INTO anket_secenekleri (baslik_id, sira, metin) VALUES (?, ?, ?)').bind(baslikId, i + 1, m)),
);
// Yanıt metnindeki "@rumuz" anmaları: en çok 3 farklı (büyük/küçük harf ayrımsız) rumuz.
export function anmalariBul(metin) {
  const bulunan = new Map();
  for (const m of String(metin).matchAll(/(?<![A-Za-z0-9ÇĞİÖŞÜçğıöşü_.])@([A-Za-z0-9ÇĞİÖŞÜçğıöşü_.]{3,21})/g)) {
    const r = m[1].replace(/\.+$/, '');
    if (r.length < 3 || r.length > 20) continue;
    const k = r.toLowerCase();
    if (!bulunan.has(k)) bulunan.set(k, r);
    if (bulunan.size >= 3) break;
  }
  return [...bulunan.values()];
}
async function yanitBildirimleri(env, { baslikId, baslikAdi, kategori, yanitId, yanitlayan, aliciIdleri, metin }) {
  const bildirilen = [];   // bu istekte zaten haber verilenler (başlık sahibi, yanıtlanan, anılanlar): takip bildirimi atlar
  await yanitBildirimi(env, { baslikId, baslikAdi, yanitlayan, aliciIdleri, bildirilen });
  const rumuzlar = anmalariBul(metin);
  if (rumuzlar.length) await anmaBildirimi(env, { baslikId, baslikAdi, yanitId, yanitlayan, rumuzlar, haricIdler: aliciIdleri, bildirilen });
  await takipBildirimi(env, { baslikId, baslikAdi, kategori, yanitlayan, haricIdler: [...aliciIdleri, ...bildirilen] });
}
async function baslikOlustur(request, env) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!KATEGORI_KODLARI.has(g.kategori)) return hataYanit(400, 'Kategori geçersiz.');
  if (g.kategori === 'ilan') return hataYanit(400, 'İlan sorularını ilan sayfasından sorabilirsin.');
  if (g.kategori === 'etkinlik' && uye.rol !== 'yonetici' && uye.rol !== 'sistem') return hataYanit(403, 'Etkinlik başlığını yalnızca yöneticiler açabilir.');
  if (g.kategori === 'oda' && uye.rol !== 'yonetici' && uye.rol !== 'sistem') return hataYanit(403, 'Sohbet odalarını yalnızca yöneticiler açabilir.');
  const b = metinDenetle(tekSatir(g.baslik), 8, 120, 'Başlık');
  if (b.hata) return b.hata;
  const o = metinDenetle(g.govde, 10, 4000, 'Metin');
  if (o.hata) return o.hata;
  const ek = baslikEkAlanlari(g);
  if (ek.hata) return ek.hata;
  const sinir = await baslikHizi(env, uye, simdi());
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const t = simdi();
  const r = await env.DB.prepare(
    "INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, olusma, son_hareket, duzey, puan_turu, puan, anket) VALUES (?, ?, ?, ?, 'uye', ?, ?, ?, ?, ?, ?)",
  ).bind(g.kategori, b.temiz, o.temiz, uye.id, t, t, ek.duzey, ek.puan_turu, ek.puan, ek.secenekler ? 1 : 0).run();
  if (g.kategori !== 'oda') await env.DB.prepare('INSERT OR IGNORE INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)').bind(uye.id, r.meta.last_row_id, t).run();
  if (ek.secenekler) await anketSecenekleriEkle(env, r.meta.last_row_id, ek.secenekler);
  const satir = await baslikSatiri(env, 'b.id = ?', r.meta.last_row_id);
  return jsonYanit({ baslik: baslikCikti(satir, true) }, 201);
}
async function yanitEkle(env, baslikId, uyeId, govde, ustId, t, takipEt = false) {
  const r = await env.DB.batch([
    env.DB.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, ust_id) VALUES (?, ?, ?, ?, ?)').bind(baslikId, uyeId, govde, t, ustId ?? null),
    env.DB.prepare('UPDATE basliklar SET yanit_sayisi = yanit_sayisi + 1, son_hareket = ? WHERE id = ?').bind(t, baslikId),
    ...(takipEt ? [env.DB.prepare('INSERT OR IGNORE INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)').bind(uyeId, baslikId, t)] : []),
  ]);
  return r[0].meta.last_row_id;
}
async function yanitYaz(request, env, ctx, baslikId) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const o = metinDenetle(g.govde, 2, 2000, 'Yanıt');
  if (o.hata) return o.hata;
  const b = await env.DB.prepare('SELECT id, baslik, uye_id, kategori FROM basliklar WHERE id = ? AND gizli = 0').bind(baslikId).first();
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  let ust = null;
  if (g.ust_id !== undefined && g.ust_id !== null) {
    ust = await env.DB.prepare('SELECT id, uye_id FROM yanitlar WHERE id = ? AND baslik_id = ? AND gizli = 0').bind(Number(g.ust_id), baslikId).first();
    if (!ust) return hataYanit(400, 'Yanıtlanan mesaj bulunamadı.');
  }
  const sinir = await yanitHizi(env, uye, simdi(), b.kategori === 'oda');
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const id = await yanitEkle(env, baslikId, uye.id, o.temiz, ust ? ust.id : null, simdi(), b.kategori !== 'oda');
  bekle(ctx, yanitBildirimleri(env, { baslikId, baslikAdi: b.baslik, kategori: b.kategori, yanitId: id, yanitlayan: uye, aliciIdleri: [b.uye_id, ust ? ust.uye_id : 0], metin: o.temiz }));
  return jsonYanit({ yanit: await yanitTek(env, id, uye) }, 201);
}
async function ilanYanitYaz(request, env, ctx, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const o = metinDenetle(g.govde, 2, 2000, 'Yanıt');
  if (o.hata) return o.hata;
  let b = await env.DB.prepare('SELECT id, gizli, baslik FROM basliklar WHERE ilan_id = ?').bind(ilanId).first();
  if (b && b.gizli) return hataYanit(403, 'Bu başlık kapatıldı.');
  const kayit = await ilanKaydiGetir(env, ilanId);
  let ad = null;
  if (!b) {
    if (kayit && kayit.baslik) ad = tekSatir(kayit.baslik).slice(0, 160);
    else {
      const a = metinDenetle(tekSatir(g.ilan_baslik), 8, 160, 'İlan başlığı');
      if (a.hata) return a.hata;
      ad = a.temiz;
    }
    if (ad.length < 8) return hataYanit(400, 'İlan başlığı en az 8 karakter olmalı.');
  }
  const sinir = await yanitHizi(env, uye, simdi());
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const t = simdi();
  if (!b) {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO basliklar (kategori, baslik, govde, uye_id, ilan_id, kaynak, olusma, son_hareket) VALUES ('ilan', ?, '', 1, ?, 'sistem', ?, ?)",
    ).bind(ad, ilanId, t, t).run();
    b = await env.DB.prepare('SELECT id, gizli, baslik FROM basliklar WHERE ilan_id = ?').bind(ilanId).first();
  }
  const soruId = await yanitEkle(env, b.id, uye.id, o.temiz, null, t, true);
  bekle(ctx, yanitBildirimleri(env, { baslikId: b.id, baslikAdi: b.baslik, kategori: 'ilan', yanitId: soruId, yanitlayan: uye, aliciIdleri: [], metin: o.temiz }));
  const yanitlar = [await yanitTek(env, soruId, uye)];
  try {
    const cevap = kayit ? asistanYaniti(o.temiz, kayit) : null;
    if (cevap) {
      const aid = await yanitEkle(env, b.id, 2, cevap, soruId, t);
      yanitlar.push(await yanitTek(env, aid, uye));
    }
  } catch (e) { console.log('asistan hatası:', e && e.message); }
  return jsonYanit({ baslik_id: b.id, yanitlar }, 201);
}

// ---------- faydalı / şikayet ----------
async function faydaliDegistir(request, env, id) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const y = await env.DB.prepare('SELECT id, uye_id FROM yanitlar WHERE id = ? AND gizli = 0').bind(id).first();
  if (!y) return hataYanit(404, 'Yanıt bulunamadı.');
  if (y.uye_id === uye.id) return hataYanit(400, 'Kendi yanıtına oy veremezsin.');
  const ekle = await env.DB.prepare('INSERT OR IGNORE INTO oylar (yanit_id, uye_id) VALUES (?, ?)').bind(id, uye.id).run();
  let oyladim;
  if (ekle.meta.changes > 0) {
    await env.DB.batch([
      env.DB.prepare('UPDATE yanitlar SET faydali = faydali + 1 WHERE id = ?').bind(id),
      itibarDegistir(env, y.uye_id, 1),
    ]);
    oyladim = true;
  } else {
    await env.DB.batch([
      env.DB.prepare('DELETE FROM oylar WHERE yanit_id = ? AND uye_id = ?').bind(id, uye.id),
      env.DB.prepare('UPDATE yanitlar SET faydali = MAX(faydali - 1, 0) WHERE id = ?').bind(id),
      itibarDegistir(env, y.uye_id, -1),
    ]);
    oyladim = false;
  }
  const s = await env.DB.prepare('SELECT faydali FROM yanitlar WHERE id = ?').bind(id).first();
  return jsonYanit({ faydali: s.faydali, oyladim });
}
// Yazarın itibarı ±1 (0'ın altına inmez; sistem ve asistan hesaplarına dokunmaz).
const itibarDegistir = (env, uyeId, fark) => env.DB.prepare(
  "UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) + ?, 0) WHERE id = ? AND rol NOT IN ('sistem', 'asistan')",
).bind(fark, uyeId);
async function baslikFaydaliDegistir(request, env, id) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const b = await env.DB.prepare('SELECT id, uye_id FROM basliklar WHERE id = ? AND gizli = 0').bind(id).first();
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  if (b.uye_id === uye.id) return hataYanit(400, 'Kendi başlığına oy veremezsin.');
  const ekle = await env.DB.prepare('INSERT OR IGNORE INTO baslik_oylar (baslik_id, uye_id) VALUES (?, ?)').bind(id, uye.id).run();
  const oyladim = ekle.meta.changes > 0;
  await env.DB.batch(oyladim ? [
    env.DB.prepare('UPDATE basliklar SET faydali = faydali + 1 WHERE id = ?').bind(id),
    itibarDegistir(env, b.uye_id, 1),
  ] : [
    env.DB.prepare('DELETE FROM baslik_oylar WHERE baslik_id = ? AND uye_id = ?').bind(id, uye.id),
    env.DB.prepare('UPDATE basliklar SET faydali = MAX(faydali - 1, 0) WHERE id = ?').bind(id),
    itibarDegistir(env, b.uye_id, -1),
  ]);
  const s = await env.DB.prepare('SELECT faydali FROM basliklar WHERE id = ?').bind(id).first();
  return jsonYanit({ faydali: s.faydali, oyladim });
}
async function anketOyla(request, env, id) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g || !Number.isInteger(g.sira)) return hataYanit(400, 'Geçersiz istek.');
  const b = await env.DB.prepare('SELECT id, anket FROM basliklar WHERE id = ? AND gizli = 0').bind(id).first();
  if (!b || !b.anket) return hataYanit(404, 'Anket bulunamadı.');
  const sec = await env.DB.prepare('SELECT sira FROM anket_secenekleri WHERE baslik_id = ? AND sira = ?').bind(id, g.sira).first();
  if (!sec) return hataYanit(400, 'Seçenek geçersiz.');
  const ekle = await env.DB.prepare('INSERT OR IGNORE INTO anket_oylari (baslik_id, uye_id, sira) VALUES (?, ?, ?)').bind(id, uye.id, g.sira).run();
  if (ekle.meta.changes === 0) return hataYanit(409, 'Bu ankette oyun var.');
  await env.DB.prepare('UPDATE anket_secenekleri SET oy = oy + 1 WHERE baslik_id = ? AND sira = ?').bind(id, g.sira).run();
  return jsonYanit(await anketGetir(env, id, uye));
}
async function yanitGizle(env, id, gizli) {
  const y = await env.DB.prepare('SELECT baslik_id, gizli FROM yanitlar WHERE id = ?').bind(id).first();
  if (!y || (y.gizli === 1) === gizli) return false;
  await env.DB.batch([
    env.DB.prepare('UPDATE yanitlar SET gizli = ? WHERE id = ?').bind(gizli ? 1 : 0, id),
    env.DB.prepare('UPDATE basliklar SET yanit_sayisi = MAX(yanit_sayisi + ?, 0) WHERE id = ?').bind(gizli ? -1 : 1, y.baslik_id),
  ]);
  return true;
}
async function sikayetEt(request, env, id) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const y = await env.DB.prepare('SELECT id, sikayet, gizli FROM yanitlar WHERE id = ?').bind(id).first();
  if (!y || y.gizli) return hataYanit(404, 'Yanıt bulunamadı.');
  const ekle = await env.DB.prepare('INSERT OR IGNORE INTO sikayetler (yanit_id, uye_id) VALUES (?, ?)').bind(id, uye.id).run();
  if (ekle.meta.changes === 0) return jsonYanit({ tamam: true, zaten: true });
  const yeni = y.sikayet + 1;
  await env.DB.prepare('UPDATE yanitlar SET sikayet = ? WHERE id = ?').bind(yeni, id).run();
  let gizlendi = false;
  if (yeni >= 3) gizlendi = await yanitGizle(env, id, true);
  return jsonYanit({ tamam: true, gizlendi });
}

// ---------- başvuru ----------
async function basvuruKimligi(request, env, kaynak) {
  const uye = await oturumUyesi(request, env);
  if (uye) return uye.engelli ? null : `u${uye.id}`;
  return typeof kaynak === 'string' && KIMLIK_DESENI.test(kaynak) ? kaynak : null;
}
async function basvuruYaz(request, env, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!ipSiniri(request.headers.get('CF-Connecting-IP'), simdi())) return hataYanit(429, 'Çok fazla istek.');
  const kimlik = await basvuruKimligi(request, env, g.kimlik);
  if (!kimlik) return hataYanit(400, 'Kimlik geçersiz.');
  let tur = null, puan = null;
  if (g.puan_turu !== undefined || g.puan !== undefined) {
    const p = Number(g.puan);
    if (typeof g.puan_turu !== 'string' || !PUAN_TURU_DESENI.test(g.puan_turu) || g.puan === null || g.puan === '' || !Number.isFinite(p) || p < 40 || p > 100) {
      return hataYanit(400, 'Puan türü (P3 gibi) ve 40-100 arası puan gerekli.');
    }
    tur = g.puan_turu; puan = Math.round(p * 100) / 100;
  }
  await env.DB.prepare(
    `INSERT INTO basvurular (ilan_id, kimlik, puan_turu, puan, olusma) VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(ilan_id, kimlik) DO UPDATE SET puan_turu = COALESCE(excluded.puan_turu, puan_turu), puan = COALESCE(excluded.puan, puan)`,
  ).bind(ilanId, kimlik, tur, puan, simdi()).run();
  return jsonYanit({ tamam: true, basvuru: await basvuruOzeti(env, ilanId, kimlik) });
}
async function basvuruSil(request, env, url, ilanId) {
  if (!gecerliIlanKimligi(ilanId)) return hataYanit(400, 'İlan kimliği geçersiz.');
  const kimlik = await basvuruKimligi(request, env, url.searchParams.get('kimlik'));
  if (!kimlik) return hataYanit(400, 'Kimlik geçersiz.');
  await env.DB.prepare('DELETE FROM basvurular WHERE ilan_id = ? AND kimlik = ?').bind(ilanId, kimlik).run();
  return jsonYanit({ tamam: true, basvuru: await basvuruOzeti(env, ilanId, kimlik) });
}

// ---------- yönetim ----------
async function yonetimBaslik(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  if (!KATEGORI_KODLARI.has(g.kategori) || g.kategori === 'ilan') return hataYanit(400, 'Kategori geçersiz.');
  const kaynak = g.kaynak === 'telegram' ? 'telegram' : g.kaynak === 'sistem' || g.kaynak === undefined ? 'sistem' : null;
  if (!kaynak) return hataYanit(400, 'Kaynak sistem ya da telegram olmalı.');
  const baslik = tekSatir(g.baslik), govde = temizle(g.govde);
  if (baslik.length < 8 || baslik.length > 120 || govde.length < 10 || govde.length > 4000) return hataYanit(400, 'Başlık 8-120, metin 10-4000 karakter olmalı.');
  const ek = baslikEkAlanlari(g);
  if (ek.hata) return ek.hata;
  const t = simdi();
  const r = await env.DB.prepare(
    'INSERT INTO basliklar (kategori, baslik, govde, uye_id, kaynak, sabit, olusma, son_hareket, duzey, puan_turu, puan, anket) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)',
  ).bind(g.kategori, baslik, govde, kaynak, g.sabit ? 1 : 0, t, t, ek.duzey, ek.puan_turu, ek.puan, ek.secenekler ? 1 : 0).run();
  if (ek.secenekler) await anketSecenekleriEkle(env, r.meta.last_row_id, ek.secenekler);
  return jsonYanit({ baslik: baslikCikti(await baslikSatiri(env, 'b.id = ?', r.meta.last_row_id), true) }, 201);
}
async function yonetimGizle(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const g = await govdeOku(request);
  if (!g || !Number.isInteger(g.id) || typeof g.gizli !== 'boolean') return hataYanit(400, 'Geçersiz istek.');
  if (g.tur === 'baslik') {
    await env.DB.prepare('UPDATE basliklar SET gizli = ? WHERE id = ?').bind(g.gizli ? 1 : 0, g.id).run();
  } else if (g.tur === 'yanit') {
    await yanitGizle(env, g.id, g.gizli);
  } else return hataYanit(400, 'tur baslik ya da yanit olmalı.');
  return jsonYanit({ tamam: true });
}
async function yonetimEngelle(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const g = await govdeOku(request);
  if (!g || !Number.isInteger(g.uye_id) || typeof g.engelli !== 'boolean') return hataYanit(400, 'Geçersiz istek.');
  await env.DB.prepare("UPDATE uyeler SET engelli = ? WHERE id = ? AND silindi IS NULL AND rol NOT IN ('sistem', 'asistan')").bind(g.engelli ? 1 : 0, g.uye_id).run();
  return jsonYanit({ tamam: true });
}
async function yonetimSikayetler(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const { results } = await env.DB.prepare(
    `SELECT y.id, y.baslik_id, y.govde, y.sikayet, y.gizli, y.olusma, y.uye_id, u.rumuz FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id
     WHERE y.sikayet > 0 ORDER BY y.sikayet DESC, y.id DESC LIMIT 100`,
  ).all();
  return jsonYanit({ yanitlar: results.map((r) => ({ ...r, gizli: !!r.gizli })) });
}

// ---------- yanıt silme (kendi mesajını gizle) ----------
async function yanitSil(request, env, id) {
  const uye = await oturumUyesi(request, env);
  if (!uye) return hataYanit(401, 'Giriş yapmalısın.');
  const y = await env.DB.prepare('SELECT y.id, y.uye_id, y.gizli, u.rol AS yazar_rol FROM yanitlar y JOIN uyeler u ON u.id = y.uye_id WHERE y.id = ?').bind(id).first();
  if (!y || y.gizli) return hataYanit(404, 'Yanıt bulunamadı.');
  const yonetici = uye.rol === 'yonetici' || yoneticiMi(request, env);
  const sistemYazari = y.yazar_rol === 'sistem' || y.yazar_rol === 'asistan';
  const izin = yonetici || (!sistemYazari && y.uye_id === uye.id && !uye.engelli);
  if (!izin) return hataYanit(403, 'Bu mesajı silemezsin.');
  await yanitGizle(env, id, true);
  return jsonYanit({ tamam: true });
}

// ---------- uygulama içi bildirimler ----------
const ONCELIK = { takip: 0, yanit: 1, anma: 2, alinti: 3 };
const kisalt = (s) => String(s || '').slice(0, 90);
const BILDIRIM_SECIM = `SELECT y.id AS yanit_id, y.baslik_id, y.govde, y.olusma, b.baslik, b.kategori, u.rumuz, u.rol, u.avatar, u.foto_surum, CASE WHEN u.foto_surum IS NOT NULL THEN u.id END AS fu
  FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id JOIN uyeler u ON u.id = y.uye_id`;
async function benBildirimler(request, env, url) {
  const uye = await oturumUyesi(request, env);
  if (!uye) return hataYanit(401, 'Giriş yapmalısın.');
  const t = simdi();
  const alt = t - BILDIRIM_GUN * 86400;
  const ham = url.searchParams.get('sonra');
  let esik = alt;
  if (ham !== null && ham !== '') {
    const s = negatifsizTamsayi(ham);
    if (s === null) return hataYanit(400, 'sonra geçersiz.');
    esik = Math.max(s, alt);
  }
  const bulunan = new Map();   // yanit_id -> { tur, r }
  const ekle = (tur, satirlar) => {
    for (const r of satirlar) {
      const var_ = bulunan.get(r.yanit_id);
      if (!var_ || ONCELIK[tur] > ONCELIK[var_.tur]) bulunan.set(r.yanit_id, { tur, r });
    }
  };
  // alıntı: üyenin yanıtlarına ust_id ile bağlanan yanıtlar
  const a = await env.DB.prepare(
    `${BILDIRIM_SECIM} JOIN yanitlar p ON p.id = y.ust_id
     WHERE p.uye_id = ? AND y.olusma > ? AND y.uye_id <> ? AND y.gizli = 0 AND b.gizli = 0 ORDER BY y.id DESC LIMIT 30`,
  ).bind(uye.id, esik, uye.id).all();
  ekle('alinti', a.results);
  // yanıt: üyenin açtığı başlıklardaki yanıtlar
  const y = await env.DB.prepare(
    `${BILDIRIM_SECIM} WHERE b.uye_id = ? AND y.olusma > ? AND y.uye_id <> ? AND y.gizli = 0 AND b.gizli = 0 ORDER BY y.id DESC LIMIT 30`,
  ).bind(uye.id, esik, uye.id).all();
  ekle('yanit', y.results);
  // anma: SQLite LIKE ASCII dışında büyük/küçük ayırır; üç yazım aranır, sonra JS'te Türkçe duyarlı doğrulanır
  const kacis = (s) => s.replace(/[\\%_]/g, '\\$&');
  const bicimler = [...new Set([uye.rumuz, trKucuk(uye.rumuz), trBuyuk(uye.rumuz)])].map((s) => `%@${kacis(s)}%`);
  const kosul = bicimler.map(() => "y.govde LIKE ? ESCAPE '\\'").join(' OR ');
  const n = await env.DB.prepare(
    `${BILDIRIM_SECIM} WHERE y.olusma > ? AND y.uye_id <> ? AND y.gizli = 0 AND b.gizli = 0 AND (${kosul}) ORDER BY y.id DESC LIMIT 60`,
  ).bind(esik, uye.id, ...bicimler).all();
  const benim = trKucuk(uye.rumuz);
  ekle('anma', n.results.filter((r) => anmalariBul(r.govde).some((x) => trKucuk(x) === benim)));
  // takip: takip edilen başlıklardaki başkalarının yanıtları (en düşük öncelik)
  const tk = await env.DB.prepare(
    `${BILDIRIM_SECIM} JOIN takipler t ON t.baslik_id = y.baslik_id AND t.uye_id = ?
     WHERE y.olusma > ? AND y.uye_id <> ? AND y.gizli = 0 AND b.gizli = 0 ORDER BY y.id DESC LIMIT 30`,
  ).bind(uye.id, esik, uye.id).all();
  ekle('takip', tk.results);
  const bildirimler = [...bulunan.values()]
    .sort((x, z) => z.r.yanit_id - x.r.yanit_id).slice(0, 30)
    .map(({ tur, r }) => ({ tur, baslik_id: r.baslik_id, baslik: r.baslik, yanit_id: r.yanit_id, rumuz: r.rumuz, rol: r.rol, kisa: kisalt(r.govde), olusma: r.olusma, oda: r.kategori === 'oda', ...avCikti(r) }));
  return jsonYanit({ bildirimler, simdi: t });
}

// ---------- herkese açık üye kartı ----------
// Yol parçasından üye satırı (yasaklı dahil; çağıran karar verir). rumuz sütunu ASCII'de büyük/küçük duyarsız;
// Türkçe harfler için ek yazımlar (küçük, BÜYÜK, İlk harf büyük) da denenir.
export async function uyeRumuzla(env, ham) {
  let rumuz;
  try { rumuz = decodeURIComponent(ham); } catch { return null; }
  const kucuk = trKucuk(rumuz), buyuk = trBuyuk(rumuz), ilkBuyuk = trBuyuk(kucuk.slice(0, 1)) + kucuk.slice(1);
  const adaylar = [...new Set([rumuz, kucuk, buyuk, ilkBuyuk])].slice(0, 4);
  return env.DB.prepare(`SELECT id, rumuz, rol, kurucu, itibar, kayit, engelli, dm_acik, tg_id, bildirim, avatar, foto_surum, kart, profil FROM uyeler WHERE rumuz IN (${adaylar.map(() => '?').join(',')}) ORDER BY rumuz = ? DESC LIMIT 1`).bind(...adaylar, rumuz).first();
}
