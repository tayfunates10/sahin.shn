import pytest

from sahin.ast_nodes import Command, Declaration, FieldDeclaration, Literal
from sahin.record_declaration_abi import (
    RecordDeclarationABIError,
    RecordMetadata,
    analyze_record_declaration,
)


def test_record_metadata_normalizes_fields_in_source_order():
    declaration = Declaration(
        kind="kayıt",
        name="Ürün",
        body=(
            FieldDeclaration("ad", "yazı", ("gerekli",)),
            FieldDeclaration("stok", "sayı"),
        ),
    )

    metadata = analyze_record_declaration(declaration)

    assert isinstance(metadata, RecordMetadata)
    assert metadata.name == "Ürün"
    assert [field.name for field in metadata.fields] == ["ad", "stok"]
    assert metadata.fields[0].required is True


def test_record_metadata_rejects_duplicate_field_names_fail_closed():
    declaration = Declaration(
        kind="kayıt",
        name="Ürün",
        body=(FieldDeclaration("ad", "yazı"), FieldDeclaration("ad", "metin")),
    )

    with pytest.raises(RecordDeclarationABIError, match="yinelenen alan adı"):
        analyze_record_declaration(declaration)


def test_record_metadata_rejects_non_field_body_statement():
    declaration = Declaration(
        kind="kayıt",
        name="Ürün",
        body=(Command("yaz", arguments=(Literal("yan etki"),)),),
    )

    with pytest.raises(RecordDeclarationABIError, match="yalnız FieldDeclaration"):
        analyze_record_declaration(declaration)


def test_record_metadata_rejects_empty_record():
    declaration = Declaration(kind="kayıt", name="Boş", body=())

    with pytest.raises(RecordDeclarationABIError, match="en az bir alan"):
        analyze_record_declaration(declaration)


def test_record_metadata_rejects_other_declaration_kinds():
    declaration = Declaration(kind="akış", name="hesapla", body=())

    with pytest.raises(RecordDeclarationABIError, match="yalnız `kayıt`"):
        analyze_record_declaration(declaration)
