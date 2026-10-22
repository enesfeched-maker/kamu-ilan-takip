// KPSS Tercihi zamanlayıcı (22 Ekim 2026): GitHub'ın kendi zamanlayıcısı yoğunlukta işleri saatlerce atlıyordu
// (24 saatte 48 tarama yerine 14). Cloudflare'ın cron'u dakikası dakikasına çalışır; bu Worker GitHub'a
// "iş akışını başlat" (workflow_dispatch) isteği gönderir. GitHub'daki eski cron'lar yedek olarak kalır.
// Sır: GH_TOKEN (yalnız bu depo, Actions: Read and write yetkili ince anahtar; kurulum.ps1 ile girilir).

const DEPO = 'enesfeched-maker/kamu-ilan-takip';

// cron ifadesi -> başlatılacak iş akışları
export const ISLER = {
  '*/30 * * * *': ['ilan.yml'],   // tarama: her saat :00 ve :30
  '7,37 * * * *': ['bekci.yml'],  // bekçi: taramadan 7 dk sonra
};

export async function baslat(env, isAkisi, fetchImpl = fetch) {
  const yanit = await fetchImpl(`https://api.github.com/repos/${DEPO}/actions/workflows/${isAkisi}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'kpsstercihi-zamanlayici',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (yanit.status !== 204) {
    // Anahtar asla yazılmaz; yalnız durum kodu ve GitHub'ın kısa mesajı.
    const metin = (await yanit.text()).slice(0, 200);
    console.log(`${isAkisi} başlatılamadı: HTTP ${yanit.status} ${metin}`);
    return false;
  }
  return true;
}

export default {
  async scheduled(olay, env, ctx) {
    if (!env.GH_TOKEN) {
      console.log('GH_TOKEN tanımlı değil; kurulum.ps1 çalıştırılmalı.');
      return;
    }
    for (const isAkisi of ISLER[olay.cron] || []) ctx.waitUntil(baslat(env, isAkisi));
  },
  async fetch() {
    return new Response('KPSS Tercihi zamanlayıcı çalışıyor.', { headers: { 'content-type': 'text/plain; charset=utf-8' } });
  },
};
