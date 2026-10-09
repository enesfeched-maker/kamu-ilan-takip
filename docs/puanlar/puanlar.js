'use strict';
const $=id=>document.getElementById(id);
const PUAN_TURU={lisans:'P3',onlisans:'P93',ortaogretim:'P94'};
const SAYFA=50,ROBOT_ILK=60,SINIR=2;
const veriler={};let duzey='lisans',kayitlar=[],sayfa=1,robotSinir=ROBOT_ILK;

function E(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;}
function kucuk(s){return String(s||'').toLocaleLowerCase('tr').replace(/\s+/g,' ').trim();}
function donemAdi(d){return d.replace('-','/');}
function puanYaz(p){return p==null?'—':p.toLocaleString('tr-TR',{minimumFractionDigits:5,maximumFractionDigits:5});}
const A=(t,p)=>{try{if(typeof window!=='undefined'&&window.kpssA)window.kpssA(t,p);}catch{}};
function readStore(k,f){try{const v=JSON.parse(localStorage.getItem(k));return v??f;}catch{return f;}}
function writeStore(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch{}}
function applyTheme(){const dark=window.kitKoyu?window.kitKoyu():readStore('kit-theme',null)==='dark';document.documentElement.dataset.theme=dark?'dark':'light';const m=document.querySelector('meta[name=theme-color]');if(m)m.content=dark?'#0D0E0C':'#F6F6F1';const b=$('theme');if(b){if(!b.dataset.hazir){b.dataset.hazir='1';if(typeof requestAnimationFrame==='function')requestAnimationFrame(()=>requestAnimationFrame(()=>b.classList.add('anahtar-hazir')));}b.setAttribute('aria-pressed',String(dark));b.setAttribute('aria-label',dark?'Açık temaya geç':'Koyu temaya geç');}}
/* kit-profil (ana sayfadaki profil): doğrulanır; geçersizse yok sayılır */
const LEVELS={lisans:'Lisans',onlisans:'Önlisans',ortaogretim:'Ortaöğretim'};
const ptLevel=p=>p==='P94'?'ortaogretim':p==='P93'?'onlisans':/^P([1-9]|[1-3]\d|4[0-8])$/.test(p)?'lisans':null;
const puanTr=n=>Number(n).toLocaleString('tr-TR',{maximumFractionDigits:5});
function profilOku(){const p=readStore('kit-profil',null);if(!p||typeof p!=='object'||p.v!==1||p.atlandi===true||!LEVELS[p.ogrenim])return null;const o={ogrenim:p.ogrenim,puan_turu:typeof p.puan_turu==='string'&&/^P\d{1,3}$/.test(p.puan_turu)&&ptLevel(p.puan_turu)===p.ogrenim?p.puan_turu:PUAN_TURU[p.ogrenim],bolum:typeof p.bolum==='string'?p.bolum.slice(0,60):'',iller:Array.isArray(p.iller)?p.iller.filter(x=>typeof x==='string'&&x.length<=40):[],tum_turkiye:p.tum_turkiye===true};if(typeof p.puan==='number'&&isFinite(p.puan)&&p.puan>0&&p.puan<=100)o.puan=p.puan;return o;}
/* "Bu unvanda açık ilanlar (N)": ../liste.json bir kez yüklenir; yüklenemezse bağlantı sessizce gösterilmez */
let acikListe=null;const acikOnbellek=new Map();
/* Python kucuk() ile aynı: Türkçe küçük harf, kesme işareti atılır, boşluk tekilleşir; parantezli ek atılır. VHKİ kısaltması tam adıyla eşleşir. */
const dizge=s=>{const k=String(s||'').toLocaleLowerCase('tr').replace(/['’`´]/g,'').replace(/\s*\(.*?\)/g,'').replace(/\s+/g,' ').trim();return k==='veri hazırlama ve kontrol işletmeni'?'vhki':k;};
async function acikListeYukle(){try{const r=await fetch('../liste.json',{cache:'no-cache'});if(!r.ok)return;const v=await r.json();if(v&&Array.isArray(v.ilanlar))acikListe=v.ilanlar.filter(i=>i&&Array.isArray(i.unvanlar)).map(i=>({u:new Set(i.unvanlar.filter(x=>typeof x==='string').map(dizge))}));}catch{}}
function acikSayi(unvan){if(!acikListe)return 0;const u=dizge(unvan);if(u.length<2)return 0;if(!acikOnbellek.has(u))acikOnbellek.set(u,acikListe.filter(i=>i.u.has(u)).length);return acikOnbellek.get(u);}
function acikBaglanti(unvan){const n=acikSayi(unvan);if(!n)return null;const a=E('a','acik-link','Bu unvanda açık ilanlar ('+n+') →');a.href='../?q='+encodeURIComponent(unvan)+'#ilanlar';return a;}
/* Açılır seçim kutusu (tek tip görünüm): data-coklu="1" ise onay kutulu çoklu seçim, data-ara varsa listede arama.
   API: ayarla([[değer, yazı]]), degerler() → dizi, sec(dizi), onDegis / onAc geri çağrıları. */
const ACIK_SECIMLER=new Set();
function secimKur(kok){
  const coklu=kok.dataset.coklu==='1',bos=kok.dataset.bos||'Tümü',araYer=kok.dataset.ara||'';
  let liste=[],secili=new Set(),acik=false;
  const btn=E('button','secim-btn'),yazi=E('span','secim-yazi',bos),ok=E('span','secim-ok');ok.setAttribute('aria-hidden','true');
  btn.type='button';btn.setAttribute('aria-haspopup','listbox');btn.setAttribute('aria-expanded','false');btn.append(yazi,ok);
  const panel=E('div','secim-panel');panel.hidden=true;
  const ara=araYer?E('input','secim-ara'):null;
  if(ara){ara.type='search';ara.placeholder=araYer;ara.autocomplete='off';ara.oninput=()=>ciz();ara.onkeydown=e=>{if(e.key==='Enter')e.preventDefault();};panel.append(ara);}
  const ul=E('div','secim-liste');ul.setAttribute('role','listbox');if(coklu)ul.setAttribute('aria-multiselectable','true');panel.append(ul);
  let alt=null;
  if(coklu){alt=E('div','secim-alt');const t=E('button','secim-temizle','Temizle'),k=E('button','secim-tamam','Tamam');t.type=k.type='button';
    t.onclick=()=>{secili.clear();degisti();ciz();};k.onclick=()=>kapat(true);alt.append(t,k);panel.append(alt);}
  kok.replaceChildren(btn,panel);
  const api={onDegis:null,onAc:null};
  function etiket(){
    const s=liste.filter(([v])=>secili.has(v)).map(([,t])=>t);
    yazi.textContent=!s.length?bos:s.length===1?s[0]:s.length===2?s.join(', '):s[0]+' +'+(s.length-1);
    kok.classList.toggle('dolu',s.length>0);
  }
  function degisti(){etiket();if(api.onDegis)api.onDegis(api.degerler());}
  function ciz(){
    const q=ara?kucuk(ara.value):'';const ogeler=[];
    if(!coklu&&!q){const b=E('button','secim-oge'+(secili.size?'':' secili'),bos);b.type='button';b.onclick=()=>{secili.clear();degisti();kapat(true);};ogeler.push(b);}
    for(const [v,t] of liste){
      if(q&&!kucuk(t).includes(q))continue;
      if(ogeler.length>=300)break;  // uzun listelerde (bölümler) ilk 300 eşleşme; arama daraltır
      if(coklu){const l=E('label','secim-oge'),c=E('input');c.type='checkbox';c.checked=secili.has(v);
        c.onchange=()=>{c.checked?secili.add(v):secili.delete(v);degisti();};l.append(c,E('span',null,t));ogeler.push(l);}
      else{const b=E('button','secim-oge'+(secili.has(v)?' secili':''),t);b.type='button';b.onclick=()=>{secili=new Set([v]);degisti();kapat(true);};ogeler.push(b);}
    }
    if(!ogeler.length)ogeler.push(E('p','secim-yok',liste.length?'Eşleşme yok':'Yükleniyor…'));
    ul.replaceChildren(...ogeler);
  }
  async function ac(){
    for(const s of ACIK_SECIMLER)s.kapat(false);
    acik=true;ACIK_SECIMLER.add(api);panel.hidden=false;btn.setAttribute('aria-expanded','true');kok.classList.add('acik');
    if(ara)ara.value='';ciz();
    if(api.onAc){await api.onAc();if(acik)ciz();}
    if(ara&&acik&&matchMedia('(pointer:fine)').matches)ara.focus();
  }
  function kapat(odak){if(!acik)return;acik=false;ACIK_SECIMLER.delete(api);panel.hidden=true;btn.setAttribute('aria-expanded','false');kok.classList.remove('acik');if(odak)btn.focus();}
  btn.onclick=()=>acik?kapat(false):ac();
  kok.addEventListener('keydown',e=>{if(e.key==='Escape'&&acik){e.preventDefault();kapat(true);}});
  Object.assign(api,{
    kapat,
    ayarla(yeni){liste=yeni;const varolan=new Set(yeni.map(([v])=>v));secili=new Set([...secili].filter(v=>varolan.has(v)));etiket();if(acik)ciz();},
    degerler:()=>liste.filter(([v])=>secili.has(v)).map(([v])=>v),
    sec(dizi){secili=new Set(dizi);etiket();if(acik)ciz();},
  });
  etiket();
  return api;
}
document.addEventListener('mousedown',e=>{for(const s of ACIK_SECIMLER)if(!s.kok.contains(e.target))s.kapat(false);});
document.addEventListener('touchstart',e=>{for(const s of ACIK_SECIMLER)if(!s.kok.contains(e.target))s.kapat(false);},{passive:true});
const SEC={};
for(const id of ['robot-bolum','robot-il','donem','il']){SEC[id]=secimKur($(id));SEC[id].kok=$(id);}
const ilYazi=x=>x.charAt(0)+x.slice(1).toLocaleLowerCase('tr');
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
  SEC['robot-bolum'].ayarla(adlar.map(a=>[a,a]));
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
  SEC['robot-bolum'].sec([]);SEC['robot-bolum'].ayarla([]);bolumListesiDuzey='';
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
  SEC.donem.ayarla(donemler.map(x=>[x,donemAdi(x)]));
  for(const id of ['il','robot-il'])SEC[id].ayarla(iller.map(x=>[x,ilYazi(x)]));
  sayfa=1;tabloCiz();$('robot-sonuc').replaceChildren();
}

function suzulmus(){
  const donem=new Set(SEC.donem.degerler()),il=new Set(SEC.il.degerler()),ara=kucuk($('ara').value).split(' ').filter(Boolean);
  const l=kayitlar.filter(k=>(!donem.size||donem.has(k.donem))&&(!il.size||il.has(k.il))&&ara.every(a=>k.metin.includes(a)));
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
  const puan=parseFloat(String($('robot-puan').value).replace(',','.')),il=new Set(SEC['robot-il'].degerler()),ara=kucuk($('robot-ara').value).split(' ').filter(Boolean);
  const kutu=$('robot-sonuc'),d=duzey,bolumAdi=SEC['robot-bolum'].degerler()[0]||'',no=++robotNo;
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
    if(k.min==null||il.size&&!il.has(k.il)||!ara.every(a=>k.metin.includes(a)))continue;
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

window.kitTemaUygula=applyTheme;applyTheme();{const y=$('yil');if(y)y.textContent=String(new Date().getFullYear());}
$('theme').onclick=()=>{A('tikla',{a:'tema',x:document.documentElement.dataset.theme==='dark'?'light':'dark'});writeStore('kit-theme',document.documentElement.dataset.theme==='dark'?'light':'dark');applyTheme();};
for(const b of document.querySelectorAll('#duzeyler .tab'))b.onclick=()=>duzeyAc(b.dataset.duzey);
$('sirala').onchange=SEC.donem.onDegis=SEC.il.onDegis=()=>{sayfa=1;tabloCiz();};
let bekle;$('ara').oninput=()=>{clearTimeout(bekle);bekle=setTimeout(()=>{sayfa=1;tabloCiz();},150);};
SEC['robot-bolum'].onAc=bolumListesiDoldur;
$('robot-form').onsubmit=e=>{e.preventDefault();robotSinir=ROBOT_ILK;const p=parseFloat(String($('robot-puan').value).replace(',','.'));if(p>0)A('tikla',{a:'robot',x:duzey,n:Math.floor(p/5)*5});robot();};
{
  const pr=profilOku(),kayitliDuzey=readStore('kit-puan-duzey','');
  duzeyAc(pr?pr.ogrenim:PUAN_TURU[kayitliDuzey]?kayitliDuzey:'lisans').then(async()=>{
    /* Profil varsa robot sessizce doldurulur; açıklama kutusu gösterilmez (sade sayfa, 9 Ekim 2026). */
    if(!pr)return;
    /* Bölüm adı listedeki bir bölümle (büyük/küçük harf farkı gözetmeden) eşleşirse robota yazılır; profildeki iller de seçilir. */
    let bolumAd='';
    if(pr.bolum){await bolumListesiDoldur();const v=bolumVerileri[duzey];if(v&&duzey===pr.ogrenim){const ad=Object.values(v.bolumler).find(a=>kucuk(a)===kucuk(pr.bolum));if(ad){bolumAd=ad;SEC['robot-bolum'].sec([ad]);}}}
    if(pr.iller.length&&!pr.tum_turkiye){const pi=new Set(pr.iller.map(kucuk));SEC['robot-il'].sec([...new Set(kayitlar.map(k=>k.il))].filter(x=>pi.has(kucuk(x))));}
    const uyumlu=pr.puan_turu===PUAN_TURU[pr.ogrenim];
    if(pr.puan&&uyumlu){$('robot-puan').value=puanTr(pr.puan);}
    if(pr.puan&&uyumlu||bolumAd)robot();
  });
  acikListeYukle().then(()=>{if(!acikListe)return;tabloCiz();if($('robot-sonuc').children.length)robot();});
}
/* Çok aranıp ilanı çıkmayan meslekler (analizden, 12 saatte bir): tıklayınca taban puanı tablosunda aranır. */
fetch('https://api.kpsstercihi.com/aranan').then(r=>r.ok?r.json():null).then(j=>{
  const k=((j&&j.kelimeler)||[]).slice(0,6);if(!k.length)return;
  const d=E('div','aranan-cip');d.append(E('span','muted','Çok arananlar:'));
  for(const x of k){const b=E('button','cip',x.kelime);b.type='button';b.onclick=()=>{A('tikla',{a:'aranan_cip',x:x.kelime});$('ara').value=x.kelime;sayfa=1;tabloCiz();$('ara').scrollIntoView({block:'center'});};d.append(b);}
  $('ara').closest('label').parentElement.after(d);
}).catch(()=>{});