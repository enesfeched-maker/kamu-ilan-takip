export const REPO = 'enesfeched-maker/kamu-ilan-takip';
export const KANAL_ID = '120363413415365306@newsletter';
export const KANAL_KODU = '0029Vb9Jn013QxS5sXJ12b2Q';
export const SITE = 'https://kpsstercihi.com/';

export function yeniSurumler(surumler, durum) {
  return surumler.filter(s => /^sosyal-\d{8}-(sabah|aksam|ilan-|ozel-)/.test(s.tag_name)
    && Date.parse(s.published_at) >= Date.parse(durum.baslangic)
    && (!durum.gonderimler[s.tag_name] || durum.gonderimler[s.tag_name].durum === 'yeniden_denenecek')).sort((a, b) => Date.parse(a.published_at) - Date.parse(b.published_at));
}

export function yayinlanmis(metin, gecmis) {
  return gecmis.some(g => g.zaman === metin.zaman && (g.ig_id || g.tt_id || g.fb_id));
}

export function kanalMetni(metin) {
  if (typeof metin.aciklama !== 'string' || !metin.aciklama.trim()) throw new Error('Paylaşım metni boş');
  let yazi = metin.aciklama.trim().replace(/profildeki bağlantı(?:da|dan)?\.?/gi, SITE);
  if (!yazi.includes('kpsstercihi.com')) yazi += '\n\nİlanlar ve başvuru bağlantıları: ' + SITE;
  return yazi.slice(0, 4000);
}

export function guvenliDosya(url) {
  const u = new URL(url);
  if (u.protocol !== 'https:' || u.hostname !== 'github.com'
      || !u.pathname.startsWith('/' + REPO + '/releases/download/')) throw new Error('Beklenmeyen dosya adresi');
  return u.href;
}
