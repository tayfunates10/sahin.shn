# Aşama 10 — Şahin IR v1 kapsam envanteri

Bu belge Aşama 10'un kalan IR/semantic lowering işini fail-closed biçimde izler. Bir düğüm burada destekleniyor görünse bile yalnızca ilgili lowering, backend doğrulama, semantik eşdeğerlik ve regression testleri CI üzerinde yeşilse tamamlanmış sayılır.

## Doğrulanmış ifade kapsamı

| AST düğümü | IR v1 durumu | Not |
|---|---|---|
| `Literal` | ✅ | `const` ile kararlı literal kodlaması |
| `Name` | ✅ | `load` |
| `Unary` | ✅ | `unary`; runtime hata payload/string ABI'si kaynak provenance ile doğrulandı |
| `Binary` (kısa devre dışı) | ✅ | `binary`; top-level ve flow-local runtime hata payload/string ABI'si kaynak provenance ile doğrulandı |
| `Binary` (`ve` / `veya`) | ✅ | Lazy RHS `branch/label/jump`, internal join alanı ve control-flow equivalence exact-head CI ile doğrulandı |
| `Predicate` | ✅ | `yok` / `boş` / `boş_değil` açık `predicate` opcode'u, backend fail-closed şeması ve equivalence testleriyle main üzerinde doğrulandı |
| `Member` | ✅ | Açık `member` opcode'u, target-temp definite-definition, WASM/native fail-closed şeması, runtime/backend equivalence ve kaynak-konumlu hata payload ABI'si doğrulandı |
| `Call` | ✅ | Doğrudan adlandırılmış `akış` için `call` opcode'u; hedef/arity doğrulaması, bağımsız çağrı frame'i, lexical capture, dönüş semantiği ve taşan hata için call-site provenance doğrulandı. Geçersiz hedef/arity backend runtime payload'ı uydurulmadan semantik/IR sınırında fail-closed reddedilir. |
| `RangeExpression` | ✅ | Explicit `range` opcode'u; WASM/native şema + CFG/use-def doğrulaması, inclusive ileri/geri equivalence ve kaynak-konumlu runtime hata payload ABI'si doğrulandı |
| `Pipeline` | ✅ | Explicit `pipeline` opcode'u; `ilk`/`sırala`/`seç` stage allow-listesi, arity/use-def/result şeması, runtime ↔ WASM/native equivalence ve kaynak-konumlu hata payload ABI'si doğrulandı |

## Doğrulanmış statement kapsamı

| AST düğümü | IR v1 durumu | Not |
|---|---|---|
| `Assignment` | ✅ | `store` |
| `Binding` | ✅ | `bind` |
| `Write` | ✅ | `write` |
| `ExpressionStatement` | ⏳ | Semantik geçerliliği açıkça modellenene kadar fail-closed |
| `FieldDeclaration` | ⏳ | Henüz lowering sözleşmesi yok |
| `Command` | 🚧 | `yaz`/`bildir` yalnız referans runtime ile aynı ilk-argüman semantiğiyle doğrulandı; host/capability etkili diğer komutlar fail-closed |
| `Declaration` (`akış`) | ✅ | `IRFlow`; parametre/type metadata, lexical captures, `return`, recursion için predeclaration ve backend flow doğrulaması exact-head CI ile doğrulandı |
| `Declaration` (diğer) | ⏳ | Kendi runtime/backend ABI sözleşmesi olmadan fail-closed |
| `IfStatement` | ✅ | Deterministik `branch/label/jump`, lexical scope ve control-flow equivalence doğrulandı |
| `ForEach` | ✅ | Iterator IR, lexical loop scope, terminator-aware `bitir`, WASM/native origin/use-def doğrulaması ve referans runtime ↔ backend equivalence exact-head CI ile doğrulandı |
| `MatchStatement` | ✅ | Subject tek değerlendirme, kaynak sıralı pattern karşılaştırması, first-match `binary ==` + `branch/label/jump` ve WASM/native equivalence exact-head CI ile doğrulandı |
| `TryStatement` | ✅ | AST lowering, `try_guard`/`catch`, lexical handler scope, normal-path handler bypass, malformed-handler fail-closed doğrulaması, başarılı/hatalı/nested handler yolları ve mevcut IR v1 kapsamındaki gözlemlenebilir hata payload/string ABI eşdeğerliği doğrulandı. |

## Control-flow ve çağrı sözleşmesi

- ✅ IR v1 için `label`, `jump`, `branch` primitive sözleşmesi tanımlandı.
- ✅ Yinelenen/geçersiz label, tanımsız hedef ve tanımsız branch temp kullanımı fail-closed doğrulanıyor.
- ✅ WASM/native adapter entegrasyonu `main` üzerinde doğrulandı.
- ✅ Gerçek `IfStatement` lowering lexical scope korunarak doğrulandı.
- ✅ Kısa devreli `ve` / `veya` lazy RHS control-flow lowering ve kullanıcı ad alanından ayrılmış internal join slotları doğrulandı.
- ✅ `IRFlow` + `call` + `return` ABI; flow adı/parametre/type/capture şeması, call target/arity ve flow-body definite-definition kontrolleriyle fail-closed doğrulandı.
- ✅ Referans runtime ↔ WASM/native plan equivalence yürütücüsü bağımsız çağrı frame'i, parametre aktarımı, dönüş değeri ve lexical capture okuma/yazma semantiğini doğruluyor.
- ✅ `RangeExpression` için inclusive ileri/geri tuple semantiği iki adapter planıyla eşdeğerlik testlerinden geçti.
- ✅ `Pipeline` stage zinciri ve `ilk`/`sırala`/`seç` semantiği iki adapter planıyla eşdeğerlik testlerinden geçti.
- ✅ `ForEach` iterable kaynağını tek kez snapshot ediyor; iterator state, lexical loop scope, ters aralık sırası ve `bitir` semantiği WASM/native plan equivalence ile doğrulandı.
- ✅ Iterator consumer opcode'ları yalnız `iter_begin` tarafından üretilmiş handle üzerinde kabul ediliyor; malformed ve use-before-definition yolları fail-closed reddediliyor.
- ✅ `MatchStatement` subject'i bir kez değerlendiriyor; patternler kaynak sırasıyla yalnız erişilen path üzerinde değerlendirilip ilk eşleşmede end label'ına ilerliyor.
- ✅ Match case `yaz`/`bildir` komutları referans runtime gibi yalnız ilk argümanı değerlendiriyor; diğer case Command türleri fail-closed kalıyor.
- ✅ `TryStatement` korunan gövde ve handler'ı ayrı lexical scope'larda indiriyor; normal başarı yolu handler'a fallthrough yapmadan açık join'e ilerliyor.
- ✅ `try_guard` / `catch` backend sözleşmesi özgün try-aware CFG üzerinde doğrulanıyor; malformed handler/catch ve normal handler girişi fail-closed reddediliyor.
- ✅ Try başarı, sıfıra bölme hata yolu ve nested-try inner-handler önceliği referans runtime ↔ WASM/native plan equivalence testlerinden geçti.
- ✅ `Binary`, `Unary`, `Member`, `RangeExpression` ve `Pipeline` runtime hata yolları top-level/flow source provenance ile kaynak-konumlu `RuntimeErrorSHN` payload/string çıktısında referans runtime ↔ WASM/native eşdeğerliğine sahip.
- ✅ Flow dışına taşan `RuntimeErrorSHN` için top-level ve flow-local call-site provenance/stack-frame zinciri referans runtime ile eşdeğer.
- ✅ Yanlış doğrudan call target/arity runtime payload'ı uydurulmadan semantik/IR sınırında fail-closed reddediliyor.
- ✅ Adapter entegrasyonu herhangi bir yeni capability/import açmıyor.

## Kalan kabul sırası

1. ✅ Control-flow IR primitives ve label/jump doğrulama sözleşmesini tanımla.
2. ✅ WASM/native adapter doğrulamasını yeni control-flow opcode'ları için fail-closed genişlet.
3. ✅ `IfStatement` semantiğini deterministik control-flow olarak indir ve exact-head CI ile doğrula.
4. ✅ Kısa devreli `ve` / `veya` semantiğini eager RHS üretmeden indir ve exact-head CI ile doğrula.
5. ✅ Referans runtime ↔ WASM/native plan semantik eşdeğerliğini control-flow kaynaklarıyla genişlet.
6. ✅ `Predicate`, `Member`, `Call` + `akış` `Declaration` ABI ve backend/equivalence entegrasyonlarını tamamla.
7. ✅ `RangeExpression` lowering + backend/equivalence kalite kapısını tamamla.
8. ✅ `Pipeline` lowering + backend/equivalence kalite kapısını tamamla.
9. ✅ `ForEach` IR lowering/control-flow + WASM/native adapter/equivalence kalite kapısını tamamla.
10. ✅ `MatchStatement` subject-once/first-match control-flow + backend equivalence kalite kapısını tamamla.
11. ✅ `TryStatement` control-flow/error-binding/backend handler ve mevcut IR v1 runtime hata payload/string ABI eşdeğerliğini kapat.
12. ⏳ Kalan `ExpressionStatement`, `FieldDeclaration`, diğer `Command` ve diğer `Declaration` düğümlerini kendi semantik/ABI/capability sözleşmeleriyle fail-closed biçimde kapat.
13. Tam AST/semantic kapsam matrisi, olumlu/olumsuz/regression/property/security testleri ve Python 3.11/3.12/3.13 + gerçek `.shn` smoke tamamen yeşil olduğunda Aşama 10'u `%94` olarak kapat.

## Kalite ilkeleri

- Desteklenmeyen düğüm sessizce atlanmaz; `IRLoweringError` ile reddedilir.
- Kısa devre semantiği eager RHS ile taklit edilmez.
- WASM/native adapter capability yüzeyi varsayılan-kapalı kalır.
- Unknown opcode/version, malformed instruction, use-before-definition ve duplicate-temp fail-closed kalır.
- `Call` yalnız doğrulanmış `IRFlow` hedefi, doğru arity ve doğrulanmış lexical capture/return ABI ile kabul edilir.
- Iterator consumer opcode'ları yalnız doğrulanmış `iter_begin` handle'ı ve CFG definite-definition kanıtı ile kabul edilir.
- Match pattern sırası ve first-match davranışı backend optimizasyonlarıyla değiştirilemez.
- Try handler yalnız doğrulanmış exceptional kenardan erişilebilir; normal jump/branch/fallthrough ile handler girişi yasaktır.
- Mevcut IR v1 kapsamındaki gözlemlenebilir hata değeri referans runtime ile payload/string eşdeğerliği kanıtlanmadan backend desteği tamamlandı sayılmaz.
- Benchmark veya performans hedefi semantik eşdeğerlik kontrolünü devre dışı bırakamaz.
