/* "Puanınla nereye başvurabilirsin?" sayfası: form, sonuç çizimi, takvim, kaydetme ve paylaşım kartı.
 * Kararlar cekirdek.js'tedir (NereyeCekirdek); bu dosya yalnız veri yükler ve gösterir. */
(function () {
  'use strict';
  const E = window.BolumEsles, C = window.NereyeCekirdek;
  const $ = (id) => document.getElementById(id);
  const AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  const FORM = {
    ortaogretim: { bolumEt: 'Lisedeki alanın ne?', ornek: 'ör. Muhasebe ve Finansman' },
    onlisans: { bolumEt: 'Bölümün ne?', ornek: 'ör. Tıbbi Dokümantasyon ve Sekreterlik' },
    lisans: { bolumEt: 'Bölümün ne?', ornek: 'ör. Hemşirelik' },
  };
  const SINIR = 2;          // merkezi atamada "sınırda" sayılan puan farkı
  const MERKEZI_ILK = 8;
  const DONEM_SAYI = 4;     // merkezi atamada bakılan son tercih dönemi sayısı
  const SITE = 'https://kpsstercihi.com/';
  // Bildirim (Web Push): bildirim botu Worker'ı. VAPID_ACIK boşsa yalnız bu cihazda kayıt yapılır (bildirim kapalı).
  const API = 'https://bildirim.kpsstercihi.com';
  const VAPID_ACIK = 'BI_V6nOUnzoI_Oa1kSsoXAxlVibe1gOzakkRibXwAs_GZv_rbKthDyn2666il66qq4TgKJpd6ElhCcngEJrs4J4';
  const KAYIT = 'kit-nereye-kayit', BILDIRIM = 'kit-nereye-bildirim';
  // sabit simgeler (yalnız bu dosyadaki sabit metin; kullanıcı verisi asla HTML olarak eklenmez)
  const OK_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
  const ZIL_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>';
  const TIK_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>';
  const TAKVIM_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>';
  const YILDIZ_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>';

  const h = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const A = (t, p) => { try { if (window.kpssA) window.kpssA(t, p); } catch (e) { /* analiz yok */ } };
  const oku = (k) => { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } };
  const yaz = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* depolama kapalı */ } };
  const bugun = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/Istanbul' });
  const getJSON = (url) => fetch(url, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });
  const puanYaz = C ? C.puanYaz : String;
  const buyukHarf = (s) => String(s).toLocaleLowerCase('tr').replace(/(^|[\s(\/-])([a-zçğıöşü])/g, (m, a, b) => a + b.toLocaleUpperCase('tr'));
  const ilYaz = (x) => (x ? x.charAt(0) + x.slice(1).toLocaleLowerCase('tr') : '');

  /* ---------- ilan yardımcıları ---------- */
  function sonAn(r) {
    if (r.son_zaman) { const t = Date.parse(r.son_zaman); if (!isNaN(t)) return t; }
    if (r.son_tarih) { const t = Date.parse(r.son_tarih + 'T23:59:59+03:00'); if (!isNaN(t)) return t; }
    return NaN;
  }
  const kapali = (r) => { const t = sonAn(r); return !isNaN(t) && t <= Date.now(); };
  const baslamadi = (r) => { const t = r.baslangic_zaman ? Date.parse(r.baslangic_zaman) : NaN; return !isNaN(t) && t > Date.now(); };
  function tarihYaz(s) { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? Number(m[3]) + ' ' + AY[Number(m[2]) - 1] : ''; }
  function kalanGun(r) {
    if (!r.son_tarih) return null;
    const g = Math.round((Date.parse(r.son_tarih + 'T00:00:00Z') - Date.parse(bugun() + 'T00:00:00Z')) / 864e5);
    return isNaN(g) ? null : g;
  }
  function kisaBaslik(r) {
    const k = r.kurum ? r.kurum.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') : '';
    return (k ? r.baslik.replace(new RegExp('^' + k + '\\s*[-–]\\s*', 'i'), '') : r.baslik) || r.baslik;
  }
  function kisiSayisi(r) {
    const m = /(?:toplam\s*)?(\d{1,5})\s*kişi/i.exec(r.kadro || '') || /\b(\d{1,5})\s*(?:adet|kişilik)\b/i.exec(r.baslik || '');
    return m ? Number(m[1]) : 0;
  }
  const ilanUrl = (key) => '../ilan/' + encodeURIComponent(key) + '/';

  /* ---------- veri ---------- */
  let ilanVeri = null;
  async function ilanlariYukle() {
    if (ilanVeri) return ilanVeri;
    // bolum-veri.json: okunmuş ve elle düzeltilmiş kadro koşullarıyla (yz_kadrolar) birleştirilmiş kayıtlar; yoksa ham veri.
    // Promise.allSettled yerine (ES2017 hedefi): liste.json yüklenemese de ilanlar gösterilir
    const [i, l] = await Promise.all([getJSON('../bolum-veri.json').catch(() => getJSON('../ilanlar.json')).catch(() => null), getJSON('../liste.json').catch(() => null)]);
    if (!i || !Array.isArray(i.ilanlar)) throw new Error('ilanlar');
    const kopya = new Map(), gorsel = new Map();
    if (l && Array.isArray(l.ilanlar)) for (const o of l.ilanlar) {
      if (!o || typeof o.key !== 'string') continue;
      if (o.kopya_of) kopya.set(o.key, o.kopya_of);
      // kurum logosu ve ilanın meslek görselleri (liste.json, site_uret.py üretir)
      gorsel.set(o.key, {
        logo: typeof o.logo === 'string' && /^ilan\/logo\/[\w.-]+$/.test(o.logo) ? '../' + o.logo : '',
        meslek: Array.isArray(o.meslek) ? o.meslek.filter((m) => typeof m === 'string' && /^\d\d-[a-z-]+\.jpg$/.test(m)) : [],
      });
    }
    const tum = i.ilanlar.filter((r) => r && typeof r.id === 'string' && typeof r.baslik === 'string');
    const duzeltmeKurum = new Set(tum.filter((r) => r.duyuru_turu && /düzeltme/i.test(r.duyuru_turu) && r.kurum).map((r) => E.fold(r.kurum)));
    const ilanlar = tum.filter((r) => !r.duyuru_turu && !kapali(r) && r.kategori !== 'akademik' && !r.iptal_edildi);
    for (const r of ilanlar) r._duzeltme = (Array.isArray(r.duzeltmeler) && r.duzeltmeler.length > 0) || r.duzeltildi === true || (!!r.kurum && duzeltmeKurum.has(E.fold(r.kurum)));
    ilanVeri = { ilanlar, kopya, gorsel };
    return ilanVeri;
  }
  const onbellek = {};
  function json(ad) { return onbellek[ad] || (onbellek[ad] = getJSON('../puanlar/' + ad + '.json').catch(() => { delete onbellek[ad]; return null; })); }

  /* ---------- bölüm önerileri ---------- */
  let duzey = 'lisans', adlar = [], oneriSecili = -1;
  async function adlariDoldur() {
    const d = duzey, v = await json(d + '-bolum');
    if (d !== duzey) return;
    adlar = v && v.bolumler ? [...new Set(Object.values(v.bolumler).filter((x) => typeof x === 'string' && x.length <= 120).map(buyukHarf))].sort((a, b) => a.localeCompare(b, 'tr')) : [];
  }
  function oneriler(q) {
    const f = E.fold(q);
    if (f.length < 2) return [];
    const bas = [], ic = [];
    for (const a of adlar) { const fa = E.fold(a); if (fa.startsWith(f)) bas.push(a); else if (fa.includes(f)) ic.push(a); }
    return bas.concat(ic).slice(0, 8);
  }
  function oneriCiz() {
    const ul = $('ny-oneri'), inp = $('ny-bolum'), l = oneriler(inp.value);
    oneriSecili = -1;
    ul.replaceChildren(...l.map((a, i) => {
      const li = h('li', 'ny-oneri-oge', a); li.id = 'ny-o' + i; li.setAttribute('role', 'option');
      li.onmousedown = (e) => { e.preventDefault(); inp.value = a; oneriKapat(); };
      return li;
    }));
    const ac = l.length > 0 && !(l.length === 1 && E.fold(l[0]) === E.fold(inp.value));
    ul.hidden = !ac; inp.setAttribute('aria-expanded', String(ac));
  }
  function oneriKapat() { $('ny-oneri').hidden = true; $('ny-bolum').setAttribute('aria-expanded', 'false'); $('ny-bolum').removeAttribute('aria-activedescendant'); }
  function oneriTus(e) {
    const ul = $('ny-oneri'); if (ul.hidden) return;
    const ogeler = [...ul.children];
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      oneriSecili = (oneriSecili + (e.key === 'ArrowDown' ? 1 : -1) + ogeler.length) % ogeler.length;
      ogeler.forEach((o, i) => o.classList.toggle('secili', i === oneriSecili));
      $('ny-bolum').setAttribute('aria-activedescendant', 'ny-o' + oneriSecili);
    } else if (e.key === 'Enter' && oneriSecili >= 0) { e.preventDefault(); $('ny-bolum').value = ogeler[oneriSecili].textContent; oneriKapat(); }
    else if (e.key === 'Escape') oneriKapat();
  }

  /* ---------- kaydetme ve takvim ---------- */
  function kayitli() { const l = oku('kit-saved'); return Array.isArray(l) ? l.filter((s) => typeof s === 'string') : []; }
  function kaydetDugmesi(rec, uyeler) {
    const ids = uyeler.map((r) => r.id).filter((x) => typeof x === 'string' && x.length <= 80);
    const b = h('button', 'ny-mini'); b.type = 'button';
    const ciz = () => { const d = kayitli().some((x) => ids.includes(x)); b.textContent = d ? 'Kaydedildi ✓' : 'Kaydet'; b.setAttribute('aria-pressed', String(d)); };
    b.onclick = () => {
      let l = kayitli(); const d = l.some((x) => ids.includes(x));
      l = d ? l.filter((x) => !ids.includes(x)) : l.concat(rec.id && rec.id.length <= 80 ? [rec.id] : ids.slice(0, 1));
      yaz('kit-saved', l); ciz();
      try { if (window.kitKayitliGonder) window.kitKayitliGonder(); } catch (e) { /* hesap yok */ }
      A('tikla', { a: d ? 'kaydi_sil' : 'kaydet', x: 'nereye' });
    };
    ciz();
    return ids.length ? b : null;
  }
  function takvimDugmesi(rec, key) {
    const metin = C.icsMetni(rec, SITE + 'ilan/' + encodeURIComponent(key) + '/');
    if (!metin) return null;
    const b = h('button', 'ny-mini', 'Takvime ekle'); b.type = 'button';
    b.onclick = () => {
      const url = URL.createObjectURL(new Blob([metin], { type: 'text/calendar;charset=utf-8' }));
      const a = h('a'); a.href = url; a.download = 'son-gun-' + String(rec.son_tarih) + '.ics';
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      A('tikla', { a: 'nereye_takvim', x: rec.kurum || '' });
    };
    return b;
  }

  /* ---------- çizim ----------
     Kart düzeni (25 Kasım 2026): üstte kurum logosu + kurum adı (en belirgin satır) ve ilan başlığı; ortada sana uyan
     kadrolar, her biri meslek fotoğrafıyla ve "Hukuk mezunları bu kadroya P48 puanıyla başvurabilir" cümlesiyle; altta
     tek satırda son gün + "Nasıl başvururum?" + Başvur. */
  let aday = { bolum: '', duzey: 'lisans' };
  // TAMAMI BÜYÜK HARF ad okunaklı yazılır ("ADLİ TIP KURUMU" → "Adli Tıp Kurumu"); kısaltmalar (SGK, TÜBİTAK) korunur
  const KISALTMA = new Set(['TÜBİTAK', 'ASELSAN', 'BOTAŞ', 'TCDD', 'TOKİ', 'DSİ', 'AFAD', 'MEB', 'KOSGEB', 'İŞKUR', 'BDDK', 'EPDK', 'TMO', 'ÇAYKUR', 'TPAO',
    'TEİAŞ', 'EÜAŞ', 'ÖSYM', 'YÖK', 'TÜİK', 'TİKA', 'MİT', 'TBMM', 'KKTC', 'TÜRKAK', 'TEDAŞ', 'TEMSAN', 'İTÜ', 'ODTÜ', 'TOBB', 'MTA', 'BİLGEM']);
  const BAGLAC = new Set(['ve', 'ile', 'veya', 'için', 'ya', 'da', 'de']);
  function okunakli(s) {
    s = String(s || '');
    if (!/[A-ZÇĞİÖŞÜ]{3}/.test(s) || /[a-zçğıöşü]/.test(s)) return s;
    let ilk = true;
    return s.split(/(\s+|[\/(),-])/).map((w) => {
      if (!/[A-ZÇĞİÖŞÜ]/.test(w)) return w;
      const k = w.toLocaleLowerCase('tr'), bas = ilk; ilk = false;
      if (KISALTMA.has(w) || (/^[A-ZÇĞİÖŞÜ]{2,5}$/.test(w) && !/[AEIİOÖUÜ]/.test(w))) return w;
      if (!bas && BAGLAC.has(k)) return k;
      return w.charAt(0) + k.slice(1);
    }).join('');
  }
  function turYaz(l) {
    if (!l || !l.length) return 'KPSS puanıyla';
    return l.length === 1 ? l[0] + ' puanıyla' : l.slice(0, 3).join('/') + (l.length > 3 ? '…' : '') + ' puanlarından biriyle';
  }
  function basHarf(kurum) {
    const k = String(kurum || '').split(/\s+/).filter((w) => w.length > 2 && !/^(ve|ile|için)$/i.test(w));
    return (k.slice(0, 2).map((w) => w.charAt(0).toLocaleUpperCase('tr')).join('') || 'K');
  }
  function logoKutu(r, logo) {
    const s = h('span', 'ny-logo');
    const harf = () => { s.classList.add('harf'); s.replaceChildren(document.createTextNode(basHarf(r.kurum))); };
    if (logo) { const im = h('img'); im.src = logo; im.alt = ''; im.width = 44; im.height = 44; im.loading = 'lazy'; im.decoding = 'async'; im.onerror = harf; s.append(im); }
    else harf();
    return s;
  }
  function meslekFoto(dosya) {
    const im = h('img', 'ny-foto'); im.src = '../assets/meslek/kucuk/' + dosya; im.alt = ''; im.width = 52; im.height = 52;
    im.loading = 'lazy'; im.decoding = 'async'; im.onerror = () => { im.style.visibility = 'hidden'; };
    return im;
  }
  function uygunCumle(k, kpsssiz, tek) {
    const kim = (aday.bolum ? buyukHarf(aday.bolum) : 'Lise') + ' mezunları ' + (tek ? 'bu kadroya ' : '');
    if (kpsssiz) return kim + 'KPSS puanı olmadan başvurabilir';
    return kim + turYaz(k.turler) + ' başvurabilir' + (k.puan !== null ? ' · en az ' + puanYaz(k.puan) : '');
  }
  function ilanKart(x, puan) {
    const r = x.rec, key = x.anahtar, g = kalanGun(r), yontem = C.basvuruSekli(r);
    const gv = (ilanVeri && ilanVeri.gorsel.get(key)) || { logo: '', meslek: [] };
    const kap = h('article', 'ny-ilan' + (g !== null && g <= 3 ? ' acil' : ''));
    kap.dataset.anahtar = key;
    // 1) kim: logo + kurum + ilan başlığı + zaman rozeti
    const ust = h('header', 'ny-ust'), kim = h('div', 'ny-kim');
    // Tekrar yok (kullanıcı 25 Kasım 2026): "5 Müfettiş Yardımcısı Alacak" gibi başlık, altındaki kadro satırını
    // tekrarlıyorsa yazılmaz; o zaman ilan sayfasına kurum adı bağlanır.
    // karşılaştırma kelime köküyle (ilk 6 harf): "Müfettiş Yardımcılığı Giriş Sınavı" ≈ "Müfettiş Yardımcısı Alımı"
    const kokler = (s) => E.fold(String(s).replace(/\([^)]*\)/g, ' ')).split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2 && !/^(alim|alimi|ilan|ilani|duyuru|duyurusu|sinav|sinavi|giris|ve|ile|icin)$/.test(w)).map((w) => w.slice(0, 6));
    const baslik = okunakli(kisaBaslik(r)), bk = new Set(kokler(baslik)), adlar = x.kadrolar.filter((k) => k.ad).map((k) => kokler(k.ad));
    const tekrar = /\balacak$/i.test(E.fold(baslik)) || (adlar.length > 0 && adlar.every((k) => k.length > 0 && k.every((w) => bk.has(w))));
    if (tekrar) { const ka = h('a', 'ny-kurum', okunakli(r.kurum) || 'Kurum'); ka.href = ilanUrl(key); kim.append(ka); }
    else {
      kim.append(h('span', 'ny-kurum', okunakli(r.kurum) || 'Kurum'));
      const t = h('h3'), a = h('a', '', baslik); a.href = ilanUrl(key); t.append(a); kim.append(t);
    }
    ust.append(logoKutu(r, gv.logo), kim);
    if (baslamadi(r)) ust.append(h('span', 'ny-gun bekle', 'Açılış ' + tarihYaz((r.baslangic_zaman || '').slice(0, 10))));
    else if (g !== null) ust.append(h('span', 'ny-gun', g <= 0 ? 'Bugün son gün' : g === 1 ? 'Yarın son gün' : g + ' gün kaldı'));
    kap.append(ust);
    // 2) ne: sana uyan kadrolar (meslek fotoğrafı + ad + kişi + uygunluk cümlesi)
    const adli = x.kadrolar.filter((k) => k.ad), uygun = x.grup === 'hemen';
    const satirlar = adli.length ? adli.slice(0, 3) : x.kadrolar.slice(0, 1);
    if (satirlar.length) {
      const ul = h('ul', 'ny-kadro');
      ul.setAttribute('aria-label', uygun ? 'Sana uyan kadrolar' : 'Kadrolar');
      for (const k of satirlar) {
        const li = h('li'), ic = h('div', 'ny-kadro-ic');
        const dosya = k.ad ? C.meslekDosya(k.ad, r.kurum) : gv.meslek[0] || '30-genel.jpg';
        const n = k.ad ? k.adet : kisiSayisi(r);
        const ad = k.ad ? okunakli(k.ad.length > 70 ? k.ad.slice(0, 69).replace(/\s+\S*$/, '') + '…' : k.ad) : 'İlandaki kadrolar';
        const bas = h('p', 'ny-kadro-ad'); bas.append(h('b', '', ad));
        if (n) bas.append(h('span', 'ny-adet', n + ' kişi'));
        ic.append(bas);
        if (uygun) { const u = h('p', 'ny-uygun'); u.insertAdjacentHTML('afterbegin', TIK_SVG); u.append(uygunCumle(k, x.kpsssiz, satirlar.length === 1)); ic.append(u); }
        else if (k.puan !== null && !x.kpsssiz) ic.append(h('p', 'ny-kadro-alt', 'En az ' + puanYaz(k.puan) + ' ' + (k.turler && k.turler.length ? k.turler.slice(0, 3).join('/') + ' ' : '') + 'puan'));
        if (k.not) ic.append(h('p', 'ny-kadro-alt uyari', k.not));
        li.append(meslekFoto(dosya), ic); ul.append(li);
      }
      if (adli.length > 3) ul.append(h('li', 'ny-kadro-ek', '+' + (adli.length - 3) + ' kadro daha · ilanda'));
      kap.append(ul);
    }
    if (x.neden && !uygun) kap.append(h('p', 'ny-neden', x.neden + '.'));
    // 3) ne zaman / nasıl: tek satır
    const alt = h('div', 'ny-alt-satir'), cip = h('div', 'ny-cipler');
    if (r.son_tarih) { const s = h('span', 'ny-son-gun'); s.insertAdjacentHTML('afterbegin', TAKVIM_SVG); s.append('Son gün ', h('b', '', tarihYaz(r.son_tarih))); cip.append(s); }
    if (r._duzeltme) cip.append(h('span', 'uyari', 'Düzeltme yayımlanmış'));
    alt.append(cip);
    kap.append(alt);
    if (x.grup === 'yetmiyor') return kap;
    // tek büyük eylem: başvuru sayfası varsa oraya, yoksa ilanın tamamına
    const ey = h('div', 'ny-eylem'), bv = h('a', 'ny-basvur');
    if (yontem.link) { bv.href = yontem.link; bv.target = '_blank'; bv.rel = 'noopener'; bv.append('Başvur'); }
    else { bv.href = ilanUrl(key); bv.append('İlanı aç'); }
    bv.insertAdjacentHTML('beforeend', OK_SVG);
    bv.addEventListener('click', () => A('tikla', { a: 'nereye_basvur', x: r.kurum || '' }));
    const ac = h('button', 'ny-nasil-ac', 'Nasıl başvururum?'); ac.type = 'button'; ac.setAttribute('aria-expanded', 'false');
    ey.append(ac, bv); alt.append(ey);

    const d = h('div', 'ny-nasil'), ol = h('ol');
    d.id = 'ny-n-' + Math.random().toString(36).slice(2, 9); d.hidden = true; ac.setAttribute('aria-controls', d.id);
    ac.onclick = () => { const acik = d.hidden; d.hidden = !acik; ac.setAttribute('aria-expanded', String(acik)); if (acik) A('tikla', { a: 'nereye_nasil', x: r.kurum || '' }); };
    const l1 = h('li'); l1.append(h('b', '', 'Nereden: '), yontem.ad);
    if (yontem.link) { const la = h('a', '', 'Başvuru sayfası ↗'); la.href = yontem.link; la.target = '_blank'; la.rel = 'noopener'; l1.append(' ', la); }
    ol.append(l1);
    const ortak = (Array.isArray(r.yz_ortak) ? r.yz_ortak : []).filter((m) => typeof m === 'string' && !/başvuru/i.test(m)).slice(0, 4);
    if (ortak.length) {
      const l2 = h('li'); l2.append(h('b', '', 'Şunlara dikkat et:'));
      const u = h('ul', 'ny-dikkat'); for (const m of ortak) u.append(h('li', '', m)); l2.append(u); ol.append(l2);
    }
    const l3 = h('li'); l3.append(h('b', '', 'Şartları son kez oku: '));
    const lb = h('a', '', 'ilanın tamamı'); lb.href = ilanUrl(key); l3.append(lb);
    if (/^https?:\/\//.test(r.link || '')) { const lr = h('a', '', 'resmî ilan ↗'); lr.href = r.link; lr.target = '_blank'; lr.rel = 'noopener'; l3.append(' · ', lr); }
    ol.append(l3);
    const l4 = h('li'); l4.append(h('b', '', 'Son güne bırakma: '), r.son_tarih ? tarihYaz(r.son_tarih) + (r.son_zaman ? ' saat ' + String(r.son_zaman).slice(11, 16) : '') + ' bitiyor.' : 'son tarih ilanda yazıyor.');
    ol.append(l4);
    const dg = h('div', 'ny-dugmeler');
    const tk = takvimDugmesi(r, key), kd = kaydetDugmesi(r, x.uyeler);
    if (tk) dg.append(tk); if (kd) dg.append(kd);
    d.append(ol); if (dg.children.length) d.append(dg);
    kap.append(d);
    return kap;
  }
  function bolge(id, baslik, alt, ogeler, bos, puan) {
    const s = h('section', 'ny-bolge'); s.id = id;
    const bb = h('h2'); bb.append(baslik, ' ', h('span', 'ny-sayi', String(ogeler.length))); s.append(bb);
    if (alt) s.append(h('p', 'ny-alt', alt));
    if (!ogeler.length) s.append(h('p', 'ny-bos', bos));
    else { const l = h('div', 'ny-liste'); for (const x of ogeler) l.append(ilanKart(x, puan)); s.append(l); }
    return s;
  }
  function merkeziBolge(m, puan, d, bolumMetni) {
    const s = h('section', 'ny-bolge ny-merkezi'); s.id = 'ny-merkezi';
    s.append(h('h2', '', 'KPSS tercihlerinde (merkezi atama)'));
    if (!m) { s.append(h('p', 'ny-bos', 'Bu düzeyin taban puanları yüklenemedi.')); return s; }
    const donem = m.donem.replace(/-(\d)/g, '/$1');
    if (puan === null) { s.append(h('p', 'ny-alt', 'Puanını yazarsan son tercih dönemlerinde (' + donem + ') puanınla yerleşilen kadroları gösteririz.')); return s; }
    if (m.bolumYok) { s.append(h('p', 'ny-bos', 'Bölüm adını listeden seçersen tercih kadrolarını da gösterebiliriz.')); return s; }
    const ozet = h('p', 'ny-buyuk');
    ozet.append(h('b', '', String(m.uygun.length)), ' kadroya ' + C.DUZEY[d].tur + ' puanınla yerleşilmiş', h('small', '', ' · son ' + DONEM_SAYI + ' tercih dönemi (' + donem + ')' + (m.kontenjan ? ', ' + m.kontenjan + ' kontenjan' : '')));
    s.append(ozet);
    if (m.sinirda.length) s.append(h('p', 'ny-alt', '+' + SINIR + ' puanla ' + m.sinirda.length + ' kadro daha açılırdı.'));
    const liste = (kadrolar, baslik) => {
      if (baslik) s.append(h('h3', 'ny-ara', baslik));
      const ol = h('ol', 'ny-kadrolar');
      for (const k of kadrolar) {
        const li = h('li'), sol = h('div');
        sol.append(h('b', '', buyukHarf(k.unvan)), h('span', '', buyukHarf(k.kurum) + ' · ' + ilYaz(k.il)));
        const sag = h('div', 'ny-taban'); sag.append(h('b', '', puanYaz(k.min)), h('span', '', k.donem.replace('-', '/') + ' tabanı · ' + k.kontenjan + ' kişi'));
        li.append(sol, sag); ol.append(li);
      }
      s.append(ol);
    };
    if (m.uygun.length) liste(m.uygun.slice(0, MERKEZI_ILK));
    else if (m.yakin.length) liste(m.yakin, 'Puanına en yakın kadrolar');
    const a = h('a', 'btn btn-ikinci ny-robot', 'Tümünü Tercih Robotu’nda gör →'); a.href = '../puanlar/';
    a.onclick = () => A('tikla', { a: 'nereye_robot', x: d });
    s.append(a);
    s.append(h('p', 'ny-dip', 'Tercih dönemi açıldığında taban puanları değişebilir; bu liste geçmiş dönemlerin sonuçlarıdır.'));
    return s;
  }

  /* ---------- paylaşım kartı (1080x1350 PNG; kişisel bilgi olarak yalnız puan, düzey ve bölüm) ---------- */
  async function kartUret(o) {
    const W = 1080, H = 1350, c = document.createElement('canvas'); c.width = W; c.height = H;
    const x = c.getContext('2d');
    try { await document.fonts.load('800 80px Inter'); await document.fonts.load('600 40px Inter'); } catch (e) { /* yazı tipi yok: sistem yazı tipi */ }
    const F = (w, s) => w + ' ' + s + 'px Inter, "Segoe UI", Arial, sans-serif';
    x.fillStyle = '#111310'; x.fillRect(0, 0, W, H);
    x.fillStyle = '#C8F169'; x.fillRect(0, 0, W, 14);
    const logo = await new Promise((res) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = '../assets/logo-192.png?v=2'; });
    if (logo) x.drawImage(logo, 80, 80, 96, 96);
    x.fillStyle = '#F0F2EB'; x.font = F('700', 44); x.textBaseline = 'middle'; x.fillText('KPSS Tercihi', logo ? 200 : 80, 128);
    const sar = (metin, mx, font, satirH, y0, renk, enCok) => {
      x.font = font; x.fillStyle = renk; x.textBaseline = 'alphabetic';
      const kel = String(metin).split(/\s+/); let sat = '', y = y0, n = 0;
      for (const k of kel) {
        const dene = sat ? sat + ' ' + k : k;
        if (x.measureText(dene).width > mx && sat) { x.fillText(sat, 80, y); y += satirH; sat = k; if (++n >= enCok - 1) break; } else sat = dene;
      }
      if (sat) { x.fillText(sat, 80, y); y += satirH; }
      return y;
    };
    let y = 360;
    if (o.sayi > 0) {
      x.fillStyle = '#C8F169'; x.font = F('800', 200); x.textBaseline = 'alphabetic'; x.fillText(String(o.sayi), 80, y + 120);
      y = sar('ilana şimdi başvurabiliyorum', 920, F('700', 72), 86, y + 230, '#F0F2EB', 3);
    } else {   // sıfır sonuç paylaşılırken "0 ilan" yazılmaz
      y = sar('Puanımla nereye başvurabileceğime baktım', 920, F('800', 88), 104, y + 60, '#C8F169', 4);
    }
    if (o.merkezi) y = sar('Tercihlerde puanım ' + o.merkezi + ' kadroya yetiyordu', 920, F('600', 44), 58, y + 30, '#C7CBBF', 2);
    x.fillStyle = '#23271F'; x.fillRect(80, H - 330, W - 160, 2);
    sar([o.duzey, o.bolum, o.puan !== null ? puanYaz(o.puan) + ' puan' : ''].filter(Boolean).join(' · '), 920, F('600', 40), 52, H - 250, '#949A8B', 2);
    x.fillStyle = '#F0F2EB'; x.font = F('700', 46); x.fillText('Sen de bak: kpsstercihi.com/nereye', 80, H - 110);
    return new Promise((res) => c.toBlob((b) => res(b), 'image/png'));
  }
  function paylasDugmeleri(o) {
    const son = h('div', 'ny-son');
    const kart = h('button', 'btn btn-ana', 'Sonucumu paylaş'); kart.type = 'button';
    kart.onclick = async () => {
      kart.disabled = true;
      try {
        const blob = await kartUret(o);
        const dosya = blob && typeof File === 'function' ? new File([blob], 'kpss-tercihi-sonucum.png', { type: 'image/png' }) : null;
        const metin = 'KPSS puanımla başvurabileceğim ilanlara baktım. Sen de bak: ' + SITE + 'nereye/';
        if (dosya && navigator.canShare && navigator.canShare({ files: [dosya] })) {
          try { await navigator.share({ files: [dosya], text: metin }); } catch (e) { /* vazgeçti */ }
        } else if (blob) {
          const url = URL.createObjectURL(blob), a = h('a'); a.href = url; a.download = 'kpss-tercihi-sonucum.png';
          document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 4000);
        }
        A('tikla', { a: 'nereye_paylas', x: o.duzeyKod });
      } finally { kart.disabled = false; }
    };
    const tg = h('a', 'btn btn-ikinci', 'Yeni ilanlar için Telegram’a katıl'); tg.href = 'https://t.me/kpsstercihi'; tg.target = '_blank'; tg.rel = 'noopener'; tg.dataset.a = 'telegram'; tg.dataset.aX = 'nereye';
    son.append(kart, tg);
    return son;
  }

  /* ---------- aramayı kaydet + bildirim ---------- */
  function kayitOku() { const k = oku(KAYIT); return k && typeof k === 'object' && FORM[k.d] ? k : null; }
  function ayniArama(k, d, b, p) {
    return !!k && k.d === d && E.fold(k.b || '') === E.fold(b || '') && (k.p == null ? null : Number(k.p)) === (p == null ? null : p);
  }
  function b64u(s) {
    const t = atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4));
    const u = new Uint8Array(t.length); for (let i = 0; i < t.length; i++) u[i] = t.charCodeAt(i); return u;
  }
  function pushDestek() { return 'serviceWorker' in navigator && 'PushManager' in window && typeof Notification !== 'undefined'; }
  async function bildirimAc(d, b, p) {
    if (!VAPID_ACIK) return 'yerel';
    if (!pushDestek()) return 'desteksiz';
    const izin = await Notification.requestPermission();
    if (izin !== 'granted') return 'izinyok';
    const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
    await navigator.serviceWorker.ready;
    const sub = (await reg.pushManager.getSubscription()) || (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64u(VAPID_ACIK) }));
    const r = await fetch(API + '/web/abone', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ abonelik: sub.toJSON(), duzey: d, bolum: b, puan: p }) });
    if (!r.ok) throw new Error(String(r.status));
    yaz(BILDIRIM, { endpoint: sub.endpoint });
    return 'acik';
  }
  async function bildirimKapat() {
    const kb = oku(BILDIRIM);
    try { localStorage.removeItem(BILDIRIM); } catch (e) { /* depolama kapalı */ }
    if (!kb || !pushDestek()) return;
    try {
      const reg = await navigator.serviceWorker.getRegistration('/');
      const sub = reg && (await reg.pushManager.getSubscription());
      if (sub) await sub.unsubscribe();
      await fetch(API + '/web/sil', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ endpoint: kb.endpoint }) });
    } catch (e) { /* sunucu silinemedi: sonraki gönderimde 410 ile düşer */ }
  }
  const DURUM_YAZI = {
    acik: 'Tamam! Bölümüne uygun yeni ilan çıkınca telefonuna bildirim gelecek.',
    yerel: 'Aramanı kaydettik. Siteye her girdiğinde yeni ilanları en üstte göreceksin.',
    desteksiz: 'Aramanı kaydettik. Bu tarayıcı bildirim göstermiyor; telefonda siteyi ana ekrana ekleyince bildirim de gelir.',
    izinyok: 'Bildirime izin verilmedi; aramanı yine de kaydettik.',
    hata: 'Bildirim şu an açılamadı; aramanı kaydettik, sonra tekrar dene.',
  };
  function kaydetBolumu(d, b, p, gorunur) {
    const s = h('section', 'ny-kaydet'); s.id = 'ny-kaydet';
    const bas = h('div', 'ny-kaydet-bas'); bas.insertAdjacentHTML('afterbegin', ZIL_SVG);
    const aciklama = h('p');
    const bm = h('div'); bm.append(h('h2', '', 'Yeni ilan çıkınca haber verelim'), aciklama);
    bas.append(bm);
    const dg = h('button', 'ny-git'); dg.type = 'button';
    const not = h('p', 'ny-kaydet-not'); not.setAttribute('role', 'status');
    const sil = h('button', 'ny-kaydet-dur', 'Kaydı sil'); sil.type = 'button';
    const ciz = () => {
      const kayitli = ayniArama(kayitOku(), d, b, p);
      dg.textContent = kayitli ? 'Kaydedildi ✓' : (VAPID_ACIK ? 'Kaydet ve bildirim al' : 'Aramayı kaydet');
      dg.setAttribute('aria-pressed', String(kayitli));
      sil.hidden = !kayitli;
      aciklama.textContent = kayitli
        ? (oku(BILDIRIM) ? 'Bu arama kayıtlı. Yeni ilan çıkınca bildirim gelecek.' : 'Bu arama kayıtlı. Siteye her girdiğinde yeni ilanlar en üstte.')
        : 'Bu aramayı kaydet; bölümüne uygun yeni ilan gelince sana bildirelim.';
    };
    dg.onclick = async () => {
      if (ayniArama(kayitOku(), d, b, p)) return;
      yaz(KAYIT, { d, b, p, gorulen: gorunur.slice(0, 300), t: bugun() });
      ciz(); dg.disabled = true;
      let sonuc;
      try { sonuc = await bildirimAc(d, b, p); } catch (e) { sonuc = 'hata'; }
      dg.disabled = false; not.textContent = DURUM_YAZI[sonuc];
      A('tikla', { a: 'nereye_kaydet', x: sonuc });
    };
    sil.onclick = async () => {
      try { localStorage.removeItem(KAYIT); } catch (e) { /* depolama kapalı */ }
      await bildirimKapat();
      ciz(); not.textContent = 'Kayıt silindi.';
      A('tikla', { a: 'nereye_kayit_sil', x: d });
    };
    ciz();
    s.append(bas, dg, not, sil);
    return s;
  }

  function hata(m) { const e = $('ny-hata'); e.textContent = m || ''; e.hidden = !m; }
  function durum(m) { const e = $('ny-durum'); e.textContent = m || ''; e.hidden = !m; }

  async function calistir() {
    hata(''); oneriKapat();
    const bolumMetni = $('ny-bolum').value.trim().slice(0, 120);
    const puansiz = $('ny-puansiz').checked;
    const ham = String($('ny-puan').value).trim().replace(',', '.');
    let puan = null;
    if (!puansiz) {
      if (!ham) { hata('KPSS puanını yaz ya da “Puanım yok” kutusunu işaretle.'); $('ny-puan').focus(); return; }
      puan = Number(ham);
      if (!(puan >= 1 && puan <= 100)) { hata('Puan 1 ile 100 arasında olmalı (ör. 72,5).'); $('ny-puan').focus(); return; }
    }
    if (!bolumMetni && duzey !== 'ortaogretim') { hata('Bölümünü yaz (' + FORM[duzey].ornek + ').'); $('ny-bolum').focus(); return; }
    if (bolumMetni && !E.bolumCoz(bolumMetni).length) { hata('Bölüm adını tanıyamadık; listeden seçmeyi dene.'); return; }
    durum('Bakılıyor…');
    let v;
    try { v = await ilanlariYukle(); } catch (e) { durum(''); hata('İlanlar yüklenemedi; sayfayı yenileyip tekrar dene.'); return; }
    const [pv, bv] = await Promise.all([json(duzey), json(duzey + '-bolum')]);
    const m = C.merkezi(pv, bv, bolumMetni, puan === null ? 0 : puan, DONEM_SAYI, SINIR);
    durum('');
    aday = { bolum: bolumMetni, duzey };

    const gruplar = { hemen: [], kontrol: [], okunamadi: [], yetmiyor: [], degil: [] };
    for (const x of C.ilanlariDegerlendir(v.ilanlar, v.kopya, bolumMetni, duzey, puan)) gruplar[x.grup].push(x);
    const sira = (a, b) => (sonAn(a.rec) || Infinity) - (sonAn(b.rec) || Infinity);
    for (const k of Object.keys(gruplar)) gruplar[k].sort(sira);

    const kap = $('ny-sonuc'); kap.replaceChildren();
    const ozet = h('div', 'ny-ozet');
    const kutu = (n, et, hedef, cls) => { const a = h('a', 'ny-kutu ' + cls); a.href = '#' + hedef; a.append(h('b', '', String(n)), h('span', '', et)); return a; };
    ozet.append(kutu(gruplar.hemen.length, 'ilana şimdi başvurabilirsin', 'ny-hemen', 'yesil'));
    if (gruplar.kontrol.length) ozet.append(kutu(gruplar.kontrol.length, 'ilanı kontrol et', 'ny-kontrol', 'sari'));
    const merkeziVar = m && !m.bolumYok && puan !== null;
    if (merkeziVar) ozet.append(kutu(m.uygun.length, 'tercih kadrosu puanına yetiyor', 'ny-merkezi', 'mavi'));
    kap.append(ozet);

    kap.append(bolge('ny-hemen', 'Şimdi başvurabilirsin', 'Bölümün' + (puan !== null ? ' ve puanın' : '') + ' tutuyor. Yaş, deneyim gibi şartlara ilanda bak.', gruplar.hemen,
      'Şu an bölümüne açık ilan yok. Yeni ilan çıkınca Telegram kanalında duyuruyoruz.', puan));
    if (gruplar.kontrol.length) kap.append(bolge('ny-kontrol', 'Kontrol et', 'Uygun olabilirsin ama bir şartı ilandan okuman gerek.', gruplar.kontrol, '', puan));
    kap.append(merkeziBolge(m, puan, duzey, bolumMetni));
    const kapaliListe = (ogeler, baslik, alt) => {
      if (!ogeler.length) return;
      const d = h('details', 'ny-bolge ny-yetmiyor'), sm = h('summary');
      sm.append(baslik + ' ', h('span', 'ny-sayi', String(ogeler.length)));
      d.append(sm);
      if (alt) d.append(h('p', 'ny-alt', alt));
      const l = h('div', 'ny-liste'); for (const x of ogeler) l.append(ilanKart(x, puan));
      d.append(l); kap.append(d);
    };
    kapaliListe(gruplar.okunamadi, 'Şartı okunamayan ilanlar', 'Bölüm şartını siteye alamadık; seni kapsıyor olabilir. Belgesine bakmak gerek.');
    kapaliListe(gruplar.yetmiyor, 'Puanın yetmeyen ilanlar');
    // kayıtlı aramada son bakıştan beri gelen ilanlar en üstte duyurulur; görülenler güncellenir
    const gorunur = gruplar.hemen.concat(gruplar.kontrol).map((x) => x.anahtar);
    const kayit = kayitOku();
    if (ayniArama(kayit, duzey, bolumMetni, puan)) {
      const eski = new Set(kayit.gorulen || []);
      const yeniler = gruplar.hemen.concat(gruplar.kontrol).filter((x) => !eski.has(x.anahtar));
      if (yeniler.length) {
        const y = h('p', 'ny-yeni'); y.insertAdjacentHTML('afterbegin', YILDIZ_SVG);
        y.append('Son bakışından beri ' + yeniler.length + ' yeni ilan var');
        kap.insertBefore(y, ozet);
        for (const x of yeniler) { const el = kap.querySelector('[data-anahtar="' + CSS.escape(x.anahtar) + '"] .ny-ust'); if (el) el.append(h('span', 'ny-yeni-rozet', 'YENİ')); }
      }
      yaz(KAYIT, Object.assign({}, kayit, { gorulen: gorunur.slice(0, 300), t: bugun() }));
    }
    // kaydet/bildirim kutusu özetin hemen altında: aşağı kaydırmadan görülsün
    kap.insertBefore(kaydetBolumu(duzey, bolumMetni, puan, gorunur), ozet.nextSibling);
    $('ny-bekle').hidden = true;
    kap.append(paylasDugmeleri({ sayi: gruplar.hemen.length, merkezi: merkeziVar ? m.uygun.length : null, duzey: C.DUZEY[duzey].ad, duzeyKod: duzey, bolum: bolumMetni ? buyukHarf(bolumMetni) : '', puan }));

    /* Profil: ana sayfa ve Tercih Robotu aynı bilgiyi kullanır (iller ve diğer alanlar korunur). */
    const eski = oku('kit-profil') || {};
    const p = { v: 1, ogrenim: duzey, puan_turu: C.DUZEY[duzey].tur, iller: Array.isArray(eski.iller) ? eski.iller : [], tum_turkiye: eski.tum_turkiye === true, bolum: bolumMetni.slice(0, 60), t: bugun() };
    if (puan !== null) p.puan = puan;
    yaz('kit-profil', p);
    yaz('kit-bolum', { d: duzey, b: bolumMetni });
    try { const q = new URLSearchParams({ d: duzey }); if (bolumMetni) q.set('b', bolumMetni); if (puan !== null) q.set('p', String(puan)); history.replaceState(null, '', '?' + q.toString()); } catch (e) { /* adres güncellenemedi */ }
    A('tikla', { a: 'nereye', x: duzey, n: puan === null ? -1 : Math.floor(puan / 5) * 5 });
    kap.scrollIntoView && kap.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function duzeySec(d) {
    if (!FORM[d]) return;
    duzey = d;
    document.querySelectorAll('#ny-duzey button').forEach((b) => { const on = b.dataset.d === d; b.classList.toggle('secili', on); b.setAttribute('aria-pressed', String(on)); });
    $('ny-bolum-et').textContent = FORM[d].bolumEt;
    $('ny-bolum').placeholder = FORM[d].ornek;
    $('ny-bolum-ipucu').hidden = d !== 'ortaogretim';
    adlar = []; adlariDoldur();
  }

  function basla() {
    if (!E || !C) { hata('Sayfa tam yüklenemedi; yenile.'); return; }
    const y = $('yil'); if (y) y.textContent = String(new Date().getFullYear());
    document.querySelectorAll('#ny-duzey button').forEach((b) => { b.onclick = () => duzeySec(b.dataset.d); });
    const inp = $('ny-bolum');
    inp.addEventListener('input', oneriCiz);
    inp.addEventListener('keydown', oneriTus);
    inp.addEventListener('blur', () => setTimeout(oneriKapat, 120));
    $('ny-puansiz').addEventListener('change', (e) => { $('ny-puan').disabled = e.target.checked; if (e.target.checked) $('ny-puan').value = ''; });
    $('ny-form').addEventListener('submit', (e) => { e.preventDefault(); calistir(); });

    const q = new URLSearchParams(location.search), pr = oku('kit-profil'), kayit = kayitOku();
    // kayıtlı arama varsa ve adreste başka arama yoksa sayfa onunla açılır (yeni ilanlar üstte gösterilir)
    if (!q.get('d') && kayit) {
      duzeySec(kayit.d);
      inp.value = String(kayit.b || '').slice(0, 120);
      if (kayit.p == null) { $('ny-puansiz').checked = true; $('ny-puan').disabled = true; } else $('ny-puan').value = String(kayit.p).replace('.', ',');
      calistir();
      return;
    }
    const prOk = pr && typeof pr === 'object' && pr.atlandi !== true && FORM[pr.ogrenim];
    const d0 = FORM[q.get('d')] ? q.get('d') : prOk ? pr.ogrenim : 'lisans';
    duzeySec(d0);
    const b0 = q.get('b') || (prOk && pr.ogrenim === d0 && typeof pr.bolum === 'string' ? pr.bolum : '');
    if (b0) inp.value = b0.slice(0, 120);
    const p0 = q.get('p') || (prOk && pr.ogrenim === d0 && typeof pr.puan === 'number' ? String(pr.puan) : '');
    if (p0 && Number(String(p0).replace(',', '.')) > 0) $('ny-puan').value = String(p0).replace('.', ',');
    // bağlantıyla gelindiyse (ör. bölüm sayfasından ?d=&b=) puan varsa hemen bakılır; yoksa puan kutusuna geçilir
    if (q.get('d') && (q.get('b') || q.get('p'))) { if ($('ny-puan').value) calistir(); else $('ny-puan').focus(); }
  }
  basla();
})();
