'use strict';

const PLATFORM = {
  instagram: 'Instagram', youtube: 'YouTube', tiktok: 'TikTok', telegram: 'Telegram', facebook: 'Facebook', x: 'X',
};
const OLCUT_ADI = {
  views: 'İzlenme', reach: 'Erişim', likes: 'Beğeni', comments: 'Yorum', shares: 'Paylaşım', saved: 'Kaydetme',
  forwards: 'İletme', reactions: 'Tepki', avg_watch_ms: 'Ort. izlenme süresi', total_watch_ms: 'Toplam izlenme süresi',
  interactions: 'Toplam etkileşim',
};
const KAYNAK_ADI = {
  gecmis: 'Bot geçmişi', bulut: 'Bulut toplayıcı', youtube_api: 'YouTube Data API', buffer: 'Buffer',
};
const DURUM_ADI = { hazir: 'hazır', kismi: 'kısmi', bekliyor: 'anahtar bekleniyor', hata: 'hata', kapali: 'bağlı değil' };

const d = {
  gonderiler: [], ozet: {}, durum: null,
  platform: '', sablon: '', ara: '', gun: '30',
  sirala: 'yayin', artan: false, secili: null, gorunum: 'akis', analizAlan: 'sablon',
};
const $ = (s, k = document) => k.querySelector(s);
const $$ = (s, k = document) => [...k.querySelectorAll(s)];
const sayi = (n) => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('tr-TR');
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const tarihBicim = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Istanbul' });
const uzunTarih = new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Istanbul' });
const tarih = (iso) => iso ? tarihBicim.format(new Date(iso)) : '—';
const sure = (ms) => {
  if (ms === null || ms === undefined) return '—';
  const sn = ms / 1000;
  if (sn < 60) return sn.toFixed(1).replace('.', ',') + ' sn';
  const dk = sn / 60;
  return dk < 60 ? dk.toFixed(1).replace('.', ',') + ' dk' : (dk / 60).toFixed(1).replace('.', ',') + ' sa';
};
const yuzde = (x) => x === null || x === undefined ? '—' : (x * 100).toFixed(1).replace('.', ',') + '%';
const puanMetni = (p) => p === null || p === undefined ? '—' : p.toFixed(2).replace('.', ',') + '×';

async function al(url, secenek) {
  const r = await fetch(url, secenek);
  if (!r.ok) throw new Error(url + ' ' + r.status);
  return r.json();
}

// ------------------------------------------------------------------ veri
async function yukle() {
  const [durum, veri] = await Promise.all([al('/api/durum'), al('/api/gonderiler')]);
  d.durum = durum; d.gonderiler = veri.gonderiler; d.ozet = veri.ozet;
  $('#ornek-seridi').hidden = !durum.ornek;
  toplamaDurumu();
  kenarCiz();
  if (d.gorunum === 'akis') akisCiz(); else analizCiz();
}

function toplamaDurumu() {
  const t = d.durum && d.durum.toplama;
  const dugme = $('#yenile');
  const suruyor = t && t.basladi && !t.bitti;
  dugme.classList.toggle('calisiyor', !!suruyor);
  dugme.textContent = suruyor ? 'Toplanıyor…' : 'Yenile';
  $('#toplama-durumu').textContent = t && t.bitti ? 'Son toplama ' + tarih(t.bitti) : '';
  return suruyor;
}

function suzulmus() {
  const ara = d.ara.toLocaleLowerCase('tr');
  const sinir = d.gun ? Date.now() - Number(d.gun) * 864e5 : null;
  let liste = d.gonderiler.filter((g) =>
    (!d.platform || g.platform === d.platform) &&
    (!d.sablon || g.sablon === d.sablon) &&
    (!sinir || (g.yayin && Date.parse(g.yayin) >= sinir)) &&
    (!ara || ((g.baslik || '') + ' ' + (g.metin || '') + ' ' + (g.sablon || '')).toLocaleLowerCase('tr').includes(ara)));
  const a = d.sirala, yon = d.artan ? 1 : -1;
  liste.sort((x, y) => {
    const vx = x[a], vy = y[a];
    if (vx === vy) return 0;
    if (vx === null || vx === undefined) return 1;
    if (vy === null || vy === undefined) return -1;
    return (vx > vy ? 1 : -1) * yon;
  });
  return liste;
}

// ------------------------------------------------------------------ kenar çubuğu
function kenarCiz() {
  const k = (d.durum && d.durum.kaynaklar) || {};
  const sinir = d.gun ? Date.now() - Number(d.gun) * 864e5 : null;
  const donemde = d.gonderiler.filter((g) => !sinir || (g.yayin && Date.parse(g.yayin) >= sinir));
  const say = (p) => donemde.filter((g) => g.platform === p).length;
  const satirlar = [`<li data-platform="" class="${d.platform ? '' : 'secili'}"><span class="nokta" style="background:var(--metin-3)"></span>Tümü<span class="adet">${sayi(donemde.length)}</span></li>`];
  (d.durum ? d.durum.platformlar : Object.keys(PLATFORM)).forEach((p, i) => {
    const durum = (k[p] || {}).durum || 'bekliyor';
    const not = durum === 'hazir' ? '' : `<span class="durum-isareti ${durum}">${DURUM_ADI[durum] || durum}</span>`;
    satirlar.push(`<li data-platform="${p}" class="${d.platform === p ? 'secili' : ''}" title="${esc((k[p] || {}).aciklama || '')} (kısayol ${i + 1})">
      <span class="nokta p-${p}"></span>${PLATFORM[p]} ${not}<span class="adet">${sayi(say(p))}</span></li>`);
  });
  $('#platformlar').innerHTML = satirlar.join('');

  const sablonlar = {};
  donemde.filter((g) => !d.platform || g.platform === d.platform).forEach((g) => { const s = g.sablon || '—'; sablonlar[s] = (sablonlar[s] || 0) + 1; });
  $('#sablonlar').innerHTML = [`<li data-sablon="" class="${d.sablon ? '' : 'secili'}">Tümü</li>`]
    .concat(Object.entries(sablonlar).sort((a, b) => b[1] - a[1]).map(([s, n]) =>
      `<li data-sablon="${esc(s)}" class="${d.sablon === s ? 'secili' : ''}">${esc(s)}<span class="adet">${sayi(n)}</span></li>`)).join('');

  const kaynaklar = Object.keys(PLATFORM).concat(Object.keys(KAYNAK_ADI)).filter((x) => k[x]);
  $('#kaynaklar').innerHTML = kaynaklar.map((x) => {
    const s = k[x];
    return `<li><b>${PLATFORM[x] || KAYNAK_ADI[x]}</b> <span class="durum-isareti ${s.durum}">${DURUM_ADI[s.durum] || s.durum}</span><br>${esc(s.aciklama || '')}</li>`;
  }).join('') || '<li class="soluk">Henüz toplama yapılmadı.</li>';
}

// ------------------------------------------------------------------ akış
function puanHucresi(g) {
  if (g.puan === null || g.puan === undefined) return '<span class="yok">—</span>';
  const g2 = Math.min(g.puan / 3, 1) * 100;
  const sinif = g.puan >= 1.25 ? 'iyi' : g.puan <= 0.8 ? 'kotu' : '';
  return `<div class="puan ${g.olgun ? '' : 'genc'}" title="${g.olgun ? 'Dönem ortalamasının ' + puanMetni(g.puan) + 'i' : 'İlk 48 saat: sayılar henüz oturmadı'}">
    <span class="cubuk"><i class="${sinif}" style="width:${g2}%"></i></span>${puanMetni(g.puan)}</div>`;
}

function akisCiz() {
  const liste = suzulmus();
  d.liste = liste;
  if (!liste.find((g) => g.id === d.secili)) d.secili = liste.length ? liste[0].id : null;
  $$('#tablo th[data-sirala]').forEach((th) => {
    th.classList.toggle('aktif', th.dataset.sirala === d.sirala);
    th.classList.toggle('artan', th.dataset.sirala === d.sirala && d.artan);
  });
  $('#satirlar').innerHTML = liste.map((g) => {
    const alt = [g.sablon, g.bicim && g.bicim !== g.sablon ? g.bicim : null].filter(Boolean).join(' · ');
    const degisim = g.degisim_24s ? `<span class="artis">+${sayi(g.degisim_24s)}</span>` : '<span class="yok">—</span>';
    return `<tr data-id="${esc(g.id)}" class="${g.id === d.secili ? 'secili' : ''}">
      <td class="t-tarih">${tarih(g.yayin)}</td>
      <td><span class="platform-adi"><span class="nokta p-${g.platform}"></span>${PLATFORM[g.platform] || g.platform}</span></td>
      <td class="baslik"><span class="ad">${esc(g.baslik || '(başlıksız)')}</span><span class="alt">${esc(alt)}</span></td>
      <td class="sayi">${g.deger === null ? '<span class="yok">—</span>' : sayi(g.deger)}</td>
      <td class="sayi">${degisim}</td>
      <td class="sayi">${g.etkilesim_orani === null ? '<span class="yok">—</span>' : yuzde(g.etkilesim_orani)}</td>
      <td>${puanHucresi(g)}</td></tr>`;
  }).join('');
  const bos = $('#bos');
  bos.hidden = liste.length > 0;
  bos.textContent = d.gonderiler.length ? 'Bu süzgeçle paylaşım yok.' : 'Henüz veri yok. İlk toplama sürüyor olabilir; birkaç dakika içinde yenilenir.';
  ayrintiCiz();
}

function seciliyiGoster() {
  $$('#satirlar tr').forEach((tr) => tr.classList.toggle('secili', tr.dataset.id === d.secili));
  const tr = $(`#satirlar tr[data-id="${CSS.escape(d.secili || '')}"]`);
  if (tr) tr.scrollIntoView({ block: 'nearest' });
  ayrintiCiz();
}

let seriIstegi = 0;
async function ayrintiCiz() {
  const kutu = $('#ayrinti');
  const g = d.gonderiler.find((x) => x.id === d.secili);
  if (!g) { kutu.innerHTML = '<p class="soluk">Bir paylaşım seçin.</p>'; return; }
  const k = ((d.durum && d.durum.kaynaklar) || {})[g.platform] || {};
  const son = g.son || {};
  const olcutler = Object.keys(OLCUT_ADI).filter((o) => son[o] !== null && son[o] !== undefined);
  const hucreler = olcutler.map((o) => `<div><span>${OLCUT_ADI[o]}</span><b>${o.endsWith('_ms') ? sure(son[o]) : sayi(son[o])}</b></div>`);
  if (g.puan !== null && g.puan !== undefined) hucreler.push(`<div><span>Puan${g.olgun ? '' : ' (ilk 48 sa)'}</span><b>${puanMetni(g.puan)}</b></div>`);
  if (g.etkilesim_orani !== null && g.etkilesim_orani !== undefined) hucreler.push(`<div><span>Etkileşim oranı</span><b>${yuzde(g.etkilesim_orani)}</b></div>`);
  const profilBaglantisi = /instagram\.com\/kpsstercihii\/?$|tiktok\.com\/@kpsstercihi$/.test(g.url || '');
  const kardesler = g.icerik ? d.gonderiler.filter((x) => x.icerik === g.icerik && x.id !== g.id) : [];
  kutu.innerHTML = `
    <div class="ust-bilgi"><span class="platform-adi"><span class="nokta p-${g.platform}"></span>${PLATFORM[g.platform]}</span>
      <span>·</span><span>${g.yayin ? uzunTarih.format(new Date(g.yayin)) : 'tarih yok'}</span></div>
    <h2>${esc(g.baslik || '(başlıksız)')}</h2>
    ${g.url ? `<a class="ac" href="${esc(g.url)}" target="_blank" rel="noopener">${profilBaglantisi ? 'Profili aç' : PLATFORM[g.platform] + '’da aç'} ↗</a>` : ''}
    ${profilBaglantisi ? '<p class="not">Bu paylaşımın kendi bağlantısı henüz yok; bulut verisi gelince doğrudan açılır.</p>' : ''}
    ${olcutler.length ? `<div class="olcutler">${hucreler.join('')}</div>` :
      `<p class="not">Ölçüm yok${k.durum && k.durum !== 'hazir' ? ': ' + esc(k.aciklama || DURUM_ADI[k.durum]) : ''}.</p>`}
    ${son.zaman ? `<p class="soluk" style="font-size:12px;margin:6px 0 0">Son ölçüm ${tarih(son.zaman)} · ${g.olcum_sayisi} ölçüm saklı${g.taban ? ' · dönem tabanı ' + sayi(Math.round(g.taban)) : ''}</p>` : ''}
    <div class="bolum grafik" id="grafik"></div>
    <div class="bolum"><h3>Sınıf</h3><div class="etiketler">
      ${[['Şablon', g.sablon], ['Biçim', g.bicim], ['Vakit', g.vakit], ['Tür', g.tur], ['Palet', g.palet], ['Müzik', g.muzik]]
        .filter((x) => x[1]).map((x) => `<span class="etiket">${x[0]}: ${esc(x[1])}</span>`).join('')}</div></div>
    ${kardesler.length ? `<div class="bolum"><h3>Aynı içerik diğer platformlarda</h3><ul class="kardesler">${kardesler.map((x) =>
      `<li><span class="nokta p-${x.platform}"></span><a href="#" data-git="${esc(x.id)}">${PLATFORM[x.platform]}</a>
       <span class="soluk">${x.deger === null ? 'ölçüm yok' : sayi(x.deger) + ' izlenme'}${x.puan ? ' · ' + puanMetni(x.puan) : ''}</span></li>`).join('')}</ul></div>` : ''}
    ${g.kapak ? `<img class="kapak" src="${esc(g.kapak)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">` : ''}
    ${g.metin ? `<div class="bolum"><h3>Metin</h3><div class="metin-kutu">${esc(g.metin)}</div></div>` : ''}`;
  const istek = ++seriIstegi;
  if (g.olcum_sayisi > 1) {
    const { seri } = await al('/api/seri?id=' + encodeURIComponent(g.id));
    if (istek === seriIstegi) grafikCiz($('#grafik'), seri, g);
  }
}

function grafikCiz(kutu, seri, g) {
  const alan = seri.some((s) => s.views !== null) ? 'views' : 'reach';
  const noktalar = seri.filter((s) => s[alan] !== null).map((s) => [Date.parse(s.zaman), s[alan]]);
  if (noktalar.length < 2 || !kutu) return;
  const G = 340, Y = 110, ust = 8, alt = 18;
  const x0 = Math.min(...noktalar.map((n) => n[0])), x1 = Math.max(...noktalar.map((n) => n[0]));
  const y1 = Math.max(...noktalar.map((n) => n[1])) || 1;
  const px = (x) => ((x - x0) / ((x1 - x0) || 1)) * (G - 4) + 2;
  const py = (y) => Y - alt - (y / y1) * (Y - alt - ust);
  const yol = noktalar.map((n, i) => (i ? 'L' : 'M') + px(n[0]).toFixed(1) + ' ' + py(n[1]).toFixed(1)).join(' ');
  const dolgu = yol + ` L${px(x1).toFixed(1)} ${Y - alt} L${px(x0).toFixed(1)} ${Y - alt} Z`;
  kutu.innerHTML = `<h3>${OLCUT_ADI[alan]} zaman içinde <span class="soluk">(${noktalar.length} ölçüm)</span></h3>
    <svg viewBox="0 0 ${G} ${Y}" preserveAspectRatio="none" role="img" aria-label="${OLCUT_ADI[alan]} grafiği">
      <path class="alan" d="${dolgu}"/><path class="cizgi" d="${yol}"/>
      <text x="2" y="${Y - 4}">${tarih(new Date(x0).toISOString())}</text>
      <text x="${G - 2}" y="${Y - 4}" text-anchor="end">${tarih(new Date(x1).toISOString())}</text>
      <text x="2" y="${ust + 2}">${sayi(y1)}</text></svg>`;
}

// ------------------------------------------------------------------ analiz
async function analizCiz() {
  const kutu = $('#analiz');
  const a = await al(`/api/analiz?platform=${encodeURIComponent(d.platform)}&gun=${encodeURIComponent(d.gun)}`);
  const ozet = Object.entries(d.ozet).filter(([p]) => !d.platform || p === d.platform);
  const k = (d.durum && d.durum.kaynaklar) || {};
  const kartlar = ozet.map(([p, o]) => `
    <div class="kart"><h4><span class="nokta p-${p}"></span>${PLATFORM[p] || p}</h4>
      <div class="buyuk">${o.olculen ? sayi(o.son_7_gun_deger) : '—'}</div>
      <div class="ince">${o.olculen ? 'son 7 günün paylaşımlarında izlenme' : esc(DURUM_ADI[(k[p] || {}).durum] || 'ölçüm yok')}</div>
      <div class="ince">${sayi(o.son_7_gun_adet)} paylaşım / 7 gün · toplam ${sayi(o.adet)}</div>
      ${o.artis_24s ? `<div class="ince">Son 24 saatte +${sayi(o.artis_24s)}</div>` : ''}
    </div>`).join('');
  const alan = a.kirilimlar[d.analizAlan];
  const enBuyuk = Math.max(3, ...alan.satirlar.map((s) => s.medyan_puan));
  const kirilim = `
    <div class="alt-sekme">${Object.entries(a.kirilimlar).map(([ad, v]) => `<button data-alan="${ad}" class="${ad === d.analizAlan ? 'secili' : ''}">${v.ad}</button>`).join('')}</div>
    ${alan.satirlar.length ? `<table class="kirilim"><thead><tr><th>${alan.ad}</th><th class="sayi">Paylaşım</th><th class="sayi">Medyan izlenme</th><th class="sayi">Etkileşim</th><th class="sayi">Medyan puan</th><th></th></tr></thead><tbody>
      ${alan.satirlar.map((s) => `<tr><td>${esc(s.ad)}</td><td class="sayi">${sayi(s.adet)}</td><td class="sayi">${sayi(Math.round(s.medyan_deger))}</td>
        <td class="sayi">${yuzde(s.etkilesim_orani)}</td><td class="sayi">${puanMetni(s.medyan_puan)}</td>
        <td class="cubuklu"><div class="yatay"><i style="width:${Math.min(s.medyan_puan / enBuyuk, 1) * 100}%"></i></div></td></tr>`).join('')}
    </tbody></table>` : '<p class="soluk">Bu dönemde ölçümü oturmuş paylaşım yok.</p>'}`;
  const sg = a.saat_gun;
  const renk = (p) => p === null || p === undefined ? 'var(--isi-0)' : p >= 1.5 ? 'var(--isi-4)' : p >= 1.15 ? 'var(--isi-3)' : p >= 0.9 ? 'var(--isi-2)' : 'var(--isi-1)';
  let isi = '<div></div>' + Array.from({ length: 24 }, (_, s) => `<div>${s % 3 === 0 ? s : ''}</div>`).join('');
  sg.izgara.forEach((satir, gi) => {
    isi += `<div class="etk">${sg.gun_adlari[gi]}</div>` + satir.map((h, s) =>
      `<div class="h" style="background:${renk(h && h.puan)}" title="${sg.gun_adlari[gi]} ${String(s).padStart(2, '0')}:00 — ${h ? h.adet + ' paylaşım, medyan puan ' + puanMetni(h.puan) : 'paylaşım yok'}"></div>`).join('');
  });
  const enIyiSaat = sg.saatler.filter((s) => s.adet >= 2).sort((x, y) => y.puan - x.puan)[0];
  const enIyiGun = sg.gunler.filter((s) => s.adet >= 2).sort((x, y) => y.puan - x.puan)[0];
  const siralama = (liste) => liste.length ? `<ol class="siralama">${liste.map((g) => `<li data-git="${esc(g.id)}">
      <span class="p">${puanMetni(g.puan)}</span><span class="ad"><span class="nokta p-${g.platform}"></span> ${esc(g.baslik || '')}</span>
      <span class="soluk">${sayi(g.deger)} · ${tarih(g.yayin)}</span></li>`).join('')}</ol>` : '<p class="soluk">Yeterli veri yok.</p>';
  kutu.innerHTML = `
    <div class="ozet-kartlari">${kartlar}</div>
    <div class="panel"><h3>Kırılım <span class="soluk">${sayi(a.olgun)} olgun paylaşım (48 saati geçmiş, ölçümü olan) · puan 1,00× = aynı dönemin olağan paylaşımı</span></h3>${kirilim}</div>
    <div class="panel"><h3>Saat ve gün <span class="soluk">Türkiye saati · hücre: o saatteki paylaşımların medyan puanı
      ${enIyiSaat ? ' · en iyi saat ' + String(enIyiSaat.saat).padStart(2, '0') + ':00 (' + puanMetni(enIyiSaat.puan) + ', ' + enIyiSaat.adet + ' paylaşım)' : ''}
      ${enIyiGun ? ' · en iyi gün ' + enIyiGun.gun + ' (' + puanMetni(enIyiGun.puan) + ')' : ''}</span></h3>
      <div class="isi">${isi}</div>
      <div class="lejant">daha zayıf <i style="background:var(--isi-1)"></i><i style="background:var(--isi-2)"></i><i style="background:var(--isi-3)"></i><i style="background:var(--isi-4)"></i> daha güçlü · boş: paylaşım yok</div></div>
    <div class="izgara-2">
      <div class="panel"><h3>En iyi 10</h3>${siralama(a.en_iyi)}</div>
      <div class="panel"><h3>En zayıf 10</h3>${siralama(a.en_kotu)}</div>
    </div>
    <p class="aciklama-notu">Puan, paylaşımın izlenmesinin (yoksa erişiminin) aynı platformda yayın sırasına göre en yakın
      20 olgun paylaşımın (12 önceki, 8 sonraki) medyanına oranıdır; kanal büyüdükçe taban da yükselir. İlk 48 saatteki paylaşımlar
      kırılımlara ve sıralamalara girmez. Telegram izlenmeleri herkese açık önizlemeden, YouTube izlenmeleri kanal RSS akışından,
      Instagram ölçümleri Graph API'den okunur.</p>`;
}

// ------------------------------------------------------------------ olaylar
function gorunumSec(g) {
  d.gorunum = g;
  $$('.sekmeler button').forEach((b) => b.classList.toggle('secili', b.dataset.gorunum === g));
  $('#akis').hidden = g !== 'akis';
  $('#analiz').hidden = g !== 'analiz';
  if (g === 'akis') akisCiz(); else analizCiz();
}

function yenidenCiz() { kenarCiz(); if (d.gorunum === 'akis') akisCiz(); else analizCiz(); }

function git(id) {
  const g = d.gonderiler.find((x) => x.id === id);
  if (!g) return;
  d.platform = ''; d.sablon = ''; d.ara = ''; $('#ara').value = '';
  if (g.yayin && d.gun && Date.parse(g.yayin) < Date.now() - Number(d.gun) * 864e5) { d.gun = ''; donemIsaretle(); }
  d.secili = id;
  gorunumSec('akis');
  kenarCiz();
  seciliyiGoster();
}

function donemIsaretle() { $$('.donem button').forEach((b) => b.classList.toggle('secili', b.dataset.gun === d.gun)); }

function ac() {
  const g = d.gonderiler.find((x) => x.id === d.secili);
  if (g && g.url) window.open(g.url, '_blank', 'noopener');
}

function adim(yon) {
  if (!d.liste || !d.liste.length) return;
  const i = d.liste.findIndex((g) => g.id === d.secili);
  const j = Math.max(0, Math.min(d.liste.length - 1, (i < 0 ? 0 : i) + yon));
  d.secili = d.liste[j].id;
  seciliyiGoster();
}

let yoklama = null;
async function yenile() {
  await al('/api/yenile?bulut=1', { method: 'POST' });
  if (yoklama) clearInterval(yoklama);
  $('#yenile').classList.add('calisiyor'); $('#yenile').textContent = 'Toplanıyor…';
  yoklama = setInterval(async () => {
    d.durum = await al('/api/durum');
    if (!toplamaDurumu()) { clearInterval(yoklama); yoklama = null; yukle(); }
  }, 2500);
}

function temaDegistir() {
  const kok = document.documentElement;
  const koyuMu = kok.dataset.theme ? kok.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  kok.dataset.theme = koyuMu ? 'light' : 'dark';
  try { localStorage.setItem('tema', kok.dataset.theme); } catch (e) { /* yok */ }
}

document.addEventListener('click', (e) => {
  const h = e.target.closest('[data-git]');
  if (h) { e.preventDefault(); git(h.dataset.git); return; }
  const tr = e.target.closest('#satirlar tr');
  if (tr) { d.secili = tr.dataset.id; seciliyiGoster(); return; }
  const th = e.target.closest('th[data-sirala]');
  if (th) { if (d.sirala === th.dataset.sirala) d.artan = !d.artan; else { d.sirala = th.dataset.sirala; d.artan = false; } akisCiz(); return; }
  const p = e.target.closest('#platformlar li');
  if (p) { d.platform = p.dataset.platform; d.sablon = ''; yenidenCiz(); return; }
  const s = e.target.closest('#sablonlar li');
  if (s) { d.sablon = s.dataset.sablon; yenidenCiz(); return; }
  const gb = e.target.closest('.sekmeler button');
  if (gb) { gorunumSec(gb.dataset.gorunum); return; }
  const db = e.target.closest('.donem button');
  if (db) { d.gun = db.dataset.gun; donemIsaretle(); yenidenCiz(); return; }
  const ab = e.target.closest('.alt-sekme button');
  if (ab) { d.analizAlan = ab.dataset.alan; analizCiz(); }
});
$('#yenile').addEventListener('click', yenile);
$('#tema').addEventListener('click', temaDegistir);
$('#yardim-ac').addEventListener('click', () => $('#yardim').showModal());
$('#ara').addEventListener('input', (e) => { d.ara = e.target.value; if (d.gorunum !== 'akis') gorunumSec('akis'); else akisCiz(); });
$('#tablo').addEventListener('dblclick', (e) => { if (e.target.closest('#satirlar tr')) ac(); });

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const yazi = e.target.matches('input, textarea');
  if (e.key === 'Escape') {
    if (yazi) e.target.blur();
    d.ara = ''; $('#ara').value = ''; d.sablon = ''; d.platform = ''; yenidenCiz(); return;
  }
  if (yazi) { if (e.key === 'Enter' || e.key === 'ArrowDown') { e.target.blur(); } return; }
  if ($('#yardim').open) return;
  const platformlar = d.durum ? d.durum.platformlar : Object.keys(PLATFORM);
  switch (e.key) {
    case 'j': case 'ArrowDown': e.preventDefault(); if (d.gorunum === 'akis') adim(1); break;
    case 'k': case 'ArrowUp': e.preventDefault(); if (d.gorunum === 'akis') adim(-1); break;
    case 'Enter': case 'o': if (d.gorunum === 'akis') ac(); break;
    case '/': e.preventDefault(); $('#ara').focus(); break;
    case 'a': gorunumSec(d.gorunum === 'akis' ? 'analiz' : 'akis'); break;
    case 'r': yenile(); break;
    case 't': temaDegistir(); break;
    case '?': $('#yardim').showModal(); break;
    default:
      if (/^[0-9]$/.test(e.key)) {
        const i = Number(e.key);
        if (i === 0) d.platform = ''; else if (platformlar[i - 1]) d.platform = platformlar[i - 1]; else return;
        d.sablon = ''; yenidenCiz();
      }
  }
});

yukle().then(() => {
  // İlk açılışta toplama sürüyorsa bitince tazele.
  if (toplamaDurumu()) {
    yoklama = setInterval(async () => {
      d.durum = await al('/api/durum');
      if (!toplamaDurumu()) { clearInterval(yoklama); yoklama = null; yukle(); }
    }, 3000);
  }
}).catch((h) => { $('#bos').hidden = false; $('#bos').textContent = 'Sunucuya ulaşılamadı: ' + h.message; });
setInterval(() => { if (!yoklama && document.visibilityState === 'visible') yukle(); }, 10 * 60 * 1000);
