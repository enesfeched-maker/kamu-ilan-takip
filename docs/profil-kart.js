/* KPSS Tercihi: profil kartı (Kasım 2026). Üye kartı (alttan açılan pencere), herkese açık profil sayfası ve "Kartım" düzenleyicisi.
   forum.js'in verdiği window.kitForumApi (api, uye, bildir, giris ...) ve avatar-ortak.js'in window.kitAvatar'ı üzerinde çalışır.
   Yalnız kullanıcı kartı ya da profil ekranını açınca yüklenir. Tüm kullanıcı metni kaçışlanır; renkler profil-kart.css'te. */
(function () {
  'use strict';
  if (window.kitKart) return;
  var K = function () { return window.kitForumApi; };
  var AV = function () { return window.kitAvatar; };
  var bet = document.currentScript;
  var TABAN = bet && bet.src ? bet.src.replace(/profil-kart\.js.*$/, '') : '/';
  var SURUM = (bet && /[?&]v=(\w+)/.exec(bet.src) || [0, '1'])[1];

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(h) { var t = document.createElement('template'); t.innerHTML = h.trim(); return t.content.firstChild; }
  function sayi(n) { return Number(n || 0).toLocaleString('tr-TR'); }
  function ikon(d, sinif) { return '<svg viewBox="0 0 24 24" aria-hidden="true"' + (sinif ? ' class="' + sinif + '"' : '') + '><path d="' + d + '"/></svg>'; }

  var DAIRE = 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z';
  var ROZETLER = {
    'kurucu': ['Kurucu üye', 'M5 21V4M5 4h11l-2 4 2 4H5'],
    'ilk-soru': ['İlk soru', 'M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17.5h.01M' + DAIRE.slice(1)],
    'ilk-cevap': ['İlk cevap', 'M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20l1-4.3A7.5 7.5 0 1 1 20 12.5z'],
    'faydali-5': ['Faydalı: 5 oy', 'M7 11v9H4v-9zM7 11l4-7c1.5 0 2.5 1 2.2 2.6L12.6 10H18a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 16.8 20H7'],
    'faydali-25': ['Faydalı: 25 oy', 'M7 11v9H4v-9zM7 11l4-7c1.5 0 2.5 1 2.2 2.6L12.6 10H18a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 16.8 20H7'],
    'faydali-100': ['Faydalı: 100 oy', 'M7 11v9H4v-9zM7 11l4-7c1.5 0 2.5 1 2.2 2.6L12.6 10H18a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 16.8 20H7'],
    'sohbet-nesesi': ['Sohbetin neşesi', 'M4 5h12v8H9l-3 3v-3H4zM18 9h2v8h-2v3l-3-3h-4'],
    'katip-hiz-40': ['Katip: 40 net/dk', 'M13 3 5 14h6l-1 7 8-11h-6z'],
    'katip-hiz-60': ['Katip: 60 net/dk', 'M13 3 5 14h6l-1 7 8-11h-6z'],
    'katip-hiz-80': ['Katip: 80 net/dk', 'M13 3 5 14h6l-1 7 8-11h-6z'],
    'katip-seri-30': ['Katip: 30 gün seri', 'M5 5h14v15H5zM5 9h14M9 3v4M15 3v4M9 14l2 2 4-4'],
    'ders-yildizi': ['Ders yıldızı', 'M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-3-5.4 3 1.1-6L3.2 9.4l6.1-.8z'],
    'yerlesti': ['Yerleşti', 'M5 12.5l4.5 4.5L19 7.5'],
    'atandi': ['Atandı', 'M5 12.5l4.5 4.5L19 7.5']
  };
  var BEYAN = { 'yerlesti': 1, 'atandi': 1 };
  var DURUMLAR = [
    ['tercih-yapacagim', 'Tercih yapacağım'], ['basvuru-yapiyorum', 'Başvuru yapıyorum'], ['basvurdum', 'Başvurdum'],
    ['yerlestim', 'Yerleştim'], ['atandim', 'Atandım'], ['calisiyorum', 'Çalışıyorum']
  ];
  var RENKLER = [['yesil', 'Yeşil'], ['mavi', 'Mavi'], ['mor', 'Mor'], ['pembe', 'Pembe'], ['turuncu', 'Turuncu'], ['sari', 'Sarı'], ['turkuaz', 'Turkuaz'], ['gri', 'Gri']];
  var DUZEYLER = { lisans: 'Lisans', onlisans: 'Önlisans', ortaogretim: 'Ortaöğretim' };
  var GIZLILIK_VARSAYILAN = { profil: 'herkes', puan_goster: false, il_goster: false, katiplik_goster: false };   // sunucuyla aynı: varsayılan gizli
  var ZARF = 'M4 6h16v12H4zM4 7l8 6 8-6';
  var HEDEF_IKON = 'M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11zM12 12a2.2 2.2 0 1 0 0-4.4 2.2 2.2 0 0 0 0 4.4z';

  function ad(liste, k) { for (var i = 0; i < liste.length; i++) if (liste[i][0] === k) return liste[i][1]; return ''; }
  function varsayilanRenk(rumuz) { var a = AV(); return RENKLER[(a ? a.ton(rumuz) : 0) % RENKLER.length][0]; }
  function css() {
    if (document.getElementById('pk-css')) return;
    var l = document.createElement('link'); l.id = 'pk-css'; l.rel = 'stylesheet'; l.href = TABAN + 'profil-kart.css?v=' + SURUM; document.head.appendChild(l);
  }
  function avatarYukle() { var a = AV(); return a ? a.yukle() : Promise.resolve(); }
  // Sayfa içi onay penceresi (forum.js -> onay.js); eski bir forum.js önbellekteyse yerleşik pencere.
  function onayla(o) { return K().onayla ? K().onayla(o) : Promise.resolve(window.confirm(o.baslik + (o.metin ? '\n\n' + o.metin : ''))); }
  function avatarHtml(u, boyut) {
    var a = AV();
    if (!a) return '';
    if (u.rol === 'asistan') return '<span class="fr-av fr-av-bot" aria-hidden="true" style="width:' + boyut + 'px;height:' + boyut + 'px">' + ikon('M7 9h10v9H7zM12 5v4M10 13h.01M14 13h.01') + '</span>';
    if (u.rol === 'sistem') return '<span class="fr-av fr-av-site" aria-hidden="true" style="width:' + boyut + 'px;height:' + boyut + 'px"><img src="' + esc(K().kok()) + 'assets/logo-96.webp?v=2" alt="" width="' + boyut + '" height="' + boyut + '"></span>';
    return boyut >= 64 && a.canli ? a.canli(u, boyut) : a.html(u, boyut);   // büyük kartta Piixpal canlı, küçükte durağan
  }
  // Kart çizilmeden önce, avatar Piixpal ise bileşeni yükler (canlı gösterim için).
  function pxOnYukle(u) {
    var a = AV(); if (!a || !a.liste()) return Promise.resolve();
    var c = u.av === 'foto' ? null : a.coz(u.av) || a.varsayilan(u.rumuz);
    return c && c.set === 'px' ? a.piixYukle() : Promise.resolve();
  }
  function rozetHtml(k) {
    var r = ROZETLER[k];
    if (!r) return '';
    return '<li class="pk-rozet' + (BEYAN[k] ? ' pk-beyan' : '') + '" data-rozet="' + esc(k) + '">' + ikon(r[1]) + '<span>' + esc(r[0]) + (BEYAN[k] ? ' <small>beyan</small>' : '') + '</span></li>';
  }
  function tarihAy(sn) { return new Date(sn * 1000).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' }); }
  function sayiKutusu(ad_, d) { return '<div><dt>' + esc(ad_) + '</dt><dd>' + d + '</dd></div>'; }

  /* ---------- kart ---------- */
  // u: /uye/:rumuz yanıtı (ya da düzenleyicinin önizleme nesnesi). o: { tum: tüm rozetler, onizleme: eylem yok, sayfa: profil sayfası }
  function kartHtml(u, o) {
    o = o || {};
    var ben = K().uye(), kendi = !!(ben && ben.rumuz === u.rumuz);
    var renk = u.kart_rengi || varsayilanRenk(u.rumuz);
    var h = '<article class="pk-kart" data-renk="' + esc(renk) + '" aria-label="' + esc(u.rumuz) + ' profil kartı"><div class="pk-kapak" aria-hidden="true"></div><div class="pk-govde">'
      + '<div class="pk-av">' + avatarHtml(u, 96) + '</div><h2 class="pk-ad">' + esc(u.rumuz) + '</h2>';
    if (u.rol === 'asistan' || u.rol === 'sistem') {
      return h + '<p class="pk-alt">' + (u.rol === 'asistan' ? 'Otomatik yanıtlayıcı' : 'Site hesabı') + '</p></div></article>';
    }
    if (u.kisitli) {
      h += '<p class="pk-kisitli">' + (u.kisitli === 'uyeler' ? 'Bu profili yalnız üyeler görebilir.' : 'Bu üye profilini gizledi.') + '</p>';
      if (!o.onizleme) {
        h += '<div class="pk-eylemler">' + (u.kisitli === 'uyeler' ? '<button type="button" class="btn btn-ana" data-pk="giris">Giriş yap</button>' : '')
          + (u.dm_acik === false ? '' : '<a class="btn btn-ikinci" href="' + esc(K().kok()) + 'forum/?mesaj=' + encodeURIComponent(u.rumuz) + '">' + ikon(ZARF) + '<span>Mesaj gönder</span></a>') + '</div>';
      }
      return h + '</div></article>';
    }
    if (u.kayit) h += '<p class="pk-alt">' + esc(tarihAy(u.kayit)) + ' tarihinde katıldı</p>';
    var rl = (u.rozetler || []).filter(function (k) { return ROZETLER[k]; });
    if (rl.length) h += '<ul class="pk-rozetler" aria-label="Rozetler">' + rl.slice(0, o.tum ? 99 : 6).map(rozetHtml).join('') + (!o.tum && rl.length > 6 ? '<li class="pk-rozet pk-daha">+' + (rl.length - 6) + '</li>' : '') + '</ul>';
    var c = [];
    if (u.durum) c.push('<span class="pk-cip pk-durum" data-durum="' + esc(u.durum) + '">' + esc(ad(DURUMLAR, u.durum)) + '</span>');
    if (u.duzey && DUZEYLER[u.duzey]) c.push('<span class="fr-duzey-cip pk-cip" data-duzey="' + esc(u.duzey) + '">' + esc(DUZEYLER[u.duzey]) + '</span>');
    if (u.hedef) c.push('<span class="pk-cip pk-hedef">' + ikon(HEDEF_IKON) + '<span>' + esc(u.hedef) + '</span></span>');
    if (u.puan != null && !u.puan_gizli) c.push('<span class="pk-cip">' + esc((u.puan_turu ? u.puan_turu + ' ' : '') + String(u.puan).replace('.', ',')) + '</span>');
    if (u.iller && u.iller.length && !u.il_gizli) c.push('<span class="pk-cip">' + esc(u.iller.slice(0, 3).join(', ')) + (u.il_sayisi > 3 ? ' +' + (u.il_sayisi - 3) : '') + '</span>');
    else if (u.tum_turkiye && !u.il_gizli) c.push('<span class="pk-cip">Tüm Türkiye</span>');
    if (c.length) h += '<div class="pk-cipler">' + c.join('') + '</div>';
    if (u.hakkimda) h += '<p class="pk-hakkimda">' + esc(u.hakkimda) + '</p>';
    h += '<dl class="pk-sayilar">' + sayiKutusu('Soru', sayi(u.soru_sayisi)) + sayiKutusu('Cevap', sayi(u.cevap_sayisi)) + sayiKutusu('Faydalı oy', sayi(u.itibar)) + '</dl>';
    if (u.katip && !u.katip_gizli) {
      h += '<section class="pk-katip" aria-label="Katiplik"><h3>Katiplik</h3><dl>' + sayiKutusu('En iyi net', sayi(u.katip.net)) + sayiKutusu('En iyi net/dk', sayi(u.katip.dk))
        + sayiKutusu('Ders', sayi(u.katip.ders) + '/16') + sayiKutusu('Günlük seri', sayi(u.katip.seri) + ' gün') + '</dl></section>';
    }
    if (kendi && o.sayfa) {
      var bs = 0; try { bs = Object.keys(JSON.parse(localStorage.getItem('fr-basvuru') || '{}') || {}).length; } catch (x) { bs = 0; }
      h += '<p class="pk-not">Başvurduğum ilanlar: <b>' + sayi(bs) + '</b></p>';
    }
    if (!o.onizleme) {
      h += '<div class="pk-eylemler">';
      if (kendi) h += '<a class="btn btn-ana" href="' + esc(K().kok()) + '?profil=kart">Profilimi düzenle</a>';
      else if (u.dm_acik === false) h += '<p class="pk-not">Bu üye özel mesaj almıyor.</p>';
      else h += '<a class="btn btn-ana" href="' + esc(K().kok()) + 'forum/?mesaj=' + encodeURIComponent(u.rumuz) + '">' + ikon(ZARF) + '<span>Mesaj gönder</span></a>';
      if (!o.sayfa) h += '<a class="btn btn-ikinci" href="' + esc(K().kok()) + 'forum/?uye=' + encodeURIComponent(u.rumuz) + '">Profil sayfası</a>';
      if (!kendi && u.fs) h += '<button type="button" class="pk-bildir" data-pk="foto-bildir" data-rumuz="' + esc(u.rumuz) + '">Fotoğrafı bildir</button>';
      h += '</div>';
    }
    return h + '</div></article>';
  }
  function eylemleriBagla(kap, ustKapat) {
    kap.addEventListener('click', function (e) {
      var d = e.target.closest('[data-pk]');
      if (!d) return;
      var ne = d.getAttribute('data-pk');
      if (ne === 'giris') { if (ustKapat) ustKapat(); K().giris('Profili görmek için giriş yap'); }
      if (ne === 'foto-bildir') {
        if (!K().oturum()) { if (ustKapat) ustKapat(); K().giris('Bildirmek için giriş yap'); return; }
        onayla({ baslik: 'Fotoğraf bildirilsin mi?', metin: 'Uygunsuz fotoğrafları yöneticiler inceler ve kaldırır.', evet: 'Bildir' }).then(function (ok) {
          if (!ok) return;
          K().api('/uye/' + encodeURIComponent(d.getAttribute('data-rumuz')) + '/foto-bildir', { yontem: 'POST', govde: {} }).then(function (j) {
            K().bildir(j.zaten ? 'Bunu zaten bildirdin' : 'Bildirildi, teşekkürler'); d.disabled = true;
          }, function (h) { K().bildir(h.message); });
        });
      }
    });
  }

  /* ---------- alttan açılan kart ---------- */
  function ac(rumuz) {
    css();
    var eski = document.getElementById('fr-uye-kart'); if (eski) eski.remove();
    var onceki = document.activeElement;
    var kutu = el('<div class="fr-perde pk-perde" id="fr-uye-kart" role="dialog" aria-modal="true" aria-label="' + esc(rumuz) + '"><div class="pk-sayfa" tabindex="-1"><div class="pk-tutamak" aria-hidden="true"></div>'
      + '<button type="button" class="pk-kapat" aria-label="Kapat">×</button><div class="pk-ic"><p class="fr-yukleniyor">Yükleniyor…</p></div></div></div>');
    document.body.appendChild(kutu);
    var sayfa = kutu.querySelector('.pk-sayfa'), ic = kutu.querySelector('.pk-ic');
    function kapat() { kutu.remove(); document.removeEventListener('keydown', tus); try { if (onceki && onceki.focus && document.body.contains(onceki)) onceki.focus(); } catch (e) {} }
    function tus(e) {
      if (e.key === 'Escape') { kapat(); return; }
      if (e.key !== 'Tab') return;
      var l = Array.prototype.filter.call(sayfa.querySelectorAll('button,a[href],input,[tabindex="0"]'), function (x) { return !x.disabled && x.offsetParent !== null; });
      if (!l.length) return;
      var ilk = l[0], son = l[l.length - 1];
      if (e.shiftKey && (document.activeElement === ilk || document.activeElement === sayfa)) { e.preventDefault(); son.focus(); }
      else if (!e.shiftKey && document.activeElement === son) { e.preventDefault(); ilk.focus(); }
    }
    document.addEventListener('keydown', tus);
    kutu.onclick = function (e) { if (e.target === kutu || e.target.closest('.pk-kapat') || e.target.closest('a[href]')) kapat(); };
    eylemleriBagla(sayfa, kapat);
    sayfa.focus({ preventScroll: true });
    Promise.all([K().api('/uye/' + encodeURIComponent(rumuz)), avatarYukle()]).then(function (s) { return pxOnYukle(s[0]).then(function () { return s; }); }).then(function (s) {
      ic.innerHTML = kartHtml(s[0], {});
      var ilkEylem = ic.querySelector('.pk-eylemler a, .pk-eylemler button'); if (ilkEylem && matchMedia('(pointer:fine)').matches) ilkEylem.focus();
    }, function (h) { ic.innerHTML = '<p class="fr-bos">' + esc(h.durum === 404 ? 'Bu üye bulunamadı.' : h.message) + '</p>'; });
  }

  /* ---------- herkese açık profil sayfası (forum/?uye=<rumuz>) ---------- */
  function sayfa(kap, rumuz) {
    css();
    kap.innerHTML = '<p class="fr-geri-link"><a class="yazi-link" data-ic href="?">Forum</a></p><div class="pk-profil-sayfa"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
    var yer = kap.querySelector('.pk-profil-sayfa');
    eylemleriBagla(yer, null);
    Promise.all([K().api('/uye/' + encodeURIComponent(rumuz) + '?tam=1'), avatarYukle()]).then(function (s) { return pxOnYukle(s[0]).then(function () { return s; }); }).then(function (s) {
      var u = s[0];
      document.title = u.rumuz + ' — Profil — KPSS Tercihi';
      var h = kartHtml(u, { tum: true, sayfa: true });
      if (!u.kisitli) {
        if (u.sorular && u.sorular.length) {
          h += '<section class="pk-liste"><h3>Son soruları</h3><ul>' + u.sorular.map(function (b) {
            return '<li><a data-ic href="?b=' + b.id + '">' + esc(b.baslik) + '</a><small>' + sayi(b.yanit_sayisi) + ' cevap</small></li>';
          }).join('') + '</ul></section>';
        }
        if (u.cevaplar && u.cevaplar.length) {
          h += '<section class="pk-liste"><h3>En faydalı cevapları</h3><ul>' + u.cevaplar.map(function (c) {
            return '<li><a data-ic href="?b=' + c.baslik_id + '#y' + c.id + '">' + esc(c.kisa) + '</a><small>' + esc(c.baslik) + ' · ' + sayi(c.faydali) + ' faydalı</small></li>';
          }).join('') + '</ul></section>';
        }
      }
      yer.innerHTML = h;
    }, function (h) { yer.innerHTML = '<p class="fr-bos">' + esc(h.durum === 404 ? 'Bu üye bulunamadı.' : h.message) + '</p>'; });
  }

  /* ---------- fotoğraf kırpma ---------- */
  // Kare kırpar, 160x160 WebP (olmazsa JPEG) üretir; 24 KB altına inene kadar kaliteyi düşürür. Sonuç: Promise<Blob>.
  var FOTO_BOYUT = 160, FOTO_EN_COK = 24 * 1024;
  function blobUret(tuval, tur, kalite) { return new Promise(function (ok) { tuval.toBlob(function (b) { ok(b); }, tur, kalite); }); }
  function fotoCikar(tuval) {
    var turler = ['image/webp', 'image/jpeg'], kaliteler = [0.8, 0.7, 0.6, 0.5, 0.4];
    function dene(ti, ki) {
      if (ti >= turler.length) return Promise.reject(new Error('Fotoğraf 24 KB altına küçültülemedi. Daha sade bir fotoğraf dene.'));
      return blobUret(tuval, turler[ti], kaliteler[ki]).then(function (b) {
        if (!b || b.type !== turler[ti]) return dene(ti + 1, 0);   // tarayıcı WebP üretemedi: JPEG'e geç
        if (b.size <= FOTO_EN_COK) return b;
        return ki + 1 < kaliteler.length ? dene(ti, ki + 1) : dene(ti + 1, 0);
      });
    }
    return dene(0, 0);
  }
  function gorselAc(dosya) {
    if (window.createImageBitmap) return createImageBitmap(dosya).catch(function () { return gorselEski(dosya); });
    return gorselEski(dosya);
  }
  function gorselEski(dosya) {
    return new Promise(function (ok, red) {
      var url = URL.createObjectURL(dosya), im = new Image();
      im.onload = function () { URL.revokeObjectURL(url); ok(im); };
      im.onerror = function () { URL.revokeObjectURL(url); red(new Error('Bu dosya görsel olarak açılamadı.')); };
      im.src = url;
    });
  }
  // Kırpma penceresi: sürükle ve yakınlaştır (ok tuşları ve +/- de çalışır). tamam(blob) çağrılır.
  function kirpPenceresi(kap, dosya, tamam, iptal) {
    gorselAc(dosya).then(function (im) {
      var W = im.width || im.naturalWidth, H = im.height || im.naturalHeight, V = 240;
      if (!W || !H) throw new Error('Bu dosya görsel olarak açılamadı.');
      var s0 = V / Math.min(W, H), z = 1, cx = W / 2, cy = H / 2;
      var k = el('<div class="pk-kirp" role="group" aria-label="Fotoğrafı kırp"><p class="pk-not">Sürükleyerek konumlandır, kaydırıcıyla yakınlaştır. Fotoğraf yuvarlak görünür.</p>'
        + '<div class="pk-kirp-alan"><canvas width="' + V + '" height="' + V + '" tabindex="0" aria-label="Kırpma alanı. Ok tuşları kaydırır, artı ve eksi yakınlaştırır."></canvas><span class="pk-kirp-maske" aria-hidden="true"></span></div>'
        + '<label class="pk-yakin">Yakınlaştır<input type="range" min="1" max="3" step="0.02" value="1"></label>'
        + '<p class="pk-hata" role="alert" hidden></p><div class="pk-kirp-dugme"><button type="button" class="btn btn-ana" data-kirp="kullan">Kullan</button><button type="button" class="btn btn-ikinci" data-kirp="vazgec">Vazgeç</button></div></div>');
      kap.appendChild(k);
      var cv = k.querySelector('canvas'), g = cv.getContext('2d'), kay = k.querySelector('input'), hata = k.querySelector('.pk-hata');
      function sinirla() { var s = s0 * z; cx = Math.min(Math.max(cx, V / 2 / s), W - V / 2 / s); cy = Math.min(Math.max(cy, V / 2 / s), H - V / 2 / s); }
      function ciz(c, boyut) {
        var s = s0 * z, o = boyut / V, ctx = c.getContext('2d');
        ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, boyut, boyut);
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(im, (V / 2 - cx * s) * o, (V / 2 - cy * s) * o, W * s * o, H * s * o);
      }
      function yenile() { sinirla(); ciz(cv, V); }
      var surukle = null;
      cv.addEventListener('pointerdown', function (e) { surukle = { x: e.clientX, y: e.clientY }; try { cv.setPointerCapture(e.pointerId); } catch (x) {} });
      cv.addEventListener('pointermove', function (e) {
        if (!surukle) return;
        var s = s0 * z, r = cv.getBoundingClientRect(), oran = V / r.width;
        cx -= (e.clientX - surukle.x) * oran / s; cy -= (e.clientY - surukle.y) * oran / s; surukle = { x: e.clientX, y: e.clientY }; yenile();
      });
      ['pointerup', 'pointercancel'].forEach(function (a) { cv.addEventListener(a, function () { surukle = null; }); });
      cv.addEventListener('keydown', function (e) {
        var adim = 12 / (s0 * z), t = true;
        if (e.key === 'ArrowLeft') cx -= adim; else if (e.key === 'ArrowRight') cx += adim; else if (e.key === 'ArrowUp') cy -= adim; else if (e.key === 'ArrowDown') cy += adim;
        else if (e.key === '+' || e.key === '=') z = Math.min(3, z + 0.1); else if (e.key === '-') z = Math.max(1, z - 0.1); else t = false;
        if (t) { e.preventDefault(); kay.value = z; yenile(); }
      });
      kay.addEventListener('input', function () { z = Number(kay.value); yenile(); });
      k.addEventListener('click', function (e) {
        var d = e.target.closest('[data-kirp]');
        if (!d) return;
        if (d.getAttribute('data-kirp') === 'vazgec') { k.remove(); if (iptal) iptal(); return; }
        d.disabled = true; hata.hidden = true;
        var out = document.createElement('canvas'); out.width = out.height = FOTO_BOYUT; ciz(out, FOTO_BOYUT);
        fotoCikar(out).then(function (blob) { k.remove(); tamam(blob); }, function (h) { hata.textContent = h.message; hata.hidden = false; d.disabled = false; });
      });
      yenile(); cv.focus({ preventScroll: true });
    }).catch(function (h) { K().bildir(h && h.message ? h.message : 'Fotoğraf açılamadı.'); if (iptal) iptal(); });
  }

  /* ---------- "Kartım" düzenleyicisi ---------- */
  // Üç kısa bölüm: Görünüm (avatar, fotoğraf, kart rengi), Bilgiler (durum, hedef, hakkında), Gizlilik. Önizleme geniş ekranda yanda sabit,
  // telefonda tek dokunuşla açılır. Avatarlar setlere (önce piksel karakterler, sonra çizimler) ve gruplara ayrılmış, kayan küçük bir ızgaradadır.
  // secenek: { gomulu: profil penceresinin içinde (bölüm sekmeleri ve Kaydet düğmesi pencerededir), bolum: ilk bölüm,
  //            degisti(): kaydedilmemiş değişiklik durumu değişince, girisIste(): üye olmayan kişi "Üye ol" deyince }
  // Dönen denetçi: { uye, kirli(), kaydet() -> Promise<boolean>, bolum(ad) }. Gömülü değilse sekmeler ve Kaydet düğmesi düzenleyicinin içindedir.
  var KISIMLAR = [['gorunum', 'Görünüm'], ['bilgiler', 'Bilgiler'], ['gizlilik', 'Gizlilik']];
  var OK_IKON = 'M6 9l6 6 6-6';
  function duzenleyici(kap, secenek, ctrl) {
    secenek = secenek || {};
    ctrl = ctrl || {
      uye: false, _bolum: secenek.bolum || 'gorunum',
      kirli: function () { return false; }, kaydet: function () { return Promise.resolve(true); }, bolum: function (ad) { ctrl._bolum = ad; }
    };
    css();
    ctrl.uye = !!K().oturum();
    if (!ctrl.uye) { girisKarti(kap, secenek, ctrl); return ctrl; }
    kap.innerHTML = '<p class="fr-yukleniyor">Yükleniyor…</p>';
    // Aynı kaba yeniden kurulursa (pencere kapanıp hızla açıldı) geç gelen eski yükleme yeni düzenleyicinin üstüne çizmesin
    var nesil = kap._pkNesil = (kap._pkNesil || 0) + 1;
    var ben = K().uye();
    var benIste = ben && ben.rumuz ? Promise.resolve(null) : K().api('/ben');
    benIste.then(function (b0) {
      var rumuz = b0 && b0.uye ? b0.uye.rumuz : ben.rumuz;
      return Promise.all([b0 || K().api('/ben'), K().api('/uye/' + encodeURIComponent(rumuz)), avatarYukle()]);
    }).then(function (s) {
      if (!document.body.contains(kap) || kap._pkNesil !== nesil) return;
      kur(kap, s[0], s[1], secenek, ctrl);
    }, function (h) { if (kap._pkNesil !== nesil) return; kap.innerHTML = '<p class="fr-bos">' + esc(h && h.message ? h.message : 'Profil kartı şu an yüklenemedi.') + '</p>'; });
    return ctrl;
  }
  function girisKarti(kap, secenek, ctrl) {
    var rumuz = 'Misafir';
    kap.innerHTML = '<div class="pk-cta"><div class="pk-av">' + (AV() ? AV().html({ rumuz: rumuz }, 72) : '') + '</div><h3>Profil kartını oluştur</h3>'
      + '<p>Avatarını seç, kendini tanıt, hedefini yaz. Kartın forumda adının yanında görünür; neyin görüneceğine sen karar verirsin.</p>'
      + '<button type="button" class="btn btn-ana" data-pk-giris>Üye ol ya da giriş yap</button>'
      + '<p class="pk-not">Üyelik ücretsiz. Tercih bilgilerin üye olmadan da bu tarayıcıda çalışır.</p></div>';
    avatarYukle().then(function () { var a = kap.querySelector('.pk-cta .pk-av'); if (a && AV()) a.innerHTML = AV().html({ rumuz: rumuz }, 72); });
    kap.querySelector('[data-pk-giris]').onclick = function () {
      if (secenek.girisIste) secenek.girisIste();
      else K().giris('Profil kartın için giriş yap', function () { duzenleyici(kap, secenek, ctrl); });
    };
  }
  function kur(kap, ben, kendiKart, secenek, ctrl) {
    var u = ben.uye, kart = ben.kart || {};
    var d = {
      avatar: kart.avatar || null, hakkimda: kart.hakkimda || '', hedef: kart.hedef || '', durum: kart.durum || null, kart_rengi: kart.kart_rengi || null,
      gizlilik: Object.assign({}, GIZLILIK_VARSAYILAN, kart.gizlilik || {})
    };
    var fotoSurum = kart.foto_surum || null;
    var kayitli = JSON.stringify(d);
    var A = AV(), man = A && A.liste(), px = A && A.pxListe();
    var gruplar = man && man.gruplar ? man.gruplar : [{ anahtar: 'hepsi', ad: 'Avatarlar' }];
    var yasSn = Math.floor(Date.now() / 1000) - (kendiKart.kayit || 0), fotoIzin = yasSn >= 86400;
    var gomulu = !!secenek.gomulu, onizAcik = false, sonDurum = null;

    function onizlemeNesnesi() {
      var o = Object.assign({}, kendiKart, { rumuz: u.rumuz, rol: 'uye', kurucu: !!u.kurucu });
      o.av = d.avatar || undefined; o.fs = fotoSurum || undefined; o.fu = fotoSurum ? u.id : undefined;
      o.hakkimda = d.hakkimda; o.hedef = d.hedef; o.durum = d.durum; o.kart_rengi = d.kart_rengi;
      o.puan_gizli = !d.gizlilik.puan_goster; o.il_gizli = !d.gizlilik.il_goster; o.katip_gizli = !d.gizlilik.katiplik_goster;
      return o;
    }
    // Seçici durağan görüntü gösterir (tek tek 49 canlı sprite çalıştırılmaz); canlı önizleme yalnız kart önizlemesindedir.
    var oncekiSvgRenk = '', oncekiPx = { r: 'pixel', h: 0 };
    function secilen() { return d.avatar && d.avatar !== 'foto' && A ? A.coz(d.avatar) : null; }
    // Açık set ve grup: seçili avatarınki; yoksa ilk piksel grubu (piksel karakterler önce gelir).
    var aktifSet = px ? 'px' : 'svg', aktifGrup = '';
    (function () {
      var c = secilen();
      if (!c) return;
      var l = c.set === 'px' ? (px ? px.avatarlar : []) : (man ? man.avatarlar : []);
      for (var i = 0; i < l.length; i++) if (l[i].anahtar === c.k) { aktifSet = c.set; aktifGrup = l[i].grup; return; }
    })();
    function tile(deger, secili, ic, ad, yazili) {
      return '<label class="pk-sec' + (yazili ? ' pk-sec-yazili' : '') + (secili ? ' pk-secili' : '') + '" title="' + esc(ad) + '"><input type="radio" name="pk-av" value="' + esc(deger) + '"' + (secili ? ' checked' : '') + '>'
        + '<span class="pk-sec-ic">' + ic + '</span><span class="' + (yazili ? 'pk-sec-et' : 'pk-sec-ad') + '">' + esc(ad) + '</span></label>';
    }
    function dugmeler(l, ad, secili) {
      return l.map(function (x) { return '<button type="button" data-' + ad + '="' + esc(x[0]) + '" aria-pressed="' + (x[0] === secili ? 'true' : 'false') + '">' + esc(x[1]) + '</button>'; }).join('');
    }
    function avatarSeceneklerHtml() {
      var varsay = A ? A.varsayilanSvg(u.rumuz) : null, c = secilen();
      var seciliK = c && c.set === 'svg' ? c.k : '', seciliR = c && c.set === 'svg' ? c.r : (oncekiSvgRenk || (varsay ? varsay.r : 'lila'));
      var seciliP = c && c.set === 'px' ? c.k : '';
      var h = '<div class="pk-secenekler pk-ust-sec" role="radiogroup" aria-label="Avatar">' + tile('', !d.avatar, A ? A.html({ rumuz: u.rumuz }, 40) : '', 'Otomatik', true);
      if (fotoSurum && A) h += tile('foto', d.avatar === 'foto', A.html({ rumuz: u.rumuz, av: 'foto', fs: fotoSurum, fu: u.id }, 40), 'Fotoğrafım', true);
      h += '</div>';
      var setler = [];
      if (px) setler.push(['px', 'Piksel karakterler']);
      if (man) setler.push(['svg', 'Çizimler']);
      if (setler.length) {
        if (!setler.some(function (s) { return s[0] === aktifSet; })) aktifSet = setler[0][0];
        var liste = aktifSet === 'px' ? px.avatarlar : man.avatarlar;
        var gl = (aktifSet === 'px' ? px.gruplar : gruplar).filter(function (g) { return liste.some(function (a) { return a.grup === g.anahtar; }); });
        if (!gl.some(function (g) { return g.anahtar === aktifGrup; })) aktifGrup = gl.length ? gl[0].anahtar : '';
        var grupAdi = ''; gl.forEach(function (g) { if (g.anahtar === aktifGrup) grupAdi = g.ad; });
        h += '<div class="pk-setler" role="group" aria-label="Avatar seti">' + dugmeler(setler, 'pk-set', aktifSet) + '</div>'
          + '<div class="pk-gruplar" role="group" aria-label="Grup">' + dugmeler(gl.map(function (g) { return [g.anahtar, g.ad]; }), 'pk-grup', aktifGrup) + '</div>'
          + '<div class="pk-secenekler pk-izgara" role="radiogroup" aria-label="' + esc(grupAdi) + '">' + liste.filter(function (a) { return a.grup === aktifGrup; }).map(function (a) {
            return aktifSet === 'px'
              ? tile('p:' + a.anahtar, seciliP === a.anahtar, A.html({ rumuz: u.rumuz, av: 'px.' + a.anahtar + ':pixel.0' }, 44), a.ad)
              : tile('s:' + a.anahtar, seciliK === a.anahtar, A.html({ rumuz: u.rumuz, av: a.anahtar + ':' + seciliR }, 44), a.ad);
          }).join('') + '</div>';
      }
      if (c && c.set === 'svg' && man) {
        h += '<fieldset class="pk-ince"><legend>Avatar zemini</legend><div class="pk-secenekler pk-renkler" role="radiogroup" aria-label="Avatar zemin rengi">' + man.renkler.map(function (r) {
          var secili = seciliR === r.anahtar;
          return '<label class="pk-sec pk-renk' + (secili ? ' pk-secili' : '') + '" title="' + esc(r.ad) + '"><input type="radio" name="pk-avr" value="' + esc(r.anahtar) + '"' + (secili ? ' checked' : '') + '><span class="pk-ornek" style="background:' + esc(r.renk) + '"></span><span class="pk-sec-ad">' + esc(r.ad) + '</span></label>';
        }).join('') + '</div></fieldset>';
      }
      if (c && c.set === 'px' && px) {
        h += '<fieldset class="pk-ince"><legend>Çizim biçimi</legend><div class="pk-secenekler" role="radiogroup" aria-label="Piksel karakter görünümü">' + px.bicimler.map(function (b) {
          return '<label class="pk-sec pk-yazi' + (c.r === b.anahtar ? ' pk-secili' : '') + '"><input type="radio" name="pk-pxb" value="' + esc(b.anahtar) + '"' + (c.r === b.anahtar ? ' checked' : '') + '><span>' + esc(b.ad) + '</span></label>';
        }).join('') + '</div></fieldset><fieldset class="pk-ince"><legend>Renk tonu</legend><div class="pk-secenekler pk-renkler" role="radiogroup" aria-label="Renk tonu">' + px.tonlar.map(function (t) {
          var resim = A.anlik({ k: c.k, r: 'pixel', h: 0 });
          return '<label class="pk-sec pk-renk' + (c.h === t.ton ? ' pk-secili' : '') + '" title="' + esc(t.ad) + '"><input type="radio" name="pk-pxt" value="' + t.ton + '"' + (c.h === t.ton ? ' checked' : '') + '><span class="pk-ornek pk-ton">' + (resim ? '<img alt="" src="' + esc(resim) + '" style="filter:hue-rotate(' + t.ton + 'deg)">' : '') + '</span><span class="pk-sec-ad">' + esc(t.ad) + '</span></label>';
        }).join('') + '</div></fieldset>';
      }
      return h;
    }
    function secim(ad, deger, etiket) {   // yazılı radyo düğmesi (durum, gizlilik)
      return '<label class="pk-sec pk-yazi' + (deger.secili ? ' pk-secili' : '') + '"><input type="radio" name="' + ad + '" value="' + esc(deger.v) + '"' + (deger.secili ? ' checked' : '') + '><span>' + esc(etiket) + '</span></label>';
    }
    function yerlestir() {
      var b = ctrl._bolum;
      if (!KISIMLAR.some(function (x) { return x[0] === b; })) b = ctrl._bolum = 'gorunum';
      kap.innerHTML = '<div class="pk-duzen' + (gomulu ? ' pk-gomulu' : '') + '">'
        + '<aside class="pk-onizleme' + (onizAcik ? ' pk-acik' : '') + '" aria-label="Kart önizlemesi">'
        + '<button type="button" class="pk-onizleme-d" aria-expanded="' + (onizAcik ? 'true' : 'false') + '" aria-controls="pk-oniz-ic"><span class="pk-mini" data-mini></span><span>Kartını önizle</span>' + ikon(OK_IKON, 'pk-ok') + '</button>'
        + '<div class="pk-onizleme-ic" id="pk-oniz-ic" aria-live="polite"></div>'
        + '<a class="pk-sayfam" href="' + esc(K().kok()) + 'forum/?uye=' + encodeURIComponent(u.rumuz) + '">Herkese açık sayfanı gör</a></aside>'
        + '<form class="pk-form" novalidate>'
        + (gomulu ? '' : '<div class="pk-kisim-sekme" role="tablist" aria-label="Kart bölümleri">' + KISIMLAR.map(function (x) {
          return '<button type="button" role="tab" id="pk-k-' + x[0] + '" data-pk-kisim="' + x[0] + '" aria-controls="pk-kisim-' + x[0] + '" aria-selected="' + (x[0] === b ? 'true' : 'false') + '" tabindex="' + (x[0] === b ? '0' : '-1') + '">' + x[1] + '</button>';
        }).join('') + '</div>')
        + '<p class="pk-hata" role="alert" hidden data-hata></p>'
        // ----- Görünüm -----
        + '<section class="pk-kisim" id="pk-kisim-gorunum" data-kisim="gorunum"' + (gomulu ? ' aria-label="Görünüm"' : ' role="tabpanel" aria-labelledby="pk-k-gorunum"') + (b === 'gorunum' ? '' : ' hidden') + '>'
        + '<fieldset class="pk-bolum"><legend>Avatarın</legend><div data-avatarlar></div>'
        + '<div class="pk-foto"><button type="button" class="btn btn-ikinci" data-foto-sec' + (fotoIzin ? '' : ' disabled') + '>' + (fotoSurum ? 'Fotoğrafı değiştir' : 'Fotoğraf yükle') + '</button>'
        + (fotoSurum ? '<button type="button" class="btn btn-ikinci pk-tehlike" data-foto-sil>Fotoğrafı kaldır</button>' : '')
        + '<input type="file" accept="image/*" hidden data-foto-dosya>'
        + '<p class="pk-not">' + (fotoIzin ? 'Kare kırpılır ve küçültülür; günde en çok 3 kez yükleyebilirsin. Uygunsuz fotoğraflar kaldırılır.' : 'Fotoğraf yüklemek için hesabının 24 saatlik olması gerekir; o zamana kadar hazır avatarlardan seç.') + '</p>'
        + '<p class="pk-hata" role="alert" hidden data-foto-hata></p></div><div data-kirp-yer></div></fieldset>'
        + '<fieldset class="pk-bolum"><legend>Kart rengi</legend><div class="pk-secenekler pk-renkler" role="radiogroup" aria-label="Kart rengi">'
        + RENKLER.map(function (r) { var secili = (d.kart_rengi || '') === r[0]; return '<label class="pk-sec pk-renk' + (secili ? ' pk-secili' : '') + '" title="' + r[1] + '"><input type="radio" name="pk-krenk" value="' + r[0] + '"' + (secili ? ' checked' : '') + '><span class="pk-ornek pk-kr" data-renk="' + r[0] + '"></span><span class="pk-sec-ad">' + r[1] + '</span></label>'; }).join('')
        + '</div></fieldset></section>'
        // ----- Bilgiler -----
        + '<section class="pk-kisim" id="pk-kisim-bilgiler" data-kisim="bilgiler"' + (gomulu ? ' aria-label="Bilgiler"' : ' role="tabpanel" aria-labelledby="pk-k-bilgiler"') + (b === 'bilgiler' ? '' : ' hidden') + '>'
        + '<fieldset class="pk-bolum"><legend>Durumun</legend><div class="pk-secenekler pk-durumlar" role="radiogroup" aria-label="Durum">'
        + secim('pk-durum', { v: '', secili: !d.durum }, 'Belirtme') + DURUMLAR.map(function (x) { return secim('pk-durum', { v: x[0], secili: d.durum === x[0] }, x[1]); }).join('')
        + '</div><p class="pk-not">“Yerleştim” ve “Atandım” kendi beyanındır; kartında “beyan” etiketiyle görünür.</p></fieldset>'
        + '<div class="pk-bolum"><label for="pk-hedef">Hedefin</label><input class="alan" id="pk-hedef" maxlength="60" autocomplete="off" placeholder="Örn. Ankara adliye katipliği" value="' + esc(d.hedef) + '"><p class="pk-say" data-say="hedef"></p></div>'
        + '<div class="pk-bolum"><label for="pk-hakkimda">Hakkında</label><textarea class="alan" id="pk-hakkimda" maxlength="160" rows="3" placeholder="Kendini kısaca tanıt (bağlantı, telefon, e-posta yazma)">' + esc(d.hakkimda) + '</textarea><p class="pk-say" data-say="hakkimda"></p></div>'
        + '</section>'
        // ----- Gizlilik -----
        + '<section class="pk-kisim" id="pk-kisim-gizlilik" data-kisim="gizlilik"' + (gomulu ? ' aria-label="Gizlilik"' : ' role="tabpanel" aria-labelledby="pk-k-gizlilik"') + (b === 'gizlilik' ? '' : ' hidden') + '>'
        + '<fieldset class="pk-bolum"><legend>Profilini kim görebilir?</legend><div class="pk-secenekler pk-durumlar" role="radiogroup" aria-label="Profilimi kim görebilir">'
        + [['herkes', 'Herkes'], ['uyeler', 'Yalnız üyeler'], ['gizli', 'Gizli']].map(function (x) { return secim('pk-gprofil', { v: x[0], secili: d.gizlilik.profil === x[0] }, x[1]); }).join('')
        + '</div><p class="pk-not">Gizli profilde kartında yalnız rumuzun ve avatarın görünür. Mesajların forumda her zaman görünür.</p></fieldset>'
        + '<fieldset class="pk-bolum"><legend>Kartında görünsün</legend>'
        + [['puan_goster', 'KPSS puanım'], ['il_goster', 'Çalışmak istediğim iller'], ['katiplik_goster', 'Katiplik sonuçlarım']].map(function (x) {
          return '<label class="pk-anahtar"><span>' + x[1] + '</span><input type="checkbox" data-g="' + x[0] + '"' + (d.gizlilik[x[0]] ? ' checked' : '') + '></label>';
        }).join('')
        + '<p class="pk-not">Hepsi varsayılan olarak gizlidir. Katiplik sonuçların açıksa avatarın katiplik liderlik tablosunda da görünür. Öğrenim düzeyin her zaman görünür.</p></fieldset>'
        + '</section>'
        + (gomulu ? '' : '<div class="pk-alt-cubuk"><p class="pk-kayit-durum" data-kayit-durum aria-live="polite"></p><button type="submit" class="btn btn-ana" data-kaydet disabled>Kaydet</button></div>')
        + '</form></div>';
      kap.querySelector('[data-avatarlar]').innerHTML = avatarSeceneklerHtml();
      sayaclar(); onizle(); durumGuncelle(true);
    }
    function onizle() {
      var yer = kap.querySelector('.pk-onizleme-ic'), o = onizlemeNesnesi();
      if (yer) yer.innerHTML = kartHtml(o, { onizleme: true, tum: false });
      var m = kap.querySelector('[data-mini]'); if (m && A) m.innerHTML = A.html(o, 28);
      var c = secilen();
      if (A && ((c && c.set === 'px') || (!d.avatar && (A.varsayilan(u.rumuz) || {}).set === 'px')) && !A.pxHazirMi()) A.piixYukle().then(function (ok) { if (ok && document.body.contains(kap)) onizle(); });
    }
    function sayaclar() {
      var h = kap.querySelector('#pk-hedef'), k = kap.querySelector('#pk-hakkimda');
      kap.querySelector('[data-say=hedef]').textContent = h.value.length + '/60';
      kap.querySelector('[data-say=hakkimda]').textContent = k.value.length + '/160';
    }
    ctrl.kirli = function () { return JSON.stringify(d) !== kayitli; };
    // Kaydet düğmesi ve durum yazısı (gömülüyse pencere kendi düğmesini secenek.degisti ile günceller)
    function durumGuncelle(ilk, kaydedildi) {
      var k = ctrl.kirli();
      var b = kap.querySelector('[data-kaydet]'), y = kap.querySelector('[data-kayit-durum]');
      if (b) b.disabled = !k;
      if (y) y.textContent = k ? 'Kaydedilmemiş değişiklik var' : kaydedildi ? 'Kaydedildi' : '';
      if (y) y.classList.toggle('pk-kirli', k);
      if (secenek.degisti && (ilk || sonDurum !== k || kaydedildi)) secenek.degisti(k, !!kaydedildi);
      sonDurum = k;
    }
    function hataGoster(m) { var p = kap.querySelector('[data-hata]'); if (p) { p.textContent = m || ''; p.hidden = !m; } }
    function degisti() { sayaclar(); onizle(); durumGuncelle(); }
    function avatarSec(ad) {   // ad: değişen denetim adı
      var cur = secilen();
      if (ad === 'pk-av') {
        var k = kap.querySelector('input[name=pk-av]:checked'), v = k ? k.value : '';
        if (cur && cur.set === 'svg') oncekiSvgRenk = cur.r;
        if (cur && cur.set === 'px') oncekiPx = { r: cur.r, h: cur.h };
        if (v === '') d.avatar = null;
        else if (v === 'foto') d.avatar = 'foto';
        else if (v.indexOf('s:') === 0) d.avatar = A.dizge({ set: 'svg', k: v.slice(2), r: oncekiSvgRenk || (A.varsayilanSvg(u.rumuz) || {}).r || 'lila' });
        else d.avatar = A.dizge({ set: 'px', k: v.slice(2), r: oncekiPx.r, h: oncekiPx.h });
      } else if (cur && ad === 'pk-avr' && cur.set === 'svg') { cur.r = kap.querySelector('input[name=pk-avr]:checked').value; d.avatar = A.dizge(cur); }
      else if (cur && cur.set === 'px') {
        if (ad === 'pk-pxb') cur.r = kap.querySelector('input[name=pk-pxb]:checked').value; else cur.h = Number(kap.querySelector('input[name=pk-pxt]:checked').value);
        d.avatar = A.dizge(cur);
      }
    }
    function secenekleriCiz(odakSecici) {
      var y = kap.querySelector('[data-avatarlar]'); y.innerHTML = avatarSeceneklerHtml();
      var odak = odakSecici && kap.querySelector(odakSecici); if (odak) odak.focus();
    }
    ctrl.bolum = function (ad) {
      if (!KISIMLAR.some(function (x) { return x[0] === ad; })) return;
      ctrl._bolum = ad;
      kap.querySelectorAll('.pk-kisim').forEach(function (s) { s.hidden = s.getAttribute('data-kisim') !== ad; });
      kap.querySelectorAll('[data-pk-kisim]').forEach(function (t) { var a = t.getAttribute('data-pk-kisim') === ad; t.setAttribute('aria-selected', a ? 'true' : 'false'); t.tabIndex = a ? 0 : -1; });
    };
    ctrl.kaydet = function () {
      if (!ctrl.kirli()) return Promise.resolve(true);
      hataGoster('');
      var b = kap.querySelector('[data-kaydet]'); if (b) { b.disabled = true; b.textContent = 'Kaydediliyor…'; }
      return K().api('/ben/kart', { yontem: 'POST', govde: d }).then(function (j) {
        var k = j.kart || {};
        d.avatar = k.avatar || null; d.hakkimda = k.hakkimda || ''; d.hedef = k.hedef || '';
        kayitli = JSON.stringify(d);
        var h = kap.querySelector('#pk-hedef'), t = kap.querySelector('#pk-hakkimda');   // sunucu boşlukları kırpabilir: alanlar kayıtla aynı kalsın
        if (h) h.value = d.hedef; if (t) t.value = d.hakkimda;
        K().uyeGuncelle(k);
        if (b) b.textContent = 'Kaydet';
        sayaclar(); onizle(); durumGuncelle(false, true);
        return true;
      }, function (h) { hataGoster(h.message); if (b) { b.textContent = 'Kaydet'; b.disabled = false; } return false; });
    };
    // yerlestir() formu baştan çizer (fotoğraf yükleyince/kaldırınca da): dinleyiciler her çizimden sonra yeni forma yeniden bağlanır.
    function yenidenCiz() { yerlestir(); bagla(); }
    yenidenCiz();
    function bagla() {
      var form = kap.querySelector('form'), onz = kap.querySelector('.pk-onizleme');
      kap.querySelector('.pk-onizleme-d').onclick = function () {
        onizAcik = !onizAcik; onz.classList.toggle('pk-acik', onizAcik); this.setAttribute('aria-expanded', onizAcik ? 'true' : 'false');
      };
      form.addEventListener('click', function (e) {
        var s = e.target.closest('[data-pk-set]'), g = e.target.closest('[data-pk-grup]'), t = e.target.closest('[data-pk-kisim]');
        if (s) { aktifSet = s.getAttribute('data-pk-set'); aktifGrup = ''; secenekleriCiz('[data-pk-set="' + aktifSet + '"]'); }
        else if (g) { aktifGrup = g.getAttribute('data-pk-grup'); secenekleriCiz('[data-pk-grup="' + aktifGrup + '"]'); }
        else if (t) ctrl.bolum(t.getAttribute('data-pk-kisim'));
      });
      var sekme = kap.querySelector('.pk-kisim-sekme');
      if (sekme) sekme.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
        e.preventDefault();
        var i = 0; KISIMLAR.forEach(function (x, n) { if (x[0] === ctrl._bolum) i = n; });
        var y = KISIMLAR[(i + (e.key === 'ArrowRight' ? 1 : KISIMLAR.length - 1)) % KISIMLAR.length][0];
        ctrl.bolum(y); kap.querySelector('#pk-k-' + y).focus();
      });
      form.addEventListener('change', function (e) {
        var t = e.target;
        if (t.name === 'pk-av' || t.name === 'pk-avr' || t.name === 'pk-pxb' || t.name === 'pk-pxt') {
          avatarSec(t.name);
          // renk seçilince seçili avatar korunur; avatar seçilince renk korunur: seçenekleri yeniden çiz (önizleme renkleri de güncellensin)
          secenekleriCiz('input[name=' + t.name + ']:checked');
        } else if (t.name === 'pk-durum') d.durum = t.value || null;
        else if (t.name === 'pk-krenk') d.kart_rengi = t.value || null;
        else if (t.name === 'pk-gprofil') d.gizlilik.profil = t.value;
        else if (t.getAttribute('data-g')) d.gizlilik[t.getAttribute('data-g')] = t.checked;
        kap.querySelectorAll('.pk-sec').forEach(function (l) { var i = l.querySelector('input'); if (i && i.type === 'radio') l.classList.toggle('pk-secili', i.checked); });
        degisti();
      });
      form.addEventListener('input', function (e) {
        if (e.target.id === 'pk-hedef') d.hedef = e.target.value;
        else if (e.target.id === 'pk-hakkimda') d.hakkimda = e.target.value;
        else return;
        degisti();
      });
      var dosya = kap.querySelector('[data-foto-dosya]'), fHata = kap.querySelector('[data-foto-hata]');
      function fotoHata(m) { fHata.textContent = m || ''; fHata.hidden = !m; }
      kap.querySelector('[data-foto-sec]').onclick = function () { fotoHata(''); dosya.value = ''; dosya.click(); };
      dosya.onchange = function () {
        var f = dosya.files && dosya.files[0];
        if (!f) return;
        if (!/^image\//.test(f.type) && f.type) { fotoHata('Lütfen bir görsel dosyası seç.'); return; }
        if (f.size > 15 * 1024 * 1024) { fotoHata('Dosya çok büyük (en çok 15 MB).'); return; }
        kirpPenceresi(kap.querySelector('[data-kirp-yer]'), f, function (blob) {
          fotoHata('Yükleniyor…');
          K().api('/ben/foto', { yontem: 'POST', ham: blob }).then(function (j) {
            fotoSurum = j.foto_surum; d.avatar = 'foto'; kayitli = JSON.stringify(Object.assign({}, JSON.parse(kayitli), { avatar: 'foto' }));
            K().uyeGuncelle({ avatar: 'foto', foto_surum: fotoSurum }); K().bildir('Fotoğrafın yüklendi');
            yenidenCiz();
          }, function (h) { fotoHata(h.message); });
        }, function () {});
      };
      var sil = kap.querySelector('[data-foto-sil]');
      if (sil) sil.onclick = function () {
        onayla({ baslik: 'Fotoğrafın kaldırılsın mı?', metin: 'Yerine otomatik avatarın ya da seçtiğin hazır avatar görünür.', evet: 'Kaldır', tehlike: true }).then(function (ok) {
          if (!ok) return;
          K().api('/ben/foto', { yontem: 'DELETE' }).then(function (j) {
            fotoSurum = null; if (d.avatar === 'foto') d.avatar = j.avatar || null;
            kayitli = JSON.stringify(Object.assign({}, JSON.parse(kayitli), { avatar: d.avatar }));
            K().uyeGuncelle({ avatar: d.avatar, foto_surum: null }); K().bildir('Fotoğrafın kaldırıldı'); yenidenCiz();
          }, function (h) { fotoHata(h.message); });
        });
      };
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (!gomulu) ctrl.kaydet();
      });
    }
  }

  window.kitKart = { kartHtml: kartHtml, ac: ac, sayfa: sayfa, duzenleyici: duzenleyici, css: css, rozetler: ROZETLER, durumlar: DURUMLAR, renkler: RENKLER, avatarHtml: avatarHtml };
})();
