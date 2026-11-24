// KPSS Tercihi servis çalışanı: yalnız Web Push bildirimi. Önbellek/fetch yakalama YOK (site davranışı değişmez).
const API = 'https://kamu-ilan-bildirim.kamuilan.workers.dev';
const IKON = '/assets/logo-192.png';
const GENEL_URL = '/nereye/';

function kisalt(s, n) {
  s = String(s || '');
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

function bildir(baslik, govde, url, etiket) {
  return self.registration.showNotification(baslik, {
    body: govde, icon: IKON, badge: IKON, tag: etiket, data: { url: url },
  });
}

async function bekleyenleriGoster() {
  let sonuc = null;
  try {
    const abonelik = await self.registration.pushManager.getSubscription();
    if (abonelik) {
      const r = await fetch(API + '/web/bekleyen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: abonelik.endpoint }),
      });
      if (r.ok) sonuc = await r.json();
    }
  } catch (e) { sonuc = null; }
  const ilanlar = sonuc && Array.isArray(sonuc.ilanlar) ? sonuc.ilanlar : [];
  if (!ilanlar.length) {
    // Chrome her push için bildirim ister.
    return bildir('KPSS Tercihi', 'Kayıtlı aramana uygun yeni ilan olabilir', GENEL_URL, 'genel');
  }
  const toplam = Math.max(sonuc.toplam || 0, ilanlar.length);
  if (toplam > 3) {
    return bildir('KPSS Tercihi', toplam + ' yeni ilan', GENEL_URL, 'ozet');
  }
  return Promise.all(ilanlar.slice(0, 3).map(function (i, n) {
    return bildir('Yeni ilan: ' + (i.kurum || 'KPSS Tercihi'), kisalt(i.baslik, 120), i.url || GENEL_URL, 'ilan-' + (i.url || n));   // ilan başına etiket: sonraki bildirim öncekini silmez
  }));
}

self.addEventListener('push', function (event) {
  event.waitUntil(bekleyenleriGoster());
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  const hedef = new URL((event.notification.data && event.notification.data.url) || GENEL_URL, self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (pencereler) {
      for (let i = 0; i < pencereler.length; i++) {
        if (pencereler[i].url === hedef && 'focus' in pencereler[i]) return pencereler[i].focus();
      }
      return self.clients.openWindow(hedef);
    })
  );
});
