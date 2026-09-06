from __future__ import annotations

import pytest

from sahin.structural_backend_validation import (
    StructuralBackendValidationError,
    validate_structural_metadata_for_backend,
)
from sahin.structural_declaration_abi import StructuralDeclarationMetadata
from sahin.structural_ir import lower_source_with_structural_metadata


def test_accepts_frontend_structural_metadata_in_source_order() -> None:
    bundle = lower_source_with_structural_metadata(
        """
uygulama Ana
    yaz \"merhaba\"

görünüm Ozet
    yaz \"tamam\"
"""
    )
    validated = validate_structural_metadata_for_backend(bundle.declarations)
    assert validated == bundle.declarations
    assert [(item.kind, item.name) for item in validated] == [
        ("uygulama", "Ana"),
        ("görünüm", "Ozet"),
    ]


def test_rejects_unknown_kind() -> None:
    item = StructuralDeclarationMetadata("unknown", "X", 0, 0)
    with pytest.raises(StructuralBackendValidationError):
        validate_structural_metadata_for_backend((item,))


def test_rejects_missing_name_for_named_kind() -> None:
    item = StructuralDeclarationMetadata("uygulama", None, 0, 0)
    with pytest.raises(StructuralBackendValidationError):
        validate_structural_metadata_for_backend((item,))


def test_rejects_header_for_no_header_kind() -> None:
    item = StructuralDeclarationMetadata("uygulama", "Ana", 1, 0)
    with pytest.raises(StructuralBackendValidationError):
        validate_structural_metadata_for_backend((item,))


def test_rejects_negative_arity() -> None:
    item = StructuralDeclarationMetadata("ekran", "Ana", 0, -1)
    with pytest.raises(StructuralBackendValidationError):
        validate_structural_metadata_for_backend((item,))
