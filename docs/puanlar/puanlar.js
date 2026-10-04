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
const GUNES='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/></svg>',AY_IKON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
function applyTheme(){const dark=readStore('kit-theme',null)==='dark';document.documentElement.dataset.theme=dark?'dark':'light';const m=document.querySelector('meta[name=theme-color]');if(m)m.content=dark?'#0D0E0C':'#F6F6F1';const b=$('theme');if(b){b.innerHTML=dark?GUNES:AY_IKON;b.setAttribute('aria-pressed',String(dark));b.setAttribute('aria-label',dark?'Açık temaya geç':'Koyu temaya geç');}}
/* kit-profil (ana sayfadaki profil): doğrulanır; geçersizse yok sayılır */
const LEVELS={lisans:'Lisans',onlisans:'Önlisans',ortaogretim:'Ortaöğretim'};
function profilOku(){const p=readStore('kit-profil',null);if(!p||typeof p!=='object'||p.v!==1||p.atlandi===true||!LEVELS[p.ogrenim])return null;const o={ogrenim:p.ogrenim,puan_turu:typeof p.puan_turu==='string'&&/^P\d{1,3}$/.test(p.puan_turu)?p.puan_turu:PUAN_TURU[p.ogrenim]};if(typeof p.puan==='number'&&isFinite(p.puan)&&p.puan>0&&p.puan<=100)o.puan=p.puan;return o;}
/* "Bu unvanda açık ilanlar (N)": ../liste.json bir kez yüklenir; yüklenemezse bağlantı sessizce gösterilmez */
let acikListe=null;const acikOnbellek=new Map();
const dizge=s=>String(s||'').toLocaleLowerCase('tr').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/ı/g,'i').replace(/\s*\(.*?\)/g,'').replace(/\s+/g,' ').trim();
async function acikListeYukle(){try{const r=await fetch('../liste.json',{cache:'no-cache'});if(!r.ok)return;const v=await r.json();if(v&&Array.isArray(v.ilanlar))acikListe=v.ilanlar.filter(i=>i&&typeof i.manset==='string').map(i=>({m:dizge(i.manset)}));}catch{}}
function acikSayi(unvan){if(!acikListe)return 0;const u=dizge(unvan);if(u.length<3)return 0;if(!acikOnbellek.has(u))acikOnbellek.set(u,acikListe.filter(i=>i.m.includes(u)).length);return acikOnbellek.get(u);}
function acikBaglanti(unvan){const n=acikSayi(unvan);if(!n)return null;const a=E('a','acik-link','Bu unvanda açık ilanlar ('+n+') →');a.href='../?q='+encodeURIComponent(unvan)+'#ilanlar';return a;}
function secenekler(sel,degerler,ilk){sel.replaceChildren(E('option',null,ilk));sel.firstChild.value='';for(const [v,t] of degerler){const o=E('option',null,t);o.value=v;sel.append(o);}}
function durum(metin){$('durum').hidden=!metin;$('durum').textContent=metin||'';}

async function yukle(d){
  if(!(d in veriler)){
    try{const r=await fetch(d+'.json',{cache:'no-cache'});veriler[d]=r.ok?await r.json():null;}catch{veriler[d]=null;}
  }
  return veriler[d];
}

const bolumVerileri={};let bolumListesiDuzey='',robotNo=0;
async function bolumYukle(d){
  if(!(d in bolumVerileri)){
    try{const r=await fetch(d+'-bolum.json',{cache:'no-cache'});if(!r.ok)return null;bolumVerileri[d]=await r.json();}catch{return null;}  // hata önbelleğe yazılmaz, tekrar denenir
  }
  return bolumVerileri[d];
}
async function bolumListesiDoldur(){
  const d=duzey,v=await bolumYukle(d);
  if(!v||d!==duzey||bolumListesiDuzey===d)return;
  const adlar=[...new Set(Object.values(v.bolumler))].sort((a,b)=>a.localeCompare(b,'tr'));
  $('bolum-liste').replaceChildren(...adlar.map(a=>{const o=E('option');o.value=a;return o;}));
  bolumListesiDuzey=d;
}
function bolumKodlari(v,ad){const k=kucuk(ad);return Object.entries(v.bolumler).filter(([,a])=>kucuk(a)===k).map(([kod])=>kod);}
const BOLUM_NOTLARI={
  belirsiz:'Bölüm şartı kılavuzun özel koşullarında; kontrol et',
  okunamadi:'Bu kadronun bölüm şartı belgeden okunamadı; kılavuzdan kontrol et',
  kismi:'Bu bölüm adının birden fazla ÖSYM program kodu var; kadro yalnız bazılarını kabul ediyor. Diplomandaki programın kabul edildiğini kılavuzdan kontrol et.'};
// Seçilen adın tüm kodları kabul ediliyorsa 'uygun', yalnız bir kısmı kabul ediliyorsa 'kismi';
// nitelik bilinmiyorsa 'belirsiz', belgeden okunamadıysa 'okunamadi'; hiçbiri değilse null (kadro elenir).
function bolumDurumu(k,v,kodlar){
  if(!k.nit||!k.nit.length)return 'belirsiz';
  const d=v.nitelikler[k.donem]||{},kabul=new Set();let okunamadi=false;
  for(const n of k.nit){
    const l=d[n]||[];
    if(l.includes('?'))okunamadi=true;
    for(const s of kodlar)if(l.includes('*')||l.some(e=>e===s||e.endsWith('-*')&&s.startsWith(e.slice(0,-1))))kabul.add(s);
  }
  if(kabul.size===kodlar.length)return 'uygun';
  return kabul.size?'kismi':okunamadi?'okunamadi':null;
}

async function duzeyAc(d){
  duzey=d;writeStore('kit-puan-duzey',d);
  for(const b of document.querySelectorAll('#duzeyler .tab')){const s=b.dataset.duzey===d;b.classList.toggle('secili',s);b.setAttribute('aria-pressed',s);}
  $('puan-turu').textContent='('+PUAN_TURU[d]+')';
  $('bolum-etiket').textContent=d==='ortaogretim'?'Mezun olduğun alan / dal':'Mezun olduğun bölüm';
  $('robot-bolum').value='';$('bolum-liste').replaceChildren();bolumListesiDuzey='';
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
    const unvanTd=E('td',null,k.unvan),bag=acikBaglanti(k.unvan);if(bag){const sm=E('small');sm.append(bag);unvanTd.append(sm);}
    tr.append(unvanTd,E('td','sayi',k.kontenjan),E('td','sayi',k.yerlesen),E('td','sayi',puanYaz(k.min)),E('td','sayi',puanYaz(k.max)));
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

async function robot(){
  const puan=parseFloat(String($('robot-puan').value).replace(',','.')),il=$('robot-il').value,ara=kucuk($('robot-ara').value).split(' ').filter(Boolean);
  const kutu=$('robot-sonuc'),d=duzey,bolumAdi=$('robot-bolum').value.trim(),no=++robotNo;
  if(!kayitlar.length||!(puan>0)){kutu.replaceChildren();return;}
  let bolum=null,kodlar=[];
  if(bolumAdi){
    bolum=await bolumYukle(d);
    if(no!==robotNo||d!==duzey)return;
    kodlar=bolum?bolumKodlari(bolum,bolumAdi):[];
    if(!kodlar.length){kutu.replaceChildren(E('p','notice',bolum?'Listeden bir bölüm seç':'Bölüm listesi yüklenemedi; bölüm alanını boş bırakıp tekrar dene.'));return;}
  }
  kutu.replaceChildren();
  // Her program kodu ayrı kadrodur (aynı unvan farklı nitelik isteyebilir); kodlar dönemler arasında
  // değiştiği için diğer dönemler yalnız aynı kurum/il/unvan için bilgi olarak gösterilir.
  const gecmis=new Map();
  for(const k of kayitlar)if(k.min!=null){const g=gecmis.get(k.anahtar)||new Map();g.set(k.donem,Math.min(g.get(k.donem)??999,k.min));gecmis.set(k.anahtar,g);}
  const sonuc=[];
  for(const k of kayitlar){
    if(k.min==null||il&&k.il!==il||!ara.every(a=>k.metin.includes(a)))continue;
    const sinif=puan>=k.max?'guclu':puan>=k.min?'uygun':puan>=k.min-SINIR?'sinirda':null;
    if(!sinif)continue;
    const bd=bolum?bolumDurumu(k,bolum,kodlar):null;
    if(bolum&&!bd)continue;
    sonuc.push({k,sinif,bd});
  }
  const agirlik={guclu:0,uygun:1,sinirda:2};
  sonuc.sort((a,b)=>b.k.donem.localeCompare(a.k.donem)||agirlik[a.sinif]-agirlik[b.sinif]||b.k.min-a.k.min);
  const say=s=>sonuc.filter(x=>x.sinif===s).length,ozet=E('div','robot-ozet');
  ozet.append(E('span',null,say('guclu')+' kadroda en yüksek puanı geçiyordun'),E('span',null,say('uygun')+' kadroda puanın yeterdi'),E('span',null,say('sinirda')+' kadroda sınırdaydın (en fazla '+SINIR+' puan eksik)'));
  if(bolum)ozet.append(E('span',null,sonuc.filter(x=>x.bd==='uygun').length+' kadro bölümüne uygun'));
  kutu.append(ozet);
  if(!sonuc.length){kutu.append(E('p','muted','Bu puanla eşleşen kadro bulunamadı. Filtreleri genişletmeyi dene.'));return;}
  const ol=E('ol','robot-liste'),ad={guclu:'Rahat yeterdi',uygun:'Yeterdi',sinirda:'Sınırda'};
  for(const {k,sinif,bd} of sonuc.slice(0,robotSinir)){
    const li=E('li');li.append(E('span','rozet '+sinif,ad[sinif]));
    const orta=E('div');orta.append(E('h3',null,k.unvan));
    orta.append(E('p',null,k.kurum+' · '+[k.il,k.teskilat].filter(Boolean).join(' · ')+' · '+k.kontenjan+' kontenjan'));
    const diger=[...gecmis.get(k.anahtar)].filter(([d])=>d!==k.donem).sort((a,b)=>b[0].localeCompare(a[0]));
    if(diger.length)orta.append(E('p',null,'Diğer dönemler: '+diger.map(([d,m])=>donemAdi(d)+' '+puanYaz(m)).join(' · ')));
    if(BOLUM_NOTLARI[bd])orta.append(E('p','bolum-not',BOLUM_NOTLARI[bd]));
    const sag=E('div','robot-puan');sag.append(E('strong',null,puanYaz(k.min)),E('span',null,donemAdi(k.donem)+' en küçük'));
    const bag=acikBaglanti(k.unvan);if(bag){const p=E('p');p.append(bag);orta.append(p);}
    li.append(orta,sag);ol.append(li);
  }
  kutu.append(ol);
  if(sonuc.length>robotSinir){const b=E('button','btn btn-ikinci','Daha fazla göster ('+(sonuc.length-robotSinir)+')');b.onclick=()=>{robotSinir+=ROBOT_ILK;robot();};kutu.append(b);}
}

applyTheme();
$('theme').onclick=()=>{writeStore('kit-theme',document.documentElement.dataset.theme==='dark'?'light':'dark');applyTheme();};
for(const b of document.querySelectorAll('#duzeyler .tab'))b.onclick=()=>duzeyAc(b.dataset.duzey);
for(const id of ['donem','il','sirala'])$(id).onchange=()=>{sayfa=1;tabloCiz();};
let bekle;$('ara').oninput=()=>{clearTimeout(bekle);bekle=setTimeout(()=>{sayfa=1;tabloCiz();},150);};
$('robot-bolum').onfocus=bolumListesiDoldur;
$('robot-form').onsubmit=e=>{e.preventDefault();robotSinir=ROBOT_ILK;robot();};
{
  const pr=profilOku(),kayitliDuzey=readStore('kit-puan-duzey','');
  duzeyAc(pr?pr.ogrenim:PUAN_TURU[kayitliDuzey]?kayitliDuzey:'lisans').then(()=>{
    if(!pr)return;
    const ip=$('profil-ipucu');
    let m='Profilinden dolduruldu: '+LEVELS[pr.ogrenim]+(pr.puan?' · KPSS '+pr.puan_turu+' '+String(pr.puan).replace('.',','):'')+'.';
    if(pr.puan_turu!==PUAN_TURU[pr.ogrenim])m+=' Bu tablo yalnızca '+PUAN_TURU[pr.ogrenim]+' puan türüyle yapılan merkezi yerleştirmeleri gösterir.';
    ip.textContent=m;ip.hidden=false;
    if(pr.puan){$('robot-puan').value=String(pr.puan).replace('.',',');robot();}
  });
  acikListeYukle().then(()=>{if(!acikListe)return;tabloCiz();if($('robot-sonuc').children.length)robot();});
}
