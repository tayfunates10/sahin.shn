from __future__ import annotations

from .ir import IRFlow, IRInstruction, IRProgram
from .range_backend_validation import validate_backend_program_with_range

_ALLOWED_PIPELINE_STAGES = frozenset({"ilk", "sırala", "seç"})


def _rewrite_sequence(
    instructions: tuple[IRInstruction, ...],
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> tuple[IRInstruction, ...]:
    rewritten: list[IRInstruction] = []
    for index, instruction in enumerate(instructions):
        if instruction.opcode != "pipeline":
            rewritten.append(instruction)
            continue

        operands = instruction.operands
        if len(operands) not in {2, 3} or instruction.result is None:
            raise error_type(
                f"{backend_name} adapter geçersiz pipeline instruction şemasını reddetti "
                f"(instruction {index}): pipeline stage + source ve en fazla 1 argüman almalı, sonuç üretmelidir"
            )
        stage, source, *arguments = operands
        if stage not in _ALLOWED_PIPELINE_STAGES:
            raise error_type(
                f"{backend_name} adapter bilinmeyen pipeline aşamasını reddetti: {stage!r} "
                f"(instruction {index})."
            )
        if not source.startswith("%"):
            raise error_type(
                f"{backend_name} adapter pipeline source operandının geçici değer olmasını zorunlu tuttu "
                f"(instruction {index})."
            )
        if arguments and not arguments[0].startswith("%"):
            raise error_type(
                f"{backend_name} adapter pipeline argüman operandının geçici değer olmasını zorunlu tuttu "
                f"(instruction {index})."
            )
        if not instruction.result.startswith("%"):
            raise error_type(
                f"{backend_name} adapter geçersiz pipeline sonuç adını reddetti: {instruction.result}"
            )

        # Ortak validator'ın opcode allow-listesini gevşetmeden pipeline'ın CFG/use-def
        # güvenliğini kanıtla. Sentetik unary/binary yalnız doğrulama içindir; adapter
        # planında özgün `pipeline` opcode'u ve stage semantiği aynen korunur.
        if arguments:
            rewritten.append(IRInstruction("binary", ("+", source, arguments[0]), instruction.result))
        else:
            rewritten.append(IRInstruction("unary", ("+", source), instruction.result))
    return tuple(rewritten)


def validate_backend_program_with_pipeline(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """IR v1 backend sınırında `range` + `pipeline` şemasını fail-closed doğrular."""
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
    validate_backend_program_with_range(
        rewritten,
        error_type=error_type,
        backend_name=backend_name,
    )
