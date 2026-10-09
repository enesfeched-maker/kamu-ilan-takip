// Komutlar ve callback işleyicileri. Kullanıcıya görünen tüm metinler Türkçe.
import { tg } from './telegram.js';
import { kullaniciGetir, kullaniciKaydet, kullaniciGuncelle, kullaniciSil } from './db.js';
import {
  ILLER, DUZEYLER, KATEGORILER, SAYFA_BOYU,
  onayKlavye, duzeyKlavye, ilKlavye, kategoriKlavye, kelimeAtlaKlavye, ayarKlavye, silOnayKlavye,
} from './klavye.js';

const ONAY_METNI =
  'Merhaba! Ben KPSS Tercihi bildirim botuyum. Öğrenim düzeyine, iline ve ilgi alanına göre uygun yeni ilanları sana özelden gönderir, son başvuru gününden önce hatırlatırım.\n\n' +
  'Tercihlerini istediğin an /sil ile tamamen silebilirsin.';

const YARDIM_METNI =
  'Komutlar:\n' +
  '/start - Başlangıç ve kurulum\n' +
  '/ayarlar - Tercihlerini gör ve düzenle\n' +
  '/kelime - Anahtar kelime filtresi\n' +
  '/durdur - Bildirimleri durdur\n' +
  '/devam - Bildirimleri sürdür\n' +
  '/sil - Tüm verilerimi sil\n' +
  '/vip - VIP bilgisi';

const ONCE_START = 'Önce /start yazıp onay vermelisin.';
const KELIME_SORUSU =
  'Anahtar kelimeleri virgülle yaz (ör. hukuk, bilgisayar). Silmek için \'yok\' yaz.';

export const varsayilanBagimliliklar = {
  async acikIlanOzeti(env, kullanici) {
    const m = await import('./bildirim.js');
    return m.acikIlanOzeti(env, kullanici);
  },
};

export const kacis = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const ad = (liste, kod) => (liste.find(([k]) => k === kod) || [kod, kod])[1];

export function tercihOzeti(k) {
  const duzey = k.duzeyler.length ? k.duzeyler.map((x) => ad(DUZEYLER, x)).join(', ') : 'Hepsi';
  const il = k.iller.length ? k.iller.join(', ') : 'Tüm Türkiye';
  const kat = k.kategoriler.length ? k.kategoriler.map((x) => ad(KATEGORILER, x)).join(', ') : 'Hepsi';
  const kel = k.kelimeler.length ? k.kelimeler.join(', ') : 'Yok';
  return (
    '<b>Tercihlerin</b>\n' +
    `Öğrenim düzeyi: ${kacis(duzey)}\n` +
    `İl: ${kacis(il)}\n` +
    `Kategori: ${kacis(kat)}\n` +
    `Anahtar kelime: ${kacis(kel)}\n` +
    `Bildirimler: ${k.aktif ? 'Açık' : 'Durduruldu'}\n` +
    `Son gün hatırlatması: ${k.hatirlatma ? 'Açık' : 'Kapalı'}`
  );
}

export function kelimeAyikla(metin) {
  const t = String(metin || '').trim().toLocaleLowerCase('tr');
  if (t === 'yok') return [];
  const out = [];
  for (const p of t.split(',')) {
    const w = p.trim().slice(0, 40);
    if (w && !out.includes(w)) out.push(w);
  }
  return out.slice(0, 10);
}

// Siteden gelen derin bağlantı: t.me/<bot>?start=k_<base64url(UTF-8 kelime)>. Geçersizse ''.
export function derinKelime(kod) {
  if (!/^[A-Za-z0-9_-]{2,62}$/.test(kod || '')) return '';
  try {
    const ikili = atob(kod.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (kod.length % 4)) % 4));
    const metin = new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.from(ikili, (c) => c.charCodeAt(0)));
    const w = metin.replace(/[\u0000-\u001f,<>]/g, ' ').replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr').slice(0, 40);
    return w.length >= 2 ? w : '';
  } catch {
    return '';
  }
}

const kelimeEkle = (liste, w) => (liste.includes(w) ? liste : [...liste, w].slice(-10));

// Mesajı düzenle (message_id varsa), olmazsa yeni gönder.
async function goster(env, chat_id, message_id, metin, klavye) {
  const params = { text: metin, parse_mode: 'HTML' };
  if (klavye) params.reply_markup = klavye;
  if (message_id) {
    try {
      await tg(env, 'editMessageText', { chat_id, message_id, ...params });
      return;
    } catch (e) {
      if (e.kod === 400 && /not modified/i.test(e.aciklama || '')) return;
      // düzenlenemediyse yeni ileti olarak gönder
    }
  }
  await tg(env, 'sendMessage', { chat_id, ...params });
}

const yolla = (env, chat_id, metin, klavye) => goster(env, chat_id, null, metin, klavye);

function degistir(liste, kod) {
  return liste.includes(kod) ? liste.filter((x) => x !== kod) : [...liste, kod];
}

async function kelimeSor(env, k, message_id, kurulum) {
  await kullaniciGuncelle(env, k.chat_id, (u) => { u.durum = kurulum ? 'kelime_bekleniyor_kurulum' : 'kelime_bekleniyor'; });
  await goster(env, k.chat_id, kurulum ? message_id : null, KELIME_SORUSU, kurulum ? kelimeAtlaKlavye() : undefined);
}

async function kurulumBitir(env, k, message_id, bag) {
  await goster(env, k.chat_id, message_id, tercihOzeti(k) + '\n\nTercihlerini /ayarlar ile istediğin an değiştirebilirsin.');
  let ozet = '';
  try {
    ozet = await bag.acikIlanOzeti(env, k);
  } catch (e) {
    console.log('acikIlanOzeti hatası:', e && e.message);
  }
  if (ozet) await yolla(env, k.chat_id, ozet);
}

async function ayarlarGoster(env, k, message_id) {
  await goster(env, k.chat_id, message_id, tercihOzeti(k), ayarKlavye(k));
}

// ---- Mesajlar ----
export async function mesajIsle(env, mesaj, bag = varsayilanBagimliliklar) {
  const chat_id = mesaj.chat.id;
  const metin = (mesaj.text || '').trim();
  if (!metin) return;
  let k = await kullaniciGetir(env, chat_id);

  if (!metin.startsWith('/')) {
    if (k && k.onay && k.durum && k.durum.startsWith('kelime_bekleniyor')) {
      const kurulum = k.durum === 'kelime_bekleniyor_kurulum';
      const kelimeler = kelimeAyikla(metin);
      const g = await kullaniciGuncelle(env, chat_id, (u) => { u.kelimeler = kelimeler; u.durum = null; if (kurulum) u.aktif = 1; });
      if (!g) return;
      if (kurulum) return kurulumBitir(env, g, null, bag);
      return yolla(
        env, chat_id,
        kelimeler.length ? `Anahtar kelimeler kaydedildi: ${kacis(kelimeler.join(', '))}` : 'Anahtar kelime filtresi kaldırıldı.',
      );
    }
    return yolla(env, chat_id, 'Komutları görmek için /yardim yaz.');
  }

  const komut = metin.split(/\s+/)[0].slice(1).split('@')[0].toLowerCase();
  if (k && k.durum) k = await kullaniciGuncelle(env, chat_id, (u) => { u.durum = null; });
  const onayli = !!(k && k.onay);

  switch (komut) {
    case 'start': {
      const arg = metin.split(/\s+/)[1] || '';
      const kod = arg.startsWith('k_') ? arg.slice(2) : '';
      const kelime = derinKelime(kod);
      if (onayli) {
        if (kelime) {
          const g = await kullaniciGuncelle(env, chat_id, (u) => { u.kelimeler = kelimeEkle(u.kelimeler || [], kelime); });
          return yolla(
            env, chat_id,
            `“${kacis(kelime)}” takibe eklendi. Bu kelimeyi içeren yeni ilan çıkınca sana haber vereceğim.\n` +
            `Takip ettiğin kelimeler: ${kacis((g ? g.kelimeler : [kelime]).join(', '))}` +
            (g && !g.aktif ? '\n\nBildirimlerin şu an kapalı; açmak için /devam yaz.' : ''),
          );
        }
        return yolla(env, chat_id, 'Tekrar hoş geldin! Tercihlerini görmek için /ayarlar, komutlar için /yardim yaz.');
      }
      return yolla(
        env, chat_id,
        ONAY_METNI + (kelime ? `\n\nOnay verince “${kacis(kelime)}” kelimesini takibe alacağım.` : ''),
        onayKlavye(kelime ? kod : ''),
      );
    }
    case 'yardim':
    case 'help':
      return yolla(env, chat_id, YARDIM_METNI);
    case 'vip':
      return yolla(
        env, chat_id,
        env.VIP_ACIK !== '1' ? 'VIP özelliği yakında!' : 'VIP bilgisi için ' + (env.SITE_URL || '') + ' adresine bakabilirsin.',
      );
    case 'sil':
      if (!k) return yolla(env, chat_id, 'Kayıtlı verin yok.');
      return yolla(env, chat_id, 'Tüm tercihlerin ve gönderim geçmişin kalıcı olarak silinecek. Emin misin?', silOnayKlavye());
    case 'ayarlar':
      if (!onayli) return yolla(env, chat_id, ONCE_START);
      return ayarlarGoster(env, k, null);
    case 'kelime':
      if (!onayli) return yolla(env, chat_id, ONCE_START);
      return kelimeSor(env, k, null, false);
    case 'durdur':
      if (!onayli) return yolla(env, chat_id, ONCE_START);
      await kullaniciGuncelle(env, chat_id, (u) => { u.aktif = 0; });
      return yolla(env, chat_id, 'Bildirimler durduruldu. Yeniden başlatmak için /devam yaz.');
    case 'devam':
      if (!onayli) return yolla(env, chat_id, ONCE_START);
      await kullaniciGuncelle(env, chat_id, (u) => { u.aktif = 1; });
      return yolla(env, chat_id, 'Bildirimler yeniden açıldı. Tercihlerini /ayarlar ile değiştirebilirsin.');
    default:
      return yolla(env, chat_id, 'Bu komutu tanımıyorum. Komutlar için /yardim yaz.');
  }
}

// ---- Callback'ler ----
export async function callbackIsle(env, cq, bag = varsayilanBagimliliklar) {
  const chat_id = cq.message && cq.message.chat && cq.message.chat.id;
  const message_id = cq.message && cq.message.message_id;
  const veri = cq.data || '';
  const cevapla = async (text) => {
    try {
      await tg(env, 'answerCallbackQuery', text ? { callback_query_id: cq.id, text } : { callback_query_id: cq.id });
    } catch (e) {
      console.log('answerCallbackQuery hatası:', e && e.kod);
    }
  };
  if (!chat_id) return cevapla();

  let k = await kullaniciGetir(env, chat_id);

  if (veri === 'onay' || veri.startsWith('onay:')) {
    await cevapla();
    if (k && k.onay) {
      // Eski düğme: durumu (ör. /durdur) değiştirme, yalnız bilgi ver.
      return goster(env, chat_id, message_id, 'Onayın zaten kayıtlı. Tercihlerini /ayarlar ile değiştirebilirsin.');
    }
    const yeni = k || { chat_id, duzeyler: [], iller: [], kategoriler: [], kelimeler: [] };
    const kelime = derinKelime(veri.slice(5));
    if (kelime) yeni.kelimeler = kelimeEkle(yeni.kelimeler || [], kelime);
    yeni.onay = 1;
    yeni.aktif = 0; // kurulum bitene kadar bildirim yok
    yeni.durum = null;
    await kullaniciKaydet(env, yeni);
    return goster(env, chat_id, message_id, 'Teşekkürler! Hangi öğrenim düzeylerindeki ilanları görmek istersin? (Birden fazla seçebilirsin; hiçbiri seçili değilse hepsi gelir.)', duzeyKlavye(yeni.duzeyler, 'w'));
  }

  if (veri.startsWith('sil:')) {
    await cevapla();
    if (veri === 'sil:evet') {
      await kullaniciSil(env, chat_id);
      return goster(env, chat_id, message_id, 'Tüm verilerin silindi. Yeniden başlamak için /start yaz.');
    }
    return goster(env, chat_id, message_id, 'Vazgeçildi, verilerin duruyor.');
  }

  if (!k || !k.onay) {
    await cevapla();
    return yolla(env, chat_id, ONCE_START);
  }

  const [alan, mod, deger] = veri.split(':');
  const kurulum = mod === 'w';

  if (alan === 'ay') {
    await cevapla();
    if (mod === 'duzey') return goster(env, chat_id, message_id, 'Öğrenim düzeyi seç:', duzeyKlavye(k.duzeyler, 'e'));
    if (mod === 'il') return goster(env, chat_id, message_id, 'İl seç:', ilKlavye(k.iller, 0, 'e'));
    if (mod === 'kategori') return goster(env, chat_id, message_id, 'Kategori seç:', kategoriKlavye(k.kategoriler, 'e'));
    if (mod === 'kelime') return kelimeSor(env, k, message_id, false);
    if (mod === 'hat') {
      k = await kullaniciGuncelle(env, chat_id, (u) => { u.hatirlatma = u.hatirlatma ? 0 : 1; });
      if (!k) return;
      return ayarlarGoster(env, k, message_id);
    }
    return;
  }

  if (alan === 'kw' && mod === 'atla') {
    await cevapla();
    k = await kullaniciGuncelle(env, chat_id, (u) => { u.durum = null; u.aktif = 1; });
    if (!k) return;
    return kurulumBitir(env, k, message_id, bag);
  }

  if (alan === 'd') {
    await cevapla();
    if (deger === 'ok') {
      if (kurulum) return goster(env, chat_id, message_id, 'Hangi illerdeki ilanları görmek istersin? (Hiçbiri seçili değilse veya "Tüm Türkiye" seçiliyse hepsi gelir.)', ilKlavye(k.iller, 0, 'w'));
      return ayarlarGoster(env, k, message_id);
    }
    if (!DUZEYLER.some(([kod]) => kod === deger)) return;
    k = await kullaniciGuncelle(env, chat_id, (u) => { u.duzeyler = degistir(u.duzeyler, deger); });
    if (!k) return;
    return goster(env, chat_id, message_id, kurulum ? 'Hangi öğrenim düzeylerindeki ilanları görmek istersin?' : 'Öğrenim düzeyi seç:', duzeyKlavye(k.duzeyler, mod));
  }

  if (alan === 'i') {
    await cevapla();
    const baslik = kurulum ? 'Hangi illerdeki ilanları görmek istersin?' : 'İl seç:';
    if (deger === 'ok') {
      if (kurulum) return goster(env, chat_id, message_id, 'Hangi kategorilerdeki ilanları görmek istersin?', kategoriKlavye(k.kategoriler, 'w'));
      return ayarlarGoster(env, k, message_id);
    }
    if (deger === 'tum') {
      k = await kullaniciGuncelle(env, chat_id, (u) => { u.iller = []; });
      if (!k) return;
      return goster(env, chat_id, message_id, baslik, ilKlavye(k.iller, 0, mod));
    }
    if (/^p\d+$/.test(deger)) return goster(env, chat_id, message_id, baslik, ilKlavye(k.iller, Number(deger.slice(1)), mod));
    if (/^t\d+$/.test(deger)) {
      const idx = Number(deger.slice(1));
      if (idx >= ILLER.length) return;
      k = await kullaniciGuncelle(env, chat_id, (u) => { u.iller = degistir(u.iller, ILLER[idx]); });
      if (!k) return;
      return goster(env, chat_id, message_id, baslik, ilKlavye(k.iller, Math.floor(idx / SAYFA_BOYU), mod));
    }
    return;
  }

  if (alan === 'k') {
    await cevapla();
    if (deger === 'ok') {
      if (kurulum) return kelimeSor(env, k, message_id, true);
      return ayarlarGoster(env, k, message_id);
    }
    let degisim;
    if (KATEGORILER.some(([kod]) => kod === deger)) degisim = (u) => { u.kategoriler = degistir(u.kategoriler, deger); };
    else return;
    k = await kullaniciGuncelle(env, chat_id, degisim);
    if (!k) return;
    return goster(env, chat_id, message_id, kurulum ? 'Hangi kategorilerdeki ilanları görmek istersin?' : 'Kategori seç:', kategoriKlavye(k.kategoriler, mod));
  }

  return cevapla();
}

// Tek giriş: update işle (yalnız özel sohbetler).
export async function updateIsle(env, update, bag = varsayilanBagimliliklar) {
  if (update.message) {
    if (!update.message.chat || update.message.chat.type !== 'private') return;
    return mesajIsle(env, update.message, bag);
  }
  if (update.callback_query) {
    const m = update.callback_query.message;
    if (!m || !m.chat || m.chat.type !== 'private') return;
    return callbackIsle(env, update.callback_query, bag);
  }
}
