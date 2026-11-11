"""Consume the local collector's public, timestamped snapshot."""
import json
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path

SNAPSHOT=Path(__file__).resolve().parents[1]/'docs'/'yerel-kaynaklar.json'
# Bozuk/şişmiş dosyaya karşı üst sınır. 11 Kasım 2026: sınır 3 MB iken dosya 2,2 MB'a ulaşmıştı (14 Ekim'de 1,6 MB);
# aşıldığında SBB ve ÇŞB hiçbir uyarı vermeden kesilecekti. Sınır yükseltildi, yaklaşınca ve aşılınca uyarı yazılır.
EN_BUYUK=12_000_000
UYARI_BOYUTU=8_000_000


def oku(path=None):
    try:
        p=path or SNAPSHOT
        boyut=p.stat().st_size
        if boyut>EN_BUYUK:
            print(f'::error::Yerel kaynak dosyası çok büyük ({boyut//1000} KB > {EN_BUYUK//1000} KB); SBB ve ÇŞB verisi okunmadı.',file=sys.stderr)
            return {}
        if boyut>UYARI_BOYUTU:
            print(f'::warning::Yerel kaynak dosyası büyüyor ({boyut//1000} KB); {EN_BUYUK//1000} KB aşılırsa SBB ve ÇŞB verisi okunmaz.',file=sys.stderr)
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
