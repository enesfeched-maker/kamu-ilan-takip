"""Kanala elle onaylanmış tek seferlik paylaşım (ör. 'Bu haftanın en iyi ilanları'): görsel + satır satır düğmeler.

Kullanım: python bot/tek_paylasim.py paylasim/<ad>.json   (tek-paylasim.yml, yalnız elle tetiklenir)
JSON: {"foto": "paylasim/x.png", "metin": "", "dugmeler": [[["Yazı", "https://..."], ...], ...]}
Video için "foto" yerine: "video": "paylasim/x.mp4", "kapak": "paylasim/x.jpg", "boyut": [genişlik, yükseklik, saniye]
Anket için ek alan: "anket": {"soru": "...", "secenekler": ["Evet", "Hayır"]} (görselin altına yanıt olarak gider; oy değiştirilebilir)
"""
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ilan_bot import utm_ekle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://kpsstercihi.com/'


def govde_hazirla(tanim, chat_id):
    klavye = [[{'text': y, 'url': utm_ekle(u, SITE)} for y, u in satir] for satir in tanim.get('dugmeler') or []]
    alanlar = {'chat_id': chat_id}
    if klavye:
        alanlar['reply_markup'] = json.dumps({'inline_keyboard': klavye}, ensure_ascii=False)
    if tanim.get('metin'):
        alanlar.update(caption=tanim['metin'], parse_mode='HTML')
    dosyalar = [('photo', 'kart.png', 'image/png', tanim.get('foto'))]
    if tanim.get('video'):   # dikey tanıtım videosu: boyut verilmezse Telegram kare kırpabiliyor
        genislik, yukseklik, sure = tanim['boyut']
        alanlar.update(width=genislik, height=yukseklik, duration=sure, supports_streaming='true')
        dosyalar = [('video', 'video.mp4', 'video/mp4', tanim['video']), ('thumbnail', 'kapak.jpg', 'image/jpeg', tanim.get('kapak'))]
    sinir = 'tek-' + uuid.uuid4().hex
    parca = [f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in alanlar.items()]
    for alan, ad, tur, yol in dosyalar:
        if yol:
            parca.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{alan}"; filename="{ad}"\r\nContent-Type: {tur}\r\n\r\n'.encode()
                         + (ROOT / yol).read_bytes() + b'\r\n')
    parca.append(f'--{sinir}--\r\n'.encode())
    return b''.join(parca), 'multipart/form-data; boundary=' + sinir


def metin_govdesi(tanim, chat_id):
    """Görselsiz paylaşım (ör. düzeltme duyurusu): sendMessage, bağlantı önizlemesi kapalı."""
    klavye = [[{'text': y, 'url': utm_ekle(u, SITE)} for y, u in satir] for satir in tanim['dugmeler']]
    return json.dumps({'chat_id': chat_id, 'text': tanim['metin'], 'parse_mode': 'HTML',
                       'link_preview_options': {'is_disabled': True},
                       'reply_markup': {'inline_keyboard': klavye}}, ensure_ascii=False).encode(), 'application/json'


def anket_govdesi(anket, chat_id, yanit_id):
    """Kanal anketi her zaman gizli oyludur; 'regular' türde kullanıcı oyunu geri alıp değiştirebilir."""
    return json.dumps({'chat_id': chat_id, 'question': anket['soru'], 'options': [{'text': s} for s in anket['secenekler']],
                       'is_anonymous': True, 'type': 'regular', 'allows_multiple_answers': False, 'allows_revoting': True,
                       'reply_parameters': {'message_id': yanit_id}}, ensure_ascii=False).encode()


def telegram(yontem, govde, tur):
    istek = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{yontem}",
                                   data=govde, headers={'Content-Type': tur})
    with urllib.request.urlopen(istek, timeout=180) as r:
        sonuc = json.load(r)
    if not sonuc.get('ok'):
        raise SystemExit('Telegram gönderimi başarısız.')
    return sonuc['result']


def main(yol):
    tanim = json.loads((ROOT / yol).read_text(encoding='utf-8'))
    if tanim.get('video'):
        hazirla, yontem = govde_hazirla, 'sendVideo'
    else:
        hazirla, yontem = (govde_hazirla, 'sendPhoto') if tanim.get('foto') else (metin_govdesi, 'sendMessage')
    govde, tur = hazirla(tanim, os.environ['TELEGRAM_CHAT_ID'])
    mesaj = telegram(yontem, govde, tur)
    print('Gönderildi, mesaj:', mesaj['message_id'])
    if tanim.get('anket'):
        anket = telegram('sendPoll', anket_govdesi(tanim['anket'], os.environ['TELEGRAM_CHAT_ID'], mesaj['message_id']), 'application/json')
        print('Anket gönderildi, mesaj:', anket['message_id'], 'oy değiştirme:', anket['poll'].get('allows_revoting', 'alan yok'))


if __name__ == '__main__':
    main(sys.argv[1])
