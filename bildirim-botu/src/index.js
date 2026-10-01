import { updateIsle } from './komutlar.js';
import { yoneticiTani } from './sosyal.js';

// Sabit süreli karşılaştırma (uzunluk farkında da tüm baytlar dolaşılır).
function esit(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a)), y = enc.encode(String(b));
  let fark = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) fark |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return fark === 0;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'GET' && url.pathname === '/') return new Response('ok');
    if (request.method !== 'POST' || url.pathname !== '/webhook') return new Response('bulunamadı', { status: 404 });
    if (!env.WEBHOOK_SECRET || !esit(request.headers.get('X-Telegram-Bot-Api-Secret-Token') ?? '', env.WEBHOOK_SECRET)) {
      return new Response('yetkisiz', { status: 401 });
    }
    try {
      const update = await request.json();
      try { await yoneticiTani(env, update); } catch { /* yönetici tanıma komut akışını bozmaz */ }
      await updateIsle(env, update);
    } catch (e) {
      // Telegram'a 500 dönülmez (tekrar denemesin); kişisel veri loglanmaz.
      console.log('update işlenemedi:', e && e.message);
    }
    return new Response('ok');
  },

  async scheduled(event, env, ctx) {
    const { cronCalistir } = await import('./bildirim.js');
    ctx.waitUntil(cronCalistir(env));
  },
};
