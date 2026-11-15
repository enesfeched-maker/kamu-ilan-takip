/* KPSS Tercihi — forum (Kasım 2026, sade sürüm).
   - ilan sayfası #tartisma: başvuran sayısı + ilanla ilgili sorular;
   - /forum/ #forum: arama, konu seçimi, başlık listesi, başlık ve yeni başlık ekranı;
   - ana sayfa ilan listesi: konuşulan ilanlara küçük mesaj rozeti.
   İlke: ekranda bir anda az şey. Ayrıntılar (puan dağılımı, ek seçenekler) istenince açılır.
   Otomatik yanıt ve site hesabı her zaman etiketiyle görünür; sayılar gerçek veridir. */
(function () {
  'use strict';
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var BOT = 'kamuilanibot';
  var KATEGORILER = [
    { kod: 'ilan', ad: 'İlanlar' }, { kod: 'puan', ad: 'Puan ve tercih' }, { kod: 'kurum', ad: 'Kurum ve şehir' },
    { kod: 'mulakat', ad: 'Mülakat' }, { kod: 'haklar', ad: 'Haklar ve tayin' }, { kod: 'hazirlik', ad: 'Hazırlık' }, { kod: 'etkinlik', ad: 'Etkinlik' }
  ];
  var DUZEYLER = [{ kod: 'lisans', ad: 'Lisans' }, { kod: 'onlisans', ad: 'Önlisans' }, { kod: 'ortaogretim', ad: 'Ortaöğretim' }, { kod: 'ekpss', ad: 'EKPSS' }, { kod: 'agrubu', ad: 'A Grubu' }];
  var PUAN_TURLERI = ['P3', 'P93', 'P94', 'P10', 'P121'];
  var HIZLI_SORULAR = ['Son başvuru ne zaman?', 'Hangi bölümler başvurabilir?', 'Mülakat var mı?'];
  var SOHBET = 'M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20l1-4.3A7.5 7.5 0 1 1 20 12.5z';

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
  function cikis() { yaz('fr-oturum', null); yaz('fr-uye', null); yenile(); }

  function api(yol, secenek) {
    secenek = secenek || {};
    var h = {}, o = oturum();
    if (o) h.Authorization = 'Bearer ' + o;
    if (secenek.govde !== undefined) h['Content-Type'] = 'application/json';
    return fetch(API + yol, { method: secenek.yontem || 'GET', headers: h, body: secenek.govde !== undefined ? JSON.stringify(secenek.govde) : undefined })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (r.status === 401 && o) { yaz('fr-oturum', null); yaz('fr-uye', null); }
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
      h = h.replace(/(^|[\s(])@([A-Za-z0-9_.çğıöşüÇĞİÖŞÜ]{3,20})/g, '$1<b class="fr-anma">@$2</b>');
      return '<p>' + h.replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }
  function insanMi(k) { return k.rol !== 'asistan' && k.rol !== 'sistem'; }
  // Mesaj yanında yalnız ayırt edici etiket: otomatik yanıt / site hesabı / yönetici. Kurucu ve Yardımsever yalnız profilde.
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
  // Pano görünümü (Hallmark Paste-up, deneme): ?tasarim=pano açar, ?tasarim=klasik kapatır; seçim bu tarayıcıda hatırlanır.
  var TASARIM = (function () {
    var q = new URLSearchParams(location.search).get('tasarim');
    if (q) yaz('fr-tasarim', q === 'pano' || q === 'sohbet' ? q : null);
    return q || oku('fr-tasarim') || 'klasik';
  })();
  var PANO = TASARIM === 'pano', SOHBET = TASARIM === 'sohbet';
  if (SOHBET) {
    document.documentElement.classList.add('fr-sohbet');
    var sl = document.createElement('link'); sl.rel = 'stylesheet'; sl.href = kok() + 'forum-sohbet.css?v=1'; document.head.appendChild(sl);
  }
  if (PANO) {
    document.documentElement.classList.add('fr-pano');
    [['https://fonts.googleapis.com/css2?family=League+Gothic&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap'], [kok() + 'forum-pano.css?v=1']].forEach(function (h) {
      var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = h[0]; document.head.appendChild(l);
    });
  }
  function katAd(kod) { for (var i = 0; i < KATEGORILER.length; i++) if (KATEGORILER[i].kod === kod) return KATEGORILER[i].ad; return ''; }
  // Bilgi parçaları ayrı öğe olarak yan yana durur (aralık CSS'ten); orta nokta ile birleştirilmez.
  function parcalar(l) { return l.filter(function (x) { return x !== '' && x != null; }).map(function (x) { return '<span>' + esc(x) + '</span>'; }).join(''); }
  function duzeyAd(k) { for (var i = 0; i < DUZEYLER.length; i++) if (DUZEYLER[i].kod === k) return DUZEYLER[i].ad; return ''; }

  /* ---------- giriş ---------- */
  var girisSonrasi = null;
  function girisKutusu(baslik) {
    var eski = document.getElementById('fr-giris');
    if (eski) eski.remove();
    var kutu = el('<div class="fr-perde" id="fr-giris" role="dialog" aria-modal="true" aria-labelledby="fr-giris-bas"><div class="fr-kutu">'
      + '<button type="button" class="fr-kapat" aria-label="Kapat">×</button>'
      + '<h2 id="fr-giris-bas">' + esc(baslik || 'Giriş yap') + '</h2><p class="fr-not">Telegram ile girersin. Sitede yalnız rumuzun görünür.</p>'
      + '<div class="fr-giris-alan"></div><p class="fr-hata" role="alert" hidden></p></div></div>');
    document.body.appendChild(kutu);
    var alan = kutu.querySelector('.fr-giris-alan');
    function kapat() { kutu.remove(); document.removeEventListener('keydown', tus); }
    function tus(e) { if (e.key === 'Escape') kapat(); }
    document.addEventListener('keydown', tus);
    kutu.querySelector('.fr-kapat').onclick = kapat;
    kutu.onclick = function (e) { if (e.target === kutu) kapat(); };
    function hata(m) { var p = kutu.querySelector('.fr-hata'); p.textContent = m; p.hidden = !m; }
    function girdi(j) {
      if (j.yeni) return rumuzSor(j.gecici);
      yaz('fr-oturum', j.oturum); yaz('fr-uye', j.uye); kapat(); iz('forum_giris');
      var f = girisSonrasi; girisSonrasi = null;
      if (f) f(); else yenile();
    }
    function rumuzForm(ipucu, yol, govdeYap) {
      alan.innerHTML = '<form class="fr-form"><input id="fr-rumuz" maxlength="20" autocomplete="nickname" required placeholder="' + ipucu + '" aria-label="Rumuz">'
        + '<button class="btn btn-ana" type="submit">Devam</button></form>';
      var f = alan.querySelector('form'), g = f.querySelector('input');
      g.focus();
      f.onsubmit = function (e) {
        e.preventDefault(); hata('');
        api(yol, { yontem: 'POST', govde: govdeYap(g.value.trim()) }).then(girdi, function (h) { hata(h.message); });
      };
    }
    function rumuzSor(gecici) {
      kutu.querySelector('h2').textContent = 'Bir rumuz seç';
      kutu.querySelector('.fr-not').textContent = '3–20 karakter. Sonradan değişmez.';
      rumuzForm('ör. memuradayi35', '/giris/rumuz', function (r) { return { gecici: gecici, rumuz: r }; });
    }
    if (YEREL) rumuzForm('Deneme rumuzu (yalnız yerelde)', '/giris/deneme', function (r) { return { rumuz: r }; });
    else {
      window.frTelegram = function (k) { hata(''); api('/giris/telegram', { yontem: 'POST', govde: k }).then(girdi, function (h) { hata(h.message); }); };
      var s = document.createElement('script');
      s.async = true; s.src = 'https://telegram.org/js/telegram-widget.js?22';
      s.setAttribute('data-telegram-login', BOT); s.setAttribute('data-size', 'large'); s.setAttribute('data-radius', '10');
      s.setAttribute('data-onauth', 'frTelegram(user)'); s.setAttribute('data-request-access', 'write');
      alan.appendChild(s);
    }
  }
  function girisGerekli(baslik, sonra) { if (oturum()) return false; girisSonrasi = sonra || null; girisKutusu(baslik); return true; }

  /* ---------- mesajlar ---------- */
  function yanitHtml(y, cocuk, yeni) {
    var ben = y.benim || (uye() && uye().rumuz === y.rumuz);
    var eylem = '';
    if (!ben) eylem += '<button type="button" class="fr-eylem" data-faydali="' + y.id + '" aria-pressed="' + (y.oyladim ? 'true' : 'false') + '">Faydalı' + (y.faydali ? ' ' + sayi(y.faydali) : '') + '</button>';
    if (!cocuk) eylem += '<button type="button" class="fr-eylem" data-yanitla="' + y.id + '" data-rumuz="' + esc(y.rumuz) + '" data-rol="' + esc(y.rol) + '">Yanıtla</button>';
    if (insanMi(y) && !ben) eylem += '<button type="button" class="fr-eylem fr-sik" data-sikayet="' + y.id + '" title="Kurallara aykırı diye bildir">Bildir</button>';
    return '<article class="fr-yanit' + (cocuk ? ' fr-cocuk' : '') + (y.rol === 'asistan' ? ' fr-yanit-bot' : '') + (ben ? ' fr-benim' : '') + (yeni ? ' fr-yeni' : '') + '" id="y' + y.id + '">'
      + avatar(y) + '<div class="fr-yanit-ic"><header><b>' + esc(y.rumuz) + '</b>' + etiket(y) + '<time datetime="' + new Date(y.olusma * 1000).toISOString() + '">' + zaman(y.olusma) + '</time></header>'
      + '<div class="fr-govde">' + metin(y.govde) + '</div>' + (eylem ? '<footer>' + eylem + '</footer>' : '') + '</div></article>';
  }
  function yanitListesi(yanitlar, gorulen) {
    var koke = [], alt = {}, bilinen = {};
    yanitlar.forEach(function (y) { if (y.ust_id) (alt[y.ust_id] = alt[y.ust_id] || []).push(y); else koke.push(y); });
    koke.forEach(function (y) { bilinen[y.id] = 1; });
    Object.keys(alt).forEach(function (u) { if (!bilinen[u]) { koke = koke.concat(alt[u]); delete alt[u]; } });
    koke.sort(function (a, b) { return a.id - b.id; });
    function yeni(y) { return gorulen && y.id > gorulen; }
    return koke.map(function (y) { return yanitHtml(y, false, yeni(y)) + (alt[y.id] || []).map(function (x) { return yanitHtml(x, true, yeni(x)); }).join(''); }).join('');
  }
  function yaziciHtml(yer, ipucu, hizli) {
    return '<form class="fr-yazici" data-yer="' + yer + '">'
      + (hizli ? '<div class="fr-hizli">' + hizli.map(function (s) { return '<button type="button" class="fr-cip" data-hizli>' + esc(s) + '</button>'; }).join('') + '</div>' : '')
      + '<div class="fr-yanitlanan" hidden><span></span><button type="button" class="fr-eylem" data-iptal>Vazgeç</button></div>'
      + '<div class="fr-yazici-ic"><label class="sr-only" for="fr-metin-' + yer + '">Mesajın</label><textarea id="fr-metin-' + yer + '" rows="1" maxlength="2000" placeholder="' + esc(ipucu) + '"></textarea>'
      + '<button type="submit" class="fr-gonder" aria-label="Gönder">' + ikon('M5 12h13M13 6l6 6-6 6') + '</button></div>'
      + '<p class="fr-hata" role="alert" hidden></p></form>';
  }
  function yaziciBagla(kap, anahtar, gonder) {
    var f = kap.querySelector('.fr-yazici');
    if (!f) return;
    var ust = null, ta = f.querySelector('textarea'), etk = f.querySelector('.fr-yanitlanan'), taslakAd = 'fr-taslak-' + anahtar;
    ta.value = oku(taslakAd) || '';
    function boy() {
      ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight + 2, 200) + 'px'; ta.style.overflowY = ta.scrollHeight > 198 ? 'auto' : 'hidden';
      f.classList.toggle('fr-dolu', !!ta.value.trim());
      var h = f.querySelector('.fr-hizli'); if (h) h.hidden = !!ta.value.trim();
    }
    boy();
    ta.addEventListener('input', function () { yaz(taslakAd, ta.value || null); boy(); });
    function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
    f.querySelector('[data-iptal]').onclick = function () { ust = null; etk.hidden = true; };
    f.addEventListener('click', function (e) {
      var c = e.target.closest('[data-hizli]');
      if (!c) return;
      ta.value = c.textContent; yaz(taslakAd, ta.value); boy(); ta.focus(); iz('forum_hizli_soru');
    });
    kap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-yanitla]');
      if (!b) return;
      ust = +b.getAttribute('data-yanitla');
      etk.querySelector('span').textContent = b.getAttribute('data-rumuz') + ' kişisine yanıt';
      etk.hidden = false;
      var an = '@' + b.getAttribute('data-rumuz') + ' ';
      if (insanMi({ rol: b.getAttribute('data-rol') }) && ta.value.indexOf(an) !== 0) { ta.value = an + ta.value; boy(); }
      ta.focus();
    });
    ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) f.requestSubmit(); });
    f.onsubmit = function (e) {
      if (e && e.preventDefault) e.preventDefault();
      hata('');
      var g = ta.value.trim();
      if (g.length < 2) { ta.focus(); return; }
      if (girisGerekli('Göndermek için giriş yap', function () { yenile(); setTimeout(function () { var y = document.querySelector('.fr-yazici[data-yer="' + f.getAttribute('data-yer') + '"]'); if (y) y.requestSubmit(); }, 400); })) return;
      var d = f.querySelector('[type=submit]'); d.disabled = true;
      gonder(g, ust).then(function () { ta.value = ''; yaz(taslakAd, null); ust = null; etk.hidden = true; boy(); }, function (h) { hata(h.message); })
        .then(function () { d.disabled = false; });
    };
  }
  function eylemleriBagla(kap, sonra) {
    kap.addEventListener('click', function (e) {
      var f = e.target.closest('[data-faydali]'), s = e.target.closest('[data-sikayet]');
      if (f) {
        if (girisGerekli('Giriş yap')) return;
        api('/yanit/' + f.getAttribute('data-faydali') + '/faydali', { yontem: 'POST', govde: {} }).then(function (j) {
          f.setAttribute('aria-pressed', String(!!j.oyladim)); f.textContent = 'Faydalı' + (j.faydali ? ' ' + sayi(j.faydali) : '');
        }, function (h) { bildir(h.message); });
      } else if (s) {
        if (girisGerekli('Giriş yap')) return;
        if (!confirm('Bu mesajı bildirmek istiyor musun?')) return;
        api('/yanit/' + s.getAttribute('data-sikayet') + '/sikayet', { yontem: 'POST', govde: {} }).then(function () {
          s.textContent = 'Bildirildi'; s.disabled = true; if (sonra) sonra();
        }, function (h) { bildir(h.message); });
      }
    });
  }
  function canliTut(f) {   // sekme açıkken yeni mesajları kendiliğinden getirir (önbellekli okuma)
    var t = setInterval(function () { if (document.visibilityState === 'visible') f(true); }, 45000);
    return function () { clearInterval(t); };
  }

  /* ---------- ilan sayfası ---------- */
  function ilanBolumu(kap) {
    var ilan = kap.getAttribute('data-ilan'), ad = kap.getAttribute('data-ad') || 'Bu ilan', acik = kap.getAttribute('data-acik') === '1';
    var sonId = 0, baslikId = null, ilk = true;
    kap.innerHTML = '<div class="fr-ilan"><header class="fr-ilan-bas"><h2>Sorular</h2><span class="fr-not" data-ozet></span></header>'
      + '<div class="fr-basvuru"></div><div class="fr-liste"></div>'
      + yaziciHtml('ilan', 'Bu ilanla ilgili sorunu yaz…', HIZLI_SORULAR) + '</div>';
    var liste = kap.querySelector('.fr-liste'), bas = kap.querySelector('.fr-basvuru');

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
    function ciz(j, sessiz) {
      var y = j.yanitlar || [];
      var enBuyuk = y.reduce(function (a, x) { return Math.max(a, x.id); }, 0);
      if (sessiz && enBuyuk <= sonId) return;
      liste.innerHTML = yanitListesi(y, ilk ? 0 : sonId);
      if (sessiz) bildir('Yeni mesaj');
      sonId = enBuyuk; ilk = false;
      if (j.baslik && j.baslik.id) baslikId = j.baslik.id;
      var n = y.filter(insanMi).length;
      kap.querySelector('[data-ozet]').textContent = n ? sayi(n) + ' mesaj' : 'Henüz soru yok';
      ctaGuncelle(n);
      if (!sessiz) basvuruCiz(j.basvuru);
    }
    function yukle(sessiz) {
      var k = basvurularim()[ilan] ? '?kimlik=' + kimlik() : '';
      return api('/ilan/' + encodeURIComponent(ilan) + k).then(function (j) { ciz(j, sessiz === true); }, function () {
        if (sessiz !== true) kap.querySelector('[data-ozet]').textContent = 'Şu an yüklenemedi';
      });
    }
    function gonder(g, ust) {
      var istek = ust && baslikId
        ? api('/baslik/' + baslikId + '/yanit', { yontem: 'POST', govde: { govde: g, ust_id: ust } })
        : api('/ilan/' + encodeURIComponent(ilan) + '/yanit', { yontem: 'POST', govde: { govde: g, ilan_baslik: ad } });
      return istek.then(function () { iz('forum_yanit', 'ilan'); return yukle(); });
    }
    yaziciBagla(kap, 'ilan-' + ilan, gonder);
    eylemleriBagla(kap, yukle);
    yenileyiciler.push(yukle);
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
  function yuzenDugme(kap) {   // yalnız telefonda, konuşma ekranda değilken görünen küçük düğme
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

  /* ---------- forum sayfası ---------- */
  // Puan özeti: ilk mesajda düzey + puan varsa ÖSYM taban puanı verisinden tarayıcıda hesaplanır, tek kısa kutu.
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
  function forumSayfasi(kok_) {
    var durdur = null;
    function git(q) { history.pushState(null, '', q || location.pathname); ciz(); window.scrollTo(0, 0); }
    kok_.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-ic]');
      if (a && !e.metaKey && !e.ctrlKey) { e.preventDefault(); git(a.getAttribute('href')); return; }
      if (e.target.closest('[data-cikis]')) cikis();
      if (e.target.closest('[data-giris]')) girisKutusu();
      var p = e.target.closest('[data-paylas]');
      if (p) {
        var u = location.href.split('#')[0];
        if (navigator.share) navigator.share({ title: document.title, url: u }).catch(function () {});
        else { try { navigator.clipboard.writeText(u); bildir('Bağlantı kopyalandı'); } catch (x) {} }
      }
    });
    window.addEventListener('popstate', ciz);
    function uyeCubugu() {
      var u = uye();
      if (!u) return '<button type="button" class="fr-eylem" data-giris>Giriş yap</button>';
      return '<details class="fr-ben"><summary>' + esc(u.rumuz) + '</summary><div>'
        + (u.kurucu ? '<p>Kurucu üye</p>' : '') + (u.itibar ? '<p>' + sayi(u.itibar) + ' kez faydalı bulundu</p>' : '')
        + '<label><input type="checkbox" data-bildirim' + (u.bildirim === 0 ? '' : ' checked') + '> Yanıtları Telegram\'dan bildir</label>'
        + '<button type="button" class="fr-eylem" data-cikis>Çıkış</button></div></details>';
    }
    function satir(b) {
      var hedef = b.ilan_id && !SOHBET ? '../ilan/' + encodeURIComponent(b.ilan_id) + '/#tartisma' : '?b=' + b.id;
      if (SOHBET) {
        return '<a class="fr-satir fr-oda-satir' + (b.id === seciliOda ? ' fr-secili' : '') + '" data-ic href="' + hedef + '"' + (b.id === seciliOda ? ' aria-current="page"' : '') + '>' + avatar(b)
          + '<span class="fr-satir-ic"><span class="fr-oda-ust"><b class="fr-satir-bas">' + esc(b.baslik) + '</b><time>' + zaman(b.son_hareket || b.olusma) + '</time></span>'
          + '<span class="fr-oda-alt"><span class="fr-oda-ozet">' + esc(b.kisa || katAd(b.kategori)) + '</span>'
          + (b.yanit_sayisi ? '<span class="fr-oda-sayi">' + sayi(b.yanit_sayisi) + '</span>' : b.sabit ? '' : '<span class="fr-oda-bekliyor">yanıtsız</span>') + '</span></span></a>';
      }
      var alt = parcalar([katAd(b.kategori), duzeyAd(b.duzey), b.anket ? 'Anket' : '', b.rumuz, zaman(b.son_hareket || b.olusma)]);
      return '<a class="fr-satir"' + (b.ilan_id ? '' : ' data-ic') + ' href="' + hedef + '"><span class="fr-satir-ic">'
        + '<b class="fr-satir-bas">' + (b.sabit ? '<span class="fr-sabit">Sabit</span> ' : '') + esc(b.baslik) + '</b><span class="fr-satir-alt">' + alt + '</span></span>'
        + '<span class="fr-yanit-sayi' + (b.yanit_sayisi || b.sabit ? '' : ' fr-sifir') + '">' + (b.yanit_sayisi ? '<b>' + sayi(b.yanit_sayisi) + '</b><small>yanıt</small>' : b.sabit ? '' : '<b>yanıtsız</b>') + '</span></a>';
    }
    function liste(p, hedef) {
      hedef = hedef || kok_;
      var secili = p.bekleyen ? 'bekleyen' : p.k;
      hedef.innerHTML = '<div class="fr-ust"><form class="fr-ara" role="search"><input type="search" maxlength="60" placeholder="Forumda ara" value="' + esc(p.q) + '" aria-label="Forumda ara"></form>'
        + '<a class="btn btn-ana" data-ic href="?yeni=1' + (p.k && p.k !== 'ilan' && p.k !== 'etkinlik' ? '&k=' + p.k : '') + '">Soru sor</a>' + uyeCubugu() + '</div>'
        + (p.q ? '<p class="fr-arama-bas"><span>“' + esc(p.q) + '” için sonuçlar</span><a class="yazi-link" data-ic href="?">Aramayı temizle</a></p>'
          : '<nav class="fr-sekmeler" aria-label="Konular"><a data-ic href="?"' + (!secili ? ' aria-current="page"' : '') + '>Tümü</a>'
            + '<a data-ic href="?bekleyen=1"' + (secili === 'bekleyen' ? ' aria-current="page"' : '') + '>Yanıtsız</a>'
            + KATEGORILER.map(function (c) { return '<a data-ic href="?k=' + c.kod + '"' + (secili === c.kod ? ' aria-current="page"' : '') + '>' + esc(c.ad) + '</a>'; }).join('') + '</nav>')
        + (PANO && !p.q && !p.bekleyen ? '<div class="fr-pano-not" hidden></div>' : '')
        + '<div class="fr-basliklar"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = hedef.querySelector('.fr-basliklar'), f = hedef.querySelector('.fr-ara');
      var not_ = hedef.querySelector('.fr-pano-not');
      if (not_) api('/durum').then(function (d) {   // panonun tek floresan kâğıdı: gerçek yanıtsız soru sayısı
        if (!d.bekleyen) return;
        not_.innerHTML = '<b>' + sayi(d.bekleyen) + ' soru cevap bekliyor</b><a class="btn" data-ic href="?bekleyen=1">Cevapla</a>';
        not_.hidden = false;
      }, function () {});
      f.onsubmit = function (e) { e.preventDefault(); var q = f.querySelector('input').value.trim(); if (q.length >= 2) { iz('forum_ara'); git('?q=' + encodeURIComponent(q)); } else if (!q) git('?'); };
      function getir(sayfa, ekle) {
        var yol = p.q ? '/ara?q=' + encodeURIComponent(p.q) : '/basliklar?kategori=' + encodeURIComponent(p.k || '') + '&sayfa=' + sayfa + (p.bekleyen ? '&bekleyen=1' : '');
        return api(yol).then(function (j) {
          var b = j.basliklar || [];
          var eski = kap.querySelector('.fr-daha'); if (eski) eski.remove();
          if (!ekle) kap.innerHTML = b.length ? '' : '<p class="fr-bos">' + (p.q ? 'Sonuç yok. <a class="yazi-link" data-ic href="?yeni=1">Sorunu sor</a>, bilen biri cevaplar.' : p.bekleyen ? 'Yanıtsız soru yok.' : 'Henüz başlık yok. <a class="yazi-link" data-ic href="?yeni=1">İlk soruyu sen sor</a>.') + '</p>';
          kap.insertAdjacentHTML('beforeend', b.map(satir).join(''));
          if (j.sonraki && !p.q) {
            var d = el('<button type="button" class="fr-eylem fr-daha">Daha fazla</button>');
            d.onclick = function () { d.disabled = true; getir(sayfa + 1, true); };
            kap.appendChild(d);
          }
        }, function (h) { kap.innerHTML = '<p class="fr-bos">' + esc(h.message) + '</p>'; });
      }
      getir(1);
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
    function baslik(id, hedef) {
      hedef = hedef || kok_;
      hedef.innerHTML = '<p class="fr-geri"><a class="yazi-link" data-ic href="?">Foruma dön</a></p><div class="fr-baslik"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = hedef.querySelector('.fr-baslik'), sonId = 0, ilk = true;
      function yukle(sessiz) {
        return api('/baslik/' + id).then(function (j) {
          var b = j.baslik, y = j.yanitlar || [];
          var enBuyuk = y.reduce(function (a, x) { return Math.max(a, x.id); }, 0);
          if (sessiz === true) { if (enBuyuk <= sonId) return; bildir('Yeni yanıt'); }
          document.title = b.baslik + ' — Forum — KPSS Tercihi';
          if (!kap.querySelector('.fr-yazici')) {
            var ust = parcalar([katAd(b.kategori), duzeyAd(b.duzey), b.puan_turu && b.puan != null ? b.puan_turu + ' ' + String(b.puan).replace('.', ',') : '']);
            var benim = uye() && uye().rumuz === b.rumuz;
            kap.innerHTML = '<p class="fr-ust-bilgi">' + ust + '</p><h2 class="fr-baslik-bas">' + esc(b.baslik) + '</h2>'
              + (b.govde ? '<div class="fr-ilk"><header><b>' + esc(b.rumuz) + '</b>' + etiket(b) + '<time>' + zaman(b.olusma) + '</time></header><div class="fr-metin">' + metin(b.govde) + '</div>'
                + '<div data-anket-yer></div><div data-puan-ozet></div>'
                + '<footer>' + (benim || !insanMi(b) ? '' : '<button type="button" class="fr-eylem" data-baslik-oy aria-pressed="' + (b.oyladim ? 'true' : 'false') + '">Faydalı' + (b.faydali ? ' ' + sayi(b.faydali) : '') + '</button>')
                + '<button type="button" class="fr-eylem" data-paylas>Paylaş</button></footer></div>' : '')
              + (b.ilan_id ? '<p><a class="yazi-link" href="../ilan/' + encodeURIComponent(b.ilan_id) + '/#tartisma">İlanı aç</a></p>' : '')
              + '<h3 class="fr-alt-bas" data-sayi></h3><div data-liste></div>' + yaziciHtml('baslik-' + id, 'Yanıtını yaz…');
            yaziciBagla(kap, 'baslik-' + id, function (g, ust_) {
              var govde = { govde: g }; if (ust_) govde.ust_id = ust_;
              return api('/baslik/' + id + '/yanit', { yontem: 'POST', govde: govde }).then(function () { iz('forum_yanit', 'baslik'); return yukle(); }).then(function () {
                if (!SOHBET) return;   // sohbet görünümü: gönderilen mesaj görünsün diye konuşmanın sonuna in
                var sc = hedef.closest('.fr-sh-oda');
                if (sc) sc.scrollTop = sc.scrollHeight; else window.scrollTo(0, document.documentElement.scrollHeight);
              });
            });
            puanOzeti(kap, b);
          }
          var ay = kap.querySelector('[data-anket-yer]');
          if (ay) ay.innerHTML = anketHtml(j.anket);
          kap.querySelector('[data-sayi]').textContent = y.length ? sayi(y.length) + ' yanıt' : 'Henüz yanıt yok';
          kap.querySelector('[data-liste]').innerHTML = '<div class="fr-liste">' + yanitListesi(y, ilk ? 0 : sonId) + '</div>';
          if (ilk && location.hash) { var h = document.getElementById(location.hash.slice(1)); if (h) h.scrollIntoView(); }
          sonId = enBuyuk; ilk = false;
        }, function (h) { if (sessiz !== true) kap.innerHTML = '<p class="fr-bos">' + (h.durum === 404 ? 'Bu başlık bulunamadı.' : esc(h.message)) + '</p>'; });
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
            bo.setAttribute('aria-pressed', String(!!j.oyladim)); bo.textContent = 'Faydalı' + (j.faydali ? ' ' + sayi(j.faydali) : '');
          }, function (h) { bildir(h.message); });
        }
      });
      eylemleriBagla(kap, yukle);
      yenileyiciler = [function () { kap.innerHTML = ''; ilk = true; return yukle(); }];
      durdur = canliTut(yukle);
      yukle();
    }
    function yeni(kategori, hedef) {
      hedef = hedef || kok_;
      var u = uye();
      var secenek = KATEGORILER.filter(function (c) { return c.kod !== 'ilan' && (c.kod !== 'etkinlik' || (u && (u.rol === 'yonetici' || u.rol === 'sistem'))); });
      var t = oku('fr-taslak-yeni') || {};
      var ekAcik = !!(t.duzey || t.puan || (t.anket && t.anket.length));
      hedef.innerHTML = '<p class="fr-geri"><a class="yazi-link" data-ic href="?">Foruma dön</a></p>'
        + '<form class="fr-form fr-yeni"><h2>Soru sor</h2>'
        + '<input id="fr-b" maxlength="120" required placeholder="Başlık: ör. Önlisans 72 puanla nereye başvurabilirim?" value="' + esc(t.baslik || '') + '" aria-label="Başlık">'
        + '<textarea id="fr-g" rows="5" maxlength="4000" required placeholder="Ayrıntı" aria-label="Ayrıntı">' + esc(t.govde || '') + '</textarea>'
        + '<select id="fr-k" aria-label="Konu">' + secenek.map(function (c) { return '<option value="' + c.kod + '"' + ((t.kategori || kategori || 'puan') === c.kod ? ' selected' : '') + '>' + esc(c.ad) + '</option>'; }).join('') + '</select>'
        + '<details class="fr-ac"' + (ekAcik ? ' open' : '') + '><summary>Düzey, puan veya anket ekle</summary><div class="fr-ek">'
        + '<select id="fr-d" aria-label="Öğrenim düzeyi"><option value="">Düzey seçme</option>' + DUZEYLER.map(function (d) { return '<option value="' + d.kod + '"' + (t.duzey === d.kod ? ' selected' : '') + '>' + d.ad + '</option>'; }).join('') + '</select>'
        + '<span class="fr-puan"><select id="fr-pt" aria-label="Puan türü">' + PUAN_TURLERI.map(function (x) { return '<option' + (t.puan_turu === x ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select>'
        + '<input id="fr-p" inputmode="decimal" placeholder="Puan" value="' + esc(t.puan || '') + '" aria-label="Puan"></span>'
        + '<div class="fr-anket-g">' + [0, 1, 2, 3].map(function (i) { return '<input maxlength="80" placeholder="Anket seçeneği ' + (i + 1) + '" value="' + esc((t.anket || [])[i] || '') + '">'; }).join('') + '</div>'
        + '</div></details>'
        + '<button class="btn btn-ana btn-buyuk" type="submit">Gönder</button><p class="fr-hata" role="alert" hidden></p></form>';
      var f = hedef.querySelector('form');
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
        if (girisGerekli('Göndermek için giriş yap', function () { git('?yeni=1'); setTimeout(function () { var x = document.querySelector('form.fr-yeni'); if (x) x.requestSubmit(); }, 300); })) return;
        api('/baslik', { yontem: 'POST', govde: govde }).then(function (j) {
          yaz('fr-taslak-yeni', null); iz('forum_baslik', g.kategori);
          git('?b=' + j.baslik.id);
        }, function (h) { hata(h.message); });
      };
    }
    var seciliOda = 0;
    function ciz() {
      if (durdur) { durdur(); durdur = null; }
      var q = new URLSearchParams(location.search);
      document.title = 'Forum — KPSS Tercihi';
      yenileyiciler = [ciz];
      var lp = { k: q.get('k') || '', bekleyen: q.get('bekleyen') === '1', q: q.get('q') || '' };
      seciliOda = +q.get('b') || 0;
      // Sohbet görünümü, geniş ekranda: solda konular, sağda açık konuşma (telefonda tek panel, sırayla).
      if (SOHBET && matchMedia('(min-width: 900px)').matches) {
        kok_.innerHTML = '<div class="fr-sh"><section class="fr-sh-liste" aria-label="Konular"></section><section class="fr-sh-oda" aria-live="polite"></section></div>';
        var L = kok_.querySelector('.fr-sh-liste'), O = kok_.querySelector('.fr-sh-oda');
        liste(lp, L);
        if (seciliOda) baslik(seciliOda, O);
        else if (q.get('yeni')) yeni(q.get('k'), O);
        else O.innerHTML = '<div class="fr-sh-bos">' + ikon(SOHBET) + '<b>Bir konu seç ya da yeni soru sor</b><a class="btn btn-ana" data-ic href="?yeni=1">Soru sor</a></div>';
        return;
      }
      if (seciliOda) baslik(seciliOda);
      else if (q.get('yeni')) yeni(q.get('k'));
      else liste(lp);
    }
    if (SOHBET) { var genisMi = matchMedia('(min-width: 900px)'); if (genisMi.addEventListener) genisMi.addEventListener('change', ciz); }
    kok_.insertAdjacentHTML('afterend', '<p class="fr-gorunum">Görünüm: <a class="yazi-link" href="?tasarim=klasik">Sade</a>, <a class="yazi-link" href="?tasarim=pano">Pano</a> veya <a class="yazi-link" href="?tasarim=sohbet">Sohbet</a></p>');
    kok_.addEventListener('change', function (e) {
      var c = e.target.closest('[data-bildirim]');
      if (!c) return;
      api('/ben/bildirim', { yontem: 'POST', govde: { acik: c.checked } }).then(function () {
        var u = uye(); if (u) { u.bildirim = c.checked ? 1 : 0; yaz('fr-uye', u); }
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
    if (!t && !f) listeRozetleri();
    if (oturum()) api('/ben').then(function (j) { yaz('fr-uye', j.uye); }, function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', basla); else basla();
})();
