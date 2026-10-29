/* KPSS Tercihi — katiplik klavye oyunları: Dosya Yetiştir (hız/refleks) ve Hata Avı (resmî hata türleri).
   Rekorlar yalnız tarayıcıda: localStorage 'kit-katip-oyun'. */
(function () {
  'use strict';
  var O = window.KatipOrtak, KK = window.KatipKlavye, $ = O.$, E = O.E;
  var rekor = O.oku('kit-katip-oyun', {}) || {};
  var duzen = O.klavyeTuru(), kelimeler = [], kume = {};
  function rekorYaz() {
    $('rek-dosya').textContent = 'Rekor: ' + (rekor.dosya || '—');
    $('rek-hata').textContent = 'Rekor: ' + (rekor.hata || '—');
  }
  function sec(d) { return d[Math.floor(Math.random() * d.length)]; }
  KK.Ses.acik = $('ses-ac').checked;
  $('ses-ac').onchange = function () { KK.Ses.acik = this.checked; };

  /* ---------- oyun seçimi ---------- */
  var oyun = 'dosya';
  function oyunSec(o) {
    oyun = o;
    [].forEach.call(document.querySelectorAll('.ko-kart'), function (b) { var a = b.dataset.oyun === o; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); });
    $('sahne-dosya').hidden = o !== 'dosya'; $('sahne-hata').hidden = o !== 'hata';
    if (o !== 'dosya') D.durdur();
    if (o !== 'hata') H.durdur();
  }
  [].forEach.call(document.querySelectorAll('.ko-kart'), function (b) { b.onclick = function () { oyunSec(b.dataset.oyun); O.A('tikla', { a: 'katip-oyun-sec', x: b.dataset.oyun }); }; });

  /* =================== DOSYA YETİŞTİR =================== */
  var D = (function () {
    var alan = $('d-alan'), giris = $('d-giris'), kartlar = [], hedef = null, cerceve = 0, son = 0, uret = 0;
    var st = null;
    function havuzSec(seviye) {
      var en = Math.min(4 + seviye, 13), alt = Math.max(2, Math.min(seviye + 1, 7));
      var h = kelimeler.slice(0, 600 + seviye * 300).filter(function (w) { return w.length >= alt && w.length <= en; });
      return h.length ? h : kelimeler.slice(0, 300);
    }
    function gosterge() {
      $('d-puan').textContent = st.puan; $('d-seviye').textContent = st.seviye; $('d-seri').textContent = '×' + st.carpan;
      $('d-hak').textContent = '❤❤❤'.slice(0, st.hak) + '♡♡♡'.slice(0, 3 - st.hak);
      $('d-hak').setAttribute('aria-label', 'Kalan hak ' + st.hak);
    }
    function kartUret() {
      var w = sec(havuzSec(st.seviye)), serit = Math.floor(Math.random() * 5);
      if (kartlar.some(function (k) { return k.serit === serit && k.x > 0.82; })) serit = (serit + 2) % 5;
      var el = E('div', 'ko-beyan'); el.appendChild(E('span', 'y')); el.appendChild(E('span', 'k', w));
      el.style.top = (8 + serit * 18) + '%';
      alan.appendChild(el);
      kartlar.push({ w: w, x: 1, el: el, serit: serit });
    }
    function cizKart(k) {
      var genislik = alan.clientWidth, sol = 96;
      k.el.style.transform = 'translateX(' + Math.round(sol + (genislik - sol - 20) * k.x - (1 - k.x) * 0) + 'px)';
    }
    function dongu(t) {
      if (!st || st.durum !== 'oyun') return;
      var dt = son ? Math.min(0.05, (t - son) / 1000) : 0; son = t;
      var hiz = 0.075 + st.seviye * 0.018; // alan genişliği / saniye
      uret -= dt;
      if (uret <= 0) { kartUret(); uret = Math.max(0.9, 2.6 - st.seviye * 0.18) * (0.75 + Math.random() * 0.5); }
      for (var i = kartlar.length - 1; i >= 0; i--) {
        var k = kartlar[i];
        k.x -= hiz * dt * (k.w.length > 9 ? 0.85 : 1);
        if (k.x <= 0) { kacti(k); continue; }
        cizKart(k);
      }
      cerceve = requestAnimationFrame(dongu);
    }
    function kaldir(k) { var i = kartlar.indexOf(k); if (i >= 0) kartlar.splice(i, 1); if (hedef === k) hedef = null; }
    function kacti(k) {
      kaldir(k);
      k.el.classList.add('kacti'); setTimeout(function () { k.el.remove(); }, 420);
      st.hak--; st.carpan = 1; st.kacan.push(k.w);
      KK.Ses.kayip();
      alan.classList.remove('sarsil'); void alan.offsetWidth; alan.classList.add('sarsil');
      if (giris.value && hedef === null) giris.value = '';
      gosterge();
      if (st.hak <= 0) bitti();
    }
    function yakala(k) {
      kaldir(k);
      st.puan += k.w.length * st.seviye * st.carpan; st.yakalanan++; st.harf += k.w.length;
      st.carpan = Math.min(5, st.carpan + (st.yakalanan % 3 === 0 ? 1 : 0));
      k.el.classList.add('yakalandi'); setTimeout(function () { k.el.remove(); }, 380);
      KK.Ses.basari();
      if (st.yakalanan % 8 === 0) { st.seviye++; KK.Ses.seviye(); alan.classList.remove('seviye'); void alan.offsetWidth; alan.classList.add('seviye'); }
      giris.value = ''; gosterge();
    }
    function vurgula() {
      kartlar.forEach(function (k) {
        var y = k === hedef ? giris.value.length : 0;
        k.el.classList.toggle('hedef', k === hedef);
        k.el.firstChild.textContent = k.w.slice(0, y); k.el.lastChild.textContent = k.w.slice(y);
      });
    }
    giris.addEventListener('keydown', function (e) {
      if (!st || st.durum !== 'oyun') return;
      if (e.key === 'Escape') { e.preventDefault(); durdur(); return; }
      if (e.key === 'Enter' || e.key === 'Tab') e.preventDefault();
      if (e.key.length === 1 && e.key !== ' ') st.kayit.ekle(hedef ? hedef.w[giris.value.length] || ' ' : null, e.key);
    });
    giris.addEventListener('input', function () {
      if (!st || st.durum !== 'oyun') { giris.value = ''; return; }
      var v = giris.value.replace(/\s+/g, '');
      if (v !== giris.value) giris.value = v;
      if (!v) { hedef = null; giris.classList.remove('yanlis'); vurgula(); return; }
      st.vurus++;
      if (!hedef || hedef.w.indexOf(v) !== 0) {
        var aday = kartlar.filter(function (k) { return k.w.indexOf(v) === 0; }).sort(function (a, b) { return a.x - b.x; })[0];
        hedef = aday || null;
      }
      if (!hedef) { st.hata++; st.carpan = 1; giris.classList.add('yanlis'); KK.Ses.hata(); gosterge(); }
      else giris.classList.remove('yanlis');
      if (hedef && hedef.w === v) yakala(hedef);
      vurgula();
    });
    ['paste', 'drop'].forEach(function (t) { giris.addEventListener(t, function (e) { e.preventDefault(); }); });
    function temizle() { kartlar.forEach(function (k) { k.el.remove(); }); kartlar = []; hedef = null; }
    function basla() {
      temizle(); cancelAnimationFrame(cerceve);
      st = { durum: 'oyun', puan: 0, seviye: 1, carpan: 1, hak: 3, yakalanan: 0, harf: 0, vurus: 0, hata: 0, kacan: [], bas: performance.now(), kayit: KK.kaydedici() };
      $('d-ortu').hidden = true; giris.value = ''; giris.disabled = false; giris.focus();
      son = 0; uret = 0.3; gosterge();
      cerceve = requestAnimationFrame(dongu);
      O.A('tikla', { a: 'katip-oyun', x: 'dosya-basla' });
    }
    function ortu(baslik, metin, dugme) { $('d-ortu-baslik').textContent = baslik; $('d-ortu-metin').textContent = metin; $('d-basla').textContent = dugme; $('d-ortu').hidden = false; $('d-basla').focus(); }
    function durdur() {
      if (!st || st.durum !== 'oyun') return;
      st.durum = 'duraklat'; cancelAnimationFrame(cerceve); son = 0;
      ortu('Duraklatıldı', 'Duruşmaya kısa bir ara verildi. Hazır olduğunda devam et.', 'Devam et');
    }
    function devam() { st.durum = 'oyun'; $('d-ortu').hidden = true; giris.focus(); son = 0; cerceve = requestAnimationFrame(dongu); }
    function bitti() {
      st.durum = 'bitti'; cancelAnimationFrame(cerceve); giris.disabled = true;
      var dk = (performance.now() - st.bas) / 60000, yeni = st.puan > (rekor.dosya || 0);
      if (yeni) { rekor.dosya = st.puan; O.yaz('kit-katip-oyun', rekor); rekorYaz(); }
      KK.birlestir(KK.analiz(st.kayit.vuruslar, duzen));
      var dogruluk = st.vurus ? Math.round((st.vurus - st.hata) / st.vurus * 100) : 100;
      ortu(yeni ? 'Yeni rekor: ' + st.puan + ' puan!' : 'Duruşma bitti · ' + st.puan + ' puan',
        st.yakalanan + ' beyan tutanağa geçti, ulaştığın seviye: ' + st.seviye + '. Hız ' + Math.round(st.yakalanan / Math.max(dk, 0.1)) + ' kelime/dk, doğruluk %' + dogruluk + '.' +
        (st.kacan.length ? ' Kaçan beyanlar: ' + st.kacan.slice(0, 5).join(', ') + '.' : ''), 'Tekrar oyna');
      setTimeout(temizle, 450);
      O.A('tikla', { a: 'katip-oyun-bitti', x: 'dosya', n: st.puan });
    }
    $('d-basla').onclick = function () { if (st && st.durum === 'duraklat') devam(); else basla(); };
    document.addEventListener('visibilitychange', function () { if (document.hidden) durdur(); });
    window.addEventListener('resize', function () { kartlar.forEach(cizKart); });
    return { durdur: durdur };
  })();

  /* =================== HATA AVI =================== */
  var H = (function () {
    var TUR = {
      'fazla-vurus': ['Fazla vuruş', 'Bir harf birden fazla yazılmış.'],
      'eksik-vurus': ['Eksik vuruş', 'Bir harf eksik yazılmış.'],
      'yer-degistirme': ['Harf yer değiştirme', 'Yan yana iki harfin yeri değişmiş.'],
      'karakter': ['Karakter hatası', 'Harf yerine noktalama işareti veya rakam yazılmış.'],
      'karisik': ['Karışık hata', 'Türkçe karakter yerine benzeri yazılmış ya da birden çok hata var.']
    };
    var TR = { 'ı': 'i', 'i': 'ı', 'ş': 's', 'ğ': 'g', 'ç': 'c', 'ö': 'o', 'ü': 'u', 's': 'ş', 'g': 'ğ', 'c': 'ç', 'o': 'ö', 'u': 'ü' };
    var TUR_SAYI = 15, SURE = 9;
    var st = null, zaman = 0;
    function boz(w, tur) {
      var i = 1 + Math.floor(Math.random() * (w.length - 2));
      if (tur === 'fazla-vurus') return w.slice(0, i) + w[i] + w.slice(i);
      if (tur === 'eksik-vurus') return w.slice(0, i) + w.slice(i + 1);
      if (tur === 'yer-degistirme') { for (var k = 0; k < 6 && w[i] === w[i + 1]; k++) i = Math.floor(Math.random() * (w.length - 1)); return w.slice(0, i) + w[i + 1] + w[i] + w.slice(i + 2); }
      if (tur === 'karakter') return w.slice(0, i) + sec(['.', ',', '1', '2', '0', ';']) + w.slice(i + 1);
      var yerler = []; for (var j = 0; j < w.length; j++) if (TR[w[j]]) yerler.push(j);
      if (!yerler.length) return w.slice(0, i) + w[i] + w.slice(i);
      var y = sec(yerler); return w.slice(0, y) + TR[w[y]] + w.slice(y + 1);
    }
    function tur() {
      var havuz = kelimeler.slice(0, 2500).filter(function (w) { return w.length >= 5 && w.length <= 12; });
      var bes = []; while (bes.length < 5) { var w = sec(havuz); if (bes.indexOf(w) < 0) bes.push(w); }
      var t = sec(Object.keys(TUR)), yanlis = Math.floor(Math.random() * 5), deneme = 0;
      if (t === 'karisik' && !/[ışğçöüsgcou]/.test(bes[yanlis])) t = 'fazla-vurus';
      var bozuk = boz(bes[yanlis], t);
      while ((bozuk === bes[yanlis] || kume[bozuk]) && deneme++ < 12) bozuk = boz(bes[yanlis], t);
      return { kelimeler: bes, yanlis: yanlis, bozuk: bozuk, tur: t };
    }
    function ciz() {
      var r = st.r, kap = $('h-kelimeler'); kap.textContent = '';
      r.kelimeler.forEach(function (w, i) {
        var b = E('button', 'ko-kelime'); b.type = 'button';
        b.appendChild(E('small', null, String(i + 1)));
        b.appendChild(E('span', null, i === r.yanlis ? r.bozuk : w));
        b.onclick = function () { secim(i); };
        kap.appendChild(b);
      });
      $('h-tur').textContent = (st.no + 1) + '/' + TUR_SAYI;
      $('h-geri').textContent = '';
      var g = $('h-giris'); g.value = ''; g.disabled = true; g.placeholder = 'Önce yanlış kelimenin numarasına bas (1–5)';
    }
    function yeniTur() {
      if (st.no >= TUR_SAYI) return bitti();
      st.r = tur(); st.asama = 'sec'; st.kalan = SURE; ciz();
      clearInterval(zaman);
      $('h-sure').textContent = st.kalan + ' sn';
      zaman = setInterval(function () { st.kalan--; $('h-sure').textContent = Math.max(0, st.kalan) + ' sn'; if (st.kalan <= 0) secim(-1); }, 1000);
    }
    function secim(i) {
      if (!st || st.asama !== 'sec') return;
      clearInterval(zaman);
      var r = st.r, butonlar = $('h-kelimeler').children, dogru = i === r.yanlis;
      butonlar[r.yanlis].classList.add('bulundu');
      if (i >= 0 && !dogru) butonlar[i].classList.add('yanlis-secim');
      st.turler[r.tur] = st.turler[r.tur] || [0, 0]; st.turler[r.tur][1]++;
      if (dogru) { st.puan += 100 + st.kalan * 10; st.bulunan++; st.turler[r.tur][0]++; KK.Ses.basari(); } else KK.Ses.hata();
      var t = TUR[r.tur];
      $('h-geri').textContent = (dogru ? 'Doğru! ' : i < 0 ? 'Süre doldu. ' : 'Yanlış kelime. ') + t[0] + ': ' + t[1] + ' “' + r.bozuk + '” yerine doğrusunu yaz ve Enter’a bas.';
      st.asama = 'yaz';
      var g = $('h-giris'); g.disabled = false; g.placeholder = 'Doğru yazımı gir ve Enter’a bas'; g.focus();
      $('h-puan').textContent = st.puan;
    }
    $('h-giris').addEventListener('keydown', function (e) {
      if (!st || st.asama !== 'yaz' || e.key !== 'Enter') return;
      e.preventDefault();
      var r = st.r, v = this.value.trim().toLocaleLowerCase('tr-TR'), ok = v === r.kelimeler[r.yanlis];
      if (ok) { st.puan += 50; st.duzeltilen++; } else KK.Ses.hata();
      $('h-geri').textContent = ok ? '+50 · doğru yazdın.' : 'Doğrusu: “' + r.kelimeler[r.yanlis] + '”.';
      $('h-puan').textContent = st.puan;
      st.asama = 'bekle'; this.disabled = true;
      st.no++;
      setTimeout(yeniTur, ok ? 650 : 1500);
    });
    document.addEventListener('keydown', function (e) {
      if (oyun !== 'hata' || !st || st.asama !== 'sec') return;
      if (/^[1-5]$/.test(e.key)) { e.preventDefault(); secim(Number(e.key) - 1); }
    });
    function basla() {
      st = { no: 0, puan: 0, bulunan: 0, duzeltilen: 0, turler: {} };
      $('h-ortu').hidden = true; $('h-puan').textContent = '0';
      yeniTur();
      O.A('tikla', { a: 'katip-oyun', x: 'hata-basla' });
    }
    function bitti() {
      clearInterval(zaman);
      var yeni = st.puan > (rekor.hata || 0);
      if (yeni) { rekor.hata = st.puan; O.yaz('kit-katip-oyun', rekor); rekorYaz(); }
      var zayif = Object.keys(st.turler).filter(function (t) { return st.turler[t][0] < st.turler[t][1]; }).map(function (t) { return TUR[t][0].toLocaleLowerCase('tr-TR'); });
      $('h-ortu-baslik').textContent = (yeni ? 'Yeni rekor: ' : 'Oyun bitti · ') + st.puan + ' puan';
      $('h-ortu-metin').textContent = TUR_SAYI + ' turda ' + st.bulunan + ' hatayı buldun, ' + st.duzeltilen + ' kelimeyi doğru yazdın.' +
        (zayif.length ? ' Kaçırdığın türler: ' + zayif.join(', ') + '. Sınavda bunların her biri 1 hatalı kelime sayılır.' : ' Bütün hata türlerini tanıdın!');
      $('h-basla').textContent = 'Tekrar oyna';
      $('h-ortu').hidden = false; $('h-basla').focus();
      $('h-kelimeler').textContent = ''; $('h-geri').textContent = ''; $('h-sure').textContent = '—';
      st.asama = 'bitti';
      O.A('tikla', { a: 'katip-oyun-bitti', x: 'hata', n: st.puan });
    }
    function durdur() { clearInterval(zaman); if (st && st.asama !== 'bitti') { st.asama = 'bitti'; $('h-ortu').hidden = false; $('h-basla').textContent = 'Yeniden başlat'; } }
    $('h-basla').onclick = basla;
    return { durdur: durdur };
  })();

  /* ---------- başlangıç ---------- */
  rekorYaz();
  $('d-basla').disabled = $('h-basla').disabled = true;
  Promise.all([KatipKutuphane.getir('zk2025'), KatipKutuphane.getir('ozgun')]).then(function (r) {
    kelimeler = O.kelimeSikligi(r).filter(function (w) { return w.length > 1; });
    kelimeler.forEach(function (w) { kume[w] = 1; });
    $('d-basla').disabled = $('h-basla').disabled = false;
    var istenen = new URLSearchParams(location.search).get('oyun');
    oyunSec(istenen === 'hata' ? 'hata' : 'dosya');
  }).catch(function () { $('d-ortu-metin').textContent = 'Kelimeler yüklenemedi. Sayfayı yenile.'; });
})();
