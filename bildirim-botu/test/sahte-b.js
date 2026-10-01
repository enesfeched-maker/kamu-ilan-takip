// Sahte D1 (bellek içi, yalnız komutlar/db.js'in kullandığı SQL kalıpları) ve sahte Telegram fetch'i.
const norm = (s) => s.replace(/\s+/g, ' ').trim();

export function sahteDB() {
  const tablolar = { kullanicilar: new Map(), gonderilen: [], kuyruk: [] };
  const durum = { sorgu: 0, degisen: 0, onceUpdate: null };

  function calistir(sql, p) {
    const s = norm(sql);
    let m;
    durum.sorgu++;
    durum.degisen = 0;
    if ((m = s.match(/^SELECT \* FROM kullanicilar WHERE chat_id = \?$/))) {
      const r = tablolar.kullanicilar.get(p[0]);
      return { results: r ? [{ ...r }] : [] };
    }
    if (/^SELECT \* FROM kullanicilar WHERE aktif = 1 AND onay = 1$/.test(s)) {
      return { results: [...tablolar.kullanicilar.values()].filter((r) => r.aktif === 1 && r.onay === 1).map((r) => ({ ...r })) };
    }
    if ((m = s.match(/^INSERT INTO kullanicilar \((.+?)\) VALUES \(.+?\) ON CONFLICT\(chat_id\) DO UPDATE SET/))) {
      const sutunlar = m[1].split(',').map((x) => x.trim());
      const yeni = Object.fromEntries(sutunlar.map((c, i) => [c, p[i]]));
      const eski = tablolar.kullanicilar.get(yeni.chat_id);
      tablolar.kullanicilar.set(yeni.chat_id, eski ? { ...eski, ...yeni, olusturma: eski.olusturma } : yeni);
      return { results: [] };
    }
    if (/^DELETE FROM kullanicilar WHERE chat_id = \?$/.test(s)) {
      tablolar.kullanicilar.delete(p[0]);
      return { results: [] };
    }
    if ((m = s.match(/^UPDATE kullanicilar SET (.+) WHERE chat_id = \? AND guncelleme = \?$/))) {
      if (durum.onceUpdate) { const f = durum.onceUpdate; durum.onceUpdate = null; f(tablolar); }
      const sutunlar = [...m[1].matchAll(/(\w+) = \?/g)].map((x) => x[1]);
      const r = tablolar.kullanicilar.get(p[sutunlar.length]);
      if (r && r.guncelleme === p[sutunlar.length + 1]) {
        sutunlar.forEach((c, i) => { r[c] = p[i]; });
        durum.degisen = 1;
      }
      return { results: [] };
    }
    if (/^DELETE FROM kuyruk WHERE chat_id = \?$/.test(s)) {
      tablolar.kuyruk = tablolar.kuyruk.filter((r) => r.chat_id !== p[0]);
      return { results: [] };
    }
    if (/^DELETE FROM gonderilen WHERE chat_id = \?$/.test(s)) {
      tablolar.gonderilen = tablolar.gonderilen.filter((r) => r.chat_id !== p[0]);
      return { results: [] };
    }
    throw new Error('Sahte D1 desteklemiyor: ' + s);
  }

  return {
    tablolar,
    durum,
    async batch(ifadeler) {
      durum.batch = (durum.batch || 0) + 1;
      const out = [];
      for (const i of ifadeler) out.push(await i.run());
      return out;
    },
    prepare(sql) {
      let p = [];
      const o = {
        bind(...a) { p = a; return o; },
        async first() { return calistir(sql, p).results[0] ?? null; },
        async all() { return calistir(sql, p); },
        async run() { calistir(sql, p); return { success: true, meta: { changes: durum.degisen } }; },
      };
      return o;
    },
  };
}

// globalThis.fetch'i değiştirir. Dönen nesne: cagrilar [{method, params}], hata(method, kod, aciklama), geri().
export function sahteTelegram() {
  const orijinal = globalThis.fetch;
  const cagrilar = [];
  const hatalar = new Map();
  globalThis.fetch = async (url, init) => {
    const m = String(url).match(/^https:\/\/api\.telegram\.org\/bot[^/]*\/(\w+)$/);
    if (!m) throw new Error('Beklenmeyen fetch: ' + url);
    const params = JSON.parse(init.body);
    cagrilar.push({ method: m[1], params });
    const h = hatalar.get(m[1]);
    if (h) {
      return new Response(JSON.stringify({ ok: false, error_code: h.kod, description: h.aciklama, parameters: h.parameters }), { status: h.kod });
    }
    return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
  };
  return {
    cagrilar,
    hata(method, kod, aciklama, parameters) { hatalar.set(method, { kod, aciklama, parameters }); },
    temizle() { cagrilar.length = 0; },
    son(method) { return [...cagrilar].reverse().find((c) => c.method === method); },
    geri() { globalThis.fetch = orijinal; },
  };
}

export const ENV = (ek = {}) => ({
  DB: sahteDB(),
  BOT_TOKEN: 'TEST_TOKEN',
  WEBHOOK_SECRET: 'gizli',
  SITE_URL: 'https://ornek.test/',
  VIP_ACIK: '0',
  ...ek,
});

export const mesaj = (chat_id, text, tip = 'private') => ({ update_id: 1, message: { message_id: 10, chat: { id: chat_id, type: tip }, text } });
export const cb = (chat_id, data, message_id = 11, tip = 'private') => ({
  update_id: 2,
  callback_query: { id: 'cq1', data, message: { message_id, chat: { id: chat_id, type: tip } } },
});
