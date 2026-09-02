# Aşama 10 — Şahin IR v1 kapsam envanteri

Bu belge Aşama 10'un kalan IR/semantic lowering işini fail-closed biçimde izler. Bir düğüm burada destekleniyor görünse bile yalnızca ilgili lowering, backend doğrulama, semantik eşdeğerlik ve regression testleri CI üzerinde yeşilse tamamlanmış sayılır.

## Doğrulanmış ifade kapsamı

| AST düğümü | IR v1 durumu | Not |
|---|---|---|
| `Literal` | ✅ | `const` ile kararlı literal kodlaması |
| `Name` | ✅ | `load` |
| `Unary` | ✅ | `unary` |
| `Binary` (kısa devre dışı) | ✅ | `binary` |
| `Binary` (`ve` / `veya`) | 🚧 | Lazy RHS `branch/label/jump` lowering bu PR'da; exact-head CI bekleniyor |
| `Predicate` | ⏳ | Henüz lowering sözleşmesi yok |
| `Member` | ⏳ | Henüz lowering sözleşmesi yok |
| `Call` | ⏳ | Çağrı/ABI sözleşmesi henüz IR v1'e taşınmadı |
| `RangeExpression` | ⏳ | Henüz lowering sözleşmesi yok |
| `Pipeline` | ⏳ | Pipeline semantiği henüz IR v1'e taşınmadı |

## Doğrulanmış statement kapsamı

| AST düğümü | IR v1 durumu | Not |
|---|---|---|
| `Assignment` | ✅ | `store` |
| `Binding` | ✅ | `bind` |
| `Write` | ✅ | `write` |
| `ExpressionStatement` | ⏳ | Semantik geçerliliği açıkça modellenene kadar fail-closed |
| `FieldDeclaration` | ⏳ | Henüz lowering sözleşmesi yok |
| `Command` | ⏳ | Host/capability etkileri açık ABI olmadan açılmamalı |
| `Declaration` | ⏳ | Fonksiyon/declaration ABI ve scope modeli eksik |
| `IfStatement` | ✅ | Deterministik `branch/label/jump`, lexical scope ve exact-head CI doğrulandı |
| `ForEach` | ⏳ | Iteration/control-flow modeli eksik |
| `MatchStatement` | ⏳ | Pattern/control-flow modeli eksik |
| `TryStatement` | ⏳ | Error/exception control-flow modeli eksik |

## Control-flow sözleşmesi

- ✅ IR v1 için `label`, `jump`, `branch` primitive sözleşmesi tanımlandı.
- ✅ Yinelenen/geçersiz label, tanımsız hedef ve tanımsız branch temp kullanımı fail-closed doğrulanıyor.
- ✅ WASM/native adapter entegrasyonu `main` üzerinde doğrulandı.
- ✅ Gerçek `IfStatement` lowering lexical scope korunarak `main` üzerinde doğrulandı.
- 🚧 Kısa devreli `ve` / `veya` için lazy RHS control-flow lowering bu PR'da uygulanıyor; CI yeşil olmadan tamamlanmış sayılmaz.

## Kalan kabul sırası

1. ✅ Control-flow IR primitives ve label/jump doğrulama sözleşmesini tanımla.
2. ✅ WASM/native adapter doğrulamasını yeni control-flow opcode'ları için fail-closed genişlet.
3. ✅ `IfStatement` semantiğini deterministik control-flow olarak indir ve exact-head CI ile doğrula.
4. 🚧 Kısa devreli `ve` / `veya` semantiğini eager RHS üretmeden indir ve exact-head CI ile doğrula.
5. Referans runtime ↔ WASM/native plan semantik eşdeğerliğini control-flow kaynaklarıyla genişlet.
6. Kalan ifade ve statement düğümlerini küçük, ayrı PR'larla ekle; capability gerektiren düğümleri açık ABI olmadan destekleme.
7. Tam AST/semantic kapsam matrisi, olumlu/olumsuz/regression/property/security testleri ve Python 3.11/3.12/3.13 + gerçek `.shn` smoke tamamen yeşil olduğunda Aşama 10'u `%94` olarak kapat.

## Kalite ilkeleri

- Desteklenmeyen düğüm sessizce atlanmaz; `IRLoweringError` ile reddedilir.
- Kısa devre semantiği eager RHS ile taklit edilmez.
- WASM/native adapter capability yüzeyi varsayılan-kapalı kalır.
- Unknown opcode/version, malformed instruction, use-before-definition ve duplicate-temp fail-closed kalır.
- Benchmark veya performans hedefi semantik eşdeğerlik kontrolünü devre dışı bırakamaz.
