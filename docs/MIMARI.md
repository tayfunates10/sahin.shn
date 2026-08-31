# Şahin Mimari Taslağı v0.1

## Hedef

Şahin kaynak kodunu tek bir anlam modeline dönüştürmek ve farklı hedeflere çalıştırabilmek.

```text
.shn kaynak
  ↓
Unicode normalizasyonu
  ↓
Lexer
  ↓
Parser
  ↓
Şahin AST
  ↓
Semantik analiz + tip çıkarımı + yetki kontrolü
  ↓
Şahin IR
  ├─ Yorumlayıcı / geliştirme modu
  ├─ Web hedefi (WASM + DOM adaptörü)
  ├─ Sunucu/native hedefi
  └─ Ara uyumluluk katmanları
```

## Katmanlar

### 1. Frontend

Lexer, parser, AST ve hata kurtarma. Türkçe Unicode tanımlayıcıları ve girintili blokları deterministik işler.

### 2. Semantic Core

- isim çözümleme
- tip çıkarımı
- null/yok güvenliği
- effect/yetki sistemi
- akış doğrulama
- kayıt şemaları
- ekran/görünüm bağlama

### 3. Şahin IR

Kaynak sözdiziminden bağımsız ara gösterim. Uzun vadede bootstrap dilinden bağımsızlığın ana noktasıdır.

Örnek düğümler:

- Const
- Bind
- Flow
- Branch
- Pipe
- Record
- Query
- Screen
- ViewRule
- Event
- Endpoint
- Job

İsimler uygulama içi olabilir; kullanıcı sözdizimiyle birebir eşleşmek zorunda değildir.

### 4. Runtime

- değer sistemi
- bellek/GC veya ownership stratejisi
- scheduler
- async I/O
- standart kütüphane
- capability tabanlı sistem erişimi
- hata/stack trace modeli

### 5. Platform adaptörleri

Arayüz ağacı doğrudan HTML değildir. Web hedefinde DOM'a, gelecekte native hedeflerde platform görünümlerine dönüştürülebilir.

Veri sorgu ağacı doğrudan SQL değildir. SQLite/PostgreSQL vb. adaptörler aynı güvenli sorgu IR'ını hedef dile çevirir.

## Bootstrap stratejisi

Aşama 1-3'te referans derleyici/yorumlayıcı hızlı geliştirme için Python ile yazılabilir. Bu bir dil tasarım kararı değil geliştirme aracıdır.

Kurallar:

1. Şahin semantiği Python davranışına göre tanımlanmaz.
2. AST ve semantik testleri dil belirtimine göre yazılır.
3. Runtime sınırları açık arayüzlerle ayrılır.
4. Performans kritik çekirdek ileride Rust/C++/WASM gibi hedeflere taşınabilir.
5. Self-hosting uzun vadeli hedeftir: Şahin derleyicisinin mümkün olan kısmı Şahin ile yazılacaktır.

## Araç zinciri hedefi

```text
şahin çalıştır uygulama.shn
şahin dene
şahin test
şahin biçimle
şahin denetle
şahin paketle
şahin yayınla
```

CLI komutlarının nihai adları kullanıcı testleriyle sabitlenecektir.

## Güvenlik

Şahin uygulamalarında dosya sistemi, ağ, süreç başlatma, native FFI ve gizli bilgi erişimi capability/izin modeliyle sınırlandırılacaktır. Web ve sunucu katmanlarında güvenli varsayılanlar tercih edilir.

## Performans hedefi

Geliştirme modunda hızlı başlangıç; üretimde AOT/WASM/native derleme. UI ve veri katmanında gereksiz yeniden hesaplamayı önleyen bağımlılık grafiği planlanmaktadır.

## Test stratejisi

- lexer golden testleri
- parser snapshot testleri
- AST invariants
- semantic/type property testleri
- Unicode fuzz testleri
- parser fuzzing
- runtime differential testleri
- web hedefi entegrasyon testleri
- veri adaptörü güvenlik testleri
- performans regresyon testleri

Kalite eşiği gevşetilerek test geçirme kabul edilmez.
