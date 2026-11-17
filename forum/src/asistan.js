// Kural tabanlı asistan: yapay zekâ yok, uydurma yok. Yalnız ilan kaydındaki veriyi aktarır.
const AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
const BAS = 'İlan belgesine göre:';
const SON = 'Kesin bilgi için resmî ilan belgesine bak.';
const AZAMI = 400;

export function normalle(s) {
  return String(s ?? '').replace(/İ/g, 'i').toLocaleLowerCase('tr')
    .replace(/ı/g, 'i').replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u')
    .replace(/[^a-z0-9]+/g, ' ').trim();
}
const kelimeBasi = (n, kokler) => kokler.some((k) => new RegExp(`(^| )${k}`).test(n));

function tarihMetni(ilan) {
  const t = String(ilan.son_zaman || ilan.son_tarih || '');
  const m = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return null;
  const ay = AYLAR[Number(m[2]) - 1];
  if (!ay) return null;
  const saat = String(ilan.son_zaman || '').match(/T(\d{2}):(\d{2})/);
  const saatMetni = saat && !(saat[1] === '00' && saat[2] === '00') ? `, saat ${saat[1]}:${saat[2]}` : '';
  return `${Number(m[3])} ${ay} ${m[1]}${saatMetni}`;
}

const OGRENIM = { lisans: 'lisans', onlisans: 'ön lisans', ortaogretim: 'lise (ortaöğretim)', ilkogretim: 'ilköğretim' };

function sonTarih(ilan) {
  const t = tarihMetni(ilan);
  return t ? `Son başvuru tarihi: ${t}.` : null;
}
function ogrenim(ilan) {
  const liste = Array.isArray(ilan.ogrenim) ? ilan.ogrenim.filter(Boolean) : [];
  if (!liste.length) return null;
  let s = `Aranan öğrenim düzeyi: ${liste.map((o) => OGRENIM[o] || o).join(', ')}.`;
  const b = Array.isArray(ilan.bolumler) ? ilan.bolumler.filter(Boolean).slice(0, 6) : [];
  if (b.length) s += ` Bölümler: ${b.join(', ')}.`;
  return s;
}
export function puanTurleri(ilan) {
  const m = normalle(ilan.metin);
  const bulunan = new Set();
  for (const x of m.matchAll(/(?:^| )(?:kpss ?)?p ?(\d{1,3})(?= |$)/g)) {
    const n = Number(x[1]);
    if (n >= 1 && n <= 123) bulunan.add(`P${n}`);
  }
  return [...bulunan].slice(0, 4);
}
function puan(ilan) {
  const t = puanTurleri(ilan);
  if (!t.length) return null;
  let s = `Aranan KPSS puan türü: ${t.join(', ')}.`;
  if (ilan.sayfa) s += ' Geçmiş taban puanları ilan sayfasında.';
  return s;
}
function kisi(ilan) {
  const m = String(ilan.metin || '').toLocaleLowerCase('tr').match(/toplam\s+(\d{1,5})\s+(?:kişi|kisi|adet|kadro|personel)/)
    || String(ilan.metin || '').toLocaleLowerCase('tr').match(/(?:^|[^\d])(\d{1,5})\s+(?:adet|kişi|kisi)\b/);
  if (!m || Number(m[1]) < 1) return null;
  return `İlanda geçen kadro sayısı: ${Number(m[1])}.`;
}
function basvuru(ilan) {
  if (!ilan.sayfa) return null;
  return `Başvuru bağlantısı ilan sayfasında: ${ilan.sayfa}`;
}
function yas(ilan) {
  const m = String(ilan.metin || '').toLocaleLowerCase('tr').match(/(\d{2})\s*yaş/);
  return m ? `İlanda yaş şartı geçiyor: ${m[1]} yaş.` : null;
}

const NIYETLER = [
  { ad: 'tarih', ara: (n) => /(^| )(son gun|son basvuru|bitis|bitiyor|bitecek)/.test(n) || /ne zamana kadar|ne zaman (bitiyor|biter)/.test(n), cevap: sonTarih },
  { ad: 'ogrenim', ara: (n) => kelimeBasi(n, ['ogrenim', 'lisans', 'onlisans', 'on lisans', 'lise', 'mezun', 'bolum', 'diploma']), cevap: ogrenim },
  { ad: 'puan', ara: (n) => kelimeBasi(n, ['puan', 'kpss', 'taban']), cevap: puan },
  { ad: 'kisi', ara: (n) => /kac (kisi|personel|kadro)|(^| )(kadro|kontenjan)/.test(n), cevap: kisi },
  { ad: 'basvuru', ara: (n) => /(nereden|nerden|nasil) (basvur|yapil)|basvuru (linki|yeri|nasil|nereden)|basvuru yap/.test(n), cevap: basvuru },
  { ad: 'yas', ara: (n) => /(^| )yas(i|ini|in|a|siniri|sarti)?( |$)/.test(n), cevap: yas },
];

export function asistanYaniti(soru, ilan) {
  if (!ilan || typeof soru !== 'string') return null;
  const n = normalle(soru);
  if (n.length < 3) return null;
  const parcalar = [];
  for (const nv of NIYETLER) {
    if (!nv.ara(n)) continue;
    const c = nv.cevap(ilan);
    if (c) parcalar.push(c);
  }
  if (!parcalar.length) return null;
  while (parcalar.length > 1 && [BAS, ...parcalar, SON].join(' ').length > AZAMI) parcalar.pop();
  const yanit = [BAS, ...parcalar, SON].join(' ');
  return yanit.length <= AZAMI + 120 ? yanit : null;
}
