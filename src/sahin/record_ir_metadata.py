from __future__ import annotations

from dataclasses import dataclass
import json

from .field_declaration_abi import FieldMetadata
from .record_declaration_abi import RecordMetadata


class RecordIRMetadataError(ValueError):
    """Record metadata cannot be serialized safely into the Stage 10 IR metadata plane."""


@dataclass(frozen=True, slots=True)
class IRFieldMetadata:
    name: str
    type_name: str
    required: bool
    unique: bool
    automatic: bool

    @classmethod
    def from_field(cls, field: FieldMetadata) -> "IRFieldMetadata":
        if not field.name or not field.type_name:
            raise RecordIRMetadataError("IR field metadata adı ve tipi boş olamaz.")
        return cls(
            name=field.name,
            type_name=field.type_name,
            required=field.required,
            unique=field.unique,
            automatic=field.automatic,
        )

    def canonical_object(self) -> dict[str, object]:
        return {
            "automatic": self.automatic,
            "name": self.name,
            "required": self.required,
            "type": self.type_name,
            "unique": self.unique,
        }


@dataclass(frozen=True, slots=True)
class IRRecordMetadata:
    name: str
    fields: tuple[IRFieldMetadata, ...]

    def canonical(self) -> str:
        if not self.name:
            raise RecordIRMetadataError("IR record metadata adı boş olamaz.")
        if not self.fields:
            raise RecordIRMetadataError("IR record metadata en az bir alan içermelidir.")
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise RecordIRMetadataError("IR record metadata yinelenen alan içeremez.")
        payload = {
            "fields": [field.canonical_object() for field in self.fields],
            "kind": "record",
            "name": self.name,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def lower_record_metadata(metadata: RecordMetadata) -> IRRecordMetadata:
    """Carry validated `kayıt` metadata into deterministic IR-side metadata.

    This function deliberately emits no executable opcode and opens no backend
    import/capability. Runtime construction, persistence and backend lowering
    remain fail-closed until their own contracts are implemented and tested.
    """

    if not metadata.name:
        raise RecordIRMetadataError("Record metadata adı boş olamaz.")
    if not metadata.fields:
        raise RecordIRMetadataError("Record metadata en az bir alan içermelidir.")

    fields = tuple(IRFieldMetadata.from_field(field) for field in metadata.fields)
    names = [field.name for field in fields]
    if len(names) != len(set(names)):
        raise RecordIRMetadataError("Record metadata yinelenen alan içeremez.")
    return IRRecordMetadata(name=metadata.name, fields=fields)
