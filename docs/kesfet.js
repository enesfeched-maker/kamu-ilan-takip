/* KPSS Tercihi — keşif katmanı (Kasım 2026).
   İlan sayfası: bölüm gezintisi + okuma ilerlemesi, yan rayda benzer ilanlar ve topluluk, kadroların ardından soru dürtüsü,
   sayfa sonunda "Sıradaki ilan" + benzerler. Ana sayfa: yan sütunda topluluk.
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

    // tarihsiz sayfa ("Resmî ilanda") kapalı sayılmaz: 23 Kasım 2026'da yeni ilan "başvurusu sona erdi" göründü
    var kapali = !!d.querySelector('.dh-son.yok:not(.tarihsiz), .dh .pill.kapali');
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
      var s = E('script'); s.src = '/bolum/esles.js?v=3';   // kadroBazli için; sürüm bolum/index.html ile aynı s.onload = function () { ok(w.BolumEsles); }; s.onerror = hata; d.head.append(s);
    });
    return _motor;
  }
  /* Bölüm seçici: aranabilir, çoklu seçimli liste; seçilenler listenin en üstünde durur. */
  var ENCOK = 5;
  var HARF = { 'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'â': 'a', 'î': 'i', 'û': 'u' };
  function katla(s) { return String(s || '').replace(/İ/g, 'i').replace(/I/g, 'ı').toLocaleLowerCase('tr').replace(/[çğıöşüâîû]/g, function (x) { return HARF[x]; }).replace(/[^a-z0-9]+/g, ' ').trim(); }
  function basHarf(s) { return String(s || '').replace(/\(\s+/g, '(').replace(/\s+\)/g, ')').replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr')
    .replace(/(^|[\s(\/-])([^\s(\/-])/g, function (m, x, y) { return x + y.toLocaleUpperCase('tr'); })
    .replace(/ (Ve|Veya|İle|Ya Da) /g, function (m) { return m.toLocaleLowerCase('tr'); }); }
  var _adlar = {};
  function bolumAdlari(duzey) {
    if (!_adlar[duzey]) _adlar[duzey] = fetch('/puanlar/' + duzey + '-bolum.json', { cache: 'default' }).then(function (r) { return r.json(); }).then(function (v) {
      var adlar = {}; Object.keys((v && v.bolumler) || {}).forEach(function (kd) { var a = v.bolumler[kd]; if (typeof a === 'string' && a.length <= 120) adlar[basHarf(a)] = 1; });
      return Object.keys(adlar).sort(function (a, b) { return a.localeCompare(b, 'tr'); }).map(function (a) { return { ad: a, k: katla(a) }; });
    }).catch(function () { _adlar[duzey] = null; return []; });
    return _adlar[duzey];
  }
  function bolumSecici(secili, degisti) {
    var kok = E('div', 'kf-secici');
    var ciplerS = E('div', 'kf-secili'); ciplerS.setAttribute('aria-label', 'Seçtiğin bölümler');
    var kutu = E('div', 'kf-ara-kutu');
    var giris = E('input'); giris.type = 'text'; giris.id = 'kf-bolum'; giris.autocomplete = 'off'; giris.setAttribute('role', 'combobox');
    giris.setAttribute('aria-autocomplete', 'list'); giris.setAttribute('aria-expanded', 'false'); giris.setAttribute('aria-controls', 'kf-bolum-liste');
    var etiket = E('label', 'sr-only', 'Bölümünü ara ve seç'); etiket.htmlFor = 'kf-bolum';
    var ok = E('button', 'kf-ac', '▾'); ok.type = 'button'; ok.tabIndex = -1; ok.setAttribute('aria-label', 'Bölüm listesini aç');
    var liste = E('ul', 'kf-liste'); liste.id = 'kf-bolum-liste'; liste.setAttribute('role', 'listbox'); liste.setAttribute('aria-multiselectable', 'true'); liste.hidden = true;
    kutu.append(etiket, giris, ok); kok.append(ciplerS, kutu, liste);
    var adlar = [], aktif = -1, secenekler = [];
    function placeholder() { giris.placeholder = secili.length ? (secili.length >= ENCOK ? 'En fazla ' + ENCOK + ' bölüm' : 'Başka bölüm ekle') : 'Bölümünü ara (ör. Hukuk)'; }
    function cipCiz() {
      ciplerS.replaceChildren.apply(ciplerS, secili.map(function (a) {
        var c = E('span', 'kf-sec-cip'); c.append(E('span', '', a));
        var x = E('button', '', '×'); x.type = 'button'; x.setAttribute('aria-label', a + ' bölümünü çıkar');
        x.addEventListener('click', function () { degis(a); giris.focus(); });
        c.append(x); return c;
      }));
      ciplerS.hidden = !secili.length; placeholder();
    }
    function degis(a) {
      var i = secili.indexOf(a);
      if (i >= 0) secili.splice(i, 1); else if (secili.length < ENCOK) secili.push(a); else return;
      giris.value = ''; cipCiz(); listeCiz(); degisti(secili.slice());
    }
    function secenek(ad, secildi, ek) {
      var li = E('li', 'kf-sec' + (secildi ? ' secili' : '')); li.setAttribute('role', 'option'); li.setAttribute('aria-selected', String(!!secildi));
      li.id = 'kf-sec-' + secenekler.length; li.append(E('span', 'kf-onay', secildi ? '✓' : ''), E('span', '', ek || ad));
      li.addEventListener('mousedown', function (e) { e.preventDefault(); });
      li.addEventListener('click', function () { degis(ad); });
      secenekler.push({ li: li, ad: ad }); return li;
    }
    function listeCiz() {
      var q = katla(giris.value), parca = []; secenekler = [];
      if (secili.length) {
        parca.push(E('li', 'kf-liste-baslik', 'Seçtiklerin'));
        secili.forEach(function (a) { parca.push(secenek(a, true)); });
      }
      var bulunan = [];
      if (q) {
        var bas = [], soz = [], ic = [];
        adlar.forEach(function (x) {
          if (secili.indexOf(x.ad) >= 0) return;
          var i = x.k.indexOf(q);
          if (i === 0) bas.push(x); else if (i > 0 && x.k.charAt(i - 1) === ' ') soz.push(x); else if (i > 0) ic.push(x);
        });
        bulunan = bas.concat(soz, ic);
      } else bulunan = adlar.filter(function (x) { return secili.indexOf(x.ad) < 0; });
      if (secili.length >= ENCOK) parca.push(E('li', 'kf-liste-not', 'En fazla ' + ENCOK + ' bölüm seçebilirsin; birini çıkarıp yenisini ekle.'));
      else {
        var yazilan = giris.value.trim();
        if (bulunan.length) {
          parca.push(E('li', 'kf-liste-baslik', q ? 'Eşleşen bölümler' : 'Tüm bölümler'));
          bulunan.slice(0, 120).forEach(function (x) { parca.push(secenek(x.ad, false)); });
          if (bulunan.length > 120) parca.push(E('li', 'kf-liste-not', bulunan.length - 120 + ' bölüm daha; aramayı daralt.'));
        } else if (q) parca.push(E('li', 'kf-liste-not', 'Listede bu adla bölüm yok.'));
        else if (!adlar.length) parca.push(E('li', 'kf-liste-not', 'Bölüm listesi yükleniyor…'));
        // listede olmayan ad da denenebilir (en sonda)
        if (yazilan.length >= 3 && !adlar.some(function (x) { return x.k === q; }) && secili.indexOf(basHarf(yazilan)) < 0) parca.push(secenek(basHarf(yazilan), false, '“' + basHarf(yazilan) + '” adıyla dene'));
      }
      liste.replaceChildren.apply(liste, parca);
      aktif = secenekler.length ? Math.min(Math.max(aktif, 0), secenekler.length - 1) : -1;
      if (q && secenekler.length > secili.length) aktif = secili.length;   // aramada Enter ilk eşleşeni seçer
      isaretle();
    }
    function isaretle() {
      secenekler.forEach(function (s, i) { s.li.classList.toggle('aktif', i === aktif); });
      if (aktif >= 0) { giris.setAttribute('aria-activedescendant', secenekler[aktif].li.id); secenekler[aktif].li.scrollIntoView({ block: 'nearest' }); }
      else giris.removeAttribute('aria-activedescendant');
    }
    function ac() { if (!liste.hidden) return; liste.hidden = false; giris.setAttribute('aria-expanded', 'true'); kok.classList.add('acik'); aktif = -1; listeCiz(); }
    function kapat() { liste.hidden = true; giris.value = '';giris.setAttribute('aria-expanded', 'false'); kok.classList.remove('acik'); }
    giris.addEventListener('focus', ac);
    giris.addEventListener('click', ac);
    giris.addEventListener('input', function () { ac(); aktif = -1; listeCiz(); });
    ok.addEventListener('mousedown', function (e) { e.preventDefault(); });
    ok.addEventListener('click', function () { if (liste.hidden) { giris.focus(); ac(); } else kapat(); });
    giris.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); ac(); aktif = Math.min(aktif + 1, secenekler.length - 1); isaretle(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); aktif = Math.max(aktif - 1, 0); isaretle(); }
      else if (e.key === 'Enter') { e.preventDefault(); if (aktif >= 0 && secenekler[aktif]) degis(secenekler[aktif].ad); }
      else if (e.key === 'Escape') { kapat(); }
      else if (e.key === 'Backspace' && !giris.value && secili.length) degis(secili[secili.length - 1]);
    });
    giris.addEventListener('blur', function () { setTimeout(function () { if (!kok.contains(d.activeElement)) kapat(); }, 120); });
    cipCiz();
    return {
      el: kok,
      adlariYukle: function (duzey) { adlar = []; if (!liste.hidden) listeCiz(); bolumAdlari(duzey).then(function (l) { adlar = l || []; if (!liste.hidden) listeCiz(); }); }
    };
  }

  var KISA = {   // kadrolara ayrılmamış ilanlar için tek cümlelik sonuç
    uygun: ['evet', 'Bölümün şartlarda geçiyor.'],
    kontrol: ['belki', 'Bölümün şartlarda geçiyor olabilir; ilan metninden kontrol et.'],
    serbest: ['evet', 'Bu ilan herhangi bir bölümden mezun olanları alıyor.'],
    bak: ['belki', 'Bölüm şartı tam okunamadı; ilan metnine bak.'],
    haric: ['hayir', 'Bölümün bu ilanda hariç tutulmuş.'],
    degil: ['hayir', 'Şartta sayılan bölümler arasında seninkini bulamadık. "Denk bölümler" ifadesi için belgeye bak.']
  };
  function kadroMetni(rec, ad) {
    var f = katla(ad), l = [];
    (rec.kadro_detay || []).concat(rec.yz_kadrolar || []).forEach(function (k) { if (k && katla(k.unvan) === f) l = l.concat(k.maddeler || k.kosullar || []); });
    (rec.sartlar || []).forEach(function (s) { if (s && katla(s.kadro) === f) l.push(s.metin); });
    return l.join(' ');
  }
  function kadroyaGit(ad) {
    var f = katla(ad), hedef = null;
    d.querySelectorAll('.kk').forEach(function (k) { var s = k.querySelector('.kk-bas strong'); if (!hedef && s && katla(s.textContent) === f) hedef = k; });
    if (!hedef) { var kb = d.getElementById('kadrolar'); if (kb) kb.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    hedef.scrollIntoView({ behavior: 'smooth', block: 'center' });
    hedef.classList.remove('kf-parla'); void hedef.offsetWidth; hedef.classList.add('kf-parla');
  }

  function uygunKutu(key, c) {
    var ogr = (c.ogrenim || []).filter(function (o) { return OGRENIM_AD[o]; });
    if (!ogr.length) return;
    var kayitli = oku(UYGUN, {}) || {}, profil = oku('kit-profil', {}) || {};
    var po = profil.ogrenim, duzey = kayitli.d || (typeof po === 'string' ? po : Array.isArray(po) && po.length === 1 ? po[0] : '');
    if (!OGRENIM_AD[duzey]) duzey = '';
    var secili = (Array.isArray(kayitli.bl) ? kayitli.bl : kayitli.b ? [kayitli.b] : [])
      .filter(function (x) { return typeof x === 'string' && x.trim(); }).slice(0, ENCOK);
    var k = E('section', 'kf-uygun'); k.setAttribute('aria-label', 'Bu ilana başvurabilir misin');
    k.append(E('h2', '', 'Bu ilana başvurabilir misin?'));
    var cipler = E('div', 'kf-cipler'); cipler.setAttribute('role', 'group'); cipler.setAttribute('aria-label', 'Mezuniyetin');
    var sonuc = E('p', 'kf-uygun-sonuc'); sonuc.setAttribute('aria-live', 'polite');
    var secici = bolumSecici(secili, function (l) { secili = l; kaydet(); denetle(); iz('kesfet', { k: 'uygun_bolum_sec', h: String(l.length) }); });
    var alan = E('div', 'kf-bolum-alan'); alan.hidden = true;
    var bolumSonuc = E('div', 'kf-bolum-sonuc'); bolumSonuc.setAttribute('aria-live', 'polite');
    alan.append(secici.el);
    ['lisans', 'onlisans', 'ortaogretim'].forEach(function (o) {
      var b = E('button', 'kf-cip', OGRENIM_AD[o]); b.type = 'button'; b.dataset.o = o;
      b.addEventListener('click', function () { if (duzey !== o) { duzey = o; kaydet(); ciz(); } iz('kesfet', { k: 'uygun_duzey', h: o }); });
      cipler.append(b);
    });
    function kaydet() { var v = oku(UYGUN, {}) || {}; v.d = duzey; v.bl = secili.slice(); v.b = secili[0] || ''; yaz(UYGUN, v); }
    var adlarDuzey = '';
    function ciz(bekle) {
      cipler.querySelectorAll('.kf-cip').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.o === duzey)); });
      bolumSonuc.replaceChildren();
      if (!duzey) { sonuc.textContent = 'Mezuniyetini seç, hemen söyleyelim.'; sonuc.className = 'kf-uygun-sonuc'; alan.hidden = true; return; }
      if (ogr.indexOf(duzey) < 0) {
        sonuc.className = 'kf-uygun-sonuc hayir';
        sonuc.textContent = 'Bu ilan yalnız ' + ogr.map(function (o) { return OGRENIM_AD[o]; }).join(' ve ') + ' mezunlarını alıyor.';
        alan.hidden = true; return;
      }
      sonuc.className = 'kf-uygun-sonuc evet';
      sonuc.textContent = OGRENIM_AD[duzey] + ' mezunları başvurabilir. ' + (duzey === 'ortaogretim' ? 'Alan şartı olan kadrolar için alanını seçebilirsin.' : 'Bölümünü seç; hangi kadrolara uyduğunu söyleyelim.');
      alan.hidden = false;
      if (adlarDuzey !== duzey) { adlarDuzey = duzey; secici.adlariYukle(duzey); }
      if (!bekle) denetle();
    }
    function denetle() {
      if (!duzey || ogr.indexOf(duzey) < 0) return;
      if (!secili.length && duzey !== 'ortaogretim') { bolumSonuc.replaceChildren(); return; }
      bolumSonuc.replaceChildren(E('p', 'kf-bekle', 'Şartlar okunuyor…'));
      var istek = secili.join('|') + '#' + duzey; denetle.son = istek;
      Promise.all([kayitAl(key), motorAl()]).then(function (s) {
        if (denetle.son !== istek) return;   // bu arada seçim değişti
        var rec = s[0], M = s[1];
        if (!rec || !M || !M.kadroBazli) throw new Error('yok');
        goster(rec, M.kadroBazli(rec, secili, duzey));
      }).catch(function () { bolumSonuc.replaceChildren(E('p', 'kf-uygun-sonuc belki', 'Şu an kontrol edilemedi; şartları aşağıdaki Kadrolar bölümünden oku.')); });
    }
    function kanitP(metin) { return E('blockquote', 'kf-kanit', '“' + metin + '”'); }
    function goster(rec, r) {
      var parca = [], cok = secili.length > 1;
      if (r.genel) {
        var g = r.kadrolar[0];
        if (!g) { bolumSonuc.replaceChildren(); return; }
        var m = KISA[g.durum] || KISA.bak;
        parca.push(E('p', 'kf-uygun-sonuc ' + m[0], m[1] + (cok && g.bolum && /uygun|kontrol/.test(g.durum) ? ' (' + g.bolum + ')' : '')));
        if (g.kanit && g.durum !== 'degil' && g.durum !== 'bak') parca.push(kanitP(g.kanit));
        var ek0 = g.durum === 'degil' ? [] : ekSartlar(rec);
        if (ek0.length) parca.push(E('p', 'kf-ek-sart', 'Bu ilanda ' + ek0.join(', ') + ' şartı da var; Kadrolar bölümünden oku.'));
        iz('kesfet', { k: 'uygun_bolum', h: g.durum });
      } else {
        var grup = { uygun: [], serbest: [], kontrol: [], bak: [], haric: [], degil: [] };
        r.kadrolar.forEach(function (x) { (grup[x.durum] || grup.bak).push(x); });
        var evet = grup.uygun.concat(grup.serbest), belki = grup.kontrol.concat(grup.bak), toplam = r.kadrolar.length;
        var bas;
        if (!secili.length) {
          bas = grup.serbest.length ? ['evet', grup.serbest.length + ' kadroda alan şartı yok; başvurabilirsin.'] : ['belki', 'Bu düzeydeki kadroların alan şartı var; alanını seç.'];
          grup.bak = grup.bak.concat(grup.kontrol, grup.degil); grup.kontrol = []; grup.degil = []; grup.uygun = [];
        } else if (evet.length) bas = ['evet', toplam === 1 ? 'Başvurabilirsin.' : evet.length === toplam ? 'Bu düzeydeki ' + toplam + ' kadronun hepsine başvurabilirsin.' : evet.length + ' kadroya başvurabilirsin.'];
        else if (belki.length) bas = ['belki', 'Kesin söyleyemiyoruz; aşağıdaki kadroların şartını ilan metninden kontrol et.'];
        else if (!toplam) bas = ['hayir', 'Bu ilanda ' + OGRENIM_AD[duzey].toLocaleLowerCase('tr') + ' düzeyinde kadro bulamadık.'];
        else bas = ['hayir', grup.haric.length && !grup.degil.length ? 'Bölümün bu ilanda hariç tutulmuş.' : 'Bölümün bu ilandaki ' + OGRENIM_AD[duzey].toLocaleLowerCase('tr') + ' kadrolarının şartlarında geçmiyor.'];
        parca.push(E('p', 'kf-uygun-sonuc ' + bas[0], bas[1]));
        var ul = E('ul', 'kf-kadrolar');
        function satirEkle(x, sinif, neden, kanit) {
          var li = E('li', 'kf-kadro ' + sinif);
          var ad = E('button', 'kf-kadro-ad', x.ad ? basHarf(x.ad) : 'İlan'); ad.type = 'button'; ad.title = 'Kadrolar bölümünde göster';
          ad.addEventListener('click', function () { kadroyaGit(x.ad); });
          li.append(ad, E('span', 'kf-kadro-neden', neden));
          if (kanit) li.append(E('span', 'kf-kadro-kanit', '“' + kanit + '”'));
          if (sinif !== 'hayir') {
            var ek = EK_SART.filter(function (e) { return e[0].test(kadroMetni(rec, x.ad)); }).map(function (e) { return e[1]; });
            if (ek.length) li.append(E('span', 'kf-kadro-ek', 'Ayrıca ' + ek.join(', ') + ' şartı var'));
          }
          ul.append(li);
        }
        grup.uygun.forEach(function (x) { satirEkle(x, 'evet', cok && x.bolum ? x.bolum + ' listede' : 'Bölümün listede',x.kanit && katla(x.kanit) !== katla(x.bolum) ? x.kanit : ''); });
        grup.serbest.forEach(function (x) { satirEkle(x, 'evet', 'Bölüm şartı yok; yalnız öğrenim düzeyi aranıyor', ''); });
        grup.kontrol.forEach(function (x) { satirEkle(x, 'belki', 'Şartı kontrol et' + (cok && x.bolum ? ' (' + x.bolum + ')' : ''), x.kanit); });
        grup.bak.forEach(function (x) { satirEkle(x, 'belki', secili.length ? 'Şart metni tam okunamadı; ilan metnine bak' : 'Alan şartı var; alanını seç', ''); });
        grup.haric.forEach(function (x) { satirEkle(x, 'hayir', 'Bölümün hariç tutulmuş', x.kanit); });
        if (ul.children.length) parca.push(ul);
        if (grup.degil.length) {
          var det = E('details', 'kf-degil'); det.append(E('summary', '', 'Bölümünün geçmediği ' + grup.degil.length + ' kadro'));
          var ul2 = E('ul', 'kf-kadrolar');
          grup.degil.forEach(function (x) {
            var li = E('li', 'kf-kadro hayir'), b = E('button', 'kf-kadro-ad', basHarf(x.ad)); b.type = 'button';
            b.addEventListener('click', function () { kadroyaGit(x.ad); }); li.append(b); ul2.append(li);
          });
          det.append(ul2); parca.push(det);
        }
        if (r.digerDuzey) parca.push(E('p', 'kf-not', 'İlanda başka öğrenim düzeyleri için ' + r.digerDuzey + ' kadro daha var.'));
        if (r.eksik) parca.push(E('p', 'kf-not', 'Bazı kadroların şartları siteye alınamadı; ilan belgesine de bak.'));
        iz('kesfet', { k: 'uygun_bolum', h: bas[0] });
      }
      if (r.duzeltme) parca.push(E('p', 'kf-not', 'Bu ilan için düzeltme yayımlanmış; güncel şartları kurumdan kontrol et.'));
      parca.push(E('p', 'kf-not', 'Son karar kurumun ilan metnine göre verilir.'));
      if (secili.length) { var l = E('a', 'yazi-link', 'Bölümüne uygun tüm ilanlar →'); l.href = '/bolum/?b=' + encodeURIComponent(secili[0]) + '&d=' + duzey; parca.push(l); }
      bolumSonuc.replaceChildren.apply(bolumSonuc, parca);
    }
    k.append(cipler, sonuc, alan, bolumSonuc);
    var bakis = d.querySelector('.d-ana .bakis'), ana = d.querySelector('.d-ana');
    if (bakis) bakis.after(k); else if (ana) ana.prepend(k);
    // kayıtlı seçim varsa sonucu kutu görünür olunca getir (ilanlar.json'u boşuna indirmemek için)
    if ((secili.length || duzey === 'ortaogretim') && 'IntersectionObserver' in w) {
      ciz(true);
      var gor = new IntersectionObserver(function (e) { if (e[0].isIntersecting) { gor.disconnect(); denetle(); } }); gor.observe(k);
    } else ciz();
  }

  /* ---------- ana sayfa ---------- */
  function anaSayfa() {
    var alan = d.getElementById('ilanlar'), yan = d.querySelector('aside.yan');
    if (!alan) return;
    forumSon().then(function (basliklar) {
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
