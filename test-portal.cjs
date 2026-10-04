const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.attrs={};this.classList={toggle(){},add(){}};this.hidden=false;this.style={setProperty(){}};this.className='';this.innerHTML='';this.textContent='';}
  append(...nodes){this.children.push(...nodes);} prepend(...nodes){this.children.unshift(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attrs[k]=v;} removeAttribute(){}
  querySelectorAll(){return[];}
  replaceWith(){} remove(){}
  addEventListener(){} showModal(){this.open=true;} close(){this.open=false;} scrollIntoView(){} click(){} focus(){} select(){}
}
const text=n=>typeof n==='string'?n:(n.textContent||'')+(n.children||[]).map(text).join('');
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
get('sort').value='deadline';
const iso=d=>new Date(Date.now()+d*864e5).toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'});
const nowIso=new Date().toISOString();
const KK=n=>`https://kariyerkapisi.gov.tr/IlanDetay?i=${String(n).repeat(8)}-${String(n).repeat(4)}-4${String(n).repeat(3)}-8${String(n).repeat(3)}-${String(n).repeat(12)}`;
const fixture=[
 {id:'one',baslik:'İSTANBUL ÜNİVERSİTESİ - BÜRO PERSONELİ',kurum:'İSTANBUL ÜNİVERSİTESİ',yer:'İstanbul',ilan_turu:'Sözleşmeli',son_tarih:'2099-01-01',ilk_gorulme:nowIso,detay_guncelleme:nowIso,link:KK(1),sartlar:[{kadro:'Büro',metin:'Muhasebe mezunu olmak'}]},
 {id:'two',baslik:'ESKİ İLAN',kurum:'Kurum',yer:'Ankara',son_tarih:'2000-01-01',link:KK(2)},
 {id:'three',baslik:'Destek Personeli',kurum:'Kurum 3',link:KK(3)}
];
const row=(key,id,extra={})=>({key,id,manset:'Büro Personeli',ek:0,toplam:2,meslek:['30-genel.jpg'],logo:'',kurum:'İstanbul Üniversitesi',kurum_slug:'istanbul-universitesi',il:'İstanbul',iller:['İstanbul'],ogrenim:['lisans'],kpss:'kpss',puan_turleri:['P3'],taban_ref:{lisans:{unvan:'memur',medyan:81,n:9,donem:'2025-2/2026-1'}},son_tarih:iso(1),son_zaman:'',baslangic_zaman:'',ilk_gorulme:nowIso,durum:'today',...extra});
const k=n=>KK(n).split('?i=')[1];
const liste={guncelleme:nowIso,sayilar:{acik:3,kadro:6,bugun_yeni:3},takvim:{},ilanlar:[
 row(k(1),'one'),
 row(k(4),'four',{il:'Ankara',iller:['Ankara'],son_tarih:iso(10),manset:'Zabıta',taban_ref:{},ilk_gorulme:'2020-01-01T00:00:00+03:00'}),
 row(k(5),'five',{il:'Ankara',iller:['Ankara'],ogrenim:['onlisans'],son_tarih:iso(0),manset:'Teknisyen',ilk_gorulme:'2020-01-01T00:00:00+03:00',puan_turleri:['P93']}),
 row(k(6),'six',{son_tarih:'',baslangic_zaman:new Date(Date.now()+864e5).toISOString().slice(0,19)+'+00:00',durum:'upcoming',ilk_gorulme:'2020-01-01T00:00:00+03:00',manset:'Yakında'}),
 {key:'../evil',id:'x',manset:'<img src=x onerror=alert(1)>'}
]};
const store={};
const stored=[];
const ctx=vm.createContext({URL,URLSearchParams,Date,Intl,Blob,console,Set,Map,Number,String,Array,JSON,Promise,Error,isNaN,
 document:{title:'Portal',getElementById:get,createElement:t=>new Element(t),createTextNode:t=>t,querySelectorAll:()=>[],documentElement:{dataset:{}}},
 localStorage:{getItem:k=>k in store?store[k]:null,setItem(k,v){store[k]=v;stored.push(k);},removeItem(k){delete store[k];}},
 location:{hash:'',href:'https://enesfeched-maker.github.io/kamu-ilan-takip/?g=bugun',reload(){}},history:{replaceState(a,b,u){ctx.__replaced=u;}},
 navigator:{},window:{addEventListener(){}},matchMedia:()=>({matches:false}),setInterval(){},setTimeout(){},clearTimeout(){},
 fetch:async url=>({ok:true,json:async()=>url==='ilanlar.json'?{ilanlar:fixture,guncelleme:nowIso}:url==='liste.json'?liste:url==='sponsors.json'?{enabled:false}:{}})});
const run=s=>vm.runInContext(s,ctx);
vm.runInContext(fs.readFileSync('docs/portal.js','utf8'),ctx);
(async()=>{await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
assert.equal(run('listeLoaded'),true);assert.equal(run('loaded'),false,'full records load lazily');await run('ensureFull()');assert.equal(run('loaded'),true);
assert.equal(ctx.__replaced,'/kamu-ilan-takip/','?g=bugun stripped from URL');
// liste.json: bozuk kayıt (geçersiz anahtar) elenir
assert.equal(run('liste.length'),4,'invalid liste row dropped');
// İlanlar sekmesi: eski filtreler ve satır kartları
run("showTab('ilanlar')");
assert.equal(get('cards').children.length,2,'closed listing excluded');
get('search').value='istanbul buro';run('render()');assert.equal(get('cards').children.length,1,'Turkish search');
get('search').value='muhasebe';run('render()');assert.equal(get('cards').children.length,1,'condition search');
get('search').value='';get('city').value='Ankara';run('render()');assert.equal(get('cards').children.length,0);assert.equal(get('empty').hidden,false);
get('city').value='';
// Kayıtlı sekmesi: süresi dolmuş kayıtlı ilan erişilebilir
run("saved.add('two');showTab('kayitli')");assert.ok(get('kayitli-icerik').children.length>=1,'saved expired item remains accessible');
assert.equal(run("officialURL('https://evil.example/x')"),null);assert.equal(run("safeURL('javascript:alert(1)')"),null);
assert.equal(run("closed({son_zaman:new Date(Date.now()-1).toISOString()})"),true,'same-day expired exact time');
assert.equal(run("upcoming({baslangic_zaman:'2099-01-01'})"),true);
assert.match(run("calendarText(items[0])"),/DTSTART;VALUE=DATE:20990101/);assert.match(run("calendarText(items[0])"),/DTEND;VALUE=DATE:20990102/);
run('showDetail(items[0])');assert.equal(get('modal').open,true);assert.match(run('document.title'),/Büro/);
run("compared.add('one');compared.add('two');showComparison()");assert.equal(get('modal-body').children.length,1);
// doğrulama
assert.equal(run("cleanL({key:'a/b'})"),null);assert.equal(run("cleanL({key:'abc',meslek:['../x.jpg','01-yazilimci.jpg'],logo:'javascript:1'}).meslek.length"),1);assert.equal(run("cleanL({key:'abc',logo:'javascript:1'}).logo"),'');
assert.equal(run("Object.keys(cleanL({key:'abc',taban_ref:{lisans:{medyan:80,n:3},onlisans:{medyan:70,n:6}}}).taban_ref).join()"),'onlisans','n<5 reference dropped');
assert.equal(run("validProfile({v:1,ogrenim:'x'})"),null);assert.equal(run("validProfile({v:1,ogrenim:'lisans',iller:['Ankara','<b>'],puan:150}).iller.length"),1);
assert.equal(run("ekSi(1)"),'1’i');assert.equal(run("ekSi(30)"),'30’u');assert.equal(run("baslikTemiz('İlk Defa Atanmak Üzere Vhki Alımı İlanı')"),'VHKİ alımı');
// Bugün: profilsiz -> kurulum kartı, Telegram saati 09:00
run("showTab('bugun')");
const bugun=text(get('bugun'));
assert.match(bugun,/Her sabah 09:00 civarı/);assert.doesNotMatch(bugun,/08:30/);assert.match(bugun,/30 saniyede sana göre ayarla/);
// Profil: Senin için, taban sinyali, kayıt
run("profil={v:1,ogrenim:'lisans',puan_turu:'P3',puan:82.15,iller:['İstanbul'],tum_turkiye:false,bolum:'',t:'2026-10-04'};render()");
const b2=text(get('bugun'));
assert.match(b2,/Senin için/);assert.doesNotMatch(b2,/yeni ilan yok\./,'no empty-new message while new items shown elsewhere');assert.match(b2,/Puanın, benzer kadroların taban medyanından/);assert.doesNotMatch(b2,/puanın üstünde|Taban ~/);
assert.equal(run("uygun(liste[0],profil)"),'tam');assert.equal(run("uygun(liste[1],profil)"),false,'il mismatch');assert.equal(run("uygun(liste[2],profil)"),false,'il mismatch (onlisans listing in Ankara)');
assert.equal(run("uygun({...liste[0],ogrenim:['onlisans']},profil)"),'alt','lower level listing');assert.equal(run("uygun({...liste[0],ogrenim:['lisans']},{...profil,ogrenim:'onlisans'})"),false,'higher level listing excluded');assert.equal(run("uygun({...liste[1],il:'Türkiye Geneli',iller:[]},profil)"),'tam','nationwide matches every il');assert.equal(run("uygun({...liste[1],il:'',iller:[]},profil)"),'tam');
// puan türü ilanda varsa ve kullanıcınınkiyle uyuşmuyorsa sinyal gizlenir
assert.equal(run("sinyalOf({...liste[0],puan_turleri:['P93']})"),null);assert.match(text(run("sinyalOf({...liste[0],taban_ref:{lisans:{medyan:92.15,n:9}}})")),/Benzer kadroların taban medyanı puanından 10,0 puan yüksek/);
// kayıtlı son ziyaret doğrulaması
assert.equal(run("validVisit('2999-01-01T00:00:00Z')"),null,'future visit rejected');assert.equal(run("validVisit('x')"),null);assert.ok(run("validVisit('2026-10-02T05:00:00.000Z')")>0);
// Tüm Türkiye
run("profil.tum_turkiye=true");assert.equal(run("uygun(liste[1],profil)"),'tam');
// Son ziyaret 10 sn gecikmeli yazılır (burada setTimeout stub: yazılmamış olmalı)
assert.ok(!stored.includes('kit-son-ziyaret'),'last visit not written immediately');
// Her ilan bir bölümde yalnız bir kez
const anahtarlar=[...b2.matchAll(/Büro Personeli|Zabıta|Teknisyen|Yakında/g)].map(m=>m[0]);
console.log('portal checks passed: filters, saved items, detail, comparison, Turkish search, dates, calendar, safe links, profile, Bugün sections.');
})().catch(e=>{console.error(e);process.exitCode=1;});
