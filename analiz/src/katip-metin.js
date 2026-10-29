// Liderlik tablosu için sitenin kendi dosyaları: resmî kriter puanlaması ve 2025 resmî sınav metinleri.
// Metin dosyası tarayıcıda KatipKutuphane.yukle(...) çağırır; burada aynı adla küçük bir yakalayıcı kurulur.
import './katip-yakala.js';
import * as puanlama from '../../docs/katiplik/puanla.js';
import '../../docs/katiplik/metin/zk2025.js';

export const RESMI_METINLER = globalThis.__katipMetin.zk2025;
// CommonJS olarak yüklenirse module.exports'tan, betik/ESM olarak yüklenirse globalThis.KatipPuan'dan gelir.
export const puanla = (puanlama.default && puanlama.default.puanla ? puanlama.default : globalThis.KatipPuan).puanla;

// Sitedeki katiplik.js ile aynı: seçilen metinden başlayıp süreye yetecek kadar metni art arda ekler.
export function zincir(liste, bas, saniye) {
  const gerek = Math.ceil(saniye / 60 * 70) + 60;
  let k = [], i = bas;
  while (k.length < gerek) { k = k.concat(liste[i % liste.length][1].split(' ')); i++; }
  return k.join(' ');
}
