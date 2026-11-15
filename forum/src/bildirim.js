// Telegram bildirimi: yanıt gelince başlık sahibine / yanıtlanan üyeye kısa mesaj.
const SINIR_SN = 600;
const son = new Map(); // "alici:baslik" -> unix sn (en iyi çaba)
export const bildirimSifirla = () => son.clear();

export async function yanitBildirimi(env, { baslikId, baslikAdi, yanitlayan, aliciIdleri }, simdi = Math.floor(Date.now() / 1000)) {
  const idler = [...new Set(aliciIdleri)].filter((i) => Number.isInteger(i) && i > 2 && i !== yanitlayan.id);
  if (!idler.length) return 0;
  const { results } = await env.DB.prepare(
    `SELECT id, tg_id, rol, bildirim, engelli FROM uyeler WHERE id IN (${idler.map(() => '?').join(',')})`,
  ).bind(...idler).all();
  const adres = `${env.SITE_URL || 'https://kpsstercihi.com/'}forum/?b=${baslikId}`;
  const metin = `${yanitlayan.rumuz} başlığına yanıt yazdı: ${String(baslikAdi).slice(0, 60)}\n${adres}`;
  let gonderilen = 0;
  for (const u of results) {
    if (!(u.tg_id > 0) || u.bildirim !== 1 || u.rol === 'sistem' || u.rol === 'asistan' || u.engelli) continue;
    const anahtar = `${u.id}:${baslikId}`;
    if (simdi - (son.get(anahtar) || 0) < SINIR_SN) continue;
    if (!env.TELEGRAM_BOT_TOKEN || env.ORTAM === 'yerel') { console.log('bildirim (gönderilmedi):', u.id, baslikId); continue; }
    son.set(anahtar, simdi);
    if (son.size > 5000) son.clear();
    try {
      await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: u.tg_id, text: metin, disable_web_page_preview: true }),
      });
      gonderilen++;
    } catch { /* bildirim hatası yazmayı etkilemez */ }
  }
  return gonderilen;
}

// Yanıtta "@rumuz" ile anılan üyelere kısa Telegram mesajı (anmalar saklanmaz). haricIdler: bu istekte zaten haber verilenler.
export async function anmaBildirimi(env, { baslikId, baslikAdi, yanitId, yanitlayan, rumuzlar, haricIdler = [] }, simdi = Math.floor(Date.now() / 1000)) {
  const adlar = [...new Set((rumuzlar || []).map((r) => String(r).toLowerCase()))].slice(0, 3);
  if (!adlar.length) return 0;
  const { results } = await env.DB.prepare(
    `SELECT id, tg_id, rol, bildirim, engelli FROM uyeler WHERE rumuz IN (${adlar.map(() => '?').join(',')})`,
  ).bind(...adlar).all();
  const adres = `${env.SITE_URL || 'https://kpsstercihi.com/'}forum/?b=${baslikId}#y${yanitId}`;
  const metin = `${yanitlayan.rumuz} seni andı: ${String(baslikAdi).slice(0, 60)}\n${adres}`;
  let gonderilen = 0;
  for (const u of results) {
    if (u.id === yanitlayan.id || haricIdler.includes(u.id)) continue;
    if (!(u.tg_id > 0) || u.bildirim !== 1 || u.rol === 'sistem' || u.rol === 'asistan' || u.engelli) continue;
    const anahtar = `anma:${u.id}:${baslikId}`;
    if (simdi - (son.get(anahtar) || 0) < SINIR_SN) continue;
    if (!env.TELEGRAM_BOT_TOKEN || env.ORTAM === 'yerel') { console.log('anma bildirimi (gönderilmedi):', u.id, baslikId); continue; }
    son.set(anahtar, simdi);
    if (son.size > 5000) son.clear();
    try {
      await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: u.tg_id, text: metin, disable_web_page_preview: true }),
      });
      gonderilen++;
    } catch { /* bildirim hatası yazmayı etkilemez */ }
  }
  return gonderilen;
}
