"""Zamanlanmış görev girişi: kodu GitHub main ile eşitler, sonra yerel taramayı çalıştırır.

Görev bu dosyayı pythonw ile çalıştırır; git ve tarama konsol penceresi açmadan çalışır.
Ağ ya da git hatasında mevcut kodla taramaya devam edilir.
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIZLI = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
GUNLUK = ROOT / 'local-data' / 'tarama.log'


def yaz(metin):
    try:
        GUNLUK.parent.mkdir(exist_ok=True)
        with GUNLUK.open('a', encoding='utf-8') as dosya:
            dosya.write(f'{datetime.now(timezone.utc).isoformat()} {metin}\n')
    except OSError:
        pass


def guncelle():
    # reset --hard: tarayıcının ürettiği izlenmeyen dosyalar (yeni PDF'ler) çekmeyi bozmasın.
    for komut in (['git', 'fetch', '-q', 'origin', 'main'], ['git', 'reset', '-q', '--hard', 'origin/main']):
        try:
            sonuc = subprocess.run(komut, cwd=ROOT, creationflags=GIZLI, timeout=120, capture_output=True)
        except (OSError, subprocess.TimeoutExpired) as hata:
            yaz(f'Kod güncellenemedi ({type(hata).__name__}); mevcut kodla devam.')
            return False
        if sonuc.returncode:
            yaz(f'Kod güncellenemedi (git {komut[1]} çıkış {sonuc.returncode}); mevcut kodla devam.')
            return False
    return True


if __name__ == '__main__':
    guncelle()
    tarama = subprocess.run([sys.executable, str(ROOT / 'bot' / 'yerel_tara.py'), *sys.argv[1:]],
                            cwd=ROOT, creationflags=GIZLI)
    sys.exit(tarama.returncode)
