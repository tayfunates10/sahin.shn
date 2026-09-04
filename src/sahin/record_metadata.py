from __future__ import annotations

from dataclasses import dataclass
import json

from .ast_nodes import Declaration, FieldDeclaration, Program
from .lexer import tokenize
from .parser import parse


class RecordMetadataError(ValueError):
    """`kayıt` alan metadata ABI'si güvenle çıkarılamadığında oluşur."""


_ALLOWED_FIELD_MODIFIERS = frozenset({"gerekli", "benzersiz", "otomatik"})


@dataclass(frozen=True, slots=True)
class RecordFieldABI:
    name: str
    type_name: str
    modifiers: tuple[str, ...] = ()

    def canonical(self) -> dict[str, object]:
        return {
            "modifiers": list(self.modifiers),
            "name": self.name,
            "type": self.type_name,
        }


@dataclass(frozen=True, slots=True)
class RecordSchemaABI:
    name: str
    fields: tuple[RecordFieldABI, ...]

    def canonical(self) -> str:
        payload = {
            "fields": [field.canonical() for field in self.fields],
            "kind": "kayıt",
            "name": self.name,
            "version": 1,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _field_abi(field: FieldDeclaration, *, record_name: str, seen: set[str]) -> RecordFieldABI:
    if not field.name or not field.type_name:
        raise RecordMetadataError(f"{record_name!r} kaydında boş alan adı/tipi reddedildi.")
    if field.name in seen:
        raise RecordMetadataError(f"{record_name!r} kaydında yinelenen alan reddedildi: {field.name!r}.")
    seen.add(field.name)

    modifiers = tuple(field.modifiers)
    if len(set(modifiers)) != len(modifiers):
        raise RecordMetadataError(f"{record_name!r}.{field.name} alanında yinelenen modifier reddedildi.")
    unknown = tuple(modifier for modifier in modifiers if modifier not in _ALLOWED_FIELD_MODIFIERS)
    if unknown:
        raise RecordMetadataError(
            f"{record_name!r}.{field.name} alanında bilinmeyen modifier reddedildi: {', '.join(unknown)}."
        )

    return RecordFieldABI(field.name, field.type_name, modifiers)


def extract_record_schemas(program: Program) -> tuple[RecordSchemaABI, ...]:
    """Top-level `kayıt` declaration'larını deterministik, capability-siz metadata ABI'sine çıkarır.

    Bu fonksiyon runtime davranışı üretmez. Yapısal veri yalnız kaynak sırasını koruyan metadata olarak
    çıkarılır; anlaşılmayan veya yanlış kapsamlı alanlar sessizce atlanmaz.
    """
    schemas: list[RecordSchemaABI] = []
    record_names: set[str] = set()

    for statement in program.statements:
        if isinstance(statement, FieldDeclaration):
            raise RecordMetadataError("FieldDeclaration yalnız bir `kayıt` gövdesinde kullanılabilir.")
        if not isinstance(statement, Declaration) or statement.kind != "kayıt":
            continue
        if not statement.name:
            raise RecordMetadataError("İsimsiz `kayıt` metadata ABI'sine dönüştürülemez.")
        if statement.name in record_names:
            raise RecordMetadataError(f"Yinelenen `kayıt` adı reddedildi: {statement.name!r}.")
        record_names.add(statement.name)

        if statement.parameters or statement.header or statement.return_type is not None or statement.inline_expression is not None:
            raise RecordMetadataError(f"{statement.name!r} kaydı desteklenmeyen declaration header biçimi içeriyor.")

        seen_fields: set[str] = set()
        fields: list[RecordFieldABI] = []
        for nested in statement.body:
            if not isinstance(nested, FieldDeclaration):
                raise RecordMetadataError(
                    f"{statement.name!r} kayıt gövdesinde yalnız FieldDeclaration kabul edilir; "
                    f"{type(nested).__name__} reddedildi."
                )
            fields.append(_field_abi(nested, record_name=statement.name, seen=seen_fields))

        schemas.append(RecordSchemaABI(statement.name, tuple(fields)))

    return tuple(schemas)


def extract_record_schemas_from_source(source: str) -> tuple[RecordSchemaABI, ...]:
    return extract_record_schemas(parse(tokenize(source)))
