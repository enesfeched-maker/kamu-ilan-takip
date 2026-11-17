// Özel mesajlar: engelleme, şikayet, hız sınırı ve denetim varsayılan olarak açık.
// index.js ile döngüsel içe aktarma güvenlidir: yardımcılar yalnız istek sırasında çağrılır.
import { jsonYanit, hataYanit, simdi, avCikti } from './yardimci.js';
import { ozelMesajHizi } from './hiz.js';
import { ozelMesajBildirimi } from './bildirim.js';
import { oturumUyesi, yazar, govdeOku, metinDenetle, uyeRumuzla, yoneticiMi, negatifsizTamsayi } from './index.js';

const SAYFA = 50;
const GUN = 86400;
const ILK_MESAJ_SINIRI = 3;   // karşı taraf yanıt verene kadar
const YENI_HESAP_MESAJ = 3;   // 1 günden genç hesap için gereken forum mesajı

const giris = async (request, env) => {
  const uye = await oturumUyesi(request, env);
  return uye ? { uye } : { hata: hataYanit(401, 'Giriş yapmalısın.') };
};
const mesajCikti = (r, benId) => ({ id: r.id, govde: r.govde, olusma: r.olusma, benden: r.gonderen === benId });
const uyeCikti = (u) => ({ rumuz: u.rumuz, rol: u.rol, kurucu: !!u.kurucu, itibar: u.itibar || 0, ...avCikti(u, u.id) });
const sistemHesabi = (u) => u.rol === 'sistem' || u.rol === 'asistan';

// Okunmamış gelen mesaj sayısı (engellenen kişilerden gelenler sayılmaz). Tek indeksli COUNT.
export async function ozelOkunmamis(env, uyeId) {
  const s = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM ozel_mesajlar WHERE alici = ? AND okundu = 0 AND gizli = 0
     AND gonderen NOT IN (SELECT engellenen FROM engeller WHERE uye_id = ?)`,
  ).bind(uyeId, uyeId).first();
  return s?.n || 0;
}

async function engelDurumu(env, benId, oId) {
  const { results } = await env.DB.prepare(
    'SELECT uye_id FROM engeller WHERE (uye_id = ? AND engellenen = ?) OR (uye_id = ? AND engellenen = ?)',
  ).bind(benId, oId, oId, benId).all();
  return { engelledim: results.some((r) => r.uye_id === benId), engellendim: results.some((r) => r.uye_id === oId) };
}

// Karşı üye: bulunamazsa ya da yasaklıysa null.
async function esUye(env, ham) {
  const u = await uyeRumuzla(env, ham);
  return u && !u.engelli ? u : null;
}

async function okunduIsaretle(env, benId, oId) {
  await env.DB.prepare('UPDATE ozel_mesajlar SET okundu = 1 WHERE alici = ? AND gonderen = ? AND okundu = 0').bind(benId, oId).run();
}

// ---------- okuma ----------
export async function ozelKonusmalar(request, env) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  // iki yönün tek taraması, eş başına MAX(id) ile gruplanır; sonra son mesaj ve üye bilgisi geri birleştirilir
  const { results } = await env.DB.prepare(
    `SELECT g.esl, g.son_id, g.okunmamis, m.govde, m.olusma, m.gonderen, u.rumuz, u.rol, u.kurucu, u.itibar, u.avatar, u.foto_surum, CASE WHEN u.foto_surum IS NOT NULL THEN u.id END AS fu
     FROM (
       SELECT esl, MAX(id) AS son_id, SUM(oku) AS okunmamis FROM (
         SELECT id, alici AS esl, 0 AS oku FROM ozel_mesajlar WHERE gonderen = ? AND gizli = 0
         UNION ALL
         SELECT id, gonderen AS esl, CASE WHEN okundu = 0 THEN 1 ELSE 0 END AS oku FROM ozel_mesajlar WHERE alici = ? AND gizli = 0
       ) GROUP BY esl
     ) g
     JOIN ozel_mesajlar m ON m.id = g.son_id
     JOIN uyeler u ON u.id = g.esl
     WHERE (u.engelli = 0 OR u.silindi IS NOT NULL) AND g.esl NOT IN (SELECT engellenen FROM engeller WHERE uye_id = ?)
     ORDER BY g.son_id DESC LIMIT 50`,
  ).bind(uye.id, uye.id, uye.id).all();
  return jsonYanit({
    konusmalar: results.map((r) => ({
      ...uyeCikti(r),
      son: { govde: String(r.govde || '').slice(0, 80), olusma: r.olusma, benden: r.gonderen === uye.id },
      okunmamis: r.okunmamis || 0,
    })),
    toplam_okunmamis: await ozelOkunmamis(env, uye.id),
  });
}

export async function ozelKonusma(request, env, url, ham) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  const onceHam = url.searchParams.get('once');
  const once = onceHam === null ? null : negatifsizTamsayi(onceHam);
  if (onceHam !== null && once === null) return hataYanit(400, 'once geçersiz.');
  const o = await esUye(env, ham);
  if (!o) return hataYanit(404, 'Üye bulunamadı.');
  const bag = [uye.id, o.id, o.id, uye.id];
  let kosul = '((gonderen = ? AND alici = ?) OR (gonderen = ? AND alici = ?)) AND gizli = 0';
  if (once !== null) { kosul += ' AND id < ?'; bag.push(once); }
  bag.push(SAYFA + 1);
  const { results } = await env.DB.prepare(`SELECT id, gonderen, govde, olusma, okundu FROM ozel_mesajlar WHERE ${kosul} ORDER BY id DESC LIMIT ?`).bind(...bag).all();
  const daha_eski = results.length > SAYFA;
  const satirlar = results.slice(0, SAYFA).reverse();
  if (satirlar.some((r) => r.gonderen === o.id && r.okundu === 0)) await okunduIsaretle(env, uye.id, o.id);
  const e = await engelDurumu(env, uye.id, o.id);
  return jsonYanit({
    uye: { ...uyeCikti(o), dm_acik: o.dm_acik !== 0 },
    mesajlar: satirlar.map((r) => mesajCikti(r, uye.id)),
    daha_eski, engelledim: e.engelledim, engellendim: e.engellendim,
  });
}

// Ucuz yoklama: sonra'dan büyük mesajlar (en çok 100); gelenler okundu olur.
export async function ozelYeni(request, env, url, ham) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  const sonra = negatifsizTamsayi(url.searchParams.get('sonra'));
  if (sonra === null) return hataYanit(400, 'sonra geçersiz.');
  const o = await esUye(env, ham);
  if (!o) return hataYanit(404, 'Üye bulunamadı.');
  const { results } = await env.DB.prepare(
    `SELECT id, gonderen, govde, olusma, okundu FROM ozel_mesajlar
     WHERE ((gonderen = ? AND alici = ?) OR (gonderen = ? AND alici = ?)) AND id > ? AND gizli = 0 ORDER BY id LIMIT 100`,
  ).bind(uye.id, o.id, o.id, uye.id, sonra).all();
  if (results.some((r) => r.gonderen === o.id && r.okundu === 0)) await okunduIsaretle(env, uye.id, o.id);
  return jsonYanit({ mesajlar: results.map((r) => mesajCikti(r, uye.id)) });
}

// ---------- gönderme ----------
async function yeniHesapMi(env, uye, t) {
  if ((uye.kayit || 0) <= t - GUN) return false;
  const s = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM (SELECT 1 FROM yanitlar WHERE uye_id = ? AND gizli = 0
       UNION ALL SELECT 1 FROM basliklar WHERE uye_id = ? AND gizli = 0 LIMIT ?)`,
  ).bind(uye.id, uye.id, YENI_HESAP_MESAJ).first();
  return (s?.n || 0) < YENI_HESAP_MESAJ;
}

export async function ozelGonder(request, env, ctx, ham) {
  const { uye, hata } = await yazar(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const o = await esUye(env, ham);
  if (!o) return hataYanit(404, 'Üye bulunamadı.');
  if (o.id === uye.id) return hataYanit(400, 'Kendine mesaj gönderemezsin.');
  if (sistemHesabi(o)) return hataYanit(403, 'Bu hesaba özel mesaj gönderilemez.');
  if (o.dm_acik === 0) return hataYanit(403, 'Bu üye özel mesaj almıyor.');
  const e = await engelDurumu(env, uye.id, o.id);
  if (e.engelledim || e.engellendim) return hataYanit(403, 'Bu üyeye mesaj gönderemezsin.');
  const t = simdi();
  if (await yeniHesapMi(env, uye, t)) return hataYanit(403, 'Özel mesaj için hesabının en az 1 günlük olması ya da forumda 3 mesajının olması gerekir.');
  const d = metinDenetle(g.govde, 1, 2000, 'Mesaj');
  if (d.hata) return d.hata;
  // karşı taraf yanıt verene kadar en çok 3 mesaj (gizlenenler de sayılır)
  const bekleyen = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM ozel_mesajlar WHERE gonderen = ? AND alici = ?
     AND id > COALESCE((SELECT MAX(id) FROM ozel_mesajlar WHERE gonderen = ? AND alici = ?), 0)`,
  ).bind(uye.id, o.id, o.id, uye.id).first();
  if ((bekleyen?.n || 0) >= ILK_MESAJ_SINIRI) return hataYanit(403, 'Karşı taraf yanıt verene kadar en fazla 3 mesaj gönderebilirsin.');
  const sinir = await ozelMesajHizi(env, uye, t);
  if (sinir) return hataYanit(sinir.durum, sinir.hata);
  const r = await env.DB.prepare('INSERT INTO ozel_mesajlar (gonderen, alici, govde, olusma) VALUES (?, ?, ?, ?)').bind(uye.id, o.id, d.temiz, t).run();
  const ctxBekle = ctx && ctx.waitUntil ? (p) => ctx.waitUntil(Promise.resolve(p).catch(() => {})) : (p) => Promise.resolve(p).catch(() => {});
  ctxBekle(ozelMesajBildirimi(env, { gonderen: uye, alici: o }, t));
  return jsonYanit({ mesaj: { id: r.meta.last_row_id, govde: d.temiz, olusma: t, benden: true } }, 201);
}

export async function ozelMesajSil(request, env, id) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  const m = await env.DB.prepare('SELECT id, gonderen, gizli FROM ozel_mesajlar WHERE id = ?').bind(id).first();
  if (!m || m.gizli) return hataYanit(404, 'Mesaj bulunamadı.');
  if (m.gonderen !== uye.id) return hataYanit(403, 'Bu mesajı silemezsin.');
  await env.DB.prepare('UPDATE ozel_mesajlar SET gizli = 1 WHERE id = ?').bind(id).run();
  return jsonYanit({ tamam: true });
}

// ---------- engelleme / şikayet ----------
export async function ozelEngelle(request, env, ham) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g || typeof g.engel !== 'boolean') return hataYanit(400, 'engel alanı true/false olmalı.');
  const o = await uyeRumuzla(env, ham);
  if (!o) return hataYanit(404, 'Üye bulunamadı.');
  if (o.id === uye.id) return hataYanit(400, 'Kendini engelleyemezsin.');
  if (g.engel) await env.DB.prepare('INSERT OR IGNORE INTO engeller (uye_id, engellenen, olusma) VALUES (?, ?, ?)').bind(uye.id, o.id, simdi()).run();
  else await env.DB.prepare('DELETE FROM engeller WHERE uye_id = ? AND engellenen = ?').bind(uye.id, o.id).run();
  return jsonYanit({ engelledim: g.engel });
}

export async function engellenenler(request, env) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  const { results } = await env.DB.prepare(
    'SELECT u.rumuz FROM engeller e JOIN uyeler u ON u.id = e.engellenen WHERE e.uye_id = ? ORDER BY e.olusma DESC LIMIT 200',
  ).bind(uye.id).all();
  return jsonYanit({ uyeler: results.map((r) => ({ rumuz: r.rumuz })) });
}

export async function ozelSikayet(request, env, ham) {
  const { uye, hata } = await giris(request, env);
  if (hata) return hata;
  const g = await govdeOku(request);
  if (!g) return hataYanit(400, 'Geçersiz istek.');
  const o = await uyeRumuzla(env, ham);
  if (!o) return hataYanit(404, 'Üye bulunamadı.');
  if (o.id === uye.id) return hataYanit(400, 'Kendini şikayet edemezsin.');
  const t = simdi();
  let mesajId = null;
  if (g.mesaj_id !== undefined && g.mesaj_id !== null) {
    if (!Number.isInteger(g.mesaj_id)) return hataYanit(400, 'mesaj_id geçersiz.');
    const m = await env.DB.prepare('SELECT id FROM ozel_mesajlar WHERE id = ? AND gonderen = ? AND alici = ?').bind(g.mesaj_id, o.id, uye.id).first();
    if (!m) return hataYanit(400, 'Şikayet edilen mesaj bulunamadı.');
    mesajId = m.id;
  } else {
    const m = await env.DB.prepare('SELECT MAX(id) AS id FROM ozel_mesajlar WHERE gonderen = ? AND alici = ?').bind(o.id, uye.id).first();
    mesajId = m?.id ?? null;
  }
  const var_ = await env.DB.prepare('SELECT 1 AS v FROM ozel_sikayetler WHERE sikayet_eden = ? AND sikayet_edilen = ? AND olusma > ?').bind(uye.id, o.id, t - GUN).first();
  const islemler = [env.DB.prepare('INSERT OR IGNORE INTO engeller (uye_id, engellenen, olusma) VALUES (?, ?, ?)').bind(uye.id, o.id, t)];
  if (!var_) islemler.push(env.DB.prepare('INSERT INTO ozel_sikayetler (sikayet_eden, sikayet_edilen, mesaj_id, olusma) VALUES (?, ?, ?, ?)').bind(uye.id, o.id, mesajId, t));
  await env.DB.batch(islemler);
  return jsonYanit({ tamam: true, engelledim: true, ...(var_ ? { zaten: true } : {}) });
}

// Yönetici: mesaj metniyle birlikte (işlem yapabilmek için).
export async function yonetimOzelSikayetler(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const { results } = await env.DB.prepare(
    `SELECT s.id, s.olusma, s.mesaj_id, a.id AS eden_id, a.rumuz AS eden, b.id AS edilen_id, b.rumuz AS edilen, b.engelli AS edilen_engelli,
       m.govde, m.gizli, m.olusma AS mesaj_olusma
     FROM ozel_sikayetler s JOIN uyeler a ON a.id = s.sikayet_eden JOIN uyeler b ON b.id = s.sikayet_edilen
     LEFT JOIN ozel_mesajlar m ON m.id = s.mesaj_id ORDER BY s.id DESC LIMIT 100`,
  ).all();
  return jsonYanit({
    sikayetler: results.map((r) => ({
      id: r.id, olusma: r.olusma, mesaj_id: r.mesaj_id,
      sikayet_eden: { id: r.eden_id, rumuz: r.eden },
      sikayet_edilen: { id: r.edilen_id, rumuz: r.edilen, engelli: !!r.edilen_engelli },
      govde: r.govde ?? null, gizli: !!r.gizli, mesaj_olusma: r.mesaj_olusma ?? null,
    })),
  });
}
