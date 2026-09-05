# Aşama 10 — Member mutation değerlendirme sırası

`Member` hedefli `artır/azalt` entegrasyonu, mevcut kernel'i ana `_Lowerer` zincirine doğrudan bağlamadan önce referans runtime değerlendirme sırasını byte/opcode seviyesinde korumalıdır.

## Referans runtime sözleşmesi

`ürün.stok artır miktar` için gözlemlenebilir sıra şöyledir:

1. `ürün.stok` tamamen değerlendirilir ve mevcut alan değeri okunur.
2. `miktar` ifadesi değerlendirilir.
3. Toplama/çıkarma sonucu hesaplanır.
4. Yazma için `command.subject.target` yeniden değerlendirilir.
5. Son değer yalnız bu ikinci owner üzerinde `member_store` eşdeğeri davranışla yazılır.

Bu ikinci owner değerlendirmesi önemlidir. `miktar` bir çağrı/yan etki üzerinden `ürün` kökünü veya nested owner zincirini değiştirirse, yazma ilk okumanın owner snapshot'ına değil, miktar değerlendirildikten ve aritmetik tamamlandıktan sonra yeniden çözülen owner'a gider.

## Mevcut kernel ile fark

`member_mutation_lowering.lower_member_mutation_kernel()` bugün tek bir `target_temp` alıyor ve hem `member` okumasında hem `member_store` yazmasında aynı temp'i kullanıyor. Bu yapı yalnız owner zincirinin aradaki değerlendirmeler boyunca değişmeyeceği kanıtlanmışsa eşdeğerdir. Genel `Command` ABI için bu kanıt henüz yoktur.

Bu nedenle ana `_Lowerer` entegrasyonu şu anda fail-closed kalmalıdır. Doğru sonraki dilim:

- read-owner ve write-owner değerlendirmelerini ayrı açık IR adımları olarak modellemek,
- sıra sözleşmesini `read -> amount -> binary -> write-owner -> member_store` biçiminde sabitlemek,
- nested member zincirlerinde aynı sırayı korumak,
- CFG/use-def validator'a `member_store` operandlarını eklemek,
- WASM/native equivalence yürütücüsünde mutable dict write davranışını referans runtime ile karşılaştırmak,
- aritmetik hata olduğunda write-owner değerlendirmesinin hiç yapılmadığını regresyon testiyle kanıtlamak.

Kalite eşiği düşürülmeyecek; owner snapshot optimizasyonu ancak gözlemlenebilir eşdeğerlik kanıtı varsa yapılabilir.
