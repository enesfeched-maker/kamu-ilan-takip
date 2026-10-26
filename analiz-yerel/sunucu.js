// KPSS Tercihi analizi - yerel toplayıcı. analiz/src içindeki Worker kodunu değiştirmeden Node üzerinde çalıştırır.
// Yalnız 127.0.0.1'i dinler; internete Tailscale Funnel açar (KURULUM.md). Çalıştırma: node --env-file=.env sunucu.js
import http from 'node:http';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import worker from '../analiz/src/index.js';
import { yerelD1 } from './d1.js';

const MAKS_GOVDE = 70_000; // toplama.js zaten 413 verir; burada yalnız bellek koruması

export function ortamKur(db, kaynak = process.env) {
  return {
    DB: db,
    PANEL_ANAHTARI: kaynak.PANEL_ANAHTARI || '',
    SITE_URL: kaynak.SITE_URL || 'https://kpsstercihi.com/',
    IZINLI_KOKENLER: kaynak.IZINLI_KOKENLER || 'https://kpsstercihi.com,https://www.kpsstercihi.com',
    TOPLAMA_KAPALI: kaynak.TOPLAMA_KAPALI || '0',
    ORTAM: kaynak.ORTAM || '',
    // Kota derdi yok: D1 bütçe bekçisi pratikte hiç devreye girmez.
    BUTCE_YAZMA: '1000000000000',
    BUTCE_OKUMA: '1000000000000',
  };
}

async function govdeOku(req) {
  const parcalar = []; let toplam = 0;
  for await (const p of req) { toplam += p.length; if (toplam > MAKS_GOVDE) break; parcalar.push(p); }
  return Buffer.concat(parcalar);
}

export function istekCevir(req, govde) {
  const baslik = new Headers();
  for (const [k, v] of Object.entries(req.headers)) if (typeof v === 'string') baslik.set(k, v);
  // İstemci IP'si yalnız Tailscale Funnel'ın (yerel) ilettiği X-Forwarded-For'dan alınır; sunucu dışarıya açık değildir.
  baslik.delete('cf-connecting-ip');
  const ip = (String(req.headers['x-forwarded-for'] || '').split(',')[0] || req.socket.remoteAddress || '').trim();
  if (ip) baslik.set('CF-Connecting-IP', ip);
  const yontem = req.method || 'GET';
  const r = new Request('http://localhost' + (req.url || '/'), { method: yontem, headers: baslik, body: ['GET', 'HEAD'].includes(yontem) ? undefined : govde });
  Object.defineProperty(r, 'cf', { value: {} }); // ülke/şehir bilgisi Cloudflare'a özgüydü; yerelde boş kalır
  return r;
}

export function sunucuKur(env) {
  const ctx = { waitUntil: (p) => Promise.resolve(p).catch((e) => console.log('arka plan hatası:', e && e.message)) };
  return http.createServer(async (req, res) => {
    try {
      const yanit = await worker.fetch(istekCevir(req, await govdeOku(req)), env, ctx);
      const baslik = {};
      yanit.headers.forEach((v, k) => { baslik[k] = v; });
      const gec = yanit.headers.getSetCookie ? yanit.headers.getSetCookie() : [];
      if (gec.length) baslik['set-cookie'] = gec;
      res.writeHead(yanit.status, baslik);
      res.end(Buffer.from(await yanit.arrayBuffer()));
    } catch (e) {
      console.log('istek hatası:', e && e.message);
      res.writeHead(500).end();
    }
  });
}

// Günlük bakım (eski Worker'da 00:30 UTC cron). Bilgisayar o saatte kapalıysa açılışta/sonraki dakikada telafi edilir.
export function bakimZamanlayici(env, durumDosyasi, simdi = () => new Date()) {
  const oku = () => { try { return readFileSync(durumDosyasi, 'utf8').trim(); } catch { return ''; } };
  let calisiyor = false;
  const dene = async () => {
    const t = simdi(); const gun = t.toISOString().slice(0, 10);
    const dakika = t.getUTCHours() * 60 + t.getUTCMinutes();
    if (calisiyor || oku() === gun || dakika < 30) return false; // 00:30 UTC'den önce çalışmaz
    calisiyor = true;
    try {
      const isler = [];
      await worker.scheduled({}, env, { waitUntil: (p) => { isler.push(p); } });
      await Promise.all(isler); // bakım bitmeden "yapıldı" yazılmaz
      writeFileSync(durumDosyasi, gun);
      return true;
    } catch (e) { console.log('bakım hatası:', e && e.message); return false; } finally { calisiyor = false; }
  };
  return { dene, baslat: () => { dene(); return setInterval(dene, 60_000); } };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const veri = process.env.VERI_DIZINI || fileURLToPath(new URL('./veri', import.meta.url));
  const db = yerelD1(`${veri}/analiz.sqlite`);
  const env = ortamKur(db);
  if (!env.PANEL_ANAHTARI) console.log('Uyarı: PANEL_ANAHTARI tanımlı değil, panel kapalı kalır.');
  const port = Number(process.env.PORT) || 8787;
  sunucuKur(env).listen(port, '127.0.0.1', () => console.log(`kpss-analiz yerel: http://127.0.0.1:${port}`));
  bakimZamanlayici(env, `${veri}/son-bakim.txt`).baslat();
}
