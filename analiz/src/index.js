import { topla } from './toplama.js';
import { panelIstegi, oturumGecerli } from './panel.js';
import { butceSarmala, butceDurumu, butceOzeti } from './butce.js';
import { bakim } from './bakim.js';
import { ilanAdlari } from './adlar.js';
import { populerIstegi } from './populer.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    env = butceSarmala(env); // her D1 ifadesinin rows_read/rows_written değeri günlük bütçeye sayılır
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
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(bakim(butceSarmala(env)));
  },
};
