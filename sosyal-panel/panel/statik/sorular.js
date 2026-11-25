'use strict';
// "İnsanlar ne soruyor": site asistanına ve Instagram yorumlarına gelen sorular. uygulama.js'teki yardımcıları
// ($, esc, sayi, yuzde, tarih, al, d) kullanır. Soru, cevap ve kullanıcı adları güvenilmez metindir: hepsi esc() ile basılır.

const TUR_ADI = {
  ilan: 'İlan', puan: 'Puan', sss: 'SSS', kimlik: 'Kimlik', selam: 'Selam', tesekkur: 'Teşekkür', bilinmiyor: 'Cevapsız',
};
const KANAL_ADI = { site: 'Site', instagram: 'Instagram' };
const IG_DURUM_ADI = { yanitlandi: 'Yanıtlandı', atlandi: 'Sana bırakıldı', hata: 'Hata' };
const SAYFA_BOYU = 200;

const s = {
  veri: null, ara: '', kanal: '', tur: '', geri: '', bas: '', bit: '', odak: null, acik: new Set(), goster: SAYFA_BOYU,
};

const gunBicim = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short', timeZone: 'Europe/Istanbul' });
const trGun = (iso) => { // Türkiye takvim günü (YYYY-AA-GG)
  if (!iso) return '';
  const t = new Date(Date.parse(iso) + 3 * 3600e3);
  return t.toISOString().slice(0, 10);
};
const katla = (x) => String(x ?? '').toLocaleLowerCase('tr').replace(/ı/g, 'i').replace(/ç/g, 'c').replace(/ğ/g, 'g')
  .replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u').normalize('NFD').replace(/[̀-ͯ]/g, '');
const guvenliUrl = (u) => /^https?:\/\//i.test(String(u || '')) ? String(u) : null;
const degisim = (simdi, once) => {
  if (!once) return '';
  const f = (simdi - once) / once;
  return `<span class="${f >= 0 ? 'artis' : 'dusus'}">${f >= 0 ? '+' : ''}${Math.round(f * 100)}%</span> önceki döneme göre`;
};

async function sorularCiz() {
  const kutu = $('#sorular');
  if (!s.veri) kutu.innerHTML = '<p class="soluk" style="padding:20px">Yükleniyor…</p>';
  try {
    s.veri = await al('/api/sorular?gun=' + encodeURIComponent(d.gun));
  } catch (h) {
    kutu.innerHTML = `<div class="bos">Sorular okunamadı: ${esc(h.message)}</div>`;
    return;
  }
  s.goster = SAYFA_BOYU;
  sorularIskeleti();
}

function anahtarNotu(v) {
  if (v.anahtar_var || v.ornek) return '';
  return `<div class="ipucu"><b>Asistan anahtarı yok.</b> Sorular toplanmıyor. <code>ASISTAN_ANAHTAR</code> değerini tek satır olarak
    şu dosyaya kaydet: <code>${esc(v.anahtar_yolu)}</code>. Panel bir sonraki toplamada (ya da Yenile ile) kayıtları çeker.</div>`;
}

function sorularIskeleti() {
  const v = s.veri, k = v.kpi, kutu = $('#sorular');
  const donemAdi = d.gun ? `son ${d.gun} gün` : 'tüm kayıtlar';
  const durumHata = v.durum && v.durum.durum === 'hata'
    ? `<div class="ipucu hata">Son toplama başarısız: ${esc(v.durum.aciklama || '')}</div>` : '';
  if (!v.toplam) {
    kutu.innerHTML = `${anahtarNotu(v)}${durumHata}<div class="bos">Henüz soru kaydı yok.${v.anahtar_var
      ? ' Asistana soru geldikçe saatlik toplamayla burada görünür.' : ''}</div>`;
    return;
  }
  const kartlar = `
    <div class="kart"><h4>Toplam soru</h4>
      <div class="buyuk">${sayi(k.son7)} <small>/ 7 gün</small></div>
      <div class="ince">${degisim(k.son7, k.once7) || '&nbsp;'}</div>
      <div class="ince">${sayi(k.son30)} / 30 gün ${k.once30 ? '· ' + degisim(k.son30, k.once30) : ''}</div></div>
    <div class="kart ${k.cevapsiz_orani >= 0.2 ? 'dikkat' : ''}"><h4>Cevapsız oranı</h4>
      <div class="buyuk">${yuzde(k.cevapsiz_orani)}</div>
      <div class="ince">${sayi(k.cevapsiz)} / ${sayi(v.donem_adet)} soru cevapsız kaldı (${donemAdi})</div>
      <div class="ince">${sayi(k.ilansiz)} ilan sorusu açık ilan bulamadı</div></div>
    <div class="kart"><h4>Faydalı oranı</h4>
      <div class="buyuk">${yuzde(k.faydali_orani)}</div>
      <div class="ince">${sayi(k.geri_evet)} işe yaradı · ${sayi(k.geri_hayir)} yaramadı</div>
      <div class="ince">Sitede soranların ${yuzde(k.geri_orani)} oy verdi</div></div>
    <div class="kart"><h4><span class="nokta p-instagram"></span>Instagram yorumları</h4>
      <div class="buyuk">${sayi(k.ig_yanitlandi)} <small>yanıtlandı</small></div>
      <div class="ince">${sayi(k.ig_birakilan)} sana bırakıldı${k.ig_hata ? ' · ' + sayi(k.ig_hata) + ' hata' : ''}${k.ig_bekleyen ? ' · ' + sayi(k.ig_bekleyen) + ' bekliyor' : ''}</div>
      <div class="ince">${sayi(k.ig_toplam)} yorum (${donemAdi})</div></div>`;

  kutu.innerHTML = `
    ${anahtarNotu(v)}${durumHata}
    <div class="ozet-kartlari">${kartlar}</div>
    <div class="panel"><h3>Günlük soru sayısı <span class="soluk">${donemAdi} · Türkiye saati</span>
      <span class="lejant-satir"><i class="k-site"></i>Site <i class="k-instagram"></i>Instagram</span></h3>
      ${gunlukCiz(v.gunluk)}</div>
    <h2 class="bolum-baslik">Neye ihtiyaç var</h2>
    <div class="panel onemli"><h3>Cevapsız kalan sorular <span class="soluk">asistanın bilmediği; benzer yazılışlar tek satırda · ${donemAdi}</span></h3>
      ${grupListesi(v.cevapsiz_sorular, 'Bu dönemde cevapsız kalan soru yok.')}</div>
    <div class="izgara-2">
      <div class="panel"><h3>En çok sorulan meslekler</h3>${sayimListesi(v.meslekler, 'meslek', 'Sorularda meslek adı geçmedi.')}</div>
      <div class="panel"><h3>En çok sorulan iller</h3>${sayimListesi(v.iller, 'il', 'Sorularda il adı geçmedi.')}</div>
    </div>
    <div class="izgara-2">
      <div class="panel"><h3>Aranıp ilanı olmayanlar <span class="soluk">talep var, açık ilan yok</span></h3>
        ${grupListesi(v.ilansiz_sorular, 'Her ilan sorusuna en az bir açık ilan bulundu.')}</div>
      <div class="panel"><h3>Sık geçen kelimeler</h3>
        <div class="kelimeler">${v.kelimeler.length ? v.kelimeler.map((w) =>
          `<button class="kelime" data-kelime="${esc(w.kelime)}" title="${esc(w.bicimler.join(', '))}">${esc(w.kelime)} <span>${sayi(w.adet)}</span></button>`).join('')
          : '<p class="soluk">Yeterli veri yok.</p>'}</div>
        <h3 style="margin-top:16px">Cevap türleri</h3>${turDagilimi(v.turler, v.donem_adet)}</div>
    </div>
    <div class="panel" id="kayit-paneli"><h3>Tüm kayıtlar <span class="soluk" id="kayit-sayisi"></span></h3>
      <div class="arac-cubugu">
        <input type="search" id="s-ara" placeholder="Soru, cevap, kullanıcı ara…" value="${esc(s.ara)}" autocomplete="off">
        <select id="s-kanal" aria-label="Kanal"><option value="">Tüm kanallar</option><option value="site">Site</option><option value="instagram">Instagram</option></select>
        <select id="s-tur" aria-label="Tür"><option value="">Tüm türler</option>${Object.entries(TUR_ADI).map(([t, a]) => `<option value="${t}">${a}</option>`).join('')}</select>
        <select id="s-geri" aria-label="Geri bildirim"><option value="">Geri bildirim: hepsi</option><option value="1">İşe yaradı</option><option value="-1">İşe yaramadı</option><option value="0">Oy yok</option></select>
        <label class="tarih-aralik">Tarih <input type="date" id="s-bas" value="${esc(s.bas)}" aria-label="Başlangıç"> – <input type="date" id="s-bit" value="${esc(s.bit)}" aria-label="Bitiş"></label>
        <span id="s-odak"></span>
        <button id="s-temizle" title="Süzgeçleri temizle">Temizle</button>
        <button id="s-csv" title="Süzülmüş kayıtları CSV olarak indir">CSV indir</button>
      </div>
      ${v.kesildi ? '<p class="not">Dönem çok büyük; en yeni 20 000 kayıt gösteriliyor. Daha kısa dönem seç.</p>' : ''}
      <div class="kayit-kap"><table class="kirilim kayitlar"><thead><tr>
        <th class="k-zaman">Zaman</th><th class="k-kanal">Kanal</th><th>Soru</th><th class="k-tur">Tür</th>
        <th class="sayi k-ilan">İlan</th><th class="k-geri">Geri bildirim</th><th class="k-durum">Durum</th></tr></thead>
        <tbody id="kayit-satirlari"></tbody></table></div>
      <div id="kayit-fazla"></div>
    </div>`;
  $('#s-kanal').value = s.kanal; $('#s-tur').value = s.tur; $('#s-geri').value = s.geri;
  kayitlarCiz();
}

function gunlukCiz(gunler) {
  if (!gunler.length) return '<p class="soluk">Veri yok.</p>';
  const enBuyuk = Math.max(1, ...gunler.map((g) => g.site + g.instagram));
  const adim = Math.ceil(gunler.length / 10);
  const sutunlar = gunler.map((g, i) => {
    const toplam = g.site + g.instagram;
    const baslik = `${gunBicim.format(new Date(g.gun + 'T12:00:00Z'))}: ${toplam} soru (site ${g.site}, Instagram ${g.instagram}) · ${g.cevapsiz} cevapsız`;
    return `<div class="sutun" title="${esc(baslik)}"><div class="yigin" style="height:${(toplam / enBuyuk) * 100}%">
      <i class="k-instagram" style="flex:${g.instagram}"></i><i class="k-site" style="flex:${g.site}"></i></div>
      <span class="etk">${(gunler.length - 1 - i) % adim === 0 ? esc(gunBicim.format(new Date(g.gun + 'T12:00:00Z'))) : ''}</span></div>`;
  }).join('');
  return `<div class="gunluk"><div class="y-ekseni"><span>${sayi(enBuyuk)}</span><span>0</span></div><div class="sutunlar">${sutunlar}</div></div>`;
}

function grupListesi(gruplar, bos) {
  if (!gruplar.length) return `<p class="soluk">${bos}</p>`;
  const enBuyuk = Math.max(...gruplar.map((g) => g.adet));
  return `<ol class="gruplar">${gruplar.map((g, i) => `
    <li data-grup="${i}" data-liste="${gruplar === s.veri.cevapsiz_sorular ? 'c' : 'i'}" title="Kayıtları göster">
      <span class="adet-rozet" style="--o:${(g.adet / enBuyuk).toFixed(2)}">${sayi(g.adet)}</span>
      <span class="g-metin">${esc(g.metin)}${g.ornekler.length ? `<span class="g-ornek">ayrıca: ${g.ornekler.map((o) => '“' + esc(o) + '”').join(', ')}</span>` : ''}</span>
      <span class="g-yan">${Object.entries(g.kanallar).map(([kn, n]) => `<span class="nokta k-${esc(kn)}"></span>${sayi(n)}`).join(' ')}
        <span class="soluk">son ${tarih(g.son)}</span></span></li>`).join('')}</ol>`;
}

function sayimListesi(satirlar, tur, bos) {
  if (!satirlar.length) return `<p class="soluk">${bos}</p>`;
  const enBuyuk = Math.max(...satirlar.map((x) => x.adet));
  return `<table class="kirilim sayim"><tbody>${satirlar.map((x) => `
    <tr data-odak="${tur}" data-deger="${esc(x.ad)}" title="Kayıtları göster"><td class="ad">${esc(x.ad)}</td>
      <td class="cubuklu"><div class="yatay sade"><i style="width:${(x.adet / enBuyuk) * 100}%"></i></div></td>
      <td class="sayi">${sayi(x.adet)}</td>
      <td class="sayi ek">${x.cevapsiz ? `<span class="uyari-metin">${sayi(x.cevapsiz)} cevapsız</span>` : ''}${x.ilansiz ? ` <span class="kotu-metin">${sayi(x.ilansiz)} ilansız</span>` : ''}</td></tr>`).join('')}
    </tbody></table>`;
}

function turDagilimi(turler, toplam) {
  if (!turler.length) return '<p class="soluk">Veri yok.</p>';
  return `<div class="tur-serit">${turler.map((t) => `<i class="t-${esc(t.tur)}" style="flex:${t.adet}" title="${esc(TUR_ADI[t.tur] || t.tur)}: ${t.adet}"></i>`).join('')}</div>
    <ul class="tur-lejant">${turler.map((t) => `<li data-tur-sec="${esc(t.tur)}"><i class="t-${esc(t.tur)}"></i>${esc(TUR_ADI[t.tur] || t.tur)}
      <b>${sayi(t.adet)}</b><span class="soluk">${yuzde(t.adet / (toplam || 1))}</span></li>`).join('')}</ul>`;
}

// ------------------------------------------------------------------ kayıt tablosu
function suzulmusKayitlar() {
  const v = s.veri;
  if (!v) return [];
  const ara = katla(s.ara.trim());
  const odakIdler = s.odak && s.odak.idler ? new Set(s.odak.idler) : null;
  return v.kayitlar.filter((r) => {
    if (s.kanal && (r.kanal || 'site') !== s.kanal) return false;
    if (s.tur && r.tur !== s.tur) return false;
    if (s.geri === '1' && r.geri !== 1) return false;
    if (s.geri === '-1' && r.geri !== -1) return false;
    if (s.geri === '0' && (r.geri === 1 || r.geri === -1)) return false;
    const g = trGun(r.zaman);
    if (s.bas && g < s.bas) return false;
    if (s.bit && g > s.bit) return false;
    if (s.odak) {
      if (odakIdler && !odakIdler.has(r.id)) return false;
      if (s.odak.tur === 'meslek' && r.meslek !== s.odak.deger) return false;
      if (s.odak.tur === 'il' && !(r.iller || []).includes(s.odak.deger)) return false;
    }
    if (ara) {
      const m = r.meta || {};
      const metin = katla([r.soru, r.metin, r.gonderilen, m.kullanici, r.sayfa].join(' '));
      if (!metin.includes(ara)) return false;
    }
    return true;
  });
}

function geriHucresi(r) {
  if ((r.kanal || 'site') !== 'site') return '<span class="yok">—</span>';
  if (r.geri === 1) return '<span class="artis">İşe yaradı</span>';
  if (r.geri === -1) return '<span class="kotu-metin">İşe yaramadı</span>';
  return '<span class="yok">oy yok</span>';
}

function durumHucresi(r) {
  if (r.kanal !== 'instagram') return '<span class="yok">—</span>';
  const ad = IG_DURUM_ADI[r.durum] || 'Bekliyor';
  return `<span class="durum-rozet d-${esc(r.durum || 'bekliyor')}">${ad}</span>`;
}

function ayrintiSatiri(r) {
  const m = r.meta || {};
  const baglantilar = (r.baglantilar || []).map(guvenliUrl).filter(Boolean);
  const alan = (ad, deger) => deger ? `<dt>${ad}</dt><dd>${deger}</dd>` : '';
  return `<tr class="acilir"><td colspan="7"><dl class="kayit-ayrinti">
    ${alan('Soru', `<div class="metin-kutu tam">${esc(r.soru || '')}</div>`)}
    ${alan('Cevap', r.metin ? `<div class="metin-kutu tam">${esc(r.metin)}</div>` : '<span class="soluk">cevap metni yok</span>')}
    ${r.kanal === 'instagram' ? alan('Gönderilen yanıt', r.gonderilen && r.durum === 'yanitlandi' ? `<div class="metin-kutu tam">${esc(r.gonderilen)}</div>`
      : `<span class="soluk">${r.durum === 'atlandi' ? 'Yanıt gönderilmedi, sana bırakıldı' : r.durum === 'hata' ? 'Gönderim hata verdi' : 'Henüz gönderilmedi'}${r.gonderilen ? ' (' + esc(r.gonderilen) + ')' : ''}</span>`) : ''}
    ${alan('Bağlantılar', baglantilar.length ? baglantilar.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(u.replace(/^https?:\/\/(www\.)?/, ''))}</a>`).join('<br>') : '')}
    ${alan('Durum', [TUR_ADI[r.tur] || esc(r.tur || '—'), r.ilan_sayisi !== null && r.ilan_sayisi !== undefined ? `${sayi(r.ilan_sayisi)} ilan` : null,
      r.kanal === 'instagram' ? (IG_DURUM_ADI[r.durum] || 'Bekliyor') : null].filter(Boolean).join(' · '))}
    ${alan('Sayfa', r.sayfa ? esc(r.sayfa) : '')}
    ${alan('Kullanıcı', m.kullanici ? esc(m.kullanici) : '')}
    ${alan('Algılanan', [r.meslek, ...(r.iller || [])].filter(Boolean).map(esc).join(' · '))}
    ${alan('Kayıt', `#${esc(r.id)} · ${uzunTarih.format(new Date(r.zaman))}`)}
  </dl></td></tr>`;
}

function kayitlarCiz() {
  const liste = suzulmusKayitlar();
  const govde = $('#kayit-satirlari');
  if (!govde) return;
  const gosterilen = liste.slice(0, s.goster);
  govde.innerHTML = gosterilen.map((r) => {
    const acik = s.acik.has(r.id);
    const kanal = r.kanal || 'site';
    return `<tr data-kid="${esc(r.id)}" class="${acik ? 'acik' : ''}" aria-expanded="${acik}">
      <td class="k-zaman">${tarih(r.zaman)}</td>
      <td><span class="platform-adi"><span class="nokta k-${esc(kanal)}"></span>${esc(KANAL_ADI[kanal] || kanal)}</span></td>
      <td class="k-soru"><span class="ad">${esc(r.soru || '')}</span></td>
      <td><span class="tur-rozet t-${esc(r.tur || '')}">${esc(TUR_ADI[r.tur] || r.tur || '—')}</span></td>
      <td class="sayi">${r.tur === 'ilan' ? (r.ilan_sayisi ? sayi(r.ilan_sayisi) : '<span class="kotu-metin">0</span>') : '<span class="yok">—</span>'}</td>
      <td>${geriHucresi(r)}</td><td>${durumHucresi(r)}</td></tr>${acik ? ayrintiSatiri(r) : ''}`;
  }).join('') || '<tr><td colspan="7" class="bos">Bu süzgeçle kayıt yok.</td></tr>';
  $('#kayit-sayisi').textContent = `${sayi(liste.length)} / ${sayi(s.veri.kayitlar.length)} kayıt`;
  $('#kayit-fazla').innerHTML = liste.length > s.goster
    ? `<button id="s-daha">${sayi(Math.min(SAYFA_BOYU, liste.length - s.goster))} kayıt daha göster</button>` : '';
  $('#s-odak').innerHTML = s.odak ? `<span class="odak-cip">${esc(s.odak.ad)} <button id="s-odak-kaldir" aria-label="Kaldır">×</button></span>` : '';
}

function csvIndir() {
  const liste = suzulmusKayitlar();
  const hucre = (x) => {
    let t = x === null || x === undefined ? '' : String(x);
    if (/^[=+\-@\t\r]/.test(t)) t = "'" + t;   // tablo programlarında formül olarak çalışmasın
    return '"' + t.replace(/"/g, '""') + '"';
  };
  const baslik = ['id', 'zaman', 'kanal', 'tur', 'soru', 'cevap', 'ilan_sayisi', 'geri', 'durum', 'gonderilen', 'baglantilar', 'sayfa', 'kullanici', 'meslek', 'iller'];
  const satirlar = liste.map((r) => [r.id, r.zaman, r.kanal, r.tur, r.soru, r.metin, r.ilan_sayisi, r.geri, r.durum, r.gonderilen,
    (r.baglantilar || []).join(' '), r.sayfa, (r.meta || {}).kullanici, r.meslek, (r.iller || []).join(' ')].map(hucre).join(';'));
  const blob = new Blob(['﻿' + [baslik.join(';'), ...satirlar].join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `sorular-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function odakla(odak) {
  s.odak = odak; s.goster = SAYFA_BOYU; s.acik.clear();
  kayitlarCiz();
  const p = $('#kayit-paneli');
  if (p) p.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ------------------------------------------------------------------ olaylar
$('#sorular').addEventListener('click', (e) => {
  const tr = e.target.closest('#kayit-satirlari tr[data-kid]');
  if (tr && !e.target.closest('a')) {
    const id = Number(tr.dataset.kid);
    if (s.acik.has(id)) s.acik.delete(id); else s.acik.add(id);
    kayitlarCiz(); return;
  }
  const g = e.target.closest('li[data-grup]');
  if (g) {
    const grup = (g.dataset.liste === 'c' ? s.veri.cevapsiz_sorular : s.veri.ilansiz_sorular)[Number(g.dataset.grup)];
    if (grup) odakla({ idler: grup.idler, ad: '“' + grup.metin + '” (' + grup.adet + ')' });
    return;
  }
  const o = e.target.closest('tr[data-odak]');
  if (o) { odakla({ tur: o.dataset.odak, deger: o.dataset.deger, ad: (o.dataset.odak === 'il' ? 'İl: ' : 'Meslek: ') + o.dataset.deger }); return; }
  const w = e.target.closest('[data-kelime]');
  if (w) { s.ara = w.dataset.kelime; $('#s-ara').value = s.ara; odakla(s.odak); return; }
  const t = e.target.closest('[data-tur-sec]');
  if (t) { s.tur = t.dataset.turSec; $('#s-tur').value = s.tur; odakla(s.odak); return; }
  if (e.target.closest('#s-odak-kaldir')) { s.odak = null; kayitlarCiz(); return; }
  if (e.target.closest('#s-daha')) { s.goster += SAYFA_BOYU; kayitlarCiz(); return; }
  if (e.target.closest('#s-csv')) { csvIndir(); return; }
  if (e.target.closest('#s-temizle')) {
    Object.assign(s, { ara: '', kanal: '', tur: '', geri: '', bas: '', bit: '', odak: null, goster: SAYFA_BOYU });
    s.acik.clear(); sorularIskeleti();
  }
});
$('#sorular').addEventListener('input', (e) => {
  const alanlar = { 's-ara': 'ara', 's-kanal': 'kanal', 's-tur': 'tur', 's-geri': 'geri', 's-bas': 'bas', 's-bit': 'bit' };
  const ad = alanlar[e.target.id];
  if (!ad) return;
  s[ad] = e.target.value; s.goster = SAYFA_BOYU;
  kayitlarCiz();
});
