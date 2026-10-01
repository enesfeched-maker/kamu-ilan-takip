// Günlük sosyal paylaşım: Instagram carousel/tek görsel + yöneticiye X taslağı (SOSYAL.md).
export const IG_API = 'https://graph.instagram.com/v25.0';
const IG_YENILEME_URL = 'https://graph.instagram.com/refresh_access_token'; // dokümanda sürümsüz
const IG_YENILEME_GUN = 50;
const DENEME_ARALIGI_MS = 10 * 60 * 1000;
const IG_YOKLAMA_MAX = 6;
const IG_YOKLAMA_BEKLE_MS = 5000;
const PENCERE_DAKIKA = 10 * 60 + 15; // İstanbul 10:15

export function istanbulDakika(simdi) {
  const p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Istanbul', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(simdi);
  return Number(p.find((x) => x.type === 'hour').value) * 60 + Number(p.find((x) => x.type === 'minute').value);
}

export function sosyalZamaniGeldi(simdi, bugun, meta) {
  return istanbulDakika(simdi) >= PENCERE_DAKIKA && meta.sosyal_son_gun !== bugun;
}

// Telegram kullanıcı adı yönetici ise chat_id'yi meta'ya BİR KEZ yazar (kalıcı; değiştirmek için D1'den elle silinir). Log yok.
export async function yoneticiTani(env, update) {
  const m = update && update.message;
  const ad = env.YONETICI_KULLANICI && String(env.YONETICI_KULLANICI).replace(/^@/, '').toLowerCase();
  if (!m || !ad || !m.chat || m.chat.type !== 'private' || !m.from || !m.from.username) return;
  if (String(m.from.username).toLowerCase() !== ad) return;
  await env.DB.prepare("INSERT OR IGNORE INTO meta (anahtar, deger) VALUES ('yonetici_chat', ?)").bind(String(m.chat.id)).run();
}

// Hata metninden token'ı ve token içeren alanları temizler, kısaltır.
export function guvenliMetin(metin, ...gizliler) {
  let s = String(metin ?? '');
  for (const g of gizliler) if (g) s = s.split(g).join('***');
  s = s.replace(/("?access_token"?\s*[:=]\s*)"?[^"&,}\s]+"?/gi, '$1***').replace(/(IG[A-Za-z0-9_-]{20,})/g, '***');
  return s.replace(/\s+/g, ' ').slice(0, 140);
}

// ctx: { env, simdi, bugun, meta, metaYaz, fetch, tg, bekle, kilitUzat } (cron sayaçlı sürümleri verir)
// Dönüş: true = cron bu çağrıda başka iş yapmadan dönmeli, false = normal akış sürsün.
export async function sosyalIsle(ctx) {
  const { env, bugun, meta, metaYaz, fetch: ag, tg, bekle } = ctx;
  const simdiMs = ctx.simdi.getTime();
  const simdiIso = ctx.simdi.toISOString();

  const sir = meta.ig_token || env.IG_TOKEN;
  const tokenGerek = !!(sir && env.IG_USER_ID && meta.ig_token_gunu !== bugun);
  const sonDeneme = Date.parse(meta.sosyal_son_deneme);
  const denemeGerek = !(Number.isFinite(sonDeneme) && simdiMs - sonDeneme < DENEME_ARALIGI_MS);
  if (!tokenGerek && !denemeGerek) return false;

  // Sosyal adım uzun sürebilir (çocuklar + yoklama): kilidi uzat; kaybedildiyse bırak.
  if (ctx.kilitUzat && !(await ctx.kilitUzat())) return true;

  const yonetici = meta.yonetici_chat ? Number(meta.yonetici_chat) : null;
  const yoneticiyeYaz = async (metin) => {
    if (!yonetici) return;
    try { await tg(env, 'sendMessage', { chat_id: yonetici, text: metin }); } catch { /* yoksay */ }
  };

  // ---- Instagram anahtarı: içerikten bağımsız, günde bir kez (ardışık boş günlerde ölmesin)
  if (tokenGerek) {
    let tarih = meta.ig_token_tarih;
    let token = sir;
    // Sırdaki anahtar ilk kullanımda D1'e taşınır; yaşı kurulum anı sayılır.
    if (!meta.ig_token || !Number.isFinite(Date.parse(tarih))) {
      await metaYaz([['ig_token', token], ['ig_token_tarih', simdiIso]]);
      meta.ig_token = token; meta.ig_token_tarih = simdiIso; tarih = simdiIso;
    }
    const yazilacak = [['ig_token_gunu', bugun]];
    if ((simdiMs - Date.parse(tarih)) / 86400000 >= IG_YENILEME_GUN) {
      try {
        const yeni = await igGet(ag, IG_YENILEME_URL, { grant_type: 'ig_refresh_token', access_token: token }, token, 'yenileme');
        if (yeni.access_token) {
          meta.ig_token = yeni.access_token; meta.ig_token_tarih = simdiIso; // yaş: şimdi (expires_in kullanılmaz)
          yazilacak.push(['ig_token', yeni.access_token], ['ig_token_tarih', simdiIso]);
        }
      } catch (e) {
        // Eski anahtarla devam; yöneticiye günde en fazla bir kez bildir.
        yazilacak.push(['ig_son_hata', guvenliMetin(`Anahtar yenilenemedi: ${e && e.message}`, token, sir)], ['ig_yenileme_hata_gunu', bugun]);
        if (meta.ig_yenileme_hata_gunu !== bugun) {
          meta.ig_yenileme_hata_gunu = bugun;
          await yoneticiyeYaz('Instagram anahtarı yenilenemedi');
        }
      }
    }
    await metaYaz(yazilacak);
    meta.ig_token_gunu = bugun;
  }
  if (!denemeGerek) return false;

  // ---- Günlük içerik (en sık 10 dakikada bir denenir)
  await metaYaz([['sosyal_son_deneme', simdiIso]]);
  let veri;
  try {
    const r = await ag(`${env.SITE_URL}paylasim/gunluk.json`);
    if (!r.ok) return false;
    veri = await r.json();
    if (!veri || typeof veri.tarih !== 'string') return false; // beklenen biçimde değil
  } catch { return false; }
  if (veri.tarih !== bugun) return false; // site henüz bugünün dosyasını yayınlamadı: gün kaybolmasın

  await metaYaz([['sosyal_son_gun', bugun]]); // gün için karar verildi; yeniden çağrıda tekrar yok
  if (veri.bos) return true;
  const gorseller = (Array.isArray(veri.gorseller) ? veri.gorseller : []).filter((u) => typeof u === 'string' && u.startsWith('https://')).slice(0, 10);
  if (!gorseller.length) return true;

  // ---- Instagram yayını
  const token0 = meta.ig_token || env.IG_TOKEN;
  if (token0 && env.IG_USER_ID && meta.ig_son_gun !== bugun) {
    const token = token0;
    try {
      await igYayinla({ ag, bekle, env, token, gorseller, metin: String(veri.ig_metin || '') });
      await metaYaz([['ig_son_gun', bugun], ['ig_son_hata', meta.ig_yenileme_hata_gunu === bugun ? 'Anahtar yenilenemedi (eski anahtarla paylaşıldı)' : '']]);
    } catch (e) {
      const kisa = guvenliMetin(e && e.message, token, sir);
      await metaYaz([['ig_son_gun', bugun], ['ig_son_hata', kisa]]); // yeniden denenmez
      await yoneticiyeYaz(`Instagram paylaşımı başarısız: ${kisa}`);
    }
  }

  // ---- X taslağı (yöneticiye)
  if (yonetici && meta.x_son_gun !== bugun && veri.x_metin) {
    try {
      await tg(env, 'sendPhoto', { chat_id: yonetici, photo: gorseller[0], caption: String(veri.x_metin) });
    } catch { /* bir kez denenir */ }
    await metaYaz([['x_son_gun', bugun]]);
  }
  return true;
}
async function igYanit(r, adim, ...gizliler) {
  let g = null;
  let ham = '';
  try { ham = await r.text(); g = JSON.parse(ham); } catch { g = null; }
  if (!r.ok || !g || g.error) {
    const mesaj = g && g.error && g.error.message ? g.error.message : ham;
    throw new Error(`Instagram ${adim} hatası ${r.status}: ${guvenliMetin(mesaj, ...gizliler)}`);
  }
  return g;
}
async function igGet(ag, url, params, token, adim) {
  const r = await ag(`${url}?${new URLSearchParams(params)}`);
  return igYanit(r, adim, token);
}
async function igPost(ag, yol, params, token, adim, env) {
  const r = await ag(`${IG_API}/${env.IG_USER_ID}/${yol}`, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ ...params, access_token: token }).toString(),
  });
  return igYanit(r, adim, token);
}

async function igYayinla({ ag, bekle, env, token, gorseller, metin }) {
  let kapsayici;
  if (gorseller.length === 1) {
    kapsayici = (await igPost(ag, 'media', { image_url: gorseller[0], caption: metin }, token, 'görsel', env)).id;
  } else {
    const cocuklar = [];
    for (const u of gorseller) {
      cocuklar.push((await igPost(ag, 'media', { image_url: u, is_carousel_item: 'true' }, token, 'çocuk', env)).id);
    }
    kapsayici = (await igPost(ag, 'media', { media_type: 'CAROUSEL', children: cocuklar.join(','), caption: metin }, token, 'kapsayıcı', env)).id;
  }
  if (!kapsayici) throw new Error('Instagram kapsayıcı kimliği alınamadı');
  let hazir = false;
  for (let d = 0; d < IG_YOKLAMA_MAX; d++) {
    const g = await igGet(ag, `${IG_API}/${kapsayici}`, { fields: 'status_code', access_token: token }, token, 'durum');
    if (g.status_code === 'FINISHED') { hazir = true; break; }
    if (g.status_code === 'ERROR' || g.status_code === 'EXPIRED') throw new Error(`Instagram işleme durumu ${g.status_code}`);
    await bekle(IG_YOKLAMA_BEKLE_MS);
  }
  if (!hazir) throw new Error('Instagram kapsayıcı zamanında hazır olmadı');
  await igPost(ag, 'media_publish', { creation_id: kapsayici }, token, 'yayın', env);
}
