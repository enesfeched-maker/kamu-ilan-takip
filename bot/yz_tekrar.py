"""Yapay zekânın tek görevi: "bu iki kayıt aynı ilanın iki kaynaktaki kopyası mı?" (21 Ekim 2026 kullanıcı kararı).

Bot önce kendi kuralıyla bakar (ilan_bot.tekrar_karari: 'ayni' / 'farkli' / 'belirsiz'). Yalnız 'belirsiz' kalan ve son
72 saatte kanalda paylaşılmış kayıtla benzeyen yeni ilan için kısa bir metin sorusu sorulur (PDF yok).
Sağlayıcılar sırayla denenir: Groq (Llama 3.3 70B, ücretsiz, hızlı) -> Gemini (yedek). Hiçbiri yanıt vermezse ilan yayınlanır.
Yapay zekânın yanlış "aynı" demesi gerçek bir ilanı yutacağı için: yalnız ayni=true VE güven >= 0.9 ise ilan tutulur;
"farklı", "emin değilim", hata, kota, zaman aşımı -> ilan beklemeden yayınlanır (tekrar sorulmaz: gönderilen sayılır).
Ayar: config.json 'yz_tekrar_acik': true; GROQ_ANAHTARI ve/veya GEMINI_ANAHTARI ortam değişkeni; yalnız gönderim adımında."""
import json
import os
import urllib.error
import urllib.request

EN_AZ_GUVEN = 0.9
CAGRI_SINIRI = 6   # tek çalışmada en çok bu kadar soru (ücretsiz kota ve süre)
ZAMAN_ASIMI = 25
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODELLER = ('llama-3.3-70b-versatile', 'llama-3.1-8b-instant')

_durum = {'etkin': False, 'groq': '', 'gemini': '', 'cagri': 0}

ISTEM = """Aşağıdaki iki kamu ilanı kaydı, AYNI gerçek ilanın iki farklı kaynaktaki (SBB, Kariyer Kapısı, İŞKUR, ÇŞB) kopyası mı?
Aynı sayılması için kurum, kadro/unvanlar, toplam kişi sayısı ve son başvuru günü birbiriyle uyuşmalı. Bir kayıtta bilgi eksikse
yalnız elindeki ortak bilgilere bak. Kurum adı farklı yazılmış olabilir (A.Ş. / Anonim Şirketi, kısaltma). Aynı kurumun aynı gün
kapanan ama FARKLI kadro/unvanlı ayrı ilanları aynı değildir. Emin değilsen ayni=false de.
Yalnız şu JSON'u yaz: {{"ayni": true|false, "guven": 0 ile 1 arası sayı, "neden": "tek kısa cümle"}}

KAYIT A:
{a}

KAYIT B:
{b}
"""
SEMA = {'type': 'OBJECT', 'properties': {'ayni': {'type': 'BOOLEAN'}, 'guven': {'type': 'NUMBER'}, 'neden': {'type': 'STRING'}},
        'required': ['ayni', 'guven']}


def ayarla(etkin, groq=None, gemini=None):
    """etkin: genel anahtar; groq/gemini verilmezse ortam değişkenlerinden (GROQ_ANAHTARI, GEMINI_ANAHTARI) okunur."""
    groq = (groq if groq is not None else os.environ.get('GROQ_ANAHTARI', '')).strip()
    gemini = (gemini if gemini is not None else os.environ.get('GEMINI_ANAHTARI', '')).strip()
    _durum.update(etkin=bool(etkin and (groq or gemini)), groq=groq, gemini=gemini, cagri=0)


def etkin():
    return _durum['etkin'] and _durum['cagri'] < CAGRI_SINIRI


def ozet(i, toplam=None):
    ozet_metin = ' '.join(str(i.get('ozet') or '').split())[:300]
    return json.dumps({'kurum': i.get('kurum'), 'baslik': i.get('baslik'), 'kadro': i.get('kadro'),
                       'toplam_kisi': toplam, 'son_basvuru': str(i.get('son_tarih') or '')[:10], 'ozet': ozet_metin},
                      ensure_ascii=False)


def _cozumle(metin):
    import re
    m = re.search(r'\{.*\}', str(metin or ''), re.S)   # düşünme etiketi/ek yazı varsa yalnız JSON kısmı
    sonuc = json.loads(m.group(0) if m else metin)
    return {'ayni': bool(sonuc.get('ayni')), 'guven': float(sonuc.get('guven') or 0), 'neden': str(sonuc.get('neden') or '')[:200]}


_groq_modelleri_onbellek = []


def groq_modelleri(anahtar, iste=None):
    """Anahtarın gördüğü sohbet modelleri, tercih sırasıyla (model adları değişebildiği için listeden seçilir):
    Llama 3.3/3.x 70B > diğer 70B+ Llama > 8B Llama > gpt-oss > diğerleri. Liste alınamazsa sabit adlar."""
    if _groq_modelleri_onbellek:
        return _groq_modelleri_onbellek
    try:
        if iste:
            kimlikler = iste()
        else:
            req = urllib.request.Request(GROQ_URL.replace('/chat/completions', '/models'),
                                         headers={'Authorization': f'Bearer {anahtar}', 'User-Agent': 'kpsstercihi-tekrar/1.0'})
            with urllib.request.urlopen(req, timeout=ZAMAN_ASIMI) as r:
                kimlikler = [m['id'] for m in json.load(r).get('data') or [] if m.get('active', True)]
    except Exception as hata:
        print(f'Uyarı: Groq model listesi alınamadı: {str(hata)[:100]}')
        return list(GROQ_MODELLER)
    dis = ('whisper', 'guard', 'tts', 'playai', 'distil', 'embed', 'vision', 'prompt', 'safeguard', 'orpheus')
    adaylar = [k for k in kimlikler if not any(x in k.lower() for x in dis)]

    def sira(k):
        s = k.lower()
        for n, kural in enumerate((lambda x: 'gpt-oss-120b' in x or ('llama' in x and '70b' in x),
                                   lambda x: 'llama' in x and ('maverick' in x or 'scout' in x), lambda x: 'qwen' in x,
                                   lambda x: 'gpt-oss' in x, lambda x: 'llama' in x and '8b' in x)):
            if kural(s):
                return n
        return 9
    sirali = sorted(adaylar, key=lambda k: (sira(k), '3.3' not in k, k))
    _groq_modelleri_onbellek[:] = sirali or list(GROQ_MODELLER)
    return _groq_modelleri_onbellek


def _groq_iste(model, istem, anahtar, zaman_asimi):
    """Önce JSON kipiyle; model bunu desteklemiyorsa (HTTP 400) JSON kipi olmadan yeniden dener (istem zaten JSON ister)."""
    govde = {'model': model, 'temperature': 0, 'max_tokens': 800, 'response_format': {'type': 'json_object'},
             'messages': [{'role': 'system', 'content': 'Yalnız geçerli JSON döndür.'}, {'role': 'user', 'content': istem}]}
    for deneme in range(2):
        req = urllib.request.Request(GROQ_URL, data=json.dumps(govde).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {anahtar}',
                                              'User-Agent': 'kpsstercihi-tekrar/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=zaman_asimi) as r:
                return json.load(r)['choices'][0]['message']['content']
        except urllib.error.HTTPError as hata:
            if hata.code != 400 or deneme:
                raise
            govde.pop('response_format', None)


def _gemini_iste(istem, anahtar, zaman_asimi, iste=None):
    import yz_denetim as yd
    govde = {'contents': [{'parts': [{'text': istem}]}],
             'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'responseSchema': SEMA}}
    iste = iste or yd._iste
    try:
        modeller = yd._MODELLER or ([yd.MODEL] if yd.MODEL else yd.modeller_bul(anahtar))
    except Exception:
        return None
    for model in list(modeller)[:2]:
        try:
            return iste(model, govde, anahtar, zaman_asimi)['candidates'][0]['content']['parts'][0]['text']
        except Exception as hata:
            print(f'Uyarı: tekrar sorusu (Gemini {model}) yanıt vermedi: {str(hata)[:100]}')
    return None


def sor(a, b, toplam_a=None, toplam_b=None, iste=None, groq_iste=None, groq_model_listesi=None):
    """{'ayni': bool, 'guven': float, 'neden': str} ya da None (hiçbir sağlayıcı yanıt vermedi). Önce Groq, sonra Gemini; bekleme yok.
    iste: Gemini isteği (test), groq_iste: Groq isteği (test)."""
    _durum['cagri'] += 1
    istem = ISTEM.format(a=ozet(a, toplam_a), b=ozet(b, toplam_b))
    if _durum['groq']:
        groq_iste = groq_iste or _groq_iste
        for model in (groq_model_listesi or groq_modelleri(_durum['groq']))[:2]:
            try:
                return _cozumle(groq_iste(model, istem, _durum['groq'], ZAMAN_ASIMI))
            except Exception as hata:   # 429/5xx/zaman aşımı/bozuk yanıt: sıradaki model, sonra Gemini
                print(f'Uyarı: tekrar sorusu (Groq {model}) yanıt vermedi: {str(hata)[:100]}')
    if _durum['gemini']:
        metin = _gemini_iste(istem, _durum['gemini'], ZAMAN_ASIMI, iste)
        if metin:
            try:
                return _cozumle(metin)
            except Exception as hata:
                print(f'Uyarı: Gemini yanıtı okunamadı: {str(hata)[:100]}')
    return None


def tutulsun_mu(sonuc):
    return bool(sonuc and sonuc['ayni'] and sonuc['guven'] >= EN_AZ_GUVEN)
