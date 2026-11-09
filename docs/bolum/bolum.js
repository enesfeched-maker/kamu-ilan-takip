/* Bölümüne uygun ilanlar. Eşleştirme kuralları esles.js içindedir; bu dosya yalnız veri yükler ve gösterir.
 * Kural: hiçbir ilan listeden çıkarılmaz; her ilan tam olarak bir grupta görünür ve toplam sayı doğrulanır. */
(function () {
  'use strict';
  const E = window.BolumEsles;
  const $ = (id) => document.getElementById(id);
  const AY = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
  const DUZEY_AD = { lisans: 'Lisans', onlisans: 'Önlisans', ortaogretim: 'Ortaöğretim' };
  const GRUPLAR = [
    ['kesin', 'Bölümün şartta geçiyor', 'Şart metninde bölümünün adı yazıyor. Altındaki alıntıyı oku.', { acik: true }],
    ['muhtemel', 'Muhtemel eşleşme', 'Bölüm adın tam geçmiyor; ilgili bir ifade ya da bağlı fakülte/bölüm grubu yazıyor. Şartı mutlaka oku.', { acik: true }],
    ['serbest', 'Bölüm şartı aranmıyor görünüyor', 'Şartta “herhangi bir bölüm/alan” yazıyor. Öğrenim düzeyini ve diğer şartları kontrol et.', { acik: true }],
    ['belirsiz', 'Kontrol et: bölüm şartı okunamadı', 'Şart metni siteye alınamadığı ya da düzgün okunamadığı için eşleştirilemedi. Bu ilanlar elenmedi; ilan belgesini açıp bölüm şartına bak.', { acik: true, kisa: true }],
    ['eslesmiyor', 'Şartta başka bölümler yazıyor', 'Şartta sayılan bölümler arasında seninkini bulamadık. Yine de listeyi aç; “denk bölümler” ya da fakülte ifadesi seni kapsıyor olabilir.', { acik: false, kisa: true }],
  ];

  function h(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  const bugun = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/Istanbul' });
  function tarihYaz(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || '');
    return m ? Number(m[3]) + ' ' + AY[Number(m[2]) - 1] + ' ' + m[1] : '';
  }
  function kapali(r) {
    if (r.son_zaman) { const t = Date.parse(r.son_zaman); if (!isNaN(t)) return t <= Date.now(); }
    return r.son_tarih ? r.son_tarih < bugun() : false;
  }
  function baslamadi(r) {
    const t = r.baslangic_zaman ? Date.parse(r.baslangic_zaman) : NaN;
    return !isNaN(t) && t > Date.now();
  }
  function anahtar(r) {
    try { return new URL(r.link).searchParams.get('i') || r.id; } catch (e) { return r.id; }
  }
  const getJSON = (url) => fetch(url, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });

  let veri = null;
  async function yukle() {
    if (veri) return veri;
    const [i, l] = await Promise.allSettled([getJSON('../ilanlar.json'), getJSON('../liste.json')]);
    if (i.status !== 'fulfilled' || !i.value || !Array.isArray(i.value.ilanlar)) throw new Error('ilanlar');
    const kopya = new Map();
    const listeVar = l.status === 'fulfilled' && l.value && Array.isArray(l.value.ilanlar);
    if (listeVar) for (const o of l.value.ilanlar) if (o && o.kopya_of && o.key) kopya.set(o.key, o.kopya_of);
    const tum = i.value.ilanlar.filter((r) => r && typeof r.id === 'string' && typeof r.baslik === 'string');
    // Düzeltme duyurusu yayımlanmış kurumların ilanları işaretlenir (şartlar değişmiş olabilir).
    const duzeltmeKurum = new Set(tum.filter((r) => r.duyuru_turu && /düzeltme/i.test(r.duyuru_turu) && r.kurum).map((r) => E.fold(r.kurum)));
    const ilanlar = tum.filter((r) => !r.duyuru_turu);
    for (const r of ilanlar) r._duzeltme = (Array.isArray(r.duzeltmeler) && r.duzeltmeler.length > 0) || r.duzeltildi === true || (!!r.kurum && duzeltmeKurum.has(E.fold(r.kurum)));
    veri = { ilanlar, kopya, listeVar };
    return veri;
  }

  /* Alıntıda bölüm sözcüklerini işaretle (DOM düğümleriyle; HTML enjekte edilmez). */
  function isaretle(kap, metin, bolum) {
    const koklar = [...new Set(bolum.flat())].filter((t) => t.length >= 4).map((t) => (t.length <= 5 ? t : t.slice(0, Math.max(5, t.length - 3))));
    for (const parca of String(metin).split(/(\s+)/)) {
      const f = E.fold(parca);
      if (f && koklar.some((k) => f.startsWith(k))) kap.append(h('mark', '', parca));
      else kap.append(document.createTextNode(parca));
    }
  }

  function satir(s, bolum, kisa) {
    const r = s.rec, key = anahtar(r);
    const kap = h('article', 'b-satir');
    kap.append(h('div', 'b-kurum', r.kurum || 'Kurum belirtilmemiş'));
    const bas = h('h4'), a = h('a', '', r.baslik.replace(r.kurum ? new RegExp('^' + r.kurum.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*-\\s*', 'i') : /^$/, '') || r.baslik);
    a.href = '../ilan/' + encodeURIComponent(key) + '/';
    bas.append(a);
    kap.append(bas);
    const meta = h('div', 'b-meta');
    if (r.son_tarih) meta.append(h('span', '', (kapali(r) ? 'Son başvuru: ' : 'Son gün: ') + tarihYaz(r.son_tarih)));
    else meta.append(h('span', '', 'Son tarih ilanda'));
    if (r.kategori === 'akademik') meta.append(h('span', 'b-etiket', 'Akademik'));
    if (r.iptal_edildi) meta.append(h('span', 'b-etiket uyari', 'İptal edildi'));
    if (baslamadi(r)) meta.append(h('span', 'b-etiket', 'Başvuru henüz başlamadı'));
    if (s.kurumIci) meta.append(h('span', 'b-etiket uyari', 'Kurum içi olabilir'));
    if (s.duzeltme) meta.append(h('span', 'b-etiket uyari', 'Düzeltme yayımlanmış'));
    for (const d of s.seviyeler || []) meta.append(h('span', 'b-etiket', DUZEY_AD[d] || d));
    kap.append(meta);
    if (s.duzeyUyari) kap.append(h('p', 'b-neden', s.duzeyUyari));
    if (!kisa) {
      kap.append(h('p', 'b-neden', s.neden + (s.kadro ? ' — kadro: ' + s.kadro : '')));
      if (s.kanit) { const q = h('p', 'b-kanit'); isaretle(q, s.kanit, bolum); kap.append(q); }
    } else if (s.kademe === 'eslesmiyor' && s.kanit) {
      const d = h('details'), sm = h('summary', '', 'Şartta yazan bölümleri göster');
      d.append(sm, h('p', 'b-kanit', s.kanit));
      kap.append(d);
    } else {
      kap.append(h('p', 'b-neden', s.neden));
    }
    const lk = h('div', 'b-linkler');
    const d1 = h('a', '', 'Site sayfası'); d1.href = '../ilan/' + encodeURIComponent(key) + '/';
    lk.append(d1);
    if (/^https?:\/\//.test(r.link || '')) { const d2 = h('a', '', 'Resmî ilan ↗'); d2.href = r.link; d2.target = '_blank'; d2.rel = 'noopener'; lk.append(d2); }
    kap.append(lk);
    return kap;
  }

  function sirala(liste, azalan) {
    const k = (s) => s.rec.son_tarih || '';
    return liste.slice().sort((a, b) => {
      if (!k(a) && !k(b)) return 0;
      if (!k(a)) return 1;
      if (!k(b)) return -1;
      return azalan ? k(b).localeCompare(k(a)) : k(a).localeCompare(k(b));
    });
  }

  function bolge(baslik, aciklama, liste, bolum, azalan) {
    const kap = h('section', 'b-bolge');
    kap.append(h('h2', '', baslik + ' (' + liste.length + ')'), h('p', '', aciklama));
    if (!liste.length) { kap.append(h('p', 'b-bos', 'Bu bölümde ilan yok.')); return kap; }
    for (const [kademe, ad, not, ayar] of GRUPLAR) {
      const alt = sirala(liste.filter((s) => s.kademe === kademe), azalan);
      const d = h('details', 'b-grup' + (ayar.kisa ? ' b-kisa' : ''));
      if (ayar.acik && alt.length) d.open = true;
      const sm = h('summary'), t = h('h3', '', ad);
      sm.append(t, h('span', 'sayi', String(alt.length)));
      d.append(sm, h('p', 'b-not', not));
      if (alt.length) { const l = h('div', 'b-liste'); for (const s of alt) l.append(satir(s, bolum, !!ayar.kisa)); d.append(l); }
      else d.append(h('p', 'b-bos', 'Bu grupta ilan yok.'));
      kap.append(d);
    }
    return kap;
  }

  function hata(msg) { const e = $('bf-hata'); e.textContent = msg; e.hidden = !msg; }
  function durum(msg) { const e = $('durum'); e.textContent = msg; e.hidden = !msg; }

  async function calistir(duzey, bolumMetni) {
    hata('');
    const bolum = E.bolumCoz(bolumMetni);
    if (!bolum.length) { hata('Bölüm adını yaz (ör. Bilgisayar Mühendisliği).'); return; }
    durum('İlanlar yükleniyor…');
    let v;
    try { v = await yukle(); } catch (e) { durum(''); hata('İlan verisi yüklenemedi; sayfayı yenileyip tekrar dene.'); return; }
    durum('');
    const sonuc = E.gruplaVeSinifla(v.ilanlar, bolum, duzey, v.kopya, anahtar);
    const acik = sonuc.filter((s) => !kapali(s.rec)), gecmis = sonuc.filter((s) => kapali(s.rec));
    const kap = $('sonuc');
    kap.replaceChildren();

    const toplam = sonuc.length;
    let grupToplam = 0;
    for (const [kademe] of GRUPLAR) grupToplam += sonuc.filter((s) => s.kademe === kademe).length;
    const kayitSayisi = sonuc.reduce((n, s) => n + s.uyeler.length, 0);
    const tamam = grupToplam === toplam && kayitSayisi === v.ilanlar.length;
    if (!tamam) console.error('Bölüm eşleştirme sayım hatası', { toplam, grupToplam, kayitSayisi, girdi: v.ilanlar.length });

    const ilk = v.ilanlar.map((r) => (r.ilk_gorulme || '').slice(0, 10)).filter(Boolean).sort()[0];
    const ozet = h('p', 'b-ozet');
    ozet.append('“', h('b', '', bolumMetni.trim()), '” için ', h('b', '', String(toplam)), ' ilan tarandı');
    if (ilk) ozet.append(' (sitede ' + tarihYaz(ilk) + ' tarihinden beri kayıtlı olanlar)');
    ozet.append(': ' + acik.length + ' açık, ' + gecmis.length + ' süresi dolmuş.');
    kap.append(ozet);
    const kontrol = h('p', 'b-kontrol' + (tamam ? '' : ' hata'),
      tamam ? 'Sayım kontrolü: ' + toplam + ' ilanın tamamı bir grupta listelendi; hiçbiri çıkarılmadı.'
        : 'Sayım kontrolü başarısız: bazı ilanlar listelenmemiş olabilir. Lütfen bize bildir.');
    kap.append(kontrol);
    if (!v.listeVar) kap.append(h('p', 'b-kontrol', 'Aynı ilanın farklı kaynaklardaki kopyaları ayrı satırlar olarak görünebilir.'));

    kap.append(bolge('Açık ilanlar', 'Başvurusu sürenler, son tarihi en yakın olan üstte.', acik, bolum, false));
    kap.append(bolge('Daha önce açılmış ilanlar', 'Süresi dolmuş ilanlar, yenisi üstte. Aynı kurumlar benzer ilanı yeniden açabilir.', gecmis, bolum, true));
    try { history.replaceState(null, '', '?d=' + encodeURIComponent(duzey) + '&b=' + encodeURIComponent(bolumMetni.trim())); } catch (e) { /* adres çubuğu güncellenemedi */ }
    try { localStorage.setItem('kit-bolum', JSON.stringify({ d: duzey, b: bolumMetni.trim() })); } catch (e) { /* depolama kapalı */ }
    kap.scrollIntoView && kap.scrollIntoView({ block: 'start' });
  }

  let duzey = 'lisans';
  const proper = (s) => String(s).toLocaleLowerCase('tr').replace(/(^|[\s(\/-])(\p{L})/gu, (m, a, b) => a + b.toLocaleUpperCase('tr'));
  async function listeDoldur() {
    const dl = $('bf-liste');
    try {
      const v = await getJSON('../puanlar/' + duzey + '-bolum.json');
      if (!v || typeof v.bolumler !== 'object') return;
      const adlar = [...new Set(Object.values(v.bolumler).filter((x) => typeof x === 'string' && x.length <= 120).map(proper))].sort((a, b) => a.localeCompare(b, 'tr'));
      dl.replaceChildren(...adlar.map((a) => { const o = document.createElement('option'); o.value = a; return o; }));
    } catch (e) { dl.replaceChildren(); }
  }
  function duzeySec(d) {
    if (!DUZEY_AD[d]) return;
    duzey = d;
    document.querySelectorAll('#bf-duzey .tab').forEach((b) => {
      const on = b.dataset.duzey === d;
      b.classList.toggle('secili', on);
      b.setAttribute('aria-pressed', String(on));
    });
    listeDoldur();
  }

  function basla() {
    if (!E) { hata('Eşleştirme kodu yüklenemedi; sayfayı yenile.'); return; }
    const y = $('yil'); if (y) y.textContent = String(new Date().getFullYear());
    document.querySelectorAll('#bf-duzey .tab').forEach((b) => { b.onclick = () => duzeySec(b.dataset.duzey); });
    $('bf').addEventListener('submit', (e) => { e.preventDefault(); calistir(duzey, $('bf-bolum').value); });
    let onceki = null;
    try { onceki = JSON.parse(localStorage.getItem('kit-bolum')); } catch (e) { /* yok */ }
    let profil = null;
    try { profil = JSON.parse(localStorage.getItem('kit-profil')); } catch (e) { /* yok */ }
    const q = new URLSearchParams(location.search);
    const d0 = q.get('d') || (onceki && onceki.d) || (profil && profil.ogrenim) || 'lisans';
    const b0 = q.get('b') || (onceki && onceki.b) || (profil && typeof profil.bolum === 'string' ? profil.bolum : '') || '';
    duzeySec(DUZEY_AD[d0] ? d0 : 'lisans');
    if (b0) $('bf-bolum').value = String(b0).slice(0, 120);
    if (q.get('b')) calistir(duzey, $('bf-bolum').value);
  }
  basla();
})();
