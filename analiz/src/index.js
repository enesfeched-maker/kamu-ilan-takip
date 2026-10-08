import { topla } from './toplama.js';
import { panelIstegi } from './panel.js';
import { bakim } from './bakim.js';
import { ilanAdlari } from './adlar.js';
import { populerIstegi } from './populer.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    try {
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
    ctx.waitUntil(bakim(env));
  },
};
