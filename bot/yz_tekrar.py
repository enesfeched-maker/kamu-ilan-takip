"""Gemini'nin tek görevi: "bu iki kayıt aynı ilanın iki kaynaktaki kopyası mı?" (21 Ekim 2026 kullanıcı kararı).

Bot önce kendi kuralıyla bakar (ilan_bot.tekrar_karari: 'ayni' / 'farkli' / 'belirsiz'). Yalnız 'belirsiz' kalan ve son
72 saatte kanalda paylaşılmış kayıtla benzeyen yeni ilan için kısa bir metin sorusu Gemini'ye sorulur (PDF yok).
Gemini'nin yanlış "aynı" demesi gerçek bir ilanı yutacağı için: yalnız ayni=true VE güven >= 0.9 ise ilan tutulur;
"farklı", "emin değilim", hata, kota, zaman aşımı -> ilan beklemeden yayınlanır (tekrar sorulmaz: gönderilen sayılır).
Ayar: config.json 'yz_tekrar_acik': true; GEMINI_ANAHTARI ortam değişkeni; yalnız gönderim adımında (ilan_bot --send-only)."""
import json
import os
import urllib.error

EN_AZ_GUVEN = 0.9
CAGRI_SINIRI = 6   # tek çalışmada en çok bu kadar soru (ücretsiz kota ve süre)
ZAMAN_ASIMI = 25

_durum = {'etkin': False, 'anahtar': '', 'cagri': 0}

ISTEM = """Aşağıdaki iki kamu ilanı kaydı, AYNI gerçek ilanın iki farklı kaynaktaki (SBB, Kariyer Kapısı, İŞKUR, ÇŞB) kopyası mı?
Aynı sayılması için kurum, kadro/unvanlar, toplam kişi sayısı ve son başvuru günü birbiriyle uyuşmalı. Bir kayıtta bilgi eksikse
yalnız elindeki ortak bilgilere bak. Kurum adı farklı yazılmış olabilir (A.Ş. / Anonim Şirketi, kısaltma). Aynı kurumun aynı gün
kapanan ama FARKLI kadro/unvanlı ayrı ilanları aynı değildir. Emin değilsen ayni=false de.

KAYIT A:
{a}

KAYIT B:
{b}
"""
SEMA = {'type': 'OBJECT', 'properties': {'ayni': {'type': 'BOOLEAN'}, 'guven': {'type': 'NUMBER'}, 'neden': {'type': 'STRING'}},
        'required': ['ayni', 'guven']}


def ayarla(etkin, anahtar=None):
    _durum.update(etkin=bool(etkin and (anahtar or os.environ.get('GEMINI_ANAHTARI', '').strip())),
                  anahtar=(anahtar or os.environ.get('GEMINI_ANAHTARI', '').strip()), cagri=0)


def etkin():
    return _durum['etkin'] and _durum['cagri'] < CAGRI_SINIRI


def ozet(i, toplam=None):
    ozet_metin = ' '.join(str(i.get('ozet') or '').split())[:300]
    return json.dumps({'kurum': i.get('kurum'), 'baslik': i.get('baslik'), 'kadro': i.get('kadro'),
                       'toplam_kisi': toplam, 'son_basvuru': str(i.get('son_tarih') or '')[:10], 'ozet': ozet_metin},
                      ensure_ascii=False)


def sor(a, b, toplam_a=None, toplam_b=None, iste=None):
    """{'ayni': bool, 'guven': float, 'neden': str} ya da None (hata/kota/okunamadı). En çok iki model denenir, bekleme yok."""
    import yz_denetim as yd
    _durum['cagri'] += 1
    govde = {'contents': [{'parts': [{'text': ISTEM.format(a=ozet(a, toplam_a), b=ozet(b, toplam_b))}]}],
             'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'responseSchema': SEMA}}
    iste = iste or yd._iste
    try:
        modeller = yd._MODELLER or ([yd.MODEL] if yd.MODEL else yd.modeller_bul(_durum['anahtar']))
    except Exception:
        return None
    for model in list(modeller)[:2]:
        try:
            yanit = iste(model, govde, _durum['anahtar'], ZAMAN_ASIMI)
            sonuc = json.loads(yanit['candidates'][0]['content']['parts'][0]['text'])
            return {'ayni': bool(sonuc.get('ayni')), 'guven': float(sonuc.get('guven') or 0), 'neden': str(sonuc.get('neden') or '')[:200]}
        except Exception as hata:   # 503/429/zaman aşımı/bozuk yanıt: ilan beklemeden yayınlanır
            print(f'Uyarı: tekrar sorusu ({model}) yanıt vermedi: {str(hata)[:120]}')
    return None


def tutulsun_mu(sonuc):
    return bool(sonuc and sonuc['ayni'] and sonuc['guven'] >= EN_AZ_GUVEN)
