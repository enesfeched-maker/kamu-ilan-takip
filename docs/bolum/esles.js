/* Bölüm → ilan eşleştirme.
 *
 * ÖNCELİKLİ KURAL: hiçbir ilan sonuçtan SİLİNMEZ. Her ilan tam olarak bir gruba girer; "eşleşmiyor" grubu da
 * sayfada görünür kalır. Bir ilan ancak şart metni TAM ve OKUNAKLI olduğu hâlde bölümü içermiyorsa "eşleşmiyor"
 * olur; metin yoksa, kesikse, bozuksa ya da eksikse "belirsiz" olur ve kullanıcıya "belgeyi kontrol et" denir.
 *
 * Gruplar (iyiden zayıfa): kesin · muhtemel · serbest · belirsiz · eslesmiyor
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.BolumEsles = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const HARITA = { 'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'â': 'a', 'î': 'i', 'û': 'u' };

  /* Türkçe duyarsız karşılaştırma biçimi: küçük harf, aksansız, noktalama yok, kesme işareti silinir ("YDS'den" → "ydsden"). */
  function fold(s) {
    s = String(s == null ? '' : s).replace(/İ/g, 'i').replace(/I/g, 'i').toLowerCase().replace(/̇/g, '');
    s = s.replace(/[çğıöşüâîû]/g, (c) => HARITA[c]).replace(/['’`´‘]/g, '');
    return s.replace(/[^a-z0-9]+/g, ' ').trim();
  }
  const tokens = (s) => fold(s).split(' ').filter(Boolean);
  const kompakt = (s) => fold(s).replace(/ /g, '');

  /* Kök: ek farklarını (mühendisliği/mühendislikleri, iktisat/iktisadi) yutmak için sondan 3 harf atılır. */
  const kok = (t) => (t.length <= 5 ? t : t.slice(0, Math.max(5, t.length - 3)));
  /* Gündelik sözcükle çakışan kısa bölüm adları yalnız tam eşleşir ("son başvuru tarihi" ≠ Tarih, "tıpta uzmanlık" ≠ Tıp). */
  const TAM_ESLES = new Set(['tarih', 'tip', 'dil', 'fen', 'din']);
  function ayniKok(metinTok, bolumTok) {
    if (metinTok === bolumTok) return true;
    if (TAM_ESLES.has(bolumTok)) return false;
    if (bolumTok.length >= 5) return metinTok.startsWith(kok(bolumTok));
    return metinTok.length <= bolumTok.length + 3 && metinTok.startsWith(bolumTok);
  }

  /* "Bilgisayar Mühendisliği (İngilizce) (KKTC)" → [['bilgisayar','muhendisligi']]; "A / B" → iki seçenek. */
  const GURULTU = new Set(['bolumu', 'programi', 'bolum', 'program', 'lisans', 'onlisans', 'mezunu', 'anabilim', 'dali', 'fakultesi', 'fakulte', 'yuksekokulu', 'yuksekokul', 've', 'veya', 'ile', 'ya', 'da']);
  /* Kısaltma ve yazım varyantları: girdiye eşdeğer ek seçenekler üretilir. */
  const SINONIM = [['ekonomi', 'iktisat'], ['makine', 'makina'], ['muh', 'muhendisligi']];
  function bolumCoz(girdi) {
    const secenekler = String(girdi || '').replace(/\([^)]*\)/g, ' ').split(/[\/|]/);
    const sonuc = [];
    const ekle = (t) => { if (!sonuc.some((x) => x.join(' ') === t.join(' '))) sonuc.push(t); };
    for (const s of secenekler) {
      const t = tokens(s).filter((x) => !GURULTU.has(x));
      // yalnız sözcük artığı kalan girdi ("ve", "bölümü") geçersizdir
      if (!t.length || t.every((x) => x.length < 3)) continue;
      const t2 = t.map((x) => (x === 'muh' ? 'muhendisligi' : x));
      ekle(t2);
      for (const [a, b] of SINONIM) {
        if (t2.includes(a)) ekle(t2.map((x) => (x === a ? b : x)));
        if (t2.includes(b)) ekle(t2.map((x) => (x === b ? a : x)));
      }
    }
    return sonuc;
  }

  /* Satır sonları PDF kaydırmasıdır (liste satırlar arasında sürer); cümleyi yalnız nokta, noktalı virgül ve madde imi böler. */
  const CUMLE_AYIR = /[.;•]+/;
  const cumleler = (metin) => String(metin || '').replace(/[\n\r]+/g, ' ').split(CUMLE_AYIR).map((s) => s.trim()).filter(Boolean);

  /* Hariç tutma: bölüm adından sonra 6 sözcük içinde "hariç/dışında" gelir ya da ad, hariç sözcüğü içeren parantezin içindedir. */
  const HARIC_SOZ = /^(haric|harici|haricinde|haricindeki|disinda|disindaki)$/;
  function haricMi(cum, cTok, b) {
    const yer = [];
    for (let i = 0; i < cTok.length; i++) if (b.some((t) => ayniKok(cTok[i], t))) yer.push(i);
    for (const son of yer) for (let i = son + 1; i < cTok.length && i <= son + 6; i++) if (HARIC_SOZ.test(cTok[i])) return true;
    const re = /\(([^)]*)\)/g;
    let m;
    while ((m = re.exec(cum))) {
      const pt = tokens(m[1]);
      if (pt.some((x) => HARIC_SOZ.test(x)) && (dizi(pt, b) || kismi(pt, b, 'mezun'))) return true;
    }
    return false;
  }
  /* Bölüm listesi şartın başka yerinde (tablo/ek/"yukarıda sayılan"): bu cümleden "bölüm yok" sonucu çıkarılamaz. */
  const REFERANS = /\btablo\b|\bek ?\d|\bekte\b|\bekli\b|\bcetvel|asagida (sayilan|belirtilen|yer alan|gosterilen)|yukarida (sayilan|belirtilen|yer alan|gosterilen)|ilan metni(nde|ndeki)|ilanda belirtilen|ilan belgesi(nde)?|belgede belirtilen bolum|belirtilen (alan|bolum|program)|ayri olarak|veya mezun veya|mezun veya belirtilen/;
  /* Nitelik cümlesi: bölüm adının geçtiği yerin gerçekten bir mezuniyet/öğrenim şartı olduğunu gösterir. */
  const NITELIK = /mezun|bolum|program|fakulte|lisans|alan|ogrenim|dal\b|dali|nitelik|diploma|sinifi/;
  /* Öğrenci olmama, ceza, askerlik gibi bölümle ilgisiz şartlar. */
  const NEGATIF = /ogrenci|ogrencilik|ceza|askerlik|kayit(li)?\b|sabika/;

  /* Metnin okunaklı olup olmadığı: kesik ("…"), harfleri ayrılmış ya da boşlukları silinmiş OCR çıktısı. */
  function sorunlu(metin) {
    const m = String(metin || '');
    if (/…\s*$|\.\.\.\s*$/.test(m)) return 'kesik';
    const t = tokens(m);
    if (t.length < 4) return '';
    if (t.some((x) => x.length > 30)) return 'bozuk';
    const tek = t.filter((x) => x.length === 1 && x !== 'a' && x !== 'b' && x !== 'c' && x !== 'd' && x !== 'e' && x !== 'f' && x !== 'g').length;
    if (tek / t.length > 0.12) return 'bozuk';
    const ort = t.reduce((a, x) => a + x.length, 0) / t.length;
    if (ort > 11.5) return 'bozuk';
    return '';
  }

  /* ---- eşleşme türleri (tek cümlelik token dizisi üzerinde) ---- */
  function dizi(cTok, b) {
    for (let i = 0; i + b.length <= cTok.length; i++) {
      let ok = true;
      for (let j = 0; j < b.length; j++) if (!ayniKok(cTok[i + j], b[j])) { ok = false; break; }
      if (ok) return true;
    }
    return false;
  }
  /* "bilgisayar, yazılım ve elektrik mühendislikleri": ortak baş sözcüğü. */
  function ortakBas(cTok, b) {
    if (b.length < 2) return false;
    const mod = b.slice(0, -1), bas = b[b.length - 1];
    const konum = mod.map((m) => cTok.findIndex((x) => ayniKok(x, m)));
    if (konum.some((k) => k < 0)) return false;
    const son = Math.max(...konum), ilk = Math.min(...konum);
    for (let i = son + 1; i < cTok.length && i <= ilk + 14; i++) if (ayniKok(cTok[i], bas)) return true;
    return false;
  }

  /* Fakülte/bölüm grubu: bölümün ait olabileceği genel ifadeler ("mühendislik fakülteleri", "iktisadi ve idari bilimler"). */
  const GRUPLAR = [
    { ad: 'Mühendislik', bolum: (t) => t.some((x) => x.startsWith('muhendis')), desen: /muhendislik (fakulte|bolum|program|alan)|muhendisliklerin|muhendislik fakulteleri/ },
    { ad: 'Eğitim', bolum: (t) => t.some((x) => /^(ogretmen|egitim|rehberlik)/.test(x)), desen: /egitim fakulte|egitim bilimleri|ogretmenlik (bolum|program|alan)/ },
    { ad: 'İktisadi ve idari bilimler', bolum: (t) => t.some((x) => /^(ekonomi|siyaset|isletme|iktisat|maliye|kamu|siyaset|uluslararasi|calisma|ekonometri|sosyal|yonetim|bankacilik|sigortacilik|dis|turizm)/.test(x)),
      desen: /iktisadi ve idari|siyasal bilgiler|isletme fakulte|iktisat fakulte|iibf|sosyal bilimler/ },
    { ad: 'Sağlık', bolum: (t) => t.some((x) => /^(hemsire|ebelik|fizyoterapi|beslenme|odyoloji|ergoterapi|cocuk|saglik|acil|dil ve konusma|podoloji|perfuzyon)/.test(x)), desen: /saglik bilimleri|saglik fakulte|saglik yuksekokul/ },
    { ad: 'Fen-edebiyat', bolum: (t) => t.some((x) => /^(matematik|fizik|kimya|biyoloji|istatistik|tarih|cografya|sosyoloji|psikoloji|felsefe|edebiyat|antropoloji|arkeoloji|dil)/.test(x)), desen: /fen edebiyat|fen fakulte|edebiyat fakulte|fen ve edebiyat/ },
    { ad: 'Tıp / sağlık bilimleri', bolum: (t) => t.some((x) => /^(tip|dis|eczacilik|veteriner)/.test(x)), desen: /tip fakulte|saglik bilimleri/ },
  ];
  function grup(cTok, cum, b) {
    return GRUPLAR.some((g) => g.bolum(b) && g.desen.test(cum));
  }

  /* Kısmi: bölüm adının ayırt edici sözcüğü (ör. "muhasebe", "bilgisayar") cümlede geçiyor; ad tam eşleşmese de olası. */
  const BOLUM_GENEL = new Set(['muhendisligi', 'muhendislik', 'yonetimi', 'uygulamalari', 'uygulama', 'programciligi', 'teknolojisi', 'teknolojileri',
    'bilimleri', 'bilimi', 'hizmetleri', 'ogretmenligi', 'egitimi', 'egitim', 'teknikerligi', 'teknisyenligi', 'ile', 'veya', 'ilgili', 'sistemleri',
    'isletmeciligi', 'danismanligi', 'tasarimi', 'planlama', 'denetimi', 'bolumu', 'sanatlar', 'islemleri', 'hizmet', 'meslek',
    'sinif', 'sinifi', 'siniflari', 'fakultesi', 'fakulte', 'mezunu', 'mezun', 'tarihi', 'yuksekokul', 'yuksekokulu', 'lisans', 'sinavi']);
  function kismi(cTok, b, cf) {
    if (!NITELIK.test(cf)) return false;
    const ayirt = b.filter((t) => t.length >= 5 && !BOLUM_GENEL.has(t));
    return ayirt.some((t) => cTok.some((x) => ayniKok(x, t)));
  }

  /* Bölüm kısıtı olmadığını AÇIKÇA söyleyen ifadeler. */
  const SERBEST = /herhangi bir (lisans |on lisans |onlisans |yuksekokul |fakulte |meslek yuksekokul )?(program|bolum|alan|fakulte|yuksekokul)|her turlu (bolum|program)|tum (bolum|program|alan)\w*|(bolum|program|alan) (sarti|kisiti) (aranmaz|aranmamaktadir|yoktur|bulunmamaktadir)|bolum ayrimi (yoktur|gozetilmeksizin)|bolum gozetilmeksizin/;

  /* Bir cümlenin gerçek bir bölüm LİSTESİ içerip içermediği: bölüm/fakülte/program sözcüğü + yeterli özgül sözcük. */
  const GENEL = new Set(('ve veya ya da ile bir birinden birine herhangi en az mezun mezunu mezunlari olmak olan olarak lisans onlisans on ' +
    'yuksekokul yuksekokulu yuksekogretim yuksekogrenim kurumlarindan kurumlarinin kurumunun fakulte fakultesi fakulteleri fakultelerin ' +
    'bolum bolumu bolumleri bolumlerinden bolumunden program programi programlari programlarindan programindan programlarinin ' +
    'dort yillik iki yurt disindaki dis yok denklik denkligi kabul edilmis edilen yuksekogretim kurulunca yetkili makamlarca ' +
    'egitim ogrenim ogrenimi veren verilen seviyesinde duzeyinde diploma sahibi sahip bulunmak almis tamamlamis ilgili ' +
    'alanlarindan alaninda alandan alan dal dali anabilim sartlarini tasimak sart sartlari kadro kadrosu ilan unvani ' +
    'yukarida asagida belirtilen belirtilmis ozel genel olmamak olmasi gerekmektedir gerekir ayrica ve/veya ' +
    'uzere icin gore kamu personel secme sinavi kpss puan puani puanindan almak almis aranan aranmaktadir ' +
    'tezli tezsiz yuksek derece derecesi doktora sarti sartli arasinda sonra once birlikte veren').split(' '));
  /* Bir bölüm/alan adı gibi görünen sözcük (liste cümlesinde en az biri bulunmalı). */
  const BOLUM_ADI = /muhendis|ogretmen|hekim|hemsire|iktisat|isletme|hukuk|yonetim|bilim|loji|ligi|lugu|sanat|edebiyat|tarih|matematik|fizik|kimya|biyoloji|mimar|ziraat|veteriner|eczac|ilahiyat|iletisim|maliye|ekonomi|muhasebe|bankacilik|insaat|makine|makina|elektrik|elektronik|bilgisayar|teknoloji|teknik|cografya|felsefe|psikoloji|sosyoloji|egitim|turizm|gida|harita|orman|saglik|tip$|dil$/;
  const LISTE_ISARET = /bolum|fakulte|program|anabilim/;
  /* PDF tablosundan gelen başlık/hücre dökümü: sütunlar karışır, "bölüm yok" sonucu çıkarmak güvenilmez. */
  const TABLO_SOZ = new Set(['sira', 'no', 'kadro', 'kadrosu', 'adedi', 'adet', 'derece', 'derecesi', 'unvan', 'unvani', 'ales', 'yds', 'puan', 'puani', 'birimi', 'birim',
    'bolumu', 'abd', 'nitelik', 'nitelikleri', 'cinsiyet', 'cinsiyeti', 'sinifi', 'hizmet', 'kpss', 'taban', 'turu', 'basvuru', 'yeri', 'kodu', 'aranan']);
  function tabloMu(cum) {
    const t = tokens(cum);
    return new Set(t.filter((x) => TABLO_SOZ.has(x))).size >= 3;
  }
  function bolumListesiVar(cum) {
    if (!LISTE_ISARET.test(cum) || tabloMu(cum) || NEGATIF.test(cum) || REFERANS.test(cum) || !/mezun|ogrenim dali/.test(cum)) return false;
    const ozgul = tokens(cum).filter((t) => !GENEL.has(t) && !/^\d+$/.test(t));
    return ozgul.length >= 3 && ozgul.some((t) => BOLUM_ADI.test(t));
  }

  /* ---- ilan kaydından metin parçaları ---- */
  function parcalar(rec) {
    const p = [];
    const ekle = (kaynak, kadro, metin) => { if (metin && String(metin).trim()) p.push({ kaynak, kadro: kadro || '', metin: String(metin) }); };
    for (const s of Array.isArray(rec.sartlar) ? rec.sartlar : []) if (s && typeof s === 'object') ekle('sart', s.kadro, s.metin);
    for (const k of Array.isArray(rec.kadro_detay) ? rec.kadro_detay : []) {
      if (!k || typeof k !== 'object') continue;
      for (const m of Array.isArray(k.maddeler) ? k.maddeler : []) ekle('sart', k.unvan, m);
    }
    for (const k of Array.isArray(rec.yz_kadrolar) ? rec.yz_kadrolar : []) {
      if (!k || typeof k !== 'object') continue;
      for (const m of Array.isArray(k.kosullar) ? k.kosullar : []) ekle('sart', k.unvan, m);
    }
    for (const m of Array.isArray(rec.yz_ortak) ? rec.yz_ortak : []) ekle('sart', '', m);
    ekle('baslik', '', rec.baslik);
    ekle('baslik', '', rec.kadro);
    ekle('ozet', '', rec.ozet);
    return p;
  }

  const SIRA = { kesin: 0, muhtemel: 1, serbest: 2, belirsiz: 3, eslesmiyor: 4 };
  const RUTBE = { ortaogretim: 0, onlisans: 1, lisans: 2 };

  function kisalt(s, n) {
    s = String(s).replace(/\s+/g, ' ').trim();
    return s.length > n ? s.slice(0, n - 1) + '…' : s;
  }

  /* rec: ilanlar.json kaydı; bolum: bolumCoz() çıktısı (dizi dizisi); duzey: kullanıcının öğrenim düzeyi ('' olabilir). */
  function siniflandir(rec, bolum, duzey) {
    if (!bolum || !bolum.length) return { kademe: 'belirsiz', neden: 'Bölüm adı geçersiz', kanit: '', kadro: '', duzeyUyari: '', seviyeler: [], kurumIci: false, duzeltme: false };
    const par = parcalar(rec);
    let en = null; // en iyi kanıt
    const ekleKanit = (kademe, p, cum, neden) => {
      if (!en || SIRA[kademe] < SIRA[en.kademe]) en = { kademe, kadro: p.kadro, kanit: kisalt(cum, 260), neden, kaynak: p.kaynak };
      else if (SIRA[kademe] === SIRA[en.kademe] && p.kadro && !en.kadro) en.kadro = p.kadro;
    };
    const kadrolar = new Set();
    let serbestVar = null;
    let listeVar = false;
    let sorun = '';
    let haricKanit = '';

    for (const p of par) {
      const sart = p.kaynak === 'sart';
      if (sart) {
        const s = sorunlu(p.metin) || (cumleler(p.metin).some((c) => tabloMu(fold(c))) ? 'tablo' : '');
        if (s && !sorun) sorun = s;
      }
      for (const cum of cumleler(p.metin)) {
        const cTok = tokens(cum), cf = fold(cum);
        let tur = '';
        let haricte = false;
        for (const b of bolum) {
          if (dizi(cTok, b)) { if (haricMi(cum, cTok, b)) haricte = true; else { tur = 'kesin'; break; } }
        }
        if (!tur) for (const b of bolum) {
          if (ortakBas(cTok, b) || kismi(cTok, b, cf)) { if (haricMi(cum, cTok, b)) { haricte = true; continue; } tur = 'muhtemel'; break; }
          if (grup(cTok, cf, b)) { tur = 'muhtemel'; break; }
        }
        if (!tur && haricte && !haricKanit) haricKanit = cum;
        // Sınav konusu gibi nitelik cümlesi olmayan geçişler ("Temel Hukuk") kesin sayılmaz.
        if (tur === 'kesin' && (sart || p.kaynak === 'ozet') && !NITELIK.test(cf)) tur = 'muhtemel';
        if (!tur && sorunlu(p.metin)) {
          // boşlukları silinmiş/bozuk metinde yalnız kompakt eşleşme denenir; kesin sayılmaz
          const kc = kompakt(cum);
          for (const b of bolum) { const kb = b.join(''); if (kb.length >= 10 && kc.includes(kb)) { tur = 'muhtemel'; break; } }
        }
        if (tur) {
          ekleKanit(tur, p, cum, tur === 'kesin' ? 'Bölüm adı şartta geçiyor' : 'Bölüm adı ya da bağlı fakülte/bölüm grubu şartta geçiyor');
          if (p.kadro && !/^belgede belirtilen/i.test(p.kadro)) kadrolar.add(p.kadro);
        }
        if (sart) {
          if (REFERANS.test(cf) && /bolum|program|fakulte|alan|mezun/.test(cf) && !sorun) sorun = 'referans';
          if (SERBEST.test(cf) && !serbestVar) serbestVar = { p, cum };
          if (bolumListesiVar(cf)) { if (!listeVar) listeVar = { p, cum }; }
        }
      }
    }

    let kademe, neden = '', kanit = '', kadro = '';
    if (en && en.kademe === 'kesin') { kademe = 'kesin'; neden = en.neden; kanit = en.kanit; }
    else if (en) { kademe = 'muhtemel'; neden = en.neden; kanit = en.kanit; }
    else if (haricKanit) { kademe = 'eslesmiyor'; neden = 'Bölümün bu ilanda hariç tutulmuş'; kanit = kisalt(haricKanit, 260); }
    else if (serbestVar) { kademe = 'serbest'; neden = 'Şartta bölüm kısıtı olmadığı yazıyor'; kanit = kisalt(serbestVar.cum, 260); }
    else {
      const sartSayisi = par.filter((p) => p.kaynak === 'sart').length;
      const eksik = rec.sart_kadro_sayisi && Array.isArray(rec.sartlar) && rec.sartlar.length < rec.sart_kadro_sayisi;
      if (!sartSayisi) { kademe = 'belirsiz'; neden = 'Şart metni siteye alınamadı'; }
      else if (sorun) { kademe = 'belirsiz'; neden = sorun === 'kesik' ? 'Şart metni kesik' : sorun === 'tablo' ? 'Şartlar tablo hâlinde; siteye düzgün alınamadı' : sorun === 'referans' ? 'Bölüm listesi tabloda/ekte; siteye alınamadı' : 'Şart metni okunaksız'; }
      else if (eksik) { kademe = 'belirsiz'; neden = 'Bazı kadroların şartları siteye alınamadı'; }
      else if (rec.belge_uyumsuz) { kademe = 'belirsiz'; neden = 'İlan belgesi doğrulanamadı'; }
      else if (!listeVar) { kademe = 'belirsiz'; neden = 'Bölüm bilgisi şart metninden net okunamadı'; }
      else {
        const sartPar = par.filter((p) => p.kaynak === 'sart');
        const genelEtiket = sartPar.every((p) => !p.kadro || /^(belgede belirtilen|sinav puani)|alinti/.test(fold(p.kadro)));
        const m = /-\s*(\d{1,4})\s/.exec(rec.baslik || '');
        const kadroSayisi = m ? Number(m[1]) : 0;
        const kc = kompakt(sartPar.map((p) => p.metin).join(' '));
        const bozukIz = bolum.some((b) => {
          const kb = b.join('');
          if (kb.length >= 8 && kc.includes(kb)) return true;
          return b.some((t) => t.length >= 7 && !BOLUM_GENEL.has(t) && kc.includes(kok(t)));
        });
        if (rec._duzeltme) { kademe = 'belirsiz'; neden = 'Bu ilan için düzeltme yayımlanmış; güncel şartları kurumdan kontrol et'; }
        else if (genelEtiket && (rec.kategori === 'akademik' || kadroSayisi > 1)) { kademe = 'belirsiz'; neden = 'Kadro şartları kısmen alınmış olabilir; ilan belgesine bak'; }
        else if (bozukIz) { kademe = 'muhtemel'; neden = 'Bölüm adı bitişik/bozuk yazılmış metinde geçiyor olabilir'; }
        else { kademe = 'eslesmiyor'; neden = 'Şartlarda başka bölümler yazıyor'; kanit = kisalt(listeVar.cum, 260); }
      }
    }
    if (kademe === 'kesin' || kademe === 'muhtemel') kadro = [...kadrolar].slice(0, 6).join(' · ');

    // Öğrenim düzeyi: yalnız UYARI; ilan grubunu değiştirmez.
    let duzeyUyari = '';
    const seviyeler = (Array.isArray(rec.ogrenim) && rec.ogrenim.length ? rec.ogrenim : Array.isArray(rec.belge_ogrenim) ? rec.belge_ogrenim : [])
      .filter((x) => x in RUTBE);
    if (duzey && duzey in RUTBE && seviyeler.length && seviyeler.every((x) => RUTBE[x] > RUTBE[duzey])) {
      duzeyUyari = 'İlan daha yüksek öğrenim düzeyi arıyor görünüyor; şartları kontrol et';
    }
    if (kademe === 'serbest' && duzey && !duzeyUyari) {
      const cf = fold(serbestVar.cum);
      const lv = /ortaogretim|lise/.test(cf) ? 'ortaogretim' : /on lisans|onlisans/.test(cf) ? 'onlisans' : /lisans/.test(cf) ? 'lisans' : '';
      if (lv && lv !== duzey) duzeyUyari = 'Bu şart ' + (lv === 'ortaogretim' ? 'ortaöğretim' : lv === 'onlisans' ? 'önlisans' : 'lisans') + ' düzeyi için yazılmış; seninkinden farklı';
    }
    const kurumIci = /gorevde yukselme|unvan degisikligi|kurum ici|kurum personeli icin|yeterlik sinavi|staj/.test(fold([rec.baslik, rec.ilan_turu].join(' ')));
    return { kademe, neden, kanit, kadro, duzeyUyari, seviyeler, kurumIci, duzeltme: !!rec._duzeltme };
  }

  /* Kopya (aynı ilanın başka kaynaktaki kaydı) gruplarında en iyi sonuç birincil kayıt adına yazılır. */
  function gruplaVeSinifla(kayitlar, bolum, duzey, kopyaHaritasi, anahtarFn) {
    const sonuc = new Map(); // anahtar → {rec, ...sınıf, uyeler:[rec]}
    for (const rec of kayitlar) {
      const k = anahtarFn(rec);
      const bas = (kopyaHaritasi && kopyaHaritasi.get(k)) || k;
      const s = siniflandir(rec, bolum, duzey);
      const mevcut = sonuc.get(bas);
      if (!mevcut) sonuc.set(bas, Object.assign({ ana: bas, rec, uyeler: [rec] }, s));
      else {
        mevcut.uyeler.push(rec);
        if (SIRA[s.kademe] < SIRA[mevcut.kademe]) Object.assign(mevcut, s);
        if (k === bas) mevcut.rec = rec; // görüntülenecek kayıt birincil olsun
      }
    }
    return [...sonuc.values()];
  }

  /* ================= Kadro bazlı denetim (ilan sayfasındaki "Bu ilana başvurabilir misin?") =================
   * Her kadronun şartındaki bölüm LİSTESİ maddelerine ayrılır ve seçilen bölüm her maddeyle BİREBİR karşılaştırılır:
   * "Kimya Mühendisliği" maddesi Kimya mezununu, "Hukuk Büro Yönetimi ve Sekreterliği" Hukuk mezununu kapsamaz.
   * Kadro durumu: uygun · kontrol · serbest · haric · degil · bak (okunamadı). */
  const KUYRUK = new Set(['lisans', 'onlisans', 'programlarinin', 'programlarindan', 'programindan', 'programi', 'programlari', 'programlarinda',
    'programlarina', 'programinin', 'bolumlerinin', 'bolumlerinden', 'bolumunden', 'bolumu', 'bolumleri', 'bolumlerine', 'bolumunun', 'fakultesinden',
    'fakultesi', 'fakultelerinin', 'fakultelerinden', 'fakultelerin', 'alanlarinin', 'alanlarindan', 'alanindan', 'alani', 'alanlari', 'dallarinin',
    'dallarindan', 'dalindan', 'dali', 'anabilim', 'mezun', 'mezunu', 'mezunlari', 'birinden', 'birinin', 'yuksekokulundan', 'yuksekokulu']);
  const BAS_GURULTU = new Set(['universitelerin', 'universitenin', 'universite', 'yuksekogretim', 'kurumlarinin', 'kurumlarindan', 'ortaogretim', 'orta',
    'ogretim', 'dort', 'yillik', 'iki', 'en', 'az', 'duzeyinde', 'meslek', 'mesleki', 'yuksekokullarinin', 'yuksekokullarindan', 'fakultelerin',
    'fakultelerinin', 'ilgili', 'olan', 'olmak', 'uzere', 'egitim', 'veren']);
  const BAS_SOZ = new Map([['muhendisligi', 'muhendisligi'], ['muhendislikleri', 'muhendisligi'], ['ogretmenligi', 'ogretmenligi'], ['ogretmenlikleri', 'ogretmenligi']]);
  const AYIR = /\s*(?:,|;|\/|\bveya\b|\bya da\b|\byahut\b|\bile\b)\s*/;

  function seviyeBul(metin) {
    const t = tokens(metin), s = new Set();
    for (let i = 0; i < t.length; i++) {
      const o = t[i - 1];
      if (t[i] === 'onlisans' || (t[i] === 'lisans' && o === 'on')) s.add('onlisans');
      else if (t[i] === 'lisans' && o !== 'yuksek') s.add('lisans');
      else if (t[i] === 'lise' || t[i] === 'ortaogretim' || (t[i] === 'ogretim' && o === 'orta') || t[i] === 'liseler') s.add('ortaogretim');
    }
    return [...s];
  }
  /* Bir cümleden bölüm maddeleri: [{ham, tok}]; yalnız düzey anlatan cümlede 'duzey'; liste değilse null. */
  const DUZEY_SOZ = /^(lise|dengi|okul|okulu|ve|ortaogretim|lisans|onlisans|herhangi|bir|tum|her|turlu|kurumu|kurumlarindan|meslek|lisesi)$/;
  function maddeler(cum) {
    const cf = fold(cum);
    if (!/mezun|program|bolum|fakulte|anabilim|ogrenim dal/.test(cf) || NEGATIF.test(cf)) return null;
    const ham = cum.replace(/\([^)]*\)/g, ' ').split(AYIR).map((x) => x.trim()).filter(Boolean);
    const out = [];
    for (const h of ham) {
      let t = tokens(h);
      // baştaki kalıp ("Üniversitelerin en az dört yıllık lisans eğitimi veren ...") atılır, sonra kuyruk ("... lisans programından mezun") kesilir
      const v = t.lastIndexOf('veren');
      if (v >= 0 && v < t.length - 1) t = t.slice(v + 1);
      while (t.length && (BAS_GURULTU.has(t[0]) || /^\d+$/.test(t[0]) || t[0] === 'lisans' || t[0] === 'onlisans' || t[0] === 'egitimi')) t = t.slice(1);
      const k = t.findIndex((x, i) => KUYRUK.has(x) || (x === 'on' && t[i + 1] === 'lisans') || (x === 'ogrenim' && /^dal/.test(t[i + 1] || '')));
      if (k >= 0) t = t.slice(0, k);
      t = t.filter((x) => !GURULTU.has(x) || x === 've');
      if (t.length) out.push({ ham: h.replace(/\s+/g, ' ').replace(/\s*(lisans|ön ?lisans|önlisans|öğrenim dal|program|bölüm|fakülte).*$/i, '').trim(), tok: t });
    }
    if (!out.length) return null;
    // yalnız düzey anlatan cümle ("Lise ve dengi okul mezunu olmak") liste sayılmaz
    if (out.every((m) => m.tok.every((x) => DUZEY_SOZ.test(x)))) return 'duzey';
    if (!out.some((m) => m.tok.some((x) => BOLUM_ADI.test(x) || /lik$/.test(x)))) return null;
    // "Bilgisayar, Yazılım veya Elektrik Mühendisliği/Mühendislikleri": baş sözcük, bir önceki baş sözcüklü maddeye
    // kadar geriye doğru tek-iki sözcüklü maddelere de eklenir
    let onceki = -1;
    out.forEach((m, i) => {
      const bas = BAS_SOZ.get(m.tok[m.tok.length - 1]);
      if (!bas) return;
      for (let j = onceki + 1; j < i; j++) if (out[j].tok.length <= 2 && !out[j].tok.some((x) => BAS_SOZ.has(x))) out[j].genis = out[j].tok.concat(bas);
      onceki = i;
    });
    return out;
  }
  const esit = (a, b) => a.length === b.length && a.every((x, i) => x === b[i] || (b[i].length >= 6 && ayniKok(x, b[i]) && Math.abs(x.length - b[i].length) <= 3));
  /* madde ↔ bölüm: 'tam' | 'genis' (ortak baş sözcükle) | 've' ("Kimya ve Biyokimya" içinde) | '' */
  function maddeEsles(m, b) {
    const t = m.tok.filter((x) => x !== 've');
    if (esit(t, b)) return 'tam';
    if (m.genis && esit(m.genis.filter((x) => x !== 've'), b)) return 'genis';
    if (m.tok.includes('ve')) {
      const parca = []; let cur = [];
      for (const x of m.tok) { if (x === 've') { parca.push(cur); cur = []; } else cur.push(x); }
      parca.push(cur);
      if (parca.some((p) => esit(p, b))) return 've';
    }
    return '';
  }

  function kadroGruplari(rec) {
    const ortak = [], gruplar = [];
    const ekle = (ad, metinler) => { const m = metinler.filter((x) => x && String(x).trim()); if (ad || m.length) gruplar.push({ ad: String(ad || '').replace(/\s+/g, ' ').trim(), metinler: m.map(String) }); };
    const kd = (Array.isArray(rec.kadro_detay) ? rec.kadro_detay : []).filter((k) => k && typeof k === 'object');
    const yz = (Array.isArray(rec.yz_kadrolar) ? rec.yz_kadrolar : []).filter((k) => k && typeof k === 'object');
    if (kd.length) kd.forEach((k) => ekle(k.unvan, (k.maddeler || []).concat(k.ogrenim ? [String(k.ogrenim)] : [])));
    else if (yz.length) yz.forEach((k) => ekle(k.unvan, (k.kosullar || []).concat(k.ogrenim ? [String(k.ogrenim)] : [])));
    const genelMi = (ad) => !ad || /^(belgede belirtilen|sinav puani|genel|ortak)/.test(fold(ad));
    for (const s of Array.isArray(rec.sartlar) ? rec.sartlar : []) {
      if (!s || typeof s !== 'object') continue;
      if (genelMi(s.kadro)) ortak.push(String(s.metin || ''));
      else if (!kd.length && !yz.length) {
        const g = gruplar.find((x) => fold(x.ad) === fold(s.kadro));
        if (g) g.metinler.push(String(s.metin || '')); else ekle(s.kadro, [s.metin]);
      }
    }
    for (const b of Array.isArray(rec.kadro_ortak) ? rec.kadro_ortak : []) if (Array.isArray(b)) ortak.push(...(b[1] || []).map(String));
    for (const m of Array.isArray(rec.yz_ortak) ? rec.yz_ortak : []) ortak.push(String(m));
    return { gruplar, ortak };
  }

  /* Tek metin kümesi için bölüm sonucu. */
  /* GÜVENLİK KURALI: "degil" yalnız temiz okunan bir bölüm listesinde bölüm gerçekten yoksa verilir. Liste tablo/ek
     dökümüyse ya da bölüm adı listede geçip madde ayrımı şüpheliyse sonuç "kontrol" ya da "bak" olur. */
  const GRUP_SINIRI = /(muhendislik|fen|edebiyat|saglik|iktisadi|egitim|hukuk|tip|ilahiyat|ziraat|mimarlik|iletisim|turizm|sanatlar|teknoloji)\w*\s+(\w+\s+)?(fakulte|yuksekokul)\w*\s+herhangi/;
  function metinDenetle(metinler, cozumler) {
    let en = null, listeVar = false, kirliListe = false, serbest = '', haric = '', bozuk = false, grupIz = '', duzey = '';
    const yaz = (durum, bolum, kanit) => {
      const s = { uygun: 0, kontrol: 1 };
      if (!en || s[durum] < s[en.durum]) en = { durum, bolum, kanit: kisalt(kanit, 220) };
    };
    for (const metin of metinler) {
      // yalnız öğrenim anlatan madde okunaksızsa önemlidir ("6 ay çalışmış olmak" gibi kısa maddeler bozuk sayılmaz)
      if (sorunlu(metin) && /mezun|program|bolum|fakulte|ogrenim/.test(fold(metin))) bozuk = true;
      for (const cum of cumleler(metin)) {
        const cf = fold(cum), cTok = tokens(cum);
        // "Mühendislik veya Fen Fakültelerinin herhangi bir bölümü" serbest değildir: fakülte grubu sınırı vardır
        if (SERBEST.test(cf) && !serbest && !GRUP_SINIRI.test(cf)) serbest = cum;
        else if (SERBEST.test(cf) && GRUP_SINIRI.test(cf) && !grupIz && cozumler.length) grupIz = cozumler[0].ad + '|' + cum;
        const mz = maddeler(cum);
        if (mz === 'duzey') { if (!duzey) duzey = cum; continue; }
        const tablo = tabloMu(cf) || REFERANS.test(cf);
        if (mz) {
          if (tablo) kirliListe = true; else listeVar = true;
          for (const c of cozumler) for (const b of c.b) {
            let bulundu = false;
            for (const m of mz) {
              const e = maddeEsles(m, b);
              if (!e) continue;
              if (haricMi(cum, cTok, b)) { if (!haric) haric = cum; bulundu = true; continue; }
              yaz(e === 've' || tablo ? 'kontrol' : 'uygun', c.ad, m.ham || cum); bulundu = true;
            }
            if (bulundu || !dizi(cTok, b) || haricMi(cum, cTok, b)) continue;
            // bölüm adı cümlede geçiyor ama hiçbir maddeyle birebir değil: madde başka bir programsa
            // ("Kimya Mühendisliği", "Hukuk Büro Yönetimi") eşleşme yok; ayrım şüpheliyse kontrol
            const m = mz.find((x) => dizi(x.tok.filter((y) => y !== 've'), b));
            const t = m ? m.tok.filter((y) => y !== 've') : [];
            const sonra = m ? t.length - (t.findIndex((y, i) => b.every((z, j) => t[i + j] && ayniKok(t[i + j], z))) + b.length) : 0;
            if (!m || tablo || t.length > 6 || sonra === 0) yaz('kontrol', c.ad, m ? m.ham : cum);
          }
        } else {
          for (const c of cozumler) for (const b of c.b) {
            if (dizi(cTok, b) && NITELIK.test(cf) && !haricMi(cum, cTok, b)) yaz('kontrol', c.ad, cum);
          }
        }
        if (!en) for (const c of cozumler) for (const b of c.b) {
          if (grup(cTok, cf, b) && !haricMi(cum, cTok, b) && !grupIz) grupIz = c.ad + '|' + cum;
        }
      }
    }
    if (en) return en;
    if (haric) return { durum: 'haric', kanit: kisalt(haric, 220) };
    if (serbest) return { durum: 'serbest', kanit: kisalt(serbest, 220) };
    if (grupIz) { const i = grupIz.indexOf('|'); return { durum: 'kontrol', bolum: grupIz.slice(0, i), kanit: kisalt(grupIz.slice(i + 1), 220) }; }
    if (bozuk || kirliListe) return { durum: 'bak' };
    if (listeVar) return { durum: 'degil' };
    return { durum: 'yok', duzey: duzey ? kisalt(duzey, 160) : '' };   // yok: metinde bölüm listesi hiç yok
  }

  /* rec: ilanlar.json kaydı; girdiler: seçilen bölüm adları; duzey: kullanıcının öğrenim düzeyi.
     Dönüş: { kadrolar:[{ad, seviyeler, durum, bolum, kanit}], eksik, genel } */
  const DURUM_SIRA = { uygun: 0, kontrol: 1, serbest: 2, bak: 3, haric: 4, degil: 5 };
  function kadroBazli(rec, girdiler, duzey) {
    const cozumler = (girdiler || []).map((ad) => ({ ad, b: bolumCoz(ad) })).filter((c) => c.b.length);
    const { gruplar, ortak } = kadroGruplari(rec);
    if (!gruplar.length) {
      // kadrolara ayrılmamış ilan: /bolum/ sayfasının bütün-ilan denetimi kullanılır (iki sayfa aynı sonucu verir)
      const ESLE = { kesin: 'uygun', muhtemel: 'kontrol', serbest: 'serbest', belirsiz: 'bak', eslesmiyor: 'degil' };
      let en = null;
      for (const c of cozumler) {
        const r = siniflandir(rec, c.b, duzey);
        const d = r.kademe === 'eslesmiyor' && /hariç/.test(r.neden || '') ? 'haric' : ESLE[r.kademe] || 'bak';
        if (!en || DURUM_SIRA[d] < DURUM_SIRA[en.durum]) en = { ad: '', seviyeler: [], durum: d, bolum: c.ad, kanit: r.kanit || '', neden: r.neden || '' };
      }
      return { kadrolar: en ? [en] : [], digerDuzey: 0, eksik: false, genel: true, duzeltme: !!rec._duzeltme };
    }
    const ortakSonuc = metinDenetle(ortak, cozumler);
    const ortakSeviye = seviyeBul(ortak.join(' '));
    const liste = (gruplar.length ? gruplar : [{ ad: '', metinler: [] }]).map((g) => {
      const seviyeler = seviyeBul([g.ad].concat(g.metinler).join(' '));
      let s = metinDenetle(g.metinler, cozumler);
      // kadronun kendi metninde bölüm listesi yoksa ortak şartlara bakılır; o da yoksa yalnız düzey aranıyor demektir
      if (s.durum === 'yok') {
        if (!/^(yok|bak)$/.test(ortakSonuc.durum)) s = ortakSonuc;
        else if (s.duzey || ortakSonuc.duzey) s = { durum: 'serbest', kanit: s.duzey || ortakSonuc.duzey };   // "Lise ve dengi okul mezunu olmak"
        else s = { durum: 'bak' };
      }
      return Object.assign({ ad: g.ad, seviyeler: seviyeler.length ? seviyeler : (gruplar.length ? [] : ortakSeviye) }, s);
    });
    const kadrolar = duzey ? liste.filter((k) => !k.seviyeler.length || k.seviyeler.includes(duzey)) : liste;
    const eksik = !!(rec.sart_kadro_sayisi && gruplar.length && gruplar.length < rec.sart_kadro_sayisi);
    return { kadrolar, digerDuzey: liste.length - kadrolar.length, eksik, genel: !gruplar.length, duzeltme: !!rec._duzeltme };
  }

  return { fold, tokens, bolumCoz, siniflandir, gruplaVeSinifla, parcalar, sorunlu, SIRA, kadroBazli, seviyeBul };
});
