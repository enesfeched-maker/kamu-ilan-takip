'use strict';
const sourceDocument = i => /^https:\/\/(?:kpsstercihi\.com|enesfeched-maker\.github\.io\/kamu-ilan-takip)\/belgeler\/sbb\/[a-f0-9]{64}\.pdf$/.test(i.belge_kopyasi||'')?i.belge_kopyasi:null;
const $ = id => document.getElementById(id);
/* Çerezsiz ziyaret istatistiği (a.js): yüklenmediyse ya da kapalıysa sessizce hiçbir şey yapmaz. */
const A=(t,p)=>{try{if(typeof window!=='undefined'&&window.kpssA)window.kpssA(t,p);}catch{}};
let izModal=false,aramaZaman=null,aramaSon='',sonSayi=0;
const E = (tag, cls, text) => { const n=document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; };
const normalize = v => String(v||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
const proper = v => String(v||'').toLocaleLowerCase('tr-TR').replace(/(^|[\s(/-])([a-zçğıöşü])/g,(_,a,b)=>a+b.toLocaleUpperCase('tr-TR')).replace(/(\S\s)(Ve|İle|Veya)(?=\s)/g,(_,a,b)=>a+b.toLocaleLowerCase('tr-TR')).replace(/\bkpss\b/gi,'KPSS').replace(/\b4\/b\b/gi,'4/B');
const kurumAdi = v => {let s=proper(v);for(const m of String(v||'').matchAll(/\(([A-ZÇĞİÖŞÜ0-9]{2,8})\)/g))s=s.replace('('+proper(m[1])+')','('+m[1]+')');return s;};
const safeURL = v => {try{const u=new URL(v);return u.protocol==='https:'?u.href:null;}catch{return null;}};
const officialURL = v => {const u=safeURL(v);return u&&['kariyerkapisi.gov.tr','kamuilan.sbb.gov.tr','www.iskur.gov.tr','iskur.gov.tr','yerelyonetimler.csb.gov.tr'].includes(new URL(u).hostname)&&!new URL(u).username&&!new URL(u).password?u:null;};
const trDate = v => v ? new Date(v.length===10?v+'T12:00:00+03:00':v).toLocaleDateString('tr-TR',{day:'numeric',month:'long',year:'numeric',timeZone:'Europe/Istanbul'}) : 'Tarih belirtilmemiş';
const trTime = v => new Date(v).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Istanbul'});
const today = () => new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'});
const days = v => v ? Math.round((Date.parse(v+'T00:00:00Z')-Date.parse(today()+'T00:00:00Z'))/86400000) : null;
function readStore(key,fallback){try{const v=JSON.parse(localStorage.getItem(key));return v??fallback;}catch{return fallback;}}
function writeStore(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{return false;}}
let saved=new Set((Array.isArray(readStore('kit-saved',[]))?readStore('kit-saved',[]):[]).filter(s=>typeof s==='string'&&s.length>0&&s.length<=80)), compared=new Set(), items=[], liste=[], listeTum=[], listeVar=false, listeZaman='', view='active', shown=20, takvimGun=7, loaded=false, listeLoaded=false, toastTimer, profil=null, sonZiyaret=null, tab='bugun', lastTab='bugun';
const PAGE_SIZE=60, defaultTitle=document.title;
/* Manşet (bugun) ve İlanlar aynı ana görünümü paylaşır; İlanlar listeye kaydırır. */
const TABS=['bugun','ilanlar','takvim','kayitli','rehber'],VIEWS=['ana','takvim','kayitli','rehber'],viewOf=t=>t==='bugun'||t==='ilanlar'?'ana':t;
const AY=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'],AYU=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'],GUNLER=['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'];
const IL_LIST=['Adana','Adıyaman','Afyonkarahisar','Ağrı','Aksaray','Amasya','Ankara','Antalya','Ardahan','Artvin','Aydın','Balıkesir','Bartın','Batman','Bayburt','Bilecik','Bingöl','Bitlis','Bolu','Burdur','Bursa','Çanakkale','Çankırı','Çorum','Denizli','Diyarbakır','Düzce','Edirne','Elazığ','Erzincan','Erzurum','Eskişehir','Gaziantep','Giresun','Gümüşhane','Hakkari','Hatay','Iğdır','Isparta','İstanbul','İzmir','Kahramanmaraş','Karabük','Karaman','Kars','Kastamonu','Kayseri','Kırıkkale','Kırklareli','Kırşehir','Kilis','Kocaeli','Konya','Kütahya','Malatya','Manisa','Mardin','Mersin','Muğla','Muş','Nevşehir','Niğde','Ordu','Osmaniye','Rize','Sakarya','Samsun','Siirt','Sinop','Sivas','Şanlıurfa','Şırnak','Tekirdağ','Tokat','Trabzon','Tunceli','Uşak','Van','Yalova','Yozgat','Zonguldak'];
const IC={sag:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg>',kayit:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.5h10a1 1 0 0 1 1 1V21l-6-4-6 4V4.5a1 1 0 0 1 1-1z"/></svg>',ok:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',saat:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>',grafik:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10m6 10V4m6 16v-7m4 7H3"/></svg>',kisi:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>',kalem:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4z"/></svg>',tg:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 4-18 7.2 6 2.3M21 4l-3 16-8.5-6.5M21 4 9.5 13.5v5.5l3-3.5"/></svg>',kitap:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5C6.5 4 9.5 4 12 6c2.5-2 5.5-2 8-.5V19c-2.5-1.5-5.5-1.5-8 .5-2.5-2-5.5-2-8-.5z"/><path d="M12 6v13.5"/></svg>',x:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>',asagi:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',sol:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 6-6 6 6 6"/></svg>',dur:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6v12M15 6v12"/></svg>',oynat:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg>'};
function ic(name){const s=E('span','ic');s.innerHTML=IC[name]||'';return s;}
const istDate=v=>new Date(v).toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'});
const kisaTarih=s=>{const [,m,d]=s.split('-').map(Number);return d+' '+AY[m-1];};
const uzunTarih=s=>{const [,m,d]=s.split('-').map(Number);return d+' '+AYU[m-1];};
const gunAdi=s=>GUNLER[(new Date(s+'T12:00:00Z').getUTCDay()+6)%7];
function ekSi(n){const son={0:'ı',1:'i',2:'si',3:'ü',4:'ü',5:'i',6:'sı',7:'si',8:'i',9:'u'},on={10:'u',20:'si',30:'u',40:'ı',50:'si',60:'ı',70:'i',80:'i',90:'ı'};return n+'’'+(n%10||n===0?son[n%10]:on[n%100]||'ü');}
function baslikTemiz(s){s=String(s||'').replace(/^İlk Defa Atanmak Üzere\s+/,'').replace(/\s+Alım(?:ı)?\s+İlanı$/,' alımı').replace(/\s+Sınav(?:ı)?\s+(?:İlanı|Duyurusu)$/,' sınavı').replace(/\s+İlanı$/,'').replace('Vhki','VHKİ').replace('.net','.NET');return s.charAt(0).toLocaleUpperCase('tr-TR')+s.slice(1);}
const KEY_RE=/^[A-Za-z0-9-]{1,80}$/,DATE_RE=/^\d{4}-\d{2}-\d{2}$/,DT_RE=/^\d{4}-\d{2}-\d{2}T[0-9:.+Zz-]{5,40}$/,PT_RE=/^P\d{1,3}$/;
/* Puan türü -> öğrenim düzeyi (derleme tarafındaki puan_duzeyi ile aynı): P94 ortaöğretim, P93 önlisans, P1–P48 lisans. */
const ptLevel=p=>p==='P94'?'ortaogretim':p==='P93'?'onlisans':/^P([1-9]|[1-3]\d|4[0-8])$/.test(p)?'lisans':null;
/* Satırın etkin düzeyleri: veri düzeyleri ∪ puan türlerinin ima ettiği düzeyler. */
const rowLevels=o=>[...new Set([...o.ogrenim,...o.puan_turleri.map(ptLevel).filter(Boolean)])];
const puanTr=n=>Number(n).toLocaleString('tr-TR',{maximumFractionDigits:5});
const posInt=(v,max)=>Number.isInteger(v)&&v>0&&v<max?v:0;
const str=(v,n)=>typeof v==='string'?v.slice(0,n):'';
const strList=(v,n,m)=>Array.isArray(v)?v.filter(x=>typeof x==='string'&&x.length<=m).slice(0,n):[];
/* liste.json kaydını doğrular: her alan biçim denetiminden geçer, geçmeyen alan boşaltılır. */
function cleanL(l){
if(!l||typeof l!=='object'||!KEY_RE.test(l.key||''))return null;
const o={key:l.key,kopya_of:KEY_RE.test(l.kopya_of||'')&&l.kopya_of!==l.key?l.kopya_of:'',kaynak_sayisi:posInt(l.kaynak_sayisi,10),kaynaklar:strList(l.kaynaklar,6,40),id:str(l.id,120)||l.key,manset:str(l.manset,160),ek:posInt(l.ek,1000),toplam:posInt(l.toplam,20000),kurum:str(l.kurum,200),il:str(l.il,80),kpss:l.kpss==='kpss'||l.kpss==='kpsssiz'?l.kpss:'',son_tarih:DATE_RE.test(l.son_tarih||'')?l.son_tarih:'',durum:str(l.durum,12),ilan_turu:str(l.ilan_turu,60),kategori:/^[a-z0-9_-]{1,30}$/.test(l.kategori||'')?l.kategori:''};
for(const k of ['son_zaman','baslangic_zaman','ilk_gorulme'])o[k]=typeof l[k]==='string'&&DT_RE.test(l[k])&&!isNaN(Date.parse(l[k]))?l[k]:'';
o.meslek=Array.isArray(l.meslek)?l.meslek.filter(f=>typeof f==='string'&&MESLEK.test(f)).slice(0,3):[];
o.logo=IMG_PATH.test(l.logo||'')?l.logo:'';
o.kurum_slug=typeof l.kurum_slug==='string'&&l.kurum_slug.length<=80&&SLUG.test(l.kurum_slug)?l.kurum_slug:'';
o.iller=strList(l.iller,20,80);o.ogrenim=strList(l.ogrenim,3,20).filter(x=>LEVELS[x]);o.puan_turleri=strList(l.puan_turleri,8,5).filter(x=>PT_RE.test(x));o.kurum_ici=l.kurum_ici===true;o.bolum_kisiti=l.bolum_kisiti===true;
const t=l.taban_ref;o.taban_ref={};if(t&&typeof t==='object')for(const d of Object.keys(LEVELS)){const r=t[d];if(r&&typeof r==='object'&&typeof r.medyan==='number'&&r.medyan>0&&r.medyan<=100&&Number.isInteger(r.n)&&r.n>=5)o.taban_ref[d]={medyan:r.medyan,n:r.n};}
return o;}
/* liste.json yoksa/yüklenemezse satır modeli tam kayıttan türetilir (taban referansı ve puan türü olmadan). */
function fallbackModel(i){const t=i.toplam||kadroSayisi(i);return{key:i.key,id:i.id,manset:baslikTemiz(i.manset||title(i)),ek:i.ek||0,toplam:t||0,kurum:kurumAdi(i.kurum),il:placeName(i),iller:strList(i.iller,20,80),ogrenim:(i.ogrenim||[]).filter(x=>LEVELS[x]),meslek:i.meslek||[],logo:i.logo||'',kurum_slug:i.kurum_slug||'',kpss:i.kpss||'',puan_turleri:[],kurum_ici:false,taban_ref:{},son_tarih:i.son_tarih||'',son_zaman:i.son_zaman||'',baslangic_zaman:i.baslangic_zaman||'',ilk_gorulme:i.ilk_gorulme||'',durum:'',ilan_turu:str(i.ilan_turu,60),kategori:/^[a-z0-9_-]{1,30}$/.test(i.kategori||'')?i.kategori:''};}
const rowOf=i=>i.L||fallbackModel(i);
/* Kaynaklar arası kopya ilanın ikincil kimlikleri birincil satıra eşlenir (alias: birincil anahtar -> ikincil kimlikler). */
let alias=new Map(),gizli=new Set(),idKey=new Map();
const idsOf=o=>[o.id,...(alias.get(o.key)||[])];
const isSaved=o=>idsOf(o).some(x=>saved.has(x));
function save(i){const was=isSaved(i);A('tikla',{a:was?'kaydi_sil':'kaydet',h:i.key});if(was){for(const x of idsOf(i)){saved.delete(x);compared.delete(x);}}else saved.add(i.id);const ok=writeStore('kit-saved',[...saved]);render();const full=items.find(x=>x.id===i.id);if(location.hash.startsWith('#ilan/')&&full)showDetail(full);notify(ok?(was?'İlan kaydedilenlerden kaldırıldı.':'İlan bu tarayıcıya kaydedildi.'):'Tarayıcı depolaması kapalı; seçim yalnızca bu oturumda saklanır.');}
function saveButton(i){const on=isSaved(i),b=E('button','kaydet'+(on?' dolu':''));b.type='button';b.setAttribute('aria-label',(on?'Kaydı kaldır: ':'İlanı kaydet: ')+(i.manset||title(i)));b.setAttribute('aria-pressed',String(on));b.innerHTML=IC.kayit;b.onclick=e=>{e.stopPropagation();save(i);};return b;}
function notify(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3500);}
function pickImages(g){const o={};if(!g)return o;if(IMG_PATH.test(g.kart||''))o.kart=g.kart,o.kart_yukseklik=Number(g.kart_yukseklik)||900;if(IMG_PATH.test(g.logo||''))o.logo=g.logo;if(Array.isArray(g.meslek)){const m=g.meslek.filter(f=>typeof f==='string'&&MESLEK.test(f)).slice(0,3);if(m.length)o.meslek=m;}if(typeof g.kurum_slug==='string'&&g.kurum_slug.length<=80&&SLUG.test(g.kurum_slug))o.kurum_slug=g.kurum_slug;for(const [k,max] of [['kurum_sayisi',100000],['ek',1000],['toplam',20000]])if(Number.isInteger(g[k])&&g[k]>0&&g[k]<max)o[k]=g[k];for(const k of ['manset','alt'])if(typeof g[k]==='string'&&g[k].trim())o[k]=g[k].slice(0,160);return o;}
function keyFor(i){try{return new URL(i.link).searchParams.get('i')||i.id;}catch{return i.id;}}
function closed(i){return i.son_zaman?Date.parse(i.son_zaman)<=Date.now():i.son_tarih?days(i.son_tarih)<0:false;}
function upcoming(i){return i.baslangic_zaman&&Date.parse(i.baslangic_zaman)>Date.now();}
function knownActive(i){return !i.duyuru_turu&&!i.iptal_edildi&&!!i.son_tarih&&!closed(i)&&!upcoming(i);}
function stale(i){return !i.detay_guncelleme||Date.now()-Date.parse(i.detay_guncelleme)>86400000;}
function status(i){if(i.iptal_edildi)return 'İptal edildi';if(i.duyuru_turu)return i.duyuru_turu;if(closed(i))return 'Başvuru sona erdi';if(upcoming(i))return 'Başvuru henüz başlamadı';const d=days(i.son_tarih);return d===null?'Son tarih doğrulanmalı':d===0?'Bugün son gün':d===1?'Yarın son gün':d+' gün kaldı';}
function statusNode(i){const d=days(i.son_tarih);return E('span','status-badge'+(closed(i)||i.iptal_edildi?' closed cancelled':i.duyuru_turu||upcoming(i)||d===null?'':d<=1?' urgent today':d<=3?' urgent':d<=7?' soon':''),status(i));}
function kadroSayisi(i){const m=String(i.kadro||'').match(/^\s*(?:toplam\s+)?(\d{1,5})\s+(?!yıl|yil)\S/i);const n=m?Number(m[1]):0;return n>0&&n<20000?n:null;}
function title(i){let t=i.baslik||'İlan';if(i.kurum&&normalize(t).startsWith(normalize(i.kurum)))t=t.slice(i.kurum.length).replace(/^\s*[-–:]\s*/,'');return proper(t);}
function detailLink(i,label,cls){const a=E('a',cls,label);a.href='ilan/'+encodeURIComponent(i.key)+'/';a.onclick=e=>{if(loaded&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey&&e.button===0){e.preventDefault();location.hash='ilan/'+encodeURIComponent(i.key);}};return a;}
const LEVELS={lisans:'Lisans',onlisans:'Önlisans',ortaogretim:'Ortaöğretim'};
const IMG_PATH=/^ilan\/(?:kart|logo)\/[A-Za-z0-9-]+\.webp$/;
const MESLEK=/^\d{2}-[a-z0-9-]{1,40}\.jpg$/,SLUG=/^[a-z0-9]+(?:-[a-z0-9]+)*$/;
function hue(v){let h=0;for(const c of String(v||''))h=(h*31+c.charCodeAt(0))>>>0;return h%360;}
function badge(i,cls){const name=kurumAdi(i.kurum)||'Kamu',b=E('span',cls,name.split(/\s+/).filter(w=>/^[a-zçğıöşü]/i.test(w)).slice(0,2).map(x=>x[0].toLocaleUpperCase('tr-TR')).join('')||'K');b.style.setProperty('--h',hue(i.kurum));b.setAttribute('aria-hidden','true');return b;}
function logoNode(i,cls,size){if(!i.logo)return badge(i,cls+' institution-badge');const im=E('img',cls+' institution-logo');im.src=i.logo;im.alt=(kurumAdi(i.kurum)||'Kurum')+' logosu';im.width=size;im.height=size;im.loading='lazy';im.decoding='async';im.onerror=()=>im.replaceWith(badge(i,cls+' institution-badge'));return im;}
function cardImage(i,preview){if(!i.kart)return null;const im=E('img',preview?'card-image':'detail-card-img');im.src=i.kart;im.alt=(kurumAdi(i.kurum)||'Kurum')+' ilan görseli';im.width=720;im.height=i.kart_yukseklik||900;im.decoding='async';if(preview)im.loading='lazy';im.onerror=()=>im.remove();return im;}
function statusKind(i){if(i.iptal_edildi)return 'cancelled';if(i.duyuru_turu)return 'info';if(closed(i))return 'closed';if(upcoming(i))return 'upcoming';const d=days(i.son_tarih);return d===null?'none':d<=1?'today':d<=3?'urgent':d<=7?'soon':'ok';}
function kurumNode(i,cls){const name=kurumAdi(i.kurum)||'Kurum belirtilmemiş';if(!i.kurum_slug)return E('p',cls,name);const a=E('a',cls,name);a.href='kurum/'+i.kurum_slug+'/';a.title=name+' — kurumun tüm ilanları';return a;}
function placeName(i){const y=String(i.yer||'').split(/\s*[\/•]\s*/)[0].replace(/^[\s-]+|[\s-]+$/g,'');if(!y)return '';return /^(bakanlık merkez|ankara)/i.test(y.toLocaleLowerCase('tr-TR'))?'Ankara':proper(y);}
/* Görev yeri: il önce, ilçe/birim parantezde; tekrarlar atılır; 3'ten fazla ilde 'Ankara, İstanbul +4' (bot/kurum_sayfasi.yer_metni ile aynı). */
function yerMetni(i,yedek=''){
const iller=new Map(),diger=[],ekle=(l,a)=>{if(!l.some(x=>normalize(x)===normalize(a)))l.push(a);},ilOf=t=>IL_LIST.find(x=>normalize(x)===normalize(t));
for(const parca of String(i.yer||'').split(/\s*•\s*/)){let cur=null;for(let t of parca.split(/\s*,\s*|\s*\/\s*|\s+-\s*|\s*-\s+/)){t=t.replace(/^[\s-]+|[\s-]+$/g,'');if(!t)continue;const il=ilOf(t);if(il){cur=il;if(!iller.has(il))iller.set(il,[]);}else if(cur)ekle(iller.get(cur),proper(t));else ekle(diger,proper(t));}}
for(const a of Array.isArray(i.iller)?i.iller:[]){const il=ilOf(a);if(il&&!iller.has(il))iller.set(il,[]);}
if(!iller.size&&!diger.length)return yedek;
const L=[...iller],yazi=L.length>3?L.slice(0,2).map(x=>x[0]).join(', ')+' +'+(L.length-2):L.map(([il,ic])=>ic.length?il+' ('+ic.join(', ')+')':il).join(', ');
return [...diger,...(yazi?[yazi]:[])].join(' · ');}
function external(url,label,cls='button primary'){const a=E('a',cls,label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function openModal(){izModal=true;if(!$('modal').open)$('modal').showModal();$('modal').scrollTop=0;}
function infoSection(parent,heading,text){parent.append(E('h3','',heading),E('p','',text));}
function showDetail(i){A('sayfa',{v:'ilan',k:i.key});const body=$('modal-body');body.replaceChildren();const header=E('div','detail-header');header.append(E('span','eyebrow',i.ilan_turu||'KAMU PERSONEL ALIMI'));const h=E('h2','',title(i));h.id='modal-title';header.append(h,kurumNode(i,'detail-kurum'));const vis=cardImage(i,false);if(vis){const box=E('div','detail-visual');if(i.logo)box.append(logoNode(i,'detail-logo',64));box.append(vis);body.append(box);}body.append(header);const layout=E('div','detail-layout'),content=E('div','detail-content'),side=E('aside','detail-aside'),dl=E('dl');for(const [k,v] of [['Durum',status(i)],['Görev yeri',yerMetni(i)||'Resmî ilandan kontrol et'],['Son başvuru',trDate(i.son_tarih)+(i.son_zaman?' · '+trTime(i.son_zaman)+' TSİ':'')],['Başlangıç',i.baslangic_zaman?trDate(i.baslangic_zaman):'Belirtilmemiş']])dl.append(E('dt','',k),E('dd','',v));side.append(dl);const docURL=sourceDocument(i);const link=docURL||officialURL(i.link);if(link){const ex=external(link,docURL?'İlan belgesini aç (PDF) ↗':'Resmî ilana git · Başvur ↗');ex.setAttribute('data-a','resmi_ilan');ex.setAttribute('data-a-h',i.key);side.append(ex);}if(docURL)side.append(E('p','muted',i.belge_aciklamasi));const sb=E('button','button secondary',isSaved(i)?'Kaydedildi · kaldır':'İlanı kaydet');sb.onclick=()=>save(i);const share=E('button','button secondary','Bağlantıyı paylaş');share.onclick=()=>shareItem(i);side.append(sb,share);if(i.son_tarih&&!closed(i)&&!i.duyuru_turu){const calendar=E('button','button secondary','Takvimime ekle');calendar.onclick=()=>{A('tikla',{a:'takvim_ics',h:i.key,x:'tek'});downloadCalendar(i);};side.append(calendar);}side.append(E('p','muted','Kaydetmek veya takvime eklemek başvuru oluşturmaz. İşlemini resmî başvuru kanalında tamamla.'));if(stale(i))content.append(E('p','notice','Bu ilanın ayrıntıları 24 saat içinde doğrulanmadı. Başvuru yapmadan önce güncel tarih ve koşulları resmî ilandan kontrol et.'));if(closed(i))content.append(E('p','notice','Kayıtlı son başvuru zamanı geçti. Bu ilan arşiv amacıyla gösteriliyor.'));if(upcoming(i))content.append(E('p','notice','Kayıtlı başvuru başlangıcı henüz gelmedi.'));infoSection(content,'Kadro ve kontenjan',i.kadro||'Kontenjan bilgisi kaynak özetinde bulunmuyor. Tam ilanı incele.');if(i.ozet)infoSection(content,'İlan özeti',i.ozet);content.append(E('h3','','Başvuru koşullarından seçmeler'));if(i.sartlar?.length){for(const s of i.sartlar){const c=E('section','condition');c.append(E('h4','',proper(s.kadro)),E('p','',s.metin));content.append(c);}content.append(E('p','muted','Bu bölüm seçilmiş alıntıları içerir; tüm kadro ve özel koşulların listesi değildir. Üç nokta ile biten metinler kısaltılmıştır.'));}else content.append(E('p','','Kaynak özetinde başvuru koşulları yer almıyor. Mezuniyet, KPSS, yaş ve diğer şartlar için resmî ilanı aç.'));if(i.basvuru_notu)infoSection(content,'Başvuruya ilişkin not',i.basvuru_notu);const related=items.filter(x=>x.id!==i.id&&knownActive(x)).sort((a,b)=>Number(b.ilan_turu===i.ilan_turu)-Number(a.ilan_turu===i.ilan_turu)).slice(0,3);if(related.length){content.append(E('h3','','Bunlara da göz at'));const box=E('div','related');for(const r of related){const a=detailLink(r,title(r));a.append(E('span','',kurumAdi(r.kurum)+' · '+status(r)));box.append(a);}content.append(box);}content.append(E('p','muted','Kaynak: '+(i.kaynaklar?.map(s=>s.ad).join(' · ')||i.kaynak||'Kariyer Kapısı')+(i.detay_guncelleme?' · Ayrıntı kontrolü: '+trDate(i.detay_guncelleme)+' '+trTime(i.detay_guncelleme):'')));layout.append(content,side);body.append(layout);document.title=title(i)+' | KPSS Tercihi';openModal();}
async function shareItem(i){const url=new URL(location.href);url.hash='ilan/'+encodeURIComponent(i.key);url.search='';try{if(navigator.share)await navigator.share({title:title(i),url:url.href});else{await navigator.clipboard.writeText(url.href);notify('İlan bağlantısı kopyalandı.');}}catch(e){if(e.name!=='AbortError'){const field=E('input');field.value=url.href;field.readOnly=true;field.setAttribute('aria-label','Paylaşılacak ilan bağlantısı');$('modal-body').append(field);field.focus();field.select();notify('Bağlantıyı seçip kopyalayabilirsin.');}}}
function calendarText(list){
const esc=v=>String(v||'').replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');const utc=d=>new Date(d).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z/,'Z');
const stamp=utc(Date.now()),ev=i=>{const date=i.son_zaman?Date.parse(i.son_zaman):null;const timing=date?['DTSTART:'+utc(date),'DTEND:'+utc(date+60000)]:['DTSTART;VALUE=DATE:'+i.son_tarih.replace(/-/g,''),'DTEND;VALUE=DATE:'+new Date(Date.parse(i.son_tarih+'T00:00:00Z')+86400000).toISOString().slice(0,10).replace(/-/g,'')];const url=officialURL(i.link);return ['BEGIN:VEVENT','UID:'+esc(i.key)+'@kamu-ilan-takip','DTSTAMP:'+stamp,...timing,'SUMMARY:'+esc('Son başvuru: '+title(i)),'DESCRIPTION:'+esc('Resmî ilandaki güncel tarih ve koşulları kontrol edin. '+(i.link||'')),...(url?['URL:'+url]:[]),'END:VEVENT'];};
return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//KPSS Tercihi//TR',...(Array.isArray(list)?list:[list]).filter(i=>i&&i.son_tarih).flatMap(ev),'END:VCALENDAR'].map(icsFold).join('\r\n')+'\r\n';}
/* RFC 5545: satırlar 75 sekizliyi aşmaz; devam satırı boşlukla başlar. */
function icsFold(line){const out=[];let cur='',n=0;for(const ch of line){const cp=ch.codePointAt(0),b=cp<0x80?1:cp<0x800?2:cp<0x10000?3:4,lim=out.length?74:75;if(n+b>lim){out.push(cur);cur='';n=0;}cur+=ch;n+=b;}out.push(cur);return out.join('\r\n ');}
function downloadCalendar(i){const u=URL.createObjectURL(new Blob([calendarText(i)],{type:'text/calendar;charset=utf-8'})),a=E('a');a.href=u;a.download='kamu-ilan-son-basvuru.ics';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);notify('Takvim dosyası indirildi. Takvim uygulamana ekleyebilirsin.');}
const articles={
 'rehber/ilan-okuma':{title:'Bir ilanı nasıl okumalısın?',intro:'Başlığın uygun görünmesi tek başına yeterli değildir. İncelemeyi seçtiğin kadro üzerinden yap.',sections:[['1. Önce kadroyu belirle','Aynı ilanda farklı unvanlar ve farklı koşullar bulunabilir. Başvurmak istediğin kadronun adı, kodu, görev yeri ve kontenjanını not et.'],['2. Koşulları birlikte değerlendir','Mezuniyet programı, puan türü ve yılı, varsa asgari puan, deneyim ve belge koşullarını tam metinden kontrol et. İlan özetindeki alıntıları tüm şartların yerine koyma.'],['3. Başvuru yolunu ve zamanı kontrol et','İlanda belirtilen başvuru kanalını kullan. Son günün yanında saat bilgisi ve varsa ayrıca teslim edilmesi gereken belgelerin tarihini de incele.'],['4. Duyurulara geri dön','Düzeltme, sonuç ve ek duyuruları ilgili kurumun resmî kanallarından takip et. Bu platform başvuru kabul etmez veya uygunluk kararı vermez.']]},
 'rehber/basvuru-listesi':{title:'Başvuru kontrol listesi',intro:'Her ilan için bu kısa listeyi yeniden gözden geçir.',steps:['Başvuracağın kadro kodunu ve görev yerini seç.','Mezuniyet ve puan koşullarını tam ilan metniyle karşılaştır.','İstenilen belgelerin güncel ve okunaklı olduğundan emin ol.','Son başvuru tarihini, saatini ve varsa ek belge teslim tarihini not et.','Resmî başvuru kanalında işlemini tamamla.','Başvurunun durumunu ilgili sistemde doğrula; kayıt veya başvuru belgeni sakla.','Sonuç ve sonraki aşama duyurularını resmî kurumdan takip et.'],sections:[['Kaydetmek, başvurmak değildir','Buradaki yer imi kişisel takip içindir. Başvuru işlemini ilanda belirtilen resmî kanalda ayrıca tamamlamalısın.']]},
 'rehber/takvim':{title:'Son günü bekleme.',intro:'İlanları son tarihlerine göre sıralamak, başvuru planını daha görünür kılar.',sections:[['Önce yakın tarihleri incele','“Son 3 gün” veya “Son 7 gün” filtresini kullan. İlan kartının kalan süresi Türkiye saatine göre hesaplanır. Kesin saat belirtilmişse ayrıntı ekranında gösterilir.'],['Takvimine ekle','İlan ayrıntısındaki “Takvimime ekle” düğmesi bir takvim dosyası indirir. Dosyayı takvim uygulamanla açıp eklemeyi tamamla. Bildirim zamanını kendi takviminde seçebilirsin.'],['Tarihi yeniden doğrula','Takvim dosyası indirildiği andaki bilgiyi taşır, sonradan otomatik güncellenmez. İlanda bir değişiklik varsa takvim kaydını da güncelle.'],['Kendine hazırlık süresi bırak','Belgeleri ve başvuru adımlarını erkenden incele. Teknik sorun yaşarsan destek için ilgili kurumun ilanda belirttiği iletişim kanalını kullan.']]},
 'bilgi/hakkimizda':{title:'Hakkımızda ve veri kaynağı',intro:'KPSS Tercihi, kamu personel ilanlarını daha kolay incelemek ve takip etmek için hazırlanmış bağımsız bir rehberdir.',sections:[['Veriler nereden geliyor?','İlanlar Kariyer Kapısı resmî RSS akışından, İŞKUR kamu memur alım ilanları sayfalarından, SBB Kamu İlan listesinden ve Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Yerel Yönetimler duyurularından (ÇŞB) derlenir. SBB belgelerinde yılı doğrulanamayan tarihler gösterilmez; SBB’den alınan ilan belgelerinin değiştirilmemiş kopyaları ilgili ilan sayfasından açılır. Kurum, görev yeri, kontenjan ve koşullar kaynağın sunduğu bilgilerle sınırlıdır.'],['Güncellik nasıl gösterilir?','Ana sayfadaki son kontrol zamanı liste taramasını gösterir. İlan ayrıntılarının kontrol tarihi ayrıca gösterilir. Otomatik bağlantılar gecikebilir; eski ayrıntılar uyarıyla sunulur.'],['Resmî bir hizmet mi?','Hayır. Herhangi bir kamu kurumuna bağlı değiliz. Başvuru kabul etmeyiz, aday uygunluğu değerlendirmeyiz. Güncel ve bağlayıcı bilgi için resmî ilanı esas alın.'],['Bir hata fark ettin mi?','İlanın bağlantısını ve hatalı alanı proje bildirim sayfasından iletebilirsin. Herkese açık bildirimlere kimlik, özgeçmiş veya başvuru belgesi ekleme.']],contact:true},
 'bilgi/gizlilik':{title:'Gizlilik ve tarayıcı verileri',intro:'Bu sürüm üyelik istemez. Özgeçmiş, kimlik bilgisi veya başvuru belgesi toplamak için bir form içermez.',sections:[['Bu cihazda saklanan bilgiler','Kaydettiğin ilanların kimlikleri, profilin (öğrenim düzeyi, puan, iller), son ziyaret zamanın ve renk teması tercihin tarayıcının yerel depolamasında tutulur. Bunlar başka cihazlara taşınmaz. Aşağıdaki düğme bu platformun yerel tercihlerini temizler.'],['Dış bağlantılar ve barındırma','Resmî başvuru sayfası, Telegram ve GitHub bağlantıları kendi hizmetlerine yönlendirir. Bu hizmetlerin veri uygulamaları ayrıdır. Site dosyaları GitHub Pages üzerinden sunulur; barındırma hizmeti teknik erişim kayıtlarını işleyebilir.'],['Ziyaret istatistikleri','Hangi sayfaların ve özelliklerin kullanıldığını anlamak için anonim ve çerezsiz ziyaret istatistikleri toplanır; IP adresin saklanmaz, kişisel veri toplanmaz ve seni sonraki günlerde tanıyacak bir kimlik tutulmaz. Tarayıcında “Do Not Track” ya da Global Privacy Control (GPC) açıksa hiç ölçüm yapılmaz. Üçüncü taraf reklam ağı veya izleme kodu yoktur.']],clear:true},
 'bilgi/reklam':{title:'Reklam ve iş birliği',intro:'Kamu kariyeriyle ilgilenen ziyaretçilere ulaşmak isteyen markalar için açıkça etiketlenmiş sponsor alanları.',sections:[['İki sade yerleşim','Ana sayfa yan sütununda ve ilan listesinin altında sponsor alanı ayrılmıştır. Aktif bir kampanya yoksa boş reklam kutuları gösterilmez.'],['İlanlardan ayrı bir alan','Sponsorlu içerik “Reklam · Sponsorlu” etiketi taşır. Reklamlar resmî ilan gibi gösterilmez; ilan sıralaması sponsorlu içerikten etkilenmez.'],['İş birliği talebi','Markanı, kampanya konunu ve tercih ettiğin alanı proje iletişim sayfasından paylaşabilirsin. Bu herkese açık kanala gizli ticari bilgiler veya kişisel belgeler ekleme.']],contact:true}
};
/* Bu platformun tüm yerel tercihleri: kit- ile başlayan her anahtar (profil, tema, kayıtlar, puan düzeyi, oturum tabanı). */
function clearLocal(){try{const ks=[];for(let i=0;i<(localStorage.length||0);i++){const k=localStorage.key(i);if(k&&k.startsWith('kit-'))ks.push(k);}for(const k of new Set([...ks,'kit-theme','kit-profil','kit-son-ziyaret','kit-saved','kit-puan-duzey']))localStorage.removeItem(k);}catch{}try{sessionStorage.removeItem('kit-sz-baz');}catch{}}
function showArticle(key){const a=articles[key];if(!a)return;A('sayfa',{v:'makale',k:key});const n=E('article','article');n.append(E('span','eyebrow',key.startsWith('rehber/')?'BAŞVURU REHBERİ':'KPSS TERCİHİ'));const h=E('h2','',a.title);h.id='modal-title';n.append(h,E('p','',a.intro));if(a.steps){const ol=E('ol');a.steps.forEach(s=>ol.append(E('li','',s)));n.append(ol);}for(const [heading,text] of a.sections)infoSection(n,heading,text);if(a.contact)n.append(external('https://github.com/enesfeched-maker/kamu-ilan-takip/issues/new','İletişim / bildirim sayfası ↗'));if(a.clear){const b=E('button','button secondary','Kaydedilen ilanları, profili ve tema tercihini temizle');b.onclick=()=>{saved.clear();writeStore('kit-saved',[]);profil=null;sonZiyaret=null;clearLocal();applyTheme();render();notify('Bu platformun yerel tercihleri temizlendi.');};n.append(b);}n.append(E('p','muted','Son düzenleme: 8 Ekim 2026'));$('modal-body').replaceChildren(n);document.title=a.title+' | KPSS Tercihi';openModal();}
function showComparison(){const rows=items.filter(i=>compared.has(i.id));if(rows.length<2){notify('Karşılaştırmak için en az 2 ilan seç.');return;}const n=E('div','comparison'),h=E('h2','','İlanları yan yana incele');h.id='modal-title';n.append(h,E('p','muted','Bu karşılaştırma bir uygunluk değerlendirmesi değildir. Tam koşullar resmî ilandadır.'));const t=E('table'),head=E('tr');head.append(E('th','','Özellik'));for(const i of rows){const th=E('th');th.append(detailLink(i,title(i)));head.append(th);}t.append(head);for(const [name,fn] of [['Kurum',i=>kurumAdi(i.kurum)],['Görev yeri',i=>proper(i.yer)||'Belirtilmemiş'],['Kadro / kontenjan',i=>i.kadro||'Belirtilmemiş'],['Son başvuru',i=>trDate(i.son_tarih)+(i.son_zaman?' '+trTime(i.son_zaman)+' TSİ':'')],['Durum',status],['Seçilmiş koşullar',i=>(i.sartlar||[]).map(s=>proper(s.kadro)+': '+s.metin).join('\n\n')||'Resmî ilandan kontrol et']]){const tr=E('tr');tr.append(E('th','',name));rows.forEach(i=>tr.append(E('td','',fn(i))));t.append(tr);}n.append(t);$('modal-body').replaceChildren(n);openModal();}
/* ---------- satır kartı (.ilan) ---------- */
function visualOf(o){
const generic=!o.meslek.length||/^30-/.test(o.meslek[0]);
if(generic&&o.logo){const s=E('span','ilan-foto logo-karo'),im=E('img');im.src=o.logo;im.alt='';im.loading='lazy';im.decoding='async';im.onerror=()=>s.replaceWith(badge({kurum:o.kurum},'ilan-foto harf-karo'));s.append(im);return{node:s,karo:true};}
if(generic)return{node:badge({kurum:o.kurum},'ilan-foto harf-karo'),karo:false};
const im=E('img','ilan-foto');im.src='assets/meslek/'+o.meslek[0];im.alt='';im.width=52;im.height=52;im.loading='lazy';im.decoding='async';im.onerror=()=>im.replaceWith(badge({kurum:o.kurum},'ilan-foto harf-karo'));return{node:im,karo:false};}
function smallLogo(o){if(o.logo){const im=E('img','kl');im.src=o.logo;im.alt='';im.width=18;im.height=18;im.loading='lazy';im.onerror=()=>im.replaceWith(badge({kurum:o.kurum},'kb'));return im;}return badge({kurum:o.kurum},'kb');}
function metaOf(o,kadroGizli){const p=[];if(o.toplam&&!kadroGizli&&!/^\d/.test(o.manset)){const b=E('b','',o.toplam.toLocaleString('tr-TR')+' kadro');p.push(['',b]);}if(o.il)p.push(['',o.il]);if(o.ogrenim.length)p.push(['',o.ogrenim.map(x=>LEVELS[x]).join(' / ')]);if(o.puan_turleri.length)p.push(['kpss','KPSS '+o.puan_turleri.slice(0,2).join(', ')]);else if(o.kpss==='kpss')p.push(['kpss','KPSS']);const m=E('p','ilan-meta');for(const [c,v] of p.slice(0,4)){const s=E('span',c);s.append(v);m.append(s);}return m;}
const RANK={ortaogretim:0,onlisans:1,lisans:2};
const activeProfile=()=>profil&&!profil.atlandi?profil:null;
/* Taban referansı: profil düzeyine göre; profil yoksa ilanın ilk düzeyine göre. */
function refFor(o,pr){const t=o.taban_ref||{},d=pr?pr.ogrenim:o.ogrenim[0];return d&&t[d]?t[d]:null;}
function sinyalOf(o){
if(upcoming(o)){const d=istDate(Date.parse(o.baslangic_zaman)),p=E('p','sinyal acilis');p.append(ic('saat'),'Başvuru '+uzunTarih(d)+'’de açılıyor');return p;}
const pr=activeProfile(),r=refFor(o,pr);
if(!pr||!r||typeof pr.puan!=='number'||pr.puan_turu!==defaultTur(pr.ogrenim)||(o.puan_turleri.length&&!o.puan_turleri.includes(pr.puan_turu)))return null;
const fark=pr.puan-r.medyan,x=Math.abs(fark).toFixed(1).replace('.',','),p=E('p','sinyal');
const tam=fark>0?'Puanın, benzer kadroların taban medyanından '+x+' puan yüksek':fark<0?'Puanın, benzer kadroların taban medyanından '+x+' puan düşük':'Puanın, benzer kadroların taban medyanıyla aynı';
const kisa=fark>0?'Benzer kadro · '+x+' puan önde':fark<0?'Benzer kadro · '+x+' puan geride':'Benzer kadro · eşit';
const not='Geçmiş yerleştirmelerden referans; bu ilanın şartı değildir';
p.title=not;p.setAttribute('aria-label',tam+'. '+not);
p.append(ic('grafik'),E('span','d',tam),E('span','m',kisa));return p;}
function tarihOf(o){
const d=E('div','tarih'),g=o.son_tarih?days(o.son_tarih):null;
if(g===null){d.className='tarih yok';d.append(E('strong','','—'),E('span','',o.durum==='belirsiz'?'tarih doğrulanamadı':'tarih ilanda'));return d;}
if(closed(o)){d.append(E('strong','',kisaTarih(o.son_tarih)),E('span','','sona erdi'));return d;}
if(g<=2&&!upcoming(o)){d.className='tarih acil';if(g<=0)d.append(E('strong','','Bugün'),E('span','','son gün'));else if(g===1)d.append(E('strong','','Yarın'),E('span','','son gün'));else d.append(E('strong','',kisaTarih(o.son_tarih)),E('span','','2 gün kaldı'));return d;}
d.append(E('strong','',kisaTarih(o.son_tarih)),E('span','',g+' gün'));return d;}
function isNew(o){const t=Date.parse(o.ilk_gorulme);if(!t)return false;return sonZiyaret?t>sonZiyaret:Date.now()-t<172800000;}
function rowEl(o,opt={}){
const n=E('article','ilan'),v=visualOf(o),govde=E('div','ilan-govde'),kurum=E('div','ilan-kurum');
if(opt.yeni&&isNew(o))kurum.append(E('span','yeni','Yeni'));
if(opt.alt)kurum.append(E('span','alt-etiket','alt düzey · şartları kontrol et'));
if(!v.karo||!o.logo)kurum.append(smallLogo(o));
const ad=o.kurum||'Kurum belirtilmemiş';
if(o.kurum_slug){const a=E('a','ad',ad);a.href='kurum/'+o.kurum_slug+'/';a.title=ad+' — kurumun tüm ilanları';a.onclick=e=>e.stopPropagation();kurum.append(a);}else kurum.append(E('span','ad',ad));
const h=E('h3'),a=detailLink(o,o.manset||'Kamu ilanı');a.setAttribute('data-a','satir_tikla');a.setAttribute('data-a-h',o.key);if(o.ek)a.append(' ',E('span','ek','+'+o.ek));h.append(a);
govde.append(kurum,h,metaOf(o,opt.kadro));const sg=sinyalOf(o);if(sg)govde.append(sg);
const sag=E('div','ilan-sag');sag.append(opt.kadro?kadroBlok(o):tarihOf(o),saveButton(o));
if(opt.kars){const l=E('label','kars'),c=E('input');c.type='checkbox';c.checked=compared.has(o.id);c.onchange=()=>{if(c.checked&&compared.size>=3){c.checked=false;notify('En fazla 3 ilan karşılaştırabilirsin.');return;}c.checked?compared.add(o.id):compared.delete(o.id);renderCompare();};l.append(c,'Karşılaştır');sag.append(l);}
n.append(v.node,govde,sag);return n;}
const listeEl=(rows,opt)=>{const d=E('div','liste');d.append(...rows.map(o=>rowEl(o,typeof opt==='function'?opt(o):opt)));return d;};
function bosKutu(...nodes){const d=E('div','bos');d.append(...nodes);return d;}
function sectionEl(id,o){const s=E('section','bolum');s.id=id;const bas=E('div','bolum-bas'),k=E('div'),h=E('h2');if(o.nokta)h.append(E('span','nokta'+(o.nokta==='acil'?' acil':'')));h.append(o.baslik);if(o.sayi!==undefined)h.append(E('span','sayi',String(o.sayi)));k.append(h);if(o.alt)k.append(E('p','',o.alt));bas.append(k);if(o.link)bas.append(o.link);s.append(bas,o.govde);return s;}
function linkTo(text,hash){const a=E('a','yazi-link',text+' ');a.href=hash;a.append(ic('sag'));return a;}
/* ---------- profil ---------- */
function validProfile(p){
if(!p||typeof p!=='object'||p.v!==1)return null;
const t=typeof p.t==='string'&&DATE_RE.test(p.t)?p.t:today();
if(p.atlandi===true)return{v:1,atlandi:true,t};
if(!LEVELS[p.ogrenim])return null;
const o={v:1,ogrenim:p.ogrenim,puan_turu:typeof p.puan_turu==='string'&&PT_RE.test(p.puan_turu)&&ptLevel(p.puan_turu)===p.ogrenim?p.puan_turu:defaultTur(p.ogrenim),iller:(Array.isArray(p.iller)?p.iller:[]).filter(x=>IL_LIST.includes(x)).slice(0,81),tum_turkiye:p.tum_turkiye===true,bolum:str(p.bolum,60),t};
if(typeof p.puan==='number'&&p.puan>0&&p.puan<=100)o.puan=p.puan;return o;}
function defaultTur(o){return o==='onlisans'?'P93':o==='ortaogretim'?'P94':'P3';}
const ilKeys=o=>(o.iller&&o.iller.length?o.iller:[String(o.il||'').replace(/\s*\+\d+$/,'')]).map(normalize);
const ILN=new Set(IL_LIST.map(normalize));
/* İli bilinmeyen / boş / "Türkiye Geneli" ilanlar ülke geneli sayılır ve her ilde görünür. */
const ulusal=o=>!ilKeys(o).some(k=>ILN.has(k));
/* İl seçilmediyse (ve Tüm Türkiye işaretli değilse) il kısıtı yoktur: Tüm Türkiye gibi davranır. */
const ilOk=(o,p)=>p.tum_turkiye||!p.iller.length||ulusal(o)||p.iller.some(x=>ilKeys(o).includes(normalize(x)));
/* Tüm Türkiye açıkken seçilen illerdeki ilanlar öne alınır. */
const ilRank=(o,p)=>p.tum_turkiye&&p.iller.length&&!p.iller.some(x=>ilKeys(o).includes(normalize(x)))?1:0;
/* 'tam' | 'alt' (profil düzeyinden aşağı) | 'bilinmiyor' (öğrenim şartı okunamadı) | false. Kurum içi sınavlar kimseye uygun sayılmaz. */
function uygun(o,p){
if(o.kurum_ici||!ilOk(o,p))return false;
const L=rowLevels(o);
if(!L.length)return 'bilinmiyor';
if(L.includes(p.ogrenim))return 'tam';
return L.some(x=>RANK[x]<RANK[p.ogrenim])?'alt':false;}
const eslesen=s=>s==='tam'||s==='alt';
const sayiTr=n=>Number(n).toLocaleString('tr-TR');
/* Öğrenim şartı okunamayan (düzeyi belirsiz) ama il olarak uyan ilanlar: sessizce "uygun" sayılmaz, süzgeç özetindeki bağlantıyla açılır. */
const bilinmiyorYama=p=>({ogr:'bilinmiyor',uygun:false,il:p.tum_turkiye?[]:p.iller.slice(0,10)});
function railTelegram(){
const b=E('section','kutu tg-kutu'),s=E('span','tg-saat'),a=E('a','btn btn-lime');s.append(ic('saat'),'Her sabah 09:00 civarı');
a.href='https://t.me/kamuilantakip';a.target='_blank';a.rel='noopener';a.setAttribute('data-a','telegram');a.setAttribute('data-a-x','kutu');a.append(ic('tg'),'Kanala katıl');
b.append(s,E('h3','','Günün özeti Telegram’da'),E('p','','Yeni ilanlar ve son günler tek mesajda. Mesajdaki bağlantı seni doğrudan bu sayfaya getirir.'),a);return b;}
const adBox={sidebar:E('div'),feed:$('ad-feed')};adBox.sidebar.hidden=true;
/* ---------- Ana sayfa: manşet ve zaman çizelgesi ---------- */
const ilanHref=o=>'ilan/'+encodeURIComponent(o.key)+'/';
/* Başvuru aralığı: başlangıç (yoksa yayın günü) – son başvuru. "6 Ekim – 20 Ekim" */
function tarihAraligi(o){
const bas=o.baslangic_zaman?istDate(Date.parse(o.baslangic_zaman)):o.ilk_gorulme?istDate(Date.parse(o.ilk_gorulme)):'',son=o.son_tarih;
if(!son)return bas&&upcoming(o)?uzunTarih(bas)+' – son tarih ilanda':'Son tarih ilanda';
if(!bas||bas>=son)return uzunTarih(son);
return uzunTarih(bas)+' – '+uzunTarih(son);}
function kurumGorseli(o,cls,size){const s=E('span',cls);if(o.logo){const im=E('img');im.src=o.logo;im.alt='';im.width=size;im.height=size;im.loading='lazy';im.decoding='async';im.onerror=()=>s.replaceChildren(badge({kurum:o.kurum},'harf'));s.append(im);}else s.append(badge({kurum:o.kurum},'harf'));return s;}
/* Manşet: kapanmamış ilanlardan 12 tane; kurum içi ve tarihi doğrulanamayanlar hariç.
   Sıra: son 7 günün popülerlik puanı (api /populer) azalan; puanı olmayanlar (ya da veri gelmediyse hepsi) kadrosu en büyükten, eşitlikte en yeni. */
let mansetPop=null,mansetEtkilesim=false;
const OKLAR={sol:'<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m14.5 5.5-6.5 6.5 6.5 6.5"/></svg>',sag:'<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>'};
const POPULER_URL='https://api.kpsstercihi.com/populer';
function mansetSecimi(){
const gor=new Set(),pop=mansetPop,puan=o=>pop&&pop.has(o.key)?pop.get(o.key):0;
return liste.filter(o=>!closed(o)&&!o.kurum_ici&&o.durum!=='belirsiz'&&o.toplam>0).sort((a,b)=>puan(b)-puan(a)||b.toplam-a.toplam||(Date.parse(b.ilk_gorulme)||0)-(Date.parse(a.ilk_gorulme)||0)).filter(o=>{const k=normalize(o.manset)+'|'+o.toplam;if(gor.has(k))return false;gor.add(k);return true;}).slice(0,12);}
/* Popülerlik verisi: 1,5 sn içinde gelmezse ya da hata verirse sessizce yok sayılır. Kullanıcı slayta dokunmadıysa manşet yeni sırayla yeniden çizilir. */
async function populerYukle(){
try{
if(typeof fetch!=='function')return;
const ac=typeof AbortController==='function'?new AbortController():null,zm=ac?setTimeout(()=>ac.abort(),1500):null;
let j;try{const r=await fetch(POPULER_URL,ac?{signal:ac.signal}:{});if(!r||!r.ok)return;j=await r.json();}finally{if(zm)clearTimeout(zm);}
const o=j&&typeof j==='object'?j.ilanlar:null;if(!o||typeof o!=='object')return;
const m=new Map();for(const [k,v] of Object.entries(o))if(KEY_RE.test(k)&&typeof v==='number'&&v>0&&isFinite(v))m.set(k,v);
if(!m.size)return;mansetPop=m;
if(!mansetEtkilesim&&listeLoaded&&viewOf(tab)==='ana'){mansetSira=0;renderManset();}
}catch{}}
/* "860 Gelir Uzman Yardımcısı alacak"; birden çok unvanda "103 personel alacak" + unvanlar alt satırda. */
function mansetBaslik(o){
const m=String(o.manset||'').trim();
if(/^\d/.test(m))return{b:m+' alacak',alt:''};
if(!o.toplam)return{b:m||'Kamu ilanı',alt:''};
if(/,/.test(m))return{b:sayiTr(o.toplam)+' personel alacak',alt:m};
return{b:sayiTr(o.toplam)+' '+m+' alacak',alt:''};}
let mansetL=[],mansetSira=0,mansetImza='',mansetZaman=null,mansetDur=null,mansetUstunde=false,mansetOdakta=false,mansetSuruk=false;
const azHareket=()=>{try{return matchMedia('(prefers-reduced-motion: reduce)').matches;}catch{return false;}};
function mansetSaat(){
clearTimeout(mansetZaman);mansetZaman=null;
if(mansetDur===null)mansetDur=azHareket();
if(mansetDur||mansetUstunde||mansetOdakta||mansetSuruk||document.hidden||mansetL.length<2||(tab!=='bugun'&&tab!=='ilanlar'))return;
const t=()=>{mansetGit(mansetSira+1);mansetZaman=setTimeout(t,6000);};mansetZaman=setTimeout(t,6000);}
function mansetGuncelle(){
const root=$('manset');if(!root)return;
root.querySelectorAll('.slayt').forEach((s,i)=>{s.hidden=i!==mansetSira;});
root.querySelectorAll('.manset-nokta button').forEach((b,i)=>{if(i===mansetSira)b.setAttribute('aria-current','true');else b.removeAttribute('aria-current');});
const d=$('manset-dur');if(d){d.innerHTML=mansetDur?IC.oynat:IC.dur;d.setAttribute('aria-label',mansetDur?'Manşeti otomatik oynat':'Otomatik geçişi durdur');}}
/* yon: -1 geri, 1 ileri (yeni slayt o yönden kayarak girer); 0/yok: aşağıdan belirir. */
function mansetGit(i,kullanici,yon){const n=mansetL.length;if(!n)return;const root=$('manset'),sl=root&&root.querySelector&&root.querySelector('.manset-slaytlar');
if(sl&&sl.style&&sl.style.setProperty){sl.style.setProperty('--gx',(yon?yon*48:0)+'px');sl.style.setProperty('--gy',yon?'0px':'6px');}
mansetSira=((i%n)+n)%n;mansetGuncelle();if(kullanici)mansetSaat();}
/* Sürükleme / kaydırma: fare ve dokunma (pointer events). Dikey kaydırma touch-action:pan-y ile tarayıcıya bırakılır. */
function mansetSurukle(sl){
const ESIK=40;let p=null,bastir=false;
const cur=()=>sl.querySelectorAll('.slayt')[mansetSira]||null;
const sifirla=(anim)=>{const c=cur();if(!c||!c.style)return;c.style.transition=anim&&!azHareket()?'transform .22s ease,opacity .22s ease':'none';c.style.transform='';c.style.opacity='';};
const bitir=(git)=>{
if(!p)return;const d=p.dx,sure=Math.max(1,Date.now()-p.t0),hiz=Math.abs(d)/sure,s=p.suruk;
try{if(p.cap&&sl.releasePointerCapture)sl.releasePointerCapture(p.id);}catch{}
p=null;if(!s)return;
mansetSuruk=false;bastir=true;setTimeout(()=>{bastir=false;},0);
const ilerle=git&&(Math.abs(d)>=ESIK||(hiz>0.45&&Math.abs(d)>12));
if(ilerle){sifirla(false);mansetGit(mansetSira+(d<0?1:-1),true,d<0?1:-1);}else{sifirla(true);mansetSaat();}};
sl.addEventListener('pointerdown',e=>{if(p||(e.pointerType==='mouse'&&e.button!==0)||mansetL.length<2)return;mansetEtkilesim=true;p={id:e.pointerId,x:e.clientX,y:e.clientY,dx:0,t0:Date.now(),suruk:false,cap:false};});
sl.addEventListener('pointermove',e=>{
if(!p||e.pointerId!==p.id)return;const dx=e.clientX-p.x,dy=e.clientY-p.y;
if(!p.suruk){if(Math.abs(dx)<8||Math.abs(dx)<Math.abs(dy)*1.2){if(Math.abs(dy)>14)p=null;return;}
p.suruk=true;mansetSuruk=true;clearTimeout(mansetZaman);mansetZaman=null;try{if(sl.setPointerCapture){sl.setPointerCapture(e.pointerId);p.cap=true;}}catch{}}
p.dx=dx;const c=cur();if(c&&c.style){c.style.transition='none';c.style.transform='translateX('+dx+'px)';c.style.opacity=String(Math.max(.35,1-Math.abs(dx)/320));}
if(e.cancelable)e.preventDefault();});
sl.addEventListener('pointerup',e=>{if(p&&e.pointerId===p.id)bitir(true);});
sl.addEventListener('pointercancel',e=>{if(p&&e.pointerId===p.id)bitir(false);});
/* Sürükleme sonrası bırakma, bağlantıyı açmasın. */
sl.addEventListener('click',e=>{if(bastir){e.preventDefault();e.stopPropagation();bastir=false;}},true);
sl.addEventListener('dragstart',e=>e.preventDefault());}
function renderManset(){
const root=$('manset');if(!root||!listeLoaded)return;
const L=mansetSecimi(),imz=L.map(o=>o.key).join();
if(imz===mansetImza&&root.dataset.hazir==='1'){mansetSaat();return;}
mansetImza=imz;root.dataset.hazir='1';mansetL=L;if(mansetSira>=L.length)mansetSira=0;
root.hidden=!L.length;if(!L.length){root.replaceChildren();return;}
const ic_=E('div','manset-ic'),sl=E('div','manset-slaytlar');
L.forEach((o,i)=>{
const s=E('article','slayt');s.setAttribute('role','group');s.setAttribute('aria-roledescription','slayt');s.setAttribute('aria-label',(i+1)+' / '+L.length+': '+o.kurum);s.hidden=i!==mansetSira;
const a=E('a','slayt-link'),tx=E('span','slayt-metin'),hb=mansetBaslik(o);a.href=ilanHref(o);a.setAttribute('data-a','manset_tikla');a.setAttribute('data-a-h',o.key);a.setAttribute('data-a-n',String(i+1));
tx.append(E('span','slayt-kurum',o.kurum||'Kurum belirtilmemiş'),E('strong','slayt-baslik',hb.b));if(hb.alt)tx.append(E('span','slayt-alt',hb.alt));
const t=E('span','slayt-tarih');t.append(ic('saat'),tarihAraligi(o));tx.append(t);
a.append(kurumGorseli(o,'slayt-logo',88),tx);s.append(a);sl.append(s);});
const kon=E('div','manset-kontrol'),nk=E('div','manset-nokta');nk.setAttribute('role','group');nk.setAttribute('aria-label','Manşet seç');
const ok=(ad,ikon,fark)=>{const b=E('button','manset-ok manset-yon manset-'+(fark<0?'onceki':'sonraki'));b.type='button';b.setAttribute('data-a','manset_ok');b.setAttribute('data-a-x',fark<0?'onceki':'sonraki');b.setAttribute('aria-label',ad);b.innerHTML=OKLAR[ikon];b.onclick=()=>{mansetEtkilesim=true;mansetGit(mansetSira+fark,true,fark);};return b;};
L.forEach((o,i)=>{const b=E('button','',String(i+1));b.type='button';b.setAttribute('aria-label',(i+1)+'. manşet: '+o.kurum);b.setAttribute('data-a','manset_nokta');b.setAttribute('data-a-n',String(i+1));b.onclick=()=>{mansetEtkilesim=true;mansetGit(i,true,Math.sign(i-mansetSira));};nk.append(b);});
const dur=E('button','manset-ok manset-dur');dur.type='button';dur.id='manset-dur';dur.onclick=()=>{mansetEtkilesim=true;mansetDur=!mansetDur;mansetSaat();mansetGuncelle();};
kon.append(nk,dur);
const sahne=E('div','manset-sahne');if(L.length>1)sahne.append(ok('Önceki manşet','sol',-1));sahne.append(sl);if(L.length>1)sahne.append(ok('Sonraki manşet','sag',1));
ic_.append(sahne,kon);root.replaceChildren(ic_);mansetSurukle(sl);
root.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();mansetEtkilesim=true;mansetGit(mansetSira+(e.key==='ArrowLeft'?-1:1),true,e.key==='ArrowLeft'?-1:1);const b=root.querySelectorAll('.manset-nokta button')[mansetSira];if(b&&b.focus&&e.target&&e.target.closest&&e.target.closest('.manset-nokta'))b.focus();}};
root.onmouseenter=()=>{mansetUstunde=true;mansetSaat();};root.onmouseleave=()=>{mansetUstunde=false;mansetSaat();};
root.onfocusin=()=>{mansetOdakta=true;mansetSaat();};root.onfocusout=e=>{if(!e.relatedTarget||!root.contains(e.relatedTarget)){mansetOdakta=false;mansetSaat();}};
mansetGuncelle();mansetSaat();}
/* Zaman çizelgesi: yayın gününe göre gruplar (en yeni gün önce); grup içinde süzgeç sırası korunur. */
function zamanGruplari(rows){
const gr=new Map();for(const o of rows){const d=o.ilk_gorulme?istDate(Date.parse(o.ilk_gorulme)):'';if(!gr.has(d))gr.set(d,[]);gr.get(d).push(o);}
return [...gr].sort((a,b)=>!a[0]?1:!b[0]?-1:b[0].localeCompare(a[0]));}
function rozetOf(o,res){
if(o.kurum_ici)return E('span','rozet','Kurum içi');
if(closed(o))return E('span','rozet soluk','Sona erdi');
if(!upcoming(o)&&o.son_tarih){const g=days(o.son_tarih);if(g!==null&&g<=3)return E('span','rozet'+(g<=1?' acil':' yakin'),g<=0?'Son gün':g===1?'Yarın son gün':g+' gün kaldı');}
if(res&&res.seviye&&res.seviye.get(o.key)==='alt')return E('span','rozet soluk','Alt düzey');
return null;}
function satirEl(o,res){
const n=E('article','satir'),g=E('div','satir-govde'),k=E('p','satir-kurum');
if(o.kurum_slug){const a=E('a','',o.kurum||'Kurum');a.setAttribute('data-a','kurum_tikla');a.setAttribute('data-a-h',o.kurum_slug);a.href='kurum/'+o.kurum_slug+'/';a.title=(o.kurum||'Kurum')+' — kurumun tüm ilanları';k.append(a);}else k.append(o.kurum||'Kurum belirtilmemiş');
const h=E('h3','satir-baslik'),a=E('a','satir-link',o.manset||'Kamu ilanı');a.href=ilanHref(o);a.setAttribute('data-a','satir_tikla');a.setAttribute('data-a-h',o.key);h.append(a);if(o.ek)h.append(' ',E('span','ek','+'+o.ek));
h.append(' ',E('span','satir-tarih','('+tarihAraligi(o)+')'));g.append(k,h);
const alt=[o.il,o.ogrenim.map(x=>LEVELS[x]).join(' / '),o.toplam&&!/^\d/.test(o.manset)?sayiTr(o.toplam)+' kadro':''].filter(Boolean);
if(alt.length)g.append(E('p','satir-alt',alt.join(' · ')));
const sag=E('div','satir-sag'),r=rozetOf(o,res);if(r)sag.append(r);sag.append(saveButton(o));
n.append(kurumGorseli(o,'satir-logo',40),g,sag);return n;}
function gunGrubu(d,rows,res){
const s=E('section','zg'),t=E('h2','gun-tarih'),ul=E('ul','gun-liste');s.id='gun-'+(d||'tarihsiz');
if(d){const [,m,g]=d.split('-').map(Number),f=days(d),et=f===0?'Bugün':f===-1?'Dün':gunAdi(d);t.append(E('strong','',String(g)),E('span','',AYU[m-1]),E('em',f===0||f===-1?'':'gunadi',et));t.setAttribute('aria-label',g+' '+AYU[m-1]+' '+et+': '+rows.length+' ilan eklendi');if(f===0)s.className='zg bugun';}
else{t.append(E('strong','','—'),E('span','','Tarihsiz'));t.setAttribute('aria-label','Yayın tarihi bilinmeyen ilanlar');}
for(const o of rows){const li=E('li');li.append(satirEl(o,res));ul.append(li);}
s.append(t,ul);return s;}
/* ---------- İlanlar: süzgeç durumu, URL eşitleme, süzme ---------- */
const OGR_SECENEK=[['lisans','Lisans'],['onlisans','Önlisans'],['ortaogretim','Ortaöğretim'],['bilinmiyor','Öğrenim belirtilmemiş'],['belediye','Belediye ilanları']];
const SB_SECENEK=[['2','Son 2 gün'],['3','Son 3 gün'],['7','Son 7 gün'],['14','Son 14 gün'],['yakinda','Yakında açılacak']];
const SIRA_SECENEK=[['son','Son tarih: en yakın'],['yeni','En yeni eklenen'],['kurum','Kurum: A–Z']];
const QKEYS=['q','il','ogr','sb','tur','kat','yeni','uygun','sira','arsiv'];
const defaultF=()=>({q:'',il:[],ogr:'',sb:'',tur:'',kat:'',yeni:false,uygun:null,sira:'son',arsiv:false});
let F=defaultF(),bootQuery=false;
const ilSlug=il=>normalize(il);
/* ?q=&il=&ogr=&sb=&tur=&yeni=1&uygun=0&sira=&arsiv=1 → süzgeç; bilinmeyen/bozuk değerler atılır. */
function parseQuery(search){
const sp=new URLSearchParams(search),f=defaultF();
f.q=str(sp.get('q')||'',80).trim();
f.il=[...new Set((sp.get('il')||'').split(',').map(x=>IL_LIST.find(il=>ilSlug(il)===normalize(x).trim())).filter(Boolean))].slice(0,10);
const ogr=sp.get('ogr');f.ogr=OGR_SECENEK.some(x=>x[0]===ogr)?ogr:'';
const sb=sp.get('sb');f.sb=SB_SECENEK.some(x=>x[0]===sb)?sb:'';
f.tur=str(sp.get('tur')||'',60);const kat=sp.get('kat');f.kat=KATEGORI.some(x=>x[0]===kat)?kat:'';f.yeni=sp.get('yeni')==='1';
const u=sp.get('uygun');f.uygun=u==='0'?false:u==='1'?true:null;
const s=sp.get('sira');f.sira=SIRA_SECENEK.some(x=>x[0]===s)?s:'son';f.arsiv=sp.get('arsiv')==='1';
return f;}
const queryHas=search=>{const sp=new URLSearchParams(search);return QKEYS.some(k=>sp.has(k));};
/* Profil varken "Profilime uygun" varsayılan açıktır; yalnız kapalıyken (uygun=0) yazılır. */
function queryOf(f,profilVar){
const sp=new URLSearchParams();
if(f.q)sp.set('q',f.q);if(f.il.length)sp.set('il',f.il.map(ilSlug).join(','));if(f.ogr)sp.set('ogr',f.ogr);if(f.sb)sp.set('sb',f.sb);if(f.tur)sp.set('tur',f.tur);if(f.kat)sp.set('kat',f.kat);if(f.yeni)sp.set('yeni','1');
if(f.uygun===false)sp.set('uygun','0');else if(f.uygun===true&&!profilVar)sp.set('uygun','1');
if(f.sira!=='son')sp.set('sira',f.sira);if(f.arsiv)sp.set('arsiv','1');
return sp.toString();}
/* Adres çubuğundaki süzgeç parametreleri İlanlar sekmesindeyken güncel tutulur, başka sekmede temizlenir. */
function syncQuery(){
try{const u=new URL(location.href),sp=new URLSearchParams(u.search);for(const k of QKEYS)sp.delete(k);
const rest=[sp.toString(),viewOf(tab)==='ana'?queryOf(F,!!activeProfile()):''].filter(Boolean).join('&'),next=u.pathname+(rest?'?'+rest:'')+u.hash;
if(next!==u.pathname+u.search+u.hash)history.replaceState(null,'',next);}catch{}}
const fullOf=o=>fmap.get(o.key)||null;
const aramaTek=o=>{const f=fullOf(o);return f?f.search:normalize([o.manset,o.kurum,o.il,...o.iller].join(' '));};
const aramaMetni=o=>(sec.get(o.key)||[]).reduce((t,k)=>{const r=lmap.get(k);return r?t+' '+aramaTek(r):t;},aramaTek(o));
/* Profil dışındaki tüm süzgeçler. Metin araması tam kayıt gelene kadar satır alanlarında yapılır. */
function rowMatches(o,f){
if(!f.arsiv&&closed(o))return false;
if(f.il.length&&!f.il.some(x=>ilKeys(o).includes(normalize(x)))&&!(f.ogr==='bilinmiyor'&&ulusal(o)))return false;
if(f.ogr==='bilinmiyor'){if(rowLevels(o).length||o.kurum_ici)return false;}
else if(f.ogr&&!rowLevels(o).includes(f.ogr)&&o.kategori!==f.ogr)return false;
if(f.tur&&turLabel(o.ilan_turu)!==f.tur)return false;
if(f.kat&&katOf(o)!==f.kat)return false;
if(f.sb==='yakinda'){if(!upcoming(o))return false;}
else if(f.sb&&!(o.son_tarih&&!closed(o)&&!upcoming(o)&&days(o.son_tarih)<=Number(f.sb)))return false;
if(f.yeni&&!isNew(o))return false;
const q=normalize(f.q).trim().split(/\s+/).filter(Boolean);
if(q.length){const t=aramaMetni(o);if(!q.every(w=>t.includes(w)))return false;}
return true;}
function sortRows(list,f){
const byDl=(a,b)=>Number(closed(a))-Number(closed(b))||(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999')||a.kurum.localeCompare(b.kurum,'tr');
/* Liste yayın gününe göre gruplanıp ilk sayfası kesildiği için varsayılan sıra en yeni gün önce; gün içinde son başvuruya göre. */
const gun=o=>o.ilk_gorulme?istDate(Date.parse(o.ilk_gorulme)):'',byGun=(a,b)=>gun(b).localeCompare(gun(a))||byDl(a,b);
const cmp=f.sira==='yeni'?(a,b)=>(Date.parse(b.ilk_gorulme)||0)-(Date.parse(a.ilk_gorulme)||0):f.sira==='kurum'?(a,b)=>a.kurum.localeCompare(b.kurum,'tr'):f.sb==='yakinda'?(a,b)=>(Date.parse(a.baslangic_zaman)||0)-(Date.parse(b.baslangic_zaman)||0):byGun;
return list.slice().sort(cmp);}
const uygunAcik=(f,pr)=>!!pr&&f.uygun!==false;
function filterIlan(base,f,pr){
const a=base.filter(o=>rowMatches(o,f)),on=uygunAcik(f,pr),seviye=new Map();let bilinmiyor=0;
const u=pr?a.filter(o=>{const s=uygun(o,pr);if(s==='bilinmiyor'){bilinmiyor++;return f.ogr==='bilinmiyor';}if(s)seviye.set(o.key,s);return !!s;}):[];
let list=sortRows(on?u:a,f);
if(on)list=list.sort((x,y)=>Number(seviye.get(x.key)==='alt')-Number(seviye.get(y.key)==='alt')||ilRank(x,pr)-ilRank(y,pr));
return{list,seviye,tum:a.length,uyan:u.length,disinda:on?a.length-u.length:0,bilinmiyor:f.ogr==='bilinmiyor'?0:bilinmiyor,on};}
const suzgecVar=f=>!!(f.q||f.il.length||f.ogr||f.sb||f.tur||f.kat||f.yeni||f.arsiv);
const ilanBase=f=>f.arsiv&&loaded?items.filter(i=>!i.duyuru_turu&&!i.iptal_edildi).map(rowOf).filter(o=>!gizli.has(o.key)):liste;
const bekleniyor=f=>!loaded&&f.arsiv;
/* Tür etiketleri kaynakta tutarsız (sonda "İlanları" eki); gösterimde ve süzmede ek atılır. */
const turLabel=t=>String(t||'').replace(/\s+İlan(?:ı|ları)$/,'').trim();
function turSecenekleri(){const m=new Map();for(const o of liste){if(closed(o))continue;const t=turLabel(o.ilan_turu);if(t)m.set(t,(m.get(t)||0)+1);}return [...m].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'tr'));}
function openIlanlar(patch){
F={...defaultF(),...patch};shown=PAGE_SIZE;$('search').value=F.q;
try{const u=new URL(location.href),q=queryOf(F,!!activeProfile());const next=u.pathname+(q?'?'+q:'')+'#ilanlar';if(tab!=='ilanlar'||next!==u.pathname+u.search+u.hash)history.pushState(null,'',next);}catch{}
lastHref=location.href;showTab('ilanlar');}
function ilanLink(text,patch,cls){
const a=E('a',cls||'yazi-link',text+' ');a.append(ic('sag'));const q=queryOf({...defaultF(),...patch},true);a.href=(q?'?'+q:'./')+'#ilanlar';
a.onclick=e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button>0)return;e.preventDefault();openIlanlar(patch);};return a;}
function ilanDegisti(){shown=PAGE_SIZE;render();}
/* ---------- Ana sayfa: yan sütun (kategori ağacı + süzgeçler) ---------- */
const KATEGORI=[['memur','Memur'],['sozlesmeli','Sözleşmeli Personel'],['isci','İşçi'],['akademik','Akademik Personel'],['diger','Diğer']];
const KAT_IKON={tum:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>',memur:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="7" width="17" height="12.5" rx="2"/><path d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M3.5 12.5h17"/></svg>',sozlesmeli:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.5h7l4 4V20a.5.5 0 0 1-.5.5h-10A.5.5 0 0 1 7 20z"/><path d="M14 3.5V8h4M10 12.5h5M10 16h5"/></svg>',isci:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17.5h16M6 17.5V14a6 6 0 0 1 12 0v3.5M12 8V5.5M10 5.5h4"/></svg>',akademik:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 9.5 9-4.5 9 4.5-9 4.5z"/><path d="M7 11.5V16c1.5 1.5 3 2 5 2s3.5-.5 5-2v-4.5M21 9.5v5"/></svg>',diger:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="18" cy="12" r="1.3"/></svg>',belediye:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20.5h16M5.5 20.5V10M18.5 20.5V10M9.5 20.5v-5h5v5M3.5 10 12 4l8.5 6z"/></svg>'};
/* İlan türü etiketinden (ve kaynak kategorisinden) üst kategori. */
function katOf(o){
const t=normalize(turLabel(o.ilan_turu));
if(o.kategori==='akademik'||/akademik|ogretim (uyesi|elemani|gorevlisi)/.test(t))return 'akademik';
if(o.kategori==='isci'||/isci/.test(t))return 'isci';
if(/sozlesmeli/.test(t))return 'sozlesmeli';
if(/memur|kamu personeli|uzman|kariyer|mufettis|denetci|kontrolor/.test(t))return 'memur';
return 'diger';}
const ilSayilari=()=>{const m=new Map();for(const o of liste){if(closed(o))continue;for(const k of new Set(ilKeys(o))){const il=IL_LIST.find(x=>ilSlug(x)===k);if(il)m.set(il,(m.get(il)||0)+1);}}return m;};
/* Kategori sayıları: arama/il/öğrenim/tarih süzgeçleri uygulanır, kategori ve tür seçimi uygulanmaz (profil eşleşmesi de). */
function katSayilari(){
const f={...F,kat:'',tur:''},m=new Map(),t=new Map();let tum=0,bel=0;
for(const o of ilanBase(f)){if(!rowMatches(o,{...f,ogr:f.ogr==='belediye'?'':f.ogr}))continue;if(o.kategori==='belediye')bel++;if(f.ogr==='belediye'&&o.kategori!=='belediye')continue;tum++;const k=katOf(o);m.set(k,(m.get(k)||0)+1);const l=turLabel(o.ilan_turu);if(l){if(!t.has(k))t.set(k,new Map());t.get(k).set(l,(t.get(k).get(l)||0)+1);}}
return{tum,m,t,bel};}
const mobilYan=()=>{try{return matchMedia('(max-width:900px)').matches;}catch{return false;}};
let yanAcik=false;
function yanAc(on){yanAcik=on;const p=$('yan-panel'),b=$('yan-ac');if(p&&p.classList)p.classList.toggle('acik',on);if(b)b.setAttribute('aria-expanded',String(on));}
/* Mobilde seçimden sonra panel kapanır ve liste görünür. */
function yanSecildi(){if(!mobilYan())return;yanAc(false);const l=$('ilanlar');if(l&&l.scrollIntoView)l.scrollIntoView({block:'start'});}
function katLink(id,ad,sayi,secili,patch,ikon,cls){
const a=E('a','agac-a'+(secili?' secili':'')+(cls?' '+cls:''));const q=queryOf({...defaultF(),...patch},!!activeProfile());a.href=(q?'?'+q:'./')+'#ilanlar';a.dataset.odak='kat-'+id;
if(secili)a.setAttribute('aria-current','true');
if(ikon){const i=E('i');i.innerHTML=KAT_IKON[ikon]||'';a.append(i);}
a.append(E('span','',ad),E('small','',String(sayi)));
a.onclick=e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button>0)return;e.preventDefault();A('tikla',{a:'kategori',h:patch.kat||patch.ogr||'tum',x:patch.tur||''});F={...F,kat:'',tur:'',...patch};if(F.ogr==='belediye'&&patch.ogr!=='belediye')F.ogr='';ilanDegisti();yanSecildi();};return a;}
function renderKategori(){
const box=$('kategoriler');if(!box)return;
const s=katSayilari(),ul=E('ul','agac'),tumSecili=!F.kat&&!F.tur&&F.ogr!=='belediye';
const li0=E('li');li0.append(katLink('tum','Tüm İlanlar',s.tum,tumSecili,{},'tum'));ul.append(li0);
for(const [k,ad] of KATEGORI){
const n=s.m.get(k)||0,altlar=[...(s.t.get(k)||new Map())].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'tr'));
if(!n&&F.kat!==k&&!altlar.some(x=>x[0]===F.tur))continue;
const acik=F.kat===k||altlar.some(x=>x[0]===F.tur),li=E('li');
li.append(katLink(k,ad,n,F.kat===k&&!F.tur,{kat:k},k,'kok'));
const anlamli=altlar.filter(x=>normalize(x[0])!==normalize(ad));
if(acik&&anlamli.length){const alt=E('ul','agac-alt');for(const [l,c] of altlar){const ali=E('li');ali.append(katLink('tur-'+normalize(l).replace(/[^a-z0-9]+/g,'-'),l,c,F.tur===l,{tur:l},null));alt.append(ali);}li.append(alt);}
ul.append(li);}
if(s.bel){const li=E('li','agac-ayrac');li.append(katLink('belediye','Belediye ilanları',s.bel,F.ogr==='belediye',{ogr:'belediye'},'belediye'));ul.append(li);}
box.replaceChildren(ul);}
function secim(id,etiket,secenekler,deger,degis){
const w=E('div','secim'),l=E('label','',etiket),s=E('select');s.id=id;l.htmlFor=id;s.dataset.odak=id;
for(const [v,t] of secenekler){const o=E('option','',t);o.value=v;if(v===deger)o.selected=true;s.append(o);}
s.value=deger;s.onchange=()=>{A('tikla',{a:'filtre',h:id.replace(/^f-/,''),x:s.value||'tumu'});degis(s.value);ilanDegisti();};w.append(l,s);return w;}
function renderSuzgec(res,pr){
const box=$('suzgecler');if(!box)return;
const say=ilSayilari(),iller=IL_LIST.filter(il=>say.has(il)||F.il.includes(il)),ilSec=[['','Tüm iller']];
if(F.il.length>1)ilSec.push(['*',F.il.slice(0,3).join(', ')+(F.il.length>3?' +'+(F.il.length-3):'')]);
for(const il of iller)ilSec.push([ilSlug(il),il+' ('+(say.get(il)||0)+')']);
const kids=[E('p','yan-baslik','Filtreler'),
secim('f-il','İl',ilSec,F.il.length>1?'*':F.il.length?ilSlug(F.il[0]):'',v=>{if(v==='*')return;F.il=v?[IL_LIST.find(x=>ilSlug(x)===v)].filter(Boolean):[];}),
secim('f-ogr','Öğrenim düzeyi',[['','Tüm düzeyler'],...OGR_SECENEK.filter(x=>x[0]!=='belediye')],F.ogr==='belediye'?'':F.ogr,v=>{F.ogr=v;}),
secim('f-sb','Son başvuru',[['','Tüm tarihler'],...SB_SECENEK],F.sb,v=>{F.sb=v;})];
const ar=E('label','yan-onay'),ac=E('input');ac.type='checkbox';ac.id='f-arsiv';ac.dataset.odak='f-arsiv';ac.checked=!!F.arsiv;ac.onchange=()=>{A('tikla',{a:'filtre',h:'arsiv',x:ac.checked?'acik':'kapali'});F.arsiv=ac.checked;ilanDegisti();};ar.append(ac,' Sona erenler dahil');kids.push(ar);
/* Profil yalnız üst bardaki simgeden açılır; profil varsa tek bir "uygun" filtresi görünür. */
if(pr){const u=E('label','yan-onay'),c=E('input');c.type='checkbox';c.id='f-uygun';c.dataset.odak='f-uygun';c.checked=!!(res&&res.on);c.onchange=()=>{A('tikla',{a:'filtre',h:'uygun',x:c.checked?'acik':'kapali'});F.uygun=c.checked;ilanDegisti();};
u.append(c,' Yalnız profilime uygun ',E('small','',String(res?res.uyan:0)));kids.push(u);}
box.replaceChildren(...kids);
const n=[F.il.length,F.ogr&&F.ogr!=='belediye',F.sb,F.arsiv,F.kat||F.tur||F.ogr==='belediye'].filter(Boolean).length,ys=$('yan-ac-sayi');if(ys){ys.textContent=String(n);ys.hidden=!n;}}
/* Yeniden çizimde odaktaki denetim (data-odak) korunur. */
function renderYan(res,pr){
let anahtar=null;try{const a=document.activeElement;anahtar=a&&a.dataset?a.dataset.odak:null;}catch{}
renderKategori();renderSuzgec(res,pr);
if(anahtar){const y=document.querySelector&&document.querySelector('[data-odak="'+anahtar+'"]');if(y&&y.focus)y.focus({preventScroll:true});}}
function listeAdi(){if(F.tur)return F.tur;if(F.kat)return (KATEGORI.find(x=>x[0]===F.kat)||[0,'Tüm İlanlar'])[1];if(F.ogr==='belediye')return 'Belediye ilanları';return 'Tüm İlanlar';}
function renderIlanlar(){
const pr=activeProfile();
if(!loaded&&(F.q||F.arsiv))ensureFull();
if(F.tur&&listeLoaded&&!turSecenekleri().some(x=>x[0]===F.tur))F.tur='';
$('liste-ad').textContent=listeAdi();
if(bekleniyor(F)){$('result-count').textContent='İlanlar yükleniyor…';$('filter-summary').textContent='';$('cards').replaceChildren();$('cards').hidden=true;$('empty').hidden=true;$('disinda').hidden=true;renderYan(null,pr);return;}
const res=filterIlan(ilanBase(F),F,pr),list=res.list,vis=list.slice(0,shown);
renderYan(res,pr);
sonSayi=list.length;$('result-count').textContent=list.length+' ilan';
/* Yalnız profil filtresi açıkken, öğrenim şartı okunamayan ilanlara tek bağlantı (sessizce gizlenmesinler). */
{const fs=$('filter-summary');
if(res.on&&res.bilinmiyor>0){const b=E('button','yazi-link',res.bilinmiyor+' ilanın öğrenim şartı okunamadı · göster');b.type='button';b.onclick=()=>{Object.assign(F,bilinmiyorYama(pr));ilanDegisti();};fs.replaceChildren(b);}else fs.replaceChildren();}
$('clear').hidden=!suzgecVar(F);
const nodes=zamanGruplari(vis).map(([d,rows])=>gunGrubu(d,rows,res));
if(list.length>vis.length){
const d=E('div','daha'),bar=E('div','bar'),fill=E('i'),b=E('button','btn btn-ikinci','Daha fazla göster');
fill.style.width=Math.round(vis.length/list.length*100)+'%';bar.setAttribute('aria-hidden','true');bar.append(fill);b.type='button';b.onclick=()=>{A('tikla',{a:'daha_fazla',n:shown+PAGE_SIZE});shown+=PAGE_SIZE;renderIlanlar();};
d.append(bar,E('small','',vis.length+' / '+list.length+' ilan gösteriliyor'),b);nodes.push(d);}
$('cards').replaceChildren(...nodes);$('cards').hidden=!list.length;$('empty').hidden=!!list.length;
if(!list.length){
const q=F.q.slice(0,60),kids=[E('h3','',q?'“'+q+'” için açık ilan bulunamadı.':'Bu filtrelerle ilan bulunamadı.')];
if(suzgecVar(F)){const b=E('button','btn btn-ikinci','Filtreleri temizle');b.type='button';b.onclick=temizle;kids.push(b);}
if(res.on&&res.disinda>0){const b=E('button','btn btn-ikinci','Profilimin dışındaki '+res.disinda+' ilanı göster');b.type='button';b.onclick=()=>{F.uygun=false;ilanDegisti();};kids.push(b);}
$('empty').replaceChildren(...kids);}
const dis=$('disinda');dis.hidden=!(res.on&&res.disinda>0&&list.length);
if(!dis.hidden){const s=E('span'),b=E('button','yazi-link','Tümünü göster ');b.type='button';b.append(ic('sag'));b.onclick=()=>{F.uygun=false;ilanDegisti();};s.append('Profilinin dışında ',E('b','',String(res.disinda)),' açık ilan daha var — diğer iller ve öğrenim düzeyleri.');dis.replaceChildren(s,b);}
syncQuery();renderCompare();}
/* Açılışta bekleyen kaydırma: #ilanlar → listeye, ?g=bugun → bugünün grubuna (yoksa listeye). Veri gelince bir kez uygulanır. */
let bekleyenKaydirma=null;
function kaydirmaUygula(){
if(!bekleyenKaydirma||!listeLoaded||(tab!=='bugun'&&tab!=='ilanlar'))return;
const ne=bekleyenKaydirma;bekleyenKaydirma=null;
let t=ne==='bugun'?$('gun-'+today()):null;if(t&&t.classList)t.classList.add('vurgu');
if(!t||!t.parentNode)t=$('ilanlar');
try{if(t&&t.scrollIntoView)t.scrollIntoView({block:'start'});}catch{}}
function temizle(){const u=F.uygun;F={...defaultF(),uygun:u};$('search').value='';ilanDegisti();}
/* ---------- Takvim ---------- */
const GUN_KISA=['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'];
let tkSeg='tumu',ayOff=0;
const addGun=(s,n)=>new Date(Date.parse(s+'T12:00:00Z')+n*864e5).toISOString().slice(0,10);
const gunEtiket=g=>g<=0?'Bugün':g===1?'Yarın':g+' gün';
function takvimRows(seg){
const acik=liste.filter(o=>!closed(o)),p=activeProfile();
return seg==='uygun'?(p?acik.filter(o=>eslesen(uygun(o,p))):[]):seg==='kayitli'?acik.filter(isSaved):acik;}
/* Son başvuru gününe göre gruplar (en yakın önce); tarihi olmayanlar ayrı. */
function takvimGruplari(rows){
const gr=new Map();
for(const o of rows.filter(o=>o.son_tarih).sort((a,b)=>a.son_tarih.localeCompare(b.son_tarih)||a.kurum.localeCompare(b.kurum,'tr'))){if(!gr.has(o.son_tarih))gr.set(o.son_tarih,[]);gr.get(o.son_tarih).push(o);}
return{gr,tarihsiz:rows.filter(o=>!o.son_tarih)};}
/* Yatay 14 günlük şerit: gün, sayı, acil/kayıtlı işareti. */
function seritGunleri(gr,kayGun){
const b=today(),out=[];
for(let n=0;n<14;n++){const d=addGun(b,n),c=(gr.get(d)||[]).length;out.push({d,n,c,acil:c>0&&n>=1&&n<=2,bugun:n===0,kayitli:kayGun.has(d)});}
return out;}
function ayHucreleri(gr,kayGun,off){
const t=today().split('-').map(Number),ay0=t[1]-1+off,y=t[0]+Math.floor(ay0/12),m=((ay0%12)+12)%12;
const ilk=(new Date(Date.UTC(y,m,1)).getUTCDay()+6)%7,say=new Date(Date.UTC(y,m+1,0)).getUTCDate(),h=[];
for(let g=1;g<=say;g++){const d=y+'-'+String(m+1).padStart(2,'0')+'-'+String(g).padStart(2,'0'),c=(gr.get(d)||[]).length;h.push({d,g,c,gecmis:d<today(),bugun:d===today(),kayitli:kayGun.has(d),seviye:d<today()||!c?0:c>=5?3:c>=3?2:1});}
return{yil:y,ay:m,bosluk:ilk,hucreler:h};}
function kadroBlok(o){
const d=E('div','kadro-blok');
if(o.toplam)d.append(E('strong','',sayiTr(o.toplam)),E('span','','kadro'));else d.append(E('strong','','—'),E('span','','kadro ilanda'));return d;}
function gotoGun(d){
let t=$('g'+d);
if(!t){const i=[...takvimGruplari(takvimRows(tkSeg)).gr.keys()].indexOf(d);if(i>=takvimGun){takvimGun=i+1;renderTakvim();t=$('g'+d);}}
if(t){let az=false;try{az=matchMedia('(prefers-reduced-motion: reduce)').matches;}catch{}t.scrollIntoView({behavior:az?'auto':'smooth',block:'start'});t.tabIndex=-1;if(t.focus)t.focus({preventScroll:true});}}
function takvimSol(gr,kayGun){
const sol=E('div'),kart=E('div','ay'),h=ayHucreleri(gr,kayGun,ayOff),bas=E('div','ay-bas'),nav=E('div','ay-nav');
const yon=(ad,ikon,fark)=>{const b=E('button','');b.type='button';b.setAttribute('aria-label',ad);b.innerHTML=IC[ikon];b.disabled=ayOff+fark<0||ayOff+fark>1;b.onclick=()=>{ayOff+=fark;renderTakvim();};return b;};
nav.append(yon('Önceki ay','sol',-1),yon('Sonraki ay','sag',1));
const bb=E('div');bb.append(E('b','',AYU[h.ay]+' '+h.yil),E('span','','kapanan ilan sayısı'));bas.append(bb,nav);
const izg=E('div','ay-izgara');for(const g of GUN_KISA)izg.append(E('small','',g.slice(0,2)));
for(let i=0;i<h.bosluk;i++)izg.append(E('span','hc'));
for(const c of h.hucreler){const cls='hc'+(c.gecmis?' gecmis':'')+(c.seviye?' l'+c.seviye:'')+(c.bugun?' bugun':'')+(c.kayitli?' kayitli':'');
const tip=c.g+' '+AYU[h.ay]+(c.c?': '+c.c+' ilan kapanıyor':'');
if(c.c&&!c.gecmis){const b=E('button',cls,String(c.g));b.type='button';b.setAttribute('aria-label',tip);b.title=tip;b.onclick=()=>gotoGun(c.d);izg.append(b);}
else{const s=E('span',cls,String(c.g));if(c.c)s.title=tip;izg.append(s);}}
const lj=E('div','lejant');for(const [c,t] of [['l1','1–2'],['l2','3–4'],['l3','5+']]){const s=E('span');s.append(E('i','l '+c),t);lj.append(s);}lj.append(E('span','','● kaydettiğin'));
kart.append(bas,izg,lj);sol.append(kart);
const yk=liste.filter(upcoming).sort((a,b)=>Date.parse(a.baslangic_zaman)-Date.parse(b.baslangic_zaman)),k=E('section','kutu');
k.append(E('h3','','Yakında açılacak'),E('p','','Başvuru tarihi henüz gelmedi.'));
if(yk.length){const ul=E('ul','mini');for(const o of yk.slice(0,5)){const li=E('li'),d=E('div');d.append(detailLink(o,o.manset),E('small','',o.kurum));li.append(d,E('em','',kisaTarih(istDate(o.baslangic_zaman))));ul.append(li);}k.append(ul);if(yk.length>5){const w=E('div','kutu-alt');w.append(ilanLink('Tümü ('+yk.length+')',{sb:'yakinda',uygun:false}));k.append(w);}}
else k.append(E('p','mbos','Şu an yakında açılacak ilan yok.'));
sol.append(k,railTelegram());return sol;}
function renderTakvim(){
const box=$('takvim-icerik');if(!box||!listeLoaded)return;
const p=activeProfile(),hepsi=takvimRows('tumu'),kay=takvimRows('kayitli'),up=p?takvimRows('uygun'):[];
for(const [k,n] of [['tumu',hepsi.length],['uygun',up.length],['kayitli',kay.length]]){const b=$('seg-'+k);if(!b)continue;b.className=k===tkSeg?'secili':'';b.setAttribute('aria-pressed',String(k===tkSeg));const s=$('segn-'+k);if(s)s.textContent=String(n);}
const rows=tkSeg==='uygun'?up:tkSeg==='kayitli'?kay:hepsi,{gr,tarihsiz}=takvimGruplari(rows),kayGun=new Set(kay.filter(o=>o.son_tarih).map(o=>o.son_tarih));
$('takvim-ozet').textContent=rows.length?rows.length+' ilan, son başvuru gününe göre. Önce en yakın.':'Son başvuru gününe göre, önce en yakın.';
const serit=$('takvim-serit');serit.replaceChildren();
for(const g of seritGunleri(gr,kayGun)){
const b=E('button','gun'+(g.bugun?' bugun':'')+(g.acil?' acil':'')+(g.c?'':' bos')+(g.kayitli?' kayitli':''));b.type='button';b.disabled=!g.c;
b.setAttribute('aria-label',uzunTarih(g.d)+' '+gunAdi(g.d)+(g.bugun?' (bugün)':'')+': '+(g.c?g.c+' ilan kapanıyor':'kapanan ilan yok')+(g.kayitli?', kaydettiğin ilan var':''));
const em=E('em');if(g.c)em.append(E('i'),String(g.c));b.append(E('small','',g.bugun?'Bugün':GUN_KISA[(new Date(g.d+'T12:00:00Z').getUTCDay()+6)%7]),E('strong','',String(Number(g.d.slice(8)))),em);b.onclick=()=>gotoGun(g.d);serit.append(b);}
$('takvim-sol').replaceChildren(takvimSol(gr,kayGun));
const out=[];let gizli=0;
[...gr].forEach(([d,l],ix)=>{const g=days(d);if(ix>=takvimGun&&g>13){gizli++;return;}
const sec=E('section','grup'),sol=E('div','grup-tarih'),sag=E('div'),kadro=l.reduce((s,o)=>s+(o.toplam||0),0);sec.id='g'+d;
sol.append(E('strong','',kisaTarih(d)),E('span','',gunAdi(d)),E('em',g<=2?'acil':'',gunEtiket(g)));
sag.append(E('p','grup-ozet',l.length+' ilan'+(kadro?' · '+sayiTr(kadro)+' kadro':'')+' · bu gün kapanıyor'),listeEl(l,{kadro:true,yeni:true}));sec.append(sol,sag);out.push(sec);});
if(!out.length&&!tarihsiz.length){const b=[];
if(tkSeg==='kayitli')b.push(E('p','','Kaydettiğin açık ilan yok. Bir ilanın yanındaki yer imi simgesine dokunarak kaydedebilirsin; son günleri burada görünür.'));
else if(tkSeg==='uygun'&&!p){b.push(E('p','','“Bana uygun” için önce profilini ayarla; öğrenim düzeyine ve illerine göre süzeriz.'));const bt=E('button','btn btn-ana','Profilimi ayarla');bt.type='button';bt.onclick=openProfile;b.push(bt);}
else b.push(E('p','','Bu görünümde açık ilan bulunmuyor.'));
out.push(bosKutu(...b));}
if(gizli){const b=E('button','btn btn-ikinci','Daha fazla gün göster ('+gizli+')'),w=E('div','daha');b.type='button';b.onclick=()=>{takvimGun+=7;renderTakvim();};w.append(b);out.push(w);}
if(tarihsiz.length){const sec=E('section','grup'),sol=E('div','grup-tarih'),sag=E('div');sec.id='g-tarihsiz';sol.append(E('strong','','Tarihi ilanda'),E('span','','kesin gün belirsiz'));sag.append(E('p','grup-ozet',tarihsiz.length+' ilanın son başvuru tarihi resmî ilanda belirtilir'),listeEl(tarihsiz,{kadro:true,yeni:true}));sec.append(sol,sag);out.push(sec);}
box.replaceChildren(...out);}
/* ---------- Kayıtlı ---------- */
function kayitliGruplari(rows){
const hafta=o=>!closed(o)&&!!o.son_tarih&&days(o.son_tarih)<=6,dl=(a,b)=>(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999');
return[['7 gün içinde kapanıyor',rows.filter(hafta).sort(dl)],['Daha sonra',rows.filter(o=>!closed(o)&&!!o.son_tarih&&!hafta(o)).sort(dl)],['Tarihi ilanda',rows.filter(o=>!closed(o)&&!o.son_tarih)],['Sona erdi',rows.filter(closed).sort((a,b)=>dl(b,a))]].filter(g=>g[1].length).map(([baslik,r])=>({baslik,rows:r}));}
const kayitliTakvimlik=()=>items.filter(i=>saved.has(i.id)&&i.son_tarih&&!closed(i)&&!i.duyuru_turu&&!i.iptal_edildi);
function renderKayitli(){
const box=$('kayitli-icerik');if(!box)return;
const by=new Map(listeTum.map(o=>[o.id,gizli.has(o.key)?(lmap.get(o.kopya_of)||o):o]));for(const i of items)if(!by.has(i.id))by.set(i.id,rowOf(i));
if(!loaded&&[...saved].some(id=>!by.has(id)))ensureFull();
const rows=[...new Map([...saved].map(id=>by.get(id)).filter(Boolean).map(o=>[o.key,o])).values()];
if(!rows.length){const a=E('a','btn btn-ana','İlanlara bak');a.href='#ilanlar';a.onclick=e=>{e.preventDefault();openIlanlar({uygun:false});};box.replaceChildren(bosKutu(E('p','','Henüz kaydettiğin ilan yok.'),E('p','','Bir ilanı kaydetmek için satırın sağındaki yer imi simgesine dokun. Kaydettiklerin burada, son başvuru gününe göre sıralı görünür; son günleri Takvim’de de işaretlenir.'),a));return;}
const bar=E('div','kayit-arac'),yazi=E('p','','Karşılaştırmak için iki veya üç ilanın “Karşılaştır” kutusunu işaretle.'),ics=E('button','btn btn-ikinci');
const n=loaded?kayitliTakvimlik().length:0;ics.type='button';ics.textContent='Takvimime ekle (.ics)'+(n?' · '+n:'');
ics.onclick=()=>{if(!loaded){notify('İlan ayrıntıları yükleniyor; birkaç saniye sonra yeniden dene.');ensureFull();return;}const l=kayitliTakvimlik();if(!l.length){notify('Takvime eklenecek açık ve tarihli kayıtlı ilan yok.');return;}A('tikla',{a:'takvim_ics',x:'kayitli',n:l.length});downloadCalendar(l);};
bar.append(yazi,ics);
const out=[bar];kayitliGruplari(rows).forEach((g,i)=>out.push(sectionEl('k-'+i,{baslik:g.baslik,sayi:g.rows.length,govde:listeEl(g.rows,{kars:true})})));
box.replaceChildren(...out);}
/* Rozet yalnızca bilinen (listede ya da tam kayıtta bulunan) kayıtlı ilanları sayar; veri gelmeden ham sayı gösterilir. */
function savedCount(){if(!listeLoaded&&!loaded)return saved.size;return new Set([...saved].map(id=>idKey.get(id)||(iids.has(id)?id:null)).filter(Boolean)).size;}
function render(){
if(!loaded&&!listeLoaded)return;
const n=savedCount();for(const id of ['saved-count','saved-count-m']){const e=$(id);if(e){e.textContent=n;e.hidden=!n;}}
if(viewOf(tab)==='ana'){renderManset();renderIlanlar();kaydirmaUygula();}else if(tab==='takvim')renderTakvim();else if(tab==='kayitli')renderKayitli();
renderCompare();sig=imza();}
/* ---------- gezinme ---------- */
function showTab(t){
const onceki=tab;tab=t;lastTab=t;A(izModal&&t===onceki?'ekran':'sayfa',{v:t});izModal=false;
for(const x of VIEWS){const v=$('v-'+x);if(v)v.hidden=x!==viewOf(t);}
document.querySelectorAll('[data-tab]').forEach(a=>{const on=a.dataset.tab===t;a.classList.toggle('aktif',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute&&a.removeAttribute('aria-current');});
navAc(false);
syncQuery();render();tryWriteVisit();if(t!==onceki)sekmeKaydir(t);if(viewOf(t)!=='ana')mansetSaat();}
/* Sekme değişince: İlanlar listeye, diğerleri sayfa başına. */
function sekmeKaydir(t){try{if(t==='ilanlar'){const l=$('ilanlar');if(l&&l.scrollIntoView)l.scrollIntoView({block:'start'});}else if(window.scrollTo)window.scrollTo(0,0);}catch{}}
let navAcik=false;
function navAc(on){navAcik=on;const tb=$('tb'),b=$('tb-ac');if(tb&&tb.classList)tb.classList.toggle('acik',on);if(b){b.setAttribute('aria-expanded',String(on));b.setAttribute('aria-label',on?'Menüyü kapat':'Menüyü aç');}}
function renderCompare(){const on=tab==='kayitli'&&compared.size>0;$('compare-bar').hidden=!on;$('compare-count').textContent=compared.size+' / 3 ilan seçildi';$('compare-open').disabled=compared.size<2;if(document.body)document.body.classList.toggle('kars-acik',on);}
function closeModal(){if($('modal').open)$('modal').close();document.title=defaultTitle;}
function route(){
const hash=location.hash.slice(1);
$('modal-back').href='#'+lastTab;
if(hash.startsWith('ilan/')||hash==='karsilastir'){if(!loaded){ensureFull().then(()=>{if(loaded)route();else notify('Ayrıntılı ilan verisi yüklenemedi.');});return;}}
if(hash.startsWith('ilan/')){let k;try{k=decodeURIComponent(hash.slice(5));}catch{k='';}const i=items.find(x=>x.key===k);if(i)showDetail(i);else{const h=E('h2','','Bu ilan artık listede bulunmuyor.');h.id='modal-title';$('modal-body').replaceChildren(h,E('p','','Güncel ilanları keşfedebilir veya resmî kaynağı kontrol edebilirsin.'),external('https://kariyerkapisi.gov.tr/isealim','Kariyer Kapısı ↗'));openModal();}}
else if(articles[hash])showArticle(hash);
else if(hash==='karsilastir'){A('sayfa',{v:'karsilastir'});showComparison();}
else{closeModal();if(TABS.includes(hash))showTab(hash);else if(hash==='')showTab(bootQuery?(bootQuery=false,'ilanlar'):'bugun');}}
function goTab(t){location.hash=t;}
/* ---------- son ziyaret ---------- */
const VISIT_RE=/^\d{4}-\d{2}-\d{2}T[0-9:.+Zz-]{5,40}$/;
const validVisit=s=>typeof s==='string'&&VISIT_RE.test(s)&&Date.parse(s)<=Date.now()?Date.parse(s):null;
/* Oturum boyunca sabit başlangıç: yeni etiketleri ve sayaçlar sayfa içinde tutarlı kalır. */
function frozenVisit(){
const stored=readStore('kit-son-ziyaret',null);
try{let v=sessionStorage.getItem('kit-sz-baz');if(v===null){v=validVisit(stored)!==null?stored:'-';sessionStorage.setItem('kit-sz-baz',v);}return v==='-'?null:validVisit(v);}catch{return validVisit(stored);}}
let visitDue=false,visitWritten=false;
function tryWriteVisit(){
if(!visitDue||visitWritten)return;
if(listeLoaded&&viewOf(tab)==='ana'&&document.visibilityState==='visible'){visitWritten=true;writeStore('kit-son-ziyaret',new Date().toISOString());}}
/* ---------- profil penceresi ---------- */
let draft=null,duzenleme=false,bolumDuzey='';
const PT_A=Array.from({length:48},(_,k)=>'P'+(k+1));
const kaydirKilidi=on=>{try{document.documentElement.style.overflow=on?'hidden':'';}catch{}};
/* Hata iletisi pencerenin içinde (toast, üst katmandaki <dialog>un arkasında kalır). */
function profilHata(msg,id){
const h=$('p-hata');h.textContent=msg;h.hidden=false;const f=id?$(id):null;
if(f){if(id!=='p-ogrenim')f.setAttribute('aria-invalid','true');const t=id==='p-ogrenim'&&f.querySelector?f.querySelector('button'):f;if(t&&t.focus)t.focus({preventScroll:true});}
if(h.scrollIntoView)h.scrollIntoView({block:'nearest'});}
function profilHataTemizle(){const h=$('p-hata');if(h){h.hidden=true;h.textContent='';}for(const id of ['p-puan','p-il'])$(id).removeAttribute('aria-invalid');}
/* Puan türü düzeye bağlı: tek seçenek (Lisans: + "Diğer (KPSS A)" -> P1–P48); düzey seçilmeden puan alanı kapalı. */
function fillTur(){
const d=draft,l=d.ogrenim,sel=$('p-tur'),sa=$('p-tur-a'),pu=$('p-puan');
sel.replaceChildren();sa.replaceChildren();pu.disabled=sel.disabled=!l;
$('p-puan-ipucu').textContent=l?'Puan türü öğrenim düzeyine göre belirlenir. Puanın yoksa boş bırak; yine de ilanları görürsün.':'Önce öğrenim düzeyini seç.';
if(!l){sa.hidden=true;return;}
const def=defaultTur(l),o1=E('option','',def);o1.value=def;sel.append(o1);
if(l==='lisans'){const o=E('option','','Diğer (KPSS A)');o.value='A';sel.append(o);for(const t of PT_A){const x=E('option','',t);x.value=t;sa.append(x);}}
const a=l==='lisans'&&ptLevel(d.puan_turu)==='lisans'&&d.puan_turu!==def;
sel.value=a?'A':def;sa.value=a?d.puan_turu:'P1';sa.hidden=!a;}
const formTur=()=>$('p-tur').value==='A'?$('p-tur-a').value:$('p-tur').value;
function fillForm(){
const d=draft,seg=$('p-ogrenim');seg.querySelectorAll('button').forEach(b=>{b.classList.toggle('secili',b.dataset.v===d.ogrenim);b.setAttribute('aria-pressed',String(b.dataset.v===d.ogrenim));});
fillTur();
$('p-puan').value=typeof d.puan==='number'?puanTr(d.puan):'';
$('p-tum').checked=!!d.tum_turkiye;$('p-bolum').value=d.bolum||'';$('p-il').value='';$('p-atla').textContent=duzenleme?'Vazgeç':'Şimdilik atla';
bolumDuzey='';$('p-bolum-liste').replaceChildren();profilHataTemizle();renderIller();}
/* Bölüm önerileri: puanlar sayfasındaki listeyle aynı kaynak (puanlar/<düzey>-bolum.json), ilk odakta yüklenir. */
async function bolumListeDoldur(){
const d=draft&&draft.ogrenim;if(!d||bolumDuzey===d)return;
try{const v=await getJSON('puanlar/'+d+'-bolum.json','no-cache');if(!draft||draft.ogrenim!==d||!v||typeof v.bolumler!=='object'||!v.bolumler)return;
const adlar=[...new Set(Object.values(v.bolumler).filter(x=>typeof x==='string'&&x.length<=120))].sort((a,b)=>a.localeCompare(b,'tr'));
$('p-bolum-liste').replaceChildren(...adlar.map(a=>{const o=E('option');o.value=a;return o;}));bolumDuzey=d;}catch{}}
function renderIller(){const box=$('p-iller');box.replaceChildren(...draft.iller.map(il=>{const c=E('span','il-cip',il),b=E('button');b.type='button';b.setAttribute('aria-label',il+' ilini kaldır');b.innerHTML=IC.x;b.onclick=()=>{draft.iller=draft.iller.filter(x=>x!==il);renderIller();};c.append(b);return c;}));}
/* Tam ad ya da tek eşleşen önek ("ank" -> Ankara); birden çok eşleşme belirsizdir. */
function ilCoz(raw){
const v=normalize(raw).trim();if(!v)return{bos:true};
const t=IL_LIST.find(x=>normalize(x)===v);if(t)return{il:t};
const on=IL_LIST.filter(x=>normalize(x).startsWith(v));
if(on.length===1)return{il:on[0]};
if(on.length>1)return{hata:'Birden fazla il eşleşiyor: '+on.slice(0,6).join(', ')+(on.length>6?' …':'')+'. Tam adı yaz.'};
return{hata:'İl adını listeden seç.'};}
function addIl(){const r=ilCoz($('p-il').value);if(r.bos)return true;if(r.hata){profilHata(r.hata,'p-il');return false;}if(!draft.iller.includes(r.il))draft.iller.push(r.il);$('p-il').value='';renderIller();return true;}
/* "75", "75,5", "75.47987" (en çok 5 ondalık); bilimsel/onaltılık gösterim, binlik ayırıcı ve fazlası reddedilir. */
function puanOku(raw){const m=String(raw||'').trim().match(/^(\d{1,3})(?:[.,](\d{1,5}))?$/);return m?Number(m[1]+'.'+(m[2]||'0')):NaN;}
function openProfile(){duzenleme=!!activeProfile();draft=duzenleme?{...profil,iller:[...profil.iller]}:{ogrenim:'',puan_turu:'',iller:[],tum_turkiye:false,bolum:''};fillForm();$('p-sifirla-kutu').hidden=!duzenleme;if(!$('profil-dialog').open){kaydirKilidi(true);$('profil-dialog').showModal();}}
/* Profili sıfırla: yalnız kit-profil silinir (Kayıtlı, tema, son ziyaret kalır); ekran profilsiz varsayılana döner. */
function resetProfile(){if(!confirm('Profil tercihlerin silinsin mi?'))return;try{localStorage.removeItem('kit-profil');}catch{}profil=null;draft=null;$('profil-dialog').close();kaydirKilidi(false);render();notify('Profilin sıfırlandı.');}
function saveProfile(){
profilHataTemizle();
if(!draft.ogrenim){profilHata('Önce öğrenim düzeyini seç.','p-ogrenim');return;}
if(!addIl())return;
const raw=$('p-puan').value.trim();let puan=null;
if(raw!==''){puan=puanOku(raw);if(!(puan>=40&&puan<=100)){profilHata('Puanı 40–100 arasında gir (örn. 82,15).','p-puan');return;}}
const p={v:1,ogrenim:draft.ogrenim,puan_turu:formTur(),iller:draft.iller,tum_turkiye:$('p-tum').checked,bolum:$('p-bolum').value.trim().slice(0,60),t:today()};if(puan!==null)p.puan=puan;
profil=validProfile(p);writeStore('kit-profil',profil);if(profil&&profil.ogrenim)A('tikla',{a:'profil_kaydet',x:profil.ogrenim,n:profil.iller.length});$('profil-dialog').close();kaydirKilidi(false);render();notify('Profilin kaydedildi.');}
function skipProfile(){if(duzenleme){$('profil-dialog').close();kaydirKilidi(false);return;}profil={v:1,atlandi:true,t:today()};writeStore('kit-profil',profil);$('profil-dialog').close();kaydirKilidi(false);render();}
function initProfile(){
const dl=$('il-listesi');IL_LIST.forEach(il=>{const o=E('option');o.value=il;dl.append(o);});
$('p-ogrenim').querySelectorAll('button').forEach(b=>b.onclick=()=>{draft.ogrenim=b.dataset.v;draft.puan_turu=defaultTur(b.dataset.v);bolumDuzey='';$('p-bolum-liste').replaceChildren();fillTur();profilHataTemizle();$('p-ogrenim').querySelectorAll('button').forEach(x=>{x.classList.toggle('secili',x===b);x.setAttribute('aria-pressed',String(x===b));});});
$('p-tur').onchange=()=>{$('p-tur-a').hidden=$('p-tur').value!=='A';profilHataTemizle();};
for(const id of ['p-puan','p-il','p-tur-a','p-tum','p-bolum'])$(id).addEventListener('input',profilHataTemizle);
$('p-bolum').addEventListener('focus',bolumListeDoldur);
$('p-il-ekle').onclick=addIl;$('p-il').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();addIl();}};
$('profil-form').onsubmit=e=>{e.preventDefault();saveProfile();};$('p-atla').onclick=skipProfile;$('p-sifirla').onclick=resetProfile;$('p-kapat').onclick=()=>{$('profil-dialog').close();kaydirKilidi(false);};$('nav-profile').onclick=openProfile;
$('profil-dialog').addEventListener('close',()=>kaydirKilidi(false));
$('profil-dialog').addEventListener('click',e=>{if(e.target===$('profil-dialog')){const r=$('profil-dialog').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('profil-dialog').close();}});}
/* ---------- tema, yükleme ---------- */
function applyTheme(){const dark=window.kitKoyu?window.kitKoyu():readStore('kit-theme',null)==='dark';document.documentElement.dataset.theme=dark?'dark':'light';const t=$('theme');if(!t.dataset.hazir){t.dataset.hazir='1';if(typeof requestAnimationFrame==='function')requestAnimationFrame(()=>requestAnimationFrame(()=>t.classList.add('anahtar-hazir')));}t.setAttribute('aria-pressed',String(dark));t.setAttribute('aria-label',dark?'Açık temaya geç':'Koyu temaya geç');const m=document.querySelector&&document.querySelector('meta[name=theme-color]');if(m)m.content=dark?'#0D0E0C':'#F6F6F1';}
async function loadSponsors(){try{const r=await fetch('sponsors.json',{cache:'no-store'});if(!r.ok)return;const cfg=await r.json();if(!cfg.enabled)return;for(const placement of ['sidebar','feed']){const s=cfg[placement],url=s&&safeURL(s.url);if(!s||!url||!s.title)continue;const box=E('aside','sponsor');box.setAttribute('aria-label','Reklam');box.append(E('span','eyebrow','REKLAM · SPONSORLU'));const a=external(url,s.title,'');a.rel='sponsored noopener noreferrer';box.append(a,E('p','',s.description||''));adBox[placement].replaceChildren(box);adBox[placement].hidden=false;}}catch{/* Optional sponsorship cannot break listing discovery. */}}
async function getJSON(url,cache){const r=await fetch(url,{cache});if(!r.ok)throw Error(url);return r.json();}
let sec=new Map(),lmap=new Map(),fmap=new Map(),iids=new Set(),lids=new Set(),fullPromise=null,fullFailed=false,sig='';
async function loadListe(){
try{const d=await getJSON('liste.json','no-cache');if(!d||!Array.isArray(d.ilanlar))throw Error('shape');
listeTum=d.ilanlar.map(cleanL).filter(Boolean);listeVar=true;listeZaman=typeof d.guncelleme==='string'&&!isNaN(Date.parse(d.guncelleme))?d.guncelleme:'';lmap=new Map(listeTum.map(o=>[o.key,o]));
/* Kopya (kaynaklar arası yinelenen) ikincil satırlar her listeden, sayıdan ve süzgeçten çıkar; kimlikleri birincile eşlenir. */
alias=new Map();gizli=new Set();sec=new Map();idKey=new Map();
for(const o of listeTum){const p=o.kopya_of&&lmap.get(o.kopya_of);if(p&&!p.kopya_of){gizli.add(o.key);alias.set(p.key,[...(alias.get(p.key)||[]),o.id]);sec.set(p.key,[...(sec.get(p.key)||[]),o.key]);idKey.set(o.id,p.key);}else idKey.set(o.id,o.id);}
liste=listeTum.filter(o=>!gizli.has(o.key));lids=new Set(listeTum.map(o=>o.id));listeLoaded=true;}catch{listeVar=false;}}
/* Tam kayıtlar (arama, ayrıntı penceresi, karşılaştırma) ilk gerektiğinde ya da boşta yüklenir. */
function ensureFull(){
if(fullPromise)return fullPromise;
if(fullFailed)return Promise.resolve();
fullPromise=(async()=>{
const [fr,gr]=await Promise.allSettled([getJSON('ilanlar.json','no-cache'),getJSON('ilan/gorseller.json','no-cache')]);
if(fr.status==='fulfilled'&&fr.value&&Array.isArray(fr.value.ilanlar)){
const data=fr.value,imgs=gr.status==='fulfilled'&&gr.value&&typeof gr.value==='object'?gr.value:{};
items=data.ilanlar.filter(i=>i&&typeof i.id==='string'&&typeof i.baslik==='string'&&i.kategori!=='akademik').map(i=>({...i,key:keyFor(i),location:proper(i.yer),...pickImages(imgs[keyFor(i)]),L:lmap.get(keyFor(i))||null,search:normalize([i.baslik,i.kurum,i.yer,i.kadro,i.ilan_turu,i.ozet,...(i.sartlar||[]).map(s=>s.kadro+' '+s.metin)].join(' '))}));
loaded=true;if(!listeZaman&&data.guncelleme)listeZaman=data.guncelleme;
if(!listeVar){liste=items.filter(i=>!i.duyuru_turu&&!i.iptal_edildi&&!closed(i)).map(fallbackModel);}
const failed=Object.entries(data.kaynak_durumlari||{}).filter(([,s])=>s.hata_sayisi>0).map(([k])=>({sbb:'SBB',csb:'ÇŞB Yerel Yönetimler'})[k]||'İŞKUR');
fmap=new Map(items.map(i=>[i.key,i]));iids=new Set(items.map(i=>i.id));
listeLoaded=true;}
else{fullPromise=null;fullFailed=true;if(tab==='ilanlar'&&bekleniyor(F)){F.tur='';F.arsiv=false;if(F.ogr==='belediye')F.ogr='';}$('result-count').textContent='Ayrıntılı ilan verisi yüklenemedi; yeniden denemek için sayfayı yenile.';}
render();})();
return fullPromise;}
async function load(){
populerYukle();
await loadListe();
if(listeVar){render();route();return;}
await ensureFull();
if(!loaded){$('result-count').textContent='';$('cards').hidden=false;$('cards').replaceChildren(E('p','not','İlan listesi yüklenemedi. Biraz sonra yeniden dene veya resmî ilan sayfalarını ziyaret et.'),external('https://kariyerkapisi.gov.tr/isealim','Resmî ilanlar ↗','btn btn-ikinci'));return;}
route();}
window.kitTemaUygula=applyTheme;applyTheme();$('year').textContent=new Date().getFullYear();
profil=validProfile(readStore('kit-profil',null));
sonZiyaret=frozenVisit();
let profilAc=false;
try{const u=new URL(location.href);if(u.searchParams.get('g')==='bugun')bekleyenKaydirma='bugun';if(u.searchParams.has('g')||u.searchParams.has('profil')){profilAc=u.searchParams.get('profil')==='1';u.searchParams.delete('g');u.searchParams.delete('profil');history.replaceState(null,'',u.pathname+u.search+u.hash);}}catch{}
let bootTab=TABS.includes(location.hash.slice(1))?location.hash.slice(1):'bugun';
try{const u=new URL(location.href);if(queryHas(u.search)){F=parseQuery(u.search);$('search').value=F.q;bootQuery=true;
if(location.hash===''){history.replaceState(null,'',u.pathname+u.search+'#ilanlar');bootTab='ilanlar';}}}catch{}
$('theme').onclick=()=>{A('tikla',{a:'tema',x:document.documentElement.dataset.theme==='dark'?'light':'dark'});writeStore('kit-theme',document.documentElement.dataset.theme==='dark'?'light':'dark');applyTheme();};
$('search-form').onsubmit=e=>{e.preventDefault();F.q=$('search').value.trim().slice(0,80);aramaIz();ilanDegisti();};
$('search').oninput=()=>{F.q=$('search').value.slice(0,80);if(F.q.trim())ensureFull();aramaIz();ilanDegisti();};
$('clear').onclick=temizle;
document.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>{F.q=b.dataset.query;$('search').value=F.q;ilanDegisti();});
document.querySelectorAll('[data-seg]').forEach(b=>b.onclick=()=>{tkSeg=b.dataset.seg;takvimGun=7;renderTakvim();});
if($('tb-ac'))$('tb-ac').onclick=()=>navAc(!navAcik);
document.querySelectorAll('.tb-nav a').forEach(a=>a.addEventListener('click',()=>navAc(false)));
if($('yan-ac'))$('yan-ac').onclick=()=>yanAc(!yanAcik);
if(document.addEventListener){document.addEventListener('keydown',e=>{if(e.key==='Escape'&&navAcik){navAc(false);const b=$('tb-ac');if(b&&b.focus)b.focus();}});
document.addEventListener('visibilitychange',()=>mansetSaat());}
const backToTab=()=>{location.hash=lastTab;};
$('modal-close').onclick=backToTab;$('modal').addEventListener('cancel',e=>{e.preventDefault();backToTab();});
$('modal').addEventListener('click',e=>{if(e.target===$('modal')){const r=$('modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)backToTab();}});
$('compare-clear').onclick=()=>{compared.clear();render();};$('compare-open').onclick=()=>{location.hash='karsilastir';};
initProfile();
if(profilAc)openProfile();
let lastHref=location.href;
function onNav(){if(location.href===lastHref)return;bootQuery=false;if(location.hash.slice(1)==='ilanlar'){F=parseQuery(new URL(location.href).search);$('search').value=F.q;shown=PAGE_SIZE;}route();lastHref=location.href;}
window.addEventListener('hashchange',onNav);window.addEventListener('popstate',onNav);
document.addEventListener&&document.addEventListener('visibilitychange',tryWriteVisit);
/* Dakikada bir yalnız tarih ya da durum değiştiyse (ilan kapandı/açıldı, gün döndü) yeniden çizer; kaydırma konumu korunur. */
const imza=()=>today()+'|'+liste.filter(closed).length+'|'+liste.filter(upcoming).length;
setInterval(()=>{if(!(loaded||listeLoaded))return;if(imza()===sig)return;const y=window.scrollY||0;render();if(window.scrollTo)window.scrollTo(0,y);},60000);
setTimeout(()=>{visitDue=true;tryWriteVisit();},10000);
if(bootTab==='ilanlar'&&!bekleyenKaydirma)bekleyenKaydirma='ilanlar';
{const y=document.querySelector&&document.querySelector('.yan');if(y)y.append(adBox.sidebar);}
/* Arama sözcüğü ve sonuç adedi (sonuçsuz aramalar önemli); yazma bitince bir kez, yalnızca sorgu metni (kişisel veri aranmaz). */
function aramaIz(){clearTimeout(aramaZaman);aramaZaman=setTimeout(async()=>{const norm=()=>F.q.trim().toLocaleLowerCase('tr-TR').replace(/\s+/g,' ').slice(0,60),q=norm();if(q.length<2||q===aramaSon)return;if(!loaded&&!fullFailed)await ensureFull();if(norm()!==q)return;aramaSon=q;A('tikla',{a:'arama',x:q,n:sonSayi});},1200);}
if(F.q)aramaIz();
showTab(bootTab);load();loadSponsors();
