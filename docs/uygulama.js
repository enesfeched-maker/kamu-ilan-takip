/* Yalnız Android/iOS uygulamasında yüklenir (portal.js sonundaki denetim). Tarayıcıda hiç çalışmaz. */
(function () {
  var C = window.Capacitor;
  if (!C || !C.isNativePlatform || !C.isNativePlatform()) return;
  var P = C.Plugins || {}, platform = C.getPlatform();

  /* AdMob hesabı açılınca reklam birimi kimlikleri buraya yazılır; boşken reklam SDK'sı hiç başlatılmaz. */
  var BANNER = { android: '', ios: '' };

  function ilkAcilisBilgisi() {
    var k = 'kit-uygulama-bilgi';
    try { if (localStorage.getItem(k)) return; } catch (e) { return; }
    var d = document.createElement('dialog'), p = document.createElement('p'), b = document.createElement('button');
    p.textContent = 'KPSS Tercihi resmî bir kurum uygulaması değildir ve hiçbir devlet kurumunu temsil etmez. Bilgiler kurumların resmî duyurularından derlenir; başvurudan önce her ilanın kaynağını kontrol et.';
    b.textContent = 'Anladım';
    b.type = 'button';
    b.style.cssText = 'padding:10px 20px';
    d.style.cssText = 'max-width:320px;border:0;border-radius:12px;padding:20px';
    b.onclick = function () { try { localStorage.setItem(k, '1'); } catch (e) {} d.close(); d.remove(); };
    d.append(p, b);
    document.body.append(d);
    d.showModal();
  }

  function kimlik(key) {
    var h = 0, s = String(key);
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 1000000007;
    return (h % 1000000000) * 2 + 2; /* her ilana iki ardışık bildirim kimliği */
  }

  function sonGun(son) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(son || '');
    if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
    var t = Date.parse(son || '');
    return isNaN(t) ? null : new Date(t);
  }

  async function izinVarMi(L) {
    var d = await L.checkPermissions();
    if (d.display === 'granted') return true;
    if (d.display === 'denied') return false;
    return (await L.requestPermissions()).display === 'granted';
  }

  async function hatirlatmaGuncelle(o) {
    var L = P.LocalNotifications;
    if (!L || !o || !o.key) return;
    var id = kimlik(o.key);
    await L.cancel({ notifications: [{ id: id }, { id: id + 1 }] });
    if (!o.kayitli) return;
    var g = sonGun(o.son);
    if (!g || !(await izinVarMi(L))) return;
    var ad = o.baslik || 'Kaydettiğin ilan', simdi = Date.now(), liste = [];
    var once = new Date(g.getFullYear(), g.getMonth(), g.getDate() - 1, 10);
    var son = new Date(g.getFullYear(), g.getMonth(), g.getDate(), 9);
    if (once.getTime() > simdi) liste.push({ id: id, title: 'Başvuru yarın bitiyor', body: ad, schedule: { at: once, allowWhileIdle: true } });
    if (son.getTime() > simdi) liste.push({ id: id + 1, title: 'Başvuruda son gün', body: ad, schedule: { at: son, allowWhileIdle: true } });
    if (liste.length) await L.schedule({ notifications: liste });
  }

  async function reklamBaslat() {
    var A = P.AdMob, birim = BANNER[platform];
    if (!A || !birim) return;
    await A.initialize({});
    if (platform === 'ios') await A.requestTrackingAuthorization();
    var r = await A.requestConsentInfo();
    if (r.isConsentFormAvailable && r.status === 'REQUIRED') r = await A.showConsentForm();
    if (r.canRequestAds === false) return;
    A.addListener('bannerAdSizeChanged', function (s) {
      document.body.style.paddingBottom = ((s && s.height) || 0) + 'px';
    });
    await A.showBanner({ adId: birim, adSize: 'ADAPTIVE_BANNER', position: 'BOTTOM_CENTER', margin: 0 });
  }

  document.addEventListener('kit-kayit', function (e) {
    hatirlatmaGuncelle(e.detail).catch(function () {});
  });
  ilkAcilisBilgisi();
  reklamBaslat().catch(function () {});
})();
