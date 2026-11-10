"""Rehber yazıları: /rehber/ ve /rehber/<slug>/ (19 Ekim 2026; 1 Kasım 2026'da genişletildi).

KPSS adaylarının en sık sorduğu konularda kalıcı, özgün yazılar. Her yazı mevzuata (657 sayılı Kanun, Genel Yönetmelik, Sözleşmeli
Personel Esasları, işçi alımı yönetmeliği, ÖSYM kılavuzları) dayanır; hesaplı örnekler "örnek" diye işaretlidir ve kurgudur.
Her yazının sonunda resmî ilanın esas olduğu hatırlatılır. Metinler sitenin dilinde (sen diye hitap, sade) yazıldı.
Bazı yazıların sonuna, o konuyla eşleşen ve başvurusu açık ilanlar derleme sırasında eklenir (acik_ilanlar)."""
import json
import re
from datetime import datetime

YAYIN = '2026-10-19'
GUNCELLEME = '2026-11-01'

# (slug, başlık, açıklama, giriş, [(ara başlık, [paragraf | ('madde', [maddeler])])], [(ilgili bağlantı adı, göreli yol)])
REHBERLER = [
    ('kpss-ile-memur-olmak', 'KPSS ile memur olmak: adım adım yol haritası',
     'KPSS puanından atamaya kadar süreç: A ve B grubu kadrolar, puanın geçerliliği, tercih, evrak ve aday memurluk.',
     'KPSS puanı memur olmanın ilk şartıdır, tek şartı değildir. Puan seni kapının önüne getirir. Kapıdan geçmek için doğru yolu '
     'seçmen, ilanın şartlarını taşıman ve evrak aşamasını hatasız tamamlaman gerekir. Aşağıda süreç sırasıyla anlatılıyor.',
     [('Süreç bir bakışta', [
         ('madde', ['Mezuniyet durumuna göre KPSS düzeyini (lisans, önlisans, ortaöğretim) seç ve sınava gir.',
                    'Sonuçlar açıklanınca puanın iki yıl geçerli olur. Bu süre içinde yerleştirme ve ilan dönemlerini kullan.',
                    'ÖSYM tercih kılavuzu yayımlanınca kadroları nitelik koduyla tek tek kontrol et; en fazla 30 tercih yaz.',
                    'Yerleştirilirsen kuruma belgelerinle süresi içinde başvur. Kurum ilanı varsa onun şartlarını ayrıca izle.',
                    'Atama öncesi beyanını ver, atama sonrası aday memurluk sürecini tamamla.'])]),
      ('Önce kadronun hangi grupta olduğuna bak', [
         'Genel Yönetmelik memur kadrolarını ikiye ayırır. A grubu; müfettiş yardımcılığı, uzman yardımcılığı, denetmen yardımcılığı '
         'gibi özel yarışma sınavıyla girilen mesleklerdir. B grubu ise bunların dışında kalan, ilanlarda en sık gördüğün memur '
         'kadrolarıdır: memur, zabıta memuru, tekniker, teknisyen gibi.',
         'A grubunda kurum ya doğrudan KPSS puanına göre atama yapar ya da KPSS’de belli bir puanı geçenleri kendi giriş sınavına '
         'çağırır. Çağrılacak aday sayısı, atama izni alınan kadro sayısının 20 katını geçemez. B grubunda yol, ÖSYM’nin merkezi '
         'yerleştirmesi ya da kurumun kendi ilanıdır. İkisini ayrı bir rehberde karşılaştırdık.']),
      ('Geçerli puan ve doğru öğrenim düzeyi', [
         'Kamuya ilk kez atanacak herkesin geçerli bir KPSS puanı olması gerekir. ÖSYM kılavuzlarına göre sonuçlar, açıklanmasından '
         'itibaren iki yıl geçerlidir. Hangi sınavın puanının kabul edildiğini her yerleştirme kılavuzu ve her ilan ayrıca yazar; '
         'tarihi kendi kafandan hesaplayıp güvenme.',
         'KPSS lisans, önlisans ve ortaöğretim düzeylerinde yapılır ve birden fazla düzeyde sınava giremezsin. Lisans diplomanı '
         'aldıysan lisans düzeyinden girmek zorundasın. Yüksek lisans ya da doktora yaptıysan başvuruyu lisans diplomanın alanı '
         'üzerinden yaparsın.',
         'Bir kural çoğu adayın gözünden kaçar: ortaöğretim ya da önlisans düzeyinden girip sonra lisans sınavına katılırsan, '
         'lisans sonucu açıklandığı anda eski düzeydeki sonucun geçerliliği biter. Elindeki puana güveniyorsan lisans sınavına '
         'girmeden önce bunu hesaba kat.']),
      ('Hangi puan hangi kadroda?', [
         'B grubu kadrolarda lisans için KPSSP3, önlisans için KPSSP93, ortaöğretim için KPSSP94 kullanılır. ÖSYM kılavuzları, '
         'Genel Yönetmelik kapsamı dışındaki kurumların da B grubu kadrolu ve sözleşmeli alımlarında bu üç türü kullanacağını yazar. '
         'A grubunda ise ilan, aranan puan türünü tek tek sayar. Ayrıntı için puan türleri rehberine bak.',
         'Puanın yetip yetmeyeceğini anlamak için geçmiş yerleştirmelerde aynı unvana hangi puanla yerleşildiğine bakabilirsin. '
         'Bu bir garanti değildir: kontenjan ve başvuran sayısı her dönem değişir. Karşılaştırma için taban puan sayfalarını ve '
         'il il, kadro kadro analizleri kullan.']),
      ('Merkezi yerleştirmede tercih nasıl yapılır?', [
         'ÖSYM, kurumların atama izni almış boş kadrolarını tercih kılavuzunda yayımlar. Kılavuzdaki kadro kodlarından en fazla 30 '
         'tanesini kendi istek sırana göre internetten bildirirsin. Tercih süresi bitene kadar listeni değiştirebilirsin. Süre '
         'bittikten sonra değişiklik yapılamaz ve kılavuz, sürenin uzatılmayacağını açıkça yazar.',
         'Tercihin geçerli olması için yerleştirme ücretini de zamanında ödemelisin. Tutarı ve son ödeme saatini her dönemin '
         'kılavuzu yazar. Ücreti yatırmayan adayın tercihleri silinir ve yerleştirmeye alınmaz. Şehit ve gazi yakınları için '
         'kılavuzda ücret muafiyeti bulunur.',
         'Yerleştirme sonucu çıkınca iş bitmez. Yerleştiğin kuruma, kılavuzda yazan belgelerle ve süresi içinde başvurman gerekir. '
         'Kurumda kurulan beş kişilik komisyon nitelikleri inceler. Şartı taşımıyorsan yerleşmiş olsan bile atama yapılmaz.']),
      ('Kurum ne kadar şart koyabilir?', [
         'Merkezi yerleştirmede kurum, Nitelik-Kod Kılavuzunda yer alanların dışında özel nitelik belirleyemez. Yani ilandaki bölüm, '
         'sertifika ya da belge şartı kılavuzdaki kodlarla sınırlıdır. Ayrıca kurumlar, kanunlarda ya da bunların yetkilendirdiği '
         'düzenlemelerde özel hüküm olmadıkça merkezi yerleştirme için yaş sınırı koyamaz.',
         'Bir kadrodaki bölüm, sertifika ya da belge şartı nitelik kodundan gelir. Kodu çözmek, hangi kadroların sana açık '
         'olduğunu tercih yapmadan önce gösterir.']),
      ('Genel yerleştirme ve ek yerleştirme', [
         'Genel yerleştirme sonunda boş kalan kadrolar için kurumlar ek yerleştirme isteyebilir. Genel yerleştirmede bir kadroya '
         'yerleşen aday ek yerleştirmeye başvuramaz. Genel yerleştirmede bir yere yerleşemediysen ek yerleştirme duyurularını '
         'izlemeye devam et; ek yerleştirme de genel yerleştirmeyle aynı usulle yapılır.',
         'Tercih formunda ya da başvuru belgesinde yanlış kodladığın, hiç kodlamadığın ya da tutarsız yazdığın bilgiler yüzünden '
         'yerleşemezsen ya da daha alt tercihine yerleşirsen bundan dolayı hak iddia edemezsin.']),
      ('Aynı puanı iki kez kullanamazsın', [
         'Genel Yönetmeliğin ek 2. maddesine göre merkezi yerleştirmeyle bir B grubu kadroya yerleşen aday, yerleşmesine esas olan '
         'puanla sonraki alımlara başvuramaz. ÖSYM bunu son kılavuzlarında “atamaları yapılsın ya da yapılmasın” diye ayrıca vurgular.',
         'Örnek (kurgu): Deniz, 2024 KPSS puanıyla bir yerleştirmede kadroya yerleşti ama göreve başlamaktan vazgeçti. Sonraki '
         'yerleştirmede aynı 2024 puanıyla tercih yapamaz; yeni bir KPSS sonucu almak zorundadır. Bu yüzden “nasılsa vazgeçerim” '
         'diye şartını taşımadığın kadrolara tercih yazma.']),
      ('Atama öncesi beyan ve aday memurluk', [
         'Atama işleminden önce kurum senden kimlik, adli sicil, askerlik ve sağlık durumuna dair yazılı beyan alır ve bu konularda '
         'beyanın dışında ayrıca belge istemez. Beyanların doğruluğu sonradan kontrol edilir. Gerçeğe aykırı belge ya da beyan '
         'verirsen atama yapılmaz, yapılmışsa iptal edilir ve ceza hükümleri işletilir.',
         'Memurluk için aranan genel şartlar 657 sayılı Kanunun 48. maddesindedir: Türk vatandaşı olmak, yaş ve öğrenim şartlarını '
         'taşımak, kamu haklarından mahrum olmamak, sayılan suçlardan mahkûm olmamak, askerlik durumu uygun olmak ve görevini '
         'sürekli yapmana engel bir akıl hastalığı bulunmamak.',
         'İlk kez atanan kişi aday memur olur. Adaylık süresi bir yıldan az, iki yıldan çok olamaz ve bu sürede başka kuruma nakil '
         'yapılamaz. Aday memurlar önce bütün memurlar için ortak temel eğitime, sonra sınıflarına özgü hazırlayıcı eğitime alınır.']),
      ('Başvuruda en sık yapılan hatalar', [
         ('madde', ['Mezun olmadan tercih yapmak. Tercihin ÖSYM’ye gönderildiği gün sınava girdiğin düzeyde mezun olmalısın; '
                    'değilsen yerleşsen bile atanmazsın.',
                    'Nitelik kodunu okumadan kadro seçmek. Bölüm, sertifika ya da belge şartını taşımıyorsan atama yapılmaz, '
                    'ama yerleştirildiğin için puanın yine de kullanılmış sayılır.',
                    'Tercih hakkını boş bırakmak. Yerleştirme istek sırana göre yapılır; şartlarını taşıdığın kadroları listene '
                    'eklemek şansını artırır.',
                    'Süresi dolmuş sonuçla başvurmak. İlan hangi sınavın sonucunu kabul ediyorsa onu kullan.',
                    'Tercih ve ücret ödeme son günlerini kaçırmak. Bu süreler uzatılmaz.'])])],
     [('Puan türleri rehberi', 'rehber/kpss-puan-turleri/'),
      ('Merkezi yerleştirme ve kurum ilanları', 'rehber/merkezi-yerlestirme-ve-kurum-ilanlari/'),
      ('Nitelik kodlarını kontrol et', 'rehber/kpss-nitelik-kodu-nasil-okunur/'),
      ('Tercih listesini sırala', 'rehber/kpss-tercih-listesi-nasil-siralanir/'),
      ('KPSS taban puanları', 'kpss-taban-puanlari/'), ('Tercih robotu', 'puanlar/'), ('Açık ilanlar', '#ilanlar')]),

    ('kpss-puan-turleri', 'KPSS puan türleri: P3, P93, P94 ve diğerleri ne anlama gelir?',
     'KPSS puanı nasıl hesaplanır, P1, P2, P3, P93, P94 ve A grubu puan türleri ne ifade eder, hangi kurum hangisini kullanır?',
     'İlanda “KPSSP3” ya da “KPSSP94” yazıyorsa kurum, başvuruları o puan türüne göre sıralayacak demektir. Türü yanlış okursan '
     'elindeki puan işe yaramaz. Bu rehber, puanın nasıl hesaplandığını ve hangi türün nerede kullanıldığını ÖSYM kılavuzlarına '
     'dayanarak anlatır.',
     [('Puan nasıl hesaplanıyor?', [
         'Her testte doğru sayısından yanlış sayısının dörtte biri çıkarılır; kalan sayı netindir. Netten, testin ortalaması ve '
         'standart sapması kullanılarak standart puan bulunur. KPSS puan türleri, bu standart puanların farklı ağırlıklarla '
         'toplanmasından çıkar.',
         'Bir puan türünün hesaplanması için ilgili her testte en az bir net yapmış olman gerekir. Genel yetenek testini boş '
         'bırakan birinin P3 puanı olmaz.',
         'Örnek (varsayımsal): Bir testte 40 doğru ve 12 yanlış yaptıysan netin 40 − 12/4 = 37 olur. Boş bıraktığın soru neti '
         'etkilemez, ama her yanlış cevap bir doğrunun dörtte birini götürür. Bu yüzden emin olmadığın sorularda tahmin riskini '
         'hesaplamak sınav stratejisinin parçasıdır.']),
      ('Hangi sınava girmelisin: A grubu mu, B grubu mu?', [
         'Lisans düzeyindeki KPSS iki parçalıdır. B grubu kadrolar için genel yetenek-genel kültür oturumu yeterlidir. A grubu '
         'kadrolar için bu oturuma ek olarak alan bilgisi oturumlarına da girersin. Kılavuz, hangi alan oturumlarına gireceğine '
         'adayın kendisinin karar vereceğini söyler ve kararı vermeden önce puan türleri tablosunu incelemeni önerir.',
         'İlk atama için A ya da B grubu fark etmeksizin geçerli bir KPSS puanı zorunludur. Önceki yıl sınava girmiş ve A grubu '
         'kadrolar için puanını yükseltmek istiyorsan, yeni dönem sınavına yeniden girebilirsin. Kılavuz bu hakkı açıkça tanır.']),
      ('Genel yetenek ve genel kültür puanları', [
         'Lisans düzeyinde üç ayrı genel yetenek-genel kültür puanı hesaplanır. Önlisans ve ortaöğretimde Diyanet’e özgü DHBT '
         'puanları dışında birer tane vardır.',
         ('madde', ['KPSSP3 (lisans): genel yetenek 0,50, genel kültür 0,50. Lisans memur alımlarında en sık göreceğin tür.',
                    'KPSSP1 (lisans): genel yetenek 0,70, genel kültür 0,30. Genel yeteneğin güçlüyse P3’ten yüksek çıkabilir.',
                    'KPSSP2 (lisans): genel yetenek 0,60, genel kültür 0,40.',
                    'KPSSP93 (önlisans): iki test de 0,50.',
                    'KPSSP94 (ortaöğretim): iki test de 0,50.']),
         'P1 ve P2, A grubu puanı değildir; lisans sınavında hesaplanan genel yetenek-genel kültür puanlarıdır. Bazı kurumlar '
         'ilanında bunları ister. İŞKUR’un kamu işçi alımı bilgi sayfası da lisans düzeyinde kurumun P1, P2 ya da P3’ten birini '
         'belirleyebildiğini söyler.']),
      ('Hangi kurum hangi türü kullanır?', [
         'ÖSYM’nin merkezi yerleştirmesinde ortaöğretim mezunları KPSSP94, önlisans mezunları KPSSP93, lisans mezunları KPSSP3 '
         'ile yarışır. Genel Yönetmelik kapsamında olmayıp kendi sınavını yapan kurumların da B grubu kadrolu ve sözleşmeli '
         'alımlarında aynı üç türü kullanacağı ÖSYM kılavuzlarında yazar.',
         'Türü kurum seçer, sen seçmezsin. İlanda birden fazla tür sayılmışsa hangisinin esas alınacağı ilan metninde yazar. '
         'Yazmıyorsa varsayım yapma, kuruma sor.']),
      ('A grubu ve alan bilgisi puanları', [
         'Müfettiş, uzman ve denetmen yardımcılığı gibi A grubu kadrolar için ÖSYM ayrıca alan bilgisi oturumları yapar. Bu '
         'testler hukuk, iktisat, işletme, maliye, muhasebe, çalışma ekonomisi ve endüstri ilişkileri, istatistik, kamu yönetimi '
         've uluslararası ilişkiler alanlarındadır. Her alan testi genel yetenek ve genel kültürle farklı ağırlıklarda birleşir; '
         'böylece P4’ten P48’e uzanan çok sayıda puan türü oluşur.',
         'Örneğin P4’te genel yetenek 0,20, genel kültür 0,20, hukuk testi 0,60 ağırlıktadır. P48 de gerçek bir puan türüdür; '
         'ağırlıkları kılavuzdaki tabloda yer alır. Numaralar ardışık gitmez, bazı numaralar tabloda hiç bulunmaz. İlan hangi '
         'numarayı istiyorsa o numaraya bak.',
         'Diyanet’te din hizmetleri kadroları için hesaplanan P122, P123 ve P124 puanları ise DHBT sonuç bilgisinin içinde yer alır.']),
      ('Örnek: ağırlık sıralamayı değiştirir', [
         'Örnek (varsayımsal): Ayşe’nin genel yetenek standart puanı 70, genel kültür standart puanı 50 olsun. P1 ağırlıklarıyla '
         '0,70×70 + 0,30×50 = 64 çıkar. P3 ağırlıklarıyla 0,50×70 + 0,50×50 = 60 çıkar.',
         'Can’ın puanları tersi olsun: genel yetenek 50, genel kültür 70. Can’ın P1’i 56, P3’ü 60 olur. İlan P1 isterse Ayşe öne '
         'geçer, P3 isterse ikisi eşitlenir. Gerçek puanlar ÖSYM’nin kendi ölçeğiyle hesaplanır; örnek yalnızca ağırlığın '
         'etkisini göstermek içindir.']),
      ('İlanı okurken dikkat edeceklerin', [
         ('madde', ['Asgari puan başvuru şartıdır, sıralama ise başvuranlar arasında yapılır. KPSS’de yüksek puan almak tek '
                    'başına bir hak doğurmaz.',
                    'Sonuçlar açıklandıktan sonra iki yıl geçerlidir. Hangi sınavın puanının kabul edildiğini ilan yazar.',
                    'Önlisans ya da ortaöğretim puanın, sonradan lisans sınavına girersen geçerliliğini yitirebilir.',
                    'Kurumlar kimlik numarasını, adı ve puanını ÖSYM’nin sitesinden doğrular. Belgede oynama yapıldığı '
                    'anlaşılırsa durum ÖSYM’ye bildirilir ve sonuç iptal edilir.',
                    'Yüksek lisans ya da doktoran olsa da başvuruyu lisans diplomanın alanı üzerinden yaparsın.'])]),
      ('Taban puanlarıyla karşılaştırırken', [
         'Taban puanları yalnızca aynı puan türü içinde karşılaştırılır. Lisans kadrosunun P3 ile oluşan taban puanını P93 ya da '
         'P94’ün tabanıyla yan yana koyman anlamsızdır; farklı sınavlardan çıkan farklı ölçeklerdir. Kadro puan sıralaması ve '
         'il il analiz sayfalarında bu yüzden öğrenim düzeyi ayrı gösterilir. Kendi puanını her zaman kadronun öğrenim düzeyine '
         'denk gelen türle karşılaştır.']),
      ('Öğretmenlik için not', [
         'Millî Eğitim Bakanlığında istihdam edilen öğretmenler, Genel Yönetmeliğin kapsamı dışında tutulmuştur. Öğretmenlik '
         'başvurularında ilgili dönemin MEB ve ÖSYM duyurularındaki sınav, puan ve başvuru koşullarını ayrıca incele.'])],
     [('Taban puanını yorumla', 'rehber/kpss-taban-puani-nasil-yorumlanir/'), ('KPSS ile memur olmak', 'rehber/kpss-ile-memur-olmak/'),
      ('Tercih robotu', 'puanlar/'), ('Kadro puan sıralaması', 'analiz/kadro-puan-siralamasi/'),
      ('KPSS taban puanları', 'kpss-taban-puanlari/')]),

    ('merkezi-yerlestirme-ve-kurum-ilanlari', 'Merkezi yerleştirme ile kurum ilanları arasındaki fark',
     'ÖSYM merkezi yerleştirmesi ile kurumların kendi ilanları nasıl işler? Başvuru, sıralama, sınav ve puan kullanımı farkları.',
     'KPSS ile atanmanın iki ana yolu aynı puana dayanır ama farklı kurallarla işler. Birinde ÖSYM seni bir kadroya yerleştirir. '
     'Diğerinde kurum kendi ilanını açar, kendi sıralamasını ya da sınavını yapar. Hangisine hazırlandığını bilmezsen zaman ve '
     'şans kaybedersin.',
     [('Merkezi yerleştirme adım adım', [
         ('madde', ['Kurum boş kadrosu için atama izni alır ve kadronun koşullarını, onaylı Nitelik-Kod Kılavuzuna göre bildirir. '
                    'Kurum bu kılavuzdaki nitelik kodlarının dışında ayrıca özel şart koyamaz.',
                    'ÖSYM tercih kılavuzunu yayımlar. Kadrolar sınıf, unvan, derece, sayı ve nitelik kodlarıyla listelenir.',
                    'Sen en fazla 30 kadro kodunu istek sırana göre internetten bildirirsin. Tercih aşamasında senden belge istenmez; '
                    'yerleştirmede beyanların esas alınır.',
                    'ÖSYM seni puanına ve tercih sırana göre yerleştirir. Bu aşamada kurum sınavı yoktur.',
                    'Yerleştiğin kuruma, kılavuzda yazan belgelerle ve verilen süre içinde başvurursun. Kurumun beş kişilik '
                    'komisyonu nitelikleri denetler ve uygun olanların atamasını önerir.']),
         'Genel Yönetmelik, her yıl Ocak ayında bir yerleştirme takvimi belirlenip ilan edilmesini öngörür. Tercih dönemlerini '
         'bu takvimden ve ÖSYM duyurularından izle.']),
      ('Kurum ilanı tek bir kural değildir', [
         'Kurum ilanı dediğimiz şeyin arkasında farklı mevzuatlar var. Hangi mevzuata dayandığına göre işleyiş değişir.',
         ('madde', ['Belediyeler, il özel idareleri ve bağlı kuruluşlar: B grubu kadrolarını ÖSYM yerleştirmesiyle ya da KPSS (B) '
                    'sıralamasında kadro sayısının beş katına kadar aday arasında yapacakları yazılı ve/veya sözlü sınavla '
                    'doldurabilir.',
                    'Sözleşmeli personel (657 sayılı Kanun md. 4/B): kurum; ÖSYM yerleştirmesi, sınavsız KPSS sıralaması ya da '
                    'pozisyon sayısının on katına kadar aday arasında yazılı/sözlü sınav yöntemlerinden birini seçer. Bazı '
                    'unvanlarda sınav hiç aranmaz.',
                    'A grubu kadrolar: kurum ya doğrudan atar ya da KPSS puanına göre çağırdığı adaylarla giriş sınavı yapar. '
                    'Çağrılan sayı kadro sayısının 20 katını geçemez.',
                    'İşçi alımı: İŞKUR aracılığıyla yapılır. Önlisans ve lisans düzeyinde KPSS puanı, diğer düzeylerde noter '
                    'kurası kullanılır.'])]),
      ('İkisi yan yana', [
         ('madde', ['Başvuru yeri: merkezi yerleştirmede ÖSYM’nin aday işlemleri sistemi. Kurum ilanında ilanın yazdığı yer: '
                    'Kariyer Kapısı, İŞKUR ya da kurumun kendi sistemi.',
                    'Sıralama: merkezi yerleştirmede puan ve tercih sırası. Kurum ilanında puan sırası, sınav başarısı ya da kura.',
                    'Zamanlama: merkezi yerleştirme ÖSYM’nin açıkladığı tercih döneminde yapılır. Kurum ilanı kurumun ihtiyacına '
                    'göre her zaman çıkabilir ve başvuru süresi kısa olabilir.',
                    'Elenme riski: merkezi yerleştirmede en büyük risk nitelik şartını yanlış okumaktır. Kurum ilanında sınav '
                    've belge aşamaları da vardır.',
                    'Puan tüketimi: merkezi yerleştirmeyle B grubu bir kadroya yerleşirsen o puanla sonraki alımlara başvuramazsın.'])]),
      ('Kurum ilanında puanın doğrulanması', [
         'Kurumlar başvuran adayların T.C. kimlik numarasını, adını, soyadını ve KPSS puanını ÖSYM’nin internet sitesinden '
         'kontrol eder. Belgede silinti, kazıntı ya da teknolojiyle değişiklik yapıldığı anlaşılırsa durum ÖSYM’ye bildirilir ve '
         'sorumlular hakkında savcılığa suç duyurusunda bulunulur. Başvuruda verdiğin bilgiler ÖSYM kaydıyla birebir tutmalı.']),
      ('Örnek: aynı puan, iki ayrı kapı', [
         'Örnek (kurgu): Bir belediye 3 zabıta memuru için kendi sınavını yapacağını duyurdu. KPSS sıralamasında en yüksek '
         'puandan başlanarak en çok 15 aday sınava çağrılabilir; bu, kadro sayısının beş katıdır. Aynı dönemde ÖSYM tercih '
         'kılavuzunda da zabıta memuru kadroları var.',
         'Belediye sıralamasında 16. olduysan sınava hiç çağrılmazsın. ÖSYM tarafında ise puanın kadronun geçmiş taban puanını '
         'geçiyorsa yerleşebilirsin. İkisi birbirinin yerine geçmez; ikisine de başvurabilirsin. Yalnız merkezi yerleştirmede bir '
         'kadroya yerleşirsen o puanla sonraki alımlara başvuramayacağını sıralamayı planlarken unutma.']),
      ('Hangisine ağırlık vermelisin?', [
         ('madde', ['Puanın geçmiş taban puanların üstündeyse ve ilgili unvanda geniş kadro varsa merkezi yerleştirmeyi öne al. '
                    'Sınav stresi yoktur ama tercih hatası affedilmez.',
                    'Puanın orta seviyedeyse kurum ilanlarını da yakından izle. Sınava çağrı sınırı yüksek tutulduğunda (örneğin '
                    'kadronun on katı) orta puanlı adaylar da sınava girer ve sınavda öne geçme şansı bulur.',
                    'Yaşayacağın yer önemliyse kurum ilanları işine yarayabilir: belediye ya da üniversite ilanı belirli bir '
                    'yere yönelik olur.',
                    'İkisini birlikte yürüt, ama merkezi yerleştirmede yerleşirsen o puanla sonraki alımlara başvuramayacağını '
                    'hesaba kat.'])]),
      ('Kurum ilanlarında duyuruyu nereden izlersin?', [
         'Sözleşmeli personel alımlarında kurum, pozisyon sayısını, nitelikleri, yerleştirme usulünü ve sınavın yer, tarih ve '
         'konularını en az on beş gün önce ilan eder. Belediyeler sınav ilanını Resmî Gazete’de, Cumhurbaşkanlığınca belirlenen '
         'kurumun internet sitesinde ve kendi sitelerinde duyurur. İşçi alımında sınav bilgisi kurumun sitesinde yayımlanır ve '
         'bu duyuru tebligat yerine geçer.',
         'İşçi alımında duyuru tebligat yerine geçtiği için sana ayrıca yazı gelmez. Diğer kurum ilanlarında da en güvenli yol, '
         'başvurduğun kurumun sitesini sınav tarihine kadar düzenli aralıklarla kontrol etmektir.']),
      ('Geçmiş taban puanlarını doğru kullan', [
         'KPSS Tercihi’ndeki taban puan sayfaları, ÖSYM’nin yerleştirme sonrasında yayımladığı sayısal bilgilerden derlenir. Bir '
         'kadroya geçmişte hangi en küçük ve en büyük puanla yerleşildiğini gösterir. Bunlar yön gösterir ama söz vermez. '
         'Kontenjan, başvuran sayısı ve puan dağılımı her dönem farklıdır.',
         'Kurum ilanlarında geçmiş taban puanı çoğu zaman yoktur; belirleyici olan ilanın kendi şartları, sınavı ve çağrılan aday '
         'sayısıdır. Yine de aynı unvanın merkezi yerleştirmedeki puanları, rekabetin seviyesi için fikir verir.'])],
     [('KPSS taban puanları', 'kpss-taban-puanlari/'), ('Tercih robotu', 'puanlar/'),
      ('İl il taban puanları', 'analiz/il-il-taban-puanlari/'), ('Kadro puan sıralaması', 'analiz/kadro-puan-siralamasi/'),
      ('Kamu ilanı istatistikleri', 'analiz/kamu-ilan-istatistikleri/'), ('Açık ilanlar', '#ilanlar')]),

    ('belediye-memur-alimi', 'Belediye memur alımları nasıl yapılır?',
     'Belediyelerin memur, sözleşmeli ve işçi alımları: KPSS sıralaması, kadro sayısının beş katı sınav kuralı, şartlar ve ilan okuma.',
     'Belediyeler zabıta memuru, itfaiye eri, tekniker, mühendis gibi kadrolara çoğunlukla kendi ilanlarıyla alım yapar. İlanlar '
     'küçük kontenjanlıdır ve başvuru süresi kısa olabilir. Önce belediyedeki üç statüyü ayırıyor, sonra memur alımının nasıl '
     'yürüdüğünü adım adım anlatıyoruz.',
     [('Belediyede üç ayrı statü var', [
         ('madde', ['Memur: norm kadroya göre ihdas edilmiş kadrolara KPSS ile atanır. Bu yazının ana konusu budur.',
                    'Sözleşmeli personel: 5393 sayılı Belediye Kanununun 49. maddesine göre avukat, mimar, mühendis, şehir plancısı, '
                    'tabip, uzman tabip, ebe, hemşire, veteriner, kimyager, teknisyen ve tekniker gibi uzman ve teknik personel '
                    'yıllık sözleşmeyle çalıştırılabilir.',
                    'İşçi: İŞKUR aracılığıyla, kamu işçi alımı kurallarına göre alınır. Belediyeler ve bağlı kuruluşları bu '
                    'yönetmeliğin kapsamındadır.'])]),
      ('Memur alımı nasıl yapılır?', [
         'Belediyenin B grubu kadroları için Genel Yönetmelik iki yol tanır. Belediye kadrosunu ÖSYM’nin merkezi yerleştirmesine '
         'bildirebilir; bu durumda kadroyu ÖSYM tercih kılavuzunda görürsün. Ya da belediye kendi ilanını verir: KPSS (B) grubu '
         'puan sıralamasında en üstten başlayarak, açıktan atama yapılacak kadro sayısının beş katına kadar aday yazılı ve/veya '
         'sözlü sınava çağrılır. Atama bu sınavdaki başarı sırasına göre yapılır.',
         'Sınav türü, konular, sınav kurulunun işleyişi, asıl ve yedek adayların belirlenmesi ve itiraz usulü, ilgili bakanlıkların '
         'birlikte çıkardığı yönetmelikle düzenlenir. Senin için pratik kaynak, belediyenin ilan metnidir.',
         'İlan; kadro sayısını, sınıf ve unvanı, atama koşullarını, KPSS puan türünü ve asgari puanı, sınavın yerini, zamanını, '
         'içeriğini ve değerlendirme yöntemini içerir. Belediye bunu Resmî Gazete’de, Cumhurbaşkanlığınca belirlenen kurumun '
         'internet sitesinde ve kendi internet sitesinde duyurur.']),
      ('Genel şartlar', [
         '657 sayılı Kanunun 48. maddesi memurluk için şu genel şartları arar:',
         ('madde', ['Türk vatandaşı olmak, yaş ve öğrenim şartlarını taşımak.',
                    'Kamu haklarından mahrum bulunmamak.',
                    'Kasten işlenen bir suçtan bir yıl veya daha fazla hapis cezası almamak. Ayrıca devletin güvenliğine karşı '
                    'suçlar, zimmet, rüşvet, hırsızlık, dolandırıcılık, sahtecilik gibi maddede sayılan suçlardan, af çıkmış olsa '
                    'bile, mahkûm olmamak.',
                    'Askerlik durumu uygun olmak: askerlikle ilgisi olmamak, askerlik çağına gelmemiş olmak ya da askerliği '
                    'yapmış, ertelemiş veya yedek sınıfa geçirilmiş olmak.',
                    'Görevini sürekli yapmana engel bir akıl hastalığı bulunmamak.']),
         'Bunlara ilanda istenen öğrenim düzeyi, bölüm ve KPSS puanı eklenir. Zabıta memuru ve itfaiye eri gibi bazı unvanlarda ilgili '
         'yönetmeliklerden gelen ek şartlar da olur. Zabıta ilanlarında sürücü belgesi ve fiziksel ölçü şartları sık görülür. Bu '
         'şartların sayısal değerleri ilandan ilana ve yönetmelik değiştikçe farklılaşır; sayıyı her zaman ilan metninden doğrula.']),
      ('Norm kadro neden önemli?', [
         'Bir belediyenin kaç memur alabileceği norm kadroya bağlıdır. Norm kadro ilke ve standartlarını kanunda sayılan '
         'kurumlar birlikte belirler; belediyenin ve bağlı kuruluşlarının norm kadrosu bu çerçevede belediye meclisi kararıyla '
         'kurulur. Norm kadroda yeri olmayan bir unvan için ilan beklememelisin.',
         'Belediye personeli belediye başkanı tarafından atanır. Birim müdürlüğü ve üstü yönetici kadrolarına yapılan atamalar '
         'ilk toplantıda belediye meclisinin bilgisine sunulur.']),
      ('Kısmi zamanlı sözleşmeli kadrolar', [
         'Avukat, mimar, inşaat mühendisi, harita mühendisi ve veteriner kadrosu bulunmayan ya da iş azlığı nedeniyle kadrolu '
         'istihdama ihtiyaç duyulmayan belediyeler, bu hizmetler için haftanın ya da ayın belirli gün veya saatlerinde kısmi '
         'zamanlı sözleşmeli personel çalıştırabilir. Böyle bir sözleşme takvim yılını aşamaz, iş sonu tazminatı ödenmez ve '
         'işsizlik sigortası primi yatırılmaz. Aynı kişi birden fazla belediye ya da bağlı kuruluşta çalıştırılamaz.']),
      ('Sözleşmeli personelde 2023 değişikliği', [
         '2023’te 7433 sayılı Kanunla belediyelerdeki sözleşmeli uzman ve teknik personelin işe alınması, memur kadrolarına ilk '
         'defa alınma usulüne bağlandı. Üç yıllık çalışmasını tamamlayan sözleşmeli, talep ederse çalıştırılmasına esas alınan '
         'memur kadrosuna atanır. Atananlar bir yıl süreyle başka kamu kurumlarına nakil olamaz.',
         'Sözleşmelilere ödenecek net ücret, ilgili unvanın birinci derece birinci kademesine göre hesaplanan net memur ödemeleri '
         'toplamının yüzde 25 fazlasını geçemez. Tutarı belediye meclisi belirler.']),
      ('İlanı okurken kontrol listesi', [
         ('madde', ['Kadro sayısı ve sınava çağrılacak en fazla aday sayısı.',
                    'KPSS puan türü, asgari puan ve hangi sınavın sonucunun geçerli olduğu.',
                    'Sınavın bölümleri: yazılı, sözlü ve varsa uygulamalı kısım.',
                    'Başvuru yöntemi, son gün ve saat.',
                    '“İlgili bölüm mezunu” ifadesi geçiyorsa bölüm listesi. Listede yoksan başvurun geçersiz sayılabilir.',
                    'Asıl ve yedek adayların nerede duyurulacağı.'])]),
      ('Örnek ilan okuması', [
         'Örnek (kurgu): Bir belediye 4 itfaiye eri alacak, ortaöğretim mezunu istiyor ve KPSSP94 puanıyla başvuru alıyor. Kadro '
         'sayısının beş katı 20 eder; yani en çok 20 aday sınava çağrılabilir. Başvuranlar arasında puanın 24. sıradaysa, '
         'asgari puanı aşmış olsan bile sınava çağrılmazsın.',
         'Bu yüzden asgari puanı geçmek yeterli bir ölçü değildir. Başvuru sayısını tahmin etmek zordur; aynı belediyenin ya da '
         'komşu belediyelerin önceki ilanları ve sonuç duyuruları fikir verebilir.']),
      ('Sık yapılan hatalar', [
         ('madde', ['Son gün ve saati özetten değil ilan metninden okumamak.',
                    'KPSS puan türünü karıştırmak. Önlisans kadrosuna P93 ile başvurulur, P3 ile değil.',
                    'Bölüm şartını geniş yorumlamak. Kurumlar ilandaki listeye göre karar verir.',
                    'Yedek listeyi takip etmemek. Asıl adaylar göreve başlamazsa yedekler çağrılabilir.',
                    'Aynı ilanda birden fazla kadroya başvurmanın serbest olup olmadığını okumadan form doldurmak.'])])],
     [('Belediye ilanları', '#ilanlar'), ('Başvuruda istenen belgeler', 'rehber/basvuru-belgeleri-ve-hatalar/'),
      ('Kamu işçi alımları', 'rehber/kamu-isci-alimi/'), ('Kamu ilanı istatistikleri', 'analiz/kamu-ilan-istatistikleri/')]),

    ('sozlesmeli-personel-4b', 'Sözleşmeli personel (4/B) nedir? Üniversite ve kurum alımları',
     '657 sayılı Kanunun 4/B maddesine göre sözleşmeli personel: seçme yöntemleri, mali yıl sözleşmesi, kadroya geçiş ve memur ile işçi farkı.',
     'İlanlarda gördüğün “4/B sözleşmeli personel” ifadesi, 657 sayılı Devlet Memurları Kanununun 4. maddesinin (B) fıkrasına göre '
     'istihdamı anlatır. Üniversiteler, hastaneler ve birçok kurum bu yolla alım yapar. Burada 4/B’nin ne olduğunu, nasıl '
     'seçildiğini ve memurluk ile işçilikten neyle ayrıldığını anlatıyoruz.',
     [('4/B nedir?', [
         'Kanuna göre sözleşmeli personel, Cumhurbaşkanınca belirlenen esas ve usuller çerçevesinde, ihdas edilen pozisyonlarda, mali '
         'yılla sınırlı olarak sözleşmeyle çalıştırılan ve işçi sayılmayan kamu hizmeti görevlileridir. Yani ne memursun ne işçi. '
         'Sözleşme süresi mali yılla sınırlıdır; yıl yıl yenilenir.',
         'Sözleşmede yazan görev yeri dışında çalıştırılamazsın ve sözleşmende belirtilen görevin dışında başka bir işte '
         'görevlendirilemezsin. Sözleşme ücreti dışında herhangi bir adla ek ödeme yapılamaz.']),
      ('Nasıl seçilirsin?', [
         'Sözleşmeli Personel Çalıştırılmasına İlişkin Esaslar, kurumlara dört yöntemden birini seçme hakkı verir:',
         ('madde', ['ÖSYM’nin KPSS (B) grubu puanlarıyla yaptığı doğrudan merkezi yerleştirme.',
                    'Yazılı ya da sözlü sınav yapmadan, KPSS (B) puan sırasına göre kurumun yaptığı yerleştirme.',
                    'Esaslara ekli cetvelde unvanı yazılan pozisyonlarda, KPSS (B) sırasına göre boş pozisyonun on katına kadar '
                    'aday arasından yapılan yazılı ve/veya sözlü sınav; yerleştirme sınav başarısına göre olur.',
                    'ÖSYM’nin Genel Yönetmelik hükümleriyle yaptığı merkezi yerleştirme.']),
         'Bazı unvanlarda hiç sınav aranmaz, bazılarında yalnız mesleki uygulamalı sınav yapılır. Kurum, pozisyon sayısını, '
         'nitelikleri, yerleştirme usulünü ve sınavın yer, tarih ve konularını en az on beş gün önce ilan etmek zorundadır. '
         'Başvuruları kurumun kurduğu beş kişilik komisyon inceler.',
         'Kullanılacak puan türü B grubu kadro niteliğindeki sözleşmeli alımlarda lisans için KPSSP3, önlisans için KPSSP93, '
         'ortaöğretim için KPSSP94’tür.']),
      ('Memur, 4/B ve 4/D yan yana', [
         ('madde', ['Dayanak: memur, 657 sayılı Kanunun 4/A ve 48. maddelerine tabidir. 4/B’li, aynı kanunun 4/B maddesine ve '
                    'Sözleşmeli Personel Çalıştırılmasına İlişkin Esaslara tabidir. 4/D’li ise iş kanunlarına göre iş '
                    'sözleşmesiyle çalışan işçidir.',
                    'Seçme: memur ÖSYM yerleştirmesi ya da belediye/giriş sınavıyla, 4/B yukarıdaki dört yöntemle, işçi İŞKUR listesi, '
                    'KPSS puanı ya da noter kurasıyla alınır.',
                    'Süre: memurun adaylığı bir ile iki yıldır ve sonrasında kadrolu olur. 4/B’de sözleşme mali yılla sınırlıdır. '
                    'Sürekli işçi belirsiz süreli sözleşmeyle çalışır; geçici işçi bir mali yılda altı aydan az çalışır.',
                    'Disiplin: 2023’ten beri sözleşmeli personele memurların tabi olduğu disiplin hükümleri uygulanır.',
                    'Giriş şartı: 4/B’de aranacak nitelikleri kurum ilanda belirler; ilanlarda çoğunlukla 657 sayılı Kanunun 48. '
                    'maddesindeki genel şartlar da sayılır. İşçi alımında ise daha yalın şartlar vardır: vatandaşlık, 18 yaş ve '
                    'sayılan suçlardan mahkûm olmamak.'])]),
      ('Ücret nasıl belirlenir?', [
         'Esaslara göre sözleşmeli personelin ücreti; pozisyon unvanı, bu unvana ilişkin eğitim düzeyi ve kamuda aynı kadro ya da '
         'pozisyon unvanında geçen hizmet süresi dikkate alınarak belirlenir. Ücret için bir üst sınır vardır ve bu sınır '
         'Cumhurbaşkanınca artırılabilir. Sözleşme ücreti dışında kimi istisnalar hariç herhangi bir ad altında ödeme yapılamaz ve '
         'sözleşmeye bu yönde hüküm konulamaz.',
         'Hizmet sözleşmesi örneği Cumhurbaşkanlığınca vize edilir. Yani sözleşmenin ücret ve süre maddeleri pazarlık konusu '
         'değildir; imzalamadan önce okumak ve kabul edip etmeyeceğine karar vermek sana kalır. Güncel ücret tavanını '
         'ilan metninden ve kurumdan öğren; bu rehber tutar vermez, çünkü tutar zamanla değişir.']),
      ('4/B ilanına başvurup başvurmamaya nasıl karar verirsin?', [
         ('madde', ['Kadroya geçmek önceliğinse, pozisyonun Cumhurbaşkanınca belirlenen unvanlar arasında olup olmadığını sor. '
                    'Değilse sözleşme her mali yıl için yapılır ve kadro hakkı doğmaz.',
                    'İş sonu tazminatı için askerlik ve doğum dışında kesintisiz en az iki hizmet yılı gerekir. '
                    'Daha kısa kalacaksan bu hakkı hesaba katma.',
                    'Dönem içinde kendi isteğinle ayrılmayı ya da sözleşmeyi yenilememeyi düşünüyorsan, sonrasındaki bir yıllık '
                    'bekleme kuralını hesaba kat.',
                    'İlan engellemediği sürece aynı puanla birden fazla yere başvurabilirsin. Ama merkezi yerleştirmeyle bir '
                    'yere yerleşirsen, o puan sonraki alımlar için kullanılmış olur.'])]),
      ('Kadroya geçiş her 4/B için geçerli değil', [
         '“4/B’liler kadroya geçer” cümlesi yarım doğrudur. 2023’te 657 sayılı Kanuna eklenen hükme göre, Cumhurbaşkanınca '
         'belirlenecek pozisyon unvanlarında çalışan sözleşmeli personel, aynı kurumda üç yıllık '
         'çalışmasını tamamlarsa süre bitiminden itibaren otuz gün içinde talep etmesi hâlinde bulunduğu yerde aynı unvanlı memur '
         'kadrosuna atanır. Aynı unvanlı memur kadrosu yoksa atanacağı kadroyu Cumhurbaşkanı belirler.',
         'Yani hak, yalnızca belirlenen unvanları kapsar. Başvuracağın pozisyon bu unvanlardan biri mi diye ilanda ya da kurumdan '
         'sor. Kadroya atananlar aynı yerde en az bir yıl daha görev yapar ve bu kapsamda memur kadrosuna atananlara iş sonu '
         'tazminatı ödenmez.']),
      ('Ayrılırken ve sözleşme biterken', [
         'Askerlik ve doğum dışında kesintisiz en az iki hizmet yılını dolduranlar, hizmetlerine gerek kalmadığı için sözleşmesi feshedilenler '
         'ya da yenilenmeyenler, yaşlılık veya malullük aylığı bağlananlar ve benzer hâllerde iş sonu tazminatı alır.',
         'Sözleşme esaslarına aykırı davrandığın için kurum sözleşmeni feshederse, dönem içinde sözleşmeyi tek taraflı '
         'feshedersen ya da sözleşmeni yenilemezsen, Cumhurbaşkanı kararıyla belirlenen istisnalar dışında, fesih ya da bitiş '
         'tarihinden itibaren bir yıl geçmeden kurumların sözleşmeli pozisyonlarında yeniden çalışamazsın. İmzalamadan önce '
         'bu kuralı bil.']),
      ('Örnek: sözleşmeli alım ilanını okumak', [
         'Örnek (kurgu): Bir üniversite bir unvan için 5 sözleşmeli personel alacak ve yöntem olarak cetvelde yer alan unvanlara '
         'uygulanan on kat kuralını seçti. Bu durumda KPSS (B) sırasına göre en çok 50 aday sınava çağrılır ve yerleştirme sınav başarısına '
         'göre yapılır. KPSS puanın yüksek olması sınava girmen için yeterlidir ama kazanman için yetmez.',
         'İlan ise “sınavsız KPSS sıralaması” diyorsa durum tersine döner: puan sırası doğrudan belirleyicidir. İki ilanın '
         'başvuru stratejisi bu yüzden farklıdır.']),
      ('Dikkat edilmesi gerekenler', [
         ('madde', ['Aynı ilanda birden fazla pozisyon varsa yalnız birine başvurabilirsin; ilan neyi söylüyorsa ona uy.',
                    'Yerleştirme sonrası istenen belgeleri süresinde teslim etmezsen hak kaybedersin.',
                    'KPSS puan türünün ve yılının ilandaki ile tutmasına dikkat et.',
                    'Sözleşmenin ücret ve süre maddelerini imzalamadan önce oku.'])])],
     [('Açık ilanlar', '#ilanlar'), ('KPSS puan türleri', 'rehber/kpss-puan-turleri/'),
      ('Kamu işçi alımları', 'rehber/kamu-isci-alimi/'), ('Merkezi yerleştirme ve kurum ilanları', 'rehber/merkezi-yerlestirme-ve-kurum-ilanlari/')]),

    ('kamu-isci-alimi', 'Kamu işçi alımları: İŞKUR, kura ve öncelikli gruplar',
     'Kamu işçi alımları nasıl işler? İŞKUR başvurusu, önlisans ve lisansta KPSS, diğer düzeylerde noter kurası, öncelikli gruplar.',
     'Kamuya işçi alımı memur alımından farklı kurallarla yapılır. Başvuru İŞKUR üzerinden alınır; sıralamayı ise ilanın '
     'eğitim düzeyi belirler. Önlisans ve lisans düzeyinde KPSS aranır, ortaöğretim ve altında noter kurası yapılır. Bu '
     'ayrım, ilanı doğru okumanın anahtarıdır.',
     [('İki ayrı yol var', [
         'Kamu kurum ve kuruluşlarına işçi alınmasına dair yönetmelik, işçi taleplerini eğitim düzeyine göre ikiye ayırır.',
         ('madde', ['Önlisans ve lisans düzeyindeki talepler KPSS puanıyla karşılanır. Aynı düzeydeki yalnız engelli taleplerinde '
                    'EKPSS puanı kullanılır.',
                    'Ortaöğretim ve daha alt düzeydeki talepler ile temizlik, güvenlik ve koruma, bakım ve onarım hizmetleri ve '
                    'eğitim şartı aranmayan kömür ve maden yeraltı işleri noter huzurunda çekilen kurayla belirlenir.']),
         '“Kamu işçisi olmak için KPSS gerekmez” cümlesi her ilan için doğru değildir. Önlisans ya da lisans düzeyi isteyen '
         'işçi ilanlarında KPSS şarttır; kura yalnızca yukarıdaki işlerde yapılır.',
         'İşçi olarak girecek kişiler için yönetmeliğin aradığı genel şartlar sadedir: Türk vatandaşı olmak, 18 yaşını '
         'tamamlamış olmak, sayılan suçlardan mahkûm olmamak ve kurumun özel kanunlarındaki şartları taşımak.']),
      ('Sürekli ve geçici işçi farkı', [
         'Sürekli işçi, belirsiz süreli iş sözleşmesiyle çalışır. Geçici işçi ise mevsimlik ve kampanya işlerinde ya da orman '
         'yangınıyla mücadele hizmetlerinde, bir mali yılda altı aydan az süreyle çalışır. İlanda hangisinin arandığı yazar.',
         '2025’te yönetmeliğe eklenen bir hükme göre, geçici işçi alımlarında kurum isterse son başvuru tarihinden önceki altı '
         'aya kadar SGK’ya bildirilmemiş olma şartı arayabilir. Tarımsal faaliyette bulunanlar, tarım ya da orman işlerinde '
         'süreksiz çalışanlar ve isteğe bağlı sigortalılar bu şarttan muaf tutulur.']),
      ('Başvuru nasıl yapılır?', [
         'Kamu işçi talepleri İŞKUR internet sayfasında ilan edilir. İŞKUR’un anlattığına göre başvuruyu internet şubesi, Alo 170 '
         'hattı ya da en yakın İŞKUR birimi üzerinden yaparsın. Başvuru süresi beş gündür. Son gün resmî tatile denk gelirse '
         'süre izleyen ilk iş günü sonuna kadar uzar.',
         'Başvuruda Adrese Dayalı Nüfus Kayıt Sistemindeki adresin esas alınır. İlçe, il ya da bölge düzeyindeki bir ilana '
         'başvuru süresi içinde o yere taşınanların başvurusu kabul edilmez. Aynı kurumun, başvuru tarihleri çakışan ilanlarından '
         'yalnız birine başvurabilirsin.',
         'Kimlik bilgisi olarak T.C. kimlik numarası beyanın yeterlidir. Adli sicil ve askerlik konusunda da beyanın esas alınır.']),
      ('KPSS’li ilanlar nasıl işler?', [
         'Önlisans ve lisans düzeyindeki işçi ilanlarına başvurmak için ilgili KPSS puan türünden en az 60 puan almış olman '
         'gerekir. Engelli taleplerinde puan barajı yoktur; EKPSS’ye girmiş olmak yeterlidir.',
         'İŞKUR, başvuranlar arasından en yüksek puandan başlayarak açık iş sayısının dört katı kadar adayı kuruma gönderir. '
         'Listenin son sırasındaki adayla aynı puana sahip olanlar da listeye eklenir. Kurum bu adaylarla yazılı veya sözlü, '
         'mesleki bilgi ve becerilere dönük sınav yapar.']),
      ('Kuraya tabi ilanlar nasıl işler?', [
         'Noter kurasına tabi ilanlarda kurum, ilanda yazan gün, saat ve adreste kurayı noter huzurunda çeker; adaylar isterse '
         'çekimi izleyebilir. Açık iş sayısının dört katı kadar asıl ve aynı sayıda yedek aday kurayla belirlenir.',
         'Kurum isterse sınav yapmadan yalnız kurayla da işe alım yapabilir; bu durumda açık iş sayısı kadar asıl ve gerekli sayıda '
         'yedek aday doğrudan kurayla belirlenir. Temizlik, güvenlik ve bakım-onarım alımlarında kura yapıldıktan sonra sınav '
         'yapılıyorsa yalnız sözlü yöntem kullanılır.']),
      ('Örnek: iki ilan, iki ayrı süreç', [
         'Örnek (kurgu): Bir kurum 10 temizlik işçisi alacak. Kura ile 40 asıl ve 40 yedek aday belirlenir; şartları taşıyan '
         'başvuruların hepsinden yalnızca bu adaylar sınav ya da işe alım aşamasına geçer. Burada puan belirleyici değildir; '
         'şansın başvuru sayısına bağlıdır.',
         'Aynı kurum 3 tekniker (önlisans) alacaksa KPSS puanın en az 60 olmalıdır. Başvuranlar arasından en yüksek puanlı 12 aday '
         'sınava gönderilir. Burada puan belirleyicidir; kura yoktur.']),
      ('Öncelikli gruplar, engelli ve eski hükümlü ilanları', [
         'Yönetmelik bazı gruplara işe göndermede öncelik tanır: terörle mücadelede malul sayılmayacak şekilde yaralananlar ve '
         'üstün başarı gösterenler, tabii afetten zarar görenler, madenler için tamamen kamulaştırılanlar ve sürekli işçi iken '
         'belirli nedenler dışında iş akdi feshedilenler. Öncelik hakkı işe yerleşme garantisi vermez ve ikinci kez kullanılamaz.',
         'Kamu işyerlerinde, elli veya daha fazla işçi çalıştıran işyerlerinde yüzde dört engelli ve yüzde iki eski hükümlü '
         'çalıştırma yükümlülüğü vardır. Bu ilanlar için İŞKUR’da engelli ya da eski hükümlü kaydın olmalı. Engelli kaydı için '
         'en az yüzde kırk engel oranını gösteren sağlık kurulu raporu gerekir.']),
      ('Başvurudan işe başlamaya', [
         'İŞKUR, son başvuru tarihini izleyen günden itibaren iki iş günü içinde listeleri kuruma gönderir. Sınav gününü, saatini '
         've yerini ve sınava hak kazananları kurum kendi internet sitesinde duyurur. Bu duyuru tebligat yerine geçer; postayla '
         'ayrıca haber gelmez. İşe alım sürecinin listelerin ulaşmasından sonra yirmi gün içinde tamamlanması esastır.',
         'Sürekli işçi olarak işe girip deneme süresi sonunda çalışmaya devam edenler, aynı KPSS ya da EKPSS puanıyla başka bir '
         'kamu kurumunun sürekli işçi talebine başvuramaz.']),
      ('Kapsam dışında kalan alımlar', [
         'Bankalar, borsalar, kamu kurumlarının Türk Ticaret Kanununa göre kurduğu şirketler, kooperatifler, sosyal '
         'yardımlaşma vakıfları ve proje bazlı bazı özel işler bu yönetmeliğin kapsamı dışındadır. Bu alımların ilanları da '
         'İŞKUR’a bildirilir ve İŞKUR’un internet sitesinde duyurulur, ama başvuru ilanı veren kurumun belirttiği yöntemle '
         'yapılır. Yani İŞKUR sitesindeki her ilan aynı kura ya da KPSS kuralına tabi olmaz. İlanın “kurum dışı” olup '
         'olmadığına bak.']),
      ('Sık yapılan hatalar', [
         ('madde', ['Kuruma doğrudan başvurmak. Yönetmeliğe göre talepler İŞKUR’dan karşılanır; ilan aksini yazmıyorsa İŞKUR yolunu kullan.',
                    'Başvuru süresinde ikamet adresini değiştirmek.',
                    'Çakışan iki ilana aynı kurum için başvurmak.',
                    'Duyuruları kurumun sitesinden izlememek. Sınav bilgisi orada yayımlanır.'])])],
     [('Açık ilanlar', '#ilanlar'), ('EKPSS ve engelli kadroları', 'rehber/ekpss-engelli-memur-alimi/'),
      ('Sözleşmeli personel (4/B)', 'rehber/sozlesmeli-personel-4b/'), ('Kamu ilanı istatistikleri', 'analiz/kamu-ilan-istatistikleri/')]),

    ('sozlesmeli-bilisim-personeli', 'Sözleşmeli bilişim personeli alımları nasıl yapılır?',
     'Kamu kurumlarının sözleşmeli bilişim personeli ilanları: dayanak, A/B/C pozisyonları, deneyim, KPSS P3 ve yabancı dil sıralaması.',
     'Bakanlıklar ve diğer kurumlar yazılım geliştirici, sistem uzmanı, veri tabanı yöneticisi, bilgi güvenliği uzmanı gibi '
     'kadrolara “sözleşmeli bilişim personeli” ilanlarıyla alım yapar. Bu ilanların kendi kuralları var ve ilandan ilana '
     'ciddi farklar gösterir. Burada ortak çerçeveyi ve ilanı okurken nelere bakacağını anlatıyoruz.',
     [('Dayanak ve kapsam', [
         'İlanlar genellikle 375 sayılı Kanun Hükmünde Kararnamenin ek 6. maddesine ve 31 Aralık 2008 tarihli, 27097 sayılı Resmî '
         'Gazetede yayımlanan Kamu Kurum ve Kuruluşlarının Büyük Ölçekli Bilgi İşlem Birimlerinde Sözleşmeli Bilişim Personeli '
         'İstihdamına İlişkin Esas ve Usuller Hakkında Yönetmeliğin 8. maddesine dayanır. Bazı kurumların kendi bilişim '
         'personeli yönetmelikleri de vardır.',
         'Bu ilanlarda seçme usulü, ilanın dayandığı yönetmeliğin kendi maddesine göre yapılır; ilanlarda çoğunlukla 8. madde '
         'anılır. Bu yüzden genel sözleşmeli personel (4/B) alımlarındaki yöntemleri buraya aynen taşıma. Kurum ilanının '
         'dayanağı olarak hangi yönetmeliği saydığına bak.']),
      ('Kimler başvurabilir?', [
         'İlanlarda ortak çerçeve şudur. Birinci gruba bilgisayar, yazılım, elektrik, elektronik, elektrik-elektronik ve endüstri '
         'mühendisliği mezunları girer. İkinci gruba ise bunların dışındaki dört yıllık mühendislik bölümleri, fen-edebiyat ve '
         'eğitim fakültelerinin bilgisayar ve teknoloji bölümleri ile istatistik, matematik ve fizik mezunları girer. Yurt '
         'dışı diplomalarda YÖK denkliği aranır. Ayrıca 657 sayılı Kanunun 48. maddesindeki genel şartlar ve güncel programlama '
         'dillerinden en az ikisini bildiğini belgelemek istenir.',
         'Ayrıntı ilandan ilana değişir. “Bölüm listesi” ve “belge listesi” bölümlerini harfi harfine kontrol et.']),
      ('A, B ve C grupları: ücret katı ve deneyim', [
         'İlanlarda pozisyonlar A, B ve C gibi gruplara ayrılır. Her pozisyonun yanında “brüt sözleşme ücret tavanının 2, 3 ya da '
         '4 katına kadar” gibi bir ifade yazar. Kat arttıkça istenen mesleki tecrübe de artar.',
         'Bir kurumun ilanında genel şart olarak, ücret tavanının iki katını geçmeyecek pozisyonlar için en az 3, üç katını '
         'geçmeyecek pozisyonlar için en az 5 yıllık yazılım ya da büyük ölçekli ağ deneyimi aranmıştı. Pozisyona özel şartlar '
         'bundan da uzun süre isteyebilir. “Kıdemli” unvanlı pozisyonlarda deneyim süresi belirgin biçimde yükselir.',
         'Mesleki tecrübeye hangi hizmetlerin sayıldığını ilan açıklar. Aynı kurum ilanında; bilişim personeli olarak kadrolu '
         'veya 4/B ya da 399 sayılı KHK’ya tabi sözleşmeli geçen hizmetler ile özel sektörde prim ödenerek işçi statüsünde '
         'bilişim personeli olarak geçen, belgelenebilir hizmetler sayıldı.']),
      ('Sıralama ve sınav nasıl yapılır?', [
         'Başvurular önce bir formülle sıralanır; en üstten başlayarak her pozisyon için ilanda yazan sayıda aday sözlü ya da '
         'uygulamalı sınava çağrılır. Formül kurumdan kuruma değişir. Bir kurum ilanında KPSS P3 puanının yüzde 70’i ile son '
         'beş yılda alınmış İngilizce YDS puanının yüzde 30’u toplanmıştı. '
         'Hangi sınavın puanının, hangi yıllarda alınmış olması gerektiğini de ilan yazar.',
         'Sınava çağrılan sayı da değişir. Kurumlar kimi ilanda pozisyon başına 4 katı, kimi ilanda 10 katı aday çağırdı. Yerleştirme '
         'sözlü ya da uygulamalı sınav başarı sırasına göre yapılır; yani formülde ilk sırada olmak işe girmek demek değildir.']),
      ('Örnek: formül sıralamayı nasıl değiştirir?', [
         'Örnek (kurgu): İlan, KPSS P3’ün yüzde 70’i ile YDS’nin yüzde 30’unu topluyor; KPSS puanı olmayan adayın KPSS puanı 70, '
         'yabancı dil puanı olmayan adayın yabancı dil puanı 0 sayılıyor.',
         'Ali’nin KPSS P3’ü 80, YDS’si 70 olsun: 0,70×80 + 0,30×70 = 77. Seda’nın KPSS’si yok ama YDS’si 90: 0,70×70 + 0,30×90 = 76. '
         'Yalnızca bir puan farkıyla Ali öne geçer. Formülün ağırlığını ve eksik belgeye verilen puanı bilmeden strateji kuramazsın.']),
      ('Hangi pozisyona başvurmalısın?', [
         'Önce deneyim yılını belgeleriyle hesapla, sonra pozisyonun ücret katına bak. Örnek (kurgu): Genel şartı “ücret '
         'tavanının 2 katı için en az 3 yıl, 3 katı için en az 5 yıl” olan bir ilanda dört yıl belgeli deneyimin varsa 2 kata '
         'kadar olan pozisyonlara başvurabilirsin. 3 kata kadar olan pozisyonlar, ilan başka bir şey söylemiyorsa sana kapalıdır. '
         'Pozisyona özgü şartlar bu genel çerçeveyi daha da yükseltebilir.',
         'Tam zamanlı, kısmi zamanlı ya da proje bazlı olup olmadığını da kontrol et. İlanlar pozisyon başına “tam zamanlı” gibi '
         'ifadeler taşır. Kıdemli pozisyonlar belirli bir sistem ya da yazılım yığınında yıllarca çalışmış olmayı ve sertifikaları '
         'ister; bu belgelerin eksiği başvurunu geçersiz kılar.',
         'KPSS puanı konusunda da ilanı oku. Bir ilan yalnızca belirli yılların KPSS sınavlarını kabul etmiş, KPSS puanı '
         'olmayan adaya 70, yabancı dil puanı olmayana 0 puan verilmişti. Bu kural senin için avantaj ya da dezavantaj '
         'yaratabilir.']),
      ('Belgelerini önceden hazırla', [
         ('madde', ['Diploma ve bölüm bilgisi; yurt dışı diplomada YÖK denklik belgesi.',
                    'Hizmet dökümü ve işveren yazısı ya da sözleşme: deneyim süresini belgelemek için gerekir.',
                    'Güncel programlama dillerini, ağ ve güvenlik bilgisini gösteren sertifika ya da belge.',
                    'Yabancı dil belgesi; ilan hangi sınavları ve kaç yıllık geçerliliği kabul ediyorsa ona uygun olmalı.',
                    'KPSS P3 sonuç belgesi.'])]),
      ('Başvuru ve takvim', [
         'Bu ilanların büyük kısmı Kariyer Kapısı üzerinden yayımlanır. Bakanlıklardan örnek ilanlarda başvuru süresi yaklaşık '
         'iki hafta sürdü. Başvurunun ardından sınava çağrı ve sonuç duyuruları ilanda yazan yerde yayımlanır.']),
      ('Sık yapılan hatalar', [
         ('madde', ['Deneyim süresini hesaplarken hangi hizmetlerin sayıldığını okumamak.',
                    'Formülü okumadan yalnız KPSS’ye güvenmek.',
                    'Yabancı dil belgesinin geçerlilik süresini kaçırmak.',
                    'Pozisyonun ücret katı ile deneyim şartını ayrı ayrı okumamak.'])])],
     [('Bilişim ilanları', '#ilanlar'), ('Kariyer Kapısı rehberi', 'rehber/kariyer-kapisi-basvuru/'),
      ('Başvuru belgeleri ve hatalar', 'rehber/basvuru-belgeleri-ve-hatalar/')]),

    ('ekpss-engelli-memur-alimi', 'EKPSS ve engelli kamu personeli alımları',
     'EKPSS nedir, engelli memur ve işçi alımları nasıl yapılır? Puan türleri, geçerlilik, kura, sağlık raporu ve tercih kuralları.',
     'Engelli adayların kamuya atanması için ayrı bir sınav, ayrı bir tercih kılavuzu ve ayrı kadrolar vardır. Bu rehber EKPSS’nin '
     'nasıl işlediğini, memur ve işçi alımlarında nelere dikkat etmen gerektiğini yönetmelik ve ÖSYM kılavuzuna göre anlatır.',
     [('EKPSS nedir?', [
         'Engelli Kamu Personeli Seçme Sınavı (EKPSS), ortaöğretim, önlisans ve lisans mezunu engelliler için ÖSYM’nin yaptığı '
         'merkezi sınavdır. Yönetmeliğe göre bu sınav, kurumların engelli kontenjanı açığı bulunduğu sürece diğer merkezi '
         'sınavlardan ayrı yapılır. İlkokul, ortaokul ve özel eğitim okulu mezunları için sınav değil kura uygulanır.',
         'ÖSYM yerleştirmede ortaöğretim kadroları için EKPSSP1, önlisans kadroları için EKPSSP2, lisans kadroları için EKPSSP3 '
         'puanını kullanır. İlköğretim, ortaokul ve ilkokul düzeyindeki kadrolara ise tercihlere göre kura ile yerleştirme yapılır.']),
      ('Engelli kime denir?', [
         'Yönetmeliğe göre engelli; bedensel, zihinsel, ruhsal, duyusal ve sosyal yeteneklerinde engel oranı en az yüzde kırk olan '
         've bunu sağlık kurulu raporuyla belgeleyen kişidir. Raporda “çalışabilir” olduğunun da yazması gerekir.']),
      ('Puan ne kadar geçerli?', [
         'EKPSS sonuçları dört yıl geçerlidir. ÖSYM’nin 2026 EKPSS/Kura tercih kılavuzu, 2022 ve 2024 EKPSS sonuçlarıyla ya da '
         'aynı yıllardaki kura kaydıyla tercih yapılabileceğini yazıyordu. Kura kayıtları iki yılda bir alınır ve kayıt dört '
         'yıl içindeki engelli memur alımları için geçerlidir. Yeni bir kılavuz çıktığında hangi yılların kabul edildiğini '
         'yeniden kontrol et.']),
      ('Memur kadroları: kontenjan ve tercih', [
         '657 sayılı Kanuna göre kurumlar, çalıştırdıkları memur kadrolarının yüzde 3’ü oranında engelli çalıştırmak zorundadır. '
         'Engelli açığı bulunan kurumlar, ertesi yıl alacakları engelli sayısını her yılın Ekim ayı sonuna kadar bildirir.',
         'ÖSYM tercih kılavuzunda ortaöğretim, önlisans ve lisans düzeyindeki kadrolar ayrı tablolarda yer alır. Kılavuza göre '
         '30’u geçmemek üzere tercih yazarsın. Tercihler yalnız internetten bildirilir; kâğıt liste ya da dilekçe işleme alınmaz.',
         'Yerleştirme sonrası kuruma kılavuzda yazan belgelerle ve verilen süre içinde başvurursun. Beş kişilik komisyon nitelikleri '
         'inceler; uygun bulunan adaylar ayrıca sınav ya da mülakat yapılmadan atanır.']),
      ('Kadroya özgü sağlık ve belge şartları', [
         'Bazı kurumlar engel durumuna ilişkin ek şart arar. ÖSYM’nin 2026 kılavuzundaki örnekler şöyle:',
         ('madde', ['Türk Silahlı Kuvvetleri, Jandarma Genel Komutanlığı ve Sahil Güvenlik Komutanlığı kadroları için “TSK’da '
                    'Engelli Memur Olur” raporunu almak gerekir. Ruhsal ve duygusal engel grubunda olanlar ya da ruhsal hastalığı '
                    'bulunanlar bu raporu alamadığı için bu kadrolara atanamaz.',
                    'Emniyet Genel Müdürlüğü kadrolarında psikiyatrik hastalık nedeniyle engel oranı bulunanlar atanamaz.',
                    'Avukat kadrosunda avukatlık ruhsatnamesine tercihlerin son günü itibarıyla sahip olmak gerekir. Staj bitirmiş '
                    'ya da ruhsat başvurusu yapmış olmak yetmez.',
                    'Bilgisayar işletmeni gibi sertifika isteyen kadrolarda sertifikanın MEB’den, MEB onaylı kurslardan ya da '
                    'yükseköğrenim kurumlarından alınmış olması gerekir.']),
         'Kılavuz ayrıca, ilgili kurumların atama öncesinde raporunda çalıştırılamayacağı işler yazmayan engelli adaylardan yeni '
         'rapor ya da kontrol muayenesi isteyebileceğini belirtir.']),
      ('Tercih hatası pahalıya patlar', [
         'ÖSYM kılavuzu açıkça uyarır: hatalı tercih yapan adayların ataması yapılmaz ve bu adaylar aynı sınav sonucuyla ya da '
         'kura başvurusuyla yeniden tercih yapamaz. Yerleştirilip kuruma başvurmayanlar da aynı puanla tekrar tercih yapamaz.',
         'Örnek (kurgu): Zeynep önlisans düzeyinde EKPSS’ye girdi. Tercih listesine yazdığı bir kadro belirli bir sertifika '
         'istiyor ve Zeynep’te bu sertifika yok. Yerleşse bile ataması yapılmaz ve o puanla başka bir dönem tercih yapamaz. Bu '
         'yüzden her kadro için nitelik koşullarını tek tek kontrol et.']),
      ('Süreç sırasıyla', [
         ('madde', ['ÖSYM EKPSS başvurusunu alır ve sınavı yapar; kura kaydı için ayrı başvuru dönemi vardır.',
                    'Sonuç açıklanır. Puanın dört yıl geçerlidir.',
                    'ÖSYM EKPSS/Kura tercih kılavuzunu yayımlar. Kadro, nitelik ve kontenjan tabloları burada olur.',
                    'Tercihlerini ÖSYM’nin aday işlemleri sistemi üzerinden bildirirsin. Süre bitene kadar değiştirebilirsin; sonrasında '
                    'dilekçeyle değişiklik yapılamaz.',
                    'ÖSYM yerleştirir. Sonuçlar duyurulur.',
                    'Yerleştiğin kuruma kılavuzdaki belgelerle ve verilen süre içinde başvurursun; kurum nitelikleri kontrol eder ve atar.'])]),
      ('Halen memursan ve emekliysen', [
         'Halen memur olarak çalışanlar, kural olarak EKPSS yerleştirmesine başvuramaz; başka hizmet sınıfındaki kadrolar ve '
         'mezun oldukları programa göre ihraz ettikleri farklı unvanlar bu kuralın dışındadır. Bir sosyal güvenlik kurumundan '
         'emeklilik ya da yaşlılık aylığı alanlar, genel bütçeli idareler gibi kurumların kadrolarına açıktan tekrar '
         'atanamaz; bu durumdaysan tercih listene o kurumları yazma.']),
      ('İşçi kadroları', [
         'Kamu kurumlarının engelli işçi talepleri İŞKUR’dan karşılanır. Önlisans ve lisans düzeyindeki yalnız engelli taleplerinde '
         'EKPSS puanı kullanılır ve puan barajı aranmaz; EKPSS’ye girmiş olmak yeterlidir. Daha alt düzeylerde noter kurası '
         'yapılır. Kuraya tabi engelli ilanlarına zihinsel engelliler eğitim durumlarına bakılmaksızın başvurabilir.',
         'İşçi alımında kurum, işin niteliği gerektirmedikçe engel oranına üst sınır koyamaz ve engel grupları arasında ayrım '
         'yapamaz. Başvuruda sınavda refakatçiye ihtiyacın olup olmadığı sorulur ve kayda alınır.']),
      ('Başvuruda aklında tutacakların', [
         ('madde', ['Sağlık kurulu raporun geçerli olmalı ve “çalışabilir” ibaresini taşımalı.',
                    'Mezuniyet, tercih gününe kadar tamamlanmalı.',
                    'Nitelik kodlarını ve başvuru özel şartlarını kılavuzdan oku.',
                    'Aynı puan ya da kura kaydıyla bir kez yerleştikten sonra yeniden başvuramazsın.'])])],
     [('Açık ilanlar', '#ilanlar'), ('Nitelik kodlarını kontrol et', 'rehber/kpss-nitelik-kodu-nasil-okunur/'),
      ('Kamu işçi alımları', 'rehber/kamu-isci-alimi/')]),

    ('basvuru-belgeleri-ve-hatalar', 'Kamu ilanlarına başvuruda istenen belgeler ve sık yapılan hatalar',
     'Kamu ilanlarında hangi belgeler, ne zaman istenir? Beyan ve belge farkı, mezuniyet ve sertifika tarihi, yanlış beyan sonuçları.',
     'Şartları taşıyan birçok aday küçük bir hata yüzünden elenir. Çoğu zaman sorun belgenin kendisinde değil, belgenin ne zaman '
     've nasıl istendiğini yanlış bilmektedir. Bu rehber, başvurudan atamaya kadar hangi aşamada ne istendiğini ve nerede hata '
     'yapıldığını gösterir.',
     [('Aşamaya göre belge: ne zaman ne istenir?', [
         ('madde', ['Merkezi yerleştirme tercihi: ÖSYM senden belge istemez. Yerleştirmede başvuru belgesi ve tercih formundaki '
                    'beyanların esas alınır. Hata yaparsan sonucunu sen yaşarsın.',
                    'Yerleştiğin kuruma başvuru: ÖSYM tercih kılavuzunda yazan belgeler ve KPSS sonuç belgesi, kılavuzdaki süre içinde teslim edilir.',
                    'Kurum sınavına başvuru: kurum KPSS sonuç belgesinin bilgisini ÖSYM’nin sitesinden doğrular. Gerisi ilan metninde yazar.',
                    'Atama öncesi: kimlik, adli sicil, askerlik ve sağlık durumu için kurum yazılı beyan alır ve bu konularda '
                    'beyandan başka belge istemez. Adli sicil ve askerlik beyanı sonradan resmî makamlardan teyit edilir.',
                    'İşçi alımı: kimlik için T.C. kimlik numarası beyanı yeterlidir; kurum aslını görmek isterse nüfus cüzdanını '
                    'istemeye hakkı vardır. Adli sicil ve askerlik beyana dayanır.',
                    'İŞKUR başvurusu: İŞKUR özgeçmişinin yanında ilanda istenen meslek sertifikalarını, engelli, eski hükümlü ya da '
                    'terörle mücadelede yaralanma durumuna ilişkin belgeleri sisteme eklemeni ister.',
                    'Kariyer Kapısı: başvuruda istenen belgeler e-Devlet üzerinden ilgili kuruma iletilir; ayrıca fiziksel evrak '
                    'göndermen gerekmez.'])]),
      ('Bilmediğin kural: beyan ve belge farkı', [
         'Kurumlar adaydan kimlik, adli sicil, askerlik ve sağlık konusunda ayrıca belge isteyemez; yazılı beyan yeterlidir. '
         'Bu, beyanını rahat yazabilirsin demek değildir. Gerçeğe aykırı belge ya da beyan verdiğin anlaşılırsa atama yapılmaz, '
         'yapılmışsa iptal edilir ve ceza hükümleri uygulanır.',
         'İşçi alımında kuruma verdiğin belgelerin suretleri, asıllarının ibraz edilmesi kaydıyla kurum tarafından tasdik edilir. '
         'Yani fotokopiyi noterde onaylatmak zorunda değilsin; aslını yanında bulundur.']),
      ('Diploma, mezuniyet ve sertifika: tarih önemlidir', [
         'Merkezi yerleştirmede, tercihlerin ÖSYM’ye gönderildiği gün sınava girdiğin düzeyde mezun olmuş olmalısın. EKPSS '
         'kılavuzu ayrıca, tercih edilecek kadrolar için aranan sertifika gibi belgelere tercihlerin son günü itibarıyla sahip '
         'olmanı ister. Sertifikanın MEB’den, MEB onaylı kurslardan ya da yükseköğretim kurumlarından alınmış olması gerekebilir.',
         'Örnek (kurgu): Bir bilgisayar işletmeni kadrosu “MEB onaylı bilgisayar işletmeni sertifikası” istiyor. Sertifika '
         'kursuna tercih tarihinden sonra bitirirsen, yerleşsen bile bu şartı taşıyamazsın. Belgeyi başvuru gününden önce '
         'elinde tut.']),
      ('Yanlış beyanın bedeli', [
         'Örnek (kurgu): Mert, adli sicil beyanında kapsamdaki bir mahkûmiyetini yazmadı ve yerleştiği kurumda ataması yapıldı. '
         'Beyanlar sonradan ilgili adli mercilerden teyit edilir. Atama işlemi bu teyit tamamlanmadan da sürdürülebildiği için '
         '“kimse bakmaz” düşüncesi yanlıştır; yanlış çıkarsa atama iptal edilir ve ceza hükümleri işletilir.',
         'Aynı kural ÖSYM tercihlerinde de geçerlidir: yerleştirmede beyanların esas alınması, beyanın hatalıysa sorumluluğun sana '
         'ait olması demektir. Mezuniyet, program ve alan bilgilerini ÖSYM sistemindeki kayıtla karşılaştırmadan tercih yapma.']),
      ('Dikkat çeken özel durum: lisansı bırakıp önlisans diploması almak', [
         'EKPSS kılavuzu, lisans programından ilişiğini keserek önlisans diploması alan adaylar için ayrı bir uyarı yapar. Hem '
         'lisansta hem önlisansta aynı adı taşıyan programlar (işletme, maliye, hemşirelik gibi) için bu adaylar kendilerini '
         'ÖSYM sistemine önlisans işletme gibi değil, “alansız önlisans diploması” olarak kaydettirmeli ve herhangi bir önlisans '
         'programı mezunluğu isteyen kadroları tercih etmelidir. Aksi hâlde yerleşseler bile atamaları yapılmaz. Benzer bir '
         'durumdaysan kendi kılavuzundaki ilgili maddeye bak.']),
      ('Tercihin ÖSYM’ye ulaştığını nasıl anlarsın?', [
         'Tercihlerini gönderdikten sonra ekranda tercihlerinin ÖSYM’ye bildirildiğini söyleyen ifadeyi görmen gerekir. '
         'Kılavuzlar bu aşamada çıktı almanı ve çıktıyı saklamanı, ardından aday işlemleri sisteminden tercihlerini kontrol '
         'etmeni ister. Bu ifadeyi görmediysen işlem tamamlanmamış olabilir.']),
      ('Aynı gün, farklı saat', [
         'Örnek olarak ÖSYM’nin KPSS-2026/1 tercih kılavuzunda tercihler son gün saat 23.59’da sona eriyordu ve bu süre kesinlikle '
         'uzatılmayacaktı. Yerleştirme ücretini bankadan ödeyenler için süre ertesi gün mesai bitiminde, kart ile internetten '
         'ödeyenler için ertesi gün 23.59’da bitiyordu. Yani tercih bitimi ile ödeme bitimi aynı an değildi. Her dönemin '
         'kılavuzundaki saatleri ayrı ayrı oku ve ikisini de takvimine yaz.']),
      ('Deneyim belgeleri', [
         'Bilişim gibi deneyim isteyen ilanlarda SGK hizmet dökümü, işveren yazısı ya da sözleşme gibi belgeler istenir. İlan '
         'hangi hizmetlerin sayılacağını açıklar; kadrolu, 4/B sözleşmeli ve özel sektörde prim ödenerek geçen işçi hizmetleri '
         'ayrı ayrı sayılabilir. Süreyi belgeden gün gün hesapla, “yaklaşık” ile başvurma.']),
      ('Başvuru öncesi mini kontrol listesi', [
         ('madde', ['Son gün ve saat ilan metninden kontrol edildi mi?',
                    'KPSS puan türü ve hangi sınavın puanı kabul ediliyor?',
                    'Bölüm, sertifika, sürücü belgesi ve deneyim şartları gerçekten karşılanıyor mu?',
                    'Başvuru yöntemi (Kariyer Kapısı, İŞKUR, ÖSYM ya da kurum sistemi) doğru mu?',
                    'Aynı ilanda birden fazla kadroya başvuru yasak mı?',
                    'E-Devlet’teki mezuniyet, askerlik ve iletişim bilgilerin güncel mi?'])]),
      ('Sık yapılan hatalar', [
         ('madde', ['Son güne bırakmak. ÖSYM kılavuzları tercih süresinin uzatılmayacağını açıkça yazar.',
                    'Yanlış puan türü ya da süresi dolmuş sonuçla başvurmak.',
                    'Mezun olmadan tercih yapmak ya da şartı karşılamayan kadroyu seçmek.',
                    'Yerleştirme ücretini zamanında ödememek. Bu durumda tercihler geçersiz sayılır.',
                    'Duyuruları takip etmemek. Sınav yeri ve tarihi kurumun kendi sitesinde duyurulur; işçi alımında bu duyuru '
                    'tebligat yerine geçer.',
                    'İşçi alımında başvuru süresi içinde ikamet adresini değiştirmek.'])]),
      ('Başvurudan sonra', [
         'Başvuru özetini, ücret dekontunu ve belgelerinin kopyalarını sakla. İlan düzeltme ya da iptal duyurusu yapılabilir; '
         'KPSS Tercihi ilan sayfalarında bu duyuruları ayrıca gösterir. İşçi alımında kurumun internet sitesindeki duyuru '
         'tebligat yerine geçer; yani sana ayrıca yazı gelmeyebilir. Diğer ilanlarda da sınav bilgisini kurumun sitesinden izle.'])],
     [('Kariyer Kapısı rehberi', 'rehber/kariyer-kapisi-basvuru/'), ('Nitelik kodları', 'rehber/kpss-nitelik-kodu-nasil-okunur/'),
      ('Açık ilanlar', '#ilanlar')]),

    ('kariyer-kapisi-basvuru', 'Kariyer Kapısı ile kamu ilanına başvuru nasıl yapılır?',
     'Kariyer Kapısı’nda kamu ilanı arama, e-Devlet ile giriş, başvuru, sonuç takibi ve ÖSYM ile İŞKUR’dan farkı.',
     'Kariyer Kapısı, kamu kurumlarının iş ilanlarını yayımladığı ve başvuruları e-Devlet şifresiyle aldığı Cumhurbaşkanlığı '
     'koordinasyonundaki bir platformdur. Birçok kurum ilanı burada yayımlar, ama memur yerleştirmesi ve işçi alımı farklı '
     'kanallardan yürür. Burada hangi işin nereden yürüdüğünü ve platformda nasıl ilerleyeceğini anlatıyoruz.',
     [('Kariyer Kapısı neyi kapsar, neyi kapsamaz?', [
         'Kariyer Kapısı, kurumların yetkili kullanıcılar aracılığıyla ilan yayımladığı bir araçtır. Başvuru koşullarını kurum '
         'belirler; seçme, işe alım ve yerleştirmeyi de kurum yapar. Platform bunu yürütmez, yalnızca başvuruyu standartlaştırır.',
         ('madde', ['ÖSYM merkezi yerleştirmesi: tercihlerini ÖSYM’nin aday işlemleri sisteminden yaparsın.',
                    'Kamu işçi alımları: İŞKUR üzerinden yapılır; kendi ilan ve başvuru sistemi vardır.',
                    'Kurum ilanları (sözleşmeli, bilişim, uzman yardımcılığı gibi): çoğu zaman Kariyer Kapısı’ndan alınır, ama kurum '
                    'başka bir yöntem seçmişse ilan nereye yönlendiriyorsa oradan başvurursun.']),
         'Platform ücretsizdir, e-Devlet erişimi olan herkes kullanabilir.']),
      ('Adım adım başvuru', [
         ('madde', ['kariyerkapisi.gov.tr adresine git ve e-Devlet şifrenle giriş yap.',
                    '“Kamu İş İlanları” bölümünden ilanı bul. İlan sayfasında kadrolar, aranan nitelikler ve başvuru tarihleri yer alır.',
                    'Şartları tek tek karşıladığından emin ol: bölüm, KPSS puan türü, deneyim, belge ve tarih.',
                    'Başvuru ekranındaki adımları sonuna kadar tamamla. Başvurunun kaydedildiğini gösteren ekranı görmeden çıkma.',
                    'Başvuruyu bitirdikten sonra ekran görüntüsünü ya da özetini sakla.'])]),
      ('Başvurmadan önce hazırlık', [
         ('madde', ['E-Devlet şifreni ve doğrulama yöntemini önceden dene; son gün şifre yenilemekle uğraşma.',
                    'KPSS ya da YDS gibi şartları ilanla karşılaştır: puan türü, sınav yılı ve asgari puan.',
                    'Nitelik tablosunu hazırla: bölüm, sertifika, deneyim yılı ve varsa ehliyet gibi şartları tek tek işaretle.',
                    'İlanın başvuru süresini ve saatini takvimine yaz.'])]),
      ('Belgelerin nasıl iletildiğine dikkat', [
         'Platformun SSS sayfasına göre kurumlar, e-Devlet üzerinden onaylı bilgi ve belgelere doğrudan erişir ve başvuruda '
         'istenen belgeler ilgili kuruma otomatik iletilir. Fiziksel evrak gönderme gerekliliği yoktur.',
         'Bu, e-Devlet kayıtlarının doğru olması gerektiği anlamına gelir. Mezuniyet, askerlik ve iletişim bilgilerinde hata '
         'varsa başvurudan önce kaynağında düzelt. Deneyim belgesi, sertifika ya da kuruma özgü ek belge gibi e-Devlet’te '
         'bulunmayan bir şey isteniyorsa ilan metninde nasıl iletileceği yazar; sonradan istenebilir.']),
      ('Başvurudan sonra', [
         'Platforma göre adaylar, e-Devlet şifresiyle giriş yaparak başvuru sonuçlarını, değerlendirme ve yerleştirme aşamalarını '
         've kurumların geri bildirimlerini takip edebilir. Sınava çağrı ve sonuç duyuruları ilanda belirtilen yerde, çoğu '
         'zaman kurumun internet sitesinde yayımlanır.',
         'KPSS ya da YDS gibi şartlar platformda değişmez. Mevzuattaki şartlar aynen uygulanır; yani KPSS isteyen bir ilanda '
         'puanın kurum tarafından doğrulanır. Platformda referans eklenebilecek bir aşama da yoktur.']),
      ('Platform neyi yapmaz?', [
         'Platformun SSS sayfası net bir sınır çizer: Cumhurbaşkanlığı işe alım süreçlerine karışmaz. Seçme, işe alım ve yerleştirme '
         'her kurumun kendi mevzuatına göre yürüttüğü bir iştir. KPSS ya da YDS gibi şartlar da değişmez. Bu yüzden bir ilanın '
         'adil olup olmadığı, kaç kişinin alınacağı ya da sınav sonucuna itiraz gibi konuların muhatabı Kariyer Kapısı değil, '
         'ilanı yayımlayan kurumdur.',
         'KPSS Tercihi’nde ilan sayfalarında kadro kadro koşulları ve resmî ilan bağlantısını görebilirsin. Başvurmadan önce '
         'bağlantıdan resmî ilana gidip tarih ve şartları orada doğrula; bir özet ile resmî metin arasında fark çıkarsa '
         'resmî metin geçerlidir.']),
      ('Üç kanalı yan yana koy', [
         ('madde', ['Kariyer Kapısı: e-Devlet şifresiyle giriş, kurum ilanları, başvuruda istenen belgelerin e-Devlet üzerinden '
                    'kuruma iletilmesi. Platform kullanıcıya ücretsizdir.',
                    'ÖSYM aday işlemleri: merkezi yerleştirme tercihi. Dönem başına en fazla 30 kadro, yerleştirme ücreti, kesin '
                    'tercih tarihleri ve tercih süresi bitince değişiklik yapılamaması.',
                    'İŞKUR: kamu işçi alımları. Başvuru süresi beş gün, ADNKS adresi esas, önlisans ve lisansta KPSS, alt '
                    'düzeylerde noter kurası.']),
         'Yani aynı gün hem ÖSYM’de tercih yapıp hem Kariyer Kapısı’ndan sözleşmeli ilanına başvurmak mümkündür, ama her biri ayrı '
         'kural seti ve ayrı süre takvimiyle yürür. Birini bitirdim diye diğerinin süresini kaçırma.']),
      ('Başvurudan sonra seni ne bekler?', [
         'Pek çok ilanda başvuru sonrası adaylar belirli bir formüle göre sıralanır, en üstten belirli sayıda aday sözlü ya da '
         'uygulamalı sınava çağrılır ve yerleştirme sınav başarı sırasına göre yapılır. Örnek olarak bir bakanlık bilişim '
         'ilanında 11 pozisyon için toplam 110 aday sınava çağrılacağı yazıyordu; pozisyon başına on kat. Kaç kişinin '
         'çağrılacağı ilanda yazar.',
         'Sınava çağrıldığında neyle gideceğin, hangi saatte ve nerede olacağın bilgisi kurumun duyurusunda yer alır. Platformdaki '
         'değerlendirme aşamasını takip etmekle birlikte kurumun kendi internet sitesine de bak. Sınav bilgisi çoğu zaman '
         'kurumun sitesinde yayımlanır.']),
      ('Örnek: süre ve yoğunluk', [
         'Örnek ilan: bir bakanlığın Mart 2026’da yayımladığı sözleşmeli bilişim personeli ilanında başvurular 13 Mart ile 29 Mart '
         'arasında alındı; 2024’te yayımlanan başka bir ilanda 11 Eylül ile 25 Eylül arasında. Yani iki hafta civarında bir pencere.',
         'Süre iki hafta civarındayken şifre yenilemek, e-Devlet bilgisini düzelttirmek ya da eksik bir belgeyi tamamlamak için '
         'zaman ayırmak zorunda kalmak başvuruyu riske atar. İlan açılmadan önce giriş yapıp bilgilerini kontrol etmek, süreyi '
         'rahat kullanmanı sağlar.']),
      ('Sık yapılan hatalar', [
         ('madde', ['Başvuru adımını yarıda bırakmak.',
                    'Bir kadroya başvurup şartı taşımadığını ilan okurken fark etmek.',
                    'Yanlış puan türüyle ya da süresi dolmuş sonuçla başvurmak.',
                    'Sınav duyurusunu yalnızca platformda aramak. Kurumun kendi sitesine de bak.',
                    'Başka kanaldan yürüyen işleri (ÖSYM tercihi, İŞKUR işçi ilanı) Kariyer Kapısı’nda aramak.'])])],
     [('Başvuru belgeleri ve hatalar', 'rehber/basvuru-belgeleri-ve-hatalar/'), ('Kamu işçi alımları', 'rehber/kamu-isci-alimi/'),
      ('Açık ilanlar', '#ilanlar')]),
]

NOT = ('Bu yazı genel bilgi amaçlıdır; kurallar ilandan ilana ve zamanla değişebilir. Başvurmadan önce her zaman ilanın resmî '
       'metnini ve ilgili mevzuatı esas al.')

# Açık ilan bloğu: slug -> (bakılacak alan, aranacak kelimeler). Eşleşme Türkçe harfler katlanarak ve küçük harfle yapılır.
ACIK_KURALLARI = {
    'belediye-memur-alimi': ('kurum', ('belediye',)),
    'sozlesmeli-bilisim-personeli': ('baslik', ('bilisim', 'yazilim', 'sistem uzmani')),
    'kamu-isci-alimi': ('baslik', ('isci',)),
    'sozlesmeli-personel-4b': ('baslik', ('sozlesmeli',)),
}
ACIK_EN_COK = 5
_KATLA = str.maketrans('ıüşöçğ', 'iusocg')


def katla(metin):
    """Türkçe harfleri ASCII'ye indirip küçültür ('İŞÇİ' -> 'isci')."""
    return str(metin or '').replace('İ', 'i').replace('I', 'ı').lower().translate(_KATLA)


def _eslesir(slug, kayit):
    alan, kelimeler = ACIK_KURALLARI[slug]
    if alan == 'kurum':
        metin = katla(kayit.get('kurum'))
    else:
        metin = katla(' '.join([str(kayit.get('manset') or '')] + [str(u) for u in (kayit.get('unvanlar') or [])]))
    if slug == 'kamu-isci-alimi':
        return re.search(r'\bisci', metin) is not None
    return any(k in metin for k in kelimeler)


def acik_ilanlar(slug, ilanlar, sayfali=None, noindex=None, simdi=None, en_cok=ACIK_EN_COK):
    """Slug'a uyan, başvurusu açık ilanlar (en yakın son tarih önce). Kural yoksa ya da eşleşme yoksa boş liste.

    Saf fonksiyondur: ana sayfadaki statik listeyle (statik_icerik.sec) aynı dışlamaları uygular – kopya, kurum içi, akademik,
    sayfası olmayan, dizinlenmeyen ve süresi geçmiş ilanlar girmez. `sayfali` verilmezse listedeki her ilanın sayfası var sayılır."""
    if slug not in ACIK_KURALLARI or not ilanlar:
        return []
    import statik_icerik as si
    simdi = simdi or datetime.now(si.TR)
    if sayfali is None:
        sayfali = {k.get('key') for k in ilanlar}
    adaylar = si.sec(ilanlar, sayfali, noindex or set(), simdi, en_cok=len(ilanlar))
    return [k for k in adaylar if _eslesir(slug, k)][:en_cok]


def acik_html(liste, esc):
    """'Şu an açık ilanlar' bölümü; liste boşsa boş metin (bölüm hiç yazılmaz)."""
    if not liste:
        return ''
    import statik_icerik as si
    satirlar = ''.join(
        f'<li><a href="../../ilan/{esc(k["key"])}/">{esc(k.get("manset") or "Kamu ilanı")}</a>'
        f' <span class="muted">· {esc(k.get("kurum") or "Kurum belirtilmemiş")} · Son başvuru: {esc(si._tarih_yazi(k["son_tarih"]))}</span></li>'
        for k in liste)
    return (f'<section class="bolum"><h2>Şu an açık ilanlar</h2><ul>{satirlar}</ul>'
            '<p class="muted">Son başvuru tarihi en yakın olanlar üstte. Başvurmadan önce ilanın kendi sayfasındaki şartları oku.</p></section>')


def _paragraf(p, esc):
    if isinstance(p, tuple) and p[0] == 'madde':
        return '<ul>' + ''.join(f'<li>{esc(m)}</li>' for m in p[1]) + '</ul>'
    return f'<p>{esc(p)}</p>'


def sayfa(r, base, acik=None):
    """`acik`: acik_ilanlar() sonucu (liste ya da None). Boşsa 'Şu an açık ilanlar' bölümü eklenmez."""
    import site_uret as su
    slug, baslik, aciklama, giris, bolumler, ilgili = r
    canonical = f'{base}rehber/{slug}/'
    kok = '../../'
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': baslik, 'description': aciklama,
          'inLanguage': 'tr', 'datePublished': YAYIN, 'dateModified': GUNCELLEME, 'mainEntityOfPage': canonical,
          'author': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base},
          'publisher': {'@type': 'Organization', 'name': 'KPSS Tercihi', 'url': base}}
    govde = ''.join(f'<section class="bolum"><h2>{su.esc(h)}</h2>' + ''.join(_paragraf(p, su.esc) for p in ps) + '</section>'
                    for h, ps in bolumler)
    govde += acik_html(acik, su.esc)
    bag = ''.join(f'<li><a href="{kok}{su.esc(y)}">{su.esc(a)}</a></li>' for a, y in ilgili)
    govde += (f'<section class="bolum"><h2>İlgili sayfalar</h2><ul>{bag}<li><a href="../">Tüm rehberler</a></li></ul></section>'
              f'<p class="kp-note">{su.esc(NOT)}</p>')
    html = (su.sayfa_basi(f'{baslik} | KPSS Tercihi', aciklama, su.esc(canonical), kok, 'article',
                          ek_head=f'<meta property="og:url" content="{su.esc(canonical)}"><script type="application/ld+json">'
                                  + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>')
            + f'<body class="kurum-page"><a class="skip" href="#icerik">İçeriğe geç</a>{su.ust_html(kok)}'
            + '<section class="kp-hero"><div class="wrap"><nav class="crumbs" aria-label="Konum"><a href="../../">Ana sayfa</a>'
              '<span aria-hidden="true">/</span><a href="../">Rehberler</a></nav>'
            + f'<span class="eyebrow">Rehber</span><h1>{su.esc(baslik)}</h1><p>{su.esc(giris)}</p>{su.kunye_html(kok, YAYIN, GUNCELLEME)}</div></section>'
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


def yaz(docs, base, ilanlar=None, sayfali=None, noindex=None, simdi=None):
    """Rehber sayfalarını yazar; site haritası için adresleri döner.

    `ilanlar` (ana sayfaya giren görünen ilan kayıtları), `sayfali` (sayfası olan ilan anahtarları), `noindex` (haritada olmayanlar)
    ve `simdi` verilirse bazı yazıların sonuna eşleşen açık ilanlar eklenir; verilmezse yazılar yalnız sabit içerikle üretilir."""
    from pathlib import Path
    docs = Path(docs)
    adresler = []
    url, html = hub(base)
    (docs / 'rehber').mkdir(parents=True, exist_ok=True)
    (docs / 'rehber' / 'index.html').write_text(html, encoding='utf-8')
    adresler.append(url)
    for r in REHBERLER:
        acik = acik_ilanlar(r[0], ilanlar, sayfali, noindex, simdi) if ilanlar else None
        url, html = sayfa(r, base, acik)
        (docs / 'rehber' / r[0]).mkdir(parents=True, exist_ok=True)
        (docs / 'rehber' / r[0] / 'index.html').write_text(html, encoding='utf-8')
        adresler.append(url)
    import uygulamali_rehberler as ur
    adresler.extend(ur.yaz(docs, base))
    return adresler
