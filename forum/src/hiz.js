// Yazma hız sınırları: D1'de ucuz, indeksli sayımlar.
import { hataYanit } from './yardimci.js';
const GUN = 86400;
const ret = (mesaj) => ({ durum: 429, hata: mesaj });

async function say(env, tablo, uyeId, esik) {
  const s = await env.DB.prepare(`SELECT COUNT(*) AS n, MAX(olusma) AS son FROM ${tablo} WHERE uye_id = ? AND olusma > ?`).bind(uyeId, esik).first();
  return { n: s?.n || 0, son: s?.son || 0 };
}

// Başarılıysa null, değilse { durum: 429, hata }.
export async function baslikHizi(env, uye, simdi) {
  const { n, son } = await say(env, 'basliklar', uye.id, simdi - GUN);
  if (son > simdi - 120) return ret('Çok hızlı yazıyorsun. Yeni bir başlık için 2 dakika bekle.');
  if (n >= 10) return ret('Bugün için başlık sınırına ulaştın. Yarın tekrar dene.');
  if ((uye.kayit || 0) > simdi - GUN && n >= 3) return ret('Yeni üyeler ilk gün en fazla 3 başlık açabilir.');
  return null;
}
export async function yanitHizi(env, uye, simdi) {
  const { n, son } = await say(env, 'yanitlar', uye.id, simdi - GUN);
  if (son > simdi - 20) return ret('Çok hızlı yazıyorsun. Birkaç saniye bekle.');
  if (n >= 60) return ret('Bugün için yanıt sınırına ulaştın. Yarın tekrar dene.');
  return null;
}

// Özel mesaj hızı: saatte 20, günde 100 (gizlenen mesajlar da sayılır). (gonderen, olusma) indeksi.
export async function ozelMesajHizi(env, uye, simdi) {
  const s = await env.DB.prepare(
    'SELECT COUNT(*) AS gun, COALESCE(SUM(CASE WHEN olusma > ? THEN 1 ELSE 0 END), 0) AS saat FROM ozel_mesajlar WHERE gonderen = ? AND olusma > ?',
  ).bind(simdi - 3600, uye.id, simdi - GUN).first();
  if ((s?.saat || 0) >= 20) return ret('Saatte en fazla 20 özel mesaj gönderebilirsin. Biraz sonra tekrar dene.');
  if ((s?.gun || 0) >= 100) return ret('Bugün için özel mesaj sınırına ulaştın. Yarın tekrar dene.');
  return null;
}

// Üyelik / giriş denemeleri: (tur, anahtar, olusma) indeksiyle ucuz sayım. Anahtarlar IP özeti, rumuz ya da ikisi birden.
// Sınıra ulaşan istekler yazma yapmaz (yalnız başarısız deneme ve kayıt denemesi satır ekler), böylece D1 yazma kotası korunur.
export const KAYIT_SINIRI = { tur: 'kayit', en_cok: 5, pencere: 3600 };
export const GIRIS_IP_SINIRI = { tur: 'giris_ip', en_cok: 10, pencere: 900 };
export const GIRIS_RUMUZ_IP_SINIRI = { tur: 'giris_rumuz_ip', en_cok: 10, pencere: 900 };   // rumuz + IP: başkasının rumuzunu kilitlemeyi zorlaştırır
export const GIRIS_RUMUZ_SINIRI = { tur: 'giris_rumuz', en_cok: 50, pencere: 900 };         // yalnız rumuz: dağıtık saldırı için çok yüksek eşik
// E-posta kodu gönderimi (src/eposta.js). Sınıra ulaşan istekler yazma yapmaz; gönderimler sayılır.
// (IP başına günlük gönderim, adres başına saatlik gönderim ve yanlış kod sayaçları atomik eposta_sayac tablosundadır: src/eposta.js)
export const SIFIRLA_SAAT_SINIRI = { tur: 'sifirla_istek', en_cok: 5, pencere: 3600 };     // şifre sıfırlama isteği (rumuz ya da adres) başına saatte 5
export const SIFIRLA_BEKLEME = { tur: 'sifirla_istek', en_cok: 1, pencere: 60 };           // ... ve en çok dakikada 1 (aynı tür; hesap var olsa da olmasa da aynı davranır)
const TEMIZLIK_OMRU = 3600;   // en uzun pencere

// Yalnız CF-Connecting-IP güvenilir (X-Forwarded-For istemci tarafından yazılabilir). Başlık yoksa tek ortak "yok" kovası, normal sınırlarla.
// IPv6 adresleri /64 ön ekiyle anahtarlanır (bir kullanıcı kendi /64'ünden sayısız adres üretebilir).
export function ipOnEki(ip) {
  const s = String(ip || '').trim().toLowerCase().split('%')[0];
  if (!s) return 'yok';
  if (!s.includes(':')) return `v4:${s}`;
  const eslesme = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/.exec(s);
  if (eslesme) return `v4:${eslesme[1]}`;
  const [bas, son] = s.split('::');
  const a = bas ? bas.split(':') : [];
  const b = son ? son.split(':') : [];
  const g = s.includes('::') ? [...a, ...Array(Math.max(0, 8 - a.length - b.length)).fill('0'), ...b] : a;
  return `v6:${g.slice(0, 4).map((x) => (parseInt(x || '0', 16) || 0).toString(16)).join(':')}`;
}
export async function ipAnahtari(request) {
  const onEk = ipOnEki(request.headers.get('CF-Connecting-IP'));
  const ozet = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`ip:${onEk}`));
  return [...new Uint8Array(ozet).slice(0, 8)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
// Günlük e-posta gönderim sayacı için daha geniş kova: IPv4 /24, IPv6 /64 (ipOnEki zaten /64 verir).
export async function ipGunAnahtari(request) {
  let onEk = ipOnEki(request.headers.get('CF-Connecting-IP'));
  if (onEk.startsWith('v4:')) onEk = `v4:${onEk.slice(3).split('.').slice(0, 3).join('.')}.0/24`;
  const ozet = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`ipgun:${onEk}`));
  return [...new Uint8Array(ozet).slice(0, 8)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
export async function denemeSinirda(env, sinir, anahtar, simdi) {
  const s = await env.DB.prepare('SELECT COUNT(*) AS n FROM giris_denemeleri WHERE tur = ? AND anahtar = ? AND olusma > ?').bind(sinir.tur, anahtar, simdi - sinir.pencere).first();
  return (s?.n || 0) >= sinir.en_cok;
}
export async function denemeTemizle(env, simdi) {   // eski satırları siler (DELETE ... LIMIT D1'de yok; rowid alt sorgusu kullanılır)
  await env.DB.prepare('DELETE FROM giris_denemeleri WHERE rowid IN (SELECT rowid FROM giris_denemeleri WHERE olusma < ? LIMIT 200)').bind(simdi - TEMIZLIK_OMRU).run();
}
export async function denemeYaz(env, sinir, anahtar, simdi, rastgele = Math.random()) {
  await env.DB.prepare('INSERT INTO giris_denemeleri (tur, anahtar, olusma) VALUES (?, ?, ?)').bind(sinir.tur, anahtar, simdi).run();
  if (rastgele < 0.01) await denemeTemizle(env, simdi);   // Worker'da zamanlayıcı yok: yazmaların ~%1'inde fırsat temizliği
}
export const cokDeneme = () => hataYanit(429, 'Çok fazla deneme yaptın. Biraz sonra tekrar dene.');
// Anonim başvuru yazımı için en iyi çaba bellek içi sınır (izolat başına).
const kovalar = new Map();
export function ipSiniri(ip, simdi, limit = 30, pencere = 60) {
  const k = ip || '?';
  const kova = kovalar.get(k);
  if (!kova || simdi - kova.t >= pencere) {
    if (kovalar.size > 5000) kovalar.clear();
    kovalar.set(k, { t: simdi, n: 1 });
    return true;
  }
  kova.n++;
  return kova.n <= limit;
}
export const ipSinirSifirla = () => kovalar.clear();
