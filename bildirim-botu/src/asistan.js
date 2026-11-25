// Site asistanı: kpsstercihi.com'daki soru-cevap kutusunun arka ucu (POST /asistan/sor).
// Cevaplar yalnız sitenin bilgi dosyasından (asistan/bilgi.json) ve açık ilan listesinden (bot-ilanlar.json) üretilir;
// D1'e dokunulmaz, soru metni saklanmaz ya da loglanmaz. Workers AI yalnızca şablon cümleyi daha doğal yazmak için
// kullanılır; çıktısı sıkı doğrulanır, geçemezse şablon cevap gider. Bağlantılar ve ilanlar her zaman koddan gelir.
import { bugunIstanbul, sureDoldu } from './eslestir.js';

const IZINLI_ORIGINLER = /^(https:\/\/(www\.)?kpsstercihi\.com|http:\/\/(localhost|127\.0\.0\.1)(:\d{1,5})?)$/;
const VARSAYILAN_SITE = 'https://kpsstercihi.com/';
const TELEGRAM = 'https://t.me/kpsstercihi';
const SORU_MAX = 300;
const GOVDE_MAX = 4096;
const HIZ_PENCERE_MS = 5 * 60 * 1000;
const HIZ_MAX = 12;
const ONBELLEK_MS = 10 * 60 * 1000;
const FETCH_ZAMAN_MS = 5000;
const YZ_ZAMAN_MS = 6000;
const VARSAYILAN_MODEL = '@cf/meta/llama-3.3-70b-instruct-fp8-fast';

// ---------------------------------------------------------------- metin işleme

export function katla(s) {
  return String(s ?? '').toLocaleLowerCase('tr')
    .replace(/ı/g, 'i').replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u')
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
}
const sade = (s) => katla(s).replace(/[^a-z0-9]+/g, ' ').trim();

const EKLER = ['larin', 'lerin', 'lari', 'leri', 'lar', 'ler', 'dan', 'den', 'tan', 'ten', 'nda', 'nde', 'ina', 'ine', 'una', 'une',
  'yla', 'yle', 'da', 'de', 'ta', 'te', 'na', 'ne', 'ya', 'ye', 'la', 'le', 'si', 'su', 'mi', 'mu', 'im', 'um', 'in', 'un', 'i', 'u']
  .sort((a, b) => b.length - a.length);

export function govdeKok(t) {
  let k = t;
  for (let tur = 0; tur < 2; tur++) {
    const ek = EKLER.find((e) => k.endsWith(e) && k.length - e.length >= 4);
    if (!ek) break;
    k = k.slice(0, k.length - ek.length);
  }
  return k;
}

const DURAK = new Set(['ve', 'veya', 'ile', 'mi', 'mu', 'ne', 'nasil', 'icin', 'bir', 'bu', 'su', 'o', 'da', 'de', 'ben', 'sen', 'biz', 'siz',
  'var', 'yok', 'olur', 'olarak', 'nedir', 'kadar', 'gibi', 'hangi', 'kim', 'neden', 'nerede', 'nereden', 'nereye', 'kac', 'midir', 'acaba',
  'lutfen', 'ama', 'fakat', 'ki', 'en', 'cok', 'daha', 'ya', 'hem', 'her', 'tum', 'olan', 'olmak', 'yapilir', 'yapabilirim', 'edebilirim',
  'miyim', 'musun', 'misin', 'musunuz', 'misiniz', 'ise', 'ancak', 'bana', 'beni', 'benim', 'mi', 'mı', 'le', 'la', 'na', 'ne']);

const tokenla = (s) => sade(s).split(' ').filter(Boolean);
// Eşanlamlı kök grupları ("nerede açıklanır" ~ "nereden görebilirim"): aynı gruba giren kökler tek kök sayılır.
const ES_ONEKLER = ['acikla', 'duyur', 'yayiml', 'gorebil', 'gorul', 'ogrenebil', 'bakabil'];
const esKok = (k) => (ES_ONEKLER.some((e) => k.startsWith(e)) ? 'g_gor' : k);
const icerikKoklari = (s) => tokenla(s).filter((t) => !DURAK.has(t)).map(govdeKok).filter((t) => !DURAK.has(t) && t.length > 1).map(esKok);

// 'padli' metinde k ifadesi kelime başında geçiyor mu (arkasında en çok 4 harflik ek olabilir).
function kelimeVar(metin, k) {
  const m = ` ${metin} `;
  const sinir = k.length <= 3 ? 2 : 4;
  let i = m.indexOf(` ${k}`);
  while (i !== -1) {
    const bas = i + 1 + k.length;
    const son = m.indexOf(' ', bas);
    if (son - bas <= sinir) return true;
    i = m.indexOf(` ${k}`, i + 1);
  }
  return false;
}

// ---------------------------------------------------------------- illerin listesi

const IL_ADLARI = ['Adana', 'Adıyaman', 'Afyonkarahisar', 'Ağrı', 'Aksaray', 'Amasya', 'Ankara', 'Antalya', 'Ardahan', 'Artvin', 'Aydın', 'Balıkesir',
  'Bartın', 'Batman', 'Bayburt', 'Bilecik', 'Bingöl', 'Bitlis', 'Bolu', 'Burdur', 'Bursa', 'Çanakkale', 'Çankırı', 'Çorum', 'Denizli', 'Diyarbakır',
  'Düzce', 'Edirne', 'Elazığ', 'Erzincan', 'Erzurum', 'Eskişehir', 'Gaziantep', 'Giresun', 'Gümüşhane', 'Hakkâri', 'Hatay', 'Iğdır', 'Isparta',
  'İstanbul', 'İzmir', 'Kahramanmaraş', 'Karabük', 'Karaman', 'Kars', 'Kastamonu', 'Kayseri', 'Kırıkkale', 'Kırklareli', 'Kırşehir', 'Kilis',
  'Kocaeli', 'Konya', 'Kütahya', 'Malatya', 'Manisa', 'Mardin', 'Mersin', 'Muğla', 'Muş', 'Nevşehir', 'Niğde', 'Ordu', 'Osmaniye', 'Rize',
  'Sakarya', 'Samsun', 'Siirt', 'Sinop', 'Sivas', 'Şanlıurfa', 'Şırnak', 'Tekirdağ', 'Tokat', 'Trabzon', 'Tunceli', 'Uşak', 'Van', 'Yalova',
  'Yozgat', 'Zonguldak'];
// Gündelik kısaltmalar (katlanmış) -> il adı.
const IL_TAKMA = { afyon: 'Afyonkarahisar', maras: 'Kahramanmaraş', urfa: 'Şanlıurfa', antep: 'Gaziantep', icel: 'Mersin' };
const IL_EKLERI = new Set(['', 'da', 'de', 'ta', 'te', 'dan', 'den', 'tan', 'ten', 'li', 'lu', 'daki', 'deki', 'taki', 'teki', 'a', 'e', 'ya', 'ye', 'in', 'nin', 'i', 'si', 'lik', 'yi']);
const IL_LISTESI = [
  ...IL_ADLARI.map((ad) => ({ ad, k: katla(ad) })),
  ...Object.entries(IL_TAKMA).map(([k, ad]) => ({ ad, k })),
];
export const IL_SAYISI = IL_ADLARI.length;

function ilBul(tokenlar) {
  const bulunan = [];
  for (const t of tokenlar) {
    for (const il of IL_LISTESI) {
      if (!t.startsWith(il.k)) continue;
      const ek = t.slice(il.k.length);
      if (!IL_EKLERI.has(ek)) continue;
      if ((ek === 'a' || ek === 'e' || ek === 'ya' || ek === 'ye' || ek === 'i' || ek === 'in') && il.k.length < 5) continue;
      if (!bulunan.includes(il.ad)) bulunan.push(il.ad);
    }
  }
  return bulunan;
}

// ---------------------------------------------------------------- soru çözümleme

const KIMLIK = ['insan misin', 'insan mi', 'bot musun', 'bot mu', 'robot musun', 'robot mu', 'yapay zeka', 'kimsin', 'gercek kisi', 'gercek misin',
  'canli misin', 'canli mi', 'makine misin', 'sen kimsin', 'adin ne', 'chatgpt', 'gercek biri'];
const SELAM = new Set(['merhaba', 'merhabalar', 'selam', 'selamlar', 'slm', 'mrb', 'gunaydin', 'hey', 'hello', 'naber', 'nasilsin', 'iyigunler',
  'iyiaksamlar', 'sa', 'iyi', 'gunler', 'aksamlar', 'hosgeldin', 'meraba']);
const TESEKKUR = new Set(['tesekkur', 'tesekkurler', 'sagol', 'saol', 'eyvallah', 'mersi', 'eyvah', 'sagolun', 'tesekkurederim', 'harikasin', 'super', 'tamam', 'ok', 'anladim', 'tsk', 'tskler', 'tesekkurler']);
const ILAN_SOZ = new Set(['ilan', 'alim', 'acik', 'kontenjan', 'alinacak', 'alimi', 'duyuru']);
const NOISE_ONEK = ['ilan', 'alim', 'basvur', 'mezun', 'hangi', 'kpss', 'puan', 'acik', 'kontenj', 'duyuru', 'bugun', 'yarin', 'hafta', 'biten',
  'bitiyor', 'bitecek', 'yaklas', 'sona', 'gunu', 'nerede', 'nereden', 'nereye', 'nasil', 'olabil', 'olur', 'varmi', 'ariyor', 'istiyor', 'bakiyor',
  'lazim', 'gerek', 'calis', 'zaman', 'yeni', 'cikti', 'cikar', 'cikac', 'guncel', 'listele', 'goster', 'yapabil', 'girebil', 'girer', 'olunur',
  'sinav', 'sonuc', 'tercih', 'kadro', 'sartlar', 'sart'];
const NOISE_TAM = new Set(['isler', 'isim', 'kisi', 'personel', 'kamu', 'devlet', 'memuriyet', 'turkiye', 'ayrica', 'sadece', 'bunu', 'bana', 'lazim']);
const KURUM_GENEL = new Set(['genel', 'mudurlugu', 'mudurluk', 'baskanligi', 'bakanligi', 'kurumu', 'belediye', 'belediyesi', 'universitesi', 'sehir',
  'hastanesi', 'daire', 'baskanlik', 'personel', 'kamu', 'turkiye', 'cumhuriyeti', 'ilan', 'alim']);

function puanSinyali(katli, tokenlar, ham) {
  const puanSozu = tokenlar.some((t) => /^(kpss|puan|puani|puanim|puanla|puanimla|yeter|yeterli|girer|girerim|girebilir|nereye|alinir|p\d{1,3})/.test(t));
  const turu = /(^|\s)p(3|9[0-9]|1[01][0-9]|12[01]|[1-9][0-9]?)(\s|$)/.test(katli);
  let sayi = null;
  for (const m of ham.matchAll(/(?<![a-z0-9.,])(\d{2,3}(?:[.,]\d{1,2})?)(?![\d])/g)) {
    const v = Number(m[1].replace(',', '.'));
    if (v >= 30 && v <= 100) { sayi = v; break; }
  }
  const kalip = /kac puan|yeter mi|yetermi|puanimla|puanla |puanim|puanimin|puan yeter|puan ile|puanla$/.test(katli);
  return { sayi, turu, kalip, puanVar: turu || kalip || (sayi !== null && puanSozu) };
}

export function cozumle(soru, veri, sayfa) {
  let katli = sade(soru).replace(/\bon lisans/g, 'onlisans').replace(/\bkpss sartsiz/g, 'kpsssiz');
  katli = katli.replace(/\bgun aydin\b/, 'gunaydin');
  const tokenlar = katli.split(' ').filter(Boolean);
  const kokler = icerikKoklari(katli);
  const ps = puanSinyali(katli, tokenlar, katla(soru));

  let duzey = null;
  if (tokenlar.includes('onlisans') || /(^|\s)p93(\s|$)/.test(katli)) duzey = 'onlisans';
  else if (tokenlar.some((t) => t.startsWith('ortaogretim') || t === 'lise' || t === 'liseli') || /(^|\s)p94(\s|$)/.test(katli)) duzey = 'ortaogretim';
  else if (tokenlar.some((t) => t === 'lisans' || t === 'lisansli') || /(^|\s)p3(\s|$)/.test(katli)) duzey = 'lisans';

  const kpsssiz = tokenlar.some((t) => t.startsWith('kpsssiz'));
  const iller = ilBul(tokenlar);

  // Meslek: en uzun eşleşen ifade kazanır ("zabıta memuru" > "memur").
  let meslek = null;
  let meslekUzunluk = 0;
  const meslekKelimeleri = new Set();
  for (const m of veri.bilgi?.meslekler || []) {
    for (const k of m.kelimeler || []) {
      if (kelimeVar(katli, k) && k.length > meslekUzunluk) { meslek = m; meslekUzunluk = k.length; }
    }
  }
  if (meslek) for (const k of meslek.kelimeler) for (const t of tokenla(k)) meslekKelimeleri.add(govdeKok(t));

  // Sayfa bağlamı: meslek sayfasındayken mesleği ayrıca söylemeye gerek yok (yalnız ilan sorularında).
  let sayfaMeslek = null;
  const sm = /^\/meslek\/([a-z0-9-]+)\/?$/.exec(String(sayfa || ''));
  if (sm) sayfaMeslek = (veri.bilgi?.meslekler || []).find((m) => String(m.u).endsWith(`/meslek/${sm[1]}/`)) || null;

  const ilanSozu = kokler.some((t) => ILAN_SOZ.has(t)) || tokenlar.some((t) => ILAN_SOZ.has(t) || ILAN_SOZ.has(govdeKok(t)) || t.startsWith('ilan') || t.startsWith('alim'))
    || /\bvar ?mi\b|\bvar ?midir\b/.test(katli);

  // Süre filtresi: bugün / yarın / bu hafta / son günü yaklaşan.
  let zaman = null;
  if (/\bbugun\b/.test(katli) && /biten|bitiyor|bitecek|son gun|sona er|kapan/.test(katli)) zaman = 'bugun';
  else if (/\byarin\b/.test(katli)) zaman = 'yarin';
  else if (/\bbu hafta\b/.test(katli)) zaman = 'hafta';
  else if (/yaklas|bitmek uzere|sona yaklas|son gunu/.test(katli)) zaman = 'yaklasan';

  // Özgün yazılış (kullanıcıya hiçbir zaman katlanmış sözcük gösterilmez).
  const orj = new Map();
  for (const t of String(soru).toLocaleLowerCase('tr').replace(/['’`´]/g, ' ').split(/[^a-zçğıöşüâîû0-9]+/).filter(Boolean)) {
    if (!orj.has(katla(t))) orj.set(katla(t), t);
  }
  const orijinal = (t) => orj.get(t) || t;

  // Fazladan içerik sözcükleri: bilinen meslek/il/düzey/gürültü dışında kalanlar (polis, bekçi, bilgisayar...).
  const ekler = [];
  for (const t of tokenlar) {
    if (t.length < 4 || DURAK.has(t) || NOISE_TAM.has(t) || NOISE_ONEK.some((e) => t.startsWith(e))) continue;
    if (/^p\d+$/.test(t) || ['lisans', 'lisansli', 'onlisans', 'lise', 'liseli'].includes(t) || t.startsWith('ortaogretim') || t.startsWith('kpsssiz')) continue;
    if (SELAM.has(t) || TESEKKUR.has(t) || ilBul([t]).length) continue;
    if (meslek && meslek.kelimeler.some((k) => k.split(' ').some((w) => t.startsWith(w) && t.length - w.length <= 4))) continue;
    if (!ekler.some((e) => govdeKok(e) === govdeKok(t))) ekler.push(t);
  }
  let meslekSozu = null;
  if (meslek) {
    const son = tokenlar.filter((t) => meslek.kelimeler.some((k) => k.split(' ').some((w) => t.startsWith(w) && t.length - w.length <= 4))).pop();
    if (son) meslekSozu = orijinal(son);
  }

  return { katli, tokenlar, kokler, ...ps, duzey, kpsssiz, iller, meslek, meslekKelimeleri, sayfaMeslek, ilanSozu, zaman, ekler, orijinal, meslekSozu };
}

// ---------------------------------------------------------------- SSS eşleştirme (BM25 benzeri)

const ortakOn = (a, b) => { let n = 0; while (n < a.length && n < b.length && a[n] === b[n]) n++; return n; };
const eslesir = (a, b) => {
  if (a === b) return true;
  const kisa = Math.min(a.length, b.length);
  if (kisa >= 4 && (a.startsWith(b) || b.startsWith(a)) && Math.abs(a.length - b.length) <= 3) return true;
  const ortak = ortakOn(a, b);
  return ortak >= 5 && ortak >= 0.7 * kisa;
};
const sssOnbellek = new WeakMap();

function sssHazirla(sss) {
  let h = sssOnbellek.get(sss);
  if (!h) {
    h = sss.map((x) => ({ x, s: icerikKoklari(x.s), c: icerikKoklari(x.c) }));
    sssOnbellek.set(sss, h);
  }
  return h;
}

export function sssBul(a, sss) {
  const sorgu = [...new Set(a.kokler)];
  if (!sorgu.length || !Array.isArray(sss) || !sss.length) return null;
  const docs = sssHazirla(sss);
  const N = docs.length;
  const ortUzun = docs.reduce((t, d) => t + d.s.length + d.c.length, 0) / N || 1;
  let en = null;
  const idf = new Map();
  for (const q of sorgu) {
    const df = docs.filter((d) => d.s.some((t) => eslesir(q, t)) || d.c.some((t) => eslesir(q, t))).length;
    idf.set(q, Math.log(1 + (N - df + 0.5) / (df + 0.5)));
  }
  for (const d of docs) {
    let skor = 0;
    let eslesen = 0;
    const uzun = d.s.length + d.c.length;
    for (const q of sorgu) {
      const tf = 2 * d.s.filter((t) => eslesir(q, t)).length + d.c.filter((t) => eslesir(q, t)).length;
      if (!tf) continue;
      eslesen++;
      skor += idf.get(q) * (tf * 2.2) / (tf + 1.2 * (0.5 + 0.5 * uzun / ortUzun));
    }
    const kapsam = eslesen / sorgu.length;
    if (!en || skor > en.skor) en = { sss: d.x, skor, eslesen, kapsam };
  }
  if (!en) return null;
  const yeterli = en.skor >= 3 && en.kapsam >= 0.5 && (sorgu.length === 1 || en.eslesen >= 2);
  return yeterli ? { ...en, guclu: en.skor >= 4.5 && en.kapsam >= 0.6 } : null;
}

function cumleKirp(c, max = 450) {
  const t = String(c || '').replace(/\s+/g, ' ').trim();
  if (t.length <= max) return t;
  const kes = t.slice(0, max);
  const son = Math.max(kes.lastIndexOf('. '), kes.lastIndexOf('! '), kes.lastIndexOf('? '));
  if (son > 120) return kes.slice(0, son + 1);
  return `${kes.slice(0, kes.lastIndexOf(' ')).replace(/[,;:\s]+$/, '')}…`;
}

// ---------------------------------------------------------------- ilan bulma

const ilanOnbellek = new WeakMap();
function ilanOzeti(i) {
  let o = ilanOnbellek.get(i);
  if (!o) {
    o = { metin: sade(`${i.baslik || ''} ${i.metin || ''} ${i.kurum || ''}`), baslik: sade(i.baslik), kurum: sade(i.kurum),
      iller: (Array.isArray(i.iller) ? i.iller : []).map(katla) };
    ilanOnbellek.set(i, o);
  }
  return o;
}

function ilanUrl(i, site) {
  const s = String(i.sayfa || '');
  if (/^https:\/\/(www\.)?kpsstercihi\.com\//.test(s)) return s;
  if (s && !/^[a-z]+:/i.test(s) && !s.startsWith('//')) return site + s.replace(/^\/+/, '');
  return site;
}

function acikIlanlar(veri, simdi) {
  const bugun = bugunIstanbul(simdi);
  return (veri.ilanlar || []).filter((i) => i && typeof i === 'object' && i.kategori !== 'akademik' && (i.son_tarih || i.son_zaman)
    && !sureDoldu(i, bugun, simdi));
}

const DUZEY_AD = { lisans: 'lisans', onlisans: 'önlisans', ortaogretim: 'ortaöğretim' };

const trBuyuk = (w) => (w ? w[0].toLocaleUpperCase('tr') + w.slice(1).toLocaleLowerCase('tr') : w);
export const basHarfBuyuk = (ad) => String(ad || '').split(/\s+/).filter(Boolean).map(trBuyuk).join(' ');

// "İstanbul" -> "İstanbul'da", "Muş" -> "Muş'ta" (ünlü uyumu + sert ünsüz).
export function bulunmaEki(ad) {
  const k = String(ad).toLocaleLowerCase('tr');
  const unlu = [...k].reverse().find((c) => 'aıoueiöüâîû'.includes(c)) || 'e';
  const sert = 'fstkçşhp'.includes(k[k.length - 1]);
  return `${ad}'${sert ? 't' : 'd'}${'aıouâû'.includes(unlu) ? 'a' : 'e'}`;
}
const ilEtiketi = (iller) => (iller.length < 2 ? bulunmaEki(iller[0]) : `${iller.slice(0, -1).join(', ')} ve ${bulunmaEki(iller[iller.length - 1])}`);

const gunEkle = (gun, n) => new Date(Date.parse(`${gun}T00:00:00Z`) + n * 86400000).toISOString().slice(0, 10);
function ekEslesir(w, t) {
  const x = govdeKok(w);
  const y = govdeKok(t);
  return x === y || (Math.min(x.length, y.length) >= 5 && ortakOn(x, y) >= 5);
}
const ekVar = (metin, w) => metin.split(' ').some((t) => ekEslesir(w, t));

function ilanSuz(a, acik, bugun) {
  // Somut filtreler: meslek, il, düzey, KPSS'siz, kurum sözcüğü, süre. Belirtilen her tür sağlanmalı (tür içinde "ya da").
  const meslek = a.meslek || (a.ilanSozu ? a.sayfaMeslek : null);
  const kurumSoz = new Map();
  for (const i of acik) for (const t of ilanOzeti(i).kurum.split(' ')) {
    const k = govdeKok(t);
    if (k.length >= 5 && !KURUM_GENEL.has(k) && !KURUM_GENEL.has(t) && !IL_LISTESI.some((il) => il.k === t) && !kurumSoz.has(k)) kurumSoz.set(k, t);
  }
  const kurumlar = [...new Set(a.kokler.filter((k) => k.length >= 5 && kurumSoz.has(k) && !(meslek && (a.meslekKelimeleri.has(k)
    || (a.sayfaMeslek && !a.meslek)))))];
  const ekler = a.ekler.filter((e) => !kurumlar.includes(govdeKok(e)) && !kurumlar.includes(esKok(govdeKok(e))));
  const iller = a.iller.map(katla);
  const baska = !!(meslek || iller.length || a.duzey || a.kpsssiz || kurumlar.length || a.zaman);
  const somut = baska || ekler.length > 0;
  if (!somut) return { somut, baska, sonuc: [], meslek, kurumlar, ekler: [], ekKullanildi: false };
  const sinir = a.zaman === 'bugun' ? bugun : a.zaman === 'yarin' ? gunEkle(bugun, 1) : a.zaman ? gunEkle(bugun, 7) : null;
  const sonuc = [];
  for (const i of acik) {
    const o = ilanOzeti(i);
    let puan = 0;
    if (meslek) {
      if (!meslek.kelimeler.some((k) => kelimeVar(o.metin, k))) continue;
      puan += 3;
    }
    if (iller.length) {
      if (!o.iller.some((x) => iller.includes(x))) continue;
      puan += 2;
    }
    if (a.duzey) {
      if (!(Array.isArray(i.ogrenim) && i.ogrenim.includes(a.duzey))) continue;
      puan += 1;
    }
    if (a.kpsssiz) {
      if (i.kpss !== 'kpsssiz') continue;
      puan += 2;
    }
    if (kurumlar.length) {
      if (!kurumlar.some((k) => o.kurum.split(' ').some((t) => govdeKok(t) === k))) continue;
      puan += 2;
    }
    if (a.zaman) {
      const t = String(i.son_tarih || '');
      if (!t || t < bugun) continue;
      if (a.zaman === 'bugun' ? t !== bugun : a.zaman === 'yarin' ? t !== sinir : t > sinir) continue;
      puan += 1;
    }
    const ekMetin = meslek ? o.metin : `${o.baslik} ${o.kurum}`;
    const ekSayi = ekler.filter((w) => ekVar(ekMetin, w)).length;
    sonuc.push({ i, puan: puan + ekSayi * 2, ekSayi });
  }
  let son = sonuc;
  let ekKullanildi = false;
  if (ekler.length) {
    const tam = sonuc.filter((x) => x.ekSayi === ekler.length);
    if (tam.length) { son = tam; ekKullanildi = true; } else if (!baska) son = []; // yalnız bilinmeyen sözcük: bulunamadı
  }
  son.sort((x, y) => y.puan - x.puan || String(x.i.son_tarih || '9999').localeCompare(String(y.i.son_tarih || '9999')));
  return { somut, baska, sonuc: son, meslek, kurumlar, ekler, ekKullanildi, kurumSoz };
}

// ---------------------------------------------------------------- cevapları kurma

const ONERI_PUAN = 'Puanımla nereye başvurabilirim?';
const ONERI_ILAN = 'Şu an açık ilanlar neler?';
const ONERI_KARIYER = 'Kariyer Kapısı’na nasıl giriş yapılır?';
const ONERI_TABAN = 'Taban puanlarına nereden bakabilirim?';
const ONERI_ZABITA = 'Açık zabıta ilanı var mı?';

function cevapNesnesi(tur, metin, baglantilar = [], ilanlar = [], oneriler = []) {
  return { tur, metin, baglantilar: baglantilar.slice(0, 3), ilanlar: ilanlar.slice(0, 5), oneriler: oneriler.slice(0, 3) };
}

export function cevapla(soru, veri, simdi = new Date(), sayfa = '') {
  const site = (veri.site || VARSAYILAN_SITE).replace(/\/?$/, '/');
  const bag = (ad, yol) => ({ ad, url: yol.startsWith('http') ? yol : site + yol });
  const ANA = bag('Ana sayfa', '');
  const NEREYE = bag('Bana uygun ilanlar', 'nereye/');
  const SSS = bag('Sık sorulan sorular', 'sss/');
  const KANAL = bag('Telegram kanalı', TELEGRAM);
  const a = cozumle(soru, veri, sayfa);

  // a) kimlik
  if (KIMLIK.some((k) => kelimeVar(a.katli, k))) {
    return cevapNesnesi('kimlik', 'KPSS Tercihi’nin otomatik asistanıyım. Sitedeki ilan ve puan bilgilerine bakarak cevap veriyorum; emin olmadığım yerde seni doğru sayfaya yönlendiriyorum.',
      [ANA, SSS], [], [ONERI_PUAN, ONERI_ILAN]);
  }

  const baska = a.puanVar || a.iller.length || a.meslek || a.duzey || a.kpsssiz || a.ilanSozu;
  // b) selam / teşekkür (kısa ve başka bir konu içermeyen mesajlar)
  if (!baska && a.tokenlar.length > 0 && a.tokenlar.length <= 5) {
    if (a.tokenlar.some((t) => TESEKKUR.has(t)) || /(^| )sag ol(un)?( |$)/.test(a.katli)) {
      return cevapNesnesi('tesekkur', 'Rica ederim, ne demek. Aklına takılan başka bir şey olursa buradayım.', [],
        [], [ONERI_PUAN, ONERI_ILAN, ONERI_KARIYER]);
    }
    if (a.tokenlar.some((t) => SELAM.has(t))) {
      return cevapNesnesi('selam', 'Merhaba, hoş geldin. KPSS Tercihi’nin asistanıyım; ilanlar, puanlar ve başvuru konularında sorularına bakabilirim.', [],
        [], [ONERI_PUAN, ONERI_ZABITA, ONERI_KARIYER]);
    }
  }

  // c) puan: asla hesap yapılmaz
  if (a.puanVar) {
    const baglantilar = [NEREYE];
    if (a.duzey) baglantilar.push(bag(`${DUZEY_AD[a.duzey][0].toLocaleUpperCase('tr')}${DUZEY_AD[a.duzey].slice(1)} taban puanları`, `kpss-taban-puanlari/${a.duzey}/`));
    else baglantilar.push(bag('KPSS taban puanları', 'kpss-taban-puanlari/'));
    if (a.meslek) baglantilar.push({ ad: `${a.meslek.ad} sayfası`, url: a.meslek.u });
    return cevapNesnesi('puan', 'Puanın yeter mi sorusuna kesin bir şey söyleyemem, çünkü şartlar ilandan ilana değişiyor. “Bana uygun ilanlar” sayfasında puanını ve bölümünü girersen açık ilanlardan sana uyanları görürsün. Geçmişte hangi puanlarla yerleşildiğini ise taban puanları sayfasında bulabilirsin. Şartlarda her zaman resmî ilan metni esastır.',
      baglantilar, [], [ONERI_ILAN, ONERI_TABAN]);
  }

  const sss = sssBul(a, veri.bilgi?.sss);
  const somutAday = !!(a.iller.length || a.meslek || a.duzey || a.kpsssiz || a.zaman);
  const varMi = /\bvar ?mi/.test(a.katli);
  const ilanNiyeti = a.ilanSozu || /basvurabil|hangi|(^| )(is|isi|isler|kadro|memurluk|memur|calis[a-z]*|ariyor[a-z]*)( |$)/.test(a.katli);
  // Güçlü bir SSS eşleşmesi varken ("zabıtada yaş sınırı") ilan listesi çıkarılmaz; "var mı", il, KPSS'siz, süre ya da
  // "düzey + hangi ilanlara başvurabilirim" gibi liste isteyen sorularda ilan aranır.
  const sssOnce = !!(sss && sss.guclu && !varMi && !a.iller.length && !a.kpsssiz && !a.zaman && !(a.duzey && ilanNiyeti));
  const acik = acikIlanlar(veri, simdi);
  const bugun = bugunIstanbul(simdi);
  const ekEsler = a.ekler.length > 0 && acik.some((i) => { const o = ilanOzeti(i); return a.ekler.every((w) => ekVar(`${o.baslik} ${o.kurum}`, w)); });
  const ilanDene = (a.ilanSozu || somutAday || ekEsler) && !sssOnce;

  // d) ilan
  if (ilanDene) {
    const suz = ilanSuz(a, acik, bugun);
    if (suz.somut || a.ilanSozu) {
      const mesBag = suz.meslek ? [{ ad: `${suz.meslek.ad} sayfası`, url: suz.meslek.u }] : [];
      const nerBag = a.duzey ? [NEREYE] : [];
      if (!suz.somut) {
        return cevapNesnesi('ilan', `Şu an sitede ${acik.length} açık ilan var; hangi ili, mesleği ya da öğrenim düzeyini aradığını yazarsan daraltırım. İlan şartlarında resmî ilan metni esastır.`,
          [ANA, NEREYE], [], [ONERI_PUAN, ONERI_ZABITA]);
      }
      // Kullanıcıya gösterilen etiket: özgün yazılış, il için bulunma eki, meslek küçük harfle.
      const konu = [];
            if (suz.kurumlar.length) {
        const ilk = suz.sonuc[0]?.i;
        const kurumAd = ilk ? basHarfBuyuk(ilk.kurum) : basHarfBuyuk(a.orijinal(suz.kurumSoz.get(suz.kurumlar[0]) || suz.kurumlar[0]));
        konu.push(kurumAd);
      }
      const ekYazi = suz.ekKullanildi ? suz.ekler.map((e) => a.orijinal(e)) : [];
      if (suz.meslek) konu.push([...ekYazi, ekYazi.length && a.meslekSozu ? a.meslekSozu : suz.meslek.ad.toLocaleLowerCase('tr')].join(' '));
      else if (ekYazi.length) konu.push(ekYazi.join(' '));
      const konuYazi = konu.join(' ');
      const mod = [];
      if (a.iller.length) mod.push(ilEtiketi(a.iller));
      if (a.duzey) mod.push(`${DUZEY_AD[a.duzey]} mezunlarına yönelik`);
      if (a.kpsssiz) mod.push('KPSS şartı olmayan');
      if (konuYazi && !a.kpsssiz) mod.push(`${konuYazi} için`);
      const icin = mod.length ? `${mod.join(' ')} ` : '';
      const isim = konuYazi && a.kpsssiz ? `${konuYazi} ilanı` : 'ilan';
      const ZAMAN_BAS = { bugun: 'Bugün son günü olan', yarin: 'Yarın son günü olan', hafta: 'Bu hafta içinde son günü gelen', yaklasan: 'Son günü 7 gün içinde gelen' };
            if (!suz.sonuc.length) {
        if (!suz.baska && suz.ekler.length) {
          const soz = suz.ekler.map((e) => a.orijinal(e)).join(' ');
          return cevapNesnesi('ilan', `Şu an başlığında “${soz}” geçen açık ilan görmüyorum. Yeni ilanlar çıktığında Telegram kanalımızda hemen paylaşılıyor.`,
            [KANAL, ANA], [], [ONERI_ILAN, ONERI_PUAN]);
        }
        const ek = suz.meslek ? ' Geçmiş ilanlara ve taban puanlarına meslek sayfasından bakabilirsin.' : '';
        const giris = a.zaman ? `${ZAMAN_BAS[a.zaman]} ${icin}açık ilan göremiyorum.` : `Şu an ${icin}açık bir ilan göremiyorum.`;
        return cevapNesnesi('ilan', `${giris} Yeni ilanlar çıktıkça Telegram kanalımızda paylaşılıyor.${ek}`,
          [...mesBag, ...nerBag, KANAL, ANA], [], [ONERI_ILAN, ONERI_PUAN]);
      }
      const n = suz.sonuc.length;
      const ilanlar = suz.sonuc.slice(0, 5).map(({ i }) => ({ baslik: i.baslik, kurum: i.kurum, son_tarih: i.son_tarih || null,
        iller: (Array.isArray(i.iller) ? i.iller : []).slice(0, 5), url: ilanUrl(i, site) }))
        .sort((x, y) => String(x.son_tarih || '9999').localeCompare(String(y.son_tarih || '9999')));
      const sayi = n > 5 ? `${n} ${isim} buldum, son tarihi en yakın 5 tanesini gösteriyorum` : `${n} ${isim} buldum`;
      const giris = a.zaman ? `${ZAMAN_BAS[a.zaman]}${icin ? `, ${icin}` : ' '}açık ${sayi}.` : `Şu an ${icin}açık ${sayi}.`;
      return cevapNesnesi('ilan', `${giris} Başvurmadan önce şartları resmî ilan metninden kontrol etmeni öneririm.`,
        [...mesBag, NEREYE], ilanlar, [ONERI_PUAN, ONERI_TABAN]);
    }
  }

  // e) sss
  if (sss) {
    const u = sss.sss.u;
    const mes = (veri.bilgi?.meslekler || []).find((m) => m.u === u);
    const sayfaBilgi = (veri.bilgi?.sayfalar || []).find((p) => p.u === u);
    const ad = mes ? `${mes.ad} sayfası` : sayfaBilgi ? sayfaBilgi.ad : /\/rehber\//.test(u) ? 'Rehber yazısı' : 'Devamı için';
    return cevapNesnesi('sss', cumleKirp(sss.sss.c), [{ ad, url: u }], [], [ONERI_PUAN, ONERI_ILAN]);
  }

  // f) bilinmiyor
  return cevapNesnesi('bilinmiyor', 'Bunu kesin bilemiyorum, yanlış bir şey söylemek istemem. Ana sayfadaki açık ilanlara ya da sık sorulan sorulara bakabilirsin; Telegram kanalımızda da güncel duyurular paylaşılıyor.',
    [ANA, SSS, KANAL], [], [ONERI_PUAN, ONERI_ILAN, ONERI_KARIYER]);
}

// ---------------------------------------------------------------- Workers AI ile cilalama

const YZ_SISTEM = `Sen kpsstercihi.com'un ("biz, KPSS Tercihi") soru-cevap kutusunda yazan sıcak ve kısa bir sesin.
Sana bir soru ve "gerçekler" verilecek. Gerçekleri aynı anlamda, doğal ve sade bir Türkçeyle 1 ile 3 cümleyle yeniden yaz.
Kurallar: Yalnızca verilen gerçekleri kullan; sayı, tarih, şart, bağlantı ya da yeni bilgi ekleme. "Sen" diliyle konuş, emir kipinden kaçın ("bakabilirsin" gibi söyle).
Emoji, "vb." ve "vs." kullanma. Kendinden yapay zekâ ya da dil modeli diye söz etme, asla insan olduğunu söyleme. Şart ve koşullarda resmî ilan metninin esas olduğunu gerektiğinde kısaca hatırlat.
Yalnızca cevap metnini yaz.`;

const YASAK = /yapay zek|dil modeli|\bvb\.|\bvs\.|insanim|insaniz|gercek (bir )?(kisi|insan)|https?:|www\.|\.com|\.gov|\.org|t\.me|@/;
// Model sayıyı yazıyla, tarihi ay adıyla ya da bugün/yarın diye uydurmasın: gerçeklerde geçmeyen bu sözcükler reddedilir.
const SAYI_SOZ = ['iki', 'uc', 'dort', 'bes', 'alti', 'yedi', 'sekiz', 'dokuz', 'on', 'yirmi', 'otuz', 'kirk', 'elli', 'altmis', 'yetmis', 'seksen',
  'doksan', 'yuz', 'bin', 'ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik',
  'bugun', 'yarin', 'hafta'];

export function yzDogrula(cikti, gercekler) {
  if (typeof cikti !== 'string') return null;
  const t = cikti.trim().replace(/^["“]|["”]$/g, '').trim();
  if (t.length < 15 || t.length > 500) return null;
  if (/[^\u0000-\u024f\u2000-\u206f]/.test(t)) return null; // Türkçe/Latin dışı yazı ve emoji
  if (YASAK.test(katla(t))) return null;
  const izinli = new Set(String(gercekler).match(/\d+/g) || []);
  for (const d of t.match(/\d+/g) || []) if (!izinli.has(d)) return null;
  const gSoz = new Set(sade(gercekler).split(' '));
  for (const s of sade(t).split(' ')) if (SAYI_SOZ.includes(s) && !gSoz.has(s)) return null;
  return t;
}

async function yzCilala(env, soru, cevap) {
  if (!env.AI || env.ASISTAN_YZ === '0') return null;
  // SSS cevapları elle yazılmış ve doğrulanmış metinlerdir; model bunları yeniden yazarsa şartı (düzey, yaş) bozabilir → olduğu gibi kalır.
  if (!['ilan', 'puan'].includes(cevap.tur)) return null;
  // İlan kartları (başlık, kurum, tarih) koddan çizilir; modele yalnız şablon cümle verilir ki tarihleri ilanlar arasında karıştıramasın.
  const gercekler = cevap.metin;
  let zamanlayici;
  try {
    const cagri = env.AI.run(env.ASISTAN_MODEL || VARSAYILAN_MODEL, {
      messages: [{ role: 'system', content: YZ_SISTEM }, { role: 'user', content: `Soru: ${soru}\n\nGerçekler: ${gercekler}` }],
      max_tokens: 220, temperature: 0.3,
    });
    const bekle = new Promise((_, red) => { zamanlayici = setTimeout(() => red(new Error('zaman aşımı')), YZ_ZAMAN_MS); });
    const sonuc = await Promise.race([cagri, bekle]);
    const metin = typeof sonuc === 'string' ? sonuc : sonuc?.response;
    return yzDogrula(metin, gercekler);
  } catch {
    return null; // kota dolması dahil her hata: şablon cevap
  } finally {
    clearTimeout(zamanlayici);
  }
}

// ---------------------------------------------------------------- veri yükleme (10 dk bellek)

const bellek = { ilan: null, bilgi: null };
const hiz = new Map();

export function testSifirla() {
  bellek.ilan = null;
  bellek.bilgi = null;
  hiz.clear();
}

async function jsonCek(url) {
  let zamanlayici;
  try {
    const bekle = new Promise((_, red) => { zamanlayici = setTimeout(() => red(new Error('zaman aşımı')), FETCH_ZAMAN_MS); });
    const r = await Promise.race([fetch(url, { cf: { cacheTtl: 300 } }), bekle]);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(zamanlayici);
  }
}

async function bellekliCek(anahtar, url, simdiMs) {
  const m = bellek[anahtar];
  if (m && simdiMs - m.t < ONBELLEK_MS) return m.veri;
  if (!url) return m ? m.veri : null;
  try {
    const veri = await jsonCek(url);
    bellek[anahtar] = { t: simdiMs, veri };
    return veri;
  } catch {
    return m ? m.veri : null; // eski kopya
  }
}

export async function veriYukle(env) {
  const simdiMs = Date.now();
  const site = String(env.SITE_URL || VARSAYILAN_SITE).replace(/\/?$/, '/');
  const [ilan, bilgi] = await Promise.all([
    bellekliCek('ilan', env.ILAN_URL, simdiMs),
    bellekliCek('bilgi', `${site}asistan/bilgi.json`, simdiMs),
  ]);
  return { site, ilanlar: Array.isArray(ilan?.ilanlar) ? ilan.ilanlar : [], bilgi: bilgi && typeof bilgi === 'object' ? bilgi : null };
}

// ---------------------------------------------------------------- HTTP

function corsBasliklari(origin) {
  const h = { 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '86400', Vary: 'Origin' };
  if (origin && IZINLI_ORIGINLER.test(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}
const yanit = (govde, durum, origin) => new Response(JSON.stringify(govde), {
  status: durum, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...corsBasliklari(origin) },
});

function hizAsildi(ip, simdiMs) {
  const liste = (hiz.get(ip) || []).filter((t) => simdiMs - t < HIZ_PENCERE_MS);
  if (liste.length >= HIZ_MAX) { hiz.set(ip, liste); return true; }
  liste.push(simdiMs);
  hiz.set(ip, liste);
  if (hiz.size > 5000) {
    for (const [k, v] of hiz) if (!v.some((t) => simdiMs - t < HIZ_PENCERE_MS)) hiz.delete(k);
    // Çok sayıda farklı IP (IPv6 döndürme) belleği şişirmesin: en eski kayıtlar atılır (Map ekleme sırasını korur).
    for (const k of hiz.keys()) { if (hiz.size <= 5000) break; hiz.delete(k); }
  }
  return false;
}

// Gövdeyi en çok 'sinir' bayt okur; aşarsa null (akış iptal edilir).
async function sinirliOku(request, sinir) {
  if (!request.body) return '';
  const okuyucu = request.body.getReader();
  const parcalar = [];
  let toplam = 0;
  for (;;) {
    const { done, value } = await okuyucu.read();
    if (done) break;
    toplam += value.byteLength;
    if (toplam > sinir) { try { await okuyucu.cancel(); } catch { /* sessiz */ } return null; }
    parcalar.push(value);
  }
  const bayt = new Uint8Array(toplam);
  let k = 0;
  for (const p of parcalar) { bayt.set(p, k); k += p.byteLength; }
  return new TextDecoder().decode(bayt);
}

const temizle = (s) => String(s).replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\ufeff]/g, ' ').replace(/\s+/g, ' ').trim();

export async function asistanIstek(request, env, ctx) {
  const origin = request.headers.get('Origin');
  const url = new URL(request.url);
  if (url.pathname !== '/asistan/sor') return yanit({ metin: 'bulunamadı' }, 404, origin);
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsBasliklari(origin) });
  if (request.method !== 'POST') return yanit({ metin: 'yöntem desteklenmiyor' }, 405, origin);
  if (origin && !IZINLI_ORIGINLER.test(origin)) return yanit({ metin: 'köken izinli değil' }, 403, origin);

  const ip = request.headers.get('CF-Connecting-IP') || 'bilinmiyor';
  if (hizAsildi(ip, Date.now())) return yanit({ metin: 'Biraz hızlı gittik, bir dakika sonra tekrar sorabilirsin.' }, 429, origin);

  let govde;
  try {
    // Gövde, JSON çözümlenmeden ve tamamı belleğe alınmadan önce sınırlanır (Content-Length yalan/eksik olabilir).
    if (Number(request.headers.get('Content-Length') || 0) > GOVDE_MAX) return yanit({ metin: 'Soru çok uzun.' }, 400, origin);
    const ham = await sinirliOku(request, GOVDE_MAX);
    if (ham === null) return yanit({ metin: 'Soru çok uzun.' }, 400, origin);
    govde = JSON.parse(ham);
  } catch {
    return yanit({ metin: 'Soruyu okuyamadım.' }, 400, origin);
  }
  if (!govde || typeof govde !== 'object' || typeof govde.soru !== 'string') return yanit({ metin: 'Soruyu okuyamadım.' }, 400, origin);
  const soru = temizle(govde.soru);
  if (!soru) return yanit({ metin: 'Bir şey yazmadın, ne öğrenmek istersin?' }, 400, origin);
  if (soru.length > 4 * SORU_MAX) return yanit({ metin: 'Soru çok uzun.' }, 400, origin);
  const kisa = soru.slice(0, SORU_MAX);
  const sayfa = typeof govde.sayfa === 'string' ? govde.sayfa.slice(0, 200) : '';

  try {
    const veri = await veriYukle(env);
    const c = cevapla(kisa, veri, new Date(), sayfa);
    const cilali = await yzCilala(env, kisa, c);
    const { tur, ...disari } = c; // eslint-disable-line no-unused-vars
    return yanit({ ...disari, metin: cilali || c.metin }, 200, origin);
  } catch {
    return yanit({ metin: 'Şu an cevap veremiyorum; biraz sonra tekrar dener misin?', baglantilar: [], ilanlar: [], oneriler: [] }, 500, origin);
  }
}
