// E-posta ile giriş: 6 haneli kod, Brevo (işleyen) üzerinden gönderilir.
//  - Kodun ve adresin kendisi veritabanında tutulmaz (eposta_kodlari: yalnız biberli özetler). Adres yalnız doğrulanınca üye satırına yazılır.
//  - Hesap var mı yok mu, yanıttan anlaşılmaz: kod isteği ve şifre sıfırlama isteği her durumda aynı yanıtı verir; gönderim ctx.waitUntil ile
//    arka planda yapılır (yanıt süresi de hesap varlığına bağlı olmaz).
//  - Brevo ücretsiz planı hesap genelinde günde 300 e-posta: UTC gün sayacı 280'de durur (eposta_gunluk); 220'den sonra hesabı olmayan
//    adreslere giriş kodu gönderilmez (kota yalnız mevcut üyelere ayrılır). Üretimde robot kontrolü (Turnstile) şarttır.
//  - Sayaçlar atomiktir (eposta_sayac: INSERT ... ON CONFLICT DO UPDATE ... RETURNING); paralel istekler sınırı aşamaz.
//  - Yalnız ORTAM=yerel iken ve BREVO_ANAHTARI yokken kod gerçekten gönderilmez, konsola yazılır (yerel deneme).
// index.js / kayit.js ile döngüsel içe aktarma güvenlidir: yardımcılar yalnız istek sırasında çağrılır.
import { jsonYanit, hataYanit, simdi, sabitEsit } from './yardimci.js';
import { rumuzKat, geciciEpostaUret, oturumUret } from './oturum.js';
import { sifreYapilandirildi, biberliOzet, sifreDogrula } from './sifre.js';
import { denemeSinirda, denemeYaz, cokDeneme, ipSiniri, ipGunAnahtari, SIFIRLA_SAAT_SINIRI, SIFIRLA_BEKLEME } from './hiz.js';
import { epostaNormalle, epostaMaskele, epostaTekil, epostaSayacAdresi } from './epostabicim.js';
import { kabaSinir, turnstileDogrula, UYE_ALANLARI, uyeBul } from './kayit.js';
import { govdeOku, oturumUyesi, oturumYaniti } from './index.js';
import { kimlikKapaliMi } from './arac.js';

const BREVO_ADRESI = 'https://api.brevo.com/v3/smtp/email';
export const KOD_OMRU = 600;             // 10 dakika
export const KOD_DENEME = 5;             // kod başına en çok 5 doğrulama denemesi
export const YENIDEN_BEKLEME = 60;       // aynı adrese iki gönderim arası en az 60 sn
export const GUNLUK_SINIR = 280;         // Brevo ücretsiz plan günde 300; pay bırakılır
export const KOTA_YEDEGI = 60;           // kalan kota bunun altına inince hesabı olmayan adreslere giriş kodu gönderilmez
export const IP_GUNLUK_GONDERIM = 5;     // IP kovası (IPv4 /24, IPv6 /64) başına günde 5 gönderim
export const ADRES_SAATLIK = 5;          // adres (tekil biçim) başına saatte 5 gönderim
export const IP_DOGRULAMA = 10;          // IP başına 15 dakikada 10 doğrulama denemesi
export const HEDEF_GUNLUK_HATA = 20;     // hedef (adres ya da üye) başına günde 20 deneme; yeni kod istemek bunu sıfırlamaz
const KAPALI = 'E-posta ile giriş şu an kapalı. Google ya da rumuzla devam edebilirsin.';
export const GUNLUK_DOLU = 'Şu an e-posta gönderemiyoruz, Google ya da rumuzla devam edebilirsin.';
const KOD_HATASI = 'Kod hatalı ya da süresi dolmuş. Yeni bir kod isteyebilirsin.';
const KOD_COK_HATA = 'Çok fazla yanlış deneme. Yeni bir kod iste.';
const ROBOT_HATASI = 'Robot kontrolü geçilemedi. Sayfayı yenileyip tekrar dene.';
const IP_GUNLUK_HATASI = 'Bu bağlantıdan bugün çok fazla kod istendi. Yarın tekrar dene ya da başka bir yöntemle gir.';

// E-posta özelliği: oturum sırrı + biber (özetler için) + ya yerel geliştirme kipi ya da (Brevo anahtarı + Turnstile).
// Üretimde robot kontrolü olmadan e-posta girişi açılmaz (kota tüketme / e-posta bombalama saldırısı).
export const yerelGelistirme = (env) => env.ORTAM === 'yerel' && !env.BREVO_ANAHTARI;
export function epostaAcik(env) {
  if (!env.OTURUM_SIRRI || !sifreYapilandirildi(env)) return false;
  return env.ORTAM === 'yerel' || (!!env.BREVO_ANAHTARI && !!env.TURNSTILE_GIZLI && !!env.TURNSTILE_SITE);
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
const sade = (govde) => `<!doctype html><html lang="tr"><head><meta charset="utf-8"></head><body style="margin:0;padding:24px;font-family:Arial,Helvetica,sans-serif;color:#1a1a1a">${govde}</body></html>`;
export function epostaIcerigi(amac, kod) {
  const [baslik, ad] = AMAC_METNI[amac] || AMAC_METNI.giris;
  const alt = '10 dakika geçerli. Bu isteği sen yapmadıysan bu e-postayı yok say.';
  return {
    konu: `${baslik}: ${kod}`,
    metin: `${ad}: ${kod}. ${alt}`,
    html: sade(`<p style="margin:0 0 12px;font-size:16px">${ad}:</p>`
      + `<p style="margin:0 0 12px;font-size:28px;font-weight:700;letter-spacing:4px">${kod}</p>`
      + `<p style="margin:0;font-size:14px;color:#444">${alt}</p>`),
  };
}
// Eski adrese giden değişiklik bildirimi.
export function degisiklikBildirimi() {
  const metin = 'E-posta adresin değiştirildi; sen yapmadıysan iletisim@kpsstercihi.com\'a yaz.';
  return { konu: 'KPSS Tercihi: e-posta adresin değiştirildi', metin, html: sade(`<p style="margin:0;font-size:16px">${metin}</p>`) };
}

// Brevo işlemsel e-posta API'si. Başarılıysa true. Hata ayrıntısı (adres içerebilir) loga yazılmaz, yalnız durum kodu.
async function epostaIlet(env, alici, etiket, { konu, metin, html }, kodGoster) {
  if (yerelGelistirme(env)) {
    console.log(`[eposta-gelistirme] ${etiket} (${alici}): ${kodGoster}`);   // yalnız ORTAM=yerel ve BREVO_ANAHTARI yok
    return true;
  }
  if (!env.BREVO_ANAHTARI) return false;
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
export const epostaGonder = (env, alici, amac, kod) => epostaIlet(env, alici, `${amac} kodu`, epostaIcerigi(amac, kod), kod);
// İşi arka planda yürütür (yanıt süresi hesap varlığına bağlı olmasın); ctx yoksa (test, eski çağrı) sonucu bekler.
const arkada = async (ctx, is) => {
  const p = Promise.resolve().then(is).catch(() => {});
  if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
};

// ---------- atomik sayaçlar ----------
// Artırıp yeni değeri döner (tek ifade: paralel istekler farklı değer görür). dilim: zaman dilimi numarası.
async function say(env, tur, anahtar, dilim, t) {
  const r = await env.DB.prepare(
    'INSERT INTO eposta_sayac (tur, anahtar, dilim, n, olusma) VALUES (?, ?, ?, 1, ?) '
    + 'ON CONFLICT(tur, anahtar, dilim) DO UPDATE SET n = n + 1, olusma = excluded.olusma RETURNING n',
  ).bind(tur, anahtar, dilim, t).first();
  if (Math.random() < 0.01) {   // Worker'da zamanlayıcı yok: yazmaların ~%1'inde fırsat temizliği
    await env.DB.prepare('DELETE FROM eposta_sayac WHERE rowid IN (SELECT rowid FROM eposta_sayac WHERE olusma < ? LIMIT 200)').bind(t - 2 * 86400).run();
  }
  return r?.n || 1;
}
const sayGeri = (env, tur, anahtar, dilim) => env.DB.prepare('UPDATE eposta_sayac SET n = MAX(0, n - 1) WHERE tur = ? AND anahtar = ? AND dilim = ?').bind(tur, anahtar, dilim).run();
const GUN = (t) => Math.floor(t / 86400);
const SAAT = (t) => Math.floor(t / 3600);
const ONBES_DK = (t) => Math.floor(t / 900);

// Doğrulama denemesi izni (artır-sonra-kontrol): IP başına 15 dakikada 10, hedef başına günde 20. Hedef: adres, üye ya da rumuz kimliği.
// Engel varsa hata yanıtı, yoksa null. Başarılı doğrulamada dogrulamaBasari ile hedef hakkı geri verilir.
export async function dogrulamaIzni(env, ipA, hedef, t) {
  if (await say(env, 'dogrula_ip', ipA, ONBES_DK(t), t) > IP_DOGRULAMA) return cokDeneme();
  const h = await say(env, 'hata_hedef', await biberliOzet(env, 'hedef', hedef), GUN(t), t);
  if (h > HEDEF_GUNLUK_HATA) return hataYanit(429, 'Bu hesap için bugünlük deneme hakkı doldu. Yarın tekrar dene ya da başka bir yöntemle gir.');
  return null;
}
export async function dogrulamaBasari(env, hedef, t) {
  await sayGeri(env, 'hata_hedef', await biberliOzet(env, 'hedef', hedef), GUN(t));
}

// ---------- günlük sayaç (UTC gün) ----------
const gunAdi = (t) => new Date(t * 1000).toISOString().slice(0, 10);
export async function gunlukKalan(env, t) {
  const s = await env.DB.prepare('SELECT n FROM eposta_gunluk WHERE gun = ?').bind(gunAdi(t)).first();
  return GUNLUK_SINIR - (s?.n || 0);
}
// Bir gönderim hakkı ayırır; tek atomik ifade (gün değişiminde de yarış yok). Sınırdaysa false.
export async function gunlukAyir(env, t) {
  const r = await env.DB.prepare('INSERT INTO eposta_gunluk (gun, n) VALUES (?, 1) ON CONFLICT(gun) DO UPDATE SET n = n + 1 WHERE n < ? RETURNING n')
    .bind(gunAdi(t), GUNLUK_SINIR).first();
  if (!r) return false;
  if (r.n === 1) await env.DB.prepare('DELETE FROM eposta_gunluk WHERE gun < ?').bind(gunAdi(t - 7 * 86400)).run();   // yeni gün: eski günler silinir
  return true;
}
async function gunlukIade(env, t) {
  await env.DB.prepare('UPDATE eposta_gunluk SET n = MAX(0, n - 1) WHERE gun = ?').bind(gunAdi(t)).run();
}

// ---------- kod satırı ----------
// amac + parçalar: 'giris' [tekil adres] | 'degistir' [uyeId, tekil adres] | 'sifirla' [uyeId]
export const kodAnahtari = (env, amac, ...parcalar) => biberliOzet(env, 'kod', `${amac}:${parcalar.join(':')}`);
const kodOzeti = (env, anahtar, kod) => biberliOzet(env, 'kodozet', `${anahtar}:${kod}`);

async function kodYaz(env, anahtar, kod, t) {
  await env.DB.prepare(
    'INSERT INTO eposta_kodlari (anahtar, kod_ozet, bitis, deneme, son_gonderim) VALUES (?, ?, ?, 0, ?) '
    + 'ON CONFLICT(anahtar) DO UPDATE SET kod_ozet = excluded.kod_ozet, bitis = excluded.bitis, deneme = 0, son_gonderim = excluded.son_gonderim',
  ).bind(anahtar, await kodOzeti(env, anahtar, kod), t + KOD_OMRU, t).run();
  if (Math.random() < 0.01) {
    await env.DB.prepare('DELETE FROM eposta_kodlari WHERE rowid IN (SELECT rowid FROM eposta_kodlari WHERE bitis < ? LIMIT 200)').bind(t - 3600).run();
  }
}
const kodSil = (env, anahtar) => env.DB.prepare('DELETE FROM eposta_kodlari WHERE anahtar = ?').bind(anahtar).run();

// 'tamam' (kod tüketildi) | 'yanlis' | 'cok' (deneme hakkı bitti). Deneme sayacı tek atomik UPDATE ... RETURNING ile artar:
// paralel istekler farklı değer alır, 5'ten fazlası satır bulamaz. Doğru kod tek kullanımlıktır (silme tek atomik adım).
export async function kodDogrula(env, anahtar, kod, t) {
  const k = kodBicimi(kod);
  const r = await env.DB.prepare('UPDATE eposta_kodlari SET deneme = deneme + 1 WHERE anahtar = ? AND bitis > ? AND deneme < ? RETURNING kod_ozet, deneme')
    .bind(anahtar, t, KOD_DENEME).first();
  if (!r) {   // kod yok, süresi dolmuş ya da deneme hakkı bitmiş
    if (k) await kodOzeti(env, anahtar, k);   // yokken de aynı işi yap
    const s = await env.DB.prepare('SELECT deneme FROM eposta_kodlari WHERE anahtar = ? AND bitis > ?').bind(anahtar, t).first();
    return s && (s.deneme || 0) >= KOD_DENEME ? 'cok' : 'yanlis';
  }
  if (k && sabitEsit(await kodOzeti(env, anahtar, k), r.kod_ozet)) {
    const d = await env.DB.prepare('DELETE FROM eposta_kodlari WHERE anahtar = ? AND kod_ozet = ?').bind(anahtar, r.kod_ozet).run();
    return (d.meta?.changes || 0) === 1 ? 'tamam' : 'yanlis';   // aynı kodla paralel ikinci istek kaybeder
  }
  return r.deneme >= KOD_DENEME ? 'cok' : 'yanlis';
}
const kodHatasi = (sonuc) => (sonuc === 'cok' ? hataYanit(429, KOD_COK_HATA) : hataYanit(400, KOD_HATASI));

// Arka plan gönderimi: başarısızsa kod satırı ve günlük hak geri alınır.
async function gonderVeGeriAl(env, anahtar, alici, amac, kod, t) {
  if (await epostaGonder(env, alici, amac, kod)) return;
  await kodSil(env, anahtar);
  await gunlukIade(env, t);
}
const gonderildi = () => jsonYanit({ tamam: true, bekle: YENIDEN_BEKLEME });
async function robotKontrol(env, g, request) {
  return !env.TURNSTILE_GIZLI || await turnstileDogrula(env, g.turnstile, request);
}

// Ortak gönderim yolu (giriş ve e-posta ekleme/değiştirme). Her adres için aynı denetimler; hesap varlığına bakılmaz
// (kota yedeği dışında: kalan kota azken hesabı olmayan adrese giriş kodu gerçekten gönderilmez ama yanıt aynıdır).
async function kodIstegi(request, env, ctx, { amac, eposta, parcalar, t }) {
  const anahtar = await kodAnahtari(env, amac, ...parcalar);
  const onceki = await env.DB.prepare('SELECT son_gonderim FROM eposta_kodlari WHERE anahtar = ?').bind(anahtar).first();
  if (onceki && (onceki.son_gonderim || 0) > t - YENIDEN_BEKLEME) {
    return hataYanit(429, 'Yeni kod için biraz bekle.', { bekle: Math.max(1, YENIDEN_BEKLEME - (t - onceki.son_gonderim)) });
  }
  if (await say(env, 'gonder_ip', await ipGunAnahtari(request), GUN(t), t) > IP_GUNLUK_GONDERIM) return hataYanit(429, IP_GUNLUK_HATASI);
  const adresA = await biberliOzet(env, 'eposta-adres', epostaSayacAdresi(eposta));
  if (await say(env, 'eposta_adres', adresA, SAAT(t), t) > ADRES_SAATLIK) return hataYanit(429, 'Bu adrese çok fazla kod gönderildi. Bir saat sonra tekrar dene.');
  const kalan = await gunlukKalan(env, t);
  if (kalan <= 0) return hataYanit(503, GUNLUK_DOLU);
  if (amac === 'giris' && kalan < KOTA_YEDEGI) {
    const var_ = await env.DB.prepare('SELECT 1 AS x FROM uyeler WHERE eposta = ?').bind(eposta).first();
    if (!var_) { await kodYaz(env, anahtar, kodUret(), t); return gonderildi(); }   // kota yedeği: hesabı olmayana gönderilmez; bekleme ve yanıt aynı
  }
  if (!(await gunlukAyir(env, t))) return hataYanit(503, GUNLUK_DOLU);
  const kod = kodUret();
  await kodYaz(env, anahtar, kod, t);
  await arkada(ctx, () => gonderVeGeriAl(env, anahtar, eposta, amac, kod, t));
  return gonderildi();
}

// ---------- POST /giris/eposta/kod ----------
export async function epostaKod(request, env, ctx) {
  if (!epostaAcik(env)) return hataYanit(503, KAPALI);
  const { ret } = await kabaSinir(request, 'epostakod', 10);
  if (ret) return ret;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const eposta = epostaNormalle(g.eposta);
  if (!eposta) return hataYanit(400, 'Geçerli bir e-posta adresi yaz.');
  if (!(await robotKontrol(env, g, request))) return hataYanit(400, ROBOT_HATASI);
  return kodIstegi(request, env, ctx, { amac: 'giris', eposta, parcalar: [epostaTekil(eposta)], t: simdi() });
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
  const hedef = `giris:${epostaTekil(eposta)}`;
  const engel = await dogrulamaIzni(env, ipA, hedef, t);
  if (engel) return engel;
  const sonuc = await kodDogrula(env, await kodAnahtari(env, 'giris', epostaTekil(eposta)), g.kod, t);
  if (sonuc !== 'tamam') return kodHatasi(sonuc);
  await dogrulamaBasari(env, hedef, t);
  const uye = await env.DB.prepare(`SELECT ${UYE_ALANLARI} FROM uyeler WHERE eposta = ?`).bind(eposta).first();
  if (uye) return oturumYaniti(env, uye);
  return jsonYanit({ yeni: true, gecici: await geciciEpostaUret(env, eposta, t) });
}

// ---------- POST /sifre-sifirla/eposta ----------
// { rumuz } ya da { eposta }: hesap var mı, e-postası kayıtlı mı fark etmez, yanıt hep aynıdır. Sayaç hedefi hesap varsa üye kimliğidir
// (rumuzla ve adresle yapılan istekler tek sayacı paylaşır), yoksa istek tanımlayıcısıdır; "bekle" uyarısı da varlığı sızdırmaz.
export async function sifirlaEposta(request, env, ctx) {
  if (!epostaAcik(env)) return hataYanit(503, KAPALI);
  const { ret } = await kabaSinir(request, 'sifirlaeposta', 10);
  if (ret) return ret;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const girdi = typeof g.eposta === 'string' ? g.eposta : g.rumuz;
  if (typeof girdi !== 'string' || !girdi.trim() || girdi.length > 254) return hataYanit(400, 'Rumuzunu ya da e-posta adresini yaz.');
  const adresle = girdi.includes('@');
  const eposta = adresle ? epostaNormalle(girdi) : null;
  const kat = adresle ? null : rumuzKat(girdi);
  if (!eposta && !kat) return hataYanit(400, adresle ? 'Geçerli bir e-posta adresi yaz.' : 'Rumuzunu ya da e-posta adresini yaz.');
  if (!(await robotKontrol(env, g, request))) return hataYanit(400, ROBOT_HATASI);
  const t = simdi();
  const uye = eposta
    ? await env.DB.prepare(`SELECT ${UYE_ALANLARI} FROM uyeler WHERE eposta = ?`).bind(eposta).first()
    : await uyeBul(env, girdi);
  const istekA = await biberliOzet(env, 'sifirla-istek', uye ? `uye:${uye.id}` : (eposta ? `eposta:${epostaTekil(eposta)}` : `rumuz:${kat}`));
  if (await denemeSinirda(env, SIFIRLA_BEKLEME, istekA, t)) return hataYanit(429, 'Yeni kod için biraz bekle.', { bekle: YENIDEN_BEKLEME });
  if (await denemeSinirda(env, SIFIRLA_SAAT_SINIRI, istekA, t)) return hataYanit(429, 'Çok fazla kod istedin. Bir saat sonra tekrar dene.');
  if (await say(env, 'gonder_ip', await ipGunAnahtari(request), GUN(t), t) > IP_GUNLUK_GONDERIM) return hataYanit(429, IP_GUNLUK_HATASI);
  if ((await gunlukKalan(env, t)) <= 0) return hataYanit(503, GUNLUK_DOLU);   // hesap var mı bakmadan: varlık sızmaz
  await denemeYaz(env, SIFIRLA_SAAT_SINIRI, istekA, t);
  if (uye && uye.eposta) {
    // adres sayacı üyenin KAYITLI adresine yazılır (giriş kodu ve sıfırlama aynı bütçeyi paylaşır); bütçe dolduysa sessizce gönderilmez
    const adresA = await biberliOzet(env, 'eposta-adres', epostaSayacAdresi(uye.eposta));
    if (await say(env, 'eposta_adres', adresA, SAAT(t), t) <= ADRES_SAATLIK && await gunlukAyir(env, t)) {
      const anahtar = await kodAnahtari(env, 'sifirla', uye.id);
      const kod = kodUret();
      await kodYaz(env, anahtar, kod, t);
      await arkada(ctx, () => gonderVeGeriAl(env, anahtar, uye.eposta, 'sifirla', kod, t));
    }
  }
  return gonderildi();
}

// Şifre sıfırlama kodu doğrulaması (kayit.js sifreSifirlaEposta kullanır): 'tamam' | 'yanlis' | 'cok'.
export async function sifirlamaKoduDogrula(env, uyeId, kod, t) {
  return kodDogrula(env, await kodAnahtari(env, 'sifirla', uyeId ?? 0), kod, t);
}
export { kodBicimi };

// ---------- POST /ben/eposta ----------
// { eposta, sifre? }: yeni adrese kod gönderir. { eposta, kod, sifre? }: kodu doğrular ve adresi hesaba yazar. Hesapta şifre varsa her iki adımda
// şifre şart. Başarıda oturum sürümü artar (başka oturumlar kapanır, istek sahibi taze jeton alır) ve ESKİ adrese bildirim gider.
export async function benEposta(request, env, ctx) {
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
  const hedef = `ben:${u.id}`;
  const sifreOzeti = (await env.DB.prepare('SELECT sifre_ozet FROM uyeler WHERE id = ?').bind(u.id).first())?.sifre_ozet;
  // şifre (varsa) ve deneme hakkı: tek artış; hata ya da engel varsa yanıt, yoksa null
  const sina = async () => {
    const engel = await dogrulamaIzni(env, ipA, hedef, t);
    if (engel) return engel;
    if (sifreOzeti && (typeof g.sifre !== 'string' || !(await sifreDogrula(env, g.sifre, sifreOzeti)))) return hataYanit(401, 'Mevcut şifre yanlış.');
    return null;
  };
  if (g.kod === undefined) {
    if (u.eposta === eposta) return hataYanit(400, 'Bu adres zaten hesabında kayıtlı.');
    if (await kimlikKapaliMi(env, { eposta })) return hataYanit(403, 'Bu adres kullanılamıyor.');   // kapatılmış hesabın adresi
    if (sifreOzeti) { const e = await sina(); if (e) return e; await dogrulamaBasari(env, hedef, t); }
    if (!(await robotKontrol(env, g, request))) return hataYanit(400, ROBOT_HATASI);
    return kodIstegi(request, env, ctx, { amac: 'degistir', eposta, parcalar: [u.id, epostaTekil(eposta)], t });
  }
  if (!kodBicimi(g.kod)) return hataYanit(400, '6 haneli kodu yaz.');
  const engel = await sina();
  if (engel) return engel;
  const sonuc = await kodDogrula(env, await kodAnahtari(env, 'degistir', u.id, epostaTekil(eposta)), g.kod, t);
  if (sonuc !== 'tamam') return kodHatasi(sonuc);
  await dogrulamaBasari(env, hedef, t);
  const baska = await env.DB.prepare('SELECT id FROM uyeler WHERE eposta = ? AND id != ?').bind(eposta, u.id).first();
  if (baska) return hataYanit(409, 'Bu adres başka bir hesapta kayıtlı.');
  try {
    await env.DB.prepare('UPDATE uyeler SET eposta = ?, eposta_dogrulandi = ?, oturum_surum = COALESCE(oturum_surum, 0) + 1 WHERE id = ?').bind(eposta, t, u.id).run();
  } catch (e) {
    if (/UNIQUE constraint failed/i.test(String(e && e.message))) return hataYanit(409, 'Bu adres başka bir hesapta kayıtlı.');
    throw e;
  }
  const surum = (await env.DB.prepare('SELECT oturum_surum FROM uyeler WHERE id = ?').bind(u.id).first())?.oturum_surum || 0;
  if (u.eposta && await gunlukAyir(env, t)) {   // eski adrese bildirim (kota bitmişse atlanır)
    await arkada(ctx, async () => { if (!(await epostaIlet(env, u.eposta, 'bildirim', degisiklikBildirimi(), 'adres degistirildi'))) await gunlukIade(env, t); });
  }
  return jsonYanit({ tamam: true, eposta: epostaMaskele(eposta), eposta_dogrulandi: true, oturum: await oturumUret(env, u.id, t, surum) });
}
