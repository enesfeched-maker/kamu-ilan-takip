import {test} from 'node:test';
import assert from 'node:assert/strict';
import {yeniSurumler, yayinlanmis, kanalMetni, guvenliDosya} from '../src/akis.js';
const surum = (tag, tarih) => ({tag_name: tag, published_at: tarih});
test('kurulum öncesi içerik ve gönderimi belirsiz içerik tekrar gitmez', () => {
  const durum = {baslangic:'2026-11-13T15:00:00Z',gonderimler:{'sosyal-20261113-aksam':{durum:'belirsiz'}}};
  const secim = yeniSurumler([
    surum('sosyal-20261113-sabah','2026-11-13T09:00:00Z'),
    surum('sosyal-20261113-aksam','2026-11-13T18:00:00Z'),
    surum('sosyal-20261113-ilan-1830','2026-11-13T15:30:00Z'),
    surum('test-release','2026-11-13T16:00:00Z')], durum);
  assert.deepEqual(secim.map(s => s.tag_name), ['sosyal-20261113-ilan-1830']);
});
test('yalnız tam zaman eşleşmesi olan yayımlanmış içerik gider', () => {
  assert.equal(yayinlanmis({zaman:'x'}, [{zaman:'x'}]), false);
  assert.equal(yayinlanmis({zaman:'x'}, [{zaman:'y',ig_id:'1'}]), false);
  assert.equal(yayinlanmis({zaman:'x'}, [{zaman:'x',fb_id:'1'}]), true);
});
test('WhatsApp metninde başvuru adresi görünür', () => {
  assert.match(kanalMetni({aciklama:'Ayrıntılar profildeki bağlantıda.'}), /https:\/\/kpsstercihi.com\//);
  assert.throws(() => kanalMetni({aciklama:''}));
});
test('dosyalar yalnız kendi depomuzun yayınlarından alınır', () => {
  assert.equal(guvenliDosya('https://github.com/enesfeched-maker/kamu-ilan-takip/releases/download/x/01.png'),
    'https://github.com/enesfeched-maker/kamu-ilan-takip/releases/download/x/01.png');
  assert.throws(() => guvenliDosya('https://example.com/a.png'));
  assert.throws(() => guvenliDosya('https://github.com/another/repo/releases/download/x/a.png'));
});

test('video açıklaması kısa başlık ve tek bağlantıdan oluşur', () => {
  const yazi = kanalMetni({baslik:'Hazine ve Maliye Bakanlığı 10 kişi alacak #shorts', aciklama:'Uzun metin '.repeat(200)});
  assert.equal(yazi, 'Hazine ve Maliye Bakanlığı 10 kişi alacak\nhttps://kpsstercihi.com/');
  assert.ok(kanalMetni({baslik:'a'.repeat(1000)}).length < 210);
});
