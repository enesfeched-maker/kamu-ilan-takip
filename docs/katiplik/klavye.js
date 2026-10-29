/* KPSS Tercihi — katiplik ortak klavye motoru: Türkçe Q/F düzenleri, parmak eşlemesi, ekran klavyesi,
   tuş istatistikleri (yalnız tarayıcıda, localStorage 'kit-katip-tus'), vuruş analizi ve sesler. */
(function () {
  'use strict';

  var PARMAK = ['Sol serçe', 'Sol yüzük', 'Sol orta', 'Sol işaret', 'Sol başparmak', 'Sağ başparmak', 'Sağ işaret', 'Sağ orta', 'Sağ yüzük', 'Sağ serçe'];
  var SATIR = {
    Q: ['1234567890*-', 'qwertyuıopğü', 'asdfghjklşi,', '<zxcvbnmöç.'],
    F: ['1234567890/-', 'fgğıodrnhpqw', 'uieaütkmlyşx', '<jövcçzsb.,']
  };
  // Sütuna göre parmak (dokunmatik yazım standardı); alt sırada '<' ve ilk harf serçe parmağa düşer.
  var SUTUN = [0, 1, 2, 3, 3, 6, 6, 7, 8, 9, 9, 9];
  var ALT = [0, 0, 1, 2, 3, 3, 6, 6, 7, 8, 9];
  var TEMEL = { Q: 'asdfjklş', F: 'uieakmly' };
  var CIKINTI = { Q: 'fj', F: 'ak' };

  var harita = {};
  Object.keys(SATIR).forEach(function (d) {
    var h = harita[d] = { ' ': { p: 4, s: 4 } };
    SATIR[d].forEach(function (satir, s) {
      satir.split('').forEach(function (c, i) { h[c] = { p: s === 3 ? ALT[i] : SUTUN[i], s: s, i: i }; });
    });
  });

  function duzen(d) { return d === 'F' ? 'F' : 'Q'; }
  function tus(c, d) { return harita[duzen(d)][String(c).toLocaleLowerCase('tr-TR')] || null; }
  function parmak(c, d) { var t = tus(c, d); return t ? t.p : -1; }

  /* ---------- ekran klavyesi ---------- */
  // ciz(kap, 'Q', { isi: {harf: 0..1}, etiket: {harf: 'metin'} }) → { vurgula(harf), temizle() }
  function ciz(kap, d, sec) {
    d = duzen(d); sec = sec || {};
    kap.textContent = '';
    kap.className = 'kk' + (sec.isi ? ' kk-isi' : '');
    kap.setAttribute('role', 'img');
    kap.setAttribute('aria-label', 'Türkçe ' + d + ' klavye' + (sec.isi ? ' ısı haritası' : ''));
    var dugmeler = {};
    SATIR[d].forEach(function (satir, s) {
      var sat = document.createElement('div');
      sat.className = 'kk-s kk-s' + s;
      satir.split('').forEach(function (c) {
        var b = document.createElement('span'), t = harita[d][c];
        b.className = 'kk-t kk-p' + t.p + (TEMEL[d].indexOf(c) >= 0 ? ' kk-temel' : '') + (CIKINTI[d].indexOf(c) >= 0 ? ' kk-cik' : '');
        b.textContent = c.toLocaleUpperCase('tr-TR');
        if (sec.isi && sec.isi[c] != null) { b.style.setProperty('--isi', Math.max(0, Math.min(1, sec.isi[c])).toFixed(3)); b.classList.add('kk-olcu'); }
        if (sec.etiket && sec.etiket[c] != null) b.title = c.toLocaleUpperCase('tr-TR') + ': ' + sec.etiket[c];
        sat.appendChild(b); dugmeler[c] = b;
      });
      kap.appendChild(sat);
    });
    var bosluk = document.createElement('div');
    bosluk.className = 'kk-s kk-s4';
    var bt = document.createElement('span'); bt.className = 'kk-t kk-bosluk kk-p4'; bt.textContent = 'boşluk';
    bosluk.appendChild(bt); kap.appendChild(bosluk); dugmeler[' '] = bt;
    var onceki = null;
    return {
      vurgula: function (c) {
        if (onceki) onceki.classList.remove('kk-sira');
        onceki = dugmeler[String(c).toLocaleLowerCase('tr-TR')] || null;
        if (onceki) onceki.classList.add('kk-sira');
      },
      temizle: function () { if (onceki) onceki.classList.remove('kk-sira'); onceki = null; }
    };
  }

  /* ---------- vuruş kaydı ve analiz ---------- */
  // Kaydedici: her vuruşta ekle(beklenen, yazilan); beklenen bilinmiyorsa null.
  function kaydedici() {
    var v = [], son = 0;
    return {
      vuruslar: v,
      ekle: function (beklenen, yazilan) {
        var t = performance.now(), ara = son ? t - son : 0;
        son = t;
        v.push({ b: beklenen, y: yazilan, ms: ara > 0 && ara < 2000 ? ara : 0 });
      },
      sifirla: function () { v.length = 0; son = 0; }
    };
  }

  function analiz(vuruslar, d, ekHatalar) {
    var tuslar = {}, parmaklar = PARMAK.map(function () { return { n: 0, ms: 0, h: 0 }; }), ikili = {};
    var onceki = null;
    vuruslar.forEach(function (x) {
      var c = String(x.b != null ? x.b : x.y).toLocaleLowerCase('tr-TR');
      if (!c || c.length !== 1) { onceki = null; return; }
      var t = tuslar[c] || (tuslar[c] = { n: 0, h: 0, ms: 0, msn: 0 });
      t.n++;
      var hata = x.b != null && x.y !== x.b;
      if (hata) t.h++;
      if (x.ms) { t.ms += x.ms; t.msn++; }
      var p = parmak(c, d);
      if (p >= 0) { parmaklar[p].n++; if (hata) parmaklar[p].h++; if (x.ms) parmaklar[p].ms += x.ms; }
      if (onceki && c !== ' ' && onceki !== ' ' && x.ms) {
        var k = onceki + c, b = ikili[k] || (ikili[k] = { n: 0, ms: 0 });
        b.n++; b.ms += x.ms;
      }
      onceki = c;
    });
    (ekHatalar || []).forEach(function (c) { var t = tuslar[c] || (tuslar[c] = { n: 1, h: 0, ms: 0, msn: 0 }); t.h++; var p = parmak(c, d); if (p >= 0) parmaklar[p].h++; });
    var parmakOrt = parmaklar.map(function (p, i) { return { ad: PARMAK[i], n: p.n, h: p.h, ort: p.n ? Math.round(p.ms / p.n) : 0 }; });
    var ikililer = Object.keys(ikili).filter(function (k) { return ikili[k].n >= 2; })
      .map(function (k) { return { k: k, n: ikili[k].n, ort: Math.round(ikili[k].ms / ikili[k].n) }; })
      .sort(function (a, b) { return b.ort - a.ort; });
    return { tuslar: tuslar, parmaklar: parmakOrt, ikililer: ikililer };
  }

  // Asıl ve yazılan kelimeyi harf harf hizalayıp kaçırılan/yanlış basılan asıl harfleri döndürür.
  function harfHatalari(a, b) {
    a = a || ''; b = b || '';
    var n = a.length, m = b.length, d = [];
    for (var i = 0; i <= n; i++) { d.push([i]); for (var j = 1; j <= m; j++) d[i].push(i ? 0 : j); }
    for (i = 1; i <= n; i++) for (j = 1; j <= m; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    var sonuc = [];
    i = n; j = m;
    while (i > 0 || j > 0) {
      if (i && j && d[i][j] === d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)) { if (a[i - 1] !== b[j - 1]) sonuc.push(a[i - 1]); i--; j--; }
      else if (i && d[i][j] === d[i - 1][j] + 1) { sonuc.push(a[i - 1]); i--; }
      else j--;
    }
    return sonuc;
  }

  /* ---------- kalıcı tuş istatistikleri ---------- */
  var ANAHTAR = 'kit-katip-tus';
  function oku() { try { var v = JSON.parse(localStorage.getItem(ANAHTAR)); return v && typeof v === 'object' ? v : {}; } catch (e) { return {}; } }
  function birlestir(a) {
    var v = oku();
    Object.keys(a.tuslar).forEach(function (c) {
      if (!/^[a-zçğıöşü]$/.test(c)) return;
      var t = a.tuslar[c], x = v[c] || [0, 0, 0, 0];
      x[0] += t.n; x[1] += t.h; x[2] += t.ms; x[3] += t.msn;
      // Eski veriyi yavaşça unut: en çok 600 vuruş tutulur
      if (x[0] > 600) { var o = 600 / x[0]; x = [600, Math.round(x[1] * o), Math.round(x[2] * o), Math.round(x[3] * o)]; }
      v[c] = x;
    });
    try { localStorage.setItem(ANAHTAR, JSON.stringify(v)); } catch (e) { /* depolama kapalı */ }
    return v;
  }
  // Zayıf tuşlar: hata oranı ve yavaşlık birlikte; yeterli veri yoksa boş döner.
  function zayiflar(adet) {
    var v = oku(), harfler = Object.keys(v).filter(function (c) { return v[c][0] >= 8; });
    if (harfler.length < 6) return [];
    var hizlar = harfler.map(function (c) { return v[c][3] ? v[c][2] / v[c][3] : 0; }).filter(Boolean);
    var ortHiz = hizlar.reduce(function (s, x) { return s + x; }, 0) / (hizlar.length || 1);
    return harfler.map(function (c) {
      var x = v[c], oran = x[1] / x[0], hiz = x[3] ? x[2] / x[3] : ortHiz;
      return { c: c, oran: oran, ms: Math.round(hiz), puan: oran * 4 + Math.max(0, hiz / ortHiz - 1) };
    }).sort(function (a, b) { return b.puan - a.puan; }).slice(0, adet || 6);
  }

  /* ---------- analiz paneli ---------- */
  function E(t, s, y) { var e = document.createElement(t); if (s) e.className = s; if (y != null) e.textContent = y; return e; }
  // analizCiz(kap, analizSonucu, 'Q') → ısı haritası (hata/hız seçmeli), parmak hızları, yavaş ikililer
  function analizCiz(kap, a, d) {
    kap.textContent = '';
    var harfler = Object.keys(a.tuslar).filter(function (c) { return /^[a-zçğıöşü]$/.test(c); });
    if (harfler.length < 4) { kap.appendChild(E('p', 'muted', 'Analiz için biraz daha uzun yazman gerekiyor.')); return; }
    var ust = E('div', 'ka-ust'), sec = E('div', 'segment'), mod = 'hata';
    [['hata', 'Hatalı tuşlar'], ['hiz', 'Yavaş tuşlar']].forEach(function (x) {
      var b = E('button', 'tab' + (x[0] === mod ? ' secili' : ''), x[1]); b.type = 'button';
      b.onclick = function () { mod = x[0]; [].forEach.call(sec.children, function (c) { c.classList.toggle('secili', c === b); }); isiCiz(); };
      sec.appendChild(b);
    });
    ust.appendChild(E('h3', null, 'Klavye ısı haritası')); ust.appendChild(sec);
    var kk = E('div'), aciklama = E('p', 'not-kucuk');
    kap.appendChild(ust); kap.appendChild(kk); kap.appendChild(aciklama);
    function isiCiz() {
      var isi = {}, et = {}, maks = 0;
      harfler.forEach(function (c) {
        var t = a.tuslar[c], v = mod === 'hata' ? t.h / t.n : (t.msn ? t.ms / t.msn : 0);
        isi[c] = v; maks = Math.max(maks, v);
        et[c] = mod === 'hata' ? t.h + ' hata / ' + t.n + ' vuruş' : (t.msn ? Math.round(t.ms / t.msn) + ' ms' : '—');
      });
      Object.keys(isi).forEach(function (c) { isi[c] = maks ? isi[c] / maks : 0; });
      ciz(kk, d, { isi: isi, etiket: et });
      aciklama.textContent = mod === 'hata' ? 'Koyu renk, o tuşta daha çok hata yaptığını gösterir. Tuşun üzerine gelince sayıları görürsün.' : 'Koyu renk, o tuşa basmadan önce daha uzun beklediğini (yavaşlığı) gösterir.';
    }
    isiCiz();
    var alt = E('div', 'ka-alt'), pk = E('div', 'ka-blok');
    pk.appendChild(E('h3', null, 'Parmak hızı (ortalama ms)'));
    var gecerli = a.parmaklar.filter(function (p, i) { return p.n >= 3 && i !== 4 && i !== 5; });
    var enYavas = Math.max.apply(null, gecerli.map(function (p) { return p.ort; }).concat([1]));
    gecerli.forEach(function (p) {
      var sat = E('div', 'ka-cubuk');
      sat.appendChild(E('span', null, p.ad));
      var c = E('i'); c.style.width = Math.round(p.ort / enYavas * 100) + '%'; var k = E('b'); k.appendChild(c); sat.appendChild(k);
      sat.appendChild(E('em', null, p.ort + ' ms' + (p.h ? ' · ' + p.h + ' hata' : '')));
      pk.appendChild(sat);
    });
    var ik = E('div', 'ka-blok');
    ik.appendChild(E('h3', null, 'En yavaş harf geçişleri'));
    var liste = E('ol', 'ka-ikili');
    a.ikililer.slice(0, 6).forEach(function (x) { var li = E('li'); li.appendChild(E('code', null, x.k)); li.appendChild(E('span', null, x.ort + ' ms · ' + x.n + ' kez')); liste.appendChild(li); });
    if (!a.ikililer.length) liste.appendChild(E('li', 'muted', 'Yeterli veri yok.'));
    ik.appendChild(liste);
    ik.appendChild(E('p', 'not-kucuk', 'Bu geçişleri içeren kelimeleri ağır ve ritimli tekrar etmek hızını en çok artıran çalışmadır.'));
    alt.appendChild(pk); alt.appendChild(ik);
    kap.appendChild(alt);
  }

  /* ---------- sesler (WebAudio ile üretilir, dosya yok) ---------- */
  var ctx = null;
  function baglam() { if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)(); if (ctx.state === 'suspended') ctx.resume(); return ctx; }
  function ton(f, sure, tip, ses, gecikme) {
    try {
      var c = baglam(), o = c.createOscillator(), g = c.createGain(), t = c.currentTime + (gecikme || 0);
      o.type = tip || 'sine'; o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(ses || 0.15, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + sure);
      o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + sure + 0.02);
    } catch (e) { /* ses desteklenmiyor */ }
  }
  var Ses = {
    acik: true,
    tik: function () {
      if (!Ses.acik) return;
      try {
        var c = baglam(), b = c.createBuffer(1, c.sampleRate * 0.025, c.sampleRate), v = b.getChannelData(0);
        for (var i = 0; i < v.length; i++) v[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / v.length, 6);
        var n = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
        n.buffer = b; f.type = 'bandpass'; f.frequency.value = 2500 + Math.random() * 700; g.gain.value = 0.3;
        n.connect(f); f.connect(g); g.connect(c.destination); n.start();
      } catch (e) { /* ses desteklenmiyor */ }
    },
    hata: function () { if (Ses.acik) ton(170, 0.12, 'square', 0.06); },
    basari: function () { if (Ses.acik) { ton(660, 0.12, 'sine', 0.12); ton(990, 0.18, 'sine', 0.12, 0.1); } },
    seviye: function () { if (Ses.acik) { ton(523, 0.1, 'triangle', 0.12); ton(659, 0.1, 'triangle', 0.12, 0.09); ton(784, 0.22, 'triangle', 0.12, 0.18); } },
    kayip: function () { if (Ses.acik) { ton(330, 0.15, 'sawtooth', 0.05); ton(220, 0.25, 'sawtooth', 0.05, 0.12); } }
  };

  window.KatipKlavye = {
    PARMAK: PARMAK, SATIR: SATIR, TEMEL: TEMEL,
    tus: tus, parmak: parmak, ciz: ciz,
    kaydedici: kaydedici, analiz: analiz, harfHatalari: harfHatalari, analizCiz: analizCiz,
    istatistik: oku, birlestir: birlestir, zayiflar: zayiflar,
    Ses: Ses
  };
})();
