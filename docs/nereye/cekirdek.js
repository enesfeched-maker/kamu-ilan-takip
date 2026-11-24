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

  /* İlan metninden en düşük KPSS puan şartı: "60 (altmış) ve üzeri", "en az 55 puan", "70 ve üzerinde".
     Birden çok kadro varsa en düşük eşik (adayın en az birine yetmesi yeter). %70 gibi yüzde ifadeleri sayılmaz. */
  const PUAN_RX = [
    /(^|[^%\d.,])(\d{2}(?:[.,]\d+)?)\s*(?:\([^)]{0,30}\)\s*)?(?:ve|veya)\s+(?:üzeri|üstü|üzerinde|üzerindeki|daha fazla)/gi,
    /(en\s+az\s+)(\d{2}(?:[.,]\d+)?)\s*(?:\([^)]{0,30}\)\s*)?puan/gi,
  ];   // site JS'i ES2017: geriye bakan (lookbehind) düzenli ifade kullanılmaz; sayı 2. grupta
  function puanSarti(r) {
    const t = ilanMetni(r);
    let en = null;
    for (const rx of PUAN_RX) {
      rx.lastIndex = 0;
      let m;
      while ((m = rx.exec(t))) {
        const cevre = t.slice(Math.max(0, m.index - 160), m.index + 80);
        if (!/kpss|puan/i.test(cevre) || /yds|yökdil|yabancı dil|ales|lys|tus|dus/i.test(cevre)) continue;
        const v = Number(m[2].replace(',', '.'));
        if (v >= 40 && v <= 100 && (en === null || v < en)) en = v;
      }
    }
    return en;
  }

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
    return {
      adet: adet && adet > 0 && adet < 100000 ? adet : null,
      puan: puan && puan >= 1 && puan <= 100 ? puan : null,
      tur: yz && typeof yz.puan_turu === 'string' && /^P\d{1,3}$/.test(yz.puan_turu) ? yz.puan_turu : null,
      ogrenim: (yz && typeof yz.ogrenim === 'string' && yz.ogrenim in RUTBE && yz.ogrenim) || (kd && typeof kd.ogrenim === 'string' && kd.ogrenim in RUTBE && kd.ogrenim) || null,
    };
  }

  /* Tek kayıt → {grup, kadrolar:[{ad, grup, adet, puan, neden}], neden}. bolumAdi boşsa (genel lise) "Lise" aranır. */
  function degerlendir(rec, bolumAdi, duzey, puan) {
    const kpsssiz = rec.kpss === 'kpsssiz';
    const ilanPuan = kpsssiz ? null : puanSarti(rec);
    const kdMetin = (Array.isArray(rec.kadro_detay) ? rec.kadro_detay : []).map((k) => (k && Array.isArray(k.maddeler) ? k.maddeler.join(' ') : '')).join(' ');
    const kurumIci = KURUM_ICI.test(E.fold([rec.baslik, rec.ilan_turu].join(' '))) || KURUM_ICI_SART.test(E.fold(ilanMetni(rec) + ' ' + kdMetin));
    if (kurumIci) return { grup: 'degil', kadrolar: [], neden: 'Kurum içi ilan', kpsssiz };
    const kb = E.kadroBazli(rec, [bolumAdi || 'Lise'], duzey);
    const sonuc = [];
    if (kb.genel) {
      // kadrolara ayrılmamış ilan: düzey ilan düzeyinde denetlenir
      const sev = (Array.isArray(rec.ogrenim) && rec.ogrenim.length ? rec.ogrenim : Array.isArray(rec.belge_ogrenim) ? rec.belge_ogrenim : []).filter((x) => x in RUTBE);
      const k = kb.kadrolar[0];
      let grup = k ? DURUM_GRUP[k.durum] || 'okunamadi' : 'okunamadi';
      let neden = k && k.neden ? k.neden : '';
      if (sev.length && !sev.includes(duzey)) {
        if (grup !== 'hemen' || k.durum !== 'uygun' || sev.every((x) => RUTBE[x] > RUTBE[duzey])) grup = 'degil';
        else { grup = 'kontrol'; neden = 'İlan ' + sev.map((x) => (DUZEY[x] ? DUZEY[x].ad.toLocaleLowerCase('tr') : x)).join('/') + ' mezunu arıyor; senin düzeyini kabul ediyor mu bak'; }
      }
      if (grup === 'kontrol' && k && k.durum === 'kontrol' && !neden) neden = 'Bölümün şartta tam adıyla geçmiyor';
      if (k && k.durum === 'kontrol' && k.kanit) neden = (bolumAdi ? 'Bölümün şartta tam adıyla geçmiyor' : 'Lise mezunlarını kabul edip etmediğine bak') + ': “' + kisalt(k.kanit, 140) + '”';
      sonuc.push({ ad: '', grup, adet: null, puan: ilanPuan, tur: null, neden });
    } else {
      for (const k of kb.kadrolar) {
        const b = kadroBilgisi(rec, k.ad);
        let grup = DURUM_GRUP[k.durum] || 'okunamadi';
        let neden = '';
        if (b.ogrenim && b.ogrenim !== duzey && RUTBE[b.ogrenim] !== RUTBE[duzey]) grup = 'degil';   // okunmuş kadro düzeyi tutmuyor
        // genel lise: "lise" sözcüğü şartta düzey olarak geçiyor; okunmuş kadro düzeyi lise ise bu bir bölüm belirsizliği değildir
        if (grup === 'kontrol' && !bolumAdi && b.ogrenim === 'ortaogretim') grup = 'hemen';
        if (grup === 'kontrol') neden = (bolumAdi ? 'Bölümün şartta tam adıyla geçmiyor' : 'Lise mezunlarını kabul edip etmediğine bak') + (k.kanit ? ': “' + kisalt(k.kanit, 140) + '”' : '');
        if (grup === 'okunamadi') neden = 'Bu kadronun bölüm şartı okunamadı';
        const esik = kpsssiz ? null : (b.puan !== null ? b.puan : ilanPuan);
        if ((grup === 'hemen' || grup === 'kontrol') && b.tur && puan !== null && b.tur !== DUZEY[duzey].tur) {
          grup = 'kontrol'; neden = 'Bu kadro ' + b.tur + ' puanı istiyor; girdiğin puan ' + DUZEY[duzey].tur;
        } else if ((grup === 'hemen' || grup === 'kontrol') && esik !== null && puan !== null && puan < esik) {
          grup = 'yetmiyor'; neden = 'En az ' + puanYaz(esik) + ' puan istiyor; seninki ' + puanYaz(puan);
        }
        sonuc.push({ ad: k.ad, grup, adet: b.adet, puan: esik, tur: b.tur, neden });
      }
    }
    // yalnız ilan düzeyinde puan şartı varsa genel kadroda da puan denetlenir
    for (const s of sonuc) {
      if (!s.ad && (s.grup === 'hemen' || s.grup === 'kontrol') && s.puan !== null && puan !== null && puan < s.puan) {
        s.grup = 'yetmiyor'; s.neden = 'En az ' + puanYaz(s.puan) + ' puan istiyor; seninki ' + puanYaz(puan);
      }
    }
    const gorunen = sonuc.filter((s) => s.grup !== 'degil');
    const grup = gorunen.reduce((g, s) => (GRUP_SIRA[s.grup] < GRUP_SIRA[g] ? s.grup : g), 'degil');
    return { grup, kadrolar: gorunen.filter((s) => s.grup === grup), neden: (gorunen.find((s) => s.grup === grup) || {}).neden || '', kpsssiz };
  }

  /* Kopyalar (aynı ilanın başka kaynaktaki kayıtları) tek satır: en iyi sonuç, birincil kaydın bağlantısıyla. */
  function ilanlariDegerlendir(kayitlar, kopya, bolumAdi, duzey, puan) {
    const gruplar = new Map();
    for (const rec of kayitlar) {
      const k = anahtar(rec), bas = (kopya && kopya.get(k)) || k;
      const d = degerlendir(rec, bolumAdi, duzey, puan);
      const g = gruplar.get(bas);
      if (!g) gruplar.set(bas, Object.assign({ rec, anahtar: bas, uyeler: [rec] }, d));
      else {
        g.uyeler.push(rec);
        if (GRUP_SIRA[d.grup] < GRUP_SIRA[g.grup]) { const r = g.rec; Object.assign(g, d); g.rec = r; }
        if (k === bas) g.rec = rec;
      }
    }
    return [...gruplar.values()];
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
    const satir = (s) => { const out = []; let x = s; while (x.length > 74) { out.push(x.slice(0, 74)); x = ' ' + x.slice(74); } out.push(x); return out.join('\r\n'); };
    const saat = rec.son_zaman ? String(rec.son_zaman).slice(11, 16) : '';
    return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//KPSS Tercihi//Nereye//TR', 'CALSCALE:GREGORIAN', 'BEGIN:VEVENT',
      'UID:' + kac(anahtar(rec)) + '@kpsstercihi.com', 'DTSTAMP:' + st, 'DTSTART;VALUE=DATE:' + g, 'DTEND;VALUE=DATE:' + ertesi,
      satir('SUMMARY:' + kac('Son gün: ' + (rec.kurum || 'Kamu ilanı'))),
      satir('DESCRIPTION:' + kac((rec.baslik || '') + (saat ? ' — başvuru ' + saat + "'de kapanır" : '') + ' — ' + siteUrl)),
      satir('URL:' + siteUrl),
      'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + kac('Yarın son gün: ' + (rec.kurum || '')), 'TRIGGER:-PT15H', 'END:VALARM',
      'END:VEVENT', 'END:VCALENDAR', ''].join('\r\n');
  }

  return { DUZEY, GRUP_SIRA, anahtar, puanSarti, basvuruSekli, kadroBilgisi, degerlendir, ilanlariDegerlendir, bolumKodlari, bolumUygun, merkezi, icsMetni, puanYaz };
});
