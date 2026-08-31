# Şahin Standart Kütüphane v0.1

Bu belge Şahin'in standart kütüphane çekirdeğinin sözleşmesini tanımlar. Amaç Python/JavaScript/PHP API'lerini Türkçeleştirmek değil; Şahin'in güvenli-varsayılan, veri akışı ve capability modeline uygun küçük ve tutarlı bir yüzey sunmaktır.

## Saf çekirdek

`Metin`, `Sayi`, `Koleksiyon`, `An` ve `Json` saf/deterministik işlemler sunar. Türkçe ve diğer Unicode girdiler NFC biçimine normalize edilir. Para işlemleri ikili kayan nokta yerine `Decimal` tabanlıdır.

## Dış dünya

`Dosya` ve `Ag` hiçbir yetkiyi kendiliğinden edinmez. Host tarafından verilen `CapabilitySet` içinde ilgili capability yoksa işlem dış kaynağa dokunmadan `SHN-G001` ile reddedilir.

- `Dosya.oku` → `dosya:oku`
- `Dosya.yaz` → `dosya:yaz`
- `Ag.getir` → `ağ`

Dosya ve ağ okumaları varsayılan boyut sınırına sahiptir. Ağ isteklerinde timeout zorunlu güvenlik sınırlarıyla denetlenir.

## Veri çözümleme

`Json.coz` UTF-8 ve boyut sınırını doğrular. Bozuk veri kontrolsüz host exception'ı olarak dışarı çıkmaz; Şahin tanı kodlarıyla `CozumlemeHatasi` / `VeriSiniriHatasi` üretir.

## Güvenlik

`Guven` yalnızca yüksek seviyeli güvenli yüzeyi sunar:

- CSPRNG ile rastgele bayt
- SHA-256/384/512 özet
- HMAC-SHA-256/384/512
- sabit-zaman karşılaştırmalı HMAC doğrulama

MD5/SHA-1, ham şifre primitive'leri, ECB veya elle nonce yönetimi gibi tehlikeli düşük seviye yüzeyler v0.1 standart kütüphanesinde yer almaz.

## Kalite sözleşmesi

Aşama 5 tamamlanmış sayılmadan önce saf API, Unicode, bozuk/aşırı büyük JSON, capability reddi, dosya sınırı, ağın capability kontrolünden önce çağrılmaması ve kripto güvenlik sınırları regression testleriyle doğrulanmalıdır. Python 3.11/3.12/3.13 CI matrisi tamamen yeşil olmalıdır.
