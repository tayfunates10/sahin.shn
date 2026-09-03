from __future__ import annotations

from .ir import IRFlow, IRInstruction, IRProgram
from .pipeline_backend_validation import validate_backend_program_with_pipeline

_ITERATOR_OPCODES = frozenset({"iter_begin", "iter_has_next", "iter_value", "iter_advance"})


def _rewrite_sequence(
    instructions: tuple[IRInstruction, ...],
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> tuple[IRInstruction, ...]:
    """Iterator opcode'larını şema/origin doğrulamasından sonra ortak validator biçimine indirger."""
    rewritten: list[IRInstruction] = []
    iterator_temps: set[str] = set()

    for index, instruction in enumerate(instructions):
        opcode = instruction.opcode
        if opcode not in _ITERATOR_OPCODES:
            rewritten.append(instruction)
            continue

        operands = instruction.operands
        result = instruction.result
        if len(operands) != 1:
            raise error_type(
                f"{backend_name} adapter geçersiz {opcode} instruction şemasını reddetti "
                f"(instruction {index}): tam olarak 1 geçici operand bekleniyor"
            )

        operand = operands[0]
        if not operand.startswith("%"):
            raise error_type(
                f"{backend_name} adapter {opcode} operandının geçici değer olmasını zorunlu tuttu "
                f"(instruction {index})."
            )

        if opcode == "iter_begin":
            if result is None or not result.startswith("%"):
                raise error_type(
                    f"{backend_name} adapter iter_begin için geçici bir iterator sonucu zorunlu tuttu "
                    f"(instruction {index})."
                )
            iterator_temps.add(result)
            # Kaynak temp kullanımı + iterator result definite-definition aynı kalır.
            rewritten.append(IRInstruction("unary", ("+", operand), result))
            continue

        if operand not in iterator_temps:
            raise error_type(
                f"{backend_name} adapter {opcode} için iter_begin tarafından üretilmiş iterator bekledi: "
                f"{operand} (instruction {index})."
            )

        if opcode == "iter_advance":
            if result is not None:
                raise error_type(
                    f"{backend_name} adapter iter_advance instruction'ının sonuç üretmesini reddetti "
                    f"(instruction {index})."
                )
            # Yalnız doğrulama kopyasında iterator temp kullanımını koru; gerçek adapter
            # planında özgün iter_advance opcode'u aynen kalır.
            rewritten.append(IRInstruction("write", (operand,)))
            continue

        if result is None or not result.startswith("%"):
            raise error_type(
                f"{backend_name} adapter {opcode} için geçici bir sonuç zorunlu tuttu "
                f"(instruction {index})."
            )
        # has_next/value aynı tek-temp/tek-result veri akışıyla doğrulanır.
        rewritten.append(IRInstruction("unary", ("+", operand), result))

    return tuple(rewritten)


def validate_backend_program_with_foreach(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """IR v1 backend sınırında range + pipeline + ForEach iterator sözleşmesini fail-closed doğrular."""
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
    validate_backend_program_with_pipeline(
        rewritten,
        error_type=error_type,
        backend_name=backend_name,
    )
