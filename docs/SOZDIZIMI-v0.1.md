# Şahin Sözdizimi v0.1

> Durum: deneysel taslak. Amaç başka dillerin Türkçe eşleniğini üretmek değil, tek ve tutarlı bir uygulama modeli kurmaktır.

## Dosya

Önerilen uzantı: `.shn`

Kaynak kod: UTF-8.

## Temel değerler

```shn
ad = "Tayfun"
yaş = 30
aktif = evet
ikincil = hayır
açıklama = yok
fiyat = 249,90₺
```

`evet`, `hayır`, `yok` dilin değerleridir. Para tipi ilk sınıf standart tip olarak planlanır.

## Veri aktarımı

`<-` bir kaynaktan değer alma/bağlama operatörüdür. Atama `=` ile aynı anlamda değildir.

```shn
ürünler <- Ürün.tümü
profil <- oturum.kullanıcı
```

`=` yerel değeri tanımlar/değiştirir; `<-` veri kaynağına bağlanan veya sonuç alan ifadeyi belirtir. Reaktif ekranlarda `<-` bağımlılığı yeniden değerlendirebilir.

## Koşul

Koşul ifadenin sonuna gelir:

```shn
yaş >= 18 ise
    bildir "Giriş serbest"
yoksa
    bildir "Giriş reddedildi"
```

Bu yapı Python/JS `if (...)` kalıbının Türkçesi değildir; Şahin'de koşul bir ifade son eki olarak modellenir.

## Eşleştirme

Uzun koşul zincirleri yerine değer eşleştirme:

```shn
duruma göre sipariş.durum
    "hazır" -> bildir "Sipariş hazır"
    "yolda" -> bildir "Kurye yolda"
    diğer -> bildir "İşleniyor"
```

## Akış

Genel çağrılabilir davranış `akış` ile tanımlanır.

```shn
akış toplam a, b
    ver a + b
```

Tek satır:

```shn
akış toplam a, b => a + b
```

`akış`, Python `def` veya JS `function` kelimesinin çevirisi değil; veri girişi, çıktı, hata ve yetki sınırları olan Şahin çalışma birimidir.

## Koleksiyon akışı

```shn
aktifler <- kullanıcılar
    | seç aktif
    | sırala ad
    | ilk 20
```

Boru hattı (`|`) sorgu, veri dönüşümü ve akışlarda ortak operatördür.

## Döngü

```shn
her ürün içinden ürünler
    yaz ürün.ad
```

Sabit sayı aralığı:

```shn
her sayı 1..10
    yaz sayı
```

## Kayıt

```shn
kayıt Kullanıcı
    ad: yazı gerekli
    eposta: eposta gerekli benzersiz
    yaş: sayı
    katılım: zaman otomatik
```

`kayıt` veri tablosu değildir. Aynı tanım domain modeli, doğrulama, serileştirme ve kalıcı veri şeması için kullanılabilir.

## Veri erişimi

```shn
yetişkinler <- Kullanıcı.tümü
    | seç yaş >= 18
    | sırala ad
    | ilk 50
```

Şahin geliştiricisi SQL dizgesi üretmek zorunda değildir. Veri sağlayıcısı bu ifade ağacını güvenli sorguya dönüştürür.

## Ekran

```shn
ekran Ana
    başlık "Hoş geldin"
    metin "Tek dille uygulama geliştir."

    eylem "Başla" -> başla
```

`ekran` DOM değildir. Derleyici bunu web DOM, native view veya başka hedeflere uyarlayabilecek soyut bir UI ağacı olarak yorumlar.

## Tekrarlı ekran içeriği

```shn
ekran Ürünler
    ürünler <- Ürün.tümü

    her ürün içinden ürünler
        kart
            başlık ürün.ad
            metin ürün.fiyat
            eylem "Sepete ekle" -> sepeteEkle ürün
```

## Görünüm

```shn
görünüm Ana
    zemin koyu
    yazı açık
    aralık 24

    kart
        köşe 14
        dolgu yüzey
        aralık 12
```

Görünüm kuralları CSS seçicileri değildir. Ekran ağacındaki semantik öğe/rol ve tema değerleriyle çalışır.

## Olay

```shn
olay uygulama.açıldı
    hazırla

olay bağlantı.koptu
    bildir "Bağlantı kesildi"
```

## Uç / ağ servisi

```shn
uç GET "/ürün/{id}"
    ürün <- Ürün.bul id

    ürün yok ise
        cevap 404, "Ürün bulunamadı"
        bitir

    cevap ürün
```

HTTP ayrıntıları gerektiğinde görünür olabilir; fakat veri doğrulama ve serileştirme varsayılan olarak Şahin çalışma zamanı tarafından yönetilir.

## İş / otomasyon

```shn
iş stokKontrol her 10 dakika
    azalanlar <- Ürün.tümü | seç stok < 5
    azalanlar boş değil ise
        bildir yöneticiler, "Stok azalıyor"
```

## Hata akışı

```shn
dene
    profil <- uzak.profil al
olmazsa hata
    bildir "Profil alınamadı: {hata.mesaj}"
```

## Metin yerleştirme

```shn
yaz "Merhaba {ad}"
```

## Tip yaklaşımı

Tipler çoğunlukla çıkarılır:

```shn
adet = 4
ad = "Şahin"
```

Sınır noktalarında açık tip önerilir:

```shn
akış fiyatHesapla adet: sayı, birim: para -> para
    ver adet * birim
```

## Tasarımda özellikle kaçınılan kalıplar

Şahin çekirdeğinde kullanıcıya aşağıdakileri zorunlu kılmama hedefi vardır:

- `{ ... }` blokları
- `;`
- HTML açılış/kapanış etiketleri
- CSS selector/specificity zinciri
- `function`, `def`, `self`, `this`, `__init__`
- SQL metin sorguları
- callback/promise zincirleri
- framework yaşam döngüsü ezberleri

Bunların altında yatan yetenekler korunur; yalnızca kullanıcı modeli sadeleştirilir.
