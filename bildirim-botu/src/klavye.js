// Satır içi klavye üreticileri. callback_data biçimi: "<alan>:<mod>:<değer>" (en çok 64 bayt).
// mod: 'w' = kurulum sihirbazı, 'e' = /ayarlar içinden düzenleme.

// bot/siniflandir.py ILLER listesinin kopyası (81 il)
export const ILLER = (
  'Adana Adıyaman Afyonkarahisar Ağrı Aksaray Amasya Ankara Antalya Ardahan Artvin Aydın Balıkesir ' +
  'Bartın Batman Bayburt Bilecik Bingöl Bitlis Bolu Burdur Bursa Çanakkale Çankırı Çorum Denizli ' +
  'Diyarbakır Düzce Edirne Elazığ Erzincan Erzurum Eskişehir Gaziantep Giresun Gümüşhane Hakkari ' +
  'Hatay Iğdır Isparta İstanbul İzmir Kahramanmaraş Karabük Karaman Kars Kastamonu Kayseri Kırıkkale ' +
  'Kırklareli Kırşehir Kilis Kocaeli Konya Kütahya Malatya Manisa Mardin Mersin Muğla Muş Nevşehir ' +
  'Niğde Ordu Osmaniye Rize Sakarya Samsun Siirt Sinop Sivas Şanlıurfa Şırnak Tekirdağ Tokat ' +
  'Trabzon Tunceli Uşak Van Yalova Yozgat Zonguldak'
).split(' ');

export const DUZEYLER = [
  ['lisans', 'Lisans'],
  ['onlisans', 'Ön lisans'],
  ['ortaogretim', 'Ortaöğretim'],
];

export const KATEGORILER = [
  ['belediye', 'Belediye'],
  ['saglik', 'Sağlık'],
  ['bilisim', 'Bilişim'],
  ['isci', 'İşçi'],
];

export const SAYFA_BOYU = 24;
export const SAYFA_SAYISI = Math.ceil(ILLER.length / SAYFA_BOYU);

const d = (text, callback_data) => ({ text, callback_data });
const isaret = (secili, ad) => (secili ? '✓ ' : '') + ad;

// kod: siteden gelen anahtar kelimenin base64url hâli; onaydan sonra kelime filtresine eklenir.
export function onayKlavye(kod = '') {
  return { inline_keyboard: [[d('Kabul ediyorum', kod ? 'onay:' + kod : 'onay')]] };
}

export function duzeyKlavye(secili = [], mod = 'w') {
  return {
    inline_keyboard: [
      ...DUZEYLER.map(([kod, ad]) => [d(isaret(secili.includes(kod), ad), `d:${mod}:${kod}`)]),
      [d('Bitti', `d:${mod}:ok`)],
    ],
  };
}

export function ilKlavye(secili = [], sayfa = 0, mod = 'w') {
  const s = Math.min(Math.max(sayfa | 0, 0), SAYFA_SAYISI - 1);
  const bas = s * SAYFA_BOYU;
  const dilim = ILLER.slice(bas, bas + SAYFA_BOYU);
  const satirlar = [];
  for (let i = 0; i < dilim.length; i += 3) {
    satirlar.push(
      dilim.slice(i, i + 3).map((il, j) => d(isaret(secili.includes(il), il), `i:${mod}:t${bas + i + j}`)),
    );
  }
  const nav = [];
  if (s > 0) nav.push(d('◀ Geri', `i:${mod}:p${s - 1}`));
  nav.push(d(`${s + 1}/${SAYFA_SAYISI}`, `i:${mod}:p${s}`));
  if (s < SAYFA_SAYISI - 1) nav.push(d('İleri ▶', `i:${mod}:p${s + 1}`));
  satirlar.push(nav);
  satirlar.push([d(isaret(secili.length === 0, 'Tüm Türkiye'), `i:${mod}:tum`)]);
  satirlar.push([d('Bitti', `i:${mod}:ok`)]);
  return { inline_keyboard: satirlar };
}

export function kategoriKlavye(secili = [], mod = 'w') {
  return {
    inline_keyboard: [
      ...KATEGORILER.map(([kod, ad]) => [d(isaret(secili.includes(kod), ad), `k:${mod}:${kod}`)]),
      [d('Bitti', `k:${mod}:ok`)],
    ],
  };
}

export function kelimeAtlaKlavye() {
  return { inline_keyboard: [[d('Atla', 'kw:atla')]] };
}

export function ayarKlavye(kullanici) {
  return {
    inline_keyboard: [
      [d('Öğrenim düzeyi', 'ay:duzey'), d('İl', 'ay:il')],
      [d('Kategori', 'ay:kategori'), d('Anahtar kelime', 'ay:kelime')],
      [d(`Son gün hatırlatması: ${kullanici && kullanici.hatirlatma ? 'açık' : 'kapalı'}`, 'ay:hat')],
    ],
  };
}

export function silOnayKlavye() {
  return { inline_keyboard: [[d('Evet, hepsini sil', 'sil:evet'), d('Vazgeç', 'sil:hayir')]] };
}
