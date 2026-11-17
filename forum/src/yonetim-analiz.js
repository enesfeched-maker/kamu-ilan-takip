// Yönetici analizi: sahibin analiz panelindeki "Forum" sekmesi için tek JSON (GET /yonetim/analiz?gun=7|30|90, X-Yonetici anahtarı).
// Salt okunur, yalnız toplu sorgular; dönem en çok 90 gün. Çıktıda e-posta, kimlik özeti, üye kimliği, özel mesaj metni ve
// kimin yönetici olduğu yoktur: üyelerden yalnız rumuz ve sayılar, içerikten yalnız herkese açık (gizli = 0) soru başlıkları çıkar.
// Sistem ve asistan satırları insan etkinliğine sayılmaz. index.js ile döngüsel içe aktarma güvenlidir (yardımcılar istekte çağrılır).
import { jsonYanit, hataYanit, simdi, KATEGORILER } from './yardimci.js';
import { yoneticiMi } from './index.js';

const GUN = 86400;
const TR = 3 * 3600; // Türkiye saati UTC+3 (yaz saati yok)
const DIS = "(SELECT id FROM uyeler WHERE rol IN ('sistem', 'asistan'))"; // insan olmayan hesaplar
const UYE = "rol NOT IN ('sistem', 'asistan')";
const SORU_DISI = "('oda', 'ilan', 'etkinlik')"; // üye sorusu sayılmayan başlık türleri
const GUNLER = [7, 30, 90];
const sayi = (v) => Number(v) || 0;
const trGun = (sn) => new Date((sn + TR) * 1000).toISOString().slice(0, 10);

function medyan(liste) {
  if (!liste.length) return null;
  const s = [...liste].sort((a, b) => a - b), o = s.length >> 1;
  return s.length % 2 ? s[o] : (s[o - 1] + s[o]) / 2;
}

export async function yonetimAnaliz(request, env) {
  if (!yoneticiMi(request, env)) return hataYanit(401, 'Yetkisiz.');
  const istenen = Number(new URL(request.url).searchParams.get('gun'));
  const gun = GUNLER.includes(istenen) ? istenen : 30;
  const t = simdi();
  const t1 = t - GUN, t7 = t - 7 * GUN, t30 = t - 30 * GUN;
  const bugunBas = Math.floor((t + TR) / GUN) * GUN - TR; // Türkiye gününün başlangıcı (unix)
  const bas = bugunBas - (gun - 1) * GUN;                 // dönem başı
  const alt = Math.min(bas, t30);                         // aktiflik eşikleri için en az 30 gün
  const db = env.DB;
  const ilk = (sql, ...b) => db.prepare(sql).bind(...b).first();
  const hepsi = async (sql, ...b) => (await db.prepare(sql).bind(...b).all()).results;
  const gunAd = (alan) => `strftime('%Y-%m-%d', ${alan} + ${TR}, 'unixepoch')`;

  const [uy, uyeG, basG, yanG, ozelG, takipG, aktif, huni, sorular, cevapsiz, cevapsizSay, enIyi, ilanS, odalar, isi, katki, top] = await Promise.all([
    ilk(`SELECT SUM(silindi IS NULL) AS toplam, SUM(silindi IS NOT NULL) AS silinen, SUM(kayit >= ?) AS yeni,
           SUM(kayit >= ?) AS g1, SUM(kayit >= ?) AS g7, SUM(kayit >= ?) AS g30,
           SUM(google_sub IS NOT NULL) AS google, SUM(tg_id > 0) AS telegram,
           SUM(eposta IS NOT NULL AND google_sub IS NULL) AS eposta, SUM(sifre_ozet IS NOT NULL) AS sifre,
           SUM(kurucu = 1 AND silindi IS NULL) AS kurucu, SUM(engelli = 1) AS engelli,
           SUM(foto_surum IS NOT NULL) AS fotolu, SUM(kart IS NOT NULL) AS kartli
         FROM uyeler WHERE ${UYE}`, bas, t1, t7, t30),
    hepsi(`SELECT ${gunAd('kayit')} AS g, COUNT(*) AS n FROM uyeler WHERE kayit >= ? AND ${UYE} GROUP BY g`, bas),
    hepsi(`SELECT ${gunAd('olusma')} AS g, SUM(kategori NOT IN ${SORU_DISI}) AS soru, SUM(anket = 1) AS anket FROM basliklar
           WHERE olusma >= ? AND gizli = 0 AND uye_id NOT IN ${DIS} GROUP BY g`, bas),
    hepsi(`SELECT ${gunAd('y.olusma')} AS g, SUM(b.kategori = 'oda') AS sohbet,
             SUM(b.kategori = 'ilan' AND y.ust_id IS NULL) AS ilan_soru,
             SUM(b.kategori != 'oda' AND NOT (b.kategori = 'ilan' AND y.ust_id IS NULL)) AS cevap
           FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id
           WHERE y.olusma >= ? AND y.uye_id NOT IN ${DIS} GROUP BY g`, bas),
    hepsi(`SELECT ${gunAd('olusma')} AS g, COUNT(*) AS n FROM ozel_mesajlar WHERE olusma >= ? AND gonderen NOT IN ${DIS} GROUP BY g`, bas),
    hepsi(`SELECT ${gunAd('olusma')} AS g, COUNT(*) AS n FROM takipler WHERE olusma >= ? AND uye_id NOT IN ${DIS} GROUP BY g`, bas),
    // yazan üyeler: soru, cevap, sohbet ve özel mesaj; "geri dönen" = dönemde en az iki farklı (Türkiye) gün yazan
    ilk(`SELECT SUM(son >= ?) AS g1, SUM(son >= ?) AS g7, SUM(son >= ?) AS g30, SUM(n > 0) AS donem, SUM(gunler >= 2) AS geri_donen FROM (
           SELECT uye_id, MAX(olusma) AS son, SUM(olusma >= ?) AS n,
                  COUNT(DISTINCT CASE WHEN olusma >= ? THEN (olusma + ${TR}) / ${GUN} END) AS gunler
           FROM (SELECT uye_id, olusma FROM yanitlar WHERE olusma >= ?
                 UNION ALL SELECT uye_id, olusma FROM basliklar WHERE olusma >= ?
                 UNION ALL SELECT gonderen AS uye_id, olusma FROM ozel_mesajlar WHERE olusma >= ?)
           WHERE uye_id NOT IN ${DIS} GROUP BY uye_id)`, t1, t7, t30, bas, bas, alt, alt, alt),
    // huni: herkese açık yazan / yalnız oy-takip-anket-özel mesaj / hiçbir iz bırakmayan (yalnız okuyan)
    ilk(`WITH yz AS (SELECT uye_id FROM yanitlar UNION SELECT uye_id FROM basliklar),
              et AS (SELECT uye_id FROM oylar UNION SELECT uye_id FROM baslik_oylar UNION SELECT uye_id FROM takipler
                     UNION SELECT uye_id FROM anket_oylari UNION SELECT gonderen FROM ozel_mesajlar)
         SELECT COUNT(*) AS toplam, SUM(yz.uye_id IS NOT NULL) AS yazan,
                SUM(yz.uye_id IS NULL AND et.uye_id IS NOT NULL) AS yalniz_etkilesim,
                SUM(yz.uye_id IS NULL AND et.uye_id IS NULL) AS iz_yok,
                SUM(u.kayit >= ?) AS yeni, SUM(u.kayit >= ? AND yz.uye_id IS NOT NULL) AS yeni_yazan
         FROM uyeler u LEFT JOIN yz ON yz.uye_id = u.id LEFT JOIN et ON et.uye_id = u.id
         WHERE u.${UYE} AND u.silindi IS NULL`, bas, bas),
    // dönemin üye soruları: yalnız zaman ve kategori döner (medyan ilk cevap süresi için), satır sayısı sınırlı
    hepsi(`SELECT b.olusma, b.kategori, (SELECT MIN(y.olusma) FROM yanitlar y WHERE y.baslik_id = b.id AND y.uye_id != b.uye_id
             AND y.gizli = 0 AND y.uye_id NOT IN ${DIS}) AS ilk
           FROM basliklar b WHERE b.olusma >= ? AND b.gizli = 0 AND b.kategori NOT IN ${SORU_DISI} AND b.uye_id NOT IN ${DIS}
           ORDER BY b.olusma DESC LIMIT 5000`, bas),
    hepsi(`SELECT id, baslik, kategori, olusma FROM basliklar WHERE gizli = 0 AND sabit = 0 AND yanit_sayisi = 0
             AND kategori NOT IN ${SORU_DISI} AND uye_id NOT IN ${DIS} ORDER BY olusma ASC, id ASC LIMIT 15`),
    ilk(`SELECT COUNT(*) AS n FROM basliklar WHERE gizli = 0 AND sabit = 0 AND yanit_sayisi = 0
           AND kategori NOT IN ${SORU_DISI} AND uye_id NOT IN ${DIS}`),
    hepsi(`SELECT b.id, b.baslik, b.kategori, b.yanit_sayisi, b.faydali, b.olusma,
             (SELECT COUNT(*) FROM takipler t WHERE t.baslik_id = b.id) AS takip
           FROM basliklar b WHERE b.olusma >= ? AND b.gizli = 0 AND b.kategori NOT IN ${SORU_DISI} AND b.uye_id NOT IN ${DIS}
             AND (b.yanit_sayisi > 0 OR b.faydali > 0)
           ORDER BY b.yanit_sayisi + b.faydali DESC, b.id DESC LIMIT 10`, bas),
    // ilan sayfasından sorulan sorular (ilan başlığına üst yanıt): insan ya da asistan cevabı aldı mı
    ilk(`SELECT COUNT(*) AS n,
           SUM(EXISTS (SELECT 1 FROM yanitlar c WHERE c.ust_id = y.id AND c.uye_id != y.uye_id AND c.uye_id NOT IN ${DIS})) AS insan,
           SUM(EXISTS (SELECT 1 FROM yanitlar c WHERE c.ust_id = y.id AND c.uye_id IN (SELECT id FROM uyeler WHERE rol = 'asistan'))) AS asistan
         FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id
         WHERE y.olusma >= ? AND b.kategori = 'ilan' AND y.ust_id IS NULL AND y.uye_id NOT IN ${DIS}`, bas),
    hepsi(`SELECT b.id, b.baslik, COUNT(y.id) AS mesaj, COUNT(DISTINCT y.uye_id) AS kisi, MAX(y.olusma) AS son
           FROM basliklar b LEFT JOIN yanitlar y ON y.baslik_id = b.id AND y.olusma >= ? AND y.uye_id NOT IN ${DIS}
           WHERE b.kategori = 'oda' AND b.gizli = 0 GROUP BY b.id ORDER BY mesaj DESC, b.id`, bas),
    hepsi(`SELECT CAST(strftime('%w', olusma + ${TR}, 'unixepoch') AS INTEGER) AS w, CAST(strftime('%H', olusma + ${TR}, 'unixepoch') AS INTEGER) AS s, COUNT(*) AS n
           FROM (SELECT uye_id, olusma FROM yanitlar WHERE olusma >= ?
                 UNION ALL SELECT uye_id, olusma FROM basliklar WHERE olusma >= ? AND kategori != 'ilan'
                 UNION ALL SELECT gonderen AS uye_id, olusma FROM ozel_mesajlar WHERE olusma >= ?)
           WHERE uye_id NOT IN ${DIS} GROUP BY w, s`, bas, bas, bas),
    hepsi(`SELECT u.rumuz, u.itibar, u.kurucu, x.soru, x.cevap, x.sohbet FROM (
             SELECT uye_id, SUM(t = 's') AS soru, SUM(t = 'c') AS cevap, SUM(t = 'h') AS sohbet FROM (
               SELECT y.uye_id, CASE WHEN b.kategori = 'oda' THEN 'h' WHEN b.kategori = 'ilan' AND y.ust_id IS NULL THEN 's' ELSE 'c' END AS t
               FROM yanitlar y JOIN basliklar b ON b.id = y.baslik_id WHERE y.olusma >= ? AND y.gizli = 0
               UNION ALL SELECT uye_id, 's' FROM basliklar WHERE olusma >= ? AND gizli = 0 AND kategori NOT IN ('oda', 'ilan'))
             GROUP BY uye_id) x JOIN uyeler u ON u.id = x.uye_id
           WHERE u.${UYE} AND u.silindi IS NULL AND u.engelli = 0
           ORDER BY x.soru + x.cevap DESC, x.sohbet DESC, u.itibar DESC LIMIT 10`, bas, bas),
    ilk(`SELECT (SELECT COUNT(*) FROM oylar) AS yanit_oy, (SELECT COUNT(*) FROM baslik_oylar) AS baslik_oy,
           (SELECT COUNT(*) FROM anket_oylari) AS anket_oy, (SELECT COUNT(*) FROM basliklar WHERE anket = 1 AND gizli = 0) AS anket,
           (SELECT COUNT(*) FROM takipler) AS takip,
           (SELECT COUNT(DISTINCT s.yanit_id) FROM sikayetler s JOIN yanitlar y ON y.id = s.yanit_id WHERE y.gizli = 0) AS sikayet,
           (SELECT COUNT(*) FROM ozel_sikayetler s JOIN uyeler b ON b.id = s.sikayet_edilen WHERE b.engelli = 0) AS ozel_sikayet,
           (SELECT COUNT(DISTINCT f.uye_id) FROM foto_bildirimleri f JOIN uyeler u ON u.id = f.uye_id AND u.foto_surum = f.surum) AS foto_bildirim,
           (SELECT COUNT(*) FROM kapali_kimlikler) AS kapali_kimlik,
           (SELECT COUNT(*) FROM engeller WHERE olusma >= ?) AS engel,
           (SELECT COUNT(*) FROM yanitlar WHERE gizli = 1 AND olusma >= ?) AS gizli_yanit,
           (SELECT COUNT(*) FROM basliklar WHERE gizli = 1 AND olusma >= ?) AS gizli_baslik`, bas, bas, bas),
  ]);

  // günlük seri (Türkiye günü): boş günler 0
  const harita = (liste, alan = 'n') => new Map(liste.map((r) => [r.g, sayi(r[alan])]));
  const m = {
    uye: harita(uyeG), soru: harita(basG, 'soru'), anket: harita(basG, 'anket'), cevap: harita(yanG, 'cevap'),
    ilan_soru: harita(yanG, 'ilan_soru'), sohbet: harita(yanG, 'sohbet'), ozel: harita(ozelG), takip: harita(takipG),
  };
  const seri = [];
  for (let i = 0; i < gun; i++) {
    const g = trGun(bas + i * GUN), satir = { gun: g };
    for (const k of Object.keys(m)) satir[k] = m[k].get(g) || 0;
    seri.push(satir);
  }
  const toplamlar = {};
  for (const k of Object.keys(m)) toplamlar[k] = seri.reduce((x, r) => x + r[k], 0);

  // soru sağlığı
  const kodAd = new Map(KATEGORILER.map((k) => [k.kod, k.ad]));
  const sureler = [], katM = new Map();
  let cevaplanan = 0, saatte = 0;
  for (const r of sorular) {
    const k = katM.get(r.kategori) || { kod: r.kategori, ad: kodAd.get(r.kategori) || r.kategori, n: 0, cevaplanan: 0 };
    k.n++;
    if (r.ilk != null) {
      const d = Math.max(0, sayi(r.ilk) - sayi(r.olusma));
      sureler.push(d); cevaplanan++; k.cevaplanan++;
      if (d <= 3600) saatte++;
    }
    katM.set(r.kategori, k);
  }
  const md = medyan(sureler);

  // saat ısısı: Pazartesi = 0
  const saat = new Array(24).fill(0);
  const isiListe = isi.map((r) => {
    const s = sayi(r.s), n = sayi(r.n);
    saat[s] += n;
    return [(sayi(r.w) + 6) % 7, s, n];
  });

  return jsonYanit({
    uretildi: t,
    gun,
    baslangic: trGun(bas),
    uyeler: {
      toplam: sayi(uy?.toplam), silinen: sayi(uy?.silinen), yeni: sayi(uy?.yeni),
      son: { g1: sayi(uy?.g1), g7: sayi(uy?.g7), g30: sayi(uy?.g30) },
      yontem: { google: sayi(uy?.google), eposta: sayi(uy?.eposta), telegram: sayi(uy?.telegram), sifre: sayi(uy?.sifre) },
      kurucu: sayi(uy?.kurucu), engelli: sayi(uy?.engelli), fotolu: sayi(uy?.fotolu), kartli: sayi(uy?.kartli),
    },
    aktif: { g1: sayi(aktif?.g1), g7: sayi(aktif?.g7), g30: sayi(aktif?.g30), donem: sayi(aktif?.donem), geri_donen: sayi(aktif?.geri_donen) },
    huni: {
      toplam: sayi(huni?.toplam), yazan: sayi(huni?.yazan), yalniz_etkilesim: sayi(huni?.yalniz_etkilesim), iz_yok: sayi(huni?.iz_yok),
      yeni: sayi(huni?.yeni), yeni_yazan: sayi(huni?.yeni_yazan),
    },
    seri,
    toplam: toplamlar,
    soru: {
      donem: sorular.length, cevaplanan, ilk_cevap_medyan_dk: md == null ? null : Math.round((md / 60) * 10) / 10, bir_saatte: saatte,
      cevapsiz: sayi(cevapsizSay?.n),
      cevapsiz_liste: cevapsiz.map((r) => ({ id: r.id, baslik: r.baslik, kategori: kodAd.get(r.kategori) || r.kategori, gun: Math.floor((t - sayi(r.olusma)) / GUN) })),
      kategori: [...katM.values()].sort((a, b) => b.n - a.n),
      en_iyi: enIyi.map((r) => ({ id: r.id, baslik: r.baslik, kategori: kodAd.get(r.kategori) || r.kategori, cevap: sayi(r.yanit_sayisi), faydali: sayi(r.faydali), takip: sayi(r.takip) })),
      ilan: { n: sayi(ilanS?.n), insan: sayi(ilanS?.insan), asistan: sayi(ilanS?.asistan) },
    },
    odalar: odalar.map((r) => ({ id: r.id, ad: r.baslik, mesaj: sayi(r.mesaj), kisi: sayi(r.kisi), son: r.son == null ? null : sayi(r.son) })),
    saat,
    isi: isiListe,
    katkilar: katki.map((r) => ({ rumuz: r.rumuz, soru: sayi(r.soru), cevap: sayi(r.cevap), sohbet: sayi(r.sohbet), itibar: sayi(r.itibar), kurucu: sayi(r.kurucu) === 1 })),
    etkilesim: {
      yanit_oy: sayi(top?.yanit_oy), baslik_oy: sayi(top?.baslik_oy), anket: sayi(top?.anket), anket_oy: sayi(top?.anket_oy), takip: sayi(top?.takip),
    },
    denetim: {
      sikayet: sayi(top?.sikayet), ozel_sikayet: sayi(top?.ozel_sikayet), foto_bildirim: sayi(top?.foto_bildirim),
      kapali_kimlik: sayi(top?.kapali_kimlik), engelli: sayi(uy?.engelli), engel: sayi(top?.engel),
      gizlenen: sayi(top?.gizli_yanit) + sayi(top?.gizli_baslik),
    },
  });
}
