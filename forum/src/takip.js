// Başlık / oda takibi. Odalar (kategori 'oda') otomatik takip edilmez; yalnız isteğe bağlı.
import { jsonYanit, hataYanit, simdi } from './yardimci.js';
import { oturumUyesi, yazar, govdeOku, baslikCikti, LISTE_ALANLARI } from './index.js';

export async function takipDegistir(request, env, baslikId) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g || typeof g.takip !== 'boolean') return hataYanit(400, 'takip alanı true/false olmalı.');
  const b = await env.DB.prepare('SELECT id FROM basliklar WHERE id = ? AND gizli = 0').bind(baslikId).first();
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  if (g.takip) await env.DB.prepare('INSERT OR IGNORE INTO takipler (uye_id, baslik_id, olusma) VALUES (?, ?, ?)').bind(uye.id, baslikId, simdi()).run();
  else await env.DB.prepare('DELETE FROM takipler WHERE uye_id = ? AND baslik_id = ?').bind(uye.id, baslikId).run();
  return jsonYanit({ takip: g.takip });
}

export async function takipMi(env, uyeId, baslikId) {
  return !!(await env.DB.prepare('SELECT 1 AS v FROM takipler WHERE uye_id = ? AND baslik_id = ?').bind(uyeId, baslikId).first());
}

export async function benTakipler(request, env) {
  const uye = await oturumUyesi(request, env);
  if (!uye) return hataYanit(401, 'Giriş yapmalısın.');
  const { results } = await env.DB.prepare(
    `SELECT ${LISTE_ALANLARI} FROM takipler t JOIN basliklar b ON b.id = t.baslik_id JOIN uyeler u ON u.id = b.uye_id
     WHERE t.uye_id = ? AND b.gizli = 0 ORDER BY b.son_hareket DESC LIMIT 100`,
  ).bind(uye.id).all();
  return jsonYanit({ basliklar: results.map((r) => baslikCikti(r, false)) });
}
