from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import unicodedata
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from .capabilities import Capability, CapabilitySet

T = TypeVar("T")
U = TypeVar("U")


class StdlibError(ValueError):
    """Şahin standart kütüphanesi kontrollü hata tabanı."""


class VeriSiniriHatasi(StdlibError):
    pass


class CozumlemeHatasi(StdlibError):
    pass


@dataclass(frozen=True, slots=True)
class Sonuc:
    deger: Any = None
    hata: str | None = None

    @property
    def basarili(self) -> bool:
        return self.hata is None


class Metin:
    @staticmethod
    def duzelt(deger: str) -> str:
        return unicodedata.normalize("NFC", deger)

    @classmethod
    def uzunluk(cls, deger: str) -> int:
        return len(cls.duzelt(deger))

    @classmethod
    def bol(cls, deger: str, ayirac: str | None = None) -> list[str]:
        return [cls.duzelt(x) for x in cls.duzelt(deger).split(ayirac)]

    @classmethod
    def birlestir(cls, degerler: Iterable[str], ayirac: str = "") -> str:
        return cls.duzelt(ayirac.join(cls.duzelt(x) for x in degerler))

    @classmethod
    def ara(cls, deger: str, aranan: str) -> int | None:
        konum = cls.duzelt(deger).find(cls.duzelt(aranan))
        return None if konum < 0 else konum

    @classmethod
    def kucult(cls, deger: str) -> str:
        return cls.duzelt(deger).lower()

    @classmethod
    def buyut(cls, deger: str) -> str:
        return cls.duzelt(deger).upper()


class Sayi:
    @staticmethod
    def ondalik(deger: Any) -> Decimal:
        try:
            return Decimal(str(deger))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise StdlibError(f"SHN-S101: sayı dönüştürülemedi: {deger!r}") from exc

    @classmethod
    def yuvarla(cls, deger: Any, basamak: int = 0) -> Decimal:
        if basamak < 0 or basamak > 28:
            raise StdlibError("SHN-S102: basamak 0..28 arasında olmalı")
        olcek = Decimal(1).scaleb(-basamak)
        return cls.ondalik(deger).quantize(olcek, rounding=ROUND_HALF_UP)

    @classmethod
    def para(cls, deger: Any, para_birimi: str = "TRY") -> str:
        kod = para_birimi.strip().upper()
        if len(kod) != 3 or not kod.isalpha():
            raise StdlibError("SHN-S103: para birimi üç harfli kod olmalı")
        return f"{cls.yuvarla(deger, 2):.2f} {kod}"

    @staticmethod
    def aralik(baslangic: int, bitis: int, adim: int = 1) -> list[int]:
        if adim == 0:
            raise StdlibError("SHN-S104: aralık adımı sıfır olamaz")
        return list(range(baslangic, bitis, adim))


class Koleksiyon:
    @staticmethod
    def sec(degerler: Iterable[T], kosul: Callable[[T], bool]) -> list[T]:
        return [x for x in degerler if kosul(x)]

    @staticmethod
    def donustur(degerler: Iterable[T], islem: Callable[[T], U]) -> list[U]:
        return [islem(x) for x in degerler]

    @staticmethod
    def sirala(degerler: Iterable[T], anahtar: Callable[[T], Any] | None = None) -> list[T]:
        return sorted(degerler, key=anahtar)

    @staticmethod
    def ilk(degerler: Iterable[T]) -> T | None:
        return next(iter(degerler), None)

    @staticmethod
    def son(degerler: Iterable[T]) -> T | None:
        bulundu = None
        var = False
        for bulundu in degerler:
            var = True
        return bulundu if var else None

    @staticmethod
    def tekillestir(degerler: Iterable[T]) -> list[T]:
        sonuc: list[T] = []
        for deger in degerler:
            if deger not in sonuc:
                sonuc.append(deger)
        return sonuc

    @staticmethod
    def grupla(degerler: Iterable[T], anahtar: Callable[[T], Any]) -> dict[Any, list[T]]:
        sonuc: dict[Any, list[T]] = {}
        for deger in degerler:
            sonuc.setdefault(anahtar(deger), []).append(deger)
        return sonuc


@dataclass(frozen=True, slots=True)
class An:
    deger: datetime

    @classmethod
    def simdi(cls, *, saat: Callable[[], datetime] | None = None) -> "An":
        kaynak = saat or (lambda: datetime.now(timezone.utc))
        deger = kaynak()
        if deger.tzinfo is None:
            deger = deger.replace(tzinfo=timezone.utc)
        return cls(deger.astimezone(timezone.utc))

    def ekle(self, *, saniye: float = 0) -> "An":
        return An(self.deger + timedelta(seconds=saniye))

    def iso(self) -> str:
        return self.deger.isoformat()


class Json:
    VARSAYILAN_SINIR = 1_000_000

    @classmethod
    def coz(cls, metin: str | bytes, *, sinir: int = VARSAYILAN_SINIR) -> Any:
        ham = metin.encode("utf-8") if isinstance(metin, str) else metin
        if sinir <= 0:
            raise VeriSiniriHatasi("SHN-J101: JSON boyut sınırı pozitif olmalı")
        if len(ham) > sinir:
            raise VeriSiniriHatasi(f"SHN-J102: JSON girdisi {sinir} bayt sınırını aştı")
        try:
            return json.loads(ham.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CozumlemeHatasi(f"SHN-J103: JSON çözümlenemedi: {exc}") from exc

    @staticmethod
    def yaz(deger: Any) -> str:
        try:
            return json.dumps(deger, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise CozumlemeHatasi(f"SHN-J104: değer JSON'a dönüştürülemedi: {exc}") from exc


class Dosya:
    @staticmethod
    def oku(yol: str | os.PathLike[str], yetkiler: CapabilitySet, *, sinir: int = 1_000_000) -> str:
        yetkiler.require(Capability.DOSYA_OKU)
        if sinir <= 0:
            raise VeriSiniriHatasi("SHN-D101: dosya boyut sınırı pozitif olmalı")
        p = Path(yol)
        with p.open("rb") as f:
            veri = f.read(sinir + 1)
        if len(veri) > sinir:
            raise VeriSiniriHatasi(f"SHN-D102: dosya {sinir} bayt sınırını aştı")
        try:
            return veri.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CozumlemeHatasi("SHN-D103: dosya UTF-8 değil") from exc

    @staticmethod
    def yaz(yol: str | os.PathLike[str], metin: str, yetkiler: CapabilitySet) -> None:
        yetkiler.require(Capability.DOSYA_YAZ)
        Path(yol).write_text(unicodedata.normalize("NFC", metin), encoding="utf-8")


class Ag:
    @staticmethod
    def getir(url: str, yetkiler: CapabilitySet, *, zaman_asimi: float = 5.0, sinir: int = 1_000_000) -> bytes:
        yetkiler.require(Capability.AG)
        if not url.startswith(("https://", "http://")):
            raise StdlibError("SHN-A101: yalnızca http/https adresleri desteklenir")
        if zaman_asimi <= 0 or zaman_asimi > 60:
            raise StdlibError("SHN-A102: zaman aşımı 0..60 saniye aralığında olmalı")
        if sinir <= 0:
            raise VeriSiniriHatasi("SHN-A103: ağ boyut sınırı pozitif olmalı")
        req = urllib.request.Request(url, headers={"User-Agent": "Sahin-stdlib/0.1"})
        with urllib.request.urlopen(req, timeout=zaman_asimi) as yanit:
            veri = yanit.read(sinir + 1)
        if len(veri) > sinir:
            raise VeriSiniriHatasi(f"SHN-A104: ağ yanıtı {sinir} bayt sınırını aştı")
        return veri


class Guven:
    @staticmethod
    def rastgele_bayt(uzunluk: int = 32) -> bytes:
        if uzunluk < 16 or uzunluk > 4096:
            raise StdlibError("SHN-K101: güvenli rastgele uzunluğu 16..4096 bayt olmalı")
        return secrets.token_bytes(uzunluk)

    @staticmethod
    def ozet(veri: str | bytes, *, algoritma: str = "sha256") -> str:
        if algoritma not in {"sha256", "sha384", "sha512"}:
            raise StdlibError("SHN-K102: izin verilen özetler sha256/sha384/sha512")
        ham = veri.encode("utf-8") if isinstance(veri, str) else veri
        return hashlib.new(algoritma, ham).hexdigest()

    @staticmethod
    def imza(veri: str | bytes, anahtar: bytes, *, algoritma: str = "sha256") -> str:
        if len(anahtar) < 16:
            raise StdlibError("SHN-K103: HMAC anahtarı en az 16 bayt olmalı")
        if algoritma not in {"sha256", "sha384", "sha512"}:
            raise StdlibError("SHN-K104: izin verilen HMAC özetleri sha256/sha384/sha512")
        ham = veri.encode("utf-8") if isinstance(veri, str) else veri
        return hmac.new(anahtar, ham, digestmod=algoritma).hexdigest()

    @staticmethod
    def imza_dogrula(veri: str | bytes, anahtar: bytes, beklenen: str, *, algoritma: str = "sha256") -> bool:
        gercek = Guven.imza(veri, anahtar, algoritma=algoritma)
        return hmac.compare_digest(gercek, beklenen)
