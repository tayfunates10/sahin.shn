import pytest

from sahin.record_ir_metadata import IRFieldMetadata, IRRecordMetadata
from sahin.record_metadata import RecordFieldABI, RecordSchemaABI
from sahin.record_metadata_unification import (
    RecordMetadataUnificationError,
    assert_record_metadata_equivalent,
    legacy_schema_to_ir_metadata,
)


def test_legacy_schema_maps_to_ir_metadata_without_semantic_loss():
    schema = RecordSchemaABI(
        "Kullanıcı",
        (
            RecordFieldABI("ad", "yazı", ("gerekli",)),
            RecordFieldABI("eposta", "eposta", ("gerekli", "benzersiz")),
            RecordFieldABI("katılım", "zaman", ("otomatik",)),
        ),
    )

    metadata = legacy_schema_to_ir_metadata(schema)

    assert metadata == IRRecordMetadata(
        "Kullanıcı",
        (
            IRFieldMetadata("ad", "yazı", True, False, False),
            IRFieldMetadata("eposta", "eposta", True, True, False),
            IRFieldMetadata("katılım", "zaman", False, False, True),
        ),
    )
    assert_record_metadata_equivalent(schema, metadata)


def test_unification_rejects_unknown_or_duplicate_modifiers_fail_closed():
    with pytest.raises(RecordMetadataUnificationError, match="bilinmeyen modifier"):
        legacy_schema_to_ir_metadata(
            RecordSchemaABI("K", (RecordFieldABI("ad", "yazı", ("gizli",)),))
        )

    with pytest.raises(RecordMetadataUnificationError, match="yinelenen modifier"):
        legacy_schema_to_ir_metadata(
            RecordSchemaABI("K", (RecordFieldABI("ad", "yazı", ("gerekli", "gerekli")),))
        )


def test_unification_detects_parallel_abi_drift():
    schema = RecordSchemaABI("K", (RecordFieldABI("ad", "yazı", ("gerekli",)),))
    drifted = IRRecordMetadata(
        "K",
        (IRFieldMetadata("ad", "yazı", False, False, False),),
    )

    with pytest.raises(RecordMetadataUnificationError, match="ABI ayrışması"):
        assert_record_metadata_equivalent(schema, drifted)


def test_unification_rejects_empty_and_duplicate_fields():
    with pytest.raises(RecordMetadataUnificationError, match="en az bir alan"):
        legacy_schema_to_ir_metadata(RecordSchemaABI("K", ()))

    with pytest.raises(RecordMetadataUnificationError, match="yinelenen alan"):
        legacy_schema_to_ir_metadata(
            RecordSchemaABI(
                "K",
                (
                    RecordFieldABI("ad", "yazı"),
                    RecordFieldABI("ad", "sayı"),
                ),
            )
        )
