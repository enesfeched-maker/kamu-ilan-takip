/* KPSS Tercihi: tarayıcının confirm()/alert() pencereleri yerine sayfa içi onay penceresi ve kısa bildirim (Kasım 2026).
   forum.js, profil-kart.js, portal.js ve katiplik yalnız gerektiğinde yükler; stil kendi içindedir, sayfanın renk belirteçlerini kullanır.
   kitOnay({ baslik, metin, evet, hayir, tehlike }) -> Promise<boolean>   (Esc, Vazgeç ve dışarı dokunma = false)
   kitOnay.bildir(metin)                                            -> ekranın altında 2,6 sn görünen not (role=status)
   Pencere <dialog> ile açılır (showModal): sayfanın geri kalanı etkisizdir, odak pencerede kalır, kapanınca odak eski yerine döner. */
(function () {
  'use strict';
  if (window.kitOnay) return;
  var STIL = ''
    + '.ko-pencere{width:min(400px,calc(100% - 32px));max-height:calc(100dvh - 32px);margin:auto;padding:0;border:0;border-radius:18px;background:var(--surface,#fff);color:var(--ink,#111310);box-shadow:0 24px 60px -20px rgba(0,0,0,.45);overflow:auto;overscroll-behavior:contain}'
    + '.ko-pencere::backdrop{background:rgba(13,14,12,.5)}'
    + '.ko-pencere[open]{animation:ko-gel .18s ease-out}'
    + '@keyframes ko-gel{from{opacity:0;transform:translateY(8px) scale(.98)}}'
    + '.ko-ic{display:flex;flex-direction:column;gap:10px;padding:22px 22px 18px}'
    + '.ko-ikon{display:grid;place-items:center;width:44px;height:44px;border-radius:50%;background:var(--surface-2,#F2F2EC);color:var(--ink-2,#3B3F37)}'
    + '.ko-ikon svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}'
    + '.ko-tehlike .ko-ikon{background:color-mix(in srgb,#D92D20 12%,transparent);color:#D92D20}'
    + ':root[data-theme=dark] .ko-tehlike .ko-ikon{color:#FF8F80}'
    + '.ko-baslik{margin:4px 0 0;font-size:18px;font-weight:700;line-height:1.3;letter-spacing:-.01em;text-wrap:balance;overflow-wrap:anywhere}'
    + '.ko-metin{margin:0;color:var(--muted,#6C7166);font-size:15px;line-height:1.5;overflow-wrap:anywhere}'
    + '.ko-dugmeler{display:flex;flex-direction:row-reverse;flex-wrap:wrap;gap:8px;margin-top:10px}'
    + '.ko-dugmeler button{flex:1 1 140px;min-height:46px;padding:0 16px;border-radius:12px;font:inherit;font-size:15px;font-weight:650;cursor:pointer;transition:background .15s,transform .15s}'
    + '.ko-dugmeler button:active{transform:scale(.98)}'
    + '.ko-dugmeler button:focus-visible{outline:2px solid var(--focus,#4a7d0a);outline-offset:2px}'
    + '.ko-evet{border:0;background:var(--btn,#111310);color:var(--btn-ink,#fff)}'
    + '.ko-evet:hover{opacity:.9}'
    + '.ko-tehlike .ko-evet{background:#D92D20;color:#fff}'
    + '.ko-tehlike .ko-evet:hover{background:#B42318;opacity:1}'
    + '.ko-hayir{border:1px solid var(--line-2,#D6D6CC);background:transparent;color:var(--ink,#111310)}'
    + '.ko-hayir:hover{background:var(--surface-2,#F2F2EC)}'
    + '.ko-not{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom,0px));z-index:2147483000;max-width:calc(100% - 32px);padding:11px 16px;border-radius:12px;background:#111310;color:#F0F2EB;font-size:15px;line-height:1.4;box-shadow:0 10px 30px -12px rgba(0,0,0,.5);transform:translateX(-50%);transition:opacity .3s,transform .3s}'
    + ':root[data-theme=dark] .ko-not{background:#F0F2EB;color:#111310}'
    + '.ko-not.ko-git{opacity:0;transform:translate(-50%,6px)}'
    + '@media (max-width:520px){.ko-pencere{width:100%;max-width:none;margin:auto 0 0;border-radius:18px 18px 0 0;max-height:92dvh}.ko-ic{padding:20px 18px calc(18px + env(safe-area-inset-bottom,0px))}.ko-dugmeler{flex-direction:column}.ko-dugmeler button{flex:none;width:100%}}'
    + '@media (prefers-reduced-motion:reduce){.ko-pencere[open]{animation:none}.ko-dugmeler button,.ko-not{transition:none}}';
  var UYARI = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4M12 16.5h.01M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>';
  var SORU = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17.5h.01M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z"/></svg>';
  var sayac = 0;

  function stil() {
    if (document.getElementById('ko-stil')) return;
    var s = document.createElement('style'); s.id = 'ko-stil'; s.textContent = STIL; document.head.appendChild(s);
  }
  function kacis(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  function onay(o) {
    o = typeof o === 'string' ? { metin: o } : (o || {});
    var baslik = o.baslik || 'Emin misin?', metin = o.metin || '';
    var d = document.createElement('dialog');
    if (typeof d.showModal !== 'function') {   // çok eski tarayıcı: yerleşik pencere
      return Promise.resolve(window.confirm(baslik + (metin ? '\n\n' + metin : '')));
    }
    stil();
    var id = 'ko-' + (++sayac), onceki = document.activeElement;
    d.className = 'ko-pencere' + (o.tehlike ? ' ko-tehlike' : '');
    d.setAttribute('role', 'alertdialog');
    d.setAttribute('aria-labelledby', id + '-b');
    if (metin) d.setAttribute('aria-describedby', id + '-m');
    d.innerHTML = '<div class="ko-ic"><span class="ko-ikon">' + (o.tehlike ? UYARI : SORU) + '</span>'
      + '<h2 class="ko-baslik" id="' + id + '-b">' + kacis(baslik) + '</h2>'
      + (metin ? '<p class="ko-metin" id="' + id + '-m">' + kacis(metin) + '</p>' : '')
      + '<div class="ko-dugmeler"><button type="button" class="ko-evet">' + kacis(o.evet || 'Tamam') + '</button>'
      + '<button type="button" class="ko-hayir">' + kacis(o.hayir || 'Vazgeç') + '</button></div></div>';
    document.body.appendChild(d);
    return new Promise(function (bitir) {
      var sonuc = false;
      function kapat(v) { sonuc = v; if (d.open) d.close(); }
      d.querySelector('.ko-evet').onclick = function () { kapat(true); };
      d.querySelector('.ko-hayir').onclick = function () { kapat(false); };
      d.addEventListener('cancel', function () { sonuc = false; });   // Esc
      d.addEventListener('click', function (e) {   // pencerenin dışına (perdeye) dokunma = Vazgeç
        if (e.target !== d) return;
        var r = d.getBoundingClientRect();
        if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) kapat(false);
      });
      d.addEventListener('close', function () {
        d.remove();
        try { if (onceki && onceki.focus && document.body.contains(onceki)) onceki.focus({ preventScroll: true }); } catch (e) {}
        bitir(sonuc);
      });
      d.showModal();
      // yıkıcı işlemde odak "Vazgeç"te başlar (yanlışlıkla Enter'la silinmesin)
      (o.tehlike ? d.querySelector('.ko-hayir') : d.querySelector('.ko-evet')).focus();
    });
  }

  var notZaman = 0;
  function bildir(metin) {
    stil();
    var t = document.getElementById('ko-not');
    if (!t) { t = document.createElement('div'); t.id = 'ko-not'; t.className = 'ko-not'; t.setAttribute('role', 'status'); }
    // açık bir <dialog> varsa not onun içine konur (üst katmanda kalsın, arkada görünmez olmasın)
    var ust = null, l = document.querySelectorAll('dialog[open]');
    if (l.length) ust = l[l.length - 1];
    (ust || document.body).appendChild(t);
    t.textContent = metin; t.classList.remove('ko-git');
    clearTimeout(notZaman);
    notZaman = setTimeout(function () { t.classList.add('ko-git'); notZaman = setTimeout(function () { t.remove(); }, 350); }, 2600);
  }
  onay.bildir = bildir;
  window.kitOnay = onay;
})();
