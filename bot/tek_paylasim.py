"""Kanala elle onaylanmış tek seferlik paylaşım (ör. 'Bu haftanın en iyi ilanları'): görsel + satır satır düğmeler.

Kullanım: python bot/tek_paylasim.py paylasim/<ad>.json   (tek-paylasim.yml, yalnız elle tetiklenir)
JSON: {"foto": "paylasim/x.png", "metin": "", "dugmeler": [[["Yazı", "https://..."], ...], ...]}
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
    klavye = [[{'text': y, 'url': utm_ekle(u, SITE)} for y, u in satir] for satir in tanim['dugmeler']]
    alanlar = {'chat_id': chat_id, 'reply_markup': json.dumps({'inline_keyboard': klavye}, ensure_ascii=False)}
    if tanim.get('metin'):
        alanlar.update(caption=tanim['metin'], parse_mode='HTML')
    sinir = 'tek-' + uuid.uuid4().hex
    parca = [f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in alanlar.items()]
    parca.append(f'--{sinir}\r\nContent-Disposition: form-data; name="photo"; filename="kart.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                 + (ROOT / tanim['foto']).read_bytes() + b'\r\n')
    parca.append(f'--{sinir}--\r\n'.encode())
    return b''.join(parca), 'multipart/form-data; boundary=' + sinir


def metin_govdesi(tanim, chat_id):
    """Görselsiz paylaşım (ör. düzeltme duyurusu): sendMessage, bağlantı önizlemesi kapalı."""
    klavye = [[{'text': y, 'url': utm_ekle(u, SITE)} for y, u in satir] for satir in tanim['dugmeler']]
    return json.dumps({'chat_id': chat_id, 'text': tanim['metin'], 'parse_mode': 'HTML',
                       'link_preview_options': {'is_disabled': True},
                       'reply_markup': {'inline_keyboard': klavye}}, ensure_ascii=False).encode(), 'application/json'


def main(yol):
    tanim = json.loads((ROOT / yol).read_text(encoding='utf-8'))
    hazirla, yontem = (govde_hazirla, 'sendPhoto') if tanim.get('foto') else (metin_govdesi, 'sendMessage')
    govde, tur = hazirla(tanim, os.environ['TELEGRAM_CHAT_ID'])
    istek = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{yontem}",
                                   data=govde, headers={'Content-Type': tur})
    with urllib.request.urlopen(istek, timeout=60) as r:
        sonuc = json.load(r)
    if not sonuc.get('ok'):
        raise SystemExit('Telegram gönderimi başarısız.')
    print('Gönderildi, mesaj:', sonuc['result']['message_id'])


if __name__ == '__main__':
    main(sys.argv[1])
