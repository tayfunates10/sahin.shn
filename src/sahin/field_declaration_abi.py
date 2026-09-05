from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import FieldDeclaration


class FieldDeclarationABIError(ValueError):
    """FieldDeclaration metadata cannot be represented safely in Stage 10 IR ABI."""


_ALLOWED_MODIFIERS = frozenset({"gerekli", "benzersiz", "otomatik"})


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    name: str
    type_name: str
    required: bool = False
    unique: bool = False
    automatic: bool = False


def analyze_field_declaration(field: FieldDeclaration) -> FieldMetadata:
    """Normalize a parsed field declaration into a fail-closed metadata contract.

    This is intentionally metadata-only. It does not make record declarations
    executable and it does not widen backend capability/import surfaces.
    """

    if not field.name:
        raise FieldDeclarationABIError("Alan adı boş olamaz.")
    if not field.type_name:
        raise FieldDeclarationABIError(f"{field.name!r} alanı için tip adı boş olamaz.")

    seen: set[str] = set()
    for modifier in field.modifiers:
        if modifier not in _ALLOWED_MODIFIERS:
            raise FieldDeclarationABIError(
                f"{field.name!r} alanında desteklenmeyen modifier: {modifier!r}."
            )
        if modifier in seen:
            raise FieldDeclarationABIError(
                f"{field.name!r} alanında yinelenen modifier: {modifier!r}."
            )
        seen.add(modifier)

    return FieldMetadata(
        name=field.name,
        type_name=field.type_name,
        required="gerekli" in seen,
        unique="benzersiz" in seen,
        automatic="otomatik" in seen,
    )
