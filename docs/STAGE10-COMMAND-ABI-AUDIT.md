# Aşama 10 — Command ABI denetimi

Bu belge `Command` AST düğümünün Aşama 10 kapsamındaki gerçek davranışlarını sınıflandırır. Amaç desteklenmeyen komutları sessizce no-op yapmak değil, referans runtime davranışı bulunan yolları açık ABI ile kapatmak ve host/capability etkili yolları kendi sözleşmeleri tanımlanana kadar fail-closed tutmaktır.

## Doğrulanmış Command yolları

- `yaz` / `bildir`: referans runtime ile aynı şekilde yalnız ilk argümanı değerlendirip `write` IR üretir.
- `ver`: yalnız `akış` gövdesinde `return` IR üretir; akış dışında fail-closed kalır.
- `bitir`: yalnız aktif yineleme içinde loop end label'ına `jump` üretir; yineleme dışında fail-closed kalır.

## Açık ABI işi

- `artır` / `azalt`: referans runtime'da gerçek state mutation semantiği vardır. IR v1 henüz bu davranışı taşımadığı için bu iki komut sessizce indirgenemez. Sonraki alt dilim mutation ABI'sini, lvalue/Member güvenliğini, use-def ve backend equivalence'ı tanımlamalıdır.
- `sakla`, `cevap` ve benzeri host/capability etkili komutlar: veri, HTTP veya başka host motorlarının açık capability sözleşmesi olmadan backend opcode'una dönüştürülmez.
- Gövdeli genel komutlar: referans runtime lexical blok çalıştırsa da UI/host anlamı ayrı motorlara aittir. Host semantiği ve capability modeli tanımlanmadan backend'de genel bir "çalıştır" opcode'u eklenmez.

## Güvenlik sınırı

- Desteklenmeyen `Command` fail-closed `IRLoweringError` üretmeye devam eder.
- `ver` ve `bitir` bağlam dışına kaçırılamaz.
- Yeni Command desteği capability/import yüzeyini dolaylı biçimde genişletemez.
- Runtime davranışı bulunan bir komut için referans runtime ↔ WASM/native equivalence kanıtlanmadan kapsam tamamlandı sayılmaz.

Genel proje ilerlemesi Aşama 10 tamamen kapanana kadar `%87` olarak kalır.
