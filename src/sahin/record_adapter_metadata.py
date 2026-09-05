from __future__ import annotations

from .record_backend_validation import RecordBackendValidationError, validate_record_metadata_for_backend
from .record_metadata import RecordSchemaABI
from .record_metadata_unification import (
    RecordMetadataUnificationError,
    assert_record_metadata_equivalent,
    legacy_schema_to_ir_metadata,
)


class RecordAdapterMetadataError(ValueError):
    """Record metadata adapter sınırında kanonik ABI ile doğrulanamadığında oluşur."""


def validate_adapter_record_schemas(
    schemas: tuple[RecordSchemaABI, ...],
) -> tuple[RecordSchemaABI, ...]:
    """Legacy wire sözleşmesini korurken her şemayı kanonik IR metadata ile doğrula.

    Bu köprü executable opcode, persistence, import veya capability açmaz. Adapter
    dış sözleşmesi şimdilik RecordSchemaABI olarak kalır; ancak tüketimden önce aynı
    metadata IRRecordMetadata'ya dönüştürülür, backend validation kapısından geçer
    ve iki temsilin semantik olarak eşdeğer olduğu doğrulanır.
    """
    validated: list[RecordSchemaABI] = []
    try:
        for schema in schemas:
            metadata = legacy_schema_to_ir_metadata(schema)
            validate_record_metadata_for_backend(metadata)
            assert_record_metadata_equivalent(schema, metadata)
            validated.append(schema)
    except (RecordMetadataUnificationError, RecordBackendValidationError) as exc:
        raise RecordAdapterMetadataError(str(exc)) from exc
    return tuple(validated)
