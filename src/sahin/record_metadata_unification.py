from __future__ import annotations

from .field_declaration_abi import FieldMetadata
from .record_declaration_abi import RecordMetadata
from .record_ir_metadata import IRRecordMetadata, lower_record_metadata
from .record_metadata import RecordSchemaABI


class RecordMetadataUnificationError(ValueError):
    """Legacy ve IR record metadata sözleşmeleri güvenle birleştirilemediğinde oluşur."""


_ALLOWED_MODIFIERS = frozenset({"gerekli", "benzersiz", "otomatik"})


def legacy_schema_to_ir_metadata(schema: RecordSchemaABI) -> IRRecordMetadata:
    """Mevcut adapter RecordSchemaABI'sini kanonik IRRecordMetadata'ya dönüştürür.

    Bu köprü yalnız metadata taşır; executable opcode, persistence, import veya
    capability yüzeyi açmaz. Bilinmeyen/yinelenen modifier ve bozuk şema
    fail-closed reddedilir.
    """
    if not schema.name:
        raise RecordMetadataUnificationError("Kayıt adı boş olamaz.")
    if not schema.fields:
        raise RecordMetadataUnificationError(f"{schema.name!r} kaydı en az bir alan içermelidir.")

    seen_fields: set[str] = set()
    fields: list[FieldMetadata] = []
    for field in schema.fields:
        if not field.name or not field.type_name:
            raise RecordMetadataUnificationError(
                f"{schema.name!r} kaydında alan adı ve tipi boş olamaz."
            )
        if field.name in seen_fields:
            raise RecordMetadataUnificationError(
                f"{schema.name!r} kaydında yinelenen alan reddedildi: {field.name!r}."
            )
        seen_fields.add(field.name)

        modifiers = tuple(field.modifiers)
        if len(modifiers) != len(set(modifiers)):
            raise RecordMetadataUnificationError(
                f"{schema.name!r}.{field.name} alanında yinelenen modifier reddedildi."
            )
        unknown = tuple(item for item in modifiers if item not in _ALLOWED_MODIFIERS)
        if unknown:
            raise RecordMetadataUnificationError(
                f"{schema.name!r}.{field.name} alanında bilinmeyen modifier reddedildi: {', '.join(unknown)}."
            )

        fields.append(
            FieldMetadata(
                name=field.name,
                type_name=field.type_name,
                required="gerekli" in modifiers,
                unique="benzersiz" in modifiers,
                automatic="otomatik" in modifiers,
            )
        )

    return lower_record_metadata(RecordMetadata(name=schema.name, fields=tuple(fields)))


def assert_record_metadata_equivalent(schema: RecordSchemaABI, metadata: IRRecordMetadata) -> None:
    """İki metadata temsilinin aynı gözlemlenebilir alan sözleşmesini taşıdığını doğrular."""
    converted = legacy_schema_to_ir_metadata(schema)
    if converted != metadata:
        raise RecordMetadataUnificationError(
            f"Record metadata ABI ayrışması tespit edildi: {schema.name!r}."
        )
