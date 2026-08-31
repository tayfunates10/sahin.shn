from __future__ import annotations

from dataclasses import dataclass, field

from .semantics import TypeKind
from .type_model import TypeSpec


_TYPE_NAMES: dict[str, TypeKind] = {
    "yazı": TypeKind.YAZI,
    "sayı": TypeKind.SAYI,
    "ondalık": TypeKind.ONDALIK,
    "para": TypeKind.PARA,
    "mantık": TypeKind.MANTIK,
    "evet_hayır": TypeKind.MANTIK,
    "yok": TypeKind.YOK,
}


def parse_type_spec(type_name: str | None) -> TypeSpec:
    """Şahin tip adını birleşik TypeSpec modeline çevirir.

    İlk desteklenen birleşik yazım `X veya yok` biçimidir. Amaç parser
    entegrasyonundan önce semantik katmanın tek ve test edilebilir bir
    normalizasyon noktası kullanmasını sağlamaktır.
    """

    if not type_name:
        return TypeSpec.of(TypeKind.BILINMEYEN)

    normalized = " ".join(type_name.strip().split())
    pieces = [piece.strip() for piece in normalized.split(" veya ")]
    members: list[TypeKind] = []
    for piece in pieces:
        kind = _TYPE_NAMES.get(piece)
        if kind is None:
            return TypeSpec.of(TypeKind.BILINMEYEN)
        members.append(kind)
    return TypeSpec.of(*members)


@dataclass(frozen=True, slots=True)
class FlowDiagnostic:
    code: str
    message: str


@dataclass(slots=True)
class FlowTypeEnvironment:
    """Akışa duyarlı opsiyonel tip daraltma ortamı.

    Bu sınıf AST veya Python scope modelini kopyalamaz. Şahin'in `yok`
    predicate'inin iki dalda ürettiği tip durumunu bağımsız biçimde taşır.
    """

    values: dict[str, TypeSpec] = field(default_factory=dict)

    def bind(self, name: str, spec: TypeSpec) -> None:
        self.values[name] = spec

    def resolve(self, name: str) -> TypeSpec:
        return self.values.get(name, TypeSpec.of(TypeKind.BILINMEYEN))

    def branch_for_yok(self, name: str) -> tuple["FlowTypeEnvironment", "FlowTypeEnvironment"]:
        current = self.resolve(name)
        yes = FlowTypeEnvironment(dict(self.values))
        no = FlowTypeEnvironment(dict(self.values))

        if current.can_be_yok:
            yes.values[name] = TypeSpec.of(TypeKind.YOK)
            no.values[name] = current.narrowed_present()
        return yes, no

    def member_access_diagnostic(self, name: str) -> FlowDiagnostic | None:
        spec = self.resolve(name)
        if not spec.can_be_yok:
            return None
        return FlowDiagnostic(
            "SHN-T302",
            f"{name!r} değeri {spec.display()} olabilir; alan erişiminden önce 'yok' durumu daraltılmalıdır.",
        )

    def assign(self, name: str, actual: TypeSpec) -> FlowDiagnostic | None:
        expected = self.resolve(name)
        if expected.is_unknown:
            self.values[name] = actual
            return None
        if expected.accepts(actual):
            self.values[name] = actual.joined(expected) if expected.is_optional else expected
            return None
        return FlowDiagnostic(
            "SHN-T203",
            f"{name!r} {expected.display()} olarak belirlendi; {actual.display()} değer atanamaz.",
        )
