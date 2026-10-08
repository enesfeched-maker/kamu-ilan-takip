const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.attrs={};this.classList={toggle(){},add(){}};this.hidden=false;this.style={setProperty(){}};this.className='';this.innerHTML='';this.textContent='';}
  append(...nodes){this.children.push(...nodes);} prepend(...nodes){this.children.unshift(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attrs[k]=v;} removeAttribute(){}
  querySelectorAll(){return this._qs||[];} querySelector(){return(this._qs||[])[0]||null;}
  replaceWith(){} remove(){}
  addEventListener(){} showModal(){this.open=true;} close(){this.open=false;} scrollIntoView(){} click(){} focus(){} select(){}
}
const text=n=>typeof n==='string'?n:(n.textContent||'')+(n.children||[]).map(text).join('');
/* Zaman çizelgesindeki ilan satırları (gün grupları içinde) */
const satirSay=n=>typeof n==='string'?0:(n.className==='satir'?1:0)+(n.children||[]).reduce((s,c)=>s+satirSay(c),0);
const bul=(n,f)=>typeof n==='string'?null:f(n)?n:(n.children||[]).map(c=>bul(c,f)).find(Boolean)||null;
const iso=d=>new Date(Date.now()+d*864e5).toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'});
const nowIso=new Date().toISOString();
const KK=n=>`https://kariyerkapisi.gov.tr/IlanDetay?i=${String(n).repeat(8)}-${String(n).repeat(4)}-4${String(n).repeat(3)}-8${String(n).repeat(3)}-${String(n).repeat(12)}`;
const fixture=[
 {id:'one',baslik:'İSTANBUL ÜNİVERSİTESİ - BÜRO PERSONELİ',kurum:'İSTANBUL ÜNİVERSİTESİ',yer:'İstanbul',ilan_turu:'Sözleşmeli',son_tarih:'2099-01-01',ilk_gorulme:nowIso,detay_guncelleme:nowIso,link:KK(1),sartlar:[{kadro:'Büro',metin:'Muhasebe mezunu olmak'}]},
 {id:'two',baslik:'ESKİ İLAN',kurum:'Kurum',yer:'Ankara',son_tarih:'2000-01-01',link:KK(2)},
 {id:'three',baslik:'Destek Personeli',kurum:'Kurum 3',link:KK(3)}
];
const row=(key,id,extra={})=>({key,id,manset:'Büro Personeli',ek:0,toplam:2,meslek:['30-genel.jpg'],logo:'',kurum:'İstanbul Üniversitesi',kurum_slug:'istanbul-universitesi',il:'İstanbul',iller:['İstanbul'],ogrenim:['lisans'],kpss:'kpss',puan_turleri:['P3'],taban_ref:{lisans:{unvan:'memur',medyan:81,n:9,donem:'2025-2/2026-1'}},son_tarih:iso(1),son_zaman:'',baslangic_zaman:'',ilk_gorulme:nowIso,durum:'today',ilan_turu:'',kategori:'',...extra});
const k=n=>KK(n).split('?i=')[1];
const liste={guncelleme:nowIso,sayilar:{acik:3,kadro:6,bugun_yeni:3},takvim:{},ilanlar:[
 row(k(1),'one',{ilan_turu:'Sözleşmeli Personel İlanları'}),
 row(k(4),'four',{il:'Ankara',iller:['Ankara'],son_tarih:iso(10),manset:'Zabıta',kategori:'belediye',ilan_turu:'Memur',taban_ref:{},ilk_gorulme:'2020-01-01T00:00:00+03:00',toplam:7}),
 row(k(5),'five',{il:'Ankara',iller:['Ankara'],ogrenim:['onlisans'],son_tarih:iso(0),manset:'Teknisyen',ilk_gorulme:'2020-01-01T00:00:00+03:00',puan_turleri:['P93']}),
 row(k(6),'six',{son_tarih:'',baslangic_zaman:new Date(Date.now()+864e5).toISOString().slice(0,19)+'+00:00',durum:'upcoming',ilk_gorulme:'2020-01-01T00:00:00+03:00',manset:'Yakında'}),
 row(k(7),'seven',{son_tarih:'2000-01-01',manset:'Kapanmış',ilk_gorulme:'2020-01-01T00:00:00+03:00'}),
 {key:'../evil',id:'x',manset:'<img src=x onerror=alert(1)>'}
]};
/* Her çağrı kendi tarayıcı bağlamını kurar: adres, hash ve yerel depolama ayrı tutulur. */
function make({href='https://kpsstercihi.com/?g=bugun',hash='',store={},liste:L=liste}={}){
 const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
 const stored=[],loc={hash:hash||new URL(href).hash,href};
 const ctx=vm.createContext({URL,URLSearchParams,Date,Intl,Blob,console,Set,Map,Number,String,Array,JSON,Promise,Error,isNaN,
  document:{title:'Portal',getElementById:get,createElement:t=>new Element(t),createTextNode:t=>t,querySelectorAll:()=>[],documentElement:{dataset:{}}},
  confirm:m=>{ctx.__confirmMsg=m;return ctx.__confirmCevap!==false;},
  localStorage:{getItem:k=>k in store?store[k]:null,setItem(k,v){store[k]=v;stored.push(k);},removeItem(k){delete store[k];},key:i=>Object.keys(store)[i]??null,get length(){return Object.keys(store).length;}},
  location:loc,history:{replaceState(a,b,u){ctx.__replaced=u;const n=new URL(u,loc.href);loc.href=n.href;loc.hash=n.hash;},pushState(a,b,u){ctx.__pushed=u;const n=new URL(u,loc.href);loc.href=n.href;loc.hash=n.hash;}},
  navigator:{},window:{innerWidth:1280,addEventListener(t,f){(ctx.__h[t]=ctx.__h[t]||[]).push(f);}},matchMedia:()=>({matches:false}),setInterval(){},setTimeout(){},clearTimeout(){},
  fetch:async url=>({ok:true,json:async()=>url==='ilanlar.json'?{ilanlar:fixture,guncelleme:nowIso}:url==='liste.json'?L:url==='sponsors.json'?{enabled:false}:{}})});
 ctx.__h={};get('p-ogrenim')._qs=['ortaogretim','onlisans','lisans'].map(v=>{const b=new Element('button');b.dataset.v=v;return b;});vm.runInContext(fs.readFileSync('docs/portal.js','utf8'),ctx);
 return{ctx,get,stored,loc,run:s=>vm.runInContext(s,ctx)};
}
const tick=async()=>{await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));};
(async()=>{
const T=make();const {ctx,get,run,stored}=T;await tick();
assert.equal(run('listeLoaded'),true);assert.equal(run('loaded'),false,'full records load lazily');await run('ensureFull()');assert.equal(run('loaded'),true);
assert.equal(ctx.__replaced,'/','?g=bugun stripped from URL');
assert.equal(run('tab'),'bugun','?g=bugun keeps Bugün');
// liste.json: bozuk kayıt (geçersiz anahtar) elenir
assert.equal(run('liste.length'),5,'invalid liste row dropped');
// ---- İlanlar: sorgu ayrıştırma / yazma
const J=s=>JSON.stringify(run(s));
const f1=JSON.parse(J("parseQuery('?q=b%C3%BCro&il=istanbul,Ankara,Atlantis&ogr=lisans&sb=2&tur=S%C3%B6zle%C5%9Fmeli&yeni=1&uygun=0&sira=yeni&arsiv=1')"));
assert.deepEqual(f1,{q:'büro',il:['İstanbul','Ankara'],ogr:'lisans',sb:'2',tur:'Sözleşmeli',kat:'',yeni:true,uygun:false,sira:'yeni',arsiv:true},'query parsed');
assert.deepEqual(JSON.parse(J("parseQuery('?ogr=x&sb=99&sira=zzz&uygun=7&il=foo')")),{q:'',il:[],ogr:'',sb:'',tur:'',kat:'',yeni:false,uygun:null,sira:'son',arsiv:false},'invalid values dropped');
assert.equal(J("parseQuery('?kat=memur').kat"),'"memur"');assert.equal(J("parseQuery('?kat=yok').kat"),'""');assert.equal(run("queryOf({...defaultF(),kat:'isci'},true)"),'kat=isci');
assert.equal(run("queryOf(parseQuery('?q=b%C3%BCro&il=istanbul,ankara&ogr=lisans&sb=2&yeni=1&uygun=0&sira=yeni'),true)"),'q=b%C3%BCro&il=istanbul%2Cankara&ogr=lisans&sb=2&yeni=1&uygun=0&sira=yeni','query serialized');
assert.equal(run("queryOf(defaultF(),true)"),'','defaults leave URL clean');
assert.equal(run("queryOf({...defaultF(),uygun:true},true)"),'','uygun default on with profile');assert.equal(run("queryOf({...defaultF(),uygun:true},false)"),'uygun=1');
assert.equal(run("queryHas('?g=bugun')"),false);assert.equal(run("queryHas('?il=ankara')"),true);
// ---- İlanlar: süzme (profil yok)
run("showTab('ilanlar')");
assert.equal(satirSay(get('cards')),4,'closed listing excluded');
assert.equal(get('result-count').textContent,'4 ilan');
const n=s=>run(`filterIlan(ilanBase(F),F,activeProfile()).list.length`);
run("F={...defaultF(),q:'istanbul buro'};render()");assert.equal(satirSay(get('cards')),1,'Turkish search');
run("F={...defaultF(),q:'muhasebe'};render()");assert.equal(satirSay(get('cards')),1,'condition search (full records)');
run("F={...defaultF(),q:'istanbul buro',il:['Ankara']};render()");assert.equal(satirSay(get('cards')),0);assert.equal(get('empty').hidden,false);assert.equal(get('clear').hidden,false);
run("F={...defaultF(),il:['Ankara']};render()");assert.equal(satirSay(get('cards')),2,'il filter');
run("F={...defaultF(),sb:'2'}");assert.equal(n(),2,'deadline <=2 days (today + tomorrow)');
run("F={...defaultF(),sb:'14'}");assert.equal(n(),3,'deadline <=14 days');
run("F={...defaultF(),sb:'yakinda'}");assert.equal(n(),1,'upcoming only');assert.equal(run("filterIlan(ilanBase(F),F,null).list[0].manset"),'Yakında');
run("F={...defaultF(),ogr:'onlisans'}");assert.equal(n(),1,'level filter');
run("F={...defaultF(),yeni:true}");assert.equal(n(),1,'only new');
run("F={...defaultF(),tur:'Sözleşmeli Personel'}");assert.equal(n(),1,'type from liste row, label normalized');assert.equal(J('turSecenekleri()'),'[[\"Memur\",1],[\"Sözleşmeli Personel\",1]]');
run("F={...defaultF(),ogr:'belediye'}");assert.equal(n(),1,'belediye via kategori');
run("F={...defaultF(),tur:'Yok'};render()");assert.equal(run('F.tur'),'','unknown type dropped');
run("F={...defaultF(),sira:'yeni'}");assert.equal(run("filterIlan(ilanBase(F),F,null).list[0].key"),k(1),'sort by newest');
run("F={...defaultF(),sira:'son'}");{const g=JSON.parse(J("filterIlan(ilanBase(F),F,null).list.map(o=>o.ilk_gorulme?istDate(Date.parse(o.ilk_gorulme)):'')"));assert.deepEqual(g,g.slice().sort().reverse(),'default timeline: newest publish day first, so the first page is never older days only');}
run("F={...defaultF(),arsiv:true}");assert.equal(n(),3,'archive view lists every full record, including the closed one');
// sayfalama + ilerleme
run("F=defaultF();shown=2;render()");assert.equal(satirSay(get('cards')),2,'2 rows + progress block');{const c=get('cards').children,son=c[c.length-1];assert.match(text(son),/2 \/ 4 ilan gösteriliyor/);assert.match(text(son),/Daha fazla göster/);}
run("shown=PAGE_SIZE;render()");assert.equal(satirSay(get('cards')),4);
// zaman çizelgesi: yayın gününe göre gruplar, en yeni gün önce; tarihli satırda başvuru aralığı
assert.equal(get('cards').children.length,2,'bugün + 2020-01-01 grupları');assert.equal(get('cards').children[0].id,'gun-'+iso(0));assert.match(text(get('cards').children[0]),/Bugün/);
assert.match(text(get('cards')),/Son gün/,'≤3 gün rozeti');assert.equal(run("tarihAraligi({son_tarih:'2026-10-20',baslangic_zaman:'2026-10-06T00:00:00+03:00',ilk_gorulme:''})"),'6 Ekim – 20 Ekim');assert.equal(run("tarihAraligi({son_tarih:'',ilk_gorulme:''})"),'Son tarih ilanda');
{const a=bul(get('cards'),n=>n.className==='satir-link');assert.match(a.href,/^ilan\/[A-Za-z0-9-]+\/$/,'satır ayrıntı sayfasına gider');}
// manşet: kapanmamış ilanlar, kadro büyükten küçüğe, kurum içi hariç
assert.equal(run("mansetSecimi().map(o=>o.toplam).join()"),'7,2,2,2','kadroya göre sıralı, kapanan hariç');
assert.equal(run("mansetBaslik({manset:'860 Gelir Uzman Yardımcısı',toplam:860}).b"),'860 Gelir Uzman Yardımcısı alacak');assert.deepEqual(JSON.parse(J("mansetBaslik({manset:'Destek Personeli, Tekniker',toplam:103})")),{b:'103 personel alacak',alt:'Destek Personeli, Tekniker'});assert.equal(run("mansetBaslik({manset:'Zabıta',toplam:7}).b"),'7 Zabıta alacak');
assert.match(text(get('manset')),/7 Zabıta alacak/);
// kategori ağacı: tür etiketinden üst kategori; seçim listeyi süzer
assert.equal(run("katOf({ilan_turu:'Sözleşmeli Personel İlanları'})"),'sozlesmeli');assert.equal(run("katOf({ilan_turu:'İşçi'})"),'isci');assert.equal(run("katOf({ilan_turu:'Kamu Personeli'})"),'memur');assert.equal(run("katOf({ilan_turu:'Askeri Personel'})"),'diger');assert.equal(run("katOf({ilan_turu:'',kategori:'akademik'})"),'akademik');
assert.match(text(get('kategoriler')),/Tüm İlanlar4/);assert.match(text(get('kategoriler')),/Memur1/);assert.match(text(get('kategoriler')),/Sözleşmeli Personel1/);
run("F={...defaultF(),kat:'memur'};render()");assert.equal(satirSay(get('cards')),1,'kategori süzgeci');assert.equal(get('liste-ad').textContent,'Memur');run("F=defaultF();render()");assert.equal(get('liste-ad').textContent,'Tüm İlanlar');
// URL eşitleme: İlanlar'dayken yazılır, başka sekmede temizlenir
run("F={...defaultF(),il:['Ankara'],ogr:'onlisans'};render()");assert.match(ctx.__replaced,/\?il=ankara&ogr=onlisans$/);
run("showTab('takvim')");assert.equal(ctx.__replaced,'/','filters cleared from URL on other tabs');
run("F=defaultF()");
// ---- profil ile: Profilime uygun, kaçış kapısı
run("profil={v:1,ogrenim:'lisans',puan_turu:'P3',puan:82.15,iller:['İstanbul'],tum_turkiye:false,bolum:'',t:'2026-10-04'};showTab('ilanlar')");
let res=JSON.parse(J("(()=>{const r=filterIlan(ilanBase(F),F,activeProfile());return{on:r.on,n:r.list.length,uyan:r.uyan,disinda:r.disinda}})()"));
assert.deepEqual(res,{on:true,n:2,uyan:2,disinda:2},'Profilime uygun default on');
assert.equal(satirSay(get('cards')),2);assert.match(text(get('disinda')),/Profilinin dışında 2 açık ilan daha/);assert.equal(get('disinda').hidden,false);
run("F.uygun=false;render()");assert.equal(satirSay(get('cards')),4);assert.equal(get('disinda').hidden,true);
assert.equal(run("queryOf(F,true)"),'uygun=0');
// alt düzey ilan 'uygun' içinde işaretlenir
assert.equal(run("(()=>{const r=filterIlan([{...liste[0],ogrenim:['onlisans'],puan_turleri:[]}],defaultF(),profil);return r.seviye.get(liste[0].key)})()"),'alt');
// Bugün'den derin bağlantılar
assert.equal(run("ilanLink('Tümü',{uygun:true}).href"),'./#ilanlar');
assert.equal(run("ilanLink('Son günler',{sb:'2',uygun:false}).href"),'?sb=2&uygun=0#ilanlar');
assert.equal(run("ilanLink('Yakında',{sb:'yakinda',uygun:false}).href"),'?sb=yakinda&uygun=0#ilanlar');
run("openIlanlar({sb:'2',uygun:false})");assert.equal(run('F.sb'),'2');assert.equal(run('F.uygun'),false);assert.equal(T.loc.hash,'#ilanlar','deep link navigates to İlanlar');assert.equal(get('v-ana').hidden,false,'İlanlar ana görünümde');assert.match(ctx.__pushed,/\?sb=2&uygun=0#ilanlar$/);assert.equal(run('tab'),'ilanlar');
// ---- Takvim
run("F=defaultF();saved.clear();showTab('takvim')");
const tg=JSON.parse(J("(()=>{const g=takvimGruplari(takvimRows('tumu'));return{keys:[...g.gr.keys()],tarihsiz:g.tarihsiz.length}})()"));
assert.deepEqual(tg,{keys:[iso(0),iso(1),iso(10)],tarihsiz:1},'grouped by deadline day, undated separate');
assert.equal(get('takvim-icerik').children.length,4,'3 day groups + Tarihi ilanda');
assert.match(text(get('takvim-icerik').children[3]),/Tarihi ilanda/);assert.match(text(get('takvim-icerik').children[0]),/1 ilan · 2 kadro · bu gün kapanıyor/);
assert.doesNotMatch(text(get('takvim-icerik').children[0]),/gün$/m);
const sg=JSON.parse(J("seritGunleri(takvimGruplari(takvimRows('tumu')).gr,new Set(['"+iso(1)+"']))"));
assert.equal(sg.length,14);assert.equal(sg[0].bugun,true);assert.equal(sg[0].acil,false,'today not orange');assert.equal(sg[1].acil,true);assert.equal(sg[1].kayitli,true);assert.equal(sg[10].c,1);assert.equal(sg[2].c,0);
assert.equal(get('takvim-serit').children.length,14);
const ay=JSON.parse(J("(()=>{const h=ayHucreleri(takvimGruplari(takvimRows('tumu')).gr,new Set(),0);return{say:h.hucreler.length,c:h.hucreler.find(x=>x.d==='"+iso(1)+"').c,sev:h.hucreler.find(x=>x.d==='"+iso(1)+"').seviye}})()"));
assert.equal(ay.c,1);assert.equal(ay.sev,1);
run("tkSeg='kayitli';renderTakvim()");assert.match(text(get('takvim-icerik')),/Kaydettiğin açık ilan yok/);
run("saved.add(liste[0].id);tkSeg='kayitli';renderTakvim()");assert.equal(get('takvim-icerik').children.length,1,'saved segment only shows saved');
run("tkSeg='uygun';renderTakvim()");assert.equal(get('takvim-icerik').children.length,2,'Bana uygun: 1 day group + undated upcoming');
run("tkSeg='tumu';saved.clear()");
// ---- Kayıtlı
run("saved.add('five');saved.add('four');saved.add('seven');saved.add('six');showTab('kayitli')");
assert.equal(JSON.parse(J("kayitliGruplari([liste[2],liste[1],liste[4],liste[3],{...liste[0],son_tarih:'2026-10-10'}]).map(g=>g.baslik)")).join(),'7 gün içinde kapanıyor,Daha sonra,Tarihi ilanda,Sona erdi','Kayıtlı groups');
assert.equal(get('kayitli-icerik').children.length,5,'toolbar + 4 groups');assert.match(text(get('kayitli-icerik').children[0]),/Takvimime ekle \(\.ics\)/);
assert.match(text(get('kayitli-icerik')),/Karşılaştır/);
assert.equal(get('compare-bar').hidden,true);run("compared.add('five');compared.add('four');renderCompare()");assert.equal(get('compare-bar').hidden,false,'compare lives on Kayıtlı');
run("showTab('ilanlar')");assert.equal(get('compare-bar').hidden,true,'no compare bar outside Kayıtlı');
assert.doesNotMatch(text(get('cards')),/Karşılaştır/,'İlanlar rows have no compare checkbox');
run("compared.clear();saved.clear();showTab('kayitli')");assert.match(text(get('kayitli-icerik')),/Henüz kaydettiğin ilan yok/);assert.match(text(get('kayitli-icerik')),/yer imi/);
// kayıtlı, süresi dolmuş ilan erişilebilir
run("saved.add('two');showTab('kayitli')");assert.ok(get('kayitli-icerik').children.length>=2,'saved expired item remains accessible');
assert.equal(run("officialURL('https://evil.example/x')"),null);assert.equal(run("safeURL('javascript:alert(1)')"),null);
assert.equal(run("closed({son_zaman:new Date(Date.now()-1).toISOString()})"),true,'same-day expired exact time');
assert.equal(run("upcoming({baslangic_zaman:'2099-01-01'})"),true);
assert.match(run("calendarText(items[0])"),/DTSTART;VALUE=DATE:20990101/);assert.match(run("calendarText(items[0])"),/DTEND;VALUE=DATE:20990102/);
assert.equal((run("calendarText([items[0],items[1],items[2]])").match(/BEGIN:VEVENT/g)||[]).length,2,'multi-event ics skips undated');
assert.doesNotMatch(run("calendarText([{...items[0],link:'https://evil.example/x'}])"),/URL:/,'unofficial URL never written to ics');
run('showDetail(items[0])');assert.equal(get('modal').open,true);assert.match(run('document.title'),/Büro/);
run("compared.add('one');compared.add('two');showComparison()");assert.equal(get('modal-body').children.length,1);
// doğrulama
assert.equal(run("cleanL({key:'a/b'})"),null);assert.equal(run("cleanL({key:'abc',meslek:['../x.jpg','01-yazilimci.jpg'],logo:'javascript:1'}).meslek.length"),1);assert.equal(run("cleanL({key:'abc',logo:'javascript:1'}).logo"),'');
assert.equal(run("Object.keys(cleanL({key:'abc',taban_ref:{lisans:{medyan:80,n:3},onlisans:{medyan:70,n:6}}}).taban_ref).join()"),'onlisans','n<5 reference dropped');
assert.equal(run("validProfile({v:1,ogrenim:'x'})"),null);assert.equal(run("validProfile({v:1,ogrenim:'lisans',iller:['Ankara','<b>'],puan:150}).iller.length"),1);
assert.equal(run("ekSi(1)"),'1’i');assert.equal(run("ekSi(30)"),'30’u');assert.equal(run("baslikTemiz('İlk Defa Atanmak Üzere Vhki Alımı İlanı')"),'VHKİ alımı');
// Bugün: profilsiz -> kurulum kartı, Telegram saati 09:00
run("profil=null;saved.clear();compared.clear();showTab('takvim')");
const tk=text(get('takvim-sol'));assert.match(tk,/Her sabah 09:00 civarı/);assert.doesNotMatch(tk,/08:30/);
run("showTab('bugun')");assert.match(text(get('suzgecler')),/^Filtreler/);assert.doesNotMatch(text(get('suzgecler')),/Profilini oluştur|Hesap gerekmez|profilime uygun/,'profilsiz: yan sütunda açıklama/profil kutusu yok');
// Profil: Senin için, taban sinyali, kayıt
run("profil={v:1,ogrenim:'lisans',puan_turu:'P3',puan:82.15,iller:['İstanbul'],tum_turkiye:false,bolum:'',t:'2026-10-04'};render()");
const b2=text(get('suzgecler'));
assert.match(b2,/Yalnız profilime uygun/);
assert.equal(run("uygun(liste[0],profil)"),'tam');assert.equal(run("uygun(liste[1],profil)"),false,'il mismatch');assert.equal(run("uygun(liste[2],profil)"),false,'il mismatch (onlisans listing in Ankara)');
assert.equal(run("uygun({...liste[0],ogrenim:['onlisans'],puan_turleri:[]},profil)"),'alt','lower level listing');assert.equal(run("uygun({...liste[0],ogrenim:['lisans']},{...profil,ogrenim:'onlisans'})"),false,'higher level listing excluded');assert.equal(run("uygun({...liste[1],il:'Türkiye Geneli',iller:[]},profil)"),'tam','nationwide matches every il');assert.equal(run("uygun({...liste[1],il:'',iller:[]},profil)"),'tam');
// puan türü ilanda varsa ve kullanıcınınkiyle uyuşmuyorsa sinyal gizlenir
assert.equal(run("sinyalOf({...liste[0],puan_turleri:['P93']})"),null);assert.match(text(run("sinyalOf({...liste[0],taban_ref:{lisans:{medyan:92.15,n:9}}})")),/Puanın, benzer kadroların taban medyanından 10,0 puan düşük/);
// kayıtlı son ziyaret doğrulaması
assert.equal(run("validVisit('2999-01-01T00:00:00Z')"),null,'future visit rejected');assert.equal(run("validVisit('x')"),null);assert.ok(run("validVisit('2026-10-02T05:00:00.000Z')")>0);
// Tüm Türkiye
run("profil.tum_turkiye=true");assert.equal(run("uygun(liste[1],profil)"),'tam');
// Son ziyaret 10 sn gecikmeli yazılır (burada setTimeout stub: yazılmamış olmalı)
assert.ok(!stored.includes('kit-son-ziyaret'),'last visit not written immediately');
// ---- Açılışta sorgu: İlanlar süzgeçlerle açılır
const B=make({href:'https://kpsstercihi.com/?il=ankara&sb=14&uygun=0',hash:''});await tick();
assert.equal(B.run('tab'),'ilanlar','query on load opens İlanlar');assert.equal(B.run("JSON.stringify(F.il)"),'["Ankara"]');assert.equal(B.run('F.sb'),'14');assert.equal(B.run('F.uygun'),false);
assert.match(B.ctx.__replaced,/#ilanlar$/,'hash set without extra history entry');assert.equal(satirSay(B.get('cards')),2,'Ankara + <=14 days (Zabıta, Teknisyen)');
assert.match(B.loc.href,/\?il=ankara&sb=14&uygun=0#ilanlar$/,'shareable URL kept');
const C=make({href:'https://kpsstercihi.com/?q=zab%C4%B1ta#takvim'});await tick();
assert.equal(C.run('tab'),'takvim','explicit hash tab wins over query');assert.equal(C.run('F.q'),'zabıta');
const D=make({href:'https://kpsstercihi.com/?g=bugun'});await tick();assert.equal(D.run('tab'),'bugun');assert.equal(D.run('queryHas(new URL(location.href).search)'),false);
const SD=h=>D.run('sourceDocument({belge_kopyasi:"'+h+'"})');{const p='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf';assert.equal(SD('https://kpsstercihi.com/belgeler/sbb/'+p),'https://kpsstercihi.com/belgeler/sbb/'+p,'yeni alan adi kabul');assert.equal(SD('https://enesfeched-maker.github.io/kamu-ilan-takip/belgeler/sbb/'+p),'https://enesfeched-maker.github.io/kamu-ilan-takip/belgeler/sbb/'+p,'eski onek kabul');assert.equal(SD('https://evil.test/belgeler/sbb/'+p),null,'yabanci alan reddedilir');}
// ---- Geri/ileri: yalnız sorgu değişse de sekme ve süzgeç eşitlenir (popstate)
const P=make({href:'https://kpsstercihi.com/#bugun'});await tick();
assert.equal(P.run('tab'),'bugun');assert.ok(P.ctx.__h.popstate&&P.ctx.__h.popstate.length,'popstate listener registered');
P.loc.href='https://kpsstercihi.com/?il=ankara&sb=14#ilanlar';P.loc.hash='#ilanlar';P.ctx.__h.popstate.forEach(f=>f());
assert.equal(P.run('tab'),'ilanlar','popstate switches tab');assert.equal(P.run('JSON.stringify(F.il)'),'["Ankara"]');assert.equal(P.run('F.sb'),'14');
P.loc.href='https://kpsstercihi.com/?il=istanbul#ilanlar';P.ctx.__h.popstate.forEach(f=>f());
assert.equal(P.run('JSON.stringify(F.il)'),'["İstanbul"]','query-only change re-parses filters');assert.equal(P.run('F.sb'),'');
P.loc.href='https://kpsstercihi.com/#bugun';P.loc.hash='#bugun';P.ctx.__h.popstate.forEach(f=>f());assert.equal(P.run('tab'),'bugun');
P.ctx.__h.hashchange.forEach(f=>f());assert.equal(P.run('tab'),'bugun','duplicate hashchange for same URL is ignored');
// ---- ?q=<unvan>#ilanlar
const Q=make({href:'https://kpsstercihi.com/?q=Zab%C4%B1ta#ilanlar'});await tick();
assert.equal(Q.run('tab'),'ilanlar');assert.equal(Q.get('search').value,'Zabıta');assert.equal(satirSay(Q.get('cards')),1,'?q= search applied');
// ---- ?profil=1 profil penceresini açar ve adresten silinir
const R1=make({href:'https://kpsstercihi.com/?profil=1'});await tick();
assert.equal(R1.get('profil-dialog').open,true);assert.equal(R1.loc.href,'https://kpsstercihi.com/');
// ---- ARIA ve arşiv çipi
// ---- yan sütun süzgeçleri
run("showTab('ilanlar')");assert.match(text(get('suzgecler')),/Sona erenler dahil/);
{const s=bul(get('suzgecler'),n=>n.id==='f-il');assert.ok(s,'il seçimi');s.value='ankara';s.onchange();assert.equal(run('JSON.stringify(F.il)'),'["Ankara"]');run("F=defaultF();render()");}
{const s=bul(get('suzgecler'),n=>n.id==='f-ogr');s.value='onlisans';s.onchange();assert.equal(run('F.ogr'),'onlisans');run("F=defaultF();render()");}
run("showTab('takvim')");assert.equal(get('v-ana').hidden,true);assert.equal(get('v-takvim').hidden,false);run("showTab('bugun')");assert.equal(get('v-ana').hidden,false,'Manşet ana görünüm');
// ---- ICS: CRLF kaçışı ve 75 sekizlik katlama
const ics=run("calendarText([{...items[0],ozet:'x',baslik:'Çok uzun başlık '.repeat(12)+'ş'}])");
assert.ok(ics.split('\r\n').every(l=>Buffer.byteLength(l)<=75),'ics lines folded to 75 octets');assert.match(ics,/\r\n [^\r\n]/,'continuation lines start with a space');
// ---- kayıtlı doğrulama ve rozet
const S=make({store:{'kit-saved':JSON.stringify(['one',5,'x'.repeat(81),'sbb-abc'])}});await tick();
assert.equal(S.run('[...saved].join()'),'one,sbb-abc','invalid saved entries dropped');
assert.equal(S.run("saved.clear(),saved.add(liste[0].id),saved.add('ghost'),savedCount()"),1,'badge counts only known ids');
// ---- kopya ilanlar (kaynaklar arası): ikincil satır her yerden çıkar, kimlikleri birincile eşlenir
const hanak=row(k(8),'eight',{manset:'Memur',kurum:'Hanak Belediyesi',kurum_slug:'hanak-belediyesi',il:'Ardahan',iller:['Ardahan'],son_tarih:iso(5),kaynak_sayisi:2,kaynaklar:['İŞKUR','ÇŞB']});
const hanak2=row(k(9),'nine',{manset:'Memur',kurum:'Hanak Belediye Başkanlığı',il:'Ardahan',iller:['Ardahan'],son_tarih:iso(5),kopya_of:k(8)});
const yetim=row(k(3),'three',{manset:'Yetim kopya',kopya_of:'yok-boyle-bir-anahtar',son_tarih:iso(6)});
liste.ilanlar.push(hanak,hanak2,yetim);
const K=make({store:{'kit-saved':JSON.stringify(['nine'])}});await tick();
assert.equal(K.run('listeTum.length'),8,'tüm satırlar saklanır');assert.equal(K.run('liste.length'),7,'ikincil satır listeden çıkar');
assert.equal(K.run("liste.some(o=>o.id==='nine')"),false);assert.equal(K.run("liste.some(o=>o.id==='three')"),true,'birincili olmayan kopya_of satırı gizlenmez');
assert.equal(K.run("lmap.get('"+k(8)+"').kaynaklar.join()"),'İŞKUR,ÇŞB');assert.equal(K.run("lmap.get('"+k(8)+"').kaynak_sayisi"),2);
assert.equal(K.run("isSaved(lmap.get('"+k(8)+"'))"),true,'ikincilin kayıtlı kimliği birincilde görünür');assert.equal(K.run('savedCount()'),1);
K.run("tab='kayitli';renderKayitli()");assert.equal((text(K.get('kayitli-icerik')).match(/Hanak/g)||[]).length,1,'Kayıtlı yalnız birincili gösterir');
assert.deepEqual(JSON.parse(K.run("JSON.stringify(filterIlan(ilanBase(defaultF()),{...defaultF(),q:'baskanligi'},null).list.map(o=>o.id))")),['eight'],'ikincilin metniyle birincil bulunur');
assert.equal(K.run("filterIlan(ilanBase(defaultF()),defaultF(),null).list.filter(o=>o.kurum.startsWith('Hanak')).length"),1,'İlanlar sayısında çift tek sayılır');
K.run("takvimRows('tumu')");assert.equal(K.run("takvimRows('tumu').filter(o=>o.kurum.startsWith('Hanak')).length"),1);
K.run("save(lmap.get('"+k(8)+"'))");assert.equal(K.run('[...saved].join()'),'','kaydı kaldırmak ikincil kimliği de siler');
K.run("tab='bugun';render()");assert.doesNotMatch(text(K.get('ilanlar')),/kaynağına erişimde sorun|24 saat içinde doğrulanmadı/,'ana sayfada uyarı kutusu yok');
// ---- görev yeri tekrarsız
assert.equal(run("yerMetni({yer:'ANKARA • ANKARA / MERKEZ'})"),'Ankara (Merkez)');
assert.equal(run("yerMetni({yer:'BOLU / GEREDE • BOLU / MENGEN • BOLU / MERKEZ'})"),'Bolu (Gerede, Mengen, Merkez)');
assert.equal(run("yerMetni({yer:'KOCAELİ, SAKARYA, YALOVA, BOLU, DÜZCE'})"),'Kocaeli, Sakarya +3');
assert.equal(run("yerMetni({yer:'ANKARA / ÇANKAYA',iller:['Ankara']})"),'Ankara (Çankaya)');assert.equal(run("yerMetni({yer:'Ankara'})"),'Ankara');
assert.equal(run("yerMetni({yer:'BAKANLIK MERKEZ TEŞKİLATI'})"),'Bakanlık Merkez Teşkilatı');assert.equal(run("yerMetni({},'Rize')"),'Rize');
// ================= Profil düzeltmeleri (4 durumlu uygun(), form, sayfa.js) =================
const sat=(n,extra={})=>row(k(n),'r'+n,{il:'Ankara',iller:['Ankara'],son_tarih:iso(3+n%5),manset:'Satır '+n,taban_ref:{},...extra});
const lisansRow=sat(11,{ogrenim:['lisans'],puan_turleri:[],manset:'Lisans satırı'});
const onlisansRow=sat(12,{ogrenim:['onlisans'],puan_turleri:[],manset:'Önlisans satırı',son_tarih:iso(2)});
const liseRow=sat(13,{ogrenim:['ortaogretim'],puan_turleri:[],manset:'Lise satırı'});
const unk=sat(14,{ogrenim:[],puan_turleri:[],manset:'Bilinmeyen satır'});
const p3only=sat(15,{ogrenim:[],puan_turleri:['P3'],manset:'P3 satırı'});
const ici=sat(16,{ogrenim:[],puan_turleri:[],kurum_ici:true,manset:'Kurum içi sınav'});
const multi=sat(17,{iller:['Antalya','Burdur'],il:'Antalya +1',ogrenim:['lisans'],puan_turleri:[],manset:'Çok il'});
const ulusalRow=sat(18,{iller:[],il:'',ogrenim:['lisans'],puan_turleri:[],manset:'Ulusal'});
const L2={...liste,ilanlar:[lisansRow,onlisansRow,liseRow,unk,p3only,ici,multi,ulusalRow]};
const PR=(ogrenim,extra={})=>({v:1,ogrenim,puan_turu:ogrenim==='onlisans'?'P93':ogrenim==='ortaogretim'?'P94':'P3',puan:75.5,iller:['Ankara'],tum_turkiye:false,bolum:'',t:'2026-10-04',...extra});
const Z=make({liste:L2,store:{'kit-profil':JSON.stringify(PR('onlisans')),'kit-son-ziyaret':JSON.stringify('2020-01-01T00:00:00.000Z')}});await tick();
const U=(row_,p)=>Z.run(`uygun(listeTum.find(o=>o.id==='${row_.id}'),${JSON.stringify(p)})`);
const onlAnk=PR('onlisans'),lisAnk=PR('lisans'),lisAnkara=lisAnk;
// 1) düzeyi okunamayan ilan hiçbir profile sessizce uymaz; "okunamayan N ilan" bağlantısı
assert.equal(U(unk,onlAnk),'bilinmiyor');
Z.run("showTab('bugun')");
assert.equal(Z.run("filterIlan(ilanBase(F),F,activeProfile()).list.some(o=>o.manset==='Bilinmeyen satır')"),false,'unknown-level row not listed as uygun');assert.match(text(Z.get('filter-summary')),/1 ilanın öğrenim şartı okunamadı/);
assert.equal(Z.run("queryOf({...defaultF(),...bilinmiyorYama(activeProfile())},true)"),'il=ankara&ogr=bilinmiyor&uygun=0');
// bağlantının açtığı liste tam olarak o N satırdır
Z.run("openIlanlar({ogr:'bilinmiyor',uygun:false,il:['Ankara']})");assert.deepEqual(JSON.parse(Z.run("JSON.stringify(filterIlan(ilanBase(F),F,activeProfile()).list.map(o=>o.manset))")),['Bilinmeyen satır']);
// 2) puan türü düzeyi ima eder
assert.equal(U(p3only,onlAnk),false);assert.equal(U(p3only,lisAnk),'tam');
// 3) düzey kuralları ve sıralama
assert.equal(U(lisansRow,PR('ortaogretim')),false);assert.equal(U(liseRow,PR('ortaogretim')),'tam');assert.equal(U(onlisansRow,lisAnk),'alt');assert.equal(U(lisansRow,lisAnk),'tam');
assert.equal(Z.run("rowLevels({ogrenim:['onlisans'],puan_turleri:['P3']}).join()"),'onlisans,lisans');
// 4) kurum içi sınav
for(const o of ['ortaogretim','onlisans','lisans'])assert.equal(U(ici,PR(o)),false,'kurum içi sınav kimseye uygun değil');
// kurum içi ilan Bugün bölümlerinde ve açık ilan sayısında yoktur (İlanlar listesinde rozetle kalır)
assert.equal(Z.run("mansetSecimi().some(o=>o.kurum_ici)"),false,'kurum içi: manşette yok');
assert.equal(Z.run("listeTum.some(o=>o.kurum_ici)"),true,'kurum içi: İlanlar için listede durur');
// 5) sayılar tüm yüzeylerde aynı; alt, tam'dan sonra
Z.run(`profil=validProfile(${JSON.stringify(lisAnk)});F=defaultF();showTab('bugun')`);
const sn=Z.run("filterIlan(ilanBase(defaultF()),defaultF(),activeProfile()).uyan");
assert.equal(sn,Z.run("takvimRows('uygun').length"),'Profilime uygun = Takvim Bana uygun');assert.equal(sn,5);
assert.equal(Z.run("filterIlan(ilanBase(defaultF()),defaultF(),activeProfile()).list.map(o=>o.manset).join()"),'P3 satırı,Lisans satırı,Ulusal,Önlisans satırı,Lise satırı','İlanlar: alt tam satırlardan sonra, tarih sırasında önde olsa da');
assert.match(text(Z.get('suzgecler')),new RegExp('Yalnız profilime uygun '+sn),'yan sütun aynı sayıyı kullanır');
Z.run("F=defaultF();showTab('ilanlar');render()");assert.match(text(Z.get('filter-summary')),/1 ilanın öğrenim şartı okunamadı/);assert.match(text(Z.get('filter-summary')),/göster/);
// 6) il seçilmemiş = tüm Türkiye
assert.equal(U(multi,{...lisAnk,iller:[],tum_turkiye:false}),'tam');assert.equal(U(multi,lisAnk),false,'il seçili ve eşleşmiyorsa dışarıda');assert.equal(U(multi,{...lisAnk,iller:['Burdur']}),'tam');
assert.equal(U(ulusalRow,lisAnk),'tam');
// Tüm Türkiye açıkken seçilen iller öne alınır
Z.run(`profil=validProfile(${JSON.stringify({...lisAnk,tum_turkiye:true})})`);{const s=Z.run("filterIlan(ilanBase(defaultF()),defaultF(),activeProfile()).list.map(o=>o.manset)");assert.ok(s.indexOf('Çok il')>s.indexOf('Lisans satırı'),'seçili il önce');assert.equal(s[s.length-1],'Lise satırı');}
// 7) validProfile: düzeyle uyumlu puan türü
const vp=(o,t)=>Z.run(`validProfile({v:1,ogrenim:'${o}',puan_turu:${JSON.stringify(t)}}).puan_turu`);
assert.equal(vp('lisans','P94'),'P3');assert.equal(vp('onlisans','P3'),'P93');assert.equal(vp('lisans','P999'),'P3');assert.equal(vp('lisans','P25'),'P25');assert.equal(vp('ortaogretim','P93'),'P94');
// sinyal: puan türü düzeyin taban tablosuyla aynı değilse gösterilmez
Z.run(`profil=validProfile(${JSON.stringify({...lisAnk,puan_turu:'P25'})})`);assert.equal(Z.run("sinyalOf({...listeTum[0],puan_turleri:[],taban_ref:{lisans:{medyan:70,n:9}}})"),null);
Z.run(`profil=validProfile(${JSON.stringify(lisAnk)})`);assert.match(text(Z.run("sinyalOf({...listeTum[0],puan_turleri:[],taban_ref:{lisans:{medyan:80,n:9}}})")),/Puanın, benzer kadroların taban medyanından 4,5 puan düşük/);assert.match(text(Z.run("sinyalOf({...listeTum[0],puan_turleri:[],taban_ref:{lisans:{medyan:80,n:9}}})")),/4,5 puan geride/);
// 11) puan gösterimi
assert.equal(Z.run("puanTr(75.5)"),'75,5');assert.equal(Z.run("puanTr(75)"),'75');assert.equal(Z.run("puanTr(75.47987)"),'75,47987');assert.equal(Z.run("puanTr(82.15)"),'82,15');
// 9) + 8) + 12) form
const F1=make({liste:L2});await tick();
F1.run("globalThis.__nd=0;{const _n=notify;notify=function(t){if($('profil-dialog').open)__nd++;return _n(t);};}");
F1.get('p-hata').hidden=true;const btn=v=>F1.get('p-ogrenim')._qs.find(b=>b.dataset.v===v);
F1.run('openProfile()');
assert.equal(F1.get('p-puan').disabled,true,'düzey seçilmeden puan alanı kapalı');assert.equal(F1.get('p-tur').children.length,0,'düzey seçilmeden P3 önseçili değil');
F1.run('saveProfile()');assert.equal(F1.get('p-hata').hidden,false);assert.match(F1.get('p-hata').textContent,/Önce öğrenim düzeyini seç/);assert.equal(F1.run('profil'),null);
btn('onlisans').onclick();
assert.equal(F1.get('p-puan').disabled,false);assert.deepEqual(F1.get('p-tur').children.map(o=>o.value),['P93'],'Önlisans: tek varsayılan');assert.equal(F1.get('p-tur-a').children.length,0,'Önlisans için P1–P48 yok');
btn('lisans').onclick();assert.deepEqual(F1.get('p-tur').children.map(o=>o.value),['P3','A'],'Lisans: P3 + Diğer');assert.equal(F1.get('p-tur-a').children.length,48);assert.equal(F1.get('p-tur-a').hidden,true);
F1.get('p-tur').value='A';F1.get('p-tur').onchange();F1.get('p-tur-a').value='P25';assert.equal(F1.get('p-tur-a').hidden,false);
btn('onlisans').onclick();btn('lisans').onclick();assert.equal(F1.get('p-tur').value,'P3','düzey değişince tür sıfırlanır');
btn('onlisans').onclick();
for(const bad of ['1e2','0x50','120','abc','75,5,3','0','39,9','-3','1.234,5','75,555555','Infinity']){
 F1.get('p-puan').value=bad;F1.get('p-hata').hidden=true;F1.run('saveProfile()');
 assert.equal(F1.get('p-hata').hidden,false,'hata görünür: '+bad);assert.match(F1.get('p-hata').textContent,/40–100/,bad);assert.equal(F1.run('profil'),null,'kaydedilmedi: '+bad);assert.equal(F1.get('p-puan').attrs['aria-invalid'],'true');}
assert.equal(F1.get('toast').textContent,'','hata toast ile gösterilmez');assert.equal(F1.run('__nd'),0,'diyalog açıkken notify çağrılmaz');
for(const [raw,beklenen] of [['75,5',75.5],['75.47987',75.47987],[' 82,15 ',82.15],['75',75],['100',100],['40',40]]){
 F1.get('p-puan').value=raw;F1.run('saveProfile()');assert.equal(F1.run('profil&&profil.puan'),beklenen,'kabul: '+raw);F1.run('profil=null;openProfile();draft.ogrenim=\'onlisans\';fillForm()');}
assert.equal(F1.run("profilHataTemizle(),$('p-hata').hidden"),true);
// il önek tamamlama
F1.run("openProfile();draft.ogrenim='lisans';fillForm()");
F1.get('p-il').value='ank';F1.get('p-il').onkeydown({key:'Enter',preventDefault(){}});assert.equal(F1.run("draft.iller.join()"),'Ankara','ank + Enter -> Ankara');
F1.get('p-il').value='İzmir';assert.equal(F1.run('addIl()'),true);assert.equal(F1.run("draft.iller.join()"),'Ankara,İzmir');
F1.get('p-il').value='ka';assert.equal(F1.run('addIl()'),false);assert.match(F1.get('p-hata').textContent,/Birden fazla il eşleşiyor/);assert.equal(F1.get('p-il').attrs['aria-invalid'],'true');
F1.get('p-il').value='zzz';assert.equal(F1.run('addIl()'),false);assert.match(F1.get('p-hata').textContent,/İl adını listeden seç/);
// 13) Gizlilik temizle her kit-* anahtarını siler
const gStore={'kit-profil':'{}','kit-theme':'"dark"','kit-saved':'[]','kit-puan-duzey':'"lisans"','kit-xyz':'1','baska':'1'};const G=make({store:gStore});await tick();
G.run("showArticle('bilgi/gizlilik')");
const bulBtn=n=>n.tag==='button'?n:(n.children||[]).map(bulBtn).find(Boolean);const gb=bulBtn(G.get('modal-body').children[0]);assert.ok(gb);gb.onclick();
assert.deepEqual(Object.keys(gStore),['baska'],'her kit-* anahtarı silindi, başkaları kaldı');
// 13b) Profili sıfırla: yalnız kit-profil gider; ekran profilsiz varsayılana döner
const rStore={'kit-profil':JSON.stringify(PR('lisans')),'kit-saved':JSON.stringify(['abc']),'kit-theme':'"dark"','kit-son-ziyaret':JSON.stringify('2020-01-01T00:00:00.000Z')};
const RS=make({store:rStore});await tick();
RS.run("showTab('bugun')");assert.ok(RS.run('activeProfile()'),'profil var');assert.match(text(RS.get('suzgecler')),/Yalnız profilime uygun/);
RS.run('openProfile()');assert.equal(RS.get('p-sifirla-kutu').hidden,false,'profil varken sıfırla düğmesi görünür');assert.equal(RS.get('profil-dialog').open,true);
RS.ctx.__confirmCevap=false;RS.get('p-sifirla').onclick();assert.equal(RS.ctx.__confirmMsg,'Profil tercihlerin silinsin mi?');assert.ok('kit-profil' in rStore,'onay verilmezse silinmez');assert.ok(RS.run('activeProfile()'));
RS.ctx.__confirmCevap=true;RS.get('p-sifirla').onclick();
assert.ok(!('kit-profil' in rStore),'kit-profil silindi');assert.deepEqual(Object.keys(rStore).sort(),['kit-saved','kit-son-ziyaret','kit-theme'],'diğer anahtarlar yerinde');
assert.equal(rStore['kit-saved'],JSON.stringify(['abc']));assert.equal(rStore['kit-theme'],'"dark"');
assert.equal(RS.run('activeProfile()'),null);assert.equal(RS.get('profil-dialog').open,false,'pencere kapandı');
assert.doesNotMatch(text(RS.get('suzgecler')),/Yalnız profilime uygun/,'profil süzgeci kalktı');
RS.run("showTab('ilanlar')");assert.equal(RS.run("filterIlan(ilanBase(F),F,activeProfile()).on"),false,'eşleşme rozeti/filtresi kapalı');
RS.run('openProfile()');assert.equal(RS.get('p-sifirla-kutu').hidden,true,'profil yokken düğme gizli');
// 14) sayfa.js: ayrıntı sayfası "Senin için"
function sayfaYap(dataset,profilVeri){
 const hedef=new Element('div');hedef.getAttribute=a=>a==='data-ana'?'../../?profil=1':null;
 const senin=new Element('section');senin.dataset=dataset;senin.querySelector=s=>s==='[data-profil]'?hedef:null;
 const doc={getElementById:id=>id==='senin'?senin:null,createElement:t=>new Element(t),querySelector:()=>null,querySelectorAll:()=>[],documentElement:{dataset:{}}};
 const st={'kit-profil':JSON.stringify(profilVeri)};
 const c=vm.createContext({document:doc,localStorage:{getItem:k=>k in st?st[k]:null,setItem(){},removeItem(){}},Date,Intl,JSON,Array,Number,String,Math,isNaN,isFinite,RegExp,parseFloat});
 vm.runInContext(fs.readFileSync('docs/sayfa.js','utf8'),c);return text(hedef);}
const sd={ogr:'lisans',pt:'',il:'Antalya +1',iller:'Antalya,Burdur',ref:'{}'};
assert.match(sayfaYap(sd,PR('lisans',{iller:['Burdur']})),/Görev yeri Burdur seçtiğin illerden biri/,'çoklu il: ikinci il eşleşir');
assert.match(sayfaYap(sd,PR('lisans',{iller:['Ankara']})),/seçtiğin illerin dışında/);
assert.match(sayfaYap({...sd,il:'',iller:''},PR('lisans')),/Görev yeri: ülke geneli \/ ilanda belirtilmemiş/);
assert.match(sayfaYap({...sd,ogr:'',pt:'P3'},PR('onlisans')),/İlan Lisans düzeyi arıyor; senin düzeyin: Önlisans/,'puan türünden çıkan düzey');
assert.match(sayfaYap({...sd,ogr:'',pt:''},PR('lisans')),/İlanda öğrenim düzeyi belirtilmemiş/);
assert.match(sayfaYap({...sd,kurumIci:'1'},PR('lisans')),/Kurum içi yeterlik sınavı/);
assert.match(sayfaYap({...sd,pt:'P3',ref:JSON.stringify({lisans:{medyan:80,n:9}})},PR('lisans',{puan_turu:'P25'})),/P3 puanı arıyor; puan türün P25/);
assert.doesNotMatch(sayfaYap({...sd,pt:'',ref:JSON.stringify({lisans:{medyan:80,n:9}})},PR('lisans',{puan_turu:'P25'})),/medyan/,'P25 profiline P3 medyanı gösterilmez');
assert.match(sayfaYap({...sd,ref:JSON.stringify({lisans:{medyan:80,n:9}})},PR('lisans')),/Puanın, benzer kadroların taban medyanından 4,5 puan düşük/);
console.log('portal checks passed: timeline groups, manşet, kategori ağacı, query sync + popstate, sidebar filters, liste-based tür/kategori, profile match, pagination, Takvim, Kayıtlı groups, compare only on Kayıtlı, folded ics, validated saved ids, ?profil=1, ?q=.');
})().catch(e=>{console.error(e);process.exitCode=1;});
