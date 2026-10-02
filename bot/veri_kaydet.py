"""Persist the generated registry without publishing Git conflict markers."""
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

PATH = 'docs/ilanlar.json'


def merge_reminders(values, aliases):
    result=set(values)
    for value in values:
        try:
            ident, deadline=json.loads(value)
            if ident in aliases:
                result.add(json.dumps([aliases[ident],deadline],ensure_ascii=False))
        except (ValueError,TypeError):
            continue
    return sorted(result)


def merge_registry(a, b):
    # Prefer the most recently checked detail per record; never forget a sent ID.
    version = max(int(a.get('telegram_yayin_surumu',1)), int(b.get('telegram_yayin_surumu',1)))
    histories = [s for s in (a,b) if int(s.get('telegram_yayin_surumu',1)) == version]
    merged = {}
    for state in sorted([a, b], key=lambda s: s.get('guncelleme') or ''):
        for item in state.get('ilanlar', []):
            old = merged.get(item['id'])
            # A cached PDF can be reprocessed with a corrected parser without
            # pretending that the original document was fetched more recently.
            # Preserve that upgrade when merging with an older parser's output.
            def detail_order(record):
                version=int(record.get('sbb_detay_surumu',0)) if record.get('kaynak_turu')=='sbb' else 0
                return version,record.get('detay_guncelleme') or ''
            if old and detail_order(old) > detail_order(item):
                item = {**item, **old}
            if old and old.get('iptal_edildi') and not item.get('iptal_edildi'):
                item={**item,'iptal_edildi':old['iptal_edildi']}  # iptal işareti hiçbir birleşmede kaybolmaz
            if old:
                item={**item,'kaynak_kimlikleri':sorted(set(old.get('kaynak_kimlikleri',[])+item.get('kaynak_kimlikleri',[])))}
                refs={s['link']:s for obj in (old,item) for s in obj.get('kaynaklar',[]) if s.get('link')}
                if refs:
                    item['kaynaklar']=list(refs.values())
            merged[item['id']] = item
    sent = set().union(*(set(s.get('telegram_gonderilen',[])) for s in histories))
    aliases={alias:i['id'] for i in merged.values() for alias in i.get('kaynak_kimlikleri',[]) if alias!=i['id']}
    for alias,hedef in aliases.items():
        eski=merged.pop(alias,None)
        if eski and eski.get('iptal_edildi') and hedef in merged and not merged[hedef].get('iptal_edildi'):
            merged[hedef]['iptal_edildi']=eski['iptal_edildi']  # takma ada dönüşen orijinalin iptal işareti korunur
    sent.update(aliases[x] for x in list(sent) if x in aliases)
    pending = set().union(*(set(s.get('telegram_bekleyen',[])) for s in histories)) - sent
    pending={aliases.get(x,x) for x in pending}-sent
    # Telegram message_id kayıtları gönderim geçmişi gibidir: asla silinmez, her iki durumun birleşimi alınır.
    mesajlar={}
    for state in sorted([a, b], key=lambda s: s.get('guncelleme') or ''):
        mesajlar.update({k:v for k,v in (state.get('telegram_mesajlari') or {}).items() if v})
    yanitlar={}
    for state in sorted([a, b], key=lambda s: s.get('guncelleme') or ''):
        for k,v in (state.get('telegram_duyuru_yanitlari') or {}).items():
            yanitlar[k]=max(str(v),yanitlar.get(k,''))
    return {'guncelleme': max(a.get('guncelleme') or '', b.get('guncelleme') or ''),
            'ilanlar': sorted(merged.values(), key=lambda i: i.get('son_tarih') or '9999'),
            'telegram_gonderilen': sorted(sent), 'telegram_bekleyen': sorted(pending),
            'telegram_yayin_surumu': version,
            'telegram_mesajlari': dict(sorted(mesajlar.items())),
            'telegram_duyuru_yanitlari': dict(sorted(yanitlar.items())),
            'telegram_toplu_hatirlatma_gunu': max([g for g in (a.get('telegram_toplu_hatirlatma_gunu'), b.get('telegram_toplu_hatirlatma_gunu')) if g] or [None]),
            'telegram_hatirlatilan': merge_reminders(set().union(*(set(s.get('telegram_hatirlatilan',[])) for s in histories)),aliases),
            'kaynak_baslangiclari': sorted(set(a.get('kaynak_baslangiclari',[])) | set(b.get('kaynak_baslangiclari',[]))),
            'canli_kimlikler': sorted({aliases.get(x,x) for x in sorted([a,b],key=lambda s:s.get('guncelleme') or '')[-1].get('canli_kimlikler',[])}),
            'kaynak_durumlari': {**a.get('kaynak_durumlari',{}), **b.get('kaynak_durumlari',{})}}


def git(*args, check=True, capture=False):
    return subprocess.run(['git', *args], check=check, text=True, encoding='utf-8',
                          stdout=subprocess.PIPE if capture else None,
                          env={**os.environ, 'GIT_EDITOR': 'true'})


def write(state):
    Path(PATH).write_text(json.dumps(state, ensure_ascii=False, indent=1)+'\n', encoding='utf-8')


# Her taramada değişen zaman damgaları; tek başına commit gerektirmez.
OYNAK_ALANLAR = {'detay_guncelleme', 'kontrol', 'yerel_kontrol'}
ZAMAN_YENILEME = timedelta(hours=3)


def anlamli(state):
    def temizle(obj):
        if isinstance(obj, dict):
            return {k: temizle(v) for k, v in obj.items() if k not in OYNAK_ALANLAR}
        if isinstance(obj, list):
            return [temizle(v) for v in obj]
        return obj
    return temizle({k: v for k, v in state.items() if k != 'guncelleme'})


def commit_gerekli(remote, state):
    """Gerçek veri değiştiyse ya da zaman damgaları 3 saatten eskiyse kaydet."""
    if anlamli(remote) != anlamli(state):
        return True
    try:
        eski = datetime.fromisoformat(remote['guncelleme'])
        yeni = datetime.fromisoformat(state['guncelleme'])
    except (KeyError, TypeError, ValueError):
        return True
    return yeni - eski >= ZAMAN_YENILEME


def main():
    state = json.loads(Path(PATH).read_text(encoding='utf-8'))
    git('config', 'user.name', 'ilan-bot')
    git('config', 'user.email', 'ilan-bot@users.noreply.github.com')
    for _ in range(3):
        git('fetch', 'origin', 'main')
        remote = json.loads(git('show', 'origin/main:'+PATH, capture=True).stdout)
        state = merge_registry(remote, state)
        write(state)
        if not commit_gerekli(remote, state):
            print('Yalnızca zaman damgaları değişti; commit atlanıyor.')
            return
        # Dizini uzak main'e eşitle: tek commit, rebase çakışması yok.
        git('reset', '--mixed', '--quiet', 'origin/main')
        git('add', PATH)
        git('commit', '--quiet', '-m', 'ilanlar güncellendi')
        if git('push', 'origin', 'HEAD:main', check=False).returncode == 0:
            print('Registry saved; sent and pending histories preserved.')
            return
    raise RuntimeError('Registry push failed after three attempts; valid local data retained.')


if __name__ == '__main__':
    main()
