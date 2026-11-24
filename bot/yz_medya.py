"""Anlatıcı videosu için Gemini ile seslendirme (TTS) ve sunucu görseli üretir (GitHub Actions'ta, GEMINI_ANAHTARI ile).

Çıktılar `yz-medya/` klasörüne: ses-<ses_adi>.wav (24 kHz mono), sunucu-<n>.png, rapor.txt. Anahtar hiçbir yere yazılmaz.
Kullanım: python bot/yz_medya.py [--ses Zephyr,Leda] [--gorsel 2]"""
import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

KOK = 'https://generativelanguage.googleapis.com/v1beta'
CIKTI = Path('yz-medya')

YONERGE = ("Aşağıdaki Türkçe metni genç, enerjik, samimi ve kendinden emin bir kadın sosyal medya anlatıcısı gibi oku. "
           "Tempo canlı ama anlaşılır olsun, cümle sonlarında kısa duraklar ver, vurgulu kelimeleri hissettir. "
           "'KPSS' kısaltmasını harf harf 'ke pe se se' diye, 'DM' kısaltmasını 'di em' diye oku. Metin:\n\n")

METIN = """KPSS'den altmış aldın diye, "atanamazsın" diyenler sana yanlış söylemiş.
Çoğu kişi puanını görünce morali bozuluyor, ilanlara bakmıyor bile.
Oysa şu an en az altmış isteyen açık ilanlar var. Biz her gün hepsini tek tek okuyoruz.
Mesela İçişleri Bakanlığı bin yüz yetmiş sözleşmeli personel alıyor; lise, önlisans, lisans. Eyyübiye Belediyesi dokuz zabıta memuru alıyor. Bartın Üniversitesi önlisans mezunu büro personeli arıyor. Üçünde de şart: en az altmış.
Hepsini videoya sığdıramam. DM'ye yazmana da gerek yok. KPSS Tercihi nokta com'a gir, arama kutusuna kadronu ya da bölümünü yaz. Sana uyan ilanlar karşına çıksın.
Atanmak isteyen, KPSS'ye hazırlanan bir arkadaşına bu videoyu gönder. O da bilsin."""

GORSEL = ("Vertical 9:16 image. A friendly young Turkish woman in her late twenties as a high-quality 3D animated film character "
          "(modern Pixar / Disney feature animation look, soft subsurface skin, expressive but natural proportions). "
          "Shoulder-length wavy dark brown hair, warm brown eyes, light natural makeup, small gold stud earrings, "
          "wearing a mustard-yellow knit sweater over a white collared shirt. She sits at a wooden desk and faces the camera "
          "straight on, head level, looking directly into the lens, lips gently closed with a warm confident smile. "
          "Her face is large, sharp and fully visible, centered horizontally, in the upper half of the frame; head, shoulders "
          "and upper torso visible, hands resting on the desk. Background: cozy modern study softly out of focus, navy blue "
          "vertical wooden slat wall, a warm orange LED strip glow, a small bookshelf. Soft cinematic key light, high detail. "
          "No text, no letters, no logos, no watermark.")


def iste(yol, govde, anahtar, zaman_asimi=180):
    istek = urllib.request.Request(f'{KOK}/{yol}', data=json.dumps(govde).encode(), method='POST',
                                   headers={'Content-Type': 'application/json', 'x-goog-api-key': anahtar})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
        return json.loads(r.read())


def modeller(anahtar):
    istek = urllib.request.Request(f'{KOK}/models?pageSize=1000', headers={'x-goog-api-key': anahtar})
    with urllib.request.urlopen(istek, timeout=60) as r:
        return [m['name'].split('/')[-1] for m in json.loads(r.read()).get('models', [])
                if 'generateContent' in m.get('supportedGenerationMethods', [])]


def ses_uret(model, ses, anahtar):
    govde = {'contents': [{'parts': [{'text': YONERGE + METIN}]}],
             'generationConfig': {'responseModalities': ['AUDIO'],
                                  'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': ses}}}}}
    y = iste(f'models/{model}:generateContent', govde, anahtar, 300)
    veri = base64.b64decode(y['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    yol = CIKTI / f'ses-{ses}.wav'
    with wave.open(str(yol), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(veri)
    return yol, len(veri) / 48000


def gorsel_uret(model, n, anahtar):
    govde = {'contents': [{'parts': [{'text': GORSEL}]}],
             'generationConfig': {'responseModalities': ['TEXT', 'IMAGE'], 'imageConfig': {'aspectRatio': '9:16'}}}
    y = iste(f'models/{model}:generateContent', govde, anahtar, 300)
    for p in y['candidates'][0]['content']['parts']:
        if 'inlineData' in p:
            yol = CIKTI / f'sunucu-{n}.png'
            yol.write_bytes(base64.b64decode(p['inlineData']['data']))
            return yol
    raise RuntimeError('görsel dönmedi')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--ses', default='Zephyr,Leda,Aoede')
    a.add_argument('--gorsel', type=int, default=2)
    s = a.parse_args()
    anahtar = os.environ.get('GEMINI_ANAHTARI', '').strip()
    if not anahtar:
        raise SystemExit('GEMINI_ANAHTARI yok')
    CIKTI.mkdir(exist_ok=True)
    rapor = []
    hepsi = modeller(anahtar)
    tts = [m for m in hepsi if 'tts' in m]
    img = [m for m in hepsi if 'image' in m and 'tts' not in m]
    rapor.append('TTS modelleri: ' + ', '.join(tts))
    rapor.append('Görsel modelleri: ' + ', '.join(img))
    tts.sort(key=lambda m: ('pro' in m, 'preview' not in m), reverse=True)    # önce pro, sonra flash
    for ses in [x for x in s.ses.split(',') if x]:
        for m in tts:
            try:
                yol, sure = ses_uret(m, ses, anahtar)
                rapor.append(f'ses {ses}: {m} → {yol.name} {sure:.1f} sn')
                break
            except urllib.error.HTTPError as h:
                rapor.append(f'ses {ses}: {m} HTTP {h.code} {h.read()[:200]!r}')
            except Exception as e:
                rapor.append(f'ses {ses}: {m} hata {str(e)[:200]}')
            time.sleep(5)
        time.sleep(22)    # ücretsiz katman dakika sınırı
    for n in range(1, s.gorsel + 1):
        for m in img:
            try:
                yol = gorsel_uret(m, n, anahtar)
                rapor.append(f'görsel {n}: {m} → {yol.name}')
                break
            except urllib.error.HTTPError as h:
                rapor.append(f'görsel {n}: {m} HTTP {h.code} {h.read()[:200]!r}')
            except Exception as e:
                rapor.append(f'görsel {n}: {m} hata {str(e)[:200]}')
        time.sleep(10)
    (CIKTI / 'rapor.txt').write_text('\n'.join(rapor), encoding='utf-8')
    print('\n'.join(rapor))


if __name__ == '__main__':
    main()
