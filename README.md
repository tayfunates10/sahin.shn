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

**Genel ilerleme: %80**

Tamamlanan son kalite kapısı: **Aşama 8 — Modül + paket ekosistemi**  
Sıradaki aşama: **Aşama 9 — Formatter + linter + test runner + LSP + debugger + REPL**

İlerleme yüzdesi yalnızca ilgili kalite kapıları ve testler geçtiğinde artırılır.

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
| 9 — Formatter + linter + test runner + LSP + debugger | %87 | 🚧 Sıradaki |
| 10 — Şahin IR + WASM/native backend + performans | %94 | ⏳ |
| 11 — Self-hosting | %97 | ⏳ |
| 12 — Fuzz/security/compatibility ve 1.0 sertifikasyonu | %100 | ⏳ |

Ayrıntılı alt aşamalar ve kabul kriterleri: [`docs/ROADMAP.md`](docs/ROADMAP.md)

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
- `docs/STANDART-KUTUPHANE.md`

## Lisans

Lisans kararı ilk mimari aşamalarda netleştirilecektir.
