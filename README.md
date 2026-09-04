# Şahin (`.shn`)

Şahin; Türkçe karakterleri doğal olarak kullanan, ancak Python/JavaScript/HTML/CSS/PHP/SQL dillerinin Türkçeleştirilmiş bir kopyası olmayan yeni nesil bir programlama dili projesidir.

## Vizyon

Tek bir sade dil ile arayüz, görünüm, uygulama mantığı, sunucu, API, veri modeli, sorgu, otomasyon ve komut satırı uygulamaları geliştirebilmek.

> Basitlik yüzeyde, güç altyapıda.

## Temel ilkeler

- Özgün sözdizimi ve özgün semantik
- UTF-8 ve Türkçe karakterler birinci sınıf vatandaş
- HTML/CSS/JS/PHP/SQL kalıplarını kullanıcıya taşıtmayan bütünleşik uygulama modeli
- Güçlü tip, modül, eşzamanlılık ve araç zinciri
- Güvenli varsayılanlar ve anlaşılır Türkçe hata mesajları
- Web, backend, veri ve otomasyon için tek dil
- WASM/native hedefleri ve ileride self-hosting

## İlk Şahin örneği

```shn
uygulama Dükkan

kayıt Ürün
    ad: yazı
    fiyat: para
    stok: sayı

ekran Ana
    başlık "Ürünler"
    ürünler <- Ürün.tümü

    her ürün içinden ürünler
        kart
            başlık ürün.ad
            metin ürün.fiyat
            eylem "Satın al" -> satınAl ürün

akış satınAl ürün
    ürün.stok <= 0 ise
        bildir "Ürün tükendi"
        bitir

    ürün.stok azalt 1
    sakla ürün
    bildir "Satın alma başarılı"
```

## Durum

**Genel ilerleme: %87**

Tamamlanan son kalite kapısı: **Aşama 9 — Araç zinciri**  
Aktif aşama: **Aşama 10 — Şahin IR + WASM/native backend + performans**

Aşama 10'da deterministik IR çekirdeği, güvenli WASM/native adapter sınırları, control-flow primitive'leri, gerçek `IfStatement` lowering + lexical scope korunumu, lazy RHS koruyan kısa devreli `ve/veya` lowering, `Predicate`, `Member`, doğrudan `Call` + `akış` `Declaration` ABI, `RangeExpression`, `Pipeline`, `ForEach` ve `MatchStatement` lowering + WASM/native/equivalence entegrasyonu doğrulandı. `TryStatement` için AST → `try_guard`/`catch` lowering, ayrı handler scope'u, normal-yol handler bypass, malformed-handler fail-closed backend doğrulaması, başarılı/hatalı/nested handler eşdeğerliği, top-level `Binary` hata payload/string eşdeğerliği, `IRFlow` içindeki `Binary` kaynak konumlarının ayrı instruction-index uzayıyla WASM/native canonical evidence içine taşınması ve flow içinde yakalanıp gözlemlenen `Binary` hata payload/string eşdeğerliği doğrulandı. Ancak flow dışına taşan hatalarda call-site provenance/stack-frame ABI'sı ile `Unary`/`Member`/`RangeExpression`/`Pipeline`/`Call` kaynaklı hata payload ABI'ları henüz kapanmadığı için `TryStatement` tam destekli gösterilmez. Kalan ana iş bu hata yürütme/provenance kapsamı ile `ExpressionStatement`, `FieldDeclaration`, diğer `Command` ve diğer `Declaration` düğümleridir; final Python 3.11/3.12/3.13 + gerçek `.shn` smoke kapısı ve tam kapsam matrisi tamamlanmadan ilerleme %94'e çıkarılmaz.

İlerleme yüzdesi yalnızca ilgili kalite kapıları ve testler geçtiğinde artırılır. Bu nedenle doğrulanmış ara ilerlemeye rağmen genel yüzde, Aşama 10 tamamlanana kadar **%87** olarak tutulur.

## Roadmap

| Aşama | Hedef yüzde | Durum |
|---|---:|---|
| 0 — Proje temeli | %3 | ✅ |
| 1 — Dil anayasası + sözdizimi çekirdeği | %10 | ✅ |
| 2 — Parser + ifade sistemi + semantik çekirdek | %22 | ✅ |
| 3 — Çalıştırma motoru + hata modeli | %32 | ✅ |
| 4 — Tip sistemi + güvenlik | %42 | ✅ |
| 5 — Standart kütüphane | %51 | ✅ |
| 6 — Arayüz + görünüm motoru | %62 | ✅ |
| 7 — Sunucu + API + veri motoru | %73 | ✅ |
| 8 — Modül + paket ekosistemi | %80 | ✅ |
| 9 — Formatter + linter + test runner + LSP + debugger + REPL | %87 | ✅ |
| 10 — Şahin IR + WASM/native backend + performans | %94 | 🚧 Devam ediyor |
| 11 — Self-hosting | %97 | ⏳ |
| 12 — Fuzz/security/compatibility ve 1.0 sertifikasyonu | %100 | ⏳ |

Ayrıntılı alt aşamalar ve kabul kriterleri: [`docs/ROADMAP.md`](docs/ROADMAP.md)  
Aşama 10 IR kapsam envanteri: [`docs/STAGE10-IR-COVERAGE.md`](docs/STAGE10-IR-COVERAGE.md)

## Doğrulanmış kalite kapıları

### Aşama 2
Native Şahin AST, ayrı `Binding`, blok parserı, precedence, scope/symbol çözümleme, ilk tip çıkarımı, golden parser sözleşmesi, Unicode NFC/property ve karşılaştırma regression testleri tamamlandı.

### Aşama 3
Lexical frame/scope, `akış` çağrıları, kontrol akışı, `Binding` runtime sözleşmesi, pipeline çekirdeği ve kaynak konumlu Şahin hata zinciri tamamlandı.

### Aşama 4
`TypeSpec`, `X veya yok`, flow-sensitive `yok` daraltma, `SHN-T302`, parametre/dönüş/atama tip güvenliği ve varsayılan-kapalı capability modeli tamamlandı.

### Aşama 5
- NFC güvenli `Metin`
- Decimal tabanlı `Sayi` ve para biçimleme
- deterministik `Koleksiyon`
- test saati enjekte edilebilen `An`
- boyut sınırlı ve kontrollü hatalı `Json`
- capability zorunlu `Dosya` okuma/yazma
- capability, timeout ve boyut sınırı zorunlu `Ag`
- CSPRNG + SHA-2 + HMAC yüksek seviyeli `Guven`
- bozuk/aşırı büyük veri, capability reddi, Unicode ve güvenlik regression testleri
- Python 3.11 / 3.12 / 3.13 compile + test + gerçek `.shn` smoke CI: yeşil

Standart kütüphane sözleşmesi: [`docs/STANDART-KUTUPHANE.md`](docs/STANDART-KUTUPHANE.md)

### Aşama 6
- immutable ve kimlikli `Dugum` / `RenderIR` UI ağacı
- selector/DOM bağımsız görünüm modeli
- tasarım tokenları ve responsive eşikler
- immutable, sürümlü ve alan-izinli state güncelleme modeli
- erişilebilirlik/focus sözleşmesi
- HTML üretmeyen host-independent `BrowserAdapter` sınırı
- kullanıcı içeriği için varsayılan kaçış ve unsafe-content fail-closed güvenliği
- Unicode, responsive, state çakışması, adapter ve XSS regression testleri
- Python 3.11 / 3.12 / 3.13 compile + test + gerçek `.shn` smoke CI: yeşil

### Aşama 7
- host-independent HTTP istek/yanıt ve `uç` route modeli
- yöntem, yol, sorgu ve gövde doğrulama zinciri
- SQL metni üretmeyen `QueryIR` / `BackendQuery` ve yapılandırılmış parametreler
- `ModelMeta` / `ModelField` veri metadata modeli ve sıralı `MigrationPlan`
- fail-closed transaction commit/rollback sözleşmesi
- veri/ağ capability kontrolleri ve injection/path/query/body/transaction regression testleri
- Python 3.11 / 3.12 / 3.13 compile + test + gerçek `.shn` smoke CI: yeşil

### Aşama 8
- immutable paket manifesti ve deterministik canonical manifest/lockfile
- SHA-256 bütünlük doğrulaması ve registry provenance eşleştirmesi
- deterministik `X.Y.Z`, `^X.Y.Z`, `~X.Y.Z` sürüm/uyumluluk çözümleme
- provenance zorunlu `RegistryAdapter` sınırı ve dependency-confusion koruması
- signer trust/revocation ile fail-closed paket imza doğrulaması
- her okumada yeniden doğrulanan offline cache
- revision tabanlı optimistic concurrency ve atomic install transaction rollback
- bütünlük, provenance, signature, revocation, stale commit/rollback ve path traversal regression/security testleri
- Python 3.11 / 3.12 / 3.13 compile + test + gerçek `.shn` smoke CI: yeşil

### Aşama 9
- deterministik ve idempotent canonical formatter
- Şahin semantic zincirini yeniden kullanan kaynak konumlu linter
- deterministik test keşfi ve başarısızlıkları gizlemeyen native test runner
- diagnostics/completion/hover/go-to-definition/symbol sağlayan semantic-backed LSP çekirdeği
- runtime state'ini değiştirmeyen breakpoint/step/frame-scope debugger çekirdeği
- varsayılan-kapalı capability, kaynak limitleri ve atomik rollback sözleşmeli REPL
- REPL runtime hata rollback, immutable binding sızıntısı, Unicode ve araç zinciri regression testleri
- Python 3.11 / 3.12 / 3.13 compile + test + gerçek `.shn` smoke CI: yeşil

### Aşama 10 — doğrulanmış ara kapılar
- deterministik ve sürümlü Şahin IR v1 çekirdeği
- fail-closed WASM/native adapter sınırları
- `label` / `jump` / `branch` control-flow sözleşmesi ve adapter entegrasyonu
- gerçek `IfStatement` lowering, nested determinism ve lexical scope korunumu
- lazy RHS koruyan kısa devreli `ve/veya` control-flow lowering ve kullanıcı ad alanından ayrılmış internal join slotları
- `yok` / `boş` / `boş_değil` için açık `predicate` IR lowering + backend/equivalence doğrulaması
- `Member` için açık `member` IR lowering, target-temp definite-definition, backend fail-closed şeması ve runtime/backend equivalence doğrulaması
- `IRFlow` + `call` + `return` ABI; parametre/type metadata, lexical capture, call target/arity doğrulaması ve bağımsız çağrı frame'i
- flow/call için referans runtime ↔ WASM/native plan semantik eşdeğerliği, lexical capture okuma/yazma ve dönüş regression testleri
- `RangeExpression` için açık `range` opcode'u, backend schema/CFG/use-def doğrulaması ve inclusive ileri/geri runtime ↔ WASM/native equivalence
- `Pipeline` için açık `pipeline` opcode'u, stage/arity/use-def/result fail-closed doğrulaması ve `ilk`/`sırala`/`seç` runtime ↔ WASM/native equivalence
- `ForEach` için explicit iterator IR, lexical loop scope, terminator-aware `bitir`, iterator-origin/use-def backend doğrulaması ve referans runtime ↔ WASM/native equivalence
- `MatchStatement` için subject-once, kaynak sıralı pattern karşılaştırması, first-match control-flow ve `yaz`/`bildir` runtime ↔ WASM/native equivalence
- `TryStatement` için `try_guard` / `catch` IR, lexical error-binding scope, normal-yol handler bypass ve malformed-handler fail-closed backend doğrulaması
- Try başarı, sıfıra bölme hata yolu ve nested-try inner-handler önceliği için referans runtime ↔ WASM/native plan equivalence
- top-level `Binary` instruction source provenance'ı WASM/native canonical evidence içine taşınıyor; yakalanan arithmetic/type hata `RuntimeErrorSHN` satır/sütun payload'ı ve `yaz hata` çıktısı referans runtime ile birebir doğrulanıyor
- `IRFlow` içindeki `Binary` provenance kayıtları flow adıyla ayrı instruction-index uzayında taşınıyor; top-level canonical biçim geriye uyumlu kalıyor ve capability/import yüzeyi genişlemiyor
- flow-local `dene/olmazsa` içinde yakalanan `Binary` arithmetic/type hata payload'ı, flow-scoped provenance kullanılarak `RuntimeErrorSHN` satır/sütun bilgisiyle referans runtime ↔ WASM/native arasında birebir doğrulanıyor
- flow dışına taşan hata call-site provenance/stack-frame kanıtı olmadan eşdeğer kabul edilmiyor; fail-closed kalıyor
- kaynak kanıtı olmayan manuel IR planları provenance uydurmuyor; capability/import yüzeyi genişletilmiyor
- control-flow dahil referans runtime ↔ WASM/native plan semantik eşdeğerlik oracle'ı
- ayrı backend örnek serileri ve workload SHA-256 kimliği kullanan tekrarlanabilir benchmark baseline'ı
- malformed IR, unknown version/opcode, use-before-definition, duplicate-temp ve capability yüzeyi için property/security regression paketi
- bu ara kapıların Python 3.11/3.12/3.13 compile + test + gerçek `.shn` smoke kalite koşuları yeşil

Aşama 10 henüz tamamlanmış değildir. `TryStatement` control-flow/error-binding/backend handler çekirdeği, top-level ve flow-local `Binary` hata source-provenance/payload eşdeğerliği doğrulandı; flow dışına taşan hata için call-site provenance/stack-frame ABI'sı ile diğer hata üretebilen opcode'ların gözlemlenebilir payload ABI'ları açık kalmaktadır. Bunun ardından `ExpressionStatement`, `FieldDeclaration`, diğer `Command` ve diğer `Declaration` düğümleri kendi semantik/ABI/capability modelleriyle kapatılacaktır.

## Kalite ve geliştirme akışı

1. Her geliştirme ayrı branch + PR ile ilerler.
2. Olumlu, olumsuz ve regression testleri zorunludur.
3. Python 3.11/3.12/3.13 CI tamamen yeşil olmadan PR `main`e alınmaz.
4. Başarısız test atlanmaz veya kalite eşiği düşürülmez; kök neden düzeltilir.
5. Unicode/Türkçe normalizasyonu ayrıca test edilir.
6. Güvenlik kritik katmanlarda property/fuzz/security testleri zorunludur.
7. README yüzdesi yalnızca doğrulanmış ilerlemeyi gösterir.

## Tasarım belgeleri

- `docs/DIL-ANAYASASI.md`
- `docs/SOZDIZIMI-v0.1.md`
- `docs/MIMARI.md`
- `docs/ROADMAP.md`
- `docs/STAGE10-IR-COVERAGE.md`
- `docs/STANDART-KUTUPHANE.md`

## Lisans

Lisans kararı ilk mimari aşamalarda netleştirilecektir.