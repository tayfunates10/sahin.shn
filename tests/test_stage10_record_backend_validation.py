import pytest

from sahin.record_backend_validation import (
    RecordBackendValidationError,
    validate_record_metadata_for_backend,
)
from sahin.record_ir_metadata import IRFieldMetadata, IRRecordMetadata


def test_record_backend_validation_preserves_metadata_order_and_flags() -> None:
    metadata = IRRecordMetadata(
        name="Ürün",
        fields=(
            IRFieldMetadata("id", "sayı", True, True, True),
            IRFieldMetadata("ad", "yazı", True, False, False),
        ),
    )

    validated = validate_record_metadata_for_backend(metadata)

    assert validated.name == "Ürün"
    assert [field.name for field in validated.fields] == ["id", "ad"]
    assert validated.fields[0].automatic is True
    assert validated.fields[1].unique is False


@pytest.mark.parametrize(
    "metadata, message",
    [
        (IRRecordMetadata("", (IRFieldMetadata("ad", "yazı", False, False, False),)), "adı boş"),
        (IRRecordMetadata("Boş", ()), "en az bir alan"),
        (
            IRRecordMetadata(
                "Yinelenen",
                (
                    IRFieldMetadata("ad", "yazı", False, False, False),
                    IRFieldMetadata("ad", "sayı", False, False, False),
                ),
            ),
            "yinelenen alan",
        ),
        (
            IRRecordMetadata("Tip", (IRFieldMetadata("ad", "", False, False, False),)),
            "alan tipi boş",
        ),
    ],
)
def test_record_backend_validation_rejects_malformed_metadata(
    metadata: IRRecordMetadata, message: str
) -> None:
    with pytest.raises(RecordBackendValidationError, match=message):
        validate_record_metadata_for_backend(metadata)


def test_record_backend_validation_rejects_non_boolean_modifier_flags() -> None:
    malformed = IRFieldMetadata("id", "sayı", 1, False, False)  # type: ignore[arg-type]
    metadata = IRRecordMetadata("Ürün", (malformed,))

    with pytest.raises(RecordBackendValidationError, match="bayrağı bool"):
        validate_record_metadata_for_backend(metadata)


def test_record_backend_validation_opens_no_executable_or_capability_surface() -> None:
    metadata = IRRecordMetadata(
        "Ürün", (IRFieldMetadata("ad", "yazı", False, False, False),)
    )

    validated = validate_record_metadata_for_backend(metadata)

    assert not hasattr(validated, "instructions")
    assert not hasattr(validated, "opcode")
    assert not hasattr(validated, "capability")
    assert not hasattr(validated, "imports")
