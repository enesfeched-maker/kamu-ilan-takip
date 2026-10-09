// Metrik katalogu. Her metrik aynı sütunlarla döner: gun, k1, k2, say, tekil, oturum, toplam.
// Aynı SQL iki yerde çalışır: (1) tamamlanmış günün özetini çıkaran bakım işinde (tek gün),
// (2) henüz özeti çıkarılmamış günlerde (bugün) ham olaylar üzerinde. Böylece 90 günlük görünüm ham tabloyu taramaz.
//
// "tekil" ve "oturum" gün bazında sayılır; çok günlük görünümde toplanır (aynı kişi farklı günlerde tekrar sayılır,
// çünkü günlük tuz yüzünden günler arası eşleştirme zaten yapılamaz).

import { gunBasSn } from './zaman.js';
import { okumaGunlugu } from './onbellek.js';

const SUT = (k1, k2 = "''") => `gun, ${k1} AS k1, ${k2} AS k2, COUNT(*) AS say, COUNT(DISTINCT zv) AS tekil, COUNT(DISTINCT os) AS oturum`;
const ILAN_EKRANI = "(sy = 'ilan' OR (sy = 'ana' AND v = 'ilan')) AND k IS NOT NULL";

function oturumBayraklari() {
  return `SELECT gun, os,
    MAX(t = 'sayfa' AND sy = 'ana' AND COALESCE(v, 'bugun') <> 'ilan') AS a1,
    MAX(t = 'sayfa' AND (sy = 'ilan' OR (sy = 'ana' AND v = 'ilan'))) AS a2,
    MAX(t = 'tikla' AND a = 'resmi_ilan') AS a3
  FROM olaylar WHERE {G} GROUP BY gun, os`;
}

function medyan(sutun, ad) {
  return `SELECT gun, '${ad}' AS k1, '' AS k2, cnt AS say, 0 AS tekil, 0 AS oturum, n AS toplam FROM (
    SELECT gun, ${sutun} AS n, ROW_NUMBER() OVER (PARTITION BY gun ORDER BY ${sutun}) AS rn, COUNT(*) OVER (PARTITION BY gun) AS cnt
    FROM olaylar WHERE t = 'hiz' AND ${sutun} > 0 AND {G}) WHERE rn = (cnt + 1) / 2`;
}

const grup = (sql, kosul, grupSut, sira = 'say DESC') => `SELECT ${sql}, 0 AS toplam FROM olaylar WHERE ${kosul} AND {G} GROUP BY gun, ${grupSut} ORDER BY ${sira} {L}`;
const ilkOturum = (boyut, ifade, ek = '', k2 = "''") => ({
  boyut,
  sql: `SELECT ${SUT(ifade, k2)}, 0 AS toplam FROM olaylar WHERE ilk = 1 ${ek} AND {G} GROUP BY gun, k1, k2 ORDER BY say DESC {L}`,
});

export const METRIKLER = [
  { boyut: 'genel', sql: `SELECT ${SUT("''")}, 0 AS toplam FROM olaylar WHERE t = 'sayfa' AND {G} GROUP BY gun` },
  { boyut: 'yeni_geri', sql: `SELECT ${SUT("CASE yeni WHEN 1 THEN 'yeni' ELSE 'geri' END")}, 0 AS toplam FROM olaylar WHERE ilk = 1 AND {G} GROUP BY gun, k1` },
  { boyut: 'etkin', sql: `SELECT ${SUT("''")}, SUM(n * COALESCE(n2, 1)) AS toplam FROM olaylar WHERE t = 'aktif' AND {G} GROUP BY gun` },
  {
    boyut: 'oturum_ozet',
    sql: `SELECT gun, CASE WHEN sp <= 1 AND tk = 0 AND ak < 10 THEN 'hemen' ELSE 'diger' END AS k1, '' AS k2, COUNT(*) AS say, COUNT(DISTINCT zv) AS tekil, COUNT(*) AS oturum, 0 AS toplam
      FROM (SELECT gun, os, MIN(zv) AS zv, SUM(t = 'sayfa') AS sp, SUM(t = 'tikla') AS tk, SUM(CASE WHEN t = 'aktif' THEN n * COALESCE(n2, 1) ELSE 0 END) AS ak
            FROM olaylar WHERE {G} GROUP BY gun, os HAVING sp >= 1) GROUP BY gun, k1`,
  },
  { boyut: 'isi', sql: `SELECT ${SUT('CAST(hg AS TEXT)', 'CAST(saat AS TEXT)')}, 0 AS toplam FROM olaylar WHERE t = 'sayfa' AND {G} GROUP BY gun, hg, saat` },
  ilkOturum('kaynak', "COALESCE(kaynak, 'Doğrudan')"),
  ilkOturum('rhost', 'rhost', 'AND rhost IS NOT NULL'),
  ilkOturum('utm', "us || '/' || COALESCE(um, '-')", 'AND us IS NOT NULL', "COALESCE(uc, '-')"),
  ilkOturum('ulke', 'ulke', 'AND ulke IS NOT NULL'),
  ilkOturum('sehir', 'sehir', 'AND sehir IS NOT NULL', "COALESCE(ulke, '')"),
  ilkOturum('cihaz', 'cihaz', 'AND cihaz IS NOT NULL'),
  ilkOturum('tarayici', 'tarayici', 'AND tarayici IS NOT NULL'),
  ilkOturum('isletim', 'isletim', 'AND isletim IS NOT NULL'),
  ilkOturum('genislik', 'gen', 'AND gen IS NOT NULL'),
  ilkOturum('dil', 'dil', 'AND dil IS NOT NULL'),
  { boyut: 'sayfa', sql: grup(SUT('p', "COALESCE(v, '')"), "t = 'sayfa'", 'p, v') },
  { boyut: 'gorunum', sql: grup(SUT('v'), "t = 'sayfa' AND sy = 'ana' AND v IS NOT NULL", 'v') },
  { boyut: 'gorunum_sure', sql: `SELECT ${SUT("COALESCE(v, 'bugun')")}, SUM(n * COALESCE(n2, 1)) AS toplam FROM olaylar WHERE t = 'aktif' AND sy = 'ana' AND {G} GROUP BY gun, k1 ORDER BY toplam DESC {L}` },
  { boyut: 'ilan_goruntu', sql: grup(SUT('k'), `t = 'sayfa' AND ${ILAN_EKRANI}`, 'k') },
  { boyut: 'ilan_sure', sql: `SELECT ${SUT('k')}, SUM(n * COALESCE(n2, 1)) AS toplam FROM olaylar WHERE t = 'aktif' AND ${ILAN_EKRANI} AND {G} GROUP BY gun, k ORDER BY toplam DESC {L}` },
  { boyut: 'kurum', sql: grup(SUT('k'), "t = 'sayfa' AND sy = 'kurum' AND k IS NOT NULL", 'k') },
  { boyut: 'taban', sql: grup(SUT("COALESCE(k, '')"), "t = 'sayfa' AND sy = 'taban'", 'k') },
  { boyut: 'tikla_ad', sql: grup(SUT('a'), "t = 'tikla'", 'a') },
  {
    boyut: 'tikla_hedef',
    sql: grup(SUT('a', "COALESCE(h, '') || '|' || COALESCE(x, '') || '|' || COALESCE(CAST(n AS TEXT), '')"), "t = 'tikla' AND a <> 'arama'", 'a, k2'),
  },
  { boyut: 'arama', sql: grup(SUT('x', "CASE WHEN COALESCE(n, 0) = 0 THEN 'sifir' ELSE 'var' END"), "t = 'tikla' AND a = 'arama' AND x IS NOT NULL", 'x, k2') },
  {
    boyut: 'huni',
    sql: `SELECT gun, 'huni' AS k1, '' AS k2, SUM(a1) AS say, SUM(a2) AS tekil, SUM(a3) AS oturum, SUM(a1 * a2) AS toplam FROM (${oturumBayraklari()}) GROUP BY gun
      UNION ALL
      SELECT gun, 'huni2' AS k1, '' AS k2, SUM(a2 * a3) AS say, 0, 0, 0 FROM (${oturumBayraklari()}) GROUP BY gun`,
  },
  // Kaydırma: ekran başına TEK olay (h = 'm': ulaşılan en büyük derinlik). Eski kümülatif olaylar h'siz gelir. Örneklenen olay n2 = ağırlık taşır.
  // Günlük ilan popülerlik puanı (/populer için; yalnız gün özetinde, ham günlük taramada çalışmaz): ilan başına benzersiz oturum.
  // görüntüleme + satır tıklaması + kaydet (1'er) ve resmî ilana gidiş (2). manset_tikla bilerek yok.
  {
    boyut: 'pop', yalnizOzet: true,
    sql: `SELECT gun, ilanKey AS k1, '' AS k2, SUM(w) AS say, 0 AS tekil, 0 AS oturum, 0 AS toplam FROM (
      SELECT DISTINCT gun, os, CASE WHEN t = 'sayfa' THEN k ELSE h END AS ilanKey, tur, CASE WHEN tur = 'resmi_ilan' THEN 2 ELSE 1 END AS w FROM (
        SELECT gun, os, t, k, h, CASE WHEN t = 'sayfa' THEN 'gor' ELSE a END AS tur FROM olaylar
        WHERE {G} AND ((t = 'sayfa' AND k IS NOT NULL AND (sy = 'ilan' OR (sy = 'ana' AND v = 'ilan')))
          OR (t = 'tikla' AND a IN ('satir_tikla', 'resmi_ilan', 'kaydet') AND h IS NOT NULL)))
    ) WHERE ilanKey IS NOT NULL GROUP BY gun, ilanKey ORDER BY say DESC {L}`,
  },
  { boyut: 'kaydirma', sql: `SELECT gun, CAST(n AS TEXT) AS k1, sy || CASE WHEN h = 'm' THEN '|m' ELSE '' END AS k2, SUM(COALESCE(n2, 1)) AS say, COUNT(DISTINCT zv) AS tekil, COUNT(DISTINCT os) AS oturum, 0 AS toplam FROM olaylar WHERE t = 'kaydirma' AND {G} GROUP BY gun, n, k2 ORDER BY say DESC {L}` },
  { boyut: 'hata', sql: grup(SUT('x', "COALESCE(h, '')"), "t = 'hata'", 'x, h') },
  { boyut: 'yok404', sql: grup(SUT('p'), "t = '404'", 'p') },
  { boyut: 'lcp', sql: medyan('n', 'lcp') },
  { boyut: 'ttfb', sql: medyan('n2', 'ttfb') },
];

const SAYI_ALANLARI = ['say', 'tekil', 'oturum', 'toplam'];

function hazirla(metrik, kosul, baglar, sinir) {
  const adet = metrik.sql.split('{G}').length - 1;
  const sql = metrik.sql.replaceAll('{G}', kosul).replaceAll('{L}', sinir ? `LIMIT ${sinir}` : '');
  const hepsi = [];
  for (let i = 0; i < adet; i++) hepsi.push(...baglar);
  return { sql, baglar: hepsi };
}

// Tüm metrikler TEK deyimde: koşula uyan ham satırlar bir kez okunup (MATERIALIZED CTE) bellekte tüm toplamalara beslenir.
// Önceki düzen her metrik için ham satırları yeniden tarıyordu (~30x D1 okuması).
// D1 tek deyimde en çok 5 bileşik SELECT terimine izin verir ("too many terms in compound SELECT"); metrikler bu sınıra göre
// deyimlere bölünür ve aynı batch'te gönderilir. Her deyim ham satırları bir kez okur (~30 tarama yerine ~8).
export const D1_BILESIK_SINIRI = 5;
const terimSayisi = (sql) => 1 + (sql.match(/\bUNION\s+ALL\b/gi) || []).length;
function tekSorgu(db, metrikler, kosul, baglar, sinir) {
  const gruplar = [];
  let grup = [], terim = 0;
  for (const m of metrikler) {
    const sql = `SELECT '${m.boyut}' AS boyut, gun, k1, k2, say, tekil, oturum, toplam FROM (${m.sql.replaceAll('{G}', '1').replaceAll('{L}', sinir ? `LIMIT ${sinir}` : '').replace(/FROM olaylar\b/g, 'FROM s')})`;
    const t = terimSayisi(m.sql);
    if (grup.length && terim + t > D1_BILESIK_SINIRI) { gruplar.push(grup); grup = []; terim = 0; }
    grup.push(sql); terim += t;
  }
  if (grup.length) gruplar.push(grup);
  return gruplar.map((g) => db.prepare(`WITH s AS MATERIALIZED (SELECT * FROM olaylar WHERE ${kosul}) ${g.join(' UNION ALL ')}`).bind(...baglar));
}
// Bölünmüş deyimlerin sonuçları tek sonuç gibi birleştirilir (okuma günlüğü için meta toplanır).
function sonuclariBirlestir(sonuclar) {
  return {
    results: sonuclar.flatMap((s) => s.results || []),
    meta: { rows_read: sonuclar.reduce((t, s) => t + Number(s.meta?.rows_read || 0), 0) },
  };
}
function satirlarBirlesik(sonuc) {
  return (sonuc.results || []).map((r) => {
    const o = { boyut: r.boyut, gun: r.gun, k1: String(r.k1 ?? ''), k2: String(r.k2 ?? '') };
    for (const a of SAYI_ALANLARI) o[a] = Number(r[a] || 0);
    return o;
  });
}

function satirlar(sonuc, boyut) {
  return (sonuc.results || []).map((r) => {
    const o = { boyut, gun: r.gun, k1: String(r.k1 ?? ''), k2: String(r.k2 ?? '') };
    for (const a of SAYI_ALANLARI) o[a] = Number(r[a] || 0);
    return o;
  });
}

// Tamamlanmış bir günün özetini yazar (var olanın üzerine yazar).
export async function gunOzetiYaz(db, gun, simdiSn = Math.floor(Date.now() / 1000)) {
  const sonuc = sonuclariBirlestir(await db.batch(tekSorgu(db, METRIKLER, 'ts >= ? AND ts < ?', [gunBasSn(gun), gunBasSn(gun) + 86400], 200)));
  okumaGunlugu('bakim/gun', sonuc);
  const kayitlar = satirlarBirlesik(sonuc);
  // 'pop' satırı olmayan gün bakımda yeniden özetlenir; boş günler bu yüzden işaret satırı ('_') taşır.
  if (!kayitlar.some((r) => r.boyut === 'pop')) kayitlar.push({ boyut: 'pop', gun, k1: '_', k2: '', say: 0, tekil: 0, oturum: 0, toplam: 0 });
  const yaz = kayitlar.map((r) => db.prepare('INSERT OR REPLACE INTO ozet (gun, boyut, k1, k2, say, tekil, oturum, toplam) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
    .bind(gun, r.boyut, r.k1.slice(0, 200), r.k2.slice(0, 200), r.say, r.tekil, r.oturum, r.toplam));
  await db.prepare('DELETE FROM ozet WHERE gun = ?').bind(gun).run();
  for (let i = 0; i < yaz.length; i += 80) await db.batch(yaz.slice(i, i + 80));
  await db.prepare('INSERT OR REPLACE INTO ozet_gun (gun, ts) VALUES (?, ?)').bind(gun, simdiSn).run();
  return kayitlar.length;
}

// [bas, bit] arasındaki tüm metrikler: özeti çıkmış günler ozet tablosundan, kalanlar ham olaylardan.
export async function aralikOku(db, bas, bit) {
  const ozetli = await db.prepare('SELECT gun, boyut, k1, k2, say, tekil, oturum, toplam FROM ozet WHERE gun BETWEEN ? AND ?').bind(bas, bit).all();
  // ts aralığı tek indeksi (idx_olaylar_ts) kullanır; gün sınırları Türkiye saatindedir.
  const kos = 'ts >= ? AND ts < ? AND gun NOT IN (SELECT gun FROM ozet_gun)';
  const hamMetrik = METRIKLER.filter((m) => !m.yalnizOzet);
  const sonuc = sonuclariBirlestir(await db.batch(tekSorgu(db, hamMetrik, kos, [gunBasSn(bas), gunBasSn(bit) + 86400], 0)));
  okumaGunlugu('panel/veri', ozetli, sonuc);
  const ham = satirlarBirlesik(sonuc);
  return [...satirlar(ozetli, null).map((r, i) => ({ ...r, boyut: ozetli.results[i].boyut })), ...ham];
}

// Satırları anahtara göre toplar (günler birleşir).
export function birlestir(satirListesi, boyut) {
  const m = new Map();
  for (const r of satirListesi) {
    if (r.boyut !== boyut) continue;
    const a = r.k1 + '\u0000' + r.k2;
    const o = m.get(a) || { k1: r.k1, k2: r.k2, say: 0, tekil: 0, oturum: 0, toplam: 0 };
    for (const f of SAYI_ALANLARI) o[f] += r[f];
    m.set(a, o);
  }
  return [...m.values()].sort((a, b) => (a.k1 < b.k1 ? -1 : a.k1 > b.k1 ? 1 : a.k2 < b.k2 ? -1 : a.k2 > b.k2 ? 1 : 0));
}
