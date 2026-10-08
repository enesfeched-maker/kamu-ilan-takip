// Günlük bakım (cron): tamamlanan günlerin özetini çıkarır, eski ham olayları ve tuzları siler.
import { gunOzetiYaz } from './sorgu.js';
import { bugun, gunEkle } from './zaman.js';

export const HAM_SAKLAMA_GUN = 90;
export const OZET_SAKLAMA_GUN = 400;

export async function bakim(env, simdiMs = Date.now()) {
  const db = env.DB;
  const simdiSn = Math.floor(simdiMs / 1000);
  const bu = bugun(simdiMs);

  // Özeti çıkmamış geçmiş günler (cron birkaç gün atlamış olabilir). Bugüne dokunulmaz.
  const bekleyen = await db.prepare('SELECT DISTINCT gun FROM olaylar WHERE gun < ? AND gun NOT IN (SELECT gun FROM ozet_gun) ORDER BY gun').bind(bu).all();
  const yazilan = [];
  for (const { gun } of bekleyen.results || []) {
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
  return { ozetlenen: yazilan };
}
