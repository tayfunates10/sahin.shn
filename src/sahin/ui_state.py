from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping
import unicodedata

from .ui import Gorunum, Olcu, UiError


@dataclass(frozen=True, slots=True)
class TasarimTokenlari:
    """Şahin görünümünün selector/DOM bağımsız tasarım sözleşmesi."""

    bosluklar: tuple[tuple[str, Olcu], ...] = ()
    tipografi: tuple[tuple[str, Olcu], ...] = ()
    vurgular: tuple[tuple[str, str], ...] = ()

    @classmethod
    def kur(
        cls,
        *,
        bosluklar: Mapping[str, Olcu] | None = None,
        tipografi: Mapping[str, Olcu] | None = None,
        vurgular: Mapping[str, str] | None = None,
    ) -> "TasarimTokenlari":
        def isimli(items: Mapping[str, Any] | None) -> tuple[tuple[str, Any], ...]:
            sonuc = []
            for ad, deger in (items or {}).items():
                temiz = _nfc(ad)
                if not temiz or any(ch.isspace() for ch in temiz):
                    raise UiError("SHN-U201: tasarım token adı boş veya boşluklu olamaz")
                sonuc.append((temiz, deger))
            return tuple(sorted(sonuc, key=lambda item: item[0]))

        vurgu_items = []
        for ad, deger in (vurgular or {}).items():
            temiz_ad = _nfc(ad)
            if not temiz_ad or any(ch.isspace() for ch in temiz_ad):
                raise UiError("SHN-U201: tasarım token adı boş veya boşluklu olamaz")
            vurgu_items.append((temiz_ad, _nfc(str(deger))))
        return cls(isimli(bosluklar), isimli(tipografi), tuple(sorted(vurgu_items)))

    def bosluk(self, ad: str) -> Olcu:
        return _bul(self.bosluklar, ad, "boşluk")

    def yazi(self, ad: str) -> Olcu:
        return _bul(self.tipografi, ad, "tipografi")

    def vurgu(self, ad: str) -> str:
        return _bul(self.vurgular, ad, "vurgu")


@dataclass(frozen=True, slots=True)
class Esik:
    ad: str
    en_az: int = 0
    en_cok: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ad", _nfc(self.ad))
        if not self.ad:
            raise UiError("SHN-U203: responsive eşik adı boş olamaz")
        if self.en_az < 0 or (self.en_cok is not None and self.en_cok < self.en_az):
            raise UiError("SHN-U204: geçersiz responsive eşik aralığı")

    def uyar(self, genislik: int) -> bool:
        return genislik >= self.en_az and (self.en_cok is None or genislik <= self.en_cok)


@dataclass(frozen=True, slots=True)
class ResponsiveKural:
    esik: Esik
    gorunum: Gorunum


@dataclass(frozen=True, slots=True)
class ResponsiveGorunum:
    temel: Gorunum = field(default_factory=Gorunum)
    kurallar: tuple[ResponsiveKural, ...] = ()

    def __post_init__(self) -> None:
        adlar = [kural.esik.ad for kural in self.kurallar]
        if len(set(adlar)) != len(adlar):
            raise UiError("SHN-U205: responsive eşik adları yinelenemez")

    def coz(self, genislik: int) -> Gorunum:
        if genislik < 0:
            raise UiError("SHN-U206: görünüm genişliği negatif olamaz")
        sonuc = self.temel
        for kural in sorted(self.kurallar, key=lambda item: item.esik.en_az):
            if kural.esik.uyar(genislik):
                sonuc = _gorunum_birlestir(sonuc, kural.gorunum)
        return sonuc


@dataclass(frozen=True, slots=True)
class Durum:
    """UI state için immutable, sürümlü ve deterministik değer deposu."""

    surum: int = 0
    degerler: tuple[tuple[str, Any], ...] = ()

    @classmethod
    def kur(cls, degerler: Mapping[str, Any] | None = None) -> "Durum":
        return cls(0, _normalize_items(degerler or {}))

    def al(self, ad: str, varsayilan: Any = None) -> Any:
        anahtar = _nfc(ad)
        return dict(self.degerler).get(anahtar, varsayilan)

    def guncelle(self, degisiklikler: Mapping[str, Any], *, beklenen_surum: int | None = None) -> "Durum":
        if beklenen_surum is not None and beklenen_surum != self.surum:
            raise UiError(
                f"SHN-U207: state sürüm çakışması; beklenen {beklenen_surum}, mevcut {self.surum}"
            )
        yeni = dict(self.degerler)
        for ad, deger in degisiklikler.items():
            anahtar = _nfc(ad)
            if not anahtar:
                raise UiError("SHN-U208: state anahtarı boş olamaz")
            yeni[anahtar] = deger
        return Durum(self.surum + 1, _normalize_items(yeni))


@dataclass(frozen=True, slots=True)
class StateIslemi:
    ad: str
    alanlar: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ad", _nfc(self.ad))
        object.__setattr__(self, "alanlar", frozenset(_nfc(ad) for ad in self.alanlar))
        if not self.ad:
            raise UiError("SHN-U209: state işlemi adı boş olamaz")

    def uygula(
        self,
        durum: Durum,
        degisiklikler: Mapping[str, Any],
        *,
        beklenen_surum: int | None = None,
    ) -> Durum:
        izin_disinda = {_nfc(ad) for ad in degisiklikler} - self.alanlar
        if izin_disinda:
            alan = sorted(izin_disinda)[0]
            raise UiError(f"SHN-U210: '{self.ad}' işlemi '{alan}' alanını değiştiremez")
        return durum.guncelle(degisiklikler, beklenen_surum=beklenen_surum)


def _gorunum_birlestir(temel: Gorunum, ek: Gorunum) -> Gorunum:
    return Gorunum(
        bosluk=ek.bosluk if ek.bosluk is not None else temel.bosluk,
        ic_bosluk=ek.ic_bosluk if ek.ic_bosluk is not None else temel.ic_bosluk,
        genislik=ek.genislik if ek.genislik is not None else temel.genislik,
        yukseklik=ek.yukseklik if ek.yukseklik is not None else temel.yukseklik,
        vurgu=ek.vurgu if ek.vurgu is not None else temel.vurgu,
        yazi_boyutu=ek.yazi_boyutu if ek.yazi_boyutu is not None else temel.yazi_boyutu,
        hizalama=ek.hizalama if ek.hizalama is not None else temel.hizalama,
    )


def _normalize_items(values: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    normalized: dict[str, Any] = {}
    for ad, deger in values.items():
        anahtar = _nfc(str(ad))
        if not anahtar:
            raise UiError("SHN-U208: state anahtarı boş olamaz")
        normalized[anahtar] = deger
    return tuple(sorted(normalized.items(), key=lambda item: item[0]))


def _bul(items: Iterable[tuple[str, Any]], ad: str, tur: str) -> Any:
    anahtar = _nfc(ad)
    for item_ad, deger in items:
        if item_ad == anahtar:
            return deger
    raise UiError(f"SHN-U202: bilinmeyen {tur} tokenı: {anahtar}")


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)
