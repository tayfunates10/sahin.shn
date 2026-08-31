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

**Aşama 1 — Dil temeli: %8**

Aktif geliştirme dalı: `feat/language-foundation-v0.1`

## Yol haritası

- [x] Aşama 0 — Repository başlangıcı (%3)
- [x] Aşama 1A — Dil anayasası ve özgünlük ilkeleri (%8)
- [ ] Aşama 1B — Sözdizimi v0.1 sabitleme (%10)
- [ ] Aşama 2 — Lexer + parser + AST (%20)
- [ ] Aşama 3 — Çalıştırma motoru ve tip sistemi (%35)
- [ ] Aşama 4 — Standart kütüphane (%50)
- [ ] Aşama 5 — Arayüz + görünüm motoru (%65)
- [ ] Aşama 6 — Sunucu + API + veri katmanı (%78)
- [ ] Aşama 7 — Paket yöneticisi + araç zinciri + LSP (%88)
- [ ] Aşama 8 — WASM/native derleme ve performans (%95)
- [ ] Aşama 9 — Güvenlik, fuzz/property testleri ve 1.0 sertifikasyonu (%100)

## Tasarım belgeleri

- `docs/DIL-ANAYASASI.md`
- `docs/SOZDIZIMI-v0.1.md`
- `docs/MIMARI.md`

## Lisans

Lisans kararı ilk mimari PR'larda netleştirilecektir.
