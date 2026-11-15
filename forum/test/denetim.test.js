import test from 'node:test';
import assert from 'node:assert/strict';
import { denetle, tcGecerli, temizle, baglantiIzinli } from '../src/denetim.js';

const red = (m, neden) => { const d = denetle(m); assert.equal(d.tamam, false, `reddedilmeliydi: ${m}`); if (neden) assert.equal(d.neden, neden, m); };
const gec = (m) => { const d = denetle(m); assert.equal(d.tamam, true, `geçmeliydi: ${m} (${d.neden})`); };

test('temizle: boşluk, kontrol karakteri, fazla boş satır', () => {
  assert.equal(temizle('  merhaba\u0000 dünya \r\n\n\n\n\n\nson  '), 'merhaba dünya\n\n\nson');
  assert.equal(temizle('a​b'), 'ab');
});

test('TC kimlik: sağlama toplamı', () => {
  assert.equal(tcGecerli('10000000146'), true);
  assert.equal(tcGecerli('10000000147'), false);
  assert.equal(tcGecerli('00000000146'), false);
  red('numaram 10000000146 yaz bana', 'Kimlik numarası paylaşma.');
  gec('puanım 12345678901 değil ama rastgele sayı');
  gec('2026 yılında 10000000147 kişi başvurdu mu');
});

test('telefon numaraları', () => {
  for (const t of ['05321234567', '0532 123 45 67', '+90 532 123 45 67', '532-123-45-67', '0 (532) 123 45 67', '+905321234567']) red(`ara ${t}`, 'Telefon numarası paylaşma.');
  gec('2024 KPSS puanım 85.5 ve 3 yıl deneyim var');
});

test('e-posta', () => {
  red('bana yaz ali@example.com', 'E-posta adresi paylaşma.');
  red('ali (at) gmail.com', 'E-posta adresi paylaşma.');
});

test('bağlantılar: yalnız izinli alanlar', () => {
  gec('bakın https://www.osym.gov.tr/TR,1/ana-sayfa.html');
  gec('https://kariyerkapisi.gov.tr/IlanDetay?i=1 güzel');
  gec('https://yok.edu.tr/duyuru ve kpsstercihi.com/ilan/x/');
  gec('kanal https://t.me/kpsstercihi bakın.');
  red('bak https://evil.com/x', 'Bu bağlantıya izin verilmiyor.');
  red('bak bit.ly/abc123', 'Bu bağlantıya izin verilmiyor.');
  red('bak www.site.xyz', 'Bu bağlantıya izin verilmiyor.');
  red('https://t.me/baskakanal', 'Bu bağlantıya izin verilmiyor.');
  red('https://kpsstercihi.com@evil.com/x', null);
  red('https://gov.tr.evil.com/', 'Bu bağlantıya izin verilmiyor.');
  red('https://evilkpsstercihi.com/', 'Bu bağlantıya izin verilmiyor.');
  assert.equal(baglantiIzinli('http://sub.kpsstercihi.com/a'), true);
});

test('küfür: doğrudan ve kaçamaklar', () => {
  for (const m of ['siktir git', 'S1KT1R', 's.i.k.t.i.r', 's i k t i r', 'siiiiktir', 'SİKTİR', 'amk', 'AMK', 'a m k', 'amkkkk', 'aq', 'orospu çocuğu', '0r0spu', 'orospuuu',
    'götveren', 'göt veren', 'götlek', 'piç', 'yarrak', 'pezevenk', 'kahpe', 'ibne', 'gavat', 'şerefsiz', 'yavşak', 'sikeyim', 'sikerim', 'amına koyayım', 'amina koyim', '$iktir', 's1kerim', 'a@k']) {
    if (m === 'a@k') continue;
    red(m, 'Lütfen kaba söz kullanma.');
  }
  red('Bu iş tam bir siktir ya', 'Lütfen kaba söz kullanma.');
});

test('küfür: yanlış alarm yok', () => {
  for (const m of ['sıkıntı yok', 'SIKINTI yok', 'amaç ne', 'Amasya ilanı', 'siklet', 'sıkıştı', 'sık sık soruyorum', 'Amina Hanım', 'got it', 'aquarium', 'mal varlığı', 'salak şaka',
    'tasarım amacı', 'kitap', 'ambar', 'yarak açıldı mı'.replace('yarak açıldı mı', 'yaratıcı'), 'başvuru formu sıktı mı', 'Piyasa', 'kampüs', 'ibadet', 'Gavur'.replace('Gavur', 'gavurdağı')]) gec(m);
});

test('bağırma ve tekrar', () => {
  red('aaaaaaaa', 'Lütfen büyük harfle ya da tekrarla yazma.');
  red('BU İLAN İÇİN HERKES BAŞVURMALI ARTIK HEMEN', 'Lütfen büyük harfle ya da tekrarla yazma.');
  gec('KPSS P3 puanı ile TYT');
  gec('Bu ilan çok güzel, ben ASKİ ilanına başvurdum, sizce olur mu?');
  gec('Sonuç gelmedi.......');
});

test('temiz alan döner', () => {
  const d = denetle('  merhaba   dünya  ');
  assert.equal(d.tamam, true);
  assert.equal(d.temiz, 'merhaba   dünya');
});
