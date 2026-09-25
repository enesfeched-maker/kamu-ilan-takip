const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.attrs={};this.classList={toggle(){}};this.hidden=false;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attrs[k]=v;}
  addEventListener(){} showModal(){this.open=true;} close(){this.open=false;} scrollIntoView(){} click(){} focus(){} select(){}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
get('sort').value='deadline';
const fixture=[
 {id:'one',baslik:'İSTANBUL ÜNİVERSİTESİ - BÜRO PERSONELİ',kurum:'İSTANBUL ÜNİVERSİTESİ',yer:'İstanbul',ilan_turu:'Sözleşmeli',son_tarih:'2099-01-01',ilk_gorulme:new Date().toISOString(),detay_guncelleme:new Date().toISOString(),link:'https://kariyerkapisi.gov.tr/IlanDetay?i=11111111-1111-4111-8111-111111111111',sartlar:[{kadro:'Büro',metin:'Muhasebe mezunu olmak'}]},
 {id:'two',baslik:'ESKİ İLAN',kurum:'Kurum',yer:'Ankara',son_tarih:'2000-01-01',link:'https://kariyerkapisi.gov.tr/IlanDetay?i=22222222-2222-4222-8222-222222222222'},
 {id:'three',baslik:'Destek Personeli',kurum:'Kurum 3',link:'https://kariyerkapisi.gov.tr/IlanDetay?i=33333333-3333-4333-8333-333333333333'}
];
const ctx=vm.createContext({URL,Date,Intl,Blob,console,Set,Number,String,Array,JSON,document:{title:'Portal',getElementById:get,createElement:t=>new Element(t),createTextNode:t=>t,querySelectorAll:()=>[],documentElement:{dataset:{}}},localStorage:{getItem:()=>null,setItem(){},removeItem(){}},location:{hash:'',href:'https://enesfeched-maker.github.io/kamu-ilan-takip/',reload(){}},navigator:{},window:{addEventListener(){}},matchMedia:()=>({matches:false}),setInterval(){},setTimeout(){},clearTimeout(){},fetch:async url=>({ok:true,json:async()=>url==='ilanlar.json'?{ilanlar:fixture,guncelleme:new Date().toISOString()}:{enabled:false}})});
const run=s=>vm.runInContext(s,ctx);
vm.runInContext(fs.readFileSync('docs/portal.js','utf8'),ctx);
(async()=>{await new Promise(r=>setImmediate(r));
assert.equal(run('loaded'),true);assert.equal(get('cards').children.length,2,'closed listing excluded');
get('search').value='istanbul buro';run('render()');assert.equal(get('cards').children.length,1,'Turkish search');
get('search').value='muhasebe';run('render()');assert.equal(get('cards').children.length,1,'condition search');
get('search').value='';get('city').value='Ankara';run('render()');assert.equal(get('cards').children.length,0);assert.equal(get('empty').hidden,false);
get('city').value='';run("saved.add('two');selectView('saved')");assert.equal(get('cards').children.length,1,'saved expired item remains accessible');
assert.equal(run("officialURL('https://evil.example/x')"),null);assert.equal(run("safeURL('javascript:alert(1)')"),null);
assert.equal(run("closed({son_zaman:new Date(Date.now()-1).toISOString()})"),true,'same-day expired exact time');
assert.equal(run("upcoming({baslangic_zaman:'2099-01-01'})"),true);
assert.match(run("calendarText(items[0])"),/DTSTART;VALUE=DATE:20990101/);assert.match(run("calendarText(items[0])"),/DTEND;VALUE=DATE:20990102/);
run('showDetail(items[0])');assert.equal(get('modal').open,true);assert.match(run('document.title'),/Büro/);
run("compared.add('one');compared.add('two');showComparison()");assert.equal(get('modal-body').children.length,1);
console.log('12 portal checks passed: filters, saved items, detail, comparison, Turkish search, dates, calendar and safe links.');
})().catch(e=>{console.error(e);process.exitCode=1;});
