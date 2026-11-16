// Profil kartı: /ben/kart, gizlilik, fotoğraf, rozetler, katiplik verisi, başvurular.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { ortam, cagir, uyeGirisi, kayitEskit } from './yardim.js';
import worker from '../src/index.js';
import { ipSinirSifirla } from '../src/hiz.js';
import { katipTemizle, katipOzeti, ozetOku, rozetleriHesapla, fotoTuru, kartTemizle, kartSakla, kartOku } from '../src/kart.js';

const YONETICI = { 'X-Yonetici': 'yonetici-anahtar' };
const dosya = (a) => readFileSync(new URL(a, import.meta.url), 'utf8');
const degisiklik = (env) => env.DB.ham.prepare('SELECT total_changes() AS n').get().n;
const satir = (env, sql, ...b) => env.DB.ham.prepare(sql).get(...b);
const PROFIL = { v: 1, ogrenim: 'lisans', puan_turu: 'P3', iller: ['Ankara', 'İstanbul'], tum_turkiye: false, bolum: 'Bilgisayar', t: '2026-11-01', puan: 78.5 };

// ham gövdeli istek (fotoğraf yükleme)
async function ham(env, yontem, yol, { token, bayt, basliklar = {} } = {}) {
  const h = { ...basliklar };
  if (token) h.Authorization = `Bearer ${token}`;
  const bekleyen = [];
  const r = await worker.fetch(new Request(`https://forum-api.kpsstercihi.com${yol}`, { method: yontem, headers: h, body: bayt }), env, { waitUntil: (p) => bekleyen.push(p) });
  await Promise.all(bekleyen);
  const b = new Uint8Array(await r.arrayBuffer());
  let json = null;
  try { json = JSON.parse(new TextDecoder().decode(b)); } catch { /* ikili */ }
  return { durum: r.status, json, basliklar: r.headers, bayt: b };
}
const webp = (n = 400) => { const b = new Uint8Array(n); b.set([0x52, 0x49, 0x46, 0x46, 1, 0, 0, 0, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50, 0x38, 0x20]); for (let i = 16; i < n; i++) b[i] = i % 251; return b; };
const jpeg = (n = 300) => { const b = new Uint8Array(n); b.set([0xff, 0xd8, 0xff, 0xe0]); return b; };
const png = (n = 300) => { const b = new Uint8Array(n); b.set([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]); return b; };
async function yetiskinUye(env, rumuz) {   // 24 saatten eski hesap
  const u = await uyeGirisi(env, rumuz);
  kayitEskit(env, u.id);
  return u;
}

// ---------- kart kaydı ----------
test('/ben/kart: kaydeder, /ben döner; varsayılanlar yazılmaz, tam değiştirme', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Kart_Sahibi');
  assert.equal((await cagir(env, 'POST', '/ben/kart', { govde: { avatar: 'kedi:mavi' } })).durum, 401);
  const b0 = (await cagir(env, 'GET', '/ben', { token: u.token })).json;
  assert.equal(b0.kart.avatar, null); assert.equal(b0.kart.durum, null); assert.deepEqual(b0.kart.gizlilik, { profil: 'herkes', puan_goster: false, il_goster: true, katiplik_goster: true });
  assert.deepEqual(b0.basvurular, []);
  const g = { avatar: { k: 'kedi', r: 'mavi' }, hakkimda: '  Adalet   katipliği hedefliyorum.  ', hedef: 'Ankara adliye katipliği', durum: 'basvuru-yapiyorum', kart_rengi: 'mor', gizlilik: { profil: 'uyeler', puan_goster: true, il_goster: false, katiplik_goster: true } };
  const r = await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: g });
  assert.equal(r.durum, 200);
  assert.equal(r.json.kart.avatar, 'kedi:mavi'); assert.equal(r.json.kart.hakkimda, 'Adalet katipliği hedefliyorum.');
  assert.equal(r.json.kart.durum, 'basvuru-yapiyorum'); assert.equal(r.json.kart.kart_rengi, 'mor');
  assert.deepEqual(r.json.kart.gizlilik, { profil: 'uyeler', puan_goster: true, il_goster: false, katiplik_goster: true });
  const ben = (await cagir(env, 'GET', '/ben', { token: u.token })).json;
  assert.deepEqual(ben.kart, r.json.kart);
  assert.equal(ben.uye.av, 'kedi:mavi');
  // yalnız varsayılan dışı alanlar saklanır
  const sakli = JSON.parse(satir(env, 'SELECT kart FROM uyeler WHERE id = ?', u.id).kart);
  assert.deepEqual(sakli.gizlilik, { profil: 'uyeler', puan_goster: true, il_goster: false });
  // tam değiştirme: eksik alanlar temizlenir
  const r2 = await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: null } });
  assert.equal(r2.durum, 200); assert.equal(r2.json.kart.hakkimda, ''); assert.equal(r2.json.kart.avatar, null);
  assert.equal(satir(env, 'SELECT kart FROM uyeler WHERE id = ?', u.id).kart, null);
});

test('/ben/kart: geçersiz alanlar 400, hakkımda denetimi 422, bozuk istek eskisini bozmaz', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Kart_Kontrol');
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'tilki:sari', hakkimda: 'Merhaba herkese' } });
  const kotuler = [
    { avatar: 'KEDI:mavi' }, { avatar: 'kedi' }, { avatar: 'kedi:Mavi' }, { avatar: 'a'.repeat(25) + ':mavi' }, { avatar: 5 }, { avatar: ['kedi', 'mavi'] }, { avatar: 'foto' },
    { durum: 'bilinmeyen' }, { durum: 5 }, { kart_rengi: 'kirmizi-ozel' }, { kart_rengi: 5 },
    { gizlilik: { profil: 'arkadaslar' } }, { gizlilik: { puan_goster: 'evet' } }, { gizlilik: 'x' }, { gizlilik: [] },
    { hakkimda: 'a'.repeat(161) }, { hakkimda: 5 }, { hedef: 'b'.repeat(61) },
  ];
  for (const k of kotuler) {
    ipSinirSifirla();
    assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: k })).durum, 400, JSON.stringify(k));
  }
  for (const k of [{ hakkimda: 'Beni ara 0532 123 45 67' }, { hakkimda: 'siteme bak www.ornek.com' }, { hedef: 'mail: ben@ornek.com' }]) {
    ipSinirSifirla();
    assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: k })).durum, 422, JSON.stringify(k));
  }
  assert.equal(satir(env, 'SELECT avatar FROM uyeler WHERE id = ?', u.id).avatar, 'tilki:sari');
  assert.equal(JSON.parse(satir(env, 'SELECT kart FROM uyeler WHERE id = ?', u.id).kart).hakkimda, 'Merhaba herkese');
});

test('/ben/kart: Piixpal avatarı izin listesiyle doğrulanır (ad, biçim, ton), nesne biçimi de kabul edilir', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Piksel_Uye');
  for (const iyi of ['px.loaf:pixel.0', 'px.wizard:voxel.270', 'px.tofu:halftone.45', { set: 'px', k: 'robo', r: 'dots', renk: 135 }]) {
    ipSinirSifirla();
    const r = await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: iyi } });
    assert.equal(r.durum, 200, JSON.stringify(iyi));
    assert.match(r.json.kart.avatar, /^px\.[a-z]+:[a-z]+\.\d+$/);
  }
  assert.equal((await cagir(env, 'GET', '/ben', { token: u.token })).json.uye.av, 'px.robo:dots.135');
  for (const kotu of ['px.loti:pixel.0', 'px.loaf:neon.0', 'px.loaf:pixel.17', 'px.loaf:pixel.360', 'px.loaf:pixel.045', 'px.loaf:pixel', 'px.:pixel.0', 'px.LOAF:pixel.0', 'px.loaf:pixel.0.0', 'px.<b>:pixel.0',
    { set: 'px', k: 'loti' }, { set: 'px', k: 'loaf', r: 'x' }, { set: 'px', k: 'loaf', renk: 7 }, { set: 'px', k: 'loaf', renk: 'kirmizi' }]) {
    ipSinirSifirla();
    assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: kotu } })).durum, 400, JSON.stringify(kotu));
  }
  assert.equal((await cagir(env, 'GET', '/uye/Piksel_Uye')).json.av, 'px.robo:dots.135');
  const t = Math.floor(Date.now() / 1000);
  const b = Number(env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('puan', 'Piksel başlığı deneme', 'gövde', ?, ?, ?)").run(u.id, t, t).lastInsertRowid);
  assert.equal((await cagir(env, 'GET', `/baslik/${b}`)).json.baslik.av, 'px.robo:dots.135');   // yazar çıktısı en küçük avatar bilgisini taşır
});

test('/ben/kart: değişmediyse yazma yok, üye başına dakikada 10 kayıt, engelli üye 403', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Kart_Tasarruf');
  const g = { avatar: 'kedi:mavi', hakkimda: 'Selam', durum: 'basvurdum' };
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: g });
  const once = degisiklik(env);
  assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: g })).durum, 200);
  assert.equal(degisiklik(env), once);
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { ...g, hakkimda: 'Başka' } });
  assert.equal(degisiklik(env), once + 1);
  for (let i = 0; i < 7; i++) assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: g })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: g })).durum, 429);
  ipSinirSifirla();
  env.DB.ham.prepare('UPDATE uyeler SET engelli = 1 WHERE id = ?').run(u.id);
  assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: g })).durum, 403);
});

test('kartTemizle / kartSakla / kartOku: saf işlevler', () => {
  const s = kartTemizle({ avatar: 'foto', durum: 'atandim' }, false);
  assert.equal(s.hata.status, 400);
  const t = kartTemizle({ avatar: 'foto', durum: 'atandim' }, true);
  assert.equal(t.avatar, 'foto'); assert.equal(t.kart.durum, 'atandim');
  assert.equal(kartSakla(kartOku(null)), null);
  assert.deepEqual(kartOku('{bozuk'), kartOku(null));
  assert.equal(kartOku('{"durum":"x","kart_rengi":"y"}').durum, null);
  assert.equal(kartOku(JSON.stringify({ hakkimda: 'x'.repeat(500) })).hakkimda.length, 160);
});

// ---------- gizlilik ----------
test('/uye/:rumuz gizlilik: herkes tam; puan varsayılan gizli, il görünür; uyeler girişsize kısıtlı; gizli yalnız rumuz+avatar; kendi kartı tam', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Gizli_Deneme');
  const bakan = await uyeGirisi(env, 'Bakan_Uye');
  await cagir(env, 'POST', '/ben/profil', { token: u.token, govde: { profil: PROFIL } });
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'kedi:mavi', hakkimda: 'Selam, ben katip adayıyım', hedef: 'Adliye', durum: 'yerlestim', kart_rengi: 'mavi' } });
  let r = (await cagir(env, 'GET', '/uye/Gizli_Deneme')).json;
  assert.equal(r.duzey, 'lisans'); assert.deepEqual(r.iller, ['Ankara', 'İstanbul']); assert.equal(r.puan, undefined); assert.equal(r.puan_turu, undefined);
  assert.equal(r.hakkimda, 'Selam, ben katip adayıyım'); assert.equal(r.hedef, 'Adliye'); assert.equal(r.durum, 'yerlestim'); assert.equal(r.kart_rengi, 'mavi'); assert.equal(r.av, 'kedi:mavi');
  assert.ok(r.rozetler.includes('yerlesti'));
  assert.equal(r.gizlilik, undefined);   // gizlilik ayarları yalnız sahibine döner
  // puan açık, il kapalı
  ipSinirSifirla();
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'kedi:mavi', durum: 'yerlestim', gizlilik: { puan_goster: true, il_goster: false } } });
  r = (await cagir(env, 'GET', '/uye/Gizli_Deneme')).json;
  assert.equal(r.puan, 78.5); assert.equal(r.puan_turu, 'P3'); assert.equal(r.iller, undefined); assert.equal(r.il_sayisi, undefined); assert.equal(r.duzey, 'lisans');
  // uyeler
  ipSinirSifirla();
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'kedi:mavi', hakkimda: 'Gizli metin', gizlilik: { profil: 'uyeler' } } });
  const anon = (await cagir(env, 'GET', '/uye/Gizli_Deneme')).json;
  assert.deepEqual(Object.keys(anon).sort(), ['av', 'dm_acik', 'kisitli', 'rol', 'rumuz']);
  assert.equal(anon.kisitli, 'uyeler');
  const uye = (await cagir(env, 'GET', '/uye/Gizli_Deneme', { token: bakan.token })).json;
  assert.equal(uye.hakkimda, 'Gizli metin'); assert.equal(uye.kisitli, undefined);
  // gizli
  ipSinirSifirla();
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'kedi:mavi', hakkimda: 'Gizli metin', gizlilik: { profil: 'gizli' } } });
  const gz = (await cagir(env, 'GET', '/uye/Gizli_Deneme', { token: bakan.token })).json;
  assert.deepEqual(Object.keys(gz).sort(), ['av', 'dm_acik', 'kisitli', 'rol', 'rumuz']);
  assert.equal(gz.kisitli, 'gizli');
  assert.ok(!JSON.stringify(gz).includes('Gizli metin') && !JSON.stringify(gz).includes('Ankara'));
  // kendi kartı her zaman tam ve gizlilik ayarlarını içerir
  const ben = (await cagir(env, 'GET', '/uye/Gizli_Deneme', { token: u.token })).json;
  assert.equal(ben.hakkimda, 'Gizli metin'); assert.equal(ben.gizlilik.profil, 'gizli');
});

test('/uye/:rumuz: anonim önbelleği kısıtlı görünümü saklar; girişli istek önbelleğe girmez', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Onbellek_Gizli');
  const bakan = await uyeGirisi(env, 'Onbellek_Bakan');
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { hakkimda: 'özel metin', gizlilik: { profil: 'uyeler' } } });
  const c = globalThis.caches; const depo = new Map();
  globalThis.caches = { default: { match: async (k) => depo.get(k.url)?.clone(), put: async (k, v) => { depo.set(k.url, v); } } };
  try {
    const a = await cagir(env, 'GET', '/uye/Onbellek_Gizli');
    assert.equal(a.json.kisitli, 'uyeler');
    const b = await cagir(env, 'GET', '/uye/Onbellek_Gizli', { token: bakan.token });
    assert.equal(b.json.hakkimda, 'özel metin');
    assert.equal(depo.size, 1);
    assert.equal((await cagir(env, 'GET', '/uye/Onbellek_Gizli')).json.hakkimda, undefined);
  } finally { globalThis.caches = c; }
});

test('/uye/:rumuz?tam=1: son sorular ve en faydalı cevaplar; sohbet odası mesajları sayılmaz', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Tam_Sayfa');
  const t = Math.floor(Date.now() / 1000);
  const baslik = (kat, ad) => Number(env.DB.ham.prepare('INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES (?, ?, ?, ?, ?, ?)').run(kat, ad, 'gövde', u.id, t, t).lastInsertRowid);
  const s1 = baslik('puan', 'Birinci soru başlığı'), s2 = baslik('puan', 'İkinci soru başlığı'), oda = baslik('oda', 'Oda başlığı deneme');
  const y = (b, g, f) => env.DB.ham.prepare('INSERT INTO yanitlar (baslik_id, uye_id, govde, olusma, faydali) VALUES (?, ?, ?, ?, ?)').run(b, u.id, g, t, f);
  y(s1, 'cevap bir', 3); y(s2, 'cevap iki', 7); y(oda, 'sohbet bir', 9); y(oda, 'sohbet iki', 0);
  const r = (await cagir(env, 'GET', '/uye/Tam_Sayfa?tam=1')).json;
  assert.equal(r.soru_sayisi, 2); assert.equal(r.sohbet_sayisi, 2); assert.equal(r.cevap_sayisi, 2); assert.equal(r.mesaj_sayisi, 4);
  assert.deepEqual(r.sorular.map((x) => x.id), [s2, s1]);
  assert.deepEqual(r.cevaplar.map((x) => x.faydali), [7, 3]);   // oda cevabı (9) listede yok
  assert.equal(r.cevaplar[0].baslik, 'İkinci soru başlığı');
  assert.ok(r.rozetler.includes('ilk-soru') && r.rozetler.includes('ilk-cevap'));
  assert.equal((await cagir(env, 'GET', '/uye/Tam_Sayfa')).json.sorular, undefined);
});

// ---------- rozetler ----------
test('rozetleriHesapla: eşikler, en yüksek kademe tek rozet, sıra, beyan rozetleri', () => {
  assert.deepEqual(rozetleriHesapla({}), []);
  assert.deepEqual(rozetleriHesapla({ kurucu: true, soru: 1 }), ['kurucu', 'ilk-soru']);
  assert.deepEqual(rozetleriHesapla({ cevap: 3 }), ['ilk-cevap']);
  assert.deepEqual(rozetleriHesapla({ itibar: 4 }), []);
  assert.deepEqual(rozetleriHesapla({ itibar: 5 }), ['faydali-5']);
  assert.deepEqual(rozetleriHesapla({ itibar: 25 }), ['faydali-25']);
  assert.deepEqual(rozetleriHesapla({ itibar: 100 }), ['faydali-100']);
  assert.deepEqual(rozetleriHesapla({ sohbet: 99 }), []);
  assert.deepEqual(rozetleriHesapla({ sohbet: 100 }), ['sohbet-nesesi']);
  assert.deepEqual(rozetleriHesapla({ katip: { dk: 39, s30: 0, ders: 3 } }), []);
  assert.deepEqual(rozetleriHesapla({ katip: { dk: 40, s30: 0, ders: 0 } }), ['katip-hiz-40']);
  assert.deepEqual(rozetleriHesapla({ katip: { dk: 65, s30: 0, ders: 0 } }), ['katip-hiz-60']);
  assert.deepEqual(rozetleriHesapla({ katip: { dk: 80, s30: 1, ders: 16 } }), ['katip-hiz-80', 'katip-seri-30', 'ders-yildizi']);
  assert.deepEqual(rozetleriHesapla({ durum: 'yerlestim' }), ['yerlesti']);
  assert.deepEqual(rozetleriHesapla({ durum: 'atandim' }), ['atandi']);
  assert.deepEqual(rozetleriHesapla({ durum: 'calisiyorum' }), []);
  assert.deepEqual(rozetleriHesapla({ kurucu: true, itibar: 30, soru: 2, cevap: 2, sohbet: 120, katip: { dk: 90, s30: 1, ders: 16 }, durum: 'atandim' }),
    ['kurucu', 'faydali-25', 'katip-hiz-80', 'katip-seri-30', 'ders-yildizi', 'sohbet-nesesi', 'ilk-cevap', 'ilk-soru', 'atandi']);
});

// ---------- fotoğraf ----------
test('fotoTuru: yalnız WebP / JPEG / PNG sihirli baytları', () => {
  assert.equal(fotoTuru(webp()), 'image/webp'); assert.equal(fotoTuru(jpeg()), 'image/jpeg'); assert.equal(fotoTuru(png()), 'image/png');
  assert.equal(fotoTuru(new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg"></svg>')), null);
  assert.equal(fotoTuru(new TextEncoder().encode('GIF89a......')), null);
  assert.equal(fotoTuru(new TextEncoder().encode('RIFF....WAVE....')), null);
  assert.equal(fotoTuru(new Uint8Array(0)), null); assert.equal(fotoTuru(new Uint8Array([0xff, 0xd8])), null);
});

test('foto yükleme: 24 saatten genç hesap 403, yetişkin hesap 201; avatar foto olur; /ben ve yazar çıktısı sürümü taşır', async () => {
  const env = ortam();
  const yeni = await uyeGirisi(env, 'Yeni_Hesap');
  const r0 = await ham(env, 'POST', '/ben/foto', { token: yeni.token, bayt: webp() });
  assert.equal(r0.durum, 403); assert.match(r0.json.hata, /24 saat/);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM fotolar').n, 0);
  const u = await yetiskinUye(env, 'Eski_Hesap');
  assert.equal((await ham(env, 'POST', '/ben/foto', { bayt: webp() })).durum, 401);
  const r = await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() });
  assert.equal(r.durum, 201); assert.equal(r.json.avatar, 'foto'); assert.ok(r.json.foto_surum > 0); assert.equal(r.json.kalan, 2);
  const ben = (await cagir(env, 'GET', '/ben', { token: u.token })).json;
  assert.equal(ben.kart.avatar, 'foto'); assert.equal(ben.kart.foto_surum, r.json.foto_surum); assert.equal(ben.uye.av, 'foto'); assert.equal(ben.uye.fs, r.json.foto_surum);
  const t = Math.floor(Date.now() / 1000);
  const b = Number(env.DB.ham.prepare("INSERT INTO basliklar (kategori, baslik, govde, uye_id, olusma, son_hareket) VALUES ('puan', 'Foto başlığı deneme', 'gövde', ?, ?, ?)").run(u.id, t, t).lastInsertRowid);
  const baslik = (await cagir(env, 'GET', `/baslik/${b}`)).json;
  assert.equal(baslik.baslik.av, 'foto'); assert.equal(baslik.baslik.fs, r.json.foto_surum); assert.equal(baslik.baslik.fu, u.id);
  const liste = (await cagir(env, 'GET', '/basliklar')).json.basliklar[0];
  assert.equal(liste.fs, r.json.foto_surum);
  // avatar tekrar hazır avatara çevrilir, foto kalır; yeniden 'foto' seçilebilir
  assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'kedi:mavi' } })).json.kart.avatar, 'kedi:mavi');
  assert.equal((await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'foto' } })).json.kart.avatar, 'foto');
});

test('foto yükleme: boyut, sihirli bayt, boş gövde, günlük 3 sınırı', async () => {
  const env = ortam();
  const u = await yetiskinUye(env, 'Foto_Sinir');
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp(24 * 1024 + 1) })).durum, 413);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: new Uint8Array(0) })).durum, 400);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>') })).durum, 415);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: new TextEncoder().encode('GIF89a-------------') })).durum, 415);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp(24 * 1024) })).durum, 201);   // tam sınır
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM fotolar').n, 1);
  for (const f of [jpeg, png]) { ipSinirSifirla(); assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: f() })).durum, 201); }
  ipSinirSifirla();
  const dorduncu = await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() });
  assert.equal(dorduncu.durum, 429); assert.match(dorduncu.json.hata, /3/);
  assert.equal(satir(env, 'SELECT tur FROM fotolar WHERE uye_id = ?', u.id).tur, 'image/png');   // son başarılı yükleme kalır
  // ertesi gün sayaç sıfırlanır
  env.DB.ham.prepare('UPDATE uyeler SET foto_gun = foto_gun - 1 WHERE id = ?').run(u.id);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() })).durum, 201);
});

test('foto yükleme: Content-Length yalan söylese de gövde sınırı uygulanır; sürüm her yüklemede artar', async () => {
  const env = ortam();
  const u = await yetiskinUye(env, 'Foto_Surum');
  const buyuk = new Request('https://forum-api.kpsstercihi.com/ben/foto', { method: 'POST', headers: { Authorization: `Bearer ${u.token}` }, body: new ReadableStream({ start(c) { c.enqueue(webp(20000)); c.enqueue(webp(20000)); c.close(); } }), duplex: 'half' });
  const r = await worker.fetch(buyuk, env, { waitUntil() {} });
  assert.equal(r.status, 413);
  const a = (await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() })).json.foto_surum;
  const b = (await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() })).json.foto_surum;
  assert.ok(b > a);
});

test('GET /foto/:id: üstbilgiler, tür, 404, uç önbelleği, sürüm uyuşmazlığı kısa önbellek', async () => {
  const env = ortam();
  const u = await yetiskinUye(env, 'Foto_Sun');
  const yuk = (await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: jpeg(500) })).json;
  assert.equal((await ham(env, 'GET', '/foto/99?v=1')).durum, 404);
  assert.equal((await ham(env, 'GET', '/foto/abc')).durum, 404);
  const c = globalThis.caches; const depo = new Map();
  globalThis.caches = { default: { match: async (k) => depo.get(k.url)?.clone(), put: async (k, v) => { depo.set(k.url, v); }, delete: async (k) => depo.delete(k.url) } };
  try {
    const r = await ham(env, 'GET', `/foto/${u.id}?v=${yuk.foto_surum}`);
    assert.equal(r.durum, 200);
    assert.equal(r.basliklar.get('Content-Type'), 'image/jpeg');
    assert.equal(r.basliklar.get('Cache-Control'), 'public, max-age=31536000, immutable');
    assert.equal(r.basliklar.get('X-Content-Type-Options'), 'nosniff');
    assert.equal(r.bayt.length, 500); assert.equal(r.bayt[0], 0xff);
    assert.equal(depo.size, 1);
    // ikinci istek uçtan gelir: D1'e sorgu gitmez
    const once = env.DB.sayac.sorgu;
    assert.equal((await ham(env, 'GET', `/foto/${u.id}?v=${yuk.foto_surum}`)).durum, 200);
    assert.equal(env.DB.sayac.sorgu, once);
    // eski / eksik sürüm: güncel görüntü ama değişmez önbellek yok, uca yazılmaz
    const eski = await ham(env, 'GET', `/foto/${u.id}?v=1`);
    assert.equal(eski.durum, 200); assert.equal(eski.basliklar.get('Cache-Control'), 'public, max-age=300');
    assert.equal((await ham(env, 'GET', `/foto/${u.id}`)).basliklar.get('Cache-Control'), 'public, max-age=300');
    assert.equal(depo.size, 1);
  } finally { globalThis.caches = c; }
});

test('DELETE /ben/foto: fotoğrafı siler, avatar foto ise varsayılana döner; fotoğraf yoksa yazma yok', async () => {
  const env = ortam();
  const u = await yetiskinUye(env, 'Foto_Sil');
  const once = degisiklik(env);
  assert.equal((await ham(env, 'DELETE', '/ben/foto', { token: u.token })).durum, 200);
  assert.equal(degisiklik(env), once);
  await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() });
  const r = await ham(env, 'DELETE', '/ben/foto', { token: u.token });
  assert.equal(r.durum, 200); assert.equal(r.json.avatar, null);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM fotolar').n, 0);
  const row = satir(env, 'SELECT avatar, foto_surum FROM uyeler WHERE id = ?', u.id);
  assert.equal(row.avatar, null); assert.equal(row.foto_surum, null);
  assert.equal((await ham(env, 'GET', '/foto/' + u.id + '?v=1')).durum, 404);
  // hazır avatar seçiliyken silmek avatarı değiştirmez
  await ham(env, 'POST', '/ben/foto', { token: u.token, bayt: webp() });
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { avatar: 'kedi:mavi' } });
  assert.equal((await ham(env, 'DELETE', '/ben/foto', { token: u.token })).json.avatar, 'kedi:mavi');
});

test('foto bildir + yönetim: bildirim listesi, kaldır avatarı sıfırlar ve yeni yüklemeyi kapatır', async () => {
  const env = ortam();
  const sahip = await yetiskinUye(env, 'Foto_Sahip');
  const a = await uyeGirisi(env, 'Bildiren_Bir');
  const b = await uyeGirisi(env, 'Bildiren_Iki');
  const yuk = (await ham(env, 'POST', '/ben/foto', { token: sahip.token, bayt: webp() })).json;
  assert.equal((await cagir(env, 'POST', '/uye/Foto_Sahip/foto-bildir')).durum, 401);
  assert.equal((await cagir(env, 'POST', '/uye/Foto_Sahip/foto-bildir', { token: sahip.token })).durum, 400);   // kendi fotoğrafı
  assert.equal((await cagir(env, 'POST', '/uye/Yok_Boyle_Biri/foto-bildir', { token: a.token })).durum, 404);
  assert.equal((await cagir(env, 'POST', '/uye/Bildiren_Bir/foto-bildir', { token: b.token })).durum, 404);   // fotoğrafı yok
  const r1 = await cagir(env, 'POST', '/uye/Foto_Sahip/foto-bildir', { token: a.token });
  assert.equal(r1.durum, 200); assert.equal(r1.json.zaten, false);
  assert.equal((await cagir(env, 'POST', '/uye/Foto_Sahip/foto-bildir', { token: a.token })).json.zaten, true);   // aynı kişi tekrar sayılmaz
  await cagir(env, 'POST', '/uye/Foto_Sahip/foto-bildir', { token: b.token });
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM foto_bildirimleri').n, 2);
  assert.equal((await cagir(env, 'GET', '/yonetim/foto-bildirimleri')).durum, 401);
  const l = (await cagir(env, 'GET', '/yonetim/foto-bildirimleri', { basliklar: YONETICI })).json.fotolar;
  assert.equal(l.length, 1); assert.equal(l[0].rumuz, 'Foto_Sahip'); assert.equal(l[0].bildirim, 2); assert.equal(l[0].foto, `/foto/${sahip.id}?v=${yuk.foto_surum}`);
  // yeni fotoğraf yüklenince eski bildirimler listede görünmez
  await ham(env, 'POST', '/ben/foto', { token: sahip.token, bayt: jpeg() });
  assert.equal((await cagir(env, 'GET', '/yonetim/foto-bildirimleri', { basliklar: YONETICI })).json.fotolar.length, 0);
  await cagir(env, 'POST', '/uye/Foto_Sahip/foto-bildir', { token: a.token });
  assert.equal((await cagir(env, 'GET', '/yonetim/foto-bildirimleri', { basliklar: YONETICI })).json.fotolar.length, 1);
  // kaldır
  assert.equal((await cagir(env, 'POST', '/yonetim/foto-kaldir', { govde: { uye_id: sahip.id } })).durum, 401);
  assert.equal((await cagir(env, 'POST', '/yonetim/foto-kaldir', { basliklar: YONETICI, govde: { uye_id: 99999 } })).durum, 404);
  const k = await cagir(env, 'POST', '/yonetim/foto-kaldir', { basliklar: YONETICI, govde: { uye_id: sahip.id } });
  assert.equal(k.durum, 200); assert.equal(k.json.yasak, true);
  const row = satir(env, 'SELECT avatar, foto_surum, foto_yasak FROM uyeler WHERE id = ?', sahip.id);
  assert.equal(row.avatar, null); assert.equal(row.foto_surum, null); assert.equal(row.foto_yasak, 1);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM fotolar').n, 0);
  assert.equal(satir(env, 'SELECT COUNT(*) AS n FROM foto_bildirimleri').n, 0);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: sahip.token, bayt: webp() })).durum, 403);   // yasak
  // yönetici yasağı kaldırabilir (rumuzla da bulunur)
  assert.equal((await cagir(env, 'POST', '/yonetim/foto-kaldir', { basliklar: YONETICI, govde: { rumuz: 'Foto_Sahip', yasak: false } })).json.yasak, false);
  assert.equal((await ham(env, 'POST', '/ben/foto', { token: sahip.token, bayt: webp() })).durum, 201);
  // sistem hesapları kaldırılmaz
  assert.equal((await cagir(env, 'POST', '/yonetim/foto-kaldir', { basliklar: YONETICI, govde: { uye_id: 1 } })).durum, 404);
});

// ---------- başvurular ----------
const U1 = '9c82aab5-022e-43c8-b7f1-e6cf329d205b', SBB = `sbb-${'a1b2c3d4e5f6'.repeat(2)}`, CSB = 'csb-12345';
test('/ben/basvurular: kaydeder, /ben döner; geçersiz atılır, 300 sınırı, bozuk 400, değişmedi yazma yok', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Basvuru_Uyesi');
  assert.equal((await cagir(env, 'POST', '/ben/basvurular', { govde: { basvurular: [U1] } })).durum, 401);
  const r = await cagir(env, 'POST', '/ben/basvurular', { token: u.token, govde: { basvurular: [U1, SBB, U1, 'x', '<script>', 5, CSB] } });
  assert.equal(r.durum, 200); assert.deepEqual(r.json.basvurular, [U1, SBB, CSB]);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token: u.token })).json.basvurular, [U1, SBB, CSB]);
  const once = degisiklik(env);
  await cagir(env, 'POST', '/ben/basvurular', { token: u.token, govde: { basvurular: [U1, SBB, CSB] } });
  assert.equal(degisiklik(env), once);
  for (const kotu of [{}, { basvurular: 'x' }, { basvurular: {} }, { basvurular: Array.from({ length: 700 }, (_, i) => `csb-${10000 + i}`) }]) {
    ipSinirSifirla();
    assert.equal((await cagir(env, 'POST', '/ben/basvurular', { token: u.token, govde: kotu })).durum, 400, JSON.stringify(kotu).slice(0, 40));
  }
  ipSinirSifirla();
  const tam = Array.from({ length: 300 }, (_, i) => `csb-${10000 + i}`);
  assert.equal((await cagir(env, 'POST', '/ben/basvurular', { token: u.token, govde: { basvurular: tam } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/basvurular', { token: u.token, govde: { basvurular: [...tam, 'csb-99999'] } })).durum, 400);
  assert.equal((await cagir(env, 'POST', '/ben/basvurular', { token: u.token, govde: { basvurular: [] } })).json.basvurular.length, 0);
  assert.deepEqual((await cagir(env, 'GET', '/ben', { token: u.token })).json.basvurular, []);
});

// ---------- katiplik ----------
const AN = 1790000000000;
const gecmis = (n, ek = {}) => Array.from({ length: n }, (_, i) => ({ t: AN - i * 3600000, m: 'sinav', s: 180, top: 120, hat: 4, atl: 0, net: 100 + (i % 7), dk: 40 + (i % 5), b: 1, no: i % 30, k: 'zk2025', ...ek }));
const katipVerisi = (ek = {}) => ({
  v: 1,
  k: { gecmis: gecmis(5), hatalar: { kelime: 3, başka: 1 }, rozetler: ['ilk', 'seri30'], gunluk: { '2026-11-10': { net: 100, top: 120, hat: 4, b: 1 } }, yol: { tarih: '2026-12-01', hedef: 100, g: 5 }, ayar: { klavye: 'F' } },
  d: { Q: { 0: { y: 3, t: AN }, 1: { y: 2, t: AN } } }, o: { dosya: 120, hata: 80 }, a: { rekor: { hiz: 55 }, gecmis: [{ t: AN, m: 'hiz', net: 55, n: 60, h: 5, s: 60 }] }, ...ek,
});
test('katipTemizle: sınırlar (200 geçmiş, 100 hata, 120 gün), geçersiz kayıtlar atılır, 32 KB', () => {
  const k = katipTemizle({ v: 1, k: {
    gecmis: [...gecmis(260), { t: 5, m: 'sinav' }, { t: AN, m: 'KOTU AD' }, null, 'x', { m: 'sinav' }],
    hatalar: Object.fromEntries(Array.from({ length: 150 }, (_, i) => [`kelime${String.fromCharCode(97 + (i % 26))}${String.fromCharCode(97 + Math.floor(i / 26))}`.replace(/\d/g, ''), i + 1])),
    rozetler: ['ilk', 'ilk', 'x y', 5, 'seri30'], gunluk: Object.fromEntries(Array.from({ length: 150 }, (_, i) => [`2026-${String(1 + Math.floor(i / 28)).padStart(2, '0')}-${String(1 + (i % 28)).padStart(2, '0')}`, { net: i, top: 1, hat: 0, b: 1 }])),
    yol: { tarih: 'saçma', hedef: 5000 },
  } });
  assert.equal(k.k.gecmis.length, 200); assert.ok(k.k.gecmis[0].t > k.k.gecmis[199].t);
  assert.ok(Object.keys(k.k.hatalar).length <= 100); assert.equal(Math.max(...Object.values(k.k.hatalar)), 150);
  assert.deepEqual(k.k.rozetler, ['ilk', 'seri30']);
  assert.equal(Object.keys(k.k.gunluk).length, 120); assert.ok(!('2026-01-01' in k.k.gunluk));
  assert.equal(k.k.yol.tarih, ''); assert.equal(k.k.yol.hedef, 90);
  assert.ok(JSON.stringify(k).length <= 32768);
  assert.equal(katipTemizle(null), null); assert.equal(katipTemizle([]), null); assert.equal(katipTemizle('x'), null);
  assert.equal(katipTemizle({}).k.gecmis.length, 0);
});

test('/ben/katip: kaydeder, GET döner; değişmediyse yazma yok; 401, 413, hız sınırı', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Katip_Uyesi');
  assert.equal((await cagir(env, 'GET', '/ben/katip')).durum, 401);
  assert.equal((await cagir(env, 'POST', '/ben/katip', { govde: { katip: katipVerisi() } })).durum, 401);
  assert.equal((await cagir(env, 'GET', '/ben/katip', { token: u.token })).json.katip, null);
  const r = await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: katipVerisi() } });
  assert.equal(r.durum, 200);
  const g = (await cagir(env, 'GET', '/ben/katip', { token: u.token })).json.katip;
  assert.equal(g.k.gecmis.length, 5); assert.equal(g.k.yol.hedef, 100); assert.equal(g.d.Q[0].y, 3); assert.equal(g.o.dosya, 120); assert.equal(g.a.rekor.hiz, 55);
  const once = degisiklik(env);
  assert.equal((await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: katipVerisi() } })).durum, 200);
  assert.equal(degisiklik(env), once);
  await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: katipVerisi({ o: { dosya: 121, hata: 80 } }) } });
  assert.equal(degisiklik(env), once + 1);
  // /ben küçük kalır: katiplik verisi içermez
  assert.ok(!('katip' in (await cagir(env, 'GET', '/ben', { token: u.token })).json));
  ipSinirSifirla();
  for (const kotu of [{}, { katip: 5 }, { katip: [] }, { katip: 'x' }]) assert.equal((await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: kotu })).durum, 400, JSON.stringify(kotu));
  const dev = { katip: { v: 1, k: { gecmis: [], hatalar: {}, rozetler: [], gunluk: {}, yol: {} }, junk: 'x'.repeat(70000) } };
  assert.equal((await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: dev })).durum, 413);
  ipSinirSifirla();
  for (let i = 0; i < 10; i++) assert.equal((await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: katipVerisi({ o: { dosya: 200 + i, hata: 1 } }) } })).durum, 200);
  assert.equal((await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: katipVerisi() } })).durum, 429);
});

test('/ben/katip: en kötü durum 32 KB altında kalır (200 geçmiş + 120 gün + 100 hata)', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Katip_Dolu');
  const k = katipVerisi();
  k.k.gecmis = gecmis(200); k.k.hatalar = Object.fromEntries(Array.from({ length: 100 }, (_, i) => [`çalışmadığımız${String.fromCharCode(97 + (i % 26))}${String.fromCharCode(97 + Math.floor(i / 26))}`, 9999]));
  k.k.gunluk = Object.fromEntries(Array.from({ length: 120 }, (_, i) => [`2026-${String(1 + Math.floor(i / 28)).padStart(2, '0')}-${String(1 + (i % 28)).padStart(2, '0')}`, { net: 100, top: 120, hat: 4, b: 1 }]));
  const r = await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: k } });
  assert.equal(r.durum, 200);
  assert.ok(satir(env, 'SELECT length(veri) AS n FROM uye_katip WHERE uye_id = ?', u.id).n <= 32768);
});

test('katiplik özeti kartta: en iyi net, net/dk, ders, seri; gizlilik kapatınca görünmez; rozetler', async () => {
  const env = ortam();
  const u = await uyeGirisi(env, 'Katip_Karti');
  const bakan = await uyeGirisi(env, 'Katip_Bakan');
  const simdiMs = Date.now();
  const k = katipVerisi();
  k.k.gecmis = [0, 1, 2].map((i) => ({ t: simdiMs - i * 86400000, m: 'sinav', net: 100 + i, dk: i === 0 ? 85 : 50, top: 120, hat: 3, b: 1 }));
  k.d = { Q: Object.fromEntries(Array.from({ length: 16 }, (_, i) => [i, { y: 3, t: AN }])) };
  k.k.rozetler = ['seri30'];
  assert.equal((await cagir(env, 'POST', '/ben/katip', { token: u.token, govde: { katip: k } })).durum, 200);
  let r = (await cagir(env, 'GET', '/uye/Katip_Karti')).json;
  assert.deepEqual(r.katip, { net: 102, dk: 85, ders: 16, seri: 3 });
  for (const x of ['katip-hiz-80', 'katip-seri-30', 'ders-yildizi']) assert.ok(r.rozetler.includes(x), x);
  ipSinirSifirla();
  await cagir(env, 'POST', '/ben/kart', { token: u.token, govde: { gizlilik: { katiplik_goster: false } } });
  r = (await cagir(env, 'GET', '/uye/Katip_Karti', { token: bakan.token })).json;
  assert.equal(r.katip, undefined); assert.ok(!r.rozetler.some((x) => x.startsWith('katip') || x === 'ders-yildizi'));
  const ben = (await cagir(env, 'GET', '/uye/Katip_Karti', { token: u.token })).json;   // sahibi görür, kapalı olduğu işaretli
  assert.equal(ben.katip.net, 102); assert.equal(ben.katip_gizli, true);
});

test('katipOzeti / ozetOku: seri bugün ya da dünden sayılır, eskiyse 0; yalnız sınav ve günün metni net sayılır', () => {
  const bugun = Date.parse('2026-11-16T12:00:00+03:00');
  const t = katipTemizle({ v: 1, k: { gecmis: [
    { t: bugun, m: 'sinav', net: 90, dk: 50 }, { t: bugun - 86400000, m: 'gunluk', net: 95, dk: 52 }, { t: bugun - 2 * 86400000, m: 'antrenman', net: 300, dk: 300 }, { t: bugun - 4 * 86400000, m: 'sinav', net: 10, dk: 5 },
  ], rozetler: [] }, d: { F: { 0: { y: 1, t: bugun }, 1: { y: 1, t: bugun } } } });
  const o = katipOzeti(t, Math.floor(bugun / 1000));
  assert.equal(o.net, 95); assert.equal(o.dk, 52); assert.equal(o.seri, 3); assert.equal(o.ders, 2); assert.equal(o.s30, 0);
  const metin = JSON.stringify(o);
  assert.equal(ozetOku(metin, Math.floor(bugun / 1000)).seri, 3);
  assert.equal(ozetOku(metin, Math.floor(bugun / 1000) + 86400).seri, 3);   // dün de etkinlik vardı: seri sürüyor
  assert.equal(ozetOku(metin, Math.floor(bugun / 1000) + 3 * 86400).seri, 0);   // iki gün hiçbir şey yok: seri bozuldu
  assert.equal(ozetOku('bozuk', 1), null);
});

// ---------- göç ----------
test('0005 göçü: eski şemaya uygulanınca profil kartı sütunları ve tabloları gelir, tekrar çalıştırmak ALTER dışında zararsız', () => {
  const db = new DatabaseSync(':memory:');
  db.exec(dosya('./eski-schema.sql'));
  db.exec(dosya('../migrations/0005_kayit.sql'));
  const sut = db.prepare('PRAGMA table_info(uyeler)').all().map((c) => c.name);
  for (const a of ['avatar', 'foto_surum', 'foto_gun', 'foto_sayi', 'foto_yasak', 'kart', 'basvurular']) assert.ok(sut.includes(a), a);
  for (const t of ['fotolar', 'foto_bildirimleri', 'uye_katip']) assert.ok(db.prepare("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?").get(t), t);
  const sema = new DatabaseSync(':memory:');
  sema.exec(dosya('../schema.sql'));
  const sSut = sema.prepare('PRAGMA table_info(uyeler)').all().map((c) => c.name).sort();
  for (const a of ['avatar', 'foto_surum', 'foto_gun', 'foto_sayi', 'foto_yasak', 'kart', 'basvurular']) assert.ok(sSut.includes(a), a);   // schema.sql de aynı sütunları verir
});
