// Kullanıcı tercihleri ile ilanı eşleştirme (saf fonksiyonlar, bağımlılık yok).

export function ilanMetni(ilan) {
  // bot-ilanlar.json'daki hazır metin (Türkçe küçük harf) varsa onu kullan.
  if (typeof ilan.metin === 'string' && ilan.metin) return ilan.metin; // zaten küçük harf
  const parcalar = [ilan.baslik, ilan.kurum, ilan.kadro, ilan.ozet];
  for (const s of Array.isArray(ilan.sartlar) ? ilan.sartlar : []) {
    if (s && typeof s === 'object') parcalar.push(s.kadro, s.metin);
    else if (typeof s === 'string') parcalar.push(s);
  }
  return parcalar.filter(Boolean).join(' ').toLocaleLowerCase('tr');
}

// Europe/Istanbul takvim günü, 'YYYY-MM-DD'.
export function bugunIstanbul(simdi = new Date()) {
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(simdi);
  const g = (t) => p.find((x) => x.type === t).value;
  return `${g('year')}-${g('month')}-${g('day')}`;
}

const liste = (x) => (Array.isArray(x) ? x : []);

export function kelimelerKucult(k) {
  return liste(k).map((x) => String(x).trim().toLocaleLowerCase('tr')).filter(Boolean);
}

// Süre doldu mu? son_zaman (simdi verilmişse) önceliklidir, yoksa son_tarih < bugün.
export function sureDoldu(ilan, bugun, simdi) {
  if (simdi && ilan.son_zaman) {
    const t = Date.parse(ilan.son_zaman);
    if (!Number.isNaN(t)) return t < simdi.getTime();
  }
  return !!ilan.son_tarih && ilan.son_tarih < bugun;
}

export function uygunMu(ilan, kullanici, bugun = bugunIstanbul(), simdi = null, sureAtla = false) {
  if (!kullanici || !kullanici.aktif || !kullanici.onay) return false;
  if (!sureAtla && sureDoldu(ilan, bugun, simdi)) return false;
  if (ilan.kategori === 'akademik') return false; // akademik ilanlar hiçbir yerde gösterilmez

  const duzeyler = liste(kullanici.duzeyler);
  const ogrenim = liste(ilan.ogrenim);
  if (duzeyler.length && ogrenim.length && !ogrenim.some((d) => duzeyler.includes(d))) return false;

  const iller = liste(kullanici.iller);
  const ilanIller = liste(ilan.iller);
  if (iller.length && ilanIller.length && !ilanIller.some((i) => iller.includes(i))) return false;

  const kategoriler = liste(kullanici.kategoriler);
  if (kategoriler.length && ilan.kategori && !kategoriler.includes(ilan.kategori)) return false;

  // Çağıran kelimeleri kullanıcı başına bir kez küçültüp kelimelerKucuk verebilir.
  const kelimeler = Array.isArray(kullanici.kelimelerKucuk) ? kullanici.kelimelerKucuk : kelimelerKucult(kullanici.kelimeler);
  if (kelimeler.length) {
    const metin = ilanMetni(ilan);
    if (!kelimeler.some((k) => metin.includes(k))) return false;
  }
  return true;
}

