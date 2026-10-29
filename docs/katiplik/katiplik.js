/* KPSS Tercihi — katiplik klavye sınavı simülasyonu ve antrenmanları.
   Puanlama: puanla.js (resmi kriterler). Metinler: kutuphane.js + metin/*.js (resmî 2025, mevzuat, özgün).
   Veri yalnız tarayıcıda: localStorage 'kit-katip'. Ortak yardımcılar: ortak.js, klavye analizi: klavye.js. */
(function () {
  'use strict';
  var O = window.KatipOrtak, KK = window.KatipKlavye, KUT = window.KatipKutuphane;
  var $ = O.$, A = O.A, E = O.E, sureYaz = O.sureYaz, karistir = O.karistir;

  /* ---------- durum ---------- */
  var P = window.KatipPuan;
  var VARSAYILAN = { aday: '', klavye: 'Q', sure: 180, metin: -1, kutuphane: 'zk2025', canli: true, takip: false, ses: false, sureGoster: true, font: 15 };
  var veri = O.oku('kit-katip', null);
  if (!veri || typeof veri !== 'object') veri = {};
  veri.gecmis = Array.isArray(veri.gecmis) ? veri.gecmis : [];
  veri.hatalar = veri.hatalar && typeof veri.hatalar === 'object' ? veri.hatalar : {};
  veri.rozetler = Array.isArray(veri.rozetler) ? veri.rozetler : [];
  veri.ayar = Object.assign({}, VARSAYILAN, veri.ayar || {});
  veri.ozel = typeof veri.ozel === 'string' ? veri.ozel : '';
  veri.gunluk = veri.gunluk && typeof veri.gunluk === 'object' ? veri.gunluk : {};
  veri.yol = Object.assign({ tarih: '', hedef: 90 }, veri.yol || {});
  var ayar = veri.ayar;
  if (!KUT.bul(ayar.kutuphane)) ayar.kutuphane = 'zk2025';
  // Başka sayfalar (ders, antrenman) de 'kit-katip' içine yazar; kaydetmeden önce onların alanlarını koru.
  function kaydet() {
    var disari = O.oku('kit-katip', {}) || {};
    if (disari.hatalar) Object.keys(disari.hatalar).forEach(function (w) { if (!(w in veri.hatalar)) veri.hatalar[w] = disari.hatalar[w]; });
    O.yaz('kit-katip', veri);
  }

  var METINLER = [], GUNLUK = [], ISINMA = [];
  var mod = 'sinav';
  var MODLAR = {
    sinav: { ust: 'Sınav simülasyonu', baslik: 'Resmi sınav koşulları', dugme: 'Sınavı başlat · 3:00' },
    antrenman: { ust: 'Serbest antrenman', baslik: 'Kendi koşullarını belirle', dugme: 'Antrenmanı başlat' },
    hatali: { ust: 'Hatalı kelimelerim', baslik: 'Zayıf kelimelerini güçlendir', dugme: 'Tekrarı başlat · 1:00' },
    isinma: { ust: 'Isınma', baslik: 'Türkçe karakter ısınması', dugme: 'Isınmayı başlat · 1:00' },
    ozel: { ust: 'Kendi metnin', baslik: 'Metnini yapıştır', dugme: 'Başlat' },
    gunluk: { ust: 'Günün metni', baslik: 'Günün duruşması', dugme: 'Günün metnini yaz' }
  };

  /* ---------- metin hazırlama ---------- */
  // Sınav metni: seçilen metin ve ardından gelenler, süreye yetecek uzunlukta (dakikada ~70 kelime + pay).
  function zincir(liste, bas, saniye) {
    var gerek = Math.ceil(saniye / 60 * 70) + 60, k = [], i = bas;
    while (k.length < gerek) { k = k.concat(liste[i % liste.length][1].split(' ')); i++; }
    return k.join(' ');
  }
  function kelimeTekrari(havuz, saniye) {
    var gerek = Math.ceil(saniye / 60 * 80) + 40, k = [];
    while (k.length < gerek) k = k.concat(karistir(havuz.slice()));
    return k.slice(0, gerek).join(' ');
  }
  function hataliHavuz() {
    return Object.keys(veri.hatalar).sort(function (a, b) { return veri.hatalar[b] - veri.hatalar[a]; }).slice(0, 60);
  }
  function gununNo() {
    var d = O.bugunAnahtar(), t = 0;
    for (var i = 0; i < d.length; i++) t = (t * 31 + d.charCodeAt(i)) >>> 0;
    return Math.floor(O.tohumlu(t)() * GUNLUK.length);
  }

  /* ---------- ayar paneli ---------- */
  function kutuphaneDoldur() {
    var s = $('kutuphane-sec'), gruplar = {};
    s.innerHTML = '';
    KUT.liste.forEach(function (k) {
      var g = gruplar[k.grup];
      if (!g) { g = gruplar[k.grup] = E('optgroup'); g.label = k.grup; s.append(g); }
      var o = E('option', null, k.ad + ' · ' + k.adet + ' metin'); o.value = k.id; g.append(o);
    });
    s.value = ayar.kutuphane;
  }
  function kutuphaneYukle(id) {
    ayar.kutuphane = id; kaydet();
    var k = KUT.bul(id);
    $('kaynak-not').textContent = '';   // yalnız yükleme hatasında dolar
    $('basla').disabled = $('hemen-sinav').disabled = true;
    return KUT.getir(id).then(function (m) {
      METINLER = m;
      if (ayar.metin >= METINLER.length) ayar.metin = -1;
      metinSecimiDoldur();
      $('basla').disabled = $('hemen-sinav').disabled = false;
    }).catch(function () { $('kaynak-not').textContent = 'Metinler yüklenemedi; bağlantını kontrol edip sayfayı yenile.'; });
  }
  function metinSecimiDoldur() {
    var s = $('metin-sec');
    s.innerHTML = '';
    var r = E('option', null, 'Rastgele metin'); r.value = '-1'; s.append(r);
    METINLER.forEach(function (m, i) { var o = E('option', null, (i + 1) + '. ' + m[0]); o.value = String(i); s.append(o); });
    s.value = String(ayar.metin >= 0 && ayar.metin < METINLER.length ? ayar.metin : -1);
  }
  function surSec(v) {
    ayar.sure = v;
    [].forEach.call(document.querySelectorAll('#sure-sec .tab'), function (b) { var a = Number(b.dataset.v) === v; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); });
  }
  function modSec(m, kaydir) {
    mod = m;
    [].forEach.call(document.querySelectorAll('.kt-mod'), function (b) { var a = b.dataset.mod === m; b.classList.toggle('secili', a); b.setAttribute('aria-pressed', String(a)); });
    [].forEach.call(document.querySelectorAll('[data-goster]'), function (e) { e.classList.toggle('kt-gizli', e.dataset.goster.split(' ').indexOf(m) < 0); });
    var t = MODLAR[m];
    $('ayar-ust').textContent = t.ust; $('ayar-baslik').textContent = t.baslik;
    $('basla').textContent = m === 'antrenman' || m === 'ozel' ? t.dugme + ' · ' + sureYaz(ayar.sure) : t.dugme;
    $('basla').setAttribute('data-a-x', 'basla-' + m);
    var not = '';   // yalnız Hatalı kelimelerim modunda durum bildirir
    if (m === 'hatali') { var n = hataliHavuz().length; not = n < 5 ? 'Henüz yeterli hatalı kelimen yok (en az 5). Önce bir sınav simülasyonu yap.' : n + ' farklı hatalı kelimen var; en çok yanlış yazdıkların öncelikli.'; }
    $('ayar-not').textContent = not;
    if (kaydir) $('ayar').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------- sınav ---------- */
  var s = { durum: 'bos', mod: 'sinav', metin: '', metinNo: -1, kutuphane: '', baslik: '', sure: 180, kalan: 180, bas: 0, zaman: 0, spanlar: null, vurgu: null, sonCanli: 0, font: 15, kayit: KK.kaydedici() };
  var yazim = $('s-yazim');
  var RESMI = { sinav: 1, gunluk: 1 };

  function sinavAc(m, secenek) {
    secenek = secenek || {};
    var sure = 180, metin = '', no = -1, baslik = '', kut = ayar.kutuphane;
    if (m === 'sinav' || m === 'antrenman') {
      if (!METINLER.length) return;
      sure = m === 'sinav' ? 180 : ayar.sure;
      no = secenek.metinNo != null ? secenek.metinNo : (m === 'antrenman' && ayar.metin >= 0 ? ayar.metin : Math.floor(Math.random() * METINLER.length));
      metin = zincir(METINLER, no, sure); baslik = KUT.bul(kut).kisa + ' · ' + METINLER[no][0];
    } else if (m === 'gunluk') {
      if (!GUNLUK.length) return;
      kut = 'zk2025'; no = gununNo(); metin = zincir(GUNLUK, no, 180); baslik = 'Günün metni · ' + O.bugunAnahtar().split('-').reverse().join('.');
    } else if (m === 'hatali') {
      var h = hataliHavuz();
      if (h.length < 5) { modSec('hatali', true); return; }
      sure = 60; metin = kelimeTekrari(h, sure); baslik = 'Hatalı kelimelerim';
    } else if (m === 'isinma') {
      if (!ISINMA.length) return;
      sure = 60; metin = kelimeTekrari(ISINMA, sure); baslik = 'Türkçe karakter ısınması';
    } else if (m === 'ozel') {
      var ham = O.sinavBicimi($('ozel-metin').value);
      if (ham.split(' ').length < 10) { alert('Lütfen en az 10 kelimelik bir metin yapıştır.'); $('ozel-metin').focus(); return; }
      veri.ozel = $('ozel-metin').value.slice(0, 20000); kaydet();
      sure = ayar.sure; var tekrar = [ham];
      while (tekrar.join(' ').split(' ').length < sure / 60 * 70 + 60) tekrar.push(ham);
      metin = tekrar.join(' '); baslik = 'Kendi metnin';
    }
    s.mod = m; s.metin = metin; s.metinNo = no; s.kutuphane = kut; s.baslik = baslik; s.sure = sure; s.kalan = sure;
    s.font = ayar.font; s.kayit.sifirla();
    var resmi = !!RESMI[m];
    $('sb-aday').textContent = ayar.aday || 'Misafir Aday';
    $('sb-klavye').textContent = ayar.klavye;
    $('sb-metin').textContent = m === 'sinav' ? 'Sistem seçimi' : baslik;
    $('sb-alt').textContent = resmi ? 'Klavye uygulaması · resmi kriterlerle değerlendirilir' : MODLAR[m].ust + ' · ' + sureYaz(sure);
    $('canli').hidden = resmi || !ayar.canli;
    $('sb-sure').classList.toggle('gizli', !resmi && !ayar.sureGoster);
    $('sb-sure').classList.remove('az');
    $('s-bitir').textContent = resmi ? 'Sınavı bitir' : 'Bitir';
    // Metni kelime kelime yerleştir (metin takibi için)
    var kutu = $('s-metin'); kutu.textContent = '';
    var parca = document.createDocumentFragment();
    metin.split(' ').forEach(function (w, i) { if (i) parca.append(' '); parca.append(E('span', null, w)); });
    kutu.append(parca); kutu.scrollTop = 0;
    s.spanlar = kutu.querySelectorAll('span'); s.vurgu = null;
    fontUygula();
    yazim.value = ''; yazim.disabled = true;
    canliYaz({ dogru: 0, hatali: 0, atlanan: 0, net: 0 });
    $('sb-sure-d').textContent = sureYaz(sure);
    $('sonuc').hidden = true; $('s-dur').hidden = true;
    $('sinav').hidden = false; document.body.classList.add('kt-sinavda');
    A('tikla', { a: 'katip-basla', x: m === 'sinav' ? 'sinav-' + kut : m });
    geriSayim();
  }
  function fontUygula() { $('s-metin').style.fontSize = s.font + 'px'; yazim.style.fontSize = s.font + 'px'; }

  function geriSayim() {
    s.durum = 'geri';
    var n = 3, o = $('s-geri');
    o.hidden = false; $('s-geri-sayi').textContent = n;
    clearInterval(s.zaman);
    s.zaman = setInterval(function () {
      n--; $('s-geri-sayi').textContent = n;
      if (n <= 0) { clearInterval(s.zaman); o.hidden = true; yazmaBasla(); }
    }, 1000);
  }
  function yazmaBasla() {
    s.durum = 'yaziyor'; s.bas = performance.now();
    yazim.disabled = false; yazim.focus();
    clearInterval(s.zaman);
    s.zaman = setInterval(function () {
      s.kalan = Math.max(0, s.sure - (performance.now() - s.bas) / 1000);
      $('sb-sure-d').textContent = sureYaz(s.kalan);
      $('sb-sure').classList.toggle('az', s.kalan <= 15);
      if (!$('canli').hidden) canliHesapla();
      if (s.kalan <= 0) bitir(true);
    }, 200);
  }
  function canliYaz(r) { $('c-dogru').textContent = r.dogru; $('c-hatali').textContent = r.hatali; $('c-atla').textContent = r.atlanan; $('c-net').textContent = r.net; }
  function canliHesapla() {
    var t = performance.now();
    if (t - s.sonCanli < 1500) return;
    s.sonCanli = t;
    canliYaz(P.puanla(s.metin, yazim.value, { sure: s.sure, saniye: s.sure - s.kalan }));
  }

  function bitir(sureDoldu) {
    if (s.durum !== 'yaziyor') return;
    clearInterval(s.zaman);
    s.durum = 'bitti'; yazim.disabled = true;
    var saniye = Math.min(s.sure, (performance.now() - s.bas) / 1000);
    $('s-dur').hidden = false;
    setTimeout(function () {
      $('s-dur').hidden = true;
      var r = P.puanla(s.metin, yazim.value, { sure: s.sure, saniye: sureDoldu ? s.sure : saniye });
      sonucGoster(r, sureDoldu);
    }, sureDoldu ? 1400 : 300);
  }
  function kapat() {
    clearInterval(s.zaman); s.durum = 'bos';
    $('sinav').hidden = true; document.body.classList.remove('kt-sinavda');
    $('s-geri').hidden = true; $('s-dur').hidden = true;
    ozetCiz();
  }

  /* ---------- sonuç tutanağı ---------- */
  function satirlar(tablo, liste) {
    tablo.textContent = '';
    liste.forEach(function (x) { var tr = E('tr', x[2] || ''); tr.append(E('td', null, x[0]), E('td', null, String(x[1]))); tablo.append(tr); });
  }
  var sonSonuc = null;
  function sonucGoster(r) {
    sonSonuc = r; r.mod = s.mod; r.tarih = new Date();
    var tarih = r.tarih;
    $('tt-alt').textContent = (ayar.aday || 'Misafir Aday') + ' · ' + MODLAR[s.mod].ust + ' · ' + s.baslik + ' · ' + sureYaz(r.saniye) + ' · ' + tarih.toLocaleString('tr-TR', { dateStyle: 'medium', timeStyle: 'short' });
    var k = $('tt-karar');
    k.textContent = r.basarili ? 'BAŞARILI' : 'BAŞARISIZ';
    k.className = 'kt-karar ' + (r.basarili ? 'basarili' : 'basarisiz');
    satirlar($('tt-kelime'), [
      ['Toplam yazılan kelime', r.toplam], ['Doğru kelime', r.dogru], ['Hatalı kelime', r.hatali],
      ['  └ fazla boşluk hatası', r.fazlaBosluk], ['Atlanan kelime', r.atlanan], ['Eksik son kelime', r.eksikSon ? '“' + r.eksikSon + '”' : '—'],
      ['Hata oranı', '%' + r.oran.toFixed(2).replace('.', ',')], ['Net kelime', r.net, 'vurgu']
    ]);
    $('tt-baraj').textContent = 'Baraj: ' + sureYaz(r.sure) + ' sürede en az ' + r.baraj + ' net kelime · toplam atlama 22\'nin altında · hata oranı en çok %25.';
    satirlar($('tt-vurus'), [
      ['Toplam vuruş', r.vurus], ['Doğru kelimelerdeki vuruş', r.dogruVurus], ['Dakikadaki vuruş', r.dakikaVurus],
      ['Dakikadaki net kelime', r.dakikaNet], ['Süre', sureYaz(r.saniye)], ['Klavye', 'Türkçe ' + ayar.klavye]
    ]);
    $('tt-neden-kap').hidden = r.basarili || !r.toplam;
    $('tt-neden').textContent = r.nedenler.length ? 'Başarısızlık nedeni: ' + r.nedenler.join(' · ') : '';
    var tl = Object.keys(r.turler).sort(function (a, b) { return r.turler[b] - r.turler[a]; }).map(function (t) { return [P.TUR_AD[t], r.turler[t]]; });
    satirlar($('tt-turler'), tl.length ? tl : [['Hata yok', 0]]);
    var ht = $('tt-hatalar'); ht.textContent = '';
    if (!r.hatalar.length) { var tr0 = E('tr'); tr0.append(E('td', null, 'Tebrikler, hatalı kelimen yok.')); ht.append(tr0); }
    r.hatalar.forEach(function (h) {
      var tr = E('tr'), td = E('td');
      if (h.a) td.append(E('del', null, h.a)); if (h.a && h.b) td.append(' → '); if (h.b) td.append(E('ins', null, h.b));
      tr.append(td, E('td', null, h.ad + (h.adet > 1 ? ' ×' + h.adet : ''))); ht.append(tr);
    });
    // Klavye analizi: tuş hızları vuruş kaydından, tuş hataları hatalı kelimelerin harf hizalamasından
    var ek = [];
    r.hatalar.forEach(function (h) { if (h.a && h.b && h.tur !== 'fazla-bosluk') ek = ek.concat(KK.harfHatalari(h.a.replace(/ /g, ''), h.b.replace(/ /g, ''))); });
    var analiz = KK.analiz(s.kayit.vuruslar, ayar.klavye, ek);
    $('tt-analiz-kap').hidden = s.kayit.vuruslar.length < 30;
    if (s.kayit.vuruslar.length >= 30) { KK.analizCiz($('tt-analiz'), analiz, ayar.klavye); KK.birlestir(analiz); }
    // Karşılaştırma
    var ks = $('tt-karsi'); ks.textContent = '';
    r.adimlar.forEach(function (a, i) {
      if (i) ks.append(' ');
      if (a.t === 'dogru') ks.append(a.a);
      else if (a.t === 'atla') ks.append(E('span', 'atla', a.a));
      else if (a.t === 'eksik-son') ks.append(E('span', 'yarim', a.b + '…'));
      else { if (a.a) ks.append(E('del', null, a.a)); if (a.b) ks.append(E('ins', null, a.b)); }
    });
    if (!r.adimlar.length) ks.textContent = 'Hiç kelime yazılmadı.';
    // Kayıt, hatalı kelimeler, rozetler, günün metni
    var yeniRozet = [];
    if (r.toplam) {
      veri.gecmis.unshift({ t: tarih.getTime(), m: s.mod, s: Math.round(r.sure), top: r.toplam, hat: r.hatali, atl: r.atlanan, net: r.net, dk: r.dakikaNet, b: r.basarili ? 1 : 0, no: s.metinNo, k: s.kutuphane });
      veri.gecmis = veri.gecmis.slice(0, 300);
      r.hatalar.forEach(function (h) { if (h.a && h.tur !== 'fazla-bosluk') h.a.split(' ').forEach(function (w) { veri.hatalar[w] = (veri.hatalar[w] || 0) + 1; }); });
      var anahtarlar = Object.keys(veri.hatalar);
      if (anahtarlar.length > 400) anahtarlar.sort(function (a, b) { return veri.hatalar[a] - veri.hatalar[b]; }).slice(0, anahtarlar.length - 400).forEach(function (w) { delete veri.hatalar[w]; });
      if (s.mod === 'gunluk' && !veri.gunluk[O.bugunAnahtar()]) veri.gunluk[O.bugunAnahtar()] = { net: r.net, top: r.toplam, hat: r.hatali, b: r.basarili ? 1 : 0 };
      yeniRozet = rozetKontrol();
      kaydet();
    }
    var yr = $('yeni-rozet');
    yr.hidden = !yeniRozet.length;
    yr.textContent = yeniRozet.length ? 'Yeni rozet kazandın: ' + yeniRozet.map(function (x) { return x.ad; }).join(', ') + ' 🎉' : '';
    $('r-hatali').hidden = r.hatalar.filter(function (h) { return h.a; }).length === 0;
    $('r-tekrar').hidden = s.metinNo < 0 || s.mod === 'gunluk';
    liderHazirla(r);
    $('sonuc').hidden = false; $('sonuc').scrollTop = 0;
    $('r-yeni').focus();
    A('tikla', { a: 'katip-bitti', x: s.mod + (r.basarili ? '-basarili' : '-basarisiz'), n: r.net });
  }

  /* ---------- rozetler, seri, grafik ---------- */
  function sinavMi(x) { return x.m === 'sinav' || x.m === 'gunluk'; }
  var ROZETLER = [
    { id: 'ilk', ad: 'İlk adım', kosul: function (g) { return g.length >= 1; } },
    { id: 'baraj', ad: 'Baraj geçildi (90 net)', kosul: function (g) { return g.some(function (x) { return sinavMi(x) && x.b; }); } },
    { id: 'n100', ad: '100 net', kosul: function (g) { return g.some(function (x) { return sinavMi(x) && x.net >= 100; }); } },
    { id: 'n120', ad: '120 net', kosul: function (g) { return g.some(function (x) { return sinavMi(x) && x.net >= 120; }); } },
    { id: 'n150', ad: '150 net', kosul: function (g) { return g.some(function (x) { return sinavMi(x) && x.net >= 150; }); } },
    { id: 'temiz', ad: 'Hatasız sınav', kosul: function (g) { return g.some(function (x) { return sinavMi(x) && x.hat === 0 && x.net >= 60; }); } },
    { id: 'gunluk', ad: 'Günün metni', kosul: function () { return Object.keys(veri.gunluk).length >= 1; } },
    { id: 'resmi30', ad: '30 resmî metin', kosul: function (g) { var k = {}; g.forEach(function (x) { if (x.k === 'zk2025' && x.no >= 0) k[x.no] = 1; }); return Object.keys(k).length >= 30; } },
    { id: 'seri3', ad: '3 gün seri', kosul: function () { return seri() >= 3; } },
    { id: 'seri7', ad: '7 gün seri', kosul: function () { return seri() >= 7; } },
    { id: 'seri30', ad: '30 gün seri', kosul: function () { return seri() >= 30; } },
    { id: 'd10', ad: '10 deneme', kosul: function (g) { return g.length >= 10; } },
    { id: 'd50', ad: '50 deneme', kosul: function (g) { return g.length >= 50; } }
  ];
  function rozetKontrol() {
    var yeni = [];
    ROZETLER.forEach(function (r) { if (veri.rozetler.indexOf(r.id) < 0 && r.kosul(veri.gecmis)) { veri.rozetler.push(r.id); yeni.push(r); } });
    return yeni;
  }
  function gun(t) { var d = new Date(t); return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate(); }
  function seri() {
    var gunler = {}; veri.gecmis.forEach(function (x) { gunler[gun(x.t)] = 1; });
    var d = new Date(), n = 0;
    if (!gunler[gun(d)]) d.setDate(d.getDate() - 1);
    while (gunler[gun(d)]) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }
  function grafikCiz() {
    var g = veri.gecmis.filter(sinavMi).slice(0, 20).reverse(), kap = $('grafik');
    if (!g.length) { kap.innerHTML = '<p class="muted" style="margin:14px 0 4px">İlk sınav simülasyonunu yaptığında net kelime gelişimin burada görünecek.</p>'; return; }
    var W = 600, H = 190, sol = 30, alt = 22, ust = 12, en = Math.max(130, Math.max.apply(null, g.map(function (x) { return x.net; })) + 10);
    var X = function (i) { return sol + (g.length === 1 ? (W - sol) / 2 : i * (W - sol - 10) / (g.length - 1)); };
    var Y = function (v) { return ust + (H - ust - alt) * (1 - v / en); };
    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Son sınav simülasyonlarında net kelime">';
    [0, 50, 100, 150].forEach(function (v) { if (v <= en) svg += '<line class="eks" x1="' + sol + '" x2="' + W + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/><text x="0" y="' + (Y(v) + 4) + '">' + v + '</text>'; });
    svg += '<line class="baraj" x1="' + sol + '" x2="' + W + '" y1="' + Y(90) + '" y2="' + Y(90) + '"/><text x="' + (W - 60) + '" y="' + (Y(90) - 5) + '">baraj 90</text>';
    var noktalar = g.map(function (x, i) { return X(i) + ',' + Y(x.net); }).join(' ');
    svg += '<defs><linearGradient id="kt-cizgi" x1="0" x2="1"><stop offset="0" stop-color="var(--k-lime)"/><stop offset=".6" stop-color="var(--k-mavi)"/><stop offset="1" stop-color="var(--k-mor)"/></linearGradient>'
      + '<linearGradient id="kt-alan" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--k-mavi)" stop-opacity=".32"/><stop offset="1" stop-color="var(--k-mavi)" stop-opacity="0"/></linearGradient></defs>';
    if (g.length > 1) svg += '<polygon class="alan" fill="url(#kt-alan)" points="' + X(0) + ',' + Y(0) + ' ' + noktalar + ' ' + X(g.length - 1) + ',' + Y(0) + '"/>';
    svg += '<polyline class="cizgi" stroke="url(#kt-cizgi)" style="stroke:url(#kt-cizgi);stroke-width:3.5" points="' + noktalar + '"/>';
    g.forEach(function (x, i) { svg += '<circle class="nokta" cx="' + X(i) + '" cy="' + Y(x.net) + '" r="4"><title>' + x.net + ' net</title></circle>'; });
    kap.innerHTML = svg + '</svg>';
  }
  var MOD_KISA = { sinav: 'Sınav', antrenman: 'Antrenman', hatali: 'Hatalılar', isinma: 'Isınma', ozel: 'Kendi metni', gunluk: 'Günün metni' };
  function ozetCiz() {
    var g = veri.gecmis, sinavlar = g.filter(sinavMi);
    $('o-en').textContent = sinavlar.length ? Math.max.apply(null, sinavlar.map(function (x) { return x.net; })) : '—';
    $('o-son').textContent = sinavlar.length ? sinavlar[0].net : '—';
    $('o-seri').textContent = seri() + (seri() ? ' gün' : '');
    $('o-sayi').textContent = g.length;
    var bugun = g.filter(function (x) { return gun(x.t) === gun(Date.now()); }).length;
    $('o-hedef').textContent = Math.min(bugun, 3) + '/3';
    $('o-hedef-cubuk').style.width = Math.min(100, bugun / 3 * 100) + '%';
    var rz = $('rozetler'); rz.textContent = '';
    ROZETLER.forEach(function (r) { var v = veri.rozetler.indexOf(r.id) >= 0; rz.append(E('span', 'kt-rozet' + (v ? ' var' : ''), (v ? '★ ' : '☆ ') + r.ad)); });
    var tb = $('gecmis'); tb.textContent = '';
    if (!g.length) { var tr0 = E('tr'), td0 = E('td', 'muted', 'Henüz deneme yok.'); td0.colSpan = 8; tr0.append(td0); tb.append(tr0); }
    g.slice(0, 15).forEach(function (x) {
      var tr = E('tr');
      tr.append(E('td', null, new Date(x.t).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })), E('td', null, MOD_KISA[x.m] || x.m),
        E('td', 'sag', sureYaz(x.s)), E('td', 'sag', x.top), E('td', 'sag', x.hat), E('td', 'sag', x.atl), E('td', 'sag', x.net),
        E('td', x.b ? 'kt-iyi' : 'kt-kotu', x.b ? 'Başarılı' : 'Başarısız'));
      tb.append(tr);
    });
    grafikCiz(); defterCiz(); gunlukCiz(); yolCiz();
  }

  /* ---------- hata defteri ---------- */
  function defterCiz() {
    var d = $('defter'), h = hataliHavuz().slice(0, 24);
    d.textContent = '';
    if (!h.length) d.append(E('span', 'muted', 'Henüz hatalı kelimen yok.'));
    h.forEach(function (w) { var e = E('span', null, w); e.append(E('b', null, '×' + veri.hatalar[w])); d.append(e); });
    $('defter-calis').disabled = h.length < 5;
  }

  /* ---------- günün metni ---------- */
  function gunlukSeri() {
    var d = new Date(), n = 0;
    if (!veri.gunluk[O.bugunAnahtar(d)]) d.setDate(d.getDate() - 1);
    while (veri.gunluk[O.bugunAnahtar(d)]) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }
  function gunlukCiz() {
    var b = veri.gunluk[O.bugunAnahtar()];
    $('g-tarih').textContent = 'Günün metni · ' + new Date().toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', weekday: 'long' });
    $('g-sonuc').hidden = !b; $('g-paylas').hidden = !b;
    if (b) $('g-sonuc').textContent = 'Bugünkü sonucun: ' + b.net + ' net · ' + b.hat + ' hata · ' + (b.b ? 'BAŞARILI' : 'baraj altında') + (gunlukSeri() > 1 ? ' · ' + gunlukSeri() + ' gün üst üste' : '') + '. Tekrar yazabilirsin ama kayıt ilk denemedir.';
    $('g-basla').textContent = b ? 'Tekrar yaz (kayda geçmez)' : 'Günün metnini yaz · 3:00';
  }
  function gunlukPaylasimMetni() {
    var b = veri.gunluk[O.bugunAnahtar()];
    if (!b) return '';
    var yesil = b.top ? Math.round((b.top - b.hat) / b.top * 10) : 0;
    return 'Günün duruşması ' + O.bugunAnahtar().split('-').reverse().join('.') + ' · ' + b.net + ' net ' + (b.b ? '✅' : '❌') + '\n' +
      '🟩'.repeat(yesil) + '🟥'.repeat(10 - yesil) + (gunlukSeri() > 1 ? '\n🔥 ' + gunlukSeri() + ' gün seri' : '');
  }

  /* ---------- 90 net yol haritası ---------- */
  function yolCiz() {
    var kap = $('y-sonuc'); kap.textContent = '';
    var hedef = Math.max(30, Math.min(250, Number(veri.yol.hedef) || 90));
    var g = veri.gecmis.filter(function (x) { return sinavMi(x) && x.s === 180; });
    if (!g.length) return;   // ilk sınavdan sonra dolar
    var son5 = g.slice(0, 5), ort = Math.round(son5.reduce(function (t, x) { return t + x.net; }, 0) / son5.length);
    // Son 30 gündeki denemelerden günlük artış eğilimi (doğrusal regresyon)
    var simdi = Date.now(), noktalar = g.filter(function (x) { return simdi - x.t < 30 * 864e5; }).map(function (x) { return [(x.t - simdi) / 864e5, x.net]; });
    var egim = 0;
    if (noktalar.length >= 3) {
      var mx = 0, my = 0; noktalar.forEach(function (p) { mx += p[0]; my += p[1]; }); mx /= noktalar.length; my /= noktalar.length;
      var pay = 0, payda = 0; noktalar.forEach(function (p) { pay += (p[0] - mx) * (p[1] - my); payda += (p[0] - mx) * (p[0] - mx); });
      egim = payda > 0.5 ? Math.max(-2, Math.min(2.5, pay / payda)) : 0;
    }
    var kalan = veri.yol.tarih ? Math.ceil((new Date(veri.yol.tarih + 'T09:00').getTime() - simdi) / 864e5) : 0;
    // Öğrenme eğrisi zamanla yavaşlar: doğrusal eğimi uzun vadeye olduğu gibi taşımak abartılı tahmin verir (ör. 93 → 223).
    // Artışı ilk haftadan sonra yarıya indir ve toplamda en çok +35 net, üst sınır 160 net kabul et.
    var artis = egim > 0 ? egim * Math.min(kalan, 7) + egim * 0.5 * Math.max(0, Math.min(kalan, 60) - 7) : egim * Math.min(kalan, 14);
    var tahmin = kalan > 0 ? Math.max(0, Math.min(160, Math.round(ort + Math.max(-20, Math.min(35, artis))))) : null;
    var t = E('div', 'kt-yol-tahmin');
    [[ort, 'Son ' + son5.length + ' sınav ortalaması'], [(egim >= 0 ? '+' : '') + egim.toFixed(1), 'Günlük değişim (net)'], [kalan > 0 ? kalan : '—', 'Sınava kalan gün'], [tahmin != null ? tahmin : '—', 'Sınav günü tahmini']].forEach(function (x) {
      var d = E('div'); d.append(E('b', null, String(x[0])), E('span', null, x[1])); t.append(d);
    });
    kap.append(t);
    var guvenli = hedef + 10, fark = guvenli - ort, plan = [];
    if (fark <= 0) {
      kap.append(E('p', null, 'Hedefinin güvenli payla (+10) üzerindesin. Formu korumak için:'));
      plan = ['Her gün günün metnini yaz (3 dk).', 'Haftada üç gün 2 sınav simülasyonu; hatasız yazmaya odaklan.', 'Sınavdan önceki gün yalnız ısınma ve tek deneme yap.'];
    } else {
      var gunluk = kalan > 0 ? fark / kalan : null;
      var dk = Math.min(90, Math.max(20, Math.round(fark * 1.2)));
      kap.append(E('p', null, 'Güvenli hedef ' + guvenli + ' net (baraj + 10 pay). Aradaki fark ' + fark + ' net' + (gunluk ? '; günde ortalama ' + gunluk.toFixed(1) + ' net artış gerekiyor' : '') + '. Önerilen günlük program (yaklaşık ' + dk + ' dakika):'));
      plan = ['5 dk Türkçe karakter ısınması.', (ort < 60 ? '20 dk klavye dersi (temel sıra ve kelimeler), ' : '10 dk kelime antrenmanı (zayıf tuşlar), ') + 'ardından 5 dk hatalı kelimeler tekrarı.',
        'Günün metni + ' + (fark > 30 ? '3' : '2') + ' sınav simülasyonu; her birinden sonra tutanaktaki hata türlerini incele.',
        ort < 60 ? 'Hız yerine doğruluk: %97 doğruluğa ulaşmadan tempoyu artırma.' : 'Uzun kelimeler ve mevzuat metinleriyle haftada iki ek oturum.'];
      if (kalan > 0 && gunluk > 2.5) plan.push('Kalan süre için fark büyük; günde iki ayrı oturuma bölmek (sabah/akşam) daha verimli olur.');
    }
    var ol = E('ol'); plan.forEach(function (x) { ol.append(E('li', null, x)); }); kap.append(ol);
    if (!veri.yol.tarih) kap.append(E('p', 'not-kucuk', 'Sınav tarihini girersen kalan güne göre tahmin de gösterilir.'));
  }

  /* ---------- sonuç kartı (paylaşılabilir görsel) ---------- */
  function sonucKarti(r) {
    var c = document.createElement('canvas'), W = 1080, H = 1080; c.width = W; c.height = H;
    var x = c.getContext('2d');
    x.fillStyle = '#F6F6F1'; x.fillRect(0, 0, W, H);
    x.fillStyle = '#111310'; x.fillRect(0, 0, W, 150);
    x.fillStyle = '#C8F169'; x.font = '700 44px Inter, Arial, sans-serif'; x.fillText('KPSS Tercihi', 70, 95);
    x.fillStyle = '#FFFFFF'; x.font = '500 30px Inter, Arial, sans-serif'; x.textAlign = 'right'; x.fillText('Katiplik klavye sınavı', W - 70, 93); x.textAlign = 'left';
    x.fillStyle = '#6C7166'; x.font = '600 34px Inter, Arial, sans-serif'; x.fillText(MODLAR[r.mod].ust + ' · ' + sureYaz(r.sure) + ' · Türkçe ' + ayar.klavye, 70, 240);
    x.fillStyle = '#111310'; x.font = '800 300px Inter, Arial, sans-serif'; x.fillText(String(r.net), 60, 540);
    x.font = '700 56px Inter, Arial, sans-serif'; x.fillText('net kelime', 80, 620);
    var ok = r.basarili; x.fillStyle = ok ? '#C8F169' : '#FFE1D6'; x.fillRect(70, 670, 440, 90);
    x.fillStyle = ok ? '#3D5C05' : '#C2410C'; x.font = '800 46px Inter, Arial, sans-serif'; x.fillText(ok ? 'BAŞARILI' : 'BARAJ ALTINDA', 100, 732);
    x.fillStyle = '#3B3F37'; x.font = '500 36px Inter, Arial, sans-serif';
    [['Toplam', r.toplam], ['Hatalı', r.hatali], ['Atlanan', r.atlanan], ['Hata oranı', '%' + r.oran.toFixed(1).replace('.', ',')]].forEach(function (s2, i) {
      var px = 70 + (i % 2) * 470, py = 850 + Math.floor(i / 2) * 70; x.fillStyle = '#6C7166'; x.fillText(s2[0], px, py); x.fillStyle = '#111310'; x.font = '700 36px Inter, Arial, sans-serif'; x.fillText(String(s2[1]), px + 230, py); x.font = '500 36px Inter, Arial, sans-serif';
    });
    x.fillStyle = '#9A9E93'; x.font = '500 28px Inter, Arial, sans-serif'; x.fillText('kpsstercihi.com/katiplik · ' + r.tarih.toLocaleDateString('tr-TR'), 70, 1040);
    return c;
  }

  /* ---------- metin takibi ---------- */
  function takip() {
    if (RESMI[s.mod] || !ayar.takip || !s.spanlar) return;
    var v = yazim.value, n = v.trim() ? v.trim().split(/\s+/).length : 0;
    if (v && !/\s$/.test(v)) n--;
    var el = s.spanlar[Math.max(0, n)];
    if (el === s.vurgu) return;
    if (s.vurgu) s.vurgu.classList.remove('su-an');
    s.vurgu = el;
    if (el) {
      el.classList.add('su-an');
      var k = $('s-metin'), y = el.offsetTop - k.offsetTop;
      if (y < k.scrollTop || y > k.scrollTop + k.clientHeight - 40) k.scrollTop = y - k.clientHeight / 3;
    }
  }

  /* ---------- liderlik tablosu ----------
     Yalnız kullanıcı "Ekle" derse gönderilir: takma ad + yazılan metin. Sunucu neti resmî kriterlerle kendisi hesaplar,
     metni saklamaz. Tarayıcı kimliği rastgele bir anahtardır ('kit-katip-lider'). */
  var LIDER_URL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname) ? 'http://localhost:8787/liderlik' : 'https://api.kpsstercihi.com/liderlik';
  var lider = O.oku('kit-katip-lider', null);
  if (!lider || typeof lider !== 'object' || !/^[a-f0-9]{32}$/.test(lider.anahtar || '')) {
    var rb = new Uint8Array(16); crypto.getRandomValues(rb);
    lider = { anahtar: [].map.call(rb, function (x) { return (x + 256).toString(16).slice(1); }).join(''), ad: '', kimlik: '' };
  }
  var liderTablo = null, liderSekme = 'haftalik', liderAday = null;
  var MADALYA = ['🥇', '🥈', '🥉'];
  var LIDER_HATA = {
    ad: 'Bu takma ad kullanılamıyor; 2–18 harf/rakam olan başka bir ad dene.', kisa: 'Tabloya girmek için biraz daha yazmalısın.',
    supheli: 'Bu sonuç doğrulanamadı.', hiz: 'Çok sık gönderdin; birkaç dakika sonra tekrar dene.', kota: 'Tablo şu an yoğun; biraz sonra tekrar dene.'
  };

  function liderCiz() {
    var ol = $('lider-liste'), liste = liderTablo ? liderTablo[liderSekme] || [] : [];
    ol.textContent = '';
    $('lider-bos').hidden = !liderTablo || liste.length > 0;
    $('lider-bos').textContent = liderSekme === 'haftalik' ? 'Bu hafta henüz kimse yok. İlk sen ol!' : 'Henüz kimse yok. İlk sen ol!';
    liste.forEach(function (x, i) {
      var li = E('li', (x.i && x.i === lider.kimlik ? 'ben ' : '') + (i < 3 ? 'ilk' + (i + 1) : ''));
      li.append(E('span', 'sira', i < 3 ? MADALYA[i] : String(i + 1)), E('span', 'ad', x.ad), E('span', 'dk', x.dk + ' vuruş/dk'), E('b', 'net', x.net + ' net'));
      ol.append(li);
    });
  }
  function liderYukle() {
    fetch(LIDER_URL).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { if (j) { liderTablo = j; liderCiz(); } }).catch(function () {});
  }
  [].forEach.call(document.querySelectorAll('[data-lt]'), function (b) {
    b.onclick = function () {
      liderSekme = b.dataset.lt;
      [].forEach.call(document.querySelectorAll('[data-lt]'), function (x) { x.classList.toggle('secili', x === b); x.setAttribute('aria-pressed', x === b); });
      liderCiz();
    };
  });

  // Sonuç ekranında "tabloya ekle" kutusu: 3 dk resmî koşullar, 2025 resmî metinleri ve fiziksel klavye.
  function liderHazirla(r) {
    var kutu = $('lider-ekle'), uygun = (s.mod === 'sinav' || s.mod === 'gunluk') && s.kutuphane === 'zk2025' && s.metinNo >= 0 && r.toplam >= 10 && r.net >= 1;
    liderAday = null;
    kutu.hidden = !uygun;
    if (!uygun) return;
    var klavyeli = s.kayit.vuruslar.length >= yazim.value.replace(/\s+$/, '').length * 0.9;
    liderAday = klavyeli ? { mod: s.mod, kut: s.kutuphane, no: s.metinNo, yazi: yazim.value, vurus: s.kayit.vuruslar.length } : null;
    kutu.classList.remove('tamam');
    $('lider-form').hidden = !klavyeli;
    $('lider-ad').value = lider.ad || (ayar.aday && ayar.aday !== 'Misafir Aday' ? ayar.aday.slice(0, 18) : '');
    $('lider-gonder').disabled = false;
    $('lider-ekle-alt').textContent = klavyeli ? r.net + ' net ile bu haftanın tablosuna gir.' : 'Liderlik tablosu yalnız fiziksel klavyeyle yapılan sınavları kabul eder.';
  }
  function liderGonder() {
    if (!liderAday) return;
    var ad = $('lider-ad').value.replace(/\s+/g, ' ').trim();
    if (ad.length < 2) { $('lider-ad').focus(); $('lider-ekle-alt').textContent = 'Önce bir takma ad yaz (2–18 karakter).'; return; }
    var b = $('lider-gonder'); b.disabled = true;
    $('lider-ekle-alt').textContent = 'Gönderiliyor…';
    var g = Object.assign({ ad: ad, anahtar: lider.anahtar }, liderAday);
    fetch(LIDER_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=UTF-8' }, body: JSON.stringify(g) })
      .then(function (r) { return r.json().catch(function () { return { hata: 'ag' }; }); })
      .then(function (j) {
        if (!j.ok) { b.disabled = false; $('lider-ekle-alt').textContent = LIDER_HATA[j.hata] || 'Gönderilemedi; bağlantını kontrol edip tekrar dene.'; return; }
        lider.ad = ad; lider.kimlik = j.kimlik; O.yaz('kit-katip-lider', lider);
        liderTablo = j.tablo; liderCiz(); liderAday = null;
        $('lider-ekle').classList.add('tamam'); $('lider-form').hidden = true;
        $('lider-ekle-alt').textContent = 'Bu hafta ' + j.sira + '. sıradasın' + (j.sira <= 3 ? ' ' + MADALYA[j.sira - 1] : '') + ' · tablo ana sayfada.';
        A('tikla', { a: 'katip-lider', x: 'ekle', n: j.net });
      })
      .catch(function () { b.disabled = false; $('lider-ekle-alt').textContent = 'Gönderilemedi; bağlantını kontrol edip tekrar dene.'; });
  }
  $('lider-gonder').onclick = liderGonder;
  $('lider-ad').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); liderGonder(); } });

  /* ---------- olaylar ---------- */
  [].forEach.call(document.querySelectorAll('.kt-mod'), function (b) { b.onclick = function () { modSec(b.dataset.mod, true); A('tikla', { a: 'katip-mod', x: b.dataset.mod }); }; });
  [].forEach.call(document.querySelectorAll('#sure-sec .tab'), function (b) { b.onclick = function () { surSec(Number(b.dataset.v)); kaydet(); modSec(mod); }; });
  $('kutuphane-sec').onchange = function () { ayar.metin = -1; kutuphaneYukle(this.value); A('tikla', { a: 'katip-kutuphane', x: this.value }); };
  $('metin-sec').onchange = function () { ayar.metin = Number(this.value); kaydet(); };
  $('aday').oninput = function () { ayar.aday = this.value.trim().slice(0, 40); kaydet(); };
  $('klavye').onchange = function () { ayar.klavye = this.value === 'F' ? 'F' : 'Q'; kaydet(); };
  [['o-canli', 'canli'], ['o-takip', 'takip'], ['o-ses', 'ses'], ['o-sure', 'sureGoster']].forEach(function (p) {
    $(p[0]).onchange = function () { ayar[p[1]] = this.checked; kaydet(); };
  });
  $('basla').onclick = function () { sinavAc(mod); };
  $('hemen-sinav').onclick = function () { modSec('sinav'); sinavAc('sinav'); };
  $('g-basla').onclick = function () { sinavAc('gunluk'); };
  $('g-paylas').onclick = function () { paylas(this, gunlukPaylasimMetni() + '\n', 'https://kpsstercihi.com/katiplik/?utm_source=paylas&utm_medium=gunluk#gunun-metni', 'Günün duruşması'); };
  $('defter-calis').onclick = function () { modSec('hatali'); sinavAc('hatali'); };
  $('y-tarih').onchange = function () { veri.yol.tarih = this.value; kaydet(); yolCiz(); A('tikla', { a: 'katip-yol', x: 'tarih' }); };
  $('y-hedef').oninput = function () { var v = Number(this.value.replace(/\D/g, '')); if (v) { veri.yol.hedef = v; kaydet(); yolCiz(); } };
  $('gecmis-sil').onclick = function () {
    if (!confirm('Tüm deneme geçmişin, hatalı kelimelerin, günlük sonuçların ve rozetlerin silinsin mi?')) return;
    veri.gecmis = []; veri.hatalar = {}; veri.rozetler = []; veri.gunluk = {}; O.yaz('kit-katip', veri); ozetCiz(); modSec(mod);
  };

  yazim.addEventListener('keydown', function (e) {
    if (s.durum !== 'yaziyor') { e.preventDefault(); return; }
    if (e.key === 'Tab' || e.key === 'Enter') { e.preventDefault(); return; }
    if ((e.ctrlKey || e.metaKey) && /^[vxyz]$/i.test(e.key)) { e.preventDefault(); return; }
    if (e.key.length === 1) s.kayit.ekle(null, e.key.toLocaleLowerCase('tr-TR'));
    if (ayar.ses && !RESMI[s.mod] && (e.key.length === 1 || e.key === 'Backspace')) KK.Ses.tik();
  });
  yazim.addEventListener('input', takip);
  ['paste', 'drop', 'cut', 'contextmenu'].forEach(function (t) { yazim.addEventListener(t, function (e) { e.preventDefault(); }); });
  $('s-metin').addEventListener('copy', function (e) { e.preventDefault(); });
  $('s-bitir').onclick = function () { if (s.durum === 'yaziyor' && confirm('Süre dolmadan bitirmek istiyor musun?')) bitir(false); };
  $('s-iptal').onclick = function () { if (s.durum !== 'yaziyor' || confirm('Bu deneme kaydedilmeden kapatılsın mı?')) kapat(); };
  [].forEach.call(document.querySelectorAll('[data-font]'), function (b) {
    b.onclick = function () { s.font = Math.max(11, Math.min(26, s.font + Number(b.dataset.font))); ayar.font = s.font; kaydet(); fontUygula(); if (s.durum === 'yaziyor') yazim.focus(); };
  });
  $('r-yeni').onclick = function () { sinavAc(s.mod === 'gunluk' ? 'sinav' : s.mod); };
  $('r-tekrar').onclick = function () { sinavAc(s.mod, { metinNo: s.metinNo }); };
  $('r-hatali').onclick = function () { modSec('hatali'); sinavAc('hatali'); };
  $('r-kapat').onclick = kapat;
  function paylas(b, metin, url, baslik) {
    var eski = b.textContent;
    if (navigator.share) { navigator.share({ title: baslik, text: metin, url: url }).catch(function () {}); return; }
    try { navigator.clipboard.writeText(metin + ' ' + url).then(function () { b.textContent = 'Kopyalandı!'; setTimeout(function () { b.textContent = eski; }, 1600); }); } catch (e) { /* pano kapalı */ }
  }
  $('r-paylas').onclick = function () {
    if (!sonSonuc) return;
    if (sonSonuc.mod === 'gunluk' && veri.gunluk[O.bugunAnahtar()]) return paylas(this, gunlukPaylasimMetni() + '\n', 'https://kpsstercihi.com/katiplik/?utm_source=paylas&utm_medium=gunluk#gunun-metni', 'Günün duruşması');
    var metin = 'Katiplik klavye simülasyonunda ' + sureYaz(sonSonuc.saniye) + ' sürede ' + sonSonuc.net + ' net kelime yazdım (' + sonSonuc.hatali + ' hata, ' + (sonSonuc.basarili ? 'BAŞARILI' : 'baraj altında') + '). Sen de dene:';
    paylas(this, metin, 'https://kpsstercihi.com/katiplik/?utm_source=paylas&utm_medium=katiplik', 'Katiplik klavye sınavı');
  };
  $('r-kart').onclick = function () {
    if (!sonSonuc) return;
    var c = sonucKarti(sonSonuc), b = this;
    c.toBlob(function (blob) {
      if (!blob) return;
      var dosya = new File([blob], 'katiplik-sonuc-' + sonSonuc.net + '-net.png', { type: 'image/png' });
      if (navigator.canShare && navigator.canShare({ files: [dosya] })) { navigator.share({ files: [dosya], title: 'Katiplik sonucum' }).catch(function () {}); return; }
      var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = dosya.name; document.body.append(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      b.textContent = 'İndirildi'; setTimeout(function () { b.textContent = 'Sonuç kartı (görsel)'; }, 1600);
    }, 'image/png');
    A('tikla', { a: 'katip-kart', n: sonSonuc.net });
  };
  document.addEventListener('keydown', function (e) {
    if ($('sinav').hidden) return;
    if (!$('sonuc').hidden) {
      if (e.key === 'Enter' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT') { e.preventDefault(); $('r-yeni').click(); }
      else if (e.key === 'Escape') kapat();
    } else if (e.key === 'Escape' && s.durum === 'geri') kapat();
  });
  window.addEventListener('beforeunload', function (e) { if (s.durum === 'yaziyor') { e.preventDefault(); e.returnValue = ''; } });

  /* ---------- başlangıç ---------- */
  kutuphaneDoldur();
  surSec(ayar.sure);
  $('aday').value = ayar.aday; $('klavye').value = ayar.klavye;
  $('o-canli').checked = ayar.canli; $('o-takip').checked = ayar.takip; $('o-ses').checked = ayar.ses; $('o-sure').checked = ayar.sureGoster;
  $('ozel-metin').value = veri.ozel;
  $('y-tarih').value = veri.yol.tarih; $('y-hedef').value = veri.yol.hedef;
  // Adres parametreleri (metin sayfalarından gelişler): ?k=kütüphane&m=metin sırası&mod=sinav|antrenman&basla=1
  var adres = new URLSearchParams(location.search), istenen = adres.get('mod');
  var istenenNo = /^\d+$/.test(adres.get('m') || '') ? Number(adres.get('m')) : null;
  if (KUT.bul(adres.get('k'))) ayar.kutuphane = adres.get('k');
  if (istenenNo != null && istenen === 'antrenman') ayar.metin = istenenNo;
  modSec(MODLAR[istenen] && istenen !== 'gunluk' ? istenen : 'sinav');
  $('g-basla').disabled = true;
  kutuphaneYukle(ayar.kutuphane).then(function () {
    if (adres.get('basla') !== '1' || (istenen && istenen !== 'sinav' && istenen !== 'antrenman')) return;
    sinavAc(mod, istenenNo != null && istenenNo < METINLER.length ? { metinNo: istenenNo } : {});
  });
  Promise.all([KUT.getir('zk2025'), KUT.getir('ozgun')]).then(function (r) {
    GUNLUK = r[0];
    var k = {};
    r.forEach(function (ml) { ml.forEach(function (m) { m[1].split(' ').forEach(function (w) { if (w.length >= 5 && (w.match(/[çğıöşü]/g) || []).length >= 2) k[w] = 1; }); }); });
    ISINMA = Object.keys(k);
    $('g-basla').disabled = false;
    if (istenen === 'gunluk') sinavAc('gunluk');
  });
  ozetCiz();
  liderYukle();
})();
