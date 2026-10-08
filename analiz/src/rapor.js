// Panel verisi: ham/özet satırlarından tek bir JSON gövdesi üretir.
import { aralikOku, birlestir } from './sorgu.js';
import { aralikCoz, gunListesi } from './zaman.js';

const sirala = (liste, alan = 'say') => liste.slice().sort((a, b) => b[alan] - a[alan]);
const ilk = (liste, n) => liste.slice(0, n);
const sayi = (r, f) => (r ? r[f] : 0);
const tamam = (n) => Math.round(n);

function parcala(k2) {
  const [h = '', x = '', n = ''] = String(k2).split('|');
  return { h, x, n: n === '' ? null : Number(n) };
}

function agirlikliOrtalama(satirlar) {
  let t = 0, a = 0;
  for (const r of satirlar) { t += r.say; a += r.say * r.toplam; }
  return t ? tamam(a / t) : null;
}

export function ilanYollari(rows) {
  const anahtarlar = new Set();
  for (const r of rows) {
    if (['ilan_goruntu', 'ilan_sure'].includes(r.boyut) && r.k1) anahtarlar.add(r.k1);
    if (r.boyut === 'tikla_hedef' && r.k1 === 'resmi_ilan') { const { h } = parcala(r.k2); if (h) anahtarlar.add(h); }
    if (r.boyut === 'sayfa') { const m = r.k1.match(/^\/ilan\/([A-Za-z0-9-]+)\/?$/); if (m) anahtarlar.add(m[1]); }
  }
  return anahtarlar;
}

export async function raporUret(env, aralik, simdiMs = Date.now(), adlariGetir = async () => ({})) {
  const { bas, bit, adet } = aralikCoz(aralik, simdiMs);
  const rows = await aralikOku(env.DB, bas, bit);
  const B = (b) => birlestir(rows, b);
  const adlar = (await adlariGetir(ilanYollari(rows))) || {};
  const ad = (k) => adlar[k] || null;

  // Günlük seri
  const genelGun = new Map(rows.filter((r) => r.boyut === 'genel').map((r) => [r.gun, r]));
  const gunler = gunListesi(bas, bit).map((g) => ({ gun: g, ziyaretci: sayi(genelGun.get(g), 'tekil'), oturum: sayi(genelGun.get(g), 'oturum'), sayfa: sayi(genelGun.get(g), 'say') }));
  const genel = B('genel')[0] || { say: 0, tekil: 0, oturum: 0 };
  const etkin = B('etkin')[0] || { toplam: 0 };
  const oz = Object.fromEntries(B('oturum_ozet').map((r) => [r.k1, r.say]));
  const hemen = oz.hemen || 0;
  const oturumToplam = hemen + (oz.diger || 0);
  const yg = Object.fromEntries(B('yeni_geri').map((r) => [r.k1, r.tekil]));

  const kpi = {
    ziyaretci: genel.tekil,
    oturum: genel.oturum,
    sayfa: genel.say,
    etkinSaniyeOrt: genel.oturum ? tamam(etkin.toplam / genel.oturum) : 0,
    hemenCikma: oturumToplam ? hemen / oturumToplam : 0,
    yeni: yg.yeni || 0,
    geri: yg.geri || 0,
  };

  const isi = B('isi').map((r) => [Number(r.k1), Number(r.k2), r.say]);
  const liste = (b, f) => ilk(sirala(B(b)).map(f), 30);
  const k1say = (r) => ({ ad: r.k1, oturum: r.say, ziyaretci: r.tekil });

  // Görünümler ve ilanlar
  const sureGorunum = new Map(B('gorunum_sure').map((r) => [r.k1, r]));
  const gorunumler = sirala(B('gorunum')).map((r) => ({ v: r.k1, say: r.say, tekil: r.tekil, sureSn: sayi(sureGorunum.get(r.k1), 'toplam') }));
  const ilanSure = new Map(B('ilan_sure').map((r) => [r.k1, r]));
  const ilanlar = sirala(B('ilan_goruntu')).map((r) => ({ k: r.k1, ad: ad(r.k1), say: r.say, tekil: r.tekil, sureSn: sayi(ilanSure.get(r.k1), 'toplam') }));
  const enUzun = ilk(sirala(B('ilan_sure').map((r) => {
    const g = B('ilan_goruntu').find((x) => x.k1 === r.k1);
    return { k: r.k1, ad: ad(r.k1), say: g ? g.say : 0, sureSn: r.toplam, ortSn: g && g.say ? tamam(r.toplam / g.say) : r.toplam };
  }), 'sureSn'), 15);

  // Etkileşim
  const hedefler = B('tikla_hedef').map((r) => ({ a: r.k1, ...parcala(r.k2), say: r.say, tekil: r.tekil }));
  const tikla = sirala(B('tikla_ad')).map((r) => ({ a: r.k1, say: r.say, tekil: r.tekil }));
  const toplaAd = (a) => sayi(B('tikla_ad').find((r) => r.k1 === a), 'say');
  const grupla = (a, anahtar) => {
    const m = new Map();
    for (const r of hedefler.filter((x) => x.a === a)) { const k = anahtar(r); m.set(k, (m.get(k) || 0) + r.say); }
    return sirala([...m].map(([k, say]) => ({ k, say })));
  };
  const aramaSatir = B('arama');
  const aramalar = new Map();
  for (const r of aramaSatir) { const o = aramalar.get(r.k1) || { q: r.k1, var: 0, sifir: 0 }; o[r.k2 === 'sifir' ? 'sifir' : 'var'] += r.say; aramalar.set(r.k1, o); }
  const aramaListe = [...aramalar.values()];
  const h1 = Object.fromEntries(B('huni').map((r) => [r.k1, r]));

  const kaydirmaToplam = new Map();
  for (const r of B('kaydirma')) kaydirmaToplam.set(r.k1, (kaydirmaToplam.get(r.k1) || 0) + r.say);

  return {
    aralik: { bas, bit, adet },
    kpi,
    gunler,
    isi,
    kaynak: ilk(sirala(B('kaynak')).map(k1say), 12),
    rhost: liste('rhost', k1say),
    utm: liste('utm', (r) => ({ kaynak: r.k1, kampanya: r.k2, oturum: r.say })),
    sehir: liste('sehir', (r) => ({ ad: r.k1, ulke: r.k2, oturum: r.say, ziyaretci: r.tekil })),
    ulke: liste('ulke', k1say),
    cihaz: liste('cihaz', k1say),
    tarayici: liste('tarayici', k1say),
    isletim: liste('isletim', k1say),
    genislik: B('genislik').sort((a, b) => ['<480', '480-767', '768-1023', '1024-1439', '1440+'].indexOf(a.k1) - ['<480', '480-767', '768-1023', '1024-1439', '1440+'].indexOf(b.k1)).map(k1say),
    sayfalar: ilk(sirala(B('sayfa')).map((r) => {
      const m = r.k1.match(/^\/ilan\/([A-Za-z0-9-]+)\/?$/);
      return { p: r.k1, v: r.k2, ad: m ? ad(m[1]) : null, say: r.say, tekil: r.tekil };
    }), 25),
    gorunumler,
    ilanlar: ilk(ilanlar, 15),
    enUzun,
    kurumlar: ilk(sirala(B('kurum')).map((r) => ({ k: r.k1, say: r.say, tekil: r.tekil })), 15),
    taban: ilk(sirala(B('taban')).map((r) => ({ k: r.k1, say: r.say, tekil: r.tekil })), 15),
    tikla: ilk(tikla, 25),
    kategori: ilk(hedefler.filter((x) => x.a === 'kategori').map((x) => ({ k: [x.h, x.x].filter(Boolean).join(' / '), say: x.say })).sort((a, b) => b.say - a.say), 15),
    filtre: ilk(hedefler.filter((x) => x.a === 'filtre').map((x) => ({ filtre: x.h, deger: x.x, say: x.say })).sort((a, b) => b.say - a.say), 20),
    aramalar: ilk(aramaListe.sort((a, b) => (b.var + b.sifir) - (a.var + a.sifir)), 20),
    sifirAramalar: ilk(aramaListe.filter((x) => x.sifir > 0).sort((a, b) => b.sifir - a.sifir), 20),
    manset: {
      konum: grupla('manset_tikla', (r) => String(r.n ?? 0)).map((r) => ({ n: Number(r.k), say: r.say })).sort((a, b) => a.n - b.n),
      nokta: toplaAd('manset_nokta'),
      ok: toplaAd('manset_ok'),
    },
    robot: ilk(hedefler.filter((x) => x.a === 'robot').map((x) => ({ duzey: x.x, puan: x.n, say: x.say })).sort((a, b) => b.say - a.say), 15),
    donusum: {
      telegram: toplaAd('telegram'), resmi: toplaAd('resmi_ilan'), kaydet: toplaAd('kaydet'), kaydiSil: toplaAd('kaydi_sil'),
      takvim: toplaAd('takvim_ics'), tema: toplaAd('tema'), profil: toplaAd('profil_kaydet'),
    },
    resmiIlanlar: ilk(grupla('resmi_ilan', (r) => r.h).map((r) => ({ k: r.k, ad: ad(r.k), say: r.say })), 10),
    kaydedilenIlanlar: ilk(grupla('kaydet', (r) => r.h).map((r) => ({ k: r.k, ad: ad(r.k), say: r.say })), 10),
    huni: {
      oturum: genel.oturum, ana: sayi(h1.huni, 'say'), ilan: sayi(h1.huni, 'tekil'), resmi: sayi(h1.huni, 'oturum'),
      anaIlan: sayi(h1.huni, 'toplam'), ilanResmi: sayi(h1.huni2, 'say'),
    },
    kalite: {
      kaydirma: [25, 50, 75, 100].map((n) => ({ n, say: kaydirmaToplam.get(String(n)) || 0 })),
      hatalar: ilk(sirala(B('hata')).map((r) => ({ mesaj: r.k1, dosya: r.k2, say: r.say, tekil: r.tekil })), 15),
      yok404: ilk(sirala(B('yok404')).map((r) => ({ p: r.k1, say: r.say })), 15),
      lcpMs: agirlikliOrtalama(rows.filter((r) => r.boyut === 'lcp')),
      ttfbMs: agirlikliOrtalama(rows.filter((r) => r.boyut === 'ttfb')),
    },
  };
}

// Canlı göstergeler: son 5 dakikadaki tekil ziyaretçi ve son 50 olay (anonim).
export async function canli(env, simdiMs = Date.now()) {
  const sn = Math.floor(simdiMs / 1000);
  const [a, akis] = await env.DB.batch([
    env.DB.prepare('SELECT COUNT(DISTINCT zv) AS n FROM olaylar WHERE ts >= ?').bind(sn - 300),
    env.DB.prepare('SELECT ts, t, p, sy, v, k, a, h, x, n, n2, sehir, cihaz, kaynak FROM olaylar ORDER BY id DESC LIMIT 50'),
  ]);
  return { aktif: Number(a.results?.[0]?.n || 0), akis: akis.results || [], sn };
}
