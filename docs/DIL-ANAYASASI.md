# Şahin Dil Anayasası v0.1

Bu belge Şahin'in tasarım kararlarını koruyan temel ilkeleri tanımlar.

## 1. Şahin bir çeviri dili değildir

Şahin; Python, JavaScript, HTML, CSS, PHP veya SQL anahtar kelimelerinin Türkçeye çevrilmiş biçimi olmayacaktır. Başka dillerden fikir alınabilir ancak kullanıcıya sunulan programlama modeli özgün ve tutarlı olmalıdır.

## 2. Tek dil, tek zihinsel model

Arayüz, görünüm, olay, veri, servis, otomasyon ve genel amaçlı programlama aynı isimlendirme ve blok kurallarını paylaşır. Kullanıcı aynı uygulama için birden fazla sözdizimi öğrenmek zorunda bırakılmaz.

## 3. Türkçe karakterler birinci sınıftır

`ç, Ç, ğ, Ğ, ı, I, i, İ, ö, Ö, ş, Ş, ü, Ü` tanımlayıcılarda güvenle kullanılabilir. Kaynak dosyalar UTF-8'dir. Unicode normalizasyonu derleyici tarafından merkezi olarak yapılır.

## 4. Okunabilirlik sembol ekonomisinden önce gelir

Noktalı virgül, süslü parantez ve gereksiz parantez zorunlu değildir. Bununla birlikte belirsiz doğal-dil yorumlarına izin verilmez: sözdizimi insan tarafından kolay okunmalı, parser tarafından tek anlamlı çözümlenmelidir.

## 5. Basit varsayılan, güçlü kaçış yolu

Yeni başlayan kullanıcı tip, async, bellek veya build ayrıntılarını bilmeden üretken olabilir. İleri kullanıcı aynı dil içinde açık tipler, paralellik, düşük seviyeli veri ve FFI özelliklerine erişebilir.

## 6. Güvenli varsayılanlar

- Null-benzeri değerler örtük hata kaynağı olmayacak.
- Para ve tarih gibi alanlarda uygun standart tipler bulunacak.
- Veri sorguları parametreli ve güvenli olacak.
- UI metinleri varsayılan olarak kaçışlı işlenecek.
- Tehlikeli sistem/FFI yetkileri açık izin gerektirecek.

## 7. Hatalar eğitim aracıdır

Hata mesajları yalnızca "ne bozuldu" değil, mümkünse "nerede", "neden" ve "nasıl düzeltilebilir" bilgisini verir. Türkçe tanımlayıcılarda yakın isim önerileri desteklenir.

## 8. Birinci sınıf uygulama kavramları

Şahin'in çekirdek söz varlığı genel amaçlı programlamanın yanında şu kavramları doğrudan modelleyebilir:

- `uygulama`: dağıtılabilir ürün sınırı
- `ekran`: kullanıcı arayüzü ağacı
- `görünüm`: görsel kurallar ve temalar
- `akış`: çağrılabilir davranış/iş akışı
- `olay`: zaman veya kullanıcı etkileşimi tetikleyicisi
- `kayıt`: veri modeli
- `uç`: ağ servis sınırı
- `iş`: arka plan/otomasyon görevi

Bu kavramlar HTML etiketi, CSS seçicisi, JS event listener, PHP route veya SQL tablosunun birebir karşılığı değildir; aynı semantik modelin farklı düğümleridir.

## 9. Backend bağımsızlığı

İlk bootstrap uygulaması başka bir dilde yazılabilir, ancak Şahin programlarının anlamı o bootstrap dilinin davranışına bağlı olmayacaktır. Resmî AST ve semantik belirtim kaynak gerçektir.

## 10. Uyumluluk kapısı

Yeni bir sözdizimi özelliği ancak şu sorulara olumlu cevap veriyorsa eklenir:

1. Mevcut bir özelliğin tekrarını azaltıyor mu?
2. Yeni başlayan için öğrenme yükünü düşürüyor mu?
3. Parser/formatter/LSP tarafından deterministik işlenebilir mi?
4. Büyük uygulamalarda ölçeklenebilir mi?
5. Başka bir dilin yalnızca yeniden adlandırılmış kalıbı olmaktan kaçınıyor mu?

Bu ilkeleri ihlal eden değişiklikler 1.0 öncesinde dahi kabul edilmemelidir.
