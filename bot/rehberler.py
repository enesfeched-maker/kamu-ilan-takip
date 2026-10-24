"""Rehber yazıları: /rehber/ ve /rehber/<slug>/ (19 Ekim 2026).

KPSS adaylarının en sık sorduğu konularda kalıcı, özgün yazılar. Bilgiler genel çerçevedir; her yazının sonunda resmî ilanın
esas olduğu hatırlatılır. Metinler sitenin dilinde (sen diye hitap, sade) yazıldı. Sayfalar site haritasına girer."""
import json

GUNCELLEME = '2026-10-19'

# (slug, başlık, açıklama, giriş, [(ara başlık, [paragraf | ('madde', [maddeler])])], [(ilgili bağlantı adı, göreli yol)])
REHBERLER = [
    ('kpss-ile-memur-olmak', 'KPSS ile memur olmak: adım adım yol haritası',
     'KPSS ile kamuya atanmanın yolları: merkezi yerleştirme, kurum ilanları, puan türleri, başvuru ve atama süreci tek yazıda.',
     'Kamuda kadrolu ya da sözleşmeli çalışmanın en yaygın yolu KPSS puanıdır. Ama puanı almak işin yarısı: hangi puanla nereye, '
     'hangi yolla başvurulacağını bilmek de en az o kadar önemli. Bu yazıda süreci baştan sona sade biçimde anlattık.',
     [('1. Önce hangi KPSS\'ye gireceğini belirle', [
         'Hangi öğrenim düzeyinden sınava girebileceğin ve hangi kadroları tercih edebileceğin, ilgili sınav ve yerleştirme kılavuzlarına bağlıdır. Mezuniyet tarihini, sınava girdiğin öğrenim düzeyini ve kullanacağın puanı birlikte kontrol et. Üst düzey bir diploma, alt düzeydeki bütün kadrolara otomatik başvuru hakkı vermez.',
         'Sınavın hangi yıl yapıldığı da önemlidir: KPSS puanlarının geçerlilik süresi sınırlıdır ve her ilan hangi yılın puanını kabul '
         'ettiğini açıkça yazar.']),
      ('2. Puan türünü tanı', [
         'Her kadro belirli bir puan türüyle eşleşir. Genel yetenek ve genel kültür testlerinden hesaplanan puanlar en yaygın olanlardır: '
         'lisans için P3, önlisans için P93, ortaöğretim için P94. A grubu kadrolarda alan bilgisi testleri de devreye girer ve farklı '
         'puan türleri (P1, P2, P4… P48 gibi) kullanılır.',
         ('madde', ['İlanda yazan puan türü dışında bir puanla başvuru yapılamaz.',
                    'Aynı sınavdan birden fazla puan türün olabilir; her biri ayrı değerlendirilir.',
                    'Puan türlerinin ayrıntısı için Puan türleri rehberine bakabilirsin.'])]),
      ('3. İki ana yol: merkezi yerleştirme ve kurum ilanları', [
         'Merkezi yerleştirmede (ÖSYM\'nin "KPSS tercihleri") kurumlar kadrolarını ÖSYM\'ye bildirir, adaylar tercih yapar ve ÖSYM '
         'puan sırasına göre yerleştirir. Kurum ilanlarında ise kurum kendi ilanını yayımlar; başvuruları kendisi toplar ve çoğu '
         'zaman KPSS puanının yanında sözlü ya da yazılı sınav, KPSS sırası ya da kura uygular.',
         'KPSS Tercihi\'nde gördüğün ilanların büyük çoğunluğu kurum ilanlarıdır. Taban puanları sayfası ise merkezi yerleştirmenin '
         'geçmiş sonuçlarını gösterir; ikisini birlikte okumak hangi puanla nerede şansın olduğunu daha iyi gösterir.']),
      ('4. İlanı dikkatle oku', [
         ('madde', ['Son başvuru günü ve saati: bazı ilanlar 17.00\'de, bazıları 23.59\'da kapanır.',
                    'Başvuru yöntemi: e-Devlet / Kariyer Kapısı, İŞKUR, şahsen ya da posta.',
                    'Öğrenim ve bölüm şartı: "ilgili bölüm mezunu olmak" ifadesi bölüm listesini kapsar; listede yoksan başvuru geçersiz sayılabilir.',
                    'Yaş, cinsiyet, sürücü belgesi, sertifika ve deneyim şartları.',
                    'Asgari KPSS puanı ve hangi yılın sınavının geçerli olduğu.'])]),
      ('5. Başvur, sonucu takip et', [
         'Başvurudan sonra kurum genellikle sınava çağrılacak adayları ya da sonuç listesini kendi internet sitesinde duyurur. '
         'Sözlü sınav tarihleri ve istenecek belgeler bu duyurularda yer alır. Duyuruları kaçırmamak için kurumun sitesini ve resmî '
         'ilan kaynağını düzenli kontrol et.',
         'Atanmaya hak kazandığında, güvenlik soruşturması/arşiv araştırması ve sağlık şartı gibi adımlar tamamlandıktan sonra atama yapılır.'])],
     [('Nitelik kodlarını kontrol et', 'rehber/kpss-nitelik-kodu-nasil-okunur/'), ('Puan türleri rehberi', 'rehber/kpss-puan-turleri/'), ('KPSS taban puanları', 'kpss-taban-puanlari/'), ('Açık ilanlar', '#ilanlar')]),

    ('kpss-puan-turleri', 'KPSS puan türleri: P3, P93, P94 ve diğerleri ne anlama gelir?',
     'KPSS puan türleri neyi ölçer, hangi kadroda hangisi istenir? P3, P93, P94 ve A grubu puanlarının sade açıklaması.',
     'İlanlarda gördüğün "KPSSP3" ya da "KPSSP94" gibi ifadeler, başvurunun hangi puanla değerlendirileceğini gösterir. Yanlış puan '
     'türüyle yapılan başvuru geçersiz sayılır; bu yüzden puan türünü doğru okumak çok önemlidir.',
     [('Genel yetenek ve genel kültür puanları', [
         'Bu puanlar sınavın genel yetenek ve genel kültür testlerinden hesaplanır ve memur alımlarının çoğunda kullanılır.',
         ('madde', ['P3: lisans mezunlarına yönelik kadrolarda en sık istenen puan.',
                    'P93: önlisans mezunlarına yönelik kadrolarda kullanılır.',
                    'P94: ortaöğretim (lise) mezunlarına yönelik kadrolarda kullanılır.'])]),
      ('A grubu ve alan bilgisi puanları', [
         'Uzman yardımcılığı, denetmen yardımcılığı gibi A grubu kadrolarda genel yetenek-genel kültürün yanında alan bilgisi testleri '
         '(hukuk, iktisat, maliye, muhasebe, kamu yönetimi gibi) de hesaba katılır. Bu kadrolarda ilan, kabul edilen puan türlerini '
         '(örneğin P1, P2, P4… P48) tek tek sayar.']),
      ('Öğretmenlik başvuruları için kapsam notu', [
         'Bu rehberin kapsamı P3, P93 ve P94 puanlarının kamu ilanlarında okunmasıdır. Öğretmenlik başvurularında ilgili dönemin MEB ve ÖSYM duyurularındaki sınav, puan ve başvuru koşullarını ayrıca incele.']),
      ('İlanı okurken dikkat', [
         ('madde', ['İlan birden fazla puan türünü kabul edebilir; hangisi yüksekse otomatik seçilmez, ilanın tarifine bakılır.',
                    'Asgari puan şartı (örneğin "en az 70 puan") ile yerleştirme sırası farklı şeylerdir: asgari puan başvuru şartıdır, '
                    'sıralama ise başvuranlar arasında yapılır.',
                    'Puanın hangi yılın sınavından alındığı ilanda yazar; eski yılın puanı kabul edilmeyebilir.'])])],
     [('Taban puanını yorumla', 'rehber/kpss-taban-puani-nasil-yorumlanir/'), ('KPSS ile memur olmak', 'rehber/kpss-ile-memur-olmak/'), ('Tercih robotu', 'puanlar/')]),

    ('merkezi-yerlestirme-ve-kurum-ilanlari', 'Merkezi yerleştirme ile kurum ilanları arasındaki fark',
     'ÖSYM tercihleri ile kurumların kendi ilanları nasıl işler? Başvuru, sınav ve sıralama farkları.',
     'KPSS ile atanmanın iki ana kapısı vardır. İkisi de KPSS puanına dayanır ama işleyişleri farklıdır. Hangisinde nasıl hazırlanman '
     'gerektiğini bilmek zaman kazandırır.',
     [('Merkezi yerleştirme (ÖSYM tercihleri)', [
         'Kurumlar boş kadrolarını ÖSYM\'ye bildirir. ÖSYM tercih kılavuzunu yayımlar, adaylar belirlenen tarihlerde tercih yapar. '
         'Yerleştirme, puan sırasına ve tercih sırasına göre ÖSYM tarafından yapılır; ayrıca sınav yoktur.',
         'Her kadronun o dönemki en küçük ve en büyük puanları ÖSYM tarafından "sayısal bilgiler" olarak açıklanır. KPSS Tercihi\'ndeki '
         'taban puanları bu verilerden derlenir.']),
      ('Kurum ilanları', [
         'Kurum, kadrosunu kendisi ilan eder. Başvurular çoğu zaman e-Devlet üzerinden Kariyer Kapısı\'nda, bazen İŞKUR\'da, bazen de '
         'şahsen ya da postayla alınır. Değerlendirme kurumun ilanında yazan yönteme göre yapılır:',
         ('madde', ['KPSS puan sırası (sınavsız),', 'KPSS puanına göre belirlenen sayıda adayla sözlü ve/veya yazılı sınav,',
                    'işçi alımlarında İŞKUR listesi ve noter kurası.'])]),
      ('Hangisi daha avantajlı?', [
         'İkisi birbirinin alternatifi değil, tamamlayıcısıdır. Merkezi yerleştirme dönemleri yılda birkaç kez açılırken kurum ilanları '
         'yıl boyunca yayımlanır. Belediyeler, üniversiteler ve bazı kurumlar özellikle kendi ilanlarıyla alım yapar; bu ilanlarda '
         'başvuran sayısı merkezi yerleştirmeye göre daha az olabilir.']),
      ('Taban puanlarını doğru yorumla', [
         'Geçmiş taban puanları sana fikir verir ama garanti değildir: kontenjan, başvuran sayısı ve o dönemki puan dağılımı her '
         'seferinde değişir. Kurum ilanlarında ise belirleyici olan ilanın kendi şartları ve sınavıdır.'])],
     [('KPSS taban puanları', 'kpss-taban-puanlari/'), ('Açık ilanlar', '#ilanlar')]),

    ('belediye-memur-alimi', 'Belediye memur alımları nasıl yapılır?',
     'Belediyelerin "ilk defa atanmak üzere" memur ilanları: şartlar, KPSS puanı, sınav ve başvuru yöntemi.',
     'Belediyeler zabıta memuru, itfaiye eri, mühendis, tekniker gibi kadrolara sık sık kendi ilanlarıyla alım yapar. Bu ilanlar '
     'çoğu zaman küçük kontenjanlı ve kısa sürelidir; o yüzden gözden kaçmaları kolaydır.',
     [('İlanlar nerede yayımlanır?', [
         'Belediye memur ilanları Resmî Gazete\'de, belediyenin internet sitesinde ve Çevre, Şehircilik ve İklim Değişikliği Bakanlığı '
         'Yerel Yönetimler sayfasında duyurulur; çoğu İŞKUR ve Kamu İlan (SBB) üzerinden de görünür. KPSS Tercihi bu kaynakları birlikte '
         'tarar.']),
      ('Genel şartlar', [
         ('madde', ['657 sayılı Devlet Memurları Kanunu\'nun 48. maddesindeki genel şartlar (Türk vatandaşı olmak, kamu haklarından '
                    'mahrum bulunmamak, askerlik durumu vb.),',
                    'ilanda belirtilen öğrenim düzeyi ve bölüm,',
                    'ilanda belirtilen yıl ve puan türünde asgari KPSS puanı,',
                    'zabıta ve itfaiye gibi kadrolarda boy-kilo, yaş ve sürücü belgesi gibi özel şartlar.'])]),
      ('Değerlendirme nasıl yapılır?', [
         'Başvurular KPSS puanına göre sıralanır ve kadro sayısının belirli bir katı kadar aday sözlü ve/veya yazılı sınava çağrılır. '
         'Başarı puanı genellikle sınav puanının ortalamasıyla belirlenir; asıl ve yedek adaylar belediyenin sitesinde ilan edilir.']),
      ('Başvuruda sık yapılan hatalar', [
         ('madde', ['Son gün kargoya verilen başvurunun ilan tarihinden sonra ulaşması (ilanda "postadaki gecikmeler dikkate alınmaz" yazar),',
                    'eksik belge: KPSS sonuç belgesi çıktısı, diploma örneği, fotoğraf ve başvuru formu,',
                    'birden fazla kadroya başvurulamayacağı halde iki kadro için form doldurmak.'])])],
     [('Belediye ilanları', '#ilanlar'), ('Başvuruda istenen belgeler', 'rehber/basvuru-belgeleri-ve-hatalar/')]),

    ('sozlesmeli-personel-4b', 'Sözleşmeli personel (4/B) nedir? Üniversite ve kurum alımları',
     '657 sayılı Kanun\'un 4/B maddesine göre sözleşmeli personel alımları: şartlar, KPSS sıralaması ve haklar.',
     'İlanlarda sık gördüğün "4/B sözleşmeli personel" ifadesi, 657 sayılı Devlet Memurları Kanunu\'nun 4. maddesinin (B) fıkrasına '
     'göre istihdamı anlatır. Üniversiteler, hastaneler ve birçok kurum bu yolla alım yapar.',
     [('Nasıl alınır?', [
         'Kurum kadroları, öğrenim düzeyi ve aranan nitelikleri ilan eder. Başvurular çoğu zaman e-Devlet / Kariyer Kapısı üzerinden '
         'alınır ve adaylar KPSS puan sırasına göre yerleştirilir; çoğunda ayrıca sınav yapılmaz. Bazı kurumlar sözlü sınav da uygulayabilir.']),
      ('Kimler başvurabilir?', [
         ('madde', ['İlanda belirtilen öğrenim düzeyi ve bölümden mezun olanlar,',
                    'ilanda belirtilen yılın KPSS\'sine girip ilgili puan türünden puanı olanlar,',
                    'hemşire, sağlık teknikeri gibi kadrolarda ilgili diploma ve sertifikaya sahip olanlar.'])]),
      ('Kadrolu memurluktan farkı', [
         'Sözleşmeli personel, kurumla yıllık hizmet sözleşmesi imzalar. Belirli şartlar ve süreler sağlandığında kadroya geçiş '
         'mümkün olabilir; bu konudaki güncel düzenlemeler için ilgili mevzuatı ve kurum duyurularını takip etmek gerekir.']),
      ('Dikkat edilmesi gerekenler', [
         ('madde', ['Aynı ilanda birden fazla kadro varsa genellikle yalnız birine başvurulabilir.',
                    'Yerleştirme sonrası istenen belgeler kısa sürede teslim edilmezse hak kaybedilir.',
                    'Ön lisans ve ortaöğretim kadrolarında P93 ve P94 puan türlerinin hangi yıla ait olduğuna dikkat et.'])])],
     [('Açık ilanlar', '#ilanlar'), ('KPSS puan türleri', 'rehber/kpss-puan-turleri/')]),

    ('kamu-isci-alimi', 'Kamu işçi alımları: İŞKUR, kura ve öncelikli gruplar',
     'Kamu kurumlarına sürekli işçi alımları nasıl yapılır? İŞKUR başvurusu, noter kurası, engelli ve eski hükümlü kontenjanları.',
     'Kamuya işçi alımları memur alımlarından farklı kurallarla yapılır. Çoğu işçi alımında KPSS şartı aranmaz; başvurular Türkiye İş '
     'Kurumu (İŞKUR) üzerinden alınır.',
     [('Başvuru nereden yapılır?', [
         'Kurumlar işçi taleplerini İŞKUR\'a bildirir. Başvurular İŞKUR\'un internet sitesi ya da hizmet merkezleri üzerinden yapılır; '
         'ilanda aksi yazmıyorsa kuruma doğrudan yapılan başvurular geçersizdir.']),
      ('Seçim nasıl yapılır?', [
         ('madde', ['Nitelik gerektirmeyen işlerde, şartları taşıyan başvuru sayısı fazlaysa adaylar noter huzurunda kura ile belirlenir.',
                    'Nitelik gerektiren işlerde sözlü ve/veya uygulamalı sınav yapılabilir.',
                    'İlanda belirtilen yerde ikamet şartı aranabilir.'])]),
      ('Öncelikli gruplar', [
         'Engelli ve eski hükümlü işçi alımları ayrı kontenjanlarla yapılır. Engelli kontenjanında genellikle en az %40 engelli olduğunu '
         'gösteren sağlık kurulu raporu istenir. Bazı ilanlarda şehit yakını ve gazi gibi öncelikli adaylar için ayrı hükümler bulunur.']),
      ('Dikkat', [
         'İşçi ilanları genellikle kısa sürelidir (çoğu zaman 4–5 gün). Başvuru tarihlerini kaçırmamak için ilan yayımlandığında hemen '
         'başvurmak gerekir.'])],
     [('Açık ilanlar', '#ilanlar')]),

    ('sozlesmeli-bilisim-personeli', 'Sözleşmeli bilişim personeli alımları nasıl yapılır?',
     'Kamu kurumlarının sözleşmeli bilişim personeli ilanları: mezuniyet, deneyim, KPSS ve yabancı dil puanı, ücret tavanı.',
     'Bakanlıklar, kurumlar ve bankacılık düzenleyicileri yazılım, siber güvenlik ve sistem uzmanı gibi kadrolara "sözleşmeli bilişim '
     'personeli" ilanlarıyla alım yapar. Bu ilanların kendine özgü kuralları vardır.',
     [('Kimler başvurabilir?', [
         ('madde', ['Bilgisayar, yazılım, elektrik, elektronik ve endüstri mühendisliği gibi bölümlerin mezunları (ilan bölüm listesini verir),',
                    'bazı pozisyonlarda diğer mühendislik bölümleri ile fen ve eğitim fakültelerinin ilgili bölümleri,',
                    'pozisyona göre belirli süre mesleki deneyimi olanlar ve istenen programlama/teknoloji bilgisini belgeleyenler.'])]),
      ('Sıralama nasıl yapılır?', [
         'Bu ilanların çoğunda adaylar KPSS P3 puanı ile yabancı dil puanının belirli ağırlıklarla toplanmasıyla sıralanır ve sözlü ya da '
         'yazılı sınava çağrılır. Bazı ilanlarda KPSS şartı aranmaz ya da KPSS puanı olmayanlara belirli bir puan verilir. Formül her ilanda '
         'açıkça yazar; mutlaka ilanın kendi metnine bak.']),
      ('Ücret ve deneyim', [
         'Ücretler ilanda "brüt sözleşme ücret tavanının 2, 3 veya 4 katı" gibi ifade edilir ve kat arttıkça istenen deneyim süresi artar. '
         'Deneyim belgesi olarak SGK hizmet dökümü ve işveren yazısı istenir.']),
      ('İpucu', [
         'Bilişim ilanları genellikle Kariyer Kapısı üzerinden yayımlanır ve başvuru süresi kısadır. Sitedeki "Bilişim" kategorisini ve '
         'Telegram kanalını takip etmek, ilanı ilk gün görmeni sağlar.'])],
     [('Bilişim ilanları', '#ilanlar')]),

    ('ekpss-engelli-memur-alimi', 'EKPSS ve engelli kamu personeli alımları',
     'Engelli adaylar için EKPSS nedir, engelli memur ve işçi alımları nasıl yapılır, hangi belgeler istenir?',
     'Engelli vatandaşların kamuya atanması için ayrı bir sınav ve ayrı kontenjanlar bulunur. Bu yazıda temel çerçeveyi özetledik.',
     [('EKPSS nedir?', [
         'Engelli Kamu Personeli Seçme Sınavı (EKPSS), engelli adayların merkezi ve kurum yerleştirmeleri için ÖSYM tarafından yapılan '
         'sınavdır. Öğrenim düzeyine göre puan türleri hesaplanır ve yerleştirmeler bu puanlara göre yapılır.']),
      ('Memur kadroları', [
         'Engelli memur alımları EKPSS tercihleriyle merkezi olarak ya da kurumların engelli kadrolarına yönelik ilanlarıyla yapılır. '
         'Başvuruda engellilik oranını gösteren sağlık kurulu raporu istenir.']),
      ('İşçi kadroları', [
         'Kamu kurumlarının engelli işçi alımları İŞKUR üzerinden yapılır. İlanlarda çoğunlukla en az %40 engelli olduğunu gösteren '
         'geçerli sağlık kurulu raporu şartı aranır; bazı alımlarda sözlü sınav ya da kura uygulanır.']),
      ('Dikkat edilmesi gerekenler', [
         ('madde', ['Raporun ilan tarihinde geçerli olması gerekir.',
                    'Kadronun görev gerekleri ile engel durumunun uyumu ilanda ayrıca belirtilebilir.',
                    'Ayrıntılar için ilanın resmî metni ve ÖSYM kılavuzu esas alınır.'])])],
     [('Açık ilanlar', '#ilanlar')]),

    ('basvuru-belgeleri-ve-hatalar', 'Kamu ilanlarına başvuruda istenen belgeler ve sık yapılan hatalar',
     'Başvurularda en sık istenen belgeler, son gün yoğunluğu, eksik belge ve yanlış kadro seçimi gibi hatalardan kaçınma yolları.',
     'Şartları taşıyan birçok aday küçük bir hata yüzünden elenir. Başvurudan önce bu listeyi kontrol etmek seni gereksiz hak '
     'kayıplarından korur.',
     [('En sık istenen belgeler', [
         ('madde', ['KPSS sonuç belgesi (genellikle internet çıktısı, doğrulama kodlu),',
                    'diploma ya da mezuniyet belgesi (e-Devlet\'ten alınan barkodlu belge çoğu yerde kabul edilir),',
                    'nüfus cüzdanı fotokopisi ve vesikalık fotoğraf,',
                    'ilanda istenmişse sürücü belgesi, sertifika, SGK hizmet dökümü, yabancı dil belgesi,',
                    'kurumun başvuru formu (imzalı).'])]),
      ('Sık yapılan hatalar', [
         ('madde', ['Son güne bırakmak: e-Devlet ve Kariyer Kapısı son gün yoğunlaşır; postayla başvuruda gecikme kabul edilmez.',
                    'Yanlış puan türü ya da yanlış yılın puanı ile başvurmak.',
                    'Bölüm şartını karşılamadığı halde başvurmak: başvuru sonradan iptal edilir.',
                    'Birden fazla kadroya başvurulamayan ilanda iki kadro seçmek.',
                    'Duyuruları takip etmemek: sınav yeri, tarih ve sonuçlar çoğu zaman yalnız kurumun sitesinde ilan edilir.'])]),
      ('Başvurudan sonra', [
         'Başvuru özetini ve belgelerin kopyasını sakla. Kariyer Kapısı\'nda "Başvurularım" bölümünden durumunu izleyebilirsin. Düzeltme '
         've iptal duyuruları da yayımlanabilir; KPSS Tercihi ilan sayfalarında bu duyuruları ayrıca gösterir.'])],
     [('Kariyer Kapısı rehberi', 'rehber/kariyer-kapisi-basvuru/'), ('Açık ilanlar', '#ilanlar')]),

    ('kariyer-kapisi-basvuru', 'Kariyer Kapısı ile kamu ilanına başvuru nasıl yapılır?',
     'e-Devlet Kariyer Kapısı Kamu İşe Alım Platformu\'nda ilan arama, özgeçmiş, başvuru ve sonuç takibi adımları.',
     'Kariyer Kapısı, Cumhurbaşkanlığı İnsan Kaynakları Ofisi\'nin kamu işe alım platformudur. Birçok kurum ilanını burada yayımlar '
     've başvuruları e-Devlet şifresiyle buradan alır.',
     [('1. Giriş ve özgeçmiş', [
         'kariyerkapisi.gov.tr adresinden e-Devlet ile giriş yap. Eğitim, KPSS ve iletişim bilgilerinin büyük kısmı e-Devlet\'ten '
         'otomatik gelir; eksik ya da hatalı bilgi varsa başvurudan önce düzelt.']),
      ('2. İlanı bul ve şartları kontrol et', [
         'İlan sayfasında kadrolar, nitelikler, belge listesi ve tarihler yer alır. KPSS Tercihi\'nde her ilanın kadro kadro koşullarını '
         've resmî ilan bağlantısını görebilirsin.']),
      ('3. Başvuruyu tamamla', [
         ('madde', ['İstenen belgeleri PDF olarak yükle,', 'tercih edilecek kadroyu/kadroları seç,',
                    'beyanları onayla ve başvuruyu "tamamla" adımına kadar götür; tamamlanmayan başvuru geçersizdir.'])]),
      ('4. Sonucu takip et', [
         'Başvurularım bölümünde başvurunun durumu görünür. Sınava çağrı ve sonuç duyuruları ilanda belirtilen yerde (çoğu zaman kurumun '
         'internet sitesinde ve Kariyer Kapısı\'nda) yayımlanır.'])],
     [('Başvuru belgeleri ve hatalar', 'rehber/basvuru-belgeleri-ve-hatalar/'), ('Açık ilanlar', '#ilanlar')]),
]

NOT = ('Bu yazı genel bilgi amaçlıdır; kurallar ilandan ilana ve zamanla değişebilir. Başvurmadan önce her zaman ilanın resmî '
       'metnini ve ilgili mevzuatı esas al.')


def _paragraf(p, esc):
    if isinstance(p, tuple) and p[0] == 'madde':
        return '<ul>' + ''.join(f'<li>{esc(m)}</li>' for m in p[1]) + '</ul>'
    return f'<p>{esc(p)}</p>'


def sayfa(r, base):
    import site_uret as su
    slug, baslik, aciklama, giris, bolumler, ilgili = r
    canonical = f'{base}rehber/{slug}/'
    kok = '../../'
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': baslik, 'description': aciklama,
          'inLanguage': 'tr', 'datePublished': GUNCELLEME, 'dateModified': '2026-10-24' if slug in ('kpss-ile-memur-olmak', 'kpss-puan-turleri') else GUNCELLEME, 'mainEntityOfPage': canonical,
          'author': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base},
          'publisher': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}}
    govde = ''.join(f'<section class="bolum"><h2>{su.esc(h)}</h2>' + ''.join(_paragraf(p, su.esc) for p in ps) + '</section>'
                    for h, ps in bolumler)
    bag = ''.join(f'<li><a href="{kok}{su.esc(y)}">{su.esc(a)}</a></li>' for a, y in ilgili)
    govde += (f'<section class="bolum"><h2>İlgili sayfalar</h2><ul>{bag}<li><a href="../">Tüm rehberler</a></li></ul></section>'
              f'<p class="kp-note">{su.esc(NOT)}</p>')
    html = (su.sayfa_basi(f'{baslik} | KPSS Tercihi', aciklama, su.esc(canonical), kok, 'article',
                          ek_head=f'<meta property="og:url" content="{su.esc(canonical)}"><script type="application/ld+json">'
                                  + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>')
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok)}'
            + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../../">Ana sayfa</a>'
              '<span aria-hidden="true">/</span><a href="../">Rehberler</a></nav>'
            + f'<span class="eyebrow">Rehber</span><h1>{su.esc(baslik)}</h1><p>{su.esc(giris)}</p></div></section>'
            + f'<main id="icerik" class="wrap kp-main"><article>{govde}</article></main>{su.alt_html(kok)}</body></html>')
    return canonical, html


def hub(base):
    import site_uret as su
    import uygulamali_rehberler as ur
    canonical = f'{base}rehber/'
    kok = '../'
    kartlar = ''.join(f'<li><a href="{su.esc(r[0])}/"><b>{su.esc(r[1])}</b></a><p class="muted">{su.esc(r[2])}</p></li>' for r in REHBERLER)
    aciklama = 'KPSS ile memur olmak, puan türleri, belediye ve işçi alımları, 4/B, bilişim personeli ve başvuru belgeleri üzerine sade rehberler.'
    html = (su.sayfa_basi('KPSS ve kamu ilanları rehberleri | KPSS Tercihi', aciklama, su.esc(canonical), kok,
                          ek_head=f'<meta property="og:url" content="{su.esc(canonical)}"><link rel="stylesheet" href="../rehber.css?v=1">')
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok)}'
            + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../">Ana sayfa</a>'
              '<span aria-hidden="true">/</span><span>Rehberler</span></nav><span class="eyebrow">Rehber</span>'
              '<h1>KPSS ve kamu ilanları rehberleri</h1><p>Başvurudan atamaya kadar en çok merak edilen konular, sade ve kalıcı yazılar.</p></div></section>'
            + f'<main id="icerik" class="wrap kp-main">{ur.kartlar()}<section class="bolum"><ul class="rehber-liste">{kartlar}</ul></section>'
              f'<p class="kp-note">{su.esc(NOT)}</p></main>{su.alt_html(kok)}</body></html>')
    return canonical, html


def yaz(docs, base):
    """Rehber sayfalarını yazar; site haritası için adresleri döner."""
    from pathlib import Path
    docs = Path(docs)
    adresler = []
    url, html = hub(base)
    (docs / 'rehber').mkdir(parents=True, exist_ok=True)
    (docs / 'rehber' / 'index.html').write_text(html, encoding='utf-8')
    adresler.append(url)
    for r in REHBERLER:
        url, html = sayfa(r, base)
        (docs / 'rehber' / r[0]).mkdir(parents=True, exist_ok=True)
        (docs / 'rehber' / r[0] / 'index.html').write_text(html, encoding='utf-8')
        adresler.append(url)
    import uygulamali_rehberler as ur
    adresler.extend(ur.yaz(docs, base))
    return adresler
