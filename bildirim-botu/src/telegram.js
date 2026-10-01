// Telegram Bot API istemcisi. Token asla loglanmaz ya da hata metnine konmaz.
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

export async function tg(env, method, params = {}, secenek = {}) {
  const yeniden = secenek.yeniden !== false; // 429'da bir kez yeniden dene (cron {yeniden:false} verir)
  let yanit;
  try {
    yanit = await fetch('https://api.telegram.org/bot' + env.BOT_TOKEN + '/' + method, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(params),
    });
  } catch {
    const e = new Error('Telegram ' + method + ' ağ hatası');
    e.kod = 0;
    e.aciklama = 'ağ hatası';
    throw e;
  }
  let veri = null;
  try {
    veri = await yanit.json();
  } catch {
    veri = null;
  }
  if (veri && veri.ok) return veri.result;
  const kod = (veri && veri.error_code) || yanit.status;
  const aciklama = (veri && veri.description) || 'bilinmeyen hata';
  if (kod === 429 && yeniden) {
    const sn = Number(veri && veri.parameters && veri.parameters.retry_after) || 1;
    await bekle(sn * 1000);
    return tg(env, method, params, { yeniden: false });
  }
  const hata = new Error('Telegram ' + method + ' hatası ' + kod + ': ' + aciklama);
  hata.kod = kod;
  hata.aciklama = aciklama;
  throw hata;
}