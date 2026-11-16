// Siteye ait kayıtlı ilanlar (localStorage "kit-saved") hesapta saklanır: ilan kimliklerinin JSON dizisi.
// 300 UUID kimliği JSON'da ~11,7 KB tutar; bayt sınırı bu yüzden 12 KB (8 KB ~210 UUID'de dolardı).
// Süresi dolmuş ya da kaldırılmış ilan kimlikleri zararsızdır (site onları göstermez).
import { gecerliIlanKimligi } from './yardimci.js';

export const KAYITLI_EN_COK = 300;
export const KAYITLI_BAYT = 12288;

// Geçerliyse temizlenmiş dizi (tekrarsız, geçerli kimlikler, sıra korunur), dizi değilse ya da sınır aşılırsa null.
export function kayitliTemizle(liste) {
  if (!Array.isArray(liste) || liste.length > KAYITLI_EN_COK * 2) return null;
  const temiz = [...new Set(liste.filter(gecerliIlanKimligi))];
  if (temiz.length > KAYITLI_EN_COK) return null;
  return JSON.stringify(temiz).length <= KAYITLI_BAYT ? temiz : null;
}

export function kayitliOku(metin) {
  if (!metin) return [];
  try { return kayitliTemizle(JSON.parse(metin)) || []; } catch { return []; }
}
