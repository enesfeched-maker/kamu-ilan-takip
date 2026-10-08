'use strict';
/* Statik sayfalar (ilan ayrıntısı, kurum): tema, kaydet, kalan gün, "Senin için". Veri yalnız bu tarayıcıdan okunur;
   her şey textContent ile yazılır. Tarayıcı depolaması yoksa sayfa yine çalışır. */
(function () {
  var LV = { lisans: 'Lisans', onlisans: 'Önlisans', ortaogretim: 'Ortaöğretim' }, RANK = { ortaogretim: 0, onlisans: 1, lisans: 2 };
  var AY = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
  var GUNES = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/></svg>';
  var AYIKON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
  var GRAFIK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10m6 10V4m6 16v-7m4 7H3"/></svg>';

  function oku(k, f) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? f : v; } catch (e) { return f; } }
  function yaz(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function el(t, c, x) { var n = document.createElement(t); if (c) n.className = c; if (x != null) n.textContent = x; return n; }
  function bugun() { return new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Istanbul' }); }
  function gun(s) { return Math.round((Date.parse(s + 'T00:00:00Z') - Date.parse(bugun() + 'T00:00:00Z')) / 864e5); }
  function kisa(s) { var p = s.split('-'); return Number(p[2]) + ' ' + AY[Number(p[1]) - 1]; }
  function virgul(n, k) { return n.toFixed(k).replace('.', ','); }

  /* Puan türü -> düzey ve satırın etkin düzeyleri (portal.js ptLevel/rowLevels ile aynı). */
  function ptLevel(p) { return p === 'P94' ? 'ortaogretim' : p === 'P93' ? 'onlisans' : /^P([1-9]|[1-3]\d|4[0-8])$/.test(p) ? 'lisans' : null; }
  function varsayilanTur(o) { return { onlisans: 'P93', ortaogretim: 'P94' }[o] || 'P3'; }

  /* kit-profil doğrulaması (portal.js validProfile ile aynı kurallar) */
  function profil() {
    var p = oku('kit-profil', null);
    if (!p || typeof p !== 'object' || p.v !== 1 || p.atlandi === true || !LV[p.ogrenim]) return null;
    var o = {
      ogrenim: p.ogrenim,
      puan_turu: typeof p.puan_turu === 'string' && /^P\d{1,3}$/.test(p.puan_turu) && ptLevel(p.puan_turu) === p.ogrenim ? p.puan_turu : varsayilanTur(p.ogrenim),
      iller: (Array.isArray(p.iller) ? p.iller : []).filter(function (x) { return typeof x === 'string' && x.length <= 40; }).slice(0, 81),
      tum: p.tum_turkiye === true
    };
    if (typeof p.puan === 'number' && isFinite(p.puan) && p.puan > 0 && p.puan <= 100) o.puan = p.puan;
    return o;
  }
  var normal = function (v) { return String(v || '').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ı/g, 'i'); };

  /* tema (açık varsayılan) */
  function tema() {
    var d = typeof window !== 'undefined' && window.kitKoyu ? window.kitKoyu() : oku('kit-theme', null) === 'dark';
    document.documentElement.dataset.theme = d ? 'dark' : 'light';
    var m = document.querySelector('meta[name=theme-color]'); if (m) m.content = d ? '#0D0E0C' : '#F6F6F1';
    var b = document.getElementById('theme');
    if (b) { b.innerHTML = d ? GUNES : AYIKON; b.setAttribute('aria-pressed', String(d)); b.setAttribute('aria-label', d ? 'Açık temaya geç' : 'Koyu temaya geç'); }
  }
  var tb = document.getElementById('theme');
  function iz(t, o) { try { if (typeof window !== 'undefined' && window.kpssA) window.kpssA(t, o); } catch (e) { /* ölçüm sayfayı bozmaz */ } }
  if (tb) tb.onclick = function () { var yeni = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; iz('tikla', { a: 'tema', x: yeni }); yaz('kit-theme', yeni); tema(); };
  if (typeof window !== 'undefined') window.kitTemaUygula = tema;
  tema();

  var yl = document.getElementById('yil'); if (yl) yl.textContent = String(new Date().getFullYear());

  /* kaydet: portal.js ile aynı anahtar (kit-saved) ve aynı kimlik (ilan id'si) */
  var kayitli = oku('kit-saved', []); if (!Array.isArray(kayitli)) kayitli = [];
  /* Kopya (kaynaklar arası yinelenen) ilanın birincil sayfasında ikincil kimlikler data-ikincil'de listelenir: biri kayıtlıysa kayıtlı görünür, kaldırınca hepsi silinir. */
  function kimlikler(b) { return [b.getAttribute('data-kaydet')].concat((b.getAttribute('data-ikincil') || '').split(',').filter(Boolean)); }
  function kaydetCiz(b) {
    var d = kimlikler(b).some(function (x) { return kayitli.indexOf(x) >= 0; }), ad = b.getAttribute('data-ad') || 'İlan';
    b.classList.toggle('dolu', d); b.setAttribute('aria-pressed', String(d));
    var y = b.querySelector('[data-yazi]');
    if (y) y.textContent = d ? 'Kaydedildi' : 'Kaydet';
    else b.setAttribute('aria-label', (d ? 'Kaydı kaldır: ' : 'İlanı kaydet: ') + ad);
  }
  function sayac() { var c = document.getElementById('saved-count-m'); if (c) { c.textContent = String(kayitli.length); c.hidden = !kayitli.length; } }
  sayac();
  Array.prototype.forEach.call(document.querySelectorAll('[data-kaydet]'), function (b) {
    kaydetCiz(b);
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      var id = b.getAttribute('data-kaydet'), ids = kimlikler(b), acik = ids.some(function (x) { return kayitli.indexOf(x) >= 0; });
      if (acik) kayitli = kayitli.filter(function (x) { return ids.indexOf(x) < 0; }); else kayitli.push(id);
      yaz('kit-saved', kayitli); sayac();
      var kart = b.closest ? b.closest('article') : null, bag = kart ? kart.querySelector('a[href*="ilan/"]') : null, mm = ((bag && bag.getAttribute('href')) || location.pathname).match(/ilan\/([A-Za-z0-9-]+)/);
      iz('tikla', { a: acik ? 'kaydi_sil' : 'kaydet', h: mm ? mm[1] : '' });
      Array.prototype.forEach.call(document.querySelectorAll('[data-kaydet]'), function (x) { if (x.getAttribute('data-kaydet') === id) kaydetCiz(x); });
    });
  });

  /* satırlardaki tarih bloğu: derleme anındaki değer, sayfa açılışında bugüne göre yenilenir */
  Array.prototype.forEach.call(document.querySelectorAll('.tarih[data-son]'), function (d) {
    var s = d.getAttribute('data-son'), z = d.getAttribute('data-zaman'), yakinda = d.getAttribute('data-yakinda') === '1', g = gun(s);
    if (isNaN(g)) return;
    var a = el('strong'), b = el('span');
    d.className = 'tarih';
    if (g < 0 || (z && Date.parse(z) <= Date.now())) { a.textContent = kisa(s); b.textContent = 'sona erdi'; }
    else if (g <= 2 && !yakinda) {
      d.className = 'tarih acil';
      if (g <= 0) { a.textContent = 'Bugün'; b.textContent = 'son gün'; } else if (g === 1) { a.textContent = 'Yarın'; b.textContent = 'son gün'; } else { a.textContent = kisa(s); b.textContent = '2 gün kaldı'; }
    } else { a.textContent = kisa(s); b.textContent = g + ' gün'; }
    d.replaceChildren(a, b);
  });

  /* ayrıntı sayfası: başlık kartındaki geri sayım (dakikada bir; JS yoksa derleme anındaki metin kalır) */
  var gg = document.querySelector('.dh-geri[data-son]');
  if (gg) {
    var hc = gg.closest('.dh-son'), zs = gg.getAttribute('data-zaman'), ds = gg.getAttribute('data-son');
    var bitis = zs ? Date.parse(zs) : Date.parse(ds + 'T23:59:59+03:00');
    var geriCiz = function () {
      var kalan = bitis - Date.now(), d = gun(ds), t;
      if (isNaN(kalan) || isNaN(d)) return;
      if (kalan <= 0) { t = 'Başvuru sona erdi'; hc.classList.remove('acil'); hc.classList.add('yok'); }
      else if (kalan < 864e5) {
        var sa = Math.floor(kalan / 36e5), dk = Math.floor(kalan % 36e5 / 6e4);
        t = (d <= 0 ? 'Bugün son gün' : 'Yarın son gün') + ' · ' + (sa ? sa + ' sa ' : '') + dk + ' dk kaldı'; hc.classList.add('acil');
      } else { t = d === 1 ? 'Yarın son gün' : d + ' gün kaldı'; hc.classList.toggle('acil', d <= 2); }
      gg.textContent = t;
    };
    geriCiz(); setInterval(geriCiz, 6e4);
  }

  /* satır sinyali: taban referansı (portal.js sinyalOf ile aynı cümleler) */
  var NOT = 'Geçmiş yerleştirmelerden referans; bu ilanın şartı değildir';
  function cumle(fark) {
    var x = virgul(Math.abs(fark), 1);
    return fark > 0 ? 'Puanın, benzer kadroların taban medyanından ' + x + ' puan yüksek'
      : fark < 0 ? 'Puanın, benzer kadroların taban medyanından ' + x + ' puan düşük'
        : 'Puanın, benzer kadroların taban medyanıyla aynı';
  }
  var pr = profil();
  Array.prototype.forEach.call(document.querySelectorAll('article.ilan[data-ref]'), function (a) {
    if (!pr || typeof pr.puan !== 'number' || pr.puan_turu !== varsayilanTur(pr.ogrenim)) return;
    var ref = {}, pt = (a.getAttribute('data-pt') || '').split(',').filter(Boolean);
    try { ref = JSON.parse(a.getAttribute('data-ref')) || {}; } catch (e) { return; }
    var r = ref[pr.ogrenim];
    if (!r || typeof r.medyan !== 'number' || (pt.length && pt.indexOf(pr.puan_turu) < 0)) return;
    var fark = pr.puan - r.medyan, x = virgul(Math.abs(fark), 1), p = el('p', 'sinyal'), sv = el('span', 'ic');
    sv.innerHTML = GRAFIK;
    var d = el('span', 'd', cumle(fark)), m = el('span', 'm', fark > 0 ? 'Benzer kadro · ' + x + ' puan önde' : fark < 0 ? 'Benzer kadro · ' + x + ' puan geride' : 'Benzer kadro · eşit');
    p.title = NOT; p.append(sv, d, m);
    var g = a.querySelector('.ilan-govde'); if (g && !g.querySelector('.sinyal')) g.append(p);
  });

  /* ayrıntı sayfası: "Senin için" kutusu */
  var s = document.getElementById('senin'), hedef = s && s.querySelector('[data-profil]');
  if (s && hedef) {
    var pt2 = (s.dataset.pt || '').split(',').filter(function (x) { return /^P\d{1,3}$/.test(x); });
    var ogr = (s.dataset.ogr || '').split(',').filter(function (x) { return LV[x]; });
    pt2.forEach(function (p) { var d = ptLevel(p); if (d && ogr.indexOf(d) < 0) ogr.push(d); });
    var il = s.dataset.il || '', ilanIller = (s.dataset.iller || '').split(',').filter(Boolean), kurumIci = s.dataset.kurumIci === '1', ref2 = {};
    try { ref2 = JSON.parse(s.dataset.ref || '{}') || {}; } catch (e) { ref2 = {}; }
    var ul = el('ul'), ek = function (sinif, parca) { var li = el('li', sinif); parca.forEach(function (x) { li.append(x); }); ul.append(li); };
    var kalin = function (t) { return el('b', '', t); };
    if (!pr) {
      var ek2 = el('p', 'senin-link'); ek2.append('Öğrenim düzeyini, KPSS puanını ve illerini ana sayfada 30 saniyede ekle; bu ilana uyup uymadığını burada göstereyim. ');
      var l = el('a', '', 'Profilini oluştur →'); l.href = hedef.getAttribute('data-ana') || '../../?profil=1'; ek2.append(l);
      hedef.replaceChildren(ek2);
    } else if (kurumIci) {
      ek('uyari', ['Kurum içi yeterlik sınavı; açıktan başvuruya açık değil.']);
      hedef.replaceChildren(ul);
    } else {
      var en = ogr.length ? Math.min.apply(null, ogr.map(function (x) { return RANK[x]; })) : -1;
      if (!ogr.length) ek('', ['İlanda öğrenim düzeyi belirtilmemiş; şartları resmî ilandan kontrol et.']);
      else if (ogr.indexOf(pr.ogrenim) >= 0) ek('tamam', ['Öğrenim düzeyin: ', kalin(LV[pr.ogrenim]), ' — ilanın aradığı düzeylerden biri.']);
      else if (RANK[pr.ogrenim] > en) ek('', ['İlan daha alt düzeyleri (' + ogr.map(function (x) { return LV[x]; }).join(' / ') + ') arıyor; şartlarını kontrol et.']);
      else ek('uyari', ['İlan ' + ogr.map(function (x) { return LV[x]; }).join(' / ') + ' düzeyi arıyor; senin düzeyin: ' + LV[pr.ogrenim] + '.']);
      if (s.dataset.bolum === '1') ek('', ['Belirli bölüm mezunları başvurabilir; şartlara bak.']);
      if (!ilanIller.length) ek('', ['Görev yeri: ülke geneli / ilanda belirtilmemiş.']);
      else if (!pr.tum && pr.iller.length) {
        var eslesen = ilanIller.filter(function (x) { return pr.iller.some(function (y) { return normal(y) === normal(x); }); });
        if (eslesen.length) ek('tamam', ['Görev yeri ', kalin(eslesen.join(', ')), ' seçtiğin illerden biri.']);
        else ek('', ['Görev yeri ' + (il || ilanIller.join(', ')) + '; seçtiğin illerin dışında.']);
      }
      if (pt2.length) {
        if (pt2.indexOf(pr.puan_turu) >= 0) ek('tamam', ['Puan türün: ', kalin(pr.puan_turu), ' — ilan ' + pt2.join(', ') + ' puanı arıyor.']);
        else ek('uyari', ['İlan ' + pt2.join(', ') + ' puanı arıyor; puan türün ' + pr.puan_turu + '.']);
      }
      var r = ref2[pr.ogrenim], uygunTur = pr.puan_turu === varsayilanTur(pr.ogrenim) && (!pt2.length || pt2.indexOf(pr.puan_turu) >= 0);
      if (r && typeof r.medyan === 'number' && uygunTur) {
        if (typeof pr.puan === 'number') ek(pr.puan >= r.medyan ? 'tamam' : '', [cumle(pr.puan - r.medyan) + ' (' + virgul(r.medyan, 1) + ').']);
        else ek('', ['Benzer kadroların taban medyanı ' + virgul(r.medyan, 1) + '. Puanını profiline eklersen farkı gösteririm.']);
      } else if (!Object.keys(ref2).length) ek('', ['Bu unvan için yeterli geçmiş yerleştirme verisi yok; taban karşılaştırması yapılamadı.']);
      hedef.replaceChildren(ul);
    }
  }
})();
