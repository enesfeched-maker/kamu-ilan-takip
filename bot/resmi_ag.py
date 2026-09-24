"""GitHub çalıştırıcılarının DNS sorunlarına karşı resmi alan adları için HTTPS DNS."""
import http.client
import ipaddress
import json
import time
import urllib.parse
import urllib.request

RESMI_ALANLAR = {'kariyerkapisi.gov.tr', 'api.kariyerkapisi.gov.tr'}
# 25 Eylül 2026: hem sistem DNS'i hem dns.google üzerinden doğrulandı.
# Sadece DNS yanıtı kullanılamazsa denenir; TLS özgün alan adını doğrulamaya devam eder.
SON_DOGRULANAN = {'kariyerkapisi.gov.tr': '94.55.123.141',
                  'api.kariyerkapisi.gov.tr': '94.55.122.127'}
ONBELLEK = {}


def adres_coz(host):
    if host not in RESMI_ALANLAR:
        raise ValueError('Resmi olmayan alan adı')
    eski = ONBELLEK.get(host)
    if eski and eski[1] > time.monotonic():
        return eski[0]
    url = 'https://dns.google/resolve?' + urllib.parse.urlencode({'name': host, 'type': 'A'})
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            veri = json.load(response)
        if veri.get('Status') == 0:
            for kayit in veri.get('Answer', []):
                if kayit.get('type') == 1 and ipaddress.ip_address(kayit['data']).is_global:
                    ONBELLEK[host] = (kayit['data'], time.monotonic() + min(kayit.get('TTL', 300), 3600))
                    return kayit['data']
        print(f'DNS yanıtı genel adres içermiyor: {host}: {json.dumps(veri)[:500]}')
    except (OSError, ValueError):
        print(f'DNS servisine ulaşılamadı: {host}')
    ONBELLEK[host] = (SON_DOGRULANAN[host], time.monotonic() + 300)
    print(f'Doğrulanmış yedek adres kullanılıyor: {host}; TLS alan adı doğrulaması açık.')
    return SON_DOGRULANAN[host]


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
