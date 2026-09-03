# Aşama 10 — Şahin IR v1 kapsam envanteri

Bu belge Aşama 10'un kalan IR/semantic lowering işini fail-closed biçimde izler. Bir düğüm burada destekleniyor görünse bile yalnızca ilgili lowering, backend doğrulama, semantik eşdeğerlik ve regression testleri CI üzerinde yeşilse tamamlanmış sayılır.

## Doğrulanmış ifade kapsamı

| AST düğümü | IR v1 durumu | Not |
|---|---|---|
| `Literal` | ✅ | `const` ile kararlı literal kodlaması |
| `Name` | ✅ | `load` |
| `Unary` | ✅ | `unary` |
| `Binary` (kısa devre dışı) | ✅ | `binary` |
| `Binary` (`ve` / `veya`) | ✅ | Lazy RHS `branch/label/jump`, internal join alanı ve control-flow equivalence exact-head CI ile doğrulandı |
| `Predicate` | ✅ | `yok` / `boş` / `boş_değil` açık `predicate` opcode'u, backend fail-closed şeması ve equivalence testleriyle main üzerinde doğrulandı |
| `Member` | ✅ | Açık `member` opcode'u, target-temp definite-definition, WASM/native fail-closed şeması ve equivalence regression testleri exact-head CI ile doğrulandı |
| `Call` | ✅ | Doğrudan adlandırılmış `akış` için `call` opcode'u; hedef/arity doğrulaması, bağımsız çağrı frame'i, lexical capture ve dönüş semantiği WASM/native + equivalence CI ile doğrulandı |
| `RangeExpression` | ✅ | Explicit `range` opcode'u; WASM/native şema + CFG/use-def doğrulaması ve inclusive ileri/geri equivalence exact-head CI ile doğrulandı |
| `Pipeline` | ✅ | Explicit `pipeline` opcode'u; `ilk`/`sırala`/`seç` stage allow-listesi, arity/use-def/result şeması ve runtime ↔ WASM/native equivalence CI ile doğrulandı |

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
| `TryStatement` | 🚧 | Sıradaki aktif dilim: hata control-flow, error binding scope ve başarılı/hatalı yollar için açık fail-closed ABI tanımlanacak |

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
11. 🚧 `TryStatement` hata control-flow/error-binding sözleşmesini küçük ayrı PR ile ekle; ardından kalan statement/Command/Declaration düğümlerini kapat.
12. Tam AST/semantic kapsam matrisi, olumlu/olumsuz/regression/property/security testleri ve Python 3.11/3.12/3.13 + gerçek `.shn` smoke tamamen yeşil olduğunda Aşama 10'u `%94` olarak kapat.

## Kalite ilkeleri

- Desteklenmeyen düğüm sessizce atlanmaz; `IRLoweringError` ile reddedilir.
- Kısa devre semantiği eager RHS ile taklit edilmez.
- WASM/native adapter capability yüzeyi varsayılan-kapalı kalır.
- Unknown opcode/version, malformed instruction, use-before-definition ve duplicate-temp fail-closed kalır.
- `Call` yalnız doğrulanmış `IRFlow` hedefi, doğru arity ve doğrulanmış lexical capture/return ABI ile kabul edilir.
- Iterator consumer opcode'ları yalnız doğrulanmış `iter_begin` handle'ı ve CFG definite-definition kanıtı ile kabul edilir.
- Match pattern sırası ve first-match davranışı backend optimizasyonlarıyla değiştirilemez.
- Benchmark veya performans hedefi semantik eşdeğerlik kontrolünü devre dışı bırakamaz.
