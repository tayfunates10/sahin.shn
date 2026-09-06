from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Declaration, Program
from .ir import IRLoweringError, IRProgram, lower_program
from .lexer import tokenize
from .parser import parse
from .record_metadata import RecordMetadataError, RecordSchemaABI, extract_record_schemas
from .semantics import SemanticAnalyzer
from .structural_declaration_abi import (
    STRUCTURAL_DECLARATION_KINDS,
    StructuralDeclarationABIError,
    StructuralDeclarationMetadata,
    extract_structural_declaration_metadata,
)


@dataclass(frozen=True, slots=True)
class AdapterSourceIRBundle:
    """Executable IR plus all non-executable metadata required by Stage 10 adapters."""

    program: IRProgram
    record_schemas: tuple[RecordSchemaABI, ...] = ()
    structural_declarations: tuple[StructuralDeclarationMetadata, ...] = ()


def lower_source_with_adapter_metadata(source: str) -> AdapterSourceIRBundle:
    """Validate source once, then split executable IR from metadata-only declarations.

    `kayıt` and the structural declaration family remain non-executable. They are
    removed from the executable program only after their existing fail-closed ABI
    validators accept them. This opens no opcode, import, capability or engine
    semantics; it only gives backend adapters one canonical frontend boundary.
    """

    parsed = parse(tokenize(source))
    model = SemanticAnalyzer().analyze(parsed)
    if not model.ok:
        details = "; ".join(item.format() for item in model.diagnostics)
        raise IRLoweringError(f"Semantik doğrulama başarısız: {details}")

    try:
        record_schemas = extract_record_schemas(parsed)
        structural_declarations = extract_structural_declaration_metadata(parsed)
    except (RecordMetadataError, StructuralDeclarationABIError) as exc:
        raise IRLoweringError(f"Adapter metadata doğrulaması başarısız: {exc}") from exc

    executable = Program(
        tuple(
            statement
            for statement in parsed.statements
            if not (
                isinstance(statement, Declaration)
                and (
                    statement.kind == "kayıt"
                    or statement.kind in STRUCTURAL_DECLARATION_KINDS
                )
            )
        )
    )
    return AdapterSourceIRBundle(
        program=lower_program(executable),
        record_schemas=record_schemas,
        structural_declarations=structural_declarations,
    )
