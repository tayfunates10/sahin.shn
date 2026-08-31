from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Capability(str, Enum):
    DOSYA_OKU = "dosya:oku"
    DOSYA_YAZ = "dosya:yaz"
    AG = "ağ"
    VERI_OKU = "veri:oku"
    VERI_YAZ = "veri:yaz"
    SAAT = "saat"
    ORTAM = "ortam"


class CapabilityError(PermissionError):
    pass


@dataclass(slots=True)
class CapabilitySet:
    """Şahin dış kaynak erişimi için varsayılan-kapalı yetki kümesi.

    Hiçbir capability otomatik verilmez. Runtime/host bir dış kaynak işlemi
    yapmadan önce require() çağırmak zorundadır.
    """

    granted: set[Capability] = field(default_factory=set)

    def allows(self, capability: Capability) -> bool:
        return capability in self.granted

    def require(self, capability: Capability) -> None:
        if not self.allows(capability):
            raise CapabilityError(
                f"SHN-G001: '{capability.value}' yetkisi verilmedi. "
                "Şahin dış kaynak erişimini varsayılan olarak kapalı tutar."
            )

    def grant(self, *capabilities: Capability) -> "CapabilitySet":
        self.granted.update(capabilities)
        return self

    def revoke(self, *capabilities: Capability) -> "CapabilitySet":
        for capability in capabilities:
            self.granted.discard(capability)
        return self
