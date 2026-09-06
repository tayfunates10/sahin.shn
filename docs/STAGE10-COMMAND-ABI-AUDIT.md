# Aşama 10 — Command ABI denetimi

Bu belge `Command` AST düğümünün Aşama 10 kapsamındaki gerçek davranışlarını sınıflandırır. Amaç desteklenmeyen komutları sessizce no-op yapmak değil, referans runtime davranışı bulunan yolları açık ABI ile kapatmak ve host/capability etkili yolları kendi sözleşmeleri tanımlanana kadar fail-closed tutmaktır.

## Doğrulanmış Command yolları

- `yaz` / `bildir`: referans runtime ile aynı şekilde yalnız ilk argümanı değerlendirip `write` IR üretir.
- `ver`: yalnız `akış` gövdesinde `return` IR üretir; akış dışında fail-closed kalır.
- `bitir`: yalnız aktif yineleme içinde loop end label'ına `jump` üretir; yineleme dışında fail-closed kalır.
- `artır` / `azalt` — doğrudan `Name` hedefi: mevcut değeri `load`, miktarı değerlendirme, `binary` ve `store` zinciriyle indirir; `<-` ile immutable bağlanan hedefler fail-closed reddedilir.
- `artır` / `azalt` — `Member` hedefi: ayrı member-mutation ABI/lowering katmanı üzerinden okuma sahibi → miktar → yazma sahibi değerlendirme sırasını korur ve `member_store` ile açık lvalue mutation üretir. Backend doğrulama/equivalence regression testleri bu yolu kilitler.

## Açık ABI işi

- `sakla`: backend-neutral veri-mutation ABI çekirdeği `DataMutationABI` ile tanımlanmıştır. Yalnız `sakla` kabul edilir, model/value-slot tanımlayıcıları fail-closed doğrulanır ve host sınırından önce açık `veri:yaz` capability'si zorunludur. Bu çekirdek henüz AST→IR lowering, gerçek host mutation yürütmesi veya runtime↔WASM/native equivalence anlamına gelmez.
- `cevap` ve diğer host/capability etkili komutlar: HTTP veya başka host motorlarının açık capability sözleşmesi olmadan backend opcode'una dönüştürülmez.
- Gövdeli genel komutlar: referans runtime lexical blok çalıştırsa da UI/host anlamı ayrı motorlara aittir. Host semantiği ve capability modeli tanımlanmadan backend'de genel bir "çalıştır" opcode'u eklenmez.

## Güvenlik sınırı

- Desteklenmeyen `Command` fail-closed `IRLoweringError` üretmeye devam eder.
- `ver` ve `bitir` bağlam dışına kaçırılamaz.
- `artır` / `azalt` immutable binding'i mutate edemez; member mutation değerlendirme sırası backend optimizasyonlarıyla değiştirilemez.
- `sakla` için `veri:yaz` capability'si verilmeden host mutation sınırı geçilemez.
- Yeni Command desteği capability/import yüzeyini dolaylı biçimde genişletemez.
- Runtime davranışı bulunan bir komut için referans runtime ↔ WASM/native equivalence kanıtlanmadan kapsam tamamlandı sayılmaz.

## Sıradaki kabul dilimi

`sakla` için ilk ABI/capability çekirdeği vardır; sıradaki eksik dilim parser/AST biçimini bu sözleşmeye kayıpsız bağlayan açık lowering katmanıdır. Bundan sonra backend host mutation doğrulaması ve referans runtime ↔ WASM/native equivalence ayrı kapılar olarak tamamlanmalıdır. Bu kapılar kapanmadan `sakla` desteklenmiş sayılmaz.

Genel proje ilerlemesi Aşama 10 tamamen kapanana kadar `%87` olarak kalır.
