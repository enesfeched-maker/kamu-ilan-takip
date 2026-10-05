'use strict';
const sourceDocument = i => /^https:\/\/enesfeched-maker\.github\.io\/kamu-ilan-takip\/belgeler\/sbb\/[a-f0-9]{64}\.pdf$/.test(i.belge_kopyasi||'')?i.belge_kopyasi:null;
const $ = id => document.getElementById(id);
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
let saved=new Set((Array.isArray(readStore('kit-saved',[]))?readStore('kit-saved',[]):[]).filter(s=>typeof s==='string'&&s.length>0&&s.length<=80)), compared=new Set(), items=[], liste=[], listeTum=[], listeUyari=null, listeVar=false, listeZaman='', view='active', shown=20, takvimGun=7, loaded=false, listeLoaded=false, toastTimer, profil=null, sonZiyaret=null, tab='bugun', lastTab='bugun';
const PAGE_SIZE=20, defaultTitle=document.title;
const TABS=['bugun','ilanlar','takvim','kayitli','rehber'];
const AY=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'],AYU=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'],GUNLER=['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'];
const IL_LIST=['Adana','Adıyaman','Afyonkarahisar','Ağrı','Aksaray','Amasya','Ankara','Antalya','Ardahan','Artvin','Aydın','Balıkesir','Bartın','Batman','Bayburt','Bilecik','Bingöl','Bitlis','Bolu','Burdur','Bursa','Çanakkale','Çankırı','Çorum','Denizli','Diyarbakır','Düzce','Edirne','Elazığ','Erzincan','Erzurum','Eskişehir','Gaziantep','Giresun','Gümüşhane','Hakkari','Hatay','Iğdır','Isparta','İstanbul','İzmir','Kahramanmaraş','Karabük','Karaman','Kars','Kastamonu','Kayseri','Kırıkkale','Kırklareli','Kırşehir','Kilis','Kocaeli','Konya','Kütahya','Malatya','Manisa','Mardin','Mersin','Muğla','Muş','Nevşehir','Niğde','Ordu','Osmaniye','Rize','Sakarya','Samsun','Siirt','Sinop','Sivas','Şanlıurfa','Şırnak','Tekirdağ','Tokat','Trabzon','Tunceli','Uşak','Van','Yalova','Yozgat','Zonguldak'];
const IC={sag:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg>',kayit:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.5h10a1 1 0 0 1 1 1V21l-6-4-6 4V4.5a1 1 0 0 1 1-1z"/></svg>',ok:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',saat:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>',grafik:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10m6 10V4m6 16v-7m4 7H3"/></svg>',kisi:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>',kalem:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4z"/></svg>',tg:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 4-18 7.2 6 2.3M21 4l-3 16-8.5-6.5M21 4 9.5 13.5v5.5l3-3.5"/></svg>',kitap:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5C6.5 4 9.5 4 12 6c2.5-2 5.5-2 8-.5V19c-2.5-1.5-5.5-1.5-8 .5-2.5-2-5.5-2-8-.5z"/><path d="M12 6v13.5"/></svg>',x:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>',asagi:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',sol:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 6-6 6 6 6"/></svg>'};
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
function save(i){const was=isSaved(i);if(was){for(const x of idsOf(i)){saved.delete(x);compared.delete(x);}}else saved.add(i.id);const ok=writeStore('kit-saved',[...saved]);render();const full=items.find(x=>x.id===i.id);if(location.hash.startsWith('#ilan/')&&full)showDetail(full);notify(ok?(was?'İlan kaydedilenlerden kaldırıldı.':'İlan bu tarayıcıya kaydedildi.'):'Tarayıcı depolaması kapalı; seçim yalnızca bu oturumda saklanır.');}
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
function breakdown(list){let a=0,u=0,x=0;for(const i of list){if(upcoming(i))u++;else if(!i.son_tarih)x++;else if(knownActive(i))a++;}const p=[];if(a)p.push(a+' başvurusu açık');if(u)p.push(u+' yakında başlıyor');if(x)p.push(x+' tarihi belirsiz');return p.length>1||u||x?p.join(' · '):'';}
function external(url,label,cls='button primary'){const a=E('a',cls,label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function openModal(){if(!$('modal').open)$('modal').showModal();$('modal').scrollTop=0;}
function infoSection(parent,heading,text){parent.append(E('h3','',heading),E('p','',text));}
function showDetail(i){const body=$('modal-body');body.replaceChildren();const header=E('div','detail-header');header.append(E('span','eyebrow',i.ilan_turu||'KAMU PERSONEL ALIMI'));const h=E('h2','',title(i));h.id='modal-title';header.append(h,kurumNode(i,'detail-kurum'));const vis=cardImage(i,false);if(vis){const box=E('div','detail-visual');if(i.logo)box.append(logoNode(i,'detail-logo',64));box.append(vis);body.append(box);}body.append(header);const layout=E('div','detail-layout'),content=E('div','detail-content'),side=E('aside','detail-aside'),dl=E('dl');for(const [k,v] of [['Durum',status(i)],['Görev yeri',yerMetni(i)||'Resmî ilandan kontrol et'],['Son başvuru',trDate(i.son_tarih)+(i.son_zaman?' · '+trTime(i.son_zaman)+' TSİ':'')],['Başlangıç',i.baslangic_zaman?trDate(i.baslangic_zaman):'Belirtilmemiş']])dl.append(E('dt','',k),E('dd','',v));side.append(dl);const docURL=sourceDocument(i);const link=docURL||officialURL(i.link);if(link)side.append(external(link,docURL?'İlan belgesini aç (PDF) ↗':'Resmî ilana git · Başvur ↗'));if(docURL)side.append(E('p','muted',i.belge_aciklamasi));const sb=E('button','button secondary',isSaved(i)?'Kaydedildi · kaldır':'İlanı kaydet');sb.onclick=()=>save(i);const share=E('button','button secondary','Bağlantıyı paylaş');share.onclick=()=>shareItem(i);side.append(sb,share);if(i.son_tarih&&!closed(i)&&!i.duyuru_turu){const calendar=E('button','button secondary','Takvimime ekle');calendar.onclick=()=>downloadCalendar(i);side.append(calendar);}side.append(E('p','muted','Kaydetmek veya takvime eklemek başvuru oluşturmaz. İşlemini resmî başvuru kanalında tamamla.'));if(stale(i))content.append(E('p','notice','Bu ilanın ayrıntıları 24 saat içinde doğrulanmadı. Başvuru yapmadan önce güncel tarih ve koşulları resmî ilandan kontrol et.'));if(closed(i))content.append(E('p','notice','Kayıtlı son başvuru zamanı geçti. Bu ilan arşiv amacıyla gösteriliyor.'));if(upcoming(i))content.append(E('p','notice','Kayıtlı başvuru başlangıcı henüz gelmedi.'));infoSection(content,'Kadro ve kontenjan',i.kadro||'Kontenjan bilgisi kaynak özetinde bulunmuyor. Tam ilanı incele.');if(i.ozet)infoSection(content,'İlan özeti',i.ozet);content.append(E('h3','','Başvuru koşullarından seçmeler'));if(i.sartlar?.length){for(const s of i.sartlar){const c=E('section','condition');c.append(E('h4','',proper(s.kadro)),E('p','',s.metin));content.append(c);}content.append(E('p','muted','Bu bölüm seçilmiş alıntıları içerir; tüm kadro ve özel koşulların listesi değildir. Üç nokta ile biten metinler kısaltılmıştır.'));}else content.append(E('p','','Kaynak özetinde başvuru koşulları yer almıyor. Mezuniyet, KPSS, yaş ve diğer şartlar için resmî ilanı aç.'));if(i.basvuru_notu)infoSection(content,'Başvuruya ilişkin not',i.basvuru_notu);const related=items.filter(x=>x.id!==i.id&&knownActive(x)).sort((a,b)=>Number(b.ilan_turu===i.ilan_turu)-Number(a.ilan_turu===i.ilan_turu)).slice(0,3);if(related.length){content.append(E('h3','','Bunlara da göz at'));const box=E('div','related');for(const r of related){const a=detailLink(r,title(r));a.append(E('span','',kurumAdi(r.kurum)+' · '+status(r)));box.append(a);}content.append(box);}content.append(E('p','muted','Kaynak: '+(i.kaynaklar?.map(s=>s.ad).join(' · ')||i.kaynak||'Kariyer Kapısı')+(i.detay_guncelleme?' · Ayrıntı kontrolü: '+trDate(i.detay_guncelleme)+' '+trTime(i.detay_guncelleme):'')));layout.append(content,side);body.append(layout);document.title=title(i)+' | Kamu İlan Takip';openModal();}
async function shareItem(i){const url=new URL(location.href);url.hash='ilan/'+encodeURIComponent(i.key);url.search='';try{if(navigator.share)await navigator.share({title:title(i),url:url.href});else{await navigator.clipboard.writeText(url.href);notify('İlan bağlantısı kopyalandı.');}}catch(e){if(e.name!=='AbortError'){const field=E('input');field.value=url.href;field.readOnly=true;field.setAttribute('aria-label','Paylaşılacak ilan bağlantısı');$('modal-body').append(field);field.focus();field.select();notify('Bağlantıyı seçip kopyalayabilirsin.');}}}
function calendarText(list){
const esc=v=>String(v||'').replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');const utc=d=>new Date(d).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z/,'Z');
const stamp=utc(Date.now()),ev=i=>{const date=i.son_zaman?Date.parse(i.son_zaman):null;const timing=date?['DTSTART:'+utc(date),'DTEND:'+utc(date+60000)]:['DTSTART;VALUE=DATE:'+i.son_tarih.replace(/-/g,''),'DTEND;VALUE=DATE:'+new Date(Date.parse(i.son_tarih+'T00:00:00Z')+86400000).toISOString().slice(0,10).replace(/-/g,'')];const url=officialURL(i.link);return ['BEGIN:VEVENT','UID:'+esc(i.key)+'@kamu-ilan-takip','DTSTAMP:'+stamp,...timing,'SUMMARY:'+esc('Son başvuru: '+title(i)),'DESCRIPTION:'+esc('Resmî ilandaki güncel tarih ve koşulları kontrol edin. '+(i.link||'')),...(url?['URL:'+url]:[]),'END:VEVENT'];};
return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Kamu Ilan Takip//TR',...(Array.isArray(list)?list:[list]).filter(i=>i&&i.son_tarih).flatMap(ev),'END:VCALENDAR'].map(icsFold).join('\r\n')+'\r\n';}
/* RFC 5545: satırlar 75 sekizliyi aşmaz; devam satırı boşlukla başlar. */
function icsFold(line){const out=[];let cur='',n=0;for(const ch of line){const cp=ch.codePointAt(0),b=cp<0x80?1:cp<0x800?2:cp<0x10000?3:4,lim=out.length?74:75;if(n+b>lim){out.push(cur);cur='';n=0;}cur+=ch;n+=b;}out.push(cur);return out.join('\r\n ');}
function downloadCalendar(i){const u=URL.createObjectURL(new Blob([calendarText(i)],{type:'text/calendar;charset=utf-8'})),a=E('a');a.href=u;a.download='kamu-ilan-son-basvuru.ics';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);notify('Takvim dosyası indirildi. Takvim uygulamana ekleyebilirsin.');}
const articles={
 'rehber/ilan-okuma':{title:'Bir ilanı nasıl okumalısın?',intro:'Başlığın uygun görünmesi tek başına yeterli değildir. İncelemeyi seçtiğin kadro üzerinden yap.',sections:[['1. Önce kadroyu belirle','Aynı ilanda farklı unvanlar ve farklı koşullar bulunabilir. Başvurmak istediğin kadronun adı, kodu, görev yeri ve kontenjanını not et.'],['2. Koşulları birlikte değerlendir','Mezuniyet programı, puan türü ve yılı, varsa asgari puan, deneyim ve belge koşullarını tam metinden kontrol et. İlan özetindeki alıntıları tüm şartların yerine koyma.'],['3. Başvuru yolunu ve zamanı kontrol et','İlanda belirtilen başvuru kanalını kullan. Son günün yanında saat bilgisi ve varsa ayrıca teslim edilmesi gereken belgelerin tarihini de incele.'],['4. Duyurulara geri dön','Düzeltme, sonuç ve ek duyuruları ilgili kurumun resmî kanallarından takip et. Bu platform başvuru kabul etmez veya uygunluk kararı vermez.']]},
 'rehber/basvuru-listesi':{title:'Başvuru kontrol listesi',intro:'Her ilan için bu kısa listeyi yeniden gözden geçir.',steps:['Başvuracağın kadro kodunu ve görev yerini seç.','Mezuniyet ve puan koşullarını tam ilan metniyle karşılaştır.','İstenilen belgelerin güncel ve okunaklı olduğundan emin ol.','Son başvuru tarihini, saatini ve varsa ek belge teslim tarihini not et.','Resmî başvuru kanalında işlemini tamamla.','Başvurunun durumunu ilgili sistemde doğrula; kayıt veya başvuru belgeni sakla.','Sonuç ve sonraki aşama duyurularını resmî kurumdan takip et.'],sections:[['Kaydetmek, başvurmak değildir','Buradaki yer imi kişisel takip içindir. Başvuru işlemini ilanda belirtilen resmî kanalda ayrıca tamamlamalısın.']]},
 'rehber/takvim':{title:'Son günü bekleme.',intro:'İlanları son tarihlerine göre sıralamak, başvuru planını daha görünür kılar.',sections:[['Önce yakın tarihleri incele','“Son 3 gün” veya “Son 7 gün” filtresini kullan. İlan kartının kalan süresi Türkiye saatine göre hesaplanır. Kesin saat belirtilmişse ayrıntı ekranında gösterilir.'],['Takvimine ekle','İlan ayrıntısındaki “Takvimime ekle” düğmesi bir takvim dosyası indirir. Dosyayı takvim uygulamanla açıp eklemeyi tamamla. Bildirim zamanını kendi takviminde seçebilirsin.'],['Tarihi yeniden doğrula','Takvim dosyası indirildiği andaki bilgiyi taşır, sonradan otomatik güncellenmez. İlanda bir değişiklik varsa takvim kaydını da güncelle.'],['Kendine hazırlık süresi bırak','Belgeleri ve başvuru adımlarını erkenden incele. Teknik sorun yaşarsan destek için ilgili kurumun ilanda belirttiği iletişim kanalını kullan.']]},
 'bilgi/hakkimizda':{title:'Hakkımızda ve veri kaynağı',intro:'Kamu İlan Takip, kamu personel ilanlarını daha kolay incelemek ve takip etmek için hazırlanmış bağımsız bir rehberdir.',sections:[['Veriler nereden geliyor?','İlanlar Kariyer Kapısı resmî RSS akışından, İŞKUR kamu memur alım ilanları sayfalarından, SBB Kamu İlan listesinden ve Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Yerel Yönetimler duyurularından (ÇŞB) derlenir. SBB belgelerinde yılı doğrulanamayan tarihler gösterilmez; SBB’den alınan ilan belgelerinin değiştirilmemiş kopyaları ilgili ilan sayfasından açılır. Kurum, görev yeri, kontenjan ve koşullar kaynağın sunduğu bilgilerle sınırlıdır.'],['Güncellik nasıl gösterilir?','Ana sayfadaki son kontrol zamanı liste taramasını gösterir. İlan ayrıntılarının kontrol tarihi ayrıca gösterilir. Otomatik bağlantılar gecikebilir; eski ayrıntılar uyarıyla sunulur.'],['Resmî bir hizmet mi?','Hayır. Herhangi bir kamu kurumuna bağlı değiliz. Başvuru kabul etmeyiz, aday uygunluğu değerlendirmeyiz. Güncel ve bağlayıcı bilgi için resmî ilanı esas alın.'],['Bir hata fark ettin mi?','İlanın bağlantısını ve hatalı alanı proje bildirim sayfasından iletebilirsin. Herkese açık bildirimlere kimlik, özgeçmiş veya başvuru belgesi ekleme.']],contact:true},
 'bilgi/gizlilik':{title:'Gizlilik ve tarayıcı verileri',intro:'Bu sürüm üyelik istemez. Özgeçmiş, kimlik bilgisi veya başvuru belgesi toplamak için bir form içermez.',sections:[['Bu cihazda saklanan bilgiler','Kaydettiğin ilanların kimlikleri, profilin (öğrenim düzeyi, puan, iller), son ziyaret zamanın ve renk teması tercihin tarayıcının yerel depolamasında tutulur. Bunlar başka cihazlara taşınmaz. Aşağıdaki düğme bu platformun yerel tercihlerini temizler.'],['Dış bağlantılar ve barındırma','Resmî başvuru sayfası, Telegram ve GitHub bağlantıları kendi hizmetlerine yönlendirir. Bu hizmetlerin veri uygulamaları ayrıdır. Site dosyaları GitHub Pages üzerinden sunulur; barındırma hizmeti teknik erişim kayıtlarını işleyebilir.'],['Reklam ve ölçüm','Bu sürümde üçüncü taraf reklam ağı veya ziyaretçi analiz kodu etkin değildir. Reklam ya da analiz hizmeti eklenmeden önce bu açıklama ve gerekli tercih mekanizmaları kullanılan hizmete göre güncellenmelidir.']],clear:true},
 'bilgi/reklam':{title:'Reklam ve iş birliği',intro:'Kamu kariyeriyle ilgilenen ziyaretçilere ulaşmak isteyen markalar için açıkça etiketlenmiş sponsor alanları.',sections:[['İki sade yerleşim','Ana sayfa yan sütununda ve ilan listesinin altında sponsor alanı ayrılmıştır. Aktif bir kampanya yoksa boş reklam kutuları gösterilmez.'],['İlanlardan ayrı bir alan','Sponsorlu içerik “Reklam · Sponsorlu” etiketi taşır. Reklamlar resmî ilan gibi gösterilmez; ilan sıralaması sponsorlu içerikten etkilenmez.'],['İş birliği talebi','Markanı, kampanya konunu ve tercih ettiğin alanı proje iletişim sayfasından paylaşabilirsin. Bu herkese açık kanala gizli ticari bilgiler veya kişisel belgeler ekleme.']],contact:true}
};
/* Bu platformun tüm yerel tercihleri: kit- ile başlayan her anahtar (profil, tema, kayıtlar, puan düzeyi, oturum tabanı). */
function clearLocal(){try{const ks=[];for(let i=0;i<(localStorage.length||0);i++){const k=localStorage.key(i);if(k&&k.startsWith('kit-'))ks.push(k);}for(const k of new Set([...ks,'kit-theme','kit-profil','kit-son-ziyaret','kit-saved','kit-puan-duzey']))localStorage.removeItem(k);}catch{}try{sessionStorage.removeItem('kit-sz-baz');}catch{}}
function showArticle(key){const a=articles[key];if(!a)return;const n=E('article','article');n.append(E('span','eyebrow',key.startsWith('rehber/')?'BAŞVURU REHBERİ':'KAMU İLAN TAKİP'));const h=E('h2','',a.title);h.id='modal-title';n.append(h,E('p','',a.intro));if(a.steps){const ol=E('ol');a.steps.forEach(s=>ol.append(E('li','',s)));n.append(ol);}for(const [heading,text] of a.sections)infoSection(n,heading,text);if(a.contact)n.append(external('https://github.com/enesfeched-maker/kamu-ilan-takip/issues/new','İletişim / bildirim sayfası ↗'));if(a.clear){const b=E('button','button secondary','Kaydedilen ilanları, profili ve tema tercihini temizle');b.onclick=()=>{saved.clear();writeStore('kit-saved',[]);profil=null;sonZiyaret=null;clearLocal();applyTheme();render();notify('Bu platformun yerel tercihleri temizlendi.');};n.append(b);}n.append(E('p','muted','Son düzenleme: 25 Eylül 2026'));$('modal-body').replaceChildren(n);document.title=a.title+' | Kamu İlan Takip';openModal();}
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
if(g===null){d.className='tarih yok';d.append(E('strong','','—'),E('span','','tarih ilanda'));return d;}
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
const h=E('h3'),a=detailLink(o,o.manset||'Kamu ilanı');if(o.ek)a.append(' ',E('span','ek','+'+o.ek));h.append(a);
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
function profilStrip(cls){
const p=profil,d=E('div','profil'+(cls?' '+cls:'')),ik=E('span','profil-ikon');ik.innerHTML=IC.kisi;
const y=E('div','profil-yazi');y.append(E('b','','PROFİLİN'));
y.append(E('span','',LEVELS[p.ogrenim]+(typeof p.puan==='number'?' · KPSS '+p.puan_turu+' '+puanTr(p.puan):'')));
const alt=[p.tum_turkiye?'Tüm Türkiye':p.iller.join(', '),p.bolum].filter(Boolean).join(' · ');if(alt)y.append(E('small','',alt));
const b=E('button','duzenle');b.type='button';b.setAttribute('aria-label','Profili düzenle');b.innerHTML=IC.kalem+(cls==='m-only'?'<span>Düzenle</span>':'');b.onclick=openProfile;d.append(ik,y,b);return d;}
function kurulumCard(){
const p=profil;
if(p&&p.atlandi&&Date.now()-Date.parse(p.t+'T12:00:00Z')<14*864e5){const d=E('p','kurulum-ince','Sana göre ayarlamak ister misin? '),b=E('button','','Profilini ayarla');b.type='button';b.onclick=openProfile;d.append(b);return d;}
const d=E('div','kurulum'),ik=E('span','profil-ikon'),t=E('div'),b=E('button','btn btn-ana','Başla');ik.innerHTML=IC.kisi;t.append(E('b','','30 saniyede sana göre ayarla'),E('span','','Öğrenim düzeyini ve illerini seç; sana uygun ilanlar en üstte görünsün.'));b.type='button';b.onclick=openProfile;d.append(ik,t,b);return d;}
/* ---------- Bugün ---------- */
function bugunModel(){
const p=activeProfile(),acik=liste.filter(o=>!closed(o)&&!o.kurum_ici),byDl=(a,b)=>(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999')||a.kurum.localeCompare(b.kurum,'tr');
const seviye=new Map(),bilinmiyor=[];
const senin=p?acik.filter(o=>{const s=uygun(o,p);if(s==='bilinmiyor'){bilinmiyor.push(o);return false;}if(s)seviye.set(o.key,s);return !!s;}).sort((a,b)=>Number(seviye.get(a.key)==='alt')-Number(seviye.get(b.key)==='alt')||ilRank(a,p)-ilRank(b,p)||Number(isNew(b))-Number(isNew(a))||byDl(a,b)):[];
const acil=acik.filter(o=>o.son_tarih&&!upcoming(o)&&days(o.son_tarih)<=2).sort(byDl);
const yeni=acik.filter(isNew).sort((a,b)=>Date.parse(b.ilk_gorulme)-Date.parse(a.ilk_gorulme));
const yakinda=acik.filter(upcoming).sort((a,b)=>Date.parse(a.baslangic_zaman)-Date.parse(b.baslangic_zaman));
const bugunYeni=acik.filter(o=>o.ilk_gorulme&&istDate(o.ilk_gorulme)===today());
return{p,acik,senin,seviye,bilinmiyor,acil,yeni,yakinda,bugunYeni};}
function h1Of(m){
const h=E('h1'),n=m.bugunYeni.length,b=m.acil.filter(o=>days(o.son_tarih)<=0).length,y=m.acil.filter(o=>days(o.son_tarih)===1).length;
const dow=new Date().toLocaleDateString('en-US',{weekday:'short',timeZone:'Europe/Istanbul'}),hs=dow==='Sat'||dow==='Sun';
const son=b>0?b+' ilanın son günü':y>0?y+' ilanın son günü yarın':'';
if(n>0)h.append('Bugün ',E('mark','',n+' yeni ilan'),' var'+(son?', '+son:'')+'.');
else h.append((hs?'Hafta sonu sakin: yeni ilan yok':'Bugün yeni ilan yok')+(son?'; '+son:'; açık ilanlar aşağıda')+'.');
return h;}
/* liste.json 'uyari' nesnesi (derleme zamanı): kaynak hatası ve 24 saatten eski ayrıntı sayısı; tek nötr satır. */
function cleanUyari(u){if(!u||typeof u!=='object')return {kaynaklar:[],eski:0};return {kaynaklar:strList(u.kaynaklar,5,40),eski:posInt(u.eski_detay,100000)};}
function uyariMetni(){
if(!listeUyari)return '';const p=[];
if(listeUyari.kaynaklar.length)p.push(listeUyari.kaynaklar.join(' ve ')+' kaynağına erişimde sorun var; bu kaynağın ilanları güncel olmayabilir.');
if(listeUyari.eski&&liste.length&&listeUyari.eski>=liste.length*0.25)p.push(listeUyari.eski+' ilanın ayrıntıları 24 saat içinde doğrulanmadı.');
return p.join(' ');}
function ozetOf(m){
const parts=[];
if(sonZiyaret&&m.yeni.length){let s=uzunTarih(istDate(sonZiyaret))+'’deki ziyaretinden beri '+m.yeni.length+' ilan eklendi';if(m.p){const u=m.yeni.filter(o=>eslesen(uygun(o,m.p))).length;if(u)s+=', '+ekSi(u)+' profiline uygun';}parts.push(s+'.');}
const k=m.acik.filter(isSaved);
if(k.length){const a=k.filter(o=>o.son_tarih&&!upcoming(o)&&days(o.son_tarih)<=2).length;if(a)parts.push('Kaydettiğin '+k.length+' ilandan '+ekSi(a)+' 2 gün içinde kapanıyor.');}
return parts.join(' ');}
/* Öğrenim şartı okunamayan (düzeyi belirsiz) ama il olarak uyan ilanlar: sessizce "uygun" sayılmaz, tek satırlık bağlantıyla açılır. */
const bilinmiyorYama=p=>({ogr:'bilinmiyor',uygun:false,il:p.tum_turkiye?[]:p.iller.slice(0,10)});
function bilinmiyorSatiri(m){const n=m.bilinmiyor.length;if(!n)return null;const s=E('p','okunamayan');s.append(ilanLink('Öğrenim şartı okunamayan '+n+' ilan',bilinmiyorYama(m.p)));return s;}
function railKayitli(m){
const k=m.acik.filter(isSaved).sort((a,b)=>(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999')).slice(0,5),box=E('section','kutu'),h=E('h3');h.append(ic('kayit'),'Kaydettiklerin');box.append(h);
if(!k.length){box.append(E('p','','Bir ilanı kaydetmek için yer imi simgesine dokun; son tarihi yaklaşınca burada hatırlatırız.'));return box;}
box.append(E('p','','Son tarihi yaklaşınca burada hatırlatırız.'));
const ul=E('ul','mini');for(const o of k){const li=E('li'),d=E('div'),a=detailLink(o,o.manset),g=o.son_tarih?days(o.son_tarih):null,em=E('em',g!==null&&g<=1?'acil':'',g===null?'—':g<=0?'Bugün son gün':g===1?'Yarın son gün':g+' gün');d.append(a,E('small','',o.kurum));li.append(d,em);ul.append(li);}
box.append(ul);return box;}
function railTelegram(){
const b=E('section','kutu tg-kutu'),s=E('span','tg-saat'),a=E('a','btn btn-lime');s.append(ic('saat'),'Her sabah 09:00 civarı');
a.href='https://t.me/kamuilantakip';a.target='_blank';a.rel='noopener';a.append(ic('tg'),'Kanala katıl');
b.append(s,E('h3','','Günün özeti Telegram’da'),E('p','','Yeni ilanlar ve son günler tek mesajda. Mesajdaki bağlantı seni doğrudan bu sayfaya getirir.'),a);return b;}
function arac(href,icon,t,s){const a=E('a','arac'),i=E('i'),d=E('span');a.href=href;i.innerHTML=IC[icon];d.append(E('b','',t),E('small','',s));a.append(i,d);return a;}
function railAraclar(){const b=E('section','kutu');b.append(E('h3','','Araçlar'),arac('puanlar/','grafik','Taban puanları ve tercih robotu','2022–2026 KPSS yerleştirme verisi'),arac('#rehber','kitap','Başvuru rehberi','İlan okuma, belge listesi, son kontrol'));return b;}
const adBox={sidebar:E('div'),feed:$('ad-feed')};adBox.sidebar.hidden=true;
function renderBugun(){
const root=$('bugun');if(!root||!listeLoaded)return;
const m=bugunModel(),p=m.p,gosterilen=new Set();
/* Her ilan ilk uygun bölümde bir kez görünür; sayılar tekilleştirilmiş havuzdan hesaplanır. */
const pool=arr=>arr.filter(o=>!gosterilen.has(o.key)),mark=arr=>arr.forEach(o=>gosterilen.add(o.key));
const bas=E('section','k1-bas'),us=E('div','ust-satir'),c=E('span','canli');
us.append(E('span','',new Date().toLocaleDateString('tr-TR',{day:'numeric',month:'long',weekday:'long',timeZone:'Europe/Istanbul'}).toLocaleUpperCase('tr-TR')));
const eski=listeZaman&&Date.now()-Date.parse(listeZaman)>864e5;
if(listeZaman&&!eski){c.append(E('span','nokta'),'Son kontrol '+trTime(listeZaman));us.append(c);}
bas.append(us,h1Of(m));const oz=ozetOf(m);if(oz)bas.append(E('p','ozet',oz));
if(eski)bas.append(E('p','tazelik','Veriler en son '+uzunTarih(istDate(listeZaman))+' '+trTime(listeZaman)+'’de güncellendi.'));
const uy=uyariMetni();if(uy)bas.append(E('p','tazelik uyari-satir',uy));
if(p)bas.append(profilStrip('m-only'));else bas.append(kurulumCard());
const main=E('div'),secs=[];
if(p){const hav=pool(m.senin),sh=hav.slice(0,5);mark(sh);
const bil=bilinmiyorSatiri(m),sg=E('div');
secs.push(['senin',hav.length,sectionEl('senin',{baslik:'Senin için',sayi:hav.length,alt:LEVELS[p.ogrenim]+' düzeyi · '+(p.tum_turkiye?'tüm Türkiye':p.iller.join(', ')||'tüm Türkiye (il seçmedin)')+'. Yeniler önce.',link:hav.length>sh.length?ilanLink('Tümü',{uygun:true}):null,govde:(sg.append(sh.length?listeEl(sh,o=>({yeni:true,alt:m.seviye.get(o.key)==='alt'})):bosKutu(E('p','','Bugün profiline uyan açık ilan yok. Bu normal; yeni ilan gelince burada görürsün.'),(()=>{const b=E('button','btn btn-ikinci','İl ekle');b.type='button';b.onclick=openProfile;return b;})(),ilanLink('Tüm ilanlara bak',{uygun:false},'btn btn-ikinci')),...(bil?[bil]:[])),sg)})]);}
else{const hav=pool(m.bugunYeni),sh=hav.slice(0,5);mark(sh);if(hav.length)secs.push(['bugunyeni',hav.length,sectionEl('bugunyeni',{nokta:'yeni',baslik:'Bugün eklenenler',sayi:hav.length,alt:'Bugün listeye giren ilanlar.',govde:listeEl(sh,{yeni:true})})]);}
{const hav=pool(m.acil),sh=hav.slice(0,6);mark(sh);
if(hav.length){const alt=E('div','liste-alt');alt.append(ilanLink('Tüm son günler ('+m.acil.length+')',{sb:'2',uygun:false}));const l=listeEl(sh,{yeni:true});l.append(alt);
secs.push(['songun',hav.length,sectionEl('songun',{nokta:'acil',baslik:'Son günü yaklaşanlar',sayi:hav.length,alt:'Bugün ve önümüzdeki iki gün içinde kapanan ilanlar.',govde:l})]);}}
{const hav=pool(m.yeni),sh=hav.slice(0,20);mark(sh);
if(sh.length){const g=E('div','liste'),gr=new Map();for(const o of sh){const d=istDate(o.ilk_gorulme);if(!gr.has(d))gr.set(d,[]);gr.get(d).push(o);}
for(const [d,l] of gr){const fark=Math.round((Date.parse(d+'T00:00:00Z')-Date.parse(today()+'T00:00:00Z'))/864e5),on=fark===0?'Bugün · ':fark===-1?'Dün · ':'';g.append(E('div','alt-baslik',on+uzunTarih(d)+' '+gunAdi(d)),...l.map(o=>rowEl(o)));}
secs.push(['yeni',hav.length,sectionEl('yeni',{nokta:'yeni',baslik:sonZiyaret?'Son ziyaretinden beri yeni':'Son iki günde eklenenler',sayi:hav.length,alt:(sonZiyaret?'Son ziyaretin '+uzunTarih(istDate(sonZiyaret))+' '+gunAdi(istDate(sonZiyaret))+', '+trTime(sonZiyaret)+' · ':'')+'yukarıda gösterilenler tekrar edilmez',govde:g})]);}
else if(!m.yeni.length)secs.push(['yeni',0,sectionEl('yeni',{nokta:'yeni',baslik:sonZiyaret?'Son ziyaretinden beri yeni':'Son iki günde eklenenler',govde:bosKutu(E('p','',(sonZiyaret?'Son ziyaretinden beri':'Son iki günde')+' yeni ilan yok.'+(listeZaman?' Son kontrol '+trTime(listeZaman)+'.':'')))})]);}
{const hav=pool(m.yakinda),sh=hav.slice(0,4);mark(sh);
if(sh.length)secs.push(['yakinda',hav.length,sectionEl('yakinda',{baslik:'Yakında başvurusu açılacak',sayi:hav.length,alt:'Belgelerini şimdiden hazırlayabilirsin.',link:ilanLink('Tümü',{sb:'yakinda',uygun:false}),govde:listeEl(sh)})]);}
const kadro=m.acik.reduce((s,o)=>s+(o.toplam||0),0),tumu=E('a','tumu'),tt=E('span'),ti=E('i');tumu.href='?uygun=0#ilanlar';tumu.onclick=e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button>0)return;e.preventDefault();openIlanlar({uygun:false});};tt.append(E('b','','Tüm açık ilanlar'),E('span','',m.acik.length+' ilan'+(kadro?' · '+sayiTr(kadro)+' kadro':'')+' · aramak ve filtrelemek için'));ti.innerHTML=IC.sag;tumu.append(tt,ti);
const atla=E('nav','atla');atla.setAttribute('aria-label','Bu sayfada git');
const ETIKET={senin:'Senin için',bugunyeni:'Bugün eklenenler',songun:'Son günler',yeni:'Yeni',yakinda:'Yakında açılacak'};
for(const [id,n] of secs.map(s=>[s[0],s[1]])){if(!n)continue;const b=E('button');b.type='button';if(id==='songun')b.append(E('span','nokta acil'));b.append(ETIKET[id]+' ',E('b','',String(n)));b.onclick=()=>{const t=document.getElementById(id);if(t)t.scrollIntoView({behavior:'smooth'});};atla.append(b);}
const tum=ilanLink('',{uygun:false},'atla-a');tum.replaceChildren('Tüm ilanlar ',E('b','',String(m.acik.length)));atla.append(tum);
bas.append(atla);
for(const s of secs)main.append(s[2]);main.append(tumu,adBox.feed);
const rail=E('aside','k1-yan');if(p)rail.append(profilStrip(''));rail.append(railKayitli(m),railTelegram(),railAraclar(),adBox.sidebar);
const gr=E('div','k1-izgara');gr.append(main,rail);
root.replaceChildren(bas,gr);}
/* ---------- İlanlar: süzgeç durumu, URL eşitleme, süzme ---------- */
const OGR_SECENEK=[['lisans','Lisans'],['onlisans','Önlisans'],['ortaogretim','Ortaöğretim'],['bilinmiyor','Öğrenim belirtilmemiş'],['belediye','Belediye ilanları']];
const SB_SECENEK=[['2','Son 2 gün'],['3','Son 3 gün'],['7','Son 7 gün'],['14','Son 14 gün'],['yakinda','Yakında açılacak']];
const SIRA_SECENEK=[['son','Son tarih: en yakın'],['yeni','En yeni eklenen'],['kurum','Kurum: A–Z']];
const QKEYS=['q','il','ogr','sb','tur','yeni','uygun','sira','arsiv'];
const defaultF=()=>({q:'',il:[],ogr:'',sb:'',tur:'',yeni:false,uygun:null,sira:'son',arsiv:false});
let F=defaultF(),menuAcik=null,bootQuery=false;const chips={};
const ilSlug=il=>normalize(il);
/* ?q=&il=&ogr=&sb=&tur=&yeni=1&uygun=0&sira=&arsiv=1 → süzgeç; bilinmeyen/bozuk değerler atılır. */
function parseQuery(search){
const sp=new URLSearchParams(search),f=defaultF();
f.q=str(sp.get('q')||'',80).trim();
f.il=[...new Set((sp.get('il')||'').split(',').map(x=>IL_LIST.find(il=>ilSlug(il)===normalize(x).trim())).filter(Boolean))].slice(0,10);
const ogr=sp.get('ogr');f.ogr=OGR_SECENEK.some(x=>x[0]===ogr)?ogr:'';
const sb=sp.get('sb');f.sb=SB_SECENEK.some(x=>x[0]===sb)?sb:'';
f.tur=str(sp.get('tur')||'',60);f.yeni=sp.get('yeni')==='1';
const u=sp.get('uygun');f.uygun=u==='0'?false:u==='1'?true:null;
const s=sp.get('sira');f.sira=SIRA_SECENEK.some(x=>x[0]===s)?s:'son';f.arsiv=sp.get('arsiv')==='1';
return f;}
const queryHas=search=>{const sp=new URLSearchParams(search);return QKEYS.some(k=>sp.has(k));};
/* Profil varken "Profilime uygun" varsayılan açıktır; yalnız kapalıyken (uygun=0) yazılır. */
function queryOf(f,profilVar){
const sp=new URLSearchParams();
if(f.q)sp.set('q',f.q);if(f.il.length)sp.set('il',f.il.map(ilSlug).join(','));if(f.ogr)sp.set('ogr',f.ogr);if(f.sb)sp.set('sb',f.sb);if(f.tur)sp.set('tur',f.tur);if(f.yeni)sp.set('yeni','1');
if(f.uygun===false)sp.set('uygun','0');else if(f.uygun===true&&!profilVar)sp.set('uygun','1');
if(f.sira!=='son')sp.set('sira',f.sira);if(f.arsiv)sp.set('arsiv','1');
return sp.toString();}
/* Adres çubuğundaki süzgeç parametreleri İlanlar sekmesindeyken güncel tutulur, başka sekmede temizlenir. */
function syncQuery(){
try{const u=new URL(location.href),sp=new URLSearchParams(u.search);for(const k of QKEYS)sp.delete(k);
const rest=[sp.toString(),tab==='ilanlar'?queryOf(F,!!activeProfile()):''].filter(Boolean).join('&'),next=u.pathname+(rest?'?'+rest:'')+u.hash;
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
if(f.sb==='yakinda'){if(!upcoming(o))return false;}
else if(f.sb&&!(o.son_tarih&&!closed(o)&&!upcoming(o)&&days(o.son_tarih)<=Number(f.sb)))return false;
if(f.yeni&&!isNew(o))return false;
const q=normalize(f.q).trim().split(/\s+/).filter(Boolean);
if(q.length){const t=aramaMetni(o);if(!q.every(w=>t.includes(w)))return false;}
return true;}
function sortRows(list,f){
const byDl=(a,b)=>Number(closed(a))-Number(closed(b))||(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999')||a.kurum.localeCompare(b.kurum,'tr');
const cmp=f.sira==='yeni'?(a,b)=>(Date.parse(b.ilk_gorulme)||0)-(Date.parse(a.ilk_gorulme)||0):f.sira==='kurum'?(a,b)=>a.kurum.localeCompare(b.kurum,'tr'):f.sb==='yakinda'?(a,b)=>(Date.parse(a.baslangic_zaman)||0)-(Date.parse(b.baslangic_zaman)||0):byDl;
return list.slice().sort(cmp);}
const uygunAcik=(f,pr)=>!!pr&&f.uygun!==false;
function filterIlan(base,f,pr){
const a=base.filter(o=>rowMatches(o,f)),on=uygunAcik(f,pr),seviye=new Map();let bilinmiyor=0;
const u=pr?a.filter(o=>{const s=uygun(o,pr);if(s==='bilinmiyor'){bilinmiyor++;return f.ogr==='bilinmiyor';}if(s)seviye.set(o.key,s);return !!s;}):[];
let list=sortRows(on?u:a,f);
if(on)list=list.sort((x,y)=>Number(seviye.get(x.key)==='alt')-Number(seviye.get(y.key)==='alt')||ilRank(x,pr)-ilRank(y,pr));
return{list,seviye,tum:a.length,uyan:u.length,disinda:on?a.length-u.length:0,bilinmiyor:f.ogr==='bilinmiyor'?0:bilinmiyor,on};}
const suzgecVar=f=>!!(f.q||f.il.length||f.ogr||f.sb||f.tur||f.yeni||f.arsiv);
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
/* ---------- İlanlar: çip çubuğu ve menüler ---------- */
const MENU=['ogr','il','sb','tur','sira'],MENU_BASLIK={ogr:'Öğrenim düzeyi',il:'İl',sb:'Son başvuru',tur:'İlan türü',sira:'Sırala'};
function buildChips(){
const bar=$('cip-seridi');if(!bar||chips.uygun)return;
const mk=(id,fn,cls)=>{const b=E('button','cip'+(cls?' '+cls:''));b.type='button';b.onclick=fn;chips[id]=b;if(MENU.includes(id)){b.setAttribute('aria-haspopup','dialog');b.setAttribute('aria-controls','cip-menu');b.setAttribute('aria-expanded','false');}bar.append(b);return b;};
mk('uygun',()=>{if(!activeProfile()){openProfile();return;}F.uygun=!uygunAcik(F,activeProfile());ilanDegisti();});
mk('ogr',()=>menuAc('ogr'));mk('il',()=>menuAc('il'));mk('sb',()=>menuAc('sb'));mk('tur',()=>menuAc('tur'));
mk('yeni',()=>{F.yeni=!F.yeni;ilanDegisti();});
mk('arsiv',()=>{F.arsiv=!F.arsiv;ilanDegisti();});
mk('sira',()=>menuAc('sira'),'sirala');}
function updateChips(res,pr){
const set=(id,label,on,opt={})=>{const b=chips[id];if(!b)return;b.className='cip'+(on?' secili':'')+(id==='sira'?' sirala':'');if(id!=='sira')b.setAttribute('aria-pressed',String(on));
const kids=[];if(opt.tik)kids.push(ic('ok'));kids.push(label);if(opt.sayi!==undefined)kids.push(E('small','',String(opt.sayi)));if(MENU.includes(id))kids.push(ic('asagi'));b.replaceChildren(...kids);};
const on=res.on;
set('uygun','Profilime uygun',on,{tik:on,sayi:pr?res.uyan:undefined});
set('ogr',(OGR_SECENEK.find(x=>x[0]===F.ogr)||[0,'Öğrenim'])[1],!!F.ogr);
set('il',F.il.length?F.il.slice(0,2).join(', ')+(F.il.length>2?' +'+(F.il.length-2):''):'İl',!!F.il.length);
set('sb',F.sb?SB_SECENEK.find(x=>x[0]===F.sb)[1]:'Son başvuru',!!F.sb);
set('tur',F.tur||'İlan türü',!!F.tur);
set('yeni','Yalnız yeniler',F.yeni);
set('arsiv','Sona erenler dahil',F.arsiv);
set('sira','Sırala: '+SIRA_SECENEK.find(x=>x[0]===F.sira)[1].replace(/: en yakın$/,''),false);}
const ilSayilari=()=>{const m=new Map();for(const o of liste){if(closed(o))continue;for(const k of new Set(ilKeys(o))){const il=IL_LIST.find(x=>ilSlug(x)===k);if(il)m.set(il,(m.get(il)||0)+1);}}return m;};
const menuMobil=()=>{try{return matchMedia('(max-width:760px)').matches;}catch{return false;}};
function menuKapat(odak){
const m=$('cip-menu'),id=menuAcik;menuAcik=null;if(m)m.hidden=true;if($('cip-perde'))$('cip-perde').hidden=true;
for(const k of MENU)if(chips[k])chips[k].setAttribute('aria-expanded','false');
if(odak&&id&&chips[id]&&chips[id].focus)chips[id].focus();}
function menuAc(id){
if(menuAcik===id){menuKapat(true);return;}
const m=$('cip-menu');menuAcik=id;
for(const k of MENU)chips[k].setAttribute('aria-expanded',String(k===id));
menuIcerik(id);m.hidden=false;if($('cip-perde'))$('cip-perde').hidden=!menuMobil();
const c=chips[id];if(c.getBoundingClientRect&&!menuMobil()){const r=c.getBoundingClientRect(),w=m.offsetWidth||280;m.style.left=Math.max(12,Math.min(r.left,window.innerWidth-w-12))+'px';m.style.top=(r.bottom+8)+'px';}
const f=menuMobil()?m.querySelector&&m.querySelector('#cip-menu-baslik'):m.querySelector&&m.querySelector('input,button');if(f&&f.focus)f.focus();}
function menuIcerik(id){
const m=$('cip-menu');m.replaceChildren();m.setAttribute('aria-labelledby','cip-menu-baslik');m.setAttribute('aria-modal',String(menuMobil()));const bas=E('p','mbas',MENU_BASLIK[id]);bas.id='cip-menu-baslik';bas.tabIndex=-1;m.append(bas);
const opt=(t,on,fn,sayi)=>{const b=E('button','mo'+(on?' secili':''));b.type='button';b.setAttribute('aria-pressed',String(on));b.append(E('span','',t));if(sayi!==undefined)b.append(E('small','',String(sayi)));b.append(ic('ok'));b.onclick=fn;return b;};
const tek=(list,cur,set,tum)=>{const box=E('div','mlist');const pick=v=>()=>{set(v);ilanDegisti();menuKapat(true);};if(tum!==null)box.append(opt(tum,!cur,pick('')));for(const [v,t] of list)box.append(opt(t,cur===v,pick(v)));m.append(box);};
if(id==='ogr')tek(OGR_SECENEK,F.ogr,v=>F.ogr=v,'Tüm düzeyler');
else if(id==='sb')tek(SB_SECENEK,F.sb,v=>F.sb=v,'Tüm tarihler');
else if(id==='sira')tek(SIRA_SECENEK,F.sira,v=>F.sira=v||'son',null);
else if(id==='tur'){const L=turSecenekleri();if(!L.length)m.append(E('p','mbos','İlan türü bilgisi yok.'));else tek(L.map(x=>[x[0],x[0]]),F.tur,v=>F.tur=v,'Tüm ilan türleri');}
else if(id==='il'){
const kutu=E('div','mlist'),ara=E('input','mara'),say=ilSayilari();ara.type='search';ara.placeholder='İl ara…';ara.autocomplete='off';ara.setAttribute('aria-label','İl ara');
const ciz=()=>{const q=normalize(ara.value).trim(),L=IL_LIST.filter(il=>(say.has(il)||F.il.includes(il))&&(!q||normalize(il).includes(q)));
kutu.replaceChildren(...L.map(il=>{const b=opt(il,F.il.includes(il),()=>{F.il=F.il.includes(il)?F.il.filter(x=>x!==il):[...F.il,il].slice(0,10);const now=F.il.includes(il);b.className='mo'+(now?' secili':'');b.setAttribute('aria-pressed',String(now));ilanDegisti();},say.get(il)||0);return b;}));
if(!L.length)kutu.append(E('p','mbos','Eşleşen il yok.'));};
ara.oninput=ciz;ciz();
const alt=E('div','malt'),t=E('button','btn btn-ikinci','Temizle'),k=E('button','btn btn-ana','Tamam');t.type=k.type='button';t.onclick=()=>{F.il=[];ilanDegisti();ciz();};k.onclick=()=>menuKapat(true);alt.append(t,k);
m.append(ara,kutu,alt);}}
function kontrolMetni(){
if(!listeZaman)return '';const t=Date.parse(listeZaman);
return 'Son kontrol '+(istDate(t)===today()?'bugün ':uzunTarih(istDate(t))+' ')+trTime(t);}
function suzgecOzeti(f,res){
const p=[];if(res.on)p.push('Profilime uygun');if(f.q)p.push('“'+f.q.slice(0,40)+'”');if(f.ogr)p.push((OGR_SECENEK.find(x=>x[0]===f.ogr)||[0,''])[1]);
if(f.il.length)p.push(f.il.slice(0,2).join(', ')+(f.il.length>2?' +'+(f.il.length-2):''));
if(f.sb)p.push(SB_SECENEK.find(x=>x[0]===f.sb)[1]);if(f.tur)p.push(f.tur);if(f.yeni)p.push('yalnız yeniler');if(f.arsiv)p.push('arşiv dahil');
const b=!f.arsiv&&!f.sb?breakdown(res.list):'';
if(b)p.push(b);return p.join(' · ');}
function renderIlanlar(){
buildChips();
const pr=activeProfile();
if(!loaded&&(F.q||F.arsiv))ensureFull();
if(F.tur&&listeLoaded&&!turSecenekleri().some(x=>x[0]===F.tur))F.tur='';
const bk=$('kontrol');if(bk){const a=liste.filter(o=>!closed(o)),y=a.filter(o=>o.ilk_gorulme&&istDate(o.ilk_gorulme)===today()).length;bk.replaceChildren(E('span','nokta'),(kontrolMetni()?kontrolMetni()+' · ':'')+a.length+' açık ilan · bugün '+y+' yeni');}
if(bekleniyor(F)){$('result-count').textContent='İlanlar yükleniyor…';$('filter-summary').textContent='';$('cards').replaceChildren();$('cards').hidden=true;$('empty').hidden=true;$('disinda').hidden=true;updateChips({on:uygunAcik(F,pr),uyan:0},pr);return;}
const res=filterIlan(ilanBase(F),F,pr),list=res.list,vis=list.slice(0,shown);
updateChips(res,pr);
$('result-count').textContent=list.length+' ilan';
{const fs=$('filter-summary'),oz=suzgecOzeti(F,res);
if(res.on&&res.bilinmiyor>0){const b=E('button','yazi-link','göster');b.type='button';b.onclick=()=>{Object.assign(F,bilinmiyorYama(pr));ilanDegisti();};fs.replaceChildren((oz?oz+' · ':'')+res.bilinmiyor+' ilanın öğrenim şartı okunamadı ',b);}else fs.textContent=oz;}
$('clear').hidden=!suzgecVar(F);
const nodes=vis.map(o=>rowEl(o,{yeni:true,alt:res.seviye.get(o.key)==='alt'}));
if(list.length>vis.length){
const d=E('div','daha'),bar=E('div','bar'),fill=E('i'),b=E('button','btn btn-ikinci','Daha fazla göster');
fill.style.width=Math.round(vis.length/list.length*100)+'%';bar.setAttribute('aria-hidden','true');bar.append(fill);b.type='button';b.onclick=()=>{shown+=PAGE_SIZE;renderIlanlar();};
d.append(bar,E('small','',vis.length+' / '+list.length+' ilan gösteriliyor'),b);nodes.push(d);}
$('cards').replaceChildren(...nodes);$('cards').hidden=!list.length;$('empty').hidden=!!list.length;
if(!list.length){
const q=F.q.slice(0,60),kids=[E('h3','',q?'“'+q+'” için açık ilan bulunamadı.':'Bu süzgeçlerle ilan bulunamadı.'),E('p','','Yazımı kontrol et, bir süzgeci kaldır'+(res.on?' veya profilinin dışındaki ilanlara da bak':'')+'.')];
if(suzgecVar(F)){const b=E('button','btn btn-ikinci','Süzgeçleri temizle');b.type='button';b.onclick=temizle;kids.push(b);}
if(res.on&&res.disinda>0){const b=E('button','btn btn-ikinci','Profilimin dışındaki '+res.disinda+' ilanı göster');b.type='button';b.onclick=()=>{F.uygun=false;ilanDegisti();};kids.push(b);}
$('empty').replaceChildren(...kids);}
const dis=$('disinda');dis.hidden=!(res.on&&res.disinda>0&&list.length);
if(!dis.hidden){const s=E('span'),b=E('button','yazi-link','Tümünü göster ');b.type='button';b.append(ic('sag'));b.onclick=()=>{F.uygun=false;ilanDegisti();};s.append('Profilinin dışında ',E('b','',String(res.disinda)),' açık ilan daha var — diğer iller ve öğrenim düzeyleri.');dis.replaceChildren(s,b);}
syncQuery();renderCompare();}
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
if(!rows.length){const a=E('a','btn btn-ana','İlanlara bak');a.href='#ilanlar';a.onclick=e=>{e.preventDefault();openIlanlar({uygun:false});};box.replaceChildren(bosKutu(E('p','','Henüz kaydettiğin ilan yok.'),E('p','','Bir ilanı kaydetmek için satırın sağındaki yer imi simgesine dokun. Kaydettiklerin burada, son başvuru gününe göre sıralı görünür; son günü yaklaşınca Bugün sayfasında hatırlatırız.'),a));return;}
const bar=E('div','kayit-arac'),yazi=E('p','','Karşılaştırmak için iki veya üç ilanın “Karşılaştır” kutusunu işaretle.'),ics=E('button','btn btn-ikinci');
const n=loaded?kayitliTakvimlik().length:0;ics.type='button';ics.textContent='Takvimime ekle (.ics)'+(n?' · '+n:'');
ics.onclick=()=>{if(!loaded){notify('İlan ayrıntıları yükleniyor; birkaç saniye sonra yeniden dene.');ensureFull();return;}const l=kayitliTakvimlik();if(!l.length){notify('Takvime eklenecek açık ve tarihli kayıtlı ilan yok.');return;}downloadCalendar(l);};
bar.append(yazi,ics);
const out=[bar];kayitliGruplari(rows).forEach((g,i)=>out.push(sectionEl('k-'+i,{baslik:g.baslik,sayi:g.rows.length,govde:listeEl(g.rows,{kars:true})})));
box.replaceChildren(...out);}
/* Rozet yalnızca bilinen (listede ya da tam kayıtta bulunan) kayıtlı ilanları sayar; veri gelmeden ham sayı gösterilir. */
function savedCount(){if(!listeLoaded&&!loaded)return saved.size;return new Set([...saved].map(id=>idKey.get(id)||(iids.has(id)?id:null)).filter(Boolean)).size;}
function render(){
if(!loaded&&!listeLoaded)return;
const n=savedCount();for(const id of ['saved-count','saved-count-m']){const e=$(id);if(e){e.textContent=n;e.hidden=!n;}}
if(tab==='bugun')renderBugun();else if(tab==='ilanlar')renderIlanlar();else if(tab==='takvim')renderTakvim();else if(tab==='kayitli')renderKayitli();
renderCompare();sig=imza();}
/* ---------- gezinme ---------- */
function showTab(t){
tab=t;lastTab=t;
for(const x of TABS){const v=$('v-'+x);if(v)v.hidden=x!==t;}
document.querySelectorAll('[data-tab]').forEach(a=>{const on=a.dataset.tab===t;a.classList.toggle('aktif',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute&&a.removeAttribute('aria-current');});
if(menuAcik)menuKapat();
syncQuery();render();tryWriteVisit();}
function renderCompare(){const on=tab==='kayitli'&&compared.size>0;$('compare-bar').hidden=!on;$('compare-count').textContent=compared.size+' / 3 ilan seçildi';$('compare-open').disabled=compared.size<2;if(document.body)document.body.classList.toggle('kars-acik',on);}
function closeModal(){if($('modal').open)$('modal').close();document.title=defaultTitle;}
function route(){
const hash=location.hash.slice(1);
$('modal-back').href='#'+lastTab;
if(hash.startsWith('ilan/')||hash==='karsilastir'){if(!loaded){ensureFull().then(()=>{if(loaded)route();else notify('Ayrıntılı ilan verisi yüklenemedi.');});return;}}
if(hash.startsWith('ilan/')){let k;try{k=decodeURIComponent(hash.slice(5));}catch{k='';}const i=items.find(x=>x.key===k);if(i)showDetail(i);else{const h=E('h2','','Bu ilan artık listede bulunmuyor.');h.id='modal-title';$('modal-body').replaceChildren(h,E('p','','Güncel ilanları keşfedebilir veya resmî kaynağı kontrol edebilirsin.'),external('https://kariyerkapisi.gov.tr/isealim','Kariyer Kapısı ↗'));openModal();}}
else if(articles[hash])showArticle(hash);
else if(hash==='karsilastir')showComparison();
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
if(listeLoaded&&tab==='bugun'&&document.visibilityState==='visible'){visitWritten=true;writeStore('kit-son-ziyaret',new Date().toISOString());}}
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
profil=validProfile(p);writeStore('kit-profil',profil);$('profil-dialog').close();kaydirKilidi(false);render();notify('Profilin kaydedildi.');}
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
const GUNES='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/></svg>',AY_IKON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
function applyTheme(){const dark=readStore('kit-theme',null)==='dark';document.documentElement.dataset.theme=dark?'dark':'light';const t=$('theme');t.innerHTML=dark?GUNES:AY_IKON;t.setAttribute('aria-pressed',String(dark));t.setAttribute('aria-label',dark?'Açık temaya geç':'Koyu temaya geç');const m=document.querySelector&&document.querySelector('meta[name=theme-color]');if(m)m.content=dark?'#0D0E0C':'#F6F6F1';}
async function loadSponsors(){try{const r=await fetch('sponsors.json',{cache:'no-store'});if(!r.ok)return;const cfg=await r.json();if(!cfg.enabled)return;for(const placement of ['sidebar','feed']){const s=cfg[placement],url=s&&safeURL(s.url);if(!s||!url||!s.title)continue;const box=E('aside','sponsor');box.setAttribute('aria-label','Reklam');box.append(E('span','eyebrow','REKLAM · SPONSORLU'));const a=external(url,s.title,'');a.rel='sponsored noopener noreferrer';box.append(a,E('p','',s.description||''));adBox[placement].replaceChildren(box);adBox[placement].hidden=false;}}catch{/* Optional sponsorship cannot break listing discovery. */}}
async function getJSON(url,cache){const r=await fetch(url,{cache});if(!r.ok)throw Error(url);return r.json();}
let sec=new Map(),lmap=new Map(),fmap=new Map(),iids=new Set(),lids=new Set(),fullPromise=null,fullFailed=false,sig='';
async function loadListe(){
try{const d=await getJSON('liste.json','no-cache');if(!d||!Array.isArray(d.ilanlar))throw Error('shape');
listeTum=d.ilanlar.map(cleanL).filter(Boolean);listeVar=true;listeZaman=typeof d.guncelleme==='string'&&!isNaN(Date.parse(d.guncelleme))?d.guncelleme:'';lmap=new Map(listeTum.map(o=>[o.key,o]));
/* Kopya (kaynaklar arası yinelenen) ikincil satırlar her listeden, sayıdan ve süzgeçten çıkar; kimlikleri birincile eşlenir. */
alias=new Map();gizli=new Set();sec=new Map();idKey=new Map();
for(const o of listeTum){const p=o.kopya_of&&lmap.get(o.kopya_of);if(p&&!p.kopya_of){gizli.add(o.key);alias.set(p.key,[...(alias.get(p.key)||[]),o.id]);sec.set(p.key,[...(sec.get(p.key)||[]),o.key]);idKey.set(o.id,p.key);}else idKey.set(o.id,o.id);}
liste=listeTum.filter(o=>!gizli.has(o.key));lids=new Set(listeTum.map(o=>o.id));listeUyari=d.uyari&&typeof d.uyari==='object'?cleanUyari(d.uyari):null;listeLoaded=true;}catch{listeVar=false;}}
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
if(failed.length&&!listeUyari){$('freshness').hidden=false;$('freshness').textContent=failed.join(' ve ')+' kaynağına erişimde sorun var; bu kaynağın ilanları güncel olmayabilir. Erişim sonraki taramada yeniden denenecek.';}
fmap=new Map(items.map(i=>[i.key,i]));iids=new Set(items.map(i=>i.id));
listeLoaded=true;}
else{fullPromise=null;fullFailed=true;if(tab==='ilanlar'&&bekleniyor(F)){F.tur='';F.arsiv=false;if(F.ogr==='belediye')F.ogr='';}$('result-count').textContent='Ayrıntılı ilan verisi yüklenemedi; yeniden denemek için sayfayı yenile.';}
render();})();
return fullPromise;}
async function load(){
await loadListe();
if(listeVar){render();route();return;}
await ensureFull();
if(!loaded){$('bugun').replaceChildren(E('p','not','İlan listesi yüklenemedi. Biraz sonra yeniden dene veya resmî ilan sayfalarını ziyaret et.'),external('https://kariyerkapisi.gov.tr/isealim','Resmî ilanlar ↗','btn btn-ikinci'));return;}
route();}
applyTheme();$('year').textContent=new Date().getFullYear();
profil=validProfile(readStore('kit-profil',null));
sonZiyaret=frozenVisit();
let profilAc=false;
try{const u=new URL(location.href);if(u.searchParams.has('g')||u.searchParams.has('profil')){profilAc=u.searchParams.get('profil')==='1';u.searchParams.delete('g');u.searchParams.delete('profil');history.replaceState(null,'',u.pathname+u.search+u.hash);}}catch{}
let bootTab=TABS.includes(location.hash.slice(1))?location.hash.slice(1):'bugun';
try{const u=new URL(location.href);if(queryHas(u.search)){F=parseQuery(u.search);$('search').value=F.q;bootQuery=true;
if(location.hash===''){history.replaceState(null,'',u.pathname+u.search+'#ilanlar');bootTab='ilanlar';}}}catch{}
$('theme').onclick=()=>{writeStore('kit-theme',document.documentElement.dataset.theme==='dark'?'light':'dark');applyTheme();};
$('search-form').onsubmit=e=>{e.preventDefault();F.q=$('search').value.trim().slice(0,80);ilanDegisti();};
$('search').oninput=()=>{F.q=$('search').value.slice(0,80);if(F.q.trim())ensureFull();ilanDegisti();};
$('clear').onclick=temizle;
document.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>{F.q=b.dataset.query;$('search').value=F.q;ilanDegisti();});
document.querySelectorAll('[data-seg]').forEach(b=>b.onclick=()=>{tkSeg=b.dataset.seg;takvimGun=7;renderTakvim();});
if(document.addEventListener){
document.addEventListener('click',e=>{if(!menuAcik)return;const m=$('cip-menu'),c=chips[menuAcik];if(m.contains(e.target)||(c&&c.contains(e.target)))return;menuKapat();});
document.addEventListener('keydown',e=>{if(!menuAcik)return;if(e.key==='Escape'){menuKapat(true);return;}if(e.key==='Tab'&&menuMobil()){const m=$('cip-menu'),f=[...m.querySelectorAll('#cip-menu-baslik,input,button')];if(!f.length)return;const i=f.indexOf(document.activeElement);if(e.shiftKey&&i<=0){e.preventDefault();f[f.length-1].focus();}else if(!e.shiftKey&&(i<0||i===f.length-1)){e.preventDefault();f[0].focus();}}});
if($('cip-perde'))$('cip-perde').onclick=e=>{e.preventDefault();e.stopPropagation();menuKapat(true);};}
window.addEventListener('scroll',()=>{if(menuAcik&&!menuMobil())menuKapat();},{passive:true});let sonGen=window.innerWidth;window.addEventListener('resize',()=>{const w=window.innerWidth;if(menuAcik&&w!==sonGen)menuKapat();sonGen=w;});
$('nav-saved').onclick=()=>goTab('kayitli');
$('nav-search').onclick=()=>{goTab('ilanlar');setTimeout(()=>$('search').focus(),50);};
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
showTab(bootTab);load();loadSponsors();
