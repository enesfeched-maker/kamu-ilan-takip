"""Refresh the exact-name logo directory from public official pages."""
import json,time,urllib.request,urllib.parse
from bs4 import BeautifulSoup
from kurum_gorseli import CATALOG,kurum_anahtari,logo_url

def read(url):
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'KamuIlanTakip/1.0'})
            with urllib.request.urlopen(req,timeout=20) as r:
                return BeautifulSoup(r.read(3_000_000),'html.parser')
        except OSError:
            if attempt==2:raise
            time.sleep(2+attempt)

def entries(doc,page):
    out={}
    for img in doc.select('img.agencyLogo'):
        row=img.find_parent('li')
        heading=row.find(['h2','h3','h4']) if row else None
        name=img.get('alt') or (heading.get_text(' ',strip=True) if heading else '')
        if not name:continue
        try:url=logo_url(urllib.parse.urljoin(page,img.get('src','')))
        except ValueError:continue
        out[kurum_anahtari(name)]={'kurum':name,'url':url,'kaynak':page}
    return out

def main():
    result=json.loads(CATALOG.read_text(encoding='utf-8')) if CATALOG.exists() else {}
    pages=['https://www.turkiye.gov.tr/universite-hizmet-listesi']
    pages+=['https://www.turkiye.gov.tr/kurumlar?'+urllib.parse.urlencode({'kurumHarf':ch}) for ch in 'ABCÇDEFGHİJKLMNOÖPRSŞTUÜVYZ']
    for page in pages:
        try:
            found=entries(read(page),page);result.update(found)
            print('Logo dizini:',len(found),'kurum',flush=True)
        except Exception as exc:print('Logo dizini atlandı:',type(exc).__name__,flush=True)
        time.sleep(.6)
    CATALOG.write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    print('Doğrulanmış kurum logoları:',len(result))

def municipalities():
    result={kurum_anahtari(v['kurum']):v for v in json.loads(CATALOG.read_text(encoding='utf-8')).values()}
    index='https://www.turkiye.gov.tr/belediyeler?bagli=isletmeler'
    options=read(index).select('select[name=belediyeUrl] option[value]')
    names={}
    for option in options:
        page=urllib.parse.urljoin(index,option['value'])
        if urllib.parse.urlsplit(page).hostname!='www.turkiye.gov.tr':continue
        city=option.get('data-name') or option.get_text(strip=True)
        try:
            found=entries(read(page),page)
            for key,value in found.items():
                value['il']=city
                names.setdefault(key,{})[value['url']]=value
                qualified=key if key.startswith(kurum_anahtari(city)+' ') else kurum_anahtari(city)+' '+key
                result[qualified]=value
            print('Belediye dizini:',city,len(found),flush=True)
        except OSError:print('Belediye dizini ertelendi:',city,flush=True)
        time.sleep(.7)
    for key,values in names.items():
        if len(values)==1:result[key]=next(iter(values.values()))
        elif key in result and result[key].get('il'):result.pop(key)
    CATALOG.write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    print('Toplam logo eşleşmesi:',len(result),flush=True)

if __name__=='__main__':main()
