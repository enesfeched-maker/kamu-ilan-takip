"""GitHub Pages paketi (docs/) 1 GB sınırına dayandı (20 Ekim 2026: 1,34 GB). Yayına giden pakete yalnız sitede
bağlantısı olan ilan belgeleri (PDF) konur; depodaki diğer belgeler (eski ilanlar, 1,3 GB) yerinde kalır, yayına girmez.

Kullanım: python bot/site_paketi.py [kaynak=docs] [hedef=_site]"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BELGE_YOLU = 'belgeler/sbb'
PDF = re.compile(r'belgeler/sbb/([a-f0-9]{64})\.pdf')


def bagli_belgeler(ilanlar_json):
    """ilanlar.json'daki kayıtların belge_sha256 / belge_kopyasi ile işaret ettiği PDF özetleri."""
    try:
        veri = json.loads(Path(ilanlar_json).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None   # okunamazsa hiçbir şey ayıklanmaz
    ozetler = set()
    for i in veri.get('ilanlar') or []:
        if i.get('belge_sha256'):
            ozetler.add(str(i['belge_sha256']))
        m = PDF.search(str(i.get('belge_kopyasi') or ''))
        if m:
            ozetler.add(m.group(1))
    return ozetler


def paketle(kaynak=ROOT / 'docs', hedef=ROOT / '_site'):
    kaynak, hedef = Path(kaynak), Path(hedef)
    ozetler = bagli_belgeler(kaynak / 'ilanlar.json')
    belge_klasoru = (kaynak / BELGE_YOLU).resolve()
    belgeler = (kaynak / 'belgeler').resolve()

    def atla(klasor, adlar):
        if Path(klasor).resolve() == belgeler and 'csb' in adlar:
            return ['csb']   # ÇŞB ek kopyaları yalnız yapay zekâ okuması için (yz_claude); yayına girmez
        if ozetler is not None and Path(klasor).resolve() == belge_klasoru:
            return [a for a in adlar if a.endswith('.pdf') and a[:-4] not in ozetler]
        return []
    if hedef.exists():
        shutil.rmtree(hedef)
    shutil.copytree(kaynak, hedef, ignore=atla)
    return ozetler


def boyut(klasor):
    return sum(f.stat().st_size for f in Path(klasor).rglob('*') if f.is_file())


if __name__ == '__main__':
    k = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'docs'
    h = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / '_site'
    oz = paketle(k, h)
    print(f'Site paketi: {boyut(h) // 2**20} MB (bağlantılı belge: {len(oz) if oz is not None else "hepsi"}).')
