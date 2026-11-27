"""Kancalı puan videoları (27 Kasım 2026): günün ana sosyal paylaşımları (öğle ve akşam) bu biçimle çıkar.

Neden: 1–25 Kasım ölçümünde elle yazılmış puan kancalı videolar ("KPSS'de 85-90 şart değil", "Önlisansta 64,45 ile
atanan var") Instagram'da 306 bin ve 5,7 bin izlendi; şablon videoların medyanı 290–585'te kaldı. Kullanıcı kararı:
"özel kancalı videolara geçelim". Bu modül o kalıbı veriden, her gün kendiliğinden kurar.

Diziler (sırayla döner; verisi yetmeyen ya da yakında yapılan atlanır):
  puanla  Şu an açık ilanlarda en düşük puan şartı ("KPSS'de 85-90 şart değil")          -> docs/ilanlar.json yz_kadrolar
  atanan  ÖSYM son dönemde en düşük taban puanla atanılanlar ("Önlisansta 64,45 ile atanan var") -> docs/puanlar/<düzey>.json
  aralik  "70–75 puanla nereye atanılır?" (puan aralığındaki yerleşmeler)                     -> docs/puanlar/<düzey>.json

Sayıların hepsi veriden; tahmin yok. Kadroların puan şartı yalnız her kadroda 1–100 arası sayı varsa kullanılır.
Kullanım (önizleme): python bot/kanca.py puanla|atanan|aralik [--cikti klasör]"""
import argparse
from datetime import timedelta
from pathlib import Path

from PIL import ImageDraw

import kart_tasarimlari as k
import reels
from kart_tasarimlari import AYLAR, F
from reels import ALT, SAG, SOL, Oge, Sahne, hap, panel, yazi

ROOT = Path(__file__).resolve().parent.parent
DIZILER = ('puanla', 'atanan', 'aralik')
TEKRAR_GUN = {'puanla': 4, 'atanan': 9, 'aralik': 6}   # aynı dizi (aynı düzey/aralık) en erken bu kadar gün sonra
PUANLA_EN_AZ, PUANLA_SINIR, PUANLA_GOSTER = 4, 70, 8   # en az 4 ilan, puan şartı <= 70, en çok 8 satır
ATANAN_SATIR = 8
ARALIK_EN_AZ, ARALIK_GOSTER = 6, 8
DUZEYLER = (('onlisans', 'Önlisans', 'ÖNLİSANSTA'), ('ortaogretim', 'Ortaöğretim', 'LİSEDE'), ('lisans', 'Lisans', 'LİSANSTA'))
BULUNMA = {'onlisans': 'Önlisansta', 'ortaogretim': 'Lisede', 'lisans': 'Lisansta'}
ARALIKLAR = (('lisans', 70), ('onlisans', 70), ('ortaogretim', 70), ('lisans', 65), ('onlisans', 65),
             ('lisans', 75), ('ortaogretim', 65), ('onlisans', 75), ('lisans', 60))
PALETLER = ('kagit', 'bordo')   # onaylı sıra; yeşil yok
SORULAR = {
    'puanla': ['Puanın ve mezuniyetin ne? Yorumlara yaz 👇', 'Sen kaç puanla başvuracaksın? 👇'],
    'atanan': ['Senin puanın bu listeye yetiyor mu? 👇', 'Listede seni şaşırtan bir kadro oldu mu? 👇'],
    'aralik': ['Senin puanın bu aralıkta mı? 👇', 'Hangi kadroyu tercih ederdin? 👇'],
}
KAPANIS = 'Tüm ilanlar ve taban puanları kpsstercihi.com\'da 💛\nTakipte kal: yeni ilan çıkınca ilk sen gör.'


# ---------------------------------------------------------------- veri
def puan_yaz(x):
    return (f'{x:.2f}' if isinstance(x, float) and x != int(x) else str(int(x))).replace('.', ',')


def _gecerli_puan(p):
    return not isinstance(p, bool) and isinstance(p, (int, float)) and 1 <= p <= 100


def puan_sartlari(acik, simdi):
    """[(puan, ilan, kadro adı)] her ilandan en düşük puan şartlı kadro; puanı belli olmayan ilan girmez."""
    sonuc = []
    for i in acik:
        kadrolar = [x for x in (i.get('yz_kadrolar') or []) if isinstance(x, dict) and _gecerli_puan(x.get('en_dusuk_puan'))]
        if not kadrolar:
            continue
        en = min(kadrolar, key=lambda x: (x['en_dusuk_puan'], x.get('unvan') or ''))
        sonuc.append((en['en_dusuk_puan'], i, (en.get('unvan') or '').split(' — ')[0].strip() or 'Personel'))
    return sorted(sonuc, key=lambda x: (x[0], -(k.veri(x[1], None, simdi)['toplam'] or 0), x[1].get('id') or ''))


# ---------------------------------------------------------------- sahneler
def _baslik(ust, satirlar, y=420, bas=0.0):
    R = reels.R
    o = [Oge(hap(ust, R.panel, R.yazi, 40, cizgi=R.vurgu), SOL, y, bas, 'buyu')]
    y += 140
    for n, s in enumerate(satirlar):
        kat = reels.sigan_yazi(s, [132, 116, 100, 88], SAG - SOL, 1, R.vurgu if n == len(satirlar) - 1 else R.yazi)
        o.append(Oge(kat, SOL, y, bas + 0.1 + 0.08 * n, 'sol'))
        y += kat.height + 6
    return o, y


def _satir(ust, alt, sag, sag_alt, w=SAG - SOL, h=200):
    """Satır: solda iki satır (kadro / kurum · yer), sağda iri puan ve altında küçük etiket."""
    R = reels.R
    kutu = panel(w, h, yaricap=36)
    d = ImageDraw.Draw(kutu)
    pw = round(d.textlength(sag, font=F(72, True)))
    d.text((w - 40, h / 2 - 14), sag, font=F(72, True), fill=R.vurgu, anchor='rm')
    d.text((w - 40, h / 2 + 44), sag_alt, font=F(28, True), fill=R.soluk, anchor='rm')
    gen = w - 80 - pw - 40
    s, yz = k.sigdir(d, ust, True, [44, 40, 36], gen, 2)
    ara = round(yz.size * 1.12)
    y = (h - (len(s) * ara + 44)) / 2
    k.blok(d, 40, y, s, yz, R.yazi, aralik=ara)
    d.text((40, y + len(s) * ara + 6), k.lines(d, alt, F(30), gen, 1)[0], font=F(30), fill=R.soluk)
    return kutu


def _liste_sahneleri(satirlar, baslik, dipnot):
    """4'erli satır sahneleri."""
    R = reels.R
    sahneler = []
    for s in range(0, len(satirlar), 4):
        parca = satirlar[s:s + 4]
        o = [Oge(yazi(baslik, 56, R.vurgu), SOL, 400, 0.0, 'sol'),
             Oge(hap(f'{s + 1}–{s + len(parca)}', R.panel, R.soluk, 34, cizgi=R.cizgi), SAG - 150, 404, 0.0)]
        for m, kat in enumerate(parca):
            o.append(Oge(kat, SOL, 500 + m * 226, 0.15 + m * 0.18))
        if dipnot:
            o.append(Oge(yazi(dipnot, 32, R.soluk, False, genislik=SAG - SOL, satir=1), SOL, min(500 + 4 * 226, ALT - 40), 0.9))
        sahneler.append(Sahne(1.8 + 0.7 * len(parca), o))
    return sahneler


def _kisa_kurum(ilan):
    return reels.kisa_kurum(ilan)


def puanla_konusu(acik, simdi, docs=None):
    sartlar = [x for x in puan_sartlari(acik, simdi) if x[0] <= PUANLA_SINIR]
    if len(sartlar) < PUANLA_EN_AZ:
        return None
    R = reels.R
    t = sartlar[0][0]
    ay = f'{AYLAR[simdi.month - 1]} {simdi.year}'
    o, y = _baslik(f'ŞU AN AÇIK İLANLAR · {k.tr_buyuk(ay)}', ["KPSS'DE 85–90", 'ŞART DEĞİL'])
    o.append(Oge(yazi('En düşük puan şartı', 52, R.yazi), SOL, y + 40, 0.35, 'sol'))
    o.append(Oge(yazi(puan_yaz(t), 260, R.vurgu), SOL, y + 110, 0.45, 'yukari'))
    o.append(Oge(yazi(f'{len(sartlar)} ilanda {PUANLA_SINIR} ve altı puan yetiyor', 44, R.soluk, genislik=SAG - SOL, satir=2),
                 SOL, y + 440, 0.6))
    sahneler = [Sahne(3.0, o)]
    goster = sartlar[:PUANLA_GOSTER]
    satirlar = []
    for p, i, ad in goster:
        b = _bitis(i)
        alt = _kisa_kurum(i) + (f' · son gün {b.day} {AYLAR[b.month - 1]}' if b else '')
        satirlar.append(_satir(ad, alt, puan_yaz(p), 'en az'))
    sahneler += _liste_sahneleri(satirlar, 'BU PUANLA BAŞVURU', 'Puan şartı ilan metninden; diğer şartlar ilanda')
    sahneler.append(reels.kapanis_sahnesi('Şartların tamamı ve başvuru'))
    ilk = ', '.join(f'{_kisa_kurum(i)} {puan_yaz(p)}' for p, i, _ in goster[:3])
    return {'tur': 'kanca', 'seri': 'puanla', 'muzik': 'sabah', 'anahtar': f'kanca:puanla:{simdi.date()}',
            'ilanlar': [i['id'] for _, i, _ in goster],
            'baslik': f'KPSS {puan_yaz(t)} Puanla Başvurulabilen İlanlar · {ay}',
            'giris': f"KPSS'de 85-90 şart değil. Şu an açık ilanlarda en düşük puan şartı {puan_yaz(t)}. {ilk}.",
            'satirlar': [f'• {_kisa_kurum(i)}: {ad} ({puan_yaz(p)})' for p, i, ad in goster[:6]],
            'etiketler': ['#kpss', '#memuralımı', '#kpss2026'], 'sorular': SORULAR['puanla'], 'kapanis': KAPANIS,
            'sahneler': sahneler}


def _bitis(i):
    from site_uret import _bitis as b
    return b(i)


def _puan_kayitlari(docs, duzey):
    from sosyal_motor import _puan_verisi
    return _puan_verisi(Path(docs or ROOT / 'docs'), duzey)


def _yer(r):
    import haftalik
    il = haftalik.basliga(r.get('il')) if r.get('il') else ''
    return haftalik._kisa(r.get('kurum')) + (f' · {il}' if il else '')


def atanan_konusu(acik, simdi, docs=None, duzey=None):
    import haftalik
    from puan_sayfalari import donem_yaz
    kod, ad, yer = next(d for d in DUZEYLER if d[0] == duzey) if duzey else DUZEYLER[0]
    donem, kayitlar = _puan_kayitlari(docs, kod)
    liste = haftalik.en_dusukler(kayitlar, ATANAN_SATIR)
    if not donem or len(liste) < ATANAN_SATIR:
        return None
    R = reels.R
    dy = donem_yaz(donem)
    en = liste[0]
    o, y = _baslik(f'KPSS {dy} · ÖSYM SONUÇLARI', [yer, f'{puan_yaz(en["min"])} İLE', 'ATANAN VAR'])
    o.append(Oge(yazi(f'{haftalik.basliga(en["unvan"])} · {_yer(en)}', 44, R.yazi, genislik=SAG - SOL, satir=2), SOL, y + 40, 0.5))
    o.append(Oge(yazi('Puanım düşük deyip vazgeçme', 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 190, 0.65))
    sahneler = [Sahne(3.0, o)]
    satirlar = [_satir(haftalik.basliga(r['unvan']), _yer(r), puan_yaz(r['min']), 'taban') for r in liste]
    sahneler += _liste_sahneleri(satirlar, 'EN DÜŞÜK TABANLAR', f'Kaynak: ÖSYM KPSS {dy} sayısal bilgiler')
    sahneler.append(reels.kapanis_sahnesi('Tercih yaparken işine yarayabilir'))
    return {'tur': 'kanca', 'seri': 'atanan', 'muzik': 'sabah', 'anahtar': f'kanca:atanan:{kod}:{donem}:{simdi.date()}',
            'ilanlar': [],
            'baslik': f'{BULUNMA[kod]} {puan_yaz(en["min"])} ile atanan var · KPSS {dy} en düşük tabanlar',
            'giris': f'📊 KPSS {dy} {ad.lower()} yerleştirmesinde en düşük taban puan {puan_yaz(en["min"])}: '
                     f'{haftalik.basliga(en["unvan"])}, {_yer(en)}. En düşük puanla atanılan kadrolar:',
            'satirlar': [f'• {haftalik.basliga(r["unvan"])}, {_yer(r)}: {puan_yaz(r["min"])}' for r in liste[:6]],
            'etiketler': ['#kpss', '#tabanpuan', f'#kpss{kod}'], 'sorular': SORULAR['atanan'], 'kapanis': KAPANIS,
            'sahneler': sahneler}


def aralik_konusu(acik, simdi, docs=None, secim=None):
    import haftalik
    from puan_sayfalari import donem_yaz
    kod, alt = secim or ARALIKLAR[0]
    ust = alt + 5
    ad = next(d[1] for d in DUZEYLER if d[0] == kod)
    donem, kayitlar = _puan_kayitlari(docs, kod)
    bant = haftalik.puan_bandi(kayitlar, alt, ust)
    if not donem or len(bant) < ARALIK_EN_AZ:
        return None
    # aynı unvan listeyi doldurmasın; aralığa yayılsın diye eşit adımla seçilir
    tekil, gorulen = [], set()
    for r in bant:
        if r['unvan'] not in gorulen:
            gorulen.add(r['unvan'])
            tekil.append(r)
    if len(tekil) < ARALIK_EN_AZ:
        return None
    adim = max(1, len(tekil) // ARALIK_GOSTER)
    liste = tekil[::adim][:ARALIK_GOSTER]
    R = reels.R
    dy = donem_yaz(donem)
    o, y = _baslik(f'KPSS {dy} · {k.tr_buyuk(ad)}', [f'{alt}–{ust} PUANLA', 'NEREYE', 'ATANILIR?'])
    o.append(Oge(yazi(f'{len(bant)} yerleşme bu aralıkta', 56, R.yazi), SOL, y + 50, 0.4, 'sol'))
    o.append(Oge(yazi('Listede kendi puanını ara', 46, R.soluk, genislik=SAG - SOL, satir=1), SOL, y + 140, 0.6))
    sahneler = [Sahne(3.0, o)]
    satirlar = [_satir(haftalik.basliga(r['unvan']), _yer(r), puan_yaz(r['min']), 'taban') for r in liste]
    sahneler += _liste_sahneleri(satirlar, f'{alt}–{ust} ARASI', f'Kaynak: ÖSYM KPSS {dy} sayısal bilgiler')
    sahneler.append(reels.kapanis_sahnesi('Puanına göre tüm liste sitede'))
    return {'tur': 'kanca', 'seri': 'aralik', 'muzik': 'sabah', 'anahtar': f'kanca:aralik:{kod}:{alt}:{donem}:{simdi.date()}',
            'ilanlar': [],
            'baslik': f'KPSS {ad} {alt}-{ust} Puanla Nereye Atanılır? ({dy})',
            'giris': f'📊 KPSS {dy} {ad.lower()} yerleştirmesinde {alt}–{ust} puan aralığında {len(bant)} yerleşme var. '
                     f'Bu puanla atanılan kadrolardan bazıları:',
            'satirlar': [f'• {haftalik.basliga(r["unvan"])}, {_yer(r)}: {puan_yaz(r["min"])}' for r in liste[:6]],
            'etiketler': ['#kpss', '#kpsstercih', f'#kpss{kod}'], 'sorular': SORULAR['aralik'], 'kapanis': KAPANIS,
            'sahneler': sahneler}


# ---------------------------------------------------------------- seçim
def _yakin(gecmis, onek, simdi, gun):
    from sosyal_motor import _zaman
    sinir = simdi - timedelta(days=gun)
    return any((g.get('anahtar') or '').startswith(onek) and (z := _zaman(g.get('zaman'))) and z > sinir for g in gecmis)


def adaylar(simdi, vakit):
    """(dizi, parametre) sırası: günden güne ve öğle/akşam arasında döner, aynı gün iki vakit aynı diziyi açmaz."""
    bas = (simdi.toordinal() * 2 + (1 if vakit == 'aksam' else 0)) % len(DIZILER)
    sonuc = []
    for n in range(len(DIZILER)):
        dizi = DIZILER[(bas + n) % len(DIZILER)]
        if dizi == 'puanla':
            sonuc.append(('puanla', None))
        elif dizi == 'atanan':
            b = simdi.toordinal() % len(DUZEYLER)
            sonuc += [('atanan', DUZEYLER[(b + m) % len(DUZEYLER)][0]) for m in range(len(DUZEYLER))]
        else:
            b = simdi.toordinal() % len(ARALIKLAR)
            sonuc += [('aralik', ARALIKLAR[(b + m) % len(ARALIKLAR)]) for m in range(len(ARALIKLAR))]
    return sonuc


def _onek(dizi, param):
    if dizi == 'puanla':
        return 'kanca:puanla:'
    if dizi == 'atanan':
        return f'kanca:atanan:{param}:'
    return f'kanca:aralik:{param[0]}:{param[1]}:'


def konu(vakit, acik, simdi, gecmis=(), docs=None):
    """Bu vaktin kancalı videosu (sosyal_motor.sablon_uret biçiminde konu) ya da None (veri yok / hepsi yakında yapıldı).
    Aynı gün yapılmış dizi ve TEKRAR_GUN içinde yapılmış düzey/aralık atlanır."""
    gecmis = list(gecmis)
    bugun = {(g.get('anahtar') or '').split(':')[1] for g in gecmis
             if (g.get('anahtar') or '').startswith('kanca:') and str(g.get('zaman', ''))[:10] == simdi.date().isoformat()}
    palet = PALETLER[(simdi.toordinal() + (1 if vakit == 'aksam' else 0)) % len(PALETLER)]
    reels.palet_sec(palet)
    for dizi, param in adaylar(simdi, vakit):
        if dizi in bugun or _yakin(gecmis, _onek(dizi, param), simdi, TEKRAR_GUN[dizi]):
            continue
        try:
            if dizi == 'puanla':
                sonuc = puanla_konusu(acik, simdi, docs)
            elif dizi == 'atanan':
                sonuc = atanan_konusu(acik, simdi, docs, param)
            else:
                sonuc = aralik_konusu(acik, simdi, docs, param)
        except Exception as hata:   # bir dizinin beklenmedik verisi diğerlerini durdurmaz
            print(f'::warning::Kanca dizisi kurulamadı ({dizi} {param}): {hata}')
            continue
        if sonuc:
            sonuc['palet'] = palet
            return sonuc
    return None


if __name__ == '__main__':
    import sosyal_motor as sm
    from datetime import datetime
    from site_uret import TR
    p = argparse.ArgumentParser()
    p.add_argument('dizi', choices=DIZILER)
    p.add_argument('--cikti', default='kanca-onizleme')
    p.add_argument('--video', action='store_true')
    a = p.parse_args()
    simdi = datetime.now(TR)
    acik = sm.acik_ilanlar(sm.ilanlari_yukle(), simdi)
    reels.palet_sec('kagit')
    c = {'puanla': lambda: puanla_konusu(acik, simdi), 'atanan': lambda: atanan_konusu(acik, simdi),
         'aralik': lambda: aralik_konusu(acik, simdi)}[a.dizi]()
    if not c:
        raise SystemExit('Veri yetersiz.')
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    for n, im in enumerate(reels.sahne_kareleri(c['sahneler']), 1):
        im.save(cikti / f'{n:02d}.png')
    if a.video:
        reels.video_yaz(c['sahneler'], cikti / 'reel.mp4')
    print(c['baslik'])
    print(c['giris'])
