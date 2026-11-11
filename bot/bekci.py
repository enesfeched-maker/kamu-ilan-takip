"""Bekçi: yarım saatte bir sistemi kontrol eder, yöneticiye Telegram'dan ÖZEL mesaj atar (kanala değil). (22 Ekim 2026)

Kontroller: tarama (ilan.yml) durmuş/arka arkaya başarısız mı, site güncel mi, Telegram sırasında ilan sıkışmış mı, sosyal
medya paylaşımı bozuk mu. Mesaj kuralı: yeni sorun hemen, aynı sorun 6 saatte bir hatırlatma, düzelince "düzeldi";
her şey yolundaysa günde iki kez (09 ve 21, TR) kısa özet. Durum bekci-durum.json dosyasında (Actions önbelleği).
Kullanım: python bot/bekci.py            # kontrol et, gerekirse mesaj at
          python bot/bekci.py --id-bul    # botla konuşan özel sohbetlerin kimliklerini yazar (TELEGRAM_YONETICI_ID için)
          python bot/bekci.py --deneme    # kontrol sonucunu yazar, mesaj atmaz"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TR = timezone(timedelta(hours=3))
SITE = 'https://kpsstercihi.com/'
DURUM = Path(os.environ.get('BEKCI_DURUM', 'bekci-durum.json'))
TARAMA_EN_GEC = timedelta(minutes=100)   # tarama yarım saatte bir; GitHub gecikmesi + 22-35 dk çalışma süresi payı
SITE_EN_GEC = timedelta(minutes=170)
HATIRLATMA = timedelta(hours=6)
YEREL_EN_GEC = timedelta(hours=12)       # bilgisayar gece kapalı olabilir; yarım günden uzun kesinti gerçek sorundur
YEREL_KAYNAKLAR = {'sbb': 'SBB', 'csb': 'ÇŞB'}   # yalnız kullanıcının bilgisayarındaki yerel tarayıcıdan gelen kaynaklar


def gh(*args):
    sonuc = subprocess.run(['gh', *args], capture_output=True, text=True, encoding='utf-8')
    if sonuc.returncode != 0:
        raise RuntimeError(sonuc.stderr.strip()[:200])
    return sonuc.stdout


def calismalar(is_akisi, adet=8):
    return json.loads(gh('run', 'list', '--workflow', is_akisi, '--limit', str(adet), '--json',
                         'status,conclusion,createdAt,updatedAt,event'))


def zaman(deger):
    return datetime.fromisoformat(str(deger).replace('Z', '+00:00'))


def yerel_gecikenler(simdi, kaynak_durumlari):
    """Yerel tarayıcıdan YEREL_EN_GEC'tir veri gelmeyen kaynakların adları. 'kontrol' yalnız başarılı okumada yazılır
    (ilan_bot); hiç yazılmamışsa ya da okunamıyorsa kaynak gecikmiş sayılır."""
    geciken = []
    for anahtar, ad in YEREL_KAYNAKLAR.items():
        durum = (kaynak_durumlari or {}).get(anahtar)
        if not isinstance(durum, dict):
            continue   # kaynak bu kurulumda hiç kullanılmıyor
        try:
            son = zaman(durum.get('kontrol'))
            son = son if son.tzinfo else son.replace(tzinfo=TR)
            gecikti = simdi - son > YEREL_EN_GEC
        except (TypeError, ValueError):
            gecikti = True
        if gecikti:
            geciken.append(ad)
    return geciken


def sorunlar(simdi, tarama, sosyal, site_guncelleme, site_hata, bekleyen, zaman_kontrol=None, kaynak_durumlari=None):
    """{anahtar: 'insan okunur sorun'} — boşsa her şey yolunda. Saf işlev (testli)."""
    s = {}
    biten = [c for c in tarama if c.get('status') == 'completed' and c.get('conclusion') != 'cancelled']
    if biten:
        son_basarili = next((c for c in biten if c['conclusion'] == 'success'), None)
        art_arda = 0
        for c in biten:
            if c['conclusion'] == 'success':
                break
            art_arda += 1
        if art_arda >= 2:
            s['tarama_hata'] = f'Tarama {art_arda} kez üst üste başarısız oldu; ilan paylaşımı ve site güncellemesi durmuş olabilir.'
        if son_basarili is None or simdi - zaman(son_basarili['updatedAt']) > TARAMA_EN_GEC:
            s['tarama_durdu'] = 'Son başarılı taramanın üzerinden 100 dakikadan fazla geçti.'
    else:
        s['tarama_durdu'] = 'Tarama kaydı okunamadı.'
    # Takılı çalışmadan SONRA başlayıp başarıyla biten tarama varsa takılma artık sırayı tutmuyor (eski kayıt): uyarılmaz.
    son_basari_bas = max((zaman(c['createdAt']) for c in biten if c['conclusion'] == 'success'), default=None)
    takili = [c for c in tarama if c.get('status') in ('waiting', 'queued')
              and simdi - zaman(c['createdAt']) > timedelta(minutes=30)
              and not (son_basari_bas and son_basari_bas > zaman(c['createdAt']))]
    if takili:
        s['tarama_takildi'] = (f'Bir tarama {int((simdi - zaman(takili[-1]["createdAt"])).total_seconds() // 60)} dakikadır başlamadan '
                               'bekliyor (GitHub tarafında takıldı); arkasındaki taramalar da sırada bekliyor.')
    if sosyal:
        son = next((c for c in sosyal if c.get('status') == 'completed' and c.get('conclusion') != 'cancelled'), None)
        if son and son['conclusion'] == 'failure':
            s['sosyal'] = 'Son sosyal medya paylaşımı başarısız oldu (hiçbir platforma gitmemiş).'
    if zaman_kontrol:
        son = next((c for c in zaman_kontrol if c.get('status') == 'completed' and c.get('conclusion') != 'cancelled'), None)
        if son and son['conclusion'] == 'failure':
            s['tarih_bombasi'] = 'Günlük zaman kontrolü (tarih bombası) düştü; yakında tarama testleri kırılabilir.'
    if site_hata:
        s['site'] = f'Site okunamadı: {site_hata}'
    elif site_guncelleme and simdi - site_guncelleme > SITE_EN_GEC:
        s['site_eski'] = f'Site {int((simdi - site_guncelleme).total_seconds() // 60)} dakikadır güncellenmemiş.'
    geciken = yerel_gecikenler(simdi, kaynak_durumlari)
    if geciken:
        s['yerel_kaynak'] = (f'{" ve ".join(geciken)} ilanları 12 saatten uzun süredir gelmiyor: bilgisayardaki yerel tarayıcı '
                             'çalışmıyor ya da gönderdiği dosya okunamıyor. Yeni ilanlar kaçıyor olabilir.')
    if bekleyen is not None and bekleyen >= 6:
        s['kuyruk'] = f'Telegram sırasında {bekleyen} ilan bekliyor (gönderim takılmış olabilir).'
    return s


def mesajlar(onceki, simdi_sorunlar, simdi, ozet_zamani, ozet):
    """(gidecek mesajlar, yeni durum). onceki: {anahtar: son uyarı zamanı ISO}."""
    giden, yeni = [], {}
    for anahtar, metin in simdi_sorunlar.items():
        son = onceki.get(anahtar)
        if son is None or simdi - zaman(son) >= HATIRLATMA:
            giden.append(('🔴 ' if son is None else '🔁 ') + metin)
            yeni[anahtar] = simdi.isoformat()
        else:
            yeni[anahtar] = son
    for anahtar in onceki:
        if anahtar not in simdi_sorunlar:
            giden.append(f'✅ Düzeldi: {anahtar.replace("_", " ")}')
    if not simdi_sorunlar and ozet_zamani:
        giden.append(ozet)
    return giden, yeni


def telegram(token, sohbet, metin):
    veri = urllib.parse.urlencode({'chat_id': sohbet, 'text': metin, 'disable_web_page_preview': 'true'}).encode()
    with urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=veri), timeout=30) as r:
        return json.load(r).get('ok', False)


def site_oku():
    try:
        req = urllib.request.Request(SITE + 'liste.json?b=' + str(int(datetime.now().timestamp())), headers={'User-Agent': 'kpsstercihi-bekci/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            guncelleme = zaman(json.load(r)['guncelleme'])
            return (guncelleme if guncelleme.tzinfo else guncelleme.replace(tzinfo=TR)), None
    except Exception as hata:
        return None, type(hata).__name__


def depo_oku():
    """Depodaki ilanlar.json: (Telegram sırasındaki ilan sayısı, kaynak durumları); okunamazsa (None, None)."""
    try:
        depo = os.environ.get('GITHUB_REPOSITORY', 'enesfeched-maker/kamu-ilan-takip')
        req = urllib.request.Request(f'https://raw.githubusercontent.com/{depo}/main/docs/ilanlar.json', headers={'User-Agent': 'kpsstercihi-bekci/1.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            veri = json.loads(r.read().decode('utf-8-sig'))
        return len(veri.get('telegram_bekleyen') or []), veri.get('kaynak_durumlari') or {}
    except Exception:
        return None, None


def ozet_metni(tr, guncelleme, bekleyen):
    """Günde iki kez giden 'her şey yolunda' satırı. Site okunamadıysa (guncelleme None) da metin kurulabilmeli:
    11 Kasım 2026'ya kadar bu satır site okunamadığında çöküyor, bekçi tam o anda uyarı atamıyordu."""
    site = f'{guncelleme.astimezone(TR):%H:%M}' if guncelleme else 'okunamadı'
    return f'✅ Sistem sağlıklı ({tr:%H:%M}). Site güncelleme: {site}' + (f', Telegram sırası: {bekleyen}' if bekleyen is not None else '') + '.'


def id_bul(token):
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getMe', timeout=30) as r:
        print('Bot:', '@' + (json.load(r).get('result') or {}).get('username', '?'))
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getWebhookInfo', timeout=30) as r:
        bilgi = json.load(r).get('result') or {}
    print('Webhook:', bilgi.get('url') or 'yok', '| bekleyen güncelleme:', bilgi.get('pending_update_count'))
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getUpdates', timeout=30) as r:
        guncellemeler = json.load(r).get('result') or []
    print('Gelen güncelleme sayısı:', len(guncellemeler), '| türler:', sorted({(g.get('message') or {}).get('chat', {}).get('type') or next(iter([k for k in g if k != 'update_id']), '?') for g in guncellemeler}))
    bulunan = {}
    for g in guncellemeler:
        m = g.get('message') or {}
        sohbet = m.get('chat') or {}
        if sohbet.get('type') == 'private':
            bulunan[sohbet['id']] = ' '.join(x for x in (sohbet.get('first_name'), sohbet.get('last_name'), sohbet.get('username') and '@' + sohbet['username']) if x)
    return bulunan


def ana():
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    if '--id-bul' in sys.argv:
        bulunan = id_bul(token)
        print('Özel sohbetler:', bulunan or 'yok — önce botla Telegram\'da özel konuşma başlatıp /start yaz, sonra yeniden çalıştır.')
        return 0
    if '--test-mesaj' in sys.argv:
        sohbet = os.environ.get('TELEGRAM_YONETICI_ID', '').strip()
        print('Test mesajı:', 'gönderildi' if sohbet and telegram(token, sohbet, 'KPSS Tercihi bekçi\n✅ Test mesajı: bildirimler çalışıyor. Bundan sonra sorun olursa ya da günde iki kez (09.00 ve 21.00) buraya yazacağım.') else 'GÖNDERİLEMEDİ (TELEGRAM_YONETICI_ID tanımlı değil)')
        return 0
    simdi = datetime.now(timezone.utc)
    tarama = calismalar('ilan.yml')
    sosyal = calismalar('sosyal.yml', 4)
    zk = calismalar('zaman-kontrol.yml', 3)
    guncelleme, site_hata = site_oku()
    bekleyen, kaynak_durumlari = depo_oku()
    s = sorunlar(simdi, tarama, sosyal, guncelleme, site_hata, bekleyen, zk, kaynak_durumlari)
    tr = simdi.astimezone(TR)
    ozet_zamani = tr.hour in (9, 21) and tr.minute < 30
    ozet = ozet_metni(tr, guncelleme, bekleyen)
    onceki = json.loads(DURUM.read_text(encoding='utf-8')) if DURUM.exists() else {}
    giden, yeni = mesajlar(onceki, s, simdi, ozet_zamani, ozet)
    print('Sorunlar:', s or 'yok', '| gidecek mesaj:', len(giden))
    if '--deneme' in sys.argv:
        for g in giden:
            print('  (gönderilmedi)', g)
        return 0
    sohbet = os.environ.get('TELEGRAM_YONETICI_ID', '').strip()
    if giden and token and sohbet:
        for g in giden:
            telegram(token, sohbet, 'KPSS Tercihi bekçi\n' + g)
    elif giden:
        print('Uyarı: TELEGRAM_YONETICI_ID tanımlı değil; mesaj gönderilemedi.')
    DURUM.write_text(json.dumps(yeni), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(ana())
