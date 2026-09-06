from __future__ import annotations

import json

import pytest

from sahin.record_adapter_metadata import (
    RecordAdapterMetadataError,
    build_validated_adapter_record_metadata,
)
from sahin.record_metadata import RecordFieldABI, RecordSchemaABI


def test_lossless_carrier_preserves_existing_wire_bytes_and_canonical_ir_semantics() -> None:
    schema = RecordSchemaABI(
        "Ürün",
        (
            # Modifier sırası mevcut adapter wire sözleşmesinin parçasıdır; migration bunu kaybetmemeli.
            RecordFieldABI("stok", "sayı", ("benzersiz", "gerekli")),
            RecordFieldABI("id", "sayı", ("otomatik",)),
        ),
    )

    (carried,) = build_validated_adapter_record_metadata((schema,))

    assert carried.wire_schema is schema
    assert carried.canonical_wire() == schema.canonical()
    assert json.loads(carried.canonical_wire())["fields"][0]["modifiers"] == ["benzersiz", "gerekli"]
    assert carried.metadata.name == "Ürün"
    assert carried.metadata.fields[0].required is True
    assert carried.metadata.fields[0].unique is True
    assert carried.metadata.fields[0].automatic is False


def test_lossless_carrier_rejects_unknown_modifier_before_adapter_consumption() -> None:
    schema = RecordSchemaABI(
        "Ürün",
        (RecordFieldABI("stok", "sayı", ("gerekli", "gizli")),),
    )

    with pytest.raises(RecordAdapterMetadataError, match="bilinmeyen modifier"):
        build_validated_adapter_record_metadata((schema,))


def test_lossless_carrier_rejects_duplicate_field_before_adapter_consumption() -> None:
    schema = RecordSchemaABI(
        "Ürün",
        (
            RecordFieldABI("stok", "sayı", ()),
            RecordFieldABI("stok", "sayı", ()),
        ),
    )

    with pytest.raises(RecordAdapterMetadataError, match="yinelenen alan"):
        build_validated_adapter_record_metadata((schema,))
