"""GitHub çalıştırıcılarının DNS sorunlarına karşı resmi alan adları için HTTPS DNS."""
import http.client
import ipaddress
import json
import time
import urllib.parse
import urllib.request

RESMI_ALANLAR = {'kariyerkapisi.gov.tr', 'api.kariyerkapisi.gov.tr'}
ONBELLEK = {}


def adres_coz(host):
    if host not in RESMI_ALANLAR:
        raise ValueError('Resmi olmayan alan adı')
    eski = ONBELLEK.get(host)
    if eski and eski[1] > time.monotonic():
        return eski[0]
    url = 'https://dns.google/resolve?' + urllib.parse.urlencode({'name': host, 'type': 'A'})
    with urllib.request.urlopen(url, timeout=10) as response:
        veri = json.load(response)
    if veri.get('Status') != 0:
        raise OSError('Resmi alan adı DNS kaydı bulunamadı')
    for kayit in veri.get('Answer', []):
        if kayit.get('type') == 1 and ipaddress.ip_address(kayit['data']).is_global:
            ONBELLEK[host] = (kayit['data'], time.monotonic() + min(kayit.get('TTL', 300), 3600))
            return kayit['data']
    raise OSError('Resmi alan adı için genel IP adresi bulunamadı')


class ResmiHTTPSBaglantisi(http.client.HTTPSConnection):
    def connect(self):
        baglan = self._create_connection
        def cozulmus_baglanti(address, *args, **kwargs):
            host, port = address
            if host in RESMI_ALANLAR:
                address = (adres_coz(host), port)
            return baglan(address, *args, **kwargs)
        self._create_connection = cozulmus_baglanti
        # HTTPSConnection özgün host ile SNI ve sertifika doğrulamasını yapar.
        super().connect()


class ResmiHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(ResmiHTTPSBaglantisi, req, context=self._context)


def url_ac(req, timeout=20):
    return urllib.request.build_opener(ResmiHTTPSHandler()).open(req, timeout=timeout)
