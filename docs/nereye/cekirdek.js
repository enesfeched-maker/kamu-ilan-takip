/* "Puanınla nereye başvurabilirsin?" karar çekirdeği (DOM yok; node ile test edilir: bot/nereye_test.cjs).
 *
 * Bir ilan için karar KADRO KADRO verilir (bolum/esles.js kadroBazli: okunmuş/elle düzeltilmiş yz_kadrolar ve
 * kadro_detay şartları). Gruplar (iyiden zayıfa):
 *   hemen     — bölümün şartta açıkça geçiyor ya da bölüm şartı yok; düzeyin tutuyor; puanın (yazıyorsa) yetiyor
 *   kontrol   — uygun olabilirsin ama bir şart (benzer bölüm adı, farklı puan türü) ilandan okunmalı
 *   yetmiyor  — bölümün uyuyor ama kadronun en düşük puanı seninkinden yüksek
 *   okunamadi — şart metni siteye düzgün alınamadı; seni kapsıyor olabilir
 *   degil     — bölümün ya da düzeyin bu ilanda yok (gösterilmez)
 * Emin olunmayan hiçbir kadro "hemen" grubuna konmaz. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.NereyeCekirdek = factory(root.BolumEsles);
})(typeof self !== 'undefined' ? self : this, function (E) {
  'use strict';

  const DUZEY = {
    ortaogretim: { ad: 'Lise', tur: 'P94' },
    onlisans: { ad: 'Önlisans', tur: 'P93' },
    lisans: { ad: 'Lisans', tur: 'P3' },
  };
  const RUTBE = { ilkogretim: 0, ortaogretim: 1, onlisans: 2, lisans: 3, yuksek_lisans: 4, doktora: 5 };
  const GRUP_SIRA = { hemen: 0, kontrol: 1, yetmiyor: 2, okunamadi: 3, degil: 4 };
  const DURUM_GRUP = { uygun: 'hemen', serbest: 'hemen', kontrol: 'kontrol', bak: 'okunamadi', degil: 'degil', haric: 'degil' };
  const KURUM_ICI = /gorevde yukselme|unvan degisikligi|kurum ici|kurum personeli icin|meslek personeli icin|yeterlik sinavi|staj|yurt ?disi (?:yuksek lisans|lisansustu|egitim)/;
  // şartında "kurumda beş yılını doldurmuş olmak" gibi çalışan personel şartı olan ilan dışarıdan başvuruya açık değildir
  const KURUM_ICI_SART = /kurumda (?:\S+ ){0,4}(?:yilini|yil) (?:doldurmus|tamamlamis)|kurum(?:umuz)? kadrolarinda (?:halen )?gorev yap|halen kurumumuzda/;

  const puanYaz = (p) => String(Math.round(Number(p) * 100) / 100).replace('.', ',');
  const kisalt = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, '') + '…'; };

  function anahtar(r) {
    const m = /[?&]i=([^&#]+)/.exec(String(r.link || ''));
    return m ? decodeURIComponent(m[1]) : r.id;
  }

  function ilanMetni(r) {
    const p = [r.ozet, r.duyuru_cumlesi];
    if (Array.isArray(r.sartlar)) for (const s of r.sartlar) if (s && s.metin) p.push(s.metin);
    for (const a of ['yz_ortak', 'basvuru_kisa_sartlar']) if (Array.isArray(r[a])) p.push(...r[a]);
    if (Array.isArray(r.kadro_ortak)) for (const b of r.kadro_ortak) if (Array.isArray(b) && Array.isArray(b[1])) p.push(...b[1]);
    return p.filter((x) => typeof x === 'string').join(' \n ');
  }

  /* ---------- KPSS puan şartı ve puan türü ----------
     "60 (altmış) ve üzeri", "en az 55 puan", "70 ve üzerinde". Yüzde ("%70"), YDS/ALES, sözlü/yazılı sınav ve "100 tam puan
     üzerinden" puanları sayılmaz. Her eşik, aynı cümlede kendinden önce yazan puan türleriyle (P3, KPSSP93…) birlikte tutulur. */
  const PUAN_RX = [
    /(^|[^%\d.,])(\d{2}(?:[.,]\d+)?)\s*(?:\([^)]{0,30}\)\s*)?(?:ve|veya)\s+(?:üzeri|üstü|üzerinde|üzerindeki|daha fazla)/gi,
    /(en\s+az\s+)(\d{2}(?:[.,]\d+)?)\s*(?:\([^)]{0,30}\)\s*)?puan/gi,
  ];   // site JS'i ES2017: geriye bakan (lookbehind) düzenli ifade kullanılmaz; sayı 2. grupta
  const PUAN_DISI = /sözlü|mülakat|yazılı sınav|uygulamalı sınav|tam puan|üzerinden|yds|yökdil|yabancı dil|ales|lys|tus|dus|kpds|toefl|ielts|diploma notu|mezuniyet not/i;
  const TUR_RX = /KPSS\s*-?\s*P\s?(\d{1,3})\b|\bP\s?(\d{1,3})\b/gi;
  function turler(metin) {
    const s = new Set(); let m; TUR_RX.lastIndex = 0;
    while ((m = TUR_RX.exec(String(metin || '')))) s.add('P' + (m[1] || m[2]));
    return [...s];
  }
  function cumleler(metin) { return String(metin || '').replace(/([.;!?])\s+/g, '$1\n').split('\n'); }
  /* metin → [{v, turler}] */
  function puanSartlari(metin) {
    const out = [];
    for (const c of cumleler(metin)) {
      if (!/kpss|puan|P\s?\d/i.test(c)) continue;
      for (const rx of PUAN_RX) {
        rx.lastIndex = 0;
        let m;
        while ((m = rx.exec(c))) {
          const bas = m.index + m[1].length;
          if (PUAN_DISI.test(c.slice(Math.max(0, bas - 60), bas + 30))) continue;
          const v = Number(m[2].replace(',', '.'));
          if (!(v >= 40 && v <= 100)) continue;
          out.push({ v, turler: turler(c.slice(Math.max(0, bas - 120), bas)) });
        }
      }
    }
    return out;
  }
  /* Adayın puan türüne uyan eşikler: {esik, karisik}. Türü yazmayan eşik herkese uyar. */
  function esikBul(metin, tur) {
    const l = puanSartlari(metin).filter((s) => !s.turler.length || s.turler.includes(tur));
    if (!l.length) return { esik: null, karisik: false };
    const d = [...new Set(l.map((s) => s.v))];
    return { esik: Math.min(...d), karisik: d.length > 1 };
  }
  /* Eski arayüz: ilan metnindeki en düşük eşik (türe bakmadan). */
  function puanSarti(r) { const l = puanSartlari(ilanMetni(r)); return l.length ? Math.min(...l.map((s) => s.v)) : null; }

  /* Başvuru şekli: olumsuz cümleler ("posta ile yapılan başvurular kabul edilmeyecektir") atlanır. */
  function basvuruSekli(r) {
    const t = [r.basvuru_notu, r.ozet, r.duyuru_cumlesi].concat(Array.isArray(r.yz_ortak) ? r.yz_ortak : []).filter((x) => typeof x === 'string').join(' ');
    const c = t.replace(/([.!?])\s+/g, '$1\n').split('\n').filter((x) => !/edilmeye|edilmez|yapılmayan|alınmayacak|kabul edilmeyecek|geçersiz/i.test(x)).join(' ');
    const link = String(r.link || '');
    if (/kariyer\s*kap[ıi]s[ıi]|kariyerkapisi/i.test(c) || /^https?:\/\/(www\.)?kariyerkapisi\.gov\.tr/.test(link))
      return { ad: 'Kariyer Kapısı üzerinden, e-Devlet şifrenle', link: /^https?:\/\/(www\.)?kariyerkapisi\.gov\.tr/.test(link) ? link : 'https://kariyerkapisi.gov.tr/isealim' };
    if (/e-?devlet|turkiye\.gov\.tr/i.test(c)) return { ad: 'e-Devlet üzerinden', link: 'https://www.turkiye.gov.tr' };
    if (/şahsen|elden/i.test(c)) return { ad: 'Kuruma şahsen giderek' };
    if (/iadeli taahhütlü|posta yoluyla|posta ile|kargo/i.test(c)) return { ad: 'Posta ile' };
    if (/e-?posta|@[a-z0-9-]+\.[a-z.]+/i.test(c)) return { ad: 'E-posta ile' };
    return { ad: 'Başvuru şekli resmî ilanda yazıyor' };
  }

  /* Okunmuş kadro bilgisi (adet, puan, öğrenim) kadro adıyla bulunur. */
  function kadroBilgisi(rec, ad) {
    const f = E.fold(ad);
    const yz = (Array.isArray(rec.yz_kadrolar) ? rec.yz_kadrolar : []).find((k) => k && E.fold(k.unvan) === f);
    const kd = (Array.isArray(rec.kadro_detay) ? rec.kadro_detay : []).find((k) => k && E.fold(k.unvan) === f);
    const sayi = (x) => (typeof x === 'number' && isFinite(x) ? x : typeof x === 'string' && /^\d+([.,]\d+)?$/.test(x.trim()) ? Number(x.replace(',', '.')) : null);
    const adet = sayi(yz && yz.adet) || sayi(kd && kd.adet);
    const puan = sayi(yz && yz.en_dusuk_puan);
    const metin = [ad].concat(yz && Array.isArray(yz.kosullar) ? yz.kosullar : [], kd && Array.isArray(kd.maddeler) ? kd.maddeler : [])
      .filter((x) => typeof x === 'string').join(' \n ');
    return {
      adet: adet && adet > 0 && adet < 100000 ? adet : null,
      puan: puan && puan >= 1 && puan <= 100 ? puan : null,
      // "P3", "KPSSP3", "P14,P15,P16", "P14P15P16" → [P3] / [P14, P15, P16]
      turler: yz && typeof yz.puan_turu === 'string' ? turler(yz.puan_turu.toUpperCase().replace(/KPSS/g, ' KPSS').replace(/P(\d+)(?=P)/g, 'P$1 ')) : [],
      ogrenim: (yz && typeof yz.ogrenim === 'string' && yz.ogrenim in RUTBE && yz.ogrenim) || (kd && typeof kd.ogrenim === 'string' && kd.ogrenim in RUTBE && kd.ogrenim) || null,
      metin,
    };
  }

  const ALAN_SARTI = /\b(?:alan[ıi]?(?:n|ndan|nda)?|alanlar[ıi]?(?:n|ndan)?|dal[ıi]?(?:n|ndan)?|dallar[ıi]?(?:n|ndan)?|bölüm(?:ü|ünden|lerinden|leri)?|program(?:ı|ından|larından)?)\b/i;
  function cinsiyetNotu(metin) {
    const e = /\berkek\b/i.test(metin), k = /\bkad[ıi]n\b/i.test(metin);
    return e && !k ? 'Yalnız erkek adaylar' : k && !e ? 'Yalnız kadın adaylar' : '';
  }
  const duzeyAdi = (l) => l.map((x) => (DUZEY[x] ? DUZEY[x].ad.toLocaleLowerCase('tr') : x === 'yuksek_lisans' ? 'yüksek lisans' : x)).join('/');

  /* Tek kayıt → {grup, kadrolar:[{ad, grup, adet, puan, neden}], neden}. bolumAdi boşsa (genel lise) "Lise" aranır. */
  /* Bir kadronun (ya da kadrolara ayrılmamış ilanın) kararı. Sıra: bölüm → düzey → puan türü → puan. Her adım yalnız
     kötüleştirir; emin olunmayan durum "kontrol" olur. */
  function kadroKarari(o) {
    const { durum, kanit, metin, seviyeler, b, rec, bolumAdi, duzey, puan, ilanMetin } = o;
    const tur = DUZEY[duzey].tur, kpsssiz = rec.kpss === 'kpsssiz';
    let grup = DURUM_GRUP[durum] || 'okunamadi', neden = '';
    // 1) bölüm
    if (!bolumAdi && (durum === 'uygun' || durum === 'kontrol')) {
      // genel lise: "lise" sözcüğü bir listede geçti; belirli alan/dal isteniyorsa kontrol, yoksa düzey şartı sayılır
      grup = ALAN_SARTI.test(metin) ? 'kontrol' : 'hemen';
      if (grup === 'kontrol') neden = 'Belirli lise alanları isteniyor olabilir' + (kanit ? ': “' + kisalt(kanit, 140) + '”' : '');
    } else if (grup === 'kontrol') neden = 'Bölümün şartta tam adıyla geçmiyor' + (kanit ? ': “' + kisalt(kanit, 140) + '”' : '');
    if (grup === 'okunamadi') neden = 'Bölüm şartı okunamadı';
    if (grup === 'degil') return { grup, neden };
    // 2) düzey: okunmuş kadro düzeyi > kadro metni > ilan düzeyi > ilan metni; hiç bilinmiyorsa kontrol
    const recSev = (Array.isArray(rec.ogrenim) && rec.ogrenim.length ? rec.ogrenim : Array.isArray(rec.belge_ogrenim) ? rec.belge_ogrenim : []).filter((x) => x in RUTBE);
    const sev = b && b.ogrenim ? [b.ogrenim] : seviyeler && seviyeler.length ? seviyeler : recSev.length ? recSev : E.seviyeBul(ilanMetin);
    if (sev.length && !sev.includes(duzey)) return { grup: 'degil', neden: 'İlan ' + duzeyAdi(sev) + ' mezunu arıyor' };
    // bölüm adıyla eşleşen kadroda düzey bölümden bellidir (bölüm listesi adayın düzeyinden gelir); serbest/genel şartta değil
    if (!sev.length && grup === 'hemen' && (durum !== 'uygun' || !bolumAdi)) { grup = 'kontrol'; neden = 'İlanda öğrenim düzeyi okunamadı; ' + DUZEY[duzey].ad.toLocaleLowerCase('tr') + ' mezunu kabul ediliyor mu bak'; }
    if (kpsssiz) return { grup, neden, esik: null };
    // 3) puan türü: okunmuş kadro türü > kadro metni > ilan metni
    const kt = b && b.turler.length ? b.turler : turler(metin).length ? turler(metin) : turler(ilanMetin);
    const kesinTur = !!(b && b.turler.length) || turler(metin).length > 0;
    if (kt.length && !kt.includes(tur) && (kesinTur || !/\bP\s?(3|93|94)\b/i.test(ilanMetin))) {
      return { grup: grup === 'okunamadi' ? 'okunamadi' : 'kontrol', neden: 'Bu kadro ' + kt.slice(0, 3).join('/') + (kt.length > 3 ? '…' : '') + ' puanı istiyor; senin puan türün ' + tur, esik: null };
    }
    if (!kt.length && /\bA grubu\b|ilgili puan türü/i.test(metin + ' ' + ilanMetin) && grup === 'hemen') { grup = 'kontrol'; neden = 'Puan türünü ilandan kontrol et'; }
    // 4) puan eşiği: okunmuş değer > kadro metni > ilan metni (ilan geneli yalnız tek eşik varsa)
    let esik = b && b.puan !== null ? b.puan : null, karisik = false;
    if (esik === null) { const e = esikBul(metin, tur); esik = e.esik; karisik = e.karisik; }
    if (esik === null) { const e = esikBul(ilanMetin, tur); esik = e.esik; karisik = e.karisik; }
    if (puan === null) {
      // puanı olmayan aday: KPSS şartı yoksa bile emin değiliz (ilan "KPSS şartı yok" demiyor)
      if (grup === 'hemen') { grup = 'kontrol'; neden = 'KPSS puanı gerekiyor' + (esik !== null && !karisik ? ' (en az ' + puanYaz(esik) + ')' : ''); }
      return { grup, neden, esik };
    }
    if (karisik && grup === 'hemen') return { grup: 'kontrol', neden: 'Kadrolara göre farklı puan şartı var; bu kadronun puanını ilandan kontrol et', esik: null };
    if (esik !== null && puan < esik && (grup === 'hemen' || grup === 'kontrol')) return { grup: 'yetmiyor', neden: 'En az ' + puanYaz(esik) + ' puan istiyor; seninki ' + puanYaz(puan), esik };
    return { grup, neden, esik };
  }

  function degerlendir(rec, bolumAdi, duzey, puan) {
    const kpsssiz = rec.kpss === 'kpsssiz';
    const ilanMetin = ilanMetni(rec);
    const kdMetin = (Array.isArray(rec.kadro_detay) ? rec.kadro_detay : []).map((k) => (k && Array.isArray(k.maddeler) ? k.maddeler.join(' ') : '')).join(' ');
    const kurumIci = KURUM_ICI.test(E.fold([rec.baslik, rec.ilan_turu].join(' '))) || KURUM_ICI_SART.test(E.fold(ilanMetin + ' ' + kdMetin));
    if (kurumIci) return { grup: 'degil', kadrolar: [], neden: 'Kurum içi ilan', kpsssiz, kurumIci: true };
    const kb = E.kadroBazli(rec, [bolumAdi || 'Lise'], duzey);
    const sonuc = [];
    if (kb.genel) {
      const k = kb.kadrolar[0];
      const r = kadroKarari({ durum: k ? k.durum : 'bak', kanit: k && k.kanit, metin: ilanMetin + ' ' + kdMetin, seviyeler: [], b: null, rec, bolumAdi, duzey, puan, ilanMetin });
      sonuc.push({ ad: '', grup: r.grup, adet: null, puan: r.esik === undefined ? null : r.esik, neden: r.neden, not: cinsiyetNotu(rec.baslik + ' ' + kdMetin) });
    } else {
      for (const k of kb.kadrolar) {
        const b = kadroBilgisi(rec, k.ad);
        const r = kadroKarari({ durum: k.durum, kanit: k.kanit, metin: b.metin, seviyeler: k.seviyeler, b, rec, bolumAdi, duzey, puan, ilanMetin });
        sonuc.push({ ad: k.ad, grup: r.grup, adet: b.adet, puan: r.esik === undefined ? null : r.esik, neden: r.neden, not: cinsiyetNotu(b.metin) });
      }
    }
    const gorunen = sonuc.filter((s) => s.grup !== 'degil');
    const grup = gorunen.reduce((g, s) => (GRUP_SIRA[s.grup] < GRUP_SIRA[g] ? s.grup : g), 'degil');
    return { grup, kadrolar: gorunen.filter((s) => s.grup === grup), neden: (gorunen.find((s) => s.grup === grup) || {}).neden || '', kpsssiz, kurumIci: false };
  }

  /* Kopyalar (aynı ilanın başka kaynaktaki kayıtları) tek satır: en iyi sonuç, birincil kaydın bağlantısıyla.
     Bir üye kurum içi çıkarsa grup bütünüyle düşer; birincil kayıt listede yoksa (kapanmış/iptal) kopya kendi adresiyle durur. */
  function ilanlariDegerlendir(kayitlar, kopya, bolumAdi, duzey, puan) {
    const varolan = new Set(kayitlar.map(anahtar));
    const gruplar = new Map();
    for (const rec of kayitlar) {
      const k = anahtar(rec), b0 = kopya && kopya.get(k), bas = b0 && varolan.has(b0) ? b0 : k;
      const d = degerlendir(rec, bolumAdi, duzey, puan);
      const g = gruplar.get(bas);
      if (!g) gruplar.set(bas, Object.assign({ rec, anahtar: bas, uyeler: [rec], veto: d.kurumIci }, d));
      else {
        g.uyeler.push(rec);
        g.veto = g.veto || d.kurumIci;
        if (GRUP_SIRA[d.grup] < GRUP_SIRA[g.grup]) { const r = g.rec; Object.assign(g, d); g.rec = r; }
        if (k === bas) g.rec = rec;
      }
    }
    return [...gruplar.values()].map((g) => (g.veto ? Object.assign(g, { grup: 'degil', kadrolar: [] }) : g));
  }

  /* ---------- merkezi atama (taban puanları) ---------- */
  function bolumKodlari(v, ad) {
    const f = E.fold(ad);
    let kod = Object.entries(v.bolumler).filter(([, a]) => E.fold(a) === f).map(([k]) => k);
    if (!kod.length && f.length >= 3) {
      const adlar = [...new Set(Object.values(v.bolumler).filter((a) => E.fold(a).includes(f)).map(E.fold))];
      if (adlar.length === 1) kod = Object.entries(v.bolumler).filter(([, a]) => E.fold(a) === adlar[0]).map(([k]) => k);
    }
    return kod;
  }
  /* puanlar.js bolumDurumu ile aynı kural. kodlar boşsa (genel lise): nitelikte "her bölüm" (*) varsa uygun. */
  function bolumUygun(k, v, kodlar) {
    if (!Array.isArray(k.nit) || !k.nit.length) return false;
    const d = v.nitelikler[k.donem] || {};
    if (!kodlar.length) return k.nit.some((n) => (d[n] || []).includes('*'));
    const kabul = new Set();
    for (const n of k.nit) {
      const l = d[n] || [];
      for (const s of kodlar) if (l.includes('*') || l.some((e) => e === s || (e.endsWith('-*') && s.startsWith(e.slice(0, -1))))) kabul.add(s);
    }
    return kabul.size === kodlar.length;
  }
  function merkezi(p, b, bolumAdi, puan, donemSayi, sinir) {
    if (!p || !p.donemler || !b || !b.bolumler) return null;
    const son = Object.keys(p.donemler).sort().slice(-donemSayi);
    const donem = son.length > 1 ? son[0] + ' – ' + son[son.length - 1] : son[0];
    let kodlar = [];
    if (bolumAdi) { kodlar = bolumKodlari(b, bolumAdi); if (!kodlar.length) return { donem, bolumYok: true }; }
    const enYeni = new Map();   // aynı kurum/il/unvan/nitelik birden çok dönemde açıldıysa en yeni dönemi sayılır
    for (const d of son) for (const k0 of p.donemler[d] || []) {
      if (k0.min == null) continue;
      const k = Object.assign({ donem: d }, k0);
      if (bolumUygun(k, b, kodlar)) enYeni.set([k.kurum, k.il, k.teskilat, k.unvan, (k.nit || []).join(',')].join('|'), k);
    }
    const uygun = [], sinirda = [], yakin = [];
    for (const k of enYeni.values()) {
      if (puan >= k.min) uygun.push(k);
      else { yakin.push(k); if (puan >= k.min - sinir) sinirda.push(k); }
    }
    uygun.sort((x, y) => y.donem.localeCompare(x.donem) || y.kontenjan - x.kontenjan || y.min - x.min);
    yakin.sort((x, y) => x.min - y.min);
    return { donem, uygun, sinirda, yakin: yakin.slice(0, 3), kontenjan: uygun.reduce((n, k) => n + (k.kontenjan || 0), 0) };
  }

  /* ---------- takvim (.ics): son günden bir gün önce ve sabah hatırlatır ---------- */
  function icsMetni(rec, siteUrl, simdi) {
    const g = String(rec.son_tarih || '').replace(/-/g, '');
    if (!/^\d{8}$/.test(g)) return '';
    const kac = (s) => String(s || '').replace(/[\\;,]/g, (c) => '\\' + c).replace(/\r?\n/g, ' ');
    const ertesi = new Date(Date.UTC(+g.slice(0, 4), +g.slice(4, 6) - 1, +g.slice(6, 8) + 1)).toISOString().slice(0, 10).replace(/-/g, '');
    const st = (simdi || new Date()).toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    // RFC 5545: satır en çok 75 OKTET; Türkçe harf UTF-8'de 2 bayt olduğundan bayta göre katlanır
    const bayt = (c) => (c.charCodeAt(0) < 0x80 ? 1 : c.charCodeAt(0) < 0x800 ? 2 : 3);
    const satir = (s) => {
      const out = []; let cur = '', n = 0;
      for (const c of s) { const b = bayt(c); if (n + b > 74) { out.push(cur); cur = ' '; n = 1; } cur += c; n += b; }
      out.push(cur); return out.join('\r\n');
    };
    const saat = rec.son_zaman ? String(rec.son_zaman).slice(11, 16) : '';
    return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//KPSS Tercihi//Nereye//TR', 'CALSCALE:GREGORIAN', 'BEGIN:VEVENT',
      satir('UID:' + kac(anahtar(rec)) + '@kpsstercihi.com'), 'DTSTAMP:' + st, 'DTSTART;VALUE=DATE:' + g, 'DTEND;VALUE=DATE:' + ertesi,
      satir('SUMMARY:' + kac('Son gün: ' + (rec.kurum || 'Kamu ilanı'))),
      satir('DESCRIPTION:' + kac((rec.baslik || '') + (saat ? ' — başvuru ' + saat + "'de kapanır" : '') + ' — ' + siteUrl)),
      satir('URL:' + siteUrl),
      'BEGIN:VALARM', 'ACTION:DISPLAY', satir('DESCRIPTION:' + kac('Yarın son gün: ' + (rec.kurum || ''))), 'TRIGGER:-PT15H', 'END:VALARM',
      'END:VEVENT', 'END:VCALENDAR', ''].join('\r\n');
  }

  return { DUZEY, GRUP_SIRA, anahtar, puanSarti, puanSartlari, esikBul, turler, basvuruSekli, kadroBilgisi, degerlendir, ilanlariDegerlendir, bolumKodlari, bolumUygun, merkezi, icsMetni, puanYaz };
});
