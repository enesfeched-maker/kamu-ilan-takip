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
var EYLEM={manset_tikla:'Manşet tıklaması',manset_nokta:'Manşet noktası',manset_ok:'Manşet oku',satir_tikla:'İlan satırı',kurum_tikla:'Kurum bağlantısı',kategori:'Kategori seçimi',filtre:'Filtre değişimi',arama:'Arama',daha_fazla:'Daha fazla göster',kaydet:'İlan kaydedildi',kaydi_sil:'Kayıt kaldırıldı',takvim_ics:'Takvim indirme (.ics)',telegram:'Telegram bağlantısı',resmi_ilan:'Resmî ilana git',profil_kaydet:'Profil kaydı',robot:'Tercih robotu',tema:'Tema değiştirme',menu:'Menü',makale:'Rehber makalesi'};
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

function cizgiGrafik(kap,gunler){
  if(gunler.length<2){bosKart(kap,'Çizgi grafik için en az iki gün gerekir; 7 gün seç.');return}
  var W=720,H=220,L=36,R=10,T=10,B=26,en=Math.max.apply(null,gunler.map(function(g){return g.ziyaretci}))||1;
  var yu=en<=5?5:Math.ceil(en/4)*4;
  var s=svg('svg',{viewBox:'0 0 '+W+' '+H,'class':'grafik',role:'img','aria-label':'Günlük tekil ziyaretçi sayısı'});
  [0,.5,1].forEach(function(f){var y=T+(H-T-B)*(1-f);s.appendChild(svg('line',{x1:L,x2:W-R,y1:y,y2:y,'class':'izgara-cizgi'}));var t=svg('text',{x:L-6,y:y+4,'text-anchor':'end'});t.textContent=tr(Math.round(yu*f));s.appendChild(t)});
  var n=gunler.length,xs=function(i){return L+(W-L-R)*(n===1?.5:i/(n-1))},ys=function(v){return T+(H-T-B)*(1-v/yu)};
  var nok=gunler.map(function(g,i){return xs(i)+','+ys(g.ziyaretci)});
  s.appendChild(svg('polygon',{points:xs(0)+','+(H-B)+' '+nok.join(' ')+' '+xs(n-1)+','+(H-B),'class':'alan'}));
  s.appendChild(svg('polyline',{points:nok.join(' '),'class':'hat'}));
  var adim=Math.max(1,Math.ceil(n/7));
  gunler.forEach(function(g,i){
    if(n<=31){var c=svg('circle',{cx:xs(i),cy:ys(g.ziyaretci),r:n<=14?4:3,'class':'nokta-g'});var t=svg('title',{});t.textContent=gunKisa(g.gun)+': '+tr(g.ziyaretci)+' tekil ziyaretçi, '+tr(g.sayfa)+' görüntüleme';c.appendChild(t);s.appendChild(c)}
    if(i%adim===0||i===n-1){var x=svg('text',{x:xs(i),y:H-8,'text-anchor':'middle'});x.textContent=gunKisa(g.gun);s.appendChild(x)}});
  kap.appendChild(s)
}
function isiHaritasi(kap,isi){
  if(!isi.length){bosKart(kap);return}
  var m={},en=1;isi.forEach(function(r){m[r[0]+'-'+r[1]]=r[2];if(r[2]>en)en=r[2]});
  var W=720,L=34,hw=(W-L-4)/24,hh=20,H=7*hh+26;
  var s=svg('svg',{viewBox:'0 0 '+W+' '+H,'class':'grafik',role:'img','aria-label':'Haftanın günü ve saate göre sayfa görüntüleme'});
  for(var g=0;g<7;g++){
    var t=svg('text',{x:L-6,y:g*hh+hh*.7,'text-anchor':'end'});t.textContent=GUNAD[g];s.appendChild(t);
    for(var sa=0;sa<24;sa++){
      var v=m[g+'-'+sa]||0,r=svg('rect',{x:L+sa*hw+1,y:g*hh+1,width:hw-2,height:hh-2,rx:3,'class':v?'hucre':'hucre-bos'});
      if(v)r.setAttribute('fill-opacity',(0.18+0.82*v/en).toFixed(2));
      var ti=svg('title',{});ti.textContent=GUNAD[g]+' '+(sa<10?'0':'')+sa+':00 — '+tr(v)+' görüntüleme';r.appendChild(ti);s.appendChild(r)}}
  [0,3,6,9,12,15,18,21].forEach(function(sa){var t=svg('text',{x:L+sa*hw+hw/2,y:H-8,'text-anchor':'middle'});t.textContent=(sa<10?'0':'')+sa;s.appendChild(t)});
  kap.appendChild(s);kap.appendChild(h('p','not','Türkiye saati. Koyu hücre = daha çok sayfa görüntüleme.'))
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
  var kp=h('div','kpi');
  [['Tekil ziyaretçi',tr(k.ziyaretci),d.aralik.adet>1?'günlük tekil sayıların toplamı':'bugün'],['Oturum',tr(k.oturum),''],['Sayfa görüntüleme',tr(k.sayfa),k.oturum?(k.sayfa/k.oturum).toFixed(1).replace('.',',')+' sayfa / oturum':''],
   ['Ort. etkin süre',sure(k.etkinSaniyeOrt),'oturum başına, sekme açık ve etkileşimliyken'],['Hemen çıkma',yuzde(k.hemenCikma),'tek sayfa, etkileşimsiz oturum'],
   ['Yeni / geri dönen',yg?yuzde(k.yeni/yg)+' / '+yuzde(k.geri/yg):'—',tr(k.yeni)+' yeni · '+tr(k.geri)+' geri dönen']].forEach(function(a){
    var c=h('div');c.appendChild(h('span',null,a[0]));c.appendChild(h('strong',null,a[1]));c.appendChild(h('em',null,a[2]));kp.appendChild(c)});
  kok.appendChild(kp);

  var g=bolum(kok,'Zaman');g.className='izgara genis';
  var c=kart(g,'Günlük tekil ziyaretçi');cizgiGrafik(c,d.gunler);
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
  aralik=a;
  document.querySelectorAll('.segment button').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.a===a))});
  try{history.replaceState(null,'','?aralik='+a)}catch(e){}
  $('icerik').replaceChildren(h('p','bos','Yükleniyor…'));
  fetch('/panel/veri?aralik='+a+(taze?'&taze=1':''),{credentials:'same-origin'}).then(function(r){if(r.status===401){location.href='/panel';throw 0}if(!r.ok)throw new Error(r.status);return r.json()}).then(ciz).catch(function(e){if(e!==0)$('icerik').replaceChildren(h('p','bos hata-mesaj','Veri alınamadı. Yeniden dene.'))})
}
document.querySelectorAll('.segment button').forEach(function(b){b.onclick=function(){yukle(b.dataset.a)}});
$('yenile').onclick=function(){yukle(aralik,true)};
var q=new URLSearchParams(location.search).get('aralik');
yukle(['bugun','7g','30g','90g'].indexOf(q)>=0?q:'7g');
setInterval(function(){if(!document.hidden)canliGuncelle()},60000);document.addEventListener('visibilitychange',function(){if(!document.hidden)canliGuncelle()});
})();
`;

export function panelSayfasi(nonce) {
  const govde = `<body><div class="kap"><header class="ust"><h1>KPSS Tercihi · Site analizi<small>Çerezsiz, anonim ziyaret istatistikleri</small></h1><span class="bosluk"></span>
<span class="canli"><span class="nokta" aria-hidden="true"></span>Şu an aktif <b id="canli-sayi">–</b><span>(son 5 dk)</span></span>
<div class="segment" role="group" aria-label="Zaman aralığı"><button type="button" data-a="bugun" aria-pressed="false">Bugün</button><button type="button" data-a="7g" aria-pressed="true">7 gün</button><button type="button" data-a="30g" aria-pressed="false">30 gün</button><button type="button" data-a="90g" aria-pressed="false">90 gün</button></div>
<div class="segment"><button type="button" id="yenile">Yenile</button></div><a class="cikis" href="/panel/cikis">Çıkış</a></header>
<main id="icerik" aria-live="polite"></main></div><script nonce="${nonce}">${ISTEMCI}</script></body></html>`;
  return kafa('Site analizi', PANEL_CSS, nonce) + govde;
}
