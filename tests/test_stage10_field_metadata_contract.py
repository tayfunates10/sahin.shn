import pytest

from sahin.ast_nodes import FieldDeclaration
from sahin.field_declaration_abi import (
    FieldDeclarationABIError,
    FieldMetadata,
    analyze_field_declaration,
)


def test_field_metadata_normalizes_supported_modifiers():
    field = FieldDeclaration("eposta", "eposta", ("gerekli", "benzersiz"))

    assert analyze_field_declaration(field) == FieldMetadata(
        name="eposta",
        type_name="eposta",
        required=True,
        unique=True,
        automatic=False,
    )


def test_field_metadata_preserves_automatic_modifier():
    field = FieldDeclaration("katılım", "zaman", ("otomatik",))

    assert analyze_field_declaration(field).automatic is True


def test_field_metadata_rejects_unknown_modifier_fail_closed():
    field = FieldDeclaration("ad", "yazı", ("gerekli", "sessizce-yoksay"))

    with pytest.raises(FieldDeclarationABIError, match="desteklenmeyen modifier"):
        analyze_field_declaration(field)


def test_field_metadata_rejects_duplicate_modifier():
    field = FieldDeclaration("ad", "yazı", ("gerekli", "gerekli"))

    with pytest.raises(FieldDeclarationABIError, match="yinelenen modifier"):
        analyze_field_declaration(field)
