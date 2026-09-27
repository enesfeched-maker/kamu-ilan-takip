"""Publish a single atomic commit to this project's existing GitHub repository."""
import base64
import hashlib
import json
import time
import urllib.request
import urllib.error

API='https://api.github.com/repos/enesfeched-maker/kamu-ilan-takip/'


def api(path,token,method='GET',data=None):
    req=urllib.request.Request(API+path,method=method,
        headers={'Authorization':'Bearer '+token,'User-Agent':'KamuIlanTakip','Accept':'application/vnd.github+json'},
        data=json.dumps(data).encode() if data is not None else None)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (403,429,502,503) and attempt<3:
                time.sleep(30);continue
            raise RuntimeError('GitHub yayın HTTP '+str(exc.code)) from None


def publish_files(files,token,message):
    blobs={}
    for retry in range(3):
        head=api('git/ref/heads/main',token)['object']['sha']
        commit=api('git/commits/'+head,token)
        tree=api('git/trees/'+commit['tree']['sha']+'?recursive=1',token)
        existing={i['path']:i['sha'] for i in tree['tree']}
        changes=[]
        for path,raw in files.items():
            if '..' in path.split('/') or not path.startswith(('bot/','docs/')):
                raise ValueError('Yayın yolu proje kapsamı dışında')
            sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if existing.get(path)==sha:continue
            if sha not in blobs:
                blobs[sha]=api('git/blobs',token,'POST',{'encoding':'base64','content':base64.b64encode(raw).decode()})['sha']
                if len(blobs)%10==0:print('Aktarılan yeni dosya:',len(blobs),flush=True)
                time.sleep(.8)
            changes.append({'path':path,'mode':'100644','type':'blob','sha':blobs[sha]})
        if not changes:return
        newtree=api('git/trees',token,'POST',{'base_tree':commit['tree']['sha'],'tree':changes})
        newcommit=api('git/commits',token,'POST',{'message':message,'tree':newtree['sha'],'parents':[head]})
        try:
            api('git/refs/heads/main',token,'PATCH',{'sha':newcommit['sha'],'force':False})
            print('Yayımlanan dosya:',len(changes),flush=True);return
        except RuntimeError as exc:
            if '422' not in str(exc) or retry==2:raise
    raise RuntimeError('Eşzamanlı GitHub güncellemesi; sonraki taramada tekrar denenecek.')
