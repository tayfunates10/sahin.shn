# Şahin Geliştirme Roadmap'i

Bu belge Şahin'in %100 tamamlanma yolunu ve kalite kapılarını tanımlar. Bir aşama yalnızca kod yazıldığı için tamamlanmış sayılmaz; testler ve CI yeşil olmadan ilerleme yüzdesi artırılmaz.

## İlerleme modeli

Toplam ilerleme: **%87**

| Aşama | Ağırlık | Durum | Kabul kapısı |
|---|---:|---|---|
| 0. Proje temeli | %3 | ✅ Tamamlandı | Repo, paket iskeleti, CI |
| 1. Dil anayasası + sözdizimi | %7 | ✅ Tamamlandı | Özgünlük, UTF-8, grammar, lexer |
| 2. Parser + semantik çekirdek | %12 | ✅ Tamamlandı | AST, precedence, bağlama, sembol/tip çıkarımı |
| 3. Runtime + hata modeli | %10 | ✅ Tamamlandı | Scope, çağrı, kontrol akışı, diagnostics |
| 4. Tip sistemi + güvenlik | %10 | ✅ Tamamlandı | `TypeSpec`, `yok` güvenliği, capability |
| 5. Standart kütüphane | %9 | ✅ Tamamlandı | metin/sayı/koleksiyon/zaman/json/dosya/ağ/kripto |
| 6. Arayüz + görünüm motoru | %11 | ✅ Tamamlandı | UI ağacı, stil, olaylar, erişilebilirlik, browser hedefi |
| 7. Sunucu + API + veri motoru | %11 | ✅ Tamamlandı | HTTP, uç, migration, sorgu, transaction |
| 8. Modül + paket ekosistemi | %7 | ✅ Tamamlandı | manifest, lockfile, registry, imza |
| 9. Araç zinciri | %7 | ✅ Tamamlandı | formatter, linter, test runner, LSP, debugger, REPL |
| 10. WASM/native + performans | %7 | 🚧 Devam ediyor | Şahin IR, WASM/native, benchmark |
| 11. Self-hosting | %3 | ⏳ | kritik derleyici bölümlerinin Şahin ile derlenmesi |
| 12. 1.0 sertifikasyonu | %3 | ⏳ | fuzz/security/compat/performance/release |

## Evrensel kalite kuralları

1. Her geliştirme ayrı branch ve PR ile yapılır.
2. CI tamamen yeşil olmadan PR `main` dalına alınmaz.
3. Başarısız test silinmez, skip edilmez veya eşik düşürülerek geçirilmez.
4. Her dil özelliğinde olumlu ve olumsuz test bulunur.
5. Parser/semantik değişikliklerinde regression + golden/snapshot testleri tutulur.
6. Türkçe Unicode ve NFC normalizasyonu ayrıca test edilir.
7. Güvenlik etkili özelliklerde property/fuzz/security testleri zorunludur.
8. README ve roadmap yalnızca doğrulanmış ilerlemeyi gösterir.
9. Şahin AST/IR başka dil AST'sinin Türkçeleştirilmiş biçimi olamaz.
10. Bootstrap dili değişse bile grammar/AST/semantik sözleşmesi korunur.

## Tamamlanan kalite kapıları

### Aşama 2 — Parser + semantik çekirdek ✅
Native Şahin AST + ayrı `Binding`, blok parserı, precedence, kontrol ifadeleri, scope/symbol çözümleme, ilk tip çıkarımı, Türkçe diagnostics, golden/Unicode/regression testleri ve Python 3.11/3.12/3.13 CI tamamlandı.

### Aşama 3 — Runtime + hata modeli ✅
Lexical scope/frame, `akış`, parametre/dönüş, kontrol akışı, pipeline runtime, `Binding` çalışma sözleşmesi, kaynak konumlu hata zinciri ve deterministik runtime regression testleri tamamlandı.

### Aşama 4 — Tip sistemi + güvenlik ✅
`TypeSpec`, birleşik/opsiyonel tipler, `X veya yok`, flow-sensitive daraltma, parametre/dönüş/atama güvenliği ve varsayılan-kapalı capability modeli tamamlandı.

### Aşama 5 — Standart kütüphane ✅
NFC güvenli metin, Decimal tabanlı sayı/para, deterministik koleksiyon, enjekte edilebilir saat, boyut sınırlı JSON, capability zorunlu dosya/ağ ve yüksek seviyeli güvenli kripto yüzeyi tamamlandı. Python 3.11/3.12/3.13 compile + test + gerçek `.shn` smoke yeşil doğrulandı.

### Aşama 6 — Arayüz + görünüm motoru ✅
Immutable/kimlikli UI ağacı, selector/DOM bağımsız görünüm modeli, tasarım tokenları, responsive kurallar, immutable state, erişilebilirlik, host-independent browser adapter ve XSS/unsafe-content fail-closed testleri tamamlandı.

### Aşama 7 — Sunucu + API + veri motoru ✅
Host-independent HTTP/uç modeli, doğrulama zinciri, `ModelMeta`/migration, SQL metni üretmeyen `QueryIR`, yapılandırılmış backend parametreleri, fail-closed transaction ve veri/ağ capability kontrolleri tamamlandı.

### Aşama 8 — Modül + paket ekosistemi ✅
Immutable manifest, deterministik lockfile, SHA-256 bütünlük, provenance/dependency-confusion koruması, deterministic semver çözümleme, signer trust/revocation, offline cache yeniden doğrulaması ve atomic optimistic-concurrency install transaction tamamlandı.

### Aşama 9 — Araç zinciri ✅
Hedef ilerleme: **%80 → %87**

- [x] Deterministik ve idempotent canonical formatter
- [x] Aynı Lexer/Parser/SemanticAnalyzer zincirini kullanan kaynak konumlu linter
- [x] Deterministik keşif yapan ve başarısız testleri gizlemeyen native test runner
- [x] Diagnostics, completion, hover, go-to-definition ve symbol bilgisi için semantic-backed LSP çekirdeği
- [x] Runtime state'ini değiştirmeden breakpoint, step ve frame/scope inspection sağlayan debugger çekirdeği
- [x] Varsayılan-kapalı capability modeli, kaynak bütçeleri ve kalıcı kontrollü scope ile REPL
- [x] Runtime hata durumunda REPL state/history atomik rollback
- [x] Başarısız `<-` binding'in sonraki girdilere sızmamasını doğrulayan regression testi
- [x] Python 3.11/3.12/3.13 compile + test + gerçek `.shn` smoke CI tamamen yeşil

### Aşama 9 doğrulama kaydı

Formatter, linter, native test runner, LSP, debugger ve REPL parçaları ayrı PR'larla tamamlandı. Son REPL kalite turunda runtime sırasında state değiştirdikten sonra hata veren bir snippet'in session state'ini sessizce kirletebildiği P1 kusuru bulundu; global frame snapshot/rollback ile kök neden düzeltildi ve iki regression testi eklendi. Düzeltmenin exact head'i Python 3.11, 3.12 ve 3.13 üzerinde compile, tüm testler ve gerçek `.shn` smoke adımlarıyla yeşil doğrulandı. PR #32 squash-merge edilerek Aşama 9 kalite kapısı kapatıldı; Issue #25 tamamlandı.

## Açık kalite kapısı

### Aşama 10 — Şahin IR + WASM/native backend + performans 🚧
Hedef ilerleme: **%87 → %94**

- [ ] Şahin'e özgü, sürümlü ve deterministik IR sözleşmesi tüm gerekli AST/semantic kapsamına genişletilmiş
- [ ] Tüm gerekli AST/semantic düğümleri fail-closed lowering ile desteklenmiş
- [x] WASM backend adapter sınırı ve mevcut IR v1 kapsamı için eşdeğerlik testleri
- [x] Native backend adapter sınırı ve mevcut IR v1 kapsamı için eşdeğerlik testleri
- [x] Mevcut adapter planlarında capability/güvenlik sınırlarının fail-closed korunduğu doğrulanmış
- [x] Tekrarlanabilir benchmark baseline'ı ve sürümlü performans raporu
- [x] Property/security/regression test paketi mevcut IR v1 ve adapter sınırları için tamamlanmış
- [ ] Tam IR/semantic lowering kapsamı sonrası Python 3.11/3.12/3.13 compile + test + gerçek `.shn` smoke ile Aşama 10 final kapısı tamamen yeşil

Doğrulanmış geliştirme dilimleri: deterministik Şahin IR çekirdeği; fail-closed WASM/native adapter sınırları; control-flow `label/jump/branch` sözleşmesi ve adapter entegrasyonu; gerçek `IfStatement` lowering ve lexical-scope korunumu; lazy RHS koruyan kısa devreli `ve/veya` lowering; `Predicate` ve `Member` lowering; `IRFlow` + `call` + `return` ABI; parametre/type metadata; lexical capture; call target/arity doğrulaması; bağımsız çağrı frame'i; flow-body definite-definition doğrulaması; flow/call için referans runtime ↔ WASM/native plan semantik eşdeğerliği; `RangeExpression` lowering + WASM/native adapter entegrasyonu + inclusive ileri/geri range semantiği; `Pipeline` lowering + `ilk`/`sırala`/`seç` WASM/native/equivalence entegrasyonu; `ForEach` IR lowering + iterator-origin/use-def WASM/native doğrulaması + lexical loop scope + terminator-aware `bitir` + runtime/backend equivalence; `MatchStatement` subject-once + kaynak sıralı first-match control-flow + `yaz/bildir` case semantiği + runtime/backend equivalence; tekrarlanabilir benchmark baseline'ı ve property/security regression paketi ayrı PR'larla doğrulandı.

Aktif geliştirme odağı tam IR/semantic lowering kapsamıdır. Mevcut IR v1 güvenli biçimde `Assignment`, `Binding`, `Write`, literal/name/unary/binary ifadeleri, `IfStatement`, kısa devreli `ve/veya`, `Predicate`, `Member`, doğrudan `Call`, `akış` `Declaration` ABI, `RangeExpression`, `Pipeline`, `ForEach` ve `MatchStatement` için lowering + backend/equivalence kapsamını destekler. `TryStatement` sıradaki aktif alt dilimdir; başarılı ve hata yolları, error binding scope ve fail-closed error ABI açıkça tanımlanacaktır. Diğer eksik düğümler kendi açık IR/control-flow/ABI sözleşmeleri tamamlanana kadar fail-closed kalır. Ayrıntılı envanter `docs/STAGE10-IR-COVERAGE.md` belgesindedir.

## Sonraki kapı

Aşama 10 Issue #33 altında devam ediyor. Sıradaki teknik dilim `TryStatement` error control-flow loweringidir; normal yol ve hata yolu ayrıştırılacak, `olmazsa hataAdı` lexical binding scope'u korunacak ve backend/equivalence katmanı hata semantiğini sessiz fallback olmadan doğrulayacaktır. Sonrasında kalan statement/Command/Declaration düğümleri ele alınacaktır. **%94** yalnızca tam IR/semantic lowering kapsamı, backend güvenliği ve tüm final CI kalite kapıları tamamlandığında gösterilecektir.
