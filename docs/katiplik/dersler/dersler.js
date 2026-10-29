/* KPSS Tercihi — on parmak klavye dersleri. Dersler Türkçe Q/F düzeninden üretilir; kelime alıştırmaları
   resmî sınav ve özgün metinlerden seçilir. İlerleme yalnız tarayıcıda: localStorage 'kit-katip-ders'. */
(function () {
  'use strict';
  var O = window.KatipOrtak, KK = window.KatipKlavye, $ = O.$, E = O.E;
  var TERIMLER = O.TERIMLER;

  var duzen = O.klavyeTuru();
  var ilerleme = O.oku('kit-katip-ders', {}) || {};
  var kelimeler = [], sikKelimeler = [], sinavMetni = [];
  var DERSLER = [], aktif = 0, adim = 0;
  var klavye = null;
  var ayar = Object.assign({ ses: false, klavye: true }, O.oku('kit-katip-ders-ayar', {}));

  function harfler(s) { return s.split('').filter(function (c) { return /[a-zçğıöşü]/.test(c); }); }
  function el(c) { var p = KK.parmak(c, duzen); return p <= 4 ? 'sol' : 'sag'; }

  /* ---------- ders planı ---------- */
  function planla() {
    var S = KK.SATIR[duzen], temel = harfler(S[2]), ust = harfler(S[1]), alt = harfler(S[3]);
    var anaTemel = KK.TEMEL[duzen].split('');
    var bol = function (dizi, taraf) { return dizi.filter(function (c) { return el(c) === taraf; }); };
    var tr = ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü', 'i'];
    DERSLER = [
      { ad: 'Temel sıra: sol el', tur: 'harf', yeni: bol(anaTemel, 'sol'), aciklama: 'Sol elin dört parmağı temel konumda. Her tuşa kendi parmağıyla bas.' },
      { ad: 'Temel sıra: sağ el', tur: 'harf', yeni: bol(anaTemel, 'sag'), aciklama: 'Sağ elin dört parmağı temel konumda.' },
      { ad: 'Temel sıra: orta tuşlar', tur: 'harf', yeni: temel.filter(function (c) { return anaTemel.indexOf(c) < 0; }), aciklama: 'İşaret ve serçe parmaklarının uzandığı tuşlar.' },
      { ad: 'Temel sıra kelimeleri', tur: 'kelime', aciklama: 'Yalnız temel sıradaki harflerle yazılan gerçek kelimeler.' },
      { ad: 'Üst sıra: sol el', tur: 'harf', yeni: bol(ust, 'sol'), aciklama: 'Parmakları yukarı uzat, bastıktan sonra temel konuma dön.' },
      { ad: 'Üst sıra: sağ el', tur: 'harf', yeni: bol(ust, 'sag'), aciklama: 'Sağ el üst sıra tuşları.' },
      { ad: 'Üst sıra kelimeleri', tur: 'kelime', aciklama: 'Temel ve üst sıra harfleriyle yazılan kelimeler.' },
      { ad: 'Alt sıra: sol el', tur: 'harf', yeni: bol(alt, 'sol'), aciklama: 'Parmakları aşağı kıvır; bilek sabit kalsın.' },
      { ad: 'Alt sıra: sağ el', tur: 'harf', yeni: bol(alt, 'sag'), aciklama: 'Sağ el alt sıra tuşları.' },
      { ad: 'Tüm harflerle kelimeler', tur: 'kelime', aciklama: 'Artık bütün harfleri biliyorsun; karışık kelimelerle pekiştir.' },
      { ad: 'Türkçe karakterler', tur: 'kelime', ozel: 'tr', yeni: tr, aciklama: 'ç, ğ, ı, ö, ş, ü ve i harflerini içeren kelimeler. Sınavda en çok hata buralarda yapılır.' },
      { ad: 'En sık 150 kelime', tur: 'kelime', ozel: 'sik', aciklama: 'Sınav metinlerinde en sık geçen kelimeler; bunları akıcı yazmak hızını doğrudan artırır.' },
      { ad: 'Hukuk terimleri', tur: 'kelime', ozel: 'terim', aciklama: 'Adliyede her gün yazılan terimler.' },
      { ad: 'Uzun kelimeler', tur: 'kelime', ozel: 'uzun', aciklama: 'On bir harf ve üzeri kelimeler; hecelere bölerek ritimle yaz.' },
      { ad: 'Rakamlar', tur: 'rakam', aciklama: 'Üst sıradaki rakam tuşları; esas numarası ve tutar yazarken gerekir.' },
      { ad: 'Sınav metni akışı', tur: 'metin', aciklama: '2025 resmî sınav metinlerinden bölümler. Cümle akışını bozmadan yaz.' }
    ];
    var izinli = [];
    DERSLER.forEach(function (d, i) {
      if (d.tur === 'harf') izinli = izinli.concat(d.yeni);
      if (i === 9) izinli = harfler(S[1] + S[2] + S[3]);
      d.izinli = izinli.slice();
      d.hedef = d.tur === 'harf' ? 12 : d.tur === 'rakam' ? 15 : d.tur === 'metin' ? 28 : 20;
    });
  }

  /* ---------- alıştırma metinleri ---------- */
  function sec(d) { return d[Math.floor(Math.random() * d.length)]; }
  function uzunlukta(ureteci, karakter) { var p = []; while (p.join(' ').length < karakter) p.push(ureteci()); return p.join(' '); }
  function izinliKelimeler(izinli, en) {
    var re = new RegExp('^[' + izinli.join('') + ']+$');
    return kelimeler.filter(function (w) { return w.length >= 2 && re.test(w); }).slice(0, en || 300);
  }
  function adimlar(d) {
    var a = [];
    if (d.tur === 'harf') {
      var y = d.yeni;
      a.push(['Tanış', uzunlukta(function () { var c = sec(y); return c + c + c; }, 48)]);
      a.push(['İkililer', uzunlukta(function () { return sec(y) + sec(y); }, 54)]);
      a.push(['Karışık gruplar', uzunlukta(function () { var n = 2 + Math.floor(Math.random() * 3), s = ''; for (var i = 0; i < n; i++) s += Math.random() < 0.55 ? sec(y) : sec(d.izinli); return s; }, 66)]);
      var k = izinliKelimeler(d.izinli);
      a.push([k.length >= 6 ? 'Kelimeler' : 'Uzun gruplar', k.length >= 6 ? uzunlukta(function () { return sec(k.slice(0, 80)); }, 72) : uzunlukta(function () { var s = ''; for (var i = 0; i < 4; i++) s += sec(d.izinli); return s; }, 72)]);
    } else if (d.tur === 'kelime') {
      var havuz;
      if (d.ozel === 'tr') havuz = kelimeler.filter(function (w) { return /[çğıöşüi]/.test(w) && w.length >= 4; }).slice(0, 250);
      else if (d.ozel === 'sik') havuz = sikKelimeler.slice(0, 150);
      else if (d.ozel === 'terim') havuz = TERIMLER;
      else if (d.ozel === 'uzun') havuz = kelimeler.filter(function (w) { return w.length >= 11; }).slice(0, 200);
      else havuz = izinliKelimeler(d.izinli, 200);
      if (havuz.length < 6) havuz = sikKelimeler.slice(0, 100);
      for (var i = 0; i < 3; i++) a.push(['Bölüm ' + (i + 1), uzunlukta(function () { return sec(havuz); }, 80)]);
    } else if (d.tur === 'rakam') {
      a.push(['Sıra', uzunlukta(function () { var s = ''; for (var i = 1; i <= 5; i++) s += String((i + Math.floor(Math.random() * 5)) % 10); return s; }, 48)]);
      a.push(['Sayılar', uzunlukta(function () { return String(Math.floor(Math.random() * 9000) + 10); }, 54)]);
      a.push(['Esas ve yıl', uzunlukta(function () { return sec(['2024', '2025', '2026']) + ' ' + (Math.floor(Math.random() * 1900) + 1) + ' esas'; }, 66)]);
    } else {
      for (var j = 0; j < 3; j++) {
        var bas = Math.floor(Math.random() * Math.max(1, sinavMetni.length - 20));
        a.push(['Bölüm ' + (j + 1), sinavMetni.slice(bas, bas + 16).join(' ')]);
      }
    }
    return a;
  }

  /* ---------- liste ve ilerleme ---------- */
  function kayit() { return ilerleme[duzen] || (ilerleme[duzen] = {}); }
  function listeCiz() {
    var l = $('ders-liste'); l.textContent = '';
    var k = kayit(), tamam = 0, yildiz = 0;
    DERSLER.forEach(function (d, i) {
      var x = k[i] || {}, b = E('button', 'kd-ders' + (i === aktif ? ' aktif' : '') + (x.y ? ' bitti' : ''));
      b.type = 'button';
      b.appendChild(E('span', 'kd-no', String(i + 1)));
      var orta = E('span', 'kd-ad'); orta.appendChild(E('b', null, d.ad));
      orta.appendChild(E('small', null, d.tur === 'harf' ? d.yeni.map(function (c) { return c.toLocaleUpperCase('tr-TR'); }).join(' ') : d.aciklama.split('.')[0]));
      b.appendChild(orta);
      b.appendChild(E('span', 'kd-yildiz', x.y ? '★★★'.slice(0, x.y) + '☆☆☆'.slice(x.y) : ''));
      if (i === aktif) b.setAttribute('aria-current', 'step');
      b.onclick = function () { dersAc(i); O.A('tikla', { a: 'katip-ders', x: duzen + '-' + (i + 1) }); };
      l.appendChild(b);
      if (x.y) { tamam++; yildiz += x.y; }
    });
    $('d-ilerleme').textContent = tamam + '/' + DERSLER.length;
    $('d-yildiz').textContent = yildiz;
  }

  /* ---------- oynatıcı ---------- */
  var s = null;
  function dersAc(i, adimNo) {
    aktif = i; adim = adimNo || 0;
    var d = DERSLER[i];
    if (!adimNo) { d.adimlar = adimlar(d); d.adimYildiz = []; }
    $('o-no').textContent = 'Ders ' + (i + 1) + ' / ' + DERSLER.length + ' · Türkçe ' + duzen;
    $('o-ad').textContent = d.ad;
    $('o-aciklama').textContent = d.aciklama + ' Hedef: %97 doğruluk ve dakikada ' + d.hedef + ' kelime.';
    listeCiz();
    adimBasla();
    try { history.replaceState(null, '', '#' + duzen.toLowerCase() + '-' + (i + 1)); } catch (e) { /* önemsiz */ }
  }
  function adimBasla() {
    var d = DERSLER[aktif], metin = d.adimlar[adim][1];
    var ad = $('o-adimlar'); ad.textContent = '';
    d.adimlar.forEach(function (x, j) { var e = E('span', 'kd-adim' + (j < adim ? ' bitti' : j === adim ? ' simdi' : ''), x[0]); ad.appendChild(e); });
    s = { metin: metin, poz: 0, hata: 0, vurus: 0, bas: 0, hatali: {}, kayit: KK.kaydedici(), bitti: false };
    var m = $('o-metin'); m.textContent = '';
    metin.split('').forEach(function (c) { m.appendChild(E('span', c === ' ' ? 'kd-b' : null, c === ' ' ? '␣' : c)); });
    $('o-sonuc').hidden = true;
    $('o-dogru').textContent = '—'; $('o-hiz').textContent = '—'; $('o-hata').textContent = '0';
    imlec();
    m.focus({ preventScroll: true });
  }
  function imlec() {
    var sp = $('o-metin').children;
    [].forEach.call(sp, function (e, i) { e.classList.toggle('imlec', i === s.poz); });
    var c = s.metin[s.poz];
    if (klavye) klavye.vurgula(c == null ? '' : c);
    var ip = $('o-ipucu');
    if (c == null) { ip.textContent = ''; return; }
    var p = KK.parmak(c, duzen);
    ip.textContent = c === ' ' ? 'Sıradaki: boşluk · başparmak' : 'Sıradaki: ' + c.toLocaleUpperCase('tr-TR') + ' · ' + (p >= 0 ? KK.PARMAK[p] + ' parmağı' : '');
    var cur = sp[s.poz];
    if (cur) { var kap = $('o-metin'); if (cur.offsetLeft - kap.scrollLeft > kap.clientWidth * 0.6 || cur.offsetLeft < kap.scrollLeft) kap.scrollLeft = cur.offsetLeft - kap.clientWidth * 0.3; }
  }
  function hizHesapla() {
    var dk = Math.max(1, performance.now() - s.bas) / 60000;
    return { hiz: Math.round(s.poz / 5 / dk), dogruluk: s.vurus ? Math.round((s.vurus - s.hata) / s.vurus * 1000) / 10 : 100 };
  }
  function tus(e) {
    if (!s || s.bitti || document.activeElement !== $('o-metin')) return;
    if ((e.ctrlKey || e.metaKey) && !e.altKey) return;
    if (e.key.length !== 1) { if (e.key === 'Backspace' || e.key === 'Tab') e.preventDefault(); return; }
    e.preventDefault();
    var beklenen = s.metin[s.poz], k = e.key === 'İ' ? 'i' : e.key;
    if (!s.bas) s.bas = performance.now();
    s.vurus++;
    s.kayit.ekle(beklenen, k);
    var sp = $('o-metin').children[s.poz];
    if (k === beklenen) {
      if (ayar.ses) KK.Ses.tik();
      sp.classList.add(s.hatali[s.poz] ? 'duzeldi' : 'dogru');
      s.poz++;
      if (s.poz >= s.metin.length) return adimBitti();
    } else {
      s.hata++; s.hatali[s.poz] = 1;
      sp.classList.remove('sars'); void sp.offsetWidth; sp.classList.add('hata', 'sars');
      if (ayar.ses) KK.Ses.hata();
    }
    var h = hizHesapla();
    $('o-dogru').textContent = '%' + String(h.dogruluk).replace('.', ','); $('o-hiz').textContent = h.hiz + ' k/dk'; $('o-hata').textContent = s.hata;
    imlec();
  }
  function adimBitti() {
    s.bitti = true;
    var d = DERSLER[aktif], h = hizHesapla();
    var y = h.dogruluk >= 97 && h.hiz >= d.hedef ? 3 : h.dogruluk >= 92 ? 2 : 1;
    KK.birlestir(KK.analiz(s.kayit.vuruslar, duzen));
    d.adimYildiz = d.adimYildiz || []; d.adimYildiz[adim] = y;
    var son = adim === d.adimlar.length - 1;
    if (son) {
      var ort = Math.round(d.adimYildiz.reduce(function (t, x) { return t + (x || 1); }, 0) / d.adimlar.length);
      var k = kayit(), eski = (k[aktif] || {}).y || 0;
      k[aktif] = { y: Math.max(eski, ort), t: Date.now() };
      O.yaz('kit-katip-ders', ilerleme);
      listeCiz();
      O.A('tikla', { a: 'katip-ders-bitti', x: duzen + '-' + (aktif + 1), n: ort });
      KK.Ses.acik = ayar.ses; if (ayar.ses) KK.Ses.seviye();
    } else if (ayar.ses) KK.Ses.basari();
    $('s-yildiz').textContent = '★★★'.slice(0, y) + '☆☆☆'.slice(y);
    $('s-baslik').textContent = son ? 'Ders tamamlandı!' : DERSLER[aktif].adimlar[adim][0] + ' tamam';
    var oneri = h.dogruluk < 92 ? 'Doğruluğun düşük; yavaşla ve her tuşa kendi parmağıyla bas.' : h.hiz < d.hedef ? 'Doğruluk iyi. Ritmi koruyarak biraz hızlanmayı dene.' : 'Harika! Hem doğru hem hızlı yazdın.';
    $('s-ozet').textContent = 'Doğruluk %' + String(h.dogruluk).replace('.', ',') + ' · ' + h.hiz + ' kelime/dk · ' + s.hata + ' hata. ' + oneri;
    $('s-devam').textContent = son ? (aktif < DERSLER.length - 1 ? 'Sonraki ders' : 'Baştan başla') : 'Sonraki alıştırma';
    $('o-sonuc').hidden = false;
    $('s-devam').focus();
  }
  function devam() {
    var d = DERSLER[aktif];
    if (adim < d.adimlar.length - 1) { adim++; adimBasla(); }
    else dersAc(aktif < DERSLER.length - 1 ? aktif + 1 : 0);
  }

  /* ---------- düzen ve ayarlar ---------- */
  function duzenSec(d, ilk) {
    duzen = d === 'F' ? 'F' : 'Q';
    if (!ilk) O.klavyeKaydet(duzen);
    [].forEach.call(document.querySelectorAll('#duzen-sec .tab'), function (b) { var a = b.dataset.v === duzen; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); });
    klavye = ayar.klavye ? KK.ciz($('o-klavye'), duzen) : null;
    $('o-klavye').hidden = !ayar.klavye;
    planla();
  }
  [].forEach.call(document.querySelectorAll('#duzen-sec .tab'), function (b) { b.onclick = function () { duzenSec(b.dataset.v); dersAc(0); }; });
  $('o-ses').checked = ayar.ses; $('o-klavye-goster').checked = ayar.klavye;
  $('o-ses').onchange = function () { ayar.ses = this.checked; KK.Ses.acik = ayar.ses; O.yaz('kit-katip-ders-ayar', ayar); $('o-metin').focus(); };
  $('o-klavye-goster').onchange = function () {
    ayar.klavye = this.checked; O.yaz('kit-katip-ders-ayar', ayar);
    klavye = ayar.klavye ? KK.ciz($('o-klavye'), duzen) : null; $('o-klavye').hidden = !ayar.klavye;
    if (s) imlec(); $('o-metin').focus();
  };
  $('s-devam').onclick = devam;
  $('s-tekrar').onclick = function () { adimBasla(); };
  document.addEventListener('keydown', function (e) {
    if (!$('o-sonuc').hidden) {
      if (e.key === 'Enter' && e.target.tagName !== 'BUTTON') { e.preventDefault(); devam(); }
      else if ((e.key === 'r' || e.key === 'R') && e.target.tagName !== 'INPUT') { e.preventDefault(); adimBasla(); }
      return;
    }
    tus(e);
  });
  $('o-metin').addEventListener('focus', function () { this.classList.add('odak'); });
  $('o-metin').addEventListener('blur', function () { this.classList.remove('odak'); });
  $('o-metin').addEventListener('click', function () { this.focus(); });
  KK.Ses.acik = ayar.ses;

  /* ---------- başlangıç ---------- */
  duzenSec(duzen, true);
  Promise.all([KatipKutuphane.getir('zk2025'), KatipKutuphane.getir('ozgun')]).then(function (r) {
    sikKelimeler = O.kelimeSikligi(r);
    kelimeler = sikKelimeler.slice(0, 4000);
    sinavMetni = r[0].map(function (m) { return m[1]; }).join(' ').split(' ');
    var h = /^#([qf])-(\d+)$/.exec(location.hash);
    if (h) { duzenSec(h[1].toUpperCase()); }
    dersAc(h ? Math.min(DERSLER.length, Math.max(1, +h[2])) - 1 : ilkEksik());
    if (matchMedia('(pointer:coarse)').matches) $('o-ipucu').textContent = 'Dersler fiziksel klavye için tasarlandı; bilgisayardan açman önerilir.';
  }).catch(function () { $('o-ad').textContent = 'Metinler yüklenemedi. Sayfayı yenile.'; });
  function ilkEksik() { var k = kayit(); for (var i = 0; i < DERSLER.length; i++) if (!k[i]) return i; return 0; }
})();
