from __future__ import annotations

from dataclasses import dataclass

from .types import TypeKind


@dataclass(frozen=True, slots=True)
class TypeSpec:
    """Şahin'in birleşik tip çekirdeği.

    TypeSpec bir başka dilin union sözdizimini taklit etmez; aynı değerin
    çalışmanın farklı yollarında alabileceği olası Şahin türlerini taşır.
    Üyeler kanonik sırada saklanır ve tekrar içermez.
    """

    members: frozenset[TypeKind]

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError("Şahin TypeSpec en az bir tür içermelidir.")

    @classmethod
    def of(cls, *members: TypeKind) -> "TypeSpec":
        return cls(frozenset(members))

    @classmethod
    def optional(cls, member: TypeKind) -> "TypeSpec":
        if member is TypeKind.YOK:
            return cls.of(TypeKind.YOK)
        return cls.of(member, TypeKind.YOK)

    @property
    def is_optional(self) -> bool:
        return TypeKind.YOK in self.members and len(self.members) > 1

    @property
    def can_be_yok(self) -> bool:
        return TypeKind.YOK in self.members

    @property
    def is_unknown(self) -> bool:
        return self.members == frozenset({TypeKind.BILINMEYEN})

    def without(self, member: TypeKind) -> "TypeSpec":
        remaining = self.members - {member}
        if not remaining:
            return TypeSpec.of(TypeKind.BILINMEYEN)
        return TypeSpec(frozenset(remaining))

    def narrowed_present(self) -> "TypeSpec":
        """`değer yok` koşulunun hayır dalındaki güvenli türü."""
        return self.without(TypeKind.YOK)

    def joined(self, other: "TypeSpec") -> "TypeSpec":
        if self.is_unknown or other.is_unknown:
            return TypeSpec.of(TypeKind.BILINMEYEN)
        return TypeSpec(self.members | other.members)

    def accepts(self, actual: "TypeSpec") -> bool:
        """Atama/parametre sözleşmesi için güvenli kapsama kontrolü."""
        if self.is_unknown or actual.is_unknown:
            return True
        if actual.members <= self.members:
            return True

        # Şahin'in mevcut sayısal genişletme kuralını birleşik tipe taşır.
        for got in actual.members:
            if got in self.members:
                continue
            if got is TypeKind.SAYI and (
                TypeKind.ONDALIK in self.members or TypeKind.PARA in self.members
            ):
                continue
            return False
        return True

    def display(self) -> str:
        order = [
            TypeKind.YAZI,
            TypeKind.SAYI,
            TypeKind.ONDALIK,
            TypeKind.PARA,
            TypeKind.MANTIK,
            TypeKind.YOK,
            TypeKind.AKIS,
            TypeKind.KAYIT,
            TypeKind.EKRAN,
            TypeKind.GORUNUM,
            TypeKind.UYGULAMA,
            TypeKind.BILINMEYEN,
        ]
        labels = [kind.value for kind in order if kind in self.members]
        if self.is_optional and len(self.members) == 2:
            present = next(kind for kind in order if kind in self.members and kind is not TypeKind.YOK)
            return f"{present.value} veya yok"
        return " veya ".join(labels)
