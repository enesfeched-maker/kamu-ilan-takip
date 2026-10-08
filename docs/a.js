/* KPSS Tercihi - çerezsiz, anonim ziyaret istatistiği. Bağımlılık yok.
   Ölçmez: DNT/GPC açıkken, yerel geliştirmede, file:, otomasyon tarayıcılarında. IP ve kalıcı kimlik yok;
   yalnız sekme ömürlü rastgele oturum kodu (sessionStorage 'kit-a') kullanılır. */
(function () {
  'use strict';
  var w = window, d = document, n = w.navigator || {}, L = w.location, URL_ = 'https://api.kpsstercihi.com/o';
  if (!L || !/^(www\.)?kpsstercihi\.com$/.test(L.hostname) || L.protocol !== 'https:') return;
  if (n.doNotTrack === '1' || n.doNotTrack === 'yes' || w.doNotTrack === '1' || n.msDoNotTrack === '1' || n.globalPrivacyControl === true || n.webdriver) return;
  if (!n.sendBeacon && typeof fetch !== 'function') return;

  var kuyruk = [], zamanlayici = 0, cur = { p: '', v: null, k: null }, sonSayfa = '', ilk = true, hata = 0;
  var sonEtk = Date.now(), aktifSn = 0, kaydirma = {}, lcp = 0, hizGitti = false;

  function oku(k) { try { return w.sessionStorage.getItem(k); } catch (e) { return null; } }
  function yaz(k, v) { try { w.sessionStorage.setItem(k, v); } catch (e) { /* depolama kapalı */ } }
  function rast() {
    var a = new Uint8Array(9), s = '';
    try { w.crypto.getRandomValues(a); } catch (e) { for (var i = 0; i < 9; i++) a[i] = Math.random() * 256; }
    for (var j = 0; j < 9; j++) s += (a[j] % 36).toString(36);
    return 'o' + s;
  }
  var oturum = null;
  try { oturum = JSON.parse(oku('kit-a')); } catch (e) { oturum = null; }
  if (!oturum || typeof oturum.s !== 'string') {
    var onceki = null;
    try { onceki = w.localStorage.getItem('kit-son-ziyaret'); } catch (e) { /* yok */ }
    oturum = { s: rast(), r: onceki ? 1 : 0, f: 0 };
    yaz('kit-a', JSON.stringify(oturum));
  }
  ilk = !oturum.f;

  function yol() { var p = L.pathname || '/'; return p.replace(/index\.html$/, '').slice(0, 120) || '/'; }
  function zarf() {
    var q = new URLSearchParams(L.search), ref = '';
    try { ref = d.referrer ? new URL(d.referrer).hostname : ''; } catch (e) { ref = ''; }
    if (ref === L.hostname || ref === 'www.' + L.hostname) ref = '';
    return { s: oturum.s, r: oturum.r, w: w.innerWidth || 0, l: n.language || '', ref: ref,
      u: { s: q.get('utm_source') || '', m: q.get('utm_medium') || '', c: q.get('utm_campaign') || '' } };
  }

  function gonder() {
    zamanlayici = 0;
    if (!kuyruk.length) return;
    var z = zarf();
    while (kuyruk.length) {
      var parca = kuyruk.splice(0, 20), govde;
      for (;;) { z.e = parca; govde = JSON.stringify(z); if (govde.length <= 4000 || parca.length < 2) break; kuyruk.unshift(parca.pop()); }
      var tamam = false;
      try { tamam = n.sendBeacon ? n.sendBeacon(URL_, govde) : false; } catch (e) { tamam = false; }
      if (!tamam && typeof fetch === 'function') { try { fetch(URL_, { method: 'POST', body: govde, keepalive: true, credentials: 'omit' }).catch(function () {}); } catch (e) { /* sessiz */ } }
    }
  }
  function sirala(hemen) {
    if (hemen || kuyruk.length >= 15) { clearTimeout(zamanlayici); gonder(); } else if (!zamanlayici) zamanlayici = setTimeout(gonder, 5000);
  }
  function olay(t, o, hemen) {
    var e = { t: t, p: cur.p || yol() };
    if (cur.v) e.v = cur.v;
    if (cur.k) e.k = cur.k;
    if (o) for (var a in o) e[a] = o[a];
    kuyruk.push(e);
    sirala(hemen);
  }
  function aktifYaz() {
    if (aktifSn > 0) { olay('aktif', { n: Math.min(aktifSn, 120) }); aktifSn = 0; }
  }
  function ekran(v, k) { aktifYaz(); cur = { p: yol(), v: v || null, k: k || null }; kaydirma = {}; }

  /* Genel API: kpssA('sayfa'|'ekran'|'tikla', {v,k,a,h,x,n}) */
  w.kpssA = function (t, o) {
    try {
      o = o || {};
      if (t === 'sayfa' || t === 'ekran') {
        var anahtar = yol() + '|' + (o.v || '') + '|' + (o.k || '');
        if (t === 'sayfa' && anahtar === sonSayfa) return;
        ekran(o.v, o.k);
        sonSayfa = anahtar;
        if (t === 'sayfa') {
          var e = { t: 'sayfa', p: cur.p };
          if (cur.v) e.v = cur.v;
          if (cur.k) e.k = cur.k;
          if (ilk) { e.f = 1; ilk = false; oturum.f = 1; yaz('kit-a', JSON.stringify(oturum)); }
          kuyruk.push(e);
          sirala(false);
        }
      } else if (t === 'tikla' && o.a) {
        var x = { a: String(o.a).slice(0, 32) };
        if (o.h != null) x.h = String(o.h).slice(0, 80);
        if (o.x != null) x.x = String(o.x).slice(0, 80);
        if (typeof o.n === 'number' && isFinite(o.n)) x.n = Math.round(o.n);
        olay('tikla', x, !!o.hemen);
      }
    } catch (e) { /* ölçüm sayfayı bozmaz */ }
  };

  /* 404 sayfası: yalnız bulunamayan adres bildirilir. */
  if (d.documentElement.hasAttribute('data-a404')) {
    kuyruk.push({ t: '404', p: yol() });
    gonder();
    return;
  }

  /* Genel tıklama: data-a="ad" data-a-h="hedef" data-a-x="değer" data-a-n="sayı" */
  function tikla(ev) {
    try {
      var el = ev.target && ev.target.closest ? ev.target.closest('[data-a]') : null;
      if (!el) return;
      var o = { a: el.getAttribute('data-a'), h: el.getAttribute('data-a-h'), x: el.getAttribute('data-a-x') }, nn = el.getAttribute('data-a-n');
      if (nn !== null && nn !== '' && isFinite(Number(nn))) o.n = Number(nn);
      if (el.tagName === 'A') o.hemen = true;
      w.kpssA('tikla', o);
    } catch (e) { /* sessiz */ }
  }
  d.addEventListener('click', tikla, true);
  d.addEventListener('auxclick', tikla, true);

  /* Etkin süre: sekme görünürken ve son 60 sn içinde etkileşim varsa 15 sn'lik adımlarla sayılır; paketler 60 sn'de bir gider. */
  function etk() { sonEtk = Date.now(); }
  ['pointerdown', 'keydown', 'touchstart', 'wheel', 'mousemove'].forEach(function (a) { d.addEventListener(a, etk, { passive: true }); });
  var adim = 0;
  setInterval(function () {
    if (d.hidden || Date.now() - sonEtk > 60000) return;
    aktifSn += 15;
    adim++;
    if (adim % 4 === 0) { aktifYaz(); sirala(true); }
  }, 15000);

  /* Kaydırma derinliği (25/50/75/100), ekran başına bir kez. Pencere/diyalog görünümlerinde ölçülmez. */
  var kaydirmaBekle = 0;
  w.addEventListener('scroll', function () {
    etk();
    if (kaydirmaBekle) return;
    kaydirmaBekle = setTimeout(function () {
      kaydirmaBekle = 0;
      if (cur.v === 'ilan' || cur.v === 'makale' || cur.v === 'karsilastir') return;
      var el = d.documentElement, toplam = el.scrollHeight, gorunen = w.innerHeight || 0;
      if (!toplam || toplam <= gorunen * 1.15) return;
      var yuzde = ((w.scrollY || el.scrollTop || 0) + gorunen) / toplam * 100;
      [25, 50, 75, 100].forEach(function (e) { if (yuzde >= (e === 100 ? 97 : e) && !kaydirma[e]) { kaydirma[e] = 1; olay('kaydirma', { n: e }); } });
    }, 400);
  }, { passive: true });

  /* JS hataları: en çok 5, yalnız bu siteden gelen betikler. */
  w.addEventListener('error', function (ev) {
    try {
      if (hata >= 5 || !ev || !ev.message || !ev.filename || ev.filename.indexOf(L.origin) !== 0) return;
      hata++;
      var dosya = ev.filename.replace(L.origin, '').replace(/\?.*$/, '');
      olay('hata', { x: String(ev.message).slice(0, 160), h: (dosya + ':' + (ev.lineno || 0)).slice(0, 80) });
    } catch (e) { /* sessiz */ }
  });

  /* Sayfa hızı: LCP + TTFB, açılıştan ~10 sn sonra bir kez. */
  try {
    new PerformanceObserver(function (l) { var s = l.getEntries(); if (s.length) lcp = Math.round(s[s.length - 1].startTime); }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) { /* desteklenmiyor */ }
  function hizYolla() {
    if (hizGitti) return;
    hizGitti = true;
    try {
      var nv = w.performance && w.performance.getEntriesByType ? w.performance.getEntriesByType('navigation')[0] : null;
      var ttfb = nv ? Math.round(nv.responseStart) : 0;
      if (lcp || ttfb) olay('hiz', { n: lcp || undefined, n2: ttfb || undefined });
    } catch (e) { /* sessiz */ }
  }
  setTimeout(hizYolla, 10000);

  function cikis() { hizYolla(); aktifYaz(); sirala(true); }
  d.addEventListener('visibilitychange', function () { if (d.hidden) cikis(); else etk(); });
  w.addEventListener('pagehide', cikis);

  /* Ana sayfa portal.js ile kendi görünümünü bildirir; bildirmeyen sayfalar için ilk sayfa görüntülemesi. */
  function baslat() { if (!sonSayfa) w.kpssA('sayfa', {}); }
  if (d.readyState === 'complete') setTimeout(baslat, 0); else d.addEventListener('DOMContentLoaded', baslat);
})();
