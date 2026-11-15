/* KPSS Tercihi — forum (Kasım 2026).
   Üç yerde çalışır:
   - ilan sayfası #tartisma: başvurdum sayacı, anonim puan, ilan soruları (özetin hemen altında) + "Soru sor" düğmeleri;
   - /forum/ #forum: canlı şerit, soru kutusu, kategoriler, başlıklar, başlık görünümü;
   - ana sayfa ilan listesi: konuşulan ilanlara küçük mesaj rozeti.
   Veri kpss-forum Worker'ından gelir; giriş Telegram ile, sitede yalnız seçilen rumuz görünür.
   Otomatik yanıt ve site hesabı her zaman rozetiyle görünür; sayılar gerçek veridir, uydurma etkinlik gösterilmez. */
(function () {
  'use strict';
  var YEREL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var API = window.FORUM_API || (YEREL ? 'http://127.0.0.1:8790' : 'https://forum-api.kpsstercihi.com');
  var BOT = 'kamuilanibot';
  var KATEGORILER = [
    { kod: 'ilan', ad: 'İlan soruları', ac: 'Başvuru, belge, son gün', ik: 'M7 4h10l3 3v13H7zM10 11h7M10 15h7' },
    { kod: 'puan', ad: 'Puan ve tercih', ac: 'Kaç puanla nereye girilir', ik: 'M4 19V9M10 19V5M16 19v-7M22 19H2' },
    { kod: 'kurum', ad: 'Kurum ve şehir', ac: 'Çalışma ortamı, lojman, şehir', ik: 'M4 20V9l8-5 8 5v11M9 20v-6h6v6' },
    { kod: 'mulakat', ad: 'Mülakat deneyimleri', ac: 'Ne soruldu, nasıl geçti', ik: 'M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20l1-4.3A7.5 7.5 0 1 1 20 12.5z' },
    { kod: 'haklar', ad: 'Haklar ve tayin', ac: '4/B, eş durumu, maaş', ik: 'M12 3l8 4v5c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V7z' },
    { kod: 'hazirlik', ad: 'Sınava hazırlık', ac: 'Kaynak, program, motivasyon', ik: 'M4 5h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H4zM20 5h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7z' },
    { kod: 'etkinlik', ad: 'Etkinlik', ac: 'Tercih ve sonuç günleri', ik: 'M5 5h14v15H5zM5 10h14M9 3v4M15 3v4' }
  ];
  var PUAN_TURLERI = ['P3', 'P93', 'P94', 'P10', 'P121'];
  var HIZLI_SORULAR = ['Son başvuru ne zaman?', 'Hangi bölümler başvurabilir?', 'Kaç kişi alınacak?', 'Mülakat var mı?', 'Başvuranlar kaç puanla başvurdu?'];

  /* ---------- küçük yardımcılar ---------- */
  function oku(a) { try { return JSON.parse(localStorage.getItem(a)); } catch (e) { return null; } }
  function yaz(a, d) { try { if (d == null) localStorage.removeItem(a); else localStorage.setItem(a, JSON.stringify(d)); } catch (e) {} }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(html) { var t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }
  function iz(ad, x) { try { if (window.kitOlay) window.kitOlay(ad, x); } catch (e) {} }
  function ikon(d, s) { return '<svg viewBox="0 0 24 24" aria-hidden="true"' + (s ? ' class="' + s + '"' : '') + '><path d="' + d + '"/></svg>'; }
  var SOHBET = 'M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20l1-4.3A7.5 7.5 0 1 1 20 12.5z';

  function kimlik() {   // anonim cihaz kimliği: yalnız başvurdum/puan için
    var k = oku('fr-kimlik');
    if (!k) {
      var b = new Uint8Array(16); (window.crypto || window.msCrypto).getRandomValues(b);
      k = Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
      yaz('fr-kimlik', k);
    }
    return k;
  }
  function basvurularim() {   // {ilan: {ad, puan_turu?, puan?}}; eski kayıtlarda değer true olabilir
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
    if (f < 3600) return Math.floor(f / 60) + ' dk önce';
    if (f < 86400) return Math.floor(f / 3600) + ' sa önce';
    if (f < 86400 * 7) return Math.floor(f / 86400) + ' gün önce';
    return new Date(sn * 1000).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' });
  }
  function sayi(n) { return Number(n || 0).toLocaleString('tr-TR'); }
  function bildir(m) {
    var t = el('<div class="fr-toast" role="status">' + esc(m) + '</div>');
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('fr-git'); setTimeout(function () { t.remove(); }, 400); }, 2600);
  }

  var IZINLI_BAG = /^https:\/\/([a-z0-9-]+\.)*(gov\.tr|edu\.tr|kpsstercihi\.com)(\/[^\s<]*)?$|^https:\/\/t\.me\/kpsstercihi\b/i;
  function metin(govde) {
    return String(govde || '').split(/\n{2,}/).map(function (p) {
      var h = esc(p).replace(/https:\/\/[^\s<]+/g, function (u) {
        var ham = u.replace(/&amp;/g, '&').replace(/[.,;:!?)]+$/, '');
        var kalan = u.slice(esc(ham).length);
        return IZINLI_BAG.test(ham) ? '<a href="' + esc(ham) + '" target="_blank" rel="noopener nofollow ugc">' + esc(ham.replace(/^https:\/\//, '')) + '</a>' + kalan : u;
      });
      h = h.replace(/(^|[\s(])@([A-Za-z0-9_.çğıöşüÇĞİÖŞÜ]{3,20})/g, '$1<b class="fr-anma">@$2</b>');   // @rumuz anmaları
      return '<p>' + h.replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }

  function insanMi(k) { return k.rol !== 'asistan' && k.rol !== 'sistem'; }
  function rozetler(k) {
    var r = '';
    if (k.rol === 'asistan') r += '<span class="fr-rozet fr-bot" title="Otomatik üretildi; yalnız ilan belgesindeki bilgiyi aktarır.">Otomatik yanıt</span>';
    if (k.rol === 'sistem') r += '<span class="fr-rozet fr-sistem">Site hesabı</span>';
    if (k.rol === 'yonetici') r += '<span class="fr-rozet fr-sistem">Yönetici</span>';
    if (k.kurucu && k.rol === 'uye') r += '<span class="fr-rozet fr-kurucu" title="Forumun ilk 200 üyesinden">Kurucu üye</span>';
    if (k.rol === 'uye' && k.itibar >= 5) r += '<span class="fr-rozet fr-yardim" title="Mesajları ' + sayi(k.itibar) + ' kez faydalı bulundu">Yardımsever</span>';
    return r;
  }
  function ton(ad) { var h = 0; ad = ad || '?'; for (var i = 0; i < ad.length; i++) h = (h * 31 + ad.charCodeAt(i)) % 360; return h; }
  function avatar(k, kucuk) {
    var s = 'fr-av' + (kucuk ? ' fr-av-k' : '');
    if (k.rol === 'asistan') return '<span class="' + s + ' fr-av-bot" aria-hidden="true">' + ikon('M7 9h10v9H7zM12 5v4M10 13h.01M14 13h.01') + '</span>';
    if (k.rol === 'sistem') return '<span class="' + s + ' fr-av-site" aria-hidden="true"><img src="' + kok() + 'assets/logo-96.webp?v=2" alt="" width="32" height="32"></span>';
    return '<span class="' + s + '" style="--h:' + ton(k.rumuz) + '" aria-hidden="true">' + esc((k.rumuz || '?').charAt(0).toLocaleUpperCase('tr-TR')) + '</span>';
  }
  function kok() { return document.body.classList.contains('detail-page') ? '../../' : document.getElementById('forum') ? '../' : ''; }
  function forumAdresi(q) { return kok() + 'forum/' + (q || ''); }
  function kat(kod) { for (var i = 0; i < KATEGORILER.length; i++) if (KATEGORILER[i].kod === kod) return KATEGORILER[i]; return { kod: kod, ad: kod || '' }; }

  /* ---------- giriş ---------- */
  var girisSonrasi = null;
  function girisKutusu(neden) {
    var eski = document.getElementById('fr-giris');
    if (eski) eski.remove();
    var kutu = el('<div class="fr-perde" id="fr-giris" role="dialog" aria-modal="true" aria-labelledby="fr-giris-bas"><div class="fr-kutu">'
      + '<button type="button" class="fr-kapat" aria-label="Kapat">×</button>'
      + '<div class="fr-kutu-ust">' + ikon(SOHBET) + '</div>'
      + '<h2 id="fr-giris-bas">' + esc(neden || 'Sohbete katıl') + '</h2><p class="fr-not">Telegram hesabınla tek dokunuşla girersin. Sitede yalnızca seçtiğin rumuz görünür; adın ve telefonun görünmez.</p>'
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
      bildir('Hoş geldin, ' + j.uye.rumuz + '!');
      var f = girisSonrasi; girisSonrasi = null;
      if (f) f(); else yenile();
    }
    function rumuzForm(etiket, ipucu, not, yol, govdeYap) {
      alan.innerHTML = '<form class="fr-form"><label for="fr-rumuz">' + etiket + '</label><input id="fr-rumuz" maxlength="20" autocomplete="nickname" required placeholder="' + ipucu + '">'
        + '<small class="fr-not">' + not + '</small><button class="btn btn-ana" type="submit">Devam et</button></form>';
      var f = alan.querySelector('form'), g = f.querySelector('input');
      g.focus();
      f.onsubmit = function (e) {
        e.preventDefault(); hata('');
        api(yol, { yontem: 'POST', govde: govdeYap(g.value.trim()) }).then(girdi, function (h) { hata(h.message); });
      };
    }
    function rumuzSor(gecici) {
      kutu.querySelector('h2').textContent = 'Sana ne diyelim?';
      rumuzForm('Rumuzun', 'ör. memuradayi35', '3–20 karakter: harf, rakam, nokta, alt çizgi. Sonradan değişmez.', '/giris/rumuz', function (r) { return { gecici: gecici, rumuz: r }; });
    }
    if (YEREL) rumuzForm('Deneme rumuzu', 'ör. deneme1', 'Yalnız yerel denemede; canlıda burada Telegram düğmesi çıkar.', '/giris/deneme', function (r) { return { rumuz: r }; });
    else {
      window.frTelegram = function (k) { hata(''); api('/giris/telegram', { yontem: 'POST', govde: k }).then(girdi, function (h) { hata(h.message); }); };
      var s = document.createElement('script');
      s.async = true; s.src = 'https://telegram.org/js/telegram-widget.js?22';
      s.setAttribute('data-telegram-login', BOT); s.setAttribute('data-size', 'large'); s.setAttribute('data-radius', '10');
      s.setAttribute('data-onauth', 'frTelegram(user)'); s.setAttribute('data-request-access', 'write');
      alan.appendChild(s);
    }
  }
  function girisGerekli(neden, sonra) { if (oturum()) return false; girisSonrasi = sonra || null; girisKutusu(neden); return true; }

  /* ---------- mesajlar (ilan sayfası ve başlık görünümü ortak) ---------- */
  // baglam 'ilan': kök insan mesajları sorudur ("Ben de merak ediyorum"), cevabı yoksa "Yanıt bekliyor" görünür.
  function yanitHtml(y, cocuk, baglam, cevapli, yeni) {
    var soru = baglam === 'ilan' && !cocuk && insanMi(y);
    var ben = y.benim || (uye() && uye().rumuz === y.rumuz);
    var oyEt = (soru ? 'Ben de merak ediyorum' : 'Faydalı') + (y.faydali ? ' · ' + sayi(y.faydali) : '');
    return '<article class="fr-yanit' + (cocuk ? ' fr-cocuk' : '') + (y.rol === 'asistan' ? ' fr-yanit-bot' : '') + (ben ? ' fr-benim' : '') + (yeni ? ' fr-yeni' : '') + '" id="y' + y.id + '">'
      + avatar(y) + '<div class="fr-yanit-ic"><header><b>' + esc(y.rumuz) + '</b>' + rozetler(y) + (ben ? '<span class="fr-rozet fr-sen-r">Sen</span>' : '')
      + '<time datetime="' + new Date(y.olusma * 1000).toISOString() + '">' + zaman(y.olusma) + '</time>'
      + (soru && !cevapli ? '<span class="fr-bekliyor">Yanıt bekliyor</span>' : '') + '</header>'
      + '<div class="fr-govde">' + metin(y.govde) + '</div>'
      + '<footer>' + (ben ? '' : '<button type="button" class="fr-eylem" data-faydali="' + y.id + '" data-soru="' + (soru ? 1 : 0) + '" aria-pressed="' + (y.oyladim ? 'true' : 'false') + '">' + oyEt + '</button>')
      + (cocuk ? '' : '<button type="button" class="fr-eylem" data-yanitla="' + y.id + '" data-rumuz="' + esc(y.rumuz) + '" data-rol="' + esc(y.rol) + '">' + (soru && !cevapli ? 'Cevapla' : 'Yanıtla') + '</button>')
      + (insanMi(y) && !ben ? '<button type="button" class="fr-eylem fr-sik" data-sikayet="' + y.id + '">Bildir</button>' : '')
      + '</footer></div></article>';
  }
  function yanitListesi(yanitlar, baglam, gorulen) {
    var koke = [], alt = {}, bilinen = {};
    yanitlar.forEach(function (y) { if (y.ust_id) (alt[y.ust_id] = alt[y.ust_id] || []).push(y); else koke.push(y); });
    koke.forEach(function (y) { bilinen[y.id] = 1; });
    Object.keys(alt).forEach(function (u) { if (!bilinen[u]) { koke = koke.concat(alt[u]); delete alt[u]; } });
    koke.sort(function (a, b) { return a.id - b.id; });
    function yeni(y) { return gorulen && y.id > gorulen; }
    return koke.map(function (y) {
      var c = alt[y.id] || [], cevapli = c.some(function (x) { return insanMi(x) || x.rol === 'asistan'; });
      return yanitHtml(y, false, baglam, cevapli, yeni(y)) + c.map(function (x) { return yanitHtml(x, true, baglam, true, yeni(x)); }).join('');
    }).join('');
  }
  function katilimcilar(yanitlar) {
    var g = {}, l = [];
    yanitlar.forEach(function (y) { if (insanMi(y) && !g[y.rumuz]) { g[y.rumuz] = 1; l.push(y); } });
    return l;
  }
  function yuzler(l, en) {
    return '<span class="fr-yuzler" aria-hidden="true">' + l.slice(0, en || 5).map(function (k) { return avatar(k, true); }).join('') + '</span>';
  }

  function yaziciHtml(yer, ipucu, hizli) {
    var u = uye();
    return '<form class="fr-yazici" data-yer="' + yer + '">'
      + (hizli ? '<div class="fr-hizli" aria-label="Hazır sorular">' + hizli.map(function (s) { return '<button type="button" class="fr-cip" data-hizli>' + esc(s) + '</button>'; }).join('') + '</div>' : '')
      + '<div class="fr-yanitlanan" hidden><span></span><button type="button" class="fr-eylem" data-iptal>Vazgeç</button></div>'
      + '<div class="fr-yazici-ic">' + (u ? avatar(u) : '<span class="fr-av fr-av-bos" aria-hidden="true">' + ikon('M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5') + '</span>')
      + '<label class="sr-only" for="fr-metin-' + yer + '">Mesajın</label><textarea id="fr-metin-' + yer + '" rows="1" maxlength="2000" placeholder="' + esc(ipucu) + '"></textarea>'
      + '<button type="submit" class="fr-gonder" aria-label="Gönder">' + ikon('M5 12h13M13 6l6 6-6 6') + '</button></div>'
      + '<p class="fr-hata" role="alert" hidden></p>'
      + '<p class="fr-yazici-not">' + (u ? esc(u.rumuz) + ' olarak yazıyorsun · ' : 'Göndermek için Telegram ile girersin · ') + 'kimlik no ve telefon paylaşma</p></form>';
  }
  function yaziciBagla(kap, anahtar, gonder) {
    var f = kap.querySelector('.fr-yazici');
    if (!f) return;
    var ust = null, ta = f.querySelector('textarea'), etiket = f.querySelector('.fr-yanitlanan');
    var taslakAd = 'fr-taslak-' + anahtar;
    ta.value = oku(taslakAd) || '';
    function boy() { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight + 2, 220) + 'px'; ta.style.overflowY = ta.scrollHeight > 218 ? 'auto' : 'hidden'; f.classList.toggle('fr-dolu', !!ta.value.trim()); }
    boy();
    ta.addEventListener('input', function () { yaz(taslakAd, ta.value || null); boy(); });
    function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
    f.querySelector('[data-iptal]').onclick = function () { ust = null; etiket.hidden = true; };
    f.addEventListener('click', function (e) {
      var c = e.target.closest('[data-hizli]');
      if (!c) return;
      ta.value = c.textContent; yaz(taslakAd, ta.value); boy(); ta.focus();
      iz('forum_hizli_soru');
    });
    kap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-yanitla]');
      if (!b) return;
      ust = +b.getAttribute('data-yanitla');
      etiket.querySelector('span').textContent = '@' + b.getAttribute('data-rumuz') + ' kişisine yanıt';
      etiket.hidden = false;
      var an = '@' + b.getAttribute('data-rumuz') + ' ';
      if (insanMi({ rol: b.getAttribute('data-rol') }) && ta.value.indexOf(an) !== 0) { ta.value = an + ta.value; boy(); }
      ta.focus();
    });
    ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) f.requestSubmit ? f.requestSubmit() : f.onsubmit(e); });
    f.onsubmit = function (e) {
      if (e && e.preventDefault) e.preventDefault();
      hata('');
      var g = ta.value.trim();
      if (g.length < 2) { ta.focus(); return hata('Önce mesajını yaz.'); }
      if (girisGerekli('Mesajın hazır, göndermek için katıl', function () { yenile(); setTimeout(function () { var y = document.querySelector('.fr-yazici[data-yer="' + f.getAttribute('data-yer') + '"]'); if (y) (y.requestSubmit ? y.requestSubmit() : y.onsubmit()); }, 400); })) return;
      var d = f.querySelector('[type=submit]'); d.disabled = true; f.classList.add('fr-gidiyor');
      gonder(g, ust).then(function () { ta.value = ''; yaz(taslakAd, null); ust = null; etiket.hidden = true; boy(); }, function (h) { hata(h.message); })
        .then(function () { d.disabled = false; f.classList.remove('fr-gidiyor'); });
    };
  }
  function eylemleriBagla(kap, sonra) {
    kap.addEventListener('click', function (e) {
      var f = e.target.closest('[data-faydali]'), s = e.target.closest('[data-sikayet]');
      if (f) {
        if (girisGerekli('Katılmak için giriş yap')) return;
        api('/yanit/' + f.getAttribute('data-faydali') + '/faydali', { yontem: 'POST', govde: {} }).then(function (j) {
          f.setAttribute('aria-pressed', String(!!j.oyladim));
          f.textContent = (f.getAttribute('data-soru') === '1' ? 'Ben de merak ediyorum' : 'Faydalı') + (j.faydali ? ' · ' + sayi(j.faydali) : '');
          if (j.oyladim) f.classList.add('fr-pit');
          setTimeout(function () { f.classList.remove('fr-pit'); }, 500);
        }, function (h) { bildir(h.message); });
      } else if (s) {
        if (girisGerekli('Bildirmek için giriş yap')) return;
        if (!confirm('Bu mesajı kurallara aykırı diye bildirmek istiyor musun?')) return;
        api('/yanit/' + s.getAttribute('data-sikayet') + '/sikayet', { yontem: 'POST', govde: {} }).then(function () {
          s.textContent = 'Bildirildi'; s.disabled = true; if (sonra) sonra();
        }, function (h) { bildir(h.message); });
      }
    });
  }
  // Sekme açıkken yeni mesajları kendiliğinden getirir (önbellekli okuma; 45 sn).
  function canliTut(f) {
    var t = setInterval(function () { if (document.visibilityState === 'visible') f(true); }, 45000);
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') f(true); });
    return function () { clearInterval(t); };
  }

  /* ---------- ilan sayfası ---------- */
  function ilanBolumu(kap) {
    var ilan = kap.getAttribute('data-ilan'), ad = kap.getAttribute('data-ad') || 'Bu ilan', acik = kap.getAttribute('data-acik') === '1';
    var sonId = 0, baslikId = null, ilkYukleme = true;
    kap.innerHTML = '<div class="fr-ilan">'
      + '<header class="fr-ilan-bas"><div><h2>' + ikon(SOHBET) + '<span data-baslik>Bu ilan hakkında konuşalım</span></h2><p class="fr-canli" data-canli>Sorunu yaz; başvuranlar ve otomatik yanıt cevaplar.</p></div><span data-yuzler></span></header>'
      + '<div class="fr-basvuru" aria-live="polite"></div>'
      + '<div class="fr-liste" aria-live="polite"></div>'
      + yaziciHtml('ilan', 'Bu ilanla ilgili sorunu yaz…', HIZLI_SORULAR)
      + '<p class="fr-forum-bag"><a class="yazi-link" href="' + forumAdresi() + '">Forumda diğer konular →</a></p></div>';
    var liste = kap.querySelector('.fr-liste'), bas = kap.querySelector('.fr-basvuru');

    function basvuruCiz(b) {
      b = b || { sayi: 0 };
      var benim = basvurularim()[ilan];
      var dugme = acik || benim
        ? '<button type="button" class="fr-basvurdum' + (benim ? ' fr-on' : '') + '" data-basvurdum aria-pressed="' + (benim ? 'true' : 'false') + '">'
          + ikon(benim ? 'M5 12.5l4.5 4.5L19 7.5' : 'M12 5v14M5 12h14') + (benim ? 'Başvurdum' : 'Ben de başvurdum') + '</button>'
        : '<span class="fr-not">Başvuru süresi bitti</span>';
      var yazi = b.sayi
        ? '<b>' + sayi(b.sayi) + '</b> kişi bu ilana başvurduğunu söyledi' + (benim ? ', sen de aralarındasın.' : '.')
        : (acik ? 'Başvurduysan işaretle; kaç kişinin başvurduğu herkese görünsün.' : 'Bu ilana başvuran işaretlenmedi.');
      var h = '<div class="fr-basvuru-ust"><p class="fr-sayac">' + yazi + '</p>' + dugme + '</div>';
      if (b.puan) {
        var p = b.puan, en = p.en_dusuk, ek = p.en_yuksek, ara = Math.max(ek - en, 0.01);
        var yz = function (x) { return ((x - en) / ara * 100).toFixed(1) + '%'; };
        h += '<div class="fr-dagilim"><p><b>' + esc(p.puan_turu) + '</b> puanını paylaşan ' + sayi(p.adet) + ' kişi · ortanca <b>' + esc(p.medyan) + '</b></p>'
          + '<div class="fr-cubuk" aria-hidden="true"><span class="fr-kutu-c" style="left:' + yz(p.ceyrek1) + ';width:calc(' + yz(p.ceyrek3) + ' - ' + yz(p.ceyrek1) + ')"></span>'
          + '<span class="fr-medyan" style="left:' + yz(p.medyan) + '"></span>'
          + (benim && benim.puan && benim.puan_turu === p.puan_turu ? '<span class="fr-sen" style="left:' + yz(Math.min(Math.max(benim.puan, en), ek)) + '"><i>Sen</i></span>' : '') + '</div>'
          + '<div class="fr-uclar"><span>' + esc(en) + '</span><span>' + esc(ek) + '</span></div>'
          + (p.sira ? '<p class="fr-not">Paylaşanlar arasında ' + sayi(p.sira) + '. sıradasın.</p>' : '')
          + '<p class="fr-not">Gönüllü paylaşılan puanlar; resmî taban puanı değildir.</p></div>';
      } else if (b.sayi && (!benim || benim.puan)) {
        h += '<p class="fr-not fr-ara">Puanını paylaşan 5 kişi olunca başvuranların puan dağılımı burada görünür.</p>';
      }
      if (benim && !benim.puan) {
        h += '<form class="fr-puan"><span>Puanını anonim ekle, kaçıncı sırada olduğunu gör:</span><span class="fr-puan-g"><select aria-label="Puan türü">' + PUAN_TURLERI.map(function (t) { return '<option>' + t + '</option>'; }).join('') + '</select>'
          + '<input type="text" inputmode="decimal" placeholder="ör. 78,45" aria-label="Puan" required><button class="btn btn-ana" type="submit">Ekle</button></span></form>';
      }
      bas.innerHTML = h;
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
        iz('forum_basvurdum', puan ? 'puan' : '');
        bildir(puan ? 'Puanın eklendi, teşekkürler.' : 'Bol şans! Sorun olursa aşağıya yaz.');
        basvuruCiz(j.basvuru);
      }, function (h) { bildir(h.message); });
    }
    bas.addEventListener('click', function (e) {
      if (!e.target.closest('[data-basvurdum]')) return;
      if (basvurularim()[ilan]) {
        if (!confirm('Başvurdum işaretini kaldırmak istiyor musun?')) return;
        api('/basvuru/' + encodeURIComponent(ilan) + '?kimlik=' + kimlik(), { yontem: 'DELETE' }).then(function (j) {
          var m = basvurularim(); delete m[ilan]; yaz('fr-basvuru', m); basvuruCiz(j.basvuru);
        }, function (h) { bildir(h.message); });
      } else basvur(null);
    });

    function ustBilgi(y) {
      var insan = y.filter(insanMi), kisiler = katilimcilar(y);
      var son = y.length ? y[y.length - 1].olusma : 0;
      kap.querySelector('[data-baslik]').textContent = insan.length ? 'Bu ilan hakkında konuşanlar' : 'Bu ilan hakkında konuşalım';
      kap.querySelector('[data-canli]').innerHTML = insan.length
        ? (Date.now() / 1000 - son < 86400 ? '<i class="fr-nokta"></i>' : '') + sayi(kisiler.length) + ' kişi · ' + sayi(insan.length) + ' mesaj · son mesaj ' + zaman(son)
        : 'İlk soruyu sen sor; başvuranlar ve otomatik yanıt cevaplar.';
      kap.querySelector('[data-yuzler]').innerHTML = kisiler.length ? yuzler(kisiler) : '';
      ctaGuncelle(insan.length);
    }
    function ciz(j, sessiz) {
      var y = j.yanitlar || [];
      var enBuyuk = y.reduce(function (a, x) { return Math.max(a, x.id); }, 0);
      if (sessiz && enBuyuk <= sonId) return;
      var yeniVar = sessiz && enBuyuk > sonId;
      liste.innerHTML = y.length ? yanitListesi(y, 'ilan', ilkYukleme ? 0 : sonId) : '';
      if (yeniVar) bildir('Yeni mesaj geldi');
      sonId = enBuyuk; ilkYukleme = false;
      if (j.baslik && j.baslik.id) baslikId = j.baslik.id;
      ustBilgi(y);
      if (!sessiz) basvuruCiz(j.basvuru);
    }
    function yukle(sessiz) {
      var k = basvurularim()[ilan] ? '?kimlik=' + kimlik() : '';   // kimliksiz okuma önbellekten gelir
      return api('/ilan/' + encodeURIComponent(ilan) + k).then(function (j) { ciz(j, sessiz === true); }, function () {
        if (sessiz !== true) bas.innerHTML = '<p class="fr-not">Konuşma şu an yüklenemedi.</p>';
      });
    }
    function gonder(g, ust) {
      var istek = ust && baslikId   // bir mesaja yanıt: başlık zaten var
        ? api('/baslik/' + baslikId + '/yanit', { yontem: 'POST', govde: { govde: g, ust_id: ust } })
        : api('/ilan/' + encodeURIComponent(ilan) + '/yanit', { yontem: 'POST', govde: { govde: g, ilan_baslik: ad } });
      return istek.then(function () { iz('forum_yanit', 'ilan'); return yukle(); });
    }
    yaziciBagla(kap, 'ilan-' + ilan, gonder);
    eylemleriBagla(kap, yukle);
    yenileyiciler.push(function () {   // girişten sonra yazma kutusu rumuzla yeniden çizilir (taslak korunur)
      var y = kap.querySelector('.fr-yazici');
      if (y) { y.replaceWith(el(yaziciHtml('ilan', 'Bu ilanla ilgili sorunu yaz…', HIZLI_SORULAR))); yaziciBagla(kap, 'ilan-' + ilan, gonder); }
      return yukle();
    });
    canliTut(yukle);
    yuzenDugme(kap);
    yukle();
  }
  // Üstteki "Soru sor" düğmesi ve sayfa kayarken beliren yüzen düğme: ikisi de konuşmaya götürür ve yazma kutusunu açar.
  var ctaSayi = 0;
  function ctaGuncelle(n) {
    ctaSayi = n;
    document.querySelectorAll('[data-fr-cta]').forEach(function (s) { s.textContent = n ? sayi(n) + ' mesaj · Soru sor' : 'Soru sor'; });
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
    var b = el('<button type="button" class="fr-yuzen" hidden>' + ikon(SOHBET) + '<span data-fr-cta>Soru sor</span></button>');
    b.onclick = konusmayaGit;
    document.body.appendChild(b);
    ctaGuncelle(ctaSayi);
    if (!('IntersectionObserver' in window)) return;
    var gorunur = { t: false, c: true }, cta = document.querySelector('a.fr-cta');
    function karar() { b.hidden = gorunur.t || gorunur.c; }
    new IntersectionObserver(function (g) { gorunur.t = g[0].isIntersecting; karar(); }, { rootMargin: '0px 0px -30% 0px' }).observe(kap);
    if (cta) new IntersectionObserver(function (g) { gorunur.c = g[0].isIntersecting || g[0].boundingClientRect.top > 0; karar(); }).observe(cta);
    else gorunur.c = false;
  }

  /* ---------- forum sayfası ---------- */
  var DUZEYLER = [{ kod: 'lisans', ad: 'Lisans' }, { kod: 'onlisans', ad: 'Önlisans' }, { kod: 'ortaogretim', ad: 'Ortaöğretim' }, { kod: 'ekpss', ad: 'EKPSS' }, { kod: 'agrubu', ad: 'A Grubu' }];
  var SIRALAR = [{ kod: 'son', ad: 'Son konuşulan' }, { kod: 'yeni', ad: 'Yeni' }, { kod: 'populer', ad: 'Popüler' }, { kod: 'begenilen', ad: 'En beğenilen' }];
  var SIK_ARANANLAR = ['eş durumu tayini', '4/B sözleşmeli', 'yaş sınırı', 'mülakat', 'güvenlik soruşturması', 'puanım yanar mı'];
  function duzeyAd(k) { for (var i = 0; i < DUZEYLER.length; i++) if (DUZEYLER[i].kod === k) return DUZEYLER[i].ad; return ''; }
  function puanYazi(b) { return b.puan_turu && b.puan != null ? esc(b.puan_turu) + ' · ' + String(b.puan).replace('.', ',') : ''; }
  function etiketler(b, yeni) {
    return (b.sabit ? '<span class="fr-etiket fr-sabit">Sabit</span>' : '')
      + (b.duzey ? '<span class="fr-etiket fr-duzey fr-d-' + esc(b.duzey) + '">' + esc(duzeyAd(b.duzey)) + '</span>' : '')
      + '<span class="fr-etiket">' + esc(kat(b.kategori).ad) + '</span>'
      + (b.anket ? '<span class="fr-etiket fr-anket-e">Anket</span>' : '')
      + (puanYazi(b) ? '<span class="fr-etiket fr-puan-e">' + puanYazi(b) + '</span>' : '')
      + (b.kaynak === 'telegram' ? '<span class="fr-etiket fr-tg">Telegram\'dan gelen soru</span>' : '')
      + (yeni ? '<span class="fr-etiket fr-yeni-e">Yeni</span>' : '');
  }
  function paylasHtml(baslik, adres) {
    var u = encodeURIComponent(adres), m = encodeURIComponent(baslik + ' ' + adres);
    return '<div class="fr-paylas"><span class="fr-not">Paylaş:</span>'
      + '<a class="fr-cip" href="https://wa.me/?text=' + m + '" target="_blank" rel="noopener">WhatsApp</a>'
      + '<a class="fr-cip" href="https://t.me/share/url?url=' + u + '&text=' + encodeURIComponent(baslik) + '" target="_blank" rel="noopener">Telegram</a>'
      + '<button type="button" class="fr-cip" data-kopyala="' + esc(adres) + '">Bağlantıyı kopyala</button></div>';
  }
  // Puan özeti: ilk mesajda düzey + puan varsa sitenin ÖSYM taban puanı verisinden tarayıcıda hesaplanır (sunucuya yük yok).
  var puanVerisi = {};
  function puanOzeti(kap, b) {
    if (!b.puan || !/^(lisans|onlisans|ortaogretim)$/.test(b.duzey || '')) return;
    var yer = kap.querySelector('[data-puan-ozet]');
    if (!yer) return;
    (puanVerisi[b.duzey] = puanVerisi[b.duzey] || fetch('../puanlar/' + b.duzey + '.json').then(function (r) { return r.json(); })).then(function (v) {
      var donem = Object.keys(v.donemler || {}).sort().pop();
      if (!donem) return;
      var satir = v.donemler[donem], uyan = satir.filter(function (s) { return s.min != null && s.min <= b.puan; });
      var unvan = {};
      uyan.forEach(function (s) { unvan[s.unvan] = (unvan[s.unvan] || 0) + (s.yerlesen || 1); });
      var enCok = Object.keys(unvan).sort(function (a, c) { return unvan[c] - unvan[a]; }).slice(0, 5);
      var toplam = satir.reduce(function (a, s) { return a + (s.yerlesen || 0); }, 0), alt = uyan.reduce(function (a, s) { return a + (s.yerlesen || 0); }, 0);
      yer.innerHTML = '<div class="fr-puan-ozet"><header><b>' + esc(v.ad) + ' ' + String(b.puan).replace('.', ',') + ' puanına göre</b><span class="fr-rozet fr-sistem">Site verisi</span></header>'
        + '<p>' + esc(donem.replace('-', '/')) + ' yerleştirmesinde en düşük puanı <b>' + String(b.puan).replace('.', ',') + '</b> ve altında kalan <b>' + sayi(uyan.length) + '</b> kadro vardı'
        + (toplam ? ' (yerleşenlerin yaklaşık %' + Math.round(alt / toplam * 100) + '\'i).' : '.') + '</p>'
        + (enCok.length ? '<ul>' + enCok.map(function (u) { return '<li>' + esc(u.charAt(0) + u.slice(1).toLocaleLowerCase('tr-TR')) + ' <small>' + sayi(unvan[u]) + ' kişi</small></li>'; }).join('') + '</ul>' : '')
        + '<p class="fr-not">Bölüm (nitelik) koşulu hesaba katılmadı. Bölümüne uyan kadroları görmek için <a href="../puanlar/">tercih robotunu</a> kullan.</p></div>';
    }, function () {});
  }
  function anketHtml(a, acik) {
    if (!a) return '';
    var oyVer = acik && a.benim == null;
    return '<div class="fr-anket" data-anket><b class="fr-anket-bas">Anket · ' + sayi(a.toplam) + ' oy</b>' + a.secenekler.map(function (s) {
      var y = a.toplam ? Math.round(s.oy / a.toplam * 100) : 0;
      return oyVer
        ? '<button type="button" class="fr-anket-s" data-oy="' + s.sira + '"><span>' + esc(s.metin) + '</span></button>'
        : '<div class="fr-anket-s fr-sonuc' + (a.benim === s.sira ? ' fr-on' : '') + '"><i style="width:' + y + '%"></i><span>' + esc(s.metin) + (a.benim === s.sira ? ' ✓' : '') + '</span><b>%' + y + '</b></div>';
    }).join('') + (oyVer ? '<p class="fr-not">Sonuçları görmek için oy ver.</p>' : '') + '</div>';
  }

  function forumSayfasi(kok_) {
    var oncekiZiyaret = oku('fr-son-ziyaret') || 0;
    yaz('fr-son-ziyaret', Math.floor(Date.now() / 1000));
    var durdur = null;
    function git(q) { history.pushState(null, '', q || location.pathname); ciz(); window.scrollTo(0, 0); }
    function adres(p) {   // mevcut süzgeçleri koruyarak liste adresi
      var q = new URLSearchParams(location.search), s = new URLSearchParams();
      ['k', 'd', 's', 'bekleyen'].forEach(function (a) { var v = a in p ? p[a] : q.get(a); if (v) s.set(a, v); });
      var t = s.toString(); return t ? '?' + t : '?';
    }
    kok_.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-ic]');
      if (a && !e.metaKey && !e.ctrlKey) { e.preventDefault(); git(a.getAttribute('href')); return; }
      var k = e.target.closest('[data-kopyala]');
      if (k) { try { navigator.clipboard.writeText(k.getAttribute('data-kopyala')); bildir('Bağlantı kopyalandı'); } catch (x) {} }
    });
    window.addEventListener('popstate', ciz);

    function profilCubugu() {
      var u = uye();
      if (!u) return '';
      return '<div class="fr-profil">' + avatar(u) + '<span><b>' + esc(u.rumuz) + '</b>' + rozetler(u) + '</span>'
        + '<label class="fr-bildirim"><input type="checkbox" data-bildirim' + (u.bildirim === 0 ? '' : ' checked') + '> Yanıt gelince Telegram\'dan haber ver</label>'
        + '<button type="button" class="fr-eylem" data-cikis>Çıkış</button></div>';
    }
    function aramaKutusu(q) {
      return '<form class="fr-ara" role="search"><span class="fr-ara-ic">' + ikon('M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4') + '<input type="search" name="q" maxlength="60" placeholder="Forumda ara: tayin, 4/B, mülakat…" value="' + esc(q || '') + '" aria-label="Forumda ara"></span><button class="btn btn-ana" type="submit">Ara</button></form>'
        + '<div class="fr-sik-aranan"><span class="fr-not">Sık arananlar:</span>' + SIK_ARANANLAR.map(function (s) { return '<a class="fr-cip" data-ic href="?q=' + encodeURIComponent(s) + '">' + esc(s) + '</a>'; }).join('') + '</div>';
    }
    function soruKutusu(kategori) {
      var u = uye();
      return '<a class="fr-sor" data-ic href="?yeni=1' + (kategori && kategori !== 'ilan' && kategori !== 'etkinlik' ? '&k=' + kategori : '') + '">'
        + (u ? avatar(u) : '<span class="fr-av fr-av-bos" aria-hidden="true">' + ikon('M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5') + '</span>')
        + '<span class="fr-sor-yazi">Aklındaki soruyu sor, anket aç ya da deneyimini anlat…</span><span class="btn btn-ana">Başlık aç</span></a>';
    }
    function basvurduklarim() {
      return Object.keys(basvurularim()).length ? '<section class="fr-yan-kart" data-benim hidden><h3>Başvurduğun ilanlar</h3><div data-benim-liste></div></section>' : '';
    }
    function basvurduklarimDoldur() {
      var k = kok_.querySelector('[data-benim]');
      if (!k) return;
      var m = basvurularim(), idler = Object.keys(m).slice(0, 30);
      api('/ozet?ilanlar=' + idler.map(encodeURIComponent).join(',')).then(function (o) {
        k.querySelector('[data-benim-liste]').innerHTML = idler.map(function (id) {
          var s = o[id] || {};
          return '<a class="fr-yan-satir" href="../ilan/' + encodeURIComponent(id) + '/#tartisma"><span>' + esc(m[id].ad || 'İlan') + '</span><small>'
            + [s.basvuru ? sayi(s.basvuru) + ' başvuran' : '', s.yanit ? sayi(s.yanit) + ' mesaj' : ''].filter(Boolean).join(' · ') + '</small></a>';
        }).join('');
        k.hidden = false;
      }, function () {});
    }
    // Yan sütun: gündem (son 24 saat), ilk yanıtı bekleyenler, konular (sayılarla), başvurduğun ilanlar. Hepsi /durum'dan, gerçek sayılar.
    function yanSutun() {
      return '<aside class="fr-yan">' + basvurduklarim()
        + '<section class="fr-yan-kart" data-gundem hidden><h3><i class="fr-nokta"></i>Gündem · son 24 saat</h3><div></div></section>'
        + '<section class="fr-yan-kart" data-ilk hidden><h3>İlk yanıtı sen yaz</h3><div></div></section>'
        + '<section class="fr-yan-kart"><h3>Konular</h3><nav class="fr-yan-katlar">' + KATEGORILER.map(function (c) {
          return '<a data-ic href="' + adres({ k: c.kod, bekleyen: '' }) + '">' + ikon(c.ik) + '<span>' + esc(c.ad) + '</span><small data-kat-sayi="' + c.kod + '"></small></a>';
        }).join('') + '</nav></section>'
        + '<section class="fr-yan-kart fr-kurallar-k"><h3>Forum kuralları</h3><ul><li>Kimlik no, telefon, e-posta paylaşma.</li><li>Kişileri değil konuyu tartış; kaba söz yok.</li><li>Bağlantılar yalnız resmî sitelere.</li><li>Otomatik yanıtlar rozetlidir; kesin bilgi resmî belgededir.</li></ul></section></aside>';
    }
    function durumDoldur() {
      api('/durum').then(function (d) {
        var s = kok_.querySelector('[data-serit]');
        if (s) {
          var p = [];
          if (d.bugun_mesaj) p.push('<span><i class="fr-nokta"></i>Son 24 saatte <b>' + sayi(d.bugun_mesaj) + '</b> mesaj, <b>' + sayi(d.bugun_yazar) + '</b> kişi yazdı</span>');
          if (d.uye) p.push('<span><b>' + sayi(d.uye) + '</b> üye</span>');
          if (d.kurucu_kalan > 0 && !uye()) p.push('<span class="fr-serit-kurucu">İlk 200 üyeye <b>Kurucu üye</b> rozeti · <b>' + sayi(d.kurucu_kalan) + '</b> yer kaldı</span>');
          if (p.length) { s.innerHTML = p.join(''); s.hidden = false; }
        }
        var kat_ = d.kategoriler || {};
        kok_.querySelectorAll('[data-kat-sayi]').forEach(function (x) { var n = kat_[x.getAttribute('data-kat-sayi')]; x.textContent = n ? sayi(n) : ''; });
        var bs = kok_.querySelector('[data-bekleyen-sayi]');
        if (bs && d.bekleyen) bs.textContent = sayi(d.bekleyen);
        function doldur(sec, l, alt) {
          var k = kok_.querySelector(sec);
          if (!k || !l || !l.length) return;
          k.querySelector('div').innerHTML = l.map(function (b) {
            return '<a class="fr-yan-satir" ' + (b.ilan_id ? 'href="../ilan/' + encodeURIComponent(b.ilan_id) + '/#tartisma"' : 'data-ic href="?b=' + b.id + '"') + '><span>' + esc(b.baslik) + '</span><small>' + alt(b) + '</small></a>';
          }).join('');
          k.hidden = false;
        }
        doldur('[data-gundem]', (d.gundem || []).filter(function (b) { return b.yanit_sayisi > 0; }),function (b) { return sayi(b.yanit_sayisi) + ' yanıt · ' + esc(kat(b.kategori).ad); });
        doldur('[data-ilk]', d.bekleyenler, function (b) { return esc(kat(b.kategori).ad) + ' · ' + zaman(b.olusma); });
      }, function () {});
    }
    function satir(b) {
      var yeni = oncekiZiyaret && (b.son_hareket || b.olusma) > oncekiZiyaret;
      var hedef = b.ilan_id ? '../ilan/' + encodeURIComponent(b.ilan_id) + '/#tartisma' : '?b=' + b.id;
      return '<a class="fr-satir' + (yeni ? ' fr-satir-yeni' : '') + '"' + (b.ilan_id ? '' : ' data-ic') + ' href="' + hedef + '">'
        + avatar(b) + '<span class="fr-satir-ic"><span class="fr-satir-ust">' + etiketler(b, yeni) + '</span>'
        + '<b class="fr-satir-bas">' + esc(b.baslik) + '</b>' + (b.kisa ? '<span class="fr-satir-kisa">' + esc(b.kisa) + '</span>' : '')
        + '<span class="fr-satir-alt">' + esc(b.rumuz || '') + rozetler(b) + ' · ' + zaman(b.son_hareket || b.olusma) + (b.faydali ? ' · ♥ ' + sayi(b.faydali) : '') + '</span></span>'
        + '<span class="fr-yanit-sayi' + (b.yanit_sayisi || b.sabit ? '' : ' fr-sifir') + '">' + ikon(SOHBET) + '<b>' + (b.yanit_sayisi || b.sabit ? sayi(b.yanit_sayisi) : 'Cevapla') + '</b></span></a>';
    }
    function liste(p) {
      var aramada = !!p.q;
      var ust = '<div class="fr-serit" data-serit hidden></div>' + aramaKutusu(p.q) + soruKutusu(p.k);
      var suzgec = aramada
        ? '<p class="fr-arama-bas">“' + esc(p.q) + '” için sonuçlar · <a class="yazi-link" data-ic href="?">Aramayı temizle</a></p>'
        : '<nav class="fr-kategoriler" aria-label="Bölümler"><a data-ic href="' + adres({ k: '', bekleyen: '' }) + '"' + (!p.k && !p.bekleyen ? ' aria-current="page"' : '') + '>Akış</a>'
          + '<a data-ic href="' + adres({ k: '', bekleyen: '1' }) + '" class="fr-sekme-bekleyen"' + (p.bekleyen ? ' aria-current="page"' : '') + '>Yanıt bekleyenler <b data-bekleyen-sayi></b></a>'
          + KATEGORILER.map(function (c) { return '<a data-ic href="' + adres({ k: c.kod, bekleyen: '' }) + '"' + (p.k === c.kod ? ' aria-current="page"' : '') + '>' + esc(c.ad) + '</a>'; }).join('') + '</nav>'
          + '<div class="fr-suzgec"><div class="fr-duzeyler" aria-label="Öğrenim düzeyi"><a data-ic href="' + adres({ d: '' }) + '"' + (!p.d ? ' aria-current="page"' : '') + '>Tüm düzeyler</a>'
          + DUZEYLER.map(function (d) { return '<a data-ic href="' + adres({ d: d.kod }) + '"' + (p.d === d.kod ? ' aria-current="page"' : '') + '>' + d.ad + '</a>'; }).join('') + '</div>'
          + '<div class="fr-siralar" aria-label="Sıralama">' + SIRALAR.map(function (s) { return '<a data-ic href="' + adres({ s: s.kod === 'son' ? '' : s.kod }) + '"' + ((p.s || 'son') === s.kod ? ' aria-current="page"' : '') + '>' + s.ad + '</a>'; }).join('') + '</div></div>';
      kok_.innerHTML = profilCubugu() + '<div class="fr-duzen"><div class="fr-ana">' + ust + suzgec + '<div class="fr-kart fr-basliklar"><p class="fr-yukleniyor">Yükleniyor…</p></div></div>' + yanSutun() + '</div>';
      durumDoldur(); basvurduklarimDoldur();
      var kap = kok_.querySelector('.fr-basliklar'), f = kok_.querySelector('.fr-ara');
      f.onsubmit = function (e) { e.preventDefault(); var q = f.querySelector('input').value.trim(); if (q.length >= 2) { iz('forum_ara'); git('?q=' + encodeURIComponent(q)); } };
      function getir(sayfa, ekle) {
        var yol = aramada ? '/ara?q=' + encodeURIComponent(p.q)
          : '/basliklar?kategori=' + encodeURIComponent(p.k || '') + '&sayfa=' + sayfa + (p.bekleyen ? '&bekleyen=1' : '') + (p.d ? '&duzey=' + p.d : '') + (p.s ? '&sirala=' + p.s : '');
        return api(yol).then(function (j) {
          var b = j.basliklar || [];
          var eski = kap.querySelector('.fr-daha'); if (eski) eski.remove();
          if (!ekle) kap.innerHTML = '';
          if (!b.length && !ekle) {
            kap.innerHTML = '<div class="fr-bos">' + (aramada ? '<b>Sonuç bulunamadı.</b><p>Sorunu yeni başlık olarak sor; bilen biri cevaplar.</p><a class="btn btn-ana" data-ic href="?yeni=1">Başlık aç</a>'
              : p.bekleyen ? '<b>Yanıtsız soru kalmadı.</b><p>Herkes cevabını almış görünüyor.</p>' : '<b>Burada ilk başlığı sen aç.</b><p>' + esc(p.k ? kat(p.k).ac : '') + '</p>') + '</div>';
          }
          kap.insertAdjacentHTML('beforeend', b.map(satir).join(''));
          if (j.sonraki && !aramada) {
            var d = el('<button type="button" class="btn btn-ikinci fr-daha">Daha fazla</button>');
            d.onclick = function () { d.disabled = true; getir(sayfa + 1, true); };
            kap.appendChild(d);
          }
        }, function (h) { kap.innerHTML = '<p class="fr-not">' + esc(h.message) + '</p>'; });
      }
      getir(1);
    }
    function baslik(id) {
      kok_.innerHTML = profilCubugu() + '<p class="fr-geri"><a class="yazi-link" data-ic href="?">← Forum</a></p><div class="fr-duzen"><div class="fr-ana"><div class="fr-kart fr-baslik"><p class="fr-yukleniyor">Yükleniyor…</p></div></div>' + yanSutun() + '</div>';
      durumDoldur(); basvurduklarimDoldur();
      var kap = kok_.querySelector('.fr-baslik'), sonId = 0, ilk = true;
      function yukle(sessiz) {
        return api('/baslik/' + id).then(function (j) {
          var b = j.baslik, y = j.yanitlar || [];
          var enBuyuk = y.reduce(function (a, x) { return Math.max(a, x.id); }, 0);
          if (sessiz === true) { if (enBuyuk <= sonId) return; bildir('Yeni yanıt geldi'); }
          document.title = b.baslik + ' — Forum — KPSS Tercihi';
          var kisiler = katilimcilar([b].concat(y)), benim = uye() && uye().rumuz === b.rumuz;
          if (!kap.querySelector('.fr-yazici')) {
            kap.innerHTML = '<header class="fr-baslik-bas"><span class="fr-satir-ust">' + etiketler(b) + '</span><h2>' + esc(b.baslik) + '</h2>'
              + '<p class="fr-canli" data-canli></p></header>'
              + (b.govde ? '<div class="fr-ilk">' + avatar(b) + '<div><header><b>' + esc(b.rumuz) + '</b>' + rozetler(b) + '<time>' + zaman(b.olusma) + '</time></header><div class="fr-govde">' + metin(b.govde) + '</div>'
                + '<div data-anket-yer></div><div data-puan-ozet></div>'
                + '<footer class="fr-ilk-alt">' + (benim || !insanMi(b) ? '' : '<button type="button" class="fr-eylem" data-baslik-oy aria-pressed="' + (b.oyladim ? 'true' : 'false') + '">♥ Faydalı' + (b.faydali ? ' · ' + sayi(b.faydali) : '') + '</button>')
                + '</footer></div></div>' : '')
              + (b.ilan_id ? '<p><a class="yazi-link" href="../ilan/' + encodeURIComponent(b.ilan_id) + '/#tartisma">İlan sayfasında aç →</a></p>' : '')
              + paylasHtml(b.baslik, location.origin + location.pathname + '?b=' + b.id)
              + '<div data-liste></div>' + yaziciHtml('baslik-' + id, y.length ? 'Sen de yaz… (@rumuz ile birini anabilirsin)' : 'İlk yanıtı sen yaz…');
            yaziciBagla(kap, 'baslik-' + id, function (g, ust) {
              var govde = { govde: g }; if (ust) govde.ust_id = ust;
              return api('/baslik/' + id + '/yanit', { yontem: 'POST', govde: govde }).then(function () { iz('forum_yanit', 'baslik'); return yukle(); });
            });
            puanOzeti(kap, b);
          }
          var ay = kap.querySelector('[data-anket-yer]');
          if (ay) ay.innerHTML = anketHtml(j.anket, true);
          kap.querySelector('[data-liste]').innerHTML = '<div class="fr-liste">' + yanitListesi(y, 'baslik', ilk ? 0 : sonId) + '</div>';
          kap.querySelector('[data-canli]').innerHTML = (y.length ? sayi(y.length) + ' yanıt · ' : 'Henüz yanıt yok · ') + sayi(kisiler.length) + ' kişi' + (kisiler.length ? ' ' + yuzler(kisiler, 6) : '');
          if (ilk && location.hash) { var h = document.getElementById(location.hash.slice(1)); if (h) h.scrollIntoView(); }
          sonId = enBuyuk; ilk = false;
        }, function (h) { if (sessiz !== true) kap.innerHTML = '<p class="fr-not">' + (h.durum === 404 ? 'Bu başlık bulunamadı ya da kaldırıldı.' : esc(h.message)) + '</p>'; });
      }
      kap.addEventListener('click', function (e) {
        var o = e.target.closest('[data-oy]'), bo = e.target.closest('[data-baslik-oy]');
        if (o) {
          if (girisGerekli('Oy vermek için katıl')) return;
          api('/baslik/' + id + '/anket', { yontem: 'POST', govde: { sira: +o.getAttribute('data-oy') } }).then(function (a) {
            kap.querySelector('[data-anket-yer]').innerHTML = anketHtml(a.anket || a, true); iz('forum_anket');
          }, function (h) { bildir(h.message); });
        } else if (bo) {
          if (girisGerekli('Katılmak için giriş yap')) return;
          api('/baslik/' + id + '/faydali', { yontem: 'POST', govde: {} }).then(function (j) {
            bo.setAttribute('aria-pressed', String(!!j.oyladim)); bo.textContent = '♥ Faydalı' + (j.faydali ? ' · ' + sayi(j.faydali) : '');
          }, function (h) { bildir(h.message); });
        }
      });
      eylemleriBagla(kap, yukle);
      yenileyiciler = [function () { kap.innerHTML = ''; ilk = true; return yukle(); }];
      durdur = canliTut(yukle);
      yukle();
    }
    function yeni(kategori) {
      var u = uye();
      var secenek = KATEGORILER.filter(function (c) { return c.kod !== 'ilan' && (c.kod !== 'etkinlik' || (u && (u.rol === 'yonetici' || u.rol === 'sistem'))); });
      var t = oku('fr-taslak-yeni') || {};
      var anketAcik = !!(t.anket && t.anket.length);
      function secim(ad, liste_, secili) {
        return '<div class="fr-secim" role="radiogroup">' + liste_.map(function (c) {
          var s = secili === c.kod;
          return '<label class="fr-secim-k' + (s ? ' fr-on' : '') + '">' + (c.ik ? ikon(c.ik) : '') + '<input type="radio" name="' + ad + '" value="' + c.kod + '"' + (s ? ' checked' : '') + '><span>' + esc(c.ad) + '</span></label>';
        }).join('') + '</div>';
      }
      kok_.innerHTML = profilCubugu() + '<p class="fr-geri"><a class="yazi-link" data-ic href="?">← Forum</a></p>'
        + '<form class="fr-kart fr-form fr-yeni"><h2>Ne sormak istersin?</h2><p class="fr-not">Düzeyini ve puanını eklersen daha isabetli cevap alırsın.</p>'
        + '<label>Konu</label>' + secim('kategori', secenek, t.kategori || kategori || 'puan')
        + '<label>Öğrenim düzeyin <small>(isteğe bağlı)</small></label>' + secim('duzey', [{ kod: '', ad: 'Belirtme' }].concat(DUZEYLER), t.duzey || '')
        + '<div class="fr-puan-alan"><label for="fr-pt">Puanın <small>(isteğe bağlı)</small></label><span class="fr-puan-g"><select id="fr-pt">' + PUAN_TURLERI.map(function (x) { return '<option' + (t.puan_turu === x ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select>'
        + '<input id="fr-p" type="text" inputmode="decimal" placeholder="ör. 71,96" value="' + esc(t.puan || '') + '"></span><small class="fr-not">Düzey ve puan yazarsan başlığında taban puanlarına göre bir özet otomatik görünür.</small></div>'
        + '<label for="fr-b">Başlık</label><input id="fr-b" maxlength="120" required placeholder="ör. Önlisans 72 puanla nerelere başvurabilirim?" value="' + esc(t.baslik || '') + '">'
        + '<label for="fr-g">Ayrıntı</label><textarea id="fr-g" rows="6" maxlength="4000" required placeholder="Bölümün, puan türün, şehir tercihin, aklına takılan…">' + esc(t.govde || '') + '</textarea>'
        + '<div class="fr-anket-alan"><label class="fr-anket-ac"><input type="checkbox" data-anket-ac' + (anketAcik ? ' checked' : '') + '> Anket ekle</label><div data-anket-secenek' + (anketAcik ? '' : ' hidden') + '>'
        + [0, 1, 2, 3, 4, 5].map(function (i) { return '<input class="fr-anket-g" maxlength="80" placeholder="Seçenek ' + (i + 1) + (i > 1 ? ' (isteğe bağlı)' : '') + '" value="' + esc((t.anket || [])[i] || '') + '">'; }).join('') + '</div></div>'
        + '<p class="fr-kurallar">Kimlik no, telefon, e-posta paylaşma · Kaba söz yok · Bağlantılar yalnız resmî sitelere · İlana özel soruyu ilan sayfasında sor.</p>'
        + '<div class="fr-yazici-alt"><span class="fr-not">' + (u ? esc(u.rumuz) + ' olarak açıyorsun' : 'Açarken Telegram ile girersin') + '</span><button class="btn btn-ana btn-buyuk" type="submit">Başlığı aç</button></div><p class="fr-hata" role="alert" hidden></p></form>';
      var f = kok_.querySelector('form');
      function deger() {
        var r = function (ad) { var x = f.querySelector('input[name=' + ad + ']:checked'); return x ? x.value : ''; };
        var p = String(f.querySelector('#fr-p').value).trim().replace(',', '.');
        var anket = f.querySelector('[data-anket-ac]').checked ? Array.prototype.map.call(f.querySelectorAll('.fr-anket-g'), function (x) { return x.value.trim(); }).filter(Boolean) : [];
        return { kategori: r('kategori') || 'puan', duzey: r('duzey'), puan_turu: f.querySelector('#fr-pt').value, puan: p, baslik: f.querySelector('#fr-b').value.trim(), govde: f.querySelector('#fr-g').value.trim(), anket: anket };
      }
      f.addEventListener('input', function () { yaz('fr-taslak-yeni', deger()); });
      f.addEventListener('change', function (e) {
        if (e.target.type === 'radio') f.querySelectorAll('.fr-secim-k').forEach(function (l) { l.classList.toggle('fr-on', l.querySelector('input').checked); });
        if (e.target.hasAttribute('data-anket-ac')) f.querySelector('[data-anket-secenek]').hidden = !e.target.checked;
        yaz('fr-taslak-yeni', deger());
      });
      function hata(m) { var p = f.querySelector('.fr-hata'); p.textContent = m || ''; p.hidden = !m; }
      f.onsubmit = function (e) {
        if (e && e.preventDefault) e.preventDefault();
        hata('');
        var g = deger(), govde = { kategori: g.kategori, baslik: g.baslik, govde: g.govde };
        if (g.baslik.length < 8) return hata('Başlık en az 8 karakter olmalı.');
        if (g.govde.length < 10) return hata('Biraz daha ayrıntı yaz (en az 10 karakter).');
        if (g.duzey) govde.duzey = g.duzey;
        if (g.puan) {
          var p = parseFloat(g.puan);
          if (!(p >= 40 && p <= 100)) return hata('Puan 40 ile 100 arasında olmalı.');
          govde.puan_turu = g.puan_turu; govde.puan = Math.round(p * 100) / 100;
        }
        if (f.querySelector('[data-anket-ac]').checked) {
          if (g.anket.length < 2) return hata('Anket için en az iki seçenek yaz.');
          govde.anket = { secenekler: g.anket };
        }
        if (girisGerekli('Başlığın hazır, açmak için katıl', function () { git('?yeni=1'); setTimeout(function () { var x = kok_.querySelector('form.fr-yeni'); if (x) (x.requestSubmit ? x.requestSubmit() : x.onsubmit()); }, 300); })) return;
        api('/baslik', { yontem: 'POST', govde: govde }).then(function (j) {
          yaz('fr-taslak-yeni', null); iz('forum_baslik', g.kategori); bildir('Başlığın açıldı');
          git('?b=' + j.baslik.id);
        }, function (h) { hata(h.message); });
      };
    }
    function ciz() {
      if (durdur) { durdur(); durdur = null; }
      var q = new URLSearchParams(location.search);
      document.title = 'Forum — KPSS Tercihi';
      yenileyiciler = [ciz];
      if (q.get('b')) baslik(+q.get('b'));
      else if (q.get('yeni')) yeni(q.get('k'));
      else liste({ k: q.get('k') || '', d: q.get('d') || '', s: q.get('s') || '', bekleyen: q.get('bekleyen') === '1', q: q.get('q') || '' });
    }
    kok_.addEventListener('click', function (e) { if (e.target.closest('[data-cikis]')) cikis(); });
    kok_.addEventListener('change', function (e) {
      var c = e.target.closest('[data-bildirim]');
      if (!c) return;
      api('/ben/bildirim', { yontem: 'POST', govde: { acik: c.checked } }).then(function () {
        var u = uye(); if (u) { u.bildirim = c.checked ? 1 : 0; yaz('fr-uye', u); }
        bildir(c.checked ? 'Yanıt gelince haber vereceğiz.' : 'Bildirimler kapandı.');
      }, function (h) { c.checked = !c.checked; bildir(h.message); });
    });
    ciz();
  }

  /* ---------- ana sayfa: konuşulan ilanlara mesaj rozeti ---------- */
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
          if (!s || !(s.yanit || s.basvuru)) return;
          (parti[k] || []).forEach(function (a) {
            var t = [];
            if (s.yanit) t.push(sayi(s.yanit) + ' mesaj');
            if (s.basvuru) t.push(sayi(s.basvuru) + ' başvuran');
            a.parentNode.insertAdjacentHTML('beforeend', '<a class="fr-liste-rozet" href="ilan/' + encodeURIComponent(k) + '/#tartisma" title="İlan hakkında konuşma">' + ikon(SOHBET) + esc(t.join(' · ')) + '</a>');
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
