"""Persist the generated registry without publishing Git conflict markers."""
import json
import os
import subprocess
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
    merged = {}
    for state in sorted([a, b], key=lambda s: s.get('guncelleme') or ''):
        for item in state.get('ilanlar', []):
            old = merged.get(item['id'])
            if old and (old.get('detay_guncelleme') or '') > (item.get('detay_guncelleme') or ''):
                item = {**item, **old}
            if old:
                item={**item,'kaynak_kimlikleri':sorted(set(old.get('kaynak_kimlikleri',[])+item.get('kaynak_kimlikleri',[])))}
                refs={s['link']:s for obj in (old,item) for s in obj.get('kaynaklar',[]) if s.get('link')}
                if refs:
                    item['kaynaklar']=list(refs.values())
            merged[item['id']] = item
    sent = set(a.get('telegram_gonderilen', [])) | set(b.get('telegram_gonderilen', []))
    aliases={alias:i['id'] for i in merged.values() for alias in i.get('kaynak_kimlikleri',[]) if alias!=i['id']}
    for alias in aliases:
        merged.pop(alias,None)
    sent.update(aliases[x] for x in list(sent) if x in aliases)
    pending = (set(a.get('telegram_bekleyen', [])) | set(b.get('telegram_bekleyen', []))) - sent
    pending={aliases.get(x,x) for x in pending}-sent
    return {'guncelleme': max(a.get('guncelleme') or '', b.get('guncelleme') or ''),
            'ilanlar': sorted(merged.values(), key=lambda i: i.get('son_tarih') or '9999'),
            'telegram_gonderilen': sorted(sent), 'telegram_bekleyen': sorted(pending),
            'telegram_hatirlatilan': merge_reminders(set(a.get('telegram_hatirlatilan', [])) | set(b.get('telegram_hatirlatilan', [])),aliases),
            'kaynak_baslangiclari': sorted(set(a.get('kaynak_baslangiclari',[])) | set(b.get('kaynak_baslangiclari',[]))),
            'kaynak_durumlari': {**a.get('kaynak_durumlari',{}), **b.get('kaynak_durumlari',{})}}


def git(*args, check=True, capture=False):
    return subprocess.run(['git', *args], check=check, text=True, encoding='utf-8',
                          stdout=subprocess.PIPE if capture else None,
                          env={**os.environ, 'GIT_EDITOR': 'true'})


def write(state):
    Path(PATH).write_text(json.dumps(state, ensure_ascii=False, indent=1)+'\n', encoding='utf-8')


def main():
    state = json.loads(Path(PATH).read_text(encoding='utf-8'))
    git('config', 'user.name', 'ilan-bot')
    git('config', 'user.email', 'ilan-bot@users.noreply.github.com')
    git('add', PATH)
    if git('diff', '--cached', '--quiet', check=False).returncode == 0:
        return
    git('commit', '-m', 'ilanlar güncellendi')
    for _ in range(3):
        git('fetch', 'origin', 'main')
        remote = json.loads(git('show', 'origin/main:'+PATH, capture=True).stdout)
        state = merge_registry(remote, state)
        result = git('rebase', 'origin/main', check=False)
        if result.returncode:
            conflicts = git('diff', '--name-only', '--diff-filter=U', capture=True).stdout.splitlines()
            if conflicts != [PATH]:
                git('rebase', '--abort', check=False)
                write(state)
                raise RuntimeError('Unexpected conflict; publication data preserved, repository not overwritten.')
            write(state)
            git('add', PATH)
            if git('rebase', '--continue', check=False).returncode:
                git('rebase', '--abort', check=False)
                write(state)
                raise RuntimeError('Registry rebase could not complete.')
        write(state)
        git('add', PATH)
        if git('diff', '--cached', '--quiet', check=False).returncode:
            git('commit', '-m', 'ilan gönderim geçmişlerini birleştir')
        if git('push', 'origin', 'HEAD:main', check=False).returncode == 0:
            print('Registry saved; sent and pending histories preserved.')
            return
    raise RuntimeError('Registry push failed after three attempts; valid local data retained.')


if __name__ == '__main__':
    main()
