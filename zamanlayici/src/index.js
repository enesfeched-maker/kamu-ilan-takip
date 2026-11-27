// KPSS Tercihi zamanlayıcı (22 Ekim 2026): GitHub'ın kendi zamanlayıcısı yoğunlukta işleri saatlerce atlıyordu
// (24 saatte 48 tarama yerine 14). Cloudflare'ın cron'u dakikası dakikasına çalışır; bu Worker GitHub'a
// "iş akışını başlat" (workflow_dispatch) isteği gönderir. GitHub'daki eski cron'lar yedek olarak kalır.
// Sır: GH_TOKEN (yalnız bu depo, Actions: Read and write yetkili ince anahtar; kurulum.ps1 ile girilir).

const DEPO = 'enesfeched-maker/kamu-ilan-takip';

// cron ifadesi -> başlatılacak iş akışları
export const ISLER = {
  '*/30 * * * *': ['ilan.yml'],   // tarama: her saat :00 ve :30
  '7,37 * * * *': ['bekci.yml'],  // bekçi: taramadan 7 dk sonra
  '25 */2 * * *': ['sosyal-yorum.yml'], // Instagram yorumlarına asistan yanıtı: 2 saatte bir
};

// 27 Kasım 2026: sosyal paylaşımlar da GitHub cron'una bırakılmaz (öğle videosu 04:00–06:30'a kayıyordu).
// Ücretsiz planda cron sayısı sınırlı olduğundan ayrı cron açılmaz: her yarım saatlik tetikte UTC saatine bakılır.
// Anahtar 'HH:MM' (UTC; Türkiye = UTC+3) ya da haftanın günüyle 'G HH:MM' (0 = pazar).
// Değer: [iş akışı, girdiler]. Girdilerde kaynak=zamanlayici: iş akışının saat kapısı (bot/yayin_kapisi.py) uygulanır.
const Z = { kaynak: 'zamanlayici' };
export const SAATLI = {
  '08:00': [['sosyal-gorsel.yml', { tur: 'otomatik', yayinla: 'true', ...Z }]],   // 11:00 TR hikâye + günlük karusel
  '09:30': [['sosyal.yml', { vakit: 'sabah', yayinla: 'true', ...Z }]],           // 12:30 TR öğle videosu (kancalı)
  '11:00': [['sosyal-gorsel.yml', { tur: 'yalniz-ilan', yayinla: 'true', ...Z }]], // 14:00 TR yeni ilan karuseli
  '13:30': [['sosyal-gorsel.yml', { tur: 'yalniz-ilan', yayinla: 'true', ...Z }]], // 16:30 TR
  '15:00': [['sosyal-ozel.yml', { ...Z }], ['sosyal-ilan.yml', { yayinla: 'true', ...Z }]], // 18:00 TR özel video ya da yeni ilan videosu
  '16:30': [['sosyal-gorsel.yml', { tur: 'yalniz-ilan', yayinla: 'true', ...Z }]], // 19:30 TR
  '18:00': [['sosyal.yml', { vakit: 'aksam', yayinla: 'true', ...Z }]],           // 21:00 TR akşam videosu (kancalı)
  '0 16:00': [['sosyal.yml', { vakit: 'haftalik', yayinla: 'true', ...Z }]],      // pazar 19:00 TR haftalık dizi
};

export function saatliIsler(zaman) {
  const d = new Date(zaman);
  const hhmm = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
  return [...(SAATLI[hhmm] || []), ...(SAATLI[`${d.getUTCDay()} ${hhmm}`] || [])];
}

export async function baslat(env, isAkisi, fetchImpl = fetch, girdiler = null) {
  const yanit = await fetchImpl(`https://api.github.com/repos/${DEPO}/actions/workflows/${isAkisi}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'kpsstercihi-zamanlayici',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(girdiler ? { ref: 'main', inputs: girdiler } : { ref: 'main' }),
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
    if (olay.cron === '*/30 * * * *') {
      // cron dakikası dakikasına gelir; scheduledTime saniyeleri sıfırdır
      for (const [isAkisi, girdiler] of saatliIsler(olay.scheduledTime ?? Date.now())) ctx.waitUntil(baslat(env, isAkisi, fetch, girdiler));
    }
  },
  async fetch() {
    return new Response('KPSS Tercihi zamanlayıcı çalışıyor.', { headers: { 'content-type': 'text/plain; charset=utf-8' } });
  },
};
