// Yazma hız sınırları: D1'de ucuz, indeksli sayımlar.
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
