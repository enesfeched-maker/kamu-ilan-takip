// Trafik kaynağı sınıflandırması: önce utm_source, yoksa yönlendiren (referrer) alan adı.

const UTM = [
  [/^(google|gclid|adwords)/, 'Google'],
  [/^bing/, 'Bing'],
  [/^yandex/, 'Yandex'],
  [/^(telegram|tg|t\.me)$/, 'Telegram'],
  [/^(instagram|ig)$/, 'Instagram'],
  [/^(x|twitter|tw)$/, 'X'],
  [/^(facebook|fb)$/, 'Facebook'],
  [/^whatsapp|^wa$/, 'WhatsApp'],
];

const HOST = [
  [/(^|\.)google\.[a-z.]+$|^com\.google\.android\.googlequicksearchbox$/, 'Google'],
  [/(^|\.)bing\.com$/, 'Bing'],
  [/(^|\.)yandex\.[a-z.]+$|(^|\.)ya\.ru$/, 'Yandex'],
  [/(^|\.)(t\.me|telegram\.org|telegram\.me|web\.telegram\.org)$|^org\.telegram\./, 'Telegram'],
  [/(^|\.)instagram\.com$/, 'Instagram'],
  [/(^|\.)(x\.com|twitter\.com|t\.co)$/, 'X'],
  [/(^|\.)(facebook\.com|fb\.com|fb\.me)$/, 'Facebook'],
  [/(^|\.)(whatsapp\.com|wa\.me)$/, 'WhatsApp'],
  [/(^|\.)(duckduckgo\.com|yahoo\.com|ecosia\.org|search\.brave\.com|startpage\.com)$/, 'Arama (diğer)'],
];

const OWN = /(^|\.)kpsstercihi\.com$/;

export function temizHost(v) {
  const h = String(v || '').trim().toLowerCase().replace(/^www\./, '');
  return /^[a-z0-9][a-z0-9.-]{0,98}$/.test(h) ? h : '';
}

export function kaynakSinifla(rhost, utmSource) {
  const us = String(utmSource || '').trim().toLowerCase();
  if (us) for (const [re, ad] of UTM) if (re.test(us)) return ad;
  const h = temizHost(rhost);
  if (!h || OWN.test(h)) return us ? 'Diğer' : 'Doğrudan';
  for (const [re, ad] of HOST) if (re.test(h)) return ad;
  return 'Diğer';
}
