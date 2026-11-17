/* KPSS Tercihi: üst çubuktaki hesap girişi (Kasım 2026). Her sayfada yüklenir (küçük, ertelenmiş).
   Giriş yoksa "Giriş yap" düğmesi, varsa avatar + küçük menü gösterir. Giriş penceresi, bildirim ayarları ve çıkış forum.js'tedir;
   forum.js (ve css'i) o sayfada yoksa yalnız kullanıcı dokununca yüklenir, bu yüzden sayfalar yavaşlamaz.
   Kayıtlı ilanların hesapla birleştirme kuralı (birlestir) burada, testlenebilir saf işlev olarak durur. */
(function () {
  'use strict';
  var KIMLIK = /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})$/i;   // sunucudaki desenle aynı (forum/src/yardimci.js)
  var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  var KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i=';   // Kariyer Kapısı ilanlarının sitedeki "id"si (bot/mudahale.py ile aynı); ilan anahtarı sonundaki UUID'dir
  var EN_COK = 300;
  function gecerli(x) { return typeof x === 'string' && KIMLIK.test(x); }
  // Sitedeki kayıtlı liste "id"leri tutar (Kariyer Kapısı için adres, diğerlerinde anahtarın kendisi); hesaba ilan ANAHTARI gider.
  function anahtar(id) {
    if (typeof id !== 'string') return null;
    if (KIMLIK.test(id)) return id.toLowerCase();
    if (id.indexOf(KK) === 0 && UUID.test(id.slice(KK.length))) return id.slice(KK.length).toLowerCase();
    return null;
  }
  function yerelKimlik(a) { return UUID.test(a) ? KK + a : a; }
  function tekrarsiz(l) { var g = Object.create(null), c = []; l.forEach(function (x) { if (typeof x === 'string' && x && x.length <= 80 && !g[x]) { g[x] = 1; c.push(x); } }); return c; }
  function sunucuAnahtarlari(sunucu) { return tekrarsiz(Array.isArray(sunucu) ? sunucu : []).filter(gecerli).map(function (x) { return x.toLowerCase(); }); }
  function yerelHaritasi(yerel) {   // anahtar -> yerelde saklanan kimlik; anahtarı olmayan (hesaba gitmeyen) kayıtlar ayrı
    var l = tekrarsiz(Array.isArray(yerel) ? yerel : []), h = Object.create(null), kalan = [];
    l.forEach(function (x) { var a = anahtar(x); if (a === null) kalan.push(x); else if (!(a in h)) h[a] = x; });
    return { harita: h, kalan: kalan, anahtarlar: Object.keys(h) };
  }
  function esit(a, b) { return a.length === b.length && a.every(function (x, i) { return x === b[i]; }); }
  function gonderilecek(yerel) { return yerelHaritasi(yerel).anahtarlar.slice(-EN_COK); }
  // Girişte: sunucu sırası önde, yerelde olup sunucuda olmayanlar arkaya; 300'ü aşarsa en eskiler düşer.
  // dönen: yerel (cihazda saklanacak), gonderilecek (sunucuya, anahtarlar), degisti (sunucudaki liste farklıysa true: bir kez yüklenir).
  function birlestir(sunucu, yerel) {
    var s = sunucuAnahtarlari(sunucu), y = yerelHaritasi(yerel), g = Object.create(null), tum = [];
    s.concat(y.anahtarlar).forEach(function (a) { if (!g[a]) { g[a] = 1; tum.push(a); } });
    if (tum.length > EN_COK) tum = tum.slice(-EN_COK);
    return { yerel: tum.map(function (a) { return y.harita[a] || yerelKimlik(a); }).concat(y.kalan), gonderilecek: tum, degisti: !esit(tum, s) };
  }
  // Eşleşmiş hesapta hesap esastır: yerel liste sunucudakine çevrilir (yerelde bulunan kimlikler korunur, hesaba gitmeyenler kalır).
  function esitle(sunucu, yerel) {
    var s = sunucuAnahtarlari(sunucu), y = yerelHaritasi(yerel);
    return { yerel: s.map(function (a) { return y.harita[a] || yerelKimlik(a); }).concat(y.kalan), ayni: esit(y.anahtarlar.slice(-EN_COK), s) };
  }
  var disari = { birlestir: birlestir, esitle: esitle, gonderilecek: gonderilecek, anahtar: anahtar, yerelKimlik: yerelKimlik, gecerli: gecerli };
  if (typeof module === 'object' && module && module.exports) module.exports = disari;
  if (typeof document === 'undefined') return;
  window.kitKayitli = disari;
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var bet = document.currentScript;
  var FS = (bet && bet.getAttribute('data-f')) || '1';
  var TABAN = bet && bet.src ? bet.src.replace(/hesap\.js.*$/, '') : '/';
  var nav = document.getElementById('tb-nav'), marka = document.querySelector('.tb-marka');
  if (!nav) return;
  var profil = nav.querySelector('.tb-ikon');
  var mh = (marka && marka.getAttribute('href')) || '';
  var KOK = mh.charAt(0) === '#' ? '' : mh.replace(/[^\/]*$/, '');   // sayfanın site köküne göreli yolu ("", "../", "../../")

  function oku(a) { try { return JSON.parse(localStorage.getItem(a)); } catch (e) { return null; } }
  function yaz(a, d) { try { if (d == null) localStorage.removeItem(a); else localStorage.setItem(a, JSON.stringify(d)); } catch (e) {} }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ton(ad) { var h = 0; ad = ad || '?'; for (var i = 0; i < ad.length; i++) h = (h * 31 + ad.charCodeAt(i)) % 360; return h; }

  /* ---------- forum.js'i yalnız gerektiğinde yükle ---------- */
  var yuk = null;
  function forumYukle() {
    if (window.kitHesap) return Promise.resolve();
    if (yuk) return yuk;
    yuk = new Promise(function (ok, red) {
      function hazir() { if (window.kitHesap) ok(); else { yuk = null; red(new Error('forum')); } }
      if (document.querySelector('script[src*="forum.js"]')) {   // sayfada zaten var, henüz çalışmadıysa bekle
        var n = 0, t = setInterval(function () { if (window.kitHesap || ++n > 50) { clearInterval(t); hazir(); } }, 100);
        return;
      }
      window.kitForumTembel = true;   // yalnız hesap penceresi için yüklendi: sayfa içi rozet taraması vb. başlamaz
      var bekle = ['forum.css', 'forum-sohbet.css'].map(function (h) {
        return new Promise(function (b) {
          var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = TABAN + h + '?v=' + FS; l.onload = l.onerror = b; document.head.appendChild(l);
        });
      });
      var s = document.createElement('script'); s.async = true; s.src = TABAN + 'forum.js?v=' + FS;
      s.onload = function () { Promise.all(bekle).then(hazir); };
      s.onerror = function () { yuk = null; red(new Error('forum')); };
      document.head.appendChild(s);
    });
    return yuk;
  }
  function forumdan(ad) {
    return forumYukle().then(function () { window.kitHesap[ad](); }, function () { gecici('Bağlantı kurulamadı, tekrar dene.'); });
  }
  var tTimer = 0;
  function gecici(m) {
    var t = document.getElementById('hs-toast');
    if (!t) { t = document.createElement('div'); t.id = 'hs-toast'; t.className = 'hs-toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = m; t.hidden = false; clearTimeout(tTimer); tTimer = setTimeout(function () { t.hidden = true; }, 2800);
  }

  /* ---------- avatar (avatar-ortak.js yalnız giriş yapılmışsa yüklenir) ve katiplik eşitleme ---------- */
  var avVaadi = null;
  function avatarKit() {
    if (!avVaadi) {
      avVaadi = (window.kitAvatar ? Promise.resolve() : new Promise(function (ok, red) {
        var s = document.createElement('script'); s.async = true; s.src = TABAN + 'avatar-ortak.js?v=' + FS; s.onload = ok; s.onerror = red; document.head.appendChild(s);
      })).then(function () { return window.kitAvatar.yukle(); }, function () {});
    }
    return avVaadi;
  }
  var katipYuklendi = false;
  function katipBaslat() {   // katiplik sayfalarında, giriş varsa: veriyi hesapla eşitleyen küçük modül
    if (katipYuklendi || !/\/katiplik\//.test(location.pathname) || !oku('fr-oturum')) return;
    katipYuklendi = true;
    var s = document.createElement('script'); s.async = true; s.src = TABAN + 'katip-senkron.js?v=' + FS;
    s.onerror = function () { katipYuklendi = false; };
    document.head.appendChild(s);
  }

  /* ---------- /ben (forum.js olmayan sayfalarda; olan sayfalarda forum.js yoklar) ---------- */
  function benCek() {
    var o = oku('fr-oturum');
    // forum.js sayfadaysa (ilan ve forum sayfalarında hesap.js'ten SONRA çalışır) /ben'i o çeker; iki kez D1 okuması olmasın
    if (window.kitHesap || !o || document.querySelector('script[src*="forum.js"]')) return;
    if (Date.now() - (oku('fr-hesap-t') || 0) < 120000 || Date.now() - (oku('fr-ben-t') || 0) < 120000) return;
    yaz('fr-hesap-t', Date.now());
    fetch(API + '/ben', { headers: { Authorization: 'Bearer ' + o } }).then(function (r) {
      if (r.status === 401) { yaz('fr-oturum', null); yaz('fr-uye', null); ciz(); return null; }
      return r.ok ? r.json() : null;
    }).then(function (j) {
      if (j && j.uye) { yaz('fr-uye', j.uye); yaz('fr-ozel-sayi', j.uye.ozel_okunmamis || 0); ciz(); }
    }).catch(function () {});
  }

  /* ---------- çizim ---------- */
  var kap = null, imza = '';
  function rozetler() {
    var n = oku('fr-ozel-sayi') || 0;
    if (kap) Array.prototype.forEach.call(kap.querySelectorAll('[data-ozel-sayi]'), function (b) { b.textContent = n ? (n > 9 ? '9+' : n) : ''; b.hidden = !n; });
  }
  function menuKapat(odak) {
    if (!kap) return;
    var m = kap.querySelector('.hs-menu'), d = kap.querySelector('.hs-av');
    if (m) m.hidden = true;
    if (d) { d.setAttribute('aria-expanded', 'false'); if (odak) d.focus(); }
  }
  function cekmeceKapat() {
    var h = document.getElementById('tb');
    if (h && h.classList.contains('acik')) { var b = document.getElementById('tb-ac'); if (b) b.click(); else h.classList.remove('acik'); }
  }
  function ciz() {
    var o = oku('fr-oturum'), u = oku('fr-uye');
    var yeni = o ? 'u:' + (u && u.rumuz || '') + '|' + (u && u.av || '') + '|' + (u && u.fs || '') : 'x';
    if (kap && yeni === imza) { rozetler(); return; }
    var acikti = kap && kap.querySelector('.hs-menu') && !kap.querySelector('.hs-menu').hidden;
    if (kap) { kap.remove(); kap = null; }
    imza = yeni;
    if (!o) {   // giriş yok: Giriş yap düğmesi; Profil (kişisel tercih ekranı) girişsiz de açık kalır
      kap = document.createElement('button'); kap.type = 'button'; kap.className = 'hs-giris'; kap.textContent = 'Giriş yap';
      kap.onclick = function () { cekmeceKapat(); forumdan('giris'); };
      if (profil) profil.hidden = false;
    } else {
      var ad = (u && u.rumuz) || '', bas = ad ? ad.charAt(0).toLocaleUpperCase('tr-TR') : '';
      kap = document.createElement('div'); kap.className = 'hs';
      kap.innerHTML = '<button type="button" class="hs-av" id="hs-ac" aria-haspopup="true" aria-expanded="false" aria-controls="hs-menu" aria-label="Hesabım' + (ad ? ': ' + esc(ad) : '') + '">'
        + '<span class="hs-d' + (ad && window.kitAvatar ? ' hs-d-av' : '') + '" style="--h:' + ton(ad) + '" aria-hidden="true">' + (ad && window.kitAvatar ? window.kitAvatar.html({ rumuz: ad, av: u.av, fs: u.fs, fu: u.fu }, 32) : ad ? '<span class="fr-av" data-avu="' + esc(JSON.stringify({ u: { rumuz: ad, av: u.av, fs: u.fs, fu: u.fu }, b: 32 })) + '" style="--h:' + ton(ad) + '" aria-hidden="true">' + esc(bas) + '</span>' : esc(bas) || '<svg viewBox="0 0 24 24"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>') + '</span>'
        + '<span class="hs-ad">Hesabım</span><b class="tb-sayi" data-ozel-sayi hidden></b></button>'
        // Menü: başlıkta avatar + rumuz (kendi profil sayfası); Profilim (sayfa: kart, kayıtlı ilanlar, son yazılar), Profili düzenle (pencere), Mesajlar, ayarlar, çıkış.
        + '<div class="hs-menu" id="hs-menu" hidden>' + (ad ? '<a class="hs-kim" href="' + KOK + 'forum/?uye=' + encodeURIComponent(ad) + '" data-hs="sayfa"><span class="hs-kim-av" aria-hidden="true">' + (window.kitAvatar ? window.kitAvatar.html({ rumuz: ad, av: u.av, fs: u.fs, fu: u.fu }, 36) : '') + '</span><span class="hs-kim-ad">' + esc(ad) + '</span></a>' : '')
        + (ad ? '<a href="' + KOK + 'forum/?uye=' + encodeURIComponent(ad) + '" data-hs="sayfa">Profilim</a>' : '')
        + '<a href="' + KOK + '?profil=kart" data-hs="duzenle">Profili düzenle</a>'
        + '<a href="' + KOK + 'forum/?bolum=mesaj" data-hs="mesaj">Mesajlar<b class="tb-sayi" data-ozel-sayi hidden></b></a>'
        + '<button type="button" data-hs="ayar">Bildirim ayarları</button>'
        + '<button type="button" data-hs="hesap">Hesap ayarları</button>'
        + '<button type="button" class="hs-cikis" data-hs="cikis">Çıkış</button></div>';
      var d = kap.querySelector('.hs-av'), m = kap.querySelector('.hs-menu');
      d.onclick = function () {
        var ac = m.hidden; m.hidden = !ac; d.setAttribute('aria-expanded', String(ac));
        if (ac) benCek();
      };
      kap.onclick = function (e) {
        var x = e.target.closest ? e.target.closest('[data-hs]') : null;
        if (!x) return;
        var ne = x.getAttribute('data-hs');
        if (ne === 'ayar' || ne === 'hesap' || ne === 'cikis') { menuKapat(false); cekmeceKapat(); forumdan(ne); return; }
        var np = ne === 'duzenle' && document.getElementById('nav-profile');   // ana sayfada düzenleyici yerinde açılır
        if (np) { e.preventDefault(); menuKapat(false); cekmeceKapat(); if (window.kitProfilAc) window.kitProfilAc('kart'); else np.click(); return; }
        menuKapat(false); cekmeceKapat();   // bağlantılar normal gezinir
      };
      if (profil) profil.hidden = true;   // "Profil" artık hesap menüsünde (Profilim)
      if (acikti) { m.hidden = false; d.setAttribute('aria-expanded', 'true'); }
    }
    if (profil && profil.parentNode) profil.parentNode.insertBefore(kap, profil); else nav.appendChild(kap);
    rozetler();
    if (o) { if (window.kitAvatar) avatarKit(); else avatarKit().then(function () { imza = ''; ciz(); }); katipBaslat(); }
  }

  document.addEventListener('click', function (e) { if (kap && !kap.contains(e.target)) menuKapat(false); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && kap && kap.querySelector('.hs-menu') && !kap.querySelector('.hs-menu').hidden) menuKapat(true);
  });
  window.addEventListener('kit-hesap', ciz);
  window.addEventListener('storage', function (e) { if (!e.key || e.key === 'fr-oturum' || e.key === 'fr-uye' || e.key === 'fr-ozel-sayi') ciz(); });
  // Bu sayfada forum.js yoksa kayıtlı listede değişiklik olunca (sayfa içi kaydet düğmeleri) gönderme işi forum.js'e devredilir.
  if (!window.kitKayitliGonder) {
    var kg = window.kitKayitliGonder = function () {
      if (!oku('fr-oturum')) { if (oku('kit-saved-uye') != null) yaz('kit-saved-kirli', 1); return; }   // oturumu düşmüş hesap listesi: yeniden girişte ezilmesin (forum.js ile aynı)
      if (!oku('fr-uye') || oku('kit-saved-uye') !== oku('fr-uye').id) return;
      forumYukle().then(function () { if (window.kitKayitliGonder && window.kitKayitliGonder !== kg) window.kitKayitliGonder(); }, function () {});
    };
  }
  ciz();
  benCek();
})();
