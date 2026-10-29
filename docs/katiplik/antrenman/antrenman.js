/* KPSS Tercihi — kelime antrenmanı: hız testi, zayıf tuşlar, sık hukuk kelimeleri, uzun kelimeler, terimler, rakamlar.
   Kelimeler tek satırda akar; boşlukla kontrol edilir. Rekorlar yalnız tarayıcıda: localStorage 'kit-katip-antrenman'. */
(function () {
  'use strict';
  var O = window.KatipOrtak, KK = window.KatipKlavye, $ = O.$, E = O.E;
  var MOD = {
    hiz: { ust: 'Klavye hız testi', baslik: 'En sık 300 kelimeyle hız ölç', sure: 60 },
    zayif: { ust: 'Zayıf tuşlarım', baslik: 'Zayıf harflerini içeren kelimeler', sure: 60 },
    hedef: { ust: 'Sık kullanılan hukuk kelimeleri', baslik: 'Sınav metinlerinin en sık kelimeleri', sure: 120 },
    uzun: { ust: 'Uzun kelimeler', baslik: 'On bir harf ve üzeri kelimeler', sure: 60 },
    terim: { ust: 'Hukuk terimleri', baslik: 'Kalemde her gün yazılan terimler', sure: 60 },
    rakam: { ust: 'Rakam ve sayı', baslik: 'Esas numaraları, yıllar ve tutarlar', sure: 60 }
  };
  var veri = O.oku('kit-katip-antrenman', {}) || {};
  veri.rekor = veri.rekor || {}; veri.ayar = Object.assign({ mod: 'hiz', adet: 200, sure: {} }, veri.ayar || {});
  var duzen = O.klavyeTuru(), mod = veri.ayar.mod, sik = [], s = null, zaman = 0;

  function havuz() {
    if (mod === 'hiz') return sik.slice(0, 300);
    if (mod === 'hedef') return sik.slice(0, veri.ayar.adet);
    if (mod === 'uzun') return sik.slice(0, 6000).filter(function (w) { return w.length >= 11; }).slice(0, 300);
    if (mod === 'terim') return O.TERIMLER;
    if (mod === 'rakam') {
      var r = [];
      for (var i = 0; i < 300; i++) {
        var t = i % 4;
        r.push(t === 0 ? String(2020 + Math.floor(Math.random() * 7)) : t === 1 ? String(Math.floor(Math.random() * 2000) + 1) : t === 2 ? String(Math.floor(Math.random() * 90000) + 1000) : String(Math.floor(Math.random() * 99) + 1));
      }
      return r;
    }
    var z = KK.zayiflar(6).map(function (x) { return x.c; });
    if (!z.length) return [];
    return sik.slice(0, 5000).map(function (w) { var n = 0; for (var i = 0; i < w.length; i++) if (z.indexOf(w[i]) >= 0) n++; return [w, n / w.length]; })
      .filter(function (x) { return x[1] >= 0.25 && x[0].length >= 3; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 250).map(function (x) { return x[0]; });
  }

  /* ---------- hazırlık ---------- */
  function modSec(m) {
    mod = MOD[m] ? m : 'hiz'; veri.ayar.mod = mod; O.yaz('kit-katip-antrenman', veri);
    [].forEach.call(document.querySelectorAll('#a-modlar .kt-mod'), function (b) { var a = b.dataset.mod === mod; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); });
    $('a-ust').textContent = MOD[mod].ust;
    $('adet-sec').hidden = mod !== 'hedef';
    segment('adet-sec', veri.ayar.adet);
    segment('sure-sec', veri.ayar.sure[mod] || MOD[mod].sure);
    hazirla();
  }
  function segment(id, v) { [].forEach.call(document.querySelectorAll('#' + id + ' .tab'), function (b) { var a = Number(b.dataset.v) === v; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); }); }
  function hazirla() {
    clearInterval(zaman);
    var h = havuz(), sure = veri.ayar.sure[mod] || MOD[mod].sure;
    $('a-sonuc').hidden = true;
    var rek = veri.rekor[mod + (mod === 'hedef' ? veri.ayar.adet : '')];
    $('a-baslik').textContent = MOD[mod].baslik + (rek ? ' · rekorun ' + rek + ' net/dk' : '');
    if (!h.length) {
      $('a-satir').textContent = 'Zayıf tuşlarını belirlemek için önce hız testi, ders veya sınav simülasyonuyla en az birkaç yüz vuruş yapmalısın.';
      $('a-giris').disabled = true; s = null; return;
    }
    var k = [];
    while (k.length < sure / 60 * 110) k = k.concat(O.karistir(h.slice()));
    s = { kelimeler: k, i: 0, sonuc: [], sure: sure, bas: 0, kalan: sure, kayit: KK.kaydedici(), bitti: false };
    var kap = $('a-satir'); kap.textContent = ''; kap.scrollTop = 0;
    k.forEach(function (w, i) { kap.appendChild(E('span', i === 0 ? 'simdi' : null, w)); kap.appendChild(document.createTextNode(' ')); });
    var g = $('a-giris'); g.disabled = false; g.value = ''; g.classList.remove('yanlis');
    g.placeholder = 'Yazmaya başladığında süre işler…';
    $('a-sure').textContent = O.sureYaz(sure); $('a-hiz').textContent = '0'; $('a-dogruluk').textContent = '—'; $('a-hata').textContent = '0';
    g.focus({ preventScroll: true });
  }

  /* ---------- yazım ---------- */
  function basla() {
    s.bas = performance.now();
    zaman = setInterval(function () {
      s.kalan = Math.max(0, s.sure - (performance.now() - s.bas) / 1000);
      $('a-sure').textContent = O.sureYaz(s.kalan);
      gosterge();
      if (s.kalan <= 0) bitir();
    }, 200);
    O.A('tikla', { a: 'katip-antrenman', x: mod });
  }
  function gosterge() {
    var gecen = Math.max(6, s.sure - s.kalan) / 60, d = s.sonuc.filter(function (x) { return x.d; }).length, n = s.sonuc.length;
    $('a-hiz').textContent = Math.round(d / gecen);
    $('a-dogruluk').textContent = n ? '%' + Math.round(d / n * 100) : '—';
    $('a-hata').textContent = n - d;
  }
  function kelimeGonder(yazilan) {
    var w = s.kelimeler[s.i], sp = $('a-satir').children[s.i];
    var d = yazilan === w;
    s.sonuc.push({ w: w, y: yazilan, d: d });
    sp.className = d ? 'dogru' : 'yanlis';
    s.i++;
    var sonraki = $('a-satir').children[s.i];
    if (sonraki) {
      sonraki.className = 'simdi';
      var kap = $('a-satir'), satir = parseFloat(getComputedStyle(kap).lineHeight) || 34;
      if (sonraki.offsetTop - kap.scrollTop > satir * 1.5) kap.scrollTop = sonraki.offsetTop - satir;
    }
    gosterge();
  }
  $('a-giris').addEventListener('keydown', function (e) {
    if (!s || s.bitti) return;
    if (e.key === 'Escape') { e.preventDefault(); hazirla(); return; }
    if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); return; }
    if ((e.ctrlKey || e.metaKey) && !e.altKey) { if (/^[vxyz]$/i.test(e.key)) e.preventDefault(); return; }
    if (e.key.length === 1) {
      if (!s.bas) basla();
      var w = s.kelimeler[s.i] || '', v = this.value;
      s.kayit.ekle(v.length < w.length ? w[v.length] : ' ', e.key);
    }
  });
  $('a-giris').addEventListener('input', function () {
    if (!s || s.bitti) return;
    var v = this.value;
    if (/\s/.test(v)) {
      var parca = v.split(/\s+/);
      if (parca[0]) kelimeGonder(parca[0]);
      this.value = parca.slice(1).join('');
    }
    var w = s.kelimeler[s.i] || '';
    this.classList.toggle('yanlis', this.value.length > 0 && w.indexOf(this.value) !== 0);
  });
  ['paste', 'drop'].forEach(function (t) { $('a-giris').addEventListener(t, function (e) { e.preventDefault(); }); });

  /* ---------- sonuç ---------- */
  function bitir() {
    if (!s || s.bitti) return;
    clearInterval(zaman); s.bitti = true;
    var g = $('a-giris'); g.disabled = true;
    var yarim = g.value.trim(); g.value = '';
    var d = s.sonuc.filter(function (x) { return x.d; }), n = s.sonuc.length, dk = s.sure / 60;
    var net = Math.round(d.length / dk), vurus = s.kayit.vuruslar.length;
    var harf = d.reduce(function (t, x) { return t + x.w.length + 1; }, 0);
    var anahtar = mod + (mod === 'hedef' ? veri.ayar.adet : ''), eski = veri.rekor[anahtar] || 0;
    var rekor = net > eski;
    if (rekor) veri.rekor[anahtar] = net;
    veri.gecmis = [{ t: Date.now(), m: anahtar, net: net, n: n, h: n - d.length, s: s.sure }].concat(veri.gecmis || []).slice(0, 100);
    O.yaz('kit-katip-antrenman', veri);
    $('r-baslik').textContent = MOD[mod].ust + (rekor && eski ? ' · yeni rekor!' : '');
    $('r-alt').textContent = O.sureYaz(s.sure) + ' · Türkçe ' + duzen + (yarim ? ' · yarım kalan son kelime sayılmadı' : '') + (eski && !rekor ? ' · rekorun ' + eski : '');
    $('r-net').textContent = net;
    var kutular = $('r-kutular'); kutular.textContent = '';
    [[d.length, 'Doğru kelime'], [n - d.length, 'Hatalı kelime'], [n ? '%' + Math.round(d.length / n * 100) : '—', 'Doğruluk'],
      [Math.round(harf / 5 / dk), 'Standart hız (5 vuruş = 1 kelime)'], [Math.round(vurus / dk), 'Vuruş / dakika']].forEach(function (x) {
      var k = E('div', 'kutu'); k.appendChild(E('b', null, String(x[0]))); k.appendChild(E('span', null, x[1])); kutular.appendChild(k);
    });
    var hl = $('r-hatalar'); hl.textContent = '';
    var yanlis = s.sonuc.filter(function (x) { return !x.d; });
    if (yanlis.length) {
      hl.appendChild(E('h3', null, 'Hatalı kelimeler'));
      var ul = E('ul');
      yanlis.slice(0, 24).forEach(function (x) { var li = E('li'); li.appendChild(E('del', null, x.y)); li.appendChild(document.createTextNode(' → ')); li.appendChild(E('ins', null, x.w)); ul.appendChild(li); });
      hl.appendChild(ul);
      // Ana sayfadaki "Hatalı kelimelerim" defterine de ekle
      var kat = O.oku('kit-katip', {}) || {}; kat.hatalar = kat.hatalar || {};
      yanlis.forEach(function (x) { if (/^[a-zçğıöşü]+$/.test(x.w)) kat.hatalar[x.w] = (kat.hatalar[x.w] || 0) + 1; });
      O.yaz('kit-katip', kat);
    }
    var a = KK.analiz(s.kayit.vuruslar, duzen);
    KK.birlestir(a);
    KK.analizCiz($('r-analiz'), a, duzen);
    $('a-sonuc').hidden = false;
    $('a-sonuc').scrollIntoView({ behavior: 'smooth', block: 'start' });
    profilCiz();
    O.A('tikla', { a: 'katip-antrenman-bitti', x: anahtar, n: net });
    s.paylas = MOD[mod].ust + ': ' + O.sureYaz(s.sure) + ' sürede dakikada ' + net + ' net kelime (' + (n ? Math.round(d.length / n * 100) : 0) + '% doğruluk).';
  }

  /* ---------- tuş profili ---------- */
  function profilCiz() {
    var p = $('profil'); p.textContent = '';
    var v = KK.istatistik(), harfler = Object.keys(v).filter(function (c) { return v[c][0] >= 5; });
    if (harfler.length < 6) { p.appendChild(E('p', 'muted', 'Henüz yeterli vuruş yok. Bir hız testi yaptığında hangi tuşlarda zorlandığın burada görünür.')); return; }
    var isi = {}, et = {}, maks = 0;
    harfler.forEach(function (c) { var o = v[c][1] / v[c][0]; isi[c] = o; maks = Math.max(maks, o); et[c] = '%' + (o * 100).toFixed(1) + ' hata · ' + (v[c][3] ? Math.round(v[c][2] / v[c][3]) + ' ms' : '—'); });
    Object.keys(isi).forEach(function (c) { isi[c] = maks ? isi[c] / maks : 0; });
    var kk = E('div'); p.appendChild(kk); KK.ciz(kk, duzen, { isi: isi, etiket: et });
    var z = KK.zayiflar(6);
    if (z.length) {
      var sat = E('p', 'ka-zayif');
      sat.appendChild(document.createTextNode('En zayıf tuşların: '));
      z.forEach(function (x) { sat.appendChild(E('code', null, x.c.toLocaleUpperCase('tr-TR'))); sat.appendChild(document.createTextNode(' ')); });
      var b = E('button', 'btn btn-ikinci', 'Bu tuşları çalış'); b.type = 'button'; b.onclick = function () { modSec('zayif'); $('oyun').scrollIntoView({ behavior: 'smooth' }); };
      p.appendChild(sat); p.appendChild(b);
    }
  }

  /* ---------- olaylar ---------- */
  [].forEach.call(document.querySelectorAll('#a-modlar .kt-mod'), function (b) { b.onclick = function () { modSec(b.dataset.mod); O.A('tikla', { a: 'katip-antrenman-mod', x: b.dataset.mod }); }; });
  [].forEach.call(document.querySelectorAll('#sure-sec .tab'), function (b) { b.onclick = function () { veri.ayar.sure[mod] = Number(b.dataset.v); segment('sure-sec', veri.ayar.sure[mod]); O.yaz('kit-katip-antrenman', veri); hazirla(); }; });
  [].forEach.call(document.querySelectorAll('#adet-sec .tab'), function (b) { b.onclick = function () { veri.ayar.adet = Number(b.dataset.v); segment('adet-sec', veri.ayar.adet); O.yaz('kit-katip-antrenman', veri); hazirla(); }; });
  [].forEach.call(document.querySelectorAll('#duzen-sec .tab'), function (b) { b.onclick = function () { duzen = b.dataset.v; O.klavyeKaydet(duzen); segment2(); hazirla(); profilCiz(); }; });
  function segment2() { [].forEach.call(document.querySelectorAll('#duzen-sec .tab'), function (b) { var a = b.dataset.v === duzen; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); }); }
  $('a-yeniden').onclick = hazirla;
  $('r-tekrar').onclick = function () { hazirla(); $('oyun').scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  $('r-paylas').onclick = function () {
    if (!s || !s.paylas) return;
    var url = 'https://kpsstercihi.com/katiplik/antrenman/?utm_source=paylas&utm_medium=katiplik', b = this, metin = s.paylas + ' Sen de dene:';
    if (navigator.share) { navigator.share({ title: 'Klavye hız testi', text: metin, url: url }).catch(function () {}); return; }
    try { navigator.clipboard.writeText(metin + ' ' + url).then(function () { b.textContent = 'Kopyalandı!'; setTimeout(function () { b.textContent = 'Sonucu paylaş'; }, 1600); }); } catch (e) { /* pano kapalı */ }
  };
  document.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !$('a-sonuc').hidden && e.target.tagName !== 'BUTTON') { e.preventDefault(); $('r-tekrar').click(); } });

  segment2();
  var istenen = new URLSearchParams(location.search).get('mod');
  KatipKutuphane.getir('zk2025').then(function (r1) {
    return Promise.all([r1, KatipKutuphane.getir('ozgun'), KatipKutuphane.getir('tck'), KatipKutuphane.getir('iik')]);
  }).then(function (r) {
    sik = O.kelimeSikligi(r).filter(function (w) { return w.length > 1; });
    modSec(MOD[istenen] ? istenen : mod);
    profilCiz();
  }).catch(function () { $('a-satir').textContent = 'Kelimeler yüklenemedi. Sayfayı yenile.'; });
})();
