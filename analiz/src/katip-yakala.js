// docs/katiplik/metin/*.js dosyalarının çağırdığı KatipKutuphane.yukle'yi yakalar (katip-metin.js'ten önce yüklenir).
const depo = (globalThis.__katipMetin = globalThis.__katipMetin || {});
if (!globalThis.KatipKutuphane) globalThis.KatipKutuphane = { yukle(ad, liste) { depo[ad] = liste; } };
