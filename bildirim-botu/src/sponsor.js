// Sponsor seçimi: aktif, tarih aralığında, hedefi eşleşen en spesifik sponsor.
import { bugunIstanbul } from './eslestir.js';

const liste = (x) => (Array.isArray(x) ? x : []);

// Boşaltma başına bir kez okunur; sonuç sponsorSec'e `sponsorlar` olarak verilir.
export async function sponsorlariOku(env, bugun = bugunIstanbul()) {
  const { results } = await env.DB
    .prepare('SELECT * FROM sponsorlar WHERE aktif = 1 AND baslangic <= ? AND bitis >= ? ORDER BY id')
    .bind(bugun, bugun)
    .all();
  return results || [];
}

export async function sponsorSec(env, kullanici, ilan, bugun = bugunIstanbul(), sponsorlar = null) {
  const adaylar = sponsorlar || (await sponsorlariOku(env, bugun));
  let en = null;
  let enPuan = -1;
  for (const s of adaylar) {
    if (s.aktif === 0 || s.baslangic > bugun || s.bitis < bugun) continue;
    let puan = 0;
    let uyar = true;
    const kontrol = (hedef, degerler) => {
      if (hedef == null || hedef === '') return;
      if (degerler.includes(hedef)) puan++;
      else uyar = false;
    };
    kontrol(s.duzey, [...liste(ilan.ogrenim), ...liste(kullanici && kullanici.duzeyler)]);
    kontrol(s.il, [...liste(ilan.iller), ...liste(kullanici && kullanici.iller)]);
    kontrol(s.kategori, [ilan.kategori, ...liste(kullanici && kullanici.kategoriler)]);
    if (uyar && puan > enPuan) { en = s; enPuan = puan; }
  }
  return en ? { metin: en.metin, link: en.link || null } : null;
}
