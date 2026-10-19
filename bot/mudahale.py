"""Sitedeki ilanlara ani müdahale (19 Ekim 2026).

İki katman birlikte yazılır:
  docs/mudahale.json  Site (portal.js) bunu GitHub'dan doğrudan okur: değişiklik site yeniden derlenmeden 1–2 dakikada görünür.
  config.json 'elle'  Kalıcı karar: sonraki taramada site derlemesine ve Telegram'a da uygulanır (gizlenen ilan kanala gitmez).

Kullanım (ilan-mudahale.yml, telefondan da çalıştırılabilir):
  python bot/mudahale.py gizle  https://kpsstercihi.com/ilan/<anahtar>/
  python bot/mudahale.py goster <anahtar>
  python bot/mudahale.py duzelt <anahtar> --manset "9 Zabıta Memuru" --son-tarih 2026-10-23 --toplam 9"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUDAHALE = ROOT / 'docs' / 'mudahale.json'
CONFIG = ROOT / 'config.json'
TR = timezone(timedelta(hours=3))
KK = 'https://kariyerkapisi.gov.tr/IlanDetay?i='
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def anahtar_coz(girdi):
    """Site bağlantısı, Kariyer Kapısı bağlantısı ya da anahtar -> (sitedeki anahtar, veri kimliği)."""
    s = (girdi or '').strip()
    m = re.search(r'/ilan/([^/?#]+)', s) or re.search(r'IlanDetay\?i=([0-9a-fA-F-]{36})', s)
    anahtar = (m.group(1) if m else s).strip()
    if UUID.match(anahtar.lower()):
        anahtar = anahtar.lower()
    if not re.fullmatch(r'[A-Za-z0-9-]{6,80}', anahtar):
        raise ValueError(f'İlan tanınmadı: {girdi!r}')
    return anahtar, (KK + anahtar if UUID.match(anahtar) else anahtar)


def _oku(yol, bos):
    try:
        return json.loads(Path(yol).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return bos


def _yaz(yol, veri, girinti):
    Path(yol).write_text(json.dumps(veri, ensure_ascii=False, indent=girinti) + '\n', encoding='utf-8', newline='\n')


def uygula(islem, girdi, manset=None, son_tarih=None, toplam=None, simdi=None, mudahale_yolu=MUDAHALE, config_yolu=CONFIG):
    anahtar, kimlik = anahtar_coz(girdi)
    m = _oku(mudahale_yolu, {})
    m.setdefault('gizle', [])
    m.setdefault('alanlar', {})
    cfg = _oku(config_yolu, {})
    elle = cfg.setdefault('elle', {})
    gizle = elle.setdefault('gizle', [])
    alanlar = elle.setdefault('alanlar', {})
    if islem == 'gizle':
        if anahtar not in m['gizle']:
            m['gizle'].append(anahtar)
        if kimlik not in gizle:
            gizle.append(kimlik)
    elif islem == 'goster':
        m['gizle'] = [k for k in m['gizle'] if k != anahtar]
        m['alanlar'].pop(anahtar, None)
        elle['gizle'] = [k for k in gizle if k != kimlik]
    elif islem == 'duzelt':
        site, veri = {}, {}
        if son_tarih:
            gun = datetime.strptime(son_tarih, '%Y-%m-%d').date().isoformat()
            site.update(son_tarih=gun, son_zaman=f'{gun}T23:59:00+03:00')
            veri.update(son_tarih=gun, son_zaman=f'{gun}T23:59:00+03:00')
        if manset:
            site['manset'] = manset.strip()[:140]
            veri['kadro'] = manset.strip()[:300]
        if toplam not in (None, ''):
            site['toplam'] = int(toplam)
        if not site:
            raise ValueError('Düzeltilecek alan yok (manşet, son tarih ya da kişi sayısı).')
        m['alanlar'].setdefault(anahtar, {}).update(site)
        if veri:
            alanlar.setdefault(kimlik, {}).update(veri)
    else:
        raise ValueError(f'Bilinmeyen işlem: {islem}')
    m['guncelleme'] = (simdi or datetime.now(TR)).isoformat(timespec='seconds')
    _yaz(mudahale_yolu, m, 1)
    if config_yolu:
        _yaz(config_yolu, cfg, 2)
    return anahtar, kimlik


def liste_uygula(ilanlar, mudahale_yolu=MUDAHALE):
    """Site derlemesinde liste.json kayıtlarına aynı müdahaleyi uygular (portal.js ile aynı kurallar)."""
    m = _oku(mudahale_yolu, {})
    gizle = set(m.get('gizle') or [])
    alan = m.get('alanlar') or {}
    sonuc = []
    for k in ilanlar:
        if k.get('key') in gizle or k.get('kopya_of') in gizle:
            continue
        a = alan.get(k.get('key'))
        if isinstance(a, dict):
            k = dict(k, **{x: a[x] for x in ('manset', 'son_tarih', 'son_zaman', 'toplam', 'il') if x in a})
        sonuc.append(k)
    return sonuc


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('islem', choices=('gizle', 'goster', 'duzelt'))
    p.add_argument('ilan')
    p.add_argument('--manset')
    p.add_argument('--son-tarih')
    p.add_argument('--toplam')
    a = p.parse_args()
    anahtar, kimlik = uygula(a.islem, a.ilan, a.manset, a.son_tarih, a.toplam)
    print(f'{a.islem}: {anahtar} ({kimlik})')
