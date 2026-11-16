/* KPSS Tercihi: katiplik verisini hesapla eşitler (Kasım 2026). Yalnız /katiplik/ sayfalarında ve giriş yapılmışsa hesap.js tarafından yüklenir.
   Eşitlenen yerel anahtarlar: kit-katip (geçmiş, hatalar, rozetler, günlük sonuçlar, yol), kit-katip-ders, kit-katip-oyun, kit-katip-antrenman.
   Gönderilmez: yazılan metin, takma ad, özel metin, tuş istatistikleri. Sunucuya en çok 32 KB gider; yerelde dar tutulur
   (geçmiş son 200, hatalar ilk 100, günlük son 120 gün). Değişiklikler 3 sn sakinlikten sonra gönderilir, değişmediyse hiçbir şey yazılmaz.
   "kit-katip-uye": verinin hangi hesapla eşlendiği (çıkışta yalnız eşleşen veri silinir), "kit-katip-kirli": gönderilmemiş değişiklik var.
   Birleştirme kuralı (girişte): geçmiş zaman damgasına göre birleşir, en iyi değerlerin büyüğü kalır, rozetler birleşir, günlük sonuçlar
   günden güne (net büyük olan) birleşir, yolda daha yeni değişiklik (yol.g) kazanır. Birleştirme saf işlevdir, test edilir. */
(function () {
  'use strict';
  var ANAHTAR = { k: 'kit-katip', d: 'kit-katip-ders', o: 'kit-katip-oyun', a: 'kit-katip-antrenman' };
  var GECMIS = 200, HATA = 100, GUN = 120, ANT_GECMIS = 30, BAYT_SINIRI = 30000;

  function obje(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
  function say(v) { return typeof v === 'number' && isFinite(v) ? v : 0; }
  function tekrarsizGecmis(liste, en_cok) {
    var goru = Object.create(null), c = [];
    (Array.isArray(liste) ? liste : []).forEach(function (x) {
      if (!x || typeof x !== 'object' || typeof x.t !== 'number') return;
      var a = x.t + ':' + x.m;
      if (goru[a]) return;
      goru[a] = 1; c.push(x);
    });
    c.sort(function (a, b) { return b.t - a.t; });
    return c.slice(0, en_cok);
  }
  function enCok(a, b) { return Math.max(say(a), say(b)); }
  function yolBirlestir(a, b) {
    a = obje(a); b = obje(b);
    var ga = say(a.g), gb = say(b.g);
    var kazanan = gb >= ga ? b : a;   // eşitse yerel (b) kalır
    return { tarih: typeof kazanan.tarih === 'string' ? kazanan.tarih : '', hedef: say(kazanan.hedef) || 90, g: Math.max(ga, gb) };
  }
  function hatalariKirp(h) {
    var anahtarlar = Object.keys(obje(h)).filter(function (w) { return say(h[w]) > 0; });
    anahtarlar.sort(function (x, y) { return h[y] - h[x]; });
    var c = {};
    anahtarlar.slice(0, HATA).forEach(function (w) { c[w] = h[w]; });
    return c;
  }
  function gunlukBirlestir(a, b) {
    a = obje(a); b = obje(b);
    var c = {};
    Object.keys(a).concat(Object.keys(b)).forEach(function (g) {
      var x = a[g], y = b[g];
      c[g] = !x ? y : !y ? x : say(y.net) >= say(x.net) ? y : x;
    });
    var gunler = Object.keys(c).sort().slice(-GUN), s = {};
    gunler.forEach(function (g) { s[g] = c[g]; });
    return s;
  }
  function dersBirlestir(a, b) {
    a = obje(a); b = obje(b);
    var s = {};
    ['Q', 'F'].forEach(function (d) {
      var x = obje(a[d]), y = obje(b[d]), c = {};
      Object.keys(x).concat(Object.keys(y)).forEach(function (i) {
        var p = x[i], q = y[i];
        c[i] = !p ? q : !q ? p : (say(q.y) > say(p.y) || (say(q.y) === say(p.y) && say(q.t) >= say(p.t))) ? q : p;
      });
      if (Object.keys(c).length) s[d] = c;
    });
    return s;
  }
  function rekorBirlestir(a, b) {
    a = obje(a); b = obje(b);
    var c = {};
    Object.keys(a).concat(Object.keys(b)).forEach(function (k) { c[k] = enCok(a[k], b[k]); });
    return c;
  }
  // a: sunucu, b: yerel; ikisi de { k, d, o, a } biçiminde.
  function birlestir(a, b) {
    a = obje(a); b = obje(b);
    var ak = obje(a.k), bk = obje(b.k), ao = obje(a.o), bo = obje(b.o), aa = obje(a.a), ba = obje(b.a);
    var roz = [], gor = Object.create(null);
    (Array.isArray(ak.rozetler) ? ak.rozetler : []).concat(Array.isArray(bk.rozetler) ? bk.rozetler : []).forEach(function (r) { if (typeof r === 'string' && !gor[r]) { gor[r] = 1; roz.push(r); } });
    var hatalar = {};
    Object.keys(obje(ak.hatalar)).concat(Object.keys(obje(bk.hatalar))).forEach(function (w) { hatalar[w] = enCok(obje(ak.hatalar)[w], obje(bk.hatalar)[w]); });
    return {
      v: 1,
      k: {
        gecmis: tekrarsizGecmis((Array.isArray(ak.gecmis) ? ak.gecmis : []).concat(Array.isArray(bk.gecmis) ? bk.gecmis : []), GECMIS),
        hatalar: hatalariKirp(hatalar), rozetler: roz.slice(0, 40), gunluk: gunlukBirlestir(ak.gunluk, bk.gunluk), yol: yolBirlestir(ak.yol, bk.yol),
        ayar: { klavye: obje(bk.ayar).klavye === 'F' || (!obje(bk.ayar).klavye && obje(ak.ayar).klavye === 'F') ? 'F' : 'Q' }
      },
      d: dersBirlestir(a.d, b.d),
      o: { dosya: enCok(ao.dosya, bo.dosya), hata: enCok(ao.hata, bo.hata) },
      a: { rekor: rekorBirlestir(aa.rekor, ba.rekor), gecmis: tekrarsizGecmis((Array.isArray(aa.gecmis) ? aa.gecmis : []).concat(Array.isArray(ba.gecmis) ? ba.gecmis : []), ANT_GECMIS) }
    };
  }
  // Sunucuya gidecek boyuta indirir (en eski geçmiş kayıtlarını düşer).
  function kirp(p) {
    var k = p.k;
    while (JSON.stringify(p).length > BAYT_SINIRI && k.gecmis.length > 20) k.gecmis.pop();
    return p;
  }
  function bos() { return birlestir({}, {}); }
  function bosMu(p) { return !p.k.gecmis.length && !Object.keys(p.k.gunluk).length && !Object.keys(p.d).length && !p.o.dosya && !p.o.hata && !p.a.gecmis.length && !Object.keys(p.a.rekor).length && !Object.keys(p.k.hatalar).length; }
  // Yerel depodan okunan ham nesnelerle yükleme biçimi: oku(anahtar) -> nesne ya da null
  function topla(oku) {
    var k = obje(oku(ANAHTAR.k)), d = obje(oku(ANAHTAR.d)), o = obje(oku(ANAHTAR.o)), a = obje(oku(ANAHTAR.a));
    return birlestir({}, { k: { gecmis: k.gecmis, hatalar: k.hatalar, rozetler: k.rozetler, gunluk: k.gunluk, yol: k.yol, ayar: k.ayar }, d: d, o: o, a: { rekor: a.rekor, gecmis: a.gecmis } });
  }
  // Birleşik veriyi yerel anahtarlara yazar; sunucuya gitmeyen alanlar (özel metin, aday adı, antrenman ayarı ...) korunur.
  function uygula(p, oku, yaz) {
    var k = obje(oku(ANAHTAR.k));
    k.gecmis = p.k.gecmis; k.hatalar = p.k.hatalar; k.rozetler = p.k.rozetler; k.gunluk = p.k.gunluk;
    k.yol = Object.assign({ tarih: '', hedef: 90 }, obje(k.yol), { tarih: p.k.yol.tarih, hedef: p.k.yol.hedef }); if (p.k.yol.g) k.yol.g = p.k.yol.g;
    k.ayar = Object.assign({}, obje(k.ayar), { klavye: p.k.ayar.klavye });
    yaz(ANAHTAR.k, k);
    yaz(ANAHTAR.d, p.d);
    yaz(ANAHTAR.o, p.o);
    var a = obje(oku(ANAHTAR.a));
    a.rekor = p.a.rekor; a.gecmis = p.a.gecmis;
    yaz(ANAHTAR.a, a);
  }
  var disari = { birlestir: birlestir, topla: topla, uygula: uygula, kirp: kirp, bos: bos, bosMu: bosMu, ANAHTAR: ANAHTAR };
  if (typeof module === 'object' && module && module.exports) module.exports = disari;
  if (typeof document === 'undefined') return;
  if (window.kitKatip) return;

  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  function oku(a) { try { var v = JSON.parse(localStorage.getItem(a)); return v == null ? null : v; } catch (e) { return null; } }
  function yaz(a, d) { try { if (d == null) localStorage.removeItem(a); else localStorage.setItem(a, JSON.stringify(d)); } catch (e) {} }
  function ham() { try { return ['k', 'd', 'o', 'a'].map(function (x) { return localStorage.getItem(ANAHTAR[x]) || ''; }).join('\u0001'); } catch (e) { return ''; } }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function api(yol, yontem, govde, jeton) {
    var h = { Authorization: 'Bearer ' + jeton };
    if (govde !== undefined) h['Content-Type'] = 'application/json';
    return fetch(API + yol, { method: yontem, headers: h, body: govde !== undefined ? JSON.stringify(govde) : undefined, keepalive: govde !== undefined && JSON.stringify(govde).length < 60000 })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) { var e = new Error(j.hata || 'hata'); e.durum = r.status; throw e; } return j; }); });
  }
  function gonder(jeton) {
    jeton = jeton || oku('fr-oturum');
    if (!jeton) return Promise.resolve();
    var once = ham(), p = kirp(topla(oku));
    return api('/ben/katip', 'POST', { katip: p }, jeton).then(function (j) {
      if (ham() === once) yaz('kit-katip-kirli', null);
      return j;
    });
  }

  var ben = oku('fr-uye'), jeton = oku('fr-oturum'), son = '', zamanlayici = 0, hazir = false;
  if (!ben || !ben.id || !jeton) return;

  function sonucNotu() {   // sonuç ekranı açıksa "profiline eklendi" notu
    ['sonuc', 'a-sonuc', 'o-sonuc'].forEach(function (id) {
      var e = document.getElementById(id);
      if (!e || e.hidden) return;
      var n = e.querySelector('.kt-profil-not');
      if (!n) { n = document.createElement('p'); n.className = 'kt-profil-not'; n.setAttribute('role', 'status'); e.insertBefore(n, e.firstChild); }
      var u = oku('fr-uye') || ben;
      n.innerHTML = (window.kitAvatar ? window.kitAvatar.html({ rumuz: u.rumuz, av: u.av, fs: u.fs, fu: u.fu }, 24) : '') + '<span><b>' + esc(u.rumuz) + '</b>, sonucun profiline eklendi.</span>';
    });
  }
  function rozet() {   // sayfa başlığının altında küçük hesap bilgisi
    var h = document.querySelector('main h1') || document.querySelector('h1');
    if (!h || document.querySelector('.kt-hesap')) return;
    var u = oku('fr-uye') || ben, p = document.createElement('p');
    p.className = 'kt-hesap';
    p.innerHTML = (window.kitAvatar ? window.kitAvatar.html({ rumuz: u.rumuz, av: u.av, fs: u.fs, fu: u.fu }, 24) : '') + '<span><b>' + esc(u.rumuz) + '</b> hesabına bağlı; sonuçların profiline eklenir.</span>';
    h.parentNode.insertBefore(p, h.nextSibling);
  }
  function degisim() {
    if (!hazir) return;
    var s = ham();
    if (s === son) return;
    son = s;
    yaz('kit-katip-kirli', 1);
    clearTimeout(zamanlayici);
    zamanlayici = setTimeout(function () {
      gonder().then(function () { sonucNotu(); }, function (h) { if (h && h.durum === 400) yaz('kit-katip-kirli', null); });
    }, 3000);
  }
  function baslat(sunucu) {
    var sahip = oku('kit-katip-uye'), yerel = topla(oku), sonuc;
    if (typeof sahip === 'number' && sahip !== ben.id) yerel = bos();   // başka üyeye ait veri sızmasın
    var sunucuVeri = sunucu ? birlestir(sunucu, {}) : bos();
    sonuc = birlestir(sunucuVeri, yerel);   // yerelde sonradan silinen geçmiş, sonraki değişiklikte (boş gönderim) hesaptan da silinir
    uygula(sonuc, oku, yaz);
    yaz('kit-katip-uye', ben.id);
    son = ham(); hazir = true;
    var fark = JSON.stringify(birlestir(sunucuVeri, {})) !== JSON.stringify(kirp(birlestir({}, sonuc)));
    if (fark || oku('kit-katip-kirli')) gonder().then(function () {}, function () { yaz('kit-katip-kirli', 1); });
    rozet();
    try { window.dispatchEvent(new Event('kit-katip-sunucudan')); } catch (e) {}
    setInterval(function () { if (!document.hidden) degisim(); }, 2000);
    document.addEventListener('visibilitychange', function () { if (document.hidden && oku('kit-katip-kirli')) { clearTimeout(zamanlayici); gonder().then(function () {}, function () {}); } });
    window.addEventListener('pagehide', function () { if (oku('kit-katip-kirli')) gonder().then(function () {}, function () {}); });
  }
  window.kitKatip = { gonder: gonder, birlestir: birlestir, topla: function () { return topla(oku); } };
  var yuk = window.kitAvatar ? window.kitAvatar.yukle() : Promise.resolve();
  // Sunucuya ulaşılamazsa eşleme yapılmaz (hesaptaki veri yerel veriyle ezilmesin); 30 sn sonra en çok 3 kez yeniden denenir.
  function ac(deneme) {
    api('/ben/katip', 'GET', undefined, oku('fr-oturum') || jeton).then(function (j) { return yuk.then(function () { baslat(j.katip); }); }, function (h) {
      if (h && h.durum === 401) return;
      if (deneme < 3) setTimeout(function () { ac(deneme + 1); }, 30000);
    });
  }
  ac(0);
})();
