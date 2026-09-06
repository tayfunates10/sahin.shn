from __future__ import annotations

from dataclasses import dataclass
import json

from .ast_nodes import Declaration, Program
from .ir import IRLoweringError, IRProgram, lower_program
from .lexer import tokenize
from .parser import parse
from .semantics import SemanticAnalyzer
from .structural_declaration_abi import (
    STRUCTURAL_DECLARATION_KINDS,
    StructuralDeclarationABIError,
    StructuralDeclarationMetadata,
    extract_structural_declaration_metadata,
)


@dataclass(frozen=True, slots=True)
class StructuralAwareIRProgram:
    """Executable IR v1 plus non-executable structural declaration metadata."""

    program: IRProgram
    declarations: tuple[StructuralDeclarationMetadata, ...] = ()

    def canonical(self) -> str:
        payload = {
            "program": json.loads(self.program.canonical()),
            "structural_declarations": [
                {
                    "body_arity": item.body_arity,
                    "header_arity": item.header_arity,
                    "kind": item.kind,
                    "name": item.name,
                }
                for item in self.declarations
            ],
            "version": 1,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def lower_source_with_structural_metadata(source: str) -> StructuralAwareIRProgram:
    """Validate source once and carry structural declarations as metadata only.

    Structural declarations remain non-executable in this Stage 10 slice. They are
    removed from the executable program only after the same fail-closed structural
    ABI validator has accepted them. No opcode, import or capability surface is
    widened here.
    """

    parsed = parse(tokenize(source))
    model = SemanticAnalyzer().analyze(parsed)
    if not model.ok:
        details = "; ".join(item.format() for item in model.diagnostics)
        raise IRLoweringError(f"Semantik doğrulama başarısız: {details}")

    try:
        metadata = extract_structural_declaration_metadata(parsed)
    except StructuralDeclarationABIError as exc:
        raise IRLoweringError(f"Yapısal Declaration metadata doğrulaması başarısız: {exc}") from exc

    executable = Program(
        tuple(
            statement
            for statement in parsed.statements
            if not (
                isinstance(statement, Declaration)
                and statement.kind in STRUCTURAL_DECLARATION_KINDS
            )
        )
    )
    return StructuralAwareIRProgram(lower_program(executable), metadata)
