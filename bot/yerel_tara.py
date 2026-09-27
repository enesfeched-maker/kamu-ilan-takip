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
from resmi_detay import detay_oku

ROOT=Path(__file__).resolve().parents[1]
REPO='enesfeched-maker/kamu-ilan-takip'
REMOTE_PATH='docs/yerel-kaynaklar.json'
API='https://api.github.com/repos/'+REPO+'/contents/'


def github(path,method='GET',payload=None,token=''):
    headers={'Accept':'application/vnd.github+json','User-Agent':'KamuIlanTakip-local','X-GitHub-Api-Version':'2022-11-28'}
    if token:
        headers['Authorization']='Bearer '+token
    request=urllib.request.Request(API+path,method=method,headers=headers,
        data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.urlopen(request,timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code==404 and method=='GET' and path==REMOTE_PATH:
            return None
        raise RuntimeError('GitHub HTTP '+str(exc.code)) from None


def decode(blob):
    if not blob:
        return {}
    return json.loads(base64.b64decode(blob['content']))


def collect(registry,old):
    previous={i['id']:i for i in registry.get('ilanlar',[])}
    previous.update({i['id']:i for i in old.get('kaynaklar',{}).get('sbb',{}).get('ilanlar',[])})
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
    failures=0
    for item in registry.get('ilanlar',[]):
        if item.get('kaynak_turu') or not item.get('link','').startswith('https://kariyerkapisi.gov.tr/IlanDetay?'):
            continue
        cached=result['detaylar'].get(item['id'],{})
        if fresh(cached):
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
    return result


def publish(snapshot,token):
    # Update only the collector file, never the bot's sent/reminder histories.
    from sbb_detay import document_url
    documents={}
    for item in snapshot.get('kaynaklar',{}).get('sbb',{}).get('ilanlar',[]):
        if document_url(item):
            path='docs/belgeler/sbb/'+item['belge_sha256']+'.pdf'
            local=ROOT/path
            if local.exists():documents[path]=local.read_bytes()
    if documents:
        from github_yayin import publish_files
        documents[REMOTE_PATH]=(json.dumps(snapshot,ensure_ascii=False,indent=1)+'\n').encode()
        publish_files(documents,token,'SBB ilan ayrıntılarını ve kaynak belgelerini güncelle')
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
    registry=decode(github('docs/ilanlar.json',token=token))
    old=decode(github(REMOTE_PATH,token=token))
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
        print('Yerel tarama tamamlanamadı:',str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__)
        raise SystemExit(1)
