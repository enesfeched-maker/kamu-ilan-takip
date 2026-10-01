"""Consume the local collector's public, timestamped snapshot."""
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path

SNAPSHOT=Path(__file__).resolve().parents[1]/'docs'/'yerel-kaynaklar.json'


def oku(path=None):
    try:
        p=path or SNAPSHOT
        if p.stat().st_size>3_000_000:
            return {}
        data=json.loads(p.read_text(encoding='utf-8'))
        return data if data.get('schema')==1 else {}
    except (OSError,ValueError,TypeError):
        return {}


def taze(stamp,minutes=90):
    try:
        age=datetime.now(timezone.utc)-datetime.fromisoformat(stamp)
        return timedelta(0)<=age<timedelta(minutes=minutes)
    except (TypeError,ValueError):
        return False


def sbb_verisi(data):
    return kaynak_verisi(data,'sbb')


def csb_verisi(data):
    return kaynak_verisi(data,'csb')


def kaynak_verisi(data,ad):
    source=data.get('kaynaklar',{}).get(ad,{})
    rows=source.get('ilanlar')
    if not taze(source.get('kontrol')) or not isinstance(rows,list) or not rows:
        return None
    if not all(isinstance(i,dict) and i.get('id') and i.get('baslik') and i.get('link','').startswith('https://') for i in rows):
        return None
    return rows,int(source.get('hata_sayisi',0)),source['kontrol']
