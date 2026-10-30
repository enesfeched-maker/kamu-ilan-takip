"""Claude ile ilan okuma (30 Ekim 2026, kullanıcı kararı: "aceleden ziyade doğruluk").

Claude Code bulut rutini 2 saatte bir çalışır (talimat: bot/yz_claude_talimat.md):
  1. python bot/yz_claude.py hazirla   -> okunacak ilanlar ve belgeleri yz-is/ klasörüne (gorevler.json)
  2. Claude her belgeyi okur, yz-is/<anahtar>.json yazar (biçim talimatta)
  3. python bot/yz_claude.py kaydet    -> sonuçlar denetilip denetim/yz.json'a işlenir
  4. rutin denetim/yz.json'u yeni bir yz-okuma-<zaman> dalına gönderir (force-push yok);
     .github/workflows/yz-okuma-al.yml main'e birleştirip dalı siler.
Site ve Telegram yz_isle.uygula ile bu veriyi kullanır; elle düzeltmeler yine üstte. Telegram yeni ilanı Claude okuyana
kadar en çok yz_isle.EN_COK_BEKLEME bekletir, sonra botun verisiyle gönderir."""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IS = ROOT / 'yz-is'
YZ = ROOT / 'denetim' / 'yz.json'
MODEL = 'claude'


def anahtar(kimlik):
    return hashlib.sha1(str(kimlik).encode()).hexdigest()[:16]


def _oku_json(yol, varsayilan):
    try:
        return json.loads(Path(yol).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return varsayilan


def hazirla(en_cok=12, simdi=None, klasor=IS, ilan_yolu=ROOT / 'docs' / 'ilanlar.json', yz_yolu=YZ, metin=None):
    import yz_isle
    import yz_yerel
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    kayitlar = _oku_json(ilan_yolu, {})
    veri = _oku_json(yz_yolu, {})
    metin = metin or (lambda i: yz_yerel.metin_al(i))
    klasor = Path(klasor)
    shutil.rmtree(klasor, ignore_errors=True)
    klasor.mkdir(parents=True)
    gorevler = []
    for item in yz_isle.adaylar(kayitlar.get('ilanlar') or [], set(kayitlar.get('telegram_bekleyen') or []), veri, simdi):
        if len(gorevler) >= en_cok:
            break
        govde, kaynak = metin(item)
        if kaynak == 'bekle':
            continue
        a = anahtar(item['id'])
        g = {'id': item['id'], 'kurum': item.get('kurum'), 'baslik': item.get('baslik'), 'kaynak': kaynak,
             'bot_son_tarih': item.get('son_tarih'), 'bot_kadro': item.get('kadro'),
             'cikti': str(klasor / f'{a}.json')}
        if govde:
            (klasor / f'{a}.txt').write_text(govde, encoding='utf-8')
            g['metin'] = str(klasor / f'{a}.txt')
        if kaynak in ('pdf', 'taranmis'):
            import yz_denetim as yd
            pdf = yz_yerel._sbb_pdf(item) or (None if kaynak == 'pdf' else yd._csb_pdf(item))
            if pdf:
                (klasor / f'{a}.pdf').write_bytes(pdf)
                g['pdf'] = str(klasor / f'{a}.pdf')
        if 'metin' not in g and 'pdf' not in g:
            continue
        gorevler.append(g)
    (klasor / 'gorevler.json').write_text(json.dumps(gorevler, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(gorevler)} ilan okunacak; liste: {klasor / "gorevler.json"}')
    for g in gorevler:
        print(f'- {g["kurum"]} — {str(g["baslik"])[:70]} ({g["kaynak"]}) -> {g["cikti"]}')
    return gorevler


def dogrula(yz):
    """Claude çıktısının en az biçimi; sorun listesi (boşsa geçerli)."""
    sorun = []
    if not isinstance(yz, dict):
        return ['JSON nesnesi değil']
    if not isinstance(yz.get('kadrolar'), list):
        sorun.append('kadrolar listesi yok')
    for k in yz.get('kadrolar') or []:
        if not isinstance(k, dict) or not str(k.get('unvan') or '').strip():
            sorun.append('unvansız kadro')
        elif k.get('adet') is not None and not isinstance(k.get('adet'), int):
            sorun.append(f'{k["unvan"]}: adet sayı değil')
    if yz.get('son_basvuru_tarihi') and not str(yz['son_basvuru_tarihi'])[:10].count('-') == 2:
        sorun.append('son_basvuru_tarihi YYYY-AA-GG değil')
    return sorun


def kaydet(simdi=None, klasor=IS, ilan_yolu=ROOT / 'docs' / 'ilanlar.json', yz_yolu=YZ):
    import yz_yerel
    from site_uret import TR
    simdi = (simdi or datetime.now(TR)).astimezone(TR)
    ilanlar = {i['id']: i for i in _oku_json(ilan_yolu, {}).get('ilanlar') or []}
    gorevler = _oku_json(Path(klasor) / 'gorevler.json', [])
    yeni = {}
    for g in gorevler:
        item = ilanlar.get(g['id'])
        cikti = _oku_json(g['cikti'], None)
        if not item or cikti is None:
            print(f'Atlandı (çıktı yok): {g.get("kurum")} — {str(g.get("baslik"))[:60]}')
            continue
        sorun = dogrula(cikti)
        if sorun:
            print(f'Atlandı ({"; ".join(sorun)}): {g.get("kurum")} — {str(g.get("baslik"))[:60]}')
            continue
        yz = yz_yerel.temizle(cikti, item, guvenilir=True)
        kaynak = 'pdf-gorsel' if g['kaynak'] == 'taranmis' else g['kaynak']   # Claude taranmış belgeyi görüntüden okur
        yeni[item['id']] = yz_yerel.kayit(item, yz, kaynak, MODEL, simdi)
        yeni[item['id']]['model'] = MODEL
        print(f'Kaydedildi: {g.get("kurum")} — {str(g.get("baslik"))[:60]}'
              + (f' · botla fark: {yeni[item["id"]]["farklar"]}' if yeni[item['id']]['farklar'] else ''))
    if yeni:
        Path(yz_yolu).parent.mkdir(parents=True, exist_ok=True)
        Path(yz_yolu).write_text(json.dumps(yz_yerel.birlestir(_oku_json(yz_yolu, {}), yeni), ensure_ascii=False,
                                            indent=1) + '\n', encoding='utf-8')
    print(f'Claude okuması: {len(yeni)} ilan kaydedildi.')
    return yeni


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    p = argparse.ArgumentParser()
    p.add_argument('komut', choices=['hazirla', 'kaydet'])
    p.add_argument('--en-cok', type=int, default=12)
    a = p.parse_args()
    hazirla(a.en_cok) if a.komut == 'hazirla' else kaydet()
