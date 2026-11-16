// E-posta ile giriş: 6 haneli kod, Brevo (işleyen) üzerinden gönderilir.
//  - Kodun ve adresin kendisi veritabanında tutulmaz (eposta_kodlari: yalnız biberli özetler). Adres yalnız doğrulanınca üye satırına yazılır.
//  - Hesap var mı yok mu, yanıttan anlaşılmaz: kod isteği ve şifre sıfırlama isteği her durumda aynı yanıtı verir.
//  - Brevo ücretsiz planı hesap genelinde günde 300 e-posta: UTC gün sayacı 280'de durur (eposta_gunluk).
//  - Yalnız ORTAM=yerel iken ve BREVO_ANAHTARI yokken kod gerçekten gönderilmez, konsola yazılır (yerel deneme).
// index.js / kayit.js ile döngüsel içe aktarma güvenlidir: yardımcılar yalnız istek sırasında çağrılır.
import { jsonYanit, hataYanit, simdi, sabitEsit } from './yardimci.js';
import { rumuzKat, geciciEpostaUret } from './oturum.js';
import { sifreYapilandirildi, biberliOzet } from './sifre.js';
import {
  denemeSinirda, denemeYaz, cokDeneme, ipSiniri,
  EPOSTA_IP_SINIRI, EPOSTA_ADRES_SINIRI, SIFIRLA_SAAT_SINIRI, SIFIRLA_BEKLEME, GIRIS_IP_SINIRI,
} from './hiz.js';
import { epostaNormalle, epostaMaskele } from './epostabicim.js';
import { kabaSinir, turnstileDogrula, UYE_ALANLARI, uyeBul } from './kayit.js';
import { govdeOku, oturumUyesi, oturumYaniti } from './index.js';

const BREVO_ADRESI = 'https://api.brevo.com/v3/smtp/email';
export const KOD_OMRU = 600;             // 10 dakika
export const KOD_DENEME = 5;             // kod başına en çok 5 doğrulama denemesi
export const YENIDEN_BEKLEME = 60;       // aynı adrese iki gönderim arası en az 60 sn
export const GUNLUK_SINIR = 280;         // Brevo ücretsiz plan günde 300; pay bırakılır
const KAPALI = 'E-posta ile giriş şu an kapalı. Google ya da rumuzla devam edebilirsin.';
export const GUNLUK_DOLU = 'Şu an e-posta gönderemiyoruz, Google ya da rumuzla devam edebilirsin.';
const KOD_HATASI = 'Kod hatalı ya da süresi dolmuş. Yeni bir kod isteyebilirsin.';
const KOD_COK_HATA = 'Çok fazla yanlış deneme. Yeni bir kod iste.';
const ROBOT_HATASI = 'Robot kontrolü geçilemedi. Sayfayı yenileyip tekrar dene.';

// E-posta özelliği: biber (özetler için) + oturum sırrı + (Brevo anahtarı ya da yerel geliştirme kipi).
export const yerelGelistirme = (env) => env.ORTAM === 'yerel' && !env.BREVO_ANAHTARI;
export function epostaAcik(env) {
  return !!env.OTURUM_SIRRI && sifreYapilandirildi(env) && (!!env.BREVO_ANAHTARI || env.ORTAM === 'yerel');
}

// 6 haneli, düzgün dağılımlı kod (mod yanlılığı yok: aralık dışı değerler yeniden çekilir).
export function kodUret() {
  const sinir = 4294967296 - (4294967296 % 1000000);
  const b = new Uint32Array(1);
  do { crypto.getRandomValues(b); } while (b[0] >= sinir);
  return String(b[0] % 1000000).padStart(6, '0');
}
const kodBicimi = (k) => {
  const s = String(k ?? '').replace(/[\s-]/g, '');
  return /^\d{6}$/.test(s) ? s : null;
};

// ---------- e-posta içeriği (düz metin + sade HTML; görsel ve izleme pikseli yok) ----------
const AMAC_METNI = {
  giris: ['KPSS Tercihi giriş kodun', 'Giriş kodun'],
  sifirla: ['KPSS Tercihi şifre sıfırlama kodun', 'Şifre sıfırlama kodun'],
  degistir: ['KPSS Tercihi e-posta doğrulama kodun', 'E-posta doğrulama kodun'],
};
export function epostaIcerigi(amac, kod) {
  const [baslik, ad] = AMAC_METNI[amac] || AMAC_METNI.giris;
  const alt = '10 dakika geçerli. Bu isteği sen yapmadıysan bu e-postayı yok say.';
  return {
    konu: `${baslik}: ${kod}`,
    metin: `${ad}: ${kod}. ${alt}`,
    html: `<!doctype html><html lang="tr"><head><meta charset="utf-8"></head><body style="margin:0;padding:24px;font-family:Arial,Helvetica,sans-serif;color:#1a1a1a">`
      + `<p style="margin:0 0 12px;font-size:16px">${ad}:</p>`
      + `<p style="margin:0 0 12px;font-size:28px;font-weight:700;letter-spacing:4px">${kod}</p>`
      + `<p style="margin:0;font-size:14px;color:#444">${alt}</p></body></html>`,
  };
}

// Brevo işlemsel e-posta API'si. Başarılıysa true. Hata ayrıntısı (adres içerebilir) loga yazılmaz, yalnız durum kodu.
export async function epostaGonder(env, alici, amac, kod) {
  if (yerelGelistirme(env)) {
    console.log(`[eposta-gelistirme] ${amac} kodu (${alici}): ${kod}`);   // yalnız ORTAM=yerel ve BREVO_ANAHTARI yok
    return true;
  }
  if (!env.BREVO_ANAHTARI) return false;
  const { konu, metin, html } = epostaIcerigi(amac, kod);
  try {
    const r = await fetch(BREVO_ADRESI, {
      method: 'POST',
      headers: { 'api-key': env.BREVO_ANAHTARI, 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        sender: { name: 'KPSS Tercihi', email: env.EPOSTA_GONDEREN || 'bildirim@kpsstercihi.com' },
        to: [{ email: alici }],
        subject: konu, textContent: metin, htmlContent: html,
      }),
    });
    if (!r.ok) console.log('eposta: Brevo durumu', r.status);
    return r.ok;
  } catch { console.log('eposta: Brevo erişilemedi'); return false; }
}

// ---------- günlük sayaç (UTC gün) ----------
const gunAdi = (t) => new Date(t * 1000).toISOString().slice(0, 10);
export async function gunlukDolu(env, t) {
  const s = await env.DB.prepare('SELECT n FROM eposta_gunluk WHERE gun = ?').bind(gunAdi(t)).first();
  return (s?.n || 0) >= GUNLUK_SINIR;
}
// Bir gönderim hakkı ayırır (ilk yazma çoğu zaman tek istektir). Sınırdaysa false.
export async function gunlukAyir(env, t) {
  const gun = gunAdi(t);
  const g = await env.DB.prepare('UPDATE eposta_gunluk SET n = n + 1 WHERE gun = ? AND n < ?').bind(gun, GUNLUK_SINIR).run();
  if ((g.meta?.changes || 0) === 1) return true;
  const e = await env.DB.prepare('INSERT OR IGNORE INTO eposta_gunluk (gun, n) VALUES (?, 1)').bind(gun).run();
  if ((e.meta?.changes || 0) === 1) {
    await env.DB.prepare('DELETE FROM eposta_gunluk WHERE gun < ?').bind(gunAdi(t - 7 * 86400)).run();   // yeni gün: eski günler silinir
    return true;
  }
  return false;
}
async function gunlukIade(env, t) {
  await env.DB.prepare('UPDATE eposta_gunluk SET n = MAX(0, n - 1) WHERE gun = ?').bind(gunAdi(t)).run();
}

// ---------- kod satırı ----------
// amac + parçalar: 'giris' [adres] | 'degistir' [uyeId, adres] | 'sifirla' [uyeId]
export const kodAnahtari = (env, amac, ...parcalar) => biberliOzet(env, 'kod', `${amac}:${parcalar.join(':')}`);
const kodOzeti = (env, anahtar, kod) => biberliOzet(env, 'kodozet', `${anahtar}:${kod}`);

async function kodYaz(env, anahtar, kod, t) {
  await env.DB.prepare(
    'INSERT INTO eposta_kodlari (anahtar, kod_ozet, bitis, deneme, son_gonderim) VALUES (?, ?, ?, 0, ?) '
    + 'ON CONFLICT(anahtar) DO UPDATE SET kod_ozet = excluded.kod_ozet, bitis = excluded.bitis, deneme = 0, son_gonderim = excluded.son_gonderim',
  ).bind(anahtar, await kodOzeti(env, anahtar, kod), t + KOD_OMRU, t).run();
  if (Math.random() < 0.01) {   // Worker'da zamanlayıcı yok: yazmaların ~%1'inde fırsat temizliği
    await env.DB.prepare('DELETE FROM eposta_kodlari WHERE rowid IN (SELECT rowid FROM eposta_kodlari WHERE bitis < ? LIMIT 200)').bind(t - 3600).run();
  }
}
async function kodSil(env, anahtar) {
  await env.DB.prepare('DELETE FROM eposta_kodlari WHERE anahtar = ?').bind(anahtar).run();
}

// 'tamam' (kod tüketildi) | 'yanlis' | 'cok' (deneme hakkı bitti). Doğru kod tek kullanımlıktır (silme tek atomik adım).
export async function kodDogrula(env, anahtar, kod, t) {
  const k = kodBicimi(kod);
  const s = await env.DB.prepare('SELECT kod_ozet, bitis, deneme FROM eposta_kodlari WHERE anahtar = ?').bind(anahtar).first();
  if (!s || s.bitis <= t) { if (k) await kodOzeti(env, anahtar, k); return 'yanlis'; }   // yokken de aynı işi yap
  if ((s.deneme || 0) >= KOD_DENEME) return 'cok';
  if (!k || !sabitEsit(await kodOzeti(env, anahtar, k), s.kod_ozet)) {
    await env.DB.prepare('UPDATE eposta_kodlari SET deneme = deneme + 1 WHERE anahtar = ?').bind(anahtar).run();
    return (s.deneme || 0) + 1 >= KOD_DENEME ? 'cok' : 'yanlis';
  }
  const r = await env.DB.prepare('DELETE FROM eposta_kodlari WHERE anahtar = ? AND kod_ozet = ? AND bitis > ? AND deneme < ?').bind(anahtar, s.kod_ozet, t, KOD_DENEME).run();
  return (r.meta?.changes || 0) === 1 ? 'tamam' : 'yanlis';
}
const kodHatasi = (sonuc) => (sonuc === 'cok' ? hataYanit(429, KOD_COK_HATA) : hataYanit(400, KOD_HATASI));

// Kodu üretip kaydeder ve gönderir. Başarısızsa kayıt ve günlük hak geri alınır. Dönen: true | hata yanıtı.
async function uretVeGonder(env, anahtar, alici, amac, t) {
  const kod = kodUret();
  await kodYaz(env, anahtar, kod, t);
  if (await epostaGonder(env, alici, amac, kod)) return true;
  await kodSil(env, anahtar);
  await gunlukIade(env, t);
  return hataYanit(502, 'Kod gönderilemedi. Biraz sonra tekrar dene.');
}
const gonderildi = () => jsonYanit({ tamam: true, bekle: YENIDEN_BEKLEME });

// Ortak gönderim yolu (giriş ve e-posta ekleme/değiştirme). Her adres için aynı denetimler; hesap varlığına bakılmaz.
async function kodIstegi(env, { amac, eposta, parcalar, ipA, t }) {
  if (await denemeSinirda(env, EPOSTA_IP_SINIRI, ipA, t)) return hataYanit(429, 'Bu bağlantıdan çok fazla kod istendi. Bir saat sonra tekrar dene.');
  const adresA = await biberliOzet(env, 'eposta-adres', eposta);
  if (await denemeSinirda(env, EPOSTA_ADRES_SINIRI, adresA, t)) return hataYanit(429, 'Bu adrese çok fazla kod gönderildi. Bir saat sonra tekrar dene.');
  const anahtar = await kodAnahtari(env, amac, ...parcalar);
  const onceki = await env.DB.prepare('SELECT son_gonderim FROM eposta_kodlari WHERE anahtar = ?').bind(anahtar).first();
  if (onceki && (onceki.son_gonderim || 0) > t - YENIDEN_BEKLEME) {
    const bekle = Math.max(1, YENIDEN_BEKLEME - (t - onceki.son_gonderim));
    return hataYanit(429, 'Yeni kod için biraz bekle.', { bekle });
  }
  if (!(await gunlukAyir(env, t))) return hataYanit(503, GUNLUK_DOLU);
  await denemeYaz(env, EPOSTA_IP_SINIRI, ipA, t);
  await denemeYaz(env, EPOSTA_ADRES_SINIRI, adresA, t);
  const s = await uretVeGonder(env, anahtar, eposta, amac, t);
  return s === true ? gonderildi() : s;
}

// ---------- POST /giris/eposta/kod ----------
export async function epostaKod(request, env) {
  if (!epostaAcik(env)) return hataYanit(503, KAPALI);
  const { ipA, ret } = await kabaSinir(request, 'epostakod', 10);
  if (ret) return ret;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const eposta = epostaNormalle(g.eposta);
  if (!eposta) return hataYanit(400, 'Geçerli bir e-posta adresi yaz.');
  if (env.TURNSTILE_GIZLI && !(await turnstileDogrula(env, g.turnstile, request))) return hataYanit(400, ROBOT_HATASI);
  return kodIstegi(env, { amac: 'giris', eposta, parcalar: [eposta], ipA, t: simdi() });
}

// ---------- POST /giris/eposta/dogrula ----------
export async function epostaDogrula(request, env) {
  if (!epostaAcik(env)) return hataYanit(503, KAPALI);
  const { ipA, ret } = await kabaSinir(request, 'epostadogrula', 20);
  if (ret) return ret;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const eposta = epostaNormalle(g.eposta);
  if (!eposta || !kodBicimi(g.kod)) return hataYanit(400, 'E-posta adresini ve 6 haneli kodu yaz.');
  const t = simdi();
  if (await denemeSinirda(env, GIRIS_IP_SINIRI, ipA, t)) return cokDeneme();
  const sonuc = await kodDogrula(env, await kodAnahtari(env, 'giris', eposta), g.kod, t);
  if (sonuc !== 'tamam') {
    await denemeYaz(env, GIRIS_IP_SINIRI, ipA, t);   // başarısız denemeler IP sınırına işlenir (başka adreslerde kod tahmini yağdırmak pahalı olsun)
    return kodHatasi(sonuc);
  }
  const uye = await env.DB.prepare(`SELECT ${UYE_ALANLARI} FROM uyeler WHERE eposta = ?`).bind(eposta).first();
  if (uye) return oturumYaniti(env, uye);
  return jsonYanit({ yeni: true, gecici: await geciciEpostaUret(env, eposta, t) });
}

// ---------- POST /sifre-sifirla/eposta ----------
// { rumuz } ya da { eposta }: hesap var mı, e-postası kayıtlı mı fark etmez, yanıt hep aynıdır. Sayaçlar istek tanımlayıcısına bağlıdır
// (hesabın adresine değil), böylece "bekle" uyarısı da hesap varlığını sızdırmaz.
export async function sifirlaEposta(request, env) {
  if (!epostaAcik(env)) return hataYanit(503, KAPALI);
  const { ipA, ret } = await kabaSinir(request, 'sifirlaeposta', 10);
  if (ret) return ret;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const girdi = typeof g.eposta === 'string' ? g.eposta : g.rumuz;
  if (typeof girdi !== 'string' || !girdi.trim() || girdi.length > 254) return hataYanit(400, 'Rumuzunu ya da e-posta adresini yaz.');
  const adresle = girdi.includes('@');
  const eposta = adresle ? epostaNormalle(girdi) : null;
  const kat = adresle ? null : rumuzKat(girdi);
  if (!eposta && !kat) return hataYanit(400, adresle ? 'Geçerli bir e-posta adresi yaz.' : 'Rumuzunu ya da e-posta adresini yaz.');
  if (env.TURNSTILE_GIZLI && !(await turnstileDogrula(env, g.turnstile, request))) return hataYanit(400, ROBOT_HATASI);
  const t = simdi();
  if (await denemeSinirda(env, EPOSTA_IP_SINIRI, ipA, t)) return hataYanit(429, 'Bu bağlantıdan çok fazla kod istendi. Bir saat sonra tekrar dene.');
  const istekA = await biberliOzet(env, 'sifirla-istek', eposta || `rumuz:${kat}`);
  if (await denemeSinirda(env, SIFIRLA_BEKLEME, istekA, t)) return hataYanit(429, 'Yeni kod için biraz bekle.', { bekle: YENIDEN_BEKLEME });
  if (await denemeSinirda(env, SIFIRLA_SAAT_SINIRI, istekA, t)) return hataYanit(429, 'Çok fazla kod istedin. Bir saat sonra tekrar dene.');
  if (await gunlukDolu(env, t)) return hataYanit(503, GUNLUK_DOLU);   // hesap var mı bakmadan: varlık sızmaz
  await denemeYaz(env, EPOSTA_IP_SINIRI, ipA, t);
  await denemeYaz(env, SIFIRLA_SAAT_SINIRI, istekA, t);
  const uye = eposta
    ? await env.DB.prepare(`SELECT ${UYE_ALANLARI} FROM uyeler WHERE eposta = ?`).bind(eposta).first()
    : await uyeBul(env, girdi);
  if (uye && uye.eposta && await gunlukAyir(env, t)) {
    const s = await uretVeGonder(env, await kodAnahtari(env, 'sifirla', uye.id), uye.eposta, 'sifirla', t);
    if (s !== true) return gonderildi();   // gönderim hatası da sızdırmasın; kullanıcı yeniden dener
  }
  return gonderildi();
}

// Şifre sıfırlama kodu doğrulaması (kayit.js sifreSifirla kullanır): kod doğruysa true.
export async function sifirlamaKoduDogrula(env, uyeId, kod, t) {
  return kodDogrula(env, await kodAnahtari(env, 'sifirla', uyeId ?? 0), kod, t);
}
export { kodBicimi };

// ---------- POST /ben/eposta ----------
// { eposta }: yeni adrese kod gönderir. { eposta, kod }: kodu doğrular ve adresi hesaba yazar (oturum sürümüne dokunulmaz).
export async function benEposta(request, env) {
  if (!epostaAcik(env)) return hataYanit(503, KAPALI);
  const { ipA, ret } = await kabaSinir(request, 'beneposta', 10);
  if (ret) return ret;
  const u = await oturumUyesi(request, env);
  if (!u) return hataYanit(401, 'Giriş yapmalısın.');
  if (!ipSiniri(`beneposta-uye:${u.id}`, simdi(), 10, 60)) return cokDeneme();   // üye başına dakikada 10 istek
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const eposta = epostaNormalle(g.eposta);
  if (!eposta) return hataYanit(400, 'Geçerli bir e-posta adresi yaz.');
  const t = simdi();
  if (g.kod === undefined) {
    if (u.eposta === eposta) return hataYanit(400, 'Bu adres zaten hesabında kayıtlı.');
    return kodIstegi(env, { amac: 'degistir', eposta, parcalar: [u.id, eposta], ipA, t });
  }
  if (!kodBicimi(g.kod)) return hataYanit(400, '6 haneli kodu yaz.');
  if (await denemeSinirda(env, GIRIS_IP_SINIRI, ipA, t)) return cokDeneme();
  const sonuc = await kodDogrula(env, await kodAnahtari(env, 'degistir', u.id, eposta), g.kod, t);
  if (sonuc !== 'tamam') { await denemeYaz(env, GIRIS_IP_SINIRI, ipA, t); return kodHatasi(sonuc); }
  const baska = await env.DB.prepare('SELECT id FROM uyeler WHERE eposta = ? AND id != ?').bind(eposta, u.id).first();
  if (baska) return hataYanit(409, 'Bu adres başka bir hesapta kayıtlı.');
  try {
    await env.DB.prepare('UPDATE uyeler SET eposta = ?, eposta_dogrulandi = ? WHERE id = ?').bind(eposta, t, u.id).run();
  } catch (e) {
    if (/UNIQUE constraint failed/i.test(String(e && e.message))) return hataYanit(409, 'Bu adres başka bir hesapta kayıtlı.');
    throw e;
  }
  return jsonYanit({ tamam: true, eposta: epostaMaskele(eposta), eposta_dogrulandi: true });
}
