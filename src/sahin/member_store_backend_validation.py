from __future__ import annotations

from dataclasses import replace

from .ir import IRFlow, IRInstruction, IRProgram
from .member_store_abi import MemberStoreABIError, validate_member_store_instruction
from .try_backend_validation import validate_backend_program_with_try


def _expand_member_store_for_cfg(
    instructions: tuple[IRInstruction, ...],
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> tuple[IRInstruction, ...]:
    """`member_store` şemasını doğrula ve CFG temp-use analizi için saf write kullanımlarına aç."""
    expanded: list[IRInstruction] = []
    for index, instruction in enumerate(instructions):
        if instruction.opcode != "member_store":
            expanded.append(instruction)
            continue
        try:
            operation = validate_member_store_instruction(instruction)
        except MemberStoreABIError as exc:
            raise error_type(
                f"{backend_name} adapter geçersiz member_store instruction şemasını reddetti "
                f"(instruction {index}): {exc}"
            ) from exc
        # Existing CFG validator already proves every `write` operand is definitely
        # defined on all reachable incoming paths. Expanding to two pure validation
        # uses therefore checks both owner and value temps without weakening gates.
        expanded.extend(
            (
                IRInstruction("write", (operation.target_temp,)),
                IRInstruction("write", (operation.value_temp,)),
            )
        )
    return tuple(expanded)


def validate_backend_program_with_member_store(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """Try + member_store dahil backend ABI/CFG sözleşmesini fail-closed doğrular."""
    instructions = _expand_member_store_for_cfg(
        program.instructions,
        error_type=error_type,
        backend_name=backend_name,
    )
    flows = tuple(
        replace(
            flow,
            instructions=_expand_member_store_for_cfg(
                flow.instructions,
                error_type=error_type,
                backend_name=backend_name,
            ),
        )
        for flow in program.flows
    )
    validate_backend_program_with_try(
        IRProgram(version=program.version, instructions=instructions, flows=flows),
        error_type=error_type,
        backend_name=backend_name,
    )
