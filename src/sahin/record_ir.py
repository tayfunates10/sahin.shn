from __future__ import annotations

from dataclasses import dataclass
import json

from .ast_nodes import Declaration, Program
from .ir import IRLoweringError, IRProgram, lower_program
from .lexer import tokenize
from .parser import parse
from .record_metadata import RecordMetadataError, RecordSchemaABI, extract_record_schemas
from .semantics import SemanticAnalyzer


@dataclass(frozen=True, slots=True)
class RecordAwareIRProgram:
    """Yürütülebilir IR v1 ile yapısal `kayıt` metadata ABI'sini birlikte taşır.

    `kayıt` tanımları runtime instruction üretmez; metadata ayrı ve capability-siz bir
    kanalda korunur. Böylece mevcut IR v1 instruction canonical sözleşmesi değişmez.
    """

    program: IRProgram
    record_schemas: tuple[RecordSchemaABI, ...] = ()

    def canonical(self) -> str:
        payload = {
            "program": json.loads(self.program.canonical()),
            "record_schemas": [json.loads(schema.canonical()) for schema in self.record_schemas],
            "version": 1,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def lower_source_with_record_metadata(source: str) -> RecordAwareIRProgram:
    """Kaynağı tek frontend doğrulamasından geçirip executable IR + kayıt metadata üretir.

    Aşama 10'un bu diliminde `kayıt` declaration'ı yürütülebilir opcode'a dönüşmez.
    Alan şeması doğrulanır ve metadata ABI olarak taşınır; kalan statement'lar mevcut
    IR v1 hattına gider. Kayıt dışındaki desteklenmeyen declaration/command sınırları
    aynen fail-closed kalır.
    """

    parsed = parse(tokenize(source))
    model = SemanticAnalyzer().analyze(parsed)
    if not model.ok:
        details = "; ".join(item.format() for item in model.diagnostics)
        raise IRLoweringError(f"Semantik doğrulama başarısız: {details}")

    try:
        schemas = extract_record_schemas(parsed)
    except RecordMetadataError as exc:
        raise IRLoweringError(f"Kayıt metadata doğrulaması başarısız: {exc}") from exc

    executable = Program(
        tuple(
            statement
            for statement in parsed.statements
            if not (isinstance(statement, Declaration) and statement.kind == "kayıt")
        )
    )
    return RecordAwareIRProgram(lower_program(executable), schemas)
