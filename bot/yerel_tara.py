"""Local collector: publish public source data only; never send Telegram messages."""
import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from ek_kaynaklar import read_sbb,fresh
from csb_kaynak import csb_oku
from resmi_detay import detay_oku, SURUM

ROOT=Path(__file__).resolve().parents[1]
REPO='enesfeched-maker/kamu-ilan-takip'
REMOTE_PATH='docs/yerel-kaynaklar.json'
API='https://api.github.com/repos/'+REPO+'/contents/'


def github(path,method='GET',payload=None,token=''):
    headers={'Accept':'application/vnd.github+json','User-Agent':'KamuIlanTakip-local','X-GitHub-Api-Version':'2022-11-28'}
    if token:
        headers['Authorization']='Bearer '+token
    request=urllib.request.Request(path if path.startswith('https://') else API+path,method=method,headers=headers,
        data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.urlopen(request,timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code==404 and method=='GET' and path==REMOTE_PATH:
            return None
        raise RuntimeError('GitHub HTTP '+str(exc.code)) from None


def decode(blob,token=''):
    """Contents API yanıtını çözer. 1 MB'tan büyük dosyada içerik boş gelir (encoding 'none'); o zaman dosya git blob
    servisinden (100 MB'a kadar) okunur. 14 Ekim 2026: yerel-kaynaklar.json 1,6 MB'a çıkınca telefon ve bilgisayar
    taraması 'JSONDecodeError' ile 18:30'dan sonra durmuştu."""
    if not blob:
        return {}
    icerik=blob.get('content') or ''
    if not icerik.strip() and blob.get('sha'):
        icerik=github('https://api.github.com/repos/'+REPO+'/git/blobs/'+blob['sha'],token=token)['content']
    return json.loads(base64.b64decode(icerik))


def collect(registry,old):
    previous={i['id']:i for i in registry.get('ilanlar',[])}
    previous.update({i['id']:i for i in old.get('kaynaklar',{}).get('sbb',{}).get('ilanlar',[])})
    previous.update({i['id']:i for i in old.get('kaynaklar',{}).get('csb',{}).get('ilanlar',[])})
    result={'schema':1,'guncelleme':datetime.now(timezone.utc).isoformat(),'kaynaklar':dict(old.get('kaynaklar',{})), 'detaylar':dict(old.get('detaylar',{}))}
    from kurum_gorseli import CATALOG
    if CATALOG.exists():
        result['logolar']=json.loads(CATALOG.read_text(encoding='utf-8'))
    try:
        rows,errors=read_sbb(previous)
        result['kaynaklar']['sbb']={'kontrol':datetime.now(timezone.utc).isoformat(),'hata_sayisi':errors,'ilanlar':rows}
        print('SBB:',len(rows),'ilan;',errors,'okuma hatası.',flush=True)
    except Exception as exc:
        print('SBB kontrolü ertelendi:',type(exc).__name__,flush=True)
    try:
        rows,errors=csb_oku(previous)
        result['kaynaklar']['csb']={'kontrol':datetime.now(timezone.utc).isoformat(),'hata_sayisi':errors,'ilanlar':rows}
        print('ÇŞB Yerel Yönetimler:',len(rows),'duyuru;',errors,'okuma hatası.',flush=True)
    except Exception as exc:
        print('ÇŞB kontrolü ertelendi:',type(exc).__name__,flush=True)
    failures=0
    for item in registry.get('ilanlar',[]):
        if item.get('kaynak_turu') or not item.get('link','').startswith('https://kariyerkapisi.gov.tr/IlanDetay?'):
            continue
        cached=result['detaylar'].get(item['id'],{})
        if fresh(cached) and cached.get('kk_detay_surumu',1)==SURUM:
            continue
        try:
            result['detaylar'][item['id']]=detay_oku(item['link'])
            failures=0
        except Exception:
            failures+=1
            if failures>=3:
                break
        time.sleep(.25)
    result['detaylar']={k:v for k,v in result['detaylar'].items() if k in previous and fresh(v)}
    print('Doğrulanmış Kariyer Kapısı ayrıntıları:',len(result['detaylar']),flush=True)
    result['_yeni_logolar']=eksik_logolar(registry,result['detaylar'])
    return result


def eksik_logolar(registry,detaylar):
    """Kütüphanede logosu olmayan kurumların Kariyer Kapısı logo adresleri: {kurum anahtarı: (kurum, adres, ilan bağlantısı)}.
    GitHub'dan Kariyer Kapısı'na erişilemediği günlerde kartlar logosuz kalıyordu (12 Ekim 2026, Milli Saraylar)."""
    from kurum_gorseli import LIBRARY,kurum_anahtari
    try:
        man=json.loads((LIBRARY/'kaynaklar.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return {}
    sonuc={}
    for item in registry.get('ilanlar',[]):
        logo=(detaylar.get(item.get('id'),{}) or {}).get('kurum_logo') or item.get('kurum_logo')
        anahtar=kurum_anahtari(item.get('kurum',''))
        if logo and anahtar and anahtar not in man and logo.startswith('https://kariyerkapisi.gov.tr/UPS/'):
            sonuc[anahtar]=(item.get('kurum',''),logo,item.get('link',''))
    return sonuc


def logo_dosyalari(yeni):
    """Eksik logoları indirir; {repo yolu: içerik} (logolar + güncel kaynaklar.json). İndirilemeyen atlanır."""
    import io,re,unicodedata
    from PIL import Image
    from kurum_gorseli import LIBRARY
    if not yeni:
        return {}
    man_yol=LIBRARY/'kaynaklar.json'
    man=json.loads(man_yol.read_text(encoding='utf-8'))
    dosyalar={}
    for anahtar,(kurum,adres,kaynak) in list(yeni.items())[:10]:
        try:
            with urllib.request.urlopen(urllib.request.Request(adres,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as r:
                raw=r.read(3_000_001)
            if len(raw)>3_000_000:
                continue
            with Image.open(io.BytesIO(raw)) as im:
                im.load()
                cikti=io.BytesIO();im.convert('RGBA').save(cikti,format='PNG');boyut=list(im.size)
        except Exception:
            continue
        ad=re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',anahtar).encode('ascii','ignore').decode()).strip('-')[:60]+'.png'
        dosyalar['docs/assets/kurum-logolari/'+ad]=cikti.getvalue()
        man[anahtar]={'dosya':ad,'kaynak':kaynak,'orijinal':adres,'boyut':boyut}
        print('Yeni kurum logosu:',kurum,flush=True)
    if dosyalar:
        dosyalar['docs/assets/kurum-logolari/kaynaklar.json']=(json.dumps(man,ensure_ascii=False,indent=2)+'\n').encode()
    return dosyalar


def publish(snapshot,token):
    # Update only the collector file, never the bot's sent/reminder histories.
    from sbb_detay import document_url
    documents=logo_dosyalari(snapshot.pop('_yeni_logolar',{}))
    for item in snapshot.get('kaynaklar',{}).get('sbb',{}).get('ilanlar',[]):
        if document_url(item):
            path='docs/belgeler/sbb/'+item['belge_sha256']+'.pdf'
            local=ROOT/path
            if local.exists():documents[path]=local.read_bytes()
    try:   # ÇŞB ek kopyaları: Claude ilan okuması bulutta bu siteye erişemiyor (csb_kaynak.belge_yolu)
        from csb_kaynak import belge_kopyalari
        documents.update(belge_kopyalari(snapshot.get('kaynaklar',{}).get('csb',{}).get('ilanlar',[])))
    except Exception as exc:
        print('ÇŞB belge kopyaları hazırlanamadı:',type(exc).__name__,flush=True)
    if documents:
        from github_yayin import publish_files
        documents[REMOTE_PATH]=(json.dumps(snapshot,ensure_ascii=False,indent=1)+'\n').encode()
        publish_files(documents,token,'SBB ilan ayrıntılarını, kaynak belgelerini ve kurum logolarını güncelle')
        return
    for attempt in range(3):
        old=github(REMOTE_PATH,token=token)
        data={'message':'Yerel kaynak kontrolünü güncelle','branch':'main',
              'content':base64.b64encode((json.dumps(snapshot,ensure_ascii=False,indent=1)+'\n').encode()).decode()}
        if old:
            data['sha']=old['sha']
        try:
            github(REMOTE_PATH,'PUT',data,token)
            return
        except RuntimeError as exc:
            if str(exc)!='GitHub HTTP 409' or attempt==2:
                raise
            time.sleep(2)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    token=os.environ.get('KAMU_GITHUB_TOKEN','')
    if not token and not args.preview:
        from yerel_guvenlik import load_token
        token=load_token()
    if not args.preview and not token:
        raise RuntimeError('GitHub bağlantısı henüz kurulmadı. Yerel kurulum penceresini tamamlayın.')
    registry=decode(github('docs/ilanlar.json',token=token),token)
    old=decode(github(REMOTE_PATH,token=token),token)
    snapshot=collect(registry,old)
    local=ROOT/'local-data';local.mkdir(exist_ok=True)
    (local/'son-kontrol.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=1),encoding='utf-8')
    if args.preview:
        print('Önizleme hazır; GitHub ve Telegram değiştirilmedi.')
        return
    publish(snapshot,token)
    (local/'durum.json').write_text(json.dumps({'son_basarili_aktarim':snapshot['guncelleme']},ensure_ascii=False),encoding='utf-8')
    print('Kaynak verisi GitHub’a aktarıldı. Yayın ve Telegram gönderimleri mevcut bot tarafından yapılacak.')


if __name__=='__main__':
    import sys
    if sys.stdout is None:
        logdir=ROOT/'local-data';logdir.mkdir(exist_ok=True)
        log=logdir/'tarama.log'
        if log.exists() and log.stat().st_size>1_000_000:
            log.replace(log.with_suffix('.onceki.log'))
        sys.stdout=sys.stderr=log.open('a',encoding='utf-8',buffering=1)
    print('Yerel tarama:',datetime.now(timezone.utc).isoformat(),flush=True)
    try:
        main()
    except Exception as exc:
        print('Yerel tarama tamamlanamadı:',str(exc) if isinstance(exc,RuntimeError) else f'{type(exc).__name__}: {str(exc)[:200]}')
        raise SystemExit(1)
