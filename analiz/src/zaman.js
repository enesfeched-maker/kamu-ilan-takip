// Türkiye saati (UTC+3, yıl boyu) yardımcıları. Sabit +3 saat kullanılır; yaz saati uygulaması yoktur.
const TR_SANIYE = 3 * 3600;

export function trParcalari(tsSaniye) {
  const d = new Date((tsSaniye + TR_SANIYE) * 1000);
  return {
    gun: d.toISOString().slice(0, 10),
    saat: d.getUTCHours(),
    hg: (d.getUTCDay() + 6) % 7, // 0 = Pazartesi
  };
}

export function gunEkle(gun, adet) {
  const d = new Date(Date.parse(gun + 'T00:00:00Z') + adet * 86400000);
  return d.toISOString().slice(0, 10);
}

// Bir Türkiye gününün 00:00'ının unix saniyesi (olaylar.ts aralığı sorguları için).
export function gunBasSn(gun) { return Date.parse(gun + 'T00:00:00Z') / 1000 - TR_SANIYE; }

export function bugun(simdiMs = Date.now()) {
  return trParcalari(Math.floor(simdiMs / 1000)).gun;
}

// "bugun" | "7g" | "30g" | "90g" -> { bas, bit, adet }
export function aralikCoz(aralik, simdiMs = Date.now()) {
  const bit = bugun(simdiMs);
  const adet = aralik === '7g' ? 7 : aralik === '30g' ? 30 : aralik === '90g' ? 90 : 1;
  return { bas: gunEkle(bit, -(adet - 1)), bit, adet, ad: adet === 1 ? 'bugun' : adet + 'g' };
}

export function gunListesi(bas, bit) {
  const out = [];
  for (let g = bas; g <= bit; g = gunEkle(g, 1)) out.push(g);
  return out;
}
