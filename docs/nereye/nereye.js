/* "Puanınla nereye başvurabilirsin?" sayfası: form, sonuç çizimi, takvim, kaydetme ve paylaşım kartı.
 * Kararlar cekirdek.js'tedir (NereyeCekirdek); bu dosya yalnız veri yükler ve gösterir. */
(function () {
  'use strict';
  const E = window.BolumEsles, C = window.NereyeCekirdek;
  const $ = (id) => document.getElementById(id);
  const AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  const FORM = {
    ortaogretim: { bolumEt: 'Alanın / dalın', ornek: 'ör. Muhasebe ve Finansman' },
    onlisans: { bolumEt: 'Bölümün', ornek: 'ör. Tıbbi Dokümantasyon ve Sekreterlik' },
    lisans: { bolumEt: 'Bölümün', ornek: 'ör. Hemşirelik' },
  };
  const SINIR = 2;          // merkezi atamada "sınırda" sayılan puan farkı
  const MERKEZI_ILK = 8;
  const DONEM_SAYI = 4;     // merkezi atamada bakılan son tercih dönemi sayısı
  const SITE = 'https://kpsstercihi.com/';

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
    const [i, l] = await Promise.allSettled([getJSON('../bolum-veri.json').catch(() => getJSON('../ilanlar.json')), getJSON('../liste.json')]);
    if (i.status !== 'fulfilled' || !i.value || !Array.isArray(i.value.ilanlar)) throw new Error('ilanlar');
    const kopya = new Map();
    if (l.status === 'fulfilled' && l.value && Array.isArray(l.value.ilanlar)) for (const o of l.value.ilanlar) if (o && o.kopya_of && o.key) kopya.set(o.key, o.kopya_of);
    const tum = i.value.ilanlar.filter((r) => r && typeof r.id === 'string' && typeof r.baslik === 'string');
    const duzeltmeKurum = new Set(tum.filter((r) => r.duyuru_turu && /düzeltme/i.test(r.duyuru_turu) && r.kurum).map((r) => E.fold(r.kurum)));
    const ilanlar = tum.filter((r) => !r.duyuru_turu && !kapali(r) && r.kategori !== 'akademik' && !r.iptal_edildi);
    for (const r of ilanlar) r._duzeltme = (Array.isArray(r.duzeltmeler) && r.duzeltmeler.length > 0) || r.duzeltildi === true || (!!r.kurum && duzeltmeKurum.has(E.fold(r.kurum)));
    ilanVeri = { ilanlar, kopya };
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

  /* ---------- çizim ---------- */
  function ilanKart(x, puan) {
    const r = x.rec, key = x.anahtar, g = kalanGun(r), yontem = C.basvuruSekli(r);
    const kap = h('article', 'ny-ilan' + (g !== null && g <= 3 ? ' acil' : ''));
    const ust = h('div', 'ny-ust');
    ust.append(h('span', 'ny-kurum', r.kurum || 'Kurum'));
    if (baslamadi(r)) ust.append(h('span', 'ny-gun', 'Başvuru başlangıcı: ' + tarihYaz((r.baslangic_zaman || '').slice(0, 10))));
    else if (g !== null) ust.append(h('span', 'ny-gun', g <= 0 ? 'Bugün son gün' : g === 1 ? 'Yarın son gün' : g + ' gün kaldı'));
    kap.append(ust);
    const t = h('h3'), a = h('a', '', kisaBaslik(r)); a.href = ilanUrl(key); t.append(a); kap.append(t);
    // sana uyan kadrolar (adlı kadro varsa)
    const adli = x.kadrolar.filter((k) => k.ad);
    if (adli.length) {
      const ul = h('ul', 'ny-kadro');
      for (const k of adli.slice(0, 3)) {
        const li = h('li'); li.append(h('b', '', k.ad.length > 70 ? k.ad.slice(0, 69).replace(/\s+\S*$/, '') + '…' : k.ad));
        const ek = [k.adet ? k.adet + ' kişi' : '', k.puan !== null ? 'en az ' + puanYaz(k.puan) + ' puan' : ''].filter(Boolean).join(' · ');
        if (ek) li.append(h('span', '', ek));
        ul.append(li);
      }
      if (adli.length > 3) ul.append(h('li', 'ny-kadro-ek', '+' + (adli.length - 3) + ' kadro daha'));
      kap.append(ul);
    }
    const cip = h('div', 'ny-cipler'), n = kisiSayisi(r);
    if (n && !adli.length) cip.append(h('span', '', n + ' kişi'));
    if (x.kpsssiz) cip.append(h('span', 'iyi', 'KPSS şartı yok'));
    else if (!adli.length && x.kadrolar[0] && x.kadrolar[0].puan !== null) {
      const p = x.kadrolar[0].puan;
      cip.append(h('span', x.grup === 'yetmiyor' ? 'kotu' : 'iyi', 'En az ' + puanYaz(p) + ' puan' + (x.grup !== 'yetmiyor' && puan !== null ? ' ✓' : '')));
    }
    if (r.son_tarih) cip.append(h('span', '', 'Son gün ' + tarihYaz(r.son_tarih)));
    if (r._duzeltme) cip.append(h('span', 'uyari', 'Düzeltme yayımlanmış'));
    if (cip.children.length) kap.append(cip);
    if (x.neden && x.grup !== 'hemen') kap.append(h('p', 'ny-neden', x.neden + '.'));
    if (x.grup === 'yetmiyor') return kap;

    const d = h('details', 'ny-nasil'), sm = h('summary', '', 'Nasıl başvururum?'), ol = h('ol');
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
    d.append(sm, ol); if (dg.children.length) d.append(dg);
    d.addEventListener('toggle', () => { if (d.open) A('tikla', { a: 'nereye_nasil', x: r.kurum || '' }); });
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
    ozet.append(h('b', '', String(m.uygun.length)), ' kadroya senin puanınla yerleşilmiş', h('small', '', ' · son ' + DONEM_SAYI + ' tercih dönemi (' + donem + ')' + (m.kontenjan ? ', ' + m.kontenjan + ' kontenjan' : '')));
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

    kap.append(bolge('ny-hemen', 'Şimdi başvurabilirsin', 'Bölümün kadro şartında geçiyor' + (puan !== null ? ', puanın yetiyor' : '') + '. Son günü en yakın olan üstte.', gruplar.hemen,
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
    $('ny-tur').textContent = C.DUZEY[d].tur;
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

    const q = new URLSearchParams(location.search), pr = oku('kit-profil');
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
