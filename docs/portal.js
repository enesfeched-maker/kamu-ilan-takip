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
let saved=new Set(Array.isArray(readStore('kit-saved',[]))?readStore('kit-saved',[]):[]), compared=new Set(), items=[], liste=[], listeVar=false, listeZaman='', view='active', shown=20, takvimGun=7, loaded=false, listeLoaded=false, toastTimer, profil=null, sonZiyaret=null, tab='bugun', lastTab='bugun';
const PAGE_SIZE=20, defaultTitle=document.title;
const TABS=['bugun','ilanlar','takvim','kayitli','rehber'];
const AY=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'],AYU=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'],GUNLER=['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'];
const IL_LIST=['Adana','Adıyaman','Afyonkarahisar','Ağrı','Aksaray','Amasya','Ankara','Antalya','Ardahan','Artvin','Aydın','Balıkesir','Bartın','Batman','Bayburt','Bilecik','Bingöl','Bitlis','Bolu','Burdur','Bursa','Çanakkale','Çankırı','Çorum','Denizli','Diyarbakır','Düzce','Edirne','Elazığ','Erzincan','Erzurum','Eskişehir','Gaziantep','Giresun','Gümüşhane','Hakkari','Hatay','Iğdır','Isparta','İstanbul','İzmir','Kahramanmaraş','Karabük','Karaman','Kars','Kastamonu','Kayseri','Kırıkkale','Kırklareli','Kırşehir','Kilis','Kocaeli','Konya','Kütahya','Malatya','Manisa','Mardin','Mersin','Muğla','Muş','Nevşehir','Niğde','Ordu','Osmaniye','Rize','Sakarya','Samsun','Siirt','Sinop','Sivas','Şanlıurfa','Şırnak','Tekirdağ','Tokat','Trabzon','Tunceli','Uşak','Van','Yalova','Yozgat','Zonguldak'];
const IC={sag:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg>',kayit:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.5h10a1 1 0 0 1 1 1V21l-6-4-6 4V4.5a1 1 0 0 1 1-1z"/></svg>',ok:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',saat:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>',grafik:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10m6 10V4m6 16v-7m4 7H3"/></svg>',kisi:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>',kalem:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4z"/></svg>',tg:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 4-18 7.2 6 2.3M21 4l-3 16-8.5-6.5M21 4 9.5 13.5v5.5l3-3.5"/></svg>',kitap:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5C6.5 4 9.5 4 12 6c2.5-2 5.5-2 8-.5V19c-2.5-1.5-5.5-1.5-8 .5-2.5-2-5.5-2-8-.5z"/><path d="M12 6v13.5"/></svg>',x:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>'};
function ic(name){const s=E('span','ic');s.innerHTML=IC[name]||'';return s;}
const istDate=v=>new Date(v).toLocaleDateString('sv-SE',{timeZone:'Europe/Istanbul'});
const kisaTarih=s=>{const [,m,d]=s.split('-').map(Number);return d+' '+AY[m-1];};
const uzunTarih=s=>{const [,m,d]=s.split('-').map(Number);return d+' '+AYU[m-1];};
const gunAdi=s=>GUNLER[(new Date(s+'T12:00:00Z').getUTCDay()+6)%7];
function ekSi(n){const son={0:'ı',1:'i',2:'si',3:'ü',4:'ü',5:'i',6:'sı',7:'si',8:'i',9:'u'},on={10:'u',20:'si',30:'u',40:'ı',50:'si',60:'ı',70:'i',80:'i',90:'ı'};return n+'’'+(n%10||n===0?son[n%10]:on[n%100]||'ü');}
function baslikTemiz(s){s=String(s||'').replace(/^İlk Defa Atanmak Üzere\s+/,'').replace(/\s+Alım(?:ı)?\s+İlanı$/,' alımı').replace(/\s+Sınav(?:ı)?\s+(?:İlanı|Duyurusu)$/,' sınavı').replace(/\s+İlanı$/,'').replace('Vhki','VHKİ').replace('.net','.NET');return s.charAt(0).toLocaleUpperCase('tr-TR')+s.slice(1);}
const KEY_RE=/^[A-Za-z0-9-]{1,80}$/,DATE_RE=/^\d{4}-\d{2}-\d{2}$/,DT_RE=/^\d{4}-\d{2}-\d{2}T[0-9:.+Zz-]{5,40}$/,PT_RE=/^P\d{1,3}$/;
const posInt=(v,max)=>Number.isInteger(v)&&v>0&&v<max?v:0;
const str=(v,n)=>typeof v==='string'?v.slice(0,n):'';
const strList=(v,n,m)=>Array.isArray(v)?v.filter(x=>typeof x==='string'&&x.length<=m).slice(0,n):[];
/* liste.json kaydını doğrular: her alan biçim denetiminden geçer, geçmeyen alan boşaltılır. */
function cleanL(l){
if(!l||typeof l!=='object'||!KEY_RE.test(l.key||''))return null;
const o={key:l.key,id:str(l.id,120)||l.key,manset:str(l.manset,160),ek:posInt(l.ek,1000),toplam:posInt(l.toplam,20000),kurum:str(l.kurum,200),il:str(l.il,80),kpss:l.kpss==='kpss'||l.kpss==='kpsssiz'?l.kpss:'',son_tarih:DATE_RE.test(l.son_tarih||'')?l.son_tarih:'',durum:str(l.durum,12)};
for(const k of ['son_zaman','baslangic_zaman','ilk_gorulme'])o[k]=typeof l[k]==='string'&&DT_RE.test(l[k])&&!isNaN(Date.parse(l[k]))?l[k]:'';
o.meslek=Array.isArray(l.meslek)?l.meslek.filter(f=>typeof f==='string'&&MESLEK.test(f)).slice(0,3):[];
o.logo=IMG_PATH.test(l.logo||'')?l.logo:'';
o.kurum_slug=typeof l.kurum_slug==='string'&&l.kurum_slug.length<=80&&SLUG.test(l.kurum_slug)?l.kurum_slug:'';
o.iller=strList(l.iller,20,80);o.ogrenim=strList(l.ogrenim,3,20).filter(x=>LEVELS[x]);o.puan_turleri=strList(l.puan_turleri,8,5).filter(x=>PT_RE.test(x));
const t=l.taban_ref;o.taban_ref=t&&typeof t==='object'&&LEVELS[t.duzey]&&typeof t.medyan==='number'&&t.medyan>0&&t.medyan<=100&&Number.isInteger(t.n)&&t.n>=5?{duzey:t.duzey,medyan:t.medyan,n:t.n}:null;
return o;}
/* liste.json yoksa/yüklenemezse satır modeli tam kayıttan türetilir (taban referansı ve puan türü olmadan). */
function fallbackModel(i){const t=i.toplam||kadroSayisi(i);return{key:i.key,id:i.id,manset:baslikTemiz(i.manset||title(i)),ek:i.ek||0,toplam:t||0,kurum:kurumAdi(i.kurum),il:placeName(i),iller:strList(i.iller,20,80),ogrenim:(i.ogrenim||[]).filter(x=>LEVELS[x]),meslek:i.meslek||[],logo:i.logo||'',kurum_slug:i.kurum_slug||'',kpss:i.kpss||'',puan_turleri:[],taban_ref:null,son_tarih:i.son_tarih||'',son_zaman:i.son_zaman||'',baslangic_zaman:i.baslangic_zaman||'',ilk_gorulme:i.ilk_gorulme||'',durum:''};}
const rowOf=i=>i.L||fallbackModel(i);
function save(i){const was=saved.has(i.id);was?saved.delete(i.id):saved.add(i.id);const ok=writeStore('kit-saved',[...saved]);render();const full=items.find(x=>x.id===i.id);if(location.hash.startsWith('#ilan/')&&full)showDetail(full);notify(ok?(was?'İlan kaydedilenlerden kaldırıldı.':'İlan bu tarayıcıya kaydedildi.'):'Tarayıcı depolaması kapalı; seçim yalnızca bu oturumda saklanır.');}
function saveButton(i){const b=E('button','kaydet'+(saved.has(i.id)?' dolu':''));b.type='button';b.setAttribute('aria-label',(saved.has(i.id)?'Kaydı kaldır: ':'İlanı kaydet: ')+(i.manset||title(i)));b.setAttribute('aria-pressed',String(saved.has(i.id)));b.innerHTML=IC.kayit;b.onclick=e=>{e.stopPropagation();save(i);};return b;}
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
function detailLink(i,label,cls){const a=E('a',cls,label);a.href='ilan/'+encodeURIComponent(i.key)+'/';a.onclick=e=>{if(!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey&&e.button===0){e.preventDefault();location.hash='ilan/'+encodeURIComponent(i.key);}};return a;}
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
function breakdown(list){let a=0,u=0,x=0;for(const i of list){if(upcoming(i))u++;else if(!i.son_tarih)x++;else if(knownActive(i))a++;}const p=[];if(a)p.push(a+' başvurusu açık');if(u)p.push(u+' yakında başlıyor');if(x)p.push(x+' tarihi belirsiz');return p.length>1||u||x?p.join(' · '):'';}
function external(url,label,cls='button primary'){const a=E('a',cls,label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function openModal(){if(!$('modal').open)$('modal').showModal();$('modal').scrollTop=0;}
function infoSection(parent,heading,text){parent.append(E('h3','',heading),E('p','',text));}
function showDetail(i){const body=$('modal-body');body.replaceChildren();const header=E('div','detail-header');header.append(E('span','eyebrow',i.ilan_turu||'KAMU PERSONEL ALIMI'));const h=E('h2','',title(i));h.id='modal-title';header.append(h,kurumNode(i,'detail-kurum'));const vis=cardImage(i,false);if(vis){const box=E('div','detail-visual');if(i.logo)box.append(logoNode(i,'detail-logo',64));box.append(vis);body.append(box);}body.append(header);const layout=E('div','detail-layout'),content=E('div','detail-content'),side=E('aside','detail-aside'),dl=E('dl');for(const [k,v] of [['Durum',status(i)],['Görev yeri',proper(i.yer)||'Resmî ilandan kontrol et'],['Son başvuru',trDate(i.son_tarih)+(i.son_zaman?' · '+trTime(i.son_zaman)+' TSİ':'')],['Başlangıç',i.baslangic_zaman?trDate(i.baslangic_zaman):'Belirtilmemiş']])dl.append(E('dt','',k),E('dd','',v));side.append(dl);const docURL=sourceDocument(i);const link=docURL||officialURL(i.link);if(link)side.append(external(link,docURL?'İlan belgesini aç (PDF) ↗':'Resmî ilana git · Başvur ↗'));if(docURL)side.append(E('p','muted',i.belge_aciklamasi));const sb=E('button','button secondary',saved.has(i.id)?'Kaydedildi · kaldır':'İlanı kaydet');sb.onclick=()=>save(i);const share=E('button','button secondary','Bağlantıyı paylaş');share.onclick=()=>shareItem(i);side.append(sb,share);if(i.son_tarih&&!closed(i)&&!i.duyuru_turu){const calendar=E('button','button secondary','Takvimime ekle');calendar.onclick=()=>downloadCalendar(i);side.append(calendar);}side.append(E('p','muted','Kaydetmek veya takvime eklemek başvuru oluşturmaz. İşlemini resmî başvuru kanalında tamamla.'));if(stale(i))content.append(E('p','notice','Bu ilanın ayrıntıları 24 saat içinde doğrulanmadı. Başvuru yapmadan önce güncel tarih ve koşulları resmî ilandan kontrol et.'));if(closed(i))content.append(E('p','notice','Kayıtlı son başvuru zamanı geçti. Bu ilan arşiv amacıyla gösteriliyor.'));if(upcoming(i))content.append(E('p','notice','Kayıtlı başvuru başlangıcı henüz gelmedi.'));infoSection(content,'Kadro ve kontenjan',i.kadro||'Kontenjan bilgisi kaynak özetinde bulunmuyor. Tam ilanı incele.');if(i.ozet)infoSection(content,'İlan özeti',i.ozet);content.append(E('h3','','Başvuru koşullarından seçmeler'));if(i.sartlar?.length){for(const s of i.sartlar){const c=E('section','condition');c.append(E('h4','',proper(s.kadro)),E('p','',s.metin));content.append(c);}content.append(E('p','muted','Bu bölüm seçilmiş alıntıları içerir; tüm kadro ve özel koşulların listesi değildir. Üç nokta ile biten metinler kısaltılmıştır.'));}else content.append(E('p','','Kaynak özetinde başvuru koşulları yer almıyor. Mezuniyet, KPSS, yaş ve diğer şartlar için resmî ilanı aç.'));if(i.basvuru_notu)infoSection(content,'Başvuruya ilişkin not',i.basvuru_notu);const related=items.filter(x=>x.id!==i.id&&knownActive(x)).sort((a,b)=>Number(b.ilan_turu===i.ilan_turu)-Number(a.ilan_turu===i.ilan_turu)).slice(0,3);if(related.length){content.append(E('h3','','Bunlara da göz at'));const box=E('div','related');for(const r of related){const a=detailLink(r,title(r));a.append(E('span','',kurumAdi(r.kurum)+' · '+status(r)));box.append(a);}content.append(box);}content.append(E('p','muted','Kaynak: '+(i.kaynaklar?.map(s=>s.ad).join(' · ')||i.kaynak||'Kariyer Kapısı')+(i.detay_guncelleme?' · Ayrıntı kontrolü: '+trDate(i.detay_guncelleme)+' '+trTime(i.detay_guncelleme):'')));layout.append(content,side);body.append(layout);document.title=title(i)+' | Kamu İlan Takip';openModal();}
async function shareItem(i){const url=new URL(location.href);url.hash='ilan/'+encodeURIComponent(i.key);url.search='';try{if(navigator.share)await navigator.share({title:title(i),url:url.href});else{await navigator.clipboard.writeText(url.href);notify('İlan bağlantısı kopyalandı.');}}catch(e){if(e.name!=='AbortError'){const field=E('input');field.value=url.href;field.readOnly=true;field.setAttribute('aria-label','Paylaşılacak ilan bağlantısı');$('modal-body').append(field);field.focus();field.select();notify('Bağlantıyı seçip kopyalayabilirsin.');}}}
function calendarText(i){const esc=v=>String(v||'').replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');const utc=d=>new Date(d).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z/,'Z');const date=i.son_zaman?Date.parse(i.son_zaman):null;const timing=date?['DTSTART:'+utc(date),'DTEND:'+utc(date+60000)]:['DTSTART;VALUE=DATE:'+i.son_tarih.replace(/-/g,''),'DTEND;VALUE=DATE:'+new Date(Date.parse(i.son_tarih+'T00:00:00Z')+86400000).toISOString().slice(0,10).replace(/-/g,'')];return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Kamu Ilan Takip//TR','BEGIN:VEVENT','UID:'+esc(i.key)+'@kamu-ilan-takip','DTSTAMP:'+utc(Date.now()),...timing,'SUMMARY:'+esc('Son başvuru: '+title(i)),'DESCRIPTION:'+esc('Resmî ilandaki güncel tarih ve koşulları kontrol edin. '+i.link),'URL:'+officialURL(i.link),'END:VEVENT','END:VCALENDAR'].join('\r\n')+'\r\n';}
function downloadCalendar(i){const u=URL.createObjectURL(new Blob([calendarText(i)],{type:'text/calendar;charset=utf-8'})),a=E('a');a.href=u;a.download='kamu-ilan-son-basvuru.ics';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);notify('Takvim dosyası indirildi. Takvim uygulamana ekleyebilirsin.');}
const articles={
 'rehber/ilan-okuma':{title:'Bir ilanı nasıl okumalısın?',intro:'Başlığın uygun görünmesi tek başına yeterli değildir. İncelemeyi seçtiğin kadro üzerinden yap.',sections:[['1. Önce kadroyu belirle','Aynı ilanda farklı unvanlar ve farklı koşullar bulunabilir. Başvurmak istediğin kadronun adı, kodu, görev yeri ve kontenjanını not et.'],['2. Koşulları birlikte değerlendir','Mezuniyet programı, puan türü ve yılı, varsa asgari puan, deneyim ve belge koşullarını tam metinden kontrol et. İlan özetindeki alıntıları tüm şartların yerine koyma.'],['3. Başvuru yolunu ve zamanı kontrol et','İlanda belirtilen başvuru kanalını kullan. Son günün yanında saat bilgisi ve varsa ayrıca teslim edilmesi gereken belgelerin tarihini de incele.'],['4. Duyurulara geri dön','Düzeltme, sonuç ve ek duyuruları ilgili kurumun resmî kanallarından takip et. Bu platform başvuru kabul etmez veya uygunluk kararı vermez.']]},
 'rehber/basvuru-listesi':{title:'Başvuru kontrol listesi',intro:'Her ilan için bu kısa listeyi yeniden gözden geçir.',steps:['Başvuracağın kadro kodunu ve görev yerini seç.','Mezuniyet ve puan koşullarını tam ilan metniyle karşılaştır.','İstenilen belgelerin güncel ve okunaklı olduğundan emin ol.','Son başvuru tarihini, saatini ve varsa ek belge teslim tarihini not et.','Resmî başvuru kanalında işlemini tamamla.','Başvurunun durumunu ilgili sistemde doğrula; kayıt veya başvuru belgeni sakla.','Sonuç ve sonraki aşama duyurularını resmî kurumdan takip et.'],sections:[['Kaydetmek, başvurmak değildir','Buradaki yer imi kişisel takip içindir. Başvuru işlemini ilanda belirtilen resmî kanalda ayrıca tamamlamalısın.']]},
 'rehber/takvim':{title:'Son günü bekleme.',intro:'İlanları son tarihlerine göre sıralamak, başvuru planını daha görünür kılar.',sections:[['Önce yakın tarihleri incele','“Son 3 gün” veya “Son 7 gün” filtresini kullan. İlan kartının kalan süresi Türkiye saatine göre hesaplanır. Kesin saat belirtilmişse ayrıntı ekranında gösterilir.'],['Takvimine ekle','İlan ayrıntısındaki “Takvimime ekle” düğmesi bir takvim dosyası indirir. Dosyayı takvim uygulamanla açıp eklemeyi tamamla. Bildirim zamanını kendi takviminde seçebilirsin.'],['Tarihi yeniden doğrula','Takvim dosyası indirildiği andaki bilgiyi taşır, sonradan otomatik güncellenmez. İlanda bir değişiklik varsa takvim kaydını da güncelle.'],['Kendine hazırlık süresi bırak','Belgeleri ve başvuru adımlarını erkenden incele. Teknik sorun yaşarsan destek için ilgili kurumun ilanda belirttiği iletişim kanalını kullan.']]},
 'bilgi/hakkimizda':{title:'Hakkımızda ve veri kaynağı',intro:'Kamu İlan Takip, kamu personel ilanlarını daha kolay incelemek ve takip etmek için hazırlanmış bağımsız bir rehberdir.',sections:[['Veriler nereden geliyor?','İlanlar Kariyer Kapısı resmî RSS akışından, İŞKUR kamu memur alım ilanları sayfalarından, SBB Kamu İlan listesinden ve Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Yerel Yönetimler duyurularından (ÇŞB) derlenir. SBB belgelerinde yılı doğrulanamayan tarihler gösterilmez; SBB’den alınan ilan belgelerinin değiştirilmemiş kopyaları ilgili ilan sayfasından açılır. Kurum, görev yeri, kontenjan ve koşullar kaynağın sunduğu bilgilerle sınırlıdır.'],['Güncellik nasıl gösterilir?','Ana sayfadaki son kontrol zamanı liste taramasını gösterir. İlan ayrıntılarının kontrol tarihi ayrıca gösterilir. Otomatik bağlantılar gecikebilir; eski ayrıntılar uyarıyla sunulur.'],['Resmî bir hizmet mi?','Hayır. Herhangi bir kamu kurumuna bağlı değiliz. Başvuru kabul etmeyiz, aday uygunluğu değerlendirmeyiz. Güncel ve bağlayıcı bilgi için resmî ilanı esas alın.'],['Bir hata fark ettin mi?','İlanın bağlantısını ve hatalı alanı proje bildirim sayfasından iletebilirsin. Herkese açık bildirimlere kimlik, özgeçmiş veya başvuru belgesi ekleme.']],contact:true},
 'bilgi/gizlilik':{title:'Gizlilik ve tarayıcı verileri',intro:'Bu sürüm üyelik istemez. Özgeçmiş, kimlik bilgisi veya başvuru belgesi toplamak için bir form içermez.',sections:[['Bu cihazda saklanan bilgiler','Kaydettiğin ilanların kimlikleri, profilin (öğrenim düzeyi, puan, iller), son ziyaret zamanın ve renk teması tercihin tarayıcının yerel depolamasında tutulur. Bunlar başka cihazlara taşınmaz. Aşağıdaki düğme bu platformun yerel tercihlerini temizler.'],['Dış bağlantılar ve barındırma','Resmî başvuru sayfası, Telegram ve GitHub bağlantıları kendi hizmetlerine yönlendirir. Bu hizmetlerin veri uygulamaları ayrıdır. Site dosyaları GitHub Pages üzerinden sunulur; barındırma hizmeti teknik erişim kayıtlarını işleyebilir.'],['Reklam ve ölçüm','Bu sürümde üçüncü taraf reklam ağı veya ziyaretçi analiz kodu etkin değildir. Reklam ya da analiz hizmeti eklenmeden önce bu açıklama ve gerekli tercih mekanizmaları kullanılan hizmete göre güncellenmelidir.']],clear:true},
 'bilgi/reklam':{title:'Reklam ve iş birliği',intro:'Kamu kariyeriyle ilgilenen ziyaretçilere ulaşmak isteyen markalar için açıkça etiketlenmiş sponsor alanları.',sections:[['İki sade yerleşim','Ana sayfa yan sütununda ve ilan listesinin altında sponsor alanı ayrılmıştır. Aktif bir kampanya yoksa boş reklam kutuları gösterilmez.'],['İlanlardan ayrı bir alan','Sponsorlu içerik “Reklam · Sponsorlu” etiketi taşır. Reklamlar resmî ilan gibi gösterilmez; ilan sıralaması sponsorlu içerikten etkilenmez.'],['İş birliği talebi','Markanı, kampanya konunu ve tercih ettiğin alanı proje iletişim sayfasından paylaşabilirsin. Bu herkese açık kanala gizli ticari bilgiler veya kişisel belgeler ekleme.']],contact:true}
};
function showArticle(key){const a=articles[key];if(!a)return;const n=E('article','article');n.append(E('span','eyebrow',key.startsWith('rehber/')?'BAŞVURU REHBERİ':'KAMU İLAN TAKİP'));const h=E('h2','',a.title);h.id='modal-title';n.append(h,E('p','',a.intro));if(a.steps){const ol=E('ol');a.steps.forEach(s=>ol.append(E('li','',s)));n.append(ol);}for(const [heading,text] of a.sections)infoSection(n,heading,text);if(a.contact)n.append(external('https://github.com/enesfeched-maker/kamu-ilan-takip/issues/new','İletişim / bildirim sayfası ↗'));if(a.clear){const b=E('button','button secondary','Kaydedilen ilanları, profili ve tema tercihini temizle');b.onclick=()=>{saved.clear();writeStore('kit-saved',[]);profil=null;sonZiyaret=null;try{for(const k of ['kit-theme','kit-profil','kit-son-ziyaret'])localStorage.removeItem(k);}catch{}applyTheme();render();notify('Bu platformun yerel tercihleri temizlendi.');};n.append(b);}n.append(E('p','muted','Son düzenleme: 25 Eylül 2026'));$('modal-body').replaceChildren(n);document.title=a.title+' | Kamu İlan Takip';openModal();}
function showComparison(){const rows=items.filter(i=>compared.has(i.id));if(rows.length<2){notify('Karşılaştırmak için en az 2 ilan seç.');return;}const n=E('div','comparison'),h=E('h2','','İlanları yan yana incele');h.id='modal-title';n.append(h,E('p','muted','Bu karşılaştırma bir uygunluk değerlendirmesi değildir. Tam koşullar resmî ilandadır.'));const t=E('table'),head=E('tr');head.append(E('th','','Özellik'));for(const i of rows){const th=E('th');th.append(detailLink(i,title(i)));head.append(th);}t.append(head);for(const [name,fn] of [['Kurum',i=>kurumAdi(i.kurum)],['Görev yeri',i=>proper(i.yer)||'Belirtilmemiş'],['Kadro / kontenjan',i=>i.kadro||'Belirtilmemiş'],['Son başvuru',i=>trDate(i.son_tarih)+(i.son_zaman?' '+trTime(i.son_zaman)+' TSİ':'')],['Durum',status],['Seçilmiş koşullar',i=>(i.sartlar||[]).map(s=>proper(s.kadro)+': '+s.metin).join('\n\n')||'Resmî ilandan kontrol et']]){const tr=E('tr');tr.append(E('th','',name));rows.forEach(i=>tr.append(E('td','',fn(i))));t.append(tr);}n.append(t);$('modal-body').replaceChildren(n);openModal();}
/* ---------- satır kartı (.ilan) ---------- */
function visualOf(o){
const generic=!o.meslek.length||/^30-/.test(o.meslek[0]);
if(generic&&o.logo){const s=E('span','ilan-foto logo-karo'),im=E('img');im.src=o.logo;im.alt='';im.loading='lazy';im.decoding='async';im.onerror=()=>s.replaceWith(badge({kurum:o.kurum},'ilan-foto harf-karo'));s.append(im);return{node:s,karo:true};}
if(generic)return{node:badge({kurum:o.kurum},'ilan-foto harf-karo'),karo:false};
const im=E('img','ilan-foto');im.src='assets/meslek/'+o.meslek[0];im.alt='';im.width=52;im.height=52;im.loading='lazy';im.decoding='async';im.onerror=()=>im.replaceWith(badge({kurum:o.kurum},'ilan-foto harf-karo'));return{node:im,karo:false};}
function smallLogo(o){if(o.logo){const im=E('img','kl');im.src=o.logo;im.alt='';im.width=18;im.height=18;im.loading='lazy';im.onerror=()=>im.replaceWith(badge({kurum:o.kurum},'kb'));return im;}return badge({kurum:o.kurum},'kb');}
function metaOf(o){const p=[];if(o.toplam&&!/^\d/.test(o.manset)){const b=E('b','',o.toplam.toLocaleString('tr-TR')+' kadro');p.push(['',b]);}if(o.il)p.push(['',o.il]);if(o.ogrenim.length)p.push(['',o.ogrenim.map(x=>LEVELS[x]).join(' / ')]);if(o.puan_turleri.length)p.push(['kpss','KPSS '+o.puan_turleri.slice(0,2).join(', ')]);else if(o.kpss==='kpss')p.push(['kpss','KPSS']);const m=E('p','ilan-meta');for(const [c,v] of p.slice(0,4)){const s=E('span',c);s.append(v);m.append(s);}return m;}
function sinyalOf(o){
if(upcoming(o)){const b=new Date(Date.parse(o.baslangic_zaman)),d=istDate(b),p=E('p','sinyal acilis');p.append(ic('saat'),'Başvuru '+uzunTarih(d)+'’de açılıyor');return p;}
const pr=profil&&!profil.atlandi?profil:null,r=o.taban_ref;
if(!pr||!r||typeof pr.puan!=='number'||r.duzey!==pr.ogrenim||(o.puan_turleri.length&&!o.puan_turleri.includes(pr.puan_turu)))return null;
const fark=pr.puan-r.medyan,med=r.medyan.toFixed(1).replace('.',','),p=E('p','sinyal'+(fark>=0?' iyi':''));
p.append(ic(fark>=0?'ok':'grafik'),E('span','d','Benzer kadro tabanı'),E('span','m','Taban'),' ~'+med+' · '+(fark>=0?'puanın üstünde':'puanından '+Math.abs(fark).toFixed(1).replace('.',',')+' yüksek'));return p;}
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
if(!v.karo||!o.logo)kurum.append(smallLogo(o));
kurum.append(E('span','ad',o.kurum||'Kurum belirtilmemiş'));
const h=E('h3'),a=detailLink(o,o.manset||'Kamu ilanı');if(o.ek)a.append(' ',E('span','ek','+'+o.ek));h.append(a);
govde.append(kurum,h,metaOf(o));const sg=sinyalOf(o);if(sg)govde.append(sg);
const sag=E('div','ilan-sag');sag.append(tarihOf(o),saveButton(o));
if(opt.kars){const l=E('label','kars'),c=E('input');c.type='checkbox';c.checked=compared.has(o.id);c.onchange=()=>{if(c.checked&&compared.size>=3){c.checked=false;notify('En fazla 3 ilan karşılaştırabilirsin.');return;}c.checked?compared.add(o.id):compared.delete(o.id);renderCompare();};l.append(c,'Karşılaştır');sag.append(l);}
n.append(v.node,govde,sag);return n;}
const listeEl=(rows,opt)=>{const d=E('div','liste');d.append(...rows.map(o=>rowEl(o,opt)));return d;};
function bosKutu(...nodes){const d=E('div','bos');d.append(...nodes);return d;}
function sectionEl(id,o){const s=E('section','bolum');s.id=id;const bas=E('div','bolum-bas'),k=E('div'),h=E('h2');if(o.nokta)h.append(E('span','nokta'+(o.nokta==='acil'?' acil':'')));h.append(o.baslik);if(o.sayi!==undefined)h.append(E('span','sayi',String(o.sayi)));k.append(h);if(o.alt)k.append(E('p','',o.alt));bas.append(k);if(o.link)bas.append(o.link);s.append(bas,o.govde);return s;}
function linkTo(text,hash){const a=E('a','yazi-link',text+' ');a.href=hash;a.append(ic('sag'));return a;}
/* ---------- profil ---------- */
function validProfile(p){
if(!p||typeof p!=='object'||p.v!==1)return null;
const t=typeof p.t==='string'&&DATE_RE.test(p.t)?p.t:today();
if(p.atlandi===true)return{v:1,atlandi:true,t};
if(!LEVELS[p.ogrenim])return null;
const o={v:1,ogrenim:p.ogrenim,puan_turu:typeof p.puan_turu==='string'&&PT_RE.test(p.puan_turu)?p.puan_turu:defaultTur(p.ogrenim),iller:(Array.isArray(p.iller)?p.iller:[]).filter(x=>IL_LIST.includes(x)).slice(0,81),tum_turkiye:p.tum_turkiye===true,bolum:str(p.bolum,60),t};
if(typeof p.puan==='number'&&p.puan>0&&p.puan<=100)o.puan=p.puan;return o;}
function defaultTur(o){return o==='onlisans'?'P93':o==='ortaogretim'?'P94':'P3';}
const ilKeys=o=>(o.iller&&o.iller.length?o.iller:[String(o.il||'').replace(/\s*\+\d+$/,'')]).map(normalize);
function uygun(o,p){if(o.ogrenim.length&&!o.ogrenim.includes(p.ogrenim))return false;return p.tum_turkiye||p.iller.some(x=>ilKeys(o).includes(normalize(x)));}
const sayiTr=n=>Number(n).toLocaleString('tr-TR');
function profilStrip(cls){
const p=profil,d=E('div','profil'+(cls?' '+cls:'')),ik=E('span','profil-ikon');ik.innerHTML=IC.kisi;
const y=E('div','profil-yazi');y.append(E('b','','PROFİLİN'));
y.append(E('span','',LEVELS[p.ogrenim]+(typeof p.puan==='number'?' · KPSS '+p.puan_turu+' '+p.puan.toFixed(2).replace('.',','):'')));
const alt=[p.tum_turkiye?'Tüm Türkiye':p.iller.join(', '),p.bolum].filter(Boolean).join(' · ');if(alt)y.append(E('small','',alt));
const b=E('button','duzenle');b.type='button';b.setAttribute('aria-label','Profili düzenle');b.innerHTML=IC.kalem+(cls==='m-only'?'<span>Düzenle</span>':'');b.onclick=openProfile;d.append(ik,y,b);return d;}
function kurulumCard(){
const p=profil;
if(p&&p.atlandi&&Date.now()-Date.parse(p.t+'T12:00:00Z')<14*864e5){const d=E('p','kurulum-ince','Sana göre ayarlamak ister misin? '),b=E('button','','Profilini ayarla');b.type='button';b.onclick=openProfile;d.append(b);return d;}
const d=E('div','kurulum'),ik=E('span','profil-ikon'),t=E('div'),b=E('button','btn btn-ana','Başla');ik.innerHTML=IC.kisi;t.append(E('b','','30 saniyede sana göre ayarla'),E('span','','Öğrenim düzeyini ve illerini seç; sana uygun ilanlar en üstte görünsün.'));b.type='button';b.onclick=openProfile;d.append(ik,t,b);return d;}
/* ---------- Bugün ---------- */
function bugunModel(){
const p=profil&&!profil.atlandi?profil:null,acik=liste.filter(o=>!closed(o)),byDl=(a,b)=>(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999')||a.kurum.localeCompare(b.kurum,'tr');
const senin=p?acik.filter(o=>uygun(o,p)).sort((a,b)=>Number(isNew(b))-Number(isNew(a))||byDl(a,b)):[];
const acil=acik.filter(o=>o.son_tarih&&!upcoming(o)&&days(o.son_tarih)<=2).sort(byDl);
const yeni=acik.filter(isNew).sort((a,b)=>Date.parse(b.ilk_gorulme)-Date.parse(a.ilk_gorulme));
const yakinda=acik.filter(upcoming).sort((a,b)=>Date.parse(a.baslangic_zaman)-Date.parse(b.baslangic_zaman));
const bugunYeni=acik.filter(o=>o.ilk_gorulme&&istDate(o.ilk_gorulme)===today());
return{p,acik,senin,acil,yeni,yakinda,bugunYeni};}
function h1Of(m){
const h=E('h1'),n=m.bugunYeni.length,b=m.acil.filter(o=>days(o.son_tarih)<=0).length,y=m.acil.filter(o=>days(o.son_tarih)===1).length;
const dow=new Date().toLocaleDateString('en-US',{weekday:'short',timeZone:'Europe/Istanbul'}),hs=dow==='Sat'||dow==='Sun';
const son=b>0?b+' ilanın son günü':y>0?y+' ilanın son günü yarın':'';
if(n>0)h.append('Bugün ',E('mark','',n+' yeni ilan'),' var'+(son?', '+son:'')+'.');
else h.append((hs?'Hafta sonu sakin: yeni ilan yok':'Bugün yeni ilan yok')+(son?'; '+son:'; açık ilanlar aşağıda')+'.');
return h;}
function ozetOf(m){
const parts=[];
if(sonZiyaret){const d=istDate(sonZiyaret),yn=m.yeni.length;if(yn){let s=uzunTarih(d)+'’deki ziyaretinden beri '+yn+' ilan eklendi';if(m.p)s+=', '+ekSi(m.yeni.filter(o=>uygun(o,m.p)).length)+' profiline uygun';parts.push(s+'.');}}
const k=m.acik.filter(o=>saved.has(o.id));
if(k.length){const a=k.filter(o=>o.son_tarih&&!upcoming(o)&&days(o.son_tarih)<=2).length;if(a)parts.push('Kaydettiğin '+k.length+' ilandan '+ekSi(a)+' 2 gün içinde kapanıyor.');}
return parts.join(' ');}
function railKayitli(m){
const k=m.acik.filter(o=>saved.has(o.id)).sort((a,b)=>(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999')).slice(0,5),box=E('section','kutu'),h=E('h3');h.append(ic('kayit'),'Kaydettiklerin');box.append(h);
if(!k.length){box.append(E('p','','Bir ilanı kaydetmek için yer imi simgesine dokun; son tarihi yaklaşınca burada hatırlatırız.'));return box;}
box.append(E('p','','Son tarihi yaklaşınca burada ve Telegram’da hatırlatırız.'));
const ul=E('ul','mini');for(const o of k){const li=E('li'),d=E('div'),a=detailLink(o,o.manset),g=o.son_tarih?days(o.son_tarih):null,em=E('em',g!==null&&g<=1?'acil':'',g===null?'—':g<=0?'Bugün son gün':g===1?'Yarın son gün':g+' gün');d.append(a,E('small','',o.kurum));li.append(d,em);ul.append(li);}
box.append(ul);return box;}
function railTelegram(){
const b=E('section','kutu tg-kutu'),s=E('span','tg-saat'),a=E('a','btn btn-lime');s.append(ic('saat'),'Her sabah 09:00');
a.href='https://t.me/kamuilantakip';a.target='_blank';a.rel='noopener';a.append(ic('tg'),'Kanala katıl');
b.append(s,E('h3','','Günün özeti Telegram’da'),E('p','','Yeni ilanlar ve son günler tek mesajda. Mesajdaki bağlantı seni doğrudan bu sayfaya getirir.'),a);return b;}
function arac(href,icon,t,s){const a=E('a','arac'),i=E('i'),d=E('span');a.href=href;i.innerHTML=IC[icon];d.append(E('b','',t),E('small','',s));a.append(i,d);return a;}
function railAraclar(){const b=E('section','kutu');b.append(E('h3','','Araçlar'),arac('puanlar/','grafik','Taban puanları ve tercih robotu','2022–2026 KPSS yerleştirme verisi'),arac('#rehber','kitap','Başvuru rehberi','İlan okuma, belge listesi, son kontrol'));return b;}
const adBox={sidebar:E('div'),feed:$('ad-feed')};adBox.sidebar.hidden=true;
function renderBugun(){
const root=$('bugun');if(!root)return;
if(!listeLoaded&&!loaded){return;}
const m=bugunModel(),p=m.p,gosterilen=new Set(),take=(arr,n)=>{const r=arr.filter(o=>!gosterilen.has(o.key)).slice(0,n);r.forEach(o=>gosterilen.add(o.key));return r;};
const bas=E('section','k1-bas'),us=E('div','ust-satir'),c=E('span','canli');
us.append(E('span','',new Date().toLocaleDateString('tr-TR',{day:'numeric',month:'long',weekday:'long',timeZone:'Europe/Istanbul'}).toLocaleUpperCase('tr-TR')));
const eski=listeZaman&&Date.now()-Date.parse(listeZaman)>864e5;
if(listeZaman&&!eski){c.append(E('span','nokta'),'Son kontrol '+trTime(listeZaman));us.append(c);}
bas.append(us,h1Of(m));const oz=ozetOf(m);if(oz)bas.append(E('p','ozet',oz));
if(eski)bas.append(E('p','tazelik','Veriler en son '+uzunTarih(istDate(listeZaman))+' '+trTime(listeZaman)+'’de güncellendi.'));
if(p)bas.append(profilStrip('m-only'));else bas.append(kurulumCard());
const main=E('div'),secs=[];
let senin=[];
if(p){senin=take(m.senin,5);
secs.push(['senin','Senin için',m.senin.length,sectionEl('senin',{baslik:'Senin için',sayi:m.senin.length,alt:LEVELS[p.ogrenim]+' düzeyi · '+(p.tum_turkiye?'tüm Türkiye':p.iller.join(', ')||'il seçilmedi')+'. Yeniler önce.',link:m.senin.length>senin.length?linkTo('Tümü','#ilanlar'):null,govde:senin.length?listeEl(senin,{yeni:true}):bosKutu(E('p','','Bugün profiline uyan açık ilan yok. Bu normal; yeni ilan gelince burada ve Telegram’da görürsün.'),(()=>{const b=E('button','btn btn-ikinci','İl ekle');b.type='button';b.onclick=openProfile;return b;})(),(()=>{const a=E('a','btn btn-ikinci','Tüm ilanlara bak');a.href='#ilanlar';return a;})())})]);}
else{const bz=take(m.bugunYeni,5);if(bz.length)secs.push(['bugunyeni','Bugün eklenenler',m.bugunYeni.length,sectionEl('bugunyeni',{nokta:'yeni',baslik:'Bugün eklenenler',sayi:m.bugunYeni.length,alt:'Bugün listeye giren ilanlar.',govde:listeEl(bz,{yeni:true})})]);}
const acil=take(m.acil,6);
if(m.acil.length){const alt=E('div','liste-alt');const a=E('a','yazi-link','Tüm son günler ('+m.acil.length+') ');a.href='#ilanlar';a.onclick=e=>{e.preventDefault();location.hash='ilanlar';$('deadline').value='2';render();};a.append(ic('sag'));alt.append(a);const l=listeEl(acil,{yeni:true});l.append(alt);
secs.push(['songun','Son günler',m.acil.length,sectionEl('songun',{nokta:'acil',baslik:'Son günü yaklaşanlar',sayi:m.acil.length,alt:'Bugün ve önümüzdeki iki gün içinde kapanan ilanlar.',govde:acil.length?l:bosKutu(E('p','','Bu ilanlar yukarıda gösterildi.'))})]);}
const yeniler=take(m.yeni,20);
{const g=E('div','liste');if(yeniler.length){const gr=new Map();for(const o of yeniler){const d=istDate(o.ilk_gorulme);if(!gr.has(d))gr.set(d,[]);gr.get(d).push(o);}for(const [d,l] of gr){const fark=Math.round((Date.parse(d+'T00:00:00Z')-Date.parse(today()+'T00:00:00Z'))/864e5),on=fark===0?'Bugün · ':fark===-1?'Dün · ':'';g.append(E('div','alt-baslik',on+uzunTarih(d)+' '+gunAdi(d)),...l.map(o=>rowEl(o)));}}
else g.append(bosKutu(E('p','',(sonZiyaret?'Son ziyaretinden beri':'Son iki günde')+' yeni ilan yok.'+(listeZaman?' Son kontrol '+trTime(listeZaman)+'.':''))));
if(yeniler.length||!m.yeni.length)secs.push(['yeni','Yeni',m.yeni.length,sectionEl('yeni',{nokta:'yeni',baslik:sonZiyaret?'Son ziyaretinden beri yeni':'Son iki günde eklenenler',sayi:m.yeni.length,alt:(sonZiyaret?'Son ziyaretin '+uzunTarih(istDate(sonZiyaret))+' '+gunAdi(istDate(sonZiyaret))+', '+trTime(sonZiyaret)+' · ':'')+'yukarıda gösterilenler tekrar edilmez',govde:g})]);}
const yk=take(m.yakinda,4);
if(yk.length)secs.push(['yakinda','Yakında açılacak',m.yakinda.length,sectionEl('yakinda',{baslik:'Yakında başvurusu açılacak',sayi:m.yakinda.length,alt:'Belgelerini şimdiden hazırlayabilirsin.',link:linkTo('Tümü','#ilanlar'),govde:listeEl(yk)})]);
const kadro=m.acik.reduce((s,o)=>s+(o.toplam||0),0),tumu=E('a','tumu'),tt=E('span'),ti=E('i');tumu.href='#ilanlar';tt.append(E('b','','Tüm açık ilanlar'),E('span','',m.acik.length+' ilan'+(kadro?' · '+sayiTr(kadro)+' kadro':'')+' · aramak ve filtrelemek için'));ti.innerHTML=IC.sag;tumu.append(tt,ti);
const atla=E('nav','atla');atla.setAttribute('aria-label','Bu sayfada git');
const chip=(label,n,id,acilNokta)=>{const b=E('button');b.type='button';if(acilNokta)b.append(E('span','nokta acil'));b.append(label+' ',E('b','',String(n)));b.onclick=()=>{const t=document.getElementById(id);if(t)t.scrollIntoView({behavior:'smooth'});};return b;};
if(p)atla.append(chip('Senin için',m.senin.length,'senin'));
else if(secs.some(s=>s[0]==='bugunyeni'))atla.append(chip('Bugün eklenenler',m.bugunYeni.length,'bugunyeni'));
if(m.acil.length)atla.append(chip('Son günler',m.acil.length,'songun',true));
if(secs.some(s=>s[0]==='yeni'))atla.append(chip('Yeni',m.yeni.length,'yeni'));
if(m.yakinda.length)atla.append(chip('Yakında açılacak',m.yakinda.length,'yakinda'));
const tum=E('a');tum.href='#ilanlar';tum.append('Tüm ilanlar ',E('b','',String(m.acik.length)));atla.append(tum);
bas.append(atla);
for(const s of secs)main.append(s[3]);main.append(tumu,adBox.feed);
const rail=E('aside','k1-yan');if(p)rail.append(profilStrip(''));rail.append(railKayitli(m),railTelegram(),railAraclar(),adBox.sidebar);
const gr=E('div','k1-izgara');gr.append(main,rail);
root.replaceChildren(bas,gr);}
/* ---------- İlanlar ---------- */
function resetFilters(){for(const id of ['search','city','type','level','deadline'])$(id).value='';$('recent').checked=false;$('sort').value='deadline';shown=PAGE_SIZE;render();}
function selectView(v){view=v;shown=PAGE_SIZE;render();}
function renderCompare(){$('compare-bar').hidden=!compared.size;$('compare-count').textContent=compared.size+' / 3 ilan seçildi';$('compare-open').disabled=compared.size<2;}
function filtered(){
const q=normalize($('search').value).trim().split(/\s+/).filter(Boolean),city=$('city').value,type=$('type').value,level=$('level').value,limit=Number($('deadline').value);
const result=items.filter(i=>view==='all'||(!closed(i)&&!i.duyuru_turu&&!i.iptal_edildi)).filter(i=>(!city||i.location===city)&&(!type||i.ilan_turu===type)&&(!level||(i.ogrenim||[]).includes(level)||i.kategori===level)&&(!limit||(knownActive(i)&&days(i.son_tarih)<=limit))&&(!$('recent').checked||(Date.now()-Date.parse(i.ilk_gorulme)>=0&&Date.now()-Date.parse(i.ilk_gorulme)<172800000))&&q.every(w=>i.search.includes(w)));
result.sort((a,b)=>$('sort').value==='new'?(Date.parse(b.ilk_gorulme)||0)-(Date.parse(a.ilk_gorulme)||0):$('sort').value==='institution'?String(a.kurum||'').localeCompare(b.kurum||'','tr'):Number(closed(a))-Number(closed(b))||(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999'));
return result;}
function renderIlanlar(){
if(!loaded)return;
const result=filtered(),vis=result.slice(0,shown);
$('cards').replaceChildren(...vis.map(i=>rowEl(rowOf(i),{yeni:true,kars:true})));
document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('secili',b.dataset.view===view);b.setAttribute('aria-pressed',String(b.dataset.view===view));});
$('result-count').textContent=result.length+' ilan'+(result.length>vis.length?' · '+vis.length+' gösteriliyor':'');
$('filter-summary').textContent=view==='active'&&breakdown(result)?'· '+breakdown(result):result.some(i=>!i.son_tarih)?'· Tarihi belirsiz ilanlar ayrıca işaretlenir':'';
$('cards').hidden=!result.length;$('empty').hidden=!!result.length;
if(!result.length){const b=E('button','btn btn-ikinci','Filtreleri temizle');b.onclick=resetFilters;const q=$('search').value.trim();$('empty').replaceChildren(E('h3','',q?'“'+q.slice(0,60)+'” için açık ilan bulunamadı.':'Bu aramada ilan bulunamadı.'),E('p','','Yazımı kontrol et, görev yeri filtresini kaldır veya arşivi de göster.'),b);}
const pg=$('pagination');pg.replaceChildren();pg.hidden=result.length<=vis.length;
if(result.length>vis.length){const b=E('button','btn btn-ikinci','Daha fazla göster ('+(result.length-vis.length)+')');b.onclick=()=>{shown+=PAGE_SIZE;renderIlanlar();};pg.append(b);}
renderCompare();}
/* ---------- Takvim ve Kayıtlı ---------- */
function renderTakvim(){
const box=$('takvim-icerik');if(!box)return;
const rows=liste.filter(o=>o.son_tarih&&!closed(o)).sort((a,b)=>a.son_tarih.localeCompare(b.son_tarih)||a.kurum.localeCompare(b.kurum,'tr')),gr=new Map();
for(const o of rows){if(!gr.has(o.son_tarih))gr.set(o.son_tarih,[]);gr.get(o.son_tarih).push(o);}
const out=[];let n=0;
for(const [d,l] of gr){if(n++>=takvimGun)break;const g=days(d),sec=E('section','bolum'),bas=E('div','bolum-bas'),k=E('div'),h=E('h2','',kisaTarih(d)+' · '+gunAdi(d)+(g<=0?' · Bugün':g===1?' · Yarın':''));if(g<=2)h.prepend(E('span','nokta acil'));const kadro=l.reduce((s,o)=>s+(o.toplam||0),0);k.append(h,E('p','',l.length+' ilan'+(kadro?' · '+sayiTr(kadro)+' kadro':'')+' · bu gün kapanıyor'));bas.append(k);sec.append(bas,listeEl(l));out.push(sec);}
if(!out.length)out.push(E('p','not','Tarihi belli açık ilan bulunmuyor.'));
if(gr.size>takvimGun){const b=E('button','btn btn-ikinci','Daha fazla gün göster');b.type='button';b.onclick=()=>{takvimGun+=7;renderTakvim();};const w=E('div','daha');w.append(b);out.push(w);}
const tarihsiz=liste.filter(o=>!o.son_tarih&&!closed(o)).length;if(tarihsiz)out.push(E('p','not',tarihsiz+' ilanın son başvuru tarihi resmî ilanda belirtilir.'));
box.replaceChildren(...out);}
function renderKayitli(){
const box=$('kayitli-icerik');if(!box)return;
const by=new Map(liste.map(o=>[o.id,o]));for(const i of items)by.set(i.id,rowOf(i));
const rows=[...saved].map(id=>by.get(id)).filter(Boolean);
if(!rows.length){box.replaceChildren(bosKutu(E('p','','Bir ilanı kaydetmek için yer imi simgesine dokun; son tarihi yaklaşınca Bugün sayfasında hatırlatırız.'),(()=>{const a=E('a','btn btn-ana','İlanlara bak');a.href='#ilanlar';return a;})()));return;}
const grp=[['Bu hafta kapanıyor',o=>!closed(o)&&o.son_tarih&&days(o.son_tarih)<=7],['Daha sonra',o=>!closed(o)&&!(o.son_tarih&&days(o.son_tarih)<=7)],['Sona erdi',o=>closed(o)]],out=[];
for(const [t,f] of grp){const l=rows.filter(f).sort((a,b)=>(a.son_tarih||'9999').localeCompare(b.son_tarih||'9999'));if(!l.length)continue;out.push(sectionEl('k-'+out.length,{baslik:t,sayi:l.length,govde:listeEl(l,{kars:true})}));}
box.replaceChildren(...out);}
function render(){
if(!loaded&&!listeLoaded)return;
const n=saved.size;for(const id of ['saved-count','saved-count-m']){const e=$(id);if(e){e.textContent=n;e.hidden=!n;}}
if(tab==='bugun')renderBugun();else if(tab==='ilanlar')renderIlanlar();else if(tab==='takvim')renderTakvim();else if(tab==='kayitli')renderKayitli();
renderCompare();}
/* ---------- gezinme ---------- */
function showTab(t){
tab=t;lastTab=t;
for(const x of TABS){const v=$('v-'+x);if(v)v.hidden=x!==t;}
document.querySelectorAll('[data-tab]').forEach(a=>{const on=a.dataset.tab===t;a.classList.toggle('aktif',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute&&a.removeAttribute('aria-current');});
render();}
function closeModal(){if($('modal').open)$('modal').close();document.title=defaultTitle;}
function route(){
const hash=location.hash.slice(1);
$('modal-back').href='#'+lastTab;
if(hash.startsWith('ilan/')){if(!loaded)return;let k;try{k=decodeURIComponent(hash.slice(5));}catch{k='';}const i=items.find(x=>x.key===k);if(i)showDetail(i);else{const h=E('h2','','Bu ilan artık listede bulunmuyor.');h.id='modal-title';$('modal-body').replaceChildren(h,E('p','','Güncel ilanları keşfedebilir veya resmî kaynağı kontrol edebilirsin.'),external('https://kariyerkapisi.gov.tr/isealim','Kariyer Kapısı ↗'));openModal();}}
else if(articles[hash])showArticle(hash);
else if(hash==='karsilastir')showComparison();
else{closeModal();showTab(TABS.includes(hash)?hash:'bugun');}}
function goTab(t){location.hash=t;}
/* ---------- profil penceresi ---------- */
let draft=null;
function fillForm(){
const d=draft,seg=$('p-ogrenim');seg.querySelectorAll('button').forEach(b=>{b.classList.toggle('secili',b.dataset.v===d.ogrenim);b.setAttribute('aria-pressed',String(b.dataset.v===d.ogrenim));});
const sel=$('p-tur');sel.replaceChildren();for(const t of [...Array.from({length:48},(_,k)=>'P'+(k+1)),'P93','P94']){const o=E('option','',t);o.value=t;sel.append(o);}sel.value=d.puan_turu||defaultTur(d.ogrenim);
$('p-puan').value=typeof d.puan==='number'?String(d.puan).replace('.',','):'';
$('p-tum').checked=!!d.tum_turkiye;$('p-bolum').value=d.bolum||'';$('p-il').value='';renderIller();}
function renderIller(){const box=$('p-iller');box.replaceChildren(...draft.iller.map(il=>{const c=E('span','il-cip',il),b=E('button');b.type='button';b.setAttribute('aria-label',il+' ilini kaldır');b.innerHTML=IC.x;b.onclick=()=>{draft.iller=draft.iller.filter(x=>x!==il);renderIller();};c.append(b);return c;}));}
function addIl(){const v=normalize($('p-il').value).trim();if(!v)return true;const il=IL_LIST.find(x=>normalize(x)===v);if(!il){notify('İl adını listeden seç.');return false;}if(!draft.iller.includes(il))draft.iller.push(il);$('p-il').value='';renderIller();return true;}
function openProfile(){draft=profil&&!profil.atlandi?{...profil,iller:[...profil.iller]}:{ogrenim:'',puan_turu:'',iller:[],tum_turkiye:false,bolum:''};fillForm();if(!$('profil-dialog').open)$('profil-dialog').showModal();}
function saveProfile(){
if(!draft.ogrenim){notify('Önce öğrenim düzeyini seç.');return;}
if(!addIl())return;
const raw=$('p-puan').value.trim().replace(',','.'),puan=raw===''?null:Number(raw);
if(puan!==null&&!(puan>0&&puan<=100)){notify('Puanı 0–100 arasında gir (örn. 82,15).');return;}
const p={v:1,ogrenim:draft.ogrenim,puan_turu:$('p-tur').value,iller:draft.iller,tum_turkiye:$('p-tum').checked,bolum:$('p-bolum').value.trim().slice(0,60),t:today()};if(puan!==null)p.puan=Math.round(puan*100)/100;
profil=validProfile(p);writeStore('kit-profil',profil);$('profil-dialog').close();render();notify('Profilin kaydedildi.');}
function skipProfile(){profil={v:1,atlandi:true,t:today()};writeStore('kit-profil',profil);$('profil-dialog').close();render();}
function initProfile(){
const dl=$('il-listesi');IL_LIST.forEach(il=>{const o=E('option');o.value=il;dl.append(o);});
$('p-ogrenim').querySelectorAll('button').forEach(b=>b.onclick=()=>{const prev=draft.ogrenim;draft.ogrenim=b.dataset.v;if(!prev||$('p-tur').value===defaultTur(prev))$('p-tur').value=defaultTur(draft.ogrenim);$('p-ogrenim').querySelectorAll('button').forEach(x=>{x.classList.toggle('secili',x===b);x.setAttribute('aria-pressed',String(x===b));});});
$('p-il-ekle').onclick=addIl;$('p-il').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();addIl();}};
$('profil-form').onsubmit=e=>{e.preventDefault();saveProfile();};$('p-atla').onclick=skipProfile;$('nav-profile').onclick=openProfile;
$('profil-dialog').addEventListener('click',e=>{if(e.target===$('profil-dialog')){const r=$('profil-dialog').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('profil-dialog').close();}});}
/* ---------- tema, yükleme ---------- */
function applyTheme(){document.documentElement.dataset.theme=readStore('kit-theme',null)==='dark'?'dark':'light';}
async function loadSponsors(){try{const r=await fetch('sponsors.json',{cache:'no-store'});if(!r.ok)return;const cfg=await r.json();if(!cfg.enabled)return;for(const placement of ['sidebar','feed']){const s=cfg[placement],url=s&&safeURL(s.url);if(!s||!url||!s.title)continue;const box=E('aside','sponsor');box.setAttribute('aria-label','Reklam');box.append(E('span','eyebrow','REKLAM · SPONSORLU'));const a=external(url,s.title,'');a.rel='sponsored noopener noreferrer';box.append(a,E('p','',s.description||''));adBox[placement].replaceChildren(box);adBox[placement].hidden=false;}}catch{/* Optional sponsorship cannot break listing discovery. */}}
async function getJSON(url,cache){const r=await fetch(url,{cache});if(!r.ok)throw Error(url);return r.json();}
async function load(){
const [lr,fr,gr]=await Promise.allSettled([getJSON('liste.json','no-cache'),getJSON('ilanlar.json','no-store'),getJSON('ilan/gorseller.json','no-cache')]);
let lmap=new Map();
if(lr.status==='fulfilled'&&lr.value&&Array.isArray(lr.value.ilanlar)){liste=lr.value.ilanlar.map(cleanL).filter(Boolean);listeVar=true;listeZaman=typeof lr.value.guncelleme==='string'&&!isNaN(Date.parse(lr.value.guncelleme))?lr.value.guncelleme:'';lmap=new Map(liste.map(o=>[o.key,o]));}
if(fr.status==='fulfilled'&&fr.value&&Array.isArray(fr.value.ilanlar)){
const data=fr.value,imgs=gr.status==='fulfilled'&&gr.value&&typeof gr.value==='object'?gr.value:{};
items=data.ilanlar.filter(i=>i&&typeof i.id==='string'&&typeof i.baslik==='string'&&i.kategori!=='akademik').map(i=>({...i,key:keyFor(i),location:proper(i.yer),...pickImages(imgs[keyFor(i)]),L:lmap.get(keyFor(i))||null,search:normalize([i.baslik,i.kurum,i.yer,i.kadro,i.ilan_turu,i.ozet,...(i.sartlar||[]).map(s=>s.kadro+' '+s.metin)].join(' '))}));
loaded=true;if(!listeZaman&&data.guncelleme)listeZaman=data.guncelleme;
if(!listeVar)liste=items.filter(i=>!i.duyuru_turu&&!i.iptal_edildi&&!closed(i)).map(fallbackModel);
const failed=Object.entries(data.kaynak_durumlari||{}).filter(([,s])=>s.hata_sayisi>0).map(([k])=>({sbb:'SBB',csb:'ÇŞB Yerel Yönetimler'})[k]||'İŞKUR');
if(failed.length){$('freshness').hidden=false;$('freshness').textContent=failed.join(' ve ')+' kaynağına erişimde sorun var; bu kaynağın ilanları güncel olmayabilir. Erişim sonraki taramada yeniden denenecek.';}
for(const [id,values] of [['city',items.map(i=>i.location).filter(Boolean)],['type',items.map(i=>i.ilan_turu).filter(Boolean)]])for(const v of [...new Set(values)].sort((a,b)=>a.localeCompare(b,'tr'))){const o=E('option','',v);o.value=v;$(id).append(o);}}
listeLoaded=listeVar||loaded;
if(!loaded)$('result-count').textContent='Ayrıntılı ilan verisi yüklenemedi; arama ve ayrıntı penceresi çalışmayabilir.';
if(!listeLoaded){$('bugun').replaceChildren(E('p','not','İlan listesi yüklenemedi. Biraz sonra yeniden dene veya resmî ilan sayfalarını ziyaret et.'),external('https://kariyerkapisi.gov.tr/isealim','Resmî ilanlar ↗','btn btn-ikinci'));$('result-count').textContent='İlan listesi yüklenemedi.';return;}
render();route();}
applyTheme();$('year').textContent=new Date().getFullYear();
profil=validProfile(readStore('kit-profil',null));
{const t=Date.parse(readStore('kit-son-ziyaret',null));sonZiyaret=isNaN(t)?null:t;}
try{const u=new URL(location.href);if(u.searchParams.has('g')){u.searchParams.delete('g');history.replaceState(null,'',u.pathname+u.search+u.hash);}}catch{}
$('theme').onclick=()=>{writeStore('kit-theme',document.documentElement.dataset.theme==='dark'?'light':'dark');applyTheme();};
$('search-form').onsubmit=e=>{e.preventDefault();shown=PAGE_SIZE;render();};
$('search').oninput=()=>{shown=PAGE_SIZE;render();};
for(const id of ['city','type','level','deadline','recent','sort'])$(id).onchange=()=>{shown=PAGE_SIZE;render();};
$('clear').onclick=resetFilters;
document.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>{resetFilters();$('search').value=b.dataset.query;view='active';render();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>selectView(b.dataset.view));
$('nav-saved').onclick=()=>goTab('kayitli');
$('nav-search').onclick=()=>{goTab('ilanlar');setTimeout(()=>$('search').focus(),50);};
const backToTab=()=>{location.hash=lastTab;};
$('modal-close').onclick=backToTab;$('modal').addEventListener('cancel',e=>{e.preventDefault();backToTab();});
$('modal').addEventListener('click',e=>{if(e.target===$('modal')){const r=$('modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)backToTab();}});
$('compare-clear').onclick=()=>{compared.clear();render();};$('compare-open').onclick=()=>{location.hash='karsilastir';};
initProfile();
window.addEventListener('hashchange',route);
setInterval(()=>{if(loaded||listeLoaded)render();},60000);
setTimeout(()=>writeStore('kit-son-ziyaret',new Date().toISOString()),10000);
showTab(TABS.includes(location.hash.slice(1))?location.hash.slice(1):'bugun');route();load();loadSponsors();
