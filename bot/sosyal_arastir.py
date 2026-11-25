"""Rakip ve konu araştırması: YouTube ve TikTok'un herkese açık verisini ücretsiz okur (yt-dlp, anahtar gerekmez).

.claude/skills altındaki ustun-video, rakip-yorum ve konu-nabzi becerileri bu betiği veri katmanı olarak kullanır:
  videolar <kaynak> [--adet 30]   bir hesabın son videoları + kendi ortalamasına göre kat (kaynak: YouTube @ad,
                                  kanal adresi ya da kimliği; TikTok için tt:@ad ya da profil adresi)
  rakipler [--adet 30] [--hepsi]  sosyal/rakipler.json'daki tüm hesaplar; ortalamasının en az 2 katı tutan, KPSS/kamu
                                  konulu videolar (--hepsi konu süzgecini kapatır)
  yorumlar <youtube-adresi> [--adet 200]   en beğenilen yorumlar, kaba etiketlerle (soru/puan/kurum/kpsssiz)
  ara <sorgu> [--adet 20] [--yeni]         YouTube araması; --yeni en yeni yüklenenleri getirir

Çıktı JSON olarak sosyal-is/arastirma/ altına yazılır (git'e girmez) ve kısa özet ekrana basılır.
Depo herkese açık: yorum sahiplerinin adı hiçbir çıktıya yazılmaz, yorum metni depoya işlenmez.
TikTok yorumları bu betikte yok; yerel oturumda vidIQ'nun tiktok_comment_list aracı kullanılır."""
import argparse
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAKIP_YOLU = ROOT / 'sosyal' / 'rakipler.json'
CIKTI = ROOT / 'sosyal-is' / 'arastirma'
BASLIK = {'Accept-Language': 'tr-TR,tr;q=0.9'}   # olmazsa YouTube başlıkları İngilizceye çevrilmiş gelir
USTUN_KAT = 2.0

SORU_KELIME = re.compile(r'\b(m[ıiuü]|m[ıiuü]y[ıiuü]m|m[ıiuü]s[ıiuü]n|nas[ıi]l|ka[çc]|nereye|nerelere|nerede|hangi|ne zaman|neden|'
                         r'niye|ne gelir|gelir ?mi|olur ?mu|do[ğg]ru ?mu|[şs]ans[ıi]m)\b', re.I)
ADRES = re.compile(r'https?://\S+')
PUAN = re.compile(r'\b([4-9]\d|100)(?:[.,]\d+)?\s*(?:puan|p\b)', re.I)
KURUM = re.compile(r'sa[ğg]l[ıi]k|adalet|emniyet|milli e[ğg]itim|meb|[çc]sb|sgk|diyanet|belediye|hastane|tapu|pttt?|tcdd|[üu]niversite', re.I)
KPSSSIZ = re.compile(r'kpss\s*(?:siz|şartı olmayan|olmadan)|i[şs][çc]i al[ıi]m', re.I)
# rakipler listesinde konu dışı videoları (tarih, yemek vb.) eler; --hepsi ile kapatılır
KONU = re.compile(r'kpss|atan|atama|al[ıi]m|memur|bakanl[ıi]|puan|tercih|i[şs][çc]i|s[öo]zle[şs]meli|kadro|[öo]sym|ba[şs]vur|'
                  r'kamu|personel|maa[şs]|lisans|[öo]nlisans|ortaö[ğg]retim|tayin|m[üu]lakat|i[şs]kur', re.I)


def konuyla_ilgili(v):
    return bool(KONU.search(v.get('baslik') or ''))


# ---------------------------------------------------------------- saf işlevler (test edilir)
def kaynak_coz(kaynak):
    """Kullanıcı girdisini (platform, adres) çiftine çevirir."""
    k = kaynak.strip()
    if k.startswith('tt:'):
        return 'tiktok', 'https://www.tiktok.com/@' + k[3:].lstrip('@')
    if 'tiktok.com' in k:
        return 'tiktok', k
    if k.startswith('http'):
        return 'youtube', k.rstrip('/')
    if k.startswith('@'):
        return 'youtube', 'https://www.youtube.com/' + k
    if re.fullmatch(r'UC[\w-]{22}', k):
        return 'youtube', 'https://www.youtube.com/channel/' + k
    raise ValueError(f'tanınmayan kaynak: {kaynak}')


def kat_hesapla(videolar):
    """Her videoya 'kat' ekler: izlenme / hesabın medyan izlenmesi. Ölçüsüz videolar medyana girmez."""
    sayilar = [v['izlenme'] for v in videolar if v.get('izlenme')]
    medyan = statistics.median(sayilar) if sayilar else 0
    for v in videolar:
        v['kat'] = round(v['izlenme'] / medyan, 2) if medyan and v.get('izlenme') else None
    return medyan


def ustunler(videolar, esik=USTUN_KAT):
    return sorted((v for v in videolar if (v.get('kat') or 0) >= esik), key=lambda v: -v['kat'])


def yorum_etiketle(metin):
    etiket = []
    if '?' in metin or SORU_KELIME.search(metin):
        etiket.append('soru')
    if PUAN.search(metin):
        etiket.append('puan')
    if KURUM.search(metin):
        etiket.append('kurum')
    if KPSSSIZ.search(metin):
        etiket.append('kpsssiz')
    return etiket


def yorum_temizle(ham):
    """yt-dlp yorumundan yalnız metin, beğeni ve etiket kalır; yazar adı ve kimliği atılır. Yanıtlar ve kopyalar elenir."""
    gorulen, sonuc = set(), []
    for c in ham:
        if c.get('parent') not in (None, 'root'):
            continue
        metin = re.sub(r'\s+', ' ', ADRES.sub('[bağlantı]', c.get('text') or '')).strip()
        if metin.count('[bağlantı]') >= 2:   # uygulama/kanal tanıtımı, soru değil
            continue
        anahtar = metin.lower()
        if len(metin) < 3 or anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        sonuc.append({'metin': metin, 'begeni': c.get('like_count') or 0, 'etiket': yorum_etiketle(metin)})
    return sorted(sonuc, key=lambda y: -y['begeni'])


def _tarih(e):
    if e.get('upload_date'):
        return f"{e['upload_date'][:4]}-{e['upload_date'][4:6]}-{e['upload_date'][6:]}"
    if e.get('timestamp'):
        return datetime.fromtimestamp(e['timestamp']).strftime('%Y-%m-%d')
    return None


def video_ozet(e, platform):
    adres = e.get('url') or e.get('webpage_url') or ''
    if platform == 'youtube' and e.get('id') and not adres.startswith('http'):
        adres = 'https://www.youtube.com/watch?v=' + e['id']
    return {'baslik': (e.get('title') or e.get('description') or '').strip()[:200], 'izlenme': e.get('view_count'),
            'yorum': e.get('comment_count'), 'sure': e.get('duration'), 'tarih': _tarih(e), 'adres': adres,
            'kanal': e.get('channel') or e.get('uploader')}


# ---------------------------------------------------------------- ağ (yt-dlp)
def _ydl(turkce=False, **ek):
    """turkce=True başlıkları Türkçe getirir ama izlenmeler bozulur ("125 B" = bin, yt-dlp milyar okur);
    bu yüzden sayılar her zaman İngilizce arayüzden, başlıklar Türkçe ayrı istekten alınır."""
    try:
        import yt_dlp
    except ImportError:
        sys.exit('yt-dlp kurulu değil: python -m pip install -q yt-dlp')
    ayar = {'quiet': True, 'no_warnings': True, 'skip_download': True,
            'http_headers': BASLIK if turkce else {'Accept-Language': 'en-US,en;q=0.9'},
            'extractor_args': {'youtube': {'lang': ['tr' if turkce else 'en']}}}
    if 'extractor_args' in ek:
        ayar['extractor_args']['youtube'].update(ek.pop('extractor_args')['youtube'])
    ayar.update(ek)
    return yt_dlp.YoutubeDL(ayar)


def _girdiler(adres, adet):
    """Sayılar İngilizce istekten; YouTube'da başlıklar ikinci, Türkçe istekle kimliğe göre değiştirilir."""
    with _ydl(extract_flat=True, playlistend=adet) as y:
        r = y.extract_info(adres, download=False)
    girdiler = [e for e in (r.get('entries') or []) if e][:adet]
    if 'youtube' in adres or adres.startswith('ytsearch'):
        try:
            with _ydl(turkce=True, extract_flat=True, playlistend=adet) as y:
                tr = y.extract_info(adres, download=False)
            basliklar = {e.get('id'): e.get('title') for e in (tr.get('entries') or []) if e}
            for e in girdiler:
                e['title'] = basliklar.get(e.get('id')) or e.get('title')
            r['channel'] = tr.get('channel') or r.get('channel')
        except Exception:
            pass   # Türkçe başlık alınamazsa İngilizce kalır
    return girdiler, r


def hesap_videolari(kaynak, adet=30):
    platform, adres = kaynak_coz(kaynak)
    if platform == 'tiktok':
        girdiler, r = _girdiler(adres, adet)
        ad = r.get('uploader') or adres.rsplit('@', 1)[-1]
        videolar = [video_ozet(e, platform) for e in girdiler]
    else:
        videolar, ad = [], None
        for sekme in ('/shorts', '/videos'):
            try:
                girdiler, r = _girdiler(adres + sekme, adet)
            except Exception as hata:   # kanalda sekme yoksa yt-dlp hata verir
                print(f'  ({sekme} okunamadı: {str(hata)[:80]})', file=sys.stderr)
                continue
            ad = ad or r.get('channel') or r.get('uploader')
            for e in girdiler:
                v = video_ozet(e, platform)
                v['bicim'] = 'shorts' if sekme == '/shorts' else 'uzun'
                videolar.append(v)
        # Shorts ile uzun videonun izlenmesi farklı ölçekte; kat her biçimin kendi medyanına göre hesaplanır.
        for bicim in ('shorts', 'uzun'):
            kat_hesapla([v for v in videolar if v.get('bicim') == bicim])
    if platform == 'tiktok':
        kat_hesapla(videolar)
    medyan = {}
    for v in videolar:
        medyan.setdefault(v.get('bicim', 'tiktok'), []).append(v['izlenme'] or 0)
    return {'platform': platform, 'kaynak': kaynak, 'ad': ad or kaynak, 'videolar': videolar,
            'medyan': {b: int(statistics.median(s)) for b, s in medyan.items() if s}}


def video_yorumlari(adres, adet=200):
    ek = {'getcomments': True, 'extractor_args': {'youtube': {'max_comments': [str(adet), 'all', '0'], 'comment_sort': ['top']}}}
    with _ydl(**ek) as y:
        e = y.extract_info(adres, download=False)
    return {'video': video_ozet(e, 'youtube'), 'yorumlar': yorum_temizle(e.get('comments') or [])}


def youtube_ara(sorgu, adet=20, yeni=False):
    if yeni:   # yt-dlp'nin ytsearchdate öneki kaldırıldı; arama sayfasının "yükleme tarihi" sıralaması (sp=CAI=) kullanılır
        from urllib.parse import quote_plus
        adres = f'https://www.youtube.com/results?search_query={quote_plus(sorgu)}&sp=CAI%3D'
    else:
        adres = f'ytsearch{adet}:{sorgu}'
    girdiler, _ = _girdiler(adres, adet)
    return [video_ozet(e, 'youtube') for e in girdiler]


# ---------------------------------------------------------------- komutlar
def _kaydet(ad, veri):
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / f"{datetime.now():%Y-%m-%d}-{ad}.json"
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nKaydedildi: {yol.relative_to(ROOT)}')


def _satir(v):
    kat = f"{v['kat']:>5}x" if v.get('kat') else '    -'
    return f"{kat} {v.get('izlenme') or 0:>9,} {v.get('tarih') or '':10} {v.get('bicim', ''):6} {v['baslik'][:80]}"


def _dosya_adi(metin):
    metin = metin.translate(str.maketrans('ıİşŞğĞüÜöÖçÇ', 'iisSgGuUoOcC')).lower()
    return re.sub(r'[^a-z0-9]+', '-', metin)[:40].strip('-') or 'kaynak'


def komut_videolar(a):
    h = hesap_videolari(a.kaynak, a.adet)
    print(f"{h['ad']} ({h['platform']}) — medyan izlenme: {h['medyan']}")
    for v in sorted(h['videolar'], key=lambda v: -(v.get('kat') or 0)):
        print(_satir(v))
    _kaydet('videolar-' + _dosya_adi(h['ad']), h)


def komut_rakipler(a):
    rakipler = json.loads(RAKIP_YOLU.read_text(encoding='utf-8'))['hesaplar']
    hesaplar, hepsi = [], []
    for r in rakipler:
        try:
            h = hesap_videolari(r['kaynak'], a.adet)
        except Exception as hata:
            print(f"! {r['ad']}: {str(hata)[:120]}", file=sys.stderr)
            continue
        h['ad'] = r['ad']
        hesaplar.append(h)
        for v in ustunler(h['videolar']):
            if not a.hepsi and not konuyla_ilgili(v):
                continue
            hepsi.append(dict(v, hesap=r['ad'], platform=h['platform']))
    hepsi.sort(key=lambda v: -v['kat'])
    print(f"{len(hesaplar)} hesap okundu; ortalamasının en az {USTUN_KAT:g} katı tutan {len(hepsi)} video:")
    for v in hepsi:
        print(f"{v['hesap'][:18]:18} " + _satir(v))
    _kaydet('rakipler', {'hesaplar': hesaplar, 'ustunler': hepsi})


def komut_yorumlar(a):
    s = video_yorumlari(a.adres, a.adet)
    ys = s['yorumlar']
    sayac = {}
    for y in ys:
        for e in y['etiket']:
            sayac[e] = sayac.get(e, 0) + 1
    print(f"{s['video']['baslik']} — {s['video']['izlenme']:,} izlenme, {len(ys)} yorum okundu; etiketler: {sayac}")
    for y in ys[:a.goster]:
        print(f"- [{y['begeni']}] {','.join(y['etiket']) or '-'}: {y['metin'][:160]}")
    _kaydet('yorumlar-' + _dosya_adi(s['video']['baslik']), s)


def komut_ara(a):
    sonuc = youtube_ara(a.sorgu, a.adet, a.yeni)
    for v in sonuc:
        print(f"{v.get('izlenme') or 0:>9,}  {(v.get('kanal') or '')[:20]:20} {v['baslik'][:90]}")
    _kaydet('ara-' + _dosya_adi(a.sorgu), {'sorgu': a.sorgu, 'yeni': a.yeni, 'videolar': sonuc})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = p.add_subparsers(dest='komut', required=True)
    k = alt.add_parser('videolar'); k.add_argument('kaynak'); k.add_argument('--adet', type=int, default=30); k.set_defaults(f=komut_videolar)
    k = alt.add_parser('rakipler'); k.add_argument('--adet', type=int, default=30)
    k.add_argument('--hepsi', action='store_true', help='konu dışı videoları da göster'); k.set_defaults(f=komut_rakipler)
    k = alt.add_parser('yorumlar'); k.add_argument('adres'); k.add_argument('--adet', type=int, default=200)
    k.add_argument('--goster', type=int, default=40); k.set_defaults(f=komut_yorumlar)
    k = alt.add_parser('ara'); k.add_argument('sorgu'); k.add_argument('--adet', type=int, default=20)
    k.add_argument('--yeni', action='store_true'); k.set_defaults(f=komut_ara)
    a = p.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    a.f(a)


if __name__ == '__main__':
    main()
