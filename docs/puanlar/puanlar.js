'use strict';
const $=id=>document.getElementById(id);
const PUAN_TURU={lisans:'P3',onlisans:'P93',ortaogretim:'P94'};
const SAYFA=50,ROBOT_ILK=60,SINIR=2;
const veriler={};let duzey='lisans',kayitlar=[],sayfa=1,robotSinir=ROBOT_ILK;

function E(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;}
function kucuk(s){return String(s||'').toLocaleLowerCase('tr').replace(/\s+/g,' ').trim();}
function donemAdi(d){return d.replace('-','/');}
function puanYaz(p){return p==null?'—':p.toLocaleString('tr-TR',{minimumFractionDigits:5,maximumFractionDigits:5});}
function readStore(k,f){try{const v=JSON.parse(localStorage.getItem(k));return v??f;}catch{return f;}}
function writeStore(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch{}}
function applyTheme(){const t=readStore('kit-theme',null);document.documentElement.dataset.theme=t==='dark'||t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
function secenekler(sel,degerler,ilk){sel.replaceChildren(E('option',null,ilk));sel.firstChild.value='';for(const [v,t] of degerler){const o=E('option',null,t);o.value=v;sel.append(o);}}
function durum(metin){$('durum').hidden=!metin;$('durum').textContent=metin||'';}

async function yukle(d){
  if(!(d in veriler)){
    try{const r=await fetch(d+'.json',{cache:'no-cache'});veriler[d]=r.ok?await r.json():null;}catch{veriler[d]=null;}
  }
  return veriler[d];
}

async function duzeyAc(d){
  duzey=d;writeStore('kit-puan-duzey',d);
  for(const b of document.querySelectorAll('#duzeyler .tab')){const s=b.dataset.duzey===d;b.classList.toggle('selected',s);b.setAttribute('aria-pressed',s);}
  $('puan-turu').textContent='('+PUAN_TURU[d]+')';
  const v=await yukle(d);
  if(d!==duzey)return;
  kayitlar=[];
  if(!v){durum('Bu öğrenim düzeyinin taban puanları henüz eklenmedi. Yakında burada olacak.');}
  else{
    durum('');
    for(const [donem,liste] of Object.entries(v.donemler))for(const k of liste){
      kayitlar.push({...k,donem,anahtar:[kucuk(k.kurum),k.il,k.teskilat,kucuk(k.unvan)].join('|'),metin:kucuk(k.kurum+' '+k.unvan+' '+k.il)});
    }
  }
  const donemler=[...new Set(kayitlar.map(k=>k.donem))].sort().reverse();
  const iller=[...new Set(kayitlar.map(k=>k.il))].sort((a,b)=>a.localeCompare(b,'tr'));
  secenekler($('donem'),donemler.map(x=>[x,donemAdi(x)]),'Tüm dönemler');
  for(const id of ['il','robot-il'])secenekler($(id),iller.map(x=>[x,x.charAt(0)+x.slice(1).toLocaleLowerCase('tr')]),'Tüm iller');
  sayfa=1;tabloCiz();$('robot-sonuc').replaceChildren();
}

function suzulmus(){
  const donem=$('donem').value,il=$('il').value,ara=kucuk($('ara').value).split(' ').filter(Boolean);
  const l=kayitlar.filter(k=>(!donem||k.donem===donem)&&(!il||k.il===il)&&ara.every(a=>k.metin.includes(a)));
  const s=$('sirala').value,yok=x=>x.min??-1;
  const sira={'min-azalan':(a,b)=>yok(b)-yok(a),'min-artan':(a,b)=>(a.min??999)-(b.min??999),
    donem:(a,b)=>b.donem.localeCompare(a.donem)||yok(b)-yok(a),kurum:(a,b)=>a.kurum.localeCompare(b.kurum,'tr')||b.donem.localeCompare(a.donem)}[s];
  return l.sort(sira);
}

function tabloCiz(){
  const l=suzulmus(),toplam=Math.max(1,Math.ceil(l.length/SAYFA));sayfa=Math.min(sayfa,toplam);
  $('tablo-ozet').textContent=l.length.toLocaleString('tr-TR')+' kadro';
  const govde=$('satirlar');govde.replaceChildren();
  for(const k of l.slice((sayfa-1)*SAYFA,sayfa*SAYFA)){
    const tr=E('tr');
    tr.append(E('td',null,donemAdi(k.donem)));
    const kurum=E('td',null,k.kurum);kurum.append(E('small',null,[k.il,k.teskilat].filter(Boolean).join(' · ')));tr.append(kurum);
    tr.append(E('td',null,k.unvan),E('td','sayi',k.kontenjan),E('td','sayi',k.yerlesen),E('td','sayi',puanYaz(k.min)),E('td','sayi',puanYaz(k.max)));
    govde.append(tr);
  }
  if(!l.length){const tr=E('tr'),td=E('td',null,kayitlar.length?'Bu filtrelerle kadro bulunamadı.':'Veri yok.');td.colSpan=7;tr.append(td);govde.append(tr);}
  const nav=$('sayfalar');nav.replaceChildren();
  if(toplam>1){
    const ekle=(t,s,etiket)=>{const b=E('button',null,t);if(etiket)b.setAttribute('aria-label',etiket);if(s===sayfa)b.setAttribute('aria-current','page');b.disabled=s<1||s>toplam;b.onclick=()=>{sayfa=s;tabloCiz();$('tablo').scrollIntoView();};nav.append(b);};
    ekle('←',sayfa-1,'Önceki sayfa');
    for(let s=Math.max(1,sayfa-2);s<=Math.min(toplam,sayfa+2);s++)ekle(String(s),s);
    ekle('→',sayfa+1,'Sonraki sayfa');
  }
}

function robot(){
  const puan=parseFloat(String($('robot-puan').value).replace(',','.')),il=$('robot-il').value,ara=kucuk($('robot-ara').value).split(' ').filter(Boolean);
  const kutu=$('robot-sonuc');kutu.replaceChildren();
  if(!kayitlar.length||!(puan>0))return;
  // Her program kodu ayrı kadrodur (aynı unvan farklı nitelik isteyebilir); kodlar dönemler arasında
  // değiştiği için diğer dönemler yalnız aynı kurum/il/unvan için bilgi olarak gösterilir.
  const gecmis=new Map();
  for(const k of kayitlar)if(k.min!=null){const g=gecmis.get(k.anahtar)||new Map();g.set(k.donem,Math.min(g.get(k.donem)??999,k.min));gecmis.set(k.anahtar,g);}
  const sonuc=[];
  for(const k of kayitlar){
    if(k.min==null||il&&k.il!==il||!ara.every(a=>k.metin.includes(a)))continue;
    const sinif=puan>=k.max?'guclu':puan>=k.min?'uygun':puan>=k.min-SINIR?'sinirda':null;
    if(sinif)sonuc.push({k,sinif});
  }
  const agirlik={guclu:0,uygun:1,sinirda:2};
  sonuc.sort((a,b)=>b.k.donem.localeCompare(a.k.donem)||agirlik[a.sinif]-agirlik[b.sinif]||b.k.min-a.k.min);
  const say=s=>sonuc.filter(x=>x.sinif===s).length,ozet=E('div','robot-ozet');
  ozet.append(E('span',null,say('guclu')+' kadroda en yüksek puanı geçiyordun'),E('span',null,say('uygun')+' kadroda puanın yeterdi'),E('span',null,say('sinirda')+' kadroda sınırdaydın (en fazla '+SINIR+' puan eksik)'));
  kutu.append(ozet);
  if(!sonuc.length){kutu.append(E('p','muted','Bu puanla eşleşen kadro bulunamadı. Filtreleri genişletmeyi dene.'));return;}
  const ol=E('ol','robot-liste'),ad={guclu:'Rahat yeterdi',uygun:'Yeterdi',sinirda:'Sınırda'};
  for(const {k,sinif} of sonuc.slice(0,robotSinir)){
    const li=E('li');li.append(E('span','rozet '+sinif,ad[sinif]));
    const orta=E('div');orta.append(E('h3',null,k.unvan));
    orta.append(E('p',null,k.kurum+' · '+[k.il,k.teskilat].filter(Boolean).join(' · ')+' · '+k.kontenjan+' kontenjan'));
    const diger=[...gecmis.get(k.anahtar)].filter(([d])=>d!==k.donem).sort((a,b)=>b[0].localeCompare(a[0]));
    if(diger.length)orta.append(E('p',null,'Diğer dönemler: '+diger.map(([d,m])=>donemAdi(d)+' '+puanYaz(m)).join(' · ')));
    const sag=E('div','robot-puan');sag.append(E('strong',null,puanYaz(k.min)),E('span',null,donemAdi(k.donem)+' en küçük'));
    li.append(orta,sag);ol.append(li);
  }
  kutu.append(ol);
  if(sonuc.length>robotSinir){const b=E('button','button secondary','Daha fazla göster ('+(sonuc.length-robotSinir)+')');b.onclick=()=>{robotSinir+=ROBOT_ILK;robot();};kutu.append(b);}
}

applyTheme();$('year').textContent=new Date().getFullYear();
$('theme').onclick=()=>{writeStore('kit-theme',document.documentElement.dataset.theme==='dark'?'light':'dark');applyTheme();};
for(const b of document.querySelectorAll('#duzeyler .tab'))b.onclick=()=>duzeyAc(b.dataset.duzey);
for(const id of ['donem','il','sirala'])$(id).onchange=()=>{sayfa=1;tabloCiz();};
let bekle;$('ara').oninput=()=>{clearTimeout(bekle);bekle=setTimeout(()=>{sayfa=1;tabloCiz();},150);};
$('robot-form').onsubmit=e=>{e.preventDefault();robotSinir=ROBOT_ILK;robot();};
duzeyAc(PUAN_TURU[readStore('kit-puan-duzey','')]?readStore('kit-puan-duzey',''):'lisans');
