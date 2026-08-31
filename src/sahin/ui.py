from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from html import escape
from typing import Any, Iterable, Mapping
import unicodedata


class UiError(ValueError):
    """Şahin arayüz/görünüm sözleşmesi ihlali."""


class Rol(str, Enum):
    EKRAN = "ekran"
    BOLUM = "bölüm"
    BASLIK = "başlık"
    METIN = "metin"
    EYLEM = "eylem"
    GIRIS = "giriş"


@dataclass(frozen=True, slots=True)
class Olcu:
    deger: float
    birim: str = "adım"

    def __post_init__(self) -> None:
        if self.deger < 0:
            raise UiError("SHN-U101: ölçü negatif olamaz")
        if self.birim not in {"adım", "oran", "px"}:
            raise UiError(f"SHN-U102: desteklenmeyen ölçü birimi: {self.birim}")


@dataclass(frozen=True, slots=True)
class Gorunum:
    bosluk: Olcu | None = None
    ic_bosluk: Olcu | None = None
    genislik: Olcu | None = None
    yukseklik: Olcu | None = None
    vurgu: str | None = None
    yazi_boyutu: Olcu | None = None
    hizalama: str | None = None

    def __post_init__(self) -> None:
        if self.hizalama not in {None, "baş", "orta", "son", "yay"}:
            raise UiError(f"SHN-U103: geçersiz hizalama: {self.hizalama}")
        if self.vurgu is not None:
            object.__setattr__(self, "vurgu", _nfc(self.vurgu))


@dataclass(frozen=True, slots=True)
class Olay:
    ad: str
    akis: str
    veri: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ad", _nfc(self.ad))
        object.__setattr__(self, "akis", _nfc(self.akis))
        if not self.ad or not self.akis:
            raise UiError("SHN-U104: olay adı ve akışı boş olamaz")

    @classmethod
    def kur(cls, ad: str, akis: str, veri: Mapping[str, Any] | None = None) -> "Olay":
        return cls(ad, akis, tuple(sorted((veri or {}).items())))


@dataclass(frozen=True, slots=True)
class Dugum:
    kimlik: str
    rol: Rol
    icerik: str | None = None
    etiket: str | None = None
    gorunum: Gorunum = field(default_factory=Gorunum)
    olaylar: tuple[Olay, ...] = ()
    cocuklar: tuple["Dugum", ...] = ()
    odaklanabilir: bool = False

    def __post_init__(self) -> None:
        kimlik = _nfc(self.kimlik)
        if not kimlik or any(ch.isspace() for ch in kimlik):
            raise UiError("SHN-U105: düğüm kimliği boşluk içermeyen bir değer olmalı")
        object.__setattr__(self, "kimlik", kimlik)
        if self.icerik is not None:
            object.__setattr__(self, "icerik", _nfc(str(self.icerik)))
        if self.etiket is not None:
            object.__setattr__(self, "etiket", _nfc(self.etiket))

        if self.rol in {Rol.EYLEM, Rol.GIRIS} and not (self.etiket or self.icerik):
            raise UiError("SHN-U106: etkileşimli düğüm erişilebilir etikete sahip olmalı")
        if self.rol is Rol.EYLEM and not self.odaklanabilir:
            object.__setattr__(self, "odaklanabilir", True)

        seen: set[str] = set()
        for child in self.cocuklar:
            if child.kimlik in seen:
                raise UiError(f"SHN-U107: aynı ebeveyn altında yinelenen kimlik: {child.kimlik}")
            seen.add(child.kimlik)

    def cocuk_ekle(self, *dugumler: "Dugum") -> "Dugum":
        return replace(self, cocuklar=self.cocuklar + tuple(dugumler))

    def gorunumle(self, **degisiklikler: Any) -> "Dugum":
        return replace(self, gorunum=replace(self.gorunum, **degisiklikler))


@dataclass(frozen=True, slots=True)
class RenderIR:
    surum: int
    kok: Dugum

    def sozluk(self) -> dict[str, Any]:
        return {"sürüm": self.surum, "kök": _dugum_sozluk(self.kok)}


@dataclass(frozen=True, slots=True)
class GuvenliMetin:
    deger: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "deger", _nfc(self.deger))

    def host_metni(self) -> str:
        """Browser/HTML adapterları için güvenli varsayılan kaçış."""
        return escape(self.deger, quote=True)


@dataclass(frozen=True, slots=True)
class HamIcerik:
    deger: str
    izin: bool = False

    def __post_init__(self) -> None:
        if not self.izin:
            raise UiError("SHN-U108: ham içerik açık güvenlik izni olmadan kullanılamaz")
        object.__setattr__(self, "deger", _nfc(self.deger))


def ekran(kimlik: str, *cocuklar: Dugum, etiket: str | None = None) -> RenderIR:
    kok = Dugum(kimlik=kimlik, rol=Rol.EKRAN, etiket=etiket, cocuklar=tuple(cocuklar))
    _tum_kimlikleri_dogrula(kok)
    return RenderIR(surum=1, kok=kok)


def baslik(kimlik: str, icerik: str, *, etiket: str | None = None) -> Dugum:
    return Dugum(kimlik, Rol.BASLIK, icerik=icerik, etiket=etiket)


def metin(kimlik: str, icerik: str) -> Dugum:
    return Dugum(kimlik, Rol.METIN, icerik=icerik)


def kart(kimlik: str, *cocuklar: Dugum, etiket: str | None = None) -> Dugum:
    return Dugum(kimlik, Rol.BOLUM, etiket=etiket, cocuklar=tuple(cocuklar))


def eylem(kimlik: str, etiket: str, akis: str, *, veri: Mapping[str, Any] | None = None) -> Dugum:
    return Dugum(
        kimlik,
        Rol.EYLEM,
        etiket=etiket,
        olaylar=(Olay.kur("etkinleştir", akis, veri),),
        odaklanabilir=True,
    )


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _tum_kimlikleri_dogrula(kok: Dugum) -> None:
    seen: set[str] = set()

    def walk(node: Dugum) -> None:
        if node.kimlik in seen:
            raise UiError(f"SHN-U109: arayüz ağacında yinelenen kimlik: {node.kimlik}")
        seen.add(node.kimlik)
        for child in node.cocuklar:
            walk(child)

    walk(kok)


def _dugum_sozluk(node: Dugum) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kimlik": node.kimlik,
        "rol": node.rol.value,
        "odaklanabilir": node.odaklanabilir,
    }
    if node.icerik is not None:
        result["içerik"] = node.icerik
    if node.etiket is not None:
        result["etiket"] = node.etiket
    style = {name: _olcu_sozluk(value) if isinstance(value, Olcu) else value for name, value in (
        ("boşluk", node.gorunum.bosluk),
        ("iç_bosluk", node.gorunum.ic_bosluk),
        ("genişlik", node.gorunum.genislik),
        ("yükseklik", node.gorunum.yukseklik),
        ("vurgu", node.gorunum.vurgu),
        ("yazı_boyutu", node.gorunum.yazi_boyutu),
        ("hizalama", node.gorunum.hizalama),
    ) if value is not None}
    if style:
        result["görünüm"] = style
    if node.olaylar:
        result["olaylar"] = [
            {"ad": event.ad, "akış": event.akis, "veri": dict(event.veri)} for event in node.olaylar
        ]
    if node.cocuklar:
        result["çocuklar"] = [_dugum_sozluk(child) for child in node.cocuklar]
    return result


def _olcu_sozluk(value: Olcu) -> dict[str, Any]:
    return {"değer": value.deger, "birim": value.birim}
