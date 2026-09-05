from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Declaration, FieldDeclaration
from .field_declaration_abi import FieldMetadata, analyze_field_declaration


class RecordDeclarationABIError(ValueError):
    """A `kayıt` declaration cannot be represented safely in the Stage 10 metadata ABI."""


@dataclass(frozen=True, slots=True)
class RecordMetadata:
    name: str
    fields: tuple[FieldMetadata, ...]


def analyze_record_declaration(declaration: Declaration) -> RecordMetadata:
    """Normalize a parsed `kayıt` declaration into deterministic field metadata.

    Stage 10 keeps this boundary metadata-only: no executable record runtime,
    persistence capability, backend import, or storage semantics are implied.
    """

    if declaration.kind != "kayıt":
        raise RecordDeclarationABIError(
            f"Record metadata ABI yalnız `kayıt` Declaration kabul eder; alındı: {declaration.kind!r}."
        )
    if not declaration.name:
        raise RecordDeclarationABIError("`kayıt` declaration adı boş olamaz.")
    if declaration.parameters or declaration.header or declaration.return_type is not None:
        raise RecordDeclarationABIError("`kayıt` declaration beklenmeyen header/parametre/dönüş metadata'sı içeriyor.")
    if declaration.inline_expression is not None:
        raise RecordDeclarationABIError("`kayıt` declaration inline expression içeremez.")

    fields: list[FieldMetadata] = []
    seen_names: set[str] = set()
    for statement in declaration.body:
        if not isinstance(statement, FieldDeclaration):
            raise RecordDeclarationABIError(
                "`kayıt` gövdesi Stage 10 metadata ABI'ında yalnız FieldDeclaration içerebilir."
            )
        if statement.name in seen_names:
            raise RecordDeclarationABIError(
                f"`kayıt` içinde yinelenen alan adı: {statement.name!r}."
            )
        seen_names.add(statement.name)
        fields.append(analyze_field_declaration(statement))

    if not fields:
        raise RecordDeclarationABIError("`kayıt` en az bir alan içermelidir.")

    return RecordMetadata(name=declaration.name, fields=tuple(fields))
