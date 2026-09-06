from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Declaration


class StructuralDeclarationABIError(ValueError):
    """Structural Declaration metadata cannot be represented safely in Stage 10."""


STRUCTURAL_DECLARATION_KINDS = frozenset({"uygulama", "ekran", "görünüm", "uç", "iş", "olay"})
_NAMED_NO_HEADER_KINDS = frozenset({"uygulama", "ekran", "görünüm"})
_NAMED_LOOSE_HEADER_KINDS = frozenset({"uç", "iş"})


@dataclass(frozen=True, slots=True)
class StructuralDeclarationMetadata:
    kind: str
    name: str | None
    header_arity: int
    body_arity: int


def analyze_structural_declaration(declaration: Declaration) -> StructuralDeclarationMetadata:
    """Validate only the observable structural shape of a non-executable declaration.

    This ABI deliberately does not execute declaration bodies, serialize header
    expressions, invent runtime opcodes, or widen capability/import surfaces.
    Motor-specific semantics remain fail-closed for later Stage 10 slices.
    """

    if declaration.kind not in STRUCTURAL_DECLARATION_KINDS:
        raise StructuralDeclarationABIError(
            f"Desteklenmeyen yapısal Declaration türü: {declaration.kind!r}."
        )
    if declaration.parameters:
        raise StructuralDeclarationABIError(
            f"{declaration.kind!r} yapısal ABI parametre kabul etmiyor."
        )
    if declaration.return_type is not None:
        raise StructuralDeclarationABIError(
            f"{declaration.kind!r} yapısal ABI dönüş tipi kabul etmiyor."
        )
    if declaration.inline_expression is not None:
        raise StructuralDeclarationABIError(
            f"{declaration.kind!r} yapısal ABI inline expression kabul etmiyor."
        )

    if declaration.kind in _NAMED_NO_HEADER_KINDS:
        if not declaration.name:
            raise StructuralDeclarationABIError(
                f"{declaration.kind!r} declaration adı boş olamaz."
            )
        if declaration.header:
            raise StructuralDeclarationABIError(
                f"{declaration.kind!r} declaration header kabul etmiyor."
            )

    if declaration.kind in _NAMED_LOOSE_HEADER_KINDS and not declaration.name:
        raise StructuralDeclarationABIError(
            f"{declaration.kind!r} declaration adı boş olamaz."
        )

    if declaration.kind == "olay":
        if not declaration.header or not declaration.name:
            raise StructuralDeclarationABIError(
                "'olay' declaration en az bir header ifadesi ve türetilmiş bir ad gerektirir."
            )

    return StructuralDeclarationMetadata(
        kind=declaration.kind,
        name=declaration.name,
        header_arity=len(declaration.header),
        body_arity=len(declaration.body),
    )
