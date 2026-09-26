"""Use only institution logos identified by official public directories."""
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image
from ek_kaynaklar import norm, clean

CATALOG=Path(__file__).with_name('kurum_logolari.json')
HOSTS={'kariyerkapisi.gov.tr','cdn.e-devlet.gov.tr'}


def kurum_anahtari(name):
    value=clean(re.sub(r'\b(?:rektorlugu|baskanligi)\b','',norm(name)))
    return re.sub(r'\bbelediyesi\b','belediye',value)


def logo_url(value):
    p=urllib.parse.urlsplit(value or '')
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('Doğrulanmış logo kaynağı gerekli')
    if p.hostname=='kariyerkapisi.gov.tr' and not re.fullmatch(r'/UPS/[a-zA-Z0-9_.-]+',p.path):
        raise ValueError('Logo yolu geçersiz')
    if p.hostname=='cdn.e-devlet.gov.tr' and not p.path.startswith('/themes/ankara/images/logos/'):
        raise ValueError('Logo yolu geçersiz')
    return value


class LogoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        logo_url(urllib.parse.urljoin(req.full_url,newurl))
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def logo_adresi(ilan):
    if ilan.get('kurum_logo'):
        return logo_url(ilan['kurum_logo'])
    if not CATALOG.exists():
        return None
    entries=json.loads(CATALOG.read_text(encoding='utf-8'))
    from yerel_kaynak import oku
    entries.update(oku().get('logolar',{}))
    item=entries.get(kurum_anahtari(ilan.get('kurum','')))
    return logo_url(item['url']) if item else None


def kurum_logosu(ilan):
    try:
        url=logo_adresi(ilan)
        if not url:
            return None
        op=urllib.request.build_opener(LogoRedirect())
        with op.open(url,timeout=10) as response:
            logo_url(response.geturl())
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:
            return None
        with Image.open(io.BytesIO(raw)) as im:
            if im.width*im.height>8_000_000:
                return None
            im=im.convert('RGBA');im.thumbnail((180,180))
            out=io.BytesIO();im.save(out,format='PNG')
            return out.getvalue()
    except Exception:
        # Missing/unavailable logos must not stop an otherwise valid announcement.
        return None
