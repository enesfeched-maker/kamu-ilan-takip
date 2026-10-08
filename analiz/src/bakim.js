// Günlük bakım (cron): tamamlanan günlerin özetini çıkarır, eski ham olayları ve tuzları siler.
import { gunOzetiYaz } from './sorgu.js';
import { butceDurumu } from './butce.js';
import { bugun, gunEkle, gunBasSn, trParcalari } from './zaman.js';

export const HAM_SAKLAMA_GUN = 90;
export const OZET_SAKLAMA_GUN = 400;

export async function bakim(env, simdiMs = Date.now()) {
  // Günlük D1 bütçesi dolduysa bakım ertelenir; ertesi gün atlanan günleri kendisi tamamlar.
  const b = await butceDurumu(env, simdiMs);
  if (b.okumaKademesi >= 2 || b.yazmaKademesi >= 3) return { ertelendi: true, ozetlenen: [] };
  const db = env.DB;
  const simdiSn = Math.floor(simdiMs / 1000);
  const bu = bugun(simdiMs);

  // Özeti çıkmamış geçmiş günler (cron birkaç gün atlamış olabilir). Bugüne dokunulmaz.
  // Tüm tabloyu taramamak için en eski olaydan bugüne gün gün gidilir; her gün ts indeksiyle LIMIT 1 yoklanır.
  const yazilan = [];
  const enEski = await db.prepare('SELECT MIN(ts) AS m FROM olaylar').first();
  if (enEski && enEski.m !== null && enEski.m !== undefined) {
    const ozetli = new Set(((await db.prepare('SELECT gun FROM ozet_gun').all()).results || []).map((r) => r.gun));
    for (let gun = trParcalari(Number(enEski.m)).gun; gun < bu; gun = gunEkle(gun, 1)) {
      if (ozetli.has(gun)) continue;
      const varMi = await db.prepare('SELECT 1 AS v FROM olaylar WHERE ts >= ? AND ts < ? LIMIT 1').bind(gunBasSn(gun), gunBasSn(gun) + 86400).first();
      if (!varMi) continue;
      await gunOzetiYaz(db, gun, simdiSn);
      yazilan.push(gun);
    }
  }

  // /populer için günlük 'pop' özeti sonradan eklendi: son 6 günden bu satırı olmayan (ve ham verisi hâlâ duran) günler bir kez yeniden özetlenir.
  const geriDoldur = await db.prepare("SELECT gun FROM ozet_gun WHERE gun BETWEEN ? AND ? AND gun NOT IN (SELECT gun FROM ozet WHERE boyut = 'pop') ORDER BY gun").bind(gunEkle(bu, -6), gunEkle(bu, -1)).all();
  for (const { gun } of geriDoldur.results || []) {
    await gunOzetiYaz(db, gun, simdiSn);
    yazilan.push(gun);
  }

  // Ham olaylar yalnız özeti çıkmış günler için silinir; özeti çıkmamış gün (hata durumu) korunur.
  const sinir = simdiSn - HAM_SAKLAMA_GUN * 86400;
  await db.prepare('DELETE FROM olaylar WHERE ts < ? AND gun IN (SELECT gun FROM ozet_gun)').bind(sinir).run();
  await db.prepare('DELETE FROM tuz WHERE gun < ?').bind(bu).run();
  await db.prepare('DELETE FROM giris_deneme WHERE ilk < ? AND kilit < ?').bind(simdiSn - 86400, simdiSn).run();
  const eski = gunEkle(bu, -OZET_SAKLAMA_GUN);
  await db.prepare('DELETE FROM ozet WHERE gun < ?').bind(eski).run();
  await db.prepare('DELETE FROM ozet_gun WHERE gun < ?').bind(eski).run();
  try { await db.prepare('DELETE FROM butce WHERE gun_utc < ?').bind(gunEkle(bu, -30)).run(); } catch { /* 0003_butce.sql henüz uygulanmadıysa atlanır */ }
  return { ozetlenen: yazilan };
}
