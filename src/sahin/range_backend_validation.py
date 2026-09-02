from __future__ import annotations

from .backend_validation import validate_backend_program
from .ir import IRFlow, IRInstruction, IRProgram


def _rewrite_sequence(
    instructions: tuple[IRInstruction, ...],
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> tuple[IRInstruction, ...]:
    rewritten: list[IRInstruction] = []
    for index, instruction in enumerate(instructions):
        if instruction.opcode != "range":
            rewritten.append(instruction)
            continue

        if len(instruction.operands) != 2 or instruction.result is None:
            raise error_type(
                f"{backend_name} adapter geçersiz range instruction şemasını reddetti "
                f"(instruction {index}): range tam olarak 2 geçici operand almalı ve sonuç üretmelidir"
            )
        start, end = instruction.operands
        if not start.startswith("%") or not end.startswith("%"):
            raise error_type(
                f"{backend_name} adapter range operandlarının geçici değer olmasını zorunlu tuttu "
                f"(instruction {index})."
            )
        if not instruction.result.startswith("%"):
            raise error_type(
                f"{backend_name} adapter geçersiz range sonuç adını reddetti: {instruction.result}"
            )

        # Ortak validator'ın opcode allow-listesini gevşetmeden range'in CFG/use-def
        # güvenliğini aynı iki-temp/tek-result veri akışıyla kanıtla. Bu sentetik
        # binary instruction yalnız doğrulama içindir; adapter planında özgün
        # `range` opcode'u korunur.
        rewritten.append(IRInstruction("binary", ("+", start, end), instruction.result))
    return tuple(rewritten)


def validate_backend_program_with_range(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """IR v1 backend sınırında `range` şemasını fail-closed biçimde genişletir."""
    flows = tuple(
        IRFlow(
            name=flow.name,
            parameters=flow.parameters,
            parameter_types=flow.parameter_types,
            return_type=flow.return_type,
            captures=flow.captures,
            instructions=_rewrite_sequence(
                flow.instructions,
                error_type=error_type,
                backend_name=backend_name,
            ),
        )
        for flow in program.flows
    )
    rewritten = IRProgram(
        version=program.version,
        instructions=_rewrite_sequence(
            program.instructions,
            error_type=error_type,
            backend_name=backend_name,
        ),
        flows=flows,
    )
    validate_backend_program(
        rewritten,
        error_type=error_type,
        backend_name=backend_name,
    )
