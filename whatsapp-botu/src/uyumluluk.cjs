// whatsapp-web.js #201823 / #201824: WhatsApp medya modeli avParams() metodunu kaldırdı.
// Yalnız kilitli sürümdeki bilinen ifadeye uygulanır; başka dosya/kod değiştirilmez.
const fs = require('node:fs');
const dosya = require.resolve('whatsapp-web.js/src/util/Injected/Utils.js');
const eski = 'mediaMetadata: msg.avParams(),';
const yeni = "mediaMetadata: typeof msg.avParams === 'function' ? msg.avParams() : window.require('WAWebMediaMetadata').mediaMetadata(msg),";
const kod = fs.readFileSync(dosya, 'utf8');
if (kod.includes(yeni)) process.exit(0);
if (kod.split(eski).length !== 2) throw new Error('WhatsApp uyumluluk düzeltmesinin hedefi değişmiş');
fs.writeFileSync(dosya, kod.replace(eski, yeni));
