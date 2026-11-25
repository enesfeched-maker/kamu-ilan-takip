// asistan_kayit tablosu için bellek içi sahte D1 (yalnız asistan-kayit.js'in SQL kalıpları).
import { SQL } from '../src/asistan-kayit.js';

const norm = (s) => s.replace(/\s+/g, ' ').trim();
const N = Object.fromEntries(Object.entries(SQL).map(([k, v]) => [norm(v), k]));

export function sahteKayitDB() {
  const d = { satirlar: [], sonId: 0, sorgular: [], hata: null, sayiDondur: null };
  return {
    d,
    prepare(sql) {
      const ad = N[norm(sql)];
      let p = [];
      const calistir = () => {
        if (!ad) throw new Error('Sahte D1 desteklemiyor: ' + sql);
        d.sorgular.push(ad);
        if (d.hata) throw new Error('D1 hatası');
        let changes = 0;
        let last = 0;
        let results = [];
        if (ad === 'ekle') {
          const [zaman, kanal, soru, tur, metin, ilan_sayisi, baglantilar, sayfa, meta] = p;
          d.satirlar.push({ id: ++d.sonId, zaman, kanal, soru, tur, metin, ilan_sayisi, baglantilar, sayfa, geri: null, durum: null, gonderilen: null, meta });
          changes = 1; last = d.sonId;
        } else if (ad === 'say') {
          results = [{ n: d.sayiDondur ?? d.satirlar.filter((r) => r.zaman >= p[0]).length }];
        } else if (ad === 'geri') {
          const r = d.satirlar.find((x) => x.id === p[1] && x.kanal === 'site' && x.zaman >= p[2]);
          if (r) { r.geri = p[0]; changes = 1; }
        } else if (ad === 'durum') {
          const r = d.satirlar.find((x) => x.id === p[2]);
          if (r) { r.durum = p[0]; r.gonderilen = p[1]; changes = 1; }
        } else if (ad === 'liste') {
          results = d.satirlar.filter((r) => r.id > p[0]).sort((a, b) => a.id - b.id).slice(0, p[1]).map((r) => ({ ...r }));
        } else if (ad === 'sil') {
          const once = d.satirlar.length;
          d.satirlar = d.satirlar.filter((r) => r.zaman >= p[0]);
          changes = once - d.satirlar.length;
        }
        return { results, meta: { changes, last_row_id: last } };
      };
      const o = {
        bind(...a) { p = a; return o; },
        async first() { return calistir().results[0] ?? null; },
        async all() { return calistir(); },
        async run() { return { success: true, ...calistir() }; },
      };
      return o;
    },
  };
}
