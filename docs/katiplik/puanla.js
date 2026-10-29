/* KPSS Tercihi — katiplik klavye uygulaması: değerlendirme motoru.
   Adalet Bakanlığı "Zabıt Kâtibi / İcra Kâtipliği Uygulamalı Sınav Değerlendirme Kriterleri"ne göre kelime bazlı sonuç:
   her hata türü 1 kelime hatası; doğru bölünen kelime 1, yanlış bölünen kelimenin her parçası 1 hata; birleştirme 1 hata;
   art arda iki ve üzeri boşluk 1 hata; atlanan kelime hata değil (toplam 22 ve üzeri başarısız); süre biterken yarım kalan
   son kelime hata değil; hatalı / toplam oranı %25'i aşarsa başarısız. Net = toplam yazılan − hatalı. */
(function (kok) {
  'use strict';

  var HARF = /^[a-zçğıöşüâîû]$/;
  var BANT = 60;          // hizalamada metin ile yazılan arasındaki en büyük kayma (kelime)
  var ATLAMA_SINIRI = 22;
  var HATA_ORANI_SINIRI = 25;

  var onbellek = new Map();
  function mesafe(a, b) {
    if (a === b) return 0;
    var anahtar = a + '|' + b, kayit = onbellek.get(anahtar);
    if (kayit !== undefined) return kayit;
    if (onbellek.size > 50000) onbellek.clear();
    kayit = hesapla(a, b);
    onbellek.set(anahtar, kayit);
    return kayit;
  }
  function hesapla(a, b) {
    var n = a.length, m = b.length;
    if (!n || !m) return 1;
    var onceki = new Array(m + 1), simdi = new Array(m + 1), i, j;
    for (j = 0; j <= m; j++) onceki[j] = j;
    for (i = 1; i <= n; i++) {
      simdi[0] = i;
      for (j = 1; j <= m; j++) {
        var c = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
        simdi[j] = Math.min(onceki[j] + 1, simdi[j - 1] + 1, onceki[j - 1] + c);
      }
      var t = onceki; onceki = simdi; simdi = t;
    }
    return onceki[m] / Math.max(n, m);
  }

  function altDizi(kisa, uzun) {
    for (var i = 0, j = 0; j < uzun.length && i < kisa.length; j++) if (kisa[i] === uzun[j]) i++;
    return i === kisa.length;
  }

  /* Yanlış yazılmış kelimenin hata türü (resmi kriterlerdeki adlarla). */
  function hataTuru(a, b) {
    var harfDisi = false, i;
    for (i = 0; i < b.length; i++) if (!HARF.test(b[i])) { harfDisi = true; break; }
    if (harfDisi) {
      if (a.length === b.length) {
        var yalniz = true;
        for (i = 0; i < a.length; i++) if (a[i] !== b[i] && HARF.test(b[i])) { yalniz = false; break; }
        if (yalniz) return 'karakter';
      }
      return 'karisik';
    }
    if (b.length > a.length && altDizi(a, b)) return 'fazla-vurus';
    if (b.length < a.length && altDizi(b, a)) return 'eksik-vurus';
    if (a.length === b.length) {
      var fark = [];
      for (i = 0; i < a.length; i++) if (a[i] !== b[i]) fark.push(i);
      if (fark.length === 2 && fark[1] === fark[0] + 1 && a[fark[0]] === b[fark[1]] && a[fark[1]] === b[fark[0]]) return 'yer-degistirme';
    }
    return 'karisik';
  }

  var TUR_AD = {
    'fazla-vurus': 'Fazla vuruş', 'eksik-vurus': 'Eksik vuruş', 'yer-degistirme': 'Harf yer değiştirme',
    'karakter': 'Karakter hatası', 'bolme': 'Kelime bölme', 'birlestirme': 'Kelime birleştirme',
    'fazla-bosluk': 'Fazla boşluk', 'karisik': 'Karışık hata', 'fazla-kelime': 'Metin dışı kelime'
  };

  /* asil: sınav metni (küçük harf, noktalamasız). yazilan: adayın yazdığı ham metin.
     secenek: { saniye: geçen süre, sure: sınav süresi (baraj bununla ölçeklenir) } */
  function puanla(asil, yazilan, secenek) {
    secenek = secenek || {};
    var sure = secenek.sure || 180;
    var saniye = Math.max(1, secenek.saniye || sure);
    var A = String(asil).split(/\s+/).filter(Boolean);
    var ham = String(yazilan || '').replace(/\r/g, '').replace(/[\n\t]/g, ' ');
    var govde = ham.trim();
    var fazlaBosluk = (govde.match(/ {2,}/g) || []).length;
    var B = govde ? govde.split(/ +/) : [];
    var sonTamam = /\s$/.test(ham);
    var M = B.length, N = Math.min(A.length, M * 2 + 40);

    var adimlar = [];
    if (M) {
      var W = N + 1, SONSUZ = 1e9;
      var maliyet = new Float64Array((N + 1) * (M + 1)).fill(SONSUZ);
      var islem = new Int8Array((N + 1) * (M + 1));   // 1 eşit, 2 yanlış, 3 atla, 4 fazla, 5 böl, 6 birleştir
      var parca = new Int8Array((N + 1) * (M + 1));
      var x = function (i, j) { return j * W + i; };
      maliyet[0] = 0;
      for (var j = 0; j <= M; j++) {
        var iAlt = Math.max(0, j - BANT), iUst = Math.min(N, j + BANT);
        for (var i = iAlt; i <= iUst; i++) {
          if (!i && !j) continue;
          var en = SONSUZ, op = 0, k = 0, c, v;
          if (i && j) {
            v = maliyet[x(i - 1, j - 1)];
            if (v < SONSUZ) {
              if (A[i - 1] === B[j - 1]) { c = v; if (c < en) { en = c; op = 1; } }
              else { c = v + 0.5 + mesafe(A[i - 1], B[j - 1]); if (c < en) { en = c; op = 2; } }
            }
          }
          if (i) { v = maliyet[x(i - 1, j)]; if (v + 0.75 < en) { en = v + 0.75; op = 3; } }
          if (j) { v = maliyet[x(i, j - 1)]; if (v + 1 < en) { en = v + 1; op = 4; } }
          if (i) {
            for (var kb = 2; kb <= 4 && kb <= j; kb++) {   // bir kelime birden çok parçaya bölünmüş
              v = maliyet[x(i - 1, j - kb)];
              if (v >= SONSUZ) continue;
              var bir = B.slice(j - kb, j).join('');
              if (bir === A[i - 1]) c = v + 0.6;
              else { var d = mesafe(A[i - 1], bir); if (d > 0.34) continue; c = v + 0.5 + d + (kb - 1) * 0.9; }
              if (c < en) { en = c; op = 5; k = kb; }
            }
          }
          if (j) {
            for (var ka = 2; ka <= 3 && ka <= i; ka++) {   // birden çok kelime bitişik yazılmış
              v = maliyet[x(i - ka, j - 1)];
              if (v >= SONSUZ) continue;
              // Yazılan kelime parçalardan birine birleşik halden daha yakınsa bu birleştirme değil, yanındaki kelime atlanmıştır.
              var parcalar = A.slice(i - ka, i), dd = mesafe(parcalar.join(''), B[j - 1]);
              if (dd > 0.34 || parcalar.some(function (p) { return mesafe(p, B[j - 1]) <= dd; })) continue;
              c = v + 0.8 + dd;
              if (c < en) { en = c; op = 6; k = ka; }
            }
          }
          maliyet[x(i, j)] = en; islem[x(i, j)] = op; parca[x(i, j)] = k;
        }
      }
      // Metnin ulaşılmamış kısmı atlanan sayılmaz: en iyi bitiş noktası seçilir.
      var bi = 0, bm = SONSUZ;
      for (var ii = 0; ii <= N; ii++) { var mv = maliyet[x(ii, M)]; if (mv < bm) { bm = mv; bi = ii; } }
      var ci = bi, cj = M;
      while (ci || cj) {
        var o = islem[x(ci, cj)], pk = parca[x(ci, cj)];
        if (o === 1) { adimlar.push({ t: 'dogru', a: A[ci - 1], b: B[cj - 1] }); ci--; cj--; }
        else if (o === 2) { adimlar.push({ t: 'yanlis', a: A[ci - 1], b: B[cj - 1] }); ci--; cj--; }
        else if (o === 3) { adimlar.push({ t: 'atla', a: A[ci - 1] }); ci--; }
        else if (o === 4) { adimlar.push({ t: 'fazla', b: B[cj - 1] }); cj--; }
        else if (o === 5) { adimlar.push({ t: 'bol', a: A[ci - 1], b: B.slice(cj - pk, cj).join(' '), k: pk }); ci--; cj -= pk; }
        else if (o === 6) { adimlar.push({ t: 'birlestir', a: A.slice(ci - pk, ci).join(' '), b: B[cj - 1], k: pk }); ci -= pk; cj--; }
        else break;
      }
      adimlar.reverse();
      while (adimlar.length && adimlar[adimlar.length - 1].t === 'atla') adimlar.pop();
    }

    var dogru = 0, hatali = 0, toplam = 0, atlanan = 0, eksikSon = null, dogruVurus = 0;
    var turler = {}, hatalar = [];
    var son = adimlar[adimlar.length - 1];
    if (son && son.t === 'yanlis' && !sonTamam && son.a.indexOf(son.b) === 0) { son.t = 'eksik-son'; eksikSon = son.b; }
    function hataEkle(tur, a, b, adet) {
      adet = adet || 1;
      hatali += adet; turler[tur] = (turler[tur] || 0) + adet;
      hatalar.push({ tur: tur, ad: TUR_AD[tur], a: a || '', b: b || '', adet: adet });
    }
    for (var s = 0; s < adimlar.length; s++) {
      var ad = adimlar[s];
      if (ad.t === 'dogru') { dogru++; toplam++; dogruVurus += ad.a.length + 1; }
      else if (ad.t === 'yanlis') { toplam++; ad.tur = hataTuru(ad.a, ad.b); hataEkle(ad.tur, ad.a, ad.b); }
      else if (ad.t === 'atla') atlanan++;
      else if (ad.t === 'fazla') { toplam++; ad.tur = 'fazla-kelime'; hataEkle('fazla-kelime', '', ad.b); }
      else if (ad.t === 'bol') {
        var adet = ad.b.replace(/ /g, '') === ad.a ? 1 : ad.k;
        toplam += adet; ad.tur = 'bolme'; hataEkle('bolme', ad.a, ad.b, adet);
      }
      else if (ad.t === 'birlestir') { toplam++; ad.tur = 'birlestirme'; hataEkle('birlestirme', ad.a, ad.b); }
    }
    if (fazlaBosluk) hataEkle('fazla-bosluk', '', 'art arda boşluk', fazlaBosluk);

    var net = Math.max(0, toplam - hatali);
    var oran = toplam ? 100 * hatali / toplam : 0;
    var baraj = Math.round(90 * sure / 180);
    var nedenler = [];
    if (net < baraj) nedenler.push('Net kelime ' + baraj + ' barajının altında');
    if (atlanan >= ATLAMA_SINIRI) nedenler.push('Toplam 22 ve üzeri kelime atlandı');
    if (oran > HATA_ORANI_SINIRI) nedenler.push('Hata oranı %25\'i aştı (anlam bütünlüğü sağlanmadı)');
    var vurus = ham.replace(/\s+$/, '').length;
    var dk = saniye / 60;

    return {
      toplam: toplam, dogru: dogru, hatali: hatali, net: net, atlanan: atlanan, eksikSon: eksikSon,
      fazlaBosluk: fazlaBosluk, oran: oran, baraj: baraj, basarili: !nedenler.length && toplam > 0, nedenler: nedenler,
      vurus: vurus, dogruVurus: Math.min(dogruVurus, vurus), dakikaVurus: Math.round(vurus / dk),
      dakikaNet: Math.round(net / dk), saniye: saniye, sure: sure,
      turler: turler, hatalar: hatalar, adimlar: adimlar
    };
  }

  var api = { puanla: puanla, hataTuru: hataTuru, TUR_AD: TUR_AD, ATLAMA_SINIRI: ATLAMA_SINIRI, HATA_ORANI_SINIRI: HATA_ORANI_SINIRI };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else kok.KatipPuan = api;
})(typeof window !== 'undefined' ? window : globalThis);
