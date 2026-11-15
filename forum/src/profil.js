// Siteye ait profil (localStorage "kit-profil") hesapta saklanır. Beyaz liste docs/portal.js validProfile ile aynıdır.
export const PROFIL_EN_COK = 2048;
const OGRENIMLER = new Set(['lisans', 'onlisans', 'ortaogretim']);
const TARIH = /^\d{4}-\d{2}-\d{2}$/;
const IL_ADI = /^[A-Za-zÇĞİÖŞÜçğıöşü' -]{2,30}$/;

// Geçerliyse temizlenmiş nesne, değilse null.
export function profilTemizle(p) {
  if (!p || typeof p !== 'object' || Array.isArray(p) || p.v !== 1) return null;
  const t = typeof p.t === 'string' && TARIH.test(p.t) ? p.t : new Date().toISOString().slice(0, 10);
  if (p.atlandi === true) return { v: 1, atlandi: true, t };
  if (typeof p.ogrenim !== 'string' || !OGRENIMLER.has(p.ogrenim)) return null;
  const o = {
    v: 1, ogrenim: p.ogrenim,
    puan_turu: typeof p.puan_turu === 'string' && /^P\d{1,3}$/.test(p.puan_turu) ? p.puan_turu : '',
    iller: (Array.isArray(p.iller) ? p.iller : []).filter((x) => typeof x === 'string' && IL_ADI.test(x)).slice(0, 81),
    tum_turkiye: p.tum_turkiye === true,
    bolum: typeof p.bolum === 'string' ? p.bolum.slice(0, 60) : '',
    t,
  };
  if (!o.puan_turu) delete o.puan_turu;
  if (typeof p.puan === 'number' && Number.isFinite(p.puan) && p.puan > 0 && p.puan <= 100) o.puan = p.puan;
  return JSON.stringify(o).length <= PROFIL_EN_COK ? o : null;
}

export function profilOku(metin) {
  if (!metin) return null;
  try { return profilTemizle(JSON.parse(metin)); } catch { return null; }
}
