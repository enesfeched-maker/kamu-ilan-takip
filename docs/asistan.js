/* KPSS Tercihi — site asistanı (Kasım 2026).
   Sayfa açılışında yalnız sağ alttaki "Soru sor" düğmesi çizilir (stili bu dosyada, ~1 KB). Panel ve docs/asistan.css ilk açılışta yüklenir.
   Sunucu: bildirim-botu Worker'ı, POST /asistan/sor {soru, sayfa} -> {metin, baglantilar, ilanlar, oneriler, kid};
   kid varsa cevabın altında "İşine yaradı mı?" sorulur ve POST /asistan/geri {kid, deger: 1|-1} gider.
   Güvenlik: sunucudan gelen her şey textContent ile yazılır; bağlantılar yalnız https://kpsstercihi.com/ ve https://t.me/ ile başlıyorsa çizilir.
   Konuşma sessionStorage'da tutulur (sayfalar arasında sürer, sekme kapanınca biter).
   Renk: Sanzo Wada #2 (lacivert #12354E + kehribar #F99D1B), docs/tasarim.css belirteçleri. */
(function () {
  'use strict';
  var w = window, d = document;
  if (w.kitAsistan) return;
  w.kitAsistan = 1;

  var ADRES = 'https://bildirim.kpsstercihi.com/asistan/sor';
  var SINIR = 300, SAYAC_ESIK = 250, ZAMAN_ASIMI = 10000, EN_COK_MESAJ = 40, ANAHTAR = 'kit-asistan';
  var HATA = 'Şu an bağlantıda bir sorun var. Biraz sonra tekrar dener misin?';
  var SELAM = 'Merhaba! İlanlar, taban puanları ya da başvuru adımlarıyla ilgili ne merak ediyorsan yazabilirsin.';
  var ILK_CIPLER = ['Puanımla nereye başvurabilirim?', 'KPSS\'siz alımlar var mı?', 'Kariyer Kapısı\'na nasıl başvurulur?'];
  var AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];

  function svg(p) { return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + p + '"/></svg>'; }
  var I_SOHBET = svg('M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20l1-4.3A7.5 7.5 0 1 1 20 12.5z');
  var I_KAPAT = svg('M6 6l12 12M18 6 6 18');
  var I_GONDER = svg('M12 19V5M5 12l7-7 7 7');
  var I_OK = svg('M5 12h14M13 6l6 6-6 6');

  var KUCUK_STIL = ''
    + '.as-ac{position:fixed;z-index:36;right:max(16px,calc(env(safe-area-inset-right,0px) + 12px));bottom:max(16px,calc(env(safe-area-inset-bottom,0px) + 12px));'
    + 'display:inline-flex;align-items:center;justify-content:center;gap:8px;height:48px;padding:0 18px 0 15px;border:0;border-radius:999px;'
    + 'background:var(--btn,#12354E);color:var(--btn-ink,#fff);font:600 15px/1 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;letter-spacing:-.005em;'
    + 'box-shadow:0 10px 28px -10px rgba(13,42,63,.55),0 1px 3px rgba(13,42,63,.18);cursor:pointer;-webkit-tap-highlight-color:transparent;transition:transform .15s}'
    + '.as-ac:hover{transform:translateY(-1px)}.as-ac:active{transform:scale(.97)}'
    + '.as-ac:focus-visible{outline:3px solid #F99D1B;outline-offset:3px}'
    + '.as-ac svg{width:20px;height:20px;fill:none;stroke:#F99D1B;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none}'
    + ':root[data-theme=dark] .as-ac svg{stroke:currentColor}'
    + '.as-ac[hidden],body.fr-konusmada .as-ac{display:none}'
    /* alt bilgi bağlantıları düğmenin altında kalmasın: koyu alt bilginin içinde boşluk (sayfanın en sonunda, kayma yaratmaz) */
    + '.ab::after{content:"";display:block;height:64px}'
    /* forumun telefondaki "Sorulara git" düğmesi görünürken simgeye küçül ve onun üstüne çık */
    + '@media (max-width:760px){body:has(.fr-yuzen:not([hidden])) .as-ac{bottom:calc(max(16px,calc(env(safe-area-inset-bottom,0px) + 12px)) + 56px);width:48px;padding:0}'
    + 'body:has(.fr-yuzen:not([hidden])) .as-ac span{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}}'
    + 'body:has(#compare-bar:not([hidden])) .as-ac{bottom:calc(max(16px,calc(env(safe-area-inset-bottom,0px) + 12px)) + 84px)}'
    + '@media (prefers-reduced-motion:reduce){.as-ac{transition:none}}'
    + '@media print{.as-ac{display:none!important}}';

  var betik = d.currentScript;
  var CSS_ADRES = betik && betik.src ? betik.src.replace(/asistan\.js(\?[^#]*)?(#.*)?$/, 'asistan.css$1') : '/asistan.css';

  function adres() {
    var h = location.hostname;
    if ((h === 'localhost' || h === '127.0.0.1') && typeof w.ASISTAN_ADRES === 'string' && w.ASISTAN_ADRES) return w.ASISTAN_ADRES;
    return ADRES;
  }
  function olc(a, x) { try { if (typeof w.kpssA === 'function') w.kpssA('tikla', { a: a, x: x }); } catch (e) { /* ölçüm sessiz */ } }

  /* ---------- depolama ---------- */
  function oku() {
    try {
      var o = JSON.parse(w.sessionStorage.getItem(ANAHTAR));
      if (o && Array.isArray(o.m)) return { m: o.m.filter(function (x) { return x && (x.r === 'k' || x.r === 'a') && typeof x.t === 'string'; }).map(function (x) {
        if (x.r === 'k') return { r: 'k', t: yazi(x.t, SINIR) };
        /* kayıtlı cevap da sunucu cevabı gibi yeniden süzülür (bozuk/elle değiştirilmiş depo çizimi bozmasın, bağlantı izni atlanmasın) */
        var c = temizle({ metin: x.t, kid: x.k,
          ilanlar: dizi(x.i).map(function (y) { y = y || {}; return { baslik: y.b, kurum: y.k, son_tarih: y.s, iller: y.il, url: y.u }; }),
          baglantilar: dizi(x.b).map(function (y) { y = y || {}; return { ad: y.a, url: y.u }; }),
          oneriler: x.o });
        if (x.g === 'e' || x.g === 'h') c.g = x.g;   /* geri bildirim verildi: tekrar sorulmaz */
        return c;
      }) };
    } catch (e) { /* yok ya da kapalı */ }
    return { m: [] };
  }
  function kaydet() {
    if (durum.m.length > EN_COK_MESAJ) durum.m = durum.m.slice(-EN_COK_MESAJ);
    try { w.sessionStorage.setItem(ANAHTAR, JSON.stringify(durum)); } catch (e) { /* depolama kapalı: konuşma yalnız bu sayfada kalır */ }
  }
  function sil() { try { w.sessionStorage.removeItem(ANAHTAR); } catch (e) { /* sessiz */ } }

  /* ---------- yardımcılar ---------- */
  function el(ad, sinif, yazi) {
    var e = d.createElement(ad);
    if (sinif) e.className = sinif;
    if (yazi != null) e.textContent = yazi;
    return e;
  }
  function yazi(x, n) { return typeof x === 'string' ? x.trim().slice(0, n) : ''; }
  function dizi(x) { return Array.isArray(x) ? x : []; }
  function guvenli(u) {
    return typeof u === 'string' && (u.indexOf('https://kpsstercihi.com/') === 0 || u.indexOf('https://t.me/') === 0) && !/[\s"<>]/.test(u) ? u : '';
  }
  function sonGun(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
    if (!m || +m[2] < 1 || +m[2] > 12) return '';
    return 'Son gün: ' + (+m[3]) + ' ' + AYLAR[+m[2] - 1] + (+m[1] !== new Date().getFullYear() ? ' ' + m[1] : '');
  }
  function temizle(j) {
    return {
      r: 'a',
      t: yazi(j.metin, 1500),
      k: typeof j.kid === 'number' && j.kid > 0 && j.kid % 1 === 0 ? j.kid : 0,
      i: dizi(j.ilanlar).slice(0, 5).map(function (x) {
        x = x || {};
        return { b: yazi(x.baslik, 200), k: yazi(x.kurum, 160), s: yazi(x.son_tarih, 10),
          il: dizi(x.iller).filter(function (y) { return typeof y === 'string' && y; }).slice(0, 6).map(function (y) { return y.slice(0, 40); }),
          u: guvenli(x.url) };
      }).filter(function (x) { return x.b; }),
      b: dizi(j.baglantilar).map(function (x) { x = x || {}; return { a: yazi(x.ad, 60), u: guvenli(x.url) }; })
        .filter(function (x) { return x.a && x.u; }).slice(0, 3),
      o: dizi(j.oneriler).map(function (x) { return yazi(x, 120); }).filter(Boolean).slice(0, 3)
    };
  }
  function bagla(a, u) {
    a.href = u;
    if (u.indexOf('https://t.me/') === 0) { a.target = '_blank'; a.rel = 'noopener'; }
  }

  /* ---------- düğme ---------- */
  var durum = oku(), buton, panel, perde, akis, form, alan, gonderD, yeniD, sayac;
  var acik = false, kuruldu = false, bekliyor = false, nesil = 0, kapanis = 0;
  var cssDurum = 0, cssBekleyen = [];

  function cssYukle(cb) {
    if (cb) cssBekleyen.push(cb);
    if (cssDurum === 2) return bitir();
    if (cssDurum === 1) return;
    cssDurum = 1;
    var l = d.createElement('link');
    l.rel = 'stylesheet';
    l.href = CSS_ADRES;
    var t = setTimeout(bitir, 3000);
    function bitir() { clearTimeout(t); cssDurum = 2; var c = cssBekleyen; cssBekleyen = []; c.forEach(function (f) { f(); }); }
    l.onload = l.onerror = bitir;
    d.head.appendChild(l);
  }

  function baslat() {
    var s = d.createElement('style');
    s.textContent = KUCUK_STIL;
    d.head.appendChild(s);
    buton = el('button', 'as-ac');
    buton.type = 'button';
    buton.setAttribute('aria-haspopup', 'dialog');
    buton.setAttribute('aria-expanded', 'false');
    buton.setAttribute('aria-label', 'Soru sor: KPSS Tercihi asistanı');
    buton.innerHTML = I_SOHBET + '<span>Soru sor</span>';
    buton.addEventListener('click', ac);
    ['pointerenter', 'touchstart', 'focus'].forEach(function (o) { buton.addEventListener(o, function () { cssYukle(); }, { passive: true, once: true }); });
    d.body.appendChild(buton);
  }

  /* ---------- panel ---------- */
  function kur() {
    if (kuruldu) return;
    kuruldu = true;
    perde = el('div', 'as-perde');
    perde.hidden = true;
    perde.addEventListener('click', kapat);
    panel = el('div', 'as-panel');
    panel.id = 'as-panel';
    panel.hidden = true;
    panel.tabIndex = -1;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-labelledby', 'as-baslik');
    panel.innerHTML = ''
      + '<div class="as-bas"><span class="as-logo" aria-hidden="true">' + I_SOHBET + '</span>'
      + '<div class="as-bas-yazi"><h2 id="as-baslik">KPSS Tercihi</h2><p>Genelde birkaç saniyede cevaplar</p></div>'
      + '<button type="button" class="as-yeni" hidden>Yeni sohbet</button>'
      + '<button type="button" class="as-kapat" aria-label="Kapat">' + I_KAPAT + '</button></div>'
      + '<div class="as-akis" role="log" aria-live="polite" aria-relevant="additions" aria-label="Konuşma"></div>'
      + '<div class="as-alt"><form class="as-form" novalidate><label class="as-gizli" for="as-soru">Sorunu yaz</label>'
      + '<textarea id="as-soru" rows="1" maxlength="' + SINIR + '" placeholder="Sorunu yaz…" autocomplete="off" aria-describedby="as-sayac"></textarea>'
      + '<button type="submit" class="as-gonder" aria-label="Gönder" disabled>' + I_GONDER + '</button></form>'
      + '<p class="as-not"><span>Otomatik asistan · Şartlarda resmî ilan metni esastır.</span><span class="as-sayac" id="as-sayac" hidden></span></p></div>';
    akis = panel.querySelector('.as-akis');
    form = panel.querySelector('.as-form');
    alan = panel.querySelector('textarea');
    gonderD = panel.querySelector('.as-gonder');
    yeniD = panel.querySelector('.as-yeni');
    sayac = panel.querySelector('.as-sayac');
    panel.querySelector('.as-kapat').addEventListener('click', kapat);
    yeniD.addEventListener('click', yeniSohbet);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = alan.value;
      if (bekliyor || !v.trim()) return;
      alan.value = '';
      boyutla();
      gonder(v, 'yazi');
    });
    alan.addEventListener('input', boyutla);
    alan.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
        e.preventDefault();
        if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });
    d.body.appendChild(perde);
    d.body.appendChild(panel);
    hepsiniCiz();
  }

  function boyutla() {
    alan.style.height = 'auto';
    alan.style.height = Math.min(alan.scrollHeight, 120) + 'px';
    guncelle();
  }
  function guncelle() {
    if (!kuruldu) return;
    var n = alan.value.length;
    gonderD.disabled = bekliyor || !alan.value.trim();
    yeniD.hidden = !durum.m.length;
    sayac.hidden = n < SAYAC_ESIK;
    sayac.textContent = n + '/' + SINIR;
    sayac.classList.toggle('as-dolu', n >= SINIR);
    Array.prototype.forEach.call(akis.querySelectorAll('.as-cip'), function (c) { c.disabled = bekliyor; });
  }
  function mobil() { return w.matchMedia ? w.matchMedia('(max-width:640px)').matches : w.innerWidth <= 640; }
  function yavas() { return w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches; }

  function ac() {
    if (acik) return;
    acik = true;
    clearTimeout(kapanis);
    olc('asistan_ac');
    buton.setAttribute('aria-expanded', 'true');
    cssYukle(function () {
      if (!acik) return;
      kur();
      perde.hidden = !mobil();
      panel.hidden = false;
      void panel.offsetWidth;
      panel.classList.add('as-gorunur');
      perde.classList.add('as-gorunur');
      buton.hidden = true;
      d.documentElement.classList.add('as-kilit');
      akis.scrollTop = akis.scrollHeight;
      if (mobil()) panel.focus(); else odakla();
      d.addEventListener('keydown', tus, true);
    });
  }
  /* Yazma alanına odak: düğme gizlenirken ve panel görünürken ilk deneme boşa gidebilir; kısa aralıklarla yeniden denenir. */
  function odakla() {
    var n = 0;
    (function dene() {
      if (!acik || d.activeElement === alan) return;
      try { alan.focus({ preventScroll: true }); } catch (e) { alan.focus(); }
      if (d.activeElement !== alan && n++ < 3) setTimeout(dene, 60);
    })();
  }
  function kapat() {
    if (!acik) return;
    acik = false;
    d.removeEventListener('keydown', tus, true);
    buton.setAttribute('aria-expanded', 'false');
    d.documentElement.classList.remove('as-kilit');
    if (!kuruldu) { buton.hidden = false; return; }
    panel.classList.remove('as-gorunur');
    perde.classList.remove('as-gorunur');
    kapanis = setTimeout(function () { panel.hidden = true; perde.hidden = true; }, yavas() ? 0 : 180);
    buton.hidden = false;
    buton.focus();
  }
  function tus(e) {
    if (!acik) return;
    if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); kapat(); return; }
    if (e.key !== 'Tab') return;
    var f = Array.prototype.filter.call(panel.querySelectorAll('a[href],button,textarea'), function (x) {
      return !x.disabled && !x.hidden && x.offsetParent !== null;
    });
    if (!f.length) return;
    var ilk = f[0], son = f[f.length - 1], o = d.activeElement;
    if (!panel.contains(o) || o === panel) { e.preventDefault(); (e.shiftKey ? son : ilk).focus(); }
    else if (e.shiftKey && o === ilk) { e.preventDefault(); son.focus(); }
    else if (!e.shiftKey && o === son) { e.preventDefault(); ilk.focus(); }
  }

  /* ---------- konuşma ---------- */
  function mesajDugum(m, sonMu) {
    var kap = el('div', 'as-m ' + (m.r === 'k' ? 'as-m-k' : 'as-m-a') + (m.h ? ' as-m-h' : ''));
    var balon = el('div', 'as-balon');
    balon.appendChild(el('span', 'as-gizli', m.r === 'k' ? 'Sen: ' : 'KPSS Tercihi: '));
    balon.appendChild(d.createTextNode(m.t));
    kap.appendChild(balon);
    if (m.i && m.i.length) {
      var ul = el('ul', 'as-ilanlar');
      ul.setAttribute('aria-label', 'İlanlar');
      m.i.forEach(function (x) {
        var li = el('li'), k = el(x.u ? 'a' : 'div', 'as-ilan');
        if (x.u) bagla(k, x.u);
        k.appendChild(el('b', '', x.b));
        var il = x.il && x.il.length ? (x.il.length > 3 ? x.il.slice(0, 2).join(', ') + ' ve ' + (x.il.length - 2) + ' il daha' : x.il.join(', ')) : '';
        var alt = [x.k, il].filter(Boolean).join(' · ');
        if (alt) k.appendChild(el('span', '', alt));
        var sg = sonGun(x.s);
        if (sg) k.appendChild(el('span', 'as-son', sg));
        li.appendChild(k);
        ul.appendChild(li);
      });
      kap.appendChild(ul);
    }
    if (m.b && m.b.length) {
      var lk = el('div', 'as-linkler');
      m.b.forEach(function (x) {
        var a = el('a', 'as-link', x.a);
        bagla(a, x.u);
        a.insertAdjacentHTML('beforeend', I_OK);
        lk.appendChild(a);
      });
      kap.appendChild(lk);
    }
    if (m.r === 'a' && m.k && !m.h && !m.g) kap.appendChild(geriSatiri(m));
    var cipler = sonMu ? (m.yeniden ? [{ a: 'Tekrar dene', s: m.yeniden }] : dizi(m.o).map(function (s) { return { a: s, s: s }; })) : [];
    if (cipler.length) {
      var cp = el('div', 'as-cipler');
      cipler.forEach(function (c) {
        var b = el('button', 'as-cip', c.a);
        b.type = 'button';
        b.disabled = bekliyor;
        b.addEventListener('click', function () { if (!bekliyor) gonder(c.s, 'cip'); });
        cp.appendChild(b);
      });
      kap.appendChild(cp);
    }
    return kap;
  }
  /* "İşine yaradı mı?" satırı: cevabın kayıt numarası (kid) varsa; tıklanınca tek istek atılır ve satır teşekküre dönüşür. */
  function geriAdres() { return adres().replace(/\/sor$/, '/geri'); }
  function geriGonder(kid, deger) {
    try {
      if (typeof fetch === 'function') {
        fetch(geriAdres(), { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'omit', cache: 'no-store',
          keepalive: true, body: JSON.stringify({ kid: kid, deger: deger }) }).catch(function () { /* sessiz */ });
      }
    } catch (e) { /* sessiz */ }
  }
  function geriSatiri(m) {
    var s = el('div', 'as-geri');
    s.appendChild(el('span', 'as-geri-y', 'İşine yaradı mı?'));
    [['Evet', 1], ['Hayır', -1]].forEach(function (c) {
      var b = el('button', 'as-geri-d', c[0]);
      b.type = 'button';
      b.addEventListener('click', function () {
        m.g = c[1] === 1 ? 'e' : 'h';
        kaydet();
        geriGonder(m.k, c[1]);
        olc('asistan_geri', c[1] === 1 ? 'evet' : 'hayir');
        var t = el('div', 'as-geri as-geri-t', c[1] === 1 ? 'Teşekkürler.' : 'Teşekkürler, bunu geliştireceğiz.');
        s.replaceWith(t);
      });
      s.appendChild(b);
    });
    return s;
  }
  function selam() { return { r: 'a', t: SELAM, o: durum.m.length ? [] : ILK_CIPLER }; }
  function hepsiniCiz() {
    akis.textContent = '';
    akis.appendChild(mesajDugum(selam(), !durum.m.length));
    durum.m.forEach(function (m, i) { akis.appendChild(mesajDugum(m, i === durum.m.length - 1)); });
    guncelle();
  }
  function ekle(dugum, basaKaydir) {
    akis.appendChild(dugum);
    var ust = dugum.offsetTop - akis.offsetTop - 12;
    akis.scrollTop = basaKaydir && dugum.offsetHeight > akis.clientHeight - 24 ? ust : akis.scrollHeight;
  }
  function ciplerSil() { Array.prototype.forEach.call(akis.querySelectorAll('.as-cipler'), function (c) { c.remove(); }); }
  function yeniSohbet() {
    nesil++;
    bekliyor = false;
    durum = { m: [] };
    sil();
    hepsiniCiz();
    alan.focus();
  }

  function gonder(soru, kaynak) {
    soru = String(soru || '').trim().slice(0, SINIR);
    if (!soru || bekliyor) return;
    var benim = ++nesil;
    bekliyor = true;
    ciplerSil();
    var km = { r: 'k', t: soru };
    durum.m.push(km);
    kaydet();
    ekle(mesajDugum(km, false));
    var nokta = el('div', 'as-m as-m-a');
    nokta.innerHTML = '<div class="as-balon as-yaziyor"><i></i><i></i><i></i><span class="as-gizli">Cevap hazırlanıyor</span></div>';
    ekle(nokta);
    guncelle();
    olc('asistan_soru', kaynak);

    var bitti = false, ctl = typeof AbortController === 'function' ? new AbortController() : null;
    var zaman = setTimeout(function () { if (ctl) ctl.abort(); son(null); }, ZAMAN_ASIMI);
    function son(j, gecici) {
      if (bitti) return;
      bitti = true;
      clearTimeout(zaman);
      if (benim !== nesil) return;   // bu arada "Yeni sohbet" seçildi
      bekliyor = false;
      nokta.remove();
      if (!j) ekle(mesajDugum({ r: 'a', t: HATA, h: 1, yeniden: soru }, true));
      else {
        var m = temizle(j);
        if (!m.t && !m.i.length) { ekle(mesajDugum({ r: 'a', t: HATA, h: 1, yeniden: soru }, true)); }
        else {
          if (gecici) m.h = 1; else { durum.m.push(m); kaydet(); }
          ekle(mesajDugum(m, true), true);
        }
      }
      guncelle();
      if (acik && !mobil() && panel.contains(d.activeElement) === false) alan.focus();
    }
    if (typeof fetch !== 'function') { son(null); return; }
    try {
      fetch(adres(), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'omit', cache: 'no-store',
        body: JSON.stringify({ soru: soru, sayfa: location.pathname }), signal: ctl ? ctl.signal : undefined
      }).then(function (r) {
        return r.json().catch(function () { return null; }).then(function (j) { return { s: r.status, ok: r.ok, j: j }; });
      }).then(function (c) {
        if (c.ok && c.j && typeof c.j.metin === 'string') son(c.j);
        else if (c.s === 429 && c.j && typeof c.j.metin === 'string' && c.j.metin.trim()) son({ metin: c.j.metin }, true);
        else son(null);
      }).catch(function () { son(null); });
    } catch (e) { son(null); }
  }

  if (d.body) baslat(); else d.addEventListener('DOMContentLoaded', baslat);
})();
