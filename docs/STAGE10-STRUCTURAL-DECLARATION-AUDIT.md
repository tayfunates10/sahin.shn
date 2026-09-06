# Aşama 10 — Yapısal Declaration ABI denetimi

Bu denetim `uygulama`, `ekran`, `görünüm`, `uç`, `iş` ve `olay` Declaration türlerinin Stage 10 sınırını açıkça kilitler.

## Mevcut referans semantiği

Referans runtime yalnız `akış` Declaration'ını çağrılabilir değer olarak kaydeder. Diğer Declaration türleri çalışma zamanında yürütülmez; UI/veri/sunucu motorlarının yapısal girdileri olarak no-op kalır. Bu nedenle Stage 10 IR katmanı bu türlere executable opcode veya yan etki uydurmamalıdır.

## Fail-closed sözleşmesi

- `uygulama`, `ekran`, `görünüm`, `uç`, `iş` ve `olay` IR v1 executable instruction'a sessizce dönüştürülemez.
- Declaration gövdeleri IR lowering sırasında yürütülmüş gibi ele alınamaz.
- İlgili UI/server/data ABI sözleşmeleri tanımlanana kadar `IRLoweringError` korunur.
- Bu sınır capability/import yüzeyini genişletmez.
- Referans runtime no-op davranışı ve IR fail-closed davranışı regression testleriyle kilitlenir.

## Sonraki kabul sırası

1. Her Declaration ailesi için gözlemlenebilir metadata alanlarını tanımla.
2. İsim/header/body sözleşmesini kendi motoru için ayrı fail-closed ABI ile doğrula.
3. Gerekli backend/capability sınırını açıkça tanımla; genel amaçlı runtime opcode uydurma.
4. Referans motor davranışı ile adapter davranışı eşdeğerlik testlerinden geçmeden coverage durumunu tamamlanmış sayma.

Bu denetim tek başına Declaration kapsamını tamamlamaz; genel ilerleme `%87` olarak kalır.
