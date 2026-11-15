// Yönetici özeti: sahibin analiz panelindeki "Forum" bölümü için tek JSON (GET /yonetim/ozet, X-Yonetici anahtarı).
// Birkaç toplu sorgu; zamanlı olanlar olusma/son_hareket indekslerini kullanır. Sistem ve asistan satırları insan etkinliğine sayılmaz.
// index.js ile döngüsel içe aktarma güvenlidir: yardımcılar yalnız istek sırasında çağrılır.
import { jsonYanit, hataYanit, simdi, KATEGORILER } from './yardimci.js';
import { yoneticiMi } from './index.js';

const GUN = 86400;
const TR = 3 * 3600; // Türkiye saati UTC+3 (yaz saati yok)
const INSAN = "(SELECT id FROM uyeler WHERE rol IN ('sistem', 'asistan'))";
const sayi = (v) => Number(v) || 0;

export async function yonetimOzet(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const t = simdi();
  const t1 = t - GUN, t7 = t - 7 * GUN, t30 = t - 30 * GUN;
  const bugunBas = Math.floor((t + TR) / GUN) * GUN - TR; // Türkiye gününün başlangıcı (unix)
  const seriBas = bugunBas - 29 * GUN;
  const db = env.DB;
  const ilk = (sql, ...b) => db.prepare(sql).bind(...b).first();
  const hepsi = async (sql, ...b) => (await db.prepare(sql).bind(...b).all()).results;
  const gunlu = (tablo, kosul, alan = 'olusma') => hepsi(
    `SELECT strftime('%Y-%m-%d', ${alan} + ${TR}, 'unixepoch') AS g, COUNT(*) AS n FROM ${tablo} WHERE ${kosul} GROUP BY g`, seriBas,
  );

  const [uy, uyeG, soruG, cevapG, sohbetG, ozelG, yazanlar, soru, ilkCevap, kat, populer, odalar, odaMesaj, takip, sGenel, sOzel, engel] = await Promise.all([
    ilk(`SELECT COUNT(*) AS toplam, SUM(kayit >= ?) AS g1, SUM(kayit >= ?) AS g7, SUM(kayit >= ?) AS g30,
           SUM(tg_id > 0) AS telegram, SUM(google_sub IS NOT NULL) AS google, SUM(sifre_ozet IS NOT NULL) AS sifre,
           SUM(kurucu = 1) AS kurucu, SUM(engelli = 1) AS engelli, SUM(dm_acik = 0) AS dm_kapali
         FROM uyeler WHERE rol NOT IN ('sistem', 'asistan')`, t1, t7, t30),
    gunlu('uyeler', "kayit >= ? AND rol NOT IN ('sistem', 'asistan')", 'kayit'),
    gunlu('basliklar', `olusma >= ? AND gizli = 0 AND kategori NOT IN ('oda', 'ilan') AND uye_id NOT IN ${INSAN}`),
    hepsi(`SELECT strftime('%Y-%m-%d', y.olusma + ${TR}, 'unixepoch') AS g, COUNT(*) AS n FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id
           WHERE y.olusma >= ? AND b.kategori != 'oda' AND y.uye_id NOT IN ${INSAN} GROUP BY g`, seriBas),
    hepsi(`SELECT strftime('%Y-%m-%d', y.olusma + ${TR}, 'unixepoch') AS g, COUNT(*) AS n FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id
           WHERE y.olusma >= ? AND b.kategori = 'oda' AND y.uye_id NOT IN ${INSAN} GROUP BY g`, seriBas),
    gunlu('ozel_mesajlar', `olusma >= ? AND gonderen NOT IN ${INSAN}`),
    // aktif yazan: son 30 günde yazan her üyenin son yazma zamanı (soru + cevap + sohbet), eşikler aşağıda sayılır
    hepsi(`SELECT uye_id, MAX(olusma) AS son FROM (
             SELECT uye_id, olusma FROM yanitlar WHERE olusma >= ?
             UNION ALL SELECT uye_id, olusma FROM basliklar WHERE olusma >= ?)
           WHERE uye_id NOT IN ${INSAN} GROUP BY uye_id`, t30, t30),
    ilk(`SELECT COUNT(*) AS toplam, SUM(yanit_sayisi = 0 AND sabit = 0) AS cevapsiz FROM basliklar
         WHERE gizli = 0 AND kategori NOT IN ('oda', 'ilan', 'etkinlik') AND uye_id NOT IN ${INSAN}`),
    ilk(`SELECT COUNT(*) AS n, AVG(ilk - olusma) AS ort FROM (
           SELECT b.olusma, (SELECT MIN(y.olusma) FROM yanitlar y WHERE y.baslik_id = b.id AND y.uye_id != b.uye_id AND y.gizli = 0
                               AND y.uye_id NOT IN ${INSAN}) AS ilk
           FROM basliklar b WHERE b.olusma >= ? AND b.son_hareket >= ? AND b.gizli = 0 AND b.kategori NOT IN ('oda', 'ilan', 'etkinlik')
             AND b.uye_id NOT IN ${INSAN}) WHERE ilk IS NOT NULL`, t7, t7),
    hepsi(`SELECT kategori, COUNT(*) AS n FROM basliklar WHERE gizli = 0 AND kategori NOT IN ('oda', 'ilan') AND uye_id NOT IN ${INSAN} GROUP BY kategori`),
    hepsi(`SELECT id, baslik, yanit_sayisi FROM basliklar WHERE son_hareket >= ? AND olusma >= ? AND gizli = 0 AND yanit_sayisi > 0
             AND kategori NOT IN ('oda', 'ilan', 'etkinlik') AND uye_id NOT IN ${INSAN} ORDER BY yanit_sayisi DESC, id DESC LIMIT 10`, t30, t30),
    hepsi("SELECT id, baslik FROM basliklar WHERE kategori = 'oda' ORDER BY id"),
    hepsi(`SELECT y.baslik_id, COUNT(*) AS n FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id
           WHERE y.olusma >= ? AND b.kategori = 'oda' AND y.uye_id NOT IN ${INSAN} GROUP BY y.baslik_id`, t7),
    ilk('SELECT COUNT(*) AS n FROM takipler'),
    ilk('SELECT COUNT(DISTINCT s.yanit_id) AS n FROM sikayetler s JOIN yanitlar y ON y.id = s.yanit_id WHERE y.gizli = 0'),
    ilk('SELECT COUNT(*) AS n FROM ozel_sikayetler s JOIN uyeler b ON b.id = s.sikayet_edilen WHERE b.engelli = 0'),
    ilk('SELECT COUNT(*) AS n FROM engeller WHERE olusma >= ?', t1),
  ]);

  const harita = (liste) => new Map(liste.map((r) => [r.g, sayi(r.n)]));
  const mU = harita(uyeG), mS = harita(soruG), mC = harita(cevapG), mH = harita(sohbetG), mO = harita(ozelG);
  const seri = [];
  for (let i = 0; i < 30; i++) {
    const g = new Date((seriBas + i * GUN + TR) * 1000).toISOString().slice(0, 10);
    seri.push({ gun: g, uye: mU.get(g) || 0, soru: mS.get(g) || 0, cevap: mC.get(g) || 0, sohbet: mH.get(g) || 0, ozel: mO.get(g) || 0 });
  }
  const kodAd = new Map(KATEGORILER.map((k) => [k.kod, k.ad]));
  const odaN = new Map(odaMesaj.map((r) => [r.baslik_id, sayi(r.n)]));

  return jsonYanit({
    uretildi: t,
    uyeler: {
      toplam: sayi(uy.toplam), yeni: { g1: sayi(uy.g1), g7: sayi(uy.g7), g30: sayi(uy.g30) },
      yontem: { telegram: sayi(uy.telegram), google: sayi(uy.google), sifre: sayi(uy.sifre) },
      kurucu: sayi(uy.kurucu), engelli: sayi(uy.engelli), dm_kapali: sayi(uy.dm_kapali),
    },
    seri,
    aktif: { g1: yazanlar.filter((r) => r.son >= t1).length, g7: yazanlar.filter((r) => r.son >= t7).length, g30: yazanlar.length },
    soru: {
      toplam: sayi(soru.toplam), cevapsiz: sayi(soru.cevapsiz),
      ilk_cevap_dk: ilkCevap.n ? Math.round((sayi(ilkCevap.ort) / 60) * 10) / 10 : null, ilk_cevap_n: sayi(ilkCevap.n),
      kategori: kat.map((r) => ({ kod: r.kategori, ad: kodAd.get(r.kategori) || r.kategori, n: sayi(r.n) })).sort((a, b) => b.n - a.n),
      populer: populer.map((r) => ({ id: r.id, baslik: r.baslik, cevap: sayi(r.yanit_sayisi) })),
    },
    sohbet: odalar.map((o) => ({ id: o.id, ad: o.baslik, mesaj: odaN.get(o.id) || 0 })),
    takip: sayi(takip.n),
    sikayet: { genel: sayi(sGenel.n), ozel: sayi(sOzel.n) },
    engel_24s: sayi(engel.n),
  });
}
