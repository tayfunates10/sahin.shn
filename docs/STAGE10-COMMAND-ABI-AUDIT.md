# Aşama 10 — Command ABI denetimi

Bu belge `Command` AST düğümünün Aşama 10 kapsamındaki gerçek davranışlarını sınıflandırır. Amaç desteklenmeyen komutları sessizce no-op yapmak değil, referans runtime davranışı bulunan yolları açık ABI ile kapatmak ve host/capability etkili yolları kendi sözleşmeleri tanımlanana kadar fail-closed tutmaktır.

## Doğrulanmış Command yolları

- `yaz` / `bildir`: referans runtime ile aynı şekilde yalnız ilk argümanı değerlendirip `write` IR üretir.
- `ver`: yalnız `akış` gövdesinde `return` IR üretir; akış dışında fail-closed kalır.
- `bitir`: yalnız aktif yineleme içinde loop end label'ına `jump` üretir; yineleme dışında fail-closed kalır.
- `artır` / `azalt` — doğrudan `Name` hedefi: mevcut değeri `load`, miktarı değerlendirme, `binary` ve `store` zinciriyle indirir; `<-` ile immutable bağlanan hedefler fail-closed reddedilir.
- `artır` / `azalt` — `Member` hedefi: ayrı member-mutation ABI/lowering katmanı üzerinden okuma sahibi → miktar → yazma sahibi değerlendirme sırasını korur ve `member_store` ile açık lvalue mutation üretir. Backend doğrulama/equivalence regression testleri bu yolu kilitler.

## Açık ABI işi

- `sakla`: backend-neutral veri-mutation ABI çekirdeği `DataMutationABI` ile tanımlanmıştır. Canonical parser biçimi `sakla <Name>` ayrı fail-closed lowering katmanıyla bu ABI'ye bağlanır. Authoritative semantic/type sonucu `ResolvedDataBinding(value_slot, model)` sınırıyla taşınır; parsed slot ile semantic binding uyuşmuyorsa lowering fail-closed durur ve model adı yazımdan tahmin edilmez. Native/WASM backend host-mutation sınırı yalnız doğrulanmış ABI + açık `veri:yaz` capability ile `DataMutationBackendPlan` üretebilir; bilinmeyen backend reddedilir. Transaction-backed host execution katmanı yazmayı mevcut `DataEngine.transaction` sınırında yürütür. Kalıcı SQLite adapterı model→table/key/field eşlemesini açık metadata ile zorunlu tutar, runtime değerinden tablo/anahtar/kolon tahmin etmez, parametreli sorgu/upsert kullanır ve adapter örnekleri arasında kalıcılığı doğrular. Native ve WASM yollarının aynı SQLite sözleşmesi üzerinde aynı kalıcı durum, upsert sonucu ve capability-denied davranışı ürettiği regression testiyle kilitlenmiştir. Kaynak runtime köprüsü artık canonical `Command` + authoritative `ResolvedDataBinding` doğrulamasından sonra yalnız doğrulanmış `value_slot` değerini runtime resolver'dan okuyup mevcut transaction-backed execution zincirine teslim eder; stale binding runtime değerine erişmeden fail-closed kalır. `sakla` yine de bu uçtan uca kaynak gözleminin referans runtime ↔ native/WASM sonuçlarıyla birebir equivalence kanıtı tamamlanmadan desteklenmiş sayılmaz.
- `cevap` ve diğer host/capability etkili komutlar: HTTP veya başka host motorlarının açık capability sözleşmesi olmadan backend opcode'una dönüştürülmez.
- Gövdeli genel komutlar: referans runtime lexical blok çalıştırsa da UI/host anlamı ayrı motorlara aittir. Host semantiği ve capability modeli tanımlanmadan backend'de genel bir "çalıştır" opcode'u eklenmez.

## Güvenlik sınırı

- Desteklenmeyen `Command` fail-closed `IRLoweringError` üretmeye devam eder.
- `ver` ve `bitir` bağlam dışına kaçırılamaz.
- `artır` / `azalt` immutable binding'i mutate edemez; member mutation değerlendirme sırası backend optimizasyonlarıyla değiştirilemez.
- `sakla` için model metadata'sı slot adından türetilmez; authoritative semantic binding parsed slot ile eşleşmek zorundadır ve `veri:yaz` capability'si verilmeden host mutation planı veya adapter erişimi oluşamaz.
- `sakla` runtime köprüsü authoritative binding doğrulanmadan slot değerine erişmez; runtime value model kimliği veya SQL metadata kaynağı olamaz.
- `sakla` backend doğrulaması yalnız `native` ve `wasm` hedeflerini kabul eder; yeni IR opcode/import/capability yüzeyi açmaz.
- `sakla` host yazımı yalnız mevcut transaction sınırında gerçekleşir; `write` sözleşmesi bulunmayan transaction rollback ile fail-closed kapanır.
- SQLite adapterı yalnız önceden bildirilen model/table/key/field eşlemesini kabul eder; bilinmeyen model/alan, eksik anahtar ve güvenli olmayan identifier fail-closed reddedilir.
- SQL değerleri placeholder parametreleriyle taşınır; runtime değerleri SQL identifier veya SQL metni olamaz.
- Native/WASM eşdeğerlik testi capability eksikliğinin iki hedefte de yazma olmadan fail-closed kaldığını doğrular.
- Yeni Command desteği capability/import yüzeyini dolaylı biçimde genişletemez.
- Runtime davranışı bulunan bir komut için referans runtime ↔ WASM/native equivalence kanıtlanmadan kapsam tamamlandı sayılmaz.

## Sıradaki kabul dilimi

`sakla` için ABI/capability çekirdeği, parser/AST → mutation-ABI shape binding, authoritative semantic metadata, backend host-mutation doğrulaması, transaction-backed host write, kalıcı SQLite adapterı, native↔WASM kalıcı-adapter equivalence regression kapısı ve kaynak runtime slotunu bu zincire bağlayan fail-closed execution köprüsü vardır. Sıradaki gerçek eksik dilim aynı gerçek `.shn` kaynak programını referans runtime ile çalıştırıp gözlemlenen kalıcı durum/çıktıyı native ve WASM sonuçlarıyla uçtan uca karşılaştırmaktır. Bu equivalence kapısı kapanmadan `sakla` desteklenmiş sayılmaz.

Genel proje ilerlemesi Aşama 10 tamamen kapanana kadar `%87` olarak kalır.
