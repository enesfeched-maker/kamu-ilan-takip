"""Build a reusable library from verified official logos; never upscale artwork."""
import concurrent.futures
import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path
from PIL import Image
from kurum_gorseli import CATALOG,LIBRARY,kurum_anahtari

ROOT=Path(__file__).resolve().parents[1]
ALIASES={
 'subasi yalova belediye':'yalova subasi belediye',
 'bahce osmaniye belediye':'osmaniye bahce belediye',
 'sorgun yozgat belediye':'yozgat sorgun belediye',
 'cumhurbaskanligi iletisim':'iletisim',
 'goc idaresi genel mudurlugu':'goc idaresi',
 'istanbul bankacilik duzenleme ve denetleme kurumu':'bankacilik duzenleme ve denetleme kurumu',
 'bankacilik duzenleme ve denetleme kurumu bddk':'bankacilik duzenleme ve denetleme kurumu',
 'sigortacilik ve ozel emeklilik duzenleme ve denetleme kurumu seddk':'sigortacilik ve ozel emeklilik duzenleme ve denetleme kurumu',
 'dogu marmara kalkinma ajansi marka':'dogu marmara kalkinma ajansi',
 'turkiye uluslararasi islam bilim ve teknoloji universitesi tibu':'turkiye uluslararasi islam bilim ve teknoloji universitesi',
}

def png256(url):
    if url and url.startswith('https://cdn.e-devlet.gov.tr/themes/ankara/images/logos/'):
        return re.sub(r'/(?:64|128)(?:webp|px)/([^/]+)\.(?:webp|png)$',r'/256px/\1.png',url)
    return url

def download(url):
    request=urllib.request.Request(url,headers={'User-Agent':'KamuIlanTakip/1.0'})
    with urllib.request.urlopen(request,timeout=18) as response:
        raw=response.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError('large image')
    with Image.open(io.BytesIO(raw)) as im:
        im.verify()
    with Image.open(io.BytesIO(raw)) as im:
        if im.width*im.height>25_000_000:raise ValueError('large dimensions')
        return raw,im.size,im.format.lower().replace('jpeg','jpg')

def main():
    institutions=json.loads((ROOT/'local-data/logo-kurumlar.json').read_text(encoding='utf-8'))
    catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
    manifest=json.loads((LIBRARY/'kaynaklar.json').read_text(encoding='utf-8'))
    candidates={}
    for key,info in institutions.items():
        canonical=ALIASES.get(key,key)
        if key in manifest or canonical in manifest:
            candidates[key]=[];continue
        entry=catalog.get(canonical,{})
        candidates[key]=list(dict.fromkeys(u for u in [png256(entry.get('url')),png256(info.get('url')),info.get('url'),entry.get('url')] if u))
    urls=list(dict.fromkeys(u for values in candidates.values() for u in values))
    results={}
    def safe(url):
        try:return url,download(url)
        except Exception:return url,None
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for index,(url,result) in enumerate(pool.map(safe,urls)):
            results[url]=result
            if index%25==0:print('Kontrol:',index+1,'/',len(urls),flush=True)
    report={}
    for key,urls in candidates.items():
        existing=manifest.get(key) or manifest.get(ALIASES.get(key,''))
        valid=[(u,results[u]) for u in urls if results[u]]
        if existing:
            report[key]={'durum':'hazır','boyut':existing['boyut']}
            manifest[key]=existing
            continue
        if not valid:
            report[key]={'durum':'kaynak bulunamadı'};continue
        url,(raw,size,extension)=max(valid,key=lambda x:min(x[1][1]))
        if min(size)<228:
            report[key]={'durum':'düşük çözünürlük','boyut':size,'url':url};continue
        filename=hashlib.sha256(raw).hexdigest()[:20]+'.'+extension
        (LIBRARY/filename).write_bytes(raw)
        manifest[key]={'dosya':filename,'kaynak':institutions[key].get('kaynak') or url,'orijinal':url,'boyut':list(size)}
        report[key]={'durum':'hazır','boyut':size}
    (LIBRARY/'kaynaklar.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'local-data/logo-kalite-raporu.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Hazır:',sum(v['durum']=='hazır' for v in report.values()),'/',len(report),flush=True)
    for k,v in report.items():
        if v['durum']!='hazır':print(k,v,flush=True)

if __name__=='__main__':main()
