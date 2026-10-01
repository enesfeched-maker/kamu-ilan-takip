// Bildirim iletileri ve dakikalık cron akışı (TASARIM.md "Sürüm 2").
import { tg as gercekTg } from './telegram.js';
import { uygunMu, bugunIstanbul, sureDoldu, kelimelerKucult } from './eslestir.js';
import { sponsorlariOku, sponsorSec } from './sponsor.js';

const GERCEK_BEKLE = (ms) => new Promise((r) => setTimeout(r, ms));
const SQL_BUTCE = 40; // çağrı başına D1 ifadesi
const ISTEK_BUTCE = 30; // çağrı başına dış istek
const PARAM_MAX = 100; // ifade başına bağlı parametre
const JSON_BAYT_MAX = 90000; // ifade başına 100 KB sınırının altında kalmak için
const CIFT_MAX = 2000; // çağrı başına kullanıcı x ilan değerlendirmesi (10 ms CPU)
const GUNLUK_MAX = 15; // kullanıcı başına günlük ilan iletisi
const KILIT_MS = 55000;
const BOSALTMA_MAX = 25;
const KULLANICI_ILETI_MAX = 10;
const SAYFA_BOYUTU = 200;
const TARAMA_ARALIGI_MS = 30 * 60 * 1000;

export function kacis(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
const kacisAttr = (s) => kacis(s).replace(/"/g, '&quot;');

export function tarihGoster(t) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(t || '');
  return m ? `${m[3]}.${m[2]}.${m[1]}` : '';
}

function ilanBaglanti(ilan, env) {
  return ilan.sayfa || ilan.link || env.SITE_URL || '';
}

function duyuruEtiketi(ilan) {
  const d = ilan.duyuru_turu;
  if (!d) return '';
  const simge = String(d).toLocaleLowerCase('tr').includes('iptal') ? '⚠️' : '📝';
  return `${simge} ${kacis(d)}: `;
}

const sponsorSatiri = (sponsor) => {
  if (!sponsor || !sponsor.metin) return null;
  const https = typeof sponsor.link === 'string' && sponsor.link.startsWith('https://');
  const metin = https ? `<a href="${kacisAttr(sponsor.link)}">${kacis(sponsor.metin)}</a>` : kacis(sponsor.metin);
  return `— Sponsorlu: ${metin}`;
};

export function ilanMesaji(ilan, sponsor, env) {
  const satirlar = [`${duyuruEtiketi(ilan)}<b>${kacis(ilan.baslik)}</b>`];
  if (ilan.kurum) satirlar.push(kacis(ilan.kurum));
  if (Array.isArray(ilan.iller) && ilan.iller.length) satirlar.push(`📍 ${kacis(ilan.iller.join(', '))}`);
  if (ilan.son_tarih) satirlar.push(`📅 Son başvuru: ${tarihGoster(ilan.son_tarih)}`);
  satirlar.push(`<a href="${kacisAttr(ilanBaglanti(ilan, env))}">İlanı incele</a>`);
  const sp = sponsorSatiri(sponsor);
  if (sp) satirlar.push('', sp);
  return { text: satirlar.join('\n'), parse_mode: 'HTML', link_preview_options: { is_disabled: true } };
}

export function hatirlatmaMesaji(ilan, env) {
  const satirlar = [`⏰ <b>Yarın son gün:</b> ${kacis(ilan.baslik)}`];
  if (ilan.kurum) satirlar.push(kacis(ilan.kurum));
  if (ilan.son_tarih) satirlar.push(`📅 Son başvuru: ${tarihGoster(ilan.son_tarih)}`);
  satirlar.push(`<a href="${kacisAttr(ilanBaglanti(ilan, env))}">İlanı incele</a>`);
  return { text: satirlar.join('\n'), parse_mode: 'HTML', link_preview_options: { is_disabled: true } };
}

async function ilanlariCek(env, fetchFn) {
  const r = await fetchFn(env.ILAN_URL);
  if (!r.ok) throw new Error(`İlan verisi alınamadı (${r.status})`);
  const veri = await r.json();
  return Array.isArray(veri.ilanlar) ? veri.ilanlar : [];
}

function jsonListe(s) {
  if (Array.isArray(s)) return s;
  try { const v = JSON.parse(s || '[]'); return Array.isArray(v) ? v : []; } catch { return []; }
}

function kullaniciCoz(satir) {
  return {
    ...satir,
    duzeyler: jsonListe(satir.duzeyler),
    iller: jsonListe(satir.iller),
    kategoriler: jsonListe(satir.kategoriler),
    kelimeler: jsonListe(satir.kelimeler),
  };
}

export async function acikIlanOzeti(env, kullanici, bagimliliklar = {}, simdi = new Date()) {
  const fetchFn = bagimliliklar.fetch || fetch;
  const bugun = bugunIstanbul(simdi);
  const site = kacis(env.SITE_URL);
  let ilanlar;
  try { ilanlar = await ilanlariCek(env, fetchFn); } catch { return `İlan listesine şu an ulaşılamadı. Güncel ilanlar: ${site}`; }
  const uygunlar = ilanlar
    .filter((i) => uygunMu(i, { ...kullanici, aktif: 1, onay: 1 }, bugun, simdi))
    .sort((a, b) => {
      if (!a.son_tarih && !b.son_tarih) return 0;
      if (!a.son_tarih) return 1;
      if (!b.son_tarih) return -1;
      return String(a.son_tarih).localeCompare(String(b.son_tarih));
    });
  if (!uygunlar.length) {
    return `Şu an tercihlerine uyan açık ilan görünmüyor. Yeni bir ilan çıkınca sana haber vereceğim.\nTüm ilanlar: ${site}`;
  }
  const satirlar = uygunlar.slice(0, 5).map((i) => `• ${kacis(i.baslik)} — ${i.son_tarih ? tarihGoster(i.son_tarih) : 'tarih yok'}`);
  return `Şu an tercihlerine uyan ${uygunlar.length} açık ilan var. Son tarihi en yakın olanlar:\n${satirlar.join('\n')}\n\nTümü: ${site}`;
}

// ---------------------------------------------------------------- cron

function istanbulSaat(simdi) {
  const p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Istanbul', hour: '2-digit', hourCycle: 'h23' }).formatToParts(simdi);
  return Number(p.find((x) => x.type === 'hour').value);
}

const yerTutucu = (n, k) => Array.from({ length: n }, () => `(${Array(k).fill('?').join(',')})`).join(',');
const yerTutucuListe = (n) => Array(n).fill('?').join(',');
const kodlayici = new TextEncoder();

// Dizi öğelerini JSON bayt sınırına göre parçalar (her parça tek ifade).
function jsonParcala(dizi) {
  const parcalar = [];
  let gecerli = [];
  let bayt = 2;
  for (const o of dizi) {
    const b = kodlayici.encode(JSON.stringify(o)).length + 1;
    if (gecerli.length && bayt + b > JSON_BAYT_MAX) { parcalar.push(gecerli); gecerli = []; bayt = 2; }
    gecerli.push(o); bayt += b;
  }
  if (gecerli.length) parcalar.push(gecerli);
  return parcalar.map((p) => JSON.stringify(p));
}

function veriOlustur(i) {
  return JSON.stringify({
    baslik: i.baslik, kurum: i.kurum, son_tarih: i.son_tarih || null, son_zaman: i.son_zaman || null,
    iller: i.iller || [], ogrenim: i.ogrenim || [], kategori: i.kategori || null,
    duyuru_turu: i.duyuru_turu || null, sayfa: i.sayfa || null,
  });
}
const kimlikler = (i) => [...new Set([i.id, ...(Array.isArray(i.kimlikler) ? i.kimlikler : [])])];

export async function cronCalistir(env, simdi = new Date(), bagimliliklar = {}) {
  const tgGercek = bagimliliklar.tg || gercekTg;
  const bekle = bagimliliklar.bekle || GERCEK_BEKLE;
  const fetchGercek = bagimliliklar.fetch || fetch;
  const sonuc = { yeni: 0, gonderilen: 0, hatirlatma: 0, hata: 0, sql: 0, istek: 0, cift: 0, kilitli: false, tokenHatasi: false };

  const hazirla = (q, a) => { sonuc.sql++; return env.DB.prepare(q).bind(...a); };
  const tum = async (q, ...a) => (await hazirla(q, a).all()).results || [];
  const calis = (q, ...a) => hazirla(q, a).run();
  // Cron gönderimleri yeniden denemesiz; her çağrı sayılır.
  const tgSay = (e, m, p) => { sonuc.istek++; return tgGercek(e, m, p, { yeniden: false }); };
  const fetchSay = (u) => { sonuc.istek++; return fetchGercek(u); };

  // Süreli kilit: aynı anda iki çağrı çalışmasın (çift gönderimi önler).
  const simdiMs = simdi.getTime();
  await calis("INSERT OR IGNORE INTO meta (anahtar, deger) VALUES ('kilit', '0')");
  const kilitSonuc = await calis("UPDATE meta SET deger = ? WHERE anahtar = 'kilit' AND CAST(deger AS INTEGER) < ?", String(simdiMs + KILIT_MS), simdiMs);
  const degisen = kilitSonuc && kilitSonuc.meta && kilitSonuc.meta.changes !== undefined ? kilitSonuc.meta.changes : kilitSonuc && kilitSonuc.changes;
  if (!degisen) { sonuc.kilitli = true; return sonuc; }
  try {
    await isle();
  } finally {
    try { await calis("UPDATE meta SET deger = '0' WHERE anahtar = 'kilit'"); } catch { /* süre dolunca kendiliğinden açılır */ }
  }
  return sonuc;

  async function isle() {
    const bugun = bugunIstanbul(simdi);
    const saat = istanbulSaat(simdi);
    const zaman = simdi.toISOString();
    const bugunBasi = new Date(`${bugun}T00:00:00+03:00`).toISOString();
    const kalan = () => SQL_BUTCE - sonuc.sql - 1; // 1 = kilidi bırakma

    const meta = {};
    for (const r of await tum('SELECT anahtar, deger FROM meta')) meta[r.anahtar] = r.deger;
    const metaYaz = (ciftler) => calis(
      `INSERT OR REPLACE INTO meta (anahtar, deger) VALUES ${yerTutucu(ciftler.length, 2)}`,
      ...ciftler.flat(),
    );

    // 1) Boşaltma ----------------------------------------------------------
    if (saat >= 8 && saat <= 22) {
      await calis('DELETE FROM kuyruk WHERE chat_id NOT IN (SELECT chat_id FROM kullanicilar WHERE aktif = 1 AND onay = 1)');
      // Sohbet başına çağrıda en çok bir ileti: yalnız o sohbetin en eski satırı.
      const satirlar = await tum(
        `SELECT k.id, k.chat_id, k.ilan_id, k.tur, b.veri, u.duzeyler AS u_duzeyler, u.iller AS u_iller, u.kategoriler AS u_kategoriler
         FROM kuyruk k INNER JOIN kullanicilar u ON u.chat_id = k.chat_id AND u.aktif = 1 AND u.onay = 1
         LEFT JOIN bilinen_ilanlar b ON b.ilan_id = k.ilan_id
         WHERE k.id = (SELECT MIN(k2.id) FROM kuyruk k2 WHERE k2.chat_id = k.chat_id)
         ORDER BY k.id LIMIT ${BOSALTMA_MAX}`,
      );
      if (satirlar.length) {
        const sponsorlar = await sponsorlariOku(env, bugun).catch(() => []);
        sonuc.sql++; // sponsorlariOku bir sorgu
        const silinecek = [];
        const ilanGonderilen = [];
        const hatirlatildi = [];
        const engelli = new Set();
        let durdur = false;
        for (const s of satirlar) {
          if (durdur) break;
          let veri = null;
          if (s.tur !== 'fazla') {
            try { veri = s.veri ? JSON.parse(s.veri) : null; } catch { veri = null; }
            if (!veri || sureDoldu(veri, bugun, simdi)) { silinecek.push(s.id); continue; }
          }
          let mesaj;
          if (s.tur === 'fazla') {
            mesaj = { text: `+${kacis(String(s.ilan_id).replace(/^\+/, ''))} ilan daha: ${kacis(env.SITE_URL)}`, parse_mode: 'HTML', link_preview_options: { is_disabled: true } };
          } else if (s.tur === 'hatirlatma') {
            mesaj = hatirlatmaMesaji(veri, env);
          } else {
            const k = { duzeyler: jsonListe(s.u_duzeyler), iller: jsonListe(s.u_iller), kategoriler: jsonListe(s.u_kategoriler) };
            mesaj = ilanMesaji(veri, await sponsorSec(env, k, veri, bugun, sponsorlar), env);
          }
          try {
            await tgSay(env, 'sendMessage', { chat_id: s.chat_id, ...mesaj });
            silinecek.push(s.id);
            if (s.tur === 'ilan') { ilanGonderilen.push(s); sonuc.gonderilen++; }
            else if (s.tur === 'hatirlatma') { hatirlatildi.push(s); sonuc.hatirlatma++; }
            await bekle(40);
          } catch (e) {
            const kod = e && e.kod;
            if (kod === 403) engelli.add(s.chat_id);
            else if (kod === 429) { durdur = true; sonuc.hata++; }
            else if (kod === 401 || kod === 404) {
              // Geçersiz/iptal edilmiş token: iletiye özgü değil; durdur, satırı tut.
              durdur = true; sonuc.hata++;
              if (!sonuc.tokenHatasi) console.error('Telegram token reddedildi');
              sonuc.tokenHatasi = true;
            }
            else if (kod >= 400 && kod < 500) { silinecek.push(s.id); sonuc.hata++; }
            else sonuc.hata++; // 5xx / ağ: kuyrukta kalır
          }
        }
        if (silinecek.length) await calis(`DELETE FROM kuyruk WHERE id IN (${yerTutucuListe(silinecek.length)})`, ...silinecek);
        if (ilanGonderilen.length) {
          await calis(
            `INSERT OR IGNORE INTO gonderilen (chat_id, ilan_id, zaman) VALUES ${yerTutucu(ilanGonderilen.length, 3)}`,
            ...ilanGonderilen.flatMap((s) => [s.chat_id, s.ilan_id, zaman]),
          );
        }
        if (hatirlatildi.length) {
          await calis(
            `UPDATE gonderilen SET hatirlatildi = 1 WHERE (chat_id, ilan_id) IN (VALUES ${yerTutucu(hatirlatildi.length, 2)})`,
            ...hatirlatildi.flatMap((s) => [s.chat_id, s.ilan_id]),
          );
        }
        if (engelli.size) {
          const ids = [...engelli];
          await calis(`UPDATE kullanicilar SET aktif = 0 WHERE chat_id IN (${yerTutucuListe(ids.length)})`, ...ids);
          await calis(`DELETE FROM kuyruk WHERE chat_id IN (${yerTutucuListe(ids.length)})`, ...ids);
        }
      }
    }

    // 2) Hatırlatma (günde bir kez, 09:00 sonrası ilk çağrı) ----------------
    if (saat >= 9 && meta.son_hatirlatma_gunu !== bugun) {
      const [y, a, g] = bugun.split('-').map(Number);
      const yarin = new Date(Date.UTC(y, a - 1, g + 1)).toISOString().slice(0, 10);
      await calis(
        `INSERT OR IGNORE INTO kuyruk (chat_id, ilan_id, tur)
         SELECT g.chat_id, g.ilan_id, 'hatirlatma' FROM gonderilen g
         JOIN bilinen_ilanlar b ON b.ilan_id = g.ilan_id JOIN kullanicilar u ON u.chat_id = g.chat_id
         WHERE b.son_tarih = ? AND g.hatirlatildi = 0 AND g.zaman < ? AND u.aktif = 1 AND u.onay = 1 AND u.hatirlatma = 1`,
        yarin, bugunBasi,
      );
      await metaYaz([['son_hatirlatma_gunu', bugun]]);
    }

    // 3) Tarama ---------------------------------------------------------------
    const sonTarama = meta.son_tarama ? Date.parse(meta.son_tarama) : 0;
    const devam = meta.tarama_imleci !== undefined && meta.tarama_imleci !== null;
    if (devam || !(sonTarama > simdiMs - TARAMA_ARALIGI_MS)) {
      let ilanlar = null;
      try { ilanlar = await ilanlariCek(env, fetchSay); } catch { sonuc.hata++; }
      if (ilanlar) await tara(ilanlar);
    }

    async function tara(ilanlar) {
      const bitir = async () => {
        await calis("DELETE FROM meta WHERE anahtar IN ('tarama_imleci', 'tarama_ilanlari', 'ilk_ofset')");
        await metaYaz([['son_tarama', zaman]]);
      };
      const bilinenYaz = async (satirlar) => { // [ilan_id, ana_id, son_tarih|null, veri|null]
        for (const p of jsonParcala(satirlar)) {
          await calis(
            `INSERT OR IGNORE INTO bilinen_ilanlar (ilan_id, ana_id, son_tarih, veri, ilk_gorulme)
             SELECT json_extract(value, '$[0]'), json_extract(value, '$[1]'), json_extract(value, '$[2]'), json_extract(value, '$[3]'), ?
             FROM json_each(?)`, zaman, p,
          );
        }
      };
      const kayitlar = (i, ana) => {
        const r = [[ana, ana, i.son_tarih || null, veriOlustur(i)]];
        for (const k of kimlikler(i)) if (k !== ana) r.push([k, ana, null, null]);
        return r;
      };

      // İlk çalıştırma: her şeyi "bilinen" yap, kimseye kuyruk yazma.
      if (!devam) {
        const var_ = await tum('SELECT 1 AS x FROM bilinen_ilanlar LIMIT 1');
        if (var_.length === 0) {
          await bilinenYaz(ilanlar.flatMap((i) => kayitlar(i, i.id)));
          await bitir();
          return;
        }
      }

      let yeniler; // [{ilan, ana}]
      if (devam) {
        let idler = [];
        try { idler = JSON.parse(meta.tarama_ilanlari || '[]'); } catch { idler = []; }
        const set = new Set(idler);
        yeniler = [];
        for (const i of ilanlar) {
          const ana = kimlikler(i).find((k) => set.has(k));
          if (ana) yeniler.push({ ilan: i, ana });
        }
      } else {
        const tumKimlikler = [...new Set(ilanlar.flatMap(kimlikler))];
        const bilinen = new Map();
        for (const p of jsonParcala(tumKimlikler)) {
          for (const r of await tum('SELECT ilan_id, ana_id, son_tarih FROM bilinen_ilanlar WHERE ilan_id IN (SELECT value FROM json_each(?))', p)) {
            bilinen.set(r.ilan_id, r);
          }
        }
        yeniler = [];
        const eklenecek = [];
        const guncellenecek = []; // [ana, son_tarih, veri]
        for (const i of ilanlar) {
          const ids = kimlikler(i);
          const taninan = ids.find((k) => bilinen.has(k));
          if (!taninan) {
            yeniler.push({ ilan: i, ana: i.id });
            eklenecek.push(...kayitlar(i, i.id));
          } else {
            const ana = bilinen.get(taninan).ana_id;
            const bilinmeyen = ids.filter((k) => !bilinen.has(k));
            for (const k of bilinmeyen) eklenecek.push([k, ana, null, null]);
            const anaSatir = bilinen.get(ana);
            const degisti = anaSatir ? (anaSatir.son_tarih || null) !== (i.son_tarih || null) : bilinmeyen.length > 0;
            if (bilinmeyen.length || degisti) guncellenecek.push([ana, i.son_tarih || null, veriOlustur(i)]);
          }
        }
        for (const p of jsonParcala(guncellenecek)) {
          await calis(
            `UPDATE bilinen_ilanlar SET son_tarih = j.s, veri = j.v
             FROM (SELECT json_extract(value, '$[0]') AS a, json_extract(value, '$[1]') AS s, json_extract(value, '$[2]') AS v FROM json_each(?)) AS j
             WHERE ilan_id = j.a`, p,
          );
        }
        await bilinenYaz(eklenecek);
        sonuc.yeni = yeniler.length;
        if (!yeniler.length) { await metaYaz([['son_tarama', zaman]]); return; }
        await metaYaz([['tarama_ilanlari', JSON.stringify(yeniler.map((y) => y.ana))], ['tarama_imleci', '0']]);
      }

      // Süresi dolmuş yeni ilanlar hiç değerlendirilmez (ilan başına bir kez).
      const aktifler = yeniler.filter((y) => !sureDoldu(y.ilan, bugun, simdi));
      if (!aktifler.length) { await bitir(); return; }

      // Daha önce gönderilmiş çiftler (normalde boş)
      const gonderilmis = new Set();
      for (const p of jsonParcala(aktifler.map((y) => y.ana))) {
        for (const r of await tum('SELECT chat_id, ilan_id FROM gonderilen WHERE ilan_id IN (SELECT value FROM json_each(?))', p)) {
          gonderilmis.add(`${r.chat_id}|${r.ilan_id}`);
        }
      }

      let imlec = devam ? Number(meta.tarama_imleci) || 0 : 0;
      let cift = 0;
      for (;;) {
        if (kalan() < 8) return;
        if (cift > 0 && cift + aktifler.length > CIFT_MAX) return; // sonraki dakika devam
        const limit = Math.min(SAYFA_BOYUTU, Math.max(1, Math.floor((CIFT_MAX - cift) / aktifler.length)));
        const kullanicilar = await tum(
          'SELECT * FROM kullanicilar WHERE aktif = 1 AND onay = 1 AND chat_id > ? ORDER BY chat_id LIMIT ?', imlec, limit,
        );
        if (!kullanicilar.length) { await bitir(); return; }

        // Sayfadaki kullanıcıların bugünkü gönderilen + bekleyen ilan sayıları: tek gruplu sorgu.
        const chatJson = JSON.stringify(kullanicilar.map((k) => k.chat_id));
        const sayimlar = new Map();
        for (const r of await tum(
          `SELECT chat_id, COUNT(*) AS n FROM (
             SELECT chat_id FROM gonderilen WHERE chat_id IN (SELECT value FROM json_each(?)) AND zaman >= ?
             UNION ALL
             SELECT chat_id FROM kuyruk WHERE chat_id IN (SELECT value FROM json_each(?)) AND tur = 'ilan'
           ) GROUP BY chat_id`, chatJson, bugunBasi, chatJson,
        )) sayimlar.set(r.chat_id, r.n);

        const satirlar = [];
        for (const satir of kullanicilar) {
          const k = kullaniciCoz(satir);
          k.kelimelerKucuk = kelimelerKucult(k.kelimeler);
          const uygun = [];
          for (const y of aktifler) {
            if (gonderilmis.has(`${k.chat_id}|${y.ana}`)) continue;
            if (uygunMu(y.ilan, k, bugun, simdi, true)) uygun.push(y.ana);
          }
          cift += aktifler.length;
          imlec = k.chat_id;
          const hak = Math.max(0, Math.min(KULLANICI_ILETI_MAX, GUNLUK_MAX - (sayimlar.get(k.chat_id) || 0)));
          for (const ana of uygun.slice(0, hak)) satirlar.push([k.chat_id, ana, 'ilan']);
          if (uygun.length > hak) satirlar.push([k.chat_id, `+${uygun.length - hak}`, 'fazla']);
        }
        for (const p of jsonParcala(satirlar)) {
          await calis(
            `INSERT OR IGNORE INTO kuyruk (chat_id, ilan_id, tur)
             SELECT json_extract(value, '$[0]'), json_extract(value, '$[1]'), json_extract(value, '$[2]') FROM json_each(?)`, p,
          );
        }
        sonuc.cift = cift;
        if (kullanicilar.length < limit) { await bitir(); return; }
        await metaYaz([['tarama_imleci', String(imlec)]]);
      }
    }
  }
}