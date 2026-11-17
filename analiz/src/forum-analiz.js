// Forum sekmesi: forum Worker'ının /yonetim/analiz çıktısı (?gun=7|30|90) + kısa "Ne yapmalı?" önerileri.
// Anahtar yalnız sunucuda kalır; tarayıcı /panel/forum-analiz'den hazır JSON alır. Analiz D1'ine hiç gidilmez.
// Dönem başına 5 dakika önbellek (caches.default); hata/eksik anahtar önbelleğe yazılmaz.
import { onbellekli } from './onbellek.js';

export const FORUM_ANALIZ_ONBELLEK_SN = 300;
export const FORUM_ANALIZ_ZAMAN_ASIMI_MS = 5000;
export const FORUM_GUNLER = [7, 30, 90];

const yuzde = (x) => Math.round(x * 100);
const saatAd = (s) => String(s).padStart(2, '0') + ':00';

// Eşiklere göre sade Türkçe öneriler: önce uyarılar, en çok 6 madde.
export function forumOnerileri(v) {
  const uyari = [], bilgi = [];
  const S = v.soru || {}, A = v.aktif || {}, H = v.huni || {}, D = v.denetim || {};
  const bekleyen = (D.sikayet || 0) + (D.ozel_sikayet || 0) + (D.foto_bildirim || 0);
  if (bekleyen > 0) uyari.push(`${bekleyen} şikâyet bekliyor. Bugün bak.`);
  if (S.cevapsiz > 0) {
    const eski = (S.cevapsiz_liste || [])[0];
    const g = eski ? eski.gun : 0;
    const metin = `${S.cevapsiz} soru cevapsız` + (eski ? `, en eskisi ${g === 0 ? 'bugün' : g + ' gün önce'} soruldu.` : '.');
    (S.cevapsiz >= 3 || g >= 2 ? uyari : bilgi).push(metin + ' Kurucu üyelerle cevapla.');
  }
  if (S.donem >= 3 && S.cevaplanan / S.donem < 0.6) uyari.push(`Cevap alan soru oranı düşük: %${yuzde(S.cevaplanan / S.donem)}.`);
  if (S.ilk_cevap_medyan_dk != null && S.cevaplanan >= 3 && S.ilk_cevap_medyan_dk > 120) {
    uyari.push(`İlk cevap genelde ${Math.round(S.ilk_cevap_medyan_dk / 60)} saat sürüyor. Yeni soruları kanalda duyur.`);
  }
  if (S.ilan && S.ilan.n >= 3 && S.ilan.insan / S.ilan.n < 0.5) {
    bilgi.push(`İlan sayfasından gelen ${S.ilan.n} sorunun ${S.ilan.n - S.ilan.insan} tanesine üye cevabı yok.`);
  }
  if (A.donem >= 5 && A.geri_donen / A.donem < 0.3) {
    uyari.push(`Başka bir gün yeniden yazan oranı düşük: %${yuzde(A.geri_donen / A.donem)}. Takip bildirimini öne çıkar.`);
  }
  if (H.yeni >= 3 && H.yeni_yazan / H.yeni < 0.4) {
    bilgi.push(`Yeni üyelerden ${H.yeni_yazan}/${H.yeni} kişi ilk yazısını yazdı. Hoş geldin mesajında ilk soruya çağır.`);
  }
  if (H.toplam >= 5 && H.iz_yok / H.toplam > 0.5) bilgi.push(`Yalnız okuyan üye oranı %${yuzde(H.iz_yok / H.toplam)}.`);
  const saat = Array.isArray(v.saat) ? v.saat : [];
  const topSaat = saat.reduce((x, y) => x + y, 0);
  if (topSaat >= 10) {
    const en = saat.indexOf(Math.max(...saat));
    bilgi.push(`En yoğun saat ${saatAd(en)}–${saatAd((en + 1) % 24)}. Duyuruları bundan biraz önce paylaş.`);
  }
  const odalar = Array.isArray(v.odalar) ? v.odalar : [];
  const sessiz = odalar.filter((o) => !o.mesaj);
  if (odalar.length > 1 && sessiz.length) {
    bilgi.push(`${sessiz.slice(0, 2).map((o) => o.ad).join(', ')}${sessiz.length > 2 ? ` ve ${sessiz.length - 2} oda daha` : ''} bu dönemde sessiz.`);
  }
  const liste = [...uyari.map((metin) => ({ tur: 'uyari', metin })), ...bilgi.map((metin) => ({ tur: 'bilgi', metin }))].slice(0, 6);
  if (!liste.length) liste.push({ tur: 'bilgi', metin: 'Belirgin bir sorun yok.' });
  return liste;
}

export async function forumAnalizi(env, gun, simdiMs, getir = fetch) {
  if (!env.FORUM_YONETICI_ANAHTARI) return { durum: 'anahtar_yok' };
  const g = FORUM_GUNLER.includes(Number(gun)) ? Number(gun) : 30;
  const taban = String(env.FORUM_API || 'https://forum-api.kpsstercihi.com').replace(/\/+$/, '');
  let yetkisiz = false;
  try {
    const o = await onbellekli('forum:analiz:' + g, FORUM_ANALIZ_ONBELLEK_SN, async () => {
      const r = await getir(`${taban}/yonetim/analiz?gun=${g}`, { headers: { 'X-Yonetici': env.FORUM_YONETICI_ANAHTARI }, signal: AbortSignal.timeout(FORUM_ANALIZ_ZAMAN_ASIMI_MS) });
      if (r.status === 401 || r.status === 403) { yetkisiz = true; throw new Error('forum yetki'); }
      if (!r.ok) throw new Error('forum ' + r.status);
      const veri = await r.json();
      if (!veri || !veri.uyeler || !Array.isArray(veri.seri) || !veri.soru || !Array.isArray(veri.saat)) throw new Error('forum biçimi');
      return JSON.stringify(veri);
    }, simdiMs);
    const veri = JSON.parse(o.govde);
    return { durum: 'tamam', veri, oneriler: forumOnerileri(veri) };
  } catch { return { durum: yetkisiz ? 'yetkisiz' : 'hata' }; }
}
