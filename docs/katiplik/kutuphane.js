/* KPSS Tercihi — katiplik metin kütüphaneleri dizini ve yükleyici (dizin kısmı üretilmiştir). */
(function () {
  'use strict';
  var bekleyen = {};
  var K = window.KatipKutuphane = {
    liste: [{"id":"zk2025","ad":"Zabıt Katipliği 2025 · resmî sınav metinleri","kisa":"ZK 2025 (resmî)","grup":"Resmî sınav metinleri","adet":30,"kaynak":"Adalet Bakanlığı Personel Genel Müdürlüğü, 2025 Yılı Zabıt Katibi Uygulamalı Sınav Metinleri (yönetmelik gereği sınavdan önce yayımlanmıştır).","url":"https://pgm.adalet.gov.tr/Resimler/dokuman/UygulamaliSinavMetinleri.zip"},{"id":"ozgun","ad":"Özgün hukuk ve adliye metinleri","kisa":"Özgün metinler","grup":"KPSS Tercihi özgün","adet":56,"kaynak":"KPSS Tercihi tarafından sınav biçiminde yazılmıştır.","url":""},{"id":"tck","ad":"Türk Ceza Kanunu (5237)","kisa":"TCK","grup":"Mevzuat","adet":50,"kaynak":"5237 sayılı Türk Ceza Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"cmk","ad":"Ceza Muhakemesi Kanunu (5271)","kisa":"CMK","grup":"Mevzuat","adet":50,"kaynak":"5271 sayılı Ceza Muhakemesi Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"hmk","ad":"Hukuk Muhakemeleri Kanunu (6100)","kisa":"HMK","grup":"Mevzuat","adet":50,"kaynak":"6100 sayılı Hukuk Muhakemeleri Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"iik","ad":"İcra ve İflas Kanunu (2004)","kisa":"İİK","grup":"Mevzuat","adet":50,"kaynak":"2004 sayılı İcra ve İflas Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"tmk","ad":"Türk Medeni Kanunu (4721)","kisa":"TMK","grup":"Mevzuat","adet":50,"kaynak":"4721 sayılı Türk Medeni Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"tbk","ad":"Türk Borçlar Kanunu (6098)","kisa":"TBK","grup":"Mevzuat","adet":50,"kaynak":"6098 sayılı Türk Borçlar Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"anayasa","ad":"Türkiye Cumhuriyeti Anayasası (2709)","kisa":"Anayasa","grup":"Mevzuat","adet":50,"kaynak":"2709 sayılı Türkiye Cumhuriyeti Anayasası, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"iyuk","ad":"İdari Yargılama Usulü Kanunu (2577)","kisa":"İYUK","grup":"Mevzuat","adet":31,"kaynak":"2577 sayılı İdari Yargılama Usulü Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"},{"id":"dmk","ad":"Devlet Memurları Kanunu (657)","kisa":"DMK","grup":"Mevzuat","adet":50,"kaynak":"657 sayılı Devlet Memurları Kanunu, Mevzuat Bilgi Sistemi. Kanun metinleri FSEK m.31 uyarınca serbestçe kullanılabilir; sınav biçimine çevrilmiştir.","url":"https://www.mevzuat.gov.tr/"}],
    veri: {},
    bul: function (id) { for (var i = 0; i < K.liste.length; i++) if (K.liste[i].id === id) return K.liste[i]; return null; },
    yukle: function (id, metinler) { K.veri[id] = metinler; (bekleyen[id] || []).forEach(function (f) { f[0](metinler); }); delete bekleyen[id]; },
    // Kütüphaneyi gerektiğinde yükler: getir('tck').then(function (metinler) { ... })
    getir: function (id) {
      if (!K.bul(id)) id = K.liste[0].id;
      if (K.veri[id]) return Promise.resolve(K.veri[id]);
      return new Promise(function (coz, red) {
        if (!bekleyen[id]) {
          bekleyen[id] = [];
          var s = document.createElement('script');
          s.src = K.kok + 'metin/' + id + '.js?v=1';
          s.onerror = function () { (bekleyen[id] || []).forEach(function (f) { f[1](new Error('Metinler yüklenemedi')); }); delete bekleyen[id]; };
          document.head.appendChild(s);
        }
        bekleyen[id].push([coz, red]);
      });
    }
  };
  // metin/ klasörünün yolu bu dosyanın yanındadır (alt sayfalar ../ ile yükler)
  var bu = document.currentScript && document.currentScript.src;
  K.kok = bu ? bu.replace(/kutuphane\.js(\?.*)?$/, '') : '';
})();
