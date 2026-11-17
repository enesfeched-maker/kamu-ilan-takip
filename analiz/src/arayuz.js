// Panel arayüzü: tek sayfa, Türkçe, açık/koyu tema, DOM ile çizim (toplanan hiçbir metin innerHTML'e girmez).
// Betik ve stil nonce ile çalışır (CSP). Grafikler satır içi SVG'dir; dış kütüphane yoktur.

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const TEMEL_CSS = String.raw`
:root{--zemin:#F6F6F1;--kart:#FFFFFF;--yazi:#16201E;--soluk:#5E6B67;--cizgi:#E3E5DF;--ac:#1B7F72;--ac-yumusak:#DCEEE9;--uyari:#B3261E;--golge:0 1px 2px rgba(20,30,28,.06)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--zemin:#0D1210;--kart:#151C1A;--yazi:#E8EEEB;--soluk:#93A39D;--cizgi:#25302D;--ac:#4FC3AE;--ac-yumusak:#1C332E;--uyari:#FF8A80;--golge:none}}
:root[data-theme=dark]{--zemin:#0D1210;--kart:#151C1A;--yazi:#E8EEEB;--soluk:#93A39D;--cizgi:#25302D;--ac:#4FC3AE;--ac-yumusak:#1C332E;--uyari:#FF8A80;--golge:none}
*{box-sizing:border-box}
body{margin:0;background:var(--zemin);color:var(--yazi);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.kap{max-width:1240px;margin:0 auto;padding:20px 16px 64px}
`;

const PANEL_CSS = String.raw`
.ust{display:flex;flex-wrap:wrap;align-items:center;gap:12px 20px;margin-bottom:20px}
.ust h1{font-size:20px;margin:0;font-weight:700;letter-spacing:-.01em}
.ust h1 small{display:block;font-size:13px;font-weight:400;color:var(--soluk)}
.bosluk{flex:1}
.segment{display:inline-flex;border:1px solid var(--cizgi);border-radius:10px;overflow:hidden;background:var(--kart)}
.segment button{border:0;background:none;color:var(--soluk);padding:7px 14px;font:inherit;cursor:pointer}
.segment button+button{border-left:1px solid var(--cizgi)}
.segment button[aria-pressed=true]{background:var(--ac);color:#fff;font-weight:600}
@media (prefers-color-scheme:dark){.segment button[aria-pressed=true]{color:#06231E}}
.canli{display:inline-flex;align-items:center;gap:8px;font-size:14px;color:var(--soluk)}
.canli b{color:var(--yazi);font-size:16px}
.nokta{width:9px;height:9px;border-radius:50%;background:var(--ac);box-shadow:0 0 0 3px var(--ac-yumusak)}
a.cikis{color:var(--soluk);font-size:13px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:12px}
.kpi div,.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;box-shadow:var(--golge)}
.kpi div{padding:14px 16px}
.kpi span{display:block;font-size:12.5px;color:var(--soluk)}
.kpi strong{display:block;font-size:26px;line-height:1.2;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi em{font-style:normal;font-size:12px;color:var(--soluk)}
h2.bolum{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--soluk);margin:30px 0 10px;font-weight:600}
.izgara{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
.izgara.genis{grid-template-columns:repeat(auto-fit,minmax(520px,1fr))}
@media (max-width:600px){.izgara,.izgara.genis{grid-template-columns:1fr}}
.kart{padding:14px 16px 16px;min-width:0}
.uye-ara{width:100%;max-width:320px;padding:8px 10px;border:1px solid var(--cizgi);border-radius:8px;background:transparent;color:inherit;font:inherit;margin-bottom:10px}
.uye-tablo{overflow-x:auto;max-height:520px;overflow-y:auto}
.uye-tablo table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
.uye-tablo th{position:sticky;top:0;background:var(--kart);text-align:left;font-weight:600;color:var(--soluk);font-size:12px;cursor:pointer;white-space:nowrap}
.uye-tablo th,.uye-tablo td{padding:7px 8px;border-bottom:1px solid var(--cizgi);white-space:nowrap}
.uye-tablo td.sayi,.uye-tablo th.sayi{text-align:right}
.uye-tablo a{color:inherit;font-weight:600}
.kart h3{margin:0 0 10px;font-size:15px;font-weight:600}
.kart h3 small{font-weight:400;color:var(--soluk);margin-left:6px;font-size:12.5px}
.not{color:var(--soluk);font-size:13px;margin:8px 0 0}
.bos{color:var(--soluk);font-size:14px;padding:8px 0}
.satir{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;padding:5px 0;border-top:1px solid var(--cizgi);align-items:center}
.satir:first-of-type{border-top:0}
.ad{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}
.ad small{color:var(--soluk)}
.say{font-variant-numeric:tabular-nums;font-size:14px;text-align:right}
.say small{color:var(--soluk);margin-left:6px}
.cubuk{grid-column:1/-1;height:5px;background:var(--ac-yumusak);border-radius:3px;overflow:hidden}
.cubuk i{display:block;height:100%;background:var(--ac);border-radius:3px;width:0}
.cubuk.uyari i{background:var(--uyari)}
.grafik{width:100%;height:auto;display:block}
.grafik text{fill:var(--soluk);font-size:11px}
.grafik .izgara-cizgi{stroke:var(--cizgi);stroke-width:1}
.grafik .hat{fill:none;stroke:var(--ac);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.grafik .alan{fill:var(--ac);opacity:.12}
.grafik .nokta-g{fill:var(--ac);stroke:var(--kart);stroke-width:2}
.grafik .hucre{fill:var(--ac)}
.grafik .hucre-bos{fill:var(--ac-yumusak)}
.huni{display:grid;gap:8px}
.huni-adim{display:grid;grid-template-columns:150px minmax(0,1fr) auto;gap:10px;align-items:center;font-size:14px}
.huni-adim .cubuk{grid-column:auto;height:18px;border-radius:4px}
.huni-adim .cubuk i{border-radius:4px}
@media (max-width:600px){.huni-adim{grid-template-columns:110px minmax(0,1fr) auto}}
.donusum{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.donusum div{border:1px solid var(--cizgi);border-radius:10px;padding:10px 12px}
.donusum span{display:block;font-size:12.5px;color:var(--soluk)}
.donusum strong{font-size:22px;font-variant-numeric:tabular-nums}
.akis{font-size:13.5px;max-height:520px;overflow:auto}
.akis div{display:grid;grid-template-columns:70px minmax(0,1fr);gap:10px;padding:5px 0;border-top:1px solid var(--cizgi)}
.akis div:first-child{border-top:0}
.akis time{color:var(--soluk);font-variant-numeric:tabular-nums}
.akis span{overflow-wrap:anywhere}
.hata-mesaj{color:var(--uyari)}
footer{margin-top:36px;color:var(--soluk);font-size:12.5px}
.sekmeler{display:flex;gap:4px;margin:-6px 0 18px;border-bottom:1px solid var(--cizgi)}
.sekmeler button{border:0;background:none;color:var(--soluk);font:inherit;font-weight:600;padding:8px 14px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
.sekmeler button[aria-selected=true]{color:var(--yazi);border-bottom-color:var(--ac)}
[hidden]{display:none!important}
/* Forum sekmesi renkleri colors.elwyn.co hazır kombinasyonlarından:
   açık tema #286 Burnt Sienna #ae5224 · Orange Yellow #fcb315 · Peacock Blue #00939b · Violet Blue #40456a
   koyu tema #300 Grenadine Pink #f48067 · Cream Yellow #fdbf68 · Turquoise Green #b5decc · Calamine Blue #78cdd0 */
.forum{--ac:#00939b;--ac-yumusak:color-mix(in srgb,#00939b 16%,transparent);--uyari:#ae5224;--s-soru:#00939b;--s-cevap:#40456a;--s-sohbet:#fcb315;--s-ozel:#ae5224}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .forum{--ac:#78cdd0;--ac-yumusak:color-mix(in srgb,#78cdd0 18%,transparent);--uyari:#f48067;--s-soru:#78cdd0;--s-cevap:#b5decc;--s-sohbet:#fdbf68;--s-ozel:#f48067}}
:root[data-theme=dark] .forum{--ac:#78cdd0;--ac-yumusak:color-mix(in srgb,#78cdd0 18%,transparent);--uyari:#f48067;--s-soru:#78cdd0;--s-cevap:#b5decc;--s-sohbet:#fdbf68;--s-ozel:#f48067}
.forum .kpi strong.uyar{color:var(--uyari)}
.oneri{margin:0;padding:0;list-style:none;display:grid;gap:8px}
.oneri li{display:grid;grid-template-columns:10px minmax(0,1fr);gap:10px;align-items:baseline;font-size:14.5px}
.oneri li::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--ac);transform:translateY(-1px)}
.oneri li.uyari::before{background:var(--uyari)}
.lejant{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12.5px;color:var(--soluk);margin:0 0 8px}
.lejant i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.grafik .s-soru{fill:var(--s-soru)}.grafik .s-cevap{fill:var(--s-cevap)}.grafik .s-sohbet{fill:var(--s-sohbet)}.grafik .s-ozel{fill:var(--s-ozel)}
.s-soru-b{background:var(--s-soru)}.s-cevap-b{background:var(--s-cevap)}.s-sohbet-b{background:var(--s-sohbet)}.s-ozel-b{background:var(--s-ozel)}
.grafik .cubuk-s{fill:var(--ac)}
.satir .det{grid-column:1/-1;font-size:12.5px;color:var(--soluk);overflow-wrap:anywhere}
.satir a{color:inherit}
.rozet{font-size:11px;border:1px solid var(--cizgi);border-radius:6px;padding:0 5px;margin-left:6px;color:var(--soluk)}
.donusum strong.uyar{color:var(--uyari)}
`;

const GIRIS_CSS = String.raw`
.giris{max-width:360px;margin:12vh auto 0;background:var(--kart);border:1px solid var(--cizgi);border-radius:14px;padding:26px;box-shadow:var(--golge)}
.giris h1{font-size:19px;margin:0 0 4px}
.giris p{color:var(--soluk);margin:0 0 16px;font-size:14px}
.giris input{width:100%;padding:10px 12px;border:1px solid var(--cizgi);border-radius:9px;background:var(--zemin);color:var(--yazi);font:inherit}
.giris button{width:100%;margin-top:12px;padding:10px;border:0;border-radius:9px;background:var(--ac);color:#fff;font:inherit;font-weight:600;cursor:pointer}
.hata{color:var(--uyari);font-size:14px;margin:0 0 12px}
`;

const kafa = (baslik, css, nonce = '') => `<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="color-scheme" content="light dark"><title>${esc(baslik)}</title><style${nonce ? ` nonce="${nonce}"` : ''}>${TEMEL_CSS}${css}</style></head>`;

export function girisSayfasi(mesaj = '') {
  return kafa('Site analizi - giriş', GIRIS_CSS) + `<body><main class="giris"><h1>KPSS Tercihi · Site analizi</h1><p>Yönetici anahtarını gir.</p>${mesaj ? `<p class="hata" role="alert">${esc(mesaj)}</p>` : ''}<form method="post" action="/panel/giris"><input type="password" name="anahtar" autocomplete="current-password" aria-label="Yönetici anahtarı" autofocus required><button type="submit">Giriş</button></form></main></body></html>`;
}

const ISTEMCI = String.raw`
(function(){
'use strict';
var $=function(id){return document.getElementById(id)};
function h(tag,cls,text){var n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n}
function svg(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(var k in attrs)n.setAttribute(k,attrs[k]);return n}
var tr=function(n){return Number(n||0).toLocaleString('tr-TR')};
var yuzde=function(x){return (x*100).toFixed(x<0.1&&x>0?1:0).replace('.',',')+'%'};
function sure(sn){sn=Math.round(sn||0);if(sn<60)return sn+' sn';var d=Math.floor(sn/60),s=sn%60;if(d<60)return d+' dk'+(s?' '+s+' sn':'');return Math.floor(d/60)+' sa '+(d%60)+' dk'}
function gunKisa(g){var p=g.split('-');return Number(p[2])+'.'+p[1]}
var GUNAD=['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'];
var EYLEM={manset_tikla:'Manşet tıklaması',manset_nokta:'Manşet noktası',manset_ok:'Manşet oku',satir_tikla:'İlan satırı',kurum_tikla:'Kurum bağlantısı',kategori:'Kategori seçimi',filtre:'Filtre değişimi',arama:'Arama',daha_fazla:'Daha fazla göster',kaydet:'İlan kaydedildi',kaydi_sil:'Kayıt kaldırıldı',takvim_ics:'Takvim indirme (.ics)',telegram:'Telegram bağlantısı',resmi_ilan:'Resmî ilana git',profil_kaydet:'Profil kaydı',robot:'Tercih robotu',tema:'Tema değiştirme',menu:'Menü',makale:'Rehber makalesi',arama_bildirim:'Sonuçsuz arama → Telegram haber al',arama_gecmis:'Sonuçsuz arama → geçmiş ilanlar',arama_cip:'Hızlı arama düğmesi',arama_taban:'Sonuçsuz arama → taban puanları','katip-basla':'Katiplik: deneme başlatıldı','katip-bitti':'Katiplik: deneme bitti','katip-mod':'Katiplik: mod seçimi','katip-kutuphane':'Katiplik: kütüphane seçimi','katip-ders':'Katiplik: ders açıldı','katip-ders-bitti':'Katiplik: ders tamamlandı','katip-antrenman':'Katiplik: antrenman başladı','katip-antrenman-bitti':'Katiplik: antrenman bitti','katip-oyun':'Katiplik: oyun başladı','katip-oyun-bitti':'Katiplik: oyun bitti','katip-kart':'Katiplik: sonuç kartı','katip-yol':'Katiplik: yol haritası',katiplik:'Katiplik düğmesi'};
var GORUNUM={bugun:'Manşet',ilanlar:'İlanlar',takvim:'Takvim',kayitli:'Kayıtlı',rehber:'Rehber',ilan:'İlan penceresi',makale:'Bilgi / rehber makalesi',karsilastir:'Karşılaştırma'};
function eylem(a){return EYLEM[a]||a}

function bosKart(kap,mesaj){kap.appendChild(h('p','bos',mesaj||'Henüz veri yok.'))}
/* Yatay çubuk listesi: en büyük değere göre ölçeklenir. */
function cubuklar(kap,satirlar,o){
  o=o||{};
  if(!satirlar.length){bosKart(kap,o.bos);return}
  var en=Math.max.apply(null,satirlar.map(function(r){return r.v}))||1;
  satirlar.forEach(function(r){
    var s=h('div','satir'),ad=h('div','ad',r.ad);if(r.alt){ad.appendChild(h('small',null,' '+r.alt))}
    ad.title=r.ad+(r.alt?' '+r.alt:'');
    var sy=h('div','say',r.yazi||tr(r.v));if(r.ek)sy.appendChild(h('small',null,r.ek));
    var c=h('div','cubuk'+(o.uyari?' uyari':'')),i=h('i');i.style.width=Math.max(2,Math.round(r.v/en*100))+'%';c.appendChild(i);
    s.appendChild(ad);s.appendChild(sy);s.appendChild(c);kap.appendChild(s)})
}
function kart(ust,baslik,alt,gen){var k=h('section','kart'),b=h('h3',null,baslik);if(alt)b.appendChild(h('small',null,alt));k.appendChild(b);ust.appendChild(k);return k}
function bolum(kok,baslik){kok.appendChild(h('h2','bolum',baslik));var g=h('div','izgara');kok.appendChild(g);return g}
function ilanAd(r){return r.ad||r.k}

function cizgiGrafik(kap,gunler,o){
  o=o||{};var al=o.alan||'ziyaretci';
  if(gunler.length<2){bosKart(kap,'Çizgi grafik için en az iki gün gerekir; 7 gün seç.');return}
  var W=720,H=220,L=36,R=10,T=10,B=26,en=Math.max.apply(null,gunler.map(function(g){return g[al]}))||1;
  var yu=en<=5?5:Math.ceil(en/4)*4;
  var s=svg('svg',{viewBox:'0 0 '+W+' '+H,'class':'grafik',role:'img','aria-label':o.ad||'Günlük tekil ziyaretçi sayısı'});
  [0,.5,1].forEach(function(f){var y=T+(H-T-B)*(1-f);s.appendChild(svg('line',{x1:L,x2:W-R,y1:y,y2:y,'class':'izgara-cizgi'}));var t=svg('text',{x:L-6,y:y+4,'text-anchor':'end'});t.textContent=tr(Math.round(yu*f));s.appendChild(t)});
  var n=gunler.length,xs=function(i){return L+(W-L-R)*(n===1?.5:i/(n-1))},ys=function(v){return T+(H-T-B)*(1-v/yu)};
  var nok=gunler.map(function(g,i){return xs(i)+','+ys(g[al])});
  s.appendChild(svg('polygon',{points:xs(0)+','+(H-B)+' '+nok.join(' ')+' '+xs(n-1)+','+(H-B),'class':'alan'}));
  s.appendChild(svg('polyline',{points:nok.join(' '),'class':'hat'}));
  var adim=Math.max(1,Math.ceil(n/7));
  gunler.forEach(function(g,i){
    if(n<=31){var c=svg('circle',{cx:xs(i),cy:ys(g[al]),r:n<=14?4:3,'class':'nokta-g'});var t=svg('title',{});t.textContent=o.ipucu?gunKisa(g.gun)+': '+tr(g[al])+' '+o.ipucu:gunKisa(g.gun)+': '+tr(g.ziyaretci)+' tekil ziyaretçi, '+tr(g.sayfa)+' görüntüleme';c.appendChild(t);s.appendChild(c)}
    if(i%adim===0||i===n-1){var x=svg('text',{x:xs(i),y:H-8,'text-anchor':'middle'});x.textContent=gunKisa(g.gun);s.appendChild(x)}});
  kap.appendChild(s)
}
/* Forum sekmesi: /panel/forum-analiz?gun= (sunucu forum Worker'ından çeker; anahtar tarayıcıya gelmez). Kullanıcı metinleri yalnız textContent ile yazılır. */
var forumGun=30,forumYuklendi=false,siteYuklendi=false;
var FORUM_DURUM={anahtar_yok:'Forum anahtarı tanımlı değil. FORUM_YONETICI_ANAHTARI sırrını ekle.',yetkisiz:'Forum anahtarı uyuşmuyor. FORUM_YONETICI_ANAHTARI, forumdaki YONETICI_ANAHTARI ile aynı olmalı.',hata:'Foruma ulaşılamadı. Biraz sonra yeniden dene.'};
var SERI=[['soru','Soru'],['cevap','Cevap'],['sohbet','Sohbet'],['ozel','Özel mesaj']];
function iki(n){return (n<10?'0':'')+n}
function forumBag(r){var a=h('a',null,r.baslik);a.href='https://kpsstercihi.com/forum/?b='+encodeURIComponent(r.id);a.target='_blank';a.rel='noopener noreferrer';return a}
function satirDet(kap,ad,say,det){
  var s=h('div','satir'),a=h('div','ad');if(typeof ad==='string')a.textContent=ad;else a.appendChild(ad);a.title=a.textContent;
  s.appendChild(a);s.appendChild(h('div','say',say));if(det)s.appendChild(h('div','det',det));kap.appendChild(s);return a
}
function kutular(kap,liste){var d=h('div','donusum');liste.forEach(function(a){var x=h('div');x.appendChild(h('span',null,a[0]));x.appendChild(h('strong',a[2]?'uyar':null,tr(a[1])));d.appendChild(x)});kap.appendChild(d)}
/* Yığılmış günlük çubuk: soru (ilan sorusu dahil), cevap, sohbet, özel mesaj. */
function yiginGrafik(kap,seri){
  var veri=seri.map(function(g){return {gun:g.gun,soru:g.soru+g.ilan_soru,cevap:g.cevap,sohbet:g.sohbet,ozel:g.ozel}});
  var lj=h('p','lejant');
  SERI.forEach(function(sr){var top=veri.reduce(function(x,r){return x+r[sr[0]]},0),sp=h('span');sp.appendChild(h('i','s-'+sr[0]+'-b'));sp.appendChild(document.createTextNode(sr[1]+' '+tr(top)));lj.appendChild(sp)});
  kap.appendChild(lj);
  var W=720,H=220,L=36,R=6,T=10,B=26,n=veri.length,en=Math.max.apply(null,veri.map(function(r){return r.soru+r.cevap+r.sohbet+r.ozel}))||1;
  var yu=en<=5?5:Math.ceil(en/4)*4,bw=(W-L-R)/n,pay=Math.min(2,bw*.15);
  var s=svg('svg',{viewBox:'0 0 '+W+' '+H,'class':'grafik',role:'img','aria-label':'Günlük forum etkinliği: soru, cevap, sohbet, özel mesaj'});
  [0,.5,1].forEach(function(f){var y=T+(H-T-B)*(1-f);s.appendChild(svg('line',{x1:L,x2:W-R,y1:y,y2:y,'class':'izgara-cizgi'}));var t=svg('text',{x:L-6,y:y+4,'text-anchor':'end'});t.textContent=tr(Math.round(yu*f));s.appendChild(t)});
  var adim=Math.max(1,Math.ceil(n/7));
  veri.forEach(function(r,i){
    var gr=svg('g',{}),y=H-B;
    gr.appendChild(svg('rect',{x:L+i*bw,y:T,width:bw,height:H-T-B,fill:'transparent'}));
    SERI.forEach(function(sr){var v=r[sr[0]];if(!v)return;var hh=(H-T-B)*v/yu;y-=hh;gr.appendChild(svg('rect',{x:L+i*bw+pay,y:y,width:Math.max(1,bw-2*pay),height:hh,'class':'s-'+sr[0]}))});
    var ti=svg('title',{});ti.textContent=gunKisa(r.gun)+': '+SERI.map(function(sr){return tr(r[sr[0]])+' '+sr[1].toLocaleLowerCase('tr-TR')}).join(', ');gr.appendChild(ti);
    s.appendChild(gr);
    if(i%adim===0||i===n-1){var t=svg('text',{x:L+i*bw+bw/2,y:H-8,'text-anchor':'middle'});t.textContent=gunKisa(r.gun);s.appendChild(t)}});
  kap.appendChild(s)
}
/* Günün saatine göre yazı sayısı (Türkiye saati); en yoğun saat tam renkli. */
function saatGrafik(kap,saat){
  var top=saat.reduce(function(x,y){return x+y},0);
  if(!top){bosKart(kap,'Bu dönemde yazı yok.');return}
  var W=720,H=180,L=36,R=6,T=10,B=24,en=Math.max.apply(null,saat)||1,bw=(W-L-R)/24,enS=saat.indexOf(en);
  var s=svg('svg',{viewBox:'0 0 '+W+' '+H,'class':'grafik',role:'img','aria-label':'Günün saatine göre yazı sayısı'});
  [0,1].forEach(function(f){var y=T+(H-T-B)*(1-f);s.appendChild(svg('line',{x1:L,x2:W-R,y1:y,y2:y,'class':'izgara-cizgi'}));var t=svg('text',{x:L-6,y:y+4,'text-anchor':'end'});t.textContent=tr(Math.round(en*f));s.appendChild(t)});
  saat.forEach(function(v,i){
    var hh=(H-T-B)*v/en,r=svg('rect',{x:L+i*bw+2,y:H-B-hh,width:bw-4,height:hh,rx:2,'class':'cubuk-s'});
    if(i!==enS)r.setAttribute('fill-opacity','.5');
    var ti=svg('title',{});ti.textContent=iki(i)+':00 — '+tr(v)+' yazı';r.appendChild(ti);s.appendChild(r);
    if(i%3===0){var t=svg('text',{x:L+i*bw+bw/2,y:H-8,'text-anchor':'middle'});t.textContent=iki(i);s.appendChild(t)}});
  kap.appendChild(s);
  kap.appendChild(h('p','not','Türkiye saati. En yoğun: '+iki(enS)+':00–'+iki((enS+1)%24)+':00 ('+tr(en)+' yazı).'))
}
// Tüm üyeler: rumuz araması ve sütuna tıklayınca sıralama. Rumuz forumdaki herkese açık profile bağlanır.
function uyeTablosu(kok,liste,toplam){
  var g=bolum(kok,'Tüm üyeler');g.className='izgara genis';
  var c=kart(g,'Üye listesi',tr(liste.length)+(toplam>liste.length?' / '+tr(toplam)+' (en yeni '+tr(liste.length)+')':' üye'));
  if(!liste.length){bosKart(c,'Henüz üye yok.');return}
  var ara=h('input','uye-ara');ara.type='search';ara.placeholder='Rumuz ara';ara.setAttribute('aria-label','Rumuz ara');c.appendChild(ara);
  var kap=h('div','uye-tablo'),tb=h('table'),bas=h('thead'),gv=h('tbody');tb.appendChild(bas);tb.appendChild(gv);kap.appendChild(tb);c.appendChild(kap);
  var tarih=function(sn){return sn?new Date(sn*1000).toLocaleDateString('tr-TR',{timeZone:'Europe/Istanbul',day:'numeric',month:'short',year:'2-digit'}):'—'};
  var once=function(sn){if(!sn)return 'hiç yazmadı';var d=Math.floor((Date.now()/1000-sn)/86400);return d<=0?'bugün':d===1?'dün':tr(d)+' gün önce'};
  var sut=[['rumuz','Rumuz'],['kayit','Katıldı'],['son','Son yazı'],['yol','Giriş'],['soru','Soru',1],['cevap','Cevap',1],['sohbet','Sohbet',1],['itibar','İtibar',1]];
  var sira={k:'kayit',ters:true},tr1=h('tr');
  sut.forEach(function(s){var th=h('th',s[2]?'sayi':null,s[1]);th.setAttribute('scope','col');th.onclick=function(){sira.ters=sira.k===s[0]?!sira.ters:s[0]!=='rumuz';sira.k=s[0];ciz()};tr1.appendChild(th)});
  bas.appendChild(tr1);
  function ciz(){
    var q=ara.value.trim().toLocaleLowerCase('tr');
    var l=liste.filter(function(u){return !q||String(u.rumuz).toLocaleLowerCase('tr').indexOf(q)>=0});
    l.sort(function(a,b){var x=a[sira.k],y=b[sira.k];if(sira.k==='yol'){x=x.join(',');y=y.join(',')}
      var r=typeof x==='string'?x.localeCompare(y,'tr'):(x||0)-(y||0);return sira.ters?-r:r});
    gv.replaceChildren();
    l.forEach(function(u){
      var tr2=h('tr'),td=h('td'),a=h('a',null,u.rumuz);a.href='https://kpsstercihi.com/forum/?uye='+encodeURIComponent(u.rumuz);a.target='_blank';a.rel='noopener';td.appendChild(a);
      if(u.kurucu)td.appendChild(h('span','rozet','kurucu'));if(u.engelli)td.appendChild(h('span','rozet','engelli'));tr2.appendChild(td);
      tr2.appendChild(h('td',null,tarih(u.kayit)));tr2.appendChild(h('td',null,once(u.son)));tr2.appendChild(h('td',null,u.yol.join(', ')||'—'));
      ['soru','cevap','sohbet','itibar'].forEach(function(k){tr2.appendChild(h('td','sayi',tr(u[k])))});
      gv.appendChild(tr2)});
    if(!l.length){var b=h('tr'),t=h('td',null,'Eşleşen rumuz yok.');t.colSpan=sut.length;b.appendChild(t);gv.appendChild(b)}
  }
  ara.oninput=ciz;ciz();
}
function forumCiz(F){
  var kok=$('forum-icerik');kok.replaceChildren();
  if(!F||F.durum!=='tamam'){var d=F&&F.durum;kok.appendChild(h('p',d==='anahtar_yok'?'bos':'bos hata-mesaj',FORUM_DURUM[d]||FORUM_DURUM.hata));return}
  var V=F.veri,U=V.uyeler,A=V.aktif,S=V.soru,Hn=V.huni,D=V.denetim,E=V.etkilesim,c,g,donem='son '+V.gun+' gün';
  var bek=D.sikayet+D.ozel_sikayet+D.foto_bildirim;
  g=h('div','izgara genis');kok.appendChild(g);
  c=kart(g,'Ne yapmalı?',donem);var ul=h('ul','oneri');(F.oneriler||[]).forEach(function(o){ul.appendChild(h('li',o.tur==='uyari'?'uyari':null,o.metin))});c.appendChild(ul);
  var kp=h('div','kpi');kp.style.marginTop='12px';kok.appendChild(kp);
  [['Üye',tr(U.toplam),'+'+tr(U.yeni)+' bu dönemde · '+tr(U.son.g1)+' son 24 sa'],
   ['Aktif yazan (7 gün)',tr(A.g7),tr(A.g1)+' son 24 sa · '+tr(A.g30)+' son 30 gün'],
   ['Geri dönen',A.donem?yuzde(A.geri_donen/A.donem):'—',tr(A.geri_donen)+' / '+tr(A.donem)+' yazan, 2+ farklı gün'],
   ['Soru',tr(S.donem),S.donem?yuzde(S.cevaplanan/S.donem)+' cevap aldı':'bu dönemde soru yok'],
   ['İlk cevap (medyan)',S.ilk_cevap_medyan_dk==null?'—':sure(S.ilk_cevap_medyan_dk*60),S.cevaplanan?tr(S.bir_saatte)+' soru 1 saat içinde cevaplandı':''],
   ['Cevapsız soru',tr(S.cevapsiz),'tüm zamanlar',S.cevapsiz>0],
   ['Bekleyen şikâyet',tr(bek),tr(D.sikayet)+' yazı · '+tr(D.ozel_sikayet)+' özel · '+tr(D.foto_bildirim)+' fotoğraf',bek>0]].forEach(function(a){
    var x=h('div');x.appendChild(h('span',null,a[0]));x.appendChild(h('strong',a[3]?'uyar':null,a[1]));x.appendChild(h('em',null,a[2]));kp.appendChild(x)});

  g=bolum(kok,'Günlük');g.className='izgara genis';
  c=kart(g,'Günlük etkinlik',donem+' · yazı');yiginGrafik(c,V.seri);
  c=kart(g,'Yeni üye',donem+' · toplam '+tr(V.toplam.uye));cizgiGrafik(c,V.seri,{alan:'uye',ad:'Günlük yeni üye',ipucu:'yeni üye'});
  c.appendChild(h('p','not','Bu dönemde '+tr(V.toplam.takip)+' takip, '+tr(V.toplam.anket)+' yeni anket.'));

  g=bolum(kok,'Sorular');
  c=kart(g,'Cevapsız sorular','en eskiden');
  if(!S.cevapsiz_liste.length)bosKart(c,'Cevapsız soru yok.');
  else S.cevapsiz_liste.forEach(function(r){satirDet(c,forumBag(r),r.gun===0?'bugün':tr(r.gun)+' gün',r.kategori)});
  if(S.cevapsiz>S.cevapsiz_liste.length)c.appendChild(h('p','not','Toplam '+tr(S.cevapsiz)+' cevapsız soru; en eski '+S.cevapsiz_liste.length+' tanesi görünüyor.'));
  c=kart(g,'En çok ilgi gören sorular',donem);
  if(!S.en_iyi.length)bosKart(c,'Bu dönemde cevap ya da oy alan soru yok.');
  else S.en_iyi.forEach(function(r){satirDet(c,forumBag(r),tr(r.cevap)+' cevap',tr(r.faydali)+' faydalı · '+tr(r.takip)+' takip · '+r.kategori)});
  c=kart(g,'Kategoriye göre',donem+' · soru');cubuklar(c,S.kategori.map(function(r){return {ad:r.ad,v:r.n,ek:yuzde(r.n?r.cevaplanan/r.n:0)+' cevaplı'}}),{bos:'Bu dönemde soru yok.'});
  c=kart(g,'İlan sayfasından gelen sorular',donem);kutular(c,[['Soru',S.ilan.n],['Üye cevabı alan',S.ilan.insan],['Asistan cevabı alan',S.ilan.asistan]]);

  g=bolum(kok,'Odalar ve saatler');
  c=kart(g,'Sohbet odaları',donem+' · mesaj');cubuklar(c,V.odalar.map(function(r){return {ad:r.ad,v:r.mesaj,ek:tr(r.kisi)+' kişi'}}),{bos:'Sohbet odası yok.'});
  c=kart(g,'Hangi saatte yazıyorlar',donem);saatGrafik(c,V.saat);
  c=kart(g,'Gün ve saat',donem+' · yazı');isiHaritasi(c,V.isi,'yazı');

  g=bolum(kok,'Üyeler');
  c=kart(g,'En çok katkı',donem);
  if(!V.katkilar.length)bosKart(c,'Bu dönemde yazan yok.');
  else V.katkilar.forEach(function(k){var a=satirDet(c,k.rumuz,tr(k.soru+k.cevap)+' yazı',tr(k.soru)+' soru · '+tr(k.cevap)+' cevap · '+tr(k.sohbet)+' sohbet · itibar '+tr(k.itibar));if(k.kurucu)a.appendChild(h('span','rozet','kurucu'))});
  c=kart(g,'Üyeler ne yapıyor','tüm üyeler');
  var w=h('div','huni'),hen=Math.max(Hn.toplam,1);
  [['Üye',Hn.toplam],['Yazı yazdı',Hn.yazan],['Yalnız oy, takip, mesaj',Hn.yalniz_etkilesim],['Yalnız okuyor',Hn.iz_yok]].forEach(function(a,i){
    var s=h('div','huni-adim');s.appendChild(h('span',null,a[0]));
    var cb=h('div','cubuk'),b=h('i');b.style.width=Math.max(a[1]?2:0,Math.round(a[1]/hen*100))+'%';cb.appendChild(b);s.appendChild(cb);
    s.appendChild(h('span','say',tr(a[1])+(i&&Hn.toplam?' · '+yuzde(a[1]/Hn.toplam):'')));w.appendChild(s)});
  c.appendChild(w);
  c.appendChild(h('p','not','Bu dönemde katılan '+tr(Hn.yeni)+' üyeden '+tr(Hn.yeni_yazan)+' tanesi yazı yazdı.'));
  c=kart(g,'Giriş yöntemi','bir üyede birden çok olabilir');cubuklar(c,[{ad:'Google',v:U.yontem.google},{ad:'E-posta',v:U.yontem.eposta},{ad:'Telegram',v:U.yontem.telegram},{ad:'Rumuz + şifre',v:U.yontem.sifre}],{bos:'Üye yok.'});
  c.appendChild(h('p','not',tr(U.kurucu)+' kurucu · '+tr(U.fotolu)+' fotoğraflı · '+tr(U.kartli)+' profil kartı dolu · '+tr(U.silinen)+' silinen hesap.'));

  uyeTablosu(kok,V.uye_listesi||[],U.toplam);

  g=bolum(kok,'Etkileşim ve denetim');
  c=kart(g,'Etkileşim','tüm zamanlar');kutular(c,[['Faydalı (cevap)',E.yanit_oy],['Faydalı (soru)',E.baslik_oy],['Anket',E.anket],['Anket oyu',E.anket_oy],['Takip',E.takip]]);
  c=kart(g,'Denetim');kutular(c,[['Yazı şikâyeti',D.sikayet,D.sikayet>0],['Özel mesaj şikâyeti',D.ozel_sikayet,D.ozel_sikayet>0],['Bildirilen fotoğraf',D.foto_bildirim,D.foto_bildirim>0],['Gizlenen yazı',D.gizlenen],['Engelleme',D.engel],['Engelli üye',D.engelli],['Kapatılan kimlik',D.kapali_kimlik]]);
  c.appendChild(h('p','not','Şikâyetler bekleyenlerdir. Gizlenen yazı ve engelleme bu dönemdendir.'));
  kok.appendChild(h('footer',null,'Veri '+new Date(V.uretildi*1000).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'})+' itibarıyla, en çok 5 dakika gecikir. Özel mesaj metni ve e-posta adresi panele gelmez.'))
}
function forumYukle(gun){
  forumGun=gun;forumYuklendi=true;
  document.querySelectorAll('#forum-aralik button').forEach(function(b){b.setAttribute('aria-pressed',String(Number(b.dataset.g)===gun))});
  $('forum-icerik').replaceChildren(h('p','bos','Forum verisi yükleniyor…'));
  fetch('/panel/forum-analiz?gun='+gun,{credentials:'same-origin'}).then(function(r){if(r.status===401){location.href='/panel';throw 0}if(!r.ok)throw new Error(r.status);return r.json()}).then(forumCiz).catch(function(e){if(e!==0)forumCiz({durum:'hata'})})
}
function sekmeAc(ad){
  var forum=ad==='forum';
  $('sekme-site').setAttribute('aria-selected',String(!forum));$('sekme-forum').setAttribute('aria-selected',String(forum));
  $('icerik').hidden=forum;$('forum-icerik').hidden=!forum;$('site-aralik').hidden=forum;$('forum-aralik').hidden=!forum;
  if(forum){try{history.replaceState(null,'','?sekme=forum')}catch(e){}if(!forumYuklendi)forumYukle(forumGun)}
  else if(!siteYuklendi){var q=new URLSearchParams(location.search).get('aralik');yukle(['bugun','7g','30g','90g'].indexOf(q)>=0?q:aralik)}
  else{try{history.replaceState(null,'','?aralik='+aralik)}catch(e){}}
}
function isiHaritasi(kap,isi,birim){
  birim=birim||'görüntüleme';
  if(!isi.length){bosKart(kap);return}
  var m={},en=1;isi.forEach(function(r){m[r[0]+'-'+r[1]]=r[2];if(r[2]>en)en=r[2]});
  var W=720,L=34,hw=(W-L-4)/24,hh=20,H=7*hh+26;
  var s=svg('svg',{viewBox:'0 0 '+W+' '+H,'class':'grafik',role:'img','aria-label':'Haftanın günü ve saate göre '+birim});
  for(var g=0;g<7;g++){
    var t=svg('text',{x:L-6,y:g*hh+hh*.7,'text-anchor':'end'});t.textContent=GUNAD[g];s.appendChild(t);
    for(var sa=0;sa<24;sa++){
      var v=m[g+'-'+sa]||0,r=svg('rect',{x:L+sa*hw+1,y:g*hh+1,width:hw-2,height:hh-2,rx:3,'class':v?'hucre':'hucre-bos'});
      if(v)r.setAttribute('fill-opacity',(0.18+0.82*v/en).toFixed(2));
      var ti=svg('title',{});ti.textContent=GUNAD[g]+' '+(sa<10?'0':'')+sa+':00 — '+tr(v)+' '+birim;r.appendChild(ti);s.appendChild(r)}}
  [0,3,6,9,12,15,18,21].forEach(function(sa){var t=svg('text',{x:L+sa*hw+hw/2,y:H-8,'text-anchor':'middle'});t.textContent=(sa<10?'0':'')+sa;s.appendChild(t)});
  kap.appendChild(s);kap.appendChild(h('p','not','Türkiye saati. Koyu hücre = daha çok '+(birim==='görüntüleme'?'sayfa görüntüleme':birim)+'.'))
}
function huni(kap,hn){
  var adimlar=[['Oturum',hn.oturum],['Ana sayfayı gördü',hn.ana],['İlan ayrıntısı açtı',hn.ilan],['Ana sayfa → ilan',hn.anaIlan],['Resmî ilana gitti',hn.resmi]];
  var en=Math.max(hn.oturum,1),w=h('div','huni');
  adimlar.forEach(function(a,i){
    var s=h('div','huni-adim');s.appendChild(h('span',null,a[0]));
    var c=h('div','cubuk'),b=h('i');b.style.width=Math.max(a[1]?2:0,Math.round(a[1]/en*100))+'%';c.appendChild(b);s.appendChild(c);
    s.appendChild(h('span','say',tr(a[1])+(i&&hn.oturum?' · '+yuzde(a[1]/hn.oturum):'')));w.appendChild(s)});
  kap.appendChild(w);
  var oran=hn.ilan?hn.ilanResmi/hn.ilan:0;
  kap.appendChild(h('p','not','İlan açan oturumların '+yuzde(oran)+'’i resmî ilana gitti ('+tr(hn.ilanResmi)+' oturum). Adımlar oturum bazındadır; aynı oturum birden çok adımda sayılır.'))
}
function olayYazi(o){
  var sf=function(){return o.v?(GORUNUM[o.v]||o.v):(o.k?o.k:o.p)};
  switch(o.t){
    case 'sayfa':return 'Sayfa: '+(o.sy==='ana'?'Ana sayfa · '+sf():o.p)+(o.kaynak?' · '+o.kaynak:'')+(o.sehir?' · '+o.sehir:'')+(o.cihaz?' · '+o.cihaz:'');
    case 'aktif':return 'Sayfada vakit geçirdi: +'+o.n+' sn · '+sf();
    case 'tikla':
      if(o.a==='arama')return 'Arama: "'+(o.x||'')+'" · '+tr(o.n)+' sonuç';
      return eylem(o.a)+(o.h?' · '+o.h:'')+(o.x?' · '+o.x:'')+(o.n!=null?' · '+o.n:'');
    case 'kaydirma':return '%'+o.n+' kaydırdı · '+o.p;
    case 'hata':return 'JS hatası: '+o.x;
    case '404':return '404 bulunamadı: '+(o.x||o.p);
    case 'hiz':return 'Sayfa hızı: LCP '+(o.n||'—')+' ms, TTFB '+(o.n2||'—')+' ms';
    default:return o.t}
}
function akisCiz(kap,akis){
  kap.replaceChildren();
  if(!akis.length){bosKart(kap,'Henüz olay yok.');return}
  var w=h('div','akis');
  akis.forEach(function(o){var d=h('div'),z=h('time',null,new Date(o.ts*1000).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul'}));d.appendChild(z);d.appendChild(h('span',o.t==='hata'?'hata-mesaj':'',olayYazi(o)));w.appendChild(d)});
  kap.appendChild(w)
}

/* Katiplik bölümü: ziyaret, süre, sınav hunisi, sonuçlar ve araç kullanımı. Ad eşlemeleri sitedeki data-a / A() değerleridir. */
var KATIP_MOD={sinav:'Sınav simülasyonu',gunluk:'Günün metni',antrenman:'Serbest antrenman',hatali:'Hatalı kelimeler',isinma:'Isınma',ozel:'Kendi metni'};
var KATIP_SAYFA={'/katiplik/':'Sınav (ana)','/katiplik/dersler/':'Dersler','/katiplik/antrenman/':'Kelime antrenmanı','/katiplik/oyunlar/':'Oyunlar','/katiplik/sinav-metinleri/':'Sınav metinleri (dizin)','/katiplik/degerlendirme-kriterleri/':'Değerlendirme kriterleri','/katiplik/klavye-sinavi-rehberi/':'Sınav rehberi'};
function katipSayfa(p){var m=p.match(/^\/katiplik\/sinav-metinleri\/metin-(\d+)\/$/);return m?'Resmî metin '+m[1]:(KATIP_SAYFA[p]||p)}
var KATIP_KUT={zk2025:'ZK 2025 (resmî)',ozgun:'Özgün metinler',tck:'TCK',cmk:'CMK',hmk:'HMK',iik:'İİK',tmk:'TMK',tbk:'TBK',anayasa:'Anayasa',iyuk:'İYUK',dmk:'DMK'};
var KATIP_ANT={hiz:'Hız testi',zayif:'Zayıf tuşlar',hedef200:'Sık 200 kelime',hedef500:'Sık 500 kelime',uzun:'Uzun kelimeler',terim:'Hukuk terimleri',rakam:'Rakam ve sayı'};
function katipMod(x){var m=String(x).replace(/-(basarili|basarisiz)$/,'');if(/^sinav-/.test(m))return 'Sınav · '+(KATIP_KUT[m.slice(6)]||m.slice(6));return KATIP_MOD[m]||m}
function katiplikCiz(kok,K){
  var k=K.kpi,kp=h('div','kpi');
  kok.appendChild(h('h2','bolum','Katiplik'));
  [['Sayfa görüntüleme',tr(k.goruntu),tr(k.girisOturum)+' oturum katiplikle başladı'],['Etkin süre',sure(k.sureSn),k.goruntu?sure(k.sureSn/k.goruntu)+' / görüntüleme':''],
   ['Başlatılan deneme',tr(k.basla),k.basla?yuzde(k.bitti/k.basla)+' tamamlandı ('+tr(k.bitti)+')':'henüz yok'],['Sınav başarısı',k.bitenSinav?yuzde(k.basariOran):'—',tr(k.bitenSinav)+' sınav · ort. '+k.ortNet+' net'],
   ['Menüden tıklama',tr(k.menu),'“Katiplik · Yeni” sekmesi'],['Paylaşım',tr(k.paylasim),tr(K.paylasimGelen)+' oturum paylaşımdan geldi']].forEach(function(a){
    var c=h('div');c.appendChild(h('span',null,a[0]));c.appendChild(h('strong',null,a[1]));c.appendChild(h('em',null,a[2]));kp.appendChild(c)});
  kok.appendChild(kp);
  var g=h('div','izgara'),c;kok.appendChild(g);
  c=kart(g,'Katiplik sayfaları','görüntüleme · ortalama etkin süre');cubuklar(c,K.sayfalar.map(function(r){return {ad:katipSayfa(r.p),v:r.say,ek:r.ortSn?sure(r.ortSn):''}}),{bos:'Katiplik sayfası henüz görüntülenmedi.'});
  c=kart(g,'Nereden geliyorlar','katiplik sayfasıyla başlayan oturum');cubuklar(c,K.kaynak.map(function(r){return {ad:r.ad,v:r.say}}),{bos:'Veri yok.'});
  c=kart(g,'Aramadan / dışarıdan giriş sayfası','oturumun ilk sayfası');cubuklar(c,K.girisSayfasi.map(function(r){return {ad:katipSayfa(r.ad),v:r.say}}),{bos:'Veri yok.'});
  c=kart(g,'Sınav sonuçları','net kelime aralığı · 3 dk sınav + günün metni');cubuklar(c,K.netDagilim.map(function(r){return {ad:r.ad+' net',v:r.say}}),{bos:'Biten sınav yok.'});
  c=kart(g,'Modlara göre sonuç','biten · başarı · ort. net');cubuklar(c,K.modlar.map(function(r){return {ad:katipMod(r.ad),v:r.say,ek:yuzde(r.basariOran)+' başarı · '+r.ortNet+' net'}}),{bos:'Biten deneme yok.'});
  c=kart(g,'Başlatılan denemeler','mod ve kütüphane');cubuklar(c,K.basla.map(function(r){return {ad:katipMod(r.ad),v:r.say}}),{bos:'Henüz deneme başlatılmadı.'});
  c=kart(g,'Kütüphane seçimi');cubuklar(c,K.kutuphane.map(function(r){return {ad:KATIP_KUT[r.ad]||r.ad,v:r.say}}),{bos:'Kütüphane değiştirilmedi (varsayılan: ZK 2025).'});
  c=kart(g,'Tamamlanan dersler','ders · ort. yıldız');cubuklar(c,K.dersler.map(function(r){return {ad:r.ad,v:r.say,ek:r.ort+'★'}}),{bos:'Tamamlanan ders yok ('+tr(K.dersAcilis)+' ders açıldı).'});
  c=kart(g,'Kelime antrenmanı','biten · ort. net/dk');cubuklar(c,K.antrenman.map(function(r){return {ad:KATIP_ANT[r.ad]||r.ad,v:r.say,ek:r.ort+' net/dk'}}),{bos:'Biten antrenman yok.'});
  c=kart(g,'Oyunlar','biten oyun · ort. puan');cubuklar(c,K.oyunlar.map(function(r){return {ad:r.ad==='dosya'?'Dosya Yetiştir':r.ad==='hata'?'Hata Avı':r.ad,v:r.say,ek:'ort. '+tr(r.ort)+' puan'}}),{bos:'Biten oyun yok.'});
  c=kart(g,'Katiplik düğmeleri','data-a="katiplik"');cubuklar(c,K.dugmeler.map(function(r){return {ad:r.ad,v:r.say}}),{bos:'Tıklama yok.'});
  c.appendChild(h('p','not','Yol haritasında sınav tarihi giren: '+tr(K.yolHaritasi)+'.'));
}
var aralik='7g',akisKap=null;
function canliGuncelle(){
  fetch('/panel/canli',{credentials:'same-origin'}).then(function(r){if(r.status===401){location.href='/panel';throw 0}return r.json()}).then(function(c){
    $('canli-sayi').textContent=tr(c.aktif);if(akisKap)akisCiz(akisKap,c.akis)}).catch(function(){})
}
function ciz(d){
  var kok=$('icerik');kok.replaceChildren();
  if(d.kota_korumasi){kok.appendChild(h('p','bos hata-mesaj','Kota koruması: günlük D1 okuma bütçesi doldu, veri yarın (UTC 00:00 sonrası) yeniden hesaplanır.'));return}
  var bt=d.butce;
  if(bt&&(bt.veriAzaltildi||bt.okumaKademesi>0)){
    var nt=[];
    if(bt.yazmaKademesi>=3)nt.push('Günlük yazma bütçesi doldu: bugün yeni olay toplanmıyor (UTC 00:00 sonrası devam eder).');
    else if(bt.veriAzaltildi)nt.push('Veri azaltıldı (yazma bütçesi: '+tr(bt.yazma)+' / '+tr(bt.sinirYazma)+'). Etkilenen ölçümler: '+bt.azaltilan.join(', ')+'.');
    if(bt.okumaKademesi>=1)nt.push('Okuma bütçesi '+(bt.okumaKademesi>=2?'doldu':'eşiği aştı')+': veriler önbellekten sunulur, güncel olmayabilir.');
    kok.appendChild(h('p','bos hata-mesaj',nt.join(' ')))
  }
  var k=d.kpi,yg=k.yeni+k.geri;
  if(k.erisim){
    // Kaç farklı kişiye ulaşıyoruz: cihaz bazında, dönem içinde tekrar sayılmadan (seçili aralıktan bağımsız).
    var E=k.erisim,eb=h('div','kpi');
    [['Bugün farklı kişi',tr(E.bugun),'bugün siteye giren'],['Bu hafta farklı kişi',tr(E.hafta),'pazartesiden beri'],['Bu ay farklı kişi',tr(E.ay),'ayın başından beri'],
     ['Toplam ulaşılan kişi',tr(E.toplam),E.baslangic?E.baslangic+' tarihinden beri':'ölçüm yeni başladı']].forEach(function(a){
      var c=h('div');c.appendChild(h('span',null,a[0]));c.appendChild(h('strong',null,a[1]));c.appendChild(h('em',null,a[2]));eb.appendChild(c)});
    kok.appendChild(h('h2','bolum','Kaç kişiye ulaşıyoruz'));kok.appendChild(eb);
  }
  var kp=h('div','kpi');
  [['Tekil ziyaretçi',tr(k.ziyaretci),d.aralik.adet>1?'günlük tekil sayıların toplamı':'bugün'],['Oturum',tr(k.oturum),''],['Sayfa görüntüleme',tr(k.sayfa),k.oturum?(k.sayfa/k.oturum).toFixed(1).replace('.',',')+' sayfa / oturum':''],
   ['Ort. etkin süre',sure(k.etkinSaniyeOrt),'oturum başına, sekme açık ve etkileşimliyken'],['Hemen çıkma',yuzde(k.hemenCikma),'tek sayfa, etkileşimsiz oturum'],
   ['Yeni / geri dönen',yg?yuzde(k.yeni/yg)+' / '+yuzde(k.geri/yg):'—',tr(k.yeni)+' yeni · '+tr(k.geri)+' geri dönen']].forEach(function(a){
    var c=h('div');c.appendChild(h('span',null,a[0]));c.appendChild(h('strong',null,a[1]));c.appendChild(h('em',null,a[2]));kp.appendChild(c)});
  kok.appendChild(kp);
  if(d.katiplik)katiplikCiz(kok,d.katiplik);

  var g,c,K=d.kayip;
  if(K){
    // Kayıp noktaları: hangi grupta ilgi düşük, tek sayfada çıkış yüksek. ilgi = ilana/kuruma/Telegram'a tıklayan oturum oranı.
    var kayipSatir=function(ad){return function(r){return {ad:ad?ad(r.ad):r.ad,v:r.oturum,yazi:tr(r.oturum),ek:(r.oturum?yuzde(r.ilgi/r.oturum):'—')+' ilgi · '+(r.oturum?yuzde(r.tekSayfa/r.oturum):'—')+' tek sayfa · '+sure(r.ortSn)}}};
    var ARAMA_AD={aramadi:'Arama yapmayan',sonuclu:'Arayıp sonuç bulan',bazen_sifir:'Bazen sonuçsuz kalan',hep_sifir:'Hep sonuçsuz kalan'};
    g=bolum(kok,'Kayıp noktaları');
    c=kart(g,'Aramaya göre oturumlar','oturum · ilgi · tek sayfa · süre');cubuklar(c,K.arama.map(kayipSatir(function(a){return ARAMA_AD[a]||a})),{bos:'Veri yok.'});
    var sz=K.sifirSonra.devam+K.sifirSonra.birakti;
    if(sz)c.appendChild(h('p',K.sifirSonra.birakti/sz>0.4?'not hata-mesaj':'not','Sonuçsuz aramadan sonra '+tr(K.sifirSonra.birakti)+' oturum ('+yuzde(K.sifirSonra.birakti/sz)+') hiçbir şeye tıklamadan bıraktı; '+tr(K.sifirSonra.devam)+' oturum devam etti.'));
    c=kart(g,'Cihaza göre','oturum · ilgi · tek sayfa · süre');cubuklar(c,K.cihaz.map(kayipSatir()),{bos:'Veri yok.'});
    c=kart(g,'Kaynağa göre','oturum · ilgi · tek sayfa · süre');cubuklar(c,K.kaynak.map(kayipSatir()),{bos:'Veri yok.'});
  }

  g=bolum(kok,'Zaman');g.className='izgara genis';
  c=kart(g,'Günlük tekil ziyaretçi');cizgiGrafik(c,d.gunler);
  c=kart(g,'Hangi gün, hangi saat','sayfa görüntüleme');isiHaritasi(c,d.isi);

  g=bolum(kok,'Nereden geliyorlar');
  c=kart(g,'Kaynak','oturum');cubuklar(c,d.kaynak.map(function(r){return {ad:r.ad,v:r.oturum,ek:''}}));
  c=kart(g,'Yönlendiren siteler');cubuklar(c,d.rhost.slice(0,12).map(function(r){return {ad:r.ad,v:r.oturum}}),{bos:'Yönlendiren site yok (hepsi doğrudan).'});
  c=kart(g,'Kampanyalar','utm');cubuklar(c,d.utm.map(function(r){return {ad:r.kaynak,alt:r.kampanya==='-'?'':r.kampanya,v:r.oturum}}),{bos:'utm_ etiketli bağlantı henüz kullanılmadı.'});
  c=kart(g,'Şehir');cubuklar(c,d.sehir.slice(0,15).map(function(r){return {ad:r.ad,alt:r.ulke&&r.ulke!=='TR'?r.ulke:'',v:r.oturum}}));
  c=kart(g,'Ülke');cubuklar(c,d.ulke.map(function(r){return {ad:r.ad,v:r.oturum}}));

  g=bolum(kok,'Cihaz');
  c=kart(g,'Cihaz türü');cubuklar(c,d.cihaz.map(function(r){return {ad:r.ad,v:r.oturum}}));
  c=kart(g,'Tarayıcı');cubuklar(c,d.tarayici.map(function(r){return {ad:r.ad,v:r.oturum}}));
  c=kart(g,'İşletim sistemi');cubuklar(c,d.isletim.map(function(r){return {ad:r.ad,v:r.oturum}}));
  c=kart(g,'Ekran genişliği','piksel');cubuklar(c,d.genislik.map(function(r){return {ad:r.ad,v:r.oturum}}));

  g=bolum(kok,'İçerik');
  c=kart(g,'En çok görüntülenen sayfalar');cubuklar(c,d.sayfalar.slice(0,12).map(function(r){return {ad:r.ad||r.p,alt:r.v?'('+(GORUNUM[r.v]||r.v)+')':'',v:r.say}}));
  c=kart(g,'Sekme ve görünümler','görüntüleme · etkin süre');cubuklar(c,d.gorunumler.map(function(r){return {ad:GORUNUM[r.v]||r.v,v:r.say,ek:r.sureSn?sure(r.sureSn):''}}));
  c=kart(g,'En çok görüntülenen ilanlar');cubuklar(c,d.ilanlar.slice(0,10).map(function(r){return {ad:ilanAd(r),v:r.say,ek:r.sureSn?sure(r.sureSn):''}}));
  c=kart(g,'En uzun incelenen ilanlar','ortalama etkin süre');cubuklar(c,d.enUzun.slice(0,10).map(function(r){return {ad:ilanAd(r),v:r.ortSn,yazi:sure(r.ortSn),ek:tr(r.say)+' gör.'}}));
  c=kart(g,'Kurum sayfaları');cubuklar(c,d.kurumlar.slice(0,10).map(function(r){return {ad:r.k,v:r.say}}));
  c=kart(g,'Taban puanı sayfaları');cubuklar(c,d.taban.slice(0,10).map(function(r){return {ad:r.k||'Genel liste',v:r.say}}));

  g=bolum(kok,'Etkileşim');
  c=kart(g,'En çok tıklanan öğeler');cubuklar(c,d.tikla.slice(0,14).map(function(r){return {ad:eylem(r.a),v:r.say}}));
  c=kart(g,'Kategori seçimi');cubuklar(c,d.kategori.map(function(r){return {ad:r.k||'tümü',v:r.say}}));
  c=kart(g,'Filtre kullanımı');cubuklar(c,d.filtre.map(function(r){return {ad:r.filtre+' = '+(r.deger||'—'),v:r.say}}));
  c=kart(g,'Aramalar','sorgu');cubuklar(c,d.aramalar.map(function(r){return {ad:r.q,v:r.var+r.sifir,ek:r.sifir?r.sifir+' sonuçsuz':''}}));
  c=kart(g,'Aranıp bulunamayanlar','sonuç = 0');cubuklar(c,d.sifirAramalar.map(function(r){return {ad:r.q,v:r.sifir}}),{uyari:true,bos:'Sonuçsuz arama yok.'});
  c=kart(g,'Manşet tıklamaları','slayt sırası');cubuklar(c,d.manset.konum.map(function(r){return {ad:r.n+'. slayt',v:r.say}}),{bos:'Manşet tıklaması yok.'});
  if(d.manset.nokta||d.manset.ok)c.appendChild(h('p','not',tr(d.manset.nokta)+' nokta tıklaması, '+tr(d.manset.ok)+' ok tıklaması.'));
  c=kart(g,'Dönüşümler');var dn=h('div','donusum'),D=d.donusum;
  [['Resmî ilana git',D.resmi],['Telegram',D.telegram],['Kaydet',D.kaydet],['Kayıt silme',D.kaydiSil],['Takvim (.ics)',D.takvim],['Profil kaydı',D.profil],['Tema değiştirme',D.tema]].forEach(function(a){var x=h('div');x.appendChild(h('span',null,a[0]));x.appendChild(h('strong',null,tr(a[1])));dn.appendChild(x)});c.appendChild(dn);
  c=kart(g,'Resmî ilana en çok gidilen ilanlar');cubuklar(c,d.resmiIlanlar.map(function(r){return {ad:ilanAd(r),v:r.say}}));
  c=kart(g,'En çok kaydedilen ilanlar');cubuklar(c,d.kaydedilenIlanlar.map(function(r){return {ad:ilanAd(r),v:r.say}}));
  c=kart(g,'Tercih robotu','düzey · puan aralığı');cubuklar(c,d.robot.map(function(r){return {ad:(r.duzey||'—')+(r.puan!=null?' · '+r.puan+'–'+(r.puan+4):''),v:r.say}}),{bos:'Tercih robotu kullanılmadı.'});
  g=bolum(kok,'Huni');g.className='izgara genis';c=kart(g,'Ana sayfa → ilan → resmî ilan');huni(c,d.huni);

  g=bolum(kok,'Kalite');
  c=kart(g,'Kaydırma derinliği','sayfa sayısı');cubuklar(c,d.kalite.kaydirma.map(function(r){return {ad:'%'+r.n,v:r.say}}),{bos:'Kaydırma verisi yok.'});
  c=kart(g,'Sayfa hızı');var hz=h('div','donusum');
  [['LCP (medyan, '+tr(d.kalite.hizOrnek||0)+' örnek)',d.kalite.lcpMs!=null?tr(d.kalite.lcpMs)+' ms':'—'],['TTFB (medyan)',d.kalite.ttfbMs!=null?tr(d.kalite.ttfbMs)+' ms':'—']].forEach(function(a){var x=h('div');x.appendChild(h('span',null,a[0]));x.appendChild(h('strong',null,a[1]));hz.appendChild(x)});c.appendChild(hz);
  c.appendChild(h('p','not','İyi: LCP 2,5 sn altı. Çok günlük görünümde günlük medyanların ağırlıklı ortalamasıdır.'));
  c=kart(g,'JavaScript hataları');cubuklar(c,d.kalite.hatalar.map(function(r){return {ad:r.mesaj,alt:r.dosya,v:r.say}}),{uyari:true,bos:'Hata kaydı yok.'});
  c=kart(g,'404 — bulunamayan adresler');cubuklar(c,d.kalite.yok404.map(function(r){return {ad:r.p,v:r.say}}),{uyari:true,bos:'404 kaydı yok.'});

  kok.appendChild(h('h2','bolum','Canlı akış'));
  akisKap=h('section','kart');kok.appendChild(akisKap);
  var f=h('footer',null,'Veriler anonimdir: IP adresi ve tarayıcı kimliği saklanmaz; ham olaylar 90 gün, özetler 400 gün tutulur. Tekil ziyaretçi günlük hesaplanır.');kok.appendChild(f);
  canliGuncelle()
}
function yukle(a,taze){
  aralik=a;siteYuklendi=true;
  document.querySelectorAll('#site-aralik button').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.a===a))});
  try{history.replaceState(null,'','?aralik='+a)}catch(e){}
  $('icerik').replaceChildren(h('p','bos','Yükleniyor…'));
  fetch('/panel/veri?aralik='+a+(taze?'&taze=1':''),{credentials:'same-origin'}).then(function(r){if(r.status===401){location.href='/panel';throw 0}if(!r.ok)throw new Error(r.status);return r.json()}).then(ciz).catch(function(e){if(e!==0)$('icerik').replaceChildren(h('p','bos hata-mesaj','Veri alınamadı. Yeniden dene.'))})
}
document.querySelectorAll('#site-aralik button').forEach(function(b){b.onclick=function(){yukle(b.dataset.a)}});
document.querySelectorAll('#forum-aralik button').forEach(function(b){b.onclick=function(){forumYukle(Number(b.dataset.g))}});
$('sekme-site').onclick=function(){sekmeAc('site')};$('sekme-forum').onclick=function(){sekmeAc('forum')};
$('yenile').onclick=function(){if(!$('forum-icerik').hidden)forumYukle(forumGun);else yukle(aralik,true)};
sekmeAc(new URLSearchParams(location.search).get('sekme')==='forum'?'forum':'site');canliGuncelle();
setInterval(function(){if(!document.hidden)canliGuncelle()},60000);document.addEventListener('visibilitychange',function(){if(!document.hidden)canliGuncelle()});
})();
`;

export function panelSayfasi(nonce) {
  const govde = `<body><div class="kap"><header class="ust"><h1>KPSS Tercihi · Site analizi<small>Çerezsiz, anonim ziyaret istatistikleri</small></h1><span class="bosluk"></span>
<span class="canli"><span class="nokta" aria-hidden="true"></span>Şu an aktif <b id="canli-sayi">–</b><span>(son 5 dk)</span></span>
<div class="segment" id="site-aralik" role="group" aria-label="Zaman aralığı"><button type="button" data-a="bugun" aria-pressed="false">Bugün</button><button type="button" data-a="7g" aria-pressed="true">7 gün</button><button type="button" data-a="30g" aria-pressed="false">30 gün</button><button type="button" data-a="90g" aria-pressed="false">90 gün</button></div>
<div class="segment" id="forum-aralik" role="group" aria-label="Forum dönemi" hidden><button type="button" data-g="7" aria-pressed="false">7 gün</button><button type="button" data-g="30" aria-pressed="true">30 gün</button><button type="button" data-g="90" aria-pressed="false">90 gün</button></div>
<div class="segment"><button type="button" id="yenile">Yenile</button></div><a class="cikis" href="/panel/cikis">Çıkış</a></header>
<nav class="sekmeler" role="tablist" aria-label="Bölüm"><button type="button" role="tab" id="sekme-site" aria-selected="true" aria-controls="icerik">Site</button><button type="button" role="tab" id="sekme-forum" aria-selected="false" aria-controls="forum-icerik">Forum</button></nav>
<main id="icerik" aria-live="polite"></main><main id="forum-icerik" class="forum" aria-live="polite" hidden></main></div><script nonce="${nonce}">${ISTEMCI}</script></body></html>`;
  return kafa('Site analizi', PANEL_CSS, nonce) + govde;
}
