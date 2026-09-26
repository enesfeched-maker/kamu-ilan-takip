"""Public SBB/İŞKUR listings. Store factual metadata and original links only."""
import hashlib
import html
import http.cookiejar
import io
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from bs4 import BeautifulSoup
from pypdf import PdfReader

TR = timezone(timedelta(hours=3))
SBB = 'https://kamuilan.sbb.gov.tr/'
ISKUR = 'https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/'
HOSTS = {'kamuilan.sbb.gov.tr', 'www.iskur.gov.tr', 'iskur.gov.tr', 'kariyerkapisi.gov.tr'}
MONTHS = ['ocak','şubat','mart','nisan','mayıs','haziran','temmuz','ağustos','eylül','ekim','kasım','aralık']


def now():
    return datetime.now(TR)


def norm(value):
    value = str(value or '').translate(str.maketrans('Iİ', 'ıi')).lower().replace('ı', 'i')
    return re.sub(r'[^a-z0-9 ]', ' ', ''.join(c for c in unicodedata.normalize('NFD', value) if not unicodedata.combining(c)))


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def identity(source, value):
    return source + '-' + hashlib.sha256(value.encode()).hexdigest()[:24]


def safe_url(value, base=''):
    value = urllib.parse.urljoin(base, html.unescape(value))
    p = urllib.parse.urlsplit(value)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password:
        raise ValueError('Resmi kaynak dışı bağlantı')
    return urllib.parse.urlunsplit((p.scheme,p.netloc,urllib.parse.quote(urllib.parse.unquote(p.path),safe='/'),p.query,''))


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl, req.full_url)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def session():
    return urllib.request.build_opener(OfficialRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(opener, url, referer=None):
    headers = {'User-Agent':'kamu-ilan-takip/1.0 (+https://enesfeched-maker.github.io/kamu-ilan-takip/)'}
    if referer:
        headers['Referer'] = referer
    request = urllib.request.Request(safe_url(url), headers=headers)
    with opener.open(request, timeout=25) as response:
        data = response.read(12_000_001)
        if len(data) > 12_000_000:
            raise ValueError('Kaynak dosya boyutu sınırı aşıldı')
        return data, safe_url(response.geturl())


def soup(data):
    return BeautifulSoup(data.decode('utf-8-sig') if isinstance(data,bytes) else data, 'html.parser')


def fresh(item):
    try:
        age = now() - datetime.fromisoformat(item['detay_guncelleme'])
        return timedelta(0) <= age < timedelta(hours=12)
    except (KeyError, ValueError, TypeError):
        return False


def kind(title):
    t = norm(title)
    for needle, label in [('ogretim uyes','Öğretim Üyesi'),('arastirma gorevl','Araştırma Görevlisi'),
                          ('ogretim eleman','Öğretim Elemanı'),('ogretim gorevl','Öğretim Görevlisi'),
                          ('pilot','Pilot'),('bilisim','Bilişim Personeli'),('uzman','Uzman'),
                          ('sozlesmeli','Sözleşmeli Personel'),('isci','İşçi'),('memur','Memur')]:
        if needle in t:
            return label
    return 'Kamu Personeli'


def notice(title):
    return any(w in norm(title) for w in ('iptal','duzeltme','sure uzatim'))


def total(item):
    text = item.get('kadro','')
    m = re.search(r'Toplam\s+(\d+)\s+kişi',text,re.I) or re.match(r'\s*(\d+)\s+',text)
    if not m:
        return None
    if ',' in text and 'Toplam' not in text and ' — ' not in text:
        values=re.findall(r'(\d+)\s+[A-ZÇĞİÖŞÜa-zçğıöşü]',text)
        return sum(map(int,values)) if values else None
    return int(m.group(1))


def institution(title):
    # Keep the actual named institution; never infer a workplace from its city name.
    m = re.match(r'(.+?\b(?:Belediye Başkanlığı|Belediyesi|Üniversitesi|Kurumu Başkanlığı|Kalkınma Ajansı|Kurumu|Birliği|Bakanlığı|Genel Müdürlüğü|Başkanlığı))\b',title,re.I)
    return clean(m.group(1)) if m else ''


def pdf_text(data):
    if not data.startswith(b'%PDF-'):
        raise ValueError('İlan bağlantısı PDF döndürmedi')
    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > 100:
        raise ValueError('PDF sayfa sınırı aşıldı')
    return clean(' '.join(p.extract_text() or '' for p in reader.pages))


def pdf_dates(text, range_text):
    """Match a listing's displayed end day/month to an explicit PDF date, never KPSS year."""
    dates = []
    for d,m,y in re.findall(r'(?<!\d)(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})(?!\d)',text):
        try:
            dates.append(date(int(y),int(m),int(d)))
        except ValueError:
            continue
    parts = re.findall(r'(\d{1,2})\s+('+'|'.join(MONTHS)+r')',range_text.lower())
    if len(parts) != 2:
        return {}
    start_day,start_month=int(parts[0][0]),MONTHS.index(parts[0][1])+1
    end_day,end_month=int(parts[1][0]),MONTHS.index(parts[1][1])+1
    candidates={d for d in dates if d.day==end_day and d.month==end_month and abs((d-now().date()).days)<370}
    # The start date also establishes the range year when the PDF says "15 days".
    if not candidates:
        starts={d for d in dates if d.day==start_day and d.month==start_month and abs((d-now().date()).days)<185}
        if len(starts)==1:
            start=next(iter(starts))
            candidates={date(start.year+(end_month<start_month),end_month,end_day)}
    if len(candidates)!=1:
        return {}
    end=next(iter(candidates))
    result={'son_tarih':end.isoformat()}
    start=date(end.year-(start_month>end_month),start_month,start_day)
    result['baslangic_zaman']=datetime.combine(start,datetime.min.time(),TR).isoformat()
    return result


def sbb_rows(data):
    doc=soup(data)
    root=doc.find(id='nav2')
    if root is None:
        raise ValueError('SBB aktif ilan listesi bulunamadı')
    rows=[]
    for a in root.select('a[href]'):
        if 'ilanDetay.aspx?' not in a.get('href',''):
            continue
        p1,p2=a.select_one('.alt_p1'),a.select_one('.alt_p2')
        if not p1 or not p2 or not p2.find('em'):
            raise ValueError('SBB ilan satırı değişti')
        period=clean(p2.find('em').get_text(' '))
        job=clean(p2.get_text(' ').replace(p2.find('em').get_text(' '),''))
        org=clean(p1.get_text(' '))
        key=identity('sbb',str(now().year)+'|'+org+'|'+job+'|'+period)
        rows.append({'id':key,'baslik':org+' - '+job,'kurum':org,'kadro':job,
            'ilan_turu':kind(job),'son_tarih':None,'kaynak':'SBB Kamu İlan',
            'kaynak_turu':'sbb','donem':period,'gecici_link':safe_url(a['href'],SBB)})
    if not rows:
        raise ValueError('SBB ilan listesi beklenmedik şekilde boş')
    return rows


def read_sbb(previous):
    op=session()
    data,_=get(op,SBB)
    records=[]
    errors=0
    cache={alias:i for i in previous.values() for alias in [i['id']]+i.get('kaynak_kimlikleri',[])}
    for row in sbb_rows(data):
        # Keep the same listing identity when a year boundary changes the hash salt.
        older=[i for i in previous.values() if i.get('kaynak_turu')=='sbb' and i.get('baslik')==row['baslik'] and i.get('donem')==row['donem'] and i.get('ilk_gorulme') and now()-datetime.fromisoformat(i['ilk_gorulme'])<timedelta(days=90)]
        if len(older)==1:
            row['id']=older[0]['id']
        cached=cache.get(row['id'])
        if cached and fresh(cached):
            cached=dict(cached)
            if cached.get('kaynak_turu')=='sbb':
                cached.update(link=SBB,kaynaklar=[{'ad':'SBB Kamu İlan','link':SBB}],
                    basvuru_notu='SBB sayfasındaki arama alanına kurum adını yazıp ilgili ilan belgesini açın.')
                if notice(cached['baslik']):
                    cached['duyuru_turu']='İptal duyurusu' if 'iptal' in norm(cached['baslik']) else 'Düzeltme / süre değişikliği'
            records.append(cached)
            continue
        try:
            data,url=get(op,row.pop('gecici_link'),SBB)
            text=pdf_text(data)
            row.update(pdf_dates(text,row['donem']))
            # SBB's PDF endpoint rejects navigation outside its own page/session.
            # Link to its working search page rather than publishing a broken PDF URL.
            row.update(link=SBB,detay_guncelleme=now().isoformat(timespec='seconds'),
                       belge_ozeti=hashlib.sha256(data).hexdigest())
            row['kaynaklar']=[{'ad':row['kaynak'],'link':SBB}]
            row['basvuru_notu']='SBB sayfasındaki arama alanına kurum adını yazıp ilgili ilan belgesini açın.'
            if notice(row['baslik']):
                row['duyuru_turu']='İptal duyurusu' if 'iptal' in norm(row['baslik']) else 'Düzeltme / süre değişikliği'
            # Do not republish the PDF text or source imagery.
            row['ozet']='Kadro ve başvuru koşulları için kaynağın ilan belgesini inceleyin.'
            records.append(row)
        except Exception as exc:
            errors+=1
            print(f'SBB belge kontrolü ertelendi ({type(exc).__name__}: {str(exc)[:100]}): {row["kurum"]}',flush=True)
            if cached:
                records.append(cached)
        time.sleep(.15)
    return records,errors


def iskur_cities(data):
    doc=soup(data)
    regions=doc.select('#svg-turkiye-haritasi g[data-iladi]')
    if len(regions)<70:
        raise ValueError('İŞKUR il haritası okunamadı')
    return [(g['id'],g['data-iladi']) for g in regions if str(g.get('data-count','')).isdigit() and int(g['data-count'])>0]


def iskur_rows(data, city):
    doc=soup(data)
    records=[]
    for tr in doc.select('tr.clickable-row'):
        td=tr.find_all('td')
        if len(td)<2 or tr.get('data-has-file')!='True':
            continue
        link=safe_url(tr.get('data-file-url',''),ISKUR)
        title=clean(td[1].get_text(' '))
        raw=clean(td[0].get_text(' '))
        match=re.match(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}',raw)
        if not match:
            raise ValueError('İŞKUR son tarih biçimi değişti')
        deadline=datetime.strptime(match.group(),'%d.%m.%Y %H:%M').replace(tzinfo=TR)
        org=institution(title)
        short=re.sub(r'\s*\d{1,2}[.]\d{1,2}[.]20\d{2}\s*$','',title)
        records.append({'id':identity('iskur',urllib.parse.unquote(link)),
            'baslik':short,'kurum':org,'yer':city,'ilan_turu':kind(title),
            'son_tarih':deadline.date().isoformat(),'son_zaman':deadline.isoformat(),
            'link':link,'kaynak':'İŞKUR','kaynak_turu':'iskur',
            'kaynaklar':[{'ad':'İŞKUR','link':link}],
            'detay_guncelleme':now().isoformat(timespec='seconds')})
    if not records and not doc.select('tr.clickable-row'):
        raise ValueError('İŞKUR il ilan tablosu boş veya okunamadı')
    return records


def read_iskur(previous):
    op=session()
    data,_=get(op,ISKUR)
    records=[]
    errors=0
    for ident,city in iskur_cities(data):
        try:
            url=ISKUR+'?'+urllib.parse.urlencode({'idId':ident,'il':city})
            data,_=get(op,url)
            records.extend(iskur_rows(data,city))
        except Exception as exc:
            errors+=1
            print(f'İŞKUR il kontrolü ertelendi ({type(exc).__name__}: {str(exc)[:100]}): {city}',flush=True)
            records.extend(i for i in previous.values() if i.get('kaynak_turu')=='iskur' and i.get('yer')==city)
        time.sleep(.2)
    return records,errors


def same_listing(a,b):
    if a['id']==b['id'] or a.get('link') and a.get('link')==b.get('link') and urllib.parse.urlsplit(a['link']).path not in ('','/'):
        return True
    if a.get('belge_ozeti') and a.get('belge_ozeti')==b.get('belge_ozeti'):
        return True
    if notice(a['baslik']) or notice(b['baslik']):
        return False
    if a.get('kaynak_turu','kariyer')==b.get('kaynak_turu','kariyer'):
        return False
    if not a.get('son_tarih') or a.get('son_tarih')!=b.get('son_tarih'):
        return False
    def org(i):
        t=norm(i.get('kurum'))
        t=re.sub(r'\b(rektorlugu|baskanligi)\b','',t)
        t=re.sub(r'\bbelediyesi\b','belediye',t)
        return clean(t)
    x,y=org(a),org(b)
    if not x or not y or not (x==y or x.endswith(' '+y) or y.endswith(' '+x)):
        return False
    # Distinct positions at the same institution/date must not disappear.
    compatible_kind=kind(a.get('ilan_turu','')+' '+a['baslik'])==kind(b.get('ilan_turu','')+' '+b['baslik'])
    count_matches=total(a) is not None and total(a)==total(b)
    iskur_missing_count=(a.get('kaynak_turu')=='iskur' or b.get('kaynak_turu')=='iskur') and (total(a) is None or total(b) is None)
    return compatible_kind and (count_matches or iskur_missing_count)


def merge_sources(records, previous):
    """Keep an existing public ID and sent history; attach alternative source references."""
    result={}
    for item in records:
        exact=previous.get(item['id'])
        matches=[old for old in previous.values() if same_listing(item,old)]
        if not matches:
            matches=[old for old in result.values() if same_listing(item,old)]
        rank=lambda obj: {'sbb':2,'iskur':1}.get(obj.get('kaynak_turu'),0)
        best=min([rank(item)]+[rank(obj) for obj in matches])
        preferred=[obj for obj in matches if rank(obj)==best and best<rank(item)]
        chosen=preferred[0] if len(preferred)==1 else exact or (matches[0] if len(matches)==1 else item)
        ident=chosen['id']
        if ident==item['id']:
            merged={**chosen,**item}
        else:
            merged={**result.get(ident,chosen)}
        prior=result.get(ident,{})
        refs={s['link']:s for obj in (chosen,prior,item) for s in obj.get('kaynaklar',[{'ad':obj.get('kaynak','Kariyer Kapısı'),'link':obj.get('link','')}]) if s.get('link')}
        merged['kaynaklar']=list(refs.values())
        merged['kaynak_kimlikleri']=sorted(set(chosen.get('kaynak_kimlikleri',[])+prior.get('kaynak_kimlikleri',[])+item.get('kaynak_kimlikleri',[])+[item['id'],ident]))
        result[ident]=merged
    return list(result.values())
