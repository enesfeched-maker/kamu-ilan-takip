/* KPSS Tercihi: üye avatarları için ortak küçük yardımcı (Kasım 2026). hesap.js, forum.js, profil-kart.js ve katiplik sayfaları kullanır.
   Avatar verisi sunucudan şu biçimlerde gelir: "kedi:lila" (kendi SVG setimiz), "px.loaf:pixel.0" (Piixpal, MIT), 'foto' (yüklenen fotoğraf) ya da boş.
   Boşsa avatar rumuzdan türetilir (rumuz sonradan değişmez): iki setin birleşik listesinden kararlı bir seçim; herkesin bir avatarı vardır.
   Piixpal canlı bir bileşendir; yalnız büyük kartta, profil sayfasında ve tercih önizlemesinde canlı gösterilir (canli()). Listelerde, sohbette ve üst çubukta
   durağan görüntü kullanılır: piksel/ton 0 için hazır görüntüler (avatar/piixpal-anlik.js), diğerleri için bileşenin tek karesi bir kez alınıp sessionStorage'a yazılır.
   Betikler (piixpal.min.js, görüntü listesi) yalnız bir Piixpal avatarı gösterilecekse yüklenir. Hata olursa harf avatarına dönülür.
   Boyut: her çıktı .fr-av sınıfını taşır (varsayılan 32 px); boyut verilirse satır içi width/height da yazılır. Piksel görüntü bir <span> içindedir. */
(function () {
  'use strict';
  if (window.kitAvatar) return;
  var bet = typeof document !== 'undefined' ? document.currentScript : null;
  var TABAN = bet && bet.src ? bet.src.replace(/avatar-ortak\.js.*$/, '') : '/';
  var SURUM = (bet && /[?&]v=(\w+)/.exec(bet.src) || [0, '1'])[1];
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var AV_ANAHTAR = /^[a-z0-9-]{1,24}$/, AV_RENK = /^[a-z-]{1,16}$/, PX = /^px\.([a-z]{2,10}):([a-z]{3,10})\.(\d{1,3})$/;
  var durum = 'bekle';   // bekle | tamam | hata  (SVG seti)
  var vaat = null, pxVaat = null, anlikVaat = null, pxHazir = false, pxHata = false;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function karma(ad) {   // FNV-1a: küçük harfli rumuzdan sabit sayı
    var h = 2166136261; ad = String(ad || '?').toLocaleLowerCase('tr-TR');
    for (var i = 0; i < ad.length; i++) { h ^= ad.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h >>> 0;
  }
  function ton(ad) { return karma(ad) % 360; }
  function liste() { var m = window.KIT_AVATAR; return m && m.avatarlar ? m : null; }
  function pxListe() { var m = window.KIT_PIIX; return m && m.avatarlar ? m : null; }
  function renkler() { var m = liste(); return m ? m.renkler || [] : []; }
  function bul(dizi, anahtar) { for (var i = 0; i < dizi.length; i++) if (dizi[i].anahtar === anahtar) return dizi[i]; return null; }
  function azalt() { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } }

  // Birleşik liste üzerinden kararlı varsayılan: SVG avatarları (pastel zemin) + Piixpal (piksel, özgün ton).
  function varsayilanSvg(rumuz) {
    var m = liste();
    if (!m) return null;
    var pastel = renkler().filter(function (r) { return !r.koyu; });
    if (!pastel.length) pastel = renkler();
    var h = karma(rumuz);
    return { set: 'svg', k: m.avatarlar[h % m.avatarlar.length].anahtar, r: pastel.length ? pastel[(h >>> 8) % pastel.length].anahtar : '' };
  }
  function varsayilan(rumuz) {
    var m = liste(), p = pxListe();
    if (!m) return null;
    var n = m.avatarlar.length, toplam = n + (p ? p.avatarlar.length : 0), i = karma(rumuz) % toplam;
    if (i >= n) return { set: 'px', k: p.avatarlar[i - n].anahtar, r: 'pixel', h: 0 };
    return varsayilanSvg(rumuz);
  }
  // Değeri çözer: svg -> { set:'svg', k, r }, Piixpal -> { set:'px', k, r, h }; bilinmeyen / bozuk -> null (çağıran varsayılana düşer).
  function coz(av) {
    if (typeof av !== 'string') return null;
    var mp = PX.exec(av);
    if (mp) {
      var p = pxListe();
      if (p && !bul(p.avatarlar, mp[1])) return null;
      if (p && !bul(p.bicimler, mp[2])) return null;
      return { set: 'px', k: mp[1], r: mp[2], h: Number(mp[3]) };
    }
    var a = av.split(':');
    if (a.length !== 2 || !AV_ANAHTAR.test(a[0]) || !AV_RENK.test(a[1])) return null;
    var m = liste();
    if (m && !bul(m.avatarlar, a[0])) return null;
    return { set: 'svg', k: a[0], r: a[1] };
  }
  function dizge(c) { return c.set === 'px' ? 'px.' + c.k + ':' + (c.r || 'pixel') + '.' + (c.h || 0) : c.k + ':' + c.r; }
  function renkDegeri(r) { var c = bul(renkler(), r); return c ? c.renk : ''; }
  function fotoAdresi(fu, fs) { return API + '/foto/' + Number(fu) + '?v=' + Number(fs); }
  function harf(rumuz, boyut, sinif, bekleyen) {
    return '<span class="fr-av' + (sinif ? ' ' + sinif : '') + '"' + (bekleyen ? ' data-avu="' + esc(JSON.stringify(bekleyen)) + '"' : '') + ' style="--h:' + ton(rumuz) + (boyut ? ';width:' + boyut + 'px;height:' + boyut + 'px;font-size:' + Math.round(boyut * 0.42) + 'px' : '') + '" aria-hidden="true">'
      + esc(String(rumuz || '?').charAt(0).toLocaleUpperCase('tr-TR')) + '</span>';
  }

  /* ---------- Piixpal: betik ve durağan görüntüler ---------- */
  function betik(url) {
    return new Promise(function (ok, red) {
      var s = document.createElement('script'); s.async = true; s.src = url; s.onload = ok; s.onerror = function () { red(new Error('betik')); };
      document.head.appendChild(s);
    });
  }
  // <piix-sprite> bileşeni: ilk gerektiğinde yüklenir (≈260 KB). Dönen söz hiçbir zaman reddedilmez; true = kullanılabilir.
  function piixYukle() {
    if (pxVaat) return pxVaat;
    var m = pxListe();
    pxVaat = (m ? Promise.resolve() : betik(TABAN + 'avatar/piixpal.js?v=' + SURUM)).then(function () {
      if (window.customElements && window.customElements.get('piix-sprite')) return;
      return betik(TABAN + (pxListe() ? pxListe().betik : 'avatar/piixpal/piixpal.min.js') + '?v=' + SURUM);
    }).then(function () { pxHazir = !!(window.customElements && window.customElements.get('piix-sprite')); if (!pxHazir) pxHata = true; return pxHazir; }, function () { pxHata = true; return false; });
    return pxVaat;
  }
  function anlikYukle() {   // ton 0 piksel görüntüleri (≈37 KB)
    if (window.KIT_PIIX_ANLIK) return Promise.resolve();
    if (!anlikVaat) anlikVaat = betik(TABAN + 'avatar/piixpal-anlik.js?v=' + SURUM).catch(function () {});
    return anlikVaat;
  }
  var bellek = {};   // "ad|biçim|ton" -> data URL
  function anahtarSnap(c) { return c.k + '|' + (c.r || 'pixel') + '|' + (c.h || 0); }
  function anlik(c) {
    var a = anahtarSnap(c);
    if (bellek[a]) return bellek[a];
    if ((c.r || 'pixel') === 'pixel' && !c.h && window.KIT_PIIX_ANLIK && window.KIT_PIIX_ANLIK[c.k]) return (bellek[a] = window.KIT_PIIX_ANLIK[c.k]);
    try { var s = sessionStorage.getItem('kit-px:' + a); if (s) return (bellek[a] = s); } catch (e) { /* depolama kapalı */ }
    return '';
  }
  var sira = [], calisan = 0;
  // Bileşenin ilk karesini alır (ekran dışında, en çok 2 eşzamanlı); sonuç belleğe ve sessionStorage'a yazılır.
  function kareAl(c) {
    return new Promise(function (ok) { sira.push({ c: c, ok: ok }); siradaki(); });
  }
  function siradaki() {
    if (calisan >= 2 || !sira.length) return;
    var is = sira.shift(); calisan++;
    piixYukle().then(function (var_) {
      if (!var_) return '';
      return new Promise(function (bitti) {
        var kap = document.createElement('div'); kap.setAttribute('aria-hidden', 'true'); kap.style.cssText = 'position:fixed;left:-300px;top:0;width:200px;height:200px;pointer-events:none';
        var e = document.createElement('piix-sprite'); e.setAttribute('name', is.c.k); e.setAttribute('size', '48');
        if (is.c.r && is.c.r !== 'pixel') e.setAttribute('render', is.c.r);
        if (is.c.h) e.setAttribute('hue', String(is.c.h));
        kap.appendChild(e); document.body.appendChild(kap);
        var n = 0, z = setInterval(function () {
          var cv = e.shadowRoot && e.shadowRoot.querySelector('canvas'), url = '';
          if (cv && cv.width) {
            try {
              var t = document.createElement('canvas'); t.width = cv.width; t.height = cv.height;
              var x = t.getContext('2d'); x.drawImage(cv, 0, 0);
              var d = x.getImageData(0, 0, t.width, t.height).data, k = 0;
              for (var i = 3; i < d.length; i += 4) if (d[i] > 20) k++;
              if (k > 8) url = t.toDataURL('image/png');
            } catch (er) { url = ''; }
          }
          if (url || ++n > 40) { clearInterval(z); kap.remove(); bitti(url); }
        }, 50);
      });
    }).then(function (url) {
      calisan--; var a = anahtarSnap(is.c);
      if (url) { bellek[a] = url; try { sessionStorage.setItem('kit-px:' + a, url); } catch (e) { /* kota */ } }
      is.ok(url); siradaki();
    });
  }
  var hazirlanan = {};   // aynı avatar için tek iş: listede 20 kez geçse de bir kare alınır; kare alınamazsa yukselt() -> html() yeniden denemez (sonsuz döngü olmaz)
  function pxHazirla(c) {   // durağan görüntü hazır olunca yer tutucular değişir
    var ah = anahtarSnap(c);
    if (hazirlanan[ah]) return;
    hazirlanan[ah] = 1;
    var p = (c.r || 'pixel') === 'pixel' && !c.h ? anlikYukle().then(function () { return anlik(c); }) : Promise.resolve(anlik(c));
    p.then(function (u) { return u || kareAl(c); }).then(function () { yukselt(); });
  }

  /* ---------- çizim ---------- */
  // uye: { rumuz, av, fs, fu }. boyut px. Alt metin boştur: rumuz yanında yazılıdır. Liste/sohbet/üst çubuk için durağan.
  function html(uye, boyut, sinif) {
    uye = uye || {};
    var s = sinif ? ' ' + sinif : '', b = boyut ? ' width="' + boyut + '" height="' + boyut + '"' : '', bs = boyut ? 'width:' + boyut + 'px;height:' + boyut + 'px' : '';   // CSS sınıfı öznitelikleri ezdiği için boyut stile de yazılır
    if (uye.fs && uye.fu && uye.av === 'foto') {
      return '<img class="fr-av fr-av-foto' + s + '" src="' + esc(fotoAdresi(uye.fu, uye.fs)) + '" alt="" loading="lazy" decoding="async"' + b + (bs ? ' style="' + bs + '"' : '') + '>';
    }
    if (durum === 'bekle') return harf(uye.rumuz, boyut, sinif, { u: { rumuz: uye.rumuz, av: uye.av, fs: uye.fs, fu: uye.fu }, b: boyut, s: sinif });   // yükleme bitince değişir
    if (durum !== 'tamam' || !liste()) return harf(uye.rumuz, boyut, sinif);
    var a = coz(uye.av) || varsayilan(uye.rumuz);
    if (!a) return harf(uye.rumuz, boyut, sinif);
    if (a.set === 'px') {
      if (pxHata) return harf(uye.rumuz, boyut, sinif);
      var u = anlik(a);
      // Görüntü dairenin içinde ortalanır: dış kutu boyutu taşır, iç görüntü %76 (img'de yüzde dolgu, kapsayıcı genişliğine göre büyüyordu)
      if (u) return '<span class="fr-av fr-av-px' + s + '" aria-hidden="true"' + (bs ? ' style="' + bs + '"' : '') + '><img src="' + esc(u) + '" alt=""' + b + ' decoding="async"></span>';
      pxHazirla(a);
      return harf(uye.rumuz, boyut, sinif, { u: { rumuz: uye.rumuz, av: uye.av, fs: uye.fs, fu: uye.fu }, b: boyut, s: sinif });
    }
    var z = renkDegeri(a.r);
    return '<svg class="fr-av fr-av-svg' + s + '"' + (z || bs ? ' style="' + (z ? '--av-z:' + esc(z) + (bs ? ';' : '') : '') + bs + '"' : '') + b + ' viewBox="0 0 64 64" aria-hidden="true" focusable="false"><use href="' + esc(TABAN + 'avatar/avatarlar.svg#av-' + a.k) + '"/></svg>';
  }
  // Büyük kart / profil sayfası / tercih önizlemesi: Piixpal ise canlı bileşen (piixYukle() sonrası), diğerlerinde html().
  function canli(uye, boyut) {
    var a = coz((uye || {}).av) || (uye && uye.av === 'foto' ? null : varsayilan((uye || {}).rumuz));
    if (!a || a.set !== 'px' || !pxHazir) return html(uye, boyut);
    var kutu = Math.round(boyut), boy = Math.round(boyut * 0.7);
    return '<span class="fr-av fr-av-px fr-av-canli" aria-hidden="true" style="width:' + kutu + 'px;height:' + kutu + 'px"><piix-sprite name="' + esc(a.k) + '" size="' + boy + '"'
      + (a.r && a.r !== 'pixel' ? ' render="' + esc(a.r) + '"' : '') + (a.h ? ' hue="' + a.h + '"' : '') + (azalt() ? ' still' : '') + '></piix-sprite></span>';
  }
  // Yükleme beklenirken çizilen harf avatarlarını gerçek avatarla değiştirir.
  function yukselt() {
    var l = document.querySelectorAll('[data-avu]');
    for (var i = 0; i < l.length; i++) {
      try {
        var o = JSON.parse(l[i].getAttribute('data-avu')), t = document.createElement('template');
        t.innerHTML = html(o.u, o.b, o.s).trim();
        var y = t.content.firstChild;
        if (y && !(y.getAttribute && y.getAttribute('data-avu'))) l[i].replaceWith(y);
      } catch (e) { l[i].removeAttribute('data-avu'); }
    }
  }
  // SVG seti ve manifestler bir kez yüklenir. Piixpal manifesti (küçük) birlikte gelir; bileşen ve görüntüler gerektiğinde. Dönen söz reddedilmez.
  function yukle() {
    if (vaat) return vaat;
    var liste_ = window.KIT_AVATAR ? Promise.resolve() : betik(TABAN + 'avatar/avatarlar.js?v=' + SURUM);
    var px_ = window.KIT_PIIX ? Promise.resolve() : betik(TABAN + 'avatar/piixpal.js?v=' + SURUM).catch(function () {});
    vaat = Promise.all([liste_, px_]).then(function () {
      if (!liste()) throw new Error('liste');
      return fetch(TABAN + 'avatar/avatarlar.svg?v=' + SURUM).then(function (r) { if (!r.ok) throw new Error('sprite'); });   // <use> aynı önbellekten okur
    }).then(function () { durum = 'tamam'; }, function () { durum = 'hata'; }).then(function () { yukselt(); try { window.dispatchEvent(new Event('kit-avatar')); } catch (e) {} });
    return vaat;
  }
  window.kitAvatar = {
    yukle: yukle, html: html, canli: canli, harf: harf, varsayilan: varsayilan, varsayilanSvg: varsayilanSvg, coz: coz, dizge: dizge, renkDegeri: renkDegeri, fotoAdresi: fotoAdresi, taban: TABAN, ton: ton,
    hazir: function () { return durum === 'tamam'; }, liste: liste, pxListe: pxListe, renkler: renkler, piixYukle: piixYukle, anlikYukle: anlikYukle, anlik: anlik, azalt: azalt,
    pxHazirMi: function () { return pxHazir; }
  };
})();
