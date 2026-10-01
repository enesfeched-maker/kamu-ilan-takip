// D1 yardimcilari. Kisisel veri yalnizca burada tutulur.
const JSON_ALANLAR = ['duzeyler', 'iller', 'kategoriler', 'kelimeler'];

function diziAyir(s) {
  try {
    const v = JSON.parse(s ?? '[]');
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

function satirdanKullanici(s) {
  if (!s) return null;
  const k = { ...s };
  for (const a of JSON_ALANLAR) k[a] = diziAyir(s[a]);
  return k;
}

export async function kullaniciGetir(env, chat_id) {
  const s = await env.DB.prepare('SELECT * FROM kullanicilar WHERE chat_id = ?').bind(chat_id).first();
  return satirdanKullanici(s);
}

export async function kullaniciKaydet(env, k) {
  const simdi = new Date().toISOString();
  const v = {
    chat_id: k.chat_id,
    onay: k.onay ? 1 : 0,
    duzeyler: JSON.stringify(k.duzeyler || []),
    iller: JSON.stringify(k.iller || []),
    kategoriler: JSON.stringify(k.kategoriler || []),
    akademik: k.akademik ? 1 : 0,
    kelimeler: JSON.stringify(k.kelimeler || []),
    aktif: k.aktif === 0 || k.aktif === false ? 0 : 1,
    hatirlatma: k.hatirlatma === 0 || k.hatirlatma === false ? 0 : 1,
    durum: k.durum ?? null,
    vip_bitis: k.vip_bitis ?? null,
    olusturma: k.olusturma || simdi,
    guncelleme: simdi,
  };
  const sutunlar = Object.keys(v);
  const guncellenecek = sutunlar.filter((s) => s !== 'chat_id' && s !== 'olusturma');
  const sql =
    'INSERT INTO kullanicilar (' + sutunlar.join(', ') + ') VALUES (' + sutunlar.map(() => '?').join(', ') + ') ' +
    'ON CONFLICT(chat_id) DO UPDATE SET ' + guncellenecek.map((s) => s + ' = excluded.' + s).join(', ');
  await env.DB.prepare(sql).bind(...sutunlar.map((s) => v[s])).run();
  return { ...k, ...v, duzeyler: k.duzeyler || [], iller: k.iller || [], kategoriler: k.kategoriler || [], kelimeler: k.kelimeler || [] };
}

export async function kullaniciSil(env, chat_id) {
  await env.DB.batch([
    env.DB.prepare('DELETE FROM gonderilen WHERE chat_id = ?').bind(chat_id),
    env.DB.prepare('DELETE FROM kuyruk WHERE chat_id = ?').bind(chat_id),
    env.DB.prepare('DELETE FROM kullanicilar WHERE chat_id = ?').bind(chat_id),
  ]);
}

export async function aktifKullanicilar(env) {
  const r = await env.DB.prepare('SELECT * FROM kullanicilar WHERE aktif = 1 AND onay = 1').all();
  return (r.results || []).map(satirdanKullanici);
}
// Oku-değiştir-yaz: tek UPDATE, guncelleme zaman damgası kontrolüyle. Çakışmada (0 satır) bir kez daha dener.
// fn(kullanici) nesneyi yerinde değiştirir. Kullanıcı yoksa null döner.
const GUNCELLENEBILIR = ['onay', 'duzeyler', 'iller', 'kategoriler', 'akademik', 'kelimeler', 'aktif', 'hatirlatma', 'durum', 'vip_bitis'];

export async function kullaniciGuncelle(env, chat_id, fn) {
  for (let deneme = 0; deneme < 2; deneme++) {
    const s = await env.DB.prepare('SELECT * FROM kullanicilar WHERE chat_id = ?').bind(chat_id).first();
    if (!s) return null;
    const k = satirdanKullanici(s);
    fn(k);
    let yeniZaman = new Date().toISOString();
    if (yeniZaman === s.guncelleme) yeniZaman = new Date(Date.now() + 1).toISOString();
    const deger = (a) => (JSON_ALANLAR.includes(a) ? JSON.stringify(k[a] || []) : a === 'durum' || a === 'vip_bitis' ? k[a] ?? null : k[a] ? 1 : 0);
    const r = await env.DB.prepare(
      'UPDATE kullanicilar SET ' + GUNCELLENEBILIR.map((a) => a + ' = ?').join(', ') +
      ', guncelleme = ? WHERE chat_id = ? AND guncelleme = ?',
    ).bind(...GUNCELLENEBILIR.map(deger), yeniZaman, chat_id, s.guncelleme).run();
    if (r && r.meta && r.meta.changes === 0) continue;
    return { ...k, guncelleme: yeniZaman };
  }
  throw new Error('kullanıcı güncellenemedi (çakışma)');
}