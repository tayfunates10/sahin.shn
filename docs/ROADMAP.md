# Şahin Geliştirme Roadmap'i

Bu belge Şahin'in %100 tamamlanma yolunu ve her aşamadaki kalite kapılarını tanımlar. Bir aşama yalnızca kod yazıldığı için tamamlanmış sayılmaz; ilgili testler yeşil olmadan ilerleme yüzdesi artırılmaz.

## İlerleme modeli

Toplam ilerleme: **%32**

| Aşama | Ağırlık | Durum | Kabul kapısı |
|---|---:|---|---|
| 0. Proje temeli | %3 | ✅ Tamamlandı | Repo, paket iskeleti, CI başlangıcı |
| 1. Dil anayasası + sözdizimi çekirdeği | %7 | ✅ Tamamlandı | Özgünlük ilkeleri, UTF-8, ilk grammar, lexer smoke testleri |
| 2. Parser + ifade sistemi + semantik çekirdek | %12 | ✅ Tamamlandı | Blok AST, precedence, bağlama, koşul/yineleme, sembol çözümleme, tip çıkarımı |
| 3. Çalıştırma motoru + hata modeli | %10 | ✅ Tamamlandı | Scope, çağrı modeli, kontrol akışı, deterministik runtime, diagnostics |
| 4. Tip sistemi + güvenlik | %10 | 🚧 Sıradaki | Statik tipler, nullable/yok güvenliği, capability modeli, type/property testleri |
| 5. Standart kütüphane | %9 | ⏳ | metin/sayı/liste/zaman/dosya/ağ/json/şifreleme temel API'leri |
| 6. Arayüz + görünüm motoru | %11 | ⏳ | Şahin UI ağacı, stil sistemi, olaylar, erişilebilirlik, browser hedefi |
| 7. Sunucu + API + veri motoru | %11 | ⏳ | HTTP, servis/uç modeli, migration, sorgu planı, transaction, güvenli veri erişimi |
| 8. Modül + paket ekosistemi | %7 | ⏳ | modüller, paket manifesti, lockfile, registry protokolü, imza/doğrulama |
| 9. Araç zinciri | %7 | ⏳ | formatter, linter, test runner, LSP, debugger, REPL, editor entegrasyonu |
| 10. WASM/native backend + performans | %7 | ⏳ | Şahin IR, WASM, native prototip, benchmark/regression kapıları |
| 11. Self-hosting | %3 | ⏳ | Derleyicinin kritik bölümünün Şahin ile derlenmesi, bootstrap doğrulaması |
| 12. 1.0 sertifikasyonu | %3 | ⏳ | fuzz/property/security/compatibility/performance testleri ve release checklist |

## Kalite kuralları

1. Her geliştirme ayrı branch ve PR ile yapılır.
2. CI tamamen yeşil olmadan PR `main` dalına alınmaz.
3. Başarısız test silinmez, skip edilmez veya eşik düşürülerek geçirilmez; kök neden düzeltilir.
4. Her dil özelliğinde en az bir olumlu ve bir olumsuz test bulunur.
5. Parser ve semantik katmanda regression + golden/snapshot testleri tutulur.
6. Unicode için Türkçe `ç, ğ, ı, İ, ö, ş, ü` karakterleri ve Unicode normalizasyon varyantları test edilir.
7. Güvenlik etkili özelliklerde property/fuzz testleri zorunludur.
8. README ve bu roadmap yalnızca doğrulanmış ilerlemeyi gösterir.
9. Şahin AST/IR başka bir dilin AST'sinin Türkçeleştirilmiş biçimi olmayacaktır.
10. Bootstrap uygulama dili değişse bile Şahin'in grammar/AST/semantik sözleşmesi korunur.

## Aşama 2 — Parser + semantik çekirdek ✅

### 2A — AST genişletme (%10 → %12)
- [x] Blok düğümü
- [x] `uygulama`, `ekran`, `görünüm`, `akış`, `kayıt`, `uç`, `iş`, `olay`
- [x] Kaynak konum bilgisi
- [x] Şahin'e özgü `Binding` düğümü (`<-`, normal `=` atamasından ayrı)

### 2B — İfade sistemi (%12 → %15)
- [x] Prefix/unary ifadeler
- [x] Binary precedence
- [x] Üye erişimi
- [x] Çağrı
- [x] `..` aralık
- [x] `|` veri hattı
- [x] Parantezli ifade

### 2C — Kontrol akışı grammarı (%15 → %18)
- [x] `... ise`
- [x] `yoksa`
- [x] `her ... içinden ...`
- [x] `duruma göre`
- [x] `bitir` komutunun AST olarak kabulü

### 2D — Semantik analiz (%18 → %20)
- [x] Sembol tablosu
- [x] Scope çözümleme
- [x] Tanımsız isim teşhisi ve yakın isim önerisi
- [x] Yeniden tanımlama/binding kuralları
- [x] İlk tip çıkarımı

### 2E — Sertifikasyon (%20 → %22)
- [x] Golden parser testleri
- [x] Unicode NFC normalizasyon testleri
- [x] Deterministik 100-varyant Unicode property testi
- [x] Hatalı girinti testleri
- [x] Diagnostic satır/sütun konum testleri
- [x] Karşılaştırma operatörleri regression testi (`<=`, `>=`, `==`, `!=`)
- [x] CI 3.11/3.12/3.13 tamamen yeşil

## Aşama 3 — Çalıştırma motoru + hata modeli ✅

Hedef ilerleme: **%22 → %32**

- [x] Lexical scope ve çalışma çerçeveleri
- [x] `akış` çağırma, parametre bağlama ve `ver`
- [x] Binary/unary ifade yürütme
- [x] `ise/yoksa`, `her`, `duruma göre`, `bitir`
- [x] `dene/olmazsa` ve Şahin hata nesnesi
- [x] `Binding` kaynak çözümü ve değişmez bağlama sözleşmesi
- [x] Pipeline yürütme çekirdeği (`seç`, `sırala`, `ilk`)
- [x] Kaynak konumlu runtime stack trace
- [x] Deterministik yürütme testleri
- [x] Runtime olumlu/olumsuz/regression testleri
- [x] CI 3.11/3.12/3.13 tamamen yeşil

### Aşama 3 hata-düzeltme kaydı

İlk CI turunda iki test, runtime nedeniyle değil v0.1 grammarında çıplak `akış()` çağrısının statement olarak desteklenmemesi nedeniyle parserda kırıldı. Testler mevcut geçerli çağrı ifadesi sözleşmesi (`sonuç = akış()`) üzerinden yürütülecek şekilde düzeltildi; ikinci CI turunda üç Python matrisi de tamamen yeşil geçti. Çıplak çağrı statement desteği ayrı grammar genişlemesi olarak korunacaktır.

## Aşama 4 — Tip sistemi + güvenlik

Hedef ilerleme: **%32 → %42**

- [ ] Nominal/temel tip sözleşmesi (`yazı`, `sayı`, `ondalık`, `para`, `evet_hayır`, `yok`)
- [ ] Akış parametre ve dönüş tipi doğrulaması
- [ ] Atama ve `Binding` tip bütünlüğü
- [ ] `yok`/nullable güvenliği
- [ ] Union/opsiyonel tip için Şahin'e özgü sade model
- [ ] Güvenli daraltma (flow-sensitive narrowing)
- [ ] Capability tabanlı dosya/ağ/veri erişim güvenliği taslağı
- [ ] Statik diagnostic kodları ve Türkçe hata açıklamaları
- [ ] Type property/regression testleri
- [ ] Güvenlik olumsuz testleri
- [ ] CI 3.11/3.12/3.13 tamamen yeşil

## Sonraki kapı

Aşama 4, yukarıdaki maddeler ve CI doğrulanmadan %42 olarak işaretlenmeyecektir.
