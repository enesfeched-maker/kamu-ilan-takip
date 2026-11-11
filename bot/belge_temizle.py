"""Depodaki kullanılmayan SBB belge kopyalarını (docs/belgeler/sbb/*.pdf) Git dizininden çıkarır.

11 Kasım 2026: depoda 8.274 PDF (2,6 GB) birikmişti, yalnız 323'üne (104 MB) bir ilan kaydı bağlıydı; her yarım saatlik
tarama bu 2,6 GB'ı baştan indiriyordu. Bir kopya, ilanlar.json ya da yerel-kaynaklar.json içindeki bir kayıt onu
gösteriyorsa kullanılıyor sayılır; diğerleri çalışma ağacından kaldırılır (Git geçmişinde durur, geri alınabilir).

Kullanım (belge-temizle.yml):  python bot/belge_temizle.py            # kaldırılacak yolları yazar, dizinden çıkarır
                               python bot/belge_temizle.py --kuru     # yalnız sayar, hiçbir şeye dokunmaz"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KLASOR = 'docs/belgeler/sbb/'
OZET = re.compile(r'belgeler/sbb/([a-f0-9]{64})\.pdf')
EN_AZ_BASVURU = 20   # bundan az kayıt belge gösteriyorsa veri eksik/bozuk demektir: hiçbir şey kaldırılmaz


def _kayit_ozetleri(kayitlar):
    ozetler = set()
    for i in kayitlar or []:
        if not isinstance(i, dict):
            continue
        if re.fullmatch(r'[a-f0-9]{64}', str(i.get('belge_sha256') or '')):
            ozetler.add(i['belge_sha256'])
        ozetler.update(OZET.findall(json.dumps(i, ensure_ascii=False)))   # belge_kopyasi ve kaynak bağlantıları
    return ozetler


def basvurulanlar(ilanlar_json, yerel_json):
    """İki veri dosyasındaki kayıtların gösterdiği belge özetleri; dosyalardan biri okunamazsa None (temizlik yapılmaz)."""
    try:
        ilanlar = json.loads(Path(ilanlar_json).read_text(encoding='utf-8-sig')).get('ilanlar')
        yerel = json.loads(Path(yerel_json).read_text(encoding='utf-8-sig')).get('kaynaklar') or {}
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(ilanlar, list):
        return None
    ozetler = _kayit_ozetleri(ilanlar)
    for kaynak in yerel.values():
        if isinstance(kaynak, dict):
            ozetler |= _kayit_ozetleri(kaynak.get('ilanlar'))
    return ozetler


def kullanilmayanlar(yollar, ozetler):
    """Depodaki belge yollarından hiçbir kaydın göstermediği PDF'ler. Veri güvenilir değilse boş liste."""
    if ozetler is None or len(ozetler) < EN_AZ_BASVURU:
        return []
    sonuc = []
    for yol in yollar:
        m = re.fullmatch(re.escape(KLASOR) + r'([a-f0-9]{64})\.pdf', yol)
        if m and m.group(1) not in ozetler:
            sonuc.append(yol)
    return sonuc


def git(*args, girdi=None):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, text=True, encoding='utf-8', input=girdi,
                          stdout=subprocess.PIPE).stdout


def main(kuru=False):
    yollar = [y for y in git('ls-files', '-z', KLASOR).split('\0') if y]
    ozetler = basvurulanlar(ROOT / 'docs' / 'ilanlar.json', ROOT / 'docs' / 'yerel-kaynaklar.json')
    fazla = kullanilmayanlar(yollar, ozetler)
    print(f'Depoda {len(yollar)} belge, kayıtların gösterdiği {len(ozetler or [])}, kaldırılacak {len(fazla)}.')
    if ozetler is None or len(ozetler) < EN_AZ_BASVURU:
        print('::warning::Veri dosyaları okunamadı ya da çok az belge gösteriyor; temizlik yapılmadı.')
        return 0
    if fazla and not kuru:
        # Dizinden çıkarılır (seyrek checkout'ta dosyalar diskte olmayabilir); çalışma ağacındaki kopya varsa silinir.
        git('update-index', '--force-remove', '-z', '--stdin', girdi='\0'.join(fazla) + '\0')
        for yol in fazla:
            (ROOT / yol).unlink(missing_ok=True)
    return len(fazla)


if __name__ == '__main__':
    main('--kuru' in sys.argv)
