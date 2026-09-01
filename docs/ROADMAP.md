# Şahin Geliştirme Roadmap'i

Bu belge Şahin'in %100 tamamlanma yolunu ve kalite kapılarını tanımlar. Bir aşama yalnızca kod yazıldığı için tamamlanmış sayılmaz; testler ve CI yeşil olmadan ilerleme yüzdesi artırılmaz.

## İlerleme modeli

Toplam ilerleme: **%73**

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
| 8. Modül + paket ekosistemi | %7 | 🚧 Sıradaki | manifest, lockfile, registry, imza |
| 9. Araç zinciri | %7 | ⏳ | formatter, linter, test runner, LSP, debugger, REPL |
| 10. WASM/native + performans | %7 | ⏳ | Şahin IR, WASM/native, benchmark |
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

## Aşama 2 — Parser + semantik çekirdek ✅

- [x] Native Şahin AST + ayrı `Binding`
- [x] Blok parserı ve ifade precedence
- [x] `ise/yoksa`, yineleme, eşleştirme, pipeline, aralık
- [x] Scope/symbol çözümleme ve ilk tip çıkarımı
- [x] Türkçe kaynak konumlu diagnostics
- [x] Golden + Unicode property + regression testleri
- [x] Python 3.11/3.12/3.13 CI

## Aşama 3 — Runtime + hata modeli ✅

- [x] Lexical scope/frame
- [x] `akış`, parametre, `ver`
- [x] Kontrol akışı ve pipeline runtime
- [x] `Binding` çalışma sözleşmesi
- [x] Kaynak konumlu hata zinciri
- [x] Deterministik runtime regression testleri
- [x] Python 3.11/3.12/3.13 CI

## Aşama 4 — Tip sistemi + güvenlik ✅

- [x] Temel tip ve parametre/dönüş sözleşmeleri
- [x] `TypeSpec` birleşik/opsiyonel tip modeli
- [x] Parserda `X veya yok`
- [x] Flow-sensitive `yok` daraltma
- [x] `SHN-T302` opsiyonel alan güvenliği
- [x] Varsayılan-kapalı capability modeli
- [x] Type/security regression testleri
- [x] Python 3.11/3.12/3.13 CI

## Aşama 5 — Standart kütüphane ✅

Hedef ilerleme: **%42 → %51**

- [x] NFC güvenli `Metin`: uzunluk, böl, birleştir, ara, dönüşüm
- [x] Decimal tabanlı `Sayi`: güvenli dönüşüm, yuvarlama, para, aralık
- [x] `Koleksiyon`: seç, dönüştür, sırala, ilk/son, grupla, tekilleştir
- [x] `An`: UTC tabanlı zaman ve deterministik test saati enjeksiyonu
- [x] `Json`: UTF-8, boyut sınırı, kontrollü çözümleme/serileştirme hataları
- [x] `Dosya`: `dosya:oku` / `dosya:yaz` capability zorunluluğu ve boyut sınırı
- [x] `Ag`: `ağ` capability, http/https kısıtı, timeout ve yanıt boyut sınırı
- [x] `Guven`: CSPRNG, SHA-256/384/512, HMAC, sabit-zaman doğrulama
- [x] MD5/SHA-1 ve tehlikeli düşük seviye kripto yüzeylerini varsayılan API dışında tutma
- [x] Türkçe diagnostic kodları ve kontrollü hata sınıfları
- [x] Unicode, bozuk/aşırı büyük veri, capability reddi ve güvenlik regression testleri
- [x] Python 3.11/3.12/3.13 compile + test + `.shn` smoke CI tamamen yeşil

### Aşama 5 doğrulama kaydı

Standart kütüphane, başka dillerin API yüzeyini Türkçeleştirmek yerine Şahin'in capability ve güvenli-varsayılan modeline göre tasarlandı. Saf işlemler deterministik ve capability'siz; dış dünya işlemleri yetki kontrolünü dış kaynağa dokunmadan önce yapıyor. JSON/dosya/ağ işlemlerinde kaynak tüketimi sınırlandırıldı. Kripto yüzeyi yüksek seviyeli güvenli primitive'lerle sınırlandı. İlk kalite turunda Python 3.11, 3.12 ve 3.13 üzerinde compile, tüm testler ve gerçek `.shn` smoke çalıştırması yeşil geçti.

## Aşama 6 — Arayüz + görünüm motoru ✅

Hedef ilerleme: **%51 → %62**

- [x] Şahin'e özgü immutable/kimlikli UI ağacı
- [x] `ekran`, `kart`, `başlık`, `metin`, `eylem` düğümlerinin runtime modeli
- [x] HTML/CSS seçicilerini kullanıcıya taşımayan temel görünüm sistemi
- [x] Tasarım tokenları, tipografi ve responsive kuralları
- [x] Olay modelinin immutable render sözleşmesi
- [x] Kontrollü, immutable ve sürümlü state güncelleme modeli
- [x] Klavye/focus/semantik erişilebilirlik çekirdek sözleşmesi
- [x] Deterministik render snapshot/golden testleri
- [x] Browser adapter/WASM öncesi host-independent render IR
- [x] XSS/unsafe-content varsayılan-kapalı güvenlik testleri
- [x] Browser adapter sınırı ve adapter contract/security testleri
- [x] Python 3.11/3.12/3.13 CI tamamen yeşil

### Aşama 6 doğrulama kaydı

Render modeli DOM veya HTML etiketi taşımayan `Dugum`/`RenderIR` yapısına dayanır. Düğümler immutable'dır, kimlikler NFC normalize edilir ve ağaç genelinde yinelenen kimlikler reddedilir. Etkileşimli `eylem` düğümleri erişilebilir etiket ve focus semantiği taşır. Kullanıcı metni host adapterına aktarılırken varsayılan olarak kaçırılır; ham içerik açık izin olmadan oluşturulamaz. Görünüm modeli selector/CSS sözdizimi yerine Şahin'e özgü ölçü, tasarım tokenı ve responsive eşik değerleri kullanır. UI state sürümlü ve immutable'dır; state işlemleri yalnızca açıkça izin verilmiş alanları değiştirebilir. Browser adapter sözleşmesi HTML metni üretmez, host ağacını yapılandırılmış veri olarak taşır ve kullanıcı metnini executable markup olarak yorumlamaz. Python 3.11, 3.12 ve 3.13 üzerinde compile, tüm testler ve gerçek `.shn` smoke kalite kapısı yeşil geçti.

## Aşama 7 — Sunucu + API + veri motoru ✅

Hedef ilerleme: **%62 → %73**

- [x] Host-independent HTTP istek/yanıt modeli
- [x] `uç` tanımı ve route çözümleme
- [x] Yöntem, yol parametresi, sorgu ve gövde doğrulama
- [x] Yapılandırılmış Türkçe hata/yanıt sözleşmesi
- [x] `ModelMeta` / `ModelField` veri metadata modeli
- [x] Sıralı, benzersiz sürümlü `MigrationPlan` / `MigrationStep`
- [x] SQL metni üretmeyen `QueryIR`
- [x] Yapılandırılmış parametre taşıyan `BackendQuery` adapter sınırı
- [x] Fail-closed transaction başlat/commit/rollback sözleşmesi
- [x] Veri/ağ capability kontrolleri
- [x] Deterministik adapter ve olumlu/olumsuz/security/regression testleri
- [x] Injection, path/query/body ve transaction failure regression testleri
- [x] Python 3.11/3.12/3.13 compile + test + `.shn` smoke CI tamamen yeşil

### Aşama 7 doğrulama kaydı

HTTP ve veri IR host-independent tutuldu; Şahin kullanıcısına doğrudan framework route API'si veya SQL string'i yazdırılmıyor. Sorgu değerleri string birleştirme yerine yapılandırılmış parametreler olarak backend adapter sınırına taşınıyor. Transaction hataları fail-closed rollback ile sonuçlanıyor ve dış dünya veri/ağ işlemleri capability kontrolünden önce yürütülmüyor. PR #18 ve PR #19 ile kabul kriterleri tamamlandı; PR #19 kalite kapısında Python 3.11, 3.12 ve 3.13 üzerinde compile, tüm testler ve gerçek `.shn` smoke tamamen yeşil geçti.

## Sonraki kapı

**Aşama 8 — Modül + paket ekosistemi** için manifest, deterministik lockfile, bağımlılık çözümleme, registry/provenance ve paket imzası/revocation güvenlik modeli geliştirilecektir. Hedef ilerleme **%73 → %80**.
