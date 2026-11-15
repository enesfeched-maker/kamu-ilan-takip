"""Yerel SQLite deposu: paylaşımlar, zaman içindeki ölçümler ve kaynak durumları.

Her ölçüm ayrı satırdır; böylece bir paylaşımın izlenmesinin günler içinde nasıl arttığı saklanır.
Aynı değerler tekrar gelirse yeni satır yazılmaz (yalnız son görülme zamanı güncellenir)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

OLCUTLER = ('views', 'reach', 'likes', 'comments', 'shares', 'saved', 'forwards', 'reactions',
            'avg_watch_ms', 'total_watch_ms', 'interactions')
GONDERI_ALANLARI = ('platform', 'yerel_id', 'url', 'baslik', 'metin', 'yayin', 'tur', 'vakit', 'sablon', 'palet',
                    'muzik', 'icerik', 'kapak', 'bicim', 'ornek')

SEMA = f"""
CREATE TABLE IF NOT EXISTS gonderi (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  yerel_id TEXT NOT NULL,
  url TEXT, baslik TEXT, metin TEXT,
  yayin TEXT,                 -- ISO 8601, UTC
  tur TEXT, vakit TEXT, sablon TEXT, palet TEXT, muzik TEXT,
  icerik TEXT,                -- aynı içeriğin diğer platformlardaki kopyalarını bağlar (geçmiş kaydının zamanı)
  kapak TEXT, bicim TEXT,
  ornek INTEGER NOT NULL DEFAULT 0,
  ilk_gorulme TEXT, son_gorulme TEXT
);
CREATE INDEX IF NOT EXISTS gonderi_yayin ON gonderi(yayin);
CREATE TABLE IF NOT EXISTS olcum (
  gonderi_id TEXT NOT NULL REFERENCES gonderi(id),
  zaman TEXT NOT NULL,
  kaynak TEXT,
  {', '.join(o + ' INTEGER' for o in OLCUTLER)},
  PRIMARY KEY (gonderi_id, zaman)
);
CREATE TABLE IF NOT EXISTS kaynak_durum (
  kaynak TEXT PRIMARY KEY,
  durum TEXT NOT NULL,        -- hazir | bekliyor | hata | kapali
  aciklama TEXT,
  son_deneme TEXT, son_basari TEXT, adet INTEGER
);
CREATE TABLE IF NOT EXISTS ayar (ad TEXT PRIMARY KEY, deger TEXT);
"""


def simdi():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def utc(deger):
    """ISO metni (saat dilimli ya da Z) -> UTC ISO; çözülemezse None."""
    if not deger:
        return None
    try:
        z = datetime.fromisoformat(str(deger).replace('Z', '+00:00'))
    except ValueError:
        return None
    if z.tzinfo is None:
        z = z.replace(tzinfo=timezone.utc)
    return z.astimezone(timezone.utc).isoformat(timespec='seconds')


class Depo:
    def __init__(self, yol):
        self.yol = str(yol)
        if self.yol != ':memory:':
            Path(self.yol).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.yol, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SEMA)
        self.db.commit()

    def kapat(self):
        self.db.close()

    # ------------------------------------------------------------ gönderiler
    def gonderi_yaz(self, platform, yerel_id, **alanlar):
        """Paylaşımı ekler ya da günceller; None verilen alanlar eski değeri korur."""
        gid = f'{platform}:{yerel_id}'
        alanlar = {k: v for k, v in alanlar.items() if k in GONDERI_ALANLARI and v is not None}
        if 'yayin' in alanlar:
            alanlar['yayin'] = utc(alanlar['yayin'])
        an = simdi()
        var = self.db.execute('SELECT 1 FROM gonderi WHERE id=?', (gid,)).fetchone()
        if var:
            if alanlar:
                atama = ', '.join(f'{k}=?' for k in alanlar)
                self.db.execute(f'UPDATE gonderi SET {atama}, son_gorulme=? WHERE id=?', (*alanlar.values(), an, gid))
            else:
                self.db.execute('UPDATE gonderi SET son_gorulme=? WHERE id=?', (an, gid))
        else:
            alanlar.update(platform=platform, yerel_id=str(yerel_id))
            adlar = ', '.join(alanlar)
            self.db.execute(f'INSERT INTO gonderi (id, {adlar}, ilk_gorulme, son_gorulme) VALUES (?, {", ".join("?" * len(alanlar))}, ?, ?)',
                            (gid, *alanlar.values(), an, an))
        return gid

    def olcum_yaz(self, gonderi_id, degerler, zaman=None, kaynak=None):
        """Ölçüm satırı ekler. Son ölçümle aynıysa yazmaz (False döner)."""
        temiz = {k: int(v) for k, v in (degerler or {}).items() if k in OLCUTLER and v is not None}
        if not temiz:
            return False
        zaman = utc(zaman) or simdi()
        son = self.db.execute(f'SELECT {", ".join(OLCUTLER)}, zaman FROM olcum WHERE gonderi_id=? ORDER BY zaman DESC LIMIT 1',
                              (gonderi_id,)).fetchone()
        if son is not None and all(son[k] == v for k, v in temiz.items()):
            return False
        adlar = ', '.join(temiz)
        self.db.execute(f'INSERT OR REPLACE INTO olcum (gonderi_id, zaman, kaynak, {adlar}) VALUES (?, ?, ?, {", ".join("?" * len(temiz))})',
                        (gonderi_id, zaman, kaynak, *temiz.values()))
        return True

    def kaydet(self):
        self.db.commit()

    # ------------------------------------------------------------ durum ve ayar
    def durum_yaz(self, kaynak, durum, aciklama='', adet=None):
        an = simdi()
        eski = self.db.execute('SELECT son_basari FROM kaynak_durum WHERE kaynak=?', (kaynak,)).fetchone()
        son_basari = an if durum == 'hazir' else (eski['son_basari'] if eski else None)
        self.db.execute('INSERT OR REPLACE INTO kaynak_durum VALUES (?, ?, ?, ?, ?, ?)',
                        (kaynak, durum, aciklama, an, son_basari, adet))
        self.db.commit()

    def durumlar(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM kaynak_durum ORDER BY kaynak')]

    def ayar(self, ad, varsayilan=None):
        r = self.db.execute('SELECT deger FROM ayar WHERE ad=?', (ad,)).fetchone()
        return json.loads(r['deger']) if r else varsayilan

    def ayar_yaz(self, ad, deger):
        self.db.execute('INSERT OR REPLACE INTO ayar VALUES (?, ?)', (ad, json.dumps(deger, ensure_ascii=False)))
        self.db.commit()

    # ------------------------------------------------------------ okuma
    def gonderiler(self):
        """Her paylaşım + son ölçümü + 24 saat önceki ölçümü (değişim için)."""
        satirlar = [dict(r) for r in self.db.execute('SELECT * FROM gonderi ORDER BY yayin DESC')]
        olcumler = {}
        for r in self.db.execute(f'SELECT gonderi_id, zaman, {", ".join(OLCUTLER)} FROM olcum ORDER BY zaman'):
            olcumler.setdefault(r['gonderi_id'], []).append(dict(r))
        for s in satirlar:
            liste = olcumler.get(s['id'], [])
            s['olcum_sayisi'] = len(liste)
            s['son'] = _birlesik_son(liste)
            s['onceki'] = _gun_once(liste)
        return satirlar

    def seri(self, gonderi_id):
        return [dict(r) for r in self.db.execute(
            f'SELECT zaman, kaynak, {", ".join(OLCUTLER)} FROM olcum WHERE gonderi_id=? ORDER BY zaman', (gonderi_id,))]


def _birlesik_son(liste):
    """En son ölçüm; bazı ölçütler son satırda yoksa (farklı kaynak) daha eski satırdan tamamlanır."""
    if not liste:
        return None
    son = {'zaman': liste[-1]['zaman']}
    for o in OLCUTLER:
        son[o] = next((r[o] for r in reversed(liste) if r[o] is not None), None)
    return son


def _gun_once(liste):
    """Son ölçümden en az 20 saat önceki en yeni ölçüm (24 saatlik değişim için)."""
    if len(liste) < 2:
        return None
    son = datetime.fromisoformat(liste[-1]['zaman'])
    for r in reversed(liste[:-1]):
        if (son - datetime.fromisoformat(r['zaman'])).total_seconds() >= 20 * 3600:
            return {'zaman': r['zaman'], 'views': r['views']}
    return None
