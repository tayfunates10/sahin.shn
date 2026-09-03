from __future__ import annotations

import json

from .foreach_backend_validation import validate_backend_program_with_foreach
from .ir import IRFlow, IRInstruction, IRProgram
from .ir_control_flow import IRControlFlowError, validate_control_flow

_TRY_OPCODES = frozenset({"try_guard", "catch"})


def _validate_try_schema(
    instructions: tuple[IRInstruction, ...],
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    for index, instruction in enumerate(instructions):
        if instruction.opcode == "try_guard":
            if len(instruction.operands) != 2 or instruction.result is not None:
                raise error_type(
                    f"{backend_name} adapter geçersiz try_guard şemasını reddetti (instruction {index})."
                )
            handler, protected_end = instruction.operands
            if (
                not handler
                or not protected_end
                or handler.startswith("%")
                or protected_end.startswith("%")
                or handler == protected_end
            ):
                raise error_type(
                    f"{backend_name} adapter geçersiz try_guard hedeflerini reddetti (instruction {index})."
                )
        elif instruction.opcode == "catch":
            if instruction.operands or instruction.result is None or not instruction.result.startswith("%"):
                raise error_type(
                    f"{backend_name} adapter geçersiz catch şemasını reddetti (instruction {index})."
                )


def _validate_try_cfg(
    instructions: tuple[IRInstruction, ...],
    *,
    predefined_names: tuple[str, ...],
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    try:
        validate_control_flow(
            IRProgram(version=1, instructions=instructions),
            predefined_names=predefined_names,
        )
    except IRControlFlowError as exc:
        raise error_type(f"{backend_name} adapter try control-flow doğrulamasını reddetti: {exc}") from exc


def _sanitize_sequence(instructions: tuple[IRInstruction, ...]) -> tuple[IRInstruction, ...]:
    """Try CFG özgün programda doğrulandıktan sonra ortak backend şema katmanı için güvenli kopya üretir."""
    rewritten: list[IRInstruction] = []
    for instruction in instructions:
        if instruction.opcode == "try_guard":
            # Exceptional kenar özgün CFG üzerinde doğrulandı. Ortak validator try opcode'unu
            # tanımadığı için yalnız doğrulama kopyasında guard kaldırılır.
            continue
        if instruction.opcode == "catch":
            assert instruction.result is not None
            rewritten.append(
                IRInstruction("const", ("metin:" + json.dumps("<yakalanan-hata>", ensure_ascii=False),), instruction.result)
            )
            continue
        rewritten.append(instruction)
    return tuple(rewritten)


def validate_backend_program_with_try(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """Try/error-region sözleşmesini doğrular, sonra mevcut backend kalite zincirini korur."""
    _validate_try_schema(program.instructions, error_type=error_type, backend_name=backend_name)
    _validate_try_cfg(
        program.instructions,
        predefined_names=(),
        error_type=error_type,
        backend_name=backend_name,
    )

    flows: list[IRFlow] = []
    for flow in program.flows:
        _validate_try_schema(flow.instructions, error_type=error_type, backend_name=backend_name)
        _validate_try_cfg(
            flow.instructions,
            predefined_names=(*flow.parameters, *flow.captures),
            error_type=error_type,
            backend_name=backend_name,
        )
        flows.append(
            IRFlow(
                name=flow.name,
                parameters=flow.parameters,
                parameter_types=flow.parameter_types,
                return_type=flow.return_type,
                captures=flow.captures,
                instructions=_sanitize_sequence(flow.instructions),
            )
        )

    sanitized = IRProgram(
        version=program.version,
        instructions=_sanitize_sequence(program.instructions),
        flows=tuple(flows),
    )
    validate_backend_program_with_foreach(
        sanitized,
        error_type=error_type,
        backend_name=backend_name,
    )
