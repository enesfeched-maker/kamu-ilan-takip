/* KPSS Tercihi — forum (Kasım 2026).
   İki yerde çalışır: ilan sayfasındaki #tartisma (başvurdum sayacı, anonim puan, ilan soruları)
   ve /forum/ sayfasındaki #forum (kategoriler, başlıklar, başlık görünümü, yeni başlık).
   Veri kpss-forum Worker'ından gelir; giriş Telegram ile yapılır, sitede yalnız seçilen rumuz görünür.
   Asistan ve "KPSS Tercihi" hesabı her zaman rozetiyle görünür: otomatik içerik insan gibi gösterilmez. */
(function () {
  'use strict';
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var BOT = 'kamuilanibot';
  var KATEGORILER = [
    { kod: 'ilan', ad: 'İlan soruları' }, { kod: 'puan', ad: 'Puan ve tercih' }, { kod: 'kurum', ad: 'Kurum ve şehir' },
    { kod: 'mulakat', ad: 'Mülakat deneyimleri' }, { kod: 'haklar', ad: 'Haklar ve tayin' },
    { kod: 'hazirlik', ad: 'Sınava hazırlık' }, { kod: 'etkinlik', ad: 'Etkinlik' }
  ];
  var PUAN_TURLERI = ['P3', 'P93', 'P94', 'P10', 'P121'];

  /* ---------- küçük yardımcılar ---------- */
  function oku(a) { try { return JSON.parse(localStorage.getItem(a)); } catch (e) { return null; } }
  function yaz(a, d) { try { if (d == null) localStorage.removeItem(a); else localStorage.setItem(a, JSON.stringify(d)); } catch (e) {} }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(html) { var t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }
  function iz(ad, x) { try { if (window.kitOlay) window.kitOlay(ad, x); } catch (e) {} }

  function kimlik() {   // anonim cihaz kimliği: yalnız başvurdum/puan için, kişiyle eşleşmez
    var k = oku('fr-kimlik');
    if (!k) {
      var b = new Uint8Array(16); (window.crypto || window.msCrypto).getRandomValues(b);
      k = Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
      yaz('fr-kimlik', k);
    }
    return k;
  }
  function oturum() { return oku('fr-oturum'); }
  function uye() { return oku('fr-uye'); }
  function cikis() { yaz('fr-oturum', null); yaz('fr-uye', null); yenile(); }

  function api(yol, secenek) {
    secenek = secenek || {};
    var basliklar = {};
    var o = oturum();
    if (o) basliklar.Authorization = 'Bearer ' + o;
    if (secenek.govde !== undefined) basliklar['Content-Type'] = 'application/json';
    return fetch(API + yol, { method: secenek.yontem || 'GET', headers: basliklar, body: secenek.govde !== undefined ? JSON.stringify(secenek.govde) : undefined })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (r.status === 401 && o) { yaz('fr-oturum', null); yaz('fr-uye', null); }
          if (!r.ok) { var h = new Error(j.hata || j.mesaj || j.error || 'Bir sorun oluştu, biraz sonra yeniden dene.'); h.durum = r.status; throw h; }
          return j;
        });
      }, function () { throw new Error('Foruma şu an ulaşılamıyor.'); });
  }

  function zaman(sn) {
    var f = Math.max(0, Date.now() / 1000 - sn);
    if (f < 60) return 'az önce';
    if (f < 3600) return Math.floor(f / 60) + ' dk önce';
    if (f < 86400) return Math.floor(f / 3600) + ' sa önce';
    if (f < 86400 * 7) return Math.floor(f / 86400) + ' gün önce';
    return new Date(sn * 1000).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
  }
  function sayi(n) { return Number(n || 0).toLocaleString('tr-TR'); }

  var IZINLI_BAG = /^https:\/\/([a-z0-9-]+\.)*(gov\.tr|edu\.tr|kpsstercihi\.com)(\/[^\s<]*)?$|^https:\/\/t\.me\/kpsstercihi\b/i;
  function metin(govde) {   // düz metin: kaçış + izinli bağlantılar + paragraflar
    return String(govde || '').split(/\n{2,}/).map(function (p) {
      var h = esc(p).replace(/https:\/\/[^\s<]+/g, function (u) {
        var ham = u.replace(/&amp;/g, '&').replace(/[.,;:!?)]+$/, '');
        var kalan = u.slice(esc(ham).length);
        return IZINLI_BAG.test(ham) ? '<a href="' + esc(ham) + '" target="_blank" rel="noopener nofollow ugc">' + esc(ham.replace(/^https:\/\//, '')) + '</a>' + kalan : u;
      });
      return '<p>' + h.replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }

  function rozetler(k) {
    var r = '';
    if (k.rol === 'asistan') r += '<span class="fr-rozet fr-bot" title="Bu yanıt otomatik üretildi; yalnız ilan belgesindeki bilgiyi aktarır.">Otomatik yanıt</span>';
    if (k.rol === 'sistem') r += '<span class="fr-rozet fr-sistem">Site hesabı</span>';
    if (k.rol === 'yonetici') r += '<span class="fr-rozet fr-sistem">Yönetici</span>';
    if (k.kurucu && k.rol === 'uye') r += '<span class="fr-rozet fr-kurucu" title="Forumun ilk üyelerinden">Kurucu üye</span>';
    return r;
  }
  function avatar(k) {
    var ad = k.rumuz || '?';
    if (k.rol === 'asistan') return '<span class="fr-av fr-av-bot" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01"/></svg></span>';
    if (k.rol === 'sistem') return '<span class="fr-av fr-av-site" aria-hidden="true"><img src="' + kok() + 'assets/logo-96.webp?v=2" alt="" width="32" height="32"></span>';
    var h = 0; for (var i = 0; i < ad.length; i++) h = (h * 31 + ad.charCodeAt(i)) % 360;
    return '<span class="fr-av" style="--h:' + h + '" aria-hidden="true">' + esc(ad.charAt(0).toLocaleUpperCase('tr-TR')) + '</span>';
  }
  function kok() { return document.body.classList.contains('detail-page') ? '../../' : '../'; }
  function forumAdresi(q) { return kok() + 'forum/' + (q || ''); }
  function katAd(kod) { for (var i = 0; i < KATEGORILER.length; i++) if (KATEGORILER[i].kod === kod) return KATEGORILER[i].ad; return kod || ''; }

  /* ---------- giriş ---------- */
  var girisSonrasi = null;
  function girisKutusu(neden) {
    var var_ = document.getElementById('fr-giris');
    if (var_) var_.remove();
    var kutu = el('<div class="fr-perde" id="fr-giris" role="dialog" aria-modal="true" aria-labelledby="fr-giris-bas"><div class="fr-kutu">'
      + '<button type="button" class="fr-kapat" aria-label="Kapat">×</button>'
      + '<h2 id="fr-giris-bas">Foruma katıl</h2><p class="fr-not">' + esc(neden || 'Yazmak için giriş yap.') + ' Telegram hesabınla girersin; sitede yalnızca seçtiğin rumuz görünür, adın ve telefonun görünmez.</p>'
      + '<div class="fr-giris-alan"></div><p class="fr-hata" role="alert" hidden></p></div></div>');
    document.body.appendChild(kutu);
    var alan = kutu.querySelector('.fr-giris-alan');
    function kapat() { kutu.remove(); document.removeEventListener('keydown', esc_); }
    function esc_(e) { if (e.key === 'Escape') kapat(); }
    document.addEventListener('keydown', esc_);
    kutu.querySelector('.fr-kapat').onclick = kapat;
    kutu.onclick = function (e) { if (e.target === kutu) kapat(); };
    function hata(m) { var p = kutu.querySelector('.fr-hata'); p.textContent = m; p.hidden = !m; }
    function girdi(j) {
      if (j.yeni) return rumuzSor(j.gecici);
      yaz('fr-oturum', j.oturum); yaz('fr-uye', j.uye); kapat(); iz('forum_giris');
      var f = girisSonrasi; girisSonrasi = null; yenile(); if (f) f();
    }
    function rumuzSor(gecici) {
      alan.innerHTML = '<form class="fr-form"><label for="fr-rumuz">Rumuz seç</label><input id="fr-rumuz" maxlength="20" autocomplete="nickname" required placeholder="ör. memuradayi35">'
        + '<small class="fr-not">3–20 karakter; harf, rakam, nokta ve alt çizgi. Sonradan değişmez.</small><button class="btn btn-ana" type="submit">Devam et</button></form>';
      var f = alan.querySelector('form');
      f.querySelector('input').focus();
      f.onsubmit = function (e) {
        e.preventDefault(); hata('');
        api('/giris/rumuz', { yontem: 'POST', govde: { gecici: gecici, rumuz: f.querySelector('input').value.trim() } }).then(girdi, function (h) { hata(h.message); });
      };
    }
    if (YEREL) {   // yerel deneme: Telegram doğrulaması olmadan rumuzla giriş (Worker ORTAM=yerel iken)
      alan.innerHTML = '<form class="fr-form"><label for="fr-deneme">Deneme rumuzu</label><input id="fr-deneme" maxlength="20" required placeholder="ör. deneme1">'
        + '<small class="fr-not">Yalnız yerel denemede görünür; canlıda Telegram düğmesi çıkar.</small><button class="btn btn-ana" type="submit">Giriş yap</button></form>';
      var f = alan.querySelector('form');
      f.querySelector('input').focus();
      f.onsubmit = function (e) {
        e.preventDefault(); hata('');
        api('/giris/deneme', { yontem: 'POST', govde: { rumuz: f.querySelector('input').value.trim() } }).then(girdi, function (h) { hata(h.message); });
      };
    } else {
      window.frTelegram = function (k) { hata(''); api('/giris/telegram', { yontem: 'POST', govde: k }).then(girdi, function (h) { hata(h.message); }); };
      var s = document.createElement('script');
      s.async = true; s.src = 'https://telegram.org/js/telegram-widget.js?22';
      s.setAttribute('data-telegram-login', BOT); s.setAttribute('data-size', 'large'); s.setAttribute('data-radius', '10');
      s.setAttribute('data-onauth', 'frTelegram(user)'); s.setAttribute('data-request-access', 'write');
      alan.appendChild(s);
    }
  }
  function girisGerekli(neden, sonra) { if (oturum()) return false; girisSonrasi = sonra || null; girisKutusu(neden); return true; }

  /* ---------- yanıtlar (ilan sayfası ve başlık görünümü ortak) ---------- */
  function yanitHtml(y, cocuk) {
    var oy = y.oyladim ? ' aria-pressed="true"' : ' aria-pressed="false"';
    var insan = y.rol !== 'asistan' && y.rol !== 'sistem';
    return '<article class="fr-yanit' + (cocuk ? ' fr-cocuk' : '') + (y.rol === 'asistan' ? ' fr-yanit-bot' : '') + '" id="y' + y.id + '">'
      + avatar(y) + '<div class="fr-yanit-ic"><header><b>' + esc(y.rumuz) + '</b>' + rozetler(y) + '<time datetime="' + new Date(y.olusma * 1000).toISOString() + '">' + zaman(y.olusma) + '</time></header>'
      + '<div class="fr-govde">' + metin(y.govde) + '</div>'
      + '<footer><button type="button" class="fr-eylem" data-faydali="' + y.id + '"' + oy + '>Faydalı' + (y.faydali ? ' · ' + sayi(y.faydali) : '') + '</button>'
      + (cocuk ? '' : '<button type="button" class="fr-eylem" data-yanitla="' + y.id + '" data-rumuz="' + esc(y.rumuz) + '">Yanıtla</button>')
      + (insan ? '<button type="button" class="fr-eylem fr-sik" data-sikayet="' + y.id + '">Bildir</button>' : '')
      + '</footer></div></article>';
  }
  function yanitListesi(yanitlar) {
    var kok_ = [], alt = {};
    yanitlar.forEach(function (y) { if (y.ust_id) (alt[y.ust_id] = alt[y.ust_id] || []).push(y); else kok_.push(y); });
    var bilinen = {}; kok_.forEach(function (y) { bilinen[y.id] = 1; });
    Object.keys(alt).forEach(function (u) { if (!bilinen[u]) { kok_ = kok_.concat(alt[u]); delete alt[u]; } });   // üstü gizlenen yanıtlar düz akar
    kok_.sort(function (a, b) { return a.id - b.id; });
    return kok_.map(function (y) { return yanitHtml(y) + (alt[y.id] || []).map(function (c) { return yanitHtml(c, true); }).join(''); }).join('');
  }
  function yaziciHtml(yer, ipucu) {
    return '<form class="fr-yazici" data-yer="' + yer + '"><div class="fr-yanitlanan" hidden><span></span><button type="button" class="fr-eylem" data-iptal>Vazgeç</button></div>'
      + '<label class="sr-only" for="fr-metin-' + yer + '">Mesajın</label><textarea id="fr-metin-' + yer + '" rows="3" maxlength="2000" placeholder="' + esc(ipucu) + '"></textarea>'
      + '<div class="fr-yazici-alt"><small class="fr-not">Kişisel bilgi (kimlik no, telefon) paylaşma. Bağlantılar yalnız resmî sitelere.</small>'
      + '<button type="submit" class="btn btn-ana">Gönder</button></div><p class="fr-hata" role="alert" hidden></p></form>';
  }
  function yaziciBagla(kap, gonder) {
    var f = kap.querySelector('.fr-yazici');
    if (!f) return;
    var ust = null, ta = f.querySelector('textarea'), etiket = f.querySelector('.fr-yanitlanan');
    function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
    ta.addEventListener('focus', function () { if (!oturum()) { ta.blur(); girisGerekli('Yazmak için giriş yap.', function () { var t = document.querySelector('.fr-yazici textarea'); if (t) t.focus(); }); } });
    f.querySelector('[data-iptal]').onclick = function () { ust = null; etiket.hidden = true; };
    kap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-yanitla]');
      if (!b) return;
      ust = +b.getAttribute('data-yanitla');
      etiket.querySelector('span').textContent = b.getAttribute('data-rumuz') + ' adlı kişiye yanıt';
      etiket.hidden = false; ta.focus();
    });
    f.onsubmit = function (e) {
      e.preventDefault(); hata('');
      var g = ta.value.trim();
      if (g.length < 2) return hata('Mesaj çok kısa.');
      if (girisGerekli('Yazmak için giriş yap.')) return;
      var dugme = f.querySelector('[type=submit]'); dugme.disabled = true;
      gonder(g, ust).then(function () { ta.value = ''; ust = null; etiket.hidden = true; }, function (h) { hata(h.message); })
        .then(function () { dugme.disabled = false; });
    };
  }
  function eylemleriBagla(kap, sonra) {
    kap.addEventListener('click', function (e) {
      var f = e.target.closest('[data-faydali]'), s = e.target.closest('[data-sikayet]');
      if (f) {
        if (girisGerekli('Oy vermek için giriş yap.')) return;
        api('/yanit/' + f.getAttribute('data-faydali') + '/faydali', { yontem: 'POST', govde: {} }).then(function (j) {
          var n = j.faydali != null ? j.faydali : null, acik = j.oyladim != null ? j.oyladim : f.getAttribute('aria-pressed') !== 'true';
          f.setAttribute('aria-pressed', String(!!acik));
          if (n != null) f.textContent = 'Faydalı' + (n ? ' · ' + sayi(n) : '');
        }, function (h) { alert(h.message); });
      } else if (s) {
        if (girisGerekli('Bildirmek için giriş yap.')) return;
        if (!confirm('Bu mesajı kurallara aykırı diye bildirmek istiyor musun?')) return;
        api('/yanit/' + s.getAttribute('data-sikayet') + '/sikayet', { yontem: 'POST', govde: {} }).then(function () {
          s.textContent = 'Bildirildi'; s.disabled = true; if (sonra) sonra();
        }, function (h) { alert(h.message); });
      }
    });
  }

  /* ---------- ilan sayfası: başvurdum + puan + sorular ---------- */
  function ilanBolumu(kap) {
    var ilan = kap.getAttribute('data-ilan'), ad = kap.getAttribute('data-ad') || 'Bu ilan', acik = kap.getAttribute('data-acik') === '1';
    var basvurular = oku('fr-basvuru') || {};
    var benim = basvurular[ilan];   // {puan_turu, puan} | true
    kap.innerHTML = '<div class="bolum-bas"><div><h2>Bu ilan hakkında</h2><p>Başvuranlar, sorular ve cevaplar</p></div></div>'
      + '<div class="fr-ilan-ust"><div class="fr-kart fr-basvuru" aria-live="polite"><p class="fr-yukleniyor">Yükleniyor…</p></div></div>'
      + '<div class="fr-kart fr-sorular"><div class="fr-ilk">' + avatar({ rol: 'sistem' }) + '<div><header><b>KPSS Tercihi</b>' + rozetler({ rol: 'sistem' }) + '</header>'
      + '<p>Bu ilanla ilgili sorunu yaz. Otomatik yanıt ilan belgesindeki bilgiyi aktarır; başvuranlar da deneyimini paylaşabilir.</p></div></div>'
      + '<div class="fr-liste"></div>' + yaziciHtml('ilan', 'Bu ilanla ilgili sorunu yaz…') + '<p class="fr-forum-bag" hidden></p></div>';
    var liste = kap.querySelector('.fr-liste'), bas = kap.querySelector('.fr-basvuru'), bag = kap.querySelector('.fr-forum-bag'), baslikId = null;

    function basvuruCiz(b) {
      b = b || { sayi: 0 };
      benim = (oku('fr-basvuru') || {})[ilan];
      var dugme = acik || benim
        ? '<button type="button" class="btn ' + (benim ? 'btn-ikinci dolu' : 'btn-ana') + '" data-basvurdum aria-pressed="' + (benim ? 'true' : 'false') + '">'
          + (benim ? '✓ Başvurdum' : 'Başvurdum') + '</button>'
        : '<span class="fr-not">Başvuru süresi bitti</span>';
      var sayiYazi = b.sayi ? '<b>' + sayi(b.sayi) + '</b> kişi başvurduğunu işaretledi' : 'Henüz başvurduğunu işaretleyen yok. İlk sen ol.';
      var h = '<div class="fr-basvuru-ust"><p class="fr-sayac">' + sayiYazi + '</p>' + dugme + '</div>';
      if (b.puan) {
        var p = b.puan, en = p.en_dusuk, ek = p.en_yuksek, ara = Math.max(ek - en, 0.01);
        var yuzde = function (x) { return ((x - en) / ara * 100).toFixed(1) + '%'; };
        h += '<div class="fr-dagilim"><p><b>' + esc(p.puan_turu) + '</b> puanını paylaşan ' + sayi(p.adet) + ' kişi · en düşük ' + esc(p.en_dusuk) + ' · ortanca ' + esc(p.medyan) + ' · en yüksek ' + esc(p.en_yuksek) + '</p>'
          + '<div class="fr-cubuk" aria-hidden="true"><span class="fr-kutu-c" style="left:' + yuzde(p.ceyrek1) + ';width:calc(' + yuzde(p.ceyrek3) + ' - ' + yuzde(p.ceyrek1) + ')"></span>'
          + '<span class="fr-medyan" style="left:' + yuzde(p.medyan) + '"></span>'
          + (benim && benim.puan && benim.puan_turu === p.puan_turu ? '<span class="fr-sen" style="left:' + yuzde(Math.min(Math.max(benim.puan, en), ek)) + '"><i>Sen</i></span>' : '') + '</div>'
          + (p.sira ? '<p class="fr-not">Paylaşanlar arasında senden yüksek puanlı ' + sayi(p.sira - 1) + ' kişi var.</p>' : '')
          + '<p class="fr-not">Yalnız gönüllü paylaşılan puanlardır; resmî taban puanı değildir.</p></div>';
      } else if (b.sayi) {
        h += '<p class="fr-not">Puanını paylaşan 5 kişi olunca başvuranların puan dağılımı burada görünür.</p>';
      }
      if (benim && !benim.puan) {
        h += '<form class="fr-puan"><span>Puanını anonim paylaş:</span><select aria-label="Puan türü">' + PUAN_TURLERI.map(function (t) { return '<option>' + t + '</option>'; }).join('') + '</select>'
          + '<input type="number" inputmode="decimal" step="0.00001" min="40" max="100" placeholder="ör. 78,45" aria-label="Puan" required><button class="btn btn-ikinci" type="submit">Paylaş</button></form>';
      }
      bas.innerHTML = h;
      var f = bas.querySelector('.fr-puan');
      if (f) f.onsubmit = function (e) {
        e.preventDefault();
        var tur = f.querySelector('select').value, p = parseFloat(String(f.querySelector('input').value).replace(',', '.'));
        if (!(p >= 40 && p <= 100)) { alert('Puan 40 ile 100 arasında olmalı.'); return; }
        basvur({ puan_turu: tur, puan: Math.round(p * 100) / 100 });
      };
    }
    function basvur(puan) {
      var govde = { kimlik: kimlik() };
      if (puan) { govde.puan_turu = puan.puan_turu; govde.puan = puan.puan; }
      api('/basvuru/' + encodeURIComponent(ilan), { yontem: 'POST', govde: govde }).then(function (j) {
        var m = oku('fr-basvuru') || {}; m[ilan] = puan || true; yaz('fr-basvuru', m);
        iz('forum_basvurdum', puan ? 'puan' : '');
        basvuruCiz(j.basvuru || j);
      }, function (h) { alert(h.message); });
    }
    bas.addEventListener('click', function (e) {
      if (!e.target.closest('[data-basvurdum]')) return;
      if ((oku('fr-basvuru') || {})[ilan]) {
        if (!confirm('Başvurdum işaretini kaldırmak istiyor musun?')) return;
        api('/basvuru/' + encodeURIComponent(ilan) + '?kimlik=' + kimlik(), { yontem: 'DELETE' }).then(function (j) {
          var m = oku('fr-basvuru') || {}; delete m[ilan]; yaz('fr-basvuru', m); basvuruCiz(j.basvuru || j);
        }, function (h) { alert(h.message); });
      } else basvur(null);
    });

    function ciz(j) {
      var y = j.yanitlar || [];
      liste.innerHTML = yanitListesi(y);
      if (j.basvuru && j.basvuru.ben && !(oku('fr-basvuru') || {})[ilan]) {   // başka sekmede/cihazda işaretlenmiş
        var m = oku('fr-basvuru') || {}; m[ilan] = j.basvuru.ben.puan ? j.basvuru.ben : true; yaz('fr-basvuru', m);
      }
      if (j.baslik && j.baslik.id) { baslikId = j.baslik.id; bag.hidden = false; bag.innerHTML = '<a class="yazi-link" href="' + forumAdresi('?b=' + j.baslik.id) + '">Forumda aç →</a>'; }
      basvuruCiz(j.basvuru);
    }
    function yukle() {
      var k = '?kimlik=' + kimlik();
      return api('/ilan/' + encodeURIComponent(ilan) + k).then(ciz, function () {
        bas.innerHTML = '<p class="fr-not">Tartışma şu an yüklenemedi.</p>';
      });
    }
    yaziciBagla(kap, function (g, ust) {
      var istek = ust && baslikId   // bir yanıta yanıt: başlık zaten var
        ? api('/baslik/' + baslikId + '/yanit', { yontem: 'POST', govde: { govde: g, ust_id: ust } })
        : api('/ilan/' + encodeURIComponent(ilan) + '/yanit', { yontem: 'POST', govde: { govde: g, ilan_baslik: ad } });
      return istek.then(function () { iz('forum_yanit', 'ilan'); return yukle(); });
    });
    eylemleriBagla(kap, yukle);
    yenileyiciler.push(yukle);
    yukle();
  }

  /* ---------- forum sayfası ---------- */
  function forumSayfasi(kok_) {
    var durum = { kategori: '', sayfa: 1 };
    function git(q) { history.pushState(null, '', q || location.pathname); ciz(); window.scrollTo(0, 0); }
    kok_.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-ic]');
      if (!a || e.metaKey || e.ctrlKey) return;
      e.preventDefault(); git(a.getAttribute('href'));
    });
    window.addEventListener('popstate', ciz);

    function profilCubugu() {
      var u = uye();
      if (!u) return '<div class="fr-profil"><span class="fr-not">Okumak serbest; yazmak için giriş yap.</span><button type="button" class="btn btn-ikinci" data-giris>Giriş yap</button></div>';
      return '<div class="fr-profil">' + avatar(u) + '<span><b>' + esc(u.rumuz) + '</b>' + rozetler(u) + '</span>'
        + '<label class="fr-bildirim"><input type="checkbox" data-bildirim' + (u.bildirim === 0 ? '' : ' checked') + '> Yanıtları Telegram\'dan bildir</label>'
        + '<button type="button" class="fr-eylem" data-cikis>Çıkış</button></div>';
    }
    function ustBolum() {
      var k = durum.kategori;
      return profilCubugu() + '<div class="fr-araclar"><nav class="fr-kategoriler" aria-label="Kategoriler"><a data-ic href="?"' + (k ? '' : ' aria-current="page"') + '>Tümü</a>'
        + KATEGORILER.map(function (c) { return '<a data-ic href="?k=' + c.kod + '"' + (k === c.kod ? ' aria-current="page"' : '') + '>' + esc(c.ad) + '</a>'; }).join('')
        + '</nav><a class="btn btn-ana" data-ic href="?yeni=1' + (k && k !== 'ilan' && k !== 'etkinlik' ? '&k=' + k : '') + '">Yeni başlık</a></div>';
    }
    function satir(b) {
      return '<a class="fr-satir" data-ic href="?b=' + b.id + '">'
        + '<span class="fr-satir-ic"><span class="fr-satir-ust">' + (b.sabit ? '<span class="fr-etiket fr-sabit">Sabit</span>' : '')
        + '<span class="fr-etiket">' + esc(katAd(b.kategori)) + '</span>' + (b.kaynak === 'telegram' ? '<span class="fr-etiket fr-tg">Telegram\'dan gelen soru</span>' : '') + '</span>'
        + '<b class="fr-satir-bas">' + esc(b.baslik) + '</b>' + (b.kisa ? '<span class="fr-satir-kisa">' + esc(b.kisa) + '</span>' : '')
        + '<span class="fr-satir-alt">' + esc(b.rumuz || '') + rozetler(b) + ' · ' + zaman(b.son_hareket || b.olusma) + '</span></span>'
        + '<span class="fr-yanit-sayi" aria-label="' + sayi(b.yanit_sayisi) + ' yanıt"><b>' + sayi(b.yanit_sayisi) + '</b><small>yanıt</small></span></a>';
    }
    function liste() {
      kok_.innerHTML = ustBolum() + '<div class="fr-kart fr-basliklar"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = kok_.querySelector('.fr-basliklar');
      function getir(sayfa, ekle) {
        return api('/basliklar?kategori=' + encodeURIComponent(durum.kategori) + '&sayfa=' + sayfa).then(function (j) {
          var b = j.basliklar || j || [];
          var eski = kap.querySelector('.fr-daha'); if (eski) eski.remove();
          if (!ekle) kap.innerHTML = '';
          if (!b.length && !ekle) kap.innerHTML = '<div class="fr-bos"><b>Bu bölümde henüz başlık yok.</b><p>İlk soruyu sen sor; ilan sorularını ilgili ilanın sayfasından da yazabilirsin.</p></div>';
          kap.insertAdjacentHTML('beforeend', b.map(satir).join(''));
          if (j.sonraki) {
            var d = el('<button type="button" class="btn btn-ikinci fr-daha">Daha fazla</button>');
            d.onclick = function () { d.disabled = true; getir(sayfa + 1, true); };
            kap.appendChild(d);
          }
        }, function (h) { kap.innerHTML = '<p class="fr-not">' + esc(h.message) + '</p>'; });
      }
      getir(1);
    }
    function baslik(id) {
      kok_.innerHTML = profilCubugu() + '<p class="fr-geri"><a class="yazi-link" data-ic href="?">← Tüm başlıklar</a></p><div class="fr-kart fr-baslik"><p class="fr-yukleniyor">Yükleniyor…</p></div>';
      var kap = kok_.querySelector('.fr-baslik');
      function yukle() {
        return api('/baslik/' + id).then(function (j) {
          var b = j.baslik || j, y = j.yanitlar || [];
          document.title = b.baslik + ' — Forum — KPSS Tercihi';
          var ilanBag = b.ilan_id ? '<p><a class="yazi-link" href="../ilan/' + encodeURIComponent(b.ilan_id) + '/">İlan sayfasını aç →</a></p>' : '';
          kap.innerHTML = '<header class="fr-baslik-bas"><span class="fr-satir-ust"><span class="fr-etiket">' + esc(katAd(b.kategori)) + '</span>'
            + (b.kaynak === 'telegram' ? '<span class="fr-etiket fr-tg">Telegram\'dan gelen soru</span>' : '') + '</span><h2>' + esc(b.baslik) + '</h2></header>'
            + (b.govde ? '<div class="fr-ilk">' + avatar(b) + '<div><header><b>' + esc(b.rumuz) + '</b>' + rozetler(b) + '<time>' + zaman(b.olusma) + '</time></header><div class="fr-govde">' + metin(b.govde) + '</div></div></div>' : '')
            + ilanBag + '<h3 class="fr-alt-bas">' + (y.length ? sayi(y.length) + ' yanıt' : 'Henüz yanıt yok') + '</h3><div class="fr-liste">' + yanitListesi(y) + '</div>'
            + yaziciHtml('baslik', 'Yanıtını yaz…');
          yaziciBagla(kap, function (g, ust) {
            var govde = { govde: g }; if (ust) govde.ust_id = ust;
            return api('/baslik/' + id + '/yanit', { yontem: 'POST', govde: govde }).then(function () { iz('forum_yanit', 'baslik'); return yukle(); });
          });
          if (location.hash) { var h = document.getElementById(location.hash.slice(1)); if (h) h.scrollIntoView(); }
        }, function (h) { kap.innerHTML = '<p class="fr-not">' + (h.durum === 404 ? 'Bu başlık bulunamadı ya da kaldırıldı.' : esc(h.message)) + '</p>'; });
      }
      eylemleriBagla(kap, yukle);
      yenileyiciler = [yukle];
      yukle();
    }
    function yeni(kat) {
      var u = uye();
      var secenek = KATEGORILER.filter(function (c) { return c.kod !== 'ilan' && (c.kod !== 'etkinlik' || (u && (u.rol === 'yonetici' || u.rol === 'sistem'))); });
      kok_.innerHTML = profilCubugu() + '<p class="fr-geri"><a class="yazi-link" data-ic href="?">← Tüm başlıklar</a></p>'
        + '<form class="fr-kart fr-form fr-yeni"><h2>Yeni başlık</h2>'
        + '<label for="fr-k">Kategori</label><select id="fr-k">' + secenek.map(function (c) { return '<option value="' + c.kod + '"' + (c.kod === kat ? ' selected' : '') + '>' + esc(c.ad) + '</option>'; }).join('') + '</select>'
        + '<label for="fr-b">Başlık</label><input id="fr-b" maxlength="120" required placeholder="ör. 2026 KPSS P3 ile hangi kurumlar mümkün?">'
        + '<label for="fr-g">Ayrıntı</label><textarea id="fr-g" rows="7" maxlength="4000" required placeholder="Sorunu ya da deneyimini anlat…"></textarea>'
        + '<ul class="fr-kurallar"><li>Kimlik no, telefon, e-posta paylaşma.</li><li>Kaba söz yok; kişileri değil konuyu tartış.</li><li>Bağlantılar yalnız resmî sitelere (gov.tr, edu.tr).</li><li>İlana özel sorularını ilgili ilanın sayfasında sor.</li></ul>'
        + '<div class="fr-yazici-alt"><span></span><button class="btn btn-ana" type="submit">Başlığı aç</button></div><p class="fr-hata" role="alert" hidden></p></form>';
      var f = kok_.querySelector('form');
      function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
      f.onsubmit = function (e) {
        e.preventDefault(); hata('');
        if (girisGerekli('Başlık açmak için giriş yap.')) return;
        var g = { kategori: f.querySelector('#fr-k').value, baslik: f.querySelector('#fr-b').value.trim(), govde: f.querySelector('#fr-g').value.trim() };
        if (g.baslik.length < 8) return hata('Başlık en az 8 karakter olmalı.');
        if (g.govde.length < 10) return hata('Ayrıntı en az 10 karakter olmalı.');
        api('/baslik', { yontem: 'POST', govde: g }).then(function (j) {
          iz('forum_baslik', g.kategori);
          var id = j.id || (j.baslik && j.baslik.id);
          git(id ? '?b=' + id : '?k=' + g.kategori);
        }, function (h) { hata(h.message); });
      };
    }
    function ciz() {
      var q = new URLSearchParams(location.search);
      durum.kategori = q.get('k') || '';
      document.title = 'Forum — KPSS Tercihi';
      yenileyiciler = [ciz];
      if (q.get('b')) baslik(+q.get('b'));
      else if (q.get('yeni')) yeni(q.get('k'));
      else liste();
    }
    kok_.addEventListener('click', function (e) {
      if (e.target.closest('[data-giris]')) girisKutusu();
      if (e.target.closest('[data-cikis]')) cikis();
    });
    kok_.addEventListener('change', function (e) {
      var c = e.target.closest('[data-bildirim]');
      if (!c) return;
      api('/ben/bildirim', { yontem: 'POST', govde: { acik: c.checked } }).then(function () {
        var u = uye(); if (u) { u.bildirim = c.checked ? 1 : 0; yaz('fr-uye', u); }
      }, function (h) { c.checked = !c.checked; alert(h.message); });
    });
    ciz();
  }

  var yenileyiciler = [];
  function yenile() { yenileyiciler.forEach(function (f) { try { f(); } catch (e) {} }); }

  function basla() {
    var t = document.getElementById('tartisma');
    if (t && t.getAttribute('data-ilan')) ilanBolumu(t);
    var f = document.getElementById('forum');
    if (f) forumSayfasi(f);
    if (oturum()) api('/ben').then(function (j) { yaz('fr-uye', j.uye || j); }, function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', basla); else basla();
})();
