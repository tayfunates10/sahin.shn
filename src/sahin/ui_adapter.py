from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from .ui import Dugum, RenderIR, Rol, UiError


@dataclass(frozen=True, slots=True)
class HostDugum:
    """Browser/desktop/WASM adapterlarının ortak, DOM bağımsız hedef sözleşmesi."""

    tur: str
    kimlik: str
    nitelikler: tuple[tuple[str, Any], ...] = ()
    metin: str | None = None
    cocuklar: tuple["HostDugum", ...] = ()

    def sozluk(self) -> dict[str, Any]:
        sonuc: dict[str, Any] = {
            "tür": self.tur,
            "kimlik": self.kimlik,
            "nitelikler": dict(self.nitelikler),
        }
        if self.metin is not None:
            sonuc["metin"] = self.metin
        if self.cocuklar:
            sonuc["çocuklar"] = [child.sozluk() for child in self.cocuklar]
        return sonuc


class BrowserAdapter:
    """RenderIR -> güvenli host ağacı.

    Bu sınıf HTML metni üretmez ve kullanıcı içeriğini executable markup olarak
    yorumlamaz. Gerçek browser/WASM köprüsü bu sözleşmenin arkasında kalır.
    """

    _TUR = {
        Rol.EKRAN: "ekran",
        Rol.BOLUM: "bölüm",
        Rol.BASLIK: "başlık",
        Rol.METIN: "metin",
        Rol.EYLEM: "eylem",
        Rol.GIRIS: "giriş",
    }

    def aktar(self, ir: RenderIR) -> HostDugum:
        if ir.surum != 1:
            raise UiError(f"SHN-U301: desteklenmeyen RenderIR sürümü: {ir.surum}")
        return self._dugum(ir.kok)

    def _dugum(self, node: Dugum) -> HostDugum:
        attrs: dict[str, Any] = {
            "rol": node.rol.value,
            "odaklanabilir": node.odaklanabilir,
        }
        if node.etiket is not None:
            attrs["erişilebilir_etiket"] = escape(node.etiket, quote=True)
        if node.olaylar:
            attrs["olaylar"] = tuple(
                (event.ad, event.akis, tuple(event.veri)) for event in node.olaylar
            )
        gorunum = node.gorunum
        stil = {
            "boşluk": _olcu(gorunum.bosluk),
            "iç_bosluk": _olcu(gorunum.ic_bosluk),
            "genişlik": _olcu(gorunum.genislik),
            "yükseklik": _olcu(gorunum.yukseklik),
            "vurgu": gorunum.vurgu,
            "yazı_boyutu": _olcu(gorunum.yazi_boyutu),
            "hizalama": gorunum.hizalama,
        }
        attrs["görünüm"] = tuple(sorted((k, v) for k, v in stil.items() if v is not None))
        return HostDugum(
            tur=self._TUR[node.rol],
            kimlik=node.kimlik,
            nitelikler=tuple(sorted(attrs.items(), key=lambda item: item[0])),
            metin=escape(node.icerik, quote=True) if node.icerik is not None else None,
            cocuklar=tuple(self._dugum(child) for child in node.cocuklar),
        )


def _olcu(value: Any) -> tuple[float, str] | None:
    if value is None:
        return None
    return (value.deger, value.birim)
