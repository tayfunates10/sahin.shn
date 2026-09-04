import pytest

from sahin.ast_nodes import Declaration, FieldDeclaration, Literal, Program, Write
from sahin.record_metadata import RecordMetadataError, extract_record_schemas, extract_record_schemas_from_source


def test_record_field_metadata_from_real_source_is_deterministic_and_source_ordered():
    schemas = extract_record_schemas_from_source(
        '''kayıt Kullanıcı
    ad: yazı gerekli
    eposta: eposta gerekli benzersiz
    yaş: sayı
    katılım: zaman otomatik
'''
    )

    assert len(schemas) == 1
    schema = schemas[0]
    assert schema.name == "Kullanıcı"
    assert tuple(field.name for field in schema.fields) == ("ad", "eposta", "yaş", "katılım")
    assert schema.canonical() == (
        '{"fields":[{"modifiers":["gerekli"],"name":"ad","type":"yazı"},'
        '{"modifiers":["gerekli","benzersiz"],"name":"eposta","type":"eposta"},'
        '{"modifiers":[],"name":"yaş","type":"sayı"},'
        '{"modifiers":["otomatik"],"name":"katılım","type":"zaman"}],'
        '"kind":"kayıt","name":"Kullanıcı","version":1}'
    )


def test_record_metadata_rejects_duplicate_fields_fail_closed():
    program = Program(
        (
            Declaration(
                kind="kayıt",
                name="Ürün",
                body=(FieldDeclaration("ad", "yazı"), FieldDeclaration("ad", "yazı")),
            ),
        )
    )

    with pytest.raises(RecordMetadataError, match="yinelenen alan"):
        extract_record_schemas(program)


def test_record_metadata_rejects_field_outside_record_scope():
    with pytest.raises(RecordMetadataError, match="yalnız bir `kayıt` gövdesinde"):
        extract_record_schemas(Program((FieldDeclaration("ad", "yazı"),)))


def test_record_metadata_rejects_unknown_or_duplicate_modifiers():
    unknown = Program((Declaration(kind="kayıt", name="Ürün", body=(FieldDeclaration("ad", "yazı", ("gizli",)),)),))
    duplicate = Program((Declaration(kind="kayıt", name="Ürün", body=(FieldDeclaration("ad", "yazı", ("gerekli", "gerekli")),)),))

    with pytest.raises(RecordMetadataError, match="bilinmeyen modifier"):
        extract_record_schemas(unknown)
    with pytest.raises(RecordMetadataError, match="yinelenen modifier"):
        extract_record_schemas(duplicate)


def test_record_metadata_rejects_runtime_statement_inside_record():
    program = Program(
        (
            Declaration(
                kind="kayıt",
                name="Ürün",
                body=(Write(Literal("yan etki")),),
            ),
        )
    )

    with pytest.raises(RecordMetadataError, match="yalnız FieldDeclaration"):
        extract_record_schemas(program)
