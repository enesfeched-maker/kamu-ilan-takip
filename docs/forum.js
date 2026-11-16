/* KPSS Tercihi — forum (Kasım 2026, sohbet sürümü).
   Forum iki ayrı bölümdür: Soru-Cevap (kalıcı sorular, kart cevaplar) ve Sohbet odaları (anlık, mesaj balonları).
   - /forum/ #forum: üstte iki bölüm sekmesi; soru listesi/sayfası ya da odalar (geniş ekranda iki panel);
   - ilan sayfası #tartisma: başvuran sayısı + ilanla ilgili sorular (soru-cevap dili);
   - her sayfada: menüdeki "Forum" bağlantısına okunmamış bildirim sayısı, ana sayfa listesinde konuşulan ilan rozeti.
   Otomatik yanıt ve site hesabı her zaman etiketlidir; sayılar gerçek veridir, uydurma etkinlik gösterilmez.
   Yoklama ucuzdur: yalnız son mesajdan sonrası istenir (/baslik/:id/yeni). */
(function () {
  'use strict';
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var BOT = 'kamuilanibot';
  var KATEGORILER = [
    { kod: 'oda', ad: 'Odalar' }, { kod: 'ilan', ad: 'İlanlar' }, { kod: 'puan', ad: 'Puan ve tercih' }, { kod: 'kurum', ad: 'Kurum ve şehir' },
    { kod: 'mulakat', ad: 'Mülakat' }, { kod: 'haklar', ad: 'Haklar ve tayin' }, { kod: 'hazirlik', ad: 'Hazırlık' }, { kod: 'etkinlik', ad: 'Etkinlik' }
  ];
  var DUZEYLER = [{ kod: 'lisans', ad: 'Lisans' }, { kod: 'onlisans', ad: 'Önlisans' }, { kod: 'ortaogretim', ad: 'Ortaöğretim' }, { kod: 'ekpss', ad: 'EKPSS' }, { kod: 'agrubu', ad: 'A Grubu' }];
  var PUAN_TURLERI = ['P3', 'P93', 'P94', 'P10', 'P121'];
  var HIZLI_SORULAR = ['Son başvuru ne zaman?', 'Hangi bölümler başvurabilir?', 'Mülakat var mı?'];
  var SOHBET = 'M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20l1-4.3A7.5 7.5 0 1 1 20 12.5z';
  var ZARF = 'M4 6h16v12H4zM4 7l8 6 8-6';
  var ZIL = 'M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15zM10 20a2 2 0 0 0 4 0';
  var BASPARMAK = 'M7 11v9H4v-9zM7 11l4-7c1.5 0 2.5 1 2.2 2.6L12.6 10H18a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 16.8 20H7';
  var GENIS = matchMedia('(min-width: 900px)');
  document.documentElement.classList.add('fr-sohbet');

  /* ---------- yardımcılar ---------- */
  function oku(a) { try { return JSON.parse(localStorage.getItem(a)); } catch (e) { return null; } }
  function yaz(a, d) { try { if (d == null) localStorage.removeItem(a); else localStorage.setItem(a, JSON.stringify(d)); } catch (e) {} }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(html) { var t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }
  function iz(ad, x) { try { if (window.kitOlay) window.kitOlay(ad, x); } catch (e) {} }
  function ikon(d) { return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + d + '"/></svg>'; }
  function kimlik() {   // anonim cihaz kimliği: yalnız başvurdum/puan için
    var k = oku('fr-kimlik');
    if (!k) {
      var b = new Uint8Array(16); (window.crypto || window.msCrypto).getRandomValues(b);
      k = Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
      yaz('fr-kimlik', k);
    }
    return k;
  }
  function basvurularim() {
    var m = oku('fr-basvuru') || {};
    Object.keys(m).forEach(function (k) { if (m[k] === true) m[k] = {}; });
    return m;
  }
  function oturum() { return oku('fr-oturum'); }
  function uye() { return oku('fr-uye'); }
  function cikis() {
    var u = uye();
    // hesabın profili bu cihazda kalmasın (ortak cihaz); marker yoksa profil giriş öncesinden kalmadır, ona dokunulmaz
    try { if (u && u.id && oku('kit-profil-uye') === u.id) { yaz('kit-profil', null); yaz('fr-duzey', null); yaz('kit-profil-uye', null); window.dispatchEvent(new Event('kit-profil-sunucudan')); } } catch (e) {}
    // kayıtlı ilanlar da böyle: hesaptan gelen liste cihazda kalmaz; hesapla eşleşmemiş (giriş öncesi) liste korunur. Bekleyen değişiklik önce gönderilir.
    try {
      if (u && u.id && oku('kit-saved-uye') === u.id) {
        if (oku('kit-saved-kirli')) kayitliGonder_();
        yaz('kit-saved', null); yaz('kit-saved-uye', null); yaz('kit-saved-kirli', null); window.dispatchEvent(new Event('kit-kayitli-sunucudan'));
      }
    } catch (e) {}
    yaz('fr-oturum', null); yaz('fr-uye', null); yaz('fr-bildirim-sayi', null); yaz('fr-ben-t', null); ozelSayisiGoster(0); hesapOlayi(); yenile();
  }
  function hesapOlayi() { try { window.dispatchEvent(new Event('kit-hesap')); } catch (e) {} }   // üst çubuktaki hesap girişi (hesap.js) kendini yeniler
  // Öğrenim düzeyi: önce forumda seçilen, yoksa sitenin profilinde tek düzey işaretlenmişse o.
  function duzeyim() {
    var d = oku('fr-duzey');
    if (d) return d === 'yok' ? '' : d;
    var p = oku('kit-profil');
    return p && p.ogrenim && p.ogrenim.length === 1 ? p.ogrenim[0] : '';
  }
  // Okunmamış: açılan her başlığın en son görülen yanıt sayısı (yalnız bu tarayıcıda).
  function gorulen() { return oku('fr-gorulen') || {}; }
  function gorulduIsaretle(id, sayi_) { var g = gorulen(); g[id] = sayi_; var k = Object.keys(g); if (k.length > 400) delete g[k[0]]; yaz('fr-gorulen', g); }

  function api(yol, secenek) {
    secenek = secenek || {};
    var h = {}, o = oturum();
    if (o) h.Authorization = 'Bearer ' + o;
    if (secenek.govde !== undefined) h['Content-Type'] = 'application/json';
    return fetch(API + yol, { method: secenek.yontem || 'GET', headers: h, body: secenek.govde !== undefined ? JSON.stringify(secenek.govde) : undefined })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (r.status === 401 && o) { yaz('fr-oturum', null); yaz('fr-uye', null); hesapOlayi(); }
          if (!r.ok) { var e = new Error(j.hata || 'Bir sorun oluştu, biraz sonra yeniden dene.'); e.durum = r.status; throw e; }
          return j;
        });
      }, function () { throw new Error('Foruma şu an ulaşılamıyor.'); });
  }
  function zaman(sn) {
    var f = Math.max(0, Date.now() / 1000 - sn);
    if (f < 60) return 'az önce';
    if (f < 3600) return Math.floor(f / 60) + ' dk';
    if (f < 86400) return Math.floor(f / 3600) + ' sa';
    if (f < 86400 * 7) return Math.floor(f / 86400) + ' gün';
    return new Date(sn * 1000).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
  }
  function saat(sn) { return new Date(sn * 1000).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }); }
  function gunAdi(sn) {
    var d = new Date(sn * 1000), b = new Date(); b.setHours(0, 0, 0, 0);
    var fark = Math.round((b - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
    if (fark === 0) return 'Bugün';
    if (fark === 1) return 'Dün';
    return d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: d.getFullYear() === b.getFullYear() ? undefined : 'numeric' });
  }
  function sayi(n) { return Number(n || 0).toLocaleString('tr-TR'); }
  function bildir(m) {
    var t = el('<div class="fr-toast" role="status">' + esc(m) + '</div>');
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('fr-git'); setTimeout(function () { t.remove(); }, 400); }, 2400);
  }
  var IZINLI_BAG = /^https:\/\/([a-z0-9-]+\.)*(gov\.tr|edu\.tr|kpsstercihi\.com)(\/[^\s<]*)?$|^https:\/\/t\.me\/kpsstercihi\b/i;
  function metin(govde) {
    return String(govde || '').split(/\n{2,}/).map(function (p) {
      var h = esc(p).replace(/https:\/\/[^\s<]+/g, function (u) {
        var ham = u.replace(/&amp;/g, '&').replace(/[.,;:!?)]+$/, '');
        var kalan = u.slice(esc(ham).length);
        return IZINLI_BAG.test(ham) ? '<a href="' + esc(ham) + '" target="_blank" rel="noopener nofollow ugc">' + esc(ham.replace(/^https:\/\//, '')) + '</a>' + kalan : u;
      });
      h = h.replace(/(^|[\s(])@([A-Za-z0-9_.çğıöşüÇĞİÖŞÜ]{3,20})/g, '$1<button type="button" class="fr-anma" data-uye="$2">@$2</button>');
      return '<p>' + h.replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }
  function kisalt(s, n) { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function insanMi(k) { return k.rol !== 'asistan' && k.rol !== 'sistem'; }
  function etiket(k) {
    if (k.rol === 'asistan') return '<span class="fr-et fr-et-bot" title="Otomatik; yalnız ilan belgesindeki bilgiyi aktarır.">otomatik</span>';
    if (k.rol === 'sistem') return '<span class="fr-et">site</span>';
    if (k.rol === 'yonetici') return '<span class="fr-et">yönetici</span>';
    return '';
  }
  function ton(ad) { var h = 0; ad = ad || '?'; for (var i = 0; i < ad.length; i++) h = (h * 31 + ad.charCodeAt(i)) % 360; return h; }
  function avatar(k) {
    if (k.rol === 'asistan') return '<span class="fr-av fr-av-bot" aria-hidden="true">' + ikon('M7 9h10v9H7zM12 5v4M10 13h.01M14 13h.01') + '</span>';
    if (k.rol === 'sistem') return '<span class="fr-av fr-av-site" aria-hidden="true"><img src="' + kok() + 'assets/logo-96.webp?v=2" alt="" width="32" height="32"></span>';
    return '<span class="fr-av" style="--h:' + ton(k.rumuz) + '" aria-hidden="true">' + esc((k.rumuz || '?').charAt(0).toLocaleUpperCase('tr-TR')) + '</span>';
  }
  function kok() { return document.body.classList.contains('detail-page') ? '../../' : document.getElementById('forum') ? '../' : ''; }
  function katAd(kod) { for (var i = 0; i < KATEGORILER.length; i++) if (KATEGORILER[i].kod === kod) return KATEGORILER[i].ad; return ''; }
  function duzeyAd(k) { for (var i = 0; i < DUZEYLER.length; i++) if (DUZEYLER[i].kod === k) return DUZEYLER[i].ad; return ''; }
  function parcalar(l) { return l.filter(function (x) { return x !== '' && x != null; }).map(function (x) { return '<span>' + esc(x) + '</span>'; }).join(''); }

  /* ---------- hesaba bağlı profil ---------- */
  // Sitedeki profil (kit-profil) giriş yapılmışsa hesapla birlikte gezer: sunucuda varsa sunucu kazanır, yoksa yereldeki yüklenir.
  function kanonik(v) {
    if (Array.isArray(v)) return v.map(kanonik);
    if (v && typeof v === 'object') { var o = {}; Object.keys(v).sort().forEach(function (k) { o[k] = kanonik(v[k]); }); return o; }
    return v;
  }
  function ayniProfil(a, b) { return JSON.stringify(kanonik(a)) === JSON.stringify(kanonik(b)); }
  // "kit-profil-uye": yereldeki profilin hangi üyeye ait olduğu. Ortak cihazda bir üyenin profili ötekine sızmasın:
  // çıkışta yalnız o üyeye ait profil silinir, girişte yalnız sahibi belli olmayan ya da aynı üyeye ait yerel profil yüklenir.
  function profilSahibi() { var m = oku('kit-profil-uye'); return typeof m === 'number' ? m : null; }
  function profilIsaretle() { var u = uye(); if (u && u.id) yaz('kit-profil-uye', u.id); }
  function profilSenkron(sunucu) {
    try {
      var yerel = oku('kit-profil'), ben = uye();
      if (sunucu && sunucu.v === 1) {
        profilIsaretle();
        if (ayniProfil(sunucu, yerel)) return;
        yaz('kit-profil', sunucu);
        if (sunucu.ogrenim) yaz('fr-duzey', sunucu.ogrenim);
        window.dispatchEvent(new Event('kit-profil-sunucudan'));
      } else if (yerel && yerel.v === 1 && oturum() && ben && (profilSahibi() === null || profilSahibi() === ben.id)) {
        profilIsaretle();
        api('/ben/profil', { yontem: 'POST', govde: { profil: yerel } }).then(function () {}, function () {});
      }
    } catch (e) {}
  }
  function profilCek() {   // /ben'i okur, üye bilgisini, profili ve kayıtlı ilanları günceller
    if (!oturum()) return Promise.resolve();
    return api('/ben').then(function (j) { yaz('fr-uye', j.uye); yaz('fr-ben-t', Date.now()); profilSenkron(j.profil); kayitliSenkron(j.kayitli); hesapOlayi(); }, function () {});
  }

  /* ---------- hesaba bağlı kayıtlı ilanlar ---------- */
  // Yerel liste "kit-saved". "kit-saved-uye": listenin hangi hesapla eşlendiği; "kit-saved-kirli": gönderilmemiş yerel değişiklik var.
  // Girişte (eşleşme yokken) sunucu ve yerel liste birleşir (önce sunucu sırası) ve değiştiyse bir kez yüklenir; eşleştikten sonra
  // hesap esastır (başka cihazdaki silmeler de gelir), yerel değişiklikler 1,5 sn gecikmeyle gönderilir.
  // Hesapta ilan ANAHTARI tutulur (UUID, sbb-…, iskur-…, csb-…); yerel listedeki "id"lerle dönüşüm hesap.js'te (kitKayitli).
  function ayniDizi(a, b) { return a.length === b.length && a.every(function (x, i) { return x === b[i]; }); }
  function yerelKayitli() { var l = oku('kit-saved'); return Array.isArray(l) ? l : []; }
  function kayitliOlayi() { try { window.dispatchEvent(new Event('kit-kayitli-sunucudan')); } catch (e) {} }
  function kayitliSenkron(sunucu) {
    try {
      var ben = uye(), K = window.kitKayitli;
      if (!oturum() || !ben || !ben.id || !Array.isArray(sunucu) || !K) return;
      var sahip = oku('kit-saved-uye'), yerel = yerelKayitli();
      if (sahip === ben.id) {
        if (oku('kit-saved-kirli')) { kayitliGonder_(); return; }
        var e = K.esitle(sunucu, yerel);
        if (!e.ayni) { yaz('kit-saved', e.yerel); kayitliOlayi(); }
        return;
      }
      var r = K.birlestir(sunucu, typeof sahip === 'number' ? [] : yerel);   // başka üyeye ait liste sızmasın
      yaz('kit-saved-uye', ben.id);
      if (!ayniDizi(r.yerel, yerel)) { yaz('kit-saved', r.yerel); kayitliOlayi(); }
      if (r.degisti) kayitliGonder_();
    } catch (e) {}
  }
  function kayitliGonder_() {
    var K = window.kitKayitli;
    if (!oturum() || !K) return;
    api('/ben/kayitli', { yontem: 'POST', govde: { kayitli: K.gonderilecek(yerelKayitli()) } }).then(function () { yaz('kit-saved-kirli', null); }, function (h) { if (h && h.durum === 400) yaz('kit-saved-kirli', null); });
  }
  var kayitliZamanlayici = 0;
  window.kitKayitliGonder = function () {   // site kayıtlı listesi değişince çağırır; giriş ya da eşleşme yoksa hiçbir şey yapmaz
    try {
      var ben = uye();
      if (!oturum() || !ben || oku('kit-saved-uye') !== ben.id) return;
      yaz('kit-saved-kirli', 1);
      clearTimeout(kayitliZamanlayici);
      kayitliZamanlayici = setTimeout(kayitliGonder_, 1500);
    } catch (e) {}
  };
  var profilZamanlayici = 0;
  window.kitProfilGonder = function () {   // site profil ekranı çağırır; giriş yoksa hiçbir şey yapmaz
    clearTimeout(profilZamanlayici);
    profilZamanlayici = setTimeout(function () {
      try {
        if (!oturum()) return;
        var p = oku('kit-profil');
        profilIsaretle();   // kullanıcı profili bu hesapta kendisi değiştirdi
        api('/ben/profil', { yontem: 'POST', govde: { profil: p && p.v === 1 ? p : null } }).then(function () {}, function () {});
      } catch (e) {}
    }, 1200);
  };

  /* ---------- giriş ve üyelik ---------- */
  var girisSonrasi = null;
  var girisAyari = null;
  function girisAyariGetir() {
    if (girisAyari) return Promise.resolve(girisAyari);
    return api('/giris/ayar').then(function (j) { girisAyari = j || {}; return girisAyari; }, function () { return {}; });
  }
  var betikler = {};
  function betikYukle(url) {   // üçüncü taraf betikler yalnız gerektiğinde, bir kez yüklenir
    if (!betikler[url]) {
      betikler[url] = new Promise(function (ok, red) {
        var s = document.createElement('script');
        s.async = true; s.src = url; s.onload = ok;
        s.onerror = function () { delete betikler[url]; red(new Error('betik')); };
        document.head.appendChild(s);
      });
    }
    return betikler[url];
  }
  function girisAlani(ad, etiket, ozellik, ipucu, sifreMi) {
    var girdi_ = '<input id="fr-g-' + ad + '" ' + ozellik + (ipucu ? ' aria-describedby="fr-g-' + ad + '-ip"' : '') + '>';
    return '<div class="fr-g-alan"><label for="fr-g-' + ad + '">' + esc(etiket) + '</label>'
      + (sifreMi ? '<div class="fr-g-sifre">' + girdi_ + '<button type="button" class="fr-g-goz" aria-pressed="false" aria-controls="fr-g-' + ad + '">Göster</button></div>' : girdi_)
      + (ipucu ? '<small id="fr-g-' + ad + '-ip">' + esc(ipucu) + '</small>' : '') + '</div>';
  }
  var RUMUZ_OZ = 'type="text" name="username" maxlength="20" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" required';
  function sifreOz(yeni) { return 'type="password" name="' + (yeni ? 'new-password' : 'password') + '" maxlength="72" autocomplete="' + (yeni ? 'new-password' : 'current-password') + '" required'; }

  // Giriş ve hesap pencerelerinin ortak kabuğu: odak tuzağı, Escape, kilit (kurtarma kodu görünürken kapanmaz).
  function kabukAc() {
    var eski = document.getElementById('fr-giris');
    if (eski) eski.remove();
    var kutu = el('<div class="fr-perde fr-giris-perde" id="fr-giris" role="dialog" aria-modal="true" aria-labelledby="fr-giris-bas"><div class="fr-kutu fr-giris-kutu" tabindex="-1">'
      + '<button type="button" class="fr-kapat" aria-label="Kapat">×</button>'
      + '<h2 id="fr-giris-bas"></h2><p class="fr-not fr-giris-not" hidden></p><div class="fr-giris-govde"></div></div></div>');
    document.body.appendChild(kutu);
    var ic = kutu.querySelector('.fr-kutu'), govde = kutu.querySelector('.fr-giris-govde'), bas = kutu.querySelector('h2'), not_ = kutu.querySelector('.fr-giris-not');
    var onceki = document.activeElement;
    var k = { kutu: kutu, govde: govde, kilitli: false };
    k.kapat = function () {
      document.removeEventListener('keydown', tus);
      kutu.remove();
      try { if (onceki && onceki.focus && document.body.contains(onceki)) onceki.focus(); } catch (e) {}
    };
    function tus(e) {
      if (!document.body.contains(kutu)) { document.removeEventListener('keydown', tus); return; }
      if (e.key === 'Escape' && !k.kilitli) { k.kapat(); return; }
      if (e.key !== 'Tab') return;
      var l = Array.prototype.filter.call(ic.querySelectorAll('button,input,a[href],select,textarea,[tabindex="0"]'), function (x) { return !x.disabled && !x.hidden && x.getAttribute('tabindex') !== '-1' && x.offsetParent !== null; });
      if (!l.length) return;
      var ilk = l[0], son = l[l.length - 1];
      if (e.shiftKey && (document.activeElement === ilk || document.activeElement === ic)) { e.preventDefault(); son.focus(); }
      else if (!e.shiftKey && document.activeElement === son) { e.preventDefault(); ilk.focus(); }
    }
    document.addEventListener('keydown', tus);
    kutu.querySelector('.fr-kapat').onclick = function () { if (!k.kilitli) k.kapat(); };
    kutu.onclick = function (e) { if (e.target === kutu && !k.kilitli) k.kapat(); };
    govde.addEventListener('click', function (e) {   // şifre göster / gizle (tüm görünümlerde)
      var g = e.target.closest('.fr-g-goz');
      if (!g) return;
      var i = document.getElementById(g.getAttribute('aria-controls'));
      if (!i) return;
      var ac = i.type === 'password';
      i.type = ac ? 'text' : 'password';
      g.textContent = ac ? 'Gizle' : 'Göster'; g.setAttribute('aria-pressed', ac ? 'true' : 'false');
    });
    k.ciz = function (b, n, html) {
      bas.textContent = b; not_.textContent = n || ''; not_.hidden = !n; govde.innerHTML = html;
      var ilkAlan = govde.querySelector('input:not([type=hidden]):not([readonly]):not([type=checkbox])');
      if (ilkAlan && matchMedia('(pointer:fine)').matches) ilkAlan.focus(); else ic.focus({ preventScroll: true });
    };
    k.hata = function (m) { var p = govde.querySelector('.fr-hata'); if (p) { p.textContent = m || ''; p.hidden = !m; } };
    k.mesgul = function (d, acik, yazi) { if (!d) return; d.disabled = !!acik; if (acik) { d._yazi = d.textContent; d.textContent = yazi || 'Bekle…'; } else if (d._yazi) d.textContent = d._yazi; };
    // Kurtarma kodu: bir kez gösterilir; "Kaydettim" işaretlenmeden devam edilemez ve pencere kapanmaz.
    k.kodGoster = function (kod, baslik, sonra) {
      k.kilitli = true;
      kutu.querySelector('.fr-kapat').hidden = true;
      k.ciz(baslik, '', '<div class="fr-kod-kart"><p class="fr-kod-uyari"><b>Bu kodu sakla. Şifreni unutursan hesabına bu kodla dönersin.</b> Ekran görüntüsü al ya da bir yere yaz. Bir daha gösterilmez.</p>'
        + '<p class="fr-kod" id="fr-kod" aria-label="Kurtarma kodun">' + esc(kod) + '</p>'
        + '<button type="button" class="fr-g-ikincil" data-kopyala>Kopyala</button></div>'
        + '<label class="fr-g-onay"><input type="checkbox" id="fr-g-kaydettim"><span>Kaydettim</span></label>'
        + '<button type="button" class="fr-g-btn" data-devam disabled>Devam et</button>');
      var kop = govde.querySelector('[data-kopyala]'), onay = govde.querySelector('#fr-g-kaydettim'), dev = govde.querySelector('[data-devam]');
      kop.onclick = function () {
        function tamam() { kop.textContent = 'Kopyalandı'; setTimeout(function () { kop.textContent = 'Kopyala'; }, 2000); }
        function yedek() {
          try {
            var r = document.createRange(); r.selectNodeContents(govde.querySelector('#fr-kod'));
            var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
            if (document.execCommand('copy')) tamam(); else bildir('Kodu seçip elle kopyalayabilirsin.');
          } catch (e) { bildir('Kodu seçip elle kopyalayabilirsin.'); }
        }
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(kod).then(tamam, yedek); else yedek();
      };
      onay.onchange = function () { dev.disabled = !onay.checked; };
      dev.onclick = function () { k.kilitli = false; if (sonra) sonra(); else k.kapat(); };
      kop.focus();
    };
    return k;
  }

  function girisKutusu(baslik, ilkSekme) {
    var k = kabukAc(), govde = k.govde, ayar = {};
    var jeton = '', tsKimlik = null;
    function oturumAc(j) {
      yaz('fr-oturum', j.oturum); yaz('fr-uye', j.uye); yaz('fr-giris-yontem', 1); iz('forum_giris'); hesapOlayi();
      return profilCek();
    }
    function bitir(bekle) {
      var tamam = false;
      function son() { if (tamam) return; tamam = true; k.kapat(); var f = girisSonrasi; girisSonrasi = null; if (f) f(); else yenile(); }
      Promise.race([bekle || Promise.resolve(), new Promise(function (ok) { setTimeout(ok, 1500); })]).then(son, son);
    }
    function girdi(j, kodBasligi) {
      if (j.yeni) return rumuzSor(j.gecici);
      var bekle = oturumAc(j);
      if (j.kurtarma_kodu) return k.kodGoster(j.kurtarma_kodu, kodBasligi || 'Kurtarma kodun hazır', function () { bitir(bekle); });
      bitir(bekle);
    }
    function turnstileKur() {
      var yer = govde.querySelector('.fr-g-turnstile');
      if (!ayar.turnstile_site || !yer) return;
      betikYukle('https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit').then(function () {
        if (!document.body.contains(yer) || !window.turnstile) return;
        tsKimlik = window.turnstile.render(yer, {
          sitekey: ayar.turnstile_site, language: 'tr', theme: 'auto',
          callback: function (t) { jeton = t; }, 'expired-callback': function () { jeton = ''; }, 'error-callback': function () { jeton = ''; }
        });
      }, function () { k.hata('Robot kontrolü yüklenemedi. Bağlantını kontrol edip sayfayı yenile.'); });
    }
    function turnstileSifirla() { jeton = ''; try { if (window.turnstile && tsKimlik !== null) window.turnstile.reset(tsKimlik); } catch (e) {} }
    function turnstileKaldir() { try { if (window.turnstile && tsKimlik !== null) window.turnstile.remove(tsKimlik); } catch (e) {} tsKimlik = null; jeton = ''; }

    function rumuzSor(gecici) {
      k.ciz('Bir rumuz seç', '3–20 karakter. Sonradan değişmez, sitede yalnız bu görünür.',
        '<form class="fr-g-form" novalidate>' + girisAlani('rumuz', 'Rumuz', RUMUZ_OZ.replace('autocomplete="username"', 'autocomplete="nickname"').replace('name="username"', 'name="rumuz"'), 'ör. memuradayi35')
        + '<p class="fr-hata" role="alert" hidden></p><button class="fr-g-btn" type="submit">Devam et</button></form>');
      var f = govde.querySelector('form'), g = f.querySelector('input'), d = f.querySelector('button[type=submit]');
      f.onsubmit = function (e) {
        e.preventDefault(); k.hata('');
        k.mesgul(d, true);
        api('/giris/rumuz', { yontem: 'POST', govde: { gecici: gecici, rumuz: g.value.trim() } }).then(function (j) { girdi(j); }, function (h) { k.hata(h.message); }).then(function () { k.mesgul(d, false); });
      };
    }

    function unuttum() {
      k.ciz('Şifreni sıfırla', 'Üye olurken sana gösterilen kurtarma kodu lazım.',
        '<form class="fr-g-form" novalidate>' + girisAlani('rumuz', 'Rumuz', RUMUZ_OZ)
        + girisAlani('kod', 'Kurtarma kodu', 'type="text" name="kod" maxlength="20" autocomplete="off" autocapitalize="characters" autocorrect="off" spellcheck="false" placeholder="XXXX-XXXX-XXXX" required')
        + girisAlani('yeni', 'Yeni şifre', sifreOz(true), 'En az 8 karakter.', true)
        + '<p class="fr-hata" role="alert" hidden></p><button class="fr-g-btn" type="submit">Şifreyi yenile</button>'
        + '<button type="button" class="fr-g-bag" data-geri>Girişe dön</button></form>');
      var f = govde.querySelector('form'), d = f.querySelector('button[type=submit]');
      f.querySelector('[data-geri]').onclick = function () { ana('giris'); };
      f.onsubmit = function (e) {
        e.preventDefault(); k.hata('');
        var rumuz = f.querySelector('#fr-g-rumuz').value.trim(), kod = f.querySelector('#fr-g-kod').value.trim(), yeni = f.querySelector('#fr-g-yeni').value;
        if (!rumuz || !kod) return k.hata('Rumuzunu ve kurtarma kodunu yaz.');
        if (yeni.length < 8) return k.hata('Yeni şifre en az 8 karakter olmalı.');
        k.mesgul(d, true);
        api('/sifre-sifirla', { yontem: 'POST', govde: { rumuz: rumuz, kod: kod, yeni_sifre: yeni } }).then(function (j) { girdi(j, 'Şifren yenilendi'); }, function (h) { k.hata(h.message); }).then(function () { k.mesgul(d, false); });
      };
    }

    function uyePaneli(panel) {
      panel.innerHTML = '<form class="fr-g-form" novalidate>' + girisAlani('rumuz', 'Rumuz', RUMUZ_OZ, '3–20 karakter. Sonradan değişmez, sitede yalnız bu görünür.')
        + girisAlani('sifre', 'Şifre', sifreOz(true), 'En az 8 karakter.', true)
        + (ayar.turnstile_site ? '<div class="fr-g-turnstile" role="group" aria-label="Robot kontrolü"></div>' : '')
        + '<p class="fr-hata" role="alert" hidden></p><button class="fr-g-btn" type="submit">Üye ol</button></form>';
      var f = panel.querySelector('form'), d = f.querySelector('button[type=submit]');
      f.onsubmit = function (e) {
        e.preventDefault(); k.hata('');
        var rumuz = f.querySelector('#fr-g-rumuz').value.trim(), sifre = f.querySelector('#fr-g-sifre').value;
        if (rumuz.length < 3) return k.hata('Rumuz en az 3 karakter olmalı.');
        if (sifre.length < 8) return k.hata('Şifre en az 8 karakter olmalı.');
        if (ayar.turnstile_site && !jeton) return k.hata('Önce robot kontrolünü tamamla.');
        k.mesgul(d, true, 'Üye olunuyor…');
        api('/kayit', { yontem: 'POST', govde: { rumuz: rumuz, sifre: sifre, turnstile: jeton || undefined } })
          .then(function (j) { girdi(j, 'Üyeliğin hazır'); }, function (h) { k.hata(h.message); turnstileSifirla(); })
          .then(function () { k.mesgul(d, false); });
      };
      turnstileKur();
    }
    function girisPaneli(panel) {
      panel.innerHTML = '<form class="fr-g-form" novalidate>' + girisAlani('rumuz', 'Rumuz', RUMUZ_OZ) + girisAlani('sifre', 'Şifre', sifreOz(false), '', true)
        + '<p class="fr-hata" role="alert" hidden></p><button class="fr-g-btn" type="submit">Giriş yap</button>'
        + '<button type="button" class="fr-g-bag" data-unuttum>Şifremi unuttum</button></form>';
      var f = panel.querySelector('form'), d = f.querySelector('button[type=submit]');
      f.querySelector('[data-unuttum]').onclick = unuttum;
      f.onsubmit = function (e) {
        e.preventDefault(); k.hata('');
        var rumuz = f.querySelector('#fr-g-rumuz').value.trim(), sifre = f.querySelector('#fr-g-sifre').value;
        if (!rumuz || !sifre) return k.hata('Rumuzunu ve şifreni yaz.');
        k.mesgul(d, true, 'Giriliyor…');
        api('/giris/sifre', { yontem: 'POST', govde: { rumuz: rumuz, sifre: sifre } }).then(function (j) { girdi(j); }, function (h) { k.hata(h.message); }).then(function () { k.mesgul(d, false); });
      };
    }

    function googleKur() {
      var yer = govde.querySelector('#fr-g-google');
      if (!ayar.google_istemci || !yer) return;
      betikYukle('https://accounts.google.com/gsi/client').then(function () {
        if (!document.body.contains(yer) || !window.google || !window.google.accounts) { yer.hidden = true; return; }
        window.google.accounts.id.initialize({
          client_id: ayar.google_istemci, ux_mode: 'popup', auto_select: false, itp_support: true,
          callback: function (r) { k.hata(''); api('/giris/google', { yontem: 'POST', govde: { kimlik_jetonu: r.credential } }).then(function (j) { girdi(j); }, function (h) { k.hata(h.message); }); }
        });
        var koyu = document.documentElement.getAttribute('data-theme') === 'dark';
        window.google.accounts.id.renderButton(yer, { type: 'standard', theme: koyu ? 'filled_black' : 'outline', size: 'large', text: 'continue_with', shape: 'rectangular', logo_alignment: 'center', locale: 'tr', width: Math.max(200, Math.min(400, yer.clientWidth || 300)) });
      }, function () { yer.hidden = true; });
    }
    function telegramAc() {
      var yer = govde.querySelector('.fr-g-tg-yer'), dugme = govde.querySelector('[data-telegram]');
      dugme.hidden = true; yer.hidden = false;
      if (YEREL) {   // yerelde Telegram çalışmaz: deneme girişi
        yer.innerHTML = '<form class="fr-g-form"><p class="fr-not">Yalnız yerel geliştirmede: deneme rumuzu.</p>' + girisAlani('deneme', 'Deneme rumuzu', RUMUZ_OZ.replace('name="username"', 'name="deneme"').replace('autocomplete="username"', 'autocomplete="off"'))
          + '<button class="fr-g-ikincil" type="submit">Deneme girişi</button></form>';
        var f = yer.querySelector('form');
        f.onsubmit = function (e) { e.preventDefault(); k.hata(''); api('/giris/deneme', { yontem: 'POST', govde: { rumuz: f.querySelector('input').value.trim() } }).then(function (j) { girdi(j); }, function (h) { k.hata(h.message); }); };
        return;
      }
      window.frTelegram = function (u) { k.hata(''); api('/giris/telegram', { yontem: 'POST', govde: u }).then(function (j) { girdi(j); }, function (h) { k.hata(h.message); }); };
      var s = document.createElement('script');
      s.async = true; s.src = 'https://telegram.org/js/telegram-widget.js?22';
      s.setAttribute('data-telegram-login', BOT); s.setAttribute('data-size', 'large'); s.setAttribute('data-radius', '12');
      s.setAttribute('data-onauth', 'frTelegram(user)'); s.setAttribute('data-request-access', 'write');
      yer.appendChild(s);
    }

    function ana(sekme) {
      turnstileKaldir();
      var uyeMi = sekme !== 'giris';
      if (ayar.sifre === false) {   // sunucuda şifreli üyelik kapalı (SIFRE_BIBERI yok): yalnız Google / Telegram
        k.ciz(baslik || 'Foruma katıl', 'Şifreyle üyelik şu an kapalı. Aşağıdaki yöntemlerden biriyle devam edebilirsin.',
          '<div class="fr-g-sosyal">' + (ayar.google_istemci ? '<div class="fr-g-google" id="fr-g-google"></div>' : '')
          + '<button type="button" class="fr-g-ikincil" data-telegram>Telegram ile devam et</button><div class="fr-g-tg-yer" hidden></div></div><p class="fr-hata" role="alert" hidden></p>');
        govde.querySelector('[data-telegram]').onclick = telegramAc;
        googleKur();
        return;
      }
      k.ciz(baslik || 'Foruma katıl', '', '<div class="fr-g-sekmeler" role="tablist" aria-label="Üyelik">'
        + '<button type="button" role="tab" id="fr-g-t-uye" data-sekme="uye" aria-controls="fr-g-panel">Üye ol</button>'
        + '<button type="button" role="tab" id="fr-g-t-giris" data-sekme="giris" aria-controls="fr-g-panel">Giriş yap</button></div>'
        + '<div id="fr-g-panel" role="tabpanel"></div>'
        + '<div class="fr-g-ayrac"><span>ya da</span></div>'
        + '<div class="fr-g-sosyal">' + (ayar.google_istemci ? '<div class="fr-g-google" id="fr-g-google"></div>' : '')
        + '<button type="button" class="fr-g-ikincil" data-telegram>Telegram ile devam et</button><div class="fr-g-tg-yer" hidden></div></div>');
      var panel = govde.querySelector('#fr-g-panel');
      var sekmeler = govde.querySelectorAll('[role=tab]');
      function sec(s, odakla) {
        turnstileKaldir();
        Array.prototype.forEach.call(sekmeler, function (b) { var acik = b.getAttribute('data-sekme') === s; b.setAttribute('aria-selected', acik ? 'true' : 'false'); b.tabIndex = acik ? 0 : -1; });
        panel.setAttribute('aria-labelledby', 'fr-g-t-' + s);
        if (s === 'giris') girisPaneli(panel); else uyePaneli(panel);
        if (odakla) { var i = panel.querySelector('input'); if (i) i.focus(); }
      }
      Array.prototype.forEach.call(sekmeler, function (b) {
        b.onclick = function () { sec(b.getAttribute('data-sekme'), true); };
        b.onkeydown = function (e) {
          if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
          e.preventDefault();
          var h = b.getAttribute('data-sekme') === 'uye' ? 'giris' : 'uye';
          sec(h, false); govde.querySelector('#fr-g-t-' + h).focus();
        };
      });
      govde.querySelector('[data-telegram]').onclick = telegramAc;
      sec(uyeMi ? 'uye' : 'giris', false);
      if (matchMedia('(pointer:fine)').matches) { var i0 = panel.querySelector('input'); if (i0) i0.focus(); }
      googleKur();
    }
    // Google düğmesi ve robot kontrolü sunucu ayarına bağlı: ayar gelmeden form çizilmez (ilk açılıştan sonra önbellekten anında gelir).
    k.ciz(baslik || 'Foruma katıl', '', '<p class="fr-yukleniyor">Yükleniyor…</p>');
    girisAyariGetir().then(function (a) {
      ayar = a || {};
      if (document.body.contains(k.kutu)) ana(ilkSekme || (oku('fr-giris-yontem') ? 'giris' : 'uye'));
    });
  }
  function girisGerekli(baslik, sonra) { if (oturum()) return false; girisSonrasi = sonra || null; girisKutusu(baslik); return true; }

  // Hesap menüsü: şifre belirle / değiştir, kurtarma kodunu yenile.
  function hesapKutusu() {
    if (!oturum()) { girisKutusu(); return; }
    var k = kabukAc();
    k.ciz('Şifre ve kurtarma kodu', '', '<p class="fr-yukleniyor">Yükleniyor…</p>');
    api('/ben').then(function (j) { yaz('fr-uye', j.uye); hesapCiz(k, j.uye); }, function (h) { k.ciz('Şifre ve kurtarma kodu', '', '<p class="fr-hata" role="alert">' + esc(h.message) + '</p>'); });
  }
  function hesapCiz(k, u) {
    var govde = k.govde;
    var gizli = '<input class="fr-g-gizli" type="text" name="username" autocomplete="username" value="' + esc(u.rumuz) + '" readonly tabindex="-1" aria-hidden="true">';
    function gonder(f, yol, govdeYap, ok) {
      var d = f.querySelector('button[type=submit]'), p = f.querySelector('.fr-hata');
      function hata(m) { p.textContent = m || ''; p.hidden = !m; }
      f.onsubmit = function (e) {
        e.preventDefault(); hata('');
        var g = govdeYap(f);
        if (typeof g === 'string') return hata(g);
        k.mesgul(d, true);
        api(yol, { yontem: 'POST', govde: g }).then(ok, function (h) { hata(h.message); }).then(function () { k.mesgul(d, false); });
      };
    }
    if (!u.sifre_var) {
      k.ciz('Şifre belirle', 'Şu an yalnız ' + (u.google_var ? 'Google' : 'Telegram') + ' ile giriyorsun. Şifre belirlersen rumuzunla da girebilirsin.',
        '<form class="fr-g-form" novalidate>' + gizli + girisAlani('yeni', 'Yeni şifre', sifreOz(true), 'En az 8 karakter.', true)
        + '<p class="fr-hata" role="alert" hidden></p><button class="fr-g-btn" type="submit">Şifre belirle</button></form>');
      gonder(govde.querySelector('form'), '/ben/sifre', function (f) {
        var y = f.querySelector('#fr-g-yeni').value;
        return y.length < 8 ? 'Şifre en az 8 karakter olmalı.' : { yeni: y };
      }, function (j) {
        var gnc = oku('fr-uye') || u; gnc.sifre_var = true; yaz('fr-uye', gnc); if (j.oturum) yaz('fr-oturum', j.oturum);   // sunucu eski oturumları kapatır, taze jeton gelir
        if (j.kurtarma_kodu) k.kodGoster(j.kurtarma_kodu, 'Şifren hazır', function () { k.kapat(); }); else { k.kapat(); bildir('Şifren kaydedildi'); }
      });
      return;
    }
    k.ciz('Şifre ve kurtarma kodu', '',
      '<form class="fr-g-form fr-g-bolum" data-form="sifre" novalidate><h3>Şifreni değiştir</h3>' + gizli
      + girisAlani('eski', 'Şimdiki şifre', sifreOz(false), '', true) + girisAlani('yeni', 'Yeni şifre', sifreOz(true), 'En az 8 karakter.', true)
      + '<p class="fr-hata" role="alert" hidden data-hata="sifre"></p><button class="fr-g-btn" type="submit">Şifreyi değiştir</button></form>'
      + '<form class="fr-g-form fr-g-bolum" data-form="kod" novalidate><h3>Kurtarma kodu</h3>'
      + '<p class="fr-not">Şifreni unutursan hesabına bu kodla dönersin. Yeni kod oluşturursan eskisi geçersiz olur.</p>' + gizli
      + girisAlani('kodsifre', 'Şifren', sifreOz(false), '', true)
      + '<p class="fr-hata" role="alert" hidden data-hata="kod"></p><button class="fr-g-ikincil" type="submit">Yeni kod oluştur</button></form>');
    var f1 = govde.querySelector('[data-form=sifre]'), f2 = govde.querySelector('[data-form=kod]');
    gonder(f1, '/ben/sifre', function (f) {
      var e = f.querySelector('#fr-g-eski').value, y = f.querySelector('#fr-g-yeni').value;
      if (!e) return 'Şimdiki şifreni yaz.';
      return y.length < 8 ? 'Yeni şifre en az 8 karakter olmalı.' : { eski: e, yeni: y };
    }, function (j) { if (j && j.oturum) yaz('fr-oturum', j.oturum); k.kapat(); bildir('Şifren değişti'); });
    gonder(f2, '/ben/kurtarma-kodu', function (f) {
      var s = f.querySelector('#fr-g-kodsifre').value;
      return s ? { sifre: s } : 'Şifreni yaz.';
    }, function (j) { if (j.oturum) yaz('fr-oturum', j.oturum); k.kodGoster(j.kurtarma_kodu, 'Yeni kurtarma kodun', function () { k.kapat(); }); });
  }

  // Bildirim ayarları (üst çubuktaki hesap menüsünden): özel mesaj izni; Telegram bildirimi yalnız Telegram ile bağlı üyelerde.
  // Sunucu /ben'de dm_acik ve bildirimi true/false verir, giriş yanıtları 0/1 olabilir: ikisi de "kapalı" sayılır.
  function kapali(v) { return v === 0 || v === false; }
  function ayarKutusu() {
    if (!oturum()) { girisKutusu(); return; }
    var k = kabukAc();
    k.ciz('Bildirim ayarları', '', '<p class="fr-yukleniyor">Yükleniyor…</p>');
    api('/ben').then(function (j) { yaz('fr-uye', j.uye); ayarCiz(k, j.uye); hesapOlayi(); }, function (h) { k.ciz('Bildirim ayarları', '', '<p class="fr-hata" role="alert">' + esc(h.message) + '</p>'); });
  }
  function ayarCiz(k, u) {
    k.ciz('Bildirim ayarları', '',
      '<div class="fr-ayar-liste"><label class="fr-anahtar-s"><input type="checkbox" data-ayar="dm_acik"' + (kapali(u.dm_acik) ? '' : ' checked') + '><span>Özel mesaj alabilirim</span></label>'
      + (u.telegram === false
        ? '<p class="fr-not">Yanıtlar, anmalar ve mesajlar sitede, üst çubuktaki hesap menüsünde ve forumdaki zil simgesinde görünür.</p>'
        : '<label class="fr-anahtar-s"><input type="checkbox" data-ayar="bildirim"' + (kapali(u.bildirim) ? '' : ' checked') + '><span>Telegram\'dan bildirim al</span></label>')
      + '</div><p class="fr-hata" role="alert" hidden></p>');
    k.govde.onchange = function (e) {
      var c = e.target.closest('[data-ayar]');
      if (!c) return;
      var ad = c.getAttribute('data-ayar'), g = {}; g[ad] = c.checked;
      k.hata('');
      api('/ben/ayar', { yontem: 'POST', govde: g }).then(function (j) {
        var gnc = oku('fr-uye') || u; yaz('fr-uye', Object.assign(gnc, j.uye || {}));
        bildir(ad === 'dm_acik' ? (c.checked ? 'Özel mesajlar açık' : 'Özel mesajlar kapalı; kimse sana yeni mesaj gönderemez') : (c.checked ? 'Telegram bildirimleri açık' : 'Telegram bildirimleri kapalı'));
      }, function (h) { c.checked = !c.checked; k.hata(h.message); });
    };
  }
  window.kitHesap = { giris: function (baslik) { girisSonrasi = null; girisKutusu(baslik || 'Üye ol ya da giriş yap'); }, ayar: ayarKutusu, cikis: cikis };

  /* ---------- üye kartı (rumuza dokununca) ---------- */
  function uyeKarti(rumuz, cikis_) {
    var eski = document.getElementById('fr-uye-kart');
    if (eski) eski.remove();
    var kutu = el('<div class="fr-perde" id="fr-uye-kart" role="dialog" aria-modal="true" aria-label="' + esc(rumuz) + '"><div class="fr-kutu fr-uye-kutu">'
      + '<button type="button" class="fr-kapat" aria-label="Kapat">×</button><p class="fr-yukleniyor">Yükleniyor…</p></div></div>');
    document.body.appendChild(kutu);
    function kapat() { kutu.remove(); document.removeEventListener('keydown', tus); }
    function tus(e) { if (e.key === 'Escape') kapat(); }
    document.addEventListener('keydown', tus);
    kutu.onclick = function (e) { if (e.target === kutu || e.target.closest('.fr-kapat') || e.target.closest('a')) kapat(); };
    var ic = kutu.querySelector('.fr-kutu');
    api('/uye/' + encodeURIComponent(rumuz)).then(function (u) {
      var rozet = [u.kurucu ? 'Kurucu üye' : '', u.itibar >= 5 ? 'Yardımsever' : ''].filter(Boolean);
      ic.innerHTML = '<button type="button" class="fr-kapat" aria-label="Kapat">×</button><div class="fr-uye-ust">' + avatar(u) + '<div><h2>' + esc(u.rumuz) + '</h2>'
        + (rozet.length ? '<p class="fr-uye-rozet">' + rozet.map(function (r) { return '<span>' + r + '</span>'; }).join('') + '</p>' : '') + '</div></div>'
        + '<dl class="fr-uye-sayilar"><div><dt>Mesaj</dt><dd>' + sayi(u.mesaj_sayisi) + '</dd></div><div><dt>Faydalı bulundu</dt><dd>' + sayi(u.itibar) + '</dd></div>'
        + '<div><dt>Katıldı</dt><dd>' + new Date(u.kayit * 1000).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' }) + '</dd></div></dl>'
        + (uye() && uye().rumuz === u.rumuz ? '' : u.dm_acik === false ? '<p class="fr-not fr-uye-dm">Bu üye özel mesaj almıyor.</p>' : '<a class="btn btn-ana fr-uye-dm" href="' + kok() + 'forum/?mesaj=' + encodeURIComponent(u.rumuz) + '">' + ikon(ZARF) + '<span>Mesaj gönder</span></a>')
        + (u.son_basliklar && u.son_basliklar.length ? '<h3>Son yazdığı konular</h3><ul class="fr-uye-konular">' + u.son_basliklar.map(function (b) {
          return '<li><a href="' + kok() + 'forum/?b=' + b.id + '">' + esc(b.baslik) + '</a></li>';
        }).join('') + '</ul>' : '');
    }, function (h) { ic.innerHTML = '<button type="button" class="fr-kapat" aria-label="Kapat">×</button><p class="fr-bos">' + esc(h.durum === 404 ? 'Bu üye bulunamadı.' : h.message) + '</p>'; });
    iz('forum_uye_kart');
  }
  document.addEventListener('click', function (e) {
    var u = e.target.closest('[data-uye]');
    if (u && (u.closest('#forum') || u.closest('#tartisma'))) { e.preventDefault(); uyeKarti(u.getAttribute('data-uye')); }
  });

  /* ---------- sohbet: mesaj listesi ---------- */
  // Düz, zaman sıralı akış: gün ayıraçları, aynı kişinin art arda mesajları gruplanır, yanıtlar alıntıyla gösterilir.
  function sohbetHtml(mesajlar, secenek) {
    secenek = secenek || {};
    var harita = {}; mesajlar.forEach(function (m) { harita[m.id] = m; });
    var u = uye(), oncekiGun = '', onceki = null, h = '';
    mesajlar.forEach(function (m) {
      var gun = gunAdi(m.olusma);
      if (gun !== oncekiGun) { h += '<div class="fr-gun" role="separator"><span>' + esc(gun) + '</span></div>'; oncekiGun = gun; onceki = null; }
      var ben = m.benim || (u && u.rumuz === m.rumuz && insanMi(m));
      var devam = onceki && onceki.rumuz === m.rumuz && m.olusma - onceki.olusma < 300 && !m.ust_id;
      var ust = m.ust_id ? harita[m.ust_id] : null;
      var alinti = m.ust_id ? '<button type="button" class="fr-alinti" data-git="y' + m.ust_id + '">' + (ust ? '<b>' + esc(ust.rumuz) + '</b><span>' + esc(kisalt(ust.govde, 90)) + '</span>' : '<span>Önceki bir mesaja yanıt</span>') + '</button>' : '';
      var eylem = '<button type="button" class="fr-eylem" data-yanitla="' + m.id + '" data-rumuz="' + esc(m.rumuz) + '" data-rol="' + esc(m.rol) + '">Yanıtla</button>';
      if (!ben) eylem += '<button type="button" class="fr-eylem" data-faydali="' + m.id + '" aria-pressed="' + (m.oyladim ? 'true' : 'false') + '">Faydalı</button>';
      if (ben) eylem += '<button type="button" class="fr-eylem fr-sik" data-sil="' + m.id + '">Sil</button>';
      else if (insanMi(m)) eylem += '<button type="button" class="fr-eylem fr-sik" data-sikayet="' + m.id + '">Bildir</button>';
      h += '<article class="fr-yanit' + (devam ? ' fr-devam' : '') + (m.rol === 'asistan' ? ' fr-yanit-bot' : '') + (ben ? ' fr-benim' : '') + (secenek.yeniden && m.id > secenek.yeniden ? ' fr-yeni' : '') + '" id="y' + m.id + '">'
        + (devam ? '<span class="fr-av-yer" aria-hidden="true"></span>' : avatar(m))
        + '<div class="fr-yanit-ic">' + (devam ? '' : '<header><button type="button" class="fr-ad" data-uye="' + esc(m.rumuz) + '"' + (insanMi(m) ? '' : ' disabled') + '>' + esc(m.rumuz) + '</button>' + etiket(m) + '</header>')
        + '<div class="fr-govde">' + alinti + metin(m.govde) + '<span class="fr-saat">' + (m.faydali ? '<span class="fr-begeni">' + ikon(BASPARMAK) + sayi(m.faydali) + '</span>' : '') + '<time datetime="' + new Date(m.olusma * 1000).toISOString() + '">' + saat(m.olusma) + '</time></span></div>'
        + '<footer>' + eylem + '</footer></div></article>';
      onceki = m;
    });
    return h;
  }
  /* ---------- soru-cevap: cevap kartları ---------- */
  // Forum dili: her cevap ayrı bir kart; en çok "faydalı" bulunan insan cevabı (en az 1 oy) etiketlenip en üste alınır.
  function cevapHtml(mesajlar, secenek) {
    secenek = secenek || {};
    var harita = {}; mesajlar.forEach(function (m) { harita[m.id] = m; });
    var u = uye(), enIyi = null;
    if (!secenek.siraKoru) mesajlar.forEach(function (m) { if (insanMi(m) && m.faydali >= 1 && (!enIyi || m.faydali > enIyi.faydali)) enIyi = m; });
    var sirali = enIyi && mesajlar.length > 1 ? [enIyi].concat(mesajlar.filter(function (m) { return m !== enIyi; })) : mesajlar;
    return sirali.map(function (m) {
      var ben = m.benim || (u && u.rumuz === m.rumuz && insanMi(m));
      var ust = m.ust_id ? harita[m.ust_id] : null;
      var eylem = ben ? (m.faydali ? '<span class="fr-faydali-sayi">' + sayi(m.faydali) + ' kişi faydalı buldu</span>' : '')
        : '<button type="button" class="fr-eylem fr-faydali-d" data-faydali="' + m.id + '" aria-pressed="' + (m.oyladim ? 'true' : 'false') + '">' + ikon(BASPARMAK) + '<span>Faydalı' + (m.faydali ? ' ' + sayi(m.faydali) : '') + '</span></button>';
      eylem += '<button type="button" class="fr-eylem" data-yanitla="' + m.id + '" data-rumuz="' + esc(m.rumuz) + '" data-rol="' + esc(m.rol) + '">Yanıtla</button>';
      if (ben) eylem += '<button type="button" class="fr-eylem fr-sik" data-sil="' + m.id + '">Sil</button>';
      else if (insanMi(m)) eylem += '<button type="button" class="fr-eylem fr-sik" data-sikayet="' + m.id + '">Bildir</button>';
      return '<article class="fr-cevap' + (m === enIyi ? ' fr-en-iyi' : '') + (m.rol === 'asistan' ? ' fr-cevap-bot' : '') + (ben ? ' fr-benim' : '') + (secenek.yeniden && m.id > secenek.yeniden ? ' fr-yeni' : '') + '" id="y' + m.id + '">'
        + (m === enIyi ? '<p class="fr-en-iyi-et">En faydalı cevap</p>' : '')
        + '<header>' + avatar(m) + '<div><button type="button" class="fr-ad" data-uye="' + esc(m.rumuz) + '"' + (insanMi(m) ? '' : ' disabled') + '>' + esc(m.rumuz) + '</button>' + etiket(m)
        + '<time datetime="' + new Date(m.olusma * 1000).toISOString() + '">' + zaman(m.olusma) + '</time></div></header>'
        + (m.ust_id ? '<button type="button" class="fr-yanitlanan-et" data-git="y' + m.ust_id + '">' + (ust ? esc(ust.rumuz) + ' kişisine yanıt' : 'Önceki bir mesaja yanıt') + '</button>' : '')
        + '<div class="fr-metin">' + metin(m.govde) + '</div><footer>' + eylem + '</footer></article>';
    }).join('');
  }
  function yaziciHtml(yer, ipucu, hizli, tur) {
    return '<form class="fr-yazici' + (tur === 'sohbet' ? ' fr-yazici-sohbet' : ' fr-yazici-cevap') + '" data-yer="' + yer + '">'
      + (hizli ? '<div class="fr-hizli">' + hizli.map(function (s) { return '<button type="button" class="fr-cip" data-hizli>' + esc(s) + '</button>'; }).join('') + '</div>' : '')
      + '<div class="fr-yanitlanan" hidden><span></span><button type="button" class="fr-eylem" data-iptal aria-label="Yanıtı iptal et">×</button></div>'
      + '<div class="fr-yazici-ic"><label class="sr-only" for="fr-metin-' + yer + '">Mesajın</label><textarea id="fr-metin-' + yer + '" rows="1" maxlength="2000" placeholder="' + esc(ipucu) + '" enterkeyhint="send"></textarea>'
      + '<button type="submit" class="fr-gonder" aria-label="Gönder">' + ikon('M5 12h13M13 6l6 6-6 6') + '</button></div>'
      + '<p class="fr-hata" role="alert" hidden></p></form>';
  }
  function yaziciBagla(kap, anahtar, gonder) {
    var f = kap.querySelector('.fr-yazici');
    if (!f) return;
    var ust = null, ta = f.querySelector('textarea'), etk = f.querySelector('.fr-yanitlanan'), taslakAd = 'fr-taslak-' + anahtar;
    ta.value = oku(taslakAd) || '';
    function boy() {
      ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight + 2, 180) + 'px'; ta.style.overflowY = ta.scrollHeight > 178 ? 'auto' : 'hidden';
      f.classList.toggle('fr-dolu', !!ta.value.trim());
      var hz = f.querySelector('.fr-hizli'); if (hz) hz.hidden = !!ta.value.trim();
    }
    boy();
    ta.addEventListener('input', function () { yaz(taslakAd, ta.value || null); boy(); });
    function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
    f.querySelector('[data-iptal]').onclick = function () { ust = null; etk.hidden = true; ta.focus(); };
    f.addEventListener('click', function (e) {
      var c = e.target.closest('[data-hizli]');
      if (!c) return;
      ta.value = c.textContent; yaz(taslakAd, ta.value); boy(); ta.focus(); iz('forum_hizli_soru');
    });
    kap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-yanitla]');
      if (!b) return;
      ust = +b.getAttribute('data-yanitla');
      var mesaj = document.getElementById('y' + ust), p_ = mesaj && mesaj.querySelector('.fr-govde > p'), on = p_ ? kisalt(p_.textContent, 70) : '';
      etk.querySelector('span').innerHTML = '<b>' + esc(b.getAttribute('data-rumuz')) + '</b> ' + esc(on);
      etk.hidden = false;
      ta.focus();
    });
    // Sohbette (masaüstü) Enter gönderir, Shift+Enter yeni satır; cevap yazarken Enter yeni satır, Ctrl+Enter gönderir.
    ta.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && GENIS.matches && f.classList.contains('fr-yazici-sohbet')) { e.preventDefault(); f.requestSubmit(); }
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); f.requestSubmit(); }
    });
    f.onsubmit = function (e) {
      if (e && e.preventDefault) e.preventDefault();
      hata('');
      var g = ta.value.trim();
      if (g.length < 2) { ta.focus(); return; }
      if (girisGerekli('Göndermek için giriş yap', function () { yenile(); setTimeout(function () { var y = document.querySelector('.fr-yazici[data-yer="' + f.getAttribute('data-yer') + '"]'); if (y) y.requestSubmit(); }, 500); })) return;
      var d = f.querySelector('[type=submit]'); d.disabled = true;
      gonder(g, ust).then(function () { ta.value = ''; yaz(taslakAd, null); ust = null; etk.hidden = true; boy(); }, function (h) { hata(h.message); })
        .then(function () { d.disabled = false; });
    };
  }
  // Mesaj eylemleri; liste: o görünümün mesaj dizisi (silinen çıkarılır), ciz: yeniden çizer.
  function eylemleriBagla(kap, liste, ciz) {
    kap.addEventListener('click', function (e) {
      var f = e.target.closest('[data-faydali]'), s = e.target.closest('[data-sikayet]'), sl = e.target.closest('[data-sil]'), g = e.target.closest('[data-git]');
      if (g) { var hedef = document.getElementById(g.getAttribute('data-git')); if (hedef) { hedef.scrollIntoView({ behavior: 'smooth', block: 'center' }); hedef.classList.add('fr-vurgu'); setTimeout(function () { hedef.classList.remove('fr-vurgu'); }, 1600); } return; }
      if (f) {
        if (girisGerekli('Giriş yap')) return;
        var id = +f.getAttribute('data-faydali');
        api('/yanit/' + id + '/faydali', { yontem: 'POST', govde: {} }).then(function (j) {
          liste().forEach(function (m) { if (m.id === id) { m.faydali = j.faydali; m.oyladim = j.oyladim; } });
          ciz();
        }, function (h) { bildir(h.message); });
      } else if (s) {
        if (girisGerekli('Giriş yap')) return;
        if (!confirm('Bu mesajı kurallara aykırı diye bildirmek istiyor musun?')) return;
        api('/yanit/' + s.getAttribute('data-sikayet') + '/sikayet', { yontem: 'POST', govde: {} }).then(function () {
          s.textContent = 'Bildirildi'; s.disabled = true; bildir('Teşekkürler, inceleyeceğiz.');
        }, function (h) { bildir(h.message); });
      } else if (sl) {
        if (!confirm('Mesajın silinsin mi?')) return;
        var sid = +sl.getAttribute('data-sil');
        api('/yanit/' + sid, { yontem: 'DELETE' }).then(function () {
          var l = liste(), i = l.findIndex(function (m) { return m.id === sid; });
          if (i >= 0) l.splice(i, 1);
          ciz(); bildir('Mesaj silindi');
        }, function (h) { bildir(h.message); });
      }
    });
  }
  function enAltta(sc) { return sc ? sc.scrollHeight - sc.scrollTop - sc.clientHeight < 80 : (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 120); }
  function enAltaIn(sc) { if (sc) sc.scrollTop = sc.scrollHeight; else window.scrollTo(0, document.documentElement.scrollHeight); }
  // Görünür sekmede yeni mesajları yoklar: odada 20 sn, diğerlerinde 45 sn; sekme gizliyken durur.
  function canliTut(f, sn) {
    var t = setInterval(function () { if (document.visibilityState === 'visible') f(true); }, (sn || 45) * 1000);
    function gorunur() { if (document.visibilityState === 'visible') f(true); }
    document.addEventListener('visibilitychange', gorunur);
    return function () { clearInterval(t); document.removeEventListener('visibilitychange', gorunur); };
  }

  /* ---------- ilan sayfası ---------- */
  function ilanBolumu(kap) {
    var ilan = kap.getAttribute('data-ilan'), ad = kap.getAttribute('data-ad') || 'Bu ilan', acik = kap.getAttribute('data-acik') === '1';
    var mesajlar = [], baslikId = null;
    kap.innerHTML = '<div class="fr-ilan"><header class="fr-ilan-bas"><h2>Sorular</h2><span class="fr-not" data-ozet></span><a class="yazi-link fr-ilan-forum" hidden>Forumda aç</a></header>'
      + '<div class="fr-basvuru"></div><div class="fr-cevaplar" aria-live="polite"></div>'
      + yaziciHtml('ilan', 'Bu ilanla ilgili sorunu yaz…', HIZLI_SORULAR, 'cevap') + '</div>';
    var liste = kap.querySelector('.fr-cevaplar'), bas = kap.querySelector('.fr-basvuru');

    function basvuruCiz(b) {
      b = b || { sayi: 0 };
      var benim = basvurularim()[ilan];
      var yazi = b.sayi ? '<b>' + sayi(b.sayi) + '</b> kişi başvurdu' : (acik ? 'Başvurduysan işaretle' : '');
      var dugme = acik || benim ? '<button type="button" class="fr-basvurdum' + (benim ? ' fr-on' : '') + '" data-basvurdum aria-pressed="' + (benim ? 'true' : 'false') + '">' + (benim ? '✓ Başvurdum' : 'Başvurdum') + '</button>' : '';
      var h = '<div class="fr-basvuru-ust"><span>' + yazi + '</span>' + dugme + '</div>';
      if (b.puan) {
        var p = b.puan, en = p.en_dusuk, ek = p.en_yuksek, ara = Math.max(ek - en, 0.01);
        var yz = function (x) { return ((x - en) / ara * 100).toFixed(1) + '%'; };
        h += '<details class="fr-ac"><summary>Başvuranların puanları (' + sayi(p.adet) + ')</summary>'
          + '<p class="fr-not fr-ara-bilgi">' + parcalar([p.puan_turu, 'en düşük ' + en, 'ortanca ' + p.medyan, 'en yüksek ' + ek, p.sira ? 'sen ' + sayi(p.sira) + '. sıradasın' : '']) + '</p>'
          + '<div class="fr-cubuk" aria-hidden="true"><span class="fr-kutu-c" style="left:' + yz(p.ceyrek1) + ';width:calc(' + yz(p.ceyrek3) + ' - ' + yz(p.ceyrek1) + ')"></span><span class="fr-medyan" style="left:' + yz(p.medyan) + '"></span>'
          + (benim && benim.puan && benim.puan_turu === p.puan_turu ? '<span class="fr-sen" style="left:' + yz(Math.min(Math.max(benim.puan, en), ek)) + '"></span>' : '') + '</div>'
          + '<p class="fr-not">Gönüllü paylaşılan puanlar; resmî değildir.</p></details>';
      }
      if (benim && !benim.puan) {
        h += '<details class="fr-ac"><summary>Puanını anonim ekle</summary><form class="fr-puan"><select aria-label="Puan türü">' + PUAN_TURLERI.map(function (t) { return '<option>' + t + '</option>'; }).join('') + '</select>'
          + '<input type="text" inputmode="decimal" placeholder="78,45" aria-label="Puan" required><button class="btn btn-ikinci" type="submit">Ekle</button></form></details>';
      }
      bas.innerHTML = h;
      bas.hidden = !yazi && !dugme;
      var f = bas.querySelector('.fr-puan');
      if (f) f.onsubmit = function (e) {
        e.preventDefault();
        var tur = f.querySelector('select').value, p = parseFloat(String(f.querySelector('input').value).replace(',', '.'));
        if (!(p >= 40 && p <= 100)) { bildir('Puan 40 ile 100 arasında olmalı.'); return; }
        basvur({ puan_turu: tur, puan: Math.round(p * 100) / 100 });
      };
    }
    function basvur(puan) {
      var govde = { kimlik: kimlik() };
      if (puan) { govde.puan_turu = puan.puan_turu; govde.puan = puan.puan; }
      api('/basvuru/' + encodeURIComponent(ilan), { yontem: 'POST', govde: govde }).then(function (j) {
        var m = basvurularim(), k = m[ilan] || {}; k.ad = ad; if (puan) { k.puan_turu = puan.puan_turu; k.puan = puan.puan; } m[ilan] = k; yaz('fr-basvuru', m);
        iz('forum_basvurdum', puan ? 'puan' : ''); bildir(puan ? 'Puanın eklendi' : 'Bol şans!');
        basvuruCiz(j.basvuru);
      }, function (h) { bildir(h.message); });
    }
    bas.addEventListener('click', function (e) {
      if (!e.target.closest('[data-basvurdum]')) return;
      if (basvurularim()[ilan]) {
        if (!confirm('Başvurdum işaretini kaldırayım mı?')) return;
        api('/basvuru/' + encodeURIComponent(ilan) + '?kimlik=' + kimlik(), { yontem: 'DELETE' }).then(function (j) {
          var m = basvurularim(); delete m[ilan]; yaz('fr-basvuru', m); basvuruCiz(j.basvuru);
        }, function (h) { bildir(h.message); });
      } else basvur(null);
    });
    function ciz(yeniden) {
      liste.innerHTML = cevapHtml(mesajlar, { yeniden: yeniden, siraKoru: true });
      var n = mesajlar.filter(insanMi).length;
      kap.querySelector('[data-ozet]').textContent = n ? sayi(n) + ' mesaj' : 'Henüz soru yok';
      ctaGuncelle(n);
      var fb = kap.querySelector('.fr-ilan-forum');
      if (baslikId) { fb.href = kok() + 'forum/?b=' + baslikId; fb.hidden = false; }
    }
    function yukle(sessiz) {
      if (sessiz === true && baslikId) {   // yoklama: yalnız son mesajdan sonrası
        var son = mesajlar.length ? mesajlar[mesajlar.length - 1].id : 0;
        return api('/baslik/' + baslikId + '/yeni?sonra=' + son).then(function (j) {
          var y = (j.yanitlar || []).filter(function (m) { return !mesajlar.some(function (x) { return x.id === m.id; }); });
          if (!y.length) return;
          mesajlar = mesajlar.concat(y); ciz(son); bildir('Yeni mesaj');
        }, function () {});
      }
      if (sessiz === true) return Promise.resolve();
      var k = basvurularim()[ilan] ? '?kimlik=' + kimlik() : '';
      return api('/ilan/' + encodeURIComponent(ilan) + k).then(function (j) {
        mesajlar = j.yanitlar || [];
        if (j.baslik && j.baslik.id) baslikId = j.baslik.id;
        ciz(); basvuruCiz(j.basvuru);
      }, function () { kap.querySelector('[data-ozet]').textContent = 'Şu an yüklenemedi'; });
    }
    function gonder(g, ust) {
      var istek = ust && baslikId
        ? api('/baslik/' + baslikId + '/yanit', { yontem: 'POST', govde: { govde: g, ust_id: ust } })
        : api('/ilan/' + encodeURIComponent(ilan) + '/yanit', { yontem: 'POST', govde: { govde: g, ilan_baslik: ad } });
      return istek.then(function () { iz('forum_yanit', 'ilan'); return yukle(); });
    }
    yaziciBagla(kap, 'ilan-' + ilan, gonder);
    eylemleriBagla(kap, function () { return mesajlar; }, function () { ciz(); });
    yenileyiciler.push(function () {
      var y = kap.querySelector('.fr-yazici');
      if (y) { y.replaceWith(el(yaziciHtml('ilan', 'Bu ilanla ilgili sorunu yaz…', HIZLI_SORULAR, 'cevap'))); yaziciBagla(kap, 'ilan-' + ilan, gonder); }
      return yukle();
    });
    canliTut(yukle);
    yuzenDugme(kap);
    yukle();
  }
  var ctaSayi = 0;
  function ctaGuncelle(n) {
    ctaSayi = n;
    document.querySelectorAll('[data-fr-cta]').forEach(function (s) { s.textContent = n ? 'Sorular (' + sayi(n) + ')' : 'Soru sor'; });
  }
  function konusmayaGit(e) {
    var t = document.getElementById('tartisma');
    if (!t) return;
    if (e) e.preventDefault();
    t.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(function () { var x = t.querySelector('.fr-yazici textarea'); if (x) x.focus({ preventScroll: true }); }, 450);
    iz('forum_cta');
  }
  function yuzenDugme(kap) {
    document.querySelectorAll('a.fr-cta').forEach(function (a) { a.addEventListener('click', konusmayaGit); });
    var b = el('<button type="button" class="fr-yuzen" hidden aria-label="Sorulara git">' + ikon(SOHBET) + '<span data-fr-cta>Soru sor</span></button>');
    b.onclick = konusmayaGit;
    document.body.appendChild(b);
    ctaGuncelle(ctaSayi);
    if (!('IntersectionObserver' in window)) return;
    var g = { t: false, c: true }, cta = document.querySelector('a.fr-cta');
    function karar() { b.hidden = g.t || g.c; }
    new IntersectionObserver(function (x) { g.t = x[0].isIntersecting; karar(); }, { rootMargin: '0px 0px -30% 0px' }).observe(kap);
    if (cta) new IntersectionObserver(function (x) { g.c = x[0].isIntersecting || x[0].boundingClientRect.top > 0; karar(); }).observe(cta);
    else g.c = false;
  }

  /* ---------- bildirimler: zil + menüdeki Forum bağlantısında sayı ---------- */
  function bildirimSayisiGoster(n) {
    var toplam = n + (oku('fr-ozel-sayi') || 0);
    document.querySelectorAll('a[data-a-x="Forum"]').forEach(function (a) {
      var b = a.querySelector('.fr-menu-sayi');
      if (!toplam) { if (b) b.remove(); return; }
      if (!b) { b = el('<b class="tb-sayi fr-menu-sayi"></b>'); a.appendChild(b); }
      b.textContent = toplam > 9 ? '9+' : String(toplam);
      b.setAttribute('aria-label', toplam + ' okunmamış bildirim ve mesaj');
    });
    document.querySelectorAll('[data-zil-sayi]').forEach(function (s) { s.textContent = n ? (n > 9 ? '9+' : n) : ''; s.hidden = !n; });
  }
  // En çok 3 dakikada bir sorulur (sonuç tarayıcıda saklanır), yalnız giriş yapmış kişiler için.
  function bildirimleriYokla(zorla) {
    if (!oturum()) { bildirimSayisiGoster(0); return Promise.resolve([]); }
    var bel = oku('fr-bildirim-sayi'), simdi = Date.now();
    if (!zorla && bel && simdi - bel.t < 180000) { bildirimSayisiGoster(bel.n); return Promise.resolve(null); }
    var son = oku('fr-bildirim-son') || 0;
    return api('/ben/bildirimler' + (son ? '?sonra=' + son : '')).then(function (j) {
      var l = j.bildirimler || [];
      yaz('fr-bildirim-sayi', { t: simdi, n: l.length });
      bildirimSayisiGoster(l.length);
      return l;
    }, function () { return []; });
  }
  function bildirimPaneli(dugme) {
    var acik = document.getElementById('fr-bildirimler');
    if (acik) { acik.remove(); return; }
    var p = el('<div class="fr-bildirim-panel" id="fr-bildirimler" role="dialog" aria-label="Bildirimler"><p class="fr-yukleniyor">Yükleniyor…</p></div>');
    dugme.parentNode.appendChild(p);
    api('/ben/bildirimler?sonra=' + Math.floor(Date.now() / 1000 - 14 * 86400)).then(function (j) {
      var l = j.bildirimler || [], son = oku('fr-bildirim-son') || 0;
      var ne = { yanit: 'konuna yazdı', alinti: 'mesajını yanıtladı', anma: 'senden bahsetti', takip: 'takip ettiğin yere yazdı' };
      p.innerHTML = '<h3>Bildirimler</h3>' + (l.length ? '<ul>' + l.map(function (b) {
        return '<li' + (b.olusma > son ? ' class="fr-okunmamis"' : '') + '><a data-ic href="?' + (b.oda ? 'oda=' : 'b=') + b.baslik_id + '#y' + b.yanit_id + '"><b>' + esc(b.rumuz) + '</b> ' + ne[b.tur] + '<span>' + esc(b.baslik) + '</span><small>' + esc(b.kisa) + '</small><time>' + zaman(b.olusma) + '</time></a></li>';
      }).join('') + '</ul>' : '<p class="fr-bos">Yeni bir şey yok. Birisi sana yanıt verince burada görünür.</p>');
      yaz('fr-bildirim-son', j.simdi || Math.floor(Date.now() / 1000));
      yaz('fr-bildirim-sayi', { t: Date.now(), n: 0 });
      bildirimSayisiGoster(0);
    }, function (h) { p.innerHTML = '<p class="fr-bos">' + esc(h.message) + '</p>'; });
    setTimeout(function () {
      document.addEventListener('click', function kapat(e) { if (!e.target.closest('#fr-bildirimler') && !e.target.closest('[data-zil]')) { p.remove(); document.removeEventListener('click', kapat); } });
    });
  }

  /* ---------- takip ve özel mesaj sayısı ---------- */
  function takipDugmesi(acik, tur) {
    return '<button type="button" class="fr-eylem fr-takip-d" data-takip="' + tur + '" aria-pressed="' + (acik ? 'true' : 'false') + '">' + ikon(ZIL) + '<span>'
      + (acik ? (tur === 'oda' ? 'Bildirim açık' : 'Takipte') : (tur === 'oda' ? 'Bildirim al' : 'Takip et')) + '</span></button>';
  }
  function ozelSayisiGoster(n) {
    yaz('fr-ozel-sayi', n || 0);
    document.querySelectorAll('[data-ozel-sayi]').forEach(function (s) { s.textContent = n ? (n > 9 ? '9+' : n) : ''; s.hidden = !n; });
    var b = oku('fr-bildirim-sayi'); bildirimSayisiGoster((b && b.n) || 0);
  }
  var benZamani = 0;
  function benYenile() {   // /ben: rumuz, ayarlar, okunmamış özel mesaj sayısı, profil ve kayıtlı ilanlar (en çok 2 dakikada bir; sayfalar arası da)
    if (!oturum() || Date.now() - benZamani < 120000 || Date.now() - (oku('fr-ben-t') || 0) < 120000) return;
    benZamani = Date.now(); yaz('fr-ben-t', benZamani);
    api('/ben').then(function (j) {
      yaz('fr-uye', j.uye); ozelSayisiGoster((j.uye && j.uye.ozel_okunmamis) || j.ozel_okunmamis || 0); profilSenkron(j.profil); kayitliSenkron(j.kayitli); hesapOlayi();
    }, function () {});
  }

  /* ---------- forum sayfası ---------- */
  var puanVerisi = {};
  function puanOzeti(kap, b) {
    if (!b.puan || !/^(lisans|onlisans|ortaogretim)$/.test(b.duzey || '')) return;
    var yer = kap.querySelector('[data-puan-ozet]');
    if (!yer) return;
    (puanVerisi[b.duzey] = puanVerisi[b.duzey] || fetch('../puanlar/' + b.duzey + '.json').then(function (r) { return r.json(); })).then(function (v) {
      var donem = Object.keys(v.donemler || {}).sort().pop();
      if (!donem) return;
      var uyan = v.donemler[donem].filter(function (s) { return s.min != null && s.min <= b.puan; });
      var p = String(b.puan).replace('.', ',');
      yer.innerHTML = '<p class="fr-puan-ozet"><span class="fr-et">site verisi</span> ' + esc(donem.replace('-', '/')) + ' yerleştirmesinde ' + esc(v.ad.toLocaleLowerCase('tr-TR')) + ' ' + p
        + ' ve altı puanla yerleşilen <b>' + sayi(uyan.length) + ' kadro</b> vardı. Bölümüne uyanlar için <a href="../puanlar/">tercih robotu</a>.</p>';
    }, function () {});
  }
  function anketHtml(a) {
    if (!a) return '';
    var oyVer = a.benim == null;
    return '<div class="fr-anket">' + a.secenekler.map(function (s) {
      var y = a.toplam ? Math.round(s.oy / a.toplam * 100) : 0;
      return oyVer ? '<button type="button" class="fr-anket-s" data-oy="' + s.sira + '">' + esc(s.metin) + '</button>'
        : '<div class="fr-anket-s fr-sonuc' + (a.benim === s.sira ? ' fr-on' : '') + '"><i style="width:' + y + '%"></i><span>' + esc(s.metin) + '</span><b>%' + y + '</b></div>';
    }).join('') + '<small class="fr-not">' + sayi(a.toplam) + ' oy</small></div>';
  }

  // Forum sayfası iki ayrı bölümdür ve bilerek farklı görünür:
  //   Soru-Cevap (?, ?b=<id>, ?yeni=1): kalıcı sorular, kart cevaplar, en faydalı cevap öne çıkar; klasik tek sütun.
  //   Sohbet odaları (?bolum=sohbet, ?oda=<id>): yalnız odalar, mesaj balonları, anlık; geniş ekranda iki panel.
  function forumSayfasi(kok_) {
    var durdur = null, listeDurdur = null, seciliOda = 0, seciliKisi = '';
    function git(q) { history.pushState(null, '', q || location.pathname); ciz(); if (!GENIS.matches || !/oda=/.test(q || '')) window.scrollTo(0, 0); }
    kok_.innerHTML = '<div class="fr-bas"><nav class="fr-bolumler" aria-label="Forum bölümleri">'
      + '<a data-ic data-bolum="soru" href="?">' + ikon('M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17.5h.01M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z') + '<span><b>Soru-Cevap</b><small>Sor, cevaplar kalıcı kalsın</small></span></a>'
      + '<a data-ic data-bolum="sohbet" href="?bolum=sohbet">' + ikon(SOHBET) + '<span><b>Sohbet odaları</b><small>Aynı sınava hazırlananlarla anlık konuş</small></span><i class="fr-bolum-sayi" data-oda-sayi hidden></i></a>'
      + '<a data-ic data-bolum="mesaj" href="?bolum=mesaj">' + ikon(ZARF) + '<span><b>Mesajlar</b><small>Üyelerle bire bir yazış</small></span><i class="fr-bolum-sayi" data-ozel-sayi hidden></i></a>'
      + '</nav><div class="fr-araclar"></div></div><div class="fr-icerik"></div>';
    var icerik = kok_.querySelector('.fr-icerik'), araclar = kok_.querySelector('.fr-araclar');
    kok_.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-ic]');
      if (a && !e.metaKey && !e.ctrlKey && !e.shiftKey) { e.preventDefault(); var p = document.getElementById('fr-bildirimler'); if (p) p.remove(); git(a.getAttribute('href')); return; }
      if (e.target.closest('[data-cikis]')) cikis();
      if (e.target.closest('[data-hesap]')) { var mn = e.target.closest('details'); if (mn) mn.open = false; hesapKutusu(); }
      if (e.target.closest('[data-giris]')) girisKutusu();
      var z = e.target.closest('[data-zil]');
      if (z) { if (girisGerekli('Bildirimler için giriş yap')) return; bildirimPaneli(z); }
      var d = e.target.closest('[data-duzey-sec]');
      if (d) {
        yaz('fr-duzey', d.getAttribute('data-duzey-sec')); iz('forum_duzey', d.getAttribute('data-duzey-sec'));
        var Ls = icerik.querySelector('.fr-sh-liste'); if (Ls) Ls.removeAttribute('data-p');
        ciz();
      }
      var tk = e.target.closest('[data-takip]');
      if (tk) {
        if (girisGerekli('Takip için giriş yap')) return;
        var id_ = +(new URLSearchParams(location.search).get('b') || new URLSearchParams(location.search).get('oda'));
        var yeniT = tk.getAttribute('aria-pressed') !== 'true';
        api('/baslik/' + id_ + '/takip', { yontem: 'POST', govde: { takip: yeniT } }).then(function (j) {
          tk.outerHTML = takipDugmesi(j.takip, tk.getAttribute('data-takip'));
          bildir(j.takip ? 'Yeni mesajlarda haber vereceğiz' : 'Takipten çıkarıldı'); iz('forum_takip', j.takip ? 'ac' : 'kapa');
        }, function (h) { bildir(h.message); });
      }
      var pl = e.target.closest('[data-paylas]');
      if (pl) {
        var u = location.href.split('#')[0];
        if (navigator.share) navigator.share({ title: document.title, url: u }).catch(function () {});
        else { try { navigator.clipboard.writeText(u); bildir('Bağlantı kopyalandı'); } catch (x) {} }
      }
    });
    window.addEventListener('popstate', ciz);
    function araclarCiz() {
      var u = uye();
      araclar.innerHTML = '<button type="button" class="fr-zil" data-zil aria-label="Bildirimler">' + ikon(ZIL) + '<b data-zil-sayi hidden></b></button>'
        + (u ? '<details class="fr-ben"><summary aria-label="Hesabım">' + avatar(u) + '</summary><div><p><b>' + esc(u.rumuz) + '</b></p>'
          + (u.kurucu ? '<p>Kurucu üye</p>' : '') + (u.itibar ? '<p>' + sayi(u.itibar) + ' kez faydalı bulundu</p>' : '')
          + '<a class="fr-ben-bag" data-ic href="?takip=1">Takip ettiklerim</a><a class="fr-ben-bag" data-ic href="?bolum=mesaj">Mesajlarım</a>'
          + '<label class="fr-anahtar-s"><input type="checkbox" data-ayar="dm_acik"' + (kapali(u.dm_acik) ? '' : ' checked') + '><span>Özel mesaj alabilirim</span></label>'
          + (u.telegram === false ? '' : '<label class="fr-anahtar-s"><input type="checkbox" data-ayar="bildirim"' + (kapali(u.bildirim) ? '' : ' checked') + '><span>Telegram\'dan bildirim al</span></label>')
          + '<button type="button" class="fr-eylem" data-hesap>Şifre ve kurtarma kodu</button><button type="button" class="fr-eylem" data-cikis>Çıkış</button></div></details>'
          : '<button type="button" class="fr-eylem fr-giris-d" data-giris>Giriş</button>');
      bildirimleriYokla();
      ozelSayisiGoster((oku('fr-ozel-sayi') || 0));
    }
    function okunmamis(b) { var g = gorulen()[b.id]; return g != null ? Math.max(0, b.yanit_sayisi - g) : 0; }

    /* ----- Soru-Cevap ----- */
    function soruSatiri(b) {
      var yeniN = okunmamis(b), n = b.yanit_sayisi || 0;
      var hedef = b._oda ? '?oda=' + b.id : '?b=' + b.id;
      return '<a class="fr-soru-satir' + (yeniN ? ' fr-okunmamis' : '') + '" data-kat="' + esc(b.ilan_id ? 'ilan' : b.kategori) + '" data-ic href="' + hedef + '">'
        + '<span class="fr-cevap-kutu' + (n ? ' fr-cevapli' : b.sabit ? '' : ' fr-yanitsiz') + '"><b>' + sayi(n) + '</b><small>cevap</small></span>'
        + '<span class="fr-soru-ic"><b class="fr-soru-bas">' + (b.sabit ? '<span class="fr-sabit">Sabit</span> ' : '') + esc(b.baslik) + '</b>'
        + '<span class="fr-soru-alt"><span class="fr-kat-cip">' + esc(b.ilan_id ? 'İlan sorusu' : katAd(b.kategori)) + '</span>' + (b.duzey ? '<span class="fr-duzey-cip" data-duzey="' + esc(b.duzey) + '">' + esc(duzeyAd(b.duzey)) + '</span>' : '') + (b.anket ? '<span class="fr-anket-cip">Anket</span>' : '') + parcalar([b.rumuz, zaman(b.son_hareket || b.olusma)]) + '</span></span>'
        + (yeniN ? '<span class="fr-yeni-cevap">' + sayi(yeniN) + ' yeni</span>' : '') + '</a>';
    }
    function soruListesi(p) {
      var secili = p.takip ? 'takip' : p.bekleyen ? 'bekleyen' : p.k;
      icerik.innerHTML = '<div class="fr-qa-ust"><form class="fr-ara" role="search"><input type="search" maxlength="60" placeholder="Sorularda ara" value="' + esc(p.q) + '" aria-label="Sorularda ara"></form>'
        + '<a class="btn btn-ana" data-ic href="?yeni=1' + (p.k && p.k !== 'ilan' && p.k !== 'etkinlik' ? '&k=' + p.k : '') + '">Soru sor</a></div>'
        + (p.q ? '<p class="fr-arama-bas"><span>“' + esc(p.q) + '” için sonuçlar</span><a class="yazi-link" data-ic href="?">Temizle</a></p>'
          : '<nav class="fr-sekmeler" aria-label="Soru konuları"><a data-ic href="?"' + (!secili ? ' aria-current="page"' : '') + '>Tümü</a>'
            + (oturum() ? '<a data-ic href="?takip=1" class="fr-sekme-takip"' + (p.takip ? ' aria-current="page"' : '') + '>Takip ettiklerim</a>' : '')
            + '<a data-ic href="?bekleyen=1"' + (secili === 'bekleyen' ? ' aria-current="page"' : '') + '>Cevap bekleyenler</a>'
            + KATEGORILER.filter(function (c) { return c.kod !== 'oda'; }).map(function (c) { return '<a data-ic href="?k=' + c.kod + '" data-kat="' + c.kod + '"' + (secili === c.kod ? ' aria-current="page"' : '') + '>' + esc(c.ad) + '</a>'; }).join('') + '</nav>')
        + '<div class="fr-sorular"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = icerik.querySelector('.fr-sorular'), f = icerik.querySelector('.fr-ara');
      f.onsubmit = function (e) { e.preventDefault(); var q = f.querySelector('input').value.trim(); if (q.length >= 2) { iz('forum_ara'); git('?q=' + encodeURIComponent(q)); } else if (!q) git('?'); };
      function getir(sayfa, ekle) {
        var yol = p.takip ? '/ben/takipler' : p.q ? '/ara?q=' + encodeURIComponent(p.q) : '/basliklar?kategori=' + encodeURIComponent(p.k || '') + '&sayfa=' + sayfa + (p.bekleyen ? '&bekleyen=1' : '');
        if (p.takip && !oturum()) { kap.innerHTML = '<p class="fr-bos">Takip ettiğin soruları görmek için <button type="button" class="fr-eylem" data-giris>giriş yap</button>.</p>'; return Promise.resolve(); }
        return api(yol).then(function (j) {
          var b = (j.basliklar || []).filter(function (x) { return p.takip || x.kategori !== 'oda'; });
          var eski = kap.querySelector('.fr-daha'); if (eski) eski.remove();
          if (!ekle) kap.innerHTML = b.length ? '' : '<p class="fr-bos">' + (p.takip ? 'Henüz bir şey takip etmiyorsun. Soru sorduğunda ya da cevap yazdığında o soru kendiliğinden takibe alınır.' : p.q ? 'Sonuç yok. <a class="yazi-link" data-ic href="?yeni=1">Sorunu sor</a>, bilen biri cevaplar.' : p.bekleyen ? 'Cevap bekleyen soru yok.' : 'Henüz soru yok. <a class="yazi-link" data-ic href="?yeni=1">İlk soruyu sen sor</a>.') + '</p>';
          kap.insertAdjacentHTML('beforeend', b.map(function (x) { return x.kategori === 'oda' ? soruSatiri(Object.assign({}, x, { _oda: true })) : soruSatiri(x); }).join(''));
          if (j.sonraki && !p.q && !p.takip) {
            var d = el('<button type="button" class="fr-eylem fr-daha">Daha fazla soru</button>');
            d.onclick = function () { d.disabled = true; getir(sayfa + 1, true); };
            kap.appendChild(d);
          }
        }, function (h) { kap.innerHTML = '<p class="fr-bos">' + esc(h.message) + '</p>'; });
      }
      getir(1);
    }
    function soruSayfasi(id) {
      icerik.innerHTML = '<p class="fr-geri-link"><a class="yazi-link" data-ic href="?">Tüm sorular</a></p><div class="fr-soru-sayfa"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = icerik.querySelector('.fr-soru-sayfa'), b = null, mesajlar = [], dahaEski = false;
      function cizCevaplar(yeniden) {
        var l = kap.querySelector('[data-cevaplar]');
        kap.querySelector('[data-cevap-sayi]').textContent = mesajlar.length ? sayi(mesajlar.length) + ' cevap' : 'Henüz cevap yok';
        l.innerHTML = mesajlar.length ? cevapHtml(mesajlar, { yeniden: yeniden }) : '<p class="fr-bos">Bu soruya ilk cevabı sen ver. Bildiğin kadarı bile yardımcı olur.</p>';
        kap.querySelector('.fr-eskiler').hidden = !dahaEski;
      }
      function ilkCiz(j) {
        b = j.baslik;
        document.title = b.baslik + ' — Soru-Cevap — KPSS Tercihi';
        var benim = uye() && uye().rumuz === b.rumuz;
        kap.innerHTML = '<article class="fr-soru-kart" data-kat="' + esc(b.ilan_id ? 'ilan' : b.kategori) + '"><p class="fr-ust-bilgi"><span class="fr-kat-cip">' + esc(b.ilan_id ? 'İlan sorusu' : katAd(b.kategori)) + '</span>' + (b.duzey ? '<span class="fr-duzey-cip" data-duzey="' + esc(b.duzey) + '">' + esc(duzeyAd(b.duzey)) + '</span>' : '') + parcalar([b.puan_turu && b.puan != null ? b.puan_turu + ' ' + String(b.puan).replace('.', ',') : '']) + '</p>'
          + '<h2 class="fr-soru-baslik">' + esc(b.baslik) + '</h2>'
          + '<header>' + avatar(b) + '<div><button type="button" class="fr-ad" data-uye="' + esc(b.rumuz) + '"' + (insanMi(b) ? '' : ' disabled') + '>' + esc(b.rumuz) + '</button>' + etiket(b) + '<time>' + zaman(b.olusma) + '</time></div></header>'
          + (b.govde ? '<div class="fr-metin">' + metin(b.govde) + '</div>' : '')
          + (b.ilan_id ? '<p><a class="yazi-link" href="../ilan/' + encodeURIComponent(b.ilan_id) + '/">İlan sayfasını aç</a></p>' : '')
          + '<div data-anket-yer></div><div data-puan-ozet></div>'
          + '<footer>' + (benim || !insanMi(b) ? '' : '<button type="button" class="fr-eylem fr-faydali-d" data-baslik-oy aria-pressed="' + (b.oyladim ? 'true' : 'false') + '">' + ikon(BASPARMAK) + '<span>Faydalı soru' + (b.faydali ? ' ' + sayi(b.faydali) : '') + '</span></button>')
          + takipDugmesi(j.takip, 'soru') + '<button type="button" class="fr-eylem" data-paylas>Paylaş</button></footer></article>'
          + '<h3 class="fr-cevap-bas" data-cevap-sayi></h3><button type="button" class="fr-eylem fr-eskiler" hidden>Önceki cevaplar</button><div class="fr-cevaplar" data-cevaplar aria-live="polite"></div>'
          + '<div class="fr-cevap-yaz"><h3>Cevabın</h3>' + yaziciHtml('soru-' + id, 'Bildiğini paylaş. Kimlik no, telefon yazma.', null, 'cevap') + '</div>';
        var ay = kap.querySelector('[data-anket-yer]'); if (ay) ay.innerHTML = anketHtml(j.anket);
        puanOzeti(kap, b);
        kap.querySelector('.fr-eskiler').onclick = function () {
          var d = this; d.disabled = true;
          api('/baslik/' + id + '?once=' + mesajlar[0].id).then(function (k) { mesajlar = (k.yanitlar || []).concat(mesajlar); dahaEski = !!k.daha_eski; cizCevaplar(); }, function (h) { bildir(h.message); }).then(function () { d.disabled = false; });
        };
        yaziciBagla(kap, 'soru-' + id, function (g, ust) {
          var govde = { govde: g }; if (ust) govde.ust_id = ust;
          return api('/baslik/' + id + '/yanit', { yontem: 'POST', govde: govde }).then(function () { iz('forum_yanit', 'soru'); bildir('Cevabın eklendi'); return yukle(true); });
        });
      }
      function yukle(sessiz) {
        if (sessiz === true && b) {
          var son = mesajlar.reduce(function (a, m) { return Math.max(a, m.id); }, 0);
          return api('/baslik/' + id + '/yeni?sonra=' + son).then(function (j) {
            var y = (j.yanitlar || []).filter(function (m) { return !mesajlar.some(function (x) { return x.id === m.id; }); });
            if (j.yanit_sayisi != null) b.yanit_sayisi = j.yanit_sayisi;
            if (!y.length) return;
            mesajlar = mesajlar.concat(y); cizCevaplar(son); gorulduIsaretle(id, b.yanit_sayisi);
          }, function () {});
        }
        return api('/baslik/' + id).then(function (j) {
          if (j.baslik.kategori === 'oda') { history.replaceState(null, '', '?oda=' + id + location.hash); ciz(); return; }
          mesajlar = j.yanitlar || []; dahaEski = !!j.daha_eski;
          ilkCiz(j); cizCevaplar(); gorulduIsaretle(id, j.baslik.yanit_sayisi);
          if (location.hash && document.getElementById(location.hash.slice(1))) document.getElementById(location.hash.slice(1)).scrollIntoView({ block: 'center' });
        }, function (h) { kap.innerHTML = '<p class="fr-bos">' + (h.durum === 404 ? 'Bu soru bulunamadı ya da kaldırıldı. <a class="yazi-link" data-ic href="?">Tüm sorular</a>' : esc(h.message)) + '</p>'; });
      }
      kap.addEventListener('click', function (e) {
        var o = e.target.closest('[data-oy]'), bo = e.target.closest('[data-baslik-oy]');
        if (o) {
          if (girisGerekli('Oy vermek için giriş yap')) return;
          api('/baslik/' + id + '/anket', { yontem: 'POST', govde: { sira: +o.getAttribute('data-oy') } }).then(function (a) {
            kap.querySelector('[data-anket-yer]').innerHTML = anketHtml(a.anket || a); iz('forum_anket');
          }, function (h) { bildir(h.message); });
        } else if (bo) {
          if (girisGerekli('Giriş yap')) return;
          api('/baslik/' + id + '/faydali', { yontem: 'POST', govde: {} }).then(function (j) {
            bo.setAttribute('aria-pressed', String(!!j.oyladim)); bo.querySelector('span').textContent = 'Faydalı soru' + (j.faydali ? ' ' + sayi(j.faydali) : '');
          }, function (h) { bildir(h.message); });
        }
      });
      eylemleriBagla(kap, function () { return mesajlar; }, function () { cizCevaplar(); });
      yenileyiciler = [function () { return yukle(); }];
      durdur = canliTut(yukle, 45);
      yukle();
    }
    function yeni(kategori) {
      var u = uye();
      var secenek = KATEGORILER.filter(function (c) { return c.kod !== 'ilan' && c.kod !== 'oda' && (c.kod !== 'etkinlik' || (u && (u.rol === 'yonetici' || u.rol === 'sistem'))); });
      var t = oku('fr-taslak-yeni') || {};
      var dz = t.duzey != null ? t.duzey : duzeyim();
      var ekAcik = !!(t.puan || (t.anket && t.anket.length));
      icerik.innerHTML = '<p class="fr-geri-link"><a class="yazi-link" data-ic href="?">Tüm sorular</a></p><form class="fr-form fr-yeni"><h2>Soru sor</h2><p class="fr-not">Sorun kalıcı bir başlık olur; bilenler cevap yazar, en faydalı cevap öne çıkar. Anlık sohbet için <a class="yazi-link" data-ic href="?bolum=sohbet">sohbet odalarına</a> geç.</p>'
        + '<input id="fr-b" maxlength="120" required placeholder="Başlık: ör. Önlisans 72 puanla nereye başvurabilirim?" value="' + esc(t.baslik || '') + '" aria-label="Başlık">'
        + '<textarea id="fr-g" rows="5" maxlength="4000" required placeholder="Ayrıntı: bölümün, puanın, aklına takılan…" aria-label="Ayrıntı">' + esc(t.govde || '') + '</textarea>'
        + '<div class="fr-yeni-satir"><select id="fr-k" aria-label="Konu">' + secenek.map(function (c) { return '<option value="' + c.kod + '"' + ((t.kategori || kategori || 'puan') === c.kod ? ' selected' : '') + '>' + esc(c.ad) + '</option>'; }).join('') + '</select>'
        + '<select id="fr-d" aria-label="Öğrenim düzeyi"><option value="">Düzey</option>' + DUZEYLER.map(function (d) { return '<option value="' + d.kod + '"' + (dz === d.kod ? ' selected' : '') + '>' + d.ad + '</option>'; }).join('') + '</select></div>'
        + '<details class="fr-ac"' + (ekAcik ? ' open' : '') + '><summary>Puan veya anket ekle</summary><div class="fr-ek">'
        + '<span class="fr-puan"><select id="fr-pt" aria-label="Puan türü">' + PUAN_TURLERI.map(function (x) { return '<option' + (t.puan_turu === x ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select>'
        + '<input id="fr-p" inputmode="decimal" placeholder="Puanın" value="' + esc(t.puan || '') + '" aria-label="Puan"></span>'
        + '<div class="fr-anket-g">' + [0, 1, 2, 3].map(function (i) { return '<input maxlength="80" placeholder="Anket seçeneği ' + (i + 1) + '" value="' + esc((t.anket || [])[i] || '') + '">'; }).join('') + '</div>'
        + '</div></details>'
        + '<button class="btn btn-ana btn-buyuk" type="submit">Soruyu yayınla</button><p class="fr-hata" role="alert" hidden></p></form>';
      var f = icerik.querySelector('form');
      function deger() {
        return { kategori: f.querySelector('#fr-k').value, duzey: f.querySelector('#fr-d').value, puan_turu: f.querySelector('#fr-pt').value,
          puan: String(f.querySelector('#fr-p').value).trim().replace(',', '.'), baslik: f.querySelector('#fr-b').value.trim(), govde: f.querySelector('#fr-g').value.trim(),
          anket: Array.prototype.map.call(f.querySelectorAll('.fr-anket-g input'), function (x) { return x.value.trim(); }).filter(Boolean) };
      }
      f.addEventListener('input', function () { yaz('fr-taslak-yeni', deger()); });
      f.addEventListener('change', function () { yaz('fr-taslak-yeni', deger()); });
      function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
      f.onsubmit = function (e) {
        if (e && e.preventDefault) e.preventDefault();
        hata('');
        var g = deger(), govde = { kategori: g.kategori, baslik: g.baslik, govde: g.govde };
        if (g.baslik.length < 8) return hata('Başlık en az 8 karakter olmalı.');
        if (g.govde.length < 10) return hata('Biraz daha ayrıntı yaz.');
        if (g.duzey) govde.duzey = g.duzey;
        if (g.puan) {
          var p = parseFloat(g.puan);
          if (!(p >= 40 && p <= 100)) return hata('Puan 40 ile 100 arasında olmalı.');
          govde.puan_turu = g.puan_turu; govde.puan = Math.round(p * 100) / 100;
        }
        if (g.anket.length === 1) return hata('Anket için en az iki seçenek yaz.');
        if (g.anket.length >= 2) govde.anket = { secenekler: g.anket };
        if (girisGerekli('Göndermek için giriş yap', function () { git('?yeni=1'); setTimeout(function () { var x = document.querySelector('form.fr-yeni'); if (x) x.requestSubmit(); }, 400); })) return;
        var d = f.querySelector('[type=submit]'); d.disabled = true;
        api('/baslik', { yontem: 'POST', govde: govde }).then(function (j) {
          yaz('fr-taslak-yeni', null); iz('forum_baslik', g.kategori);
          git('?b=' + j.baslik.id);
        }, function (h) { hata(h.message); d.disabled = false; });
      };
    }

    /* ----- Sohbet odaları ----- */
    function odaSatiri(b) {
      var yeniN = okunmamis(b), benimDuzey = b.duzey && b.duzey === duzeyim();
      return '<a class="fr-oda-satir' + (b.id === seciliOda ? ' fr-secili' : '') + (yeniN ? ' fr-okunmamis' : '') + '" data-ic href="?oda=' + b.id + '"' + (b.id === seciliOda ? ' aria-current="page"' : '') + '>'
        + '<span class="fr-av fr-av-oda" aria-hidden="true">' + ikon(SOHBET) + '</span>'
        + '<span class="fr-satir-ic"><span class="fr-oda-ust"><b class="fr-satir-bas">' + esc(b.baslik) + '</b>' + (benimDuzey ? '<span class="fr-et fr-et-sen">senin odan</span>' : '') + '<time>' + zaman(b.son_hareket || b.olusma) + '</time></span>'
        + '<span class="fr-oda-alt"><span class="fr-oda-ozet">' + esc(b.yanit_sayisi ? sayi(b.yanit_sayisi) + ' mesaj' : 'Henüz mesaj yok') + '</span>'
        + (yeniN ? '<span class="fr-oda-sayi" aria-label="' + yeniN + ' okunmamış">' + sayi(yeniN) + '</span>' : '') + '</span></span></a>';
    }
    function odaListesi(hedef) {
      var dz = duzeyim(), sorulmadi = !oku('fr-duzey') && !dz;
      hedef.innerHTML = (sorulmadi ? '<div class="fr-duzey-sor"><span>Hangi sınava hazırlanıyorsun? Odanı öne alalım.</span><div>' + DUZEYLER.slice(0, 4).map(function (d) { return '<button type="button" class="fr-cip" data-duzey-sec="' + d.kod + '">' + d.ad + '</button>'; }).join('')
          + '<button type="button" class="fr-eylem" data-duzey-sec="yok">Geç</button></div></div>' : '')
        + '<div class="fr-odalar"><p class="fr-yukleniyor">Yükleniyor…</p></div>'
        + '<p class="fr-oda-bilgi">Odalarda konuşulanlar akıp gider. Kalıcı cevap istediğin soruları <a class="yazi-link" data-ic href="?yeni=1">Soru-Cevap</a> bölümüne sor.</p>';
      var kap = hedef.querySelector('.fr-odalar');
      api('/basliklar?kategori=oda').then(function (j) {
        var o = (j.basliklar || []).slice();
        o.sort(function (a, b) { return ((b.duzey && b.duzey === dz) ? 1 : 0) - ((a.duzey && a.duzey === dz) ? 1 : 0) || (b.son_hareket - a.son_hareket); });
        kap.innerHTML = o.length ? o.map(odaSatiri).join('') : '<p class="fr-bos">Odalar yakında açılacak.</p>';
        var top = o.reduce(function (a, b) { return a + okunmamis(b); }, 0), s = kok_.querySelector('[data-oda-sayi]');
        if (s) { s.textContent = top ? sayi(top) : ''; s.hidden = !top; }
      }, function (h) { kap.innerHTML = '<p class="fr-bos">' + esc(h.message) + '</p>'; });
    }
    function sohbetOdasi(id, hedef) {
      hedef.innerHTML = '<div class="fr-oda"><header class="fr-oda-bas"><a class="fr-geri" data-ic href="?bolum=sohbet" aria-label="Odalara dön">' + ikon('M15 6l-6 6 6 6') + '</a>'
        + '<span class="fr-av fr-av-oda" aria-hidden="true">' + ikon(SOHBET) + '</span><div class="fr-oda-bas-ic"><h2 class="fr-oda-adi">Yükleniyor…</h2><p class="fr-ust-bilgi"></p></div><span data-takip-yer></span></header>'
        + '<div class="fr-oda-akis"><p class="fr-oda-not" hidden></p><button type="button" class="fr-eylem fr-eskiler" hidden>Daha eski mesajlar</button><div class="fr-liste" data-liste aria-live="polite"></div></div>'
        + yaziciHtml('oda-' + id, 'Mesaj yaz…', null, 'sohbet') + '</div>';
      var kap = hedef.querySelector('.fr-oda'), sc = hedef.closest('.fr-sh-oda'), b = null, mesajlar = [], dahaEski = false;
      var listeKap = kap.querySelector('[data-liste]'), eskiDugme = kap.querySelector('.fr-eskiler');
      function cizMesajlar(yeniden) {
        listeKap.innerHTML = mesajlar.length ? sohbetHtml(mesajlar, { yeniden: yeniden }) : '<p class="fr-sessiz">Odada henüz kimse yazmadı. Selam ver, sohbeti sen başlat.</p>';
        eskiDugme.hidden = !dahaEski;
      }
      function yukle(sessiz) {
        if (sessiz === true && b) {
          var son = mesajlar.length ? mesajlar[mesajlar.length - 1].id : 0, altta = enAltta(sc);
          return api('/baslik/' + id + '/yeni?sonra=' + son).then(function (j) {
            var y = (j.yanitlar || []).filter(function (m) { return !mesajlar.some(function (x) { return x.id === m.id; }); });
            if (j.yanit_sayisi != null) b.yanit_sayisi = j.yanit_sayisi;
            if (!y.length) return;
            mesajlar = mesajlar.concat(y); cizMesajlar(son); gorulduIsaretle(id, b.yanit_sayisi);
            if (altta) enAltaIn(sc); else bildir('Yeni mesaj');
          }, function () {});
        }
        return api('/baslik/' + id).then(function (j) {
          if (j.baslik.kategori !== 'oda') { history.replaceState(null, '', '?b=' + id + location.hash); ciz(); return; }
          b = j.baslik; mesajlar = j.yanitlar || []; dahaEski = !!j.daha_eski;
          document.title = b.baslik + ' — Sohbet — KPSS Tercihi';
          kap.querySelector('.fr-oda-adi').textContent = b.baslik;
          kap.querySelector('.fr-ust-bilgi').innerHTML = parcalar(['Sohbet odası', duzeyAd(b.duzey), sayi(b.yanit_sayisi) + ' mesaj']);
          var not_ = kap.querySelector('.fr-oda-not'); if (b.govde) { not_.textContent = b.govde; not_.hidden = false; }
          kap.querySelector('[data-takip-yer]').innerHTML = takipDugmesi(j.takip, 'oda');
          cizMesajlar(); gorulduIsaretle(id, b.yanit_sayisi);
          var sat = icerik.querySelector('.fr-oda-satir[href="?oda=' + id + '"]');
          if (sat) { sat.classList.remove('fr-okunmamis'); var c = sat.querySelector('.fr-oda-sayi'); if (c) c.remove(); }
          if (location.hash && document.getElementById(location.hash.slice(1))) document.getElementById(location.hash.slice(1)).scrollIntoView({ block: 'center' });
          else enAltaIn(sc);
        }, function (h) { kap.innerHTML = '<p class="fr-bos">' + (h.durum === 404 ? 'Bu oda bulunamadı. <a class="yazi-link" data-ic href="?bolum=sohbet">Odalara dön</a>' : esc(h.message)) + '</p>'; });
      }
      eskiDugme.onclick = function () {
        if (!mesajlar.length) return;
        eskiDugme.disabled = true;
        var yukseklik = sc ? sc.scrollHeight : document.documentElement.scrollHeight;
        api('/baslik/' + id + '?once=' + mesajlar[0].id).then(function (j) {
          mesajlar = (j.yanitlar || []).concat(mesajlar); dahaEski = !!j.daha_eski; cizMesajlar();
          if (sc) sc.scrollTop += sc.scrollHeight - yukseklik; else window.scrollBy(0, document.documentElement.scrollHeight - yukseklik);
        }, function (h) { bildir(h.message); }).then(function () { eskiDugme.disabled = false; });
      };
      yaziciBagla(kap, 'oda-' + id, function (g, ust) {
        var govde = { govde: g }; if (ust) govde.ust_id = ust;
        return api('/baslik/' + id + '/yanit', { yontem: 'POST', govde: govde }).then(function () { iz('forum_yanit', 'oda'); return yukle(true); }).then(function () { enAltaIn(sc); });
      });
      eylemleriBagla(kap, function () { return mesajlar; }, function () { cizMesajlar(); });
      yenileyiciler = [function () { return yukle(); }];
      durdur = canliTut(yukle, 20);
      yukle();
    }


    /* ----- Mesajlar (özel) ----- */
    // Bire bir yazışma: yalnız giriş yapmış üyeler; alıcı kapattıysa ya da engellendiyse gönderilemez (kurallar sunucuda).
    function mesajGirisIste(hedef) {
      hedef.innerHTML = '<div class="fr-dm-bos">' + ikon(ZARF) + '<b>Özel mesajlar</b><p class="fr-not">Üyelerle bire bir yazışmak için giriş yap. İstemediğin kişiyi engelleyebilir, mesajları tamamen kapatabilirsin.</p><button type="button" class="btn btn-ana" data-giris>Giriş yap</button></div>';
    }
    function mesajListesi(hedef) {
      if (!oturum()) return mesajGirisIste(hedef);
      hedef.innerHTML = '<div class="fr-dm-ust"><b>Mesajlar</b><span class="fr-not" data-dm-durum></span></div><div class="fr-dm-liste"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = hedef.querySelector('.fr-dm-liste'), u = uye();
      hedef.querySelector('[data-dm-durum]').textContent = u && kapali(u.dm_acik) ? 'Özel mesajların kapalı' : '';
      dmListeDoldur(kap, false);
      listeDurdur = canliTut(function () { dmListeYenile(); }, 60);   // yeni bir kişi yazarsa konuşma listede kendiliğinden belirir
    }
    // Konuşma listesini (sol panel) yeniden çeker. İlk mesaj gönderilince ya da yeni konuşma gelince liste güncellenir.
    function dmListeDoldur(kap, sessiz) {
      return api('/ozel').then(function (j) {
        var l = j.konusmalar || [];
        ozelSayisiGoster(j.toplam_okunmamis || 0);
        kap.innerHTML = l.length ? l.map(function (k) {
          return '<a class="fr-dm-satir' + (k.okunmamis ? ' fr-okunmamis' : '') + (k.rumuz === seciliKisi ? ' fr-secili' : '') + '" data-ic href="?mesaj=' + encodeURIComponent(k.rumuz) + '">' + avatar(k)
            + '<span class="fr-satir-ic"><span class="fr-oda-ust"><b class="fr-satir-bas">' + esc(k.rumuz) + '</b><time>' + zaman(k.son.olusma) + '</time></span>'
            + '<span class="fr-oda-alt"><span class="fr-oda-ozet">' + (k.son.benden ? 'Sen: ' : '') + esc(k.son.govde) + '</span>' + (k.okunmamis ? '<span class="fr-oda-sayi">' + sayi(k.okunmamis) + '</span>' : '') + '</span></span></a>';
        }).join('') : '<p class="fr-bos">Henüz özel mesajın yok. Bir üyenin adına dokunup "Mesaj gönder" diyebilirsin.</p>';
      }, function (h) { if (!sessiz) kap.innerHTML = '<p class="fr-bos">' + esc(h.message) + '</p>'; });
    }
    function dmListeYenile() {
      if (!oturum()) return;
      var kap = icerik.querySelector('.fr-dm-liste');   // dar ekranda açık konuşmayla birlikte liste yoktur
      if (kap) dmListeDoldur(kap, true);
    }
    function ozelKonusma(rumuz, hedef) {
      if (!oturum()) return mesajGirisIste(hedef);
      hedef.innerHTML = '<div class="fr-oda fr-dm"><header class="fr-oda-bas"><a class="fr-geri" data-ic href="?bolum=mesaj" aria-label="Mesajlara dön">' + ikon('M15 6l-6 6 6 6') + '</a>'
        + avatar({ rumuz: rumuz, rol: 'uye' }) + '<div class="fr-oda-bas-ic"><button type="button" class="fr-ad fr-oda-adi" data-uye="' + esc(rumuz) + '">' + esc(rumuz) + '</button><p class="fr-ust-bilgi">Yalnız ikiniz görürsünüz</p></div>'
        + '<details class="fr-dm-menu"><summary aria-label="Seçenekler">' + ikon('M12 6h.01M12 12h.01M12 18h.01') + '</summary><div><button type="button" class="fr-eylem" data-dm-engel></button><button type="button" class="fr-eylem fr-sik" data-dm-sikayet>Bildir ve engelle</button></div></details></header>'
        + '<div class="fr-oda-akis"><button type="button" class="fr-eylem fr-eskiler" hidden>Daha eski mesajlar</button><div class="fr-liste" data-liste aria-live="polite"></div></div>'
        + '<div data-dm-yazici></div></div>';
      var kap = hedef.querySelector('.fr-dm'), sc = hedef.closest('.fr-sh-oda'), mesajlar = [], dahaEski = false, durum = {};
      var listeKap = kap.querySelector('[data-liste]'), eskiDugme = kap.querySelector('.fr-eskiler'), yerYazici = kap.querySelector('[data-dm-yazici]');
      function dmHtml() {
        var gun = '', h = '';
        mesajlar.forEach(function (m) {
          var g = gunAdi(m.olusma);
          if (g !== gun) { h += '<div class="fr-gun" role="separator"><span>' + esc(g) + '</span></div>'; gun = g; }
          h += '<article class="fr-yanit' + (m.benden ? ' fr-benim' : '') + '" id="dm' + m.id + '"><div class="fr-yanit-ic"><div class="fr-govde">' + metin(m.govde)
            + '<span class="fr-saat"><time>' + saat(m.olusma) + '</time></span></div>' + (m.benden ? '<footer><button type="button" class="fr-eylem fr-sik" data-dm-sil="' + m.id + '">Sil</button></footer>' : '') + '</div></article>';
        });
        return h;
      }
      function ciz_() {
        listeKap.innerHTML = mesajlar.length ? dmHtml() : '<p class="fr-sessiz">' + (durum.engelledim ? 'Bu üyeyi engelledin.' : 'İlk mesajı sen yaz. Saygılı ol; rahatsız edici mesajlar bildirilebilir.') + '</p>';
        eskiDugme.hidden = !dahaEski;
        kap.querySelector('[data-dm-engel]').textContent = durum.engelledim ? 'Engeli kaldır' : 'Engelle';
        var kapali = durum.engelledim || durum.engellendim || (durum.uye && durum.uye.dm_acik === false);
        var neden = durum.engelledim ? 'Bu üyeyi engelledin; yazmak için engeli kaldır.' : durum.engellendim ? 'Bu üyeye mesaj gönderemezsin.' : 'Bu üye özel mesaj almıyor.';
        if (kapali) yerYazici.innerHTML = '<p class="fr-dm-kapali">' + esc(neden) + '</p>';
        else if (!yerYazici.querySelector('.fr-yazici')) {
          yerYazici.innerHTML = yaziciHtml('dm-' + rumuz, 'Mesaj yaz…', null, 'sohbet');
          yaziciBagla(kap, 'dm-' + rumuz, function (g) {
            return api('/ozel/' + encodeURIComponent(rumuz), { yontem: 'POST', govde: { govde: g } }).then(function () { iz('forum_ozel_mesaj'); return yukle(true); }).then(function () { enAltaIn(sc); dmListeYenile(); });
          });
        }
      }
      function yukle(sessiz) {
        if (sessiz === true && mesajlar.length) {
          var son = mesajlar[mesajlar.length - 1].id, altta = enAltta(sc);
          return api('/ozel/' + encodeURIComponent(rumuz) + '/yeni?sonra=' + son).then(function (j) {
            var y = (j.mesajlar || []).filter(function (m) { return !mesajlar.some(function (x) { return x.id === m.id; }); });
            if (!y.length) return;
            mesajlar = mesajlar.concat(y); ciz_(); if (altta) enAltaIn(sc); dmListeYenile();
          }, function () {});
        }
        return api('/ozel/' + encodeURIComponent(rumuz)).then(function (j) {
          durum = j; mesajlar = j.mesajlar || []; dahaEski = !!j.daha_eski;
          document.title = rumuz + ' — Mesajlar — KPSS Tercihi';
          ciz_(); enAltaIn(sc);
          var sat = icerik.querySelector('.fr-dm-satir[href="?mesaj=' + encodeURIComponent(rumuz) + '"]');
          if (sat) { sat.classList.remove('fr-okunmamis'); var c = sat.querySelector('.fr-oda-sayi'); if (c) c.remove(); }
          benYenile();
        }, function (h) { kap.innerHTML = '<p class="fr-bos">' + (h.durum === 404 ? 'Bu üye bulunamadı. <a class="yazi-link" data-ic href="?bolum=mesaj">Mesajlara dön</a>' : esc(h.message)) + '</p>'; });
      }
      eskiDugme.onclick = function () {
        eskiDugme.disabled = true;
        var yk = sc ? sc.scrollHeight : document.documentElement.scrollHeight;
        api('/ozel/' + encodeURIComponent(rumuz) + '?once=' + mesajlar[0].id).then(function (j) {
          mesajlar = (j.mesajlar || []).concat(mesajlar); dahaEski = !!j.daha_eski; ciz_();
          if (sc) sc.scrollTop += sc.scrollHeight - yk; else window.scrollBy(0, document.documentElement.scrollHeight - yk);
        }, function (h) { bildir(h.message); }).then(function () { eskiDugme.disabled = false; });
      };
      kap.addEventListener('click', function (e) {
        var en = e.target.closest('[data-dm-engel]'), sk = e.target.closest('[data-dm-sikayet]'), sl = e.target.closest('[data-dm-sil]');
        if (en) {
          var yeniDurum = !durum.engelledim;
          if (yeniDurum && !confirm(rumuz + ' engellensin mi? Sana mesaj gönderemez.')) return;
          api('/ozel/' + encodeURIComponent(rumuz) + '/engelle', { yontem: 'POST', govde: { engel: yeniDurum } }).then(function (j) {
            durum.engelledim = !!j.engelledim; yerYazici.innerHTML = ''; ciz_(); bildir(durum.engelledim ? 'Engellendi' : 'Engel kaldırıldı');
            var m = kap.querySelector('.fr-dm-menu'); if (m) m.open = false;
          }, function (h) { bildir(h.message); });
        } else if (sk) {
          if (!confirm('Bu konuşmayı yöneticilere bildirmek ve ' + rumuz + ' kişisini engellemek istiyor musun?')) return;
          var sonGelen = mesajlar.filter(function (m) { return !m.benden; }).pop();
          api('/ozel/' + encodeURIComponent(rumuz) + '/sikayet', { yontem: 'POST', govde: sonGelen ? { mesaj_id: sonGelen.id } : {} }).then(function () {
            durum.engelledim = true; yerYazici.innerHTML = ''; ciz_(); bildir('Bildirildi ve engellendi. Teşekkürler.');
          }, function (h) { bildir(h.message); });
        } else if (sl) {
          if (!confirm('Mesajın silinsin mi?')) return;
          var id = +sl.getAttribute('data-dm-sil');
          api('/ozel/mesaj/' + id, { yontem: 'DELETE' }).then(function () { mesajlar = mesajlar.filter(function (m) { return m.id !== id; }); ciz_(); }, function (h) { bildir(h.message); });
        }
      });
      yenileyiciler = [function () { return yukle(); }];
      durdur = canliTut(yukle, 20);
      yukle();
    }

    function ciz() {
      if (durdur) { durdur(); durdur = null; }
      if (listeDurdur) { listeDurdur(); listeDurdur = null; }
      var q = new URLSearchParams(location.search);
      document.title = 'Forum — KPSS Tercihi';
      yenileyiciler = [ciz];
      seciliOda = +q.get('oda') || 0; seciliKisi = q.get('mesaj') || '';
      var soruId = +q.get('b') || 0, bolum = seciliKisi || q.get('bolum') === 'mesaj' ? 'mesaj' : seciliOda || q.get('bolum') === 'sohbet' ? 'sohbet' : 'soru';
      kok_.querySelectorAll('[data-bolum]').forEach(function (a) { var s = a.getAttribute('data-bolum') === bolum; a.classList.toggle('fr-aktif', s); if (s) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
      kok_.setAttribute('data-bolum', bolum);
      document.body.classList.toggle('fr-konusmada', !!(seciliOda || seciliKisi) && !GENIS.matches);
      araclarCiz(); benYenile();
      if (bolum === 'mesaj') {   // özel mesajlar: sohbet gibi iki panel, mercan vurgulu
        icerik.className = 'fr-icerik fr-chat fr-mesajlar';
        if (GENIS.matches) {
          icerik.innerHTML = '<div class="fr-sh"><section class="fr-sh-liste" aria-label="Konuşmalar"></section><section class="fr-sh-oda" aria-label="Konuşma"></section></div>';
          var LM = icerik.querySelector('.fr-sh-liste'), OM = icerik.querySelector('.fr-sh-oda');
          mesajListesi(LM);
          if (seciliKisi) ozelKonusma(seciliKisi, OM);
          else OM.innerHTML = '<div class="fr-sh-bos">' + ikon(ZARF) + '<b>Bir konuşma seç</b><p class="fr-not">Yeni bir konuşma başlatmak için forumda bir üyenin adına dokun.</p></div>';
        } else if (seciliKisi) ozelKonusma(seciliKisi, icerik);
        else mesajListesi(icerik);
        return;
      }
      if (bolum === 'soru') {
        icerik.className = 'fr-icerik fr-qa';
        if (soruId) soruSayfasi(soruId);
        else if (q.get('yeni')) yeni(q.get('k'));
        else soruListesi({ k: q.get('k') || '', bekleyen: q.get('bekleyen') === '1', takip: q.get('takip') === '1', q: q.get('q') || '' });
        return;
      }
      icerik.className = 'fr-icerik fr-chat';
      if (GENIS.matches) {   // geniş ekran: solda odalar, sağda açık oda
        var L = icerik.querySelector('.fr-sh-liste[aria-label="Sohbet odaları"]'), O = icerik.querySelector('.fr-sh-oda');
        if (!L) {
          icerik.innerHTML = '<div class="fr-sh"><section class="fr-sh-liste" aria-label="Sohbet odaları"></section><section class="fr-sh-oda" aria-label="Oda"></section></div>';
          L = icerik.querySelector('.fr-sh-liste'); O = icerik.querySelector('.fr-sh-oda');
        }
        if (!L.hasAttribute('data-p')) { L.setAttribute('data-p', '1'); odaListesi(L); }
        else L.querySelectorAll('.fr-oda-satir').forEach(function (a) { var s = a.getAttribute('href') === '?oda=' + seciliOda; a.classList.toggle('fr-secili', s); if (s) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
        if (seciliOda) sohbetOdasi(seciliOda, O);
        else O.innerHTML = '<div class="fr-sh-bos">' + ikon(SOHBET) + '<b>Bir oda seç</b><p class="fr-not">Odalar anlık sohbet içindir. Kalıcı cevap istediğin sorular için <a class="yazi-link" data-ic href="?">Soru-Cevap</a>.</p></div>';
        return;
      }
      if (seciliOda) sohbetOdasi(seciliOda, icerik);
      else odaListesi(icerik);
    }
    if (GENIS.addEventListener) GENIS.addEventListener('change', function () { icerik.innerHTML = ''; ciz(); });
    kok_.addEventListener('change', function (e) {
      var c = e.target.closest('[data-ayar]');
      if (!c) return;
      var ad = c.getAttribute('data-ayar'), g = {}; g[ad] = c.checked;
      api('/ben/ayar', { yontem: 'POST', govde: g }).then(function (j) {
        var u = uye(); if (u) { u[ad] = c.checked ? 1 : 0; yaz('fr-uye', Object.assign(u, j.uye || {})); }
        bildir(ad === 'dm_acik' ? (c.checked ? 'Özel mesajlar açık' : 'Özel mesajlar kapalı; kimse sana yeni mesaj gönderemez') : (c.checked ? 'Telegram bildirimleri açık' : 'Telegram bildirimleri kapalı'));
      }, function (h) { c.checked = !c.checked; bildir(h.message); });
    });
    ciz();
  }

  /* ---------- ana sayfa: konuşulan ilanlara küçük mesaj rozeti ---------- */
  function listeRozetleri() {
    var bekleyen = {}, zamanlayici = null, bilinen = {};
    function tara() {
      document.querySelectorAll('a[data-a="satir_tikla"][data-a-h]:not([data-fr])').forEach(function (a) {
        a.setAttribute('data-fr', '1');
        var k = a.getAttribute('data-a-h');
        if (!/^([0-9a-f-]{36}|(sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})$/.test(k)) return;
        (bekleyen[k] = bekleyen[k] || []).push(a);
      });
      if (!zamanlayici && Object.keys(bekleyen).length) zamanlayici = setTimeout(getir, 400);
    }
    function getir() {
      zamanlayici = null;
      var parti = bekleyen; bekleyen = {};
      var idler = Object.keys(parti).filter(function (k) { return !bilinen[k]; }).slice(0, 100);
      if (!idler.length) return;
      idler.forEach(function (k) { bilinen[k] = 1; });
      api('/ozet?ilanlar=' + idler.join(',')).then(function (o) {
        idler.forEach(function (k) {
          var s = o[k];
          if (!s || !s.yanit) return;
          (parti[k] || []).forEach(function (a) {
            a.parentNode.insertAdjacentHTML('beforeend', '<a class="fr-liste-rozet" href="ilan/' + encodeURIComponent(k) + '/#tartisma" title="İlan hakkındaki sorular">' + ikon(SOHBET) + sayi(s.yanit) + '</a>');
          });
        });
      }, function () {});
    }
    tara();
    new MutationObserver(tara).observe(document.body, { childList: true, subtree: true });
  }

  var yenileyiciler = [];
  function yenile() { yenileyiciler.forEach(function (f) { try { f(); } catch (e) {} }); }
  function basla() {
    var t = document.getElementById('tartisma');
    if (t && t.getAttribute('data-ilan')) ilanBolumu(t);
    var f = document.getElementById('forum');
    if (f) forumSayfasi(f);
    if (!t && !f && !window.kitForumTembel) listeRozetleri();   // hesap.js'in tembel yüklediği sayfada yalnız hesap penceresi çalışır
    benYenile();
    if (!f) bildirimleriYokla();   // forum sayfası kendi yoklar
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', basla); else basla();
})();
