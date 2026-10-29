/* KPSS Tercihi — katiplik sayfalarının ortak yardımcıları: tema anahtarı (sayfa.js ile aynı davranış), yıl,
   kayıtlı sayacı, ölçüm, tarayıcı depolama ve metin biçimi. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  function A(t, o) { try { if (window.kpssA) window.kpssA(t, o); } catch (e) { /* ölçüm sayfayı bozmaz */ } }
  function oku(k, f) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? f : v; } catch (e) { return f; } }
  function yaz(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* depolama kapalı */ } }
  function E(etiket, sinif, yazi) { var e = document.createElement(etiket); if (sinif) e.className = sinif; if (yazi != null) e.textContent = yazi; return e; }

  function tema() {
    var d = window.kitKoyu ? window.kitKoyu() : oku('kit-theme', null) === 'dark';
    document.documentElement.dataset.theme = d ? 'dark' : 'light';
    var m = document.querySelector('meta[name=theme-color]'); if (m) m.content = d ? '#0D0E0C' : '#F6F6F1';
    var b = $('theme');
    if (b) {
      if (!b.dataset.hazir) { b.dataset.hazir = '1'; requestAnimationFrame(function () { requestAnimationFrame(function () { b.classList.add('anahtar-hazir'); }); }); }
      b.setAttribute('aria-pressed', String(d)); b.setAttribute('aria-label', d ? 'Açık temaya geç' : 'Koyu temaya geç');
    }
  }
  if ($('theme')) $('theme').onclick = function () {
    var yeni = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    A('tikla', { a: 'tema', x: yeni }); yaz('kit-theme', { t: yeni, a: window.kitOto ? window.kitOto() : null }); tema();
  };
  window.kitTemaUygula = tema; tema();
  if ($('yil')) $('yil').textContent = String(new Date().getFullYear());
  (function () { var k = oku('kit-saved', []), c = $('saved-count-m'); if (c && Array.isArray(k)) { c.textContent = String(k.length); c.hidden = !k.length; } })();

  function sinavBicimi(x) {
    return String(x).toLocaleLowerCase('tr-TR').replace(/[âàá]/g, 'a').replace(/[îíì]/g, 'i').replace(/[ûúù]/g, 'u')
      .replace(/[^a-zçğıöşü\s]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function karistir(d) { for (var i = d.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = d[i]; d[i] = d[j]; d[j] = t; } return d; }
  function sureYaz(sn) { sn = Math.max(0, Math.ceil(sn)); return Math.floor(sn / 60) + ':' + String(sn % 60).padStart(2, '0'); }
  // Tarihe bağlı tekrarlanabilir rastgele sayı (günün metni herkes için aynı olsun diye)
  function tohumlu(tohum) { var s = tohum >>> 0; return function () { s = (s + 0x6D2B79F5) >>> 0; var t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function bugunAnahtar(d) { d = d || new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }

  // Katiplik ayarlarındaki klavye türü tüm sayfalarda ortak
  function klavyeTuru() { var v = oku('kit-katip', {}); return v && v.ayar && v.ayar.klavye === 'F' ? 'F' : 'Q'; }
  function klavyeKaydet(d) { var v = oku('kit-katip', {}) || {}; v.ayar = v.ayar || {}; v.ayar.klavye = d === 'F' ? 'F' : 'Q'; yaz('kit-katip', v); }

  // Kelime havuzu: yüklenen kütüphanelerden sıklık sıralı kelimeler
  function kelimeSikligi(metinListeleri) {
    var s = {};
    metinListeleri.forEach(function (ml) { ml.forEach(function (m) { m[1].split(' ').forEach(function (w) { s[w] = (s[w] || 0) + 1; }); }); });
    return Object.keys(s).sort(function (a, b) { return s[b] - s[a] || a.localeCompare(b, 'tr'); });
  }

  var TERIMLER = ('mahkeme hakim savcı sanık şüpheli müşteki mağdur tanık bilirkişi avukat vekil davacı davalı duruşma tutanak ' +
    'dilekçe tebligat tebliğ müzekkere celse keşif yemin beyan ifade itiraz istinaf temyiz bozma onama karar hüküm gerekçe ' +
    'ilam icra haciz takip ödeme emri alacaklı borçlu ihtiyati tedbir harç masraf avans vekalet ücret esas numara dosya kalem ' +
    'zabıt katibi yazı işleri müdürü adliye cumhuriyet başsavcılığı soruşturma kovuşturma iddianame tutuklama adli kontrol ' +
    'gözaltı uzlaştırma arabuluculuk sulh feragat kabul ıslah ihbar delil emare yargılama kesinleşme şerh mühür arşiv ' +
    'uyap elektronik imza duruşma salonu ara karar zamanaşımı hak düşürücü süre').split(' ');

  window.KatipOrtak = { $: $, A: A, oku: oku, yaz: yaz, E: E, sinavBicimi: sinavBicimi, karistir: karistir, sureYaz: sureYaz,
    tohumlu: tohumlu, bugunAnahtar: bugunAnahtar, klavyeTuru: klavyeTuru, klavyeKaydet: klavyeKaydet, kelimeSikligi: kelimeSikligi, TERIMLER: TERIMLER };
})();
