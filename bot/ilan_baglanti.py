import re
import uuid
from urllib.parse import urlsplit, parse_qs


def ilan_anahtari(ilan):
    raw=parse_qs(urlsplit(ilan.get('link','')).query).get('i',[''])[0]
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        ident=ilan.get('id','')
        if re.fullmatch(r'(?:(?:sbb|iskur)-[a-f0-9]{24}|csb-\d{4,9})',ident):
            return ident
        raise ValueError('İlanın site bağlantısı oluşturulamadı')


def ilan_sayfasi(ilan, site_url):
    base=urlsplit(site_url)
    if base.scheme!='https' or not base.hostname or base.username or base.password:
        raise ValueError('Geçerli HTTPS site adresi gerekli')
    return site_url.rstrip('/')+'/ilan/'+ilan_anahtari(ilan)+'/'
