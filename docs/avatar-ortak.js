/* KPSS Tercihi: üye avatarları için ortak küçük yardımcı (Kasım 2026). hesap.js, forum.js, profil-kart.js ve katiplik sayfaları kullanır.
   Avatarlar yalnız piksel karakterdir (Piixpal, MIT): "px.<ad>:pixel.<ton>" ya da 'foto' (yüklenen fotoğraf). Her üye üyelikte rastgele bir
   karakterle başlar (sunucu atar). Eski kayıtlar da düzgün görünür: çizim setinden kalma "kedi:lila" gibi değerler ve diğer piksel biçimleri
   (dots/halftone/voxel) en yakın piksel karaktere çevrilir (forum/src/kart.js ESKI_SVG_PX ile aynı tablo). Değer yoksa rumuzdan türetilir.
   Listelerde, sohbette ve üst çubukta durağan görüntü kullanılır: hazır ton 0 görüntüleri (avatar/piixpal-anlik.js), diğer tonlar CSS hue-rotate ile.
   Canlı bileşen yalnız büyük kartta ve önizlemede (canli()).
   "muhtar" sitenin kendi çizdiği özel karakterdir (yalnız gizli yöneticiler seçebilir; sunucu denetler). Hata olursa harf avatarına dönülür.
   Boyut: her çıktı .fr-av sınıfını taşır (varsayılan 32 px); boyut verilirse satır içi width/height da yazılır. Piksel görüntü bir <span> içindedir. */
(function () {
  'use strict';
  if (window.kitAvatar) return;
  var bet = typeof document !== 'undefined' ? document.currentScript : null;
  var TABAN = bet && bet.src ? bet.src.replace(/avatar-ortak\.js.*$/, '') : '/';
  var SURUM = (bet && /[?&]v=(\w+)/.exec(bet.src) || [0, '1'])[1];
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var PX = /^px\.([a-z]{2,10}):([a-z]{3,10})\.(\d{1,3})$/, ESKI = /^([a-z0-9-]{1,24}):([a-z-]{1,16})$/;
  var TONLAR = [0, 45, 90, 135, 180, 225, 270, 315];
  // Eski çizim seti -> piksel karakter ve renk -> ton (forum/src/kart.js ve migrations/0006 ile aynı)
  var ESKI_SVG_PX = {
    kedi: 'loaf', tavsan: 'hops', panda: 'mumu', tilki: 'loaf', baykus: 'star', ayicik: 'mumu', penguen: 'whale', koala: 'mumu', sincap: 'hops', kuzu: 'fluff',
    ordek: 'egg', hamster: 'mochi', kirpi: 'cactus', geyik: 'llama', kelebek: 'heart', astronot: 'astronaut', kaptan: 'wizard', kitapkurdu: 'brain', dagci: 'planet',
    bisikletci: 'bolt', asci: 'cookie', ressam: 'star', gitarist: 'flick', satranc: 'keycap', kahve: 'coffee', saksi: 'cactus', robot: 'robo', dinozor: 'dragon',
    ayikaptan: 'mumu', kurt: 'dragon', aslan: 'loaf', kartal: 'cloud', kalem: 'prompty', dosya: 'inbox', muhur: 'token', cay: 'boba', tus: 'keycap', kitap: 'floppy'
  };
  var ESKI_RENK_TON = { lila: 270, pembe: 315, seftali: 45, limon: 45, nane: 135, gok: 225, lavanta: 270, kum: 0, mercan: 315, adacayi: 90 };
  // Muhtar: 16x18 piksel, setle aynı çizgi kalınlığı ve koyu dış hat. Renkler colors.elwyn.co (Sanzo Wada) birleşimlerinden: #113, #257, #67, #92, #49, #46.
  var MUHTAR = 'muhtar';
  var MUHTAR_RESIM = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAASCAYAAABSO15qAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAC4SURBVDhPY2DAAgSFRf5jw+jqMABMoYmrD1aM1yBkjcuvPAFjdAOQDULXj2IAIYxhALpficUYhvy9spcojKEZ3QBshqHLo+sHG/C1rwVDIzoGqcFpAEiBt7E4XozXBTAD0G2FYbwGgAA2v6NjnJphABZF2DTi1QxXkLfjPww8llcDYxgAyWE1CKYRhvEZAMMohsAMiGrajGIIsgEw8T+bRcGYoAEgDDMAWTMoHeA0gBiM0wXkYJBeAHuu2N3Y4H6pAAAAAElFTkSuQmCC';
  var durum = 'bekle';   // bekle | tamam | hata  (piksel listesi)
  var vaat = null, pxVaat = null, anlikVaat = null, pxHazir = false;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function karma(ad) {   // FNV-1a: küçük harfli rumuzdan sabit sayı
    var h = 2166136261; ad = String(ad || '?').toLocaleLowerCase('tr-TR');
    for (var i = 0; i < ad.length; i++) { h ^= ad.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h >>> 0;
  }
  function ton(ad) { return karma(ad) % 360; }
  function pxListe() { var m = window.KIT_PIIX; return m && m.avatarlar ? m : null; }
  function bul(dizi, anahtar) { for (var i = 0; i < dizi.length; i++) if (dizi[i].anahtar === anahtar) return dizi[i]; return null; }
  function azalt() { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } }
  var sahip = Object.prototype.hasOwnProperty;

  // Değeri olmayan üye için rumuzdan kararlı piksel karakter (ton 0: hazır görüntü, ek iş yok).
  function varsayilan(rumuz) {
    var p = pxListe();
    if (!p) return null;
    return { set: 'px', k: p.avatarlar[karma(rumuz) % p.avatarlar.length].anahtar, r: 'pixel', h: 0 };
  }
  // Değeri çözer -> { set:'px', k, r:'pixel', h } (eski değerler çevrilir); tanınmayan / bozuk -> null (çağıran varsayılana düşer).
  function coz(av) {
    if (typeof av !== 'string') return null;
    var p = pxListe(), mp = PX.exec(av);
    if (mp) {
      var h = Number(mp[3]);
      if (String(h) !== mp[3] || TONLAR.indexOf(h) < 0) return null;
      if (mp[1] === MUHTAR) return mp[2] === 'pixel' && !h ? { set: 'px', k: MUHTAR, r: 'pixel', h: 0 } : null;
      if (p && (!bul(p.avatarlar, mp[1]) || !bul(p.bicimler, mp[2]))) return null;
      return { set: 'px', k: mp[1], r: 'pixel', h: h };
    }
    var me = ESKI.exec(av);
    if (!me || !sahip.call(ESKI_SVG_PX, me[1])) return null;
    return { set: 'px', k: ESKI_SVG_PX[me[1]], r: 'pixel', h: sahip.call(ESKI_RENK_TON, me[2]) ? ESKI_RENK_TON[me[2]] : 0 };
  }
  function dizge(c) { return 'px.' + c.k + ':pixel.' + (c.h || 0); }
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
  // <piix-sprite> bileşeni: yalnız büyük kartın canlı gösterimi için (≈260 KB). Dönen söz reddedilmez; true = kullanılabilir.
  function piixYukle() {
    if (pxVaat) return pxVaat;
    pxVaat = (pxListe() ? Promise.resolve() : betik(TABAN + 'avatar/piixpal.js?v=' + SURUM)).then(function () {
      if (window.customElements && window.customElements.get('piix-sprite')) return;
      return betik(TABAN + (pxListe() ? pxListe().betik : 'avatar/piixpal/piixpal.min.js') + '?v=' + SURUM);
    }).then(function () { pxHazir = !!(window.customElements && window.customElements.get('piix-sprite')); return pxHazir; }, function () { return false; });
    return pxVaat;
  }
  function anlikYukle() {   // ton 0 piksel görüntüleri (≈37 KB)
    if (window.KIT_PIIX_ANLIK) return Promise.resolve();
    if (!anlikVaat) anlikVaat = betik(TABAN + 'avatar/piixpal-anlik.js?v=' + SURUM).catch(function () {});
    return anlikVaat;
  }
  // Ton 0 durağan görüntü (data URL); yoksa ''.
  function anlik(c) {
    if (c.k === MUHTAR) return MUHTAR_RESIM;
    return window.KIT_PIIX_ANLIK && window.KIT_PIIX_ANLIK[c.k] || '';
  }
  // Ton, ton 0 görüntüsüne CSS hue-rotate ile verilir (seçicideki örneklerle aynı); bileşen çalıştırılmaz, sayfa gizliyken de çalışır.
  var hazirlanan = false;
  function pxHazirla() {
    if (hazirlanan) return;
    hazirlanan = true;
    anlikYukle().then(function () { yukselt(); });
  }
  /* ---------- çizim ---------- */
  // Görüntü dairenin içinde ortalanır: dış kutu boyutu taşır, iç görüntü %76 (img'de yüzde dolgu kapsayıcı genişliğine göre büyüyordu).
  function pikselHtml(u, s, b, bs, h) {
    return '<span class="fr-av fr-av-px' + s + '" aria-hidden="true"' + (bs ? ' style="' + bs + '"' : '') + '><img src="' + esc(u) + '" alt=""' + b + (h ? ' style="filter:hue-rotate(' + Number(h) + 'deg)"' : '') + ' decoding="async"></span>';
  }
  // uye: { rumuz, av, fs, fu }. boyut px. Alt metin boştur: rumuz yanında yazılıdır.
  function html(uye, boyut, sinif) {
    uye = uye || {};
    var s = sinif ? ' ' + sinif : '', b = boyut ? ' width="' + boyut + '" height="' + boyut + '"' : '', bs = boyut ? 'width:' + boyut + 'px;height:' + boyut + 'px' : '';   // CSS sınıfı öznitelikleri ezdiği için boyut stile de yazılır
    if (uye.fs && uye.fu && uye.av === 'foto') {
      return '<img class="fr-av fr-av-foto' + s + '" src="' + esc(fotoAdresi(uye.fu, uye.fs)) + '" alt="" loading="lazy" decoding="async"' + b + (bs ? ' style="' + bs + '"' : '') + '>';
    }
    var bekleyen = { u: { rumuz: uye.rumuz, av: uye.av, fs: uye.fs, fu: uye.fu }, b: boyut, s: sinif };
    var a = coz(uye.av);
    if (a && a.k === MUHTAR) return pikselHtml(MUHTAR_RESIM, s, b, bs);   // listeye bağlı değil, hemen çizilir
    if (durum === 'bekle') return harf(uye.rumuz, boyut, sinif, bekleyen);   // yükleme bitince değişir
    if (durum !== 'tamam' || !pxListe()) return harf(uye.rumuz, boyut, sinif);
    a = a || varsayilan(uye.rumuz);
    if (!a) return harf(uye.rumuz, boyut, sinif);
    var u = anlik({ k: a.k, h: 0 });
    if (u) return pikselHtml(u, s, b, bs, a.h);
    pxHazirla();
    return harf(uye.rumuz, boyut, sinif, bekleyen);
  }
  // Büyük kart / profil sayfası / önizleme: piksel karakter canlı bileşenle (piixYukle() sonrası); muhtar ve fotoğraf durağan.
  function canli(uye, boyut) {
    uye = uye || {};
    var a = uye.av === 'foto' ? null : (coz(uye.av) || varsayilan(uye.rumuz));
    if (!a || a.k === MUHTAR || !pxHazir) return html(uye, boyut);
    var kutu = Math.round(boyut), boy = Math.round(boyut * 0.7);
    return '<span class="fr-av fr-av-px fr-av-canli" aria-hidden="true" style="width:' + kutu + 'px;height:' + kutu + 'px"><piix-sprite name="' + esc(a.k) + '" size="' + boy + '"'
      + (a.h ? ' hue="' + a.h + '"' : '') + (azalt() ? ' still' : '') + '></piix-sprite></span>';
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
  // Piksel listesi (küçük) ve ton 0 görüntüleri bir kez yüklenir. Dönen söz reddedilmez.
  function yukle() {
    if (vaat) return vaat;
    var liste_ = pxListe() ? Promise.resolve() : betik(TABAN + 'avatar/piixpal.js?v=' + SURUM);
    vaat = Promise.all([liste_, anlikYukle()]).then(function () {
      if (!pxListe()) throw new Error('liste');
    }).then(function () { durum = 'tamam'; }, function () { durum = 'hata'; }).then(function () { yukselt(); try { window.dispatchEvent(new Event('kit-avatar')); } catch (e) {} });
    return vaat;
  }
  window.kitAvatar = {
    yukle: yukle, html: html, canli: canli, harf: harf, varsayilan: varsayilan, coz: coz, dizge: dizge, fotoAdresi: fotoAdresi, taban: TABAN, ton: ton,
    hazir: function () { return durum === 'tamam'; }, liste: pxListe, pxListe: pxListe, piixYukle: piixYukle, anlikYukle: anlikYukle, anlik: anlik, azalt: azalt,
    pxHazirMi: function () { return pxHazir; }, MUHTAR: MUHTAR, TONLAR: TONLAR, eskiTablo: ESKI_SVG_PX, eskiTon: ESKI_RENK_TON
  };
})();
