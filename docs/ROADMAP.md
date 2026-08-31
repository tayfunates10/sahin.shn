# Şahin Geliştirme Roadmap'i

Bu belge Şahin'in %100 tamamlanma yolunu ve her aşamadaki kalite kapılarını tanımlar. Bir aşama yalnızca kod yazıldığı için tamamlanmış sayılmaz; ilgili testler yeşil olmadan ilerleme yüzdesi artırılmaz.

## İlerleme modeli

Toplam ilerleme: **%10**

| Aşama | Ağırlık | Durum | Kabul kapısı |
|---|---:|---|---|
| 0. Proje temeli | %3 | ✅ Tamamlandı | Repo, paket iskeleti, CI başlangıcı |
| 1. Dil anayasası + sözdizimi çekirdeği | %7 | ✅ Tamamlandı | Özgünlük ilkeleri, UTF-8, ilk grammar, lexer smoke testleri |
| 2. Parser + ifade sistemi + semantik çekirdek | %12 | 🚧 Aktif | Blok AST, precedence, bağlama, koşul/yineleme, sembol çözümleme, tip çıkarımı |
| 3. Çalıştırma motoru + hata modeli | %10 | ⏳ | Scope, çağrı modeli, kontrol akışı, deterministik runtime, diagnostics |
| 4. Tip sistemi + güvenlik | %10 | ⏳ | Statik tipler, nullable/yok güvenliği, capability modeli, type/property testleri |
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

## Aşama 2 — Parser + semantik çekirdek

### 2A — AST genişletme (%10 → %12)
- [ ] Blok düğümü
- [ ] `uygulama`, `ekran`, `görünüm`, `akış`, `kayıt`, `uç`, `iş`, `olay`
- [ ] Kaynak konum bilgisi
- [ ] Şahin'e özgü binding düğümü

### 2B — İfade sistemi (%12 → %15)
- [ ] Prefix/unary ifadeler
- [ ] Binary precedence
- [ ] Üye erişimi
- [ ] Çağrı
- [ ] `..` aralık
- [ ] `|` veri hattı
- [ ] Parantezli ifade

### 2C — Kontrol akışı grammarı (%15 → %18)
- [ ] `... ise`
- [ ] `yoksa`
- [ ] `her ... içinden ...`
- [ ] `duruma göre`
- [ ] `bitir`

### 2D — Semantik analiz (%18 → %20)
- [ ] Sembol tablosu
- [ ] Scope çözümleme
- [ ] Tanımsız isim teşhisi
- [ ] Yeniden tanımlama/binding kuralları
- [ ] İlk tip çıkarımı

### 2E — Sertifikasyon (%20 → %22)
- [ ] Golden parser testleri
- [ ] Unicode normalizasyon testleri
- [ ] Hatalı girinti testleri
- [ ] Diagnostic konum testleri
- [ ] CI 3.11/3.12/3.13 tamamen yeşil

## Sonraki kapı

Aşama 2 %22'ye ulaşmadan Aşama 3 tamamlanmış sayılmaz. Deneysel runtime çalışmaları yapılabilir, ancak roadmap yüzdesi kalite kapısına göre hesaplanır.
