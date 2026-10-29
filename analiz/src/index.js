import { topla } from './toplama.js';
import { panelIstegi, oturumGecerli } from './panel.js';
import { butceSarmala, butceDurumu, butceOzeti, butceBekliyor, butceYaz } from './butce.js';
import { bakim } from './bakim.js';
import { ilanAdlari } from './adlar.js';
import { populerIstegi } from './populer.js';
import { arananIstegi } from './aranan.js';
import { liderlikIstegi } from './liderlik.js';

export default {
  async fetch(request, env, ctx) {
    env = butceSarmala(env); // her D1 ifadesinin rows_read/rows_written değeri günlük bütçeye sayılır
    const yanit = await yonlendir(request, env);
    // Ağır istekten sonra harcama hemen yazılır (izolat kapanırsa sayaç kaybolmasın).
    if (butceBekliyor() && ctx && ctx.waitUntil) ctx.waitUntil(butceYaz(env).catch(() => {}));
    return yanit;
  },

  async scheduled(event, env, ctx) {
    env = butceSarmala(env);
    ctx.waitUntil(bakim(env).finally(() => butceYaz(env).catch(() => {})));
  },
};

async function yonlendir(request, env) {
  const url = new URL(request.url);
  try {
    if (url.pathname === '/butce' && request.method === 'GET') {
      // Not: panel çerezi Path=/panel olduğundan tarayıcı bunu /butce'ye göndermez; panel içinden /panel/butce kullanılır.
      const yerel = env.ORTAM === 'yerel' && !env.PANEL_ANAHTARI;
      if (!yerel && !(env.PANEL_ANAHTARI && await oturumGecerli(env, request, Math.floor(Date.now() / 1000)))) {
        return new Response(JSON.stringify({ hata: 'yetkisiz' }), { status: 401, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
      }
      return new Response(JSON.stringify(butceOzeti(await butceDurumu(env))), { headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
    }
    if (url.pathname === '/o') return await topla(request, env);
    if (url.pathname === '/populer') return await populerIstegi(request, env);
    if (url.pathname === '/aranan') return await arananIstegi(request, env);
    if (url.pathname === '/liderlik') return await liderlikIstegi(request, env);
    if (url.pathname === '/panel' || url.pathname.startsWith('/panel/')) {
      return await panelIstegi(request, env, url, { adlariGetir: (anahtarlar) => ilanAdlari(env, anahtarlar) });
    }
    if (url.pathname === '/') return new Response('kpss-analiz', { headers: { 'Cache-Control': 'no-store' } });
  } catch (e) {
    // Ölçüm hatası ziyaretçiyi etkilemez; ayrıntı (kişisel veri içermez) yalnız günlüğe yazılır.
    console.log('hata:', e && e.message);
    return new Response(null, { status: url.pathname === '/o' ? 204 : 500 });
  }
  return new Response('bulunamadı', { status: 404 });
}
