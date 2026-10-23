"""Kullanıcının elle doğruladığı ilanları mevcut botun standart gönderim akışıyla paylaşır."""
import json
import sys
import urllib.request
from pathlib import Path

import ilan_bot as bot
from ilan_baglanti import ilan_anahtari, ilan_sayfasi

ROOT=Path(__file__).resolve().parents[1]


def dogrula(item, alan, liste):
    toplam=sum(k['adet'] for k in alan['yz_kadrolar'])
    kayit=next((i for i in liste['ilanlar'] if i.get('key')==ilan_anahtari(item)),None)
    if not kayit or kayit.get('toplam')!=toplam or kayit.get('son_tarih')!=alan['son_tarih']:
        raise RuntimeError('Canlı listedeki kadro/tarih henüz güncel değil: '+item['id'])
    if set(kayit.get('ogrenim') or [])!=set(alan['ogrenim']):
        raise RuntimeError('Canlı öğrenim bilgisi güncel değil: '+item['id'])
    with urllib.request.urlopen(ilan_sayfasi(item,'https://kpsstercihi.com/'),timeout=30) as r:
        html=r.read().decode('utf-8')
    if alan['son_tarih'] not in html or str(toplam) not in html:
        raise RuntimeError('Canlı ayrıntı sayfası henüz güncel değil: '+item['id'])


def main():
    cfg=json.loads((ROOT/'config.json').read_text('utf-8'))
    alanlar=(cfg.get('elle') or {}).get('alanlar') or {}
    hedef=set(sys.argv[1:])
    if not hedef or any(not alanlar.get(k,{}).get('telegram_hemen') for k in hedef):
        raise RuntimeError('Yalnız kullanıcı tarafından elle doğrulanmış ilanlar gönderilebilir.')
    veri=json.loads((ROOT/'docs/ilanlar.json').read_text('utf-8'))
    with urllib.request.urlopen('https://kpsstercihi.com/liste.json',timeout=30) as r: liste=json.load(r)
    for k in hedef:
        item=next(i for i in veri['ilanlar'] if i['id']==k)
        dogrula(dict(item,**alanlar[k]),alanlar[k],liste)
    # Kart, tek satırlık açıklama, düğmeler, 150 saniyelik aralık ve mesaj geçmişi normal botta kalır.
    sirasi=bot.telegram_sirasi
    bot.telegram_sirasi=lambda *a,**kw:[i for i in sirasi(*a,**kw) if i['id'] in hedef]
    bot.toplu_zamani=lambda *a,**kw:False
    bot.aksam_zamani=lambda *a,**kw:False
    sys.argv=[sys.argv[0],'--send-only']
    bot.main()
    yeni=json.loads((ROOT/'docs/ilanlar.json').read_text('utf-8'))
    eksik=hedef-set(yeni.get('telegram_gonderilen',[]))
    if eksik: raise RuntimeError('Gönderilmeyen onaylı ilanlar: '+', '.join(sorted(eksik)))
    print('Onaylı ilanların tamamı normal kanal biçimiyle gönderildi.')


if __name__=='__main__': main()
