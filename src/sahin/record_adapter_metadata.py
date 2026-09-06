from __future__ import annotations

from dataclasses import dataclass

from .record_backend_validation import RecordBackendValidationError, validate_record_metadata_for_backend
from .record_ir_metadata import IRRecordMetadata
from .record_metadata import RecordSchemaABI
from .record_metadata_unification import (
    RecordMetadataUnificationError,
    assert_record_metadata_equivalent,
    legacy_schema_to_ir_metadata,
)


class RecordAdapterMetadataError(ValueError):
    """Record metadata adapter sınırında kanonik ABI ile doğrulanamadığında oluşur."""


@dataclass(frozen=True, slots=True)
class ValidatedAdapterRecordMetadata:
    """Kanonik IR metadata ile mevcut wire şemasını birlikte ve kayıpsız taşır.

    `IRRecordMetadata` semantik/backend doğrulama düzlemidir. `wire_schema` ise
    mevcut dış adapter sözleşmesinin byte-compatible temsilidir. Representation
    migration tamamlanana kadar iki görünüm de aynı doğrulanmış kaynaktan gelir.
    """

    metadata: IRRecordMetadata
    wire_schema: RecordSchemaABI

    def canonical_wire(self) -> str:
        return self.wire_schema.canonical()


def build_validated_adapter_record_metadata(
    schemas: tuple[RecordSchemaABI, ...],
) -> tuple[ValidatedAdapterRecordMetadata, ...]:
    """Legacy wire şemalarını kanonik IR metadata ile doğrulayıp kayıpsız taşıyıcıya çevir."""
    validated: list[ValidatedAdapterRecordMetadata] = []
    try:
        for schema in schemas:
            metadata = legacy_schema_to_ir_metadata(schema)
            validate_record_metadata_for_backend(metadata)
            assert_record_metadata_equivalent(schema, metadata)
            validated.append(ValidatedAdapterRecordMetadata(metadata=metadata, wire_schema=schema))
    except (RecordMetadataUnificationError, RecordBackendValidationError) as exc:
        raise RecordAdapterMetadataError(str(exc)) from exc
    return tuple(validated)


def validate_adapter_record_schemas(
    schemas: tuple[RecordSchemaABI, ...],
) -> tuple[RecordSchemaABI, ...]:
    """Legacy wire sözleşmesini korurken her şemayı kanonik IR metadata ile doğrula.

    Bu köprü executable opcode, persistence, import veya capability açmaz. Adapter
    dış sözleşmesi şimdilik RecordSchemaABI olarak kalır; ancak tüketimden önce aynı
    metadata IRRecordMetadata'ya dönüştürülür, backend validation kapısından geçer
    ve iki temsilin semantik olarak eşdeğer olduğu doğrulanır.
    """
    return tuple(
        item.wire_schema
        for item in build_validated_adapter_record_metadata(schemas)
    )
