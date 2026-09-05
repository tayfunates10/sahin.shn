import json

import pytest

from sahin.field_declaration_abi import FieldMetadata
from sahin.record_declaration_abi import RecordMetadata
from sahin.record_ir_metadata import RecordIRMetadataError, lower_record_metadata


def test_record_metadata_lowering_preserves_field_order_and_flags() -> None:
    metadata = RecordMetadata(
        name="Ürün",
        fields=(
            FieldMetadata(name="id", type_name="sayı", required=True, unique=True, automatic=True),
            FieldMetadata(name="ad", type_name="yazı", required=True),
        ),
    )

    lowered = lower_record_metadata(metadata)
    payload = json.loads(lowered.canonical())

    assert payload == {
        "fields": [
            {"automatic": True, "name": "id", "required": True, "type": "sayı", "unique": True},
            {"automatic": False, "name": "ad", "required": True, "type": "yazı", "unique": False},
        ],
        "kind": "record",
        "name": "Ürün",
    }


def test_record_metadata_canonical_is_deterministic() -> None:
    metadata = RecordMetadata(
        name="Kişi",
        fields=(FieldMetadata(name="ad", type_name="yazı"),),
    )

    lowered = lower_record_metadata(metadata)
    assert lowered.canonical() == lowered.canonical()
    assert lowered.canonical() == (
        '{"fields":[{"automatic":false,"name":"ad","required":false,'
        '"type":"yazı","unique":false}],"kind":"record","name":"Kişi"}'
    )


@pytest.mark.parametrize(
    "metadata, message",
    [
        (RecordMetadata(name="", fields=(FieldMetadata(name="ad", type_name="yazı"),)), "adı boş"),
        (RecordMetadata(name="Boş", fields=()), "en az bir alan"),
        (
            RecordMetadata(
                name="Yinelenen",
                fields=(
                    FieldMetadata(name="ad", type_name="yazı"),
                    FieldMetadata(name="ad", type_name="sayı"),
                ),
            ),
            "yinelenen alan",
        ),
    ],
)
def test_record_metadata_lowering_fails_closed(metadata: RecordMetadata, message: str) -> None:
    with pytest.raises(RecordIRMetadataError, match=message):
        lower_record_metadata(metadata)


def test_record_metadata_carrier_emits_no_executable_opcode_or_capability() -> None:
    metadata = RecordMetadata(
        name="Ürün",
        fields=(FieldMetadata(name="ad", type_name="yazı"),),
    )

    payload = json.loads(lower_record_metadata(metadata).canonical())

    assert "opcode" not in payload
    assert "instructions" not in payload
    assert "capability" not in payload
    assert "import" not in payload
