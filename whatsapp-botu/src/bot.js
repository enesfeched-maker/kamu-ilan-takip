import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import wweb from 'whatsapp-web.js';
import QRCode from 'qrcode';
import { REPO, KANAL_ID, KANAL_KODU, yeniSurumler, yayinlanmis, kanalMetni, guvenliDosya } from './akis.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const VERI = path.join(ROOT, 'veri');
fs.mkdirSync(VERI, {recursive: true});
const DOSYA = path.join(VERI, 'durum.json');
const LOCK = path.join(VERI, 'bot.lock');
try {
  fs.writeFileSync(LOCK, String(process.pid), {flag: 'wx'});
} catch {
  const pid = Number(fs.readFileSync(LOCK, 'utf8'));
  try { process.kill(pid, 0); throw new Error('WhatsApp botu zaten çalışıyor'); }
  catch (e) {
    if (e.code !== 'ESRCH') throw e;
    fs.writeFileSync(LOCK, String(process.pid));
  }
}
let durum;
try { durum = JSON.parse(fs.readFileSync(DOSYA, 'utf8')); }
catch (e) {
  if (e.code !== 'ENOENT') throw new Error('Gönderim geçmişi okunamadı; güvenli duruş');
  durum = {baslangic: new Date().toISOString(), gonderimler: {}};
}
if (!durum.gonderimler || !Number.isFinite(Date.parse(durum.baslangic))) throw new Error('Geçersiz gönderim geçmişi');
function kaydet() {
  fs.writeFileSync(DOSYA + '.tmp', JSON.stringify(durum, null, 2));
  fs.renameSync(DOSYA + '.tmp', DOSYA);
}
kaydet();
let qr = '', durumAdi = 'başlatılıyor', sonHata = '', hazir = false, mesgul = false, kanal;
function bilgi(metin) { fs.appendFileSync(path.join(VERI, 'gunluk.log'), new Date().toISOString() + ' ' + metin + '\n'); }

const server = http.createServer((req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Content-Security-Policy', "default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'");
  if (req.method !== 'GET') { res.writeHead(405); return res.end(); }
  if (req.url === '/durum') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.end(JSON.stringify({durum: durumAdi, qr, sonHata, kanal: kanal?.name || '',
      sonKontrol: durum.sonKontrol, gonderimler: Object.values(durum.gonderimler).filter(g => g.durum === 'gonderildi').length}));
  }
  if (req.url !== '/') { res.writeHead(404); return res.end(); }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(`<!doctype html><html lang="tr"><meta charset="utf-8"><title>KPSS Tercihi — WhatsApp botu</title>
<style>body{font:18px system-ui;background:#f4f7f5;max-width:650px;margin:60px auto;padding:24px;color:#183d30}section{background:white;padding:32px;border-radius:18px}img{width:300px;max-width:100%}p{line-height:1.6}</style>
<section><h1>WhatsApp kanal botu</h1><p id="durum">Başlatılıyor…</p><img id="qr" hidden alt="WhatsApp bağlantı QR kodu">
<p id="yonerge">Telefonda WhatsApp → Ayarlar → Bağlı cihazlar → Cihaz bağla yolunu açıp kodu okut.</p>
<p>Hedef: KPSS Tercihi kanalı. Oturum bu bilgisayarda saklanır. Bot, yeni sosyal paylaşımları kanalına aktarır.</p><p id="hata"></p></section>
<script>async function oku(){try{const d=await(await fetch('/durum')).json();document.getElementById('durum').textContent=d.durum+(d.kanal?' · '+d.kanal:'')+' · '+d.gonderimler+' paylaşım';const q=document.getElementById('qr');q.hidden=!d.qr;if(d.qr)q.src=d.qr;document.getElementById('yonerge').hidden=!d.qr;document.getElementById('hata').textContent=d.sonHata;}catch{document.getElementById('durum').textContent='Bot bağlantısı kesildi';}}oku();setInterval(oku,2000);</script></html>`);
});
server.listen(8789, '127.0.0.1');
server.on('error', () => { bilgi('Kurulum paneli açılamadı'); process.exit(1); });

async function jsonAl(url) {
  const r = await fetch(url, {headers: {'User-Agent': 'kpsstercihi-whatsapp-bot/1.0'}, signal: AbortSignal.timeout(30000)});
  if (!r.ok) throw new Error('Yayın kaynağı HTTP ' + r.status);
  return r.json();
}
async function tur(ilk = false) {
  if (!hazir || mesgul) return;
  mesgul = true;
  try {
    const [surumler, gecmis] = await Promise.all([
      jsonAl('https://api.github.com/repos/' + REPO + '/releases?per_page=20'),
      jsonAl('https://raw.githubusercontent.com/' + REPO + '/main/sosyal/gecmis.json')]);
    if (!Array.isArray(surumler) || !Array.isArray(gecmis)) throw new Error('Geçersiz yayın kaynağı');
    const secimDurumu = ilk ? {...durum, baslangic: new Date(Date.now() - 86400000).toISOString()} : durum;
    const adaylar = yeniSurumler(surumler, secimDurumu);
    for (const surum of (ilk ? adaylar.slice(-1) : adaylar.slice(0, 3))) {
      const dosya = surum.assets.find(a => a.name === 'paylasim.json');
      if (!dosya) continue;
      const metin = await jsonAl(guvenliDosya(dosya.browser_download_url));
      // Önizleme sürümleri paylaşılmaz; sosyal botun yayın geçmişiyle tam eşleşme gerekir.
      if (!yayinlanmis(metin, gecmis)) continue;
      const yazi = kanalMetni(metin);
      const kapak = surum.assets.find(a => a.name === '01.png');
      let medya;
      if (kapak) {
        const r = await fetch(guvenliDosya(kapak.browser_download_url), {signal: AbortSignal.timeout(30000)});
        if (!r.ok) throw new Error('Kapak indirilemedi');
        const veri = Buffer.from(await r.arrayBuffer());
        if (veri.length > 10 * 1024 * 1024) throw new Error('Kapak boyutu fazla');
        medya = new wweb.MessageMedia('image/png', veri.toString('base64'), 'kpss-tercihi.png');
      }
      // Gönderimden önce kaydet: bağlantı koparsa aynı içeriği körlemesine tekrar gönderme.
      durum.gonderimler[surum.tag_name] = {durum: 'belirsiz', zaman: new Date().toISOString(), onceki_deneme: durum.gonderimler[surum.tag_name]};
      kaydet();
      const sonuc = await kanal.sendMessage(medya || yazi, {...(medya ? {caption: yazi} : {}), sendSeen: false, parseVCards: false, waitUntilMsgSent: true});
      if (!sonuc?.id) throw new Error('WhatsApp gönderim sonucu doğrulanamadı');
      durum.gonderimler[surum.tag_name] = {durum: 'gonderildi', zaman: new Date().toISOString(), id: sonuc.id._serialized};
      kaydet();
      bilgi('Kanal paylaşımı tamamlandı: ' + surum.tag_name);
    }
    durum.sonKontrol = new Date().toISOString(); kaydet(); sonHata = '';
  } catch (e) {
    sonHata = 'Paylaşım kontrolünde sorun var. Günlük dosyasını kontrol edin.';
    bilgi('Kontrol hatası: ' + String(e.stack || e.message || e.name).slice(0, 1500)); // Oturum, QR ve özel mesajlar günlükte tutulmaz.
  } finally { mesgul = false; }
}

const client = new wweb.Client({
  authStrategy: new wweb.LocalAuth({clientId: 'kpsstercihi-kanal', dataPath: path.join(VERI, 'oturum')}),
  puppeteer: {headless: true, executablePath: process.env.WHATSAPP_TARAYICI ||
    path.join(process.env.LOCALAPPDATA, 'BraveSoftware/Brave-Browser/Application/brave.exe')},
  webVersionCache: {type: 'local', path: path.join(VERI, 'web-onbellek')}
});
client.on('qr', async kod => { qr = await QRCode.toDataURL(kod); durumAdi = 'QR okutulması bekleniyor'; });
client.on('authenticated', () => { qr = ''; durumAdi = 'Oturum açıldı, kanal yükleniyor'; });
client.on('auth_failure', () => { hazir = false; durumAdi = 'Oturum doğrulanamadı'; });
client.on('disconnected', () => { hazir = false; durumAdi = 'Bağlantı kesildi'; process.exitCode = 1; setTimeout(() => process.exit(1), 2000); });
client.on('ready', async () => {
  try {
    const kanallar = await client.getChannels();
    kanal = kanallar.find(k => k.id?._serialized === KANAL_ID);
    if (!kanal) kanal = await client.getChannelByInviteCode(KANAL_KODU);
    if (kanal?.id?._serialized !== KANAL_ID || kanal.name !== 'KPSS Tercihi') throw new Error('Hedef kanal eşleşmedi');
    hazir = true; qr = ''; durumAdi = 'Bağlı · otomatik paylaşım açık'; bilgi('KPSS Tercihi kanalı bağlandı');
    await tur(process.argv.includes('--ilk-paylasim'));
  } catch (e) { bilgi('Kanal doğrulama: ' + String(e.message).slice(0, 250)); durumAdi = 'Kanal doğrulanamadı'; sonHata = 'Kanal bağlantısı kontrol ediliyor.'; }
});
const interval = setInterval(() => tur(), 5 * 60 * 1000);
async function kapat() {
  clearInterval(interval); hazir = false;
  await client.destroy().catch(() => {}); server.close();
  try { fs.unlinkSync(LOCK); } catch {}
  process.exit();
}
process.on('SIGINT', kapat); process.on('SIGTERM', kapat);
// Görev Zamanlayıcı wscript'i durdurunca alt Node süreci de oturumunu kapatsın.
if (process.argv.includes('--gorev')) {
  setInterval(() => {
    try { process.kill(process.ppid, 0); }
    catch (e) { if (e.code === 'ESRCH') kapat(); }
  }, 15000).unref();
}
process.on('exit', () => { try { if (fs.readFileSync(LOCK, 'utf8') === String(process.pid)) fs.unlinkSync(LOCK); } catch {} });
client.initialize().catch(() => { bilgi('WhatsApp başlatılamadı'); process.exit(1); });
