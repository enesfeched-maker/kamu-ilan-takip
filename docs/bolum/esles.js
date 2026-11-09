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

    for (const p of par) {
      const sart = p.kaynak === 'sart';
      if (sart) {
        const s = sorunlu(p.metin) || (cumleler(p.metin).some((c) => tabloMu(fold(c))) ? 'tablo' : '');
        if (s && !sorun) sorun = s;
      }
      for (const cum of cumleler(p.metin)) {
        const cTok = tokens(cum), cf = fold(cum);
        let tur = '';
        for (const b of bolum) {
          if (dizi(cTok, b)) { tur = 'kesin'; break; }
        }
        if (!tur) for (const b of bolum) {
          if (ortakBas(cTok, b)) { tur = 'muhtemel'; break; }
          if (grup(cTok, cf, b)) { tur = 'muhtemel'; break; }
          if (kismi(cTok, b, cf)) { tur = 'muhtemel'; break; }
        }
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

  return { fold, tokens, bolumCoz, siniflandir, gruplaVeSinifla, parcalar, sorunlu, SIRA };
});
