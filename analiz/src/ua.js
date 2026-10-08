// User-Agent'tan yalnızca kaba bilgi çıkarılır (bot mu, cihaz türü, tarayıcı ve işletim sistemi ailesi).
// Tam User-Agent hiçbir yerde saklanmaz.

const BOT = /bot\b|bot[\/;_ -]|crawl|spider|slurp|facebookexternalhit|bingpreview|headless|lighthouse|pagespeed|gtmetrix|pingdom|uptime|monitor|curl\/|wget|python|httpclient|http-client|axios|node-fetch|undici|go-http|okhttp\/\d|java\/|libwww|scrapy|preview|scanner|checker|archiver|ahrefs|semrush|mj12|dotbot|petalbot|bytespider|yandex(?:bot|images|metrika)|telegrambot|whatsapp\/|twitterbot|discordbot|linkedinbot|skypeuripreview|embedly|pinterest|validator|wappalyzer|phantom|puppeteer|playwright|selenium/i;

export function botMu(ua) {
  const u = String(ua || '').trim();
  return u.length < 10 || BOT.test(u);
}

export function cihazTuru(ua) {
  const u = String(ua || '');
  if (/ipad|tablet|kindle|silk\/|playbook|nexus 7|nexus 9|sm-t\d|(android(?!.*mobile))/i.test(u)) return 'tablet';
  if (/mobi|iphone|ipod|android.*mobile|windows phone|blackberry/i.test(u)) return 'mobil';
  return 'masaüstü';
}

export function tarayiciAilesi(ua) {
  const u = String(ua || '');
  if (/instagram/i.test(u)) return 'Instagram (uygulama içi)';
  if (/FBAN|FBAV|FB_IAB/i.test(u)) return 'Facebook (uygulama içi)';
  if (/Edg(?:e|A|iOS)?\//.test(u)) return 'Edge';
  if (/OPR\/|Opera|OPiOS/.test(u)) return 'Opera';
  if (/SamsungBrowser/i.test(u)) return 'Samsung Internet';
  if (/YaBrowser/i.test(u)) return 'Yandex Tarayıcı';
  if (/Firefox\/|FxiOS/i.test(u)) return 'Firefox';
  if (/Chrome\/|CriOS/i.test(u)) return 'Chrome';
  if (/Safari\//.test(u)) return 'Safari';
  return 'Diğer';
}

export function isletimAilesi(ua) {
  const u = String(ua || '');
  if (/windows/i.test(u)) return 'Windows';
  if (/android/i.test(u)) return 'Android';
  if (/iphone|ipad|ipod/i.test(u)) return 'iOS';
  if (/mac os x|macintosh/i.test(u)) return 'macOS';
  if (/cros/i.test(u)) return 'ChromeOS';
  if (/linux|x11/i.test(u)) return 'Linux';
  return 'Diğer';
}

// Ekran genişliği kovaları (CSS pikseli).
export function genislikKovasi(w) {
  const n = Number(w);
  if (!Number.isFinite(n) || n <= 0) return '';
  if (n < 480) return '<480';
  if (n < 768) return '480-767';
  if (n < 1024) return '768-1023';
  if (n < 1440) return '1024-1439';
  return '1440+';
}
