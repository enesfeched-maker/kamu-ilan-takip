/* KPSS Tercihi — keşif katmanı (Kasım 2026).
   İlan sayfası: bölüm gezintisi + okuma ilerlemesi, yan rayda benzer ilanlar ve topluluk, kadroların ardından soru dürtüsü,
   sayfa sonunda "Sıradaki ilan" + benzerler. Ana sayfa: "Kaldığın yerden" şeridi ve yan sütunda topluluk.
   Veri: /liste.json (açık ilanlar) ve forumun herkese açık /son ucu. Okuma geçmişi yalnız bu tarayıcıda ('kit-okunan'). */
(function () {
  'use strict';
  var d = document, w = window;
  var YEREL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  var API = w.KESFET_FORUM_API || (YEREL ? '/__forum' : 'https://forum-api.kpsstercihi.com');
  var GECMIS = 'kit-okunan', GECMIS_SINIR = 40;
  var OGRENIM_AD = { lisans: 'Lisans', onlisans: 'Önlisans', ortaogretim: 'Ortaöğretim', ilkogretim: 'İlköğretim' };

  function oku(k, v) { try { var x = JSON.parse(localStorage.getItem(k)); return x == null ? v : x; } catch (e) { return v; } }
  function yaz(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* gizli pencere */ } }
  function E(tag, cls, txt) { var n = d.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function iz(ad, veri) { try { if (typeof w.kpssA === 'function') w.kpssA('tikla', Object.assign({ a: ad }, veri || {})); } catch (e) { /* yok say */ } }
  function norm(s) { return String(s || '').replace(/İ/g, 'i').replace(/I/g, 'ı').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ı/g, 'i'); }

  function liste() {
    return fetch('/liste.json', { cache: 'default' }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { return (j && j.ilanlar) || []; }).catch(function () { return []; });
  }
  function forumAl(yol) {
    return fetch(API + yol).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { return (j && j.basliklar) || []; }).catch(function () { return []; });
  }
  function forumSon() { return forumAl('/son'); }
  /* İlan sayfası için konu havuzu: son hareketler + ilan konuları + bu ilanın öğrenim düzeyindeki sorular (tekilleştirilmiş). */
  function forumHavuz(ogrenim) {
    var istek = [forumAl('/son'), forumAl('/basliklar?kategori=ilan')];
    (ogrenim || []).slice(0, 2).forEach(function (o) { istek.push(forumAl('/basliklar?duzey=' + encodeURIComponent(o))); });
    return Promise.all(istek).then(function (l) {
      var gor = {}, hepsi = [];
      l.forEach(function (x) { x.forEach(function (b) { if (b && !gor[b.id]) { gor[b.id] = 1; hepsi.push(b); } }); });
      return hepsi;
    });
  }

  /* ---------- tarih ---------- */
  function gunFarki(i) {
    if (!i.son_tarih) return null;
    var bug = new Date(); bug.setHours(0, 0, 0, 0);
    var p = i.son_tarih.split('-'); var s = new Date(+p[0], +p[1] - 1, +p[2]);
    return Math.round((s - bug) / 864e5);
  }
  function acik(i) { var t = i.son_zaman ? Date.parse(i.son_zaman) : NaN; return isNaN(t) ? (gunFarki(i) == null || gunFarki(i) >= 0) : t > Date.now(); }
  function kalanYazi(i) {
    var g = gunFarki(i);
    if (g == null) return { t: 'Tarih yakında', acil: false };
    if (g <= 0) return { t: 'Bugün son gün', acil: true };
    if (g === 1) return { t: 'Yarın son gün', acil: true };
    return { t: g + ' gün kaldı', acil: g <= 3 };
  }

  /* ---------- benzerlik ---------- */
  function kesisim(a, b) { var n = 0; (a || []).forEach(function (x) { if ((b || []).indexOf(x) >= 0) n++; }); return n; }
  /* Meslek alanları: başlık + kadro adlarından çıkarılır (aksansız, küçük harf). "Benzer" demek önce aynı alanda olmak demek;
     öğrenim, il, puan türü yalnız aynı alandaki ilanları kendi arasında sıralar. zayif: geniş bir alan (memur/uzman gibi). */
  var ALANLAR = [
    { ad: 'Hukuk', r: /avukat|hukuk|hakim|savci|icra (mudur|katib)|zabit katib|noter/ },
    { ad: 'Güvenlik', r: /zabita|itfaiye|bekci|guvenlik gorevlisi|koruma ve guvenlik|polis|infaz koruma/ },
    { ad: 'Askerî', r: /astsubay|subay|uzman erbas|sozlesmeli er\b|askeri/ },
    { ad: 'Mühendislik', r: /muhendis|mimar(?!i\b)|tekniker|teknisyen|sehir ve bolge|harita|insaat/ },
    { ad: 'Bilişim', r: /yazilim|programci|cozumleyici|sistem uzman|ag uzman|network|veri taban|siber|bilgi guvenligi|bilgisayar|bilisim/ },
    { ad: 'Denetim', r: /mufettis|denetmen|denetci|kontrolor/ },
    { ad: 'Uzman yardımcılığı', r: /uzman yardimcisi|kaymakam/ },
    { ad: 'Sağlık ve sosyal', r: /psikolog|sosyal calismaci|hemsire|\bebe\b|doktor|hekim|saglik|eczaci|diyetisyen|fizyoterap|cocuk gelisim/ },
    { ad: 'Mali', r: /muhasebe|mali |maliye|hazine|vergi|gelir uzman/ },
    { ad: 'Eğitim', r: /ogretmen|egitmen|egitim uzman/ },
    { ad: 'Büro', r: /memur|buro|sekreter|isletmen|veri hazirlama|uzman personel|sozlesmeli uzman|^\d* ?uzman$/, zayif: 1 },
    { ad: 'İşçi', r: /isci|destek personeli|temizlik|sofor|asci|bahcivan/, zayif: 1 }
  ];
  function alanlar(i) {
    if (i._alan) return i._alan;
    var metinler = [norm(i.manset)].concat((i.unvanlar || []).map(norm)).concat(i.baslikN ? [i.baslikN] : []);
    var l = ALANLAR.filter(function (a) { return metinler.some(function (m) { return a.r.test(m); }); });
    // "Zabıta memuru" Büro değil Güvenlik'tir: belirgin bir alan bulunduysa geniş alanlar düşer
    if (l.some(function (a) { return !a.zayif; })) l = l.filter(function (a) { return !a.zayif; });
    return (i._alan = l);
  }
  function puanla(i, c) {
    var p = 0, neden = null;
    // 1) aynı kadro adı (en güçlü)
    var u = kesisim((i.unvanlar || []).map(norm), (c.unvanlar || []).map(norm));
    if (u) { p += 10 + Math.min(u - 1, 2); neden = 'Aynı kadro'; }
    // 2) aynı meslek alanı
    var ca = alanlar(c), ortak = alanlar(i).filter(function (a) { return ca.indexOf(a) >= 0; });
    var guclu = ortak.filter(function (a) { return !a.zayif; });
    if (guclu.length) { p += 6; neden = neden || guclu[0].ad; } else if (ortak.length) { p += 3; neden = neden || ortak[0].ad; }
    // 3) aynı kurum
    var kurum = c.kurum_slug && i.kurum_slug === c.kurum_slug;
    if (kurum) { p += 3; neden = neden || 'Aynı kurum'; }
    var ilgili = p > 0;
    // 4) sıralama ayrıntıları: aynı şartlarla başvurulabilir mi, yakın mı, acil mi
    if (kesisim(i.ogrenim, c.ogrenim)) p += 1.5;
    if (kesisim(i.puan_turleri, c.puan_turleri)) p += 1;
    var il = c.iller && c.iller.length && (i.iller || []).filter(function (x) { return c.iller.indexOf(x) >= 0; })[0];
    if (il) p += 1;
    var g = gunFarki(i); if (g != null && g >= 0 && g <= 5) p += 0.4;
    if (i.ilk_gorulme && Date.now() - Date.parse(i.ilk_gorulme) < 3 * 864e5) p += 0.2;
    // alan bulunamayan ilanlarda (ör. "Personel alımı") eski ölçüt: aynı öğrenim + puan türü
    if (!ilgili && !ca.length && kesisim(i.ogrenim, c.ogrenim) && kesisim(i.puan_turleri, c.puan_turleri)) {
      ilgili = true; neden = OGRENIM_AD[(i.ogrenim || []).filter(function (x) { return (c.ogrenim || []).indexOf(x) >= 0; })[0]] || null;
    }
    if (neden && il && neden !== 'Aynı kurum') neden += ' · ' + il;
    return { i: i, p: p, neden: neden, ilgili: ilgili };
  }
  /* İki liste döner: benzer (aynı kadro/alan/kurum) ve sart (alan farklı ama aynı öğrenim + puan türüyle başvurulabilir). */
  function benzerler(ilanlar, c, haric) {
    var gor = {}; (haric || []).forEach(function (k) { gor[k] = 1; });
    var hepsi = ilanlar.filter(function (i) { return !gor[i.key] && acik(i); })
      .map(function (i) { return puanla(i, c); })
      .sort(function (a, b) { return b.p - a.p || (gunFarki(a.i) || 99) - (gunFarki(b.i) || 99); });
    var benzer = hepsi.filter(function (r) { return r.ilgili; });
    var sart = hepsi.filter(function (r) { return !r.ilgili && kesisim(r.i.ogrenim, c.ogrenim) && kesisim(r.i.puan_turleri, c.puan_turleri); })
      .sort(function (a, b) { return (gunFarki(a.i) || 99) - (gunFarki(b.i) || 99); })
      .map(function (r) { return { i: r.i, p: r.p, neden: OGRENIM_AD[(r.i.ogrenim || []).filter(function (x) { return (c.ogrenim || []).indexOf(x) >= 0; })[0]] || null }; });
    var yakin = hepsi.slice().sort(function (a, b) { return (gunFarki(a.i) || 99) - (gunFarki(b.i) || 99); })
      .map(function (r) { return { i: r.i, p: r.p, neden: null }; });
    return { benzer: benzer, sart: sart, yakin: yakin };
  }

  /* ---------- parçalar ---------- */
  function logo(i, boy) {
    var k = E('span', 'kf-logo');
    if (i.logo) { var im = E('img'); im.src = '/' + i.logo; im.alt = ''; im.loading = 'lazy'; im.width = boy; im.height = boy; k.append(im); }
    else k.textContent = (i.kurum || '?').split(/\s+/).slice(0, 2).map(function (s) { return s[0]; }).join('').toUpperCase();
    return k;
  }
  function adres(i) { return '/ilan/' + encodeURIComponent(i.key) + '/'; }
  function satir(r, kaynak) {
    var i = r.i, a = E('a', 'kf-s'); a.href = adres(i);
    a.addEventListener('click', function () { iz('kesfet', { k: kaynak, h: i.key }); });
    var g = E('span'); var k = kalanYazi(i);
    g.append(E('span', 'kf-s-kurum', i.kurum), E('span', 'kf-s-bas', i.manset || 'İlan'));
    var alt = E('span', 'kf-s-alt'); alt.append(E('span', 'kf-kalan' + (k.acil ? ' acil' : ''), k.t));
    if (r.neden) alt.append(E('span', 'kf-neden', r.neden));
    g.append(alt); a.append(logo(i, 36), g); return a;
  }
  function kart(r) {
    var i = r.i, a = E('a', 'kf-kart'); a.href = adres(i);
    a.addEventListener('click', function () { iz('kesfet', { k: 'izgara', h: i.key }); });
    var ust = E('span', 'kf-kart-ust'); ust.append(logo(i, 36), E('span', 'kf-s-kurum', i.kurum));
    var k = kalanYazi(i), alt = E('span', 'kf-kart-alt');
    alt.append(E('span', 'kf-kalan' + (k.acil ? ' acil' : ''), k.t));
    if (r.neden) alt.append(E('span', 'kf-neden', r.neden));
    if (i.il) alt.append(E('span', '', i.il));
    a.append(ust, E('span', 'kf-s-bas', i.manset || 'İlan'), alt); return a;
  }
  function soruAdres(b) { return '/forum/?' + (b.kategori === 'oda' ? 'oda=' : 'b=') + b.id; }
  function ne_zaman(sn) {
    var f = Math.max(0, Date.now() / 1000 - sn);
    if (f < 3600) return Math.max(1, Math.round(f / 60)) + ' dk önce';
    if (f < 86400) return Math.round(f / 3600) + ' saat önce';
    return Math.round(f / 86400) + ' gün önce';
  }
  /* Konuları bu ilana yakınlığına göre sıralar: benzer bir ilanın konusu > aynı öğrenim düzeyi > geri kalan (yeniden eskiye).
     Bu ilanın kendi konusu zaten "Sorular" bölümünde olduğu için yan rayda tekrar gösterilmez. */
  function toplulukSirala(basliklar, c, key, benzerAnahtarlar) {
    var oge = (c && c.ogrenim) || [];
    return basliklar.filter(function (x) { return x.kategori !== 'oda' && x.ilan_id !== key; }).map(function (x) {
      var p = 0, etiket = '';
      if (x.ilan_id && benzerAnahtarlar.indexOf(x.ilan_id) >= 0) { p = 3 - benzerAnahtarlar.indexOf(x.ilan_id) / 100; etiket = 'Benzer ilan'; }
      else if (x.duzey && oge.indexOf(x.duzey) >= 0) { p = 2; etiket = OGRENIM_AD[x.duzey] || ''; }
      else if (x.kategori === 'ilan' && x.yanit_sayisi) p = 1;
      return { x: x, p: p, etiket: etiket };
    }).sort(function (a, b) { return b.p - a.p || (b.x.son_hareket || 0) - (a.x.son_hareket || 0); })
      .map(function (r) { r.x._etiket = r.etiket; return r.x; });
  }
  function toplulukBlok(basliklar, adet) {
    var b = E('section', 'kf-blok kf-topluluk'); var h = E('h2', '', 'Toplulukta şimdi');
    var tum = E('a', '', 'Forum →'); tum.href = '/forum/'; h.append(tum); b.append(h);
    var sorular = basliklar.filter(function (x) { return x.kategori !== 'oda'; }).slice(0, adet);
    if (!sorular.length) b.append(E('p', 'kf-bos', 'Adaylar ilanları, puanları ve mülakatları burada konuşuyor.'));
    sorular.forEach(function (x) {
      var a = E('a', 'kf-soru'); a.href = soruAdres(x);
      a.addEventListener('click', function () { iz('kesfet', { k: 'topluluk', h: String(x.id) }); });
      var y = x.yanit_sayisi ? x.yanit_sayisi + ' yanıt' : 'İlk yanıtı sen ver';
      a.append(E('b', '', x.baslik), E('small', '', (x._etiket ? x._etiket + ' · ' : '') + y + ' · ' + ne_zaman(x.son_hareket || x.olusma)));
      b.append(a);
    });
    var k = E('a', 'kf-katil', 'Sen de sor'); k.href = '/forum/'; b.append(k);
    return b;
  }

  /* ---------- geçmiş ---------- */
  function gecmiseYaz(key) {
    var g = oku(GECMIS, []); if (!Array.isArray(g)) g = [];
    g = g.filter(function (x) { return x && x.k !== key; }); g.unshift({ k: key, t: Date.now() });
    yaz(GECMIS, g.slice(0, GECMIS_SINIR));
  }
  function gecmisAnahtarlar() { var g = oku(GECMIS, []); return Array.isArray(g) ? g.map(function (x) { return x && x.k; }).filter(Boolean) : []; }

  /* ---------- ilan sayfası ---------- */
  function sayfadanOzellik() {
    var c = { ogrenim: [], puan_turleri: [], iller: [], unvanlar: [] };
    d.querySelectorAll('.dh-bilgi > div').forEach(function (div) {
      var dt = norm((div.querySelector('dt') || {}).textContent), dd = ((div.querySelector('dd') || {}).textContent || '').trim();
      if (dt.indexOf('ogrenim') === 0) {
        var n = norm(dd);
        if (n.indexOf('onlisans') >= 0) c.ogrenim.push('onlisans');
        if (/(^|[^n])lisans/.test(n)) c.ogrenim.push('lisans');
        if (n.indexOf('ortaogretim') >= 0 || n.indexOf('lise') >= 0) c.ogrenim.push('ortaogretim');
      } else if (dt.indexOf('kpss') === 0) { c.puan_turleri = (dd.match(/P\d+/g) || []); }
    });
    var ka = d.querySelector('.dh-kurum'); var m = ka && (ka.getAttribute('href') || '').match(/kurum\/([^/]+)\//);
    if (m) c.kurum_slug = m[1];
    var h1 = d.querySelector('.dh h1, main h1'); c.baslikN = norm(h1 && h1.textContent);
    return c;
  }
  function bolumBul() {
    var ozet = d.querySelector('.bakis'), kadro = null;
    d.querySelectorAll('.d-ana > .d-bolum').forEach(function (s) {
      var h = s.querySelector(':scope > h2'); if (!kadro && h && /^(Kadrolar|Başvuru şartları|Başvuru koşulları)/i.test(h.textContent.trim())) kadro = s;
    });
    return { ozet: ozet, kadro: kadro, sorular: d.getElementById('tartisma') };
  }
  function gezinti(b, son) {
    var ogeler = [];
    function ekle(el, id, ad) { if (!el) return; if (!el.id) el.id = id; ogeler.push({ el: el, ad: ad }); }
    ekle(b.ozet, 'ozet', 'Özet'); ekle(b.kadro, 'kadrolar', 'Kadrolar'); ekle(b.sorular, 'tartisma', 'Sorular'); ekle(son, 'kf-son', 'Benzer ilanlar');
    if (ogeler.length < 2) return;
    // kısa sayfada (iki ekrandan az) bölüm çubuğu kalabalıktan başka bir şey değil
    var ana0 = d.querySelector('.d-ana'); if (!ana0 || ana0.offsetHeight < innerHeight * 2.2) return;
    var nav = E('nav', 'kf-gez'); nav.setAttribute('aria-label', 'Sayfa bölümleri');
    var linkler = ogeler.map(function (o) { var a = E('a', '', o.ad); a.href = '#' + o.el.id; nav.append(a); return a; });
    var bar = E('span', 'kf-bar'), dol = E('i'); bar.append(dol); nav.append(bar);
    // main'in doğrudan çocuğu olmalı: yapışkan konum ebeveyninin sonuna kadar geçerlidir
    d.querySelector('.d-bas').after(nav);
    // okuma ilerlemesi + etkin bölüm
    var bekliyor = false;
    function guncelle() {
      bekliyor = false;
      var ana = d.querySelector('.d-ana'); if (!ana) return;
      var r = ana.getBoundingClientRect(), boy = r.height - innerHeight * 0.6;
      var oran = Math.min(1, Math.max(0, -r.top / Math.max(1, boy)));
      dol.style.transform = 'scaleX(' + oran.toFixed(3) + ')';
      var etkin = 0; ogeler.forEach(function (o, n) { if (o.el.getBoundingClientRect().top < 140) etkin = n; });
      linkler.forEach(function (a, n) { a.classList.toggle('aktif', n === etkin && oran > 0); });
    }
    addEventListener('scroll', function () { if (!bekliyor) { bekliyor = true; requestAnimationFrame(guncelle); } }, { passive: true });
    guncelle();
    return linkler;
  }
  function durtu(b) {
    if (!b.kadro || !b.sorular) return;
    var k = E('aside', 'kf-durt'), y = E('div', 'kf-durt-yazi');
    y.append(E('b', '', 'Aklına takılan bir şey mi var?'), E('span', '', 'Bu ilana başvuranlar sorularını burada konuşuyor.'));
    var a = E('a', '', 'Soru sor'); a.href = '#tartisma';
    a.addEventListener('click', function (e) {
      iz('kesfet', { k: 'durtu' });
      var giris = b.sorular.querySelector('textarea, input[type=text]');
      if (giris) { e.preventDefault(); b.sorular.scrollIntoView({ behavior: 'smooth', block: 'start' }); setTimeout(function () { try { giris.focus({ preventScroll: true }); } catch (_) { giris.focus(); } }, 450); }
    });
    k.append(y, a);
    // Yalnız ilanın henüz hiç sorusu yoksa görünür: sorusu olan ilanda "Sorular" bölümü zaten aynı işi yapıyor
    k.hidden = true;
    // kadro kartlarının hemen ardından (uzun ayrıntı metninden önce); yoksa bölümün sonuna
    var kk = b.kadro.querySelector('.kk-liste, .sb, .tablo-kap');
    if (kk) kk.after(k); else b.kadro.append(k);
    function bak() {
      var oz = b.sorular.querySelector('[data-ozet]'), t = oz ? oz.textContent.trim() : '';
      if (/Henüz soru yok/i.test(t)) { k.hidden = false; gozcu.disconnect(); }
      else if (/mesaj/i.test(t)) { k.remove(); gozcu.disconnect(); }
    }
    var gozcu = new MutationObserver(bak);
    gozcu.observe(b.sorular, { childList: true, subtree: true, characterData: true });
    bak();
  }
  function ilanSayfasi(key) {
    var main = d.getElementById('icerik'); if (!main || !main.querySelector('.d-bas')) return;
    gecmiseYaz(key);
    var b = bolumBul();
    durtu(b);
    var son = E('section', 'd-bolum kf-son'); son.id = 'kf-son'; son.hidden = true;
    var ilgili = d.querySelector('.ilgili-sayfalar'), ana = d.querySelector('.d-ana');
    if (ilgili) ilgili.before(son); else if (ana) ana.append(son);
    var linkler = gezinti(b, son);
    var ray = E('aside', 'kf-ray'); ray.setAttribute('aria-label', 'Benzer ilanlar ve topluluk'); main.append(ray);

    var kapali = !!d.querySelector('.dh-son.yok, .dh .pill.kapali');
    liste().then(function (ilanlar) {
      var bu = ilanlar.filter(function (i) { return i.key === key; })[0];
      var c = bu ? Object.assign({ baslikN: sayfadanOzellik().baslikN }, bu) : sayfadanOzellik();
      if (bu && !kapali) uygunKutu(key, c);
      var sonuc = benzerler(ilanlar, c, [key]);
      // Okunanlar en sona: sıradaki ilan hep yeni bir şey göstersin
      var okunan = gecmisAnahtarlar();
      function tazeOnce(l) { return l.filter(function (r) { return okunan.indexOf(r.i.key) < 0; }).concat(l.filter(function (r) { return okunan.indexOf(r.i.key) >= 0; })); }
      var benzer = tazeOnce(sonuc.benzer), sart = tazeOnce(sonuc.sart);
      // Benzer yoksa aynı şartlarla başvurulabilenler gösterilir; başlık bunu açıkça söyler (alakasız "benzer" yok)
      var yakin = tazeOnce(sonuc.yakin);
      var sira = benzer.length ? benzer : sart.length ? sart : yakin;
      var rayBaslik = benzer.length ? 'Benzer ilanlar' : sart.length ? 'Aynı şartlarla başvurabileceğin' : 'Son günü yaklaşanlar';
      if (sira.length) {
        var bl = E('section', 'kf-blok'), h = E('h2', '', rayBaslik), t = E('a', '', 'Tümü →'); t.href = '/'; h.append(t); bl.append(h);
        var ul = E('ul', 'kf-satirlar'); sira.slice(0, 5).forEach(function (r) { var li = E('li'); li.append(satir(r, 'ray')); ul.append(li); });
        bl.append(ul); ray.append(bl);
        // sayfa sonu
        son.hidden = false; son.append(E('h2', '', 'Sıradaki ilan'));
        var r0 = sira[0], i0 = r0.i, a = E('a', 'kf-sirada'); a.href = adres(i0);
        a.addEventListener('click', function () { iz('kesfet', { k: 'sirada', h: i0.key }); });
        var g = E('span'), kk = kalanYazi(i0);
        g.append(E('small', '', r0.neden ? r0.neden + ' · ' + kk.t : kk.t), E('strong', '', i0.manset || 'İlan'), E('span', 'kf-sk', i0.kurum + (i0.il ? ' · ' + i0.il : '')));
        a.append(logo(i0, 64), g, E('span', 'kf-ok', '→')); son.append(a);
        var devam = sira.slice(1, 7);
        if (devam.length) {
          son.append(E('h2', 'alt-h', benzer.length ? 'Bunlara da göz at' : rayBaslik));
          var iz_ = E('div', 'kf-izgara'); devam.forEach(function (r) { iz_.append(kart(r)); }); son.append(iz_);
        }
        // benzerler azsa: alanı farklı ama aynı öğrenim + puan türüyle başvurulabilen ilanlar, ayrı başlıkla
        if (benzer.length && benzer.length < 7 && sart.length) {
          son.append(E('h2', 'alt-h', 'Aynı şartlarla başvurabileceğin'));
          var iz2 = E('div', 'kf-izgara'); sart.slice(0, benzer.length < 4 ? 6 : 3).forEach(function (r) { iz2.append(kart(r)); }); son.append(iz2);
        }
        // sayfa üreticisinin eski "Benzer ilanlar" listesi artık bunun tekrarı
        var eski = d.querySelector('.d-ana > .benzer'); if (eski) eski.hidden = true;
        if (kapali) kapaliUyari(sira, benzer.length ? 'Şu an açık benzer ilanlar' : rayBaslik);
      } else if (linkler) { linkler[linkler.length - 1].remove(); }
      var benzerAnahtarlar = benzer.slice(0, 12).map(function (r) { return r.i.key; });
      return forumHavuz(c.ogrenim).then(function (havuz) {
        var basliklar = toplulukSirala(havuz, c, key, benzerAnahtarlar);
        ray.append(toplulukBlok(basliklar, 4));
        // telefonda yan ray görünmez: topluluk bloğu sayfa sonuna da girer
        var mob = toplulukBlok(basliklar, 3); mob.classList.add('kf-mobil'); son.hidden = false; son.append(mob);
      });
    });
  }

  /* Süresi dolmuş ilan: aramadan gelen ziyaretçi sayfanın sonuna inmeden çıkmasın; açık benzerler en üstte. */
  function kapaliUyari(sira, baslik) {
    var bas = d.querySelector('.d-bas'); if (!bas || !sira.length) return;
    var k = E('section', 'kf-kapali'); k.setAttribute('aria-label', 'Açık ilanlar');
    var h = E('div', 'kf-kapali-bas');
    h.append(E('b', '', 'Bu ilanın başvurusu sona erdi.'), E('span', '', baslik + ':'));
    var ul = E('ul', 'kf-satirlar'); sira.slice(0, 3).forEach(function (r) { var li = E('li'); li.append(satir(r, 'kapali')); ul.append(li); });
    var tum = E('a', 'kf-kapali-tum', 'Tüm açık ilanlar →'); tum.href = '/#ilanlar';
    k.append(h, ul, tum); bas.after(k);
  }

  /* ---------- "Bu ilana başvurabilir misin?" ----------
     Öğrenim düzeyi anında karşılaştırılır. Bölüm, /bolum/ sayfasının eşleştirme motoruyla (bolum/esles.js) bu ilanın
     şart metnine karşı denetlenir; şart metinleri ilanlar.json'da olduğu için o dosya yalnız bölüm girilince yüklenir. */
  var UYGUN = 'kit-bolum';   // /bolum/ sayfasıyla ortak: {d: düzey, b: bölüm}
  var KADEME = {
    kesin: ['evet', 'Bölümün şartlarda geçiyor.'],
    muhtemel: ['belki', 'Bölümün şartlarda geçiyor olabilir; ilan metninden kontrol et.'],
    serbest: ['evet', 'Bu ilan herhangi bir bölümden mezun olanları alıyor.'],
    belirsiz: ['belki', 'Bölüm şartı tam okunamadı; ilan metnine bak.'],
    eslesmiyor: ['hayir', 'Şartta sayılan bölümler arasında seninkini bulamadık. "Denk bölümler" ifadesi için belgeye bak.'],
    haric: ['hayir', 'Bölümün bu ilanda hariç tutulmuş.']
  };
  /* Bölüm uysa bile başvuruyu engelleyebilecek ek şartlar: yalnız varlığı söylenir, kişiye göre yorumlanmaz. */
  var EK_SART = [[/yaşını (doldurmamış|bitirmemiş)|yaşından gün almamış|yaş sınırı/i, 'yaş'], [/tecrübe|deneyim/i, 'deneyim'],
    [/sürücü belgesi|ehliyet/i, 'sürücü belgesi'], [/\bYDS\b|YÖKDİL|yabancı dil/i, 'yabancı dil'], [/sertifika/i, 'sertifika']];
  function ekSartlar(rec) {
    var metin = (rec.sartlar || []).map(function (s) { return s && s.metin; })
      .concat((rec.kadro_detay || []).map(function (k) { return ((k && k.maddeler) || []).join(' '); }))
      .concat((rec.kadro_ortak || []).map(function (b) { return ((b && b[1]) || []).join(' '); })).join(' ');
    return EK_SART.filter(function (e) { return e[0].test(metin); }).map(function (e) { return e[1]; });
  }
  var _kayit = null, _motor = null;
  function kayitAl(key) {
    if (!_kayit) _kayit = fetch('/ilanlar.json', { cache: 'default' }).then(function (r) { return r.json(); }).then(function (j) {
      var l = (j && j.ilanlar) || [];
      return l.filter(function (r) { return r.key === key || r.id === key || String(r.id || '').split('i=')[1] === key; })[0]
        || l.filter(function (r) { return String(r.id || '').indexOf(key) >= 0; })[0] || null;
    });
    return _kayit;
  }
  function motorAl() {
    if (!_motor) _motor = w.BolumEsles ? Promise.resolve(w.BolumEsles) : new Promise(function (ok, hata) {
      var s = E('script'); s.src = '/bolum/esles.js'; s.onload = function () { ok(w.BolumEsles); }; s.onerror = hata; d.head.append(s);
    });
    return _motor;
  }
  function uygunKutu(key, c) {
    var ogr = (c.ogrenim || []).filter(function (o) { return OGRENIM_AD[o]; });
    if (!ogr.length) return;
    var kayitli = oku(UYGUN, {}) || {}, profil = oku('kit-profil', {}) || {};
    var po = profil.ogrenim, duzey = kayitli.d || (typeof po === 'string' ? po : Array.isArray(po) && po.length === 1 ? po[0] : '');
    if (!OGRENIM_AD[duzey]) duzey = '';
    var k = E('section', 'kf-uygun'); k.setAttribute('aria-label', 'Bu ilana başvurabilir misin');
    k.append(E('h2', '', 'Bu ilana başvurabilir misin?'));
    var cipler = E('div', 'kf-cipler'); cipler.setAttribute('role', 'group'); cipler.setAttribute('aria-label', 'Mezuniyetin');
    var sonuc = E('p', 'kf-uygun-sonuc'); sonuc.setAttribute('aria-live', 'polite');
    var form = E('form', 'kf-bolum-form'); form.hidden = true;
    var etiket = E('label', 'sr-only', 'Bölümün'); etiket.htmlFor = 'kf-bolum';
    var giris = E('input'); giris.id = 'kf-bolum'; giris.type = 'text'; giris.placeholder = 'Bölümünü yaz (ör. Hukuk)'; giris.autocomplete = 'off';
    giris.setAttribute('list', 'kf-bolum-liste'); giris.value = kayitli.b || '';
    var dl = E('datalist'); dl.id = 'kf-bolum-liste';
    var dugme = E('button', '', 'Kontrol et'); dugme.type = 'submit';
    var bolumSonuc = E('div', 'kf-bolum-sonuc'); bolumSonuc.setAttribute('aria-live', 'polite');
    form.append(etiket, giris, dl, dugme);
    ['lisans', 'onlisans', 'ortaogretim'].forEach(function (o) {
      var b = E('button', 'kf-cip', OGRENIM_AD[o]); b.type = 'button'; b.dataset.o = o;
      b.addEventListener('click', function () { duzey = o; kaydet(); ciz(); iz('kesfet', { k: 'uygun_duzey', h: o }); });
      cipler.append(b);
    });
    function kaydet() { var v = oku(UYGUN, {}) || {}; v.d = duzey; v.b = giris.value.trim(); yaz(UYGUN, v); }
    var listeYuklu = '';
    function ciz(bekle) {
      cipler.querySelectorAll('.kf-cip').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.o === duzey)); });
      bolumSonuc.replaceChildren();
      if (!duzey) { sonuc.textContent = 'Mezuniyetini seç, hemen söyleyelim.'; sonuc.className = 'kf-uygun-sonuc'; form.hidden = true; return; }
      if (ogr.indexOf(duzey) < 0) {
        sonuc.className = 'kf-uygun-sonuc hayir';
        sonuc.textContent = 'Bu ilan yalnız ' + ogr.map(function (o) { return OGRENIM_AD[o]; }).join(' ve ') + ' mezunlarını alıyor.';
        form.hidden = true; return;
      }
      sonuc.className = 'kf-uygun-sonuc evet';
      sonuc.textContent = OGRENIM_AD[duzey] + ' mezunları başvurabilir. Bölümün uyuyor mu?';
      form.hidden = false;
      if (listeYuklu !== duzey) {
        listeYuklu = duzey;
        fetch('/puanlar/' + duzey + '-bolum.json', { cache: 'default' }).then(function (r) { return r.json(); }).then(function (v) {
          var adlar = {}; Object.keys((v && v.bolumler) || {}).forEach(function (kd) { var a = v.bolumler[kd]; if (typeof a === 'string' && a.length <= 120) adlar[a.toLocaleLowerCase('tr').replace(/(^|[\s(\/-])(\S)/g, function (m, x, y) { return x + y.toLocaleUpperCase('tr'); })] = 1; });
          dl.replaceChildren.apply(dl, Object.keys(adlar).sort(function (a, b) { return a.localeCompare(b, 'tr'); }).map(function (a) { var o = E('option'); o.value = a; return o; }));
        }).catch(function () { /* öneri listesi isteğe bağlı */ });
      }
      if (giris.value.trim() && !bekle) denetle();
    }
    function denetle() {
      var ad = giris.value.trim(); if (!ad) return;
      kaydet();
      bolumSonuc.replaceChildren(E('p', 'kf-bekle', 'Şartlar okunuyor…'));
      Promise.all([kayitAl(key), motorAl()]).then(function (s) {
        var rec = s[0], M = s[1];
        if (!rec || !M) throw new Error('yok');
        var r = M.siniflandir(rec, M.bolumCoz(ad), duzey);
        var haric = r.kademe === 'eslesmiyor' && /hariç/.test(r.neden || '');
        var k2 = haric ? KADEME.haric : KADEME[r.kademe] || KADEME.belirsiz;
        var p = E('p', 'kf-uygun-sonuc ' + k2[0], k2[1]); var parca = [p];
        if (r.kanit && (haric || r.kademe === 'kesin' || r.kademe === 'muhtemel' || r.kademe === 'serbest')) {
          parca.push(E('blockquote', 'kf-kanit', '“' + r.kanit + '”'));
        }
        var ek = r.kademe === 'eslesmiyor' ? [] : ekSartlar(rec);
        if (ek.length) parca.push(E('p', 'kf-ek-sart', 'Bu ilanda ' + ek.join(', ') + ' şartı da var; Kadrolar bölümünden oku.'));
        parca.push(E('p', 'kf-not', 'Son karar kurumun ilan metnine göre verilir.'));
        var l = E('a', 'yazi-link', 'Bölümüne uygun tüm ilanlar →'); l.href = '/bolum/?b=' + encodeURIComponent(ad) + '&d=' + duzey; parca.push(l);
        bolumSonuc.replaceChildren.apply(bolumSonuc, parca);
        iz('kesfet', { k: 'uygun_bolum', h: r.kademe });
      }).catch(function () { bolumSonuc.replaceChildren(E('p', 'kf-uygun-sonuc belki', 'Şu an kontrol edilemedi; şartları aşağıdaki Kadrolar bölümünden oku.')); });
    }
    form.addEventListener('submit', function (e) { e.preventDefault(); denetle(); });
    k.append(cipler, sonuc, form, bolumSonuc);
    var bakis = d.querySelector('.d-ana .bakis'), ana = d.querySelector('.d-ana');
    if (bakis) bakis.after(k); else if (ana) ana.prepend(k);
    // kayıtlı bölüm varsa sonucu kutu görünür olunca getir (ilanlar.json'u boşuna indirmemek için)
    if (kayitli.b && 'IntersectionObserver' in w) {
      ciz(true);
      var gor = new IntersectionObserver(function (e) { if (e[0].isIntersecting) { gor.disconnect(); if (!form.hidden) denetle(); } }); gor.observe(k);
    } else ciz();
  }

  /* ---------- ana sayfa ---------- */
  function anaSayfa() {
    var alan = d.getElementById('ilanlar'), yan = d.querySelector('aside.yan');
    if (!alan) return;
    Promise.all([liste(), forumSon()]).then(function (s) {
      var ilanlar = s[0], basliklar = s[1];
      var harita = {}; ilanlar.forEach(function (i) { harita[i.key] = i; });
      var son = gecmisAnahtarlar().map(function (k) { return harita[k]; }).filter(function (i) { return i && acik(i); }).slice(0, 6);
      if (son.length) {
        var k = E('section', 'kf-kaldigin'); k.setAttribute('aria-label', 'Kaldığın yerden');
        var h = E('h2', '', 'Kaldığın yerden'), sil = E('button', '', 'Temizle'); sil.type = 'button';
        sil.addEventListener('click', function () { yaz(GECMIS, []); k.remove(); iz('kesfet', { k: 'gecmis_sil' }); });
        h.append(sil); k.append(h);
        var y = E('div', 'kf-yatay'); son.forEach(function (i) { y.append(satir({ i: i, neden: null }, 'kaldigin')); }); k.append(y);
        var bas = alan.querySelector('.liste-ozet') || alan.querySelector('.liste-bas');
        if (bas) bas.after(k); else alan.prepend(k);
      }
      if (yan) yan.append(toplulukBlok(basliklar, 4));
    });
  }

  function basla() {
    var m = location.pathname.match(/^\/ilan\/([^/]+)\/?$/);
    if (m) { try { ilanSayfasi(decodeURIComponent(m[1])); } catch (e) { /* katman isteğe bağlı */ } return; }
    if (location.pathname === '/' || location.pathname === '/index.html') { try { anaSayfa(); } catch (e) { /* yok say */ } }
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', basla); else basla();
})();
