from __future__ import annotations

from dataclasses import dataclass

from .record_ir_metadata import IRFieldMetadata, IRRecordMetadata


class RecordBackendValidationError(ValueError):
    """Record metadata is malformed at the Stage 10 backend boundary."""


@dataclass(frozen=True, slots=True)
class ValidatedRecordMetadata:
    """Capability-free evidence accepted by backend adapters.

    This carrier deliberately contains metadata only. It does not authorize
    persistence, allocation, imports, or executable record operations.
    """

    name: str
    fields: tuple[IRFieldMetadata, ...]


def validate_record_metadata_for_backend(metadata: IRRecordMetadata) -> ValidatedRecordMetadata:
    """Validate IR-side `kayıt` metadata before any backend may consume it.

    The boundary is intentionally fail-closed: malformed names, field types,
    flags, and duplicate fields are rejected instead of being normalized or
    silently repaired by a backend.
    """

    if not isinstance(metadata, IRRecordMetadata):
        raise RecordBackendValidationError("Backend record metadata IRRecordMetadata olmalıdır.")
    if not isinstance(metadata.name, str) or not metadata.name:
        raise RecordBackendValidationError("Backend record metadata adı boş olamaz.")
    if not isinstance(metadata.fields, tuple) or not metadata.fields:
        raise RecordBackendValidationError("Backend record metadata en az bir alan içermelidir.")

    seen_names: set[str] = set()
    validated_fields: list[IRFieldMetadata] = []
    for field in metadata.fields:
        if not isinstance(field, IRFieldMetadata):
            raise RecordBackendValidationError("Backend record alanı IRFieldMetadata olmalıdır.")
        if not isinstance(field.name, str) or not field.name:
            raise RecordBackendValidationError("Backend record alan adı boş olamaz.")
        if field.name in seen_names:
            raise RecordBackendValidationError(
                f"Backend record metadata yinelenen alan içeremez: {field.name!r}."
            )
        seen_names.add(field.name)
        if not isinstance(field.type_name, str) or not field.type_name:
            raise RecordBackendValidationError(
                f"Backend record alan tipi boş olamaz: {field.name!r}."
            )
        for flag_name, flag_value in (
            ("required", field.required),
            ("unique", field.unique),
            ("automatic", field.automatic),
        ):
            if type(flag_value) is not bool:
                raise RecordBackendValidationError(
                    f"Backend record alan bayrağı bool olmalıdır: {field.name!r}.{flag_name}."
                )
        validated_fields.append(field)

    return ValidatedRecordMetadata(name=metadata.name, fields=tuple(validated_fields))
