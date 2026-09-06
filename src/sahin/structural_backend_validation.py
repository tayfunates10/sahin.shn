from __future__ import annotations

from .structural_declaration_abi import (
    STRUCTURAL_DECLARATION_KINDS,
    StructuralDeclarationMetadata,
)


class StructuralBackendValidationError(ValueError):
    """Structural declaration metadata cannot cross the backend boundary safely."""


def validate_structural_metadata_for_backend(
    declarations: tuple[StructuralDeclarationMetadata, ...],
) -> tuple[StructuralDeclarationMetadata, ...]:
    """Validate structural metadata without inventing executable/backend semantics.

    The validator is intentionally shape-only and fail-closed. It preserves source
    order and exact metadata values, but rejects malformed or ambiguous entries
    before an adapter can consume them.
    """

    validated: list[StructuralDeclarationMetadata] = []
    for index, item in enumerate(declarations):
        if not isinstance(item, StructuralDeclarationMetadata):
            raise StructuralBackendValidationError(
                f"Yapısal metadata[{index}] beklenmeyen tür içeriyor."
            )
        if item.kind not in STRUCTURAL_DECLARATION_KINDS:
            raise StructuralBackendValidationError(
                f"Desteklenmeyen yapısal metadata türü: {item.kind!r}."
            )
        if item.header_arity < 0 or item.body_arity < 0:
            raise StructuralBackendValidationError(
                f"{item.kind!r} metadata arity değerleri negatif olamaz."
            )
        if item.kind in {"uygulama", "ekran", "görünüm", "uç", "iş"} and not item.name:
            raise StructuralBackendValidationError(
                f"{item.kind!r} backend metadata adı boş olamaz."
            )
        if item.kind in {"uygulama", "ekran", "görünüm"} and item.header_arity != 0:
            raise StructuralBackendValidationError(
                f"{item.kind!r} backend metadata header kabul etmiyor."
            )
        if item.kind == "olay" and (not item.name or item.header_arity < 1):
            raise StructuralBackendValidationError(
                "'olay' backend metadata adı ve en az bir header öğesi gerektirir."
            )
        validated.append(item)

    return tuple(validated)
