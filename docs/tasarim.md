# Ders Ofisi — Tasarım Belgesi

Tarih: 2026-11-23

## 1. Amaç ve neden

Kullanıcı ders çalışırken yanında, her birinin ayrı görevi olan ve aynı anda çalışan yapay zekâ asistanları istiyor. Bu asistanlar New York'ta yüksek katlı bir ofiste, kendi masalarında oturan karakterler olarak 3D görünecek. Amaç PDF ders materyalinden en hızlı şekilde özet, formül ve soru çıkarmak. Ayrıca sınavlara yetişip yetişemeyeceğini görmek ve eksiklerini bulup tekrar etmek. Hepsi tek ekranda olacak ve keyifli bir ortamda çalışılacak.

Kullanıcı tek kişi, kendi Windows bilgisayarında kullanacak.

## 2. Hedefler

- Tarayıcıda açılan, sabit kameralı (döndürme ve yakınlaştırma serbest, yürüme yok) 3D bir NYC ofisi.
- Ofiste dokuz asistan, her biri kendi masasında. Durumları görünür: boşta, çalışıyor (`…` balonu ve yanan ekran), bitti (✅). Asistana tıklayınca çıktısı yanda açılan bir panelde gösterilir.
- Üst çubukta ders seçimi, PDF bırakma alanı ve çalışma süresi sayacı (başlat ve duraklat) bulunur.
- Her dersin bilgisayarda bir klasörü var. Bütün çıktılar orada kalıcı olarak saklanır, ertesi gün kaldığı yerden devam edilir.
- Yapay zekâ işleri kullanıcının **Claude aboneliği** ile, Claude Code'un komut satırı aracı (`claude -p`) üzerinden yapılır. API anahtarı kullanılmaz.

## 3. Asistanlar

| # | Asistan | Ne yapar | Ne zaman çalışır | Yapay zekâ? |
|---|---|---|---|---|
| 1 | **Özetçi** | PDF'i özetler. Kendi önemli bulduğu noktaları özetin içinde ayrıca işaretler (eski 1 ve 6 birleşti). | PDF bırakılınca, otomatik | Evet |
| 2 | **Formülcü** | PDF'teki formülleri çıkarır. Her formül için ne anlama geldiğini, hangi tip soruda ve nerede kullanılacağını açıklar. | PDF bırakılınca, otomatik | Evet |
| 3 | **Süre analisti** | Derse göre toplam çalışma süresini tutar. Kalan konu ve sınav tarihine bakarak "bu hızla yetişir / yetişmez" tahminini kabaca gösterir (grafik ve bir cümle yorum). | Sürekli (süre); analiz panel açılınca | Hesap kodla yapılır. Yorum cümlesi isteğe bağlı olarak yapay zekâ ile |
| 4 | **Soru araştırmacısı** | O an seçili dersin konusuyla ilgili, yerli ve yabancı üniversitelerin sınavlarından soruları internette arar ve kaynağını gösterir. Bulamazsa kendisi kolay, orta ve zor soru yazar ve bunu açıkça belirtir. | Kullanıcı "soru bul" deyince (Pro limiti yüzünden) | Evet (web araması) |
| 5 | **Not tutucu** | Kullanıcının "önemli" dediği notları o dersin klasörüne kaydeder ve listeler. | Kullanıcı not ekleyince | Hayır |
| 6 | **Sınavcı** | Kolay, orta ve zor sorular sorar (Soru araştırmacısının sorularını da kullanır). Cevapları değerlendirir, eksik konuları ve neyi tekrar etmek gerektiğini söyler. | Kullanıcı "beni test et" deyince | Evet (çok turlu) |
| 7 | **Tekrar planlayıcı** | Sınavcı'nın bulduğu eksik konuları 1, 3 ve 7 gün sonra "bugün tekrar et" diye hatırlatır. | Ofis açılınca ve sınav bitince | Hayır |
| 8 | **Soru-cevap hocası** | Anlaşılmayan yeri sorarsın, o dersin PDF'lerine dayanarak açıklar. | Kullanıcı sorunca | Evet (çok turlu) |
| 9 | **Mola** | Süre sayacına bağlıdır. Belirli aralıklarla (varsayılan 50 dk çalışma, 10 dk mola) mola hatırlatır. | Sayaç çalışırken | Hayır |

Not: 5, 7 ve 9 numaralı asistanların yapay zekâya ihtiyacı yok. Ofiste diğerleri gibi karakter olarak görünürler, ama aboneliğin kullanım limitini harcamazlar.

## 4. Kısıtlar

- **Abonelik: Claude Pro** (kullanıcı söyledi). Limit düşük olduğu için:
  - PDF bırakılınca önce bir kez metne çevrilir (Markdown, formüller LaTeX). Bu işi Claude yapar, PDF'i 20 sayfalık parçalar halinde sırayla okur. Bu yöntem taranmış sayfaları da okur ve ek bir Python paketi gerektirmez. Metin ders klasörüne kaydedilir. 1, 2, 4, 6 ve 8 numaralı asistanlar bu metni okur, PDF'i tekrar okumaz.
  - Bir parça bitince Özetçi ve Formülcü o parça üzerinde çalışmaya başlar. Böylece ilk sonuçlar, PDF'in tamamı çevrilmeden görünür.
  - Aynı anda en fazla 2 yapay zekâ işi çalışır, fazlası sıraya girer.
  - Modeller: çevirme, Özetçi, Formülcü, Sınavcı ve Soru-cevap hocası Sonnet kullanır. Konu eşleştirme ve Soru araştırmacısı Haiku kullanır. Model adları tek bir ayar dosyasındadır, kullanıcı Max'e geçerse değiştirilebilir.
  - Soru araştırmacısı PDF bırakılınca kendiliğinden çalışmaz. Kullanıcı masasına tıklayıp "soru bul" deyince çalışır.
  - Claude limit dolu hatası verirse iş "bekliyor" durumuna geçer, ofiste o asistan uyur (💤). Kullanıcı limit açılınca "devam" der, kalan parçalardan devam edilir. Hiçbir çıktı kaybolmaz.
- **PDF'ler:** en fazla yaklaşık 150 sayfa. Metin içeren mi taranmış mı olduğu bilinmiyor, ikisi de desteklenir.
- Claude Code bilgisayarda kurulu ve aboneliğe giriş yapılmış olmalı. Ofisin çalışması için Claude Code penceresinin açık olması gerekmez.
- Windows 11 kullanılıyor ve Python 3.14 kurulu.
- Her şey yerelde çalışır. İnternete yalnızca Claude ve Soru araştırmacısının web araması çıkar.
- Sunucu yalnızca `127.0.0.1` adresini dinler, ağdaki başka cihazlar erişemez.

## 5. Yaklaşımlar

Değerlendirilen iki yol vardı:

- **A — Ofis kendi başına çalışır (seçildi).** Yerel küçük bir program hem 3D sayfayı sunar hem de her asistan işi için arka planda `claude -p` çalıştırır. Sınavcı ve Soru-cevap hocasıyla konuşmalar ofis ekranından yapılır. Artısı tek pencerede gerçek bir uygulama olması, eksisi yapımının daha uzun sürmesi.
- **B — Claude Code ofisi yönetir.** 3D sayfa sadece izleme ekranı olur. İşleri Claude Code oturumu paralel başlatır, sınav cevapları Claude Code penceresine yazılır. Daha hızlı kurulur ama hep iki pencere gerekir ve soru-cevap ofisin dışında kalır.

Kullanıcı A'yı seçti, çünkü asıl istek ofisin içinde çalışmak ve A bunu tek pencerede sağlıyor. (Claude.ai artifact olarak yapmak da düşünüldü. Bilgisayardaki ders klasörlerine erişemediği için elendi.)

## 6. Kullanıcının kararları

- Asistanlar yapay zekâ, gerçek insan değil.
- Yukarıdaki dokuz asistan (1 ile 6 birleşti; tekrar planlayıcı, soru-cevap hocası ve mola eklendi).
- Görünüm: 3D, New York'ta bir ofis.
- Kamera sabit: tıklamak yeterli, ofiste yürüme yok.
- Yapay zekâ Claude aboneliği ile çalışacak.
- Yol A.
- Abonelik: Pro. PDF'ler en fazla yaklaşık 150 sayfa.
- Konum: `C:\Users\mirac\ders-ofisi\`, ders klasörleri `ders-ofisi\Dersler\` altında.

## 7. Önerilen yapı (benim kararım, kullanıcı değiştirebilir)

**Teknoloji**
- Sunucu: Python standart kütüphanesi (`http.server`, `subprocess`, `threading`). Tek ek paket PyMuPDF, PDF'ten görüntü kesmek için kullanılır. Asistan durumları tarayıcıya Server-Sent Events ile gönderilir.
- Ön yüz: tek bir HTML sayfası ve [three.js](https://threejs.org). three.js proje içine kopyalanır, internetten yüklenmez. Ofis ve karakterler basit, low-poly geometrilerle kodda çizilir, hazır model dosyası indirilmez. NYC silüeti pencere dışında, ışıkları yanan bina blokları olarak çizilir. **Işık kullanıcının bulunduğu yerin o anki saatine göre değişir (kullanıcı söyledi; şu an İtalya'da):** bilgisayarın yerel saatine ve İtalya enlemine göre güneşin yüksekliği hesaplanır. Gündüz güneş ışığı, gün doğumu ve batımında turuncu ton, gece karanlık gökyüzü ile yanan bina pencereleri ve ofis lambaları gösterilir. Işık dakikada bir güncellenir.
**Sıra (kullanıcı söyledi):** önce 3D ofis görsel olarak yapılıp gösterilir, sonra asistanlar bağlanır.
- Yapay zekâ çağrısı: `claude -p "<görev talimatı>" --output-format json`, çalışma dizini ders klasörü. Her asistanın kendine ait bir talimat dosyası vardır (`asistanlar/ozetci.md` vb.). Çok turlu konuşmalarda (Sınavcı, Soru-cevap hocası) oturum `--resume <session_id>` ile sürdürülür. Soru araştırmacısına `WebSearch` ve `WebFetch` araçları açılır. Diğerlerine yalnızca dosya okuma ve yazma izni verilir.

**Ders klasörü düzeni**
```
Dersler/
  Fizik 1/
    ders.json          # sınav tarihi, konu listesi, toplam süre kayıtları
    pdf/               # bırakılan PDF'ler
    metin/             # PDF'lerin Markdown'a çevrilmiş hali
    ozet/              # Özetçi çıktıları (önemli noktalar işaretli)
    formuller/         # Formülcü çıktıları
    sorular/           # Soru araştırmacısının soruları (kaynak, zorluk)
    notlar.md          # Not tutucu
    sinavlar/          # Sınavcı oturumları ve sonuçları (eksik konular)
    tekrar.json        # Tekrar planlayıcı takvimi
```

**Akış**
1. `baslat.bat` dosyasına çift tıklanır. Sunucu açılır ve tarayıcıda ofis açılır.
2. Ders seçilir ya da yeni ders eklenir. İlk seferde sınav tarihi ve konu listesi girilir (Süre analisti için gerekli).
3. PDF bırakılır. Metne çevirme parça parça ilerler, Özetçi ve Formülcü her biten parçanın üzerinde çalışır.
4. Sayaç başlatılır, Mola ona göre hatırlatır.
5. Kullanıcı istediği masaya tıklayıp çıktıyı okur, not ekler, test olur ya da soru sorar.

**Ders başına bir dönemlik PDF (kullanıcı söyledi):** Her dersin genelde bir dönemlik tek notu vardır (yaklaşık 150 sayfa). Bu PDF dönem başında bir kez metne çevrilir. Sonra o dönem boyunca bütün asistanlar hep bu kayıtlı dosyaları kullanır ve PDF bir daha okunmaz.

**Ders değiştirme, karışıklık yok (kullanıcı söyledi):** Gün içinde dersler arasında geçilebilir. Örneğin Computer Science çalıştıktan 1 saat sonra Math 1'e geçmek mümkündür. Bu geçişte kurallar şöyledir:
- Her yapay zekâ işi, başlatıldığı dersin klasöründe çalışır (`claude -p` çalışma dizini o klasördür) ve yalnızca o klasörü okuyup yazabilir. Başka bir dersin dosyasını göremez.
- Ders değiştirildiğinde süren işler durmaz. Bu işler kendi dersine yazmaya devam eder, ofis ise yeni dersi gösterir. Arka planda başka derste çalışan asistanın masasında küçük bir ders etiketi görünür.
- Sınavcı ve Soru-cevap hocası konuşmaları her ders için ayrı tutulur. Math 1'e geçince Computer Science sohbeti devam etmez, ama derse geri dönülünce kaldığı yerden sürer.
- Süre sayacı derse bağlıdır. Ders değiştirilince eski dersin süresi kaydedilir ve yeni dersin sayacı başlar.

**Formüller ve önemli görseller orijinal görüntü olarak (kullanıcı söyledi):** Formüller, şekiller, grafikler ve hocanın notlarındaki önemli çizimler yazıya çevrilerek gösterilmez. Hocanın notundan kesilmiş orijinal görüntü olarak gösterilir.
- Çevirme adımında Claude her formül ve önemli görsel için sayfa numarasını ve sayfadaki yaklaşık konumunu (yüzde olarak bir kutu) kaydeder.
- Sunucu o bölgeyi PDF'ten yüksek çözünürlükte, biraz pay bırakarak keser. Görüntüyü `gorseller/<sayfa>-<no>.png` olarak ders klasörüne kaydeder.
- Formülcü, Özetçi ve Sınavcı çıktılarında bu görüntüler kendi açıklamalarının yanında yer alır. Formülcü için örnek: [formül görüntüsü] + "ne demek, hangi soruda, nerede kullanılır".
- Görüntüye tıklanınca o sayfanın tamamı açılır. Bu, kesim yanlış olursa diye bir güvencedir. Kullanıcı kesimi elle düzeltebilir.
- Teknik not (benim kararım): Python standart kütüphanesi PDF sayfasını görüntüye çeviremez. Bu yüzden tek bir paket eklenir: PyMuPDF (`pip install pymupdf`). Bu paket parçalara bölme işini de kolaylaştırır.

**PDF ile ders ilişkisi (benim kararım):**
- Özetçi, Formülcü ve Soru araştırmacısı yalnızca yeni bırakılan PDF üzerinde çalışır. Çıktılar PDF adıyla kaydedilir (`ozet/<pdf-adı>.md` gibi). Eski PDF'ler yeniden işlenmez.
- Her PDF'in metnine, ders konu listesinden hangi konuları kapsadığı yazılır (`metin/<pdf-adı>.konular.json`). Bu eşleştirmeyi çevirme adımında Claude yapar, kullanıcı panelden düzeltebilir.
- Sınavcı başlarken kullanıcı konu seçer (varsayılan: tüm ders). Sınavcı yalnızca seçilen konuları kapsayan metinleri okur. Eksik konuları yalnızca ders konu listesindeki adlarla raporlar. Tekrar planlayıcı ve Süre analisti de aynı adları kullanır.
- Soru-cevap hocası önce konu eşleştirmesine bakar, sadece ilgili metinleri okur.

**Süre analisti hesabı (kaba):** Bugüne kadar bitirilen konu sayısı bölü harcanan süre çalışma hızını verir. Kalan konular bu hızla tahmini bir süreye çevrilir. Bu süre, sınava kadar kalan günler ile son 7 günün günlük ortalama çalışmasının çarpımıyla karşılaştırılır. Bir konunun "bitti" sayılması için kullanıcı konu listesinde işaretler.

## 8. Hedef dışı

- Ofiste yürüme veya birinci şahıs kamera yok.
- Başka kullanıcılar, çoklu oyuncu, hesap sistemi ve buluta yükleme yok.
- Telefon uygulaması yok (sayfa telefonda açılabilir ama hedef bu değil).
- Sesli konuşan asistanlar yok.
- PDF dışındaki formatlar (Word, PowerPoint) ilk sürümde yok.

## 9. Başarısızlık sayılacak durumlar (anti-hedefler)

- Ofis güzel görünüyor ama bir PDF'in sonuçları çok uzun sürüyor ya da abonelik limiti tek bir oturumda bitiyor.
- 3D sahne bilgisayarı yavaşlatıp çalışmayı zorlaştırıyor. Düşük bir dizüstünde bile akıcı olmalı.
- Soru araştırmacısı internetten bulunmuş gibi uydurma soru gösteriyor. Kaynağı olmayan her soru "asistan yazdı" olarak işaretlenmeli.
- Çıktılar kayboluyor. Her çıktı bittiği anda dosyaya yazılmalı.

## 10. Yapana bırakılanlar

- Ofisin ve karakterlerin görsel detayları, renkler, ışık.
- Masaların yerleşimi.
- Panelin tasarımı (Markdown ve LaTeX gösterimi gerekli, kütüphane seçimi serbest).
- Asistan talimat metinlerinin tam ifadesi.
- Hata mesajları (ör. Claude Code kurulu değil veya giriş yapılmamış) ve yeniden deneme davranışı.
