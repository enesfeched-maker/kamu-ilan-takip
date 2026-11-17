// Gizli yönetici araçları (Kasım 2026). Yönetici, uyeler.rol'den AYRI bir tablodadır (gizli_yoneticiler): rol, rozet ve hiçbir herkese açık
// çıktı değişmez; kim olduğu dışarıdan anlaşılmaz. Yetki her istekte sunucuda denetlenir (istemciye güvenilmez).
//   GET    /ben/arac                 yönetici: 200 { tamam }, diğer herkes: 404 (yol yokmuş gibi)
//   DELETE /arac/yanit/:id           cevap / sohbet mesajı kalıcı silinir (yer tutucu kalmaz)
//   DELETE /arac/baslik/:id          soru ve bütün cevapları kalıcı silinir (sohbet odaları silinmez)
//   DELETE /arac/ozel/:id            özel mesaj kalıcı silinir
//   POST   /arac/uye/:rumuz/kapat    hesap ve bütün içeriği kalıcı silinir; Google / Telegram / e-posta kimliğinin özeti saklanır, yeniden üye olunamaz
// Silmelerde sayaçlar (yanıt sayısı, faydalı oyları, itibar, anket oyları) da geri alınır.
import { jsonYanit, hataYanit, simdi } from './yardimci.js';
import { biberliOzet } from './sifre.js';
import { rumuzKat } from './oturum.js';
import { oturumUyesi, uyeRumuzla } from './index.js';

export async function gizliYoneticiMi(env, uyeId) {
  if (!uyeId) return false;
  const r = await env.DB.prepare('SELECT 1 AS x FROM gizli_yoneticiler WHERE uye_id = ?').bind(uyeId).first();
  return !!r;
}
// { uye } ya da { hata }: giriş yoksa 401, yönetici değilse 403.
async function yonetici(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u) return { hata: hataYanit(401, 'Giriş yapmalısın.') };
  if (u.engelli || !(await gizliYoneticiMi(env, u.id))) return { hata: hataYanit(403, 'Bu işlem için yetkin yok.') };
  return { uye: u };
}
export async function benArac(request, env) {
  const u = await oturumUyesi(request, env);
  if (!u || u.engelli || !(await gizliYoneticiMi(env, u.id))) return hataYanit(404, 'Bulunamadı.');
  return jsonYanit({ tamam: true });
}

// ---------- kapalı kimlikler (yeniden üyelik engeli) ----------
// Yalnız biberli özet saklanır: 'google:<sub>', 'tg:<id>', 'eposta:<adres>'.
const kimlikOzeti = (env, tur, deger) => biberliOzet(env, 'kapali', `${tur}:${String(deger).toLowerCase()}`);
export async function kimlikKapaliMi(env, kimlik) {
  const adaylar = [];
  if (kimlik.google_sub) adaylar.push(await kimlikOzeti(env, 'google', kimlik.google_sub));
  if (kimlik.tg_id && kimlik.tg_id > 0) adaylar.push(await kimlikOzeti(env, 'tg', kimlik.tg_id));
  if (kimlik.eposta) adaylar.push(await kimlikOzeti(env, 'eposta', kimlik.eposta));
  if (!adaylar.length) return false;
  const r = await env.DB.prepare(`SELECT 1 AS x FROM kapali_kimlikler WHERE ozet IN (${adaylar.map(() => '?').join(',')}) LIMIT 1`).bind(...adaylar).first();
  return !!r;
}

// ---------- silme yardımcıları (D1 deyimleri döner; çağıran tek batch'te çalıştırır) ----------
// Bir yanıtın kalıcı silinmesi: aldığı faydalı oylar yazarın itibarından düşer, ona verilen yanıtlar yerinde kalır (alıntısız).
function yanitDeyimleri(env, y) {
  const d = [];
  if (y.faydali > 0) d.push(env.DB.prepare("UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) - ?, 0) WHERE id = ? AND rol NOT IN ('sistem', 'asistan')").bind(y.faydali, y.uye_id));
  d.push(
    env.DB.prepare('DELETE FROM oylar WHERE yanit_id = ?').bind(y.id),
    env.DB.prepare('DELETE FROM sikayetler WHERE yanit_id = ?').bind(y.id),
    env.DB.prepare('UPDATE yanitlar SET ust_id = NULL WHERE ust_id = ?').bind(y.id),
    env.DB.prepare('DELETE FROM yanitlar WHERE id = ?').bind(y.id),
  );
  if (!y.gizli) d.push(env.DB.prepare('UPDATE basliklar SET yanit_sayisi = MAX(yanit_sayisi - 1, 0) WHERE id = ?').bind(y.baslik_id));
  return d;
}
// Bir başlığın (soru) bütün cevaplarıyla kalıcı silinmesi.
// Sayaçlar batch içindeki güncel değerden okunur (aynı batch'te önceki deyimler oyları zaten düşmüş olabilir).
function baslikDeyimleri(env, b) {
  const d = [
    env.DB.prepare(`UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) - (SELECT COALESCE(SUM(faydali), 0) FROM yanitlar WHERE baslik_id = ? AND uye_id = uyeler.id), 0)
      WHERE id IN (SELECT uye_id FROM yanitlar WHERE baslik_id = ?) AND rol NOT IN ('sistem', 'asistan')`).bind(b.id, b.id),
    env.DB.prepare(`UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) - COALESCE((SELECT faydali FROM basliklar WHERE id = ?), 0), 0)
      WHERE id = (SELECT uye_id FROM basliklar WHERE id = ?) AND rol NOT IN ('sistem', 'asistan')`).bind(b.id, b.id),
  ];
  d.push(
    env.DB.prepare('DELETE FROM oylar WHERE yanit_id IN (SELECT id FROM yanitlar WHERE baslik_id = ?)').bind(b.id),
    env.DB.prepare('DELETE FROM sikayetler WHERE yanit_id IN (SELECT id FROM yanitlar WHERE baslik_id = ?)').bind(b.id),
    env.DB.prepare('DELETE FROM yanitlar WHERE baslik_id = ?').bind(b.id),
    env.DB.prepare('DELETE FROM baslik_oylar WHERE baslik_id = ?').bind(b.id),
    env.DB.prepare('DELETE FROM anket_oylari WHERE baslik_id = ?').bind(b.id),
    env.DB.prepare('DELETE FROM anket_secenekleri WHERE baslik_id = ?').bind(b.id),
    env.DB.prepare('DELETE FROM takipler WHERE baslik_id = ?').bind(b.id),
    env.DB.prepare('DELETE FROM basliklar WHERE id = ?').bind(b.id),
  );
  return d;
}

// ---------- DELETE /arac/yanit/:id ----------
export async function aracYanitSil(request, env, id) {
  const { hata } = await yonetici(request, env);
  if (hata) return hata;
  const y = await env.DB.prepare('SELECT id, baslik_id, uye_id, faydali, gizli FROM yanitlar WHERE id = ?').bind(id).first();
  if (!y) return hataYanit(404, 'Mesaj bulunamadı.');
  await env.DB.batch(yanitDeyimleri(env, y));
  return jsonYanit({ tamam: true });
}
// ---------- DELETE /arac/baslik/:id ----------
export async function aracBaslikSil(request, env, id) {
  const { hata } = await yonetici(request, env);
  if (hata) return hata;
  const b = await env.DB.prepare('SELECT id, uye_id, kategori, faydali FROM basliklar WHERE id = ?').bind(id).first();
  if (!b) return hataYanit(404, 'Başlık bulunamadı.');
  if (b.kategori === 'oda') return hataYanit(400, 'Sohbet odaları silinemez; odadaki mesajları tek tek silebilirsin.');
  await env.DB.batch(baslikDeyimleri(env, b));
  return jsonYanit({ tamam: true });
}
// ---------- DELETE /arac/ozel/:id ----------
export async function aracOzelSil(request, env, id) {
  const { hata } = await yonetici(request, env);
  if (hata) return hata;
  const r = await env.DB.prepare('DELETE FROM ozel_mesajlar WHERE id = ?').bind(id).run();
  if (!r.meta.changes) return hataYanit(404, 'Mesaj bulunamadı.');
  return jsonYanit({ tamam: true });
}

// ---------- POST /arac/uye/:rumuz/kapat ----------
export async function aracHesapKapat(request, env, ham) {
  const { uye: ben, hata } = await yonetici(request, env);
  if (hata) return hata;
  const s = await uyeRumuzla(env, ham);
  if (!s) return hataYanit(404, 'Üye bulunamadı.');
  if (s.rol === 'sistem' || s.rol === 'asistan') return hataYanit(400, 'Bu hesap kapatılamaz.');
  if (s.id === ben.id) return hataYanit(400, 'Kendi hesabını buradan kapatamazsın.');
  // başka bir yönetici (gizli ya da rolü yönetici) bu araçla kapatılamaz
  if (s.rol === 'yonetici' || (await gizliYoneticiMi(env, s.id))) return hataYanit(400, 'Bu hesap kapatılamaz.');
  const k = await env.DB.prepare('SELECT id, rumuz, google_sub, tg_id, eposta FROM uyeler WHERE id = ?').bind(s.id).first();
  const X = k.id;
  const d = [];
  // 1) yeniden üyelik engeli: yalnız kimlik özetleri
  const t = simdi();
  if (k.google_sub) d.push(env.DB.prepare('INSERT OR IGNORE INTO kapali_kimlikler (ozet, olusma) VALUES (?, ?)').bind(await kimlikOzeti(env, 'google', k.google_sub), t));
  if (k.tg_id && k.tg_id > 0) d.push(env.DB.prepare('INSERT OR IGNORE INTO kapali_kimlikler (ozet, olusma) VALUES (?, ?)').bind(await kimlikOzeti(env, 'tg', k.tg_id), t));
  if (k.eposta) d.push(env.DB.prepare('INSERT OR IGNORE INTO kapali_kimlikler (ozet, olusma) VALUES (?, ?)').bind(await kimlikOzeti(env, 'eposta', k.eposta), t));
  d.push(env.DB.prepare('INSERT OR REPLACE INTO ayrilmis_rumuzlar (kat, bitis) VALUES (?, ?)').bind(rumuzKat(k.rumuz), t + 180 * 86400));
  // 2) üyenin verdiği oylar başkalarının sayaçlarından düşer
  d.push(
    env.DB.prepare(`UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) - (SELECT COUNT(*) FROM oylar o JOIN yanitlar y ON y.id = o.yanit_id WHERE o.uye_id = ? AND y.uye_id = uyeler.id), 0)
      WHERE id IN (SELECT y.uye_id FROM oylar o JOIN yanitlar y ON y.id = o.yanit_id WHERE o.uye_id = ?) AND rol NOT IN ('sistem', 'asistan')`).bind(X, X),
    env.DB.prepare('UPDATE yanitlar SET faydali = MAX(faydali - 1, 0) WHERE id IN (SELECT yanit_id FROM oylar WHERE uye_id = ?)').bind(X),
    env.DB.prepare(`UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) - (SELECT COUNT(*) FROM baslik_oylar o JOIN basliklar b ON b.id = o.baslik_id WHERE o.uye_id = ? AND b.uye_id = uyeler.id), 0)
      WHERE id IN (SELECT b.uye_id FROM baslik_oylar o JOIN basliklar b ON b.id = o.baslik_id WHERE o.uye_id = ?) AND rol NOT IN ('sistem', 'asistan')`).bind(X, X),
    env.DB.prepare('UPDATE basliklar SET faydali = MAX(faydali - 1, 0) WHERE id IN (SELECT baslik_id FROM baslik_oylar WHERE uye_id = ?)').bind(X),
    env.DB.prepare('UPDATE anket_secenekleri SET oy = MAX(oy - 1, 0) WHERE EXISTS (SELECT 1 FROM anket_oylari a WHERE a.uye_id = ? AND a.baslik_id = anket_secenekleri.baslik_id AND a.sira = anket_secenekleri.sira)').bind(X),
    env.DB.prepare('DELETE FROM oylar WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM baslik_oylar WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM anket_oylari WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM sikayetler WHERE uye_id = ?').bind(X),
  );
  // 3) üyenin açtığı başlıklar (bütün cevaplarıyla). Küme tabanlı: başlık sayısı ne olursa olsun deyim sayısı sabit kalır
  //    (çok içerik açmış bir hesapta batch D1 sorgu sınırını aşmasın). Başlık sahibinin kendi itibarı hesapla birlikte silinir.
  const BX = "SELECT id FROM basliklar WHERE uye_id = ? AND kategori <> 'oda'";
  d.push(
    env.DB.prepare(`UPDATE uyeler SET itibar = MAX(COALESCE(itibar, 0) - (SELECT COALESCE(SUM(faydali), 0) FROM yanitlar WHERE baslik_id IN (${BX}) AND uye_id = uyeler.id), 0)
      WHERE id IN (SELECT uye_id FROM yanitlar WHERE baslik_id IN (${BX})) AND rol NOT IN ('sistem', 'asistan')`).bind(X, X),
    env.DB.prepare(`DELETE FROM oylar WHERE yanit_id IN (SELECT id FROM yanitlar WHERE baslik_id IN (${BX}))`).bind(X),
    env.DB.prepare(`DELETE FROM sikayetler WHERE yanit_id IN (SELECT id FROM yanitlar WHERE baslik_id IN (${BX}))`).bind(X),
    env.DB.prepare(`DELETE FROM yanitlar WHERE baslik_id IN (${BX})`).bind(X),
    env.DB.prepare(`DELETE FROM baslik_oylar WHERE baslik_id IN (${BX})`).bind(X),
    env.DB.prepare(`DELETE FROM anket_oylari WHERE baslik_id IN (${BX})`).bind(X),
    env.DB.prepare(`DELETE FROM anket_secenekleri WHERE baslik_id IN (${BX})`).bind(X),
    env.DB.prepare(`DELETE FROM takipler WHERE baslik_id IN (${BX})`).bind(X),
    env.DB.prepare("DELETE FROM basliklar WHERE uye_id = ? AND kategori <> 'oda'").bind(X),
  );
  // 4) başka başlıklardaki cevapları ve sohbet mesajları
  d.push(
    env.DB.prepare(`UPDATE basliklar SET yanit_sayisi = MAX(yanit_sayisi - (SELECT COUNT(*) FROM yanitlar WHERE baslik_id = basliklar.id AND uye_id = ? AND gizli = 0), 0)
      WHERE id IN (SELECT baslik_id FROM yanitlar WHERE uye_id = ?)`).bind(X, X),
    env.DB.prepare('DELETE FROM oylar WHERE yanit_id IN (SELECT id FROM yanitlar WHERE uye_id = ?)').bind(X),
    env.DB.prepare('DELETE FROM sikayetler WHERE yanit_id IN (SELECT id FROM yanitlar WHERE uye_id = ?)').bind(X),
    env.DB.prepare('UPDATE yanitlar SET ust_id = NULL WHERE ust_id IN (SELECT id FROM yanitlar WHERE uye_id = ?)').bind(X),
    env.DB.prepare('DELETE FROM yanitlar WHERE uye_id = ?').bind(X),
  );
  // 5) özel mesajlar, engeller, takip, fotoğraf, katiplik, başvurdum işaretleri ve hesabın kendisi
  d.push(
    env.DB.prepare('DELETE FROM ozel_mesajlar WHERE gonderen = ? OR alici = ?').bind(X, X),
    env.DB.prepare('DELETE FROM engeller WHERE uye_id = ? OR engellenen = ?').bind(X, X),
    env.DB.prepare('DELETE FROM ozel_sikayetler WHERE sikayet_eden = ? OR sikayet_edilen = ?').bind(X, X),
    env.DB.prepare('DELETE FROM takipler WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM fotolar WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM foto_bildirimleri WHERE uye_id = ? OR bildiren = ?').bind(X, X),
    env.DB.prepare('DELETE FROM uye_katip WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM basvurular WHERE kimlik = ?').bind(`u${X}`),
    env.DB.prepare('DELETE FROM gizli_yoneticiler WHERE uye_id = ?').bind(X),
    env.DB.prepare('DELETE FROM uyeler WHERE id = ?').bind(X),
  );
  await env.DB.batch(d);
  return jsonYanit({ tamam: true });
}
