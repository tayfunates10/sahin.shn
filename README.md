# Şahin (`.shn`)

Şahin; Türkçe karakterleri doğal olarak kullanan, ancak Python/JavaScript/HTML/CSS/PHP/SQL dillerinin Türkçeleştirilmiş bir kopyası olmayan yeni nesil bir programlama dili projesidir.

## Vizyon

Tek bir sade dil ile arayüz, görünüm, uygulama mantığı, sunucu, API, veri modeli, sorgu, otomasyon ve komut satırı uygulamaları geliştirebilmek.

> Basitlik yüzeyde, güç altyapıda.

## Neden Şahin?

Bugünkü web geliştirmede HTML + CSS + JavaScript/TypeScript + backend + SQL + framework + ORM zincirini öğrenmek gerekir. Şahin'in amacı bu katmanların kullanıcıya yansıyan bilişsel yükünü tek bir tutarlı dil modelinde azaltmaktır.

Şahin'in hedefi "aynı dillerin Türkçesi" olmak değil; arayüz, olay, veri, işlem ve servis kavramlarını tek AST ve tek çalışma modeli altında birleştirmektir.

## Temel ilkeler

- Özgün sözdizimi ve özgün semantik
- UTF-8 ve Türkçe karakterler birinci sınıf vatandaş
- HTML/CSS/JS/PHP/SQL kalıplarını kullanıcıya taşıtmayan bütünleşik uygulama modeli
- Yeni başlayan için düşük bilişsel yük
- Büyük projeler için güçlü tip, modül, eşzamanlılık ve araç zinciri
- Güvenli varsayılanlar ve anlaşılır hata mesajları
- Web, backend, veri ve otomasyon için tek dil
- Gelecekte WASM/native hedefleri

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

Bu örnek herhangi bir HTML etiketi, CSS seçicisi, JavaScript fonksiyonu veya SQL sorgusu kullanmaz.

## Durum

**Genel ilerleme: %22**

Tamamlanan son kalite kapısı: **Aşama 2 — Parser + ifade sistemi + semantik çekirdek**  
Sıradaki aşama: **Aşama 3 — Çalıştırma motoru + hata modeli**

İlerleme yüzdesi yalnızca ilgili kalite kapıları ve testler geçtiğinde artırılır.

## Roadmap

| Aşama | Hedef yüzde | Durum |
|---|---:|---|
| 0 — Proje temeli | %3 | ✅ |
| 1 — Dil anayasası + sözdizimi çekirdeği | %10 | ✅ |
| 2 — Parser + ifade sistemi + semantik çekirdek | %22 | ✅ |
| 3 — Çalıştırma motoru + hata modeli | %32 | 🚧 Sıradaki |
| 4 — Tip sistemi + güvenlik | %42 | ⏳ |
| 5 — Standart kütüphane | %51 | ⏳ |
| 6 — Arayüz + görünüm motoru | %62 | ⏳ |
| 7 — Sunucu + API + veri motoru | %73 | ⏳ |
| 8 — Modül + paket ekosistemi | %80 | ⏳ |
| 9 — Formatter + linter + test runner + LSP + debugger | %87 | ⏳ |
| 10 — Şahin IR + WASM/native backend + performans | %94 | ⏳ |
| 11 — Self-hosting | %97 | ⏳ |
| 12 — Fuzz/security/compatibility ve 1.0 sertifikasyonu | %100 | ⏳ |

Ayrıntılı alt aşamalar ve kabul kriterleri: [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Aşama 2 doğrulaması

- Native Şahin AST ve ayrı `Binding` düğümü
- Blok parserı ve özgün postfix koşul modeli
- Precedence, çağrı, üye erişimi, `..` ve `|`
- Scope/symbol çözümleme ve ilk tip çıkarımı
- Türkçe diagnostic + yakın isim önerisi
- Golden AST sözleşmesi
- Unicode NFC + 100 varyant deterministik property testi
- Karşılaştırma operatörleri regression testi
- Python 3.11 / 3.12 / 3.13 CI: yeşil

## Kalite ve geliştirme akışı

1. Her geliştirme ayrı branch + PR ile ilerler.
2. Parser/runtime değişikliklerinde olumlu, olumsuz ve regression testleri eklenir.
3. Python 3.11/3.12/3.13 referans frontend CI matrisi tamamen yeşil olmadan PR `main`e alınmaz.
4. Başarısız test atlanmaz veya kalite eşiği düşürülmez; kök neden düzeltilir.
5. Unicode/Türkçe karakter normalizasyonu ayrıca test edilir.
6. Güvenlik kritik katmanlarda property/fuzz testleri zorunludur.
7. README yüzdesi yalnızca doğrulanmış ilerlemeyi gösterir.

## Tasarım belgeleri

- `docs/DIL-ANAYASASI.md`
- `docs/SOZDIZIMI-v0.1.md`
- `docs/MIMARI.md`
- `docs/ROADMAP.md`

## Lisans

Lisans kararı ilk mimari aşamalarda netleştirilecektir.
